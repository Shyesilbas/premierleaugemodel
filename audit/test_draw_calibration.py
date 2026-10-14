"""
Analyze raw vs calibrated probabilities for Brentford vs Liverpool and Leeds vs Man Utd.
"""
import joblib
import numpy as np
import pandas as pd
from src.models.model_utils import apply_probability_calibrator, blend_log
from src.api.server import (
    df_matches,
    features_all,
    outcome_artifact,
    build_prediction_row,
    _safe_features,
)

df_feat = pd.read_parquet(features_all)
o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact["feature_names"])

# Test cases:
# 1. Brentford (130) vs Liverpool (10)
# 2. Leeds (14) vs Man United (1)
for home_id, away_id, name in [
    (130, 10, "Brentford vs Liverpool"),
    (14, 1, "Leeds United vs Man United"),
    (11, 8, "Man City vs Ipswich"),
    (7, 4, "Everton vs Chelsea"),
]:
    sim_df = build_prediction_row(home_id, away_id, df_matches, df_feat, match_date=None, season="2026_27")
    
    # 1. Standalone Logreg raw
    p_logreg_raw = outcome_artifact["model_1x2"].predict_proba(_safe_features(sim_df, o_features, fill_value=np.nan))[0]
    
    # 2. Standalone Dixon-Coles raw
    p_dc_raw = outcome_artifact["model_dc"].predict_proba(sim_df)[0]
    
    # 3. Current production blend (0.65 logreg, 0.35 DC)
    blend_65_35 = blend_log(p_logreg_raw.reshape(1, -1), p_dc_raw.reshape(1, -1), 0.65)[0]
    
    # 4. Calibrated blend (Current production)
    cal_ens = outcome_artifact.get("calibrators", {}).get("1x2_ensemble")
    p_curr_prod = apply_probability_calibrator(blend_65_35.reshape(1, -1), cal_ens)[0]
    
    # 5. Let's test blend with 50/50 and with neutral draw bias or slightly higher DC weight
    blend_50_50 = blend_log(p_logreg_raw.reshape(1, -1), p_dc_raw.reshape(1, -1), 0.50)[0]
    # Bias-neutral calibrator (just temperature 0.95, zero bias)
    cal_neutral = {"temperature": 0.95, "bias": [0.0, 0.0, 0.0]}
    p_blend_neutral = apply_probability_calibrator(blend_65_35.reshape(1, -1), cal_neutral)[0]
    
    # Slightly tuned draw bias: e.g. bias = [0.0, -0.05, 0.0] or reduced draw bias
    cal_balanced = {"temperature": 0.95, "bias": [-0.03, 0.02, -0.01]}
    p_balanced = apply_probability_calibrator(blend_50_50.reshape(1, -1), cal_balanced)[0]

    print(f"\n=================== {name} ===================")
    print(f"  1. Logreg raw:          H={p_logreg_raw[0]*100:.1f}%  X={p_logreg_raw[1]*100:.1f}%  A={p_logreg_raw[2]*100:.1f}%")
    print(f"  2. Dixon-Coles raw:     H={p_dc_raw[0]*100:.1f}%  X={p_dc_raw[1]*100:.1f}%  A={p_dc_raw[2]*100:.1f}%")
    print(f"  3. Blend raw (65/35):   H={blend_65_35[0]*100:.1f}%  X={blend_65_35[1]*100:.1f}%  A={blend_65_35[2]*100:.1f}%")
    print(f"  4. Current Prod (cal):  H={p_curr_prod[0]*100:.1f}%  X={p_curr_prod[1]*100:.1f}%  A={p_curr_prod[2]*100:.1f}%")
    print(f"  5. Blend 50/50 raw:     H={blend_50_50[0]*100:.1f}%  X={blend_50_50[1]*100:.1f}%  A={blend_50_50[2]*100:.1f}%")
    print(f"  6. Blend 50/50 bal cal: H={p_balanced[0]*100:.1f}%  X={p_balanced[1]*100:.1f}%  A={p_balanced[2]*100:.1f}%")
