"""Regression tests for Stage 2 backend audit fixes (regex/NaN safety, competition scoping, TM exact match, conn closing)."""

import sqlite3
import tempfile
import warnings
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api import state
from src.api.routes import fixtures as fixtures_route
from src.api.routes import matches as matches_route
from src.api.routes import players as players_route
from src.api.routes import stats as stats_route
from src.api.routes import teams as teams_route
from src.api.server import app
from src.db import database

client = TestClient(app)


def _init_temp_db(tmp: str) -> Path:
    db_path = Path(tmp) / "audit_test.db"
    with mock.patch.object(database, "DATA_DIR", Path(tmp)), mock.patch.object(database, "DB_PATH", db_path):
        database.init_db()
        conn = database.get_db(db_path)
        database.ensure_market_value_tables(conn)
        conn.close()
    return db_path


def test_fixtures_search_escapes_regex_characters_and_handles_nan():
    df = pd.DataFrame({
        "match_id": [1, 2],
        "season": ["2026_27", "2026_27"],
        "home_name": ["Arsenal [Home]", None],
        "away_name": ["Chelsea", "Spurs (A)"],
        "ground_name": [np.nan, "N17"],
        "home_score": [1.0, np.nan],
        "match_date": pd.to_datetime(["2026-08-01", "2026-08-02"]),
    })
    with mock.patch.object(state, "df_matches", df):
        res_bracket = client.get("/api/fixtures", params={"search": "["})
        res_paren = client.get("/api/fixtures", params={"search": "(A)"})
    assert res_bracket.status_code == 200
    assert [m["match_id"] for m in res_bracket.json()["fixtures"]] == [1]
    assert res_paren.status_code == 200
    assert [m["match_id"] for m in res_paren.json()["fixtures"]] == [2]


def test_match_recent_form_scopes_db_fallback_by_competition_id():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO matches (
                match_id, competition_id, season, gameweek, match_date, kickoff_label,
                home_id, home_name, away_id, away_name, home_score, away_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                # Prior UCL match (comp=2) for same team ID 10 — must NOT leak into PL (comp=39) form
                (100, 2, "2026_27", 1, "2026-08-05", "18:00", 10, "Team A", 99, "Other", 0.0, 4.0, "COMPLETED"),
                # Prior PL match (comp=39) for Team A (won) and Team B (lost)
                (101, 39, "2026_27", 1, "2026-08-01", "15:00", 10, "Team A", 20, "Team B", 3.0, 0.0, "COMPLETED"),
                # Target PL match
                (102, 39, "2026_27", 2, "2026-08-10", "15:00", 10, "Team A", 20, "Team B", None, None, "UPCOMING"),
            ],
        )
        conn.commit()
        conn.close()

        opener = lambda: database.get_db(db_path)
        with (
            mock.patch.object(state, "df_matches", pd.DataFrame()),
            mock.patch.object(fixtures_route, "get_db", side_effect=opener),
        ):
            res = client.get("/api/match/102/recent-form")
        assert res.status_code == 200
        form = res.json()["form"]
        assert form["10"] == ["W"]
        assert form["20"] == ["L"]


def test_market_value_lookup_prioritizes_exact_name_over_higher_value_surname():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO player_market_values (
                player_id, team_id, name, position, market_value, market_value_eur,
                age, nationality, season, updated_at, competition_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("tm_high", 1, "Bernardo Silva", "M", 80_000_000, 80.0, 30, "POR", "2026_27", "now", 39),
                ("tm_exact", 2, "Fabio Silva", "F", 15_000_000, 15.0, 23, "POR", "2026_27", "now", 39),
            ],
        )
        conn.commit()
        conn.close()

        reg_player = {"id": 9999, "name": "Fabio Silva", "position": "F", "teamId": 2, "teamName": "Wolves"}
        opener = lambda: database.get_db(db_path)
        with (
            mock.patch.object(state, "all_players", [reg_player]),
            mock.patch.object(state, "get_player_match_logs", return_value=[]),
            mock.patch("src.api.routes.players.get_match_bookings_map", return_value={}),
            mock.patch.object(players_route, "get_db", side_effect=opener),
        ):
            profile_res = client.get("/api/players/profile", params={"player_id": "9999"})
            history_res = client.get("/api/players/9999/market-value-history", params={"name": "Fabio Silva"})

        assert profile_res.status_code == 200
        assert profile_res.json()["player"]["market_value"]["tm_id"] == "tm_exact"
        assert profile_res.json()["player"]["market_value"]["market_value_eur"] == 15.0
        assert history_res.status_code == 200
        assert history_res.json()["tm_id"] == "tm_exact"


