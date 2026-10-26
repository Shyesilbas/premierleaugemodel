#!/usr/bin/env python3
"""
P1 Final Verifications:
1. Feature Ablation: 58 vs 57 features (dropping effective_log_mv_ratio) across 1,200 holdout matches.
   10,000 Bootstrap test on Delta Log-Loss and Delta AUC.
2. Edge Sweep Multiple Testing: 7 thresholds (0%, 2%, 3%, 4%, 5%, 7%, 10%) on 218 market odds matches.
   Binomial test and ROI permutation test with Bonferroni and Benjamini-Hochberg FDR corrections.
"""

import numpy as np
import pandas as pd
import joblib
from scipy import stats
from sklearn.metrics import log_loss, roc_auc_score, brier_score_loss

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def benjamini_hochberg(p_values):
    p_values = np.asarray(p_values)
    n = len(p_values)
    order = np.argsort(p_values)
    ranked_p = p_values[order]
    q_vals = np.zeros(n)
    running_min = 1.0
    for i in range(n - 1, -1, -1):
        q = (ranked_p[i] * n) / (i + 1)
        running_min = min(running_min, q)
        q_vals[i] = min(running_min, 1.0)
    res = np.zeros(n)
    res[order] = q_vals
    return res

def main():
    print("===================================================================")
    print("1. AKSİYON 1: EFFECTIVE_LOG_MV_RATIO ABLASYON TESTİ (58 vs 57 ÖZELLİK)")
    print("===================================================================")

    artifact = joblib.load("models/production/premier_league/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]
    features_57 = [f for f in features_58 if f != "effective_log_mv_ratio"]

    df = pd.read_parquet("data/competitions/premier_league/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))

    y_all = []
    p_58_all = []
    p_57_all = []

    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]

        if len(train_df) < 300 or len(test_df) == 0:
            continue

        dc = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
        dc_h, dc_a = dc.lambdas(test_df)

        # 58 features
        feat_58 = FeatureGoalModel(features=features_58, alpha=chosen["feature_alpha"]).fit(train_df)
        f58_h, f58_a = feat_58.lambdas(test_df)
        geo58_h = blend_lambdas(dc_h, f58_h, chosen["dc_weight"])
        geo58_a = blend_lambdas(dc_a, f58_a, chosen["dc_weight"])
        rho58 = 0.5 * (dc.rho_ + feat_58.rho_)
        mats58 = matrix_from_lambdas(geo58_h, geo58_a, rho58)
        p_58 = over_prob(mats58, 2.5)

        # 57 features (without effective_log_mv_ratio)
        feat_57 = FeatureGoalModel(features=features_57, alpha=chosen["feature_alpha"]).fit(train_df)
        f57_h, f57_a = feat_57.lambdas(test_df)
        geo57_h = blend_lambdas(dc_h, f57_h, chosen["dc_weight"])
        geo57_a = blend_lambdas(dc_a, f57_a, chosen["dc_weight"])
        rho57 = 0.5 * (dc.rho_ + feat_57.rho_)
        mats57 = matrix_from_lambdas(geo57_h, geo57_a, rho57)
        p_57 = over_prob(mats57, 2.5)

        hs = test_df["home_score"].to_numpy(dtype=int)
        as_ = test_df["away_score"].to_numpy(dtype=int)
        y_true = ((hs + as_) > 2.5).astype(int)

        y_all.extend(y_true)
        p_58_all.extend(p_58)
        p_57_all.extend(p_57)

    y_all = np.array(y_all)
    p_58_all = np.array(p_58_all)
    p_57_all = np.array(p_57_all)
    N = len(y_all)

    ll_58 = log_loss(y_all, p_58_all)
    br_58 = brier_score_loss(y_all, p_58_all)
    auc_58 = roc_auc_score(y_all, p_58_all)

    ll_57 = log_loss(y_all, p_57_all)
    br_57 = brier_score_loss(y_all, p_57_all)
    auc_57 = roc_auc_score(y_all, p_57_all)

    print(f"Toplam Değerlendirilen Holdout Maç: {N}")
    print(f"58 Özellik (Mevcut Üretim) : Log-Loss = {ll_58:.6f}, Brier = {br_58:.6f}, AUC = {auc_58:.6f}")
    print(f"57 Özellik (MV Ratio Silindi): Log-Loss = {ll_57:.6f}, Brier = {br_57:.6f}, AUC = {auc_57:.6f}")
    print(f"Fark (57 - 58)             : ΔLL = {ll_57 - ll_58:+.6f}, ΔAUC = {auc_57 - auc_58:+.6f}")

    # 10,000 Bootstrap on Delta Log-Loss and Delta AUC
    rng = np.random.RandomState(42)
    boot_delta_ll = []
    boot_delta_auc = []

    for _ in range(10000):
        idx = rng.randint(0, N, size=N)
        b_y = y_all[idx]
        b_58 = p_58_all[idx]
        b_57 = p_57_all[idx]

        b_ll_58 = log_loss(b_y, b_58)
        b_ll_57 = log_loss(b_y, b_57)
        boot_delta_ll.append(b_ll_57 - b_ll_58)

        b_auc_58 = roc_auc_score(b_y, b_58)
        b_auc_57 = roc_auc_score(b_y, b_57)
        boot_delta_auc.append(b_auc_57 - b_auc_58)

    ci_ll = np.percentile(boot_delta_ll, [2.5, 97.5])
    p_val_ll = 2.0 * min(np.mean(np.array(boot_delta_ll) >= 0), np.mean(np.array(boot_delta_ll) <= 0))

    ci_auc = np.percentile(boot_delta_auc, [2.5, 97.5])
    p_val_auc = 2.0 * min(np.mean(np.array(boot_delta_auc) >= 0), np.mean(np.array(boot_delta_auc) <= 0))

    print(f"\n10.000 Bootstrap ΔLL (57 - 58):  %95 CI [{ci_ll[0]:+.6f}, {ci_ll[1]:+.6f}], p = {p_val_ll:.4f}")
    print(f"10.000 Bootstrap ΔAUC (57 - 58): %95 CI [{ci_auc[0]:+.6f}, {ci_auc[1]:+.6f}], p = {p_val_auc:.4f}")

    # =====================================================================
    # 2. AKSİYON 2: EDGE SWEEP MULTIPLE TESTING (7 EŞİK)
    # =====================================================================
    print("\n===================================================================")
    print("2. AKSİYON 2: EDGE STRATEJİSİ MULTIPLE TESTING DÜZELTMESİ (7 EŞİK)")
    print("===================================================================")

    # Load matches with odds from sqlite
    import sqlite3
    conn = sqlite3.connect("data/football.db")
    odds_df = pd.read_sql_query("""
        SELECT match_id, bookmaker, over_25_open, under_25_open, btts_yes_open, btts_no_open
        FROM external_match_odds
        WHERE over_25_open IS NOT NULL AND under_25_open IS NOT NULL
    """, conn)
    conn.close()

    # Build predictions dataframe for all holdout matches
    pred_records = []
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
        mats = matrix_from_lambdas(geo_h, geo_a, rho)
        p_o = over_prob(mats, 2.5)

        for i, (_, row) in enumerate(test_df.iterrows()):
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            pred_records.append({
                "match_id": row["match_id"],
                "season": test_season,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "p_model": p_o[i],
            })

    pred_df = pd.DataFrame(pred_records)
    mkt_res = pd.merge(pred_df, odds_df, on="match_id", how="inner")
    print(f"Toplam Model vs Piyasa Değerlendirilen Maç: {len(mkt_res)}")

    raw_mkt_o = 1.0 / mkt_res["over_25_open"].to_numpy()
    raw_mkt_u = 1.0 / mkt_res["under_25_open"].to_numpy()
    mkt_res["p_market"] = raw_mkt_o / (raw_mkt_o + raw_mkt_u)
    mkt_res["edge"] = mkt_res["p_model"] - mkt_res["p_market"]
    mkt_res["odds_over25"] = mkt_res["over_25_open"].astype(float)

    thresholds = [0.00, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10]
    k_thresh = len(thresholds)

    results_edge = []

    for th in thresholds:
        sub = mkt_res[mkt_res["edge"] >= th].copy()
        n_bets = len(sub)
        if n_bets == 0:
            results_edge.append({
                "threshold": f">{th*100:.0f}%", "n": 0, "wins": 0, "win_rate": 0,
                "roi": 0, "binom_p": 1.0, "roi_p": 1.0
            })
            continue

        wins = sub["is_o25"].sum()
        win_rate = wins / n_bets
        # ROI: 1 unit bet on each
        returns = np.where(sub["is_o25"] == 1, sub["odds_over25"] - 1.0, -1.0)
        roi = np.sum(returns) / n_bets * 100.0

        # Binomial test against average market implied probability
        expected_p = sub["p_market"].mean()
        binom_res = stats.binomtest(wins, n_bets, expected_p, alternative='greater')
        binom_p = binom_res.pvalue

        # Permutation / one-sample t-test on returns > 0
        t_stat, t_p = stats.ttest_1samp(returns, popmean=0.0, alternative='greater')

        results_edge.append({
            "threshold": f">{th*100:.0f}%",
            "n": n_bets,
            "wins": wins,
            "win_rate": win_rate * 100.0,
            "expected_p": expected_p * 100.0,
            "roi": roi,
            "binom_p": binom_p,
            "t_p": t_p,
        })

    edge_df = pd.DataFrame(results_edge)

    # Apply Bonferroni and Benjamini-Hochberg FDR to the 7 thresholds
    edge_df["binom_p_bonf"] = np.clip(edge_df["binom_p"] * k_thresh, 0.0, 1.0)
    edge_df["binom_q_fdr"] = benjamini_hochberg(edge_df["binom_p"])
    edge_df["t_p_bonf"] = np.clip(edge_df["t_p"] * k_thresh, 0.0, 1.0)
    edge_df["t_q_fdr"] = benjamini_hochberg(edge_df["t_p"])

    print(f"\nk = {k_thresh} Eşik Karşılaştırması için Çoklu Test Düzeltmesi (Multiple Testing Correction):")
    print(f"{'Eşik':<7} | {'N':<5} | {'Kazanma':<8} | {'Beklenen':<8} | {'ROI %':<8} | {'Binom p(raw)':<13} | {'Binom p(Bonf)':<13} | {'Binom q(FDR)':<13} | {'ROI p(raw)':<10} | {'ROI p(Bonf)':<11} | {'ROI q(FDR)':<10}")
    print("-" * 135)
    for _, row in edge_df.iterrows():
        sig = "🚨 ANLAMLI" if row["binom_q_fdr"] < 0.05 else "GÜRÜLTÜ"
        print(f"{row['threshold']:<7} | {int(row['n']):<5d} | %{row['win_rate']:<6.1f} | %{row['expected_p']:<6.1f} | %{row['roi']:<+6.2f} | {row['binom_p']:<13.4f} | {row['binom_p_bonf']:<13.4f} | {row['binom_q_fdr']:<13.4f} | {row['t_p']:<10.4f} | {row['t_p_bonf']:<11.4f} | {row['t_q_fdr']:<10.4f} | {sig}")

if __name__ == "__main__":
    main()
