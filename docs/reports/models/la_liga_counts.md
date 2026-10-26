# LaLiga Sayım Modelleri (Korner, Taç, Ofsayt, Kart, Kurtarış)

**Rapor tarihi:** 26 Ekim 2026 (`v1.0`)
**Kod:** `src/features/build_league_features.py` (özellikler, `count_feature_columns`), `src/models/train_league_counts.py` (eğitim), `src/models/count_model.py` ve `src/models/model_utils.py` (Premier League ile ortak seçim ve kapı kodu), `src/api/league_prediction.py` (servis)
**Ham sonuçlar (tek kaynak):** `docs/reports/models/la_liga_count_models.json` — bu sayfadaki sayılar bu dosyadan alınmıştır.
**Yeniden üretim:** `python3 -m src.models.train_league_counts --competition la_liga`
**Üretim dosyaları:** `models/production/la_liga/{corner,throws,offside,cards,saves}_model_v1.joblib`
**Veri:** yalnızca LaLiga (`competition_id = 140`), TheStatsAPI, 2022/23-2026/27; oynanmış 1.617 maç (hedefe göre 1.559-1.613 maçta hedef dolu). 2026/27 kısmi sezondur (97 maç), seçimde değil yalnızca izlemede görünür.

## 1. Karar

Premier League sayım modelleriyle aynı seçim kodu çalıştırıldı (`train_count_model`): ilk %80'de 4 genişleyen zaman katı, aday modeller (Ridge, Poisson, ElasticNet, LightGBM) ve `training_mean`; modelin eğitim ortalamasını en az %0,5 farkla ve en az 3 katta geçmesi (CV kapısı) ve ardından iç içe dış sezonlarda çoğunlukla geçmesi (dış sezon kapısı) gerekir. Kapıyı geçemeyen pazar `training_mean` sunar ve arayüzde `baseline` etiketi taşır.

