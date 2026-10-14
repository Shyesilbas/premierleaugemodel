#!/usr/bin/env python3
"""
Premier League Model Engine — FastAPI Backend Server
Serves interactive prediction engine, fixtures, events, and static frontend dashboard.
"""

import json
import logging
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.models.model_utils import apply_probability_calibrator, blend_log, count_tail_probability
from src.models.dixon_coles import btts_prob, over_prob
from src.db.database import get_referees_list, get_referee_detail, get_all_grouped_fixtures, get_referee_summary
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

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models" / "production"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else (BASE_DIR / "frontend")

# Load the current combined datasets & production models into memory.
logger.info("Loading cached datasets and models...")
matches_all = DATA_DIR / "processed" / "matches_summary_all.parquet"
features_all = DATA_DIR / "processed" / "features_matches_all.parquet"
matches_parquet = matches_all
features_parquet = features_all

df_matches = pd.read_parquet(matches_parquet) if matches_parquet.exists() else pd.DataFrame()
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

    df_matches = pd.read_parquet(matches_parquet) if matches_parquet.exists() else pd.DataFrame()
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
    if not _long_history.empty:
        get_live_state(None)


def _run_season_sync_job(job_id: str, season: str) -> None:
    script_path = BASE_DIR / "src" / "ingest" / "sync_season_data.py"
    command = [sys.executable, str(script_path), "--season-name", season]
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
                _sync_job.update(status="completed", message="Veriler güncellendi.", output=output)
    except Exception as exc:
        logger.exception("Season sync job failed")
        with _sync_job_lock:
            if _sync_job.get("id") == job_id:
                _sync_job.update(status="failed", message=str(exc), output="")


