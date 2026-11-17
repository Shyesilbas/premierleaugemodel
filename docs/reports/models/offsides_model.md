# Ofsayt Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Kasım 2026  
**Artifact:** `models/production/premier_league/offside_model_v1.joblib` · **Eğitim kodu:** `src/models/train_offsides.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** `total_offsides` (maç toplam ofsayt)  
**Veri:** 1.608 tamamlanmış maç (1.286 geliştirme, 322 holdout); 2026/27 kilitli sezon (88 maç).  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../../../reports/model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

**Üretimde `ridge_250`.** Sayım modellerinin en tutarlılarından biri: CV kapısını %3.65 kazanç ve 4/4 katla, geliştirme dış sezon kapısını 2/2 ile geçiyor. Holdout'ta RMSE %5.4 daha iyi (`1.9263` vs `2.0356`, `R² 0.0931`); Üst 3.5'te sabit orandan `0.043` log-loss daha iyi.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Özellikler (10) | `home/away_offsides_for_roll_5/10`, `home/away_offsides_against_roll_5/10`, `home/away_possession_roll_5` |
| Aday modeller | `lgbm_shallow`, Ridge, Poisson, ElasticNet ızgaraları (`train_offsides.py`) + `training_mean` |
| Seçim | İlk %80'de (1.286 maç) 4 genişleyen zaman katı, RMSE; CV kapısı + geliştirme dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0479 — sayım modelleri arasında belirgin aşırı yayılım |
| En etkili özellikler (mutlak katsayı) | `away_offsides_against_roll_10`, `home_offsides_against_roll_5`, `away_offsides_against_roll_5`, `away_possession_roll_5` |

## 3. Sonuçlar

**Kapılar:** CV kazancı %3.65, 4/4 kat [PASS] · Geliştirme dış sezon kapısı 2/2 [PASS]

**Holdout (son %20, 322 maç):**

| Ölçüm | Model | Ortalama |
| :--- | :---: | :---: |
| RMSE | 1.9263 | 2.0356 |
| MAE | 1.5386 | 1.6465 |
| R² | 0.0931 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `elastic_0.1_0.5` | 2.0995 | 2.2248 | Evet |
| 2024_25 | 760 | `poisson_1` | 1.9902 | 2.0401 | Evet |
| 2025_26 | 1140 | `poisson_1` | 1.8004 | 1.9255 | Evet |
| 2026_27 (kilitli, kısmi, 88 maç) | 1520 | `poisson_1` | 2.1169 | 2.1042 | Hayır |

**Eşik pazarı (holdout):** Üst 3.5 (`%45.3` dev oranı): NB2 LL `0.6382` (`%65.2` isabet), Poisson LL `0.6377` (`%63.7`), sabit oran LL `0.6811` (`%58.7`).

## 4. Bilinen Sınırlar

- Kilitli 2026/27'nin ilk 88 maçında ortalamadan hafif kötü (2.1169 vs 2.1042). Örneklem küçük; sezon tamamlanınca izlenmeli.
- Üst 3.5'te Poisson LL, NB2'den hafif iyi (0.6377 vs 0.6382).

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `ridge_250`, RMSE 1.9064. |
| 24 Ekim 2026 | Geliştirme dış sezon kapısı `%20` test döneminden yalıtıldı (`2/2`) → `ridge_250` (RMSE 1.906). |
| 17 Kasım 2026 | 1.608 maçla yeniden eğitildi (`1.286` dev / `322` holdout) → `ridge_250`, holdout RMSE `1.9263`. |
