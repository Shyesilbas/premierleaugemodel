import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import mock

from src.ingest import import_thestatsapi_odds as odds
from src.ingest import import_thestatsapi_xg as xg

SEASONS = {"data": [{"id": "s1", "name": "2026/27", "start_year": 2026, "end_year": 2027}]}


def _api_match(pid, matchday, home, away):
    return {"id": pid, "matchday": matchday, "status": "finished", "xg_available": True, "odds_available": True,
            "home_team": {"name": home}, "away_team": {"name": away}, "score": {"home": 1, "away": 0}}


API_MATCHES = [_api_match("m1", 1, "Arsenal", "Chelsea"), _api_match("m2", 8, "Liverpool", "Everton"),
               _api_match("m3", 8, "Tottenham Hotspur", "Fulham")]
LOCAL = [(1, "Arsenal", "Chelsea", 1), (2, "Liverpool", "Everton", 8), (3, "Tottenham Hotspur", "Fulham", 8)]
XG = {"data": {"overview": {"expected_goals": {"all": {"home": 1.2, "away": 0.8}}}}}
NO_XG = {"data": {"overview": {"expected_goals": None}}}
ODDS = {"data": {"bookmakers": [{"bookmaker": "Bet365", "markets": {"match_odds": {
    "home": {"opening": 2.0, "last_seen": 1.9}, "draw": {"opening": 3.4, "last_seen": 3.5},
    "away": {"opening": 3.8, "last_seen": 4.0}}}}]}}


class FakeClient:
    """Stands in for TheStatsApiClient and records every path it was asked for."""

    calls: list[str] = []
    stats_404 = False

    def __init__(self, *_, **__):
        pass

    def get_json(self, path, params=None):
        FakeClient.calls.append(path)
        if path.endswith("/seasons"):
            return SEASONS
        if path == "/football/matches":
            return {"data": API_MATCHES, "meta": {"total_pages": 1}}
        if path.endswith("/stats"):
            if "m2" in path and FakeClient.stats_404:
                raise RuntimeError("TheStatsAPI returned HTTP 404 for " + path)
            return NO_XG if "m3" in path else XG
        if path.endswith("/odds"):
            return ODDS
        raise AssertionError(path)


def _db(tmp: str) -> Path:
    path = Path(tmp) / "db.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE matches (match_id INTEGER, season TEXT, gameweek INTEGER, match_date TEXT, "
                     "home_name TEXT, away_name TEXT, home_score REAL, away_score REAL)")
        conn.executemany("INSERT INTO matches VALUES (?, '2026_27', ?, '', ?, ?, 1, 0)", [(i, g, h, a) for i, h, a, g in LOCAL])
    return path


def _xg_args(max_gameweek):
    return argparse.Namespace(season="2026_27", max_gameweek=max_gameweek, limit=None,
                              competition_id="comp_3039", minimum_interval=0)


def _run_xg(max_gameweek):
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(xg, "DB_PATH", _db(tmp)), \
         mock.patch.object(xg, "TheStatsApiClient", FakeClient), mock.patch.dict("os.environ", {"THESTATSAPI_API_KEY": "k"}):
        return xg.import_season(_xg_args(max_gameweek))


def test_xg_import_has_no_gameweek_cap_by_default():
    counts = _run_xg(None)
    assert counts["eligible"] == 3 and counts["imported"] == 2 and counts["stats_missing_xg"] == 1


def test_xg_gameweek_cap_is_still_honoured_when_given():
    counts = _run_xg(6)
    assert counts["eligible"] == 1 and counts["imported"] == 1


def test_xg_main_exits_nonzero_when_the_provider_flags_xg_it_does_not_send():
    with mock.patch.object(xg, "import_season", return_value={"stats_missing_xg": 1, "unmatched": 0}), \
         mock.patch.object(sys, "argv", ["x"]):
        try:
            xg.main()
        except SystemExit as exit_:
            assert exit_.code == 1
        else:
            raise AssertionError("expected SystemExit(1)")


def _run_odds(refresh):
    FakeClient.calls = []
    with tempfile.TemporaryDirectory() as tmp:
        db = _db(tmp)
        with mock.patch.object(odds, "DB_PATH", db), mock.patch.object(odds, "TheStatsApiClient", FakeClient):
            conn = sqlite3.connect(db)
            odds.init_odds_table(conn)
            conn.execute("INSERT INTO external_match_odds (match_id, provider, provider_match_id, provider_season_id, "
                         "bookmaker, fetched_at_utc) VALUES (1, 'TheStatsAPI', 'm1', 's1', 'Bet365', 'x')")
            conn.commit()
            conn.close()
            stats = odds.import_odds("k", season="2026_27", minimum_interval=0, refresh=refresh)
    return stats, [c for c in FakeClient.calls if c.endswith("/odds")]


def test_odds_import_skips_matches_already_stored():
    stats, odds_calls = _run_odds(refresh=False)
    assert stats["skipped_existing"] == 1 and stats["total_targets"] == 2
    assert not any("/m1/" in call for call in odds_calls) and len(odds_calls) == 2


def test_odds_refresh_fetches_stored_matches_again():
    stats, odds_calls = _run_odds(refresh=True)
    assert stats["skipped_existing"] == 0 and len(odds_calls) == 3


def test_xg_import_survives_a_404_and_counts_it_separately_from_missing_xg():
    FakeClient.stats_404 = True
    try:
        counts = _run_xg(None)
    finally:
        FakeClient.stats_404 = False
    assert counts["imported"] == 1 and counts["stats_not_published"] == 1 and counts["stats_missing_xg"] == 1  # m1 stored; m2 404; m3 null xG
