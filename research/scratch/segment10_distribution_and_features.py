#!/usr/bin/env python3
"""
Diagnostic Script for P1c Foundation:
1. Test 3.1: Chi-Square Goodness-of-Fit & Dispersion Index Test (Poisson vs Negative Binomial)
   - Segment 10 (Low λ < 2.871) vs High λ vs Global Holdout
2. Test 3.2: Variance and Signal Analysis of Existing 'Chaos' Features
   - big_chances, shots_ontarget, touches_in_opp_box, xg_against in Segment 10 vs Global
   - Correlations with actual goals inside Segment 10
"""

import numpy as np
import pandas as pd
import joblib
from scipy.stats import poisson, nbinom, chisquare, pearsonr, spearmanr
from scipy.optimize import minimize

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def fit_negative_binomial(data):
    """Fit Negative Binomial (r, p) using maximum likelihood."""
    y = np.asarray(data, dtype=int)
    mean_y = np.mean(y)
    var_y = np.var(y)
    if var_y <= mean_y:
        # No overdispersion, degenerate to Poisson
        return np.inf, 1.0, np.sum(poisson.logpmf(y, mean_y))
    
    # Method of moments initial guess: p = mean / var, r = mean * p / (1 - p)
    p_init = mean_y / var_y
    r_init = mean_y * p_init / (1.0 - p_init)
    
    def neg_ll(params):
        r, p = params
        if r <= 0 or p <= 0 or p >= 1:
            return 1e10
        # scipy.stats.nbinom pmf: P(X=k) where X is number of failures before r successes
        return -np.sum(nbinom.logpmf(y, r, p))
    
    res = minimize(neg_ll, [r_init, p_init], bounds=[(0.01, 100.0), (0.01, 0.99)])
    r_fit, p_fit = res.x
    ll = -res.fun
    return r_fit, p_fit, ll

