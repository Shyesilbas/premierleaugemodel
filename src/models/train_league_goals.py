#!/usr/bin/env python3
"""Production goal model of a TheStatsAPI league (LaLiga): the Premier League's goal model on the Premier League feature definitions.

Usage: python3 -m src.models.train_league_goals --competition la_liga [--no-save]

The feature set and penalty are chosen on the unlocked seasons by the Premier League's own forward-fold procedure
(``select_blend_config``); the final model is fitted on every played match. Which markets it serves comes from the outer-season
evaluation in ``docs/reports/models/<key>_goal_model_eval.json`` (``evaluate_league_goal_models``): a market whose decision names
this model is served from it, any other market is served as the training base rate and labelled ``baseline``. The score matrix is
aligned to the 1X2 model at serving time, so the two stay coherent.

Reads: data/football.db and the evaluation JSON. Writes: models/production/<key>/goals_models_v1.joblib.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import joblib

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, competition_paths, configure_logging
from src.db.database import get_db
from src.features.build_league_features import load_league_matches, load_player_lines
from src.features.build_league_pl_features import build_parity_features
from src.models.train_goals import blend_model, goal_feature_sets, select_blend_config
from src.models.train_league_model import GOAL_MARKETS, goal_base_rates

logger = logging.getLogger("train_league_goals")
MODEL_NAME = "pl_feature_model"


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--no-save", action="store_true", help="select and fit, print the result, write no artifact")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    evaluation_path = REPORTS_DIR / "models" / f"{comp.key}_goal_model_eval.json"
    if not evaluation_path.exists():
        raise SystemExit(f"Run src.models.evaluate_league_goal_models first: {evaluation_path} is missing")
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    conn = get_db()
    try:
        matches, lines = load_league_matches(conn, comp.id), load_player_lines(conn, comp.id)
    finally:
        conn.close()
    table = build_parity_features(matches, lines)
    played = table[table["home_score"].notna()].reset_index(drop=True)
    dev = played[~played["season"].isin(LOCKED_SEASONS)].reset_index(drop=True)
    sets = {k: [c for c in v if dev[c].nunique() > 1] for k, v in goal_feature_sets(list(played.columns)).items()}
    chosen = select_blend_config(dev, sets)
    features = sets[chosen["feature_set"]]
    model = blend_model(features, chosen).fit(played)
    skill_gate: Dict[str, str] = {m: "model" if evaluation["decision"][m]["serving"] == MODEL_NAME else "baseline" for m in GOAL_MARKETS}
    artifact: Dict[str, Any] = {"model": model, "model_name": MODEL_NAME, "feature_names": features, "chosen": chosen, "skill_gate": skill_gate,
                                "base_rates": goal_base_rates(dev), "evaluation_file": evaluation_path.name, "calibration_matches": int(len(dev)),
                                "production_fit_matches": int(len(played)), "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    logger.info("chosen %s; features %d; skill gate %s", chosen, len(features), skill_gate)
    if not args.no_save:
        target = competition_paths(comp.key).models / "goals_models_v1.joblib"
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, target)
        logger.info("Artifact: %s", target)
    print(json.dumps({"chosen": chosen, "features": len(features), "skill_gate": skill_gate, "base_rates": artifact["base_rates"]}, indent=2))


if __name__ == "__main__":
    main()
