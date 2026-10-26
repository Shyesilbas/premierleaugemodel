# Script Referansı

Projedeki tüm çalıştırılabilir script ve modüllerin ne işe yaradığı. Kaynak: her dosyanın docstring'i ve fonksiyon listesi. Hangi dosyaların listelendiği `tests/test_docs.py` ile denetlenir (yeni dosya eklenip burada geçmezse test kırılır); açıklamaların içeriği satır satır doğrulanmadı. `node_modules`, `frontend/src` (React bileşenleri) ve `graphify-out` kapsam dışı.

Tipik veri akışı: **ingest** (ham JSON indir) → **processing** (Parquet/SQLite) → **features** (sızıntısız özellikler) → **models** (eğitim) → **api** (servis) → **frontend**.

Turnuva başına veri kaynakları: [data_sources.md](data_sources.md). Tüm veri çekme araçlarının listesi: `python3 -m src.ingest --help`.

## 0. Yapılandırma ve ortam değişkenleri

`src/config.py` projedeki tüm yolların ve sezon politikasının tek kaynağıdır (`ROOT`, `DATA_DIR`, `COMPETITIONS_DIR`, `DB_PATH`, `MODELS_ROOT`, `REPORTS_DIR`, `LOCKED_SEASONS`, `EXCLUDED_1X2_TRAINING_SEASONS`). Bir turnuvanın klasörlerine `competition_paths("la_liga")` ile ulaşılır; `RAW_DIR`, `MATCHES_RAW_DIR`, `PROCESSED_DIR`, `FEATURES_PATH`, `MATCHES_SUMMARY_PATH`, `MODELS_DIR` sabitleri Premier League'in yollarıdır.

### Dizin düzeni (turnuva bazlı)

```
data/football.db                          ortak SQLite (ayrıştırılmış satırlar); her maç satırı competition_id taşır (39 PL, 2 UCL, 3 UEL)
data/competitions/<anahtar>/raw/          sağlayıcıdan inen ham dosyalar. Premier League: fixtures_<sezon>.json, matches/<id>_*.json (PulseLive).
                                          Avrupa kupaları: <sağlayıcı>/fixtures_<sezon>.json, standings_<sezon>.json, matches/<id>_<tür>.json, competition/<sezon>_<tür>.json (uefa, thestatsapi)
data/competitions/<anahtar>/processed/    parquet tabloları, özellikler, değerlendirme JSON'ları, tahmin günlüğü
models/production/<anahtar>/              o turnuvanın eğitilmiş .joblib dosyaları
models/backup/<anahtar>/                  eski sürüm yedekleri
```

Bir turnuvanın eğitimi yalnızca kendi klasörlerini okur ve yazar. `train_match_outcome` ve `train_goals` `--competition` ile çalışır ve tanı JSON'larını o turnuvanın `processed/` klasörüne yazar.

| Değişken | Etkisi |
|---|---|
| `PLM_DATA_DIR` | Veri dizinini (`competitions/`, SQLite) değiştirir; pipeline'ı izole bir veri kopyasında çalıştırmak için. Varsayılan `<repo>/data`. |
| `PLM_SEASON` | Betiklerin varsayılan sezonu. Verilmezse `data/competitions/premier_league/raw/fixtures_*.json` içindeki en yeni sezon (`config.DEFAULT_SEASON`); tüm önbellek sezonları `config.SEASONS`. |
| `PLM_ADMIN_TOKEN` | Tanımlıysa `/api/admin/*` uçları (senkron başlat/durum, model yenile) `X-Admin-Token` başlığında bu değeri ister (ASCII, örn. `openssl rand -hex 24`); tanımsızsa uçlar açık kalır ve bir kez uyarı loglanır. **Sunucuda `/opt/plm/.env` içine ekleyin.** Arayüz jetonu `localStorage.setItem('plm_admin_token', '<jeton>')` ile okur. |
| `PLM_CORS_ORIGINS` | API'yi tarayıcıdan çağırabilecek kökenler (virgülle). Varsayılan yerel geliştirme sunucuları (`localhost:5173`, `localhost:8080`); `*` artık varsayılan değil. Aynı kökenden gelen trafik (Vite proxy, Caddy) CORS gerektirmez. |
| `PLM_REPORTS_DIR` | Üretilen raporların (`data_quality.md`, `prospective_1x2_scorecard.json` ...) yazıldığı dizin. Varsayılan `docs/reports`. İzole denemelerde gerçek raporları ezmemek için. |
| `PLM_MODELS_ROOT` | Tüm turnuvaların model kökünü değiştirir. Varsayılan `<repo>/models/production`. |
| `PLM_MODELS_DIR` | Yalnızca Premier League'in model klasörünü değiştirir. Varsayılan `<repo>/models/production/premier_league`. |

Örnek: `PLM_DATA_DIR=/tmp/veri python3 -m src.processing.process_season_data --season-name all`.

## 1. Kök dizin

