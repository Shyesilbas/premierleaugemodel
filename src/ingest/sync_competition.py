"""Bring one competition's data up to date; what the "Veri güncelle" button runs outside the Premier League.

Usage: python3 -m src.ingest.sync_competition --competition la_liga --season 2026_27

What it does (the Premier League has its own pipeline, ``sync_season_data``):

* a TheStatsAPI league (la_liga ...): downloads the files still missing for the season (``fetch_thestatsapi_league``), refreshes the
  full-season calendar (``fetch_openfootball_schedule``) and loads everything (``load_thestatsapi_league``);
* a UEFA cup: refreshes fixtures, results and the official table from UEFA and, when a TheStatsAPI key is available, the match
  statistics, lineups and player data (``sync_competition_data`` + ``sync_thestatsapi_competition``).

Reads:  TheStatsAPI, UEFA APIs, openfootball.
Writes: ``data/competitions/<key>/raw/...`` and ``data/football.db``.
Needs:  ``THESTATSAPI_API_KEY`` in the environment for everything except the UEFA fixtures. Takes a per-competition lock, prints one
        ``SYNC_RESULT`` line (the matches that received new data) for the API, and exits with code 3 when another sync of the same
        competition is running.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any, Dict, List

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.ingest.raw_store import CompetitionSyncRunning, competition_lock, season_file_path

logger = logging.getLogger("sync_competition")
LOCK_EXIT_CODE = 3


def _match_names(competition_key: str, season: str, provider_ids: List[str]) -> List[str]:
    from src.ingest.providers.thestatsapi_league import PROVIDER

    path = season_file_path(competition_key, PROVIDER, "fixtures", season)
    if not path.exists() or not provider_ids:
        return []
    wanted = set(provider_ids)
    names = []
    for fixture in json.loads(path.read_text(encoding="utf-8")):
        if fixture["id"] in wanted:
            score = fixture.get("score") or {}
            names.append(f"{fixture['home_team']['name']} {score.get('home')} - {score.get('away')} {fixture['away_team']['name']}")
    return names


def sync_statsapi_league(competition_key: str, season: str, api_key: str) -> Dict[str, Any]:
    from src.ingest.fetch_thestatsapi_league import fetch_league
    from src.ingest.load_thestatsapi_league import load_league

    from src.ingest.fetch_openfootball_schedule import fetch_schedule

    fetched = fetch_league(competition_key, api_key, [season])
    fetch_schedule(competition_key, [season])  # the weeks the provider has not published yet
    load_league(competition_key, [season])
    return {"matches": _match_names(competition_key, season, fetched["match_provider_ids"]), "failed_downloads": len(fetched["failures"])}


def sync_uefa_cup(competition_key: str, season: str, api_key: str) -> Dict[str, Any]:
    from src.competitions.registry import get_competition as comp_for
    from src.db.database import ensure_external_payload_tables, ensure_external_xg_table, get_db, init_db
    from src.ingest.sync_competition_data import sync_competition_season
    from src.ingest.sync_thestatsapi_competition import PacedClient, sync_matches

    init_db()
    rows = sync_competition_season(competition_key, season)
    failures = 0
    if api_key:
        comp = comp_for(competition_key)
        conn = get_db()
        try:
            ensure_external_xg_table(conn)
            ensure_external_payload_tables(conn)
            client = PacedClient(api_key, 0.65)
            counts = sync_matches(client, conn, competition_key, comp.id, season, False, None)
            logger.info("TheStatsAPI details: %s", counts)
        finally:
            conn.close()
    return {"matches": [f"{rows} maç güncellendi"] if rows else [], "failed_downloads": failures}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (not premier_league)")
    parser.add_argument("--season", required=True, help="season label such as 2026_27")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    api_key = os.environ.get("THESTATSAPI_API_KEY", "").strip()
    try:
        with competition_lock(comp.key):
            if comp.provider == "thestatsapi":
                if not api_key:
                    raise SystemExit("THESTATSAPI_API_KEY tanımlı değil; bu lig yalnızca TheStatsAPI'den beslenir.")
                result = sync_statsapi_league(comp.key, args.season, api_key)
            elif comp.provider == "uefa":
                result = sync_uefa_cup(comp.key, args.season, api_key)
            else:
                raise SystemExit(f"{comp.key}: bu turnuva kendi boru hattıyla güncellenir (sync_season_data).")
    except CompetitionSyncRunning:
        raise SystemExit(LOCK_EXIT_CODE)
    print("SYNC_RESULT " + json.dumps(result, ensure_ascii=False))
    if result["failed_downloads"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
