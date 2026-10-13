# 1X2 Maç Sonucu Modeli: Uçtan Uca Denetim

**İnceleme tarihi:** 13 Ekim 2026  
**Veri anlık görüntüsü:** 1.580 tamamlanmış maç, 2022/23–2026/27; son sezon 60 maçlık kısmi örnek.  
**Kapsam:** sonuç etiketleri, maç öncesi özellikler, zaman sıralı eğitim/değerlendirme, beraberlik olasılıkları ve API sunumu. Bu incelemede model kodu ve yerel veriler okundu; yeni bir model veya bahis oranı kaynağı eklenmedi, test paketi çalıştırılmadı.

## Kısa sonuç

Model tamamen başarısız değil: son kronolojik holdout'ta log-loss **1,044**, sınıf-prior baseline'ında **1,114**; çok sınıflı Brier **0,630**, baseline'da **0,675**. Dixon–Coles karşılaştırması **1,065** log-loss verdi. Yani mevcut sınıflandırıcı bu değerlendirmelerde basit referanslardan daha iyi.

Asıl açık, **beraberlik olasılığının düşük kalması ve maçları beraberlik olarak ayıracak sinyalin zayıf olması**. Aynı 316 maçta gerçek beraberlik oranı **%31,0**, tahmin edilen ortalama beraberlik olasılığı **%23,5**; model yalnızca **2 maçı** en olası sonuç olarak beraberlik seçti. Beraberlik için ROC AUC **0,531** (0,5 rastgele sıralama düzeyidir). Bu, yalnızca eşik veya global kalibrasyonla çözülecek bir sorun değil.

İkinci önemli etken zaman içindeki sonuç dağılımı. 2025/26 sezonunun ilk 124 maçında beraberlik oranı **%20,2**, kalan 256 maçta **%30,9** olmuş. Ana 80/20 bölmesi sezonun içine denk geldiği için model, düşük beraberlik oranlı başlangıç döneminden öğrenip daha yüksek oranlı sonraki dönemde sınanıyor.

## Model akışı

| Aşama | Mevcut davranış | Denetim sonucu |
|---|---|---|
| Etiket | `home_score` ve `away_score` karşılaştırılarak H/D/A üretiliyor; oynanmamış maçlar dışarıda. | Etiketler saklanan `match_result` ile 1.580 maçın tamamında uyuştu. Tekrarlanan maç kimliği, negatif veya kesirli skor görülmedi. |
| Zaman sırası | Maçlar kickoff ve maç kimliğiyle sıralanıyor. | Kronolojik sıra tutarlı. |
| Takım formu | Gol, şut, xG proxy'si ve diğer takım metrikleri; rolling ve EWMA ile geçmişten hesaplanıyor, mevcut maçtan önce bir adım kaydırılıyor. | Kodda mevcut maç sonucunu kendi özelliğine katan doğrudan bir kaçak bulmadım. Bu, tüm olası sızıntıların biçimsel olarak kanıtlandığı anlamına gelmez. |
| Takım gücü | Elo ve sezon içi puan/averaj durumları sonuç güncellenmeden önce kaydediliyor; sezon geçişinde Elo ortalamaya çekiliyor ve lig tablosu önsel değere dönüyor. | Eğitim tarafının zaman sırası mantıklı. Yaklaşan fikstürün sezon etiketi artık API feature satırına aktarılıyor; geçiş kodu eklendi, entegrasyon testi yapılmadı (aşağıda). |
| 1X2 özellikleri | 91 özellik: Elo/PPG/averaj, gol/xG/kaleyi bulan şut formu, bunların farkları, dinlenme günü ve beklenen xG proxy'si. | 884 ana geliştirme satırına karşı 91 özellik var; birçok form penceresi birbirine bağlı. Bu ölçekte karmaşık yeni özellikleri denetimsiz eklemek overfit riskini artırır. |
| Model seçimi | Düzenlileştirilmiş multinomial lojistik regresyon ve küçük LightGBM adayları; dört expanding-window zaman katında log-loss ile seçim. En iyi aday `logreg_C0.003`. | Zaman sıralı seçim uygun bir başlangıç. Kalibrasyon ve aday seçimi yalnız geliştirme bölümünde yapılıyor. |
| Kalibrasyon | Holdout ölçümünde geliştirme OOF'si, üretim artefaktında uygun tüm etiketlerin forward OOF'si kullanılıyor. | Yeni üretim kalibrasyonu 960 OOF tahminini kapsıyor. Tek bir global dönüşüm dönem içi değişimi bütünüyle çözmüyor; sınıf ayrımını da tek başına yaratamaz. |
| Üretim | API model olasılıklarını kalibre edip H/D/A yüzdeleri olarak döndürüyor. | 2022/23 sonuçları 1X2 fitinden çıkarılmış; sezon, daha yeni maçların geçmiş özelliklerini üretmek için veri geçmişinde tutuluyor. |

