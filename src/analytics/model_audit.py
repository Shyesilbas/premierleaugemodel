"""Model Performance & Prospective Audit Service for Premier League Model.

Audits pre-kickoff prospective predictions (from 1x2_forecast_log.jsonl) and explicitly
labeled historical backfill predictions against match results and closing market odds.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.api.prediction_service import (
    predict_1x2_probabilities,
    predict_count_market,
    predict_goals_markets,
)
from src.config import DEFAULT_SEASON, FEATURES_PATH, MODELS_DIR, PROCESSED_DIR, REPORTS_DIR
from src.db.database import get_db
from src.models.eval_utils import multiclass_report, paired_bootstrap_delta, per_match_log_loss

logger = logging.getLogger(__name__)

FORECAST_LOG_PATH = PROCESSED_DIR / "1x2_forecast_log.jsonl"
_RESULT_TO_IDX = {"home": 0, "draw": 1, "away": 2}


def init_audit_table(conn: sqlite3.Connection, season: Optional[str] = None) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_match_audit (
            match_id INTEGER PRIMARY KEY,
            season TEXT NOT NULL,
            gameweek INTEGER NOT NULL,
            match_date TEXT,
            home_name TEXT NOT NULL,
            away_name TEXT NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            actual_result TEXT NOT NULL,
            actual_corners REAL,
            actual_cards REAL,
            prob_home REAL NOT NULL,
            prob_draw REAL NOT NULL,
            prob_away REAL NOT NULL,
            favorite_label TEXT NOT NULL,
            confidence_tier TEXT NOT NULL,
            is_balanced INTEGER NOT NULL,
            predicted_winner TEXT NOT NULL,
            hit_1x2 INTEGER NOT NULL,
            expected_goals REAL NOT NULL,
            prob_over_25 REAL NOT NULL,
            hit_over_25 INTEGER NOT NULL,
            prob_btts REAL NOT NULL,
            hit_btts INTEGER NOT NULL,
            expected_corners REAL,
            corner_error REAL,
            expected_cards REAL,
            card_error REAL,
            market_home_odds REAL,
            market_draw_odds REAL,
            market_away_odds REAL,
            market_over_25_odds REAL,
            market_under_25_odds REAL,
            market_btts_odds REAL,
            market_btts_no_odds REAL,
            primary_bookmaker TEXT,
            highest_edge_side TEXT,
            edge_pct REAL,
            evaluation_type TEXT NOT NULL DEFAULT 'in_sample_backfill',
            audited_at_utc TEXT NOT NULL
        )
    """)
    for col_ddl in (
        "ALTER TABLE model_match_audit ADD COLUMN market_under_25_odds REAL",
        "ALTER TABLE model_match_audit ADD COLUMN market_btts_no_odds REAL",
        "ALTER TABLE model_match_audit ADD COLUMN evaluation_type TEXT NOT NULL DEFAULT 'in_sample_backfill'",
    ):
        try:
            conn.execute(col_ddl)
        except sqlite3.OperationalError:
            pass
    if season:
        conn.execute(
            "DELETE FROM model_match_audit WHERE season = ? AND COALESCE(evaluation_type, 'in_sample_backfill') != 'prospective'",
            (season,),
        )
    conn.commit()


def get_summary_json_path(season: str) -> Path:
    if season == DEFAULT_SEASON:
        return PROCESSED_DIR / "model_audit_summary.json"
    return PROCESSED_DIR / f"model_audit_summary_{season}.json"


def _load_prospective_forecasts(season: str) -> Dict[int, Dict[str, Any]]:
    """Load the latest valid pre-kickoff forecast per match_id from ``1x2_forecast_log.jsonl``."""
    if not FORECAST_LOG_PATH.exists():
        return {}
    by_match: Dict[int, Dict[str, Any]] = {}
    try:
        with FORECAST_LOG_PATH.open("r", encoding="utf-8") as stream:
            for line in stream:
                text = line.strip()
                if not text:
                    continue
                try:
                    entry = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if str(entry.get("season")) != str(season):
                    continue
                try:
                    mid = int(entry["match_id"])
                    kickoff = pd.Timestamp(entry["kickoff_utc"])
                    made_at = pd.Timestamp(entry["prediction_made_at_utc"])
                except Exception:
                    continue
                if made_at >= kickoff:
                    continue
                probs = entry.get("probabilities")
                if not isinstance(probs, list) or len(probs) != 3:
                    continue
                prev = by_match.get(mid)
                if prev is None or pd.Timestamp(prev["prediction_made_at_utc"]) <= made_at:
                    by_match[mid] = entry
    except Exception as exc:
        logger.warning("Could not read prospective forecast log: %s", exc)
    return by_match


def _file_sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _match_prob_vector(item: Dict[str, Any], raw_probs: Optional[Dict[int, np.ndarray]] = None) -> Optional[np.ndarray]:
    if raw_probs is not None:
        vec = raw_probs.get(int(item["match_id"]))
        if vec is not None:
            arr = np.asarray(vec, dtype=float)
            s = float(arr.sum())
            if arr.shape == (3,) and np.isfinite(arr).all() and s > 0:
                return arr / s
    raw = np.array(
        [float(item.get("prob_home", 0.0)), float(item.get("prob_draw", 0.0)), float(item.get("prob_away", 0.0))],
        dtype=float,
    )
    total = float(raw.sum())
    if not np.isfinite(raw).all() or total <= 0:
        return None
    return raw / total


