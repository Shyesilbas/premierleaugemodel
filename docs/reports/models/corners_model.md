# Korner Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026  
**Artifact:** `models/production/corner_model_v1.joblib` · **Eğitim kodu:** `src/models/train_corners.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** maç toplam korner sayısı (eksik 67 maç olay akışından kurtarıldı — ana rapor Bölüm 2.3)  
**Veri:** 1.580 tamamlanmış maç; 2026/27 kilitli sezon (60 maç), yalnızca raporlanır.  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../model_benchmarks.md)

> Bu rapor artifact metriklerinin özetidir; kart ve gol modellerindeki gibi derin bir denetim (özellik ablasyonu, sinyal kaynağı analizi) henüz yapılmadı.

---

## 1. Karar

🏆 **Üretimde `elastic_0.05_0.8`.** Her iki kapıyı geçiyor, ama kazanç küçük: holdout'ta RMSE %1.3 iyi, R² yalnızca 0.004. Üst 8.5 / 9.5 / 10.5 pazarlarında sabit orandan 0.010–0.016 LL daha iyi.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Özellikler (10) | `home/away_corners_for_roll_10`, `home/away_corners_against_roll_10`, `home/away_corners_for_roll_5`, `home/away_shots_for_roll_5`, `home/away_touches_in_opp_box_roll_5` |
| Aday modeller | `train_corners.py` içindeki Ridge / Poisson / ElasticNet / LGBM ızgarası + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; CV kapısı + dış sezon kapısı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | NB2(μ, α), α = 0.0114 (neredeyse Poisson) |

## 3. Sonuçlar

**Kapılar:** CV kazancı %0.87, 3/4 kat ✅ · Dış sezon 2/3 ✅

**Holdout (son %20, 316 maç):**

| Ölçüm | Model | Ortalama |
| :--- | :---: | :---: |
| RMSE | 3.1999 | 3.2405 |
| MAE | 2.6023 | 2.6610 |
| R² | 0.0042 | — |

**Dış sezonlar:**

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `training_mean` | 3.5986 | 3.5986 | ❌ (eşit) |
| 2024_25 | 760 | `ridge_250` | 3.4342 | 3.4719 | ✅ |
| 2025_26 | 1140 | `elastic_0.05_0.5` | 3.2535 | 3.2892 | ✅ |
| 2026_27 🔒 (kilitli, kısmi) | 1520 | `ridge_50` | 3.1648 | 3.2401 | ✅ |

**Eşik pazarları (holdout):**

| Pazar | Dev oranı | NB LL | Poisson LL | Sabit oran LL | NB isabet | Çoğunluk isabet |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Üst 8.5 | %69.5 | 0.6598 | 0.6637 | 0.6713 | %62.7 | %62.7 |
| Üst 9.5 | %58.3 | 0.6859 | 0.6870 | 0.6955 | %54.1 | %53.5 |
| Üst 10.5 | %47.9 | 0.6708 | 0.6707 | 0.6865 | %60.8 | %58.9 |

## 4. Bilinen Sınırlar

- Kazanç küçük (R² ≈ 0); pazarlarda isabet çoğunluk tahmininin ancak 0–2 puan üstünde. Olasılıklar bilgi verir, bahis edge'i iddiası için yeterli değil.
- Seçilen algoritma sezondan sezona değişiyor (Ridge ↔ ElasticNet); sinyal zayıf ve ızgarada birbirine çok yakın adaylar var.

## 5. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `elastic_0.05_0.5`, RMSE 3.1952. (Ana rapordaki "`poisson_10`, 19 özellik, RMSE 3.2198" kaydı bu artifact ile uyuşmuyordu.) |
| 17 Ekim 2026 | Dış sezon kapısı eklendi (geçti); 16 Ekim özellik verisiyle yeniden eğitildi → `elastic_0.05_0.8`, RMSE 3.1999. |
