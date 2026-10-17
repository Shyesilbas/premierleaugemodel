# Premier League Modelleri — API & Sistem Entegrasyon Kılavuzu

**Dokümantasyon Ağı:** [README](../README.md) · [Ana Kapsamlı Rapor](reports/premier_league_models_comprehensive_report.md) · [Rapor Merkezi](reports/README.md) · [Paper Trading 2026/27](reports/paper_trading_protocol_2026_27.md) · [AI Context](../AI_CONTEXT.md) · [Veri Kataloğu](../VERI_VE_GOSTERIM_KATALOGU.md)

Bu doküman, üretim modellerinin (gol skor matrisi `goals_models_v1`, 1X2 `outcome_models_v1` ve beş sayım modeli) çıktılarının `GET /api/predict` alanlarına ve React bileşenlerine nasıl bağlandığını anlatır. Modellerin kendisi için bkz. [model raporları](reports/models/).

---

## 1. Sistem Mimari Akışı

Gol modelimiz tek bir ikili (binary) sınıflandırıcı yerine, maçın tüm olası skorlarını eş zamanlı modelleyen bir **$13 \times 13$ skor matrisi** üzerinde çalışır: iki bağımsız Poisson oranı (Dixon-Coles takım modeli × 11 özellikli Poisson regresyonu, geometrik harman) + düşük skor hücrelerinde Dixon-Coles $\tau$ düzeltmesi. Gerçek bir *bivariate* Poisson değildir.

**Tek kaynak kuralı (17 Ekim 2026):** `GET /api/predict` içinde matris, lojistik 1X2 modelinin (`outcome_models_v1`) olasılıklarına hizalanır (`align_to_outcome_probs`). Böylece ekrandaki 1X2, Üst/Alt, KG, takım baremleri ve beklenen goller aynı dağılımdan gelir ve birbiriyle çelişmez.

```
                    [SKOR MATRİSİ — lojistik 1X2'ye hizalı]
                                         │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
[2.5 Üst/Alt]     [1.5 & 3.5 Üst]   [KG Var/Yok]   [Takım Baremleri]  [Beklenen Goller]
  API & UI           API & UI         API & UI      0.5, 1.5, 2.5      matris beklentisi
```

---

## 2. API Uç Noktaları ve Kullanılan Alanlar

### 2.1. 2.5 Gol Üst / Alt Piyasası
- **API Alanı:** `GET /api/predict` -> `goals.over_2.5.pct`
- **Arayüz Bileşeni:** `MatchPredictionTab.jsx` ve genel maç listesi kartları.
- **Piyasa Karşılaştırması:** Bahis bürosu adil kapanış oranı ile kıyaslanarak Value (Edge) tespitinde referans alınır.

### 2.2. 1.5 ve 3.5 Gol Üst / Alt Piyasaları
- **API Alanı:** `/api/predict` -> `goals.over_1.5.pct`, `goals.over_3.5.pct`
- **Arayüz Bileşeni:** `MatchPredictionTab.jsx` 4'lü piyasa paneli.
- **Matematiksel Monotonluk:** $P(1.5) \ge P(2.5) \ge P(3.5)$ kuralı ortak $13 \times 13$ matris üzerinden matematiksel olarak garanti altındadır.

### 2.3. Karşılıklı Gol Var / Yok (BTTS)
- **API Alanı:** `/api/predict` -> `goals.btts_pct`, `goals.btts_prediction`
- **Hesaplama Formülü:** Matrisin sıfır gol içeren satır ve sütunlarının elenmesiyle türetilir:
  $$P(\text{BTTS}) = 1 - \sum_{i=0}^{12} M_{i,0} - \sum_{j=0}^{12} M_{0,j} + M_{0,0}$$