def test_team_market_values_keeps_newest_season_without_overwriting():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO player_market_values (
                player_id, team_id, name, position, market_value, market_value_eur,
                age, nationality, season, updated_at, competition_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("p1", 10, "Alex Doe", "M", 12_000_000, 12.0, 22, "ENG", "2023_24", "old", 39),
                ("p1", 10, "Alex Doe", "M", 45_000_000, 45.0, 24, "ENG", "2025_26", "new", 39),
            ],
        )
        conn.commit()
        conn.close()

        opener = lambda: database.get_db(db_path)
        with mock.patch.object(teams_route, "get_db", side_effect=opener):
            _, player_values = teams_route._load_team_market_values(10, "2026_27")
        assert player_values["alex doe"]["eur"] == 45.0


def test_grouped_fixtures_non_pl_emits_no_utcnow_deprecation_warning():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            INSERT INTO matches (
                match_id, competition_id, season, gameweek, match_date, kickoff_label,
                home_id, home_name, away_id, away_name, status
            ) VALUES (100001, 2, '2026_27', 1, '2026-08-15', '17:00', 101, 'Home', 102, 'Away', 'UPCOMING')
            """
        )
        conn.commit()
        conn.close()

        opener = lambda: database.get_db(db_path)
        with (
            mock.patch.object(database, "DB_PATH", db_path),
            mock.patch.object(fixtures_route, "get_db", side_effect=opener),
            warnings.catch_warnings(record=True) as caught,
        ):
            warnings.simplefilter("always", DeprecationWarning)
            res = client.get("/api/fixtures/grouped", params={"season": "2026_27", "competition": "champions_league"})

        assert res.status_code == 200
        assert not [w for w in caught if "utcnow" in str(w.message)]


def test_sqlite_connections_are_explicitly_closed_on_success_and_error():
    closed_flags = []

    class TrackedConn:
        def __init__(self, inner: sqlite3.Connection, raise_on_exec: bool = False):
            self._inner = inner
            self._raise = raise_on_exec
            self.closed = False
            closed_flags.append(self)

        def cursor(self):
            return self

        def execute(self, *args, **kwargs):
            if self._raise:
                raise sqlite3.OperationalError("simulated error")
            return self._inner.execute(*args, **kwargs)

        def fetchall(self):
            return []

        def fetchone(self):
            return None

        def close(self):
            self.closed = True
            self._inner.close()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    def _make_tracked(db_path: Path, raise_on_exec: bool = False):
        return TrackedConn(database.get_db(db_path), raise_on_exec=raise_on_exec)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        with mock.patch.object(matches_route, "get_db", side_effect=lambda: _make_tracked(db_path, raise_on_exec=True)):
            assert matches_route.get_match_odds_list(1) == []
            assert matches_route._fetch_match_xg_info(1) == (None, None, None, None, None)

        with mock.patch.object(stats_route, "get_db", side_effect=lambda: _make_tracked(db_path, raise_on_exec=True)):
            assert stats_route._audit_rows("2026_27") == []

        with mock.patch.object(fixtures_route, "get_db", side_effect=lambda: _make_tracked(db_path, raise_on_exec=False)):
            assert client.get("/api/referees", params={"competition": "champions_league", "season": "2026_27"}).status_code == 200
            assert client.get("/api/standings", params={"competition": "champions_league", "season": "2026_27"}).status_code == 200
            assert client.get("/api/match/999/recent-form").status_code == 404

    assert len(closed_flags) == 6
    assert all(conn.closed for conn in closed_flags)


def test_extract_main_referee_supports_flat_and_nested_officials():
    assert matches_route._extract_main_referee([
        {"role": "FOURTH_OFFICIAL", "name": {"display": "Fourth"}},
        {"role": "MAIN", "name": {"display": "Andy Madley"}},
    ]) == "Andy Madley"
    assert matches_route._extract_main_referee([
        {"type": "Referee", "matchOfficial": {"name": {"display": "Peter Bankes"}}},
    ]) == "Peter Bankes"
    assert matches_route._extract_main_referee([]) is None


def test_reload_middleware_skips_admin_routes_and_active_syncs():
    from src.api.routes import meta as meta_route

    with mock.patch.object(state, "_reload_if_data_changed") as reload_spy:
        assert client.get("/api/admin/sync-season").status_code == 200
        reload_spy.assert_not_called()

        with mock.patch.object(meta_route, "is_sync_running", return_value=True):
            assert client.get("/api/data-version").status_code == 200
            reload_spy.assert_not_called()

        with mock.patch.object(meta_route, "is_sync_running", return_value=False):
            assert client.get("/api/data-version").status_code == 200
            reload_spy.assert_called_once()


def test_etag_middleware_returns_304_on_unchanged_read_route_and_skips_data_version():
    res1 = client.get("/api/competitions")
    assert res1.status_code == 200
    etag = res1.headers.get("etag")
    assert etag and etag.startswith('W/"')
    assert "no-cache" in (res1.headers.get("cache-control") or "")

    res2 = client.get("/api/competitions", headers={"If-None-Match": etag})
    assert res2.status_code == 304
    assert res2.content == b""

    res_ver = client.get("/api/data-version")
    assert res_ver.status_code == 200
    assert "etag" not in {k.lower() for k in res_ver.headers}


def test_players_compare_data_serves_premier_league_and_competition_profiles():
    import json

    fake_players = [
        {"id": 10, "name": "Bukayo Saka", "position": "F", "shirt": 7, "teamId": 1, "teamName": "Arsenal"},
        {"id": 20, "name": "Cole Palmer", "position": "M", "shirt": 20, "teamId": 4, "teamName": "Chelsea"},
    ]
    fake_logs = {
        "10": [
            {
                "match_id": 500, "season": "2026_27", "gameweek": 1, "minutes_played": 90,
                "goals": 2, "assists": 1, "team_id": 1, "team_name": "Arsenal", "team_score": 3, "opp_score": 0, "started": True,
            },
        ],
        "20": [
            {
                "match_id": 501, "season": "2026_27", "gameweek": 1, "minutes_played": 80,
                "goals": 1, "assists": 0, "team_id": 4, "team_name": "Chelsea", "team_score": 1, "opp_score": 2, "started": True,
            },
        ],
    }

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO player_market_values (
                player_id, team_id, name, position, market_value, market_value_eur,
                age, nationality, season, updated_at, competition_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [("9001", 1, "Bukayo Saka", "RW", 140000000, 140.0, 24, "England", "2026_27", "2026-08-01", 39)],
        )
        conn.execute(
            """
            INSERT INTO matches (
                match_id, competition_id, season, gameweek, match_date, kickoff_label,
                home_id, home_name, away_id, away_name, home_score, away_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (900, 2, "2026_27", 1, "2026-09-15", "18:00", 50, "Real Madrid", 60, "PSG", 2.0, 0.0, "COMPLETED"),
        )
        conn.execute(
            "INSERT INTO external_competition_payloads (competition_id, season, provider, kind, payload, fetched_at_utc) VALUES (?, ?, ?, ?, ?, ?)",
            (2, "2026_27", "TheStatsAPI", "squad", json.dumps({
                "team": {"id": "ts_rm", "name": "Real Madrid"},
                "data": [{"id": "ts_p1", "name": "Kylian Mbappe", "position": "F", "market_value": 180000000, "current_team": {"jersey_number": 9}}],
            }), "2026-09-15T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO external_match_payloads (match_id, provider, kind, provider_match_id, payload, fetched_at_utc) VALUES (?, ?, ?, ?, ?, ?)",
            (900, "TheStatsAPI", "player_stats", "ts_m900", json.dumps({
                "data": [{
                    "player_id": "ts_p1", "player_name": "Kylian Mbappe", "team_id": "ts_rm",
                    "played": True, "started": True, "minutes_played": 90, "rating": 8.4,
                    "shooting": {"goals": 2, "expected_goals": 1.35, "total_shots": 5, "shots_on_target": 3},
                    "passing": {"assists": 0, "key_passes": 2},
                    "general": {"yellow_cards": 0, "red_cards": 0},
                }],
            }), "2026-09-15T22:00:00Z"),
        )
        conn.commit()
        conn.close()

        opener = lambda: database.get_db(db_path)
        state._player_compare_cache.clear()
        with (
            mock.patch.object(state, "all_players", fake_players),
            mock.patch.object(state, "_player_logs_dict", fake_logs),
            mock.patch.object(state, "_player_cards_dict", {"2026_27_10": {"yellow": 1, "red": 0}}),
            mock.patch.object(players_route, "get_db", side_effect=opener),
            mock.patch.object(players_route, "DB_PATH", db_path),
            mock.patch.object(players_route, "get_match_bookings_map", return_value={}),
        ):
            res_pl = client.get("/api/players/compare-data")
            assert res_pl.status_code == 200
            body_pl = res_pl.json()
            assert body_pl["competition"] == "premier_league"
            assert {p["id"] for p in body_pl["profiles"]} == {10, 20}
            saka = body_pl["averages"]["10"]["2026_27"]
            assert saka["goals"] == 2 and saka["assists"] == 1 and saka["clean_sheets"] == 1
            assert saka["yellow_cards"] == 1 and saka["market_value_eur"] == 140.0

            res_ucl = client.get("/api/players/compare-data", params={"competition": "champions_league"})
            assert res_ucl.status_code == 200
            body_ucl = res_ucl.json()
            assert body_ucl["competition"] == "champions_league"
            assert body_ucl["averages"]["ts_p1"]["2026_27"]["expected_goals"] == 1.35
            assert body_ucl["averages"]["ts_p1"]["2026_27"]["avg_rating"] == 8.4
        state._player_compare_cache.clear()


def test_pending_matches_lists_overdue_uncompleted_fixtures():
    from src.api import match_refresh

    with tempfile.TemporaryDirectory() as tmp:
        db_path = _init_temp_db(tmp)
        conn = sqlite3.connect(db_path)
        conn.executemany(
            """
            INSERT INTO matches (
                match_id, competition_id, season, gameweek, match_date, kickoff_label,
                home_id, home_name, away_id, away_name, home_score, away_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                # Overdue past match still UPCOMING -> must appear in pending
                (7001, 39, "2026_27", 1, "2025-01-01", "Wed 01 Jan 2025, 15:00 GMT", 1, "Arsenal", 4, "Chelsea", None, None, "UPCOMING"),
                # Future match -> must NOT appear in pending
                (7002, 39, "2026_27", 30, "2099-05-01", "Fri 01 May 2099, 15:00 BST", 1, "Arsenal", 4, "Chelsea", None, None, "UPCOMING"),
            ],
        )
        conn.commit()
        conn.close()

        opener = lambda: database.get_db(db_path)
        with (
            mock.patch.object(match_refresh, "get_db", side_effect=opener),
            mock.patch.object(match_refresh, "RAW_DIR", Path(tmp)),
            mock.patch.object(match_refresh, "MATCHES_RAW_DIR", Path(tmp)),
        ):
            res = client.get("/api/fixtures/pending", params={"season": "2026_27", "competition": "premier_league"})
        assert res.status_code == 200
        data = res.json()
        assert data["pending_match_ids"] == [7001]
        assert data["count"] == 1


def test_match_refresh_and_reload_clear_analytics_inner_lru_caches():
    from src.analytics import player_ratings, team_attackers, team_scenarios, team_tactics
    from src.api import match_refresh

    team_tactics.load_team_match_rows()
    team_scenarios.load_team_match_scenarios()
    team_attackers._load_inputs()
    player_ratings._bookings_cache = {1: {}}

    assert team_tactics.load_team_match_rows.cache_info().currsize >= 1
    assert team_scenarios.load_team_match_scenarios.cache_info().currsize >= 1
    assert team_attackers._load_inputs.cache_info().currsize >= 1

    match_refresh._invalidate_match_caches(1)
    assert team_tactics.load_team_match_rows.cache_info().currsize == 0
    assert team_scenarios.load_team_match_scenarios.cache_info().currsize == 0
    assert team_attackers._load_inputs.cache_info().currsize == 0
    assert player_ratings._bookings_cache is None


def test_incremental_player_index_and_season_parquets_match_full_rebuild():
    import json
    import time
    from src.processing import build_player_index, process_season_data

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        raw_dir = root / "raw"
        matches_dir = raw_dir / "matches"
        proc_dir = root / "processed"
        matches_dir.mkdir(parents=True)
        proc_dir.mkdir(parents=True)

        fixture = [{
            "id": 8801,
            "status": "C",
            "kickoff": {"label": "Sat 10 Oct 2026, 15:00 BST", "millis": 1791644400000},
            "gameweek": {"gameweek": 1},
            "teams": [
                {"team": {"id": 1, "name": "Arsenal", "club": {"abbr": "ARS"}}, "score": 2},
                {"team": {"id": 4, "name": "Chelsea", "club": {"abbr": "CHE"}}, "score": 0},
            ],
        }]
        details = {
            "id": 8801,
            "teams": fixture[0]["teams"],
            "events": [{"type": "G", "personId": 101, "clock": {"label": "10'"}}],
            "teamLists": [
                {"teamId": 1, "lineup": [{"id": 101, "name": {"display": "Test Striker"}, "matchPosition": "F"}], "substitutes": []},
                {"teamId": 4, "lineup": [{"id": 202, "name": {"display": "Test Defender"}, "matchPosition": "D"}], "substitutes": []},
            ],
        }
        (raw_dir / "fixtures_2026_27.json").write_text(json.dumps(fixture), encoding="utf-8")
        (matches_dir / "8801_details.json").write_text(json.dumps(details), encoding="utf-8")
        (matches_dir / "8801_stats.json").write_text(json.dumps({"entity": {"id": 8801}, "data": {}}), encoding="utf-8")
        (matches_dir / "8801_stream.json").write_text(json.dumps({"events": {"content": []}}), encoding="utf-8")

        with (
            mock.patch.object(build_player_index, "RAW_DIR", raw_dir),
            mock.patch.object(build_player_index, "PROCESSED_DIR", proc_dir),
            mock.patch.object(build_player_index, "SEASONS", ["2026_27"]),
        ):
            build_player_index.parse_player_data(force=True)
            reg_full = (proc_dir / "players_registry.json").read_text(encoding="utf-8")
            logs_full = (proc_dir / "player_match_logs.json").read_text(encoding="utf-8")

            build_player_index.parse_player_data(force=False)
            assert (proc_dir / "players_registry.json").read_text(encoding="utf-8") == reg_full
            assert (proc_dir / "player_match_logs.json").read_text(encoding="utf-8") == logs_full

        with (
            mock.patch.object(process_season_data, "RAW_DIR", raw_dir),
            mock.patch.object(process_season_data, "PROCESSED_DIR", proc_dir),
        ):
            process_season_data.process_season("2026_27")
            m_pq = proc_dir / "matches_summary_2026_27.parquet"
            e_pq = proc_dir / "shots_events_2026_27.parquet"
            assert process_season_data._season_parquets_fresh("2026_27", raw_dir / "fixtures_2026_27.json", m_pq, e_pq)
            time.sleep(0.02)
            (matches_dir / "8801_stats.json").touch()
            assert not process_season_data._season_parquets_fresh("2026_27", raw_dir / "fixtures_2026_27.json", m_pq, e_pq)
