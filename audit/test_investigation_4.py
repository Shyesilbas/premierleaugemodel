"""
Audit Investigation 4: Trace the Full Inference Path and Re-evaluate Components
Compares Standalone Logistic Regression, Dixon-Coles, and the Blended Ensemble.
"""
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path

def trace_production_model():
    print("=== 1. PRODUCTION INFERENCE ARTIFACT INSPECTION ===")
    pkg = joblib.load("models/production/outcome_models_v1.joblib")
    
    print(f"Has standalone logreg ('model_1x2')? {'model_1x2' in pkg}")
    print(f"Has Dixon-Coles ('model_dc')? {'model_dc' in pkg}")
    print(f"Ensemble weight in artifact: {pkg.get('ensemble_weight')}")
    print(f"Available calibrators: {list(pkg.get('calibrators', {}).keys())}")
    
    m = pkg["metrics"]
    print("\n--- Component Breakdown in Metrics ---")
    
    # 1. Standalone Logreg
    m_single = m.get("model_1x2", {})
    print(f"Standalone Logreg Holdout Log-Loss: {m_single.get('log_loss'):.4f}")
    print(f"Standalone Logreg Holdout Brier:    {m_single.get('brier_score'):.4f}")
    print(f"Standalone Logreg Holdout Accuracy: {m_single.get('test_accuracy_pct'):.2f}%")
    
    # 2. Dixon-Coles component
    m_dc = m.get("dixon_coles_1x2", {})
    if m_dc:
        print(f"\nDixon-Coles Holdout Log-Loss: {m_dc.get('holdout_log_loss', m_dc.get('log_loss'))}")
        print(f"Dixon-Coles Parameters: {m_dc.get('parameters')}")
    else:
        print("\nDixon-Coles component metrics directly recorded in dc section.")
        
    # 3. Ensemble
    m_ens = m.get("1x2_ensemble_outer_eval", {})
    print(f"\nEnsemble Outer Evaluation: {json.dumps(m_ens, indent=2)[:400]}")
    
    # Check ensemble production key
    ens_prod = m.get("1x2_ensemble_production", {})
    print(f"\nEnsemble Production Settings: {ens_prod}")

if __name__ == "__main__":
    trace_production_model()
