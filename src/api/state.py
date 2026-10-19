"""Loaded datasets, model artifacts and caches for the API, plus the code that (re)loads them.

Importing this module loads everything (~30 s). Other modules read it as ``state.<name>``;
names are rebound on reload, so never ``from src.api.state import <variable>``."""

import joblib
import json
import logging
import pandas as pd
import re
import threading
import time
from datetime import datetime
from src.analytics.team_attackers import get_team_attacking_leaders
from src.analytics.team_scenarios import get_team_scenario_profile
from src.analytics.team_tactics import get_team_tactical_profile
from src.config import DATA_DIR, DEFAULT_SEASON, MODELS_DIR
from src.db.database import attach_statsapi_xg
from src.features.build_features import build_team_match_history, calculate_rest_days, compute_strength_state, compute_team_states
from src.features.draw_features import build_draw_state
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("api_server")

# Load the current combined datasets & production models into memory.
logger.info("Loading cached datasets and models...")


matches_all = DATA_DIR / "processed" / "matches_summary_all.parquet"


features_all = DATA_DIR / "processed" / "features_matches_all.parquet"


matches_parquet = matches_all


features_parquet = features_all


df_matches = pd.read_parquet(matches_parquet) if matches_parquet.exists() else pd.DataFrame()


if not df_matches.empty:
    df_matches = attach_statsapi_xg(df_matches)


df_features = pd.read_parquet(features_parquet) if features_parquet.exists() else pd.DataFrame()


# Load trained models
corner_artifact = joblib.load(MODELS_DIR / "corner_model_v1.joblib") if (MODELS_DIR / "corner_model_v1.joblib").exists() else None


throws_artifact = joblib.load(MODELS_DIR / "throws_model_v1.joblib") if (MODELS_DIR / "throws_model_v1.joblib").exists() else None


saves_artifact = joblib.load(MODELS_DIR / "saves_model_v1.joblib") if (MODELS_DIR / "saves_model_v1.joblib").exists() else None


outcome_artifact = joblib.load(MODELS_DIR / "outcome_models_v1.joblib") if (MODELS_DIR / "outcome_models_v1.joblib").exists() else None


goals_artifact = joblib.load(MODELS_DIR / "goals_models_v1.joblib") if (MODELS_DIR / "goals_models_v1.joblib").exists() else None


offside_artifact = joblib.load(MODELS_DIR / "offside_model_v1.joblib") if (MODELS_DIR / "offside_model_v1.joblib").exists() else None


cards_artifact = joblib.load(MODELS_DIR / "cards_model_v1.joblib") if (MODELS_DIR / "cards_model_v1.joblib").exists() else None


# Load Player Registry and Match Logs
players_reg_file = DATA_DIR / "processed" / "players_registry.json"


players_logs_file = DATA_DIR / "processed" / "player_match_logs.json"


all_players = []


if players_reg_file.exists():
    with open(players_reg_file, "r", encoding="utf-8") as f:
        all_players = json.load(f)


player_registry_map: Dict[int, Dict[str, Any]] = {int(p["id"]): p for p in all_players if "id" in p}


