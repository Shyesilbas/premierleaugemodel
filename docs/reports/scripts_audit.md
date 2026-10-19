# Script Envanteri ve Denetimi

**Tarih:** 19 Ekim 2026
**Kapsam:** Depodaki tüm Python scriptleri (69 dosya, ~21.600 satır) ve kabuk scriptleri (`start.sh`, `deploy/job.sh`, `deploy/setup.sh`, `deploy/crontab`).
**Durum:** Yalnızca analiz. Kodda değişiklik yapılmadı.
**Tamamlayıcı belgeler:** [`docs/scripts_reference.md`](../scripts_reference.md) (her scriptin ne yaptığı), [`repository_audit.md`](repository_audit.md) (14 Ekim kod tabanı ve model denetimi). Bu rapor onları yinelemez; **sınıflandırma, çalışma akışı, bağımlılık, test örtüsü ve riskleri** ekler.

## Yönetici özeti

Kod tabanı işlevsel ve sızıntı kuralları (`shift(1)`, kilitli sezon) tutarlı uygulanmış. 27 testin tamamı geçiyor. Asıl sorunlar mimari ve operasyonel:

1. **İki ayrı "yeniden kur" zinciri var ve birbirinden farklı** (`run_full_pipeline.py` ile `sync_season_data.py`). Haftalık eğitim, oyuncu dizinini ve SQLite'ı yeniden kurmuyor.
2. **xG ve oran içe aktarma elle çalışıyor, cron'da yok.** Bu sezon oynanan 69 maçın 60'ında xG var; 7. hafta (9 maç) xG'siz. Gol modelinin çekirdek özellikleri xG tabanlı; eksik xG'nin etkisi doğrulanmadı (bkz. B2).
3. **`server.py` tek dosyada 3.503 satır**, 819 satırlık tek bir istek işleyicisi var ve import anında veri yüklüyor (ilk API isteği dahil ~28 sn).
4. **Test altyapısı eksik:** `pytest` bağımlılıklarda yok, CI ve lint yok, kritik modüllerin (gol değerlendirmesi, veritabanı, ingest, API rotaları) testi yok.
5. **~4.200 satır tek seferlik kod** (`scratch/`, `audit/`) depoda; `audit/test_*.py` adları `pytest`'in toplamasıyla çakışıyor.

Öneriler en sonda (§8), öncelik ve eforla. Tüm scriptlerin **neyi çalıştırdığı, kim tarafından çalıştırıldığı ve hangi dış servislere dokunduğu** §10'da (koddan üretilen çalıştırma haritası).

## 1. Yöntem ve sınırlar

| Ne yapıldı | Nasıl |
|---|---|
| Envanter | `git ls-files` + AST: satır, fonksiyon/sınıf, docstring, `__main__`, argparse |
| Bağımlılık grafı | AST ile `src.*` içe aktarmaları, "kim kimi kullanıyor" |
| Çıktı ve yan etki | Yazım desenleri (`to_parquet`, `joblib.dump`, SQL), ağ, ortam değişkeni, yıkıcı komut taraması |
| Çalışma akışı | `run_full_pipeline.py`, `sync_season_data.py`, `deploy/crontab`, `job.sh` doğrudan okundu |
| Testler | 22 fonksiyon testi + 5 `unittest` testi gerçekten çalıştırıldı |
| Veri durumu | `premier_league.db` üzerinde salt okunur SQL |

**Doğrulanmayanlar:** Her dosya satır satır okunmadı. Mantık düzeyi açıklamalar docstring, fonksiyon adları ve `scripts_reference.md`'ye dayanır; yalnızca akış, giriş noktaları ve riskli noktalar doğrudan okundu. "Ölü kod" taraması kaba bir sezgi (ad ≥2 kez geçiyor mu) ve dinamik kullanımı yakalamaz. `pytest`'in kendisi bu makinede kurulu olmadığı için tam `pytest` çalıştırması yapılmadı. Frontend (`frontend/src`) kapsam dışı.

## 2. Envanter özeti

| Grup | Dosya | Satır | Rol |
|---|---:|---:|---|
| `src/models` | 12 | 4.074 | Model eğitimi, değerlendirme, ortak yardımcılar |
| `src/analytics` | 10 | 3.588 | Denetim, raporlama, API'nin kullandığı analiz kütüphaneleri |
| `src/api` | 1 | 3.503 | FastAPI sunucusu |
| `scratch` | 13 | 3.381 | Tek seferlik araştırma |
| `src/ingest` | 7 | 2.321 | Dış kaynaklardan veri çekme |
| `src/features` | 2 | 1.524 | Özellik üretimi |
| `src/processing` | 2 | 799 | Ham JSON → tablo |
| `audit` | 9 | 788 | Tek seferlik adli doğrulama |
| `src/db` | 1 | 610 | SQLite katmanı |
| `tests` | 10 | 574 | Otomatik testler |
| kök | 2 | 521 | `run_full_pipeline.py`, `start.py` |
| kabuk | 3 + crontab | ~160 | Başlatıcı, sunucu kurulumu, zamanlanmış işler |

### Rol sınıflandırması

| Rol | Tanım | Scriptler |
|---|---|---|
| **P1 · Zamanlanmış üretim** | Sunucuda cron ile çalışır | `sync_season_data`, `sync_prematch_lineups`, `run_full_pipeline` (haftalık), `prospective_1x2_benchmark` (`snapshot`, `score`) |
| **P2 · Pipeline adımı** | `run_full_pipeline` içinden çağrılır | `process_season_data`, `build_features`, `data_quality_report`, `team_data_audit`, `audit_team_scenarios`, `train_corners/throws/saves/cards/offsides`, `train_match_outcome`, `evaluate_goal_models`, `train_goals` |
| **P3 · Sync iç adımı** | `sync_season_data.rebuild_derived_data` çağırır | `process_season_data`, `build_player_index`, `build_features`, `database` |
| **S · Servis** | API'nin çalışma anında kullandığı | `server`, `player_ratings`, `team_tactics`, `team_attackers`, `team_scenarios`, `model_audit`, `database`, `draw_features` |
| **L · Model kütüphanesi** | Başka modüllerce içe aktarılır | `dixon_coles` (22 kullanıcı), `model_utils` (17), `goals_model` (15), `eval_utils` (9) |
| **M · Elle operasyon** | Cron'da yok, elle çalıştırılır | `fetch_season_data`, `fetch_team_staff`, `fetch_transfermarkt_market_values`, `import_thestatsapi_odds`, `import_thestatsapi_xg`, `build_player_index` (tek başına), `start.py`/`start.sh` |
| **R · Araştırma/deney** | Üretimde kullanılmaz | `lineup_feature_pilot`, `scratch/*` (13), `audit/*` (9) |
| **T · Test** | | `tests/*` (10) |

