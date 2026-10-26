#!/usr/bin/env python3
"""Outer-season evaluation of the goal-market models of a TheStatsAPI league (LaLiga).

Usage: python3 -m src.models.evaluate_league_goal_models --competition la_liga

Candidates, each fitted on earlier seasons only and scored on every outer season (2024/25, 2025/26; the locked season is reported,
never used in the decision):
* ``current``: the production model, two Poisson rate models on the 118 league features (``train_league_model.fit_goals``);
* ``pl_feature_model``: the Premier League's goal model (``train_goals.select_blend_config`` picks the feature set and penalty on
  forward folds of the training seasons, ``FeatureGoalModel`` fits it) on the Premier League feature definitions;
* ``dixon_coles``: team attack and defence strengths with a 365-day half-life, no features.
Every candidate's score matrix is aligned to the production model's calibrated 1X2 probabilities of the same walk-forward fold, as in serving, and gives the over 1.5 / 2.5 / 3.5 and both-teams-to-score probabilities; each market is compared with
the training base rate by the paired bootstrap (10,000 draws, seed 42) and the whole family (candidates x markets) is
Benjamini-Hochberg adjusted.

Decision rule, written before the run: a market is served from a model only if some candidate beats the training base rate on it
(negative paired difference with q < 0.05); the candidate with the lowest mean log-loss among those wins. Otherwise the market
stays on the base rate and is labelled ``baseline``. No candidate is chosen on the locked season.

Reads: data/football.db. Writes: docs/reports/models/<key>_goal_model_eval.json (no artifact).
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, configure_logging
from src.db.database import get_db
from src.features.build_league_features import build_league_features, feature_columns, load_league_matches, load_player_lines
from src.features.build_league_pl_features import build_parity_features
from src.models.dixon_coles import DixonColesModel, align_to_outcome_probs, btts_prob, expected_goals, matrix_from_lambdas, over_prob
from src.models.eval_utils import apply_fdr, with_inference
from src.models.train_goals import blend_model, goal_feature_sets, select_blend_config
from src.models.train_league_model import GOAL_MARKETS, OUTER_SEASONS, RHO, binary_log_loss, fit_goals, walk_forward

logger = logging.getLogger("evaluate_league_goal_models")
CANDIDATES = ("current", "pl_feature_model", "dixon_coles")
LINES = {"over_15": 1.5, "over_25": 2.5, "over_35": 3.5}
SCORE_CAP = 12


def played_before(table: pd.DataFrame, season: str) -> pd.DataFrame:
    played = table[table["home_score"].notna()]
    return played[(played["season"] < season) & ~played["season"].isin(LOCKED_SEASONS)].reset_index(drop=True)


def candidate_matrices(base_train: pd.DataFrame, base_test: pd.DataFrame, columns: List[str], pl_train: pd.DataFrame, pl_test: pd.DataFrame) -> Dict[str, np.ndarray]:
    home, away, _ = fit_goals(base_train, columns)
    lam_home, lam_away = np.clip(home.predict(base_test[columns]), 0.15, 5.5), np.clip(away.predict(base_test[columns]), 0.15, 5.5)
    sets = {k: [c for c in v if pl_train[c].nunique() > 1] for k, v in goal_feature_sets(list(pl_train.columns)).items()}
    chosen = select_blend_config(pl_train, sets)
    logger.info("PL goal model: %s", chosen)
    feature = blend_model(sets[chosen["feature_set"]], chosen).fit(pl_train)
    dixon_coles = DixonColesModel(half_life_days=365.0).fit(pl_train)
    if not dixon_coles.fit_ok_:
        raise RuntimeError("Dixon-Coles did not converge")
    return {"current": matrix_from_lambdas(lam_home, lam_away, rho=RHO, max_goals=SCORE_CAP), "pl_feature_model": feature.predict_matrices(pl_test),
            "dixon_coles": dixon_coles.predict_matrices(pl_test)}


def season_rows(name: str, matrices: np.ndarray, test: pd.DataFrame, train: pd.DataFrame, season: str, outcome: np.ndarray) -> pd.DataFrame:
    matrices = align_to_outcome_probs(matrices, outcome)
    goals_h, goals_a = test["home_score"].to_numpy(dtype=int), test["away_score"].to_numpy(dtype=int)
    cells = np.arange(len(test))
    total = goals_h + goals_a
    lam_h, lam_a = expected_goals(matrices)
    out = pd.DataFrame({"candidate": name, "season": season, "match_id": test["match_id"].to_numpy(),
                        "score_nll": -np.log(np.clip(matrices[cells, np.minimum(goals_h, SCORE_CAP), np.minimum(goals_a, SCORE_CAP)], 1e-12, None)),
                        "mae_total": np.abs(lam_h + lam_a - total)})
    train_total = (train["home_score"] + train["away_score"]).to_numpy()
    rates = {m: float((train_total > line).mean()) for m, line in LINES.items()}
    rates["btts"] = float(((train["home_score"] > 0) & (train["away_score"] > 0)).mean())
    actual = {m: (total > line).astype(int) for m, line in LINES.items()}
    actual["btts"] = ((goals_h > 0) & (goals_a > 0)).astype(int)
    for market in GOAL_MARKETS:
        p = btts_prob(matrices) if market == "btts" else over_prob(matrices, LINES[market])
        out[f"{market}_model"] = binary_log_loss(np.asarray(p), actual[market])
        out[f"{market}_base"] = binary_log_loss(np.full(len(test), rates[market]), actual[market])
    out["mae_base"] = np.abs(float(train_total.mean()) - total)
    return out


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    conn = get_db()
    try:
        matches, lines = load_league_matches(conn, comp.id), load_player_lines(conn, comp.id)
    finally:
        conn.close()
    base = build_league_features(matches)
    columns = [c for c in feature_columns(base) if base[c].notna().any()]
    parity = build_parity_features(matches, lines)
    walk = walk_forward(base, columns, {})["rows"]["model"].set_index("match_id")  # calibrated 1X2 of the production model, fold by fold
    seasons = sorted(base.loc[base["home_score"].notna(), "season"].unique())
    folds = [s for s in (*OUTER_SEASONS, *[s for s in seasons if s in LOCKED_SEASONS]) if s in seasons]
    frames: List[pd.DataFrame] = []
    for season in folds:
        base_train, pl_train = played_before(base, season), played_before(parity, season)
        base_test = base[(base["season"] == season) & base["home_score"].notna()].reset_index(drop=True)
        pl_test = parity.set_index("match_id").loc[base_test["match_id"]].reset_index()
        for name, matrices in candidate_matrices(base_train, base_test, columns, pl_train, pl_test).items():
            frames.append(season_rows(name, matrices, base_test, base_train, season, walk.loc[base_test["match_id"], ["p_home", "p_draw", "p_away"]].to_numpy()))
        logger.info("%s done (%d training matches)", season, len(base_train))
    table = pd.concat(frames, ignore_index=True)
    outer = table[table["season"].isin(OUTER_SEASONS)]
    tests: Dict[str, Dict[str, Any]] = {}
    summary: Dict[str, Any] = {}
    for name in CANDIDATES:
        part = outer[outer["candidate"] == name]
        summary[name] = {"score_nll": {s: float(table[(table["candidate"] == name) & (table["season"] == s)]["score_nll"].mean()) for s in folds}}
        for market in GOAL_MARKETS:
            summary[name][market] = {s: {"model": float(g[f"{market}_model"].mean()), "base_rate": float(g[f"{market}_base"].mean())}
                                     for s, g in table[table["candidate"] == name].groupby("season")}
            tests[f"{name}:{market}"] = with_inference(part[f"{market}_model"].to_numpy(), part[f"{market}_base"].to_numpy())
        tests[f"{name}:total_goals_mae"] = with_inference(part["mae_total"].to_numpy(), part["mae_base"].to_numpy())
    apply_fdr(tests)
    decision: Dict[str, Any] = {}
    for market in GOAL_MARKETS:
        passing = [n for n in CANDIDATES if tests[f"{n}:{market}"]["mean_delta"] < 0 and tests[f"{n}:{market}"]["significant_fdr_05"]]
        pooled = {n: float(outer[outer["candidate"] == n][f"{market}_model"].mean()) for n in CANDIDATES}
        decision[market] = {"serving": min(passing, key=pooled.get) if passing else "baseline", "passing_candidates": passing, "pooled_log_loss": pooled}
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key,
              "protocol": {"outer_seasons": list(OUTER_SEASONS), "locked_monitoring": [s for s in folds if s not in OUTER_SEASONS], "bootstrap_draws": 10000, "seed": 42,
                           "candidates": list(CANDIDATES), "family_size": len(tests)},
              "per_season": summary, "vs_training_base_rate": tests, "decision": decision}
    out = REPORTS_DIR / "models" / f"{comp.key}_goal_model_eval.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    logger.info("Report: %s", out)
    print(json.dumps({"decision": {m: d["serving"] for m, d in decision.items()},
                      "tests": {k: {x: round(v[x], 4) for x in ("mean_delta", "ci_low", "ci_high", "q_fdr")} for k, v in tests.items()}}, indent=2))


if __name__ == "__main__":
    main()
