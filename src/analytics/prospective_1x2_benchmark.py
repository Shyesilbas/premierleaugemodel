#!/usr/bin/env python3
"""Save pre-kickoff 1X2 forecasts and score them after matches are completed.

Run ``python -m src.analytics.prospective_1x2_benchmark snapshot`` periodically
while the API's local fixture/data snapshot is current. Each forecast is kept in
an append-only JSONL log. ``score`` uses the latest saved forecast made before
kickoff for each completed match, grouped by production-artifact fingerprint.

``--competition`` picks the league (default ``premier_league``). A league fed by TheStatsAPI (``la_liga``) keeps its own
log in ``data/competitions/<key>/processed/``, takes its forecasts from the same function that serves the match page
(``compute_league_prediction``), reads results from ``data/football.db`` and writes ``prospective_1x2_scorecard_<key>.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from src.models.eval_utils import multiclass_report


from dataclasses import dataclass

from src.config import DEFAULT_COMPETITION, FEATURES_PATH, MATCHES_SUMMARY_PATH as MATCHES_PATH, MODELS_DIR, PROCESSED_DIR, REPORTS_DIR, competition_paths, display_path

MODEL_PATH = MODELS_DIR / "outcome_models_v1.joblib"
GOALS_MODEL_PATH = MODELS_DIR / "goals_models_v1.joblib"
FORECAST_LOG = PROCESSED_DIR / "1x2_forecast_log.jsonl"
SCORECARD_PATH = REPORTS_DIR / "prospective_1x2_scorecard.json"
logger = logging.getLogger("prospective_1x2_benchmark")
GOAL_MARKETS = ("over_1.5", "over_2.5", "over_3.5", "btts")


@dataclass(frozen=True)
class Targets:
    """Files one competition's forecasts are read from and written to."""

    key: str
    model: Path
    goals_model: Path
    forecast_log: Path
    scorecard: Path


def targets(competition: str = DEFAULT_COMPETITION) -> Targets:
    if competition == DEFAULT_COMPETITION:
        return Targets(competition, MODEL_PATH, GOALS_MODEL_PATH, FORECAST_LOG, SCORECARD_PATH)
    paths = competition_paths(competition)
    return Targets(competition, paths.models / "outcome_models_v1.joblib", paths.models / "goals_models_v1.joblib",
                   paths.processed / "1x2_forecast_log.jsonl", REPORTS_DIR / f"prospective_1x2_scorecard_{competition}.json")


def _artifact_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_forecast_log(path: Path = FORECAST_LOG) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}") from exc
    return rows


