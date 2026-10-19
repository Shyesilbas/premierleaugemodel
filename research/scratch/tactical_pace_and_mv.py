#!/usr/bin/env python3
"""
A/B Benchmark Experiment:
Testing the impact of Dampening/Removing Market Value (effective_log_mv_ratio)
and Adding Tactical Tempo (Shot Volume, Match Pace) and Defensive Line Depth (Offsides Against/For).
Evaluated on 1,200 holdout matches across 4 forward seasons (2023/24 - 2026/27).
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

def engineer_tactical_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # 1. Total Shot Pace (Takımların maç başına toplam şut temposu: attığı + yediği şutlar)
    # Takımın dahil olduğu maçlar ne kadar açık / tempolu geçiyor?
    h_s_for = df["home_shots_for_roll_10"].fillna(13.0)
    h_s_against = df["home_shots_against_roll_10"].fillna(13.0)
    a_s_for = df["away_shots_for_roll_10"].fillna(11.5)
    a_s_against = df["away_shots_against_roll_10"].fillna(13.5)
    
    df["home_match_openness"] = h_s_for + h_s_against  # Ev sahibinin maçlarındaki toplam şut hacmi
    df["away_match_openness"] = a_s_for + a_s_against  # Deplasmanın maçlarındaki toplam şut hacmi
    df["combined_shot_pace"] = (df["home_match_openness"] + df["away_match_openness"]) / 2.0
    
    # 2. Defensive Line Depth / Offside Trap (Yüksek Savunma Çizgisi)
    # Bir takım rakibini ne kadar çok ofsayta düşürüyorsa (offsides_against), savunma hattı o kadar öndedir!
    df["home_high_line"] = df["home_offsides_against_roll_10"].fillna(1.63)
    df["away_high_line"] = df["away_offsides_against_roll_10"].fillna(1.63)
    # Her iki takımın da önde oynaması -> arkada devasa boşluklar -> gol patlaması
    df["mutual_high_line_risk"] = df["home_high_line"] * df["away_high_line"]
    
    # 3. Dampened Market Value variants
    df["dampened_mv_ratio_50"] = df["effective_log_mv_ratio"] * 0.50
    df["dampened_mv_ratio_25"] = df["effective_log_mv_ratio"] * 0.25
    df["zero_mv"] = 0.0
    
    return df

def run_tactical_benchmark():
    print("Loading feature dataset...")
    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    df = engineer_tactical_features(df)
    
    base_feats = feature_set("o25", list(df.columns))
    print(f"Base feature count: {len(base_feats)}")
    
    # Define candidate variants
    # V0: Baseline
    # V1: Baseline without MV ratio (Kadro Değeri Tamamen Çıkarıldı)
    v1_no_mv = [f for f in base_feats if f != "effective_log_mv_ratio"]
    
    # V2: Baseline with Dampened MV (Kadro Değeri %50 Bastırıldı)
    v2_damp_mv = [f if f != "effective_log_mv_ratio" else "dampened_mv_ratio_50" for f in base_feats]
    
    # V3: Baseline + Tactical Tempo (Şut Hacmi & Açık Oyun Endeksi)
    tempo_feats = [
        "home_shots_for_roll_10", "away_shots_for_roll_10",
        "home_shots_against_roll_10", "away_shots_against_roll_10",
        "combined_shot_pace"
    ]
    v3_tempo = base_feats + tempo_feats
    
    # V4: Baseline + Defensive Line (Savunma Çizgisi Derinliği / Ofsayt Tuzağı)
    line_feats = [
        "home_high_line", "away_high_line", "mutual_high_line_risk"
    ]
    v4_line = base_feats + line_feats
    
    # V5: Baseline + Tempo + Defensive Line (Tüm Taktiksel Felsefe Paketi)
    v5_full_tactical = base_feats + tempo_feats + line_feats
    
    # V6: Full Tactical + Dampened MV (Kadro Değeri %50 Bastırılmış + Full Taktiksel Felsefe)
    v6_tactical_damp_mv = [f if f != "effective_log_mv_ratio" else "dampened_mv_ratio_50" for f in v5_full_tactical]
    
    # V7: Full Tactical + NO MV (Kadro Değeri Sıfırlandı + Full Taktiksel Felsefe)
    v7_tactical_no_mv = [f for f in v5_full_tactical if f != "effective_log_mv_ratio"]
    
    variants = {
        "Baseline (Mevcut 55 Özellik)": base_feats,
        "V1 (Kadro Değeri Çıkarıldı - No MV)": v1_no_mv,
        "V2 (Kadro Değeri %50 Bastırıldı)": v2_damp_mv,
        "V3 (+ Şut Temposu & Açıklık - 5 Özellik)": v3_tempo,
        "V4 (+ Savunma Çizgisi & Ofsayt - 3 Özellik)": v4_line,
        "V5 (Baseline + Tempo + Savunma Çizgisi - 63 Özellik)": v5_full_tactical,
        "V6 (Full Taktik + %50 Bastırılmış Kadro Değeri)": v6_tactical_damp_mv,
        "V7 (Full Taktik + Sıfır Kadro Değeri)": v7_tactical_no_mv,
    }
    
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))
    
    results = {name: {
        "o25_preds": [], "o15_preds": [], "o35_preds": [], "btts_preds": [],
        "lam_home": [], "lam_away": [], "o25_targets": [], "o15_targets": [], 
        "o35_targets": [], "btts_targets": [], "actual_home": [], "actual_away": []
    } for name in variants}
    
    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]
        
        if len(train_df) < 300 or len(test_df) == 0:
            continue
            
        print(f"Evaluating {test_season} (Train={len(train_df)}, Test={len(test_df)})...")
        
        dc_model = DixonColesModel(half_life_days=365.0).fit(train_df)
        dc_h, dc_a = dc_model.lambdas(test_df)
        
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
            
            results[name]["o25_preds"].extend(over_prob(matrices, 2.5))
            results[name]["o15_preds"].extend(over_prob(matrices, 1.5))
            results[name]["o35_preds"].extend(over_prob(matrices, 3.5))
            results[name]["btts_preds"].extend(btts_prob(matrices))
            results[name]["lam_home"].extend(blend_h)
            results[name]["lam_away"].extend(blend_a)
            results[name]["o25_targets"].extend(y_o25)
            results[name]["o15_targets"].extend(y_o15)
            results[name]["o35_targets"].extend(y_o35)
            results[name]["btts_targets"].extend(y_btts)
            results[name]["actual_home"].extend(actual_h)
            results[name]["actual_away"].extend(actual_a)
            
    print("\n" + "="*95)
    print("A/B DENEYİ SONUÇLARI (1.200 Holdout Maçı Havuzu)")
    print("="*95)
    
    summary = []
    base_o25_losses = None
    
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
        
        lam_tot = np.array(results[name]["lam_home"]) + np.array(results[name]["lam_away"])
        act_tot = np.array(results[name]["actual_home"]) + np.array(results[name]["actual_away"])
        goals_mae = mean_absolute_error(act_tot, lam_tot)
        
        if name == "Baseline (Mevcut 55 Özellik)":
            base_o25_losses = per_match_log_loss(np.column_stack([1-p_o25, p_o25]), y_o25)
            delta_str = "REFERANS"
            ci_str = "-"
        else:
            cand_losses = per_match_log_loss(np.column_stack([1-p_o25, p_o25]), y_o25)
            delta = paired_bootstrap_delta(cand_losses, base_o25_losses, n_boot=2000)
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
            "Gol MAE": round(goals_mae, 3),
            "Δ LogLoss": delta_str,
            "95% CI": ci_str
        })
        
    res_df = pd.DataFrame(summary)
    print(res_df.to_string(index=False))
    
    # Check learned weights of the tactical features on full dataset
    print("\n" + "="*95)
    print("V5 (FULL TAKTİK) POISSON REGRESYONU KATSAYILARI")
    print("="*95)
    m_v5 = FeatureGoalModel(features=v5_full_tactical, alpha=10.0).fit(played)
    coef_h = m_v5.home_.named_steps["poissonregressor"].coef_
    coef_a = m_v5.away_.named_steps["poissonregressor"].coef_
    cdf = pd.DataFrame({"Özellik": v5_full_tactical, "Katsayı (Ev)": coef_h, "Katsayı (Dep)": coef_a})
    
    tactical_names = tempo_feats + line_feats
    print("Eklenen Taktiksel Özelliklerin Katsayıları:")
    print(cdf[cdf["Özellik"].isin(tactical_names)].to_string(index=False))

if __name__ == "__main__":
    run_tactical_benchmark()
