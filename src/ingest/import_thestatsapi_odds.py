"""Import historical 1X2 opening and last-seen odds for a local date window."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.import_thestatsapi_xg import (
    BASE_DIR,
    PROVIDER,
    TheStatsApiClient,
    find_local_match,
    normalize_team,
)


DB_PATH = BASE_DIR / "data" / "premier_league.db"


def parse_local_date(match: sqlite3.Row) -> str | None:
    if match["match_date"]:
        return str(match["match_date"])[:10]
    kickoff = str(match["kickoff_label"] or "")
    try:
        return datetime.strptime(kickoff.split(",")[0].strip(), "%a %d %b %Y").date().isoformat()
    except ValueError:
        return None


def read_local_date_window(conn: sqlite3.Connection, season: str, date_from: str) -> list[sqlite3.Row]:
    rows = conn.execute("SELECT * FROM matches WHERE season = ?", (season,)).fetchall()
    return [row for row in rows if (parse_local_date(row) or "") >= date_from]


def import_odds(args: argparse.Namespace) -> dict[str, Any]:
    client = TheStatsApiClient(__import__("os").environ.get("THESTATSAPI_API_KEY", "").strip(), args.minimum_interval)
    if not client.api_key:
        raise RuntimeError("Set THESTATSAPI_API_KEY in the process environment; it is never stored in a file.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS external_match_odds (
            match_id INTEGER NOT NULL REFERENCES matches(match_id),
            provider TEXT NOT NULL,
            provider_match_id TEXT NOT NULL,
            provider_season_id TEXT NOT NULL,
            bookmaker TEXT NOT NULL,
            home_open REAL,
            draw_open REAL,
            away_open REAL,
            home_last_seen REAL,
            draw_last_seen REAL,
            away_last_seen REAL,
            fetched_at_utc TEXT NOT NULL,
            PRIMARY KEY (match_id, provider, bookmaker)
        )
    """)
    conn.commit()

    season_response = client.get_json(f"/football/competitions/{args.competition_id}/seasons")
    target = next(
        (
            season for season in season_response.get("data", [])
            if f"{season.get('start_year')}_{int(season.get('end_year') or 0) % 100:02d}" == args.season
        ),
        None,
    )
    if target is None:
        raise RuntimeError(f"Season {args.season} was not returned by TheStatsAPI")

    api_matches: list[dict[str, Any]] = []
    page = 1
    while True:
        response = client.get_json(
            "/football/matches",
            {"competition_id": args.competition_id, "season_id": target["id"], "page": page, "per_page": 100},
        )
        api_matches.extend(response.get("data") or [])
        pages = int((response.get("meta") or {}).get("total_pages", 1))
        if page >= pages:
            break
        page += 1

    local_rows = read_local_date_window(conn, args.season, args.date_from)
    local_by_teams = {
        (normalize_team(row["home_name"]), normalize_team(row["away_name"])): row
        for row in local_rows
    }
    matches_to_fetch = []
    unmatched = 0
    for match in api_matches:
        key = (
            normalize_team((match.get("home_team") or {}).get("name", "")),
            normalize_team((match.get("away_team") or {}).get("name", "")),
        )
        local = local_by_teams.get(key)
        if local is None:
            continue
        if (parse_local_date(local) or "") < args.date_from:
            continue
        matches_to_fetch.append((match, local))

    counts: dict[str, Any] = {
        "local_matches_in_window": len(local_rows),
        "provider_matches_listed": len(api_matches),
        "matched_fixtures": len(matches_to_fetch),
        "requests_with_odds": 0,
        "bookmaker_rows": 0,
        "unmatched_local": max(0, len(local_rows) - len(matches_to_fetch)),
        "bookmakers": {},
    }

    for index, (match, local) in enumerate(matches_to_fetch, start=1):
        if match.get("odds_available") is False:
            continue
        payload = client.get_json(f"/football/matches/{match['id']}/odds").get("data") or {}
        bookmakers = payload.get("bookmakers") or []
        if not bookmakers:
            continue
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        saved = 0
        for bookmaker in bookmakers:
            markets = bookmaker.get("markets") or {}
            result = markets.get("match_odds") or markets.get("1x2") or {}
            if not result:
                continue

            def price(side: str, timepoint: str) -> float | None:
                raw = (result.get(side) or {}).get(timepoint)
                return float(raw) if raw not in (None, "") else None

            values = (
                local["match_id"], PROVIDER, match["id"], target["id"], bookmaker.get("bookmaker") or "unknown",
                price("home", "opening"), price("draw", "opening"), price("away", "opening"),
                price("home", "last_seen"), price("draw", "last_seen"), price("away", "last_seen"), fetched,
            )
            if not any(value is not None for value in values[5:11]):
                continue
            conn.execute(
                """INSERT INTO external_match_odds
                   (match_id, provider, provider_match_id, provider_season_id, bookmaker,
                    home_open, draw_open, away_open, home_last_seen, draw_last_seen, away_last_seen, fetched_at_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(match_id, provider, bookmaker) DO UPDATE SET
                     provider_match_id=excluded.provider_match_id,
                     provider_season_id=excluded.provider_season_id,
                     home_open=excluded.home_open, draw_open=excluded.draw_open, away_open=excluded.away_open,
                     home_last_seen=excluded.home_last_seen, draw_last_seen=excluded.draw_last_seen,
                     away_last_seen=excluded.away_last_seen, fetched_at_utc=excluded.fetched_at_utc""",
                values,
            )
            saved += 1
            counts["bookmakers"][values[4]] = counts["bookmakers"].get(values[4], 0) + 1
        if saved:
            conn.commit()
            counts["requests_with_odds"] += 1
            counts["bookmaker_rows"] += saved
        if index % 10 == 0 or index == len(matches_to_fetch):
            print(f"Odds checked {index}/{len(matches_to_fetch)} matches; rows={counts['bookmaker_rows']}.", flush=True)

    conn.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2025_26")
    parser.add_argument("--date-from", default="2025-10-18")
    parser.add_argument("--competition-id", default="comp_3039")
    parser.add_argument("--minimum-interval", type=float, default=5.2)
    args = parser.parse_args()
    print(import_odds(args))


if __name__ == "__main__":
    main()
