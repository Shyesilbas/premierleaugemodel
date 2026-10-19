# research/

Tek seferlik denetim ve deney scriptleri. **Üretim pipeline'ında, cron'da ve testlerde kullanılmaz;** bakımı yapılmaz.

| Klasör | İçerik | Dikkat |
|---|---|---|
| `audit/` | Adli doğrulamalar (özellik sızıntısı, DB sayıları, kayıtlı metrikler, olasılık aksiyomları, kalibrasyon). | `draw_recalibration.py` içe aktarırken `127.0.0.1:8000`'e HTTP isteği atar (API açık olmalı); `draw_calibration.py` ve `tune_blend.py` `src.api.server`'ı yükler (~30 sn). |
| `scratch/` | Gol modeli P0/P1 denetimleri, Segment 10 teşhisi, XGBoost ve özellik A/B denemeleri. | Sayılar 17–18 Ekim 2026 öncesi modele aittir. `diagnose_segment10_and_test_xgboost.py` `xgboost` ister; `requirements.txt`'te yok. |

Kökten çalıştırın: `PYTHONPATH=. python3 research/audit/investigation_1.py`. Dosyalar `test_` ile başlamaz, böylece `pytest` bunları toplamaz.
