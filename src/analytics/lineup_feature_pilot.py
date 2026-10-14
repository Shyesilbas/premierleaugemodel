"""Replay a confirmed-starting-XI experiment without changing production models.

This small pilot asks whether same-season XI continuity adds signal to the
existing 1X2 feature set. It uses local PulseLive lineups for historical matches
and treats the target match's announced starters as known before kickoff.
It does not label missing players as injured or suspended.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score

from src.models.model_utils import apply_probability_calibrator
from src.models.eval_utils import paired_bootstrap_delta, per_match_log_loss
from src.models.train_match_outcome import (
    EXCLUDED_1X2_TRAINING_SEASONS,
    LOCKED_SEASONS,
    candidate_models,
    chronological_oof_predictions,
    feature_set,
    fit_model,
    fit_probability_calibrator,
    ordered_probabilities,
)


ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data/processed/features_matches_all.parquet"
DETAILS_DIR = ROOT / "data/raw/matches"
OUTPUT_PATH = ROOT / "reports/1x2_lineup_feature_pilot.md"
LABELS = [0, 1, 2]
TARGET_SEASON = "2026_27"
TARGET_MAX_GAMEWEEK = 6
MODEL_NAME = "logreg_C0.003"


def read_starting_xis(match_ids: pd.Series) -> dict[int, dict[int, set[int]]]:
    """Return match -> team -> starting player ids from cached match details."""
    result: dict[int, dict[int, set[int]]] = {}
    for match_id in match_ids.astype(int):
        path = DETAILS_DIR / f"{match_id}_details.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        teams: dict[int, set[int]] = {}
        for team_list in payload.get("teamLists") or []:
            team_id = team_list.get("teamId")
            if team_id is None:
                continue
            starters = {
                int(player["id"])
                for player in (team_list.get("lineup") or [])
                if player.get("id") is not None
            }
            if len(starters) == 11:
                teams[int(team_id)] = starters
        if teams:
            result[int(match_id)] = teams
    return result


def add_xi_continuity(matches: pd.DataFrame, xis: dict[int, dict[int, set[int]]]) -> pd.DataFrame:
    """Add same-season starters retained from each team's previous league XI."""
    frame = matches.sort_values(["kickoff_millis", "match_id"], kind="mergesort").copy()
    histories: dict[int, list[set[int]]] = {}
    previous_season: str | None = None
    home_rates: list[float] = []
    away_rates: list[float] = []

    for row in frame.itertuples(index=False):
        season = str(row.season)
        if season != previous_season:
            histories = {}
            previous_season = season

        match_xis = xis.get(int(row.match_id), {})
        rates: dict[str, float] = {}
        for side, team_id in (("home", int(row.home_id)), ("away", int(row.away_id))):
            current = match_xis.get(team_id)
            prior = histories.get(team_id, [])
            rates[side] = (
                len(current.intersection(prior[-1])) / 11.0
                if current is not None and prior
                else np.nan
            )

        home_rates.append(rates["home"])
        away_rates.append(rates["away"])

        # Store this match's XI only after computing its pre-match features.
        for team_id in (int(row.home_id), int(row.away_id)):
            if team_id not in match_xis:
                histories[team_id] = []
        for team_id, starting_xi in match_xis.items():
            histories.setdefault(team_id, []).append(starting_xi)

    frame["home_xi_previous_match_retention"] = home_rates
    frame["away_xi_previous_match_retention"] = away_rates
    frame["xi_retention_difference"] = frame["home_xi_previous_match_retention"] - frame[
        "away_xi_previous_match_retention"
    ]
    return frame


def score_arm(
    train: pd.DataFrame,
    test: pd.DataFrame,
    columns: list[str],
) -> dict[str, Any]:
    model = candidate_models()[MODEL_NAME]
    train = train.reset_index(drop=True)
    test = test.reset_index(drop=True)
    train_x = train[columns]
    train_y = train["target_1x2"].astype(int)
    train_kickoffs = train["kickoff_millis"]
    oof_probs, oof_y = chronological_oof_predictions(
        model,
        train_x,
        train_y,
        LABELS,
        kickoff_times=train_kickoffs,
    )
    calibrator = fit_probability_calibrator(oof_probs, pd.Series(oof_y), LABELS)
    fitted = fit_model(model, train_x, train_y)
    raw = ordered_probabilities(fitted, test[columns], LABELS)
    probabilities = apply_probability_calibrator(raw, calibrator)
    actual = test["target_1x2"].to_numpy(dtype=int)
    draw_actual = (actual == 1).astype(int)
    return {
        "train_rows": int(len(train)),
        "oof_rows": int(len(oof_y)),
        "test_rows": int(len(test)),
        "log_loss": float(log_loss(actual, probabilities, labels=LABELS)),
        "multiclass_brier": float(np.mean(np.sum((probabilities - np.eye(3)[actual]) ** 2, axis=1))),
        "accuracy": float(accuracy_score(actual, probabilities.argmax(axis=1))),
        "draw_brier": float(np.mean((probabilities[:, 1] - draw_actual) ** 2)),
        "draw_auc": float(roc_auc_score(draw_actual, probabilities[:, 1])) if len(np.unique(draw_actual)) > 1 else None,
        "actual_draws": int(draw_actual.sum()),
        "draw_argmax_picks": int((probabilities.argmax(axis=1) == 1).sum()),
        "mean_draw_probability": float(probabilities[:, 1].mean()),
        "per_match_log_loss": per_match_log_loss(probabilities, actual),
        "probabilities": probabilities.tolist(),
    }


