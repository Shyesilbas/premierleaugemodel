import numpy as np
import pandas as pd

from src.models.train_match_outcome import (
    chronological_holdout_split,
    forward_time_splits,
    summarize_draw_propensity_gate,
)
from src.models.model_utils import safe_feature_frame


def test_grouped_forward_folds_keep_equal_kickoffs_together():
    kickoff_times = np.repeat(np.arange(10), [1, 2, 1, 3, 2, 1, 2, 1, 3, 2])

    folds = forward_time_splits(len(kickoff_times), kickoff_times)

    assert len(folds) == 4
    previous_train_size = 0
    for train_idx, valid_idx in folds:
        train_groups = set(kickoff_times[train_idx])
        valid_groups = set(kickoff_times[valid_idx])
        assert train_groups.isdisjoint(valid_groups)
        assert max(train_groups) < min(valid_groups)
        assert len(train_idx) > previous_train_size
        previous_train_size = len(train_idx)


def test_grouped_holdout_chooses_nearest_boundary_without_splitting_kickoffs():
    kickoff_times = np.repeat(np.arange(10), [1, 2, 1, 3, 2, 1, 2, 1, 3, 2])

    split_idx = chronological_holdout_split(len(kickoff_times), kickoff_times)

    assert kickoff_times[split_idx - 1] != kickoff_times[split_idx]
    boundaries = np.flatnonzero(
        np.r_[kickoff_times[1:] != kickoff_times[:-1], True]
    ) + 1
    valid_boundaries = boundaries[(boundaries > 0) & (boundaries < len(kickoff_times))]
    target = int(len(kickoff_times) * 0.8)
    assert abs(split_idx - target) == min(abs(int(boundary) - target) for boundary in valid_boundaries)


def test_draw_propensity_gate_ignores_fallback_seasons_and_needs_three_clean_seasons():
    rows = []
    for season, fallback in (("2023_24", True), ("2024_25", False), ("2025_26", False)):
        for feature_name, loss, auc in (
            ("with_draw_propensity", 1.00, 0.56),
            ("without_draw_propensity", 1.01, 0.54),
        ):
            rows.append({
                "season": season,
                "partial_season": False,
                "policy": "exclude_2022_23",
                "features": feature_name,
                "early_season_fallback_included_excluded_history": fallback,
                "test_samples": 300,
                "log_loss": loss,
                "draw_auc": auc,
            })

    summary = summarize_draw_propensity_gate(rows)

    assert summary["season_count"] == 2
    assert summary["gate_passed"] is False


def test_draw_propensity_gate_passes_only_with_three_clean_outer_seasons():
    rows = []
    for season in ("2024_25", "2025_26", "2026_27"):
        for feature_name, loss, auc in (
            ("with_draw_propensity", 1.00, 0.56),
            ("without_draw_propensity", 1.01, 0.54),
        ):
            rows.append({
                "season": season,
                "partial_season": False,
                "policy": "exclude_2022_23",
                "features": feature_name,
                "early_season_fallback_included_excluded_history": False,
                "test_samples": 300,
                "log_loss": loss,
                "draw_auc": auc,
            })

    summary = summarize_draw_propensity_gate(rows)

    assert summary["season_count"] == 3
    assert summary["gate_passed"] is True


def test_safe_feature_frame_preserves_missing_values_when_requested():
    source = pd.DataFrame({"known": [1.0, np.nan]})

    preserve_missing = safe_feature_frame(source, ["known", "missing"], fill_value=np.nan)
    zero_fill = safe_feature_frame(source, ["known", "missing"], fill_value=0.0)

    assert preserve_missing["known"].iloc[1] != preserve_missing["known"].iloc[1]
    assert preserve_missing["missing"].isna().all()
    assert zero_fill["known"].iloc[1] == 0.0
    assert zero_fill["missing"].eq(0.0).all()
