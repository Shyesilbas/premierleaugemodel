#!/usr/bin/env python3
"""
Fetch authentic Transfermarkt squad & player market values for 2026_27 Premier League teams.
Uses rate-limit controlled requests to avoid throttling.
Stores data in SQLite (team_market_values, player_market_values) and data/processed/market_values_2026_27.json.
"""

import json
import logging
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fetch_tm_market_values")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "premier_league.db"
JSON_OUT_PATH = DATA_DIR / "processed" / "market_values_2026_27.json"

TM_API_BASE = "https://transfermarkt-api.fly.dev"
REQUEST_INTERVAL = 1.3  # Sleep 1.3 seconds between calls to respect rate limits

# Explicit mapping between Transfermarkt club IDs and Premier League Pulse IDs
TM_CLUB_MAPPING = {
    281: {"pulse_id": 11, "name": "Manchester City", "abbr": "MCI"},
    11: {"pulse_id": 1, "name": "Arsenal", "abbr": "ARS"},
    631: {"pulse_id": 4, "name": "Chelsea", "abbr": "CHE"},
    31: {"pulse_id": 10, "name": "Liverpool", "abbr": "LIV"},
    985: {"pulse_id": 12, "name": "Manchester United", "abbr": "MUN"},
    148: {"pulse_id": 21, "name": "Tottenham Hotspur", "abbr": "TOT"},
    762: {"pulse_id": 23, "name": "Newcastle United", "abbr": "NEW"},
    1237: {"pulse_id": 131, "name": "Brighton & Hove Albion", "abbr": "BHA"},
    1148: {"pulse_id": 130, "name": "Brentford", "abbr": "BRE"},
    405: {"pulse_id": 2, "name": "Aston Villa", "abbr": "AVL"},
    989: {"pulse_id": 127, "name": "Bournemouth", "abbr": "BOU"},
    873: {"pulse_id": 6, "name": "Crystal Palace", "abbr": "CRY"},
    703: {"pulse_id": 15, "name": "Nottingham Forest", "abbr": "NFO"},
    289: {"pulse_id": 29, "name": "Sunderland", "abbr": "SUN"},
    399: {"pulse_id": 9, "name": "Leeds United", "abbr": "LEE"},
    29: {"pulse_id": 7, "name": "Everton", "abbr": "EVE"},
    931: {"pulse_id": 34, "name": "Fulham", "abbr": "FUL"},
    677: {"pulse_id": 8, "name": "Ipswich Town", "abbr": "IPS"},
    990: {"pulse_id": 5, "name": "Coventry City", "abbr": "COV"},
    3008: {"pulse_id": 41, "name": "Hull City", "abbr": "HUL"},
    1031: {"pulse_id": 163, "name": "Luton Town", "abbr": "LUT"},
    350: {"pulse_id": 18, "name": "Sheffield United", "abbr": "SHU"},
    180: {"pulse_id": 20, "name": "Southampton", "abbr": "SOU"},
    1003: {"pulse_id": 26, "name": "Leicester City", "abbr": "LEI"},
    1132: {"pulse_id": 43, "name": "Burnley", "abbr": "BUR"},
    543: {"pulse_id": 38, "name": "Wolverhampton Wanderers", "abbr": "WOL"},
    379: {"pulse_id": 25, "name": "West Ham United", "abbr": "WHU"},
}


