# Kurtarış Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Kasım 2026  
**Artifact:** `models/production/premier_league/saves_model_v1.joblib` · **Eğitim kodu:** `src/models/train_saves.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam kaleci kurtarışı  
**Veri:** 1.608 tamamlanmış maç (1.286 geliştirme, 322 holdout); 2026/27 kilitli sezon (88 maç).  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../../../reports/model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

**[Baseline] Üretimde sabit ortalama (`training_mean`).** Aday `ridge_100` CV kapısını %0.64 kazanç ve 3/4 kat ile geçse de, geliştirme dış sezon kapısında 0/2 tam sezonda kaldığı için `training_mean` korundu. API `saves.model_skill = "baseline"` döner.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Aday özellikler (13) | `home/away_saves_roll_3/5/10`, `home/away_shots_against_roll_5`, `home/away_shots_ontarget_against_roll_5`, `home/away_shots_for_roll_5`, `exp_match_shots_5` |
| Aday modeller | `lgbm_shallow`, Ridge ve Poisson ızgaraları (`train_saves.py`) + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; CV kapısı + dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Dağılım | α = 0.0209 (neredeyse Poisson) |

## 3. Sonuçlar

**Kapılar:** CV kazancı %0.64 (`ridge_100`), 3/4 kat [PASS] · Geliştirme dış sezon kapısı 0/2 [FAIL]

**Holdout (son %20, 322 maç):** üretim ortalaması RMSE `2.3633`, MAE `1.9085`.

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `training_mean` | 2.8066 | 2.8066 | Hayır (eşit) |
| 2024_25 | 760 | `training_mean` | 2.5770 | 2.5770 | Hayır (eşit) |
| 2025_26 | 1140 | `ridge_500` | 2.3632 | 2.3785 | Evet |
| 2026_27 (kilitli, kısmi, 88 maç) | 1520 | `ridge_500` | 2.4299 | 2.3641 | Hayır |

## 4. Bilinen Sınırlar

- Kaleci kurtarışı, rakibin isabetli şutuna ve kaleci formuna bağlı; maç öncesi rolling istatistikler bunu ortalamadan iyi kestiremiyor.
- Eşik pazarı olasılıkları üretilmiyor (artifact'ta `count_threshold_metrics` yok).

## 5. Reddedilen Deneyler

| Deneme | Sonuç | Karar |
| :--- | :--- | :--- |
| Kurtarış Poisson / Ridge modeli | CV kapısı geçilemedi (bağıl kazanç ~%0.5, 2/4 kat) | [Reddedildi] Lig ortalaması korundu |

## 6. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `training_mean` (CV kapısı). |
| 17 Ekim 2026 | Dış sezon kapısı eklendi; 16 Ekim verisiyle yeniden eğitildi → yine `training_mean`. |
| 17 Kasım 2026 | 1.608 maçla (`1.286` dev / `322` holdout) yeniden eğitildi → geliştirme dış sezon kapısı `0/2` ile `training_mean` (RMSE `2.3633`). |
