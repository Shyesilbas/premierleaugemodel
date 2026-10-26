"""Pre-match prediction for a league fed by TheStatsAPI (LaLiga), in the response shape of the Premier League predictor.

The features of every match, played or not, come from ``build_league_features`` (the same function that built the
training table), so a prediction for an upcoming match uses exactly what the model was trained on. What is served depends
on the walk-forward gate stored in the artifact: the fitted model, or - when the model was not shown to beat the Elo
baseline - the Elo baseline, labelled as a baseline. Count markets (corners, cards ...) are league running averages and
are labelled ``baseline``; no count model exists for these leagues.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from src.competitions.registry import get_competition
from src.config import DB_PATH, competition_paths
from src.models.dixon_coles import align_to_outcome_probs, matrix_from_lambdas
from src.db.database import get_db
from src.features.build_league_features import build_league_features, load_league_matches
from src.models.model_utils import apply_probability_calibrator
from src.models.train_match_outcome import ordered_probabilities

LABELS = [0, 1, 2]
MAX_GOALS = 12
COUNT_PRIORS = {"corners": 9.8, "cards": 4.2, "throws": 33.0, "saves": 7.0, "shots": 24.0, "offsides": 3.5}
COUNT_COLUMNS = {"corners": "total_corners", "cards": "total_cards", "throws": "total_throws", "saves": "total_saves", "shots": "total_shots"}
LINES = {"corners": (8.5, 9.5, 10.5), "cards": (3.5, 4.5, 5.5), "throws": (33.5, 34.5, 36.5), "offsides": (2.5, 3.5, 4.5)}
BASELINE_NOTE = "Model, Elo temelli referans olasılıklarından ayırt edilemedi; Elo temelli referans gösteriliyor."


def _stamp() -> Tuple[int, int]:
    wal = DB_PATH.with_name(DB_PATH.name + "-wal")
    return DB_PATH.stat().st_mtime_ns, wal.stat().st_mtime_ns if wal.exists() else 0


@lru_cache(maxsize=4)
def _table(competition_id: int, stamp: Tuple[int, int]) -> pd.DataFrame:
    conn = get_db()
    try:
        return build_league_features(load_league_matches(conn, competition_id))
    finally:
        conn.close()


@lru_cache(maxsize=4)
def _artifact(path: str, mtime: float) -> Dict[str, Any]:
    return joblib.load(path)


def artifact_for(competition_key: str) -> Optional[Dict[str, Any]]:
    path = competition_paths(competition_key).models / "outcome_models_v1.joblib"
    return _artifact(str(path), path.stat().st_mtime) if path.exists() else None


def _running_mean(history: pd.DataFrame, name: str) -> float:
    column = COUNT_COLUMNS.get(name)
    values = history[column].dropna() if column in history else pd.Series(dtype=float)
    if name == "offsides":
        values = (history["home_offsides"] + history["away_offsides"]).dropna()
    prior = COUNT_PRIORS[name]
    return float((values.sum() + prior * 10.0) / (len(values) + 10.0))


def _count_block(name: str, expected: float) -> Dict[str, Any]:
    block: Dict[str, Any] = {"model_skill": "baseline", "expected_total": round(expected, 1),
                             "expected_home": round(expected / 2.0, 1), "expected_away": round(expected / 2.0, 1)}
    for line in LINES.get(name, ()):
        block[f"prob_over_{str(line).replace('.', '_')}_pct"] = round(float(1.0 - poisson.cdf(int(line), expected)) * 100.0, 1)
    return block


def compute_league_prediction(home_id: int, away_id: int, match_id: Optional[int], competition_key: str) -> Dict[str, Any]:
    comp = get_competition(competition_key)
    artifact = artifact_for(comp.key)
    if artifact is None:
        raise LookupError(f"No trained model for {comp.key}")
    table = _table(comp.id, _stamp())
    rows = table[table["match_id"] == match_id] if match_id is not None else table.iloc[0:0]
    if rows.empty:
        upcoming = table[table["home_score"].isna() & (table["home_id"] == home_id) & (table["away_id"] == away_id)]
        rows = upcoming.head(1)
    if rows.empty:
        raise LookupError("Match not found")
    row = rows.iloc[0]
    columns = artifact["feature_names"]
    serving = artifact["decision"]["serving"]
    if serving == "model":
        outcome = apply_probability_calibrator(ordered_probabilities(artifact["model_1x2"], rows[columns], LABELS), artifact["calibrator"])
    else:
        outcome = ordered_probabilities(artifact["elo_baseline"], rows[artifact["elo_columns"]], LABELS)
    p_home, p_draw, p_away = (float(x) for x in outcome[0])

    lam_h = float(np.clip(artifact["goals_home"].predict(rows[columns])[0], 0.15, 5.5))
    lam_a = float(np.clip(artifact["goals_away"].predict(rows[columns])[0], 0.15, 5.5))
    matrix = align_to_outcome_probs(matrix_from_lambdas(np.array([lam_h]), np.array([lam_a]), rho=artifact["rho"], max_goals=MAX_GOALS), outcome)[0]
    totals = np.arange(MAX_GOALS + 1)[:, None] + np.arange(MAX_GOALS + 1)[None, :]

    def line(threshold: float) -> Dict[str, Any]:
        over = float(matrix[totals > threshold].sum() * 100.0)
        fair = lambda pct: round(100.0 / pct, 2) if pct > 0.5 else None
        return {"over_pct": round(over, 1), "under_pct": round(100.0 - over, 1), "fair_odds_over": fair(over), "fair_odds_under": fair(100.0 - over)}

    lines = {str(t): line(t) for t in (0.5, 1.5, 2.5, 3.5)}
    history = table[table["home_score"].notna() & (table["kickoff"] < row["kickoff"])]
    conn = get_db()
    try:
        info = conn.execute("SELECT home_abbr, home_logo, away_abbr, away_logo, referee_name FROM matches WHERE match_id = ?", (int(row["match_id"]),)).fetchone()
    finally:
        conn.close()
    names = (row["home_name"], row["away_name"])
    favorite = names[0] if p_home >= max(p_draw, p_away) else (names[1] if p_away >= max(p_home, p_draw) else "Beraberlik")
    counts = {name: _count_block(name, _running_mean(history, name)) for name in ("corners", "cards", "throws", "saves", "shots", "offsides")}
    return {
        "home_team": {"id": int(row["home_id"]), "name": names[0], "abbr": (info["home_abbr"] if info else None) or names[0][:3].upper(), "logo": info["home_logo"] if info else None},
        "away_team": {"id": int(row["away_id"]), "name": names[1], "abbr": (info["away_abbr"] if info else None) or names[1][:3].upper(), "logo": info["away_logo"] if info else None},
        "favorite_label": favorite,
        "competition_id": comp.id,
        "model_engine": ("Lojistik regresyon + sıcaklık kalibrasyonu" if serving == "model" else "Elo farkı + ev sahibi avantajı (referans)"),
        "model_skill": "model" if serving == "model" else "baseline",
        "model_note": None if serving == "model" else BASELINE_NOTE,
        "data_cutoff": pd.Timestamp(row["kickoff"]).isoformat(),
        "outcome": {"home_win_pct": round(p_home * 100.0, 1), "draw_pct": round(p_draw * 100.0, 1), "away_win_pct": round(p_away * 100.0, 1),
                    "over_2_5_goals_pct": lines["2.5"]["over_pct"], "over_2_5_source": "poisson_dixon_coles"},
        "goals": {"expected_goals": round(lam_h + lam_a, 2), "expected_home": round(lam_h, 2), "expected_away": round(lam_a, 2),
                  "primary_line": "2.5", "primary_over_pct": lines["2.5"]["over_pct"], "primary_under_pct": lines["2.5"]["under_pct"],
                  "primary_fair_odds_over": lines["2.5"]["fair_odds_over"], "primary_fair_odds_under": lines["2.5"]["fair_odds_under"],
                  "btts_pct": round(float(matrix[1:, 1:].sum()) * 100.0, 1), "lines": lines},
        "corners": counts["corners"], "cards": counts["cards"],
        "referee": {"name": (info["referee_name"] if info else None) or "Atanmadı", "avg_cards": counts["cards"]["expected_total"]},
        "throws": counts["throws"], "saves": counts["saves"], "shots": counts["shots"], "offsides": counts["offsides"],
        "lineup_analysis": None,
    }
