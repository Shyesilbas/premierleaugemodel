"""Unified prediction service for API endpoints, pre-match lineup sync, and model audit."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.analytics.player_ratings import analyze_match_starting_xis
from src.api import state
from src.features.build_features import build_prediction_row
from src.models.dixon_coles import (
    align_to_outcome_probs,
    btts_prob,
    expected_goals,
    over_prob,
    team_over_prob,
)
from src.models.model_utils import (
    apply_probability_calibrator,
    blend_log,
    count_tail_probability,
    safe_feature_frame,
)

logger = logging.getLogger("api_server")


def regression_model_skill(artifact: Optional[Dict[str, Any]]) -> str:
    """Expose whether a count prediction uses the gated model, mean baseline, or fallback constant."""
    if artifact is None or "model" not in artifact:
        return "fallback_constant"
    metrics = artifact.get("metrics") or {}
    if metrics.get("selected_model") == "training_mean" or metrics.get("skill_gate_applied"):
        return "baseline"
    return "model"


def _col_float(df: pd.DataFrame, col: str, default: float) -> float:
    """Read a scalar float from the first row of ``df``, preserving 0.0 values."""
    if col not in df.columns or df.empty:
        return float(default)
    val = df[col].iloc[0]
    if pd.isna(val):
        return float(default)
    try:
        fval = float(val)
        return fval if np.isfinite(fval) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _compute_home_share(
    home_exp: float,
    away_exp: float,
    min_share: float = 0.20,
    max_share: float = 0.80,
    default: float = 0.50,
) -> float:
    """Clamp the home team's expected share of a match total within ``[min_share, max_share]``."""
    total = float(home_exp) + float(away_exp)
    if total <= 0.0 or not np.isfinite(total):
        return float(default)
    return float(max(min_share, min(max_share, float(home_exp) / total)))


def is_1x2_ensemble_active(outcome_artifact: Optional[Dict[str, Any]]) -> bool:
    """Return True only when the 1X2 ensemble is both enabled and passed the outer-season gate."""
    if not outcome_artifact or "model_dc" not in outcome_artifact:
        return False
    metrics = outcome_artifact.get("metrics") or {}
    prod_cfg = metrics.get("1x2_ensemble_production") or {}
    if not prod_cfg.get("enabled", True):
        return False
    outer_eval = metrics.get("1x2_ensemble_outer_eval")
    if isinstance(outer_eval, dict) and "gate_passed" in outer_eval:
        return bool(outer_eval["gate_passed"])
    return True


def predict_1x2_probabilities(
    row_df: pd.DataFrame,
    outcome_artifact: Dict[str, Any],
) -> Tuple[np.ndarray, bool]:
    """Compute calibrated 1X2 probabilities ``[p_home, p_draw, p_away]`` for a single-row frame."""
    o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact["feature_names"])
    X_1x2 = safe_feature_frame(row_df, list(o_features), fill_value=np.nan)
    probs_1x2 = outcome_artifact["model_1x2"].predict_proba(X_1x2)

    has_ensemble = is_1x2_ensemble_active(outcome_artifact)
    if has_ensemble:
        dc_probs_1x2 = outcome_artifact["model_dc"].predict_proba(row_df)
        probs_1x2 = blend_log(probs_1x2, dc_probs_1x2, outcome_artifact["ensemble_weight"])
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2_ensemble")
    else:
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2")

    if calibrator_1x2:
        probs_1x2 = apply_probability_calibrator(probs_1x2, calibrator_1x2)
    return np.asarray(probs_1x2[0], dtype=float), has_ensemble


