# Premier League Model Engine — Proje Durumu (PROJECT_STATUS)

**Son Güncelleme:** Güncel Sezon (2026-27) Oynanmış Maç Verileri, Kadrolar & Oyuncu Kütüğü Entegre Edildi  
**Aktif Faz:** 3 Sezonluk Canlı Veri Tabanı (1140 Maç, 868 Oyuncu, 31,932 Opta Olayı)

---

## 1. Faz Durum Özeti

| Faz | Açıklama | Durum | İlerleme |
|:---|:---|:---:|:---:|
| **Faz 1** | **Veri İndirme (2024-25, 2025-26 & 2026-27)** | 🟢 Tamamlandı | %100 (1140 Maç Detayı, 819 Oynanmış Maç) |
| **Faz 2** | **Tablolama & Çoklu Sezon Denetimi** | 🟢 Tamamlandı | %100 (1140 Maç Parquet, 868 Oyuncu Kütüğü) |
| **Faz 3** | **Zaman Serisi Öznitelik Mühendisliği** | 🟢 Tamamlandı | %100 (Leakage-Free İspatlandı) |
| **Faz 4** | **Model Eğitimi & Tahmin Motoru** | 🟢 Tamamlandı | %100 (5 Model Aktif: Korner, Taç, Kurtarış, Sonuç, Ofsayt) |
| **Frontend**| **Sidebar, Soft Gri/Beyaz Tema, Fikstür, Profiller, Maç Tahminleri & Detaylar** | 🟢 Canlıda | http://127.0.0.1:5173 (API: :8000) |

---

## 2. Tamamlanan Son Düzenlemeler
- [x] **Maç Detay Modalı Kapsamlı İstatistikler & Oyuncu Karnesi:**
  - `MatchDetailModal.jsx` içine "İstatistikler" sekmesi eklendi.
  - Sofascore tarzı 5 kategorili karşılaştırmalı takım istatistik çubukları (Şut & Hücum, Top Hakimiyeti & Pas, Duran Top & Baskı, Savunma & İkili Mücadele, Disiplin & Kaleci).
  - Maç özelinde ev sahibi ve deplasman oyuncu karnesi: Oynanan dakika, gol, asist, şut, isabetli şut, faul yapma, faul alma, ofsayt, kartlar.
- [x] **Yakalanılan Ofsayt Motoru (Offside Prediction Model v1):**
  - XGBoost Regressor + Poisson dağılımı ile eğitildi (`models/production/offside_model_v1.joblib`).
  - Test RMSE: 1.937 (Baseline: 1.974), 3.5 Üst Doğruluğu: %67.68.
  - `src/features/build_features.py` içine sızıntısız geçmiş ofsayt metrikleri (`offsides_for`, `offsides_against`), büyük fırsatlar (`big_chances`), ceza sahası topla buluşma ve fauller eklendi (336 öznitelik).
  - Sızıntı testi (`tests/test_data_leakage.py`) 0.000 fark ile başarıyla doğrulandı.
- [x] **Tahmin & Benchmark Arayüzü Güncellemesi:**
  - Sidebar ve kod tabanından Model & Denetim sekmesi kaldırıldı.
  - `/api/predict` uç noktası güncellendi.
  - Unplayed maçlardaki float NaN değerleri temizlenerek API JSON uyumluluğu sağlandı.
- [x] **Oyuncu Profilleri & Kadro Görselleştirme:**
  - 850+ oyuncunun resmi Premier League kafa fotoğrafları ve forma numaraları kütüğe eklendi.
  - `PlayerProfilesTab.jsx` ve `TeamProfilesTab.jsx` resmi oyuncu fotoğrafları, forma numaraları, mevki filtreleri ve modern kart düzeniyle yenilendi.
