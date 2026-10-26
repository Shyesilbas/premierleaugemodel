#!/usr/bin/env python3
"""Feature-group ablation of the league 1X2 model: does adding a group of features beat the production set out of sample?

Usage: python3 -m src.models.ablate_league_features --competition la_liga --group xi

Both sets go through the same walk-forward protocol as ``train_league_model`` (every outer season is predicted by a model
selected and calibrated on earlier seasons only), and the per-match log-loss difference is tested with the paired
bootstrap (10,000 draws, seed 42). Decision rule, fixed before the run: adopt the group only if the pooled outer-season
mean difference is negative with a 95% interval that excludes zero AND the sinama season (the last outer season) alone is
also negative; otherwise the group is recorded as "No Gain, Not Adopted" and the production set does not change.

Reads: data/football.db. Writes: docs/reports/models/<key>_<group>_ablation.json (no model artifact).
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

import pandas as pd

from src.competitions.registry import get_competition
from src.config import REPORTS_DIR, configure_logging
from src.db.database import get_db
from src.features.build_league_features import build_league_features, feature_columns, load_league_matches, load_player_lines, xi_feature_columns
from src.models.eval_utils import per_match_log_loss, with_inference
from src.models.train_league_model import OUTER_SEASONS, market_probabilities, walk_forward

logger = logging.getLogger("ablate_league_features")

GROUPS: Dict[str, Callable[[pd.DataFrame], List[str]]] = {"xi": xi_feature_columns}


def match_losses(result: Dict[str, Any]) -> pd.Series:
    table = result["rows"]["model"]
    losses = per_match_log_loss(table[["p_home", "p_draw", "p_away"]].to_numpy(), table["y"].to_numpy(dtype=int))
    return pd.Series(losses, index=pd.MultiIndex.from_arrays([table["season"], table["match_id"]]))


def compare(candidate: pd.Series, base: pd.Series, seasons: List[str]) -> Dict[str, Any]:
    ids = [i for i in base.index if i[0] in seasons and i in candidate.index]
    return with_inference(candidate.loc[ids].to_numpy(), base.loc[ids].to_numpy())


def decide(pooled: Dict[str, Any], last_season: Dict[str, Any]) -> Dict[str, Any]:
    significant = pooled["mean_delta"] < 0 and pooled["ci_high"] < 0
    adopt = bool(significant and last_season["mean_delta"] < 0)
    return {"adopt": adopt, "pooled_negative_and_significant": bool(significant), "last_outer_season_negative": bool(last_season["mean_delta"] < 0),
            "rule": "adopt only if the pooled outer-season difference is negative with a 95% interval below zero and the last outer season alone is also negative"}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--group", required=True, choices=sorted(GROUPS), help="feature group to add on top of the production set")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    conn = get_db()
    try:
        matches, market, lines = load_league_matches(conn, comp.id), market_probabilities(conn, comp.id), load_player_lines(conn, comp.id)
    finally:
        conn.close()
    frame = build_league_features(matches, lines)
    base_columns = [c for c in feature_columns(frame) if frame[c].notna().any()]
    extra = [c for c in GROUPS[args.group](frame) if frame[c].notna().any()]
    logger.info("base: %d features, %s group: %d features", len(base_columns), args.group, len(extra))
    base = walk_forward(frame, base_columns, market)
    candidate = walk_forward(frame, base_columns + extra, market)
    base_loss, candidate_loss = match_losses(base), match_losses(candidate)
    outer = list(OUTER_SEASONS)
    pooled, last = compare(candidate_loss, base_loss, outer), compare(candidate_loss, base_loss, outer[-1:])
    per_season = {s: {"base": float(base_loss[[i for i in base_loss.index if i[0] == s]].mean()),
                      args.group: float(candidate_loss[[i for i in candidate_loss.index if i[0] == s]].mean())} for s in base["detail"]}
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key, "group": args.group,
        "protocol": {"outer_seasons": outer, "locked_monitoring": [s for s in base["detail"] if s not in outer], "bootstrap_draws": 10000, "seed": 42,
                     "base_feature_count": len(base_columns), "added_features": extra},
        "mean_log_loss": per_season, "selected_models": {"base": {s: d["selected_model"] for s, d in base["detail"].items()},
                                                         args.group: {s: d["selected_model"] for s, d in candidate["detail"].items()}},
        "candidate_minus_base": {"pooled_outer": pooled, "last_outer_season": last}, "decision": decide(pooled, last),
    }
    out = REPORTS_DIR / "models" / f"{comp.key}_{args.group}_ablation.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    logger.info("Report: %s", out)
    print(json.dumps({"mean_log_loss": per_season, "pooled_outer": pooled, "last_outer_season": last, "decision": report["decision"]}, indent=2, default=float))


if __name__ == "__main__":
    main()
