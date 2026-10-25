"""Tests for train-serve feature parity (K5) and model audit/prediction invariants (K1, K3, K4, K6, K8)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.api.prediction_service import (
    _col_float,
    _compute_home_share,
    is_1x2_ensemble_active,
    predict_count_market,
)
from src.config import MATCHES_SUMMARY_PATH
from src.db.database import attach_statsapi_xg
from src.features import build_features as bf
from src.features.draw_features import add_draw_features, build_draw_state
from src.models.model_utils import chronological_regression_evaluation, estimate_count_dispersion
from src.models.train_cards import CURATED_FEATURES as CARD_FEATURES
from src.models.train_corners import CURATED_FEATURES as CORNER_FEATURES
from src.models.train_goals import derive_goal_skill_gate
from src.models.train_match_outcome import feature_set
from src.models.train_offsides import CURATED_FEATURES as OFFSIDE_FEATURES
from src.models.train_saves import CURATED_FEATURES as SAVE_FEATURES
from src.models.train_throws import CURATED_FEATURES as THROW_FEATURES


def test_col_float_preserves_zero_values_instead_of_falsy_fallback():
    df = pd.DataFrame({
        "home_offsides_for_roll_5": [0.0],
        "home_cards_for_roll_5": [np.nan],
    })
    assert _col_float(df, "home_offsides_for_roll_5", 1.6) == 0.0
    assert _col_float(df, "home_cards_for_roll_5", 2.1) == 2.1
    assert _col_float(df, "missing_col", 4.15) == 4.15


def test_compute_home_share_clamps_and_handles_zero_total():
    assert _compute_home_share(0.0, 0.0, default=0.52) == 0.52
    assert _compute_home_share(9.0, 1.0, min_share=0.20, max_share=0.80) == 0.80
    assert _compute_home_share(1.0, 9.0, min_share=0.20, max_share=0.80) == 0.20
    assert abs(_compute_home_share(3.0, 2.0) - 0.60) < 1e-9


def test_predict_count_market_labels_missing_artifact_as_fallback_constant():
    row_df = pd.DataFrame({"home_offsides_for_roll_5": [1.2]})
    exp_val, probs, skill = predict_count_market(
        row_df,
        None,
        min_val=0.5,
        max_val=10.0,
        fallback_total=3.26,
        thresholds=(2, 3),
        fallback_probs_pct=(65.0, 45.0),
    )
    assert exp_val == 3.26
    assert skill == "fallback_constant"
    assert probs == {2: 65.0, 3: 45.0}


def test_is_1x2_ensemble_active_respects_outer_season_gate():
    artifact_failed = {
        "model_dc": object(),
        "metrics": {
            "1x2_ensemble_production": {"enabled": True},
            "1x2_ensemble_outer_eval": {"gate_passed": False},
        },
    }
    assert is_1x2_ensemble_active(artifact_failed) is False

    artifact_passed = {
        "model_dc": object(),
        "metrics": {
            "1x2_ensemble_production": {"enabled": True},
            "1x2_ensemble_outer_eval": {"gate_passed": True},
        },
    }
    assert is_1x2_ensemble_active(artifact_passed) is True


def test_derive_goal_skill_gate_reflects_evaluation_and_calibration():
    evaluation = {
        "outer_season_results": [
            {"target": "over_1.5", "model": "blend_dc_feat", "delta_vs_prior": -0.004},
            {"target": "over_2.5", "model": "blend_dc_feat", "delta_vs_prior": -0.005},
            {"target": "over_3.5", "model": "blend_dc_feat", "delta_vs_prior": 0.002},
            {"target": "btts", "model": "blend_dc_feat", "delta_vs_prior": 0.001},
        ]
    }
    gate = {
        "passed": True,
        "btts_gate": {
            "passed": False,
            "pooled_paired_bootstrap_vs_null": {"mean_delta": 0.001},
        },
    }
    calibration_metrics = {
        "over_1.5": {"calibration_applied": False},
        "over_2.5": {"calibration_applied": True},
        "over_3.5": {"calibration_applied": True},
        "btts": {"calibration_applied": False},
    }
    skill_gate = derive_goal_skill_gate(evaluation, gate, calibration_metrics)
    assert skill_gate["over_1.5"] == "model_matrix"
    assert skill_gate["over_2.5"] == "model"
    assert skill_gate["over_3.5"] == "baseline"
    assert skill_gate["btts"] == "baseline"


def test_residual_dispersion_is_smaller_than_unconditional_when_signal_exists():
    rng = np.random.default_rng(42)
    mu = np.linspace(4.0, 16.0, 300)
    y = pd.Series(rng.poisson(mu).astype(float))
    unconditional_alpha = estimate_count_dispersion(y)
    conditional_alpha = estimate_count_dispersion(y, mu)
    assert unconditional_alpha > 0.05
    assert conditional_alpha < unconditional_alpha


def test_chronological_regression_outer_gate_does_not_peek_at_test_holdout():
    rng = np.random.default_rng(7)
    n = 400
    X = pd.DataFrame({"f1": rng.normal(size=n), "f2": rng.normal(size=n)})
    # Pure noise in development (first 320 rows), strong signal only in the last 80 test holdout rows
    y_vals = rng.normal(loc=10.0, scale=2.0, size=n)
    y_vals[320:] = 10.0 + 5.0 * X["f1"].iloc[320:].to_numpy()
    y = pd.Series(y_vals)
    seasons = pd.Series(["2021_22"] * 160 + ["2022_23"] * 160 + ["2023_24"] * 80)

    from sklearn.linear_model import Ridge
    from src.models.model_utils import make_regression_pipeline

    candidates = {"ridge_1": make_regression_pipeline(Ridge(alpha=1.0), scale=True)}
    selected, _, _, metrics, _, _ = chronological_regression_evaluation(
        X, y, candidates, seasons=seasons, partial_seasons=set()
    )
    assert selected == "training_mean"
    assert metrics["selected_model"] == "training_mean"


@pytest.mark.needs_data
def test_train_serve_feature_parity_including_xi_attack_defense():
    if not MATCHES_SUMMARY_PATH.exists():
        pytest.skip("matches_summary_all.parquet not available")

    bf._XI_MATCH_CACHE = None
    raw = attach_statsapi_xg(pd.read_parquet(MATCHES_SUMMARY_PATH))
    raw = raw.drop(columns=[c for c in ("home_xg", "away_xg", "total_xg") if c in raw.columns])

    df_rest = bf.calculate_rest_days(raw)
    long_df = bf.build_team_match_history(df_rest)
    long_df_feat = bf.compute_pre_match_features(long_df)
    df_train = bf.merge_features_to_matches(df_rest, long_df_feat)
    df_train = bf.compute_referee_features(df_train)
    df_train = bf.compute_strength_features(df_train)
    df_train = bf.add_interaction_features(df_train)
    df_train = add_draw_features(df_train)

    all_model_cols = sorted(set(
        feature_set("1x2", list(df_train.columns))
        + feature_set("o25", list(df_train.columns))
        + list(CORNER_FEATURES)
        + list(THROW_FEATURES)
        + list(SAVE_FEATURES)
        + list(CARD_FEATURES)
        + list(OFFSIDE_FEATURES)
    ))

    prepared = df_rest
    long_history = bf.build_team_match_history(prepared)
    played = df_train[df_train["is_played"]].copy()

    # Sample 10 played matches across distinct kickoff timestamps
    sample_rows = played.tail(80).drop_duplicates(subset=["match_date"]).tail(10)
    assert len(sample_rows) >= 5

    for _, tr_row in sample_rows.iterrows():
        m_date = pd.Timestamp(tr_row["match_date"])
        # Strictly earlier matches (before m_date)
        cutoff = m_date - pd.Timedelta(microseconds=1)
        prior_matches = prepared[prepared["is_played"] & (prepared["match_date"] < m_date)]
        if len(prior_matches) < 50:
            continue

        # Also check that no other match occurred at the exact same timestamp before this match_id
        same_ts = prepared[
            prepared["is_played"]
            & (prepared["match_date"] == m_date)
            & (prepared["match_id"] < tr_row["match_id"])
        ]
        if not same_ts.empty:
            continue

        team_states = bf.compute_team_states(long_history, until=cutoff)
        strength_state = bf.compute_strength_state(prepared, until=cutoff)
        draw_state = build_draw_state(prior_matches)
        ref_info = {
            c: tr_row[c]
            for c in ("referee_name", "referee_avg_cards", "referee_avg_fouls", "referee_prior_matches")
            if c in tr_row.index
        }
        serve_df = bf.build_prediction_row(
            team_states,
            strength_state,
            int(tr_row["home_id"]),
            int(tr_row["away_id"]),
            m_date,
            ref_info,
            season=str(tr_row["season"]),
            draw_state=draw_state,
            gameweek=float(tr_row["gameweek"]),
            match_id=int(tr_row["match_id"]),
        )
        for col in all_model_cols:
            v_tr = float(tr_row[col])
            v_sv = float(serve_df[col].iloc[0])
            if np.isnan(v_tr) and np.isnan(v_sv):
                continue
            assert abs(v_tr - v_sv) < 1e-6, (
                f"Parity mismatch on match {tr_row['match_id']} col {col}: "
                f"train={v_tr} vs serve={v_sv}"
            )
