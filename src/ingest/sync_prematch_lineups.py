#!/usr/bin/env python3
"""Fetch pre-match official starting XIs from PulseLive, update local match cache,
and compare model predictions (Last Match XI vs Confirmed Official XI) alongside
bookmaker closing/latest odds.

Usage examples:
  # Check today's / next 12h matches:
  python3 -m src.ingest.sync_prematch_lineups

  # Check a specific team's upcoming match:
  python3 -m src.ingest.sync_prematch_lineups --team Everton

  # Check a specific match ID:
  python3 -m src.ingest.sync_prematch_lineups --match-id 128986

  # Check all upcoming matches in Gameweek 7:
  python3 -m src.ingest.sync_prematch_lineups --gameweek 7
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src" / "ingest") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "ingest"))

from src.ingest.fetch_season_data import build_session, fetch_match_details
from src.analytics.player_ratings import (
    calculate_single_match_score,
    get_all_player_logs,
    get_all_players_registry,
    get_match_bookings_map,
)
from src.features.build_features import _aggregate_xi_ratings, _compute_pre_match_player_rating
from src.models.dixon_coles import align_to_outcome_probs, btts_prob, expected_goals, over_prob
from src.models.model_utils import apply_probability_calibrator, blend_log, safe_feature_frame

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "premier_league.db"
FEATURES_PATH = DATA_DIR / "processed" / "features_matches_all.parquet"
MATCHES_RAW_DIR = DATA_DIR / "raw" / "matches"
OUTCOME_MODEL_PATH = PROJECT_ROOT / "models" / "production" / "outcome_models_v1.joblib"
GOALS_MODEL_PATH = PROJECT_ROOT / "models" / "production" / "goals_models_v1.joblib"


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def extract_team_lists(details: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """Returns team_id -> {'formation': str, 'lineup': list, 'subs': list} when official XI is present."""
    result: Dict[int, Dict[str, Any]] = {}
    teams_info = details.get("teams") or []
    for idx, tl in enumerate(details.get("teamLists") or []):
        if not tl or not isinstance(tl, dict):
            continue
        t_id = tl.get("teamId")
        if not t_id and idx < len(teams_info):
            t_id = (teams_info[idx].get("team") or {}).get("id")
        if not t_id:
            continue
        lineup = tl.get("lineup") or []
        subs = tl.get("substitutes") or []
        formation = (tl.get("formation") or {}).get("label") or "-"
        if len(lineup) >= 7:
            result[int(t_id)] = {
                "formation": str(formation),
                "lineup": lineup,
                "subs": subs,
            }
    return result


def build_player_history_and_last_xi(
    df_features: pd.DataFrame,
) -> Tuple[
    Dict[int, List[Tuple[str, float, float, float]]],
    Dict[int, Set[int]],
    Dict[int, Tuple[float, float, float]],
]:
    """Replays played matches chronologically to build exact point-in-time player history and each team's last played XI."""
    logs_by_player = get_all_player_logs()
    reg = get_all_players_registry()
    bmap = get_match_bookings_map()

    match_starters: Dict[int, Dict[int, List[Tuple[int, str]]]] = {}
    match_scores: Dict[int, Dict[int, List[Tuple[int, str, float, float, float]]]] = {}

    for pid_str, plogs in logs_by_player.items():
        try:
            pid = int(pid_str)
        except (ValueError, TypeError):
            continue
        pos = str(reg.get(pid, {}).get("position", "M"))
        for l in plogs:
            mid = int(l.get("match_id") or 0)
            tid = int(l.get("team_id") or 0)
            if not mid or not tid:
                continue
            if l.get("started"):
                match_starters.setdefault(mid, {}).setdefault(tid, []).append((pid, pos))
            sc = calculate_single_match_score(l, pos, bmap, pid)
            if sc is not None:
                match_scores.setdefault(mid, {}).setdefault(tid, []).append(
                    (pid, pos, float(sc["overall"]), float(sc["attack"]), float(sc["defense"]))
                )

    played = df_features[df_features["is_played"].fillna(False).astype(bool)].copy()
    played = played.sort_values(["kickoff_millis", "match_id"], kind="mergesort")

    player_history: Dict[int, List[Tuple[str, float, float, float]]] = {}
    last_xi_pids: Dict[int, Set[int]] = {}
    last_xi_ratings: Dict[int, Tuple[float, float, float]] = {}

    for row in played.itertuples(index=False):
        mid = int(row.match_id)
        s_str = str(row.season)
        for tid in (int(row.home_id), int(row.away_id)):
            starters = match_starters.get(mid, {}).get(tid, [])
            if len(starters) >= 7:
                last_xi_ratings[tid] = _aggregate_xi_ratings(starters, player_history, s_str)
                last_xi_pids[tid] = {pid for pid, _ in starters}
        for tid in (int(row.home_id), int(row.away_id)):
            for pid, _pos, sc_ov, sc_at, sc_df in match_scores.get(mid, {}).get(tid, []):
                player_history.setdefault(pid, []).append((s_str, sc_ov, sc_at, sc_df))

    return player_history, last_xi_pids, last_xi_ratings


