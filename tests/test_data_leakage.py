#!/usr/bin/env python3
"""
Limited feature leakage sanity checks.

These checks look for a few direct target-column mistakes and verify that changing
one match's result does not change its own pre-match rolling features. They do not
prove that every feature, imputation step, or model training path is leakage-free.
"""

import sys
import pandas as pd
from pathlib import Path

import pytest

from src.config import FEATURES_PATH, MATCHES_SUMMARY_PATH

pytestmark = pytest.mark.needs_data

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.features.build_features import calculate_rest_days, build_team_match_history, compute_pre_match_features, merge_features_to_matches


def test_no_target_in_features():
    """Checks that selected rolling/expected feature names are not direct targets."""
    feat_path = FEATURES_PATH
    df = pd.read_parquet(feat_path)
    feature_cols = [
        c for c in df.columns if (
            "_roll_" in c or "_ewma_" in c or "rest_days" in c or "exp_" in c
        ) and not c.startswith("match_") and not c.startswith("total_") and not c.startswith("target_")
    ]

    for c in feature_cols:
        for f in ["score", "match_result", "home_win", "away_win", "total_corners", "total_throws", "total_saves"]:
            if c == f:
                raise AssertionError(f"LEAKAGE DETECTED: Column '{c}' directly contains match target!")

    print(f"✅ TEST 1 PASSED: No direct target name found among {len(feature_cols)} selected feature columns.")


def test_invariance_to_match_outcome():
    """
    Changes in-match values for one row, rebuilds features, and compares that row's
    pre-match rolling/expected features. This is a narrow local invariance check.
    """
    df_raw = pd.read_parquet(MATCHES_SUMMARY_PATH).head(20).copy()

    # Base features
    df1 = calculate_rest_days(df_raw.copy())
    long1 = build_team_match_history(df1)
    long1 = compute_pre_match_features(long1)
    merged1 = merge_features_to_matches(df1, long1)

    # Injected modification into match index 5 (simulate heavy outcome changes)
    df_tampered = df_raw.copy()
    target_match_id = df_tampered.loc[5, "match_id"]
    df_tampered.loc[5, "home_score"] = 99
    df_tampered.loc[5, "away_score"] = 88
    df_tampered.loc[5, "home_won_corners"] = 77.0
    df_tampered.loc[5, "away_won_corners"] = 66.0
    df_tampered.loc[5, "home_total_throws"] = 55.0

    df2 = calculate_rest_days(df_tampered)
    long2 = build_team_match_history(df2)
    long2 = compute_pre_match_features(long2)
    merged2 = merge_features_to_matches(df2, long2)

    # Check match 5 pre-match features in merged1 vs merged2
    feature_cols = [c for c in merged1.columns if "_roll_" in c or "_ewma_" in c or "exp_" in c]

    row1 = merged1[merged1["match_id"] == target_match_id][feature_cols].iloc[0]
    row2 = merged2[merged2["match_id"] == target_match_id][feature_cols].iloc[0]

    max_diff = (row1 - row2).abs().max()
    assert max_diff == 0.0, f"LEAKAGE DETECTED: Match features changed by {max_diff} when in-match stats were tampered!"

    print(f"✅ TEST 2 PASSED: Modifying in-match values caused 0.000 change in that row's selected pre-match features.")


if __name__ == "__main__":
    print("--- Running limited feature leakage sanity checks ---")
    test_no_target_in_features()
    test_invariance_to_match_outcome()
    print("--- Sanity checks passed; this is not a complete leakage audit. ---")
