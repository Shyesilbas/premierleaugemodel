# Skor Durumu ve Korner Analizi — Veri Doğrulaması

Bu denetim play-by-play akışını maç ve takım istatistikleriyle karşılaştırır.

## Olay akışı kapsamı

| Sezon | Maç akışı bulunan maç |
|---|---:|
| 2023-24 | 379 |
| 2024-25 | 380 |
| 2025-26 | 380 |
| 2026-27 | 59 |

- Son skor **1198/1198** maçta gol olaylarından yeniden kuruldu.
- 31445 şut olayı ve 12379 korner olayı okundu.
- Saat bilgisi olmayan aksiyon: 0.

## Ham maç istatistikleriyle eşleşme

| Kontrol | Eşleşen takım-maç | Karşılaştırılan takım-maç |
|---|---:|---:|
| Play-by-play şut sayısı = `total_scoring_att` | 2396 | 2396 |
| Play-by-play korner sayısı = `won_corners` | 2342 | 2342 |

## Yorum ve sınırlar

- Skor durumu, her gol olayında metinde yazan skor kullanılarak sonraki aksiyonlar için güncellenir. Böylece şut ve kornerler eşitlikte, öndeyken veya gerideyken sayılabilir.
- Tempo, olay sayısının ilgili skor durumunda geçen oyun dakikasına bölünüp 90 dakikaya ölçeklenmesiyle hesaplanır. Bir skor durumu için 90 dakikadan az örnek varsa arayüz oranı gizler.
- Ham `won_corners` sayısı olay akışıyla karşılaştırılan 2342 takım-maçın tamamında eşleşti. `corner_taken` ve korner isabet alt ölçüleri daha az tutarlı; ilk analiz bunlara dayandırılmaz.
- Korner olayında hedef koordinatı bulunmadığından ön direk/arka direk tercihi çıkarılmaz.