def _snapshot_league(horizon_days: int, target: Targets) -> int:
    """League snapshot: the saved probabilities are exactly what the match page serves (``compute_league_prediction``)."""
    from src.api.league_prediction import artifact_for, compute_league_prediction, _stamp, _table
    from src.competitions.registry import get_competition

    comp = get_competition(target.key)
    artifact = artifact_for(comp.key)
    if artifact is None or not target.model.exists():
        raise FileNotFoundError(f"No production artifact for {comp.key}: {target.model}")
    goals_path = target.goals_model
    rates = (joblib.load(goals_path) if goals_path.exists() else artifact).get("base_rates", {})  # the file whose model serves the goal markets
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=horizon_days)
    artifact_hash = _artifact_fingerprint(target.model)
    goal_hash = _artifact_fingerprint(goals_path) if goals_path.exists() else artifact_hash
    saved_today = {(str(r.get("match_id")), r.get("artifact_sha256"), r.get("goal_artifact_sha256"), str(r.get("prediction_made_at_utc", ""))[:10])
                   for r in _read_forecast_log(target.forecast_log)}
    table = _table(comp.id, _stamp())
    kickoff = pd.to_datetime(table["kickoff"]).dt.tz_localize("UTC")
    upcoming = table.loc[table["home_score"].isna() & (kickoff > pd.Timestamp(now)) & (kickoff <= pd.Timestamp(horizon))].assign(_kickoff_utc=kickoff).sort_values("_kickoff_utc")
    new_rows: List[Dict[str, Any]] = []
    for _, fixture in upcoming.iterrows():
        match_id = int(fixture["match_id"])
        if (str(match_id), artifact_hash, goal_hash, now.date().isoformat()) in saved_today:
            continue
        try:
            result = compute_league_prediction(int(fixture["home_id"]), int(fixture["away_id"]), match_id, comp.key)
            outcome = result["outcome"]
            probabilities = np.asarray([float(outcome["home_win_pct"]), float(outcome["draw_pct"]), float(outcome["away_win_pct"])]) / 100.0
            if not np.isfinite(probabilities).all() or (probabilities < 0).any() or probabilities.sum() <= 0:
                raise ValueError("invalid 1X2 probabilities")
            probabilities /= probabilities.sum()
            goals = result["goals"]
            served = {"over_1.5": (goals["lines"]["1.5"]["over_pct"], goals["lines"]["1.5"]["source"], "over_15"),
                      "over_2.5": (goals["lines"]["2.5"]["over_pct"], goals["lines"]["2.5"]["source"], "over_25"),
                      "over_3.5": (goals["lines"]["3.5"]["over_pct"], goals["lines"]["3.5"]["source"], "over_35"),
                      "btts": (goals["btts_pct"], goals["btts_source"], "btts")}
            goal_markets = {market: {"probability": round(pct / 100.0, 6), "source": "baseline" if source == "baseline" else "model",
                                     "baseline_probability": round(float(rates[key]), 6) if key in rates else None}
                            for market, (pct, source, key) in served.items()}
            new_rows.append({
                "match_id": match_id, "season": str(fixture["season"]), "home_id": int(fixture["home_id"]), "away_id": int(fixture["away_id"]),
                "home_name": str(fixture.get("home_name", "")), "away_name": str(fixture.get("away_name", "")),
                "kickoff_utc": fixture["_kickoff_utc"].isoformat(), "prediction_made_at_utc": datetime.now(timezone.utc).isoformat(),
                "artifact_sha256": artifact_hash, "goal_artifact_sha256": goal_hash, "class_order": ["home", "draw", "away"],
                "probabilities": [round(float(v), 6) for v in probabilities], "goal_markets": goal_markets,
                "model_skill": result.get("model_skill"),
            })
        except Exception:
            logger.exception("Could not save forecast for match_id=%s", match_id)
    if new_rows:
        target.forecast_log.parent.mkdir(parents=True, exist_ok=True)
        with target.forecast_log.open("a", encoding="utf-8") as stream:
            for row in new_rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Saved {len(new_rows)} pre-kickoff forecasts within {horizon_days} days; log: {target.forecast_log}; artifact: {artifact_hash[:12]}")
    return len(new_rows)


