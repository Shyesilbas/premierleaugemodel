# Premier League Model Engine — Model Karşılaştırma ve Başarım Raporu (2024-25)

**Test Metodolojisi:** Zaman Serisi Bölümlemesi (Time-Series Split).  
İlk %80 maç (~304 maç) eğitim kümesi; son %20 maç (~76 maç) gerçek zamanlı geriye dönük test (backtesting) kümesi olarak kullanılmıştır.  
Tüm öznitelikler **veri sızıntısızdır (leakage-free)**; her maç için yalnızca maç saatinden önce tamamlanmış karşılaşmaların istatistikleri ve EWMA değerleri kullanılmıştır.

---

## 1. Model Başarım Özeti

| Hedef Metrik | Model Algoritması | Test RMSE | Test MAE | Baseline RMSE | Baseline MAE | Doğruluk / Başarım |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **Toplam Korner** | XGBoost Regressor | 3.344 | 2.712 | 3.214 | 2.676 | %55.92 (Üst 9.5 Doğruluğu) |
| **Toplam Taç** | LightGBM Regressor | 7.544 | 6.176 | 7.592 | 6.072 | %54.61 (Üst 34.5 Doğruluğu) |
| **Kaleci Kurtarışları** | XGBoost Regressor | 2.319 | 1.901 | 2.302 | 1.908 | - |
| **1X2 Maç Sonucu** | Multi-class LightGBM | - | - | - | - | %43.42 (Temel: %38.82) |
| **2.5 Gol Alt/Üst** | Binary XGBoost | - | - | - | - | %59.21 (Brier: 0.237) |

---

## 2. En Etkili Öznitelikler (Feature Importance)

### Korner Modeli
- `away_saves_roll_10`: 0.0156
- `home_shots_ontarget_against_ewma_02`: 0.0125
- `away_saves_roll_5`: 0.0124
- `away_saves_ewma_02`: 0.0121
- `away_shots_ontarget_against_ewma_04`: 0.0120
- `away_shots_ontarget_for_roll_5`: 0.0118
- `away_shots_ontarget_against_roll_5`: 0.0118

### Taç Modeli
- `home_corners_for_roll_3`: 52
- `home_opponent_throws_ewma_02`: 41
- `away_throws_roll_10`: 36
- `home_throws_roll_10`: 36
- `away_shots_against_ewma_02`: 35
- `away_goals_for_ewma_04`: 35
- `away_shots_ontarget_for_ewma_04`: 32

### Kaleci Kurtarış Modeli
- `home_goals_against_roll_10`: 0.0178
- `away_throws_ewma_04`: 0.0176
- `away_shots_ontarget_against_roll_10`: 0.0158
- `home_throws_ewma_02`: 0.0154
- `home_throws_ewma_04`: 0.0144
- `home_shots_for_ewma_04`: 0.0136
- `exp_match_throws_5`: 0.0134

---

## 3. Üretim Dağıtımı ve Karar
Tüm modeller `models/production/` dizinine `.joblib` formatında kaydedilmiş olup üretim ortamına hazırdır.
