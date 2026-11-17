"""Serving of a configured TheStatsAPI league model against the local database and artifact (skipped when absent); audit page is Premier League only."""

import sqlite3

import pytest

from src.competitions.registry import CompetitionRegistry
from src.config import DB_PATH, competition_paths


def _configured_thestatsapi_league():
    for comp in CompetitionRegistry.list_all():
        if comp.provider == "thestatsapi" and comp.has_model:
            artifact = competition_paths(comp.key).models / "outcome_models_v1.joblib"
            if DB_PATH.exists() and artifact.exists():
                return comp, artifact
    return None, None


_COMP, ARTIFACT = _configured_thestatsapi_league()
needs_thestatsapi_league = pytest.mark.skipif(
    _COMP is None,
    reason="No configured TheStatsAPI domestic league data/model available locally",
)


def upcoming_match(competition_id: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            "SELECT match_id, home_id, away_id FROM matches WHERE competition_id = ? AND status != 'COMPLETED' ORDER BY match_date LIMIT 1",
            (competition_id,),
        ).fetchone()
    finally:
        conn.close()


@needs_thestatsapi_league
def test_upcoming_match_prediction_is_coherent_and_labelled():
    import joblib

    from src.api.league_prediction import COUNT_MODELS, compute_league_prediction
    from src.api.prediction_service import regression_model_skill

    match_id, home_id, away_id = upcoming_match(_COMP.id)
    result = compute_league_prediction(home_id, away_id, match_id, _COMP.key)
    outcome = result["outcome"]
    assert outcome["home_win_pct"] + outcome["draw_pct"] + outcome["away_win_pct"] == pytest.approx(100.0, abs=0.5)
    lines = result["goals"]["lines"]
    assert lines["1.5"]["over_pct"] >= lines["2.5"]["over_pct"] >= lines["3.5"]["over_pct"]
    assert result["model_skill"] in ("model", "baseline")
    assert result["shots"]["model_skill"] == "baseline"
    goals_artifact = joblib.load(ARTIFACT.with_name("goals_models_v1.joblib"))
    gates, rates = goals_artifact["skill_gate"], goals_artifact["base_rates"]
    lines = result["goals"]["lines"]
    for market, key in (("over_15", "1.5"), ("over_25", "2.5"), ("over_35", "3.5")):
        assert lines[key]["source"] == ("model" if gates[market] == "model" else "baseline"), market
        if gates[market] == "baseline":  # the base rate is served (a monotonic cap against a lower line can only lower it)
            assert lines[key]["over_pct"] <= round(rates[market] * 100.0, 1) + 0.06
    assert result["goals"]["btts_source"] == ("model" if gates["btts"] == "model" else "baseline")
    if gates["btts"] == "baseline":
        assert result["goals"]["btts_pct"] == pytest.approx(rates["btts"] * 100.0, abs=0.06)
    assert lines["1.5"]["over_pct"] >= lines["2.5"]["over_pct"] >= lines["3.5"]["over_pct"]
    assert lines["0.5"]["over_pct"] >= lines["1.5"]["over_pct"]
    for market, (filename, *_rest) in COUNT_MODELS.items():
        artifact = joblib.load(ARTIFACT.with_name(filename))
        assert result[market]["model_skill"] == regression_model_skill(artifact), market
        assert result[market]["expected_home"] + result[market]["expected_away"] == pytest.approx(result[market]["expected_total"], abs=0.2)
    assert result["referee"]["avg_cards"] > 0 and result["referee"]["avg_fouls"] > 0
    assert result["home_team"]["id"] == home_id and result["data_cutoff"]


@needs_thestatsapi_league
def test_prediction_of_the_served_choice_matches_the_artifact_decision():
    import joblib

    from src.api.league_prediction import compute_league_prediction

    match_id, home_id, away_id = upcoming_match(_COMP.id)
    artifact = joblib.load(ARTIFACT)
    result = compute_league_prediction(home_id, away_id, match_id, _COMP.key)
    assert result["model_skill"] == ("model" if artifact["decision"]["serving"] == "model" else "baseline")
    assert (result["model_note"] is None) == (artifact["decision"]["serving"] == "model")


def test_model_audit_is_premier_league_only():
    from src.api.routes.predict import get_model_audit

    payload = get_model_audit(season="2025_26", competition="champions_league")
    assert payload["model_available"] is False and payload["matches"] == [] and payload["competition_id"] == 2


@needs_thestatsapi_league
def test_the_report_keeps_the_locked_season_out_of_every_choice():
    import json

    from src.config import REPORTS_DIR

    report = json.loads((REPORTS_DIR / "models" / f"{_COMP.key}_walk_forward.json").read_text(encoding="utf-8"))
    protocol = report["protocol"]
    assert set(protocol["locked_monitoring"]).isdisjoint(protocol["outer_seasons"])
    assert report["folds"]["2026_27"]["locked_monitoring"] and report["decision"]["serving"] in ("model", "elo_baseline")
