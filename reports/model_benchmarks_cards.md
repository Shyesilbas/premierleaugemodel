# Model Benchmark Raporu — Toplam Kart Tahmin Motoru (Cards)

- **Hedef Değişken:** `total_cards` (Sarı + Kırmızı Kart)
- **Eğitim Kümesi (İlk %80):** 959 maç (2023-24, 2024-25, 2025-26, 2026-27 zaman ağırlıklı)
- **Test Kümesi (Out-of-time %20):** 240 maç
- **Sezon Ağırlıkları:** 2026-27: 4.50 | 2025-26: 2.20 | 2024-25: 0.90 | 2023-24: 0.40
- **Test RMSE:** `1.987` (Temel Model: `1.908`)
- **Test MAE:** `1.625` (Temel Model: `1.528`)
- **3.5 Üst Doğruluğu:** `%54.58`
- **4.5 Üst Doğruluğu:** `%57.92`

### En Etkili 10 Öznitelik (Feature Importance)

| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
| 1 | `away_fouls_drawn_roll_5` | 0.0125 |
| 2 | `home_xg_for_roll_10` | 0.0102 |
| 3 | `home_big_chances_for_roll_10` | 0.0102 |
| 4 | `home_opponent_throws_roll_3` | 0.0099 |
| 5 | `away_possession_ewma_02` | 0.0094 |
| 6 | `away_touches_in_opp_box_roll_3` | 0.0092 |
| 7 | `exp_match_cards_5` | 0.0088 |
| 8 | `home_shots_ontarget_for_roll_10` | 0.0088 |
| 9 | `away_offsides_for_roll_3` | 0.0087 |
| 10 | `home_shots_against_roll_5` | 0.0086 |
