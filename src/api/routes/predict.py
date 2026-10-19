"""Prediction, model audit and benchmark routes."""

import logging
import numpy as np
import pandas as pd
from fastapi import HTTPException, Query
from src.analytics.model_audit import run_model_audit
from src.analytics.player_ratings import analyze_match_starting_xis
from src.config import DEFAULT_SEASON, ROOT as BASE_DIR
from src.features.build_features import build_prediction_row
from src.models.dixon_coles import align_to_outcome_probs, btts_prob, expected_goals, over_prob, team_over_prob
from src.models.model_utils import apply_probability_calibrator, blend_log, count_tail_probability, safe_feature_frame as _safe_features
from typing import Any, Dict, Optional
from src.api import state
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("api_server")

def _regression_model_skill(artifact: Optional[Dict[str, Any]]) -> str:
    """Expose whether a count prediction uses the gated model or mean baseline."""
    if artifact is None:
        return "baseline"
    metrics = artifact.get("metrics") or {}
    if metrics.get("selected_model") == "training_mean" or metrics.get("skill_gate_applied"):
        return "baseline"
    return "model"


@router.get("/api/model-audit")
def get_model_audit(
    season: str = DEFAULT_SEASON,
    gameweek: Optional[int] = None,
    force_recalc: bool = False,
):
    """Returns prospective zero-leakage model performance metrics and

    match verification cards vs actual outcomes and market odds.
    """
    data = run_model_audit(season=season, force_recalc=force_recalc)
    if gameweek is not None and "matches" in data:
        filtered = [m for m in data["matches"] if m.get("gameweek") == int(gameweek)]
        return {**data, "matches": filtered, "selected_gameweek": gameweek}
    return data