def get_target_fixtures(
    df_features: pd.DataFrame,
    season: str = "2026_27",
    match_id: Optional[int] = None,
    team_query: Optional[str] = None,
    gameweek: Optional[int] = None,
    hours_ahead: float = 12.0,
) -> pd.DataFrame:
    upcoming = df_features[
        (df_features["season"].astype(str) == season)
        & (~df_features["is_played"].fillna(False).astype(bool))
    ].copy()
    if upcoming.empty:
        return upcoming

    upcoming["_kickoff_utc"] = pd.to_datetime(
        pd.to_numeric(upcoming["kickoff_millis"], errors="coerce"), unit="ms", utc=True
    )

    if match_id is not None:
        return upcoming[upcoming["match_id"].astype(int) == int(match_id)].sort_values("_kickoff_utc")

    if gameweek is not None:
        upcoming = upcoming[upcoming["gameweek"].astype(int) == int(gameweek)]

    if team_query:
        q = team_query.strip().lower()
        mask = (
            upcoming["home_name"].astype(str).str.lower().str.contains(q, na=False)
            | upcoming["away_name"].astype(str).str.lower().str.contains(q, na=False)
        )
        upcoming = upcoming[mask]
        if gameweek is None and len(upcoming) > 1:
            upcoming = upcoming.sort_values("_kickoff_utc").iloc[:1]
        return upcoming.sort_values("_kickoff_utc")

    if gameweek is not None:
        return upcoming.sort_values("_kickoff_utc")

    now_utc = pd.Timestamp(datetime.now(timezone.utc))
    window_start = now_utc - pd.Timedelta(hours=3)
    window_end = now_utc + pd.Timedelta(hours=hours_ahead)
    in_window = upcoming[
        (upcoming["_kickoff_utc"] >= window_start) & (upcoming["_kickoff_utc"] <= window_end)
    ]
    if not in_window.empty:
        return in_window.sort_values("_kickoff_utc")
    next_gw = int(upcoming.sort_values("_kickoff_utc").iloc[0]["gameweek"])
    return upcoming[upcoming["gameweek"].astype(int) == next_gw].sort_values("_kickoff_utc")