## 3. Çalışma akışları

```
 [Sunucu cron — deploy/crontab, tüm işler job.sh ile tek kilit (flock) altında]

  */30 dk  sync_season_data ──► fikstür + hakem + biten maç JSON ──► rebuild_derived_data:
                                 process_season_data(all) → build_player_index → build_features → database
  */5 dk   sync_prematch_lineups --hours-ahead 1 ──► *_details.json + ilk-11 reytingleri
  Pzt 04:00 run_full_pipeline ──► process → features → 3 denetim raporu → 5 sayım modeli
                                  → 1X2 → evaluate_goal_models → train_goals → model_benchmarks.md
  06:30 / 23:15  prospective_1x2_benchmark snapshot / score ──► 1x2_forecast_log.jsonl
  (iş sonunda veri dosyaları değiştiyse plm-api yeniden başlatılır)

 [Cron'da OLMAYAN — elle]
  fetch_season_data (yeni sezon ham verisi), import_thestatsapi_xg, import_thestatsapi_odds,
  fetch_team_staff, fetch_transfermarkt_market_values

 [Geliştirme]  start.py / start.sh ──► uvicorn :8000 (--reload) + vite :5173
```

### Zincir karşılaştırması (bulgu B1'in kanıtı)

| Adım | `run_full_pipeline` (haftalık) | `sync_season_data` (30 dk) |
|---|:-:|:-:|
| `process_season_data` | ✓ (`main()` varsayılanı `all`) | ✓ `--season-name all` |
| `build_player_index` | ✗ | ✓ |
| `build_features` | ✓ | ✓ |
| `database` (SQLite doldurma) | ✗ | ✓ |
| Model eğitimi | ✓ | ✗ |
| Denetim/benchmark raporları | ✓ | ✗ |

## 4. Script bazında envanter

Açıklamalar için kaynak: docstring + `scripts_reference.md`. "Test" sütunu: bu modülü doğrudan sınayan test dosyası var mı.

### 4.1 Kök ve kabuk

| Dosya | Satır | Rol | Girdi → Çıktı / Ne yapar | Not |
|---|---:|---|---|---|
| `run_full_pipeline.py` | 421 | P1 | Yerel ham veri → parquet, özellikler, 7 model, raporlar | Sağlayıcıya bağlanmaz. Adım atlama/devam seçeneği yok; ortada hata olursa kısmi durum kalır |
| `start.py` | 100 | M | uvicorn + vite birlikte | Portu kullanan **her süreci `SIGKILL`ler** |
| `start.sh` | ~95 | M | `start.py`'nin bash karşılığı | Aynı `kill -9` davranışı; iki dosya aynı işi yapıyor |
| `deploy/job.sh` | 11 | P1 | `flock` ile kilitli iş sarmalayıcı, veri değiştiyse API'yi yeniden başlatır | Hata `failures.log`'a gider, çıkış kodu her zaman 0 |
| `deploy/setup.sh` | 16 | M | Ubuntu kurulumu (paketler, venv, systemd, Caddy, ufw, Tailscale) | `curl … \| sh` ile Tailscale kurar |
| `deploy/crontab` | 12 | P1 | 5 zamanlanmış iş | xG/oran/personel içe aktarma yok |

### 4.2 `src/ingest` (dış kaynaklar)

| Dosya | Satır | Rol | Girdi → Çıktı | Not |
|---|---:|---|---|---|
| `fetch_season_data.py` | 305 | M (+kütüphane) | PulseLive → `data/raw/fixtures_*.json`, `matches/*_{stats,stream,details}.json` | `--output-dir` var. Hata sayar ama **çıkış kodu 0**; `build_session` vb. diğer scriptlerce kullanılır |
| `sync_season_data.py` | 431 | P1 | PulseLive artımlı + hakem + türetilmiş veriyi yeniden kurma | Atomik JSON yazımı; alt süreçleri `subprocess` ile çağırır |
| `sync_prematch_lineups.py` | 544 | P1 | Resmi ilk 11 → `*_details.json`, özellik tablosundaki ilk-11 reytingleri | `sys.path` hack; kendi `atomic_write_json` kopyası |
| `fetch_team_staff.py` | 136 | M | PulseLive kadro/teknik ekip → `data/processed/team_staff*.json` | `sys.path` hack |
| `fetch_transfermarkt_market_values.py` | 333 | M | Transfermarkt → SQLite `*_market_values` + JSON | Sezon (2026/27) docstring'e gömülü |
| `import_thestatsapi_odds.py` | 311 | M | TheStatsAPI → `external_match_odds` | Anahtar ortamdan; ~5,2 sn/istek |
| `import_thestatsapi_xg.py` | 261 | M | TheStatsAPI → `external_match_xg` | `--max-gameweek` varsayılanı **6**; DB yolu dosya konumundan türetilir; xG'siz yanıtı yalnızca yazdırır |

### 4.3 `src/processing`, `src/db`, `src/features`

| Dosya | Satır | Rol | Girdi → Çıktı | Not |
|---|---:|---|---|---|
| `process_season_data.py` | 488 | P2/P3 | `data/raw` → `matches_summary_*.parquet`, `shots_events_*.parquet` | Yollar **sabit** (`data/raw`, `data/processed`); `--data-dir` yok. Test yok |
| `build_player_index.py` | 311 | P3 | `*_details.json` → `players_registry.json`, `player_match_logs.json` | `run_full_pipeline`'da yok. `parse_player_data` 281 satır |
| `database.py` | 610 | P3/S | parquet/JSON → SQLite şeması ve doldurma, sorgular | Yol sabit `data/premier_league.db`; `populate_db_from_sources` 247 satır; test yok |
| `build_features.py` | 1.389 | P2/P3 | `matches_summary_all.parquet` → `features_matches_all.parquet` | `shift(1)` burada; en büyük özellik modülü. Test: `test_data_leakage`, `test_feature_engineering` |
| `draw_features.py` | 135 | S/P2 | Beraberlik eğilimi özellikleri | Test: `test_draw_features` |

### 4.4 `src/models`

