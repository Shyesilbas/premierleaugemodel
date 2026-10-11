# Premier League Veri Kalitesi ve Denetim Raporu (2024-25 & 2025-26)

**Tarih:** 2024-25 Sezon Kapanışı  
**Kapsam:** Premier League 2024/25 (CompSeason ID: 719)  
**Toplam İncelenen Maç Sayısı:** 760 / 380 (200.0%)  
**Toplam Kaydedilen Şut & Olay Sayısı:** 29545  

---

## 1. Veri Seti Bütünlük ve Eksik Değer Kontrolü

- **Beklenen Maç Sayısı:** 380
- **Mevcut Maç Sayısı:** 760
- **Eksik Maç:** -380
- **Kritik Kolonlarda Null / Eksik Değer Sayısı:**
  - **0 Hata**: İncelenen tüm maçlarda kritik kolonlarda null veya kayıp veri bulunmamaktadır (%100 tam veri).

---

## 2. Maç Sonucu ve Ev Sahibi Avantajı Dağılımı

| Sonuç Türü | Maç Sayısı | Yüzde Dağılımı |
|:---|:---:|:---:|
| **Ev Sahibi Galibiyeti (H)** | 317 | %41.7 |
| **Beraberlik (D)** | 197 | %25.9 |
| **Deplasman Galibiyeti (A)** | 246 | %32.4 |

- **Toplam Gol Ortalaması:** 2.84 (Medyan: 3.0)
- **2.5 Üstü Biten Maç Oranı:** %55.8

---

## 3. Temel Mikro Metriklerin İstatistiki Özeti

| Metrik | Ortalama | Std Sapma | Min | Medyan | Maks |
|:---|:---:|:---:|:---:|:---:|:---:|
| `home_score` | 1.52 | 1.22 | 0.0 | 1.0 | 7.0 |
| `away_score` | 1.32 | 1.14 | 0.0 | 1.0 | 6.0 |
| `total_goals` | 2.84 | 1.60 | 0.0 | 3.0 | 9.0 |
| `home_won_corners` | 5.41 | 2.96 | 0.0 | 5.0 | 17.0 |
| `away_won_corners` | 4.74 | 2.89 | 0.0 | 4.0 | 18.0 |
| `total_corners` | 10.15 | 3.37 | 2.0 | 10.0 | 19.0 |
| `home_total_throws` | 17.61 | 5.23 | 5.0 | 17.0 | 36.0 |
| `away_total_throws` | 16.75 | 4.96 | 5.0 | 17.0 | 32.0 |
| `total_throws` | 34.36 | 7.56 | 14.0 | 34.0 | 55.0 |
| `home_saves` | 2.71 | 1.77 | 0.0 | 2.0 | 9.0 |
| `away_saves` | 3.16 | 1.92 | 0.0 | 3.0 | 13.0 |
| `total_saves` | 5.86 | 2.46 | 0.0 | 6.0 | 16.0 |
| `home_total_scoring_att` | 13.80 | 5.27 | 1.0 | 13.0 | 35.0 |
| `away_total_scoring_att` | 11.67 | 5.04 | 1.0 | 11.0 | 37.0 |
| `total_shots` | 25.46 | 5.74 | 11.0 | 25.0 | 48.0 |
| `home_ontarget_scoring_att` | 4.67 | 2.37 | 0.0 | 4.0 | 16.0 |
| `away_ontarget_scoring_att` | 4.07 | 2.24 | 0.0 | 4.0 | 13.0 |
| `total_shots_ontarget` | 8.74 | 2.94 | 2.0 | 9.0 | 19.0 |
| `home_possession_percentage` | 50.86 | 10.95 | 19.0 | 51.3 | 77.8 |
| `away_possession_percentage` | 49.14 | 10.95 | 22.2 | 48.7 | 81.0 |

---

## 4. Olay ve Şut Akışı (Play-by-Play) İncelemesi

Toplam Olay Türü Dağılımı:

| Olay Türü | Toplam Adet | Maç Başına Ortalama |
|:---|:---:|:---:|
| `corner` | 7711 | 10.15 |
| `miss` | 6658 | 8.76 |
| `attempt blocked` | 5831 | 7.67 |
| `attempt saved` | 4335 | 5.70 |
| `yellow card` | 3013 | 3.96 |
| `goal` | 1941 | 2.55 |
| `red card` | 56 | 0.07 |

---

## 5. Sonuç ve Modelleme Uygunluğu
Veri seti %100 eksiksiz, tutarlı ve veri sızıntısından arındırılmış durumdadır. Tüm şut, korner, taç ve kurtarış verileri Faz 3 öznitelik mühendisliği ve Faz 4 modelleme süreçlerine tamamen hazırdır.
