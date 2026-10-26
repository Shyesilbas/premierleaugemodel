# LaLiga 1X2 ve Gol Modeli

**Rapor tarihi:** 26 Ekim 2026 (`v1.0`)
**Kod:** `src/features/build_league_features.py` (özellikler), `src/models/train_league_model.py` (eğitim ve değerlendirme), `src/api/league_prediction.py` (tahmin servisi), `src/analytics/league_audit.py` (Model Doğrulama sayfası)
**Ham sonuçlar (tek kaynak):** `docs/reports/models/la_liga_walk_forward.json` — bu sayfadaki sayılar bu dosyadan alınmıştır.
**Yeniden üretim:** `python3 -m src.models.train_league_model --competition la_liga` (yaklaşık 40 saniye)
**Üretim dosyası:** `models/production/la_liga/outcome_models_v1.joblib`

## 1. Amaç ve veri

LaLiga maçları için maç sonucu (1X2), toplam gol (alt/üst 1.5, 2.5, 3.5) ve karşılıklı gol olasılıkları. Veri yalnızca TheStatsAPI'dendir (2022/23-2026/27, 1.617 oynanmış maç; bkz. `docs/data_sources.md`). PL modelinin kullandığı PulseLive olay akışı ve oyuncu rating hattı yoktur; bu yüzden özellik üretici ayrı yazıldı.

## 2. Özellikler (118 adet)

Hepsi maç başlamadan önce bilinen bilgidir: her takımın geçmişi bir maç kaydırılır (`shift(1)`) ve ancak sonra kayan ortalama ya da üstel ortalama alınır; Elo ve puan tablosu sonuç kaydedildikten sonra güncellenir; lig geneli öncüller yalnızca önceki günlerden gelir.
- Elo (genel ve iç saha/deplasman), maç başına puan ve averaj, terfi bayrağı, dinlenme günü (PL modeliyle aynı sabitler).
- Gol, xG, isabetli şut, şut, büyük şans, topa sahip olma, pas isabeti, rakip ceza sahasında dokunuş: son 5 ve 10 maç ortalaması, üstel ortalama (0.2), iç saha/deplasmana özgü 5 maçlık ortalama, farklar.
- Dışarıda bırakılanlar: kadro piyasa değerleri (sağlayıcı yalnızca bugünkü kadroyu verir, geçmiş sezonlara uygulamak gelecek bilgisini sızdırır), ceza sahası giriş sayısı (kaynakta yok; PL modelinde de katkısı ölçülebilir değildi), ilk 11 derecelendirmesi ve devamlılığı (yazıldı ve sınandı; kazanç getirmediği için üretim kümesine alınmadı, bkz. Bölüm 7).

## 3. Protokol

| Rol | Sezon |
|---|---|
| Isınma (yalnızca geçmiş olarak kullanılır) | 2022/23 |
| Dış sezon 1 | 2024/25 (öncesindeki sezonlarla eğitildi) |
| Sınama (dış sezon 2) | 2025/26 (öncesindeki sezonlarla eğitildi) |
| İzleme, karar için kullanılmaz | 2026/27 (kilitli; 97 maç) |

Her sezon, yalnızca ondan önceki sezonlarla eğitilmiş modelle tahmin edildi. Aday model (lojistik regresyon ya da LightGBM) kronolojik çapraz doğrulamayla, sıcaklık/sapma kalibratörü eğitim içi ileriye dönük tahminlerle seçildi; hiçbir seçimde dış sezon verisi kullanılmadı. Kıyaslar: lig taban oranı, Elo farkı + ev sahibi avantajı (aynı geçmişe eğitilmiş), 2024/25'ten itibaren bahis şirketlerinin kapanış oranları. Eşli bootstrap 10.000 çekiliş, tohum 42, Benjamini-Hochberg düzeltmesi, farkın gürültü içinde kaldığı yerde %80 güç için gereken örneklem.

## 4. Sonuçlar (log-loss, düşük daha iyi)

| Sezon | Maç | Model | Taban oran | Elo | Piyasa |
|---|---|---|---|---|---|
| 2024/25 | 380 | 0.9750 | 1.0708 | 0.9754 | 0.9447 |
| **2025/26 (sınama)** | 380 | **0.9725** | 1.0489 | 0.9885 | 0.9624 |
| 2026/27 (izleme) | 97 | 0.9402 | 1.0742 | 0.9631 | 0.9134 |

