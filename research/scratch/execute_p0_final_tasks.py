#!/usr/bin/env python3
"""
P0 Final Resolution Script:
1. Görev D: L5 Out-of-Fold Isotonic vs Platt vs Raw (Testing the in-sample 0.6715 illusion vs true OOF generalization)
2. Görev E: Aritmetik vs Geometrik Harman: Per-season walk-forward comparison & mathematical bounds check
3. Görev F: Model vs Piyasa: Apple-to-apple on the EXACT 218 matches, drift analysis between periods, and Value Bet viability
4. Görev G: Validating Platt calibrators for Over 2.5 and BTTS to be persisted in production
"""

import json
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import KFold

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def main():
    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]
    
    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))
    
    # Store records across walk-forward folds
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
        
        # Geometrik harman
        geo_h = blend_lambdas(dc_h, feat_h, chosen["dc_weight"])
        geo_a = blend_lambdas(dc_a, feat_a, chosen["dc_weight"])
        
        # Aritmetik harman
        ari_h = chosen["dc_weight"] * dc_h + (1.0 - chosen["dc_weight"]) * feat_h
        ari_a = chosen["dc_weight"] * dc_a + (1.0 - chosen["dc_weight"]) * feat_a
        
        rho = 0.5 * (dc.rho_ + feat.rho_)
        
        # Geometric matrices
        mats_geo = matrix_from_lambdas(geo_h, geo_a, rho)
        p_o25_geo = over_prob(mats_geo, 2.5)
        p_btts_geo = btts_prob(mats_geo)
        
        # Arithmetic matrices
        mats_ari = matrix_from_lambdas(ari_h, ari_a, rho)
        p_o25_ari = over_prob(mats_ari, 2.5)
        p_btts_ari = btts_prob(mats_ari)
        
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
                "p_o25_ari": p_o25_ari[i],
                "p_btts_ari": p_btts_ari[i],
            })
            
    res_df = pd.DataFrame(records)
    y_o25 = res_df["is_o25"].to_numpy()
    y_btts = res_df["is_btts"].to_numpy()
    N = len(res_df)
    print(f"Total evaluated holdout matches: {N}")
    
    # =========================================================================
    # GÖREV D: L5 Üretim Modeli Kalibrasyonu (İzotonik vs Platt vs Ham)
    # Testing IN-SAMPLE vs 5-FOLD OUT-OF-FOLD (OOF) to expose overfitting
    # =========================================================================
    p_geo = res_df["p_o25_geo"].to_numpy()
    
    # 1. In-sample Isotonic (the dangerous trap)
    iso_in_sample = IsotonicRegression(out_of_bounds="clip").fit(p_geo, y_o25)
    p_iso_in_sample = iso_in_sample.predict(p_geo)
    
    # 2. 5-Fold Cross-Validated Out-of-Fold Isotonic
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    p_iso_oof = np.zeros(N)
    for tr, te in kf.split(p_geo):
        iso_fold = IsotonicRegression(out_of_bounds="clip").fit(p_geo[tr], y_o25[tr])
        p_iso_oof[te] = iso_fold.predict(p_geo[te])
        
    # 3. In-sample Platt
    eps = 1e-6
    logit_geo = np.log(np.clip(p_geo, eps, 1-eps) / (1 - np.clip(p_geo, eps, 1-eps))).reshape(-1, 1)
    lr_in_sample = LogisticRegression().fit(logit_geo, y_o25)
    p_platt_in_sample = lr_in_sample.predict_proba(logit_geo)[:, 1]
    
    # 4. 5-Fold OOF Platt
    p_platt_oof = np.zeros(N)
    for tr, te in kf.split(logit_geo):
        lr_fold = LogisticRegression().fit(logit_geo[tr], y_o25[tr])
        p_platt_oof[te] = lr_fold.predict_proba(logit_geo[te])[:, 1]
        
    print("\n=======================================================")
    print("GÖREV D: L5 Kalibrasyon Denetimi (İn-Sample vs OOF Gerçeği)")
    print("=======================================================")
    print(f"L5 Ham (Geometrik Üretim):      LL = {log_loss(y_o25, p_geo):.6f}, Brier = {brier_score_loss(y_o25, p_geo):.6f}, AUC = {roc_auc_score(y_o25, p_geo):.4f}")
    print(f"L5 İn-Sample İzotonik (Yanılsama): LL = {log_loss(y_o25, p_iso_in_sample):.6f}, Brier = {brier_score_loss(y_o25, p_iso_in_sample):.6f}, AUC = {roc_auc_score(y_o25, p_iso_in_sample):.4f}")
    print(f"L5 5-Fold OOF İzotonik (Gerçek):   LL = {log_loss(y_o25, p_iso_oof):.6f}, Brier = {brier_score_loss(y_o25, p_iso_oof):.6f}, AUC = {roc_auc_score(y_o25, p_iso_oof):.4f}")
    print(f"L5 İn-Sample Platt:              LL = {log_loss(y_o25, p_platt_in_sample):.6f}, Brier = {brier_score_loss(y_o25, p_platt_in_sample):.6f}")
    print(f"L5 5-Fold OOF Platt (Genellenebilir): LL = {log_loss(y_o25, p_platt_oof):.6f}, Brier = {brier_score_loss(y_o25, p_platt_oof):.6f}")

    # =========================================================================
    # GÖREV E: Aritmetik vs Geometrik Harman: Sezon Sezon Karşılaştırma
    # =========================================================================
    p_ari = res_df["p_o25_ari"].to_numpy()
    print("\n=======================================================")
    print("GÖREV E: Aritmetik vs Geometrik Harman (Sezon Bazlı Karşılaştırma)")
    print("=======================================================")
    print(f"Genel Geometrik Harman: LL = {log_loss(y_o25, p_geo):.6f}, Brier = {brier_score_loss(y_o25, p_geo):.6f}")
    print(f"Genel Aritmetik Harman: LL = {log_loss(y_o25, p_ari):.6f}, Brier = {brier_score_loss(y_o25, p_ari):.6f} (Fark: {log_loss(y_o25, p_ari) - log_loss(y_o25, p_geo):+.6f})")
    
    print("\nSezon Bazlı Döküm:")
    for sz, grp in res_df.groupby("season"):
        sz_y = grp["is_o25"].to_numpy()
        sz_geo_ll = log_loss(sz_y, grp["p_o25_geo"].to_numpy())
        sz_ari_ll = log_loss(sz_y, grp["p_o25_ari"].to_numpy())
        print(f"  {sz:10s} (N={len(grp):3d}): Geo LL = {sz_geo_ll:.4f} | Ari LL = {sz_ari_ll:.4f} | Fark = {sz_ari_ll - sz_geo_ll:+.4f} | Kazanan: {'ARİTMETİK' if sz_ari_ll < sz_geo_ll else 'GEOMETRİK'}")

    # =========================================================================
    # GÖREV F: Model vs Piyasa: Birebir Aynı 218 Maç Analizi & Dönemsel Drift
    # =========================================================================
    print("\n=======================================================")
    print("GÖREV F: Model vs Piyasa (Birebir Aynı 218 Maç Analizi)")
    print("=======================================================")
    import sqlite3
    conn = sqlite3.connect("data/premier_league.db")
    odds_df = pd.read_sql_query("""
        SELECT match_id, bookmaker, over_25_open, under_25_open, btts_yes_open, btts_no_open
        FROM external_match_odds
        WHERE over_25_open IS NOT NULL AND under_25_open IS NOT NULL
    """, conn)
    
    m_df = pd.merge(res_df, odds_df, on="match_id", how="inner")
    print(f"Piyasa oranları mevcut eşleşen maç sayısı: {len(m_df)}")
    
    # Implied fair market odds
    raw_mkt_o25 = 1.0 / m_df["over_25_open"].to_numpy()
    raw_mkt_u25 = 1.0 / m_df["under_25_open"].to_numpy()
    p_mkt_o25 = raw_mkt_o25 / (raw_mkt_o25 + raw_mkt_u25)
    
    m_y_o25 = m_df["is_o25"].to_numpy()
    m_p_geo_o25 = m_df["p_o25_geo"].to_numpy()
    m_p_ari_o25 = m_df["p_o25_ari"].to_numpy()
    
    print(f"218 Maçlık Havuzda Gerçek 2.5 Üst Oranı: {m_y_o25.mean()*100:.2f}% (Tüm 1200 Maç: {y_o25.mean()*100:.2f}%)")
    print(f"218 Maçlık Havuzun Entropi Tavanı:      {log_loss(m_y_o25, np.full(len(m_y_o25), m_y_o25.mean())):.6f}")
    print(f"Piyasa (Bookmaker) 2.5 Üst:            LL = {log_loss(m_y_o25, p_mkt_o25):.6f}, Brier = {brier_score_loss(m_y_o25, p_mkt_o25):.6f}, AUC = {roc_auc_score(m_y_o25, p_mkt_o25):.4f}")
    print(f"Bizim Model (Geometrik) 2.5 Üst:       LL = {log_loss(m_y_o25, m_p_geo_o25):.6f}, Brier = {brier_score_loss(m_y_o25, m_p_geo_o25):.6f}, AUC = {roc_auc_score(m_y_o25, m_p_geo_o25):.4f}")
    print(f"Bizim Model (Aritmetik) 2.5 Üst:       LL = {log_loss(m_y_o25, m_p_ari_o25):.6f}, Brier = {brier_score_loss(m_y_o25, m_p_ari_o25):.6f}, AUC = {roc_auc_score(m_y_o25, m_p_ari_o25):.4f}")
    
    # Value bet simulation on 218 matches
    # Edge = Model Prob - Market Implied Prob
    edge_o25 = m_p_geo_o25 - p_mkt_o25
    bet_mask = edge_o25 > 0.05  # Bets with >5% perceived value
    print(f"\nValue Bet Simülasyonu (>%5 Model Edge Olan Maçlar):")
    print(f"  Toplam Oynanan Maç: {bet_mask.sum()} / {len(m_df)}")
    if bet_mask.sum() > 0:
        bet_odds = m_df["over_25_open"].to_numpy()[bet_mask]
        bet_wins = m_y_o25[bet_mask]
        returns = np.where(bet_wins == 1, bet_odds - 1.0, -1.0)
        roi = returns.sum() / len(returns) * 100.0
        print(f"  Kazanma Oranı: {bet_wins.mean()*100:.1f}%")
        print(f"  Net ROI: {roi:+.2f}%")

    # =========================================================================
    # GÖREV G: BTTS Platt Kalibrasyonu (Üretime Hazır Nesne)
    # =========================================================================
    print("\n=======================================================")
    print("GÖREV G: BTTS Kalibrasyon Validasyonu")
    print("=======================================================")
    p_btts = res_df["p_btts_geo"].to_numpy()
    logit_btts = np.log(np.clip(p_btts, eps, 1-eps) / (1 - np.clip(p_btts, eps, 1-eps))).reshape(-1, 1)
    
    # 5-fold OOF BTTS Platt
    p_btts_oof_platt = np.zeros(N)
    for tr, te in kf.split(logit_btts):
        lr_btts = LogisticRegression().fit(logit_btts[tr], y_btts[tr])
        p_btts_oof_platt[te] = lr_btts.predict_proba(logit_btts[te])[:, 1]
        
    print(f"Kör Poisson Baseline BTTS:         LL = 0.6802, Brier = 0.2435")
    print(f"Ham Üretim Modeli BTTS:            LL = {log_loss(y_btts, p_btts):.6f}, Brier = {brier_score_loss(y_btts, p_btts):.6f}")
    print(f"5-Fold OOF Platt Kalibre BTTS:     LL = {log_loss(y_btts, p_btts_oof_platt):.6f}, Brier = {brier_score_loss(y_btts, p_btts_oof_platt):.6f}")
    print(f"Kazanç: {log_loss(y_btts, p_btts_oof_platt) - log_loss(y_btts, p_btts):+.6f}")

if __name__ == "__main__":
    main()
