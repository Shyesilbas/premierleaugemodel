# 1X2 Maç Sonucu Modeli — Model Raporu

**Rapor tarihi:** 25 Ekim 2026 (`v1.4`)
**Artifact:** `models/production/outcome_models_v1.joblib` · **Kod:** `src/models/train_match_outcome.py`, `src/models/model_utils.py`, `src/features/build_features.py`, `src/processing/process_season_data.py`
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Gol Model Raporu](goals_model.md) · **[Detaylı uçtan uca denetim (14 Ekim 2026)](../1x2_model_audit.md)**

> Bu içerik 17 Ekim 2026'da ana rapordan taşındı ve 25 Ekim 2026 (`v1.3 -> v1.4`) dış sezon deneyleriyle güncellendi. API'de ve Gol modelinin kalibrasyon/değerlendirme hattında 13x13 gol skor matrisi bu modelin 1X2 olasılıklarına hizalanır — bkz. [Gol Model Raporu §11.11](goals_model.md).

---

## Mimari ve Değerlendirme Sonuçları (`v1.4`)

> Değerler üretim artifact'ının (`models/production/outcome_models_v1.joblib`, 25 Ekim 2026) `metrics['model_1x2']` alanından alındı.

- **Mimari:** 74 özellik (`v1.3`'teki 71 özelliğe ek olarak: (1) son 12 maçtaki dakika paylarına göre ilk 11 kadro istikrarı ve uyum üstünlüğü `xi_continuity_diff`, (2) ilk 11 oyuncularının maç önü reytinglerinin son 12 maç dakika paylarıyla ağırlıklandırılmış net farkı `xi_weighted_ov_diff`, (3) son 12 maçta >=%40 dakika alıp bugünkü ilk 11'de yer almayan eksik as oyuncuların toplam dakika payı net farkı `missing_reg_mins_diff`) → `SimpleImputer(median, keep_empty_features=True)` → `StandardScaler` → `LogisticRegression(C=0.003, max_iter=5000)` → ayrıştırılmış L2 cezalı ileri OOF sıcaklık + sınıf kesişimi kalibrasyonu (`reg_temp=0.10`, `reg_bias=0.50`; `922` OOF maçı). Draw-propensity özellikleri (`draw_propensity_enabled: false`) ve Dixon-Coles ensemble (`1x2_ensemble_production.enabled: false`) dış sezon kapısını geçemediği için kapalıdır.
- **Seçim:** `logreg_C0.003`, geliştirme CV log-loss **`0.9674`** (`v1.3`: `0.9709`, `v1.2`: `0.9739`, `v1.1`: `0.9755`; 836 maç, `2022/23` sabit dışlama sonrası). Final üretim fit `1.215` oynanmış maç (`2026/27` kilitli sezon kalibrasyon ve model seçiminden hariç).

### 1. Üç Tam Dış Sezon Yürüyen Pencere (Walk-Forward) Sonuçları (`2023/24–2025/26`, `N = 1,140`)

Her dış sezon yalnızca kendinden önceki sezonlarla eğitilip kalibre edilerek tek seferde puanlanmıştır (`2023/24` sezonu tek öncül sezon olan `2022/23` ile `early_season_fallback=True` olarak raporlanır):

