"""Player search, profile, market value and rating routes."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.analytics.player_ratings import calculate_single_match_score, get_match_bookings_map
from src.api import state
from src.config import SEASON_ORDER
from src.db.database import get_db

router = APIRouter()
logger = logging.getLogger("api_server")

@router.get("/api/players")
def get_players(team_id: Optional[int] = None, search: Optional[str] = None, season: Optional[str] = None, limit: int = 100):
    """Returns player directory with optional filters including season-accurate club rosters."""
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


@router.get("/api/players/profile")
def get_player_profile(player_id: int, season: Optional[str] = "all"):
    """
    Returns player profile and their match-by-match preview log:
    including opponent, score, minutes played, goals, and assists.
    """
    player = next((p for p in state.all_players if p["id"] == player_id), None)
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
        conn = get_db()
        last_name = p_name.split()[-1] if p_name else ""
        row = conn.execute(
            "SELECT player_id, market_value, market_value_eur, position, age, nationality FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
            (p_name, f"%{last_name}%")
        ).fetchone()
        if row:
            mv_eur = row["market_value_eur"]
            tm_mv = {
                "tm_id": row["player_id"],
                "market_value_eur": mv_eur,
                "formatted": f"€{mv_eur:,.1f}M" if mv_eur >= 1.0 else f"€{int(mv_eur*1000)}k"
            }
        conn.close()
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

    return {
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
            last = name.split()[-1] if name else ""
            tm_row = conn.execute(
                "SELECT * FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
                (name, f"%{last}%")
            ).fetchone()

        if not tm_row:
            # Check all_players registry by ID
            pl_match = next((p for p in state.all_players if str(p.get("id")) == str(player_id)), None)
            if pl_match:
                pname = pl_match.get("name") or f"{pl_match.get('firstName', '')} {pl_match.get('lastName', '')}".strip()
                last = pname.split()[-1] if pname else ""
                tm_row = conn.execute(
                    "SELECT * FROM player_market_values WHERE LOWER(name) = LOWER(?) OR LOWER(name) LIKE LOWER(?) ORDER BY market_value DESC LIMIT 1",
                    (pname, f"%{last}%")
                ).fetchone()

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
                "SELECT season, market_value, market_value_eur, age FROM player_market_values WHERE player_id = ? OR LOWER(name) = LOWER(?) ORDER BY season ASC",
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
