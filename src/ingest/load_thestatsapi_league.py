"""Load a national league's raw TheStatsAPI files into the shared SQLite store.

Usage: python3 -m src.ingest.load_thestatsapi_league --competition la_liga [--seasons 2024_25 2025_26]
Reads what ``fetch_thestatsapi_league`` saved under ``data/competitions/<key>/raw/thestatsapi/`` (no network, no key):

1. fixtures and results become ``matches`` rows (``sync_competition_data``), with referee and venue from the match files;
2. every match payload (stats, lineups, player stats, timeline, shot map, odds) goes into ``external_match_payloads``;
   the statistics fill the match totals (corners, shots, cards, xG ...), odds fill ``external_match_odds``;
3. squads and team statistics go into ``external_competition_payloads``, and the clubs' managers are derived from the
   fixture list.

It can be repeated: payload rows are replaced, never duplicated.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.db.database import ensure_external_payload_tables, ensure_external_xg_table, get_db, init_db
from src.ingest.import_thestatsapi_odds import store_bookmaker_odds
from src.ingest.providers.thestatsapi_league import PROVIDER, local_match_id, local_team_id
from src.ingest.raw_store import match_payload_path, provider_dir, season_file_path
from src.ingest.sync_competition_data import sync_competition_season
from src.ingest.sync_thestatsapi_competition import _apply_stats

logger = logging.getLogger("load_thestatsapi_league")
KINDS = ("match", "stats", "lineups", "player_stats", "timeline", "shotmap", "odds")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path) -> Optional[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def available_seasons(competition_key: str) -> list:
    return sorted(p.stem.removeprefix("fixtures_") for p in provider_dir(competition_key, PROVIDER).glob("fixtures_*.json"))


def load_match_payloads(conn, comp_key: str, comp_id: int, season: str, fixtures: list) -> Dict[str, int]:
    counts = {"payloads": 0, "stats": 0, "odds": 0, "matches_with_files": 0}
    local_ids = {r[0] for r in conn.execute("SELECT match_id FROM matches WHERE competition_id = ? AND season = ?", (comp_id, season))}
    for fixture in fixtures:
        match_id = local_match_id(fixture["id"])
        if match_id not in local_ids:
            continue
        found = False
        for kind in KINDS:
            payload = _read(match_payload_path(comp_key, PROVIDER, match_id, kind))
            if payload is None:
                continue
            found = True
            db_kind = kind
            conn.execute(
                "INSERT OR REPLACE INTO external_match_payloads (match_id, provider, kind, provider_match_id, payload, fetched_at_utc) VALUES (?,?,?,?,?,?)",
                (match_id, PROVIDER, db_kind, fixture["id"], json.dumps(payload, ensure_ascii=False), _now()),
            )
            counts["payloads"] += 1
            if payload.get("unavailable"):
                continue
            if kind == "stats":
                try:
                    _apply_stats(conn, match_id, fixture, fixture.get("season_id", ""), payload.get("data") or {})
                    counts["stats"] += 1
                except (AttributeError, TypeError, ValueError) as exc:
                    logger.warning("Could not derive totals for %s: %s", fixture["id"], exc)
            elif kind == "odds":
                store_bookmaker_odds(conn, match_id, fixture["id"], fixture.get("season_id", ""), (payload.get("data") or {}).get("bookmakers") or [], _now())
                counts["odds"] += 1
        counts["matches_with_files"] += int(found)
    return counts


def load_competition_payloads(conn, comp_key: str, comp_id: int, season: str, fixtures: list) -> Dict[str, int]:
    counts = {"squads": 0, "team_stats": 0, "managers": 0}
    folder = provider_dir(comp_key, PROVIDER) / "competition"
    for path in sorted(folder.glob(f"{season}_*.json")):
        kind = "squad" if "_squad_" in path.name else "team_stats" if "_team_stats_" in path.name else None
        payload = _read(path)
        if kind is None or payload is None or payload.get("unavailable"):
            continue
        conn.execute(
            "INSERT OR REPLACE INTO external_competition_payloads (competition_id, season, provider, kind, ref, payload, fetched_at_utc) VALUES (?,?,?,?,?,?,?)",
            (comp_id, season, PROVIDER, kind, payload["team"]["id"], json.dumps(payload, ensure_ascii=False), _now()),
        )
        counts[f"{kind}s" if kind == "squad" else kind] += 1
    managers: Dict[str, Dict[str, str]] = {}
    for fixture in sorted(fixtures, key=lambda m: str(m.get("utc_date"))):  # the latest fixture wins: the current manager
        for side in ("home", "away"):
            manager = fixture.get(f"{side}_manager") or {}
            if manager.get("name"):
                managers[fixture[f"{side}_team"]["id"]] = {"name": manager["name"], "team": fixture[f"{side}_team"]["name"]}
    conn.execute(
        "INSERT OR REPLACE INTO external_competition_payloads (competition_id, season, provider, kind, ref, payload, fetched_at_utc) VALUES (?,?,?,?,?,?,?)",
        (comp_id, season, PROVIDER, "managers", "", json.dumps({"managers": managers}, ensure_ascii=False), _now()),
    )
    counts["managers"] = len(managers)
    return counts


def load_league(competition_key: str, seasons: Optional[list] = None) -> Dict[str, Any]:
    comp = get_competition(competition_key)
    init_db()
    conn = get_db()
    ensure_external_xg_table(conn)
    ensure_external_payload_tables(conn)
    summary: Dict[str, Any] = {}
    try:
        for season in seasons or available_seasons(competition_key):
            fixtures = json.loads(season_file_path(competition_key, PROVIDER, "fixtures", season).read_text(encoding="utf-8"))
            rows = sync_competition_season(competition_key, season, conn)
            summary[season] = {"matches": rows, **load_match_payloads(conn, competition_key, comp.id, season, fixtures),
                               **load_competition_payloads(conn, competition_key, comp.id, season, fixtures)}
            conn.commit()
            logger.info("%s %s: %s", competition_key, season, summary[season])
    finally:
        conn.close()
    return summary


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml")
    parser.add_argument("--seasons", nargs="+", help="season labels such as 2025_26; default: every season with saved fixtures")
    args = parser.parse_args()
    load_league(args.competition, args.seasons)


if __name__ == "__main__":
    main()
