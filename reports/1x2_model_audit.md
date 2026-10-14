# 1X2 Maç Sonucu Modeli: Uçtan Uca Denetim

**İnceleme tarihi:** 13 Ekim 2026  
**Veri anlık görüntüsü:** 1.580 tamamlanmış maç, 2022/23–2026/27; son sezon 60 maçlık kısmi örnek.  
**Kapsam:** sonuç etiketleri, maç öncesi özellikler, zaman sıralı eğitim/değerlendirme, beraberlik olasılıkları ve API sunumu. Yerel pipeline yeniden çalıştırıldı; test paketi çalıştırılmadı.

## Kısa sonuç

Model tamamen başarısız değil: güncel kronolojik holdout'ta log-loss **1,045**, sınıf-prior baseline'ında **1,114**; çok sınıflı Brier **0,630**, baseline'da **0,675**. Dixon–Coles karşılaştırması **1,065** log-loss verdi. Genel olasılık skoru baseline'dan iyi, ancak beraberlik ayrımı hâlâ zayıf.

Asıl açık, **beraberlik olasılığının düşük kalması ve maçları beraberlik olarak ayıracak sinyalin zayıf olması**. Aynı 316 maçta gerçek sonuçların 98'i beraberlik (%31,0); modelin ortalama beraberlik olasılığı %23,4 ve yalnızca **4 maçı** en olası sonuç olarak beraberlik seçti. Beraberlik AUC'si **0,5381**, Brier'ı **0,2188**. Gerçek beraberliklerdeki ortalama tahmin %23,9, diğer maçlarda %23,1; sıralama sinyali hâlâ çok zayıf.

İkinci önemli etken zaman içindeki sonuç dağılımı. 2025/26 sezonunun ilk 124 maçında beraberlik oranı **%20,2**, kalan 256 maçta **%30,9** olmuş. Ana 80/20 bölmesi sezonun içine denk geldiği için model, düşük beraberlik oranlı başlangıç döneminden öğrenip daha yüksek oranlı sonraki dönemde sınanıyor.

## Model akışı

| Aşama | Mevcut davranış | Denetim sonucu |
|---|---|---|
| Etiket | `home_score` ve `away_score` karşılaştırılarak H/D/A üretiliyor; oynanmamış maçlar dışarıda. | Etiketler saklanan `match_result` ile 1.580 maçın tamamında uyuştu. Tekrarlanan maç kimliği, negatif veya kesirli skor görülmedi. |
| Zaman sırası | Maçlar kickoff ve maç kimliğiyle sıralanıyor. | Kronolojik sıra tutarlı. |
| Takım formu | Gol, şut, xG proxy'si ve diğer takım metrikleri; rolling ve EWMA ile geçmişten hesaplanıyor, mevcut maçtan önce bir adım kaydırılıyor. | Kodda mevcut maç sonucunu kendi özelliğine katan doğrudan bir kaçak bulmadım. Bu, tüm olası sızıntıların biçimsel olarak kanıtlandığı anlamına gelmez. |
| Takım gücü | Elo ve sezon içi puan/averaj durumları sonuç güncellenmeden önce kaydediliyor; sezon geçişinde Elo ortalamaya çekiliyor ve lig tablosu önsel değere dönüyor. | Eğitim tarafının zaman sırası mantıklı. Yaklaşan fikstürün sezon etiketi artık API feature satırına aktarılıyor; geçiş kodu eklendi, entegrasyon testi yapılmadı (aşağıda). |
| 1X2 özellikleri | 100 özellik: Elo/PPG/averaj ve mutlak farkları, gol/xG/kaleyi bulan şut formu, beklenen xG dengesi, xG proxy gözlem yaşı ve dinlenme. | 884 ana geliştirme satırı var. Yeni özellikler basit, maç öncesi ölçüler; dış sezon kıyası bunların ek katkısını sınırlı ve karışık gösteriyor. |
| Model seçimi | Düzenlileştirilmiş multinomial lojistik regresyon ve küçük LightGBM adayları; dört expanding-window zaman katında log-loss ile seçim. En iyi aday `logreg_C0.003`. | Zaman sıralı seçim uygun bir başlangıç. Kalibrasyon ve aday seçimi yalnız geliştirme bölümünde yapılıyor. |
| Kalibrasyon | Holdout ölçümünde geliştirme OOF'si, üretim artefaktında uygun tüm etiketlerin forward OOF'si kullanılıyor. | Üretim kalibrasyonu 960 OOF tahminini kapsıyor. Tek bir global dönüşüm dönem içi değişimi bütünüyle çözmüyor; sınıf ayrımını da tek başına yaratamaz. |
| Üretim | API model olasılıklarını kalibre edip H/D/A yüzdeleri olarak döndürüyor. | 2022/23 sonuçları 1X2 fitinden çıkarılmış; sezon, daha yeni maçların geçmiş özelliklerini üretmek için veri geçmişinde tutuluyor. |

