"""National leagues fed only by TheStatsAPI: id mapping, fixture rows and the match timeline."""

from src.api.statsapi_match_details import build_lineups, build_statsapi_match_details, build_timeline
from src.competitions.registry import get_competition
from src.ingest.providers.thestatsapi_league import (
    MATCH_ID_OFFSET,
    TEAM_ID_OFFSET,
    TheStatsApiLeagueProvider,
    abbreviation,
    local_match_id,
    local_team_id,
    provider_match_id,
    season_label,
)

HOME, AWAY = 10000001, 10000002
MATCH = {
    "match_id": 100000001, "home_id": HOME, "away_id": AWAY, "home_name": "Alpha", "away_name": "Beta", "home_score": 2, "away_score": 1,
    "kickoff_label": "Sun 25 Oct 2026, 15:15 GMT", "ground_name": "Estadio", "referee_name": "R. Ref", "status": "COMPLETED",
}


def fixture(**changes):
    base = {
        "id": "mt_733716933", "status": "finished", "matchday": 10, "utc_date": "2026-10-25T15:15:00.000Z", "_season": "2026_27",
        "home_team": {"id": "tm_20116", "name": "Celta Vigo"}, "away_team": {"id": "tm_64056", "name": "Real Betis"},
        "score": {"home": 0, "away": 0, "regulation": {"home": 0, "away": 0}},
    }
    return {**base, **changes}


def test_provider_ids_are_shifted_out_of_the_other_feeds_ranges():
    assert local_match_id("mt_733716933") == MATCH_ID_OFFSET + 733716933
    assert local_team_id("tm_20116") == TEAM_ID_OFFSET + 20116
    assert provider_match_id(local_match_id("mt_000000042")) == "mt_000000042"
    assert MATCH_ID_OFFSET > 2_050_200 > 129_302  # above the highest Premier League and UEFA match ids seen


def test_fixture_row_is_canonical_and_uses_london_time():
    provider = TheStatsApiLeagueProvider(140, "la_liga")
    row = provider.normalize_fixture_record(fixture())
    assert row["competition_id"] == 140 and row["stage"] == "league" and row["gameweek"] == 10
    assert row["status"] == "COMPLETED" and row["home_score"] == 0.0 and row["away_score"] == 0.0
    assert row["time_label"] == "15:15 GMT" and row["match_date"] == "2026-10-25" and row["season"] == "2026_27"
    assert (row["home_abbr"], row["away_abbr"]) == ("CEL", "BET")


def test_unplayed_and_cancelled_fixtures():
    provider = TheStatsApiLeagueProvider(140, "la_liga")
    scheduled = provider.normalize_fixture_record(fixture(status="scheduled", score={"home": None, "away": None, "regulation": None}))
    assert scheduled["status"] == "UPCOMING" and scheduled["home_score"] is None
    assert provider.normalize_fixture_record(fixture(status="cancelled")) is None


def test_abbreviations_and_season_labels():
    assert abbreviation("Atlético Madrid") == "ATM" and abbreviation("Real Madrid") == "RMA"
    assert abbreviation("Unknown FC") == "UNK"
    assert season_label("22/23") == "2022_23"


def test_registry_describes_la_liga_as_a_domestic_league_with_its_own_model():
    comp = get_competition("la_liga")
    assert comp.id == 140 and comp.is_domestic and comp.has_model and comp.provider == "thestatsapi"
    assert [z["key"] for z in comp.zones] == ["champions_league", "europa_league", "relegation"]
    assert get_competition("premier_league").has_model


def lineup_payload():
    def side(prefix, names):
        return {"formation": "4-4-2", "starting_xi": [{"id": f"pl_{prefix}{i}", "name": n, "position": "M", "jersey_number": i} for i, n in enumerate(names, 1)],
                "substitutes": [{"id": f"pl_{prefix}99", "name": "Sub", "position": "F", "jersey_number": 99}]}
    return {"data": {"home": side(1, ["A", "B"]), "away": side(2, ["C", "D"])}}


