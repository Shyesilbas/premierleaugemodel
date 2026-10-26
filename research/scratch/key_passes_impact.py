#!/usr/bin/env python3
"""
A/B Benchmark Experiment: Testing the Impact of Key Passes (Shot Assists) on Goal Prediction Models.
Evaluates whether adding lagging rolling/EWMA key passes improves:
1. Over 2.5 Goals Log-loss & Brier Score
2. Over 1.5 & Over 3.5 Goals Brier Score
3. BTTS (KG Var) Log-loss & Brier Score
4. Total Goals Lambda Error (Poisson deviance & MAE)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, brier_score_loss, mean_absolute_error

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas
from src.models.eval_utils import paired_bootstrap_delta, per_match_log_loss
from src.models.train_match_outcome import feature_set

def compute_key_pass_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes strictly historical, zero-leakage rolling & EWMA key pass metrics for each team."""
    df = df.copy()
    if "match_date" not in df.columns:
        if "kickoff_millis" in df.columns:
            df["match_date"] = pd.to_datetime(df["kickoff_millis"], unit="ms")
        else:
            df["match_date"] = pd.to_datetime(df["kickoff_label"])
            
    # Build chronological long table of played matches
    played_mask = df["home_score"].notna() & df["away_score"].notna()
    played_df = df[played_mask].sort_values(["match_date", "match_id"]).reset_index(drop=True)
    
    rows = []
    for _, r in played_df.iterrows():
        m_id = r["match_id"]
        m_date = r["match_date"]
        # Home
        rows.append({
            "match_id": m_id,
            "match_date": m_date,
            "team_id": r["home_id"],
            "is_home": 1,
            "kp_for": float(r.get("home_total_att_assist", 10.62) or 10.62),
            "kp_against": float(r.get("away_total_att_assist", 8.78) or 8.78),
            "shots_for": float(r.get("home_total_scoring_att", 13.0) or 13.0),
        })
        # Away
        rows.append({
            "match_id": m_id,
            "match_date": m_date,
            "team_id": r["away_id"],
            "is_home": 0,
            "kp_for": float(r.get("away_total_att_assist", 8.78) or 8.78),
            "kp_against": float(r.get("home_total_att_assist", 10.62) or 10.62),
            "shots_for": float(r.get("away_total_scoring_att", 11.5) or 11.5),
        })
        
    long_df = pd.DataFrame(rows).sort_values(["team_id", "match_date", "match_id"]).reset_index(drop=True)
    
    # Group by team and calculate strictly lagged rolling & ewma
    grouped = long_df.groupby("team_id")
    
    long_df["kp_for_roll_5"] = grouped["kp_for"].transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean()).fillna(9.7)
    long_df["kp_for_roll_10"] = grouped["kp_for"].transform(lambda s: s.shift(1).rolling(10, min_periods=1).mean()).fillna(9.7)
    long_df["kp_for_ewma_02"] = grouped["kp_for"].transform(lambda s: s.shift(1).ewm(alpha=0.2, min_periods=1).mean()).fillna(9.7)
    
    long_df["kp_against_roll_5"] = grouped["kp_against"].transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean()).fillna(9.7)
    long_df["kp_against_roll_10"] = grouped["kp_against"].transform(lambda s: s.shift(1).rolling(10, min_periods=1).mean()).fillna(9.7)
    long_df["kp_against_ewma_02"] = grouped["kp_against"].transform(lambda s: s.shift(1).ewm(alpha=0.2, min_periods=1).mean()).fillna(9.7)
    
    shots_roll_10 = grouped["shots_for"].transform(lambda s: s.shift(1).rolling(10, min_periods=1).mean()).fillna(12.5)
    long_df["kp_share_roll_10"] = (long_df["kp_for_roll_10"] / (shots_roll_10 + 1e-5)).clip(0.1, 1.0)
    
    # Split back into home and away features
    home_feats = long_df[long_df["is_home"] == 1].set_index("match_id")
    away_feats = long_df[long_df["is_home"] == 0].set_index("match_id")
    
    feat_cols = ["kp_for_roll_5", "kp_for_roll_10", "kp_for_ewma_02", 
                 "kp_against_roll_5", "kp_against_roll_10", "kp_against_ewma_02", "kp_share_roll_10"]
    
    for c in feat_cols:
        df[f"home_{c}"] = df["match_id"].map(home_feats[c]).fillna(9.7 if "share" not in c else 0.75)
        df[f"away_{c}"] = df["match_id"].map(away_feats[c]).fillna(9.7 if "share" not in c else 0.75)
        
    df["kp_ewma_diff"] = df["home_kp_for_ewma_02"] - df["away_kp_for_ewma_02"]
    return df