def main():
    artifact = joblib.load("models/production/premier_league/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]

    df = pd.read_parquet("data/competitions/premier_league/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))

    records = []
    train_lambdas_all = []

    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]

        if len(train_df) < 300 or len(test_df) == 0:
            continue

        dc = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
        dc_h, dc_a = dc.lambdas(test_df)

        feat = FeatureGoalModel(features=features_58, alpha=chosen["feature_alpha"]).fit(train_df)
        feat_h, feat_a = feat.lambdas(test_df)

        dc_tr_h, dc_tr_a = dc.lambdas(train_df)
        feat_tr_h, feat_tr_a = feat.lambdas(train_df)
        geo_tr_h = blend_lambdas(dc_tr_h, feat_tr_h, chosen["dc_weight"])
        geo_tr_a = blend_lambdas(dc_tr_a, feat_tr_a, chosen["dc_weight"])
        train_lambdas_all.extend((geo_tr_h + geo_tr_a).tolist())

        geo_h = blend_lambdas(dc_h, feat_h, chosen["dc_weight"])
        geo_a = blend_lambdas(dc_a, feat_a, chosen["dc_weight"])
        rho = 0.5 * (dc.rho_ + feat.rho_)

        mats = matrix_from_lambdas(geo_h, geo_a, rho)
        p_o25 = over_prob(mats, 2.5)

        for i, (_, row) in enumerate(test_df.iterrows()):
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            rec = {
                "match_id": row["match_id"],
                "season": test_season,
                "home_score": hs,
                "away_score": as_,
                "total_score": hs + as_,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "pred_lambda": float(geo_h[i] + geo_a[i]),
                "pred_p_o25": float(p_o25[i]),
            }
            # Record key features
            for f in [
                "home_big_chances_for_roll_10", "away_big_chances_for_roll_10",
                "home_big_chances_against_roll_10", "away_big_chances_against_roll_10",
                "home_shots_ontarget_for_roll_10", "away_shots_ontarget_for_roll_10",
                "home_touches_in_opp_box_roll_10", "away_touches_in_opp_box_roll_10",
                "home_xg_for_roll_10", "away_xg_for_roll_10",
                "home_xg_against_roll_10", "away_xg_against_roll_10",
                "exp_match_shots_5", "home_high_line", "away_high_line", "mutual_high_line_risk"
            ]:
                if f in row:
                    rec[f] = float(row[f])
            records.append(rec)

    res_df = pd.DataFrame(records)
    train_lambdas = np.array(train_lambdas_all)
    q33_train = np.quantile(train_lambdas, 0.3333)
    q66_train = np.quantile(train_lambdas, 0.6667)

    res_df["seg_low"] = res_df["pred_lambda"] < q33_train
    res_df["seg_high"] = res_df["pred_lambda"] >= q66_train
    res_df["seg_mid"] = (~res_df["seg_low"]) & (~res_df["seg_high"])

    # =========================================================================
    # TEST 3.1: GOL DAĞILIMI TESTİ (POISSON MU, NEGATİF BİNOM MU?)
    # =========================================================================
    print("===================================================================")
    print("TEST 3.1: DAĞILIM VE OVERDISPERSION ANALİZİ (POISSON vs NEGATİF BİNOM)")
    print("===================================================================")
    
    cohorts = {
        "Segment 10 (Düşük λ < 2.87)": res_df[res_df["seg_low"]]["total_score"].to_numpy(),
        "Segment High (Yüksek λ >= 3.04)": res_df[res_df["seg_high"]]["total_score"].to_numpy(),
        "Tüm Holdout (1.200 Maç)": res_df["total_score"].to_numpy(),
    }

    for name, goals in cohorts.items():
        n = len(goals)
        mean_g = float(np.mean(goals))
        var_g = float(np.var(goals, ddof=1))
        dispersion_ratio = var_g / mean_g  # Should be 1.0 under Poisson
        
        # Chi-Square test against Poisson
        max_k = 7
        obs_counts = np.bincount(np.clip(goals, 0, max_k), minlength=max_k+1)
        # Expected counts
        exp_probs = [poisson.pmf(k, mean_g) for k in range(max_k)]
        exp_probs.append(1.0 - sum(exp_probs))
        exp_counts = np.array(exp_probs) * n
        
        # Merge bins if expected < 5
        chi2_stat, p_chi2 = chisquare(obs_counts, exp_counts)
        
        # Poisson Log-Likelihood
        ll_poisson = np.sum(poisson.logpmf(goals, mean_g))
        
        # Negative Binomial fit
        r_nb, p_nb, ll_nb = fit_negative_binomial(goals)
        lr_test_stat = 2 * (ll_nb - ll_poisson)  # Likelihood ratio test statistic
        
        print(f"\n--- {name} (N = {n}) ---")
        print(f"  Gerçekleşen Ortalama Gol (Mean):   {mean_g:.3f}")
        print(f"  Gerçekleşen Varyans (Variance):    {var_g:.3f}")
        print(f"  Aşırı Dağılım İndeksi (Var / Mean): {dispersion_ratio:.3f}  ({'AŞIRI DAĞILIM (Overdispersed)' if dispersion_ratio > 1.05 else 'Poisson Uyumlu'})")
        print(f"  Poisson Ki-Kare Testi (Chi2):      stat = {chi2_stat:.2f}, p-value = {p_chi2:.4f}  ({'POISSON REDDEDİLDİ (p < 0.05)' if p_chi2 < 0.05 else 'Poisson Reddedilemez'})")
        print(f"  Poisson Log-Likelihood:            {ll_poisson:.2f}")
        print(f"  Negatif Binom Log-Likelihood:      {ll_nb:.2f} (Delta LL: {ll_nb - ll_poisson:+.2f})")
        print(f"  Negatif Binom Parametreleri:       r = {r_nb:.2f}, p = {p_nb:.4f}")
        print(f"  Likelihood Ratio Test Stat:        {lr_test_stat:.2f} (p < 0.05 gerektirir > 3.84)")

    # =========================================================================
    # TEST 3.2: MEVCUT "KAOS" ÖZELLİKLERİNİN VARYANS VE SİNYAL ANALİZİ
    # =========================================================================
    print("\n" + "="*75)
    print("TEST 3.2: MEVCUT 'KAOS' ÖZELLİKLERİNİN SEGMENT 10 VARYANS VE SİNYAL ANALİZİ")
    print("="*75)
    
    seg10_df = res_df[res_df["seg_low"]].copy()
    high_df = res_df[res_df["seg_high"]].copy()
    
    check_features = [
        ("Toplam Big Chance For (Roll 10)", "home_big_chances_for_roll_10", "away_big_chances_for_roll_10"),
        ("Toplam Big Chance Against (Roll 10)", "home_big_chances_against_roll_10", "away_big_chances_against_roll_10"),
        ("Toplam İsabetli Şut (Roll 10)", "home_shots_ontarget_for_roll_10", "away_shots_ontarget_for_roll_10"),
        ("Ceza Sahası Temas (Roll 10)", "home_touches_in_opp_box_roll_10", "away_touches_in_opp_box_roll_10"),
        ("Toplam xG For (Roll 10)", "home_xg_for_roll_10", "away_xg_for_roll_10"),
        ("Toplam xG Against (Roll 10)", "home_xg_against_roll_10", "away_xg_against_roll_10"),
        ("Beklenen Toplam Şut (exp_match_shots_5)", "exp_match_shots_5", None),
        ("Karşılıklı Yüksek Savunma Hattı", "mutual_high_line_risk", None),
    ]

    print(f"{'ÖZELLİK ADI':<40} | {'SEG 10 ORT':<10} | {'SEG 10 STD':<10} | {'GENEL STD':<10} | {'SEG 10 KORELASYON':<17}")
    print("-" * 95)

    for label, h_col, a_col in check_features:
        if a_col is not None:
            val_seg10 = seg10_df[h_col] + seg10_df[a_col]
            val_all = res_df[h_col] + res_df[a_col]
        else:
            val_seg10 = seg10_df[h_col]
            val_all = res_df[h_col]
            
        mean_s10 = val_seg10.mean()
        std_s10 = val_seg10.std()
        std_all = val_all.std()
        
        # Correlation with actual goals inside Segment 10
        r_p, p_p = pearsonr(val_seg10, seg10_df["total_score"])
        r_s, p_s = spearmanr(val_seg10, seg10_df["total_score"])
        
        print(f"{label:<40} | {mean_s10:<10.3f} | {std_s10:<10.3f} | {std_all:<10.3f} | r={r_p:+.3f} (p={p_p:.3f})")

if __name__ == "__main__":
    main()
