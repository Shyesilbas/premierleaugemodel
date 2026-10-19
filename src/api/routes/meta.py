"""Data version, model reload and season sync (admin) routes."""

import json
import logging
import subprocess
import sys
import threading
import uuid
from fastapi import HTTPException, Query
from src.config import DEFAULT_SEASON, ROOT as BASE_DIR, SEASONS
from typing import Any, Dict, List
from src.api import state
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("api_server")

_sync_job_lock = threading.Lock()


_sync_job: Dict[str, Any] = {"id": None, "status": "idle", "season": None, "message": None, "output": ""}


@router.get("/api/data-version")
def get_data_version():
    """Changes whenever the API reloads data; the frontend drops its localStorage caches on change."""
    return {"version": str(state._loaded_data_version)}


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

        state.reload_runtime_datasets()
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


@router.post("/api/admin/sync-season")
def start_season_sync(season: str = Query(DEFAULT_SEASON), kind: str = Query("matches")):
    """Start a background sync: matches (results + stats), referees, or lineups."""
    if kind not in {"matches", "referees", "lineups"}:
        raise HTTPException(status_code=400, detail="Unsupported sync kind")
    if season not in set(SEASONS):
        raise HTTPException(status_code=400, detail="Unsupported season")
    with _sync_job_lock:
        if _sync_job.get("status") in {"queued", "running"}:
            return {**_sync_job, "already_running": True}
        job_id = str(uuid.uuid4())
        _sync_job.update(id=job_id, status="running", season=season, kind=kind, message="Başlandı...", matches=[], output="")
    thread = threading.Thread(target=_run_season_sync_job, args=(job_id, season, kind), daemon=True)
    thread.start()
    return {**_sync_job, "already_running": False}


@router.post("/api/admin/reload-models")
def admin_reload_models():
    """Reload all runtime datasets and ML model artifacts."""
    state.reload_runtime_datasets()
    return {"status": "success", "message": "All models and feature datasets reloaded successfully"}


@router.get("/api/admin/sync-season")
def get_season_sync_status():
    with _sync_job_lock:
        return dict(_sync_job)