İki dış sezon birlikte (760 maç), model eksi rakip (negatif model lehine), %95 aralık:
- Taban orana karşı: -0.0861 [-0.1198, -0.0511], q = 0.000. **Anlamlı üstünlük.**
- Elo'ya karşı: -0.0082 [-0.0249, +0.0089], q = 0.343. **Ayırt edilemiyor**; modelin ortalaması her sezonda Elo'nun önünde ama fark gürültü içinde. Bu farkı %80 güçle görmek için yaklaşık 6,619 maç gerekir.
- Piyasaya karşı: +0.0194 [+0.0024, +0.0367], q = 0.038. Piyasa daha iyi; sınama sezonunda tek başına fark +0.0101 [-0.0095, +0.0300] ile gürültü içinde.

Sınama sezonu (2025/26) tek başına: taban orana karşı -0.0764 [-0.1187, -0.0346]; Elo'ya karşı -0.0161 [-0.0371, +0.0045].

**Kapı kararı:** Model, taban oranı anlamlı biçimde geçtiği ve ortalaması Elo referansının altında olduğu için sunuluyor (`decision.serving = model`). Elo'dan üstünlüğü kanıtlanmış değildir; kural bilerek "kötü değil" eşiğidir. Model bir gün Elo'dan kötü çıkarsa servis otomatik olarak Elo referansına döner ve arayüzde "referans" olarak etiketlenir.

## 5. Gol pazarları (760 dış sezon maçı)

> **Güncelleme (26 Ekim 2026):** Bu bölümdeki model artık üretimde değildir; gol pazarları PL'nin gol modeliyle ve ayrı bir dış sezon değerlendirmesiyle sunuluyor (1.5 ve 2.5 üstü modelden, 3.5 üstü ve KG taban oranından). Ayrıntı: [la_liga_goals.md](la_liga_goals.md). Aşağıdaki tablo önceki modelin (beşli aile) sonucudur ve karşılaştırma için saklıdır.

Aynı iki dış sezonda her pazar, eğitim taban oranına karşı eşli bootstrap (10.000 çekiliş, tohum 42) ile sınandı; beş testin ailesi üzerinde Benjamini-Hochberg düzeltmesi uygulandı. Fark negatifse model lehinedir.

| Ölçü | Model | Taban / eğitim ortalaması | Fark [%95 aralık] | q | Servis |
|---|---|---|---|---|---|
| Toplam gol MAE | 1.2274 | 1.2537 | -0.0263 [-0.0523, -0.0003] | 0.118 | beklenen gol gösterilir |
| Alt/üst 1.5 log-loss | 0.5512 | 0.5630 | -0.0117 [-0.0236, +0.0009] | 0.118 | `baseline` |
| Alt/üst 2.5 log-loss | 0.6766 | 0.6940 | -0.0174 [-0.0311, -0.0034] | 0.081 | `baseline` |
| Alt/üst 3.5 log-loss | 0.5483 | 0.5595 | -0.0112 [-0.0264, +0.0040] | 0.152 | `baseline` |
| Karşılıklı gol log-loss | 0.6879 | 0.6917 | -0.0038 [-0.0087, +0.0011] | 0.152 | `baseline` |

