# Project Status

**Snapshot:** 26 Ekim 2026  
**Belgeler:** [Veri kaynakları haritası](docs/data_sources.md) · [README](README.md) · [Rapor Merkezi](docs/reports/README.md) · [Ana Rapor](docs/reports/premier_league_models_comprehensive_report.md) · [Model Raporları](docs/reports/models/) · [Model Benchmarks](docs/reports/model_benchmarks.md)

---

## 1. Veri

| Kalem | Değer |
| :--- | :--- |
| Fikstür | 1.900 (5 sezon: 2022/23–2026/27) |
| Oynanmış maç | 1.600 · 2026/27: 80/380 (kilitli sezon, yalnızca raporlanır) |
| Sağlayıcı xG kapsamı (iki takım) | 2022/23 366/380 · 2023/24 378/380 · 2024/25 380/380 · 2025/26 380/380 · 2026/27 69/80 oynanmış |
| Özellik tablosu | `data/competitions/premier_league/processed/features_matches_all.parquet` (eğitim-tahmin XI mevki uyumu doğrulandı) |
| İleriye dönük tahmin kaydı | `data/competitions/premier_league/processed/1x2_forecast_log.jsonl`: 220 kayıt (15 oynanmış maç `docs/reports/prospective_1x2_scorecard.json` içinde puanlandı; scorecard 24 Ekim 2026) |

### Ulusal ligler (TheStatsAPI)

