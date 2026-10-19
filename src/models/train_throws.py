#!/usr/bin/env python3
"""
Throws Prediction Model (Regularized Regression & Count Probabilities)
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
from lightgbm import LGBMRegressor
from sklearn.linear_model import PoissonRegressor, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from src.models.model_utils import (
    chronological_regression_evaluation,
    estimate_count_dispersion,
    evaluate_count_threshold,
    final_estimator,
    incomplete_seasons,
    make_regression_pipeline,
)
from src.config import FEATURES_PATH, MODELS_DIR, configure_logging

logger = logging.getLogger("train_throws")

CURATED_FEATURES = [
    "home_throws_roll_5",
    "home_throws_roll_10",
    "away_throws_roll_10",
    "home_opponent_throws_roll_10",
    "away_opponent_throws_roll_5",
    "away_opponent_throws_roll_10",
    "exp_home_throws_5",
    "exp_away_throws_5",
    "home_possession_roll_5",
    "away_possession_roll_5",
    "home_pass_pct_roll_10",
    "away_pass_pct_roll_10",
    "home_inacc_fwd_pass_roll_10",
    "away_inacc_fwd_pass_roll_10",
]


def train_throws_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")
    partial_seasons = incomplete_seasons(df)

    target_col = "total_throws"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "is_played" in df.columns:
        df = df[df["is_played"]].copy()

    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with throws data.")

    missing_features = [c for c in CURATED_FEATURES if c not in df.columns]
    if missing_features:
        raise ValueError(f"Throws model features missing from dataset: {missing_features}")
    feature_cols = list(CURATED_FEATURES)
    logger.info(f"Selected {len(feature_cols)} curated features for Throws model.")

    X_all = df[feature_cols].copy()
    y_all = df[target_col].astype(float)

    candidates = {
        "lgbm_shallow": make_regression_pipeline(LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.02,
            n_estimators=60,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )),
        **{
            f"ridge_{alpha}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in (1.0, 10.0, 50.0, 100.0, 500.0)
        },
        **{
            f"poisson_{alpha:g}": make_regression_pipeline(
                PoissonRegressor(alpha=alpha, max_iter=2000), scale=True
            )
            for alpha in (1.0, 10.0, 50.0, 200.0)
        },
    }

    best_name, eval_model, prod_model, metrics, preds_test, y_test = chronological_regression_evaluation(
        X_all, y_all, candidates, df.get("season"), partial_seasons
    )
    split_idx = metrics["train_samples"]
    X_train, y_train = X_all.iloc[:split_idx], y_all.iloc[:split_idx]
    logger.info("Selected %s by development-period time-series CV", best_name)

    alpha_dev = metrics["count_dispersion_alpha_dev"]
    threshold_result = evaluate_count_threshold(y_train, y_test, preds_test, 34, alpha_dev)
    o34_acc = threshold_result["negative_binomial"]["accuracy_pct"]
    majority_o34 = threshold_result["majority_accuracy_pct"]

    fitted_estimator = final_estimator(prod_model)
    if hasattr(fitted_estimator, "feature_importances_"):
        imps = fitted_estimator.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        top_features = {feature_cols[i]: float(imps[i]) for i in sorted_idx[:10]}
    elif hasattr(fitted_estimator, "coef_"):
        coefs = np.abs(fitted_estimator.coef_)
        sorted_idx = np.argsort(coefs)[::-1]
        top_features = {feature_cols[i]: float(coefs[i]) for i in sorted_idx[:10]}
    else:
        top_features = {}

    metrics.update({
        "model_type": f"Chronological CV-selected {best_name} (Throws)",
        "train_rmse": round(float(mean_squared_error(y_train, eval_model.predict(X_train)) ** 0.5), 4),
        "train_mae": round(float(mean_absolute_error(y_train, eval_model.predict(X_train))), 4),
        "over_34_5_accuracy_pct": round(o34_acc, 2),
        "majority_baseline_pct": round(majority_o34, 2),
        "count_threshold_metrics": {"over_34_5": threshold_result},
        "top_features": top_features,
    })

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    model_file = Path(model_output_dir) / "throws_model_v1.joblib"
    joblib.dump(
        {
            "model": prod_model,
            "feature_names": feature_cols,
            "feature_cols": feature_cols,
            "baseline_mean": metrics["baseline_mean"],
            "count_dispersion_alpha": estimate_count_dispersion(y_all),
            "metrics": metrics,
            "top_features": top_features,
        },
        model_file,
    )
    logger.info(f"Model saved to {model_file}")

    return metrics


if __name__ == "__main__":
    configure_logging()
    train_throws_model()
