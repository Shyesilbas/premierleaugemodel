# Veri Kaynakları Haritası

**Güncelleme:** 25 Ekim 2026. Hangi turnuva için hangi veri nereden geliyor, hangi script çekiyor, ham dosya ve veritabanında nerede duruyor. Yeni bir kaynak ya da turnuva eklendiğinde bu dosya güncellenir.

Dizin düzeni ve ortam değişkenleri: [scripts_reference.md §0](scripts_reference.md). Script ayrıntıları: [scripts_reference.md](scripts_reference.md). Bu sayfanın sonunda yeni eklenen script'lerin kataloğu var.

## 1. Özet: veri türü x turnuva

| Veri | Premier League (39) | Şampiyonlar Ligi (2) | Avrupa Ligi (3) | LaLiga (140) |
|---|---|---|---|---|
| Fikstür ve sonuç | PulseLive | UEFA maç API'si | UEFA maç API'si | TheStatsAPI (yayınlanan ~4 hafta) + openfootball takvimi (kalan haftalar) |
| Resmi puan durumu | Maçlardan hesaplanır | UEFA puan durumu API'si (eşitlik bozma kuralları dahil) | UEFA puan durumu API'si | Maçlardan hesaplanır |
| Takım maç istatistiği | PulseLive | TheStatsAPI | TheStatsAPI | TheStatsAPI |
| xG | TheStatsAPI | TheStatsAPI | TheStatsAPI | TheStatsAPI |
| Kadro ve oyuncu maç verisi | PulseLive | UEFA (kadro, anlık) + TheStatsAPI (oyuncu istatistiği, rating) | Aynı | TheStatsAPI |
| Olay akışı / zaman akışı | PulseLive | UEFA (anlık, saklanmaz) + TheStatsAPI (zaman akışı) | Aynı | TheStatsAPI |
| Şut haritası | PulseLive (şut olayları) | TheStatsAPI (indirilmiş olanlar) | TheStatsAPI (indirilmiş olanlar) | TheStatsAPI (yalnızca baştan indirilmiş olanlar; artık çekilmez) |
| Bahis oranları | TheStatsAPI | TheStatsAPI, 2024/25 ve sonrası | TheStatsAPI, 2024/25 ve sonrası | TheStatsAPI, 2024/25 ve sonrası |
| Takım kadrosu, piyasa değeri | Transfermarkt (kamu API sarmalayıcı) | TheStatsAPI | TheStatsAPI | TheStatsAPI |
| Teknik direktör | PulseLive (resmi kadro) + elle doğrulanmış değişiklik dosyası | TheStatsAPI (son fikstürdeki) | Aynı | TheStatsAPI (son fikstürdeki) |
| Hakem | PulseLive | UEFA | UEFA | TheStatsAPI (maç künyesi) |
| Stadyum | PulseLive | UEFA | UEFA | TheStatsAPI (maç künyesi) |
| Kulüp rozeti | Depodaki yerel dosyalar | UEFA CDN (bağlantı) | UEFA CDN (bağlantı) | TheSportsDB'den indirilen yerel dosyalar |
| Turnuva logosu | Resmi amblem, kırpılmış (`frontend/public/competitions`) | Aynı | Aynı | TheSportsDB lig rozeti |
| Tahmin modeli | Var (`models/production/premier_league/`) | Yok | Yok | Var (`models/production/la_liga/`, walk-forward; bkz. `docs/reports/models/la_liga_outcome.md`) |

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

