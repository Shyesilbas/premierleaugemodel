#!/usr/bin/env python3
"""
Premier League Model Engine — FastAPI Backend Server
Serves interactive prediction engine, fixtures, events, and static frontend dashboard.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from scipy.stats import poisson

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_server")

app = FastAPI(title="Premier League Model Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models" / "production"
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else (BASE_DIR / "frontend")

# Load Datasets & Models into memory (Prefer combined multi-season, fallback to 2024-25)
logger.info("Loading cached datasets and models...")
matches_all = DATA_DIR / "processed" / "matches_summary_all.parquet"
features_all = DATA_DIR / "processed" / "features_matches_all.parquet"
events_all = DATA_DIR / "processed" / "shots_events_all.parquet"

matches_parquet = matches_all if matches_all.exists() else (DATA_DIR / "processed" / "matches_summary_2024_25.parquet")
features_parquet = features_all if features_all.exists() else (DATA_DIR / "processed" / "features_matches_2024_25.parquet")
events_parquet = events_all if events_all.exists() else (DATA_DIR / "processed" / "shots_events_2024_25.parquet")

df_matches = pd.read_parquet(matches_parquet) if matches_parquet.exists() else pd.DataFrame()
df_features = pd.read_parquet(features_parquet) if features_parquet.exists() else pd.DataFrame()
df_events = pd.read_parquet(events_parquet) if events_parquet.exists() else pd.DataFrame()

# Load trained models
corner_artifact = joblib.load(MODELS_DIR / "corner_model_v1.joblib") if (MODELS_DIR / "corner_model_v1.joblib").exists() else None
throws_artifact = joblib.load(MODELS_DIR / "throws_model_v1.joblib") if (MODELS_DIR / "throws_model_v1.joblib").exists() else None
saves_artifact = joblib.load(MODELS_DIR / "saves_model_v1.joblib") if (MODELS_DIR / "saves_model_v1.joblib").exists() else None
outcome_artifact = joblib.load(MODELS_DIR / "outcome_models_v1.joblib") if (MODELS_DIR / "outcome_models_v1.joblib").exists() else None
offside_artifact = joblib.load(MODELS_DIR / "offside_model_v1.joblib") if (MODELS_DIR / "offside_model_v1.joblib").exists() else None

# Load Player Registry and Match Logs
players_reg_file = DATA_DIR / "processed" / "players_registry.json"
players_logs_file = DATA_DIR / "processed" / "player_match_logs.json"

all_players = []
if players_reg_file.exists():
    with open(players_reg_file, "r", encoding="utf-8") as f:
        all_players = json.load(f)

player_logs_dict = {}
if players_logs_file.exists():
    with open(players_logs_file, "r", encoding="utf-8") as f:
        player_logs_dict = json.load(f)

# Load 2026-27 fixtures if available
raw_fixtures_2627 = []
fix_2627_path = DATA_DIR / "raw" / "fixtures_2026_27.json"
if fix_2627_path.exists():
    with open(fix_2627_path, "r", encoding="utf-8") as f:
        raw_fixtures_2627 = json.load(f)


# Unique Teams and Match Stats Lookup
teams_dict = {}
match_stats_map = {}
if not df_matches.empty:
    for _, r in df_matches.iterrows():
        mid = int(r["match_id"])
        teams_dict[int(r["home_id"])] = {"id": int(r["home_id"]), "name": r["home_name"], "abbr": r["home_abbr"]}
        teams_dict[int(r["away_id"])] = {"id": int(r["away_id"]), "name": r["away_name"], "abbr": r["away_abbr"]}
        if pd.notnull(r.get("total_corners")):
            match_stats_map[mid] = {
                "total_corners": r.get("total_corners"),
                "total_throws": r.get("total_throws"),
                "total_shots": r.get("total_shots"),
                "total_shots_ontarget": r.get("total_shots_ontarget"),
                "total_saves": r.get("total_saves"),
                "home_won_corners": r.get("home_won_corners"),
                "away_won_corners": r.get("away_won_corners"),
                "home_total_throws": r.get("home_total_throws"),
                "away_total_throws": r.get("away_total_throws"),
            }

teams_list = sorted(list(teams_dict.values()), key=lambda x: x["name"])


@app.get("/api/teams")
def get_teams(season: Optional[str] = None):
    """Returns sorted list of teams, optionally filtered by season (2024_25 or 2025_26)."""
    if df_matches.empty:
        return {"teams": teams_list}

    df = df_matches
    if season and "season" in df.columns:
        df = df[df["season"] == season]

    filtered_teams = {}
    for _, r in df.iterrows():
        filtered_teams[int(r["home_id"])] = {"id": int(r["home_id"]), "name": r["home_name"], "abbr": r["home_abbr"]}
        filtered_teams[int(r["away_id"])] = {"id": int(r["away_id"]), "name": r["away_name"], "abbr": r["away_abbr"]}

    result = sorted(list(filtered_teams.values()), key=lambda x: x["name"])
    return {"teams": result, "count": len(result)}


@app.get("/api/fixtures")
def get_fixtures(limit: int = 800, search: Optional[str] = None, season: Optional[str] = None):
    """Returns list of matches, optionally filtered by season and search."""
    if df_matches.empty:
        return {"fixtures": []}

    df = df_matches.copy()
    if season and "season" in df.columns and season != "all":
        df = df[df["season"] == season]

    if search:
        s = search.lower()
        mask = (
            df["home_name"].str.lower().str.contains(s) |
            df["away_name"].str.lower().str.contains(s) |
            df["ground_name"].str.lower().str.contains(s)
        )
        df = df[mask]

    records = df.head(limit).to_dict(orient="records")
    return {"fixtures": records, "total": len(records)}


@app.get("/api/fixtures/grouped")
def get_grouped_fixtures(season: str = "2026_27"):
    """
    Returns fixtures grouped by Gameweek, and within each Gameweek, grouped by match day.
    Supports 2026_27 (upcoming/current), 2025_26, 2024_25, or 'all'.
    """
    raw_fixtures = []

    if season == "2026_27" and raw_fixtures_2627:
        for f in raw_fixtures_2627:
            teams = f.get("teams", [])
            h_team = teams[0].get("team", {}) if len(teams) > 0 else {}
            a_team = teams[1].get("team", {}) if len(teams) > 1 else {}
            h_score = teams[0].get("score") if len(teams) > 0 else None
            a_score = teams[1].get("score") if len(teams) > 1 else None

            kickoff_str = f.get("kickoff", {}).get("label", "")
            # Example label: "Fri 21 Aug 2026, 20:00 BST"
            day_part = kickoff_str.split(",")[0].strip() if "," in kickoff_str else kickoff_str
            time_part = kickoff_str.split(",")[1].strip() if "," in kickoff_str else ""

            mid = int(f.get("id", 0))
            m_stats = match_stats_map.get(mid, {})

            raw_fixtures.append({
                "match_id": mid,
                "gameweek": int(f.get("gameweek", {}).get("gameweek", 1)),
                "kickoff_label": kickoff_str,
                "day_label": day_part,
                "time_label": time_part,
                "ground_name": f.get("ground", {}).get("name", ""),
                "home_id": int(h_team.get("id", 0)),
                "home_name": h_team.get("name", ""),
                "home_abbr": h_team.get("club", {}).get("abbr", ""),
                "home_score": h_score,
                "away_id": int(a_team.get("id", 0)),
                "away_name": a_team.get("name", ""),
                "away_abbr": a_team.get("club", {}).get("abbr", ""),
                "away_score": a_score,
                "total_corners": m_stats.get("total_corners"),
                "total_throws": m_stats.get("total_throws"),
                "total_shots": m_stats.get("total_shots"),
                "total_shots_ontarget": m_stats.get("total_shots_ontarget"),
                "total_saves": m_stats.get("total_saves"),
                "home_won_corners": m_stats.get("home_won_corners"),
                "away_won_corners": m_stats.get("away_won_corners"),
                "home_total_throws": m_stats.get("home_total_throws"),
                "away_total_throws": m_stats.get("away_total_throws"),
                "status": "COMPLETED" if (h_score is not None and a_score is not None) else "UPCOMING",
                "season": "2026_27",
            })
    else:
        df = df_matches.copy()
        if season != "all" and "season" in df.columns:
            df = df[df["season"] == season]

        for _, r in df.iterrows():
            kickoff_str = str(r.get("kickoff_label", ""))
            day_part = kickoff_str.split(",")[0].strip() if "," in kickoff_str else kickoff_str
            time_part = kickoff_str.split(",")[1].strip() if "," in kickoff_str else ""

            raw_fixtures.append({
                "match_id": int(r["match_id"]),
                "gameweek": int(r.get("gameweek") or 1),
                "kickoff_label": kickoff_str,
                "day_label": day_part,
                "time_label": time_part,
                "ground_name": str(r.get("ground_name", "")),
                "home_id": int(r["home_id"]),
                "home_name": str(r["home_name"]),
                "home_abbr": str(r.get("home_abbr", "")),
                "home_score": int(r["home_score"]) if pd.notnull(r.get("home_score")) else None,
                "away_id": int(r["away_id"]),
                "away_name": str(r["away_name"]),
                "away_abbr": str(r.get("away_abbr", "")),
                "away_score": int(r["away_score"]) if pd.notnull(r.get("away_score")) else None,
                "total_corners": int(r["total_corners"]) if pd.notnull(r.get("total_corners")) else None,
                "total_throws": int(r["total_throws"]) if pd.notnull(r.get("total_throws")) else None,
                "total_shots": int(r["total_shots"]) if pd.notnull(r.get("total_shots")) else None,
                "total_saves": int(r["total_saves"]) if pd.notnull(r.get("total_saves")) else None,
                "home_won_corners": int(r["home_won_corners"]) if pd.notnull(r.get("home_won_corners")) else None,
                "away_won_corners": int(r["away_won_corners"]) if pd.notnull(r.get("away_won_corners")) else None,
                "home_total_throws": int(r["home_total_throws"]) if pd.notnull(r.get("home_total_throws")) else None,
                "away_total_throws": int(r["away_total_throws"]) if pd.notnull(r.get("away_total_throws")) else None,
                "status": "COMPLETED" if pd.notnull(r.get("home_score")) else "UPCOMING",
                "season": str(r.get("season", "2024_25")),
            })

    # Group by Gameweek -> Day
    gw_groups = {}
    for fix in raw_fixtures:
        gw = fix["gameweek"]
        if gw not in gw_groups:
            gw_groups[gw] = {}
        day = fix["day_label"] or "Belirtilmemiş Gün"
        if day not in gw_groups[gw]:
            gw_groups[gw][day] = []
        gw_groups[gw][day].append(fix)

    structured = []
    for gw in sorted(gw_groups.keys()):
        day_list = []
        for d in gw_groups[gw]:
            day_list.append({"day": d, "matches": gw_groups[gw][d]})
        structured.append({"gameweek": gw, "days": day_list})

    # Determine current gameweek:
    current_gw = 1
    upcoming_gws = [
        gw for gw in sorted(gw_groups.keys())
        if any(m.get("status") == "UPCOMING" for d in gw_groups[gw].values() for m in d)
    ]
    if upcoming_gws:
        current_gw = upcoming_gws[0]
    elif gw_groups:
        current_gw = max(gw_groups.keys())

    return {
        "season": season,
        "gameweeks": structured,
        "total_matches": len(raw_fixtures),
        "current_gameweek": current_gw,
    }


@app.get("/api/teams/profile")
def get_team_profile(team_id: int, season: Optional[str] = "all"):
    """
    Returns team profile with match previews, W/D/L record, and squad roster.
    """
    team_meta = teams_dict.get(team_id)
    if not team_meta:
        # Fallback search in all_players
        p_team = next((p for p in all_players if p.get("teamId") == team_id), None)
        if p_team:
            team_meta = {"id": team_id, "name": p_team.get("teamName", ""), "abbr": ""}
        else:
            raise HTTPException(status_code=404, detail="Team not found")

    df = df_matches.copy()
    if season and season != "all" and "season" in df.columns:
        df = df[df["season"] == season]

    # Filter team matches
    team_matches_df = df[(df["home_id"] == team_id) | (df["away_id"] == team_id)].copy()
    if "kickoff_millis" in team_matches_df.columns:
        team_matches_df = team_matches_df.sort_values(by="kickoff_millis")

    matches_list = []
    wins, draws, losses = 0, 0, 0
    gf, ga = 0, 0

    for _, r in team_matches_df.iterrows():
        is_home = (int(r["home_id"]) == team_id)
        opp_id = int(r["away_id"]) if is_home else int(r["home_id"])
        opp_name = str(r["away_name"]) if is_home else str(r["home_name"])
        t_score = r["home_score"] if is_home else r["away_score"]
        o_score = r["away_score"] if is_home else r["home_score"]

        res = "-"
        if pd.notnull(t_score) and pd.notnull(o_score):
            t_score_int = int(t_score)
            o_score_int = int(o_score)
            gf += t_score_int
            ga += o_score_int
            if t_score_int > o_score_int:
                res = "W"
                wins += 1
            elif t_score_int < o_score_int:
                res = "L"
                losses += 1
            else:
                res = "D"
                draws += 1
            t_score = t_score_int
            o_score = o_score_int
        else:
            t_score = None
            o_score = None

        matches_list.append({
            "match_id": int(r["match_id"]),
            "season": str(r.get("season", "")),
            "status": "COMPLETED" if pd.notnull(t_score) else "UNPLAYED",
            "gameweek": r.get("gameweek"),
            "kickoff_label": r.get("kickoff_label"),
            "is_home": is_home,
            "opponent_id": opp_id,
            "opponent_name": opp_name,
            "team_score": t_score,
            "opp_score": o_score,
            "result": res,
            "total_corners": int(r["total_corners"]) if pd.notnull(r.get("total_corners")) else None,
            "total_throws": int(r["total_throws"]) if pd.notnull(r.get("total_throws")) else None,
            "total_shots": int(r["total_shots"]) if pd.notnull(r.get("total_shots")) else None,
            "total_saves": int(r["total_saves"]) if pd.notnull(r.get("total_saves")) else None,
        })

    # Squad list
    squad = [p for p in all_players if p.get("teamId") == team_id]

    return {
        "team": team_meta,
        "season": season,
        "record": {"wins": wins, "draws": draws, "losses": losses, "played": len(matches_list), "gf": gf, "ga": ga},
        "matches": matches_list,
        "squad": squad,
    }


@app.get("/api/players")
def get_players(team_id: Optional[int] = None, search: Optional[str] = None, limit: int = 100):
    """Returns player directory with optional filters."""
    result = all_players
    if team_id:
        result = [p for p in result if p.get("teamId") == team_id]
    if search:
        s = search.lower()
        result = [p for p in result if s in p.get("name", "").lower() or s in p.get("teamName", "").lower()]

    return {"players": result[:limit], "total": len(result)}


@app.get("/api/players/profile")
def get_player_profile(player_id: int, season: Optional[str] = "all"):
    """
    Returns player profile and their match-by-match preview log:
    including opponent, score, minutes played, goals, and assists.
    """
    player = next((p for p in all_players if p["id"] == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    raw_logs = player_logs_dict.get(str(player_id), player_logs_dict.get(player_id, []))
    if season and season != "all":
        logs = [m for m in raw_logs if m.get("season") == season]
    else:
        logs = raw_logs

    tot_mins = sum(m.get("minutes_played", 0) for m in logs)
    tot_goals = sum(m.get("goals", 0) for m in logs)
    tot_assists = sum(m.get("assists", 0) for m in logs)

    return {
        "player": player,
        "season": season,
        "season_stats": {
            "appearances": len(logs),
            "minutes": tot_mins,
            "goals": tot_goals,
            "assists": tot_assists,
        },
        "matches": logs,
    }


@app.get("/api/match/{match_id}/details")
def get_match_full_details(match_id: int):
    """
    Returns full match lineup rosters, substitutes, tactical formations,
    and play-by-play events.
    """
    raw_details = DATA_DIR / "raw" / "matches" / f"{match_id}_details.json"
    raw_stream = DATA_DIR / "raw" / "matches" / f"{match_id}_stream.json"

    raw_stats = DATA_DIR / "raw" / "matches" / f"{match_id}_stats.json"

    lineups = []
    metadata = {}
    team_stats = []
    player_stats = {"home": [], "away": []}

    d = {}
    if raw_details.exists():
        with open(raw_details, "r", encoding="utf-8") as f:
            d = json.load(f)

        metadata = {
            "match_id": match_id,
            "kickoff_label": d.get("kickoff", {}).get("label"),
            "ground": d.get("ground", {}).get("name"),
            "attendance": d.get("attendance"),
            "referee": d.get("matchOfficials", [{}])[0].get("matchOfficial", {}).get("name", {}).get("display") if d.get("matchOfficials") else None,
            "halfTimeScore": d.get("halfTimeScore"),
        }

        teams_info = d.get("teams", [])
        for idx, tl in enumerate(d.get("teamLists", [])):
            if not tl or not isinstance(tl, dict):
                continue
            t_obj = teams_info[idx].get("team", {}) if idx < len(teams_info) else {}
            score_val = teams_info[idx].get("score") if idx < len(teams_info) else None

            starters = []
            for p in tl.get("lineup", []):
                starters.append({
                    "id": p.get("id"),
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": p.get("matchPosition") or p.get("info", {}).get("position"),
                    "captain": p.get("captain", False),
                    "country": p.get("nationalTeam", {}).get("country"),
                })

            subs = []
            for p in tl.get("substitutes", []):
                subs.append({
                    "id": p.get("id"),
                    "name": p.get("name", {}).get("display"),
                    "shirt": p.get("matchShirtNumber"),
                    "position": p.get("matchPosition") or p.get("info", {}).get("position"),
                })

            lineups.append({
                "team_id": tl.get("teamId"),
                "team_name": t_obj.get("name"),
                "score": score_val,
                "formation": tl.get("formation", {}).get("label", "4-3-3"),
                "starters": starters,
                "substitutes": subs,
            })

    # Team Stats (Comparative 182 Metrics across categories)
    if raw_stats.exists():
        with open(raw_stats, "r", encoding="utf-8") as f:
            s_data = json.load(f)

        t_data = s_data.get("data", {})
        teams_info = d.get("teams", [])
        h_id_str = str(int(teams_info[0].get("team", {}).get("id", 0))) if len(teams_info) > 0 else "0"
        a_id_str = str(int(teams_info[1].get("team", {}).get("id", 0))) if len(teams_info) > 1 else "0"

        hm = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(h_id_str, {}).get("M", [])}
        am = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(a_id_str, {}).get("M", [])}

        def m_pair(key, def_val=0.0):
            return hm.get(key, def_val), am.get(key, def_val)

        h_pass, a_pass = m_pair("total_pass")
        h_acc_p, a_acc_p = m_pair("accurate_pass")
        h_pass_pct = round((h_acc_p / max(1.0, h_pass)) * 100, 1) if h_pass > 0 else 0.0
        a_pass_pct = round((a_acc_p / max(1.0, a_pass)) * 100, 1) if a_pass > 0 else 0.0

        team_stats = [
            {
                "category": "Şut & Hücum Hacmi",
                "items": [
                    {"label": "Toplam Şut", "home": hm.get("total_scoring_att", 0), "away": am.get("total_scoring_att", 0)},
                    {"label": "İsabetli Şut", "home": hm.get("ontarget_scoring_att", 0), "away": am.get("ontarget_scoring_att", 0)},
                    {"label": "İsabetsiz Şut", "home": hm.get("shot_off_target", 0), "away": am.get("shot_off_target", 0)},
                    {"label": "Bloklanan Şut", "home": hm.get("blocked_scoring_att", 0), "away": am.get("blocked_scoring_att", 0)},
                    {"label": "Ceza Sahası İçi Şut", "home": hm.get("attempts_ibox", 0), "away": am.get("attempts_ibox", 0)},
                    {"label": "Ceza Sahası Dışı Şut", "home": hm.get("attempts_obox", 0), "away": am.get("attempts_obox", 0)},
                    {"label": "Yaratılan Net Fırsat", "home": hm.get("big_chance_created", 0), "away": am.get("big_chance_created", 0)},
                    {"label": "Kaçan Net Fırsat", "home": hm.get("big_chance_missed", 0), "away": am.get("big_chance_missed", 0)},
                    {"label": "Rakip Ceza Sahasında Topla Buluşma", "home": hm.get("touches_in_opp_box", 0), "away": am.get("touches_in_opp_box", 0)},
                    {"label": "Kilit Pas / Şut Pası", "home": hm.get("total_att_assist", 0), "away": am.get("total_att_assist", 0)},
                ]
            },
            {
                "category": "Top Hakimiyeti & Pas",
                "items": [
                    {"label": "Topa Sahip Olma", "home": hm.get("possession_percentage", 0), "away": am.get("possession_percentage", 0), "suffix": "%"},
                    {"label": "Toplam Pas", "home": h_pass, "away": a_pass},
                    {"label": "İsabetli Pas", "home": h_acc_p, "away": a_acc_p},
                    {"label": "Pas İsabet Oranı", "home": h_pass_pct, "away": a_pass_pct, "suffix": "%"},
                    {"label": "3. Bölge (Final Third) Pasları", "home": hm.get("total_final_third_passes", 0), "away": am.get("total_final_third_passes", 0)},
                    {"label": "Başarılı 3. Bölge Pasları", "home": hm.get("successful_final_third_passes", 0), "away": am.get("successful_final_third_passes", 0)},
                    {"label": "Toplam Orta / İsabet", "home": f"{int(hm.get('total_cross',0))} ({int(hm.get('accurate_cross',0))})", "away": f"{int(am.get('total_cross',0))} ({int(am.get('accurate_cross',0))})", "rawHome": hm.get("total_cross", 0), "rawAway": am.get("total_cross", 0)},
                    {"label": "Uzun Toplar", "home": hm.get("total_long_balls", 0), "away": am.get("total_long_balls", 0)},
                ]
            },
            {
                "category": "Duran Top & Baskı",
                "items": [
                    {"label": "Kazanılan Korner", "home": hm.get("won_corners", 0), "away": am.get("won_corners", 0)},
                    {"label": "Ceza Sahasına İsabetli Korner", "home": hm.get("accurate_corners_intobox", 0), "away": am.get("accurate_corners_intobox", 0)},
                    {"label": "Toplam Taç", "home": hm.get("total_throws", 0), "away": am.get("total_throws", 0)},
                    {"label": "İsabetli Taç", "home": hm.get("accurate_throws", 0), "away": am.get("accurate_throws", 0)},
                    {"label": "PPDA (Pres Baskı İndeksi)", "home": hm.get("ppda", 0), "away": am.get("ppda", 0)},
                ]
            },
            {
                "category": "Savunma & İkili Mücadele",
                "items": [
                    {"label": "Top Kapma (Kazanılan)", "home": f"{int(hm.get('total_tackle',0))} ({int(hm.get('won_tackle',0))})", "away": f"{int(am.get('total_tackle',0))} ({int(am.get('won_tackle',0))})", "rawHome": hm.get("total_tackle", 0), "rawAway": am.get("total_tackle", 0)},
                    {"label": "Pas Arası (Interception)", "home": hm.get("interception", 0), "away": am.get("interception", 0)},
                    {"label": "Tehlike Uzaklaştırma (Clearance)", "home": hm.get("total_clearance", 0), "away": am.get("total_clearance", 0)},
                    {"label": "Bloklanan Şut & Pas", "home": hm.get("outfielder_block", 0) + hm.get("blocked_pass", 0), "away": am.get("outfielder_block", 0) + am.get("blocked_pass", 0)},
                    {"label": "Sahipsiz Top Kazanma", "home": hm.get("ball_recovery", 0), "away": am.get("ball_recovery", 0)},
                    {"label": "Kazanılan İkili Mücadele", "home": hm.get("duel_won", 0), "away": am.get("duel_won", 0)},
                    {"label": "Kazanılan Hava Topu", "home": hm.get("aerial_won", 0), "away": am.get("aerial_won", 0)},
                ]
            },
            {
                "category": "Disiplin & Kaleci",
                "items": [
                    {"label": "Toplam Kurtarış", "home": hm.get("saves", 0), "away": am.get("saves", 0)},
                    {"label": "Ceza Sahası İçi Kurtarış", "home": hm.get("saved_ibox", 0), "away": am.get("saved_ibox", 0)},
                    {"label": "Yapılan Faul", "home": hm.get("fk_foul_lost", 0), "away": am.get("fk_foul_lost", 0)},
                    {"label": "Alınan Faul", "home": hm.get("fk_foul_won", 0), "away": am.get("fk_foul_won", 0)},
                    {"label": "Ofsayt", "home": hm.get("total_offside", 0), "away": am.get("total_offside", 0)},
                    {"label": "Sarı Kart", "home": hm.get("total_yel_card", 0), "away": am.get("total_yel_card", 0)},
                    {"label": "Kırmızı Kart", "home": hm.get("total_red_card", 0), "away": am.get("total_red_card", 0)},
                ]
            }
        ]

    # Player Match Performance Table (from details & stream)
    events = []
    if raw_stream.exists():
        with open(raw_stream, "r", encoding="utf-8") as f:
            st = json.load(f)
            events = st.get("events", {}).get("content", [])

    # Compute player metrics from details and stream
    det_events = d.get("events", [])
    sub_on = {}
    sub_off = {}
    goals = {}
    assists = {}
    yc = {}
    rc = {}

    for ev in det_events:
        etype = ev.get("type")
        pid = ev.get("personId")
        clk = ev.get("clock", {}).get("label", "")
        min_v = 0
        if clk:
            try:
                min_v = int(clk.split("'")[0].split("+")[0])
            except:
                pass
        if etype == "G" and pid:
            goals[pid] = goals.get(pid, 0) + 1
        elif etype == "AS" and pid:
            assists[pid] = assists.get(pid, 0) + 1
        elif etype == "S" and pid:
            if ev.get("description") == "ON":
                sub_on[pid] = min_v
            elif ev.get("description") == "OFF":
                sub_off[pid] = min_v
        elif etype == "B" and pid:
            if ev.get("description") == "Y":
                yc[pid] = yc.get(pid, 0) + 1
            elif ev.get("description") == "R":
                rc[pid] = rc.get(pid, 0) + 1

    fouls_lost = {}
    fouls_won = {}
    shots = {}
    shots_ot = {}
    offsides = {}

    for se in events:
        stype = se.get("type")
        pids = se.get("playerIds", [])
        if not pids:
            continue
        p0 = pids[0]
        if stype == "free kick lost":
            fouls_lost[p0] = fouls_lost.get(p0, 0) + 1
        elif stype == "free kick won":
            fouls_won[p0] = fouls_won.get(p0, 0) + 1
        elif stype in ["goal", "attempt saved", "miss", "attempt blocked"]:
            shots[p0] = shots.get(p0, 0) + 1
            if stype in ["goal", "attempt saved"]:
                shots_ot[p0] = shots_ot.get(p0, 0) + 1
        elif stype == "offside":
            offsides[p0] = offsides.get(p0, 0) + 1

    # Populate home & away player cards
    for idx, tl in enumerate(d.get("teamLists", [])):
        if not tl or not isinstance(tl, dict):
            continue
        side = "home" if idx == 0 else "away"
        lineup_p = tl.get("lineup", [])
        subs_p = tl.get("substitutes", [])

        # Process starters
        for p in lineup_p:
            pid = p.get("id")
            if not pid:
                continue
            mins = sub_off.get(pid, 90)
            player_stats[side].append({
                "id": pid,
                "name": p.get("name", {}).get("display", "Unknown"),
                "shirt": p.get("matchShirtNumber"),
                "position": p.get("matchPosition") or p.get("info", {}).get("position", "M"),
                "is_starter": True,
                "captain": p.get("captain", False),
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
            })

        # Process substitutes who actually played
        for p in subs_p:
            pid = p.get("id")
            if not pid or pid not in sub_on:
                continue
            mins = max(1, 90 - sub_on[pid])
            player_stats[side].append({
                "id": pid,
                "name": p.get("name", {}).get("display", "Unknown"),
                "shirt": p.get("matchShirtNumber"),
                "position": p.get("matchPosition") or p.get("info", {}).get("position", "M"),
                "is_starter": False,
                "captain": False,
                "minutes": mins,
                "goals": goals.get(pid, 0),
                "assists": assists.get(pid, 0),
                "shots": shots.get(pid, 0),
                "shots_ontarget": shots_ot.get(pid, 0),
                "fouls_committed": fouls_lost.get(pid, 0),
                "fouls_won": fouls_won.get(pid, 0),
                "offsides": offsides.get(pid, 0),
                "yellow_cards": yc.get(pid, 0),
                "red_cards": rc.get(pid, 0),
            })

    return {
        "metadata": metadata,
        "lineups": lineups,
        "team_stats": team_stats,
        "player_stats": player_stats,
        "events": events,
    }


@app.get("/api/predict")
def predict_match(home_id: int = Query(...), away_id: int = Query(...), season: Optional[str] = None):
    """
    Computes real-time micro-metrics and match predictions between two teams
    using trained models and the latest available team rolling statistics.
    Optionally scoped to a specific season (2024_25 or 2025_26).
    """
    if home_id == away_id:
        raise HTTPException(status_code=400, detail="Home and Away teams must be different.")

    home_meta = teams_dict.get(home_id)
    away_meta = teams_dict.get(away_id)
    if not home_meta or not away_meta:
        raise HTTPException(status_code=404, detail="Team not found.")

    feature_pool = df_features.copy()
    if season and "season" in feature_pool.columns and season != "all":
        season_subset = feature_pool[feature_pool["season"] == season]
        if not season_subset.empty:
            feature_pool = season_subset

    home_rows = feature_pool[feature_pool["home_id"] == home_id]
    away_rows = feature_pool[feature_pool["away_id"] == away_id]

    if home_rows.empty:
        home_rows = feature_pool[feature_pool["away_id"] == home_id]
    if away_rows.empty:
        away_rows = feature_pool[feature_pool["home_id"] == away_id]

    if home_rows.empty or away_rows.empty:
        # Fallback to full features if not in that season
        home_rows = df_features[df_features["home_id"] == home_id]
        away_rows = df_features[df_features["away_id"] == away_id]

    latest_home = home_rows.iloc[-1]
    latest_away = away_rows.iloc[-1]

    # Build simulated feature vector
    simulated_row = pd.Series(latest_home).to_dict()
    # Overwrite away team attributes with latest away data
    for col in latest_away.index:
        if col.startswith("away_"):
            simulated_row[col] = latest_away[col]

    simulated_df = pd.DataFrame([simulated_row])

    # 1. Corner Prediction
    c_features = corner_artifact["feature_names"]
    X_c = simulated_df[c_features]
    exp_corners = float(corner_artifact["model"].predict(X_c)[0])
    exp_corners = max(5.0, min(18.0, exp_corners))
    # Poisson probabilities
    prob_c85 = float((1.0 - poisson.cdf(8, exp_corners)) * 100)
    prob_c95 = float((1.0 - poisson.cdf(9, exp_corners)) * 100)
    prob_c105 = float((1.0 - poisson.cdf(10, exp_corners)) * 100)

    # 2. Throws Prediction
    t_features = throws_artifact["feature_names"]
    X_t = simulated_df[t_features]
    exp_throws = float(throws_artifact["model"].predict(X_t)[0])
    exp_throws = max(20.0, min(50.0, exp_throws))
    prob_t335 = float((1.0 - poisson.cdf(33, exp_throws)) * 100)
    prob_t365 = float((1.0 - poisson.cdf(36, exp_throws)) * 100)

    # 3. Saves Prediction
    s_features = saves_artifact["feature_names"]
    X_s = simulated_df[s_features]
    exp_saves = float(saves_artifact["model"].predict(X_s)[0])
    exp_saves = max(2.0, min(12.0, exp_saves))

    # 4. Outcome & Goals Prediction
    o_features = outcome_artifact["feature_names"]
    X_o = simulated_df[o_features]
    probs_1x2 = outcome_artifact["model_1x2"].predict_proba(X_o)[0]
    prob_h = float(probs_1x2[0] * 100)
    prob_d = float(probs_1x2[1] * 100)
    prob_a = float(probs_1x2[2] * 100)

    prob_o25 = float(outcome_artifact["model_o25"].predict_proba(X_o)[0][1] * 100)

    fav = home_meta["name"] if prob_h > prob_a else away_meta["name"]
    fav_label = f"{fav} Favori" if abs(prob_h - prob_a) > 10 else "Dengeli Mücadele"

    # 5. Offside Prediction
    exp_offsides = 3.26
    prob_off25 = 65.0
    prob_off35 = 45.0
    prob_off45 = 25.0
    home_off_share = 0.52

    if offside_artifact is not None:
        off_features = offside_artifact.get("feature_cols") or offside_artifact.get("feature_names", [])
        missing_cols = [c for c in off_features if c not in simulated_df.columns]
        for m in missing_cols:
            simulated_df[m] = 0.0
        X_off = simulated_df[off_features].fillna(0.0)
        try:
            exp_offsides = float(offside_artifact["model"].predict(X_off)[0])
            exp_offsides = max(0.5, min(10.0, exp_offsides))
            prob_off25 = float((1.0 - poisson.cdf(2, exp_offsides)) * 100)
            prob_off35 = float((1.0 - poisson.cdf(3, exp_offsides)) * 100)
            prob_off45 = float((1.0 - poisson.cdf(4, exp_offsides)) * 100)
        except Exception as e:
            logger.warning("Error predicting offsides: %s", e)

        # Dynamic home/away offside split based on team rates
        if "home_offsides_for_roll_5" in simulated_df.columns and "away_offsides_for_roll_5" in simulated_df.columns:
            h_off = float(simulated_df["home_offsides_for_roll_5"].iloc[0] or 1.6)
            a_off = float(simulated_df["away_offsides_for_roll_5"].iloc[0] or 1.6)
            if (h_off + a_off) > 0:
                home_off_share = max(0.2, min(0.8, h_off / (h_off + a_off)))

    # Splits (Home vs Away breakdown)
    home_c_share = 0.55
    home_t_share = 0.51
    home_s_share = 0.46

    return {
        "home_team": home_meta,
        "away_team": away_meta,
        "favorite_label": fav_label,
        "outcome": {
            "home_win_pct": round(prob_h, 1),
            "draw_pct": round(prob_d, 1),
            "away_win_pct": round(prob_a, 1),
            "over_2_5_goals_pct": round(prob_o25, 1),
        },
        "corners": {
            "expected_total": round(exp_corners, 1),
            "expected_home": round(exp_corners * home_c_share, 1),
            "expected_away": round(exp_corners * (1 - home_c_share), 1),
            "prob_over_8_5_pct": round(prob_c85, 1),
            "prob_over_9_5_pct": round(prob_c95, 1),
            "prob_over_10_5_pct": round(prob_c105, 1),
        },
        "throws": {
            "expected_total": round(exp_throws, 1),
            "expected_home": round(exp_throws * home_t_share, 1),
            "expected_away": round(exp_throws * (1 - home_t_share), 1),
            "prob_over_33_5_pct": round(prob_t335, 1),
            "prob_over_36_5_pct": round(prob_t365, 1),
        },
        "saves": {
            "expected_total": round(exp_saves, 1),
            "expected_home": round(exp_saves * home_s_share, 1),
            "expected_away": round(exp_saves * (1 - home_s_share), 1),
        },
        "shots": {
            "expected_total": round(exp_saves * 4.1, 1),
        },
        "offsides": {
            "expected_total": round(exp_offsides, 1),
            "expected_home": round(exp_offsides * home_off_share, 1),
            "expected_away": round(exp_offsides * (1 - home_off_share), 1),
            "prob_over_2_5_pct": round(prob_off25, 1),
            "prob_over_3_5_pct": round(prob_off35, 1),
            "prob_over_4_5_pct": round(prob_off45, 1),
        }
    }


@app.get("/api/benchmarks")
def get_benchmarks():
    """Returns saved model benchmark metrics and summary."""
    benchmarks_path = BASE_DIR / "reports" / "model_benchmarks.md"
    content = ""
    if benchmarks_path.exists():
        with open(benchmarks_path, "r", encoding="utf-8") as f:
            content = f.read()

    offside_report_path = BASE_DIR / "reports" / "model_benchmarks_offsides.md"
    if offside_report_path.exists():
        with open(offside_report_path, "r", encoding="utf-8") as f:
            content += "\n\n---\n\n" + f.read()

    return {
        "corner": corner_artifact["metrics"] if corner_artifact else {},
        "throws": throws_artifact["metrics"] if throws_artifact else {},
        "saves": saves_artifact["metrics"] if saves_artifact else {},
        "outcome": outcome_artifact["metrics"] if outcome_artifact else {},
        "offside": offside_artifact["metrics"] if offside_artifact else {},
        "markdown_report": content,
    }


@app.get("/")
def root():
    return {
        "service": "Premier League Model Engine API",
        "status": "online",
        "frontend": "http://localhost:5173"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
