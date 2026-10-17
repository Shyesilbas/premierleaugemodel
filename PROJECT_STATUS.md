# Project Status

**Snapshot:** 17 Ekim 2026  
**Belgeler:** [README](README.md) · [Rapor Merkezi](docs/reports/README.md) · [Ana Rapor](docs/reports/premier_league_models_comprehensive_report.md) · [Model Raporları](docs/reports/models/) · [Model Benchmarks](docs/reports/model_benchmarks.md)

---

## 1. Veri

| Kalem | Değer |
| :--- | :--- |
| Fikstür | 1.900 (5 sezon: 2022/23–2026/27) |
| Oynanmış maç | 1.580 · 2026/27: 60/380 (kilitli sezon, yalnızca raporlanır) |
| Sağlayıcı xG kapsamı (iki takım) | 2022/23 366/380 · 2023/24 378/380 · 2024/25 380/380 · 2025/26 380/380 · 2026/27 60/60 oynanmış |
| Özellik tablosu | `data/processed/features_matches_all.parquet` (16 Ekim 2026) |
| İleriye dönük tahmin kaydı | `data/processed/1x2_forecast_log.jsonl`: 140 kayıt (son yazım 17 Ekim 2026: 7. ve 8. hafta, eski ve yeni 1X2 artifact'ıyla) |

- Eksik `won_corners` değerleri olay akışından kurtarılır (67 takım değeri). Kurtarış hedefi de olay akışıyla 1.580 maçın tamamında kullanılabilir. Ham değerler ve kurtarma bayrakları ayrı tutulur.
- Gerçekleşmiş maç xG'si yalnızca gösterim ve maç sonrası analiz içindir; maç öncesi modellerde kullanılmaz, çünkü başlama saatinden sonra bilinir.
- Ayrıntı: [Data Quality](docs/reports/data_quality.md).

## 2. Modeller

| Model | Üretimde | Değerlendirme | Rapor |
| :--- | :--- | :--- | :--- |
| Gol skor matrisi (`v1.3`) | Bağımsız Poisson × Dixon-Coles, 11 özellik, α=30, w_dc=0.5; API'de 1X2'ye hizalı | O2.5 LL 0.6803 vs prior 0.6847, CI [−0.0105, +0.0014]: **anlamlı değil** | [goals_model.md](docs/reports/models/goals_model.md) |
| 1X2 | 77 özellikli lojistik (C=0.003) + sıcaklık kalibrasyonu | LL 1.026 vs 1.092, Brier 0.617 vs 0.661; beraberlik AUC 0.557 | [outcome_1x2_model.md](docs/reports/models/outcome_1x2_model.md) |
| Korner | `elastic_0.05_0.8` | RMSE 3.200 vs 3.241; dış sezon 2/3 | [corners_model.md](docs/reports/models/corners_model.md) |
| Taç | `poisson_10` | RMSE 7.022 vs 7.388; dış sezon 3/3 | [throws_model.md](docs/reports/models/throws_model.md) |
| Ofsayt | `ridge_250` | RMSE 1.910 vs 2.024; dış sezon 3/3 | [offsides_model.md](docs/reports/models/offsides_model.md) |
| Kart | `training_mean` | Özellikli aday dış sezon 1/3 → ortalama | [cards_model.md](docs/reports/models/cards_model.md) |
| Kurtarış | `training_mean` | CV kapısı 2/4 kat → ortalama | [saves_model.md](docs/reports/models/saves_model.md) |

Artifact tarihleri: tüm modeller 17 Ekim 2026, aynı özellik tablosuyla (16 Ekim 23:24) eğitildi. Veri 6. haftanın sonuna kadar (1.580 maç); bir sonraki tam pipeline 7. hafta bittikten sonra (19 Ekim).

## 3. Son Değişiklikler (17 Ekim 2026)

- **Gol modeli denetimi ve `v1.3`:** Hiperparametreler artık iç içe ileri katlarla ve 1-SE kuralıyla seçiliyor; özellik sayısı 58'den 11'e indi; skor matrisi API'de lojistik 1X2'ye hizalanıyor; KG etiketi %50 eşiğine bağlandı. Ayrıntı: [goals_model.md §11](docs/reports/models/goals_model.md#bölüm-11-bağımsız-denetim-17-ekim-2026--gol-modeli--api-bulguları).
- **Sayım modelleri için dış sezon kapısı** (`apply_outer_season_gate`, `src/models/model_utils.py`): Özellikli model ancak tam dış sezonların çoğunluğunda ortalamayı yenerse üretime girer. Sonuç: kart modeli ortalamaya düştü (holdout'ta ortalamadan kötüydü), diğerleri değişmedi.
- **Belge yapısı:** Her modelin kendi raporu var (`docs/reports/models/`); ana rapor bir indeks. Tüm raporlar tek konumda: `docs/reports/`. Kod artık eski `reports/` klasörüne yazmıyor.
- **1X2 yeniden eğitildi:** Eski artifact güncel özellik tablosundan önce eğitilmişti. Holdout manşet değerleri aynı (LL 1.026, Brier 0.617, isabet %49.67, beraberlik AUC 0.557); sıcaklık 0.9587 → 0.9591, beraberlik ECE %4.6 → %5.3. Yedek: `models/production/outcome_models_v1.backup_2026-10-16.joblib`.
- **Testler:** 22/22 geçiyor (`tests/`).

## 4. Bilinen Sınırlar

- **Gol modeli** takım güç farkını yakalıyor (gol farkı korelasyonu 0.44) ama toplam gol hacmini neredeyse hiç ayırt edemiyor (0.065). Prior'a karşı farkı anlamlı değil; bahis edge'i iddiası için temel oluşturmaz.
- **1X2 modeli** genel beraberlik oranını biliyor ama beraberliği maç maç ayıramıyor (beraberlik olasılığı, beraberlikle biten maçlarda %25.7, diğerlerinde %24.8).
- **Sayım modellerinin** ortalamaya karşı kazancı küçük. Kart ve kurtarış ortalamada. Kilitli sezonun ilk 60 maçında ofsayt ve taç ortalamadan hafif kötü; örneklem küçük, izleniyor.
- **API'de model olmayan alanlar:** `shots.expected_total` sabit çarpandır (`kurtarış × 4.1`). Ev/deplasman paylaşımları rolling oranlardan gelir. Bkz. [API Entegrasyonu §2.6](docs/model_api_integration.md).
- **`/api/benchmarks`** kart metriklerini döndürmüyor (yalnızca korner, taç, kurtarış, 1X2, ofsayt).
- **Ortam:** Python bağımlılıkları için `requirements.txt` / `pyproject.toml` yok. `pytest` sistem Python'ında kurulu değil; testler bu turda doğrudan çalıştırıldı.
- **İleriye dönük kayıt** 7. ve 8. hafta için alındı (17 Ekim). Puan kartı (`docs/reports/prospective_1x2_scorecard.json`) henüz üretilmedi; 7. hafta bitince `score` komutuyla üretilecek.

## 5. Sıradaki İşler

1. Her oyun haftasından sonra `python3 run_full_pipeline.py` çalıştır, ardından API'yi yeniden başlat. Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_*.md`) bu sırada yenilenir.
2. Maç öncesi tahmin kaydını sürdür (`prospective_1x2_benchmark snapshot`) ve biten maçları puanla. Kısmi sezona bakarak modeli tekrar tekrar ayarlama.
3. Korner, ofsayt ve taç modellerine kart modelindeki gibi derin denetim yap: özellik ablasyonu, kazancın "seviye uyumu" ile "maçlar arası ayrım" arasında ayrıştırılması.
4. 1X2 denetimini güncel artifact (77 özellik) üzerinde yenile; [1x2_model_audit.md](docs/reports/1x2_model_audit.md) 14 Ekim tarihli.
5. Python bağımlılıklarını bir `requirements.txt` dosyasına sabitle; `pytest`'i geliştirme bağımlılığı olarak ekle.
6. Kart hedefinde `total_yellow_cards_target_usable` bayrağının eğitimde filtrelenmesi gerekip gerekmediğini doğrula.
