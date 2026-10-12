# Takım Taktik Analizi — Veri Kapsamı Denetimi

Bu rapor `data/raw/matches/*_stats.json` dosyalarındaki takım düzeyi `M` istatistiklerini inceler. Bir metriğin dosyada bulunmaması sıfır kabul edilmez.

## Sezon kapsamı

| Sezon | İstatistik dosyası olan maç | Takım-maç satırı | Farklı metrik adı |
|---|---:|---:|---:|
| 2023-24 | 380 | 760 | 253 |
| 2024-25 | 380 | 760 | 251 |
| 2025-26 | 380 | 760 | 257 |
| 2026-27 | 59 | 118 | 254 |

Tüm sezonlarda toplam **257 farklı metrik adı** bulundu. 2026-27 sezonu tamamlanmış sezonlarla aynı örneklem gibi değerlendirilmemelidir.

## İlk sürüm için aday metriklerin kapsaması

Kapsama, ilgili sezondaki takım-maç satırlarında metriğin sayısal değerinin bulunma oranıdır. Parantez içindeki değer, mevcut ve sıfır olmayan değerlerin sayısını gösterir.

| Grup | Metrik | Sezon | Değer bulunan satır | Kapsama | Açıkça sıfır |
|---|---|---|---:|---:|---:|
| Topa sahip olma ve ilerleme | `possession_percentage` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `possession_percentage` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_fwd_zone_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_fwd_zone_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `total_back_zone_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `accurate_back_zone_pass` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Topa sahip olma ve ilerleme | `final_third_entries` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_def_3rd` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_mid_3rd` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2023-24 | 738/760 (738 sıfır olmayan) | 97.1% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2024-25 | 729/760 (729 sıfır olmayan) | 95.9% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2025-26 | 726/760 (726 sıfır olmayan) | 95.5% | 0 |
| Üçüncü bölgelerde top kazanımı | `poss_won_att_3rd` | 2026-27 | 112/118 (112 sıfır olmayan) | 94.9% | 0 |
| Şut | `total_scoring_att` | 2023-24 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2024-25 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Şut | `total_scoring_att` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Şut | `attempts_ibox` | 2023-24 | 759/760 (759 sıfır olmayan) | 99.9% | 0 |
| Şut | `attempts_ibox` | 2024-25 | 758/760 (758 sıfır olmayan) | 99.7% | 0 |
| Şut | `attempts_ibox` | 2025-26 | 759/760 (759 sıfır olmayan) | 99.9% | 0 |
| Şut | `attempts_ibox` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Şut | `attempts_obox` | 2023-24 | 734/760 (734 sıfır olmayan) | 96.6% | 0 |
| Şut | `attempts_obox` | 2024-25 | 729/760 (729 sıfır olmayan) | 95.9% | 0 |
| Şut | `attempts_obox` | 2025-26 | 734/760 (734 sıfır olmayan) | 96.6% | 0 |
| Şut | `attempts_obox` | 2026-27 | 116/118 (116 sıfır olmayan) | 98.3% | 0 |
| Şut | `att_obox_target` | 2023-24 | 488/760 (488 sıfır olmayan) | 64.2% | 0 |
| Şut | `att_obox_target` | 2024-25 | 428/760 (428 sıfır olmayan) | 56.3% | 0 |
| Şut | `att_obox_target` | 2025-26 | 427/760 (427 sıfır olmayan) | 56.2% | 0 |
| Şut | `att_obox_target` | 2026-27 | 67/118 (67 sıfır olmayan) | 56.8% | 0 |
| Şut | `att_obox_blocked` | 2023-24 | 547/760 (547 sıfır olmayan) | 72.0% | 0 |
| Şut | `att_obox_blocked` | 2024-25 | 553/760 (553 sıfır olmayan) | 72.8% | 0 |
| Şut | `att_obox_blocked` | 2025-26 | 562/760 (562 sıfır olmayan) | 73.9% | 0 |
| Şut | `att_obox_blocked` | 2026-27 | 90/118 (90 sıfır olmayan) | 76.3% | 0 |
| Şut | `att_obox_miss` | 2023-24 | 597/760 (597 sıfır olmayan) | 78.6% | 0 |
| Şut | `att_obox_miss` | 2024-25 | 582/760 (582 sıfır olmayan) | 76.6% | 0 |
| Şut | `att_obox_miss` | 2025-26 | 595/760 (595 sıfır olmayan) | 78.3% | 0 |
| Şut | `att_obox_miss` | 2026-27 | 101/118 (101 sıfır olmayan) | 85.6% | 0 |
| Korner ve duran top | `won_corners` | 2023-24 | 742/760 (742 sıfır olmayan) | 97.6% | 0 |
| Korner ve duran top | `won_corners` | 2024-25 | 736/760 (736 sıfır olmayan) | 96.8% | 0 |
| Korner ve duran top | `won_corners` | 2025-26 | 749/760 (749 sıfır olmayan) | 98.6% | 0 |
| Korner ve duran top | `won_corners` | 2026-27 | 117/118 (117 sıfır olmayan) | 99.2% | 0 |
| Korner ve duran top | `corner_taken` | 2023-24 | 742/760 (742 sıfır olmayan) | 97.6% | 0 |
| Korner ve duran top | `corner_taken` | 2024-25 | 736/760 (736 sıfır olmayan) | 96.8% | 0 |
| Korner ve duran top | `corner_taken` | 2025-26 | 749/760 (749 sıfır olmayan) | 98.6% | 0 |
| Korner ve duran top | `corner_taken` | 2026-27 | 117/118 (117 sıfır olmayan) | 99.2% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2023-24 | 732/760 (732 sıfır olmayan) | 96.3% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2024-25 | 724/760 (724 sıfır olmayan) | 95.3% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2025-26 | 738/760 (738 sıfır olmayan) | 97.1% | 0 |
| Korner ve duran top | `total_corners_intobox` | 2026-27 | 117/118 (117 sıfır olmayan) | 99.2% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2023-24 | 538/760 (538 sıfır olmayan) | 70.8% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2024-25 | 508/760 (508 sıfır olmayan) | 66.8% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2025-26 | 529/760 (529 sıfır olmayan) | 69.6% | 0 |
| Korner ve duran top | `accurate_corners_intobox` | 2026-27 | 75/118 (75 sıfır olmayan) | 63.6% | 0 |
| Korner ve duran top | `att_corner` | 2023-24 | 640/760 (640 sıfır olmayan) | 84.2% | 0 |
| Korner ve duran top | `att_corner` | 2024-25 | 603/760 (603 sıfır olmayan) | 79.3% | 0 |
| Korner ve duran top | `att_corner` | 2025-26 | 622/760 (622 sıfır olmayan) | 81.8% | 0 |
| Korner ve duran top | `att_corner` | 2026-27 | 93/118 (93 sıfır olmayan) | 78.8% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2023-24 | 515/760 (515 sıfır olmayan) | 67.8% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2024-25 | 488/760 (488 sıfır olmayan) | 64.2% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2025-26 | 483/760 (483 sıfır olmayan) | 63.6% | 0 |
| Korner ve duran top | `att_assist_setplay` | 2026-27 | 77/118 (77 sıfır olmayan) | 65.3% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2025-26 | 760/760 (760 sıfır olmayan) | 100.0% | 0 |
| Kapsaması sınırlı adaylar | `ppda` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2025-26 | 320/760 (320 sıfır olmayan) | 42.1% | 0 |
| Kapsaması sınırlı adaylar | `carries` | 2026-27 | 116/118 (116 sıfır olmayan) | 98.3% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2025-26 | 320/760 (320 sıfır olmayan) | 42.1% | 0 |
| Kapsaması sınırlı adaylar | `progressive_carries` | 2026-27 | 116/118 (116 sıfır olmayan) | 98.3% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2023-24 | 4/760 (4 sıfır olmayan) | 0.5% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2024-25 | 160/760 (160 sıfır olmayan) | 21.1% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2025-26 | 170/760 (170 sıfır olmayan) | 22.4% | 0 |
| Kapsaması sınırlı adaylar | `pen_area_entries_open_play` | 2026-27 | 118/118 (118 sıfır olmayan) | 100.0% | 0 |

## İlk sürüm için karar

- İleri/geri bölge pasları, son üç bölgeye girişler ve orta bölge top kazanımı ana karşılaştırma setine adaydır; sezonlar arası kapsama ayrıca yukarıdaki tabloda gösterilir.
- Şut bölgesi toplamı, iki alanın da bulunduğu 2309 takım-maçın 2309'inde `attempts_ibox + attempts_obox = total_scoring_att` eşitliğini sağladı (0 tutarsızlık). Bir taraf eksik ve diğer taraf toplam şuta eşitse eksik taraf güvenle sıfır alınabilir; 0 satır çözümsüz kaldı.
- Ceza sahası dışı şut payı, yalnızca doğrulanmış şut bölgesi satırlarından hesaplanır; uzaktan isabet/blok/kaçan şut alt metrikleri belirgin biçimde daha seyrek olduğu için ilk sürümde kullanılmaz.
- PPDA, top sürme ve açık oyunda ceza sahasına giriş metrikleri sezonlara göre değişken kapsamalıdır; kapsama denetimi yapılmadan çok sezonlu sıralamalara katılmamalıdır.
- `total_corners_intobox / won_corners`, ceza sahasına gönderilen kornerlerin kullanılan kornerlere oranı olarak hesaplanabilir; bu, kısa korner veya hedef bölge bilgisini vermez.
- `accurate_corners_intobox` pozitif `total_corners_intobox` değerleri varken de sıkça eksiktir; eksik değerleri sıfır varsayarak isabet oranı hesaplanmamalıdır.
- Özet Parquet üretiminde bulunmayan metriklerin `0` ile doldurulduğu görülüyor. Taktiksel hesaplama ham JSON değerlerini kullanmalı veya işlenmiş tabloda eksikliği korumalıdır.

## Yöntem notu

Bu denetim metrik tanımlarının anlamsal doğruluğunu kanıtlamaz; ham dosyalardaki sayısal değer kapsamasını ve temel şut bölgesi eşitliğini ölçer. Ham alanın yokluğu yalnızca eşitlik koşulu sağlandığında sıfır olarak yorumlanır.
