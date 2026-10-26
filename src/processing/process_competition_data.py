"""Unified multi-competition data processing and SQLite synchronization pipeline.

Parses raw fixtures, match statistics, details, and play-by-play streams for any registered
competition (Premier League, Champions League, Europa League), outputs canonical Parquet tables,
and updates the SQLite matches database table with competition_id tagging.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.competitions.registry import get_competition
from src.config import competition_paths, configure_logging
from src.db.database import get_db, init_db
from src.processing.process_season_data import (
    parse_match,
    parse_stream_events,
)

logger = logging.getLogger("process_competition_data")


def process_competition_season(
    competition_key: str = "champions_league",
    season_name: str = "2026_27",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Process a single season for a given competition."""
    comp = get_competition(competition_key)
    paths = competition_paths(comp.key)
    comp_raw_dir = paths.raw

    if not comp_raw_dir.exists():
        logger.warning(f"No raw data directory for {comp.key}: {comp_raw_dir}")
        return pd.DataFrame(), pd.DataFrame()

    matches_dir = comp_raw_dir / "matches"
    fixture_file = comp_raw_dir / f"fixtures_{season_name}.json"

    if not fixture_file.exists():
        logger.warning(f"No fixture file found at {fixture_file}")
        return pd.DataFrame(), pd.DataFrame()

    with open(fixture_file, "r", encoding="utf-8") as f:
        fixtures_data = json.load(f)

    # Some providers return {"content": [...]}, others a flat list [...]
    fixtures = fixtures_data.get("content", fixtures_data) if isinstance(fixtures_data, dict) else fixtures_data

    matches_rows: List[Dict[str, Any]] = []
    events_rows: List[Dict[str, Any]] = []

    for fix in fixtures:
        match_id = int(fix["id"])
        stats_file = matches_dir / f"{match_id}_stats.json"
        stream_file = matches_dir / f"{match_id}_stream.json"
        details_file = matches_dir / f"{match_id}_details.json"

        stats_data = None
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                stats_data = json.load(f)

        details_data = None
        if details_file.exists():
            with open(details_file, "r", encoding="utf-8") as f:
                details_data = json.load(f)

        stream_data = None
        if stream_file.exists():
            with open(stream_file, "r", encoding="utf-8") as f:
                stream_data = json.load(f)

        match_record = parse_match(fix, stats_data, details_data, stream_data)
        if match_record:
            match_record["season"] = season_name
            match_record["competition_id"] = comp.id
            match_record["stage"] = fix.get("gameweek", {}).get("stage", "league")
            if stats_data and "data" in stats_data:
                h_id_str = str(match_record.get("home_id"))
                a_id_str = str(match_record.get("away_id"))
                h_xg = stats_data["data"].get(h_id_str, {}).get("xg")
                a_xg = stats_data["data"].get(a_id_str, {}).get("xg")
                if h_xg is not None:
                    match_record["home_xg"] = float(h_xg)
                if a_xg is not None:
                    match_record["away_xg"] = float(a_xg)
                if h_xg is not None and a_xg is not None:
                    match_record["total_xg"] = float(h_xg) + float(a_xg)
            matches_rows.append(match_record)

        if stream_data is not None:
            stream_events = parse_stream_events(match_id, stream_data)
            for ev in stream_events:
                ev["competition_id"] = comp.id
            events_rows.extend(stream_events)

    df_matches = pd.DataFrame(matches_rows)
    df_events = pd.DataFrame(events_rows)

    # Save to processed directory
    comp_processed_dir = paths.processed
    comp_processed_dir.mkdir(parents=True, exist_ok=True)

    matches_parquet = comp_processed_dir / f"matches_summary_{season_name}.parquet"
    events_parquet = comp_processed_dir / f"shots_events_{season_name}.parquet"

    if not df_matches.empty:
        df_matches.to_parquet(matches_parquet, index=False)
        logger.info(f"Saved {len(df_matches)} matches to {matches_parquet}")

    if not df_events.empty:
        df_events.to_parquet(events_parquet, index=False)
        logger.info(f"Saved {len(df_events)} events to {events_parquet}")

    # Synchronize into SQLite matches database
    sync_matches_to_sqlite(df_matches, comp.id, season_name)

    return df_matches, df_events


def sync_matches_to_sqlite(df_matches: pd.DataFrame, competition_id: int, season: str) -> None:
    """Inserts or replaces processed match rows into the SQLite matches table."""
    if df_matches.empty:
        return

    init_db()
    conn = get_db()
    cursor = conn.cursor()

    matches_to_insert = []
    for _, r in df_matches.iterrows():
        mid = int(r["match_id"])
        h_score = float(r["home_score"]) if pd.notnull(r.get("home_score")) else None
        a_score = float(r["away_score"]) if pd.notnull(r.get("away_score")) else None
        is_completed = (h_score is not None and a_score is not None)

        kickoff = str(r.get("kickoff_label") or "")
        day_p = kickoff.split(",")[0].strip() if "," in kickoff else kickoff
        time_p = kickoff.split(",")[1].strip() if "," in kickoff else ""

        ref_name = str(r.get("referee_name") or "Unknown").strip()

        matches_to_insert.append((
            mid,
            str(r.get("season", season)),
            int(r.get("gameweek", 1)),
            str(r.get("stage", "league")),
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
            competition_id,
        ))

    cursor.executemany("""
    INSERT OR REPLACE INTO matches (
        match_id, season, gameweek, stage, match_date, kickoff_label, day_label, time_label,
        ground_name, home_id, home_name, home_abbr, home_score, away_id, away_name, away_abbr, away_score,
        status, total_corners, home_won_corners, away_won_corners, total_throws, home_total_throws,
        away_total_throws, total_shots, total_shots_ontarget, total_saves, referee_id, referee_name,
        total_yellow_cards, total_red_cards, total_cards, total_fouls, home_total_yel_card, away_total_yel_card,
        home_total_red_card, away_total_red_card, home_xg, away_xg, total_xg, competition_id
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
    """, matches_to_insert)

    conn.commit()
    conn.close()
    logger.info(f"Synchronized {len(matches_to_insert)} matches for competition {competition_id} into SQLite.")


def main():
    parser = argparse.ArgumentParser(description="Process competition season data.")
    parser.add_argument("--competition", type=str, default="champions_league", help="Competition key (premier_league, champions_league, europa_league)")
    parser.add_argument("--season", type=str, default="2026_27", help="Season name (e.g. 2026_27)")
    args = parser.parse_args()

    configure_logging()
    process_competition_season(competition_key=args.competition, season_name=args.season)


if __name__ == "__main__":
    main()