def _calc_team_totals(score_matrix: np.ndarray, side_name: str, lam: float) -> Dict[str, Any]:
    p_05 = round(float(team_over_prob(score_matrix, side_name, 0.5)[0] * 100.0), 1)
    p_15 = round(float(team_over_prob(score_matrix, side_name, 1.5)[0] * 100.0), 1)
    p_25 = round(float(team_over_prob(score_matrix, side_name, 2.5)[0] * 100.0), 1)
    p_15 = min(p_05, p_15)
    p_25 = min(p_15, p_25)

    lines = [
        {
            "line": 0.5,
            "over_pct": p_05,
            "under_pct": round(100.0 - p_05, 1),
            "fair_odds_over": round(100.0 / max(p_05, 1.0), 2),
            "fair_odds_under": round(100.0 / max(100.0 - p_05, 1.0), 2),
            "dist": abs(p_05 - 50.0),
        },
        {
            "line": 1.5,
            "over_pct": p_15,
            "under_pct": round(100.0 - p_15, 1),
            "fair_odds_over": round(100.0 / max(p_15, 1.0), 2),
            "fair_odds_under": round(100.0 / max(100.0 - p_15, 1.0), 2),
            "dist": abs(p_15 - 50.0),
        },
        {
            "line": 2.5,
            "over_pct": p_25,
            "under_pct": round(100.0 - p_25, 1),
            "fair_odds_over": round(100.0 / max(p_25, 1.0), 2),
            "fair_odds_under": round(100.0 / max(100.0 - p_25, 1.0), 2),
            "dist": abs(p_25 - 50.0),
        },
    ]
    primary = min(lines, key=lambda x: x["dist"])
    return {
        "expected_goals": round(float(lam), 2),
        "primary_line": primary["line"],
        "primary_over_pct": primary["over_pct"],
        "primary_under_pct": primary["under_pct"],
        "primary_fair_odds_over": primary["fair_odds_over"],
        "primary_fair_odds_under": primary["fair_odds_under"],
        "lines": {
            "0.5": {
                "over_pct": p_05,
                "under_pct": round(100.0 - p_05, 1),
                "fair_odds_over": lines[0]["fair_odds_over"],
                "fair_odds_under": lines[0]["fair_odds_under"],
            },
            "1.5": {
                "over_pct": p_15,
                "under_pct": round(100.0 - p_15, 1),
                "fair_odds_over": lines[1]["fair_odds_over"],
                "fair_odds_under": lines[1]["fair_odds_under"],
            },
            "2.5": {
                "over_pct": p_25,
                "under_pct": round(100.0 - p_25, 1),
                "fair_odds_over": lines[2]["fair_odds_over"],
                "fair_odds_under": lines[2]["fair_odds_under"],
            },
        },
    }


