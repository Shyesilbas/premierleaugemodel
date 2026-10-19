"""Compare score-matrix goal models on forward-only season holdouts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.models.dixon_coles import (
    DixonColesModel,
    btts_prob,
    matrix_from_lambdas,
    outcome_probs,
    over_prob,
)
from src.models.eval_utils import paired_bootstrap_delta, per_match_log_loss
from src.models.goals_model import FeatureGoalModel
from src.models.model_utils import apply_probability_calibrator
from src.models.train_goals import BLEND_GRID, SCORE_CAP, blend_model, goal_feature_sets, select_blend_config
from src.models.train_match_outcome import (
    LOCKED_SEASONS,
    candidate_models,
    chronological_oof_predictions,
    feature_set,
    fit_model,
    fit_probability_calibrator,
    ordered_probabilities,
    select_model,
)


OU_LINES = (1.5, 2.5, 3.5)
FEATURE_ALPHAS = (3.0, 10.0, 30.0, 100.0, 300.0)


def _binary_probs(event_probability: np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(event_probability, dtype=float), 1e-6, 1 - 1e-6)
    return np.column_stack([1 - probability, probability])


def _market_probabilities(match_ids: pd.Series, db_path: str = "data/premier_league.db") -> pd.DataFrame:
    """Vig-free Bet365 last-seen O2.5 / BTTS probabilities per match (NaN when absent).

    Benchmark only: never a model input and never part of a pass/fail decision.
    """
    with sqlite3.connect(db_path) as conn:
        odds = pd.read_sql_query(
            "SELECT match_id, over_25_last_seen AS o, under_25_last_seen AS u, "
            "btts_yes_last_seen AS yes, btts_no_last_seen AS no "
            "FROM external_match_odds WHERE bookmaker = 'Bet365'",
            conn,
            index_col="match_id",
        )
    odds = odds.reindex(match_ids)
    return pd.DataFrame({
        "o25": (1 / odds["o"]) / (1 / odds["o"] + 1 / odds["u"]),
        "btts": (1 / odds["yes"]) / (1 / odds["yes"] + 1 / odds["no"]),
    }).reset_index(drop=True)


def _score_row(
    season: str,
    target: str,
    model_name: str,
    probabilities: np.ndarray,
    y: np.ndarray,
    prior_probabilities: np.ndarray,
) -> dict[str, Any]:
    loss = per_match_log_loss(probabilities, y)
    prior_loss = per_match_log_loss(prior_probabilities, y)
    if model_name == "prior":
        delta = {"mean_delta": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    else:
        delta = paired_bootstrap_delta(loss, prior_loss, n_boot=2000)
    return {
        "season": season,
        "target": target,
        "model": model_name,
        "log_loss": float(loss.mean()),
        "n": int(len(y)),
        "delta_vs_prior": float(delta["mean_delta"]),
        "ci_low": float(delta["ci_low"]),
        "ci_high": float(delta["ci_high"]),
    }


def _pooled_reliability(probabilities: np.ndarray, actual: np.ndarray) -> dict[str, Any]:
    """Summarize calibration across all outer seasons using quantile bins."""
    p = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    y = np.asarray(actual, dtype=int)
    if len(p) != len(y) or len(p) == 0:
        raise ValueError("Reliability inputs must be non-empty and aligned")

    edges = np.unique(np.quantile(p, np.linspace(0.0, 1.0, 11)))
    if len(edges) < 2:
        bin_ids = np.zeros(len(p), dtype=int)
    else:
        bin_ids = np.searchsorted(edges[1:-1], p, side="right")

    rows = []
    for bin_id in np.unique(bin_ids):
        mask = bin_ids == bin_id
        rows.append({
            "bin": int(bin_id) + 1,
            "n": int(mask.sum()),
            "mean_predicted": float(p[mask].mean()),
            "observed_rate": float(y[mask].mean()),
        })
    total = len(p)
    ece = sum(row["n"] * abs(row["mean_predicted"] - row["observed_rate"]) for row in rows) / total
    observed = np.asarray([row["observed_rate"] for row in rows], dtype=float)
    monotonic_share = float(np.mean(np.diff(observed) >= 0.0)) if len(observed) > 1 else 1.0
    return {
        "n": total,
        "ece": float(ece),
        "monotonic_adjacent_share": monotonic_share,
        "bins": rows,
    }


def _goal_matrices(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    matrices: dict[str, np.ndarray] = {}
    dc_variants = {"dc": None, "dc_hl365": 365.0, "dc_hl730": 730.0}
    dc_models = {
        name: DixonColesModel(half_life_days=half_life).fit(train)
        for name, half_life in dc_variants.items()
    }
    for name, model in dc_models.items():
        matrices[name] = model.predict_matrices(test)

    # League-average benchmark: every match gets the training-mean goals, no team signal.
    matrices["null"] = matrix_from_lambdas(
        np.full(len(test), train["home_score"].mean()),
        np.full(len(test), train["away_score"].mean()),
        0.0,
    )

    for alpha in FEATURE_ALPHAS:
        model = FeatureGoalModel(features, alpha=alpha).fit(train)
        matrices[f"feat_alpha{alpha:g}"] = model.predict_matrices(test)

    # Nested: choose the blend on forward folds of the training seasons only,
    # exactly as production training does on all unlocked seasons.
    feature_sets = goal_feature_sets(list(train.columns))
    chosen = select_blend_config(train, feature_sets)
    matrices[BLEND_GRID["kind"]] = (
        blend_model(feature_sets[chosen["feature_set"]], chosen).fit(train).predict_matrices(test)
    )
    return matrices, chosen


def _logreg_o25_probabilities(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> np.ndarray:
    """Fit and calibrate the existing O25 classifier using prior seasons only."""
    train_y = ((train["home_score"] + train["away_score"]) > 2.5).astype(int)
    labels = [0, 1]
    train_kickoffs = train["kickoff_millis"] if "kickoff_millis" in train else None
    selected, _ = select_model("o25", train[features], train_y, labels, train_kickoffs)
    model = candidate_models()[selected]
    oof_probabilities, oof_targets = chronological_oof_predictions(
        model,
        train[features],
        train_y,
        labels,
        kickoff_times=train_kickoffs,
    )
    calibrator = fit_probability_calibrator(oof_probabilities, pd.Series(oof_targets), labels)
    fitted = fit_model(model, train[features], train_y)
    raw = ordered_probabilities(fitted, test[features], labels)
    calibrated = apply_probability_calibrator(raw, calibrator)
    return calibrated[:, 1]


def evaluate_outer_seasons(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return outer-season scores, pooled reliability, and O2.5 gate summaries."""
    required = {
        "season", "home_score", "away_score", "home_id", "away_id",
        "kickoff_millis", "match_id",
    }
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Goal evaluation data missing columns: {sorted(missing)}")
    if df[["home_score", "away_score"]].isna().any().any():
        raise ValueError("Goal evaluation expects played matches only")

    ordered = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)
    features = feature_set("o25", list(ordered.columns))
    seasons = list(pd.unique(ordered["season"].astype(str)))
    results: list[dict[str, Any]] = []
    pooled_o25_predictions: dict[str, list[np.ndarray]] = {}
    pooled_o25_actuals: list[np.ndarray] = []
    pooled_o25_losses: dict[str, list[np.ndarray]] = {}
    pooled_o25_prior_losses: list[np.ndarray] = []
    selected_configs: dict[str, dict[str, Any]] = {}
    pooled_btts_losses: dict[str, list[np.ndarray]] = {}
    pooled_btts_actuals: list[np.ndarray] = []
    pooled_score_nll: dict[str, list[np.ndarray]] = {}
    pooled_market: dict[str, list[np.ndarray]] = {"o25": [], "btts": []}

    for season_index, season in enumerate(seasons):
        if season_index == 0:
            continue
        test_mask = ordered["season"].astype(str).eq(season)
        train_mask = ordered["season"].astype(str).isin(seasons[:season_index])
        train, test = ordered.loc[train_mask], ordered.loc[test_mask]
        if len(train) < 300 or test.empty:
            continue

        matrices, selected_configs[season] = _goal_matrices(train, test, features)
        total_goals = (test["home_score"] + test["away_score"]).to_numpy(dtype=float)
        home_cell = np.minimum(test["home_score"].to_numpy(dtype=int), SCORE_CAP)
        away_cell = np.minimum(test["away_score"].to_numpy(dtype=int), SCORE_CAP)
        for model_name, matrix in matrices.items():
            pooled_score_nll.setdefault(model_name, []).append(
                -np.log(matrix[np.arange(len(test)), home_cell, away_cell])
            )

        for line in OU_LINES:
            target = f"over_{line:g}"
            y = (total_goals > line).astype(int)
            prior_rate = float(((train["home_score"] + train["away_score"]) > line).mean())
            prior_probabilities = _binary_probs(np.full(len(y), prior_rate))
            results.append(_score_row(season, target, "prior", prior_probabilities, y, prior_probabilities))
            if line == 2.5:
                pooled_o25_actuals.append(y)
                pooled_o25_prior_losses.append(per_match_log_loss(prior_probabilities, y))
            for model_name, matrix in matrices.items():
                event_probability = over_prob(matrix, line)
                probabilities = _binary_probs(event_probability)
                results.append(_score_row(season, target, model_name, probabilities, y, prior_probabilities))
                if line == 2.5:
                    pooled_o25_predictions.setdefault(model_name, []).append(event_probability)
                    pooled_o25_losses.setdefault(model_name, []).append(
                        per_match_log_loss(probabilities, y)
                    )
            if line == 2.5:
                p_logreg = _logreg_o25_probabilities(train, test, features)
                pooled_o25_predictions.setdefault("logreg_o25", []).append(p_logreg)
                pooled_o25_losses.setdefault("logreg_o25", []).append(
                    per_match_log_loss(_binary_probs(p_logreg), y)
                )
                results.append(_score_row(
                    season,
                    target,
                    "logreg_o25",
                    _binary_probs(p_logreg),
                    y,
                    prior_probabilities,
                ))

        y_btts = (
            (test["home_score"] >= 1) & (test["away_score"] >= 1)
        ).to_numpy(dtype=int)
        pooled_btts_actuals.append(y_btts)
        prior_btts = float(
            ((train["home_score"] >= 1) & (train["away_score"] >= 1)).mean()
        )
        prior_btts_probabilities = _binary_probs(np.full(len(y_btts), prior_btts))
        results.append(_score_row(
            season, "btts", "prior", prior_btts_probabilities, y_btts, prior_btts_probabilities
        ))
        for model_name, matrix in matrices.items():
            btts_probabilities = _binary_probs(btts_prob(matrix))
            pooled_btts_losses.setdefault(model_name, []).append(per_match_log_loss(btts_probabilities, y_btts))
            results.append(_score_row(
                season,
                "btts",
                model_name,
                btts_probabilities,
                y_btts,
                prior_btts_probabilities,
            ))
        market = _market_probabilities(test["match_id"])
        pooled_market["o25"].append(market["o25"].to_numpy())
        pooled_market["btts"].append(market["btts"].to_numpy())

        y_1x2 = np.select(
            [test["home_score"] > test["away_score"], test["home_score"] == test["away_score"]],
            [0, 1],
            default=2,
        )
        train_1x2 = np.select(
            [train["home_score"] > train["away_score"], train["home_score"] == train["away_score"]],
            [0, 1],
            default=2,
        )
        prior_1x2 = pd.Series(train_1x2).value_counts(normalize=True).reindex([0, 1, 2], fill_value=0).to_numpy()
        prior_1x2_probabilities = np.tile(prior_1x2, (len(y_1x2), 1))
        results.append(_score_row(
            season, "1x2", "prior", prior_1x2_probabilities, y_1x2, prior_1x2_probabilities
        ))
        for model_name, matrix in matrices.items():
            results.append(_score_row(
                season,
                "1x2",
                model_name,
                outcome_probs(matrix),
                y_1x2,
                prior_1x2_probabilities,
            ))
    actual = np.concatenate(pooled_o25_actuals) if pooled_o25_actuals else np.asarray([], dtype=int)
    reliability = {
        name: _pooled_reliability(np.concatenate(probabilities), actual)
        for name, probabilities in pooled_o25_predictions.items()
    }
    result_frame = pd.DataFrame(
        [row for row in results if row["target"] == "over_2.5" and row["model"] != "prior"]
    )
    logreg_mean = float(result_frame.loc[result_frame["model"] == "logreg_o25", "log_loss"].mean())
    candidate_gates = {}
    matrix_names = sorted(set(result_frame["model"]) - {"logreg_o25", "null"})
    null_o25 = np.concatenate(pooled_o25_losses["null"])
    for model_name in matrix_names:
        model_rows = result_frame[result_frame["model"] == model_name]
        rel = reliability[model_name]
        mean_delta = float(model_rows["delta_vs_prior"].mean())
        negative_seasons = int((model_rows["delta_vs_prior"] < 0).sum())
        better_than_logreg = float(model_rows["log_loss"].mean()) < logreg_mean
        vs_null = paired_bootstrap_delta(np.concatenate(pooled_o25_losses[model_name]), null_o25, n_boot=2000)
        score_nll = np.concatenate(pooled_score_nll[model_name])
        candidate_gates[model_name] = {
            # Exact-score NLL is the blend-selection criterion (Ç1); reported so changes are comparable.
            "mean_score_nll": float(score_nll.mean()),
            "score_nll_vs_null": paired_bootstrap_delta(
                score_nll, np.concatenate(pooled_score_nll["null"]), n_boot=2000
            ),
            "pooled_paired_bootstrap_vs_null": vs_null,
            "mean_delta_vs_prior": mean_delta,
            "negative_seasons": negative_seasons,
            "mean_log_loss": float(model_rows["log_loss"].mean()),
            "mean_logreg_o25_log_loss": logreg_mean,
            "better_than_logreg_o25": better_than_logreg,
            "reliability_ece": rel["ece"],
            "reliability_monotonic_adjacent_share": rel["monotonic_adjacent_share"],
            "reliability_endpoints_rising": (
                rel["bins"][-1]["observed_rate"] > rel["bins"][0]["observed_rate"]
            ),
            "pooled_paired_bootstrap": paired_bootstrap_delta(
                np.concatenate(pooled_o25_losses[model_name]),
                np.concatenate(pooled_o25_prior_losses),
                n_boot=2000,
            ),
            "passed": bool(
                mean_delta < -0.003
                and negative_seasons >= 2
                and better_than_logreg
                and vs_null["mean_delta"] < 0  # must beat a constant league-average Poisson, not just the prior
                and rel["bins"][-1]["observed_rate"] > rel["bins"][0]["observed_rate"]
            ),
        }
    for gate in candidate_gates.values():
        # Reported, not enforced: the pass rule above has no significance requirement.
        gate["ci_excludes_zero"] = bool(gate["pooled_paired_bootstrap"]["ci_high"] < 0)
        gate["ci_vs_null_excludes_zero"] = bool(gate["pooled_paired_bootstrap_vs_null"]["ci_high"] < 0)
    if BLEND_GRID["kind"] in candidate_gates:
        candidate_gates[BLEND_GRID["kind"]]["selection_grid"] = BLEND_GRID
        candidate_gates[BLEND_GRID["kind"]]["selected_configs"] = selected_configs
        kind = BLEND_GRID["kind"]
        o25_blend, o25_null = np.concatenate(pooled_o25_losses[kind]), null_o25
        btts_blend, btts_null = np.concatenate(pooled_btts_losses[kind]), np.concatenate(pooled_btts_losses["null"])
        # BTTS has its own gate: a market that cannot beat the league average is shown as such.
        btts_vs_null = paired_bootstrap_delta(btts_blend, btts_null, n_boot=2000)
        candidate_gates[kind]["btts_gate"] = {
            "mean_log_loss": float(btts_blend.mean()),
            "pooled_paired_bootstrap_vs_null": btts_vs_null,
            # Significance required: a label on a gain the CI cannot tell from zero is not information.
            "passed": bool(btts_vs_null["ci_high"] < 0),
            "ci_excludes_zero": bool(btts_vs_null["ci_high"] < 0),
        }
        # Report-only market benchmark on matches that have Bet365 odds.
        market_report = {}
        for name, blend_loss in (("o25", o25_blend), ("btts", btts_blend)):
            p_market = np.concatenate(pooled_market[name])
            has_odds = ~np.isnan(p_market)
            market_loss = per_match_log_loss(_binary_probs(p_market[has_odds]), (
                np.concatenate(pooled_o25_actuals) if name == "o25" else np.concatenate(pooled_btts_actuals)
            )[has_odds])
            market_report[name] = {
                "n": int(has_odds.sum()),
                "model_log_loss": float(blend_loss[has_odds].mean()),
                "market_log_loss": float(market_loss.mean()),
                "model_minus_market": paired_bootstrap_delta(blend_loss[has_odds], market_loss, n_boot=2000),
            }
        candidate_gates[kind]["market_comparison"] = market_report
    return results, reliability, candidate_gates