Ana değerlendirme modeli 884 geliştirme satırıyla fit edilip 316 maçta ölçülüyor. Üretim sınıflandırıcısı 2022/23 dışındaki **1.200 etiketli maça** tekrar fit ediliyor.

## Bulgular

### 1. Yüksek öncelik: beraberlik olasılığı son holdout'ta düşük ve ayrıştırma zayıf

Ana kronolojik holdout, 29 Kasım 2025–12 Ekim 2026 arasındaki 316 maç. Sınıf sırası ev sahibi / beraberlik / deplasman.

| Sonuç | Gerçek maç sayısı | Gerçek oran | Ortalama tahmin olasılığı | Modelin en olası sınıf seçimi |
|---|---:|---:|---:|---:|
| Ev sahibi | 120 | %38,0 | %43,2 | 188 |
| Beraberlik | 98 | %31,0 | %23,5 | 2 |
| Deplasman | 98 | %31,0 | %33,4 | 126 |

Karışıklık matrisi; satırlar gerçek, sütunlar tahmin edilen sonuç:

| Gerçek \\ Tahmin | Ev sahibi | Beraberlik | Deplasman |
|---|---:|---:|---:|
| Ev sahibi | 89 | 0 | 31 |
| Beraberlik | 53 | 2 | 43 |
| Deplasman | 46 | 0 | 52 |

Beraberlik olan 98 maçın 96'sında model başka bir sonucu daha olası buldu. Beraberlik olasılığının ortalaması gerçek beraberliklerde **%24,0**, diğer maçlarda **%23,2**. Bu iki grubun farkı çok küçük; beraberlik ROC AUC'si **0,531**. Mevcut kalibratörün sınıf ofseti bu eksik sıralama bilgisini telafi edemez.

**Yorum:** Genel 1X2 skoru baseline'dan iyi; tüm modeli atmak için kanıt yok. Ancak beraberlik yüzdesini ayrı bir kalite boyutu olarak ele almak gerekiyor. Sadece beraberlik sabitini yükseltmek daha çok maçı “D” seçtirir ama hangi maçların beraberlik olduğunu öğrenmiş olmaz.

### 2. Yüksek öncelik: beraberlik oranı zaman içinde değişmiş

| Sezon | Maç | Ev sahibi | Beraberlik | Deplasman |
|---|---:|---:|---:|---:|
| 2022/23 | 380 | %48,4 | %22,9 | %28,7 |
| 2023/24 | 380 | %46,1 | %21,6 | %32,4 |
| 2024/25 | 380 | %40,8 | %24,5 | %34,7 |
| 2025/26 | 380 | %42,6 | %27,4 | %30,0 |
| 2026/27 (kısmi) | 60 | %38,3 | %31,7 | %30,0 |

Ana modelin geliştirme diliminde 2022/23 fit dışı bırakılınca kalan 884 maçın beraberlik oranı **%22,6**. Holdout oranı **%31,0**. Özellikle 2025/26 içindeki fark büyük: ilk 124 maçta **%20,2**, sonraki 256 maçta **%30,9** beraberlik var. Bu, mevcut ana değerlendirmedeki düşük beraberlik tahmininin önemli bir açıklaması; oran değişiminin nedeni bu veriden tek başına çıkarılamaz.

Tam sezon ilerlemeli kontrolleri, 2025/26 verisinin işe yaramadığını göstermiyor. Kalibrasyonlu ortalama beraberlik olasılığı / gerçek oran:

| Test sezonu | Tahmin edilen ortalama P(D) | Gerçek beraberlik oranı | Test maç sayısı |
|---|---:|---:|---:|
| 2024/25 | %24,4 | %24,5 | 380 |
| 2025/26 | %26,4 | %27,4 | 380 |
| 2026/27 | %28,3 | %31,7 | 60 |

2026/27 tahmini, 2025/26 tam sezonunu eğitimde kullanan ileri-zamanlı kontroldür; 60 maçlık örnek geçicidir. 2025/26 verisi sonraki sezonun tahminini geçmiş sezonlara kıyasla yaklaştırmış, ama yükselen beraberlik oranını bütünüyle yakalayamamıştır. Bu nedenle “yeni sezon işe yaramadı” sonucu doğru olmaz; daha doğru sonuç, **yeni verinin katkısı var ama dönem/kalibrasyon farkı sürüyor**.

### 3. Uygulandı: üretim kalibratörünü tüm uygun geçmişle yeniden fit et