Beş ölçünün beşinde de yön modelin lehine, ama düzeltmeden sonra hiçbiri q < 0.05 değil (en güçlüsü 2.5 üstü, q = 0.081; düzeltmesiz aralığı sıfırı dışarıda bırakıyor). Önceden yazılmış kapı kuralı (PL'deki pazar bazlı `skill_gate` mantığı): pazar, eğitim taban oranını FDR düzeltmeli olarak geçmedikçe serviste taban oranı sunulur ve `baseline` etiketi taşır. Bu yüzden şu an dört pazar da taban oranı gösteriyor (eğitim taban oranları: 1.5 üstü %73,2; 2.5 üstü %48,1; 3.5 üstü %24,8; KG %52,6); beklenen gol sayıları (ev/deplasman/toplam) ve 0.5 üstü modelden gelmeye devam eder. Bu farkı %80 güçle ayırt etmek için 2.5 üstünde yaklaşık 1.022, diğerlerinde 1.742 ile 2.846 maç gerekir; yani bir ila iki ek sezon.

Bağımsız Poisson oranları, Dixon-Coles matrisi (rho = -0.04) kalibre edilmiş 1X2'ye hizalanır; böylece tüm pazarlar tek dağılımdan çıkar. Korner, taç, ofsayt, kart ve kurtarış için ayrı sayım modelleri vardır (bkz. [la_liga_counts.md](la_liga_counts.md)); taç ve ofsayt kapıyı geçti, diğerleri `baseline` etiketli ortalamadır. Şut için model yoktur, lig koşan ortalaması `baseline` etiketiyle gösterilir.

## 6. Bilinen sınırlar

- Seçilen düzenlileştirme (C = 0.001) eski ızgaranın en güçlü ucuydu; daha güçlü adaylar (C = 0.0003, 0.0001) Bölüm 8'de sınandı ve her sezonda CV'de daha kötü çıktı, yani 0.001 gerçek bir en iyidir. 118 özellik yerine 22 özellikli küme de sınandı ve anlamlı kazanç vermedi (Bölüm 8).
- Elo'dan üstünlük kanıtlanamadığı için model, Elo'ya yakın bir yetenektedir; piyasa ise anlamlı derecede daha iyi.
- Ceza sahası giriş sayısı ve piyasa değeri yoktur. İlk 11 özellikleri yazıldı ama üretim kümesinde değildir (Bölüm 7); serviste maç başlamadan önce resmi ilk 11 kullanılmaz.
- Üretim dosyası oynanmış tüm maçlarla (kilitli sezonun oynanmış 97 maçı dahil) eğitildi; seçimler yalnızca kilitsiz sezonlarla yapıldı. Takvimden gelen yer tutucu maçların tarihleri değişebilir; saatleri belli değildir.
- Model doğrulama sayfası yalnızca dış sezonları (2024/25, 2025/26) ve izleme sezonunu gösterir; 2022/23-2023/24 eğitim verisidir, bağımsız tahmin yoktur. Oynanmamış maç tahminleri sayfada yoktur, maç sayfasında vardır.

## 7. Reddedilen deney: ilk 11 ve oyuncu rating özellikleri (No Gain, Not Adopted)

**Ham sonuçlar:** `docs/reports/models/la_liga_xi_ablation.json`. **Yeniden üretim:** `python3 -m src.models.ablate_league_features --competition la_liga --group xi` (yaklaşık 1 dakika).

**Eklenen 12 özellik** (PL'nin ilk 11 özelliklerinin karşılığı, `src/features/build_league_features.py` içinde `_xi_features`): ilk 11'in oyuncu formu ortalaması (`home/away_xi_rating`, `xi_rating_diff`), hücum oyuncularının formu ile rakip savunmanın formu (`home_xi_att_vs_away_def`, `away_xi_att_vs_home_def`, `xi_att_vs_def_diff`), ilk 11 devamlılığı (son 12 maçta ilk 11 oyuncularının dakika payı ortalaması; `*_xi_continuity`, `xi_continuity_diff`) ve dakika payıyla ağırlıklı form (`*_xi_weighted_ov`, `xi_weighted_ov_diff`). Oyuncu formu yalnızca o maçtan önceki görünümlerden gelir: son 5 görünümün ağırlıklı ortalamasının %70'i ile sezon ortalamasının %30'u, en az 20 dakikalık görünümler, geçmişi olmayan oyuncuya o ana kadarki lig ortalaması. Kaynak, sağlayıcının oyuncu başına `rating` alanıdır; PL'deki gibi ayrı hücum ve savunma puanı yoktur, hücum/savunma ayrımı pozisyonla (F, M / D, G) yapılır. Sızıntı testi: `test_xi_features_ignore_the_match_itself_and_later_matches_and_stay_out_of_the_default_set`.

**Protokol ve karar kuralı (çalıştırmadan önce yazıldı):** Her dış sezon yalnızca ondan önceki sezonlarla seçilmiş ve kalibre edilmiş modelle tahmin edildi; üretim kümesi (118) ile üretim kümesi + 12 ilk 11 özelliği aynı yürüyen protokolde karşılaştırıldı; maç başına log-loss farkı eşli bootstrap (10.000 çekiliş, tohum 42). Benimseme: iki dış sezonun toplam farkı negatif ve %95 aralığı sıfırın altında olmalı, ayrıca sınama sezonu tek başına da negatif olmalı.

| Sezon | 118 özellik | 118 + ilk 11 |
|---|---|---|
| 2024/25 | 0.9750 | 0.9783 |
| 2025/26 (sınama) | 0.9725 | 0.9728 |
| 2026/27 (izleme) | 0.9402 | 0.9402 |

Fark (ilk 11 eklenmiş eksi taban, pozitif eklenmişin daha kötü olduğu anlamına gelir): iki dış sezon birlikte +0.0018 [-0.0005, +0.0041], p = 0.117; sınama sezonu tek başına +0.0003 [-0.0026, +0.0032]. Her iki durumda da seçilen aday `logreg_C0.001`. **Karar: kazanç yok, benimsenmedi; üretim özellik kümesi 118 olarak kaldı.**

Yorum (kanıtlanmış değil): C = 0.001 ile model çok güçlü düzenlileştirilmiş olduğundan 12 yeni, birbirine ve mevcut form özelliklerine bağlı sütunun eklenebileceği ek bilgi çok az; oyuncu rating'i takım düzeyindeki xG ve şut formunda zaten büyük ölçüde görünüyor olabilir. Bu bir açıklama önerisidir; ayrı bir deneyle sınanmadı. İlk 11 özellikleri `feature_columns(frame, include_xi=True)` ile açılır; yeni bir protokolde (örneğin daha az, daha seçilmiş özellik kümesi) yeniden denenebilir.

## 8. Reddedilen deneyler: daha güçlü düzenlileştirme ve özellik azaltma (No Gain, Not Adopted)

**Ham sonuçlar:** `docs/reports/models/la_liga_ablation_low_c_core_core_low_c.json`. **Yeniden üretim:** `python3 -m src.models.ablate_league_features --competition la_liga --group low_c core core_low_c` (yaklaşık 1 dakika).

Bölüm 6'daki iki açık soru, Bölüm 7'deki protokolle ve çalıştırmadan önce yazılmış kuralla sınandı (benimseme: iki dış sezonun toplam farkı negatif, %95 aralığı sıfırın altında, üç varyantın ailesi üzerinde Benjamini-Hochberg q < 0.05 ve sınama sezonu tek başına negatif):
- **`low_c`:** aday ızgarasına C = 0.0003 ve 0.0001 eklendi. Adayı yine yalnızca önceki sezonlarla kronolojik CV seçti. CV log-loss (2024/25, 2025/26, 2026/27 için; düşük iyi):

| C | 2024/25 | 2025/26 | 2026/27 |
|---|---|---|---|
| 0.0001 | 1.0294 | 1.0189 | 1.0054 |
| 0.0003 | 1.0063 | 0.9960 | 0.9862 |
| **0.001** | **0.9921** | **0.9850** | **0.9796** |
| 0.003 | 0.9970 | 0.9900 | 0.9867 |

CV eğrisi U şeklindedir: 0.001 her sezonda en iyidir, daha güçlü de daha zayıf düzenlileştirme de daha kötüdür. Seçim değişmediği için dış sezon sonuçları üretimle birebir aynıdır (fark 0). Sonuç: ızgara kenarı endişesi giderildi.
- **`core`:** 118 özellik yerine, sonuçlara bakmadan yazılmış 22 özellik (Elo, puan ve averaj farkları, xG formu ve iç saha/deplasman farkı, büyük şans ve isabetli şut farkları, dinlenme ve terfi bayrakları; liste `src/models/ablate_league_features.py` içinde `CORE_FEATURES`). Seçilen aday `logreg_C0.003`.

| Sezon | 118 özellik | 22 özellik |
|---|---|---|
| 2024/25 | 0.9750 | 0.9770 |
| 2025/26 (sınama) | 0.9725 | 0.9646 |
| 2026/27 (izleme) | 0.9402 | 0.9539 |

İki dış sezon birlikte fark (22 eksi 118; negatif 22 özelliğin lehine) -0.0029 [-0.0137, +0.0075], q = 0.585; sınama sezonu tek başına -0.0079 [-0.0200, +0.0046], p = 0.215. Yön sezondan sezona değişiyor (2024/25 ve izleme sezonunda daha kötü, sınama sezonunda daha iyi) ve aralık sıfırı geniş biçimde içeriyor; bu farkı %80 güçle ayırt etmek için yaklaşık 20.000 maç gerekirdi. `core_low_c` aynı adayı seçtiği için `core` ile aynı sonucu verir.

**Karar: ikisi de benimsenmedi; üretim modeli 118 özellik ve `logreg_C0.001` olarak kaldı.** Daha az özellikli modelin eşit derecede iyi çıkması, 118 özelliğin bilgi eklemediğini düşündürür ama bunu kanıtlamıyor; iki kümeyi ayırt edecek veri yok. Özellik ailesi permütasyon denetimi de aynı yöndedir ([la_liga_feature_audit.md](la_liga_feature_audit.md)): hiçbir aile tek başına ayırt edilemiyor, bilgi yedekli. Bu, Bölüm 4'teki "Elo'ya yakın yetenek" bulgusuyla tutarlıdır: bu veri boyutunda form özelliklerinin Elo'nun ötesinde eklediği bilgi, ölçülebilir değildir.

## 9. PL özellik tanımlarıyla 1X2 (No Gain, Not Adopted: anlamlı olarak daha kötü)

**Ham sonuçlar:** `docs/reports/models/la_liga_pl_parity_ablation.json`. **Yeniden üretim:** `python3 -m src.models.ablate_league_features --competition la_liga --group pl_parity` (yaklaşık 1 dakika).

**Soru.** LaLiga 1X2 modelinin 118 özelliği PL modelinin 74 özelliğiyle aynı değildi: ad düzeyinde 74 PL özelliğinin yalnızca 37'si LaLiga tablosunda vardı, geri kalanının tanımı farklıydı (rakip Elo normalizasyonu ve penaltı arındırma yoktu; venue formları büzülmesizdi; `sdiff_*`, `schedule_*` ve devamlılık özellikleri yoktu). PL'nin özellik koduyla aynı özelliklerin LaLiga'da daha iyi olup olmadığı sınandı.

**Yöntem.** `src/features/build_league_pl_features.py`, LaLiga istatistiklerini PL'nin ham sütun adlarına çevirip PL'nin kendi özellik fonksiyonlarını çalıştırır (kopya değil, aynı kod), PL'nin 74 özellikli 1X2 listesini (`feature_set("1x2")`) üretir. LaLiga'da verisi olmayan 5 sütun çıkarıldı: `log_mv_ratio`, `effective_log_mv_ratio`, `schedule_mv_diff` (geçmiş sezonlar için kadro piyasa değeri yok) ve `sdiff_pa_entries_e02/r10` (ceza sahası giriş sayısı yok; sütunlar sabit değildi ama varsayılan değerin rakip Elo çarpanıyla ölçeklenmesinden doğan, gizli bir Elo özelliğiydi, bu yüzden açıkça çıkarıldı). Kalan 69 özellik, Bölüm 7-8'deki aynı yürüyen protokol, aday ızgarası, eşli bootstrap ve benimseme kuralıyla üretim modeliyle (118 özellik) karşılaştırıldı. İlk 11 özellikleri LaLiga'da sağlayıcının oyuncu rating'inden gelir (PL'nin kendi oyuncu puanı yoktur).

| Sezon | 118 özellik (üretim) | 69 özellik (PL tanımları) | Seçilen aday |
|---|---|---|---|
| 2024/25 | 0.9750 | 1.0360 | `logreg_C0.003` |
| 2025/26 (sınama) | 0.9725 | 0.9733 | `logreg_C0.001` |
| 2026/27 (izleme) | 0.9402 | 0.9459 | `logreg_C0.001` |

Fark (PL tanımları eksi üretim; pozitif PL tanımlarının daha kötü olduğu anlamına gelir): iki dış sezon birlikte +0.0310 [+0.0110, +0.0515], q = 0.0016; sınama sezonu tek başına +0.0009 [-0.0096, +0.0109]. **Karar: benimsenmedi; üretim 1X2 modeli 118 özellikli kaldı.**

**Yorum (kanıtlanmış değil).** Fark yalnızca 2024/25'ten geliyor; o sezonu tahmin eden model yalnızca iki sezonluk (760 maç) geçmişle eğitiliyor. PL'nin tanımları 37 form ve venue sütunu içeriyor ve kayan pencerelerde `min_periods=1` kullanıyor; küçük örneklemde bu sütunlar gürültü ekliyor olabilir. 2025/26'da eğitim 1.140 maça çıkınca fark kayboluyor (+0.0009). Bu bir öğrenme eğrisi açıklamasıdır ve ayrı bir deneyle sınanmadı; yön, daha fazla veriyle PL tanımlarının eşitlenmesi yönündedir, ama bu da kanıtlanmış değildir.

**Sonuç.** Aynı özellik kodunu LaLiga'ya taşımak 1X2 modelini iyileştirmedi, ilk sezonlarda zarar verdi. Sayım modelleri için ise aynı karşılaştırma farklı sonuç verdi ve orada PL tanımları benimsendi (bkz. [la_liga_counts.md](la_liga_counts.md) Bölüm 2). Bu yüzden LaLiga'da iki özellik tablosu vardır: 1X2 ve gol modeli kendi 118 özelliklidir; sayım modelleri PL tanımlıdır.
