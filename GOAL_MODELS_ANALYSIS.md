# Gol / 2.5 Üst / KG Modelleri — Problem Analizi ve Çözüm Yöntemi

**Tarih:** 19 Ekim 2026
**Kapsam:** `models/production/goals_models_v1.joblib`, `src/models/goals_model.py`, `src/models/dixon_coles.py`, `src/models/train_goals.py`, `src/models/evaluate_goal_models.py`, `src/api/server.py`
**Durum:** Analiz. Kodda değişiklik yapılmadı.

## Yöntem

- **Dış sezon değerlendirmesi:** 2023/24, 2024/25 ve 2025/26, toplam 1.140 maç. Her sezon yalnızca kendinden önceki sezonlarla eğitildi.
- **Kilitli sezon:** 2026/27 hiçbir seçim kararında kullanılmadı; yalnızca raporlandı.
- **Belirsizlik:** Eşleşmeli bootstrap, 2.000 örnek (`paired_bootstrap_delta`).
- **Piyasa kıyası:** `external_match_odds` tablosundaki Bet365 `last_seen` oranları, marjı (vig) çıkarılmış hâlleriyle kullanıldı. 2.5 Üst için 1.134 maç, KG için 1.138 maç. Oranlar özellik olarak değil, yalnızca kıyas noktası olarak kullanıldı.
- **Analiz betikleri:** `goal_diag.py` (teşhis) ve `goal_nested.py` (iç içe test). Oturumun geçici dizinindeydiler; kalıcı olmaları gerekiyorsa `scratch/` altına taşınmalı.

---

## 1. Mevcut Metrikler

