# LaLiga Sayım Modelleri (Korner, Taç, Ofsayt, Kart, Kurtarış)

**Rapor tarihi:** 26 Ekim 2026 (`v2.0`: Premier League özellik tanımlarına geçildi)
**Kod:** `src/features/build_league_pl_features.py` (özellikler: PL'nin kendi fonksiyonları), `src/models/train_league_counts.py` (eğitim), `src/models/count_model.py` ve `src/models/model_utils.py` (PL ile ortak seçim ve kapı kodu), `src/api/league_prediction.py` (servis)
**Ham sonuçlar (tek kaynak):** `docs/reports/models/la_liga_count_models.json` (üretim: PL özellik tanımları) ve `docs/reports/models/la_liga_count_models_league_features.json` (ilk sürüm: LaLiga'ya özgü özellikler; karşılaştırma için saklı) — bu sayfadaki sayılar bu dosyalardan alınmıştır.
**Yeniden üretim:** `python3 -m src.models.train_league_counts --competition la_liga` (üretim); ilk sürüm: `--features league` (yalnızca değerlendirir)
**Üretim dosyaları:** `models/production/la_liga/{corner,throws,offside,cards,saves}_model_v1.joblib`
**Veri:** yalnızca LaLiga (`competition_id = 140`), TheStatsAPI, 2022/23-2026/27; oynanmış 1.617 maç (hedefe göre 1.559-1.613 maçta hedef dolu). 2026/27 kısmi sezondur (97 maç) ve seçimde kullanılmaz, yalnızca izlenir.

## 1. Karar

PL sayım modelleriyle aynı seçim kodu çalıştırılır (`train_count_model`): ilk %80'de 4 genişleyen zaman katı, aday modeller (Ridge, Poisson, ElasticNet, LightGBM) ve `training_mean`; modelin eğitim ortalamasını en az %0,5 farkla ve en az 3 katta geçmesi (CV kapısı), ardından iç içe dış sezonlarda çoğunlukla geçmesi (dış sezon kapısı) gerekir. Kapıyı geçemeyen pazar `training_mean` sunar ve arayüzde `baseline` etiketi taşır.

| Pazar | Servis edilen | CV kazancı | Kat galibiyeti | Dış sezon | Holdout RMSE (model / ortalama) |
|---|---|---|---|---|---|
| Taç | `poisson_10` | %14,19 | 4/4 | 2/2 geçti | 7,339 / 9,154 |
| Ofsayt | `ridge_50` | %8,36 | 3/4 | 2/2 geçti | 2,140 / 2,257 |
| Kart | `training_mean` (ham en iyi `ridge_250`) | %1,81 | 3/4 | 1/2 geçemedi | 2,374 / 2,374 |
| Korner | `training_mean` (ham en iyi `elastic_0.5_0.2`) | %0,45 | 3/4 | CV kazancı eşik olan %0,5'in altında | 3,578 / 3,578 |
| Kurtarış | `training_mean` (ham en iyi `ridge_500`) | %0,41 | 3/4 | CV kazancı %0,5'in altında | 2,678 / 2,678 |

Servis edilen model `training_mean` olduğunda holdout RMSE iki sütunda aynıdır; çünkü servis edilen şey ortalamanın kendisidir. Üretimde iki pazar (taç ve ofsayt) model, üç pazar `baseline`dır.

## 2. Özellikler: PL ile aynı kod

İlk sürümde (bu raporun `v1.0`'ı) LaLiga'ya özgü bir özellik üretici kullanılmıştı. `v2.0`'da sayım modelleri PL'nin kendi özellik koduyla çalışır: `build_league_pl_features.py`, LaLiga istatistiklerini PL'nin ham sütun adlarına çevirir ve PL'nin `build_team_match_history`, `compute_pre_match_features`, `merge_features_to_matches`, `add_interaction_features` ve `compute_referee_features` fonksiyonlarını değiştirmeden çalıştırır. Rakip Elo normalizasyonu, penaltı arındırma (xG eksi penaltı başına 0,78; büyük şans eksi penaltı başına 1), kayan ve üstel pencereler, venue büzülmesi ve hakem eğilimleri bu yüzden PL ile aynı kodun çıktısıdır. Özellik listeleri PL'nin `CURATED_FEATURES` listeleridir; LaLiga'da verisi olmayan sütunlar çıkarılır.

| Pazar | Özellik sayısı | PL listesinden çıkarılanlar |
|---|---|---|
| Korner | 10 | yok |
| Taç | 12 | `home/away_inacc_fwd_pass_roll_10` (ileri pas hatası kaynakta yok) |
| Ofsayt | 10 | yok |
| Kart | 11 | yok (hakem ortalamaları PL'nin `compute_referee_features` çıktısı) |
| Kurtarış | 13 | yok |

Veri farkları: penaltı sayısı sağlayıcının xG ve penaltısız xG alanlarından kestirilir (`round((xG - npxG) / 0,78)`; penaltılı maçlarda fark 0,78-0,79 çıkar); ceza sahası giriş sayısı kaynakta yoktur, PL'deki bu sütun bu ligde sabittir ve kullanılmaz; PL'nin lig öncülleri (soğuk başlangıç doldurması) PL sabitleridir.

### v1.0 (LaLiga'ya özgü özellikler) ile karşılaştırma ve benimseme kararı

Karşılaştırmadan önce yazılan kural: PL tanımları, hiçbir modelin kapı sonucu kötüleşmediyse ve kapıyı geçen bir modelin holdout RMSE'si %2'den fazla artmadıysa benimsenir; gerekçe PL ile aynı tanımları kullanmaktır, performans kovalamak değildir.

| Pazar | v1.0 (LaLiga özellikleri) | v2.0 (PL özellikleri) |
|---|---|---|
| Taç | geçti, holdout RMSE 7,385 | geçti, 7,339 (%0,6 daha iyi) |
| Ofsayt | geçemedi (dış sezon 1/2), servis `training_mean` | geçti (2/2), holdout 2,140 |
| Kart | geçemedi | geçemedi |
| Korner | geçemedi | geçemedi |
| Kurtarış | geçemedi | geçemedi |

Kural sağlandığı için PL tanımları benimsendi. **Dikkat:** ofsayt kararı kırılgandır. İki sürümde özellik adları aynıdır ve 2024/25 ile 2025/26 sezonlarında iki sürüm neredeyse aynı sonucu verir (2,082 ve 2,087 karşı 2,085 ve 2,091). Fark yalnızca 2023/24 iç içe sezonundan gelir (tek sezonluk geçmiş): v1.0 orada `training_mean` seçti, PL tanımları (kayan pencerelerde `min_periods=1`) 2,358 ile ortalamanın (2,430) altına inebildi. Ofsayt modelinin kapıyı "geçmesi" bu nedenle tek bir erken sezona bağlıdır; 2027/28 verisiyle yeniden değerlendirilmelidir.

## 3. Sonuçlar (v2.0)

Dış sezon tablosu her sezonu yalnızca ondan önceki sezonlarla seçilip eğitilmiş modelle skorlar (RMSE; model / `training_mean`):

| Sezon | Korner | Taç | Ofsayt | Kart | Kurtarış |
|---|---|---|---|---|---|
| 2023/24 | 3,160 / 3,160 | 8,093 / 9,295 | 2,358 / 2,430 | 2,545 / 2,545 | 2,637 / 2,637 |
| 2024/25 | 3,281 / 3,281 | 8,421 / 9,863 | 2,082 / 2,330 | 2,484 / 2,575 | 2,438 / 2,438 |
| 2025/26 | 3,433 / 3,433 | 7,233 / 9,104 | 2,087 / 2,310 | 2,455 / 2,504 | 2,617 / 2,617 |
| 2026/27 (kısmi, izleme) | 3,868 / 3,897 | 7,460 / 8,757 | 2,215 / 2,282 | 2,035 / 2,122 | 2,534 / 2,534 |

- **Taç:** en net sinyal. Her dış sezonda ve her katta ortalamayı geçiyor; alt/üst 34,5 log-loss 0,608 (sabit oran 0,723). Permütasyon denetimi (bkz. [la_liga_feature_audit.md](la_liga_feature_audit.md)) en büyük payı topa sahip olma ve pas isabeti ailesine verir (RMSE +0,46); yani sinyal geçmiş taç sayısından çok takımın oyun tarzından geliyor. Nedensel kanıt değildir.
- **Ofsayt:** 2024/25 ve 2025/26'da ortalamanın yaklaşık %10 altında. Alt/üst 3,5 log-loss 0,688 (sabit oran 0,705). Bkz. yukarıdaki kırılganlık notu.
- **Kart:** küçük ama tutarlı bir eğilim var (2024/25, 2025/26 ve izleme sezonunda ortalamanın altında); CV kazancı %1,8 ama dış sezon kapısı 1/2 ile geçemedi.
- **Korner ve kurtarış:** ortalamadan ayırt edilemiyor; ikisi de CV kapısında elendi. Alt/üst log-loss'ları sabit orana eşit (korner 9,5 için 0,695 / 0,696).

## 4. Servis

`src/api/league_prediction.py`, PL'nin kendi `predict_count_market` fonksiyonunu kullanır: beklenen toplam, ev/deplasman payı (takımların 10 maçlık ortalamalarının oranı) ve negatif binom artı olasılıkları. Modeller PL tanımlı özellik tablosunun sütunlarını beklediği için servis o tabloyu (`build_parity_features`, süreç başına bir kez; veritabanı değişince yenilenir) kullanır; ilk istek yaklaşık yarım dakika sürer. Kapıyı geçemeyen pazarlar `model_skill = "baseline"` döner; hakem bloğu PL'nin hesabıyla hakemin ortalama kart ve faulünü gösterir. Şut pazarı için model yoktur, lig koşan ortalaması `baseline` olarak gösterilir.

## 5. Bilinen sınırlar

- Üretimde yalnızca taç ve ofsayt modeli kapıyı geçti; ofsayt kararı yukarıda anlatıldığı gibi tek bir erken iç içe sezona bağlıdır.
- İç içe dış sezon kapısı yalnızca iki sezon üretiyor; kapı tek bir sezonluk farkla karar verebilir.
- LaLiga için ayrı bir özellik ablasyonu yapılmadı; PL listeleri olduğu gibi kullanıldı. Taç ve ofsayt modellerinin permütasyon önemi [la_liga_feature_audit.md](la_liga_feature_audit.md) içindedir (taç: dört özellik ailesi de bilgi taşıyor, en büyüğü topa sahip olma ve pas isabeti; ofsayt: sinyal rakibin ofsayt geçmişinden geliyor).
- Hedefler 2022/23 başından beri dolu, ancak ofsayt hedefi 1.559, kurtarış 1.605 maçta var (kalanı kaynakta eksik; satır atılır).
- Alt/üst anlamlılık testi (bootstrap) yapılmadı; sonuçlar log-loss ve RMSE farklarıdır.
- PL özellik tablosunun üretimi yaklaşık 30 saniye sürer (PL kodu satır satır çalışır); PL kodu bu yüzden değiştirilmedi.
