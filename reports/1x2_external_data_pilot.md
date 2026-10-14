# 1X2 Harici Veri Pilot Denetimi

**Tarih:** 14 Ekim 2026  
**Kapsam:** 2026/27 ilk altı maç haftası (60 maç); xG, kadro ve eksikler, 1X2 oranları.

## Bulgu özeti

- Proje veritabanında ilk altı haftanın **60 maçı** var. Ham PulseLive maç detayları ve istatistik dosyaları 60/60 maçta mevcut.
- Maç detaylarında **60/60 ilk 11** ile toplam 1.320 ilk 11 ve 1.080 yedek kaydı var. Kadro dışı oyuncuların listesi ve oyuncunun sakat, cezalı veya teknik tercih nedeniyle eksik olduğu bilgisi bu kayıtta yok.
- TheStatsAPI xG'si `external_match_xg` tablosunda kaynak bilgisiyle tutuluyor; yerel proxy sütunlarının üzerine yazılmıyor. Mevcut kapsama 2022/23'te 366/380, 2023/24'te 35/380, 2024/25'te 60/380, 2025/26'da 320/380, 2026/27'de oynanmış 60/60 maçtır. Yazılan tüm satırlarda ev ve deplasman xG birlikte mevcut.
- TheStatsAPI xG ham maç verisi olarak parquet'e ekleniyor ve maç API/UI'sinde gösteriliyor. Bu maçın xG'si maç sonrasında bilindiğinden 1X2 ön-tahmin özelliklerinden lag'li xG sütunlarını çıkardım; model gelecekteki maç xG'sini kullanmıyor. Eski xG özellikleriyle yapılan A/B ölçümü tarihsel keşif olarak kaldı ve üretim modelini temsil etmiyor.
- xG'siz 1X2 modeli yeniden eğitildi. Aynı 304 maçlık ana holdout'ta log-loss **1,028**, Brier **0,620**; sınıf-prior log-loss'u **1,092**. Ham TheStatsAPI xG DB ve gösterim yolunda duruyor; yalnız tahmin girdisi değil.
- xGStat'ın maç haftası sayfaları 2026/27'nin ilk altı haftası için maç başına iki takım xG'sini gösteriyor; örnek: [6. hafta](https://www.xgstat.com/competitions/premier-league/fixtures?gameweek=6). Ancak güncel kullanım koşulları otomatik veri çekmeyi ve platform dışına veri aktarmayı yasaklıyor ([xG Stat kullanım koşulları](https://www.xgstat.com/terms), bölümler 3–4). Bu nedenle sayfadan toplu veri çekmedim veya model girdisi olarak kaydetmedim. Ayrıca xG modeli yerel istatistiklerdeki sağlayıcıyla aynı olmayabilir.
- Football-Data.co.uk, 2026/27 Premier League için sonuç ve oran CSV'si yayımlandığını, sezon sayfasının 12 Ekim'de güncellendiğini belirtiyor ([sezon veri sayfası](https://www.football-data.co.uk/englandm.php)). Bu çalışma ortamından CSV'yi indirme isteği zaman aşımına uğradı; web okuyucusu da CSV içerik türünü açamıyor. Footiqo'nun erişilebilen sayfası 1xBet kapanış oranlarını gösteriyor, ancak tarayıcı görünümünde yalnız ilk 25 maç satırı geldi ([Footiqo oran tablosu](https://footiqo.com/database/leagues/england-premier-league/)). 60 maçın tamamı için oran tablosu bu denemede yerel dosyaya aktarılamadı.

## İlk altı haftayı neden doğrudan test holdout'u olarak kullanamıyoruz?

Maç öncesi tahmin günlüğünde ilk altı haftanın tahminleri bulunmuyor; günlük şu anda ileri fikstür tahminlerini içeriyor. Git'teki mevcut üretim artefaktının meta verisi de 1.200 eğitim satırını gösteriyor; bu sayı ilk altı haftadaki 60 maçı içeriyor. Bu artefaktı ilk altı hafta üzerinde puanlamak hedef sonuçların eğitime girmiş olması nedeniyle sızıntılı olur.

İlk altı haftayı kullanmak için sezon öncesi veriyle yeniden eğitilmiş, yalnız 2025/26 ve daha eski maçları gören bir temel model gerekir. Ardından xG ve kadro bilgileri aynı 60 maçta bir kez sınanabilir. 60 maç küçük bir örnek olduğundan sonuç keşif amaçlı olmalı; özellik ve model seçimini bu haftalara göre yapmamalıyız.

## Kadro, sakatlık ve ceza bilgisinin sınırı

Maç detayları resmî ilk 11'i ve yedekleri içeriyor; bu, ilk 11 açıklandıktan sonraki tahmin senaryosunu test etmek için kullanılabilir. Fakat kayıtlar maç öncesi yayın zamanını veya kadroda olmayan oyuncuların nedenini tutmuyor. Sakatlık etkisini geriye dönük test etmek için her maçtan önceki tarihli sakatlık/ceza anlık görüntüleri gerekir. Bu olmadan “oynamadı” bilgisini sakatlık diye etiketlemek doğru olmaz.

## Sonraki geçerli deney

1. API hız sınırına uyarak xG tarihçesini ve 2026/27 odds verisini tamamla; oddsları tahmin öncesi piyasa benchmark'ı olarak tut.
2. Oddsları modele girdi yapmadan, marjdan arındırılmış H/D/A olasılıklarını ayrı piyasa benchmark'ı olarak karşılaştır.
3. İleride maç öncesi xG tahmini sağlayan bir kaynağa erişilirse bunu gerçekleşmiş maç xG'sinden ayrı bir özellik olarak ileri-zamanlı benchmark et.
4. Kadro etkisini ayrı bir “ilk 11 açıklandıktan sonra” modeli olarak sınayacak şekilde tasarla. Tarihli sakatlık/ceza arşivi bulunana kadar bu modeli sakatlık nedeni tahmini diye adlandırma.
5. 2026/27'nin kalan tahminlerini tahmin anı, model özeti ve veri kaynaklarıyla maç başlamadan arşivle; böylece gerçekten bağımsız ileriye dönük ölçüm oluşur.

**Güncelleme (14 Ekim 2026):** TheStatsAPI xG uçtan uca bağlandı; 2024/25'e 60, 2025/26'ya 320 kayıt eklendi. Ham xG DB, parquet maç satırları ve maç detayı/API'de kalıyor. Lag'li xG form feature'ları ön-tahmin modelinden ve feature datasetinden kaldırıldı; 1X2 artefaktı xG'siz yeniden üretildi. Oddsların tarihsel çekimi bu pilot kapsamında tamamlanmadı.