Ana değerlendirme modeli 884 geliştirme satırıyla fit edilip 316 maçta ölçülüyor. Üretim sınıflandırıcısı 2022/23 dışındaki **1.200 etiketli maça** tekrar fit ediliyor.

## Bulgular

### 1. Yüksek öncelik: beraberlik olasılığı son holdout'ta düşük ve ayrıştırma zayıf

Ana kronolojik holdout, 29 Kasım 2025–12 Ekim 2026 arasındaki 316 maç. Sınıf sırası ev sahibi / beraberlik / deplasman.

| Sonuç | Gerçek maç sayısı | Gerçek oran | Modelin en olası sınıf seçimi |
|---|---:|---:|---:|
| Ev sahibi | 120 | %38,0 | 202 |
| Beraberlik | 98 | %31,0 | 4 |
| Deplasman | 98 | %31,0 | 110 |

Güncel holdout olasılık metrikleri `reports/model_benchmarks.md` içinde veriliyor. Sınıf ofsetini artırmak toplam beraberlik tahminini yükseltebilir; gerçek beraberlikleri diğer maçlardan ayırma farkı yalnızca 0,8 yüzde puan olduğundan bu tek başına yeterli çözüm olmaz.

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

### 3. Uygulandı: üretim kalibratörünü tüm uygun geçmişle fit et

Üretim kalibratörü, 2022/23 etiketleri hariç 1.200 üretim etiketinin ileri-zamanlı OOF tahminleriyle fit ediliyor; OOF doğrulama blokları toplam **960 tahmin** içeriyor. Holdout metrikleri yalnız geliştirme döneminde fit edilen ayrı kalibratörle hesaplanıyor.

Bu değişiklik üretim kalibratörüne son sezon bilgisini ekler. Bunun gelecekteki kalibrasyonu iyileştirdiği henüz bağımsız gelecek sezonla ölçülmedi; OOF fit değerleri performans sonucu olarak yorumlanmamalı.

### 4. Uygulandı: dış sezonlarda karşılaştırmalı değerlendirme; son sezon hâlâ kilitli değil

Koddaki ana prosedür ilk %80'de model seçip son %20'yi sınama olarak ayırıyor. Ancak 2022/23'ü fit dışı bırakma kararı ve çeşitli model denemeleri, raporlanan aynı sezon kontrollerine bakılarak verilmiş. Bu sonuçlar faydalı teşhis verileri; artık tamamen dokunulmamış bir final test seti gibi yorumlanmamalı.

Birden fazla tam sezon dışarıda tutularak 1X2 geçmiş penceresi, recency ağırlığı ve xG proxy ablasyonu karşılaştırıldı. Log-loss, çok sınıflı ve beraberlik Brier'ı, beraberlik AUC'si, gerçekleşen/tahmin edilen beraberlik oranı ve beraberlik sınıf tahminleri rapora eklendi. Ancak bu kontroller politika seçmek için kullanıldığı için artık tamamen dokunulmamış test sayılmaz; 2026/27 tamamlanınca son sezonu yeni kararlar için kilitli tutmak gerekir. Olasılık dilimi raporu bu turda eklenmedi.

### 5. Uygulandı: yakın dönem, xG proxy'si ve beraberlik dengesi özelliklerini dış sezonlarda karşılaştır

Her dış sezonda aynı `logreg_C0.003` modeli sabit tutuldu; tüm geçmiş, 2022/23'ü çıkarma, son iki sezon ve 1,5 sezon yarı ömürlü recency ağırlığı; tüm özellikler, xG proxy'siz özellikler ve beraberlik dengesi özellikleri çıkarılmış özellikler karşılaştırıldı. Kalibrasyon her dış sezon için yalnız o sezondan önceki OOF tahminleriyle fit edildi. Kıyaslama ayrıntıları `reports/model_benchmarks.md` içindeki yeni tabloda.

2024/25–2026/27 ortak dış sezonlarında `exclude_2022_23` tüm özellikler ortalaması log-loss **1,0161** oldu; beraberlik dengesi özelliklerini çıkarmak **1,0179** verdi. Fark küçük ve sezon sonuçları karışık; bu özellikler güçlü veya kesin bir kazanç sayılmaz. 2026/27 de yalnız 60 maçtır. Mevcut 2022/23 fit dışı politikayı korudum, ancak bunu doğrulanmış genel kural saymıyorum.

