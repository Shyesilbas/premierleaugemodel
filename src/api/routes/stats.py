"""League statistics route: week and season rankings for the Statistics page."""

import logging
import sqlite3
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.analytics.league_stats import build_league_stats
from src.analytics.player_ratings import get_match_bookings_map
from src.api import state
from src.config import DATA_DIR, DEFAULT_SEASON, SEASONS
from src.db.database import get_db

router = APIRouter()
logger = logging.getLogger("api_server")

GOAL_EVENTS_FILE = DATA_DIR / "processed" / "shots_events_all.parquet"
_CACHE_LIMIT = 64

_goal_events_cache: Tuple[int, pd.DataFrame] = (0, pd.DataFrame())
_result_cache: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _goal_events() -> pd.DataFrame:
    """Goal rows of the shot-event file, reloaded when the file changes."""
    global _goal_events_cache
    if not GOAL_EVENTS_FILE.exists():
        return pd.DataFrame()
    mtime = GOAL_EVENTS_FILE.stat().st_mtime_ns
    if _goal_events_cache[0] != mtime:
        events = pd.read_parquet(GOAL_EVENTS_FILE, columns=["match_id", "event_id", "event_type", "minute", "seconds", "text"])
        _goal_events_cache = (mtime, events[events["event_type"] == "goal"].reset_index(drop=True))
    return _goal_events_cache[1]


def _audit_rows(season: str) -> List[Dict[str, Any]]:
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT match_id, actual_result, prob_home, prob_draw, prob_away FROM model_match_audit WHERE season = ?",
                (season,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        logger.warning("model_match_audit is unavailable; the surprises section stays empty")
        return []


def _normalise(name: Any) -> str:
    """Lower-case, accent-free name used to join Transfermarkt rows to the PL player registry."""
    decomposed = unicodedata.normalize("NFKD", str(name or ""))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def _ages(season: str) -> Dict[int, int]:
    """Player age by registry id; Transfermarkt ids differ from PL ids, so rows join on name."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT team_id, name, age FROM player_market_values WHERE season = ? AND age IS NOT NULL",
                (season,),
            ).fetchall()
    except sqlite3.Error:
        return {}

    by_team_name: Dict[Tuple[int, str], int] = {}
    by_name: Dict[str, List[int]] = {}
    by_team_last: Dict[Tuple[int, str], List[int]] = {}
    for row in rows:
        full = _normalise(row["name"])
        by_team_name[(int(row["team_id"]), full)] = int(row["age"])
        by_name.setdefault(full, []).append(int(row["age"]))
        by_team_last.setdefault((int(row["team_id"]), full.split(" ")[-1]), []).append(int(row["age"]))

    ages: Dict[int, int] = {}
    for pid, reg in state.player_registry_map.items():
        full = _normalise(reg.get("name"))
        team_id = int(reg["teamId"]) if reg.get("teamId") is not None else -1
        found = by_team_name.get((team_id, full))
        if found is None and len(by_name.get(full, [])) == 1:
            found = by_name[full][0]
        if found is None:
            last_matches = by_team_last.get((team_id, full.split(" ")[-1]), [])
            found = last_matches[0] if len(last_matches) == 1 else None
        if found is not None:
            ages[pid] = found
    return ages


def _player_logs() -> Dict[str, List[Dict[str, Any]]]:
    state.get_player_match_logs(0)  # loads the lazily cached dict
    return state._player_logs_dict or {}


@router.get("/api/stats")
def get_league_stats(
    season: str = Query(DEFAULT_SEASON),
    scope: str = Query("week", pattern="^(week|season)$"),
    gameweek: Optional[int] = Query(None, ge=1, le=38),
):
    """Rankings for one gameweek (scope=week) or the whole season (scope=season).

    Scope sections cover only the selected scope; cumulative sections (goalkeepers, minutes,
    young players, referees, form, movers, venue tables, goal minutes) cover everything up to
    and including the selected gameweek.
    """
    if season not in SEASONS:
        raise HTTPException(status_code=404, detail=f"Unknown season: {season}")

    key = (state._loaded_data_version, season, scope, gameweek if scope == "week" else None)
    cached = _result_cache.get(key)
    if cached is not None:
        return cached

    result = build_league_stats(
        season=season,
        scope=scope,
        gameweek=gameweek,
        matches=state.df_matches,
        logs=_player_logs(),
        registry=state.player_registry_map,
        bookings=get_match_bookings_map(),
        goal_events=_goal_events(),
        audit_rows=_audit_rows(season),
        ages=_ages(season),
        teams=state.teams_dict,
        photo_url=state.resolve_player_photo,
    )
    if len(_result_cache) >= _CACHE_LIMIT:
        _result_cache.clear()
    _result_cache[key] = result
    return result
