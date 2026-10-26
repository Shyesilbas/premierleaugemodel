# Project Rules — Premier League Model App

Premier League maçları için makine öğrenmesi tahmin motoru, analitik ETL hattı, FastAPI backend ve React/Tailwind arayüzü.

## Uzmanlaşmış Agent Skill'leri (`.agents/skills/`)
Detaylı iş akışları ve standartlar `.agents/skills/` altındadır; ilgili görevlerde mutlaka bu skill'leri oku ve uygula:
- **`quant-model-experiment-and-audit`** (`.agents/skills/quant-model-experiment-and-audit/SKILL.md`): Model deneyleri, özellik ablasyonları, sıfır sızıntı (`shift(1)` ve OOF kalibrasyon), kilitli sezon (`2026/27`), dış sezon skill gate (`training_mean` / prior karşılaştırması), bootstrap CI, ortak skor matrisi tutarlılığı ve rapor/registry güncelleme zinciri.
- **`sports-pipeline-and-paper-trading`** (`.agents/skills/sports-pipeline-and-paper-trading/SKILL.md`): Veri çekme/ETL, olay akışından istatistik kurtarma, SQLite veritabanı (`data/football.db`), maç öncesi append-only tahmin kaydı (`1x2_forecast_log.jsonl`) ve puan kartı (`prospective_1x2_scorecard.json`) akışı.
- **`restrained-ui-design-standard`** (`.agents/skills/restrained-ui-design-standard/SKILL.md`): Apple/Spotify-tier sade arayüz tasarım kuralları, semantik tokenlar, radius tavanı (`rounded-md`), 4 veri durumu (loading/empty/error/pending) ve iş bitimi zorunlu lint/regex kontrolleri.

## Hızlı Komutlar
- **Uygulamayı Başlat (Backend + Frontend):** `python3 start.py`
- **Tüm Pipeline'ı Çalıştır (ETL + Model Eğitimi + Benchmark):** `python3 run_full_pipeline.py`
- **Maç Öncesi Tahmin Kaydı (Paper Trading):** `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14`
- **Testleri Çalıştır:** `pytest`
- **Frontend Geliştirme & Doğrulama:** `cd frontend && npm run lint && npm run build`
- **Veritabanı Sorgulama:** `sqlite3 data/football.db "SELECT ... LIMIT 5;"` (`.db` ve `.parquet` dosyalarını asla metin olarak doğrudan okuma).

## Mimari Özeti & Dokümantasyon Haritası
- **Aktif Üretim Modelleri (`models/production/premier_league/`; her turnuvanın modelleri kendi alt klasöründe, verisi `data/competitions/<anahtar>/` altında):**
  - `goals_models_v1.joblib`: Bağımsız Poisson + Dixon-Coles 13x13 skor matrisi (`evaluate_goal_models` -> `train_goals`), API'de lojistik 1X2'ye hizalı.
  - `outcome_models_v1.joblib`: 74 özellikli Lojistik Regresyon + sıcaklık kalibrasyonu (npxG + npBC + ceza sahası giriş üstünlüğü + ilk 11 kadro derecesi ve devamlılığı).
  - Sayım Modelleri (`corner`, `throws`, `offside`, `cards`, `saves`): CV kapısı + dış sezon kapısını (`apply_outer_season_gate`) geçemeyenler otomatik olarak `training_mean` döndürür.
  - La Liga (`models/production/la_liga/outcome_models_v1.joblib`): kendi özellik üreticisi (`src/features/build_league_features.py`) ve eğitici (`src/models/train_league_model.py`); kapıyı geçmezse Elo `baseline` sunulur. Sayım modelleri (`corner`, `throws`, `offside`, `cards`, `saves`) `src/models/train_league_counts.py` ile PL'nin aynı kapılarından geçirilir, hakem özellikleri LaLiga verisinden gelir. UCL/UEL için model yoktur, yalnızca veri gösterilir.