| Sezon | Maç (`N`) | Ham LL (`v1.4`) | Kalibre LL (`v1.4`) | Kalibre LL (`v1.3` / `v1.2` / `v1.1`) | Sınıf-Prior LL | Bet365 Kapanış LL | İsabet (`v1.4` / `v1.3`) | Çok Sınıflı Brier | RPS (`v1.4` / Prior) | Draw AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`2023/24`** | 380 | 0.9299 | **0.9292** | 0.9278 / 0.9278 / 0.9317 | 1.0563 | 0.9028 | **%59.74** / %61.32 | 0.5445 | **0.1878** / 0.2346 | 0.5550 |
| **`2024/25`** | 380 | 0.9715 | **0.9730** | 0.9777 / 0.9792 / 0.9827 | 1.0834 | 0.9674 | **%54.47** / %55.26 | 0.5815 | **0.1979** / 0.2358 | 0.5120 |
| **`2025/26`** | 380 | 1.0167 | **1.0174** | 1.0184 / 1.0201 / 1.0223 | 1.0852 | 1.0136 | **%49.21** / %48.68 | 0.6110 | **0.2073** / 0.2279 | 0.5678 |
| **Pooled (`N=1,140`)** | **1,140** | **0.9727** | **0.9732** | 0.9746 / 0.9757 / 0.9789 | 1.0750 | 0.9613 (`N=1,134`) | **%54.47** / %55.09 | **0.5790** (`v1.1`: 0.5826) | **0.1977** (`v1.1`: 0.1994) | **0.5449** |

- **Toplam İlerleme (`v1.1 -> v1.4`, `N=1,140`):** Havuzlanmış 3 dış sezon Log-Loss `0.9789 -> 0.9757 -> 0.9746 -> 0.9732` ($\Delta = \mathbf{-0.0057}$), Çok Sınıflı Brier `0.5826 -> 0.5806 -> 0.5798 -> 0.5790`, RPS `0.1994 -> 0.1985 -> 0.1980 -> 0.1977`. Kilitli `2026/27` sezonundaki (`N=75` maç) Log-Loss `0.9983 -> 0.9943`'e düşerken denetim isabeti de `%49.3 -> %50.7`'ye yükselmiştir.
- **Gol Modeli (`v1.6`) Üzerindeki Hizalama Etkisi:** 1X2 modelindeki `v1.4` güncellemesiyle 1X2-hizalı Gol modelinin 2.5 Üst haftalık refit Log-Loss'u `0.6752`'ye (`2025/26` dondurulmuş 2.5 Üst LL: `0.6887`), dış sezon Tam Skor NLL'si `2.9686`'ya optimize olmuştur.

### 2. Ana Kronolojik Holdout (`N = 304` Maç, Eşit Başlama Saatleri Bölünmeden Son %20)

| Ölçüm | Model (`v1.4`) | Sınıf-Prior | Dixon-Coles (Kalibre / Ham) |
| :--- | :---: | :---: | :---: |
| **Log-loss** | **1.024** (`1.0240`, Ham: `1.0240`) | 1.092 | 1.0459 / 1.0477 |
| **Çok sınıflı Brier** | **0.616** (`0.6160`) | 0.661 | 0.6290 / 0.6291 |
| **RPS (Ranked Probability Score)** | **0.2073** (`v1.3`: `0.2076`, `v1.1`: `0.2083`) | 0.2288 | — |
| **İsabet (Accuracy)** | **%50.33** (`v1.3`: `%49.34`) | %40.79 | %44.08 / %44.08 |

- Eşleştirilmiş bootstrap model–prior log-loss farkı: **`-0.0680`**, %95 CI **`[-0.1062, -0.0285]`**, `P(daha iyi) = %99.98`.

