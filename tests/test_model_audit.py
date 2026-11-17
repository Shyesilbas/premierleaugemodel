"""Tests for enriched model audit metrics, calibration bands, and benchmark verdicts."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.analytics import model_audit


def test_calibration_bands_and_rolling_accuracy():
    played = [
        {"match_id": 1, "gameweek": 1, "match_date": "2026-08-15", "prob_home": 72.0, "prob_draw": 18.0, "prob_away": 10.0, "actual_result": "home", "hit_1x2": True},
        {"match_id": 2, "gameweek": 1, "match_date": "2026-08-16", "prob_home": 55.0, "prob_draw": 25.0, "prob_away": 20.0, "actual_result": "away", "hit_1x2": False},
        {"match_id": 3, "gameweek": 2, "match_date": "2026-08-22", "prob_home": 38.0, "prob_draw": 32.0, "prob_away": 30.0, "actual_result": "draw", "hit_1x2": False},
        {"match_id": 4, "gameweek": 2, "match_date": "2026-08-23", "prob_home": 62.0, "prob_draw": 22.0, "prob_away": 16.0, "actual_result": "home", "hit_1x2": True},
        {"match_id": 5, "gameweek": 3, "match_date": "2026-08-29", "prob_home": 74.0, "prob_draw": 16.0, "prob_away": 10.0, "actual_result": "home", "hit_1x2": True},
    ]
    bands = model_audit._compute_calibration_bands(played)
    assert [b["label"] for b in bands] == ["<%40", "%50-60", "%60-70", "%70+"]
    assert bands[-1]["count"] == 2
    assert bands[-1]["actual_accuracy"] == 100.0

    rolling = model_audit._compute_rolling_accuracy(played, window=3)
    assert len(rolling) == 1
    assert rolling[0]["index"] == 5
    assert rolling[0]["cumulative_acc"] == 60.0
    assert rolling[0]["home_baseline_acc"] == 60.0


def test_benchmark_suite_handles_prior_elo_base_and_market():
    prior_rows = []
    for idx in range(30):
        outcome = idx % 3
        prior_rows.append({
            "match_id": 1000 + idx,
            "season": "2024_25",
            "is_played": True,
            "home_score": 2 if outcome == 0 else 1,
            "away_score": 1 if outcome in (0, 1) else 2,
            "elo_diff": 80.0 if outcome == 0 else (-60.0 if outcome == 2 else 5.0),
            "elo_venue_diff": 60.0 if outcome == 0 else (-40.0 if outcome == 2 else 0.0),
        })
    test_rows = []
    played_items = []
    raw_probs = {}
    for idx in range(10):
        mid = 2000 + idx
        outcome = 0 if idx < 6 else (1 if idx < 8 else 2)
        test_rows.append({
            "match_id": mid,
            "season": "2025_26",
            "is_played": True,
            "home_score": 2 if outcome == 0 else 1,
            "away_score": 1 if outcome in (0, 1) else 2,
            "elo_diff": 90.0 if outcome == 0 else (-70.0 if outcome == 2 else 0.0),
            "elo_venue_diff": 70.0 if outcome == 0 else (-50.0 if outcome == 2 else 0.0),
        })
        p_vec = np.array([0.70, 0.20, 0.10]) if outcome == 0 else (np.array([0.30, 0.45, 0.25]) if outcome == 1 else np.array([0.15, 0.25, 0.60]))
        raw_probs[mid] = p_vec
        played_items.append({
            "match_id": mid,
            "actual_result": ["home", "draw", "away"][outcome],
            "prob_home": round(p_vec[0] * 100, 1),
            "prob_draw": round(p_vec[1] * 100, 1),
            "prob_away": round(p_vec[2] * 100, 1),
            "market_home_odds": 1.8 if idx < 6 else 2.6,
            "market_draw_odds": 3.5,
            "market_away_odds": 4.2 if idx < 6 else 2.2,
        })

    df_all = pd.DataFrame(prior_rows + test_rows)
    suite = model_audit._compute_benchmark_suite(df_all, "2025_26", played_items, raw_probs, "prospective")
    assert suite["role"] == "prospective"
    assert set(suite["scores"].keys()) >= {"model", "base_rate", "elo", "market"}
    assert set(suite["verdicts"].keys()) >= {"model_vs_base_rate", "model_vs_elo", "model_vs_market"}
    assert suite["verdicts"]["model_vs_base_rate"]["verdict"] == "better"


def test_optional_artifact_loaders_degrade_gracefully_when_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(model_audit, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(model_audit, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(model_audit, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(model_audit, "FORECAST_LOG_PATH", tmp_path / "missing.jsonl")

    sc = model_audit._load_prospective_scorecard()
    assert sc["groups"] == [] and sc["goal_market_groups"] == [] and sc["active_outcome_sha256"] is None

    bt = model_audit._load_backtest_calibration()
    assert bt["o25_reliability"] is None and bt["goal_outer_seasons"] == [] and bt["x12_season_holdouts"] == []
