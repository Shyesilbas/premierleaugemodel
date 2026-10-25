# Project Rules — Premier League Model App

Premier League maçları için makine öğrenmesi tahmin motoru, analitik ETL hattı, FastAPI backend ve React/Tailwind arayüzü.

## Uzmanlaşmış Agent Skill'leri (`.agents/skills/`)
Detaylı iş akışları ve standartlar `.agents/skills/` altındadır; ilgili görevlerde mutlaka bu skill'leri oku ve uygula:
- **`quant-model-experiment-and-audit`** (`.agents/skills/quant-model-experiment-and-audit/SKILL.md`): Model deneyleri, özellik ablasyonları, sıfır sızıntı (`shift(1)` ve OOF kalibrasyon), kilitli sezon (`2026/27`), dış sezon skill gate (`training_mean` / prior karşılaştırması), bootstrap CI, ortak skor matrisi tutarlılığı ve rapor/registry güncelleme zinciri.
- **`sports-pipeline-and-paper-trading`** (`.agents/skills/sports-pipeline-and-paper-trading/SKILL.md`): Veri çekme/ETL, olay akışından istatistik kurtarma, SQLite veritabanı (`data/premier_league.db`), maç öncesi append-only tahmin kaydı (`1x2_forecast_log.jsonl`) ve puan kartı (`prospective_1x2_scorecard.json`) akışı.
- **`restrained-ui-design-standard`** (`.agents/skills/restrained-ui-design-standard/SKILL.md`): Apple/Spotify-tier sade arayüz tasarım kuralları, semantik tokenlar, radius tavanı (`rounded-md`), 4 veri durumu (loading/empty/error/pending) ve iş bitimi zorunlu lint/regex kontrolleri.

## Hızlı Komutlar
- **Uygulamayı Başlat (Backend + Frontend):** `python3 start.py`
- **Tüm Pipeline'ı Çalıştır (ETL + Model Eğitimi + Benchmark):** `python3 run_full_pipeline.py`
- **Maç Öncesi Tahmin Kaydı (Paper Trading):** `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14`
- **Testleri Çalıştır:** `pytest`
- **Frontend Geliştirme & Doğrulama:** `cd frontend && npm run lint && npm run build`
- **Veritabanı Sorgulama:** `sqlite3 data/premier_league.db "SELECT ... LIMIT 5;"` (`.db` ve `.parquet` dosyalarını asla metin olarak doğrudan okuma).

## Mimari Özeti & Dokümantasyon Haritası
- **Aktif Üretim Modelleri (`models/production/`):**
  - `goals_models_v1.joblib`: Bağımsız Poisson + Dixon-Coles 13x13 skor matrisi (`evaluate_goal_models` -> `train_goals`), API'de lojistik 1X2'ye hizalı.
  - `outcome_models_v1.joblib`: 74 özellikli Lojistik Regresyon + sıcaklık kalibrasyonu (npxG + npBC + ceza sahası giriş üstünlüğü + ilk 11 dakika ağırlığı/devamlılığı).
  - Sayım Modelleri (`corner`, `throws`, `offside`, `cards`, `saves`): CV kapısı + dış sezon kapısını (`apply_outer_season_gate`) geçemeyenler otomatik olarak `training_mean` döndürür.
- **Referans Belgeler (Tek Kaynak Sırası):**
  1. `ARTIFACT_REGISTRY.md` — Veri, model ve rapor envanteri.
  2. `PROJECT_STATUS.md` — Güncel sezon, model durumu ve bilinen sınırlar.
  3. `docs/reports/models/*.md` — Her modelin kendi mimari, denetim ve reddedilen deney raporu.
  4. `docs/reports/premier_league_models_comprehensive_report.md` — Ana rapor indeksi.
  5. `AI_CONTEXT.md` ve `VERI_VE_GOSTERIM_KATALOGU.md` — Makine okunabilir özet ve veri/API şema kataloğu.
  6. Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_tactical_data_audit.md`, `team_scenario_validation.md`) pipeline tarafından üretilir; elle düzenlenmez.

## Kod ve Bağlam Verimliliği
- **Sıfır Emoji:** Kod, yorum satırı, docstring, commit mesajı, UI ve raporlarda kesinlikle emoji kullanma.
- **Nokta Atışı Okuma ve Düzenleme:** Büyük dosyaları tamamen okumak yerine `grep` ve satır aralıklı okuma kullan; veri dosyalarında yalnızca şema veya ilk birkaç satırı incele.