def test_timeline_credits_goals_pairs_substitutions_and_counts_the_score():
    lineups = build_lineups(lineup_payload(), MATCH)
    team = lambda tid: {"id": f"tm_{tid - TEAM_ID_OFFSET}", "name": "x"}
    events = [
        {"sequence": 1, "minute": 10, "extra_time": 0, "type": "goal", "team": team(HOME), "player": {"id": "pl_11", "name": "A"}},
        {"sequence": 2, "minute": 30, "extra_time": 0, "type": "penalty_scored", "team": team(AWAY), "player": {"id": "pl_21", "name": "C"}},
        {"sequence": 3, "minute": 55, "extra_time": 0, "type": "own_goal", "team": team(AWAY), "player": {"id": "pl_22", "name": "D"}},
        {"sequence": 4, "minute": 60, "extra_time": 0, "type": "substitution", "team": team(HOME), "player": {"id": "pl_12", "name": "B"}},
        {"sequence": 5, "minute": 60, "extra_time": 0, "type": "substitution", "team": team(HOME), "player": {"id": "pl_199", "name": "Sub"}},
        {"sequence": 6, "minute": 75, "extra_time": 0, "type": "yellow_card", "team": team(AWAY), "player": {"id": "pl_21", "name": "C"}},
        {"sequence": 7, "minute": 90, "extra_time": 3, "type": "added_time", "team": None, "player": None},
    ]
    timeline = build_timeline({"data": {"events": events}}, lineups, MATCH)
    kinds = [item["type"] for item in timeline]
    assert kinds == ["goal", "goal", "goal", "substitution", "yellow_card", "added_time"]
    goals = [item for item in timeline if item["type"] == "goal"]
    assert [g["score"] for g in goals] == ["1 - 0", "1 - 1", "2 - 1"]  # an own goal counts for the other side
    assert goals[2]["team_id"] == HOME and goals[2]["is_own_goal"] and goals[1]["is_penalty"]
    swap = next(item for item in timeline if item["type"] == "substitution")
    assert (swap["player_out_name"], swap["player_in_name"]) == ("B", "Sub")


def test_match_detail_without_payloads_still_has_the_page_structure():
    result = build_statsapi_match_details(MATCH, {}, [])
    assert result["lineups"] == [] and result["timeline"] == []
    assert result["metadata"]["referee"] == "R. Ref" and result["metadata"]["ground"] == "Estadio"


def test_update_button_runs_the_pipeline_of_the_selected_competition():
    from src.api.routes.meta import _sync_command

    league = _sync_command("matches", "2026_27", "la_liga")
    assert league[1:] == ["-m", "src.ingest.sync_competition", "--competition", "la_liga", "--season", "2026_27"]
    cup = _sync_command("matches", "2025_26", "champions_league")
    assert "src.ingest.sync_competition" in cup and "champions_league" in cup
    premier = _sync_command("referees", "2026_27")
    assert premier[-1] == "--referees-only" and premier[1].endswith("sync_season_data.py")
    assert get_competition("premier_league").sync_kinds == ("matches", "referees", "lineups")
    assert get_competition("la_liga").sync_kinds == ("matches",)


def test_a_competition_cannot_be_synced_twice_at_once():
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace
    from unittest import mock

    import pytest

    from src.ingest import raw_store

    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(raw_store, "competition_paths", lambda key: SimpleNamespace(raw=Path(tmp) / key)):
            with raw_store.competition_lock("la_liga"):
                with pytest.raises(raw_store.CompetitionSyncRunning):
                    with raw_store.competition_lock("la_liga"):
                        pass
                with raw_store.competition_lock("europa_league"):  # another competition is not blocked
                    pass
            with raw_store.competition_lock("la_liga"):  # released afterwards
                pass


