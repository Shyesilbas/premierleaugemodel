# Premier League Model Engine — Çoklu Sezon Başarım Raporu (2023-24 ~ 2026-27)

**Veri Seti:** 4 Sezon (2023-24, 2024-25, 2025-26, 2026-27) — Toplam 1.520 maç (1.199 tamamlanmış veri sızıntısız maç).  
**Test Metodolojisi:** Kronolojik Zaman Serisi Bölümlemesi (Time-Series Split).  
İlk %80 maç (~959 maç) eğitim kümesi; son %20 maç (~240 maç) gerçek zamanlı geriye dönük test (out-of-time backtest) kümesi.  
**Zaman Ağırlıklandırması (Time-Decay Sample Weights):**
- **2026-27 (Güncel Sezon):** `4.50` (En yüksek öncelik ve etki)
- **2025-26 (Geçen Sezon):** `2.20` (Yüksek etki)
- **2024-25 (Referans Sezon):** `0.90` (Temel seviye)
- **2023-24 (Tarihsel Sezon):** `0.40` (Genel futbol dinamiklerini öğreten kontrollü etki)

---

## 1. Model Başarım Özeti

| Hedef Metrik | Model Algoritması | Test RMSE | Test MAE | Baseline RMSE | Baseline MAE | Doğruluk / Başarım |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Toplam Korner** | XGBoost Regressor | 3.226 | 2.602 | 3.215 | 2.672 | %55.4 (Üst 9.5 Doğruluğu) |
| **Toplam Taç** | LightGBM Regressor | 7.339 | 5.860 | 7.462 | 5.953 | %57.9 (Üst 34.5 Doğruluğu) |
| **Kaleci Kurtarışları** | XGBoost Regressor | 2.329 | 1.906 | 2.332 | 1.928 | Dengeli Kurtarış Dağılımı |
| **Yakalanılan Ofsayt** | XGBoost Regressor + Poisson | 1.898 | 1.474 | 2.047 | 1.640 | %67.5 (Üst 3.5 Doğruluğu) |
| **Kartlar & Disiplin** | XGBoost Regressor + Hakem Eğilimi | 1.987 | 1.625 | 1.908 | 1.528 | %57.9 (Üst 4.5 Doğruluğu) |
| **1X2 Maç Sonucu** | Multi-class LightGBM | - | - | - | - | %43.3 (Temel: %38.8) |
| **2.5 Gol Alt/Üst** | Binary XGBoost | - | - | - | - | %53.8 (Brier: 0.253) |
| **Beklenen Gol (xG)** | xG Engine (Şut Konumu + Büyük Şans) | - | - | - | - | Çift Taraflı Formülasyon |

---

## 2. Hakem & Disiplin Modeli Özellikleri
- `referee_avg_cards`: Hakemin maç saatinden önce yönettiği tüm Premier League maçlarındaki sarı/kırmızı kart ortalaması.
- `referee_avg_fouls`: Hakemin maç saatinden önce düdük çaldığı faul ortalaması.
- `referee_prior_matches`: Hakemin ligdeki maç deneyimi (tecrübe ve tolerans indeksi).
- `home_cards_for_roll_5` / `away_cards_against_roll_5`: Takımların son 5 maçtaki kart eğilimleri.

---

## 3. Üretim Dağıtımı
Tüm modeller `models/production/` dizinine `.joblib` formatında kaydedilmiş olup FastAPI backend uç noktalarına (`/api/predict`) ve kullanıcı arayüzüne entegre edilmiştir.
