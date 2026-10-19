"""
SQLite Built-in Database Layer for Premier League Model App.
Stores matches, referees, teams, and prediction caches with high-performance indexing.
Eliminates heavy Parquet/JSON file reads on runtime requests.
"""

import os
import sqlite3
import json
from typing import List, Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger("db_layer")

from src.config import DATA_DIR, DB_PATH, DEFAULT_SEASON, RAW_DIR, SEASONS


def get_db():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def attach_statsapi_xg(matches: pd.DataFrame) -> pd.DataFrame:
    """Attach explicitly sourced TheStatsAPI xG to a match frame by local match_id."""
    out = matches.copy()
    if "match_id" not in out.columns:
        return out
    try:
        conn = get_db()
        try:
            xg = pd.read_sql_query(
                "SELECT match_id, provider, home_xg, away_xg, xg_quality FROM external_match_xg",
                conn,
            )
        finally:
            conn.close()
    except Exception as exc:
        logger.info("Provider xG table unavailable; attaching null provider xG: %s", exc)
        xg = pd.DataFrame(columns=["match_id", "provider", "home_xg", "away_xg", "xg_quality"])
    xg = xg.rename(columns={
        "provider": "xg_provider", "home_xg": "statsapi_home_xg",
        "away_xg": "statsapi_away_xg", "xg_quality": "statsapi_xg_quality",
    })
    out = out.drop(columns=[c for c in xg.columns if c != "match_id" and c in out.columns])
    return out.merge(xg, on="match_id", how="left", validate="many_to_one")


