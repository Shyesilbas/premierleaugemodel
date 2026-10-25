"""Sync fixtures and results for a non-Premier-League competition into SQLite.

Usage: python3 -m src.ingest.sync_competition_data --competition champions_league --season 2026_27
Only rows of the given competition_id are replaced; Premier League rows are never touched.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.db.database import get_db, init_db
from src.ingest.provider_factory import get_provider

logger = logging.getLogger("sync_competition_data")

COLUMNS = (
    "match_id", "season", "gameweek", "stage", "match_date", "kickoff_label", "day_label", "time_label",
    "ground_name", "home_id", "home_name", "home_abbr", "home_logo", "home_score",
    "away_id", "away_name", "away_abbr", "away_logo", "away_score", "status", "referee_name", "competition_id",
    "group_name", "leg", "advancing_team_id", "advance_reason", "home_penalties", "away_penalties",
)


def official_ranks(tables: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """team id -> {rank, played, points, group} from UEFA's standings feed."""
    ranks: Dict[str, Dict[str, Any]] = {}
    for table in tables:
        group = ((table.get("group") or {}).get("metaData") or {}).get("groupName") or ""
        label = group.replace("Group", "").strip() if group.startswith("Group") else None
        for item in table.get("items") or []:
            ranks[str(item["team"]["id"])] = {"rank": item["rank"], "played": item["played"], "points": item["points"], "group": label}
    return ranks


def sync_competition_season(competition_key: str, season: str, conn: sqlite3.Connection | None = None) -> int:
    comp = get_competition(competition_key)
    if comp.key == "premier_league":
        raise ValueError("Premier League is synced by sync_season_data.py")

    provider = get_provider(comp.key)
    rows: List[Dict[str, Any]] = []
    for raw in provider.fetch_fixtures(season):
        row = provider.normalize_fixture_record(raw)
        if row is not None:
            rows.append(row)
    if not rows:
        logger.warning("No fixtures returned for %s %s; database left unchanged.", comp.key, season)
        return 0

    own_conn = conn is None
    conn = conn or get_db()
    try:
        season = rows[0]["season"]
        # Upsert so statistics columns filled by other providers (corners, xG, ...) survive a fixture refresh.
        updates = ", ".join(f"{c} = excluded.{c}" for c in COLUMNS if c != "match_id")
        conn.executemany(
            f"INSERT INTO matches ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))}) "
            f"ON CONFLICT(match_id) DO UPDATE SET {updates}",
            [tuple(r[c] for c in COLUMNS) for r in rows],
        )
        keep = [r["match_id"] for r in rows]
        conn.execute(
            f"DELETE FROM matches WHERE competition_id = ? AND season = ? AND match_id NOT IN ({', '.join('?' * len(keep))})",
            (comp.id, season, *keep),
        )
        # UEFA's own tables carry the tie-break rules (head-to-head etc.), so keep their ranking as well.
        try:
            tables = provider.fetch_standings(season)
        except Exception as exc:  # the fixtures are the important part; standings can be fetched on the next run
            logger.warning("Official standings unavailable for %s %s: %s", comp.key, season, exc)
            tables = []
        if tables:
            conn.execute(
                "INSERT OR REPLACE INTO external_competition_payloads (competition_id, season, provider, kind, ref, payload, fetched_at_utc) VALUES (?,?,?,?,?,?,?)",
                (comp.id, season, "UEFA", "standings", "", json.dumps(official_ranks(tables)), datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
        conn.commit()
    finally:
        if own_conn:
            conn.close()
    logger.info("Wrote %d %s matches for %s.", len(rows), comp.key, rows[0]["season"])
    return len(rows)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", required=True, choices=["champions_league", "europa_league"])
    parser.add_argument("--season", default="2026_27")
    args = parser.parse_args()
    init_db()
    sync_competition_season(args.competition, args.season)


if __name__ == "__main__":
    main()