def main() -> None:
    matches = pd.read_parquet(FEATURES_PATH)
    matches = matches[matches["home_score"].notna() & matches["away_score"].notna()].copy()
    matches["target_1x2"] = np.select(
        [matches["home_score"] > matches["away_score"], matches["home_score"] == matches["away_score"]],
        [0, 1],
        default=2,
    ).astype(int)
    matches = matches.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)
    xis = read_starting_xis(matches["match_id"])
    all_played_matches = len(matches)
    matches = add_xi_continuity(matches, xis)
    matches = matches[matches["match_id"].astype(int).isin(xis)].copy()

    test_mask = matches["season"].astype(str).eq(TARGET_SEASON) & matches["gameweek"].le(TARGET_MAX_GAMEWEEK)
    test = matches.loc[test_mask].copy()
    train_mask = ~matches["season"].astype(str).isin(LOCKED_SEASONS | EXCLUDED_1X2_TRAINING_SEASONS)
    train = matches.loc[train_mask].copy()
    if test.empty:
        raise RuntimeError("No first-six-week 2026/27 rows found in the local feature data")
    if len(test) != 60:
        raise RuntimeError(f"Expected all 60 first-six-week matches with lineups, found {len(test)}")

    base_columns = feature_set("1x2", list(matches.columns))
    lineup_columns = base_columns + [
        "home_xi_previous_match_retention",
        "away_xi_previous_match_retention",
        "xi_retention_difference",
    ]
    base = score_arm(train, test, base_columns)
    lineup = score_arm(train, test, lineup_columns)
    prior = np.bincount(train["target_1x2"].astype(int), minlength=3).astype(float)
    prior /= prior.sum()
    actual = test["target_1x2"].to_numpy(dtype=int)
    prior_probs = np.tile(prior, (len(test), 1))
    prior_log_loss = float(log_loss(actual, prior_probs, labels=LABELS))
    prior_brier = float(np.mean(np.sum((prior_probs - np.eye(3)[actual]) ** 2, axis=1)))

    delta = lineup["log_loss"] - base["log_loss"]
    bootstrap = paired_bootstrap_delta(lineup["per_match_log_loss"], base["per_match_log_loss"])
    report = f"""# 1X2 İlk 11 Özelliği Pilot Deneyi

**Tarih:** 14 Ekim 2026  
**Tahmin anı:** Resmî ilk 11 yayımlandıktan sonra.  
**Test aralığı:** 2026/27 ilk altı maç haftası.  
**Test fikstürü:** {len(test)} maç.  
**Eğitim:** {len(train)} maç; yalnız kilitli sezon öncesi, 2022/23 dışlama politikası sabit.  
**İlk 11 kapsaması:** {len(xis)}/{all_played_matches} oynanmış maç; eksik tarihli satırlar bu deneyin eğitiminden çıkarıldı.

## Deney

Aynı `logreg_C0.003` lojistik modeli ve aynı eğitim maçları karşılaştırıldı. Her iki kolun kalibratörü yalnızca eğitim dönemindeki gruplu, genişleyen-zaman OOF tahminlerinde fit edildi. Testte gerçek maçın ilk 11'i kullanıldı; özellikler takımın aynı sezondaki bir önceki maç ilk 11'inden kaç oyuncunun döndüğünü ve ev/deplasman farkını ölçüyor.

Bu, kadro değişimini ölçen bir proxy'dir. Oyuncunun sakat mı, cezalı mı, dinlendiriliyor mu olduğunu tahmin etmez; oyuncu kalitesini de doğrudan ölçmez.

| Ölçüm | Eğitim sınıf prior'ı | Mevcut özellikler | + İlk 11 devamlılığı |
|---|---:|---:|---:|
| Log loss | {prior_log_loss:.4f} | {base['log_loss']:.4f} | {lineup['log_loss']:.4f} |
| Çok sınıflı Brier | {prior_brier:.4f} | {base['multiclass_brier']:.4f} | {lineup['multiclass_brier']:.4f} |
| Doğruluk | {(prior.argmax() == actual).mean():.3f} | {base['accuracy']:.3f} | {lineup['accuracy']:.3f} |
| Beraberlik Brier | — | {base['draw_brier']:.4f} | {lineup['draw_brier']:.4f} |
| Beraberlik AUC | — | {base['draw_auc']:.3f} | {lineup['draw_auc']:.3f} |
| En olası sınıfı beraberlik olan maç | — | {base['draw_argmax_picks']} | {lineup['draw_argmax_picks']} |

İlk 11 devamlılığı eklenince eşleştirilmiş test log-loss farkı **{delta:+.4f}** oldu (negatif değer daha iyi); maç bazlı bootstrap %95 aralığı **[{bootstrap['ci_low']:+.4f}, {bootstrap['ci_high']:+.4f}]**, yeni kolun daha iyi olma payı **{bootstrap['p_a_better']:.3f}**. 60 maçlık örnek küçük olduğundan bu tek başına üretim kararına yetmez. Tahminlerde kullanılan ilk 11'lerin maç önü yayım zaman damgası bu yerel arşivde bulunmuyor; deney ilk 11'in başlama saatinden önce bilindiği varsayımına dayanıyor.

## Yorum

"+ ilk 11" sonucu, yalnız bu tarih aralığı ve model seçimi sabitken hesaplandı. Bu pilot dış sakatlık/ceza arşivi, xG verisi veya oran kullanmadı. Model artefaktlarına dokunulmadı.
"""
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
