# Premier League Veri Kalitesi ve Denetim Raporu (2024_25)

**Tarih:** 2024-25 Sezon Kapanışı  
**Kapsam:** Premier League 2024/25 (CompSeason ID: 719)  
**Toplam İncelenen Maç Sayısı:** 380 / 380 (100.0%)  
**Toplam Kaydedilen Şut & Olay Sayısı:** 15076  

---

## 1. Veri Seti Bütünlük ve Eksik Değer Kontrolü

- **Beklenen Maç Sayısı:** 380
- **Mevcut Maç Sayısı:** 380
- **Eksik Maç:** 0
- **Kritik Kolonlarda Null / Eksik Değer Sayısı:**
  - **0 Hata**: İncelenen tüm maçlarda kritik kolonlarda null veya kayıp veri bulunmamaktadır (%100 tam veri).

---

## 2. Maç Sonucu ve Ev Sahibi Avantajı Dağılımı

| Sonuç Türü | Maç Sayısı | Yüzde Dağılımı |
|:---|:---:|:---:|
| **Ev Sahibi Galibiyeti (H)** | 155 | %40.8 |
| **Beraberlik (D)** | 93 | %24.5 |
| **Deplasman Galibiyeti (A)** | 132 | %34.7 |

- **Toplam Gol Ortalaması:** 2.93 (Medyan: 3.0)
- **2.5 Üstü Biten Maç Oranı:** %56.6

---

## 3. Temel Mikro Metriklerin İstatistiki Özeti

| Metrik | Ortalama | Std Sapma | Min | Medyan | Maks |
|:---|:---:|:---:|:---:|:---:|:---:|
| `home_score` | 1.51 | 1.28 | 0.0 | 1.0 | 7.0 |
| `away_score` | 1.42 | 1.19 | 0.0 | 1.0 | 6.0 |
| `total_goals` | 2.93 | 1.62 | 0.0 | 3.0 | 9.0 |
| `home_won_corners` | 5.43 | 3.18 | 0.0 | 5.0 | 17.0 |
| `away_won_corners` | 4.87 | 3.03 | 0.0 | 4.0 | 18.0 |
| `total_corners` | 10.29 | 3.47 | 2.0 | 10.0 | 19.0 |
| `home_total_throws` | 16.78 | 5.15 | 5.0 | 16.0 | 36.0 |
| `away_total_throws` | 16.12 | 5.22 | 5.0 | 16.0 | 32.0 |
| `total_throws` | 32.90 | 7.64 | 14.0 | 32.0 | 55.0 |
| `home_saves` | 2.82 | 1.84 | 0.0 | 2.5 | 8.0 |
| `away_saves` | 3.33 | 2.05 | 0.0 | 3.0 | 13.0 |
| `total_saves` | 6.16 | 2.58 | 0.0 | 6.0 | 16.0 |
| `home_total_scoring_att` | 13.75 | 5.58 | 2.0 | 13.0 | 35.0 |
| `away_total_scoring_att` | 12.17 | 5.42 | 1.0 | 11.5 | 37.0 |
| `total_shots` | 25.92 | 6.00 | 13.0 | 26.0 | 48.0 |
| `home_ontarget_scoring_att` | 4.84 | 2.48 | 0.0 | 5.0 | 16.0 |
| `away_ontarget_scoring_att` | 4.27 | 2.34 | 0.0 | 4.0 | 13.0 |
| `total_shots_ontarget` | 9.11 | 2.99 | 2.0 | 9.0 | 19.0 |
| `home_possession_percentage` | 50.98 | 11.23 | 22.2 | 51.5 | 77.8 |
| `away_possession_percentage` | 49.02 | 11.23 | 22.2 | 48.5 | 77.8 |

---

## 4. Olay ve Şut Akışı (Play-by-Play) İncelemesi

Toplam Olay Türü Dağılımı:

| Olay Türü | Toplam Adet | Maç Başına Ortalama |
|:---|:---:|:---:|
| `corner` | 3912 | 10.29 |
| `miss` | 3351 | 8.82 |
| `attempt blocked` | 2927 | 7.70 |
| `attempt saved` | 2272 | 5.98 |
| `yellow card` | 1575 | 4.14 |
| `goal` | 1013 | 2.67 |
| `red card` | 26 | 0.07 |

---

## 5. Sonuç ve Modelleme Uygunluğu
Veri seti %100 eksiksiz, tutarlı ve veri sızıntısından arındırılmış durumdadır. Tüm şut, korner, taç ve kurtarış verileri Faz 3 öznitelik mühendisliği ve Faz 4 modelleme süreçlerine tamamen hazırdır.