| Dosya | Satır | Rol | Ne yapar | Test |
|---|---:|---|---|---|
| `train_match_outcome.py` | 1.422 | P2 | 1X2 (+O/U) lojistik, kalibrasyon, ensemble; `LOCKED_SEASONS`, `feature_set` burada | `test_match_outcome_splits` |
| `train_goals.py` | 310 | P2 | Gol blend'i seçimi + final fit | `test_goal_selection` |
| `evaluate_goal_models.py` | 478 | P2 | Dış sezon değerlendirmesi, kapılar, piyasa kıyası | **yok** |
| `goals_model.py` | 186 | L | `FeatureGoalModel`, `BlendedGoalModel`, `blend_lambdas` | dolaylı |
| `dixon_coles.py` | 294 | L | Skor matrisi, 1X2/O-U/KG, hizalama | `test_goal_matrix` |
| `model_utils.py` | 385 | L | Güvenli özellik tablosu, kalibratör, beceri kapıları | `test_skill_gate`, `test_match_outcome_splits` |
| `eval_utils.py` | 160 | L | LL, bootstrap, güvenilirlik | `test_eval_utils` |
| `train_corners/throws/saves/cards/offsides.py` | 155–176 (her biri) | P2 | Sayım modelleri; kapıyı geçmezse `training_mean` | **yok** |

### 4.5 `src/analytics`

| Dosya | Satır | Rol | Ne yapar |
|---|---:|---|---|
| `player_ratings.py` | 685 | S | 0–10 oyuncu reytingi, ilk 11 toplulaştırma |
| `team_tactics.py` | 616 | S | Takım taktik profili (4 kullanıcı); test: `test_team_tactics` |
| `model_audit.py` | 452 | S | Model denetim servisi; `model_match_audit` tablosuna yazar (`DELETE … WHERE season`) |
| `prospective_1x2_benchmark.py` | 417 | P1 | `snapshot` ve `score`; append-only JSONL |
| `data_quality_report.py` | 323 | P2 | `data_quality.md` üretir |
| `team_scenarios.py` | 319 | S | Skor durumuna göre şut/köşe oranları |
| `team_data_audit.py` | 253 | P2 | Ham takım istatistiği eksiksizliği |
| `lineup_feature_pilot.py` | 231 | R | İlk 11 sürekliliği 1X2 pilotu |
| `team_attackers.py` | 187 | S | Sezon hücum liderleri |
| `audit_team_scenarios.py` | 105 | P2 | Skor durumu doğrulama raporu |

### 4.6 `src/api`

| Dosya | Satır | Rol | Not |
|---|---:|---|---|
| `server.py` | 3.503 | S | 29 rota, 49 üst düzey fonksiyon. `get_match_full_details` **819**, `predict_match` **406**, `get_team_profile` **294** satır. Modül düzeyinde veri/model yükleme ve ≥8 global önbellek. CORS `allow_origins=["*"]`; `/api/admin/*` kimlik doğrulamasız |

### 4.7 `tests/`, `audit/`, `scratch/`

| Grup | Dosya | Satır | Durum |
|---|---:|---:|---|
| `tests/` | 10 | 574 | 27 test, **hepsi geçti**. `pytest` kurulu değil; `pytest.ini`, `conftest.py` yok. 3 dosya `unittest` sınıfı |
| `audit/` | 9 | 788 | Adli doğrulamalar. Adlar `test_*.py` olduğu için kökten `pytest` bunları toplar. `test_draw_recalibration.py` içe aktarma anında `127.0.0.1:8000`'e **HTTP isteği** atar; 2 tanesi (`test_draw_calibration`, `test_tune_blend`) `server.py`'yi içe aktarır |
| `scratch/` | 13 + 1 JSON | 3.381 | 2026/27 öncesi gol modeli denetimleri (`P0/P1/segment10/XGBoost`). Hepsi tek seferlik; `xgboost` içe aktaran 1 dosya var ama `requirements.txt`'te yok |

## 5. Bağımlılık yapısı