Bu turda üretim kalibratörünü, 1.200 üretim etiketinin ileri-zamanlı OOF tahminleriyle fit edecek şekilde değiştirdim. OOF doğrulama blokları toplam **960 tahmin** içeriyor. Mevcut üretim kalibratörü sıcaklığı **0,973**, beraberlik ofseti **+0,105**. Holdout metrikleri geliştirme döneminde fit edilen ayrı kalibratörle hesaplanmaya devam ediyor.

Bu değişiklik üretim kalibratörüne son sezon bilgisini ekler. Bunun gelecekteki kalibrasyonu iyileştirdiği henüz bağımsız gelecek sezonla ölçülmedi; OOF fit değerleri performans sonucu olarak yorumlanmamalı.

### 4. Uygulandı: dış sezonlarda karşılaştırmalı değerlendirme; son sezon hâlâ kilitli değil

Koddaki ana prosedür ilk %80'de model seçip son %20'yi sınama olarak ayırıyor. Ancak 2022/23'ü fit dışı bırakma kararı ve çeşitli model denemeleri, raporlanan aynı sezon kontrollerine bakılarak verilmiş. Bu sonuçlar faydalı teşhis verileri; artık tamamen dokunulmamış bir final test seti gibi yorumlanmamalı.

Birden fazla tam sezon dışarıda tutularak 1X2 geçmiş penceresi, recency ağırlığı ve xG proxy ablasyonu karşılaştırıldı. Log-loss, çok sınıflı ve beraberlik Brier'ı, beraberlik AUC'si, gerçekleşen/tahmin edilen beraberlik oranı ve beraberlik sınıf tahminleri rapora eklendi. Ancak bu kontroller politika seçmek için kullanıldığı için artık tamamen dokunulmamış test sayılmaz; 2026/27 tamamlanınca son sezonu yeni kararlar için kilitli tutmak gerekir. Olasılık dilimi raporu bu turda eklenmedi.

### 5. Uygulandı: yakın dönem ve xG proxy ablasyonunu dış sezonlarda karşılaştır

Her dış sezonda aynı `logreg_C0.003` modeli sabit tutuldu; tüm geçmiş, 2022/23'ü çıkarma, son iki sezon ve 1,5 sezon yarı ömürlü recency ağırlığı; ayrıca tüm özellikler ve xG proxy'si çıkarılmış özellikler karşılaştırıldı. Kalibrasyon her dış sezon için yalnız o sezondan önceki OOF tahminleriyle fit edildi. Kıyaslama ayrıntıları `reports/model_benchmarks.md` içindeki yeni tabloda.

2024/25–2026/27 ortak dış sezonlarında, tüm özelliklerle `exclude_2022_23` ortalama log-loss **1,0176**, recency ağırlığı **1,0185**, tüm geçmiş **1,0218**, yalnız son iki sezon **1,0255** oldu. Bu küçük farklar yalnız üç dış sezona dayanıyor; 2026/27 de 60 maç. Mevcut 2022/23 fit dışı politikayı şimdilik korudum, ancak bunu doğrulanmış genel kural saymıyorum. Son iki sezon penceresi özellikle kısmi 2026/27'de geride kaldı.

xG proxy'sini kaldırmak log-loss'ta tutarlı sonuç vermedi; bazı sezonlarda iyileştirirken bazılarında kötüleştirdi. Buna karşılık xG'siz seçenek 2025/26 ve 2026/27 dış sezonlarında beraberlik AUC'sini bir miktar yükseltti. Örnekler küçük ve karışık olduğundan xG proxy'sini üretim özelliklerinden henüz çıkarmadım.

### 6. Orta öncelik: xG özellikleri seyrek bir proxy'den geliyor

Resmi şut-başı xG kullanılmıyor. Yerel xG, şut ve büyük şans toplamlarından üretilmiş bir proxy. Bu proxy, oynanmış maçlardaki 3.160 takım-maç satırının yalnızca **1.337'sinde (%42,3)** kaynak verisiyle mevcut.

Özellik üretimi eksik xG maçlarını rolling penceresine almıyor; son geçerli xG gözlemlerinin ortalamasını kullanıyor ve bu gözlemin kaç gün önce olduğuna dair bir yaş özelliği üretmiyor. Ana holdout'ta son xG proxy gözlemi takım-maçlerin yaklaşık **%15,4'ünde 30 günden**, **%6,1'inde 90 günden** eskiydi. Böylece dolu görünen bir özellik bazen güncel olmayan veriyi temsil ediyor.

Bu durumun beraberlik açığının doğrudan nedeni olduğunu söylemek için kanıt yok. xG proxy'sini çıkarma seçeneği dış sezonlarda karşılaştırıldı; xG gözlem yaşı/doluluk göstergesi henüz eklenmedi. Doğrulanmış maç başı xG bulunursa bunu ayrı bir dış sezon deneyiyle değerlendirmek gerekir.

