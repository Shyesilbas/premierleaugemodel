# Kod Tabanı, Raporlar ve Model Değerlendirmesi

**Denetim tarihi:** 14 Ekim 2026  
**Veri anlık görüntüsü:** 5 sezon, 1.900 fikstür, 1.580 tamamlanmış maç ve 320 gelecek fikstür  
**Raporların giriş noktası:** [Rapor Merkezi](README.md)

## Yönetici özeti

Proje uçtan uca çalışan bir futbol veri akışı, zaman sıralı model değerlendirmesi ve React/FastAPI arayüzü içeriyor. Bu rapordan sonraki 14 Ekim 1X2 düzeltme turunda tam yerel pipeline yeniden tamamlandı; güncel Python test paketi 18 testi geçti ve kaynaklar derlendi. Ön yüz `npm run lint` komutunu uyarılarla tamamladı. Vite derlemesi, `frontend` dizininde seçilen Node 20.11 ile başarısız oldu; aynı derleme Node 22.12 ile geçti. Kurulum belgeleri Node sürümünü belirtmiyor.

Model tarafında 1X2 genel log-loss'u sınıf öncülünden iyi olsa da beraberlikleri ayırma gücü rastgele düzeye yakın. Over 2.5 ana holdout'ta sabit öncülü geçmiyor. Regresyon sonuçları hedefe göre değişiyor; kart tahmini ana holdout'ta ortalama baz çizgisinden kötü. Gelecek sezon kayıtlı tahminleri puanlamak için henüz sonuç yok.

En önemli mühendislik riskleri, dış ağa açılırsa kimlik doğrulaması olmadan veri güncellemesi başlatabilen yönetim endpoint'i, başlatıcıların portu kullanan herhangi bir süreci zorla öldürmesi, 1X2 dışındaki bazı tahmin yollarının eksik değerleri sessizce sıfırlaması ve sabit sezon/oyun haftası değerleridir. Değerlendirme testleri model matematiğinin temel özelliklerini kontrol ediyor; API endpoint'leri, veri eşitleme, tüm eğitim akışı ve arayüz için uçtan uca otomatik testler hâlâ yok.

## Denetim kapsamı ve doğrulama

Birinci taraf `src/`, `tests/` ve `frontend/src/` kodlarının envanteri yaklaşık **16.533 satır** gösteriyor. İnceleme veri alma, işleme, özellik üretimi, tüm model aileleri, değerlendirme yardımcıları, API/SQLite, analitik modülleri, React bileşenleri, testler ve rapor üreticilerini kapsadı. `node_modules`, `frontend/dist`, ham/işlenmiş veri dosyaları, SQLite ve ikili model artefaktları kaynak kodu denetiminin dışında tutuldu.

Bu çalışma canlı veri sağlayıcısına istek göndermedi. İlk kod denetimi pipeline'ı çalıştırmamıştı; sonraki 1X2 düzeltme turu pipeline'ı yerel ham veri önbelleğinden tamamladı. Kontroller:

| Kontrol | Sonuç |
|---|---|
| `PYTHONPATH=/private/tmp/codex-pytest-deps python3 -m pytest tests -q` | **18 geçti**, 14,25 saniye |
| `python3 -m compileall -q src run_full_pipeline.py start.py tests` | Başarılı |
| `python3 run_full_pipeline.py` | Başarılı; yerel veri, modeller ve benchmark raporu yenilendi |
| `npm run lint` (`frontend/`) | Başarılı çıkış; kullanılmayan importlar, hook bağımlılıkları ve effect içinde state güncellemeleri için çok sayıda uyarı |
| `npm run build` (`frontend/`, Node 20.11) | Başarısız: Node `node:util` içinden `styleText` dışa aktarmıyor; Vite/Rolldown sürümü bu Node sürümünü desteklemiyor |
| `npm --prefix frontend run build` (depo kökü, Node 22.12) | Başarılı; Vite 8.3.4, 1.915 modül derlendi |
| Yerel veri bütünlüğü hızlı kontrolü | 1.900 satır; yinelenen maç kimliği, boş veya sıfır kickoff zamanı görülmedi |

