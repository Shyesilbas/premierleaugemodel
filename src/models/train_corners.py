#!/usr/bin/env python3
"""
Corner Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match corners and probabilities for Over 8.5 / 9.5 / 10.5 corners.
Uses strictly curated, domain-relevant features (corners, shots, possession, box entries).
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_corners")

CURATED_FEATURES = [
    "home_corners_for_roll_3",
    "home_corners_for_roll_5",
    "home_corners_for_roll_10",
    "away_corners_for_roll_3",
    "away_corners_for_roll_5",
    "away_corners_for_roll_10",
    "home_corners_against_roll_5",
    "away_corners_against_roll_5",
    "home_shots_for_roll_5",
    "away_shots_for_roll_5",
    "home_shots_against_roll_5",
    "away_shots_against_roll_5",
    "exp_match_corners_5",
    "exp_home_corners_5",
    "exp_away_corners_5",
    "home_possession_roll_5",
    "away_possession_roll_5",
    "home_touches_in_opp_box_roll_5",
    "away_touches_in_opp_box_roll_5",
]


def train_corners_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")
    partial_seasons = incomplete_seasons(df)

    target_col = "total_corners"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "is_played" in df.columns:
        df = df[df["is_played"]].copy()

    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with corner data.")

    missing_features = [c for c in CURATED_FEATURES if c not in df.columns]
    if missing_features:
        raise ValueError(f"Corner model features missing from dataset: {missing_features}")
    feature_cols = list(CURATED_FEATURES)
    logger.info(f"Selected {len(feature_cols)} curated features for Corner model.")

    X_all = df[feature_cols].copy()
    y_all = df[target_col].astype(float)

    # Candidates comparison
    candidates = {
        "lgbm_shallow": make_regression_pipeline(LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.02,
            n_estimators=55,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )),
        **{
            f"ridge_{alpha}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in (1.0, 10.0, 50.0, 100.0)
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

    # Threshold probabilities use an NB2 dispersion estimate fitted on development data.
    alpha_dev = metrics["count_dispersion_alpha_dev"]
    threshold_results = {
        threshold: evaluate_count_threshold(y_train, y_test, preds_test, threshold, alpha_dev)
        for threshold in (8, 9, 10)
    }
    o95_acc = threshold_results[9]["negative_binomial"]["accuracy_pct"]
    majority_o95 = threshold_results[9]["majority_accuracy_pct"]

    # Top features
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
        "model_type": f"Chronological CV-selected {best_name} (Corners)",
        "train_rmse": round(float(mean_squared_error(y_train, eval_model.predict(X_train)) ** 0.5), 4),
        "train_mae": round(float(mean_absolute_error(y_train, eval_model.predict(X_train))), 4),
        "over_9_5_accuracy_pct": round(o95_acc, 2),
        "majority_baseline_pct": round(majority_o95, 2),
        "count_threshold_metrics": {f"over_{threshold}_5": result for threshold, result in threshold_results.items()},
        "top_features": top_features,
    })

    # Save model and artifacts
    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    model_file = Path(model_output_dir) / "corner_model_v1.joblib"
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
    train_corners_model()