def predict_goals_markets(
    row_df: pd.DataFrame,
    probs_1x2: np.ndarray,
    goals_artifact: Optional[Dict[str, Any]],
    outcome_artifact: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], float, str]:
    """Compute aligned score-matrix markets, O/U lines, BTTS, and team totals."""
    goals_extra: Dict[str, Any] = {}
    over_source = "legacy"
    prob_o25 = 50.0

    if goals_artifact is not None:
        score_matrix = align_to_outcome_probs(
            goals_artifact["model"].predict_matrices(row_df),
            np.atleast_2d(probs_1x2),
        )
        lam_h, lam_a = expected_goals(score_matrix)
        for line in goals_artifact.get("ou_lines", [1.5, 2.5, 3.5]):
            key = f"over_{line}"
            gate = goals_artifact.get("skill_gate", {}).get(key, "model_matrix")
            if gate == "baseline":
                p_line = float(goals_artifact["base_rates"][key])
                source = "baseline"
            else:
                p_line = float(over_prob(score_matrix, line)[0])
                calibrator = goals_artifact.get("calibrators", {}).get(key)
                if calibrator:
                    binary = np.array([[1.0 - p_line, p_line]], dtype=float)
                    p_line = float(apply_probability_calibrator(binary, calibrator)[0, 1])
                source = "model" if gate == "model" else "model_matrix"
            goals_extra[key] = {"pct": round(p_line * 100.0, 1), "source": source}

        p_btts = float(btts_prob(score_matrix)[0])
        btts_gate_choice = goals_artifact.get("skill_gate", {}).get("btts", "model_matrix")
        btts_prior = float(goals_artifact.get("base_rates", {}).get("btts", 0.566))
        if btts_gate_choice == "baseline":
            p_btts = btts_prior
            btts_source = "baseline"
        else:
            btts_calibrator = goals_artifact.get("calibrators", {}).get("btts")
            if btts_calibrator:
                p_btts = float(
                    apply_probability_calibrator(np.array([[1.0 - p_btts, p_btts]]), btts_calibrator)[0, 1]
                )
            btts_source = "model" if btts_gate_choice == "model" else "model_matrix"

        goals_extra["btts_pct"] = round(p_btts * 100.0, 1)
        goals_extra["btts_source"] = btts_source
        goals_extra["btts_prior_pct"] = round(btts_prior * 100.0, 1)
        btts_informative = bool(
            goals_artifact.get("evaluation_gate", {}).get("btts_gate", {}).get("passed", False)
        )
        goals_extra["btts_informative"] = btts_informative
        goals_extra["btts_prediction"] = (
            ("KG Var" if p_btts >= 0.5 else "KG Yok") if btts_informative else None
        )
        goals_extra["expected_home_goals"] = round(float(lam_h[0]), 2)
        goals_extra["expected_away_goals"] = round(float(lam_a[0]), 2)
        goals_extra["expected_total_goals"] = round(float(lam_h[0] + lam_a[0]), 2)

        if "over_1.5" in goals_extra and "over_2.5" in goals_extra and "over_3.5" in goals_extra:
            p_15 = goals_extra["over_1.5"]["pct"]
            p_25 = min(p_15, goals_extra["over_2.5"]["pct"])
            p_35 = min(p_25, goals_extra["over_3.5"]["pct"])
            goals_extra["over_2.5"]["pct"] = p_25
            goals_extra["over_3.5"]["pct"] = p_35

        goals_extra["team_totals"] = {
            "home": _calc_team_totals(score_matrix, "home", float(lam_h[0])),
            "away": _calc_team_totals(score_matrix, "away", float(lam_a[0])),
        }

        over_source = goals_extra.get("over_2.5", {}).get("source", "model_matrix")
        prob_o25 = float(goals_extra.get("over_2.5", {}).get("pct", 50.0))
    elif outcome_artifact is not None and "model_o25" in outcome_artifact:
        o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact.get("feature_names", []))
        o25_features = outcome_artifact.get("feature_names_o25", o_features)
        probs_o25 = outcome_artifact["model_o25"].predict_proba(
            safe_feature_frame(row_df, list(o25_features), fill_value=np.nan)
        )
        calibrator_o25 = outcome_artifact.get("calibrators", {}).get("o25")
        if calibrator_o25:
            probs_o25 = apply_probability_calibrator(probs_o25, calibrator_o25)
        prob_o25 = float(probs_o25[0][1] * 100.0)
        over_source = "legacy"
    else:
        over_source = "fallback_constant"

    return goals_extra, prob_o25, over_source


def predict_count_market(
    row_df: pd.DataFrame,
    artifact: Optional[Dict[str, Any]],
    *,
    min_val: float,
    max_val: float,
    fallback_total: float,
    thresholds: Sequence[int] = (),
    fallback_probs_pct: Sequence[float] = (),
) -> Tuple[float, Dict[int, float], str]:
    """Predict expected count and NB2 tail probabilities with consistent NaN imputation."""
    skill = regression_model_skill(artifact)
    if artifact is not None and "model" in artifact:
        features = artifact.get("feature_names") or artifact.get("feature_cols") or []
        X = safe_feature_frame(row_df, list(features), fill_value=np.nan)
        try:
            exp_val = float(artifact["model"].predict(X)[0])
            exp_val = max(min_val, min(max_val, exp_val))
            alpha = float(artifact.get("count_dispersion_alpha", 0.0))
            probs = {
                int(t): count_tail_probability(exp_val, alpha, int(t)) * 100.0
                for t in thresholds
            }
            return exp_val, probs, skill
        except Exception as exc:
            logger.warning("Count model prediction failed; using fallback constant: %s", exc)
            skill = "fallback_constant"

    probs = {
        int(t): float(fallback_probs_pct[idx]) if idx < len(fallback_probs_pct) else 50.0
        for idx, t in enumerate(thresholds)
    }
    return float(fallback_total), probs, "fallback_constant"


