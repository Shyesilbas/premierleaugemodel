#!/usr/bin/env python3
"""
Master Pipeline Orchestrator for Premier League Model Engine
Executes:
  1. Ingestion Check (PulseLive API -> data/raw/)
  2. Tabulation & Audit (data/raw/ -> data/processed/ & reports/data_audit_2024_25.md)
  3. Feature Engineering (data/processed/ -> features_matches_all.parquet)
  4. Model Training & Benchmarking for all 6 models:
     - 1X2 Outcome & Over 2.5 Goals
     - Corners
     - Throws
     - Saves
     - Cards
     - Offsides
"""

import sys
import logging
from pathlib import Path

from src.processing.process_season_data import main as run_processing
from src.features.build_features import build_feature_dataset
from src.models.train_corners import train_corners_model
from src.models.train_throws import train_throws_model
from src.models.train_saves import train_saves_model
from src.models.train_cards import train_cards_model
from src.models.train_offsides import train_offsides_model
from src.models.train_match_outcome import train_match_outcome_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("master_pipeline")


def generate_benchmark_report(corner_res, throws_res, saves_res, cards_res, offsides_res, outcome_res, output_path: Path):
    """Compiles all model benchmark results into reports/model_benchmarks.md."""
    c_m = corner_res.get("metrics", corner_res)
    t_m = throws_res.get("metrics", throws_res)
    s_m = saves_res.get("metrics", saves_res)
    cd_m = cards_res.get("metrics", cards_res)
    off_m = offsides_res.get("metrics", offsides_res)

    md_content = f"""# Premier League Model Engine — Model Karşılaştırma ve Başarım Raporu

**Test Metodolojisi:** Kronolojik Zaman Serisi Bölümlemesi (Out-of-time Backtesting, Son %20 Maç).  
Tüm öznitelikler **veri sızıntısızdır (leakage-free)**; her maç için yalnızca maç saatinden önce tamamlanmış karşılaşmaların istatistikleri ve EWMA değerleri kullanılmıştır. Tüm modeller alan odaklı (curated) özniteliklerle optimize edilmiş ve üretim için %100 güncel veriyle yeniden eğitilmiştir.

---

## 1. Model Başarım Özeti

| Hedef Metrik | Model Algoritması | Test RMSE | Test MAE | Baseline RMSE | Baseline MAE | Doğruluk / Başarım |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Toplam Korner** | {c_m.get('selected_model', 'LGBM')} | {c_m['test_rmse']} | {c_m['test_mae']} | {c_m['baseline_test_rmse']} | {c_m['baseline_test_mae']} | %{c_m.get('over_9_5_accuracy_pct', '-')} (Üst 9.5 Doğruluğu) |
| **Toplam Taç** | {t_m.get('selected_model', 'LGBM')} | {t_m['test_rmse']} | {t_m['test_mae']} | {t_m['baseline_test_rmse']} | {t_m['baseline_test_mae']} | %{t_m.get('over_34_5_accuracy_pct', '-')} (Üst 34.5 Doğruluğu) |
| **Kaleci Kurtarışları** | {s_m.get('selected_model', 'LGBM')} | {s_m['test_rmse']} | {s_m['test_mae']} | {s_m['baseline_test_rmse']} | {s_m['baseline_test_mae']} | Dengeli Kurtarış Dağılımı |
| **Kartlar & Disiplin** | {cd_m.get('selected_model', 'Ridge')} | {cd_m['test_rmse']} | {cd_m['test_mae']} | {cd_m['baseline_rmse']} | {cd_m['baseline_mae']} | %{cd_m.get('o35_accuracy', '-')} (Üst 3.5 Doğruluğu) |
| **Yakalanılan Ofsayt** | {off_m.get('selected_model', 'Ridge')} | {off_m['test_rmse']} | {off_m['test_mae']} | {off_m['baseline_test_rmse']} | {off_m['baseline_test_mae']} | %{off_m.get('over_3_5_accuracy_pct', '-')} (Üst 3.5 Doğruluğu) |
| **1X2 Maç Sonucu** | {outcome_res['model_1x2'].get('selected_model', 'LogReg')} | - | - | - | - | %{outcome_res['model_1x2']['test_accuracy_pct']} (Temel: %{outcome_res['model_1x2']['baseline_accuracy_pct']}) LogLoss: {outcome_res['model_1x2'].get('log_loss', '-')} (Temel: {outcome_res['model_1x2'].get('baseline_log_loss', '-')}) |
| **2.5 Gol Alt/Üst** | {outcome_res['model_over_2_5'].get('selected_model', 'LogReg')} | - | - | - | - | %{outcome_res['model_over_2_5']['test_accuracy_pct']} LogLoss: {outcome_res['model_over_2_5'].get('log_loss', '-')} (Temel: {outcome_res['model_over_2_5'].get('baseline_log_loss', '-')}) Brier: {outcome_res['model_over_2_5']['brier_score']} |

---

## 2. Üretim Dağıtımı ve Karar
Tüm 6 model `models/production/` dizinine `.joblib` formatında kaydedilmiş olup FastAPI backend uç noktalarına (`/api/predict`) ve kullanıcı arayüzüne entegre edilmiştir.
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
    matches_parquet = Path("data/processed/matches_summary_all.parquet")
    features_parquet = Path("data/processed/features_matches_all.parquet")
    build_feature_dataset(matches_parquet, features_parquet)

    # Step 3: Model Training
    logger.info("--- Running Phase 4: Model Training ---")
    corner_res = train_corners_model()
    throws_res = train_throws_model()
    saves_res = train_saves_model()
    cards_res = train_cards_model()
    offsides_res = train_offsides_model()
    outcome_res = train_match_outcome_models()

    # Step 4: Benchmark Report
    bench_report = Path("reports/model_benchmarks.md")
    generate_benchmark_report(corner_res, throws_res, saves_res, cards_res, offsides_res, outcome_res, bench_report)

    logger.info("=== Master Pipeline Complete! ===")


if __name__ == "__main__":
    main()
