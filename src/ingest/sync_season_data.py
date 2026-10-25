#!/usr/bin/env python3
"""Incrementally sync one Premier League season from PulseLive.

Refreshes the season-wide fixture list, downloads match data only for matches
that have newly completed/changed or are missing cached data, then rebuilds
the processed all-season datasets and SQLite database.
"""

import argparse
import fcntl
import json
import logging
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # works for `python3 src/...py` and `python -m`
from src.config import DATA_DIR, DEFAULT_SEASON  # noqa: E402
from src.ingest.files import atomic_write_json  # noqa: E402
from src.pipeline.rebuild import rebuild_derived_data  # noqa: E402
from src.ingest.fetch_season_data import (  # noqa: E402
    build_session,
    fetch_fixtures,
    fetch_match_details,
    fetch_match_stats,
    fetch_match_stream,
)

logger = logging.getLogger("sync_season_data")
SDP_API_BASE = "https://sdp-prem-prod.premier-league-prod.pulselive.com/api"
LOCK_EXIT_CODE = 3
DOWNLOAD_WORKERS = 4


class SyncAlreadyRunning(RuntimeError):
    """Another sync process holds the lock; two would write the same parquet/SQLite files."""


@contextmanager
def sync_lock():
    """Cross-process lock, so the API button, cron and a terminal run cannot overlap."""
    lock_path = DATA_DIR / "raw" / ".sync.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SyncAlreadyRunning("Baska bir veri guncellemesi calisiyor.") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_fixture_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    return data if isinstance(data, list) else data.get("content", [])


def fixture_is_completed(fixture: Optional[Dict[str, Any]]) -> bool:
    if not fixture:
        return False
    status = str(fixture.get("status") or "").upper()
    if status:
        return status == "C"
    teams = fixture.get("teams") or []
    has_scores = len(teams) >= 2 and all(team.get("score") is not None for team in teams[:2])
    return fixture.get("outcome") is not None or has_scores


def scores(fixture: Optional[Dict[str, Any]]) -> Tuple[Any, Any]:
    teams = (fixture or {}).get("teams") or []
    if len(teams) < 2:
        return None, None
    return teams[0].get("score"), teams[1].get("score")


