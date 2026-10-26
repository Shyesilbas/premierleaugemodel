# Kart Sayım Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026  
**Artifact:** `models/production/premier_league/cards_model_v1.joblib` · **Eğitim kodu:** `src/models/train_cards.py` · **Ortak yardımcılar:** `src/models/model_utils.py`  
**Hedef:** `total_cards` = iki takımın sarı + kırmızı kart toplamı (`src/processing/process_season_data.py:282`)  
**Veri:** 1.580 tamamlanmış maç (2022/23–2026/27); 2026/27 kilitli sezon (60 maç), yalnızca raporlanır.  
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Model Benchmarks](../model_benchmarks.md)

---

## 1. Karar

🛡️ **Üretimde sabit ortalama (`training_mean`).** Özellikli aday (`poisson_1`) CV kapısını geçti ama iç içe dış sezonların yalnızca 1/3'ünde ortalamayı yendi; 17 Ekim 2026'da eklenen dış sezon kapısı onu ortalamaya düşürdü. API `cards.model_skill = "baseline"` döner, arayüz "Veri ortalaması tabanlı tahmin" rozetini gösterir.

Maç öncesi verilerle toplam kart sayısı bu veri setinde ortalamadan güvenilir biçimde iyi tahmin edilemiyor. En büyük değişkenlik kaynağı sezonlar arası seviye kayması (3.70 → 4.37 → 4.23 → 3.87 kart/maç); hakem ve takım disiplin özellikleri bunu öngörmüyor.

## 2. Mimari

| Bileşen | Değer |
| :--- | :--- |
| Aday özellikler (11) | `home/away_cards_for_roll_5`, `home/away_cards_against_roll_5`, `home/away_fouls_committed_roll_5`, `home/away_fouls_drawn_roll_5`, `abs_elo_diff`, `referee_avg_cards`, `referee_avg_fouls` |
| Aday modeller | `lgbm_shallow`, Ridge, Poisson, ElasticNet ızgaraları (`train_cards.py`) + `training_mean` |
| Seçim | İlk %80'de 4 genişleyen zaman katı, RMSE; ardından iki kapı (ana rapor Bölüm 8, madde 7) |
| Olasılıklar | Üst 3.5 / 4.5 / 5.5: NB2(μ, α), α = 0.0287 (tüm veri), dev α = 0.0339 |
| Sızıntı | Takım özellikleri `shift(1)` ile; hakem ortalaması aynı başlama saatindeki maçlar okunduktan sonra güncellenir (`build_features.py:1148-1170`), 10 maçlık büzülme ile 4.15'e çekilir |

## 3. Sonuçlar

**Kapılar:**

| Kapı | Sonuç |
| :--- | :--- |
| CV kapısı (≥%0.5 kazanç, ≥3/4 kat) | ✅ `poisson_1`: %1.76 kazanç, 4/4 kat |
| Dış sezon kapısı (tam sezonların çoğunluğu) | ❌ 1/3 → `training_mean` |

**Dış sezonlar** (her sezon yalnızca önceki sezonlarla seçildi ve eğitildi):

| Dış sezon | Eğitim maçı | Seçilen | RMSE | Ortalama RMSE | Ortalamayı geçti |
| :--- | :---: | :--- | :---: | :---: | :---: |
| 2023_24 | 380 | `training_mean` | 2.3007 | 2.3007 | ❌ |
| 2024_25 | 760 | `poisson_1` | 2.1937 | 2.2572 | ✅ |
| 2025_26 | 1140 | `poisson_1` | 2.0528 | 2.0379 | ❌ |
| 2026_27 🔒 (kilitli, kısmi) | 1520 | `poisson_1` | 1.9048 | 1.8762 | ❌ |

**Kapıdan önceki özellikli model, son %20 holdout (316 maç):** RMSE 2.0201 / ortalama 2.0014, MAE 1.633 / 1.608, R² −0.025. Üst 3.5 log-loss NB 0.6888 / sabit oran 0.6837; Üst 4.5 0.6646 / 0.6588. Model her ölçüde ortalamadan kötüydü. (Holdout kilitli sezonu içerdiği için kapı kararında kullanılmaz.)

**Üretimdeki ortalama ile holdout:** RMSE 2.0014, Üst 3.5 LL 0.6834, Üst 4.5 LL 0.6580.