def run_experiment():
    print("Loading feature dataset...")
    df = pd.read_parquet("data/competitions/premier_league/processed/features_matches_all.parquet")
    print(f"Total rows in dataset: {len(df)}")
    
    print("Generating strictly lagging key pass features...")
    df = compute_key_pass_features(df)
    
    # Define feature sets
    base_features = feature_set("o25", list(df.columns))
    print(f"Baseline feature count: {len(base_features)}")
    
    var1_features = base_features + [
        "home_kp_for_roll_10", "away_kp_for_roll_10",
        "home_kp_for_ewma_02", "away_kp_for_ewma_02",
    ]
    
    var2_features = var1_features + [
        "home_kp_against_roll_10", "away_kp_against_roll_10",
        "home_kp_against_ewma_02", "away_kp_against_ewma_02",
    ]
    
    var3_features = var2_features + [
        "home_kp_share_roll_10", "away_kp_share_roll_10",
        "kp_ewma_diff"
    ]
    
    variants = {
        "Baseline (Mevcut 55 Özellik)": base_features,
        "V1 (+ Kilit Pas Hücum 4 Özellik)": var1_features,
        "V2 (+ Kilit Pas Hücum & Savunma 8 Özellik)": var2_features,
        "V3 (+ Kilit Pas Dönüşüm & Fark 11 Özellik)": var3_features,
    }
    
    # Chronological forward walk-forward splits
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))
    print(f"Chronological seasons in evaluation: {seasons}")
    
    results = {name: {
        "o25_preds": [], "o15_preds": [], "o35_preds": [], "btts_preds": [],
        "lam_home": [], "lam_away": [], "o25_targets": [], "o15_targets": [], 
        "o35_targets": [], "btts_targets": [], "actual_home": [], "actual_away": []
    } for name in variants}
    
    # Evaluate walk-forward holdouts
    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]
        
        if len(train_df) < 300 or len(test_df) == 0:
            continue
            
        print(f"\n--- Evaluating Holdout Season: {test_season} (Train N={len(train_df)}, Test N={len(test_df)}) ---")
        
        # Fit Dixon-Coles on train_df
        dc_model = DixonColesModel(half_life_days=365.0).fit(train_df)
        dc_h, dc_a = dc_model.lambdas(test_df)
        
        # Targets
        actual_h = test_df["home_score"].to_numpy(dtype=float)
        actual_a = test_df["away_score"].to_numpy(dtype=float)
        total_g = actual_h + actual_a
        y_o25 = (total_g > 2.5).astype(int)
        y_o15 = (total_g > 1.5).astype(int)
        y_o35 = (total_g > 3.5).astype(int)
        y_btts = ((actual_h > 0) & (actual_a > 0)).astype(int)
        
        for name, feats in variants.items():
            feat_model = FeatureGoalModel(features=feats, alpha=10.0).fit(train_df)
            feat_h, feat_a = feat_model.lambdas(test_df)
            
            blend_h = blend_lambdas(dc_h, feat_h, 0.25)
            blend_a = blend_lambdas(dc_a, feat_a, 0.25)
            blend_rho = 0.5 * (dc_model.rho_ + feat_model.rho_)
            
            matrices = matrix_from_lambdas(blend_h, blend_a, blend_rho)
            p_o25 = over_prob(matrices, 2.5)
            p_o15 = over_prob(matrices, 1.5)
            p_o35 = over_prob(matrices, 3.5)
            p_btts = btts_prob(matrices)
            
            results[name]["o25_preds"].extend(p_o25)
            results[name]["o15_preds"].extend(p_o15)
            results[name]["o35_preds"].extend(p_o35)
            results[name]["btts_preds"].extend(p_btts)
            results[name]["lam_home"].extend(blend_h)
            results[name]["lam_away"].extend(blend_a)
            results[name]["o25_targets"].extend(y_o25)
            results[name]["o15_targets"].extend(y_o15)
            results[name]["o35_targets"].extend(y_o35)
            results[name]["btts_targets"].extend(y_btts)
            results[name]["actual_home"].extend(actual_h)
            results[name]["actual_away"].extend(actual_a)
            
    print("\n" + "="*80)
    print("TOPLU DEĞERLENDİRME SONUÇLARI (Tüm İleri Holdout Sezonları Havuzu)")
    print("="*80)
    
    summary = []
    base_o25_loss = None
    
    for name in variants:
        y_o25 = np.array(results[name]["o25_targets"])
        p_o25 = np.clip(np.array(results[name]["o25_preds"]), 1e-6, 1 - 1e-6)
        
        y_o15 = np.array(results[name]["o15_targets"])
        p_o15 = np.clip(np.array(results[name]["o15_preds"]), 1e-6, 1 - 1e-6)
        
        y_o35 = np.array(results[name]["o35_targets"])
        p_o35 = np.clip(np.array(results[name]["o35_preds"]), 1e-6, 1 - 1e-6)
        
        y_btts = np.array(results[name]["btts_targets"])
        p_btts = np.clip(np.array(results[name]["btts_preds"]), 1e-6, 1 - 1e-6)
        
        loss_o25 = log_loss(y_o25, p_o25)
        brier_o25 = brier_score_loss(y_o25, p_o25)
        
        brier_o15 = brier_score_loss(y_o15, p_o15)
        brier_o35 = brier_score_loss(y_o35, p_o35)
        
        loss_btts = log_loss(y_btts, p_btts)
        brier_btts = brier_score_loss(y_btts, p_btts)
        
        # Poisson deviance / MAE on expected goals
        lam_tot = np.array(results[name]["lam_home"]) + np.array(results[name]["lam_away"])
        act_tot = np.array(results[name]["actual_home"]) + np.array(results[name]["actual_away"])
        goals_mae = mean_absolute_error(act_tot, lam_tot)
        
        if name == "Baseline (Mevcut 55 Özellik)":
            base_o25_losses = per_match_log_loss(np.column_stack([1-p_o25, p_o25]), y_o25)
            delta_str = "REFERANS"
            ci_str = "-"
        else:
            cand_o25_losses = per_match_log_loss(np.column_stack([1-p_o25, p_o25]), y_o25)
            delta = paired_bootstrap_delta(cand_o25_losses, base_o25_losses, n_boot=2000)
            diff = delta["mean_delta"]
            delta_str = f"{diff:+.5f}"
            ci_str = f"[{delta['ci_low']:+.5f}, {delta['ci_high']:+.5f}]"
            
        summary.append({
            "Model Varyantı": name,
            "Özellik": len(variants[name]),
            "2.5 Üst LogLoss": round(loss_o25, 4),
            "2.5 Üst Brier": round(brier_o25, 4),
            "1.5 Üst Brier": round(brier_o15, 4),
            "3.5 Üst Brier": round(brier_o35, 4),
            "KG Var LogLoss": round(loss_btts, 4),
            "KG Var Brier": round(brier_btts, 4),
            "Gol MAE": round(goals_mae, 3),
            "Δ LogLoss (vs Base)": delta_str,
            "95% Güven Aralığı": ci_str
        })
        
    res_df = pd.DataFrame(summary)
    print(res_df.to_string(index=False))
    
    # Feature weights check on full training data
    print("\n" + "="*80)
    print("POISSON REGRESYONU KATSAYI İNCELEMESİ (Candidate 2 için)")
    print("="*80)
    all_played = played.copy()
    m2 = FeatureGoalModel(features=var2_features, alpha=10.0).fit(all_played)
    pipe_home = m2.home_
    pipe_away = m2.away_
    coef_home = pipe_home.named_steps["poissonregressor"].coef_
    coef_away = pipe_away.named_steps["poissonregressor"].coef_
    
    coef_df = pd.DataFrame({
        "Özellik": var2_features,
        "Ev Katsayısı (λ_home)": coef_home,
        "Dep Katsayısı (λ_away)": coef_away,
    })
    
    kp_coefs = coef_df[coef_df["Özellik"].str.contains("kp_")].sort_values(by="Ev Katsayısı (λ_home)", ascending=False)
    print("Kilit Pas Özelliklerinin Poisson Katsayıları:")
    print(kp_coefs.to_string(index=False))
    
    # Top 10 most impactful features overall
    print("\nEn Yüksek Katsayıya Sahip İlk 8 Özellik (Ev Golü λ_home):")
    top_home = coef_df.reindex(coef_df["Ev Katsayısı (λ_home)"].abs().sort_values(ascending=False).index).head(8)
    print(top_home.to_string(index=False))

if __name__ == "__main__":
    run_experiment()