def score_row_with_production_models(
    simulated_df: pd.DataFrame,
    outcome_artifact: Dict[str, Any],
    goals_artifact: Optional[Dict[str, Any]],
) -> Dict[str, float]:
    """Score a pre-built feature row using the unified 1X2 and goals pipeline."""
    probs_1x2, _ = predict_1x2_probabilities(simulated_df, outcome_artifact)
    goals_extra, prob_o25, _ = predict_goals_markets(
        simulated_df, probs_1x2, goals_artifact, outcome_artifact
    )
    lam_h = float(goals_extra.get("expected_home_goals", 0.0))
    lam_a = float(goals_extra.get("expected_away_goals", 0.0))
    p_btts = float(goals_extra.get("btts_pct", 0.0))

    return {
        "home_pct": float(probs_1x2[0] * 100.0),
        "draw_pct": float(probs_1x2[1] * 100.0),
        "away_pct": float(probs_1x2[2] * 100.0),
        "lambda_home": lam_h,
        "lambda_away": lam_a,
        "lambda_total": lam_h + lam_a,
        "over_25_pct": float(prob_o25),
        "btts_pct": p_btts,
        "home_xi_rating": _col_float(simulated_df, "home_xi_rating", 0.0),
        "away_xi_rating": _col_float(simulated_df, "away_xi_rating", 0.0),
        "xi_rating_diff": _col_float(simulated_df, "xi_rating_diff", 0.0),
        "xi_att_vs_def_diff": _col_float(simulated_df, "xi_att_vs_def_diff", 0.0),
    }


