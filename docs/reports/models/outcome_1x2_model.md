# 1X2 Maç Sonucu Modeli — Model Raporu

**Rapor tarihi:** 17 Ekim 2026 (`v1.1`)
**Artifact:** `models/production/outcome_models_v1.joblib` · **Kod:** `src/models/train_match_outcome.py`, `src/models/model_utils.py`
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Gol Model Raporu](goals_model.md) · **[Detaylı uçtan uca denetim (14 Ekim 2026)](../1x2_model_audit.md)**

> Bu içerik 17 Ekim 2026'da ana rapordan taşındı. Ayrıntılı denetim (etiketler, özellikler, beraberlik analizi, API sunumu) [1x2_model_audit.md](../1x2_model_audit.md)'dedir. API'de gol skor matrisi bu modelin 1X2 olasılıklarına hizalanır — bkz. [Gol Model Raporu §11.8](goals_model.md#118-uygulanan-düzeltmeler-ve-sonuçları-17-ekim-2026).

---

## Mimari ve Holdout Sonuçları

> Değerler üretim artifact'ının `metrics['model_1x2']` alanından alındı (artifact: 17 Ekim 2026, güncel özellik tablosuyla yeniden eğitildi; holdout log-loss, Brier, isabet ve beraberlik AUC'si 16 Ekim artifact'ıyla aynı). Bu bölüm ana rapordan taşınırken eski bir çalıştırmanın değerlerini (44 özellik, Brier 0.619, isabet %49.01, beraberlik AUC 0.527) içeriyordu; 17 Ekim 2026'da güncellendi.

- **Mimari:** 77 özellik → `SimpleImputer(median)` → `StandardScaler` → `LogisticRegression(C=0.003)` → ileri OOF sıcaklık kalibrasyonu ($T=0.9591$, $b = [-0.0727, +0.0300, -0.0093]$). Draw-propensity özellikleri kapalı (`draw_propensity_enabled: false`).
- **Seçim:** `logreg_C0.003`, geliştirme CV log-loss 0.9756 (836 maç; 2022/23 sabit dışlama sonrası). Final fit 1.200 maç.
- **Holdout (304 maç, eşit başlama saatleri bölünmeden son %20):**

| Ölçüm | Model | Sınıf-prior |
| :--- | :---: | :---: |
| Log-loss | **1.026** | 1.092 |
| Çok sınıflı Brier | **0.617** | 0.661 |
| İsabet | **%49.67** | %40.79 |

Eşleştirilmiş bootstrap model–prior log-loss farkı −0.0622, %95 CI [−0.0999, −0.0225] ([1x2_model_audit.md](../1x2_model_audit.md)). Dixon-Coles karşılaştırıcısı aynı satırlarda 1.0454 (kalibre; ham 1.0477).

### Beraberlik Ayrım Gücü (Draw AUC = 0.557)
- Holdout'ta gerçek beraberlik oranı %27.96; modelin ortalama beraberlik olasılığı %25.08.
- Beraberlikle biten maçlara ortalama **%25.68**, diğer maçlara **%24.85** beraberlik olasılığı veriyor: ayrım farkı yalnızca **+0.83 puan**.
- Beraberlik kalibrasyon hatası (ECE) %5.3. Model genel beraberlik oranını bilir ama beraberliği maç maç ayıramaz.


---

## Reddedilen Deneyler (1X2)

| Model | Denenen Çözüm | Test Sonucu | Alınan Ders & Karar |
| :--- | :--- | :---: | :--- |
| **1X2** | **Lag'li xG Özellikleri** | Holdout kazancı yok | Zamanlama sızıntısı ve veri eksikliği. ❌ **Kaldırıldı.** |
| **1X2** | **İki Aşamalı Beraberlik Modeli** | LL 1.026 $\to$ **1.0536**, Brier 0.6378 | Beraberlik ayrımını çözmedi. ❌ **Reddedildi.** |
| **1X2** | **9 Draw-Propensity Özelliği** | Dış sezon LL 0.9834 $\to$ **0.9875** | Gürültüyü artırdı; kapıyı geçemedi. ❌ **Reddedildi.** |
| **1X2** | **1X2 Dixon-Coles Ensemble** | Dış sezonda $\Delta = +0.0045$ ($p=0.1754$) | Lojistik model tek başına daha üstün. ❌ **Reddedildi.** |
