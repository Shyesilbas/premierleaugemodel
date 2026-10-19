# Script Referansı

Projedeki tüm çalıştırılabilir script ve modüllerin ne işe yaradığı. Kaynak: her dosyanın docstring'i ve fonksiyon listesi (içerikleri satır satır doğrulanmadı). `node_modules`, `frontend/src` (React bileşenleri) ve `graphify-out` kapsam dışı.

Tipik veri akışı: **ingest** (ham JSON indir) → **processing** (Parquet/SQLite) → **features** (sızıntısız özellikler) → **models** (eğitim) → **api** (servis) → **frontend**.

## 0. Yapılandırma ve ortam değişkenleri

`src/config.py` projedeki tüm yolların ve sezon politikasının tek kaynağıdır (`ROOT`, `DATA_DIR`, `RAW_DIR`, `PROCESSED_DIR`, `DB_PATH`, `MODELS_DIR`, `REPORTS_DIR`, `LOCKED_SEASONS`, `EXCLUDED_1X2_TRAINING_SEASONS`).

| Değişken | Etkisi |
|---|---|
| `PLM_DATA_DIR` | Veri dizinini (`raw/`, `processed/`, SQLite) değiştirir; pipeline'ı izole bir veri kopyasında çalıştırmak için. Varsayılan `<repo>/data`. |
| `PLM_SEASON` | Betiklerin varsayılan sezonu. Verilmezse `data/raw/fixtures_*.json` içindeki en yeni sezon (`config.DEFAULT_SEASON`); tüm önbellek sezonları `config.SEASONS`. |
| `PLM_ADMIN_TOKEN` | Tanımlıysa `/api/admin/*` uçları (senkron başlat/durum, model yenile) `X-Admin-Token` başlığında bu değeri ister (ASCII, örn. `openssl rand -hex 24`); tanımsızsa uçlar açık kalır ve bir kez uyarı loglanır. **Sunucuda `/opt/plm/.env` içine ekleyin.** Arayüz jetonu `localStorage.setItem('plm_admin_token', '<jeton>')` ile okur. |
| `PLM_CORS_ORIGINS` | API'yi tarayıcıdan çağırabilecek kökenler (virgülle). Varsayılan yerel geliştirme sunucuları (`localhost:5173`, `localhost:8080`); `*` artık varsayılan değil. Aynı kökenden gelen trafik (Vite proxy, Caddy) CORS gerektirmez. |
| `PLM_REPORTS_DIR` | Üretilen raporların (`data_quality.md`, `prospective_1x2_scorecard.json` ...) yazıldığı dizin. Varsayılan `docs/reports`. İzole denemelerde gerçek raporları ezmemek için. |
| `PLM_MODELS_DIR` | Model dizinini değiştirir. Varsayılan `<repo>/models/production`. |

Örnek: `PLM_DATA_DIR=/tmp/veri python3 -m src.processing.process_season_data --season-name all`.

## 1. Kök dizin

| Dosya | Ne yapar |
|---|---|
| `start.py` | Backend (uvicorn, `:8000`, `--reload`) ve frontend'i (Vite, `:5173`) birlikte başlatır, Ctrl+C ile ikisini kapatır. Başlamadan önce portlarda **bu projenin** eski sürecini kapatır; başka bir uygulama varsa dokunmadan durur (`--force` ile kapatır). |
| `start.sh` | `start.py`'yi çağıran ince sarmalayıcı (`exec python3 start.py "$@"`). |
| `run_full_pipeline.py` | Ana pipeline, **aşamalı**: `rebuild` (işleme → oyuncu dizini → özellikler → veritabanı), `audits`, `counts` (köşe, atış, kurtarış, kart, ofsayt), `outcome` (1X2), `goals` (değerlendirme + eğitim). `--only goals`, `--skip rebuild,audits`; geçersiz aşama çıkış 2, hatada çıkış 1. Sağlayıcıya bağlanmaz. |

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
| `sync_prematch_lineups.py` | Maç öncesi **resmi ilk 11'i** çeker, `data/raw/matches/*_details.json` önbelleğini günceller, özellik tablosundaki ilk 11 reytinglerini yazar ve "son maç 11'i" ile "resmi 11" tahminlerini yan yana yazdırır. `--match-id`, `--team`, `--gameweek`, `--hours-ahead` seçenekleri var. |
| `fetch_team_staff.py` | Takımların kadro ve teknik ekip (görevli) bilgisini çeker, `data/processed/team_staff.json`'a yazar. |
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
| `database.py` | SQLite katmanı (`data/premier_league.db`): şema, kaynaklardan doldurma (`populate_db_from_sources`), hakem özetleri, gruplanmış fikstür sorguları, xG ekleme. API'nin çalışma anında ağır Parquet/JSON okumasını önler. |

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
| `prospective_1x2_benchmark.py` | **İleriye dönük test:** `snapshot` maç öncesi 1X2 tahminini append-only `1x2_forecast_log.jsonl`'a kaydeder, `score` maçlar bitince puanlar. Paper trading protokolünün temeli. |
| `model_audit.py` | Model çıktılarını gerçek sonuçlar ve kapanış oranlarıyla denetler: kalibrasyon, eşik, değer farkı. |
| `data_quality_report.py` | Veri envanteri ve ham metrik kapsamı raporu (`data_quality.md`). |
| `team_data_audit.py` | Ham takım istatistiklerinin eksiksizliğini denetler (eksik ile sıfırı ayırır). |
| `audit_team_scenarios.py` | Skor durumu ve köşe olayları doğrulama raporu. |
| `team_scenarios.py` | Olay akışından skor durumuna göre şut ve köşe oranları. |
| `team_tactics.py` | Ham maç istatistiklerinden takım taktik profili (API tarafından kullanılır). |
| `team_attackers.py` | Takımın sezon hücum liderleri (oyuncu kayıtları ve şut olaylarından). |
| `player_ratings.py` | 0-10 oyuncu reytingi (genel, hücum, savunma, kart riski): son 5 maç EWMA %70 + sezon tabanı %30. Tahmini ve resmi ilk 11 toplulaştırması. |
| `pipeline_health.py` | **Sağlık kontrolü** (yalnızca okur): sezon başına xG ve oran kapsamı, eksik ham dosyalar, özellik/veritabanı uyumsuzluğu, bayat model dosyaları. `python3 -m src.analytics.pipeline_health [--strict] [--json]`; FAIL varsa çıkış kodu 1. |
| `lineup_feature_pilot.py` | İlk 11 sürekliliği özelliği 1X2'ye sinyal katıyor mu, üretimi değiştirmeden dener. |

