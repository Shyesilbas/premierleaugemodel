# Premier League Match Analysis & Predictive Modeling System

Premier League maçları için uçtan uca maç analizi ve tahmin platformu: ham maç verisinden maç öncesi özellikler (`shift(1)`, veri sızıntısız), gol skor matrisi modeli, 1X2 maç sonucu sınıflandırma modeli, beş sayım modeli (korner, kart, kurtarış, ofsayt, taç), FastAPI backend servisi ve React/Vite kullanıcı arayüzü.

**Veri ve Model Kapsamı:** 5 sezon, 1.900 fikstür (1.595 oynanmış maç; 2026/27 kilitli canlı sezon). Ayrıntılı durum için: [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## Kurulum ve Calistirma Rehberi

Bu depoyu yeni klonlayan bir gelistiricinin projeyi yerel ortaminda calisir duruma getirmesi icin asagidaki adimlari izlemesi gerekmektedir.

### Gereksinimler

- **Python:** 3.12 (veya 3.11+)
- **Node.js:** Node ^20.19.0 veya >=22.12.0 (Vite 8 destegi icin)
- **Paket Yoneticisi:** `npm` (veya `pnpm` / `yarn`)
- **Isletim Sistemi:** Linux, macOS veya WSL (Windows Subsystem for Linux)

---

### Adim 1: Depoyu Klonlayin

```bash
git clone https://github.com/Serhathy/premierLeaugeModelApp.git
cd premierLeaugeModelApp
```

---

### Adim 2: Python Sanal Ortamini Olusturun ve Bagimliliklari Yukleyin

```bash
# Sanal ortam olusturma
python3 -m venv .venv

# Sanal ortami etkinlestirme
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# Temel calisma zamani bagimliliklarini yukleme
pip install -r requirements.txt

# Gelistirme, test ve linter bagimliliklarini yukleme (onerilen)
pip install -r requirements-dev.txt
```

---

### Adim 3: Frontend Bagimliliklarini Yukleyin

```bash
cd frontend
npm install
cd ..
```

---

### Adim 4: Uygulamayi Baslatin

Uygulamayi hem FastAPI backend hem de Vite frontend servisleriyle birlikte tek komutla calistirabilirsiniz:

```bash
python3 start.py
# veya
./start.sh
```

Bu baslatici:
- Gerekli portlari (FastAPI icin `8000`, Vite icin `5173`) kontrol eder ve eski surecleri temizler.
- `frontend/node_modules` eksikse otomatik olarak yukler.
- Her iki servisi paralel baslatir ve `Ctrl+C` ile her ikisini de duzenli sekilde kapatir.

Baslatma sonrasi erisim noktalari:
- **Web Arayuzu (Dashboard):** [http://localhost:5173](http://localhost:5173)
- **Model API (FastAPI):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Swagger API Dokumantasyonu:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Alternatif: Servisleri Ayri Ayri Calistirma

Gelistirme sirasinda servisleri ayri terminallerde calistirmak isterseniz:

```bash
# Terminal 1 - Backend API:
uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend Dashboard:
cd frontend && npm run dev
```

---

### Adim 5: Testleri ve Kod Kalitesini Dogrulayin

Kod tabaninin dogrulugunu teyit etmek icin test paketini ve statik analiz araclarini calistirin:

```bash
# Python test paketini calistirma (90+ birim ve entegrasyon testi)
pytest

# Python linter kontrolu (Ruff)
ruff check .

# Frontend tip ve lint kontrolu
cd frontend && npm run lint

# Frontend production derleme kontrolu
npm run build
```

---

### Adim 6: (Opsiyonel) Veri ve Model Pipeline'ini Calistirin

Depo icerisinde egitilmis uretim modelleri (`models/production/premier_league/*.joblib`) ve islenmis yerel veritabani (`data/football.db`) hazir olarak bulunmaktadir. Uygulamayi calistirmak icin pipeline'i tekrar kosturmaniz **gerekmez**.

Eger ham veriden ozellik cikarimini, model egitimlerini ve otomatik benchmark raporlarini sifirdan yeniden uretmek isterseniz:

```bash
python3 run_full_pipeline.py
```

- Pipeline yerel ham onbellekten calisir; dis agdan veri cekmez ve SQLite semasini bozmaz.
- Pipeline calistirildiktan sonra yeni modellerin bellege yuklenmesi icin API servisini yeniden baslatin.

---

## Modeller

| Model | Uretimdeki Mimarisi | Performans & Durum | Rapor |
| :--- | :--- | :--- | :--- |
| **Gol (Skor Matrisi)** | 13x13 matris: bagimsiz Poisson x Dixon-Coles tau, lambda = lambda_Feat (w_dc=0), full 60 ozellik (`exp_match_xg_10` ve `exp_venue_match_xg` dahil), alpha=3; egitim/degerlendirme/API'de 1X2 (`v1.3`) marjinaline hizalanir | [Uretimde] Skor dagilimi iyilesti (NLL 2.9686), 2.5 Ust'te prior'i 3/3 sezonda ve anlamli geciyor (LL 0.6767, haftalik refit 0.6753, Delta -0.0080); KG LL 0.6804 (etiket kilitli) | [goals_model.md](docs/reports/models/goals_model.md) |
| **1X2 Mac Sonucu** | 71 ozellikli L2 duzenlilestirilmis cok terimli lojistik regresyon + ayristirilmis L2 cezali sicaklik/bias kalibrasyonu (`reg_temp=0.10, reg_bias=0.50`; npxG + npBC + ceza sahasi giris farklari) | [Uretimde] 3 dis sezonda (`N=1,140`) anlamli iyilesme (LL 0.9746 vs v1.2 0.9757, v1.1 0.9789, Brier 0.5798, RPS 0.1980, Isabet %55.09); 304 holdout LL 1.026 (`1.0256`) vs 1.092 | [outcome_1x2_model.md](docs/reports/models/outcome_1x2_model.md) |
| **Korner** | Sabit ortalama (`training_mean`) | [Baseline] Gelistirme donemi dis sezon kapisinda (1/2) elendigi icin durust ortalama korundu (holdout RMSE 3.235) | [corners_model.md](docs/reports/models/corners_model.md) |
| **Tac** | PoissonRegressor (alpha=10.0), 14 ozellik | [Uretimde] Gelistirme dis sezon 2/2 basarim (RMSE 6.941 vs 7.337) | [throws_model.md](docs/reports/models/throws_model.md) |
| **Ofsayt** | Ridge (alpha=250.0), 10 ozellik | [Uretimde] Gelistirme dis sezon 2/2 basarim (RMSE 1.906 vs 2.013) | [offsides_model.md](docs/reports/models/offsides_model.md) |
| **Kart** | Sabit ortalama (`training_mean`) | [Baseline] Ozellikli aday dis sezon kapisini gecemedigi (1/2) icin durust ortalama korundu | [cards_model.md](docs/reports/models/cards_model.md) |
| **Kurtaris** | Sabit ortalama (`training_mean`) | [Baseline] Capraz dogrulama kapisi gecilemedigi icin durust ortalama korundu | [saves_model.md](docs/reports/models/saves_model.md) |
| **La Liga 1X2** | 118 ozellikli lojistik (C=0.001) + Elo referansi; kapi: taban orani anlamli gecmeli ve log-loss Elo'dan kotu olmamali; yoksa Elo `baseline` olarak sunulur | [Uretimde] 760 dis sezon macinda taban orani anlamli geciyor (-0.086), Elo'dan ayirt edilemiyor (-0.008, N_req ~6,619), piyasadan kotu (+0.019); gol pazarlari (alt/ust 1.5, 2.5, 3.5, KG) yonu modelin lehine ama FDR sonrasi anlamli degil (2.5 ust q=0.081), bu yuzden `baseline` (taban orani) sunulur | [la_liga_outcome.md](docs/reports/models/la_liga_outcome.md) |
| **La Liga sayim modelleri** | Korner, tac, ofsayt, kart, kurtaris: PL ile ayni CV ve dis sezon kapilari, LaLiga'ya ozgu ozellik listeleri | [Uretimde] PL ozellik koduyla egitildi. Tac (holdout RMSE 7.34, ortalama 9.15) ve ofsayt (2.14, ortalama 2.26; kirilgan karar) kapiyi gecti; korner, kart, kurtaris `training_mean` (`baseline`) | [la_liga_counts.md](docs/reports/models/la_liga_counts.md) |

Sayim modellerinde ozellikli bir model ancak hem CV kapisini hem de kronolojik dis sezon test kapisini gecerse uretim modeline alinir. Gecemezse sabit ortalama kullanilir ve API `model_skill: "baseline"` degeri doner.

---

## Ileriye Donuk Olcum (Paper Trading)

Canli 2026/27 sezonunda model tahminlerinin piyasaya karsi performansini ileriye donuk (out-of-sample forward test) olcmek icin:

```bash
# Gelecek 14 gunun mac tahminlerini dondurarak log dosyasina ekle:
python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14

# Oynanmis ve sonuclanmis maclari puanla:
python3 -m src.analytics.prospective_1x2_benchmark score
# LaLiga icin ayni komutlara --competition la_liga eklenir
```

Tahminler `data/competitions/premier_league/processed/1x2_forecast_log.jsonl` dosyasina yalnizca ekleme (append-only) yontemiyle yazilir; puan karti `docs/reports/prospective_1x2_scorecard.json` uzerinden takip edilir. Protokol kurallari: [Paper Trading Protokolu](docs/reports/paper_trading_protocol_2026_27.md).

---

## Degerlendirme Ilkeleri (Sifir Sizinti / Zero Leakage)

Metodolojik kurallarin tamami: [Metodolojik Anayasa (Ana Rapor, Bolum 8)](docs/reports/premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage).

1. **Sifir Veri Sizintisi (Zero Leakage):** Tum mac oncesi metrikler `shift(1)` ile gecmis maclardan hesaplanir; ayni baslama saatindeki maclar birbirinden bagimsiz tutulur.
2. **Kilitli Sezon:** 2026/27 sezonu model egitiminde veya hiperparametre seciminde kullanilmaz, yalnizca ileriye donuk raporlanir.
3. **Ic Ice Gecmis Degerlendirme (Nested CV):** Model kararlari yalnizca egitim sezonlarindaki expanding-window katlariyla verilir; test setine sizma yapilmaz.
4. **Sadelik Kapisi:** Karmasik model, basit referans modelini kronolojik dis testte anlamli derecede gecmedikce reddedilir; uretimde gereksiz karmasiklik barindirilmaz.
5. **Istatistiki Belirsizlik:** Alt grup analizlerinde bootstrap guven araliklari (%95 CI) ve coklu hipotez duzeltmesi (BH-FDR) uygulanir.

---

## Dokumantasyon Haritasi

```
README.md                      <- Genel bakis ve kurulum rehberi
PROJECT_STATUS.md              <- Guncel proje durumu, bilinen sinirlar, yol haritasi
CLAUDE.md / AI_CONTEXT.md      <- Ajanlar icin talimatlar ve makine-okunur parametre referansi
ARTIFACT_REGISTRY.md           <- Veri setleri ve model artefaktlari kayit defteri
VERI_VE_GOSTERIM_KATALOGU.md   <- Veri semasi, taktik metrikler ve arayuz gosterimleri
data/
├── football.db                <- Ortak SQLite; her mac satiri competition_id tasir (39 PL, 2 UCL, 3 UEL)
└── competitions/<anahtar>/    <- Turnuva basina raw/ (saglayici ciktilari) ve processed/ (parquet, ozellikler, degerlendirme JSON'lari)
models/production/<anahtar>/   <- Turnuva basina egitilmis modeller (yalnizca premier_league icin mevcut)
docs/
├── data_sources.md            <- Hangi turnuva icin hangi veri nereden geliyor (kaynak haritasi)
├── model_api_integration.md   <- Model ciktilari -> FastAPI uclari -> React bilesenleri
├── scripts_reference.md       <- Tum scriptlerin gorevleri ve kullanim referansi
└── reports/
    ├── README.md              <- Rapor dizini
    ├── premier_league_models_comprehensive_report.md  <- Kapsamli model & benchmark ana raporu
    ├── models/                <- Her model ailesinin ozel teknik raporu
    ├── model_benchmarks.md    <- Pipeline tarafindan uretilen benchmark skorlari
    ├── data_quality.md        <- Veri kalitesi ve eksik veri analiz raporu
    └── paper_trading_protocol_2026_27.md  <- 2026/27 sezonu canli test protokolü
```

| Konu | Baglanti |
| :--- | :--- |
| Model Mimarileri, Sonuclar ve Deneyler | [docs/reports/models/](docs/reports/models/) |
| Kapsamli Sistem Raporu & Anayasa | [Ana Rapor](docs/reports/premier_league_models_comprehensive_report.md) |
| Guncel Model Benchmark Sonuclari | [Model Benchmarks](docs/reports/model_benchmarks.md) |
| Veri Kalitesi ve Kapsam | [Data Quality](docs/reports/data_quality.md) |
| Veri Semasi ve Taktik Alanlar | [Veri Kataloğu](VERI_VE_GOSTERIM_KATALOGU.md) |
| API Alan Eslestirmeleri | [Model API Entegrasyonu](docs/model_api_integration.md) |
| Canli Sezon Takibi (Paper Trading) | [Paper Trading Protokolu](docs/reports/paper_trading_protocol_2026_27.md) |
| Script Referansi ve Envanteri | [Script Referansi](docs/scripts_reference.md) |
| Rapor Merkezi | [Rapor Merkezi](docs/reports/README.md) |
