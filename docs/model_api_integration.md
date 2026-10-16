# Premier League Gol Modeli — API & Sistem Entegrasyon Kılavuzu

Bu doküman, Premier League Gol Tahmin Modeli'nin (`goals_models_v1.joblib`) backend API uç noktaları, veritabanı şeması ve kullanıcı arayüzü bileşenleri ile olan teknik entegrasyon detaylarını içerir.

---

## 1. Sistem Mimari Akışı

Gol modelimiz tek bir ikili (binary) sınıflandırıcı yerine, maçın tüm olası skorlarını eş zamanlı modelleyen **$13 \times 13$ İki Değişkenli (Bivariate) Skor Matrisi** üzerinde çalışır ve aşağıdaki API uç noktalarını besler:

```
                          [GOL MODELİ BİVARİATE MATRİSİ]
                                         │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
[2.5 Üst/Alt]     [1.5 & 3.5 Üst]   [KG Var/Yok]   [Takım Baremleri]  [1X2 Doğrulama]
  API & UI           API & UI         API & UI      0.5, 1.5, 2.5        Dixon-Coles
```

---

## 2. API Uç Noktaları ve Kullanılan Alanlar

### 2.1. 2.5 Gol Üst / Alt Piyasası
- **API Alanı:** `/api/predict` -> `goals.over_2.5.pct`
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
- **Dinamik Eşik:** Ligin tarihsel KG Var ortalaması (%56.6) dinamik sınıflandırma eşiği olarak kullanılır.

### 2.4. Tek Taraflı Takım Gol Baremleri (Team Totals)
- **API Alanı:** `/api/predict` -> `goals.team_totals.home` ve `goals.team_totals.away`
- **Kapsam:** Ev ve deplasman için 0.5, 1.5, 2.5 baremleri; her baremin Üst/Alt yüzdesi ve adil ondalık oranı.
- **Dinamik Piyasa Çizgisi:** %50 olasılığa en yakın barem otomatik olarak `🎯 Ana Barem` olarak etiketlenir.
- **Arayüz Bileşeni:** `MatchPredictionTab.jsx` takım baremleri paneli ve `PredictorMetricCards.jsx` özet rozeti.

### 2.5. 1X2 Maç Sonucu Modeli Çapraz Doğrulaması
- 1X2 sınıflandırıcısının (XGBoost/LightGBM) yanında, Dixon-Coles matrisinin köşegen altı ve üstü toplamı alınarak saf skor bazlı 1X2 olasılıkları üretilir ve model denetim raporlarında çapraz kontrol çıpası olarak kullanılır.

### 2.6. Model Audit & Simülasyon
- `ModelAuditTab.jsx` üzerinden haftalık/sezonluk bahis simülasyonları ve ROI analizlerinde girdi olarak kullanılır.

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
