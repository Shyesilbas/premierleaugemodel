#!/usr/bin/env python3
"""
Premier League Cards Prediction Model (XGBoost Regressor & Poisson Probabilities)
Predicts total match cards (Yellow + Red) and probabilities for Over 3.5 / 4.5 / 5.5 cards.
Incorporate strictly historical referee tendencies and time-decay season weighting.
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
logger = logging.getLogger("train_cards")

SEASON_WEIGHTS = {
    "2023_24": 0.40,
    "2024_25": 0.90,
    "2025_26": 2.20,
    "2026_27": 4.50,
}


def train_cards_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

    target_col = "total_cards"
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    df = df[df[target_col].notnull()].copy()
    if "kickoff_millis" in df.columns:
        df = df.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
    logger.info(f"Filtered {len(df)} completed matches with card data.")

    # Candidate feature columns
    feature_candidates = [
        c for c in df.columns if (
            "_roll_" in c or "_ewma_" in c or "rest_days" in c or "exp_" in c or "referee_" in c
        ) and not c.startswith("match_") and not c.startswith("total_") and not c.startswith("over_")
    ]
    feature_cols = [c for c in feature_candidates if np.issubdtype(df[c].dtype, np.number)]
    logger.info(f"Selected {len(feature_cols)} features for Cards model.")

    # Time-decay season weights
    weights = df["season"].map(SEASON_WEIGHTS).fillna(1.0).values

    # Time-series chronological train/test split: first 80% train, last 20% test
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    X_train, y_train = train_df[feature_cols], train_df[target_col]
    X_test, y_test = test_df[feature_cols], test_df[target_col]
    w_train = weights[:split_idx]

    logger.info(f"Train matches: {len(train_df)}, Test matches: {len(test_df)}")

    # Model definition
    model = XGBRegressor(
        n_estimators=140,
        learning_rate=0.035,
        max_depth=3,
        subsample=0.85,
        colsample_bytree=0.8,
        reg_alpha=0.2,
        reg_lambda=1.2,
        random_state=42,
        objective="reg:squarederror",
    )

    model.fit(X_train, y_train, sample_weight=w_train)

    # Evaluation
    preds_train = model.predict(X_train)
    preds_test = model.predict(X_test)

    # Metrics
    train_rmse = float(np.sqrt(mean_squared_error(y_train, preds_train)))
    train_mae = float(mean_absolute_error(y_train, preds_train))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    test_mae = float(mean_absolute_error(y_test, preds_test))

    # Baseline: Historical mean of train set
    baseline_pred = float(np.average(y_train, weights=w_train))
    baseline_test_rmse = float(np.sqrt(mean_squared_error(y_test, [baseline_pred] * len(y_test))))
    baseline_test_mae = float(mean_absolute_error(y_test, [baseline_pred] * len(y_test)))

    # Poisson probabilities for Over 3.5 and Over 4.5
    prob_o35_pred = [float(1.0 - poisson.cdf(3.5, mu)) for mu in preds_test]
    actual_o35 = (y_test > 3.5).astype(int).values
    o35_acc = float(np.mean((np.array(prob_o35_pred) > 0.5) == actual_o35) * 100)

    prob_o45_pred = [float(1.0 - poisson.cdf(4.5, mu)) for mu in preds_test]
    actual_o45 = (y_test > 4.5).astype(int).values
    o45_acc = float(np.mean((np.array(prob_o45_pred) > 0.5) == actual_o45) * 100)

    logger.info(f"Test RMSE: {test_rmse:.3f} (Baseline: {baseline_test_rmse:.3f})")
    logger.info(f"Test MAE: {test_mae:.3f} (Baseline: {baseline_test_mae:.3f})")
    logger.info(f"Over 3.5 Cards Accuracy: {o35_acc:.2f}%")
    logger.info(f"Over 4.5 Cards Accuracy: {o45_acc:.2f}%")

    # Feature Importance
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    top_features = [
        {"feature": feature_cols[i], "importance": float(importances[i])}
        for i in sorted_idx[:15]
    ]

    # Save artifact
    out_dir = Path(model_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / "cards_model_v1.joblib"

    artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "baseline_mean": baseline_pred,
        "target_col": target_col,
        "season_weights": SEASON_WEIGHTS,
        "metrics": {
            "test_rmse": test_rmse,
            "test_mae": test_mae,
            "baseline_rmse": baseline_test_rmse,
            "baseline_mae": baseline_test_mae,
            "o35_accuracy": o35_acc,
            "o45_accuracy": o45_acc,
        },
        "top_features": top_features,
    }
    joblib.dump(artifact, artifact_path)
    logger.info(f"Saved production cards model artifact to {artifact_path}")

    # Save benchmark markdown report
    rep_dir = Path(reports_output_dir)
    rep_dir.mkdir(parents=True, exist_ok=True)
    report_md = rep_dir / "model_benchmarks_cards.md"

    feat_rows = "\n".join([f"| {i+1} | `{f['feature']}` | {f['importance']:.4f} |" for i, f in enumerate(top_features[:10])])

    report_content = f"""# Model Benchmark Raporu — Toplam Kart Tahmin Motoru (Cards)

- **Hedef Değişken:** `{target_col}` (Sarı + Kırmızı Kart)
- **Eğitim Kümesi (İlk %80):** {len(train_df)} maç (2023-24, 2024-25, 2025-26, 2026-27 zaman ağırlıklı)
- **Test Kümesi (Out-of-time %20):** {len(test_df)} maç
- **Sezon Ağırlıkları:** 2026-27: 4.50 | 2025-26: 2.20 | 2024-25: 0.90 | 2023-24: 0.40
- **Test RMSE:** `{test_rmse:.3f}` (Temel Model: `{baseline_test_rmse:.3f}`)
- **Test MAE:** `{test_mae:.3f}` (Temel Model: `{baseline_test_mae:.3f}`)
- **3.5 Üst Doğruluğu:** `%{o35_acc:.2f}`
- **4.5 Üst Doğruluğu:** `%{o45_acc:.2f}`

### En Etkili 10 Öznitelik (Feature Importance)

| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
{feat_rows}
"""
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Generated benchmark report at {report_md}")

    return artifact


if __name__ == "__main__":
    train_cards_model()
