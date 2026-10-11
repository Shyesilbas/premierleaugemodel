# Premier League Veri Kalitesi ve Denetim Raporu (2025_26)

**Tarih:** 2024-25 Sezon Kapanışı  
**Kapsam:** Premier League 2024/25 (CompSeason ID: 719)  
**Toplam İncelenen Maç Sayısı:** 380 / 380 (100.0%)  
**Toplam Kaydedilen Şut & Olay Sayısı:** 14469  

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
| **Ev Sahibi Galibiyeti (H)** | 162 | %42.6 |
| **Beraberlik (D)** | 104 | %27.4 |
| **Deplasman Galibiyeti (A)** | 114 | %30.0 |

- **Toplam Gol Ortalaması:** 2.75 (Medyan: 3.0)
- **2.5 Üstü Biten Maç Oranı:** %55.0

---

## 3. Temel Mikro Metriklerin İstatistiki Özeti

| Metrik | Ortalama | Std Sapma | Min | Medyan | Maks |
|:---|:---:|:---:|:---:|:---:|:---:|
| `home_score` | 1.53 | 1.17 | 0.0 | 1.0 | 5.0 |
| `away_score` | 1.22 | 1.08 | 0.0 | 1.0 | 5.0 |
| `total_goals` | 2.75 | 1.57 | 0.0 | 3.0 | 9.0 |
| `home_won_corners` | 5.39 | 2.73 | 0.0 | 5.0 | 14.0 |
| `away_won_corners` | 4.60 | 2.75 | 0.0 | 4.0 | 15.0 |
| `total_corners` | 10.00 | 3.27 | 3.0 | 10.0 | 19.0 |
| `home_total_throws` | 18.45 | 5.19 | 5.0 | 18.0 | 34.0 |
| `away_total_throws` | 17.38 | 4.62 | 6.0 | 17.0 | 31.0 |
| `total_throws` | 35.83 | 7.20 | 16.0 | 36.0 | 53.0 |
| `home_saves` | 2.59 | 1.69 | 0.0 | 2.0 | 9.0 |
| `away_saves` | 2.98 | 1.77 | 0.0 | 3.0 | 10.0 |
| `total_saves` | 5.57 | 2.30 | 0.0 | 5.0 | 13.0 |
| `home_total_scoring_att` | 13.84 | 4.94 | 1.0 | 14.0 | 35.0 |
| `away_total_scoring_att` | 11.17 | 4.58 | 3.0 | 11.0 | 30.0 |
| `total_shots` | 25.01 | 5.43 | 11.0 | 25.0 | 42.0 |
| `home_ontarget_scoring_att` | 4.51 | 2.24 | 0.0 | 4.0 | 11.0 |
| `away_ontarget_scoring_att` | 3.88 | 2.11 | 0.0 | 4.0 | 11.0 |
| `total_shots_ontarget` | 8.38 | 2.84 | 2.0 | 8.0 | 18.0 |
| `home_possession_percentage` | 50.73 | 10.68 | 19.0 | 51.1 | 76.2 |
| `away_possession_percentage` | 49.27 | 10.68 | 23.8 | 48.9 | 81.0 |

---

## 4. Olay ve Şut Akışı (Play-by-Play) İncelemesi

Toplam Olay Türü Dağılımı:

| Olay Türü | Toplam Adet | Maç Başına Ortalama |
|:---|:---:|:---:|
| `corner` | 3799 | 10.00 |
| `miss` | 3307 | 8.70 |
| `attempt blocked` | 2904 | 7.64 |
| `attempt saved` | 2063 | 5.43 |
| `yellow card` | 1438 | 3.78 |
| `goal` | 928 | 2.44 |
| `red card` | 30 | 0.08 |

---

## 5. Sonuç ve Modelleme Uygunluğu
Veri seti %100 eksiksiz, tutarlı ve veri sızıntısından arındırılmış durumdadır. Tüm şut, korner, taç ve kurtarış verileri Faz 3 öznitelik mühendisliği ve Faz 4 modelleme süreçlerine tamamen hazırdır.
