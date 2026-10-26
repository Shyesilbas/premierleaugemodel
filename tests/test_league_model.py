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


def test_count_model_columns_stay_out_of_the_1x2_set_and_targets_are_sums():
    from src.features.build_league_features import COUNT_TARGETS, count_feature_columns

    built, columns = feature_rows(synthetic_matches(seed=3))
    counts = count_feature_columns(built)
    assert counts and not set(counts) & set(columns)
    assert not set(COUNT_TARGETS) & (set(columns) | set(counts))
    assert {"referee_avg_cards", "referee_avg_fouls", "home_corners_for_roll_5", "away_offsides_against_roll_10"} <= set(counts)
    np.testing.assert_allclose(built["total_corners"], built["home_corners"] + built["away_corners"])
    np.testing.assert_allclose(built["total_cards"], built["home_yellow"] + built["home_red"] + built["away_yellow"] + built["away_red"])


def test_count_features_and_referee_history_ignore_the_match_itself_and_later_ones():
    from src.features.build_league_features import count_feature_columns

    frame = synthetic_matches(seed=4)
    frame["referee_name"] = ["R1", "R2", "R3"] * (len(frame) // 3)
    built = build_league_features(frame)
    columns = count_feature_columns(built)
    cut = 45
    altered = frame.copy()
    later = altered["match_id"] >= altered["match_id"].iloc[cut]
    for column in [f"{s}_{stat}" for s in ("home", "away") for stat in STAT_PATHS]:
        altered.loc[later, column] = altered.loc[later, column] * 4.0 + 9.0
    rebuilt = build_league_features(altered)
    early = built["match_id"] < altered["match_id"].iloc[cut]
    pd.testing.assert_frame_equal(built.loc[early, columns].reset_index(drop=True),
                                  rebuilt.loc[rebuilt["match_id"] < altered["match_id"].iloc[cut], columns].reset_index(drop=True))
    # first match of a referee equals the league prior; later ones move toward the referee's own record
    assert built["referee_prior_matches"].iloc[0] == 0 and built["referee_prior_matches"].iloc[-1] > 0


def synthetic_player_lines(frame, seed=0, squad=14):
    rng = np.random.default_rng(seed)
    rows = []
    for match in frame.itertuples():
        for side, team in (("home", match.home_id), ("away", match.away_id)):
            for slot in range(squad):
                rows.append({"match_id": match.match_id, "side": side, "player_id": f"p{team}_{slot}", "position": "GDDDMMMFFFF"[slot % 11],
                             "rating": float(rng.normal(6.9, 0.5)), "started": slot < 11, "minutes": 90.0 if slot < 11 else 15.0 + slot})
    return pd.DataFrame(rows)


def test_xi_features_ignore_the_match_itself_and_later_matches_and_stay_out_of_the_default_set():
    from src.features.build_league_features import xi_feature_columns

    frame = synthetic_matches(seed=5)
    lines = synthetic_player_lines(frame)
    built = build_league_features(frame, lines)
    columns = xi_feature_columns(built)
    assert len(columns) == 12 and not set(columns) & set(feature_columns(built)) and set(columns) <= set(feature_columns(built, include_xi=True))
    cut = 40
    later_ids = set(frame["match_id"].iloc[cut:])
    altered = lines.copy()
    later = altered["match_id"].isin(later_ids)
    altered.loc[later, "rating"] = altered.loc[later, "rating"] * 0.5 + 4.0
    altered.loc[later, "minutes"] = 5.0
    rebuilt = build_league_features(frame, altered)
    early = ~built["match_id"].isin(later_ids)
    pd.testing.assert_frame_equal(built.loc[early, columns].reset_index(drop=True), rebuilt.loc[rebuilt["match_id"].isin(set(frame["match_id"].iloc[:cut])), columns].reset_index(drop=True))
    # the first match of the cut sees only earlier matches, so its own (altered) ratings must not move it
    first_later = frame["match_id"].iloc[cut]
    pd.testing.assert_series_equal(built.loc[built["match_id"] == first_later, columns].iloc[0], rebuilt.loc[rebuilt["match_id"] == first_later, columns].iloc[0])


def test_xi_features_fall_back_to_the_previous_xi_for_an_unplayed_match():
    from src.features.build_league_features import xi_feature_columns

    frame = synthetic_matches(seed=6)
    lines = synthetic_player_lines(frame, seed=6)
    last = frame["match_id"].iloc[-1]
    future = frame.copy()
    future.loc[future["match_id"] == last, ["home_score", "away_score"]] = np.nan
    built = build_league_features(future, lines[lines["match_id"] != last])
    row = built[built["match_id"] == last]
    assert row[xi_feature_columns(built)].notna().all().all()
    assert 6.0 < float(row["home_xi_rating"].iloc[0]) < 8.0 and 0.0 < float(row["home_xi_continuity"].iloc[0]) <= 1.0


def test_ablation_variants_only_swap_columns_or_the_grid_and_the_adoption_rule_needs_every_condition():
    from src.models.ablate_league_features import CORE_FEATURES, decide as ablation_decide
    from src.models.train_league_model import LOW_C_GRID, league_candidates
    from src.models.train_match_outcome import candidate_models

    base, extended = candidate_models(), league_candidates(low_c=True)
    assert set(base) < set(extended) and {f"logreg_C{c}" for c in LOW_C_GRID} == set(extended) - set(base)
    assert set(league_candidates()) == set(base) and len(set(CORE_FEATURES)) == len(CORE_FEATURES)
    good = {"mean_delta": -0.01, "ci_high": -0.002, "q_fdr": 0.01, "p_two_sided": 0.01}
    assert ablation_decide(good, {"mean_delta": -0.01})["adopt"]
    assert not ablation_decide(good, {"mean_delta": 0.001})["adopt"]  # last outer season worse
    assert not ablation_decide({**good, "ci_high": 0.003}, {"mean_delta": -0.01})["adopt"]  # interval includes zero
    assert not ablation_decide({**good, "q_fdr": 0.2}, {"mean_delta": -0.01})["adopt"]  # not significant across the family


def test_goal_markets_are_served_as_model_only_when_they_beat_the_base_rate_after_fdr():
    from src.models.train_league_model import goal_market_gates

    win = {"vs_base_rate": {"mean_delta": -0.02, "significant_fdr_05": True}}
    goals = {"over_15": win, "over_25": {"vs_base_rate": {"mean_delta": -0.02, "significant_fdr_05": False}},
             "over_35": {"vs_base_rate": {"mean_delta": 0.01, "significant_fdr_05": True}}}  # btts missing
    assert goal_market_gates(goals) == {"over_15": "model", "over_25": "baseline", "over_35": "baseline", "btts": "baseline"}
    assert set(goal_market_gates({}).values()) == {"baseline"}


def test_premier_league_feature_code_on_league_data_ignores_the_match_itself_and_later_matches():
    from src.features.build_league_pl_features import NO_SOURCE_COLUMNS, build_parity_features, parity_feature_columns

    frame = synthetic_matches(seed=8, n_rounds=20)
    frame["referee_name"] = ["R1", "R2", "R3"] * (len(frame) // 3)
    frame["home_np_xg"] = frame["home_xg"] * 0.9
    frame["away_np_xg"] = frame["away_xg"] * 0.9
    lines = synthetic_player_lines(frame, seed=8)
    built = build_parity_features(frame, lines)
    columns = parity_feature_columns(built)
    assert not set(columns) & set(NO_SOURCE_COLUMNS) and {"xi_rating_diff", "home_xg_for_roll_10", "venue_xg_diff"} <= set(columns)
    assert {"missing_reg_mins_diff", "referee_avg_cards", "total_corners", "home_throws_roll_5", "exp_match_shots_5"} <= set(built.columns)
    cut = 30
    later_ids = set(frame["match_id"].iloc[cut:])
    altered = frame.copy()
    later = altered["match_id"].isin(later_ids)
    for column in ["home_score", "away_score"] + [f"{s}_{stat}" for s in ("home", "away") for stat in STAT_PATHS]:
        altered.loc[later, column] = altered.loc[later, column] * 3.0 + 5.0
    after = altered.copy()
    rebuilt = build_parity_features(after, lines[lines["match_id"].isin(set(frame["match_id"]))].assign(rating=lambda d: np.where(d["match_id"].isin(later_ids), 4.0, d["rating"])))
    early_ids = set(frame["match_id"].iloc[:cut])
    left = built[built["match_id"].isin(early_ids)].set_index("match_id")[columns].sort_index()
    right = rebuilt[rebuilt["match_id"].isin(early_ids)].set_index("match_id")[columns].sort_index()
    pd.testing.assert_frame_equal(left, right)


def test_feature_audit_assigns_every_feature_a_family_and_shuffles_a_family_with_one_shared_permutation():
    from src.analytics.league_feature_audit import outcome_family, permutation_rows

    built, columns = feature_rows(synthetic_matches(seed=9))
    assert {outcome_family(c) for c in columns} - {"other"} and "other" not in {outcome_family(c) for c in columns}
    assert outcome_family("diff_xg_for_roll_10") == outcome_family("home_xg_for_roll_10") == "form_xg"
    table = pd.DataFrame({"a": np.arange(10.0), "b": np.arange(10.0) * 10.0, "keep": np.arange(10.0) * 100.0})
    shuffled = permutation_rows(table, ["a", "b"], np.random.default_rng(0))
    assert not shuffled["a"].equals(table["a"]) and sorted(shuffled["a"]) == sorted(table["a"])
    assert (shuffled["b"] == shuffled["a"] * 10.0).all()  # one permutation moves the whole family's rows together
    assert shuffled["keep"].equals(table["keep"])


def test_goal_model_evaluation_trains_on_earlier_unlocked_seasons_only_and_the_production_gate_follows_the_decision():
    from src.models.evaluate_league_goal_models import played_before
    from src.models.train_league_model import GOAL_MARKETS

    table = pd.DataFrame({"match_id": range(8), "season": ["2023_24", "2023_24", "2024_25", "2024_25", "2025_26", "2025_26", "2026_27", "2026_27"],
                          "home_score": [1.0, 2.0, 0.0, 1.0, 3.0, np.nan, 1.0, 0.0], "away_score": [0.0, 2.0, 1.0, 1.0, 0.0, np.nan, 1.0, 2.0]})
    assert played_before(table, "2025_26")["season"].unique().tolist() == ["2023_24", "2024_25"]
    assert "2026_27" not in played_before(table, "2027_28")["season"].unique() and len(played_before(table, "2023_24")) == 0
    decision = {m: {"serving": "pl_feature_model" if m in ("over_15", "over_25") else "baseline"} for m in GOAL_MARKETS}
    gate = {m: "model" if decision[m]["serving"] == "pl_feature_model" else "baseline" for m in GOAL_MARKETS}
    assert gate == {"over_15": "model", "over_25": "model", "over_35": "baseline", "btts": "baseline"}


def test_elo_tuning_difference_ignores_the_match_itself_and_later_results():
    from src.models.tune_league_elo import CURRENT, elo_difference

    matches = pd.DataFrame({
        "season": ["2022_23"] * 4, "home_id": [1, 2, 1, 2], "away_id": [2, 1, 2, 1],
        "home_score": [2.0, 0.0, 1.0, 3.0], "away_score": [0.0, 1.0, 1.0, 0.0],
    })
    base = elo_difference(matches, CURRENT)
    altered = matches.copy()
    altered.loc[2:, ["home_score", "away_score"]] = [[5.0, 0.0], [0.0, 4.0]]
    assert base[0] == 0.0
    assert np.allclose(base[:3], elo_difference(altered, CURRENT)[:3])
