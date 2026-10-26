"""Data version, model reload and season sync (admin) routes."""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import uuid
from fastapi import Depends, HTTPException, Query
from src.config import DB_PATH, DEFAULT_SEASON, ROOT as BASE_DIR, SEASONS
from typing import Any, Dict, List
from src.api import state
from src.api.security import require_admin_token
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("api_server")

_sync_job_lock = threading.Lock()


_sync_job: Dict[str, Any] = {"id": None, "status": "idle", "season": None, "message": None, "output": ""}


@router.get("/api/data-version")
def get_data_version():
    """Changes whenever the API reloads data; the frontend drops its localStorage caches on change."""
    # Also changes when the database file does, so a league loaded from the command line drops the browsers' cached copies.
    stamps = [p.stat().st_mtime_ns for p in (DB_PATH, DB_PATH.with_name(DB_PATH.name + "-wal")) if p.exists()]
    return {"version": f"{state._loaded_data_version}-{max(stamps, default=0)}"}


@router.get("/api/competitions")
def get_competitions():
    """Returns list of registered football competitions and tournaments."""
    from src.competitions.registry import CompetitionRegistry
    return [
        {
            "key": c.key,
            "id": c.id,
            "name": c.name,
            "type": c.type,
            "country": c.country,
            "uefa_coefficient": c.uefa_coefficient,
            "format": c.format,
            "default_season": c.default_season,
            "has_npxg": c.has_npxg,
            "has_model": c.has_model,
            "sync_kinds": list(c.sync_kinds),
            "data_source": c.provider,
        }
        for c in CompetitionRegistry.list_all()
    ]


def _sync_command(kind: str, season: str, competition: str = "premier_league") -> List[str]:
    from src.competitions.registry import get_competition

    comp = get_competition(competition)
    if comp.provider != "pulselive":  # every other competition has one pipeline, which also covers referees
        return [sys.executable, "-m", "src.ingest.sync_competition", "--competition", comp.key, "--season", season]
    sync_season_script = str(BASE_DIR / "src" / "ingest" / "sync_season_data.py")
    return {
        "matches": [sys.executable, sync_season_script, "--season-name", season],
        "referees": [sys.executable, sync_season_script, "--season-name", season, "--referees-only"],
        # 2h window: official XIs are published roughly 60-75 min before kickoff
        "lineups": [sys.executable, "-m", "src.ingest.sync_prematch_lineups", "--season", season, "--hours-ahead", "2"],
    }[kind]


SYNC_TIMEOUT_SECONDS = 60 * 30
SYNC_LOCKED_EXIT_CODE = 3  # keep in step with LOCK_EXIT_CODE in sync_season_data
_OUTPUT_TAIL = 6000


def _parse_sync_result(stdout: str) -> Dict[str, Any]:
    for line in stdout.splitlines():
        if line.startswith("SYNC_RESULT "):
            return json.loads(line[len("SYNC_RESULT "):])
    return {}


def _run_season_sync_job(job_id: str, season: str, kind: str = "matches", competition: str = "premier_league") -> None:
    command = _sync_command(kind, season, competition)
    lines: List[str] = []
    try:
        process = subprocess.Popen(
            command,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,  # own process group, so a timeout also stops the rebuild steps it spawned
        )

        def kill_group() -> None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        timer = threading.Timer(SYNC_TIMEOUT_SECONDS, kill_group)
        timer.start()
        try:
            for line in process.stdout:
                lines.append(line)
                with _sync_job_lock:
                    if _sync_job.get("id") == job_id:
                        _sync_job["output"] = "".join(lines)[-_OUTPUT_TAIL:]
            returncode = process.wait()
        finally:
            timer.cancel()
        stdout = "".join(lines)
        output = stdout.strip()[-_OUTPUT_TAIL:]
        result = _parse_sync_result(stdout)

        if returncode == SYNC_LOCKED_EXIT_CODE:
            update = dict(status="failed", message="Baska bir veri guncellemesi zaten calisiyor.", output=output)
        elif returncode != 0 and not result:
            update = dict(status="failed", message="Veri güncellemesi tamamlanamadı.", output=output)
        else:
            # A partial run (some downloads failed) still saved and rebuilt the rest, so reload what it did finish.
            state.reload_runtime_datasets()
            matches = result.get("matches", [])
            failed = result.get("failed_downloads", 0)
            if returncode != 0:
                update = dict(status="failed", matches=matches, output=output,
                              message=f"Kısmen tamamlandı: {failed} dosya indirilemedi, tekrar deneyin.")
            else:
                update = dict(status="completed", matches=matches, output=output,
                              message="Veri bulundu" if matches else "Veri bulunamadı")
        with _sync_job_lock:
            if _sync_job.get("id") == job_id:
                _sync_job.update(update)
    except Exception as exc:
        logger.exception("Season sync job failed")
        with _sync_job_lock:
            if _sync_job.get("id") == job_id:
                _sync_job.update(status="failed", message=str(exc), output="")


@router.post("/api/admin/sync-season", dependencies=[Depends(require_admin_token)])
def start_season_sync(season: str = Query(DEFAULT_SEASON), kind: str = Query("matches"), competition: str = Query("premier_league")):
    """Start a background sync of one competition: matches (results + stats), and for the Premier League also referees or lineups."""
    from src.competitions.registry import get_competition

    try:
        comp = get_competition(competition)
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown competition")
    if kind not in comp.sync_kinds:
        raise HTTPException(status_code=400, detail="Unsupported sync kind")
    if season not in set(SEASONS):
        raise HTTPException(status_code=400, detail="Unsupported season")
    with _sync_job_lock:
        if _sync_job.get("status") in {"queued", "running"}:
            return {**_sync_job, "already_running": True}
        job_id = str(uuid.uuid4())
        _sync_job.update(id=job_id, status="running", season=season, kind=kind, competition=comp.key, message="Başlandı...", matches=[], output="")
    thread = threading.Thread(target=_run_season_sync_job, args=(job_id, season, kind, comp.key), daemon=True)
    thread.start()
    return {**_sync_job, "already_running": False}


@router.post("/api/admin/reload-models", dependencies=[Depends(require_admin_token)])
def admin_reload_models():
    """Reload all runtime datasets and ML model artifacts."""
    state.reload_runtime_datasets()
    return {"status": "success", "message": "All models and feature datasets reloaded successfully"}


@router.get("/api/admin/sync-season", dependencies=[Depends(require_admin_token)])
def get_season_sync_status():
    with _sync_job_lock:
        return dict(_sync_job)
