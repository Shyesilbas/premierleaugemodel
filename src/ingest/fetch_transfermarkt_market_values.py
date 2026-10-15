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
            team_id INTEGER PRIMARY KEY,
            tm_club_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            season TEXT NOT NULL,
            market_value INTEGER NOT NULL,
            market_value_eur REAL NOT NULL,
            squad_size INTEGER,
            avg_market_value_eur REAL,
            updated_at TEXT NOT NULL
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
            updated_at TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES team_market_values(team_id)
        )
    """)
    conn.commit()


def run_pipeline() -> None:
    logger.info("Starting Transfermarkt market values ingestion for 2026_27 season...")
    conn = sqlite3.connect(DB_PATH)
    init_market_value_tables(conn)

    teams_data: List[Dict[str, Any]] = []
    players_data: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc).isoformat()

    total_clubs = len(TM_CLUB_MAPPING)
    idx = 0

    for tm_club_id, meta in TM_CLUB_MAPPING.items():
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
            ON CONFLICT(team_id) DO UPDATE SET
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
