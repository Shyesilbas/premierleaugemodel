#!/usr/bin/env python3
"""Count models (corners, throws, offsides, cards, saves) of a league fed by TheStatsAPI.

Usage: python3 -m src.models.train_league_counts --competition la_liga [--no-save]

It runs the Premier League's own selection code (``train_count_model``: expanding-window CV, the skill gate against
``training_mean`` and the nested outer-season gate), so a model that cannot beat the training mean on earlier seasons is
served as ``training_mean`` here too. Only the feature lists differ, because the Premier League lists use columns this
provider cannot give (for example forward-pass accuracy). Reads: data/football.db. Writes: the feature table
``data/competitions/<key>/processed/features_matches_all.parquet`` and one ``*_model_v1.joblib`` per model under
``models/production/<key>/``, and the metrics of every model in ``docs/reports/models/<key>_count_models.json`` (nothing is
written to the Premier League folders).
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.competitions.registry import get_competition
from src.config import REPORTS_DIR, competition_paths, configure_logging
from src.db.database import get_db
from src.features.build_league_features import build_league_features, count_feature_columns, load_league_matches
from src.models.count_model import CountModelSpec, train_count_model
from src.models.train_cards import CARDS_MODEL_SPEC
from src.models.train_corners import CORNER_MODEL_SPEC
from src.models.train_offsides import OFFSIDES_MODEL_SPEC
from src.models.train_saves import SAVES_MODEL_SPEC
from src.models.train_throws import THROWS_MODEL_SPEC

logger = logging.getLogger("train_league_counts")

LEAGUE_COUNT_SPECS: Dict[str, CountModelSpec] = {
    "corners": replace(CORNER_MODEL_SPEC, features=(
        "home_corners_for_roll_10", "away_corners_for_roll_10", "home_corners_against_roll_10", "away_corners_against_roll_10",
        "home_corners_for_roll_5", "away_corners_for_roll_5", "home_shots_for_roll_5", "away_shots_for_roll_5",
        "home_touches_box_roll_5", "away_touches_box_roll_5")),
    "throws": replace(THROWS_MODEL_SPEC, features=(
        "home_throws_for_roll_5", "home_throws_for_roll_10", "away_throws_for_roll_5", "away_throws_for_roll_10",
        "home_throws_against_roll_10", "away_throws_against_roll_10", "home_possession_roll_5", "away_possession_roll_5",
        "home_pass_pct_roll_10", "away_pass_pct_roll_10")),
    "offsides": replace(OFFSIDES_MODEL_SPEC, features=(
        "home_offsides_for_roll_5", "home_offsides_for_roll_10", "away_offsides_for_roll_5", "away_offsides_for_roll_10",
        "home_offsides_against_roll_5", "away_offsides_against_roll_5", "home_offsides_against_roll_10", "away_offsides_against_roll_10",
        "home_possession_roll_5", "away_possession_roll_5")),
    "cards": replace(CARDS_MODEL_SPEC, features=(
        "home_cards_for_roll_5", "away_cards_for_roll_5", "home_cards_against_roll_5", "away_cards_against_roll_5",
        "home_fouls_committed_roll_5", "away_fouls_committed_roll_5", "home_fouls_drawn_roll_5", "away_fouls_drawn_roll_5",
        "abs_elo_diff", "referee_avg_cards", "referee_avg_fouls")),
    "saves": replace(SAVES_MODEL_SPEC, features=(
        "home_saves_for_roll_5", "home_saves_for_roll_10", "away_saves_for_roll_5", "away_saves_for_roll_10",
        "home_shots_against_roll_5", "away_shots_against_roll_5", "home_sot_against_roll_5", "away_sot_against_roll_5",
        "home_shots_for_roll_5", "away_shots_for_roll_5")),
}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--no-save", action="store_true", help="evaluate and print the metrics, but write no artifact and no feature table")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    paths = competition_paths(comp.key)
    conn = get_db()
    try:
        frame = build_league_features(load_league_matches(conn, comp.id))
    finally:
        conn.close()
    missing = {name: [c for c in spec.features if c not in frame.columns] for name, spec in LEAGUE_COUNT_SPECS.items()}
    if any(missing.values()):
        raise SystemExit(f"feature columns missing from the league table: {missing}")
    logger.info("%d count-model columns available", len(count_feature_columns(frame)))
    results: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as scratch:
        table = paths.features if not args.no_save else Path(scratch) / "features.parquet"
        out_dir = paths.models if not args.no_save else Path(scratch) / "models"
        table.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(table, index=False)
        for name, spec in LEAGUE_COUNT_SPECS.items():
            results[name] = {"target": spec.target_col, "features": list(spec.features), **train_count_model(spec, str(table), str(out_dir), logger)}
    if not args.no_save:
        report = REPORTS_DIR / "models" / f"{comp.key}_count_models.json"
        payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key, "models": results}
        report.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info("Report: %s", report)
    keys = ("selected_model", "raw_selected_model", "skill_gate_passed", "train_samples", "test_samples", "test_rmse", "baseline_test_rmse", "test_mae", "baseline_test_mae")
    print(json.dumps({name: {k: r.get(k) for k in keys} for name, r in results.items()}, indent=2, default=str))

if __name__ == "__main__":
    main()
