"""Raw provider responses on disk, one folder tree per competition and provider.

Layout under ``data/competitions/<competition>/raw/<provider>/``::

    fixtures_<season>.json            the fixture list exactly as the provider returned it
    standings_<season>.json           the provider's official tables
    matches/<match_id>_<kind>.json    one file per match payload (stats, lineups, player-stats, ...)
    competition/<season>_<kind>[_<ref>].json   season-level payloads (squads, team stats, managers, standings)

The SQLite store keeps the parsed rows and a copy of the payloads for the API; these files are the archive and the
provenance, so a competition's raw data can be inspected, backed up or deleted without touching another one.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.config import competition_paths


def provider_dir(competition_key: str, provider: str) -> Path:
    return competition_paths(competition_key).raw / provider.lower()


def write_json(path: Path, payload: Any) -> Path:
    """Atomic write, so an interrupted sync never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
    return path


def match_payload_path(competition_key: str, provider: str, match_id: int, kind: str) -> Path:
    return provider_dir(competition_key, provider) / "matches" / f"{int(match_id)}_{kind}.json"


def competition_payload_path(competition_key: str, provider: str, season: str, kind: str, ref: str = "") -> Path:
    name = f"{season}_{kind}" + (f"_{ref}" if ref else "")
    return provider_dir(competition_key, provider) / "competition" / f"{name}.json"


def season_file_path(competition_key: str, provider: str, name: str, season: str) -> Path:
    return provider_dir(competition_key, provider) / f"{name}_{season}.json"


class CompetitionSyncRunning(RuntimeError):
    """Another sync of the same competition holds its lock."""


@contextmanager
def competition_lock(competition_key: str):
    """Cross-process lock per competition, so the button, cron and a terminal cannot sync the same one twice."""
    path = competition_paths(competition_key).raw / ".sync.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CompetitionSyncRunning(f"{competition_key} is already being synced") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