| Turnuva | Satır | Oynanmış | Durum |
| :--- | :--- | :--- | :--- |
| LaLiga (`competition_id` 140) | 2026/27: 380 (97 oynanmış; 240'ı takvimden yer tutucu); 2025/26: 380 | 477 | 2026/27 ve 2025/26 yüklü (künye, istatistik, kadro, oyuncu, olay akışı, şut haritası, oran, kadro/piyasa değeri); 2022/23-2025/26 indiriliyor, bitince `python3 -m src.ingest.load_thestatsapi_league --competition la_liga` ile yüklenir |

TheStatsAPI bir sezonun yalnızca yaklaşık 4 hafta ilerisini yayınladığı için (26/27'de 14 hafta, 140 maç), eksik haftalar openfootball takviminden yer tutucu olarak eklenir (saat belli olmayanlar yalnızca tarihle görünür); TheStatsAPI maçı yayınlayınca yer tutucu silinir. Ertelenen (iptal) maç takvimde kalır. Kimlikler başka kaynaklarla çakışmasın diye sağlayıcı numaraları kaydırılır (`match_id` +100.000.000, `team_id` +10.000.000). Maç saatleri diğer turnuvalar gibi Londra saatiyle gösterilir.

### Avrupa kupaları (yalnızca veri, model yok)

| Turnuva | Satır | Oynanmış | Kaynak |
| :--- | :--- | :--- | :--- |
| Şampiyonlar Ligi (`competition_id` 2) | 772 | 682 | UEFA herkese açık API (fikstür, sonuç, kadro, olay, puan durumu) + TheStatsAPI (istatistik, xG, oyuncu, şut haritası, kadro/piyasa değeri) |
| Avrupa Ligi (`competition_id` 3) | 804 | 714 | Aynı |

Sezonlar 2022/23–2026/27. 2022/23-2023/24 sekiz gruplu klasik grup aşaması, 2024/25'ten itibaren tek 36 takımlı lig aşaması (8 hafta) ve eleme turları. Eleme turları 9-13 sabit hafta numaralarını taşır. Oranlar yalnızca 2024/25 ve sonrası için çekildi. TheStatsAPI ayrıntısı 1.396 maç için (istatistik, kadro, oyuncu istatistiği, olay akışı, şut haritası); 2022/23 Avrupa Ligi'nde bir play-off maçı sağlayıcıda yok.

- Eksik `won_corners` değerleri olay akışından kurtarılır (68 takım değeri). Kurtarış hedefi de olay akışıyla 1.595 maçın tamamında kullanılabilir. Ham değerler ve kurtarma bayrakları ayrı tutulur.
- Gerçekleşmiş maç xG'si yalnızca gösterim ve maç sonrası analiz içindir; maç öncesi modellerde kullanılmaz, çünkü başlama saatinden sonra bilinir.
- Ayrıntı: [Data Quality](docs/reports/data_quality.md).

## 2. Modeller

| Model | Üretimde | Değerlendirme | Rapor |
| :--- | :--- | :--- | :--- |
| Gol skor matrisi (`v1.6`) | Bağımsız Poisson × Dixon-Coles, `full` 60 özellik (`exp_match_xg_10` ve `exp_venue_match_xg` dahil), α=3, w_dc=0.0; eğitim/değerlendirme/API'de 1X2'ye (`v1.3`) hizalı; O1.5, O2.5, O3.5 ve KG kalibratörleri aktif; KG etiketi kapalı | Skor NLL 2.9686 (v1.5: 2.9737, v1.4: 2.9786); O2.5 LL 0.6767 (haftalık refit 0.6753), Δ prior −0.0080 CI [−0.0156, −0.00001] (3/3 negatif sezon); KG LL 0.6804 | [goals_model.md](docs/reports/models/goals_model.md) |
| 1X2 (`v1.4`) | 74 özellikli lojistik (C=0.003; penaltı arındırılmış `npxG` + `npBC` + `sdiff_pa_entries_e02/r10` ve İlk 11 dakika ağırlıklı istikrar/eksik as oyuncu farkları `xi_continuity_diff`, `xi_weighted_ov_diff`, `missing_reg_mins_diff` eklendi) + ayrıştırılmış L2 cezalı OOF sıcaklık/bias kalibrasyonu (`reg_temp=0.10, reg_bias=0.50`) | 3 dış sezon (`N=1,140`) Pooled LL 0.9732 (v1.3: 0.9746, v1.2: 0.9757, v1.1: 0.9789), Brier 0.5790, RPS 0.1977, CV LL 0.9674; 304 maç holdout LL 1.024 (`1.0240`) vs 1.092, Brier 0.616, RPS 0.2073, Acc %50.33 | [outcome_1x2_model.md](docs/reports/models/outcome_1x2_model.md) |
| Korner | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE 3.235) | [corners_model.md](docs/reports/models/corners_model.md) |
| Taç | `poisson_10` | RMSE 6.941 vs 7.337; geliştirme dış sezon 2/2 | [throws_model.md](docs/reports/models/throws_model.md) |
| Ofsayt | `ridge_250` | RMSE 1.906 vs 2.013; geliştirme dış sezon 2/2 | [offsides_model.md](docs/reports/models/offsides_model.md) |
| Kart | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE 1.992) | [cards_model.md](docs/reports/models/cards_model.md) |
| Kurtarış | `training_mean` | CV kapısı 2/4 kat → ortalama (holdout RMSE 2.348) | [saves_model.md](docs/reports/models/saves_model.md) |

Artifact tarihleri: tüm modeller 24 Ekim 2026, o günkü özellik tablosuyla (1.595 maç) eğitildi; bu oturumda yalnızca dizinleri taşındı (`models/production/premier_league/`), yeniden eğitilmedi. Üretim modeli Premier League ve LaLiga için vardır; Şampiyonlar Ligi ve Avrupa Ligi yalnızca veri gösterir.

## 3. Son Değişiklikler (26 Ekim 2026)

