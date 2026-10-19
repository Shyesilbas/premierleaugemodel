#!/usr/bin/env python3
"""
Goalkeeper Saves Prediction Model (Regularized Ridge & Baseline Shrinkage)
Predicts total match goalkeeper saves.
Uses strictly curated, domain-relevant features (shots conceded, shots on target conceded, xG against).
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
    make_regression_pipeline,
)
from src.models.count_model import load_count_dataset, save_count_artifact, top_features_of, train_errors
from src.config import FEATURES_PATH, MODELS_DIR, configure_logging

logger = logging.getLogger("train_saves")

CURATED_FEATURES = [
    "home_saves_roll_3",
    "home_saves_roll_5",
    "home_saves_roll_10",
    "away_saves_roll_3",
    "away_saves_roll_5",
    "away_saves_roll_10",
    "home_shots_against_roll_5",
    "away_shots_against_roll_5",
    "home_shots_ontarget_against_roll_5",
    "away_shots_ontarget_against_roll_5",
    "home_shots_for_roll_5",
    "away_shots_for_roll_5",
    "exp_match_shots_5",
]


def train_saves_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    target_col = "total_saves"
    df, X_all, y_all, partial_seasons = load_count_dataset(data_path, target_col, CURATED_FEATURES, "Saves", logger)
    feature_cols = list(CURATED_FEATURES)

    candidates = {
        **{
            f"ridge_{alpha:g}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in (0.1, 1.0, 10.0, 50.0, 100.0, 500.0, 1000.0)
        },
        **{
            f"poisson_{alpha:g}": make_regression_pipeline(
                PoissonRegressor(alpha=alpha, max_iter=2000), scale=True
            )
            for alpha in (1.0, 10.0, 50.0, 200.0)
        },
        "lgbm_shallow": make_regression_pipeline(LGBMRegressor(
            max_depth=2,
            num_leaves=4,
            learning_rate=0.02,
            n_estimators=40,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )),
    }

    best_name, eval_model, prod_model, metrics, preds_test, y_test = chronological_regression_evaluation(
        X_all, y_all, candidates, df.get("season"), partial_seasons
    )
    split_idx = metrics["train_samples"]
    X_train, y_train = X_all.iloc[:split_idx], y_all.iloc[:split_idx]
    logger.info("Selected %s by development-period time-series CV", best_name)

    top_features = top_features_of(prod_model, feature_cols)

    metrics.update({
        "model_type": f"Chronological CV-selected {best_name} (Saves)",
        **train_errors(y_train, eval_model, X_train),
        "top_features": top_features,
    })

    save_count_artifact(
        model_output_dir, "saves_model_v1.joblib", prod_model, feature_cols, metrics, y_all, top_features
    )
    logger.info("Model saved to %s", Path(model_output_dir) / "saves_model_v1.joblib")

    return metrics


if __name__ == "__main__":
    configure_logging()
    train_saves_model()
