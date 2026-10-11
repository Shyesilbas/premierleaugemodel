# Premier League Model Engine (2024-25)

Premier League için maçın nihai skorundan ziyade süreci yöneten mikro metriklere (şut hacmi, korner, taç, kaleci kurtarışı, pas ve topa sahip olma) odaklanan, sızıntısız (leakage-free) zaman serisi öznitelikleriyle çalışan bilimsel bir makine öğrenimi tahmin motoru.

---

## 1. Mimari Genel Bakış

```text
premierLeaugeModelApp/
├── data/
│   ├── raw/
│   │   ├── fixtures_2024_25.json             # 380 maçın ham fikstürü
│   │   └── matches/                          # Her maç için:
│   │       ├── {match_id}_stats.json         # Takım istatistikleri (150+ metrik)
│   │       ├── {match_id}_stream.json        # Play-by-play akışı (şutlar, kartlar vb.)
│   │       └── {match_id}_details.json       # Kadrolar, dizilişler, stadyum, hakem
│   └── processed/
│       ├── matches_summary_2024_25.parquet   # Temizlenmiş 380 maçlık ana istatistik tablosu
│       └── shots_events_2024_25.parquet      # Şut ve olay bazlı oyuncu tablosu
├── models/
│   ├── production/                           # Kabul testini geçen aktif modeller
│   └── experimental/                         # Eğitilen aday modeller
├── src/
│   ├── ingest/
│   │   └── fetch_season_data.py              # PulseLive'dan batch veri çeken script
│   ├── features/
│   │   └── build_features.py                 # Rolling EWMA, rakip düzeltmesi, dinlenme günleri
│   └── models/
│       ├── train_corners.py                  # Korner tahmin modeli
│       ├── train_throws.py                   # Taç tahmin modeli
│       ├── train_saves.py                    # Kaleci kurtarış modeli
│       └── train_match_outcome.py            # 1X2 ve Alt/Üst Poisson/XGBoost modelleri
├── reports/
│   ├── data_audit_2024_25.md                 # Kayıp veri ve veri kalitesi raporu
│   └── model_benchmarks.md                   # Model doğrulama ve metrik sonuçları
├── PROJECT_STATUS.md                         # Aktif faz, tamamlananlar ve sonraki adımlar
├── ARTIFACT_REGISTRY.md                      # Veri ve model dosyalarının tek doğruluk kaynağı
└── README.md                                 # Proje kullanım ve mimari rehberi
```

---

## 2. Veri Kaynağı ve Protokolü

- **Sağlayıcı:** Premier League Resmi Altyapısı (PulseLive API)
- **CompSeason ID (2024/25):** `719`
- **Gerekli Başlıklar:**
  - `Origin: https://www.premierleague.com`
  - `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)`
- **Ana Endpoint'ler:**
  - Fikstür: `https://footballapi.pulselive.com/football/fixtures?comps=1&compSeasons=719&pageSize=400&sort=asc`
  - Takım İstatistikleri: `https://footballapi.pulselive.com/football/stats/match/{match_id}`
  - Play-by-Play Akış: `https://footballapi.pulselive.com/football/fixtures/{match_id}/textstream/en?pageSize=500`
  - Kadro ve Detaylar: `https://footballapi.pulselive.com/football/fixtures/{match_id}`

---

## 3. Kurulum ve Çalıştırma

### Gereksinimler
Python 3.10+ ve temel veri bilimi kütüphaneleri:
```bash
pip install requests pandas pyarrow numpy scipy xgboost lightgbm scikit-learn tqdm
```

### Veri Çekme (Faz 1)
```bash
python3 src/ingest/fetch_season_data.py --season 719 --season-name 2024_25
```
Seçenekler:
- `--limit N`: Test amaçlı ilk N maçı çeker.
- `--force`: Mevcut önbellek dosyalarını yeniden indirir.
- `--delay SECONDS`: İstekler arası bekleme süresi (varsayılan: 0.1 sn).
