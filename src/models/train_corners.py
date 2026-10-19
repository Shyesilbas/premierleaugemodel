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

from lightgbm import LGBMRegressor
from sklearn.linear_model import ElasticNet, PoissonRegressor, Ridge
from src.models.model_utils import (
    chronological_regression_evaluation,
    evaluate_count_threshold,
    make_regression_pipeline,
)
from src.models.count_model import load_count_dataset, save_count_artifact, top_features_of, train_errors
from src.config import FEATURES_PATH, MODELS_DIR, configure_logging

logger = logging.getLogger("train_corners")

CURATED_FEATURES = [
    "home_corners_for_roll_10",
    "away_corners_for_roll_10",
    "home_corners_against_roll_10",
    "away_corners_against_roll_10",
    "home_corners_for_roll_5",
    "away_corners_for_roll_5",
    "home_shots_for_roll_5",
    "away_shots_for_roll_5",
    "home_touches_in_opp_box_roll_5",
    "away_touches_in_opp_box_roll_5",
]


def train_corners_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    target_col = "total_corners"
    df, X_all, y_all, partial_seasons = load_count_dataset(data_path, target_col, CURATED_FEATURES, "Corner", logger)
    feature_cols = list(CURATED_FEATURES)

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
            f"ridge_{alpha:g}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in (1.0, 10.0, 50.0, 100.0, 250.0, 500.0)
        },
        **{
            f"poisson_{alpha:g}": make_regression_pipeline(
                PoissonRegressor(alpha=alpha, max_iter=2000), scale=True
            )
            for alpha in (1.0, 10.0, 50.0, 200.0)
        },
        **{
            f"elastic_{alpha}_{l1}": make_regression_pipeline(
                ElasticNet(alpha=alpha, l1_ratio=l1, max_iter=2000), scale=True
            )
            for alpha in (0.05, 0.1, 0.5) for l1 in (0.2, 0.5, 0.8)
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

    top_features = top_features_of(prod_model, feature_cols)

    metrics.update({
        "model_type": f"Chronological CV-selected {best_name} (Corners)",
        **train_errors(y_train, eval_model, X_train),
        "over_9_5_accuracy_pct": round(o95_acc, 2),
        "majority_baseline_pct": round(majority_o95, 2),
        "count_threshold_metrics": {f"over_{threshold}_5": result for threshold, result in threshold_results.items()},
        "top_features": top_features,
    })

    save_count_artifact(
        model_output_dir, "corner_model_v1.joblib", prod_model, feature_cols, metrics, y_all, top_features
    )
    logger.info("Model saved to %s", Path(model_output_dir) / "corner_model_v1.joblib")

    return metrics


if __name__ == "__main__":
    configure_logging()
    train_corners_model()