- **Etiket Eşiği:** `btts_prediction` = "KG Var" ⇔ $P \ge 0.5$. Ligin tarihsel KG oranı ayrıca `btts_prior_pct` alanında döner (yalnızca bilgi). *(17 Ekim 2026 öncesi eşik lig ortalamasıydı; %56.4'e "KG Yok" yazıyordu.)*

### 2.4. Tek Taraflı Takım Gol Baremleri (Team Totals)
- **API Alanı:** `/api/predict` -> `goals.team_totals.home` ve `goals.team_totals.away`
- **Kapsam:** Ev ve deplasman için 0.5, 1.5, 2.5 baremleri; her baremin Üst/Alt yüzdesi ve adil ondalık oranı.
- **Dinamik Piyasa Çizgisi:** %50 olasılığa en yakın barem otomatik olarak `🎯 Ana Barem` olarak etiketlenir.
- **Arayüz Bileşeni:** `MatchPredictionTab.jsx` takım baremleri paneli ve `PredictorMetricCards.jsx` özet rozeti.

### 2.5. 1X2 ile Skor Matrisinin Hizalanması
- 1X2 olasılıkları lojistik modelden gelir (aynı sezon holdout'larında matris 1X2'sinden sezon başına 0.006–0.016 log-loss daha iyi).
- Matrisin ev galibiyeti / beraberlik / deplasman bölgeleri bu olasılıklara ölçeklenir; bölge içindeki skor dağılımı korunur. Holdout testi: 1X2 −0.0157, O2.5 −0.0012, O1.5/O3.5 ≈ 0, BTTS +0.0014.
- `goals.expected_home_goals` / `expected_away_goals` hizalanmış matristen hesaplanır (`expected_goals`).

### 2.6. Sayım Modelleri (Korner, Kart, Kurtarış, Ofsayt, Taç)
- **API Alanları:** `GET /api/predict` → `corners`, `cards`, `saves`, `offsides`, `throws`. Her biri `expected_total`, `expected_home`, `expected_away` ve (kurtarış hariç) `prob_over_*_pct` döner; `cards` için ayrıca `referee { name, avg_cards, avg_fouls }`.
- **`model_skill`:** `"model"` ya da `"baseline"`. Model iki kapıyı da geçemezse (CV + iç içe dış sezon; [Ana Rapor Bölüm 8, madde 7](reports/premier_league_models_comprehensive_report.md#bölüm-8-metodolojik-anayasa--sıfır-sızıntı-zero-leakage)) artifact eğitim ortalamasını taşır ve alan `"baseline"` olur. Arayüz bunu "Veri ortalaması tabanlı tahmin" rozetiyle gösterir. Güncel durum: kart ve kurtarış `baseline`, diğerleri `model`.
- **Olasılıklar:** `expected_total` üzerinden NB2(μ, α) kuyruk olasılığı; α artifact'taki `count_dispersion_alpha`.
- **Ev/deplasman paylaşımı model değildir:** toplam, takımların rolling for/against ortalamalarından türetilen bir oranla bölünür (%20–%80 aralığına kırpılır).
- **`shots.expected_total` model değildir:** `expected_saves × 4.1` sabit çarpanıdır; kurtarış modeli ortalamada olduğundan pratikte her maçta aynıdır.
- **Arayüz Bileşenleri:** `PredictorMetricCards.jsx`, `MatchPredictionTab.jsx`. Model ayrıntıları: [docs/reports/models/](reports/models/).

### 2.7. Model Audit & Simülasyon
- `ModelAuditTab.jsx` üzerinden haftalık/sezonluk bahis simülasyonları ve ROI analizlerinde girdi olarak kullanılır. `src/analytics/model_audit.py` API ile aynı yolu izler (hizalanmış matris, kayıtlı kalibratörler, KG eşiği %50); önbellekteki özetler `force_recalc=True` ile yenilenmelidir.

---

## 3. Mühendislik & Veri Bütünlüğü Standartları

1. **Sıfır Gelecek Sızıntısı Kuralı (Zero-Leakage & `shift(1)`):**
   - Bir maçın tahmininde o maçın kendi istatistikleri **asla** kullanılamaz. Tüm hareketli ortalamalar (`roll_10`) ve üssel ağırlıklar (`ewma_02`), kesin olarak bir önceki maçtan (`shift(1)`) itibaren hesaplanır.
2. **Kilitli Sezon Kuralı (`LOCKED_SEASONS = {'2026_27'}`):**
   - İçinde bulunulan 2026/27 sezonunun ilk 60 maçı hiperparametre seçimine sokulmamış; bağımsız canlı test katmanı olarak korunmuştur.
3. **Sayısal Sınırlar (Numerical Clipping):**
   - Poisson hızları ($\lambda$) aşırı uç değerleri önlemek için $[0.05, 6.0]$ aralığına kırpılır.
4. **Soğuk Başlangıç Küçültmesi (Bayesian Shrinkage):**
   - Sezon başında henüz 1-2 maçı olan takımlar veya lige yeni çıkan kulüpler için istatistikler lig tarihsel ortalamalarına (`LEAGUE_PRIORS`) doğru büzülür.
