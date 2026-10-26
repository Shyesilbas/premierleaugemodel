# Taç Atışı Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026  
**Artifact:** `models/production/premier_league/throws_model_v1.joblib` · **Eğitim kodu:** `src/models/train_throws.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam taç atışı  
**Veri:** 1.580 tamamlanmış maç; 2026/27 kilitli sezon (60 maç), yalnızca raporlanır.  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim henüz yapılmadı.

---

## 1. Karar

🏆 **Üretimde `poisson_10`.** CV'de ortalamaya karşı en büyük kazanç bu modelde (%15.1, 4/4 kat); dış sezon kapısı 3/3. Holdout'ta RMSE %5.0 iyi (R² 0.092); Üst 34.5'te sabit orandan 0.033 LL daha iyi.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Özellikler (14) | `home_throws_roll_5/10`, `away_throws_roll_10`, `home_opponent_throws_roll_10`, `away_opponent_throws_roll_5/10`, `exp_home/away_throws_5`, `home/away_possession_roll_5`, `home/away_pass_pct_roll_10`, `home/away_inacc_fwd_pass_roll_10` |
| Aday modeller | `lgbm_shallow`, Ridge ve Poisson ızgaraları (`train_throws.py`) + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; CV kapısı + dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0265 |
| En etkili özellikler (mutlak katsayı) | `home_possession_roll_5`, `home_opponent_throws_roll_10`, `away_throws_roll_10`, `home_pass_pct_roll_10` |

## 3. Sonuçlar

**Kapılar:** CV kazancı %15.14, 4/4 kat ✅ · Dış sezon 3/3 ✅

**Holdout (son %20, 316 maç):**

| Ölçüm | Model | Ortalama |
| :--- | :---: | :---: |
| RMSE | 7.0221 | 7.3881 |
| MAE | 5.6042 | 5.9665 |
| R² | 0.0919 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `poisson_10` | 7.5199 | 9.1766 | ✅ |
| 2024_25 | 760 | `ridge_50.0` | 6.9666 | 8.5265 | ✅ |
| 2025_26 | 1140 | `ridge_100.0` | 6.9305 | 7.2030 | ✅ |
| 2026_27 🔒 (kilitli, kısmi) | 1520 | `poisson_10` | 7.3552 | 7.3005 | ❌ |

**Eşik pazarı (holdout):**

| Pazar | Dev oranı | NB LL | Poisson LL | Sabit oran LL | NB isabet | Çoğunluk isabet |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Üst 34.5 | %52.8 | 0.6598 | 0.6655 | 0.6929 | %62.0 | %51.6 |

## 4. Bilinen Sınırlar

- Ortalamaya karşı büyük kazancın bir kısmı sezon seviyesindeki kaymadan geliyor (2023/24'te ortalama RMSE 9.18, model 7.52): takım bazlı rolling özellikler lig seviyesini sabit ortalamadan daha hızlı izliyor. Kazancın ne kadarının "maçlar arası ayrım", ne kadarının "seviye uyumu" olduğu ayrıştırılmadı.
- Kilitli 2026/27'nin ilk 60 maçında ortalamadan hafif kötü (7.3552 vs 7.3005); izlenmeli.

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `poisson_10`, RMSE 7.0221. |
| 17 Ekim 2026 | Dış sezon kapısı eklendi (geçti); 16 Ekim verisiyle yeniden eğitildi → değişmedi. |
