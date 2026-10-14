"""Pre-match draw-propensity features from one incremental history state."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

PRIOR_DRAW = 0.25
PRIOR_LOW = 0.45
PRIOR_GOALS = 2.7
TEAM_K = 5.0
LEAGUE_K = 20.0
TEAM_WINDOW = 10
LEAGUE_WINDOW = 100

DRAW_PROPENSITY_FEATURES = [
    "home_draw_rate_10", "away_draw_rate_10", "pair_draw_rate_10",
    "home_low_scoring_10", "away_low_scoring_10", "pair_low_scoring_10",
    "pair_total_goals_10", "league_draw_rate_100", "season_progress",
]


def _shrunk(total: float, n: int, prior: float, k: float) -> float:
    return (float(total) + k * prior) / (n + k)


class DrawFeatureState:
    """Rolling team and league results, updated only after each kickoff batch."""

    def __init__(self) -> None:
        self.team: Dict[int, deque] = defaultdict(lambda: deque(maxlen=TEAM_WINDOW))
        self.league: deque = deque(maxlen=LEAGUE_WINDOW)

    def _team_stats(self, team_id: int) -> tuple[float, float, float]:
        history = self.team[int(team_id)]
        n = len(history)
        draws = sum(row[0] for row in history)
        low_scoring = sum(row[1] for row in history)
        total_goals = sum(row[2] for row in history)
        return (
            _shrunk(draws, n, PRIOR_DRAW, TEAM_K),
            _shrunk(low_scoring, n, PRIOR_LOW, TEAM_K),
            _shrunk(total_goals, n, PRIOR_GOALS, TEAM_K),
        )

    def features(
        self,
        home_id: int,
        away_id: int,
        gameweek: Optional[float] = None,
    ) -> Dict[str, Any]:
        home_draw, home_low, home_goals = self._team_stats(home_id)
        away_draw, away_low, away_goals = self._team_stats(away_id)
        league_n = len(self.league)
        league_draw = _shrunk(sum(self.league), league_n, PRIOR_DRAW, LEAGUE_K)
        progress = (
            float(gameweek) / 38.0
            if gameweek is not None and pd.notna(gameweek) and gameweek > 0
            else np.nan
        )
        return {
            "home_draw_rate_10": home_draw,
            "away_draw_rate_10": away_draw,
            "pair_draw_rate_10": (home_draw + away_draw) / 2.0,
            "home_low_scoring_10": home_low,
            "away_low_scoring_10": away_low,
            "pair_low_scoring_10": (home_low + away_low) / 2.0,
            "pair_total_goals_10": (home_goals + away_goals) / 2.0,
            "league_draw_rate_100": league_draw,
            "season_progress": progress,
        }

    def update(self, home_id: int, away_id: int, home_goals: int, away_goals: int) -> None:
        is_draw = int(home_goals == away_goals)
        total_goals = int(home_goals) + int(away_goals)
        entry = (is_draw, int(total_goals <= 2), total_goals)
        self.team[int(home_id)].append(entry)
        self.team[int(away_id)].append(entry)
        self.league.append(is_draw)


def _ordered_batches(matches: pd.DataFrame):
    required = {"kickoff_millis"}
    missing = required.difference(matches.columns)
    has_match_id = "match_id" in matches.columns or matches.index.name == "match_id"
    if not has_match_id:
        missing.add("match_id")
    if missing:
        raise KeyError(f"Draw features require columns: {sorted(missing)}")
    if pd.to_numeric(matches["kickoff_millis"], errors="coerce").isna().any():
        raise ValueError("Draw features require valid kickoff_millis values")
    match_ids = matches["match_id"] if "match_id" in matches.columns else pd.Series(matches.index, index=matches.index)
    order_keys = pd.DataFrame({"kickoff_millis": matches["kickoff_millis"], "_match_id": match_ids}, index=matches.index)
    sorted_idx = order_keys.sort_values(["kickoff_millis", "_match_id"], kind="mergesort").index
    ordered = matches.loc[sorted_idx]
    return ordered.groupby("kickoff_millis", sort=False, dropna=False)


def _update_batch(state: DrawFeatureState, batch: pd.DataFrame) -> None:
    for row in batch.itertuples(index=False):
        if pd.notna(row.home_score) and pd.notna(row.away_score):
            state.update(int(row.home_id), int(row.away_id), int(row.home_score), int(row.away_score))


def build_draw_state(played: pd.DataFrame) -> DrawFeatureState:
    """Build the state after the supplied played history for live predictions."""
    state = DrawFeatureState()
    for _, batch in _ordered_batches(played):
        _update_batch(state, batch)
    return state


def add_draw_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add pre-match draw features without leaking results from tied kickoffs."""
    required = {"home_id", "away_id", "home_score", "away_score"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Draw features require columns: {sorted(missing)}")

    state = DrawFeatureState()
    rows: Dict[Any, Dict[str, Any]] = {}
    has_gameweek = "gameweek" in df.columns
    for _, batch in _ordered_batches(df):
        for index, row in batch.iterrows():
            gameweek = row.get("gameweek") if has_gameweek else None
            rows[index] = state.features(int(row["home_id"]), int(row["away_id"]), gameweek)
        _update_batch(state, batch)

    feature_frame = pd.DataFrame.from_dict(rows, orient="index")[DRAW_PROPENSITY_FEATURES]
    feature_frame = feature_frame.reindex(df.index)
    return df.drop(columns=[name for name in DRAW_PROPENSITY_FEATURES if name in df.columns]).join(feature_frame)
