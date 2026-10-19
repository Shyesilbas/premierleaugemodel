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


def test_reload_rebinds_the_shared_state_and_routes_follow_it(client):
    """Routes read ``state.<name>``; a reload rebinds those names, so a stale reference would keep old data."""
    from src.api import state

    teams = client.get("/api/teams").json()["teams"]
    params = {"home_id": teams[0].get("id", teams[0].get("team_id")), "away_id": teams[1].get("id", teams[1].get("team_id"))}
    before = client.get("/api/predict", params=params).json()
    old_features, old_matches = state.df_features, state.df_matches

    assert client.post("/api/admin/reload-models").status_code == 200  # reloads artifacts
    state.reload_runtime_datasets()                                     # reloads and rebinds the dataframes

    assert state.df_features is not old_features and state.df_matches is not old_matches
    assert client.get("/api/predict", params=params).json() == before   # same data, read through the new objects
    assert client.get("/api/data-version").json()["version"] == str(state._loaded_data_version)


def test_admin_routes_need_the_token_when_one_is_configured(client):
    import os
    from unittest import mock

    with mock.patch.dict(os.environ, {"PLM_ADMIN_TOKEN": "t0ken"}):
        assert client.get("/api/admin/sync-season").status_code == 401
        assert client.post("/api/admin/reload-models").status_code == 401  # rejected before any reload starts
        assert client.post("/api/admin/sync-season", headers={"X-Admin-Token": "nope"}).status_code == 401
        assert client.get("/api/admin/sync-season", headers={"X-Admin-Token": "t0ken"}).status_code == 200
    assert client.get("/api/data-version").status_code == 200  # ordinary routes never need the token


def test_cors_allows_the_local_frontend_only(client):
    ask = lambda origin: client.options(
        "/api/data-version", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert ask("http://localhost:5173").headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in ask("https://evil.example").headers
