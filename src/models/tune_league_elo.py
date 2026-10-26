#!/usr/bin/env python3
"""Tune the Elo rating constants of a league fed by TheStatsAPI, without touching any outer season for the choice.

Usage: python3 -m src.models.tune_league_elo --competition la_liga [--no-save]

The league's Elo uses the Premier League constants (K, home advantage, season regression, newcomer rating). This script asks
whether other constants rate La Liga better. Protocol (written before the first run): a grid of constants is scored by the
log-loss of a one-feature multinomial logistic regression on the Elo difference, fitted on every earlier season. For each
outer season the constants are chosen on the seasons that precede it only (2024/25: tuning season 2023/24; 2025/26: tuning
seasons 2023/24 and 2024/25), then that season is scored with them. The locked season is only monitored. The tuned Elo is
compared with the current constants on the pooled outer seasons (paired bootstrap, 10,000 draws, seed 42). Reads:
data/football.db. Writes: docs/reports/models/<key>_elo_tuning.json (nothing else).
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, configure_logging
from src.db.database import get_db
from src.features.build_features import ELO_HOME_ADV, ELO_INIT, ELO_K, ELO_NEWCOMER, ELO_SEASON_REGRESS
from src.features.build_league_features import load_league_matches
from src.models.eval_utils import per_match_log_loss, with_inference

logger = logging.getLogger("tune_league_elo")

OUTER_SEASONS = ("2024_25", "2025_26")
WARM_UP_SEASON = "2022_23"
GRID = {
    "k": (10.0, 15.0, 20.0, 30.0, 40.0),
    "home_adv": (40.0, 60.0, 80.0, 100.0),
    "regress": (0.1, 0.2, 0.3, 0.4),
    "newcomer": (1380.0, 1430.0, 1480.0),
    "margin": ("log", "none", "sqrt"),
}
CURRENT = {"k": ELO_K, "home_adv": ELO_HOME_ADV, "regress": ELO_SEASON_REGRESS, "newcomer": ELO_NEWCOMER, "margin": "log"}


def margin_weight(margin: float, mode: str) -> float:
    if margin <= 0 or mode == "none":
        return 1.0
    return float(np.log(margin + 1.0) + 1.0) if mode == "log" else float(np.sqrt(margin))


def elo_difference(matches: pd.DataFrame, params: Dict[str, Any]) -> np.ndarray:
    """Pre-match Elo difference (home minus away) for every match; ratings change only after a played result."""
    elo: Dict[int, float] = {}
    previous_teams: set = set()
    seen: set = set()
    season = None
    first_season = matches["season"].iloc[0]
    diffs = np.empty(len(matches))
    for i, row in enumerate(matches.itertuples(index=False)):
        if row.season != season:
            previous_teams = set(seen)
            for team in elo:
                elo[team] = (1 - params["regress"]) * elo[team] + params["regress"] * ELO_INIT
            seen, season = set(), row.season
        h, a = int(row.home_id), int(row.away_id)
        for team in (h, a):
            if team not in elo:
                elo[team] = ELO_INIT if season == first_season else params["newcomer"]
        diffs[i] = elo[h] - elo[a]
        seen.update((h, a))
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        hs, as_ = float(row.home_score), float(row.away_score)
        expected = 1.0 / (1.0 + 10 ** ((elo[a] - (elo[h] + params["home_adv"])) / 400.0))
        result = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        delta = params["k"] * margin_weight(abs(hs - as_), params["margin"]) * (result - expected)
        elo[h] += delta
        elo[a] -= delta
    return diffs


def outcome_index(matches: pd.DataFrame) -> np.ndarray:
    """0 home win, 1 draw, 2 away win (NaN scores give -1)."""
    hs, as_ = matches["home_score"].to_numpy(float), matches["away_score"].to_numpy(float)
    y = np.where(hs > as_, 0, np.where(hs == as_, 1, 2))
    return np.where(np.isnan(hs) | np.isnan(as_), -1, y)


def season_probabilities(diff: np.ndarray, y: np.ndarray, seasons: np.ndarray, target: str) -> Tuple[np.ndarray, np.ndarray]:
    """Probabilities of one season from a logistic regression on the Elo difference fitted on every earlier played match."""
    order = sorted(set(seasons))
    earlier = np.isin(seasons, order[: order.index(target)]) & (y >= 0)
    test = (seasons == target) & (y >= 0)
    model = LogisticRegression(C=1.0, max_iter=2000).fit(diff[earlier].reshape(-1, 1), y[earlier])
    return model.predict_proba(diff[test].reshape(-1, 1)), y[test]


def score(diff: np.ndarray, y: np.ndarray, seasons: np.ndarray, targets: Sequence[str]) -> float:
    losses: List[float] = []
    for target in targets:
        probs, truth = season_probabilities(diff, y, seasons, target)
        losses.extend(per_match_log_loss(probs, truth))
    return float(np.mean(losses))


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--no-save", action="store_true", help="print the result but write no report")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    conn = get_db()
    try:
        matches = load_league_matches(conn, comp.id)
    finally:
        conn.close()
    seasons = matches["season"].to_numpy()
    y = outcome_index(matches)
    names = list(GRID)
    combos = [dict(zip(names, values)) for values in itertools.product(*GRID.values())]
    logger.info("scoring %d Elo configurations", len(combos))
    cache = {tuple(c.values()): elo_difference(matches, c) for c in combos}
    current_key = tuple(CURRENT[n] for n in names)
    if current_key not in cache:
        cache[current_key] = elo_difference(matches, CURRENT)

    folds: Dict[str, Any] = {}
    tuned_losses: List[np.ndarray] = []
    current_losses: List[np.ndarray] = []
    for outer in OUTER_SEASONS:
        tuning = [s for s in sorted(set(seasons)) if WARM_UP_SEASON < s < outer]
        board = sorted(((score(d, y, seasons, tuning), key) for key, d in cache.items()), key=lambda item: item[0])
        best_loss, best_key = board[0]
        best = dict(zip(names, best_key))
        for label, key, bucket in (("tuned", best_key, tuned_losses), ("current", current_key, current_losses)):
            probs, truth = season_probabilities(cache[key], y, seasons, outer)
            bucket.append(per_match_log_loss(probs, truth))
        folds[outer] = {
            "tuning_seasons": tuning, "chosen": best, "tuning_log_loss": best_loss,
            "current_tuning_log_loss": score(cache[current_key], y, seasons, tuning),
            "top5": [{"params": dict(zip(names, k)), "tuning_log_loss": l} for l, k in board[:5]],
            "outer_log_loss": {"tuned": float(tuned_losses[-1].mean()), "current": float(current_losses[-1].mean())},
        }
    comparison = with_inference(np.concatenate(tuned_losses), np.concatenate(current_losses))
    # marginal effect of each constant around the current setting, on the tuning seasons of the last fold (descriptive)
    last_tuning = folds[OUTER_SEASONS[-1]]["tuning_seasons"]
    marginal = {}
    for name in names:
        marginal[name] = {str(v): score(cache[tuple({**CURRENT, name: v}[n] for n in names)], y, seasons, last_tuning) for v in GRID[name]}
    monitor = {}
    for locked in LOCKED_SEASONS:
        if locked in set(seasons):
            chosen = tuple(folds[OUTER_SEASONS[-1]]["chosen"][n] for n in names)
            for label, key in (("tuned", chosen), ("current", current_key)):
                probs, truth = season_probabilities(cache[key], y, seasons, locked)
                monitor.setdefault(locked, {})[label] = float(per_match_log_loss(probs, truth).mean())
    pooled = {"n": int(sum(len(a) for a in tuned_losses)), "tuned": float(np.concatenate(tuned_losses).mean()), "current": float(np.concatenate(current_losses).mean())}
    # adoption rule, fixed before the run: the pooled delta is negative, its interval is below zero and the last outer season improves too
    last_improves = folds[OUTER_SEASONS[-1]]["outer_log_loss"]["tuned"] < folds[OUTER_SEASONS[-1]]["outer_log_loss"]["current"]
    adopt = bool(comparison["mean_delta"] < 0 and comparison["ci_high"] < 0 and last_improves)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key,
        "protocol": {"outer_seasons": list(OUTER_SEASONS), "warm_up_season": WARM_UP_SEASON, "grid": GRID, "configurations": len(combos),
                     "current": CURRENT, "bootstrap_draws": 10000, "seed": 42,
                     "rule": "adopt only if the pooled outer delta is negative, its 95% interval is below zero and the last outer season improves"},
        "folds": folds, "pooled_outer": pooled, "tuned_vs_current": comparison, "marginal_tuning_log_loss": marginal,
        "locked_monitoring": monitor, "adopt": adopt,
    }
    print(json.dumps({k: payload[k] for k in ("pooled_outer", "tuned_vs_current", "locked_monitoring", "adopt")}, indent=2, default=str))
    for outer, fold in folds.items():
        print(outer, fold["chosen"], fold["outer_log_loss"])
    if not args.no_save:
        path = REPORTS_DIR / "models" / f"{comp.key}_elo_tuning.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info("Report: %s", path)


if __name__ == "__main__":
    main()
