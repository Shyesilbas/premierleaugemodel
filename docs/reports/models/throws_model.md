# Taç Atışı Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Kasım 2026  
**Artifact:** `models/production/premier_league/throws_model_v1.joblib` · **Eğitim kodu:** `src/models/train_throws.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam taç atışı  
**Veri:** 1.608 tamamlanmış maç (1.286 geliştirme, 322 holdout); 2026/27 kilitli sezon (88 maç).  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../../../reports/model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

**Üretimde `ridge_100`.** CV'de ortalamaya karşı en büyük kazanç taç modelinde (%15.11, 4/4 kat); geliştirme dış sezon kapısı 2/2 geçti (`outer_season_gate_passed: True`). Holdout'ta RMSE `6.9994` vs ortalama `7.3884` (`R² 0.0932`); Üst 34.5'te NB2 log-loss sabit orandan `0.0415` daha iyi (`0.6525` vs `0.6940`).

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Özellikler (14) | `home_throws_roll_5/10`, `away_throws_roll_10`, `home_opponent_throws_roll_10`, `away_opponent_throws_roll_5/10`, `exp_home/away_throws_5`, `home/away_possession_roll_5`, `home/away_pass_pct_roll_10`, `home/away_inacc_fwd_pass_roll_10` |
| Aday modeller | `lgbm_shallow`, Ridge ve Poisson ızgaraları (`train_throws.py`) + `training_mean` |
| Seçim | İlk %80'de (1.286 maç) 4 genişleyen zaman katı, RMSE; CV kapısı + geliştirme dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0148 |
| En etkili özellikler (mutlak katsayı) | `home_possession_roll_5`, `home_opponent_throws_roll_10`, `away_throws_roll_10`, `home_inacc_fwd_pass_roll_10` |

## 3. Sonuçlar

**Kapılar:** CV kazancı %15.11, 4/4 kat [PASS] · Geliştirme dış sezon kapısı 2/2 [PASS]

**Holdout (son %20, 322 maç):**

| Ölçüm | Model | Ortalama |
| :--- | :---: | :---: |
| RMSE | 6.9994 | 7.3884 |
| MAE | 5.5780 | 5.9953 |
| R² | 0.0932 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `poisson_10` | 7.5199 | 9.1766 | Evet |
| 2024_25 | 760 | `ridge_50` | 6.9666 | 8.5265 | Evet |
| 2025_26 | 1140 | `ridge_100` | 6.9305 | 7.2030 | Evet |
| 2026_27 (kilitli, kısmi, 88 maç) | 1520 | `poisson_10` | 7.0654 | 7.4397 | Evet |

**Eşik pazarı (holdout):** Üst 34.5 (`%52.8` dev oranı): NB2 LL `0.6525` (`%62.4` isabet), Poisson LL `0.6594` (`%61.8`), sabit oran LL `0.6940` (`%50.6`).

## 4. Bilinen Sınırlar

- Ortalamaya karşı büyük kazancın bir kısmı sezon seviyesindeki kaymadan geliyor (2023/24'te ortalama RMSE 9.18, model 7.52): takım bazlı rolling özellikler lig seviyesini sabit ortalamadan daha hızlı izliyor. Kazancın ne kadarının "maçlar arası ayrım", ne kadarının "seviye uyumu" olduğu ayrıştırılmadı.

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `poisson_10`, RMSE 7.0221. |
| 24 Ekim 2026 | Geliştirme dış sezon kapısı `%20` test döneminden yalıtıldı (`2/2`) → `poisson_10` korundu (RMSE 6.941). |
| 17 Kasım 2026 | 1.608 maçla yeniden eğitildi (`1.286` dev / `322` holdout) → CV lideri `ridge_100` (`7.2817` CV RMSE), holdout RMSE `6.9994` (`2/2` geliştirme dış sezon). |
