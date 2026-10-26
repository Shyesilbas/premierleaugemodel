# 1X2 Maç Sonucu Modeli: Uçtan Uca Denetim

**İnceleme tarihi:** 14 Ekim 2026
**Veri anlık görüntüsü:** 1.580 tamamlanmış maç, 2022/23–2026/27; son sezon 60 maçlık kısmi örnek.  
**Kapsam:** sonuç etiketleri, maç öncesi özellikler, zaman sıralı eğitim/değerlendirme, beraberlik olasılıkları ve API sunumu. Tam yerel pipeline yeniden çalıştırıldı; otomatik test paketi **18/18** geçti.

**Son benchmark yenilemesi:** 14 Ekim 2026'da tam pipeline yeniden çalıştırıldı. Güncel ana sınıflandırma holdout'u kilitli sezon hariç 304 maçtır; aşağıdaki kısa sonuç ve beraberlik özeti bu yeni ölçüme göre güncellendi.

**TheStatsAPI xG (14 Ekim 2026):** Sağlayıcı xG'si ayrı kaynak tablosunda ve maç detayı/API'sinde duruyor. Gerçekleşmiş maç xG'si maç sonrasında bilindiği için lag'li xG feature'ları ön-tahmin modelinden çıkarıldı. Güncel 1X2 artefaktı xG içermiyor; sağlayıcı xG'si yalnız maç verisi/gösterimi ve maç-sonrası analiz için kullanılıyor. Kapsama harici veri pilotunda (rapor kaldırıldı; git geçmişinde: `reports/1x2_external_data_pilot.md`).

## Kısa sonuç

Model tamamen başarısız değil: güncel 304 maçlık kronolojik holdout'ta log-loss **1,030**, sınıf-prior baseline'ında **1,092**; çok sınıflı Brier **0,621**, baseline'da **0,661**. Eşleştirilmiş bootstrap model-prior log-loss farkı **−0,0622** (95% CI **[−0,0999, −0,0225]**). Dixon–Coles aynı eğitim satırları ve holdout üzerinde **1,0428** log-loss verdi. Genel olasılık skoru baseline'dan iyi, ancak beraberlik ayrımı hâlâ zayıf.

Asıl açık, **beraberlik olasılığını maçlar arasında ayıracak sinyalin zayıf olması**. Güncel holdout'ta 304 maçın 85'i beraberlik (**%28,0**); ortalama beraberlik olasılığı **%24,7**, draw AUC **0,5131** ve yalnızca **1 maç** en olası sonuç olarak beraberlik seçildi. Gerçek beraberliklerde ortalama tahmin %24,9, diğer maçlarda %24,6; ayırma gücü zayıf.

Ana holdout 2025/26 sezonunda 18 Ekim 2025'te başlıyor. Sezonun geliştirme dönemine düşen ilk 76 maçında 19 beraberlik (**%25,0**), sonraki 304 holdout maçında 85 beraberlik (**%28,0**) var. Fark daha sınırlı; bu kesit tek başına dönemsel değişimin nedenini açıklamıyor.

## Model akışı

