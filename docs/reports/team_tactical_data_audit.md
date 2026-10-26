# Takım Taktik Analizi — Veri Kapsamı Denetimi

Snapshot generated 2026-10-25 from cached raw provider responses.

Bu rapor `data/competitions/premier_league/raw/matches/*_stats.json` dosyalarındaki takım düzeyi `M` istatistiklerini inceler. Bir metriğin dosyada bulunmaması sıfır kabul edilmez.

## Sezon kapsamı

| Sezon | İstatistik dosyası olan maç | Takım-maç satırı | Farklı metrik adı |
|---|---:|---:|---:|
| 2022-23 | 380 | 760 | 239 |
| 2023-24 | 380 | 760 | 253 |
| 2024-25 | 380 | 760 | 251 |
| 2025-26 | 380 | 760 | 257 |
| 2026-27 | 80 | 160 | 254 |

Tüm sezonlarda toplam **259 farklı metrik adı** bulundu. 2026-27 sezonu tamamlanmış sezonlarla aynı örneklem gibi değerlendirilmemelidir.

## Candidate metric coverage

Kapsama, ilgili sezondaki takım-maç satırlarında metriğin sayısal değerinin bulunma oranıdır. Parantez içindeki değer, mevcut ve sıfır olmayan değerlerin sayısını gösterir.

| Grup | Metrik | Sezon | Değer bulunan satır | Kapsama | Açıkça sıfır |
|---|---|---|---:|---:|---:|
| Topa sahip olma ve ilerleme | `possession_percentage` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2022-23 | 743/760 (743 sıfır olmayan) | 97.8% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2023-24 | 738/760 (738 sıfır olmayan) | 97.1% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2024-25 | 729/760 (729 sıfır olmayan) | 95.9% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2025-26 | 726/760 (726 sıfır olmayan) | 95.5% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2026-27 | 150/160 (150 sıfır olmayan) | 93.8% | 0 |
| Şut | `total_scoring_att` | 2022-23 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Şut | `attempts_ibox` | 2022-23 | 758/760 (758 sıfır olmayan) | 99.7% | 0 |
| Şut | `attempts_ibox` | 2023-24 | 759/760 (759 sıfır olmayan) | 99.9% | 0 |
| Şut | `attempts_ibox` | 2024-25 | 758/760 (758 sıfır olmayan) | 99.7% | 0 |
| Şut | `attempts_ibox` | 2025-26 | 759/760 (759 sıfır olmayan) | 99.9% | 0 |
| Şut | `attempts_ibox` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Şut | `attempts_obox` | 2022-23 | 737/760 (737 sıfır olmayan) | 97.0% | 0 |
| Şut | `attempts_obox` | 2023-24 | 734/760 (734 sıfır olmayan) | 96.6% | 0 |
| Şut | `attempts_obox` | 2024-25 | 729/760 (729 sıfır olmayan) | 95.9% | 0 |
| Şut | `attempts_obox` | 2025-26 | 734/760 (734 sıfır olmayan) | 96.6% | 0 |
| Şut | `attempts_obox` | 2026-27 | 157/160 (157 sıfır olmayan) | 98.1% | 0 |
| Şut | `att_obox_target` | 2022-23 | 458/760 (458 sıfır olmayan) | 60.3% | 0 |
| Şut | `att_obox_target` | 2023-24 | 488/760 (488 sıfır olmayan) | 64.2% | 0 |
| Şut | `att_obox_target` | 2024-25 | 428/760 (428 sıfır olmayan) | 56.3% | 0 |
| Şut | `att_obox_target` | 2025-26 | 427/760 (427 sıfır olmayan) | 56.2% | 0 |
| Şut | `att_obox_target` | 2026-27 | 91/160 (91 sıfır olmayan) | 56.9% | 0 |
| Şut | `att_obox_blocked` | 2022-23 | 546/760 (546 sıfır olmayan) | 71.8% | 0 |
| Şut | `att_obox_blocked` | 2023-24 | 547/760 (547 sıfır olmayan) | 72.0% | 0 |
| Şut | `att_obox_blocked` | 2024-25 | 553/760 (553 sıfır olmayan) | 72.8% | 0 |
| Şut | `att_obox_blocked` | 2025-26 | 562/760 (562 sıfır olmayan) | 73.9% | 0 |
| Şut | `att_obox_blocked` | 2026-27 | 119/160 (119 sıfır olmayan) | 74.4% | 0 |
| Şut | `att_obox_miss` | 2022-23 | 574/760 (574 sıfır olmayan) | 75.5% | 0 |
| Şut | `att_obox_miss` | 2023-24 | 597/760 (597 sıfır olmayan) | 78.6% | 0 |
| Şut | `att_obox_miss` | 2024-25 | 582/760 (582 sıfır olmayan) | 76.6% | 0 |
| Şut | `att_obox_miss` | 2025-26 | 595/760 (595 sıfır olmayan) | 78.3% | 0 |
| Şut | `att_obox_miss` | 2026-27 | 133/160 (133 sıfır olmayan) | 83.1% | 0 |
| Korner ve duran top | `won_corners` | 2022-23 | 747/760 (747 sıfır olmayan) | 98.3% | 0 |
| Korner ve duran top | `won_corners` | 2023-24 | 742/760 (742 sıfır olmayan) | 97.6% | 0 |
| Korner ve duran top | `won_corners` | 2024-25 | 736/760 (736 sıfır olmayan) | 96.8% | 0 |
| Korner ve duran top | `won_corners` | 2025-26 | 749/760 (749 sıfır olmayan) | 98.6% | 0 |
| Korner ve duran top | `won_corners` | 2026-27 | 158/160 (158 sıfır olmayan) | 98.8% | 0 |
| Korner ve duran top | `corner_taken` | 2022-23 | 747/760 (747 sıfır olmayan) | 98.3% | 0 |
| Korner ve duran top | `corner_taken` | 2023-24 | 742/760 (742 sıfır olmayan) | 97.6% | 0 |
| Korner ve duran top | `corner_taken` | 2024-25 | 736/760 (736 sıfır olmayan) | 96.8% | 0 |
| Korner ve duran top | `corner_taken` | 2025-26 | 749/760 (749 sıfır olmayan) | 98.6% | 0 |
| Korner ve duran top | `corner_taken` | 2026-27 | 158/160 (158 sıfır olmayan) | 98.8% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2022-23 | 735/760 (735 sıfır olmayan) | 96.7% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2023-24 | 732/760 (732 sıfır olmayan) | 96.3% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2024-25 | 724/760 (724 sıfır olmayan) | 95.3% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2025-26 | 738/760 (738 sıfır olmayan) | 97.1% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2026-27 | 158/160 (158 sıfır olmayan) | 98.8% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2022-23 | 531/760 (531 sıfır olmayan) | 69.9% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2023-24 | 538/760 (538 sıfır olmayan) | 70.8% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2024-25 | 508/760 (508 sıfır olmayan) | 66.8% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2025-26 | 529/760 (529 sıfır olmayan) | 69.6% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2026-27 | 105/160 (105 sıfır olmayan) | 65.6% | 0 |
| Korner ve duran top | `att_corner` | 2022-23 | 605/760 (605 sıfır olmayan) | 79.6% | 0 |
| Korner ve duran top | `att_corner` | 2023-24 | 640/760 (640 sıfır olmayan) | 84.2% | 0 |
| Korner ve duran top | `att_corner` | 2024-25 | 603/760 (603 sıfır olmayan) | 79.3% | 0 |
| Korner ve duran top | `att_corner` | 2025-26 | 622/760 (622 sıfır olmayan) | 81.8% | 0 |
| Korner ve duran top | `att_corner` | 2026-27 | 128/160 (128 sıfır olmayan) | 80.0% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2022-23 | 515/760 (515 sıfır olmayan) | 67.8% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2023-24 | 515/760 (515 sıfır olmayan) | 67.8% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2024-25 | 488/760 (488 sıfır olmayan) | 64.2% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2025-26 | 483/760 (483 sıfır olmayan) | 63.6% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2026-27 | 108/160 (108 sıfır olmayan) | 67.5% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2022-23 | 0/760 (0 sıfır olmayan) | 0.0% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2022-23 | 0/760 (0 sıfır olmayan) | 0.0% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2025-26 | 320/760 (320 sıfır olmayan) | 42.1% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2026-27 | 154/160 (154 sıfır olmayan) | 96.2% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2022-23 | 0/760 (0 sıfır olmayan) | 0.0% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2025-26 | 320/760 (320 sıfır olmayan) | 42.1% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2026-27 | 154/160 (154 sıfır olmayan) | 96.2% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2022-23 | 0/760 (0 sıfır olmayan) | 0.0% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2025-26 | 170/760 (170 sıfır olmayan) | 22.4% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2026-27 | 160/160 (160 sıfır olmayan) | 100.0% | 0 |