### 7. Uygulandı: API'de yaklaşan fikstür sezonuna geçiş

Eğitimde `_run_strength`, yeni sezonun ilk maçını işlerken Elo'yu %20 ortalamaya çekiyor ve PPG/averaj tablosunu sıfırlanmış sezon önselinden başlatıyordu. Bu turda `build_prediction_row`'a yaklaşan fikstürün sezonunu ekledim; API artık yeni sezonun ilk maçından önce aynı Elo regresyonunu ve tablo sıfırlamasını uyguluyor.

Değişiklikten önce eğitim satırı ile eski API mantığını karşılaştırdığımda 2025/26 açılışındaki Liverpool–Bournemouth için `elo_diff` yaklaşık **37,2**, `ppg_diff` **0,68**, `gdpg_diff` **0,80** farklıydı. Form özellikleri aynıydı; fark sezon geçişindeydi. Koddaki düzeltme bu farkı kapatmayı hedefliyor; test paketi çalıştırılmadı.

### 8. Ürün arayüzü kapsam dışı

Bu çalışma boyunca bahis oranları kullanılmadı; model girdisi veya sonuç değerlendirmesine dahil edilmedi.

## Geliştirme sırası ve bu turdaki durumu

1. **Tamamlandı — dış zaman ölçümü:** sezon bazlı dış holdout'lar ve beraberlik metrikleri eklendi. Aynı sonuçlar üzerinde politika kıyası yapıldığı için 2026/27'nin kalan maçlarını kilitli test olarak tut.
2. **Tamamlandı — zaman penceresi deneyi:** tüm geçmiş, 2022/23 etiketlerini çıkarma, son iki sezon ve 1,5 sezon yarı ömürlü ağırlıklar karşılaştırıldı. Mevcut fit politikasını korudum; üstünlük küçük ve üç sezonla sınırlı.
3. **Tamamlandı — Dixon–Coles kıyası:** sezon dış katları ve ana holdout'ta değerlendirildi. Prior baseline'ı geçti ama ana holdout'ta mevcut sınıflandırıcıyı geçmedi; üretim modeli olarak seçilmedi. Model karışımı denenmedi.
4. **Kısmen tamamlandı — xG proxy ablasyonu:** proxy var/yok kıyaslandı, sonuçlar karışık olduğu için üretim özellikleri korunuyor. Gözlem yaşı/doluluk göstergesi ve doğrulanmış xG deneyi açık.
5. **Kodlandı, doğrulama bekliyor — API sezon sınırı:** fikstürün sezonu feature üretimine aktarılıyor; otomatik test veya API entegrasyon kontrolü bu turda çalıştırılmadı.
6. **Başlatıldı — ileriye dönük holdout:** API'nin gerçek üretim tahminlerini maçtan önce kaydeden `src/analytics/prospective_1x2_benchmark.py` eklendi. İlk anlık görüntüde 13 Ekim 2026 itibarıyla, önümüzdeki 14 gün içindeki 20 maç için tahmin saklandı. Tahminler `data/processed/1x2_forecast_log.jsonl` içinde model artefaktı SHA-256 değeriyle tutuluyor; maç sonucu geldiğinde yeniden tahmin edilmiyor.
7. **Bekliyor — yeni sonuçlar:** veri eşitlendikten sonra `python3 -m src.analytics.prospective_1x2_benchmark score` komutu, maç öncesi kaydedilmiş tahminleri tamamlanmış sonuçlarla eşleştirip log-loss, çok sınıflı/beraberlik Brier'ı, beraberlik AUC'si ve oran uyumunu hesaplar. 2026/27 tamamlanınca sezonun kalan bölümünü kilitli dış test olarak kullan; ilk 60 maçtan kesin sonuç çıkarma.

İleriye dönük tahminleri düzenli yenilemek için veri güncellemesinden sonra `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` çalıştır. Aynı gün, aynı maç ve aynı model artefaktı için yinelenen kayıt eklenmez. Sonuçlar gelmeden performans metrikleri hesaplanamaz.

## İncelenen kod yolları

- `src/processing/process_season_data.py`: skor ve maç özeti etiketlerinin oluşturulması.
- `src/features/build_features.py`: geçmiş form, dinlenme, Elo/puan tablosu ve tahmin satırı.
- `src/models/train_match_outcome.py`: 1X2 özellikleri, kronolojik CV, kalibrasyon, sezon holdout'ları ve üretim fit'i.
- `src/api/server.py`: canlı state ve `/api/predict` olasılık dönüşümü.
- `frontend/src/components/PredictorTab.jsx`: olasılıktan türetilen teorik oran metni.