def _provider_fixture(number, home, away, status="scheduled", day="2026-11-01T15:00:00.000Z", matchday=1):
    return {"id": f"mt_{number:09d}", "status": status, "matchday": matchday, "utc_date": day, "_season": "2026_27",
            "home_team": {"id": f"tm_{home[0]}", "name": home[1]}, "away_team": {"id": f"tm_{away[0]}", "name": away[1]},
            "score": {"home": None, "away": None, "regulation": None}}


def test_calendar_fills_the_weeks_the_provider_has_not_published():
    from zoneinfo import ZoneInfo

    from src.ingest.providers.thestatsapi_league import SCHEDULE_ID_OFFSET, missing_fixtures

    barca, espanyol = (1, "Barcelona"), (2, "Espanyol")
    published = [_provider_fixture(7, barca, espanyol, status="finished")]
    calendar = {"matches": [
        {"round": "Matchday 1", "date": "2026-08-15", "team1": "FC Barcelona", "team2": "RCD Espanyol de Barcelona"},  # already published
        {"round": "Matchday 20", "date": "2027-01-10", "time": "21:00", "team1": "RCD Espanyol de Barcelona", "team2": "FC Barcelona"},
        {"round": "Matchday 21", "date": "2027-01-17", "team1": "FC Barcelona", "team2": "RCD Espanyol de Barcelona"},  # same pair listed above
    ]}
    placeholders = missing_fixtures("2026_27", published, calendar, ZoneInfo("Europe/Madrid"))
    assert len(placeholders) == 1  # the published pair wins; "Espanyol de Barcelona" does not take "Barcelona"
    held = placeholders[0]
    assert held["home_team"]["name"] == "Espanyol" and held["away_team"]["name"] == "Barcelona" and held["matchday"] == 20
    assert held["utc_date"] == "2027-01-10T20:00:00.000Z" and not held["_time_unknown"]  # 21:00 in Madrid in winter
    assert held["_local_id"] >= SCHEDULE_ID_OFFSET and held["status"] == "scheduled"
    again = missing_fixtures("2026_27", published, calendar, ZoneInfo("Europe/Madrid"))
    assert again[0]["_local_id"] == held["_local_id"]  # stable, so a rerun updates the same row


def test_a_postponed_match_stays_on_the_calendar_and_unknown_clubs_skip_it():
    from zoneinfo import ZoneInfo

    from src.ingest.providers.thestatsapi_league import missing_fixtures

    cancelled = [_provider_fixture(1, (1, "Barcelona"), (2, "Espanyol"), status="cancelled")]
    calendar = {"matches": [{"round": "Matchday 8", "date": "2026-10-10", "team1": "FC Barcelona", "team2": "RCD Espanyol de Barcelona"}]}
    assert len(missing_fixtures("2026_27", cancelled, calendar, ZoneInfo("Europe/Madrid"))) == 1
    stranger = {"matches": [{"round": "Matchday 8", "date": "2026-10-10", "team1": "FC Barcelona", "team2": "Brand New Club"}]}
    assert missing_fixtures("2026_27", cancelled, stranger, ZoneInfo("Europe/Madrid")) == []


def test_calendar_placeholder_becomes_an_upcoming_row_without_a_clock_time():
    provider = TheStatsApiLeagueProvider(140, "la_liga")
    row = provider.normalize_fixture_record({
        "id": "schedule_2026_27_20_1_2", "_schedule_only": True, "_local_id": 300000123, "_season": "2026_27", "_time_unknown": True,
        "status": "scheduled", "matchday": 20, "utc_date": "2027-01-17T00:00:00.000Z",
        "home_team": {"id": "tm_1", "name": "Barcelona"}, "away_team": {"id": "tm_2", "name": "Espanyol"}, "score": {"home": None, "away": None},
    })
    assert row["match_id"] == 300000123 and row["status"] == "UPCOMING" and row["time_label"] == ""
    assert row["kickoff_label"] == row["day_label"] and row["gameweek"] == 20
