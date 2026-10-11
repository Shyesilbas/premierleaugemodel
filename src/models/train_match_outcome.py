#!/usr/bin/env python3
"""
Match Outcome Prediction Models (1X2 & Over/Under 2.5 Goals)
Trains:
  1. Multi-class LightGBM Classifier for Match Outcome (H / D / A)
  2. Binary XGBoost Classifier for Over/Under 2.5 Goals
Evaluates accuracy, log-loss, Brier score, and benchmark baselines on the final 20% of the season.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss, classification_report
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_match_outcome")


def train_match_outcome_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        data_path = "data/processed/features_matches_2024_25.parquet"

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    # Target 1: Match outcome H (0), D (1), A (2)
    result_map = {"H": 0, "D": 1, "A": 2}
    df["target_1x2"] = df["match_result"].map(result_map)

    # Target 2: Over 2.5 Goals (0 / 1)
    df["target_o25"] = df["over_2_5_goals"]

    df = df[df["target_1x2"].notnull() & df["target_o25"].notnull()].copy()
    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)

    feature_candidates = [
        c for c in df.columns if (
            "_roll_" in c or "_ewma_" in c or "rest_days" in c or "exp_" in c
        ) and not c.startswith("match_") and not c.startswith("total_") and not c.startswith("target_") and not c.startswith("over_")
    ]
    feature_cols = [c for c in feature_candidates if np.issubdtype(df[c].dtype, np.number)]
    logger.info(f"Selected {len(feature_cols)} features for outcome models.")

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train, y_train_1x2, y_train_o25 = train_df[feature_cols], train_df["target_1x2"], train_df["target_o25"]
    X_test, y_test_1x2, y_test_o25 = test_df[feature_cols], test_df["target_1x2"], test_df["target_o25"]

    # 1. 1X2 Multi-class Model
    model_1x2 = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.03,
        num_leaves=15,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model_1x2.fit(X_train, y_train_1x2)

    probs_1x2 = model_1x2.predict_proba(X_test)
    preds_1x2 = model_1x2.predict(X_test)
    acc_1x2 = float(accuracy_score(y_test_1x2, preds_1x2) * 100)
    loss_1x2 = float(log_loss(y_test_1x2, probs_1x2))

    # Baseline 1X2 (predict most frequent outcome in training)
    train_most_frequent = y_train_1x2.mode()[0]
    baseline_acc_1x2 = float((y_test_1x2 == train_most_frequent).mean() * 100)

    # 2. Over/Under 2.5 Model
    model_o25 = XGBClassifier(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
    )
    model_o25.fit(X_train, y_train_o25)

    probs_o25 = model_o25.predict_proba(X_test)[:, 1]
    preds_o25 = model_o25.predict(X_test)
    acc_o25 = float(accuracy_score(y_test_o25, preds_o25) * 100)
    loss_o25 = float(log_loss(y_test_o25, probs_o25))
    brier_o25 = float(brier_score_loss(y_test_o25, probs_o25))

    baseline_o25_mode = y_train_o25.mode()[0]
    baseline_acc_o25 = float((y_test_o25 == baseline_o25_mode).mean() * 100)

    metrics = {
        "model_1x2": {
            "test_accuracy_pct": round(acc_1x2, 2),
            "baseline_accuracy_pct": round(baseline_acc_1x2, 2),
            "log_loss": round(loss_1x2, 3),
        },
        "model_over_2_5": {
            "test_accuracy_pct": round(acc_o25, 2),
            "baseline_accuracy_pct": round(baseline_acc_o25, 2),
            "log_loss": round(loss_o25, 3),
            "brier_score": round(brier_o25, 3),
        },
    }

    logger.info("=== Match Outcome Metrics ===")
    logger.info(f"1X2 Accuracy: {acc_1x2:.1f}% (Baseline: {baseline_acc_1x2:.1f}%), Log Loss: {loss_1x2:.3f}")
    logger.info(f"Over 2.5 Accuracy: {acc_o25:.1f}% (Baseline: {baseline_acc_o25:.1f}%), Brier: {brier_o25:.3f}")

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump({"model_1x2": model_1x2, "model_o25": model_o25, "feature_names": feature_cols, "metrics": metrics},
                Path(model_output_dir) / "outcome_models_v1.joblib")

    return metrics


if __name__ == "__main__":
    train_match_outcome_models()
