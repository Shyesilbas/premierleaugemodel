# LaLiga Gol Modeli (Alt/Üst 1.5, 2.5, 3.5 ve Karşılıklı Gol)

**Rapor tarihi:** 26 Ekim 2026 (`v1.0`)
**Kod:** `src/models/evaluate_league_goal_models.py` (dış sezon değerlendirmesi), `src/models/train_league_goals.py` (üretim), `src/models/goals_model.py` ve `src/models/train_goals.py` (PL'nin gol modeli ve seçim kodu), `src/features/build_league_pl_features.py` (özellikler), `src/api/league_prediction.py` (servis)
**Ham sonuçlar (tek kaynak):** `docs/reports/models/la_liga_goal_model_eval.json`
**Yeniden üretim:** `python3 -m src.models.evaluate_league_goal_models --competition la_liga` (yaklaşık 1 dakika), ardından `python3 -m src.models.train_league_goals --competition la_liga`
**Üretim dosyası:** `models/production/la_liga/goals_models_v1.joblib`

## 1. Karar

Üç aday aynı yürüyen protokolle (her dış sezon yalnızca ondan önceki sezonlarla eğitilir; dış sezonlar 2024/25 ve 2025/26, kilitli 2026/27 yalnızca izlenir) skorlandı. Her adayın skor matrisi, üretim 1X2 modelinin kalibre olasılıklarına hizalanır (serviste olduğu gibi). Her pazar eğitim taban oranıyla eşli bootstrap (10.000 çekiliş, tohum 42) ile karşılaştırıldı ve 15 testlik ailenin tamamı Benjamini-Hochberg ile düzeltildi. Kural çalıştırmadan önce betiğin başlığına yazıldı: bir pazar, ancak bir aday taban oranını anlamlı biçimde (q < 0,05) geçerse modelden sunulur; geçenler arasında ortalama log-loss'u en düşük olan kazanır.

| Pazar | Servis edilen | Eğitim taban oranı |
|---|---|---|
| Alt/üst 1.5 | PL gol modeli | %73,2 |
| Alt/üst 2.5 | PL gol modeli | %48,1 |
| Alt/üst 3.5 | `baseline` (taban oranı) | %24,8 |
| Karşılıklı gol | `baseline` (taban oranı) | %52,6 |

## 2. Adaylar

- **`current`:** önceki üretim modeli; 118 LaLiga özelliği üzerinde iki bağımsız Poisson oran modeli (ceza CV ile seçilir), Dixon-Coles rho = -0,04 sabit.
- **`pl_feature_model`:** PL'nin gol modeli (`FeatureGoalModel`), PL özellik tanımlarıyla. Özellik kümesi ve ceza, PL'nin kendi ileriye dönük katlı seçimiyle (`select_blend_config`) yalnızca eğitim sezonlarından seçilir; her dış sezonda seçim aynı çıktı: 13 özellikli kompakt küme, ceza 1,0, Dixon-Coles ağırlığı 0. Kompakt küme: Elo (ev ve deplasman), xG ve isabetli şutun hücum/savunma üstel ortalamaları, beklenen maç şutu ve xG.
- **`dixon_coles`:** takım hücum/savunma gücü, 365 günlük yarı ömür, özelliksiz.

## 3. Sonuçlar (iki dış sezon, 760 maç)

Fark = aday eksi eğitim taban oranı log-loss'u (negatif aday lehine); q, 15 testlik aile üzerinden düzeltilmiş değer.

| Aday | Pazar | Fark [%95 aralık] | q |
|---|---|---|---|
| `pl_feature_model` | Alt/üst 1.5 | -0,0187 [-0,0283, -0,0088] | 0,006 |
| | Alt/üst 2.5 | -0,0200 [-0,0319, -0,0079] | 0,011 |
| | Alt/üst 3.5 | -0,0133 [-0,0262, -0,0003] | 0,095 |
| | Karşılıklı gol | -0,0003 [-0,0068, +0,0062] | 0,927 |
| | Toplam gol MAE | -0,0389 [-0,0622, -0,0154] | 0,011 |
| `current` | Alt/üst 1.5 | -0,0117 [-0,0236, +0,0009] | 0,118 |
| | Alt/üst 2.5 | -0,0174 [-0,0311, -0,0034] | 0,049 |
| | Alt/üst 3.5 | -0,0112 [-0,0264, +0,0040] | 0,190 |
| | Karşılıklı gol | -0,0038 [-0,0087, +0,0011] | 0,182 |
| | Toplam gol MAE | -0,0283 [-0,0558, -0,0011] | 0,095 |
| `dixon_coles` | Alt/üst 1.5 | -0,0117 [-0,0268, +0,0038] | 0,182 |
| | Alt/üst 2.5 | -0,0081 [-0,0263, +0,0100] | 0,438 |
| | Alt/üst 3.5 | -0,0054 [-0,0245, +0,0135] | 0,604 |
| | Karşılıklı gol | +0,0144 [-0,0000, +0,0293] | 0,095 |
| | Toplam gol MAE | -0,0440 [-0,0780, -0,0098] | 0,047 |

Sezon sezon ortalama log-loss (model / taban oranı), `pl_feature_model`:

| Sezon | 1.5 | 2.5 | 3.5 | KG | Skor NLL |
|---|---|---|---|---|---|
| 2024/25 | 0,5724 / 0,5898 | 0,6723 / 0,6935 | 0,5293 / 0,5507 | 0,6898 / 0,6934 | 2,766 |
| 2025/26 | 0,5161 / 0,5361 | 0,6755 / 0,6944 | 0,5632 / 0,5683 | 0,6931 / 0,6900 | 2,768 |
| 2026/27 (izleme) | 0,5464 / 0,5502 | 0,6606 / 0,6990 | 0,6535 / 0,6967 | 0,6837 / 0,6853 | 3,018 |

- **1.5 ve 2.5 üstü:** PL gol modeli iki pazarda da taban oranı düzeltmeden sonra anlamlı biçimde geçiyor. İki dış sezonda da her ikisinde yön aynı (modelin lehine). `current` 2.5 üstünde de eşiği geçiyor (q = 0,049) ama 15 testlik aileyle sınırda; `pl_feature_model` hem daha düşük kayıp hem daha küçük q veriyor ve kazanıyor.
- **3.5 üstü:** `pl_feature_model` yön olarak lehine (-0,0133, aralık sıfıra çok yakın: -0,0262 ile -0,0003) ama q = 0,095, kapıyı geçemedi; taban oranı sunulur.
- **Karşılıklı gol:** hiçbir aday taban oranını geçemiyor. `dixon_coles` taban oranından kötü yönde. LaLiga'da bu pazar için ayırt edilebilir bir sinyal bulunamadı.
- **Önceki raporla fark:** [la_liga_outcome.md](la_liga_outcome.md) Bölüm 5'teki q değerleri beş testlik ailenin değerleridir (en iyisi 2.5 üstü q = 0,081, hiçbiri geçmedi). Burada aile üç aday ve beş ölçüyle 15 teste çıktığı için `current` için değerler farklıdır (2.5 üstü q = 0,049); her iki rapor da kendi ailesini belirtir. Karar, tek kural ve tek aile üzerinden verilmiştir.

## 4. Servis

`goals_models_v1.joblib` PL gol modelini, seçilen özellik adlarını, pazar bazlı kapıyı (`skill_gate`) ve eğitim taban oranlarını taşır. Serviste skor matrisi PL tanımlı özellik tablosundan çıkar, üretim 1X2 modeline hizalanır (böylece 1X2 ve gol pazarları tutarlıdır), 1.5 ve 2.5 üstü modelden, 3.5 üstü ve karşılıklı gol taban oranından sunulur ve `baseline` etiketi taşır. Üst çizgiler alt çizgiyi aşamaz (1.5 >= 2.5 >= 3.5). Beklenen ev, deplasman ve toplam gol bu matristen gelir. Yedek olarak eski iki Poisson modeli 1X2 dosyasında durur ve gol dosyası yoksa kullanılır.

## 5. Bilinen sınırlar

- Üç aday ve 15 test için çoklu test düzeltmesi yapıldı, ama adaylar çalıştırmadan önce sabitlenmişti; yine de aday kümesi küçük bir "forking paths" riski taşır.
- Karşılıklı gol pazarı taban oranında kaldı; 3.5 üstü sınırda (q = 0,095) ve bir ila iki ek sezonla yeniden değerlendirilmelidir.
- Dixon-Coles adayı özelliksizdir ve ilk dış sezonda yalnızca iki sezonluk veriyle çalışır; tek başına zayıf kalması beklenen bir sonuçtur.
- Kilitli 2026/27 izlenir ama karara girmez (97 maç). Orada 3.5 üstünde `pl_feature_model` (0,6535) `current`'tan (0,6471) kötüdür; örneklem küçük.
- Değerlendirmede 1X2 hizalaması dış sezon başına üretim modelinin yürüyen tahminleriyle yapıldı (örneklem dışı).
