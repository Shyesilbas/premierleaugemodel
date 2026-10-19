#!/usr/bin/env python3
"""
Premier League Model Engine — FastAPI Backend Server
Serves interactive prediction engine, fixtures, events, and static frontend dashboard.
"""

import json
import logging
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None  # type: ignore

import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.models.model_utils import (
    apply_probability_calibrator,
    blend_log,
    count_tail_probability,
    safe_feature_frame as _safe_features,
)
from src.models.dixon_coles import align_to_outcome_probs, btts_prob, expected_goals, over_prob, team_over_prob
from src.db.database import get_referees_list, get_referee_detail, get_all_grouped_fixtures, get_referee_summary, get_db, attach_statsapi_xg
from src.features.build_features import (
    calculate_rest_days,
    build_team_match_history,
    compute_team_states,
    compute_strength_state,
    build_prediction_row,
)
from src.features.draw_features import build_draw_state
from src.analytics.team_tactics import get_team_tactical_profile
from src.analytics.team_scenarios import get_team_scenario_profile
from src.analytics.team_attackers import get_team_attacking_leaders
from src.analytics.model_audit import run_model_audit
from src.analytics.player_ratings import (
    analyze_match_starting_xis,
    get_player_dynamic_rating,
    calculate_detailed_match_score,
    calculate_single_match_score,
    get_match_bookings_map,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

app = FastAPI(title="Premier League Model Engine API", version="1.0.0")

_sync_job_lock = threading.Lock()
_sync_job: Dict[str, Any] = {"id": None, "status": "idle", "season": None, "message": None, "output": ""}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.config import DATA_DIR, MODELS_DIR, ROOT as BASE_DIR
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else (BASE_DIR / "frontend")

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



@app.get("/api/teams/staff")
def get_team_staff(season: str = "2026_27", team_id: Optional[int] = None):
    """Return season staff, falling back to archived source data for older seasons."""
    staff_path = DATA_DIR / "processed" / "team_staff.json"
    raw_staff_path = DATA_DIR / "processed" / "team_staff_raw.json"
    manager_rosters_path = DATA_DIR / "processed" / "team_manager_rosters.json"
    if not staff_path.exists():
        raise HTTPException(status_code=404, detail="Team staff data not available")
    try:
        with staff_path.open("r", encoding="utf-8") as stream:
            staff_by_season = json.load(stream)
        raw_staff_by_season = {}
        if raw_staff_path.exists():
            with raw_staff_path.open("r", encoding="utf-8") as stream:
                raw_staff_by_season = json.load(stream)
        manager_rosters = {}
        if manager_rosters_path.exists():
            with manager_rosters_path.open("r", encoding="utf-8") as stream:
                manager_rosters = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read team staff data")
        raise HTTPException(status_code=500, detail="Could not read team staff data") from exc

    # The normalized file currently has complete coverage only for 2026/27;
    # archived PulseLive responses contain the older seasons.
    season_staff = {
        **raw_staff_by_season.get(season, {}),
        **staff_by_season.get(season, {}),
    }
    season_manager_roster = manager_rosters.get(season, {}).get("managers", {})
    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    season_changes = []
    if changes_path.exists():
        try:
            with changes_path.open("r", encoding="utf-8") as stream:
                season_changes = json.load(stream).get(season, {}).get("events", [])
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read manager change data for staff fallback")

    for event in season_changes:
        current_team_id = str(event.get("team_id", ""))
        if current_team_id and current_team_id not in season_staff:
            season_staff[current_team_id] = {"team_name": event.get("team_name", ""), "officials": []}
    for current_team_id, entry in season_manager_roster.items():
        season_staff.setdefault(current_team_id, {"team_name": entry.get("team_name", ""), "officials": []})

    def add_manager_fallback(current_team_id: str, staff: Dict[str, Any]) -> Dict[str, Any]:
        officials = list(staff.get("officials") or [])
        has_manager = any(
            str(official.get("role", "")).lower() == "manager"
            and (official.get("name") or {}).get("display")
            for official in officials
        )
        if not has_manager:
            roster_entry = season_manager_roster.get(current_team_id)
            manager_name = (roster_entry or {}).get("name")
            if not manager_name:
                appointments = [
                    event for event in season_changes
                    if str(event.get("team_id")) == current_team_id and event.get("incoming_manager")
                ]
                latest = max(appointments, key=lambda event: event.get("appointment_date", "")) if appointments else None
                manager_name = (latest or {}).get("incoming_manager")
            if manager_name:
                officials.append({
                    "role": "Manager",
                    "active": True,
                    "name": {"display": manager_name},
                    "inferred_from_manager_changes": not bool(roster_entry),
                })
        return {**staff, "officials": officials}

    if team_id is not None:
        staff = season_staff.get(str(team_id))
        if staff is None and not any(str(event.get("team_id")) == str(team_id) for event in season_changes):
            raise HTTPException(status_code=404, detail="Team staff not found for this season")
        staff = staff or {"officials": []}
        staff = add_manager_fallback(str(team_id), staff)
        return {"season": season, "team_id": team_id, "staff": staff}

    managers = {}
    for current_team_id, staff in season_staff.items():
        staff = add_manager_fallback(str(current_team_id), staff)
        officials = staff.get("officials") or []
        manager = next(
            (official for official in officials if official.get("role", "").lower() == "manager" and official.get("active")),
            next((official for official in officials if official.get("role", "").lower() == "manager"), None),
        )
        name = (manager or {}).get("name") or {}
        display = name.get("display") or " ".join(
            part for part in (name.get("first"), name.get("last")) if part
        )
        if display:
            managers[str(current_team_id)] = display
    return {"season": season, "managers": managers}

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
fix_2627_path = DATA_DIR / "raw" / "fixtures_2026_27.json"
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


@app.middleware("http")
async def reload_changed_data(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        await run_in_threadpool(_reload_if_data_changed)
    return await call_next(request)


@app.get("/api/data-version")
def get_data_version():
    """Changes whenever the API reloads data; the frontend drops its localStorage caches on change."""
    return {"version": str(_loaded_data_version)}


def _sync_command(kind: str, season: str) -> List[str]:
    sync_season_script = str(BASE_DIR / "src" / "ingest" / "sync_season_data.py")
    return {
        "matches": [sys.executable, sync_season_script, "--season-name", season],
        "referees": [sys.executable, sync_season_script, "--season-name", season, "--referees-only"],
        # 2h window: official XIs are published roughly 60-75 min before kickoff
        "lineups": [sys.executable, "-m", "src.ingest.sync_prematch_lineups", "--season", season, "--hours-ahead", "2"],
    }[kind]


def _run_season_sync_job(job_id: str, season: str, kind: str = "matches") -> None:
    command = _sync_command(kind, season)
    try:
        result = subprocess.run(
            command,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=60 * 30,
            check=False,
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()[-6000:]
        if result.returncode != 0:
            with _sync_job_lock:
                if _sync_job.get("id") == job_id:
                    _sync_job.update(status="failed", message="Veri güncellemesi tamamlanamadı.", output=output)
            return

        reload_runtime_datasets()
        with _sync_job_lock:
            if _sync_job.get("id") == job_id:
                matches = []
                for line in result.stdout.splitlines():
                    if line.startswith("SYNC_RESULT "):
                        matches = json.loads(line[len("SYNC_RESULT "):]).get("matches", [])
                _sync_job.update(
                    status="completed",
                    message="Veri bulundu" if matches else "Veri bulunamadı",
                    matches=matches,
                    output=output,
                )
    except Exception as exc:
        logger.exception("Season sync job failed")
        with _sync_job_lock:
            if _sync_job.get("id") == job_id:
                _sync_job.update(status="failed", message=str(exc), output="")


@app.post("/api/admin/sync-season")
def start_season_sync(season: str = Query("2026_27"), kind: str = Query("matches")):
    """Start a background sync: matches (results + stats), referees, or lineups."""
    if kind not in {"matches", "referees", "lineups"}:
        raise HTTPException(status_code=400, detail="Unsupported sync kind")
    if season not in {"2022_23", "2023_24", "2024_25", "2025_26", "2026_27"}:
        raise HTTPException(status_code=400, detail="Unsupported season")
    with _sync_job_lock:
        if _sync_job.get("status") in {"queued", "running"}:
            return {**_sync_job, "already_running": True}
        job_id = str(uuid.uuid4())
        _sync_job.update(id=job_id, status="running", season=season, kind=kind, message="Başlandı...", matches=[], output="")
    thread = threading.Thread(target=_run_season_sync_job, args=(job_id, season, kind), daemon=True)
    thread.start()
    return {**_sync_job, "already_running": False}


@app.post("/api/admin/reload-models")
def admin_reload_models():
    """Reload all runtime datasets and ML model artifacts."""
    reload_runtime_datasets()
    return {"status": "success", "message": "All models and feature datasets reloaded successfully"}


@app.get("/api/admin/sync-season")
def get_season_sync_status():
    with _sync_job_lock:
        return dict(_sync_job)


@app.get("/api/teams")
def get_teams(season: Optional[str] = None):
    """Returns sorted list of teams, optionally filtered by season."""
    if season == "2026_27":
        current_teams = {}
        for fixture in raw_fixtures_2627:
            for entry in fixture.get("teams", []):
                team = entry.get("team") or {}
                team_id = team.get("id")
                if team_id is None:
                    continue
                club = team.get("club") or {}
                current_teams[int(team_id)] = {
                    "id": int(team_id),
                    "name": team.get("name") or club.get("name") or "",
                    "abbr": club.get("abbr") or "",
                }

        if current_teams:
            result = sorted(current_teams.values(), key=lambda team: team["name"])
            return {"teams": result, "count": len(result)}

    if df_matches.empty:
        return {"teams": teams_list}

    df = df_matches
    if season and "season" in df.columns:
        df = df[df["season"] == season]

    filtered_teams = {}
    for _, r in df.iterrows():
        filtered_teams[int(r["home_id"])] = {"id": int(r["home_id"]), "name": r["home_name"], "abbr": r["home_abbr"]}
        filtered_teams[int(r["away_id"])] = {"id": int(r["away_id"]), "name": r["away_name"], "abbr": r["away_abbr"]}

    result = sorted(list(filtered_teams.values()), key=lambda x: x["name"])
    return {"teams": result, "count": len(result)}


@app.get("/api/fixtures")
def get_fixtures(limit: int = 800, search: Optional[str] = None, season: Optional[str] = None):
    """Returns list of matches, optionally filtered by season and search."""
    if df_matches.empty:
        return {"fixtures": []}

    df = df_matches.copy()
    if season and "season" in df.columns and season != "all":
        df = df[df["season"] == season]

    if search:
        s = search.lower()
        mask = (
            df["home_name"].str.lower().str.contains(s) |
            df["away_name"].str.lower().str.contains(s) |
            df["ground_name"].str.lower().str.contains(s)
        )
        df = df[mask]

    records = df.head(limit).to_dict(orient="records")
    return {"fixtures": records, "total": len(records)}


_fixture_pred_cache: Dict[Tuple[int, int, Optional[str]], Dict[str, Any]] = {}
_fixture_pred_cache.clear()

def get_quick_fixture_prediction(home_id: int, away_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not home_id or not away_id or home_id == away_id:
        return None
    cache_key = (home_id, away_id, season)
    if cache_key in _fixture_pred_cache:
        return _fixture_pred_cache[cache_key]
    try:
        p = predict_match(home_id, away_id, season)
        summary = {
            "favorite_label": p["favorite_label"],
            "home_win_pct": p["outcome"]["home_win_pct"],
            "draw_pct": p["outcome"]["draw_pct"],
            "away_win_pct": p["outcome"]["away_win_pct"],
            "over_2_5_goals_pct": p["outcome"]["over_2_5_goals_pct"],
            "over_2_5_source": p["outcome"].get("over_2_5_source", "legacy"),
            "goals": p.get("goals", {}),
            "expected_corners": p["corners"]["expected_total"],
            "corners_model_skill": p["corners"]["model_skill"],
            "expected_cards": p["cards"]["expected_total"],
            "cards_model_skill": p["cards"]["model_skill"],
            "prob_over_3_5_cards": p["cards"]["prob_over_3_5_pct"],
            "referee_name": p["referee"]["name"],
        }
        _fixture_pred_cache[cache_key] = summary
        return summary
    except Exception as e:
        logger.warning(f"Error generating quick prediction for {home_id} vs {away_id}: {e}")
        return None


def _regression_model_skill(artifact: Optional[Dict[str, Any]]) -> str:
    """Expose whether a count prediction uses the gated model or mean baseline."""
    if artifact is None:
        return "baseline"
    metrics = artifact.get("metrics") or {}
    if metrics.get("selected_model") == "training_mean" or metrics.get("skill_gate_applied"):
        return "baseline"
    return "model"


@app.get("/api/teams/manager-changes")
def get_manager_changes(season: str = "2026_27"):
    """Place verified appointment events on each team's first subsequent league fixture."""
    if season not in ("2026_27", "all") and season in _historical_manager_changes_cache:
        return _historical_manager_changes_cache[season]

    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    if not changes_path.exists():
        return {"season": season, "events_by_match": {}}
    try:
        with changes_path.open("r", encoding="utf-8") as stream:
            changes_by_season = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read manager change data")
        raise HTTPException(status_code=500, detail="Could not read manager change data") from exc

    seasons = list(changes_by_season) if season == "all" else [season]
    all_events_by_match: Dict[str, List[Dict[str, Any]]] = {}
    for current_season in seasons:
      season_changes = changes_by_season.get(current_season, {}).get("events", [])
      fixtures = get_all_grouped_fixtures(current_season)
      fixtures_by_team: Dict[int, List[Tuple[datetime, Dict[str, Any]]]] = {}
      for fixture in fixtures:
        kickoff = parse_kickoff_datetime(fixture.get("kickoff_label", ""))
        if kickoff == datetime.min:
          continue
        for current_team_id in (int(fixture["home_id"]), int(fixture["away_id"])):
          fixtures_by_team.setdefault(current_team_id, []).append((kickoff, fixture))
      for team_fixtures in fixtures_by_team.values():
        team_fixtures.sort(key=lambda item: item[0])

      for event in season_changes:
        try:
            appointment_date = datetime.strptime(event["appointment_date"], "%Y-%m-%d").date()
            team_id = int(event["team_id"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed manager change record: %s", event)
            continue

        # Appointment sources provide dates, not times. The first fixture on a
        # later calendar date is the first one after the announcement.
        next_match = next(
            ((kickoff, fixture) for kickoff, fixture in fixtures_by_team.get(team_id, [])
             if kickoff.date() > appointment_date),
            None,
        )
        if next_match is None:
            continue
        _, next_fixture = next_match
        match_id = str(next_fixture["match_id"])
        all_events_by_match.setdefault(match_id, []).append({
            **event,
            "season": current_season,
            "gameweek": next_fixture.get("gameweek"),
            "effective_match_date": next_fixture.get("kickoff_label", ""),
        })

    response_data = {"season": season, "events_by_match": all_events_by_match}
    if season not in ("2026_27", "all"):
        _historical_manager_changes_cache[season] = response_data
    return response_data


@app.get("/api/teams/manager-performance")
def get_manager_performance(team_id: int, manager_name: str, season: str = "all"):
    """Summarize a manager's completed league matches against each opponent."""
    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    rosters_path = DATA_DIR / "processed" / "team_manager_rosters.json"
    staff_path = DATA_DIR / "processed" / "team_staff.json"
    try:
        changes = json.loads(changes_path.read_text(encoding="utf-8")) if changes_path.exists() else {}
        rosters = json.loads(rosters_path.read_text(encoding="utf-8")) if rosters_path.exists() else {}
        staff_by_season = json.loads(staff_path.read_text(encoding="utf-8")) if staff_path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Could not read manager history") from exc

    df = df_matches.copy()
    if season != "all" and "season" in df.columns:
        df = df[df["season"] == season]
    matching = []
    for match_season, group in changes.items():
        if season != "all" and match_season != season:
            continue
        events = sorted(
            [event for event in group.get("events", []) if int(event.get("team_id", -1)) == team_id],
            key=lambda event: event.get("appointment_date", ""),
        )
        season_staff = staff_by_season.get(match_season, {}).get(str(team_id), {})
        listed_manager = next((
            official.get("name", {}).get("display")
            for official in season_staff.get("officials", [])
            if str(official.get("role", "")).lower() == "manager"
            and (official.get("name", {}).get("display") or "").casefold() == manager_name.casefold()
        ), None)
        baseline = (
            listed_manager
            or rosters.get(match_season, {}).get("managers", {}).get(str(team_id), {}).get("name")
            or (events[0].get("outgoing_manager") if events else None)
        )
        # If this season has no change record or roster entry, a continuing
        # manager listed for the following season is a useful baseline.
        if not baseline:
            later_staff = staff_by_season.get("2026_27", {}).get(str(team_id), {})
            baseline = next((
                official.get("name", {}).get("display")
                for official in later_staff.get("officials", [])
                if str(official.get("role", "")).lower() == "manager"
                and (official.get("name", {}).get("display") or "").casefold() == manager_name.casefold()
            ), None)
        for _, row in df[df["season"] == match_season].iterrows():
            home = int(row["home_id"]) == team_id
            if not home and int(row["away_id"]) != team_id:
                continue
            kickoff = str(row.get("kickoff_label", ""))
            try:
                match_date = datetime.strptime(kickoff.split(",")[0].strip(), "%a %d %b %Y").date().isoformat()
            except ValueError:
                millis = row.get("kickoff_millis")
                match_date = datetime.fromtimestamp(float(millis) / 1000).date().isoformat() if pd.notnull(millis) else ""
            coach = baseline
            for event in events:
                if event.get("appointment_date", "") <= match_date:
                    coach = event.get("incoming_manager")
                else:
                    break
            if coach and coach.casefold() == manager_name.casefold():
                matching.append((row, home))

    summary = {}
    total = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    for row, home in matching:
        opponent_id = int(row["away_id"] if home else row["home_id"])
        opponent = str(row["away_name"] if home else row["home_name"])
        scored = row["home_score"] if home else row["away_score"]
        conceded = row["away_score"] if home else row["home_score"]
        if pd.isnull(scored) or pd.isnull(conceded):
            continue
        scored, conceded = int(scored), int(conceded)
        item = summary.setdefault(opponent_id, {"opponent_id": opponent_id, "opponent": opponent, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0})
        item["matches"] += 1
        item["gf"] += scored
        item["ga"] += conceded
        item["wins" if scored > conceded else "losses" if scored < conceded else "draws"] += 1
        total["matches"] += 1
        total["gf"] += scored
        total["ga"] += conceded
        total["wins" if scored > conceded else "losses" if scored < conceded else "draws"] += 1
    return {"team_id": team_id, "manager_name": manager_name, "season": season, "total": total,
            "opponents": sorted(summary.values(), key=lambda item: item["opponent"].casefold())}


@app.get("/api/fixtures/grouped")
def get_grouped_fixtures(season: str = "2026_27"):
    """
    Returns fixtures grouped by Gameweek, and within each Gameweek, grouped by match day.
    Uses indexed SQLite database with instant response time and attached referee cards data.
    """
    if season not in ("2026_27", "current") and season in _historical_fixtures_grouped_cache:
        return _historical_fixtures_grouped_cache[season]

    db_fixtures = get_all_grouped_fixtures(season)
    raw_fixtures = []

    # Determine current active gameweek (the earliest gameweek with unplayed matches)
    unplayed_gws = [
        int(r["gameweek"]) for r in db_fixtures
        if not (r.get("status") == "COMPLETED" or (r.get("home_score") is not None and r.get("away_score") is not None))
    ]
    current_gw = min(unplayed_gws) if unplayed_gws else (int(db_fixtures[-1]["gameweek"]) if db_fixtures else 1)

    for r in db_fixtures:
        mid = int(r["match_id"])
        h_id = int(r["home_id"])
        a_id = int(r["away_id"])
        gw = int(r["gameweek"])
        h_score = r["home_score"]
        a_score = r["away_score"]
        is_completed = (r["status"] == "COMPLETED" or (h_score is not None and a_score is not None))
        match_stats = match_stats_map.get(mid, {})

        # Compute AI predictions strictly for uncompleted matches in the CURRENT gameweek only
        pred = (
            get_quick_fixture_prediction(h_id, a_id, r.get("season") or season)
            if (not is_completed and gw == current_gw)
            else None
        )

        kickoff_ms = None
        if "kickoff_millis" in r and pd.notnull(r["kickoff_millis"]):
            try:
                kickoff_ms = int(r["kickoff_millis"])
            except (ValueError, TypeError):
                kickoff_ms = None

        raw_fixtures.append({
            "match_id": mid,
            "gameweek": gw,
            "kickoff_label": r.get("kickoff_label") or "",
            "kickoff_millis": kickoff_ms,
            "day_label": r.get("day_label") or "",
            "time_label": r.get("time_label") or "",
            "ground_name": r.get("ground_name") or "",
            "home_id": h_id,
            "home_name": r["home_name"],
            "home_abbr": r.get("home_abbr") or "",
            "home_score": h_score,
            "away_id": a_id,
            "away_name": r["away_name"],
            "away_abbr": r.get("away_abbr") or "",
            "away_score": a_score,
            "total_corners": r.get("total_corners"),
            "total_throws": r.get("total_throws"),
            "total_shots": r.get("total_shots"),
            "home_total_shots": match_stats.get("home_total_shots"),
            "away_total_shots": match_stats.get("away_total_shots"),
            "total_shots_ontarget": r.get("total_shots_ontarget"),
            "total_saves": r.get("total_saves"),
            "home_won_corners": r.get("home_won_corners"),
            "away_won_corners": r.get("away_won_corners"),
            "home_total_throws": r.get("home_total_throws"),
            "away_total_throws": r.get("away_total_throws"),
            "referee_name": r.get("referee_name") or "Atanmadı",
            "referee_id": r.get("referee_id"),
            "total_yellow_cards": r.get("total_yellow_cards"),
            "total_red_cards": r.get("total_red_cards"),
            "total_cards": r.get("total_cards"),
            "total_fouls": r.get("total_fouls"),
            "ref_avg_cards": r.get("ref_avg_cards"),
            "ref_strictness": r.get("ref_strictness"),
            "home_xg": round(float(r["statsapi_home_xg"]), 2) if r.get("statsapi_home_xg") is not None else None,
            "away_xg": round(float(r["statsapi_away_xg"]), 2) if r.get("statsapi_away_xg") is not None else None,
            "total_xg": round(float(r["statsapi_home_xg"] + r["statsapi_away_xg"]), 2)
                if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None else None,
            "xg_source": r.get("xg_provider") if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None else None,
            "xg_quality": r.get("statsapi_xg_quality"),
            "status": "COMPLETED" if is_completed else "UPCOMING",
            "season": r.get("season") or season,
            "prediction": pred,
        })

    # Group by Gameweek -> Day
    gw_groups = {}
    for fix in raw_fixtures:
        gw = fix["gameweek"]
        if gw not in gw_groups:
            gw_groups[gw] = {}
        day = fix["day_label"] or "Belirtilmemiş Gün"
        if day not in gw_groups[gw]:
            gw_groups[gw][day] = []
        gw_groups[gw][day].append(fix)

    structured = []
    for gw in sorted(gw_groups.keys()):
        # Sort matches within each day chronologically
        for d in gw_groups[gw]:
            gw_groups[gw][d].sort(key=lambda m: parse_kickoff_datetime(m.get("kickoff_label", "")))

        # Sort days within the gameweek strictly chronologically by earliest match on each day
        sorted_day_keys = sorted(
            gw_groups[gw].keys(),
            key=lambda d: parse_kickoff_datetime(gw_groups[gw][d][0].get("kickoff_label", "")) if gw_groups[gw][d] else datetime.min
        )

        day_list = [{"day": d, "matches": gw_groups[gw][d]} for d in sorted_day_keys]
        structured.append({"gameweek": gw, "days": day_list})

    # Determine current gameweek:
    current_gw = 1
    upcoming_gws = [
        gw for gw in sorted(gw_groups.keys())
        if any(m.get("status") == "UPCOMING" for d in gw_groups[gw].values() for m in d)
    ]
    if upcoming_gws:
        current_gw = upcoming_gws[0]
    elif gw_groups:
        current_gw = max(gw_groups.keys())

    next_unplayed = next((f for f in raw_fixtures if f.get("status") == "UPCOMING"), None)
    next_match_info = None
    if next_unplayed:
        next_match_info = {
            "match_id": next_unplayed["match_id"],
            "gameweek": next_unplayed["gameweek"],
            "kickoff_label": next_unplayed["kickoff_label"],
            "kickoff_millis": next_unplayed.get("kickoff_millis"),
        }

    res = {
        "season": season,
        "gameweeks": structured,
        "total_matches": len(raw_fixtures),
        "current_gameweek": current_gw,
        "next_match": next_match_info,
    }
    if season not in ("2026_27", "current"):
        _historical_fixtures_grouped_cache[season] = res
    return res


@app.get("/api/referees")
def get_referees(season: str = "2026_27", search: Optional[str] = None):
    """Returns list of Premier League referees and card statistics from SQLite."""
    return {"referees": get_referees_list(season, search)}


@app.get("/api/referees/{name}")
def get_referee_profile(name: str, season: str = "2026_27"):
    """Returns detailed profile and matches officiated by referee from SQLite."""
    return get_referee_detail(name, season)



@app.get("/api/standings")
def get_standings(season: str = "2026_27"):
    """
    Computes Premier League standings table for the specified season.
    Includes Played, Won, Drawn, Lost, GF, GA, GD, Points, and Last 5 Form,
    plus Home and Away breakdowns.
    """
    if season not in ("2026_27", "current") and season in _historical_standings_cache:
        return _historical_standings_cache[season]

    matches_to_process = []

    if season == "2026_27" and raw_fixtures_2627:
        for f in raw_fixtures_2627:
            teams = f.get("teams", [])
            if len(teams) < 2:
                continue
            h_score = teams[0].get("score")
            a_score = teams[1].get("score")
            if h_score is None or a_score is None:
                continue
            matches_to_process.append({
                "gameweek": int(f.get("gameweek", {}).get("gameweek", 1)),
                "home_id": int(teams[0]["team"]["id"]),
                "home_name": teams[0]["team"]["name"],
                "away_id": int(teams[1]["team"]["id"]),
                "away_name": teams[1]["team"]["name"],
                "home_score": int(h_score),
                "away_score": int(a_score),
            })
    else:
        df = df_matches.copy()
        if season != "all" and "season" in df.columns:
            df = df[df["season"] == season]
        for _, r in df.iterrows():
            if pd.isnull(r.get("home_score")) or pd.isnull(r.get("away_score")):
                continue
            matches_to_process.append({
                "gameweek": int(r.get("gameweek") or 1),
                "home_id": int(r["home_id"]),
                "home_name": str(r["home_name"]),
                "away_id": int(r["away_id"]),
                "away_name": str(r["away_name"]),
                "home_score": int(r["home_score"]),
                "away_score": int(r["away_score"]),
            })

    # Sort matches chronologically by gameweek for accurate form
    matches_to_process.sort(key=lambda m: m["gameweek"])

    table = {}
    for m in matches_to_process:
        hid = m["home_id"]
        hname = m["home_name"]
        aid = m["away_id"]
        aname = m["away_name"]
        h_score = m["home_score"]
        a_score = m["away_score"]

        for tid, tname in [(hid, hname), (aid, aname)]:
            if tid not in table:
                t_meta = teams_dict.get(tid, {})
                table[tid] = {
                    "id": tid,
                    "name": tname,
                    "short": t_meta.get("short", tname),
                    "abbr": t_meta.get("abbr", ""),
                    "badge": f"/badges/{tid}.svg",
                    "played": 0, "won": 0, "drawn": 0, "lost": 0,
                    "gf": 0, "ga": 0, "gd": 0, "points": 0,
                    "form": [],
                    "home": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
                    "away": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
                }

        table[hid]["played"] += 1
        table[hid]["home"]["played"] += 1
        table[hid]["gf"] += h_score
        table[hid]["home"]["gf"] += h_score
        table[hid]["ga"] += a_score
        table[hid]["home"]["ga"] += a_score

        table[aid]["played"] += 1
        table[aid]["away"]["played"] += 1
        table[aid]["gf"] += a_score
        table[aid]["away"]["gf"] += a_score
        table[aid]["ga"] += h_score
        table[aid]["away"]["ga"] += h_score

        if h_score > a_score:
            table[hid]["won"] += 1
            table[hid]["home"]["won"] += 1
            table[hid]["points"] += 3
            table[hid]["home"]["points"] += 3
            table[hid]["form"].append("W")

            table[aid]["lost"] += 1
            table[aid]["away"]["lost"] += 1
            table[aid]["form"].append("L")
        elif h_score < a_score:
            table[aid]["won"] += 1
            table[aid]["away"]["won"] += 1
            table[aid]["points"] += 3
            table[aid]["away"]["points"] += 3
            table[aid]["form"].append("W")

            table[hid]["lost"] += 1
            table[hid]["home"]["lost"] += 1
            table[hid]["form"].append("L")
        else:
            table[hid]["drawn"] += 1
            table[hid]["home"]["drawn"] += 1
            table[hid]["points"] += 1
            table[hid]["home"]["points"] += 1
            table[hid]["form"].append("D")

            table[aid]["drawn"] += 1
            table[aid]["away"]["drawn"] += 1
            table[aid]["points"] += 1
            table[aid]["away"]["points"] += 1
            table[aid]["form"].append("D")

    standings_list = []
    for t in table.values():
        t["gd"] = t["gf"] - t["ga"]
        t["home"]["gd"] = t["home"]["gf"] - t["home"]["ga"]
        t["away"]["gd"] = t["away"]["gf"] - t["away"]["ga"]
        t["form"] = t["form"][-5:]  # Keep last 5 matches for form
        standings_list.append(t)

    # Sort standard PL rules: Points DESC -> GD DESC -> GF DESC
    standings_list.sort(key=lambda x: (x["points"], x["gd"], x["gf"]), reverse=True)

    for rank, item in enumerate(standings_list, 1):
        item["rank"] = rank

    res = {
        "season": season,
        "total_teams": len(standings_list),
        "standings": standings_list
    }
    if season not in ("2026_27", "current"):
        _historical_standings_cache[season] = res
    return res


@app.get("/api/match/{match_id}/recent-form")
def get_match_recent_form(match_id: int):
    """Return each team's last five completed league results before a match."""
    # The current season standings are sourced from the live fixture feed, so
    # use that same source here to ensure current fixtures have pre-match form.
    if raw_fixtures_2627:
        current_fixtures = []
        for fixture in raw_fixtures_2627:
            fixture_teams = fixture.get("teams", [])
            if len(fixture_teams) < 2:
                continue
            current_fixtures.append({
                "match_id": int(fixture.get("match", {}).get("id") or fixture.get("match_id") or fixture.get("id") or 0),
                "gameweek": int((fixture.get("gameweek") or {}).get("gameweek", 1)),
                "kickoff": (fixture.get("kickoff") or {}).get("millis") or (fixture.get("kickoff") or {}).get("label", ""),
                "home_id": int(fixture_teams[0]["team"]["id"]),
                "away_id": int(fixture_teams[1]["team"]["id"]),
                "home_score": fixture_teams[0].get("score"),
                "away_score": fixture_teams[1].get("score"),
            })
        selected = next((fixture for fixture in current_fixtures if fixture["match_id"] == match_id), None)
        if selected:
            selected_kickoff = selected["kickoff"] or ""
            previous_fixtures = [
                fixture for fixture in current_fixtures
                if fixture["match_id"] != match_id
                and fixture["home_score"] is not None and fixture["away_score"] is not None
                and (fixture["gameweek"], fixture["kickoff"], fixture["match_id"])
                    < (selected["gameweek"], selected_kickoff, selected["match_id"])
                and (fixture["home_id"] in (selected["home_id"], selected["away_id"])
                     or fixture["away_id"] in (selected["home_id"], selected["away_id"]))
            ]
            previous_fixtures.sort(key=lambda fixture: (fixture["gameweek"], fixture["kickoff"], fixture["match_id"]), reverse=True)
            form = {str(selected["home_id"]): [], str(selected["away_id"]): []}
            for fixture in previous_fixtures:
                home_score = int(fixture["home_score"])
                away_score = int(fixture["away_score"])
                for team_id in (selected["home_id"], selected["away_id"]):
                    results = form[str(team_id)]
                    if len(results) >= 5:
                        continue
                    if team_id == fixture["home_id"]:
                        results.append("W" if home_score > away_score else "L" if home_score < away_score else "D")
                    elif team_id == fixture["away_id"]:
                        results.append("W" if away_score > home_score else "L" if away_score < home_score else "D")
            for results in form.values():
                results.reverse()
            return {"match_id": match_id, "season": "2026_27", "form": form}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT season, match_date, kickoff_label, home_id, away_id, home_score, away_score
        FROM matches
        WHERE match_id = ?
    """, (match_id,))
    selected = cursor.fetchone()
    if not selected:
        conn.close()
        raise HTTPException(status_code=404, detail="Match not found")

    season = selected["season"]
    cutoff_date = selected["match_date"] or ""
    cutoff_kickoff = selected["kickoff_label"] or ""
    teams = (int(selected["home_id"]), int(selected["away_id"]))
    cursor.execute("""
        SELECT match_id, match_date, kickoff_label, home_id, away_id, home_score, away_score
        FROM matches
        WHERE season = ? AND match_id != ? AND home_score IS NOT NULL AND away_score IS NOT NULL
          AND (match_date < ? OR (match_date = ? AND kickoff_label < ?))
          AND (home_id IN (?, ?) OR away_id IN (?, ?))
        ORDER BY match_date DESC, kickoff_label DESC, match_id DESC
    """, (season, match_id, cutoff_date, cutoff_date, cutoff_kickoff, *teams, *teams))
    previous_matches = [dict(row) for row in cursor.fetchall()]
    conn.close()

    form = {str(team_id): [] for team_id in teams}
    for previous in previous_matches:
        home_id = int(previous["home_id"])
        away_id = int(previous["away_id"])
        home_score = int(previous["home_score"])
        away_score = int(previous["away_score"])
        for team_id in teams:
            if len(form[str(team_id)]) >= 5:
                continue
            if team_id == home_id:
                result = "W" if home_score > away_score else "L" if home_score < away_score else "D"
            elif team_id == away_id:
                result = "W" if away_score > home_score else "L" if away_score < home_score else "D"
            else:
                continue
            form[str(team_id)].append(result)

    for results in form.values():
        results.reverse()
    return {"match_id": match_id, "season": season, "form": form}



@app.get("/api/teams/profile")
def get_team_profile(team_id: int, season: Optional[str] = "all"):
    """
    Returns team profile with match previews, W/D/L record, and squad roster.
    """
    team_meta = teams_dict.get(team_id)
    if not team_meta:
        # Fallback search in all_players
        p_team = next((p for p in all_players if p.get("teamId") == team_id), None)
        if p_team:
            team_meta = {"id": team_id, "name": p_team.get("teamName", ""), "abbr": ""}
        else:
            raise HTTPException(status_code=404, detail="Team not found")

    df = df_matches.copy()
    if season and season != "all" and "season" in df.columns:
        df = df[df["season"] == season]

    # Filter team matches
    team_matches_df = df[(df["home_id"] == team_id) | (df["away_id"] == team_id)].copy()
    if "kickoff_millis" in team_matches_df.columns:
        team_matches_df = team_matches_df.sort_values(by="kickoff_millis")

    matches_list = []
    wins, draws, losses = 0, 0, 0
    gf, ga = 0, 0

    for _, r in team_matches_df.iterrows():
        is_home = (int(r["home_id"]) == team_id)
        opp_id = int(r["away_id"]) if is_home else int(r["home_id"])
        opp_name = str(r["away_name"]) if is_home else str(r["home_name"])
        t_score = r["home_score"] if is_home else r["away_score"]
        o_score = r["away_score"] if is_home else r["home_score"]

        res = "-"
        if pd.notnull(t_score) and pd.notnull(o_score):
            t_score_int = int(t_score)
            o_score_int = int(o_score)
            gf += t_score_int
            ga += o_score_int
            if t_score_int > o_score_int:
                res = "W"
                wins += 1
            elif t_score_int < o_score_int:
                res = "L"
                losses += 1
            else:
                res = "D"
                draws += 1
            t_score = t_score_int
            o_score = o_score_int
        else:
            t_score = None
            o_score = None

        kickoff_ms = None
        if "kickoff_millis" in r and pd.notnull(r["kickoff_millis"]):
            try:
                kickoff_ms = int(r["kickoff_millis"])
            except (ValueError, TypeError):
                kickoff_ms = None

        matches_list.append({
            "match_id": int(r["match_id"]),
            "season": str(r.get("season", "")),
            "status": "COMPLETED" if pd.notnull(t_score) else "UNPLAYED",
            "gameweek": r.get("gameweek"),
            "kickoff_label": r.get("kickoff_label"),
            "kickoff_millis": kickoff_ms,
            "is_home": is_home,
            "opponent_id": opp_id,
            "opponent_name": opp_name,
            "team_score": t_score,
            "opp_score": o_score,
            "result": res,
            "total_corners": int(r["total_corners"]) if pd.notnull(r.get("total_corners")) else None,
            "total_throws": int(r["total_throws"]) if pd.notnull(r.get("total_throws")) else None,
            "total_shots": int(r["total_shots"]) if pd.notnull(r.get("total_shots")) else None,
            "total_saves": int(r["total_saves"]) if pd.notnull(r.get("total_saves")) else None,
        })

    # Find the next upcoming unplayed match
    next_match = None
    for m in matches_list:
        if m["status"] == "UNPLAYED":
            next_match = {
                "match_id": m["match_id"],
                "gameweek": m["gameweek"],
                "kickoff_label": m["kickoff_label"],
                "kickoff_millis": m.get("kickoff_millis"),
                "opponent_id": m["opponent_id"],
                "opponent_name": m["opponent_name"],
                "is_home": m["is_home"],
            }
            break

    # Squad list with season-accurate statistics
    all_logs = _player_logs_dict or {}
    if not all_logs and players_logs_file.exists():
        get_player_match_logs(0)
        all_logs = _player_logs_dict or {}
    cards_dict = get_player_cards_dict()

    # Identify players who played for this team in this season (or any season if season == 'all')
    pids_season = set()
    for pid_str, plist in all_logs.items():
        for l in plist:
            if (season == "all" or l.get("season") == season) and l.get("team_id") == team_id:
                try:
                    pids_season.add(int(pid_str))
                except (ValueError, TypeError):
                    pass

    # If 2026_27, use the official verified 2026_27 roster from team_staff.json
    roster_players = []
    if season == "2026_27":
        staff_path = DATA_DIR / "processed" / "team_staff.json"
        if staff_path.exists():
            try:
                with staff_path.open("r", encoding="utf-8") as sf:
                    staff_data = json.load(sf)
                    roster_players = staff_data.get("2026_27", {}).get(str(team_id), {}).get("players", [])
            except Exception:
                roster_players = []
        roster_pids = {int(p["id"]) for p in roster_players if "id" in p}
        all_team_pids = roster_pids.union(pids_season)
    else:
        all_team_pids = pids_season
    # Fetch Transfermarkt market values
    tm_team_data = None
    player_values_map = {}
    try:
        conn = sqlite3.connect(DATA_DIR / "premier_league.db")
        conn.row_factory = sqlite3.Row
        
        # 1. Team market value for requested season (fallback to latest available)
        t_row = conn.execute(
            "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? AND season = ?",
            (team_id, season)
        ).fetchone()
        if not t_row:
            t_row = conn.execute(
                "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? ORDER BY season DESC LIMIT 1",
                (team_id,)
            ).fetchone()

        # 2. Complete 5-year historical market value evolution for this team
        hist_rows = conn.execute(
            "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? ORDER BY season ASC",
            (team_id,)
        ).fetchall()
        
        history_list = []
        for hr in hist_rows:
            s_val = hr["season"]
            mv_val = hr["market_value_eur"]
            avg_val = hr["avg_market_value_eur"]
            history_list.append({
                "season": s_val,
                "season_label": s_val.replace("_", "/"),
                "market_value_eur": mv_val,
                "avg_market_value_eur": avg_val,
                "squad_size": hr["squad_size"],
                "formatted": f"€{mv_val/1000:.2f}B" if mv_val >= 1000 else f"€{mv_val:,.1f}M",
                "avg_formatted": f"€{avg_val:.2f}M" if avg_val else "-",
            })

        if t_row:
            mv_eur = t_row["market_value_eur"]
            tm_team_data = {
                "season": t_row["season"],
                "market_value_eur": mv_eur,
                "avg_market_value_eur": t_row["avg_market_value_eur"],
                "squad_size": t_row["squad_size"],
                "formatted": f"€{mv_eur/1000:.2f}B" if mv_eur >= 1000 else f"€{mv_eur:,.1f}M",
                "avg_formatted": f"€{t_row['avg_market_value_eur']:.2f}M",
                "history": history_list,
            }
        
        # 3. Player market values for requested season (fallback to latest season)
        p_rows = conn.execute(
            "SELECT player_id, name, market_value_eur FROM player_market_values WHERE team_id = ? AND season = ?",
            (team_id, season)
        ).fetchall()
        if not p_rows:
            p_rows = conn.execute(
                "SELECT player_id, name, market_value_eur FROM player_market_values WHERE team_id = ? ORDER BY season DESC",
                (team_id,)
            ).fetchall()

        for pr in p_rows:
            norm_name = pr["name"].lower().strip()
            val_obj = {"eur": pr["market_value_eur"], "tm_id": pr["player_id"]}
            player_values_map[norm_name] = val_obj
            parts = norm_name.split()
            if len(parts) > 1:
                player_values_map[parts[-1]] = val_obj
        conn.close()
    except Exception as e:
        logger.warning(f"Could not load market values for team {team_id}: {e}")

    squad = []
    for pid in all_team_pids:
        p = player_registry_map.get(pid)
        if not p:
            roster_match = next((x for x in roster_players if x.get("id") == pid), None)
            if roster_match:
                n = roster_match.get("name", {})
                dname = n.get("display") or f"{n.get('first', '')} {n.get('last', '')}".strip()
                p = {
                    "id": pid,
                    "name": dname,
                    "position": roster_match.get("info", {}).get("position") or roster_match.get("latestPosition"),
                    "shirt": roster_match.get("info", {}).get("shirtNum"),
                    "country": roster_match.get("nationalTeam", {}).get("country"),
                    "captain": False,
                }
            else:
                p = next((x for x in all_players if x.get("id") == pid), {"id": pid, "name": f"Oyuncu {pid}", "position": "M", "shirt": None})

        p_logs = all_logs.get(str(pid), all_logs.get(pid, []))
        if season == "all":
            team_logs = [l for l in p_logs if l.get("team_id") == team_id]
            yc = sum(v.get("yellow", 0) for k, v in cards_dict.items() if k.endswith(f"_{pid}"))
            rc = sum(v.get("red", 0) for k, v in cards_dict.items() if k.endswith(f"_{pid}"))
        else:
            team_logs = [l for l in p_logs if l.get("season") == season and l.get("team_id") == team_id]
            card_info = cards_dict.get(f"{season}_{pid}", {})
            yc = card_info.get("yellow", 0)
            rc = card_info.get("red", 0)

        apps = len(team_logs)
        starts = sum(1 for l in team_logs if l.get("started"))
        goals = sum(int(l.get("goals") or 0) for l in team_logs)
        assists = sum(int(l.get("assists") or 0) for l in team_logs)

        # For historical seasons, don't include players with 0 appearances for this team in this season
        if season != "all" and season != "2026_27" and apps == 0:
            continue

        photo_url = resolve_player_photo(pid, p)

        # Match player market value
        p_name_lower = (p.get("name") or "").lower().strip()
        last_name = p_name_lower.split()[-1] if p_name_lower else ""
        p_val_entry = player_values_map.get(p_name_lower) or player_values_map.get(last_name)
        if isinstance(p_val_entry, dict):
            p_mv = p_val_entry.get("eur")
            p_tm_id = p_val_entry.get("tm_id")
        else:
            p_mv = p_val_entry
            p_tm_id = None
        p_mv_fmt = f"€{p_mv:.1f}M" if p_mv is not None and p_mv >= 1.0 else (f"€{int(p_mv*1000)}k" if p_mv is not None and p_mv > 0 else None)

        squad.append({
            "id": pid,
            "tm_id": p_tm_id,
            "name": p.get("name"),
            "shirt": p.get("shirt"),
            "position": p.get("position"),
            "photo_url": photo_url,
            "appearances": apps,
            "starts": starts,
            "goals": goals,
            "assists": assists,
            "yellow_cards": yc,
            "red_cards": rc,
            "country": p.get("country"),
            "captain": p.get("captain", False),
            "market_value_eur": p_mv,
            "market_value_formatted": p_mv_fmt,
        })

    # Sort squad: by position order, then by market value desc, then by appearances desc
    pos_order = {"G": 0, "GK": 0, "D": 1, "DF": 1, "M": 2, "MF": 2, "F": 3, "FW": 3}
    squad.sort(key=lambda x: (
        pos_order.get(x.get("position", ""), 4),
        -(x.get("market_value_eur") or 0),
        -(x.get("appearances") or 0),
        -(x.get("goals") or 0),
        x.get("shirt") if x.get("shirt") is not None else 999
    ))

    team_resp = dict(team_meta)
    team_resp["market_value"] = tm_team_data

    return {
        "team": team_resp,
        "season": season,
        "record": {"wins": wins, "draws": draws, "losses": losses, "played": len(matches_list), "gf": gf, "ga": ga},
        "market_value": tm_team_data,
        "matches": matches_list,
        "next_match": next_match,
        "squad": squad,
    }


TEAM_ID_TO_TM_CLUB_ID = {
    1: 11,    # Arsenal
    2: 405,   # Aston Villa
    4: 631,   # Chelsea
    5: 990,   # Coventry City
    6: 873,   # Crystal Palace
    7: 29,    # Everton
    8: 677,   # Ipswich Town
    9: 399,   # Leeds United
    10: 31,   # Liverpool
    11: 281,  # Manchester City
    12: 985,  # Manchester United
    13: 1003, # Leicester City
    15: 703,  # Nottingham Forest
    18: 350,  # Sheffield United
    20: 180,  # Southampton
    21: 148,  # Tottenham Hotspur
    23: 762,  # Newcastle United
    25: 379,  # West Ham United
    26: 1003, # Leicester City
    29: 289,  # Sunderland
    34: 931,  # Fulham
    38: 543,  # Wolverhampton Wanderers
    41: 3008, # Hull City
    43: 1132, # Burnley
    90: 1132, # Burnley
    127: 989, # Bournemouth
    130: 1148,# Brentford
    131: 1237,# Brighton & Hove Albion
    163: 1031,# Luton Town
}


def _parse_tm_fee(fee_str: str) -> Tuple[float, str, str]:
    if not fee_str:
        return 0.0, "-", "Bilinmiyor"
    s = fee_str.strip().lower()
    if "free" in s or "ablösefrei" in s:
        return 0.0, "Bedelsiz", "Serbest"
    if "end of loan" in s or "leih-ende" in s:
        return 0.0, "Kira Sonu", "Kiradan Geri Dönüş"
    if s.startswith("loan") or "leihe" in s:
        m = re.search(r"€([\d\.]+)\s*(m|k|th)", s)
        if m:
            val = float(m.group(1))
            unit = m.group(2)
            eur = round(val if unit == "m" else val / 1000.0, 2)
            return eur, f"Kiralık (€{eur:.1f}M)", "Kiralık"
        return 0.0, "Kiralık", "Kiralık"

    m = re.search(r"€([\d\.]+)\s*(m|k|th)", s)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        eur = round(val if unit == "m" else val / 1000.0, 2)
        fmt = f"€{eur:.1f}M" if eur >= 1.0 else f"€{int(eur*1000)}k"
        return eur, fmt, "Bonservis"

    return 0.0, fee_str.strip(), "Diğer"


def fetch_club_transfers_from_tm(tm_club_id: int, season_year: int, team_id: int, team_name: str) -> Dict[str, Any]:
    url = f"https://www.transfermarkt.com/club/transfers/verein/{tm_club_id}/saison_id/{season_year}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })
    try:
        html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error downloading Transfermarkt transfers HTML for tm_club_id={tm_club_id}, season={season_year}: {e}")
        return {
            "team_id": team_id,
            "tm_club_id": tm_club_id,
            "team_name": team_name,
            "season": f"{season_year}_{str(season_year+1)[2:]}",
            "summary": {
                "total_spent_eur": 0, "total_spent_formatted": "€0",
                "total_income_eur": 0, "total_income_formatted": "€0",
                "net_balance_eur": 0, "net_balance_formatted": "€0",
                "arrivals_count": 0, "departures_count": 0
            },
            "arrivals": [],
            "departures": []
        }

    soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
    arrivals, departures = [], []
    season_str = f"{str(season_year)[2:]}/{str(season_year+1)[2:]}"

    conn = sqlite3.connect(DATA_DIR / "premier_league.db")
    conn.row_factory = sqlite3.Row

    if soup:
        for b in soup.select(".box"):
            h2 = b.select_one("h2")
            if not h2:
                continue
            title = h2.get_text(strip=True)
            is_arr = "Arrivals" in title
            is_dep = "Departures" in title
            if not (is_arr or is_dep):
                continue

            target_list = arrivals if is_arr else departures
            direction = "in" if is_arr else "out"

            for r in b.select("table.items > tbody > tr"):
                name_el = r.select_one(".hauptlink a")
                if not name_el:
                    continue
                player_name = name_el.get_text(strip=True)
                p_href = name_el.get("href", "")
                pid_m = re.search(r"/spieler/(\d+)", p_href)
                player_id = pid_m.group(1) if pid_m else None

                # Position
                tables = r.select("table.inline-table")
                pos = "-"
                if tables:
                    tds = tables[0].select("tr td")
                    if len(tds) >= 2:
                        pos = tds[-1].get_text(strip=True)

                # Age
                age_el = r.select_one("td.zentriert")
                age_val = None
                if age_el and age_el.get_text(strip=True).isdigit():
                    age_val = int(age_el.get_text(strip=True))

                # Counterpart
                counterpart = "Bilinmiyor"
                counterpart_cid = None
                counterpart_badge = None
                if len(tables) > 1:
                    cp_a = tables[1].select_one(".hauptlink a")
                    if cp_a:
                        counterpart = cp_a.get_text(strip=True)
                        cid_m = re.search(r"/verein/(\d+)", cp_a.get("href", ""))
                        if cid_m:
                            counterpart_cid = int(cid_m.group(1))
                    cp_img = tables[1].select_one("img.tiny_wappen")
                    if cp_img:
                        counterpart_badge = cp_img.get("src")

                fee_el = r.select_one(".rechts a, .rechts")
                fee_str = fee_el.get_text(strip=True) if fee_el else "-"
                fee_eur, fee_fmt, t_type = _parse_tm_fee(fee_str)

                # Look up market value if exists in db
                mv_eur = 0.0
                mv_fmt = "—"
                if player_id:
                    try:
                        row = conn.execute("SELECT market_value_eur FROM player_market_values WHERE player_id = ? ORDER BY season DESC LIMIT 1", (player_id,)).fetchone()
                        if row and row["market_value_eur"]:
                            mv_eur = round(row["market_value_eur"] / 1000.0, 2)
                            mv_fmt = f"€{mv_eur:.1f}M" if mv_eur >= 1.0 else f"€{int(mv_eur*1000)}k"
                    except Exception:
                        pass

                transfer_id = None
                if fee_el and fee_el.name == "a":
                    t_href = fee_el.get("href", "")
                    t_m = re.search(r"/transfer_id/(\d+)", t_href)
                    if t_m:
                        transfer_id = t_m.group(1)

                target_list.append({
                    "id": transfer_id or f"{player_id or 0}_{direction}_{season_year}",
                    "player_id": player_id,
                    "player_name": player_name,
                    "position": pos,
                    "age": age_val,
                    "counterpart_club_name": counterpart,
                    "counterpart_club_id": counterpart_cid,
                    "counterpart_club_badge": counterpart_badge,
                    "direction": direction,
                    "transfer_type": t_type,
                    "fee_eur": fee_eur,
                    "fee_formatted": fee_fmt,
                    "market_value_eur": mv_eur,
                    "market_value_formatted": mv_fmt,
                    "date": f"{season_year}-07-01",
                    "date_formatted": f"1 Tem {season_year}",
                    "season": season_str
                })

    conn.close()

    spent = round(sum(x["fee_eur"] for x in arrivals), 2)
    income = round(sum(x["fee_eur"] for x in departures), 2)
    net = round(income - spent, 2)

    team_info = teams_dict.get(team_id, {})
    return {
        "team_id": team_id,
        "tm_club_id": tm_club_id,
        "team_name": team_name or team_info.get("name"),
        "team_badge": team_info.get("badge") or f"/badges/{team_id}.svg",
        "season": f"{season_year}_{str(season_year+1)[2:]}",
        "summary": {
            "total_spent_eur": spent,
            "total_spent_formatted": f"€{spent:.1f}M" if spent >= 1.0 else f"€{int(spent*1000)}k",
            "total_income_eur": income,
            "total_income_formatted": f"€{income:.1f}M" if income >= 1.0 else f"€{int(income*1000)}k",
            "net_balance_eur": net,
            "net_balance_formatted": f"+€{net:.1f}M" if net > 0 else (f"-€{abs(net):.1f}M" if net < 0 else "€0"),
            "arrivals_count": len(arrivals),
            "departures_count": len(departures)
        },
        "arrivals": arrivals,
        "departures": departures
    }


@app.get("/api/teams/{team_id}/transfers")
async def get_team_transfers(team_id: int, season: Optional[str] = None):
    """
    Returns verified Transfermarkt transfer history (arrivals and departures)
    with fees, loan types, and counterparty clubs for the requested season.
    """
    conn = sqlite3.connect(DATA_DIR / "premier_league.db")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_season_transfers_cache (
                team_id INTEGER,
                season TEXT,
                tm_club_id INTEGER,
                data_json TEXT,
                updated_at TEXT,
                PRIMARY KEY (team_id, season)
            )
        """)
        conn.commit()

        season_key = (season or "2026_27").strip()
        if season_key == "all":
            season_key = "2026_27"

        # Check season cache
        cache_row = conn.execute(
            "SELECT data_json FROM team_season_transfers_cache WHERE team_id = ? AND season = ?",
            (team_id, season_key)
        ).fetchone()
        if cache_row and cache_row["data_json"]:
            try:
                return json.loads(cache_row["data_json"])
            except Exception:
                pass

        # Resolve tm_club_id
        tm_row = conn.execute(
            "SELECT tm_club_id FROM team_market_values WHERE team_id = ? LIMIT 1",
            (team_id,)
        ).fetchone()
        tm_club_id = tm_row["tm_club_id"] if tm_row else TEAM_ID_TO_TM_CLUB_ID.get(team_id)
        if not tm_club_id:
            raise HTTPException(status_code=404, detail="Transfermarkt club ID not found for team")

        team_info = teams_dict.get(team_id, {})
        team_name = team_info.get("name", "")

        # If 2026_27 and already in team_transfers_cache, use it!
        if season_key == "2026_27":
            old_row = conn.execute("SELECT data_json FROM team_transfers_cache WHERE team_id = ?", (team_id,)).fetchone()
            if old_row and old_row["data_json"]:
                data = json.loads(old_row["data_json"])
                conn.execute(
                    "INSERT OR REPLACE INTO team_season_transfers_cache (team_id, season, tm_club_id, data_json, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
                    (team_id, season_key, tm_club_id, old_row["data_json"])
                )
                conn.commit()
                return data

        # Scrape and cache for requested season
        try:
            season_year = int(season_key.split("_")[0])
        except Exception:
            season_year = 2026

        result = fetch_club_transfers_from_tm(tm_club_id, season_year, team_id, team_name)
        conn.execute(
            "INSERT OR REPLACE INTO team_season_transfers_cache (team_id, season, tm_club_id, data_json, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (team_id, season_key, tm_club_id, json.dumps(result))
        )
        conn.commit()
        return result
    finally:
        conn.close()



@app.get("/api/teams/tactics")
def get_team_tactics(team_id: int, season: Optional[str] = "all"):
    """Returns a team-level tactical profile and same-season league benchmarks."""
    if team_id not in teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_tactical_profile(team_id, season or "all")


@app.get("/api/teams/attacking-leaders")
def get_team_attacking_leaders_endpoint(team_id: int, season: Optional[str] = "all"):
    """Return the team's top three players by explainable attacking rating."""
    if team_id not in teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_attacking_leaders(team_id, season or "all")


@app.get("/api/teams/scenarios")
def get_team_scenarios(team_id: int, season: Optional[str] = "all"):
    """Returns shot and corner rates split by the live score state."""
    if team_id not in teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_scenario_profile(team_id, season or "all")


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

    if season == "2026_27":
        staff_path = DATA_DIR / "processed" / "team_staff.json"
        if staff_path.exists():
            try:
                with staff_path.open("r", encoding="utf-8") as sf:
                    staff_data = json.load(sf)
                    for tid_str, tdata in staff_data.get("2026_27", {}).items():
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


@app.get("/api/players")
def get_players(team_id: Optional[int] = None, search: Optional[str] = None, season: Optional[str] = None, limit: int = 100):
    """Returns player directory with optional filters including season-accurate club rosters."""
    result = all_players
    if season and season != "all":
        s_map = get_season_players_map(season)
        updated_result = []
        for p in result:
            pid = p.get("id")
            if pid in s_map:
                p_copy = dict(p)
                p_copy["teamId"] = s_map[pid]["teamId"]
                if s_map[pid]["teamName"]:
                    p_copy["teamName"] = s_map[pid]["teamName"]
                updated_result.append(p_copy)
        result = updated_result

    if team_id:
        result = [p for p in result if p.get("teamId") == team_id]
    if search:
        s = search.lower()
        result = [p for p in result if s in p.get("name", "").lower() or s in p.get("teamName", "").lower()]

    return {"players": result[:limit], "total": len(result)}


@app.get("/api/players/profile")
def get_player_profile(player_id: int, season: Optional[str] = "all"):
    """
    Returns player profile and their match-by-match preview log:
    including opponent, score, minutes played, goals, and assists.
    """
    player = next((p for p in all_players if p["id"] == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    raw_logs = get_player_match_logs(player_id)
    if season and season != "all":
        logs = [m for m in raw_logs if m.get("season") == season]
    else:
        logs = raw_logs

    # Clone player dict and ensure teamId and teamName match the active season
    player_data = dict(player)
    season_order = {'2022_23': 0, '2023_24': 0.5, '2024_25': 1, '2025_26': 2, '2026_27': 3}
    active_logs = logs if logs else raw_logs
    if active_logs:
        sorted_active = sorted(
            active_logs, 
            key=lambda x: (season_order.get(x.get("season", ""), 0), float(x.get("gameweek") or 0))
        )
        latest_match = sorted_active[-1]
        if latest_match.get("team_id"):
            player_data["teamId"] = latest_match["team_id"]
    # Fetch authentic Transfermarkt player market value
    tm_mv = None
    p_name = player_data.get("name") or f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}".strip()
    try:
        conn = sqlite3.connect(DATA_DIR / "premier_league.db")
        conn.row_factory = sqlite3.Row
        last_name = p_name.split()[-1] if p_name else ""
        row = conn.execute(
            "SELECT player_id, market_value, market_value_eur, position, age, nationality FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
            (p_name, f"%{last_name}%")
        ).fetchone()
        if row:
            mv_eur = row["market_value_eur"]
            tm_mv = {
                "tm_id": row["player_id"],
                "market_value_eur": mv_eur,
                "formatted": f"€{mv_eur:,.1f}M" if mv_eur >= 1.0 else f"€{int(mv_eur*1000)}k"
            }
        conn.close()
    except Exception as e:
        logger.warning(f"Error fetching player market value: {e}")

    player_data["market_value"] = tm_mv

    tot_mins = sum(m.get("minutes_played", 0) for m in logs)
    tot_goals = sum(m.get("goals", 0) for m in logs)
    tot_assists = sum(m.get("assists", 0) for m in logs)

    bookings_map = get_match_bookings_map()
    pos = player.get("position") or "M"

    enriched_matches = []
    valid_ratings = []
    for m in logs:
        m_copy = dict(m)
        m_score = calculate_single_match_score(m_copy, pos, bookings_map, player_id)
        if m_score is not None and m_score.get("overall") is not None:
            m_copy["rating"] = m_score["overall"]
            valid_ratings.append(m_score["overall"])
        else:
            m_copy["rating"] = None
        enriched_matches.append(m_copy)

    avg_rating = round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else None

    return {
        "player": player_data,
        "season": season,
        "season_stats": {
            "appearances": len(logs),
            "minutes": tot_mins,
            "goals": tot_goals,
            "assists": tot_assists,
            "average_rating": avg_rating,
            "rated_matches_count": len(valid_ratings),
        },
        "matches": enriched_matches,
    }


TR_MONTHS = {
    '01': 'Oca', '02': 'Şub', '03': 'Mar', '04': 'Nis', '05': 'May', '06': 'Haz',
    '07': 'Tem', '08': 'Ağu', '09': 'Eyl', '10': 'Eki', '11': 'Kas', '12': 'Ara'
}

def _format_date_tr(iso_date: str) -> str:
    try:
        parts = iso_date.split('-')
        return f"{int(parts[2])} {TR_MONTHS.get(parts[1], parts[1])} {parts[0]}"
    except Exception:
        return iso_date

def _format_player_mv(mv_eur: Optional[float]) -> str:
    if mv_eur is None:
        return "—"
    if mv_eur >= 1000.0:
        return f"€{mv_eur/1000:.2f}B"
    if mv_eur >= 1.0:
        return f"€{mv_eur:,.1f}M"
    return f"€{int(mv_eur * 1000)}k"


@app.get("/api/players/{player_id}/market-value-history")
def get_player_market_value_history(player_id: str, name: Optional[str] = None):
    """
    Returns authentic career market value progression curve & chronological history
    for a player, sourced from Transfermarkt career evaluations with SQLite fallback.
    """
    conn = sqlite3.connect(DATA_DIR / "premier_league.db")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_market_value_history_cache (
                tm_id TEXT PRIMARY KEY,
                player_name TEXT,
                data_json TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

        # 1. Resolve Transfermarkt player record
        tm_row = conn.execute(
            "SELECT * FROM player_market_values WHERE player_id = ? ORDER BY season DESC LIMIT 1",
            (str(player_id),)
        ).fetchone()

        if not tm_row and name:
            last = name.split()[-1] if name else ""
            tm_row = conn.execute(
                "SELECT * FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
                (name, f"%{last}%")
            ).fetchone()

        if not tm_row:
            # Check all_players registry by ID
            pl_match = next((p for p in all_players if str(p.get("id")) == str(player_id)), None)
            if pl_match:
                pname = pl_match.get("name") or f"{pl_match.get('firstName', '')} {pl_match.get('lastName', '')}".strip()
                last = pname.split()[-1] if pname else ""
                tm_row = conn.execute(
                    "SELECT * FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
                    (pname, f"%{last}%")
                ).fetchone()

        tm_id = str(tm_row["player_id"]) if tm_row else (str(player_id) if str(player_id).isdigit() and len(str(player_id)) >= 5 else None)
        resolved_name = tm_row["name"] if tm_row else (name or f"Oyuncu {player_id}")
        resolved_pos = tm_row["position"] if tm_row else None
        resolved_team_id = tm_row["team_id"] if tm_row else None

        # 2. Check SQLite cache
        cached_data = None
        if tm_id:
            c_row = conn.execute(
                "SELECT data_json FROM player_market_value_history_cache WHERE tm_id = ?",
                (tm_id,)
            ).fetchone()
            if c_row and c_row["data_json"]:
                try:
                    cached_data = json.loads(c_row["data_json"])
                except Exception:
                    cached_data = None

        # 3. If not cached, fetch from Transfermarkt API
        if not cached_data and tm_id:
            try:
                import urllib.request
                url = f"https://transfermarkt-api.fly.dev/players/{tm_id}/market_value"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    cached_data = json.loads(resp.read().decode())
                    conn.execute(
                        "INSERT OR REPLACE INTO player_market_value_history_cache (tm_id, player_name, data_json, updated_at) VALUES (?, ?, ?, datetime('now'))",
                        (tm_id, resolved_name, json.dumps(cached_data))
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not fetch TM market value for player {tm_id}: {e}")

        # 4. Parse history points
        raw_history = (cached_data or {}).get("marketValueHistory", [])
        history_points = []
        prev_val = None

        if raw_history:
            for item in raw_history:
                mv_raw = item.get("marketValue", 0)
                mv_eur = round(mv_raw / 1_000_000, 2)
                chg_pct = round(((mv_eur - prev_val) / prev_val) * 100, 1) if prev_val and prev_val > 0 else None
                chg_diff = round(mv_eur - prev_val, 2) if prev_val is not None else None
                prev_val = mv_eur
                dt = item.get("date", "")

                history_points.append({
                    "date": dt,
                    "year": dt.split("-")[0] if "-" in dt else "",
                    "date_formatted": _format_date_tr(dt),
                    "age": item.get("age"),
                    "club_name": item.get("clubName") or "Kulüp",
                    "market_value": mv_raw,
                    "market_value_eur": mv_eur,
                    "formatted": _format_player_mv(mv_eur),
                    "change_pct": chg_pct,
                    "change_diff": chg_diff,
                })
        else:
            # Fallback to SQLite seasonal records
            seasonal_rows = conn.execute(
                "SELECT season, market_value, market_value_eur, age FROM player_market_values WHERE player_id = ? OR LOWER(name) = LOWER(?) ORDER BY season ASC",
                (tm_id or "", resolved_name)
            ).fetchall()
            for s_row in seasonal_rows:
                mv_eur = s_row["market_value_eur"]
                chg_pct = round(((mv_eur - prev_val) / prev_val) * 100, 1) if prev_val and prev_val > 0 else None
                chg_diff = round(mv_eur - prev_val, 2) if prev_val is not None else None
                prev_val = mv_eur
                s_label = s_row["season"].replace("_", "/")
                history_points.append({
                    "date": s_row["season"],
                    "year": s_row["season"].split("_")[0],
                    "date_formatted": f"{s_label} Sezonu",
                    "age": s_row["age"],
                    "club_name": "Premier League",
                    "market_value": s_row["market_value"],
                    "market_value_eur": mv_eur,
                    "formatted": _format_player_mv(mv_eur),
                    "change_pct": chg_pct,
                    "change_diff": chg_diff,
                })

        first_point = history_points[0] if history_points else None
        current_point = history_points[-1] if history_points else None
        peak_point = max(history_points, key=lambda x: x["market_value_eur"]) if history_points else None

        total_growth_pct = None
        total_growth_diff = None
        if first_point and current_point and first_point["market_value_eur"] > 0:
            total_growth_pct = round(((current_point["market_value_eur"] - first_point["market_value_eur"]) / first_point["market_value_eur"]) * 100, 1)
            total_growth_diff = round(current_point["market_value_eur"] - first_point["market_value_eur"], 2)

        team_meta = teams_dict.get(resolved_team_id, {}) if resolved_team_id else {}
        team_badge = team_meta.get("badge") or (f"/badges/{resolved_team_id}.svg" if resolved_team_id else None)

        return {
            "player_id": player_id,
            "tm_id": tm_id,
            "name": resolved_name,
            "position": resolved_pos,
            "team_id": resolved_team_id,
            "team_name": team_meta.get("name"),
            "team_badge": team_badge,
            "current_value": current_point,
            "peak_value": peak_point,
            "first_value": first_point,
            "total_growth_pct": total_growth_pct,
            "total_growth_diff": total_growth_diff,
            "evaluations_count": len(history_points),
            "history": history_points,
        }
    finally:
        conn.close()


@app.get("/api/match/{match_id}/details")
def get_match_full_details(match_id: int):
    """
    Returns full match lineup rosters, substitutes, tactical formations,
    and play-by-play events.
    """
    if match_id in _completed_match_details_cache:
        return _completed_match_details_cache[match_id]

    raw_details = DATA_DIR / "raw" / "matches" / f"{match_id}_details.json"
    raw_stream = DATA_DIR / "raw" / "matches" / f"{match_id}_stream.json"

    raw_stats = DATA_DIR / "raw" / "matches" / f"{match_id}_stats.json"

    lineups = []
    metadata = {}
    team_stats = []
    player_stats = {"home": [], "away": []}

    # Query DB for match xG and score stats if available
    h_xg = None
    a_xg = None
    tot_xg = None
    xg_source = None
    xg_quality = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""SELECT x.provider, x.home_xg, x.away_xg, x.xg_quality
                          FROM matches m LEFT JOIN external_match_xg x ON x.match_id = m.match_id
                          WHERE m.match_id = ?""", (match_id,))
        db_match = cursor.fetchone()
        conn.close()
        if db_match:
            h_xg = round(float(db_match["home_xg"]), 2) if db_match["home_xg"] is not None else None
            a_xg = round(float(db_match["away_xg"]), 2) if db_match["away_xg"] is not None else None
            tot_xg = round(h_xg + a_xg, 2) if h_xg is not None and a_xg is not None else None
            xg_source = db_match["provider"] if h_xg is not None and a_xg is not None else None
            xg_quality = db_match["xg_quality"]
    except Exception as e:
        logger.warning(f"Error fetching match {match_id} from SQLite: {e}")

    d = {}
    if raw_details.exists():
        with open(raw_details, "r", encoding="utf-8") as f:
            d = json.load(f)

        metadata = {
            "match_id": match_id,
            "kickoff_label": d.get("kickoff", {}).get("label"),
            "ground": d.get("ground", {}).get("name"),
            "attendance": d.get("attendance"),
            "referee": d.get("matchOfficials", [{}])[0].get("matchOfficial", {}).get("name", {}).get("display") if d.get("matchOfficials") else None,
            "halfTimeScore": d.get("halfTimeScore"),
            "home_xg": h_xg,
            "away_xg": a_xg,
            "total_xg": tot_xg,
            "xg_source": xg_source,
            "xg_quality": xg_quality,
        }

        # Parse match events (goals, assists, cards, subs) from details
        det_events = d.get("events", [])
        sub_on = {}
        sub_off = {}
        goals = {}
        assists = {}
        yc = {}
        rc = {}
        for ev in det_events:
            etype = ev.get("type")
            pid = ev.get("personId")
            clk = ev.get("clock", {}).get("label", "")
            min_v = 0
            if clk:
                try:
                    min_v = int(clk.split("'")[0].split("+")[0])
                except Exception:
                    pass
            if etype == "G" and pid:
                goals[pid] = goals.get(pid, 0) + 1
            elif etype == "AS" and pid:
                assists[pid] = assists.get(pid, 0) + 1
            elif etype == "S" and pid:
                if ev.get("description") == "ON":
                    sub_on[pid] = min_v
                elif ev.get("description") == "OFF":
                    sub_off[pid] = min_v
            elif etype == "B" and pid:
                if ev.get("description") == "Y":
                    yc[pid] = yc.get(pid, 0) + 1
                elif ev.get("description") == "R":
                    rc[pid] = rc.get(pid, 0) + 1

        # Parse detailed stream events (shots, fouls, penalties, offsides, saves)
        fouls_lost = {}
        fouls_won = {}
        shots = {}
        shots_ot = {}
        offsides = {}
        pens_won = {}
        pens_conceded = {}
        pens_missed = {}
        saves = {}

        stream_events = []
        if raw_stream.exists():
            try:
                with open(raw_stream, "r", encoding="utf-8") as f:
                    st = json.load(f)
                    stream_events = st.get("events", {}).get("content", [])
            except Exception:
                stream_events = []
        events = stream_events

        # Find team starting goalkeepers and player team mapping
        player_team_map = {}
        team_gk_map = {}
        for idx, tl in enumerate(d.get("teamLists", [])):
            if not tl or not isinstance(tl, dict):
                continue
            tid = tl.get("teamId")
            for p in tl.get("lineup", []):
                pid = p.get("id")
                if pid:
                    player_team_map[pid] = tid
                    pos = p.get("matchPosition") or p.get("info", {}).get("position") or "M"
                    if pos in ("G", "GK") and tid not in team_gk_map:
                        team_gk_map[tid] = pid
            for p in tl.get("substitutes", []):
                pid = p.get("id")
                if pid:
                    player_team_map[pid] = tid

        team_ids_list = list(team_gk_map.keys())

        for se in stream_events:
            stype = se.get("type", "")
            stext = se.get("text", "")
            pids = se.get("playerIds", [])
            if not pids:
                continue
            p0 = pids[0]
            if stype == "free kick lost":
                fouls_lost[p0] = fouls_lost.get(p0, 0) + 1
            elif stype == "free kick won":
                fouls_won[p0] = fouls_won.get(p0, 0) + 1
            elif stype in ["goal", "attempt saved", "miss", "attempt blocked"]:
                shots[p0] = shots.get(p0, 0) + 1
                if stype in ["goal", "attempt saved"]:
                    shots_ot[p0] = shots_ot.get(p0, 0) + 1
                if stype == "attempt saved":
                    # The defending opponent goalkeeper gets a save
                    shooter_tid = player_team_map.get(p0)
                    opp_tid = next((t for t in team_ids_list if t != shooter_tid), None)
                    if opp_tid and opp_tid in team_gk_map:
                        opp_gk_id = team_gk_map[opp_tid]
                        saves[opp_gk_id] = saves.get(opp_gk_id, 0) + 1
            elif stype == "offside":
                offsides[p0] = offsides.get(p0, 0) + 1
            elif stype == "penalty lost":
                pens_conceded[p0] = pens_conceded.get(p0, 0) + 1
            elif stype == "penalty won":
                pens_won[p0] = pens_won.get(p0, 0) + 1
            elif stype in ["penalty miss", "penalty saved"] or "penalty missed" in stext.lower():
                pens_missed[p0] = pens_missed.get(p0, 0) + 1

        teams_info = d.get("teams", [])
        h_score_val = teams_info[0].get("score") if len(teams_info) > 0 else None
        a_score_val = teams_info[1].get("score") if len(teams_info) > 1 else None
        is_match_completed = (h_score_val is not None and a_score_val is not None)

        for idx, tl in enumerate(d.get("teamLists", [])):
            if not tl or not isinstance(tl, dict):
                continue
            t_obj = teams_info[idx].get("team", {}) if idx < len(teams_info) else {}
            score_val = teams_info[idx].get("score") if idx < len(teams_info) else None
            opp_score_val = teams_info[1 - idx].get("score") if len(teams_info) > 1 and (1 - idx) < len(teams_info) else 0

            starters = []
            team_overall_sum = 0.0
            team_attack_sum = 0.0
            team_defense_sum = 0.0
            team_cards_risk_sum = 0.0
            starter_count = 0

            for p in tl.get("lineup", []):
                pid = p.get("id")
                reg_p = player_registry_map.get(int(pid), {}) if pid else {}
                photo = resolve_player_photo(pid, reg_p)
                pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"
                
                # Dynamic player rating calculation
                p_rat = {}
                if pid:
                    try:
                        p_rat = get_player_dynamic_rating(pid, as_of_match_id=match_id)
                    except Exception:
                        p_rat = {}

                p_mins = sub_off.get(pid, 90)
                p_stats = {
                    "minutes": p_mins,
                    "goals": goals.get(pid, 0),
                    "assists": assists.get(pid, 0),
                    "shots": shots.get(pid, 0),
                    "shots_ontarget": shots_ot.get(pid, 0),
                    "fouls_committed": fouls_lost.get(pid, 0),
                    "fouls_won": fouls_won.get(pid, 0),
                    "offsides": offsides.get(pid, 0),
                    "yellow_cards": yc.get(pid, 0),
                    "red_cards": rc.get(pid, 0),
                    "penalties_won": pens_won.get(pid, 0),
                    "penalties_conceded": pens_conceded.get(pid, 0),
                    "penalties_missed": pens_missed.get(pid, 0),
                    "saves": saves.get(pid, 0),
                }

                if is_match_completed:
                    perf = calculate_detailed_match_score(
                        p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0
                    )
                    overall_r = perf["overall"]
                    att_r = perf["attack"]
                    def_r = perf["defense"]
                    match_r = perf["overall"]
                else:
                    overall_r = p_rat.get("overall_rating", 6.0)
                    att_r = p_rat.get("attack_rating", 6.0)
                    def_r = p_rat.get("defense_rating", 6.0)
                    match_r = None

                cards_r = p_rat.get("cards_risk", 3.0)

                team_overall_sum += overall_r
                team_attack_sum += att_r
                team_defense_sum += def_r
                team_cards_risk_sum += cards_r
                starter_count += 1

                starters.append({
                    "id": pid,
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": pos,
                    "captain": p.get("captain", False),
                    "country": p.get("nationalTeam", {}).get("country"),
                    "photo_url": photo,
                    "rating": overall_r,
                    "match_rating": match_r,
                    "form_rating": p_rat.get("overall_rating", 6.0),
                    "is_match_rating": is_match_completed,
                    "attack_rating": att_r,
                    "defense_rating": def_r,
                    "cards_risk": cards_r,
                    "form_label": p_rat.get("form_label", "Normal"),
                    "trend": p_rat.get("trend", "stable"),
                    "penalties_conceded": pens_conceded.get(pid, 0),
                    "penalties_won": pens_won.get(pid, 0),
                    "penalties_missed": pens_missed.get(pid, 0),
                })

            subs = []
            for p in tl.get("substitutes", []):
                pid = p.get("id")
                reg_p = player_registry_map.get(int(pid), {}) if pid else {}
                photo = resolve_player_photo(pid, reg_p)
                pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"
                
                p_rat = {}
                if pid:
                    try:
                        p_rat = get_player_dynamic_rating(pid, as_of_match_id=match_id)
                    except Exception:
                        p_rat = {}

                p_mins = (90 - sub_on.get(pid, 75)) if pid in sub_on else 0
                p_stats = {
                    "minutes": p_mins,
                    "goals": goals.get(pid, 0),
                    "assists": assists.get(pid, 0),
                    "shots": shots.get(pid, 0),
                    "shots_ontarget": shots_ot.get(pid, 0),
                    "fouls_committed": fouls_lost.get(pid, 0),
                    "fouls_won": fouls_won.get(pid, 0),
                    "offsides": offsides.get(pid, 0),
                    "yellow_cards": yc.get(pid, 0),
                    "red_cards": rc.get(pid, 0),
                    "penalties_won": pens_won.get(pid, 0),
                    "penalties_conceded": pens_conceded.get(pid, 0),
                    "penalties_missed": pens_missed.get(pid, 0),
                    "saves": saves.get(pid, 0),
                }

                if is_match_completed and p_mins > 0:
                    perf = calculate_detailed_match_score(
                        p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0
                    )
                    sub_r = perf["overall"]
                    match_r = perf["overall"]
                else:
                    sub_r = p_rat.get("overall_rating", 6.0)
                    match_r = None

                subs.append({
                    "id": pid,
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": pos,
                    "photo_url": photo,
                    "rating": sub_r,
                    "match_rating": match_r,
                    "form_rating": p_rat.get("overall_rating", 6.0),
                    "is_match_rating": is_match_completed,
                    "cards_risk": p_rat.get("cards_risk", 3.0),
                    "form_label": p_rat.get("form_label", "Normal"),
                    "trend": p_rat.get("trend", "stable"),
                    "penalties_conceded": pens_conceded.get(pid, 0),
                    "penalties_won": pens_won.get(pid, 0),
                    "penalties_missed": pens_missed.get(pid, 0),
                })

            # Sort starters & substitutes by position: Kaleci (GK) -> Savunma (DEF) -> Orta Saha (MID) -> Forvet (FWD)
            starters.sort(key=lambda x: (get_position_order(x.get("position")), x.get("shirt") or 99))
            subs.sort(key=lambda x: (get_position_order(x.get("position")), x.get("shirt") or 99))

            formation_obj = tl.get("formation") or {}
            if isinstance(formation_obj, dict):
                form_label = formation_obj.get("label", "4-3-3")
                form_matrix = formation_obj.get("players", [])
            else:
                form_label = str(formation_obj) if formation_obj else "4-3-3"
                form_matrix = []

            divisor = starter_count if starter_count > 0 else 1
            lineups.append({
                "team_id": tl.get("teamId"),
                "team_name": t_obj.get("name"),
                "score": score_val,
                "formation": form_label,
                "formation_matrix": form_matrix,
                "team_ratings": {
                    "overall": round(team_overall_sum / divisor, 2),
                    "attack": round(team_attack_sum / divisor, 2),
                    "defense": round(team_defense_sum / divisor, 2),
                    "cards_risk": round(team_cards_risk_sum / divisor, 2),
                },
                "starters": starters,
                "substitutes": subs,
            })

    # Team Stats (Comparative 182 Metrics across categories)
    if raw_stats.exists():
        with open(raw_stats, "r", encoding="utf-8") as f:
            s_data = json.load(f)

        t_data = s_data.get("data", {})
        teams_info = d.get("teams", [])
        h_id_str = str(int(teams_info[0].get("team", {}).get("id", 0))) if len(teams_info) > 0 else "0"
        a_id_str = str(int(teams_info[1].get("team", {}).get("id", 0))) if len(teams_info) > 1 else "0"

        hm = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(h_id_str, {}).get("M", [])}
        am = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(a_id_str, {}).get("M", [])}

        def m_pair(key, def_val=0.0):
            return hm.get(key, def_val), am.get(key, def_val)

        h_pass, a_pass = m_pair("total_pass")
        h_acc_p, a_acc_p = m_pair("accurate_pass")
        h_pass_pct = round((h_acc_p / max(1.0, h_pass)) * 100, 1) if h_pass > 0 else 0.0
        a_pass_pct = round((a_acc_p / max(1.0, a_pass)) * 100, 1) if a_pass > 0 else 0.0

        team_stats = [
            {
                "category": "Şut & Hücum Hacmi",
                "items": [
                    {
                        "label": "TheStatsAPI Beklenen Gol (xG)",
                        "home": h_xg if h_xg is not None else "Not Found",
                        "away": a_xg if a_xg is not None else "Not Found",
                        "rawHome": h_xg,
                        "rawAway": a_xg,
                        "isXg": True,
                        "notFound": (h_xg is None and a_xg is None),
                    },
                    {"label": "Toplam Şut", "home": hm.get("total_scoring_att", 0), "away": am.get("total_scoring_att", 0)},
                    {"label": "İsabetli Şut", "home": hm.get("ontarget_scoring_att", 0), "away": am.get("ontarget_scoring_att", 0)},
                    {"label": "İsabetsiz Şut", "home": hm.get("shot_off_target", 0), "away": am.get("shot_off_target", 0)},
                    {"label": "Bloklanan Şut", "home": hm.get("blocked_scoring_att", 0), "away": am.get("blocked_scoring_att", 0)},
                    {"label": "Ceza Sahası İçi Şut", "home": hm.get("attempts_ibox", 0), "away": am.get("attempts_ibox", 0)},
                    {"label": "Ceza Sahası Dışı Şut", "home": hm.get("attempts_obox", 0), "away": am.get("attempts_obox", 0)},
                    {"label": "Yaratılan Net Fırsat", "home": hm.get("big_chance_created", 0), "away": am.get("big_chance_created", 0)},
                    {"label": "Kaçan Net Fırsat", "home": hm.get("big_chance_missed", 0), "away": am.get("big_chance_missed", 0)},
                    {"label": "Rakip Ceza Sahasında Topla Buluşma", "home": hm.get("touches_in_opp_box", 0), "away": am.get("touches_in_opp_box", 0)},
                    {"label": "Kilit Pas / Şut Pası", "home": hm.get("total_att_assist", 0), "away": am.get("total_att_assist", 0)},
                ]
            },
            {
                "category": "Top Hakimiyeti & Pas",
                "items": [
                    {"label": "Topa Sahip Olma", "home": hm.get("possession_percentage", 0), "away": am.get("possession_percentage", 0), "suffix": "%"},
                    {"label": "Toplam Pas", "home": h_pass, "away": a_pass},
                    {"label": "İsabetli Pas", "home": h_acc_p, "away": a_acc_p},
                    {"label": "Pas İsabet Oranı", "home": h_pass_pct, "away": a_pass_pct, "suffix": "%"},
                    {"label": "3. Bölge (Final Third) Pasları", "home": hm.get("total_final_third_passes", 0), "away": am.get("total_final_third_passes", 0)},
                    {"label": "Başarılı 3. Bölge Pasları", "home": hm.get("successful_final_third_passes", 0), "away": am.get("successful_final_third_passes", 0)},
                    {"label": "Toplam Orta / İsabet", "home": f"{int(hm.get('total_cross',0))} ({int(hm.get('accurate_cross',0))})", "away": f"{int(am.get('total_cross',0))} ({int(am.get('accurate_cross',0))})", "rawHome": hm.get("total_cross", 0), "rawAway": am.get("total_cross", 0)},
                    {"label": "Uzun Toplar", "home": hm.get("total_long_balls", 0), "away": am.get("total_long_balls", 0)},
                ]
            },
            {
                "category": "Duran Top & Baskı",
                "items": [
                    {"label": "Kazanılan Korner", "home": hm.get("won_corners", 0), "away": am.get("won_corners", 0)},
                    {"label": "Ceza Sahasına İsabetli Korner", "home": hm.get("accurate_corners_intobox", 0), "away": am.get("accurate_corners_intobox", 0)},
                    {"label": "Toplam Taç", "home": hm.get("total_throws", 0), "away": am.get("total_throws", 0)},
                    {"label": "İsabetli Taç", "home": hm.get("accurate_throws", 0), "away": am.get("accurate_throws", 0)},
                    {"label": "PPDA (Pres Baskı İndeksi)", "home": hm.get("ppda", 0), "away": am.get("ppda", 0)},
                ]
            },
            {
                "category": "Savunma & İkili Mücadele",
                "items": [
                    {"label": "Top Kapma (Kazanılan)", "home": f"{int(hm.get('total_tackle',0))} ({int(hm.get('won_tackle',0))})", "away": f"{int(am.get('total_tackle',0))} ({int(am.get('won_tackle',0))})", "rawHome": hm.get("total_tackle", 0), "rawAway": am.get("total_tackle", 0)},
                    {"label": "Pas Arası (Interception)", "home": hm.get("interception", 0), "away": am.get("interception", 0)},
                    {"label": "Tehlike Uzaklaştırma (Clearance)", "home": hm.get("total_clearance", 0), "away": am.get("total_clearance", 0)},
                    {"label": "Bloklanan Şut & Pas", "home": hm.get("outfielder_block", 0) + hm.get("blocked_pass", 0), "away": am.get("outfielder_block", 0) + am.get("blocked_pass", 0)},
                    {"label": "Sahipsiz Top Kazanma", "home": hm.get("ball_recovery", 0), "away": am.get("ball_recovery", 0)},
                    {"label": "Kazanılan İkili Mücadele", "home": hm.get("duel_won", 0), "away": am.get("duel_won", 0)},
                    {"label": "Kazanılan Hava Topu", "home": hm.get("aerial_won", 0), "away": am.get("aerial_won", 0)},
                ]
            },
            {
                "category": "Disiplin & Kaleci",
                "items": [
                    {"label": "Toplam Kurtarış", "home": hm.get("saves", 0), "away": am.get("saves", 0)},
                    {"label": "Ceza Sahası İçi Kurtarış", "home": hm.get("saved_ibox", 0), "away": am.get("saved_ibox", 0)},
                    {"label": "Yapılan Faul", "home": hm.get("fk_foul_lost", 0), "away": am.get("fk_foul_lost", 0)},
                    {"label": "Alınan Faul", "home": hm.get("fk_foul_won", 0), "away": am.get("fk_foul_won", 0)},
                    {"label": "Ofsayt", "home": hm.get("total_offside", 0), "away": am.get("total_offside", 0)},
                    {"label": "Sarı Kart", "home": hm.get("total_yel_card", 0), "away": am.get("total_yel_card", 0)},
                    {"label": "Kırmızı Kart", "home": hm.get("total_red_card", 0), "away": am.get("total_red_card", 0)},
                ]
            }
        ]
    elif h_xg is not None or a_xg is not None:
        team_stats = [
            {
                "category": "Şut & Hücum Hacmi",
                "items": [
                    {
                        "label": "TheStatsAPI Beklenen Gol (xG)",
                        "home": h_xg if h_xg is not None else "Not Found",
                        "away": a_xg if a_xg is not None else "Not Found",
                        "rawHome": h_xg,
                        "rawAway": a_xg,
                        "isXg": True,
                        "notFound": (h_xg is None and a_xg is None),
                    }
                ]
            }
        ]

    # Populate home & away player cards
    for idx, tl in enumerate(d.get("teamLists", [])):
        if not tl or not isinstance(tl, dict):
            continue
        side = "home" if idx == 0 else "away"
        lineup_p = tl.get("lineup", [])
        subs_p = tl.get("substitutes", [])
        score_val = teams_info[idx].get("score") if idx < len(teams_info) else None
        opp_score_val = teams_info[1 - idx].get("score") if len(teams_info) > 1 and (1 - idx) < len(teams_info) else 0

        # Process starters
        for p in lineup_p:
            pid = p.get("id")
            if not pid:
                continue
            mins = sub_off.get(pid, 90)
            reg_p = player_registry_map.get(int(pid), {}) if pid else {}
            photo = resolve_player_photo(pid, reg_p)
            pos = p.get("matchPosition") or p.get("info", {}).get("position", "M")

            p_stats = {
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
                "saves": saves.get(pid, 0),
            }

            p_rating = 6.0
            p_attack = 6.0
            p_defense = 6.0
            if is_match_completed:
                perf = calculate_detailed_match_score(p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0)
                p_rating = perf["overall"]
                p_attack = perf.get("attack")
                p_defense = perf.get("defense")

            player_stats[side].append({
                "id": pid,
                "name": p.get("name", {}).get("display", "Unknown"),
                "shirt": p.get("matchShirtNumber"),
                "position": pos,
                "is_starter": True,
                "captain": p.get("captain", False),
                "photo_url": photo,
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
                "saves": saves.get(pid, 0),
                "rating": p_rating,
                "attack_rating": p_attack,
                "defense_rating": p_defense,
                "team_score": score_val or 0,
                "opp_score": opp_score_val or 0,
                "match_rating": p_rating if is_match_completed else None,
                "is_match_rating": is_match_completed,
            })

        # Process substitutes who actually played
        for p in subs_p:
            pid = p.get("id")
            if not pid or pid not in sub_on:
                continue
            mins = max(1, 90 - sub_on[pid])
            reg_p = player_registry_map.get(int(pid), {}) if pid else {}
            photo = resolve_player_photo(pid, reg_p)
            pos = p.get("matchPosition") or p.get("info", {}).get("position", "M")

            p_stats = {
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
                "saves": saves.get(pid, 0),
            }

            p_rating = 6.0
            p_attack = 6.0
            p_defense = 6.0
            if is_match_completed:
                perf = calculate_detailed_match_score(p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0)
                p_rating = perf["overall"]
                p_attack = perf.get("attack")
                p_defense = perf.get("defense")

            player_stats[side].append({
                "id": pid,
                "name": p.get("name", {}).get("display", "Unknown"),
                "shirt": p.get("matchShirtNumber"),
                "position": pos,
                "is_starter": False,
                "captain": False,
                "photo_url": photo,
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
                "saves": saves.get(pid, 0),
                "rating": p_rating,
                "attack_rating": p_attack,
                "defense_rating": p_defense,
                "team_score": score_val or 0,
                "opp_score": opp_score_val or 0,
                "match_rating": p_rating if is_match_completed else None,
                "is_match_rating": is_match_completed,
            })

        # Sort player_stats by position: Kaleci -> Savunma -> Orta Saha -> Forvet
        player_stats[side].sort(key=lambda x: (0 if x.get("is_starter") else 1, get_position_order(x.get("position")), x.get("shirt") or 99))

    # Build clean Key Timeline Events
    key_timeline = []
    player_names = {}
    player_photos = {}
    for tl in (d.get("teamLists") or []):
        if not tl or not isinstance(tl, dict):
            continue
        lineup_p = tl.get("lineup") or []
        subs_p = tl.get("substitutes") or []
        for p in (lineup_p + subs_p):
            if not p or not isinstance(p, dict):
                continue
            pid = p.get("id")
            if pid:
                pname = (p.get("name") or {}).get("display") or "Bilinmeyen Oyuncu"
                player_names[pid] = pname
                player_photos[pid] = resolve_player_photo(pid)

    team_names_map = {}
    teams_info = d.get("teams", [])
    for t_item in teams_info:
        t_obj = t_item.get("team", {})
        if t_obj.get("id"):
            team_names_map[int(t_obj["id"])] = t_obj.get("name", "")

    sub_events = {}
    for ev in det_events:
        if ev.get("type") == "S":
            eid = ev.get("id")
            if eid not in sub_events:
                sub_events[eid] = {}
            if ev.get("description") == "ON":
                sub_events[eid]["on"] = ev.get("personId")
            elif ev.get("description") == "OFF":
                sub_events[eid]["off"] = ev.get("personId")

    seen_sub_ids = set()
    for ev in det_events:
        etype = ev.get("type")
        clock_lbl = ev.get("clock", {}).get("label", "")
        minute_display = clock_lbl.split("'")[0] + "'" if "'" in clock_lbl else clock_lbl
        tid = ev.get("teamId")
        tname = team_names_map.get(tid, "")

        if etype == "PS":
            phase = ev.get("phase")
            if phase == "1":
                key_timeline.append({
                    "type": "period_start",
                    "minute": "0'",
                    "label": "Maç Başlangıcı",
                    "description": "1. Yarı Başladı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
            elif phase == "2":
                key_timeline.append({
                    "type": "period_start",
                    "minute": "45'",
                    "label": "2. Yarı Başlangıcı",
                    "description": "2. Yarı Başladı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
        elif etype == "PE":
            phase = ev.get("phase")
            if phase == "1":
                key_timeline.append({
                    "type": "period_end",
                    "minute": minute_display,
                    "label": "İlk Yarı Sonu",
                    "description": "İlk Yarı Tamamlandı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
            elif phase == "2":
                key_timeline.append({
                    "type": "period_end",
                    "minute": minute_display,
                    "label": "Maç Sonu (FT)",
                    "description": "Karşılaşma Sona Erdi",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
        elif etype in ["G", "P", "O"]:
            pid = ev.get("personId")
            aid = ev.get("assistId")
            desc = ev.get("description", "G")
            is_penalty = (etype == "P" or desc == "P")
            is_own_goal = (etype == "O" or desc in ["OG", "O"])
            goal_type = "Penaltı Golü" if is_penalty else ("Kendi Kalesine Gol" if is_own_goal else "Gol")
            h_s = ev.get("score", {}).get("homeScore", 0)
            a_s = ev.get("score", {}).get("awayScore", 0)
            credited_team_id = tid
            if is_own_goal and tid is not None:
                credited_team_id = next(
                    (team_id for team_id in team_names_map if team_id != tid),
                    tid,
                )
            key_timeline.append({
                "type": "goal",
                "goal_type": goal_type,
                "is_penalty": is_penalty,
                "is_own_goal": is_own_goal,
                "minute": minute_display,
                "team_id": credited_team_id,
                "team_name": team_names_map.get(credited_team_id, tname),
                "player_id": pid,
                "player_name": player_names.get(pid, "Bilinmeyen Oyuncu"),
                "photo_url": player_photos.get(pid),
                "assist_id": aid,
                "assist_name": player_names.get(aid) if aid else None,
                "score": f"{h_s} - {a_s}"
            })
        elif etype == "B":
            pid = ev.get("personId")
            card_desc = ev.get("description", "Y")
            key_timeline.append({
                "type": "yellow_card" if card_desc == "Y" else "red_card",
                "minute": minute_display,
                "team_id": tid,
                "team_name": tname,
                "player_id": pid,
                "player_name": player_names.get(pid, "Bilinmeyen Oyuncu"),
                "photo_url": player_photos.get(pid),
            })
        elif etype == "S":
            eid = ev.get("id")
            if eid and eid not in seen_sub_ids:
                seen_sub_ids.add(eid)
                sub_info = sub_events.get(eid, {})
                p_in = sub_info.get("on")
                p_out = sub_info.get("off")
                key_timeline.append({
                    "type": "substitution",
                    "minute": minute_display,
                    "team_id": tid,
                    "team_name": tname,
                    "player_in_id": p_in,
                    "player_in_name": player_names.get(p_in, "Giren Oyuncu"),
                    "player_in_photo": player_photos.get(p_in),
                    "player_out_id": p_out,
                    "player_out_name": player_names.get(p_out, "Çıkan Oyuncu"),
                    "player_out_photo": player_photos.get(p_out),
                })

    # Also capture stoppage / added time and missed penalties from stream events
    for se in events:
        stype = se.get("type", "")
        stext = se.get("text", "")
        time_info = se.get("time", {})
        s_min = time_info.get("label", "")
        if s_min and "'" not in s_min:
            s_min = f"{s_min}'"

        if stype == "added time":
            key_timeline.append({
                "type": "added_time",
                "minute": s_min or "45+'",
                "label": "Uzatma Süresi",
                "description": stext or "Uzatma Süresi İlan Edildi",
            })
        elif stype == "penalty missed" or "penalty missed" in stext.lower() or "penalty saved" in stext.lower():
            pids = se.get("playerIds", [])
            pid = pids[0] if pids else None
            key_timeline.append({
                "type": "penalty_missed",
                "minute": s_min or "-",
                "label": "Kaçan Penaltı",
                "description": stext or "Penaltı Kaçtı",
                "player_id": pid,
                "player_name": player_names.get(pid) if pid else None,
                "photo_url": player_photos.get(pid) if pid else None,
            })

    # Chronologically sort timeline
    def parse_minute_sort(item):
        m = str(item.get("minute", "0")).replace("'", "").strip()
        prio_map = {
            "period_start": 0,
            "added_time": 1,
            "goal": 2,
            "yellow_card": 2,
            "red_card": 2,
            "penalty_missed": 2,
            "substitution": 2,
            "period_end": 3
        }
        prio = prio_map.get(item.get("type"), 2)
        if "+" in m:
            parts = m.split("+")
            try:
                return (float(parts[0]) + float(parts[1]) * 0.01, prio)
            except:
                pass
        try:
            return (float(m), prio)
        except:
            return (0.0, prio)

    key_timeline.sort(key=parse_minute_sort)

    res = {
        "metadata": metadata,
        "lineups": lineups,
        "team_stats": team_stats,
        "player_stats": player_stats,
        "events": events,
        "timeline": key_timeline,
        "odds": get_match_odds_list(match_id),
    }
    if bool(team_stats or events):
        _completed_match_details_cache[match_id] = res
    return res


def get_match_odds_list(match_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bookmaker,
                   home_last_seen, draw_last_seen, away_last_seen,
                   home_open, draw_open, away_open,
                   over_25_last_seen, under_25_last_seen,
                   btts_yes_last_seen, btts_no_last_seen,
                   corners_over_last_seen, corners_under_last_seen,
                   cards_over_last_seen, cards_under_last_seen,
                   fetched_at_utc
            FROM external_match_odds
            WHERE match_id = ?
            ORDER BY CASE 
                WHEN bookmaker = 'Bet365' THEN 1 
                WHEN bookmaker = 'Pinnacle' THEN 2 
                WHEN bookmaker = 'Betfair Exchange' THEN 3 
                WHEN bookmaker = 'Paddy Power' THEN 4 
                ELSE 5 
            END
        """, (match_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"Error fetching odds for match {match_id}: {e}")
        return []


@app.get("/api/match/{match_id}/odds")
def get_match_odds(match_id: int):
    """Returns stored pre-match & closing betting odds across bookmakers for this match."""
    return {"match_id": match_id, "odds": get_match_odds_list(match_id)}


@app.get("/api/model-audit")
def get_model_audit(
    season: str = "2026_27",
    gameweek: Optional[int] = None,
    force_recalc: bool = False,
):
    """Returns prospective zero-leakage model performance metrics and

    match verification cards vs actual outcomes and market odds.
    """
    data = run_model_audit(season=season, force_recalc=force_recalc)
    if gameweek is not None and "matches" in data:
        filtered = [m for m in data["matches"] if m.get("gameweek") == int(gameweek)]
        return {**data, "matches": filtered, "selected_gameweek": gameweek}
    return data


@app.get("/api/predict")
def predict_match(
    home_id: int = Query(...),
    away_id: int = Query(...),
    season: Optional[str] = None,
    match_id: Optional[int] = None,
):
    """
    Computes real-time micro-metrics and match predictions between two teams
    using trained models and the latest available team rolling statistics.
    Optionally scoped to a specific season (2024_25 or 2025_26).
    """
    if home_id == away_id:
        raise HTTPException(status_code=400, detail="Home and Away teams must be different.")

    home_meta = teams_dict.get(home_id)
    away_meta = teams_dict.get(away_id)
    if not home_meta or not away_meta:
        raise HTTPException(status_code=404, detail="Team not found.")

    team_states, strength_state, until, draw_state = get_live_state(season)
    target_season = str(season) if season and season != "all" else CURRENT_SEASON
    gameweek: Optional[float] = None
    target_match_id: Optional[int] = None

    # Reference date & referee: use the scheduled (unplayed) fixture of this pairing if it exists
    referee_info: Optional[Dict[str, Any]] = None
    if until is None:
        match_date = pd.Timestamp.now()
        if not df_features.empty and "is_played" in df_features.columns:
            upcoming = df_features[
                (df_features["home_id"] == home_id) & (df_features["away_id"] == away_id) & (~df_features["is_played"])
            ]
            if not upcoming.empty:
                fx = upcoming.iloc[0]
                match_date = pd.Timestamp(fx["match_date"])
                if pd.notnull(fx.get("match_id")):
                    try:
                        target_match_id = int(fx["match_id"])
                    except Exception:
                        pass
                if pd.notnull(fx.get("season")):
                    target_season = str(fx["season"])
                if pd.notnull(fx.get("gameweek")):
                    gameweek = float(fx["gameweek"])
                referee_info = {
                    c: (fx[c] if pd.notnull(fx.get(c)) else None)
                    for c in ["referee_name", "referee_avg_cards", "referee_avg_fouls", "referee_prior_matches"]
                    if c in fx.index
                }
    else:
        match_date = until + pd.Timedelta(days=7)  # Hypothetical next match after season end

    simulated_df = build_prediction_row(
        team_states,
        strength_state,
        home_id,
        away_id,
        match_date,
        referee_info,
        season=target_season,
        draw_state=draw_state,
        gameweek=gameweek,
        match_id=match_id or target_match_id,
    )

    # 1. Corner Prediction
    c_features = corner_artifact["feature_names"]
    X_c = _safe_features(simulated_df, c_features)
    exp_corners = float(corner_artifact["model"].predict(X_c)[0])
    exp_corners = max(5.0, min(18.0, exp_corners))
    # Use the count distribution fitted with the production model.
    corner_alpha = corner_artifact.get("count_dispersion_alpha", 0.0)
    prob_c85 = count_tail_probability(exp_corners, corner_alpha, 8) * 100
    prob_c95 = count_tail_probability(exp_corners, corner_alpha, 9) * 100
    prob_c105 = count_tail_probability(exp_corners, corner_alpha, 10) * 100

    # 2. Throws Prediction
    t_features = throws_artifact["feature_names"]
    X_t = _safe_features(simulated_df, t_features)
    exp_throws = float(throws_artifact["model"].predict(X_t)[0])
    exp_throws = max(20.0, min(50.0, exp_throws))
    throws_alpha = throws_artifact.get("count_dispersion_alpha", 0.0)
    prob_t335 = count_tail_probability(exp_throws, throws_alpha, 33) * 100
    prob_t345 = count_tail_probability(exp_throws, throws_alpha, 34) * 100
    prob_t365 = count_tail_probability(exp_throws, throws_alpha, 36) * 100

    # 3. Saves Prediction
    s_features = saves_artifact["feature_names"]
    X_s = _safe_features(simulated_df, s_features)
    exp_saves = float(saves_artifact["model"].predict(X_s)[0])
    exp_saves = max(2.0, min(12.0, exp_saves))

    # 4. Outcome & Goals Prediction
    o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact["feature_names"])
    o25_features = outcome_artifact.get("feature_names_o25", o_features)
    # Preserve missing 1X2 inputs so the fitted sklearn median imputer (or
    # LightGBM's native missing-value handling) sees the same representation
    # used at training time. Filling with zero here bypasses that preprocessing.
    probs_1x2 = outcome_artifact["model_1x2"].predict_proba(
        _safe_features(simulated_df, o_features, fill_value=np.nan)
    )
    # Enable Dixon-Coles physics blend if 1x2_ensemble_production is enabled
    has_ensemble = (
        "model_dc" in outcome_artifact
        and outcome_artifact.get("metrics", {})
        .get("1x2_ensemble_production", {})
        .get("enabled", True)
    )
    if has_ensemble:
        dc_probs_1x2 = outcome_artifact["model_dc"].predict_proba(simulated_df)
        probs_1x2 = blend_log(probs_1x2, dc_probs_1x2, outcome_artifact["ensemble_weight"])
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2_ensemble")
    else:
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2")
    if calibrator_1x2:
        probs_1x2 = apply_probability_calibrator(probs_1x2, calibrator_1x2)
    probs_1x2 = probs_1x2[0]
    prob_h = float(probs_1x2[0] * 100)
    prob_d = float(probs_1x2[1] * 100)
    prob_a = float(probs_1x2[2] * 100)

    goals_extra: Dict[str, Any] = {}
    over_source = "legacy"
    if goals_artifact is not None:
        # Align score cells to the (better-scoring) 1X2 model so every market shown agrees with it.
        score_matrix = align_to_outcome_probs(
            goals_artifact["model"].predict_matrices(simulated_df), np.atleast_2d(probs_1x2)
        )
        lam_h, lam_a = expected_goals(score_matrix)
        for line in goals_artifact.get("ou_lines", [1.5, 2.5, 3.5]):
            key = f"over_{line}"
            gate = goals_artifact.get("skill_gate", {}).get(key, "model_matrix")
            if gate == "baseline":
                p_line = float(goals_artifact["base_rates"][key])
                source = "baseline"
            else:
                p_line = float(over_prob(score_matrix, line)[0])
                calibrator = goals_artifact.get("calibrators", {}).get(key)
                if calibrator:
                    binary = np.array([[1.0 - p_line, p_line]], dtype=float)
                    p_line = float(apply_probability_calibrator(binary, calibrator)[0, 1])
                source = "model" if gate == "model" else "model_matrix"
            goals_extra[key] = {"pct": round(p_line * 100.0, 1), "source": source}

        # BTTS from bivariate score matrix with dynamic Bayesian prior threshold
        p_btts = float(btts_prob(score_matrix)[0])
        btts_calibrator = goals_artifact.get("calibrators", {}).get("btts")
        if btts_calibrator:
            p_btts = float(apply_probability_calibrator(np.array([[1.0 - p_btts, p_btts]]), btts_calibrator)[0, 1])
        btts_prior = float(goals_artifact.get("base_rates", {}).get("btts", 0.566))
        goals_extra["btts_pct"] = round(p_btts * 100.0, 1)
        goals_extra["btts_source"] = "model_matrix"
        goals_extra["btts_prior_pct"] = round(btts_prior * 100.0, 1)
        # No label when the BTTS gate failed (model not better than the league average, GOAL_MODELS_ANALYSIS P5).
        btts_informative = bool(goals_artifact.get("evaluation_gate", {}).get("btts_gate", {}).get("passed", False))
        goals_extra["btts_informative"] = btts_informative
        goals_extra["btts_prediction"] = ("KG Var" if p_btts >= 0.5 else "KG Yok") if btts_informative else None
        goals_extra["expected_home_goals"] = round(float(lam_h[0]), 2)
        goals_extra["expected_away_goals"] = round(float(lam_a[0]), 2)
        goals_extra["expected_total_goals"] = round(float(lam_h[0] + lam_a[0]), 2)

        # Enforce mathematical monotonicity: P(Over 1.5) >= P(Over 2.5) >= P(Over 3.5)
        p_15 = goals_extra["over_1.5"]["pct"]
        p_25 = min(p_15, goals_extra["over_2.5"]["pct"])
        p_35 = min(p_25, goals_extra["over_3.5"]["pct"])
        goals_extra["over_2.5"]["pct"] = p_25
        goals_extra["over_3.5"]["pct"] = p_35

        # Individual Team Totals (Tek taraflı gol baremleri: 0.5, 1.5, 2.5)
        def _calc_team_totals(side_name: str, lam: float) -> Dict[str, Any]:
            p_05 = round(float(team_over_prob(score_matrix, side_name, 0.5)[0] * 100.0), 1)
            p_15 = round(float(team_over_prob(score_matrix, side_name, 1.5)[0] * 100.0), 1)
            p_25 = round(float(team_over_prob(score_matrix, side_name, 2.5)[0] * 100.0), 1)
            p_15 = min(p_05, p_15)
            p_25 = min(p_15, p_25)

            lines = [
                {"line": 0.5, "over_pct": p_05, "under_pct": round(100.0 - p_05, 1), "fair_odds_over": round(100.0 / max(p_05, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_05, 1.0), 2), "dist": abs(p_05 - 50.0)},
                {"line": 1.5, "over_pct": p_15, "under_pct": round(100.0 - p_15, 1), "fair_odds_over": round(100.0 / max(p_15, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_15, 1.0), 2), "dist": abs(p_15 - 50.0)},
                {"line": 2.5, "over_pct": p_25, "under_pct": round(100.0 - p_25, 1), "fair_odds_over": round(100.0 / max(p_25, 1.0), 2), "fair_odds_under": round(100.0 / max(100.0 - p_25, 1.0), 2), "dist": abs(p_25 - 50.0)},
            ]
            primary = min(lines, key=lambda x: x["dist"])
            return {
                "expected_goals": round(float(lam), 2),
                "primary_line": primary["line"],
                "primary_over_pct": primary["over_pct"],
                "primary_under_pct": primary["under_pct"],
                "primary_fair_odds_over": primary["fair_odds_over"],
                "primary_fair_odds_under": primary["fair_odds_under"],
                "lines": {
                    "0.5": {"over_pct": p_05, "under_pct": round(100.0 - p_05, 1), "fair_odds_over": lines[0]["fair_odds_over"], "fair_odds_under": lines[0]["fair_odds_under"]},
                    "1.5": {"over_pct": p_15, "under_pct": round(100.0 - p_15, 1), "fair_odds_over": lines[1]["fair_odds_over"], "fair_odds_under": lines[1]["fair_odds_under"]},
                    "2.5": {"over_pct": p_25, "under_pct": round(100.0 - p_25, 1), "fair_odds_over": lines[2]["fair_odds_over"], "fair_odds_under": lines[2]["fair_odds_under"]},
                }
            }

        goals_extra["team_totals"] = {
            "home": _calc_team_totals("home", lam_h[0]),
            "away": _calc_team_totals("away", lam_a[0]),
        }

        over_source = goals_extra["over_2.5"]["source"]
        prob_o25 = float(p_25)
    else:
        probs_o25 = outcome_artifact["model_o25"].predict_proba(_safe_features(simulated_df, o25_features))
        calibrator_o25 = outcome_artifact.get("calibrators", {}).get("o25")
        if calibrator_o25:
            probs_o25 = apply_probability_calibrator(probs_o25, calibrator_o25)
        prob_o25 = float(probs_o25[0][1] * 100)

    fav = home_meta["name"] if prob_h > prob_a else away_meta["name"]
    fav_label = f"{fav} Favori" if abs(prob_h - prob_a) > 10 else "Dengeli Mücadele"

    # 5. Offside Prediction
    exp_offsides = 3.26
    prob_off25 = 65.0
    prob_off35 = 45.0
    prob_off45 = 25.0
    home_off_share = 0.52

    if offside_artifact is not None:
        off_features = offside_artifact.get("feature_cols") or offside_artifact.get("feature_names", [])
        missing_cols = [c for c in off_features if c not in simulated_df.columns]
        for m in missing_cols:
            simulated_df[m] = 0.0
        X_off = simulated_df[off_features].fillna(0.0)
        try:
            exp_offsides = float(offside_artifact["model"].predict(X_off)[0])
            exp_offsides = max(0.5, min(10.0, exp_offsides))
            offside_alpha = offside_artifact.get("count_dispersion_alpha", 0.0)
            prob_off25 = count_tail_probability(exp_offsides, offside_alpha, 2) * 100
            prob_off35 = count_tail_probability(exp_offsides, offside_alpha, 3) * 100
            prob_off45 = count_tail_probability(exp_offsides, offside_alpha, 4) * 100
        except Exception as e:
            logger.warning("Error predicting offsides: %s", e)

        # Dynamic home/away offside split blending offside tendency and opponent trap/line
        h_off_for = float(simulated_df.get("home_offsides_for_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        a_off_for = float(simulated_df.get("away_offsides_for_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        h_off_against = float(simulated_df.get("home_offsides_against_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        a_off_against = float(simulated_df.get("away_offsides_against_roll_5", pd.Series([1.6])).iloc[0] or 1.6)
        home_exp_off = 0.5 * (h_off_for + a_off_against)
        away_exp_off = 0.5 * (a_off_for + h_off_against)
        total_exp_off = home_exp_off + away_exp_off
        if total_exp_off > 0:
            home_off_share = max(0.20, min(0.80, home_exp_off / total_exp_off))

    # 6. Cards Prediction
    exp_cards = 4.2
    prob_c35 = 62.0
    prob_c45 = 44.0
    prob_c55 = 26.0
    home_cards_share = 0.50

    if cards_artifact is not None:
        c_features = cards_artifact.get("feature_cols", [])
        missing_c = [c for c in c_features if c not in simulated_df.columns]
        for m in missing_c:
            simulated_df[m] = 0.0
        X_cards = simulated_df[c_features].fillna(0.0)
        try:
            exp_cards = float(cards_artifact["model"].predict(X_cards)[0])
            exp_cards = max(1.0, min(12.0, exp_cards))
            cards_alpha = cards_artifact.get("count_dispersion_alpha", 0.0)
            prob_c35 = count_tail_probability(exp_cards, cards_alpha, 3) * 100
            prob_c45 = count_tail_probability(exp_cards, cards_alpha, 4) * 100
            prob_c55 = count_tail_probability(exp_cards, cards_alpha, 5) * 100
        except Exception as e:
            logger.warning("Error predicting cards: %s", e)

    h_c_for = float(simulated_df.get("home_cards_for_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    a_c_for = float(simulated_df.get("away_cards_for_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    h_c_against = float(simulated_df.get("home_cards_against_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    a_c_against = float(simulated_df.get("away_cards_against_roll_5", pd.Series([2.1])).iloc[0] or 2.1)
    home_exp_cards = 0.5 * (h_c_for + a_c_against)
    away_exp_cards = 0.5 * (a_c_for + h_c_against)
    total_exp_cards = home_exp_cards + away_exp_cards
    if total_exp_cards > 0:
        home_cards_share = max(0.20, min(0.80, home_exp_cards / total_exp_cards))

    raw_ref = simulated_df.get("referee_name", pd.Series([None])).iloc[0]
    ref_name = str(raw_ref) if pd.notnull(raw_ref) and raw_ref else "Premier League Hakem Heyeti"
    ref_avg_c = float(simulated_df.get("referee_avg_cards", pd.Series([4.15])).iloc[0] or 4.15)
    ref_avg_f = float(simulated_df.get("referee_avg_fouls", pd.Series([21.5])).iloc[0] or 21.5)
    regression_skills = {
        "corners": _regression_model_skill(corner_artifact),
        "throws": _regression_model_skill(throws_artifact),
        "saves": _regression_model_skill(saves_artifact),
        "offsides": _regression_model_skill(offside_artifact),
        "cards": _regression_model_skill(cards_artifact),
    }

    # Dynamic splits blending team production (FOR) and opponent volume conceded (AGAINST)
    h_crn_for = float(simulated_df.get("home_corners_for_roll_5", pd.Series([5.2])).iloc[0] or 5.2)
    a_crn_for = float(simulated_df.get("away_corners_for_roll_5", pd.Series([4.8])).iloc[0] or 4.8)
    h_crn_against = float(simulated_df.get("home_corners_against_roll_5", pd.Series([4.8])).iloc[0] or 4.8)
    a_crn_against = float(simulated_df.get("away_corners_against_roll_5", pd.Series([5.2])).iloc[0] or 5.2)
    home_exp_crn = 0.5 * (h_crn_for + a_crn_against)
    away_exp_crn = 0.5 * (a_crn_for + h_crn_against)
    total_exp_crn = home_exp_crn + away_exp_crn
    home_c_share = max(0.20, min(0.80, home_exp_crn / total_exp_crn)) if total_exp_crn > 0 else 0.55

    h_th_for_5 = float(simulated_df.get("home_throws_roll_5", pd.Series([18.0])).iloc[0] or 18.0)
    a_th_for_5 = float(simulated_df.get("away_throws_roll_5", pd.Series([17.0])).iloc[0] or 17.0)
    h_th_opp_5 = float(simulated_df.get("home_opponent_throws_roll_5", pd.Series([17.0])).iloc[0] or 17.0)
    a_th_opp_5 = float(simulated_df.get("away_opponent_throws_roll_5", pd.Series([18.0])).iloc[0] or 18.0)
    h_th_for_10 = float(simulated_df.get("home_throws_roll_10", pd.Series([h_th_for_5])).iloc[0] or h_th_for_5)
    a_th_for_10 = float(simulated_df.get("away_throws_roll_10", pd.Series([a_th_for_5])).iloc[0] or a_th_for_5)
    h_th_opp_10 = float(simulated_df.get("home_opponent_throws_roll_10", pd.Series([h_th_opp_5])).iloc[0] or h_th_opp_5)
    a_th_opp_10 = float(simulated_df.get("away_opponent_throws_roll_10", pd.Series([a_th_opp_5])).iloc[0] or a_th_opp_5)
    home_exp_th = 0.25 * (h_th_for_5 + a_th_opp_5) + 0.25 * (h_th_for_10 + a_th_opp_10)
    away_exp_th = 0.25 * (a_th_for_5 + h_th_opp_5) + 0.25 * (a_th_for_10 + h_th_opp_10)
    total_exp_th = home_exp_th + away_exp_th
    home_t_share = max(0.25, min(0.75, home_exp_th / total_exp_th)) if total_exp_th > 0 else 0.51

    h_sv = float(simulated_df.get("home_saves_roll_5", pd.Series([2.8])).iloc[0] or 2.8)
    a_sv = float(simulated_df.get("away_saves_roll_5", pd.Series([2.9])).iloc[0] or 2.9)
    h_sot_for = float(simulated_df.get("home_shots_ontarget_for_roll_5", pd.Series([4.5])).iloc[0] or 4.5)
    a_sot_for = float(simulated_df.get("away_shots_ontarget_for_roll_5", pd.Series([4.0])).iloc[0] or 4.0)
    home_exp_sv = 0.5 * (h_sv + a_sot_for * 0.70)
    away_exp_sv = 0.5 * (a_sv + h_sot_for * 0.70)
    total_exp_sv = home_exp_sv + away_exp_sv
    home_s_share = max(0.20, min(0.80, home_exp_sv / total_exp_sv)) if total_exp_sv > 0 else 0.48

    # 7. Dynamic Starting XI & Form Modulators
    target_mid = match_id or target_match_id
    lineup_analysis = None
    try:
        lineup_analysis = analyze_match_starting_xis(
            home_id=home_id,
            away_id=away_id,
            match_id=target_mid,
            referee_avg_cards=ref_avg_c,
        )
    except Exception as e:
        logger.warning(f"Error computing lineup analysis in predict_match: {e}")

    return {
        "home_team": home_meta,
        "away_team": away_meta,
        "favorite_label": fav_label,
        "outcome": {
            "home_win_pct": round(prob_h, 1),
            "draw_pct": round(prob_d, 1),
            "away_win_pct": round(prob_a, 1),
            **({
                "ensemble_probabilities_pct": [
                    round(float(prob_h), 1), round(float(prob_d), 1), round(float(prob_a), 1)
                ]
            } if has_ensemble else {}),
            "over_2_5_goals_pct": round(prob_o25, 1),
            "over_2_5_source": over_source,
        },
        "goals": goals_extra,
        "corners": {
            "model_skill": regression_skills["corners"],
            "expected_total": round(exp_corners, 1),
            "expected_home": round(exp_corners * home_c_share, 1),
            "expected_away": round(exp_corners * (1 - home_c_share), 1),
            "prob_over_8_5_pct": round(prob_c85, 1),
            "prob_over_9_5_pct": round(prob_c95, 1),
            "prob_over_10_5_pct": round(prob_c105, 1),
        },
        "cards": {
            "model_skill": regression_skills["cards"],
            "expected_total": round(exp_cards, 1),
            "expected_home": round(exp_cards * home_cards_share, 1),
            "expected_away": round(exp_cards * (1 - home_cards_share), 1),
            "prob_over_3_5_pct": round(prob_c35, 1),
            "prob_over_4_5_pct": round(prob_c45, 1),
            "prob_over_5_5_pct": round(prob_c55, 1),
        },
        "referee": {
            "name": ref_name,
            "avg_cards": round(ref_avg_c, 1),
            "avg_fouls": round(ref_avg_f, 1),
        },
        "throws": {
            "model_skill": regression_skills["throws"],
            "expected_total": round(exp_throws, 1),
            "expected_home": round(exp_throws * home_t_share, 1),
            "expected_away": round(exp_throws * (1 - home_t_share), 1),
            "prob_over_33_5_pct": round(prob_t335, 1),
            "prob_over_34_5_pct": round(prob_t345, 1),
            "prob_over_36_5_pct": round(prob_t365, 1),
        },
        "saves": {
            "model_skill": regression_skills["saves"],
            "expected_total": round(exp_saves, 1),
            "expected_home": round(exp_saves * home_s_share, 1),
            "expected_away": round(exp_saves * (1 - home_s_share), 1),
        },
        "shots": {
            "expected_total": round(exp_saves * 4.1, 1),
        },
        "offsides": {
            "model_skill": regression_skills["offsides"],
            "expected_total": round(exp_offsides, 1),
            "expected_home": round(exp_offsides * home_off_share, 1),
            "expected_away": round(exp_offsides * (1 - home_off_share), 1),
            "prob_over_2_5_pct": round(prob_off25, 1),
            "prob_over_3_5_pct": round(prob_off35, 1),
            "prob_over_4_5_pct": round(prob_off45, 1),
        },
        "lineup_analysis": lineup_analysis,
    }


@app.get("/api/players/{player_id}/rating")
def get_player_rating_endpoint(player_id: int, as_of_match_id: Optional[int] = None):
    """
    Returns player's dynamic 0-10 rating, 5-match EWMA form, season baseline,
    and cards risk index.
    """
    try:
        data = get_player_dynamic_rating(player_id, as_of_match_id=as_of_match_id)
        if not data:
            raise HTTPException(status_code=404, detail="Player rating data not found.")
        return data
    except Exception as e:
        logger.warning(f"Error fetching player rating for {player_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/benchmarks")
def get_benchmarks():
    """Returns saved model benchmark metrics and summary."""
    benchmarks_path = BASE_DIR / "docs" / "reports" / "model_benchmarks.md"
    content = ""
    if benchmarks_path.exists():
        with open(benchmarks_path, "r", encoding="utf-8") as f:
            content = f.read()

    return {
        "corner": corner_artifact["metrics"] if corner_artifact else {},
        "throws": throws_artifact["metrics"] if throws_artifact else {},
        "saves": saves_artifact["metrics"] if saves_artifact else {},
        "outcome": outcome_artifact["metrics"] if outcome_artifact else {},
        "offside": offside_artifact["metrics"] if offside_artifact else {},
        "markdown_report": content,
    }


@app.get("/")
def root():
    return {
        "service": "Premier League Model Engine API",
        "status": "online",
        "frontend": "http://localhost:5173"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
