# Premier League 2026/27 Paper Trading Protokolü (v1.0)

**Tarih:** 17 Ekim 2026  
**Durum:** Resmi Protokol (Yürürlükte)  
**Metodolojik Dayanak:** [Premier League Modelleri Raporu — Bölüm 8: Metodolojik Anayasa](premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage)  
**Dokümantasyon Ağı:** [README](../../README.md) · [Ana Kapsamlı Rapor](premier_league_models_comprehensive_report.md) · [Rapor Merkezi](README.md) · [AI Context](../../AI_CONTEXT.md) · [API Entegrasyonu](../model_api_integration.md)

---

## 1. Amaç & Metodolojik Gerekçe

Holdout veri setindeki 218 maçlık geçmiş piyasa oranları denetiminde; modelin büroya karşı **Edge $> 3\%$** gördüğü 51 maçta **%56.9 kazanma oranı** ve **+%10.02 ROI** simüle edilmiştir. 

Ancak yapılan $k=7$ eşikli çoklu hipotez denetiminde (Multiple Testing Correction):
- Binomial test $p = 0.1995 \to$ Bonferroni $p = \mathbf{1.0000}$, FDR $q = \mathbf{0.8289}$
- ROI $t$-test $p = 0.2323 \to$ Bonferroni $p = \mathbf{1.0000}$, FDR $q = \mathbf{0.9026}$

olarak saptanmıştır. Bu durum, $N=51$ maçlık geçmiş örneğin tek başına bir "alfa tescili" olmadığını; istatistiksel varyans ile gerçek piyasa avantajını ayırt etmek için **$N \ge 200 - 350$ maçlık ileriye dönük (forward-testing / out-of-sample) bir Paper Trading protokolünün** zorunlu olduğunu kanıtlamıştır.

---

## 2. Kapsam & Evren (Universe & Markets)

1. **Lig & Dönem:** 
   - Premier League 2026/27 Sezonu (Kalan ~320 maç).
   - Yetersiz güç durumunda 2027/28 sezonu ilk yarısı dahil edilir.
2. **Hedef Piyasalar:**
   - **2.5 Gol Üstü / Altı** ($P(\text{Üst } 2.5)$)
   - **Karşılıklı Gol Var / Yok (BTTS)** ($P(\text{BTTS})$)
   *(Her iki piyasanın olasılıkları istisnasız $13 \times 13$ iki değişkenli skor matrisinden $M_{ij}$ türetilir; bağımsız alt model dallanması yasaktır).*
   > **Değişiklik (19 Ekim 2026):** Bu iki piyasada **bahis sinyali üretilmez**; yalnızca olasılık kaydı tutulur (log-loss izleme). Gerekçe: 3 dış sezonda model Bet365'ten anlamlı derecede kötü (2.5 Üst +0.0114, CI [+0.0031, +0.0195]; KG +0.0075, CI [+0.0014, +0.0137]), KG ayrıca sabit Poisson'u geçemiyor (`GOAL_MODELS_ANALYSIS.md`). Kural, kanıt değişirse (yeni özellik, Ç4) yeniden açılır.
3. **Oran Kaynağı:**
   - Kapanış / Açılış piyasa oranları (`over_25_open`, `under_25_open`, `btts_yes_open`, `btts_no_open`).
   - Adil piyasa olasılığı, büro marjı (vig) çıkarılarak normalize edilir:
     $$P_{\text{market\_fair}} = \frac{1 / \text{odds}_{\text{over}}}{1 / \text{odds}_{\text{over}} + 1 / \text{odds}_{\text{under}}}$$

---

## 3. Paralel İzleme Eşikleri (Thresholds)

Modelin piyasaya göre sağladığı avantaj:
$$\text{Edge} = P_{\text{model}} - P_{\text{market\_fair}}$$

