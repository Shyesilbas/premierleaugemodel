# LaLiga Modelleri: Özellik Ailesi Önemi (Permütasyon Denetimi)

**Rapor tarihi:** 26 Ekim 2026 (`v1.0`)
**Kod:** `src/analytics/league_feature_audit.py` · **Ham sonuçlar (tek kaynak):** `docs/reports/models/la_liga_feature_audit.json`
**Yeniden üretim:** `python3 -m src.analytics.league_feature_audit --competition la_liga` (yaklaşık 4 dakika)

## 1. Yöntem

Regresyon katsayıları önem olarak okunmadı (doğrusal modelde ilişkili özellikler büyük katsayı alıp kayba etki etmeyebilir). Özellikler ailelere ayrıldı; bir ailenin tüm sütunları, test maçlarında tek bir ortak satır permütasyonuyla birlikte karıştırıldı (ailenin iç ilişkisi korunur) ve kayıptaki artış önem sayıldı. 30 tekrar, tohum 42. Bir aile, ortalama artış tekrarlar arası yayılımın iki katını aşıyorsa "bilgi taşıyor" kabul edildi.

- **1X2 (118 özellik, üretim modeli):** her dış sezon (2024/25, 2025/26), yalnızca öncesindeki sezonlarla seçilip kalibre edilmiş modelle tahmin edilir (walk-forward protokolüyle aynı); ölçü log-loss artışıdır. Hem kalibre olasılık hem de kalibratörden önceki ham model çıktısı için ayrı ölçüldü (JSON'da `mean_increase` ve `raw_mean_increase`).
- **Sayım modelleri (taç, ofsayt):** seçilen model ilk %80'de yeniden eğitilir, son %20'de (taç 323, ofsayt 312 maç) karıştırılır; ölçü RMSE artışıdır. Üretim dosyasındaki model tüm maçlarla eğitildiği için kullanılmadı (örneklem içi olurdu).

## 2. 1X2: tek tek hiçbir aile ayırt edilemiyor, birlikte çok değerli

| Aile (özellik sayısı) | 2024/25 artış | 2025/26 artış | Her iki sezonda bilgi taşıyor mu |
|---|---|---|---|
| Elo ve güç (7) | +0,0034 | +0,0054 | hayır |
| xG formu (21) | +0,0030 | +0,0087 | hayır |
| Ceza sahasında dokunuş (7) | +0,0132 | +0,0019 | hayır |
| Gol formu (17) | -0,0021 | +0,0038 | hayır |
| Topa sahip olma ve pas (13) | +0,0034 | -0,0060 | hayır |
| Büyük şans (13) | -0,0027 | +0,0013 | hayır |
| Şut (12) | +0,0010 | -0,0016 | hayır |
| İsabetli şut (17) | -0,0014 | +0,0002 | hayır |
| Puan ve averaj (7) | -0,0001 | +0,0023 | hayır |
| Dinlenme ve terfi (4) | +0,0013 | +0,0014 | hayır |
| **Tüm özellikler birlikte (118)** | **+0,2724** | **+0,1783** | evet (yayılım 0,031 ve 0,024) |

- Hiçbir aile iki sezonda da kendi kriterimizi geçmedi. En büyük tekil artışlar: ceza sahasında dokunuş 2024/25'te +0,0132 (yayılımın 1,8 katı) ve xG formu 2025/26'da +0,0087 (1,7 katı). İşaretler sezondan sezona değişiyor (topa sahip olma ve pas +0,0034 sonra -0,0060), yani bu farklar gürültüyle ayırt edilemiyor.
- Tüm özellikler birlikte karıştırıldığında log-loss 0,18-0,27 kötüleşiyor: model özelliklerden gerçekten yararlanıyor, ama bilgi aileler arasında büyük ölçüde yedekli (xG, şut, gol ve Elo aynı takım gücünü farklı yönlerden ölçüyor); bir ailenin kaybı diğerleri tarafından telafi ediliyor.
- Bu, önceki bulgularla tutarlıdır: 22 özellikli küme 118 özellikli kümeden ayırt edilemedi ([la_liga_outcome.md](la_liga_outcome.md) Bölüm 8) ve model Elo'dan ayırt edilemiyor (Bölüm 4). Yorum (kanıtlanmış değil): form özellikleri takım gücünü yeniden ölçüyor ve Elo'nun ötesinde ölçülebilir bilgi eklemiyor.

## 3. Sayım modelleri

| Model | Aile (özellik sayısı) | Holdout RMSE artışı | Yayılım | Bilgi taşıyor mu |
|---|---|---|---|---|
| Taç (holdout RMSE 7,339) | Topa sahip olma ve pas isabeti (4) | +0,458 | 0,089 | evet |
| | Kendi taç geçmişi (3) | +0,241 | 0,059 | evet |
| | Rakibe verilen taç geçmişi (3) | +0,188 | 0,046 | evet |
| | Beklenen taç (iki takımın birleşimi) (2) | +0,143 | 0,043 | evet |
| Ofsayt (holdout RMSE 2,140) | Rakibin yakalandığı ofsayt geçmişi (4) | +0,204 | 0,041 | evet |
| | Kendi ofsayt geçmişi (4) | -0,007 | 0,003 | hayır |
| | Topa sahip olma (2) | +0,014 | 0,012 | hayır |

- **Taç:** dört ailenin dördü de bilgi taşıyor; en büyüğü topa sahip olma ve pas isabeti. Yani modelin gücü takımın oyun tarzından (topa sahip olma, pas oranı) geliyor, yalnızca geçmiş taç sayılarından değil. Bu, "oyun tarzı kalıcıdır" yorumunu destekler ama nedensel kanıt değildir.
- **Ofsayt:** sinyal tamamen "bir takımın ofsayta düşürme geçmişinden" (rakip ofsayt geçmişi: `*_offsides_against_*`) geliyor; takımın kendi ofsayt geçmişi bilgi taşımıyor. Bu, savunma hattı yüksekliği/ofsayt tuzağı gibi bir takım özelliği olabilir; bu bir yorumdur, sınanmadı.

## 4. Sınırlar

- Ham ve kalibre olasılık ayrı ölçüldü ve aileler için sonuç aynı yöndedir (örneğin ceza sahasında dokunuş 2024/25: kalibre +0,0132, ham +0,0150; tümü birlikte: +0,2724 ve +0,2481). Kalibratör nötre yakındır: ham log-loss 2024/25'te 0,9713, kalibre 0,9750 (kalibratör 0,0037 kötüleştirdi); 2025/26'da 0,9722 ve 0,9725. Bu fark ayrıca sınanmadı.
- Yayılım yalnızca permütasyon tekrarlarının değişkenliğidir; örneklemin (380 maçlık sezon) kendi belirsizliğini içermez. Aileler arası küçük farklar (örneğin +0,0132) bu nedenle yine de gürültü olabilir.
- Aile ataması sütun adlarındaki ifadelere dayanır (`outcome_family`); farklar (ör. `diff_xg_for_roll_10`) ait olduğu istatistiğin ailesindedir.
- Sayım modelleri için yalnızca taç ve ofsayt incelendi (kapıyı geçenler).