xG proxy'sini kaldırmak log-loss'ta tutarlı sonuç vermedi; bazı sezonlarda iyileştirirken bazılarında kötüleştirdi. Beraberlik AUC etkisi de sezona göre değişti. Bu nedenle proxy üretim özelliklerinde kaldı; sonuçlar yeni bir sabit ayarı seçmek için yeterli değil.

### 6. Orta öncelik: xG özellikleri seyrek bir proxy'den geliyor; gözlem yaşı artık modele veriliyor

Resmi şut-başı xG kullanılmıyor. Yerel xG, şut ve büyük şans toplamlarından üretilmiş bir proxy. Bu proxy, oynanmış maçlardaki 3.160 takım-maç satırının yalnızca **1.337'sinde (%42,3)** kaynak verisiyle mevcut.

Özellik üretimi eksik xG maçlarını rolling penceresine almıyor; son geçerli xG gözlemlerinin ortalamasını kullanıyor. Bu yenilemede her takım için xG proxy'sinin son geçerli maçından beri geçen gün sayısı da eklendi; eğitim ve canlı tahminde aynı maç öncesi zaman sırası uygulanıyor.

Bu durumun beraberlik açığının doğrudan nedeni olduğunu söylemek için kanıt yok. xG gözlem yaşının tek başına etkisi henüz ayrıştırılmadı. Doğrulanmış maç başı xG bulunursa bunu aynı dış sezon protokolünde değerlendirmek gerekir.

### 7. Uygulandı: API'de yaklaşan fikstür sezonuna geçiş

Eğitimde `_run_strength`, yeni sezonun ilk maçını işlerken Elo'yu %20 ortalamaya çekiyor ve PPG/averaj tablosunu sıfırlanmış sezon önselinden başlatıyor. `build_prediction_row` yaklaşan fikstürün sezonunu kullanarak canlı tahminde aynı geçişi uyguluyor.

Önceki API mantığıyla karşılaştırmada 2025/26 açılışındaki Liverpool–Bournemouth için `elo_diff` yaklaşık **37,2**, `ppg_diff` **0,68**, `gdpg_diff` **0,80** farklıydı. Form özellikleri aynıydı; fark sezon geçişindeydi. Yeni model özellikleriyle 20 ileriye dönük API tahmini kaydedildi; otomatik feature-parity testi ve genel test paketi bu çalışmada çalıştırılmadı.

### 8. Ürün arayüzü kapsam dışı

Bu çalışma boyunca bahis oranları kullanılmadı; model girdisi veya sonuç değerlendirmesine dahil edilmedi.

## Geliştirme sırası ve bu turdaki durumu

1. **Tamamlandı — dış zaman ölçümü:** sezon bazlı dış holdout'lar ve beraberlik metrikleri eklendi. Aynı sonuçlar üzerinde politika kıyası yapıldığı için 2026/27'nin kalan maçlarını kilitli test olarak tut.
2. **Tamamlandı — zaman penceresi deneyi:** tüm geçmiş, 2022/23 etiketlerini çıkarma, son iki sezon ve 1,5 sezon yarı ömürlü ağırlıklar karşılaştırıldı. Mevcut fit politikasını korudum; üstünlük küçük ve üç sezonla sınırlı.
3. **Tamamlandı — Dixon–Coles kıyası:** sezon dış katları ve ana holdout'ta değerlendirildi. Prior baseline'ı geçti ama ana holdout'ta mevcut sınıflandırıcıyı geçmedi; üretim modeli olarak seçilmedi. Model karışımı denenmedi.
4. **Kısmen tamamlandı — xG proxy:** proxy var/yok dış sezonlarda kıyaslandı ve gözlem yaşı özelliği eklendi. Proxy'nin doğrulanmış xG ile karşılaştırılması açık.
5. **Kodlandı — API özellik eşleşmesi:** sezon sınırı ve yeni xG gözlem yaşı/beraberlik özellikleri canlı feature satırında üretiliyor; 20 ileriye dönük API tahmini başarıyla kaydedildi. Otomatik test paketi çalıştırılmadı.
6. **Başlatıldı — ileriye dönük holdout:** `src/analytics/prospective_1x2_benchmark.py` gerçek API tahminlerini maçtan önce kaydediyor. 13 Ekim 2026'da güncel üretim artefaktıyla önümüzdeki 14 gün içindeki 20 maç için tahmin saklandı (SHA-256 öneki `d9cb30d28d02`); aynı maçların önceki artefakt kayıtları korunuyor. Tahminler `data/processed/1x2_forecast_log.jsonl` içinde tutuluyor ve maç sonucu geldiğinde yeniden tahmin edilmiyor.
7. **Bekliyor — yeni sonuçlar:** veri eşitlendikten sonra `python3 -m src.analytics.prospective_1x2_benchmark score` komutu, maç öncesi kaydedilmiş tahminleri tamamlanmış sonuçlarla eşleştirip log-loss, çok sınıflı/beraberlik Brier'ı, beraberlik AUC'si ve oran uyumunu hesaplar. 2026/27 tamamlanınca sezonun kalan bölümünü kilitli dış test olarak kullan; ilk 60 maçtan kesin sonuç çıkarma.

