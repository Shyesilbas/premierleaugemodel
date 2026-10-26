"""Model-audit payload for a league fed by TheStatsAPI (LaLiga), in the shape the audit page reads.

Every row is a walk-forward prediction saved by ``train_league_model``: the model had been fitted only on the seasons
before the match's season, so nothing here is in-sample. The season-level benchmark block comes from the same report,
so the page and the report cannot drift apart. Corner and card figures are running league averages (no count model),
and the page labels them as such.
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, competition_paths
from src.models.dixon_coles import align_to_outcome_probs, matrix_from_lambdas
from src.models.eval_utils import multiclass_report
from src.db.database import get_db

HIGH_CONFIDENCE = 0.55
BALANCED_CEILING = 0.42
OUTCOME_KEYS = ("home", "draw", "away")
MAX_GOALS = 12


def _report(competition_key: str) -> Optional[Dict[str, Any]]:
    path = REPORTS_DIR / "models" / f"{competition_key}_walk_forward.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@lru_cache(maxsize=2)
def _predictions(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path)


def _odds(conn: sqlite3.Connection, competition_id: int) -> Dict[int, Dict[str, float]]:
    rows = conn.execute(
        """SELECT o.match_id, o.bookmaker, COALESCE(o.home_last_seen, o.home_open), COALESCE(o.draw_last_seen, o.draw_open), COALESCE(o.away_last_seen, o.away_open),
                  COALESCE(o.over_25_last_seen, o.over_25_open), COALESCE(o.btts_yes_last_seen, o.btts_yes_open)
           FROM external_match_odds o JOIN matches m ON m.match_id = o.match_id WHERE m.competition_id = ?""",
        (competition_id,),
    ).fetchall()
    grouped: Dict[int, List[tuple]] = {}
    for row in rows:
        if row[2] and row[3] and row[4]:
            grouped.setdefault(int(row[0]), []).append(row)
    return {m: {"bookmaker": r[0][1], "home": float(np.mean([x[2] for x in r])), "draw": float(np.mean([x[3] for x in r])), "away": float(np.mean([x[4] for x in r])),
                "over_25": float(np.mean([x[5] for x in r if x[5]])) if any(x[5] for x in r) else None,
                "btts": float(np.mean([x[6] for x in r if x[6]])) if any(x[6] for x in r) else None} for m, r in grouped.items()}


def build_league_audit(competition_key: str, season: str, gameweek: Optional[int] = None) -> Dict[str, Any]:
    comp = get_competition(competition_key)
    report = _report(comp.key)
    path = competition_paths(comp.key).processed / "walk_forward_predictions.parquet"
    empty = {"season": season, "competition_id": comp.id, "overall": {}, "gameweeks": [], "matches": [], "model_available": bool(report)}
    if not report or not path.exists():
        return empty
    serving = report["decision"]["serving"]
    key = "model" if serving == "model" else "elo"
    predictions = _predictions(str(path), path.stat().st_mtime)
    predictions = predictions[predictions["season"] == season]
    if predictions.empty:
        return empty

    conn = get_db()
    try:
        info = pd.read_sql_query(
            """SELECT match_id, gameweek, match_date, home_id, away_id, home_name, away_name, home_score, away_score, total_corners, total_cards
               FROM matches WHERE competition_id = ? AND season = ? AND status = 'COMPLETED'""",
            conn, params=(comp.id, season),
        )
        odds = _odds(conn, comp.id)
        history = pd.read_sql_query(
            "SELECT match_id, match_date, total_corners, total_cards FROM matches WHERE competition_id = ? AND status = 'COMPLETED' ORDER BY match_date, match_id",
            conn, params=(comp.id,),
        )
    finally:
        conn.close()
    # running league averages (the previous matches only) stand in for count models
    for column in ("total_corners", "total_cards"):
        history[f"mean_{column}"] = history[column].expanding().mean().shift(1)
    running = history.set_index("match_id")

    table = info.merge(predictions, on="match_id", how="inner").sort_values(["gameweek", "match_date", "match_id"])
    served = table[[f"{key}_p_home", f"{key}_p_draw", f"{key}_p_away"]].to_numpy()
    matrices = align_to_outcome_probs(matrix_from_lambdas(table["lam_home"].to_numpy(), table["lam_away"].to_numpy(), rho=-0.04, max_goals=MAX_GOALS), served)
    totals = np.arange(MAX_GOALS + 1)[:, None] + np.arange(MAX_GOALS + 1)[None, :]
    over = (matrices * (totals > 2)).sum(axis=(1, 2))
    btts = matrices[:, 1:, 1:].sum(axis=(1, 2))

    rows: List[Dict[str, Any]] = []
    for i, (_, m) in enumerate(table.iterrows()):
        probs = served[i]
        side = OUTCOME_KEYS[int(np.argmax(probs))]
        actual = "home" if m["home_score"] > m["away_score"] else ("draw" if m["home_score"] == m["away_score"] else "away")
        best = float(probs.max())
        quote = odds.get(int(m["match_id"]))
        mean = running.loc[m["match_id"]] if m["match_id"] in running.index else None
        corners = None if mean is None or pd.isna(mean["mean_total_corners"]) else round(float(mean["mean_total_corners"]), 1)
        cards = None if mean is None or pd.isna(mean["mean_total_cards"]) else round(float(mean["mean_total_cards"]), 1)
        total = m["home_score"] + m["away_score"]
        row = {
            "match_id": int(m["match_id"]), "gameweek": int(m["gameweek"]), "match_date": m["match_date"], "home_id": int(m["home_id"]), "away_id": int(m["away_id"]),
            "home_name": m["home_name"], "away_name": m["away_name"], "home_score": int(m["home_score"]), "away_score": int(m["away_score"]),
            "score": f"{int(m['home_score'])} - {int(m['away_score'])}", "is_played": True, "actual_result": actual, "predicted_winner": side,
            "prob_home": round(float(probs[0]) * 100, 1), "prob_draw": round(float(probs[1]) * 100, 1), "prob_away": round(float(probs[2]) * 100, 1),
            "favorite_label": m["home_name"] if side == "home" else (m["away_name"] if side == "away" else "Beraberlik"),
            "confidence_tier": "high" if best >= HIGH_CONFIDENCE else "medium", "is_balanced": best < BALANCED_CEILING, "hit_1x2": side == actual,
            "expected_goals": round(float(m["lam_home"] + m["lam_away"]), 2), "prob_over_25": round(float(over[i]) * 100, 1), "hit_over_25": bool(total > 2) == bool(over[i] >= 0.5),
            "prob_btts": round(float(btts[i]) * 100, 1), "btts_threshold": 50.0, "hit_btts": bool(m["home_score"] > 0 and m["away_score"] > 0) == bool(btts[i] >= 0.5),
            "expected_corners": corners, "actual_corners": None if pd.isna(m["total_corners"]) else float(m["total_corners"]),
            "expected_cards": cards, "actual_cards": None if pd.isna(m["total_cards"]) else float(m["total_cards"]),
            "evaluation_type": "monitoring" if season in LOCKED_SEASONS else "walk_forward",
        }
        row["corner_error"] = None if corners is None or row["actual_corners"] is None else round(corners - row["actual_corners"], 1)
        row["card_error"] = None if cards is None or row["actual_cards"] is None else round(cards - row["actual_cards"], 1)
        if quote:
            row.update(market_home_odds=round(quote["home"], 2), market_draw_odds=round(quote["draw"], 2), market_away_odds=round(quote["away"], 2),
                       market_over_25_odds=quote["over_25"], market_btts_odds=quote["btts"], bookmaker=quote["bookmaker"])
        rows.append(row)

    payload = {"season": season, "competition_id": comp.id, "method": "walk_forward", "model_available": True, "serving": serving,
               "overall": _overall(rows, season, served, table), "matches": rows, "gameweeks": _gameweeks(rows), "benchmark": _benchmark(report, season)}
    payload["overall_accuracy"] = payload["overall"].get("hit_rate_1x2_pct")
    payload["total_matches"] = len(rows)
    if gameweek is not None:
        payload = {**payload, "matches": [r for r in rows if r["gameweek"] == int(gameweek)]}
    return payload


def _rate(hits: int, total: int) -> Optional[float]:
    return round(hits / total * 100.0, 1) if total else None


def _mae(values: List[Optional[float]]) -> Optional[float]:
    real = [abs(v) for v in values if v is not None]
    return round(float(np.mean(real)), 2) if real else None


def _overall(rows: List[Dict[str, Any]], season: str, served: np.ndarray, table: pd.DataFrame) -> Dict[str, Any]:
    high = [r for r in rows if r["confidence_tier"] == "high"]
    y = np.array([OUTCOME_KEYS.index(r["actual_result"]) for r in rows])
    report = multiclass_report(served, y) if len(rows) else {}
    return {
        "total_audited_matches": len(rows), "upcoming_predicted_matches": 0,
        "evaluation_scope": "monitoring_season" if season in LOCKED_SEASONS else "walk_forward_backtest",
        "prospective_matches_count": 0, "in_sample_backfill_matches_count": 0,
        "hit_rate_1x2_pct": _rate(sum(r["hit_1x2"] for r in rows), len(rows)), "hits_1x2": sum(r["hit_1x2"] for r in rows),
        "hit_rate_over_25_pct": _rate(sum(r["hit_over_25"] for r in rows), len(rows)), "hits_over_25": sum(r["hit_over_25"] for r in rows),
        "hit_rate_btts_pct": _rate(sum(r["hit_btts"] for r in rows), len(rows)), "hits_btts": sum(r["hit_btts"] for r in rows),
        "corner_mae": _mae([r["corner_error"] for r in rows]), "card_mae": _mae([r["card_error"] for r in rows]),
        "high_confidence_count": len(high), "high_confidence_hit_rate": _rate(sum(r["hit_1x2"] for r in high), len(high)),
        "balanced_count": sum(r["is_balanced"] for r in rows), "value_bets_count": 0,
        "log_loss": report.get("log_loss"), "rps": report.get("rps"),
    }


def _gameweeks(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for gw in sorted({r["gameweek"] for r in rows}):
        part = [r for r in rows if r["gameweek"] == gw]
        out.append({
            "gameweek": gw, "label": f"Hafta {gw}", "matches_count": len(part), "upcoming_count": 0,
            "hit_rate_1x2_pct": _rate(sum(r["hit_1x2"] for r in part), len(part)), "hit_rate_over_25_pct": _rate(sum(r["hit_over_25"] for r in part), len(part)),
            "hit_rate_btts_pct": _rate(sum(r["hit_btts"] for r in part), len(part)),
            "corner_mae": _mae([r["corner_error"] for r in part]), "card_mae": _mae([r["card_error"] for r in part]),
        })
    return out


def _benchmark(report: Dict[str, Any], season: str) -> Optional[Dict[str, Any]]:
    scores = report.get("per_season", {}).get(season)
    if not scores:
        return None
    protocol = report["protocol"]
    role = "monitor" if season in protocol["locked_monitoring"] else "hold_out" if season == protocol["outer_seasons"][-1] else "walk_forward"
    return {"role": role, "protocol": protocol, "scores": scores, "serving": report["decision"]["serving"]}