def details_have_main_referee(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as stream:
            details = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return False
    for official in details.get("matchOfficials") or []:
        if official.get("role") == "MAIN" and (official.get("name") or {}).get("display"):
            return True
    return False


def normalize_team_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    value = re.sub(r"[^a-z0-9]+", "", value)
    aliases = {
        "brightonandhovealbion": "brightonhovealbion",
        "newcastle": "newcastleunited",
        "manutd": "manchesterunited",
        "mancity": "manchestercity",
        "nottmforest": "nottinghamforest",
        "spurs": "tottenhamhotspur",
    }
    return aliases.get(value, value)


def fixture_pair(fixture: Dict[str, Any]) -> Tuple[str, str]:
    teams = fixture.get("teams") or []
    if len(teams) < 2:
        return "", ""
    home = (teams[0].get("team") or {}).get("name") or ""
    away = (teams[1].get("team") or {}).get("name") or ""
    return normalize_team_name(home), normalize_team_name(away)


def match_label(fixture: Dict[str, Any]) -> str:
    teams = fixture.get("teams") or []
    if len(teams) < 2:
        return str(fixture.get("id"))
    return f"{(teams[0].get('team') or {}).get('name')} - {(teams[1].get('team') or {}).get('name')}"


def main_referee_name(officials: Any) -> Optional[str]:
    for entry in officials or []:
        official = entry.get("official") or entry.get("matchOfficial") or entry
        role = entry.get("type") or entry.get("role") or official.get("role")
        name_value = official.get("name")
        name = name_value.get("display") or name_value.get("name") if isinstance(name_value, dict) else name_value
        name = name or " ".join(
            part for part in (official.get("firstName"), official.get("lastName")) if part
        )
        if role in {"Referee", "MAIN"} and name:
            return str(name).strip()
    return None


def sync_upcoming_referees(
    session,
    season_name: str,
    fresh_fixtures: List[Dict[str, Any]],
    old_by_id: Dict[int, Dict[str, Any]],
    changed: Optional[List[str]] = None,
) -> int:
    """Refresh appointments for upcoming fixtures in the next two weeks.

    The legacy fixture/details feed does not publish these assignments. The
    current PL SDP API exposes them through /api/v1/matches/{id}/officials.
    """
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=14)
    targets = []
    for fixture in fresh_fixtures:
        kickoff_ms = (fixture.get("kickoff") or {}).get("millis")
        if kickoff_ms is None:
            continue
        kickoff = datetime.fromtimestamp(float(kickoff_ms) / 1000, tz=timezone.utc)
        if now < kickoff <= horizon:
            targets.append(fixture)
    if not targets:
        return 0

    season_id = season_name.split("_", 1)[0]
    matches_by_week: Dict[int, Dict[Tuple[str, str], str]] = {}
    updates = 0
    for fixture in targets:
        gameweek = int((fixture.get("gameweek") or {}).get("gameweek") or 0)
        if gameweek < 1:
            continue
        if gameweek not in matches_by_week:
            try:
                response = session.get(
                    f"{SDP_API_BASE}/v2/matches",
                    params={"competition": 8, "season": season_id, "matchweek": gameweek, "_limit": 50},
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                by_pair: Dict[Tuple[str, str], str] = {}
                for match in payload.get("data") or []:
                    pair = (
                        normalize_team_name((match.get("homeTeam") or {}).get("name") or ""),
                        normalize_team_name((match.get("awayTeam") or {}).get("name") or ""),
                    )
                    if all(pair):
                        by_pair[pair] = str(match.get("matchId") or "")
                matches_by_week[gameweek] = by_pair
            except Exception:
                logger.exception("Could not fetch PL matchweek %s for referee sync", gameweek)
                matches_by_week[gameweek] = {}

        pair = fixture_pair(fixture)
        external_match_id = matches_by_week[gameweek].get(pair)
        if not external_match_id:
            logger.warning("Could not map referee appointment: %s GW%s %s", season_name, gameweek, pair)
            continue
        try:
            response = session.get(
                f"{SDP_API_BASE}/v1/matches/{external_match_id}/officials",
                timeout=20,
            )
            response.raise_for_status()
            officials = response.json().get("matchOfficials") or []
        except Exception:
            logger.exception("Could not fetch officials for PL match %s", external_match_id)
            continue

        referee = main_referee_name(officials)
        if not referee:
            # Preserve a previously sourced appointment if the provider has
            # temporarily returned an empty list.
            old = old_by_id.get(int(fixture.get("id", -1)), {})
            referee = main_referee_name(old.get("matchOfficials"))
            if not referee:
                continue
            officials = old.get("matchOfficials") or []

        existing_referee = main_referee_name(fixture.get("matchOfficials"))
        if existing_referee != referee:
            fixture["matchOfficials"] = [{
                "role": "MAIN",
                "name": {"display": referee},
            }]
            updates += 1
            if changed is not None:
                changed.append(f"{match_label(fixture)} ({referee})")
            logger.info("Referee assigned for %s GW%s %s: %s", season_name, gameweek, pair, referee)
    return updates




def fetch_one(session, match_id: int, kind: str) -> bool:
    fetchers = {
        "stats": fetch_match_stats,
        "stream": fetch_match_stream,
        "details": fetch_match_details,
    }
    try:
        result = fetchers[kind](session, match_id)
        if not result:
            logger.warning("No %s data returned for match %s", kind, match_id)
            return False
        path = DATA_DIR / "raw" / "matches" / f"{match_id}_{kind}.json"
        atomic_write_json(path, result)
        return True
    except Exception:
        logger.exception("Could not fetch %s for match %s", kind, match_id)
        return False


def sync_season(
    season_name: str,
    season_id: Optional[int] = None,
    comps: int = 1,
    delay: float = 0.1,
    dry_run: bool = False,
    rebuild: bool = True,
    referees_only: bool = False,
) -> Dict[str, int]:
    raw_dir = DATA_DIR / "raw"
    matches_dir = raw_dir / "matches"
    fixture_path = raw_dir / f"fixtures_{season_name}.json"
    pending_path = raw_dir / f".sync_pending_{season_name}"
    old_fixtures = load_fixture_file(fixture_path)

    if season_id is None:
        for fixture in old_fixtures:
            comp_season = (fixture.get("gameweek") or {}).get("compSeason") or {}
            if comp_season.get("id") is not None:
                season_id = int(comp_season["id"])
                break
    if season_id is None:
        raise ValueError(f"No cached compSeason ID for {season_name}; pass --season-id")

    session = build_session()
    fresh_fixtures = fetch_fixtures(session, season_id, comps=comps)
    old_by_id = {int(f["id"]): f for f in old_fixtures if f.get("id") is not None}
    fresh_by_id = {int(f["id"]): f for f in fresh_fixtures if f.get("id") is not None}

    referee_matches: List[str] = []
    appointment_updates = sync_upcoming_referees(session, season_name, fresh_fixtures, old_by_id, referee_matches)
    fixture_changes = sum(
        {
            key: value for key, value in old_by_id.get(mid, {}).items()
            if key != "matchOfficials"
        }
        != {
            key: value for key, value in fixture.items()
            if key != "matchOfficials"
        }
        for mid, fixture in fresh_by_id.items()
    )
    appointment_changes = sum(
        main_referee_name(old_by_id.get(mid, {}).get("matchOfficials"))
        != main_referee_name(fixture.get("matchOfficials"))
        for mid, fixture in fresh_by_id.items()
    )
    if referees_only:
        # Store only the appointments; old fixture state stays so a later full sync still sees finished matches.
        merged = [
            {**f, "matchOfficials": officials}
            if (officials := fresh_by_id.get(int(f.get("id", -1)), {}).get("matchOfficials")) else f
            for f in old_fixtures
        ]
        if appointment_changes and not dry_run:
            atomic_write_json(fixture_path, merged)
            if rebuild:
                rebuild_derived_data()
        logger.info("Referee-only sync: %s appointments changed", appointment_changes)
        return {"fixtures": len(fresh_fixtures), "fixture_changes": 0, "referee_appointments_updated": appointment_changes,
                "completed_or_score_changes": 0, "matches_with_downloads": 0, "files_downloaded": 0, "failed_downloads": 0,
                "matches": referee_matches}
    completed_changes = []
    needs_download: Dict[int, List[str]] = {}
    for match_id, fixture in fresh_by_id.items():
        if not fixture_is_completed(fixture):
            continue
        old_fixture = old_by_id.get(match_id)
        newly_completed = not fixture_is_completed(old_fixture)
        score_changed = scores(old_fixture) != scores(fixture)
        force_match_refresh = newly_completed or score_changed
        if force_match_refresh:
            completed_changes.append(match_id)

        missing = []
        for kind in ("stats", "stream", "details"):
            cached_path = matches_dir / f"{match_id}_{kind}.json"
            missing_file = not cached_path.exists()
            missing_referee = (
                kind == "details"
                and not details_have_main_referee(cached_path)
                and (not cached_path.exists() or time.time() - cached_path.stat().st_mtime >= 6 * 60 * 60)
            )
            if (force_match_refresh and kind in ("stats", "stream", "details")) or missing_file or missing_referee:
                missing.append(kind)
        if missing:
            needs_download[match_id] = missing

    logger.info(
        "Season %s: %s fixtures; %s fixture records changed; %s referee appointments refreshed; %s newly completed/score-updated; %s matches need data downloads",
        season_name, len(fresh_fixtures), fixture_changes, appointment_updates, len(completed_changes), len(needs_download),
    )
    summary = {
        "fixtures": len(fresh_fixtures),
        "fixture_changes": fixture_changes,
        "referee_appointments_updated": appointment_changes,
        "completed_or_score_changes": len(completed_changes),
        "matches_with_downloads": len(needs_download),
        "files_downloaded": 0,
        "failed_downloads": 0,
        "matches": [],
    }

    if dry_run:
        for match_id, kinds in sorted(needs_download.items()):
            logger.info("Would fetch match %s: %s", match_id, ", ".join(kinds))
        return summary

    matches_dir.mkdir(parents=True, exist_ok=True)
    failed_match_ids = set()

    def download(job: Tuple[int, str]) -> Tuple[int, bool]:
        match_id, kind = job
        ok = fetch_one(session, match_id, kind)
        time.sleep(delay)
        return match_id, ok

    jobs = [(match_id, kind) for match_id, kinds in sorted(needs_download.items()) for kind in kinds]
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as pool:
        for match_id, ok in pool.map(download, jobs):
            if ok:
                summary["files_downloaded"] += 1
            else:
                failed_match_ids.add(match_id)
                summary["failed_downloads"] += 1

    summary["matches"] = [match_label(fresh_by_id[mid]) for mid in sorted(needs_download) if mid not in failed_match_ids]

    # Keep old fixture state for failed matches so their score/status change is
    # detected and retried the next time the sync runs.
    fixtures_to_save = [
        old_by_id.get(int(fixture["id"]), fixture)
        if int(fixture.get("id", -1)) in failed_match_ids
        else fixture
        for fixture in fresh_fixtures
    ]
    raw_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(fixture_path, fixtures_to_save)

    rebuild_needed = bool(
        fixture_changes or appointment_changes or summary["files_downloaded"] or pending_path.exists()
    )
    if rebuild_needed:
        pending_path.write_text("Derived datasets need rebuilding.\n", encoding="utf-8")

    if rebuild and rebuild_needed:
        rebuild_derived_data()
        pending_path.unlink(missing_ok=True)
    elif rebuild:
        logger.info("No data changes; skipping processed dataset rebuild")
    elif rebuild_needed:
        logger.info("Derived data rebuild deferred; a later run without --no-rebuild will complete it")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Incrementally sync a Premier League season.")
    parser.add_argument("--season-name", default=DEFAULT_SEASON, help="Local season label, e.g. 2026_27 (default: current season)")
    parser.add_argument("--season-id", type=int, help="PulseLive compSeason ID (inferred from cached fixtures when omitted)")
    parser.add_argument("--comps", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.1, help="Pause between match-data requests")
    parser.add_argument("--dry-run", action="store_true", help="Fetch fixture index and report planned downloads without writing data")
    parser.add_argument("--referees-only", action="store_true", help="Only refresh upcoming referee appointments; skip match downloads")
    parser.add_argument("--no-rebuild", action="store_true", help="Do not regenerate Parquet, feature, and SQLite data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    try:
        with sync_lock():
            summary = sync_season(
                season_name=args.season_name,
                season_id=args.season_id,
                comps=args.comps,
                delay=args.delay,
                dry_run=args.dry_run,
                rebuild=not args.no_rebuild,
                referees_only=args.referees_only,
            )
    except SyncAlreadyRunning as exc:
        logger.error("%s", exc)
        raise SystemExit(LOCK_EXIT_CODE)
    logger.info("Sync summary: %s", summary)
    # Printed before any failure exit so a partial run still reports the matches it did sync.
    print("SYNC_RESULT " + json.dumps(
        {"matches": summary.get("matches", []), "failed_downloads": summary["failed_downloads"]}, ensure_ascii=False))
    if summary["failed_downloads"]:
        logger.error("Some match files failed; rerun the sync to retry them.")
        raise SystemExit(1)
    if not args.dry_run and not args.no_rebuild and (summary["fixture_changes"] or summary["files_downloaded"]):
        logger.info("Restart the API process to reload its in-memory datasets and prediction features.")


if __name__ == "__main__":
    main()
