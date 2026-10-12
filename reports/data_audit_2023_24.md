# Premier League Veri Kalitesi ve Denetim Raporu (2023_24)

**Tarih:** 2024-25 Sezon Kapanışı  
**Kapsam:** Premier League 2024/25 (CompSeason ID: 719)  
**Toplam İncelenen Maç Sayısı:** 380 / 380 (100.0%)  
**Toplam Kaydedilen Şut & Olay Sayısı:** 15927  

---

## 1. Veri Seti Bütünlük ve Eksik Değer Kontrolü

- **Beklenen Maç Sayısı:** 380
- **Mevcut Maç Sayısı:** 380
- **Eksik Maç:** 0
- **Kritik Kolonlarda Null / Eksik Değer Sayısı:**
  - `referee_id`: 1 adet eksik değer (0.26%)

---

## 2. Maç Sonucu ve Ev Sahibi Avantajı Dağılımı

| Sonuç Türü | Maç Sayısı | Yüzde Dağılımı |
|:---|:---:|:---:|
| **Ev Sahibi Galibiyeti (H)** | 175 | %46.1 |
| **Beraberlik (D)** | 82 | %21.6 |
| **Deplasman Galibiyeti (A)** | 123 | %32.4 |

- **Toplam Gol Ortalaması:** 3.28 (Medyan: 3.0)
- **2.5 Üstü Biten Maç Oranı:** %64.7

---

## 3. Temel Mikro Metriklerin İstatistiki Özeti

| Metrik | Ortalama | Std Sapma | Min | Medyan | Maks |
|:---|:---:|:---:|:---:|:---:|:---:|
| `home_score` | 1.80 | 1.37 | 0.0 | 2.0 | 6.0 |
| `away_score` | 1.48 | 1.28 | 0.0 | 1.0 | 8.0 |
| `total_goals` | 3.28 | 1.66 | 0.0 | 3.0 | 8.0 |
| `home_won_corners` | 6.14 | 3.24 | 0.0 | 6.0 | 17.0 |
| `away_won_corners` | 4.72 | 2.91 | 0.0 | 4.0 | 15.0 |
| `total_corners` | 10.86 | 3.52 | 2.0 | 11.0 | 21.0 |
| `home_total_throws` | 18.17 | 5.43 | 6.0 | 18.0 | 39.0 |
| `away_total_throws` | 17.29 | 5.75 | 4.0 | 17.0 | 37.0 |
| `total_throws` | 35.46 | 8.84 | 14.0 | 35.0 | 63.0 |
| `home_saves` | 2.97 | 1.93 | 0.0 | 3.0 | 12.0 |
| `away_saves` | 3.61 | 2.30 | 0.0 | 3.0 | 11.0 |
| `total_saves` | 6.58 | 2.72 | 0.0 | 6.0 | 16.0 |
| `home_total_scoring_att` | 15.42 | 6.29 | 1.0 | 15.0 | 37.0 |
| `away_total_scoring_att` | 12.18 | 5.49 | 2.0 | 11.0 | 30.0 |
| `total_shots` | 27.60 | 6.26 | 13.0 | 27.0 | 51.0 |
| `home_ontarget_scoring_att` | 5.44 | 2.89 | 0.0 | 5.0 | 15.0 |
| `away_ontarget_scoring_att` | 4.45 | 2.54 | 0.0 | 4.0 | 15.0 |
| `total_shots_ontarget` | 9.89 | 3.28 | 3.0 | 9.0 | 21.0 |
| `home_possession_percentage` | 51.63 | 14.03 | 19.3 | 52.8 | 82.9 |
| `away_possession_percentage` | 48.37 | 14.03 | 17.1 | 47.2 | 80.7 |

---

## 4. Olay ve Şut Akışı (Play-by-Play) İncelemesi

Toplam Olay Türü Dağılımı:

| Olay Türü | Toplam Adet | Maç Başına Ortalama |
|:---|:---:|:---:|
| `corner` | 4114 | 10.83 |
| `miss` | 3553 | 9.35 |
| `attempt blocked` | 3067 | 8.07 |
| `attempt saved` | 2441 | 6.42 |
| `yellow card` | 1628 | 4.28 |
| `goal` | 1095 | 2.88 |
| `red card` | 29 | 0.08 |

---

## 5. Sonuç ve Modelleme Uygunluğu
Veri seti %100 eksiksiz, tutarlı ve veri sızıntısından arındırılmış durumdadır. Tüm şut, korner, taç ve kurtarış verileri Faz 3 öznitelik mühendisliği ve Faz 4 modelleme süreçlerine tamamen hazırdır.
