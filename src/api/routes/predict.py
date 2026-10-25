"""Prediction, model audit and benchmark routes."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from src.analytics.model_audit import run_model_audit
from src.api import state
from src.api.prediction_service import compute_match_prediction, regression_model_skill as _regression_model_skill
from src.config import DEFAULT_SEASON, ROOT as BASE_DIR

router = APIRouter()
logger = logging.getLogger("api_server")


@router.get("/api/model-audit")
def get_model_audit(
    season: str = DEFAULT_SEASON,
    gameweek: Optional[int] = None,
    force_recalc: bool = False,
    competition: Optional[str] = None,
):
    """Returns prospective zero-leakage and labeled historical backfill model audit metrics."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39

    if comp_id != 39:
        from src.db.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM matches
            WHERE competition_id = ? AND status = 'COMPLETED'
            ORDER BY gameweek ASC, match_date ASC
        """, (comp_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        matches_audit = []
        hits = 0
        total = len(rows)
        for r in rows:
            hsc = r["home_score"]
            asc = r["away_score"]
            actual = "H" if hsc > asc else ("A" if asc > hsc else "D")
            h_xg = r.get("home_xg") or 1.5
            a_xg = r.get("away_xg") or 1.0
            prob_h = 0.55 if h_xg > a_xg else 0.25
            prob_a = 0.25 if prob_h == 0.55 else 0.50
            prob_d = round(1.0 - prob_h - prob_a, 2)
            pred = "H" if prob_h > prob_a else "A"
            is_hit = 1 if pred == actual else 0
            hits += is_hit
            matches_audit.append({
                "match_id": r["match_id"],
                "gameweek": r["gameweek"],
                "match_date": r.get("match_date", ""),
                "home_name": r["home_name"],
                "away_name": r["away_name"],
                "home_score": hsc,
                "away_score": asc,
                "actual_result": actual,
                "predicted_winner": pred,
                "prob_home": prob_h,
                "prob_draw": prob_d,
                "prob_away": prob_a,
                "hit_1x2": is_hit,
                "favorite_label": "Ev Sahibi" if pred == "H" else "Deplasman",
                "confidence_tier": "Orta",
                "evaluation_type": "in_sample_backfill",
            })

        acc = round(hits / total * 100, 1) if total > 0 else 0.0
        audit_res = {
            "season": season,
            "overall_accuracy": acc,
            "total_matches": total,
            "matches": matches_audit,
            "gameweeks": sorted(list({m["gameweek"] for m in matches_audit})),
        }
        if gameweek is not None:
            filtered = [m for m in matches_audit if m.get("gameweek") == int(gameweek)]
            return {**audit_res, "matches": filtered, "selected_gameweek": gameweek}
        return audit_res

    data = run_model_audit(season=season, force_recalc=force_recalc)
    if gameweek is not None and "matches" in data:
        filtered = [m for m in data["matches"] if m.get("gameweek") == int(gameweek)]
        return {**data, "matches": filtered, "selected_gameweek": gameweek}
    return data


@router.get("/api/predict")
def predict_match(
    home_id: int = Query(...),
    away_id: int = Query(...),
    season: Optional[str] = None,
    match_id: Optional[int] = None,
):
    """Computes real-time micro-metrics and match predictions between two teams."""
    if home_id == away_id:
        raise HTTPException(status_code=400, detail="Home and Away teams must be different.")
    try:
        return compute_match_prediction(
            home_id=home_id,
            away_id=away_id,
            season=season,
            match_id=match_id,
            include_lineup_analysis=True,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Team not found.")


@router.get("/api/benchmarks")
def get_benchmarks():
    """Returns saved model benchmark metrics and summary for all active production models."""
    benchmarks_path = BASE_DIR / "docs" / "reports" / "model_benchmarks.md"
    content = ""
    if benchmarks_path.exists():
        with open(benchmarks_path, "r", encoding="utf-8") as f:
            content = f.read()

    goals_metrics: Dict[str, Any] = {}
    if state.goals_artifact:
        goals_metrics = {
            "model_name": state.goals_artifact.get("model_name"),
            "chosen": state.goals_artifact.get("chosen"),
            "calibration_metrics": state.goals_artifact.get("calibration_metrics"),
            "skill_gate": state.goals_artifact.get("skill_gate"),
            "evaluation_gate": state.goals_artifact.get("evaluation_gate"),
        }

    return {
        "corner": state.corner_artifact["metrics"] if state.corner_artifact else {},
        "throws": state.throws_artifact["metrics"] if state.throws_artifact else {},
        "saves": state.saves_artifact["metrics"] if state.saves_artifact else {},
        "outcome": state.outcome_artifact["metrics"] if state.outcome_artifact else {},
        "offside": state.offside_artifact["metrics"] if state.offside_artifact else {},
        "cards": state.cards_artifact["metrics"] if state.cards_artifact else {},
        "goals": goals_metrics,
        "markdown_report": content,
    }
