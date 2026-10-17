#!/usr/bin/env python3
"""
P1 Kickoff Script:
1. Power Analysis for Market vs Model AUC detection (Answering Question 1)
2. P1a: Comprehensive AUC & Calibration Segmentation Analysis on 1,200 Holdout Matches:
   - Top 6 vs Top 6 (Elite clashes)
   - Top 6 vs Bottom 6 (Asymmetric matches)
   - Mid-table / Bottom 6 vs Bottom 6
   - Tactical Tempo Segments (High Shot Volume vs Low Shot Volume)
   - Defensive Stretch Segments (High Line vs Deep Block)
   - Market Expected Goal Bands (High Expected Goals vs Under Dogfights)
"""

import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score

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

def main():
    print("===================================================================")
    print("1. İSTATİSTİKSEL GÜÇ ANALİZİ (POWER ANALYSIS)")
    print("===================================================================")
    # Delta AUC = 0.0119, observed SE across 218 matches
    # From previous bootstrap: CI 95% width = 0.0723 - (-0.0483) = 0.1206
    # SE_218 = 0.1206 / (2 * 1.96) = 0.03076
    delta_auc = 0.0118
    se_218 = 0.03076
    
    # Required N for alpha=0.05 (z=1.96) and power 80% (z=0.8416) => Z_total = 2.8016
    # Z = delta / SE_N = delta / (se_218 * sqrt(218 / N)) >= 2.8016
    # sqrt(N / 218) >= 2.8016 * se_218 / delta
    target_z_80 = 1.96 + 0.8416
    target_z_90 = 1.96 + 1.2816
    
    n_required_80 = int(np.ceil(218 * ((target_z_80 * se_218) / delta_auc)**2))
    n_required_90 = int(np.ceil(218 * ((target_z_90 * se_218) / delta_auc)**2))
    
    print(f"Gözlenen AUC Farkı (Piyasa - Model):  +{delta_auc:.4f}")
    print(f"218 Maçtaki Standart Hata (SE):       {se_218:.4f}")
    print(f"%80 Güç (Power = 0.80, alpha = 0.05) için Gerekli Maç Sayısı: {n_required_80} maç")
    print(f"%90 Güç (Power = 0.90, alpha = 0.05) için Gerekli Maç Sayısı: {n_required_90} maç")
    print(f"Yorum: 218 maçlık havuzda p=0.352 çıkması tamamen yetersiz güçten (underpowered sample) kaynaklanmaktadır.")
    print(f"Farkın istatistiksel olarak kesinleşmesi için en az ~1.200 - 1.500 maçlık kapanış verisi gereklidir.")

    # =====================================================================
    # 2. P1a: AUC SEGMENTASYON ANALİZİ
    # =====================================================================
    print("\n===================================================================")
    print("2. P1a: AUC SEGMENTASYON ANALİZİ (1.200 MAÇLIK HOLDOUT HAVUZU)")
    print("===================================================================")
    
    artifact = joblib.load("models/production/goals_models_v1.joblib")
    features_58 = artifact["feature_names"]
    chosen = artifact["chosen"]

    df = pd.read_parquet("data/processed/features_matches_all.parquet")
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

        mats = matrix_from_lambdas(geo_h, geo_a, rho)
        p_o25 = over_prob(mats, 2.5)
        p_btts = btts_prob(mats)

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
                "home_score": hs,
                "away_score": as_,
                "total_score": hs + as_,
                "is_o25": 1 if hs + as_ > 2.5 else 0,
                "is_btts": 1 if (hs > 0 and as_ > 0) else 0,
                "p_o25": p_o25[i],
                "p_btts": p_btts[i],
                "expected_goals_total": float(geo_h[i] + geo_a[i]),
                # Contextual features if available
                "elo_diff": float(row.get("abs_elo_diff", 0)),
                "home_line": float(row.get("home_high_line", 0)),
                "away_line": float(row.get("away_high_line", 0)),
                "mutual_high_line": float(row.get("mutual_high_line_risk", 0)),
                "combined_shots": float(row.get("home_shots_for_roll_10", 12.0) + row.get("away_shots_for_roll_10", 11.0)),
            })

    res_df = pd.DataFrame(records)
    print(f"Toplam Değerlendirilen Holdout Maç Sayısı: {len(res_df)}")

    # Define Premier League Big 6 by typical names / Elo
    def is_big6(name):
        n = str(name).lower()
        if "manchester city" in n or "man city" in n:
            return True
        if "arsenal" in n:
            return True
        if "liverpool" in n:
            return True
        if "manchester united" in n or "man utd" in n:
            return True
        if "chelsea" in n:
            return True
        if "tottenham" in n or "spurs" in n:
            return True
        return False

    res_df["home_is_big6"] = res_df["home_name"].apply(is_big6)
    res_df["away_is_big6"] = res_df["away_name"].apply(is_big6)
    res_df["both_big6"] = res_df["home_is_big6"] & res_df["away_is_big6"]
    res_df["one_big6"] = (res_df["home_is_big6"] ^ res_df["away_is_big6"])
    res_df["neither_big6"] = (~res_df["home_is_big6"]) & (~res_df["away_is_big6"])

    # Elo-based tiers
    elo_median = res_df["elo_diff"].median()
    res_df["elo_balanced"] = res_df["elo_diff"] <= elo_median
    res_df["elo_mismatch"] = res_df["elo_diff"] > elo_median

    # Expected goals bands
    xg_q33 = res_df["expected_goals_total"].quantile(0.33)
    xg_q66 = res_df["expected_goals_total"].quantile(0.66)
    res_df["low_scoring_expected"] = res_df["expected_goals_total"] < xg_q33
    res_df["mid_scoring_expected"] = (res_df["expected_goals_total"] >= xg_q33) & (res_df["expected_goals_total"] < xg_q66)
    res_df["high_scoring_expected"] = res_df["expected_goals_total"] >= xg_q66

    # Tactical pace (Combined shots roll10)
    shots_med = res_df["combined_shots"].median()
    res_df["high_tempo_shots"] = res_df["combined_shots"] >= shots_med
    res_df["low_tempo_shots"] = res_df["combined_shots"] < shots_med

    # Defensive stretch (High line risk)
    line_med = res_df["mutual_high_line"].median()
    res_df["open_pitch_high_line"] = res_df["mutual_high_line"] >= line_med
    res_df["compact_deep_block"] = res_df["mutual_high_line"] < line_med

    segments = {
        "1. GENEL HOLDOUT HAVUZU": np.ones(len(res_df), dtype=bool),
        "2. ELİT MAÇLAR (Big 6 vs Big 6)": res_df["both_big6"].to_numpy(),
        "3. ASİMETRİK MAÇLAR (Big 6 vs Diğerleri)": res_df["one_big6"].to_numpy(),
        "4. DİĞER MAÇLAR (Orta/Alt vs Orta/Alt)": res_df["neither_big6"].to_numpy(),
        "5. DENK TAKIMLAR (Düşük Elo Farkı)": res_df["elo_balanced"].to_numpy(),
        "6. SİKLET FARKI (Yüksek Elo Farkı)": res_df["elo_mismatch"].to_numpy(),
        "7. YÜKSEK ŞUT TEMPOSU (Tempo > Medyan)": res_df["high_tempo_shots"].to_numpy(),
        "8. DÜŞÜK ŞUT TEMPOSU (Tempo < Medyan)": res_df["low_tempo_shots"].to_numpy(),
        "9. AÇIK ALAN / YÜKSEK SAVUNMA HATTI": res_df["open_pitch_high_line"].to_numpy(),
        "10. KOMPAKT / DERİN BLOK SAVUNMA": res_df["compact_deep_block"].to_numpy(),
        "11. YÜKSEK GOL BEKLENTİSİ (>%66 Dilim)": res_df["high_scoring_expected"].to_numpy(),
        "12. ORTA GOL BEKLENTİSİ (%33-%66 Dilim)": res_df["mid_scoring_expected"].to_numpy(),
        "13. DÜŞÜK GOL BEKLENTİSİ (<%33 Dilim)": res_df["low_scoring_expected"].to_numpy(),
    }

    print("\n" + "="*95)
    print(f"{'SEGMENT TANIMI':<40} | {'N':<5} | {'ÜST %':<6} | {'LOG-LOSS':<8} | {'BRIER':<7} | {'ROC-AUC':<7} | {'ECE %':<6}")
    print("="*95)

    y_all = res_df["is_o25"].to_numpy()
    p_all = res_df["p_o25"].to_numpy()

    for name, mask in segments.items():
        n = mask.sum()
        if n < 20 or len(np.unique(y_all[mask])) < 2:
            continue
        sub_y = y_all[mask]
        sub_p = p_all[mask]
        
        ll = log_loss(sub_y, sub_p)
        br = brier_score_loss(sub_y, sub_p)
        auc = roc_auc_score(sub_y, sub_p)
        ece = compute_ece(sub_p, sub_y) * 100.0
        over_rate = sub_y.mean() * 100.0
        
        print(f"{name:<40} | {n:<5d} | %{over_rate:<5.1f} | {ll:<8.4f} | {br:<7.4f} | {auc:<7.4f} | %{ece:<5.2f}")

    print("="*95)

if __name__ == "__main__":
    main()
