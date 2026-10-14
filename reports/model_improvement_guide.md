# Model İyileştirme Kılavuzu (Over 2.5 Yeniden Yazımı + Tüm Öneriler)

Bu belge, `reports/` altındaki raporların bulgularına göre modeli nasıl geliştireceğini **dosya dosya, fonksiyon fonksiyon** anlatır. Kod blokları gerçek dosya yapına göre yazıldı (`src/models/train_match_outcome.py`, `src/models/dixon_coles.py`, `src/models/model_utils.py`, `src/features/build_features.py`, `src/api/server.py`).

> [!IMPORTANT]
> Bu kılavuz ilk yazıldığında kod çalıştırılmadan hazırlanmıştı; örnekler öneri niteliğindeydi. Gerçek uygulama durumu ve henüz yapılmayan doğrulamalar bu belgenin sonundaki **Yürütme Kaydı** bölümünde tutulur. "DOĞRULA" işaretli veri/kod varsayımlarını uygulamadan önce kontrol et.

---

## 0. Önce Büyük Resim

### 0.1 Neyi neden yapıyoruz

| # | İş | Neden | Beklenen kazanç | Risk |
|---|---|---|---|---|
| F1 | Değerlendirme altyapısı (bootstrap, güvenilirlik tablosu, kilitli sezon) | Diğer her şeyin "iyileşti mi?" sorusunu cevaplamak için gerekli | Yok, ama karar kalitesi artar | Düşük |
| F2 | Skor-matrisi tabanlı gol modeli (Over/Under, BTTS, 1X2 tek kaynaktan) | Over 2.5 şu an baseline'dan kötü; beraberlik yapısal olarak skor matrisinin köşegeninden gelir | Orta | Orta |
| F3 | Over 2.5 ürün tarafı (API + arayüz + güven bayrağı) | Baseline'ı geçmeyen sayıyı kullanıcıya olduğu gibi göstermemek | Doğruluk/dürüstlük | Düşük |
| F4 | 1X2 ensemble (lojistik regresyon + Dixon–Coles) | Farklı hata kaynaklarını birleştirme olasılığı; dış sezon ölçümü tamamlandı, karar kapısı geçilmedi | Küçük–orta | Düşük |
| F5 | Beraberlik özellikleri | Draw AUC 0.538, neredeyse rastgele | Belirsiz, küçük olabilir | Orta (sızıntı riski) |
| F6 | Sürüklenme (drift) yönetimi | Beraberlik oranı %22 → %31 kaydı | Orta | Düşük |
| F7 | xG Modeli / Proksisi | Kaldırıldı: Güvenilir olmayan proxy (%42 doluluk) model, boru hattı ve arayüzden tamamen temizlendi | Dürüstlük / Veri Bütünlüğü | Tamamlandı |
| F8 | Regresyon hedefleri için "beceri kapısı" + Poisson adayları | Corners/cards/saves ridge'i ortalamadan iyi değil | Dürüstlük + küçük | Düşük |
| F9 | Saves etiket kurtarma | %13 eksik, seçilim yanlılığı | Küçük | Düşük |
| F10 | İleriye dönük kayıt + testler + dokümantasyon | Gerçek doğrulama ve bakım | Yüksek (uzun vadede) | Düşük |

### 0.2 Dürüst beklenti yönetimi

Son `model_benchmarks.md` çıktısındaki kilitli sezon hariç 304 maçlık holdout'ta 1X2 log-loss **1.024** (prior baseline **1.092**); Over 2.5 log-loss **0.689** (prior baseline **0.688**). Futbol 1X2 tahmininde, bahis piyasası bile kabaca 0.97–1.00 log-loss civarındadır. Yani **elindeki verilerle 1.00'in altına inmek gerçekçi bir hedef değil**. Gerçekçi hedef:

- 1X2: log-loss'ta **0.005–0.020** ek iyileşme (1.024 → ~1.01). Bunu 304 maçlık holdout'ta görmek zor; bu yüzden F1 şart.
- Over 2.5: baseline'ı **tutarlı biçimde** geçmek (log-loss ≈ 0.685–0.690 civarı). Bundan fazlasını bekleme. Toplam gol çok gürültülü.
- Beraberlik AUC: 0.54 → 0.56–0.58 olursa başarılı.

Her faz bir **karar kapısı** içerir: kriteri geçmezse o değişikliği üretime alma, sonucu rapora "denendi, işe yaramadı" olarak yaz. Bu da değerli bir sonuçtur.

### 0.3 Çalışma düzeni (her faz için aynı)