def compute_match_prediction(
    home_id: int,
    away_id: int,
    season: Optional[str] = None,
    match_id: Optional[int] = None,
    *,
    include_lineup_analysis: bool = True,
) -> Dict[str, Any]:
    """Compute the full match prediction payload for ``home_id`` vs ``away_id``."""
    home_meta = state.teams_dict.get(home_id)
    away_meta = state.teams_dict.get(away_id)
    if not home_meta or not away_meta:
        raise KeyError("Team not found.")

    team_states, strength_state, until, draw_state = state.get_live_state(season)
    target_season = str(season) if season and season != "all" else state.CURRENT_SEASON
    gameweek: Optional[float] = None
    target_match_id: Optional[int] = None

    referee_info: Optional[Dict[str, Any]] = None
    if until is None:
        match_date = pd.Timestamp.now()
        if not state.df_features.empty and "is_played" in state.df_features.columns:
            upcoming = state.df_features[
                (state.df_features["home_id"] == home_id)
                & (state.df_features["away_id"] == away_id)
                & (~state.df_features["is_played"])
            ]
            if not upcoming.empty:
                fx = upcoming.iloc[0]
                match_date = pd.Timestamp(fx["match_date"])
                if pd.notnull(fx.get("match_id")):
                    try:
                        target_match_id = int(fx["match_id"])
                    except Exception:
                        pass
                if pd.notnull(fx.get("season")):
                    target_season = str(fx["season"])
                if pd.notnull(fx.get("gameweek")):
                    gameweek = float(fx["gameweek"])
                referee_info = {
                    c: (fx[c] if pd.notnull(fx.get(c)) else None)
                    for c in ["referee_name", "referee_avg_cards", "referee_avg_fouls", "referee_prior_matches"]
                    if c in fx.index
                }
    else:
        match_date = until + pd.Timedelta(days=7)

    simulated_df = build_prediction_row(
        team_states,
        strength_state,
        home_id,
        away_id,
        match_date,
        referee_info,
        season=target_season,
        draw_state=draw_state,
        gameweek=gameweek,
        match_id=match_id or target_match_id,
    )

    # 1. Corners
    exp_corners, corner_probs, corner_skill = predict_count_market(
        simulated_df,
        state.corner_artifact,
        min_val=5.0,
        max_val=18.0,
        fallback_total=10.2,
        thresholds=(8, 9, 10),
        fallback_probs_pct=(68.0, 54.0, 40.0),
    )

    # 2. Throws
    exp_throws, throws_probs, throws_skill = predict_count_market(
        simulated_df,
        state.throws_artifact,
        min_val=20.0,
        max_val=50.0,
        fallback_total=35.0,
        thresholds=(33, 34, 36),
        fallback_probs_pct=(58.0, 50.0, 38.0),
    )

    # 3. Saves
    exp_saves, _, saves_skill = predict_count_market(
        simulated_df,
        state.saves_artifact,
        min_val=2.0,
        max_val=12.0,
        fallback_total=5.7,
        thresholds=(),
    )

    # 4. Outcome & Goals
    probs_1x2, _ = predict_1x2_probabilities(simulated_df, state.outcome_artifact)
    prob_h = float(probs_1x2[0] * 100.0)
    prob_d = float(probs_1x2[1] * 100.0)
    prob_a = float(probs_1x2[2] * 100.0)

    goals_extra, prob_o25, over_source = predict_goals_markets(
        simulated_df, probs_1x2, state.goals_artifact, state.outcome_artifact
    )

    fav = home_meta["name"] if prob_h > prob_a else away_meta["name"]
    fav_label = f"{fav} Favori" if abs(prob_h - prob_a) > 10 else "Dengeli Mücadele"

    # 5. Offsides
    exp_offsides, offside_probs, offside_skill = predict_count_market(
        simulated_df,
        state.offside_artifact,
        min_val=0.5,
        max_val=10.0,
        fallback_total=3.26,
        thresholds=(2, 3, 4),
        fallback_probs_pct=(65.0, 45.0, 25.0),
    )
    h_off_for = _col_float(simulated_df, "home_offsides_for_roll_5", 1.6)
    a_off_for = _col_float(simulated_df, "away_offsides_for_roll_5", 1.6)
    h_off_against = _col_float(simulated_df, "home_offsides_against_roll_5", 1.6)
    a_off_against = _col_float(simulated_df, "away_offsides_against_roll_5", 1.6)
    home_off_share = _compute_home_share(
        0.5 * (h_off_for + a_off_against),
        0.5 * (a_off_for + h_off_against),
        default=0.52,
    )

    # 6. Cards
    exp_cards, cards_probs, cards_skill = predict_count_market(
        simulated_df,
        state.cards_artifact,
        min_val=1.0,
        max_val=12.0,
        fallback_total=4.2,
        thresholds=(3, 4, 5),
        fallback_probs_pct=(62.0, 44.0, 26.0),
    )
    h_c_for = _col_float(simulated_df, "home_cards_for_roll_5", 2.1)
    a_c_for = _col_float(simulated_df, "away_cards_for_roll_5", 2.1)
    h_c_against = _col_float(simulated_df, "home_cards_against_roll_5", 2.1)
    a_c_against = _col_float(simulated_df, "away_cards_against_roll_5", 2.1)
    home_cards_share = _compute_home_share(
        0.5 * (h_c_for + a_c_against),
        0.5 * (a_c_for + h_c_against),
        default=0.50,
    )

    raw_ref = simulated_df.get("referee_name", pd.Series([None])).iloc[0]
    ref_name = str(raw_ref) if pd.notnull(raw_ref) and raw_ref else "Premier League Hakem Heyeti"
    ref_avg_c = _col_float(simulated_df, "referee_avg_cards", 4.15)
    ref_avg_f = _col_float(simulated_df, "referee_avg_fouls", 21.5)

    # Dynamic shares for corners, throws, saves
    h_crn_for = _col_float(simulated_df, "home_corners_for_roll_5", 5.2)
    a_crn_for = _col_float(simulated_df, "away_corners_for_roll_5", 4.8)
    h_crn_against = _col_float(simulated_df, "home_corners_against_roll_5", 4.8)
    a_crn_against = _col_float(simulated_df, "away_corners_against_roll_5", 5.2)
    home_c_share = _compute_home_share(
        0.5 * (h_crn_for + a_crn_against),
        0.5 * (a_crn_for + h_crn_against),
        default=0.55,
    )

    h_th_for_5 = _col_float(simulated_df, "home_throws_roll_5", 18.0)
    a_th_for_5 = _col_float(simulated_df, "away_throws_roll_5", 17.0)
    h_th_opp_5 = _col_float(simulated_df, "home_opponent_throws_roll_5", 17.0)
    a_th_opp_5 = _col_float(simulated_df, "away_opponent_throws_roll_5", 18.0)
    h_th_for_10 = _col_float(simulated_df, "home_throws_roll_10", h_th_for_5)
    a_th_for_10 = _col_float(simulated_df, "away_throws_roll_10", a_th_for_5)
    h_th_opp_10 = _col_float(simulated_df, "home_opponent_throws_roll_10", h_th_opp_5)
    a_th_opp_10 = _col_float(simulated_df, "away_opponent_throws_roll_10", a_th_opp_5)
    home_t_share = _compute_home_share(
        0.25 * (h_th_for_5 + a_th_opp_5) + 0.25 * (h_th_for_10 + a_th_opp_10),
        0.25 * (a_th_for_5 + h_th_opp_5) + 0.25 * (a_th_for_10 + h_th_opp_10),
        min_share=0.25,
        max_share=0.75,
        default=0.51,
    )

    h_sv = _col_float(simulated_df, "home_saves_roll_5", 2.8)
    a_sv = _col_float(simulated_df, "away_saves_roll_5", 2.9)
    h_sot_for = _col_float(simulated_df, "home_shots_ontarget_for_roll_5", 4.5)
    a_sot_for = _col_float(simulated_df, "away_shots_ontarget_for_roll_5", 4.0)
    home_s_share = _compute_home_share(
        0.5 * (h_sv + a_sot_for * 0.70),
        0.5 * (a_sv + h_sot_for * 0.70),
        default=0.48,
    )

    target_mid = match_id or target_match_id
    lineup_analysis = None
    if include_lineup_analysis:
        try:
            lineup_analysis = analyze_match_starting_xis(
                home_id=home_id,
                away_id=away_id,
                match_id=target_mid,
                referee_avg_cards=ref_avg_c,
            )
        except Exception as exc:
            logger.warning("Error computing lineup analysis in compute_match_prediction: %s", exc)

    return {
        "home_team": home_meta,
        "away_team": away_meta,
        "favorite_label": fav_label,
        "outcome": {
            "home_win_pct": round(prob_h, 1),
            "draw_pct": round(prob_d, 1),
            "away_win_pct": round(prob_a, 1),
            "over_2_5_goals_pct": round(prob_o25, 1),
            "over_2_5_source": over_source,
        },
        "goals": goals_extra,
        "corners": {
            "model_skill": corner_skill,
            "expected_total": round(exp_corners, 1),
            "expected_home": round(exp_corners * home_c_share, 1),
            "expected_away": round(exp_corners * (1.0 - home_c_share), 1),
            "prob_over_8_5_pct": round(corner_probs[8], 1),
            "prob_over_9_5_pct": round(corner_probs[9], 1),
            "prob_over_10_5_pct": round(corner_probs[10], 1),
        },
        "cards": {
            "model_skill": cards_skill,
            "expected_total": round(exp_cards, 1),
            "expected_home": round(exp_cards * home_cards_share, 1),
            "expected_away": round(exp_cards * (1.0 - home_cards_share), 1),
            "prob_over_3_5_pct": round(cards_probs[3], 1),
            "prob_over_4_5_pct": round(cards_probs[4], 1),
            "prob_over_5_5_pct": round(cards_probs[5], 1),
        },
        "referee": {
            "name": ref_name,
            "avg_cards": round(ref_avg_c, 1),
            "avg_fouls": round(ref_avg_f, 1),
        },
        "throws": {
            "model_skill": throws_skill,
            "expected_total": round(exp_throws, 1),
            "expected_home": round(exp_throws * home_t_share, 1),
            "expected_away": round(exp_throws * (1.0 - home_t_share), 1),
            "prob_over_33_5_pct": round(throws_probs[33], 1),
            "prob_over_34_5_pct": round(throws_probs[34], 1),
            "prob_over_36_5_pct": round(throws_probs[36], 1),
        },
        "saves": {
            "model_skill": saves_skill,
            "expected_total": round(exp_saves, 1),
            "expected_home": round(exp_saves * home_s_share, 1),
            "expected_away": round(exp_saves * (1.0 - home_s_share), 1),
        },
        "shots": {
            "model_skill": "heuristic_from_saves",
            "expected_total": round(exp_saves * 4.1, 1),
        },
        "offsides": {
            "model_skill": offside_skill,
            "expected_total": round(exp_offsides, 1),
            "expected_home": round(exp_offsides * home_off_share, 1),
            "expected_away": round(exp_offsides * (1.0 - home_off_share), 1),
            "prob_over_2_5_pct": round(offside_probs[2], 1),
            "prob_over_3_5_pct": round(offside_probs[3], 1),
            "prob_over_4_5_pct": round(offside_probs[4], 1),
        },
        "lineup_analysis": lineup_analysis,
    }