### 3. Beraberlik Ayrım Gücü (`Draw AUC = 0.5574` Holdout · `0.5449` 3 Dış Sezon)
- Holdout'ta gerçek beraberlik oranı `%27.96`; modelin ortalama beraberlik olasılığı `%24.60`.
- Model genel beraberlik oranını kalibre eder ancak tekil maçlarda beraberliği ayırt etme gücü doğrusal sınırlar içindedir (`Bet365` kapanış oranlarında dahi 3 dış sezon Draw AUC `0.5699`'dur).

---

## Deney Kayıtları: Kabul Edilen ve Reddedilen Deneyler (1X2)

### Kabul Edilen İyileştirmeler (`v1.3 -> v1.4`, 25 Ekim 2026)

| Kod | Denenen Çözüm | 3 Dış Sezon (`N=1,140`) / Holdout Sonucu | Karar |
| :--- | :--- | :---: | :--- |
| **XI_MIN_1** | **İlk 11 Kadro Devamlılığı (`xi_continuity_diff`, `71 -> 72` özellik)** | CV LL `0.9709 -> 0.9683`, Holdout LL `1.0256 -> 1.0245`, Holdout Acc `%49.34 -> %50.00`, 3S Pooled LL `0.9746 -> 0.9726` (tüm dış sezonlarda kazanç: `23/24`: `0.9263`, `24/25`: `0.9742`, `25/26`: `1.0174`), Kilitli `2026/27` LL `0.9983 -> 0.9947` | Transfermarkt piyasa değeri yerine takımların son 12 maçındaki dakika payları üzerinden ilk 11 uyumu ve as kadro devamlılığı ölçüldü. **Üretimde (`v1.4`).** |
| **XI_MIN_2** | **İlk 11 Dakika Ağırlıklı Oyuncu Reyting Farkı (`xi_weighted_ov_diff`)** | CV LL `0.9709 -> 0.9707`, Holdout LL `1.0256 -> 1.0254`, `xi_continuity_diff` ile birleştiğinde CV LL `0.9681`, Holdout LL `1.0242` | Yedek/genç oyuncuların reyting ortalamasını şişirmesi engellendi; 11'in reytingi son 12 maçtaki dakika paylarıyla ağırlıklandırıldı. **Üretimde (`v1.4`).** |
| **XI_MIN_3** | **Eksik As Oyuncu Dakika Payı Farkı (`missing_reg_mins_diff`, `71 -> 74` özellik)** | Tüm 3 özellik birlikte: Dev CV LL **`0.9674`**, Holdout LL **`1.0240`**, Holdout Acc **`%50.33`**, Holdout RPS **`0.2073`**, Holdout Brier **`0.6160`**, Kilitli `2026/27` LL **`0.9943`** | Son 12 maçta >=%40 dakika alan ancak bugünkü ilk 11'de olmayan as oyuncuların toplam dakika kaybı net farkı modele eklendi. **Üretimde (`v1.4`).** |

### Reddedilen Deneyler (`v1.1` – `v1.4`)

| Model | Denenen Çözüm | Test Sonucu | Alınan Ders & Karar |
| :--- | :--- | :---: | :--- |
| **1X2** | **`missing_reg_impact_diff` (Reyting Çarpanlı Eksik Oyuncu Etkisi: $\sum \text{mins} \times (\text{rating}-6)$)** | Dev CV LL `0.9709 -> 0.9711`, 3S Pooled LL `0.9746 -> 0.9748` | Küçük örneklemli oyuncu reytinglerinin dakika payıyla çarpılması aşırı gürültü ve overfit yarattı; dakika payının (`missing_reg_mins_diff`) ve reytingin (`xi_weighted_ov_diff`) bağımsız özellikleri olarak verilmesi çok daha üstün performans sağladı. **Reddedildi.** |
| **1X2** | **Lag'li xG Özellikleri** | Holdout kazancı yok | Zamanlama sızıntısı ve veri eksikliği. **Kaldırıldı.** |
| **1X2** | **İki Aşamalı Beraberlik Modeli** | LL 1.026 $\to$ **1.0536**, Brier 0.6378 | Beraberlik ayrımını çözmedi. **Reddedildi.** |
| **1X2** | **9 Draw-Propensity Özelliği** | Dış sezon LL 0.9834 $\to$ **0.9875** | Gürültüyü artırdı; kapıyı geçemedi. **Reddedildi.** |
| **1X2** | **1X2 Dixon-Coles Ensemble** | Dış sezonda $\Delta = +0.0044$ ($p=0.1864$) | Lojistik model tek başına daha üstün. **Reddedildi.** |
| **1X2** | **H1a: OOF Kat Boyutu Ölçekli `C_fold` + Standart Kalibratör (`reg=0.01`)** | Dış sezon Pooled LL `0.9789 -> 0.9824` (`2023/24`: `0.9411`) | `C_fold` ölçeklendiğinde dahi serbest sınıf bias'ları (`reg=0.01`) ilk sezonda aşırı uyum üretti; `reg_bias=0.50` tek başına sorunu çözdü. **Reddedildi.** |
| **1X2** | **H2a / H2b: `LogReg` + `FeatureGoalModel (v1.6)` Skor Matrisi OOF Ensemble** | Sabit 70/30 harman dış sezonda `0.9753` verse de, ileri OOF ile ağırlık seçildiğinde (`H2a`) Pooled LL `0.9782`, Holdout LL `1.0285`, Holdout Acc `%48.03`, Draw ECE `%3.93`'e geriledi | Erken katlarda OOF harman ağırlığı seçimi gürültülü ve kalibrasyonu bozuyor; 1X2 modelinin bağımsız kalıp Gol matrisini hizalaması daha üstün. **Reddedildi.** |
| **1X2** | **H3a–H3d: Tempo $\times$ Güç Dengesi ve Analitik Poisson Beraberlik Özellikleri (`exp_match_xg_10`, `poisson_xg_draw_prob`, `low_tempo_x_balance`, `abs_sdiff_sot_r10`)** | Pooled LL `0.9760` (ham) $\to$ `0.9762–0.9777`, Holdout LL `1.0263 -> 1.0268–1.0278`, Draw ECE `%2.36 -> %3.80–%4.39` | Doğrusal multinomial lojistik regresyonda ek tempo/mutlak fark sütunları beraberlik ECE'sini ve `2025/26` dış sezon kaybını kötüleştirdi. **Reddedildi.** |
| **1X2** | **H4a / H4b: Güç Seviye Sütunlarının (`elo_home/away`, `ppg_home/away`) veya `log_mv_ratio`'nun Çıkarılması** | `H4a` Pooled LL `0.9760 -> 0.9786`; `H4c - log_mv_ratio` (`C3`) Pooled LL `0.9755 -> 0.9771` | L2 cezası altında hem `log_mv_ratio` hem `effective_log_mv_ratio` ile saha/genel güç seviyelerinin birlikte kalması dış sezonlarda ek sinyal taşıyor; yalnızca ham gol seviyelerinin (`H4c`) çıkarılması kazanç sağladı. **Reddedildi.** |
| **1X2** | **P2a / P2b: Gerçekleşen Gol Formundan (`goals_for/against`) Penaltı Gollerinin Silinmesi** | Pooled LL `0.9757 -> 0.9760`, Holdout LL `1.0261 -> 1.0268` | Penaltı pozisyonu beklentisi (`npxG`, `npBC`) arındırıldığında gerçek skor formunun (`sdiff_goals`) olduğu gibi korunması bitiricilik sinyalini tamamlıyor; gollerden penaltıyı silmek bilgi kaybettiriyor. **Reddedildi.** |
| **1X2** | **E1–E5: Elo ve Sezon Averaj (`gdpg`) Güncellemelerinde Penaltı Gol İskontosu** | `V3` üzerinde Pooled LL `0.9747 -> 0.9748–0.9749`, Brier `0.5798 -> 0.5799` | Elo güncellemelerinde resmi maç sonucunun ve gol farkının değiştirilmesi ek dış sezon kazancı sağlamadı. **Reddedildi.** |

| Model | Denenen Çözüm | Test Sonucu | Alınan Ders & Karar |
| :--- | :--- | :---: | :--- |
| **1X2** | **Lag'li xG Özellikleri** | Holdout kazancı yok | Zamanlama sızıntısı ve veri eksikliği. **Kaldırıldı.** |
| **1X2** | **İki Aşamalı Beraberlik Modeli** | LL 1.026 $\to$ **1.0536**, Brier 0.6378 | Beraberlik ayrımını çözmedi. **Reddedildi.** |
| **1X2** | **9 Draw-Propensity Özelliği** | Dış sezon LL 0.9834 $\to$ **0.9875** | Gürültüyü artırdı; kapıyı geçemedi. **Reddedildi.** |
| **1X2** | **1X2 Dixon-Coles Ensemble** | Dış sezonda $\Delta = +0.0044$ ($p=0.1864$) | Lojistik model tek başına daha üstün. **Reddedildi.** |
| **1X2** | **H1a: OOF Kat Boyutu Ölçekli `C_fold` + Standart Kalibratör (`reg=0.01`)** | Dış sezon Pooled LL `0.9789 -> 0.9824` (`2023/24`: `0.9411`) | `C_fold` ölçeklendiğinde dahi serbest sınıf bias'ları (`reg=0.01`) ilk sezonda aşırı uyum üretti; `reg_bias=0.50` tek başına sorunu çözdü. **Reddedildi.** |
| **1X2** | **H2a / H2b: `LogReg` + `FeatureGoalModel (v1.6)` Skor Matrisi OOF Ensemble** | Sabit 70/30 harman dış sezonda `0.9753` verse de, ileri OOF ile ağırlık seçildiğinde (`H2a`) Pooled LL `0.9782`, Holdout LL `1.0285`, Holdout Acc `%48.03`, Draw ECE `%3.93`'e geriledi | Erken katlarda OOF harman ağırlığı seçimi gürültülü ve kalibrasyonu bozuyor; 1X2 modelinin bağımsız kalıp Gol matrisini hizalaması daha üstün. **Reddedildi.** |
| **1X2** | **H3a–H3d: Tempo $\times$ Güç Dengesi ve Analitik Poisson Beraberlik Özellikleri (`exp_match_xg_10`, `poisson_xg_draw_prob`, `low_tempo_x_balance`, `abs_sdiff_sot_r10`)** | Pooled LL `0.9760` (ham) $\to$ `0.9762–0.9777`, Holdout LL `1.0263 -> 1.0268–1.0278`, Draw ECE `%2.36 -> %3.80–%4.39` | Doğrusal multinomial lojistik regresyonda ek tempo/mutlak fark sütunları beraberlik ECE'sini ve `2025/26` dış sezon kaybını kötüleştirdi. **Reddedildi.** |
| **1X2** | **H4a / H4b: Güç Seviye Sütunlarının (`elo_home/away`, `ppg_home/away`) veya `log_mv_ratio`'nun Çıkarılması** | `H4a` Pooled LL `0.9760 -> 0.9786`; `H4c - log_mv_ratio` (`C3`) Pooled LL `0.9755 -> 0.9771` | L2 cezası altında hem `log_mv_ratio` hem `effective_log_mv_ratio` ile saha/genel güç seviyelerinin birlikte kalması dış sezonlarda ek sinyal taşıyor; yalnızca ham gol seviyelerinin (`H4c`) çıkarılması kazanç sağladı. **Reddedildi.** |
| **1X2** | **P2a / P2b: Gerçekleşen Gol Formundan (`goals_for/against`) Penaltı Gollerinin Silinmesi** | Pooled LL `0.9757 -> 0.9760`, Holdout LL `1.0261 -> 1.0268` | Penaltı pozisyonu beklentisi (`npxG`, `npBC`) arındırıldığında gerçek skor formunun (`sdiff_goals`) olduğu gibi korunması bitiricilik sinyalini tamamlıyor; gollerden penaltıyı silmek bilgi kaybettiriyor. **Reddedildi.** |
| **1X2** | **E1–E5: Elo ve Sezon Averaj (`gdpg`) Güncellemelerinde Penaltı Gol İskontosu** | `V3` üzerinde Pooled LL `0.9747 -> 0.9748–0.9749`, Brier `0.5798 -> 0.5799` | Elo güncellemelerinde resmi maç sonucunun ve gol farkının değiştirilmesi ek dış sezon kazancı sağlamadı. **Reddedildi.** |
