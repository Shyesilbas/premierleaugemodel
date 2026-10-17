# Kurtarış Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026  
**Artifact:** `models/production/saves_model_v1.joblib` · **Eğitim kodu:** `src/models/train_saves.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam kaleci kurtarışı  
**Veri:** 1.580 tamamlanmış maç; 2026/27 kilitli sezon (60 maç), yalnızca raporlanır.  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

🛡️ **Üretimde sabit ortalama (`training_mean`).** En iyi CV adayı `ridge_500` CV kapısını geçemedi: kazanç %0.51, eşiğin hemen üstünde; ama yalnızca 2/4 katta kazanıyor (en az 3 gerekli). Dış sezon kapısı da 1/3 ile geçilemezdi. API `saves.model_skill = "baseline"` döner.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Aday özellikler (13) | `home/away_saves_roll_3/5/10`, `home/away_shots_against_roll_5`, `home/away_shots_ontarget_against_roll_5`, `home/away_shots_for_roll_5`, `exp_match_shots_5` |
| Aday modeller | `lgbm_shallow`, Ridge ve Poisson ızgaraları (`train_saves.py`) + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; CV kapısı + dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Dağılım | α = 0.0128 (neredeyse Poisson) |

## 3. Sonuçlar

**Kapılar:** CV kazancı %0.51, 2/4 kat ❌ · Dış sezon 1/3 ❌

**Holdout (son %20, 316 maç):** üretim ortalaması RMSE 2.3785, MAE 1.9203.

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `training_mean` | 2.8066 | 2.8066 | ❌ (eşit) |
| 2024_25 | 760 | `training_mean` | 2.5770 | 2.5770 | ❌ (eşit) |
| 2025_26 | 1140 | `ridge_500` | 2.3632 | 2.3785 | ✅ |
| 2026_27 🔒 (kilitli, kısmi) | 1520 | `ridge_500` | 2.3233 | 2.2825 | ❌ |

## 4. Bilinen Sınırlar

- Kaleci kurtarışı, rakibin isabetli şutuna ve kaleci formuna bağlı; maç öncesi rolling istatistikler bunu ortalamadan iyi kestiremiyor.
- Eşik pazarı olasılıkları üretilmiyor (artifact'ta `count_threshold_metrics` yok).

## 5. Reddedilen Deneyler

| Deneme | Sonuç | Karar |
| :--- | :--- | :--- |
| Kurtarış Poisson / Ridge modeli | CV kapısı geçilemedi (bağıl kazanç ~%0.5, 2/4 kat) | ❌ Lig ortalaması korundu |

## 6. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `training_mean` (CV kapısı). |
| 17 Ekim 2026 | Dış sezon kapısı eklendi; 16 Ekim verisiyle yeniden eğitildi → yine `training_mean`. |