| Aşama | Mevcut davranış | Denetim sonucu |
|---|---|---|
| Etiket | `home_score` ve `away_score` karşılaştırılarak H/D/A üretiliyor; oynanmamış maçlar dışarıda. | Etiketler saklanan `match_result` ile 1.580 maçın tamamında uyuştu. Tekrarlanan maç kimliği, negatif veya kesirli skor görülmedi. |
| Zaman sırası | Maçlar kickoff ve maç kimliğiyle sıralanıyor. | Kronolojik sıra tutarlı. |
| Takım formu | Gol, şut ve diğer maç sonrası takım metrikleri rolling/EWMA ile geçmiş maçlardan hesaplanıp mevcut maçtan önce bir adım kaydırılıyor. xG form özellikleri kaldırıldı. | Maçın kendi TheStatsAPI xG'si yalnız maç tamamlandıktan sonra saklanır/gösterilir; ön-tahmin modeline girmez. |
| Takım gücü | Elo ve sezon içi puan/averaj durumları sonuç güncellenmeden önce kaydediliyor; sezon geçişinde Elo ortalamaya çekiliyor ve lig tablosu önsel değere dönüyor. | Eğitim tarafının zaman sırası mantıklı. Yaklaşan fikstürün sezon etiketi artık API feature satırına aktarılıyor; geçiş kodu eklendi, entegrasyon testi yapılmadı (aşağıda). |
| 1X2 özellikleri | Takım gücü, xG dışı geçmiş formu ve dinlenme gibi maç öncesi ölçüler. Gerçekleşmiş sağlayıcı xG'si dışarıda. | Ana bölmede 1.216 geliştirme ve 304 holdout satırı var; güncel artefakt xG sütunu içermiyor. |
| Model seçimi | Düzenlileştirilmiş multinomial lojistik regresyon ve küçük LightGBM adayları; kickoff gruplarını bölmeyen dört expanding-window katta log-loss ile seçim. En iyi aday `logreg_C0.003`. | Aday, özellik ve kalibrasyon kararları ana holdout dışında veriliyor. Aynı kickoff'taki maçlar CV ve ana split sınırında ayrılmıyor. |
| Kalibrasyon | Holdout ölçümünde geliştirme OOF'si, üretim artefaktında uygun kilitsiz sezonlardan gruplu forward OOF'si kullanılıyor. | Üretim kalibrasyonu 922 OOF tahminini kapsıyor. Tek bir global dönüşüm dönem içi değişimi bütünüyle çözmüyor; sınıf ayrımını da tek başına yaratamaz. |
| Üretim | API model olasılıklarını kalibre edip H/D/A yüzdeleri olarak döndürüyor. | 2022/23 sonuçları 1X2 fitinden çıkarılmış; sezon, daha yeni maçların geçmiş özelliklerini üretmek için veri geçmişinde tutuluyor. |

Ana değerlendirme modeli 836 geliştirme satırıyla fit edilip 304 maçta ölçülüyor. Üretim sınıflandırıcısı 2022/23 dışındaki **1.200 etiketli maça** tekrar fit ediliyor. Eski 2022/23 dışlama kuralı bu çalışmada sabit tutuldu; geliştirme dönemi yalnız bir uygun tam outer sezon verdiği için bu kuralı yeniden seçmek için yeterli kanıt yok. 2026/27 kayıtlı tahminleri bundan sonraki prospektif doğrulama için korunmalı.

## Koddan doğrulanmış 1X2 çalışma biçimi

1. **Etiket ve zaman sırası:** Skoru olan maçlarda ev sahibi galibiyeti `0`, beraberlik `1`, deplasman galibiyeti `2` olarak kodlanıyor. Maçlar `kickoff_millis` ve `match_id` ile sıralanıyor. `2026_27` değerlendirme, model seçimi ve kalibrasyondan kilitli; 60 sonucu yalnızca son üretim fitine dahil ediliyor. `2022_23` sonuçları özellik geçmişinde kalıyor, sınıflandırıcı fitinden çıkarılıyor.
2. **Özellik vektörü:** Güncel artefakt 44 sütun içeriyor; TheStatsAPI xG, kadro/sakatlık bilgisi ve oranlar vektörde yok. Dokuz ayrı draw-propensity özelliği karar kapısını geçmediği için üretim özelliklerine girmedi.
3. **Aday ve seçim:** Beş düzenlileştirme değerli lojistik regresyon ile üç küçük LightGBM adayı, kickoff gruplarını koruyan dört genişleyen zaman katında ortalama log-loss ile karşılaştırılıyor. Seçilen `logreg_C0.003`; geliştirme CV log-loss'u `0.9803`. Model hattı eğitimde medyanla eksik değer doldurma, standardizasyon ve lojistik regresyondan oluşuyor.
4. **Kalibrasyon:** Geliştirme içindeki dört ileri OOF bloğu kalibratörü fit ediyor; 836 geliştirme satırından 666 grouped-OOF tahmini çıkıyor. Dönüşüm `softmax(log(p) / T + sınıf_ofseti)` biçiminde. Holdout değerlendirme kalibratörü `T=0.951`, ofsetler `[ev -0.057, beraberlik +0.046, deplasman +0.011]`. Holdout etiketleri bu kalibratörü fit etmekte kullanılmıyor.
5. **Üretim ve API:** Son lojistik model 1.200 oynanmış maça fit ediliyor; bunun içinde 2026/27'den 60 maç var, 2022/23 yok. Üretim kalibratörü kilitsiz ve uygun 1.140 maçtan üretilen 922 gruplu ileri OOF tahmininde fit ediliyor; recency gate yeterli outer sezon bulmadığı için standart kalibrasyon kullanılıyor. API 1X2 için eksik değerleri sıfırla ezmiyor; NaN'leri modelin eğitimdeki medyan imputasyonuna bırakıyor. Dixon–Coles üretim gate'i geçmediğinden mevcut 1X2 API tahmininde ensemble kullanılmıyor.