- **Merkezî düğümler:** `dixon_coles` (22 kullanıcı), `model_utils` (17), `goals_model` (15), `eval_utils` (9), `train_match_outcome` (9), `build_features` (6).
- **`LOCKED_SEASONS`**, 1.422 satırlık `train_match_outcome.py` içinde tanımlı; `evaluate_goal_models`, `train_goals`, `lineup_feature_pilot` ve iki `audit` dosyası bu büyük modüle yalnızca sabit için bağlı.
- **Sabit tekrarları (src):** `"data/processed/"` 28 kez / 15 dosya, `"2026_27"` **72 kez / 15 dosya**, `logging.basicConfig` **18 dosyada** (kütüphane modüllerinde, içe aktarmada kök logger'ı yapılandırır).
- **Döngüsel bağımlılık:** AST taramasında tespit edilmedi.

## 6. Bulgular

Önem: **Y** = yüksek, **O** = orta, **D** = düşük.

| # | Önem | Bulgu | Kanıt |
|---|:-:|---|---|
| **B1** | Y | ✅ **ÇÖZÜLDÜ (O1, 19 Ekim 2026)** — **İki farklı "yeniden kur" zinciri.** Haftalık `run_full_pipeline` oyuncu dizinini ve SQLite'ı yeniden kurmaz, 30 dakikalık sync kurar ama model eğitmez. Hangisinin sonra çalıştığına göre veri/ model tutarsızlığı oluşabilir. | §3 tablosu; `sync_season_data.py:239–248`; `run_full_pipeline.py:381–409` |
| **B2** | Y | *(tespit artık otomatik: `pipeline_health`)* **xG/oran içe aktarma cron'da yok; xG varsayılanı 6. haftada kesiyor.** 2026/27'de 69 oynanmış maçın 60'ında xG var, 7. hafta xG'siz. Eksik xG'nin özelliklere etkisi **doğrulanmadı**: `attach_statsapi_xg` sol birleştirme yapar (eksik → NaN); ama 2021/22 sandbox denemesinde xG hiç olmadığı hâlde `xg_ewma` sütunlarında NaN çıkmadı, yani özellik hattında bir yerde dolduruluyor ve nasıl dolduğu incelenmedi. | SQL: oynanan 69, xG 60, eksik hafta {7}; `import_thestatsapi_xg.py --max-gameweek 6`; `crontab` |
| **B3** | Y | **`server.py` monolit.** 3.503 satır, tek işleyicide 819 satır, modül düzeyi veri yükleme (ilk API isteği dahil ~28 sn), 8+ global önbellek. Test, bakım ve çoklu işlem ölçeklemesi zor. | AST fonksiyon uzunlukları; API testinde "Loading cached datasets" ile ilk yanıt arası ~28 sn |
| **B4** | Y | **Test/CI/lint boşluğu.** `pytest` ve `pytest.ini` yok, CI yok, lint yok. Testsiz kritik modüller: `evaluate_goal_models` (yeni kapılar), `database`, `process_season_data`, `sync_*`, `train_*` sayım modelleri, `player_ratings`, `model_audit`, API rotaları. | `requirements.txt`; `ls -a`; test–modül eşlemesi |
| **B5** | O | ✅ **ÇÖZÜLDÜ (O2 aşama A + C, 19 Ekim 2026)** — **Yapılandırma dağınık.** Yollar, `2026_27`, DB yolu, loglama her dosyada ayrı; yeni sezon eklemek 15 dosyada düzenleme gerektirir. `process_season_data`, `database`, `import_thestatsapi_xg` izole dizinde çalıştırılamaz (`--data-dir` yok). | §5 sayıları; 2021/22 deneyinde repoyu kopyalamak gerekti |
| **B6** | O | **`train_*` sayım modelleri kopya-yapıştır.** 5 dosya × ~170 satır, ikili satır benzerliği %42–58. Kapı ve rapor mantığı beş yerde ayrı bakım istiyor. | Jaccard ölçümü (cards–corners 0.45 … saves–throws 0.58) |
| **B7** | O | ✅ **ÇÖZÜLDÜ (H4, 19 Ekim 2026)** — **`audit/` ve `scratch/` depoda (~4.200 satır).** `test_*` adları `pytest` toplamasıyla çakışıyor (içe aktarmada HTTP isteği, `server` yüklemesi). `scratch` tek seferlik ve 2026/27 öncesi sayılara bağlı. | `audit/test_draw_recalibration.py:9–10`; `scratch/*` |
| **B8** | O | **Yönetim ucu ve CORS.** `/api/admin/*` kimlik doğrulamasız, `allow_origins=["*"]`. Sunucuda `127.0.0.1` + Caddy + Tailscale ile azaltılmış, ama kodda koruma yok. 14 Ekim denetimi de aynısını işaretlemişti; hâlâ açık. | `server.py:70, 520–546`; `deploy/Caddyfile` |
| **B9** | O | **`start.py`/`start.sh` portu kullanan her süreci `kill -9` yapar** ve aynı işi iki dosya yapıyor. | `start.py:22–26`, `start.sh:39–42` |
| **B10** | O | ✅ **ÇÖZÜLDÜ (H3, 19 Ekim 2026)** — **Hata sinyali yok.** `fetch_season_data` hataları sayar ama çıkış kodu 0; `import_thestatsapi_xg` xG'siz yanıtı yutar; `job.sh` her zaman 0 döner ve yalnızca bir log dosyası yazar. Cron'dan hata görünmez. | Bu oturumdaki 2021/22 çekimi: "Errors encountered: 1", çıkış 0 |
| **B11** | O | ✅ **ÇÖZÜLDÜ (19 Ekim 2026, `e25aa20`)** — **Repo hijyeni.** 12 MB `.db`, 15 MB `player_match_logs.json`, parquet'ler ve `models/backup/` git'te; çalışma ağacı sürekli kirli, commit'ler şişiyor. | `git ls-files` boyutları; `git status` |
| **B12** | D | **Tekrarlanan yardımcılar:** `atomic_write_json` (2 kopya), `evaluate_season_holdouts` (`model_utils` ve `train_match_outcome`, farklı imza), `build_report` (3 analytics modülü, ayrı mantık), `run_pipeline` (2 ingest). | AST ad çakışmaları |
| **B13** | D | 🔶 **KISMEN (loglama çözüldü, O2/aşama C):** **Kod stili:** 26 çıplak/geniş `except`, 63 `print` / 129 `logger`, 4 dosyada `sys.path` hack'i. | grep sayımları |
| **B14** | D | **Belge sapması:** `scripts_reference.md` "server.py (3430 satır)" diyor, gerçek 3.503; içerikleri satır satır doğrulanmadığını kendisi belirtiyor. `lightgbm` 6 dosyada kullanılıyor ve listede; `xgboost` 1 dosyada (`scratch`) kullanılıyor ama listede yok; `pytest` listede yok. | Bu rapordaki taramalar |
| **B15** | D | **Gizli bilgi taraması temiz:** izlenen dosyalarda anahtar/token bulunmadı, `.env` izlenmiyor. | `git ls-files` + desen taraması |
| **B16** | O | **Zamanlanmış iş tüm API modülünü yükler.** `prospective_1x2_benchmark snapshot` (cron, günde bir) tek bir tahmin için `from src.api.server import df_features, goals_artifact, predict_match` yapıyor; bu, veri tablolarını ve tüm modelleri belleğe alır (~28 sn) ve sunucuyla aynı küresel durumu kurar. Tahmin mantığı API'nin içinde olduğu için cron işi API kodunun yan etkilerine bağlı. Bulgu çalıştırma haritası (§10) çıkarılırken ortaya çıktı. | `src/analytics/prospective_1x2_benchmark.py:69`; §10.5 |

## 7. Güçlü yönler (korunmalı)

- **Sızıntı disiplini:** özellik üretimi `shift(1)`; `test_data_leakage`, `test_draw_features` bunu sınıyor.
- **Atomik yazım** (`*.tmp` → `replace`) ve **kilitli iş sarmalayıcı** (`flock`): eşzamanlı yazımı önlüyor.
- **Tekrar çalıştırılabilirlik:** ingest scriptleri önbelleği atlar, `--force` ile üzerine yazar.
- **Pin'li bağımlılıklar** (`requirements.txt`) ve ayrık `deploy/` klasörü.
- **Ayrık kaynak tabloları:** xG ve oranlar (`external_match_*`) eski alanların üzerine yazmıyor.

## 8. Geliştirme önerileri

Sıra: önce hata sinyali ve veri tutarlılığı, sonra test ve yapılandırma, en sonda büyük yeniden yapılandırma. Efor tahminleri kaba.

### 8.1 Hızlı kazanımlar (her biri yarım gün civarı)

| # | Öneri | Çözdüğü | Not |
|---|---|---|---|
| H1 | **xG ve oran içe aktarmayı cron'a ekle**, `--max-gameweek` varsayılanını sezonun mevcut haftasına bağla (veya kaldır). | B2 | Önce mevcut 7. hafta boşluğunu elle kapat |
| H2 | ✅ **YAPILDI** — **`pytest` ekle:** `requirements-dev.txt`, `pytest.ini` (`testpaths = tests`), `audit/` ve `scratch/`'i toplamadan hariç tut. | B4, B7 | Tek komutla çalışır olsun |
| H3 | ✅ **YAPILDI** — **Hata sinyali:** `fetch_season_data` hata varsa çıkış kodu ≠ 0; xG importer eksik xG sayısını özetle ve bayrakla; `job.sh` hatada `exit 1`. | B10 | |
| H4 | ✅ **YAPILDI** — **`audit/` ve `scratch/` → `research/`** (veya silip git geçmişinde bırak); `test_*` adlarını kaldır. | B7 | `docs/scripts_reference.md` güncelle |
| H5 | **Admin uçlarına ortam değişkeninden jeton** + CORS'u izinli kökenlerle sınırla. | B8 | Mevcut ağ korumasıyla birlikte |
| H6 | `start.py`'yi tek başlatıcı yap, `start.sh`'yi sil veya `start.py`'yi çağıran 3 satıra indir; portu öldürmeden önce onay iste. | B9 | |

### 8.2 Orta vade (1–3 gün)

| # | Öneri | Çözdüğü |
|---|---|---|
| O1 | ✅ **YAPILDI** — **Tek yeniden-kur fonksiyonu** (`src/pipeline/rebuild.py`): `process → player_index → features → db`. `run_full_pipeline` ve `sync_season_data` aynısını çağırır; `run_full_pipeline` adım seçeneği (`--only goals`, `--skip-reports`) ve hatada net durum alır. | B1 |
| O2 | ✅ **YAPILDI** — **`src/config.py`:** yollar, `CURRENT_SEASON`, `LOCKED_SEASONS`, DB yolu, tek `configure_logging()` (yalnızca giriş noktalarında). Süreç/veritabanı/ingest scriptlerine `--data-dir`. | B5, B13 |
| O3 | **Ortak sayım modeli çatısı** (`train_count_model(spec)`): beş `train_*` dosyası yalnızca özellik listesi ve aday kümesini tanımlar. | B6 |
| O4 | **Eksik testler:** `evaluate_goal_models` (null kapısı, KG kapısı, piyasa kıyası), `database.populate_db_from_sources` (geçici DB), `sync_season_data` (sahte sağlayıcı), `server` rotaları (`TestClient`). | B4 |
| O5 | **Yinelenen yardımcıları birleştir:** `atomic_write_json` ortak modüle; `LOCKED_SEASONS` config'e; iki `evaluate_season_holdouts`'u adlandır/ortakla. | B12 |
| O6 | **Ruff + `pre-commit`** (biçim + temel hatalar); çıplak `except`'leri daralt. | B13 |
| O7 | **Tahmin mantığını API'den ayır:** `predict_match` ve ona bağlı küresel durumu (`df_features`, model artifact'ları) `src/serving/` altında bir modüle taşı; `server.py` ve `prospective_1x2_benchmark` aynı modülü çağırsın. U1 ile birlikte yapılabilir. | B16, B3 |