### LaLiga (140)
- **Fikstür ve sonuç:** TheStatsAPI (`comp_8814`); sağlayıcı sezonun yalnızca yaklaşık 4 hafta ilerisini yayınlar. Script: `src/ingest/fetch_thestatsapi_league.py` (indirir), `load_thestatsapi_league.py` (veritabanına yükler).
- **Yayınlanmamış haftalar:** openfootball (kamu malı) tam sezon takvimi; script `src/ingest/fetch_openfootball_schedule.py`. Bu maçlar yer tutucudur ve TheStatsAPI yayınlayınca gerçeğiyle değişir. Ertelenen (iptal) maç takvimde kalır.
- **Maç künyesi (hakem, stadyum), istatistik, xG, kadro, oyuncu istatistiği, zaman akışı, oran:** TheStatsAPI. Oranlar yalnızca 2024/25 ve sonrası; şut haritası artık hiçbir sezon için çekilmez (inmiş dosyalar durur ve yüklenir).
- **Kadro, piyasa değeri, takım istatistiği, teknik direktör:** TheStatsAPI `/teams/{id}/players`, `/teams/{id}/stats`, fikstürdeki `home_manager`/`away_manager`. Sezon kadrosu, eski sezonlarda bugünkü kadroyu verir; yalnızca oynayan oyuncular listelenir.
- **Rozetler ve logo:** TheSportsDB (ücretsiz test anahtarı), `src/ingest/fetch_team_badges.py`; `frontend/public/badges/la_liga/<takım id>.png` ve `frontend/public/competitions/la_liga.png`. Üçüncü taraf markalardır, yalnızca kulübü tanımlamak için gösterilir.
- **Ham dosya:** `data/competitions/la_liga/raw/thestatsapi/{fixtures_<sezon>.json,matches/,competition/}` ve `raw/openfootball/fixtures_<sezon>.json`.
- **Kimlikler:** TheStatsAPI kimlikleri başka kaynaklarla çakışmasın diye kaydırılır: `match_id` +100.000.000, takım kimliği +10.000.000, takvim yer tutucuları 300.000.000 + sağlama değeri. Maç saatleri Londra saatiyle gösterilir.
- **Veritabanı:** `matches` (`competition_id = 140`, hepsi `stage = league`), `external_match_payloads`, `external_competition_payloads`, `external_match_xg`, `external_match_odds`.

## 3. Dış servisler ve kurallar

| Servis | Ne için | Anahtar | Sınır ve notlar |
|---|---|---|---|
| TheStatsAPI (`api.thestatsapi.com`) | İstatistik, xG, oyuncu, oran, kadro (UCL, UEL, LaLiga, PL xG/oran) | `THESTATSAPI_API_KEY` ortam değişkeni; hiçbir dosyaya yazılmaz | Dakikada 100 istek (ölçüldü; aşılınca 429). Aylık kota 500.000. Script'ler isteklerin başlangıcını 0,65 sn aralıkla dağıtır |
| UEFA maç ve puan durumu API'si | UCL/UEL fikstür, sonuç, kadro, olay, resmi tablo | Yok | Düz `Mozilla/5.0` kullanıcı aracısı çalışır; özel imza engellenir |
| PulseLive | Premier League resmi verisi | Yok | |
| openfootball (`raw.githubusercontent.com/openfootball/football.json`) | Lig takvimi | Yok | Kamu malı (CC0) |
| TheSportsDB | Kulüp rozeti, lig logosu | Genel test anahtarı | Dakikada ~30 istek; sınırlandığında script bekler |
| Transfermarkt (kamu API sarmalayıcı) | PL piyasa değerleri | Yok | Hız sınırlı |

## 4. Karar günlüğü (neden böyle)

- **Sahte veri yok:** Gemini oturumundan kalan rastgele UCL/UEL verisi tamamen silindi.
- **Oranlar:** 2024/25 öncesi sezonlar için çekilmez (istek tasarrufu); `--old-extras` ile açılabilir.
- **Şut haritası:** Hiçbir turnuva, sezon ya da maç için yeni çekilmez (25 Ekim 2026 kararı). 1X2 modeli bu veriden beslenmiyor; takım düzeyindeki xG ve şut sayıları zaten istatistik yanıtında geliyor.
- **Tahmin modeli:** Yalnızca Premier League. UCL/UEL için denenen yürüyen pencere modeli taban orandan iyi, ülke öncüllü Elo'dan ayırt edilemez, piyasadan kötü çıktığı için kaldırıldı. LaLiga için `src/models/train_league_model.py` ile walk-forward model eğitildi (taban orandan anlamlı iyi, Elo'dan ayırt edilemez; kapı kuralı modeli seçti).
- **Tek veritabanı:** `data/football.db` ortaktır (PL takım sayfalarında Avrupa maçlarını birleştirmek için); ham veri ise turnuva klasörlerinde dosya olarak tutulur.

## 5. Yeni bir lig eklerken

