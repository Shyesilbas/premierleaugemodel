"""Serving and audit of the LaLiga model against the real local database and artifact (skipped on a fresh clone)."""

import sqlite3

import pytest

from src.config import DB_PATH, competition_paths

ARTIFACT = competition_paths("la_liga").models / "outcome_models_v1.joblib"
needs_laliga = pytest.mark.skipif(not (DB_PATH.exists() and ARTIFACT.exists()), reason="LaLiga data or model not available locally")


def upcoming_match():
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute("SELECT match_id, home_id, away_id FROM matches WHERE competition_id = 140 AND status != 'COMPLETED' ORDER BY match_date LIMIT 1").fetchone()
    finally:
        conn.close()


@needs_laliga
def test_upcoming_match_prediction_is_coherent_and_labelled():
    import joblib

    from src.api.league_prediction import COUNT_MODELS, compute_league_prediction
    from src.api.prediction_service import regression_model_skill

    match_id, home_id, away_id = upcoming_match()
    result = compute_league_prediction(home_id, away_id, match_id, "la_liga")
    outcome = result["outcome"]
    assert outcome["home_win_pct"] + outcome["draw_pct"] + outcome["away_win_pct"] == pytest.approx(100.0, abs=0.5)
    lines = result["goals"]["lines"]
    assert lines["1.5"]["over_pct"] >= lines["2.5"]["over_pct"] >= lines["3.5"]["over_pct"]
    assert result["model_skill"] in ("model", "baseline")
    assert result["shots"]["model_skill"] == "baseline"
    for market, (filename, *_rest) in COUNT_MODELS.items():
        artifact = joblib.load(ARTIFACT.with_name(filename))
        assert result[market]["model_skill"] == regression_model_skill(artifact), market
        assert result[market]["expected_home"] + result[market]["expected_away"] == pytest.approx(result[market]["expected_total"], abs=0.2)
    assert result["referee"]["avg_cards"] > 0 and result["referee"]["avg_fouls"] > 0
    assert result["home_team"]["id"] == home_id and result["data_cutoff"]


@needs_laliga
def test_prediction_of_the_served_choice_matches_the_artifact_decision():
    import joblib

    from src.api.league_prediction import compute_league_prediction

    match_id, home_id, away_id = upcoming_match()
    artifact = joblib.load(ARTIFACT)
    result = compute_league_prediction(home_id, away_id, match_id, "la_liga")
    assert result["model_skill"] == ("model" if artifact["decision"]["serving"] == "model" else "baseline")
    assert (result["model_note"] is None) == (artifact["decision"]["serving"] == "model")


@needs_laliga
def test_audit_rows_are_out_of_sample_and_internally_consistent():
    from src.analytics.league_audit import build_league_audit

    payload = build_league_audit("la_liga", "2025_26")
    assert payload["method"] == "walk_forward" and payload["overall"]["evaluation_scope"] == "walk_forward_backtest"
    rows = payload["matches"]
    assert len(rows) == 380 and all(r["evaluation_type"] == "walk_forward" for r in rows)
    assert sum(r["hit_1x2"] for r in rows) == payload["overall"]["hits_1x2"]
    for row in rows[:20]:
        assert row["prob_home"] + row["prob_draw"] + row["prob_away"] == pytest.approx(100.0, abs=0.3)
        assert row["predicted_winner"] in ("home", "draw", "away") and row["actual_result"] in ("home", "draw", "away")
    assert payload["benchmark"]["role"] == "hold_out" and {"model", "base_rate", "elo"} <= set(payload["benchmark"]["scores"])


@needs_laliga
def test_the_report_keeps_the_locked_season_out_of_every_choice():
    import json

    from src.config import REPORTS_DIR

    report = json.loads((REPORTS_DIR / "models" / "la_liga_walk_forward.json").read_text(encoding="utf-8"))
    protocol = report["protocol"]
    assert set(protocol["locked_monitoring"]).isdisjoint(protocol["outer_seasons"])
    assert report["folds"]["2026_27"]["locked_monitoring"] and report["decision"]["serving"] in ("model", "elo_baseline")
