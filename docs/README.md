# premierLeaugeModelApp Mimari Dokümantasyonu (`/docs`)

Bu dizin, modül README'lerinin ötesine geçen, birden fazla modülü kesen mimari dokümanları, artifact envanterini ve el ile bakımı yapılan model tasarım raporlarını içerir. Modül iş kuralları `src/<module>/README.md` ve `frontend/src/<module>/README.md` içindedir.

---

## Doküman Haritası

### Yönetişim, Durum ve Kaynaklar
| Doküman | Kapsam |
| :--- | :--- |
| **[artifact_registry.md](artifact_registry.md)** | Üretim model artifact'ları (`models/production/`), işlenmiş parquet veri setleri, SQLite tabloları ve PL eğitim çıktıları envanteri. |
| **[project_status.md](project_status.md)** | Güncel veri anlık görüntüsü, aktif üretim modelleri, son değişiklikler, bilinen sınırlar ve sıradaki mühendislik adımları. |
| **[data_sources.md](data_sources.md)** | Turnuva bazlı veri sağlayıcıları (PulseLive, TheStatsAPI, UEFA, openfootball, Transfermarkt, TheSportsDB), hız sınırları, karar günlüğü ve script kataloğu. |
| **[scripts_reference.md](scripts_reference.md)** | `src/`, `scripts/` ve `tests/` altındaki tüm modül ve script'lerin referansı (`tests/test_docs.py` tarafından denetlenir). |

### Veri, API ve Canlı Takip Rehberleri
| Doküman | Kapsam |
| :--- | :--- |
| **[model_api_integration.md](model_api_integration.md)** | $13 \times 13$ gol matrisi, 1X2 kalibrasyonu ve sayım modeli çıktılarının `GET /api/predict` ve React bileşenlerine eşlenmesi. |
| **[data_and_ui_catalog.md](data_and_ui_catalog.md)** | Maç, takım, oyuncu ve hakem verilerinin şemaları, mühendislik metrikleri (`shift(1)`) ve arayüz gösterim kataloğu. |
| **[paper_trading_protocol_2026_27.md](paper_trading_protocol_2026_27.md)** | Kilitli `2026_27` sezonu için ileriye dönük tahmin kilitleme, portföy kuralları ve FDR doğrulama protokolü. |

### Üretim Model Mimari Raporları
| Doküman | Kapsam |
| :--- | :--- |
| **[reports/premier_league_models_comprehensive_report.md](reports/premier_league_models_comprehensive_report.md)** | PL tahmin motorunun uçtan uca sistem mimarisi, veri akışı, edge denetimi ve metodolojik anayasası. |
| **[reports/models/goals_model.md](reports/models/goals_model.md)** | PL bağımsız Poisson + Dixon-Coles $13 \times 13$ gol matrisi (`v1.6`), 1X2 hizalaması, O/U & BTTS kapıları. |
| **[reports/models/outcome_1x2_model.md](reports/models/outcome_1x2_model.md)** | PL 74 özellikli çok terimli lojistik 1X2 modeli (`v1.4`), OOF sıcaklık kalibrasyonu ve bilinen sınırlar. |
| **[reports/models/corners_model.md](reports/models/corners_model.md)** | PL korner sayım modeli ve CV / dış sezon kapısı kararı (`training_mean` baseline). |
| **[reports/models/cards_model.md](reports/models/cards_model.md)** | PL kart sayım modeli, hakem istatistikleri ve dış sezon kapısı kararı (`training_mean` baseline). |
| **[reports/models/saves_model.md](reports/models/saves_model.md)** | PL kaleci kurtarış sayım modeli ve CV kapısı kararı (`training_mean` baseline). |
| **[reports/models/offsides_model.md](reports/models/offsides_model.md)** | PL ofsayt sayım modeli (`ridge_250`, dış sezon kapısını geçti). |
| **[reports/models/throws_model.md](reports/models/throws_model.md)** | PL taç sayım modeli (`poisson_10`, dış sezon kapısını geçti). |

---

## Üretilmiş Çıktılar ve Tarihsel Denetimler (`/reports`)

Kod tarafından otomatik üretilen benchmark/kalite JSON ve markdown dosyaları ile tarih damgalı denetimler [`reports/README.md`](../reports/README.md) altında yönetilir:
- **[model_benchmarks.md](../reports/model_benchmarks.md)** — `run_full_pipeline.py` tarafından üretilen PL walk-forward ve sayım modeli karnesi.
- **[data_quality.md](../reports/data_quality.md)** — 5 sezonluk ham ve işlenmiş veri kapsam raporu.
- **[audits/1x2_model_audit.md](../reports/audits/1x2_model_audit.md)** & **[audits/goal_models_analysis.md](../reports/audits/goal_models_analysis.md)** — Tarihsel denetim kayıtları.

## Temel Mimari Prensipler

1. **Sıfır Sızıntı (`shift(1)`) ve Train-Serve Parity:** Eğitim ve canlı tahminler aynı `src/features/` yardımcılarını ve kronolojik kesim sınırlarını kullanır.
2. **Kilitli Sezon (`2026_27`):** Yalnızca prospektif izleme ve `1x2_forecast_log.jsonl` kayıtları içindir; model/hiperparametre kararlarında kullanılmaz.
3. **Turnuva İzolasyonu:** `src.config.competition_paths(key)` her turnuvanın ham ve işlenmiş verisini ayrı tutar; ortak SQLite (`data/football.db`) `competition_id` ile bölünür.
