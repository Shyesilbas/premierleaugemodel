"""Smoke tests for the read-only API routes against the local data lake and models."""

import pytest
from fastapi.testclient import TestClient

from src.api.server import app

pytestmark = pytest.mark.needs_data


@pytest.fixture(scope="module")
def client():
    return TestClient(app)  # loads datasets and models once (~30 s)


@pytest.mark.parametrize("route, keys", [
    ("/api/data-version", {"version"}),
    ("/api/teams", {"teams", "count"}),
    ("/api/standings", {"season", "total_teams", "standings"}),
    ("/api/fixtures/grouped", {"season", "gameweeks", "total_matches"}),
    ("/api/referees", {"referees"}),
    ("/api/benchmarks", {"corner", "outcome"}),
])
def test_read_routes_answer_with_their_documented_keys(client, route, keys):
    response = client.get(route)
    assert response.status_code == 200
    assert keys <= set(response.json())


def test_predict_returns_consistent_goal_markets_and_withholds_the_btts_label(client):
    teams = client.get("/api/teams").json()["teams"]
    ids = [team.get("id", team.get("team_id")) for team in teams[:2]]
    response = client.get("/api/predict", params={"home_id": ids[0], "away_id": ids[1]})
    assert response.status_code == 200
    goals = response.json()["goals"]
    over = [goals[f"over_{line}"]["pct"] for line in ("1.5", "2.5", "3.5")]
    assert all(0.0 <= p <= 100.0 for p in over) and over[0] >= over[1] >= over[2]
    assert isinstance(goals["btts_informative"], bool)
    if not goals["btts_informative"]:
        assert goals["btts_prediction"] is None  # no label while the BTTS gate fails
    assert 0.0 <= goals["btts_pct"] <= 100.0


def test_predict_rejects_a_team_against_itself(client):
    assert client.get("/api/predict", params={"home_id": 1, "away_id": 1}).status_code == 400