- **LaLiga sayım modelleri ve hakem özellikleri (26 Ekim 2026):** `src/models/train_league_counts.py` korner, taç, ofsayt, kart ve kurtarış modellerini PL'nin kendi seçim kodu ve kapılarıyla (`train_count_model`) LaLiga verisiyle eğitir; özellik üretici `build_league_features.py` sayım geçmişlerini ve hakem ortalamalarını ayrı sütun kümesi (`count_feature_columns`) olarak üretir, 1X2 modelinin 118 özelliği değişmedi. Sonuç: taç modeli kapıyı geçti, diğer dördü `training_mean`. API bu modelleri `predict_count_market` ile servis eder. Rapor: [la_liga_counts.md](docs/reports/models/la_liga_counts.md), ham sayılar `la_liga_count_models.json`.
- **Kod tabanı sadeleştirme:** `src/core/` (kopya) kaldırıldı; `src/models/` ve `src/features/` tek kaynak. `apply_fdr`, `benjamini_hochberg`, `with_inference` `src/models/eval_utils.py`'ye taşındı; tüm `src.core` import'ları güncellendi. Eski `data/processed`, `data/raw` ve `models/production/*.joblib` takipten çıkarıldı (yeni yer: `data/competitions/<anahtar>/`, `models/production/<anahtar>/`). `research/scratch/*` betikleri de yeni yollara taşındı; kodda eski yol kalmadı (`premier_league.db` yedeği 2026-10-26 kaldırıldı; sunucuda DB `football.db` olmalı).

