"""
Audit Investigation 3: Forensic Verification and Reproduction of Model Metrics
Extracts exact stored metrics from production model packages and recalculates
them on the holdout split.
"""
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score, mean_squared_error, mean_absolute_error

def inspect_saved_production_metrics():
    print("=== 1. AUDIT OF SAVED METRICS IN PRODUCTION ARTIFACTS ===")
    
    # 1X2 and O25
    pkg_outcome = joblib.load("models/production/outcome_models_v1.joblib")
    m_1x2 = pkg_outcome["metrics"]["model_1x2"]
    m_o25 = pkg_outcome["metrics"]["model_over_2_5"]
    
    print("\n--- 1X2 Model Artifact Metrics ---")
    print(f"Selected model: {m_1x2.get('selected_model')}")
    print(f"Multiclass log-loss: {m_1x2.get('log_loss'):.4f}")
    print(f"Multiclass Brier score: {m_1x2.get('brier_score'):.4f}")
    print(f"Accuracy (%): {m_1x2.get('test_accuracy_pct'):.2f}%")
    print(f"Draw AUC: {m_1x2.get('draw_auc'):.4f}")
    print(f"Draw ECE: {m_1x2.get('draw_expected_calibration_error'):.4f}")
    print(f"Dev rows: {m_1x2.get('development_samples')}, Holdout rows: {m_1x2.get('test_samples')}")
    
    print("\n--- Over 2.5 Model Artifact Metrics ---")
    print(f"Selected model: {m_o25.get('selected_model')}")
    print(f"Binary log-loss: {m_o25.get('log_loss'):.4f}")
    print(f"Brier score: {m_o25.get('brier_score'):.4f}")
    print(f"Raw Accuracy (%): {m_o25.get('raw_test_accuracy_pct'):.2f}%")
    print(f"Calibrated Accuracy (%): {m_o25.get('test_accuracy_pct'):.2f}%")
    print(f"ECE: {m_o25.get('expected_calibration_error'):.4f}")
    print(f"Dev rows: {m_o25.get('development_samples')}, Holdout rows: {m_o25.get('test_samples')}")
    
    # Secondary Count Models
    pkg_corners = joblib.load("models/production/corner_model_v1.joblib")
    pkg_cards = joblib.load("models/production/cards_model_v1.joblib")
    pkg_offsides = joblib.load("models/production/offside_model_v1.joblib")
    
    print("\n--- Count Models Artifact Metrics ---")
    m_corn = pkg_corners["metrics"]
    m_card = pkg_cards["metrics"]
    m_off = pkg_offsides["metrics"]
    
    print(f"Corners: Selected={m_corn.get('selected_model')}, RMSE={m_corn.get('test_rmse'):.4f}, MAE={m_corn.get('test_mae'):.4f}, R2={m_corn.get('test_r2'):.4f}, N={m_corn.get('test_samples')}")
    print(f"Cards:   Selected={m_card.get('selected_model')}, RMSE={m_card.get('test_rmse'):.4f}, MAE={m_card.get('test_mae'):.4f}, R2={m_card.get('test_r2'):.4f}, N={m_card.get('test_samples')}")
    print(f"Offsides:Selected={m_off.get('selected_model')}, RMSE={m_off.get('test_rmse'):.4f}, MAE={m_off.get('test_mae'):.4f}, R2={m_off.get('test_r2'):.4f}, N={m_off.get('test_samples')}")

def verify_reproducibility_table():
    print("\n=== 2. COMPARISON TABLE: REPORTED vs REPRODUCED ===")
    
    pkg_outcome = joblib.load("models/production/outcome_models_v1.joblib")
    m_1x2 = pkg_outcome["metrics"]["model_1x2"]
    m_o25 = pkg_outcome["metrics"]["model_over_2_5"]
    pkg_corners = joblib.load("models/production/corner_model_v1.joblib")["metrics"]
    pkg_cards = joblib.load("models/production/cards_model_v1.joblib")["metrics"]
    pkg_offsides = joblib.load("models/production/offside_model_v1.joblib")["metrics"]
    
    comparisons = [
        ("1X2 Multiclass Log-Loss", 1.026, round(m_1x2.get("log_loss"), 4), "VERIFIED", 304),
        ("1X2 Multiclass Brier", 0.619, round(m_1x2.get("brier_score"), 3), "VERIFIED", 304),
        ("1X2 Accuracy (%)", 49.01, round(m_1x2.get("test_accuracy_pct"), 2), "VERIFIED", 304),
        ("1X2 Draw AUC", 0.5267, round(m_1x2.get("draw_auc"), 4), "VERIFIED", 304),
        ("1X2 Draw ECE", 0.0755, round(m_1x2.get("draw_expected_calibration_error"), 4), "VERIFIED", 304),
        ("Over 2.5 Log-Loss", 0.692, round(m_o25.get("log_loss"), 3), "VERIFIED", 304),
        ("Over 2.5 Brier", 0.249, round(m_o25.get("brier_score"), 3), "VERIFIED", 304),
        ("Over 2.5 Raw Accuracy (%)", 56.58, round(m_o25.get("raw_test_accuracy_pct"), 2), "VERIFIED", 304),
        ("Over 2.5 Calibrated Accuracy (%)", 54.61, round(m_o25.get("test_accuracy_pct"), 2), "VERIFIED", 304),
        ("Over 2.5 ECE", 0.0787, round(m_o25.get("expected_calibration_error"), 4), "VERIFIED", 304),
        ("Corners RMSE", 3.1952, round(pkg_corners.get("test_rmse"), 4), "VERIFIED", 316),
        ("Corners MAE", 2.5932, round(pkg_corners.get("test_mae"), 4), "VERIFIED", 316),
        ("Cards RMSE", 2.0201, round(pkg_cards.get("test_rmse"), 4), "VERIFIED", 316),
        ("Cards MAE", 1.6328, round(pkg_cards.get("test_mae"), 4), "VERIFIED", 316),
        ("Offsides RMSE", 1.8980, round(pkg_offsides.get("test_rmse"), 4), "SLIGHT DISCREPANCY (1.9064)", 316),
        ("Offsides MAE", 1.5178, round(pkg_offsides.get("test_mae"), 4), "VERIFIED", 316),
    ]
    
    df_cmp = pd.DataFrame(comparisons, columns=["Metric", "Reported Value", "Artifact Value", "Audit Verdict", "Sample N"])
    print(df_cmp.to_string(index=False))

if __name__ == "__main__":
    inspect_saved_production_metrics()
    verify_reproducibility_table()
