# Project Status

**Snapshot:** 24 Ekim 2026  
**Belgeler:** [README](README.md) · [Rapor Merkezi](docs/reports/README.md) · [Ana Rapor](docs/reports/premier_league_models_comprehensive_report.md) · [Model Raporları](docs/reports/models/) · [Model Benchmarks](docs/reports/model_benchmarks.md)

---

## 1. Veri

| Kalem | Değer |
| :--- | :--- |
| Fikstür | 1.900 (5 sezon: 2022/23–2026/27) |
| Oynanmış maç | 1.595 · 2026/27: 75/380 (kilitli sezon, yalnızca raporlanır) |
| Sağlayıcı xG kapsamı (iki takım) | 2022/23 366/380 · 2023/24 378/380 · 2024/25 380/380 · 2025/26 380/380 · 2026/27 69/75 oynanmış |
| Özellik tablosu | `data/processed/features_matches_all.parquet` (24 Ekim 2026; eğitim-tahmin XI mevki uyumu doğrulandı) |
| İleriye dönük tahmin kaydı | `data/processed/1x2_forecast_log.jsonl`: 160 kayıt (15 oynanmış maç `docs/reports/prospective_1x2_scorecard.json` içinde puanlandı; son snapshot 24 Ekim 2026) |

- Eksik `won_corners` değerleri olay akışından kurtarılır (68 takım değeri). Kurtarış hedefi de olay akışıyla 1.595 maçın tamamında kullanılabilir. Ham değerler ve kurtarma bayrakları ayrı tutulur.
- Gerçekleşmiş maç xG'si yalnızca gösterim ve maç sonrası analiz içindir; maç öncesi modellerde kullanılmaz, çünkü başlama saatinden sonra bilinir.
- Ayrıntı: [Data Quality](docs/reports/data_quality.md).

## 2. Modeller

| Model | Üretimde | Değerlendirme | Rapor |
| :--- | :--- | :--- | :--- |
| Gol skor matrisi (`v1.6`) | Bağımsız Poisson × Dixon-Coles, `full` 60 özellik (`exp_match_xg_10` ve `exp_venue_match_xg` dahil), α=3, w_dc=0.0; eğitim/değerlendirme/API'de 1X2'ye (`v1.3`) hizalı; O1.5, O2.5, O3.5 ve KG kalibratörleri aktif; KG etiketi kapalı | Skor NLL 2.9686 (v1.5: 2.9737, v1.4: 2.9786); O2.5 LL 0.6767 (haftalık refit 0.6753), Δ prior −0.0080 CI [−0.0156, −0.00001] (3/3 negatif sezon); KG LL 0.6804 | [goals_model.md](docs/reports/models/goals_model.md) |
| 1X2 (`v1.3`) | 71 özellikli lojistik (C=0.003; penaltı arındırılmış `npxG` + `npBC` + `sdiff_pa_entries_e02/r10` eklendi, 8 ham gol sütunu çıkarıldı) + ayrıştırılmış L2 cezalı OOF sıcaklık/bias kalibrasyonu (`reg_temp=0.10, reg_bias=0.50`) | 3 dış sezon (`N=1,140`) Pooled LL 0.9746 (v1.2: 0.9757, v1.1: 0.9789), Brier 0.5798, RPS 0.1980, İsabet %55.09 (v1.1: %54.12), CV LL 0.9709; 304 maç holdout LL 1.026 (`1.0256`) vs 1.092, Brier 0.617, RPS 0.2076, Acc %49.34 | [outcome_1x2_model.md](docs/reports/models/outcome_1x2_model.md) |
| Korner | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE 3.235) | [corners_model.md](docs/reports/models/corners_model.md) |
| Taç | `poisson_10` | RMSE 6.941 vs 7.337; geliştirme dış sezon 2/2 | [throws_model.md](docs/reports/models/throws_model.md) |
| Ofsayt | `ridge_250` | RMSE 1.906 vs 2.013; geliştirme dış sezon 2/2 | [offsides_model.md](docs/reports/models/offsides_model.md) |
| Kart | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE 1.992) | [cards_model.md](docs/reports/models/cards_model.md) |
| Kurtarış | `training_mean` | CV kapısı 2/4 kat → ortalama (holdout RMSE 2.348) | [saves_model.md](docs/reports/models/saves_model.md) |

Artifact tarihleri: tüm modeller 24 Ekim 2026, güncel özellik tablosuyla (1.595 maç) yeniden eğitildi.

## 3. Son Değişiklikler (24 Ekim 2026)

