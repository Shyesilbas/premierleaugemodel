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

from lightgbm import LGBMRegressor
from sklearn.linear_model import PoissonRegressor, Ridge
from src.models.model_utils import (
    chronological_regression_evaluation,
    evaluate_count_threshold,
    make_regression_pipeline,
)
from src.models.count_model import load_count_dataset, save_count_artifact, top_features_of, train_errors
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
    target_col = "total_throws"
    df, X_all, y_all, partial_seasons = load_count_dataset(data_path, target_col, CURATED_FEATURES, "Throws", logger)
    feature_cols = list(CURATED_FEATURES)

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

    top_features = top_features_of(prod_model, feature_cols)

    metrics.update({
        "model_type": f"Chronological CV-selected {best_name} (Throws)",
        **train_errors(y_train, eval_model, X_train),
        "over_34_5_accuracy_pct": round(o34_acc, 2),
        "majority_baseline_pct": round(majority_o34, 2),
        "count_threshold_metrics": {"over_34_5": threshold_result},
        "top_features": top_features,
    })

    save_count_artifact(
        model_output_dir, "throws_model_v1.joblib", prod_model, feature_cols, metrics, y_all, top_features
    )
    logger.info("Model saved to %s", Path(model_output_dir) / "throws_model_v1.joblib")

    return metrics


if __name__ == "__main__":
    configure_logging()
    train_throws_model()
