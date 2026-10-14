# Proje Rapor Merkezi

Bu sayfa raporların tek giriş noktasıdır. Güncel model puanları için önce benchmark raporuna, kod ve ürün incelemesi için kapsamlı denetime bakın.

## Başlangıç noktaları

| İhtiyaç | Rapor | İçerik |
|---|---|---|
| Güncel model başarımı | [Model Benchmarks](model_benchmarks.md) | Kronolojik holdout, sezon bazlı sonuçlar, kalibrasyon, regresyon ve gol-market ölçümleri |
| Kod tabanı ve yapılacaklar | [Repository Audit](repository_audit.md) | Mimari, test/benchmark kapsamı, riskler ve önceliklendirilmiş geliştirme planı |
| Proje özeti | [Project Status](../PROJECT_STATUS.md) | Veri anlık görüntüsü, bilinen model sınırları ve sıradaki işler |
| Veri ve kaynak kalitesi | [Data Quality](data_quality.md) | Maç sayıları, ham alan kapsaması, eksik hedefler ve kurtarılan etiketler |
| 1X2 ek veri pilotu | [External Data Pilot](1x2_external_data_pilot.md) | İlk altı hafta için xG, kadro/eksikler ve bahis oranı kaynaklarının kapsaması |
| İlk 11 özelliği deneyi | [Lineup Feature Pilot](1x2_lineup_feature_pilot.md) | Sezon öncesi eğitimle ilk altı haftada kadro devamlılığının küçük örneklemli etkisi |

## Rapor envanteri

| Rapor | Konu ve kullanım |
|---|---|
| [Model Benchmarks](model_benchmarks.md) | Güncel skorların ve değerlendirme protokolünün tek kaynağı. Tam pipeline tarafından üretilir. |
| [1X2 Model Audit](1x2_model_audit.md) | 1X2 olasılıkları, beraberlik ayrımı, zamansal değişim ve ileriye dönük ölçüm. Benchmark raporunu tamamlar. |
| [1X2 External Data Pilot](1x2_external_data_pilot.md) | İlk altı haftada harici xG/oran kaynakları, yerel kadro kapsaması ve geçerli deney sınırları. |
| [1X2 Lineup Feature Pilot](1x2_lineup_feature_pilot.md) | İlk 11 açıklandıktan sonra tahmin edilen senaryo için üretim dışı keşif deneyi. |
| [Data Quality](data_quality.md) | Kaynak verinin, etiketlerin ve eksik değerlerin dağılımı. Pipeline tarafından üretilir. |
| [Team Tactical Data Audit](team_tactical_data_audit.md) | Taktik alanların sezon bazında ham veri kapsaması. Pipeline tarafından üretilir. |
| [Team Scenario Validation](team_scenario_validation.md) | Olay akışından çıkarılan şut/korner senaryolarının maç istatistikleriyle karşılaştırması. Pipeline tarafından üretilir. |
| [Model Diagnostic Follow-up](model_diagnostic_followup.md) | Önceki veri anlık görüntülerindeki araştırma notları. Tarihsel belgedir; güncel skor kaynağı değildir. |
| [Artifact Registry](../ARTIFACT_REGISTRY.md) | Veri, model ve değerlendirme dosyalarının hangi komutlarla üretildiği. |

## Makine tarafından üretilen değerlendirmeler

| Dosya | İçerik |
|---|---|
| [`regression_skill_gate_eval.json`](../data/processed/regression_skill_gate_eval.json) | Beş sayım hedefi için CV kapısı, seçilen model ve sezon holdout'ları |
| [`goal_model_outer_eval.json`](../data/processed/goal_model_outer_eval.json) | Gol pazarı ve skor matrisi modellerinin dış-sezon sonuçları |
| [`1x2_ensemble_outer_eval.json`](../data/processed/1x2_ensemble_outer_eval.json) | Dixon–Coles ve lojistik ensemble dış-sezon kapısı |
| [`1x2_draw_propensity_outer_eval.json`](../data/processed/1x2_draw_propensity_outer_eval.json) | Beraberlik özellikleri için dış-sezon karar kapısı |
| [`1x2_calibration_drift_outer_eval.json`](../data/processed/1x2_calibration_drift_outer_eval.json) | Zaman ağırlıklı kalibrasyon karşılaştırması |
| [`1x2_forecast_log.jsonl`](../data/processed/1x2_forecast_log.jsonl) | Maç öncesinde kaydedilmiş, artefakt SHA-256 değerleriyle ilişkilendirilmiş tahminler |
| `reports/prospective_1x2_scorecard.json` | Tamamlanan kayıtlı tahminlerin ileriye dönük skor kartı; henüz oluşmadı |

## Raporların güncellenme düzeni

`python3 run_full_pipeline.py` yerel ham veriden işlenmiş tabloları ve özellikleri yeniden kurar; model artefaktlarını, `model_benchmarks.md`, `data_quality.md`, `team_tactical_data_audit.md` ve `team_scenario_validation.md` raporlarını günceller. Komut dış kaynaktan yeni veri çekmez ve SQLite veritabanını yenilemez.

`1x2_model_audit.md`, `model_diagnostic_followup.md`, `PROJECT_STATUS.md` ve `ARTIFACT_REGISTRY.md` açıklamalı dokümanlardır; pipeline bunları otomatik yenilemez. Yeni ölçümden sonra tarihsel metriklerin güncel değer gibi görünmemesi için bu belgeleri bu sayfayla birlikte kontrol edin.

## Envanter notu

Denetim başlangıcında Git çalışma ağacı `reports/model_improvement_guide.md` dosyasını silinmiş (`D`) gösteriyordu. Proje durum ve 1X2 denetim belgelerinde bu dosyaya giden bağlantılar vardı. Kırık bağlantılar güncel rapor merkezine yönlendirildi; dosyanın silinmiş durumunu değiştirmedim. Önceki sürüm Git geçmişinde duruyor. F4–F10 için hâlâ geçerli kararların özeti [Repository Audit](repository_audit.md) içindedir.
