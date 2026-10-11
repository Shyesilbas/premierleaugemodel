# Model Benchmark Raporu — Yakalanılan Ofsayt Motoru (Offsides)

- **Hedef Değişken:** `total_offsides`
- **Eğitim Kümesi (İlk %80):** 655 maç
- **Test Kümesi (Out-of-time %20):** 164 maç
- **Test RMSE:** `1.937` (Temel Model: `1.974`)
- **Test MAE:** `1.471` (Temel Model: `1.559`)
- **3.5 Üst Doğruluğu:** `%67.68`

### En Etkili 10 Öznitelik (Feature Importance)

| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
| 1 | `home_possession_ewma_02` | 0.0131 |
| 2 | `home_offsides_for_ewma_04` | 0.0101 |
| 3 | `home_offsides_against_roll_3` | 0.0101 |
| 4 | `away_offsides_against_roll_10` | 0.0099 |
| 5 | `away_offsides_against_ewma_04` | 0.0098 |
| 6 | `away_shots_ontarget_for_ewma_02` | 0.0097 |
| 7 | `home_corners_for_ewma_02` | 0.0097 |
| 8 | `away_shots_ontarget_against_ewma_04` | 0.0097 |
| 9 | `home_corners_against_ewma_04` | 0.0096 |
| 10 | `home_shots_ontarget_against_ewma_02` | 0.0096 |