1. Yeni dal aç: `git checkout -b feat/<faz-adı>`.
2. Başlamadan **referans çıktıyı sakla**:
   ```bash
   cp reports/model_benchmarks.md reports/_baseline_before_<faz>.md
   cp models/production/outcome_models_v1.joblib /tmp/outcome_models_v1.before.joblib
   ```
   (`_baseline_*` dosyalarını commit etme; `.gitignore`'a ekleyebilirsin.)
3. Kodu yaz, testleri yaz.
4. `python3 -m pytest tests -q` (veya mevcut stilde: `python3 tests/test_data_leakage.py`).
5. `python3 run_full_pipeline.py` — rapor yeniden üretilir.
6. Kabul kriterini kontrol et. Geçtiyse commit, geçmediyse dalı bırak.
7. `./start.sh` ile çalışan API model dosyalarını **açılışta** yüklüyor (`server.py` satır 73). Model artefaktı değişince API'yi **yeniden başlat**.

> [!WARNING]
> Pipeline tüm `reports/*.md` dosyalarından yalnızca birkaçını yeniden üretir (benchmark, data_quality, team_*). `1x2_model_audit.md` ve `model_diagnostic_followup.md` **elle yazılmış**; bunları kendin güncelle.

### 0.4 Önerilen sıra

Önerilen uygulama sırası: `F1 → F2 → F3 → F4 → F6 → F5 → F8 → F9 → F10`. F7, xG proxy'sini kaldırma kararıyla mevcut çalışma ağacında tamamlandı.

F1–F9 uygulandı. F4 ensemble, F6 zaman ağırlıklı kalibrasyon ve F5 beraberlik özellikleri karar kapılarını geçmedi; üretim 1X2 artefaktı bu nedenle korundu. F5'in dokuz özelliği ortak eğitim/canlı tahmin koduna eklendi, ancak üretim modelinde açılmadı. F8 dört katlı beceri kapısını uyguluyor; F9 saves etiketlerini 1.371'den 1.580 kullanılabilir maça çıkardı. F10 tahmin günlüğü, rapor bağlantıları ve 14 Ekim snapshot'ı tamamlandı. Test paketi çalıştırılmadı; ileriye dönük skor, maç sonuçları geldikçe oluşacak.

---

## FAZ 1 — Değerlendirme Altyapısı

Bunu en başta yap. Çünkü 316 maçlık holdout'ta log-loss farkının standart hatası ≈ 0.01–0.02. Raporlardaki politika farkları (0.001–0.005) bunun içinde kayboluyor.

### 1.1 Yeni dosya: `src/models/eval_utils.py`

```python
"""Shared evaluation helpers: per-match losses, paired bootstrap, reliability tables."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def per_match_log_loss(probabilities: np.ndarray, y: np.ndarray) -> np.ndarray:
    """-log p(actual class) for every match. `probabilities` is (n, k), y is int labels 0..k-1."""
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-12, 1.0)
    y = np.asarray(y, dtype=int)
    return -np.log(p[np.arange(len(y)), y])


def paired_bootstrap_delta(
    loss_a: np.ndarray,
    loss_b: np.ndarray,
    n_boot: int = 5000,
    seed: int = 42,
) -> Dict[str, float]:
    """Bootstrap the mean per-match loss difference d = loss_a - loss_b.

    Negative mean => model A is better. `p_a_better` is the share of bootstrap
    resamples where A has lower mean loss. A 95% interval that excludes 0 is
    the minimum bar for calling an improvement real.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    if len(d) == 0:
        raise ValueError("Empty loss arrays")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    return {
        "mean_delta": float(d.mean()),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "p_a_better": float((means < 0).mean()),
        "n": int(len(d)),
    }


def reliability_table(p_event: np.ndarray, actual: np.ndarray, bins: int = 10) -> List[Dict[str, Any]]:
    """Quantile-binned reliability table for a binary event (e.g. Over 2.5, draw)."""
    p = np.asarray(p_event, dtype=float)
    a = np.asarray(actual, dtype=float)
    frame = pd.DataFrame({"p": p, "a": a})
    frame["bin"] = pd.qcut(frame["p"], q=bins, duplicates="drop")
    rows = []
    for interval, g in frame.groupby("bin", observed=True):
        rows.append({
            "bin": str(interval),
            "n": int(len(g)),
            "mean_predicted": round(float(g["p"].mean()), 4),
            "observed_rate": round(float(g["a"].mean()), 4),
        })
    return rows


def expected_calibration_error(p_event: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    rows = reliability_table(p_event, actual, bins)
    total = sum(r["n"] for r in rows)
    return float(sum(r["n"] * abs(r["mean_predicted"] - r["observed_rate"]) for r in rows) / total)
```

### 1.2 Kilitli sezon kuralı

Hedef: Bu fazda **2026/27 sezonu 1X2 ve Over 2.5 sınıflandırıcılarının model seçimi, kalibrasyonu, dış-sezon karşılaştırması veya kalite ölçümünde kullanılmasın**; sezon tamamlanınca kilit kaldırılarak bir kez puanlansın. Sezon içindeki oynanmış maçlar nihai üretim sınıflandırıcılarının eğitimine girebilir. Korner/kart/kurtarış gibi regresyon ailelerinin holdout protokolü bu fazda değiştirilmez; bu sonuçlar en yeni kısmi sezonu içermeye devam eder.

`src/models/train_match_outcome.py` modül seviyesinde, `EXCLUDED_1X2_TRAINING_SEASONS` tanımının yanına ekle:

```python
LOCKED_SEASONS = {"2026_27"}   # dosyanın üstüne, EXCLUDED_1X2_TRAINING_SEASONS'ın altına koy
```

Fonksiyonda hedefleri oluşturup maçları sıraladıktan sonra üretim verisiyle değerlendirme verisini ayır. Değerlendirme, dış-sezon karşılaştırmaları ve kalibrasyon yalnızca `df` üzerinden yürür. `season` sütunu yoksa kilit uygulanamayacağından sessizce devam etme; açık hata ver.

```python
# fonksiyonun içinde, hedef sütunlarını oluşturup sort_values yaptıktan sonra:
df_all = df.copy()                                   # üretim fit'i bunu kullanır
df = df[~df["season"].astype(str).isin(LOCKED_SEASONS)].reset_index(drop=True)  # değerlendirme bunu kullanır
```

Sonra:
- `split_idx`, `dev`, `hold`, `select_model`, `chronological_oof_predictions`, `evaluate_season_holdouts`, `evaluate_1x2_training_variants`, `evaluate_dixon_coles` çağrıları **`df`** (kilitli sezon hariç) ile çalışır.
- Üretim fit'i (`final_fit = df` olan iki yer) **`df_all`** kullanır:
  ```python
  final_fit = df_all
  if excluded_training_seasons:
      final_fit = df_all[~df_all["season"].astype(str).isin(excluded_training_seasons)]
  ```
- Üretim kalibratörünün ileriye dönük OOF tahminlerini **`df`** üzerinden üret; 1X2 için `EXCLUDED_1X2_TRAINING_SEASONS`'ı da bu kalibrasyon çerçevesinden çıkar. Böylece kilitli sezon son modelin eğitimine girebilir ama kalibrasyon örneği olamaz.
- `metrics["played_matches_total"] = int(len(df_all))`; ayrıca değerlendirmede kullanılan maç sayısını ve kilit nedeniyle dışarıda bırakılan oynanmış maç sayısını raporla.

> [!NOTE]
> Üretim modeli 2026/27 maçlarını eğitimde görebilir ama bu maçlar hiçbir kalite metriğine, model/özellik seçimine veya kalibratöre girmez. Gerçek sezon içi doğrulama, ileriye dönük tahmin günlüğüdür (Faz 10).
> Sezon bitince `LOCKED_SEASONS = set()` yapıp tek bir "final skor" çalıştırması al, sonucu rapora yaz, sonra kilidi bir sonraki sezona kaydır.

**DOĞRULA:** `season` sütununun değerleri `"2026_27"` biçiminde mi (raporlarda `2026_27` görünüyor)? `python3 -c "import pandas as pd; print(pd.read_parquet('data/processed/features_matches_all.parquet')['season'].unique())"`.

### 1.3 Mevcut raporlara bootstrap ve güvenilirlik ekleme

`train_match_outcome_models` içinde, `res = {...}` oluşturulduktan sonra, 1X2 ve o25 için kalibre edilmiş holdout olasılıklarıyla maç-başı kayıpları ve eşleştirilmiş bootstrap farkı hesapla. Over 2.5 ve beraberlik olayı için ayrıca güvenilirlik tablosu ve ECE ekle. Uygulama durumu için bu dosyanın sonundaki Yürütme Kaydı'na bak.

```python
from src.models.eval_utils import (
    expected_calibration_error, paired_bootstrap_delta, per_match_log_loss, reliability_table,
)

# fonksiyonun içinde, res tanımından sonra:
model_loss = per_match_log_loss(probs, y_hold.to_numpy(dtype=int))
prior_loss = per_match_log_loss(prior_probs, y_hold.to_numpy(dtype=int))
res["bootstrap_vs_prior"] = paired_bootstrap_delta(model_loss, prior_loss)
if kind == "o25":
    actual_event = y_hold.to_numpy(dtype=int)
    res["reliability"] = reliability_table(probs[:, 1], actual_event)
    res["expected_calibration_error"] = expected_calibration_error(probs[:, 1], actual_event)
else:
    actual_draw = (y_hold.to_numpy(dtype=int) == 1).astype(int)
    res["reliability_draw"] = reliability_table(probs[:, 1], actual_draw)
    res["draw_expected_calibration_error"] = expected_calibration_error(probs[:, 1], actual_draw)
```

`run_full_pipeline.py` içindeki `generate_benchmark_report`'a sınıflandırma tablosundan sonra bootstrap özeti ve iki güvenilirlik tablosu ekle. `Mean Δ` negatifse model daha iyi; 95% aralık sıfırı içermiyorsa iyileşme için daha güçlü kanıt vardır. ECE'yi de özetle.

```python
lines.extend(["", "## Bootstrap: model vs class-prior (per-match log loss, 95% CI)", "",
              "| Target | Mean Δ | CI low | CI high | P(model better) | n | ECE |", "|---|---:|---:|---:|---:|---:|---:|"])
for key, label in (("model_1x2", "1X2 result"), ("model_over_2_5", "Over 2.5 goals")):
    b = outcome_res[key]["bootstrap_vs_prior"]
    ece_key = "draw_expected_calibration_error" if key == "model_1x2" else "expected_calibration_error"
    lines.append(f"| {label} | {b['mean_delta']:.4f} | {b['ci_low']:.4f} | {b['ci_high']:.4f} | {b['p_a_better']:.2f} | {b['n']} | {outcome_res[key][ece_key]:.4f} |")
```

(Aynı kalıpla güvenilirlik tablolarını da yaz: `outcome_res["model_over_2_5"]["reliability"]` satırlarını markdown tabloya çevir.)

### 1.4 Kabul kriteri
- Rapor yeni bölümleri içeriyor; `Mean Δ` negatif ve CI sıfırı içermiyorsa "model baseline'ı gerçekten geçiyor" diyebilirsin. Over 2.5 için büyük ihtimalle CI sıfırı içerecek; bu beklenen sonuç.
- `df` ve `df_all` ayrımı sonrası 1X2 sayıları **değişmeli**: holdout 316 yerine daha az maç içerir (60 maç kilitli). Bu normal. Eski rapor sayılarıyla birebir karşılaştırma yapma; yeni çıktıyı yeni baseline say.

---

## FAZ 2 — Skor Matrisi Tabanlı Gol Modeli

Fikir: tek bir model **λ_ev ve λ_dep** (beklenen goller) üretir. Bunlardan 0–12 gol için 13×13 skor olasılık matrisi çıkar. Sonra:

- 1X2 = matrisin alt üçgeni / köşegeni / üst üçgeni
- Over/Under X.5 = toplam gol > X olan hücrelerin toplamı
- BTTS = her iki takım ≥ 1 gol olan hücreler

Hepsi **aynı** matristen geldiği için birbiriyle tutarlıdır (ör. beraberlik yüksekken toplam gol düşük olur).

### 2.1 `src/models/dixon_coles.py` — ortak matris fonksiyonları

Dosyanın en üstündeki `import`'lara dokunma. `DixonColesModel` sınıfından **önce** şu fonksiyonları ekle:

```python
def matrix_from_lambdas(lam_h, lam_a, rho: float, max_goals: int = 12) -> np.ndarray:
    """(n, G+1, G+1) score matrices. Axis 1 = home goals, axis 2 = away goals."""
    lam_h = np.asarray(lam_h, dtype=float)
    lam_a = np.asarray(lam_a, dtype=float)
    goals = np.arange(max_goals + 1)
    home_pmf = poisson.pmf(goals[None, :], lam_h[:, None])
    away_pmf = poisson.pmf(goals[None, :], lam_a[:, None])
    m = home_pmf[:, :, None] * away_pmf[:, None, :]
    m[:, 0, 0] *= 1.0 - lam_h * lam_a * rho
    m[:, 0, 1] *= 1.0 + lam_h * rho
    m[:, 1, 0] *= 1.0 + lam_a * rho
    m[:, 1, 1] *= 1.0 - rho
    m = np.clip(m, 0.0, None)
    total = m.sum(axis=(1, 2), keepdims=True)
    bad = (total <= 0).reshape(-1)
    m = m / np.where(total > 0, total, 1.0)
    if bad.any():
        m[bad] = 1.0 / (m.shape[1] * m.shape[2])
    return m


def outcome_probs(m: np.ndarray) -> np.ndarray:
    """Home / draw / away probabilities from score matrices."""
    g = m.shape[1]
    i, j = np.indices((g, g))
    probs = np.stack([
        (m * (i > j)).sum(axis=(1, 2)),
        (m * (i == j)).sum(axis=(1, 2)),
        (m * (i < j)).sum(axis=(1, 2)),
    ], axis=1)
    probs = np.clip(probs, 1e-12, 1.0)
    return probs / probs.sum(axis=1, keepdims=True)


def over_prob(m: np.ndarray, line: float) -> np.ndarray:
    """P(total goals > line). line is a half-goal line such as 1.5, 2.5, 3.5."""
    g = m.shape[1]
    i, j = np.indices((g, g))
    return (m * ((i + j) > line)).sum(axis=(1, 2))


def btts_prob(m: np.ndarray) -> np.ndarray:
    g = m.shape[1]
    i, j = np.indices((g, g))
    return (m * ((i >= 1) & (j >= 1))).sum(axis=(1, 2))
```

### 2.2 `DixonColesModel`: λ, matris ve zaman ağırlığı

**(a) Zaman ağırlığı (`fit`).** Eski maçlar daha az ağırlık alsın (Dixon–Coles'in orijinal fikri). `__init__` imzasını değiştir:

```python
def __init__(self, ridge: float = 1.0, max_goals: int = 12, half_life_days: float | None = None):
    self.ridge = float(ridge)
    self.max_goals = int(max_goals)
    self.half_life_days = half_life_days
    ...  # geri kalanı aynı
```

`fit` içinde, `data` hazırlandıktan ve `if data.empty` kontrolünden sonra, `self.teams_ = ...` satırından önce ağırlık vektörünü hesapla:

```python
weights = np.ones(len(data), dtype=float)
if self.half_life_days and "match_date" in data.columns:
    dates = pd.to_datetime(data["match_date"])
    age_days = (dates.max() - dates).dt.total_seconds().to_numpy() / 86400.0
    weights = 0.5 ** (age_days / float(self.half_life_days))
    weights = weights / weights.mean()          # ortalama 1: ridge cezası ölçeğini bozmaz
```

`objective` içinde iki satırı değiştir:

```python
# ESKİ
return float(-np.log(tau).sum() - log_likelihood.sum() + penalty)
# YENİ
return float(-(weights * np.log(tau)).sum() - (weights * log_likelihood).sum() + penalty)
```

Aynı fonksiyondaki `if np.any(tau <= 1e-8):` korumasını **değiştirme**.

> [!NOTE]
> `weights` bir kapanış (closure) değişkeni olarak `objective`'e girer. `objective`'i `weights` tanımından **sonra** tanımla (mevcut sıra zaten böyle olur: `weights` en üste gelirse yeterli).

**(b) λ ve matris metotları.** `predict_proba`'yı bu üç metotla değiştir (eski gövdeyi sil):

```python
def lambdas(self, matches: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    home_id = matches["home_id"].astype(int).to_numpy()
    away_id = matches["away_id"].astype(int).to_numpy()
    attack_h = np.asarray([self.attack_.get(t, 0.0) for t in home_id])
    attack_a = np.asarray([self.attack_.get(t, 0.0) for t in away_id])
    defence_h = np.asarray([self.defence_.get(t, 0.0) for t in home_id])
    defence_a = np.asarray([self.defence_.get(t, 0.0) for t in away_id])
    lam_h = np.exp(np.clip(self.intercept_ + self.home_advantage_ + attack_h - defence_a, -4, 4))
    lam_a = np.exp(np.clip(self.intercept_ + attack_a - defence_h, -4, 4))
    return lam_h, lam_a

def predict_matrices(self, matches: pd.DataFrame) -> np.ndarray:
    lam_h, lam_a = self.lambdas(matches)
    return matrix_from_lambdas(lam_h, lam_a, self.rho_, self.max_goals)

def predict_proba(self, matches: pd.DataFrame) -> np.ndarray:
    return outcome_probs(self.predict_matrices(matches))
```

### 2.3 Regresyon testi (önce bunu yaz, sonra refaktör sonucunu doğrula)

`tests/test_goal_matrix.py`:

```python
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.dixon_coles import (
    DixonColesModel, btts_prob, matrix_from_lambdas, outcome_probs, over_prob,
)


def test_matrix_sums_to_one_and_derived_probs_consistent():
    m = matrix_from_lambdas([1.4, 0.9], [1.1, 1.3], rho=-0.05)
    assert np.allclose(m.sum(axis=(1, 2)), 1.0)
    p = outcome_probs(m)
    assert np.allclose(p.sum(axis=1), 1.0)
    assert (over_prob(m, 2.5) + over_prob(m, 1.5) * 0 >= 0).all()
    assert (over_prob(m, 1.5) >= over_prob(m, 2.5)).all()        # daha düşük çizgi daha olası
    assert (over_prob(m, 2.5) >= over_prob(m, 3.5)).all()
    assert ((btts_prob(m) >= 0) & (btts_prob(m) <= 1)).all()


def test_symmetry_equal_lambdas_equal_home_and_away():
    m = matrix_from_lambdas([1.2], [1.2], rho=0.0)
    p = outcome_probs(m)[0]
    assert abs(p[0] - p[2]) < 1e-9


def test_dixon_coles_predict_proba_unchanged_shape_and_sum():
    rng = np.random.default_rng(0)
    teams = list(range(1, 9))
    rows = []
    for k in range(200):
        h, a = rng.choice(teams, 2, replace=False)
        rows.append({"home_id": h, "away_id": a,
                     "home_score": rng.poisson(1.5), "away_score": rng.poisson(1.1),
                     "match_date": pd.Timestamp("2024-08-01") + pd.Timedelta(days=k)})
    df = pd.DataFrame(rows)
    model = DixonColesModel(half_life_days=365).fit(df)
    p = model.predict_proba(df.head(10))
    assert p.shape == (10, 3) and np.allclose(p.sum(axis=1), 1.0)
```

> [!IMPORTANT]
> Refaktörden önce **eski** `predict_proba` ile aynı veride çıktı al (`python3 -c ...`), refaktörden sonra aynı veriyle karşılaştır. `half_life_days=None` iken fark `1e-9` altında olmalı. Bu, refaktörün davranışı bozmadığının kanıtıdır.

### 2.4 Özellik-tabanlı gol modeli: `src/models/goals_model.py`

DC yalnızca takım kimliğine bakar (hücum/savunma katsayıları). Elo, form, dinlenme gibi mevcut özellikleri de kullanan ikinci bir λ modeli ekliyoruz.

```python
"""Feature-driven goal-rate models and score-matrix derived probabilities."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.models.dixon_coles import matrix_from_lambdas

RHO_GRID = np.linspace(-0.15, 0.15, 31)


class FeatureGoalModel:
    """Two Poisson regressions (home goals, away goals) + Dixon–Coles low-score rho."""

    def __init__(self, features: List[str], alpha: float = 30.0, max_goals: int = 12):
        self.features = list(features)
        self.alpha = float(alpha)
        self.max_goals = int(max_goals)
        self.rho_ = 0.0

    def _pipe(self):
        return make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            PoissonRegressor(alpha=self.alpha, max_iter=3000),
        )

    def fit(self, df: pd.DataFrame, sample_weight: np.ndarray | None = None) -> "FeatureGoalModel":
        X = df[self.features]
        kwargs = {} if sample_weight is None else {"poissonregressor__sample_weight": sample_weight}
        self.home_ = self._pipe().fit(X, df["home_score"].astype(float), **kwargs)
        self.away_ = self._pipe().fit(X, df["away_score"].astype(float), **kwargs)
        self.rho_ = self._fit_rho(df)
        return self

    def lambdas(self, df: pd.DataFrame):
        X = df[self.features]
        lam_h = np.clip(self.home_.predict(X), 0.05, 6.0)
        lam_a = np.clip(self.away_.predict(X), 0.05, 6.0)
        return lam_h, lam_a

    def _fit_rho(self, df: pd.DataFrame) -> float:
        lam_h, lam_a = self.lambdas(df)
        hg = df["home_score"].to_numpy(dtype=int)
        ag = df["away_score"].to_numpy(dtype=int)
        best_rho, best_ll = 0.0, -np.inf
        for rho in RHO_GRID:
            tau = np.ones(len(df))
            tau[(hg == 0) & (ag == 0)] = 1 - lam_h[(hg == 0) & (ag == 0)] * lam_a[(hg == 0) & (ag == 0)] * rho
            tau[(hg == 0) & (ag == 1)] = 1 + lam_h[(hg == 0) & (ag == 1)] * rho
            tau[(hg == 1) & (ag == 0)] = 1 + lam_a[(hg == 1) & (ag == 0)] * rho
            tau[(hg == 1) & (ag == 1)] = 1 - rho
            if np.any(tau <= 1e-6):
                continue
            ll = float(np.log(tau).sum())
            if ll > best_ll:
                best_rho, best_ll = float(rho), ll
        return best_rho

    def predict_matrices(self, df: pd.DataFrame) -> np.ndarray:
        lam_h, lam_a = self.lambdas(df)
        return matrix_from_lambdas(lam_h, lam_a, self.rho_, self.max_goals)


def blend_lambdas(lam_a, lam_b, weight_a: float):
    """Geometric blend of two lambda vectors (weight on model A)."""
    return np.exp(weight_a * np.log(lam_a) + (1 - weight_a) * np.log(lam_b))
```

Kullanılacak özellik listesi: 1X2 ile aynı çekirdek özellikler. `train_match_outcome.py`'dan import et:

```python
from src.models.train_match_outcome import feature_set
feats = feature_set("o25", list(df.columns))   # STRENGTH + DIFF + form + EXTRA_O25
```

`alpha` değerleri için `{3, 10, 30, 100, 300}` ızgarası dene (Poisson regresyonda L2 gücü; standartlaştırılmış özelliklerle 884–1264 satırda yüksek alpha daha güvenli).

### 2.5 Dış sezon değerlendirmesi: `src/models/evaluate_goal_models.py`

Amaç: **aynı protokolde** (her sezon yalnızca önceki sezonlarla eğit) şu adayları Over/Under çizgileri ve 1X2 için karşılaştırmak:

| Aday | Açıklama |
|---|---|
| `prior` | Eğitimdeki oran (baseline) |
| `logreg_o25` | Mevcut model (yalnızca Over 2.5) |
| `dc` | Dixon–Coles (`half_life_days=None`) |
| `dc_hl365` | Dixon–Coles, yarı ömür 365 gün |
| `dc_hl730` | Dixon–Coles, yarı ömür 730 gün |
| `feat_alpha{a}` | Özellik tabanlı Poisson, alpha=a |
| `blend_dc_feat` | λ'ların geometrik ortalaması (0.5/0.5) |

İskelet (yapıştırıp çalıştırılabilir olacak şekilde yazıldı; ayrıntılar senin verinle ince ayar ister):

```python
"""Outer-season comparison of goal-matrix models for O/U lines, BTTS and 1X2."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.models.dixon_coles import (
    DixonColesModel, btts_prob, matrix_from_lambdas, outcome_probs, over_prob,
)
from src.models.eval_utils import paired_bootstrap_delta, per_match_log_loss
from src.models.goals_model import FeatureGoalModel, blend_lambdas
from src.models.train_match_outcome import (
    LOCKED_SEASONS, N_CV_SPLITS, feature_set,
)

logger = logging.getLogger("evaluate_goal_models")

OU_LINES = (1.5, 2.5, 3.5)


def _binary_probs(p_event: np.ndarray) -> np.ndarray:
    p = np.clip(p_event, 1e-6, 1 - 1e-6)
    return np.column_stack([1 - p, p])


def _candidate_matrices(train: pd.DataFrame, test: pd.DataFrame, feats: List[str]) -> Dict[str, np.ndarray]:
    out: Dict[str, np.ndarray] = {}
    dc_variants = {"dc": None, "dc_hl365": 365.0, "dc_hl730": 730.0}
    dc_models = {name: DixonColesModel(half_life_days=hl).fit(train) for name, hl in dc_variants.items()}
    for name, model in dc_models.items():
        out[name] = model.predict_matrices(test)
    feat_models = {}
    for alpha in (10.0, 30.0, 100.0, 300.0):
        fm = FeatureGoalModel(feats, alpha=alpha).fit(train)
        feat_models[alpha] = fm
        out[f"feat_alpha{alpha:g}"] = fm.predict_matrices(test)
    # Blend: DC (hl365) lambdas x feature (alpha=100) lambdas
    lh_a, la_a = dc_models["dc_hl365"].lambdas(test)
    lh_b, la_b = feat_models[100.0].lambdas(test)
    rho = 0.5 * (dc_models["dc_hl365"].rho_ + feat_models[100.0].rho_)
    out["blend_dc_feat"] = matrix_from_lambdas(
        blend_lambdas(lh_a, lh_b, 0.5), blend_lambdas(la_a, la_b, 0.5), rho
    )
    return out


def evaluate_outer_seasons(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """`df` must be sorted by kickoff, played-only, locked seasons already removed."""
    feats = feature_set("o25", list(df.columns))
    seasons = list(pd.unique(df["season"].astype(str)))
    rows: List[Dict[str, Any]] = []
    for idx, season in enumerate(seasons):
        if idx == 0:
            continue
        test = df[df["season"].astype(str) == season]
        train = df[df["season"].astype(str).isin(seasons[:idx])]
        if len(train) < 300 or test.empty:
            continue
        mats = _candidate_matrices(train, test, feats)
        total_goals = (test["home_score"] + test["away_score"]).to_numpy()
        for line in OU_LINES:
            y = (total_goals > line).astype(int)
            prior_rate = float((train["home_score"] + train["away_score"] > line).mean())
            prior_loss = per_match_log_loss(_binary_probs(np.full(len(y), prior_rate)), y)
            rows.append({"season": season, "target": f"over_{line}", "model": "prior",
                         "log_loss": float(prior_loss.mean()), "n": int(len(y)),
                         "delta_vs_prior": 0.0, "ci_low": 0.0, "ci_high": 0.0})
            for name, m in mats.items():
                loss = per_match_log_loss(_binary_probs(over_prob(m, line)), y)
                boot = paired_bootstrap_delta(loss, prior_loss, n_boot=2000)
                rows.append({"season": season, "target": f"over_{line}", "model": name,
                             "log_loss": float(loss.mean()), "n": int(len(y)),
                             "delta_vs_prior": boot["mean_delta"],
                             "ci_low": boot["ci_low"], "ci_high": boot["ci_high"]})
        # BTTS
        y_btts = ((test["home_score"] >= 1) & (test["away_score"] >= 1)).astype(int).to_numpy()
        prior_btts = float(((train["home_score"] >= 1) & (train["away_score"] >= 1)).mean())
        prior_loss = per_match_log_loss(_binary_probs(np.full(len(y_btts), prior_btts)), y_btts)
        for name, m in mats.items():
            loss = per_match_log_loss(_binary_probs(btts_prob(m)), y_btts)
            boot = paired_bootstrap_delta(loss, prior_loss, n_boot=2000)
            rows.append({"season": season, "target": "btts", "model": name,
                         "log_loss": float(loss.mean()), "n": int(len(y_btts)),
                         "delta_vs_prior": boot["mean_delta"],
                         "ci_low": boot["ci_low"], "ci_high": boot["ci_high"]})
        # 1X2
        y1 = np.select([test["home_score"] > test["away_score"],
                        test["home_score"] == test["away_score"]], [0, 1], default=2)
        prior1 = np.tile(
            pd.Series(np.select([train["home_score"] > train["away_score"],
                                 train["home_score"] == train["away_score"]], [0, 1], default=2)
                      ).value_counts(normalize=True).reindex([0, 1, 2], fill_value=0).to_numpy(),
            (len(y1), 1))
        prior_loss = per_match_log_loss(prior1, y1)
        for name, m in mats.items():
            loss = per_match_log_loss(outcome_probs(m), y1)
            boot = paired_bootstrap_delta(loss, prior_loss, n_boot=2000)
            rows.append({"season": season, "target": "1x2", "model": name,
                         "log_loss": float(loss.mean()), "n": int(len(y1)),
                         "delta_vs_prior": boot["mean_delta"],
                         "ci_low": boot["ci_low"], "ci_high": boot["ci_high"]})
    return rows


if __name__ == "__main__":
    import json
    from pathlib import Path

    df = pd.read_parquet("data/processed/features_matches_all.parquet")
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df = df[~df["season"].astype(str).isin(LOCKED_SEASONS)]
    df = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)
    results = evaluate_outer_seasons(df)
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    Path("data/processed/goal_model_outer_eval.json").write_text(json.dumps(results, indent=2))
    table = pd.DataFrame(results).pivot_table(index=["target", "model"], columns="season",
                                              values="delta_vs_prior")
    table["mean_delta"] = table.mean(axis=1)
    print(table.round(4).sort_values(["target", "mean_delta"]).to_string())
```

Çalıştır:

```bash
python3 -m src.models.evaluate_goal_models
```

> [!NOTE]
> `FeatureGoalModel` NaN içeren özellikleri `SimpleImputer(median)` ile dolduruyor; imputer pipeline içinde olduğu için her `fit`'te yalnızca eğitim verisinden öğrenilir (sızıntı yok).
> `LOCKED_SEASONS` Faz 1.2'de eklendi. Faz 1 yapılmadan bu import hata verir.
> Çalışma süresi: DC fit'i ~birkaç saniye; 3 DC + 4 feature + 3–4 dış sezon ≈ birkaç dakika. Uzun sürerse `n_boot`'u düşür.

### 2.6 Karar kapısı (Over 2.5 için)

Bir adayı Over 2.5 üretim modeli yapmak için **hepsi** sağlanmalı:

1. Tam sezonlarda (2023/24, 2024/25, 2025/26) `delta_vs_prior` ortalaması **< −0.003** (log-loss).
2. En az 2/3 tam sezonda `delta_vs_prior < 0`.
3. Mevcut `logreg_o25`'ten (aynı dış sezonlarda) ortalama olarak daha iyi.
4. Güvenilirlik tablosunda (Faz 1) en düşük ve en yüksek olasılık dilimleri arasında gerçek oran **aynı yönde** artıyor (monotonluk kabaca).

Hiçbir aday geçmezse Over 2.5 için **prior (taban oran)** kullan ve arayüzde "model sinyali zayıf" göster (Faz 3). Bu da meşru ve dürüst bir sonuç.

---

## FAZ 3 — Over 2.5'i Üretime Alma (API + Arayüz)

### 3.1 Yeni artefakt: `goals_models_v1.joblib`

Mevcut `outcome_models_v1.joblib`'a dokunma (geriye uyumluluk). Yeni eğitim betiği `src/models/train_goals.py`:

```python
"""Train the production goal-matrix models and persist them with their evaluation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.models.dixon_coles import DixonColesModel, over_prob
from src.models.goals_model import FeatureGoalModel, blend_lambdas   # seçime göre
from src.models.model_utils import apply_probability_calibrator
from src.models.train_match_outcome import (
    LOCKED_SEASONS, N_CV_SPLITS, feature_set, fit_probability_calibrator,
)

logger = logging.getLogger("train_goals")

# Faz 2.5 sonuçlarına göre BURAYI doldur:
CHOSEN = {"kind": "dc", "half_life_days": 365.0}   # ör. {"kind": "feature", "alpha": 100.0}
OU_LINES = (1.5, 2.5, 3.5)


def _forward_ou_oof(df: pd.DataFrame, line: float) -> tuple[np.ndarray, np.ndarray]:
    """Forward-only P(over) for calibration. DC refit on all rows before each block."""
    probs, ys = [], []
    for _, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(df):
        block = df.iloc[valid_idx]
        train = df[df["kickoff_millis"] < block["kickoff_millis"].min()]
        model = DixonColesModel(half_life_days=CHOSEN.get("half_life_days")).fit(train)
        probs.append(over_prob(model.predict_matrices(block), line))
        ys.append(((block["home_score"] + block["away_score"]) > line).astype(int).to_numpy())
    return np.concatenate(probs), np.concatenate(ys)


def train_goals_models(
    data_path: str = "data/processed/features_matches_all.parquet",
    model_output_dir: str = "models/production",
) -> Dict[str, Any]:
    df = pd.read_parquet(data_path)
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)

    final_model = DixonColesModel(half_life_days=CHOSEN.get("half_life_days")).fit(df)  # üretim: tüm veri

    calibrators: Dict[str, Dict[str, Any]] = {}
    base_rates: Dict[str, float] = {}
    for line in OU_LINES:
        total = df["home_score"] + df["away_score"]
        base_rates[f"over_{line}"] = float((total > line).mean())
        p, y = _forward_ou_oof(df, line)
        two_col = np.column_stack([1 - np.clip(p, 1e-6, 1 - 1e-6), np.clip(p, 1e-6, 1 - 1e-6)])
        calibrators[f"over_{line}"] = fit_probability_calibrator(two_col, pd.Series(y), [0, 1])

    artifact = {
        "model": final_model,
        "chosen": CHOSEN,
        "ou_lines": list(OU_LINES),
        "calibrators": calibrators,
        "base_rates": base_rates,
        "skill_gate": {},      # Faz 2.6 sonucu: {"over_2.5": "model" | "baseline", ...}
    }
    Path(model_output_dir).mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, Path(model_output_dir) / "goals_models_v1.joblib")
    return artifact


if __name__ == "__main__":
    train_goals_models()
```

> [!IMPORTANT]
> `skill_gate` değerlerini **elle**, Faz 2.6 sonucuna göre doldur (`"model"` veya `"baseline"`). Otomatik doldurma istiyorsan `evaluate_goal_models.py`'ın JSON çıktısını (`data/processed/goal_model_outer_eval.json`) okuyup 2.6'daki kuralı kodla uygula. Başta elle yap, doğrulaması daha kolay.
>
> Kalibratör notu: Over 2.5 raporunda kalibrasyon sonrası log-loss (0.699) ham değerden (0.694) kötüydü; sinyal zayıfken 2 parametreli kalibratör bile gürültü ekleyebiliyor. Faz 2.5 değerlendirmesini **ham** olasılıkla yaptın; kalibratörü yalnızca **iç içe (nested) OOF'ta** log-loss'u düşürüyorsa kullan. Düşürmüyorsa `calibrators[...] = None` bırak ve API'de uygulama.

`run_full_pipeline.py`'a eğitim adımını ekle (diğer `train_*` çağrılarının yanına):

```python
from src.models.train_goals import train_goals_models
...
goals_res = train_goals_models()
```

### 3.2 API: `src/api/server.py`

**(a)** Satır 73 civarı, `outcome_artifact` yüklemesinin hemen altına:

```python
goals_artifact = joblib.load(MODELS_DIR / "goals_models_v1.joblib") if (MODELS_DIR / "goals_models_v1.joblib").exists() else None
```

`dixon_coles` ve `apply_probability_calibrator` import'ları zaten ya da kolayca eklenir:

```python
from src.models.dixon_coles import btts_prob, over_prob, outcome_probs
```

**(b)** Satır 1577–1581'deki Over 2.5 bloğunu **şu mantıkla değiştir** (eski `model_o25` yolunu geri dönüş olarak tut):

```python
over_block = {"over_2_5_goals_pct": None, "source": "legacy"}
goals_extra: Dict[str, Any] = {}
if goals_artifact is not None:
    row_df = pd.DataFrame([{"home_id": home_id, "away_id": away_id}])
    matrix = goals_artifact["model"].predict_matrices(row_df)
    lam_h, lam_a = goals_artifact["model"].lambdas(row_df)
    for line in goals_artifact["ou_lines"]:
        key = f"over_{line}"
        gate = goals_artifact.get("skill_gate", {}).get(key, "baseline")
        if gate == "model":
            p_line = float(over_prob(matrix, line)[0])
            cal = goals_artifact["calibrators"].get(key)
            if cal:
                p_line = float(apply_probability_calibrator(
                    np.array([[1 - p_line, p_line]]), cal)[0, 1])
        else:
            p_line = float(goals_artifact["base_rates"][key])
        goals_extra[key] = {"pct": round(p_line * 100, 1), "source": gate}
    goals_extra["btts_pct"] = round(float(btts_prob(matrix)[0]) * 100, 1)
    goals_extra["expected_home_goals"] = round(float(lam_h[0]), 2)
    goals_extra["expected_away_goals"] = round(float(lam_a[0]), 2)
    prob_o25 = goals_extra["over_2.5"]["pct"]
    over_block = {"over_2_5_goals_pct": prob_o25, "source": goals_extra["over_2.5"]["source"]}
else:
    probs_o25 = outcome_artifact["model_o25"].predict_proba(simulated_df[o25_features])
    calibrator_o25 = outcome_artifact.get("calibrators", {}).get("o25")
    if calibrator_o25:
        probs_o25 = apply_probability_calibrator(probs_o25, calibrator_o25)
    prob_o25 = float(probs_o25[0][1] * 100)
```

**(c)** Döndürülen `outcome` sözlüğüne (satır ~1685–1690) **geriye uyumlu** ekle:

```python
"outcome": {
    "home_win_pct": round(prob_h, 1),
    "draw_pct": round(prob_d, 1),
    "away_win_pct": round(prob_a, 1),
    "over_2_5_goals_pct": round(prob_o25, 1),
    "over_2_5_source": over_block["source"],     # "model" | "baseline" | "legacy"
},
"goals": goals_extra,
```

**(d)** Satır 467'de (`over_2_5_goals_pct` fikstür listesi) aynı `p["outcome"]` kullanıldığı için ekstra iş gerekmez; sadece `over_2_5_source`'u da oraya geçirmek istersen aynı satırın yanına ekle.

### 3.3 Arayüz

Dosyalar ve satırlar: `PredictorTab.jsx` (~597–602), `FixturesTab.jsx` (~881), `MatchDetailModal.jsx` (~605, ~796).

- `over_2_5_source === "baseline"` ise yüzdenin yanına küçük bir etiket koy: **"Taban oran (model sinyali zayıf)"**.
- `over_2_5_source === "model"` ise normal göster.
- Yeni alanları (`goals.btts_pct`, `goals["over_1.5"]`, `goals["over_3.5"]`, `goals.expected_home_goals`) `PredictorTab` içinde mevcut Over 2.5 çubuğunun altında göster.
- JS'te `goals["over_2.5"]` gibi anahtarlar noktalı; köşeli parantez kullan.

### 3.4 Kabul kriteri

```bash
curl -s "http://localhost:<port>/api/predict?home_id=<A>&away_id=<B>" | python3 -m json.tool | head -60
```
(Port ve parametre adlarını `start.sh` / `server.py`'dan doğrula.) Çıktıda `over_2_5_goals_pct`, `over_2_5_source` ve `goals` bloğu olmalı. Toplam Over 1.5 ≥ Over 2.5 ≥ Over 3.5 olmalı.

---

## FAZ 4 — 1X2 Ensemble (Lojistik Regresyon + Dixon–Coles)

### 4.1 Neden işe yarayabilir
İki model farklı bilgi kullanıyor (özellikler vs takım kimliği kümesi) ve farklı hata yapıyor. Log-olasılık karışımı bu tür durumlarda sık sık tek modelden küçük de olsa daha iyi çıkar.

### 4.2 Hizalama kuralı (en kritik nokta)
İki modelin OOF tahminleri **aynı maçlar için ve aynı sırada** olmalı. Mevcut kod:
- Lojistik OOF: `chronological_oof_predictions(model, dev_fit[cols], ...)` — `TimeSeriesSplit(4)` bloklarıyla `dev_fit` üzerinde.
- DC OOF (`_dixon_coles_oof_predictions`) ise `matches` çerçevesinin satırlarına göre bölüyor.

`dev_fit` 2022/23'ü hariç tutuyor, DC ise tüm maçlarla çalışabilir. Bu yüzden **blokları lojistiğin bölmesinden al**, DC'yi bu blokların başlangıç tarihinden önceki **tüm** maçlarla eğit:

`src/models/train_match_outcome.py`'a ekle:

```python
def dc_forward_for_blocks(df_all: pd.DataFrame, df_fit: pd.DataFrame, half_life_days: float | None = None) -> np.ndarray:
    """DC probabilities aligned with chronological_oof_predictions(df_fit)."""
    blocks = []
    for _, valid_idx in TimeSeriesSplit(n_splits=N_CV_SPLITS).split(df_fit):
        block = df_fit.iloc[valid_idx]
        start = block["kickoff_millis"].min()
        train = df_all[df_all["kickoff_millis"] < start]
        blocks.append(DixonColesModel(half_life_days=half_life_days).fit(train).predict_proba(block))
    return np.vstack(blocks)


def blend_log(p_a: np.ndarray, p_b: np.ndarray, w: float) -> np.ndarray:
    z = w * np.log(np.clip(p_a, 1e-12, 1.0)) + (1.0 - w) * np.log(np.clip(p_b, 1e-12, 1.0))
    z -= z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def choose_blend_weight(p_a, p_b, y, labels, grid=np.linspace(0.0, 1.0, 21)):
    losses = [_ll(pd.Series(y), blend_log(p_a, p_b, w), labels) for w in grid]
    best = int(np.argmin(losses))
    return float(grid[best]), [round(l, 5) for l in losses]
```

### 4.3 `train_match_outcome_models` içinde kullanım (yalnızca `kind == "1x2"`)

Holdout değerlendirmesi (geliştirme verisiyle ağırlık seç, holdout'ta **bir kez** ölç):

```python
if kind == "1x2":
    df_all_before_holdout = dev   # DC için tarih sınırı: geliştirme bölümü (kilitli sezon df'te yok)
    p_lr_oof, y_oof = oof_probs, oof_targets                       # lojistik OOF (zaten hesaplandı)
    p_dc_oof = dc_forward_for_blocks(dev, dev_fit)                 # DC, aynı bloklar
    w_blend, w_curve = choose_blend_weight(p_lr_oof, p_dc_oof, y_oof, labels)

    blend_oof = blend_log(p_lr_oof, p_dc_oof, w_blend)
    blend_cal = fit_probability_calibrator(blend_oof, pd.Series(y_oof), labels)

    dc_dev = DixonColesModel().fit(dev)
    hold_blend = apply_probability_calibrator(
        blend_log(raw_probs, dc_dev.predict_proba(hold), w_blend), blend_cal)
    res["ensemble"] = {
        "weight_logreg": w_blend,
        "weight_curve": w_curve,
        "log_loss": round(_ll(y_hold, hold_blend, labels), 4),
        "brier": round(float(np.mean(np.sum((hold_blend - np.eye(3)[y_hold.values]) ** 2, axis=1))), 4),
        "draw_auc": round(float(roc_auc_score((y_hold.to_numpy() == 1), hold_blend[:, 1])), 4),
        "bootstrap_vs_single": paired_bootstrap_delta(
            per_match_log_loss(hold_blend, y_hold.to_numpy(dtype=int)),
            per_match_log_loss(probs, y_hold.to_numpy(dtype=int))),
    }
```

> [!NOTE]
> Burada `dev_fit` ile `dev` farkı önemli: DC için eğitim kümesi `dev`'dir (2022/23 dahil), lojistik için `dev_fit`. DC'nin `kickoff_millis < start` filtresi ileriye bakmayı engeller.

### 4.4 Dış sezon doğrulaması
`evaluate_season_holdouts` mantığını (satır 188–235) kopyalayıp `evaluate_season_holdouts_ensemble` yap: her dış sezon için lojistik OOF + DC bloğu + ağırlık seçimi + holdout ölçümü. **Ağırlığı her dış sezonda yalnızca o sezondan önceki veriyle seç.**

### 4.5 Karar kapısı
- Ensemble, tek lojistik modele karşı dış sezonların **≥2/3'ünde** daha düşük log-loss **ve** ortalama fark < −0.002 ise üretime al.
- Aksi halde üretim modeli değişmez; rapora sonucu yaz.

### 4.6 Üretime alma (kapıyı geçerse)
- Artefakta (`outcome_models_v1.joblib` dict'i) ekle: `"model_dc"` (DC, tüm veriyle fit), `"ensemble_weight"`, `"calibrators"["1x2_ensemble"]`.
- `server.py` satır 1568–1575: `if "model_dc" in outcome_artifact:` ise
  ```python
  p_lr = outcome_artifact["model_1x2"].predict_proba(simulated_df[o_features])
  p_dc = outcome_artifact["model_dc"].predict_proba(pd.DataFrame([{"home_id": home_id, "away_id": away_id}]))
  probs_1x2 = blend_log(p_lr, p_dc, outcome_artifact["ensemble_weight"])
  probs_1x2 = apply_probability_calibrator(probs_1x2, outcome_artifact["calibrators"]["1x2_ensemble"])
  ```
  aksi halde eski yolu kullan. `blend_log`'u `model_utils.py`'a taşıyıp iki yerden de import et (döngüsel import olmasın diye).

---

## FAZ 5 — Beraberlik Özellikleri

### 5.1 Eklenecek özellikler (tam tanım)

Hepsi **yalnızca kendi maçından önceki** maçlardan hesaplanır.

| Özellik | Tanım | Shrinkage |
|---|---|---|
| `home_draw_rate_10` | Ev sahibinin son 10 maçında beraberlik oranı | `(beraberlik + 5·0.25)/(n + 5)` |
| `away_draw_rate_10` | Deplasmanın son 10 maçında beraberlik oranı | aynı |
| `pair_draw_rate_10` | İkisinin ortalaması | — |
| `home_low_scoring_10` | Son 10 maçta toplam gol ≤ 2 oranı | `(x + 5·0.45)/(n + 5)` |
| `away_low_scoring_10` | aynı, deplasman | aynı |
| `pair_low_scoring_10` | ortalama | — |
| `pair_total_goals_10` | İki takımın son 10 maçındaki ortalama toplam gol | `(Σ + 5·2.7)/(n+5)` |
| `league_draw_rate_100` | Maçtan önceki son 100 lig maçında beraberlik oranı | `(x + 20·0.25)/(n+20)` |
| `season_progress` | `gameweek / 38` | yok; gameweek yoksa NaN |

Sezon geçişlerinde takım geçmişi **sıfırlanmaz** (takım kalitesi taşınır); az maçı olan (yeni çıkan) takımlar shrinkage ile ligin ortalamasına çekilir.

> Sabitler (0.25, 0.45, 2.7, 5, 20) başlangıç değeridir. **Bunları sonuçlara bakarak ayarlama**; ayarlayacaksan yalnızca geliştirme verisinde yap.

### 5.2 Tek kaynak: `src/features/draw_features.py`

Eğitim ve canlı tahminin **aynı kodu** kullanması için bir durum (state) sınıfı yazıyoruz. Eğitimde maçları sırayla gezip `features` → `update` çağırıyoruz; canlıda, tüm oynanmış maçlar işlendikten sonra elde kalan durumdan `features` çağırıyoruz. Böylece özellik eşleşmesi yapısal olarak garantili.

```python
"""Pre-match draw-propensity features built from a single incremental state."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

PRIOR_DRAW = 0.25
PRIOR_LOW = 0.45
PRIOR_GOALS = 2.7
TEAM_K = 5.0
LEAGUE_K = 20.0
TEAM_WINDOW = 10
LEAGUE_WINDOW = 100

DRAW_PROPENSITY_FEATURES = [
    "home_draw_rate_10", "away_draw_rate_10", "pair_draw_rate_10",
    "home_low_scoring_10", "away_low_scoring_10", "pair_low_scoring_10",
    "pair_total_goals_10", "league_draw_rate_100", "season_progress",
]


def _shrunk(total: float, n: int, prior: float, k: float) -> float:
    return (total + k * prior) / (n + k)


class DrawFeatureState:
    def __init__(self) -> None:
        self.team: Dict[int, deque] = defaultdict(lambda: deque(maxlen=TEAM_WINDOW))
        self.league: deque = deque(maxlen=LEAGUE_WINDOW)

    def _team_stats(self, team_id: int) -> tuple[float, float, float]:
        history = self.team[team_id]
        n = len(history)
        draws = sum(h[0] for h in history)
        low = sum(h[1] for h in history)
        goals = sum(h[2] for h in history)
        return (
            _shrunk(draws, n, PRIOR_DRAW, TEAM_K),
            _shrunk(low, n, PRIOR_LOW, TEAM_K),
            _shrunk(goals, n, PRIOR_GOALS, TEAM_K),
        )

    def features(self, home_id: int, away_id: int, gameweek: Optional[float] = None) -> Dict[str, Any]:
        hd, hl, hg = self._team_stats(int(home_id))
        ad, al, ag = self._team_stats(int(away_id))
        league_n = len(self.league)
        league_draw = _shrunk(sum(self.league), league_n, PRIOR_DRAW, LEAGUE_K)
        progress = float(gameweek) / 38.0 if gameweek is not None and pd.notna(gameweek) and gameweek > 0 else np.nan
        return {
            "home_draw_rate_10": hd, "away_draw_rate_10": ad, "pair_draw_rate_10": (hd + ad) / 2,
            "home_low_scoring_10": hl, "away_low_scoring_10": al, "pair_low_scoring_10": (hl + al) / 2,
            "pair_total_goals_10": (hg + ag) / 2,
            "league_draw_rate_100": league_draw,
            "season_progress": progress,
        }

    def update(self, home_id: int, away_id: int, home_goals: int, away_goals: int) -> None:
        is_draw = int(home_goals == away_goals)
        total = int(home_goals) + int(away_goals)
        entry = (is_draw, int(total <= 2), total)
        self.team[int(home_id)].append(entry)
        self.team[int(away_id)].append(entry)
        self.league.append(is_draw)


def build_draw_state(played: pd.DataFrame) -> DrawFeatureState:
    """State after all played matches (used by the live prediction path)."""
    state = DrawFeatureState()
    for _, batch in _ordered_batches(played):
        _update_batch(state, batch)
    return state


def _ordered_batches(matches: pd.DataFrame):
    ordered = matches.sort_values(["kickoff_millis", "match_id"], kind="mergesort")
    return ordered.groupby("kickoff_millis", sort=False, dropna=False)


def _update_batch(state: DrawFeatureState, batch: pd.DataFrame) -> None:
    for r in batch.itertuples(index=False):
        if pd.notna(r.home_score) and pd.notna(r.away_score):
            state.update(int(r.home_id), int(r.away_id), int(r.home_score), int(r.away_score))


def add_draw_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add DRAW_PROPENSITY_FEATURES, row-aligned with `df` (unplayed fixtures included)."""
    state = DrawFeatureState()
    rows: Dict[Any, Dict[str, Any]] = {}
    has_gw = "gameweek" in df.columns
    for _, batch in _ordered_batches(df):
        for idx, r in batch.iterrows():
            rows[idx] = state.features(
                int(r["home_id"]), int(r["away_id"]), r["gameweek"] if has_gw else None
            )
        _update_batch(state, batch)
    feats = pd.DataFrame.from_dict(rows, orient="index")[DRAW_PROPENSITY_FEATURES]
    return df.drop(columns=[c for c in DRAW_PROPENSITY_FEATURES if c in df.columns]).join(feats)
```

**DOĞRULA:** `features_matches_all.parquet` içinde `gameweek` sütunu var mı ve değerleri 1–38 arası mı? `build_team_match_history` satır 148'de `row.get("gameweek", 0)` kullanıyor, yani büyük ihtimalle var. Yoksa `season_progress` NaN kalır (imputer median ile doldurur; özellik etkisiz olur).

### 5.3 Bağlama

**Eğitim:** `src/features/build_features.py` → `build_feature_dataset` içinde `add_interaction_features` satırından hemen sonra:

```python
from src.features.draw_features import add_draw_features
...
featured_matches = add_interaction_features(featured_matches)
featured_matches = add_draw_features(featured_matches)
```

**Canlı:** `build_prediction_row` imzasına isteğe bağlı parametre ekle:

```python
def build_prediction_row(team_states, strength_state, home_id, away_id, match_date,
                         referee=None, season=None, draw_state=None, gameweek=None):
    ...
    # fill_feature_priors / add_interaction_features'tan ÖNCE:
    if draw_state is not None:
        row.update(draw_state.features(home_id, away_id, gameweek))
```

`server.py` içindeki `get_live_state(season)` fonksiyonunu **aç ve oku** (strength_state'in nasıl hesaplanıp önbelleğe alındığını gör). Aynı kalıpla `draw_state = build_draw_state(played_df_up_to_until)` üret, `get_live_state`'in döndürdüğü demetine ekle ve `build_prediction_row(..., draw_state=draw_state)` çağrısına geçir. **DOĞRULA:** `get_live_state` imzası ve dönüş değeri (şu an 3'lü demet: `team_states, strength_state, until`). Demeti 4'e çıkarırsan fonksiyonu çağıran **tüm** yerleri güncelle (`grep -n get_live_state src/api/server.py`).

**Modelde kullanım:** `train_match_outcome.py`:

```python
from src.features.draw_features import DRAW_PROPENSITY_FEATURES
DRAW_BALANCE_FEATURES = [... mevcut ...]            # dokunma
DRAW_PROPENSITY = list(DRAW_PROPENSITY_FEATURES)

def feature_set(kind, columns, include_draw_propensity: bool = False):
    ...
    wanted = STRENGTH_FEATURES + DIFF_FEATURES + _form_features() + extra + draw_balance
    if kind == "1x2" and include_draw_propensity:
        wanted = wanted + DRAW_PROPENSITY
    ...
```

Varsayılan `False` bırak: ilk önce **deney** olarak ölç, kapıyı geçerse `True` yap.

### 5.4 Ablasyon deneyi
`evaluate_1x2_training_variants` (satır 238–335) zaten özellik varyantlarını karşılaştırıyor. `feature_variants` sözlüğüne iki giriş ekle:

```python
"with_draw_propensity": list(X.columns),                     # X zaten propensity içeriyorsa
"without_draw_propensity": [c for c in X.columns if c not in DRAW_PROPENSITY],
```

Bunun için `evaluate_1x2_training_variants`'a gönderdiğin `X`'in propensity sütunlarını içermesi gerekir: çağrıdaki `df[feats["1x2"]]` yerine `feature_set("1x2", cols, include_draw_propensity=True)` kullan. Raporda yeni tabloda `Draw AUC` ve `Log loss` sütunlarına bak.

### 5.5 Sızıntı ve eşleşme testleri (zorunlu)

`tests/test_draw_features.py`:

```python
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.features.draw_features import DRAW_PROPENSITY_FEATURES, add_draw_features, build_draw_state


def _frame(n=30, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n):
        h, a = rng.choice([1, 2, 3, 4, 5, 6], 2, replace=False)
        rows.append({"match_id": k, "kickoff_millis": 1_700_000_000_000 + k * 86_400_000,
                     "home_id": h, "away_id": a,
                     "home_score": int(rng.poisson(1.4)), "away_score": int(rng.poisson(1.1)),
                     "gameweek": 1 + k // 3})
    return pd.DataFrame(rows)


def test_own_result_does_not_change_own_features():
    df = _frame()
    base = add_draw_features(df)
    tampered = df.copy()
    tampered.loc[10, ["home_score", "away_score"]] = [9, 9]
    out = add_draw_features(tampered)
    assert (base.loc[10, DRAW_PROPENSITY_FEATURES] == out.loc[10, DRAW_PROPENSITY_FEATURES]).all()
    assert (base.loc[:10, DRAW_PROPENSITY_FEATURES].fillna(-1) == out.loc[:10, DRAW_PROPENSITY_FEATURES].fillna(-1)).all().all()


def test_live_state_matches_offline_for_next_match():
    df = _frame()
    played = df.iloc[:-1]
    last = df.iloc[-1]
    offline = add_draw_features(df).iloc[-1][DRAW_PROPENSITY_FEATURES]
    live = build_draw_state(played).features(int(last["home_id"]), int(last["away_id"]), last["gameweek"])
    for k in DRAW_PROPENSITY_FEATURES:
        assert np.isclose(offline[k], live[k], equal_nan=True), k
```

### 5.6 Karar kapısı
Dış sezonlarda (ortak 3 sezon) `with_draw_propensity` vs `without_draw_propensity`: **ortalama log-loss farkı < −0.002** ve **ortalama Draw AUC ≥ +0.01**. Geçmezse `include_draw_propensity=False` kalır; raporda "denendi" olarak not düş.

---

## FAZ 6 — Sürüklenme (Drift) Yönetimi

Gözlem: beraberlik oranı %22.9 → %21.6 → %24.5 → %27.4 → %31.7. Mevcut kalibratör **tek ve global**.

Üç parça, hepsi ayrı ayrı ölçülür:

### 6.1 `league_draw_rate_100` özelliği
Faz 5'te zaten var. Bu, modele "lig şu an daha çok beraberlik üretiyor" bilgisi verir.

### 6.2 Zaman ağırlıklı kalibratör
`fit_probability_calibrator` zaten `sample_weight` destekliyor (satır 138–167). OOF tahminlerinin **satır sırasına göre** üstel ağırlık ver:

```python
def recency_weights(n: int, half_life_rows: float = 300.0) -> np.ndarray:
    age = np.arange(n - 1, -1, -1, dtype=float)
    w = 0.5 ** (age / half_life_rows)
    return w / w.mean()
```

Kullanım (hem `evaluation_calibrator` hem `production_calibrator` için, kıyas amaçlı):

```python
w = recency_weights(len(oof_targets), half_life_rows=300.0)
cal_recent = fit_probability_calibrator(oof_probs, pd.Series(oof_targets), labels, sample_weight=w)
```

Dış sezon ölçümü: `evaluate_season_holdouts` içinde iki kalibratör oluşturup (normal ve ağırlıklı) log-loss'u ayrı sütunlara yaz. `half_life_rows ∈ {150, 300, 600}` dene.

### 6.3 Karar kapısı
Ağırlıklı kalibratör, dış sezonlarda ortalama log-loss'u **≥0.002** düşürürse ve **hiçbir tam sezonda** 0.005'ten fazla kötüleştirmezse üretime al.

> [!WARNING]
> Drift'e çok agresif tepki verme. 60 maçlık son sezon örneği küçük; "son maçlarda çok beraberlik olmuş" bilgisi tek başına tahmin değeri taşımayabilir. Bu fazdaki en değerli şey ölçüm; küçük ve kararlı iyileşme yeterli.

---

## FAZ 7 — Öğrenilmiş xG Modeli (en belirsiz faz)

### 7.1 Önce veriyi incele (karar kapısı)

Şu an elinde **şut koordinatı yok** gibi görünüyor: olay akışında (`data/raw/matches/*_stream.json`) şutlar `type` + metin (`text`) ile geliyor (`team_scenarios.py` metinden parse ediyor). Önce neyin mevcut olduğuna bak:

```bash
python3 - <<'EOF'
import json, glob, collections
paths = sorted(glob.glob("data/raw/matches/*_stream.json"))[:20]
types = collections.Counter(); keys = collections.Counter(); samples = []
for p in paths:
    payload = json.load(open(p))
    events = payload.get("events") or payload.get("event") or []
    # DOĞRULA: olay listesi anahtarının gerçek adını `team_scenarios.py` satır 140'tan sonrasında gör
    for e in events:
        types[e.get("type")] += 1
        if e.get("type") in {"goal", "miss", "attempt saved", "attempt blocked", "post"} and len(samples) < 25:
            samples.append(e)
            keys.update(e.keys())
print(types.most_common(25)); print(keys); 
for s in samples: print(s)
EOF
```

`team_scenarios.py` satır 140'tan sonrasını (olayların hangi anahtarda tutulduğunu) oku ve yukarıdaki betikteki `events = ...` satırını ona göre düzelt.

**Karar:**
- Şut olaylarında **konum bilgisi** (kutu içi/dışı, açı, uzaklık, kafa/ayak, büyük şans) varsa → 7.3 (şut-bazlı xG).
- Yoksa → yalnızca 7.2 (takım-maç düzeyinde öğrenilmiş xG). 7.3'ü **yapma**.

### 7.2 Takım-maç düzeyinde öğrenilmiş xG (veri ne olursa olsun yapılabilir)

Şu anki proxy elle yazılmış ağırlıklarla (`xg proxy`, hesabı `process_season_data.py` içinde olmalı — **DOĞRULA**: `grep -n "xg" src/processing/process_season_data.py`). Bunun yerine, takım-maç satırları üzerinde gol sayısını şu girdilerden **öğrenen** küçük bir Poisson regresyonu kur:

Girdiler (kaynak sütun adları ham veri alanlarına karşılık gelir; işlenmiş sütun adlarını **DOĞRULA**):
- `attempts_ibox`, `attempts_obox` (kutu içi / dışı şut)
- `att_ibox_target`, `att_obox_target` (isabetli şut)
- `big_chance_created`

Eksik değer sorunu: bunların bir kısmı %78–86 dolu. Çözüm: tüm girdiler var olan satırlarda eğit; yoksa iki ek model kur: (a) yalnızca `total_scoring_att` ve `att_ibox_target` (daha dolu girdilerle) (b) tam girdili model. Tahmin sırasında mevcut en kapsamlı modeli kullan. Böylece `%42` doluluk sorunu azalır.

```python
# src/models/train_xg.py (özet)
FULL = ["attempts_ibox", "attempts_obox", "att_ibox_target", "att_obox_target", "big_chance_created"]
LITE = ["total_scoring_att", "att_ibox_target"]

def fit_xg_models(team_rows: pd.DataFrame):
    models = {}
    for name, cols in (("full", FULL), ("lite", LITE)):
        rows = team_rows.dropna(subset=cols + ["goals_for"])
        models[name] = (cols, PoissonRegressor(alpha=1.0, max_iter=2000).fit(rows[cols], rows["goals_for"]))
    return models
```

**Sızıntı notu:** Katsayıları tüm veriyle öğrenip geçmiş maçlara uygulamak, 5–6 parametre için ihmal edilebilir bir sızıntıdır; ama titiz olmak istiyorsan katsayıları dış sezon değerlendirmesinde **her dış sezon için yalnızca önceki sezonlarla** yeniden fit et. Üretim özelliği olarak (Faz 7.4) tüm veriyle fit edilen katsayıları kullanıp bu notu rapora yaz.

Doğrulama: `goals_for` ile `xg_learned` arasındaki log-likelihood'u ve Brier'ı (gol≥1 olayı için), eski proxy ile **grup-bazlı (maça göre) CV** ile karşılaştır.

### 7.3 Şut-bazlı xG (yalnızca 7.1'de konum/şut tipi bilgisi bulunursa)

1. **Veri seti:** her şut olayı = 1 satır. Etiket `goal` (tür: `goal`; `penalty goal` ayrı ele alınır, penaltı için sabit ≈ 0.76 kullan; `own goal` hariç).
2. **Özellikler:** metinden/alanlardan: kutu içi/dışı, kafa/ayak, set-piece/open-play, dakika, skor durumu (`team_scenarios.py` zaten üretiyor), büyük şans.
3. **Model:** `LogisticRegression(C=0.3)` + isteğe bağlı küçük `LGBMClassifier(num_leaves=7, n_estimators=150)`.
4. **Değerlendirme:** `GroupKFold` (maç kimliğine göre grupla). Metrikler: log-loss vs taban oran, ROC-AUC, güvenilirlik. Konum bilgisi olmayan veride AUC ≈ 0.65–0.72 beklenir; <0.62 çıkarsa bu fazı bırak.
5. **Toplama:** takım-maç `xg_model_for/against = Σ P(gol | şut)`.

### 7.4 Üretime alma
Çıktıyı mevcut `home_xg`/`away_xg` yerine **ayrı** sütunlar olarak ekle: `home_xgl`, `away_xgl`. Mevcut `FORM_STATS`'a (satır 43) `xgl_for`, `xgl_against` ekleyip `compute_pre_match_features` yoluyla rolling/EWMA üret; canlı yol aynı kodu kullandığından `build_prediction_row` otomatik alır (form sütunları `_roll_`/`_ewma_` kalıbıyla otomatik toplanıyor, satır 629).

Ablasyonu `evaluate_1x2_training_variants` içinde `without_xg_proxy` yanına `with_learned_xg` olarak ekle.

### 7.5 Karar kapısı
Dış sezonlarda eski proxy'ye göre ortalama log-loss farkı < −0.002. Aksi halde eski proxy kalır. (Rapor zaten "proxy'yi çıkarmak tutarlı fark yaratmıyor" diyor; yeni xG'nin de büyük fark yaratması beklenmemeli. Bu yüzden bu faz **en sona** bırakılmalı.)

> [!NOTE]
> Dış kaynak (Understat, FBref) resmi şut-bazlı xG sağlar. Kullanım şartlarını ve ağ erişimini kendin kontrol et; bu belge scraping kodu içermiyor. Bahis oranlarını kapsam dışı bıraktığını belirtmiştin; bu öneri de oran içermiyor.

---

## FAZ 8 — Regresyon Hedefleri: "Beceri Kapısı" ve Poisson Adayları

### 8.1 Mevcut durum
`model_utils.py` `_include_training_mean` zaten bir "eğitim ortalaması" adayı ekliyor ve CV'de ortalama kazanıyorsa o seçiliyor. Ama Corners/Cards/Saves'te ridge **CV'de** ortalamayı az farkla geçip holdout'ta kaybediyor. Yani seçim kuralı çok cömert.

### 8.2 Kapı fonksiyonu: `src/models/model_utils.py`

Dosyaya ekle:

```python
def apply_skill_gate(
    fold_scores: Dict[str, list],
    selected: str,
    baseline: str = "training_mean",
    min_relative_gain: float = 0.005,
    min_fold_wins: int = 3,
) -> str:
    """Keep a feature model only if it beats the mean predictor by >=0.5% RMSE and wins >=3 of 4 folds."""
    if selected == baseline or baseline not in fold_scores:
        return selected
    sel = np.asarray(fold_scores[selected], dtype=float)
    base = np.asarray(fold_scores[baseline], dtype=float)
    gain = (base.mean() - sel.mean()) / base.mean()
    wins = int((sel < base).sum())
    return selected if (gain >= min_relative_gain and wins >= min_fold_wins) else baseline
```

`chronological_regression_evaluation` içinde (satır 208–220):

```python
cv_rmse: Dict[str, float] = {}
cv_folds: Dict[str, list] = {}            # YENİ
for name, candidate in candidates.items():
    fold_scores = []
    for train_idx, valid_idx in cv.split(X_dev):
        ...
        fold_scores.append(...)
    cv_rmse[name] = float(np.mean(fold_scores))
    cv_folds[name] = fold_scores            # YENİ

raw_selected = min(cv_rmse, key=cv_rmse.get)
selected_name = apply_skill_gate(cv_folds, raw_selected)      # YENİ (eski `selected_name = min(...)` yerine)
```

`metrics`'e ekle: `"skill_gate_applied": bool(raw_selected != selected_name)`, `"raw_selected_model": raw_selected`.

Aynı değişikliği `select_regression_candidate` (satır 88–103) ve `evaluate_season_holdouts` için de yap, ya da `select_regression_candidate` içine gömüp ikisinin de bunu kullanmasını sağla (daha az tekrar). Bunun için `select_regression_candidate`'in fold skorlarını da döndürmesi veya içeride kapıyı uygulaması gerekir; imzayı değiştirirsen çağıranları (`rg -n "select_regression_candidate" src`) güncelle.

### 8.3 Poisson regresyon adayları
Sayı hedefleri (korner, kart, ofsayt, taç) için doğal bağ fonksiyonu log'dur. Her `train_*.py` içindeki `candidates` sözlüğüne ekle:

```python
from sklearn.linear_model import PoissonRegressor
**{
    f"poisson_{alpha:g}": make_regression_pipeline(PoissonRegressor(alpha=alpha, max_iter=2000), scale=True)
    for alpha in (1.0, 10.0, 50.0, 200.0)
},
```

Dosyalar: `train_corners.py`, `train_cards.py`, `train_throws.py`, `train_saves.py`, `train_offsides.py`. (Her birinde `candidates = {...}` yapısını **DOĞRULA**; `train_offsides.py` satır 88–103'te gördüm, diğerleri benzer olmalı.)

> [!NOTE]
> `PoissonRegressor` hedefin negatif olmamasını ister; bu hedefler sayı olduğu için sorun yok. RMSE ile seçmeye devam ediyoruz (API ortalama tahmini kullanıyor), eşik olasılıkları NB2 ile hesaplanıyor.

### 8.4 Kartlara hakem özelliği
`build_features.py` `compute_referee_features` zaten `referee_avg_cards`, `referee_avg_fouls`, `referee_prior_matches` üretiyor (satır 564–611). `train_cards.py` içinde bunların `CURATED_FEATURES` listesinde olup olmadığını **DOĞRULA**. Yoksa ekle ve ablasyonla (özelliğin olduğu/olmadığı) karşılaştır. `referee_prior_matches` küçükse (örn. <10) hakem ortalaması gürültülü olur; shrinkage ekle:

```python
shrunk = (ref_sum_cards + 10 * 4.15) / (ref_n + 10)
```
(`REFEREE_DEFAULTS["referee_avg_cards"] = 4.15`.) Mevcut kod `compute_referee_features` içinde bunu yapıyor mu **DOĞRULA** (satır 580–611).

### 8.5 API'de dürüstlük bayrağı
`server.py` satır 1539–1563 (corners/throws/saves) ve 1593–1637 (offsides/cards): artefakt metriklerinden `skill_gate_applied` / `selected_model == "training_mean"` ise yanıta `"model_skill": "baseline"` ekle, aksi halde `"model"`. Arayüzde "Beklenen: 10.3 (takım ortalaması tabanlı)" gibi göster.

### 8.6 Kabul kriteri
Rapor tablosunda hedeflerin çoğu için `Selected model = training_mean` görünüyorsa **bu başarıdır**: model aldatıcı sinyal üretmiyor demek. Offsides ve Throw-ins'in model seçmeye devam etmesi beklenir.

---

## FAZ 9 — Saves Etiket Kurtarma

### 9.1 Mantık
Bir takımın kurtarış sayısı ≈ **rakibin isabetli şutları − rakibin golleri** (penaltı kurtarışları dahil, kendi kalesine atılan goller hariç). Raporda `saves` sağlayıcıda %93.2 dolu; `shots on target` ise ayrı alan(lar).

### 9.2 Önce doğrula (kod yazmadan)
İşlenmiş tabloda hem saves hem rakip isabetli şut bilgisi olan satırlarda eşleşme oranını ölç:

```python
import pandas as pd
df = pd.read_parquet("data/processed/matches_summary_all.parquet")
# DOĞRULA: sütun adları (home_saves, away_saves, home_att_ibox_target ... vb.) — df.columns'a bak
sot_home = df["home_att_ibox_target"].fillna(0) + df["home_att_obox_target"].fillna(0)
sot_away = df["away_att_ibox_target"].fillna(0) + df["away_att_obox_target"].fillna(0)
est_home_saves = sot_away - df["away_score"]       # ev kalecisi: deplasmanın isabetli şutu - deplasman golü
est_away_saves = sot_home - df["home_score"]
mask = df["home_saves"].notna() & df["away_saves"].notna()
exact = ((est_home_saves[mask] == df.loc[mask, "home_saves"]) & (est_away_saves[mask] == df.loc[mask, "away_saves"])).mean()
print("tam eşleşme oranı:", exact)
```

> [!IMPORTANT]
> `att_obox_target` kapsaması %59, yani isabetli şut toplamı çoğu maçta eksik girdiyle hesaplanır (eksik = 0 sayılırsa yanlış). Bu nedenle tahmini yalnızca **iki alanın da mevcut olduğu** satırlarda yap. Tam eşleşme **≥ %95** değilse, bu yolu **kullanma**; olay akışından "attempt saved" olaylarını takıma göre say (korner/kart/ofsayt için yapılan event kurtarmanın aynısı; kodu `src/processing/process_season_data.py` içinde bu kurtarmanın nasıl yapıldığına bakarak çoğalt).

### 9.3 Uygulama
- Kurtarılan değerleri `total_saves` hedefine yazmadan önce `home_saves_event_reconstructed` benzeri bir bayrak sütunu ekle (kart/korner için mevcut kalıbı izle; `data_quality.md` "Event-based label recovery" bölümü bunu anlatıyor).
- `reports/data_quality.md` üreten `data_quality_report.py`'ı, saves için "Usable match labels" satırını gösterecek şekilde güncelle.
- Pipeline'ı yeniden çalıştır; saves örnek sayısı 1371 → ~1580'e çıkmalı.

### 9.4 Kabul kriteri
Saves eksik oranı %13'ten %3'ün altına iner ve ilgili `Missing` tablosunda takım başına eksik oranı eşitlenir (Arsenal %15 → ~%0–2).

---

## FAZ 10 — İleriye Dönük Kayıt, Testler, Dokümantasyon

### 10.1 İleriye dönük günlüğe yeni tahminleri ekle
`src/analytics/prospective_1x2_benchmark.py` `snapshot()` (satır 57–145) şu an yalnızca 1X2'yi kaydediyor. Dosyayı **aç**, günlüğe yazılan kaydın alanlarını gör ve ekle:

- `ensemble` olasılıkları (Faz 4 üretildiyse),
- `over_1.5/2.5/3.5` ve `btts` olasılıkları + `source` ("model"/"baseline"),
- model artefaktlarının parmak izi (`_artifact_fingerprint` zaten var; `goals_models_v1.joblib` için de uygula).

`score()` (satır 145–231) içinde, Over/Under ve BTTS için log-loss/Brier'ı ve taban oran karşılaştırmasını hesapla ve yazdır. Aynı maç ve aynı artefakt için yinelenen kayıt yazmama kuralını koru.

Düzenli çalıştırma:
```bash
python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14
python3 -m src.analytics.prospective_1x2_benchmark score
```
Bunu haftalık otomatikleştirmek istersen `/schedule` komutunu kullanabilirsin.

### 10.2 Test özeti

| Test dosyası | Ne doğrular |
|---|---|
| `tests/test_goal_matrix.py` (Faz 2.3) | Matris toplamı 1, tutarlı çizgiler, DC çıktı şekli |
| `tests/test_draw_features.py` (Faz 5.5) | Kendi sonucu kendi özelliğini değiştirmez; canlı = çevrimdışı |
| `tests/test_eval_utils.py` | Bootstrap: eşit kayıpta Δ≈0, açık üstünlükte CI<0 |
| `tests/test_skill_gate.py` | Kapı: kazanç <%0.5 ise baseline'a döner |

Örnek `tests/test_eval_utils.py`:

```python
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.models.eval_utils import paired_bootstrap_delta


def test_bootstrap_identical_losses_centered_on_zero():
    a = np.random.default_rng(0).uniform(0.5, 1.5, 300)
    r = paired_bootstrap_delta(a, a.copy())
    assert abs(r["mean_delta"]) < 1e-12 and r["ci_low"] <= 0 <= r["ci_high"]


def test_bootstrap_detects_clear_improvement():
    rng = np.random.default_rng(1)
    base = rng.uniform(0.8, 1.2, 400)
    better = base - 0.05
    r = paired_bootstrap_delta(better, base)
    assert r["ci_high"] < 0 and r["p_a_better"] > 0.99
```

Örnek `tests/test_skill_gate.py`:

```python
from src.models.model_utils import apply_skill_gate


def test_gate_falls_back_when_gain_small():
    folds = {"ridge_100.0": [3.00, 3.01, 3.02, 3.03], "training_mean": [3.01, 3.02, 3.03, 3.04]}
    assert apply_skill_gate(folds, "ridge_100.0") == "training_mean"


def test_gate_keeps_model_with_clear_gain():
    folds = {"ridge_10.0": [2.8, 2.8, 2.8, 2.8], "training_mean": [3.0, 3.0, 3.0, 3.0]}
    assert apply_skill_gate(folds, "ridge_10.0") == "ridge_10.0"
```

Çalıştırma:
```bash
python3 -m pytest tests -q          # pytest kuruluysa
# kurulu değilse: pip install pytest  (veya mevcut stilde `python3 tests/<dosya>.py`)
```

### 10.3 Dokümantasyon senkronu (zorunlu)
Aşağıdakileri **kısa, tekrarsız** güncelle:

| Dosya | Eklenecek |
|---|---|
| `README.md` | Yeni modüller (`goals_model`, `train_goals`, `draw_features`, `eval_utils`) ve yeni komutlar |
| `ARTIFACT_REGISTRY.md` | `goals_models_v1.joblib` (içerik, eğitim veri aralığı, hangi komutla üretilir) |
| `PROJECT_STATUS.md` | Hangi faz tamamlandı, hangi karar kapısı geçti/geçmedi |
| `reports/1x2_model_audit.md` | Faz 4–6 sonuçları (elle) |
| `reports/model_benchmarks.md` | Otomatik; `run_full_pipeline.py` içine yeni tablo üreten kodu ekledikten sonra yeniden üret |

### 10.4 Rapor üreticisine yeni bölümler
`run_full_pipeline.py` `generate_benchmark_report` içine (diğer bölümlerin yanına) şunları ekle:
- Over/Under çizgileri için dış sezon tablosu (Faz 2.5 JSON'undan)
- Ensemble tablosu (Faz 4)
- Draw-propensity ablasyonu (zaten `1x2_variant_outer_holdouts` içinde)
- Bootstrap ve güvenilirlik tabloları (Faz 1)

---

## Ek A — Karar Kapıları Özeti

| Faz | Geçmesi gereken | Geçmezse |
|---|---|---|
| 2/3 Over 2.5 | Tam sezonların ortalama Δlog-loss < −0.003, ≥2/3 sezon iyi, mevcut modelden iyi | Prior göster, "model sinyali zayıf" etiketi |
| 4 Ensemble | ≥2/3 dış sezonda daha iyi ve ortalama Δ < −0.002 | Tek lojistik modeli koru |
| 5 Beraberlik özellikleri | Ortalama Δlog-loss < −0.002 ve ΔDraw AUC ≥ +0.01 | Özellik `False` kalır |
| 6 Drift | Ağırlıklı kalibratör ortalama Δ ≤ −0.002, hiçbir sezonda +0.005'ten kötü değil | Normal kalibratör |
| 7 xG | Eski proxy'ye göre ortalama Δ < −0.002 | Eski proxy |
| 8 Beceri kapısı | Yok (her zaman uygulanır) | — |
| 9 Saves | Tam eşleşme ≥ %95 (tahmin yolu) | Olay akışı yolu |

## Ek B — Yapılmaması Gerekenler

1. **Holdout'a bakıp ayar yapma.** Sabitleri (shrinkage, yarı ömür, alpha) yalnızca geliştirme verisi / dış sezon ablasyonunda seç. Aynı sezonla hem seçip hem raporlarsan sonuç şişer (raporun kendisi de bunu kabul ediyor).
2. **Sızıntı.** Yeni her özellik için "kendi maçının sonucu bu özelliği değiştirir mi?" testini yaz (Faz 5.5'teki kalıp).
3. **Canlı ≠ eğitim.** Yeni her özellik için eğitim ve canlı yol **aynı fonksiyondan** çıkmalı.
4. **2026/27'yi kilitli tut.** Faz 1.2'ye uy.
5. **Doğrulanmamış sütun adlarını varsayma.** "DOĞRULA" işaretli yerleri kontrol et.
6. **Tek seferde her şeyi birleştirme.** Faz başına bir dal, bir rapor, bir commit.

## Ek C — Tahmini Efor

| Faz | Süre (odaklı çalışma) |
|---|---|
| 1 Değerlendirme altyapısı | 0.5–1 gün |
| 2 Gol modeli + dış sezon karşılaştırması | 1–2 gün |
| 3 Over 2.5 üretime alma (API + UI) | 0.5–1 gün |
| 4 Ensemble | 1 gün |
| 5 Beraberlik özellikleri (+ canlı yol + test) | 1–1.5 gün |
| 6 Drift | 0.5 gün |
| 7 xG | 1 gün (veri incelemesi) + 2–4 gün (karar kapısı geçerse) |
| 8 Beceri kapısı + Poisson | 0.5–1 gün |
| 9 Saves kurtarma | 0.5 gün |
| 10 İleriye dönük kayıt + testler + doküman | 1 gün |

Toplam ≈ 8–13 gün (Faz 7 hariç ≈ 6–9 gün).

---

## Yürütme Kaydı

Bu bölüm, yukarıdaki planın gerçek kod durumunu takip eder. İlerleme için ayrı bir durum dosyası yoktur; faz tamamlandıkça bu tablo ve ilgili fazın açıklaması güncellenecek.

### F1 — Değerlendirme altyapısı

**Durum: Uygulama ve benchmark kabul ölçütleri tamamlandı; otomatik testler çalıştırılmadı.**

Bu çalışma ayrı bir git dalında değil: başlangıçta çalışma ağacında çok sayıda kullanıcı değişikliği vardı. Pipeline'ı geçici kopyada çalıştırdım; üretilen benchmark ve model artefaktını mevcut dosyaların yedeğini aldıktan sonra güncelledim.

| Alan | Yapılan / mevcut durum |
|---|---|
| Ortak metrik yardımcıları | `src/models/eval_utils.py` eklendi: maç bazında log-loss, eşleştirilmiş paired bootstrap, quantile reliability tablosu ve ECE. Boş/düzensiz girdiler ile sabit tahminlerdeki qcut durumu ele alındı. |
| Kilitli sezon | `src/models/train_match_outcome.py` içinde `LOCKED_SEASONS = {"2026_27"}` tanımlandı. Kilitli maçlar 1X2 ve Over 2.5 sınıflandırıcılarının model seçimi, ana holdout, dış-sezon değerlendirmesi ve kalibrasyon verisinden çıkarılıyor. Regresyon ailelerinin mevcut sezon değerlendirmesi F1 kapsamına alınmadı. Sezon sütunu yoksa sessizce devam etmek yerine hata veriliyor. |
| Üretim fit'i | Oynanmış kilitli sezon maçları nihai üretim modellerinin fit'ine girebilir. 1X2 üretim fit'inde mevcut 2022/23 dışlama kuralı da korunuyor. |
| Benchmark raporu | `run_full_pipeline.py` artık sınıf-prior'a karşı bootstrap ortalama farkını ve %95 aralığı, modelin daha iyi olma oranını, ECE'yi; ayrıca Over 2.5 ve beraberlik olasılıkları için reliability tablolarını yazacak şekilde güncellendi. |
| Veri kontrolü | Mevcut `features_matches_all.parquet` içinde 2026/27 için 380 fikstür satırı, 60 oynanmış maç var. Bu 60 maç sınıflandırıcı değerlendirme/kalibrasyon dışında kalır. Diğer dört sezonun 1.520 oynanmış maçı sınıflandırıcı değerlendirme havuzunda kalır. Regresyon raporundaki ayrı holdout tabloları 2026/27 kısmi sezonunu içermeyi sürdürür. |
| Çalıştırma | Tam `run_full_pipeline.py`, mevcut çalışma ağacındaki kullanıcı değişikliklerini korumak için `/tmp/f1-eval.x3mSFR/repo` kopyasında başarıyla tamamlandı. İşlenmiş maç özeti ve özellik dosyalarının SHA-256 değerleri çalışma ağacıyla aynıydı. Yeni `reports/model_benchmarks.md` ve `outcome_models_v1.joblib` çıktıları geri alındı; önceki iki dosya aynı `/tmp/f1-eval.x3mSFR/` klasöründe yedeklendi. |
| Holdout boyutu | 1X2/Over 2.5 ana holdout'u 316'dan 304 maça indi. Değerlendirme havuzunda 1.520 maç kaldı; kilitli sezondan 60 oynanmış maç çıkarıldı. |
| 1X2 sonucu | Log-loss 1.024, sınıf-prior 1.092. Model-prior Δ = −0.0676, %95 bootstrap CI [−0.1063, −0.0285], `P(model better)=1.000`. Draw ECE 0.0700. |
| Over 2.5 sonucu | Log-loss 0.689, sınıf-prior 0.688. Model-prior Δ = +0.0013, %95 bootstrap CI [−0.0065, +0.0094], `P(model better)=0.369`. Model taban tahminini geçmiyor; bu F1 ölçüm çıktısıdır, F2/F3 karar kapısı henüz uygulanmadı. ECE 0.0849. |
| Üretim kalibrasyonu | Kilitli sezon kalibrasyona girmedi: 1X2 için 912 forward-OOF kalibrasyon tahmini (1.200 final-fit satırı), Over 2.5 için 1.216 tahmin (1.580 final-fit satırı). |
| Otomatik testler | Test dosyaları eklenmedi ve pytest çalıştırılmadı. |

**Sonuç:** F1'in bootstrap/reliability bölümleri, kilitli sezon kuralı ve kabul çıktısı tamamlandı. 1X2 mevcut prior'ı anlamlı biçimde geçiyor; Over 2.5 geçmiyor. Üretim artefaktı yenilendiği için çalışan API süreci kullanımdan önce yeniden başlatılmalı. F2, önerilen sıradaki adımdır.

**Uygulama ayrıntısı:** kılavuzun eski taslağında production kalibratörü için kilitli sezondan OOF örnekleri girebilecek bir belirsizlik vardı. Uygulamada kilitli sezonu kalibrasyondan da çıkardım; böylece "model seçimi, kalibrasyon ve değerlendirmede kullanma" kuralı her yerde aynı anlama geliyor. Nihai üretim modelinin kilitli sezonun oynanmış maçlarıyla fit edilmesi ayrı tutuluyor.

İlk geçici pipeline çalıştırması yeni takip sayaçlarını model sonuç nesnesi sanan eski log döngüsünde durdu. Log döngüsü metadata anahtarlarını atlayacak şekilde düzeltildi; sonraki tam çalıştırma başarıyla bitti.

### F2 — Skor matrisi ve gol modelleri

**Durum: Kod ve dış sezon değerlendirmesi tamamlandı; O2.5 karar kapısı iki aday için biçimsel olarak geçti. Üretime alma yapılmadı. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Ortak skor matrisi | src/models/dixon_coles.py içine λ'lardan 0–12 gollü normalize skor matrisi üretimi ve matristen 1X2, O/U ve BTTS olasılıkları eklendi. Eski predict_proba artık aynı matristen 1X2 türetiyor. |
| Zaman ağırlıklı DC | DixonColesModel artık half_life_days alıyor; maç tarihi varsa match_date, yoksa kickoff_millis kullanıyor. None varsayılanında bütün maç ağırlıkları 1. Tarih yok/geçersiz veya yarı ömür sonlu-pozitif değilse hata veriyor. |
| Özellik tabanlı model | src/models/goals_model.py ev/deplasman golleri için ayrı Poisson regresyonu, eğitim içi ρ ızgarası ve geometrik λ harmanını sağlıyor. Alpha 3, 10, 30, 100, 300 değerlendirildi. |
| Dış sezon karşılaştırması | src/models/evaluate_goal_models.py her dış sezonu yalnızca önceki kilitsiz sezonlarla eğitiyor. 2026/27 değerlendirme dışında. Her dış sezonda O/U 1.5/2.5/3.5, BTTS ve 1X2 skorlanıyor; O2.5 için mevcut seçilip kalibre edilen lojistik model de karşılaştırılıyor. |
| Çalıştırma ve çıktı | python3 -m src.models.evaluate_goal_models başarıyla çalıştı. 2023/24, 2024/25 ve 2025/26 dış sezonlarında 380'er maç, toplam 1.140 maç puanlandı. Ham sonuçlar, bootstrap aralıkları, birleştirilmiş O2.5 reliability tabloları ve otomatik kapı özeti [data/processed/goal_model_outer_eval.json](../data/processed/goal_model_outer_eval.json) dosyasında. |
| 1X2 / prior | Tüm matris adayları üç sezonda da sınıf-prior'dan daha düşük log-loss aldı. En düşük ortalama delta feat_alpha3 için −0.0867; bu karşılaştırma mevcut lojistik 1X2 modelini içermediğinden üretim üstünlüğü anlamına gelmiyor. |
| O2.5 kararı | İki aday kılavuzdaki dört ölçütü karşıladı. blend_dc_feat: ortalama sezon Δ −0.00423; 2/3 sezonda negatif; ortalama log-loss 0.68054, mevcut lojistik 0.68729; alt/üst reliability dilim gerçek oranı %55.3 → %69.3. feat_alpha10: ortalama Δ −0.00315; 3/3 sezonda negatif; log-loss 0.68163; uç dilimler %66.7 → %67.5. İki aday da O2.5 kapısını geçti. |
| Belirsizlik | Eşleştirilmiş 1.140 maç bootstrap'ında harman Δ %95 CI [−0.01055, +0.00180], P(model better)=0.900; feat_alpha10 CI [−0.00971, +0.00378], P(model better)=0.818. İki aralık da sıfırı içeriyor. Bu yüzden kapı sonucu adayları F3'e taşımayı destekliyor, üstünlüğü kesinleştirmiyor. |
| Henüz yapılmayanlar | API, artefakt ve arayüz değişmedi. F3 için iki geçen aday arasından seçim ve ürün entegrasyonu gerekiyor. F2 otomatik testleri eklenmedi/çalıştırılmadı; dış sezon değerlendirmesi fonksiyonel çalıştırma olarak yapıldı. |

**F2 kararı:** O2.5'te prior'a dönme koşulu oluşmadı; iki skor-matrisi adayı kapıyı geçti. İkisi de bootstrap CI bakımından belirsiz ve tek bir kazanan çıkmadığı için F3 öncesi aday seçimi açık. F3'te API/arayüz entegrasyonuna başlanabilir; üretim adayı blend_dc_feat (daha iyi ortalama log-loss ve uç dilim ayrımı) veya feat_alpha10 (daha düşük ECE) olarak seçilmeli ve seçim gerekçesi kayda eklenmeli. Bu dış sezon taramasında birden çok aday incelendi; dolayısıyla sonuçları yeni bağımsız doğrulama gibi yorumlamamak gerekir.

### F3 — Over 2.5'i üretime alma

**Durum: Model artefaktı, API ve arayüz tamamlandı; doğrudan tahmin, yerel HTTP yanıtı ve frontend üretim derlemesi başarılı. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Üretim adayı | F2'de O2.5 kapısını geçen ve ortalama log-loss'u daha düşük olan blend_dc_feat seçildi: DC yarı ömrü 365 gün, özellik Poisson alpha 100, iki λ için geometrik harman ağırlığı 0.5. |
| Eğitim ve kilitli sezon | Yeni src/models/train_goals.py üretim modelini oynanmış 1.580 maçla fit ediyor. İleri OOF kalibrasyonu 2026/27 kilitli sezonunu dışarıda bırakıp 1.520 maçta çalışıyor. Eğitim betiği, F2 değerlendirme JSON'unda seçilen aday kapıyı geçmiyorsa artefaktı yazmayı reddediyor. |
| Kalibrasyon | Her gol çizgisi için kalibrasyon, ayrı ileri OOF tahminlerinde genişleyen zaman dilimleriyle ölçülüyor. O2.5 ham log-loss 0.67804, kalibre log-loss 0.68336 (972 iç doğrulama tahmini); kalibrasyon kötüleştirdiği için kullanılmıyor. O1.5 ve O3.5 kalibrasyonu da ham skoru iyileştirmedi ve kapalı kaldı. |
| Artefakt ve pipeline | models/production/goals_models_v1.joblib üretildi. run_full_pipeline.py artık önce dış sezon aday değerlendirmesini yeniliyor, ardından gol modelini eğitiyor; böylece eğitim kapı kanıtını güncel JSON'dan okuyor. |
| API | src/api/server.py artefaktı açılışta yüklüyor. Yeni goals bloğu O/U 1.5/2.5/3.5, BTTS ve λ gol beklentilerini aynı skor matrisinden döndürüyor. outcome.over_2_5_source değeri model, baseline veya eski artefakt yolu için legacy olabiliyor. goals artefaktı yoksa önceki O2.5 sınıflandırıcı geri dönüşü korunuyor. Fikstür hızlı tahmin nesnesine de kaynak ve gol alanları eklendi. |
| Arayüz | PredictorTab O1.5/O3.5, BTTS ve model gol beklentisini gösteriyor. FixturesTab ve MatchDetailModal da kaynak taban oran olduğunda “Taban oran (model sinyali zayıf)” işaretini gösteriyor. |
| Doğrulama | Üretim artefaktı yüklendikten sonra predict_match(1, 4) doğrudan çağrıldı: O1.5 %79.9, O2.5 %56.5, O3.5 %34.2, BTTS %55.8; λ_ev 1.90, λ_dep 1.05. O/U sırası kabul koşulunu sağladı. Frontend npm build /tmp/premier-goal-ui-f3 yoluna başarıyla derlendi. |
| HTTP doğrulaması | Geçici Uvicorn süreci 127.0.0.1:8001 üzerinde başlatıldı ve /api/predict?home_id=1&away_id=4 yanıt verdi. JSON'da over_2_5_goals_pct, over_2_5_source=model ve goals bloğu mevcut; O1.5 %79.9 ≥ O2.5 %56.5 ≥ O3.5 %34.2. Doğrulama süreci test sonrasında kapatıldı. |

**F3 kararı:** Model olasılıkları ham skor matrisinden gelir; nested OOF kalibratörleri ham log-loss'u düşürmediği için kullanılmıyor. API ve arayüz geriye uyumlu alanları taşıyor. Üretim artefaktı API açılışında yüklendiğinden mevcut API süreci yeni gol modelini kullanmak için yeniden başlatılmalı.

### F4 — 1X2 lojistik + Dixon–Coles ensemble

**Durum: İleri OOF hizalaması, ana holdout ölçümü ve üç tam sezonda dış doğrulama tamamlandı. Karar kapısı geçmedi; üretim artefaktı mevcut lojistik model olarak bırakıldı. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| OOF hizalaması | `src/models/train_match_outcome.py` içindeki `dc_forward_for_blocks`, lojistik `TimeSeriesSplit(4)` doğrulama bloklarını kullanıyor. Her DC modeli o bloğun ilk başlama zamanından önceki tüm maçlarla fit ediliyor; böylece 2022/23 lojistik fit'inden çıkarılsa da DC geçmişi korunuyor. |
| Harman ve kalibrasyon | `src/models/model_utils.py` içindeki `blend_log` log-olasılıkları harmanlıyor. Ağırlık 0.00–1.00 arasında 0.05 adımla, yalnızca ileri OOF log-loss ile seçiliyor; ensemble kalibratörü harmanlanmış OOF tahminlerinden fit ediliyor. |
| Dış sezon yöntemi | Her tam sezonda aday lojistik model geçmiş verideki walk-forward CV ile seçildi; ağırlık ve iki kalibratör yalnızca o sezon öncesi OOF tahminleriyle belirlendi. Holdout sezonu seçim ve kalibrasyona girmedi. 2026/27 kilitli sezon değerlendirme verisinden çıkarıldı. |
| 2023/24 sınır durumu | Mevcut lojistik üretim kuralı 2022/23 etiketlerini fit dışında tutuyor. 2023/24 için bundan sonra geçmiş sezon kalmadığından dış doğrulama lojistiği yalnızca bu ilk sezon ölçümünde 2022/23 ile fit edildi; aksi durumda o sezon değerlendirilemez ve 3 tam sezonluk karar paydası oluşmaz. Bu istisna yalnızca dış değerlendirmeye ait; üretim fit kuralı değişmedi. |
| Dış sezon sonuçları | Mevcut [ensemble değerlendirme JSON'unda](../data/processed/1x2_ensemble_outer_eval.json) ağırlık lojistik/DC: 2023/24 **0.35**, log-loss **0.95393 / 0.97118**, Δ **+0.01725**; 2024/25 **0.50**, **0.99811 / 0.99961**, Δ **+0.00150**; 2025/26 **0.65**, **1.02593 / 1.02009**, Δ **−0.00584**. Ensemble 3 sezonun yalnızca 1'inde daha iyi; ortalama Δ **+0.00430**. Eşleştirilmiş bootstrap aralıkları her sezonda sıfırı içeriyor. |
| Ana holdout | Geliştirme OOF'sinde seçilen lojistik ağırlığı **0.50** oldu. Kalibre ensemble log-loss **1.0246**, kalibre lojistik **1.0240**; ensemble−lojistik Δ **+0.00054**, %95 eşleştirilmiş bootstrap aralığı **[−0.01493, +0.01612]**, `P(ensemble better)=0.475`. Bu holdout tek başına da ensemble lehine kanıt vermiyor. |
| Karar kapısı | Gereken: en az **2/3** tam sezonda daha düşük log-loss ve ortalama Δ **< −0.002**. Güncel dış sezon dosyası: **1/3** sezon ve ortalama **+0.00430**; iki koşul da başarısız. |
| Üretim / API | `model_dc`, `ensemble_weight` ve `calibrators["1x2_ensemble"]` üretilmedi. `models/production/outcome_models_v1.joblib`, F4 çalışması öncesindeki dosya baytlarına geri yüklendi; API'nin ensemble dalı artefaktta `model_dc` bulunduğunda kullanılacak şekilde koşullu. Mevcut artefakt bu dalı tetiklemiyor. |
| Çalıştırma | `PYTHONPATH=. python3 -m src.models.train_match_outcome` başarıyla tamamlandı. Değerlendirme JSON'u yenilendi. Otomatik test dosyaları eklenmedi ve test paketi çalıştırılmadı. |

**F4 kararı:** Dixon–Coles tahminini lojistik tahminle harmanlamak bu üç sezonda tutarlı bir iyileşme sağlamadı; ortalama log-loss kötüleşti. Üretimde mevcut tek lojistik 1X2 modeli korunuyor. Yeni bağımsız sezon verisi oluştuğunda aynı dış sezon değerlendirmesi yeniden çalıştırılabilir; bu kayıt sonraki fazların takibini değiştirmez.

### F6 — Sürüklenme ve zaman ağırlıklı kalibrasyon

**Durum: Zaman ağırlıklı kalibrasyonun üç tam sezonda dış değerlendirmesi tamamlandı; karar kapısı geçmedi. Standart üretim kalibratörü korundu. `league_draw_rate_100` F5'te değerlendirildi ve F5 kapısı geçmediği için üretim dışı kaldı. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Zaman ağırlıkları | `src/models/train_match_outcome.py` içine `recency_weights` eklendi. Ağırlıklar tahmin satır sırasına göre hesaplanıyor; yarı ömür son OOF satırına göre 150, 300 veya 600 maç. Her kalibratör aynı forward OOF tahminlerini kullanıyor; kilitli sezon OOF havuzuna girmiyor. |
| Dış sezon yöntemi | 2023/24, 2024/25 ve 2025/26 ayrı dış sezonlar olarak ölçüldü. Her sezonun standart ve ağırlıklı kalibratörleri yalnızca o sezondan önceki verideki ileri OOF tahminleriyle fit edildi. İlk dış sezonda üretim dışlama kuralı hiç eğitim satırı bırakmadığı için 2022/23 yalnızca bu sezona ait değerlendirme modelinde kullanıldı; 2026/27 kilitli kaldı. |
| Dış sezon sonuçları | Δ, ağırlıklı kalibratör log-loss'u eksi standart kalibratör log-loss'udur. 150 satır: ortalama **−0.00006**, en kötü sezon **+0.00287**, 1/3 sezonda iyileşme. 300 satır: **−0.00019**, en kötü **+0.00169**, 1/3. 600 satır: **−0.00014**, en kötü **+0.00089**, 1/3. Ayrıntılı sezon skorları ve bootstrap aralıkları [data/processed/1x2_calibration_drift_outer_eval.json](../data/processed/1x2_calibration_drift_outer_eval.json) içinde. |
| Ana holdout | Standart kalibratör log-loss'u **1.024**. Ağırlıklı sonuçlar: 150 satır **1.02735** (Δ **+0.00324**), 300 satır **1.02503** (Δ **+0.00092**), 600 satır **1.02440** (Δ **+0.00030**). Üçü de ana holdout'ta standart kalibratörden kötü. Bu holdout seçim amacıyla kullanılmadı. |
| Karar kapısı | Gereken: ortalama dış sezon Δ **≤ −0.002** ve hiçbir tam sezonda Δ **> +0.005** olmamalı. Üç seçenek de kötüleşme sınırını korudu ancak gerekli ortalama iyileşmeye ulaşmadı. **Hiçbir yarı ömür seçilmedi.** |
| Üretim kalibrasyonu | `calibrators["1x2"]` standart forward OOF kalibratörü olarak bırakıldı. Mevcut 912 OOF kalibrasyon satırı ve 1.200 final lojistik fit satırı korunuyor; artefakt F6 çalışması öncesindeki dosya baytlarına geri yüklendi. |
| Uygulama | `train_match_outcome_models` artık dış sezon ölçümünü ve F6 JSON'unu yeniden üretir; karar kapısı geçerse seçilen yarı ömürle production kalibratörünü güncelleyebilir. Şimdiki sonuçta `selected_half_life_rows` null ve `gate_passed` false. Pipeline aynı outcome eğitim adımını çağırdığı için JSON da pipeline çalışmasında yenilenir. |
| Çalıştırma | `PYTHONPATH=. python3 -m src.models.train_match_outcome` başarıyla tamamlandı. Otomatik test dosyaları eklenmedi ve test paketi çalıştırılmadı. |

**F6 kararı:** Yalnızca zaman ağırlıklı kalibrasyon mevcut standart kalibrasyondan gereken ölçüde iyi çıkmadı; üretim tahminleri değişmedi. `league_draw_rate_100` özelliği F5'te değerlendirildi, ancak F5 kapısı geçmediği için üretim modeline alınmadı.

### F5 — Beraberlik eğilimi özellikleri

**Durum: Dokuz özellik ortak offline/canlı hesaplayıcıyla eklendi ve üç tam sezonda değerlendirildi. Karar kapısı geçmedi; üretim 1X2 artefaktı önceki baytlarına geri yüklendi. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Özellikler | `src/features/draw_features.py` dokuz özelliği üretir: ev/deplasman ve eşleşme için son 10 maç beraberlik/düşük skor oranları, eşleşme toplam gol ortalaması, son 100 lig maçının beraberlik oranı ve gameweek üzerinden sezon ilerlemesi. Kılavuzdaki başlangıç prior ve shrinkage sabitleri değiştirilmedi; takım ve lig geçmişi sezonlar arasında taşınır. |
| Aynı kickoff zamanı | Maçların `kickoff_millis` değerleri aynı olabildiği için özellik satırları aynı başlama zamanlı maçlar için sonuçlar işlenmeden önce çıkarılır; sonra o grubun sonuçları duruma eklenir. Böylece aynı saatteki bir maçın sonucu diğer maçın özelliğine sızmaz. Mevcut oynanmış veride başka maçla aynı kickoff zamanını paylaşan 886 satır bulundu. |
| Offline/canlı eşleşmesi | `build_feature_dataset` ve `train_match_outcome_models` aynı `add_draw_features` uygulamasını kullanıyor. Canlı API, geçmiş oynanmış maçlardan `DrawFeatureState` kurup `build_prediction_row` üzerinden aynı state özelliklerini ekliyor; `get_live_state` önbelleği bu state'i de taşıyor. `gameweek`, mevcut 1.900 satırın tümünde bulunuyordu ve 1–38 aralığındaydı. |
| Üretim özellik seçimi | Eğitim önce `with_draw_propensity` ve `without_draw_propensity` varyantlarını aynı dış sezonlarda karşılaştırıyor. Özellikler ancak kapı geçilirse üretim 1X2 listesine girecek şekilde koşullu; bu çalışmada gate false olduğu için üretim listesi taban özelliklerde kaldı. Fikstür feature parquet'i dokuz sütun eklenerek 580 sütunla yeniden üretildi. |
| Dış sezon yöntemi | `exclude_2022_23` politikası altında 2023/24, 2024/25 ve 2025/26'nın her birinde 380 tam sezon maçı değerlendirildi. 2023/24'te kuralın önceki tüm veriyi dışarıda bırakması nedeniyle eğitim kalmasın diye yalnız o dış sezon değerlendirmesinde 2022/23 geçmişi geri alındı; bu istisna raporlanan JSON'da işaretli. 2026/27 kilitli kaldı. |
| Dış sezon sonuçları | Δ, özellikli model log-loss'u eksi özelliksiz model log-loss'udur. 2023/24: **−0.0009**, Draw AUC Δ **+0.0066**; 2024/25: **+0.0034**, **+0.0191**; 2025/26: **+0.0086**, **−0.0056**. Ortalama log-loss Δ **+0.0037** (kötüleşme), ortalama Draw AUC Δ **+0.0067**. Ayrıntılar [data/processed/1x2_draw_propensity_outer_eval.json](../data/processed/1x2_draw_propensity_outer_eval.json) içinde. |
| Karar kapısı ve artefakt | Gereken: ortalama log-loss Δ **< −0.002** ve ortalama Draw AUC Δ **≥ +0.01**. İki koşul da başarısız. `models/production/outcome_models_v1.joblib`, F5 eğitim çalışması öncesindeki dosyanın SHA-256 değeri `fbd51904b437268909d2bb5e144143c3af1895ee13102e59812356e0e8bbe183` olacak şekilde byte-for-byte geri yüklendi. |
| Çalıştırma ve testler | Özellik veri kümesi doğrudan `build_feature_dataset` ile yeniden üretildi. `train_match_outcome_models()` dış değerlendirmeyi ve mevcut model eğitim/raporlarını başarıyla çalıştırdı; değerlendirme sırasında eksik `test_samples` alanı fark edilip sonuç sözlüğüne eklendi. Ayrı otomatik test eklenmedi/çalıştırılmadı. |

**F5 kararı:** Bu dokuz beraberlik özelliği ortalama log-loss'u iyileştirmedi ve iki gate ölçütünü de karşılamadı. Özellik kodu ve dış değerlendirme kaydı korundu; üretim modeline özellikler alınmadı. `league_draw_rate_100` da bu kararın kapsamındadır. Yeni bağımsız sezon verisi oluştuğunda aynı kapı yeniden ölçülebilir.

### F8 — Regresyon beceri kapısı ve Poisson adayları

**Durum: Beş sayım hedefinde beceri kapısı ve Poisson adayları uygulandı; özellik verisi yenilendi, üretim artefaktları yeni seçime göre eğitildi. Ana CV seçiminde kurtarış modeli ortalama tahminine döndü. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Beceri kapısı | `src/models/model_utils.py` içindeki `apply_skill_gate`, özellikli adayın dört expanding-window CV katında fold-fitted `training_mean` baz çizgiyi en az **%0,5 RMSE** geçmesini ve **4 katın en az 3'ünü** kazanmasını şart koşuyor. Aynı seçim `chronological_regression_evaluation` ve sezon bazlı dış değerlendirmede kullanılıyor. Başarısızsa hem holdout hem üretim modeli `training_mean` olarak fit ediliyor; seçim holdout'a bakmıyor. |
| Poisson adayları | Korner, taç, kurtarış, kart ve ofsayt adaylarına `PoissonRegressor(alpha=1, 10, 50, 200; max_iter=2000)` eklendi. Tüm beş hedefin verideki değerleri negatif değil. Özellik imputation/ölçekleme her CV katının içinde fit edilmeye devam ediyor. |
| Hakem özelliği | `train_cards.py` zaten `referee_avg_cards` ve `referee_avg_fouls` kullanıyordu; önceki özellik üretiminde küçük hakem örnekleri prior'a çekilmiyordu. `compute_referee_features` şimdi her iki ortalamayı 10 maçlık lig prior'ıyla shrink ediyor (`4.15` kart ve `21.5` faul). Aynı `match_date` grubundaki maçların özellikleri geçmiş güncellenmeden çıkarılıyor. |
| Özellik verisi | Güncel F7 temizliği xG proxy sütunlarını kaldırdığı için sayım hedeflerine ait özellik verisi yeniden üretildi; çıktı **550 sütun** içeriyor. `train_saves.py` özellik listesi de artık kaldırılmış xG proxy rolling sütunlarına bağlı değil. Sayım verileri: korner/kart/taç/ofsayt **1.580**, kurtarış **1.371** oynanmış maç. |
| Seçim sonuçları | Kriter: CV RMSE kazanımı ve kazanılan kat sayısı. Korner `poisson_10`: **%0,677**, **3/4**; taç `poisson_10`: **%14,635**, **4/4**; kurtarış `ridge_500` ham kazanan olsa da **%0,733**, **2/4** nedeniyle `training_mean`; kart `ridge_500`: **%1,441**, **4/4**; ofsayt `ridge_250`: **%3,657**, **4/4**. Yani ana seçimde yalnızca kurtarış ortalama baz çizgiye döndü. |
| Ana kronolojik holdout | RMSE model/baz çizgi: korner **3,2198 / 3,2405**; taç **7,0675 / 7,3881**; kurtarış **2,1955 / 2,1955**; kart **2,0298 / 2,0014**; ofsayt **1,9043 / 2,0238**. Kart Ridge'i CV kapısını geçti fakat bu holdout'ta baz çizgiden kötü çıktı; bu holdout seçime katılmadığından model sonradan değiştirilmedi. MAE ve bütün sezon sonuçları JSON'da. |
| Sezon bazlı sonuçlar | Her sezonda yalnızca önceki sezonlarla model/CV seçimi yapıldı. Tam sezonlarda taç ve ofsayt seçilen modelleri 3/3 sezonda korudu; korner, kart ve kurtarış bazı sezonlarda `training_mean`'e döndü. 2026/27 için 60 maçlık kısmi regresyon holdout'u mevcut protokol gereği raporda duruyor; kilitli 1X2 sınıflandırıcı değerlendirmesiyle karıştırılmamalı. Ayrıntılar [data/processed/regression_skill_gate_eval.json](../data/processed/regression_skill_gate_eval.json) içinde. |
| API ve arayüz | `predict_match` beş sayım bloğuna `model_skill: "model" | "baseline"` ekliyor; hızlı fikstür tahmini korner/kart etiketlerini de taşıyor. Predictor, maç ayrıntısı ve fikstür kartları baz çizgi kullanıldığında “Veri ortalaması”/“Veri ortalaması tabanlı tahmin” gösteriyor. Benchmark üreticisi artık ham CV kazananını, son seçimi ve kapı kararını yazacak şekilde güncellendi. |
| Çalıştırma ve testler | Özellik verisi doğrudan `build_feature_dataset` ile yenilendi; beş trainer doğrudan çalıştırıldı ve modeller `models/production/` altındaki kendi artefaktlarına kaydedildi. Değerlendirme dosyasına yukarıdaki tam CV/holdout/sezon metrikleri yazıldı. API endpoint'i ve frontend build'i bu turda çalıştırılmadı; otomatik test eklenmedi ve test paketi çalıştırılmadı. |

**F8 kararı:** Önceden belirtilen CV kapısı beş sayım ailesine uygulandı. Kurtarışta zayıf Ridge yerine ortalama üretime alındı. Korner ve taçta Poisson, ofsaytta Ridge, kartta Ridge kapıyı geçti ve üretim için seçildi. Kart sonucu holdout'ta ortalamadan kötü olsa da holdout seçimde kullanılmadı; bu nedenle yeni bağımsız veride izlenmesi gereken açık risk olarak kaydedildi. Ayrı benchmark raporu bu çalışmada eski 1X2 artefakt metrikleriyle yeniden yazılmadı; `run_full_pipeline.py` üreticisi sonraki tam pipeline çalışmasında yeni kapı sütunlarını gösterecek şekilde güncellendi.

### F9 — Saves etiket kurtarma

**Durum: Etiket kurtarma ve raporlama tamamlandı; saves özellik verisi ve üretim artefaktı güncellendi. Beceri kapısı üretimdeki ortalama tahminini korudu. Otomatik test eklenmedi/çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Formül kontrolü | Kaleci saves değerini rakip takımın isabetli şut sayısı eksi rakip golleri olarak türetme adayı, sağlayıcıda iki tarafın `ontarget_scoring_att` alanı bulunan **1.512/1.580** maçta incelendi. Sağlayıcının iki saves tarafının da bulunduğu 1.368 eşleşmede formül iki tarafı birlikte yalnızca **888/1.368 (%64,9)** kez tam eşleştirdi; kılavuzdaki **%95** eşiğini geçmedi. `att_ibox_target + att_obox_target` bileşenlerini kullanan alternatif ise dört bileşenin de bulunduğu 406 maçın yalnızca **13'ünde (%3,2)** tam eşleşti. Bu nedenle şut formülüyle etiket doldurulmadı. |
| Event eşleme | `attempt saved` ve `penalty saved` olayları sayılıyor. Metindeki ilk parantezli takım şutörün takımıdır; kurtarış rakip kaleci tarafına yazılıyor. Takım adları aksan/noktalama farklarına göre normalize ediliyor. Mevcut **1.580** oynanmış maç akışındaki **9.375** kurtarış olayı takım tarafına eşlendi; eksik ya da belirsiz eşleme olduğunda o maç için saves fallback'i kapalı kalıyor. |
| Sağlayıcıyla karşılaştırma | İki saves tarafı da sağlayıcıda bulunan **1.371** maçta event hesabı ev sahibi tarafında **1.292/1.371 (%94,2)**, deplasman tarafında **1.296/1.371 (%94,5)** kez tam eşleşti. Değerler ev sahibi tarafında **%99,78**, deplasman tarafında **%99,93** oranında en fazla bir kurtarış farklıydı. Maç toplamı event sayımı **1.226/1.371 (%89,4)** kez tam, **%99,2** oranında ±1 içindeydi (MAE **0,115**). Sağlayıcının verdiği değer her zaman öncelikli kaldı; karşılaştırma, event kaynaklı değerlerin sağlayıcıyla kusursuz aynı olduğu anlamına gelmiyor. |
| Kaynak ve provenance | `src/processing/process_season_data.py` eksik `home_saves`/`away_saves` değerlerini yalnızca event akışı geçerli ve tüm kurtarışlar takımlara atanabilir olduğunda dolduruyor. Ham değerler `_raw`, API varlığı `_reported`, kurtarılmış değerler `_event_reconstructed`, kullanılabilirlik `_usable` sütunlarında korunuyor. `total_saves_reported` yalnızca iki ham sağlayıcı tarafının da mevcut olduğunu; `total_saves_target_usable` ise son hedefin kullanılabilir olduğunu gösteriyor. |
| Kapsama ve takım dengesi | Önce **1.371/1.580** maç hedef etiketi kullanılabiliyordu; **209** maçta toplam hedef eksikti. Kurtarma 130 ev sahibi ve 84 deplasman takım değeri olmak üzere **214 takım-maç değerini** doldurdu. Kullanılabilir saves hedefi **1.580/1.580** oldu; eksiklik **%13,2'den %0'a** indi. Ham sağlayıcı verisinde en yüksek takım eksikliği Arsenal'de **24/158 (%15,2)** ve Manchester City'de **21/158 (%13,3)** idi; kurtarma sonrasında 27 takımın kullanılabilir takım-maç değerlerinde eksik kalmadı. |
| Veri kalite raporu | `src/analytics/data_quality_report.py` saves satırında ham sağlayıcı etiketi, kurtarılan takım değeri ve kullanılabilir maç hedefini ayrı gösteriyor; sezon ve takım eksikliği artık kurtarma sonrası kullanılabilirliği ölçüyor. Üretilen rapor: [reports/data_quality.md](data_quality.md). Kurtarma sonrasında toplam saves ortalaması **6,035**; yalnızca sağlayıcı etiketi bulunan örneklemde **6,420** idi. Bu fark, eksikliğin rastgele olmayabileceğini gösteriyor; ham sağlayıcı göstergeleri saklanmaya devam ediyor. |
| Özellikler ve model | [features_matches_all.parquet](../data/processed/features_matches_all.parquet) yeniden üretildi (**1.900 satır, 553 sütun**); saves modeli **1.580** tamamlanmış etiketle tekrar eğitildi. Ham CV kazananı `ridge_500`, `training_mean`'e göre **%0,608** RMSE iyileşmesi gösterdi ancak yalnızca **2/4** fold kazandı; kapı en az 3/4 istediği için başarısız. Üretim modeli `training_mean` kaldı; 316 maçlık holdout RMSE/MAE'si baz çizgiyle eşit (**2,3785 / 1,9203**). |
| Artefakt ve değerlendirme | [saves_model_v1.joblib](../models/production/saves_model_v1.joblib), mevcut model seçimiyle yeniden yazıldı. [regression_skill_gate_eval.json](../data/processed/regression_skill_gate_eval.json) saves bölümü yeni kapsama göre güncellendi; [model_benchmarks.md](model_benchmarks.md) saves satırları ve sezon sonuçları aynı değerlendirmeyi gösteriyor. `run_full_pipeline.py` çalıştırılmadı; yalnızca veri işleme, özellik üretimi, saves trainer ve data quality raporu doğrudan çalıştırıldı. |
| Otomatik testler | Test eklenmedi ve test paketi çalıştırılmadı. |

**F9 kararı:** Saves hedefinde şut formülü yeterince güvenilir çıkmadı; takım tarafı belirlenebilen event kurtarması 209 eksik maç hedefini kullanılabilir hale getirdi ve takım bazlı kullanılabilirlik farkını sıfırladı. Mevcut sağlayıcı değerleri korunup yalnızca boş olanlar dolduruldu. Ek örneklem saves Ridge'ini beceri kapısından geçirmediği için üretim tahmin yöntemi değişmedi; `training_mean` kullanılmaya devam ediyor.

### Sonraki fazlar

F1–F10 kod ve dokümantasyon işleri tamamlandı. F7 xG proxy temizliği tamamlandı; F5 beraberlik özellikleri değerlendirildi ancak kapıyı geçmediği için üretime alınmadı. F10'un kalan işi ileriye dönük kayıtları sonuçlarla skorlamak ve otomatik testleri ayrı bir çalıştırmada yürütmektir. Regresyon ailelerinin 2026/27 kısmi sezon holdout'ları mevcut protokolünde duruyor; bunlar F1 sınıflandırıcı kilidinin parçası değil.

### F10 — İleriye dönük kayıt, testler ve dokümantasyon

**Durum: Günlük kodu ve doküman bağlantıları tamamlandı; canlı 14 günlük snapshot başarıyla kaydedildi. Skorlama için henüz tamamlanmış maç yok. Otomatik testler mevcut, çalıştırılmadı.**

| Alan | Yapılan / mevcut durum |
|---|---|
| Snapshot | `python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14` 14 Ekim 2026'da başarıyla çalıştı ve **20** yeni maç öncesi kayıt ekledi. Önceki **60** kayıt korundu; günlükte toplam **80** satır var. |
| Kayıt alanları | Yeni kayıtların her birinde 1X2 ve Over 1.5/2.5/3.5 ile BTTS olasılıkları, `model` kaynak etiketi, tahmin anındaki baz oranlar ve iki model artefaktının SHA-256 parmak izi bulunuyor. Yeni kayıtlardaki parmak izi önekleri: 1X2 `4846811efb2b`, gol modeli `993994d49c9b`. Tüm tahmin zamanları başlama saatinden önce. |
| Ensemble | Güncel üretim artefaktında F4 ensemble bulunmuyor; API ensemble olasılığı döndürmediği için günlükte `ensemble_probabilities` alanı yok. Bu, başarısız F4 kapısıyla uyumlu. |
| Skorlama | Günlükteki **80** maçın hiçbirinin sonucu henüz `matches_summary_all.parquet` içinde tamamlanmış değil. `score` komutu çalıştırılmadı; sonuçlar geldikten sonra 1X2 ve gol pazarları log-loss/Brier metrikleriyle, saklanan tahmin-anı baz oranlarına karşı skorlanacak ve `reports/prospective_1x2_scorecard.json` üretilecek. |
| Benchmark raporu | `run_full_pipeline.py` artık gol pazarı ve 1X2 ensemble dış sezon tablolarını JSON değerlendirmelerinden üretiyor. Eksik bölümler mevcut JSON'lardan `generate_outer_validation_sections()` ile [model_benchmarks.md](model_benchmarks.md) içine eşitlendi. Tam pipeline bu adımda çalıştırılmadı. |
| Dokümantasyon | README, artifact registry, project status ve 1X2 audit F10 komutlarını, artefaktı ve skor kartı yolunu gösteriyor. F4 dış sezon tablosu güncel JSON ile eşleştirildi. |
| Testler | `test_goal_matrix.py`, `test_draw_features.py`, `test_eval_utils.py` ve `test_skill_gate.py` mevcut. Otomatik test paketi çalıştırılmadı. |

**F10 kararı:** Tahmin kaydı artık sonuçlardan bağımsız ve artefakt sürümüne bağlı şekilde tutuluyor; yeni snapshot 20 maç için tüm istenen gol pazarlarını kaydetti. Prospektif performans ölçümü sonuçlar geldikten sonra yapılabilir. Takip komutları:

```bash
python3 -m src.analytics.prospective_1x2_benchmark snapshot --horizon-days 14
python3 -m src.analytics.prospective_1x2_benchmark score
```