def init_db():
    """Initializes SQLite schema and indexes."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # Matches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY,
        season TEXT NOT NULL,
        gameweek INTEGER NOT NULL,
        match_date TEXT,
        kickoff_label TEXT,
        day_label TEXT,
        time_label TEXT,
        ground_name TEXT,
        home_id INTEGER NOT NULL,
        home_name TEXT NOT NULL,
        home_abbr TEXT,
        home_score REAL,
        away_id INTEGER NOT NULL,
        away_name TEXT NOT NULL,
        away_abbr TEXT,
        away_score REAL,
        status TEXT NOT NULL,
        total_corners REAL,
        home_won_corners REAL,
        away_won_corners REAL,
        total_throws REAL,
        home_total_throws REAL,
        away_total_throws REAL,
        total_shots REAL,
        total_shots_ontarget REAL,
        total_saves REAL,
        referee_id INTEGER,
        referee_name TEXT,
        total_yellow_cards REAL,
        total_red_cards REAL,
        total_cards REAL,
        total_fouls REAL,
        home_total_yel_card REAL,
        away_total_yel_card REAL,
        home_total_red_card REAL,
        away_total_red_card REAL,
        home_xg REAL,
        away_xg REAL,
        total_xg REAL
    );
    """)

    # Provider-sourced xG is kept separate from the legacy aggregate proxy
    # stored on matches so its source and quality remain explicit.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_match_xg (
        match_id INTEGER PRIMARY KEY REFERENCES matches(match_id),
        provider TEXT NOT NULL,
        provider_match_id TEXT NOT NULL UNIQUE,
        provider_season_id TEXT NOT NULL,
        home_xg REAL NOT NULL,
        away_xg REAL NOT NULL,
        xg_quality TEXT,
        fetched_at_utc TEXT NOT NULL
    );
    """)

    cursor.execute("""
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
        over_25_open REAL,
        under_25_open REAL,
        over_25_last_seen REAL,
        under_25_last_seen REAL,
        btts_yes_open REAL,
        btts_no_open REAL,
        btts_yes_last_seen REAL,
        btts_no_last_seen REAL,
        corners_over_open REAL,
        corners_under_open REAL,
        corners_over_last_seen REAL,
        corners_under_last_seen REAL,
        cards_over_open REAL,
        cards_under_open REAL,
        cards_over_last_seen REAL,
        cards_under_last_seen REAL,
        raw_markets_json TEXT,
        fetched_at_utc TEXT NOT NULL,
        PRIMARY KEY (match_id, provider, bookmaker)
    );
    """)

    # Referees Aggregates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referee_name TEXT NOT NULL,
        season TEXT NOT NULL,
        matches_count INTEGER NOT NULL,
        total_yellow_cards REAL DEFAULT 0,
        avg_yellow_cards REAL DEFAULT 0,
        total_red_cards REAL DEFAULT 0,
        avg_red_cards REAL DEFAULT 0,
        total_cards REAL DEFAULT 0,
        avg_cards REAL DEFAULT 0,
        total_fouls REAL DEFAULT 0,
        avg_fouls REAL DEFAULT 0,
        over_3_5_cards_count INTEGER DEFAULT 0,
        over_3_5_pct REAL DEFAULT 0,
        strictness_label TEXT DEFAULT 'Dengeli',
        UNIQUE(referee_name, season)
    );
    """)

    # Predictions Cache Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions_cache (
        cache_key TEXT PRIMARY KEY,
        home_id INTEGER NOT NULL,
        away_id INTEGER NOT NULL,
        season TEXT NOT NULL,
        prediction_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes for lightning-fast queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_season_gw ON matches (season, gameweek);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_referee ON matches (referee_name, season);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches (home_id, away_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_referees_season ON referees (season);")

    conn.commit()
    conn.close()


def populate_db_from_sources():
    """Populates the SQLite database from Parquet and raw JSON sources."""
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    parquet_path = DATA_DIR / "processed" / "matches_summary_all.parquet"
    if not parquet_path.exists():
        logger.warning(f"{parquet_path} not found. Skipping parquet import.")
        return

    df = pd.read_parquet(parquet_path)
    logger.info(f"Loaded {len(df)} matches from parquet for SQLite import.")

    # Load 2026-27 raw fixtures for upcoming matches
    fix_2627_path = RAW_DIR / f"fixtures_{DEFAULT_SEASON}.json"
    raw_2627 = []
    if fix_2627_path.exists():
        with open(fix_2627_path, "r", encoding="utf-8") as f:
            raw_2627 = json.load(f)

    # Insert / Replace matches from Parquet
    matches_to_insert = []
    for _, r in df.iterrows():
        mid = int(r["match_id"])
        h_score = float(r["home_score"]) if pd.notnull(r.get("home_score")) else None
        a_score = float(r["away_score"]) if pd.notnull(r.get("away_score")) else None
        is_completed = (h_score is not None and a_score is not None)

        kickoff = str(r.get("kickoff_label", ""))
        day_p = kickoff.split(",")[0].strip() if "," in kickoff else kickoff
        time_p = kickoff.split(",")[1].strip() if "," in kickoff else ""

        ref_name = str(r.get("referee_name") or "Unknown").strip()
        if ref_name == "" or ref_name.lower() == "nan":
            ref_name = "Unknown"

        matches_to_insert.append((
            mid,
            str(r.get("season", "2024_25")),
            int(r.get("gameweek", 1)),
            str(r.get("match_date", "")),
            kickoff,
            day_p,
            time_p,
            str(r.get("ground_name", "")),
            int(r["home_id"]),
            str(r["home_name"]),
            str(r.get("home_abbr", "")),
            h_score,
            int(r["away_id"]),
            str(r["away_name"]),
            str(r.get("away_abbr", "")),
            a_score,
            "COMPLETED" if is_completed else "UPCOMING",
            float(r["total_corners"]) if pd.notnull(r.get("total_corners")) else None,
            float(r["home_won_corners"]) if pd.notnull(r.get("home_won_corners")) else None,
            float(r["away_won_corners"]) if pd.notnull(r.get("away_won_corners")) else None,
            float(r["total_throws"]) if pd.notnull(r.get("total_throws")) else None,
            float(r["home_total_throws"]) if pd.notnull(r.get("home_total_throws")) else None,
            float(r["away_total_throws"]) if pd.notnull(r.get("away_total_throws")) else None,
            float(r["total_shots"]) if pd.notnull(r.get("total_shots")) else None,
            float(r["total_shots_ontarget"]) if pd.notnull(r.get("total_shots_ontarget")) else None,
            float(r["total_saves"]) if pd.notnull(r.get("total_saves")) else None,
            int(r["referee_id"]) if pd.notnull(r.get("referee_id")) else None,
            ref_name,
            float(r["total_yellow_cards"]) if pd.notnull(r.get("total_yellow_cards")) else None,
            float(r["total_red_cards"]) if pd.notnull(r.get("total_red_cards")) else None,
            float(r["total_cards"]) if pd.notnull(r.get("total_cards")) else None,
            float(r["total_fouls"]) if pd.notnull(r.get("total_fouls")) else None,
            float(r["home_total_yel_card"]) if pd.notnull(r.get("home_total_yel_card")) else None,
            float(r["away_total_yel_card"]) if pd.notnull(r.get("away_total_yel_card")) else None,
            float(r["home_total_red_card"]) if pd.notnull(r.get("home_total_red_card")) else None,
            float(r["away_total_red_card"]) if pd.notnull(r.get("away_total_red_card")) else None,
            float(r["home_xg"]) if pd.notnull(r.get("home_xg")) else None,
            float(r["away_xg"]) if pd.notnull(r.get("away_xg")) else None,
            float(r["total_xg"]) if pd.notnull(r.get("total_xg")) else None,
        ))

    cursor.executemany("""
    INSERT OR REPLACE INTO matches (
        match_id, season, gameweek, match_date, kickoff_label, day_label, time_label,
        ground_name, home_id, home_name, home_abbr, home_score, away_id, away_name, away_abbr, away_score,
        status, total_corners, home_won_corners, away_won_corners, total_throws, home_total_throws,
        away_total_throws, total_shots, total_shots_ontarget, total_saves, referee_id, referee_name,
        total_yellow_cards, total_red_cards, total_cards, total_fouls, home_total_yel_card, away_total_yel_card,
        home_total_red_card, away_total_red_card, home_xg, away_xg, total_xg
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
    """, matches_to_insert)

    # Insert remaining upcoming 2026_27 fixtures from raw json if not in parquet
    existing_mids = set(r[0] for r in matches_to_insert)
    upcoming_to_insert = []
    for f in raw_2627:
        mid = int(f.get("id", 0))
        if mid in existing_mids:
            continue
        teams = f.get("teams", [])
        if len(teams) < 2:
            continue
        h_team = teams[0].get("team", {})
        a_team = teams[1].get("team", {})
        h_score = teams[0].get("score")
        a_score = teams[1].get("score")
        kickoff_str = f.get("kickoff", {}).get("label", "")
        day_p = kickoff_str.split(",")[0].strip() if "," in kickoff_str else kickoff_str
        time_p = kickoff_str.split(",")[1].strip() if "," in kickoff_str else ""
        gw = int(f.get("gameweek", {}).get("gameweek", 1))

        # Check match official if any
        officials = f.get("matchOfficials", [])
        ref_id = officials[0].get("matchOfficial", {}).get("id") if officials else None
        ref_n = officials[0].get("matchOfficial", {}).get("name", {}).get("display") if officials else "Atanmadı"

        upcoming_to_insert.append((
            mid, DEFAULT_SEASON, gw, "", kickoff_str, day_p, time_p,
            f.get("ground", {}).get("name", "Premier League Stadı"),
            int(h_team.get("id", 0)), h_team.get("name", ""), h_team.get("club", {}).get("abbr", ""),
            h_score, int(a_team.get("id", 0)), a_team.get("name", ""), a_team.get("club", {}).get("abbr", ""),
            a_score, "COMPLETED" if (h_score is not None and a_score is not None) else "UPCOMING",
            None, None, None, None, None, None, None, None, None, ref_id, ref_n,
            None, None, None, None, None, None, None, None, None, None, None
        ))

    if upcoming_to_insert:
        cursor.executemany("""
        INSERT OR REPLACE INTO matches (
            match_id, season, gameweek, match_date, kickoff_label, day_label, time_label,
            ground_name, home_id, home_name, home_abbr, home_score, away_id, away_name, away_abbr, away_score,
            status, total_corners, home_won_corners, away_won_corners, total_throws, home_total_throws,
            away_total_throws, total_shots, total_shots_ontarget, total_saves, referee_id, referee_name,
            total_yellow_cards, total_red_cards, total_cards, total_fouls, home_total_yel_card, away_total_yel_card,
            home_total_red_card, away_total_red_card, home_xg, away_xg, total_xg
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """, upcoming_to_insert)

    conn.commit()

    # Now calculate and aggregate referees table
    cursor.execute("DELETE FROM referees;")

    # Seasons to process + 'all'
    seasons = list(reversed(SEASONS))
    for s in seasons:
        cursor.execute("""
        SELECT 
            referee_name,
            COUNT(*) as matches_count,
            SUM(total_yellow_cards) as total_yellows,
            AVG(total_yellow_cards) as avg_yellows,
            SUM(total_red_cards) as total_reds,
            AVG(total_red_cards) as avg_reds,
            SUM(total_cards) as total_c,
            AVG(total_cards) as avg_c,
            SUM(total_fouls) as total_f,
            AVG(total_fouls) as avg_f,
            SUM(CASE WHEN total_cards >= 4 THEN 1 ELSE 0 END) as over_35_cnt
        FROM matches
        WHERE referee_name != 'Unknown' AND referee_name != 'Atanmadı' AND status = 'COMPLETED' AND season = ?
        GROUP BY referee_name
        HAVING COUNT(*) > 0
        """, (s,))
        rows = cursor.fetchall()

        for r in rows:
            m_cnt = r["matches_count"]
            avg_c = round(r["avg_c"] or 0.0, 2)
            avg_y = round(r["avg_yellows"] or 0.0, 2)
            avg_r = round(r["avg_reds"] or 0.0, 2)
            avg_f = round(r["avg_f"] or 0.0, 1)
            over_35_pct = round((r["over_35_cnt"] / m_cnt) * 100, 1) if m_cnt > 0 else 0.0

            if avg_c >= 4.6 or over_35_pct >= 70.0:
                strictness = "Yüksek Kart Eğilimi"
            elif avg_c <= 3.2:
                strictness = "Akıcı Oyun / Az Kart"
            else:
                strictness = "Dengeli Yönetim"

            cursor.execute("""
            INSERT INTO referees (
                referee_name, season, matches_count, total_yellow_cards, avg_yellow_cards,
                total_red_cards, avg_red_cards, total_cards, avg_cards, total_fouls, avg_fouls,
                over_3_5_cards_count, over_3_5_pct, strictness_label
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """, (
                r["referee_name"], s, m_cnt,
                r["total_yellows"] or 0.0, avg_y,
                r["total_reds"] or 0.0, avg_r,
                r["total_c"] or 0.0, avg_c,
                r["total_f"] or 0.0, avg_f,
                r["over_35_cnt"], over_35_pct, strictness
            ))

    # All-time aggregates across all seasons
    cursor.execute("""
    SELECT 
        referee_name,
        COUNT(*) as matches_count,
        SUM(total_yellow_cards) as total_yellows,
        AVG(total_yellow_cards) as avg_yellows,
        SUM(total_red_cards) as total_reds,
        AVG(total_red_cards) as avg_reds,
        SUM(total_cards) as total_c,
        AVG(total_cards) as avg_c,
        SUM(total_fouls) as total_f,
        AVG(total_fouls) as avg_f,
        SUM(CASE WHEN total_cards >= 4 THEN 1 ELSE 0 END) as over_35_cnt
    FROM matches
    WHERE referee_name != 'Unknown' AND referee_name != 'Atanmadı' AND status = 'COMPLETED'
    GROUP BY referee_name
    HAVING COUNT(*) > 0
    """)
    all_rows = cursor.fetchall()
    for r in all_rows:
        m_cnt = r["matches_count"]
        avg_c = round(r["avg_c"] or 0.0, 2)
        avg_y = round(r["avg_yellows"] or 0.0, 2)
        avg_r = round(r["avg_reds"] or 0.0, 2)
        avg_f = round(r["avg_f"] or 0.0, 1)
        over_35_pct = round((r["over_35_cnt"] / m_cnt) * 100, 1) if m_cnt > 0 else 0.0

        if avg_c >= 4.6 or over_35_pct >= 70.0:
            strictness = "Yüksek Kart Eğilimi"
        elif avg_c <= 3.2:
            strictness = "Akıcı Oyun / Az Kart"
        else:
            strictness = "Dengeli Yönetim"

        cursor.execute("""
        INSERT INTO referees (
            referee_name, season, matches_count, total_yellow_cards, avg_yellow_cards,
            total_red_cards, avg_red_cards, total_cards, avg_cards, total_fouls, avg_fouls,
            over_3_5_cards_count, over_3_5_pct, strictness_label
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);
        """, (
            r["referee_name"], "all", m_cnt,
            r["total_yellows"] or 0.0, avg_y,
            r["total_reds"] or 0.0, avg_r,
            r["total_c"] or 0.0, avg_c,
            r["total_f"] or 0.0, avg_f,
            r["over_35_cnt"], over_35_pct, strictness
        ))

    conn.commit()
    conn.close()
    logger.info("Successfully populated SQLite database and referee aggregates.")


def get_referee_summary(name: str, season: str = DEFAULT_SEASON) -> Dict[str, Any]:
    """Returns referee aggregates for a given season or career fallback."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM referees WHERE referee_name = ? AND season = ?", (name, season))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM referees WHERE referee_name = ? AND season = 'all'", (name,))
        row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "referee_name": name,
        "season": season,
        "matches_count": 0,
        "avg_yellow_cards": 4.15,
        "avg_red_cards": 0.12,
        "avg_cards": 4.27,
        "avg_fouls": 21.5,
        "over_3_5_pct": 55.0,
        "strictness_label": "Standart Hakem"
    }


def get_referees_list(season: str = DEFAULT_SEASON, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns list of referees for the selected season, optionally filtered by search."""
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT * FROM referees 
        WHERE season = ?
    """
    params = [season]
    if search:
        query += " AND referee_name LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY matches_count DESC, avg_cards DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]

    # If few referees in current season, also fetch available active refs from 'all'
    if len(rows) < 10 and season == DEFAULT_SEASON:
        cursor.execute("SELECT * FROM referees WHERE season = 'all' ORDER BY matches_count DESC")
        all_refs = {r["referee_name"]: dict(r) for r in cursor.fetchall()}
        existing_names = {r["referee_name"] for r in rows}
        for name, ref_data in all_refs.items():
            if name not in existing_names and (not search or search.lower() in name.lower()):
                ref_copy = dict(ref_data)
                ref_copy["season"] = season
                ref_copy["is_career_fallback"] = True
                rows.append(ref_copy)

    conn.close()
    return rows


def get_referee_detail(referee_name: str, season: str = DEFAULT_SEASON) -> Dict[str, Any]:
    """Returns referee detailed profile, career stats, and match history."""
    conn = get_db()
    cursor = conn.cursor()

    # Season stats
    cursor.execute("SELECT * FROM referees WHERE referee_name = ? AND season = ?", (referee_name, season))
    season_row = cursor.fetchone()
    season_stats = dict(season_row) if season_row else None

    # Career stats
    cursor.execute("SELECT * FROM referees WHERE referee_name = ? AND season = 'all'", (referee_name,))
    career_row = cursor.fetchone()
    career_stats = dict(career_row) if career_row else None

    # Matches officiated in this season (or all if requested)
    if season != "all":
        cursor.execute("""
            SELECT * FROM matches 
            WHERE referee_name = ? AND season = ? AND status = 'COMPLETED'
            ORDER BY gameweek DESC, match_date DESC
        """, (referee_name, season))
    else:
        cursor.execute("""
            SELECT * FROM matches 
            WHERE referee_name = ? AND status = 'COMPLETED'
            ORDER BY season DESC, gameweek DESC, match_date DESC
        """, (referee_name,))
    matches = [dict(r) for r in cursor.fetchall()]

    # Disciplinary breakdown by team
    team_card_counts = {}
    for m in matches:
        hid, hname = m["home_id"], m["home_name"]
        aid, aname = m["away_id"], m["away_name"]
        hy = m["home_total_yel_card"] or 0
        hr = m["home_total_red_card"] or 0
        ay = m["away_total_yel_card"] or 0
        ar = m["away_total_red_card"] or 0

        if hname not in team_card_counts:
            team_card_counts[hname] = {"team_id": hid, "team_name": hname, "yellows": 0, "reds": 0, "matches": 0}
        team_card_counts[hname]["yellows"] += hy
        team_card_counts[hname]["reds"] += hr
        team_card_counts[hname]["matches"] += 1

        if aname not in team_card_counts:
            team_card_counts[aname] = {"team_id": aid, "team_name": aname, "yellows": 0, "reds": 0, "matches": 0}
        team_card_counts[aname]["yellows"] += ay
        team_card_counts[aname]["reds"] += ar
        team_card_counts[aname]["matches"] += 1

    team_breakdown = sorted(list(team_card_counts.values()), key=lambda x: (x["yellows"] + x["reds"] * 2), reverse=True)

    conn.close()
    return {
        "referee_name": referee_name,
        "selected_season": season,
        "season_stats": season_stats or career_stats or {
            "referee_name": referee_name, "matches_count": 0, "avg_cards": 4.15, "avg_fouls": 21.5, "strictness_label": "Standart"
        },
        "career_stats": career_stats or season_stats,
        "matches_count": len(matches),
        "matches": matches,
        "team_breakdown": team_breakdown[:8]
    }


def get_all_grouped_fixtures(season: str = DEFAULT_SEASON) -> List[Dict[str, Any]]:
    """Fetches all matches from SQLite for the given season with referee stats pre-attached."""
    conn = get_db()
    cursor = conn.cursor()
    if season != "all":
        cursor.execute("""
            SELECT m.*, x.provider AS xg_provider, x.home_xg AS statsapi_home_xg,
                   x.away_xg AS statsapi_away_xg, x.xg_quality AS statsapi_xg_quality,
                   r.avg_cards as ref_avg_cards, r.avg_yellow_cards as ref_avg_yellows,
                   r.avg_red_cards as ref_avg_reds, r.strictness_label as ref_strictness
            FROM matches m
            LEFT JOIN external_match_xg x ON x.match_id = m.match_id
            LEFT JOIN referees r ON m.referee_name = r.referee_name AND r.season = m.season
            WHERE m.season = ?
            ORDER BY m.gameweek ASC, m.match_date ASC, m.match_id ASC
        """, (season,))
    else:
        cursor.execute("""
            SELECT m.*, x.provider AS xg_provider, x.home_xg AS statsapi_home_xg,
                   x.away_xg AS statsapi_away_xg, x.xg_quality AS statsapi_xg_quality,
                   r.avg_cards as ref_avg_cards, r.avg_yellow_cards as ref_avg_yellows,
                   r.avg_red_cards as ref_avg_reds, r.strictness_label as ref_strictness
            FROM matches m
            LEFT JOIN external_match_xg x ON x.match_id = m.match_id
            LEFT JOIN referees r ON m.referee_name = r.referee_name AND r.season = 'all'
            ORDER BY m.season DESC, m.gameweek ASC, m.match_date ASC
        """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    populate_db_from_sources()

