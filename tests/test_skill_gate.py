from src.models.model_utils import apply_outer_season_gate, apply_skill_gate


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


def _season(beats, partial=False):
    return {"beats_baseline_rmse": beats, "partial_season": partial}


def test_outer_season_gate_falls_back_without_majority_and_ignores_locked_season():
    # Cards pattern: one win, one loss, one tie; a locked-season win must not rescue it.
    holdouts = [_season(False), _season(True), _season(False), _season(True, partial=True)]
    gate = {"raw_selected_model": "poisson_1", "skill_gate_applied": False}

    selected, details = apply_outer_season_gate(holdouts, "poisson_1", gate)

    assert selected == "training_mean"
    assert details["skill_gate_applied"] is True
    assert details["reason"] == "model_failed_outer_season_gate"
    assert (details["outer_season_wins"], details["outer_season_count"]) == (1, 3)


def test_outer_season_gate_keeps_model_with_majority_wins():
    holdouts = [_season(False), _season(True), _season(True)]

    selected, details = apply_outer_season_gate(holdouts, "ridge_50", {"skill_gate_applied": False})

    assert selected == "ridge_50"
    assert details["outer_season_gate_passed"] is True
