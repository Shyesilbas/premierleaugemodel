import json
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd

from src.config import DEFAULT_SEASON
from src.db import database

PAST_SEASON = "2025_26"  # referee aggregates run over database.SEASONS, which is empty without cached fixtures


def _match(match_id, gameweek, home_score, away_score, cards):
    return {
        "match_id": match_id, "season": PAST_SEASON, "gameweek": gameweek, "match_date": "",
        "kickoff_label": "Sat 1 Aug 2026, 15:00 BST", "ground_name": "Emirates",
        "home_id": 1, "home_name": "Arsenal", "home_abbr": "ARS", "home_score": home_score,
        "away_id": 2, "away_name": "Chelsea", "away_abbr": "CHE", "away_score": away_score,
        "referee_id": 77, "referee_name": "A Referee", "total_cards": cards, "total_yellow_cards": cards,
        "total_red_cards": 0.0, "total_fouls": 20.0,
    }


def _fixture(match_id):
    team = lambda tid, name, abbr: {"team": {"id": tid, "name": name, "club": {"abbr": abbr}}, "score": None}
    return {"id": match_id, "teams": [team(3, "Spurs", "TOT"), team(4, "Fulham", "FUL")],
            "kickoff": {"label": "Sat 8 Aug 2026, 15:00 BST"}, "gameweek": {"gameweek": 2},
            "matchOfficials": [], "ground": {"name": "Tottenham Hotspur Stadium"}}


def _populate(tmp: str) -> sqlite3.Connection:
    root = Path(tmp)
    (root / "processed").mkdir()
    (root / "raw").mkdir()
    pd.DataFrame([_match(10, 1, 2.0, 0.0, 3.0), _match(11, 2, 1.0, 1.0, 6.0), _match(12, 3, None, None, None)]).to_parquet(
        root / "processed" / "matches_summary_all.parquet")
    (root / "raw" / f"fixtures_{DEFAULT_SEASON}.json").write_text(json.dumps([_fixture(999)]))
    return root


def test_populate_loads_matches_upcoming_fixtures_and_referee_aggregates_and_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        root = _populate(tmp)
        with mock.patch.multiple(database, DATA_DIR=root, DB_PATH=root / "db.sqlite", RAW_DIR=root / "raw", MATCHES_SUMMARY_PATH=root / "processed" / "matches_summary_all.parquet", SEASONS=[PAST_SEASON]):
            database.populate_db_from_sources()
            database.populate_db_from_sources()  # a second run must change nothing
            conn = sqlite3.connect(root / "db.sqlite")
            status = dict(conn.execute("SELECT match_id, status FROM matches"))
            referee = conn.execute(
                "SELECT matches_count, avg_cards, strictness_label FROM referees WHERE referee_name = 'A Referee' AND season = ?",
                (PAST_SEASON,),
            ).fetchall()
            n_matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
            conn.close()
    assert status == {10: "COMPLETED", 11: "COMPLETED", 12: "UPCOMING", 999: "UPCOMING"}
    assert n_matches == 4  # 3 from parquet + the raw-fixture-only match, no duplicates after two runs
    assert referee == [(2, 4.5, "Dengeli Yönetim")]  # only the two completed matches count


def test_populate_keeps_provider_xg_and_odds_tables():
    with tempfile.TemporaryDirectory() as tmp:
        root = _populate(tmp)
        with mock.patch.multiple(database, DATA_DIR=root, DB_PATH=root / "db.sqlite", RAW_DIR=root / "raw", MATCHES_SUMMARY_PATH=root / "processed" / "matches_summary_all.parquet", SEASONS=[PAST_SEASON]):
            database.init_db()
            conn = sqlite3.connect(root / "db.sqlite")
            conn.execute("INSERT INTO external_match_xg VALUES (10, 'TheStatsAPI', 'm1', 's1', 1.4, 0.6, 'full', 'x')")
            conn.commit()
            conn.close()
            database.populate_db_from_sources()
            conn = sqlite3.connect(root / "db.sqlite")
            kept = conn.execute("SELECT home_xg, away_xg FROM external_match_xg WHERE match_id = 10").fetchall()
            conn.close()
    assert kept == [(1.4, 0.6)]
