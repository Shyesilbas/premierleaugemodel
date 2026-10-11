#!/usr/bin/env python3
"""
Master Pipeline Orchestrator for Premier League Model Engine
Executes:
  1. Ingestion Check (PulseLive API -> data/raw/)
  2. Tabulation & Audit (data/raw/ -> data/processed/ & reports/data_audit_2024_25.md)
  3. Feature Engineering (data/processed/ -> features_matches_2024_25.parquet)
  4. Model Training & Benchmarking (models/production/ & reports/model_benchmarks.md)
"""

import sys
import logging
from pathlib import Path

from src.processing.process_season_data import main as run_processing
from src.features.build_features import build_feature_dataset
from src.models.train_corners import train_corners_model
from src.models.train_throws import train_throws_model
from src.models.train_saves import train_saves_model
from src.models.train_match_outcome import train_match_outcome_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("master_pipeline")


def generate_benchmark_report(corner_res, throws_res, saves_res, outcome_res, output_path: Path):
    """Compiles all model benchmark results into reports/model_benchmarks.md."""
    md_content = f"""# Premier League Model Engine — Model Karşılaştırma ve Başarım Raporu (2024-25)

**Test Metodolojisi:** Zaman Serisi Bölümlemesi (Time-Series Split).  
İlk %80 maç (~304 maç) eğitim kümesi; son %20 maç (~76 maç) gerçek zamanlı geriye dönük test (backtesting) kümesi olarak kullanılmıştır.  
Tüm öznitelikler **veri sızıntısızdır (leakage-free)**; her maç için yalnızca maç saatinden önce tamamlanmış karşılaşmaların istatistikleri ve EWMA değerleri kullanılmıştır.

---

## 1. Model Başarım Özeti

| Hedef Metrik | Model Algoritması | Test RMSE | Test MAE | Baseline RMSE | Baseline MAE | Doğruluk / Başarım |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Toplam Korner** | XGBoost Regressor | {corner_res['test_rmse']} | {corner_res['test_mae']} | {corner_res['baseline_test_rmse']} | {corner_res['baseline_test_mae']} | %{corner_res['over_9_5_accuracy_pct']} (Üst 9.5 Doğruluğu) |
| **Toplam Taç** | LightGBM Regressor | {throws_res['test_rmse']} | {throws_res['test_mae']} | {throws_res['baseline_test_rmse']} | {throws_res['baseline_test_mae']} | %{throws_res['over_34_5_accuracy_pct']} (Üst 34.5 Doğruluğu) |
| **Kaleci Kurtarışları** | XGBoost Regressor | {saves_res['test_rmse']} | {saves_res['test_mae']} | {saves_res['baseline_test_rmse']} | {saves_res['baseline_test_mae']} | - |
| **1X2 Maç Sonucu** | Multi-class LightGBM | - | - | - | - | %{outcome_res['model_1x2']['test_accuracy_pct']} (Temel: %{outcome_res['model_1x2']['baseline_accuracy_pct']}) |
| **2.5 Gol Alt/Üst** | Binary XGBoost | - | - | - | - | %{outcome_res['model_over_2_5']['test_accuracy_pct']} (Brier: {outcome_res['model_over_2_5']['brier_score']}) |

---

## 2. En Etkili Öznitelikler (Feature Importance)

### Korner Modeli
"""
    for feat, imp in list(corner_res["top_features"].items())[:7]:
        md_content += f"- `{feat}`: {imp:.4f}\n"

    md_content += "\n### Taç Modeli\n"
    for feat, imp in list(throws_res["top_features"].items())[:7]:
        md_content += f"- `{feat}`: {imp}\n"

    md_content += "\n### Kaleci Kurtarış Modeli\n"
    for feat, imp in list(saves_res["top_features"].items())[:7]:
        md_content += f"- `{feat}`: {imp:.4f}\n"

    md_content += """
---

## 3. Üretim Dağıtımı ve Karar
Tüm modeller `models/production/` dizinine `.joblib` formatında kaydedilmiş olup üretim ortamına hazırdır.
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Model benchmark report written to {output_path}")


def main():
    logger.info("=== Starting Master Pipeline Execution ===")

    # Step 1: Processing & Audit
    logger.info("--- Running Phase 2: Processing & Audit ---")
    run_processing()

    # Step 2: Feature Engineering
    logger.info("--- Running Phase 3: Feature Engineering ---")
    matches_parquet = Path("data/processed/matches_summary_2024_25.parquet")
    features_parquet = Path("data/processed/features_matches_2024_25.parquet")
    build_feature_dataset(matches_parquet, features_parquet)

    # Step 3: Model Training
    logger.info("--- Running Phase 4: Model Training ---")
    corner_res = train_corners_model()
    throws_res = train_throws_model()
    saves_res = train_saves_model()
    outcome_res = train_match_outcome_models()

    # Step 4: Benchmark Report
    bench_report = Path("reports/model_benchmarks.md")
    generate_benchmark_report(corner_res, throws_res, saves_res, outcome_res, bench_report)

    logger.info("=== Master Pipeline Complete! ===")


if __name__ == "__main__":
    main()
