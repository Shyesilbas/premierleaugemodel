#!/usr/bin/env python3
"""Ablation of the league 1X2 model: does a variant (extra features, a smaller feature set, a stronger penalty grid) beat the production model out of sample?

Usage: python3 -m src.models.ablate_league_features --competition la_liga --group xi
       python3 -m src.models.ablate_league_features --competition la_liga --group low_c core core_low_c

Variants: ``xi`` adds the first-XI columns; ``low_c`` adds logistic candidates with C below the old grid edge (chosen, like every
candidate, by chronological CV on earlier seasons only); ``core`` replaces the 118 features with a short curated list written down
before the run (``CORE_FEATURES``); ``core_low_c`` combines the last two.

Both sets go through the same walk-forward protocol as ``train_league_model`` (every outer season is predicted by a model
selected and calibrated on earlier seasons only), and the per-match log-loss difference is tested with the paired
bootstrap (10,000 draws, seed 42). Decision rule, fixed before the run: adopt a variant only if the pooled outer-season
mean difference is negative with a 95% interval that excludes zero, its Benjamini-Hochberg q across the variants of the run is
below 0.05, AND the sinama season (the last outer season) alone is also negative; otherwise the variant is recorded as
"No Gain, Not Adopted" and the production model does not change.

Reads: data/football.db. Writes: docs/reports/models/<key>_<group>_ablation.json for one variant, or
<key>_ablation_<group>_<group>.json for several (no model artifact).
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from src.competitions.registry import get_competition
from src.config import REPORTS_DIR, configure_logging
from src.db.database import get_db
from src.features.build_league_pl_features import build_parity_features, parity_feature_columns
from src.features.build_league_features import build_league_features, feature_columns, load_league_matches, load_player_lines, xi_feature_columns
from src.models.eval_utils import apply_fdr, per_match_log_loss, with_inference
from src.models.train_league_model import OUTER_SEASONS, league_candidates, market_probabilities, walk_forward

logger = logging.getLogger("ablate_league_features")

# Fixed before the run: team strength (Elo, points, goal difference), expected-goals form (overall and by venue), the differences the
# 118-feature set builds from them, rest and promotion flags. No count histories, no single-statistic rolling windows.
CORE_FEATURES = (
    "elo_diff", "elo_venue_diff", "abs_elo_diff", "ppg_diff", "abs_ppg_diff", "gdpg_diff", "xg_diff_10", "abs_xg_diff_10", "venue_xg_diff",
    "diff_xg_for_roll_10", "diff_xg_against_roll_10", "diff_sot_for_roll_10", "diff_goals_for_roll_10", "diff_big_chances_for_roll_10",
    "home_xg_for_ewma_02", "home_xg_against_ewma_02", "away_xg_for_ewma_02", "away_xg_against_ewma_02",
    "home_rest_days", "away_rest_days", "is_promoted_home", "is_promoted_away",
)

# variant -> (table, columns, candidate grid) given the production table, the production columns, the matches and the player lines.
# Only ``pl_parity`` swaps the table: its columns carry the Premier League's definitions and share names with the production ones.
Context = Dict[str, Any]
Variant = Callable[[Context], Tuple[pd.DataFrame, List[str], Optional[Dict[str, Any]]]]


def _parity(ctx: Context) -> Tuple[pd.DataFrame, List[str], Optional[Dict[str, Any]]]:
    table = build_parity_features(ctx["matches"], ctx["lines"])
    return table, parity_feature_columns(table), None


VARIANTS: Dict[str, Variant] = {
    "xi": lambda ctx: (ctx["frame"], ctx["base"] + [c for c in xi_feature_columns(ctx["frame"]) if ctx["frame"][c].notna().any()], None),
    "low_c": lambda ctx: (ctx["frame"], ctx["base"], league_candidates(low_c=True)),
    "core": lambda ctx: (ctx["frame"], [c for c in CORE_FEATURES if c in ctx["base"]], None),
    "core_low_c": lambda ctx: (ctx["frame"], [c for c in CORE_FEATURES if c in ctx["base"]], league_candidates(low_c=True)),
    "pl_parity": _parity,
}


def match_losses(result: Dict[str, Any]) -> pd.Series:
    table = result["rows"]["model"]
    losses = per_match_log_loss(table[["p_home", "p_draw", "p_away"]].to_numpy(), table["y"].to_numpy(dtype=int))
    return pd.Series(losses, index=pd.MultiIndex.from_arrays([table["season"], table["match_id"]]))


def compare(candidate: pd.Series, base: pd.Series, seasons: List[str]) -> Dict[str, Any]:
    ids = [i for i in base.index if i[0] in seasons and i in candidate.index]
    return with_inference(candidate.loc[ids].to_numpy(), base.loc[ids].to_numpy())


def decide(pooled: Dict[str, Any], last_season: Dict[str, Any]) -> Dict[str, Any]:
    significant = bool(pooled["mean_delta"] < 0 and pooled["ci_high"] < 0 and pooled.get("q_fdr", pooled["p_two_sided"]) < 0.05)
    adopt = bool(significant and last_season["mean_delta"] < 0)
    return {"adopt": adopt, "pooled_negative_and_significant": significant, "last_outer_season_negative": bool(last_season["mean_delta"] < 0),
            "rule": "adopt only if the pooled outer-season difference is negative with a 95% interval below zero, q (Benjamini-Hochberg across the variants of the run) below 0.05, and the last outer season alone is also negative"}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--group", required=True, nargs="+", choices=sorted(VARIANTS), help="variant(s) to compare with the production model")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    conn = get_db()
    try:
        matches, market, lines = load_league_matches(conn, comp.id), market_probabilities(conn, comp.id), load_player_lines(conn, comp.id)
    finally:
        conn.close()
    frame = build_league_features(matches, lines)
    base_columns = [c for c in feature_columns(frame) if frame[c].notna().any()]
    base = walk_forward(frame, base_columns, market)
    base_loss = match_losses(base)
    outer = list(OUTER_SEASONS)
    seasons = list(base["detail"])
    detail: Dict[str, Any] = {}
    pooled_family: Dict[str, Dict[str, Any]] = {}
    for name in args.group:
        table, columns, candidates = VARIANTS[name]({"frame": frame, "base": base_columns, "matches": matches, "lines": lines})
        logger.info("%s: %d features (production %d), %s grid", name, len(columns), len(base_columns), "extended" if candidates else "production")
        run = walk_forward(table, columns, market, candidates)
        loss = match_losses(run)
        pooled_family[name] = compare(loss, base_loss, outer)
        detail[name] = {"feature_count": len(columns), "added_features": [c for c in columns if c not in base_columns], "removed_feature_count": len([c for c in base_columns if c not in columns]),
                        "mean_log_loss": {s: float(loss[[i for i in loss.index if i[0] == s]].mean()) for s in seasons},
                        "selected_models": {s: d["selected_model"] for s, d in run["detail"].items()},
                        "cv_log_loss": {s: d["cv_log_loss"] for s, d in run["detail"].items()},
                        "last_outer_season": compare(loss, base_loss, outer[-1:])}
    apply_fdr(pooled_family)
    for name in args.group:
        detail[name]["pooled_outer"] = pooled_family[name]
        detail[name]["decision"] = decide(pooled_family[name], detail[name]["last_outer_season"])
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key, "variants": list(args.group),
        "protocol": {"outer_seasons": outer, "locked_monitoring": [s for s in seasons if s not in outer], "bootstrap_draws": 10000, "seed": 42,
                     "base_feature_count": len(base_columns), "base_selected_models": {s: d["selected_model"] for s, d in base["detail"].items()},
                     "base_mean_log_loss": {s: float(base_loss[[i for i in base_loss.index if i[0] == s]].mean()) for s in seasons}},
        "candidate_minus_base": detail,
    }
    name = f"{comp.key}_{args.group[0]}_ablation.json" if len(args.group) == 1 else f"{comp.key}_ablation_{'_'.join(args.group)}.json"
    out = REPORTS_DIR / "models" / name
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    logger.info("Report: %s", out)
    print(json.dumps({n: {"features": d["feature_count"], "mean_log_loss": {s: round(v, 4) for s, v in d["mean_log_loss"].items()},
                          "selected": d["selected_models"], "pooled_outer": {k: d["pooled_outer"].get(k) for k in ("mean_delta", "ci_low", "ci_high", "q_fdr")},
                          "last_outer_season": {k: d["last_outer_season"][k] for k in ("mean_delta", "ci_low", "ci_high")}, "adopt": d["decision"]["adopt"]}
                      for n, d in detail.items()}, indent=2, default=float))


if __name__ == "__main__":
    main()