def resolve_player_photo(pid: Any, reg_p: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Return verified Premier League CDN photo URL or None if not found in registry."""
    if not pid:
        return None
    try:
        if reg_p is None:
            reg_p = player_registry_map.get(int(pid), {})
        if reg_p.get("photo_url"):
            return reg_p["photo_url"]
        opta_c = reg_p.get("opta_code")
        if opta_c:
            return f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"
    except Exception:
        pass
    return None


def get_position_order(pos_str: Optional[str]) -> int:
    """Returns sort priority 1..5 for Kaleci, Savunma, Orta Saha, Forvet."""
    if not pos_str:
        return 5
    p = str(pos_str).strip().upper()
    if p in ["G", "GK", "GOALKEEPER"]:
        return 1
    if p in ["D", "DEF", "DEFENDER", "CB", "LB", "RB", "LWB", "RWB"]:
        return 2
    if p in ["M", "MID", "MIDFIELDER", "CM", "DM", "AM", "LM", "RM"]:
        return 3
    if p in ["F", "FWD", "FORWARD", "ST", "CF", "RW", "LW", "ATT"]:
        return 4
    return 5


def parse_kickoff_datetime(kickoff_str: str) -> datetime:
    """Parses Premier League kickoff string (e.g. 'Sat 10 Oct 2026, 12:30 BST') into sortable datetime."""
    if not kickoff_str:
        return datetime.min
    try:
        clean = re.sub(r'\s+[A-Z]{3,4}$', '', str(kickoff_str).strip())
        return datetime.strptime(clean, '%a %d %b %Y, %H:%M')
    except Exception:
        return datetime.min


_player_logs_dict: Optional[Dict[str, Any]] = None


def get_player_match_logs(pid: int) -> List[Dict[str, Any]]:
    global _player_logs_dict
    if _player_logs_dict is None:
        if players_logs_file.exists():
            try:
                with open(players_logs_file, "r", encoding="utf-8") as f:
                    _player_logs_dict = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading player match logs: {e}")
                _player_logs_dict = {}
        else:
            _player_logs_dict = {}
    return _player_logs_dict.get(str(pid), _player_logs_dict.get(pid, []))


_player_cards_dict: Optional[Dict[str, Any]] = None


def get_player_cards_dict() -> Dict[str, Any]:
    global _player_cards_dict
    if _player_cards_dict is None:
        cards_file = DATA_DIR / "processed" / "player_cards_by_season.json"
        if cards_file.exists():
            try:
                with open(cards_file, "r", encoding="utf-8") as f:
                    _player_cards_dict = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading player cards cache: {e}")
                _player_cards_dict = {}
        else:
            _player_cards_dict = {}
    return _player_cards_dict


# Load 2026-27 fixtures if available
raw_fixtures_2627 = []


fix_2627_path = DATA_DIR / "raw" / f"fixtures_{DEFAULT_SEASON}.json"


if fix_2627_path.exists():
    with open(fix_2627_path, "r", encoding="utf-8") as f:
        raw_fixtures_2627 = json.load(f)


# Unique Teams and Match Stats Lookup
teams_dict = {}


match_stats_map = {}


if not df_matches.empty:
    for _, r in df_matches.iterrows():
        mid = int(r["match_id"])
        teams_dict[int(r["home_id"])] = {"id": int(r["home_id"]), "name": r["home_name"], "abbr": r["home_abbr"]}
        teams_dict[int(r["away_id"])] = {"id": int(r["away_id"]), "name": r["away_name"], "abbr": r["away_abbr"]}
        if pd.notnull(r.get("total_corners")) or pd.notnull(r.get("home_total_scoring_att")) or pd.notnull(r.get("away_total_scoring_att")):
            match_stats_map[mid] = {
                "total_corners": r.get("total_corners"),
                "total_throws": r.get("total_throws"),
                "total_shots": r.get("total_shots"),
                "total_shots_ontarget": r.get("total_shots_ontarget"),
                "total_saves": r.get("total_saves"),
                "home_won_corners": r.get("home_won_corners"),
                "away_won_corners": r.get("away_won_corners"),
                "home_total_throws": r.get("home_total_throws"),
                "away_total_throws": r.get("away_total_throws"),
                "home_total_shots": int(r["home_total_scoring_att"]) if pd.notnull(r.get("home_total_scoring_att")) else None,
                "away_total_shots": int(r["away_total_scoring_att"]) if pd.notnull(r.get("away_total_scoring_att")) else None,
            }


teams_list = sorted(list(teams_dict.values()), key=lambda x: x["name"])


# Live team states (form + strength) built with the SAME definitions as the training features.
# Each team's state includes its latest played match (no stale / future-fixture rows).
_matches_prepared = calculate_rest_days(df_matches) if not df_matches.empty else pd.DataFrame()


_long_history = build_team_match_history(_matches_prepared) if not _matches_prepared.empty else pd.DataFrame()


_played_matches = _matches_prepared[_matches_prepared["is_played"]] if not _matches_prepared.empty else pd.DataFrame()


CURRENT_SEASON = (
    str(_played_matches["season"].iloc[-1]) if not _played_matches.empty and "season" in _played_matches.columns else None
)


_live_state_cache: Dict[str, Tuple[pd.DataFrame, Dict[str, Any], Optional[pd.Timestamp], Any]] = {}


_historical_manager_changes_cache: Dict[str, Any] = {}


_completed_match_details_cache: Dict[int, Any] = {}


_historical_standings_cache: Dict[str, Any] = {}


_historical_fixtures_grouped_cache: Dict[str, Any] = {}


def get_live_state(
    season: Optional[str],
) -> Tuple[pd.DataFrame, Dict[str, Any], Optional[pd.Timestamp], Any]:
    """Return team form, strength, draw history, and cutoff; past seasons use end state."""
    key = "current" if (not season or season in ("all", CURRENT_SEASON)) else season
    if key not in _live_state_cache:
        until: Optional[pd.Timestamp] = None
        if key != "current" and "season" in _played_matches.columns:
            season_played = _played_matches[_played_matches["season"] == season]
            if not season_played.empty:
                until = season_played["match_date"].max()
        draw_history = _played_matches
        if until is not None:
            draw_history = draw_history[draw_history["match_date"] <= until]
        _live_state_cache[key] = (
            compute_team_states(_long_history, until=until),
            compute_strength_state(_matches_prepared, until=until),
            until,
            build_draw_state(draw_history),
        )
    return _live_state_cache[key]


if not _long_history.empty:
    get_live_state(None)  # Warm up current-season state at startup


def reload_runtime_datasets() -> None:
    """Reload data files refreshed by the season sync job into this API worker."""
    global df_matches, df_features, raw_fixtures_2627, teams_dict, match_stats_map
    global teams_list, _matches_prepared, _long_history, _played_matches, CURRENT_SEASON, _live_state_cache
    global outcome_artifact, goals_artifact, offside_artifact, cards_artifact, _loaded_data_version

    # Captured before reading so a write landing mid-reload triggers another reload.
    version = current_data_version()
    outcome_artifact = joblib.load(MODELS_DIR / "outcome_models_v1.joblib") if (MODELS_DIR / "outcome_models_v1.joblib").exists() else None
    goals_artifact = joblib.load(MODELS_DIR / "goals_models_v1.joblib") if (MODELS_DIR / "goals_models_v1.joblib").exists() else None
    offside_artifact = joblib.load(MODELS_DIR / "offside_model_v1.joblib") if (MODELS_DIR / "offside_model_v1.joblib").exists() else None
    cards_artifact = joblib.load(MODELS_DIR / "cards_model_v1.joblib") if (MODELS_DIR / "cards_model_v1.joblib").exists() else None

    df_matches = pd.read_parquet(matches_parquet) if matches_parquet.exists() else pd.DataFrame()
    if not df_matches.empty:
        df_matches = attach_statsapi_xg(df_matches)
    df_features = pd.read_parquet(features_parquet) if features_parquet.exists() else pd.DataFrame()
    if fix_2627_path.exists():
        with fix_2627_path.open("r", encoding="utf-8") as stream:
            raw_fixtures_2627 = json.load(stream)
    else:
        raw_fixtures_2627 = []

    teams_dict = {}
    match_stats_map = {}
    if not df_matches.empty:
        for _, row in df_matches.iterrows():
            match_id = int(row["match_id"])
            teams_dict[int(row["home_id"])] = {"id": int(row["home_id"]), "name": row["home_name"], "abbr": row["home_abbr"]}
            teams_dict[int(row["away_id"])] = {"id": int(row["away_id"]), "name": row["away_name"], "abbr": row["away_abbr"]}
            if pd.notnull(row.get("total_corners")) or pd.notnull(row.get("home_total_scoring_att")) or pd.notnull(row.get("away_total_scoring_att")):
                match_stats_map[match_id] = {
                    "total_corners": row.get("total_corners"),
                    "total_throws": row.get("total_throws"),
                    "total_shots": row.get("total_shots"),
                    "total_shots_ontarget": row.get("total_shots_ontarget"),
                    "total_saves": row.get("total_saves"),
                    "home_won_corners": row.get("home_won_corners"),
                    "away_won_corners": row.get("away_won_corners"),
                    "home_total_throws": row.get("home_total_throws"),
                    "away_total_throws": row.get("away_total_throws"),
                    "home_total_shots": int(row["home_total_scoring_att"]) if pd.notnull(row.get("home_total_scoring_att")) else None,
                    "away_total_shots": int(row["away_total_scoring_att"]) if pd.notnull(row.get("away_total_scoring_att")) else None,
                }
    teams_list = sorted(teams_dict.values(), key=lambda item: item["name"])
    _matches_prepared = calculate_rest_days(df_matches) if not df_matches.empty else pd.DataFrame()
    _long_history = build_team_match_history(_matches_prepared) if not _matches_prepared.empty else pd.DataFrame()
    _played_matches = _matches_prepared[_matches_prepared["is_played"]] if not _matches_prepared.empty else pd.DataFrame()
    CURRENT_SEASON = (
        str(_played_matches["season"].iloc[-1])
        if not _played_matches.empty and "season" in _played_matches.columns
        else None
    )
    _live_state_cache = {}
    _fixture_pred_cache.clear()
    _historical_manager_changes_cache.clear()
    _completed_match_details_cache.clear()
    _historical_standings_cache.clear()
    _historical_fixtures_grouped_cache.clear()
    get_team_tactical_profile.cache_clear()
    get_team_scenario_profile.cache_clear()
    get_team_attacking_leaders.cache_clear()
    if not _long_history.empty:
        get_live_state(None)
    _loaded_data_version = version


_RELOAD_WATCHED = [matches_parquet, features_parquet, fix_2627_path] + [
    MODELS_DIR / name
    for name in ("outcome_models_v1.joblib", "goals_models_v1.joblib", "offside_model_v1.joblib", "cards_model_v1.joblib")
]


_RELOAD_SETTLE_NS = 2_000_000_000  # don't read files a sync script may still be writing


def current_data_version() -> int:
    """Newest mtime (ns) among the files reload_runtime_datasets loads into memory."""
    return max((p.stat().st_mtime_ns for p in _RELOAD_WATCHED if p.exists()), default=0)


_loaded_data_version = current_data_version()


_data_reload_lock = threading.Lock()


def _reload_if_data_changed() -> None:
    """Pick up files rewritten outside the API (e.g. sync scripts run from a terminal)."""
    version = current_data_version()
    if version == _loaded_data_version or time.time_ns() - version < _RELOAD_SETTLE_NS:
        return
    with _data_reload_lock:
        if current_data_version() == _loaded_data_version:  # another request already reloaded
            return
        logger.info("Data files changed on disk; reloading runtime datasets")
        try:
            reload_runtime_datasets()
        except Exception:
            logger.exception("Automatic data reload failed; will retry on a later request")


_fixture_pred_cache: Dict[Tuple[int, int, Optional[str]], Dict[str, Any]] = {}


_fixture_pred_cache.clear()


_season_players_cache: Dict[str, Dict[int, Dict[str, Any]]] = {}


def get_season_players_map(season: str) -> Dict[int, Dict[str, Any]]:
    global _season_players_cache, _player_logs_dict
    if season in _season_players_cache:
        return _season_players_cache[season]

    if _player_logs_dict is None and players_logs_file.exists():
        get_player_match_logs(0)
    logs_map = _player_logs_dict or {}

    s_map: Dict[int, Dict[str, Any]] = {}
    for pid_str, plist in logs_map.items():
        for l in plist:
            if l.get("season") == season:
                try:
                    pid_int = int(pid_str)
                    if pid_int not in s_map or l.get("team_id"):
                        s_map[pid_int] = {
                            "teamId": l.get("team_id"),
                            "teamName": l.get("team_name"),
                        }
                except (ValueError, TypeError):
                    pass

    if season == DEFAULT_SEASON:
        staff_path = DATA_DIR / "processed" / "team_staff.json"
        if staff_path.exists():
            try:
                with staff_path.open("r", encoding="utf-8") as sf:
                    staff_data = json.load(sf)
                    for tid_str, tdata in staff_data.get(DEFAULT_SEASON, {}).items():
                        t_name = tdata.get("name")
                        for p in tdata.get("players", []):
                            if "id" in p:
                                try:
                                    pid_int = int(p["id"])
                                    s_map[pid_int] = {
                                        "teamId": int(tid_str),
                                        "teamName": t_name,
                                    }
                                except (ValueError, TypeError):
                                    pass
            except Exception:
                pass

    _season_players_cache[season] = s_map
    return s_map
