# Premier League Model App — Kapsamlı Veri ve Gösterim Kataloğu

**Dokümantasyon Ağı:** [Ana Sayfa (README)](README.md) · [Ana Kapsamlı Rapor](docs/reports/premier_league_models_comprehensive_report.md) · [Paper Trading Protokolü](docs/reports/paper_trading_protocol_2026_27.md) · [Rapor Merkezi](docs/reports/README.md) · [AI Context](AI_CONTEXT.md) · [API Entegrasyonu](docs/model_api_integration.md)

Bu belge, Premier League Model App platformunda **Maç (Match)**, **Takım (Team)**, **Oyuncu (Player)** ve **Hakem (Referee)** varlıklarına ilişkin erişilebilen, hesaplanan, veri tabanında saklanan ve kullanıcı arayüzünde (UI) gösterilen **tüm verileri, metrikleri, olayları ve modelleri** en ince ayrıntısına kadar eksiksiz olarak belgelemektedir.

---

## 📌 İçindekiler
1. [Maç (Match) Verileri ve Detayları](#1-maç-match-verileri-ve-detayları)
   - 1.1 Temel Maç Kimlik ve Üst Verileri (Metadata)
   - 1.2 Canlı Maç İçi Olaylar ve Zaman Akışı (Match Timeline & Events)
   - 1.3 Karşılaştırmalı Takım Maç İstatistikleri (Opta 244+ Metrik)
   - 1.4 TheStatsAPI Doğrulanmış Beklenen Gol (xG) Entegrasyonu
   - 1.5 Maç Kadroları, Taktik Dizilişler ve Saha Görselleştirmesi
   - 1.6 Yapay Zeka Ön Maç Tahmin Motoru (AI Predictions)
   - 1.7 Bahis Oranları ve Piyasa Kapanış Fiyatları (Odds & Bookmakers)
   - 1.8 Model Doğrulama ve Performans Denetimi (Model Audit)
   - 1.9 Ön Maç Form Kayıtları (Pre-Match Recent Form)
2. [Takım (Team) Verileri ve Detayları](#2-takım-team-verileri-ve-detayları)
   - 2.1 Temel Takım Kimliği ve Sezonluk Rekor
   - 2.2 Puan Durumu ve Sıralama (Standings)
   - 2.3 Opta İleri Taktik Oyun Profili (27 Temel Taktik Metrik)
   - 2.4 Skor Durumu Senaryoları (Game-State Scenarios: Beraberlik, Önde, Geride)
   - 2.5 Takım Hücum Liderleri ve Şut Asistleri (Attacking Leaders)
   - 2.6 Transfermarkt Kulüp Piyasa Değeri ve 5 Yıllık Tarihsel Trend
   - 2.7 Kulüp Transfer Geçmişi (Gelenler, Gidenler, Bonservisler, Net Bilanço)
   - 2.8 Teknik Direktör Geçmişi ve Rakip Bazlı Performans Karnesi
   - 2.9 Takım Sezonluk Fikstür ve Sonuç Arşivi
   - 2.10 Takım Kadrosu ve Oyuncu Listesi (Squad Roster)
3. [Oyuncu (Player) Verileri ve Detayları](#3-oyuncu-player-verileri-ve-detayları)
   - 3.1 Oyuncu Kimlik ve Sicil Verileri (Registry)
   - 3.2 Sezonluk ve Kariyer Kümülatif İstatistikleri
   - 3.3 Maç Performans Puanlama Motoru (0–10 Rating Engine)
   - 3.4 Oyuncu Maç Karnesi Detayları (Player Match Performance Modal)
   - 3.5 Oyuncu Maç Günlüğü ve Geçmişi (Match-by-Match Logs)
   - 3.6 Dinamik Oyuncu Form ve Trend Analizi (70% EWMA + 30% Baseline)
   - 3.7 Transfermarkt Oyuncu Piyasa Değeri ve Kariyer Değer Grafiği
4. [Hakem (Referee) Verileri ve Detayları](#4-hakem-referee-verileri-ve-detayları)
   - 4.1 Hakem Kimlik ve Sezonluk Yönetim Profili
   - 4.2 Disiplin ve Kart İstatistikleri (Sarı, Kırmızı, Toplam Kart)
   - 4.3 Faul Ortalamaları ve Yönetim Karakteri (Katılık Etiketi)
   - 4.4 3.5+ ve 4.5+ Kart Üstü Yönetim Yüzdeleri
   - 4.5 Takım Bazlı Disiplin Dağılımı (En Çok Kart Gösterilen Takımlar)
   - 4.6 Hakem Maç Geçmişi Arşivi ve Kariyer Karşılaştırması
   - 4.7 Model Tahminlerine Hakem Modülatörü Olarak Etki
5. [Veri Mimarisi, Kaynaklar ve API Uç Noktaları](#5-veri-mimarisi-kaynaklar-ve-api-uç-noktaları)
   - 5.1 Veri Tabanı Şemaları (SQLite & Parquet)
   - 5.2 Veri Kaynakları ve Akış Hatları (Ingestion Pipelines)
   - 5.3 REST API Uç Noktaları Özeti
   - 5.4 Ön Yüz Bileşenleri (Frontend UI Mapping)

---

## 1. Maç (Match) Verileri ve Detayları

Platformda 2022/23'ten 2026/27 sezonuna kadar **1.900 karşılaşmanın tamamı** kayıtlıdır. Bir maça tıklandığında veya detay sayfası açıldığında aşağıdaki veriler sunulur:

### 1.1 Temel Maç Kimlik ve Üst Verileri (Metadata)
* **Maç Kimliği (`match_id`):** Premier League resmi maç ID'si.
* **Sezon (`season`):** İlgili sezon kodu (Örn: `2026_27`, `2025_26`, `2024_25`, `2023_24`, `2022_23`).
* **Hafta (`gameweek`):** 1 ile 38 arasındaki fikstür haftası.
* **Tarih ve Saat Bilgisi:**
  - `match_date`: ISO formatında maç tarihi (`YYYY-MM-DD`).
  - `kickoff_label`: Resmi Premier League başlama etiketi (Örn: `"Sat 10 Oct 2026, 12:30 BST"`).
  - `day_label`: Gün formatı (Örn: `"Cumartesi"`, `"Pazar"`).
  - `time_label`: Başlama saati (Örn: `"15:00"`).
  - `kickoff_millis`: Unix zaman damgası (milisaniye cinsinden kesin sıralama).
* **Stadyum & Saha Bilgisi (`ground_name`):** Karşılaşmanın oynandığı stadyum adı (Örn: *"Emirates Stadium"*, *"Anfield"*).
* **Seyirci Sayısı (`attendance`):** Stadyumdaki resmi seyirci sayısı (Tamamlanan maçlarda).
* **Maç Durumu (`status`):** `COMPLETED` (Tamamlandı) veya `UPCOMING` (Oynanacak / Gelecek).
* **Skorlar:**
  - `home_score`: Ev sahibi takımın tam zamanlı (FT) attığı gol sayısı.
  - `away_score`: Deplasman takımının tam zamanlı (FT) attığı gol sayısı.
  - `halfTimeScore`: İlk yarı sonucu (`homeScore`, `awayScore`).
* **Kulüp Bilgileri:**
  - Ev Sahibi: `home_id`, `home_name`, `home_abbr` (Örn: ARS), SVG Kulüp Arması (`/badges/{home_id}.svg`).
  - Deplasman: `away_id`, `away_name`, `away_abbr` (Örn: MCI), SVG Kulüp Arması (`/badges/{away_id}.svg`).
* **Teknik Direktörler (Managers):**
  - `home_manager`: Ev sahibi teknik direktör adı.
  - `away_manager`: Deplasman teknik direktör adı.
  - Maç tarihi itibarıyla kulüp başındaki güncel veya atanmış teknik direktör otomatik eşleştirilir.
* **Maç Resmi Hakem Heyeti (`matchOfficials`):**
  - **Ana Hakem (MAIN):** Hakem adı, ID'si ve profil bağlantısı.
  - **Yardımcı Hakemler (ASSISTANT):** 1. ve 2. Çizgi Hakemleri.
  - **Dördüncü Hakem (FOURTH_OFFICIAL):** 4. Hakem adı ve ID'si.
  - **VAR Hakemi (VAR):** Video Yardımcı Hakem adı.
  - **AVAR Hakemi (ASSISTANT_VAR):** Asistan Video Yardımcı Hakem adı.

---

### 1.2 Canlı Maç İçi Olaylar ve Zaman Akışı (Match Timeline & Events)
`{match_id}_details.json` ve `{match_id}_stream.json` dosyalarından derlenen, dakika dakika kronolojik maç olayları:

* **Periyot Başlangıç & Bitiş Olayları:**
  - `period_start`: 1. Yarı Başladı (0'), 2. Yarı Başladı (45').
  - `period_end`: İlk Yarı Sonu (HT), Karşılaşma Sonu (FT - Maç Sonu).
  - O andaki anlık skor tablosu.
* **Gol Olayları (`goal`):**
  - Normal Gol (`Gol`): Golü atan oyuncu adı, fotoğrafı, kulübü, gol dakikası (`minute`), güncel skor (`score`).
  - Asist (`assist`): Gol pasını veren oyuncu adı ve ID'si.
  - Penaltı Golü (`is_penalty: true`): Penaltıdan atılan gol etiketi ve penaltı ikonu.
  - Kendi Kalesine Gol (`is_own_goal: true`): Kendi kalesine atan oyuncu bilgisi ve golün doğru takıma yazılması.
* **Kaçan Penaltılar (`penalty_missed`):**
  - Penaltıyı kaçıran oyuncu, kaleci kurtarışı veya auta gidiş detayı, olayın dakikası.
* **Kartlar (`yellow_card` & `red_card`):**
  - Sarı Kart: Oyuncu adı, fotoğrafı, kulübü, kart dakikası.
  - Kırmızı Kart / İkinci Sarıdan Kırmızı: Doğrudan ihraç veya çift sarı kart ayrımı, oyuncu bilgisi ve dakikası.
* **Oyuncu Değişiklikleri (`substitution`):**
  - Oyundan Çıkan (`player_out`): Adı, ID'si, fotoğrafı.
  - Oyuna Giren (`player_in`): Adı, ID'si, fotoğrafı.
  - Değişikliğin gerçekleştiği dakika ve takım bilgisi.
* **Uzatma Süreleri (`added_time`):**
  - İlan edilen duraklama süresi (Örn: 1. yarı +3 dk, 2. yarı +6 dk).

---

### 1.3 Karşılaştırmalı Takım Maç İstatistikleri (Opta 244+ Metrik)
Tamamlanan her karşılaşma için raw Opta `{match_id}_stats.json` dosyasından 244 farklı ham istatistik okunur ve arayüzde 5 ana taktiksel kategoride karşılaştırmalı görsel barlar ile sunulur:

#### 1. Şut & Hücum Hacmi (Shooting & Attacking Volume)
| Metrik Adı | Kaynak Opta Anahtarı | Açıklama |
| :--- | :--- | :--- |
| **Beklenen Gol (xG)** | `external_match_xg` | TheStatsAPI doğrulanmış hücum xG değeri |
| **Toplam Şut** | `total_scoring_att` | İki takımın toplam şut denemesi |
| **İsabetli Şut** | `ontarget_scoring_att` | Kaleyi bulan şutlar |
| **İsabetsiz Şut** | `shot_off_target` | Dışarı giden şutlar |
| **Bloklanan Şut** | `blocked_scoring_att` | Savunma tarafından engellenen şutlar |
| **Ceza Sahası İçi Şut** | `attempts_ibox` | 18 yarda ceza sahası içinden yapılan vuruşlar |
| **Ceza Sahası Dışı Şut** | `attempts_obox` | Ceza sahası dışından çekilen şutlar |
| **Yaratılan Net Fırsat** | `big_chance_created` | Yüksek gol beklentili net pozisyon sayısı |
| **Kaçan Net Fırsat** | `big_chance_missed` | Golle sonuçlandırılamayan net gol şansı |
| **Rakip Ceza Sahasında Topla Buluşma** | `touches_in_opp_box` | Rakip ceza sahasında topla oynama adedi |
| **Kilit Pas / Şut Pası** | `total_att_assist` | Şutla sonuçlanan paslar |

#### 2. Top Hakimiyeti & Pas Dağılımı (Possession & Passing)
| Metrik Adı | Kaynak Opta Anahtarı | Açıklama |
| :--- | :--- | :--- |
| **Topa Sahip Olma (%)** | `possession_percentage` | Topa sahip olma yüzdesi |
| **Toplam Pas** | `total_pass` | Denenen toplam pas sayısı |
| **İsabetli Pas** | `accurate_pass` | Başarıyla adrese ulaşan pas sayısı |
| **Pas İsabet Oranı (%)** | `(accurate_pass / total_pass)` | Yüzdesel pas başarı oranı |
| **3. Bölge (Final Third) Pasları** | `total_final_third_passes` | Hücum bölgesine ve içinde denenen paslar |
| **Başarılı 3. Bölge Pasları** | `successful_final_third_passes` | Son bölgedeki isabetli paslar |
| **Toplam Orta / İsabet** | `total_cross` & `accurate_cross` | Yapılan toplam orta ve isabetli orta sayısı |
| **Uzun Toplar** | `total_long_balls` & `accurate_long_balls` | Uzun pas denemeleri ve isabeti |

#### 3. Duran Top & Baskı (Set Pieces & Pressing)
| Metrik Adı | Kaynak Opta Anahtarı | Açıklama |
| :--- | :--- | :--- |
| **Kazanılan Korner** | `won_corners` | Kullanılan toplam köşe vuruşu |
| **Ceza Sahasına İsabetli Korner** | `accurate_corners_intobox` | Tehlike bölgesine ulaşan kornerler |
| **Toplam Taç** | `total_throws` | Karşılaşmadaki taç atışı sayısı |
| **İsabetli Taç** | `accurate_throws` | Takım arkadaşına ulaşan taç atışları |
| **PPDA (Pres Baskı İndeksi)** | `ppda` | Rakibin savunma aksiyonu başına yaptığı pas sayısı |

#### 4. Savunma & İkili Mücadele (Defending & Duels)
| Metrik Adı | Kaynak Opta Anahtarı | Açıklama |
| :--- | :--- | :--- |
| **Top Kapma (Kazanılan)** | `total_tackle` & `won_tackle` | Müdahale denemesi ve kazanılan müdahale sayısı |
| **Pas Arası (Interception)** | `interception` | Rakip pasını kesme sayısı |
| **Tehlike Uzaklaştırma (Clearance)** | `total_clearance` | Savunmadan top uzaklaştırma adedi |
| **Bloklanan Şut & Pas** | `outfielder_block` + `blocked_pass` | Şut ve pas engelleme aksiyonları |
| **Sahipsiz Top Kazanma** | `ball_recovery` | Sahipsiz kalan topların kontrolünü alma |
| **Kazanılan İkili Mücadele** | `duel_won` | Yerdeki ikili mücadele kazanım sayısı |
| **Kazanılan Hava Topu** | `aerial_won` | Hava topu mücadelesi kazanım sayısı |

#### 5. Disiplin & Kaleci Performansı (Discipline & Goalkeeping)
| Metrik Adı | Kaynak Opta Anahtarı | Açıklama |
| :--- | :--- | :--- |
| **Toplam Kurtarış** | `saves` | Kalecinin yaptığı kurtarış adedi |
| **Ceza Sahası İçi Kurtarış** | `saved_ibox` | Altıpas ve ceza sahası içinden kurtarılan şutlar |
| **Yapılan Faul** | `fk_foul_lost` | Hakem tarafından aleyhte çalınan faul sayısı |
| **Alınan Faul** | `fk_foul_won` | Takımın lehine çalınan faul sayısı |
| **Ofsayt** | `total_offside` | Ofsayta düşme adedi |
| **Sarı Kart** | `total_yel_card` | Görülen sarı kart adedi |
| **Kırmızı Kart** | `total_red_card` | Görülen kırmızı kart adedi |

---

### 1.4 TheStatsAPI Doğrulanmış Beklenen Gol (xG) Entegrasyonu
Sistemimizde xG verileri eski proxy hesaplamalarından ayrıştırılarak doğrudan `external_match_xg` tablosundan beslenir:
* **Ev Sahibi xG (`home_xg` / `statsapi_home_xg`):** Ev sahibinin ürettiği şut kalitesi bazlı beklenen gol.
* **Deplasman xG (`away_xg` / `statsapi_away_xg`):** Deplasmanın ürettiği beklenen gol.
* **Toplam xG (`total_xg`):** Karşılaşmadaki toplam gol beklentisi.
* **Sağlayıcı & Kalite Etiketi (`xg_provider`, `xg_quality`):** Verinin kaynağı (`thestatsapi`) ve kalitesi (Örn: `verified_match_feed`). Veri henüz girilmemişse UI üzerinde "Not Found" yerine zarif bir şekilde "Yok" olarak işaretlenir.

---

### 1.5 Maç Kadroları, Taktik Dizilişler ve Saha Görselleştirmesi
Karşılaşmanın kadro sekmesinde iki farklı görünüm seçeneği sunulur: **Taktik Saha (Pitch Visualizer)** ve **Detaylı Liste (List View)**:

* **Taktik Formasyon:**
  - Ev ve Deplasman formasyon etiketi (Örn: `4-3-3`, `4-2-3-1`, `3-4-2-1`, `5-3-2`).
  - Opta koordinat matrisi (`formation_matrix`): Oyuncuların sahadaki dizilim hatları (Kaleci, Defans Hattı, Orta Saha Hattı, Forvet Hattı).
* **İlk 11 Oyuncuları (Starters - 11 Oyuncu):**
  - Oyuncu Adı ve ID'si.
  - Forma Numarası (`matchShirtNumber`).
  - Pozisyonu (`matchPosition`: G, D, M, F veya CB, LB, RB, CM, LW, RW, ST).
  - Kaptanlık Rozeti (`captain: true`).
  - Ülke / Milliyet (`country`).
  - Premier League Resmi CDN Fotoğrafı (`photo_url`).
  - Maç Performans Reytingi (`rating` / `match_rating`: 0–10 arası, tamamlanan maçlar için).
  - Form Reytingi (`form_rating`: Son 5 maçın form puanı).
  - Hücum Reytingi (`attack_rating`) ve Savunma Reytingi (`defense_rating`).
  - Kart Riski Skoru (`cards_risk`: 0–10).
  - Form Trendi (`trend`: yükselişte, stabil, düşüşte).
  - Form Etiketi (`form_label`: *"Yıldız Formda"*, *"Formda"*, *"Normal"*, *"Düşüşte"*).
* **Yedek Oyuncular (Substitutes - 9 Oyuncu):**
  - Aynı metriklerle kulübedeki oyuncular.
  - Oyuna girip girmediği, kaçıncı dakikada girdiği (`sub_on`).
  - Oyuna giren yedekler için süre aldıkları dakikaya göre hesaplanmış Maç Reytingi.
* **Takım Düzeyi İlk 11 Ortalama Reytingleri:**
  - `overall`: İlk 11'in genel güç ortalaması (0–10).
  - `attack`: İlk 11 hücum gücü ortalaması.
  - `defense`: İlk 11 savunma gücü ortalaması.
  - `cards_risk`: Takımın agresiflik / kart görme risk ortalaması.
* **Kadro Durum Etiketi:**
  - *"Resmi Kadrolar Açıklandı"* (Maçtan 1 saat önce açıklanan resmi 11).
  - *"Muhtemel 11'ler Baz Alındı"* (Gelecek maçlar için son 8 haftanın başlama sıklığına göre projekte edilen 11).

---

### 1.6 Yapay Zeka Ön Maç Tahmin Motoru (AI Predictions)
Henüz oynanmamış maçlar için eğitilmiş üretim modelleri (LightGBM, Ridge Regression, Dixon-Coles Poisson) çalıştırılarak anlık tahminler üretilir:

#### 1. Maç Sonucu (1X2 Piyasası & Ensemble)
* **Ev Sahibi Galibiyeti (`home_win_pct`):** Yüzdesel kazanma olasılığı (Örn: `%54.2`).
* **Beraberlik (`draw_pct`):** Kalibre edilmiş beraberlik olasılığı (Örn: `%24.1`).
* **Deplasman Galibiyeti (`away_win_pct`):** Deplasman kazanma olasılığı (Örn: `%21.7`).
* **Favori Etiketi (`favorite_label`):** *"Arsenal Favori"* veya *"Dengeli Mücadele"*.
* **Fizik Tabanlı Ensemble:** Dixon-Coles Poisson modeli ile Gradient Boosting modellerinin logaritmik harmanlanması (`blend_log`) ve izotonik kalibrasyon.

#### 2. Gol Tahminleri & Alt/Üst Baremleri
* **Beklenen Ev Sahibi Golü (`expected_home_goals`):** Lambda ev (Örn: `1.84`).
* **Beklenen Deplasman Golü (`expected_away_goals`):** Lambda dep (Örn: `1.02`).
* **Toplam Beklenen Gol (`expected_total_goals`):** Maç geneli beklenen gol (Örn: `2.86`).
* **1.5 Gol Üstü Yüzdesi (`over_1.5`):** Monotonik tutarlılık denetimli olasılık.
* **2.5 Gol Üstü Yüzdesi (`over_2.5` / `over_2_5_goals_pct`):** Model olasılığı.
* **3.5 Gol Üstü Yüzdesi (`over_3.5`):** Model olasılığı.
* **Karşılıklı Gol (KG Var / KG Yok - BTTS):**
  - `btts_pct`: İki takımın da gol atma ihtimali (Örn: `%58.3`).
  - `btts_prediction`: *"KG Var"* veya *"KG Yok"*.
  - `btts_prior_pct`: Dinamik Bayesyen lig öncül eşiği (`%56.6`).
* **Bireysel Takım Gol Baremleri (Team Totals):**
  - Ev Sahibi 0.5, 1.5, 2.5 Alt/Üst yüzdeleri ve adil oranları (`fair_odds_over`, `fair_odds_under`).
  - Deplasman 0.5, 1.5, 2.5 Alt/Üst yüzdeleri ve adil oranları.

#### 3. Korner Modeli (Corners Prediction)
* **Toplam Beklenen Korner (`expected_total`):** Örn: `10.4`.
* **Ev Sahibi Beklenen Korner (`expected_home`):** Takımın hücum korner üretimi ve rakibin verdiği korner hacmi harmanı.
* **Deplasman Beklenen Korner (`expected_away`).**
* **8.5 Üst Olasılığı (`prob_over_8_5_pct`).**
* **9.5 Üst Olasılığı (`prob_over_9_5_pct`).**
* **10.5 Üst Olasılığı (`prob_over_10_5_pct`).**
* **Model Beceri Durumu (`model_skill`):** `model` veya `baseline` (Skill Gate).

#### 4. Kart & Disiplin Modeli (Cards Prediction)
> Güncel durum (17 Ekim 2026): özellikli kart modeli dış sezon kapısını geçemediği için toplam kart tahmini eğitim ortalamasından gelir (`model_skill: baseline`); ev/deplasman paylaşımı ve hakem k/m kutusu bilgi amaçlıdır. Bkz. [Kart Model Raporu](docs/reports/models/cards_model.md).

* **Toplam Beklenen Kart (`expected_total`):** Örn: `4.3 kart`.
* **Ev & Deplasman Kart Paylaşımı:** Takımların geçmiş kart görme ve rakibe kart aldırma oranlarına göre dağılım.
* **3.5 Üst Kart Yüzdesi (`prob_over_3_5_pct`).**
* **4.5 Üst Kart Yüzdesi (`prob_over_4_5_pct`).**
* **5.5 Üst Kart Yüzdesi (`prob_over_5_5_pct`).**
* **Atanan Hakem Modülatörü:** Hakemin kariyer kart ortalamasının lige oranı çarpan olarak modele etki eder.

#### 5. Taç Modeli (Throws Prediction)
* **Toplam Beklenen Taç (`expected_total`):** Örn: `35.2 taç`.
* **Ev & Deplasman Dağılımı (`expected_home`, `expected_away`).**
* **33.5 Üst Taç Yüzdesi (`prob_over_33_5_pct`).**
* **34.5 Üst Taç Yüzdesi (`prob_over_34_5_pct`).**
* **36.5 Üst Taç Yüzdesi (`prob_over_36_5_pct`).**

#### 6. Kurtarış & Şut Modeli (Saves & Shots Prediction)
* **Toplam Beklenen Kaleci Kurtarışı (`expected_total`):** Örn: `6.4 kurtarış`.
* **Ev Kalecisi Beklenen Kurtarış:** Deplasmanın isabetli şut hacmine bağlı.
* **Deplasman Kalecisi Beklenen Kurtarış.**
* **Toplam Beklenen Şut Sayısı (`shots.expected_total`):** Model çarpanı ile hesaplanan toplam şut beklentisi.

#### 7. Ofsayt Modeli (Offsides Prediction)
* **Toplam Beklenen Ofsayt (`expected_total`):** Örn: `3.4 ofsayt`.
* **Ev & Deplasman Beklenen Ofsayt Dağılımı.**
* **2.5 Üst Ofsayt Yüzdesi (`prob_over_2_5_pct`).**
* **3.5 Üst Ofsayt Yüzdesi (`prob_over_3_5_pct`).**
* **4.5 Üst Ofsayt Yüzdesi (`prob_over_4_5_pct`).**
* **Taktiksel Çıkarım:** Yüksek savunma çizgisi veya derin blok tercihi tespiti.

#### 8. İlk 11 Modülatörleri ve Dinamik Etki Analizi (Lineup Impact Analysis)
* `delta_home_goals`: İlk 11 hücum-savunma kalitesine göre ev gol beklentisindeki sapma (Örn: `+0.18`).
* `delta_away_goals`: Deplasman gol beklentisi sapması (Örn: `-0.05`).
* `delta_cards`: İki takımın ilk 11 kart riskine göre beklenen ekstra kart sayısı (Örn: `+0.4 Kart`).
* `delta_home_win_pct`: İlk 11 gücüne göre galibiyet yüzdesindeki değişim.
* `delta_away_win_pct`: Deplasman galibiyet yüzdesindeki değişim.
* `summary_text`: Etki özeti (Örn: *"Ev Gol Etkisi: +0.22 · Kart Beklentisi: +0.4 Kart"*).

---

### 1.7 Bahis Oranları ve Piyasa Kapanış Fiyatları (Odds & Bookmakers)
`external_match_odds` tablosunda saklanan, dünyanın önde gelen 5 büyük bahis şirketinin (Bookmakers) açılış ve maç başlangıcı kapanış oranları:
* **Kapsanan Bahis Şirketleri:**
  1. `Bet365`
  2. `Pinnacle`
  3. `Betfair Exchange`
  4. `Paddy Power`
  5. `BetMGM UK`
* **Sezon Kapsamı:** 2026/27 → 80 maç, 5 büro (açılış + kapanış). 2023/24, 2024/25 ve 2025/26 → her biri 380 maç, yalnızca `Bet365`, yalnızca kapanış (`*_open` alanları NULL; TheStatsAPI geçmiş sezonda açılış vermiyor).
* **Piyasa Türleri:**
  - **1X2 Maç Sonucu:** Açılış (`open`) ve Kapanış (`last_seen`) oranları (Ev Sahibi, Beraberlik, Deplasman).
  - **2.5 Gol Alt / Üst:** `over_25_open`, `under_25_open`, `over_25_last_seen`, `under_25_last_seen`.
  - **Karşılıklı Gol (BTTS):** `btts_yes_open`, `btts_no_open`, `btts_yes_last_seen`, `btts_no_last_seen`.
  - **Özel Çizgiler:** `corners_over_last_seen`, `corners_under_last_seen`, `cards_over_last_seen`, `cards_under_last_seen`.

---

### 1.8 Model Doğrulama ve Performans Denetimi (Model Audit)
Oynanmış her maç için, maç öncesi üretilen saf tahminlerin gerçekleşen sonuçlarla karşılaştırıldığı doğrulama verileri:
* **Tahmin Başarısı:**
  - `hit_1x2`: 1X2 tahmininin tutup tutmadığı (1 veya 0).
  - `hit_over_25`: 2.5 Üst tahmininin tutup tutmadığı.
  - `hit_btts`: KG Var tahmininin tutup tutmadığı.
* **Sapma & Hata Payları:**
  - `corner_error`: Beklenen korner ile gerçek korner farkı.
  - `card_error`: Beklenen kart ile gerçek kart farkı.
* **Piyasa Değer Avantajı (Value Edge):**
  - `highest_edge_side`: Modelin piyasaya göre en çok değer bulduğu taraf (Home, Draw, Away).
  - `edge_pct`: Model olasılığı ile piyasa ima edilen olasılığı arasındaki pozitif fark (% Edge).
  - `is_value_bet`: %5+ değer avantajı olan bahisler.
  - `confidence_tier`: Model güven derecesi (`high`, `medium`, `low`).
  - `is_balanced`: Maçın dengeli olup olmadığı.

---

### 1.9 Ön Maç Form Kayıtları (Pre-Match Recent Form)
`/api/match/{match_id}/recent-form` uç noktası üzerinden:
* İki takımın bu karşılaşmaya çıkmadan önce oynadığı **son 5 lig maçının sonuçları** (kronolojik: `W`, `D`, `L`).
* Veri sızıntısını (data leakage) önlemek amacıyla yalnızca bu maçın başlama saatinden önceki maçlar dikkate alınır.

---

## 2. Takım (Team) Verileri ve Detayları

Takım Profili sekmesinde (`/api/teams/profile`, `/api/teams/tactics`, `/api/teams/scenarios`, `/api/teams/attacking-leaders`, `/api/teams/staff`, `/api/teams/{team_id}/transfers`) sunulan eksiksiz takım verileri:

### 2.1 Temel Takım Kimliği ve Sezonluk Rekor
* **Kulüp Bilgisi:** ID, Tam Adı (Örn: *Arsenal*), Kısa Adı (*Arsenal*), Kısaltması (*ARS*), Stadyum Adı (*Emirates Stadium*), SVG Logo/Arma.
* **Sezonluk Maç Rekoru (`record`):**
  - `played`: Oynanan maç sayısı.
  - `wins`: Galibiyet sayısı.
  - `draws`: Beraberlik sayısı.
  - `losses`: Mağlubiyet sayısı.
  - `gf`: Atılan toplam gol (Goals For).
  - `ga`: Yenilen toplam gol (Goals Against).
  - `gd`: Genel averaj (Goal Difference = GF - GA).
  - `points`: Toplanan puan (3 * G + 1 * B).
* **Bir Sonraki Karşılaşma (`next_match`):** Takımın oynayacağı bir sonraki unplayed maç (Tarih, Saat, Hafta, Rakip Kulüp, İç/Dış saha bilgisi).

---

### 2.2 Puan Durumu ve Sıralama (Standings)
Premier League resmi sıralama kuralları (Puan -> Averaj -> Atılan Gol) ile hesaplanan lig tablosu:
* `rank`: Ligdeki güncel sırası (1–20).
* **Genel Tablo:** O, G, B, M, AG, YG, AV, Puan.
* **İç Saha Tablosu (`home`):** Evinde O, G, B, M, AG, YG, AV, Puan.
* **Deplasman Tablosu (`away`):** Deplasmanda O, G, B, M, AG, YG, AV, Puan.
* **Son 5 Maç Formu (`form`):** Takımın son 5 lig maçındaki form dizilimi (Örn: `['W', 'W', 'D', 'W', 'L']`).

---

### 2.3 Opta İleri Taktik Oyun Profili (27 Temel Taktik Metrik)
`team_tactics.py` motoru, Opta ham maç istatistiklerinden her takım için 27 taktiksel parametre üretir. Her parametre lig ortalaması ile karşılaştırılır:

#### 1. Genel Oyun Karakteri
* **Topa Sahip Olma (`possession`):** Ortalama topa sahip olma yüzdesi (`%`).
* **İleri Bölge Pas Payı (`forward_pass_share`):** Toplam paslar içinde ileriye doğru atılan pasların payı (`%`).

#### 2. Hücum Üretimi ve Şut Profili
* **Son Bölgeye Giriş (`final_third_entries`):** Maç başına rakip hücum 3. bölgesine yapılan giriş adedi.
* **Son Bölgede Pas (`final_third_passes`):** Maç başına hücum 3. bölgesinde yapılan pas sayısı.
* **Son Bölge Pas İsabeti (`final_third_pass_accuracy`):** Hücum bölgesindeki pas isabet yüzdesi (`%`).
* **Rakip Ceza Sahası Dokunuşu (`opposition_box_touches`):** Maç başına rakip ceza sahasında topla buluşma.
* **Maç Başına Şut (`shots_per_match`):** Toplam şut denemesi.
* **İsabetli Şut Oranı (`shots_on_target_share`):** Kaleyi bulan şutların toplam şuta oranı (`%`).
* **Ceza Sahası İçi Şut Payı (`inside_box_shot_share`):** Tüm şutlar içinde ceza sahası içinden vurulanların payı (`%`).
* **Ceza Sahası Dışı Şut Payı (`outside_box_shot_share`):** Ceza sahası dışından çekilen şutların oranı (`%`).

#### 3. Pas Tercihleri ve Uzun Toplar
* **Uzun Pas Payı (`long_ball_share`):** Toplam paslar içinde uzun topların oranı (`%`).
* **Uzun Pas İsabeti (`long_ball_accuracy`):** Uzun pasların isabet yüzdesi (`%`).
* **Maç Başına Orta (`crosses_per_match`):** Yapılan orta sayısı.
* **Orta İsabeti (`cross_accuracy`):** İsabetli ortaların toplam ortalara oranı (`%`).

#### 4. Duran Toplar
* **Ceza Sahasına Gönderilen Korner Oranı (`corners_into_box_share`):** Kullanılan kornerlerin doğrudan içeri kesilme yüzdesi (`%`).

#### 5. Savunma Aksiyonları & Pres
* **İzin Verilen Şut (`shots_conceded_per_match`):** Maç başına rakibe verilen şut imkanı.
* **Topu Geri Kazanma (`ball_recoveries`):** Sahipsiz topları kazanma sıklığı.
* **Savunma Bölgesinde Top Kazanımı (`defensive_third_recoveries`):** Kendi 1. bölgesinde kazanılan toplar.
* **Orta Bölgede Top Kazanımı (`mid_third_recoveries`):** Orta sahada kazanılan toplar.
* **Hücum Bölgesinde Top Kazanımı (`attacking_third_recoveries`):** Rakip kalede presle kazanılan toplar.
* **Pres Yoğunluğu - PPDA (`pressing_intensity`):** Rakip pası başına yapılan savunma aksiyonu (düşük değer = yüksek pres).
* **Pas Arası (`interceptions`):** Maç başına araya girme adedi.
* **Müdahale Başarısı (`tackle_success`):** İkili mücadelede top kapma yüzdesi (`%`).
* **Hava Topu Kazanma Oranı (`aerial_duel_success`):** Hava topu mücadelelerinin kazanılma oranı (`%`).
* **Uzaklaştırma (`clearances`):** Maç başına tehlike savuşturma sayısı.

#### 6. Top Kaybı Profili
* **Toplam Top Kaybı (`possession_losses`):** Maç başına top kaybı (`poss_lost_all`).
* **Kontrollü Top Kaybı (`controlled_possession_losses`):** Kontrol altındayken yapılan top kaybı (`poss_lost_ctrl`).

---

### 2.4 Skor Durumu Senaryoları (Game-State Scenarios)
`team_scenarios.py` ile her maçın stream akışı taranarak takımın skor durumuna göre nasıl reaksiyon verdiği analiz edilir:
* **Üç Farklı Oyun Senaryosu:**
  1. **Skor Eşitken (`level`):** Maçın 0-0, 1-1, 2-2 vb. berabere devam ettiği dakikalar.
  2. **Skor Öndeyken (`leading`):** Takımın 1 veya daha fazla farkla önde olduğu dakikalar.
  3. **Skor Gerideyken (`trailing`):** Takımın 1 veya daha fazla farkla mağlup olduğu dakikalar.
* **Her Senaryoda Ölçülen Değerler:**
  - `minutes`: Bu skor durumunda geçirilen toplam dakika süresi.
  - `shots`: Bu skor durumunda çekilen toplam şut sayısı.
  - `corners`: Bu skor durumunda kazanılan toplam köşe vuruşu sayısı.
  - `shots_per_90`: Bu skor durumunda 90 dakika başına üretilen normalize şut temposu.
  - `corners_per_90`: Bu skor durumunda 90 dakika başına üretilen normalize korner temposu.
  - `sample_confidence`: Güven skoru (yeterli dakika oynandı mı: yüksek/orta/düşük).

---

### 2.5 Takım Hücum Liderleri ve Şut Asistleri (Attacking Leaders)
`team_attackers.py` algoritması ile takımın hücumdaki en etkili 3 oyuncusu derecelendirilir:
* **Dikkate Alınan Kriterler (90 Dk Normalize):**
  - `goals`: Attığı goller.
  - `assists`: Yaptığı resmi asistler.
  - `shots`: Çektiği şutlar.
  - `shot_assists`: Şutla sonuçlanan paslar ("Assisted by" Opta stream ayrıştırması).
* **Hücum Reytingi (`rating`):** Takım içi maksimumlara göre normalize edilmiş 0–100 arası bağıl hücum puanı.
* **Filtre Şartı:** Sezonda en az 180 dakika forma giymiş olmak (`minimum_minutes: 180`).
* **Kapsam Oranı (`shot_assist_coverage_pct`):** Takım şutlarının ne kadarında asist kaydının doğrulanabildiği.

---

### 2.6 Transfermarkt Kulüp Piyasa Değeri ve 5 Yıllık Tarihsel Trend
`team_market_values` tablosundan sağlanan veriler:
* **Toplam Kulüp Piyasa Değeri:** Milyon / Milyar Euro cinsinden (Örn: `€1.25B` veya `€850.5M`).
* **Kadro Büyüklüğü (`squad_size`):** Kayıtlı A takım oyuncu sayısı.
* **Oyuncu Başına Ortalama Piyasa Değeri (`avg_market_value_eur`):** Örn: `€48.2M`.
* **5 Yıllık Değer Gelişim Grafiği (`history`):**
  - 2022/23, 2023/24, 2024/25, 2025/26 ve 2026/27 sezonlarındaki toplam piyasa değerinin evrimi.

---

### 2.7 Kulüp Transfer Geçmişi (Transfers)
Transfermarkt API üzerinden kulübün sezonluk transfer bilançosu:
* **Özet Finansal Göstergeler:**
  - `total_spent_formatted`: Toplam bonservis harcaması (Örn: `€125.4M`).
  - `total_income_formatted`: Toplam oyuncu satış geliri (Örn: `€65.0M`).
  - `net_balance_formatted`: Net transfer bilançosu (Kâr / Zarar).
  - `arrivals_count`: Gelen oyuncu sayısı.
  - `departures_count`: Ayrılan oyuncu sayısı.
* **Gelen Transferler Listesi (`arrivals`):**
  - Oyuncu Adı, Yaşı, Uyruğu, Mevkisi, Geldiği Kulüp (Adı & Arması), Piyasa Değeri, Transfer Bedeli (Bonservis, Kiralık, Bedelsiz, Kiradan Dönüş).
* **Giden Transferler Listesi (`departures`):**
  - Oyuncu Adı, Yaşı, Uyruğu, Mevkisi, Gittiği Kulüp (Adı & Arması), Piyasa Değeri, Satış Bedeli.

---

### 2.8 Teknik Direktör Geçmişi ve Rakip Bazlı Performans Karnesi
`manager_changes.json` ve `team_staff.json` verileriyle:
* **Teknik Kadro Rosterı:** Menajer ve Yardımcı Menajer isimleri.
* **Menajer Değişiklikleri (`manager-changes`):**
  - Görevden Ayrılan Menajer (`outgoing_manager`).
  - Yeni Göreve Başlayan Menajer (`incoming_manager`).
  - Atanma Tarihi (`appointment_date`).
  - Atanma Türü (`permanent` / `interim`).
  - İlk Maç Tarihi ve Haftası.
* **Menajer Rakip Karnesi (`manager-performance`):**
  - Belirli bir teknik direktörün takımın başında çıktığı tüm maçlar taranarak:
  - Toplam Maç, Galibiyet, Beraberlik, Mağlubiyet, Atılan Gol, Yenilen Gol.
  - **Rakip Bazlı Döküm:** Ligdeki her bir rakibe karşı menajerin performansı (Örn: Pep Guardiola vs Arsenal: 14 maç, 10G, 2B, 2M, 32AG, 12YG).

---

### 2.9 Takım Sezonluk Fikstür ve Sonuç Arşivi
Takımın o sezon oynadığı ve oynayacağı 38 maçın tamamı:
* Hafta, Tarih, Başlama Saati.
* İç Saha / Dış Saha durumu.
* Rakip Takım Adı ve Arması.
* Karşılaşma Skoru (Tamamlananlar için) ve Sonuç (`W` - Galibiyet, `D` - Beraberlik, `L` - Mağlubiyet).
* Maçtaki Toplam Korner, Taç, Şut ve Kaleci Kurtarışı sayıları.

---

### 2.10 Takım Kadrosu ve Oyuncu Listesi (Squad Roster)
Takım kadrosundaki her bir futbolcu için:
* Forma Numarası, Fotoğrafı, Adı, Pozisyonu (GK, DEF, MID, FWD), Ülkesi, Kaptanlık Rozeti.
* Sezonluk İstatistikler: Maç Sayısı (`appearances`), İlk 11 Başlama (`starts`), Attığı Gol (`goals`), Yaptığı Asist (`assists`), Sarı Kartlar (`yellow_cards`), Kırmızı Kartlar (`red_cards`).
* Transfermarkt Bireysel Piyasa Değeri (Formatlı €M / €k).
* Tıklanabilir sıralama seçenekleri (Mevkiye göre, Piyasa Değerine göre, Gol/Asist/Maç sayısına göre).

---

## 3. Oyuncu (Player) Verileri ve Detayları

Oyuncu sekmesinde (`/api/players`, `/api/players/profile`, `/api/players/{player_id}/rating`, `/api/players/{player_id}/market-value-history`) erişilen ve gösterilen tüm parametreler:

### 3.1 Oyuncu Kimlik ve Sicil Verileri (Registry)
* **Oyuncu ID (`id`):** Premier League resmi oyuncu ID'si.
* **Adı Soyadı (`name`):** Tam oyuncu adı.
* **Kulübü (`teamId`, `teamName`):** Oynadığı kulüp ve arması (Sezon bazlı doğru transfer geçmişine göre güncellenir).
* **Mevki (`position`):** Kaleci (G), Defans (D), Orta Saha (M), Forvet (F).
* **Forma Numarası (`shirt`):** Sırt numarası.
* **Uyruk (`country`):** Temsil ettiği milliyet / ülke.
* **Premier League Fotoğrafı (`photo_url`):** Premier League resmi CDN fotoğrafı (`https://resources.premierleague.com/...`).
* **Opta Kodu (`opta_code`):** Opta veri tabanı oyuncu referans kodu.

---

### 3.2 Sezonluk ve Kariyer Kümülatif İstatistikleri
* **Sezon Filtresi:** 2026/27, 2025/26, 2024/25, 2023/24, 2022/23 ve "Tüm Sezonlar" (Kariyer).
* **Toplam Maç Sayısı (`appearances`):** Süre aldığı lig maçı sayısı.
* **Toplam Dakika (`minutes`):** Sahada kaldığı toplam süre.
* **Toplam Gol (`goals`):** Attığı gol adedi.
* **Toplam Asist (`assists`):** Yaptığı resmi asist adedi.
* **Ortalama Maç Reytingi (`average_rating`):** Puanlanan maçlardaki ağırlıklı genel puan ortalaması.
* **Kariyer Toplamı:** Premier League kariyerindeki toplam maç, gol ve asist dökümü.

---

### 3.3 Maç Performans Puanlama Motoru (0–10 Rating Engine)
`player_ratings.py` içindeki matematiksel puanlama sistemiyle, bir oyuncunun oynadığı tek bir maçtaki performansı 0–10 arasında puanlanır:
* **Baz Başlangıç Puanı:** `6.0` (Standart lig ortalaması).
* **Süre Şartı:** 10 dakikadan az oynayan ve belirleyici aksiyonu (gol, asist, kart, penaltı) olmayan oyuncular değerlendirmeye alınmaz (`—`).
* **Pozisyona Göre Gol & Asist Ağırlıkları:**
  - Forvet: Gol `+1.25`, Asist `+0.70`.
  - Orta Saha: Gol `+1.40`, Asist `+0.80`.
  - Defans / Kaleci: Gol `+1.65`, Asist `+0.90`.
* **Pozisyona Göre Savunma & Clean Sheet Etkisi:**
  - Kaleci / Defans: Kalesini gole kapatma (Clean Sheet, 60+ dk) `+0.85`, 1 gol yeme `+0.15`, 3+ gol yeme `-0.35 * (gol - 2)`.
  - Orta Saha: Clean Sheet `+0.35`, 3+ gol yeme `-0.15 * (gol - 2)`.
* **Mikro Metrik Etkileri:**
  - Penaltı Kazandırma: `+0.75`.
  - Penaltı Yaptırma: `-1.10`.
  - Penaltı Kaçırma: `-1.15`.
  - İsabetli Şut Katkısı: `(isabetli şut - gol) * +0.20`.
  - Kaleci Kurtarışı: `kurtarış * +0.35`.
  - Sarı Kart Cezası: `-0.60`.
  - Kırmızı Kart Cezası: `-2.50`.
* **Puan Sınırlandırması:** Skorlar kesin olarak `3.0` ile `10.0` arasında sınırlandırılır (clamped).

---

### 3.4 Oyuncu Maç Karnesi Detayları (Player Match Performance Modal)
Bir maç detay sayfasında veya oyuncu profilinde herhangi bir maçtaki oyuncu kartına tıklandığında açılan detaylı karne:
* **Üst Başlık:** Oyuncu Fotoğrafı, Forma Numarası, Mevkisi, Takım Arması, Kaptanlık Rozeti, Maç Reytingi (Büyük renkli skor kutusu), Sahada Kaldığı Süre, İlk 11 / Yedek durumu.
* **3 Farklı Sekme Görünümü:**
  1. **Genel Sekmesi (Mevkiye Özel Öne Çıkanlar):**
     - Kaleci ise: Kurtarış sayısı, Gol yeme/Clean sheet durumu, Yaptırdığı penaltı, Kartlar.
     - Defans ise: Clean sheet durumu, Kazanılan/kaybedilen faul, Penaltı hatası, Gol/Asist.
     - Orta Saha ise: Asist & şans yaratma, Gol, Şut tehdidi (isabet oranı), Faul mücadeleleri.
     - Forvet ise: Gol, Asist, İsabetli şut / şut yüzdesi, Ofsayt & kazanılan penaltı.
  2. **Hücum Sekmesi (Attack Breakdown):**
     - Hücum Reytingi (Attack Rating), Goller, Asistler, Toplam Şut, İsabetli Şut, Şut İsabet Oranı (`%`), Ofsaytlar, Kazanılan Penaltılar, Kaçan Penaltılar.
  3. **Savunma & Disiplin Sekmesi (Defense & Discipline Breakdown):**
     - Savunma Reytingi (Defense Rating), Yapılan Fauller, Kazanılan Fauller, Yaptırılan Penaltılar, Sarı Kartlar, Kırmızı Kartlar, Kaleciler için Kurtarışlar ve Ceza Sahası Kurtarışları.
* **Kritik Maç Olayları Rozetleri:** *"⚽ 2 Gol Attı"*, *"🎯 1 Asist Yaptı"*, *"🧤 5 Kurtarış"*, *"⭐ Penaltı Kazandırdı"*, *"⚠️ Penaltı Yaptırdı"*, *"❌ Penaltı Kaçırdı"*, *"🟨 Sarı Kart Gördü"*, *"🟥 Kırmızı Kart Gördü"*, *"🛡️ Gol Yemedi (Clean Sheet)"*.

---

### 3.5 Oyuncu Maç Günlüğü ve Geçmişi (Match-by-Match Logs)
Oyuncunun seçilen sezonda oynadığı tüm lig maçlarının kronolojik dökümü:
* Maç Haftası (`gameweek`).
* Karşılaşma Tarihi ve Başlama Saati.
* İç Saha / Dış Saha durumu (`İç` / `Dep`).
* Rakip Takım Adı ve Arması.
* Maç Skoru (Örn: `2 - 1`).
* Oyuncunun O Maçtaki Performans Reytingi (Renkli kutucuk, Örn: `8.2`).
* Sahada Kaldığı Dakika (`minutes_played`) ve Başlangıç Statüsü (`İlk 11` veya `Yedek`).
* O Maçtaki Gol ve Asist Sayısı.
* Tıklandığında doğrudan ilgili karşılaşmanın tam detay sayfasına gitme imkanı.

---

### 3.6 Dinamik Oyuncu Form ve Trend Analizi (70% EWMA + 30% Baseline)
`get_player_dynamic_rating` motoru tarafından hesaplanan dinamik form:
* **Formül:** `%70` Son 5 Maçın Üstel Hareketli Ortalaması (EWMA) + `%30` Sezonluk Baz Başlangıç Puanı.
* **Hesaplanan Değerler:**
  - `overall_rating`: Anlık form puanı (0–10).
  - `attack_rating`: Hücum form puanı.
  - `defense_rating`: Savunma form puanı.
  - `cards_risk`: Kart görme riski (0–10).
  - `trend`: Form trendi (`improving` - yükselişte, `declining` - düşüşte, `stable` - stabil).
  - `form_label`:
    * `7.8+`: *"Yıldız Formda"* ⭐
    * `6.8 - 7.7`: *"Formda"* 🟢
    * `5.8 - 6.7`: *"Normal"* 🔵
    * `< 5.8`: *"Düşüşte"* 🔴
  - `recent_scores`: Son 5 maçın tekil reyting dizisi (Örn: `[7.4, 8.1, 6.5, 7.8, 8.5]`).

---

### 3.7 Transfermarkt Oyuncu Piyasa Değeri ve Kariyer Değer Grafiği
Transfermarkt API ve yerel SQLite önbelleği üzerinden:
* **Güncel Piyasa Değeri:** Milyon / Bin Euro cinsinden (Örn: `€110.0M` veya `€450k`).
* **Kariyer Değer Gelişim Eğrisi (Interactive Valuation History Modal):**
  - Oyuncunun profesyonel kariyerindeki her bir piyasa değeri güncellemesi (Tarih, O zamanki Yaşı, O zamanki Kulübü, Piyasa Değeri, Bir önceki değere göre yüzdesel ve parasal değişim).
  - **Kariyer Zirve Değeri (`peak_value`):** Kariyerinde ulaştığı en yüksek değer ve tarihi (Örn: `€150.0M` - 2024).
  - **İlk Kayıtlı Değeri (`first_value`):** Profesyonel kariyerine başladığı ilk değer.
  - **Toplam Kariyer Değer Artışı:** Yüzdesel ve tutarsal büyüme (Örn: `+%1.250 · +€95M`).
  - **Görsel Alan Çizgi Grafiği (Area Chart):** SVG tabanlı interaktif kariyer değer eğrisi.

---

## 4. Hakem (Referee) Verileri ve Detayları

Hakemler sekmesinde (`/api/referees`, `/api/referees/{name}`) sunulan kapsamlı hakem istatistikleri ve maç yönetim profilleri:

### 4.1 Hakem Kimlik ve Sezonluk Yönetim Profili
* **Hakem Adı (`referee_name`):** Örn: *Michael Oliver*, *Anthony Taylor*, *Paul Tierney*.
* **Sezon Kapsamı:** Güncel sezon (`2026_27`), geçmiş sezonlar (`2025_26`, `2024_25`, `2023_24`, `2022_23`) veya Kariyer (`all`).
* **Yönettiği Maç Sayısı (`matches_count`):** Seçilen sezonda veya kariyerinde düdük çaldığı lig maçı adedi.

---

### 4.2 Disiplin ve Kart İstatistikleri
* **Toplam Sarı Kart (`total_yellow_cards`):** Gösterdiği toplam sarı kart adedi.
* **Maç Başına Sarı Kart (`avg_yellow_cards`):** Sezonluk sarı kart ortalaması (Örn: `4.12`).
* **Toplam Kırmızı Kart (`total_red_cards`):** Gösterdiği doğrudan veya çift sarıdan kırmızı kart sayısı.
* **Maç Başına Kırmızı Kart (`avg_red_cards`):** Kırmızı kart ortalaması (Örn: `0.18`).
* **Toplam Kart (`total_cards`):** Sarı + Kırmızı kart toplamı.
* **Maç Başına Ortalama Kart (`avg_cards`):** Hakemin kart çıkarma sıklığı (Örn: `4.30 kart/maç`).

---

### 4.3 Faul Ortalamaları ve Yönetim Karakteri (Katılık Etiketi)
* **Toplam Faul (`total_fouls`):** Çaldığı toplam faul sayısı.
* **Maç Başına Ortalama Faul (`avg_fouls`):** Karşılaşma başına çaldığı düdük sayısı (Örn: `22.4 faul/maç`).
* **Yönetim Karakteri / Katılık Etiketi (`strictness_label`):**
  - **"Yüksek Kart Eğilimi" (Kırmızı Rozet):** Maç başına kart ortalaması `4.6+` olan veya maçlarının `%70`'inden fazlasında 4+ kart çıkan sert hakemler.
  - **"Akıcı Oyun / Az Kart" (Yeşil Rozet):** Maç başına kart ortalaması `3.2` ve altında kalan, oyunu oynatmaya meyilli hakemler.
  - **"Dengeli Yönetim" (Sarı Rozet):** Lig ortalamasında (`3.3 - 4.5` arası) düdük çalan standart hakemler.

---

### 4.4 3.5+ Kart Üstü Yönetim Yüzdesi
* **3.5 Kart Üstü Maç Sayısı (`over_3_5_cards_count`):** En az 4 kart gösterdiği maç sayısı.
* **3.5 Kart Üstü Yönetim Oranı (`over_3_5_pct`):** Yönettiği maçların yüzde kaçında 4 ve üzeri kart çıktığı (Görsel ilerleme çubuğu ile gösterilir, Örn: `%72.4`).

---

### 4.5 Takım Bazlı Disiplin Dağılımı (Team Breakdown)
Hakem profilinde, kariyerinde veya sezonda **en çok kart gösterdiği takımlar** listelenir:
* Takım Adı ve ID'si.
* Yönettiği Maç Sayısı.
* O Takıma Gösterdiği Sarı Kart Sayısı.
* O Takıma Gösterdiği Kırmızı Kart Sayısı.
* Ağırlıklı kart puanına göre sıralı ilk 8 takım.

---

### 4.6 Hakem Maç Geçmişi Arşivi ve Kariyer Karşılaştırması
* **Yönettiği Tüm Maçların Listesi:**
  - Hafta, Tarih, Stadyum.
  - Ev Sahibi ve Deplasman Takımları, Logoları ve Maç Skoru.
  - Maçta Çıkan Sarı ve Kırmızı Kart Sayıları.
  - Tıklandığında o karşılaşmanın tam detay sayfasına gitme.
* **Sezon vs Kariyer Kıyaslaması:**
  - Hakemin o sezondaki performansı ile tüm kariyeri boyunca çıktığı maçlardaki kart ve faul ortalamaları yan yana karşılaştırılır.

---

### 4.7 Model Tahminlerine Hakem Modülatörü Olarak Etki
Yapay Zeka tahmin motorunda kart ve disiplin tahminleri üretilirken:
* Karşılaşmaya atanan ana hakemin kart ortalaması lig normuna oranlanır (`ref_factor = referee_avg_cards / 4.15`).
* Kart beklentisi bu katsayı ile modüle edilir (`delta_cards`). Maç kart baremleri (3.5 Üst, 4.5 Üst) doğrudan atanan hakemin katılığına göre güncellenir.

---

## 5. Veri Mimarisi, Kaynaklar ve API Uç Noktaları

### 5.1 Veri Tabanı Şemaları (Database Architecture)
Uygulama `data/premier_league.db` (SQLite) ve `data/processed/*.parquet` katmanlarını birlikte kullanır:

#### SQLite Tabloları:
1. `matches`: 1.900 karşılaşmanın skorları, tarihleri, hakemleri, temel korner/taç/şut/faul/kart/xG özetleri.
2. `external_match_xg`: TheStatsAPI üzerinden çekilen doğrulanmış ev ve deplasman xG değerleri ve kalite etiketleri.
3. `external_match_odds`: Bet365, Pinnacle, Betfair vb. şirketlerin 1X2, 2.5 Alt/Üst, KG Var/Yok açılış ve kapanış oranları.
4. `referees`: Hakemlerin sezonluk ve kariyer ("all") maç sayısı, sarı/kırmızı kart ve faul ortalamaları, katılık etiketleri.
5. `team_market_values`: Transfermarkt kulüp piyasa değerleri ve kadro büyüklükleri.
6. `player_market_values`: Transfermarkt oyuncu piyasa değerleri, mevkileri, yaşları ve uyrukları.
7. `player_market_value_history_cache`: Oyuncuların tüm kariyer değer gelişim eğrilerinin JSON önbelleği.
8. `team_transfers_cache` & `team_season_transfers_cache`: Kulüp transferlerinin (gelen/giden) önbelleği.
9. `model_match_audit`: Modelin geriye dönük ve canlı tahmin başarılarının, sapmalarının ve value edge analizlerinin denetim tablosu.
10. `predictions_cache`: Üretilen tahminlerin runtime önbelleği.

#### Parquet ve JSON Veri Setleri:
* `matches_summary_all.parquet`: 5 sezonun tüm karşılaşma özet istatistikleri.
* `features_matches_all.parquet`: Makine öğrenimi için üretilmiş 200+ rolling, EWMA, Elo, PPG, GDPG ve taktiksel özellik.
* `shots_events_all.parquet`: Tüm şut, gol, blok ve kurtarış anlarının koordinat ve oyuncu bazlı olay kayıtları.
* `players_registry.json`: 1.000+ Premier League futbolcusunun resmi sicil bilgileri.
* `player_match_logs.json`: Futbolcuların maç bazlı oynama süreleri, gol ve asist günlükleri.
* `manager_changes.json`: 5 sezonun doğrulanmış teknik direktör atama ve ayrılma takvimi.
* `team_staff.json`: Kulüplerin resmi teknik heyet listeleri.

---

### 5.2 Veri Kaynakları ve Akış Hatları (Ingestion Pipelines)
* **Opta / PulseLive (Premier League Resmi Feed):** Fikstür, resmi skorlar, ilk 11 dizilişleri, oyuncu değişiklikleri, maç olayları, 244 farklı maç içi istatistik.
* **TheStatsAPI:** Şut kalitesi bazlı bağımsız ve doğrulanmış Beklenen Gol (xG) ve piyasa oranları.
* **Transfermarkt:** Kulüp ve oyuncu piyasa değerleri, 5 yıllık kulüp değer trendleri, oyuncu kariyer değer eğrileri, gelen/giden transfer hareketleri ve bonservis bedelleri.
* **Bahis Şirketleri:** Bet365, Pinnacle, Betfair Exchange kapanış ve açılış piyasa çizgileri.

---

### 5.3 REST API Uç Noktaları Özeti (Server Endpoints)
| Uç Nokta (Endpoint) | Metot | Açıklama |
| :--- | :---: | :--- |
| `/api/fixtures/grouped` | GET | Fikstürün haftalara ve günlere göre gruplanmış tam listesi, hakem ve xG verileriyle. |
| `/api/fixtures` | GET | Filtrelenebilir düz maç listesi. |
| `/api/standings` | GET | Premier League puan durumu (Genel, Ev, Deplasman ve son 5 maç formu). |
| `/api/match/{match_id}/details` | GET | Maçın kadroları, dizilişleri, oyuncu reytingleri, timeline olayları ve 5 kategoride takım istatistikleri. |
| `/api/match/{match_id}/odds` | GET | Maçın bahis şirketleri bazında açılış ve kapanış oranları. |
| `/api/match/{match_id}/recent-form` | GET | Karşılaşma öncesinde iki takımın son 5 maçlık form dizilimi. |
| `/api/predict` | GET | İki takım arasında yapay zeka maç sonucu (1X2), goller, korner, kart, taç, ofsayt, kurtarış ve ilk 11 modülatör tahminleri. |
| `/api/teams` | GET | Premier League kulüpler listesi ve armaları. |
| `/api/teams/profile` | GET | Kulüp profili, maç arşivi, kadrosu, Transfermarkt değeri ve 5 yıllık gelişimi. |
| `/api/teams/tactics` | GET | Takımın 27 metrikten oluşan Opta taktik profili ve lig ortalamasıyla kıyaslaması. |
| `/api/teams/scenarios` | GET | Takımın skor eşitken, öndeyken ve gerideyken sergilediği şut ve korner temposu. |
| `/api/teams/attacking-leaders`| GET | Takımın en etkili 3 hücumcusu, şut asistleri ve gol katkıları. |
| `/api/teams/staff` | GET | Takımın teknik direktör ve antrenör kadrosu. |
| `/api/teams/manager-changes` | GET | Sezonluk teknik direktör değişiklikleri ve maç eşleşmeleri. |
| `/api/teams/manager-performance` | GET | Bir teknik direktörün takımla çıktığı maçların rakip bazlı karnesi. |
| `/api/teams/{team_id}/transfers` | GET | Takımın sezonluk gelen ve giden transferleri, bonservisleri ve net bilançosu. |
| `/api/players` | GET | Oyuncu arama dizini (takım ve sezona göre filtrelenebilir). |
| `/api/players/profile` | GET | Oyuncunun sezonluk istatistikleri, maç günlüğü ve maç puanları. |
| `/api/players/{player_id}/rating` | GET | Oyuncunun son 5 maçlık dinamik form puanı, trendi ve kart riski. |
| `/api/players/{player_id}/market-value-history` | GET | Oyuncunun tüm kariyeri boyunca Transfermarkt piyasa değeri değişim eğrisi. |
| `/api/referees` | GET | Hakemler listesi, maç sayıları, kart ve faul ortalamaları, katılık etiketleri. |
| `/api/referees/{name}` | GET | Hakemin detaylı profili, yönettiği maçlar ve en çok kart gösterdiği takımlar. |
| `/api/model-audit` | GET | Modelin out-of-sample tahmin doğruluğu, hit oranları ve piyasa değer avantajı (Edge) denetimi. |

---

### 5.4 Ön Yüz Bileşenleri (Frontend UI Mapping)
* **Fikstür ve Maçlar:** `FixturesTab.jsx`, `FixturesGameweeksView.jsx`, `FixturesStandingsView.jsx`, `FixtureMatchRow.jsx`, `FixtureMatchCard.jsx`.
* **Maç Detayı:** `MatchDetailPage.jsx`, `MatchScoreboard.jsx`, `MatchTimelineTab.jsx`, `MatchStatsTab.jsx`, `MatchLineupsTab.jsx`, `PitchLineup.jsx`, `MatchPredictionTab.jsx`, `MatchPageOddsTab.jsx`, `PlayerMatchPerformanceModal.jsx`.
* **Takım Profilleri:** `TeamProfilesTab.jsx`, `TeamProfileHero.jsx`, `TeamGameProfileSection.jsx`, `TeamSquadSection.jsx`, `TeamFixturesSection.jsx`, `TeamTransfersSection.jsx`, `TeamManagerHistorySection.jsx`, `TeamManagerPerformanceModal.jsx`, `TeamMarketValueDialogs.jsx`.
* **Oyuncu Profilleri:** `PlayerProfilesTab.jsx`, `PlayerSearchPanel.jsx`, `PlayerProfileHeader.jsx`, `PlayerMatchHistory.jsx`, `PlayerMarketValueHistoryModal.jsx`.
* **Hakem Profilleri:** `RefereesTab.jsx`.
* **Model Denetimi:** `ModelAuditTab.jsx`, `AuditMatchCard.jsx`.