- **Turnuva bazlı dizin düzeni:** Veri ve modeller artık turnuva anahtarıyla ayrıldı: `data/competitions/<anahtar>/{raw,processed}/` ve `models/production/<anahtar>/` (Premier League: `premier_league`). Ortak SQLite artık `data/football.db` (eski adı `premier_league.db` yanıltıcıydı; eski ad yedeği sonradan kaldırıldı); satırlar `competition_id` taşır. Avrupa kupalarının ham sağlayıcı yanıtları (UEFA fikstür ve puan durumu, TheStatsAPI maç ve sezon verisi) `data/competitions/<anahtar>/raw/<sağlayıcı>/` altında dosya olarak da tutulur; mevcut veriler `export_competition_raw` ile dışa aktarıldı, sonraki senkronizasyonlar dosyaları kendisi yazar. Turnuvalar arası maç kimliği çakışması `sync_competition_data` içinde engellenir. Yollar `src/config.py` içindeki `competition_paths(anahtar)` ile alınır; eğiticiler tanı JSON'larını kendi turnuvalarının klasörüne yazar (başka turnuvanın dosyasını ezmez). Taşıma öncesi yedek alındı; tüm testler ve gerçek veriyle API uçları taşıma sonrası doğrulandı. Ayrıntı: [scripts_reference](docs/scripts_reference.md) §0.
- **Avrupa kupaları gerçek veriye bağlandı:** Sahte (rastgele üretilmiş) veri silindi; UEFA ve TheStatsAPI'den fikstür, sonuç, kadro, maç istatistiği, xG, oyuncu verisi, olay akışı ve şut haritası çekildi. Turnuva ağacı, grup puan durumu ve takım/oyuncu/hakem profilleri turnuva bazlı çalışır; PL takım, oyuncu ve hakem sayfalarında Avrupa maçları da görünür.
- **Avrupa kupaları için tahmin modeli kurulup kaldırıldı:** Yürüyen pencere (walk-forward) hücum/savunma modeli sızıntısız protokolle sınandı (ayar 2023/24-2024/25, sınama 2025/26, izleme 2026/27). Sonuç: taban orandan anlamlı iyi, ülke öncüllü basit Elo'dan ayırt edilemez, piyasadan anlamlı kötü; sayım pazarlarında kazanç yok denecek kadar az. Bu yüzden Şampiyonlar Ligi ve Avrupa Ligi'nde tahmin sunulmuyor. Model Doğrulama sekmesi ve maç detayındaki tahmin sekmesi bu turnuvalarda gizli; `/api/predict` PL dışı takım için 404 verir. Önceki rastgele "tahmin" ve denetim kodu da kaldırıldı.
- **Hata düzeltmeleri:** `pipeline_health` artık yalnız PL satırlarını sayar (Avrupa maçlarını "özelliklerde eksik" saymıyordu); işleme hattının PL satırlarını yanlış `competition_id` ile ezme riski kaldırıldı ve test edildi.
- **LaLiga eklendi (uçtan uca):** `config/competitions.yaml` girdisi (kimlik 140, bölgeler: 1-4 Şampiyonlar Ligi, 5 Avrupa Ligi, 18-20 küme düşme), TheStatsAPI ingest katmanı (`fetch_thestatsapi_league` indirir, `load_thestatsapi_league` ağ kullanmadan veritabanına yükler, ham yanıtlar `data/competitions/la_liga/raw/thestatsapi/` altında), TheSportsDB'den 29 kulüp rozeti ve lig logosu, TheStatsAPI tabanlı maç sayfası (`statsapi_match_details`). LaLiga takım sayfalarında Şampiyonlar Ligi/Avrupa Ligi maçları, hakem ve oyuncu sayfalarında Avrupa bölümü görünür. Tahmin modeli sonradan eklendi (aşağıda).
- **LaLiga modeli (26 Ekim 2026):** Walk-forward 1X2 ve gol modeli (`train_league_model`, rapor: [la_liga_outcome.md](docs/reports/models/la_liga_outcome.md)). İki dış sezonda (760 maç) taban orandan anlamlı iyi, Elo referansından ayırt edilemez (her sezonda ortalamada önde), piyasadan daha kötü; kapı kuralı modeli seçti. Sayım modelleri (`train_league_counts`, rapor: [la_liga_counts.md](docs/reports/models/la_liga_counts.md)) PL ile aynı kapıdan geçirildi: yalnızca taç kapıyı geçti (holdout RMSE 7,39, ortalama 9,15); ofsayt CV'de önde ama dış sezon kapısında 1/2 ile kıl payı elendi; korner, kart ve kurtarış `training_mean` (`baseline` etiketli). Hakem ortalamaları (kart, faul) LaLiga verisinden hesaplanır. Maç sayfasında tahmin, Model Doğrulama sekmesinde LaLiga denetimi açık. Beş sezon (1.900 maç, 2026/27'de takvimden yer tutucular dahil) yüklü.
- **Güncel hafta (lig dışı turnuvalar):** Ertelenen bir maç eski bir haftayı aylarca "oynanmamış" bırakıyordu; PL dışındaki turnuvalarda güncel hafta artık takvimde geride kalmamış ilk oynanmamış maçın haftasıdır (LaLiga'da 10. hafta; ertelenen Rayo - Athletic maçı 8. haftada takvimde kalır).
- **Veri güncelle düğmesi turnuva bazlı:** Düğme eskiden hangi ligde olursan ol Premier League script'ini çalıştırıyordu. Artık `competition` parametresiyle seçili turnuvanın boru hattını çalıştırır (`sync_competition`: TheStatsAPI ligi için eksikleri indirip yükler, UEFA kupası için UEFA'dan fikstür/sonuç ve anahtar varsa TheStatsAPI ayrıntısı); menü yalnızca o turnuvanın desteklediği türleri gösterir. Sunucu işlemi `THESTATSAPI_API_KEY` ortam değişkenini görmelidir.
- **Arayüz yetenek bayrakları:** Turnuvalar `kind` (lig/kupa), `hasModel`, `richData`, `syncKinds` ile tanımlanır; sekmeler turnuva adına değil bu bayraklara bakar, yeni bir lig aynı sayfaları otomatik alır.
- **Yeni lig hazırlığı (ablasyon):** PL 1X2 modelinde sağlayıcıya özgü ceza sahası giriş ve dokunuş özelliklerinin çıkarılması dış sezonlarda ölçülebilir kayıp vermedi (toplu log-loss farkı ≤ 0.0009, hiçbiri anlamlı değil). Ayrıntı: [yeni lig hazırlığı](docs/reports/experiments/2026-10-25_new_league_readiness.md).
- **Doküman senkronu kuralı:** `AGENTS.md` ve üç skill dosyası, her ekleme/değişiklik/silme sonrası ilgili belgelerin kullanıcı istemeden güncellenmesini zorunlu kılar (değişiklik türü → güncellenecek belgeler tablosu). `tests/test_docs.py` bunu kısmen otomatik denetler: her turnuva `docs/data_sources.md`'de olmalı, her veri aracı `src.ingest` dizininde listelenmeli, her script `scripts_reference.md`'de yer almalı, buradaki test sayısı gerçek sayıyla eşleşmeli.
- **Kaynak haritası ve yardım metinleri:** `docs/data_sources.md` hangi turnuva için hangi verinin nereden, hangi script'le ve nereye geldiğini, dış servis sınırlarını, karar günlüğünü ve yeni script kataloğunu içerir. Tüm veri araçlarının `--help` çıktısı kullanım, girdi, çıktı ve gereksinimi anlatır; `python3 -m src.ingest --help` hepsini tek yerde listeler.
- **Testler:** 234/234 geçiyor.

