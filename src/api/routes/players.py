"""Player search, profile, market value and rating routes."""

import json
import logging
from contextlib import closing
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from src.analytics.player_ratings import calculate_single_match_score, get_match_bookings_map
from src.api import state
from src.api.competition_squads import _finalize_compare_bucket, _new_compare_bucket
from src.config import DB_PATH, DEFAULT_SEASON, SEASON_ORDER, SEASONS
from src.db.database import get_db

router = APIRouter()
logger = logging.getLogger("api_server")


def _lookup_tm_player_by_name(conn: Any, player_name: str) -> Any:
    """Resolve a Transfermarkt player row, preferring an exact name match over a surname fallback."""
    clean_name = (player_name or "").strip()
    if not clean_name:
        return None
    last_name = clean_name.split()[-1]
    return conn.execute(
        """
        SELECT * FROM player_market_values
        WHERE competition_id = 39 AND (LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?))
        ORDER BY (LOWER(name) = LOWER(?)) DESC, market_value DESC
        LIMIT 1
        """,
        (clean_name, f"%{last_name}%", clean_name),
    ).fetchone()

@router.get("/api/players")
def get_players(team_id: Optional[int] = None, search: Optional[str] = None, season: Optional[str] = None, competition: Optional[str] = None, limit: int = 100):
    """Returns player directory with optional filters including season-accurate club rosters."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39

    if comp_id != 39:
        from src.api.competition_squads import list_squad_players
        conn = get_db()
        try:
            return list_squad_players(conn, comp_id, season if season and season != "all" else comp.default_season, team_id, search, limit)
        finally:
            conn.close()

    result = state.all_players
    if season and season != "all":
        s_map = state.get_season_players_map(season)
        updated_result = []
        for p in result:
            pid = p.get("id")
            if pid in s_map:
                p_copy = dict(p)
                p_copy["teamId"] = s_map[pid]["teamId"]
                if s_map[pid]["teamName"]:
                    p_copy["teamName"] = s_map[pid]["teamName"]
                updated_result.append(p_copy)
        result = updated_result

    if team_id:
        result = [p for p in result if p.get("teamId") == team_id]
    if search:
        s = search.lower()
        result = [p for p in result if s in p.get("name", "").lower() or s in p.get("teamName", "").lower()]

    return {"players": result[:limit], "total": len(result)}


def _build_pl_compare_data() -> Dict[str, Any]:
    """Aggregate Premier League player profiles and per-season stats from cached runtime data."""
    if state._player_logs_dict is None and state.players_logs_file.exists():
        state.get_player_match_logs(0)
    logs_map = state._player_logs_dict or {}
    cards_dict = state.get_player_cards_dict()
    bookings_map = get_match_bookings_map()

    mv_by_name: Dict[str, Dict[str, float]] = {}
    mv_latest_by_name: Dict[str, float] = {}
    mv_by_surname: Dict[str, float] = {}
    with closing(get_db()) as conn:
        rows = conn.execute(
            "SELECT LOWER(TRIM(name)) AS lname, season, market_value_eur "
            "FROM player_market_values WHERE competition_id = 39 ORDER BY season ASC"
        ).fetchall()
        for r in rows:
            lname = r["lname"]
            mv_eur = r["market_value_eur"]
            if not lname or mv_eur is None:
                continue
            val = float(mv_eur)
            mv_by_name.setdefault(lname, {})[r["season"]] = val
            mv_latest_by_name[lname] = val
            parts = lname.split()
            if len(parts) > 1:
                mv_by_surname.setdefault(parts[-1], val)

    def _mv_for(name: str, season_key: str) -> Optional[float]:
        lname = (name or "").lower().strip()
        if not lname:
            return None
        if season_key != "all" and season_key in mv_by_name.get(lname, {}):
            return mv_by_name[lname][season_key]
        if lname in mv_latest_by_name:
            return mv_latest_by_name[lname]
        parts = lname.split()
        return mv_by_surname.get(parts[-1]) if parts else None

    seasons_seen = set(SEASONS)
    averages: Dict[str, Dict[str, Any]] = {}
    profiles: List[Dict[str, Any]] = []

    for player in state.all_players:
        pid = player.get("id")
        if pid is None:
            continue
        pid_str = str(pid)
        p_name = (
            player.get("name")
            or f"{player.get('firstName', '')} {player.get('lastName', '')}".strip()
        )
        pos = player.get("position") or "M"
        raw_logs = logs_map.get(pid_str, logs_map.get(pid, []))

        sorted_logs = sorted(
            raw_logs,
            key=lambda x: (SEASON_ORDER.get(x.get("season", ""), 0), float(x.get("gameweek") or 0)),
        )
        buckets: Dict[str, Dict[str, Any]] = {}
        for m in sorted_logs:
            m_season = m.get("season")
            if not m_season:
                continue
            seasons_seen.add(m_season)
            mins = int(m.get("minutes_played") or 0)
            goals = int(m.get("goals") or 0)
            assists = int(m.get("assists") or 0)
            t_score = m.get("team_score")
            o_score = m.get("opp_score")
            tid = m.get("team_id")
            tname = m.get("team_name")
            score_obj = calculate_single_match_score(m, pos, bookings_map, int(pid))
            rating = score_obj.get("overall") if score_obj else None

            for bkey in (m_season, "all"):
                b = buckets.setdefault(bkey, _new_compare_bucket(False))
                b["appearances"] += 1
                if m.get("started"):
                    b["starts"] += 1
                b["minutes"] += mins
                b["goals"] += goals
                b["assists"] += assists
                if o_score is not None and float(o_score) == 0.0 and mins >= 60:
                    b["clean_sheets"] += 1
                if t_score is not None and o_score is not None and float(t_score) > float(o_score):
                    b["wins"] += 1
                if rating is not None:
                    b["ratings"].append(float(rating))
                if tid is not None and tid not in b["teams"]:
                    b["teams"].append(tid)
                if tname and tname not in b["team_names"]:
                    b["team_names"].append(tname)

        if not buckets:
            continue

        all_y, all_r = 0, 0
        for skey, b in buckets.items():
            if skey == "all":
                continue
            cinfo = cards_dict.get(f"{skey}_{pid_str}", {})
            y = int(cinfo.get("yellow", 0))
            r = int(cinfo.get("red", 0))
            b["yellow"] = y
            b["red"] = r
            all_y += y
            all_r += r
        if "all" in buckets:
            buckets["all"]["yellow"] = all_y
            buckets["all"]["red"] = all_r

        p_avgs: Dict[str, Any] = {}
        for skey, b in buckets.items():
            p_avgs[skey] = _finalize_compare_bucket(b, _mv_for(p_name, skey))
        averages[pid_str] = p_avgs

        latest_team_id = buckets["all"]["teams"][-1] if buckets.get("all", {}).get("teams") else player.get("teamId")
        latest_team_name = (
            buckets["all"]["team_names"][-1]
            if buckets.get("all", {}).get("team_names")
            else (player.get("teamName") or "")
        )
        mv_eur = _mv_for(p_name, DEFAULT_SEASON)
        profiles.append({
            "id": pid,
            "name": p_name,
            "position": pos,
            "teamId": latest_team_id,
            "teamName": latest_team_name,
            "teamBadge": f"/badges/{latest_team_id}.svg" if latest_team_id else None,
            "shirt": player.get("shirt"),
            "country": player.get("country"),
            "age": None,
            "photo_url": state.resolve_player_photo(pid, player),
            "market_value_eur": mv_eur,
            "market_value_formatted": _format_player_mv(mv_eur) if mv_eur is not None else None,
        })

    def _pl_sort_key(p: Dict[str, Any]) -> Tuple[int, float, int, int, str]:
        p_avgs = averages.get(str(p["id"]), {})
        active = 1 if DEFAULT_SEASON in p_avgs else 0
        mv = float(p.get("market_value_eur") or 0.0)
        cur = p_avgs.get(DEFAULT_SEASON) or p_avgs.get("all") or {}
        return (-active, -mv, -int(cur.get("goals_plus_assists", 0)), -int(cur.get("appearances", 0)), p["name"])

    profiles.sort(key=_pl_sort_key)
    ordered_seasons = sorted(
        [s for s in seasons_seen if s in SEASON_ORDER],
        key=lambda s: SEASON_ORDER[s],
        reverse=True,
    )
    return {
        "competition": "premier_league",
        "seasons": ordered_seasons + ["all"],
        "profiles": profiles,
        "averages": averages,
    }


@router.get("/api/players/compare-data")
def get_players_compare_data(competition: Optional[str] = None):
    """Return pre-aggregated player directory profiles and per-season statistics for fast comparison."""
    from src.competitions.registry import get_competition

    try:
        comp = get_competition(competition) if competition else get_competition("premier_league")
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown competition")

    db_mtime = DB_PATH.stat().st_mtime_ns if DB_PATH.exists() else 0
    cache_key = (comp.key, state._loaded_data_version, db_mtime)
    cached = state._player_compare_cache.get(cache_key)
    if cached is not None:
        return cached

    if comp.id != 39:
        from src.api.competition_squads import build_compare_data

        with closing(get_db()) as conn:
            result = build_compare_data(conn, comp.id, comp.key, comp.default_season)
    else:
        result = _build_pl_compare_data()

    # Keep only fresh cache entries per competition
    stale_keys = [k for k in state._player_compare_cache if k[0] == comp.key]
    for k in stale_keys:
        state._player_compare_cache.pop(k, None)
    state._player_compare_cache[cache_key] = result
    return result


@router.get("/api/players/profile")
def get_player_profile(player_id: str, season: Optional[str] = "all", competition: Optional[str] = None):
    """
    Returns player profile and their match-by-match preview log:
    including opponent, score, minutes played, goals, and assists.
    """
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    if comp and comp.id != 39:
        from src.api.competition_squads import build_player_profile
        conn = get_db()
        try:
            profile = build_player_profile(conn, comp.id, season if season and season != "all" else comp.default_season, player_id)
            if profile is not None and comp.is_domestic:
                # A national league's player also appears in Europe: his UCL / UEL games, matched by name inside his club.
                from src.api.european_fixtures import COMPETITIONS, player_european_log
                for match in profile["matches"]:
                    match["competition"] = COMPETITIONS[comp.id]
                club = profile["player"].get("teamName")
                profile["european"] = player_european_log(conn, profile["player"].get("name") or "", {profile["season"]: {club}} if club else {})
        finally:
            conn.close()
        if profile is None:
            raise HTTPException(status_code=404, detail="Player not found in this competition")
        return profile

    player = next((p for p in state.all_players if str(p.get("id")) == str(player_id)), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    raw_logs = state.get_player_match_logs(player_id)
    if season and season != "all":
        logs = [m for m in raw_logs if m.get("season") == season]
    else:
        logs = raw_logs

    # Clone player dict and ensure teamId and teamName match the active season
    player_data = dict(player)
    active_logs = logs if logs else raw_logs
    if active_logs:
        sorted_active = sorted(
            active_logs, 
            key=lambda x: (SEASON_ORDER.get(x.get("season", ""), 0), float(x.get("gameweek") or 0))
        )
        latest_match = sorted_active[-1]
        if latest_match.get("team_id"):
            player_data["teamId"] = latest_match["team_id"]
    # Fetch authentic Transfermarkt player market value
    tm_mv = None
    p_name = player_data.get("name") or f"{player_data.get('firstName', '')} {player_data.get('lastName', '')}".strip()
    try:
        with closing(get_db()) as conn:
            row = _lookup_tm_player_by_name(conn, p_name)
            if row:
                mv_eur = row["market_value_eur"]
                tm_mv = {
                    "tm_id": row["player_id"],
                    "market_value_eur": mv_eur,
                    "formatted": f"€{mv_eur:,.1f}M" if mv_eur >= 1.0 else f"€{int(mv_eur*1000)}k"
                }
    except Exception as e:
        logger.warning(f"Error fetching player market value: {e}")

    player_data["market_value"] = tm_mv

    tot_mins = sum(m.get("minutes_played", 0) for m in logs)
    tot_goals = sum(m.get("goals", 0) for m in logs)
    tot_assists = sum(m.get("assists", 0) for m in logs)

    bookings_map = get_match_bookings_map()
    pos = player.get("position") or "M"

    enriched_matches = []
    valid_ratings = []
    for m in logs:
        m_copy = dict(m)
        m_score = calculate_single_match_score(m_copy, pos, bookings_map, player_id)
        if m_score is not None and m_score.get("overall") is not None:
            m_copy["rating"] = m_score["overall"]
            valid_ratings.append(m_score["overall"])
        else:
            m_copy["rating"] = None
        enriched_matches.append(m_copy)

    avg_rating = round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else None

    # Champions League / Europa League games, matched by name inside the clubs he played for that season.
    from src.api.european_fixtures import player_european_log
    clubs_by_season: Dict[str, set] = {}
    for m in logs:
        if m.get("season") and m.get("team_name"):
            clubs_by_season.setdefault(m["season"], set()).add(m["team_name"])
    conn = get_db()
    try:
        european = player_european_log(conn, p_name, clubs_by_season)
    finally:
        conn.close()

    return {
        "european": european,
        "player": player_data,
        "season": season,
        "season_stats": {
            "appearances": len(logs),
            "minutes": tot_mins,
            "goals": tot_goals,
            "assists": tot_assists,
            "average_rating": avg_rating,
            "rated_matches_count": len(valid_ratings),
        },
        "matches": enriched_matches,
    }


TR_MONTHS = {
    '01': 'Oca', '02': 'Şub', '03': 'Mar', '04': 'Nis', '05': 'May', '06': 'Haz',
    '07': 'Tem', '08': 'Ağu', '09': 'Eyl', '10': 'Eki', '11': 'Kas', '12': 'Ara'
}


def _format_date_tr(iso_date: str) -> str:
    try:
        parts = iso_date.split('-')
        return f"{int(parts[2])} {TR_MONTHS.get(parts[1], parts[1])} {parts[0]}"
    except Exception:
        return iso_date


def _format_player_mv(mv_eur: Optional[float]) -> str:
    if mv_eur is None:
        return "—"
    if mv_eur >= 1000.0:
        return f"€{mv_eur/1000:.2f}B"
    if mv_eur >= 1.0:
        return f"€{mv_eur:,.1f}M"
    return f"€{int(mv_eur * 1000)}k"


@router.get("/api/players/{player_id}/market-value-history")
def get_player_market_value_history(player_id: str, name: Optional[str] = None):
    """
    Returns authentic career market value progression curve & chronological history
    for a player, sourced from Transfermarkt career evaluations with SQLite fallback.
    """
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_market_value_history_cache (
                tm_id TEXT PRIMARY KEY,
                player_name TEXT,
                data_json TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

        # 1. Resolve Transfermarkt player record
        tm_row = conn.execute(
            "SELECT * FROM player_market_values WHERE player_id = ? ORDER BY season DESC LIMIT 1",
            (str(player_id),)
        ).fetchone()

        if not tm_row and name:
            tm_row = _lookup_tm_player_by_name(conn, name)

        if not tm_row:
            # Check all_players registry by ID
            pl_match = next((p for p in state.all_players if str(p.get("id")) == str(player_id)), None)
            if pl_match:
                pname = pl_match.get("name") or f"{pl_match.get('firstName', '')} {pl_match.get('lastName', '')}".strip()
                tm_row = _lookup_tm_player_by_name(conn, pname)

        tm_id = str(tm_row["player_id"]) if tm_row else (str(player_id) if str(player_id).isdigit() and len(str(player_id)) >= 5 else None)
        resolved_name = tm_row["name"] if tm_row else (name or f"Oyuncu {player_id}")
        resolved_pos = tm_row["position"] if tm_row else None
        resolved_team_id = tm_row["team_id"] if tm_row else None

        # 2. Check SQLite cache
        cached_data = None
        if tm_id:
            c_row = conn.execute(
                "SELECT data_json FROM player_market_value_history_cache WHERE tm_id = ?",
                (tm_id,)
            ).fetchone()
            if c_row and c_row["data_json"]:
                try:
                    cached_data = json.loads(c_row["data_json"])
                except Exception:
                    cached_data = None

        # 3. If not cached, fetch from Transfermarkt API
        if not cached_data and tm_id:
            try:
                import urllib.request
                url = f"https://transfermarkt-api.fly.dev/players/{tm_id}/market_value"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    cached_data = json.loads(resp.read().decode())
                    conn.execute(
                        "INSERT OR REPLACE INTO player_market_value_history_cache (tm_id, player_name, data_json, updated_at) VALUES (?, ?, ?, datetime('now'))",
                        (tm_id, resolved_name, json.dumps(cached_data))
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Could not fetch TM market value for player {tm_id}: {e}")

        # 4. Parse history points
        raw_history = (cached_data or {}).get("marketValueHistory", [])
        history_points = []
        prev_val = None

        if raw_history:
            for item in raw_history:
                mv_raw = item.get("marketValue", 0)
                mv_eur = round(mv_raw / 1_000_000, 2)
                chg_pct = round(((mv_eur - prev_val) / prev_val) * 100, 1) if prev_val and prev_val > 0 else None
                chg_diff = round(mv_eur - prev_val, 2) if prev_val is not None else None
                prev_val = mv_eur
                dt = item.get("date", "")

                history_points.append({
                    "date": dt,
                    "year": dt.split("-")[0] if "-" in dt else "",
                    "date_formatted": _format_date_tr(dt),
                    "age": item.get("age"),
                    "club_name": item.get("clubName") or "Kulüp",
                    "market_value": mv_raw,
                    "market_value_eur": mv_eur,
                    "formatted": _format_player_mv(mv_eur),
                    "change_pct": chg_pct,
                    "change_diff": chg_diff,
                })
        else:
            # Fallback to SQLite seasonal records
            seasonal_rows = conn.execute(
                "SELECT season, market_value, market_value_eur, age FROM player_market_values WHERE player_id = ? OR (competition_id = 39 AND LOWER(name) = LOWER(?)) ORDER BY season ASC",
                (tm_id or "", resolved_name)
            ).fetchall()
            for s_row in seasonal_rows:
                mv_eur = s_row["market_value_eur"]
                chg_pct = round(((mv_eur - prev_val) / prev_val) * 100, 1) if prev_val and prev_val > 0 else None
                chg_diff = round(mv_eur - prev_val, 2) if prev_val is not None else None
                prev_val = mv_eur
                s_label = s_row["season"].replace("_", "/")
                history_points.append({
                    "date": s_row["season"],
                    "year": s_row["season"].split("_")[0],
                    "date_formatted": f"{s_label} Sezonu",
                    "age": s_row["age"],
                    "club_name": "Premier League",
                    "market_value": s_row["market_value"],
                    "market_value_eur": mv_eur,
                    "formatted": _format_player_mv(mv_eur),
                    "change_pct": chg_pct,
                    "change_diff": chg_diff,
                })

        first_point = history_points[0] if history_points else None
        current_point = history_points[-1] if history_points else None
        peak_point = max(history_points, key=lambda x: x["market_value_eur"]) if history_points else None

        total_growth_pct = None
        total_growth_diff = None
        if first_point and current_point and first_point["market_value_eur"] > 0:
            total_growth_pct = round(((current_point["market_value_eur"] - first_point["market_value_eur"]) / first_point["market_value_eur"]) * 100, 1)
            total_growth_diff = round(current_point["market_value_eur"] - first_point["market_value_eur"], 2)

        team_meta = state.teams_dict.get(resolved_team_id, {}) if resolved_team_id else {}
        team_badge = team_meta.get("badge") or (f"/badges/{resolved_team_id}.svg" if resolved_team_id else None)

        return {
            "player_id": player_id,
            "tm_id": tm_id,
            "name": resolved_name,
            "position": resolved_pos,
            "team_id": resolved_team_id,
            "team_name": team_meta.get("name"),
            "team_badge": team_badge,
            "current_value": current_point,
            "peak_value": peak_point,
            "first_value": first_point,
            "total_growth_pct": total_growth_pct,
            "total_growth_diff": total_growth_diff,
            "evaluations_count": len(history_points),
            "history": history_points,
        }
    finally:
        conn.close()
