#!/usr/bin/env python3
"""
Audit Script:
1. Multiple Testing Correction on P1a Segments (AUC p-value via Mann-Whitney U / DeLong & correlation t-test).
   Apply Bonferroni and Benjamini-Hochberg (FDR) corrections.
2. Permutation Feature Importance on 1,200 holdout matches vs Raw Poisson Regression Coefficients.
3. Codebase Reproducibility & Seed Inspection.
"""

import sys
import numpy as np
import pandas as pd
import joblib
from scipy import stats
from sklearn.metrics import log_loss, roc_auc_score, brier_score_loss

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def auc_p_value_mann_whitney(y_true, y_pred):
    """Mann-Whitney U test p-value for H0: AUC = 0.50."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    n1 = np.sum(y_true == 1)
    n0 = np.sum(y_true == 0)
    if n1 == 0 or n0 == 0:
        return 1.0, 0.5
    u_stat, p_val = stats.mannwhitneyu(y_pred[y_true == 1], y_pred[y_true == 0], alternative='two-sided')
    auc = u_stat / (n1 * n0)
    return p_val, auc

def benjamini_hochberg(p_values):
    """Calculate Benjamini-Hochberg FDR adjusted p-values (q-values)."""
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
    print("1. AKSİYON 1: MULTIPLE TESTING CORRECTION (P1a SEGMENTS)")
    print("===================================================================")

    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]

    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))

    records = []
    models_per_season = {}

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
        p_o25 = over_prob(mats, 2.5)

        models_per_season[test_season] = {
            "dc": dc, "feat": feat, "train_df": train_df, "test_df": test_df,
            "geo_h": geo_h, "geo_a": geo_a, "rho": rho
        }

        for i, (_, row) in enumerate(test_df.iterrows()):
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            records.append({
                "match_id": row["match_id"],
                "season": test_season,
                "home_id": row["home_id"],
                "away_id": row["away_id"],
                "home_name": row.get("home_name", str(row["home_id"])),
                "away_name": row.get("away_name", str(row["away_id"])),
                "total_score": hs + as_,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "p_o25": p_o25[i],
                "expected_goals_total": float(geo_h[i] + geo_a[i]),
                "elo_diff": float(row.get("abs_elo_diff", 0)),
                "mutual_high_line": float(row.get("mutual_high_line_risk", 0)),
                "combined_shots": float(row.get("home_shots_for_roll_10", 12.0) + row.get("away_shots_for_roll_10", 11.0)),
            })

    res_df = pd.DataFrame(records)
    print(f"Holdout Match Count: {len(res_df)}")

    def is_big6(name):
        n = str(name).lower()
        return any(b in n for b in ["manchester city", "man city", "arsenal", "liverpool", "manchester united", "man utd", "chelsea", "tottenham", "spurs"])

    res_df["home_is_big6"] = res_df["home_name"].apply(is_big6)
    res_df["away_is_big6"] = res_df["away_name"].apply(is_big6)
    res_df["both_big6"] = res_df["home_is_big6"] & res_df["away_is_big6"]
    res_df["one_big6"] = (res_df["home_is_big6"] ^ res_df["away_is_big6"])
    res_df["neither_big6"] = (~res_df["home_is_big6"]) & (~res_df["away_is_big6"])

    elo_med = res_df["elo_diff"].median()
    shots_med = res_df["combined_shots"].median()
    line_med = res_df["mutual_high_line"].median()
    xg_q33 = res_df["expected_goals_total"].quantile(0.33)
    xg_q66 = res_df["expected_goals_total"].quantile(0.66)

    # 12 specific disjoint/substantive segments (excluding the global pool)
    test_segments = {
        "Elit (Big 6 vs Big 6)": res_df["both_big6"].to_numpy(),
        "Asimetrik (Big 6 vs Diğer)": res_df["one_big6"].to_numpy(),
        "Orta/Alt vs Orta/Alt": res_df["neither_big6"].to_numpy(),
        "Düşük Elo Farkı": (res_df["elo_diff"] <= elo_med).to_numpy(),
        "Yüksek Elo Farkı": (res_df["elo_diff"] > elo_med).to_numpy(),
        "Yüksek Şut Temposu": (res_df["combined_shots"] >= shots_med).to_numpy(),
        "Düşük Şut Temposu": (res_df["combined_shots"] < shots_med).to_numpy(),
        "Açık Alan Yüksek Hat": (res_df["mutual_high_line"] >= line_med).to_numpy(),
        "Kompakt Derin Blok": (res_df["mutual_high_line"] < line_med).to_numpy(),
        "Yüksek Gol Beklentisi (>q66)": (res_df["expected_goals_total"] >= xg_q66).to_numpy(),
        "Orta Gol Beklentisi (q33-q66)": ((res_df["expected_goals_total"] >= xg_q33) & (res_df["expected_goals_total"] < xg_q66)).to_numpy(),
        "Düşük Gol Beklentisi (<q33) [Segment 10]": (res_df["expected_goals_total"] < xg_q33).to_numpy(),
    }

    k = len(test_segments)
    seg_names = []
    n_list = []
    auc_list = []
    p_raw_list = []
    r_list = []
    p_r_list = []

    y_all = res_df["is_o25"].to_numpy()
    p_all = res_df["p_o25"].to_numpy()
    g_all = res_df["total_score"].to_numpy()
    exp_all = res_df["expected_goals_total"].to_numpy()

    for name, mask in test_segments.items():
        sub_y = y_all[mask]
        sub_p = p_all[mask]
        sub_g = g_all[mask]
        sub_exp = exp_all[mask]
        n = mask.sum()

        p_val, auc = auc_p_value_mann_whitney(sub_y, sub_p)
        r, p_r = stats.pearsonr(sub_exp, sub_g)

        seg_names.append(name)
        n_list.append(n)
        auc_list.append(auc)
        p_raw_list.append(p_val)
        r_list.append(r)
        p_r_list.append(p_r)

    p_bonf = np.clip(np.array(p_raw_list) * k, 0.0, 1.0)
    q_fdr = benjamini_hochberg(p_raw_list)

    print(f"\nk = {k} Hipotez Karşılaştırması için Düzeltmeler:")
    print(f"{'Segment':<42} | {'N':<5} | {'AUC':<7} | {'p (raw)':<8} | {'p (Bonf)':<8} | {'q (BH FDR)':<10} | {'r(λ,goals)':<10} | {'p(r)':<7}")
    print("-" * 115)
    for i in range(k):
        sig = "🚨 ANLAMLI" if q_fdr[i] < 0.05 else ("⚠️ MARGINAL" if p_raw_list[i] < 0.05 else "GÜRÜLTÜ")
        print(f"{seg_names[i]:<42} | {n_list[i]:<5d} | {auc_list[i]:<7.4f} | {p_raw_list[i]:<8.4f} | {p_bonf[i]:<8.4f} | {q_fdr[i]:<10.4f} | {r_list[i]:<+10.4f} | {p_r_list[i]:<7.4f} | {sig}")

    print("\n" + "="*95)
    print("2. AKSİYON 2: PERMUTATION IMPORTANCE VS REGRESSION COEFFICIENTS")
    print("===================================================================")

    # Let's inspect feature coefficients of FeatureGoalModel
    # FeatureGoalModel fits PoissonRegressor for home and away
    latest_season = seasons[-1]
    last_model = models_per_season[latest_season]["feat"]
    coefs_home = np.abs(last_model.home_.named_steps["poissonregressor"].coef_)
    coefs_away = np.abs(last_model.away_.named_steps["poissonregressor"].coef_)
    mean_abs_coef = 0.5 * (coefs_home + coefs_away)

    coef_df = pd.DataFrame({
        "feature": features_58,
        "mean_abs_coef": mean_abs_coef,
        "home_coef": last_model.home_.named_steps["poissonregressor"].coef_,
        "away_coef": last_model.away_.named_steps["poissonregressor"].coef_,
    }).sort_values("mean_abs_coef", ascending=False)

    # Now compute Permutation Importance on the full 1,200 holdout matches
    # Baseline metrics
    base_ll = log_loss(y_all, p_all)
    base_auc = roc_auc_score(y_all, p_all)
    print(f"Baseline Global Log-Loss: {base_ll:.4f}, AUC: {base_auc:.4f}")

    rng = np.random.RandomState(42)
    n_repeats = 5
    perm_importance = []

    for f_idx, feat_name in enumerate(features_58):
        delta_ll_list = []
        delta_auc_list = []

        for rep in range(n_repeats):
            # Evaluate across each test season with permuted feature
            perm_p_all = []
            perm_y_all = []

            for s_idx in range(1, len(seasons)):
                test_season = seasons[s_idx]
                mod_info = models_per_season[test_season]
                test_df_copy = mod_info["test_df"].copy()

                # Permute feature f_idx in test_df
                vals = test_df_copy[feat_name].to_numpy().copy()
                rng.shuffle(vals)
                test_df_copy[feat_name] = vals

                feat_m = mod_info["feat"]
                dc_m = mod_info["dc"]
                dc_h, dc_a = dc_m.lambdas(test_df_copy)
                feat_h, feat_a = feat_m.lambdas(test_df_copy)

                geo_h = blend_lambdas(dc_h, feat_h, chosen["dc_weight"])
                geo_a = blend_lambdas(dc_a, feat_a, chosen["dc_weight"])
                mats = matrix_from_lambdas(geo_h, geo_a, mod_info["rho"])
                p_o = over_prob(mats, 2.5)

                perm_p_all.extend(p_o)
                perm_y_all.extend(test_df_copy["home_score"] + test_df_copy["away_score"] > 2.5)

            rep_ll = log_loss(perm_y_all, perm_p_all)
            rep_auc = roc_auc_score(perm_y_all, perm_p_all)
            delta_ll_list.append(rep_ll - base_ll)
            delta_auc_list.append(base_auc - rep_auc)

        perm_importance.append({
            "feature": feat_name,
            "mean_delta_ll": np.mean(delta_ll_list),
            "std_delta_ll": np.std(delta_ll_list),
            "mean_delta_auc": np.mean(delta_auc_list),
            "mean_abs_coef": coef_df.loc[coef_df["feature"] == feat_name, "mean_abs_coef"].values[0]
        })

    perm_df = pd.DataFrame(perm_importance)
    print("\nTOP 15 FEATURES BY RAW REGRESSION COEFFICIENT:")
    print(coef_df[["feature", "mean_abs_coef", "home_coef", "away_coef"]].head(15).to_string(index=False))

    print("\nTOP 15 FEATURES BY PERMUTATION IMPORTANCE (Delta Log-Loss when shuffled):")
    top_perm = perm_df.sort_values("mean_delta_ll", ascending=False).reset_index(drop=True)
    print(top_perm[["feature", "mean_delta_ll", "mean_delta_auc", "mean_abs_coef"]].head(15).to_string(index=False))

    # Check rank correlation between raw coefficient and permutation importance
    r_spearman, p_spearman = stats.spearmanr(perm_df["mean_abs_coef"], perm_df["mean_delta_ll"])
    print(f"\nSpearman Rank Correlation between |Coefficient| and Permutation Importance: r = {r_spearman:.4f} (p = {p_spearman:.4e})")

    # Specifically check effective_log_mv_ratio
    mv_row = perm_df[perm_df["feature"] == "effective_log_mv_ratio"]
    print("\nInspection of 'effective_log_mv_ratio':")
    print(mv_row.to_string(index=False))

    print("\n" + "="*95)
    print("3. AKSİYON 3: REPRODUCIBILITY & SEED MANAGEMENT AUDIT")
    print("===================================================================")
    # Check if models are deterministic across 2 identical training runs
    train_df = played[played["season"].astype(str) == seasons[0]]
    test_df = played[played["season"].astype(str) == seasons[1]]

    m1 = FeatureGoalModel(features=features_58, alpha=chosen["feature_alpha"]).fit(train_df)
    m2 = FeatureGoalModel(features=features_58, alpha=chosen["feature_alpha"]).fit(train_df)

    h1, a1 = m1.lambdas(test_df)
    h2, a2 = m2.lambdas(test_df)

    diff = np.max(np.abs(h1 - h2)) + np.max(np.abs(a1 - a2))
    print(f"FeatureGoalModel Determinism Test (Max Difference between 2 runs): {diff:.10e}")

    dc1 = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
    dc2 = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
    dch1, dca1 = dc1.lambdas(test_df)
    dch2, dca2 = dc2.lambdas(test_df)
    diff_dc = np.max(np.abs(dch1 - dch2)) + np.max(np.abs(dca1 - dca2))
    print(f"DixonColes Determinism Test (Max Difference between 2 runs): {diff_dc:.10e}")

if __name__ == "__main__":
    main()
