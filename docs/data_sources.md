# Veri Kaynakları Haritası

**Güncelleme:** 17 Kasım 2026. Hangi turnuva için hangi veri nereden geliyor, hangi script çekiyor, ham dosya ve veritabanında nerede duruyor. Yeni bir kaynak ya da turnuva eklendiğinde bu dosya güncellenir.

Dizin düzeni ve ortam değişkenleri: [scripts_reference.md §0](scripts_reference.md). Script ayrıntıları: [scripts_reference.md](scripts_reference.md). Bu sayfanın sonunda turnuva veri script'lerinin kataloğu var.

## 1. Özet: veri türü x turnuva

| Veri | Premier League (39) | Şampiyonlar Ligi (2) | Avrupa Ligi (3) |
|---|---|---|---|
| Fikstür ve sonuç | PulseLive | UEFA maç API'si | UEFA maç API'si |
| Resmi puan durumu | Maçlardan hesaplanır | UEFA puan durumu API'si (eşitlik bozma kuralları dahil) | UEFA puan durumu API'si |
| Takım maç istatistiği | PulseLive | TheStatsAPI | TheStatsAPI |
| xG | TheStatsAPI | TheStatsAPI | TheStatsAPI |
| Kadro ve oyuncu maç verisi | PulseLive | UEFA (kadro, anlık) + TheStatsAPI (oyuncu istatistiği, rating) | Aynı |
| Olay akışı / zaman akışı | PulseLive | UEFA (anlık, saklanmaz) + TheStatsAPI (zaman akışı) | Aynı |
| Şut haritası | PulseLive (şut olayları) | TheStatsAPI (indirilmiş olanlar) | TheStatsAPI (indirilmiş olanlar) |
| Bahis oranları | TheStatsAPI | TheStatsAPI, 2024/25 ve sonrası | TheStatsAPI, 2024/25 ve sonrası |
| Takım kadrosu, piyasa değeri | Transfermarkt (kamu API sarmalayıcı) | TheStatsAPI | TheStatsAPI |
| Teknik direktör | PulseLive (resmi kadro) + elle doğrulanmış değişiklik dosyası | TheStatsAPI (son fikstürdeki) | Aynı |
| Hakem | PulseLive | UEFA | UEFA |
| Stadyum | PulseLive | UEFA | UEFA |
| Kulüp rozeti | Depodaki yerel dosyalar | UEFA CDN (bağlantı) | UEFA CDN (bağlantı) |
| Turnuva logosu | Resmi amblem, kırpılmış (`frontend/public/competitions`) | Aynı | Aynı |
| Tahmin modeli | Var (`models/production/premier_league/`) | Yok | Yok |

## 2. Turnuva turnuva

### Premier League (`competition_id` 39)
- **Sağlayıcı:** PulseLive (resmi veri). Fikstür, takım ve oyuncu maç istatistikleri, olay akışı, maç detayı, kadro.
- **Script:** `src/ingest/fetch_season_data.py` (tek sezon), `sync_season_data.py` (artımlı; düğmenin çalıştırdığı), `sync_prematch_lineups.py` (maç öncesi resmi kadrolar), `fetch_team_staff.py` (teknik kadro).
- **Ek kaynaklar:** xG `import_thestatsapi_xg.py`, oranlar `import_thestatsapi_odds.py` (TheStatsAPI), piyasa değerleri `fetch_transfermarkt_market_values.py` (Transfermarkt, `transfermarkt-api.fly.dev`).
- **Ham dosya:** `data/competitions/premier_league/raw/fixtures_<sezon>.json`, `raw/matches/<id>_{stats,stream,details}.json`.
- **İşlenmiş:** `processed/` altındaki parquet tabloları, özellikler, değerlendirme JSON'ları, tahmin günlüğü.
- **Veritabanı:** `matches` (`competition_id = 39`), `external_match_xg`, `external_match_odds`, `team_market_values`, `player_market_values`, `referees`.

### Şampiyonlar Ligi (2) ve Avrupa Ligi (3)
- **Fikstür, sonuç, puan durumu:** UEFA'nın herkese açık, anahtarsız API'leri (`match.uefa.com/v5/matches`, `standings.uefa.com/v1/standings`). Script: `src/ingest/sync_competition_data.py`. Eleme turları 9-13 sabit hafta numarasını taşır; eleme öncesi eleme turları (preliminary/qualifying) alınmaz. 2022/23-2023/24 sekiz gruplu grup aşaması, 2024/25 ve sonrası tek 36 takımlı lig aşaması.
- **Kadro ve olaylar (anlık):** UEFA `/lineups` ve `/events` uç noktaları, maç sayfası açılırken sorgulanır; veritabanına yazılmaz.
- **İstatistik, xG, oyuncu, zaman akışı, oran, kadro, takım istatistiği, teknik direktör:** TheStatsAPI. Script: `src/ingest/sync_thestatsapi_competition.py`; TheStatsAPI turnuva kimlikleri UCL `comp_3498`, UEL `comp_7739`. Oranlar 2024/25 öncesi için çekilmedi.
- **Ham dosya:** `data/competitions/<anahtar>/raw/uefa/{fixtures,standings}_<sezon>.json` ve `raw/thestatsapi/{matches,competition}/...` (`export_competition_raw.py` ile mevcut veritabanı içeriği dosyalara dökülmüştür; sonraki senkronizasyonlar dosyaları kendisi yazar).
- **Veritabanı:** `matches` (`competition_id` 2/3, `stage`, `group_name`, `leg`, `advancing_team_id`...), `external_match_payloads`, `external_competition_payloads`, `external_match_xg`, `external_match_odds`.
- **Not:** Önceki sahte (rastgele üretilmiş) veri silindi; yalnızca bu kaynaklar kullanılır.

