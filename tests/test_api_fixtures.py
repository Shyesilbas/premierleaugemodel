from unittest import mock

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api import state
from src.api.server import app

client = TestClient(app)


def _matches():
    return pd.DataFrame({
        "match_id": [1, 2, 3], "season": ["2026_27", "2026_27", "2025_26"],
        "home_name": ["Arsenal", "Chelsea", "Spurs"], "away_name": ["Fulham", "Everton", "Wolves"],
        "ground_name": ["Emirates", "Stamford Bridge", "N17"],
        "home_score": [2.0, np.nan, 1.0],                       # an unplayed match carries NaN
        "match_date": pd.to_datetime(["2026-08-01", "2026-08-08", pd.NaT]),  # and a missing date is NaT
    })


def test_fixtures_route_serialises_missing_values_instead_of_failing():
    """Regression: GET /api/fixtures returned 500 because NaN is not valid JSON."""
    with mock.patch.object(state, "df_matches", _matches()):
        response = client.get("/api/fixtures")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    by_id = {row["match_id"]: row for row in body["fixtures"]}
    assert by_id[2]["home_score"] is None and by_id[1]["home_score"] == 2.0
    assert by_id[3]["match_date"] is None and by_id[1]["match_date"].startswith("2026-08-01")


def test_fixtures_route_filters_by_season_and_search_and_honours_the_limit():
    with mock.patch.object(state, "df_matches", _matches()):
        in_season = client.get("/api/fixtures", params={"season": "2026_27"}).json()
        searched = client.get("/api/fixtures", params={"search": "spurs"}).json()
        limited = client.get("/api/fixtures", params={"limit": 1}).json()
    assert {row["match_id"] for row in in_season["fixtures"]} == {1, 2}
    assert [row["match_id"] for row in searched["fixtures"]] == [3]
    assert limited["total"] == 1
