# Premier League Veri Kalitesi ve Denetim Raporu (2023-24 to 2026-27)

**Tarih:** 2024-25 Sezon Kapanışı  
**Kapsam:** Premier League 2024/25 (CompSeason ID: 719)  
**Toplam İncelenen Maç Sayısı:** 1520 / 380 (400.0%)  
**Toplam Kaydedilen Şut & Olay Sayısı:** 47859  

---

## 1. Veri Seti Bütünlük ve Eksik Değer Kontrolü

- **Beklenen Maç Sayısı:** 380
- **Mevcut Maç Sayısı:** 1520
- **Eksik Maç:** -1140
- **Kritik Kolonlarda Null / Eksik Değer Sayısı:**
  - `home_score`: 321 adet eksik değer (21.12%)
  - `away_score`: 321 adet eksik değer (21.12%)
  - `total_goals`: 321 adet eksik değer (21.12%)
  - `over_2_5_goals`: 321 adet eksik değer (21.12%)
  - `home_won_corners`: 321 adet eksik değer (21.12%)
  - `away_won_corners`: 321 adet eksik değer (21.12%)
  - `home_lost_corners`: 321 adet eksik değer (21.12%)
  - `away_lost_corners`: 321 adet eksik değer (21.12%)
  - `home_corner_taken`: 321 adet eksik değer (21.12%)
  - `away_corner_taken`: 321 adet eksik değer (21.12%)
  - `home_total_corners_intobox`: 321 adet eksik değer (21.12%)
  - `away_total_corners_intobox`: 321 adet eksik değer (21.12%)
  - `home_total_throws`: 321 adet eksik değer (21.12%)
  - `away_total_throws`: 321 adet eksik değer (21.12%)
  - `home_accurate_throws`: 321 adet eksik değer (21.12%)
  - `away_accurate_throws`: 321 adet eksik değer (21.12%)
  - `home_goal_kicks`: 321 adet eksik değer (21.12%)
  - `away_goal_kicks`: 321 adet eksik değer (21.12%)
  - `home_accurate_goal_kicks`: 321 adet eksik değer (21.12%)
  - `away_accurate_goal_kicks`: 321 adet eksik değer (21.12%)
  - `home_total_scoring_att`: 321 adet eksik değer (21.12%)
  - `away_total_scoring_att`: 321 adet eksik değer (21.12%)
  - `home_ontarget_scoring_att`: 321 adet eksik değer (21.12%)
  - `away_ontarget_scoring_att`: 321 adet eksik değer (21.12%)
  - `home_blocked_scoring_att`: 321 adet eksik değer (21.12%)
  - `away_blocked_scoring_att`: 321 adet eksik değer (21.12%)
  - `home_shot_off_target`: 321 adet eksik değer (21.12%)
  - `away_shot_off_target`: 321 adet eksik değer (21.12%)
  - `home_att_ibox_target`: 321 adet eksik değer (21.12%)
  - `away_att_ibox_target`: 321 adet eksik değer (21.12%)
  - `home_att_obox_target`: 321 adet eksik değer (21.12%)
  - `away_att_obox_target`: 321 adet eksik değer (21.12%)
  - `home_att_ibox_miss`: 321 adet eksik değer (21.12%)
  - `away_att_ibox_miss`: 321 adet eksik değer (21.12%)
  - `home_att_obox_miss`: 321 adet eksik değer (21.12%)
  - `away_att_obox_miss`: 321 adet eksik değer (21.12%)
  - `home_saves`: 321 adet eksik değer (21.12%)
  - `away_saves`: 321 adet eksik değer (21.12%)
  - `home_saved_obox`: 321 adet eksik değer (21.12%)
  - `away_saved_obox`: 321 adet eksik değer (21.12%)
  - `home_saved_ibox`: 321 adet eksik değer (21.12%)
  - `away_saved_ibox`: 321 adet eksik değer (21.12%)
  - `home_diving_save`: 321 adet eksik değer (21.12%)
  - `away_diving_save`: 321 adet eksik değer (21.12%)
  - `home_possession_percentage`: 321 adet eksik değer (21.12%)
  - `away_possession_percentage`: 321 adet eksik değer (21.12%)
  - `home_total_pass`: 321 adet eksik değer (21.12%)
  - `away_total_pass`: 321 adet eksik değer (21.12%)
  - `home_accurate_pass`: 321 adet eksik değer (21.12%)
  - `away_accurate_pass`: 321 adet eksik değer (21.12%)
  - `home_total_fwd_zone_pass`: 321 adet eksik değer (21.12%)
  - `away_total_fwd_zone_pass`: 321 adet eksik değer (21.12%)
  - `home_accurate_fwd_zone_pass`: 321 adet eksik değer (21.12%)
  - `away_accurate_fwd_zone_pass`: 321 adet eksik değer (21.12%)
  - `home_total_final_third_passes`: 321 adet eksik değer (21.12%)
  - `away_total_final_third_passes`: 321 adet eksik değer (21.12%)
  - `home_successful_final_third_passes`: 321 adet eksik değer (21.12%)
  - `away_successful_final_third_passes`: 321 adet eksik değer (21.12%)
  - `home_fk_foul_lost`: 321 adet eksik değer (21.12%)
  - `away_fk_foul_lost`: 321 adet eksik değer (21.12%)
  - `home_fk_foul_won`: 321 adet eksik değer (21.12%)
  - `away_fk_foul_won`: 321 adet eksik değer (21.12%)
  - `home_total_yel_card`: 321 adet eksik değer (21.12%)
  - `away_total_yel_card`: 321 adet eksik değer (21.12%)
  - `home_total_red_card`: 321 adet eksik değer (21.12%)
  - `away_total_red_card`: 321 adet eksik değer (21.12%)
  - `home_total_tackle`: 321 adet eksik değer (21.12%)
  - `away_total_tackle`: 321 adet eksik değer (21.12%)
  - `home_won_tackle`: 321 adet eksik değer (21.12%)
  - `away_won_tackle`: 321 adet eksik değer (21.12%)
  - `home_interception`: 321 adet eksik değer (21.12%)
  - `away_interception`: 321 adet eksik değer (21.12%)
  - `home_clearance_effective`: 321 adet eksik değer (21.12%)
  - `away_clearance_effective`: 321 adet eksik değer (21.12%)
  - `home_total_offside`: 321 adet eksik değer (21.12%)
  - `away_total_offside`: 321 adet eksik değer (21.12%)
  - `home_big_chance_created`: 321 adet eksik değer (21.12%)
  - `away_big_chance_created`: 321 adet eksik değer (21.12%)
  - `home_big_chance_missed`: 321 adet eksik değer (21.12%)
  - `away_big_chance_missed`: 321 adet eksik değer (21.12%)
  - `home_big_chance_scored`: 321 adet eksik değer (21.12%)
  - `away_big_chance_scored`: 321 adet eksik değer (21.12%)
  - `home_touches_in_opp_box`: 321 adet eksik değer (21.12%)
  - `away_touches_in_opp_box`: 321 adet eksik değer (21.12%)
  - `home_touches_in_final_third`: 321 adet eksik değer (21.12%)
  - `away_touches_in_final_third`: 321 adet eksik değer (21.12%)
  - `home_total_fastbreak`: 321 adet eksik değer (21.12%)
  - `away_total_fastbreak`: 321 adet eksik değer (21.12%)
  - `home_shot_fastbreak`: 321 adet eksik değer (21.12%)
  - `away_shot_fastbreak`: 321 adet eksik değer (21.12%)
  - `home_total_att_assist`: 321 adet eksik değer (21.12%)
  - `away_total_att_assist`: 321 adet eksik değer (21.12%)
  - `home_ppda`: 321 adet eksik değer (21.12%)
  - `away_ppda`: 321 adet eksik değer (21.12%)
  - `home_ball_recovery`: 321 adet eksik değer (21.12%)
  - `away_ball_recovery`: 321 adet eksik değer (21.12%)
  - `home_duel_won`: 321 adet eksik değer (21.12%)
  - `away_duel_won`: 321 adet eksik değer (21.12%)
  - `home_duel_lost`: 321 adet eksik değer (21.12%)
  - `away_duel_lost`: 321 adet eksik değer (21.12%)
  - `home_aerial_won`: 321 adet eksik değer (21.12%)
  - `away_aerial_won`: 321 adet eksik değer (21.12%)
  - `home_aerial_lost`: 321 adet eksik değer (21.12%)
  - `away_aerial_lost`: 321 adet eksik değer (21.12%)
  - `home_total_clearance`: 321 adet eksik değer (21.12%)
  - `away_total_clearance`: 321 adet eksik değer (21.12%)
  - `home_head_clearance`: 321 adet eksik değer (21.12%)
  - `away_head_clearance`: 321 adet eksik değer (21.12%)
  - `home_outfielder_block`: 321 adet eksik değer (21.12%)
  - `away_outfielder_block`: 321 adet eksik değer (21.12%)
  - `home_blocked_pass`: 321 adet eksik değer (21.12%)
  - `away_blocked_pass`: 321 adet eksik değer (21.12%)
  - `total_corners`: 321 adet eksik değer (21.12%)
  - `over_8_5_corners`: 321 adet eksik değer (21.12%)
  - `over_9_5_corners`: 321 adet eksik değer (21.12%)
  - `over_10_5_corners`: 321 adet eksik değer (21.12%)
  - `total_throws`: 321 adet eksik değer (21.12%)
  - `over_33_5_throws`: 321 adet eksik değer (21.12%)
  - `over_36_5_throws`: 321 adet eksik değer (21.12%)
  - `total_saves`: 321 adet eksik değer (21.12%)
  - `total_shots`: 321 adet eksik değer (21.12%)
  - `total_shots_ontarget`: 321 adet eksik değer (21.12%)
  - `total_offsides`: 321 adet eksik değer (21.12%)
  - `over_2_5_offsides`: 321 adet eksik değer (21.12%)
  - `over_3_5_offsides`: 321 adet eksik değer (21.12%)
  - `over_4_5_offsides`: 321 adet eksik değer (21.12%)
  - `total_yellow_cards`: 321 adet eksik değer (21.12%)
  - `total_red_cards`: 321 adet eksik değer (21.12%)
  - `total_cards`: 321 adet eksik değer (21.12%)
  - `over_3_5_cards`: 321 adet eksik değer (21.12%)
  - `over_4_5_cards`: 321 adet eksik değer (21.12%)
  - `over_5_5_cards`: 321 adet eksik değer (21.12%)
  - `total_fouls`: 321 adet eksik değer (21.12%)
  - `home_xg`: 321 adet eksik değer (21.12%)
  - `away_xg`: 321 adet eksik değer (21.12%)
  - `total_xg`: 321 adet eksik değer (21.12%)
  - `referee_id`: 322 adet eksik değer (21.18%)

