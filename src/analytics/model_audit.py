"""Model Performance & Prospective Audit Service for Premier League Model.

Audits pre-kickoff prospective predictions (from 1x2_forecast_log.jsonl) and explicitly
labeled historical backfill predictions against match results and closing market odds.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from src.api.prediction_service import (
    predict_1x2_probabilities,
    predict_count_market,
    predict_goals_markets,
)
from src.config import DEFAULT_SEASON, FEATURES_PATH, MODELS_DIR, PROCESSED_DIR
from src.db.database import get_db

logger = logging.getLogger(__name__)

FORECAST_LOG_PATH = PROCESSED_DIR / "1x2_forecast_log.jsonl"


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


def _compute_subset_summary(subset: List[Dict[str, Any]]) -> Dict[str, Any]:
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
    return {
        "matches_count": total,
        "hit_rate_1x2_pct": round(hits_1x2 / total * 100, 1) if total else 0.0,
        "hits_1x2": hits_1x2,
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


def run_model_audit(season: str = DEFAULT_SEASON, force_recalc: bool = False) -> Dict[str, Any]:
    """Audit season predictions, distinguishing frozen pre-kickoff forecasts from historical backfill."""
    summary_path = get_summary_json_path(season)
    features_path = FEATURES_PATH
    log_mtime = FORECAST_LOG_PATH.stat().st_mtime if FORECAST_LOG_PATH.exists() else 0.0
    cache_fresh = (
        summary_path.exists()
        and features_path.exists()
        and summary_path.stat().st_mtime >= max(features_path.stat().st_mtime, log_mtime)
    )
    if not force_recalc and cache_fresh:
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if (
                    cached.get("season") == season
                    and len(cached.get("matches", [])) > 0
                    and "evaluation_scope" in cached.get("overall", {})
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
        gw_stats: Dict[int, Dict[str, Any]] = {}
        upcoming_gws: Dict[int, int] = {}
        audit_now_utc = datetime.now(timezone.utc).isoformat()

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
            if prospective_entry is not None:
                evaluation_type = "prospective"
                frozen_probs = prospective_entry["probabilities"]
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
                p_home = round(float(saved_prospective["prob_home"]), 1)
                p_draw = round(float(saved_prospective["prob_draw"]), 1)
                p_away = round(float(saved_prospective["prob_away"]), 1)
                p_over25 = round(float(saved_prospective["prob_over_25"]), 1)
                p_btts = round(float(saved_prospective["prob_btts"]), 1)
                exp_tot_goals = round(float(saved_prospective["expected_goals"]), 2)
            else:
                evaluation_type = "in_sample_backfill" if played else "upcoming"
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

    combined_summary = _compute_subset_summary(played_matches)
    prospective_summary = _compute_subset_summary(prospective_played)
    backfill_summary = _compute_subset_summary(backfill_played)

    if prospective_played and not backfill_played:
        eval_scope = "prospective"
    elif backfill_played and not prospective_played:
        eval_scope = "in_sample_backfill"
    elif prospective_played and backfill_played:
        eval_scope = "hybrid"
    else:
        eval_scope = "upcoming_only"

    total_m = len(played_matches)
    overall_metrics = {
        "total_audited_matches": total_m,
        "upcoming_predicted_matches": len(audited_matches) - total_m,
        "evaluation_scope": eval_scope,
        "prospective_matches_count": len(prospective_played),
        "in_sample_backfill_matches_count": len(backfill_played),
        "hit_rate_1x2_pct": combined_summary["hit_rate_1x2_pct"],
        "hits_1x2": combined_summary["hits_1x2"],
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