## Güncel model ve benchmark durumu

Tek güncel skor kaynağı [Model Benchmarks](model_benchmarks.md) raporudur. Holdout sonuçları seçilen eğitim prosedürünü ölçer; tüm veriyle yeniden fit edilen üretim artefaktının bağımsız testi değildir.

| Hedef | Güncel ölçüm | Yorum |
|---|---|---|
| 1X2 | 304 maç; log-loss **1,030** (sınıf prior **1,092**); Brier **0,621** (prior **0,661**); doğruluk **%48,68** | Genel olasılık skoru prior'dan iyi. Gerçek beraberlik oranı **%28,0**, ortalama P(draw) **%24,7**, draw AUC **0,5131** ve model yalnızca **1/304** maçta beraberliği en olası sınıf seçti. Beraberlik ayrımı çözülmüş değil. |
| Over 2.5 | 304 maç; kalibre log-loss **0,687**, prior **0,688**; eşleştirilmiş Δ **−0,0010**, %95 CI **[−0,0082, +0,0065]** | Ana holdout'ta ölçülebilir üstünlük yok; aralık sıfırı içeriyor. |
| Korner | RMSE **3,2198**, ortalama baz çizgi **3,2405** | Kazanç küçük. |
| Taç | RMSE **7,0675**, ortalama baz çizgi **7,3881** | Mevcut regresyon hedefleri içinde daha belirgin kazanım. |
| Kurtarış | RMSE **2,3785**, baz çizgi **2,3785** | Üretim tahmini `training_mean`. Etiketler olay akışıyla tüm 1.580 maça çıkarılmış olsa da özellik modeli beceri kapısını geçmedi. |
| Kart | RMSE **2,0298**, baz çizgi **2,0014** | CV kapısını geçmiş Ridge ana holdout'ta baz çizgiden kötü; bağımsız yeni maçlarla izlenmeli. |
| Ofsayt | RMSE **1,9043**, baz çizgi **2,0238** | Holdout'ta baz çizgiden iyi. |

Regresyon holdout'u 316 maç ve son sezonun 60 maçlık kısmi bölümünü içerir. 1X2 ve Over 2.5 sınıflandırıcı değerlendirmesi `2026_27` sezonunu kilitli tutar; bu 60 sonuç model seçimi/kalibrasyon/holdout puanlamasında kullanılmaz. Ana 1X2 split'i kickoff gruplarını korur; güncel feature/ensemble/recency kararları yalnız geliştirme döneminden alınır. Dixon–Coles ana kıyası aynı holdout ve aynı `2022_23` fit dışı kuralını kullanır. Ayrıntılı protokol ve sezon sonuçları benchmark raporundadır.

### Daha önceki model geliştirme kararları

Çalışma ağacında silinmiş olan model geliştirme kılavuzundan ve mevcut artefakt/raporlardan doğrulanabilen kararlar:

