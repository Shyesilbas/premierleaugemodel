#!/usr/bin/env python3
"""
Deep-dive investigation script for P0 Goal Model validation:
1. Görev A: L4 (Feature Poisson alone) raw vs calibrated (Platt / Isotonic)
2. Görev B: L5 gain isolation across DC weights (0.0, 0.10, 0.25, 0.50, 1.0) and Blend Type (Geometric vs Arithmetic)
3. Görev C: Re-evaluating 55-feature baseline vs Perfect In-Sample Constant (0.6779 vs 0.6779)
4. BTTS Investigation: DC rho calibration vs Dedicated BTTS Logistic Calibrator (keeping matrix consistency)
5. Model vs Market: Evaluating holdout matches with external bookmaker odds
"""

import json
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score, accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def run_deep_dive():
    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]
    
    # 55-feature baseline list (without the 3 tactical defensive line features)
    features_55 = [f for f in features_58 if f not in [
        "team_defensive_line_depth_roll8",
        "opp_defensive_line_depth_roll8",
        "match_pace_defensive_stretch_roll8"
    ]]
    
    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))
    
    # Collect walk-forward data across test seasons
    records = []
    
    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]
        
        if len(train_df) < 300 or len(test_df) == 0:
            continue
            
        # Fit models
        dc = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
        dc_h, dc_a = dc.lambdas(test_df)
        
        # 58-feat model
        feat58 = FeatureGoalModel(features=features_58, alpha=chosen["feature_alpha"]).fit(train_df)
        f58_h, f58_a = feat58.lambdas(test_df)
        
        # 55-feat baseline model
        feat55 = FeatureGoalModel(features=features_55, alpha=chosen["feature_alpha"]).fit(train_df)
        f55_h, f55_a = feat55.lambdas(test_df)
        
        # Also compute train-set predictions for fitting out-of-fold / pre-test calibrators
        dc_train_h, dc_train_a = dc.lambdas(train_df)
        f58_train_h, f58_train_a = feat58.lambdas(train_df)
        train_blend_h = blend_lambdas(dc_train_h, f58_train_h, chosen["dc_weight"])
        train_blend_a = blend_lambdas(dc_train_a, f58_train_a, chosen["dc_weight"])
        train_mats = matrix_from_lambdas(train_blend_h, train_blend_a, 0.5 * (dc.rho_ + feat58.rho_))
        p_btts_train = btts_prob(train_mats)
        y_btts_train = ((train_df["home_score"] > 0) & (train_df["away_score"] > 0)).astype(int).to_numpy()
        
        # Fit a Platt calibrator (LogisticRegression) on train BTTS
        btts_calibrator = LogisticRegression(C=1.0)
        # Using log-odds feature
        eps = 1e-6
        log_odds_train = np.log(np.clip(p_btts_train, eps, 1-eps) / (1 - np.clip(p_btts_train, eps, 1-eps))).reshape(-1, 1)
        btts_calibrator.fit(log_odds_train, y_btts_train)
        
        # Test-set evaluations
        for i, (_, row) in enumerate(test_df.iterrows()):
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            records.append({
                "match_id": row["match_id"],
                "season": test_season,
                "home_score": hs,
                "away_score": as_,
                "total_score": hs + as_,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "is_btts": 1 if (hs > 0 and as_ > 0) else 0,
                
                # Raw lambdas
                "dc_h": dc_h[i], "dc_a": dc_a[i],
                "f58_h": f58_h[i], "f58_a": f58_a[i],
                "f55_h": f55_h[i], "f55_a": f55_a[i],
                "dc_rho": dc.rho_,
                "f58_rho": feat58.rho_,
                "btts_calibrator": btts_calibrator,
            })
            
    res_df = pd.DataFrame(records)
    y_o25 = res_df["is_o25"].to_numpy()
    y_btts = res_df["is_btts"].to_numpy()
    N = len(res_df)
    print(f"Total holdout matches: {N}")
    print(f"True Holdout Over 2.5 rate: {y_o25.mean():.6f}")
    print(f"True Holdout BTTS rate: {y_btts.mean():.6f}")
    
    # -------------------------------------------------------------
    # GÖREV C: Re-evaluating 55-feat vs 58-feat vs Perfect In-Sample Constant
    # -------------------------------------------------------------
    p_perfect_const = np.full(N, y_o25.mean())
    ll_perfect_const = log_loss(y_o25, p_perfect_const)
    brier_perfect_const = brier_score_loss(y_o25, p_perfect_const)
    
    mean_rho = float(np.mean(res_df["dc_rho"].to_numpy() + res_df["f58_rho"].to_numpy()) * 0.5)
    
    # 55-feat blended model
    b55_h = blend_lambdas(res_df["dc_h"].to_numpy(), res_df["f55_h"].to_numpy(), chosen["dc_weight"])
    b55_a = blend_lambdas(res_df["dc_a"].to_numpy(), res_df["f55_a"].to_numpy(), chosen["dc_weight"])
    mats_55 = matrix_from_lambdas(b55_h, b55_a, mean_rho)
    p_o25_55 = over_prob(mats_55, 2.5)
    
    # 58-feat blended model (production)
    b58_h = blend_lambdas(res_df["dc_h"].to_numpy(), res_df["f58_h"].to_numpy(), chosen["dc_weight"])
    b58_a = blend_lambdas(res_df["dc_a"].to_numpy(), res_df["f58_a"].to_numpy(), chosen["dc_weight"])
    mats_58 = matrix_from_lambdas(b58_h, b58_a, mean_rho)
    p_o25_58 = over_prob(mats_58, 2.5)
    
    print("\n--- GÖREV C: 55-Feat vs 58-Feat vs Perfect Constant ---")
    print(f"Holdout True Over 2.5 Rate:   {y_o25.mean()*100:.2f}% (Holdout Entropy H = {ll_perfect_const:.6f})")
    print(f"Perfect In-Sample Constant:   LL = {ll_perfect_const:.6f}, Brier = {brier_perfect_const:.6f}")
    print(f"55-Feature Blended Model:     LL = {log_loss(y_o25, p_o25_55):.6f}, Brier = {brier_score_loss(y_o25, p_o25_55):.6f}")
    print(f"58-Feature Blended Model:     LL = {log_loss(y_o25, p_o25_58):.6f}, Brier = {brier_score_loss(y_o25, p_o25_58):.6f}")
    
    # -------------------------------------------------------------
    # GÖREV A: L4 (58-feat Poisson Alone) Raw vs Calibrated
    # -------------------------------------------------------------
    mean_f58_rho = float(np.mean(res_df["f58_rho"].to_numpy()))
    mats_f58 = matrix_from_lambdas(res_df["f58_h"].to_numpy(), res_df["f58_a"].to_numpy(), mean_f58_rho)
    p_o25_f58_raw = over_prob(mats_f58, 2.5)
    ll_f58_raw = log_loss(y_o25, p_o25_f58_raw)
    brier_f58_raw = brier_score_loss(y_o25, p_o25_f58_raw)
    auc_f58_raw = roc_auc_score(y_o25, p_o25_f58_raw)
    
    # Let's test calibration on p_o25_f58
    # 1. Logistic Calibration (Platt) on log-odds using 5-fold CV on holdout or expanding walk-forward
    # Let's see what optimal scaling achieves on holdout
    eps = 1e-6
    logit_f58 = np.log(np.clip(p_o25_f58_raw, eps, 1-eps) / (1 - np.clip(p_o25_f58_raw, eps, 1-eps))).reshape(-1, 1)
    lr_cal = LogisticRegression().fit(logit_f58, y_o25)
    p_o25_f58_cal_platt = lr_cal.predict_proba(logit_f58)[:, 1]
    
    # 2. Isotonic Calibration
    iso_cal = IsotonicRegression(out_of_bounds="clip").fit(p_o25_f58_raw, y_o25)
    p_o25_f58_cal_iso = iso_cal.predict(p_o25_f58_raw)
    
    print("\n--- GÖREV A: L4 (Feature Poisson Alone) Raw vs Calibrated ---")
    print(f"L4 Raw Feature Poisson:        LL = {ll_f58_raw:.6f}, Brier = {brier_f58_raw:.6f}, AUC = {auc_f58_raw:.4f}, Mean Prob = {p_o25_f58_raw.mean():.4f}")
    print(f"L4 Platt Calibrated (Optimal): LL = {log_loss(y_o25, p_o25_f58_cal_platt):.6f}, Brier = {brier_score_loss(y_o25, p_o25_f58_cal_platt):.6f}")
    print(f"L4 Isotonic Calibrated:        LL = {log_loss(y_o25, p_o25_f58_cal_iso):.6f}, Brier = {brier_score_loss(y_o25, p_o25_f58_cal_iso):.6f}")
    
    # -------------------------------------------------------------
    # GÖREV B: L5 Gain Isolation Across Blend Weights & Types
    # -------------------------------------------------------------
    print("\n--- GÖREV B: Blend Weight Sweeps (Geometric vs Arithmetic) ---")
    weights = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.0]
    
    print("WEIGHT | GEOMETRIC LL | ARITHMETIC LL | GEOM BRIER | ARITH BRIER | MEAN LAMBDA | LAMBDA STD")
    for w in weights:
        # Geometric blend: exp(w * ln(dc) + (1-w) * ln(f58))
        geo_h = blend_lambdas(res_df["dc_h"].to_numpy(), res_df["f58_h"].to_numpy(), w)
        geo_a = blend_lambdas(res_df["dc_a"].to_numpy(), res_df["f58_a"].to_numpy(), w)
        mats_geo = matrix_from_lambdas(geo_h, geo_a, mean_rho)
        p_geo = over_prob(mats_geo, 2.5)
        ll_geo = log_loss(y_o25, p_geo)
        br_geo = brier_score_loss(y_o25, p_geo)
        
        # Arithmetic blend: w * dc + (1-w) * f58
        ari_h = w * res_df["dc_h"].to_numpy() + (1 - w) * res_df["f58_h"].to_numpy()
        ari_a = w * res_df["dc_a"].to_numpy() + (1 - w) * res_df["f58_a"].to_numpy()
        mats_ari = matrix_from_lambdas(ari_h, ari_a, mean_rho)
        p_ari = over_prob(mats_ari, 2.5)
        ll_ari = log_loss(y_o25, p_ari)
        br_ari = brier_score_loss(y_o25, p_ari)
        
        print(f" {w:4.2f}  |    {ll_geo:.6f}   |    {ll_ari:.6f}    |   {br_geo:.6f} |   {br_ari:.6f} |   {(geo_h+geo_a).mean():.4f}    |   {(geo_h+geo_a).std():.4f}")
        
    # Check what Dixon-Coles alone produces
    mats_dc_alone = matrix_from_lambdas(res_df["dc_h"].to_numpy(), res_df["dc_a"].to_numpy(), mean_rho)
    p_dc_alone = over_prob(mats_dc_alone, 2.5)
    print(f"DC Alone (w=1.0): LL = {log_loss(y_o25, p_dc_alone):.6f}, Brier = {brier_score_loss(y_o25, p_dc_alone):.6f}, AUC = {roc_auc_score(y_o25, p_dc_alone):.4f}, Mean Prob = {p_dc_alone.mean():.4f}")
    
    # -------------------------------------------------------------
    # BTTS INVESTIGATION: Logistic Calibrator vs Raw vs DC Rho
    # -------------------------------------------------------------
    print("\n--- BTTS INVESTIGATION: Raw Blended vs Dedicated Logistic Calibrator ---")
    p_btts_prod = btts_prob(mats_58)
    ll_btts_prod = log_loss(y_btts, p_btts_prod)
    br_btts_prod = brier_score_loss(y_btts, p_btts_prod)
    auc_btts_prod = roc_auc_score(y_btts, p_btts_prod)
    
    # Walk-forward Platt calibrator applied per test fold:
    p_btts_calibrated = []
    for i, row in res_df.iterrows():
        cal = row["btts_calibrator"]
        raw_p = p_btts_prod[i]
        lo = np.log(np.clip(raw_p, 1e-6, 1-1e-6) / (1 - np.clip(raw_p, 1e-6, 1-1e-6))).reshape(1, -1)
        p_cal = float(cal.predict_proba(lo)[0, 1])
        p_btts_calibrated.append(p_cal)
    p_btts_calibrated = np.array(p_btts_calibrated)
    
    print(f"Blind Poisson Baseline:          LL = 0.6802, Brier = 0.2435")
    print(f"Production Blended (Raw):        LL = {ll_btts_prod:.6f}, Brier = {br_btts_prod:.6f}, AUC = {auc_btts_prod:.4f}, Mean Prob = {p_btts_prod.mean():.4f}")
    print(f"Walk-Forward Platt Calibrated:   LL = {log_loss(y_btts, p_btts_calibrated):.6f}, Brier = {brier_score_loss(y_btts, p_btts_calibrated):.6f}, AUC = {roc_auc_score(y_btts, p_btts_calibrated):.4f}, Mean Prob = {p_btts_calibrated.mean():.4f}")
    
    # In-sample optimal Platt on holdout for theoretical upper bound
    lo_holdout = np.log(np.clip(p_btts_prod, 1e-6, 1-1e-6) / (1 - np.clip(p_btts_prod, 1e-6, 1-1e-6))).reshape(-1, 1)
    lr_btts_opt = LogisticRegression().fit(lo_holdout, y_btts)
    p_btts_opt_cal = lr_btts_opt.predict_proba(lo_holdout)[:, 1]
    print(f"Optimal Platt Calibrated:        LL = {log_loss(y_btts, p_btts_opt_cal):.6f}, Brier = {brier_score_loss(y_btts, p_btts_opt_cal):.6f}")

    # -------------------------------------------------------------
    # MODEL VS MARKET (Bookmaker Odds)
    # -------------------------------------------------------------
    print("\n--- MODEL VS MARKET (Bookmaker Odds Analysis) ---")
    res_df["p_o25_prod"] = p_o25_58
    res_df["p_btts_prod"] = p_btts_prod
    
    import sqlite3
    conn = sqlite3.connect("data/premier_league.db")
    odds_df = pd.read_sql_query("""
        SELECT match_id, bookmaker, over_25_open, under_25_open, btts_yes_open, btts_no_open
        FROM external_match_odds
        WHERE over_25_open IS NOT NULL AND under_25_open IS NOT NULL
    """, conn)
    
    # Merge with res_df on match_id
    m_df = pd.merge(res_df, odds_df, on="match_id", how="inner")
    print(f"Holdout matches with external bookmaker odds: {len(m_df)} matches")
    if len(m_df) > 0:
        # Implied probabilities from bookmaker (with margin removal)
        raw_mkt_o25 = 1.0 / m_df["over_25_open"].to_numpy()
        raw_mkt_u25 = 1.0 / m_df["under_25_open"].to_numpy()
        margin = raw_mkt_o25 + raw_mkt_u25
        p_mkt_o25 = raw_mkt_o25 / margin
        
        # True outcomes
        m_y_o25 = m_df["is_o25"].to_numpy()
        p_model_o25 = m_df["p_o25_prod"].to_numpy()
        
        print(f"Market (Fair Bookmaker) Over 2.5: LL = {log_loss(m_y_o25, p_mkt_o25):.6f}, Brier = {brier_score_loss(m_y_o25, p_mkt_o25):.6f}, AUC = {roc_auc_score(m_y_o25, p_mkt_o25):.4f}")
        print(f"Our Model Over 2.5:              LL = {log_loss(m_y_o25, p_model_o25):.6f}, Brier = {brier_score_loss(m_y_o25, p_model_o25):.6f}, AUC = {roc_auc_score(m_y_o25, p_model_o25):.4f}")
        
        # BTTS comparison if available
        btts_mask = m_df["btts_yes_open"].notna() & m_df["btts_no_open"].notna()
        if btts_mask.sum() > 0:
            sub = m_df[btts_mask]
            raw_btts_y = 1.0 / sub["btts_yes_open"].to_numpy()
            raw_btts_n = 1.0 / sub["btts_no_open"].to_numpy()
            mkt_btts = raw_btts_y / (raw_btts_y + raw_btts_n)
            sub_y = sub["is_btts"].to_numpy()
            sub_model = sub["p_btts_prod"].to_numpy()
            print(f"Market (Fair Bookmaker) BTTS:    LL = {log_loss(sub_y, mkt_btts):.6f}, Brier = {brier_score_loss(sub_y, mkt_btts):.6f}, AUC = {roc_auc_score(sub_y, mkt_btts):.4f}")
            print(f"Our Model BTTS:                  LL = {log_loss(sub_y, sub_model):.6f}, Brier = {brier_score_loss(sub_y, sub_model):.6f}, AUC = {roc_auc_score(sub_y, sub_model):.4f}")

if __name__ == "__main__":
    run_deep_dive()
