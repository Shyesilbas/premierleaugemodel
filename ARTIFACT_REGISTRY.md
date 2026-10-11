# Premier League Model Engine — Eser Kayıt Defteri (ARTIFACT_REGISTRY)

Bu dosya, projede üretilen tüm veri setleri, modeller ve analiz raporlarının tek doğruluk kaynağıdır (single source of truth).

---

## 1. Veri Kümeleri (Datasets)

| Kategori | Dosya Yolu | Format | Boyut / Satır | Durum |
|:---|:---|:---:|:---:|:---:|
| Raw | `data/raw/fixtures_2024_25.json` | JSON | 380 Maç | ✅ Tamamlandı |
| Raw | `data/raw/fixtures_2025_26.json` | JSON | 380 Maç | ✅ Tamamlandı |
| Raw | `data/raw/fixtures_2026_27.json` | JSON | 380 Maç (59 Tamamlanmış, 321 Yaklaşan) | ✅ Tamamlandı |
| Raw | `data/raw/matches/{id}_stats.json` | JSON | 819 Dosya (~28 MB) | ✅ Tamamlandı |
| Raw | `data/raw/matches/{id}_stream.json` | JSON | 819 Dosya (~20 MB) | ✅ Tamamlandı |
| Raw | `data/raw/matches/{id}_details.json` | JSON | 1140 Dosya (~25 MB) | ✅ Tamamlandı |
| Processed | `data/processed/matches_summary_all.parquet` | Parquet | **1140 Satır, 90+ Sütun (819 Tamamlanmış Maç)** | ✅ Üretildi |
| Processed | `data/processed/shots_events_all.parquet` | Parquet | **31,932 Olay Satırı** | ✅ Üretildi |
| Processed | `data/processed/players_registry.json` | JSON | **868 Oyuncu Profili** | ✅ Üretildi |
| Processed | `data/processed/player_match_logs.json` | JSON | **868 Oyuncu Maç & Dakika Kütüğü** | ✅ Üretildi |
| Features | `data/processed/features_matches_all.parquet` | Parquet | **1140 Satır, 336 Öznitelik (Ofsayt, Fırsat, Faul)** | ✅ Üretildi |

---

## 2. Üretim Modelleri (Production Models)

| Model Adı | Dosya Yolu | Algoritma | Hedef Metrik | Başarım |
|:---|:---|:---:|:---:|:---:|
| Corner Regressor | `models/production/corner_model_v1.joblib` | XGBoost Regressor | Toplam Korner / 9.5-10.5 Üst | Test RMSE: **3.34**, Üst 9.5: **%55.3** |
| Throws Regressor | `models/production/throws_model_v1.joblib` | LightGBM Regressor | Toplam Taç / 34.5 Üst | Test RMSE: 7.62, Üst 34.5: **%52.0** |
| Saves Regressor | `models/production/saves_model_v1.joblib` | XGBoost Regressor | Kaleci Kurtarışları | Test RMSE: **2.32**, MAE: **1.90** |
| Match Outcome | `models/production/outcome_models_v1.joblib` | Multi-LGBM + XGBoost | 1X2 & 2.5 Gol Alt/Üst | 1X2: **%43.4** (Temel: %38.8), 2.5 Üst: **%61.2** (Brier: 0.236) |
| Offside Regressor | `models/production/offside_model_v1.joblib` | XGBoost + Poisson | Yakalanılan Ofsayt / 3.5 Üst | Test RMSE: **1.937**, 3.5 Üst Doğruluğu: **%67.68** |

---

## 3. Raporlar ve Denetim Belgeleri (Reports)

| Rapor Dosyası | Kapsam | İlgili Faz | Durum |
|:---|:---|:---:|:---:|
| [`reports/data_audit_multi_season.md`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/reports/data_audit_multi_season.md) | 760 maçlık veri bütünlüğü, eksik değer kontrolü (0 hata) | Faz 2 | ✅ Onaylandı |
| [`reports/data_audit_2026_27.md`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/reports/data_audit_2026_27.md) | 2026-27 sezonu 380 fikstür ve 59 oynanmış maç denetimi | Faz 2 | ✅ Onaylandı |
| [`reports/model_benchmarks.md`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/reports/model_benchmarks.md) | Out-of-time backtest sonuçları ve sızıntısızlık metrikleri | Faz 4 | ✅ Onaylandı |
| [`reports/model_benchmarks_offsides.md`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/reports/model_benchmarks_offsides.md) | Ofsayt modeli eğitim sonuçları, metrikleri ve feature importance | Faz 4 | ✅ Onaylandı |

---

## 4. Kullanıcı Arayüzü ve API (Application Layer)

| Bileşen | Dosya Yolu | Port / URL | Açıklama |
|:---|:---|:---:|:---|
| Backend API | `src/api/server.py` | `http://127.0.0.1:8000/api` | 1140 maçlık veri tabanı, 868 oyuncu profili ve canlı tahmin motoru |
| Web Dashboard (React + Vite) | `frontend/src/App.jsx` | `http://127.0.0.1:5173/` | Sidebar navigasyonlu, açık temalı, haftalık/günlük fikstür ve profiller |
| Kulüp Vektör Logoları | `frontend/public/badges/*.svg` | `/badges/{id}.svg` | Premier League kulüplerinin resmi SVG armaları |