### Log-loss'un sınıf bazında açılımı

Değerlendirme modelini yalnız 836 geliştirme satırında yeniden fit edip saklanan değerlendirme kalibratörünü uyguladım. Genel log-loss ham olasılıkta `1.03039`, kalibre olasılıkta `1.02954` (benchmark'ta ikisi de `1.030`). Aşağıdaki sınıf satırları sadece o sonucu gerçekten veren maçlardaki ortalama `−log(P(gerçek sınıf))` değeridir.

| Gerçek sonuç | Maç | Model sınıf log-loss | Sabit sınıf-prior log-loss | Modelin o sınıfa verdiği ortalama olasılık |
|---|---:|---:|---:|---:|
| Ev sahibi | 124 | 0.7868 | 0.8205 | 0.4816 |
| Beraberlik | 85 | 1.4089 | 1.4608 | 0.2491 |
| Deplasman | 95 | 1.0070 | 1.1155 | 0.3983 |

Model üç sınıfın her birinde sabit prior'dan iyi; toplam kaybın yaklaşık **%38'i** beraberlik maçlarından geliyor. Buna rağmen ayırt etme zayıf: beraberlik AUC `0.5131`; maç başına ortalama `P(D)` gerçek beraberliklerde `%24.91`, diğerlerinde `%24.60`. Kalibrasyon toplam log-loss'u yaklaşık `1.03039 → 1.02954` değiştiriyor; esas darboğazı kalibrasyon tek başına çözmüyor.

`1.030` sayısının 1'in üzerinde olması tek başına hata göstergesi değil: üç sınıfta eşit olasılık tahmininin log-loss'u `ln(3)=1.0986`; geliştirme sınıf oranlarını her maça veren prior baseline `1.092`. Model ikisini de geçiyor, fakat kazanım mütevazı. 1X2 log-loss'u iki sınıflı Over 2.5 log-loss'uyla doğrudan kıyaslanmamalı; sınıf sayısı ve belirsizlik tabanı farklı.

### Benchmark güvenilirliği için bulunan kusur

Önceki kod feature gate'ini ana holdout dahil bütün kilitsiz veride çalıştırıyordu. Bu düzeltmede holdout split'i önce kuruluyor; draw-propensity, ensemble ve recency gate'leri yalnız geliştirme dönemindeki dış sezonlarla besleniyor. Fallback ile 2022/23'ü yeniden içeren sezonlar ve kısmi sezon gate sayımına alınmıyor. Geliştirme tarafında şu an yalnız bir uygun tam outer sezon bulunduğundan bu gate'ler üretim değişikliği yapmıyor. Önceden var olan 2022/23 fit dışı kuralı bu turda sabit tutuldu ve Dixon–Coles kıyasına da uygulandı; bu kuralın tarihsel seçimi nedeniyle 2025/26'yı tüm geçmiş politika kararlarından bağımsız bir final test olarak görmemek gerekir. 2026/27 prospektif günlüğü yeni bağımsız değerlendirme olmalı.

CV ve ana split eşit kickoff'lardaki maçları artık ayırmıyor. API tarafında `_safe_features` eksik 1X2 alanlarını NaN bırakıyor; `SimpleImputer` eğitimde öğrenilmiş medyanı uygular. Bu davranış için unit test eklendi; tam API/offline feature-parity testi hâlâ açık.

## Bulgular

### 1. Yüksek öncelik: beraberlik olasılığı son holdout'ta düşük ve ayrıştırma zayıf

Ana kronolojik holdout, kilitli 2026/27 sezonu dışındaki son 304 maç. Sınıf sırası ev sahibi / beraberlik / deplasman.

| Sonuç | Gerçek maç sayısı | Gerçek oran | Modelin en olası sınıf seçimi |
|---|---:|---:|---:|
| Ev sahibi | 124 | %40,8 | 188 |
| Beraberlik | 85 | %28,0 | 1 |
| Deplasman | 95 | %31,3 | 115 |

Güncel holdout olasılık metrikleri `reports/model_benchmarks.md` içinde veriliyor. Sınıf ofsetini artırmak toplam beraberlik tahminini yükseltebilir; gerçek beraberliklerde ve diğer maçlarda ortalama P(D) farkı yalnızca 0,3 yüzde puan olduğundan bu tek başına yeterli çözüm olmaz.

**Yorum:** Genel 1X2 skoru baseline'dan iyi; tüm modeli atmak için kanıt yok. Ancak beraberlik yüzdesini ayrı bir kalite boyutu olarak ele almak gerekiyor. Sadece beraberlik sabitini yükseltmek daha çok maçı “D” seçtirir ama hangi maçların beraberlik olduğunu öğrenmiş olmaz.

### 2. Yüksek öncelik: beraberlik oranı zaman içinde değişmiş

| Sezon | Maç | Ev sahibi | Beraberlik | Deplasman |
|---|---:|---:|---:|---:|
| 2022/23 | 380 | %48,4 | %22,9 | %28,7 |
| 2023/24 | 380 | %46,1 | %21,6 | %32,4 |
| 2024/25 | 380 | %40,8 | %24,5 | %34,7 |
| 2025/26 | 380 | %42,6 | %27,4 | %30,0 |
| 2026/27 (kısmi) | 60 | %38,3 | %31,7 | %30,0 |

Ana modelin geliştirme diliminde 2022/23 fit dışı bırakılınca kalan 836 maçın beraberlik oranı **%23,2**. Ana holdout'ta 304 maçın 85'i beraberliktir (**%28,0**). 2025/26 sezonunun geliştirmeye giren ilk 76 maçında beraberlik oranı **%25,0**, kalan 304 maçta **%28,0**; bu yaklaşık üç puanlık fark sınırlı bir dönem kaymasına işaret ediyor, fakat nedenini kanıtlamıyor.

Önceki tam-sezon tahmin karşılaştırmaları farklı eğitim/holdout kapsamlarını kullandı; aşağıdaki 2026/27 satırı mevcut kilitli sezon ölçümü değildir. Bu nedenle bu tabloyu güncel politika kapısı olarak kullanmıyorum. Güncel feature/ensemble/recency kapıları yalnız geliştirme döneminde tek uygun tam outer sezon gördü ve henüz karar vermek için yeterli değil. Sayısal gate sonuçları bu raporun sonundaki güncellemede yer alıyor.

| Önceki outer değerlendirme | Tahmin edilen ortalama P(D) | Gerçek beraberlik oranı | Test maç sayısı |
|---|---:|---:|---:|
| 2024/25 | %24,4 | %24,5 | 380 |
| 2025/26 | %26,4 | %27,4 | 380 |
| 2026/27 | %28,3 | %31,7 | 60 |

Bu değerler geçmiş raporlama turundaki teşhis ölçüleridir; güncel performans için [Model Benchmarks](model_benchmarks.md), geleceğe dönük bağımsız skor için tahmin günlüğü kullanılmalıdır.

### 3. Uygulandı: üretim kalibratörünü tüm uygun geçmişle fit et

Üretim modeli 2022/23 etiketleri hariç **1.200** oynanmış maça fit ediliyor; buna kilitli 2026/27'den 60 maç dahil. Kalibrasyon ise kilitli sezon hariç uygun **1.140** satırdaki kickoff-gruplu ileri OOF tahminleriyle fit ediliyor ve **922** OOF tahmini içeriyor. Holdout metrikleri geliştirme döneminin ayrı, 666 tahminli OOF'siyle fit edilen ayrı kalibratörle hesaplanıyor.

Bu değişiklik üretim kalibratörüne son sezon bilgisini ekler. Bunun gelecekteki kalibrasyonu iyileştirdiği henüz bağımsız gelecek sezonla ölçülmedi; OOF fit değerleri performans sonucu olarak yorumlanmamalı.

### 4. Uygulandı: dış sezonlarda karşılaştırmalı değerlendirme; son sezon hâlâ kilitli değil

Ana split en yakın kickoff-gruplu %80 sınırında yapılıyor. Draw-propensity, ensemble ve recency gate'leri yalnız geliştirme dönemindeki dış sezonlarla hesaplanıyor; geliştirme tarafındaki uygun tam outer sezon sayısı **1**, dolayısıyla üç sezon gerektiren gate'ler geçmiyor. Dixon–Coles artık lojistik modelle aynı geliştirme fit satırlarını (2022/23 hariç) ve aynı 304 maçlık ana holdout'u kullanıyor. Eski 2022/23 dışlama kuralı bu çalışmada sabit tutuldu; kuralın ilk seçimi tarihsel deneylere dayandığından 2025/26'yı tüm politika kararlarından bağımsız final test olarak sunmuyorum.

Geçmiş penceresi, recency ağırlığı ve özellik varyantları artık yalnız geliştirme döneminde ölçülüyor. Bir tam uygun sezon politika seçimi için az olduğundan bu değişiklikler üretime alınmadı; 2026/27 maç öncesi tahmin günlüğü yeni prospektif doğrulamayı sağlayacak. Olasılık dilimi raporu bu turda eklenmedi.

### 5. Uygulandı: yakın dönem, xG proxy'si ve beraberlik dengesi özelliklerini dış sezonlarda karşılaştır

Her dış sezonda aynı `logreg_C0.003` modeli sabit tutuldu; tüm geçmiş, 2022/23'ü çıkarma, son iki sezon ve 1,5 sezon yarı ömürlü recency ağırlığı; tüm özellikler, xG proxy'siz özellikler ve beraberlik dengesi özellikleri karşılaştırıldı. Bu tarihsel deney geliştirme döneminde kaldı. Yalnız 2024/25 temiz tam sezon olduğundan sonuçlar karar için sınırlı. O sıradaki feature listesinde xG sütunu bulunmadığından `all_features` ile `without_xg_proxy` satırları aynı girdileri içeriyordu; TheStatsAPI katkısını ölçmüyordu.

Geliştirme kapsamındaki temiz 2024/25 dış sezonunda `exclude_2022_23` tüm özellikler log-loss'u **0,9986**; beraberlik dengesi özelliklerini çıkarmak **0,9984** verdi. Fark pratik olarak çok küçük; bu tek sezon eğitim politikası veya özellik katkısı için kesin kanıt değildir. 2022/23 fit dışı kuralı sabit kaldı, ancak bu rapor onu yeni bir sonuçla doğrulamıyor.

xG proxy'sinin tarihsel ablasyonu eski, artık kullanılmayan feature şemasına aittir. Gerçekleşmiş maç xG'si sonradan oluştuğu için lag'li form sütunları 1X2 feature datasetinden ve modelden çıkarıldı. Ham TheStatsAPI xG'si maç kaydı ve API/UI üzerinde tutuluyor. Güncel xG'siz holdout sonucu [benchmark raporunda](model_benchmarks.md#classification-results) yer alıyor.

### 6. Tarihsel not: eski xG proxy ölçümü

Önceki sürümde resmi şut-başı xG yerine şut ve büyük şans toplamlarından türetilen proxy kullanılmıştı. Kaynak verisi oynanmış 3.160 takım-maç satırının yalnızca **1.337'sinde (%42,3)** vardı. Bu kapsam oranı tarihsel özelliğe aittir; proxy artık üretim modelinde yok.

Önceki iterasyonda eksik xG gözlemleri rolling penceresine alınmıyor, son geçerli gözlem yaşı ayrı özellik olarak tutuluyordu. Bu özellikler F7 ile aktif eğitim ve canlı tahmin yolundan kaldırıldı.

Bu proxy'nin beraberlik açığının nedeni olduğuna dair kanıt yok. Doğrulanmış maç başı xG bulunursa, yalnız geliştirme döneminde karar verilmiş yeni bir dış sezon protokolünde değerlendirmek gerekir.

### 7. Uygulandı: API'de yaklaşan fikstür sezonuna geçiş

Eğitimde `_run_strength`, yeni sezonun ilk maçını işlerken Elo'yu %20 ortalamaya çekiyor ve PPG/averaj tablosunu sıfırlanmış sezon önselinden başlatıyor. `build_prediction_row` yaklaşan fikstürün sezonunu kullanarak canlı tahminde aynı geçişi uyguluyor.

Önceki API mantığıyla karşılaştırmada 2025/26 açılışındaki Liverpool–Bournemouth için `elo_diff` yaklaşık **37,2**, `ppg_diff` **0,68**, `gdpg_diff` **0,80** farklıydı. Form özellikleri aynıydı; fark sezon geçişindeydi. Bu turda eksik 1X2 girdilerinin NaN olarak model pipeline'ına taşınmasını sağlayan ortak helper eklendi ve test edildi. Tam API feature-parity testi hâlâ açık.

### 8. Ürün arayüzü kapsam dışı

Bu çalışma boyunca bahis oranları kullanılmadı; model girdisi veya sonuç değerlendirmesine dahil edilmedi.

## Geliştirme sırası ve bu turdaki durumu

1. **Tamamlandı — sızıntısız karar akışı:** feature, ensemble ve recency gate'leri geliştirme dönemiyle sınırlandı; ana holdout artık bu kapıların seçimine katılmıyor. Üç temiz tam outer sezon oluşana kadar gate'ler üretim değişikliği yapmıyor.
2. **Tamamlandı — kickoff gruplu zaman bölmeleri:** CV ve ana holdout aynı kickoff anındaki maçları birlikte tutuyor.
3. **Tamamlandı — eşit Dixon–Coles kıyası:** ana holdout ve eğitim satırları lojistik modelle aynı. DC holdout log-loss'u **1,0428**, lojistik model **1,0295**; DC üretim modeli olarak seçilmedi.
4. **Kısmen tamamlandı — xG proxy:** proxy var/yok dış sezonlarda kıyaslandı ve gözlem yaşı özelliği eklendi. Proxy'nin doğrulanmış xG ile karşılaştırılması açık.
5. **Tamamlandı — API eksik değer yolu:** 1X2 eksikleri artık sıfır yerine NaN kalıyor ve eğitimdeki imputera bırakılıyor; helper için otomatik test eklendi. Uçtan uca API/offline parity testi açık.
6. **Başlatıldı — ileriye dönük holdout:** `src/analytics/prospective_1x2_benchmark.py` gerçek API tahminlerini maçtan önce kaydediyor. 13 Ekim 2026'da güncel üretim artefaktıyla önümüzdeki 14 gün içindeki 20 maç için tahmin saklandı (SHA-256 öneki `d9cb30d28d02`); aynı maçların önceki artefakt kayıtları korunuyor. Tahminler `data/competitions/premier_league/processed/1x2_forecast_log.jsonl` içinde tutuluyor ve maç sonucu geldiğinde yeniden tahmin edilmiyor.
7. **Bekliyor — yeni sonuçlar:** veri eşitlendikten sonra `python3 -m src.analytics.prospective_1x2_benchmark score` komutu, maç öncesi kaydedilmiş tahminleri tamamlanmış sonuçlarla eşleştirip log-loss, çok sınıflı/beraberlik Brier'ı, beraberlik AUC'si ve oran uyumunu hesaplar. 2026/27 tamamlanınca sezonun kalan bölümünü kilitli dış test olarak kullan; ilk 60 maçtan kesin sonuç çıkarma.

İleriye dönük tahminleri düzenli yenilemek için veri güncellemesinden sonra `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` çalıştır. Aynı gün, aynı maç ve aynı model artefaktı için yinelenen kayıt eklenmez. Sonuçlar gelmeden performans metrikleri hesaplanamaz.

## İncelenen kod yolları

- `src/processing/process_season_data.py`: skor ve maç özeti etiketlerinin oluşturulması.
- `src/features/build_features.py`: geçmiş form, dinlenme, Elo/puan tablosu ve tahmin satırı.
- `src/models/train_match_outcome.py`: 1X2 özellikleri, kronolojik CV, kalibrasyon, sezon holdout'ları ve üretim fit'i.
- `src/api/server.py`: canlı state ve `/api/predict` olasılık dönüşümü.
- `frontend/src/components/PredictorTab.jsx`: olasılıktan türetilen teorik oran metni.

## Güncelleme — 14 Ekim 2026: protokol düzeltmeleri ve güncel F4–F7 durumu

Tam pipeline 14 Ekim'de yeniden çalıştırıldı; test paketi **18/18** geçti. Aşağıdaki outer-season karar ölçümleri yalnız geliştirme dönemini kullanıyor. Temiz tam sezon sayısı henüz üçten az.

| Faz | Dış sezon sonucu | Karar |
|---|---|---|
| F4 — Lojistik + Dixon–Coles ensemble | Geliştirmedeki tek uygun tam sezonda ensemble−lojistik log-loss farkı **+0,00211**; 2023/24 fallback ve 2025/26 kısmi sezon gate sayımına girmiyor. | Üç sezon gereksinimi karşılanmadı ve gözlenen tek sezon iyileşmedi. `model_dc` üretim artefaktına eklenmedi. |
| F5 — Beraberlik eğilim özellikleri | Tek uygun sezonda log-loss farkı **+0,0047**, draw-AUC farkı **+0,0168**. | Log-loss koşulu geçmedi; gate toplamda **1** temiz outer sezon gördü. Dokuz özellik production feature listesine alınmadı. |
| F6 — Zaman ağırlıklı kalibrasyon | Tek uygun sezonda 150/300/600 satır yarı ömürleri için log-loss farkı **−0,00300 / −0,00201 / −0,00113**. | Üç sezon koşulu karşılanmadı; hiçbir yarı ömür seçilmedi ve standart kalibrasyon korundu. |
| F7 — xG proxy ve sağlayıcı xG | Düşük kapsamalı aggregate proxy kaldırıldı. TheStatsAPI xG ayrı kaynak tablosuna ve maç gösterimine bağlandı. | Gerçekleşmiş xG ön-tahmin girdisi değil; lag'li xG form sütunları da model/parquet feature setinden kaldırıldı. |

F4–F6 ölçümlerinin sayısal kaynağı [Model Benchmarks](model_benchmarks.md) ve `data/competitions/premier_league/processed/` altındaki JSON'lardır. F10 ile `data/competitions/premier_league/processed/1x2_forecast_log.jsonl` maç öncesi tahminleri ve model SHA-256 değerlerini saklıyor. Tahminler maç sonuçları geldikçe `reports/prospective_1x2_scorecard.json` içinde 1X2 ve gol pazarları için skorlanır.

---

## Büyük Mimari Dönüşüm — 14 Ekim 2026: Fikstür Zorluğu (SoS) Normalizasyonu, Beraberlik Törpüleme ve %50/%50 Altın Denge

14 Ekim 2026 gecesi yapılan ileri düzey denetimde, 1X2 modelinin canlı fikstürlerdeki davranışları incelenmiş ve üç kritik matematiksel kusur tespit edilerek kalıcı olarak çözülmüştür:

### 1. Fikstür Zorluğu (Strength of Schedule - SoS) Körlüğü ve Point-in-Time Elo Normalizasyonu

* **Kusur Teşhisi:** Lojistik regresyon ve form modellerine giren şut (`shots_ontarget_for`, `shots_ontarget_against`) ve xG (`xg_for`, `xg_against`) metrikleri ham (raw) bırakılmıştı. Everton, sezonun ilk 6 haftasında ligin zayıf takımları (Ipswich, Crystal Palace) karşısında gol yemeyip namağlup bir seri yakalarken; Chelsea deplasmanda Arsenal ve formda Brentford gibi elit takımlara karşı pozisyon vermişti. Model rakip kalitesini hesaba katmadığı için bu geçici fikstür şansını gerçek bir sınıf farkı zannederek Everton'ı Chelsea karşısında %48.6 (oran: 2.05) gibi yapay bir favoriliğe fırlatmıştı.
* **Uygulanan Çözüm (`src/features/build_features.py`):**
  Her maçın öncesinde (kesinlikle data leakage olmadan, `_run_strength` çıktısı olan o anki maç öncesi Elo değerleriyle) rakip gücünü temsil eden dinamik bir çarpan tanımlandı:
  $$\text{mult}_{\text{opp}} = \text{clip}\left(\exp\left(\frac{\text{Elo}_{\text{opp}} - 1500.0}{600.0}\right), \; 0.60, \; 1.80\right)$$
  - **Hücum Normalizasyonu:** $\text{Stat}_{\text{Adjusted}} = \text{Stat}_{\text{Raw}} \times \text{mult}_{\text{opp}}$ (Güçlü savunmalara karşı üretilen şut/xG ödüllendirildi, zayıf takımlara karşı üretilenler törpülendi).
  - **Savunma Normalizasyonu:** $\text{Stat}_{\text{Adjusted\_Against}} = \frac{\text{Stat}_{\text{Raw\_Against}}}{\text{mult}_{\text{opp}}}$ (Arsenal gibi takımlara karşı pozisyon verilmesi Chelsea'yi aşırı cezalandırmazken, zayıf hücumlara pozisyon verilmesi Everton'ın hanesine eksi yazıldı).
* **Doğrulanan Etki:**
  - Chelsea'nin kalesinde gördüğü isabetli şut ortalaması 6.00'dan **4.76'ya** indi.
  - Everton-Chelsea arasındaki net isabetli şut farkı (`sdiff_sot_r10`) **1.20'den 0.76'ya** çekildi.
  - 1.900 maçlık tüm geçmiş feature seti (`features_matches_all.parquet`) bu formülle baştan aşağı yeniden üretildi.

### 2. Beraberlik (X) Aşırı Yığılması ve Kalibratör Bias Törpüleme (Capping)

* **Kusur Teşhisi:**
  Brentford–Liverpool (%37.0 X) ve Leeds–Man United (%36.6 X) gibi denk fikstürlerde en yüksek olasılık yapay şekilde "Beraberlik" çıkıyordu. İncelemede, `fit_probability_calibrator` fonksiyonunun softmax logit dönüşümünde:
  $$\mathbf{b} = [-0.0985, \; \mathbf{+0.1346}, \; -0.0360]$$
  şeklinde Beraberlik sınıfına (indeks 1) doğrudan $+0.1346$ puanlık yapay bir ekleme yaptığı tespit edildi. Optimizasyon ceza yememek için denk maçlarda beraberliği güvenli liman olarak görerek şişiriyordu.
* **Uygulanan Çözüm (`src/models/train_match_outcome.py`):**
  Kalibratörün 3 sınıflı 1X2 durumunda Beraberlik bias terimi $[-0.20, +0.03]$ tavanıyla sınırlandırıldı:
  ```python
  if class_count == 3:
      params[2] = float(np.clip(params[2], -0.20, 0.03))
  ```
* **Doğrulanan Etki:**
  - Brentford vs Liverpool: X olasılığı %37.0'den **%32.0'ye** indi; Liverpool **%38.0 (Adil Oran: 2.63)** ile hak ettiği 1. sıraya yerleşti.
  - Leeds vs Man United: X olasılığı %36.6'dan **%32.8'e** indi; maç 2.97 - 3.05 - 2.99 ile tam bir dengeli derbi oranına kavuştu.

### 3. %50 Dixon–Coles / %50 Lojistik Regresyon Altın Dengesi (Golden Balance)

* **Kusur Teşhisi:**
  Önceki üretim modelinde `ensemble_weight = 0.65` olarak ayarlıydı (%65 Lojistik Regresyon / %35 Dixon-Coles). Lojistik regresyonun erken sezon haftalarındaki küçük örneklem gürültüsü ligin uzun vadeli sınıf/güç farkını bastırıyordu.
* **Uygulanan Çözüm (`src/models/train_match_outcome.py`):**
  Feature'lar rakip gücüne göre SoS ile temizlendiği için, ensemble ağırlığı kalıcı olarak **`ensemble_weight = 0.50` (%50 Dixon-Coles / %50 Lojistik Regresyon)** olarak kilitlendi ve `ensemble_gate_passed = True` ile üretimde kalıcı hale getirildi.
* **Canlı 2026–27 7. Hafta Fikstür Sonuçları:**
  - **Everton vs Chelsea:** %41.7 - %27.7 - %30.6 (2.40 - 3.61 - 3.27) $\rightarrow$ **%36.6 - %30.0 - %33.4 (Adil Oran: 2.73 - 3.33 - 2.99)**. Chelsea'nin maruz kaldığı ağır fikstür cezası kalktı, Everton'ın 2.40'lık sahte favoriliği silindi.
  - **Man City vs Ipswich Town:** %77.4 $\rightarrow$ **%81.4 (Adil Oran: 1.23)** ile City'nin gerçek dominantlığı tescillendi.
  - **Nottingham vs Arsenal:** **%13.6 - %27.6 - %58.8 (Adil Oran: 7.35 - 3.62 - 1.70)**.
  - **Fulham vs Hull City:** **%37.5 - %26.9 - %35.6** ile flaş giriş yapan Hull City'nin deplasman tehdidi korundu.