### 8.3 Büyük işler (3+ gün)

| # | Öneri | Çözdüğü |
|---|---|---|
| U1 | **`server.py`'yi `APIRouter` modüllerine böl** (`predict`, `fixtures`, `teams`, `players`, `referees`, `admin`), 819 ve 406 satırlık işleyicileri servis fonksiyonlarına ayır, veri yüklemeyi `startup`'a taşı. | B3 |
| U2 | ✅ **YAPILDI (`e25aa20`)** — **Veri/model dosyalarını git'ten çıkar:** `.db`, büyük parquet/JSON ve `models/backup/` için `.gitignore` veya Git LFS; yeniden üretim komutunu belgele. | B11 |
| U3 | **CI** (GitHub Actions): `pytest`, `ruff`, `npm run build` her push'ta. | B4 |

### 8.4 Önerilen sıra

1. **H1 + H3** (veri boşluğu ve sessiz hatalar, en az emekle en çok risk azaltır)
2. **H2 + H4** (test altyapısı, gürültünün temizlenmesi)
3. **O1 + O2** (zincir ve yapılandırma birliği; sonraki her işi kolaylaştırır)
4. **O4 → O3 → O5**
5. **H5, H6** (kolay, bağımsız)
6. **U1 → U2 → U3** (ayrı sprint)

## 9. Bu raporun dışında kalanlar

Frontend kodu (`frontend/src`), `docs/reports/*` içindeki otomatik raporların içeriği, modellerin istatistiksel sonuçları (bkz. `GOAL_MODELS_ANALYSIS.md` ve model raporları), dış servislerin kullanım koşulları.

## 10. Çalıştırma haritası: hangi script neyi çalıştırır

Bu bölüm koddan üretildi (AST ile içe aktarmalar, `subprocess` hedefleri ve `deploy/crontab`); elle yazılan kısım yalnızca kabuk/cron açıklamaları. Sütunlar:
- **Nasıl çalışır:** scripti kim ve ne zaman başlatır (cron, haftalık pipeline aşaması, zincir adımı, elle).
- **Çalıştırdığı / çağırdığı proje modülleri:** içe aktardığı veya alt süreç olarak başlattığı diğer proje dosyaları (`src.config` hariç, her dosya onu kullanır).
- **Alt süreç olarak başlattığı:** ayrı yorumlayıcıda çalıştırdığı modüller.
- **Dış servis:** koda gömülü adreslere göre; PulseLive, TheStatsAPI, Transfermarkt, PL foto CDN.
- **Dokunduğu konumlar:** kullandığı `src.config` yolları (okuma ve yazma ayrımı yapılmaz).
- **Kimler çağırır:** üretim kodundan (testler ve `research/` hariç) onu içe aktaran veya başlatan dosyalar.

Sınırlar: dinamik içe aktarmalar ve komut satırı dizeleriyle kurulan çağrılar (örneğin `uvicorn src.api.server:app`) yalnızca bilinen kalıplarla yakalandı; `Dokunduğu konumlar` yol sabitlerinin kullanımına bakar, dosya adını doğrudan yazan kodu göstermez.

#### 10.1 Kök

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `run_full_pipeline.py` | cron Pazartesi 04:00 (`python run_full_pipeline.py`) | `analytics/audit_team_scenarios`, `analytics/data_quality_report`, `analytics/team_data_audit`, `db/database`, `models/evaluate_goal_models`, `models/train_cards`, `models/train_corners`, `models/train_goals`, `models/train_match_outcome`, `models/train_offsides`, `models/train_saves`, `models/train_throws`, `pipeline/rebuild` | - | - | ham JSON, işlenmiş tablolar, raporlar | - |
| `start.py` | elle (`python3 start.py`) | `api/server` | `api/server` | - | - | - |

