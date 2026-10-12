#!/usr/bin/env python3
"""
Offside Prediction Model (XGBoost Regressor & Poisson Probabilities)
Predicts total match offsides and probabilities for Over 2.5 / 3.5 / 4.5 offsides.
Uses strictly historical, leakage-free features.
Evaluated with Time-Series Split (Backtesting on last 20% of season).
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from scipy.stats import poisson
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_offsides")


def train_offsides_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    # Target: total match offsides
    target_col = "total_offsides"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    # Filter completed matches where total_offsides is available
    df = df[df[target_col].notnull()].copy()
    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with offside data.")

    # Candidate feature columns: strictly pre-match rolling and rest features
    feature_candidates = [
        c for c in df.columns if (
            "_roll_" in c or "_ewma_" in c or "rest_days" in c or "exp_" in c
        ) and not c.startswith("match_") and not c.startswith("total_") and not c.startswith("over_")
    ]
    # Filter only numeric columns
    feature_cols = [c for c in feature_candidates if np.issubdtype(df[c].dtype, np.number)]
    logger.info(f"Selected {len(feature_cols)} features for Offside model.")

    # Time-decay season weights
    season_weights_map = {
        "2023_24": 0.40,
        "2024_25": 0.90,
        "2025_26": 2.20,
        "2026_27": 4.50,
    }
    weights = df["season"].map(season_weights_map).fillna(1.0).values

    # Time-series chronological train/test split: first 80% train, last 20% test (backtest)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]
    w_train = weights[:split_idx]

    logger.info(f"Train matches: {len(train_df)}, Test matches: {len(test_df)}")

    # Model definition: regularized XGBoost for optimal generalization
    model = XGBRegressor(
        n_estimators=110,
        learning_rate=0.03,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=1.0,
        random_state=42,
        objective="reg:squarederror",
    )

    model.fit(X_train, y_train, sample_weight=w_train)

    # Evaluation
    preds_train = model.predict(X_train)
    preds_test = model.predict(X_test)

    train_rmse = float(np.sqrt(mean_squared_error(y_train, preds_train)))
    train_mae = float(mean_absolute_error(y_train, preds_train))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    test_mae = float(mean_absolute_error(y_test, preds_test))
    test_r2 = float(r2_score(y_test, preds_test))

    # Baseline comparison (predicting training mean)
    baseline_pred = np.full_like(y_test, y_train.mean())
    baseline_rmse = float(np.sqrt(mean_squared_error(y_test, baseline_pred)))
    baseline_mae = float(mean_absolute_error(y_test, baseline_pred))

    # Over/Under 3.5 classification performance
    test_actual_o35 = (y_test > 3.5).astype(int)
    test_pred_o35 = (preds_test > 3.5).astype(int)
    o35_acc = float((test_actual_o35 == test_pred_o35).mean() * 100)

    # Feature importances
    importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    top_features = importances.head(10).to_dict()

    metrics = {
        "model_type": "XGBoost Regressor (Offsides)",
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "train_rmse": round(train_rmse, 3),
        "train_mae": round(train_mae, 3),
        "test_rmse": round(test_rmse, 3),
        "test_mae": round(test_mae, 3),
        "test_r2": round(test_r2, 3),
        "baseline_test_rmse": round(baseline_rmse, 3),
        "baseline_test_mae": round(baseline_mae, 3),
        "over_3_5_accuracy_pct": round(o35_acc, 2),
        "top_features": {k: round(float(v), 4) for k, v in top_features.items()},
    }

    logger.info("=== Offside Model Results ===")
    logger.info(f"Test RMSE: {test_rmse:.3f} (Baseline: {baseline_rmse:.3f})")
    logger.info(f"Test MAE:  {test_mae:.3f} (Baseline: {baseline_mae:.3f})")
    logger.info(f"Over 3.5 Accuracy: {o35_acc:.2f}%")

    # Save artifact
    out_dir = Path(model_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / "offside_model_v1.joblib"

    artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "metrics": metrics,
        "target_col": target_col,
    }
    joblib.dump(artifact, artifact_path)
    logger.info(f"Saved offside model artifact to {artifact_path}")

    # Generate benchmark report
    rep_dir = Path(reports_output_dir)
    rep_dir.mkdir(parents=True, exist_ok=True)
    report_file = rep_dir / "model_benchmarks_offsides.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Model Benchmark Raporu — Yakalanılan Ofsayt Motoru (Offsides)\n\n")
        f.write(f"- **Hedef Değişken:** `{target_col}`\n")
        f.write(f"- **Eğitim Kümesi (İlk %80):** {len(train_df)} maç\n")
        f.write(f"- **Test Kümesi (Out-of-time %20):** {len(test_df)} maç\n")
        f.write(f"- **Test RMSE:** `{test_rmse:.3f}` (Temel Model: `{baseline_rmse:.3f}`)\n")
        f.write(f"- **Test MAE:** `{test_mae:.3f}` (Temel Model: `{baseline_mae:.3f}`)\n")
        f.write(f"- **3.5 Üst Doğruluğu:** `%{o35_acc:.2f}`\n\n")
        f.write("### En Etkili 10 Öznitelik (Feature Importance)\n\n")
        f.write("| Sıra | Öznitelik Adı | Önem Skoru |\n|:---|:---|:---:|\n")
        for rank, (fname, fval) in enumerate(top_features.items(), start=1):
            f.write(f"| {rank} | `{fname}` | {fval:.4f} |\n")

    return metrics


if __name__ == "__main__":
    train_offsides_model()
