# Korner Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Kasım 2026  
**Artifact:** `models/production/premier_league/corner_model_v1.joblib` · **Eğitim kodu:** `src/models/train_corners.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam korner sayısı (eksik 69 maç olay akışından kurtarıldı — ana rapor Bölüm 2.3)  
**Veri:** 1.608 tamamlanmış maç (1.286 geliştirme, 322 holdout); 2026/27 kilitli sezon (88 maç).  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../../../reports/model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim (özellik ablasyonu, sinyal kaynağı analizi) henüz yapılmadı.

---

## 1. Karar

**[Baseline] Üretimde sabit ortalama (`training_mean`).** Aday özellikli model (`elastic_0.05_0.8`) geliştirme dönemi 4 katlı CV kapısını %0.96 RMSE kazancı (3/4 kat) ile geçse de, kilitli sezon dışı geliştirme dış sezon kapısında yalnızca 1/2 tam sezonda ortalamayı yendi (`outer_season_gate_passed: False`). Bu nedenle dürüst sabit ortalama sunulur; API `corners.model_skill = "baseline"` döner.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Aday özellikler (10) | `home/away_corners_for_roll_10`, `home/away_corners_against_roll_10`, `home/away_corners_for_roll_5`, `home/away_shots_for_roll_5`, `home/away_touches_in_opp_box_roll_5` |
| Aday modeller | `train_corners.py` içindeki Ridge / Poisson / ElasticNet / LGBM ızgarası + `training_mean` |
| Seçim | İlk %80'de (1.286 maç) 4 genişleyen zaman katı, RMSE; CV kapısı + geliştirme dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0158 (neredeyse Poisson) |

## 3. Sonuçlar

**Kapılar:** CV kazancı %0.96, 3/4 kat [PASS] · Geliştirme dış sezon kapısı 1/2 [FAIL] → `training_mean`

**Holdout (son %20, 322 maç — üretim `training_mean`):**

| Ölçüm | Üretim (`training_mean`) | Ham CV Kazananı (`elastic_0.05_0.8` CV) |
| :--- | :---: | :---: |
| RMSE | 3.2276 | CV RMSE 3.4229 (ortalama CV 3.4559) |
| MAE | 2.6601 | — |
| R² | -0.0196 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `training_mean` | 3.5986 | 3.5986 | Hayır (eşit) |
| 2024_25 | 760 | `ridge_250` | 3.4342 | 3.4719 | Evet |
| 2025_26 | 1140 | `elastic_0.05_0.5` | 3.2535 | 3.2892 | Evet |
| 2026_27 (kilitli, kısmi, 88 maç) | 1520 | `ridge_50` | 3.2248 | 3.2623 | Evet |

**Eşik pazarları (holdout, NB2):** Üst 8.5 LL `0.6688` (prior `0.6706`, isabet `%62.7`) · Üst 9.5 LL `0.6942` (prior `0.6956`, isabet `%53.4`) · Üst 10.5 LL `0.6823` (prior `0.6863`, isabet `%58.7`).

## 4. Bilinen Sınırlar

- Sinyal zayıf ve geliştirme dönemindeki temiz tam sezon kapısında (2023/24 + 2024/25) yalnızca 1/2 sezon kazanıldığı için özellikli model üretime alınmadı.
- Eşik olasılıkları geliştirme ortalamasından NB2 dağılımıyla üretilir; bahis edge'i iddiası için yeterli değildir.

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `elastic_0.05_0.5`, RMSE 3.1952. |
| 17 Ekim 2026 | Dış sezon kapısı eklendi → `elastic_0.05_0.8`, RMSE 3.1999. |
| 24 Ekim 2026 | Geliştirme dış sezon kapısı `%20` test döneminden yalıtıldı (`1/2`) → `training_mean` (`baseline`). |
| 17 Kasım 2026 | 1.608 maçla yeniden eğitildi (`1.286` dev / `322` holdout) → yine `training_mean` (RMSE `3.2276`). |