| Dosya | Ne yapar |
|---|---|
| `start.py` | Backend (uvicorn, `:8000`, `--reload`) ve frontend'i (Vite, `:5173`) birlikte başlatır, Ctrl+C ile ikisini kapatır. Başlamadan önce portlarda **bu projenin** eski sürecini kapatır; başka bir uygulama varsa dokunmadan durur (`--force` ile kapatır). |
| `start.sh` | `start.py`'yi çağıran ince sarmalayıcı (`exec python3 start.py "$@"`). |
| `run_full_pipeline.py` | Ana pipeline, **aşamalı**: `rebuild` (işleme → oyuncu dizini → özellikler → veritabanı), `audits`, `counts` (köşe, atış, kurtarış, kart, ofsayt), `outcome` (1X2), `goals` (değerlendirme + eğitim). `--only goals`, `--skip rebuild,audits`; geçersiz aşama çıkış 2, hatada çıkış 1. Sağlayıcıya bağlanmaz. |

## 1c. Çoklu turnuva altyapısı

`config/competitions.yaml` turnuvaları (Premier League, Champions League, Europa League) ve sağlayıcılarını tanımlar. UCL/UEL fikstür ve sonuçları UEFA'nın herkese açık, anahtarsız maç API'sinden gelir; `python3 -m src.ingest.sync_competition_data --competition champions_league` (veya `europa_league`) `matches` tablosuna yalnızca o turnuvanın satırlarını yazar. Veri yoksa arayüz boş durum gösterir. Maç istatistikleri, xG, oyuncu ve oran verisi TheStatsAPI'den gelir (`python3 -m src.ingest.sync_thestatsapi_competition`); tahmin modeli bu turnuvalar için yoktur (denendi, sızıntısız sınamada ülke öncüllü Elo'dan ayırt edilemedi ve piyasadan kötüydü).

