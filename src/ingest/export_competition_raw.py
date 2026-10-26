"""One-off export of what the database already holds for the European cups into per-competition raw files.

Usage: python3 -m src.ingest.export_competition_raw [--no-uefa]

What it does: the TheStatsAPI payloads that were stored only in SQLite (match statistics, lineups, player stats, timeline,
odds, squads, team statistics) are written as files, and the UEFA fixture and standings feeds are fetched again and saved
exactly as returned. Existing files are left alone, so it can be repeated. From now on the sync scripts write these files
themselves; this exists to archive what was synced before they did.

Reads:  ``data/football.db`` (``external_match_payloads``, ``external_competition_payloads``) and the public UEFA APIs.
Writes: ``data/competitions/champions_league|europa_league/raw/thestatsapi/`` and ``raw/uefa/``.
Needs:  no key (the UEFA part can be skipped with --no-uefa to work offline).
"""

from __future__ import annotations

import argparse
import json
import logging

from src.config import configure_logging
from src.db.database import get_db
from src.ingest.providers.uefa import UefaProvider
from src.ingest.raw_store import competition_payload_path, match_payload_path, season_file_path, write_json

logger = logging.getLogger("export_competition_raw")

COMPETITIONS = {2: "champions_league", 3: "europa_league"}
SEASONS = ("2022_23", "2023_24", "2024_25", "2025_26", "2026_27")


def export_database_payloads(conn) -> dict:
    counts = {"match_payloads": 0, "competition_payloads": 0, "skipped": 0}
    rows = conn.execute(
        """SELECT p.match_id, p.provider, p.kind, p.payload, m.competition_id
           FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id
           WHERE m.competition_id IN (2, 3)"""
    )
    for match_id, provider, kind, payload, competition_id in rows:
        path = match_payload_path(COMPETITIONS[competition_id], provider, match_id, kind)
        if path.exists():
            counts["skipped"] += 1
            continue
        write_json(path, json.loads(payload))
        counts["match_payloads"] += 1
    rows = conn.execute(
        "SELECT competition_id, season, provider, kind, ref, payload FROM external_competition_payloads WHERE competition_id IN (2, 3)"
    )
    for competition_id, season, provider, kind, ref, payload in rows:
        path = competition_payload_path(COMPETITIONS[competition_id], provider, season, kind, ref)
        if path.exists():
            counts["skipped"] += 1
            continue
        write_json(path, json.loads(payload))
        counts["competition_payloads"] += 1
    return counts


def export_uefa_feeds() -> int:
    saved = 0
    for competition_id, key in COMPETITIONS.items():
        provider = UefaProvider(competition_id=competition_id, competition_key=key)
        for season in SEASONS:
            for name, fetch in (("fixtures", provider.fetch_fixtures), ("standings", provider.fetch_standings)):
                path = season_file_path(key, "uefa", name, season)
                if path.exists():
                    continue
                write_json(path, fetch(season))
                saved += 1
    return saved


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-uefa", action="store_true", help="skip re-fetching the UEFA feeds")
    args = parser.parse_args()
    conn = get_db()
    try:
        logger.info("Database payloads: %s", export_database_payloads(conn))
    finally:
        conn.close()
    if not args.no_uefa:
        logger.info("UEFA feed files saved: %d", export_uefa_feeds())


if __name__ == "__main__":
    main()
