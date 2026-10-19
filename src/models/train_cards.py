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

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import ElasticNet, PoissonRegressor, Ridge
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
    if not Path(data_path).exists():
        raise FileNotFoundError(f"Feature dataset not found: {data_path}. Run the full pipeline to rebuild it.")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")
    partial_seasons = incomplete_seasons(df)

    target_col = "total_cards"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    # Filter completed matches where total_cards is available
    df = df[df[target_col].notnull()].copy()
    if "is_played" in df.columns:
        df = df[df["is_played"]].copy()

    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with card data.")

    missing_features = [c for c in CURATED_FEATURES if c not in df.columns]
    if missing_features:
        raise ValueError(f"Cards model features missing from dataset: {missing_features}")
    feature_cols = list(CURATED_FEATURES)
    logger.info(f"Selected {len(feature_cols)} curated features for Cards model: {feature_cols}")

    X_all = df[feature_cols].copy()
    y_all = df[target_col].astype(float)

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

    # Feature importances / coefficients
    fitted_estimator = final_estimator(prod_model)
    if hasattr(fitted_estimator, "feature_importances_"):
        imps = fitted_estimator.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        top_features = [{"feature": feature_cols[i], "importance": float(imps[i])} for i in sorted_idx[:10]]
    elif hasattr(fitted_estimator, "coef_"):
        coefs = np.abs(fitted_estimator.coef_)
        sorted_idx = np.argsort(coefs)[::-1]
        top_features = [{"feature": feature_cols[i], "importance": float(coefs[i])} for i in sorted_idx[:10]]
    else:
        top_features = []

    metrics.update({
        "train_rmse": round(float(mean_squared_error(y_train, eval_model.predict(X_train)) ** 0.5), 4),
        "train_mae": round(float(mean_absolute_error(y_train, eval_model.predict(X_train))), 4),
        "o35_accuracy": round(o35_acc, 2),
        "o35_majority_baseline": round(majority_o35, 2),
        "o45_accuracy": round(o45_acc, 2),
        "count_threshold_metrics": {"over_3_5": threshold_35, "over_4_5": threshold_45},
        "top_features": top_features,
    })

    # Save artifact
    out_dir = Path(model_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / "cards_model_v1.joblib"

    artifact = {
        "model": prod_model,
        "feature_cols": feature_cols,
        "feature_names": feature_cols,
        "baseline_mean": metrics["baseline_mean"],
        "count_dispersion_alpha": estimate_count_dispersion(y_all),
        "target_col": target_col,
        "metrics": metrics,
        "top_features": top_features,
    }
    joblib.dump(artifact, artifact_path)
    logger.info(f"Saved production cards model artifact to {artifact_path}")

    return artifact


if __name__ == "__main__":
    configure_logging()
    train_cards_model()