- **F4, 1X2 ensemble:** Geliştirmede yalnızca 1 temiz tam outer sezon kaldı; bu sezonda ensemble−lojistik log-loss farkı **+0,00211**. Üç sezon eşiği karşılanmadı; API üretim modeline alınmadı.
- **F5, beraberlik özellikleri:** Bir temiz tam outer sezonda log-loss farkı **+0,0047**, draw AUC farkı **+0,0168**. Log-loss kapısı geçmedi; dokuz özellik üretim sınıflandırıcısında açılmadı.
- **F6, zaman ağırlıklı kalibrasyon:** Tek temiz outer sezonda 150/300/600 satır yarı ömürleri **−0,00300 / −0,00201 / −0,00113** fark verdi; üç sezon koşulu karşılanmadığı için standart forward-OOF kalibrasyon devam ediyor.
- **F7, xG proxy:** Seyrek kapsamalı aggregate-stat proxy aktif model/API girdilerinden kaldırıldı. Depoda shot-level, eğitilmiş bir xG modeli yok.
- **F8, sayım modeli kapısı:** Korner (10 feature, `elastic_0.05_0.5`), taç (`poisson_10`), kurtarış (`training_mean`), kart (11 feature, rekabet dengesi/tansiyonu eklenerek `poisson_1`), ofsayt (10 feature, `ridge_250`) seçildi. Korner holdout R² değeri pozitife (+0.0071) döndü; kart modelinde hakem ve çekişme dengesi ağırlıklandırılarak test hatası ve çoklu bağlantı giderildi.
- **F9, kurtarış etiketi:** Eksik sağlayıcı değerleri takım tarafı belirlenebilen olaylarla tamamlandı; 1.580/1.580 maç etiketi kullanılabilir. Kaynak değerleri ve kurtarma işaretleri ayrıca saklanıyor.
- **F10, ileriye dönük kayıt:** Günlükte 100 tahmin var; son genişletilmiş kayıtların 40'ında gol marketleri bulunuyor. Bu 100 maçtan **0'ı** yerel maç tablosunda tamamlanmış durumda; `prospective_1x2_scorecard.json` henüz oluşmadı.

## Mimari ve kaynak haritası

| Katman | Ana dosyalar | Sorumluluk |
|---|---|---|
| Veri alma | `src/ingest/fetch_season_data.py`, `sync_season_data.py`, `fetch_team_staff.py` | PulseLive fikstür/istatistik/olay akışlarını önbelleğe alma ve artımlı eşitleme |
| İşleme | `src/processing/process_season_data.py`, `build_player_index.py` | Sağlayıcı JSON'unu maç, olay ve oyuncu tablolarına çevirme |
| Özellikler | `src/features/build_features.py`, `draw_features.py` | Geçmiş maçlardan pre-match rolling, Elo, dinlenme, hakem ve beraberlik özellikleri |
| Modeller | `src/models/train_*.py`, `goals_model.py`, `dixon_coles.py`, `model_utils.py` | 1X2, gol pazarı, skor matrisi ve beş sayım hedefini eğitme/değerlendirme |
| API ve depolama | `src/api/server.py`, `src/db/database.py` | FastAPI endpoint'leri, tahminler ve SQLite sorguları |
| Ürün arayüzü | `frontend/src/App.jsx`, `frontend/src/components/*.jsx` | Fikstür, tahmin, takım, oyuncu ve hakem panelleri |
| Rapor üretimi | `run_full_pipeline.py`, `src/analytics/*.py` | Model benchmark'ı, veri kalitesi, taktik kapsama ve senaryo raporları |

Özellik üretiminde ana yaklaşım doğru kurulmuş: takım formu mevcut maçtan önce kaydırılıyor, beraberlik özellikleri eşzamanlı kickoff sonuçlarını batch olarak güncelliyor ve eğitim ile canlı tahmin aynı feature yardımcılarını kullanıyor. Test açıklamaları da leakage kontrolünün sınırlı olduğunu açıkça belirtiyor; bu kontroller tam sızıntı kanıtı sayılmamalı.

## Bulgular ve öneriler

### Yüksek öncelik

1. **Yönetim veri eşitlemesi kimlik doğrulamasız.** `POST /api/admin/sync-season` arka planda dış kaynaktan veri çekip dosyaları ve SQLite'ı güncelliyor; endpoint'te kullanıcı doğrulaması yok. CORS da tüm origin'lere açık (`src/api/server.py`, middleware ve 379–397. satırlar). Başlatıcı API'yi localhost'a bağlasa da farklı bir dağıtım host'u dış ağa açabilir. Yönetim endpoint'ini yetkilendirin, origin listesini sınırlandırın ve üretimde yerel arayüz geliştirme ayarlarını kullanmayın.

2. **Başlatıcılar portu kullanan ilgisiz süreçleri zorla öldürüyor.** `start.sh` 8000/5173 portlarındaki bütün PID'lere `kill -9` gönderiyor; `start.py` de `SIGKILL` kullanıyor. Bu PID'lerin bu projeye ait olduğu doğrulanmıyor. Başlatıcıyı PID dosyası/proses grubu ile sınırlandırın; önce nazik kapatma ve açık çakışma mesajı kullanın.

