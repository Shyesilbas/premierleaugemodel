"""Leakage and decision checks for the TheStatsAPI league model (LaLiga)."""

import numpy as np
import pandas as pd

from src.models.eval_utils import apply_fdr, benjamini_hochberg, with_inference
from src.features.build_league_features import STAT_PATHS, build_league_features, feature_columns, kickoff
from src.models.train_league_model import base_rate, decide, outcome_label


def synthetic_matches(seed=0, n_rounds=24, teams=6):
    rng = np.random.default_rng(seed)
    rows, match_id = [], 1
    start = pd.Timestamp("2024-08-17 20:00")
    for round_number in range(n_rounds):
        order = rng.permutation(teams)
        for i in range(0, teams, 2):
            home, away = int(order[i]) + 1, int(order[i + 1]) + 1
            row = {"match_id": match_id, "season": "2024_25", "gameweek": round_number + 1, "home_id": home, "away_id": away,
                   "home_name": f"T{home}", "away_name": f"T{away}", "kickoff": start + pd.Timedelta(days=7 * round_number, hours=i),
                   "home_score": float(rng.poisson(1.6)), "away_score": float(rng.poisson(1.1)), "status": "COMPLETED",
                   "match_date": "2024-08-17", "time_label": "20:00 BST", "referee_name": "R"}
            for stat in STAT_PATHS:
                scale = {"possession": 50.0, "passes": 450.0, "accurate_passes": 380.0}.get(stat, 4.0)
                row[f"home_{stat}"] = float(rng.normal(scale, scale * 0.1))
                row[f"away_{stat}"] = float(rng.normal(scale, scale * 0.1))
            rows.append(row)
            match_id += 1
    frame = pd.DataFrame(rows)
    frame["kickoff_millis"] = frame["kickoff"].astype("int64") // 1_000_000
    return frame


def feature_rows(frame):
    built = build_league_features(frame)
    return built, feature_columns(built)


def test_features_of_a_match_ignore_its_own_result_and_everything_after_it():
    frame = synthetic_matches()
    built, columns = feature_rows(frame)
    cut = 40
    altered = frame.copy()
    later = altered["match_id"] >= altered["match_id"].iloc[cut]
    for column in ["home_score", "away_score"] + [f"{s}_{stat}" for s in ("home", "away") for stat in STAT_PATHS]:
        altered.loc[later, column] = altered.loc[later, column] * 3.0 + 7.0
    rebuilt, _ = feature_rows(altered)
    early = built["match_id"] < altered["match_id"].iloc[cut]
    left = built.loc[early, columns].reset_index(drop=True)
    right = rebuilt.loc[rebuilt["match_id"] < altered["match_id"].iloc[cut], columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(left, right)
    # the match at the cut and the ones after it do react to the changed past results
    assert not built.loc[~early, columns].reset_index(drop=True).equals(rebuilt.loc[rebuilt["match_id"] >= altered["match_id"].iloc[cut], columns].reset_index(drop=True))


def test_a_matchs_features_do_not_move_when_only_its_own_result_changes():
    frame = synthetic_matches(seed=1)
    built, columns = feature_rows(frame)
    target = frame["match_id"].iloc[30]
    altered = frame.copy()
    row = altered["match_id"] == target
    altered.loc[row, ["home_score", "away_score"]] = [9.0, 0.0]
    altered.loc[row, "home_xg"] = 5.0
    rebuilt, _ = feature_rows(altered)
    a = built.loc[built["match_id"] == target, columns].iloc[0]
    b = rebuilt.loc[rebuilt["match_id"] == target, columns].iloc[0]
    pd.testing.assert_series_equal(a, b)


def test_unplayed_matches_get_features_but_never_feed_the_history():
    frame = synthetic_matches(seed=2)
    future = frame.copy()
    tail = future["match_id"] > future["match_id"].max() - 3
    future.loc[tail, ["home_score", "away_score"]] = np.nan
    built, columns = feature_rows(future)
    assert built.loc[tail.values, columns].notna().all().all()
    base, _ = feature_rows(frame)
    pd.testing.assert_frame_equal(built.loc[~tail.values, columns].reset_index(drop=True), base.loc[~tail.values, columns].reset_index(drop=True))


def test_feature_columns_exclude_raw_per_match_numbers():
    built, columns = feature_rows(synthetic_matches())
    assert "home_score" not in columns and "home_xg" not in columns and "kickoff" not in columns
    assert {"elo_diff", "ppg_diff", "xg_diff_10", "home_xg_for_roll_10", "home_rest_days"} <= set(columns)


def test_kickoff_uses_london_time_and_midnight_when_no_clock_time():
    assert kickoff("2026-10-25", "15:15 GMT") == pd.Timestamp("2026-10-25 15:15")
    assert kickoff("2026-07-01", "20:00 BST") == pd.Timestamp("2026-07-01 19:00")
    assert kickoff("2027-01-17", "") == pd.Timestamp("2027-01-17 00:00")


def test_gate_serves_the_model_only_when_it_beats_the_base_rate_and_the_elo_baseline():
    def summary(base_delta, base_sig, elo_delta):
        return {"comparisons": {"vs_base_rate": {"pooled_outer": {"mean_delta": base_delta, "significant_fdr_05": base_sig}},
                                "vs_elo": {"pooled_outer": {"mean_delta": elo_delta}}}}

    assert decide(summary(-0.05, True, -0.01))["serving"] == "model"
    assert decide(summary(-0.05, True, 0.004))["serving"] == "elo_baseline"  # worse than Elo
    assert decide(summary(-0.05, False, -0.01))["serving"] == "elo_baseline"  # not distinguishable from the base rate
    assert decide(summary(0.01, True, -0.01))["serving"] == "elo_baseline"


def test_base_rate_and_labels():
    y = np.array([0, 0, 1, 2])
    probabilities = base_rate(y, 3)
    assert probabilities.shape == (3, 3) and np.allclose(probabilities.sum(axis=1), 1.0)
    frame = pd.DataFrame({"home_score": [2, 1, 0], "away_score": [0, 1, 3]})
    assert outcome_label(frame).tolist() == [0, 1, 2]


def test_inference_helpers_report_power_and_adjust_p_values():
    rng = np.random.default_rng(0)
    a = rng.normal(0.9, 0.3, 400)
    b = a + rng.normal(0.02, 0.2, 400)
    result = with_inference(a, b, n_boot=2000)
    assert result["mean_delta"] < 0 and result["n_required_80_power"] > 0 and 0 <= result["p_two_sided"] <= 1
    adjusted = benjamini_hochberg([0.01, 0.04, 0.5])
    assert adjusted == sorted(adjusted) and all(q >= p for q, p in zip(adjusted, [0.01, 0.04, 0.5]))
    entries = {"x": {"p_two_sided": 0.001}, "y": {"p_two_sided": 0.9}, "z": None}
    apply_fdr(entries)
    assert entries["x"]["significant_fdr_05"] and not entries["y"]["significant_fdr_05"]
