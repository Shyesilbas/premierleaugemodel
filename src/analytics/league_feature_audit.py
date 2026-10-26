#!/usr/bin/env python3
"""Permutation importance of the LaLiga models by feature family, out of sample.

Usage: python3 -m src.analytics.league_feature_audit --competition la_liga

Regression coefficients are not read as importance (collinear features can have large coefficients and no effect on the loss).
For every outer season the 1X2 model is fitted on earlier seasons only (exactly as in ``train_league_model.walk_forward``), the
family's columns are shuffled together (one permutation of the rows shared by all the family's columns, so their internal
correlation survives) in that season's matches, and the increase in log-loss is the importance (reported for the calibrated probabilities and, separately, for the raw model output before the calibrator). For the count models (throws,
offsides) the selected model is refitted on the first 80% of the matches and the family is shuffled in the last 20%. 30 repeats,
seed 42; a family is called informative only if its mean increase exceeds twice the spread over the repeats.

Reads: data/football.db and the production artifacts' selected model names. Writes: docs/reports/models/<key>_feature_audit.json.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_squared_error

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, competition_paths, configure_logging
from src.db.database import get_db
from src.features.build_league_features import build_league_features, feature_columns, load_league_matches, load_player_lines
from src.features.build_league_pl_features import build_parity_features
from src.models.count_model import build_count_candidates
from src.models.eval_utils import per_match_log_loss
from src.models.train_league_counts import premier_league_specs
from src.models.train_league_model import LABELS, OUTER_SEASONS, fit_outcome, outcome_label, predict_outcome
from src.models.train_match_outcome import ordered_probabilities

logger = logging.getLogger("league_feature_audit")
REPEATS = 30
SEED = 42
STAT_FAMILIES = (("xg", "xg"), ("big_chances", "big_chances"), ("shots_on_target", "sot"), ("shots", "shots"), ("goals", "goals"),
                 ("touches_box", "touches_box"), ("possession_passing", "possession"), ("possession_passing", "pass_pct"))


def outcome_family(column: str) -> str:
    """Family of a 1X2 feature column (differences go with the statistic they are built from)."""
    if "elo" in column:
        return "elo_strength"
    if "ppg" in column or "gdpg" in column:
        return "points_goal_difference"
    if "rest_days" in column or "promoted" in column:
        return "rest_and_promotion"
    for family, token in STAT_FAMILIES:
        if token in column:
            return f"form_{family}"
    return "other"


def permutation_rows(frame: pd.DataFrame, columns: List[str], rng: np.random.Generator) -> pd.DataFrame:
    shuffled = frame.copy()
    order = rng.permutation(len(frame))
    shuffled[columns] = frame[columns].to_numpy()[order]
    return shuffled


def outcome_importance(frame: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
    played = frame[frame["home_score"].notna()].copy()
    played["y"] = outcome_label(played)
    families: Dict[str, List[str]] = {}
    for column in columns:
        families.setdefault(outcome_family(column), []).append(column)
    families["all_features_together"] = list(columns)  # context row: how much the whole set is worth, not a family
    result: Dict[str, Any] = {}
    for season in OUTER_SEASONS:
        train = played[(played["season"] < season) & ~played["season"].isin(LOCKED_SEASONS)].reset_index(drop=True)
        test = played[played["season"] == season].reset_index(drop=True)
        model, calibrator, name, _ = fit_outcome(train, columns)
        y = test["y"].to_numpy(dtype=int)
        base = float(per_match_log_loss(predict_outcome(model, calibrator, test, columns), y).mean())
        raw_base = float(per_match_log_loss(ordered_probabilities(model, test[columns], LABELS), y).mean())
        entry: Dict[str, Any] = {"selected_model": name, "log_loss": base, "raw_log_loss": raw_base, "families": {}}
        for family, members in sorted(families.items()):
            rng = np.random.default_rng(SEED)
            shuffled = [permutation_rows(test, members, rng) for _ in range(REPEATS)]
            increases = [float(per_match_log_loss(predict_outcome(model, calibrator, frame_, columns), y).mean()) - base for frame_ in shuffled]
            raw_increases = [float(per_match_log_loss(ordered_probabilities(model, frame_[columns], LABELS), y).mean()) - raw_base for frame_ in shuffled]
            entry["families"][family] = {"features": len(members), "mean_increase": float(np.mean(increases)), "spread": float(np.std(increases, ddof=1)),
                                         "informative": bool(np.mean(increases) > 2.0 * np.std(increases, ddof=1)),
                                         "raw_mean_increase": float(np.mean(raw_increases)), "raw_spread": float(np.std(raw_increases, ddof=1))}
        result[season] = entry
        logger.info("1X2 %s: %s", season, {f: round(v["mean_increase"], 4) for f, v in entry["families"].items()})
    return result


def count_family(column: str) -> str:
    stem = column.split("_", 1)[1] if column.startswith(("home_", "away_")) else column
    if stem.startswith(("exp_",)):
        return "expected_from_both_teams"
    if "opponent" in stem or "against" in stem:
        return "conceded_or_opponent_history"
    if "possession" in stem or "pass_pct" in stem:
        return "possession_passing"
    if "referee" in stem or "elo" in stem:
        return "referee_and_strength"
    return "own_history"


def count_importance(table: pd.DataFrame, name: str, spec: Any, selected: str) -> Dict[str, Any]:
    data = table[table[spec.target_col].notna() & table["is_played"]].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    split = int(len(data) * 0.8)
    X, y = data[list(spec.features)], data[spec.target_col].astype(float)
    model = clone(build_count_candidates(spec)[selected]).fit(X.iloc[:split], y.iloc[:split])
    test_X, test_y = X.iloc[split:].reset_index(drop=True), y.iloc[split:].to_numpy()
    base = float(mean_squared_error(test_y, model.predict(test_X)) ** 0.5)
    families: Dict[str, List[str]] = {}
    for column in spec.features:
        families.setdefault(count_family(column), []).append(column)
    entry = {"selected_model": selected, "holdout_rmse": base, "holdout_matches": int(len(test_X)), "families": {}}
    for family, members in sorted(families.items()):
        rng = np.random.default_rng(SEED)
        increases = [float(mean_squared_error(test_y, model.predict(permutation_rows(test_X, members, rng))) ** 0.5) - base for _ in range(REPEATS)]
        entry["families"][family] = {"features": len(members), "mean_increase": float(np.mean(increases)), "spread": float(np.std(increases, ddof=1)),
                                     "informative": bool(np.mean(increases) > 2.0 * np.std(increases, ddof=1))}
    logger.info("%s: %s", name, {f: round(v["mean_increase"], 4) for f, v in entry["families"].items()})
    return entry


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
    frame = build_league_features(matches)
    columns = [c for c in feature_columns(frame) if frame[c].notna().any()]
    table = build_parity_features(matches, lines)
    specs = premier_league_specs(table)
    counts: Dict[str, Any] = {}
    for name, filename in (("throws", "throws_model_v1.joblib"), ("offsides", "offside_model_v1.joblib")):
        import joblib

        selected = joblib.load(competition_paths(comp.key).models / filename)["metrics"]["raw_selected_model"]
        counts[name] = count_importance(table, name, specs[name], selected)
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key,
              "protocol": {"repeats": REPEATS, "seed": SEED, "outer_seasons": list(OUTER_SEASONS), "informative_rule": "mean increase greater than twice the spread over the repeats"},
              "outcome_1x2": outcome_importance(frame, columns), "count_models": counts}
    out = REPORTS_DIR / "models" / f"{comp.key}_feature_audit.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Report: %s", out)
    print(json.dumps({"outcome_1x2": {s: {f: round(v["mean_increase"], 4) for f, v in e["families"].items()} for s, e in report["outcome_1x2"].items()},
                      "count_models": {n: {f: round(v["mean_increase"], 4) for f, v in e["families"].items()} for n, e in counts.items()}}, indent=2))


if __name__ == "__main__":
    main()