İleriye dönük tahminleri düzenli yenilemek için veri güncellemesinden sonra `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` çalıştır. Aynı gün, aynı maç ve aynı model artefaktı için yinelenen kayıt eklenmez. Sonuçlar gelmeden performans metrikleri hesaplanamaz.

## İncelenen kod yolları

- `src/processing/process_season_data.py`: skor ve maç özeti etiketlerinin oluşturulması.
- `src/features/build_features.py`: geçmiş form, dinlenme, Elo/puan tablosu ve tahmin satırı.
- `src/models/train_match_outcome.py`: 1X2 özellikleri, kronolojik CV, kalibrasyon, sezon holdout'ları ve üretim fit'i.
- `src/api/server.py`: canlı state ve `/api/predict` olasılık dönüşümü.
- `frontend/src/components/PredictorTab.jsx`: olasılıktan türetilen teorik oran metni.

## Güncelleme — 14 Ekim 2026: F4–F7 kararları ve ileriye dönük günlük

Bu ek, raporun 13 Ekim tarihli ilk incelemesinden sonraki faz kararlarını kaydeder. Aşağıdaki sonuçlar, aynı üç tam dış sezon üzerinde karşılaştırma yapıldığı için yeni bağımsız sezon verisi gibi yorumlanmamalıdır.

| Faz | Dış sezon sonucu | Karar |
|---|---|---|
| F4 — Lojistik + Dixon–Coles ensemble | Ensemble 3 sezonun **1** tanesinde iyileşti; ortalama ensemble−lojistik log-loss farkı **+0,00312**. Karar kapısı en az 2/3 sezon ve ortalama Δ < −0,002 gerektiriyordu. | Kapı geçmedi. `model_dc` üretim artefaktına eklenmedi; API mevcut lojistik 1X2 olasılıklarını kullanmayı sürdürüyor. |
| F5 — Beraberlik eğilim özellikleri | Ortalama log-loss farkı **+0,0037**; Draw AUC farkı **+0,0067**. Kapı log-loss Δ < −0,002 ve Draw AUC Δ ≥ +0,01 gerektiriyordu. | Kapı geçmedi. Dokuz özellik ortak offline/canlı hesaplayıcıda mevcut, ancak production feature listesine alınmadı. |
| F6 — Zaman ağırlıklı kalibrasyon | 150/300/600 satır yarı ömürleri için ortalama dış sezon log-loss farkları sırasıyla **−0,00006 / −0,00019 / −0,00014**; gerekli eşik **≤ −0,002** idi. | Hiçbir yarı ömür seçilmedi; standart kalibratör ve 1X2 artefaktı korundu. |
| F7 — xG proxy | Aggregate şut istatistiklerinden türetilen ve yalnızca %42,3 kapsaması olan proxy model özelliklerinden, feature üretiminden ve API/UI yolundan kaldırıldı. | Üretim tahmininde xG proxy kullanılmıyor. Bu raporun 13 Ekim tarihli ilk bölümlerinde proxy hakkında yazılanlar tarihsel durumu anlatır; yeni kararı değiştirmez. |

F4–F6 deney ayrıntıları, dış sezon JSON'ları ve artefakt parmak izleri [model-improvement guide yürütme kaydında](model_improvement_guide.md) tutuluyor. F10 ile `data/processed/1x2_forecast_log.jsonl` günlük kayıtları gol-market tahminlerini ve ayrı goals-model SHA-256 değerini de saklıyor. Mevcut üretim artefaktında F4 ensemble bulunmadığından ensemble alanı yeni kayıtlarda oluşmuyor; bu alan ileride API çıktısına bir ensemble eklenirse koşullu olarak yazılır. Tahminler maç sonuçları geldikçe `reports/prospective_1x2_scorecard.json` içinde 1X2, Over 1.5/2.5/3.5 ve BTTS için skorlanır.