| Dosya | Ne yapar |
|---|---|
| `src/competitions/registry.py` | `config/competitions.yaml` ve `priors.yaml` dosyalarını okuyup turnuva kayıt defterini sunar. |
| `src/competitions/normalizer.py` | Turnuvalar arası istatistik normalizasyonu. |
| `src/ingest/base_provider.py` | Veri sağlayıcıları için soyut taban sınıf. |
| `src/ingest/provider_factory.py` | Turnuvaya uygun sağlayıcı istemcisini (PulseLive veya API-Football) üretir. |
| `src/ingest/providers/pulselive.py` | Premier League için PulseLive sağlayıcısı. |
| `src/ingest/providers/uefa.py` | UCL/UEL için UEFA maç API'si sağlayıcısı: lig aşaması ve eleme turlarını, hakem, stadyum ve takım logo URL'lerini getirir; ön eleme turlarını atlar. |
| `src/api/competition_squads.py` | UCL/UEL kulüpleri için saklanan TheStatsAPI verisinden kadro, takım piyasa değeri, oyuncu sezon toplamları, oyuncu dizini/profili ve teknik direktörleri üretir; eşleşmeyen kulüp için boş döner, tahmin üretmez. |
| `src/api/competition_stats.py` | UCL/UEL istatistikler sekmesini saklanan TheStatsAPI verisinden kurar (golcüler, oyuncu notları, hücum/savunma, kaleciler, hakemler); ortak `build_league_stats` üreticisine PL biçiminde veri çevirir. |
| `src/api/european_fixtures.py` | Premier Lig kulübünün takım profili fikstürüne UCL/UEL maçlarını ekler: kulüpleri UEFA ID'leriyle isimden eşler (veri yeniden çekilmez), maçı kulüp açısından çevirir, turnuva/tur etiketi ve kick-off zamanı ekler. Lig rekoru yalnızca PL maçlarından hesaplanır. Aynı modül PL hakemlerinin Avrupa maçlarını (isimden eşleşir, kart/faul yalnızca istatistiği olan maçlardan) ve PL oyuncularının Avrupa maç kayıtlarını (kulüp içinde isimle eşleşir) verir. |
| `tests/test_cli_help.py` | Veri araçlarının `--help` çıktısının çalıştığını, kullanım/girdi/çıktı/gereksinim anlattığını, `python3 -m src.ingest` dizininin tüm araçları listelediğini ve `docs/data_sources.md`'nin hepsinden bahsettiğini doğrular. |
| `tests/test_thestatsapi_league.py` | Kimlik aralıkları, fikstür satırı, kısaltmalar, kayıt defteri girdisi ve zaman akışı (gol, kendi kalesine, penaltı, değişiklik eşleme) testleri. |
| `tests/test_raw_store.py` | Ham dosya yollarının turnuva ve sağlayıcı bazlı ayrımı, atomik yazma ve turnuvalar arası maç kimliği çakışma koruması. |
| `tests/test_european_fixtures.py` | Bu birleştirmenin çevrimdışı ve API testleri. |
| `src/api/knockout.py` | UCL/UEL eleme turlarında maçları eşleşmelere (tie) toplar: iki ayağın toplam skoru, turu geçen takım ve nedeni (toplam skor/uzatma/penaltı), maç kartları için özet ve turnuva ağacı yerleşimi (`/api/fixtures/bracket`). |
| `tests/test_knockout.py` | Eleme eşleşmesi toplama ve ağaç sıralamasının çevrimdışı testleri. |
| `src/api/uefa_match_details.py` | UCL/UEL maç detayı: UEFA kadro ve olay akışından kadro, gol/kart/değişiklik zaman akışı ve olay sayımına dayalı takım istatistikleri (şut, korner, faul, ofsayt, kurtarış, kart) üretir; xG, pas ve topa sahip olma bu akışta yoktur. |
| `tests/test_uefa_match_details.py` | UEFA maç detayı üreticisinin çevrimdışı testleri. |
| `src/ingest/sync_thestatsapi_competition.py` | UCL/UEL için TheStatsAPI'den (`THESTATSAPI_API_KEY`, yalnızca ortam değişkeninden; dakikada 100 istek) oynanmış maçların takım istatistiklerini, kadrolarını, oyuncu istatistiklerini, olay akışını, şut haritasını ve oranlarını ham olarak `external_match_payloads` tablosuna, xG'yi `external_match_xg`'ye, toplamları `matches` satırına yazar; ayrıca puan durumu ve kadroları `external_competition_payloads`'a alır. Yeniden çalıştırılabilir: kayıtlı veriler atlanır, `--refresh` ile yeniden çeker. **Oranlar 2024/25'ten itibaren çekilir, 2023/24 ve öncesinde atlanır** (`--include-odds` ile açılır). |
| `tests/test_statsapi_competition_sync.py` | TheStatsAPI senkronunun ve maç detayı katmanının çevrimdışı testleri. |
| `src/ingest/providers/thestatsapi_league.py` | TheStatsAPI'yi ulusal ligin fikstür kaynağı yapar (LaLiga ve aynı yolla eklenen ligler): sağlayıcı kimliklerini yerel tamsayı aralıklarına kaydırır (`match_id` +100.000.000, `team_id` +10.000.000), Londra saatiyle etiket üretir, 3 harfli kısaltma ve rozet yolunu bulur. |
| `src/ingest/fetch_thestatsapi_league.py` | Bir ulusal ligin fikstür listesini, bitmiş maçların 7 türdeki yanıtlarını (maç, istatistik, kadro, oyuncu istatistiği, zaman akışı, şut haritası, oran) ve kulüp kadro/sezon istatistiklerini `data/competitions/<anahtar>/raw/thestatsapi/` altına indirir. Var olanı atlar, 100 istek/dakika sınırını aşmaz; oranlar yalnızca 2024/25'ten itibaren (`--old-extras` eski sezonlar için de çeker); şut haritası hiçbir sezon için çekilmez. Anahtar yalnızca ortam değişkeninden. |
| `src/ingest/fetch_openfootball_schedule.py` | Ligin tam sezon takvimini openfootball'dan (kamu malı, anahtarsız) `raw/openfootball/` altına indirir. TheStatsAPI yalnızca yaklaşık 4 hafta ilerisini yayınladığı için, yayınlanmamış haftalar bu takvimden yer tutucu maç olarak eklenir; sağlayıcı o maçı yayınlayınca yer tutucu gerçeğiyle değişir (`schedule_source` alanı `competitions.yaml`'da). |
| `src/ingest/load_thestatsapi_league.py` | Yukarıdaki ham dosyaları ağ kullanmadan ortak veritabanına yükler: maç satırları, ham yanıt kayıtları, maç toplamları (korner, şut, kart, xG), oranlar, kadro/takım istatistikleri ve teknik direktörler. Tekrar çalıştırılabilir. |
| `src/ingest/sync_competition.py` | "Veri güncelle" düğmesinin Premier League dışındaki turnuvalar için çalıştırdığı boru hattı: TheStatsAPI ligi için eksik dosyaları indirir ve yükler; UEFA kupası için fikstür, sonuç ve resmi tabloyu UEFA'dan (anahtar varsa TheStatsAPI ayrıntısını) tazeler. Turnuva başına kilit kullanır; son satırda `SYNC_RESULT` yazar. |
| `src/ingest/fetch_team_badges.py` | Bir turnuvanın kulüp rozetlerini TheSportsDB'den `frontend/public/badges/<anahtar>/<takım id>.png` olarak indirir; eşleşmeyenleri tahmin etmez, listeler. |
| `src/api/statsapi_match_details.py` | Yalnızca TheStatsAPI ile beslenen liglerde maç sayfası: kadro ve zaman akışından (gol, penaltı, kart, değişiklik çiftleri, uzatma) temel yapıyı kurar, istatistik/rating/şut/oran katmanını UEFA maçlarıyla ortak olarak ekler. |
| `src/ingest/__main__.py` | `python3 -m src.ingest --help`: tüm veri çekme araçlarının tek satırlık dizini. |
| `src/features/build_league_features.py` | TheStatsAPI ligleri (LaLiga) için maç öncesi özellikler: Elo, puan/averaj, xG, şut, büyük şans, sahip olma, pas, dokunuş kayan ve üstel ortalamaları; hepsi `shift(1)` ile sızıntısız, eğitim ve servis aynı fonksiyonu kullanır. |
| `src/analytics/league_feature_audit.py` | Ulusal lig modelleri için özellik ailesi önemi: 1X2 (her dış sezon) ve taç/ofsayt sayım modelleri (son %20) için ortak satır permütasyonu, 30 tekrar, tohum 42; `docs/reports/models/<anahtar>_feature_audit.json` yazar (`--competition la_liga`). |
| `src/features/build_league_pl_features.py` | LaLiga için PL özellik tanımları: LaLiga istatistiklerini PL'nin ham sütun adlarına çevirip PL'nin kendi `build_team_match_history`, `compute_pre_match_features`, `merge_features_to_matches` ve `compute_referee_features` fonksiyonlarını çalıştırır; sayım modelleri bu tabloyla eğitilir ve servis edilir. |
| `src/models/ablate_league_features.py` | Ulusal lig 1X2 modeli için ablasyon: üretim modeli ile bir veya birkaç varyant (`xi` ilk 11 özellikleri, `low_c` daha güçlü düzenlileştirme adayları, `core` 22 özellikli küme, `core_low_c`, `pl_parity` PL özellik tanımları) aynı walk-forward protokolde karşılaştırılır; eşli bootstrap, Benjamini-Hochberg ve önceden yazılmış benimseme kuralı uygulanır, rapor JSON'u yazar (`--competition la_liga --group low_c core`; üretim dosyasına dokunmaz). |
| `src/models/train_league_counts.py` | Ulusal lig için korner, taç, ofsayt, kart ve kurtarış sayım modelleri: Premier League ile aynı seçim kodu, kapılar ve özellik tanımları (`train_count_model`, `build_league_pl_features`; `--features league` ilk sürümün LaLiga'ya özgü özelliklerini yalnızca değerlendirir); özellik tablosunu, `*_model_v1.joblib` dosyalarını ve `docs/reports/models/<anahtar>_count_models.json` raporunu yazar (`--competition la_liga`, `--no-save` yalnızca değerlendirir). |
| `src/models/train_league_model.py` | Ulusal lig için walk-forward 1X2 ve gol modeli eğitimi/denetimi: taban oran, Elo ve piyasa kıyası, bootstrap + FDR, kapı kararı, rapor JSON'u ve üretim dosyası (`--competition la_liga`). |
| `src/api/league_prediction.py` | LaLiga maç tahmini (`/api/predict`): modeli ya da kapı kararına göre Elo referansını sunar, gol pazarlarını Dixon-Coles ile üretir, sayım pazarlarını `baseline` etiketler. |
| `src/analytics/league_audit.py` | LaLiga Model Doğrulama sayfası verisi: kaydedilmiş walk-forward tahminlerden maç satırları, hafta özetleri, kıyas bloğu. |
| `tests/test_league_model.py` | LaLiga özelliklerinin sızıntı testleri (kendi sonucu ve sonrası değiştirilince özellikler aynı kalır), kapı kararı, istatistik yardımcıları. |
| `tests/test_prospective_league.py` | Ligin ileriye dönük tahmin kaydı: kendi kayıt, puan kartı ve artifact yolları; puanlamanın yalnızca kickoff öncesi ve her maçın son tahminini sayması. |
| `tests/test_league_serving.py` | LaLiga tahmin ve denetim yanıtının tutarlılığı (yerel veri yoksa atlanır). |
| `src/ingest/raw_store.py` | Ham sağlayıcı yanıtlarını `data/competitions/<anahtar>/raw/<sağlayıcı>/` altına atomik yazan yardımcılar ve yol kuralları. |
| `src/ingest/export_competition_raw.py` | Tek seferlik: veritabanındaki UCL/UEL TheStatsAPI kayıtlarını dosyalara döker, UEFA fikstür ve puan durumu yanıtlarını yeniden çekip kaydeder. Sonraki senkronizasyonlar dosyaları kendisi yazar. |
| `src/ingest/sync_competition_data.py` | Seçilen turnuva ve sezonun maçlarını sağlayıcıdan çekip `matches` tablosuna yazar (yalnızca o `competition_id`). |
| `src/ingest/providers/api_football.py` | UCL/UEL için API-Football sağlayıcısı (`API_FOOTBALL_KEY` gerekir). |
| `src/processing/process_competition_data.py` | Bir turnuvanın ham fikstürlerini işleyip `competition_id` ile SQLite'a yazar; ham veri yoksa boş döner. |
| `tests/test_competition_pipeline.py` | Turnuva izolasyonunu ve ham veri yokken DB'nin değişmediğini doğrular. |
| `tests/test_competitions.py` | Turnuva kayıt defteri testleri. |
| `tests/test_provider_clients.py` | Sağlayıcı istemci testleri. |

## 1b. `src/pipeline/`

| Dosya | Ne yapar |
|---|---|
| `rebuild.py` | **Tek yeniden-kur zinciri** (`python -m src.pipeline.rebuild [--skip adım,adım]` ile de çalışır): `process → player_index → features → database`, her adım ayrı süreçte. `sync_season_data` (cron, 30 dk) ve `run_full_pipeline` (haftalık) aynı `rebuild_derived_data()` fonksiyonunu çağırır; ilk hatada durur ve adı `RebuildError` içinde söyler. `PLM_DATA_DIR` alt süreçlere geçer. |

## 2. `src/ingest/` — veri çekme

| Dosya | Ne yapar |
|---|---|
| `files.py` | `atomic_write_json`: JSON'u geçici dosyaya yazıp yerine taşır (iki senkron scripti paylaşır). |
| `fetch_season_data.py` | PulseLive API'den bir sezonun fikstürünü, maç istatistiklerini, olay akışını (stream) ve maç detaylarını indirir. Diğer ingest scriptlerinin kullandığı ortak istemci fonksiyonları burada (`build_session`, `fetch_match_details` vb.). |
| `sync_season_data.py` | Artımlı senkronizasyon: fikstürü yeniler, **önümüzdeki 14 gün için hakem atamalarını** çeker, yeni biten veya eksik maçların verisini indirir, sonra Parquet/özellik/SQLite'ı yeniden kurar. Tekrar çalıştırmak güvenlidir. |
| `sync_prematch_lineups.py` | Maç öncesi **resmi ilk 11'i** çeker, `data/competitions/premier_league/raw/matches/*_details.json` önbelleğini günceller, özellik tablosundaki ilk 11 reytinglerini yazar ve "son maç 11'i" ile "resmi 11" tahminlerini yan yana yazdırır. `--match-id`, `--team`, `--gameweek`, `--hours-ahead` seçenekleri var. |
| `fetch_team_staff.py` | Takımların kadro ve teknik ekip (görevli) bilgisini çeker, `data/competitions/premier_league/processed/team_staff.json`'a yazar. |
| `fetch_transfermarkt_market_values.py` | Transfermarkt'tan takım ve oyuncu piyasa değerlerini çeker, SQLite'a (`team_market_values`, `player_market_values`) ve JSON'a yazar. |
| `import_thestatsapi_odds.py` | TheStatsAPI'den açılış/kapanış bahis oranlarını (1X2, O/U 2.5, BTTS, köşe, kart) içe aktarır. Hız sınırı: ~5.2 sn/istek. |
| `import_thestatsapi_xg.py` | TheStatsAPI'den maç bazlı xG'yi, mevcut alanların üzerine yazmadan, ayrı bir kaynak tablosuna aktarır. Anahtar `THESTATSAPI_API_KEY` ortam değişkeninden okunur. |

## 3. `src/processing/` — ham veriyi tabloya çevirme

| Dosya | Ne yapar |
|---|---|
| `process_season_data.py` | Ham JSON'ları sezon ve birleşik Parquet tablolarına çevirir: `matches_summary_*.parquet`, `shots_events_*.parquet`. |
| `build_player_index.py` | Tüm `*_details.json` dosyalarını okuyup oyuncu kayıt defterini (`players_registry.json`) ve maç geçmişini (`player_match_logs.json`) üretir: maç sayısı, dakika, gol, asist. |

## 4. `src/db/`

| Dosya | Ne yapar |
|---|---|
| `database.py` | SQLite katmanı (`data/football.db`): şema, kaynaklardan doldurma (`populate_db_from_sources`), hakem özetleri, gruplanmış fikstür sorguları, xG ekleme. API'nin çalışma anında ağır Parquet/JSON okumasını önler. |

## 5. `src/features/` — özellik mühendisliği

| Dosya | Ne yapar |
|---|---|
| `build_features.py` | Ana özellik hattı: yuvarlanan pencere ve EWMA istatistikleri, rakibe göre düzeltilmiş metrikler, dinlenme günleri, form, Elo, sezon puanı. Veri sızıntısı yasağı burada uygulanır (`shift(1)`). Ayrıca oyuncu reytinglerinden ilk 11 özetleri üretir. |
| `draw_features.py` | Beraberlik eğilimi özellikleri, tek artımlı geçmiş durumundan hesaplanır. |

## 6. `src/models/` — modeller

| Dosya | Ne yapar |
|---|---|
| `train_match_outcome.py` | 1X2 (ve O/U 2.5) modellerini eğitir: lojistik regresyon, kalibrasyon, ensemble; `outcome_models_v1.joblib`'ı üretir. |
| `train_goals.py` | Gol skor matrisi modelini (bağımsız Poisson + Dixon-Coles) eğitir, harman ızgarasını seçer; `goals_models_v1.joblib`. |
| `evaluate_goal_models.py` | Gol model adaylarını ileriye dönük sezon holdout'larında karşılaştırır. `train_goals`'tan önce çalıştırılır. |
| `goals_model.py` | Özellik tabanlı gol hızları (lambda) ve harmanlama (`blend_lambdas`). |
| `dixon_coles.py` | Dixon-Coles skor matrisi: 1X2, üst/alt, BTTS, takım üst/alt olasılıkları ve 1X2'ye hizalama. |
| `train_corners.py`, `train_cards.py`, `train_saves.py`, `train_throws.py`, `train_offsides.py` | Sayım modelleri: köşe, kart (hakem özetleriyle), kurtarış, taç, ofsayt. Toplam sayıyı ve eşik üstü olasılıkları verir. Kapıyı geçemezse `training_mean`'e düşer. |
| `count_model.py` | Beş sayım eğiticisinin ortak parçaları: veri yükleme ve doğrulama (`load_count_dataset`), öne çıkan özellikler (`top_features_of`), eğitim hatası (`train_errors`), artifact yazma (`save_count_artifact`). Her eğitici adaylarını, eşiklerini ve API/rapor için metrik anahtarlarını kendi dosyasında tutar. |
| `model_utils.py` | Ortak yardımcılar: güvenli özellik tablosu, dağılım tahmini, sayım kuyruk olasılığı, kalibratör, beceri kapıları (`apply_skill_gate`, `apply_outer_season_gate`). |
| `eval_utils.py` | Log loss, eşleştirilmiş bootstrap, güvenilirlik tablosu, ECE. |

## 7. `src/analytics/` — analiz ve denetim

| Dosya | Ne yapar |
|---|---|
| `prospective_1x2_benchmark.py` | **İleriye dönük test:** `snapshot` maç öncesi 1X2 tahminini append-only `1x2_forecast_log.jsonl`'a kaydeder, `score` maçlar bitince puanlar. Paper trading protokolünün temeli. | `--competition la_liga` ile LaLiga'nın kendi kaydı (`data/competitions/la_liga/processed/1x2_forecast_log.jsonl`) ve puan kartı (`docs/reports/prospective_1x2_scorecard_la_liga.json`) kullanılır; tahminler maç sayfasının kullandığı `compute_league_prediction` çıktısıdır, sonuçlar `data/football.db`'den okunur.
| `model_audit.py` | Model çıktılarını gerçek sonuçlar ve kapanış oranlarıyla denetler: kalibrasyon, eşik, değer farkı. |
| `data_quality_report.py` | Veri envanteri ve ham metrik kapsamı raporu (`data_quality.md`). |
| `team_data_audit.py` | Ham takım istatistiklerinin eksiksizliğini denetler (eksik ile sıfırı ayırır). |
| `audit_team_scenarios.py` | Skor durumu ve köşe olayları doğrulama raporu. |
| `team_scenarios.py` | Olay akışından skor durumuna göre şut ve köşe oranları. |
| `team_tactics.py` | Ham maç istatistiklerinden takım taktik profili (API tarafından kullanılır). |
| `league_stats.py` | İstatistikler sayfasının hesapları: haftanın/sezonun kadrosu, hücum-defans, gol-asist krallığı, disiplin, kaleciler, form ve sıralama hareketi, ev-deplasman tabloları, gol dakikaları, hakem ve genç oyuncu sıralamaları. Saf fonksiyon (`build_league_stats`). |
| `team_attackers.py` | Takımın sezon hücum liderleri (oyuncu kayıtları ve şut olaylarından). |
| `player_ratings.py` | 0-10 oyuncu reytingi (genel, hücum, savunma, kart riski): son 5 maç EWMA %70 + sezon tabanı %30. Tahmini ve resmi ilk 11 toplulaştırması. |
| `pipeline_health.py` | **Sağlık kontrolü** (yalnızca okur): sezon başına xG ve oran kapsamı, eksik ham dosyalar, özellik/veritabanı uyumsuzluğu, bayat model dosyaları. `python3 -m src.analytics.pipeline_health [--strict] [--json]`; FAIL varsa çıkış kodu 1. |

## 8. `src/api/`

| Dosya | Ne yapar |
|---|---|
| `server.py` | İnce giriş noktası (~50 satır): `FastAPI` uygulaması, CORS, veri değişince yeniden yükleme ara katmanı, yönlendiricileri bağlar, `/` ve `__main__`. |
| `state.py` | Yüklü veri çerçeveleri, model artifact'ları, önbellekler ve yeniden yükleme (`reload_runtime_datasets`). **İçe aktarılınca her şeyi yükler (~30 sn).** Veri yeniden yüklemede değişkenler yeniden bağlanır; diğer modüller bunları yalnızca `state.<ad>` olarak okur (`from src.api.state import <değişken>` yapmayın). |
| `prediction_service.py` | Ortak tahmin servisi: 1X2 (kalibrasyon ve kapılı ensemble), 1X2'ye hizalı skor matrisi ve O/U/KG kalibratörleri, 5 sayım modeli (`fill_value=np.nan`), ev/deplasman pay hesabı. `/api/predict`, `/api/fixtures/grouped`, `sync_prematch_lineups` ve `model_audit` tek bir tahmin akışını paylaşır. |
| `security.py` | Yönetim ucu jetonu (`require_admin_token`) ve CORS kökenleri (`cors_origins`). |
| `routes/meta.py` | `/api/data-version`, `/api/admin/*` (model yenileme, sezon senkronu; `PLM_ADMIN_TOKEN` ile korunur). |
| `routes/teams.py` | `/api/teams*`: kadro/teknik ekip, teknik direktör, profil, transfer, taktik, hücum liderleri, senaryolar. |
| `routes/fixtures.py` | `/api/fixtures*`, `/api/standings`, `/api/referees*`, `/api/match/{id}/recent-form`. |
| `routes/players.py` | `/api/players*`: arama, profil ve piyasa değeri geçmişi. |
| `routes/matches.py` | `/api/match/{id}/details` ve `/odds`. |
| `routes/stats.py` | `/api/stats`: hafta veya sezon kapsamında lig istatistikleri (`league_stats.py` çıktısı, veri sürümüne göre önbellekli). |
| `routes/predict.py` | `/api/predict`, `/api/model-audit`, `/api/benchmarks`. `predict_match` doğrudan çağrılabilir (`prospective_1x2_benchmark` bunu kullanır; FastAPI uygulaması gerekmez). |

## 9. `tests/` — `pytest`

| Dosya | Ne test eder |
|---|---|
| `test_data_leakage.py` | Hedef kolonun özelliklere sızmadığı; bir maçın sonucunun kendi maç öncesi özelliklerini değiştirmediği. |
| `test_feature_engineering.py` | Özellik hesaplarının temel doğruluğu. |
| `test_draw_features.py` | Beraberlik özelliklerinde sızıntı yok; canlı durum çevrimdışı hesapla aynı. |
| `test_goal_matrix.py` | Skor matrisi normalleşmesi, üst/alt monotonluğu, 1X2 hizalaması. |
| `test_goal_selection.py` | Harman ızgarası seçimi ve ileriye dönük kalibrasyon. |
| `test_match_outcome_splits.py` | Eğitim/holdout bölmeleri, aynı kickoff'un bölünmemesi, beraberlik kapısı. |
| `test_skill_gate.py` | Sayım modeli CV ve dış sezon kapıları. |
| `test_eval_utils.py` | Bootstrap. |
| `test_inference_logic.py` | Çıkarım mantığı ve ev/deplasman payı. |
| `test_league_stats.py` | İstatistikler hesapları (dört takımlık sentetik lig üzerinde). |
| `test_team_tactics.py` | Takım taktik özetleri. |
| `test_pipeline_health.py` | Sağlık kontrolü (xG boşluğu, eksik ham dosya) ve `fetch_season_data` çıkış kodu. |
| `test_config.py`, `test_rebuild.py` | Yapılandırma (`PLM_DATA_DIR`, `PLM_SEASON`) ve tek yeniden-kur zinciri, aşama seçimi. |
| `test_stats_api_imports.py` | xG ve oran içe aktarıcıları (sahte API istemcisiyle): tavansız xG, 404 dayanıklılığı, kayıtlı maçları atlama. |
| `test_database.py` | `populate_db_from_sources`: maç/yaklaşan fikstür/hakem özetleri, ikinci çalıştırmada değişmeme, xG tablosunun korunması. |
| `test_sync_helpers.py` | `sync_season_data` saf yardımcıları: tamamlanma, skor, takım adı eşleme, hakem. |
| `test_evaluate_goal_models.py` | Gol kapıları (sabit Poisson, KG, piyasa) sentetik veriyle, piyasa marjı temizleme. |
| `test_api_routes.py` | API rota duman testleri, tahmin tutarlılığı, yeniden yüklemede durumun yeniden bağlanması, yönetim ucu ve CORS (`needs_data`). |
| `test_api_fixtures.py` | `GET /api/fixtures`: NaN/NaT serileştirme (regresyon) ve sezon/arama/limit filtreleri. |
| `test_api_security.py` | Yönetim jetonu (`PLM_ADMIN_TOKEN`) ve CORS kökenleri; mini uygulamayla, veri gerektirmez. |
| `test_count_models.py` | Beş sayım eğiticisinin ortak yardımcıları ve her eğiticinin sentetik veriyle uçtan uca çalışması. |
| `test_ingest_files.py` | `atomic_write_json`. |
| `test_start.py` | `start.py` port mantığı: yalnızca projenin kendi süreci kapatılır, `--force`. |
| `test_train_serve_parity.py` | Eğitim ve çıkarım özelliklerinin (ilk 11 hücum/savunma farkları dahil) birebir eşleşmesi, koşullu NB2 dispersiyonu ve dış sezon kapı izolasyonu. |
| `test_docs.py` | Bu belgenin gerçeğe uyması: her `src/` ve `tests/` dosyası burada geçer, burada geçen her dosya vardır. |
| `conftest.py` | `needs_data` işareti: yerel veri ve model yoksa o testler atlanır. |

Çalıştırma: `pip install -r requirements-dev.txt && pytest` (`pytest.ini` yalnızca `tests/` toplar; `research/` hariç). Lint: `ruff check .` (`pyproject.toml`: sözdizimi, tanımsız ad, kullanılmayan içe aktarma, çıplak `except`; CI'da çalışır, yerelde `pre-commit install` ile commit öncesi de). Yerel veri ve modelleri okuyan testler `needs_data` işaretlidir ve veri yoksa (temiz klon, CI) otomatik atlanır. CI: `.github/workflows/ci.yml` (backend `pytest`, frontend `npm run build`).

## 10. `research/audit/` — tek seferlik adli denetimler

Doğrulama amaçlı scriptler; pipeline'a bağlı değil, elle çalıştırılır. Ayrıntı ve uyarılar: [`research/README.md`](../research/README.md).

| Dosya | Konu |
|---|---|
| `investigation_1.py` | Yuvarlanan özelliklerde takım izolasyonu, shift gecikmesi, aynı anda başlayan maçlar. |
| `investigation_2.py` | Veritabanı sayıları, bölmeler ve holdout yeniden kurulumu. |
| `investigation_3.py` | Üretim modellerinin kayıtlı metriklerini yeniden hesaplama. |
| `investigation_4.py` | Çıkarım yolu: lojistik, Dixon-Coles ve harman karşılaştırması. |
| `investigation_5.py` | Olasılık aksiyomları, monotonluk, BTTS ve skor matrisi tutarlılığı. |
| `investigation_6.py` | Kalibrasyon ve hafta bloklu bootstrap belirsizliği. |
| `draw_calibration.py`, `draw_recalibration.py`, `tune_blend.py` | Beraberlik kalibrasyonu ve harman ağırlığı denemeleri (birkaç somut maç üzerinde). |

## 11. `research/scratch/` — araştırma ve deney scriptleri

Tek seferlik analizler; üretim pipeline'ında kullanılmaz. Çoğu 1.200 maçlık holdout üzerinde bootstrap ile çalışır.

| Dosya | Konu |
|---|---|
| `audit_multiple_testing_and_permutation_importance.py` | Çoklu test düzeltmesi (Bonferroni, BH) ve permütasyon önemi. |
| `deep_dive_p0_investigation.py`, `execute_p0_final_tasks.py`, `execute_p0_final_closure.py` | P0 gol modeli doğrulaması: Platt/izotonik kalibrasyon, aritmetik/geometrik harman, BTTS kalibrasyonu, piyasa karşılaştırması. |
| `execute_deep_dive_audit_p0_p1.py` | Dixon-Coles rho, harman ağırlığı taraması, kuyruk riski. |
| `execute_p1_final_verifications.py` | 58'e 57 özellik ablasyonu ve edge eşiği taraması. |
| `rigorous_p1c_evaluation.py` | Shrinkage bootstrap ve yan etkileri. |
| `run_p1a_auc_segmentation.py` | AUC ve kalibrasyon segmentasyonu (Top 6 maçları vb.), güç analizi. |
| `diagnose_segment10_and_test_xgboost.py` | Segment 10 teşhisi ve 3 XGBoost mimarisi. |
| `segment10_distribution_and_features.py` | Poisson/Negatif Binom uyumu ve dağılım testleri. |
| `key_passes_impact.py` | Key pass özelliklerinin gol modellerine etkisi (A/B). |
| `tactical_pace_and_mv.py` | Piyasa değeri ağırlığı düşürme, tempo ve savunma hattı özellikleri (A/B). |
| `extract_all_goal_metrics.py` | `goals_models_v1.joblib` için tüm metrikleri toplu çıkarır. |
| `box_features_ablation.py` | PL 1X2 modelinde sağlayıcıya özgü ceza sahası giriş ve dokunuş özelliklerinin dış sezon ablasyonu; sonuç `docs/reports/experiments/` altına yazılır, üretim dosyalarına dokunmaz. |
| `lineup_feature_pilot.py` | İlk 11 sürekliliği özelliği 1X2'ye sinyal katıyor mu, üretimi değiştirmeden dener (`research/` altında). |

## 12. `deploy/` — sunucu dosyaları (yeni)

`setup.sh` (Ubuntu kurulumu), `job.sh` (kilitli iş sarmalayıcı), `crontab`, `plm-api.service`, `Caddyfile`. Ayrıntı için sunucuya kurulum notlarına bakın.

## 13. Frontend yapılandırması

`frontend/vite.config.js` (dev sunucu `:5173`, `/api` isteklerini `:8000`'e yönlendirir), `tailwind.config.js`, `postcss.config.js`.

## Zamanlama için notlar

- Sürekli çalışması gerekenler: `sync_season_data` (hakem + biten maç), `sync_prematch_lineups` (kadro).
- `prospective_1x2_benchmark.py snapshot` periyodik çalışmalı, aksi halde ileriye dönük test kaydı boş kalır. `deploy/crontab`'a eklendi: `snapshot` 06:30 UTC, `score` 23:15 UTC. Script bir maç için günde yalnızca 1 tahmin kaydeder, bu yüzden kayıt maç günü sabahki (resmi kadro öncesi) tahmin olur.
- `run_full_pipeline.py` ağırdır, haftalık yeterli.
