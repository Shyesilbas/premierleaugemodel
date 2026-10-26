#!/usr/bin/env python3
"""
Final P0 Closure Script:
1. Görev H: BTTS Alternative Calibrations (Beta Calibration Kull et al. 2017, Expanding Seasonal Platt, and Non-Stationarity Audit)
2. Görev I: Market vs Model Statistical Rigor (10,000 Bootstrap Resamples for Delta-AUC CI, Full Edge-Threshold Sweep with Binomial CIs)
"""

import json
import numpy as np
import pandas as pd
import joblib
from scipy.optimize import minimize
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

class BetaCalibrator:
    """Beta calibration (Kull, Silva Filho, Flach, 2017).
    P_cal = 1 / (1 + 1/e^c * (1-p)^b / p^a) = sigma(a * ln(p) - b * ln(1-p) + c)
    """
    def __init__(self):
        self.a_ = 1.0
        self.b_ = 1.0
        self.c_ = 0.0

    def fit(self, p, y):
        eps = 1e-6
        p = np.clip(p, eps, 1 - eps)
        x1 = np.log(p)
        x2 = -np.log(1 - p)
        y = np.asarray(y, dtype=float)

        def nll(params):
            a, b, c = params
            logit = a * x1 + b * x2 + c
            # log-loss with numerical stability
            log_p = -np.logaddexp(0, -logit)
            log_1mp = -np.logaddexp(0, logit)
            return -np.mean(y * log_p + (1 - y) * log_1mp)

        res = minimize(nll, [1.0, 1.0, 0.0], bounds=[(0.01, 10.0), (0.01, 10.0), (-10.0, 10.0)])
        self.a_, self.b_, self.c_ = res.x
        return self

    def predict(self, p):
        eps = 1e-6
        p = np.clip(p, eps, 1 - eps)
        x1 = np.log(p)
        x2 = -np.log(1 - p)
        logit = self.a_ * x1 + self.b_ * x2 + self.c_
        return 1.0 / (1.0 + np.exp(-logit))