@app.post("/api/admin/sync-season")
def start_season_sync(season: str = Query("2026_27")):
    """Start an incremental season sync in the background."""
    if season not in {"2022_23", "2023_24", "2024_25", "2025_26", "2026_27"}:
        raise HTTPException(status_code=400, detail="Unsupported season")
    with _sync_job_lock:
        if _sync_job.get("status") in {"queued", "running"}:
            return {**_sync_job, "already_running": True}
        job_id = str(uuid.uuid4())
        _sync_job.update(id=job_id, status="running", season=season, message="Sezon verileri kontrol ediliyor...", output="")
    thread = threading.Thread(target=_run_season_sync_job, args=(job_id, season), daemon=True)
    thread.start()
    return {**_sync_job, "already_running": False}


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
    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    if not changes_path.exists():
        return {"season": season, "events_by_match": {}}
    try:
        with changes_path.open("r", encoding="utf-8") as stream:
            changes_by_season = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read manager change data")
        raise HTTPException(status_code=500, detail="Could not read manager change data") from exc

    season_changes = changes_by_season.get(season, {}).get("events", [])
    fixtures = get_all_grouped_fixtures(season)
    events_by_match: Dict[str, List[Dict[str, Any]]] = {}
    for event in season_changes:
        try:
            appointment_date = datetime.strptime(event["appointment_date"], "%Y-%m-%d").date()
            team_id = int(event["team_id"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed manager change record: %s", event)
            continue

        next_fixture = None
        next_kickoff = datetime.max
        for fixture in fixtures:
            if team_id not in (int(fixture["home_id"]), int(fixture["away_id"])):
                continue
            kickoff = parse_kickoff_datetime(fixture.get("kickoff_label", ""))
            # Appointment sources provide dates, not times. Using the following
            # calendar day avoids attributing a match played before an announcement.
            if kickoff == datetime.min or kickoff.date() <= appointment_date:
                continue
            if kickoff < next_kickoff:
                next_fixture, next_kickoff = fixture, kickoff

        if next_fixture is None:
            continue
        match_id = str(next_fixture["match_id"])
        events_by_match.setdefault(match_id, []).append({
            **event,
            "gameweek": next_fixture.get("gameweek"),
            "effective_match_date": next_fixture.get("kickoff_label", ""),
        })

    return {"season": season, "events_by_match": events_by_match}


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
    db_fixtures = get_all_grouped_fixtures(season)
    raw_fixtures = []

    for r in db_fixtures:
        mid = int(r["match_id"])
        h_id = int(r["home_id"])
        a_id = int(r["away_id"])
        gw = int(r["gameweek"])
        h_score = r["home_score"]
        a_score = r["away_score"]
        is_completed = (r["status"] == "COMPLETED" or (h_score is not None and a_score is not None))
        match_stats = match_stats_map.get(mid, {})

        # Compute AI predictions for uncompleted matches in current/upcoming gameweeks
        pred = get_quick_fixture_prediction(h_id, a_id, r.get("season") or season) if (not is_completed and gw in [6, 7, 8]) else None

        raw_fixtures.append({
            "match_id": mid,
            "gameweek": gw,
            "kickoff_label": r.get("kickoff_label") or "",
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

    return {
        "season": season,
        "gameweeks": structured,
        "total_matches": len(raw_fixtures),
        "current_gameweek": current_gw,
    }


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

    return {
        "season": season,
        "total_teams": len(standings_list),
        "standings": standings_list
    }



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

        matches_list.append({
            "match_id": int(r["match_id"]),
            "season": str(r.get("season", "")),
            "status": "COMPLETED" if pd.notnull(t_score) else "UNPLAYED",
            "gameweek": r.get("gameweek"),
            "kickoff_label": r.get("kickoff_label"),
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

    # Squad list
    squad = [p for p in all_players if p.get("teamId") == team_id]

    return {
        "team": team_meta,
        "season": season,
        "record": {"wins": wins, "draws": draws, "losses": losses, "played": len(matches_list), "gf": gf, "ga": ga},
        "matches": matches_list,
        "squad": squad,
    }


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


@app.get("/api/players")
def get_players(team_id: Optional[int] = None, search: Optional[str] = None, limit: int = 100):
    """Returns player directory with optional filters."""
    result = all_players
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
            player_data["teamName"] = latest_match["team_name"]

    tot_mins = sum(m.get("minutes_played", 0) for m in logs)
    tot_goals = sum(m.get("goals", 0) for m in logs)
    tot_assists = sum(m.get("assists", 0) for m in logs)

    return {
        "player": player_data,
        "season": season,
        "season_stats": {
            "appearances": len(logs),
            "minutes": tot_mins,
            "goals": tot_goals,
            "assists": tot_assists,
        },
        "matches": logs,
    }


@app.get("/api/match/{match_id}/details")
def get_match_full_details(match_id: int):
    """
    Returns full match lineup rosters, substitutes, tactical formations,
    and play-by-play events.
    """
    raw_details = DATA_DIR / "raw" / "matches" / f"{match_id}_details.json"
    raw_stream = DATA_DIR / "raw" / "matches" / f"{match_id}_stream.json"

    raw_stats = DATA_DIR / "raw" / "matches" / f"{match_id}_stats.json"

    lineups = []
    metadata = {}
    team_stats = []
    player_stats = {"home": [], "away": []}

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
        }

        teams_info = d.get("teams", [])
        for idx, tl in enumerate(d.get("teamLists", [])):
            if not tl or not isinstance(tl, dict):
                continue
            t_obj = teams_info[idx].get("team", {}) if idx < len(teams_info) else {}
            score_val = teams_info[idx].get("score") if idx < len(teams_info) else None

            starters = []
            for p in tl.get("lineup", []):
                pid = p.get("id")
                reg_p = player_registry_map.get(int(pid), {}) if pid else {}
                opta_c = reg_p.get("opta_code") or f"p{pid}"
                photo = reg_p.get("photo_url") or f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"
                pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"
                starters.append({
                    "id": pid,
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": pos,
                    "captain": p.get("captain", False),
                    "country": p.get("nationalTeam", {}).get("country"),
                    "photo_url": photo,
                })

            subs = []
            for p in tl.get("substitutes", []):
                pid = p.get("id")
                reg_p = player_registry_map.get(int(pid), {}) if pid else {}
                opta_c = reg_p.get("opta_code") or f"p{pid}"
                photo = reg_p.get("photo_url") or f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"
                pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"
                subs.append({
                    "id": pid,
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": pos,
                    "photo_url": photo,
                })

            # Sort starters & substitutes by position: Kaleci (GK) -> Savunma (DEF) -> Orta Saha (MID) -> Forvet (FWD)
            starters.sort(key=lambda x: (get_position_order(x.get("position")), x.get("shirt") or 99))
            subs.sort(key=lambda x: (get_position_order(x.get("position")), x.get("shirt") or 99))

            lineups.append({
                "team_id": tl.get("teamId"),
                "team_name": t_obj.get("name"),
                "score": score_val,
                "formation": tl.get("formation", {}).get("label", "4-3-3"),
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

    # Player Match Performance Table (from details & stream)
    events = []
    if raw_stream.exists():
        with open(raw_stream, "r", encoding="utf-8") as f:
            st = json.load(f)
            events = st.get("events", {}).get("content", [])

    # Compute player metrics from details and stream
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
            except:
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

    fouls_lost = {}
    fouls_won = {}
    shots = {}
    shots_ot = {}
    offsides = {}

    for se in events:
        stype = se.get("type")
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
        elif stype == "offside":
            offsides[p0] = offsides.get(p0, 0) + 1

    # Populate home & away player cards
    for idx, tl in enumerate(d.get("teamLists", [])):
        if not tl or not isinstance(tl, dict):
            continue
        side = "home" if idx == 0 else "away"
        lineup_p = tl.get("lineup", [])
        subs_p = tl.get("substitutes", [])

        # Process starters
        for p in lineup_p:
            pid = p.get("id")
            if not pid:
                continue
            mins = sub_off.get(pid, 90)
            reg_p = player_registry_map.get(int(pid), {}) if pid else {}
            opta_c = reg_p.get("opta_code") or f"p{pid}"
            photo = reg_p.get("photo_url") or f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"
            pos = p.get("matchPosition") or p.get("info", {}).get("position", "M")
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
            })

        # Process substitutes who actually played
        for p in subs_p:
            pid = p.get("id")
            if not pid or pid not in sub_on:
                continue
            mins = max(1, 90 - sub_on[pid])
            reg_p = player_registry_map.get(int(pid), {}) if pid else {}
            opta_c = reg_p.get("opta_code") or f"p{pid}"
            photo = reg_p.get("photo_url") or f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"
            pos = p.get("matchPosition") or p.get("info", {}).get("position", "M")
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
                reg_p = player_registry_map.get(int(pid), {})
                opta_c = reg_p.get("opta_code") or f"p{pid}"
                player_photos[pid] = reg_p.get("photo_url") or f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta_c}.png"

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
        elif etype == "G":
            pid = ev.get("personId")
            aid = ev.get("assistId")
            desc = ev.get("description", "G")
            goal_type = "Penaltı Golü" if desc == "P" else ("Kendi Kalesine Gol" if desc == "OG" else "Gol")
            h_s = ev.get("score", {}).get("homeScore", 0)
            a_s = ev.get("score", {}).get("awayScore", 0)
            key_timeline.append({
                "type": "goal",
                "goal_type": goal_type,
                "minute": minute_display,
                "team_id": tid,
                "team_name": tname,
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

    return {
        "metadata": metadata,
        "lineups": lineups,
        "team_stats": team_stats,
        "player_stats": player_stats,
        "events": events,
        "timeline": key_timeline,
    }


@app.get("/api/predict")
def predict_match(home_id: int = Query(...), away_id: int = Query(...), season: Optional[str] = None):
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
    )

    def _safe_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
        for c in features:
            if c not in df.columns:
                df[c] = 0.0
        return df[features].fillna(0.0)

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
    prob_t365 = count_tail_probability(exp_throws, throws_alpha, 36) * 100

    # 3. Saves Prediction
    s_features = saves_artifact["feature_names"]
    X_s = _safe_features(simulated_df, s_features)
    exp_saves = float(saves_artifact["model"].predict(X_s)[0])
    exp_saves = max(2.0, min(12.0, exp_saves))

    # 4. Outcome & Goals Prediction
    o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact["feature_names"])
    o25_features = outcome_artifact.get("feature_names_o25", o_features)
    probs_1x2 = outcome_artifact["model_1x2"].predict_proba(_safe_features(simulated_df, o_features))
    has_ensemble = "model_dc" in outcome_artifact
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
        goal_model = goals_artifact["model"]
        score_matrix = goal_model.predict_matrices(simulated_df)
        lam_h, lam_a = goal_model.lambdas(simulated_df)
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

        goals_extra["btts_pct"] = round(float(btts_prob(score_matrix)[0]) * 100.0, 1)
        goals_extra["btts_source"] = "model_matrix"
        goals_extra["expected_home_goals"] = round(float(lam_h[0]), 2)
        goals_extra["expected_away_goals"] = round(float(lam_a[0]), 2)
        goals_extra["expected_total_goals"] = round(float(lam_h[0] + lam_a[0]), 2)
        over_source = goals_extra["over_2.5"]["source"]
        prob_o25 = float(goals_extra["over_2.5"]["pct"])
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

        # Dynamic home/away offside split based on team rates
        if "home_offsides_for_roll_5" in simulated_df.columns and "away_offsides_for_roll_5" in simulated_df.columns:
            h_off = float(simulated_df["home_offsides_for_roll_5"].iloc[0] or 1.6)
            a_off = float(simulated_df["away_offsides_for_roll_5"].iloc[0] or 1.6)
            if (h_off + a_off) > 0:
                home_off_share = max(0.2, min(0.8, h_off / (h_off + a_off)))

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

    if "home_cards_for_roll_5" in simulated_df.columns and "away_cards_for_roll_5" in simulated_df.columns:
        h_c = float(simulated_df["home_cards_for_roll_5"].iloc[0] or 2.1)
        a_c = float(simulated_df["away_cards_for_roll_5"].iloc[0] or 2.1)
        if (h_c + a_c) > 0:
            home_cards_share = max(0.2, min(0.8, h_c / (h_c + a_c)))


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

    # Splits (Home vs Away breakdown dynamically calculated from team rolling rates)
    home_c_share = 0.55
    if "home_corners_for_roll_5" in simulated_df.columns and "away_corners_for_roll_5" in simulated_df.columns:
        h_crn = float(simulated_df["home_corners_for_roll_5"].iloc[0] or 5.2)
        a_crn = float(simulated_df["away_corners_for_roll_5"].iloc[0] or 4.8)
        if (h_crn + a_crn) > 0:
            home_c_share = max(0.25, min(0.75, h_crn / (h_crn + a_crn)))

    home_t_share = 0.51
    if "home_throws_roll_5" in simulated_df.columns and "away_throws_roll_5" in simulated_df.columns:
        h_th = float(simulated_df["home_throws_roll_5"].iloc[0] or 18.0)
        a_th = float(simulated_df["away_throws_roll_5"].iloc[0] or 17.0)
        if (h_th + a_th) > 0:
            home_t_share = max(0.30, min(0.70, h_th / (h_th + a_th)))

    home_s_share = 0.48
    if "home_saves_roll_5" in simulated_df.columns and "away_saves_roll_5" in simulated_df.columns:
        h_sv = float(simulated_df["home_saves_roll_5"].iloc[0] or 2.8)
        a_sv = float(simulated_df["away_saves_roll_5"].iloc[0] or 2.9)
        if (h_sv + a_sv) > 0:
            home_s_share = max(0.25, min(0.75, h_sv / (h_sv + a_sv)))

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
        }
    }


@app.get("/api/benchmarks")
def get_benchmarks():
    """Returns saved model benchmark metrics and summary."""
    benchmarks_path = BASE_DIR / "reports" / "model_benchmarks.md"
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