def score_row_with_production_models(
    simulated_df: pd.DataFrame,
    outcome_artifact: Dict[str, Any],
    goals_artifact: Optional[Dict[str, Any]],
) -> Dict[str, float]:
    o_features = outcome_artifact.get("feature_names_1x2", outcome_artifact["feature_names"])
    probs_1x2 = outcome_artifact["model_1x2"].predict_proba(
        safe_feature_frame(simulated_df, o_features, fill_value=np.nan)
    )
    has_ensemble = (
        "model_dc" in outcome_artifact
        and outcome_artifact.get("metrics", {})
        .get("1x2_ensemble_production", {})
        .get("enabled", True)
    )
    if has_ensemble:
        dc_probs_1x2 = outcome_artifact["model_dc"].predict_proba(simulated_df)
        probs_1x2 = blend_log(probs_1x2, dc_probs_1x2, outcome_artifact["ensemble_weight"])
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2_ensemble")
    else:
        calibrator_1x2 = outcome_artifact.get("calibrators", {}).get("1x2")
    if calibrator_1x2:
        probs_1x2 = apply_probability_calibrator(probs_1x2, calibrator_1x2)
    p1x2 = probs_1x2[0]

    lam_h, lam_a, p_o25, p_btts = 0.0, 0.0, 0.0, 0.0
    if goals_artifact is not None:
        score_matrix = align_to_outcome_probs(
            goals_artifact["model"].predict_matrices(simulated_df), np.atleast_2d(p1x2)
        )
        lh, la = expected_goals(score_matrix)
        lam_h, lam_a = float(lh[0]), float(la[0])
        p_o25 = float(over_prob(score_matrix, 2.5)[0]) * 100.0
        p_btts = float(btts_prob(score_matrix)[0]) * 100.0

    return {
        "home_pct": float(p1x2[0] * 100.0),
        "draw_pct": float(p1x2[1] * 100.0),
        "away_pct": float(p1x2[2] * 100.0),
        "lambda_home": lam_h,
        "lambda_away": lam_a,
        "lambda_total": lam_h + lam_a,
        "over_25_pct": p_o25,
        "btts_pct": p_btts,
        "home_xi_rating": float(simulated_df["home_xi_rating"].iloc[0]),
        "away_xi_rating": float(simulated_df["away_xi_rating"].iloc[0]),
        "xi_rating_diff": float(simulated_df["xi_rating_diff"].iloc[0]),
        "xi_att_vs_def_diff": float(simulated_df["xi_att_vs_def_diff"].iloc[0]),
    }


