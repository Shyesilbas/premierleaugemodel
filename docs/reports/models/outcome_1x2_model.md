# 1X2 Maç Sonucu Modeli — Model Raporu

**Rapor tarihi:** 25 Ekim 2026 (`v1.3`)
**Artifact:** `models/production/outcome_models_v1.joblib` · **Kod:** `src/models/train_match_outcome.py`, `src/models/model_utils.py`, `src/features/build_features.py`, `src/processing/process_season_data.py`
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [Gol Model Raporu](goals_model.md) · **[Detaylı uçtan uca denetim (14 Ekim 2026)](../1x2_model_audit.md)**

> Bu içerik 17 Ekim 2026'da ana rapordan taşındı ve 25 Ekim 2026 (`v1.2 -> v1.3`) dış sezon deneyleriyle güncellendi. API'de ve Gol modelinin kalibrasyon/değerlendirme hattında 13x13 gol skor matrisi bu modelin 1X2 olasılıklarına hizalanır — bkz. [Gol Model Raporu §11.11](goals_model.md).

---

## Mimari ve Değerlendirme Sonuçları (`v1.3`)

> Değerler üretim artifact'ının (`models/production/outcome_models_v1.joblib`, 25 Ekim 2026) `metrics['model_1x2']` alanından alındı.

- **Mimari:** 71 özellik (`v1.2`'deki 69 özelliğe ek olarak: (1) geçmiş maçların `xg_for/against` ve `big_chances_for/against` serilerinden penaltı vuruşu kaynaklı şişkinliğin [`0.78 xG` ve `1.0 big chance` / penaltı] rakip Elo normalizasyonu öncesinde arındırılması [`npxG` ve `npBC`], (2) rakip Elo'suna göre düzeltilmiş ve erken sezon örneklem küçültmeli [`k=3.0`] rakip ceza sahasına giriş net üstünlük farkları `sdiff_pa_entries_e02` ve `sdiff_pa_entries_r10`) → `SimpleImputer(median, keep_empty_features=True)` → `StandardScaler` → `LogisticRegression(C=0.003, max_iter=5000)` → ayrıştırılmış L2 cezalı ileri OOF sıcaklık + sınıf kesişimi kalibrasyonu (`reg_temp=0.10`, `reg_bias=0.50`; `922` OOF maçı). Draw-propensity özellikleri (`draw_propensity_enabled: false`) ve Dixon-Coles ensemble (`1x2_ensemble_production.enabled: false`) dış sezon kapısını geçemediği için kapalıdır.
- **Seçim:** `logreg_C0.003`, geliştirme CV log-loss **`0.9709`** (`v1.2`: `0.9739`, `v1.1`: `0.9755`; 836 maç, `2022/23` sabit dışlama sonrası). Final üretim fit `1.215` oynanmış maç (`2026/27` kilitli sezon kalibrasyon ve model seçiminden hariç).

### 1. Üç Tam Dış Sezon Yürüyen Pencere (Walk-Forward) Sonuçları (`2023/24–2025/26`, `N = 1,140`)

Her dış sezon yalnızca kendinden önceki sezonlarla eğitilip kalibre edilerek tek seferde puanlanmıştır (`2023/24` sezonu tek öncül sezon olan `2022/23` ile `early_season_fallback=True` olarak raporlanır):

| Sezon | Maç (`N`) | Ham LL (`v1.3`) | Kalibre LL (`v1.3`) | Kalibre LL (`v1.2` / `v1.1`) | Sınıf-Prior LL | Bet365 Kapanış LL | İsabet (`v1.3` / `v1.2`) | Çok Sınıflı Brier | RPS (`v1.3` / Prior) | Draw AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`2023/24`** | 380 | 0.9282 | **0.9278** | 0.9278 / 0.9317 | 1.0563 | 0.9028 | **%61.32** / %60.26 | 0.5447 | **0.1879** / 0.2346 | 0.5545 |
| **`2024/25`** | 380 | 0.9760 | **0.9777** | 0.9792 / 0.9827 | 1.0834 | 0.9674 | **%55.26** / %54.47 | 0.5830 | **0.1985** / 0.2358 | 0.5118 |
| **`2025/26`** | 380 | 1.0180 | **1.0184** | 1.0201 / 1.0223 | 1.0852 | 1.0136 | **%48.68** / %48.16 | 0.6117 | **0.2076** / 0.2279 | 0.5672 |
| **Pooled (`N=1,140`)** | **1,140** | **0.9741** | **0.9746** | 0.9757 / 0.9789 | 1.0750 | 0.9613 (`N=1,134`) | **%55.09** / %54.30 | **0.5798** (`v1.1`: 0.5826) | **0.1980** (`v1.1`: 0.1994) | **0.5445** |

- **Toplam İlerleme (`v1.1 -> v1.3`, `N=1,140`):** Havuzlanmış 3 dış sezon Log-Loss `0.9789 -> 0.9757 -> 0.9746` ($\Delta = \mathbf{-0.0043}$), Çok Sınıflı Brier `0.5826 -> 0.5806 -> 0.5798`, RPS `0.1994 -> 0.1985 -> 0.1980`, İsabet `%54.12 -> %54.30 -> %55.09` (+11 ek doğru maç tahmini). Kilitli `2026/27` sezonundaki (`N=75` maç) denetim isabeti de `%49.3 -> %50.7`'ye yükselmiştir.
- **Gol Modeli (`v1.6`) Üzerindeki Hizalama Etkisi:** 1X2 modelindeki `v1.3` güncellemesiyle 1X2-hizalı Gol modelinin dış sezon Tam Skor NLL'si `2.9729 -> 2.9696 -> 2.9686`'ya, 2.5 Üst haftalık refit Log-Loss'u `0.6756 -> 0.6753`'e (`2025/26` dondurulmuş 2.5 Üst LL: `0.6892 -> 0.6882`) iyileşmiştir.

