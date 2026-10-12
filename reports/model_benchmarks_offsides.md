# Model Benchmark Raporu — Yakalanılan Ofsayt Motoru (Offsides)

- **Hedef Değişken:** `total_offsides`
- **Seçilen Model:** `ridge_50` (Tüm veriyle yeniden eğitildi)
- **Test RMSE:** `1.907` (Temel Model: `2.041`)
- **Test MAE:** `1.508` (Temel Model: `1.631`)
- **3.5 Üst Doğruluğu:** `%66.25`

### En Etkili Öznitelikler

| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
| 1 | `away_offsides_against_roll_10` | 0.2617 |
| 2 | `exp_match_offsides_5` | 0.1674 |
| 3 | `away_offsides_against_roll_5` | 0.1631 |
| 4 | `home_offsides_against_roll_10` | 0.1464 |
| 5 | `exp_home_offsides_5` | 0.1164 |
| 6 | `home_offsides_for_roll_3` | 0.1114 |
| 7 | `home_offsides_against_roll_5` | 0.1089 |
| 8 | `home_offsides_for_roll_5` | 0.0697 |
| 9 | `exp_away_offsides_5` | 0.0511 |
| 10 | `home_offsides_for_roll_10` | 0.0362 |