@router.get("/api/predict")
def predict_match(
    home_id: int = Query(...),
    away_id: int = Query(...),
    season: Optional[str] = None,
    match_id: Optional[int] = None,
):
    """
    Computes real-time micro-metrics and match predictions between two teams
    using trained models and the latest available team rolling statistics.
    Optionally scoped to a specific season (2024_25 or 2025_26).
    """
    if home_id == away_id:
        raise HTTPException(status_code=400, detail="Home and Away teams must be different.")

    home_meta = state.teams_dict.get(home_id)
    away_meta = state.teams_dict.get(away_id)
    if not home_meta or not away_meta:
        raise HTTPException(status_code=404, detail="Team not found.")

    team_states, strength_state, until, draw_state = state.get_live_state(season)
    target_season = str(season) if season and season != "all" else state.CURRENT_SEASON
    gameweek: Optional[float] = None
    target_match_id: Optional[int] = None

    # Reference date & referee: use the scheduled (unplayed) fixture of this pairing if it exists
    referee_info: Optional[Dict[str, Any]] = None
    if until is None:
        match_date = pd.Timestamp.now()
        if not state.df_features.empty and "is_played" in state.df_features.columns:
            upcoming = state.df_features[
                (state.df_features["home_id"] == home_id) & (state.df_features["away_id"] == away_id) & (~state.df_features["is_played"])
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
        match_date = until + pd.Timedelta(days=7)  # Hypothetical next match after season end

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

    # 1. Corner Prediction
    c_features = state.corner_artifact["feature_names"]
    X_c = _safe_features(simulated_df, c_features)
    exp_corners = float(state.corner_artifact["model"].predict(X_c)[0])
    exp_corners = max(5.0, min(18.0, exp_corners))
    # Use the count distribution fitted with the production model.
    corner_alpha = state.corner_artifact.get("count_dispersion_alpha", 0.0)
    prob_c85 = count_tail_probability(exp_corners, corner_alpha, 8) * 100
    prob_c95 = count_tail_probability(exp_corners, corner_alpha, 9) * 100
    prob_c105 = count_tail_probability(exp_corners, corner_alpha, 10) * 100

    # 2. Throws Prediction
    t_features = state.throws_artifact["feature_names"]
    X_t = _safe_features(simulated_df, t_features)
    exp_throws = float(state.throws_artifact["model"].predict(X_t)[0])
    exp_throws = max(20.0, min(50.0, exp_throws))
    throws_alpha = state.throws_artifact.get("count_dispersion_alpha", 0.0)
    prob_t335 = count_tail_probability(exp_throws, throws_alpha, 33) * 100
    prob_t345 = count_tail_probability(exp_throws, throws_alpha, 34) * 100
    prob_t365 = count_tail_probability(exp_throws, throws_alpha, 36) * 100

    # 3. Saves Prediction
    s_features = state.saves_artifact["feature_names"]
    X_s = _safe_features(simulated_df, s_features)
    exp_saves = float(state.saves_artifact["model"].predict(X_s)[0])
    exp_saves = max(2.0, min(12.0, exp_saves))

    # 4. Outcome & Goals Prediction
    o_features = state.outcome_artifact.get("feature_names_1x2", state.outcome_artifact["feature_names"])
    o25_features = state.outcome_artifact.get("feature_names_o25", o_features)
    # Preserve missing 1X2 inputs so the fitted sklearn median imputer (or
    # LightGBM's native missing-value handling) sees the same representation
    # used at training time. Filling with zero here bypasses that preprocessing.
    probs_1x2 = state.outcome_artifact["model_1x2"].predict_proba(
        _safe_features(simulated_df, o_features, fill_value=np.nan)
    )
    # Enable Dixon-Coles physics blend if 1x2_ensemble_production is enabled
    has_ensemble = (
        "model_dc" in state.outcome_artifact
        and state.outcome_artifact.get("metrics", {})
        .get("1x2_ensemble_production", {})
        .get("enabled", True)
    )
    if has_ensemble:
        dc_probs_1x2 = state.outcome_artifact["model_dc"].predict_proba(simulated_df)
        probs_1x2 = blend_log(probs_1x2, dc_probs_1x2, state.outcome_artifact["ensemble_weight"])
        calibrator_1x2 = state.outcome_artifact.get("calibrators", {}).get("1x2_ensemble")
    else:
        calibrator_1x2 = state.outcome_artifact.get("calibrators", {}).get("1x2")
    if calibrator_1x2:
        probs_1x2 = apply_probability_calibrator(probs_1x2, calibrator_1x2)
    probs_1x2 = probs_1x2[0]
    prob_h = float(probs_1x2[0] * 100)
    prob_d = float(probs_1x2[1] * 100)
    prob_a = float(probs_1x2[2] * 100)

    goals_extra: Dict[str, Any] = {}
    over_source = "legacy"
    if state.goals_artifact is not None:
        # Align score cells to the (better-scoring) 1X2 model so every market shown agrees with it.
        score_matrix = align_to_outcome_probs(
            state.goals_artifact["model"].predict_matrices(simulated_df), np.atleast_2d(probs_1x2)
        )
        lam_h, lam_a = expected_goals(score_matrix)
        for line in state.goals_artifact.get("ou_lines", [1.5, 2.5, 3.5]):
            key = f"over_{line}"
            gate = state.goals_artifact.get("skill_gate", {}).get(key, "model_matrix")
            if gate == "baseline":
                p_line = float(state.goals_artifact["base_rates"][key])
                source = "baseline"
            else:
                p_line = float(over_prob(score_matrix, line)[0])
                calibrator = state.goals_artifact.get("calibrators", {}).get(key)
                if calibrator:
                    binary = np.array([[1.0 - p_line, p_line]], dtype=float)
                    p_line = float(apply_probability_calibrator(binary, calibrator)[0, 1])
                source = "model" if gate == "model" else "model_matrix"
            goals_extra[key] = {"pct": round(p_line * 100.0, 1), "source": source}

        # BTTS from bivariate score matrix with dynamic Bayesian prior threshold
        p_btts = float(btts_prob(score_matrix)[0])
        btts_calibrator = state.goals_artifact.get("calibrators", {}).get("btts")
        if btts_calibrator:
            p_btts = float(apply_probability_calibrator(np.array([[1.0 - p_btts, p_btts]]), btts_calibrator)[0, 1])
        btts_prior = float(state.goals_artifact.get("base_rates", {}).get("btts", 0.566))
        goals_extra["btts_pct"] = round(p_btts * 100.0, 1)
        goals_extra["btts_source"] = "model_matrix"
        goals_extra["btts_prior_pct"] = round(btts_prior * 100.0, 1)
        # No label when the BTTS gate failed (model not better than the league average, GOAL_MODELS_ANALYSIS P5).
        btts_informative = bool(state.goals_artifact.get("evaluation_gate", {}).get("btts_gate", {}).get("passed", False))
        goals_extra["btts_informative"] = btts_informative
        goals_extra["btts_prediction"] = ("KG Var" if p_btts >= 0.5 else "KG Yok") if btts_informative else None
        goals_extra["expected_home_goals"] = round(float(lam_h[0]), 2)
        goals_extra["expected_away_goals"] = round(float(lam_a[0]), 2)
        goals_extra["expected_total_goals"] = round(float(lam_h[0] + lam_a[0]), 2)

        # Enforce mathematical monotonicity: P(Over 1.5) >= P(Over 2.5) >= P(Over 3.5)
        p_15 = goals_extra["over_1.5"]["pct"]
        p_25 = min(p_15, goals_extra["over_2.5"]["pct"])
        p_35 = min(p_25, goals_extra["over_3.5"]["pct"])
        goals_extra["over_2.5"]["pct"] = p_25
        goals_extra["over_3.5"]["pct"] = p_35

        # Individual Team Totals (Tek taraflı gol baremleri: 0.5, 1.5, 2.5)
        def _calc_team_totals(side_name: str, lam: float) -> Dict[str, Any]:
            p_05 = round(float(team_over_prob(score_matrix, side_name, 0.5)[0] * 100.0), 1)
            p_15 = round(float(team_over_prob(score_matrix, side_name, 1.5)[0] * 100.0), 1)
            p_25 = round(float(team_over_prob(score_matrix, side_name, 2.5)[0] * 100.0), 1)
            p_15 = min(p_05, p_15)
            p_25 = min(p_15, p_25)

            lines = [
                {"line": 0.5, "over_pct": p_05, "under_pct": round(100.0 - p_05, 1), "fair_odds_over": round(100.0 / max(p_05, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_05, 1.0), 2), "dist": abs(p_05 - 50.0)},
                {"line": 1.5, "over_pct": p_15, "under_pct": round(100.0 - p_15, 1), "fair_odds_over": round(100.0 / max(p_15, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_15, 1.0), 2), "dist": abs(p_15 - 50.0)},
                {"line": 2.5, "over_pct": p_25, "under_pct": round(100.0 - p_25, 1), "fair_odds_over": round(100.0 / max(p_25, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_25, 1.0), 2), "dist": abs(p_25 - 50.0)},
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
                    "0.5": {"over_pct": p_05, "under_pct": round(100.0 - p_05, 1), "fair_odds_over": lines[0]["fair_odds_over"], "fair_odds_under": lines[0]["fair_odds_under"]},
                    "1.5": {"over_pct": p_15, "under_pct": round(100.0 - p_15, 1), "fair_odds_over": lines[1]["fair_odds_over"], "fair_odds_under": lines[1]["fair_odds_under"]},
                    "2.5": {"over_pct": p_25, "under_pct": round(100.0 - p_25, 1), "fair_odds_over": lines[2]["fair_odds_over"], "fair_odds_under": lines[2]["fair_odds_under"]},
                }
            }

        goals_extra["team_totals"] = {
            "home": _calc_team_totals("home", lam_h[0]),
            "away": _calc_team_totals("away", lam_a[0]),
        }

        over_source = goals_extra["over_2.5"]["source"]
        prob_o25 = float(p_25)
    else:
        probs_o25 = state.outcome_artifact["model_o25"].predict_proba(_safe_features(simulated_df, o25_features))
        calibrator_o25 = state.outcome_artifact.get("calibrators", {}).get("o25")
        if calibrator_o25:
            probs_o25 = apply_probability_calibrator(probs_o25, calibrator_o25)
        prob_o25 = float(probs_o25[0][1] * 100)

    fav = home_meta["name"] if prob_h > prob_a else away_meta["name"]
    fav_label = f"{fav} Favori" if abs(prob_h - prob_a) > 10 else "Dengeli Mücadele"

    # 5. Offside Prediction
    exp_offsides = 3.26
    prob_off25 = 65.0
    prob_off35 = 45.0
    prob_off45 = 25.0
    home_off_share = 0.52

    if state.offside_artifact is not None:
        off_features = state.offside_artifact.get("feature_cols") or state.offside_artifact.get("feature_names", [])
        missing_cols = [c for c in off_features if c not in simulated_df.columns]
        for m in missing_cols:
            simulated_df[m] = 0.0
        X_off = simulated_df[off_features].fillna(0.0)
        try:
            exp_offsides = float(state.offside_artifact["model"].predict(X_off)[0])
            exp_offsides = max(0.5, min(10.0, exp_offsides))
            offside_alpha = state.offside_artifact.get("count_dispersion_alpha", 0.0)
            prob_off25 = count_tail_probability(exp_offsides, offside_alpha, 2) * 100
            prob_off35 = count_tail_probability(exp_offsides, offside_alpha, 3) * 100
            prob_off45 = count_tail_probability(exp_offsides, offside_alpha, 4) * 100
        except Exception as e:
            logger.warning("Error predicting offsides: %s", e)

        # Dynamic home/away offside split blending offside tendency and opponent trap/line
        h_off_for = float(simulated_df.get("home_offsides_for_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        a_off_for = float(simulated_df.get("away_offsides_for_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        h_off_against = float(simulated_df.get("home_offsides_against_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        a_off_against = float(simulated_df.get("away_offsides_against_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        home_exp_off = 0.5 * (h_off_for + a_off_against)
        away_exp_off = 0.5 * (a_off_for + h_off_against)
        total_exp_off = home_exp_off + away_exp_off
        if total_exp_off > 0:
            home_off_share = max(0.20, min(0.80, home_exp_off / total_exp_off))

    # 6. Cards Prediction
    exp_cards = 4.2
    prob_c35 = 62.0
    prob_c45 = 44.0
    prob_c55 = 26.0
    home_cards_share = 0.50

    if state.cards_artifact is not None:
        c_features = state.cards_artifact.get("feature_cols", [])
        missing_c = [c for c in c_features if c not in simulated_df.columns]
        for m in missing_c:
            simulated_df[m] = 0.0
        X_cards = simulated_df[c_features].fillna(0.0)
        try:
            exp_cards = float(state.cards_artifact["model"].predict(X_cards)[0])
            exp_cards = max(1.0, min(12.0, exp_cards))
            cards_alpha = state.cards_artifact.get("count_dispersion_alpha", 0.0)
            prob_c35 = count_tail_probability(exp_cards, cards_alpha, 3) * 100
            prob_c45 = count_tail_probability(exp_cards, cards_alpha, 4) * 100
            prob_c55 = count_tail_probability(exp_cards, cards_alpha, 5) * 100
        except Exception as e:
            logger.warning("Error predicting cards: %s", e)

    h_c_for = float(simulated_df.get("home_cards_for_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    a_c_for = float(simulated_df.get("away_cards_for_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    h_c_against = float(simulated_df.get("home_cards_against_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    a_c_against = float(simulated_df.get("away_cards_against_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    home_exp_cards = 0.5 * (h_c_for + a_c_against)
    away_exp_cards = 0.5 * (a_c_for + h_c_against)
    total_exp_cards = home_exp_cards + away_exp_cards
    if total_exp_cards > 0:
        home_cards_share = max(0.20, min(0.80, home_exp_cards / total_exp_cards))

    raw_ref = simulated_df.get("referee_name", pd.Series([None])).iloc[0]
    ref_name = str(raw_ref) if pd.notnull(raw_ref) and raw_ref else "Premier League Hakem Heyeti"
    ref_avg_c = float(simulated_df.get("referee_avg_cards", pd.Series([4.15])).iloc[0] or 4.15)
    ref_avg_f = float(simulated_df.get("referee_avg_fouls", pd.Series([21.5])).iloc[0] or 21.5)
    regression_skills = {
        "corners": _regression_model_skill(state.corner_artifact),
        "throws": _regression_model_skill(state.throws_artifact),
        "saves": _regression_model_skill(state.saves_artifact),
        "offsides": _regression_model_skill(state.offside_artifact),
        "cards": _regression_model_skill(state.cards_artifact),
    }

    # Dynamic splits blending team production (FOR) and opponent volume conceded (AGAINST)
    h_crn_for = float(simulated_df.get("home_corners_for_roll_5", pd.Series([5.2])).iloc[0] or 5.2)
    a_crn_for = float(simulated_df.get("away_corners_for_roll_5", pd.Series([4.8])).iloc[0] or 4.8)
    h_crn_against = float(simulated_df.get("home_corners_against_roll_5", pd.Series([4.8])).iloc[0] or 4.8)
    a_crn_against = float(simulated_df.get("away_corners_against_roll_5", pd.Series([5.2])).iloc[0] or 5.2)
    home_exp_crn = 0.5 * (h_crn_for + a_crn_against)
    away_exp_crn = 0.5 * (a_crn_for + h_crn_against)
    total_exp_crn = home_exp_crn + away_exp_crn
    home_c_share = max(0.20, min(0.80, home_exp_crn / total_exp_crn)) if total_exp_crn > 0 else 0.55

    h_th_for_5 = float(simulated_df.get("home_throws_roll_5", pd.Series([18.0])).iloc[0] or 18.0)
    a_th_for_5 = float(simulated_df.get("away_throws_roll_5", pd.Series([17.0])).iloc[0] or 17.0)
    h_th_opp_5 = float(simulated_df.get("home_opponent_throws_roll_5", pd.Series([17.0])).iloc[0] or 17.0)
    a_th_opp_5 = float(simulated_df.get("away_opponent_throws_roll_5", pd.Series([18.0])).iloc[0] or 18.0)
    h_th_for_10 = float(simulated_df.get("home_throws_roll_10", pd.Series([h_th_for_5])).iloc[0] or h_th_for_5)
    a_th_for_10 = float(simulated_df.get("away_throws_roll_10", pd.Series([a_th_for_5])).iloc[0] or a_th_for_5)
    h_th_opp_10 = float(simulated_df.get("home_opponent_throws_roll_10", pd.Series([h_th_opp_5])).iloc[0] or h_th_opp_5)
    a_th_opp_10 = float(simulated_df.get("away_opponent_throws_roll_10", pd.Series([a_th_opp_5])).iloc[0] or a_th_opp_5)
    home_exp_th = 0.25 * (h_th_for_5 + a_th_opp_5) + 0.25 * (h_th_for_10 + a_th_opp_10)
    away_exp_th = 0.25 * (a_th_for_5 + h_th_opp_5) + 0.25 * (a_th_for_10 + h_th_opp_10)
    total_exp_th = home_exp_th + away_exp_th
    home_t_share = max(0.25, min(0.75, home_exp_th / total_exp_th)) if total_exp_th > 0 else 0.51

    h_sv = float(simulated_df.get("home_saves_roll_5", pd.Series([2.8])).iloc[0] or 2.8)
    a_sv = float(simulated_df.get("away_saves_roll_5", pd.Series([2.9])).iloc[0] or 2.9)
    h_sot_for = float(simulated_df.get("home_shots_ontarget_for_roll_5", pd.Series([4.5])).iloc[0] or 4.5)
    a_sot_for = float(simulated_df.get("away_shots_ontarget_for_roll_5", pd.Series([4.0])).iloc[0] or 4.0)
    home_exp_sv = 0.5 * (h_sv + a_sot_for * 0.70)
    away_exp_sv = 0.5 * (a_sv + h_sot_for * 0.70)
    total_exp_sv = home_exp_sv + away_exp_sv
    home_s_share = max(0.20, min(0.80, home_exp_sv / total_exp_sv)) if total_exp_sv > 0 else 0.48

    # 7. Dynamic Starting XI & Form Modulators
    target_mid = match_id or target_match_id
    lineup_analysis = None
    try:
        lineup_analysis = analyze_match_starting_xis(
            home_id=home_id,
            away_id=away_id,
            match_id=target_mid,
            referee_avg_cards=ref_avg_c,
        )
    except Exception as e:
        logger.warning(f"Error computing lineup analysis in predict_match: {e}")

    return {
        "home_team": home_meta,
        "away_team": away_meta,
        "favorite_label": fav_label,
        "outcome": {
            "home_win_pct": round(prob_h, 1),
            "draw_pct": round(prob_d, 1),
            "away_win_pct": round(prob_a, 1),
            **({
                "ensemble_probabilities_pct": [
                    round(float(prob_h), 1), round(float(prob_d), 1), round(float(prob_a), 1)
                ]
            } if has_ensemble else {}),
            "over_2_5_goals_pct": round(prob_o25, 1),
            "over_2_5_source": over_source,
        },
        "goals": goals_extra,
        "corners": {
            "model_skill": regression_skills["corners"],
            "expected_total": round(exp_corners, 1),
            "expected_home": round(exp_corners * home_c_share, 1),
            "expected_away": round(exp_corners * (1 - home_c_share), 1),
            "prob_over_8_5_pct": round(prob_c85, 1),
            "prob_over_9_5_pct": round(prob_c95, 1),
            "prob_over_10_5_pct": round(prob_c105, 1),
        },
        "cards": {
            "model_skill": regression_skills["cards"],
            "expected_total": round(exp_cards, 1),
            "expected_home": round(exp_cards * home_cards_share, 1),
            "expected_away": round(exp_cards * (1 - home_cards_share), 1),
            "prob_over_3_5_pct": round(prob_c35, 1),
            "prob_over_4_5_pct": round(prob_c45, 1),
            "prob_over_5_5_pct": round(prob_c55, 1),
        },
        "referee": {
            "name": ref_name,
            "avg_cards": round(ref_avg_c, 1),
            "avg_fouls": round(ref_avg_f, 1),
        },
        "throws": {
            "model_skill": regression_skills["throws"],
            "expected_total": round(exp_throws, 1),
            "expected_home": round(exp_throws * home_t_share, 1),
            "expected_away": round(exp_throws * (1 - home_t_share), 1),
            "prob_over_33_5_pct": round(prob_t335, 1),
            "prob_over_34_5_pct": round(prob_t345, 1),
            "prob_over_36_5_pct": round(prob_t365, 1),
        },
        "saves": {
            "model_skill": regression_skills["saves"],
            "expected_total": round(exp_saves, 1),
            "expected_home": round(exp_saves * home_s_share, 1),
            "expected_away": round(exp_saves * (1 - home_s_share), 1),
        },
        "shots": {
            "expected_total": round(exp_saves * 4.1, 1),
        },
        "offsides": {
            "model_skill": regression_skills["offsides"],
            "expected_total": round(exp_offsides, 1),
            "expected_home": round(exp_offsides * home_off_share, 1),
            "expected_away": round(exp_offsides * (1 - home_off_share), 1),
            "prob_over_2_5_pct": round(prob_off25, 1),
            "prob_over_3_5_pct": round(prob_off35, 1),
            "prob_over_4_5_pct": round(prob_off45, 1),
        },
        "lineup_analysis": lineup_analysis,
    }


@router.get("/api/benchmarks")
def get_benchmarks():
    """Returns saved model benchmark metrics and summary."""
    benchmarks_path = BASE_DIR / "docs" / "reports" / "model_benchmarks.md"
    content = ""
    if benchmarks_path.exists():
        with open(benchmarks_path, "r", encoding="utf-8") as f:
            content = f.read()

    return {
        "corner": state.corner_artifact["metrics"] if state.corner_artifact else {},
        "throws": state.throws_artifact["metrics"] if state.throws_artifact else {},
        "saves": state.saves_artifact["metrics"] if state.saves_artifact else {},
        "outcome": state.outcome_artifact["metrics"] if state.outcome_artifact else {},
        "offside": state.offside_artifact["metrics"] if state.offside_artifact else {},
        "markdown_report": content,
    }
