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
        if comp is not None and comp.has_model:
            from src.analytics.league_audit import build_league_audit

            payload = build_league_audit(comp.key, season, gameweek)
            return {**payload, "selected_gameweek": gameweek} if gameweek is not None else payload
        # Competitions without a prediction model show data only.
        return {"season": season, "competition_id": comp_id, "overall": {}, "gameweeks": [], "matches": [], "model_available": False}

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
    if home_id not in state.teams_dict or away_id not in state.teams_dict:
        from src.api.league_prediction import compute_league_prediction
        from src.competitions.registry import get_competition
        from src.db.database import get_db

        conn = get_db()
        try:
            row = (conn.execute("SELECT competition_id FROM matches WHERE match_id = ?", (match_id,)).fetchone() if match_id is not None else None) or conn.execute(
                "SELECT competition_id FROM matches WHERE home_id = ? AND away_id = ? ORDER BY match_date DESC LIMIT 1", (home_id, away_id)).fetchone()
        finally:
            conn.close()
        comp = get_competition(row["competition_id"]) if row else None
        if comp is None or not comp.has_model or comp.provider != "thestatsapi":
            raise HTTPException(status_code=404, detail="No prediction model exists for this competition.")
        try:
            return compute_league_prediction(home_id, away_id, match_id, comp.key)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
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