def api_request(endpoint: str, max_retries: int = 4) -> Optional[Dict[str, Any]]:
    """Fetch JSON from Transfermarkt API with rate limit safety and backoff."""
    url = f"{TM_API_BASE}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PremierLeagueModelApp/1.0)"})

    for attempt in range(max_retries):
        try:
            time.sleep(REQUEST_INTERVAL)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = (attempt + 1) * 8
                logger.warning(f"Rate limited on {endpoint}. Sleeping {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            elif e.code == 404:
                logger.error(f"Endpoint {endpoint} returned 404 Not Found.")
                return None
            else:
                logger.warning(f"HTTPError {e.code} on {endpoint}: {e.reason}. Retrying...")
                time.sleep(3)
        except Exception as e:
            logger.warning(f"Request error on {endpoint}: {e}. Retrying...")
            time.sleep(3)

    logger.error(f"Failed to fetch {endpoint} after {max_retries} retries.")
    return None


def init_market_value_tables(conn: sqlite3.Connection) -> None:
    """Create team and player market value tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_market_values (
            team_id INTEGER NOT NULL,
            tm_club_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            season TEXT NOT NULL,
            market_value INTEGER NOT NULL,
            market_value_eur REAL NOT NULL,
            squad_size INTEGER,
            avg_market_value_eur REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (team_id, season)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_market_values (
            player_id TEXT PRIMARY KEY,
            team_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position TEXT,
            market_value INTEGER NOT NULL,
            market_value_eur REAL NOT NULL,
            age INTEGER,
            nationality TEXT,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()


def fetch_historical_seasons_market_values(conn: sqlite3.Connection) -> int:
    """Fetches authentic historical Transfermarkt squad market values for 2022-2026."""
    import subprocess
    import re
    
    seasons = [
        (2022, "2022_23"),
        (2023, "2023_24"),
        (2024, "2024_25"),
        (2025, "2025_26")
    ]
    now_utc = datetime.now(timezone.utc).isoformat()
    total_inserted = 0

    for s_year, s_str in seasons:
        logger.info(f"Fetching historical market values for season {s_str} ({s_year})...")
        try:
            cmd = [
                "curl", "-s", "-L",
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                f"https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1/plus/?saison_id={s_year}"
            ]
            html = subprocess.check_output(cmd).decode("utf-8")
            pattern = (
                r'/kader/verein/(\d+)/saison_id/' + str(s_year) +
                r'\"[^>]*>(\d+)</a>.*?<td class=\"rechts\">€([0-9\.,]+)(bn|m|k|Th\.)</td><td class=\"rechts\"><a title=\"([^\"]+)\"[^>]*>€([0-9\.,]+)(bn|m|k|Th\.)</a>'
            )
            matches = re.findall(pattern, html, re.DOTALL)
            logger.info(f"   -> Parsed {len(matches)} clubs for {s_str}")

            for tm_id_str, sq_size, avg_val, avg_unit, club_title, tot_val, tot_unit in matches:
                tm_id = int(tm_id_str)
                meta = TM_CLUB_MAPPING.get(tm_id)
                if not meta:
                    logger.warning(f"Unmapped club {tm_id}: {club_title}")
                    continue

                tot_flt = float(tot_val.replace(",", "."))
                if tot_unit == "bn":
                    mv_eur_m = tot_flt * 1000.0
                elif tot_unit in ("k", "Th."):
                    mv_eur_m = tot_flt / 1000.0
                else:
                    mv_eur_m = tot_flt

                avg_flt = float(avg_val.replace(",", "."))
                if avg_unit == "bn":
                    avg_eur_m = avg_flt * 1000.0
                elif avg_unit in ("k", "Th."):
                    avg_eur_m = avg_flt / 1000.0
                else:
                    avg_eur_m = avg_flt

                entry = {
                    "team_id": meta["pulse_id"],
                    "tm_club_id": tm_id,
                    "name": meta["name"],
                    "season": s_str,
                    "market_value": int(mv_eur_m * 1_000_000),
                    "market_value_eur": round(mv_eur_m, 2),
                    "squad_size": int(sq_size),
                    "avg_market_value_eur": round(avg_eur_m, 2),
                    "updated_at": now_utc,
                }
                conn.execute("""
                    INSERT INTO team_market_values (
                        team_id, tm_club_id, name, season, market_value,
                        market_value_eur, squad_size, avg_market_value_eur, updated_at
                    ) VALUES (
                        :team_id, :tm_club_id, :name, :season, :market_value,
                        :market_value_eur, :squad_size, :avg_market_value_eur, :updated_at
                    ) ON CONFLICT(team_id, season) DO UPDATE SET
                        market_value = excluded.market_value,
                        market_value_eur = excluded.market_value_eur,
                        squad_size = excluded.squad_size,
                        avg_market_value_eur = excluded.avg_market_value_eur,
                        updated_at = excluded.updated_at
                """, entry)
                total_inserted += 1
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to fetch historical market values for {s_str}: {e}")

    return total_inserted


def run_pipeline() -> None:
    logger.info("Starting Transfermarkt market values ingestion for 2026_27 season...")
    conn = sqlite3.connect(DB_PATH)
    init_market_value_tables(conn)

    # 1. Fetch Historical Seasons (2022-2026)
    hist_inserted = fetch_historical_seasons_market_values(conn)
    logger.info(f"Historical market values ingestion done: {hist_inserted} records saved.")

    teams_data: List[Dict[str, Any]] = []
    players_data: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc).isoformat()

    current_2026_27_ids = [
        281, 11, 631, 31, 985, 148, 762, 1237, 1148, 405,
        989, 873, 703, 289, 399, 29, 931, 677, 990, 3008
    ]
    total_clubs = len(current_2026_27_ids)
    idx = 0

    for tm_club_id in current_2026_27_ids:
        meta = TM_CLUB_MAPPING[tm_club_id]
        idx += 1
        pulse_id = meta["pulse_id"]
        club_name = meta["name"]
        logger.info(f"[{idx}/{total_clubs}] Fetching {club_name} (TM ID: {tm_club_id}, Pulse ID: {pulse_id})...")

        # 1. Fetch Club Profile
        profile_res = api_request(f"/clubs/{tm_club_id}/profile")
        raw_mv = 0
        squad_size = 0
        if profile_res:
            raw_mv = profile_res.get("currentMarketValue") or 0
            squad_meta = profile_res.get("squad") or {}
            squad_size = squad_meta.get("size") or 0

        # In Millions EUR
        mv_eur_m = round(raw_mv / 1_000_000.0, 2)
        avg_mv_eur_m = round(mv_eur_m / max(squad_size, 1), 2) if squad_size > 0 else 0.0

        team_entry = {
            "team_id": pulse_id,
            "tm_club_id": tm_club_id,
            "name": club_name,
            "season": "2026_27",
            "market_value": raw_mv,
            "market_value_eur": mv_eur_m,
            "squad_size": squad_size,
            "avg_market_value_eur": avg_mv_eur_m,
            "updated_at": now_utc,
        }
        teams_data.append(team_entry)

        # Upsert into team_market_values
        conn.execute("""
            INSERT INTO team_market_values (team_id, tm_club_id, name, season, market_value, market_value_eur, squad_size, avg_market_value_eur, updated_at)
            VALUES (:team_id, :tm_club_id, :name, :season, :market_value, :market_value_eur, :squad_size, :avg_market_value_eur, :updated_at)
            ON CONFLICT(team_id, season) DO UPDATE SET
                market_value = excluded.market_value,
                market_value_eur = excluded.market_value_eur,
                squad_size = excluded.squad_size,
                avg_market_value_eur = excluded.avg_market_value_eur,
                updated_at = excluded.updated_at
        """, team_entry)

        # 2. Fetch Squad Players
        players_res = api_request(f"/clubs/{tm_club_id}/players")
        if players_res and "players" in players_res:
            raw_players = players_res.get("players", [])
            logger.info(f"   -> Retrieved {len(raw_players)} players for {club_name}")

            for p in raw_players:
                p_id = str(p.get("id"))
                p_name = p.get("name", "")
                p_pos = p.get("position", "")
                p_age = p.get("age")
                p_nat = ", ".join(p.get("nationality", [])) if isinstance(p.get("nationality"), list) else str(p.get("nationality") or "")
                p_raw_mv = p.get("marketValue") or 0
                p_mv_eur_m = round(p_raw_mv / 1_000_000.0, 2)

                p_entry = {
                    "player_id": p_id,
                    "team_id": pulse_id,
                    "name": p_name,
                    "position": p_pos,
                    "market_value": p_raw_mv,
                    "market_value_eur": p_mv_eur_m,
                    "age": p_age,
                    "nationality": p_nat,
                    "updated_at": now_utc,
                }
                players_data.append(p_entry)

                conn.execute("""
                    INSERT INTO player_market_values (player_id, team_id, name, position, market_value, market_value_eur, age, nationality, updated_at)
                    VALUES (:player_id, :team_id, :name, :position, :market_value, :market_value_eur, :age, :nationality, :updated_at)
                    ON CONFLICT(player_id) DO UPDATE SET
                        team_id = excluded.team_id,
                        name = excluded.name,
                        position = excluded.position,
                        market_value = excluded.market_value,
                        market_value_eur = excluded.market_value_eur,
                        age = excluded.age,
                        nationality = excluded.nationality,
                        updated_at = excluded.updated_at
                """, p_entry)

        conn.commit()

    # Save complete snapshot JSON
    JSON_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"updated_at": now_utc, "teams": teams_data, "players_count": len(players_data), "players": players_data}, f, indent=2, ensure_ascii=False)

    logger.info(f"Done! Successfully saved {len(teams_data)} teams and {len(players_data)} players market values.")
    conn.close()


if __name__ == "__main__":
    run_pipeline()
