import math
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from src.models import evaluate_goal_models as ev
from src.models.train_match_outcome import EXTRA_O25, STRENGTH_FEATURES_O25, _form_features


def _synthetic_matches(per_season: int = 100, seasons: int = 4, seed: int = 0) -> pd.DataFrame:
    """Random features that carry a little signal; enough rows for one outer season (>= 300 training rows)."""
    rng = np.random.default_rng(seed)
    columns = STRENGTH_FEATURES_O25 + _form_features("o25") + EXTRA_O25
    n = per_season * seasons
    frame = pd.DataFrame(rng.normal(size=(n, len(columns))), columns=columns)
    home = rng.integers(0, 10, n)
    away = (home + rng.integers(1, 10, n)) % 10
    frame["home_id"], frame["away_id"] = home, away
    frame["home_score"] = rng.poisson(np.exp(0.3 + 0.15 * frame[columns[0]]))
    frame["away_score"] = rng.poisson(np.exp(0.1 - 0.15 * frame[columns[0]]))
    frame["match_id"] = np.arange(n)
    frame["kickoff_millis"] = 1_600_000_000_000 + np.arange(n) * 86_400_000
    frame["match_date"] = pd.to_datetime(frame["kickoff_millis"], unit="ms", utc=True)
    frame["season"] = np.repeat([f"20{20 + i}_{21 + i}" for i in range(seasons)], per_season)
    return frame


def _flat_market(match_ids, db_path=None):
    return pd.DataFrame({"o25": np.full(len(match_ids), 0.55), "btts": np.full(len(match_ids), 0.5)})


def test_gates_report_the_constant_poisson_btts_and_market_comparisons():
    with mock.patch.object(ev, "_market_probabilities", _flat_market):
        _, _, gates = ev.evaluate_outer_seasons(_synthetic_matches())
    assert "null" not in gates  # the benchmark is reported through the other gates, not gated itself
    gate = gates["blend_dc_feat"]
    for key in ("mean_score_nll", "score_nll_vs_null", "pooled_paired_bootstrap_vs_null", "btts_gate", "market_comparison"):
        assert key in gate, key
    assert math.isfinite(gate["mean_score_nll"]) and gate["mean_score_nll"] > 0
    assert gate["pooled_paired_bootstrap_vs_null"]["n"] == 100  # one outer season was evaluated
    assert gate["market_comparison"]["o25"]["n"] == 100 and gate["market_comparison"]["btts"]["n"] == 100


def test_a_model_cannot_pass_without_beating_the_constant_poisson_and_btts_needs_a_clear_win():
    with mock.patch.object(ev, "_market_probabilities", _flat_market):
        _, _, gates = ev.evaluate_outer_seasons(_synthetic_matches())
    for gate in gates.values():
        if gate["passed"]:
            assert gate["pooled_paired_bootstrap_vs_null"]["mean_delta"] < 0
    btts = gates["blend_dc_feat"]["btts_gate"]
    assert btts["passed"] == (btts["pooled_paired_bootstrap_vs_null"]["ci_high"] < 0)


def test_market_probabilities_remove_the_bookmaker_margin():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "db.sqlite"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE external_match_odds (match_id INTEGER, bookmaker TEXT, over_25_last_seen REAL, "
                         "under_25_last_seen REAL, btts_yes_last_seen REAL, btts_no_last_seen REAL)")
            conn.executemany("INSERT INTO external_match_odds VALUES (?, ?, ?, ?, ?, ?)", [
                (1, "Bet365", 1.9, 1.9, 1.8, 2.0), (2, "Bet365", 1.6, 2.4, None, None), (3, "Pinnacle", 1.5, 2.6, 1.5, 2.6),
            ])
        probs = ev._market_probabilities(pd.Series([1, 2, 3, 4]), db_path=str(db))
    assert probs["o25"].iloc[0] == 0.5
    assert abs(probs["o25"].iloc[1] - 0.6) < 1e-9  # (1/1.6) / (1/1.6 + 1/2.4)
    assert abs(probs["btts"].iloc[0] - (1 / 1.8) / (1 / 1.8 + 1 / 2.0)) < 1e-9
    assert probs["btts"].iloc[1:].isna().all()  # no BTTS price, other bookmaker, and unknown match all stay NaN
    assert math.isnan(probs["o25"].iloc[2]) and math.isnan(probs["o25"].iloc[3])
