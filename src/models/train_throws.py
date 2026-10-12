#!/usr/bin/env python3
"""
Throws Prediction Model (Regularized LightGBM & Poisson Probabilities)
Predicts total match throws (taç) and probabilities for Over 33.5 / 34.5 / 36.5 throws.
Uses strictly curated, domain-relevant features (throws for/against, possession, tempo).
Evaluated with Time-Series Split and refitted on 100% data for production.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from scipy.stats import poisson
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_throws")

CURATED_FEATURES = [
    "home_throws_roll_3",
    "home_throws_roll_5",
    "home_throws_roll_10",
    "away_throws_roll_3",
    "away_throws_roll_5",
    "away_throws_roll_10",
    "home_opponent_throws_roll_5",
    "away_opponent_throws_roll_5",
    "home_opponent_throws_roll_10",
    "away_opponent_throws_roll_10",
    "exp_match_throws_5",
    "exp_home_throws_5",
    "exp_away_throws_5",
    "home_possession_roll_5",
    "away_possession_roll_5",
]


def train_throws_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        data_path = "data/processed/features_matches_2024_25.parquet"

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    target_col = "total_throws"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "is_played" in df.columns:
        df = df[df["is_played"]].copy()

    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with throws data.")

    feature_cols = [c for c in CURATED_FEATURES if c in df.columns]
    logger.info(f"Selected {len(feature_cols)} curated features for Throws model.")

    X_all = df[feature_cols].fillna(df[feature_cols].mean())
    y_all = df[target_col].astype(float)

    weights_all = np.linspace(0.65, 1.20, len(df))

    split_idx = int(len(df) * 0.8)
    X_train, y_train = X_all.iloc[:split_idx], y_all.iloc[:split_idx]
    X_test, y_test = X_all.iloc[split_idx:], y_all.iloc[split_idx:]
    w_train = weights_all[:split_idx]

    logger.info(f"Train matches: {len(X_train)}, Test matches: {len(X_test)}")

    baseline_pred = float(np.average(y_train, weights=w_train))
    baseline_test_rmse = float(np.sqrt(mean_squared_error(y_test, np.full_like(y_test, baseline_pred))))
    baseline_test_mae = float(mean_absolute_error(y_test, np.full_like(y_test, baseline_pred)))

    candidates = {
        "lgbm_shallow": LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.02,
            n_estimators=60,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        ),
        "ridge_50": Ridge(alpha=50.0),
    }

    best_name = None
    best_rmse = float("inf")
    for name, cand in candidates.items():
        cand.fit(X_train, y_train, sample_weight=w_train)
        preds = cand.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))
        logger.info(f"Candidate {name}: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}")
        if rmse < best_rmse:
            best_rmse = rmse
            best_name = name

    logger.info(f"Selected best model for Throws: {best_name} (RMSE: {best_rmse:.4f} vs Baseline: {baseline_test_rmse:.4f})")

    eval_model = candidates[best_name]
    preds_test = eval_model.predict(X_test)
    test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    test_mae = float(mean_absolute_error(y_test, preds_test))
    test_r2 = float(r2_score(y_test, preds_test))

    test_actual_o34 = (y_test > 34.5).astype(int)
    prob_o34_pred = [float(1.0 - poisson.cdf(34, max(15.0, mu))) for mu in preds_test]
    o34_acc = float((test_actual_o34 == (np.array(prob_o34_pred) > 0.5).astype(int)).mean() * 100)
    majority_o34 = max(test_actual_o34.mean(), 1 - test_actual_o34.mean()) * 100

    # Production Refit on 100% of data
    logger.info("Refitting winning architecture on 100% of played matches for production...")
    if best_name == "lgbm_shallow":
        prod_model = LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.02,
            n_estimators=60,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )
    else:
        prod_model = Ridge(alpha=50.0)

    prod_model.fit(X_all, y_all, sample_weight=weights_all)

    if hasattr(prod_model, "feature_importances_"):
        imps = prod_model.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        top_features = {feature_cols[i]: float(imps[i]) for i in sorted_idx[:10]}
    else:
        coefs = np.abs(prod_model.coef_)
        sorted_idx = np.argsort(coefs)[::-1]
        top_features = {feature_cols[i]: float(coefs[i]) for i in sorted_idx[:10]}

    metrics = {
        "model_type": f"Regularized {best_name.upper()} (Throws)",
        "selected_model": best_name,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_rmse": round(float(np.sqrt(mean_squared_error(y_train, eval_model.predict(X_train)))), 3),
        "train_mae": round(float(mean_absolute_error(y_train, eval_model.predict(X_train))), 3),
        "test_rmse": round(test_rmse, 3),
        "test_mae": round(test_mae, 3),
        "test_r2": round(test_r2, 3),
        "baseline_test_rmse": round(baseline_test_rmse, 3),
        "baseline_test_mae": round(baseline_test_mae, 3),
        "beats_baseline": bool(test_rmse < baseline_test_rmse),
        "over_34_5_accuracy_pct": round(o34_acc, 2),
        "majority_baseline_pct": round(majority_o34, 2),
        "top_features": top_features,
    }

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    model_file = Path(model_output_dir) / "throws_model_v1.joblib"
    joblib.dump(
        {
            "model": prod_model,
            "feature_names": feature_cols,
            "feature_cols": feature_cols,
            "baseline_mean": baseline_pred,
            "metrics": metrics,
            "top_features": top_features,
        },
        model_file,
    )
    logger.info(f"Model saved to {model_file}")

    return metrics


if __name__ == "__main__":
    train_throws_model()
