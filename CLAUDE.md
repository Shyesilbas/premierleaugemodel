# CLAUDE.md — Premier League Model App

Premier League maçları için makine öğrenmesi tahmin motoru, analitik ETL hattı, FastAPI backend ve React/Tailwind arayüzü.

## ⚡ Hızlı Komutlar
- **Uygulamayı Başlat (Backend + Frontend):** `python3 start.py`
- **Tüm Pipeline'ı Çalıştır (ETL + Model Eğitimi + Benchmark):** `python3 run_full_pipeline.py`
- **Testleri Çalıştır:** `pytest`
- **Frontend Geliştirme:** `cd frontend && npm run dev`
- **Veritabanı Sorgulama:** `sqlite3 data/premier_league.db "SELECT ..."`

## 🛡️ Temel Kurallar & Mimari İlkeler
- **Veri Sızıntısı Yasağı:** Tüm maç öncesi yuvarlanan metriklerde mutlak suretle `shift(1)` uygulanmalıdır; gelecek bilgisi kullanılamaz.
- **Model Ailesi:** Skor matrisi için bağımsız Poisson + Dixon-Coles, 11 özellik, API'de 1X2'ye hizalı (`goals_models_v1.joblib`; seçim `train_goals.BLEND_GRID`, önce `evaluate_goal_models` sonra `train_goals`), 1X2 için 77 özellikli Lojistik Regresyon (`outcome_models_v1.joblib`), 5 sayım modeli (NB2/Poisson olasılıkları). Sayım modeli ancak CV kapısı + iç içe dış sezon kapısını geçerse üretime girer, yoksa `training_mean` (`src/models/model_utils.py`).
- **Kilitli Sezon:** 2026/27 hiçbir seçim/dağıtım kararında kullanılmaz; son %20 holdout onu içerdiği için yalnızca raporlanır.
- **Veritabanı Erişimi:** `.db` dosyası binary olduğu için metin olarak okunmaz (`.claudeignore`); şema için kataloglara bakın, canlı veri için SQL çalıştırın.

## 🗺️ Dokümantasyon & Yol Haritası (İhtiyaç Halinde Oku)
Tüm raporlar `docs/reports/` altındadır (kök dizinde `reports/` klasörü yok; kod oraya yazmaz). Haritası: `README.md` → "Dokümantasyon Haritası". Güncel durum: `PROJECT_STATUS.md`.
- **Ana Rapor (indeks):** `docs/reports/premier_league_models_comprehensive_report.md` (özet karne, veri/ETL, edge denetimi, denetim anayasası, API).
- **Model Raporları (her modelin kendi raporu):** `docs/reports/models/` — `goals_model.md`, `outcome_1x2_model.md`, `corners_model.md`, `cards_model.md`, `saves_model.md`, `offsides_model.md`, `throws_model.md`. Bir model değişince sırayla güncelle: kendi raporu → ana rapordaki özet karne → `README.md` model tablosu → `PROJECT_STATUS.md` → `AI_CONTEXT.md`. Sayıları belgelerden değil artifact'tan (`joblib.load(...)["metrics"]`) al.
- **Otomatik Raporlar (elle düzenlenmez):** `model_benchmarks.md`, `data_quality.md`, `team_tactical_data_audit.md`, `team_scenario_validation.md` — pipeline üzerine yazar.
- **Veri Şeması, Metrikler & API Entegrasyonu:** `VERI_VE_GOSTERIM_KATALOGU.md`, `AI_CONTEXT.md` ve `docs/model_api_integration.md`.
- **Canlı Takip & Forward Testing:** `docs/reports/paper_trading_protocol_2026_27.md` ve `docs/reports/model_benchmarks.md`.
