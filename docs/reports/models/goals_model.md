# Gol Modeli (Bağımsız Poisson + Dixon-Coles Skor Matrisi) — Model Raporu

**Rapor tarihi:** 19 Ekim 2026 (`v1.4`)
**Artifact:** `models/production/goals_models_v1.joblib` · **Kod:** `src/models/goals_model.py`, `src/models/dixon_coles.py`, `src/models/train_goals.py`, `src/models/evaluate_goal_models.py`
**Dokümantasyon:** [Ana Rapor](../premier_league_models_comprehensive_report.md) · [Metodolojik Anayasa (Bölüm 8)](../premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage) · [1X2 Model Raporu](outcome_1x2_model.md) · [API Entegrasyonu](../../model_api_integration.md)

> **Bölüm numaraları:** Bu içerik 17 Ekim 2026'da ana rapordan taşındı. "Bölüm 3" ve "Bölüm 11.x" numaraları, AI_CONTEXT ve diğer belgelerdeki atıflar bozulmasın diye korunmuştur. **Güncel değerler: [11.11](#1111-gol-modeli--güncel-değerler-v14-19-ekim-2026)** · **İş akışı: [11.12](#1112-gol-modeli-iş-akışı-workflow)**

---
## BÖLÜM 3: Amiral Gemisi Gol Modeli (Bivariate Poisson + Dixon-Coles)

Gol modelimiz bağımsız sınıflandırıcılar yerine tek bir **$13 \times 13$ İki Değişkenli Skor Matrisi ($M_{ij}$)** üzerinden çalışır:

```
                            [GOL MODELİ 13x13 MATRİSİ]
                                        │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
[2.5 Üst/Alt]     [1.5 & 3.5 Üst]   [KG Var/Yok]   [Takım Baremleri]  [Skor Olasılığı]
  LL: 0.6774         Monotonik       %56.6 Eşik      0.5, 1.5, 2.5      0-0'dan 12-12'ye
```

### 3.1. Hibrit Formülasyon & Parametre Doğrulaması:
$$\lambda_{\text{Final}} = \lambda_{\text{Dixon-Coles}}^{0.25} \times \lambda_{\text{Feature-Poisson}}^{0.75}$$
> **İsim düzeltmesi:** Kod (`src/models/goals_model.py`) gerçek bir *Bivariate Poisson* (ortak kovaryans terimi $\lambda_3$) değildir. Ev ve deplasman golleri için **iki bağımsız `PoissonRegressor`** + yalnızca dört düşük skor hücresine uygulanan **Dixon-Coles $\tau$ düzeltmesi** kullanılır. Doğru ad: *"Bağımsız Poisson + Dixon-Coles skor matrisi"*.
- **Feature-Poisson:** 58 taktiksel özellik (ev ve deplasman regresyonu aynı 58 özelliği kullanır), L2 regülarizasyonu (`alpha = 10.0`; `docs/reports/model_benchmarks.md` hâlâ `20.0` yazıyor), Poisson Deviance kaybı.
  - 🔄 **Güncel (19 Ekim 2026):** 58 özellik (`full`), α=3, $w_{dc}=0.0$; ayarlar iç içe ileri katlarla ve en düşük skor NLL'ine göre seçilir. Bu bölümdeki diğer rakamlar denetim öncesi tarihsel değerlerdir — güncel değerler **Bölüm 11.11**'de.
- **Dixon-Coles Parametresi ($\rho = -0.0910$):**
  - Bootstrap 1.000 standart hatası $\text{SE} = \pm 0.0408$, %95 Güven Aralığı $[-0.1500, -0.0062]$.
  - **Matematiksel Değişmezlik:** $\rho$ değeri $[-0.20, +0.10]$ aralığında ne seçilirse seçilsin 2.5 Üst Log-Loss'u tam olarak `0.67743` kalır ($\Delta = 0.000000$). Çünkü Dixon-Coles düzeltmesi $\{(0,0), (1,0), (0,1), (1,1)\}$ hücrelerini yeniden dağıtır; bu hücrelerin tamamı 2 gol ve altındadır (Under 2.5). Ancak $\rho = -0.0610$ ortak harmanı BTTS ve doğru skor NLL'sini (2.4549) minimize eder.
  - ⚠️ **Denetim notu:** Değişmezlik iddiası matematiksel olarak doğrudur ($\tau$ düzeltmesi bu dört hücrede toplam kütleyi korur). Ancak $\rho$ ileri katlarda kararsızdır (DC: `+0.072`, `-0.003`, `-0.005`, `-0.085`); bootstrap CI'nin alt sınırı ($-0.150$) `RHO_GRID`/optimizer sınırına yapışmıştır, yani gerçek belirsizlik raporlanandan büyüktür. Üretimdeki $\rho=-0.061$, iki bileşenin *kendi* $\lambda$'larına göre bulunmuş $\rho$'larının ortalamasıdır; harmanlanmış $\lambda$ üzerinde yeniden kestirilmez.
- **Harman Ağırlığı Taraması ($w_{\text{dc}}$):** Grid search global optimumu $w_{\text{dc}} = 0.20$ verir ($LL = 0.67737$). Üretimdeki $w_{\text{dc}} = 0.25$ ($LL = 0.67743$) ile fark yalnızca $\Delta LL = +0.000056$'dır ve ROC-AUC üretim ağırlığında daha yüksektir (0.5366 vs 0.5355).
  - ⚠️ **Denetim notu:** Bu tarama kilitli 2026/27 sezonunu içeren 1.200 maçlık havuzda ve raporlanan holdout ile **aynı** sezonlarda yapılmıştır ([ana rapor Bölüm 8](../premier_league_models_comprehensive_report.md) madde 1 ve 5 ihlali). Bkz. Bölüm 11.1.

### 3.2. Holdout Performansı & Uç Risk (Tail Risk) Analizi:
> ⚠️ Aşağıdaki tablo kilitli sezonu içeren 1.200 maçlık havuzdan ve sabit genişlikli dilimlerden üretilmiştir; tahminlerin %68'i %50–%60 aralığına düştüğü için sistematik sapmayı gizler. Kilitli sezon hariç, eşit sayılı desil tablosu için bkz. **Bölüm 11.2**.

Model olasılıkları $\%41.09$ ile $\%74.55$ arasındadır; model aşırı güvenden (>%85) kaçınır.

| Olasılık Dilimi | Maç Sayısı | Dilim Payı | Model Ort. Tahmini | Gerçekleşme Oranı | Log-Loss | Brier | Kalibrasyon Yorumu |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **< %45 (Aşırı Alt)** | 8 | %0.7 | %43.70 | %75.00 | 0.7682 | 0.2873 | Küçük örneklem gürültüsü ($N=8$). |
| **%45 - %50 (Hafif Alt)** | 117 | %9.8 | %48.22 | %55.56 | 0.6992 | 0.2530 | Lig genelinde gol patlaması sapması. |
| **%50 - %55 (Dengeli)** | 345 | %28.7 | %52.99 | %53.62 | 0.6932 | 0.2500 | Kusursuz kalibrasyon ($\Delta = +0.63\%$). |
| **%55 - %60 (Hafif Üst)** | 469 | %39.1 | %57.34 | %59.91 | 0.6756 | 0.2413 | Yüksek kararlılık ($\Delta = +2.58\%$). |
| **%60 - %65 (Belirgin Üst)**| 188 | %15.7 | %62.00 | %61.17 | 0.6660 | 0.2366 | Kusursuz kalibrasyon ($\Delta = -0.83\%$). |
| **%65 - %70 (Yüksek Üst)** | 56 | %4.7 | %66.79 | %69.64 | 0.6147 | 0.2118 | Mükemmel ayrım, Log-loss 0.614'e indi. |
| **> %70 (Aşırı Üst)** | 17 | %1.4 | %72.47 | %76.47 | **0.5470** | **0.1804** | Zirve güvenilirlik, Log-loss 0.547. |


