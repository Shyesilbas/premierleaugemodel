# Premier League Match Analysis & Predictive Modeling System

Premier League maçları için uçtan uca bir tahmin platformu: ham maç verisinden maç öncesi özellikler (`shift(1)`, sızıntısız), bir gol skor matrisi modeli, bir 1X2 maç sonucu modeli, beş sayım modeli (korner, kart, kurtarış, ofsayt, taç), FastAPI backend ve React/Vite arayüzü.

**Durum (17 Ekim 2026):** 5 sezon, 1.900 fikstür (1.580 oynanmış; 2026/27'de 60/380). Güncel durum ve bilinen sınırlar: [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## 🚀 Hızlı Başlangıç

```bash
python3 start.py                 # Backend (:8000) + frontend (:5173) birlikte; bu portlardaki süreçleri kapatır
python3 run_full_pipeline.py     # ETL → özellikler → değerlendirme → tüm modellerin eğitimi → otomatik raporlar
pytest                           # Test paketi (22 test)
```

Ayrı ayrı çalıştırmak için:

```bash
uvicorn src.api.server:app --reload --host 127.0.0.1 --port 8000   # API, dokümantasyon: http://127.0.0.1:8000/docs
cd frontend && npm ci && npm run dev                                # Arayüz (Vite 8: Node ^20.19.0 veya >=22.12.0)
sqlite3 data/premier_league.db "SELECT ..."                        # Canlı veri sorgusu
```

- Pipeline yerel ham önbellekten çalışır; upstream veri indirmez ve SQLite'ı yeniden kurmaz. Yeni maç verisi arayüzdeki Fikstürler sayfasından artımlı senkronizasyonla gelir.
- Pipeline'dan sonra API'yi yeniden başlatın; modeller açılışta yüklenir.

---

## ⚽ Modeller

| Model | Üretimdeki Hali | Durum | Rapor |
| :--- | :--- | :--- | :--- |
| **Gol (skor matrisi)** | 13×13 matris: bağımsız Poisson × Dixon-Coles τ, $\lambda = \lambda_{Feat}$ ($w_{dc}=0$), `full` 58 özellik, α=3; API'de 1X2'ye hizalanır | ⚠️ Skor dağılımı iyileşti (NLL 2.9786), 2.5 Üst'te prior'a karşı sınırda anlamlı (LL 0.6774, Δ −0.0074), lig ortalamasına karşı ve piyasaya karşı anlamlı beceri yok; KG etiketi kapalı | [goals_model.md](docs/reports/models/goals_model.md) |
| **1X2 maç sonucu** | 77 özellikli L2 çok terimli lojistik + sıcaklık kalibrasyonu | 🏆 Prior'u anlamlı geçiyor (LL 1.026 vs 1.092); beraberlik ayrımı zayıf | [outcome_1x2_model.md](docs/reports/models/outcome_1x2_model.md) |
| **Korner** | `elastic_0.05_0.8`, 10 özellik | 🏆 Küçük kazanç (RMSE 3.200 vs 3.241) | [corners_model.md](docs/reports/models/corners_model.md) |
| **Taç** | `poisson_10`, 14 özellik | 🏆 Dış sezon 3/3 (RMSE 7.022 vs 7.388) | [throws_model.md](docs/reports/models/throws_model.md) |
| **Ofsayt** | `ridge_250`, 10 özellik | 🏆 Dış sezon 3/3 (RMSE 1.910 vs 2.024) | [offsides_model.md](docs/reports/models/offsides_model.md) |
| **Kart** | Sabit ortalama (`training_mean`) | 🛡️ Özellikli aday dış sezon kapısını geçemedi (1/3) | [cards_model.md](docs/reports/models/cards_model.md) |
| **Kurtarış** | Sabit ortalama (`training_mean`) | 🛡️ CV kapısı geçilemedi (2/4 kat) | [saves_model.md](docs/reports/models/saves_model.md) |

Sayım modellerinde özellikli model ancak hem CV kapısını hem de iç içe dış sezon kapısını geçerse üretime girer. Geçemezse sabit ortalama kullanılır ve API `model_skill: "baseline"` döner; arayüz bunu "Veri ortalaması tabanlı tahmin" rozetiyle gösterir.

---

## 🗺️ Dokümantasyon Haritası

```
README.md                      ← buradasınız: genel bakış ve hızlı başlangıç
PROJECT_STATUS.md              ← güncel durum, bilinen sınırlar, sıradaki işler
CLAUDE.md / AI_CONTEXT.md      ← ajanlar için talimatlar ve makine-okunur referans
ARTIFACT_REGISTRY.md           ← veri ve model artefaktları: ne, nerede, kim üretiyor
VERI_VE_GOSTERIM_KATALOGU.md   ← veri şeması, metrikler, arayüz gösterimleri
docs/
├── model_api_integration.md   ← model çıktıları → API alanları → React bileşenleri
└── reports/
    ├── README.md              ← rapor merkezi (tüm raporların dizini)
    ├── premier_league_models_comprehensive_report.md  ← ana rapor: özet karne, veri/ETL, edge, anayasa
    ├── models/                ← her modelin kendi raporu (yukarıdaki tablo)
    ├── model_benchmarks.md, data_quality.md, team_*.md   ← pipeline'ın otomatik ürettiği raporlar
    └── 1x2_model_audit.md, paper_trading_protocol_2026_27.md, repository_audit.md, ...  ← elle tutulan raporlar
```

| Ne arıyorsunuz? | Nereye bakın |
| :--- | :--- |
| Bir modelin nasıl çalıştığı, sonuçları, reddedilen deneyler | [docs/reports/models/](docs/reports/models/) |
| Tüm modellerin tek tablo özeti, metodolojik anayasa | [Ana Rapor](docs/reports/premier_league_models_comprehensive_report.md) |
| Güncel benchmark rakamları (pipeline üretir) | [Model Benchmarks](docs/reports/model_benchmarks.md) |
| Veri kapsamı ve kalitesi | [Data Quality](docs/reports/data_quality.md) · [Veri Kataloğu](VERI_VE_GOSTERIM_KATALOGU.md) |
| API alanlarının nereden geldiği | [Model API Entegrasyonu](docs/model_api_integration.md) |
| Canlı sezon takibi ve bahis edge'i | [Paper Trading Protokolü](docs/reports/paper_trading_protocol_2026_27.md) |
| Uçtan uca örnek maç | [Liverpool – Manchester City](LIVERPOOL_MANCHESTER_CITY_MAC_VE_VERI_DETAYI.md) |
| Tüm raporların listesi | [Rapor Merkezi](docs/reports/README.md) |

**Güncelleme kuralı:** Bir model değişince önce kendi raporu, sonra ana rapordaki özet karne, README'deki model tablosu, PROJECT_STATUS ve AI_CONTEXT güncellenir. Otomatik raporları (`model_benchmarks.md`, `data_quality.md`, `team_*.md`) elle düzenlemeyin; pipeline üzerine yazar.

---

## 📈 İleriye Dönük Ölçüm (Paper Trading)

```bash
python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14   # Gelecek maçların tahminlerini dondur
python3 -m src.analytics.prospective_1x2_benchmark score                       # Biten maçları puanla
```

Tahminler `data/processed/1x2_forecast_log.jsonl` dosyasına (yalnızca ekleme) yazılır, puan kartı `docs/reports/prospective_1x2_scorecard.json`'dır. Kurallar: [Paper Trading Protokolü](docs/reports/paper_trading_protocol_2026_27.md).

---

## 🧪 Değerlendirme İlkeleri

Tam liste: [Metodolojik Anayasa (Ana Rapor, Bölüm 8)](docs/reports/premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage).

1. **Sızıntı yok:** Tüm maç öncesi rolling metrikler `shift(1)` ile hesaplanır; aynı başlama saatindeki maçlar bölünmez.
2. **Kilitli sezon:** 2026/27 model seçiminde kullanılmaz, yalnızca raporlanır.
3. **İç içe değerlendirme:** Hiperparametreler ve dağıtım kararları yalnızca eğitim sezonları içindeki ileri katlarla verilir; test havuzunda optimizasyon yapılmaz.
4. **Sadelik:** Daha karmaşık bir seçenek, basit olanı kronolojik dış testte geçmedikçe reddedilir; reddedilenler ilgili model raporuna yazılır.
5. **Küçük örneklem:** N < 500 alt gruplarda bootstrap güven aralığı ve çoklu test düzeltmesi (Bonferroni / BH-FDR) zorunludur.