| Pazar | Model LL | Prior LL | Δ prior (%95 CI) | AUC | Piyasa kıyası |
|---|---|---|---|---|---|
| 2.5 Üst | 0.6803 | 0.6848 | −0.0044 [−0.0105, +0.0014] | ~0.56 | Model piyasadan **+0.0115 kötü**, CI [+0.0012, +0.0210] |
| KG | 0.6823 | 0.6849 | −0.0026 [−0.0071, +0.0019] | **~0.52** | Model piyasadan +0.0069 kötü, CI [−0.0006, +0.0138], P(piyasa daha iyi) %97 |
| 1.5 Üst | 0.4742 | — | −0.0043 [−0.0091, +0.0000] | — | — |
| 3.5 Üst | 0.6582 | — | +0.0006 (prior'dan kötü) | — | — |

**Piyasanın kendi performansı (Δ prior):**
- 2.5 Üst: −0.0326, −0.0081 ve −0.0069 (sezon sırasıyla). AUC 0.57–0.58.
- KG: −0.0094, CI [−0.0168, −0.0015]. AUC 0.54–0.59.

**2026/27 kilitli sezon** (69 maç, yalnızca rapor):
- 2.5 Üst: model 0.6763, prior 0.6932.
- Oranı olan 66 maçta: model 0.6794, piyasa 0.6849.
- Örnek çok küçük; anlamlı değildir.

### Kazancın ne kadarı gerçek?

"Sabit Poisson", her maça aynı λ'yı veren, yalnızca lig ortalamasından oluşan bir Poisson modelidir. Bu model bile prior'u geçiyor:

| Pazar | Sabit Poisson Δ prior | Üretim modeli Δ prior | Modelin ayırt edici katkısı |
|---|---|---|---|
| 2.5 Üst | −0.0023 (CI sıfırı dışlıyor) | −0.0044 | **≈ −0.002** |
| KG | −0.0032 | −0.0026 | **≈ 0, hatta negatif** |

### Sinyal nerede var, nerede yok?

| Ölçüm | Değer |
|---|---|
| Tahmin edilen toplam gol (λ_ev + λ_dep) ile gerçek toplam gol korelasyonu | 0.06 – 0.14 |
| Tahmin edilen gol farkı (λ_ev − λ_dep) ile gerçek gol farkı korelasyonu | 0.39 – 0.44 |

**Sonuç:** Model gol farkını (kimin kazanacağını) biliyor. Maçta kaç gol olacağını bilmiyor.

---

## 2. Problemler

### ✅ ÇÖZÜLDÜ — P1 — Feature-Poisson üretimde fiilen kapalı

Üretim ayarı: `compact`, α=30, w_dc=0.5.

**Belirti:**
- En büyük standartlaştırılmış katsayı **0.0097**. Yani bir standart sapmalık değişim λ'yı %1'den az oynatıyor.
- Bu modelin tahmin ettiği toplam gol maçtan maça yalnızca 0.04 gol değişiyor; pratikte sabit.
- Dolayısıyla blend formülü `λ = λ_DC^0.5 · λ_Feat^0.5` fiilen "Dixon-Coles λ'sını yarı yarıya lig ortalamasına çek" anlamına geliyor.

**Neden:** sklearn `PoissonRegressor` şu amaç fonksiyonunu küçültür:

```
1/(2n) · Σ deviance + α/2 · ‖w‖²
```

Ceza, toplam değil **ortalama** deviance'a ekleniyor. Bu ölçekte α=1 bile güçlü bir ceza; α=30 modeli sıfırlıyor. `BLEND_GRID` içindeki α ∈ {1, 3, 10, 30} ızgarası tamamen bu aşırı ceza bölgesinde kalıyor.

Kanıt (dış sezon ortalaması, skor matrisi NLL; düşük daha iyi):

| Model | Skor NLL | Gol farkı korelasyonu |
|---|---|---|
| Üretim blend'i (compact, α=30, w=0.5) | 3.0248 | 0.386 |
| Feature modeli (full, α=1) | 2.9735 | 0.438 |
| Feature modeli (compact, α=0.1) | 2.9845 | 0.421 |
| Sabit Poisson | 3.0959 | 0 |

### ✅ ÇÖZÜLDÜ — P2 — Seçim ölçütü düşük güçlü, 1-SE kuralı modeli boş modele itiyor

`select_blend_config` (`src/models/train_goals.py`) iki sorun taşıyor:

- **Zayıf ölçüt:** Ayarlar yalnızca **2.5 Üst ikili log-loss**'una göre seçiliyor. Bu ölçüt, toplam gol sinyali zayıf olduğu için ayarları birbirinden ayıramıyor; hemen hepsi "berabere" çıkıyor.
- **Yanlış yöne iten beraberlik kuralı:** Beraberlikte 1-SE kuralı en güçlü L2'yi seçiyor (`-key[1]`), bu da her seferinde α=30, yani neredeyse boş bir feature modeli demek.
- **Kaybedilen bilgi:** Skor matrisinin asıl taşıdığı bilgi (gol farkı, takım bazlı goller) seçimde hiç ölçülmüyor.

### P3 (Ç5 denendi, çözmedi) — Dixon-Coles toplam gol hacminde aşırı emin

- DC'nin toplam λ'sı maçtan maça 0.42 gol değişiyor; feature modelinin ve gerçek sinyalin taşıyabileceğinden çok daha fazla.
- Tek başına DC prior'dan kötü: 2.5 Üst'te +0.0031, KG'de +0.0069.
- `DixonColesModel(ridge=1.0)` hücum ve savunma parametrelerini yeterince küçültmüyor.
- Şu anki blend bunu dolaylı bir küçültme ile telafi ediyor (bkz. P1).

### ✅ ÇÖZÜLDÜ — P4 — Değerlendirme kapısı çok kolay geçiliyor

`evaluate_goal_models.evaluate_outer_seasons` içindeki kapı:

- **Zayıf kıyas noktası:** Yalnızca eğitim setinin Üst oranıyla, yani prior ile kıyaslıyor. Oysa sabit Poisson tek başına bu prior'u geçiyor.
- **Anlamlılık zorunlu değil:** `ci_excludes_zero` raporlanıyor ama kararı etkilemiyor.
- **Eksik kıyaslar:** Piyasa ve sabit Poisson kıyası hiç yok.
- **Kapsam dar:** Kapı yalnızca 2.5 Üst'e bakıyor; KG için hiçbir kapı yok, ama KG yine de API'de tahmin olarak sunuluyor.

### ✅ ÇÖZÜLDÜ — P5 — KG tahmin gibi sunuluyor ama ayırt etme gücü yok

- `server.py` "KG Var/Yok" etiketini %50 eşiğiyle üretiyor.
- KG AUC'si ~0.52 ve model sabit Poisson'dan kötü.
- Kullanıcı bu etiketi bilgi taşıyan bir tahmin olarak okuyor.

### P6 (Ç4 denendi, çözmedi) — Toplam gol bilgisi eksik (asıl tavan)

| Kaynak | 2.5 Üst AUC | KG AUC |
|---|---|---|
| Bet365 piyasası | 0.57 – 0.58 | 0.54 – 0.59 |
| Bizim model | 0.55 – 0.58 | 0.51 – 0.53 |

- Özellik setinde (takım bazlı xG ve isabetli şut EWMA'ları, Elo) maçın gol hacmini belirleyen bilgi yok.
- Bu, ayarla veya dağılım şekliyle çözülebilecek bir sorun değil. Daha önce denenen COM-Poisson, zaman ağırlığı, izotonik kalibrasyon ve XGBoost residual denemeleri de bu yüzden başarısız oldu (`docs/reports/models/goals_model.md`, "Reddedilen Deneyler").

---

### ❌ DENENDİ, REDDEDİLDİ — Ç6 — Ek özellik grupları (P6, 19 Ekim 2026)

Ç4'ün devamı. Mevcut verilerle dört özellik grubu, Ç1 prosedürüyle (iç içe, 3 dış sezon, 1.140 maç) tek tek ve hep birlikte sınandı. Hepsi maç öncesi bilgiyle hesaplandı (`shift(1)` / yalnızca önceki satırlar).

| Grup | Özellikler | Skor NLL Δ | 2.5 Üst Δ | KG Δ |
|---|---|---|---|---|
| A Dinlenme | ev/dep dinlenme günü (en çok 14) | 0.0000 | +0.0001 [−0.0006, +0.0009] | −0.0002 [−0.0007, +0.0004] |
| B Hakem | önceki maçlardan hakem gol ortalaması (küçültülmüş), faul, kart | −0.0007 [−0.0018, +0.0004] | +0.0005 [−0.0000, +0.0010] | +0.0002 [−0.0002, +0.0006] |
| C Teknik direktör | son atamadan bu yana gün (en çok 120) | +0.0002 | +0.0005 [+0.0000, +0.0009] | −0.0002 [−0.0007, +0.0002] |
| D Kadro/savunma | ilk 11'de eksik düzenli oyuncu sayısı; XI'ın önceki gol yeme oranı | −0.0013 [−0.0032, +0.0006] | +0.0003 [−0.0003, +0.0010] | +0.0002 [−0.0002, +0.0006] |
| Hepsi | A+B+C+D | −0.0018 [−0.0045, +0.0007] | **+0.0015 [+0.0002, +0.0027]** | +0.0000 [−0.0009, +0.0010] |

Baz: skor NLL 2.9786, 2.5 Üst 0.6774, KG 0.6804. Pozitif Δ = kötüleşme.

- **Karar:** Kabul ölçütü (2.5 Üst veya KG'de anlamlı iyileşme) hiçbir grupta sağlanmadı; 2.5 Üst'te hiçbiri iyileştirmedi, hepsi birlikte anlamlı kötüleştirdi (gürültü özellikleri eklemek aşırı uyum yapıyor). Kod repoya alınmadı.
- **Sınırlar:** Dinlenme günü yalnızca lig maçlarından hesaplandı (Avrupa kupaları ve milli maçlar yok). Hava durumu, pres/duran top istatistikleri denenmedi (veri yok).
- **Sonuç:** P6 (toplam gol bilgisi eksik) bu veri kümesinde, mevcut kaynaklarla çözülemiyor. Kalan yollar: daha fazla geçmiş sezon veya yeni veri kaynağı.

### P7 — Ç1/Ç2 sırasında fark edilen yeni sorunlar

Ç1 ve Ç2 uygulanırken ortaya çıktı. Hepsi açık.

| # | Sorun | Veri / kanıt | Önerilen çözüm |
|---|---|---|---|
| P7a | **Kapı hâlâ zayıf (v1.4 güncellemesi: prior'a karşı CI artık sıfırı sınırda dışlıyor, [−0.0146, −0.0001]; sabit Poisson'a karşı hâlâ içeriyor, [−0.0119, +0.0019]; KG kapısına anlamlılık eklendi):** 2.5 Üst kapısı yalnızca ortalama farkın negatif olmasını istiyor; anlamlılık zorunlu değil. | Üretim modeli − sabit Poisson = −0.0023, CI [−0.0094, +0.0047] (sıfırı içeriyor). Kapı yine de `passed: True`. | Kapıyı CI'a bağlamak mı, yoksa "uyarı" olarak bırakmak mı, karar gerekiyor. CI zorunlu olursa üretim modeli kapıdan düşer ve `train_goals` hata verir. |
| P7b | **Kalibrasyon biraz bozuldu:** Ç1 sonrası 2.5 Üst ECE yükseldi. | ECE 0.0459 → 0.0494 (monotonluk payı 0.56 → 0.67). Nedeni incelenmedi. | Ç5 ile birlikte bakılmalı; ayrıca ham olasılıkların ayrı bir kalibrasyon testi eklenmeli. |
| P7c | ✅ ÇÖZÜLDÜ — **Skor NLL'i pipeline'da raporlanmıyor.** Ç1'in asıl ölçütü olan skor NLL'i `evaluate_goal_models` çıktısında yok; önce/sonra kıyası geçici bir betikle (`nll.py`) yapıldı. | Betik repo dışında, scratchpad'de. | Skor NLL'ini (ve gol farkı korelasyonunu) `evaluate_outer_seasons` sonuçlarına ekle. |
| P7d | **Test örtüsü zayıf.** `pytest` bu makinedeki hiçbir Python'da kurulu değil; testler elle çağrıldı. `test_select_blend_config_returns_a_grid_point` yalnızca "ızgara noktası döner" diye bakıyor, NLL ölçütünü ve yeni kapıları (null, `btts_gate`, piyasa kıyası) sınamıyor. | Yeni kapılar için test yok. | `pytest`i bağımlılıklara ekle; NLL seçimi ve null kapısı için küçük sentetik testler yaz. |
| P7e | ✅ ÇÖZÜLDÜ — **Kapı sonucu artifact/API'ye bağlı değil.** `btts_gate.passed` şu an `False`, ama bunu `server.py` ve frontend kullanmıyor; KG hâlâ model tahmini gibi sunuluyor. | KG − sabit Poisson = +0.0012; KG − piyasa = +0.0075, CI [+0.0014, +0.0137]. | Ç3 kapsamında. |
| P7f | **Piyasa kıyası kırılgan.** `_market_probabilities` veritabanı yolunu çalışma dizinine göre sabit alıyor; oranlar yalnızca Bet365, tek zaman damgası (`last_seen`), kapanış oranı olduğu doğrulanmadı (bkz. §5). | 2.5 Üst için 1.134, KG için 1.138 maç. | Yolu yapılandırmadan al; zaman damgasını doğrula. |
| P7g | **3.5 Üst iyileşmesi doğrulanmadı.** Üretim OOF'unda 3.5 Üst 0.6497 → 0.6468 düştü, ama dış sezon CI'ı hesaplanmadı. | Dış sezonda önceki ölçüm: 3.5 Üst +0.0006 (prior'dan kötü). | CI ile doğrula; aksi hâlde "iyileşti" denmesin. |
| P7h | ✅ KISMEN ÇÖZÜLDÜ — **Belgeler eski sayılarda.** Belgeler 19 Ekim 2026'da v1.4 değerleriyle güncellendi (`goals_model.md` §11.11, ana rapor, `README.md`, `PROJECT_STATUS.md`, `AI_CONTEXT.md`); commit hâlâ yapılmadı. Ç1/Ç2 sonrası `goals_model.md`, özet karne, `README.md`, `PROJECT_STATUS.md`, `AI_CONTEXT.md` güncellenmedi; değişiklikler commit edilmedi. | — | Bölüm 4'teki sırayla güncelle. |

### ✅ ÇÖZÜLDÜ — P8 — Tek başına feature modeli, üretim blend'ini yeniyor (P7c çıktısında fark edildi)

`evaluate_goal_models` artık her aday için skor NLL'ini raporluyor. Dış sezon ortalaması (3 sezon, 1.140 maç):

| Model | Skor NLL | 2.5 Üst LL |
|---|---|---|
| Feature, α=3 | **2.9722** | **0.6753** |
| Feature, α=10 | 2.9829 | 0.6775 |
| Feature, α=30 | 3.0105 | 0.6793 |
| **Üretim blend'i (iç içe seçim)** | 3.0003 | 0.6802 |
| Dixon-Coles (hl 365) | 3.0469 | 0.6879 |
| Feature, α=100 / 300 | 3.0523 / 3.0784 | 0.6809 / 0.6818 |

- **Bulgu:** Feature α=3 modeli blend'den skor NLL'inde 0.028, 2.5 Üst LL'inde 0.005 daha iyi. Blend'in ızgarası (`dc_weight=0`, α=3) bu modele çok yakın bir noktayı içeriyor, ama iç içe seçim onu seçmedi (iç katlar 0.25/0.5 ağırlığı seçti).
- **Dikkat:** Bu karşılaştırma iç içe değil. Beş α'dan en iyisi sonradan seçildi (üçü blend'den iyi), seçim yanlılığı küçük ama sıfır değil. Doğrulama gerekiyor.
- **Olası nedenler (test edilmedi):** (a) iç katlarda DC'li ayarlar gürültüyle seçiliyor, (b) blend'in `rho`'su DC ile ortalanıyor, (c) DC bu veri hacminde feature modeline bilgi katmıyor.
- **Önerilen adım:** `dc_weight=0` ve `dc_weights=[0]` (DC'siz) ızgarasını iç içe sınamak; kazanırsa DC bileşeni ve ilgili kodu kaldırıp mimariyi sadeleştirmek. Önce 2.5 Üst ve KG için sabit Poisson'a karşı CI'ya bakılmalı.

**Sonuç (19 Ekim 2026):** İç içe sınandı (seçim her sezonda yalnızca önceki sezonlarla); ızgara `dc_weights=[0.0]`'a daraltıldı ve üretim yeniden eğitildi. İç katlar her sezonda w=0'ı seçti.

| Ölçüm | Önce (Ç1 sonrası) | Sonra | Fark (CI) |
|---|---|---|---|
| Skor NLL | 3.0003 | **2.9786** | **−0.0217 [−0.0328, −0.0111]** |
| 2.5 Üst LL | 0.6802 | 0.6774 | −0.0028 [−0.0078, +0.0023] |
| KG LL | 0.6829 | 0.6804 | −0.0025 [−0.0064, +0.0011] |
| 2.5 Üst Δ prior | −0.0046 | −0.0074 | — |
| 2.5 Üst − sabit Poisson | −0.0023 [−0.0094, +0.0047] | −0.0051 [−0.0119, +0.0019] | hâlâ anlamlı değil |
| KG − sabit Poisson | +0.0012 [−0.0053, +0.0075] | −0.0013 [−0.0071, +0.0042] | hâlâ anlamlı değil |
| 2.5 Üst − piyasa | +0.0114 [+0.0031, +0.0195] | +0.0086 [+0.0011, +0.0162] | piyasa hâlâ anlamlı iyi |
| KG − piyasa | +0.0075 [+0.0014, +0.0137] | +0.0050 [−0.0005, +0.0106] | artık anlamlı değil |
| Güvenilirlik ECE | 0.0494 | 0.0507 | biraz kötü |

- **Üretim ayarı:** full, α=3, dc_weight=0.0 (önceden full, α=3, w=0.25).
- **KG kapısı:** Ortalama fark negatife döndüğü için `btts_gate` eski kuralla `passed: True` olacaktı ve "KG Var/Yok" etiketini sessizce geri getirecekti. Fark CI'ın içinde olduğundan kapıya anlamlılık şartı eklendi (`ci_high < 0`); KG hâlâ `btts_informative=false`.
- **DC tamamen kaldırılmadı:** `dc_weight=0` iken DC yalnızca ortak `rho`'ya katkı veriyor (`rho = 0.5·(DC + feature)`). DC'yi ve `rho` ortaklığını da kaldırmak ayrı bir iç içe test gerektirir; açık.
- **Kalan:** Ham 2.5 Üst kazancı sabit Poisson'a karşı hâlâ gürültüden ayırt edilemiyor (P7a).

---

## 3. Çözüm Yöntemi

### ✅ ÇÖZÜLDÜ — Ç1 — Seçim ölçütünü skor matrisi NLL'sine çevir, α ızgarasını genişlet (P1 + P2)

**Değişiklik** (`src/models/train_goals.py`):

1. `BLEND_GRID["feature_alphas"]` → `[0.1, 0.3, 1.0, 3.0, 10.0, 30.0]`.
2. `select_blend_config`, 2.5 Üst ikili LL yerine **gerçekleşen skor hücresinin negatif log olasılığını** biriktirsin:

   ```python
   -log M[i, min(home_score, 12), min(away_score, 12)]
   ```
3. Kaybı en düşük olan ayar seçilsin. Ya 1-SE kuralı kaldırılsın ya da beraberlikte güçlü L2 yerine daha az parametreli seti tercih etsin.
4. `evaluate_goal_models` aynı fonksiyonu kullandığı için iç içe değerlendirme otomatik olarak güncellenir. Sıra: `evaluate_goal_models` → `train_goals`.

**İç içe test sonucu** (seçim her sezonda yalnızca eğitim sezonlarıyla yapıldı):

| Sezon | Üretim seçimi | Yeni seçim |
|---|---|---|
| 2023/24 | compact, α=30, w=0.5 | compact, α=10, w=0.5 |
| 2024/25 | full, α=30, w=0.5 | full, α=3, w=0.25 |
| 2025/26 | full, α=10, w=0.25 | full, α=3, w=0.25 |

| Ölçüm | Üretim | Yeni | Δ (CI) |
|---|---|---|---|
| Skor NLL | 3.0152 | 3.0003 | **−0.0149 [−0.0210, −0.0087]** ✅ |
| 2.5 Üst LL | 0.6803 | 0.6802 | −0.0001 [−0.0026, +0.0024] |
| KG LL | 0.6823 | 0.6829 | +0.0006 [−0.0014, +0.0026] |
| 1.5 Üst LL | 0.4742 | 0.4747 | +0.0005 [−0.0013, +0.0024] |
| 3.5 Üst LL | 0.6582 | 0.6573 | −0.0010 [−0.0034, +0.0017] |

**Beklenen etki:**
- İyileşenler: doğru skor, takım baremleri, handikap ve API'deki beklenen goller.
- Değişmeyenler: 2.5 Üst ve KG. Bu, P6'daki teşhisi doğruluyor.

**Not:** API'de matris lojistik 1X2'ye hizalandığı için gol farkındaki iyileşmenin bir kısmı 1X2 tarafında zaten karşılanıyor. Kazanç asıl olarak bölge içi skor dağılımına ve takım gollerine yansır.

### ✅ ÇÖZÜLDÜ — Ç2 — Kapıyı dürüstleştir (P4)

`evaluate_goal_models.py` içinde:

1. **Yeni kıyas noktaları:** Kapıya sabit Poisson (`null`) ile, oranı olan maçlarda piyasa kıyasını ekle. Piyasa kıyası karar vermek için değil, raporlamak için.
2. **2.5 Üst kuralı:** `passed` için Δ'nın prior'a değil, sabit Poisson'a göre negatif olmasını şart koş. `ci_excludes_zero` için eşik ya zorunlu olsun ya da açıkça "uyarı" olarak işaretlensin.
3. **KG için ayrı kapı:** Sabit Poisson'u geçemeyen bir pazar API'de "model tahmini" olarak değil, "lig ortalaması" olarak işaretlensin.

### ✅ ÇÖZÜLDÜ — Ç3 — KG ve 2.5 Üst sunumu (P5)

- `server.py` / frontend: "KG Var/Yok" etiketini kaldır veya yanına "düşük ayırt edicilik" notu ekle. Olasılık yüzdesi kalabilir.
- Paper-trading (`docs/reports/paper_trading_protocol_2026_27.md`): 2.5 Üst ve KG için bahis sinyali üretilmesin. Model piyasadan anlamlı derecede kötü.

### ❌ DENENDİ, REDDEDİLDİ — Ç4 — Toplam gol bilgisi: kadro tabanlı özellikler (P6, hipotez, test edildi)

Piyasanın bizden fazla bildiği şey büyük ihtimalle **ilk 11 ve eksik oyuncular**. Elimizdeki veri: `player_match_logs.json`, dizilişler (`read_starting_xis`), `shots_events_*`.

**Aday özellikler:**
- **Kadro xG oranı:** İlk 11'in son N maçtaki oyuncu başı xG ve şut katkılarının toplamı, takımın tam kadro ortalamasına oranla. Hem hücum hem savunma yönünde hesaplanır.
- **Eksik oyuncu payı:** Kilit hücum oyuncusu yokken takımın xG'si ne kadar düşüyor?

**Kurallar:**
- Bütün oyuncu metrikleri `shift(1)` ile yalnızca geçmiş maçlardan hesaplanmalı.
- Dizilişler maçtan ~1 saat önce açıklanıyor. Bu yüzden iki tahmin modu gerekir:
  - **Kadro öncesi:** Mevcut model.
  - **Kadro sonrası:** Yeni özelliklerle.

**Kabul ölçütü:** Seçenek, iç içe ızgaraya eklenir ve Ç1'deki prosedürle sınanır. Dış sezonlarda 2.5 Üst ve KG LL'si sabit Poisson'a karşı anlamlı biçimde iyileşmiyorsa kod kaldırılır ve "Reddedilen Deneyler" tablosuna işlenir.

**Sonuç (19 Ekim 2026):** Hipotez, kabul ölçütüne göre reddedildi. İlk 11 (`teamLists`) ve oyuncu şut hacmi (`shots_events` + `player_match_logs`) ile iki varyant, Ç1 prosedürüyle (seçim her sezonda yalnızca önceki sezonlarla) 3 dış sezonda sınandı. Oyuncu hızları yalnızca maçtan önceki satırlardan (`cumsum` − mevcut maç) ve takım tabanı `shift(1)` ile hesaplandı; veri sızıntısı yok.

| Ölçüm | Ç1 sonrası | + kadro özellikleri | Fark (CI) |
|---|---|---|---|
| Varyant 1 (olağan XI'dan sapma): skor NLL | 3.0003 | 2.9999 | −0.0004 [−0.0013, +0.0005] |
| Varyant 2 (+ mutlak güç, kilit şutör eksikliği): skor NLL | 3.0003 | **2.9970** | **−0.0033 [−0.0051, −0.0016]** |
| Varyant 2: 2.5 Üst LL | 0.6802 | 0.6797 | −0.0005 [−0.0015, +0.0004] |
| Varyant 2: KG LL | 0.6829 | 0.6829 | 0.0000 [−0.0006, +0.0005] |
| Varyant 2, sabit Poisson'a karşı 2.5 Üst | — | — | −0.0028 [−0.0101, +0.0044] |
| Varyant 2, sabit Poisson'a karşı KG | — | — | +0.0011 [−0.0055, +0.0077] |

- **Karar:** Kabul ölçütü 2.5 Üst ve KG'de sabit Poisson'a karşı anlamlı iyileşme istiyordu; ikisinde de CI sıfırı içeriyor. Kod repoya alınmadı (denemeler geçici dizinde yapıldı), deney `goals_model.md` "Reddedilen Deneyler" tablosuna işlendi.
- **Tek gerçek bulgu:** Varyant 2 skor NLL'ini 0.0033 düşürdü ve CI sıfırı dışlıyor. Ama bu iki varyant denemesi sonrası alınmış bir sonuç (çoklu deneme), etkisi küçük ve toplam gol bilgisini değil skor dağılımını iyileştiriyor. İki tahmin modu (kadro öncesi/sonrası) ve ETL bakımı maliyetini haklı çıkarmıyor.
- **Sınırlar:** Oyuncu xG'si yok, şut hacmi vekil olarak kullanıldı; ilk 11'in maçtan önce yayımlanma zamanı arşivde doğrulanmadı; savunma yönü (kadro bazlı) denenmedi. Piyasanın toplam gol bilgisinin kaynağı hâlâ bilinmiyor, P6 açık.

### ❌ DENENDİ, REDDEDİLDİ — Ç5 — Dixon-Coles cezasını ayarla (P3, hipotez, test edildi)

- `DixonColesModel.ridge` değerini {1, 3, 10, 30} arasında, Ç1'deki skor NLL ölçütüyle iç içe seç.
- İyi ayarlanmış bir DC, blend'in şu anki dolaylı küçültme işlevini doğrudan üstlenebilir ve mimariyi sadeleştirebilir.

**Sonuç (19 Ekim 2026):** Ridge ∈ {1, 3, 10, 30} iç içe ızgaraya eklendi ve sınandı. Ayar seçimi 3 dış sezonda 1, 3 ve 1'i seçti (yani yüksek ridge seçilmedi).

| Ölçüm | Ç1 sonrası blend | Blend + ridge araması |
|---|---|---|
| Skor NLL | 3.0003 | 3.0005 |

Doğrudan hipotez testi (tek başına DC, dış sezonlar):

| DC ridge | Skor NLL | 2.5 Üst LL |
|---|---|---|
| 1 | 3.0469 | 0.6879 |
| 3 | 3.0418 | 0.6863 |
| 10 | 3.0329 | 0.6829 |
| 30 | 3.0314 | 0.6796 |
| *Blend (Ç1)* | *3.0003* | *0.6802* |

İyi ayarlanmış DC kendi başına iyileşiyor ama blend'in 0.031 NLL gerisinde kalıyor; blend'in yerini tutmuyor, mimari sadeleşmedi. Kod geri alındı; deney `docs/reports/models/goals_model.md` "Reddedilen Deneyler" tablosuna işlendi. P3 açık.

---

## 4. Uygulama Sırası ve Kontrol Listesi

| # | İş | Efor | Etkilenen dosyalar |
|---|---|---|---|
| 1 | ✅ ÇÖZÜLDÜ — Ç1: skor NLL ile seçim + α ızgarası | Küçük | `train_goals.py`, `tests/test_goal_selection.py` |
| 2 | ✅ ÇÖZÜLDÜ — Ç2: sabit Poisson ve piyasa kıyası, KG kapısı | Küçük–Orta | `evaluate_goal_models.py` |
| 3 | ✅ ÇÖZÜLDÜ — Pipeline: `evaluate_goal_models` → `train_goals` | — | `goal_model_outer_eval.json`, `goals_models_v1.joblib` |
| 4 | ✅ ÇÖZÜLDÜ — Ç3: KG etiketi ve paper-trading kuralı | Çok küçük | `server.py`, frontend, protokol belgesi |
| 5 | ❌ DENENDİ, REDDEDİLDİ — Ç5: DC ridge araması | Küçük | `dixon_coles.py`, `train_goals.py` |
| 6 | ❌ DENENDİ, REDDEDİLDİ — Ç4: kadro tabanlı özellikler | Büyük | ETL, özellik üretimi, `train_goals.py` |

Her model değişikliğinden sonra belgeler şu sırayla güncellenir (sayılar `joblib.load(...)["metrics"]` / artifact'tan alınır):

1. `docs/reports/models/goals_model.md`
2. Ana rapordaki özet karne
3. `README.md` model tablosu
4. `PROJECT_STATUS.md`
5. `AI_CONTEXT.md`

---

## 5. Varsayımlar ve Sınırlar

- **Oran zamanlaması:** Bet365 `last_seen` oranlarının maç öncesi kapanış oranları olduğu varsayıldı. Marj ~%5 ile normal görünüyor, ancak zaman damgaları doğrulanmadı.
- **Kapsam dışı:** Haftalık yeniden eğitim modu (`evaluate_in_season_refit`) bu analizde yeniden değerlendirilmedi. Tüm rakamlar donuk (sezon başı) modelden.
- **Seçim temizliği:** Ç1'deki karşılaştırma aynı üç dış sezonda yapılan ikinci prosedürdür. Ancak yeni ayar dış sezonlara bakılarak seçilmedi; seçim tamamen iç katlarda yapıldı.
- **Ölçüm kaynağı:** "Gol farkı / toplam gol korelasyonu" ve "skor NLL" dış sezon tahminlerinden ölçüldü, üretim artifact'ından değil.
