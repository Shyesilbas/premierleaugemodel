# Skor Durumu ve Korner Analizi — Veri Doğrulaması

Snapshot generated 2026-10-25 from cached event streams and raw team stats.

Bu denetim play-by-play akışını maç ve takım istatistikleriyle karşılaştırır.

## Olay akışı kapsamı

| Sezon | Maç akışı bulunan maç |
|---|---:|
| 2022-23 | 380 |
| 2023-24 | 380 |
| 2024-25 | 380 |
| 2025-26 | 380 |
| 2026-27 | 80 |

- Son skor, olay akışı bulunan **1600/1600** maçta gol olaylarından yeniden kuruldu.
- 41661 şut olayı ve 16450 korner olayı okundu.
- Saat bilgisi olmayan aksiyon: 0.

## Ham maç istatistikleriyle eşleşme

| Kontrol | Eşleşen takım-maç | Karşılaştırılan takım-maç |
|---|---:|---:|
| Play-by-play şut sayısı = `total_scoring_att` | 3192 | 3200 |
| Play-by-play korner sayısı = `won_corners` | 3126 | 3132 |

## Yorum ve sınırlar

- Skor durumu, her gol olayında metinde yazan skor kullanılarak sonraki aksiyonlar için güncellenir. Böylece şut ve kornerler eşitlikte, öndeyken veya gerideyken sayılabilir.
- Tempo, olay sayısının ilgili skor durumunda geçen oyun dakikasına bölünüp 90 dakikaya ölçeklenmesiyle hesaplanır. Bir skor durumu için 90 dakikadan az örnek varsa arayüz oranı gizler.
- Ham `won_corners` sayısı 3126/3132 karşılaştırılan takım-maçta olay akışıyla eşleşti. `corner_taken` ve korner isabet alt ölçüleri daha az tutarlı; ilk analiz bunlara dayandırılmaz.
- İşlenmiş eğitim hedefinde, ham `won_corners` eksikse takım adı olay akışından eşleşen korner sayısı kullanılır; `_raw`, `_reported` ve `_event_reconstructed` alanları kaynak ve kurtarma durumunu ayrı tutar.
- Korner olayında hedef koordinatı bulunmadığından ön direk/arka direk tercihi çıkarılmaz.
