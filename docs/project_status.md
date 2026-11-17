# Project Status

**Snapshot:** 17 Kasım 2026  
**Belgeler:** [Veri kaynakları haritası](data_sources.md) · [README](../README.md) · [Rapor Merkezi](../reports/README.md) · [Ana Rapor](reports/premier_league_models_comprehensive_report.md) · [Model Raporları](reports/models/) · [Model Benchmarks](../reports/model_benchmarks.md)

---

## 1. Veri

| Kalem | Değer |
| :--- | :--- |
| Fikstür (Premier League) | 1.900 (5 sezon: 2022/23–2026/27) |
| Oynanmış maç | 1.608 · 2026/27: 88/380 (kilitli sezon, yalnızca raporlanır) |
| Sağlayıcı xG kapsamı (2026/27) | 69 maç (`external_match_xg`; toplam DB'de 2.966 satır) |
| Özellik tablosu | `data/competitions/premier_league/processed/features_matches_all.parquet` (`1.900` satır, `747` sütun) |
| İleriye dönük tahmin kaydı | `data/competitions/premier_league/processed/1x2_forecast_log.jsonl`: 220 kayıt (`reports/prospective_1x2_scorecard.json` 17 Kasım 2026 itibarıyla güncellendi; son üretim gruplarında 13–20 maç puanlı) |

### Avrupa kupaları (yalnızca veri, model yok)

| Turnuva | Satır | Oynanmış | Kaynak |
| :--- | :--- | :--- | :--- |
| Şampiyonlar Ligi (`competition_id` 2) | 772 | 700 | UEFA herkese açık API (fikstür, sonuç, kadro, olay, puan durumu) + TheStatsAPI (istatistik, xG, oyuncu, şut haritası, kadro/piyasa değeri) |
| Avrupa Ligi (`competition_id` 3) | 804 | 732 | Aynı |

Sezonlar 2022/23–2026/27. 2022/23-2023/24 sekiz gruplu klasik grup aşaması, 2024/25'ten itibaren tek 36 takımlı lig aşaması (8 hafta) ve eleme turları. Eleme turları 9-13 sabit hafta numaralarını taşır. Oranlar yalnızca 2024/25 ve sonrası için çekildi.

- Eksik `won_corners` değerleri olay akışından kurtarılır (`69` takım değeri; kurtarış hedefi olay akışıyla `1.608` maçın tamamında dolu). Ham değerler ve kurtarma bayrakları ayrı tutulur.
- Gerçekleşmiş maç xG'si yalnızca gösterim ve maç sonrası analiz içindir; maç öncesi modellerde kullanılmaz, çünkü başlama saatinden sonra bilinir.
- Ayrıntı: [Data Quality](../reports/data_quality.md).

## 2. Modeller

| Model | Üretimde | Değerlendirme | Rapor |
| :--- | :--- | :--- | :--- |
| Gol skor matrisi (`v1.6`) | Bağımsız Poisson × Dixon-Coles, `full` 60 özellik (`exp_match_xg_10` ve `exp_venue_match_xg` dahil), α=3, w_dc=0.0; eğitim/değerlendirme/API'de 1X2'ye (`v1.4`) hizalı; O1.5, O2.5, O3.5 ve KG kalibratörleri aktif; KG etiketi kapalı | 1.608 fit (`1.520` kalibrasyon); Skor NLL `2.9673` (null `3.0959`), O2.5 LL `0.6763` (haftalık refit `0.6752`), Δ prior `−0.0085` CI `[−0.0163, −0.0005]` (3/3 negatif sezon, `P=%98.4`); KG LL `0.6805` | [goals_model.md](reports/models/goals_model.md) |
| 1X2 (`v1.4`) | 74 özellikli lojistik (C=0.003; `npxG` + `npBC` + `sdiff_pa_entries` + İlk 11 `xi_continuity_diff`, `xi_weighted_ov_diff`, `missing_reg_mins_diff`) + ayrıştırılmış L2 cezalı OOF sıcaklık/bias kalibrasyonu (`reg_temp=0.10, reg_bias=0.50`) | `1.228` fit (`922` OOF); 3 dış sezon (`N=1,140`) Pooled LL `0.9732`, Brier `0.5790`, RPS `0.1977`, CV LL `0.9674`; 304 holdout LL `1.024` (`1.0240`) vs `1.092`, Brier `0.616`, RPS `0.2073`, Acc `%50.33` | [outcome_1x2_model.md](reports/models/outcome_1x2_model.md) |
| Korner | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE `3.2276`, MAE `2.6601`) | [corners_model.md](reports/models/corners_model.md) |
| Taç | `ridge_100` | Holdout RMSE `6.9994` vs `7.3884` (`R² 0.0932`); geliştirme dış sezon `2/2` | [throws_model.md](reports/models/throws_model.md) |
| Ofsayt | `ridge_250` | Holdout RMSE `1.9263` vs `2.0356` (`R² 0.0931`); geliştirme dış sezon `2/2` | [offsides_model.md](reports/models/offsides_model.md) |
| Kart | `training_mean` | Geliştirme dış sezon 1/2 → ortalama (holdout RMSE `1.9744`, MAE `1.5783`) | [cards_model.md](reports/models/cards_model.md) |
| Kurtarış | `training_mean` | Geliştirme dış sezon 0/2 → ortalama (holdout RMSE `2.3633`, MAE `1.9085`) | [saves_model.md](reports/models/saves_model.md) |