def fetch_db_odds(match_id: int) -> List[Dict[str, Any]]:
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT bookmaker, home_open, draw_open, away_open,
               home_last_seen, draw_last_seen, away_last_seen,
               over_25_open, under_25_open, over_25_last_seen, under_25_last_seen,
               btts_yes_open, btts_no_open, btts_yes_last_seen, btts_no_last_seen,
               fetched_at_utc
        FROM external_match_odds
        WHERE match_id = ?
        ORDER BY CASE bookmaker
            WHEN 'Pinnacle' THEN 1
            WHEN 'Bet365' THEN 2
            WHEN 'Betfair Exchange' THEN 3
            ELSE 4
        END
        """,
        (int(match_id),),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def print_match_report(
    fx: pd.Series,
    details: Optional[Dict[str, Any]],
    player_history: Dict[int, List[Tuple[str, float, float, float]]],
    last_xi_pids: Dict[int, Set[int]],
    last_xi_ratings: Dict[int, Tuple[float, float, float]],
    outcome_artifact: Dict[str, Any],
    goals_artifact: Optional[Dict[str, Any]],
    reg: Dict[int, Dict[str, Any]],
) -> Optional[Dict[str, float]]:
    mid = int(fx["match_id"])
    home_id, away_id = int(fx["home_id"]), int(fx["away_id"])
    home_name = str(fx.get("home_name") or home_id)
    away_name = str(fx.get("away_name") or away_id)
    season = str(fx.get("season") or "2026_27")
    gw = int(fx.get("gameweek") or 0)
    kickoff_utc = fx.get("_kickoff_utc")
    tr_time_str = (
        (kickoff_utc + pd.Timedelta(hours=3)).strftime("%d.%m.%Y %H:%M (TSİ)")
        if pd.notnull(kickoff_utc)
        else str(fx.get("match_date"))
    )

    team_lists = extract_team_lists(details or {})
    has_official = (home_id in team_lists) and (away_id in team_lists)

    print("=" * 90)
    print(f"⚽ MAÇ [{mid}] | GW{gw} | {home_name} vs {away_name} | {tr_time_str}")
    print(f"👨‍⚖️ Hakem: {fx.get('referee_name') or 'Belirlenmedi'}")
    if has_official:
        h_form = team_lists[home_id]["formation"]
        a_form = team_lists[away_id]["formation"]
        print(f"✅ KADRO DURUMU: RESMİ İLK 11'LER AÇIKLANDI ({home_name}: {h_form} | {away_name}: {a_form})")
    else:
        print("⏳ KADRO DURUMU: Resmi 11'ler henüz PulseLive'da yayınlanmadı (maçtan ~60-75 dk önce açıklanır).")
    print("=" * 90)

    # Last match XI baseline ratings
    h_prev_ov, h_prev_att, h_prev_def = last_xi_ratings.get(home_id, (6.15, 6.15, 6.15))
    a_prev_ov, a_prev_att, a_prev_def = last_xi_ratings.get(away_id, (6.15, 6.15, 6.15))

    h_curr_ov, h_curr_att, h_curr_def = h_prev_ov, h_prev_att, h_prev_def
    a_curr_ov, a_curr_att, a_curr_def = a_prev_ov, a_prev_att, a_prev_def

    if has_official:
        for side_label, tid, tname in (("EV SAHİBİ", home_id, home_name), ("DEPLASMAN", away_id, away_name)):
            t_data = team_lists[tid]
            lineup = t_data["lineup"]
            subs = t_data["subs"]
            prev_pids = last_xi_pids.get(tid, set())
            curr_pids = {int(p["id"]) for p in lineup if p.get("id") is not None}

            added_pids = curr_pids - prev_pids
            removed_pids = prev_pids - curr_pids

            starters_tuples: List[Tuple[int, str]] = []
            print(f"\n📋 {side_label}: {tname} (Diziliş: {t_data['formation']})")
            print(f"   {'No':<4} {'Oyuncu':<26} {'Mevki':<6} {'Genel':>6} {'Hücum':>6} {'Savunma':>7}  {'Durum'}")
            print("   " + "-" * 74)
            for p in lineup:
                pid = int(p["id"])
                shirt = p.get("matchShirtNumber") or "-"
                pname = (p.get("name") or {}).get("display") or reg.get(pid, {}).get("name") or str(pid)
                pos = str(p.get("matchPosition") or reg.get(pid, {}).get("position") or "M")
                starters_tuples.append((pid, pos))
                ov, att, df_r = _compute_pre_match_player_rating(player_history, pid, season)
                tag = "🆕 (11'e Girdi)" if (prev_pids and pid in added_pids) else ""
                print(f"   #{str(shirt):<3} {pname:<26} {pos:<6} {ov:>6.2f} {att:>6.2f} {df_r:>7.2f}  {tag}")

            ov_agg, att_agg, def_agg = _aggregate_xi_ratings(starters_tuples, player_history, season)
            if tid == home_id:
                h_curr_ov, h_curr_att, h_curr_def = ov_agg, att_agg, def_agg
            else:
                a_curr_ov, a_curr_att, a_curr_def = ov_agg, att_agg, def_agg

            if prev_pids and removed_pids:
                removed_names = []
                for rpid in removed_pids:
                    rname = reg.get(rpid, {}).get("name") or f"ID:{rpid}"
                    rov, _, _ = _compute_pre_match_player_rating(player_history, rpid, season)
                    removed_names.append(f"{rname} ({rov:.2f})")
                print(f"   🔻 Geçen Maçın 11'inden Çıkanlar ({len(removed_names)}): {', '.join(removed_names)}")
            elif prev_pids:
                print("   🔄 Geçen maçın ilk 11'i ile birebir aynı (0 değişiklik).")

            sub_names = [(s.get("name") or {}).get("display") for s in subs if (s.get("name") or {}).get("display")]
            if sub_names:
                print(f"   🪑 Yedekler: {', '.join(sub_names)}")

    base_df = fx.to_frame().T.copy()

    # Row with previous match XI
    row_prev = base_df.copy()
    row_prev["home_xi_rating"] = h_prev_ov
    row_prev["away_xi_rating"] = a_prev_ov
    row_prev["xi_rating_diff"] = h_prev_ov - a_prev_ov
    row_prev["home_xi_att_vs_away_def"] = h_prev_att - a_prev_def
    row_prev["away_xi_att_vs_home_def"] = a_prev_att - h_prev_def
    row_prev["xi_att_vs_def_diff"] = (h_prev_att - a_prev_def) - (a_prev_att - h_prev_def)
    pred_prev = score_row_with_production_models(row_prev, outcome_artifact, goals_artifact)

    # Row with official announced XI
    row_curr = base_df.copy()
    row_curr["home_xi_rating"] = h_curr_ov
    row_curr["away_xi_rating"] = a_curr_ov
    row_curr["xi_rating_diff"] = h_curr_ov - a_curr_ov
    row_curr["home_xi_att_vs_away_def"] = h_curr_att - a_curr_def
    row_curr["away_xi_att_vs_home_def"] = a_curr_att - h_curr_def
    row_curr["xi_att_vs_def_diff"] = (h_curr_att - a_curr_def) - (a_curr_att - h_curr_def)
    pred_curr = score_row_with_production_models(row_curr, outcome_artifact, goals_artifact)

    print("\n📊 MODEL GİRDİ & TAHMİN KARŞILAŞTIRMASI (Geçen Maç 11'i vs Bugünkü Resmi 11):")
    print(f"   {'Metrik':<34} {'Önceki (Geçen Maç 11)':>22} {'Güncel (Resmi 11)':>20} {'Fark (Δ)':>10}")
    print("   " + "-" * 88)
    metrics_rows = [
        (f"{home_name} XI Genel Reyting", pred_prev["home_xi_rating"], pred_curr["home_xi_rating"], "{:.2f}", "{:+.2f}"),
        (f"{away_name} XI Genel Reyting", pred_prev["away_xi_rating"], pred_curr["away_xi_rating"], "{:.2f}", "{:+.2f}"),
        (f"{home_name} Hücum / Savunma", h_prev_att, h_curr_att, "{:.2f}", "{:+.2f}"),
        (f"{away_name} Hücum / Savunma", a_prev_att, a_curr_att, "{:.2f}", "{:+.2f}"),
        ("Net XI Kalite Farkı (xi_diff)", pred_prev["xi_rating_diff"], pred_curr["xi_rating_diff"], "{:+.2f}", "{:+.2f}"),
        ("Hücum vs Savunma (att_vs_def)", pred_prev["xi_att_vs_def_diff"], pred_curr["xi_att_vs_def_diff"], "{:+.2f}", "{:+.2f}"),
        (f"1 - {home_name} Kazanır (%)", pred_prev["home_pct"], pred_curr["home_pct"], "%{:.1f}", "{:+.1f} pt"),
        ("X - Beraberlik (%)", pred_prev["draw_pct"], pred_curr["draw_pct"], "%{:.1f}", "{:+.1f} pt"),
        (f"2 - {away_name} Kazanır (%)", pred_prev["away_pct"], pred_curr["away_pct"], "%{:.1f}", "{:+.1f} pt"),
        (f"{home_name} Gol Beklentisi (λ_H)", pred_prev["lambda_home"], pred_curr["lambda_home"], "{:.2f}", "{:+.2f}"),
        (f"{away_name} Gol Beklentisi (λ_A)", pred_prev["lambda_away"], pred_curr["lambda_away"], "{:.2f}", "{:+.2f}"),
        ("Toplam Gol Beklentisi (λ_Top)", pred_prev["lambda_total"], pred_curr["lambda_total"], "{:.2f}", "{:+.2f}"),
        ("2.5 Gol Üstü (%)", pred_prev["over_25_pct"], pred_curr["over_25_pct"], "%{:.1f}", "{:+.1f} pt"),
        ("Karşılıklı Gol Var (%)", pred_prev["btts_pct"], pred_curr["btts_pct"], "%{:.1f}", "{:+.1f} pt"),
    ]
    for label, v_old, v_new, fmt_v, fmt_d in metrics_rows:
        diff = v_new - v_old
        print(f"   {label:<34} {fmt_v.format(v_old):>22} {fmt_v.format(v_new):>20} {fmt_d.format(diff):>10}")

    odds_rows = fetch_db_odds(mid)
    if odds_rows:
        print("\n💰 PİYASA ORANLARI (Açılış -> Son / Kapanış) & GÜNCEL MODEL DEĞER (EDGE) ANALİZİ:")
        print(f"   {'Büro':<18} {'Açılış (1-X-2)':<20} {'Son Oran (1-X-2)':<20} {'Edge 1':>8} {'Edge X':>8} {'Edge 2':>8}")
        print("   " + "-" * 88)
        for r in odds_rows:
            bm = r["bookmaker"]
            ho, do, ao = r["home_open"], r["draw_open"], r["away_open"]
            hl, dl, al = r["home_last_seen"] or ho, r["draw_last_seen"] or do, r["away_last_seen"] or ao
            if not (hl and dl and al):
                continue
            inv_sum = (1.0 / hl) + (1.0 / dl) + (1.0 / al)
            fair_h = (1.0 / hl) / inv_sum * 100.0
            fair_d = (1.0 / dl) / inv_sum * 100.0
            fair_a = (1.0 / al) / inv_sum * 100.0
            edge_h = pred_curr["home_pct"] - fair_h
            edge_d = pred_curr["draw_pct"] - fair_d
            edge_a = pred_curr["away_pct"] - fair_a
            open_str = f"{ho:.2f}-{do:.2f}-{ao:.2f}" if (ho and do and ao) else "-"
            last_str = f"{hl:.2f}-{dl:.2f}-{al:.2f}"
            print(f"   {bm:<18} {open_str:<20} {last_str:<20} {edge_h:>+7.1f}% {edge_d:>+7.1f}% {edge_a:>+7.1f}%")

        ou_btts_printed = False
        for r in odds_rows:
            bm = r["bookmaker"]
            o25 = r["over_25_last_seen"] or r["over_25_open"]
            u25 = r["under_25_last_seen"] or r["under_25_open"]
            by = r["btts_yes_last_seen"] or r["btts_yes_open"]
            bn = r["btts_no_last_seen"] or r["btts_no_open"]
            if o25 and u25:
                if not ou_btts_printed:
                    print("\n   Gol Pazarları (2.5 Üst & KG Var):")
                    ou_btts_printed = True
                fair_o25 = (1.0 / o25) / ((1.0 / o25) + (1.0 / u25)) * 100.0
                edge_o25 = pred_curr["over_25_pct"] - fair_o25
                btts_part = ""
                if by and bn:
                    fair_btts = (1.0 / by) / ((1.0 / by) + (1.0 / bn)) * 100.0
                    edge_btts = pred_curr["btts_pct"] - fair_btts
                    btts_part = f" | KG Var: {by:.2f} (Adil %{fair_btts:.1f}, Edge {edge_btts:+.1f}%)"
                print(f"   • {bm:<16}: 2.5 Üst: {o25:.2f} (Adil %{fair_o25:.1f}, Edge {edge_o25:+.1f}%){btts_part}")
    print()

    if has_official:
        return {
            "home_xi_rating": h_curr_ov,
            "away_xi_rating": a_curr_ov,
            "xi_rating_diff": h_curr_ov - a_curr_ov,
            "home_xi_att_vs_away_def": h_curr_att - a_curr_def,
            "away_xi_att_vs_home_def": a_curr_att - h_curr_def,
            "xi_att_vs_def_diff": (h_curr_att - a_curr_def) - (a_curr_att - h_curr_def),
        }
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch pre-match official lineups from PulseLive and run updated model predictions."
    )
    parser.add_argument("--season", default="2026_27", help="Season label (default: 2026_27)")
    parser.add_argument("--match-id", type=int, help="Specific PulseLive match ID (e.g. 128986)")
    parser.add_argument("--team", type=str, help="Team name filter (e.g. Everton, Chelsea)")
    parser.add_argument("--gameweek", type=int, help="Specific gameweek number (e.g. 7)")
    parser.add_argument("--hours-ahead", type=float, default=12.0, help="Lookahead window in hours when no filter is given")
    parser.add_argument("--refresh-odds", action="store_true", help="Refresh live odds from TheStatsAPI if THESTATSAPI_KEY is set")
    args = parser.parse_args()

    df_features = pd.read_parquet(FEATURES_PATH)
    outcome_artifact = joblib.load(OUTCOME_MODEL_PATH)
    goals_artifact = joblib.load(GOALS_MODEL_PATH) if GOALS_MODEL_PATH.exists() else None

    targets = get_target_fixtures(
        df_features,
        season=args.season,
        match_id=args.match_id,
        team_query=args.team,
        gameweek=args.gameweek,
        hours_ahead=args.hours_ahead,
    )
    if targets.empty:
        print("Eşleşen yaklaşan maç bulunamadı.")
        return

    if args.refresh_odds:
        import os
        api_key = os.environ.get("THESTATSAPI_KEY", "").strip()
        if api_key:
            from src.ingest.import_thestatsapi_odds import import_odds
            import_odds(api_key=api_key, season=args.season, only_played=False)
        else:
            print("⚠️  --refresh-odds verildi ancak THESTATSAPI_KEY ortam değişkeni tanımlı değil; mevcut veritabanı oranları kullanılıyor.")

    player_history, last_xi_pids, last_xi_ratings = build_player_history_and_last_xi(df_features)
    session = build_session()
    reg = get_all_players_registry()

    parquet_updated = False
    found_labels: List[str] = []
    for _, fx in targets.iterrows():
        mid = int(fx["match_id"])
        details = fetch_match_details(session, mid)
        if details:
            atomic_write_json(MATCHES_RAW_DIR / f"{mid}_details.json", details)
        else:
            cached = MATCHES_RAW_DIR / f"{mid}_details.json"
            if cached.exists():
                details = json.loads(cached.read_text(encoding="utf-8"))

        xi_updates = print_match_report(
            fx=fx,
            details=details,
            player_history=player_history,
            last_xi_pids=last_xi_pids,
            last_xi_ratings=last_xi_ratings,
            outcome_artifact=outcome_artifact,
            goals_artifact=goals_artifact,
            reg=reg,
        )
        if xi_updates:
            found_labels.append(f"{fx.get('home_name')} - {fx.get('away_name')}")
            mask = df_features["match_id"].astype(int) == mid
            for col, val in xi_updates.items():
                if col in df_features.columns:
                    df_features.loc[mask, col] = float(val)
            parquet_updated = True

    if parquet_updated:
        df_features.to_parquet(FEATURES_PATH, index=False)
        print(f"💾 Resmi ilk 11 reytingleri '{FEATURES_PATH.relative_to(PROJECT_ROOT)}' tablosuna kaydedildi.")
    print("SYNC_RESULT " + json.dumps({"matches": found_labels}, ensure_ascii=False))


if __name__ == "__main__":
    main()
