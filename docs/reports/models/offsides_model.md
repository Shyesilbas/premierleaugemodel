# Ofsayt Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026  
**Artifact:** `models/production/premier_league/offside_model_v1.joblib` · **Eğitim kodu:** `src/models/train_offsides.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** `total_offsides` (maç toplam ofsayt)  
**Veri:** 1.580 tamamlanmış maç; 2026/27 kilitli sezon (60 maç), yalnızca raporlanır.  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

🏆 **Üretimde `ridge_250`.** Sayım modellerinin en tutarlısı: CV kapısını 4/4 katla, dış sezon kapısını 3/3 ile geçiyor. Holdout'ta RMSE %5.6 iyi (R² 0.093); Üst 3.5'te sabit orandan 0.040 LL daha iyi.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Özellikler (10) | `home/away_offsides_for_roll_5/10`, `home/away_offsides_against_roll_5/10`, `home/away_possession_roll_5` |
| Aday modeller | `lgbm_shallow`, Ridge, Poisson, ElasticNet ızgaraları (`train_offsides.py`) + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; CV kapısı + dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0761 — sayım modelleri arasında en belirgin aşırı yayılım |
| En etkili özellikler (mutlak katsayı) | `away_offsides_against_roll_10`, `home_offsides_against_roll_5`, `away_offsides_against_roll_5`, `away_possession_roll_5` |

## 3. Sonuçlar

**Kapılar:** CV kazancı %3.63, 4/4 kat ✅ · Dış sezon 3/3 ✅

**Holdout (son %20, 316 maç):**

| Ölçüm | Model | Ortalama |
| :--- | :---: | :---: |
| RMSE | 1.9102 | 2.0238 |
| MAE | 1.5231 | 1.6302 |
| R² | 0.0934 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `elastic_0.1_0.5` | 2.0995 | 2.2248 | ✅ |
| 2024_25 | 760 | `poisson_1` | 1.9902 | 2.0401 | ✅ |
| 2025_26 | 1140 | `poisson_1` | 1.8004 | 1.9255 | ✅ |
| 2026_27 🔒 (kilitli, kısmi) | 1520 | `poisson_1` | 2.2635 | 2.2377 | ❌ |

**Eşik pazarı (holdout):**

| Pazar | Dev oranı | NB LL | Poisson LL | Sabit oran LL | NB isabet | Çoğunluk isabet |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Üst 3.5 | %45.1 | 0.6414 | 0.6404 | 0.6812 | %63.3 | %58.5 |

## 4. Bilinen Sınırlar

- Kilitli 2026/27'nin ilk 60 maçında ortalamadan hafif kötü (2.2635 vs 2.2377). Örneklem küçük; sezon tamamlanınca izlenmeli.
- α = 0.076'ya rağmen Üst 3.5'te Poisson LL, NB'den hafif iyi (0.6404 vs 0.6414); NB2 varsayımı bu eşikte avantaj sağlamıyor.

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `ridge_250`, RMSE 1.9064. |
| 17 Ekim 2026 | Dış sezon kapısı eklendi (geçti); 16 Ekim verisiyle yeniden eğitildi → `ridge_250`, RMSE 1.9102. |
