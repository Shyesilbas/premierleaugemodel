#!/usr/bin/env python3
"""Incrementally sync one Premier League season from PulseLive.

Refreshes the season-wide fixture list, downloads match data only for matches
that have newly completed/changed or are missing cached data, then rebuilds
the processed all-season datasets and SQLite database.
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fetch_season_data import (
    build_session,
    fetch_fixtures,
    fetch_match_details,
    fetch_match_stats,
    fetch_match_stream,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
logger = logging.getLogger("sync_season_data")


def load_fixture_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    return data if isinstance(data, list) else data.get("content", [])


def fixture_is_completed(fixture: Dict[str, Any]) -> bool:
    teams = fixture.get("teams") or []
    has_scores = len(teams) >= 2 and all(team.get("score") is not None for team in teams[:2])
    return fixture.get("status") == "C" or fixture.get("outcome") is not None or has_scores


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


def atomic_write_json(path: Path, payload: Any) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    temp_path.replace(path)


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


def rebuild_derived_data() -> None:
    commands = [
        [sys.executable, "src/processing/process_season_data.py", "--season-name", "all"],
        [sys.executable, "src/features/build_features.py"],
        [sys.executable, "-m", "src.db.database"],
    ]
    for command in commands:
        logger.info("Running: %s", " ".join(command))
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def sync_season(
    season_name: str,
    season_id: Optional[int] = None,
    comps: int = 1,
    delay: float = 0.1,
    dry_run: bool = False,
    rebuild: bool = True,
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

    fixture_changes = sum(old_by_id.get(mid) != fixture for mid, fixture in fresh_by_id.items())
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
        "Season %s: %s fixtures; %s fixture records changed; %s newly completed/score-updated; %s matches need data downloads",
        season_name, len(fresh_fixtures), fixture_changes, len(completed_changes), len(needs_download),
    )
    summary = {
        "fixtures": len(fresh_fixtures),
        "fixture_changes": fixture_changes,
        "completed_or_score_changes": len(completed_changes),
        "matches_with_downloads": len(needs_download),
        "files_downloaded": 0,
        "failed_downloads": 0,
    }

    if dry_run:
        for match_id, kinds in sorted(needs_download.items()):
            logger.info("Would fetch match %s: %s", match_id, ", ".join(kinds))
        return summary

    matches_dir.mkdir(parents=True, exist_ok=True)
    failed_match_ids = set()
    for match_id, kinds in sorted(needs_download.items()):
        for kind in kinds:
            if fetch_one(session, match_id, kind):
                summary["files_downloaded"] += 1
            else:
                failed_match_ids.add(match_id)
                summary["failed_downloads"] += 1
            time.sleep(delay)

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

    rebuild_needed = bool(fixture_changes or summary["files_downloaded"] or pending_path.exists())
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
    parser.add_argument("--season-name", default="2026_27", help="Local season label, e.g. 2026_27")
    parser.add_argument("--season-id", type=int, help="PulseLive compSeason ID (inferred from cached fixtures when omitted)")
    parser.add_argument("--comps", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.1, help="Pause between match-data requests")
    parser.add_argument("--dry-run", action="store_true", help="Fetch fixture index and report planned downloads without writing data")
    parser.add_argument("--no-rebuild", action="store_true", help="Do not regenerate Parquet, feature, and SQLite data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    summary = sync_season(
        season_name=args.season_name,
        season_id=args.season_id,
        comps=args.comps,
        delay=args.delay,
        dry_run=args.dry_run,
        rebuild=not args.no_rebuild,
    )
    logger.info("Sync summary: %s", summary)
    if summary["failed_downloads"]:
        logger.error("Some match files failed; rerun the sync to retry them.")
        raise SystemExit(1)
    if not args.dry_run and not args.no_rebuild and (summary["fixture_changes"] or summary["files_downloaded"]):
        logger.info("Restart the API process to reload its in-memory datasets and prediction features.")


if __name__ == "__main__":
    main()