Protokol kapsamında 3 paralel sanal portföy eş zamanlı izlenir:
1. **Portföy A (Geniş Havuz):** $\text{Edge} \ge +2.0\%$ (Beklenen maç hacmi: ~100-120 maç/sezon)
2. **Portföy B (Referans Havuz):** $\text{Edge} \ge +3.0\%$ (Beklenen maç hacmi: ~70-90 maç/sezon)
3. **Portföy C (Yüksek Değer Havuzu):** $\text{Edge} \ge +5.0\%$ (Beklenen maç hacmi: ~25-35 maç/sezon)

*Her bahiste sabit 1 birim (flat stake) sanal bahis kabul edilir.*

---

## 4. Örneklem Büyüklüğü & İstatistiksel Güç (Power Analysis)

Standart güç analizi formülü gereği:
$$N_{\text{req}} = \frac{(Z_{\alpha/2} + Z_\beta)^2 \cdot \sigma^2}{\Delta^2}$$

- $\Delta = +0.03$ (%3'lük kalıcı getiri avantajı) ve $\sigma_{\text{binary}} \approx 0.50$ varsayımıyla:
  - $\alpha = 0.05$ ($Z_{\alpha/2} = 1.96$)
  - Güç $= 0.80$ ($Z_\beta = 0.8416$)
  - **Gereken Asgari Örneklem:** $N \approx 218$ maç.
- **Değerlendirme Takvimi:**
  - **İlk Ara Değerlendirme (Interim):** $N = 100$ maç (Güven aralığı trendi).
  - **Resmi Karar Noktası (Checkpoint):** $N = 200$ maç.
  - **Nihai Sezon Değerlendirmesi:** $N = 380$ maç (Sezon sonu).

---

## 5. Raporlanacak Metrikler

Her 50 maçta bir otomatik güncellenecek metrik seti:
1. **Finansal Performans:**
   - Sanal ROI %: $(\text{Toplam Net Kâr} / N) \times 100$
   - Kazanma Oranı (Win Rate) %
   - Maksimum Drawdown (Birim)
2. **İstatistiksel Sinyal Testleri:**
   - Binomial Test $p$-değeri ($H_0: p_{\text{win}} \le \bar{p}_{\text{market}}$)
   - One-sample $t$-test / Permütasyon $p$-değeri ($H_0: \text{ROI} \le 0$)
   - **Çoklu Test Düzeltmesi:** 3 portföy için Benjamini-Hochberg FDR $q$-değeri.
   - **10.000 İterasyonlu Bootstrap %95 Güven Aralığı:** Hem ROI hem $\Delta \text{AUC}$ için raporlanır.

---

## 6. Durdurma & Karar Kuralları (Termination & Acceptance Rules)

| Durum | Kriter | Karar / Aksiyon |
| :--- | :--- | :--- |
| 🛑 **Erken Durdurma (Hard Stop)** | $N \ge 100$ maçta $\text{ROI} < -5.0\%$ VEYA Drawdown $> 20$ birim | İlgili eşik stratejisi derhal dondurulur; hipotez reddedilir. |
| ⚠️ **Gürültü / Yetersiz Güç** | $N = 200$'de $\text{ROI} > 0$ fakat FDR $q \ge 0.05$ | Canlıya alınmaz; test 2027/28 sezonuna uzatılır. |
| 🏆 **Strateji Kabulü (Production)** | $N \ge 200$'de $\text{ROI} \ge +3.0\%$ VE FDR $q < 0.05$ VE Bootstrap %95 CI tabanı $> 0$ | Modelin piyasaya karşı yapısal avantajı tescillenir; canlı bahis entegrasyonu onaylanır. |

---

## 7. Yürütme ve Kayıt

Her hafta oynanan maçlar öncesinde `src/analytics/paper_trading_tracker.py` betiği çalıştırılarak maç öncesi piyasa kapanış oranları ve model tahminleri kaydedilecek, maç bitiminde skorlar otomatik işlenerek kümülatif getiri eğrisi güncellenecektir.
