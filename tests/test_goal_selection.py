import numpy as np
import pandas as pd

from src.models.train_goals import BLEND_GRID, _calibration_result, select_blend_config


def _synthetic_matches(n: int = 240, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    strength = rng.normal(size=n)
    return pd.DataFrame({
        "home_id": rng.integers(0, 10, n),
        "away_id": rng.integers(10, 20, n),
        "kickoff_millis": np.arange(n) * 86_400_000,
        "match_date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "strength": strength,
        "home_score": rng.poisson(np.exp(0.3 + 0.3 * strength)),
        "away_score": rng.poisson(np.exp(0.1 - 0.3 * strength)),
    })


def test_select_blend_config_returns_a_grid_point():
    matches = _synthetic_matches()
    matches["noise"] = np.random.default_rng(2).normal(size=len(matches))
    chosen = select_blend_config(matches, {"full": ["strength", "noise"], "compact": ["strength"]})

    assert chosen["kind"] == BLEND_GRID["kind"]
    assert chosen["feature_set"] in BLEND_GRID["feature_sets"]
    assert chosen["feature_alpha"] in BLEND_GRID["feature_alphas"]
    assert chosen["dc_weight"] in BLEND_GRID["dc_weights"]


def test_calibration_is_scored_forward_and_kept_when_it_fixes_a_bias():
    rng = np.random.default_rng(1)
    n = 600
    y = rng.binomial(1, 0.6, n)
    biased = np.full(n, 0.45)  # constant under-prediction of a 60% event

    calibrator, metrics = _calibration_result(biased, y, np.arange(n))

    assert calibrator is not None
    assert metrics["calibration_applied"] is True
    assert metrics["calibrated_oof_log_loss"] < metrics["raw_oof_log_loss"]
    assert metrics["scored_matches"] < metrics["oof_matches"]  # first block is never scored