| Pazar | Servis edilen | Ham en iyi aday | CV kazancı | Kat galibiyeti | Dış sezon | Holdout RMSE (model / ortalama) |
|---|---|---|---|---|---|---|
| Taç | `ridge_100` | `ridge_100` | %14,68 | 4/4 | 2/2 geçti | 7,385 / 9,154 |
| Korner | `training_mean` | `ridge_500` | %0,28 | 3/4 | CV kapısında elendi (kazanç eşik olan %0,5'in altında) | 3,578 / 3,578 |
| Ofsayt | `training_mean` | `ridge_50` | %8,52 | 4/4 | 1/2 geçemedi | 2,257 / 2,257 |
| Kart | `training_mean` | `ridge_250` | %2,58 | 3/4 | 1/2 geçemedi | 2,374 / 2,374 |
| Kurtarış | `training_mean` | `ridge_500` | %0,17 | 2/4 | CV kapısında elendi (kazanç %0,5'in altında, 3 kat gerekir) | 2,678 / 2,678 |

Servis edilen model `training_mean` olduğunda holdout RMSE iki sütunda aynıdır; çünkü servis edilen şey ortalamanın kendisidir.

## 2. Özellikler

Hepsi maç başlamadan önce bilinen bilgidir: takım geçmişi bir maç kaydırılır (`shift(1)`) ve ancak sonra kayan ortalama alınır; hakem ortalamaları yalnızca önceki kick-off gruplarından gelir ve lig ortalamasına doğru 8 maçlık ağırlıkla çekilir. 1X2 modelinin 118 özelliği değişmedi; sayım sütunları ayrı tutulur ve 1X2 kümesine girmez (test: `test_count_model_columns_stay_out_of_the_1x2_set_and_targets_are_sums`).

| Pazar | Hedef | Özellikler |
|---|---|---|
| Korner | `total_corners` | takımların atılan/yenilen korner (5 ve 10 maç), şut (5), rakip ceza sahasında dokunuş (5) |
| Taç | `total_throws` | takımların taç sayısı ve rakibe verilen taç (5 ve 10 maç), topa sahip olma (5), pas isabeti (10) |
| Ofsayt | `total_offsides` | takımların ofsayt sayısı ve rakibin ofsaytı (5 ve 10 maç), topa sahip olma (5) |
| Kart | `total_cards` (sarı + kırmızı) | takımların kart ve faul geçmişi (5), `abs_elo_diff`, hakem ortalama kart ve faul |
| Kurtarış | `total_saves` | takımların kurtarış sayısı (5 ve 10), rakibin şut ve isabetli şutu (5), şut (5) |

Premier League listelerinden farkı: PL'de kullanılan ve bu sağlayıcıda olmayan sütunlar yoktur (ileri pas hatası `inacc_fwd_pass`, beklenen taç `exp_*_throws_5`, `exp_match_shots_5`, 3 maçlık kurtarış penceresi); yerine sağlayıcıda olan karşılıkları kullanıldı. Hakem verisi PL'deki gibi kullanılır (`referee_avg_cards`, `referee_avg_fouls`), ancak hakem kodu bu sağlayıcıdan gelir ve PL'nin sabit varsayılanları yerine LaLiga'nın önceki günlerdeki lig ortalaması kullanılır.

## 3. Sonuçlar

Dış sezon tablosu her sezonu yalnızca ondan önceki sezonlarla seçilip eğitilmiş modelle skorlar (RMSE; model / `training_mean`):

| Sezon | Korner | Taç | Ofsayt | Kart | Kurtarış |
|---|---|---|---|---|---|
| 2023/24 | 3,160 / 3,160 | 8,061 / 9,295 | 2,430 / 2,430 | 2,545 / 2,545 | 2,637 / 2,637 |
| 2024/25 | 3,281 / 3,281 | 8,393 / 9,863 | 2,085 / 2,330 | 2,454 / 2,575 | 2,438 / 2,438 |
| 2025/26 | 3,433 / 3,433 | 7,228 / 9,104 | 2,091 / 2,310 | 2,435 / 2,504 | 2,617 / 2,617 |
| 2026/27 (kısmi, izleme) | 3,897 / 3,897 | 7,555 / 8,757 | 2,234 / 2,282 | 2,070 / 2,122 | 2,534 / 2,534 |

- **Taç:** tek net sinyal. Her dış sezonda ve her katta ortalamayı geçiyor. Alt/üst 34,5 olasılığı log-loss 0,608 (sabit oran 0,723). Olası bir neden, takımların taç atma alışkanlığının (oyun tarzı) sezonlar arasında kalıcı olmasıdır; bu bir açıklama önerisidir, özellik ablasyonuyla sınanmadı.
- **Ofsayt (kıl payı reddedildi):** CV'de ortalamayı %8,5 geçiyor ve 4/4 katı kazanıyor; 2024/25 ve 2025/26'da ortalamanın altında (2,085 ve 2,091 karşı 2,330 ve 2,310). Ancak kapı, iç içe dış sezonların çoğunluğunu ister ve ilk dış sezon (2023/24) yalnızca bir sezonluk geçmişle `training_mean` seçti; bu yüzden 1/2 oldu ve kapı geçmedi. Bu bir veri kıtlığı sonucudur, model zayıflığının kanıtı değildir. Veri biriktikçe (2027/28) yeniden değerlendirilmeli; kapıyı gevşetmek yerine bekleniyor.
- **Kart:** küçük ama tutarlı bir eğilim (2024/25, 2025/26, 2026/27'de ortalamanın altında) var; CV kazancı %2,6 ama kapıdan geçmedi (dış sezon 1/2).
- **Korner ve kurtarış:** ortalamadan ayırt edilemiyor; ikisi de CV kapısında elendi (CV kazancı %0,28 ve %0,17). Alt/üst log-loss'ları sabit orana eşit (korner 9,5 için 0,695 / 0,696).

## 4. Servis

`src/api/league_prediction.py`, Premier League'in kendi `predict_count_market` fonksiyonunu kullanır: beklenen toplam, ev/deplasman payı (takımların 10 maçlık ortalamalarının oranı) ve negatif binom artı olasılıkları. Kapıyı geçemeyen pazarlar `model_skill = "baseline"` döner; hakem bloğu hakemin LaLiga'daki ortalama kart ve faulünü gösterir. Şut pazarı için model yoktur, lig koşan ortalaması `baseline` olarak gösterilir.

## 5. Bilinen sınırlar

- Yalnızca taç modeli kapıyı geçti. Dört pazar ortalamayı servis ediyor; bu PL'deki davranışla aynı kuraldır, hata değildir.
- İç içe dış sezon kapısı yalnızca iki dış sezon üretiyor (2023/24, 2024/25 geliştirme bölümünde); kapı tek bir sezonluk farkla karar verebilir. Ofsayt bunun örneğidir.
- Özellik listeleri PL listelerinin karşılığı olarak seçildi; LaLiga için ayrı bir özellik ablasyonu yapılmadı. Taç modelinin kazancının hangi özellikten geldiği (tablo: üst katsayılar `home_pass_pct_roll_10`, `home_throws_against_roll_10`) incelenmedi.
- Hedefler 2022/23 başından beri dolu, ancak ofsayt hedefi 1.559, kurtarış 1.605 maçta var (kalanı kaynakta eksik; satır atılır).
- Alt/üst anlamlılık testi (bootstrap) yapılmadı; sonuçlar log-loss ve RMSE farklarıdır.