## 4. Denetim Bulguları (17 Ekim 2026)

1. **Kapı açığı (düzeltildi).** Eski kapı yalnızca geliştirme dönemindeki CV'ye bakıyordu; özellikli model holdout'ta kaybettiği halde API "model" diyordu. Dış sezon kapısı eklendi (`apply_outer_season_gate`).
2. **Sinyal kararsız.** Özellikler 2023/24 ve 2024/25'te ortalamayı ~%1.2–2.8 RMSE geçiyor, 2025/26 ve kilitli 2026/27'de kaybediyor. Tam sezonlar birleştirildiğinde kazanç ~%1.2 RMSE ve 0.006–0.008 LL; tamamı ilk iki sezondan.
3. **11 özellik ≈ 1 özellik.** Eşleşme bazlı beklenen kart toplamı (`exp_home_cards_5 + exp_away_cards_5`) tek başına 11 özellikli modelle aynı sonucu veriyor (havuz RMSE 2.1705 vs 2.1731). Bu sadeleştirme dış sezon kapısını yine geçemiyor (0/3), bu yüzden aday listesi değiştirilmedi.
4. **Hakem etkisi bu veride yok; özellik doğru kurulmuş.**
   - 15+ maçlı 20 hakemde ANOVA p = 0.28, Kruskal p = 0.20; hakem ortalamaları 3.62 (Oliver) – 4.58 (Coote).
   - Hakem ortalamalarının ikiye bölünmüş veride tutarlılığı 0.11.
   - Önceki sezonların (sezon-ortalamasından arındırılmış) hakem ortalaması, sonraki sezonu tahmin etmiyor (Spearman −0.10 … 0.06).
   - `referee_avg_cards` ile toplam kart Spearman korelasyonu 0.011.
5. **Seviye kayması baskın.** Son 380 maçın ortalaması genel ortalamadan bile kötü (havuz RMSE 2.2036 vs 2.1986): yeni sezonun kart seviyesi önceden bilinemiyor.
6. **Dağılım neredeyse Poisson.** Sezonluk α 0.015–0.047; NB ile Poisson olasılıkları arasındaki fark ≤0.0005 LL.
7. **Gizli API riski (tetiklenmiyor).** `server.py` eksik özellikleri `0.0` ile dolduruyor; hakem alanları eksik gelseydi eski model 4.11 yerine 3.37 tahmin ederdi. Normal akışta `build_prediction_row` hakem varsayılanlarını koyuyor; artık üretim modeli ortalama olduğu için etkisi de yok.
8. **Arayüz notu.** Ev/deplasman kart dağılımı (`home_cards_share`) ve hakem k/m kutusu modelden değil, rolling ortalamalardan ve hakem tablosundan gelir; bunlar bilgi amaçlıdır.

## 5. Reddedilen / Uygulanmayan Deneyler

| Deneme | Sonuç | Karar |
| :--- | :--- | :--- |
| Tek özellik (`exp_home_cards_5`, `exp_away_cards_5`) | Dış sezon 0/3 | ❌ Aday listesi değişmedi |
| Son 380 maç ortalaması (seviye uyumu) | Havuz RMSE 2.2036 > 2.1986 | ❌ |
| Hakem büzülmesini azaltmak | Hakem kimliği anlamlı sinyal taşımıyor (ANOVA p = 0.28) | ❌ Denenmedi, gerekçesiz |

## 6. Açık Sorular

- `total_yellow_cards_target_usable` bayrağı eğitimde filtrelenmiyor; eksik raporlanmış maçlar hedefe girmiş olabilir. Sayısı doğrulanmadı.
- Sinyal sezon içinde geri gelirse dış sezon kapısı özellikli modeli kendiliğinden geri alır; 2026/27 tamamlanınca yeniden değerlendirilmeli.

## 7. Değişiklik Geçmişi

| Tarih | Değişiklik |
| :--- | :--- |
| 14 Ekim 2026 | `poisson_1` (11 özellik) üretimde; holdout'ta ortalamadan kötü olduğu fark edilmedi. Ana rapordaki "`ridge_500`, 17 özellik, RMSE 2.0298" kaydı bu artifact ile zaten uyuşmuyordu. |
| 17 Ekim 2026 | Denetim; dış sezon kapısı eklendi; model 16 Ekim özellik verisiyle yeniden eğitildi → `training_mean`. |