- **Kod tabanı ve model metodolojisi denetimi (`K1–K9`):**
  - **1X2 ensemble kapısı (`K1`):** `ensemble_gate_passed` doğrudan dış-sezon kapısına bağlandı (`False`); harman ağırlığı `choose_blend_weight` çıktısından alınıyor; kullanılmayan `model_o25` çıkarıldı.
  - **Hibrit `/api/model-audit` (`K2`):** `1x2_forecast_log.jsonl` içindeki maç öncesi kayıtlar `prospective`, geçmiş maçlar `in_sample_backfill` olarak ayrıştırıldı; prospektif kayıtlar ezilmiyor.
  - **Goals hizalı kalibrasyon ve değerlendirme (`K3`, `K7`):** O/U ve KG kalibratörleri ile dış-sezon değerlendirmesi, API ile birebir aynı şekilde 1X2-hizalı skor matrisi üzerinde çalışıyor; `rho` parametresi OOF/harmanlanmış $\lambda$'lar üzerinde `sample_weight` ile tahmin ediliyor; `skill_gate` değerlendirmeden dinamik türetiliyor. Skor NLL `2.9786 -> 2.9737`, O2.5 LL `0.6774 -> 0.6765`, ECE `%5.07 -> %3.99` iyileşti.
  - **Sayım modelleri metodolojisi (`K4`, `K6`):** NB2 dispersiyonu ($\alpha$) koşullu model artıklarından (residuals) tahmin ediliyor; dış-sezon kapısı `%20` test holdout dönemine sızmadan yalnızca `%80` geliştirme dönemindeki tam sezonları kullanıyor (bunun sonucunda korner modeli `1/2` dış sezonla `training_mean`'e çekildi); tüm sayım modelleri `CountModelSpec` ve `fill_value=np.nan` (`SimpleImputer`) ile birleştirildi.
  - **Eğitim–tahmin XI mevki uyumu (`K5`):** `build_features.py` ve `sync_prematch_lineups.py` maç günü mevkisini (`load_official_match_starters`) kullanacak şekilde eşitlendi; 140 model sütununun tamamı `tests/test_train_serve_parity.py` ile doğrulandı.
  - **Birleşik tahmin servisi ve API temizliği (`K8`, `K9`):** Tüm tahmin akışı `src/api/prediction_service.py` altında toplandı; `state.py` içinde `corner`, `throws`, `saves` yeniden yükleme listesine eklendi; `/api/benchmarks` artık `cards` ve `goals` metriklerini de döndürüyor.
- **Testler:** 103/103 geçiyor (`tests/`).

## 4. Bilinen Sınırlar

- **Gol modeli** takım güç farkını yakalıyor (gol farkı korelasyonu 0.44) ama toplam gol hacmini neredeyse hiç ayırt edemiyor (0.065). Sabit Poisson'a karşı farkı anlamlı değil; bahis edge'i iddiası için temel oluşturmaz.
- **1X2 modeli** genel beraberlik oranını biliyor ama beraberliği maç maç ayıramıyor (beraberlik olasılığı, beraberlikle biten maçlarda %25.7, diğerlerinde %24.9).
- **Sayım modellerinin** ortalamaya karşı kazancı yalnızca taç ve ofsaytta dış-sezon kapısını geçiyor; korner, kart ve kurtarış dürüst `training_mean` baseline'ında.
- **API'de model olmayan alanlar:** `shots.expected_total` sabit çarpandır (`kurtarış × 4.1`) ve API'de `model_skill: "heuristic_from_saves"` olarak açıkça etiketlenir. Ev/deplasman paylaşımları rolling oranlardan gelir. Bkz. [API Entegrasyonu §2.6](docs/model_api_integration.md).
- **İleriye dönük kayıt:** `docs/reports/prospective_1x2_scorecard.json` ilk 15 tamamlanmış prospektif maç için üretildi; örneklem büyüdükçe istatistiksel güç artacak.

## 5. Sıradaki İşler

1. Her oyun haftasından sonra `python3 run_full_pipeline.py` çalıştır, ardından API'yi yeniden başlat. Otomatik raporlar (`model_benchmarks.md`, `data_quality.md`, `team_*.md`) bu sırada yenilenir.
2. Maç öncesi tahmin kaydını sürdür (`prospective_1x2_benchmark snapshot`) ve biten maçları puanla. Kısmi sezona bakarak modeli tekrar tekrar ayarlama.
3. Korner, ofsayt ve taç modellerine kart modelindeki gibi derin denetim yap: özellik ablasyonu, kazancın "seviye uyumu" ile "maçlar arası ayrım" arasında ayrıştırılması.
4. 1X2 denetimini güncel artifact (77 özellik) üzerinde yenile; [1x2_model_audit.md](docs/reports/1x2_model_audit.md) 14 Ekim tarihli.
5. Python bağımlılıklarını bir `requirements.txt` dosyasına sabitle; `pytest`'i geliştirme bağımlılığı olarak ekle.
6. Kart hedefinde `total_yellow_cards_target_usable` bayrağının eğitimde filtrelenmesi gerekip gerekmediğini doğrula.
