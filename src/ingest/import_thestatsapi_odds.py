"""Import historical opening and closing odds for Premier League matches from TheStatsAPI.

Captures 1X2, Over/Under 2.5 goals, BTTS, Corners, Cards, and full market payload.
Enforces API rate limit (default: 5.2s interval = ~11.5 req/min).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from src.config import DB_PATH, DEFAULT_SEASON
from src.db.database import ensure_external_odds_table as init_odds_table, get_db
from src.ingest.import_thestatsapi_xg import (
    PROVIDER,
    TheStatsApiClient,
    normalize_team,
)


def parse_price(val: Any) -> float | None:
    try:
        return float(val) if val not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None


def store_bookmaker_odds(
    conn: Any,
    match_id: int,
    provider_match_id: str,
    season_id: str,
    bookmakers: list[dict[str, Any]],
    fetched_at: str,
) -> list[str]:
    """Upsert one row per bookmaker into external_match_odds; returns the bookmaker names saved."""
    bm_names: list[str] = []

    for bm in bookmakers:
        bm_name = bm.get("bookmaker") or "unknown"
        markets = bm.get("markets") or {}
        mo = markets.get("match_odds") or markets.get("1x2") or {}
        tg = markets.get("total_goals", {}).get("2.5", {}) or markets.get("over_under_2_5", {})
        btts = markets.get("btts") or markets.get("both_teams_to_score") or {}
        corn = markets.get("match_corners", {}).get("9.5", {})
        card = markets.get("total_cards", {}).get("4.5", {}) or markets.get("total_cards", {}).get("3.5", {})

        # 1X2
        h_open = parse_price(mo.get("home", {}).get("opening"))
        d_open = parse_price(mo.get("draw", {}).get("opening"))
        a_open = parse_price(mo.get("away", {}).get("opening"))
        h_last = parse_price(mo.get("home", {}).get("last_seen"))
        d_last = parse_price(mo.get("draw", {}).get("last_seen"))
        a_last = parse_price(mo.get("away", {}).get("last_seen"))

        # Over/Under 2.5
        o25_open = parse_price(tg.get("over", {}).get("opening"))
        u25_open = parse_price(tg.get("under", {}).get("opening"))
        o25_last = parse_price(tg.get("over", {}).get("last_seen"))
        u25_last = parse_price(tg.get("under", {}).get("last_seen"))

        # BTTS
        btts_y_open = parse_price(btts.get("yes", {}).get("opening"))
        btts_n_open = parse_price(btts.get("no", {}).get("opening"))
        btts_y_last = parse_price(btts.get("yes", {}).get("last_seen"))
        btts_n_last = parse_price(btts.get("no", {}).get("last_seen"))

        # Corners 9.5
        corn_o_open = parse_price(corn.get("over", {}).get("opening"))
        corn_u_open = parse_price(corn.get("under", {}).get("opening"))
        corn_o_last = parse_price(corn.get("over", {}).get("last_seen"))
        corn_u_last = parse_price(corn.get("under", {}).get("last_seen"))

        # Cards 4.5
        card_o_open = parse_price(card.get("over", {}).get("opening"))
        card_u_open = parse_price(card.get("under", {}).get("opening"))
        card_o_last = parse_price(card.get("over", {}).get("last_seen"))
        card_u_last = parse_price(card.get("under", {}).get("last_seen"))

        # Filter out bookmakers with zero relevant data
        all_prices = [
            h_open, d_open, a_open, h_last, d_last, a_last,
            o25_open, u25_open, o25_last, u25_last,
            btts_y_open, btts_n_open, btts_y_last, btts_n_last,
        ]
        if not any(p is not None for p in all_prices):
            continue

        raw_json = json.dumps(markets, ensure_ascii=False)

        conn.execute(
            """INSERT INTO external_match_odds
               (match_id, provider, provider_match_id, provider_season_id, bookmaker,
                home_open, draw_open, away_open, home_last_seen, draw_last_seen, away_last_seen,
                over_25_open, under_25_open, over_25_last_seen, under_25_last_seen,
                btts_yes_open, btts_no_open, btts_yes_last_seen, btts_no_last_seen,
                corners_over_open, corners_under_open, corners_over_last_seen, corners_under_last_seen,
                cards_over_open, cards_under_open, cards_over_last_seen, cards_under_last_seen,
                raw_markets_json, fetched_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(match_id, provider, bookmaker) DO UPDATE SET
                 provider_match_id=excluded.provider_match_id,
                 provider_season_id=excluded.provider_season_id,
                 home_open=excluded.home_open, draw_open=excluded.draw_open, away_open=excluded.away_open,
                 home_last_seen=excluded.home_last_seen, draw_last_seen=excluded.draw_last_seen,
                 away_last_seen=excluded.away_last_seen,
                 over_25_open=excluded.over_25_open, under_25_open=excluded.under_25_open,
                 over_25_last_seen=excluded.over_25_last_seen, under_25_last_seen=excluded.under_25_last_seen,
                 btts_yes_open=excluded.btts_yes_open, btts_no_open=excluded.btts_no_open,
                 btts_yes_last_seen=excluded.btts_yes_last_seen, btts_no_last_seen=excluded.btts_no_last_seen,
                 corners_over_open=excluded.corners_over_open, corners_under_open=excluded.corners_under_open,
                 corners_over_last_seen=excluded.corners_over_last_seen, corners_under_last_seen=excluded.corners_under_last_seen,
                 cards_over_open=excluded.cards_over_open, cards_under_open=excluded.cards_under_open,
                 cards_over_last_seen=excluded.cards_over_last_seen, cards_under_last_seen=excluded.cards_under_last_seen,
                 raw_markets_json=excluded.raw_markets_json, fetched_at_utc=excluded.fetched_at_utc""",
            (
                match_id, PROVIDER, provider_match_id, season_id, bm_name,
                h_open, d_open, a_open, h_last, d_last, a_last,
                o25_open, u25_open, o25_last, u25_last,
                btts_y_open, btts_n_open, btts_y_last, btts_n_last,
                corn_o_open, corn_u_open, corn_o_last, corn_u_last,
                card_o_open, card_u_open, card_o_last, card_u_last,
                raw_json, fetched_at,
            ),
        )
        bm_names.append(bm_name)

    return bm_names


def import_odds(
    api_key: str,
    season: str = DEFAULT_SEASON,
    competition_id: str = "comp_3039",
    only_played: bool = True,
    minimum_interval: float = 5.2,
    refresh: bool = False,
) -> dict[str, Any]:
    if not api_key:
        raise ValueError("API key must be provided.")

    client = TheStatsApiClient(api_key.strip(), minimum_interval=minimum_interval)
    conn = get_db(DB_PATH)
    init_odds_table(conn)

    # 1. Fetch seasons for this competition
    print(f"Fetching seasons for competition {competition_id}...")
    season_response = client.get_json(f"/football/competitions/{competition_id}/seasons")
    seasons_list = season_response.get("data", [])

    target_season = None
    for s in seasons_list:
        start_year = s.get("start_year")
        end_year = s.get("end_year")
        code = f"{start_year}_{int(end_year or 0) % 100:02d}"
        if code == season or str(s.get("year", "")).replace("/", "_") == season:
            target_season = s
            break

    if target_season is None:
        raise RuntimeError(f"Season '{season}' not found in TheStatsAPI competition {competition_id}")

    season_id = target_season["id"]
    print(f"Matched season: {target_season.get('name')} (ID: {season_id})")

    # 2. Fetch matches from API for this season
    print("Fetching matches from TheStatsAPI...")
    api_matches: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = client.get_json(
            "/football/matches",
            {"competition_id": competition_id, "season_id": season_id, "page": page, "per_page": 100},
        )
        api_matches.extend(resp.get("data") or [])
        total_pages = int((resp.get("meta") or {}).get("total_pages", 1))
        if page >= total_pages:
            break
        page += 1

    print(f"Total API matches returned: {len(api_matches)}")

    # 3. Read local matches from DB
    query = "SELECT * FROM matches WHERE season = ?"
    if only_played:
        query += " AND home_score IS NOT NULL"
    query += " ORDER BY gameweek ASC, match_date ASC"

    local_rows = conn.execute(query, (season,)).fetchall()
    local_by_teams = {
        (normalize_team(row["home_name"]), normalize_team(row["away_name"])): row
        for row in local_rows
    }
    print(f"Local matches in target scope ({season}, only_played={only_played}): {len(local_rows)}")

    matches_to_fetch = []
    for m in api_matches:
        if only_played and m.get("status") != "finished" and m.get("score", {}).get("home") is None:
            continue
        h = normalize_team(m.get("home_team", {}).get("name", ""))
        a = normalize_team(m.get("away_team", {}).get("name", ""))
        local = local_by_teams.get((h, a))
        if local is not None:
            matches_to_fetch.append((m, local))

    # Played matches have final odds; re-fetching them costs one 5.2 s request each and would hold the
    # shared cron lock for half an hour late in the season. --refresh forces a re-fetch.
    skipped_existing = 0
    if not refresh:
        already = {row[0] for row in conn.execute("SELECT DISTINCT match_id FROM external_match_odds")}
        kept = [(m, local) for m, local in matches_to_fetch if local["match_id"] not in already]
        skipped_existing, matches_to_fetch = len(matches_to_fetch) - len(kept), kept
    print(f"Matches to process: {len(matches_to_fetch)} ({skipped_existing} already stored)")

    stats = {
        "total_targets": len(matches_to_fetch),
        "skipped_existing": skipped_existing,
        "matches_processed": 0,
        "odds_fetched_count": 0,
        "bookmaker_rows_saved": 0,
        "bookmakers": {},
    }

    start_time = time.time()
    for index, (api_match, local_match) in enumerate(matches_to_fetch, start=1):
        mid = local_match["match_id"]
        h_name = local_match["home_name"]
        a_name = local_match["away_name"]
        gw = local_match["gameweek"]
        score_str = f"{int(local_match['home_score'])} - {int(local_match['away_score'])}" if local_match["home_score"] is not None else "vs"

        if api_match.get("odds_available") is False:
            print(f"[{index}/{len(matches_to_fetch)}] (GW{gw}) {h_name} {score_str} {a_name} -> No odds available.")
            continue

        try:
            payload = client.get_json(f"/football/matches/{api_match['id']}/odds").get("data") or {}
        except Exception as exc:
            print(f"[{index}/{len(matches_to_fetch)}] Failed to fetch odds for {api_match['id']}: {exc}")
            continue

        bookmakers = payload.get("bookmakers") or []
        if not bookmakers:
            print(f"[{index}/{len(matches_to_fetch)}] (GW{gw}) {h_name} {score_str} {a_name} -> Empty bookmakers.")
            continue

        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        saved_names = store_bookmaker_odds(conn, mid, api_match["id"], season_id, bookmakers, fetched_at)
        saved_for_match = len(saved_names)
        bm_names = saved_names
        for bm_name in saved_names:
            stats["bookmakers"][bm_name] = stats["bookmakers"].get(bm_name, 0) + 1

        if saved_for_match > 0:
            conn.commit()
            stats["odds_fetched_count"] += 1
            stats["bookmaker_rows_saved"] += saved_for_match

        stats["matches_processed"] += 1
        elapsed = time.time() - start_time
        print(f"[{index}/{len(matches_to_fetch)}] (GW{gw}) {h_name} {score_str} {a_name} -> Saved {saved_for_match} bookmakers ({', '.join(bm_names[:3])}) | Total rows: {stats['bookmaker_rows_saved']} | Elapsed: {elapsed:.1f}s", flush=True)

    conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=os.environ.get("THESTATSAPI_API_KEY", ""))
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--competition-id", default="comp_3039")
    parser.add_argument("--only-played", action="store_true", default=True)
    parser.add_argument("--minimum-interval", type=float, default=5.2)
    parser.add_argument("--refresh", action="store_true", help="re-fetch odds for matches already stored")
    args = parser.parse_args()

    results = import_odds(
        api_key=args.api_key,
        season=args.season,
        competition_id=args.competition_id,
        only_played=args.only_played,
        minimum_interval=args.minimum_interval,
        refresh=args.refresh,
    )
    print("\n--- INGESTION COMPLETE ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