### Orta öncelik

3. **Ön yüz Node sürümü kurulum talimatıyla uyumsuz.** [`package-lock.json`](../../frontend/package-lock.json#L2307) içindeki Vite/Rolldown motor koşulu Node `^20.19.0 || >=22.12.0`. `frontend/` dizinindeki `npm run build` denetim ortamının Node 20.11 sürümünde başarısız oldu. Node 22.12 ile derleme geçti. README'ye sürüm koşulu eklendi; ayrıca `frontend/package.json` içine `engines`, depo içine `.nvmrc`/`.node-version` eklemek ve CI'da aynı sürümü kullanmak önerilir.

4. **Bazı tahmin girdileri hâlâ varsayılan sıfırla dolduruluyor.** 1X2 tahminleri artık ortak `safe_feature_frame` helper'ında NaN'leri koruyarak `SimpleImputer`'a bırakıyor; helper testi eklendi. Diğer model aileleri varsayılan `0.0` politikasını sürdürüyor. Canlı/offline feature parity ve her model ailesinin eksik değer sözleşmesi için entegrasyon testi ekleyin.

5. **Fikstür tahminleri sabit oyun haftalarına bağlanmış.** Endpoint yorumu “current/upcoming gameweeks” dese de tahmini yalnızca `gw in [6, 7, 8]` için üretiyor (`src/api/server.py`, 659–660). Takvim ilerledikçe diğer yaklaşan haftaların tahmin alanı boş kalır. Güncel hafta ve bir sonraki N haftayı veri/ayar üzerinden belirleyin.

6. **Sezon kimliği kodun birçok katmanında sabit.** `2026_27` API varsayılanlarında, takım/puan tablosu özel dallarında, frontend isteklerinde ve SQLite referee aggregate listesinde yer alıyor. Yeni sezon eklenince tüm katmanların aynı anda güncellenmesi gerekiyor; aksi halde panel farklı veri dönemlerini gösterebilir. `CURRENT_SEASON`/veri manifesti gibi tek bir sezon keşif kaynağı kullanın ve API sezon parametrelerini doğrulayın.

7. **Python bağımlılıkları ve otomatik CI tanımlı değil.** Depoda `requirements*.txt`, `pyproject.toml` veya Python kilit dosyası bulunmuyor. Frontend'in lock dosyası var, ancak package script'lerinde test komutu yok. Bu nedenle Python sürümü/LightGBM/sklearn uyumu ve test kurulumu makineye bağlı. Sürüm sabitleyen Python bağımlılık dosyası, Node motor bildirimi ve CI adımları (pytest, compile, frontend lint/build, Markdown link denetimi) ekleyin.

8. **Otomatik testler API ve uçtan uca akışın küçük bölümünü kapsıyor.** Yedi test modülünde 18 test var. Yeni testler kickoff gruplu CV/holdout bölmelerini, feature-gate sezon eşiğini ve NaN/zero doldurma politikasını kapsıyor. Endpoint/DB, veri eşitleme, etiket parser'ı, tam offline/live feature parity, model eğitim pipeline'ı ve React bileşenleri hâlâ test edilmiyor. `test_team_tactics.py` ayrıca gerçek yerel 2026/27 verisindeki Arsenal kimliğine bağlı; sentetik fixture kullanımıyla ortamdan bağımsız hale getirin.

9. **Benchmark belirsizliği maç bazında IID bootstrap ile hesaplanıyor.** `paired_bootstrap_delta` maç satırlarını bağımsız örnekleyerek güven aralığı üretiyor (`src/models/eval_utils.py`, 34–64). Sezon/hafta içindeki ortak zaman etkileri bu aralıkta hesaba katılmıyor. Takvim haftası veya sezon bloklu bootstrap ekleyin; mevcut sonucu da match-IID olarak etiketleyin. Tek bir 304 maçlık holdout'tan çok sayıda model/politika karşılaştırması yapıldığı için seçilmiş sezon sonuçlarını yeni bağımsız test gibi yorumlamayın.

10. **Olay akışıyla hedef kurtarmada parser sessiz eksik sayım yapabilir.** `process_season_data.py` köşe/offsides/kart olaylarını metin kalıplarıyla takım tarafına atıyor. Tanınmayan metin sayacı artırmadan kalabilir; ancak olay akışı geçerliyse eksik alan kurtarılmış sıfır olarak işaretlenebilir. Şu an senaryo raporu aggregate tutarsızlıklarını kontrol ediyor, fakat olay başına ayrıştırma başarısızlığını açık bir kalite bayrağına dönüştürmek daha güvenli olur. Bilinmeyen metin/attribution oranını kaydedin ve eşik aşılırsa o metrik için fallback'i kapatın.

11. **Üretim artefaktı eksikliği uygulama açılışında doğrulanmıyor.** Model dosyaları bulunmazsa API değişkenleri `None` kalıyor; `/api/predict` içinde daha sonra artefakt sözlüğü gibi kullanılınca 500 hatası oluşuyor. Başlangıçta zorunlu artefaktları ve beklenen sürümlerini doğrulayıp açık bir health/status hatası verin.

### Kod bakımı ve ürün kalitesi

12. **Büyük modüller değişiklik riskini artırıyor.** `src/api/server.py` yaklaşık 1.850 satır; `train_match_outcome.py` 1.147 satır; `MatchDetailModal.jsx` 1.527, `TeamProfilesTab.jsx` 1.195 ve `FixturesTab.jsx` 921 satır. API endpoint'lerini router'lara, model değerlendirme protokollerini yardımcı paketlere ve büyük React panellerini veri/hooks/görünüm bileşenlerine ayırın.

13. **Ön yüz lint uyarıları temizlenmemiş.** Kullanılmayan ikon/yerel değişkenler var; `PredictorTab.jsx` ve `TeamProfilesTab.jsx` içinde hook bağımlılık uyarıları da mevcut. Eksik bağımlılıklar bazı state değişikliklerinde stale seçim/parametre kullanabilir. Basit unused kodu temizleyip hook bağımlılıklarını ve veri isteklerinde iptal/yarış davranışını gözden geçirin.

14. **İki veri alma yolu var.** Günlük API akışı `sync_season_data.py` üzerinden artımlı ve atomik JSON yazımlı. Eski `fetch_season_data.py` paralel worker'larla aynı `requests.Session` nesnesini paylaşabiliyor ve JSON dosyalarını doğrudan yazıyor. Tek desteklenen akışı açıkça belgeleyin veya eski akışa aynı güvenli yazım ve istek yaşam döngüsü kurallarını taşıyın.

15. **Benchmark ve tarihsel raporlar farklı güncelleniyor.** Tam pipeline benchmark ve bazı veri raporlarını üretirken 1X2 denetimi, proje özeti ve takip belgesi elle tutuluyor. `model_diagnostic_followup.md` içinde 1.200 maç/240 holdout gibi eski değerler bulunuyor; yeni okuyucu bunları güncel benchmark sanabilir. Bu raporun başına tarihsel olduğunu belirten not eklendi, ortak rapor envanteri kuruldu. Sonraki adım rapor metriklerini tek JSON/manifestten üretmek.

## Test ve benchmark boşlukları

| Alan | Şu an var | Eksik olan |
|---|---|---|
| Model kalitesi | Zaman sıralı CV, kronolojik holdout, sezon holdout'ları, calibration/Brier/log-loss, count RMSE/MAE, mean/prior baz çizgileri, skill gate |
| İstatistiksel belirsizlik | Eşleştirilmiş maç bazlı bootstrap | Hafta/sezon bloklu aralıklar, politika/özellik denemeleri için çoklu karşılaştırma kontrolü |
| Prospektif ölçüm | Artefakt parmak izli 100 maçlık kayıt; 100 kayıt kickoff öncesi | Sonuç gelmediği için skor kartı/gerçek performans yok |
| Python testleri | 18 test geçti; kickoff gruplama ve feature imputasyonu için yeni kontroller var | API/DB/ingestion/model pipeline regresyon testleri, fixture tabanlı leakage testi ve kapsama raporu |
| Frontend | Oxlint ve Vite build komutları | React testleri, erişilebilirlik/etkileşim testleri, API hata senaryoları |
| Performans | `/api/benchmarks` model metriklerini sunuyor | Endpoint gecikmesi, eşzamanlı istek, bellek ve senkronizasyon yük testi; bu uygulama performans benchmark'ı değil |

Model kalite kapıları regresyon adaylarını seçmede yararlı; fakat mevcut örneklem yalnızca dört tam sezondan oluşuyor. 1X2'nin en temiz bağımsız ölçümü, kilitli 2026/27 sezonu tamamlanıp tahmin günlüğü puanlandıktan sonra oluşacak. O zamana dek yeni politika seçimini aynı 2023/24–2025/26 dış sezonlarına göre tekrar tekrar yapmak seçim yanlılığı yaratabilir.

## Önceliklendirilmiş iyileştirme planı

### P0 — Erişim ve güvenli çalıştırma

1. Yönetim eşitleme endpoint'ine kimlik doğrulama/yetki ekleyin; CORS'u gerekli origin'lerle sınırlayın.
2. `start.sh` ve `start.py` porttaki bütün süreçleri öldürmesin; sadece kendi çocuk süreçlerini düzgün kapatsın.
3. Python bağımlılıklarını kilitleyin; Node için `engines` ve `.nvmrc`/`.node-version` belirleyin.

### P1 — Test edilebilir sözleşmeler

4. API boot-time artefakt kontrolü ve feature schema sürümü ekleyin; sessiz sıfır doldurmayı kaldırın.
5. Sezon ve oyun haftası seçimlerini tek veri kaynağından dinamik yapın.
6. Parser ve API için küçük sentetik fixture testleri; feature offline/live parity testi; en az bir tahmin endpoint smoke testi ekleyin.
7. CI'da Python testleri/compile ve Node lint/build'i aynı sabit sürümlerde çalıştırın.

### P2 — Model doğrulaması

8. Kilitli 2026/27 tahminlerini düzenli kaydedin; sonuçlar geldikçe `python3 -m src.analytics.prospective_1x2_benchmark score` çalıştırın. Yeni tahmin üretim anındaki artefaktı korusun.
9. Match-IID bootstrap'a sezon/hafta bloklu aralık ekleyin. Aynı outer seasons üzerinde defalarca denenmiş politika/özellik kararlarını bağımsız test diye sunmayın.
10. 1X2'de draw discriminative güç ve kalibrasyonunu ayrı kabul kriterleri yapın. Over 2.5 için modelin prior'a göre faydası prospektif örneklemde görülene kadar üstünlük iddiasında bulunmayın.
11. Kart modelinin holdout'ta ortalama baz çizgisini geçmediğini yeni maçlarda takip edin; bu holdout'u tekrar tekrar kullanarak hiperparametre seçmeyin.

### P3 — Bakım ve rapor üretimi

12. API, eğitim/değerlendirme ve React bileşenlerini görev sınırlarına göre bölün.
13. Raporların son güncelleme tarihi, veri snapshot kimliği, kod revizyonu ve artefakt parmak izini ortak manifestte saklayın.
14. Tarihsel raporları açıkça arşivleyin; tüm rapor bağlantılarını merkezi indeksten verin.

## Çalışma ağacı notu

Denetim başlamadan önce `git status` içinde `reports/model_improvement_guide.md` silinmiş olarak görünüyordu. Dosyayı geri yüklemedim; `PROJECT_STATUS.md` ve `1x2_model_audit.md` içindeki bu dosyaya giden bağlantılar yerine Rapor Merkezi ve bu denetim raporuna yönlendirdim. Git geçmişindeki sürüm korunuyor.
