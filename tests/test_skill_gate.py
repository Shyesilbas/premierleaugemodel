from src.models.model_utils import apply_skill_gate


def test_gate_falls_back_when_relative_gain_is_below_threshold():
    folds = {
        "ridge_100.0": [3.00, 3.01, 3.02, 3.03],
        "training_mean": [3.01, 3.02, 3.03, 3.04],
    }

    selected, details = apply_skill_gate(folds, "ridge_100.0")

    assert selected == "training_mean"
    assert details["skill_gate_applied"] is True
    assert details["fold_wins"] == 4


def test_gate_keeps_model_with_clear_gain_and_fold_wins():
    folds = {
        "ridge_10.0": [2.8, 2.8, 2.8, 2.8],
        "training_mean": [3.0, 3.0, 3.0, 3.0],
    }

    selected, details = apply_skill_gate(folds, "ridge_10.0")

    assert selected == "ridge_10.0"
    assert details["skill_gate_passed"] is True
    assert details["fold_wins"] == 4
