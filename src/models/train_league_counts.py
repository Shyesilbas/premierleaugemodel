#!/usr/bin/env python3
"""Count models (corners, throws, offsides, cards, saves) of a league fed by TheStatsAPI.

Usage: python3 -m src.models.train_league_counts --competition la_liga [--features pl|league] [--no-save]

The production variant (``--features pl``, the default) runs the five models on the Premier League's own feature code and curated
lists (``build_league_pl_features``), minus the columns this league has no data for. ``--features league`` is the league's own
feature set (``build_league_features``); it was the first version, is kept so the comparison can be reproduced, and only evaluates.

It runs the Premier League's own selection code (``train_count_model``: expanding-window CV, the skill gate against
``training_mean`` and the nested outer-season gate), so a model that cannot beat the training mean on earlier seasons is
served as ``training_mean`` here too. Only the feature lists differ, because the Premier League lists use columns this
provider cannot give (for example forward-pass accuracy). Reads: data/football.db. Writes: the feature table
``data/competitions/<key>/processed/features_matches_all.parquet`` and one ``*_model_v1.joblib`` per model under
``models/production/<key>/``, and the metrics of every model in ``docs/reports/models/<key>_count_models.json`` (nothing is
written to the Premier League folders). ``--features league`` never writes the feature table or an artifact, only its report.
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
from src.features.build_league_features import build_league_features, count_feature_columns, load_league_matches, load_player_lines
from src.features.build_league_pl_features import build_parity_features
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


def premier_league_specs(frame) -> Dict[str, CountModelSpec]:
    """The Premier League's own specs with their feature lists cut to the columns that exist and vary in this league's table."""
    played = frame["home_score"].notna()
    specs = {}
    for name, spec in (("corners", CORNER_MODEL_SPEC), ("throws", THROWS_MODEL_SPEC), ("offsides", OFFSIDES_MODEL_SPEC), ("cards", CARDS_MODEL_SPEC), ("saves", SAVES_MODEL_SPEC)):
        usable = tuple(c for c in spec.features if c in frame.columns and frame.loc[played, c].nunique() > 1)
        specs[name] = replace(spec, features=usable)
    return specs


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--features", choices=("pl", "league"), default="pl", help="feature definitions: the Premier League's code and lists (production) or the league's own set (evaluation only)")
    parser.add_argument("--no-save", action="store_true", help="evaluate and print the metrics, but write no artifact and no feature table")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    paths = competition_paths(comp.key)
    conn = get_db()
    try:
        matches = load_league_matches(conn, comp.id)
        frame = build_parity_features(matches, load_player_lines(conn, comp.id)) if args.features == "pl" else build_league_features(matches)
    finally:
        conn.close()
    specs = premier_league_specs(frame) if args.features == "pl" else LEAGUE_COUNT_SPECS
    missing = {name: [c for c in spec.features if c not in frame.columns] for name, spec in specs.items()}
    if any(missing.values()):
        raise SystemExit(f"feature columns missing from the league table: {missing}")
    if args.features == "league":
        logger.info("%d count-model columns available", len(count_feature_columns(frame)))
    results: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as scratch:
        write_artifacts = not args.no_save and args.features == "pl"  # the league's own variant only evaluates
        table = paths.features if write_artifacts else Path(scratch) / "features.parquet"
        out_dir = paths.models if write_artifacts else Path(scratch) / "models"
        table.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(table, index=False)
        for name, spec in specs.items():
            results[name] = {"target": spec.target_col, "features": list(spec.features), **train_count_model(spec, str(table), str(out_dir), logger)}
    if not args.no_save:
        report = REPORTS_DIR / "models" / f"{comp.key}_count_models{'_league_features' if args.features == 'league' else ''}.json"
        payload = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key, "models": results}
        report.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info("Report: %s", report)
    keys = ("selected_model", "raw_selected_model", "skill_gate_passed", "train_samples", "test_samples", "test_rmse", "baseline_test_rmse", "test_mae", "baseline_test_mae")
    print(json.dumps({name: {k: r.get(k) for k in keys} for name, r in results.items()}, indent=2, default=str))

if __name__ == "__main__":
    main()