## 3. Dış servisler ve kurallar

| Servis | Ne için | Anahtar | Sınır ve notlar |
|---|---|---|---|
| TheStatsAPI (`api.thestatsapi.com`) | İstatistik, xG, oyuncu, oran, kadro (UCL, UEL, PL xG/oran ve isteğe bağlı ulusal ligler) | `THESTATSAPI_API_KEY` ortam değişkeni; hiçbir dosyaya yazılmaz | Dakikada 100 istek (ölçüldü; aşılınca 429). Aylık kota 500.000. Script'ler isteklerin başlangıcını 0,65 sn aralıkla dağıtır |
| UEFA maç ve puan durumu API'si | UCL/UEL fikstür, sonuç, kadro, olay, resmi tablo | Yok | Düz `Mozilla/5.0` kullanıcı aracısı çalışır; özel imza engellenir |
| PulseLive | Premier League resmi verisi | Yok | |
| openfootball (`raw.githubusercontent.com/openfootball/football.json`) | Ulusal lig takvimi (isteğe bağlı) | Yok | Kamu malı (CC0) |
| TheSportsDB | Kulüp rozeti, lig logosu (isteğe bağlı) | Genel test anahtarı | Dakikada ~30 istek; sınırlandığında script bekler |
| Transfermarkt (kamu API sarmalayıcı) | PL piyasa değerleri | Yok | Hız sınırlı; 26 Ekim 2026'da `transfermarkt-api.fly.dev` 504 (upstream timeout) döndü |
| Transfermarkt (`www.transfermarkt.com`, sayfalar ve `ceapi/marketValueDevelopment/graph`) | İsteğe bağlı ulusal lig kulüp/oyuncu değeri ve tarihli değer geçmişi | Yok | Tarayıcı kullanıcı aracısı gerekir; hızlı istemciye 403/429 döner, script istekleri 2,5 sn aralıkla yapar ve indirilmiş dosyayı tekrar çekmez |

## 4. Karar günlüğü (neden böyle)

- **Sahte veri yok:** Gemini oturumundan kalan rastgele UCL/UEL verisi tamamen silindi.
- **Oranlar:** 2024/25 öncesi sezonlar için çekilmez (istek tasarrufu); `--old-extras` ile açılabilir.
- **Şut haritası:** Hiçbir turnuva, sezon ya da maç için yeni çekilmez (25 Ekim 2026 kararı). 1X2 modeli bu veriden beslenmiyor; takım düzeyindeki xG ve şut sayıları zaten istatistik yanıtında geliyor.
- **Tahmin modeli:** Yalnızca Premier League üretimde aktiftir. UCL/UEL için denenen yürüyen pencere modeli taban orandan iyi, ülke öncüllü Elo'dan ayırt edilemez, piyasadan kötü çıktığı için kaldırıldı.
- **Ortak piyasa değeri tabloları (`team_market_values`, `player_market_values`):** Çoklu turnuva şemasında `competition_id` taşır; PL ad eşlemeleri `competition_id = 39` ile sınırlandırılır (`ensure_market_value_tables`).
- **PL piyasa değeri sızıntısı (26 Ekim 2026):** PL'nin sezon satırları da sezon sonu değerlemesidir ve 1X2 modelinde maç öncesi özellik olarak kullanılır. Etki tavanı küçük olduğu için tarihli değerlerle yeniden üretim yapılmadı; PL Transfermarkt çekimi durduruldu (kısmi ham dosyalar `data/competitions/premier_league/raw/transfermarkt/`, kullanılmıyor). Ayrıntı: `docs/reports/models/outcome_1x2_model.md` §4.
- **Tek veritabanı:** `data/football.db` ortaktır (PL takım sayfalarında Avrupa maçlarını birleştirmek için); ham veri ise turnuva klasörlerinde dosya olarak tutulur.

## 5. Yeni bir lig eklerken