---

## Reddedilen Deneyler (Gol)

| Model | Denenen Çözüm | Test Sonucu | Alınan Ders & Karar |
| :--- | :--- | :---: | :--- |
| **Gol** | **İzotonik Kalibrasyon** | In-sample 0.6712 $\to$ **OOF 0.7107** | Basamak fonksiyonunda aşırı uyum. ❌ **Reddedildi.** |
| **Gol** | **XGBoost Residual Learner** | LL `0.6890 - 0.6904` (Üretim: 0.6774) | Poisson L2 düzgünlüğünü bozdu, gürültüyü böldü. ❌ **Reddedildi.** |
| **Gol** | **Sliding Window (500 Maç)** | LL `0.6801` (Üretim: 0.6774) | Takım başına 25 maça düşerek veri açlığı yarattı. ❌ **Reddedildi.** |
| **Gol** | **$\lambda$-Taban Shrinkage** | Train optimumu $\alpha = 0.0000$ | Önceki 0.40 holdout snooping'di. ❌ **Reddedildi.** |
| **Gol** | **Segment 10 Kör Noktası** | Ham $p=0.1687$, Bonferroni $p=1.0000$ | 12 alt grupta düzeltmesiz test sonucu çıkan Type I Error. ❌ **Gürültü.** |
| **Gol** | **O/U Sıcaklık Kalibrasyonu** (17.10.2026) | Karışık KFold'da kazanç; ileri katlarda O2.5 `0.6777 → 0.6799` | Kazanç zaman sızıntısıydı. ❌ **Reddedildi.** |
| **Gol** | **COM-Poisson Dağılım Parametresi** ($\nu$ = 1.15/1.3, 17.10.2026) | İç içe: Δ −0.0040 (temel −0.0044), ECE %6.8 (temel %4.6) | Toplam-gol şekli sorunu aslında sezon seviyesi kaymasıydı. ❌ **Reddedildi.** |
| **Gol** | **Özellik Modeline Zaman Ağırlığı** (yarı ömür 180/365 gün, 17.10.2026) | İç içe ızgarada hiç seçilmedi; haftalık yeniden eğitimde −0.0004 | Gürültü düzeyi. ❌ **Reddedildi.** |
| **Gol** | **Kapanış Oranlarını Özellik Yapmak** (17.10.2026) | Denenmedi | Piyasayı kopyalar, bağımsız görüş üretmez; oranlar yalnızca **kıyas** olarak kalır. ❌ **İlke gereği reddedildi.** |
| **Gol** | **Dixon-Coles Ridge Araması** (ridge 1/3/10/30, iç içe seçim, 19.10.2026) | Skor NLL `3.0003 → 3.0005`; tek başına DC: ridge 1 `3.0469`, ridge 30 `3.0314` (blend `3.0003`) | Sıkı ridge DC'yi iyileştiriyor ama blend'in yerini tutmuyor; arama maliyeti 4x, kazanç yok. ❌ **Reddedildi.**, kod kaldırıldı. |
| **Gol** | **Kadro Tabanlı Hücum Özellikleri** (ilk 11 şut hacmi: olağan XI'dan sapma, mutlak güç, kilit şutör eksikliği; 2 varyant, 19.10.2026) | Skor NLL `3.0003 → 2.9970` (Δ −0.0033, CI [−0.0051, −0.0016]); 2.5 Üst Δ −0.0005 CI [−0.0015, +0.0004]; KG Δ 0.0000; sabit Poisson'a karşı 2.5 Üst −0.0028 CI [−0.0101, +0.0044], KG +0.0011 CI [−0.0055, +0.0077] | Yalnızca skor matrisinde küçük kazanç; toplam gol pazarlarında etki yok. ❌ **Reddedildi.** Kod repoya alınmadı. |
| **Gol** | **DC Ağırlığı 0.25/0.5** (blend ızgarası, 19.10.2026) | İç içe: skor NLL `3.0003 → 2.9786` (Δ −0.0217, CI [−0.0328, −0.0111]) ağırlık 0'a daraltılınca | İç katlar her sezonda w=0 seçti; DC yalnızca `rho`'ya katkı veriyor. ❌ **Izgaradan kaldırıldı** (`dc_weights=[0.0]`). |
| **Gol** | **Ek özellik grupları** (dinlenme günü; hakem gol/faul/kart eğilimi; teknik direktör değişikliğinden bu yana gün; ilk 11'de eksik düzenli oyuncu + XI savunma oranı; iç içe, 19.10.2026) | Hiçbir grup 2.5 Üst'ü iyileştirmedi: Δ +0.0001…+0.0005, hepsi birlikte **+0.0015 [+0.0002, +0.0027] (kötüleşme)**; KG Δ −0.0002…+0.0002; skor NLL en iyi −0.0018 [−0.0045, +0.0007] | Toplam gol için bu veride bilgi yok. Reddedildi. Kod repoya alınmadı. |
| **Gol** | **Yönlü (Asimetrik) Ev/Deplasman Özellik Kümeleri ve Ayrı $\alpha_{\text{home}}, \alpha_{\text{away}}$** (24.10.2026) | Havuzda skor NLL `2.9740 -> 2.9695` ve O2.5 LL `0.6768 -> 0.6746` ($\Delta = -0.0021$, CI $[-0.0073, +0.0030]$), ancak `2025/26` sezonunda prior'dan kötüleşti (`+0.0035`, dış sezon galibiyeti `3/3 -> 2/3`); iç içe seçim ızgarasına (`directional in {False, True}`) eklendiğinde iç katlar `3/3` sezonda `directional=False` seçti | Karşı tarafın hücum/savunma temposunu gizlemek son sezonda kalibrasyonu bozuyor ve iç kat seçimi tarafından tercih edilmiyor. Reddedildi. |
| **Gol** | **Maç Öncesi Kayan Lig Gol Rejimi Özelliği / Çarpımsal Rejim Ölçekleme (`H2a`, `H2b`)** (24.10.2026) | `H2a` (son 40 maç büzülmeli lig gol ortalaması özelliği): $\Delta\text{O2.5} = -0.0000$ ($[-0.0004, +0.0003]$), $\Delta\text{NLL} = +0.0001$; `H2b` (iç katta seçilen $\gamma$ ile çarpımsal $\lambda$ ölçekleme): $\Delta\text{O2.5} = +0.0010$ ($[-0.0026, +0.0046]$), ECE `%3.35 -> %4.56` | Eğitim katlarında sabit terim ve takım form ortalamalarıyla doğrusal bağımlı; çarpımsal ölçekleme sezon geçişlerinde aşırı tepki veriyor. Reddedildi. |
| **Gol** | **Toplam Gol ($\mu_{\text{total}}$) + Pay ($p_{\text{home}}$) Ayrıştırması (`H3a`)** (24.10.2026) | O2.5 $\Delta\text{Null} = -0.0060$ (CI üst sınırı `-0.0011`), ancak O2.5 $\Delta\text{Base} = -0.0003$ ($[-0.0037, +0.0030]$) gürültü içinde ve KG Log-Loss `+0.0019` (`0.6810 -> 0.6830`), ECE `%3.35 -> %4.17` kötüleşti | Yüksek regülarizasyonlu toplam gol modeli takım bazlı varyansı bastırarak KG (BTTS) ayrımını bozuyor. Reddedildi. |
| **Gol** | **Doğrusal Olmayan Çarpımsal/Minimum xG ve Şut Başına xG Türevleri (`min_exp_xg`, `prod_exp_xg`, `xg_per_sot`)** (24.10.2026) | `exp_match_xg_10` ve `exp_venue_match_xg` üzerine eklendiğinde `2025/26` sezonunu pozitife çevirdi (`+0.0002`, `2/3` sezon) ve ECE'yi `%3.80 -> %4.17` bozdu | Yalnızca mevcut `exp_match_xg_10` ve `exp_venue_match_xg` toplam xG temposu özellikleri anlamlı kazanç sağladı (`v1.6`'ya alındı); ek türevler çoklu doğrusallık ekledi. Reddedildi. |
| **Gol** | **L2 Cezalı İnce Izgara $\rho \in [-0.25, +0.25]$ (`H5b`)** (24.10.2026) | Tüm dış sezon metriklerinde $\Delta = 0.0000$ | Mevcut `RHO_GRID` (`[-0.15, +0.15]`) ile fark sıfır. Reddedildi. |

---

## BÖLÜM 11: Bağımsız Denetim (17 Ekim 2026) — Gol Modeli & API Bulguları

**Kapsam:** `src/models/goals_model.py`, `src/models/dixon_coles.py`, `src/models/train_goals.py`, `src/models/evaluate_goal_models.py`, `src/api/server.py` (`predict_match`), `data/processed/goal_model_outer_eval.json`, `models/production/goals_models_v1.joblib` ve `scratch/goal_model_comprehensive_metrics.json`.  
**Yöntem:** Üretim konfigürasyonu (`hl=365`, `alpha=10`, `w_dc=0.25`) genişleyen sezon bazlı ileri değerlendirme ile yeniden üretildi (her sezon yalnızca önceki sezonlarla eğitildi). 2026/27 kilitli sezonu **yalnızca raporlandı**, hiçbir seçim kararında kullanılmadı. Bootstrap: 2.000 eşleşmeli örnek, `seed=42`.

### 11.1. Gerçek Holdout Rakamları (Kilitli Sezon Hariç, N = 1.140)

| Model (O2.5) | Log-Loss | Δ Prior | %95 CI | ROC-AUC | Olasılık Aralığı |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Prior (eğitim Over oranı) | 0.6848 | — | — | 0.500 | 0.526 – 0.587 |
| Dixon-Coles (hl=365) tek başına | 0.6879 | **+0.0031** | [−0.0085, +0.0145] | 0.537 | 0.262 – 0.826 |
| Feature-Poisson α=10 tek başına | 0.6775 | −0.0072 | [−0.0132, −0.0013] | 0.525 | 0.436 – 0.788 |
| **Üretim: Blend (α=10, w_dc=0.25)** | **0.6773** | **−0.0075** | **[−0.0134, −0.0016]** | **0.535** | 0.411 – 0.745 |
| Blend (α=10, w_dc=0.50) | 0.6790 | −0.0058 | [−0.0131, +0.0013] | 0.539 | 0.367 – 0.740 |

**Sezon kırılımı (Δ Prior, negatif = iyi):**

| Sezon | N | Blend Δ | Feature α=10 Δ | Feature α=10 AUC | DC Δ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 2023/24 | 380 | −0.0098 | −0.0142 | 0.534 | +0.0171 |
| 2024/25 | 380 | −0.0089 | −0.0057 | 0.566 | −0.0089 |
| 2025/26 | 380 | −0.0038 | −0.0018 | **0.507** | +0.0013 |
| 2026/27 🔒 (canlı) | 60 | −0.0037 (CI [−0.0224, +0.0152]) | +0.0017 | 0.525 | −0.0137 |

**Yorum:**
- Model prior'u istatistiksel olarak anlamlı ama **çok küçük** bir farkla geçiyor (göreli ~%1.1). Raporlanan `0.6774` gerçek değere yakın (`0.6773`), ancak **"1.200 maç" havuzu kilitli sezonu içeriyordu** (`scratch/extract_all_goal_metrics.py` tüm oynanmış sezonları döngüye alıyor).
- **Hiperparametreler test setinde seçildi:** `alpha` (100 → 20 → 10) ve `w_dc` (0.20/0.25), raporlanan holdout ile aynı üç dış sezonda seçilmiştir; `model_benchmarks.md` ayrıca seçimi tek tek fikstürlere (Man City–Ipswich, Forest–Arsenal) bakarak gerekçelendiriyor. İç içe (nested) seçim yok → `0.6773` iyimser bir tahmindir. Tek temiz test 60 maçlık kilitli sezondur ve orada fark anlamlı değildir.
- **Sinyal sezondan sezona eriyor:** Feature modelin prior'a karşı kazancı −0.0142 → −0.0057 → −0.0018 → +0.0017. 2025/26'da feature modelinin O2.5 AUC'si **0.49–0.51** (tüm α değerlerinde) — yani ayrım gücü sıfır; blend'in o sezondaki AUC'si (0.536) neredeyse tamamen DC bileşeninden geliyor.
- **DC bileşeni O2.5'te prior'dan kötü** (havuzda +0.0031); blend'e kattığı değer hacim değil, takım gücü bilgisinden geliyor.

### 11.2. Kalibrasyon: Sistematik "Alt" Sapması

Kilitli sezon hariç, eşit sayılı 10 desil (her biri 114 maç), üretim blend'i:

| Desil | Ort. Tahmin | Gerçekleşen | Fark |
| :---: | :---: | :---: | :---: |
| 1 | %47.8 | %57.0 | **−9.2** |
| 2 | %51.2 | %62.3 | **−11.1** |
| 3 | %53.2 | %48.3 | +4.9 |
| 4 | %54.6 | %52.6 | +2.0 |
| 5 | %55.8 | %57.9 | −2.1 |
| 6 | %57.0 | %63.2 | −6.2 |
| 7 | %58.1 | %59.7 | −1.5 |
| 8 | %59.6 | %57.9 | +1.7 |
| 9 | %61.7 | %57.0 | +4.7 |
| 10 | %66.7 | %71.9 | −5.2 |

- **Ortalama tahmin %56.6, gerçekleşen %58.8** → model Over'ı sistematik olarak ~2.2 puan düşük veriyor.
- **Desil ECE = %4.9** (resmi `goal_model_outer_eval.json`: %5.4). Önceki rapordaki **%2.17**, sabit genişlikli dilimlerle ve kilitli sezon dahil hesaplanmıştı; tahminler dar bir aralıkta toplandığı için bu yöntem sapmayı gizler. Gürültü tabanı (114 maçlık dilimde beklenen |hata| ≈ %3.7) dikkate alındığında sapma gerçektir.
- **Kanıt atılıyor:** `train_goals.py` her pazar için OOF kalibrasyon kazancını hesaplıyor (O2.5: `0.6773 → 0.6754`, O1.5: `0.4756 → 0.4726`, O3.5: `0.6537 → 0.6515`, BTTS: `0.6822 → 0.6805`) ve artifact'e `"calibration_applied": true` yazıyor; ama hemen ardından `calibrators[key] = None` ile kalibratörü atıyor. **Artifact meta verisi gerçeği yansıtmıyor.** (Not: bu OOF değerlendirmesi zaman sıralı veride karıştırılmış `KFold` kullanıyor; kazanç küçük ölçüde iyimser olabilir — ileri katlarla doğrulanmalı.)
  - ✅ **Doğrulandı (Bölüm 11.8):** İleri katlarla yapılan değerlendirmede O2.5 ve O3.5 kalibrasyonu **kazanç sağlamıyor** (O2.5: `0.6777 → 0.6799`, O3.5: `0.6481 → 0.6517`). Karışık KFold'daki kazanç zaman sızıntısından kaynaklanıyordu. Kalibrasyon yalnızca O1.5 (`0.4721 → 0.4707`) ve BTTS (`0.6831 → 0.6822`, T=1.24 → model BTTS'de aşırı emin) için anlamlı. Desil tablosundaki Alt sapması sabit bir kaymayla düzeltilemiyor: sapma sezona göre yön değiştiriyor.

