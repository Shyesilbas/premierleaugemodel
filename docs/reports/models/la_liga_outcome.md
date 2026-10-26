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
- Dışarıda bırakılanlar: kadro piyasa değerleri (sağlayıcı yalnızca bugünkü kadroyu verir, geçmiş sezonlara uygulamak gelecek bilgisini sızdırır), ceza sahası giriş sayısı (kaynakta yok; PL modelinde de katkısı ölçülebilir değildi), ilk 11 derecelendirmesi ve devamlılığı (henüz yazılmadı).

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

| Ölçü | Model | Taban / eğitim ortalaması |
|---|---|---|
| Toplam gol MAE | 1.2274 | 1.2537 |
| Alt/üst 1.5 log-loss | 0.5512 | 0.563 |
| Alt/üst 2.5 log-loss | 0.6766 | 0.694 |
| Alt/üst 3.5 log-loss | 0.5483 | 0.5595 |
| Karşılıklı gol log-loss | 0.6879 | 0.6917 |

Bağımsız Poisson oranları, Dixon-Coles matrisi (rho = -0.04) kalibre edilmiş 1X2'ye hizalanır; böylece tüm pazarlar tek dağılımdan çıkar. İyileşmeler küçüktür; anlamlılık testi yapılmadı. Korner, kart, taç, kurtarış, şut ve ofsayt için model yoktur; arayüzde lig koşan ortalamaları `baseline` etiketiyle gösterilir.

## 6. Bilinen sınırlar

- Seçilen düzenlileştirme (C = 0.001) adayların en güçlüsü; yani ızgara kenarında. Daha güçlü düzenlileştirmenin daha iyi olup olmadığına bakılmadı. Özellik sayısı (118) örneklem için fazla; özellik azaltma denemesi dış sezonlara bakmadan, yeni bir protokolle yapılmalı.
- Elo'dan üstünlük kanıtlanamadığı için model, Elo'ya yakın bir yetenektedir; piyasa ise anlamlı derecede daha iyi.
- İlk 11 ve oyuncu rating özellikleri, ceza sahası giriş sayısı ve piyasa değeri yoktur. Maç başlamadan önce resmi ilk 11 kullanılmaz.
- Üretim dosyası oynanmış tüm maçlarla (kilitli sezonun oynanmış 97 maçı dahil) eğitildi; seçimler yalnızca kilitsiz sezonlarla yapıldı. Takvimden gelen yer tutucu maçların tarihleri değişebilir; saatleri belli değildir.
- Model doğrulama sayfası yalnızca dış sezonları (2024/25, 2025/26) ve izleme sezonunu gösterir; 2022/23-2023/24 eğitim verisidir, bağımsız tahmin yoktur. Oynanmamış maç tahminleri sayfada yoktur, maç sayfasında vardır.