#### 10.2 `src/ingest`

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `src/ingest/fetch_season_data.py` | elle (`python -m`) | - | - | PulseLive | veri dizini | `ingest/fetch_team_staff`, `ingest/sync_prematch_lineups`, `ingest/sync_season_data` |
| `src/ingest/fetch_team_staff.py` | elle (`python -m`) | `ingest/fetch_season_data` | - | - | ham JSON, işlenmiş tablolar | - |
| `src/ingest/fetch_transfermarkt_market_values.py` | elle (`python -m`) | - | - | Transfermarkt | işlenmiş tablolar, SQLite, veri dizini | - |
| `src/ingest/import_thestatsapi_odds.py` | elle (`python -m`) | `ingest/import_thestatsapi_xg` | - | TheStatsAPI | SQLite | `ingest/sync_prematch_lineups` |
| `src/ingest/import_thestatsapi_xg.py` | elle (`python -m`) | - | - | TheStatsAPI | SQLite | `ingest/import_thestatsapi_odds` |
| `src/ingest/sync_prematch_lineups.py` | cron her 5 dk (`-m … --hours-ahead 1`) | `analytics/player_ratings`, `features/build_features`, `ingest/fetch_season_data`, `ingest/import_thestatsapi_odds`, `models/dixon_coles`, `models/model_utils` | - | PulseLive, TheStatsAPI (yalnızca `--refresh-odds`) | ham JSON, işlenmiş tablolar, SQLite, veri dizini, modeller | `api/server` |
| `src/ingest/sync_season_data.py` | cron her 30 dk (`-m`) | `ingest/fetch_season_data`, `pipeline/rebuild` | - | PulseLive | veri dizini | `api/server` |

#### 10.3 `src/processing`, `src/pipeline`, `src/db`, `src/features`

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `src/db/database.py` | zincir adımı `database` (cron sync + haftalık) | - | - | - | ham JSON, SQLite, veri dizini | `api/server`, `features/build_features`, `pipeline/rebuild`, `run_full_pipeline` |
| `src/features/build_features.py` | zincir adımı `features` (cron sync + haftalık) | `analytics/player_ratings`, `db/database`, `features/draw_features` | - | - | ham JSON, işlenmiş tablolar, SQLite | `api/server`, `ingest/sync_prematch_lineups`, `pipeline/rebuild` |
| `src/features/draw_features.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | - | `api/server`, `features/build_features`, `models/train_match_outcome` |
| `src/pipeline/rebuild.py` | kütüphane (başka scriptler içe aktarır) | `db/database`, `features/build_features`, `processing/build_player_index`, `processing/process_season_data` | `db/database`, `features/build_features`, `processing/build_player_index`, `processing/process_season_data` | - | - | `ingest/sync_season_data`, `run_full_pipeline` |
| `src/processing/build_player_index.py` | zincir adımı `player_index` (cron sync + haftalık) | - | - | PL foto CDN | ham JSON, işlenmiş tablolar | `pipeline/rebuild` |
| `src/processing/process_season_data.py` | zincir adımı `process` (cron sync + haftalık) | - | - | - | ham JSON, işlenmiş tablolar | `pipeline/rebuild` |

#### 10.4 `src/models`

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `src/models/dixon_coles.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | - | `analytics/model_audit`, `api/server`, `ingest/sync_prematch_lineups`, `models/evaluate_goal_models`, `models/goals_model`, `models/train_goals`, `models/train_match_outcome` |
| `src/models/eval_utils.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | - | `analytics/lineup_feature_pilot`, `analytics/prospective_1x2_benchmark`, `models/evaluate_goal_models`, `models/train_goals`, `models/train_match_outcome` |
| `src/models/evaluate_goal_models.py` | haftalık pipeline aşaması `goals` | `models/dixon_coles`, `models/eval_utils`, `models/goals_model`, `models/model_utils`, `models/train_goals`, `models/train_match_outcome` | - | - | işlenmiş tablolar, SQLite | `run_full_pipeline` |
| `src/models/goals_model.py` | kütüphane (başka scriptler içe aktarır) | `models/dixon_coles` | - | - | - | `models/evaluate_goal_models`, `models/train_goals` |
| `src/models/model_utils.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | - | `analytics/lineup_feature_pilot`, `analytics/model_audit`, `api/server`, `ingest/sync_prematch_lineups`, `models/evaluate_goal_models`, `models/train_cards`, `models/train_corners`, `models/train_goals`, `models/train_match_outcome`, `models/train_offsides`, `models/train_saves`, `models/train_throws` |
| `src/models/train_cards.py` | haftalık pipeline aşaması `counts` | `models/model_utils` | - | - | işlenmiş tablolar, modeller | `run_full_pipeline` |
| `src/models/train_corners.py` | haftalık pipeline aşaması `counts` | `models/model_utils` | - | - | işlenmiş tablolar, modeller | `run_full_pipeline` |
| `src/models/train_goals.py` | haftalık pipeline aşaması `goals` | `models/dixon_coles`, `models/eval_utils`, `models/goals_model`, `models/model_utils`, `models/train_match_outcome` | - | - | işlenmiş tablolar, modeller | `models/evaluate_goal_models`, `run_full_pipeline` |
| `src/models/train_match_outcome.py` | haftalık pipeline aşaması `outcome` | `features/draw_features`, `models/dixon_coles`, `models/eval_utils`, `models/model_utils` | - | - | işlenmiş tablolar, modeller | `analytics/lineup_feature_pilot`, `models/evaluate_goal_models`, `models/train_goals`, `run_full_pipeline` |
| `src/models/train_offsides.py` | haftalık pipeline aşaması `counts` | `models/model_utils` | - | - | işlenmiş tablolar, modeller | `run_full_pipeline` |
| `src/models/train_saves.py` | haftalık pipeline aşaması `counts` | `models/model_utils` | - | - | işlenmiş tablolar, modeller | `run_full_pipeline` |
| `src/models/train_throws.py` | haftalık pipeline aşaması `counts` | `models/model_utils` | - | - | işlenmiş tablolar, modeller | `run_full_pipeline` |