### 11.3. Kök Neden: Poisson Dağılım Şekli ve Toplam Gol Sinyali Eksikliği

**a) Toplam gol underdispersed (varyans/ortalama = 0.887 < 1).** Bağımsız Poisson matrisi uçlara fazla kütle veriyor:

| Toplam Gol | Model | Gerçek |
| :---: | :---: | :---: |
| 0 | %5.3 | %4.7 |
| 1 | %15.5 | %13.2 |
| 2 | %22.6 | %23.3 |
| 3 | %22.2 | %23.3 |
| 4 | %16.4 | %18.4 |
| 5 | %9.8 | %10.4 |
| 6+ | %8.2 | %6.7 |

0–1 gol olasılığı +2.9 puan fazla (özellikle 1-0 hücresi: %8.5 vs %6.4), 3–4 gol −3.1 puan eksik → **Over 2.5'in sistematik olarak düşük çıkmasının ana mekanizması budur.** $\rho$ bunu düzeltemez (yalnızca ≤1 gollü hücreler arasında kütle taşır).

**b) Model "kim atar"ı biliyor, "kaç gol"u bilmiyor:**

| Metrik | Değer |
| :--- | :---: |
| corr(λ_ev, ev golü) | 0.346 |
| corr(λ_dep, dep golü) | 0.305 |
| corr(λ_ev − λ_dep, gol farkı) | **0.442** |
| corr(λ_ev + λ_dep, toplam gol) | **0.065** |
| λ_toplam ortalama / std | 2.960 / **0.238** |

