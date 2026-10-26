"""Per-competition raw files and the guard against match-id clashes between competitions."""

import json
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from src.ingest import raw_store
from src.ingest.sync_competition_data import assert_ids_free


def test_raw_files_live_under_their_own_competition_and_provider():
    with tempfile.TemporaryDirectory() as tmp:
        fake = lambda key: SimpleNamespace(raw=Path(tmp) / key / "raw")
        with mock.patch.object(raw_store, "competition_paths", fake):
            ucl = raw_store.match_payload_path("champions_league", "TheStatsAPI", 7, "stats")
            uel = raw_store.match_payload_path("europa_league", "TheStatsAPI", 7, "stats")
            assert ucl != uel
            assert ucl == Path(tmp) / "champions_league" / "raw" / "thestatsapi" / "matches" / "7_stats.json"
            assert raw_store.competition_payload_path("europa_league", "UEFA", "2025_26", "standings") == (
                Path(tmp) / "europa_league" / "raw" / "uefa" / "competition" / "2025_26_standings.json"
            )
            assert raw_store.season_file_path("champions_league", "uefa", "fixtures", "2025_26").name == "fixtures_2025_26.json"


def test_write_json_is_atomic_and_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "a" / "b.json"
        raw_store.write_json(target, {"k": "ğ"})
        assert json.loads(target.read_text(encoding="utf-8")) == {"k": "ğ"}
        assert list(target.parent.glob("*.tmp")) == []


def test_a_feed_cannot_reuse_another_competitions_match_id():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE matches (match_id INTEGER PRIMARY KEY, competition_id INTEGER)")
    conn.executemany("INSERT INTO matches VALUES (?, ?)", [(1, 39), (2, 2)])
    assert_ids_free(conn, 2, [2, 3])  # its own id and a new one are fine
    with pytest.raises(ValueError, match="another competition"):
        assert_ids_free(conn, 3, [1, 9])
