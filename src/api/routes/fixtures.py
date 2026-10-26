"""Fixtures, standings, referees and recent-form routes."""

import json
import logging
import pandas as pd
from datetime import datetime
from fastapi import HTTPException
from src.config import DEFAULT_SEASON
from src.db.database import get_all_grouped_fixtures, get_db, get_referee_detail, get_referees_list
from typing import Any, Dict, Optional
from src.api import state
from src.api.prediction_service import compute_match_prediction
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("api_server")

@router.get("/api/fixtures")
def get_fixtures(limit: int = 800, search: Optional[str] = None, season: Optional[str] = None):
    """Returns list of matches, optionally filtered by season and search."""
    if state.df_matches.empty:
        return {"fixtures": []}

    df = state.df_matches.copy()
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

    # to_json turns NaN into null and timestamps into ISO strings; plain to_dict leaves NaN, which JSON rejects.
    records = json.loads(df.head(limit).to_json(orient="records", date_format="iso"))
    return {"fixtures": records, "total": len(records)}


def get_quick_fixture_prediction(home_id: int, away_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not home_id or not away_id or home_id == away_id:
        return None
    cache_key = (home_id, away_id, season)
    if cache_key in state._fixture_pred_cache:
        return state._fixture_pred_cache[cache_key]
    try:
        p = compute_match_prediction(home_id, away_id, season, include_lineup_analysis=False)
        summary = {
            "favorite_label": p["favorite_label"],
            "home_win_pct": p["outcome"]["home_win_pct"],
            "draw_pct": p["outcome"]["draw_pct"],
            "away_win_pct": p["outcome"]["away_win_pct"],
            "over_2_5_goals_pct": p["outcome"]["over_2_5_goals_pct"],
            "over_2_5_source": p["outcome"].get("over_2_5_source", "legacy"),
            "goals": p.get("goals", {}),
            "expected_corners": p["corners"]["expected_total"],
            "corners_model_skill": p["corners"]["model_skill"],
            "expected_cards": p["cards"]["expected_total"],
            "cards_model_skill": p["cards"]["model_skill"],
            "prob_over_3_5_cards": p["cards"]["prob_over_3_5_pct"],
            "referee_name": p["referee"]["name"],
        }
        state._fixture_pred_cache[cache_key] = summary
        return summary
    except Exception as e:
        logger.warning(f"Error generating quick prediction for {home_id} vs {away_id}: {e}")
        return None


# Bump when fixture fields are added so browsers drop their cached copies of older responses.
FIXTURES_SCHEMA = 3


@router.get("/api/fixtures/grouped")
def get_grouped_fixtures(season: str = DEFAULT_SEASON, competition: Optional[str] = None):
    """
    Returns fixtures grouped by Gameweek, and within each Gameweek, grouped by match day.
    Uses indexed SQLite database with instant response time and attached referee cards data.
    """
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39
    comp_key = comp.key if comp else "premier_league"

    cache_key = f"{comp_key}_{season}"
    if season not in (DEFAULT_SEASON, "current") and cache_key in state._historical_fixtures_grouped_cache:
        return state._historical_fixtures_grouped_cache[cache_key]

    db_fixtures = get_all_grouped_fixtures(season, competition_id=comp_id)
    from src.api.knockout import tie_summaries
    ties_by_match = tie_summaries(db_fixtures) if comp_id != 39 else {}
    raw_fixtures = []

    # Determine current active gameweek (the earliest gameweek with unplayed matches)
    unplayed_gws = [
        int(r["gameweek"]) for r in db_fixtures
        if not (r.get("status") == "COMPLETED" or (r.get("home_score") is not None and r.get("away_score") is not None))
    ]
    current_gw = min(unplayed_gws) if unplayed_gws else (int(db_fixtures[-1]["gameweek"]) if db_fixtures else 1)

    for r in db_fixtures:
        mid = int(r["match_id"])
        h_id = int(r["home_id"])
        a_id = int(r["away_id"])
        gw = int(r["gameweek"])
        h_score = r["home_score"]
        a_score = r["away_score"]
        is_completed = (r["status"] == "COMPLETED" or (h_score is not None and a_score is not None))
        match_stats = state.match_stats_map.get(mid, {})

        # Compute AI predictions strictly for uncompleted matches in the CURRENT gameweek only
        pred = (
            get_quick_fixture_prediction(h_id, a_id, r.get("season") or season)
            if (comp_id == 39 and not is_completed and gw == current_gw)
            else None
        )

        kickoff_ms = None
        if "kickoff_millis" in r and pd.notnull(r["kickoff_millis"]):
            try:
                kickoff_ms = int(r["kickoff_millis"])
            except (ValueError, TypeError):
                kickoff_ms = None

        raw_fixtures.append({
            "match_id": mid,
            "gameweek": gw,
            "kickoff_label": r.get("kickoff_label") or "",
            "kickoff_millis": kickoff_ms,
            "day_label": r.get("day_label") or "",
            "time_label": r.get("time_label") or "",
            "ground_name": r.get("ground_name") or "",
            "home_id": h_id,
            "home_name": r["home_name"],
            "home_abbr": r.get("home_abbr") or "",
            "home_logo": r.get("home_logo"),
            "home_score": h_score,
            "away_id": a_id,
            "away_name": r["away_name"],
            "away_abbr": r.get("away_abbr") or "",
            "away_logo": r.get("away_logo"),
            "away_score": a_score,
            "total_corners": r.get("total_corners"),
            "total_throws": r.get("total_throws"),
            "total_shots": r.get("total_shots"),
            "home_total_shots": match_stats.get("home_total_shots"),
            "away_total_shots": match_stats.get("away_total_shots"),
            "total_shots_ontarget": r.get("total_shots_ontarget"),
            "total_saves": r.get("total_saves"),
            "home_won_corners": r.get("home_won_corners"),
            "away_won_corners": r.get("away_won_corners"),
            "home_total_throws": r.get("home_total_throws"),
            "away_total_throws": r.get("away_total_throws"),
            "referee_name": r.get("referee_name") or "Atanmadı",
            "referee_id": r.get("referee_id"),
            "total_yellow_cards": r.get("total_yellow_cards"),
            "total_red_cards": r.get("total_red_cards"),
            "total_cards": r.get("total_cards"),
            "total_fouls": r.get("total_fouls"),
            "ref_avg_cards": r.get("ref_avg_cards"),
            "ref_strictness": r.get("ref_strictness"),
            "home_xg": round(float(r["statsapi_home_xg"]), 2) if r.get("statsapi_home_xg") is not None else (round(float(r["home_xg"]), 2) if r.get("home_xg") is not None else None),
            "away_xg": round(float(r["statsapi_away_xg"]), 2) if r.get("statsapi_away_xg") is not None else (round(float(r["away_xg"]), 2) if r.get("away_xg") is not None else None),
            "total_xg": round(float(r["statsapi_home_xg"] + r["statsapi_away_xg"]), 2)
                if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None
                else (round(float(r["total_xg"]), 2) if r.get("total_xg") is not None else None),
            "xg_source": r.get("xg_provider") if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None else ("Official" if r.get("home_xg") is not None else None),
            "xg_quality": r.get("statsapi_xg_quality"),
            "status": "COMPLETED" if is_completed else "UPCOMING",
            "stage": r.get("stage") or "league",
            "group": r.get("group_name"),
            "tie": ties_by_match.get(mid),
            "home_penalties": r.get("home_penalties"),
            "away_penalties": r.get("away_penalties"),
            "season": r.get("season") or season,
            "prediction": pred,
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
    stage_titles = {
        "league": "Lig Aşaması",
        "group": "Grup Aşaması",
        "playoff": "Play-off Eleme Turu",
        "r16": "Son 16 Turu",
        "qf": "Çeyrek Final (Son 8)",
        "sf": "Yarı Final",
        "final": "Final",
    }
    for gw in sorted(gw_groups.keys()):
        # Sort matches within each day chronologically
        for d in gw_groups[gw]:
            gw_groups[gw][d].sort(key=lambda m: state.parse_kickoff_datetime(m.get("kickoff_label", "")))

        # Sort days within the gameweek strictly chronologically by earliest match on each day
        sorted_day_keys = sorted(
            gw_groups[gw].keys(),
            key=lambda d: state.parse_kickoff_datetime(gw_groups[gw][d][0].get("kickoff_label", "")) if gw_groups[gw][d] else datetime.min
        )

        day_list = [{"day": d, "matches": gw_groups[gw][d]} for d in sorted_day_keys]
        first_match = day_list[0]["matches"][0] if day_list and day_list[0]["matches"] else {}
        gw_stage = first_match.get("stage", "league")
        title_label = stage_titles.get(gw_stage, f"Hafta {gw}")
        if gw_stage in ("league", "group"):
            title_label = f"Hafta {gw}"

        structured.append({
            "gameweek": gw,
            "stage": gw_stage,
            "title": title_label,
            "stage_title": stage_titles.get(gw_stage, "Lig Aşaması"),
            "days": day_list
        })

    # Determine current gameweek. A postponed match keeps an old week "unplayed" for months, so outside the Premier
    # League the current week is the first one with an upcoming match that has not been left behind by the calendar.
    current_gw = 1
    dates = {int(r["match_id"]): str(r.get("match_date") or "") for r in db_fixtures}
    today = datetime.utcnow().date().isoformat()
    fresh = (lambda m: dates.get(int(m["match_id"]), "") >= today) if comp_id != 39 else (lambda m: True)
    upcoming_gws = [
        gw for gw in sorted(gw_groups.keys())
        if any(m.get("status") == "UPCOMING" and fresh(m) for d in gw_groups[gw].values() for m in d)
    ] or [
        gw for gw in sorted(gw_groups.keys())
        if any(m.get("status") == "UPCOMING" for d in gw_groups[gw].values() for m in d)
    ]
    if upcoming_gws:
        current_gw = upcoming_gws[0]
    elif gw_groups:
        current_gw = max(gw_groups.keys())

    next_unplayed = next((f for f in raw_fixtures if f.get("status") == "UPCOMING" and fresh(f)), None) or next((f for f in raw_fixtures if f.get("status") == "UPCOMING"), None)
    next_match_info = None
    if next_unplayed:
        next_match_info = {
            "match_id": next_unplayed["match_id"],
            "gameweek": next_unplayed["gameweek"],
            "kickoff_label": next_unplayed["kickoff_label"],
            "kickoff_millis": next_unplayed.get("kickoff_millis"),
        }

    res = {
        "schema": FIXTURES_SCHEMA,
        "season": season,
        "competition": {
            "key": comp.key if comp else "premier_league",
            "id": comp_id,
            "name": comp.name if comp else "Premier League",
        },
        "gameweeks": structured,
        "total_matches": len(raw_fixtures),
        "current_gameweek": current_gw,
        "next_match": next_match_info,
    }
    if season not in (DEFAULT_SEASON, "current"):
        state._historical_fixtures_grouped_cache[cache_key] = res
    return res


@router.get("/api/fixtures/bracket")
def get_knockout_bracket(season: str = DEFAULT_SEASON, competition: Optional[str] = None):
    """Knockout bracket (play-off to final) of a UEFA competition; the league phase is not part of it."""
    from src.api.knockout import build_bracket
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    if comp is None or not comp.is_continental:
        raise HTTPException(status_code=404, detail="This competition has no knockout bracket")
    rows = [r for r in get_all_grouped_fixtures(season, competition_id=comp.id)]
    return {"season": season, "competition": {"key": comp.key, "id": comp.id, "name": comp.name}, **build_bracket(rows)}


@router.get("/api/referees")
def get_referees(season: str = DEFAULT_SEASON, search: Optional[str] = None, competition: Optional[str] = None):
    """Returns list of referees and card statistics from SQLite, filtered by competition."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39

    if comp_id != 39:
        from src.db.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        query = """
            SELECT 
                referee_name,
                COUNT(*) as matches_count,
                ROUND(SUM(total_yellow_cards), 1) as total_yellow_cards,
                ROUND(AVG(total_yellow_cards), 2) as avg_yellow_cards,
                ROUND(SUM(total_red_cards), 1) as total_red_cards,
                ROUND(AVG(total_red_cards), 2) as avg_red_cards,
                ROUND(SUM(total_cards), 1) as total_cards,
                ROUND(AVG(total_cards), 2) as avg_cards,
                ROUND(SUM(total_fouls), 1) as total_fouls,
                ROUND(AVG(total_fouls), 2) as avg_fouls,
                SUM(CASE WHEN total_cards > 3.5 THEN 1 ELSE 0 END) as over_3_5_cards_count,
                ROUND(SUM(CASE WHEN total_cards > 3.5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as over_3_5_pct,
                CASE 
                    WHEN AVG(total_cards) >= 4.5 THEN 'Cok Sıkı'
                    WHEN AVG(total_cards) >= 3.8 THEN 'Sıkı'
                    WHEN AVG(total_cards) <= 2.8 THEN 'Cok Rahat'
                    WHEN AVG(total_cards) <= 3.4 THEN 'Rahat'
                    ELSE 'Dengeli'
                END as strictness_label
            FROM matches
            WHERE competition_id = ? AND (season = ? OR ? = 'all')
              AND referee_name IS NOT NULL AND referee_name != 'Atanmadı' AND status = 'COMPLETED'
            GROUP BY referee_name
        """
        params = [comp_id, season, season]
        if search:
            query += " HAVING referee_name LIKE ?"
            params.append(f"%{search}%")
        query += " ORDER BY matches_count DESC, avg_cards DESC"
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return {"referees": rows}

    return {"referees": get_referees_list(season, search)}


@router.get("/api/referees/{name}")
def get_referee_profile(name: str, season: str = DEFAULT_SEASON, competition: Optional[str] = None):
    """Returns detailed profile and matches officiated by referee from SQLite."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39

    if comp_id != 39:
        from src.db.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM matches
            WHERE referee_name = ? AND competition_id = ? AND (season = ? OR ? = 'all')
            ORDER BY gameweek DESC, match_date DESC
        """, (name, comp_id, season, season))
        matches = [dict(r) for r in cursor.fetchall()]
        completed = [m for m in matches if m.get("status") == "COMPLETED"]
        m_count = len(completed)
        tot_cards = sum(m.get("total_cards") or 0.0 for m in completed)
        tot_fouls = sum(m.get("total_fouls") or 0.0 for m in completed)
        tot_y = sum(m.get("total_yellow_cards") or 0.0 for m in completed)
        tot_r = sum(m.get("total_red_cards") or 0.0 for m in completed)
        avg_c = round(tot_cards / m_count, 2) if m_count > 0 else None
        avg_f = round(tot_fouls / m_count, 2) if m_count > 0 else None
        strictness = None if avg_c is None else "Sıkı" if avg_c >= 4.0 else ("Rahat" if avg_c < 3.0 else "Dengeli")

        stats = {
            "referee_name": name,
            "season": season,
            "matches_count": m_count,
            "total_yellow_cards": tot_y,
            "avg_yellow_cards": round(tot_y / m_count, 2) if m_count > 0 else 0.0,
            "total_red_cards": tot_r,
            "avg_red_cards": round(tot_r / m_count, 2) if m_count > 0 else 0.0,
            "total_cards": tot_cards,
            "avg_cards": avg_c,
            "total_fouls": tot_fouls,
            "avg_fouls": avg_f,
            "strictness_label": strictness,
        }
        european = None
        if comp.is_domestic:
            from src.api.european_fixtures import referee_european_matches
            european = referee_european_matches(conn, name, season)
        conn.close()
        return {
            "referee_name": name,
            "selected_season": season,
            "season_stats": stats,
            "career_stats": stats,
            "matches_count": len(matches),
            "matches": matches,
            "team_breakdown": [],
            **({"european": european} if european is not None else {}),
        }

    return get_referee_detail(name, season)


def _official_ranks(comp_id: int, season: str) -> Dict[str, Dict[str, Any]]:
    from src.db.database import get_db
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT payload FROM external_competition_payloads WHERE competition_id = ? AND season = ? AND provider = 'UEFA' AND kind = 'standings'",
            (comp_id, season),
        ).fetchone()
    finally:
        conn.close()
    return json.loads(row["payload"]) if row else {}


@router.get("/api/standings")
def get_standings(season: str = DEFAULT_SEASON, competition: Optional[str] = None):
    """
    Computes standings table for the specified season and competition.
    Includes Played, Won, Drawn, Lost, GF, GA, GD, Points, and Last 5 Form,
    plus Home and Away breakdowns and tournament qualification zones.
    """
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39
    comp_key = comp.key if comp else "premier_league"

    cache_key = f"{comp_key}_{season}"
    if season not in (DEFAULT_SEASON, "current") and cache_key in state._historical_standings_cache:
        return state._historical_standings_cache[cache_key]

    matches_to_process = []
    teams_meta = {}

    if comp_id != 39:
        from src.db.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        # Fetch all teams in the competition
        cursor.execute(
            "SELECT DISTINCT home_id, home_name, home_abbr, home_logo, group_name FROM matches "
            "WHERE competition_id = ? AND stage IN ('league', 'group') AND (season = ? OR ? = 'all')",
            (comp_id, season, season),
        )
        for r in cursor.fetchall():
            teams_meta[int(r[0])] = {"id": int(r[0]), "name": r[1], "abbr": r[2] or "", "logo": r[3], "group": r[4]}

        # Fetch completed league phase matches
        cursor.execute("""
            SELECT gameweek, home_id, home_name, home_abbr, home_score, away_id, away_name, away_abbr, away_score
            FROM matches
            WHERE competition_id = ? AND (season = ? OR ? = 'all')
              AND status = 'COMPLETED' AND home_score IS NOT NULL AND away_score IS NOT NULL
              AND stage IN ('league', 'group')
            ORDER BY gameweek ASC, match_date ASC
        """, (comp_id, season, season))
        for r in cursor.fetchall():
            matches_to_process.append({
                "gameweek": int(r[0]),
                "home_id": int(r[1]),
                "home_name": r[2],
                "away_id": int(r[5]),
                "away_name": r[6],
                "home_score": int(r[4]),
                "away_score": int(r[8]),
            })
        conn.close()
    else:
        # Premier League logic
        if season == DEFAULT_SEASON and state.raw_fixtures_2627:
            for f in state.raw_fixtures_2627:
                teams = f.get("teams", [])
                if len(teams) < 2:
                    continue
                h_score = teams[0].get("score")
                a_score = teams[1].get("score")
                if h_score is None or a_score is None:
                    continue
                matches_to_process.append({
                    "gameweek": int(f.get("gameweek", {}).get("gameweek", 1)),
                    "home_id": int(teams[0]["team"]["id"]),
                    "home_name": teams[0]["team"]["name"],
                    "away_id": int(teams[1]["team"]["id"]),
                    "away_name": teams[1]["team"]["name"],
                    "home_score": int(h_score),
                    "away_score": int(a_score),
                })
        else:
            df = state.df_matches.copy()
            if season != "all" and "season" in df.columns:
                df = df[df["season"] == season]
            for _, r in df.iterrows():
                if pd.isnull(r.get("home_score")) or pd.isnull(r.get("away_score")):
                    continue
                matches_to_process.append({
                    "gameweek": int(r.get("gameweek") or 1),
                    "home_id": int(r["home_id"]),
                    "home_name": str(r["home_name"]),
                    "away_id": int(r["away_id"]),
                    "away_name": str(r["away_name"]),
                    "home_score": int(r["home_score"]),
                    "away_score": int(r["away_score"]),
                })

    # Sort matches chronologically by gameweek for accurate form
    matches_to_process.sort(key=lambda m: m["gameweek"])

    table = {}
    # Initialize all known teams from meta if present
    for tid, tmeta in teams_meta.items():
        table[tid] = {
            "id": tid,
            "name": tmeta["name"],
            "short": tmeta["name"],
            "abbr": tmeta["abbr"],
            "badge": tmeta.get("logo") or f"/badges/{tid}.svg",
            "group": tmeta.get("group"),
            "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "gf": 0, "ga": 0, "gd": 0, "points": 0,
            "form": [],
            "home": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
            "away": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
        }

    for m in matches_to_process:
        hid = m["home_id"]
        hname = m["home_name"]
        aid = m["away_id"]
        aname = m["away_name"]
        h_score = m["home_score"]
        a_score = m["away_score"]

        for tid, tname in [(hid, hname), (aid, aname)]:
            if tid not in table:
                t_meta = state.teams_dict.get(tid, {})
                table[tid] = {
                    "id": tid,
                    "name": tname,
                    "short": t_meta.get("short", tname),
                    "abbr": t_meta.get("abbr", ""),
                    "badge": f"/badges/{tid}.svg",
                    "played": 0, "won": 0, "drawn": 0, "lost": 0,
                    "gf": 0, "ga": 0, "gd": 0, "points": 0,
                    "form": [],
                    "home": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
                    "away": {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "gd": 0, "points": 0},
                }

        table[hid]["played"] += 1
        table[hid]["home"]["played"] += 1
        table[hid]["gf"] += h_score
        table[hid]["home"]["gf"] += h_score
        table[hid]["ga"] += a_score
        table[hid]["home"]["ga"] += a_score

        table[aid]["played"] += 1
        table[aid]["away"]["played"] += 1
        table[aid]["gf"] += a_score
        table[aid]["away"]["gf"] += a_score
        table[aid]["ga"] += h_score
        table[aid]["away"]["ga"] += h_score

        if h_score > a_score:
            table[hid]["won"] += 1
            table[hid]["home"]["won"] += 1
            table[hid]["points"] += 3
            table[hid]["home"]["points"] += 3
            table[hid]["form"].append("W")

            table[aid]["lost"] += 1
            table[aid]["away"]["lost"] += 1
            table[aid]["form"].append("L")
        elif h_score < a_score:
            table[aid]["won"] += 1
            table[aid]["away"]["won"] += 1
            table[aid]["points"] += 3
            table[aid]["away"]["points"] += 3
            table[aid]["form"].append("W")

            table[hid]["lost"] += 1
            table[hid]["home"]["lost"] += 1
            table[hid]["form"].append("L")
        else:
            table[hid]["drawn"] += 1
            table[hid]["home"]["drawn"] += 1
            table[hid]["points"] += 1
            table[hid]["home"]["points"] += 1
            table[hid]["form"].append("D")

            table[aid]["drawn"] += 1
            table[aid]["away"]["drawn"] += 1
            table[aid]["points"] += 1
            table[aid]["away"]["points"] += 1
            table[aid]["form"].append("D")

    standings_list = []
    for t in table.values():
        t["gd"] = t["gf"] - t["ga"]
        t["home"]["gd"] = t["home"]["gf"] - t["home"]["ga"]
        t["away"]["gd"] = t["away"]["gf"] - t["away"]["ga"]
        t["form"] = t["form"][-5:]  # Keep last 5 matches for form
        standings_list.append(t)

    # Sort standard rules: Points DESC -> GD DESC -> GF DESC (within a group when the phase is played in groups)
    has_groups = comp_id != 39 and any(t.get("group") for t in standings_list)
    official = _official_ranks(comp_id, season) if comp_id != 39 else {}
    # UEFA's table applies the tie-break rules (head-to-head etc.); trust it only when it describes the same results.
    use_official = bool(official) and all(
        str(t["id"]) in official and official[str(t["id"])]["played"] == t["played"] and official[str(t["id"])]["points"] == t["points"]
        for t in standings_list
    )
    if use_official:
        standings_list.sort(key=lambda x: (x.get("group") or "", official[str(x["id"])]["rank"]))
    else:
        standings_list.sort(key=lambda x: (x.get("group") or "", -x["points"], -x["gd"], -x["gf"]) if has_groups else (-x["points"], -x["gd"], -x["gf"]))

    rank_in_group: Dict[Any, int] = {}
    for rank, item in enumerate(standings_list, 1):
        if has_groups:
            rank_in_group[item["group"]] = rank = rank_in_group.get(item["group"], 0) + 1
        item["rank"] = rank
        if comp_id != 39 and has_groups:
            # Classic group stage: the winner goes straight to the last 16; a Champions League third place
            # drops into the Europa League knockout play-offs, a Europa League runner-up plays the play-off round.
            if rank == 1 or (rank == 2 and comp_id == 2):
                item["zone"], item["zone_label"] = "direct_r16", "Son 16 Turu"
            elif (rank == 3 and comp_id == 2) or (rank == 2 and comp_id == 3):
                item["zone"] = "playoff"
                item["zone_label"] = "Avrupa Ligi play-off" if comp_id == 2 else "Play-off Eleme Turu"
            else:
                item["zone"], item["zone_label"] = "eliminated", "Elendi"
        elif comp_id in (2, 3):
            # UEFA league phase (36 teams): top 8 straight to the last 16, 9-24 to the play-offs
            if rank <= 8:
                item["zone"] = "direct_r16"
                item["zone_label"] = "Son 16 Turu (Doğrudan)"
            elif rank <= 24:
                item["zone"] = "playoff"
                item["zone_label"] = "Play-off Eleme Turu"
            else:
                item["zone"] = "eliminated"
                item["zone_label"] = "Elendi"
        else:
            # National leagues: qualification and relegation places come from config/competitions.yaml
            zone = next((z for z in (comp.zones if comp else get_competition(39).zones) if z["from"] <= rank <= z["to"]), None)
            item["zone"] = zone["key"] if zone else "none"
            item["zone_label"] = zone["label"] if zone else ""

    res = {
        "season": season,
        "competition": {
            "key": comp.key if comp else "premier_league",
            "id": comp_id,
            "name": comp.name if comp else "Premier League",
        },
        "total_teams": len(standings_list),
        "format": "groups" if has_groups else "league",
        "groups": sorted({t["group"] for t in standings_list if t.get("group")}) if has_groups else [],
        "standings": standings_list
    }
    if season not in (DEFAULT_SEASON, "current"):
        state._historical_standings_cache[cache_key] = res
    return res


@router.get("/api/match/{match_id}/recent-form")
def get_match_recent_form(match_id: int):
    """Return each team's last five completed league results before a match."""
    # The current season standings are sourced from the live fixture feed, so
    # use that same source here to ensure current fixtures have pre-match form.
    if state.raw_fixtures_2627:
        current_fixtures = []
        for fixture in state.raw_fixtures_2627:
            fixture_teams = fixture.get("teams", [])
            if len(fixture_teams) < 2:
                continue
            current_fixtures.append({
                "match_id": int(fixture.get("match", {}).get("id") or fixture.get("match_id") or fixture.get("id") or 0),
                "gameweek": int((fixture.get("gameweek") or {}).get("gameweek", 1)),
                "kickoff": (fixture.get("kickoff") or {}).get("millis") or (fixture.get("kickoff") or {}).get("label", ""),
                "home_id": int(fixture_teams[0]["team"]["id"]),
                "away_id": int(fixture_teams[1]["team"]["id"]),
                "home_score": fixture_teams[0].get("score"),
                "away_score": fixture_teams[1].get("score"),
            })
        selected = next((fixture for fixture in current_fixtures if fixture["match_id"] == match_id), None)
        if selected:
            selected_kickoff = selected["kickoff"] or ""
            previous_fixtures = [
                fixture for fixture in current_fixtures
                if fixture["match_id"] != match_id
                and fixture["home_score"] is not None and fixture["away_score"] is not None
                and (fixture["gameweek"], fixture["kickoff"], fixture["match_id"])
                    < (selected["gameweek"], selected_kickoff, selected["match_id"])
                and (fixture["home_id"] in (selected["home_id"], selected["away_id"])
                     or fixture["away_id"] in (selected["home_id"], selected["away_id"]))
            ]
            previous_fixtures.sort(key=lambda fixture: (fixture["gameweek"], fixture["kickoff"], fixture["match_id"]), reverse=True)
            form = {str(selected["home_id"]): [], str(selected["away_id"]): []}
            for fixture in previous_fixtures:
                home_score = int(fixture["home_score"])
                away_score = int(fixture["away_score"])
                for team_id in (selected["home_id"], selected["away_id"]):
                    results = form[str(team_id)]
                    if len(results) >= 5:
                        continue
                    if team_id == fixture["home_id"]:
                        results.append("W" if home_score > away_score else "L" if home_score < away_score else "D")
                    elif team_id == fixture["away_id"]:
                        results.append("W" if away_score > home_score else "L" if away_score < home_score else "D")
            for results in form.values():
                results.reverse()
            return {"match_id": match_id, "season": DEFAULT_SEASON, "form": form}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT season, match_date, kickoff_label, home_id, away_id, home_score, away_score
        FROM matches
        WHERE match_id = ?
    """, (match_id,))
    selected = cursor.fetchone()
    if not selected:
        conn.close()
        raise HTTPException(status_code=404, detail="Match not found")

    season = selected["season"]
    cutoff_date = selected["match_date"] or ""
    cutoff_kickoff = selected["kickoff_label"] or ""
    teams = (int(selected["home_id"]), int(selected["away_id"]))
    cursor.execute("""
        SELECT match_id, match_date, kickoff_label, home_id, away_id, home_score, away_score
        FROM matches
        WHERE season = ? AND match_id != ? AND home_score IS NOT NULL AND away_score IS NOT NULL
          AND (match_date < ? OR (match_date = ? AND kickoff_label < ?))
          AND (home_id IN (?, ?) OR away_id IN (?, ?))
        ORDER BY match_date DESC, kickoff_label DESC, match_id DESC
    """, (season, match_id, cutoff_date, cutoff_date, cutoff_kickoff, *teams, *teams))
    previous_matches = [dict(row) for row in cursor.fetchall()]
    conn.close()

    form = {str(team_id): [] for team_id in teams}
    for previous in previous_matches:
        home_id = int(previous["home_id"])
        away_id = int(previous["away_id"])
        home_score = int(previous["home_score"])
        away_score = int(previous["away_score"])
        for team_id in teams:
            if len(form[str(team_id)]) >= 5:
                continue
            if team_id == home_id:
                result = "W" if home_score > away_score else "L" if home_score < away_score else "D"
            elif team_id == away_id:
                result = "W" if away_score > home_score else "L" if away_score < home_score else "D"
            else:
                continue
            form[str(team_id)].append(result)

    for results in form.values():
        results.reverse()
    return {"match_id": match_id, "season": season, "form": form}
