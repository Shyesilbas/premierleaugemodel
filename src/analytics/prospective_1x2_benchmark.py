#!/usr/bin/env python3
"""Save pre-kickoff 1X2 forecasts and score them after matches are completed.

Run ``python -m src.analytics.prospective_1x2_benchmark snapshot`` periodically
while the API's local fixture/data snapshot is current. Each forecast is kept in
an append-only JSONL log. ``score`` uses the latest saved forecast made before
kickoff for each completed match, grouped by production-artifact fingerprint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features_matches_all.parquet"
MATCHES_PATH = PROJECT_ROOT / "data" / "processed" / "matches_summary_all.parquet"
MODEL_PATH = PROJECT_ROOT / "models" / "production" / "outcome_models_v1.joblib"
FORECAST_LOG = PROJECT_ROOT / "data" / "processed" / "1x2_forecast_log.jsonl"
SCORECARD_PATH = PROJECT_ROOT / "reports" / "prospective_1x2_scorecard.json"
logger = logging.getLogger("prospective_1x2_benchmark")


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


def snapshot(horizon_days: int = 14) -> int:
    """Append current production probabilities for upcoming fixtures."""
    if horizon_days < 1:
        raise ValueError("horizon-days must be positive")
    if not FEATURES_PATH.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError("Features or production 1X2 artifact is missing")

    # Import the same live prediction path used by the API so the saved forecast
    # includes the API's feature construction and production calibrator.
    from src.api.server import df_features, predict_match

    if df_features.empty:
        raise ValueError("API loaded an empty feature dataset")
    required = {"match_id", "season", "home_id", "away_id", "is_played", "kickoff_millis"}
    missing = required.difference(df_features.columns)
    if missing:
        raise KeyError(f"Feature dataset lacks required forecast columns: {sorted(missing)}")

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=horizon_days)
    artifact_hash = _artifact_fingerprint(MODEL_PATH)
    existing = _read_forecast_log()
    already_saved_today = {
        (str(row.get("match_id")), row.get("artifact_sha256"), str(row.get("prediction_made_at_utc", ""))[:10])
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
        daily_key = (str(match_id), artifact_hash, now.date().isoformat())
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
            forecasted_at = datetime.now(timezone.utc)
            new_rows.append({
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
            })
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
        f"log: {FORECAST_LOG.relative_to(PROJECT_ROOT)}; artifact: {artifact_hash[:12]}"
    )
    return len(new_rows)


def score() -> Dict[str, Any]:
    """Score the latest pre-kickoff forecast per completed match and artifact."""
    if not MATCHES_PATH.exists():
        raise FileNotFoundError(f"Completed-match dataset not found: {MATCHES_PATH}")
    forecasts = _read_forecast_log()
    if not forecasts:
        print("No saved forecasts yet. Run the snapshot command before fixtures kick off.")
        return {"groups": []}

    matches = pd.read_parquet(MATCHES_PATH)
    completed = matches.loc[matches["home_score"].notna() & matches["away_score"].notna()].copy()
    completed["match_id"] = completed["match_id"].astype(int)
    outcomes = completed.set_index("match_id")

    # Keep only forecasts made before the recorded kickoff, then use the latest
    # forecast for each match/model version (e.g. after fixture rescheduling).
    latest: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in forecasts:
        try:
            match_id = int(row["match_id"])
            if match_id not in outcomes.index:
                continue
            forecasted_at = pd.Timestamp(row["prediction_made_at_utc"])
            kickoff = pd.Timestamp(row["kickoff_utc"])
            if forecasted_at.tzinfo is None or kickoff.tzinfo is None or forecasted_at >= kickoff:
                continue
            key = (str(row["artifact_sha256"]), str(match_id))
            previous = latest.get(key)
            if previous is None or forecasted_at > pd.Timestamp(previous["prediction_made_at_utc"]):
                latest[key] = row
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed forecast record: %s", row)

    groups: Dict[str, List[tuple[Dict[str, Any], int]]] = {}
    for (artifact_hash, match_id), row in latest.items():
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
        })

    scorecard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "immutable pre-kickoff API forecasts matched to completed local results",
        "groups": results,
    }
    SCORECARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORECARD_PATH.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    if not results:
        print("No saved forecasts have completed yet; scorecard is empty.")
    for row in results:
        print(
            f"artifact={row['artifact_sha256'][:12]} n={row['matches']} "
            f"LL={row['log_loss']:.4f} Brier={row['multiclass_brier']:.4f} "
            f"draw_Brier={row['draw_brier']:.4f} draw_AUC={row['draw_auc']} "
            f"P(draw)={row['mean_draw_probability']:.3f}/{row['actual_draw_rate']:.3f}"
        )
    print(f"Scorecard: {SCORECARD_PATH.relative_to(PROJECT_ROOT)}")
    return scorecard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = commands.add_parser("snapshot", help="save upcoming API forecasts before kickoff")
    snapshot_parser.add_argument("--horizon-days", type=int, default=14)
    commands.add_parser("score", help="score saved forecasts for matches with completed results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "snapshot":
        snapshot(args.horizon_days)
    else:
        score()


if __name__ == "__main__":
    main()