Artifact tarihleri: Tüm Premier League modelleri **17 Kasım 2026**'da `1.608` maçlık güncel yerel veriyle (`2026_27` kilitli sezonu seçime ve kalibrasyona kapalı tutularak) yeniden eğitilmiştir (`models/production/premier_league/`). Şampiyonlar Ligi ve Avrupa Ligi yalnızca veri gösterir; yerel yapılandırmada üç aktif turnuva (`premier_league`, `champions_league`, `europa_league`) bulunur.

## 3. Son Değişiklikler (17 Kasım 2026)

- **Tek lig + Avrupa kupaları sadeleştirmesi:** Yalnızca `premier_league` (39) ve UEFA kupaları (`champions_league` 2, `europa_league` 3) aktif bırakıldı; çoklu ulusal lig iskeleti (`provider: thestatsapi`) genel amaçlı biçimde korundu.
- **Tam PL pipeline ve rapor senkronu:** `run_full_pipeline.py` ve `prospective_1x2_benchmark score` güncel veritabanıyla (`1.608` oynanmış PL maçı, `2026_27: 88`) yeniden çalıştırıldı; taç modeli `poisson_10`'dan `ridge_100`'e geçti, korner/kart/kurtarış dürüst `training_mean` baz çizgisinde kaldı ve el ile bakımı yapılan tüm model dokümanları yeni `.joblib` çıktılarıyla hizalandı.
- **Dokümantasyon ve doğrulama hattı:** `AGENTS.md`, modül hub `README.md` dosyaları, `.agents/skills/*` ve `scripts/verify.sh` birleşik kontrol zinciri (`check_no_emoji`, `check_docs`, `check_api_endpoints`, backend testleri, frontend `lint:design`, `oxlint`, `vite build`) kuruldu; frontend yerel `<dialog>` ve semantik karanlık/aydınlık mod token'larına geçirildi.
- **Testler:** 268/271 geçiyor (ek yerel `thestatsapi` lig modeli olmadığından 3 `test_league_serving` testi atlanıyor).

### Önceki Kilometre Taşları (24–26 Ekim 2026)