## Findings and limits

- İleri/geri bölge pasları, son üç bölgeye girişler ve orta bölge top kazanımı ana karşılaştırma setine adaydır; sezonlar arası kapsama ayrıca yukarıdaki tabloda gösterilir.
- Şut bölgesi toplamı, iki alanın da bulunduğu 3085 takım-maçın 3085'inde `attempts_ibox + attempts_obox = total_scoring_att` eşitliğini sağladı (0 tutarsızlık). Bir taraf eksik ve diğer taraf toplam şuta eşitse eksik taraf güvenle sıfır alınabilir; 0 satır çözümsüz kaldı.
- Ceza sahası dışı şut payı, yalnızca doğrulanmış şut bölgesi satırlarından hesaplanır; uzaktan isabet/blok/kaçan şut alt metrikleri belirgin biçimde daha seyrek olduğu için ilk sürümde kullanılmaz.
- PPDA, top sürme ve açık oyunda ceza sahasına giriş metrikleri sezonlara göre değişken kapsamalıdır; kapsama denetimi yapılmadan çok sezonlu sıralamalara katılmamalıdır.
- `total_corners_intobox / won_corners`, ceza sahasına gönderilen kornerlerin kullanılan kornerlere oranı olarak hesaplanabilir; bu, kısa korner veya hedef bölge bilgisini vermez.
- `accurate_corners_intobox` pozitif `total_corners_intobox` değerleri varken de sıkça eksiktir; eksik değerleri sıfır varsayarak isabet oranı hesaplanmamalıdır.
- İşlenmiş Parquet dosyaları artık kaynakta bulunmayan metrikleri null ve ayrı `_reported` bayraklarıyla saklar. Önceki sıfır doldurma davranışıyla üretilmiş eski tablolar bu kapsama uymayabilir; tam pipeline yeniden çalıştırılmalıdır.

## Yöntem notu

Bu denetim metrik tanımlarının anlamsal doğruluğunu kanıtlamaz; ham dosyalardaki sayısal değer kapsamasını ve temel şut bölgesi eşitliğini ölçer. Ham alanın yokluğu yalnızca eşitlik koşulu sağlandığında sıfır olarak yorumlanır.
