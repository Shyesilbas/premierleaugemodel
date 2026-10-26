"""Prospective forecast log of a league: where it lives, and that scoring counts only forecasts made before kickoff."""

import json

import numpy as np
import pandas as pd
import pytest

from src.analytics import prospective_1x2_benchmark as bench


def row(match_id, made_at, probabilities, artifact="a" * 64, over25=0.6):
    return {"match_id": match_id, "season": "2026_27", "home_id": 1, "away_id": 2, "home_name": "H", "away_name": "A",
            "kickoff_utc": "2026-10-26T20:00:00+00:00", "prediction_made_at_utc": made_at, "artifact_sha256": artifact,
            "goal_artifact_sha256": artifact, "class_order": ["home", "draw", "away"], "probabilities": probabilities,
            "goal_markets": {"over_2.5": {"probability": over25, "source": "model", "baseline_probability": 0.5}}}


def test_a_league_has_its_own_log_scorecard_and_artifact_paths():
    league, premier = bench.targets("la_liga"), bench.targets("premier_league")
    assert "la_liga" in str(league.forecast_log) and "la_liga" in str(league.model) and league.scorecard.name == "prospective_1x2_scorecard_la_liga.json"
    assert premier.forecast_log == bench.FORECAST_LOG and premier.scorecard == bench.SCORECARD_PATH
    assert league.forecast_log != premier.forecast_log and league.model != premier.model


def test_scoring_uses_only_forecasts_made_before_kickoff_and_the_latest_of_them(tmp_path, monkeypatch):
    log = tmp_path / "log.jsonl"
    rows = [row(7, "2026-10-20T10:00:00+00:00", [0.2, 0.3, 0.5]),  # superseded by the later forecast
            row(7, "2026-10-25T10:00:00+00:00", [0.6, 0.25, 0.15]),  # the one that counts: home win happened
            row(7, "2026-10-26T21:00:00+00:00", [0.99, 0.005, 0.005]),  # after kickoff: ignored
            row(8, "2026-10-26T21:00:00+00:00", [0.9, 0.05, 0.05])]  # only a post-kickoff forecast: match not scored
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    target = bench.Targets("la_liga", tmp_path / "m.joblib", tmp_path / "g.joblib", log, tmp_path / "scorecard.json")
    monkeypatch.setattr(bench, "targets", lambda competition="premier_league": target)
    monkeypatch.setattr(bench, "_league_results", lambda key: pd.DataFrame({"match_id": [7, 8], "home_score": [2, 1], "away_score": [0, 1]}))
    result = bench.score("la_liga")
    group = result["groups"][0]
    assert group["matches"] == 1 and group["log_loss"] == pytest.approx(-np.log(0.6), abs=1e-4)
    goals = result["goal_market_groups"][0]["markets"]["over_2.5"]
    assert goals["matches"] == 1 and goals["log_loss"] == pytest.approx(-np.log(0.4), abs=1e-4)  # 2-0 stays under 2.5 goals, so an over forecast of 0.6 pays -ln(0.4)
    assert json.loads(target.scorecard.read_text(encoding="utf-8"))["groups"][0]["matches"] == 1
