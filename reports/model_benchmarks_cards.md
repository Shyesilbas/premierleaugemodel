# Model Benchmark Raporu — Toplam Kart Tahmin Motoru (Cards)

- **Hedef Değişken:** `total_cards` (Sarı + Kırmızı Kart)
- **Seçilen Model:** `ridge_100` (Tüm veriyle yeniden eğitildi)
- **Öznitelik Sayısı:** 17 (Gürültüsüz, alan odaklı, `referee_id` çıkarıldı)
- **Test RMSE:** `1.908` (Temel Model: `1.912`) — ✅ Baseline Geçildi
- **Test MAE:** `1.555` (Temel Model: `1.552`)
- **3.5 Üst Doğruluğu:** `%60.00` (Çoğunluk Kuralı: `%59.58`)
- **4.5 Üst Doğruluğu:** `%60.42`

### En Etkili Öznitelikler
| Sıra | Öznitelik Adı | Önem Skoru |
|:---|:---|:---:|
| 1 | `home_cards_for_roll_10` | 0.3109 |
| 2 | `home_cards_against_roll_5` | 0.1275 |
| 3 | `away_cards_for_roll_3` | 0.0800 |
| 4 | `exp_away_cards_5` | 0.0741 |
| 5 | `away_cards_for_roll_10` | 0.0647 |
| 6 | `exp_match_cards_5` | 0.0556 |
| 7 | `away_fouls_drawn_roll_5` | 0.0526 |
| 8 | `referee_avg_cards` | 0.0403 |
| 9 | `home_cards_for_roll_5` | 0.0339 |
| 10 | `away_cards_for_roll_5` | 0.0207 |