1. `config/competitions.yaml`: kimlik (benzersiz), sağlayıcı, `provider_competition_id`, bölgeler, varsa `schedule_source`.
2. `fetch_thestatsapi_league` ile indir, `fetch_openfootball_schedule` ile tam takvimi al, `fetch_team_badges --league-id` ile rozetleri indir.
3. `load_thestatsapi_league` ile yükle; kimlik çakışması koruması (`assert_ids_free`) çalışır.
4. `frontend/src/context/CompetitionContext.jsx` içine turnuvayı ekle (`kind`, `hasModel`, `richData`, `syncKinds`) ve `index.css` içine vurgu rengini.
5. Bu dosyayı ve [ARTIFACT_REGISTRY.md](../ARTIFACT_REGISTRY.md) girdilerini güncelle.

## 6. Script kataloğu: turnuva verisi için eklenenler

Hepsi `--help` ile kullanım, girdi, çıktı ve gereksinimi yazar. Hepsinin dizinini `python3 -m src.ingest --help` da listeler.

| Komut | Ne işe yarar | Anahtar | Yazdığı yer |
|---|---|---|---|
| `python3 -m src.ingest.sync_competition --competition <anahtar> --season <sezon>` | "Veri güncelle" düğmesinin PL dışı turnuvalar için çalıştırdığı boru hattı: eksikleri indirir ve yükler | TheStatsAPI için gerekli | Ham dosyalar ve `football.db` |
| `python3 -m src.ingest.fetch_thestatsapi_league --competition la_liga [--seasons ...]` | Ulusal ligin fikstür listesini, maç yanıtlarını (künye, istatistik, kadro, oyuncu, zaman akışı, oran) ve kadro/takım istatistiklerini indirir | Gerekli | `raw/thestatsapi/` |
| `python3 -m src.ingest.load_thestatsapi_league --competition la_liga [--seasons ...]` | İndirilen dosyaları ağ kullanmadan veritabanına yükler | Gerekmez | `football.db` |
| `python3 -m src.ingest.fetch_openfootball_schedule --competition la_liga` | Tam sezon takvimini indirir (yayınlanmamış haftalar için) | Gerekmez | `raw/openfootball/` |
| `python3 -m src.ingest.fetch_team_badges --competition la_liga [--league-id 4335]` | Kulüp rozetlerini ve lig logosunu indirir | Gerekmez (test anahtarı) | `frontend/public/badges/`, `frontend/public/competitions/` |
| `python3 -m src.ingest.sync_competition_data --competition <anahtar> --season <sezon>` | Fikstür, sonuç ve resmi tabloyu veritabanına yazar (UEFA kupaları için UEFA'dan, ligler için kaydedilmiş dosyalardan) | Gerekmez | `football.db`, `raw/uefa/` |
| `python3 -m src.ingest.sync_thestatsapi_competition --competition champions_league --season <sezon>` | UCL/UEL maçları için TheStatsAPI ayrıntısını çekip yazar | Gerekli | `football.db`, `raw/thestatsapi/` |
| `python3 -m src.ingest.export_competition_raw` | Tek seferlik: veritabanındaki UCL/UEL TheStatsAPI kayıtlarını dosyalara döker, UEFA yanıtlarını yeniden çekip kaydeder | Gerekmez | `raw/uefa/`, `raw/thestatsapi/` |
| `python3 -m src.models.train_league_counts --competition la_liga` | Ulusal lig korner, taç, ofsayt, kart ve kurtarış sayım modellerini PL ile aynı kapılarla eğitir, rapor JSON'u ve üretim dosyalarını yazar | Gerekmez | `docs/reports/models/`, `models/production/la_liga/` |
| `python3 -m src.models.train_league_model --competition la_liga` | Ulusal lig 1X2 ve gol modelini walk-forward eğitir, kıyaslar, rapor ve üretim dosyası yazar | Gerekmez | `docs/reports/models/`, `models/production/la_liga/` |
| `python3 research/box_features_ablation.py` | PL 1X2 modelinde ceza sahası giriş ve dokunuş özelliklerinin dış sezon ablasyonu | Gerekmez | `docs/reports/experiments/` |

Yardımcı modüller (komut satırı yok): `src/ingest/raw_store.py` (ham dosya yolları, atomik yazma, turnuva kilidi), `src/ingest/providers/uefa.py`, `src/ingest/providers/thestatsapi_league.py` (sağlayıcılar), `src/api/uefa_match_details.py`, `src/api/statsapi_match_details.py` (maç sayfası), `src/api/competition_squads.py`, `src/api/competition_stats.py`, `src/api/european_fixtures.py`, `src/api/knockout.py`.
