"""Import TheStatsAPI match-level xG without overwriting legacy match fields.

The API key must be supplied through THESTATSAPI_API_KEY. By default this
imports one season through a selected gameweek and stores a provider audit row
for every uniquely matched fixture in ``external_match_xg``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `python3 src/...py` import src.config
from src.config import DB_PATH, ROOT as BASE_DIR, DEFAULT_SEASON  # noqa: E402

API_BASE = "https://api.thestatsapi.com/api"
PROVIDER = "TheStatsAPI"


def normalize_team(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-z0-9]+", "", value.casefold())
    aliases = {
        "wolverhampton": "wolverhamptonwanderers",
        "wolves": "wolverhamptonwanderers",
        "manutd": "manchesterunited",
        "manchesterutd": "manchesterunited",
        "mancity": "manchestercity",
        "westham": "westhamunited",
    }
    return aliases.get(normalized, normalized)


class TheStatsApiClient:
    def __init__(self, api_key: str, minimum_interval: float) -> None:
        self.api_key = api_key
        self.minimum_interval = minimum_interval
        self.last_request_at = 0.0

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        while True:
            elapsed = time.monotonic() - self.last_request_at
            if elapsed < self.minimum_interval:
                time.sleep(self.minimum_interval - elapsed)
            request = Request(url, headers={"Authorization": f"Bearer {self.api_key}"})
            try:
                with urlopen(request, timeout=30) as response:
                    body = response.read()
                self.last_request_at = time.monotonic()
                return json.loads(body)
            except HTTPError as exc:
                self.last_request_at = time.monotonic()
                if exc.code == 429:
                    delay = int(exc.headers.get("Retry-After", "30")) + 1
                    print(f"Rate limit hit; waiting {delay}s before retry.", flush=True)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"TheStatsAPI returned HTTP {exc.code} for {path}") from exc
            except URLError as exc:
                self.last_request_at = time.monotonic()
                raise RuntimeError(f"TheStatsAPI request failed for {path}: {exc.reason}") from exc


def create_source_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS external_match_xg (
            match_id INTEGER PRIMARY KEY REFERENCES matches(match_id),
            provider TEXT NOT NULL,
            provider_match_id TEXT NOT NULL UNIQUE,
            provider_season_id TEXT NOT NULL,
            home_xg REAL NOT NULL,
            away_xg REAL NOT NULL,
            xg_quality TEXT,
            fetched_at_utc TEXT NOT NULL
        )
    """)
    conn.commit()


