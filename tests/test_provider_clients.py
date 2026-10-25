"""Tests for multi-provider ingestion client architecture and schema normalization."""

from __future__ import annotations

import pytest

from src.ingest.provider_factory import get_provider
from src.ingest.providers.api_football import ApiFootballProvider
from src.ingest.providers.pulselive import PulseLiveProvider
from src.ingest.providers.uefa import UefaProvider


def test_provider_factory_resolution():
    pl_prov = get_provider("premier_league")
    assert isinstance(pl_prov, PulseLiveProvider)
    assert pl_prov.competition_id == 39

    ucl_prov = get_provider("champions_league")
    assert isinstance(ucl_prov, UefaProvider)
    assert ucl_prov.competition_id == 2

    uel_prov = get_provider(3)
    assert isinstance(uel_prov, UefaProvider)
    assert uel_prov.competition_id == 3


def test_api_football_fixture_normalization():
    prov = ApiFootballProvider(competition_id=2, competition_key="champions_league")

    mock_raw_fixture = {
        "fixture": {
            "id": 12345,
            "referee": "S. Marciniak, Poland",
            "date": "2024-11-26T20:00:00+00:00",
            "venue": {"name": "Santiago Bernabeu"},
            "status": {"short": "FT"},
        },
        "league": {
            "id": 2,
            "season": 2024,
            "round": "League Stage - 5",
        },
        "teams": {
            "home": {"id": 541, "name": "Real Madrid", "code": "RMA"},
            "away": {"id": 50, "name": "Manchester City", "code": "MCI"},
        },
        "goals": {
            "home": 2,
            "away": 1,
        },
    }

    norm = prov.normalize_fixture_record(mock_raw_fixture)

    assert norm["match_id"] == 12345
    assert norm["competition_id"] == 2
    assert norm["season"] == "2024"
    assert norm["gameweek"] == 5
    assert norm["home_name"] == "Real Madrid"
    assert norm["away_name"] == "Manchester City"
    assert norm["home_score"] == 2.0
    assert norm["away_score"] == 1.0
    assert norm["status"] == "COMPLETED"
    assert norm["referee_name"] == "S. Marciniak"
    assert norm["ground_name"] == "Santiago Bernabeu"


def test_api_football_stats_normalization():
    prov = ApiFootballProvider(competition_id=2, competition_key="champions_league")

    mock_raw_stats = {
        "teams": [
            {
                "team": {"id": 541, "name": "Real Madrid"},
                "statistics": [
                    {"type": "Shots on Goal", "value": 6},
                    {"type": "Total Shots", "value": 15},
                    {"type": "Corner Kicks", "value": 7},
                    {"type": "Fouls", "value": 9},
                    {"type": "Ball Possession", "value": "52%"},
                    {"type": "Yellow Cards", "value": 2},
                    {"type": "Red Cards", "value": 0},
                    {"type": "Goalkeeper Saves", "value": 4},
                    {"type": "expected_goals", "value": "1.85"},
                ],
            },
            {
                "team": {"id": 50, "name": "Manchester City"},
                "statistics": [
                    {"type": "Shots on Goal", "value": 5},
                    {"type": "Total Shots", "value": 12},
                    {"type": "Corner Kicks", "value": 4},
                    {"type": "Fouls", "value": 11},
                    {"type": "Ball Possession", "value": "48%"},
                    {"type": "Yellow Cards", "value": 1},
                    {"type": "Red Cards", "value": 0},
                    {"type": "Goalkeeper Saves", "value": 4},
                    {"type": "expected_goals", "value": "1.42"},
                ],
            },
        ]
    }

    stats = prov.normalize_stats_record(mock_raw_stats)

    assert stats["home_won_corners"] == 7.0
    assert stats["away_won_corners"] == 4.0
    assert stats["total_corners"] == 11.0
    assert stats["total_shots"] == 27.0
    assert stats["total_shots_ontarget"] == 11.0
    assert stats["total_saves"] == 8.0
    assert stats["total_yellow_cards"] == 3.0
    assert stats["total_cards"] == 3.0
    assert stats["home_xg"] == pytest.approx(1.85)
    assert stats["away_xg"] == pytest.approx(1.42)
    assert stats["total_xg"] == pytest.approx(3.27)


def _uefa_fixture(round_type="GROUP_STANDINGS", status="FINISHED", with_score=True):
    team = lambda i, n, c: {"id": str(i), "internationalName": n, "teamCode": c, "mediumLogoUrl": f"https://img.uefa.com/{i}.png"}
    fixture = {
        "id": "2049001",
        "status": status,
        "seasonYear": "2027",
        "round": {"metaData": {"type": round_type}},
        "matchday": {"name": "MD3", "sequenceNumber": "3"},
        "kickOffTime": {"dateTime": "2026-10-21T19:00:00Z"},
        "homeTeam": team(52280, "Arsenal", "ARS"),
        "awayTeam": team(50138, "Inter", "INT"),
        "stadium": {"translations": {"mediaName": {"EN": "Emirates Stadium"}}},
        "referees": [{"role": "REFEREE", "person": {"translations": {"name": {"EN": "Daniele Chiffi"}}}}],
    }
    if with_score:
        fixture["score"] = {"total": {"home": 2, "away": 1}}
    return fixture


def test_uefa_fixture_normalization():
    prov = get_provider("champions_league")
    row = prov.normalize_fixture_record(_uefa_fixture())

    assert row["match_id"] == 2049001
    assert row["season"] == "2026_27"
    assert row["gameweek"] == 3 and row["stage"] == "league"
    assert row["status"] == "COMPLETED" and row["home_score"] == 2.0 and row["away_score"] == 1.0
    assert row["day_label"] == "Wed 21 Oct 2026" and row["time_label"] == "20:00 BST"
    assert row["ground_name"] == "Emirates Stadium" and row["referee_name"] == "Daniele Chiffi"
    assert row["home_logo"].endswith("52280.png")


def test_uefa_upcoming_has_no_score_and_qualifiers_are_skipped():
    prov = get_provider("europa_league")
    upcoming = prov.normalize_fixture_record(_uefa_fixture(status="UPCOMING", with_score=False))
    assert upcoming["status"] == "UPCOMING" and upcoming["home_score"] is None

    assert prov.normalize_fixture_record(_uefa_fixture(round_type="SECOND_QUALIFYING")) is None
    assert prov.normalize_fixture_record(_uefa_fixture(round_type="PLAY_OFF")) is None


def _group_fixture(group_count, group_name="Group C", round_type="GROUP_STANDINGS"):
    fixture = _uefa_fixture(round_type=round_type)
    fixture["round"] = {"metaData": {"type": round_type}, "groupCount": group_count}
    fixture["group"] = {"metaData": {"groupName": group_name}}
    fixture["matchday"] = {"name": "MD4", "sequenceNumber": "4"}
    fixture["winner"] = {"match": {"reason": "WIN_REGULAR", "team": {"id": "52280"}}}
    return fixture


def test_classic_group_stage_keeps_the_group_and_has_no_advancing_team():
    prov = get_provider("champions_league")
    row = prov.normalize_fixture_record(_group_fixture(group_count=8))

    assert row["stage"] == "group" and row["group_name"] == "C" and row["gameweek"] == 4
    assert row["advancing_team_id"] is None  # a group match winner is not a tie winner


def test_single_league_phase_is_not_treated_as_groups():
    prov = get_provider("champions_league")
    row = prov.normalize_fixture_record(_group_fixture(group_count=1, group_name="League"))
    assert row["stage"] == "league" and row["group_name"] is None
