# 1X2 İlk 11 Özelliği Pilot Deneyi

**Tarih:** 14 Ekim 2026  
**Tahmin anı:** Resmî ilk 11 yayımlandıktan sonra.  
**Test aralığı:** 2026/27 ilk altı maç haftası.  
**Test fikstürü:** 60 maç.  
**Eğitim:** 1139 maç; yalnız kilitli sezon öncesi, 2022/23 dışlama politikası sabit.  
**İlk 11 kapsaması:** 1579/1580 oynanmış maç; eksik tarihli satırlar bu deneyin eğitiminden çıkarıldı.

## Deney

Aynı `logreg_C0.003` lojistik modeli ve aynı eğitim maçları karşılaştırıldı. Her iki kolun kalibratörü yalnızca eğitim dönemindeki gruplu, genişleyen-zaman OOF tahminlerinde fit edildi. Testte gerçek maçın ilk 11'i kullanıldı; özellikler takımın aynı sezondaki bir önceki maç ilk 11'inden kaç oyuncunun döndüğünü ve ev/deplasman farkını ölçüyor.

Bu, kadro değişimini ölçen bir proxy'dir. Oyuncunun sakat mı, cezalı mı, dinlendiriliyor mu olduğunu tahmin etmez; oyuncu kalitesini de doğrudan ölçmez.

| Ölçüm | Eğitim sınıf prior'ı | Mevcut özellikler | + İlk 11 devamlılığı |
|---|---:|---:|---:|
| Log loss | 1.1062 | 1.0224 | 1.0251 |
| Çok sınıflı Brier | 0.6708 | 0.6099 | 0.6115 |
| Doğruluk | 0.383 | 0.433 | 0.433 |
| Beraberlik Brier | — | 0.2016 | 0.2031 |
| Beraberlik AUC | — | 0.684 | 0.689 |
| En olası sınıfı beraberlik olan maç | — | 4 | 4 |

İlk 11 devamlılığı eklenince eşleştirilmiş test log-loss farkı **+0.0026** oldu (negatif değer daha iyi); maç bazlı bootstrap %95 aralığı **[-0.0047, +0.0099]**, yeni kolun daha iyi olma payı **0.247**. 60 maçlık örnek küçük olduğundan bu tek başına üretim kararına yetmez. Tahminlerde kullanılan ilk 11'lerin maç önü yayım zaman damgası bu yerel arşivde bulunmuyor; deney ilk 11'in başlama saatinden önce bilindiği varsayımına dayanıyor.

## Yorum

"+ ilk 11" sonucu, yalnız bu tarih aralığı ve model seçimi sabitken hesaplandı. Bu pilot dış sakatlık/ceza arşivi, xG verisi veya oran kullanmadı. Model artefaktlarına dokunulmadı.
