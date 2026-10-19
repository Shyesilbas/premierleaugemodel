"""Model Performance & Prospective Audit Service for Premier League Model.

Audits out-of-sample predictions vs real match results and closing market odds.
Evaluates calibration, decision thresholding, and market value edge.
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

from src.models.dixon_coles import align_to_outcome_probs, btts_prob, expected_goals, over_prob
from src.models.model_utils import blend_log, apply_probability_calibrator

logger = logging.getLogger(__name__)

from src.config import DATA_DIR, DB_PATH, MODELS_DIR, PROCESSED_DIR, ROOT as BASE_DIR

SUMMARY_JSON = PROCESSED_DIR / "model_audit_summary.json"


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
            audited_at_utc TEXT NOT NULL
        )
    """)
    if season:
        conn.execute("DELETE FROM model_match_audit WHERE season = ?", (season,))
    try:
        conn.execute("ALTER TABLE model_match_audit ADD COLUMN market_under_25_odds REAL")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE model_match_audit ADD COLUMN market_btts_no_odds REAL")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def get_summary_json_path(season: str) -> Path:
    if season == "2026_27":
        return DATA_DIR / "processed" / "model_audit_summary.json"
    return DATA_DIR / "processed" / f"model_audit_summary_{season}.json"


def run_model_audit(season: str = "2026_27", force_recalc: bool = False) -> Dict[str, Any]:
    """Generates zero-leakage predictions for completed matches in the specified season
    and evaluates performance against final match results and market odds.
    """
    summary_path = get_summary_json_path(season)
    if not force_recalc and summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("season") == season and len(cached.get("matches", [])) > 0:
                    return cached
        except Exception as e:
            logger.warning(f"Failed to read cached audit summary: {e}")

    features_path = DATA_DIR / "processed" / "features_matches_all.parquet"
    if not features_path.exists():
        return {"error": "Features parquet file not found."}

    # Load production artifacts
    outcome_art = joblib.load(MODELS_DIR / "outcome_models_v1.joblib")
    goals_art = joblib.load(MODELS_DIR / "goals_models_v1.joblib")
    corner_art = joblib.load(MODELS_DIR / "corner_model_v1.joblib")
    cards_art = joblib.load(MODELS_DIR / "cards_model_v1.joblib")

    df_all = pd.read_parquet(features_path)
    matches_df = df_all[(df_all["season"] == season) & (df_all["is_played"])].sort_values(
        ["gameweek", "match_date"]
    ).copy()

    if matches_df.empty:
        return {"season": season, "overall": {}, "gameweeks": {}, "matches": []}

    # Fetch stored odds
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_audit_table(conn, season=season)

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

    o_feats = outcome_art.get("feature_names_1x2", outcome_art["feature_names"])
    c_feats = corner_art["feature_names"]
    card_feats = cards_art.get("feature_cols", [])

    audited_matches = []
    gw_stats: Dict[int, Dict[str, Any]] = {}
    audit_now_utc = datetime.now(timezone.utc).isoformat()

    for _, row in matches_df.iterrows():
        mid = int(row["match_id"])
        gw = int(row["gameweek"])
        h_name = str(row["home_name"])
        a_name = str(row["away_name"])
        m_date = str(row["match_date"])[:10] if pd.notnull(row["match_date"]) else ""

        h_score = int(row["home_score"])
        a_score = int(row["away_score"])
        actual_res = "home" if h_score > a_score else ("away" if a_score > h_score else "draw")

        # 1X2 Prediction with Full Calibration
        X1 = pd.DataFrame([row]).reindex(columns=o_feats, fill_value=np.nan)
        p1 = outcome_art["model_1x2"].predict_proba(X1)
        if "model_dc" in outcome_art and outcome_art.get("metrics", {}).get("1x2_ensemble_production", {}).get("enabled", True):
            dc_p = outcome_art["model_dc"].predict_proba(pd.DataFrame([row]))
            w = outcome_art["ensemble_weight"]
            p1 = blend_log(p1, dc_p, w)
            calibrator_1x2 = outcome_art.get("calibrators", {}).get("1x2_ensemble")
        else:
            calibrator_1x2 = outcome_art.get("calibrators", {}).get("1x2")

        if calibrator_1x2:
            p1 = apply_probability_calibrator(p1, calibrator_1x2)

        p1_flat = p1[0]
        p_home = round(float(p1_flat[0] * 100), 1)
        p_draw = round(float(p1_flat[1] * 100), 1)
        p_away = round(float(p1_flat[2] * 100), 1)

        # Natural Argmax for prediction (Highest probability wins the pick)
        if p_home >= p_draw and p_home >= p_away:
            pred_winner = "home"
        elif p_away >= p_draw and p_away >= p_home:
            pred_winner = "away"
        else:
            pred_winner = "draw"

        # Confidence Tiering & Metadata (Labels & Filters without corrupting argmax)
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

        hit_1x2 = bool(pred_winner == actual_res)

        # Goals Prediction
        # Same scoring path as /api/predict: matrix aligned to the 1X2 model, then stored calibrators.
        mat = align_to_outcome_probs(goals_art["model"].predict_matrices(pd.DataFrame([row])), p1)
        lam_h, lam_a = expected_goals(mat)
        exp_tot_goals = round(float(lam_h[0] + lam_a[0]), 2)
        goal_calibrators = goals_art.get("calibrators", {})
        raw_o25, raw_btts = float(over_prob(mat, 2.5)[0]), float(btts_prob(mat)[0])
        if goal_calibrators.get("over_2.5"):
            raw_o25 = float(apply_probability_calibrator(np.array([[1.0 - raw_o25, raw_o25]]), goal_calibrators["over_2.5"])[0, 1])
        if goal_calibrators.get("btts"):
            raw_btts = float(apply_probability_calibrator(np.array([[1.0 - raw_btts, raw_btts]]), goal_calibrators["btts"])[0, 1])
        p_over25 = round(raw_o25 * 100, 1)
        p_btts = round(raw_btts * 100, 1)

        actual_tot_goals = h_score + a_score
        hit_over25 = bool((p_over25 >= 50.0) == (actual_tot_goals > 2.5))
        btts_threshold = 50.0
        hit_btts = bool((p_btts >= btts_threshold) == (h_score > 0 and a_score > 0))

        # Corners
        Xc = pd.DataFrame([row]).reindex(columns=c_feats, fill_value=np.nan)
        exp_corners = round(float(corner_art["model"].predict(Xc)[0]), 1)
        act_corners = float(row["total_corners"]) if pd.notnull(row.get("total_corners")) else None
        corner_err = round(abs(act_corners - exp_corners), 1) if act_corners is not None else None

        # Cards
        Xcard = pd.DataFrame([row]).reindex(columns=card_feats, fill_value=0.0)
        exp_cards = round(float(cards_art["model"].predict(Xcard)[0]), 1)
        act_cards = float(row["total_cards"]) if pd.notnull(row.get("total_cards")) else None
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

        # Edge calculation
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
            "status": "COMPLETED",
            "is_played": True,
            "score": f"{h_score} - {a_score}",
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

        # Insert to SQLite
        conn.execute("""
            INSERT OR REPLACE INTO model_match_audit (
                match_id, season, gameweek, match_date, home_name, away_name,
                home_score, away_score, actual_result, actual_corners, actual_cards,
                prob_home, prob_draw, prob_away, favorite_label, confidence_tier, is_balanced,
                predicted_winner, hit_1x2, expected_goals, prob_over_25, hit_over_25,
                prob_btts, hit_btts, expected_corners, corner_error, expected_cards, card_error,
                market_home_odds, market_draw_odds, market_away_odds, market_over_25_odds, market_under_25_odds,
                market_btts_odds, market_btts_no_odds, primary_bookmaker, highest_edge_side, edge_pct, audited_at_utc
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
        """, (
            mid, season, gw, m_date, h_name, a_name,
            h_score, a_score, actual_res, act_corners, act_cards,
            p_home, p_draw, p_away, fav_label, confidence_tier, int(is_balanced),
            pred_winner, int(hit_1x2), exp_tot_goals, p_over25, int(hit_over25),
            p_btts, int(hit_btts), exp_corners, corner_err, exp_cards, card_err,
            h_odds, d_odds, a_odds, o25_odds, u25_odds,
            btts_odds, btts_no_odds, bm_name, edge_side if best_edge >= 3.0 else None, round(best_edge, 1) if best_edge >= 3.0 else 0.0,
            audit_now_utc
        ))

        # Gameweek breakdown
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
    conn.close()

    # Gameweek summaries
    gw_summary_list = []
    for g, s in sorted(gw_stats.items()):
        total_g = s["matches_count"]
        gw_summary_list.append({
            "gameweek": g,
            "matches_count": total_g,
            "hit_rate_1x2_pct": round(s["hits_1x2"] / total_g * 100, 1),
            "hit_rate_over_25_pct": round(s["hits_over_25"] / total_g * 100, 1),
            "hit_rate_btts_pct": round(s["hits_btts"] / total_g * 100, 1),
            "corner_mae": round(float(np.mean(s["corner_errors"])), 2) if s["corner_errors"] else None,
            "card_mae": round(float(np.mean(s["card_errors"])), 2) if s["card_errors"] else None,
        })

    total_m = len(audited_matches)
    tot_hits_1x2 = sum(1 for m in audited_matches if m["hit_1x2"])
    tot_hits_o25 = sum(1 for m in audited_matches if m["hit_over_25"])
    tot_hits_btts = sum(1 for m in audited_matches if m["hit_btts"])
    all_c_errs = [m["corner_error"] for m in audited_matches if m["corner_error"] is not None]
    all_card_errs = [m["card_error"] for m in audited_matches if m["card_error"] is not None]

    # Tier statistics
    high_matches = [m for m in audited_matches if m["confidence_tier"] == "high"]
    high_hits = sum(1 for m in high_matches if m["hit_1x2"])
    balanced_matches = [m for m in audited_matches if m["is_balanced"]]
    val_bets = [m for m in audited_matches if m["is_value_bet"]]

    overall_metrics = {
        "total_audited_matches": total_m,
        "hit_rate_1x2_pct": round(tot_hits_1x2 / total_m * 100, 1) if total_m else 0,
        "hits_1x2": tot_hits_1x2,
        "hit_rate_over_25_pct": round(tot_hits_o25 / total_m * 100, 1) if total_m else 0,
        "hits_over_25": tot_hits_o25,
        "hit_rate_btts_pct": round(tot_hits_btts / total_m * 100, 1) if total_m else 0,
        "hits_btts": tot_hits_btts,
        "corner_mae": round(float(np.mean(all_c_errs)), 2) if all_c_errs else 0.0,
        "card_mae": round(float(np.mean(all_card_errs)), 2) if all_card_errs else 0.0,
        "high_confidence_count": len(high_matches),
        "high_confidence_hit_rate": round(high_hits / len(high_matches) * 100, 1) if high_matches else 0,
        "balanced_count": len(balanced_matches),
        "value_bets_count": len(val_bets),
    }

    result_payload = {
        "season": season,
        "overall": overall_metrics,
        "gameweeks": gw_summary_list,
        "matches": audited_matches,
    }

    # Save to JSON cache
    DATA_DIR.joinpath("processed").mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    logger.info(f"Audit completed: {total_m} matches processed and saved to SQLite & JSON.")
    return result_payload


if __name__ == "__main__":
    import sys
    season_arg = sys.argv[1] if len(sys.argv) > 1 else "2026_27"
    res = run_model_audit(season=season_arg, force_recalc=True)
    print("Zero-leakage audit updated successfully!")
    print(f"Overall metrics for {season_arg}:", res["overall"])