def snapshot(horizon_days: int = 14, competition: str = DEFAULT_COMPETITION) -> int:
    """Append current production probabilities for upcoming fixtures."""
    if horizon_days < 1:
        raise ValueError("horizon-days must be positive")
    if competition != DEFAULT_COMPETITION:
        return _snapshot_league(horizon_days, targets(competition))
    if not FEATURES_PATH.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError("Features or production 1X2 artifact is missing")

    # Use the same live prediction path as the API so the saved forecast includes its feature
    # construction and production calibrator. state and routes.predict need no FastAPI app.
    from src.api import state
    from src.api.routes.predict import predict_match

    df_features, goals_artifact = state.df_features, state.goals_artifact

    if df_features.empty:
        raise ValueError("API loaded an empty feature dataset")
    required = {"match_id", "season", "home_id", "away_id", "is_played", "kickoff_millis"}
    missing = required.difference(df_features.columns)
    if missing:
        raise KeyError(f"Feature dataset lacks required forecast columns: {sorted(missing)}")

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=horizon_days)
    artifact_hash = _artifact_fingerprint(MODEL_PATH)
    goals_artifact_hash = (
        _artifact_fingerprint(GOALS_MODEL_PATH) if GOALS_MODEL_PATH.exists() else None
    )
    existing = _read_forecast_log()
    already_saved_today = {
        (
            str(row.get("match_id")),
            row.get("artifact_sha256"),
            row.get("goal_artifact_sha256"),
            str(row.get("prediction_made_at_utc", ""))[:10],
        )
        for row in existing
    }

    upcoming = df_features.loc[~df_features["is_played"].fillna(False).astype(bool)].copy()
    upcoming["_kickoff_utc"] = pd.to_datetime(
        pd.to_numeric(upcoming["kickoff_millis"], errors="coerce"), unit="ms", utc=True
    )
    upcoming = upcoming.loc[
        upcoming["_kickoff_utc"].notna()
        & (upcoming["_kickoff_utc"] > pd.Timestamp(now))
        & (upcoming["_kickoff_utc"] <= pd.Timestamp(horizon))
    ].sort_values("_kickoff_utc")

    new_rows: List[Dict[str, Any]] = []
    for _, fixture in upcoming.iterrows():
        match_id = int(fixture["match_id"])
        daily_key = (
            str(match_id), artifact_hash, goals_artifact_hash, now.date().isoformat()
        )
        if daily_key in already_saved_today:
            continue
        try:
            result = predict_match(
                home_id=int(fixture["home_id"]),
                away_id=int(fixture["away_id"]),
                season=str(fixture["season"]),
            )
            outcome = result["outcome"]
            probabilities = np.asarray([
                float(outcome["home_win_pct"]),
                float(outcome["draw_pct"]),
                float(outcome["away_win_pct"]),
            ]) / 100.0
            if not np.isfinite(probabilities).all() or (probabilities < 0).any() or probabilities.sum() <= 0:
                raise ValueError("API returned invalid 1X2 probabilities")
            probabilities /= probabilities.sum()
            goal_markets: Dict[str, Dict[str, Any]] = {}
            goals = result.get("goals", {})
            base_rates = goals_artifact.get("base_rates", {}) if goals_artifact else {}
            if goals_artifact_hash and isinstance(goals, dict):
                for market in GOAL_MARKETS:
                    if market == "btts":
                        raw_probability = goals.get("btts_pct")
                        raw_source = goals.get("btts_source", "model_matrix")
                    else:
                        market_result = goals.get(market)
                        if not isinstance(market_result, dict):
                            continue
                        raw_probability = market_result.get("pct")
                        raw_source = market_result.get("source", "model")
                    if raw_probability is None:
                        continue
                    probability = float(raw_probability) / 100.0
                    if not np.isfinite(probability) or not 0.0 <= probability <= 1.0:
                        raise ValueError(f"API returned invalid {market} probability")
                    source = "baseline" if raw_source == "baseline" else "model"
                    baseline_probability = None
                    # Baseline probabilities are captured with each forecast so
                    # future scoring never estimates them from held-out results.
                    baseline_probability = base_rates.get(market)
                    goal_markets[market] = {
                        "probability": round(probability, 6),
                        "source": source,
                        "baseline_probability": (
                            round(float(baseline_probability), 6)
                            if baseline_probability is not None else None
                        ),
                    }
            forecasted_at = datetime.now(timezone.utc)
            row = {
                "match_id": match_id,
                "season": str(fixture["season"]),
                "home_id": int(fixture["home_id"]),
                "away_id": int(fixture["away_id"]),
                "home_name": str(fixture.get("home_name", "")),
                "away_name": str(fixture.get("away_name", "")),
                "kickoff_utc": fixture["_kickoff_utc"].isoformat(),
                "prediction_made_at_utc": forecasted_at.isoformat(),
                "artifact_sha256": artifact_hash,
                "class_order": ["home", "draw", "away"],
                "probabilities": [round(float(value), 6) for value in probabilities],
            }
            if goals_artifact_hash:
                row["goal_artifact_sha256"] = goals_artifact_hash
                if goal_markets:
                    row["goal_markets"] = goal_markets
            new_rows.append(row)
            already_saved_today.add(daily_key)
        except Exception:
            logger.exception("Could not save forecast for match_id=%s", match_id)

    if new_rows:
        FORECAST_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FORECAST_LOG.open("a", encoding="utf-8") as stream:
            for row in new_rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"Saved {len(new_rows)} pre-kickoff forecasts within {horizon_days} days; "
        f"log: {FORECAST_LOG}; artifact: {artifact_hash[:12]}"
    )
    return len(new_rows)


def _league_results(key: str) -> pd.DataFrame:
    from src.competitions.registry import get_competition
    from src.db.database import get_db

    conn = get_db()
    try:
        return pd.read_sql_query("SELECT match_id, home_score, away_score FROM matches WHERE competition_id = ? AND status = 'COMPLETED'",
                                 conn, params=(get_competition(key).id,))
    finally:
        conn.close()


