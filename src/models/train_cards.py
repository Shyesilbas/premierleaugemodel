#!/usr/bin/env python3
"""
Premier League Cards Prediction Model (Regularized Regression & Count Probabilities)
Predicts total match cards (Yellow + Red) and probabilities for Over 3.5 / 4.5 cards.
Uses curated pre-match discipline features and referee aggregates (no raw IDs).
Candidate selection uses expanding chronological folds; the final holdout is scored once.
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

logger = logging.getLogger("train_cards")

CURATED_FEATURES = [
    "home_cards_for_roll_5",
    "away_cards_for_roll_5",
    "home_cards_against_roll_5",
    "away_cards_against_roll_5",
    "home_fouls_committed_roll_5",
    "away_fouls_committed_roll_5",
    "home_fouls_drawn_roll_5",
    "away_fouls_drawn_roll_5",
    "abs_elo_diff",
    "referee_avg_cards",
    "referee_avg_fouls",
]


def train_cards_model(
    data_path: str = str(FEATURES_PATH),
    model_output_dir: str = str(MODELS_DIR),
) -> Dict[str, Any]:
    target_col = "total_cards"
    df, X_all, y_all, partial_seasons = load_count_dataset(data_path, target_col, CURATED_FEATURES, "Cards", logger)
    feature_cols = list(CURATED_FEATURES)

    # Candidates comparison
    candidates = {
        "lgbm_shallow": make_regression_pipeline(LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.03,
            n_estimators=50,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )),
        **{
            f"ridge_{alpha:g}": make_regression_pipeline(Ridge(alpha=alpha), scale=True)
            for alpha in (0.1, 1.0, 10.0, 50.0, 100.0, 250.0, 500.0)
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

    # Over 3.5 & Over 4.5 Cards classification accuracy
    alpha_dev = metrics["count_dispersion_alpha_dev"]
    threshold_35 = evaluate_count_threshold(y_train, y_test, preds_test, 3, alpha_dev)
    threshold_45 = evaluate_count_threshold(y_train, y_test, preds_test, 4, alpha_dev)
    o35_acc = threshold_35["negative_binomial"]["accuracy_pct"]
    o45_acc = threshold_45["negative_binomial"]["accuracy_pct"]
    majority_o35 = threshold_35["majority_accuracy_pct"]

    top_features = top_features_of(prod_model, feature_cols, as_records=True)

    metrics.update({
        **train_errors(y_train, eval_model, X_train),
        "o35_accuracy": round(o35_acc, 2),
        "o35_majority_baseline": round(majority_o35, 2),
        "o45_accuracy": round(o45_acc, 2),
        "count_threshold_metrics": {"over_3_5": threshold_35, "over_4_5": threshold_45},
        "top_features": top_features,
    })

    artifact = save_count_artifact(
        model_output_dir, "cards_model_v1.joblib", prod_model, feature_cols, metrics, y_all, top_features, target_col=target_col
    )
    logger.info("Saved production cards model artifact to %s", Path(model_output_dir) / "cards_model_v1.joblib")

    return artifact


if __name__ == "__main__":
    configure_logging()
    train_cards_model()
