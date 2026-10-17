#!/usr/bin/env python3
"""
Comprehensive Metric Extraction Script for Premier League Goal Model (goals_models_v1.joblib).
Extracts:
- Brier Score, Log-Loss, Accuracy, ROC-AUC, Precision, Recall, F1, ECE for 1.5, 2.5, 3.5, BTTS
- Goal Lambda metrics: MAE, RMSE, Poisson Deviance, Correlation
- Exact Score Top-1, Top-3, Top-5 hit rates
- Full 58-feature Poisson regression coefficients and rankings
- Per-season walk-forward breakdown
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import (
    log_loss, brier_score_loss, accuracy_score, roc_auc_score,
    precision_score, recall_score, f1_score, mean_absolute_error, mean_squared_error
)
import joblib

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, over_prob, btts_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas

def compute_ece(probs, actual, n_bins=10):
    p = np.clip(np.asarray(probs, dtype=float), 0.0, 1.0)
    y = np.asarray(actual, dtype=int)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = len(p)
    for i in range(n_bins):
        mask = (p >= edges[i]) & (p < edges[i+1] if i < n_bins - 1 else p <= edges[i+1])
        if mask.sum() > 0:
            bin_p = p[mask].mean()
            bin_y = y[mask].mean()
            ece += mask.sum() * abs(bin_p - bin_y)
    return ece / total if total > 0 else 0.0

def run_extraction():
    # Load model and data
    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features = artifact["feature_names"]
    chosen = artifact["chosen"]
    print(f"Loaded model with {len(features)} features.")
    
    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    played = df[df["home_score"].notna() & df["away_score"].notna()].sort_values(["kickoff_millis", "match_id"]).reset_index(drop=True)
    seasons = list(pd.unique(played["season"].astype(str)))
    
    # Store predictions across all holdout folds
    holdout_records = []
    
    for s_idx in range(1, len(seasons)):
        test_season = seasons[s_idx]
        train_seasons = seasons[:s_idx]
        train_df = played[played["season"].astype(str).isin(train_seasons)]
        test_df = played[played["season"].astype(str) == test_season]
        
        if len(train_df) < 300 or len(test_df) == 0:
            continue
            
        dc_model = DixonColesModel(half_life_days=chosen["dc_half_life_days"]).fit(train_df)
        dc_h, dc_a = dc_model.lambdas(test_df)
        
        feat_model = FeatureGoalModel(features=features, alpha=chosen["feature_alpha"]).fit(train_df)
        feat_h, feat_a = feat_model.lambdas(test_df)
        
        blend_h = blend_lambdas(dc_h, feat_h, chosen["dc_weight"])
        blend_a = blend_lambdas(dc_a, feat_a, chosen["dc_weight"])
        blend_rho = 0.5 * (dc_model.rho_ + feat_model.rho_)
        
        matrices = matrix_from_lambdas(blend_h, blend_a, blend_rho)
        p_o15 = over_prob(matrices, 1.5)
        p_o25 = over_prob(matrices, 2.5)
        p_o35 = over_prob(matrices, 3.5)
        p_btts = btts_prob(matrices)
        
        for i, (_, row) in enumerate(test_df.iterrows()):
            mat = matrices[i]
            hs = int(row["home_score"])
            as_ = int(row["away_score"])
            
            # Rank scores by probability in mat
            flat_indices = np.argsort(mat.ravel())[::-1]
            top_scores = [(idx // 13, idx % 13) for idx in flat_indices[:5]]
            actual_score = (hs, as_)
            
            holdout_records.append({
                "match_id": row["match_id"],
                "season": test_season,
                "home_team": row.get("home_name", str(row["home_id"])),
                "away_team": row.get("away_name", str(row["away_id"])),
                "home_score": hs,
                "away_score": as_,
                "total_score": hs + as_,
                "lam_home": float(blend_h[i]),
                "lam_away": float(blend_a[i]),
                "lam_total": float(blend_h[i] + blend_a[i]),
                "p_o15": float(p_o15[i]),
                "p_o25": float(p_o25[i]),
                "p_o35": float(p_o35[i]),
                "p_btts": float(p_btts[i]),
                "top1_hit": 1 if actual_score == top_scores[0] else 0,
                "top3_hit": 1 if actual_score in top_scores[:3] else 0,
                "top5_hit": 1 if actual_score in top_scores[:5] else 0,
            })
            
    res_df = pd.DataFrame(holdout_records)
    print(f"Total holdout matches evaluated: {len(res_df)}")
    
    # Calculate Overall Metrics
    def calc_binary_metrics(probs, targets):
        p = np.clip(probs, 1e-6, 1 - 1e-6)
        y = targets.astype(int)
        y_pred = (p >= 0.50).astype(int)
        return {
            "brier": round(float(brier_score_loss(y, p)), 4),
            "log_loss": round(float(log_loss(y, p)), 4),
            "accuracy": round(float(accuracy_score(y, y_pred)) * 100.0, 1),
            "roc_auc": round(float(roc_auc_score(y, p)), 3),
            "precision": round(float(precision_score(y, y_pred, zero_division=0)) * 100.0, 1),
            "recall": round(float(recall_score(y, y_pred, zero_division=0)) * 100.0, 1),
            "f1": round(float(f1_score(y, y_pred, zero_division=0)), 3),
            "ece": round(float(compute_ece(p, y)) * 100.0, 2),
        }
        
    y_o15 = (res_df["total_score"] > 1.5).to_numpy()
    y_o25 = (res_df["total_score"] > 2.5).to_numpy()
    y_o35 = (res_df["total_score"] > 3.5).to_numpy()
    y_btts = ((res_df["home_score"] > 0) & (res_df["away_score"] > 0)).to_numpy()
    
    metrics = {
        "over_1_5": calc_binary_metrics(res_df["p_o15"], y_o15),
        "over_2_5": calc_binary_metrics(res_df["p_o25"], y_o25),
        "over_3_5": calc_binary_metrics(res_df["p_o35"], y_o35),
        "btts": calc_binary_metrics(res_df["p_btts"], y_btts),
    }
    
    # Continuous Goal Metrics
    h_act = res_df["home_score"].to_numpy()
    a_act = res_df["away_score"].to_numpy()
    t_act = res_df["total_score"].to_numpy()
    
    h_pred = res_df["lam_home"].to_numpy()
    a_pred = res_df["lam_away"].to_numpy()
    t_pred = res_df["lam_total"].to_numpy()
    
    goal_metrics = {
        "home": {
            "mae": round(float(mean_absolute_error(h_act, h_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(h_act, h_pred))), 3),
            "corr": round(float(np.corrcoef(h_act, h_pred)[0, 1]), 3),
        },
        "away": {
            "mae": round(float(mean_absolute_error(a_act, a_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(a_act, a_pred))), 3),
            "corr": round(float(np.corrcoef(a_act, a_pred)[0, 1]), 3),
        },
        "total": {
            "mae": round(float(mean_absolute_error(t_act, t_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(t_act, t_pred))), 3),
            "corr": round(float(np.corrcoef(t_act, t_pred)[0, 1]), 3),
        },
        "exact_score": {
            "top1_accuracy": round(float(res_df["top1_hit"].mean()) * 100.0, 1),
            "top3_accuracy": round(float(res_df["top3_hit"].mean()) * 100.0, 1),
            "top5_accuracy": round(float(res_df["top5_hit"].mean()) * 100.0, 1),
        }
    }
    
    # Season by season metrics
    seasons_summary = {}
    for season_name, grp in res_df.groupby("season"):
        g_y_o25 = (grp["total_score"] > 2.5).to_numpy()
        g_p_o25 = grp["p_o25"].to_numpy()
        g_y_btts = ((grp["home_score"] > 0) & (grp["away_score"] > 0)).to_numpy()
        g_p_btts = grp["p_btts"].to_numpy()
        
        seasons_summary[season_name] = {
            "n_matches": len(grp),
            "o25_log_loss": round(float(log_loss(g_y_o25, np.clip(g_p_o25, 1e-6, 1-1e-6))), 4),
            "o25_brier": round(float(brier_score_loss(g_y_o25, g_p_o25)), 4),
            "o25_acc": round(float(accuracy_score(g_y_o25, g_p_o25 >= 0.5)) * 100.0, 1),
            "btts_brier": round(float(brier_score_loss(g_y_btts, g_p_btts)), 4),
            "goal_mae": round(float(mean_absolute_error(grp["total_score"], grp["lam_total"])), 3),
            "top3_score_hit": round(float(grp["top3_hit"].mean()) * 100.0, 1),
        }
        
    # Feature Coefficients from Production Model
    feat_model = artifact["model"].feature_model_
    coef_h = feat_model.home_.named_steps["poissonregressor"].coef_
    coef_a = feat_model.away_.named_steps["poissonregressor"].coef_
    
    coef_list = []
    for f, ch, ca in zip(features, coef_h, coef_a):
        coef_list.append({
            "feature": f,
            "coef_home": round(float(ch), 6),
            "coef_away": round(float(ca), 6),
            "abs_impact": round(float(abs(ch) + abs(ca)), 6)
        })
    coef_list.sort(key=lambda x: x["abs_impact"], reverse=True)
    
    # Save full dump to json
    dump = {
        "model_architecture": {
            "kind": artifact["model_name"],
            "dc_half_life_days": chosen["dc_half_life_days"],
            "feature_alpha": chosen["feature_alpha"],
            "dc_weight": chosen["dc_weight"],
            "total_features": len(features),
            "fit_matches": artifact["production_fit_matches"],
            "calibration_matches": artifact["calibration_matches"],
        },
        "market_metrics": metrics,
        "goal_metrics": goal_metrics,
        "seasons_summary": seasons_summary,
        "feature_coefficients": coef_list,
    }
    
    with open("scratch/goal_model_comprehensive_metrics.json", "w") as f:
        json.dump(dump, f, indent=2)
        
    print("Metrics extraction completed successfully! Saved to scratch/goal_model_comprehensive_metrics.json")
    print(json.dumps(metrics, indent=2))
    print("Goal metrics:", json.dumps(goal_metrics, indent=2))
    print("Season summary:", json.dumps(seasons_summary, indent=2))
    print("Top 10 impactful features:")
    for row in coef_list[:10]:
        print(f"  {row['feature']}: home={row['coef_home']:+.5f}, away={row['coef_away']:+.5f}, impact={row['abs_impact']:.5f}")

if __name__ == "__main__":
    run_extraction()
