# Model Benchmark Raporu — Yakalanılan Ofsayt Motoru (Offsides)

- **Hedef Değişken:** `total_offsides`
- **Eğitim Kümesi (İlk %80):** 959 maç
- **Test Kümesi (Out-of-time %20):** 240 maç
- **Test RMSE:** `1.898` (Temel Model: `2.047`)
- **Test MAE:** `1.474` (Temel Model: `1.640`)
- **3.5 Üst Doğruluğu:** `%67.50`

### En Etkili 10 Öznitelik (Feature Importance)

| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
| 1 | `exp_match_offsides_5` | 0.0148 |
| 2 | `away_shots_ontarget_for_ewma_02` | 0.0102 |
| 3 | `away_cards_for_ewma_02` | 0.0100 |
| 4 | `away_possession_roll_10` | 0.0093 |
| 5 | `away_offsides_against_ewma_04` | 0.0091 |
| 6 | `away_big_chances_for_roll_10` | 0.0091 |
| 7 | `away_shots_ontarget_against_ewma_02` | 0.0088 |
| 8 | `away_shots_against_ewma_02` | 0.0085 |
| 9 | `home_offsides_for_roll_10` | 0.0085 |
| 10 | `away_throws_ewma_02` | 0.0082 |