def fetch_all_matches(client: TheStatsApiClient, competition_id: str, season_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        response = client.get_json(
            "/football/matches",
            {"competition_id": competition_id, "season_id": season_id, "page": page, "per_page": 100},
        )
        rows.extend(response.get("data") or [])
        total_pages = int((response.get("meta") or {}).get("total_pages", 1))
        if page >= total_pages:
            return rows
        page += 1


def find_local_match(
    conn: sqlite3.Connection,
    season: str,
    gameweek: int,
    home_name: str,
    away_name: str,
) -> sqlite3.Row | None:
    rows = conn.execute(
        "SELECT match_id, home_name, away_name FROM matches WHERE season = ? AND gameweek = ?",
        (season, gameweek),
    ).fetchall()
    matches = [
        row for row in rows
        if normalize_team(row["home_name"]) == normalize_team(home_name)
        and normalize_team(row["away_name"]) == normalize_team(away_name)
    ]
    if not matches:
        # Re-arranged fixtures can retain their original provider matchday while
        # the local source assigns the gameweek in which they were played.
        rows = conn.execute(
            "SELECT match_id, home_name, away_name FROM matches WHERE season = ?",
            (season,),
        ).fetchall()
        matches = [
            row for row in rows
            if normalize_team(row["home_name"]) == normalize_team(home_name)
            and normalize_team(row["away_name"]) == normalize_team(away_name)
        ]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous local match mapping: {season} GW{gameweek} {home_name} v {away_name}")
    return matches[0] if matches else None


def extract_xg(payload: dict[str, Any]) -> tuple[float, float]:
    data = payload.get("data") or {}
    expected = ((data.get("overview") or {}).get("expected_goals") or {}).get("all") or {}
    home_xg, away_xg = expected.get("home"), expected.get("away")
    if home_xg is None or away_xg is None:
        raise ValueError("Stats response did not contain overview.expected_goals.all for both teams")
    return float(home_xg), float(away_xg)


def import_season(args: argparse.Namespace) -> dict[str, int]:
    api_key = os.environ.get("THESTATSAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set THESTATSAPI_API_KEY in the process environment; it is never read from or written to a file.")
    client = TheStatsApiClient(api_key, args.minimum_interval)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_source_table(conn)

    seasons_response = client.get_json(f"/football/competitions/{args.competition_id}/seasons")
    target = next(
        (
            season for season in seasons_response.get("data", [])
            if f"{season.get('start_year')}_{int(season.get('end_year') or 0) % 100:02d}" == args.season
        ),
        None,
    )
    if target is None:
        raise RuntimeError(f"Season {args.season} was not returned by TheStatsAPI")

    matches = fetch_all_matches(client, args.competition_id, target["id"])
    candidates = [
        match for match in matches
        if int(match.get("matchday") or 0) <= args.max_gameweek
        and match.get("status") == "finished"
        and match.get("xg_available")
    ]
    counts = {
        "listed": len(matches), "eligible": len(candidates), "imported": 0,
        "skipped_existing": 0, "duplicate_conflicts": 0, "unmatched": 0, "stats_missing_xg": 0,
    }

    for index, match in enumerate(candidates, start=1):
        if args.limit is not None and counts["imported"] >= args.limit:
            break
        local = find_local_match(
            conn,
            args.season,
            int(match["matchday"]),
            (match.get("home_team") or {}).get("name", ""),
            (match.get("away_team") or {}).get("name", ""),
        )
        if local is None:
            counts["unmatched"] += 1
            print(
                f"Unmatched fixture {index}/{len(candidates)}: GW{match.get('matchday')} "
                f"{(match.get('home_team') or {}).get('name')} v {(match.get('away_team') or {}).get('name')}",
                flush=True,
            )
            continue
        existing = conn.execute(
            "SELECT provider, provider_match_id FROM external_match_xg WHERE match_id = ?",
            (local["match_id"],),
        ).fetchone()
        if existing:
            counts["skipped_existing"] += 1
            continue
        provider_id_exists = conn.execute(
            "SELECT match_id FROM external_match_xg WHERE provider_match_id = ?",
            (match["id"],),
        ).fetchone()
        if provider_id_exists:
            counts["duplicate_conflicts"] += 1
            print(f"Skipped duplicate provider fixture id {match['id']} already mapped to local match {provider_id_exists['match_id']}.", flush=True)
            continue

        stats = client.get_json(f"/football/matches/{match['id']}/stats")
        try:
            home_xg, away_xg = extract_xg(stats)
        except ValueError as exc:
            counts["stats_missing_xg"] += 1
            print(f"No xG values for {match['id']} ({args.season} GW{match.get('matchday')}): {exc}", flush=True)
            continue
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.execute(
            """INSERT OR IGNORE INTO external_match_xg
               (match_id, provider, provider_match_id, provider_season_id, home_xg, away_xg, xg_quality, fetched_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                local["match_id"], PROVIDER, match["id"], target["id"], home_xg, away_xg,
                match.get("xg_quality"), fetched,
            ),
        )
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            counts["duplicate_conflicts"] += 1
            continue
        counts["imported"] += 1
        if index % 10 == 0 or index == len(candidates):
            print(f"Imported {index}/{len(candidates)} for {args.season}.", flush=True)

    conn.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default=DEFAULT_SEASON, help="Season label such as 2026_27")
    parser.add_argument("--max-gameweek", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new xG records to import")
    parser.add_argument("--competition-id", default="comp_3039")
    parser.add_argument("--minimum-interval", type=float, default=5.2)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    counts = import_season(args)
    print(json.dumps(counts, sort_keys=True))
    if counts["stats_missing_xg"] or counts["unmatched"]:
        # Provider flagged xG as available but did not deliver it, or a fixture has no local match.
        print(
            f"WARNING: {counts['stats_missing_xg']} matches without xG values, "
            f"{counts['unmatched']} unmatched fixtures.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
