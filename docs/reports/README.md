# Premier League Rapor & Analiz Merkezi

**Dokümantasyon Ağı:** [Ana Sayfa (README)](../../README.md) · [Ana Kapsamlı Rapor](premier_league_models_comprehensive_report.md) · [Paper Trading 2026/27](paper_trading_protocol_2026_27.md) · [AI Context](../../AI_CONTEXT.md) · [API Entegrasyonu](../model_api_integration.md) · [Veri Kataloğu](../../VERI_VE_GOSTERIM_KATALOGU.md)

Bu sayfa projedeki tüm araştırma, mimari, veri tabanı, model, benchmark ve operasyonel denetim raporlarının merkezi giriş noktasıdır.

---

## 1. Ana Rapor ve Model Raporları

Ana rapor sistemin indeksidir (özet karne, veri/ETL, edge denetimi, metodolojik anayasa, API). Her modelin mimarisi, sonuçları, denetim bulguları, reddedilen deneyleri ve değişiklik geçmişi **kendi raporundadır** (17 Ekim 2026'dan itibaren):

| Model Raporu | Üretim Durumu (17 Ekim 2026) |
| :--- | :--- |
| **[Gol Modeli](models/goals_model.md)** | Poisson + Dixon-Coles, 58 özellik (α=3, w_dc=0); skor dağılımı iyi, 2.5 Üst'te lig ortalamasına/piyasaya karşı anlamlı beceri yok |
| **[1X2 Maç Sonucu](models/outcome_1x2_model.md)** | 77 özellikli lojistik; ayrıntılı denetim: [1x2_model_audit.md](1x2_model_audit.md) |
| **[Korner](models/corners_model.md)** | `elastic_0.05_0.8`, küçük kazanç |
| **[Kart](models/cards_model.md)** | Sabit ortalama (dış sezon kapısı) |
| **[Kurtarış](models/saves_model.md)** | Sabit ortalama (CV kapısı) |
| **[Ofsayt](models/offsides_model.md)** | `ridge_250`, dış sezon 3/3 |
| **[Taç](models/throws_model.md)** | `poisson_10`, dış sezon 3/3 |

| Belge | Tür | Kapsam & Özet |
| :--- | :---: | :--- |
| **[Premier League Tahmin Motoru & Veri Mimarisi — Kapsamlı Model, Benchmark ve Yönetici Raporu](premier_league_models_comprehensive_report.md)** | **Ana Rapor (indeks)** | **Özet karne + ortak konular** (model ayrıntıları yukarıdaki raporlarda): 11 özellikli Poisson + Dixon-Coles Gol Modeli (O2.5 dürüst holdout `0.6803`, haftalık yeniden eğitimle `0.6756`; prior'a karşı anlamlı değil — §11), 44 özellikli 1X2 Lojistik Regresyon (`1.026` Log-Loss), 5 Sayım Modeli (Korner, Taç, Ofsayt, Kart, Kurtarış), SQLite şemaları (12 tablo, 1.900 fikstür), 1.140 holdout maçı, reddedilen deneyler ve quant anayasası. |
| **[2026/27 Sezonu Paper Trading Protokolü](paper_trading_protocol_2026_27.md)** | Canlı Takip | Sezonun kalan ~320 maçı için resmi forward-testing protokolü. 3 paralel edge portföyü (>%2, >%3, >%5), $N=100$ ara kontrol, $N=200$ karar eşiği, çoklu test FDR düzeltmesi ve durdurma kuralları. |
| **[AI Context & Machine Reference](../../AI_CONTEXT.md)** | Makine Bağlamı | Yapay zeka ajanları ve quant araştırmacılar için kanonik tek dosya: tüm modellerin hiperparametreleri, metrikleri, şemaları ve API eşlemeleri. |
| **[Model API & Sistem Entegrasyon Kılavuzu](../model_api_integration.md)** | Mühendislik | $13 \times 13$ skor matrisi ve diğer model çıktılarının FastAPI uç noktalarına (`/api/predict`) ve React frontend bileşenlerine (`MatchPredictionTab`, `PredictorMetricCards`) teknik eşlenmesi. |

---

## 2. Otomatik Benchmark & Veri Kalitesi Raporları

Bu raporlar `python3 run_full_pipeline.py` çalıştırıldığında yerel ham veriden otomatik olarak üretilir ve yenilenir:

| Rapor | Konu ve Kullanım |
| :--- | :--- |
| **[Model Benchmarks](model_benchmarks.md)** | Kronolojik holdout, sezon bazlı sonuçlar, sayım hedefleri regresyon kapıları ve 1X2 temel skorları. |
| **[Data Quality](data_quality.md)** | 5 sezonluk ham ve işlenmiş veri kalitesi, eksik hedefler, kurtarılan istatistikler ve sağlayıcı kapsaması. |
| **[Team Tactical Data Audit](team_tactical_data_audit.md)** | Taktik alanların (pres, PPDA, tempo, pas kanalları) sezon bazında ham veri kapsaması ve güvenilirlik denetimi. |
| `prospective_1x2_scorecard.json` | İleriye dönük tahmin puan kartı; `python3 -m src.analytics.prospective_1x2_benchmark score` ile üretilir (henüz üretilmedi). |
| **[Team Scenario Validation](team_scenario_validation.md)** | Olay akışından (event stream) çıkarılan şut/korner senaryolarının resmi maç istatistikleriyle karşılaştırmalı doğrulaması. |

---

## 3. Sistem Mimarisi, Kod Denetimi & Referanslar

| Belge | Konu ve Kullanım |
| :--- | :--- |
| **[Veri ve Gösterim Kataloğu](../../VERI_VE_GOSTERIM_KATALOGU.md)** | 58 taktiksel metrik, veri kaynakları, mühendislik formülleri, `shift(1)` prensibi ve arayüz görselleştirmeleri. |
| **[Repository Audit](repository_audit.md)** | Kod tabanı mimarisi, test kapsamı, teknik borç analizi ve geliştirme yol haritası. |
| **[Script Envanteri ve Denetimi](scripts_audit.md)** | Tüm scriptlerin rolü, çalışma akışı, bağımlılıkları, test örtüsü, riskler ve öncelikli öneriler (19 Ekim 2026). |
| **[Project Status](../../PROJECT_STATUS.md)** | Veri anlık görüntüsü, tamamlanan maçlar, bilinen model sınırları ve sıradaki mühendislik adımları. |
| **[Artifact Registry](../../ARTIFACT_REGISTRY.md)** | Veri setleri ve `models/production/*.joblib` artefaktları: amaç, üreten kod, yenileme yolu. |

---

## 4. Raporların Güncellenme Düzeni

```bash
# Tüm pipeline'ı yerel ham veriden çalıştırmak için:
python3 run_full_pipeline.py
```
- `run_full_pipeline.py` çalıştırıldığında işlenmiş tabloları ve modelleri yeniden üretir; `model_benchmarks.md`, `data_quality.md`, `team_tactical_data_audit.md` ve `team_scenario_validation.md` raporlarını otomatik yeniler.
- [Ana Kapsamlı Rapor](premier_league_models_comprehensive_report.md) ve [model raporları](models/) elle, kontrollü olarak güncellenir. Bir model değişince önce kendi raporu, sonra ana rapordaki özet karne güncellenir.
