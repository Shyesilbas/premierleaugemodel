"""Fixtures, standings, referees and recent-form routes."""

import logging
import pandas as pd
from datetime import datetime
from fastapi import HTTPException
from src.config import DEFAULT_SEASON
from src.db.database import get_all_grouped_fixtures, get_db, get_referee_detail, get_referees_list
from typing import Any, Dict, Optional
from src.api import state
from src.api.routes.predict import predict_match
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

    records = df.head(limit).to_dict(orient="records")
    return {"fixtures": records, "total": len(records)}


def get_quick_fixture_prediction(home_id: int, away_id: int, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not home_id or not away_id or home_id == away_id:
        return None
    cache_key = (home_id, away_id, season)
    if cache_key in state._fixture_pred_cache:
        return state._fixture_pred_cache[cache_key]
    try:
        p = predict_match(home_id, away_id, season)
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


@router.get("/api/fixtures/grouped")
def get_grouped_fixtures(season: str = DEFAULT_SEASON):
    """
    Returns fixtures grouped by Gameweek, and within each Gameweek, grouped by match day.
    Uses indexed SQLite database with instant response time and attached referee cards data.
    """
    if season not in (DEFAULT_SEASON, "current") and season in state._historical_fixtures_grouped_cache:
        return state._historical_fixtures_grouped_cache[season]

    db_fixtures = get_all_grouped_fixtures(season)
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
            if (not is_completed and gw == current_gw)
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
            "home_score": h_score,
            "away_id": a_id,
            "away_name": r["away_name"],
            "away_abbr": r.get("away_abbr") or "",
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
            "home_xg": round(float(r["statsapi_home_xg"]), 2) if r.get("statsapi_home_xg") is not None else None,
            "away_xg": round(float(r["statsapi_away_xg"]), 2) if r.get("statsapi_away_xg") is not None else None,
            "total_xg": round(float(r["statsapi_home_xg"] + r["statsapi_away_xg"]), 2)
                if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None else None,
            "xg_source": r.get("xg_provider") if r.get("statsapi_home_xg") is not None and r.get("statsapi_away_xg") is not None else None,
            "xg_quality": r.get("statsapi_xg_quality"),
            "status": "COMPLETED" if is_completed else "UPCOMING",
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

    next_unplayed = next((f for f in raw_fixtures if f.get("status") == "UPCOMING"), None)
    next_match_info = None
    if next_unplayed:
        next_match_info = {
            "match_id": next_unplayed["match_id"],
            "gameweek": next_unplayed["gameweek"],
            "kickoff_label": next_unplayed["kickoff_label"],
            "kickoff_millis": next_unplayed.get("kickoff_millis"),
        }

    res = {
        "season": season,
        "gameweeks": structured,
        "total_matches": len(raw_fixtures),
        "current_gameweek": current_gw,
        "next_match": next_match_info,
    }
    if season not in (DEFAULT_SEASON, "current"):
        state._historical_fixtures_grouped_cache[season] = res
    return res


@router.get("/api/referees")
def get_referees(season: str = DEFAULT_SEASON, search: Optional[str] = None):
    """Returns list of Premier League referees and card statistics from SQLite."""
    return {"referees": get_referees_list(season, search)}


@router.get("/api/referees/{name}")
def get_referee_profile(name: str, season: str = DEFAULT_SEASON):
    """Returns detailed profile and matches officiated by referee from SQLite."""
    return get_referee_detail(name, season)


@router.get("/api/standings")
def get_standings(season: str = DEFAULT_SEASON):
    """
    Computes Premier League standings table for the specified season.
    Includes Played, Won, Drawn, Lost, GF, GA, GD, Points, and Last 5 Form,
    plus Home and Away breakdowns.
    """
    if season not in (DEFAULT_SEASON, "current") and season in state._historical_standings_cache:
        return state._historical_standings_cache[season]

    matches_to_process = []

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

    # Sort standard PL rules: Points DESC -> GD DESC -> GF DESC
    standings_list.sort(key=lambda x: (x["points"], x["gd"], x["gf"]), reverse=True)

    for rank, item in enumerate(standings_list, 1):
        item["rank"] = rank

    res = {
        "season": season,
        "total_teams": len(standings_list),
        "standings": standings_list
    }
    if season not in (DEFAULT_SEASON, "current"):
        state._historical_standings_cache[season] = res
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
