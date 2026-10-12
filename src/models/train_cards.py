#!/usr/bin/env python3
"""
Premier League Cards Prediction Model (Regularized LightGBM & Poisson Probabilities)
Predicts total match cards (Yellow + Red) and probabilities for Over 3.5 / 4.5 cards.
Uses curated, leakage-free discipline features, referee metrics (NO raw IDs), and gentle time weighting.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from scipy.stats import poisson
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("train_cards")

CURATED_FEATURES = [
    "home_cards_for_roll_3",
    "home_cards_for_roll_5",
    "home_cards_for_roll_10",
    "away_cards_for_roll_3",
    "away_cards_for_roll_5",
    "away_cards_for_roll_10",
    "home_cards_against_roll_5",
    "away_cards_against_roll_5",
    "home_fouls_committed_roll_5",
    "away_fouls_committed_roll_5",
    "home_fouls_drawn_roll_5",
    "away_fouls_drawn_roll_5",
    "exp_match_cards_5",
    "exp_home_cards_5",
    "exp_away_cards_5",
    "referee_avg_cards",
    "referee_avg_fouls",
]


def train_cards_model(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
    reports_output_dir: str = "reports",
) -> Dict[str, Any]:
    if not Path(data_path).exists():
        data_path = "data/processed/features_matches_2024_25.parquet"

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded featured dataset with {len(df)} matches.")

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

    feature_cols = [c for c in CURATED_FEATURES if c in df.columns]
    logger.info(f"Selected {len(feature_cols)} curated features for Cards model: {feature_cols}")

    # Fill missing with column means
    X_all = df[feature_cols].fillna(df[feature_cols].mean())
    y_all = df[target_col].astype(float)

    # Gentle time-decay weights: 0.65 to 1.20 linearly over history
    weights_all = np.linspace(0.65, 1.20, len(df))

    # Time-series chronological train/test split: first 80% train, last 20% test
    split_idx = int(len(df) * 0.8)
    X_train, y_train = X_all.iloc[:split_idx], y_all.iloc[:split_idx]
    X_test, y_test = X_all.iloc[split_idx:], y_all.iloc[split_idx:]
    w_train = weights_all[:split_idx]

    logger.info(f"Train matches: {len(X_train)}, Test matches: {len(X_test)}")

    # Baseline comparison (predicting train mean)
    baseline_pred = float(np.average(y_train, weights=w_train))
    baseline_test_rmse = float(np.sqrt(mean_squared_error(y_test, np.full_like(y_test, baseline_pred))))
    baseline_test_mae = float(mean_absolute_error(y_test, np.full_like(y_test, baseline_pred)))

    # Candidates comparison
    candidates = {
        "lgbm_shallow": LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.03,
            n_estimators=50,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        ),
        "ridge_100": Ridge(alpha=100.0),
    }

    best_name = None
    best_rmse = float("inf")
    candidate_metrics = {}

    for name, cand in candidates.items():
        cand.fit(X_train, y_train, sample_weight=w_train)
        preds = cand.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae = float(mean_absolute_error(y_test, preds))
        r2 = float(r2_score(y_test, preds))
        candidate_metrics[name] = {"rmse": rmse, "mae": mae, "r2": r2}
        logger.info(f"Candidate {name}: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}")
        if rmse < best_rmse:
            best_rmse = rmse
            best_name = name

    logger.info(f"Selected best model for Cards: {best_name} (RMSE: {best_rmse:.4f} vs Baseline: {baseline_test_rmse:.4f})")

    # Evaluate best candidate on test set
    eval_model = candidates[best_name]
    preds_test = eval_model.predict(X_test)
    test_rmse = float(np.sqrt(mean_squared_error(y_test, preds_test)))
    test_mae = float(mean_absolute_error(y_test, preds_test))
    test_r2 = float(r2_score(y_test, preds_test))

    # Over 3.5 & Over 4.5 Cards classification accuracy
    prob_o35_pred = [float(1.0 - poisson.cdf(3, max(0.5, mu))) for mu in preds_test]
    actual_o35 = (y_test > 3.5).astype(int).values
    o35_acc = float(np.mean((np.array(prob_o35_pred) > 0.5) == actual_o35) * 100)

    prob_o45_pred = [float(1.0 - poisson.cdf(4, max(0.5, mu))) for mu in preds_test]
    actual_o45 = (y_test > 4.5).astype(int).values
    o45_acc = float(np.mean((np.array(prob_o45_pred) > 0.5) == actual_o45) * 100)

    majority_o35 = max(actual_o35.mean(), 1 - actual_o35.mean()) * 100

    # Production Refit: Train selected architecture on 100% of all played matches
    logger.info("Refitting winning architecture on 100% of played matches for production...")
    if best_name == "lgbm_shallow":
        prod_model = LGBMRegressor(
            max_depth=3,
            num_leaves=7,
            learning_rate=0.03,
            n_estimators=50,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=-1,
        )
    else:
        prod_model = Ridge(alpha=100.0)

    prod_model.fit(X_all, y_all, sample_weight=weights_all)

    # Feature importances / coefficients
    if hasattr(prod_model, "feature_importances_"):
        imps = prod_model.feature_importances_
        sorted_idx = np.argsort(imps)[::-1]
        top_features = [{"feature": feature_cols[i], "importance": float(imps[i])} for i in sorted_idx[:10]]
    else:
        coefs = np.abs(prod_model.coef_)
        sorted_idx = np.argsort(coefs)[::-1]
        top_features = [{"feature": feature_cols[i], "importance": float(coefs[i])} for i in sorted_idx[:10]]

    metrics = {
        "selected_model": best_name,
        "test_rmse": round(test_rmse, 3),
        "test_mae": round(test_mae, 3),
        "test_r2": round(test_r2, 3),
        "baseline_rmse": round(baseline_test_rmse, 3),
        "baseline_mae": round(baseline_test_mae, 3),
        "beats_baseline": bool(test_rmse < baseline_test_rmse),
        "o35_accuracy": round(o35_acc, 2),
        "o35_majority_baseline": round(majority_o35, 2),
        "o45_accuracy": round(o45_acc, 2),
    }

    # Save artifact
    out_dir = Path(model_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / "cards_model_v1.joblib"

    artifact = {
        "model": prod_model,
        "feature_cols": feature_cols,
        "feature_names": feature_cols,
        "baseline_mean": baseline_pred,
        "target_col": target_col,
        "metrics": metrics,
        "top_features": top_features,
    }
    joblib.dump(artifact, artifact_path)
    logger.info(f"Saved production cards model artifact to {artifact_path}")

    # Generate benchmark report
    rep_dir = Path(reports_output_dir)
    rep_dir.mkdir(parents=True, exist_ok=True)
    report_md = rep_dir / "model_benchmarks_cards.md"

    feat_rows = "\n".join([f"| {i+1} | `{f['feature']}` | {f['importance']:.4f} |" for i, f in enumerate(top_features)])
    report_content = f"""# Model Benchmark Raporu — Toplam Kart Tahmin Motoru (Cards)

- **Hedef Değişken:** `{target_col}` (Sarı + Kırmızı Kart)
- **Seçilen Model:** `{best_name}` (Tüm veriyle yeniden eğitildi)
- **Öznitelik Sayısı:** {len(feature_cols)} (Gürültüsüz, alan odaklı, `referee_id` çıkarıldı)
- **Test RMSE:** `{test_rmse:.3f}` (Temel Model: `{baseline_test_rmse:.3f}`) — {'✅ Baseline Geçildi' if test_rmse < baseline_test_rmse else '❌'}
- **Test MAE:** `{test_mae:.3f}` (Temel Model: `{baseline_test_mae:.3f}`)
- **3.5 Üst Doğruluğu:** `%{o35_acc:.2f}` (Çoğunluk Kuralı: `%{majority_o35:.2f}`)
- **4.5 Üst Doğruluğu:** `%{o45_acc:.2f}`

### En Etkili Öznitelikler
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
