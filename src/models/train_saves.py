#!/usr/bin/env python3
"""
Goalkeeper Saves Prediction Model (XGBoost Regressor)
Predicts total match goalkeeper saves and per-team saves.
Uses strictly historical, leakage-free features (shots conceded rolling averages, saves EWMA).
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_saves")


def train_saves_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        data_path = "data/processed/features_matches_2024_25.parquet"

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    target_col = "total_saves"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)

    feature_candidates = [
        c for c in df.columns if (
            "_roll_" in c or "_ewma_" in c or "rest_days" in c or "exp_" in c
        ) and not c.startswith("match_") and not c.startswith("total_") and not c.startswith("over_")
    ]
    feature_cols = [c for c in feature_candidates if np.issubdtype(df[c].dtype, np.number)]
    logger.info(f"Selected {len(feature_cols)} features for Saves model.")

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]

    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        objective="reg:squarederror",
    )

    model.fit(X_train, y_train)

    preds_train = model.predict(X_train)
    preds_test = model.predict(X_test)

    train_rmse = float(np.sqrt(mean_squared_error(y_train, preds_train)))
    train_mae = float(mean_absolute_error(y_train, preds_train))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    test_mae = float(mean_absolute_error(y_test, preds_test))
    test_r2 = float(r2_score(y_test, preds_test))

    baseline_pred = np.full_like(y_test, y_train.mean())
    baseline_rmse = float(np.sqrt(mean_squared_error(y_test, baseline_pred)))
    baseline_mae = float(mean_absolute_error(y_test, baseline_pred))

    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    top_features = importances.head(10).to_dict()

    metrics = {
        "model_type": "XGBoost Regressor (Saves)",
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "train_rmse": round(train_rmse, 3),
        "train_mae": round(train_mae, 3),
        "test_rmse": round(test_rmse, 3),
        "test_mae": round(test_mae, 3),
        "test_r2": round(test_r2, 3),
        "baseline_test_rmse": round(baseline_rmse, 3),
        "baseline_test_mae": round(baseline_mae, 3),
        "top_features": top_features,
    }

    logger.info("=== Saves Model Metrics ===")
    logger.info(f"Test RMSE: {test_rmse:.3f} (Baseline: {baseline_rmse:.3f})")
    logger.info(f"Test MAE: {test_mae:.3f} (Baseline: {baseline_mae:.3f})")

    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    model_file = Path(model_output_dir) / "saves_model_v1.joblib"
    joblib.dump({"model": model, "feature_names": feature_cols, "metrics": metrics}, model_file)
    logger.info(f"Model saved to {model_file}")

    return metrics


if __name__ == "__main__":
    train_saves_model()