### 24 Ekim 2026

- **Kod tabanı ve model metodolojisi denetimi (`K1–K9`):**
  - **1X2 ensemble kapısı (`K1`):** `ensemble_gate_passed` doğrudan dış-sezon kapısına bağlandı (`False`); harman ağırlığı `choose_blend_weight` çıktısından alınıyor; kullanılmayan `model_o25` çıkarıldı.
  - **Hibrit `/api/model-audit` (`K2`):** `1x2_forecast_log.jsonl` içindeki maç öncesi kayıtlar `prospective`, geçmiş maçlar `in_sample_backfill` olarak ayrıştırıldı; prospektif kayıtlar ezilmiyor.
  - **Goals hizalı kalibrasyon ve değerlendirme (`K3`, `K7`):** O/U ve KG kalibratörleri ile dış-sezon değerlendirmesi, API ile birebir aynı şekilde 1X2-hizalı skor matrisi üzerinde çalışıyor; `rho` parametresi OOF/harmanlanmış $\lambda$'lar üzerinde `sample_weight` ile tahmin ediliyor; `skill_gate` değerlendirmeden dinamik türetiliyor. Skor NLL `2.9786 -> 2.9737`, O2.5 LL `0.6774 -> 0.6765`, ECE `%5.07 -> %3.99` iyileşti.
  - **Sayım modelleri metodolojisi (`K4`, `K6`):** NB2 dispersiyonu ($\alpha$) koşullu model artıklarından (residuals) tahmin ediliyor; dış-sezon kapısı `%20` test holdout dönemine sızmadan yalnızca `%80` geliştirme dönemindeki tam sezonları kullanıyor (bunun sonucunda korner modeli `1/2` dış sezonla `training_mean`'e çekildi); tüm sayım modelleri `CountModelSpec` ve `fill_value=np.nan` (`SimpleImputer`) ile birleştirildi.
  - **Eğitim–tahmin XI mevki uyumu (`K5`):** `build_features.py` ve `sync_prematch_lineups.py` maç günü mevkisini (`load_official_match_starters`) kullanacak şekilde eşitlendi; 140 model sütununun tamamı `tests/test_train_serve_parity.py` ile doğrulandı.
  - **Birleşik tahmin servisi ve API temizliği (`K8`, `K9`):** Tüm tahmin akışı `src/api/prediction_service.py` altında toplandı; `state.py` içinde `corner`, `throws`, `saves` yeniden yükleme listesine eklendi; `/api/benchmarks` artık `cards` ve `goals` metriklerini de döndürüyor.
- **Testler:** o gün 103/103 geçiyordu.

## 4. Bilinen Sınırlar

- **Gol modeli** takım güç farkını yakalıyor (gol farkı korelasyonu 0.44) ama toplam gol hacmini neredeyse hiç ayırt edemiyor (0.065). Sabit Poisson'a karşı farkı anlamlı değil; bahis edge'i iddiası için temel oluşturmaz.
- **1X2 modeli** genel beraberlik oranını biliyor ama beraberliği maç maç ayıramıyor (beraberlik olasılığı, beraberlikle biten maçlarda %25.7, diğerlerinde %24.9).
- **Sayım modellerinin** ortalamaya karşı kazancı yalnızca taç ve ofsaytta dış-sezon kapısını geçiyor; korner, kart ve kurtarış dürüst `training_mean` baseline'ında.
- **API'de model olmayan alanlar:** `shots.expected_total` sabit çarpandır (`kurtarış × 4.1`) ve API'de `model_skill: "heuristic_from_saves"` olarak açıkça etiketlenir. Ev/deplasman paylaşımları rolling oranlardan gelir. Bkz. [API Entegrasyonu §2.6](docs/model_api_integration.md).
- **İleriye dönük kayıt:** `docs/reports/prospective_1x2_scorecard.json` ilk 15 tamamlanmış prospektif maç için üretildi; örneklem büyüdükçe istatistiksel güç artacak.

## 5. Çoklu Lig Mimari Altyapısı (Multi-League Readiness)

- **Turnuva Kayıt Defteri (`config/competitions.yaml`):** Premier League (39), Şampiyonlar Ligi (2), Avrupa Ligi (3); biçim, sağlayıcı ve sezon varsayılanları burada.
- **Dizin düzeni:** Her turnuva kendi `data/competitions/<anahtar>/` ve `models/production/<anahtar>/` klasörlerine sahip (bkz. §3). Özellik üretimi (`build_features`) ve iki eğitici (`train_match_outcome`, `train_goals`) `--competition` alır.
- **Ortak Motor Katmanı (`src/models/`):** Dixon-Coles, Poisson/gol modelleri, sayım modelleri ve değerlendirme metrikleri ligden bağımsız; PL ve La Liga aynı modülleri kullanır (eski `src/core/` kopyası kaldırıldı 2026-10-26).
- **Sağlayıcılar (`src/ingest/`):** PulseLive (Premier League), UEFA herkese açık API (Avrupa kupaları fikstür/olay), TheStatsAPI (istatistik, xG, oyuncu, oran; her lig için). Yeni bir lig için TheStatsAPI örneği çekilip hangi özelliklerin üretilebildiği ölçülmeli.
- **Veritabanı:** `matches.competition_id` (varsayılan 39), grup, tur, ayak ve penaltı sütunları; `external_match_payloads` ve `external_competition_payloads` ham sağlayıcı çıktıları.
- **Henüz hazır olmayanlar (model eğitimi için):** ulusal ligin maçlarını PL'nin özellik hattının beklediği tablo biçimine (`matches_summary`) çeviren adım, sayım modellerinin ve `run_full_pipeline.py`'nin turnuva parametresi, API'de turnuvaya göre model seçimi, `LOCKED_SEASONS`'ın turnuva bazlı tanımı. Veri gösterimi için her şey hazır. `src/competitions/normalizer.py` şu an hiçbir modelde kullanılmıyor.

## 6. Sıradaki İşler

1. Her oyun haftasından sonra `python3 run_full_pipeline.py` çalıştır, ardından API'yi yeniden başlat. Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_*.md`) bu sırada yenilenir.
2. Maç öncesi tahmin kaydını sürdür (`prospective_1x2_benchmark snapshot`) ve biten maçları puanla. Kısmi sezona bakarak modeli tekrar tekrar ayarlama.
3. Korner, ofsayt ve taç modellerine kart modelindeki gibi derin denetim yap: özellik ablasyonu, kazancın "seviye uyumu" ile "maçlar arası ayrım" arasında ayrıştırılması.
4. LaLiga modeli: özellik azaltma ve daha zayıf düzenlileştirme (seçilen C ızgara kenarında) için yeni protokol; ilk 11 ve oyuncu rating özellikleri; sayım pazarı modelleri.
5. 1X2 denetimini güncel artifact (74 özellik) üzerinde yenile; [1x2_model_audit.md](docs/reports/1x2_model_audit.md) 14 Ekim tarihli.
5. Python bağımlılıklarını bir `requirements.txt` dosyasına sabitle; `pytest`'i geliştirme bağımlılığı olarak ekle.
6. Kart hedefinde `total_yellow_cards_target_usable` bayrağının eğitimde filtrelenmesi gerekip gerekmediğini doğrula.