def _subset_prob_metrics(
    subset: List[Dict[str, Any]],
    raw_probs: Optional[Dict[int, np.ndarray]] = None,
) -> Dict[str, Optional[float]]:
    probs_list: List[np.ndarray] = []
    y_list: List[int] = []
    for item in subset:
        idx = _RESULT_TO_IDX.get(str(item.get("actual_result", "")))
        vec = _match_prob_vector(item, raw_probs)
        if idx is None or vec is None:
            continue
        probs_list.append(vec)
        y_list.append(idx)
    if not y_list:
        return {"log_loss": None, "brier": None, "rps": None}
    report = multiclass_report(np.vstack(probs_list), np.asarray(y_list, dtype=int))
    return {
        "log_loss": report["log_loss"],
        "brier": report["brier"],
        "rps": report["rps"],
    }


def _compute_subset_summary(
    subset: List[Dict[str, Any]],
    raw_probs: Optional[Dict[int, np.ndarray]] = None,
) -> Dict[str, Any]:
    total = len(subset)
    hits_1x2 = sum(1 for m in subset if m.get("hit_1x2"))
    hits_o25 = sum(1 for m in subset if m.get("hit_over_25"))
    hits_btts = sum(1 for m in subset if m.get("hit_btts"))
    c_errs = [m["corner_error"] for m in subset if m.get("corner_error") is not None]
    card_errs = [m["card_error"] for m in subset if m.get("card_error") is not None]
    high_m = [m for m in subset if m.get("confidence_tier") == "high"]
    high_hits = sum(1 for m in high_m if m.get("hit_1x2"))
    balanced_m = [m for m in subset if m.get("is_balanced")]
    val_bets = [m for m in subset if m.get("is_value_bet")]
    prob_metrics = _subset_prob_metrics(subset, raw_probs)
    home_wins = sum(1 for m in subset if m.get("actual_result") == "home")
    return {
        "matches_count": total,
        "hit_rate_1x2_pct": round(hits_1x2 / total * 100, 1) if total else 0.0,
        "hits_1x2": hits_1x2,
        "home_baseline_accuracy": round(home_wins / total * 100, 1) if total else 0.0,
        "log_loss": prob_metrics["log_loss"],
        "brier": prob_metrics["brier"],
        "rps": prob_metrics["rps"],
        "hit_rate_over_25_pct": round(hits_o25 / total * 100, 1) if total else 0.0,
        "hits_over_25": hits_o25,
        "hit_rate_btts_pct": round(hits_btts / total * 100, 1) if total else 0.0,
        "hits_btts": hits_btts,
        "corner_mae": round(float(np.mean(c_errs)), 2) if c_errs else 0.0,
        "card_mae": round(float(np.mean(card_errs)), 2) if card_errs else 0.0,
        "high_confidence_count": len(high_m),
        "high_confidence_hit_rate": round(high_hits / len(high_m) * 100, 1) if high_m else 0.0,
        "balanced_count": len(balanced_m),
        "value_bets_count": len(val_bets),
    }