def evaluate_in_season_refit(
    df: pd.DataFrame,
    selected_configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score the season-start blend config refitted before every gameweek, like weekly retraining.

    The config stays the one chosen on earlier seasons; only parameters see the
    season's already-played matches. The fair baseline is a prior refreshed the same way.
    """
    ordered = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)
    feature_sets = goal_feature_sets(list(ordered.columns))
    seasons = list(pd.unique(ordered["season"].astype(str)))
    losses: dict[str, list[np.ndarray]] = {"refit": [], "frozen": [], "rolling_prior": []}
    by_season: dict[str, dict[str, float]] = {}
    for season, chosen in selected_configs.items():
        features = feature_sets[chosen["feature_set"]]
        before = ordered[ordered["season"].astype(str).isin(seasons[:seasons.index(season)])]
        current = ordered[ordered["season"].astype(str).eq(season)]
        frozen = blend_model(features, chosen).fit(before)
        season_losses: dict[str, list[np.ndarray]] = {key: [] for key in losses}
        blocks = sorted(current.groupby("gameweek", dropna=False), key=lambda item: item[1]["kickoff_millis"].min())
        for _, block in blocks:
            train = pd.concat([before, current[current["kickoff_millis"] < block["kickoff_millis"].min()]])
            y = ((block["home_score"] + block["away_score"]) > 2.5).to_numpy(dtype=int)
            prior_rate = float(((train["home_score"] + train["away_score"]) > 2.5).mean())
            refit = blend_model(features, chosen).fit(train)
            season_losses["refit"].append(per_match_log_loss(_binary_probs(over_prob(refit.predict_matrices(block), 2.5)), y))
            season_losses["frozen"].append(per_match_log_loss(_binary_probs(over_prob(frozen.predict_matrices(block), 2.5)), y))
            season_losses["rolling_prior"].append(per_match_log_loss(_binary_probs(np.full(len(y), prior_rate)), y))
        by_season[season] = {key: float(np.concatenate(parts).mean()) for key, parts in season_losses.items()}
        for key, parts in season_losses.items():
            losses[key].extend(parts)
    pooled = {key: np.concatenate(parts) for key, parts in losses.items()}
    return {
        "n": int(len(pooled["refit"])),
        "log_loss": {key: float(values.mean()) for key, values in pooled.items()},
        "refit_vs_frozen": paired_bootstrap_delta(pooled["refit"], pooled["frozen"], n_boot=2000),
        "refit_vs_rolling_prior": paired_bootstrap_delta(pooled["refit"], pooled["rolling_prior"], n_boot=2000),
        "by_season": by_season,
    }


def main(
    data_path: str = "data/processed/features_matches_all.parquet",
    output_path: str = "data/processed/goal_model_outer_eval.json",
) -> list[dict[str, Any]]:
    df = pd.read_parquet(data_path)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    if LOCKED_SEASONS:
        df = df[~df["season"].astype(str).isin(LOCKED_SEASONS)].copy()
    results, reliability, candidate_gates = evaluate_outer_seasons(df)
    in_season_refit = evaluate_in_season_refit(df, candidate_gates[BLEND_GRID["kind"]]["selected_configs"])

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "outer_season_results": results,
        "pooled_o25_reliability": reliability,
        "o25_candidate_gates": candidate_gates,
        "o25_in_season_refit": in_season_refit,
    }, indent=2), encoding="utf-8")

    table = pd.DataFrame(results).pivot_table(
        index=["target", "model"],
        columns="season",
        values="delta_vs_prior",
    )
    table["mean_delta"] = table.mean(axis=1)
    print(table.round(4).sort_values(["target", "mean_delta"]).to_string())
    print("\nO2.5 candidate gates:")
    print(pd.DataFrame(candidate_gates).T.round(4).to_string())
    print("\nO2.5 weekly in-season refit:", json.dumps(in_season_refit, indent=2))
    return results


if __name__ == "__main__":
    main()