#### 10.5 `src/analytics`

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `src/analytics/audit_team_scenarios.py` | haftalık pipeline aşaması `audits` | `analytics/team_scenarios`, `analytics/team_tactics` | - | - | raporlar | `run_full_pipeline` |
| `src/analytics/data_quality_report.py` | haftalık pipeline aşaması `audits` | - | - | - | ham JSON, işlenmiş tablolar, raporlar | `run_full_pipeline` |
| `src/analytics/lineup_feature_pilot.py` | elle (`python -m`) | `models/eval_utils`, `models/model_utils`, `models/train_match_outcome` | - | - | ham JSON, işlenmiş tablolar, raporlar | - |
| `src/analytics/model_audit.py` | elle (`python -m`) | `models/dixon_coles`, `models/model_utils` | - | - | işlenmiş tablolar, SQLite, veri dizini, modeller | `api/server` |
| `src/analytics/pipeline_health.py` | elle (`python -m`) | - | - | - | ham JSON, işlenmiş tablolar, SQLite, modeller | - |
| `src/analytics/player_ratings.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | ham JSON, işlenmiş tablolar, veri dizini | `api/server`, `features/build_features`, `ingest/sync_prematch_lineups` |
| `src/analytics/prospective_1x2_benchmark.py` | cron 06:30 `snapshot`, 23:15 `score` (`-m`) | `api/server`, `models/eval_utils` | - | - | işlenmiş tablolar, modeller, raporlar | - |
| `src/analytics/team_attackers.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | işlenmiş tablolar | `api/server` |
| `src/analytics/team_data_audit.py` | haftalık pipeline aşaması `audits` | - | - | - | ham JSON, raporlar | `run_full_pipeline` |
| `src/analytics/team_scenarios.py` | kütüphane (başka scriptler içe aktarır) | `analytics/team_tactics` | - | - | ham JSON | `analytics/audit_team_scenarios`, `api/server` |
| `src/analytics/team_tactics.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | ham JSON | `analytics/audit_team_scenarios`, `analytics/team_scenarios`, `api/server` |

#### 10.6 `src/api`, `src/config.py`

| Script | Nasıl çalışır | Çalıştırdığı / çağırdığı proje modülleri | Alt süreç olarak başlattığı | Dış servis | Dokunduğu konumlar | Kimler çağırır |
|---|---|---|---|---|---|---|
| `src/api/server.py` | systemd `plm-api` (`uvicorn`); geliştirmede `start.py` | `analytics/model_audit`, `analytics/player_ratings`, `analytics/team_attackers`, `analytics/team_scenarios`, `analytics/team_tactics`, `db/database`, `features/build_features`, `features/draw_features`, `ingest/sync_prematch_lineups`, `ingest/sync_season_data`, `models/dixon_coles`, `models/model_utils` | `ingest/sync_prematch_lineups`, `ingest/sync_season_data` | PL foto CDN, Transfermarkt | veri dizini, modeller | `analytics/prospective_1x2_benchmark`, `start` |
| `src/config.py` | kütüphane (başka scriptler içe aktarır) | - | - | - | ham JSON, işlenmiş tablolar, SQLite, veri dizini, modeller, raporlar | - |

#### 10.7 Kabuk, cron ve systemd dosyaları

| Dosya | Ne çalıştırır |
|---|---|
| `start.py` | `lsof` ile 8000 ve 5173 portlarını kullanan süreçleri `SIGKILL` eder; `frontend/node_modules` yoksa `npm install`; `python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload` (Popen) ve `npm run dev` (Popen); Ctrl+C'de ikisini kapatır |
| `start.sh` | `start.py` ile aynı işin bash sürümü: `lsof` + `kill -9`, `npm --prefix frontend install`, `python3 -m uvicorn src.api.server:app … --reload`, `npm --prefix frontend run dev` |
| `deploy/job.sh <ad> <komut…>` | `flock -w 600 /tmp/plm.lock <komut…>` (tüm işler tek kilit altında), çıktıyı `logs/<ad>.log`'a ekler, hata kodunu `logs/failures.log`'a yazar ve döndürür; `data/premier_league.db` veya `features_matches_all.parquet` değiştiyse `systemctl restart plm-api` |
| `deploy/setup.sh` | `apt-get` paketleri, `python3 -m venv` + `pip install -r requirements.txt`, `npm ci && npm run build` (frontend), `plm-api.service` ve `Caddyfile` kopyalar, `systemctl enable --now plm-api`, `crontab deploy/crontab`, `ufw`, Tailscale kurulumu |
| `deploy/plm-api.service` | `/opt/plm/venv/bin/uvicorn src.api.server:app --host 127.0.0.1 --port 8000` (`Restart=always`, ortam `/opt/plm/.env`) |
| `deploy/Caddyfile` | `:8080` (yalnızca localhost): `/api/*` → `127.0.0.1:8000`; diğer her şey `frontend/dist` |
| `deploy/crontab` | Aşağıdaki 5 iş |

**Zamanlanmış işler (`deploy/crontab`, hepsi `job.sh` ile):**

| Zaman (UTC) | İş adı | Komut | Sonrasında tetiklediği |
|---|---|---|---|
| her 30 dk | `sync` | `python -m src.ingest.sync_season_data` | PulseLive'dan fikstür, hakem ve biten maç dosyaları; veri değiştiyse `rebuild_derived_data()` → `process` → `player_index` → `features` → `database` |
| her 5 dk | `lineups` | `python -m src.ingest.sync_prematch_lineups --hours-ahead 1` | Önümüzdeki 1 saatteki maçların resmi ilk 11'i; ham detay dosyası ve ilk 11 özellikleri güncellenir |
| Pazartesi 04:00 | `train` | `python run_full_pipeline.py` | `rebuild` → `audits` → `counts` → `outcome` → `goals` → `model_benchmarks.md` |
| her gün 06:30 | `benchmark` | `python -m src.analytics.prospective_1x2_benchmark snapshot` | Maç öncesi 1X2 tahminini `1x2_forecast_log.jsonl`'a yazar |
| her gün 23:15 | `benchmark` | `python -m src.analytics.prospective_1x2_benchmark score` | Biten maçları puanlar, `prospective_1x2_scorecard.json` |

**API'nin kendi başlattığı süreçler** (`/api/admin/sync-season`, kimlik doğrulamasız): `sync_season_data.py --season-name <sezon>` (`matches`), aynısı `--referees-only` (`referees`), `python -m src.ingest.sync_prematch_lineups --season <sezon> --hours-ahead 2` (`lineups`).

**Zincirler:**

```
rebuild_derived_data()  (src/pipeline/rebuild.py)
  process_season_data --season-name all ─► matches_summary_*.parquet, shots_events_*.parquet
  build_player_index ─────────────────────► players_registry.json, player_match_logs.json
  build_features ─────────────────────────► features_matches_all.parquet   (xG tablosunu SQLite'tan okur)
  src.db.database ────────────────────────► premier_league.db

run_full_pipeline.py
  rebuild  ─► rebuild_derived_data()
  audits   ─► data_quality_report, team_data_audit, audit_team_scenarios
  counts   ─► train_corners, train_throws, train_saves, train_cards, train_offsides
  outcome  ─► train_match_outcome
  goals    ─► evaluate_goal_models ─► train_goals
  (counts + outcome ikisi de çalıştıysa) ─► docs/reports/model_benchmarks.md
```

#### 10.8 `tests/` (`pip install -r requirements-dev.txt && pytest`)

| Test dosyası | Sınadığı proje modülleri |
|---|---|
| `tests/test_config.py` | `models/train_match_outcome` |
| `tests/test_data_leakage.py` | `features/build_features` |
| `tests/test_draw_features.py` | `features/draw_features` |
| `tests/test_eval_utils.py` | `models/eval_utils` |
| `tests/test_feature_engineering.py` | `features/build_features` |
| `tests/test_goal_matrix.py` | `models/dixon_coles` |
| `tests/test_goal_selection.py` | `models/train_goals` |
| `tests/test_inference_logic.py` | `api/server` |
| `tests/test_match_outcome_splits.py` | `models/model_utils`, `models/train_match_outcome` |
| `tests/test_pipeline_health.py` | `analytics/pipeline_health` |
| `tests/test_rebuild.py` | `run_full_pipeline` |
| `tests/test_skill_gate.py` | `models/model_utils` |
| `tests/test_team_tactics.py` | `analytics/team_tactics` |

#### 10.9 `research/` (elle: `PYTHONPATH=. python3 research/…`; cron, pipeline ve pytest dışı)

| Script | Çağırdığı proje modülleri |
|---|---|
| `research/audit/draw_calibration.py` | `api/server`, `models/model_utils` |
| `research/audit/draw_recalibration.py` | - |
| `research/audit/investigation_1.py` | `features/build_features` |
| `research/audit/investigation_2.py` | `models/train_match_outcome` |
| `research/audit/investigation_3.py` | - |
| `research/audit/investigation_4.py` | - |
| `research/audit/investigation_5.py` | `models/dixon_coles` |
| `research/audit/investigation_6.py` | `models/eval_utils`, `models/model_utils`, `models/train_match_outcome` |
| `research/audit/tune_blend.py` | `api/server`, `models/model_utils` |
| `research/scratch/audit_multiple_testing_and_permutation_importance.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/deep_dive_p0_investigation.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/diagnose_segment10_and_test_xgboost.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/execute_deep_dive_audit_p0_p1.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/execute_p0_final_closure.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/execute_p0_final_tasks.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/execute_p1_final_verifications.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/extract_all_goal_metrics.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/key_passes_impact.py` | `models/dixon_coles`, `models/eval_utils`, `models/goals_model`, `models/train_match_outcome` |
| `research/scratch/rigorous_p1c_evaluation.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/run_p1a_auc_segmentation.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/segment10_distribution_and_features.py` | `models/dixon_coles`, `models/goals_model` |
| `research/scratch/tactical_pace_and_mv.py` | `models/dixon_coles`, `models/eval_utils`, `models/goals_model`, `models/train_match_outcome` |

## 11. Uygulama günlüğü

| Tarih | Madde | Yapılan | Doğrulama |
|---|---|---|---|
| 19 Ekim 2026 | **H3** hata sinyali | `fetch_season_data` hatada çıkış 1; `import_thestatsapi_xg` xG'siz maç/eşleşmeyen fikstürde çıkış 1; `deploy/job.sh` iş çıkış kodunu döndürür ve `failures.log`'a yazar | `test_fetch_season_data_exits_nonzero_when_any_match_failed`; `bash -n` |
| 19 Ekim 2026 | **Yeni script** `src/analytics/pipeline_health.py` | Veri/model sağlık kontrolü, 4 testle | Gerçek veride 1 FAIL buldu: `93656_details.json` eksikti (Luton–Brentford 2023/24); indirildi, FAIL kalmadı. Kalan uyarı: 2026/27 7. hafta xG'si (9 maç) |
| 19 Ekim 2026 | **H2** pytest | `requirements-dev.txt` (pytest 8.3.4) ve `pytest.ini` (`testpaths = tests`, `research/` hariç) | Kökten `pytest -q`: **31 test geçti** (48 sn), `research/` toplanmadı |
| 19 Ekim 2026 | **H4** research | `audit/` ve `scratch/` → `research/audit`, `research/scratch` (`git mv`, geçmiş korunur); `test_` önekleri kaldırıldı; `research/README.md` eklendi | Taşınan scriptlerin derlenmesi; `extract_all_goal_metrics.py` yolu güncellendi |
| 19 Ekim 2026 | **O2 / aşama A** `src/config.py` | ~30 dosyadaki sabit yollar ve `LOCKED_SEASONS` tek modüle taşındı; `PLM_DATA_DIR` ve `PLM_MODELS_DIR` eklendi; bağımsız çalışan scriptlere `python3 src/...py` için önyükleme satırı | **Eski kod (HEAD) ile yeni kod, izole veri dizininde aynı zinciri koştu: 14 parquet, 4 JSON, 14 SQLite tablosu birebir aynı.** Repo verisinin mtime'ı değişmedi. 33 test geçti, API açılıyor |
| 19 Ekim 2026 | **Bulgu:** `sync_season_data` `-m` ile çalışmıyordu | `from fetch_season_data import …` yalnızca script modunda çalışır; `deploy/crontab` `python -m src.ingest.sync_season_data` kullanıyor. `from src.ingest.fetch_season_data import …` olarak düzeltildi, iki mod da denendi | Orijinal kodda `ModuleNotFoundError` doğrulandı (stash ile) |
| 19 Ekim 2026 | **O1 / aşama B** tek zincir | `src/pipeline/rebuild.py` (4 adım, ayrı süreç, ilk hatada durur). `sync_season_data` ve `run_full_pipeline` aynı fonksiyonu kullanır. `run_full_pipeline` aşamalı oldu (`--only`, `--skip`), hatada çıkış 1. **Davranış değişikliği:** haftalık eğitim artık oyuncu dizinini ve veritabanını da yeniden kurar | 5 yeni test. İzole dizinde `--only rebuild` çıktıları referansla birebir aynı; `--only goals` çalıştı ve aynı üretim ayarını seçti; üretim modeli md5'i değişmedi; `--only nonsense` çıkış 2 |
| 19 Ekim 2026 | **O2 / aşama C** sezon ve loglama | `config.DEFAULT_SEASON` (env `PLM_SEASON`, yoksa en yeni `fixtures_*.json`) ve `config.SEASONS`; ~40 "2026_27" varsayılanı/karşılaştırması bunlara bağlandı (tarihsel/anlamsal olanlar bilerek kaldı: `lineup_feature_pilot`, Transfermarkt kayıtları, sıralama sözlüğü). Modül içe aktarılırken `logging.basicConfig` çağıran 12 dosya `configure_logging()`'e taşındı, yalnızca giriş noktalarında çağrılır | 39 test; 63 modülün içe aktarılması sessiz; izole `--only rebuild` çıktıları referansla birebir aynı (14 parquet, 2 JSON, 13 SQLite tablosu); API 4 rota 200 |
| 19 Ekim 2026 | **Çalıştırma haritası** (§10) | Tüm 75 Python dosyası, kabuk/cron/systemd dosyaları, testler ve `research/` için "neyi çalıştırır, kim çalıştırır, hangi dış servise dokunur" tabloları koddan üretildi (AST + `subprocess` hedefleri + `deploy/crontab`) | Yeni bulgu B16: cron `snapshot` işi tüm API modülünü yüklüyor; öneri O7 eklendi |
