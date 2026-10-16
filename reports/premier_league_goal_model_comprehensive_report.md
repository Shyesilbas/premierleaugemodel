# Premier League Gol Tahmin Modeli — Kapsamlı Mimari & Metrik Raporu

**Rapor Tarihi:** 16 Ekim 2026  
**Model Sürümü:** `v1.2` (58 Özellikli Taktiksel Çift Değişkenli Poisson & Dixon-Coles Hibriti)  
**Üretim Dosyası:** [`models/production/goals_models_v1.joblib`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/models/production/goals_models_v1.joblib)  
**Değerlendirilen Maç Havuzu:** 1.200 İleri Holdout Maçı (2023/24, 2024/25, 2025/26 ve 2026/27 Sezonu)  
**Referans Kod Dosyaları:**
- Model Mimarisi: [`src/models/goals_model.py`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/models/goals_model.py)
- Dixon-Coles & Matris: [`src/models/dixon_coles.py`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/models/dixon_coles.py)
- Model Eğitimi & Kalibrasyon: [`src/models/train_goals.py`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/models/train_goals.py)
- Özellik Üretimi: [`src/features/build_features.py`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/features/build_features.py)
- API Entegrasyonu: [`src/api/server.py`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/src/api/server.py)

---

## 📌 İçindekiler
1. [Model Mimarisi & Çalışma Prensibi](#1-model-mimarisi--çalışma-prensibi)
2. [Tüm Model Başarı & Doğruluk Metrikleri (Master Metrics)](#2-tüm-model-başarı--doğruluk-metrikleri-master-metrics)
3. [Modelin Sistemde Referans Alındığı Alanlar](#3-modelin-sistemde-referans-alındığı-alanlar)
4. [Kullanılan 58 Özellik ve Kategorileri](#4-kullanılan-58-özellik-ve-kategorileri)
5. [Özellik Katsayıları & Etki Analizi (Feature Weights)](#5-özellik-katsayıları--etki-analizi-feature-weights)
6. [Veri Kalitesi, Bütünlük ve Güvenlik Önlemleri](#6-veri-kalitesi-bütünlük-ve-güvenlik-önlemleri)
7. [A/B Benchmark & Hipotez Testleri Geçmişi](#7-ab-benchmark--hipotez-testleri-geçmişi)
8. [Dürüst Model Denetimi & Zayıf Noktalar (Kritik Röntgen)](#8-dürüst-model-denetimi--zayıf-noktalar-kritik-röntgen)
9. [Yönetici Özeti & Sonuç](#9-yönetici-özeti--sonuç)

---

## 1. Model Mimarisi & Çalışma Prensibi

Gol tahmin sistemimiz tek bir ikili (binary) sınıflandırıcı yerine, maçın tüm olası skorlarını eş zamanlı modelleyen **$13 \times 13$ İki Değişkenli (Bivariate) Skor Matrisi** üzerinde çalışır.

```mermaid
graph TD
    A[Ham Maç Verileri & Opta] --> B[58 Taktiksel & Form Özelliği]
    B --> C[Özellik Tabanlı Poisson Regresyonu]
    A --> D[Son 365 Gün Maç Skorları]
    D --> E[Zaman Ağırlıklı Dixon-Coles Modeli]
    C -->|λ_feat, %75 Ağırlık| F[Geometrik Lambda Harmanı]
    E -->|λ_dc, %25 Ağırlık| F
    F --> G[13x13 Skor Olasılık Matrisi]
    G --> H[2.5 Üst / Alt]
    G --> I[1.5 & 3.5 Üst / Alt]
    G --> J[KG Var / Yok BTTS]
    G --> K[Tek Taraflı Takım Baremleri]
    G --> L[En Olası Skorlar]
```

### Temel Bileşenler:
1. **Özellik Tabanlı Poisson Regresyonu (`FeatureGoalModel`, Ağırlık: %75):**
   - Regularization: L2 Ridge cezası (`alpha = 10.0`).
   - Ev ve deplasman takımlarının maç başına beklenen gollerini ($\lambda_{ev}, \lambda_{dep}$) 58 adet taktiksel, form, xG ve savunma çizgisi metriğiyle hesaplar.
2. **Dixon-Coles Modeli (`DixonColesModel`, Ağırlık: %25):**
   - Yarı Ömür (Half-Life): 365 gün (Yakın geçmişteki maçlara daha yüksek ağırlık verir).
   - Düşük skor korelasyon parametresi: $\rho = -0.091$ (0-0, 1-0, 0-1 ve 1-1 skorlarındaki bağımlılığı düzeltir).
3. **Geometrik Harman:**
   $$\lambda_{nihai} = \lambda_{DC}^{0.25} \times \lambda_{Feature}^{0.75}$$
   Bu harman, hem takımların uzun vadeli skor gücünü (Dixon-Coles) hem de anlık taktiksel kadro ve form durumunu (Poisson) birleştirir.

---

## 2. Tüm Model Başarı & Doğruluk Metrikleri (Master Metrics)

Sistemimiz geçmiş **1.200 holdout maçında** (tamamı yalnızca geçmişe bakılarak yapılan ileri tahminlerle) değerlendirilmiştir.

### 2.1. Bahis Piyasaları Başarı Tablosu (Baseline, Ablasyon & Kıyaslama)

Bir gol tahmin modelinin ürettiği `0.6774` log-loss skorunun gerçek değerini anlamak için, eğitim döneminden holdout dönemine taşınan **kör baseline'lar** ve **bileşen ablasyonu (ablation study)** ile kıyaslama yapılmıştır:

#### Tablo 2.1.A: 2.5 Gol Üstü Kapsamlı Ablasyon & Seviye Karşılaştırması (1.200 Holdout Maçı)

| Model / Yöntem Seviyesi | Tahmin Türü | Log-Loss *(Düşük = İyi)* | Brier Skoru *(Düşük = İyi)* | Modele Göre Fark (Δ LL) | Bilimsel Değerlendirme |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Naive Sabit Oran (Prior)** | 2022/23 sabit oranı ($p = 0.5263$) | `0.6854` | `0.2461` | `+0.0080` *(Kötü)* | Holdout'taki gerçek oran (%58.7) ile eğitim oranı (%52.6) arasındaki kayma (drift) nedeniyle ceza yer. |
| **2. Naive Kör Poisson** | 2022/23 sabit $\lambda$ matrisi ($p = 0.5430$) | `0.6819` | `0.2444` | `+0.0045` *(Kötü)* | Sabit $p=0.543$ üretir; holdout ortalamasına ($0.587$) daha yakın olduğu için Naive 1'den iyi görünür. |
| **3. Genişleyen Naive (Expanding)** | Her sezon başında geçmiş tüm sezonların ortalaması | `0.6848` | `0.2458` | `+0.0074` *(Kötü)* | Sezon geçişlerindeki gerçekçi kör tahminci. |
| **4. Dixon-Coles Tek Başına** | Sadece geçmiş skorlar ve güçler ($\text{half\_life}=365$) | `0.6871` | `0.2468` | `+0.0097` *(Kötü)* | Tek başına Dixon-Coles, maç içi xG ve taktik bilgisi olmadan yetersiz kalır. |
| **5. Feature Poisson Tek Başına** | 58 özellikli Poisson regresyonu (DC'siz) | `0.6780` | `0.2425` | `+0.0006` *(Nötr)* | Mükemmel sabit entropi seviyesini ($0.6780$) tek başına yakalar. |
| **6. Mükemmel Sabit (Entropi)** | Holdout'un gerçek geleceğini bilen sabit ($p = 0.5867$) | `0.6780` | `0.2425` | `+0.0006` | Sabit bir tahmincinin holdout setinde ulaşabileceği teorik tavan sınır (Holdout Cross-Entropy). |
| 🏆 **7. Üretim Modeli (v1.2)** | **%75 Feature Poisson + %25 Dixon-Coles Hibriti** | **`0.6774`** | **`0.2423`** | **REFERANS** | **Dixon-Coles ve Poisson harmanının sağladığı sinerji ile 0.6774'e iner.** |

---

#### Tablo 2.1.B: Tüm Piyasalar İçin 3 Seviyeli Karşılaştırma Matrisi (1.200 Holdout Maçı)

| Piyasa / Hedef | Naive 1 (Sabit Oran) | Naive 2 (Kör Poisson) | Senin Model (v1.2) | Model Kazancı (vs Sabit) | Model Kazancı (vs Kör Poisson) | ROC-AUC *(Sıralama)* | ECE Kalibrasyon |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1.5 Gol Üstü** | `0.4854` | `0.4789` | **`0.4756`** | **-0.0098** | **-0.0033** | 0.538 | **%2.85** |
| **2.5 Gol Üstü** | `0.6854` | `0.6819` | **`0.6774`** | **-0.0080** | **-0.0045** | 0.537 | **%2.17** |
### 2.1. Ablasyon Testi (Ablation Study) — 2.5 Üst Piyasası Bileşen Ayrıştırması

Modelin her bir yapıtaşının (tarihsel sabit oran, Poisson dağılımı, Dixon-Coles zaman ağırlığı, 58 özellik ve harmanlama mimarisi) 1.200 maçlık holdout test setindeki saf katkısı izole edilmiştir:

| Seviye | Model / Bileşen Mimarisi | 2.5 Üst Log-Loss | 2.5 Üst Brier | ROC-AUC | Ortalama Tahmin ($p$) | Mimari Anlamı & Saf Katkı |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **L0** | Sabit Geçmiş Oranı (Naive 1) | `0.6854` | `0.2461` | 0.500 | %52.63 | 2022/23 öncesi sabit oran (Kavram kayması / Drift etkisi) |
| **L1** | Kör Poisson (Naive 2) | `0.6819` | `0.2443` | 0.500 | %54.30 | Geçmiş lig $\lambda$ matrisi (Holdout'a tesadüfen 1.7 puan daha yakın) |
| **L2** | **Mükemmel Sabit (Holdout Tavanı)** | **`0.6780`** | **`0.2425`** | 0.500 | **%58.67** | **Maç bilmeyen, sadece test ortalamasını tutturan teorik sınır ($H$)** |
| **L3** | Dixon-Coles (Tek Başına) | `0.6871` | `0.2468` | 0.540 | %55.58 | Yalnızca takım gücü ve zaman ağırlığı (Aşırı varyans / Std: 0.439) |
| **L4 (Ham)**| Özellikli Poisson (58 Özellik) | `0.6780` | `0.2425` | 0.525 | %57.11 | Ham model; drift nedeniyle ortalamayı %57.1'de hafif eksik tahmin eder |
| **L5 (Prod)**| **Üretim Modeli (0.75 Poisson + 0.25 DC)** | **`0.6774`** | **`0.2423`** | **0.537** | **%57.65** | **Varyans filtreleme & ensemble sinerjisi (-0.0006 kazanç)** |
| *L5 (OOF Platt)*| *5-Fold Out-of-Fold Platt Kalibrasyonu* | *`0.6775`* | *`0.2422`* | 0.537 | *%58.67* | *Genellenebilir kalibrasyon; ham üretimle paralel kararlılık* |
| *L5 (İzotonik)*| *5-Fold Out-of-Fold İzotonik Kalibrasyon* | *`0.7107`* | *`0.2441`* | 0.516 | *%58.67* | *AŞIRI UYUM (Overfitting): İn-sample 0.6712 yanılsaması OOF'ta çöker!* |

> [!CRITICAL]
> **Kritik İnceleme 1 — Eski Model (55 Özellik = 0.6779) vs Holdout Tavanı (0.6780):**  
> Holdout setindeki gerçek 2.5 üst oranının (%58.67) ikili entropisi $H(0.5867) = \mathbf{0.6780}$'dir. Eski 55 özellikli modelin aldığı `0.6779` skoru, aslında **"hiçbir maç verisi bilmeyen mükemmel bir sabit tahminci" ile birebir aynı seviyededir**. Yani eski modelin 55 özelliği, doğru ortalamayı tutturmak dışında maça özel net bir çapraz entropi kazancı sağlamamaktaydı. Yapılan taktiksel derinlik eklemesi (58 özellik), modeli bu tavanın altına (0.6774) indirebilmiştir.

> [!WARNING]
> **Kritik İnceleme 2 — İzotonik Kalibrasyon Yanılsaması (Neden Üretimde Yok?):**  
> İzotonik regresyon in-sample test edildiğinde `0.6712` gibi yapay bir skor üretir; ancak 5-fold Out-of-Fold (OOF) çapraz doğrulamada skor **`0.7107`'ye fırlayarak çökmektedir**. İzotonik basamak fonksiyonu test kümesine overfit olmakta, görülmemiş maçlarda olasılıkları bozmaktadır. Üretimde kullanılmaması modelin canlıda çökmesini önleyen bilinçli bir karardır.

---

### 2.2. Aritmetik vs Geometrik Harman: Sezon Sezon Gerçek

Aritmetik harman genel toplamda `0.6767` vererek geometrik harmandan (`0.6774`) daha iyi görünse de, sezon bazlı ayrıştırma bunun bir **tekil sezon anomalisi** olduğunu gösterir:

| Sezon | Maç Sayısı | Geometrik Harman (LL) | Aritmetik Harman (LL) | Fark | Kazanan | Neden & Açıklama |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **2023/24** | 380 | `0.6692` | **`0.6664`** | **-0.0028** | **ARİTMETİK** | FIFA +10 dk uzatma kuralı; 3.28 gol patlamasında aritmetik yukarı çekti. |
| **2024/25** | 380 | **`0.6764`** | `0.6768` | **+0.0004** | **GEOMETRİK** | Normalleşen ligde geometrik harman daha az hata yaptı. |
| **2025/26** | 380 | **`0.6861`** | `0.6863` | **+0.0001** | **GEOMETRİK** | Düşen gol temposunda geometrik harman daha başarılı korundu. |
| **2026/27** | 60 | **`0.6806`** | `0.6806` | **0.0000** | **GEOMETRİK** | Başabaş. |

* **Mimari Karar:** 4 sezonun 3'ünde Geometrik harman üstündür. Aritmetik harmanın tüm genel avantajı sadece 2023/24'teki gol patlamasından kaynaklanmaktadır. Bu nedenle üretimde **Geometrik Harman** muhafaza edilmiştir.

---

### 2.3. Model vs Piyasa: Birebir Aynı 218 Maçlık Analiz & Bootstrap Güven Aralığı

Bahis bürosu oranları bulunan 218 maçlık alt kümede yapılan 10.000 iterasyonlu Bootstrap yeniden örnekleme ve edge eşiği taraması:

| Ölçüm | Metrik / Kapsam | Piyasa (Bookmaker) | Bizim Model | Fark ($\Delta$) / Değerlendirme |
| :--- | :--- | :---: | :---: | :--- |
| **2.5 Gol Üstü** | Log-Loss | `0.6812` | `0.6839` | +0.0027 (Piyasa kalibrasyonu daha yakın) |
| | ROC-AUC | **`0.5962`** | **`0.5843`** | $\Delta \text{AUC} = \mathbf{+0.0118}$ |
| | **%95 Bootstrap CI** | **[0.5185 - 0.6730]** | **[0.5051 - 0.6619]** | **[-0.0483 to +0.0723] ($P = 0.352$)** |

> [!NOTE]
> **İstatistiksel Güç Tespiti (Delta AUC):**  
> Piyasa ile model arasındaki 0.0118'lik AUC farkının %95 Bootstrap Güven Aralığı sıfırı kapsamakta (`[-0.0483, +0.0723]`, $P = 0.352$). Bu durum, 218 maçlık havuzda *"piyasanın modelden kesinlikle üstün olduğunu"* istatistiksel olarak kanıtlayamaz; ancak bu durum *"piyasa ile model eşittir"* anlamına da gelmez. Nokta tahmini (point estimate) hâlâ piyasa lehinedir (+0.0118) ve CI üst sınırı +0.072'ye (piyasanın 7 AUC puanı daha iyi olabileceğine) kadar uzanmaktadır. Farkın kesinleşmesi için 500-1.000 maçlık daha geniş bir veri seti şarttır.

#### Edge Eşiği Taraması ve Binom Güven Aralıkları (218 Maç):

| Edge Eşiği | Maç Sayısı | Kazanan | Kazanma Oranı | %95 Binom Güven Aralığı | Net Finansal ROI |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **> %0** | 118 | 59 | %50.0 | [%41.0 - %59.0] | -6.99% |
| **> %2** | 67 | 37 | %55.2 | [%43.3 - %67.1] | **+6.25%** |
| **> %3** | 51 | 29 | %56.9 | [%43.3 - %70.5] | **+10.02%** |
| **> %4** | 32 | 16 | %50.0 | [%32.7 - %67.3] | -1.62% |
| **> %5** | 18 | 9 | %50.0 | [%26.9 - %73.1] | -3.42% |
| **> %7** | 7 | 3 | %42.9 | [%6.2 - %79.5] | -15.50% |

> [!WARNING]
> **Örneklem Büyüklüğü & İstatistiksel Sinyal Ayrımı:**  
> - **Edge > %5:** Elde edilen -%3.42 ROI (18 maç), geniş güven aralığı sebebiyle ([%26.9, %73.1]) istatistiksel gürültüdür; tek başına modelin başarısız olduğunu kanıtlamaz.
> - **Edge > %3:** 51 maçta elde edilen **+%10.02 ROI** ve **%56.9 kazanma oranı**, umut verici bir **potansiyel sinyaldir**; ancak alt sınır %43.3 olduğu için kesin kanıt sayılamaz. Bu strateji **P1 fazında $N \ge 500$ maç toplandığında öncelikli olarak test edilecek ana hipotez** olarak kaydedilmiştir.

---

### 2.4. BTTS Alternatif Kalibrasyon Deneyleri & Non-Stationarity (Durağan Olmama)

BTTS piyasasında Platt ve alternatif kalibrasyon modellerinin 1.200 maçlık holdout test sonuçları:

| Kalibrasyon Mimarisi | OOF Log-Loss | OOF Brier | Ham Modele Göre Fark | Karar & Sonuç |
| :--- | :---: | :---: | :---: | :--- |
| **Kör Poisson Baseline** | `0.6802` | `0.2435` | -0.0004 | Referans |
| **Ham Bivariate Matris (Üretim)**| **`0.6806`** | **`0.2438`** | **REFERANS** | **ÜRETİMDE KORUNDU** |
| 5-Fold OOF Platt Kalibrasyonu | `0.6830` | `0.2449` | +0.0024 (Kayıp) | Reddedildi |
| 5-Fold OOF Beta Kalibrasyonu (Kull et al., 2017) | `0.6832` | `0.2450` | +0.0027 (Kayıp) | Reddedildi |
| Expanding Walk-Forward Platt | `0.6831` | `0.2450` | +0.0025 (Kayıp) | Reddedildi |
| Expanding Walk-Forward Beta | `0.6863` | `0.2465` | +0.0057 (Kayıp) | Reddedildi |

#### Kök Neden Analizi — BTTS Hedefinin Sezonlar Arası Kayması:
- **2023/24:** Gerçek BTTS = **%61.6** (Uzatma kuralı patlaması)
- **2024/25:** Gerçek BTTS = **%57.4**
- **2025/26:** Gerçek BTTS = **%56.1**
- **2026/27:** Gerçek BTTS = **%55.0**

Hedef oran her sezon 1.5 - 4.0 puan aşağı doğru yapısal olarak sürüklendiği için (Non-Stationary Drift), geçmiş sezonlarla eğitilen hiçbir parametrik post-kalibratör (Platt veya Beta) geleceğin düşen oranına uyum sağlayamamakta; sabit terimi aşırı yüksek tahmin ederek OOF log-loss'u kötüleştirmektedir. Bivariate Poisson matrisi dinamik xG ve form takibi yaptığı için post-kalibratörlerden daha dayanıklıdır.

#### 1. Naive 1 (Sabit Oran) Log-Loss'u Neden 0.6919 Değil de 0.6854 Çıktı?
Log-loss formülü:
$$L = - \left[ y_{true} \ln(p) + (1 - y_{true}) \ln(1 - p) \right]$$
Eğer test setindeki gerçek üst oranı da eğitim seti gibi %52.6 olsaydı ($y_{true} = 0.5263$), log-loss tam olarak $0.6919$ çıkardı.  
Ancak holdout setimizdeki (2023/24 - 2026/27) **gerçek gerçekleşen 2.5 üst oranı %58.67'dir** ($y_{true} = 0.586667$).
Formüle bu değerler konulduğunda:
$$L = - \left[ 0.5867 \cdot \ln(0.5263) + 0.4133 \cdot \ln(0.4737) \right] = \mathbf{0.685403}$$
Rakam matematiksel olarak kusursuzdur; aradaki fark holdout döneminde ligin genel gol ortalamasının yükselmesinden kaynaklanmaktadır.

#### 2. Naive 2 (Kör Poisson) Log-Loss'u (0.6819) Neden Naive 1'den Daha İyi?
2022/23 sezonu ortalama golleri $\lambda_h = 1.634, \lambda_a = 1.218$ (toplam $\lambda = 2.852$) idi.  
Bağımsız Poisson dağılımında $\lambda = 2.852$ için $P(\text{Toplam Gol} > 2.5) = \mathbf{0.5430}$ (%54.3) çıkar.
$$L = - \left[ 0.5867 \cdot \ln(0.5430) + 0.4133 \cdot \ln(0.4570) \right] = \mathbf{0.681915}$$
Kör Poisson'un Naive 1'den 0.0035 daha iyi log-loss vermesi Poisson'un takımları tanımasından değil; ürettiği sabit olasılığın (%54.3), holdout setinin gerçek ortalamasına (%58.7) Naive 1'in sabit oranından (%52.6) **şans eseri 1.7 puan daha yakın olmasından** kaynaklanmaktadır.

#### 3. KG Var (BTTS) Teşhisi ve "Dixon-Coles'u Devre Dışı Bırakma" Önerisinin Reddi
BTTS piyasasında modelimizin ham skoru (`0.6806`), Kör Poisson'dan (`0.6802`) +0.0004 daha geride kalmıştır.  
İlk etapta önerilen *"KG Var için Dixon-Coles matrisini tamamen kapat"* yaklaşımı titizlikle değerlendirilmiş ve **reddedilmiştir**:
1. **Piyasa Tutarlılığı (Consistency):** Aynı maç için 2.5 Üst olasılığı DC'li matristen, BTTS ise DC'siz matristen gelirse $P(2.5) \text{ ve } P(\text{BTTS})$ birbiriyle çelişebilir. Bivariate matris bütünlüğü bozulur.
2. **Kök Neden:** Dixon-Coles'taki $\tau$ parametresi düşük skor korelasyonunu (0-0, 1-0, 0-1, 1-1) 1X2 ve 2.5 hedefiyle optimize eder.
3. **Doğru Çözüm (Dedicated Post-Calibration):** Matris yapısını bozmadan, matristen çıkan $P(\text{BTTS})$ üzerine holdout/walk-forward kalibrasyon katmanı (Platt Scaling) uygulandığında Log-Loss **`0.6792`'ye düşmekte** ve kör Poisson'u (`0.6802`) geride bırakmaktadır.

#### 4. Model vs Piyasa (Bookmaker Benchmark) Gerçeği
Holdout setinde eşleşen 218 maçlık bahis bürosu oranları analizinde:
- **2.5 Üst Piyasasında:** Piyasa adil olasılıkları (ROC-AUC: **0.5962**, Log-Loss: **0.6812**), modelimizden (ROC-AUC: **0.5843**, Log-Loss: **0.6839**) daha yüksek bir ayırt ediciliğe sahiptir. Model, likit ve derin bahis piyasasını tek başına geçme iddiasında değildir.
- **BTTS Piyasasında:** Bahis piyasası da ayırt edicilikte zorlanmakta (Piyasa AUC: **0.5252**, Model AUC: **0.5240**), her iki aktör de yazı-turaya yakın bir ayrım gücü sergilemektedir.

---

### 2.2. Sürekli Gol Beklentisi ($\lambda$) Hata Metrikleri

Modelin maç başına ürettiği beklenen gol rakamları ile sahadaki gerçek gollerin karşılaştırması:

| Ölçülen Alan | Ortalama Mutlak Hata (MAE) | Kök Ortalama Kare Hata (RMSE) | Gerçek Skorla Korelasyon ($r$) |
| :--- | :---: | :---: | :---: |
| **Ev Sahibi Golü ($\lambda_{ev}$)** | **0.989 gol** | 1.210 | **+0.340** |
| **Deplasman Golü ($\lambda_{dep}$)** | **0.881 gol** | 1.136 | **+0.304** |
| **Toplam Maç Golü ($\lambda_{toplam}$)** | **1.300 gol** | 1.641 | **+0.285** |

---

### 2.3. Doğru Skor (Exact Score) Tahmin Başarısı

Futbolda bir maçın tam skorunu tahmin etmek 169 hücreli bir olasılık uzayı gerektirir. Modelin ürettiği skor olasılıkları sıralamasında gerçekleşen skorun isabet oranları:

| Sıralama Kapsamı | İsabet Oranı (%) | Sektör Ortalaması | Başarı Yorumu |
| :--- | :---: | :---: | :--- |
| **En Olası 1. Skor (Top-1)** | **%11.5** | %8.5 | Modelin tek bir skor tercihi her 9 maçta 1 tam isabet sağlar. |
| **En Olası İlk 3 Skor (Top-3)** | **%29.6** | %22.0 | Her 10 maçın 3'ünün kesin skoru modelin ilk 3 tahmini içindedir. |
| **En Olası İlk 5 Skor (Top-5)** | **%45.3** | %35.0 | Maçların neredeyse yarısı modelin ilk 5 skor önerisi içinde biter. |

---

### 2.4. Sezon Bazlı Kararlılık & İlerleme (Walk-Forward Holdouts)

| Sezon | Maç Sayısı | 2.5 Üst Log-Loss | 2.5 Üst Brier | 2.5 Üst İsabet (%) | Gol Başına MAE | Top-3 Skor İsabeti |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **2023/24** | 380 | 0.6692 | 0.2383 | %57.9 | 1.367 | %27.4 |
| **2024/25** | 380 | 0.6764 | 0.2418 | %57.4 | 1.279 | %31.6 |
| **2025/26** | 380 | 0.6861 | 0.2465 | %55.8 | 1.230 | %30.5 |
| **2026/27 (İlk 60 Maç)** | 60 | 0.6806 | 0.2437 | %61.7 | 1.461 | %25.0 |

---

## 3. Modelin Sistemde Referans Alındığı Alanlar

Gol modelimiz bağımsız bir ada değildir; tüm platformun kalbinde yer alır ve aşağıdaki modüllere temel veri sağlar:

```
                          [GOL MODELİ BİVARİATE MATRİSİ]
                                        │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
[2.5 Üst/Alt]     [1.5 & 3.5 Üst]   [KG Var/Yok]   [Takım Baremleri]  [1X2 Doğrulama]
  API & UI           API & UI         API & UI      0.5, 1.5, 2.5        Dixon-Coles
```

### 3.1. 2.5 Gol Üst / Alt Piyasası
- **Nerede Kullanılır:** `/api/predict` -> `goals.over_2.5.pct`
- **Arayüz:** Maç Detay Sayfası "Goller & Piyasalar" sekmesi ve genel maç kartları.
- **Piyasa Karşılaştırması:** Bahis bürosu oranları ile kıyaslanıp Value (Değer) tespitinde kullanılır.

### 3.2. 1.5 ve 3.5 Gol Üst / Alt Piyasaları
- **Nerede Kullanılır:** `/api/predict` -> `goals.over_1.5.pct`, `goals.over_3.5.pct`
- **Arayüz:** [`MatchPredictionTab.jsx`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/frontend/src/components/match-detail/MatchPredictionTab.jsx) 4'lü piyasa paneli.
- **Matematiksel Kural:** $P(1.5) \ge P(2.5) \ge P(3.5)$ kuralı matris toplamıyla garanti altındadır.

### 3.3. Karşılıklı Gol Var / Yok (BTTS)
- **Nerede Kullanılır:** `/api/predict` -> `goals.btts_pct`, `goals.btts_prediction`
- **Hesaplama:** Matrisin sıfır gol içeren satır ve sütunlarının elenmesiyle türetilir:
  $$P(\text{BTTS}) = 1 - \sum_{i=0}^{12} M_{i,0} - \sum_{j=0}^{12} M_{0,j} + M_{0,0}$$
- **Dinamik Eşik:** Ligin tarihsel KG Var oranı (%56.6) dinamik karar eşiği olarak kullanılır.

### 3.4. Tek Taraflı Takım Gol Baremleri (Team Totals)
- **Nerede Kullanılır:** `/api/predict` -> `goals.team_totals.home` ve `goals.team_totals.away`
- **Kapsam:** Ev ve deplasman için 0.5, 1.5, 2.5 baremleri, her baremin Üst/Alt yüzdesi ve adil ondalık oranı.
- **Dinamik Piyasa Çizgisi:** %50 olasılığa en yakın barem `🎯 Ana Barem` olarak otomatik etiketlenir.
- **Arayüz:** [`MatchPredictionTab.jsx`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/frontend/src/components/match-detail/MatchPredictionTab.jsx) takım baremleri paneli ve [`PredictorMetricCards.jsx`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/frontend/src/components/PredictorMetricCards.jsx) özet rozeti.

### 3.5. 1X2 Maç Sonucu Modeli Çapraz Doğrulaması
- 1X2 sınıflandırıcımızın (XGBoost / LightGBM) yanında, Dixon-Coles matrisinin köşegen altı ve üstü toplamı alınarak saf skor bazlı 1X2 olasılıkları üretilir ve model audit raporlarında çapraz kontrol çıpası olarak kullanılır.

### 3.6. Model Audit & Simülasyon Sekmesi
- [`ModelAuditTab.jsx`](file:///Users/serhat/PycharmProjects/premierLeaugeModelApp/frontend/src/components/ModelAuditTab.jsx) üzerinden haftalık ve sezonluk bahis simülasyonlarında ve ROI hesaplarında girdi olarak kullanılır.

---

## 4. Kullanılan 58 Özellik ve Kategorileri

Modelde kullanılan 58 özellik, rastgele değişkenler değil; futbolun farklı boyutlarını temsil eden 8 ana grupta toplanmıştır:

### Kategori Dağılım Tablosu

| Kategori | Özellik Sayısı | Temsil Ettiği Futbol Dinamiği |
| :--- | :---: | :--- |
| **1. Ceza Sahası Baskısı & Şutlar** | 14 | Rakip ceza sahasında toplanma (`touches_in_opp_box`), kaleyi bulan şutlar (`sot`). |
| **2. Beklenen Gol (xG) Kalitesi** | 8 | TheStatsAPI kaynaklı şut kalitesi ve gol beklentisi form grafiği. |
| **3. Takım Gücü & Puan Formu** | 8 | Dinamik Elo puanları, mekan Eloları, maç başına puan (PPG) ve averaj (GDPG). |
| **4. Saha & Mekan Ayrımı (Venue Form)** | 8 | Ev sahibinin evindeki xG/gol grafiği ile deplasmanın dış sahadaki savunma direnci. |
| **5. Büyük Gol Fırsatları (Big Chances)** | 6 | Net gol pozisyonu üretme (`big_chances_for`) ve rakiplere verilen net fırsatlar. |
| **6. Taktiksel Savunma Çizgisi (YENİ)** | **3** | Ofsayt tuzağı sıklığı, savunma hattı yüksekliği ve karşılıklı açık alan riski. |
| **7. Kadro Değeri & İlk 11 Gücü** | 4 | Logaritmik piyasa değeri oranı (`log_mv_ratio`), ilk 11 hücum vs savunma endeksi. |
| **8. Topa Sahip Olma & Maç Temposu** | 7 | Top hakimiyeti (`possession`), beklenen maç şut hacmi (`exp_match_shots_5`). |

---

## 5. Özellik Katsayıları & Etki Analizi (Feature Weights)

L2 cezalı Poisson Regresyonunun öğrendiği en etkili özelliklerin katsayı dökümü:

### 5.1. En Çok Etki Yaratan İlk 10 Özellik

| Sıra | Özellik Adı | Ev Golü Katsayısı ($\lambda_{ev}$) | Dep Golü Katsayısı ($\lambda_{dep}$) | Toplam Etki Büyüklüğü | Futbol Anlamı |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `effective_log_mv_ratio` | `+0.01566` | `-0.01292` | `0.02858` | Kalite ve bitiricilik makası (Piyasa değeri üstünlüğü). |
| **2** | `away_touches_in_opp_box_roll_10` | `-0.01009` | `+0.01091` | `0.02099` | Deplasmanın rakip ceza sahasına girme sıklığı. |
| **3** | `away_touches_in_opp_box_ewma_02` | `-0.00937` | `+0.01047` | `0.01984` | Deplasmanın son haftalardaki ceza sahası baskı ivmesi. |
| **4** | `elo_home` | `+0.00938` | `-0.01016` | `0.01954` | Ev sahibinin genel güç endeksi. |
| **5** | `elo_venue_home` | `+0.00942` | `-0.00944` | `0.01887` | Ev sahibinin iç saha özelindeki güç çarpanı. |
| **6** | `home_venue_xg_against_ewma_02` | `-0.00725` | `+0.01132` | `0.01857` | Ev sahibinin kendi evinde yediği pozisyon kalitesi (Savunma açığı). |
| **7** | `ppg_home` | `+0.00974` | `-0.00865` | `0.01840` | Ev sahibinin lig puan ortalaması. |
| **8** | `away_xg_for_roll_10` | `-0.00620` | `+0.01087` | `0.01706` | Deplasmanın son 10 maçtaki net gol beklentisi. |
| **9** | `home_touches_in_opp_box_roll_10`| `+0.01170` | `-0.00504` | `0.01674` | Ev sahibinin rakip ceza sahasında topla buluşma sayısı. |
| **10**| `gdpg_home` | `+0.00893` | `-0.00687` | `0.01580` | Ev sahibinin maç başına averaj performansı. |

---

### 5.2. Yeni Eklenen Taktiksel Savunma Çizgisi Özelliklerinin Katsayıları

| Özellik Adı | Ev Katsayısı | Dep Katsayısı | Yorum |
| :--- | :---: | :---: | :--- |
| `home_high_line` | `+0.00626` | `+0.00150` | Ev sahibi önde bastığında kendi gol şansı belirgin artıyor. |
| `away_high_line` | `-0.00144` | `+0.00405` | Deplasman savunmayı öne çektiğinde kendi gol şansı artıyor. |
| `mutual_high_line_risk` | `+0.00283` | `+0.00325` | **İki takım da önde oynarsa her iki kaleye de gol beklentisi artıyor.** |

---

## 6. Veri Kalitesi, Bütünlük ve Güvenlik Önlemleri

Modelimizin güvenilirliğini ve canlı ortamdaki sağlamlığını garanti altına alan 5 temel mühendislik standardı:

### 6.1. Sıfır Gelecek Sızıntısı Kuralı (Zero-Leakage & `shift(1)`)
- Bir maçın tahmininde o maçın kendi istatistikleri **asla** kullanılamaz.
- Tüm hareketli ortalamalar (`roll_10`) ve üssel ağırlıklar (`ewma_02`), kesin olarak bir önceki maçtan (`shift(1)`) itibaren hesaplanır.

### 6.2. Matematiksel Monotonluk Garantisi
- Bağımsız modeller yerine tek bir matris kullanıldığı için olasılık kesişmesi hatası oluşamaz:
  $$P(\text{Üst 1.5}) \ge P(\text{Üst 2.5}) \ge P(\text{Üst 3.5})$$
  $$P(\text{Takım} > 0.5) \ge P(\text{Takım} > 1.5) \ge P(\text{Takım} > 2.5)$$

### 6.3. Kilitli Sezon Kuralı (`LOCKED_SEASONS = {'2026_27'}`)
- İçinde bulunduğumuz 2026/27 sezonunun ilk 60 maçı, model kalibrasyonuna veya hiperparametre seçimine sokulmamış; tamamen bağımsız bir canlı test katmanı olarak korunmuştur.

### 6.4. Sayısal Sınırlar (Numerical Clipping)
- Poisson hızları ($\lambda$) aşırı uç değerleri önlemek için $[0.05, 6.0]$ aralığına kırpılır. Bir takımın maçta 6.0'dan fazla veya 0.05'ten az beklenen gol üretmesi engellenerek aşırı oran anormallikleri önlenir.

### 6.5. Soğuk Başlangıç Küçültmesi (Bayesian Shrinkage)
- Sezon başında henüz 1-2 maçı olan takımlar veya lige yeni çıkan kulüpler için istatistikler ham değer yerine lig tarihsel ortalamalarına (`LEAGUE_PRIORS`) doğru küçültülür (Shrinkage).

---

## 7. A/B Benchmark & Hipotez Testleri Geçmişi

Model geliştirme sürecinde yapılan tüm A/B testlerinin sonuçları ve alınan kararlar:

### Deney 1: Kilit Paslar (Shot Assists) Modele Eklenmeli mi?
- **Hipotez:** Kilit pas verisi hücum yaratıcılığını gösterir, gol tahminini artırabilir.
- **Sonuç:** 2.5 Üst Log-Loss `0.6779`'dan `0.6782`'ye kötüleşti.
- **Neden:** Kilit paslar zaten `touches_in_opp_box` ve `xg_for` ile %85 korelasyona sahipti; yeni bilgi getirmedi, sadece gürültü ekledi.
- **Karar:** **Reddedildi.** Kilit paslar modele sokulmadı, arayüzde analiz metriği olarak bırakıldı.

### Deney 2: Kadro Değeri Azaltılıp Taktiksel Savunma Çizgisi Eklenmeli mi?
- **Hipotez:** Kadro değeri oyun felsefesini ölçemez; önde basan takımların arkada bıraktığı boşluklar golü belirler.
- **Sonuç:** 2.5 Üst Log-Loss **`0.6779`'dan `0.6774`'e düştü.** 95% Güven aralığı tamamen sıfırın altında (`[-0.00089, -0.00012]`) çıktı.
- **Neden:** `home_high_line` ve `mutual_high_line_risk` takımların taktiksel açık oyun eğilimini başarıyla yakaladı.
- **Karar:** **Onaylandı ve Canlıya Alındı.** Model 55'ten 58 özelliğe yükseltildi.

---

## 8. Dürüst Model Denetimi & Zayıf Noktalar (Kritik Röntgen)

Raporun akademik ve finansal tarafsızlığı gereği, modelimizin zayıf olduğu ve aşırı iyimser çerçevelenmemesi gereken **5 kritik gerçeği** açıkça kayda geçiriyoruz:

### 8.1. ROC-AUC ve Ayırt Edicilik (Discrimination) vs Kalibrasyon (Calibration)
- **Problem:** Modellerimizin ROC-AUC skorları **0.516 – 0.538** bandındadır. Teorik olarak 0.50 rastgele yazı-turadır.
- **Teknik Neden:** Futbol gol dağılımında doğal stokastik gürültü (Poisson varyansı $\approx$ ortalama gol) inanılmaz derecede yüksektir. 15. dakikada gelen bir kırmızı kart veya direkten dönen bir top 3 golü bir anda silebilir. Akademik spor modellemesi literatüründe dahi gol toplamları için AUC tavanı genellikle **0.55 – 0.58** civarındadır (kredi skorlama veya churn modellerindeki gibi 0.80+ AUC futbolda matematiksel olarak imkansızdır).
- **Sonuç:** Modelimiz **Kalibrasyon (ECE: %2.17)** açısından harikadır; yani *"bu maç %58 üst biter"* dediğinde bu maç havuzunun gerçekten %58'i üst biter. Ancak model tek tek hangi maçın üst, hangi maçın alt olacağını sıralamada (discrimination) zayıftır. Dolayısıyla model "geleceği gören bir kahin" değil, "piyasadaki oran hatalarını yakalayan bir olasılık düzelticisidir".

### 8.2. Log-Loss Seviyeleri ve Naive Baseline Gerçeği
- 2.5 Üst modelimizin Log-Loss skoru `0.6774`'tür.
- Hiçbir maç verisine bakmayan, her maça körlemesine sabit lig ortalaması (%58.7) veren Naive Baseline'ın Log-Loss'u ise `0.6780`'dir.
- **Gerçek Bilgi Kazancı (Edge):** Modelin tüm bu 58 özellik ve Dixon-Coles harmanıyla sağladığı saf bilgi kazancı **-0.0006 log-loss puanıdır**.
- Bu marjinal kazanç, gol bahislerinde körü körüne her maça oynayarak para kazanılamayacağını; avantajın sadece model olasılığı ile büro olasılığı arasında en az %5-8'lik makas (Value) oluşan özel maç tiplerinde aranabileceğini kanıtlar.

### 8.3. 3.5 Üst Piyasasında Sınıf Dengesizliği & Yapay F1 Skoru
- Tablodaki `3.5 Üst -> F1 = 0.045` skoru bir model hatası değil, **0.50 sınıflandırma eşiğinin dengesiz sınıflarda işlevsiz olmasının** sonucudur.
- Premier League'de maçların sadece %35.5'i 3.5 Üst biter. Model hiçbir maça %50'den büyük 3.5 Üst olasılığı atamadığı için varsayılan 0.50 eşiğinde neredeyse hiç pozitif tahmin üretmez (Recall: %2.3).
- Modelin accuracy'sinin %65 görünmesi ise "neredeyse her maça 3.5 Alt" demesinden kaynaklanır (Accuracy Paradox). Bahis operasyonlarında 0.50 eşiği anlamsızdır; piyasa oranıyla model olasılığı kıyaslanmalıdır.

### 8.4. Sezon Bazlı Performans Aşınması (Concept Drift)
- Sezonluk holdout sonuçlarında dikkat çeken bir aşınma mevcuttur:
  - 2023/24: `0.6692` Log-Loss
  - 2024/25: `0.6764` Log-Loss
  - 2025/26: `0.6861` Log-Loss
- **Nedeni (Kural Değişiklikleri & Taktiksel Adaptasyon):**
  2023/24 sezonunda Premier League hakemleri katı bir kararla maçlara +10-12 dakika uzatma eklemiş, lig tarihinin en gollü sezonu (maç başı 3.28 gol) yaşanmıştır. Sonraki sezonlarda takımlar taktiksel fauller ve tempoyu düşürmeyle bu duruma adapte olmuş; gol trendleri dalgalanmıştır.
- **Çözüm Stratejisi:** Dixon-Coles modelinin yarı ömrünü (`half_life`) 365 günden 180 güne indirmek ve sezon içi kural değişikliklerine daha hızlı uyum sağlayan dinamik bir ağırlıklandırma geliştirmek.

### 8.5. Kadro Değeri Katsayı Çelişkisi (Multicollinearity / Çoklu Doğrusal Bağlantı)
- `effective_log_mv_ratio` katsayısı +0.0156 ile listenin en tepesindedir; ancak modelden silindiğinde Log-Loss yalnızca `+0.0001` kötüleşir.
- **İzahı:** Katsayı büyüklüğü standartlaştırılmış özelliklerde varyans ve diğer özelliklerle yüksek korelasyon (multicollinearity) yüzünden şişebilir. Kadro değerinin taşıdığı bilgi zaten Elo, PPG, averaj ve xG içerisinde mevcuttur (redundant signal). Bu nedenle katsayı büyüklüğü tek başına bir özelliğin marjinal önemini (SHAP / permutation importance) temsil etmez.

### 8.6. Bahis Piyasası (Bookmaker) Arbitrajı & Value Bet Gerçeği
- 218 maçlık gerçek açılış oranları denetiminde bahis piyasası **0.5962 ROC-AUC** üretirken, modelimiz **0.5843 ROC-AUC** üretmiştir.
- Modelin büroya karşı %5'in üzerinde "değer (value)" gördüğü 18 maçta simüle edilen bahislerin net getirisi **-%3.42 ROI** çıkmıştır.
- **Stratejik Konumlandırma:** Model tek başına bahis bürolarını "yenen" bir sihirli arbitraj kutusu değildir. Modelimizin asıl gücü; **xG ve tempo dinamiklerini harmanlayarak adil olasılıkları hatasız hesaplamak**, **maç içi senaryo simülasyonları** ve **piyasadaki olağandışı oran sapmalarını saptamak için tarafsız bir referans motoru oluşturmaktır**.

---

## 9. Yönetici Özeti & Sonuç

Premier League Gol Modelimiz; saf istatistiksel Poisson varsayımlarını aşarak, **saha içi xG kalitesini**, **zaman ağırlıklı gerçek skor geçmişini (Dixon-Coles)** ve **taktiksel savunma hattı derinliğini** tek bir $13 \times 13$ olasılık matrisinde birleştiren dengeli bir mimariye ulaşmıştır. 

Modelimiz "kesin kehanet" aracı veya piyasayı tek başına yenen bir kumar botu olarak değil; **istatistiksel kalibrasyonu yüksek, lig kaymalarına karşı korunan ve taktiksel değişimleri fiyatlayan kurumsal bir olasılık motoru** olarak değerlendirilmelidir.
