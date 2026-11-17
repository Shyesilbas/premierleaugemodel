"""On-demand per-match and pending-batch refresh services for fast UI updates.

For Premier League matches, refreshes individual fixtures directly via PulseLive
(`details`, `stats`, `stream`), updates raw JSON and SQLite immediately (~1 s),
invalidates API caches so UI cards/standings/match-detail views reflect new
scores right away, and schedules an asynchronous derived-dataset rebuild.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import HTTPException

from src.config import DEFAULT_SEASON, MATCHES_RAW_DIR, RAW_DIR, ROOT as BASE_DIR, SEASONS
from src.db.database import get_db
from src.ingest.fetch_season_data import (
    build_session,
    fetch_match_details,
    fetch_match_stats,
    fetch_match_stream,
)
from src.ingest.files import atomic_write_json
from src.ingest.sync_season_data import load_fixture_file, match_label, sync_lock, SyncAlreadyRunning
from src.processing.process_season_data import parse_match

logger = logging.getLogger("api_server")

_jobs_lock = threading.Lock()
_ingest_lock = threading.Lock()
_rebuild_lock = threading.Lock()
_rebuild_pending = False
_rebuild_running = False

_single_jobs: Dict[int, Dict[str, Any]] = {}
_batch_job: Dict[str, Any] = {
    "id": None,
    "status": "idle",
    "season": None,
    "competition": "premier_league",
    "total": 0,
    "completed": 0,
    "refreshed_count": 0,
    "failed_count": 0,
    "current_match_id": None,
    "matches": [],
    "message": None,
}


def _opt_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def _opt_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
        return int(val)
    except (TypeError, ValueError):
        return None


def _kickoff_utc_from_row(row: Dict[str, Any], raw_millis_map: Dict[int, int]) -> Optional[datetime]:
    mid = int(row["match_id"])
    millis = raw_millis_map.get(mid)
    if millis:
        return datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)

    from src.api import state

    label = str(row.get("kickoff_label") or "")
    parsed = state.parse_kickoff_datetime(label)
    if parsed != datetime.min:
        return parsed.replace(tzinfo=timezone.utc)

    match_date = str(row.get("match_date") or "").strip()
    if match_date:
        try:
            date_part = match_date[:10]
            time_part = str(row.get("time_label") or "").strip()
            if len(time_part) == 5 and ":" in time_part:
                return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            return datetime.strptime(date_part, "%Y-%m-%d").replace(hour=23, minute=59, tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _raw_kickoff_millis_map(season: str) -> Dict[int, int]:
    path = RAW_DIR / f"fixtures_{season}.json"
    out: Dict[int, int] = {}
    if not path.exists():
        return out
    for f in load_fixture_file(path):
        mid = f.get("id")
        millis = (f.get("kickoff") or {}).get("millis")
        if mid is not None and millis:
            try:
                out[int(mid)] = int(millis)
            except (TypeError, ValueError):
                pass
    return out


def list_pending_matches(season: str = DEFAULT_SEASON, competition: str = "premier_league") -> Dict[str, Any]:
    """Return IDs of past/ended matches that still lack completed status or match files."""
    from src.competitions.registry import get_competition

    comp = get_competition(competition)
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(minutes=110)

    raw_millis_map = _raw_kickoff_millis_map(season) if comp.provider == "pulselive" else {}
    pending_ids: List[int] = []

    with closing(get_db()) as conn:
        rows = conn.execute(
            "SELECT match_id, status, match_date, kickoff_label, time_label, home_score, away_score "
            "FROM matches WHERE competition_id = ? AND season = ? ORDER BY gameweek ASC, match_date ASC, match_id ASC",
            (comp.id, season),
        ).fetchall()

        existing_payloads: Dict[int, set] = {}
        if comp.provider != "pulselive":
            payload_rows = conn.execute(
                "SELECT p.match_id, p.kind FROM external_match_payloads p "
                "JOIN matches m ON m.match_id = p.match_id "
                "WHERE m.competition_id = ? AND m.season = ?",
                (comp.id, season),
            ).fetchall()
            for pr in payload_rows:
                existing_payloads.setdefault(int(pr["match_id"]), set()).add(pr["kind"])

    for r in rows:
        row = dict(r)
        mid = int(row["match_id"])
        status = str(row.get("status") or "").upper()
        is_completed = status == "COMPLETED" and row.get("home_score") is not None and row.get("away_score") is not None

        if not is_completed:
            ko = _kickoff_utc_from_row(row, raw_millis_map)
            if ko is not None and ko <= cutoff_utc:
                pending_ids.append(mid)
            continue

        if comp.provider == "pulselive":
            if any(not (MATCHES_RAW_DIR / f"{mid}_{kind}.json").exists() for kind in ("stats", "stream", "details")):
                pending_ids.append(mid)
        elif comp.provider == "thestatsapi":
            kinds = existing_payloads.get(mid, set())
            if "stats" not in kinds or "timeline" not in kinds:
                pending_ids.append(mid)

    return {
        "season": season,
        "competition": comp.key,
        "pending_match_ids": pending_ids,
        "count": len(pending_ids),
    }


def _schedule_background_rebuild() -> None:
    """Queue a single non-blocking derived dataset rebuild after instant SQLite updates."""
    global _rebuild_pending, _rebuild_running
    with _rebuild_lock:
        if _rebuild_running:
            _rebuild_pending = True
            return
        _rebuild_running = True
        _rebuild_pending = False

    def _worker() -> None:
        global _rebuild_pending, _rebuild_running
        from src.api import state
        from src.pipeline.rebuild import rebuild_derived_data

        while True:
            try:
                with sync_lock():
                    rebuild_derived_data()
                    state.reload_runtime_datasets()
            except SyncAlreadyRunning:
                logger.info("Skipping background rebuild because another sync already holds the lock")
            except Exception:
                logger.exception("Background derived-data rebuild after match refresh failed")
            with _rebuild_lock:
                if _rebuild_pending:
                    _rebuild_pending = False
                    continue
                _rebuild_running = False
                break

    threading.Thread(target=_worker, daemon=True).start()


def _upsert_pl_match_in_sqlite(record: Dict[str, Any]) -> None:
    """Apply parsed Premier League match stats directly to SQLite without waiting for full parquet rebuild."""
    mid = int(record["match_id"])
    status = "COMPLETED" if record.get("home_score") is not None and record.get("away_score") is not None else "UPCOMING"
    ref_name = str(record.get("referee_name") or "Unknown").strip() or "Unknown"

    with closing(get_db()) as conn:
        existing = conn.execute(
            "SELECT home_xg, away_xg, total_xg, referee_id, referee_name FROM matches WHERE match_id = ?",
            (mid,),
        ).fetchone()
        home_xg = _opt_float(record.get("home_xg"))
        away_xg = _opt_float(record.get("away_xg"))
        total_xg = _opt_float(record.get("total_xg"))
        if home_xg is None and existing:
            home_xg = existing["home_xg"]
        if away_xg is None and existing:
            away_xg = existing["away_xg"]
        if total_xg is None and existing:
            total_xg = existing["total_xg"]

        ref_id = _opt_int(record.get("referee_id"))
        if ref_id is None and existing:
            ref_id = existing["referee_id"]
        if (not ref_name or ref_name == "Unknown") and existing and existing["referee_name"]:
            ref_name = existing["referee_name"]

        conn.execute(
            """
            UPDATE matches SET
                home_score = ?,
                away_score = ?,
                status = ?,
                total_corners = COALESCE(?, total_corners),
                home_won_corners = COALESCE(?, home_won_corners),
                away_won_corners = COALESCE(?, away_won_corners),
                total_throws = COALESCE(?, total_throws),
                home_total_throws = COALESCE(?, home_total_throws),
                away_total_throws = COALESCE(?, away_total_throws),
                total_shots = COALESCE(?, total_shots),
                total_shots_ontarget = COALESCE(?, total_shots_ontarget),
                total_saves = COALESCE(?, total_saves),
                referee_id = ?,
                referee_name = ?,
                total_yellow_cards = COALESCE(?, total_yellow_cards),
                total_red_cards = COALESCE(?, total_red_cards),
                total_cards = COALESCE(?, total_cards),
                total_fouls = COALESCE(?, total_fouls),
                home_total_yel_card = COALESCE(?, home_total_yel_card),
                away_total_yel_card = COALESCE(?, away_total_yel_card),
                home_total_red_card = COALESCE(?, home_total_red_card),
                away_total_red_card = COALESCE(?, away_total_red_card),
                home_xg = ?,
                away_xg = ?,
                total_xg = ?
            WHERE match_id = ?
            """,
            (
                _opt_float(record.get("home_score")),
                _opt_float(record.get("away_score")),
                status,
                _opt_float(record.get("total_corners")),
                _opt_float(record.get("home_won_corners")),
                _opt_float(record.get("away_won_corners")),
                _opt_float(record.get("total_throws")),
                _opt_float(record.get("home_total_throws")),
                _opt_float(record.get("away_total_throws")),
                _opt_float(record.get("total_shots")),
                _opt_float(record.get("total_shots_ontarget")),
                _opt_float(record.get("total_saves")),
                ref_id,
                ref_name,
                _opt_float(record.get("total_yellow_cards")),
                _opt_float(record.get("total_red_cards")),
                _opt_float(record.get("total_cards")),
                _opt_float(record.get("total_fouls")),
                _opt_float(record.get("home_total_yel_card")),
                _opt_float(record.get("away_total_yel_card")),
                _opt_float(record.get("home_total_red_card")),
                _opt_float(record.get("away_total_red_card")),
                home_xg,
                away_xg,
                total_xg,
                mid,
            ),
        )
        conn.commit()


def _invalidate_match_caches(match_id: int) -> None:
    from src.analytics.player_ratings import clear_caches as clear_player_rating_caches
    from src.analytics.team_attackers import _load_inputs as _load_attacker_inputs, get_team_attacking_leaders
    from src.analytics.team_scenarios import get_team_scenario_profile, load_team_match_scenarios
    from src.analytics.team_tactics import get_team_tactical_profile, load_team_match_rows
    from src.api import state

    state._completed_match_details_cache.pop(match_id, None)
    state._historical_fixtures_grouped_cache.clear()
    state._historical_standings_cache.clear()
    state._fixture_pred_cache.clear()
    state._player_compare_cache.clear()
    load_team_match_rows.cache_clear()
    load_team_match_scenarios.cache_clear()
    _load_attacker_inputs.cache_clear()
    clear_player_rating_caches()
    get_team_tactical_profile.cache_clear()
    get_team_scenario_profile.cache_clear()
    get_team_attacking_leaders.cache_clear()
    state._loaded_data_version += 1


def _refresh_pl_match_sync(match_id: int, season: str, session: Any) -> Dict[str, Any]:
    MATCHES_RAW_DIR.mkdir(parents=True, exist_ok=True)

    details_data = fetch_match_details(session, match_id)
    if not isinstance(details_data, dict):
        raise RuntimeError(f"Mac detaylari alinamadi ({match_id})")
    stats_data = fetch_match_stats(session, match_id)
    stream_data = fetch_match_stream(session, match_id)

    atomic_write_json(MATCHES_RAW_DIR / f"{match_id}_details.json", details_data)
    if isinstance(stats_data, dict):
        atomic_write_json(MATCHES_RAW_DIR / f"{match_id}_stats.json", stats_data)
    if isinstance(stream_data, dict):
        atomic_write_json(MATCHES_RAW_DIR / f"{match_id}_stream.json", stream_data)

    fixture_path = RAW_DIR / f"fixtures_{season}.json"
    fixtures = load_fixture_file(fixture_path)
    updated_fixture: Optional[Dict[str, Any]] = None
    updated_fixtures: List[Dict[str, Any]] = []

    details_status = str(details_data.get("status") or "").upper()
    details_teams = details_data.get("teams") or []
    for f in fixtures:
        if int(f.get("id", -1)) == match_id:
            merged = dict(f)
            if details_status:
                merged["status"] = details_status
            if len(details_teams) >= 2:
                merged["teams"] = details_teams
            if details_data.get("matchOfficials"):
                merged["matchOfficials"] = details_data["matchOfficials"]
            if details_data.get("outcome"):
                merged["outcome"] = details_data["outcome"]
            updated_fixture = merged
            updated_fixtures.append(merged)
        else:
            updated_fixtures.append(f)

    if updated_fixture is None:
        updated_fixture = details_data
    elif fixtures:
        atomic_write_json(fixture_path, updated_fixtures)
        if season == DEFAULT_SEASON:
            from src.api import state

            state.raw_fixtures_2627 = updated_fixtures

    record = parse_match(updated_fixture, stats_data, details_data, stream_data)
    if record:
        _upsert_pl_match_in_sqlite(record)
    _invalidate_match_caches(match_id)

    return {
        "match_id": match_id,
        "status": "COMPLETED" if str(updated_fixture.get("status") or "").upper() == "C" else "UPCOMING",
        "label": match_label(updated_fixture),
        "home_score": record.get("home_score") if record else None,
        "away_score": record.get("away_score") if record else None,
    }


def _run_competition_sync_subprocess(competition_key: str, season: str) -> None:
    cmd = [sys.executable, "-m", "src.ingest.sync_competition", "--competition", competition_key, "--season", season]
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        detail = (res.stderr or res.stdout or "").strip().splitlines()
        msg = detail[-1] if detail else f"exit code {res.returncode}"
        raise RuntimeError(msg)


def refresh_single_match_job(match_id: int, season: str, competition: str = "premier_league") -> Dict[str, Any]:
    from src.api import state
    from src.competitions.registry import get_competition

    comp = get_competition(competition)
    if season not in set(SEASONS):
        raise HTTPException(status_code=400, detail="Unsupported season")

    with _jobs_lock:
        current = _single_jobs.get(match_id)
        if current and current.get("status") in {"queued", "running"}:
            return dict(current)
        job = {
            "id": str(uuid.uuid4()),
            "match_id": match_id,
            "season": season,
            "competition": comp.key,
            "status": "running",
            "message": "Mac verisi getiriliyor...",
            "refreshed": False,
        }
        _single_jobs[match_id] = job

    def _worker() -> None:
        try:
            with _ingest_lock:
                if comp.provider == "pulselive":
                    session = build_session()
                    info = _refresh_pl_match_sync(match_id, season, session)
                    if info.get("status") == "COMPLETED":
                        _schedule_background_rebuild()
                    update = {
                        "status": "completed",
                        "refreshed": info.get("status") == "COMPLETED",
                        "message": f"Guncellendi: {info.get('label', match_id)}",
                        "match": info,
                    }
                else:
                    _run_competition_sync_subprocess(comp.key, season)
                    state.reload_runtime_datasets()
                    _invalidate_match_caches(match_id)
                    update = {
                        "status": "completed",
                        "refreshed": True,
                        "message": "Turnuva mac verileri guncellendi",
                        "match": {"match_id": match_id},
                    }
        except Exception as exc:
            logger.exception("Single-match refresh failed for %s (%s)", match_id, comp.key)
            update = {"status": "failed", "refreshed": False, "message": str(exc)}

        with _jobs_lock:
            _single_jobs[match_id] = {**_single_jobs.get(match_id, {}), **update}

    threading.Thread(target=_worker, daemon=True).start()
    return dict(job)


def get_single_match_job(match_id: int) -> Dict[str, Any]:
    with _jobs_lock:
        return dict(_single_jobs.get(match_id, {"match_id": match_id, "status": "idle"}))


def start_batch_refresh_job(
    season: str = DEFAULT_SEASON,
    competition: str = "premier_league",
    match_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    from src.api import state
    from src.competitions.registry import get_competition

    comp = get_competition(competition)
    if season not in set(SEASONS):
        raise HTTPException(status_code=400, detail="Unsupported season")

    with _jobs_lock:
        if _batch_job.get("status") in {"queued", "running"}:
            return {**_batch_job, "already_running": True}

        target_ids = list(match_ids) if match_ids else list_pending_matches(season, comp.key)["pending_match_ids"]
        job_id = str(uuid.uuid4())
        _batch_job.update(
            id=job_id,
            status="running" if target_ids else "completed",
            season=season,
            competition=comp.key,
            total=len(target_ids),
            completed=0,
            refreshed_count=0,
            failed_count=0,
            current_match_id=target_ids[0] if target_ids else None,
            matches=[],
            message="Veri taraniyor..." if target_ids else "Eksik mac verisi bulunmuyor.",
        )

    if not target_ids:
        return {**_batch_job, "already_running": False}

    def _worker() -> None:
        updated_any = False
        try:
            with _ingest_lock:
                if comp.provider == "pulselive":
                    session = build_session()
                    for idx, mid in enumerate(target_ids, start=1):
                        with _jobs_lock:
                            _batch_job["current_match_id"] = mid
                            _batch_job["message"] = f"Mac indiriliyor ({idx}/{len(target_ids)})..."
                        try:
                            info = _refresh_pl_match_sync(int(mid), season, session)
                            updated_any = updated_any or info.get("status") == "COMPLETED"
                            with _jobs_lock:
                                _batch_job["completed"] = idx
                                _batch_job["refreshed_count"] += 1
                                if info.get("label"):
                                    _batch_job["matches"].append(info["label"])
                        except Exception as exc:
                            logger.warning("Batch match refresh failed for %s: %s", mid, exc)
                            with _jobs_lock:
                                _batch_job["completed"] = idx
                                _batch_job["failed_count"] += 1
                        time.sleep(0.05)

                    if updated_any:
                        _schedule_background_rebuild()
                else:
                    _run_competition_sync_subprocess(comp.key, season)
                    state.reload_runtime_datasets()
                    with _jobs_lock:
                        _batch_job["completed"] = len(target_ids)
                        _batch_job["refreshed_count"] = len(target_ids)

            with _jobs_lock:
                if _batch_job.get("id") == job_id:
                    rc = _batch_job["refreshed_count"]
                    fc = _batch_job["failed_count"]
                    _batch_job.update(
                        status="completed" if rc > 0 or fc == 0 else "failed",
                        current_match_id=None,
                        message=f"{rc} mac guncellendi" + (f", {fc} hata" if fc else ""),
                    )
        except Exception as exc:
            logger.exception("Batch match refresh failed")
            with _jobs_lock:
                if _batch_job.get("id") == job_id:
                    _batch_job.update(status="failed", current_match_id=None, message=str(exc))

    threading.Thread(target=_worker, daemon=True).start()
    return {**_batch_job, "already_running": False}


def is_rebuild_running() -> bool:
    with _rebuild_lock:
        return _rebuild_running


def get_batch_refresh_status() -> Dict[str, Any]:
    with _jobs_lock:
        return dict(_batch_job)
