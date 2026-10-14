"""
Test tuning of ensemble weight and draw calibration bias.
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
model_1x2 = outcome_artifact["model_1x2"]
model_dc = outcome_artifact["model_dc"]

fixtures = [
    (130, 10, "Brentford vs Liverpool"),
    (9, 12, "Leeds vs Man United"),
    (11, 8, "Man City vs Ipswich"),
    (7, 4, "Everton vs Chelsea"),
    (15, 1, "Nottingham vs Arsenal"),
]

# We will test:
# Option A: Current (weight=0.65, bias=[-0.0985, +0.1346, -0.0360])
# Option B: weight=0.50, current calibrator
# Option C: weight=0.50, draw-tempered calibrator (bias=[-0.04, +0.02, +0.02], temp=0.92)
# Option D: weight=0.45, bias=[-0.02, 0.00, +0.02], temp=0.95

print("Option A (Current Production: weight=0.65, Draw bias=+0.135):")
for h, a, name in fixtures:
    sim_df = df_feat[(df_feat["home_id"] == h) & (df_feat["away_id"] == a)]
    if sim_df.empty:
        # construct dummy from build_prediction_row
        from src.api.server import predict_match
        p = predict_match(h, a)
        print(f"  {name:25s}: H={p['outcome']['home_win_pct']}%  X={p['outcome']['draw_pct']}%  A={p['outcome']['away_win_pct']}%")

print("\n--- Testing Custom Blend Weights & Draw Tempering ---")

for h, a, name in fixtures:
    from src.api.server import _predict_fixture_row
    # We can inspect the raw model probabilities directly
    from src.api.server import predict_match
    # Let's inspect raw probs before calibration
