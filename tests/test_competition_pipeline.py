"""Integration test verifying multi-competition data processing and isolation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.server import app
from src.db.database import get_db
from src.processing.process_competition_data import process_competition_season


def _match_counts():
    conn = get_db()
    try:
        return dict(conn.execute("SELECT competition_id, COUNT(*) FROM matches GROUP BY competition_id").fetchall())
    finally:
        conn.close()


def test_process_competition_without_raw_data_leaves_db_untouched():
    before = _match_counts()

    df_matches, df_events = process_competition_season("champions_league", "2099_00")

    assert df_matches.empty and df_events.empty
    assert _match_counts() == before
    assert before.get(39, 0) > 1000


def test_api_grouped_fixtures_competition_isolation():
    client = TestClient(app)

    resp_pl = client.get("/api/fixtures/grouped?season=2026_27")
    assert resp_pl.status_code == 200
    data_pl = resp_pl.json()
    assert data_pl["competition"]["key"] == "premier_league"
    assert data_pl["total_matches"] == 380

    resp_ucl = client.get("/api/fixtures/grouped?competition=champions_league&season=2026_27")
    assert resp_ucl.status_code == 200
    data_ucl = resp_ucl.json()
    assert data_ucl["competition"]["key"] == "champions_league"
    assert data_ucl["total_matches"] > 0
    first = data_ucl["gameweeks"][0]["days"][0]["matches"][0]
    assert first["home_logo"].startswith("https://img.uefa.com/")

    pl_ids = {m["match_id"] for gw in data_pl["gameweeks"] for d in gw["days"] for m in d["matches"]}
    ucl_ids = {m["match_id"] for gw in data_ucl["gameweeks"] for d in gw["days"] for m in d["matches"]}
    assert not pl_ids & ucl_ids


def test_team_profile_is_scoped_to_the_selected_competition():
    client = TestClient(app)

    # Arsenal's Premier League id must not resolve inside the Champions League.
    assert client.get("/api/teams/profile?team_id=1&season=2026_27&competition=champions_league").status_code == 404

    ucl = client.get("/api/teams/profile?team_id=52280&season=2026_27&competition=champions_league").json()
    assert ucl["team"]["name"] == "Arsenal"
    assert all(p["id"] != 1 for p in ucl["squad"])  # squad, when synced, holds UEFA-provider players only
    assert ucl["matches"] and all(m["match_id"] > 2_000_000 for m in ucl["matches"])

    pl = client.get("/api/teams/profile?team_id=1&season=2026_27").json()
    # The Premier League page lists European matches too, but its league matches never come from the UEFA profile.
    pl_only = {m["match_id"] for m in pl["matches"] if m["competition"]["key"] == "premier_league"}
    assert pl_only.isdisjoint({m["match_id"] for m in ucl["matches"]})
    assert {m["match_id"] for m in ucl["matches"]} <= {m["match_id"] for m in pl["matches"]}


def test_group_stage_seasons_have_per_group_standings_and_zones():
    client = TestClient(app)
    table = client.get("/api/standings?competition=champions_league&season=2023_24").json()

    assert table["format"] == "groups" and table["groups"] == list("ABCDEFGH")
    group_a = [row for row in table["standings"] if row["group"] == "A"]
    assert [row["rank"] for row in group_a] == [1, 2, 3, 4]
    assert [row["zone"] for row in group_a] == ["direct_r16", "direct_r16", "playoff", "eliminated"]

    league = client.get("/api/standings?competition=europa_league&season=2025_26").json()
    assert league["format"] == "league" and league["standings"][0]["zone"] == "direct_r16"
    assert league["standings"][-1]["zone"] == "eliminated"  # not the Premier League relegation zone