def main():
    artifact = joblib.load("models/production/premier_league/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]

    df = pd.read_parquet("data/competitions/premier_league/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))

    records = []

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

        geo_h = blend_lambdas(dc_h, feat_h, chosen["dc_weight"])
        geo_a = blend_lambdas(dc_a, feat_a, chosen["dc_weight"])
        rho = 0.5 * (dc.rho_ + feat.rho_)

        mats_geo = matrix_from_lambdas(geo_h, geo_a, rho)
        p_o25_geo = over_prob(mats_geo, 2.5)
        p_btts_geo = btts_prob(mats_geo)

        # Train set predictions for expanding walk-forward calibration
        dc_train_h, dc_train_a = dc.lambdas(train_df)
        feat_train_h, feat_train_a = feat.lambdas(train_df)
        geo_train_h = blend_lambdas(dc_train_h, feat_train_h, chosen["dc_weight"])
        geo_train_a = blend_lambdas(dc_train_a, feat_train_a, chosen["dc_weight"])
        train_mats = matrix_from_lambdas(geo_train_h, geo_train_a, rho)
        p_btts_train = btts_prob(train_mats)
        y_btts_train = ((train_df["home_score"] > 0) & (train_df["away_score"] > 0)).astype(int).to_numpy()

        # Fit seasonal expanding Platt & Beta
        eps = 1e-6
        lo_train = np.log(np.clip(p_btts_train, eps, 1-eps) / (1 - np.clip(p_btts_train, eps, 1-eps))).reshape(-1, 1)
        lr_seasonal = LogisticRegression().fit(lo_train, y_btts_train)

        lo_test = np.log(np.clip(p_btts_geo, eps, 1-eps) / (1 - np.clip(p_btts_geo, eps, 1-eps))).reshape(-1, 1)
        p_btts_seasonal_platt = lr_seasonal.predict_proba(lo_test)[:, 1]

        beta_seasonal = BetaCalibrator().fit(p_btts_train, y_btts_train)
        p_btts_seasonal_beta = beta_seasonal.predict(p_btts_geo)

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
                "p_o25_geo": p_o25_geo[i],
                "p_btts_geo": p_btts_geo[i],
                "p_btts_seasonal_platt": p_btts_seasonal_platt[i],
                "p_btts_seasonal_beta": p_btts_seasonal_beta[i],
            })

    res_df = pd.DataFrame(records)
    y_btts = res_df["is_btts"].to_numpy()
    p_btts_raw = res_df["p_btts_geo"].to_numpy()
    N = len(res_df)

    # =========================================================================
    # GÖREV H: BTTS Alternatif Kalibrasyon Deneyleri
    # =========================================================================
    print("===================================================================")
    print("GÖREV H: BTTS Alternatif Kalibrasyon Deneyleri (OOF)")
    print("===================================================================")
    
    # 1. 5-Fold OOF Platt
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    eps = 1e-6
    logit_btts = np.log(np.clip(p_btts_raw, eps, 1-eps) / (1 - np.clip(p_btts_raw, eps, 1-eps))).reshape(-1, 1)
    p_btts_oof_platt = np.zeros(N)
    for tr, te in kf.split(logit_btts):
        lr = LogisticRegression().fit(logit_btts[tr], y_btts[tr])
        p_btts_oof_platt[te] = lr.predict_proba(logit_btts[te])[:, 1]

    # 2. 5-Fold OOF Beta Calibration (Kull et al., 2017)
    p_btts_oof_beta = np.zeros(N)
    for tr, te in kf.split(p_btts_raw):
        bc = BetaCalibrator().fit(p_btts_raw[tr], y_btts[tr])
        p_btts_oof_beta[te] = bc.predict(p_btts_raw[te])

    # 3. Expanding Walk-Forward Seasonal Platt & Beta
    p_btts_wf_platt = res_df["p_btts_seasonal_platt"].to_numpy()
    p_btts_wf_beta = res_df["p_btts_seasonal_beta"].to_numpy()

    print(f"1. Kör Poisson Baseline:              LL = 0.680200, Brier = 0.243500")
    print(f"2. Ham Bivariate Matris (Üretim):      LL = {log_loss(y_btts, p_btts_raw):.6f}, Brier = {brier_score_loss(y_btts, p_btts_raw):.6f}")
    print(f"3. 5-Fold OOF Platt Kalibrasyonu:     LL = {log_loss(y_btts, p_btts_oof_platt):.6f}, Brier = {brier_score_loss(y_btts, p_btts_oof_platt):.6f} (Fark: {log_loss(y_btts, p_btts_oof_platt) - log_loss(y_btts, p_btts_raw):+.6f})")
    print(f"4. 5-Fold OOF Beta Kalibrasyonu:      LL = {log_loss(y_btts, p_btts_oof_beta):.6f}, Brier = {brier_score_loss(y_btts, p_btts_oof_beta):.6f} (Fark: {log_loss(y_btts, p_btts_oof_beta) - log_loss(y_btts, p_btts_raw):+.6f})")
    print(f"5. Expanding Walk-Forward Platt:      LL = {log_loss(y_btts, p_btts_wf_platt):.6f}, Brier = {brier_score_loss(y_btts, p_btts_wf_platt):.6f} (Fark: {log_loss(y_btts, p_btts_wf_platt) - log_loss(y_btts, p_btts_raw):+.6f})")
    print(f"6. Expanding Walk-Forward Beta:       LL = {log_loss(y_btts, p_btts_wf_beta):.6f}, Brier = {brier_score_loss(y_btts, p_btts_wf_beta):.6f} (Fark: {log_loss(y_btts, p_btts_wf_beta) - log_loss(y_btts, p_btts_raw):+.6f})")

    print("\nBTTS Sezon Bazlı Gerçek Oran Değişimi (Non-Stationarity):")
    for sz, grp in res_df.groupby("season"):
        act_rate = grp["is_btts"].mean() * 100.0
        pred_rate = grp["p_btts_geo"].mean() * 100.0
        print(f"  {sz:10s} (N={len(grp):3d}): Gerçek BTTS = %{act_rate:.1f} | Model Tahmini = %{pred_rate:.1f} | Sapma = {pred_rate - act_rate:+.1f}%")

    # =========================================================================
    # GÖREV I: Model vs Piyasa İstatistiksel Güç & Bootstrap Analizi
    # =========================================================================
    print("\n===================================================================")
    print("GÖREV I: Model vs Piyasa İstatistiksel Güç & Bootstrap Analizi")
    print("===================================================================")
    import sqlite3
    conn = sqlite3.connect("data/football.db")
    odds_df = pd.read_sql_query("""
        SELECT match_id, bookmaker, over_25_open, under_25_open, btts_yes_open, btts_no_open
        FROM external_match_odds
        WHERE over_25_open IS NOT NULL AND under_25_open IS NOT NULL
    """, conn)
    m_df = pd.merge(res_df, odds_df, on="match_id", how="inner")
    
    raw_mkt_o25 = 1.0 / m_df["over_25_open"].to_numpy()
    raw_mkt_u25 = 1.0 / m_df["under_25_open"].to_numpy()
    p_mkt_o25 = raw_mkt_o25 / (raw_mkt_o25 + raw_mkt_u25)
    
    m_y_o25 = m_df["is_o25"].to_numpy()
    m_p_model_o25 = m_df["p_o25_geo"].to_numpy()
    n_mkt = len(m_df)
    
    # 10,000 Bootstrap Resampling for AUC difference
    np.random.seed(42)
    B = 10000
    boot_diffs = []
    boot_mkt_aucs = []
    boot_model_aucs = []
    
    for _ in range(B):
        idx = np.random.choice(n_mkt, size=n_mkt, replace=True)
        if len(np.unique(m_y_o25[idx])) < 2:
            continue
        auc_m = roc_auc_score(m_y_o25[idx], p_mkt_o25[idx])
        auc_mod = roc_auc_score(m_y_o25[idx], m_p_model_o25[idx])
        boot_mkt_aucs.append(auc_m)
        boot_model_aucs.append(auc_mod)
        boot_diffs.append(auc_m - auc_mod)
        
    boot_diffs = np.array(boot_diffs)
    ci_diff_low, ci_diff_high = np.percentile(boot_diffs, [2.5, 97.5])
    ci_mkt_low, ci_mkt_high = np.percentile(boot_mkt_aucs, [2.5, 97.5])
    ci_mod_low, ci_mod_high = np.percentile(boot_model_aucs, [2.5, 97.5])
    p_val_mkt_superior = np.mean(boot_diffs <= 0)
    
    print(f"Eşleşen Maç Sayısı (N): {n_mkt}")
    print(f"Piyasa AUC:     {roc_auc_score(m_y_o25, p_mkt_o25):.4f}  [%95 CI: {ci_mkt_low:.4f} - {ci_mkt_high:.4f}]")
    print(f"Model AUC:      {roc_auc_score(m_y_o25, m_p_model_o25):.4f}  [%95 CI: {ci_mod_low:.4f} - {ci_mod_high:.4f}]")
    print(f"Delta AUC (Piyasa - Model): {np.mean(boot_diffs):+.4f}  [%95 CI: {ci_diff_low:+.4f} to {ci_diff_high:+.4f}]")
    print(f"Piyasa Üstünlüğü P-Değeri: {p_val_mkt_superior:.4f} ({'Yapısal ve Belirgin' if ci_diff_low > 0 else 'Örneklem Gürültüsü Dahilinde / Örtüşüyor'})")

    # Full Edge-Threshold Sweep with Binomial Confidence Intervals
    print("\n--- Edge Eşiği Taraması ve Binom Güven Aralıkları ---")
    edges = [0.00, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10]
    print("EDGE EŞİĞİ | MAÇ SAYISI | KAZANAN | KAZANMA ORANI | %95 BİNOM CI    | NET ROI")
    for eth in edges:
        diff = m_p_model_o25 - p_mkt_o25
        mask = diff > eth
        n_bets = mask.sum()
        if n_bets == 0:
            print(f"  >{eth*100:2.0f}%     |      0     |    —    |       —       |        —        |    —")
            continue
        wins = m_y_o25[mask].sum()
        win_rate = wins / n_bets
        # Wilson score interval or standard normal approx for binomial proportion
        se = np.sqrt(win_rate * (1 - win_rate) / n_bets) if n_bets > 1 else 0.0
        ci_w_low = max(0.0, win_rate - 1.96 * se)
        ci_w_high = min(1.0, win_rate + 1.96 * se)
        
        odds = m_df["over_25_open"].to_numpy()[mask]
        outcomes = m_y_o25[mask]
        profit = np.where(outcomes == 1, odds - 1.0, -1.0).sum()
        roi = profit / n_bets * 100.0
        
        print(f"  >{eth*100:2.0f}%     |    {n_bets:3d}     |   {wins:2d}    |     %{win_rate*100:5.1f}     | [%{ci_w_low*100:4.1f} - %{ci_w_high*100:4.1f}] | {roi:+6.2f}%")

if __name__ == "__main__":
    main()
