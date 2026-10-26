"""Download a national league from TheStatsAPI into the per-competition raw folder.

Usage:
  THESTATSAPI_API_KEY=... python3 -m src.ingest.fetch_thestatsapi_league --competition la_liga \\
      [--seasons 2023_24 2024_25] [--kinds match stats lineups ...] [--skip-teams]

Writes ``data/competitions/<key>/raw/thestatsapi/``: ``fixtures_<season>.json`` (the match list, each entry tagged with its
season), ``matches/<local id>_<kind>.json`` for every finished match and ``competition/<season>_<kind>_<team>.json`` for
squads and team statistics. Files that already exist are skipped, so a run can be repeated or resumed. Requests are
spaced to stay under the 100 requests/minute limit. Odds are fetched from 2024/25 onward only (``--old-extras`` fetches them for older seasons too); shot maps are never fetched. The key is read from the
environment, never from a file.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.ingest.import_thestatsapi_xg import fetch_all_matches
from src.ingest.providers.thestatsapi_league import PROVIDER, local_match_id, local_team_id
from src.ingest.raw_store import competition_payload_path, match_payload_path, provider_dir, season_file_path, write_json
from src.ingest.sync_thestatsapi_competition import PacedClient

logger = logging.getLogger("fetch_thestatsapi_league")

ENDPOINTS = {
    "match": "",
    "stats": "/stats",
    "lineups": "/lineups",
    "player_stats": "/player-stats",
    "timeline": "/timeline",
    "odds": "/odds",
}
# Odds are only fetched from this season onward (a decision to save requests; --old-extras overrides it).
# Shot maps are never fetched, for any season (decision of 2026-10-25); files already on disk stay and are still loaded.
KIND_FIRST_START_YEAR = {"odds": 2024}
SEASON_LABEL = {"22/23": "2022_23"}


def season_key(season: Dict[str, Any]) -> str:
    return f"{season['start_year']}_{str(season['end_year'])[2:]}"


def migrate_flat_layout(competition_key: str) -> int:
    """Move files written by the first LaLiga download (``raw/matches/mt_*_<kind>.json``) into the provider layout."""
    from src.config import competition_paths

    paths = competition_paths(competition_key)
    flat = paths.matches_raw
    moved = 0
    for path in sorted(paths.raw.glob("matches_list_*.json")):  # fixture lists of the first download
        label = path.stem.removeprefix("matches_list_")
        label = f"20{label}" if len(label) == 5 else label
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        for fixture in fixtures:
            fixture["_season"] = label
        write_json(season_file_path(competition_key, PROVIDER, "fixtures", label), fixtures)
        path.unlink()
        moved += 1
    if not flat.exists():
        return moved
    for path in sorted(flat.glob("mt_*_*.json")):
        provider_id, _, kind = path.stem.rpartition("_")
        kind = {"player-stats": "player_stats"}.get(kind, kind)
        target = match_payload_path(competition_key, PROVIDER, local_match_id(provider_id), kind)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
            moved += 1
        else:
            path.unlink()
    return moved


def build_jobs(competition_key: str, season: str, fixtures: List[Dict[str, Any]], kinds: List[str], start_year: int, old_extras: bool = False) -> List[tuple]:
    jobs = []
    for fixture in fixtures:
        if fixture.get("status") != "finished":
            continue
        for kind in kinds:
            if not old_extras and start_year < KIND_FIRST_START_YEAR.get(kind, 0):
                continue
            if kind == "odds" and fixture.get("odds_available") is False:
                continue
            path = match_payload_path(competition_key, PROVIDER, local_match_id(fixture["id"]), kind)
            if not path.exists():
                jobs.append((fixture["id"], kind, path))
    return jobs


def fetch_league(
    competition_key: str,
    api_key: str,
    seasons: Optional[List[str]] = None,
    kinds: Optional[List[str]] = None,
    skip_teams: bool = False,
    workers: int = 6,
    old_extras: bool = False,
) -> Dict[str, Any]:
    """Download what is missing for a league; returns the ids of matches that got new files and the failures."""
    comp = get_competition(competition_key)
    if comp.provider != "thestatsapi" or not comp.provider_competition_id:
        raise ValueError(f"{comp.key} is not configured as a TheStatsAPI league in config/competitions.yaml")
    kinds = kinds or list(ENDPOINTS)
    logger.info("Moved %d files from the old flat layout", migrate_flat_layout(comp.key))

    client = PacedClient(api_key, minimum_interval=0.65)
    offered = client.get_json(f"/football/competitions/{comp.provider_competition_id}/seasons")["data"]
    wanted = [s for s in offered if int(s["start_year"]) >= 2022 and (not seasons or season_key(s) in seasons)]

    jobs: List[tuple] = []
    teams_by_season: Dict[str, Dict[str, str]] = {}
    api_season_ids: Dict[str, str] = {}
    for season in sorted(wanted, key=lambda s: s["start_year"], reverse=True):  # newest first, so recent seasons are usable early
        label = season_key(season)
        api_season_ids[label] = season["id"]
        fixtures = fetch_all_matches(client, comp.provider_competition_id, season["id"])
        for fixture in fixtures:
            fixture["_season"] = label
        write_json(season_file_path(comp.key, PROVIDER, "fixtures", label), fixtures)
        teams_by_season[label] = {f[s]["id"]: f[s]["name"] for f in fixtures for s in ("home_team", "away_team")}
        season_jobs = build_jobs(comp.key, label, fixtures, kinds, int(season["start_year"]), old_extras)
        logger.info("%s: %d matches listed, %d downloads queued", label, len(fixtures), len(season_jobs))
        jobs.extend(season_jobs)

    if not skip_teams:
        for label, teams in teams_by_season.items():
            for team_id in teams:
                for kind, path in (("squad", f"/football/teams/{team_id}/players"), ("team_stats", f"/football/teams/{team_id}/stats?season_id={api_season_ids[label]}")):
                    target = competition_payload_path(comp.key, PROVIDER, label, kind, team_id)
                    if not target.exists():
                        jobs.append((team_id, kind, target, path, teams[team_id]))
    logger.info("%d downloads in total", len(jobs))

    def download(job: tuple) -> Optional[str]:
        provider_id, kind, target = job[0], job[1], job[2]
        url = job[3] if len(job) > 3 else f"/football/matches/{provider_id}{ENDPOINTS[kind]}"
        try:
            payload = client.get_json(url)
        except RuntimeError as exc:
            if "HTTP 404" in str(exc) or "HTTP 409" in str(exc):
                payload = {"unavailable": True}
            else:
                return f"{provider_id} {kind}: {exc}"
        if len(job) > 3:
            payload = {"team": {"id": provider_id, "name": job[4]}, **payload}
        write_json(target, payload)
        return None

    failures: List[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, result in enumerate(pool.map(download, jobs), 1):
            if result:
                failures.append(result)
            if index % 200 == 0:
                logger.info("%d/%d", index, len(jobs))
    logger.info("done: %d saved, %d failures", len(jobs) - len(failures), len(failures))
    for line in failures[:20]:
        logger.warning(line)
    return {"downloads": len(jobs) - len(failures), "failures": failures, "match_provider_ids": sorted({j[0] for j in jobs if len(j) == 3})}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml")
    parser.add_argument("--seasons", nargs="+", help="season labels such as 2023_24; default: every season from 2022_23")
    parser.add_argument("--kinds", nargs="+", default=list(ENDPOINTS), choices=list(ENDPOINTS))
    parser.add_argument("--skip-teams", action="store_true", help="skip squads and team statistics")
    parser.add_argument("--workers", type=int, default=6, help="parallel downloads; the request rate stays under the API limit regardless")
    parser.add_argument("--old-extras", action="store_true", help="also fetch odds for seasons before 2024/25")
    args = parser.parse_args()
    key = os.environ.get("THESTATSAPI_API_KEY", "").strip()
    if not key:
        raise SystemExit("Set THESTATSAPI_API_KEY in the process environment; it is never read from or written to a file.")
    fetch_league(args.competition, key, args.seasons, args.kinds, args.skip_teams, args.workers, args.old_extras)


if __name__ == "__main__":
    main()