- **Referans Belgeler (Tek Kaynak Sırası):**
  1. `ARTIFACT_REGISTRY.md` — Veri, model ve rapor envanteri. Hangi turnuva verisi nereden geliyor: `docs/data_sources.md`.
  2. `PROJECT_STATUS.md` — Güncel sezon, model durumu ve bilinen sınırlar.
  3. `docs/reports/models/*.md` — Her modelin kendi mimari, denetim ve reddedilen deney raporu.
  4. `docs/reports/premier_league_models_comprehensive_report.md` — Ana rapor indeksi.
  5. `AI_CONTEXT.md` ve `VERI_VE_GOSTERIM_KATALOGU.md` — Makine okunabilir özet ve veri/API şema kataloğu.
  6. Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_tactical_data_audit.md`, `team_scenario_validation.md`) pipeline tarafından üretilir; elle düzenlenmez.

## Her Değişiklikten Sonra: Doküman ve Rapor Senkronu (ZORUNLU)
Kullanıcıdan istenmesini bekleme: bir şeyi eklediğinde, değiştirdiğinde ya da sildiğinde, işi bitirmeden ve "tamam" demeden önce aşağıdaki tabloya göre ilgili belgeleri aynı oturumda güncelle. Güncellenmemiş doküman eksik iştir.

| Ne değişti | Güncellenecek belgeler |
|---|---|
| Veri kaynağı, sağlayıcı, ingest/load script'i, yeni turnuva veya lig | `docs/data_sources.md` (kaynak tablosu, turnuva bölümü, karar günlüğü, script kataloğu), `docs/scripts_reference.md`, `ARTIFACT_REGISTRY.md`, `src/ingest/__main__.py` içindeki `TOOLS` dizini, script'in `--help` metni, `PROJECT_STATUS.md` |
| Dizin, dosya yolu, veritabanı adı, ortam değişkeni | `docs/scripts_reference.md` §0, `ARTIFACT_REGISTRY.md` (Directory layout), `README.md`, `AGENTS.md`, `AI_CONTEXT.md`, `.gitignore` ve `.claudeignore` |
| Model eğitimi, özellik, eşik, ablasyon, reddedilen deney | `docs/reports/models/<model>.md` (olumsuz sonuç dahil, "No Gain, Not Adopted"), `ARTIFACT_REGISTRY.md`, `PROJECT_STATUS.md`, `AI_CONTEXT.md`, `README.md` benchmark tablosu; üretilen raporlar için ilgili komutu çalıştır |
| API uç noktası, yanıt şeması, önbellek davranışı | `VERI_VE_GOSTERIM_KATALOGU.md`, `docs/model_api_integration.md`, `AI_CONTEXT.md` (endpoint eşlemesi) |
| Arayüz sekmesi, bileşen, turnuva yeteneği (`CompetitionContext`) | `VERI_VE_GOSTERIM_KATALOGU.md` (arayüz gösterimleri), `PROJECT_STATUS.md`; frontend için `npm run lint && npm run build` |
| Yeni veya silinen script, test dosyası | `docs/scripts_reference.md` (`tests/test_docs.py` bunu zorlar) |
| Veri atlama, model reddi, kapsam kararı | `docs/data_sources.md` karar günlüğü ve ilgili model raporu |
| Her oturumun sonu | `PROJECT_STATUS.md`: "Son Değişiklikler" (tarihli), test sayısı, "Bilinen Sınırlar", "Sıradaki İşler" |

Kurallar: (1) Sayıları elle uydurma, üretilen JSON/çıktıdan oku; elle yazılan sayının yanına tarih koy. (2) Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_*.md`) elle düzenlenmez; üreten komutu çalıştır. (3) Eski yol, ad veya sayı kalmadığını `grep` ile doğrula. (4) Bitirmeden `pytest` çalıştır; `tests/test_docs.py` ve `tests/test_cli_help.py` doküman eksiklerini yakalar. (5) Neyi güncellediğini son mesajda tek satırla say.

## Kod ve Bağlam Verimliliği
- **Belge Dili:** Türkçe belgeler (`PROJECT_STATUS.md`, `docs/`) Türkçe kalır; kod, docstring ve `--help` metinleri İngilizce yazılır.
- **Sıfır Emoji:** Kod, yorum satırı, docstring, commit mesajı, UI ve raporlarda kesinlikle emoji kullanma.
- **Nokta Atışı Okuma ve Düzenleme:** Büyük dosyaları tamamen okumak yerine `grep` ve satır aralıklı okuma kullan; veri dosyalarında yalnızca şema veya ilk birkaç satırı incele.