def _compute_calibration_bands(played_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    bands = [
        (0.0, 40.0, "<%40"),
        (40.0, 50.0, "%40-50"),
        (50.0, 60.0, "%50-60"),
        (60.0, 70.0, "%60-70"),
        (70.0, 101.0, "%70+"),
    ]
    results: List[Dict[str, Any]] = []
    for low, high, label in bands:
        in_band = []
        for m in played_matches:
            conf = max(float(m.get("prob_home", 0.0)), float(m.get("prob_draw", 0.0)), float(m.get("prob_away", 0.0)))
            if low <= conf < high:
                in_band.append((conf, bool(m.get("hit_1x2"))))
        if not in_band:
            continue
        results.append({
            "label": label,
            "count": len(in_band),
            "avg_confidence": round(sum(c for c, _ in in_band) / len(in_band), 1),
            "actual_accuracy": round(sum(1 for _, h in in_band if h) / len(in_band) * 100.0, 1),
        })
    return results


def _compute_rolling_accuracy(played_matches: List[Dict[str, Any]], window: int = 20) -> List[Dict[str, Any]]:
    ordered = sorted(
        played_matches,
        key=lambda m: (int(m.get("gameweek") or 0), str(m.get("match_date") or ""), int(m["match_id"])),
    )
    series: List[Dict[str, Any]] = []
    cum_hits = 0
    cum_home = 0
    for idx, m in enumerate(ordered):
        if m.get("hit_1x2"):
            cum_hits += 1
        if m.get("actual_result") == "home":
            cum_home += 1
        n = idx + 1
        win_slice = ordered[max(0, idx + 1 - window) : idx + 1]
        win_hits = sum(1 for item in win_slice if item.get("hit_1x2"))
        win_home = sum(1 for item in win_slice if item.get("actual_result") == "home")
        if n >= 5 or n == len(ordered):
            series.append({
                "index": n,
                "gameweek": int(m.get("gameweek") or 0),
                "label": f"H{int(m.get('gameweek') or 0)}",
                "rolling_acc": round(win_hits / len(win_slice) * 100.0, 1),
                "cumulative_acc": round(cum_hits / n * 100.0, 1),
                "home_baseline_acc": round(cum_home / n * 100.0, 1),
                "rolling_home_baseline": round(win_home / len(win_slice) * 100.0, 1),
            })
    return series


def _format_bootstrap_verdict(delta_dict: Dict[str, Any]) -> Dict[str, Any]:
    ci_low = float(delta_dict["ci_low"])
    ci_high = float(delta_dict["ci_high"])
    if ci_high < 0.0:
        verdict = "better"
    elif ci_low > 0.0:
        verdict = "worse"
    else:
        verdict = "inconclusive"
    return {
        "mean_delta": round(float(delta_dict["mean_delta"]), 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "p_a_better": round(float(delta_dict["p_a_better"]), 3),
        "n": int(delta_dict["n"]),
        "verdict": verdict,
    }


def _compute_benchmark_suite(
    df_all: pd.DataFrame,
    season: str,
    played_matches: List[Dict[str, Any]],
    raw_probs: Dict[int, np.ndarray],
    eval_scope: str,
) -> Dict[str, Any]:
    pairs: List[tuple[Dict[str, Any], np.ndarray, int]] = []
    for m in played_matches:
        idx = _RESULT_TO_IDX.get(str(m.get("actual_result", "")))
        vec = _match_prob_vector(m, raw_probs)
        if idx is not None and vec is not None:
            pairs.append((m, vec, idx))
    if not pairs:
        return {}

    items = [p[0] for p in pairs]
    p_model = np.vstack([p[1] for p in pairs])
    y_true = np.asarray([p[2] for p in pairs], dtype=int)
    model_losses = per_match_log_loss(p_model, y_true)
    scores: Dict[str, Any] = {"model": multiclass_report(p_model, y_true)}
    verdicts: Dict[str, Any] = {}

    prior_mask = (df_all["season"].astype(str) < str(season)) & df_all["is_played"].astype(bool)
    prior_df = df_all.loc[prior_mask].copy()
    if len(prior_df) >= 20:
        y_prior = np.where(
            prior_df["home_score"] > prior_df["away_score"],
            0,
            np.where(prior_df["home_score"] < prior_df["away_score"], 2, 1),
        )
        counts = np.bincount(y_prior, minlength=3).astype(float)
        base_dist = (counts + 1.0) / (len(y_prior) + 3.0)
        p_base = np.tile(base_dist, (len(y_true), 1))
        scores["base_rate"] = multiclass_report(p_base, y_true)
        verdicts["model_vs_base_rate"] = _format_bootstrap_verdict(
            paired_bootstrap_delta(model_losses, per_match_log_loss(p_base, y_true), n_boot=1000, seed=42)
        )

        elo_cols = ["elo_diff", "elo_venue_diff"]
        if all(col in prior_df.columns for col in elo_cols) and len(np.unique(y_prior)) == 3:
            if prior_df[elo_cols].notna().any().any():
                try:
                    df_idx = df_all.drop_duplicates("match_id").set_index("match_id")
                    mids = [int(m["match_id"]) for m in items]
                    if all(mid in df_idx.index for mid in mids):
                        pipe = Pipeline([
                            ("imp", SimpleImputer(strategy="median")),
                            ("sc", StandardScaler()),
                            ("clf", LogisticRegression(C=1.0, max_iter=500)),
                        ])
                        pipe.fit(prior_df[elo_cols], y_prior)
                        p_elo = np.asarray(pipe.predict_proba(df_idx.loc[mids, elo_cols]), dtype=float)
                        p_elo = p_elo / np.clip(p_elo.sum(axis=1, keepdims=True), 1e-12, None)
                        scores["elo"] = multiclass_report(p_elo, y_true)
                        verdicts["model_vs_elo"] = _format_bootstrap_verdict(
                            paired_bootstrap_delta(model_losses, per_match_log_loss(p_elo, y_true), n_boot=1000, seed=42)
                        )
                except Exception as exc:
                    logger.warning("Could not compute Elo benchmark for %s: %s", season, exc)

    mkt_rows: List[np.ndarray] = []
    mkt_model_rows: List[np.ndarray] = []
    mkt_y: List[int] = []
    for item, vec, y_idx in pairs:
        ho, do, ao = item.get("market_home_odds"), item.get("market_draw_odds"), item.get("market_away_odds")
        if ho and do and ao and float(ho) > 1.0 and float(do) > 1.0 and float(ao) > 1.0:
            imp = np.array([1.0 / float(ho), 1.0 / float(do), 1.0 / float(ao)], dtype=float)
            imp_norm = imp / float(imp.sum())
            mkt_rows.append(imp_norm)
            mkt_model_rows.append(vec)
            mkt_y.append(y_idx)
    if len(mkt_y) >= 5:
        p_mkt = np.vstack(mkt_rows)
        p_m_sub = np.vstack(mkt_model_rows)
        y_mkt = np.asarray(mkt_y, dtype=int)
        scores["market"] = multiclass_report(p_mkt, y_mkt)
        scores["model_on_market"] = multiclass_report(p_m_sub, y_mkt)
        verdicts["model_vs_market"] = _format_bootstrap_verdict(
            paired_bootstrap_delta(
                per_match_log_loss(p_m_sub, y_mkt),
                per_match_log_loss(p_mkt, y_mkt),
                n_boot=1000,
                seed=42,
            )
        )

    return {
        "role": "prospective" if eval_scope == "prospective" else "diagnostic",
        "scope": eval_scope,
        "prior_matches_used": int(len(prior_df)),
        "scores": scores,
        "verdicts": verdicts,
    }


def _load_prospective_scorecard() -> Dict[str, Any]:
    active_outcome = _file_sha256(MODELS_DIR / "outcome_models_v1.joblib")
    active_goals = _file_sha256(MODELS_DIR / "goals_models_v1.joblib")
    payload: Dict[str, Any] = {
        "active_outcome_sha256": active_outcome[:12] if active_outcome else None,
        "active_goals_sha256": active_goals[:12] if active_goals else None,
        "generated_at_utc": None,
        "total_logged_entries": 0,
        "distinct_logged_matches": 0,
        "groups": [],
        "goal_market_groups": [],
    }
    if FORECAST_LOG_PATH.exists():
        try:
            seen_mids = set()
            entries = 0
            for raw in FORECAST_LOG_PATH.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                entries += 1
                try:
                    seen_mids.add(int(json.loads(raw)["match_id"]))
                except Exception:
                    pass
            payload["total_logged_entries"] = entries
            payload["distinct_logged_matches"] = len(seen_mids)
        except OSError:
            pass

    scorecard_path = REPORTS_DIR / "prospective_1x2_scorecard.json"
    if not scorecard_path.exists():
        return payload
    try:
        sc = json.loads(scorecard_path.read_text(encoding="utf-8"))
        payload["generated_at_utc"] = sc.get("generated_at_utc")
        payload["groups"] = [
            {
                "artifact_sha256": g.get("artifact_sha256", ""),
                "short_sha": str(g.get("artifact_sha256", ""))[:12],
                "is_active": bool(active_outcome and g.get("artifact_sha256") == active_outcome),
                "matches": g.get("matches", 0),
                "accuracy_pct": round(float(g.get("accuracy", 0.0)) * 100.0, 1),
                "log_loss": g.get("log_loss"),
                "multiclass_brier": g.get("multiclass_brier"),
                "rps": g.get("rps"),
                "actual_draw_rate": g.get("actual_draw_rate"),
                "mean_draw_probability": g.get("mean_draw_probability"),
            }
            for g in sc.get("groups", [])
        ]
        payload["goal_market_groups"] = [
            {
                "goal_artifact_sha256": g.get("goal_artifact_sha256", ""),
                "short_sha": str(g.get("goal_artifact_sha256", ""))[:12],
                "is_active": bool(active_goals and g.get("goal_artifact_sha256") == active_goals),
                "markets": g.get("markets", {}),
            }
            for g in sc.get("goal_market_groups", [])
        ]
    except Exception as exc:
        logger.warning("Could not read prospective scorecard: %s", exc)
    return payload


def _load_backtest_calibration() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "o25_reliability": None,
        "goal_outer_seasons": [],
        "x12_season_holdouts": [],
    }
    goal_eval_path = PROCESSED_DIR / "goal_model_outer_eval.json"
    if goal_eval_path.exists():
        try:
            g = json.loads(goal_eval_path.read_text(encoding="utf-8"))
            rel_map = g.get("pooled_o25_reliability") or {}
            rel = rel_map.get("blend_dc_feat") or next(iter(rel_map.values()), None)
            if isinstance(rel, dict):
                out["o25_reliability"] = {
                    "n": rel.get("n"),
                    "ece": round(float(rel.get("ece", 0.0)), 4),
                    "monotonic_adjacent_share": round(float(rel.get("monotonic_adjacent_share", 0.0)), 3),
                    "bins": [
                        {
                            "bin": b.get("bin"),
                            "n": b.get("n"),
                            "mean_predicted": round(float(b.get("mean_predicted", 0.0)), 4),
                            "observed_rate": round(float(b.get("observed_rate", 0.0)), 4),
                        }
                        for b in rel.get("bins", [])
                    ],
                }
            outer_rows = g.get("outer_season_results") or []
            o25_by_season: Dict[str, Dict[str, Any]] = {}
            for row in outer_rows:
                if row.get("target") != "over_2.5":
                    continue
                s = str(row.get("season", ""))
                entry = o25_by_season.setdefault(s, {"season": s, "n": row.get("n")})
                if row.get("model") == "prior":
                    entry["prior_log_loss"] = round(float(row.get("log_loss", 0.0)), 4)
                elif row.get("model") == "blend_dc_feat":
                    entry["blend_log_loss"] = round(float(row.get("log_loss", 0.0)), 4)
                    entry["delta_vs_prior"] = round(float(row.get("delta_vs_prior", 0.0)), 4)
                    entry["ci_low"] = round(float(row.get("ci_low", 0.0)), 4)
                    entry["ci_high"] = round(float(row.get("ci_high", 0.0)), 4)
                elif row.get("model") == "feat_alpha3":
                    entry["feat_log_loss"] = round(float(row.get("log_loss", 0.0)), 4)
            out["goal_outer_seasons"] = [o25_by_season[k] for k in sorted(o25_by_season.keys())]
        except Exception as exc:
            logger.warning("Could not read goal_model_outer_eval.json: %s", exc)

    cal_eval_path = PROCESSED_DIR / "1x2_calibration_drift_outer_eval.json"
    if cal_eval_path.exists():
        try:
            c = json.loads(cal_eval_path.read_text(encoding="utf-8"))
            out["x12_season_holdouts"] = [
                {
                    "season": str(sh.get("season", "")),
                    "partial_season": bool(sh.get("partial_season")),
                    "train_samples": sh.get("train_samples"),
                    "test_samples": sh.get("test_samples"),
                    "selected_model": sh.get("selected_model"),
                    "cv_log_loss": round(float(sh.get("cv_log_loss", 0.0)), 4) if sh.get("cv_log_loss") is not None else None,
                    "standard_log_loss": round(float(sh.get("standard_log_loss", 0.0)), 4) if sh.get("standard_log_loss") is not None else None,
                }
                for sh in c.get("season_holdouts", [])
            ]
        except Exception as exc:
            logger.warning("Could not read 1x2_calibration_drift_outer_eval.json: %s", exc)
    return out


def run_model_audit(season: str = DEFAULT_SEASON, force_recalc: bool = False) -> Dict[str, Any]:
    """Audit season predictions, distinguishing frozen pre-kickoff forecasts from historical backfill."""
    summary_path = get_summary_json_path(season)
    features_path = FEATURES_PATH
    log_mtime = FORECAST_LOG_PATH.stat().st_mtime if FORECAST_LOG_PATH.exists() else 0.0
    scorecard_path = REPORTS_DIR / "prospective_1x2_scorecard.json"
    scorecard_mtime = scorecard_path.stat().st_mtime if scorecard_path.exists() else 0.0
    cache_fresh = (
        summary_path.exists()
        and features_path.exists()
        and summary_path.stat().st_mtime >= max(features_path.stat().st_mtime, log_mtime, scorecard_mtime)
    )
    if not force_recalc and cache_fresh:
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if (
                    cached.get("season") == season
                    and len(cached.get("matches", [])) > 0
                    and "evaluation_scope" in cached.get("overall", {})
                    and "benchmark" in cached
                    and "calibration_bands" in cached
                    and "prospective_scorecard" in cached
                ):
                    return cached
        except Exception as e:
            logger.warning(f"Failed to read cached audit summary: {e}")

    if not features_path.exists():
        return {"error": "Features parquet file not found."}

    outcome_art = joblib.load(MODELS_DIR / "outcome_models_v1.joblib")
    goals_art = joblib.load(MODELS_DIR / "goals_models_v1.joblib")
    corner_art = joblib.load(MODELS_DIR / "corner_model_v1.joblib")
    cards_art = joblib.load(MODELS_DIR / "cards_model_v1.joblib")

    df_all = pd.read_parquet(features_path)
    matches_df = df_all[df_all["season"] == season].sort_values(
        ["gameweek", "match_date"]
    ).copy()

    played_gws = matches_df.loc[matches_df["is_played"], "gameweek"]
    cur_gw = played_gws.max() if not played_gws.empty else matches_df["gameweek"].min() - 1
    matches_df = matches_df[matches_df["is_played"] | matches_df["gameweek"].isin([cur_gw, cur_gw + 1])]

    if matches_df.empty:
        return {"season": season, "overall": {}, "gameweeks": {}, "matches": []}

    prospective_by_match = _load_prospective_forecasts(season)

    conn = get_db()
    try:
        init_audit_table(conn, season=season)

        existing_prospective: Dict[int, Dict[str, Any]] = {}
        for row_db in conn.execute(
            "SELECT * FROM model_match_audit WHERE season = ? AND evaluation_type = 'prospective'",
            (season,),
        ).fetchall():
            existing_prospective[int(row_db["match_id"])] = dict(row_db)

        odds_cursor = conn.execute("""
            SELECT match_id, bookmaker, home_last_seen, draw_last_seen, away_last_seen,
                   over_25_last_seen, under_25_last_seen, btts_yes_last_seen, btts_no_last_seen
            FROM external_match_odds
        """)
        odds_by_match: Dict[int, Dict[str, Any]] = {}
        for r in odds_cursor.fetchall():
            mid = int(r["match_id"])
            bm = r["bookmaker"]
            if mid not in odds_by_match:
                odds_by_match[mid] = {}
            odds_by_match[mid][bm] = dict(r)

        audited_matches = []
        raw_probs_by_match: Dict[int, np.ndarray] = {}
        gw_stats: Dict[int, Dict[str, Any]] = {}
        upcoming_gws: Dict[int, int] = {}
        audit_now_utc = datetime.now(timezone.utc).isoformat()
        active_outcome_sha = _file_sha256(MODELS_DIR / "outcome_models_v1.joblib")
        active_outcome_short = active_outcome_sha[:12] if active_outcome_sha else None

        for _, row in matches_df.iterrows():
            mid = int(row["match_id"])
            gw = int(row["gameweek"])
            h_name = str(row["home_name"])
            a_name = str(row["away_name"])
            m_date = str(row["match_date"])[:10] if pd.notnull(row["match_date"]) else ""

            played = bool(row["is_played"])
            if played:
                h_score = int(row["home_score"])
                a_score = int(row["away_score"])
                actual_res = "home" if h_score > a_score else ("away" if a_score > h_score else "draw")
            else:
                h_score = a_score = actual_res = None

            row_df = pd.DataFrame([row])
            p1_flat, _ = predict_1x2_probabilities(row_df, outcome_art)
            goals_extra, p_over25, _ = predict_goals_markets(row_df, p1_flat, goals_art, outcome_art)
            exp_tot_goals = float(goals_extra.get("expected_total_goals", 0.0))
            p_btts = float(goals_extra.get("btts_pct", 0.0))

            prospective_entry = prospective_by_match.get(mid)
            saved_prospective = existing_prospective.get(mid)
            match_artifact_sha = active_outcome_short
            if prospective_entry is not None:
                evaluation_type = "prospective"
                frozen_probs = prospective_entry["probabilities"]
                raw_probs_by_match[mid] = np.asarray(frozen_probs, dtype=float)
                entry_sha = str(prospective_entry.get("artifact_sha256") or "")
                match_artifact_sha = entry_sha[:12] if entry_sha else active_outcome_short
                p_home = round(float(frozen_probs[0]) * 100.0, 1)
                p_draw = round(float(frozen_probs[1]) * 100.0, 1)
                p_away = round(float(frozen_probs[2]) * 100.0, 1)
                g_markets = prospective_entry.get("goal_markets") or {}
                if "over_2.5" in g_markets and g_markets["over_2.5"].get("probability") is not None:
                    p_over25 = round(float(g_markets["over_2.5"]["probability"]) * 100.0, 1)
                if "btts" in g_markets and g_markets["btts"].get("probability") is not None:
                    p_btts = round(float(g_markets["btts"]["probability"]) * 100.0, 1)
            elif saved_prospective is not None and played:
                evaluation_type = "prospective"
                match_artifact_sha = None
                p_home = round(float(saved_prospective["prob_home"]), 1)
                p_draw = round(float(saved_prospective["prob_draw"]), 1)
                p_away = round(float(saved_prospective["prob_away"]), 1)
                p_over25 = round(float(saved_prospective["prob_over_25"]), 1)
                p_btts = round(float(saved_prospective["prob_btts"]), 1)
                exp_tot_goals = round(float(saved_prospective["expected_goals"]), 2)
                raw_probs_by_match[mid] = np.array([p_home / 100.0, p_draw / 100.0, p_away / 100.0], dtype=float)
            else:
                evaluation_type = "in_sample_backfill" if played else "upcoming"
                raw_probs_by_match[mid] = np.asarray(p1_flat, dtype=float)
                p_home = round(float(p1_flat[0] * 100.0), 1)
                p_draw = round(float(p1_flat[1] * 100.0), 1)
                p_away = round(float(p1_flat[2] * 100.0), 1)

            if p_home >= p_draw and p_home >= p_away:
                pred_winner = "home"
            elif p_away >= p_draw and p_away >= p_home:
                pred_winner = "away"
            else:
                pred_winner = "draw"

            max_p = max(p_home, p_draw, p_away)
            diff_ha = abs(p_home - p_away)
            is_balanced = bool(max_p < 40.0 or diff_ha < 5.0)

            if max_p >= 50.0:
                confidence_tier = "high"
                fav_name = h_name if pred_winner == "home" else (a_name if pred_winner == "away" else "Beraberlik")
                fav_label = f"{fav_name} (Net Favori)"
            elif is_balanced:
                confidence_tier = "balanced"
                fav_name = h_name if pred_winner == "home" else (a_name if pred_winner == "away" else "Beraberlik")
                fav_label = f"{fav_name} (Dengeli / Yakın)"
            else:
                confidence_tier = "medium"
                fav_name = h_name if pred_winner == "home" else (a_name if pred_winner == "away" else "Beraberlik")
                fav_label = f"{fav_name} Favori"

            hit_1x2 = bool(pred_winner == actual_res) if played else None

            btts_threshold = 50.0
            if played:
                hit_over25 = bool((p_over25 >= 50.0) == (h_score + a_score > 2.5))
                hit_btts = bool((p_btts >= btts_threshold) == (h_score > 0 and a_score > 0))
            else:
                hit_over25 = hit_btts = None

            # Corners & Cards via unified prediction_service (NaN imputation preserved)
            exp_corners_raw, _, _ = predict_count_market(
                row_df, corner_art, min_val=5.0, max_val=18.0, fallback_total=10.2
            )
            exp_corners = round(float(exp_corners_raw), 1)
            act_corners = float(row["total_corners"]) if played and pd.notnull(row.get("total_corners")) else None
            corner_err = round(abs(act_corners - exp_corners), 1) if act_corners is not None else None

            exp_cards_raw, _, _ = predict_count_market(
                row_df, cards_art, min_val=1.0, max_val=12.0, fallback_total=4.2
            )
            exp_cards = round(float(exp_cards_raw), 1)
            act_cards = float(row["total_cards"]) if played and pd.notnull(row.get("total_cards")) else None
            card_err = round(abs(act_cards - exp_cards), 1) if act_cards is not None else None

            # Market Odds (Bet365 / Pinnacle / Fallback)
            m_odds = odds_by_match.get(mid, {})
            bm_data = m_odds.get("Bet365") or m_odds.get("Pinnacle") or (next(iter(m_odds.values())) if m_odds else {})

            h_odds = bm_data.get("home_last_seen") or next((b.get("home_last_seen") for b in m_odds.values() if b.get("home_last_seen")), None)
            d_odds = bm_data.get("draw_last_seen") or next((b.get("draw_last_seen") for b in m_odds.values() if b.get("draw_last_seen")), None)
            a_odds = bm_data.get("away_last_seen") or next((b.get("away_last_seen") for b in m_odds.values() if b.get("away_last_seen")), None)
            o25_odds = bm_data.get("over_25_last_seen") or next((b.get("over_25_last_seen") for b in m_odds.values() if b.get("over_25_last_seen")), None)
            u25_odds = bm_data.get("under_25_last_seen") or next((b.get("under_25_last_seen") for b in m_odds.values() if b.get("under_25_last_seen")), None)
            btts_odds = bm_data.get("btts_yes_last_seen") or next((b.get("btts_yes_last_seen") for b in m_odds.values() if b.get("btts_yes_last_seen")), None)
            btts_no_odds = bm_data.get("btts_no_last_seen") or next((b.get("btts_no_last_seen") for b in m_odds.values() if b.get("btts_no_last_seen")), None)
            bm_name = bm_data.get("bookmaker", "Piyasa")

            edge_side = None
            best_edge = 0.0
            if h_odds and h_odds > 1.0:
                imp_h = (1.0 / h_odds) * 100.0
                diff = p_home - imp_h
                if diff > best_edge:
                    best_edge = diff
                    edge_side = "home"
            if a_odds and a_odds > 1.0:
                imp_a = (1.0 / a_odds) * 100.0
                diff = p_away - imp_a
                if diff > best_edge:
                    best_edge = diff
                    edge_side = "away"
            if d_odds and d_odds > 1.0:
                imp_d = (1.0 / d_odds) * 100.0
                diff = p_draw - imp_d
                if diff > best_edge:
                    best_edge = diff
                    edge_side = "draw"

            is_val_bet = bool(best_edge >= 5.0)

            h_id = int(row.get("home_id", 0)) if pd.notnull(row.get("home_id")) else None
            a_id = int(row.get("away_id", 0)) if pd.notnull(row.get("away_id")) else None

            item = {
                "match_id": mid,
                "gameweek": gw,
                "match_date": m_date,
                "home_id": h_id,
                "away_id": a_id,
                "home_name": h_name,
                "away_name": a_name,
                "status": "COMPLETED" if played else "UPCOMING",
                "is_played": played,
                "evaluation_type": evaluation_type,
                "artifact_sha256": match_artifact_sha,
                "score": f"{h_score} - {a_score}" if played else None,
                "home_score": h_score,
                "away_score": a_score,
                "actual_result": actual_res,
                "actual_corners": act_corners,
                "actual_cards": act_cards,
                "prob_home": p_home,
                "prob_draw": p_draw,
                "prob_away": p_away,
                "predicted_winner": pred_winner,
                "favorite_label": fav_label,
                "favorite_name": fav_name,
                "confidence_tier": confidence_tier,
                "is_balanced": is_balanced,
                "hit_1x2": hit_1x2,
                "expected_goals": exp_tot_goals,
                "prob_over_25": p_over25,
                "hit_over_25": hit_over25,
                "prob_btts": p_btts,
                "btts_threshold": btts_threshold,
                "hit_btts": hit_btts,
                "expected_corners": exp_corners,
                "corner_error": corner_err,
                "expected_cards": exp_cards,
                "card_error": card_err,
                "market_home_odds": h_odds,
                "market_draw_odds": d_odds,
                "market_away_odds": a_odds,
                "market_over_25_odds": o25_odds,
                "market_under_25_odds": u25_odds,
                "market_btts_odds": btts_odds,
                "market_btts_no_odds": btts_no_odds,
                "bookmaker": bm_name,
                "highest_edge_side": edge_side if best_edge >= 3.0 else None,
                "edge_pct": round(best_edge, 1) if best_edge >= 3.0 else 0.0,
                "is_value_bet": is_val_bet,
            }
            audited_matches.append(item)
            if not played:
                upcoming_gws[gw] = upcoming_gws.get(gw, 0) + 1
                continue

            if mid not in existing_prospective or evaluation_type == "prospective":
                conn.execute("""
                    INSERT OR REPLACE INTO model_match_audit (
                        match_id, season, gameweek, match_date, home_name, away_name,
                        home_score, away_score, actual_result, actual_corners, actual_cards,
                        prob_home, prob_draw, prob_away, favorite_label, confidence_tier, is_balanced,
                        predicted_winner, hit_1x2, expected_goals, prob_over_25, hit_over_25,
                        prob_btts, hit_btts, expected_corners, corner_error, expected_cards, card_error,
                        market_home_odds, market_draw_odds, market_away_odds, market_over_25_odds, market_under_25_odds,
                        market_btts_odds, market_btts_no_odds, primary_bookmaker, highest_edge_side, edge_pct,
                        evaluation_type, audited_at_utc
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?
                    )
                """, (
                    mid, season, gw, m_date, h_name, a_name,
                    h_score, a_score, actual_res, act_corners, act_cards,
                    p_home, p_draw, p_away, fav_label, confidence_tier, int(is_balanced),
                    pred_winner, int(hit_1x2), exp_tot_goals, p_over25, int(hit_over25),
                    p_btts, int(hit_btts), exp_corners, corner_err, exp_cards, card_err,
                    h_odds, d_odds, a_odds, o25_odds, u25_odds,
                    btts_odds, btts_no_odds, bm_name, edge_side if best_edge >= 3.0 else None, round(best_edge, 1) if best_edge >= 3.0 else 0.0,
                    evaluation_type, audit_now_utc,
                ))

            if gw not in gw_stats:
                gw_stats[gw] = {
                    "gameweek": gw,
                    "matches_count": 0,
                    "hits_1x2": 0,
                    "hits_over_25": 0,
                    "hits_btts": 0,
                    "corner_errors": [],
                    "card_errors": [],
                }
            gw_stats[gw]["matches_count"] += 1
            if hit_1x2:
                gw_stats[gw]["hits_1x2"] += 1
            if hit_over25:
                gw_stats[gw]["hits_over_25"] += 1
            if hit_btts:
                gw_stats[gw]["hits_btts"] += 1
            if corner_err is not None:
                gw_stats[gw]["corner_errors"].append(corner_err)
            if card_err is not None:
                gw_stats[gw]["card_errors"].append(card_err)

        conn.commit()
    finally:
        conn.close()

    gw_summary_list = []
    for g, s in sorted(gw_stats.items()):
        total_g = s["matches_count"]
        gw_summary_list.append({
            "gameweek": g,
            "matches_count": total_g,
            "upcoming_count": upcoming_gws.get(g, 0),
            "hit_rate_1x2_pct": round(s["hits_1x2"] / total_g * 100, 1),
            "hit_rate_over_25_pct": round(s["hits_over_25"] / total_g * 100, 1),
            "hit_rate_btts_pct": round(s["hits_btts"] / total_g * 100, 1),
            "corner_mae": round(float(np.mean(s["corner_errors"])), 2) if s["corner_errors"] else None,
            "card_mae": round(float(np.mean(s["card_errors"])), 2) if s["card_errors"] else None,
        })

    for g, n in sorted(upcoming_gws.items()):
        if g not in gw_stats:
            gw_summary_list.append({
                "gameweek": g, "matches_count": 0, "upcoming_count": n,
                "hit_rate_1x2_pct": None, "hit_rate_over_25_pct": None,
                "hit_rate_btts_pct": None, "corner_mae": None, "card_mae": None,
            })

    played_matches = [m for m in audited_matches if m["is_played"]]
    prospective_played = [m for m in played_matches if m.get("evaluation_type") == "prospective"]
    backfill_played = [m for m in played_matches if m.get("evaluation_type") == "in_sample_backfill"]

    combined_summary = _compute_subset_summary(played_matches, raw_probs_by_match)
    prospective_summary = _compute_subset_summary(prospective_played, raw_probs_by_match)
    backfill_summary = _compute_subset_summary(backfill_played, raw_probs_by_match)

    if prospective_played and not backfill_played:
        eval_scope = "prospective"
    elif backfill_played and not prospective_played:
        eval_scope = "in_sample_backfill"
    elif prospective_played and backfill_played:
        eval_scope = "hybrid"
    else:
        eval_scope = "upcoming_only"

    benchmark_suite = _compute_benchmark_suite(
        df_all=df_all,
        season=season,
        played_matches=played_matches,
        raw_probs=raw_probs_by_match,
        eval_scope=eval_scope,
    )
    calibration_bands = _compute_calibration_bands(played_matches)
    rolling_accuracy = _compute_rolling_accuracy(played_matches)
    prospective_scorecard = _load_prospective_scorecard()
    backtest_calibration = _load_backtest_calibration()

    total_m = len(played_matches)
    overall_metrics = {
        "total_audited_matches": total_m,
        "upcoming_predicted_matches": len(audited_matches) - total_m,
        "evaluation_scope": eval_scope,
        "prospective_matches_count": len(prospective_played),
        "in_sample_backfill_matches_count": len(backfill_played),
        "hit_rate_1x2_pct": combined_summary["hit_rate_1x2_pct"],
        "hits_1x2": combined_summary["hits_1x2"],
        "home_baseline_accuracy": combined_summary["home_baseline_accuracy"],
        "log_loss": combined_summary["log_loss"],
        "brier": combined_summary["brier"],
        "rps": combined_summary["rps"],
        "hit_rate_over_25_pct": combined_summary["hit_rate_over_25_pct"],
        "hits_over_25": combined_summary["hits_over_25"],
        "hit_rate_btts_pct": combined_summary["hit_rate_btts_pct"],
        "hits_btts": combined_summary["hits_btts"],
        "corner_mae": combined_summary["corner_mae"],
        "card_mae": combined_summary["card_mae"],
        "high_confidence_count": combined_summary["high_confidence_count"],
        "high_confidence_hit_rate": combined_summary["high_confidence_hit_rate"],
        "balanced_count": combined_summary["balanced_count"],
        "value_bets_count": combined_summary["value_bets_count"],
        "prospective_metrics": prospective_summary,
        "in_sample_backfill_metrics": backfill_summary,
    }

    result_payload = {
        "season": season,
        "overall": overall_metrics,
        "gameweeks": gw_summary_list,
        "matches": audited_matches,
        "benchmark": benchmark_suite,
        "calibration_bands": calibration_bands,
        "rolling_accuracy": rolling_accuracy,
        "prospective_scorecard": prospective_scorecard,
        "backtest_calibration": backtest_calibration,
        "generated_at_utc": audit_now_utc,
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    logger.info(
        "Model audit completed for %s: %d played matches (%d prospective, %d backfill), %s%% 1X2 hit rate.",
        season,
        total_m,
        len(prospective_played),
        len(backfill_played),
        overall_metrics["hit_rate_1x2_pct"],
    )
    return result_payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_model_audit(DEFAULT_SEASON, force_recalc=True)