Toplam gol beklentisinin maçtan maça standart sapması yalnızca 0.24 goldür; bu yüzden O2.5 olasılıkları dar bir banda sıkışır ve AUC 0.53–0.54'te kalır. Sınıflandırma metrikleri bunu doğrular: O2.5 doğruluğu %57.2 ≈ "her zaman Üst" taban çizgisi, O1.5 recall %100, O3.5 recall %2.3 — **bu pazarlarda doğruluk/precision/F1 bilgi taşımaz**, yalnızca log-loss/Brier/kalibrasyon raporlanmalıdır.

**c) Aşırı regülarizasyon + çoklu doğrusallık:** α=10 ile standartlaştırılmış katsayıların en büyüğü **0.019** (1 SD değişim → λ'da ~%1.9), 58 katsayının mutlak toplamı ~0.40–0.44. 58 özellik büyük ölçüde aynı bilgiyi tekrar ediyor (aynı istatistiğin `roll_10` + `ewma_02` versiyonları; `elo`, `elo_venue`, `ppg`, `gdpg`). Ev ve deplasman regresyonları aynı 58 özelliği kullandığı için 116 katsayı ~1.140–1.520 maçtan öğreniliyor. Daha düşük α erken sezonlarda daha iyi (α=1 havuzda 0.6745) ama 2025/26'da prior'dan kötüleşiyor → sorun α'nın tek başına ayarı değil, **sinyalin kendisinin zayıf ve kararsız olması.**

### 11.4. API (`src/api/server.py`) Bulguları

| # | Bulgu | Kanıt | Etki |
| :---: | :--- | :--- | :--- |
| A1 | **1X2 ile skor matrisi tutarsız.** `predict_match` 1X2'yi lojistik `outcome_models_v1`'den, O/U, BTTS, takım baremleri ve beklenen golleri gol matrisinden üretiyor. "Tek tutarlı mimari" iddiası API'de geçerli değil. | Sıradaki 10 fikstürde ortalama \|ΔEv\| = **5.6 puan**, \|ΔBeraberlik\| = **4.9 puan**. Forest–Arsenal: API ev galibiyeti **%12.3**, matris **%26.6**. Brentford–Liverpool: API beraberlik %36.7, matris %25.9. | Kullanıcı aynı ekranda birbiriyle çelişen 1X2 ve skor olasılıkları görüyor. |
| A2 | **BTTS etiketi yanıltıcı.** `btts_prediction = "KG Var" if p >= base_rate` (~%56.6). | Fulham–Hull %56.3, Man City–Ipswich %56.4 → **"KG Yok"**, oysa model KG Var'a >%50 veriyor. | Etiket aslında "ortalamanın üstü/altı" anlamına geliyor. |
| A3 | Uç nokta `GET`, dokümanda `POST` yazıyordu. | `@app.get("/api/predict")` | Düzeltildi (Bölüm 9). |
| A4 | ✅ **Eğitim/sunum çarpıklığı (training-serving skew) yok.** | 10 yaklaşan fikstürde `build_prediction_row` çıktısı parquet satırlarıyla 58/58 özellikte birebir aynı; λ değerleri aynı. | Olumlu. |
| A5 | O/U monotonluk kıskacı (`min`) zararsız ama gereksiz: kalibratör olmadığı için değerler zaten aynı matristen monotondur. Kalibratör açılırsa kıskaç gerçek iş görecektir. | — | Bilgi. |

### 11.5. Kod & Süreç Hijyeni

1. **Konfigürasyon üç yerde:** `train_goals.CHOSEN` (α=10, w=0.25, hl=365), `evaluate_goal_models._goal_matrices` içinde sabit kodlanmış `10.0` / `0.25` / `365.0`, ve `BlendedGoalModel` varsayılanları (**α=100, w_dc=0.5**). `train_goals` kapıyı yalnızca `kind="blend_dc_feat"` adıyla okur; `CHOSEN` değişirse eski değerlendirmenin kapısı yine "geçti" der.
2. **DC yakınsama kontrolü tutarsız:** `BlendedGoalModel.fit` yakınsamazsa hata fırlatır, `evaluate_goal_models` DC'yi `fit_ok_` kontrol etmeden kullanır.
3. **Dokümantasyon sürüklenmesi:** `model_benchmarks.md` α=20 diyor (kod: 10); `AI_CONTEXT.md` ve `docs/model_api_integration.md` "Bivariate" diyor ve ECE %2.17 veriyor. Raporun üç kopyası var (`docs/reports/`, `reports/`, `docs/report → reports` sembolik bağlantısı); tek kaynak seçilmeli.
4. **Testler bu denetimde çalıştırılamadı:** ortamda `pytest` kurulu değil.

### 11.6. Önceliklendirilmiş Aksiyon Listesi

| Öncelik | Aksiyon | Beklenen Etki | Efor |
| :---: | :--- | :--- | :---: |
| ✅ **P0** | `train_goals.py`'de hesaplanan kalibratörü atmak yerine **ileri (zaman sıralı) katlarla doğrulayıp** O1.5/O2.5/O3.5/BTTS için devreye al; meta veriyi gerçeğe uydur. | **Yapıldı** — yalnızca O1.5 ve BTTS'de kazanç var (Bölüm 11.8) | Küçük |
| ✅ **P0** | API'de 1X2 için **tek kaynak**: ya 1X2'yi matristen türet ya da iki kaynağı ayrı etiketle göster. | **Yapıldı** — matris lojistik 1X2'ye hizalanıyor (Bölüm 11.8) | Küçük |
| ✅ **P0** | BTTS etiketini %50 eşiğine bağla veya "Ortalamanın Üstü/Altı" olarak yeniden adlandır. | **Yapıldı** (%50 eşiği) | Çok küçük |
| ✅ **P0** | α ve w_dc'yi **iç içe** seç (yalnızca eğitim sezonları içindeki ileri katlarda), dış sezonları yalnızca raporlama için kullan; konfigürasyonu tek yerden oku. | **Yapıldı** — dürüst kazanç anlamlı değil (Bölüm 11.8) | Orta |
| ✅ **P1 (yeni)** | Seçim kararsız (α sezona göre 1↔30 arasında sıçrıyor): ızgarayı daralt veya α'yı 1-SE kuralıyla seç; asıl çözüm özellik sadeleştirme. | **Yapıldı** — 1-SE kuralı; α artık 30/30/10 (Bölüm 11.9) | Küçük |
| ✅ **P1** | Özellik sadeleştirme (58 → ~15–20, `roll`/`ewma` çiftlerinden biri, tek güç göstergesi); ev/deplasman için ilgili tarafın özellikleri. | **Yapıldı** — 11 özellik; doğruluk değişmedi, model sadeleşti (Bölüm 11.9) | Orta |
| **P1** | Underdispersion için toplam-gol dağılım düzeltmesi dene (kalibrasyon katmanı veya underdispersion'a izin veren sayım dağılımı) — kapı: ileri katlarda O2.5 ve O3.5 LL birlikte iyileşmeli. | Alt sapmasının kök nedenine çözüm | Orta |
| **P1** | Kapanış oranlarını **referans/özellik** olarak kullan: büro AUC 0.596 > model 0.584; toplam-gol bilgisinin en güçlü kaynağı piyasa. | Toplam gol sinyalinin artması | Orta |
| **P2** | Doğruluk/precision/recall/F1'i gol pazarı raporlarından kaldır; desil-ECE + reliability tablosunu standart yap. | Yanıltıcı metriklerin kalkması | Çok küçük |
| **P2** | Doküman kopyalarını tekilleştir, `model_benchmarks.md` / `AI_CONTEXT.md`'yi bu bölümle senkronla. | — | Küçük |

### 11.7. Denetim Kararı

Gol modeli **kullanılabilir ama abartılmıştır**: prior'u küçük ve anlamlı bir farkla geçer (ΔLL −0.0075), takım güç farkını iyi yakalar (gol farkı korelasyonu 0.44), ancak toplam gol hacmini neredeyse hiç ayırt edemez (korelasyon 0.065), Over'ı sistematik olarak ~2 puan düşük verir ve özellik sinyali son sezonda sıfıra yaklaşmıştır. Raporlanan performans rakamları, kilitli sezonu içeren ve hiperparametrelerin seçildiği havuzdan geldiği için iyimserdir. Bu haliyle **bahis edge'i iddiası için temel oluşturmaz**; [ana rapor Bölüm 6](../premier_league_models_comprehensive_report.md)'daki "edge yok" sonucu bu denetimle tutarlıdır.

### 11.8. Uygulanan Düzeltmeler ve Sonuçları (17 Ekim 2026)

**Kod değişiklikleri:**
1. `src/api/server.py` — `btts_prediction` artık `p ≥ 0.5` ile belirleniyor (önceden lig ortalamasıyla). Frontend bu alanı kullanmıyor; yalnızca API yanıtı etkilenir.
2. `src/models/train_goals.py` — sabit `CHOSEN` kaldırıldı; tek arama uzayı `BLEND_GRID` (α ∈ {1, 3, 10, 30}, w_dc ∈ {0, 0.25, 0.5}, hl=365). Yeni `select_blend_config()` α ve w_dc'yi yalnızca verilen verinin ileri katlarında O2.5 log-loss'a göre seçiyor. Kalibrasyon değerlendirmesi karışık `KFold` yerine `forward_time_splits` kullanıyor; kalibratör yalnızca ileri katlarda kazanç varsa kaydediliyor ve meta veri gerçeği yansıtıyor.
3. `src/models/evaluate_goal_models.py` — sabit kodlanmış `10.0 / 0.25` kaldırıldı; `blend_dc_feat` her dış sezonda **yalnızca o sezondan önceki verilerle** `select_blend_config()` çalıştırılarak kuruluyor (iç içe seçim). Kapı kaydına `selection_grid` ve sezon bazlı `selected_configs` yazılıyor; `train_goals` farklı bir ızgarayla üretilmiş kapıyı reddediyor.
4. `tests/test_goal_selection.py` — seçim ve ileri kalibrasyon için iki test.
5. Eski üretim modeli yedeklendi: `models/production/goals_models_v1.backup_2026-10-17.joblib`.

**Dürüst (iç içe) holdout sonucu, 1.140 maç:**

| Ölçüm | Önceki (sabit α=10, w=0.25, test setinde seçilmiş) | Yeni (iç içe seçim) |
| :--- | :---: | :---: |
| O2.5 ortalama sezon LL | 0.6778 | **0.6798** |
| Δ Prior (havuz) | −0.0070 | **−0.0049** |
| %95 CI | [−0.0134, −0.0016] | **[−0.0126, +0.0027]** |
| P(model > prior) | ~%99 | **%89.6** |
| Desil ECE | %5.4 | %5.5 |
| Seçilen ayar (2023/24 · 2024/25 · 2025/26) | sabit | α=30,w=0.5 · α=1,w=0.5 · α=1,w=0.25 |

**Yorum:** Önceki rakamın ~0.0021'lik kısmı seçim iyimserliğiydi. Prosedür düzeyinde gol modeli prior'u **istatistiksel olarak anlamlı biçimde geçmiyor**; kapı ise geçiyor çünkü kapı kuralları (ortalama Δ < −0.003, ≥2 negatif sezon) güven aralığı istemiyor. Seçimin sezondan sezona sıçraması, sinyalin zayıf ve kararsız olduğunu teyit ediyor (Bölüm 11.3).

**Yeni üretim modeli** (tüm kilitsiz sezonların ileri katlarında seçildi): α=3, w_dc=0.5, hl=365. Kalibratör: O1.5 ✅, BTTS ✅, O2.5 ❌, O3.5 ❌. 2026/27 kilitli sezonu bu karar için **kullanılmadı**.

**1X2 tek kaynak kararı için veri (aynı sezon holdout'ları, her sezon önceki sezonlarla eğitildi):**

| Sezon | Lojistik 1X2 (`outcome_models_v1`) | Gol matrisi 1X2 (`blend_dc_feat`, önceki ayar) | Prior |
| :---: | :---: | :---: | :---: |
| 2023/24 | **0.9327** | 0.9483 | 1.0563 |
| 2024/25 | **0.9786** (kalibre: 0.9834) | 0.9898 | 1.0860 |
| 2025/26 | **1.0197** (kalibre: 1.0226) | 1.0279 | 1.0845 |

Lojistik model 1X2'de her sezon 0.006–0.016 daha iyi. Not: eğitim satırları birebir aynı değil (lojistik model 2022/23 etiketlerini eğitimden dışlıyor), bu yüzden karşılaştırma yaklaşıktır.

**Karar: skor matrisi lojistik 1X2'ye hizalanır.** Yeni `align_to_outcome_probs()` (`src/models/dixon_coles.py`), matrisin ev galibiyeti / beraberlik / deplasman bölgelerini lojistik 1X2 olasılıklarına göre ölçekler; her bölgenin içindeki skor dağılımı korunur. Beklenen goller artık hizalanmış matristen hesaplanır (`expected_goals()`).

Hizalama testi (aynı 1.140 maç, her sezon önceki sezonlarla eğitildi, iç içe seçimli blend + o sezonda yeniden eğitilmiş lojistik 1X2):

| Pazar | Ham matris LL | Hizalanmış LL | Δ | %95 CI |
| :--- | :---: | :---: | :---: | :---: |
| 1X2 | 0.9956 | **0.9798** | **−0.0157** | [−0.0283, −0.0027] |
| Over 2.5 | 0.6798 | 0.6786 | −0.0012 | [−0.0031, +0.0004] |
| Over 1.5 | 0.4744 | 0.4744 | +0.0000 | [−0.0008, +0.0008] |
| Over 3.5 | 0.6574 | 0.6570 | −0.0003 | [−0.0012, +0.0005] |
| BTTS | 0.6834 | 0.6848 | +0.0014 | [+0.0000, +0.0029] |

Hizalama 1X2'yi anlamlı biçimde iyileştirir, Üst/Alt pazarlarını bozmaz. BTTS'te sınırda küçük bir kayıp var (+0.0014); tüm pazarların aynı matristen gelmesi için kabul edildi.

**Ek düzeltmeler (aynı tur):**
- `server.py` BTTS kalibratörünü hiç uygulamıyordu (önceden tüm kalibratörler `None` olduğu için görünmüyordu); artık uyguluyor.
- `src/analytics/model_audit.py` API ile aynı yolu izliyor: hizalanmış matris, kayıtlı O2.5/BTTS kalibratörleri, BTTS isabet eşiği %50 (önceden lig ortalaması). Önbelleğe alınmış denetim özetleri (`data/processed/model_audit_summary*.json`) `force_recalc=True` ile yeniden hesaplanana kadar eski mantıkla kalır.
- Doğrulama: sıradaki 10 fikstürde API'nin 1X2'si ile matrisin ima ettiği 1X2 arasındaki en büyük fark **0.06 puan** (yalnızca yuvarlama). Önceden ortalama fark 5.6 puandı.
- Testler: `tests/test_goal_matrix.py`'ye hizalama testi eklendi.

### 11.9. Özellik Sadeleştirme ve 1-SE Seçim Kuralı (17 Ekim 2026)

**Ne yapıldı:**
- `COMPACT_GOAL_FEATURES` (`src/models/train_goals.py`): veriye bakılmadan, alan bilgisiyle tanımlanan **11 özellik** — `elo_home/away`; her iki takım için `xg_for/against_ewma_02` ve `shots_ontarget_for/against_ewma_02`; `exp_match_shots_5`. Tamamı mevcut 58'in alt kümesidir (yeni sızıntı riski yok). `effective_log_mv_ratio` ([ana rapor Bölüm 10](../premier_league_models_comprehensive_report.md) madde 2) bu sette yoktur.
- `BLEND_GRID` artık özellik setini de arıyor (`compact`, `full`). Seçim **1-SE kuralı** ile yapılıyor: en iyi ayarla eşleşmeli bir standart hata içinde kalan ayarlar arasından en basiti (önce `compact`, sonra daha güçlü L2), sonra en düşük kayıp.

**İç katlar (tüm kilitsiz sezonlar, 1.216 OOF maç, O2.5 LL):**

| Set | En iyi ayar | Havuz LL | En yeni kat |
| :--- | :--- | :---: | :---: |
| full (58) | α=3, w=0.5 | 0.6768 | 0.6880 |
| compact (11) | α=3, w=0.5 | 0.6769 | **0.6853** |

İki set istatistiksel olarak berabere; 1-SE kuralı olmadan seçim gürültüyle `full`'a gidiyordu (tüm dış sezonlarda).

**Dürüst (iç içe) dış holdout, 1.140 maç:**

| Prosedür | Ort. LL | Δ Prior | %95 CI | Desil ECE | Seçilenler (23/24 · 24/25 · 25/26) |
| :--- | :---: | :---: | :---: | :---: | :--- |
| En düşük kayıp (Bölüm 11.8) | 0.6798 | −0.0049 | [−0.0126, +0.0027] | %5.5 | full α30 · full α1 · full α1 |
| **1-SE kuralı (yeni)** | 0.6803 | −0.0044 | **[−0.0105, +0.0014]** | **%4.6** | compact α30 · full α30 · full α10 |

**Yorum:** Doğruluk farkı gürültü düzeyinde; kazanım doğrulukta değil, **sadelik ve kararlılıkta**: α artık 1↔30 arasında sıçramıyor, kalibrasyon hatası düştü, güven aralığı daraldı. Ancak model hâlâ prior'u istatistiksel olarak anlamlı biçimde geçmiyor ve 2023/24'te O2.5/O3.5'te prior'dan kötü. **58 özelliğin 11'e indirilmesi bilgi kaybettirmedi** → bu, 58 özelliğin büyük kısmının fazlalık olduğunu ve O2.5 için sınırlayıcı faktörün özellik sayısı değil, veride toplam gol sinyalinin zayıflığı olduğunu teyit eder (Bölüm 11.3).

> Not: 1-SE kuralı, iç kat sonuçları (seçim verisi) görüldükten sonra eklendi; dış sezonlar için hiçbir ayar seçilmedi. Yine de bu, aynı dış sezonlarda değerlendirilen ikinci prosedürdür; iki prosedür arasındaki fark zaten anlamsız olduğundan tercih sadelik gerekçesiyle yapılmıştır.

**Yeni üretim modeli** (Bölüm 11.8'dekinin yerine geçer): `compact` (11 özellik), α=30, w_dc=0.5, hl=365. İleri katlarda hiçbir pazarda kalibrasyon kazanç sağlamadığı için **kalibratör yok** (O1.5 `0.4720→0.4729`, O2.5 `0.6782→0.6835`, O3.5 `0.6497→0.6560`, BTTS `0.6827→0.6843`). Matris API'de lojistik 1X2'ye hizalanmaya devam eder. 2026/27 kilitli sezonu kullanılmadı.

**Sıradaki gerçekçi kazanç kaynağı:** özellik mühendisliği değil, **piyasa bilgisi** (kapanış O/U oranları; büro AUC 0.596) ve underdispersion'a uygun toplam-gol dağılımı (Bölüm 11.6, P1).

### 11.10. Eksiklerin Giderilmesi Denemeleri (17 Ekim 2026)

**İlke:** Kapanış oranlarını özellik olarak kullanmak modeli piyasanın kopyasına çevirir; oranlar yalnızca **kıyas** olarak kalır ([ana rapor Bölüm 6](../premier_league_models_comprehensive_report.md)). İyileştirmeler model içinden arandı ve hepsi aynı iç içe ızgara + 1-SE kuralıyla sınandı: yeni seçenek iç katlarda gerçekten kazanmazsa en basit model korunur.

| Deneme | Hedeflenen eksik | Sonuç (dış holdout, 1.140 maç) | Karar |
| :--- | :--- | :--- | :--- |
| **COM-Poisson dağılımı** ($\nu \in \{1.15, 1.3\}$, ortalama korunur, varyans daralır) | Toplam golün underdispersion'ı | İki sezonda seçildi; Δ prior −0.0040 (temel −0.0044), ECE %6.8 (temel %4.6), BTTS 2025/26 prior'dan kötü | ❌ Reddedildi, kod kaldırıldı |
| **Özellik modeline zaman ağırlığı** (yarı ömür 365 g) | Lig gol seviyesindeki kayma | Hiçbir dış sezonda seçilmedi | ❌ Reddedildi, kod kaldırıldı |
| **Haftalık yeniden eğitim** (ayar sezon başında sabit, parametreler her hafta öncesi yeniden fit) | Sezon içi seviye uyumu | Donuk modele göre **−0.0048, CI [−0.0093, −0.0005]** (anlamlı); haftalık güncellenen prior'a göre −0.0046, CI [−0.0108, +0.0015] | ✅ İş akışına ve değerlendirmeye eklendi |

**Teşhis — "Alt sapması"nın gerçek kaynağı sezon seviyesi kaymasıdır, dağılım şekli değil:**

| Dış sezon | Eğitim verisi gol/maç | Gerçekleşen gol/maç | Model O2.5 ort. | Gerçek O2.5 |
| :---: | :---: | :---: | :---: | :---: |
| 2023/24 | 2.85 | **3.28** | %52.2 | **%64.7** |
| 2024/25 | 3.07 | 2.93 | %58.3 | %56.6 |
| 2025/26 | 3.02 | 2.75 | %57.3 | %55.0 |

2023/24'teki gol patlamasını hiçbir maç öncesi model önceden göremez; ancak sezon içinde yeniden eğitilen model birkaç haftada uyum sağlar (2023/24: donuk `0.6794` → haftalık `0.6609`). Diğer iki sezonda haftalık yeniden eğitim nötr/hafif negatif (`0.6755 → 0.6779`, `0.6861 → 0.6878`). Underdispersion'ın havuzda görünmesi, farklı seviyelerdeki sezonların karışmasından kaynaklanıyordu; sezon içinde 0–1 gol oranı zaten doğru tahmin ediliyor (2025/26: %20.3'e karşı %21.1).

**Sonuç:** Haftalık yeniden eğitim, ligin gol seviyesine uyumu sağlayan tek iyileştirmedir; ancak aynı şekilde güncellenen bir taban oranın da yakaladığı bir kazançtır. Modelin taban orana karşı **ayırt edici** katkısı ~0.005 LL'de kalır ve anlamlı değildir.

### 11.11. Gol Modeli — Güncel Değerler (v1.6, 24 Ekim 2026)

> Sayılar `models/production/goals_models_v1.joblib` ve `data/processed/goal_model_outer_eval.json` dosyalarından alınmıştır. Değişikliklerin gerekçesi ve adım adım sonuçları: `GOAL_MODELS_ANALYSIS.md` (Ç1–Ç5, P1–P8) ve 24 Ekim 2026 `K1–K9` + toplam/saha xG temposu (`exp_match_xg_10`, `exp_venue_match_xg`) güncellemeleri.

**Ölçümler ne anlatıyor?**

| Ölçüm | Ne anlatıyor | Nasıl okunur |
| :--- | :--- | :--- |
| **Skor NLL** | Gerçekleşen skorun (örn. 2-1) modelin matrisinde aldığı olasılığın negatif logu; modelin *tüm skor dağılımını* ne kadar iyi bildiğini ölçer | Düşük iyi. Sabit lig ortalaması (`null`) 3.0959 |
| **Log-loss (LL)** | Tek bir pazarda (2.5 Üst, KG) olasılığın ne kadar isabetli olduğu; kesin tahmin yanlışsa ağır cezalanır | Düşük iyi. 0.693 = yazı-tura |
| **Δ prior** | Modelin LL'si eksi "hep tarihsel oranı söyle" LL'si | Negatif = prior'dan iyi |
| **Δ sabit Poisson (`null`)** | Modelin LL'si eksi "her maça aynı lig ortalaması gol" modelinin LL'si; modelin takım bilgisinin gerçekten işe yarayıp yaramadığını gösterir | Negatif = takım bilgisi katkı veriyor |
| **Δ piyasa** | Modelin LL'si eksi marjı çıkarılmış Bet365 olasılığının LL'si (yalnızca kıyas, özellik değil) | Pozitif = piyasa daha iyi bilgili |
| **%95 CI** | Eşleşmeli bootstrap güven aralığı; sıfırı içeriyorsa fark gürültüden ayırt edilemez | Sıfırı dışlıyorsa anlamlı |
| **ECE** | Tahmin edilen olasılıkla gerçekleşme oranı arasındaki ortalama sapma (desil) | Düşük iyi; modelin "%60" dediği maçların ne kadarının gerçekten gol attığını gösterir |

**Mimari & üretim ayarı** (1.595 maçla fit; 2026/27 kilitli sezonu seçimde kullanılmadı):

| Bileşen | Değer | Ne anlatıyor |
| :--- | :--- | :--- |
| Oranlar | $\lambda = \lambda_{Feat}$ ($w_{dc}=0$); `dc_weight=0` iken gereksiz DC fit atlanır | Golleri özellik modeli tahmin ediyor; ortak $\rho$ harmanlanmış $\lambda$ üzerinden kestirilir |
| Feature-Poisson | `full`, 60 özellik (`compact`: 13 özellik; `exp_match_xg_10` ve `exp_venue_match_xg` dahil), α=3, medyan imputasyon + standartlaştırma | Toplam ve saha bazlı beklenen xG temposu özellikleri (`exp_match_xg_10`, `exp_venue_match_xg`) skor NLL'yi anlamlı iyileştirdi ($\Delta = -0.0008$, CI $[-0.0015, -0.0002]$) |
| Skor matrisi | 13×13, bağımsız Poisson × Dixon-Coles $\tau$ ($\rho = -0.0300$), lojistik 1X2'ye (`v1.2`, 69 özellik) hizalı | Eğitim kalibrasyonu, dış sezon değerlendirmesi ve API aynı 1X2-hizalı matrisi kullanır |
| Kalibratör | `over_1.5`, `over_2.5`, `over_3.5` ve `btts` **tamamı uygulanıyor** (ileri OOF LL: O1.5 `0.4729->0.4707`, O2.5 `0.6774->0.6758`, O3.5 `0.6469->0.6460`, BTTS `0.6830->0.6817`) | 1X2 `v1.2` hizalamasıyla dört pazarın tamamı ileri katlarda kazanç sağladı; `skill_gate` dinamik türetilir |
| Seçim ölçütü | İleri katlarda skor NLL, en düşük kayıp kazanır (1-SE kuralı kaldırıldı) | Eskiden 2.5 Üst LL'si seçiyordu ve ayarları ayırt edemiyordu |
| Izgara | `feature_sets [compact, full]`, `feature_alphas [0.1…30]`, `dc_weights [0.0]` | DC ağırlığı iç içe testte her sezon 0 seçildi |
| API | Matris lojistik 1X2'ye hizalanır; `btts_prediction` kapı geçilmediği için `null` | KG'de ayırt edicilik kanıtlanmadığından etiket yok, yalnızca yüzde |

**Dış holdout (1.140 maç, iç içe seçim, her sezon yalnızca önceki sezonlarla) — model / prior LL:**

| Pazar | 2023/24 | 2024/25 | 2025/26 |
| :--- | :---: | :---: | :---: |
| Over 2.5 | 0.6645 / 0.6790 | 0.6763 / 0.6854 | 0.6892 / 0.6900 |
| Over 1.5 | 0.4192 / 0.4379 | 0.4834 / 0.4817 | 0.5122 / 0.5159 |
| Over 3.5 | 0.6970 / 0.7158 | 0.6423 / 0.6451 | 0.6052 / 0.6118 |
| BTTS | 0.6709 / 0.6863 | 0.6840 / 0.6824 | 0.6851 / 0.6859 |

**Özet:**

| Ölçüm | Değer | Ne anlatıyor |
| :--- | :--- | :--- |
| Skor NLL | **2.9686** (v1.6-1X2v1.2: 2.9696, v1.5: 2.9737, v1.4: 2.9786; sabit lig ortalaması 3.0959) | 1X2 `v1.3` hizalaması (`npxG` + `npBC` + `sdiff_pa_entries`) ve toplam/saha xG temposu (`v1.6`) ile skor dağılımı anlamlı iyileşti ($\Delta\text{Null} = -0.1271$, CI $[-0.1570, -0.0986]$) |
| O2.5 ortalama LL (donuk) | **0.6767** (v1.4: 0.6774) | Δ prior −0.0080, CI [−0.0156, −0.00001], P(daha iyi) %97.5, 3/3 negatif sezon (25/26 LL 0.6892 -> 0.6882) → prior'dan **anlamlı** iyi |
| O2.5 − sabit Poisson | −0.0058, CI [−0.0132, +0.0018] | P(daha iyi) %93.6; %95 CI sıfırı kesiyor |
| O2.5 − piyasa | +0.0078, CI [+0.0001, +0.0156] | Piyasa (Bet365 kapanış) anlamlı biçimde önde |
| KG LL | **0.6804** (v1.5: 0.6808) | Sabit Poisson'a karşı −0.0014; KG kapısı kapalı |
| KG − piyasa | +0.0048, CI [−0.0007, +0.0102] | Piyasa ile fark dar seviyede korunuyor, piyasadan anlamlı kötü değil |
| O2.5 haftalık yeniden eğitim | **0.6753** (v1.6-1X2v1.2: 0.6756, v1.4: 0.6760) | Donuğa göre −0.0018 [−0.0041, +0.0007]; haftalık prior'a göre −0.0048 [−0.0113, +0.0017] |
| O2.5 desil ECE | **%4.24** (v1.4: %5.07) | 1X2-hizalı değerlendirme ile kalibrasyon iyileşti |
| Kapı (`passed`) / `ci_excludes_zero` / `ci_vs_null_excludes_zero` | Geçti / Geçti / Geçmedi | Prior'u 3/3 sezonda ve anlamlı geçiyor; sabit Poisson'a karşı %93.6 olasılıkla önde |
| Sezon bazlı seçilen ayarlar | 23/24: full α10 w0 · 24/25: full α3 w0 · 25/26: full α3 w0 | İç katlar her sezon DC'siz seçti |
| 1X2 (API) | Lojistik model; kalibrasyon, değerlendirme ve API aynı hizalanmış matrisi kullanır | — |

**Bilinen sınırlar:** (1) toplam gol hacmi hâlâ öngörülemiyor; piyasa 2.5 Üst'te anlamlı biçimde önde; (2) kadro tabanlı özellikler (ilk 11 şut hacmi) denendi, 2.5 Üst ve KG'ye katkı vermedi (Reddedilen Deneyler); (3) ECE hafif kötüleşti; (4) 2.5 Üst kapısı yalnızca ortalama farkın negatif olmasını ve prior'a karşı sonucu istiyor, sabit Poisson'a karşı anlamlılık zorunlu değil; (5) DC tamamen kaldırılmadı, $\rho$ ortak.

### 11.12. Gol Modeli İş Akışı (Workflow)

```
                 data/processed/features_matches_all.parquet  (shift(1) maç öncesi özellikler)
                                        │
        ┌───────────────────────────────┴───────────────────────────────┐
        ▼                                                               ▼
 1) python -m src.models.evaluate_goal_models                    (kilitli 2026/27 hariç)
    • Her dış sezon S için: S'den önceki sezonlarda select_blend_config()
      (BLEND_GRID × ileri katlar, en düşük skor NLL) → seçilen blend S'de skorlanır
    • Sabit-ayar adayları (dc_*, feat_alpha*) ve logreg_o25 kıyas için
    • Haftalık yeniden eğitim bloğu: evaluate_in_season_refit()
    • Çıktı: data/processed/goal_model_outer_eval.json
        (outer_season_results, o25_candidate_gates[selection_grid,
         selected_configs, ci_excludes_zero], o25_in_season_refit)
        │
        ▼
 2) python -m src.models.train_goals
    • Kapı kontrolü: blend_dc_feat.passed == True ve selection_grid == BLEND_GRID
      (aksi halde eğitim durur: "rerun evaluate_goal_models")
    • Tüm kilitsiz sezonlarda select_blend_config() → üretim ayarı
    • İleri OOF + ileri kalibrasyon testi → kalibratör yalnızca kazanç varsa
    • Final fit: tüm oynanmış maçlar (kilitli sezon dahil, yalnızca parametre için)
    • Çıktı: models/production/goals_models_v1.joblib
        (model, chosen, selection_grid, calibrators, calibration_metrics, base_rates)
        │
        ▼
 3) API — GET /api/predict (src/api/server.py)
    • outcome_models_v1 → 1X2
    • goals_models_v1.predict_matrices → align_to_outcome_probs(1X2)
    • O1.5/2.5/3.5, KG, takım baremleri, beklenen goller aynı matristen
    • Model Denetimi (src/analytics/model_audit.py) aynı yolu izler
```

**Çalıştırma sıklığı:** Her oyun haftası (gameweek) bittikten sonra `python3 run_full_pipeline.py` (ETL → özellikler → değerlendirme → eğitim). Haftalık yeniden eğitim, ligin gol seviyesine uyumun tek kaynağıdır (Bölüm 11.10); pipeline haftalarca çalıştırılmazsa model donuk değerlendirmedeki gibi davranır.

**Değişiklik kuralları:**
1. Arama uzayı yalnızca `BLEND_GRID`'de değiştirilir; değişiklikten sonra önce değerlendirme, sonra eğitim çalıştırılır (sıra kodla zorlanır).
2. Yeni bir model seçeneği yalnızca iç içe dış holdout'ta mevcut prosedürü geçerse ızgarada kalır; aksi halde kodu kaldırılır ve bu rapordaki **Reddedilen Deneyler** tablosuna işlenir.
3. Dış sezon sonuçlarına bakarak tek bir ayar seçilmez; kilitli 2026/27 sezonu yalnızca raporlanır.
4. Kapanış oranları özellik olarak kullanılmaz; yalnızca kıyas ve paper-trading içindir.

**Testler:** `tests/test_goal_matrix.py` (matris, monotonluk, 1X2 hizalaması), `tests/test_goal_selection.py` (ızgara seçimi, ileri kalibrasyon). Not: ortamda `pytest` kurulu değil; testler doğrudan Python ile çalıştırıldı.