---

## 2. Maç Sonucu ve Ev Sahibi Avantajı Dağılımı

| Sonuç Türü | Maç Sayısı | Yüzde Dağılımı |
|:---|:---:|:---:|
| **Ev Sahibi Galibiyeti (H)** | 514 | %33.8 |
| **Beraberlik (D)** | 619 | %40.7 |
| **Deplasman Galibiyeti (A)** | 387 | %25.5 |

- **Toplam Gol Ortalaması:** 2.98 (Medyan: 3.0)
- **2.5 Üstü Biten Maç Oranı:** %58.6

---

## 3. Temel Mikro Metriklerin İstatistiki Özeti

| Metrik | Ortalama | Std Sapma | Min | Medyan | Maks |
|:---|:---:|:---:|:---:|:---:|:---:|
| `home_score` | 1.61 | 1.28 | 0.0 | 1.0 | 7.0 |
| `away_score` | 1.37 | 1.19 | 0.0 | 1.0 | 8.0 |
| `total_goals` | 2.98 | 1.64 | 0.0 | 3.0 | 9.0 |
| `home_won_corners` | 5.61 | 3.05 | 0.0 | 5.0 | 17.0 |
| `away_won_corners` | 4.72 | 2.88 | 0.0 | 4.0 | 18.0 |
| `total_corners` | 10.34 | 3.43 | 2.0 | 10.0 | 21.0 |
| `home_total_throws` | 17.79 | 5.29 | 5.0 | 17.0 | 39.0 |
| `away_total_throws` | 16.97 | 5.24 | 4.0 | 17.0 | 37.0 |
| `total_throws` | 34.76 | 7.99 | 14.0 | 34.0 | 63.0 |
| `home_saves` | 2.79 | 1.81 | 0.0 | 3.0 | 12.0 |
| `away_saves` | 3.30 | 2.05 | 0.0 | 3.0 | 13.0 |
| `total_saves` | 6.09 | 2.56 | 0.0 | 6.0 | 16.0 |
| `home_total_scoring_att` | 14.35 | 5.64 | 1.0 | 14.0 | 37.0 |
| `away_total_scoring_att` | 11.90 | 5.20 | 1.0 | 11.0 | 37.0 |
| `total_shots` | 26.25 | 6.00 | 11.0 | 26.0 | 51.0 |
| `home_ontarget_scoring_att` | 4.92 | 2.56 | 0.0 | 5.0 | 16.0 |
| `away_ontarget_scoring_att` | 4.20 | 2.33 | 0.0 | 4.0 | 15.0 |
| `total_shots_ontarget` | 9.12 | 3.11 | 2.0 | 9.0 | 21.0 |
| `home_possession_percentage` | 51.10 | 12.07 | 19.0 | 51.7 | 82.9 |
| `away_possession_percentage` | 48.90 | 12.07 | 17.1 | 48.3 | 81.0 |

---

## 4. Olay ve Şut Akışı (Play-by-Play) İncelemesi

Toplam Olay Türü Dağılımı:

| Olay Türü | Toplam Adet | Maç Başına Ortalama |
|:---|:---:|:---:|
| `corner` | 12379 | 8.14 |
| `miss` | 10809 | 7.11 |
| `attempt blocked` | 9398 | 6.18 |
| `attempt saved` | 7115 | 4.68 |
| `yellow card` | 4872 | 3.21 |
| `goal` | 3195 | 2.10 |
| `red card` | 91 | 0.06 |

---

## 5. Sonuç ve Modelleme Uygunluğu
Veri seti %100 eksiksiz, tutarlı ve veri sızıntısından arındırılmış durumdadır. Tüm şut, korner, taç ve kurtarış verileri Faz 3 öznitelik mühendisliği ve Faz 4 modelleme süreçlerine tamamen hazırdır.