## 8. `src/api/`

| Dosya | Ne yapar |
|---|---|
| `server.py` | İnce giriş noktası (~50 satır): `FastAPI` uygulaması, CORS, veri değişince yeniden yükleme ara katmanı, yönlendiricileri bağlar, `/` ve `__main__`. |
| `state.py` | Yüklü veri çerçeveleri, model artifact'ları, önbellekler ve yeniden yükleme (`reload_runtime_datasets`). **İçe aktarılınca her şeyi yükler (~30 sn).** Veri yeniden yüklemede değişkenler yeniden bağlanır; diğer modüller bunları yalnızca `state.<ad>` olarak okur (`from src.api.state import <değişken>` yapmayın). |
| `security.py` | Yönetim ucu jetonu (`require_admin_token`) ve CORS kökenleri (`cors_origins`). |
| `routes/meta.py` | `/api/data-version`, `/api/admin/*` (model yenileme, sezon senkronu; `PLM_ADMIN_TOKEN` ile korunur). |
| `routes/teams.py` | `/api/teams*`: kadro/teknik ekip, teknik direktör, profil, transfer, taktik, hücum liderleri, senaryolar. |
| `routes/fixtures.py` | `/api/fixtures*`, `/api/standings`, `/api/referees*`, `/api/match/{id}/recent-form`. |
| `routes/players.py` | `/api/players*`: arama, profil, piyasa değeri geçmişi, reyting. |
| `routes/matches.py` | `/api/match/{id}/details` ve `/odds`. |
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
| `test_team_tactics.py` | Takım taktik özetleri. |
| `test_pipeline_health.py` | Sağlık kontrolü (xG boşluğu, eksik ham dosya) ve `fetch_season_data` çıkış kodu. |
| `test_config.py`, `test_rebuild.py` | Yapılandırma (`PLM_DATA_DIR`, `PLM_SEASON`) ve tek yeniden-kur zinciri, aşama seçimi. |
| `test_stats_api_imports.py` | xG ve oran içe aktarıcıları (sahte API istemcisiyle): tavansız xG, 404 dayanıklılığı, kayıtlı maçları atlama. |
| `test_database.py` | `populate_db_from_sources`: maç/yaklaşan fikstür/hakem özetleri, ikinci çalıştırmada değişmeme, xG tablosunun korunması. |
| `test_sync_helpers.py` | `sync_season_data` saf yardımcıları: tamamlanma, skor, takım adı eşleme, hakem. |
| `test_evaluate_goal_models.py` | Gol kapıları (sabit Poisson, KG, piyasa) sentetik veriyle, piyasa marjı temizleme. |
| `test_api_routes.py` | API rota duman testleri ve tahmin tutarlılığı (`needs_data`). |

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

## 12. `deploy/` — sunucu dosyaları (yeni)

`setup.sh` (Ubuntu kurulumu), `job.sh` (kilitli iş sarmalayıcı), `crontab`, `plm-api.service`, `Caddyfile`. Ayrıntı için sunucuya kurulum notlarına bakın.

## 13. Frontend yapılandırması

`frontend/vite.config.js` (dev sunucu `:5173`, `/api` isteklerini `:8000`'e yönlendirir), `tailwind.config.js`, `postcss.config.js`.

## Zamanlama için notlar

- Sürekli çalışması gerekenler: `sync_season_data` (hakem + biten maç), `sync_prematch_lineups` (kadro).
- `prospective_1x2_benchmark.py snapshot` periyodik çalışmalı, aksi halde ileriye dönük test kaydı boş kalır. `deploy/crontab`'a eklendi: `snapshot` 06:30 UTC, `score` 23:15 UTC. Script bir maç için günde yalnızca 1 tahmin kaydeder, bu yüzden kayıt maç günü sabahki (resmi kadro öncesi) tahmin olur.
- `run_full_pipeline.py` ağırdır, haftalık yeterli.