def score(competition: str = DEFAULT_COMPETITION) -> Dict[str, Any]:
    """Score the latest pre-kickoff forecast per completed match and artifact."""
    target = targets(competition)
    scorecard_path = target.scorecard
    if competition == DEFAULT_COMPETITION and not MATCHES_PATH.exists():
        raise FileNotFoundError(f"Completed-match dataset not found: {MATCHES_PATH}")
    forecasts = _read_forecast_log(target.forecast_log)
    if not forecasts:
        print("No saved forecasts yet. Run the snapshot command before fixtures kick off.")
        return {"groups": []}

    matches = pd.read_parquet(MATCHES_PATH) if competition == DEFAULT_COMPETITION else _league_results(competition)
    completed = matches.loc[matches["home_score"].notna() & matches["away_score"].notna()].copy()
    completed["match_id"] = completed["match_id"].astype(int)
    outcomes = completed.set_index("match_id")

    # Keep only forecasts made before kickoff. The independent latest maps avoid
    # counting a match twice when just one of the two production artifacts changes.
    latest_1x2: Dict[tuple[str, str], Dict[str, Any]] = {}
    latest_goals: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in forecasts:
        try:
            match_id = int(row["match_id"])
            if match_id not in outcomes.index:
                continue
            forecasted_at = pd.Timestamp(row["prediction_made_at_utc"])
            kickoff = pd.Timestamp(row["kickoff_utc"])
            if forecasted_at.tzinfo is None or kickoff.tzinfo is None or forecasted_at >= kickoff:
                continue
            outcome_key = (str(row["artifact_sha256"]), str(match_id))
            previous = latest_1x2.get(outcome_key)
            if previous is None or forecasted_at > pd.Timestamp(previous["prediction_made_at_utc"]):
                latest_1x2[outcome_key] = row
            if row.get("goal_markets"):
                goal_hash = str(row.get("goal_artifact_sha256", "legacy"))
                goal_key = (goal_hash, str(match_id))
                previous_goal = latest_goals.get(goal_key)
                if previous_goal is None or forecasted_at > pd.Timestamp(
                    previous_goal["prediction_made_at_utc"]
                ):
                    latest_goals[goal_key] = row
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed forecast record: %s", row)

    groups: Dict[str, List[tuple[Dict[str, Any], int]]] = {}
    for (artifact_hash, match_id), row in latest_1x2.items():
        match = outcomes.loc[int(match_id)]
        home_score, away_score = float(match["home_score"]), float(match["away_score"])
        actual = 0 if home_score > away_score else (1 if home_score == away_score else 2)
        groups.setdefault(artifact_hash, []).append((row, actual))

    results: List[Dict[str, Any]] = []
    for artifact_hash, rows in sorted(groups.items()):
        if not rows:
            continue
        y = np.asarray([actual for _, actual in rows], dtype=int)
        probabilities = np.asarray([row["probabilities"] for row, _ in rows], dtype=float)
        probabilities = np.clip(probabilities, 1e-9, 1.0)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        predicted = probabilities.argmax(axis=1)
        draw_actual = (y == 1).astype(int)
        report = multiclass_report(probabilities, y)
        results.append({
            "artifact_sha256": artifact_hash,
            "matches": int(len(y)),
            "log_loss": round(float(log_loss(y, probabilities, labels=[0, 1, 2])), 4),
            "multiclass_brier": round(float(np.mean(np.sum(
                (probabilities - np.eye(3)[y]) ** 2, axis=1
            ))), 4),
            "draw_brier": round(float(brier_score_loss(draw_actual, probabilities[:, 1])), 4),
            "draw_auc": round(float(roc_auc_score(draw_actual, probabilities[:, 1])), 4)
            if len(np.unique(draw_actual)) == 2 else None,
            "actual_draw_rate": round(float(draw_actual.mean()), 4),
            "mean_draw_probability": round(float(probabilities[:, 1].mean()), 4),
            "accuracy": round(float(accuracy_score(y, predicted)), 4),
            "predicted_draws": int((predicted == 1).sum()),
            "rps": report["rps"],
            "auc_by_class": report["auc_by_class"],
            "ece_by_class": report["ece_by_class"],
        })

    goal_groups: Dict[str, List[tuple[Dict[str, Any], Dict[str, int]]]] = {}
    for (goal_hash, match_id), row in latest_goals.items():
        match = outcomes.loc[int(match_id)]
        home_score, away_score = float(match["home_score"]), float(match["away_score"])
        actuals = {
            "over_1.5": int(home_score + away_score > 1.5),
            "over_2.5": int(home_score + away_score > 2.5),
            "over_3.5": int(home_score + away_score > 3.5),
            "btts": int(home_score > 0 and away_score > 0),
        }
        goal_groups.setdefault(goal_hash, []).append((row, actuals))

    goal_results: List[Dict[str, Any]] = []
    for goal_hash, rows in sorted(goal_groups.items()):
        market_results: Dict[str, Any] = {}
        for market in GOAL_MARKETS:
            observations = []
            for row, actuals in rows:
                entry = row.get("goal_markets", {}).get(market)
                if not isinstance(entry, dict):
                    continue
                try:
                    probability = float(entry["probability"])
                    baseline_probability = entry.get("baseline_probability")
                    if baseline_probability is not None:
                        baseline_probability = float(baseline_probability)
                    actual = actuals[market]
                    if (
                        not np.isfinite(probability) or not 0.0 <= probability <= 1.0
                        or (baseline_probability is not None and (
                            not np.isfinite(baseline_probability)
                            or not 0.0 <= baseline_probability <= 1.0
                        ))
                    ):
                        continue
                    observations.append((probability, baseline_probability, actual, entry.get("source", "model")))
                except (KeyError, TypeError, ValueError):
                    continue
            if not observations:
                continue
            model_p = np.clip(np.asarray([item[0] for item in observations]), 1e-9, 1.0 - 1e-9)
            actual = np.asarray([item[2] for item in observations], dtype=int)
            market_score: Dict[str, Any] = {
                "matches": int(len(actual)),
                "source_counts": {
                    source: sum(item[3] == source for item in observations)
                    for source in ("model", "baseline")
                },
                "log_loss": round(float(log_loss(actual, model_p, labels=[0, 1])), 4),
                "brier": round(float(brier_score_loss(actual, model_p)), 4),
            }
            baseline_rows = [item for item in observations if item[1] is not None]
            if baseline_rows:
                baseline_p = np.clip(
                    np.asarray([item[1] for item in baseline_rows]), 1e-9, 1.0 - 1e-9
                )
                baseline_y = np.asarray([item[2] for item in baseline_rows], dtype=int)
                comparable_model_p = np.clip(
                    np.asarray([item[0] for item in baseline_rows]), 1e-9, 1.0 - 1e-9
                )
                comparable_model_log_loss = float(
                    log_loss(baseline_y, comparable_model_p, labels=[0, 1])
                )
                comparable_model_brier = float(brier_score_loss(baseline_y, comparable_model_p))
                baseline_log_loss = float(log_loss(baseline_y, baseline_p, labels=[0, 1]))
                baseline_brier = float(brier_score_loss(baseline_y, baseline_p))
                market_score.update({
                    "baseline_matches": int(len(baseline_y)),
                    "baseline_log_loss": round(baseline_log_loss, 4),
                    "baseline_brier": round(baseline_brier, 4),
                    "comparable_model_log_loss": round(comparable_model_log_loss, 4),
                    "comparable_model_brier": round(comparable_model_brier, 4),
                    "log_loss_delta_vs_baseline": round(comparable_model_log_loss - baseline_log_loss, 4),
                    "brier_delta_vs_baseline": round(comparable_model_brier - baseline_brier, 4),
                })
            market_results[market] = market_score
        if market_results:
            goal_results.append({
                "goal_artifact_sha256": goal_hash,
                "markets": market_results,
            })

    scorecard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "immutable pre-kickoff API forecasts matched to completed local results",
        "groups": results,
        "goal_market_groups": goal_results,
    }
    scorecard_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard_path.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    if not results:
        print("No saved forecasts have completed yet; scorecard is empty.")
    for row in results:
        print(
            f"artifact={row['artifact_sha256'][:12]} n={row['matches']} "
            f"LL={row['log_loss']:.4f} Brier={row['multiclass_brier']:.4f} RPS={row['rps']:.4f} "
            f"draw_Brier={row['draw_brier']:.4f} draw_AUC={row['draw_auc']} "
            f"P(draw)={row['mean_draw_probability']:.3f}/{row['actual_draw_rate']:.3f}"
        )
    for group in goal_results:
        for market, metrics in group["markets"].items():
            baseline_delta = metrics.get("log_loss_delta_vs_baseline")
            print(
                f"goal_artifact={group['goal_artifact_sha256'][:12]} market={market} "
                f"n={metrics['matches']} LL={metrics['log_loss']:.4f} "
                f"Brier={metrics['brier']:.4f} baseline_LL_delta={baseline_delta}"
            )
    print(f"Scorecard: {display_path(scorecard_path)}")
    return scorecard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = commands.add_parser("snapshot", help="save upcoming API forecasts before kickoff")
    snapshot_parser.add_argument("--horizon-days", type=int, default=14)
    score_parser = commands.add_parser("score", help="score saved forecasts for matches with completed results")
    for sub in (snapshot_parser, score_parser):
        sub.add_argument("--competition", default=DEFAULT_COMPETITION, help="competition key from config/competitions.yaml (default: premier_league)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "snapshot":
        snapshot(args.horizon_days, args.competition)
    else:
        score(args.competition)


if __name__ == "__main__":
    main()
