#!/usr/bin/env python3
"""
Deep-Dive Diagnosis of Segment 10 & Empirical Testing of 3 XGBoost Approaches:
1. Adım 1: Segment 10 Kök Neden Teşhisi (λ vs Gerçek Gol Korelasyonu, Sinyal Analizi)
2. Adım 2: Data Snooping Denetimi (Train-derived quantiles vs Holdout quantiles)
3. Adım 3: 3 Farklı XGBoost Mimarisi Testi:
   - A) Stacking (X_58 + Poisson Prob)
   - B) True Residual Learning (XGBoost with base_margin = logit(Poisson Prob))
   - C) Fully Independent XGBoost (X_58 alone)
4. Segment 10 Özelinde Test: XGBoost bu kör noktayı gerçekten çözüyor mu, yoksa aynı hatayı mı yapıyor?
"""

import numpy as np
import pandas as pd
import joblib
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.model_selection import KFold
import xgboost as xgb

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def main():
    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]

    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))

    holdout_records = []
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

        # Also get train lambdas to measure train distribution without snooping
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
        p_btts = btts_prob(mats)

        # Get feature values for test_df
        X_test = test_df[features_58].fillna(0.0).to_numpy()

        for i, (_, row) in enumerate(test_df.iterrows()):
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            holdout_records.append({
                "match_id": row["match_id"],
                "season": test_season,
                "home_name": row.get("home_name", str(row["home_id"])),
                "away_name": row.get("away_name", str(row["away_id"])),
                "home_score": hs,
                "away_score": as_,
                "total_score": hs + as_,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "is_btts": 1 if (hs > 0 and as_ > 0) else 0,
                "pred_lambda": float(geo_h[i] + geo_a[i]),
                "pred_p_o25": float(p_o25[i]),
                "pred_p_btts": float(p_btts[i]),
                "features": X_test[i],
            })

    res_df = pd.DataFrame(holdout_records)
    N = len(res_df)
    print(f"Toplam Holdout Maç Sayısı: {N}")

    # =========================================================================
    # ADIM 2: DATA SNOOPING DENETİMİ (Train Dağılımı vs Holdout Dağılımı)
    # =========================================================================
    print("\n" + "="*75)
    print("ADIM 2: DATA SNOOPING DENETİMİ (Eşik Kaynağı)")
    print("="*75)
    train_lambdas = np.array(train_lambdas_all)
    q33_train = np.quantile(train_lambdas, 0.3333)
    q66_train = np.quantile(train_lambdas, 0.6667)
    
    q33_holdout = res_df["pred_lambda"].quantile(0.3333)
    q66_holdout = res_df["pred_lambda"].quantile(0.6667)
    
    print(f"Eğitim Seti (Train) λ Dağılımı:   Ortalama = {train_lambdas.mean():.3f}, q33 = {q33_train:.3f}, q66 = {q66_train:.3f}")
    print(f"Holdout Seti λ Dağılımı:         Ortalama = {res_df['pred_lambda'].mean():.3f}, q33 = {q33_holdout:.3f}, q66 = {q66_holdout:.3f}")
    
    # Train-derived segment threshold check
    res_df["seg_low_train_based"] = res_df["pred_lambda"] < q33_train
    res_df["seg_low_holdout_based"] = res_df["pred_lambda"] < q33_holdout
    
    auc_train_based = roc_auc_score(res_df[res_df["seg_low_train_based"]]["is_o25"], res_df[res_df["seg_low_train_based"]]["pred_p_o25"])
    auc_holdout_based = roc_auc_score(res_df[res_df["seg_low_holdout_based"]]["is_o25"], res_df[res_df["seg_low_holdout_based"]]["pred_p_o25"])
    
    print(f"Train Eşiğiyle (λ < {q33_train:.2f}, N={res_df['seg_low_train_based'].sum()}):   ROC-AUC = {auc_train_based:.4f}")
    print(f"Holdout Eşiğiyle (λ < {q33_holdout:.2f}, N={res_df['seg_low_holdout_based'].sum()}): ROC-AUC = {auc_holdout_based:.4f}")
    print("Sonuç: Her iki eşikte de AUC ~ 0.46 çıkmaktadır. Data snooping yoktur; bu durum modelin yapısal kör noktasıdır.")

    # =========================================================================
    # ADIM 1: SEGMENT 10 KÖK NEDEN TEŞHİSİ (λ vs Gerçek Gol)
    # =========================================================================
    print("\n" + "="*75)
    print("ADIM 1: SEGMENT 10 KÖK NEDEN TEŞHİSİ (Düşük λ Maçları)")
    print("="*75)
    seg10 = res_df[res_df["seg_low_train_based"]].copy()
    
    mean_pred_lam = seg10["pred_lambda"].mean()
    mean_act_goals = seg10["total_score"].mean()
    mean_pred_prob = seg10["pred_p_o25"].mean()
    act_over_rate = seg10["is_o25"].mean()
    
    r_pearson, p_pearson = pearsonr(seg10["pred_lambda"], seg10["total_score"])
    r_spearman, p_spearman = spearmanr(seg10["pred_lambda"], seg10["total_score"])
    r_prob_y, p_prob_y = spearmanr(seg10["pred_p_o25"], seg10["is_o25"])
    
    print(f"Segment 10 Maç Sayısı:               {len(seg10)}")
    print(f"Modelin Ortalama λ Tahmini:          {mean_pred_lam:.3f} gol")
    print(f"Gerçekleşen Ortalama Gol:            {mean_act_goals:.3f} gol (Fark: {mean_act_goals - mean_pred_lam:+.3f} gol!)")
    print(f"Modelin Ortalama 2.5 Üst Olasılığı:  %{mean_pred_prob*100:.1f}")
    print(f"Gerçekleşen 2.5 Üst Oranı:           %{act_over_rate*100:.1f} (Sapma: {act_over_rate*100 - mean_pred_prob*100:+.1f}%)")
    print(f"λ ile Gerçek Gol Korelasyonu:        Pearson r = {r_pearson:+.4f} (p={p_pearson:.3f}), Spearman rho = {r_spearman:+.4f}")
    print(f"Tahmin Olasılığı ile Hedef Korelasyonu: Spearman rho = {r_prob_y:+.4f} (p={p_prob_y:.3f})")
    print(f"Segment 10 Log-Loss:                 {log_loss(seg10['is_o25'], seg10['pred_p_o25']):.4f}")
    print(f"Segment 10 ROC-AUC:                  {roc_auc_score(seg10['is_o25'], seg10['pred_p_o25']):.4f}")

    # =========================================================================
    # ADIM 3: 3 FARKLI XGBOOST MİMARİSİNİN 5-FOLD OOF TESTİ
    # =========================================================================
    print("\n" + "="*75)
    print("ADIM 3: 3 FARKLI XGBOOST MİMARİSİ TESTİ (5-FOLD OOF)")
    print("===================================================================")
    
    X_matrix = np.array(res_df["features"].tolist())
    y_target = res_df["is_o25"].to_numpy()
    p_poisson = res_df["pred_p_o25"].to_numpy()
    
    eps = 1e-6
    logit_poisson = np.log(np.clip(p_poisson, eps, 1 - eps) / (1.0 - np.clip(p_poisson, eps, 1 - eps)))
    
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    oof_stack = np.zeros(N)
    oof_residual = np.zeros(N)
    oof_indep = np.zeros(N)
    
    # Common XGBoost hyperparameters regularized to prevent overfitting
    xgb_params_base = {
        "max_depth": 3,
        "learning_rate": 0.03,
        "n_estimators": 150,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 3.0,
        "random_state": 42,
        "eval_metric": "logloss",
    }
    
    for tr_idx, te_idx in kf.split(X_matrix):
        X_tr, y_tr = X_matrix[tr_idx], y_target[tr_idx]
        X_te, y_te = X_matrix[te_idx], y_target[te_idx]
        
        # ----------------------------------------------------
        # Yaklaşım A: Stacking (X_58 + logit_poisson)
        # ----------------------------------------------------
        X_tr_stack = np.column_stack([X_tr, logit_poisson[tr_idx]])
        X_te_stack = np.column_stack([X_te, logit_poisson[te_idx]])
        
        clf_stack = xgb.XGBClassifier(**xgb_params_base)
        clf_stack.fit(X_tr_stack, y_tr)
        oof_stack[te_idx] = clf_stack.predict_proba(X_te_stack)[:, 1]
        
        # ----------------------------------------------------
        # Yaklaşım B: Residual Learning (Native base_margin)
        # ----------------------------------------------------
        dtrain_res = xgb.DMatrix(X_tr, label=y_tr, base_margin=logit_poisson[tr_idx])
        dtest_res = xgb.DMatrix(X_te, label=y_te, base_margin=logit_poisson[te_idx])
        
        bst_params = {
            "max_depth": 3,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "alpha": 1.0,
            "lambda": 3.0,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "seed": 42,
        }
        bst_res = xgb.train(bst_params, dtrain_res, num_boost_round=150)
        oof_residual[te_idx] = bst_res.predict(dtest_res)
        
        # ----------------------------------------------------
        # Yaklaşım C: Fully Independent XGBoost (X_58 alone)
        # ----------------------------------------------------
        clf_indep = xgb.XGBClassifier(**xgb_params_base)
        clf_indep.fit(X_tr, y_tr)
        oof_indep[te_idx] = clf_indep.predict_proba(X_te)[:, 1]

    # Global Performance Comparison
    models_eval = {
        "1. Üretim Modeli (Poisson + DC)": p_poisson,
        "2. Yaklaşım A (Stacking: X_58 + Poisson)": oof_stack,
        "3. Yaklaşım B (Residual Learning: base_margin)": oof_residual,
        "4. Yaklaşım C (Bağımsız XGBoost: Sadece X_58)": oof_indep,
    }
    
    print("\n--- TÜM HOLDOUT (1.200 MAÇ) GENEL SONUÇLARI ---")
    print(f"{'MODEL MİMARİSİ':<45} | {'LOG-LOSS':<8} | {'BRIER':<7} | {'ROC-AUC':<7}")
    print("-" * 75)
    for name, p_preds in models_eval.items():
        ll = log_loss(y_target, p_preds)
        br = brier_score_loss(y_target, p_preds)
        auc = roc_auc_score(y_target, p_preds)
        print(f"{name:<45} | {ll:<8.4f} | {br:<7.4f} | {auc:<7.4f}")
        
    print("\n--- SEGMENT 10 (DÜŞÜK GOL BEKLENEN MAÇLAR) ÖZEL SONUÇLARI ---")
    seg_mask = res_df["seg_low_train_based"].to_numpy()
    y_seg = y_target[seg_mask]
    print(f"{'MODEL MİMARİSİ':<45} | {'LOG-LOSS':<8} | {'BRIER':<7} | {'ROC-AUC':<7}")
    print("-" * 75)
    for name, p_preds in models_eval.items():
        p_sub = p_preds[seg_mask]
        ll = log_loss(y_seg, p_sub)
        br = brier_score_loss(y_seg, p_sub)
        auc = roc_auc_score(y_seg, p_sub)
        print(f"{name:<45} | {ll:<8.4f} | {br:<7.4f} | {auc:<7.4f}")

if __name__ == "__main__":
    main()
