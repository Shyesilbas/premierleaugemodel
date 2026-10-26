# Yeni lig hazırlığı: özellik ablasyonu ve LaLiga örnek verisi

**Tarih:** 25 Ekim 2026
**Ham sonuç (tek kaynak):** `docs/reports/experiments/2026-10-25_box_features_ablation.json`
**Kod:** `research/box_features_ablation.py` (PL ablasyonu), `src/ingest/fetch_thestatsapi_league.py` (LaLiga çekimi)

## 1. Soru

Premier League 1X2 modelinin 74 özelliğinden ikisi sağlayıcıya özgüdür: ceza sahası giriş üstünlüğü (`sdiff_pa_entries_e02/r10`, PulseLive `pen_area_entries`) ve rakip ceza sahasında dokunuş (4 özellik, `touches_in_opp_box`). TheStatsAPI'nin verdiği veride ilkinin karşılığı yok, ikincisinin yakın bir karşılığı var (`touches_in_penalty_area`). Yeni bir ligde bu özellikler olmadan model ne kaybeder?

## 2. Yöntem

Üretim tahmincisi (lojistik regresyon, C=0.003) her dış sezon için o sezondan önceki sezonlarla yeniden eğitilir (2022/23 üretimdeki gibi eğitim geçmişinden çıkarılır, ilk dış sezon hariç), kalibrasyon yalnızca geçmişin ileriye dönük OOF tahminlerinden yapılır, dış sezonda puanlanır. Dış sezonlar 2023/24, 2024/25, 2025/26 (1.140 maç); kilitli 2026/27'ye dokunulmaz. Maç bazlı log-loss üzerinde eşli bootstrap (10.000, tohum 42), üç karşılaştırma için Benjamini-Hochberg. Üretim modeli ve dosyaları değiştirilmedi.

## 3. Sonuç (log-loss, düşük daha iyi)

| Varyant | Özellik | 2023/24 | 2024/25 | 2025/26 | Toplu |
|---|---|---|---|---|---|
| Tam model | 74 | 0.9292 | 0.9730 | 1.0174 | 0.9732 |
| Giriş (`pa_entries`) çıkarıldı | 72 | 0.9294 | 0.9736 | 1.0184 | 0.9738 |
| Dokunuş çıkarıldı | 70 | 0.9306 | 0.9711 | 1.0177 | 0.9731 |
| İkisi çıkarıldı | 68 | 0.9312 | 0.9720 | 1.0190 | 0.9740 |

Çıkarmanın farkı (çıkarılmış eksi tam): +0.0006 [-0.0008, 0.0020], -0.0000 [-0.0015, 0.0014], +0.0009 [-0.0017, 0.0035]; hiçbiri anlamlı değil (q = 0.72, 0.95, 0.72). Bu farkları görmek için gereken örneklem on binlerce maç. **İki özellik grubu da modele ölçülebilir katkı vermiyor.** Sonuç yalnızca bu tahminci için geçerlidir: güçlü düzenlileştirme (C=0.003) ve birbiriyle ilişkili özellikler, tek tek katkıyı gizliyor olabilir. Bu bir "model bu özellikleri kullanmıyor" değil, "çıkarınca ölçülebilir kayıp yok" sonucudur.

## 4. LaLiga örnek verisi (TheStatsAPI `comp_8814`, 2026/27, 96 bitmiş maç)

Üç uç noktadan (istatistik, kadro, oyuncu istatistiği) 288 yanıt, hata yok. Kapsam: xG, npxG, isabetli şut, büyük şans, sahip olma, pas ve isabetli pas, ceza sahasında dokunuş, son üçte bir girişi ve ceza sahası içi şut 96/96 maçta dolu. Oyuncu satırı 4.382, 3.017'sinde rating var, hepsinde dakika var.

| Ölçü | LaLiga (TheStatsAPI) | PL (PulseLive, takım-maç ortalaması) |
|---|---|---|
| Ceza sahasında dokunuş | 23.6 | 26.1 |
| Sahip olma | 50.0 | 50.9 |

Dokunuşta yaklaşık %10 fark var; tanım aynı olmayabilir ama ölçek benzer. İki ligin aynı özellik olarak kullanılması gerekmez: yeni lig modeli kendi verisiyle eğitilir.

## 5. Sonuç

PL modelinin 74 özelliğinin 72'si TheStatsAPI verisiyle üretilebilir ya da yakın karşılığı vardır; tek doğrudan eksik olan ceza sahası giriş üstünlüğünün modele katkısı ölçülemeyecek kadar küçük. Yeni lig için sınırlayıcı etken özellik eksikliği değil, kadro/oyuncu rating'i ve piyasa değeri gibi ek kaynakların kurulması ile yeterli maç sayısıdır. Sonraki adım, bir LaLiga modelini aynı sızıntısız protokolle (ayar, sınama, taban Elo ile kıyas) eğitip denemek; bu adım henüz yapılmadı.
