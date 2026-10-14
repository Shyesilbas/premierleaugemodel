from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.models.eval_utils import paired_bootstrap_delta


def test_bootstrap_identical_losses_centered_on_zero():
    losses = np.random.default_rng(0).uniform(0.5, 1.5, 300)

    result = paired_bootstrap_delta(losses, losses.copy())

    assert abs(result["mean_delta"]) < 1e-12
    assert result["ci_low"] <= 0 <= result["ci_high"]


def test_bootstrap_detects_clear_improvement():
    baseline = np.random.default_rng(1).uniform(0.8, 1.2, 400)
    better = baseline - 0.05

    result = paired_bootstrap_delta(better, baseline)

    assert result["ci_high"] < 0
    assert result["p_a_better"] > 0.99