- **Kod tabanı sadeleştirme ve turnuva bazlı düzen:** `src/core/` kaldırıldı; `data/competitions/<anahtar>/` ve `models/production/<anahtar>/` klasör yapısı, `data/football.db`, UEFA + TheStatsAPI Avrupa kupaları verisi ve yetenek bayrakları (`hasModel`, `hasAudit`, `richData`, `syncKinds`) yerleştirildi.
- **Kod tabanı ve model metodolojisi denetimi (`K1–K9`):** 1X2 ensemble kapısı, hibrit `prospective` vs `in_sample_backfill` ayrımı, 1X2-hizalı gol değerlendirme/kalibrasyon hattı, sayım modelleri iki-aşamalı CV + geliştirme dış sezon kapısı ve `140` sütunluk train-serve parity (`tests/test_train_serve_parity.py`) tamamlandı.
- **PL piyasa değeri sızıntısı notu:** PL 1X2 modelinin `log_mv_ratio` / `effective_log_mv_ratio` özellikleri geçmiş sezonlarda sezon sonu Transfermarkt değerini okur; etki tavanı küçük (`+0.0016`, `H4c`) olduğu için düşük öncelikli kontrol olarak izlenmektedir ([outcome_1x2_model.md](reports/models/outcome_1x2_model.md) §4).
- **Testler:** Güncel test koşusu doğrulama adımında izlenir (`pytest -q`).

## 4. Bilinen Sınırlar

- **Gol modeli** takım güç farkını yakalıyor ama toplam gol hacmini sınırlı ayırt edebiliyor; piyasa 2.5 Üst'te önde olduğundan bahis edge'i iddiası için temel oluşturmaz.
- **1X2 modeli** genel beraberlik oranını biliyor ama beraberliği maç maç sınırlı ayırabiliyor (holdout `Draw AUC = 0.5574`).
- **Sayım modellerinin** ortalamaya karşı kazancı yalnızca taç (`ridge_100`) ve ofsaytta (`ridge_250`) dış-sezon kapısını geçiyor; korner, kart ve kurtarış `training_mean` baseline'ında.
- **API'de model olmayan alanlar:** `shots.expected_total` sabit çarpandır (`kurtarış × 4.1`) ve API'de `model_skill: "heuristic_from_saves"` olarak etiketlenir. Bkz. [API Entegrasyonu §2.6](model_api_integration.md).
- **İleriye dönük kayıt:** `reports/prospective_1x2_scorecard.json` her artifact parmak izi için ayrı prospektif gruplar tutar; örneklem büyüdükçe istatistiksel güç artacaktır.

## 5. Çoklu Lig Mimari Altyapısı (Multi-League Readiness)

- **Turnuva Kayıt Defteri (`config/competitions.yaml`):** Premier League (`39`), Şampiyonlar Ligi (`2`), Avrupa Ligi (`3`); biçim, sağlayıcı ve sezon varsayılanları burada.
- **Ortak Motor & Sağlayıcılar:** `src/models/` ve `src/features/` modülleri çoklu turnuvaya uyumludur; yeni bir TheStatsAPI ligi eklendiğinde `fetch_thestatsapi_league`, `load_thestatsapi_league`, `fetch_openfootball_schedule`, `train_league_*` ve `league_prediction` modülleri yeniden kullanılabilir. `src/competitions/normalizer.py` şu an üretim modellerinde kablolanmamıştır.

## 6. Sıradaki İşler

1. Her oyun haftasından sonra `python3 run_full_pipeline.py` çalıştır, ardından API'yi yeniden başlat (`model_benchmarks.md`, `data_quality.md`, `team_*.md` yenilenir).
2. Maç öncesi tahmin kaydını sürdür (`python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14`) ve biten maçları puanla (`score`).
3. Korner, ofsayt ve taç modellerine kart modelindeki gibi özellik ablasyonu ve seviye-uyumu / maçlar-arası ayrım denetimi yap.
4. 1X2 forensic denetimini (`reports/audits/1x2_model_audit.md`) güncel 74 özellikli (`v1.4`) üretim artifact'ı üzerinde yenile.
5. (Düşük öncelik) PL piyasa değeri özelliklerinin sezon sonu sızıntısını S-1 sezon satırıyla test et ([outcome_1x2_model.md](reports/models/outcome_1x2_model.md) §4).
6. Kart hedefinde `total_yellow_cards_target_usable` bayrağının eğitimde filtrelenmesi gerekip gerekmediğini doğrula.