### 2. Ana Kronolojik Holdout (`N = 304` Maç, Eşit Başlama Saatleri Bölünmeden Son %20)

| Ölçüm | Model (`v1.3`) | Sınıf-Prior | Dixon-Coles (Kalibre / Ham) |
| :--- | :---: | :---: | :---: |
| **Log-loss** | **1.026** (`1.0256`, Ham: `1.0247`) | 1.092 | 1.0459 / 1.0477 |
| **Çok sınıflı Brier** | **0.617** (`0.6168`) | 0.661 | 0.6290 / 0.6291 |
| **RPS (Ranked Probability Score)** | **0.2076** (`v1.2`: `0.2080`, `v1.1`: `0.2083`) | 0.2288 | — |
| **İsabet (Accuracy)** | **%49.34** | %40.79 | %44.08 / %44.08 |

- Eşleştirilmiş bootstrap model–prior log-loss farkı: **`-0.0661`**, %95 CI **`[-0.1049, -0.0268]`**, `P(daha iyi) = %99.96`.

### 3. Beraberlik Ayrım Gücü (`Draw AUC = 0.5495` Holdout · `0.5445` 3 Dış Sezon)
- Holdout'ta gerçek beraberlik oranı `%27.96`; modelin ortalama beraberlik olasılığı `%24.66`.
- Model genel beraberlik oranını kalibre eder ancak tekil maçlarda beraberliği ayırt etme gücü doğrusal sınırlar içindedir (`Bet365` kapanış oranlarında dahi 3 dış sezon Draw AUC `0.5699`'dur).

---

## Deney Kayıtları: Kabul Edilen ve Reddedilen Deneyler (1X2)

### Kabul Edilen İyileştirmeler (`v1.2 -> v1.3`, 25 Ekim 2026)

| Kod | Denenen Çözüm | 3 Dış Sezon (`N=1,140`) Sonucu | Karar |
| :--- | :--- | :---: | :--- |
| **H4c** | **Çoklu Doğrusal 8 Ham Gol Seviye Özelliğinin Çıkarılması (`77 -> 69` özellik)** | Pooled LL `0.9789 -> 0.9781` (kalibreli) / `0.9760 -> 0.9750` (ham), Holdout LL `1.0261 -> 1.0258`, Holdout Acc `%49.67 -> %50.33` | `sdiff_goals_e02/r10`, `gdpg_diff`, `venue_goals_diff` ve `xg_for/against` varken ters işaretli katsayı üreten 8 ham gol sütunu çıkarıldı. **Üretimde (`v1.2`).** |
| **H1** | **Ayrıştırılmış L2 Cezalı OOF Kalibrasyonu (`reg_temp=0.10, reg_bias=0.50`)** | `H4c` ile birlikte Pooled LL `0.9789 -> 0.9757` ($\Delta = -0.0032$, %95 CI `[-0.0058, -0.0005]`, 3/3 dış sezon kazancı), Brier `0.5826 -> 0.5806`, RPS `0.1994 -> 0.1985`, Draw ECE `%2.64 -> %2.29` | Serbest sınıf bias'larının (`reg=0.01`) geçmiş sezon beraberlik oranına aşırı uyumu ve OOF örneklem boyutu keskinlik sapması önlendi. **Üretimde (`v1.2`).** |
| **H5** | **`evaluate_classification_season_holdouts` İlk Dış Sezon (`2023/24`) Fallback Raporlaması** | `model_1x2['season_holdouts']` artık 2 yerine 3 tam dış sezonu (`2023/24`, `2024/25`, `2025/26`) eksiksiz raporluyor | İlk dış sezonda `2022/23` dışlandığında oluşan boş eğitim kümesi `early_season_fallback=True` ile korundu. **Üretimde (`v1.2`).** |
| **P1c + P3b** | **Penaltı Arındırılmış `npxG` + `npBC` ve Ceza Sahası Giriş Üstünlüğü (`sdiff_pa_entries_e02/r10`, `69 -> 71` özellik)** | CV LL `0.9739 -> 0.9709`, Pooled LL `0.9757 -> 0.9746` (`24/25`: `0.9792 -> 0.9777`, `25/26`: `1.0201 -> 1.0184`), Holdout LL `1.0261 -> 1.0256`, Brier `0.5806 -> 0.5798`, RPS `0.1985 -> 0.1980`, İsabet `%54.30 -> %55.09`, Tam Skor NLL `2.9696 -> 2.9686` | Geçmiş maçlardaki penaltı vuruşlarının `xG` (`0.78`) ve `big_chance_created` (`1.0`) üzerindeki yapay şişkinliği temizlendi; akan oyun ceza sahası baskısını ölçen `sdiff_pa_entries_e02/r10` (`k=3.0` Bayesçi erken-sezon küçültmesiyle) eklendi. **Üretimde (`v1.3`).** |

### Reddedilen Deneyler (`v1.1` – `v1.3`)

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