1. `config/competitions.yaml`: kimlik (benzersiz), sağlayıcı, `provider_competition_id`, bölgeler, varsa `schedule_source`.
2. `fetch_thestatsapi_league` ile indir, `fetch_openfootball_schedule` ile tam takvimi al, `fetch_team_badges --league-id` ile rozetleri indir; piyasa değeri için `transfermarkt_code` ekleyip `fetch_transfermarkt_league` çalıştır.
3. `load_thestatsapi_league` ile yükle; kimlik çakışması koruması (`assert_ids_free`) çalışır.
4. `frontend/src/context/competitionState.js` içine turnuvayı ekle (`kind`, `hasModel`, `hasAudit`, `richData`, `syncKinds`) ve `index.css` içine vurgu rengini.
5. Bu dosyayı ve [artifact_registry.md](artifact_registry.md) girdilerini güncelle.

## 6. Script kataloğu: turnuva verisi için eklenenler

Hepsi `--help` ile kullanım, girdi, çıktı ve gereksinimi yazar. Hepsinin dizinini `python3 -m src.ingest --help` da listeler.

| Komut | Ne işe yarar | Anahtar | Yazdığı yer |
|---|---|---|---|
| `python3 -m src.ingest.sync_competition --competition <anahtar> --season <sezon>` | "Veri güncelle" düğmesinin PL dışı turnuvalar için çalıştırdığı boru hattı: eksikleri indirir ve yükler | TheStatsAPI için gerekli | Ham dosyalar ve `football.db` |
| `python3 -m src.ingest.fetch_thestatsapi_league --competition <anahtar> [--seasons ...]` | Ulusal ligin fikstür listesini, maç yanıtlarını (künye, istatistik, kadro, oyuncu, zaman akışı, oran) ve kadro/takım istatistiklerini indirir | Gerekli | `raw/thestatsapi/` |
| `python3 -m src.ingest.load_thestatsapi_league --competition <anahtar> [--seasons ...]` | İndirilen dosyaları ağ kullanmadan veritabanına yükler | Gerekmez | `football.db` |
| `python3 -m src.ingest.fetch_openfootball_schedule --competition <anahtar>` | Tam sezon takvimini indirir (yayınlanmamış haftalar için) | Gerekmez | `raw/openfootball/` |
| `python3 -m src.ingest.fetch_team_badges --competition <anahtar> [--league-id <id>]` | Kulüp rozetlerini ve lig logosunu indirir | Gerekmez (test anahtarı) | `frontend/public/badges/`, `frontend/public/competitions/` |
| `python3 -m src.ingest.fetch_transfermarkt_league --competition <anahtar> [--seasons ...] [--skip-history] [--offline]` | Transfermarkt'tan sezon sezon kulüp ve oyuncu piyasa değerlerini ve oyuncuların tarihli değer geçmişini indirir ve yükler; `--offline` yalnızca diskteki dosyaları yükler, `--download-only` veritabanına yazmaz | Gerekmez | `raw/transfermarkt/`, `football.db` |
| `python3 -m src.ingest.sync_competition_data --competition <anahtar> --season <sezon>` | Fikstür, sonuç ve resmi tabloyu veritabanına yazar (UEFA kupaları için UEFA'dan, ligler için kaydedilmiş dosyalardan) | Gerekmez | `football.db`, `raw/uefa/` |
| `python3 -m src.ingest.sync_thestatsapi_competition --competition champions_league --season <sezon>` | UCL/UEL maçları için TheStatsAPI ayrıntısını çekip yazar | Gerekli | `football.db`, `raw/thestatsapi/` |
| `python3 -m src.ingest.export_competition_raw` | Tek seferlik: veritabanındaki UCL/UEL TheStatsAPI kayıtlarını dosyalara döker, UEFA yanıtlarını yeniden çekip kaydeder | Gerekmez | `raw/uefa/`, `raw/thestatsapi/` |
| `python3 -m src.models.train_league_counts --competition <anahtar>` | Ulusal lig korner, taç, ofsayt, kart ve kurtarış sayım modellerini PL ile aynı kapılarla eğitir, rapor JSON'u ve üretim dosyalarını yazar | Gerekmez | `reports/models/`, `models/production/<anahtar>/` |
| `python3 -m src.models.train_league_model --competition <anahtar>` | Ulusal lig 1X2 ve gol modelini walk-forward eğitir, kıyaslar, rapor ve üretim dosyası yazar | Gerekmez | `reports/models/`, `models/production/<anahtar>/` |
| `python3 research/box_features_ablation.py` | PL 1X2 modelinde ceza sahası giriş ve dokunuş özelliklerinin dış sezon ablasyonu | Gerekmez | `reports/experiments/` |

Yardımcı modüller (komut satırı yok): `src/ingest/raw_store.py` (ham dosya yolları, atomik yazma, turnuva kilidi), `src/ingest/providers/uefa.py`, `src/ingest/providers/thestatsapi_league.py` (sağlayıcılar), `src/api/uefa_match_details.py`, `src/api/statsapi_match_details.py` (maç sayfası), `src/api/competition_squads.py`, `src/api/competition_stats.py`, `src/api/european_fixtures.py`, `src/api/knockout.py`.
