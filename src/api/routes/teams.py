"""Team, staff, manager, transfer and tactical routes."""

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None
import json
import logging
import pandas as pd
import re
import sqlite3
import urllib.request
from datetime import datetime
from fastapi import HTTPException
from src.analytics.team_attackers import get_team_attacking_leaders
from src.analytics.team_scenarios import get_team_scenario_profile
from src.analytics.team_tactics import get_team_tactical_profile
from src.config import DATA_DIR, DEFAULT_SEASON
from src.db.database import get_all_grouped_fixtures, get_db
from typing import Any, Dict, List, Optional, Tuple
from src.api import state
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("api_server")

PREMIER_LEAGUE_ID = 39


def _competition_id(competition: Optional[str]) -> int:
    """Resolve a competition key to its id; no key means the Premier League."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    return comp.id if comp else PREMIER_LEAGUE_ID


def _competition_team_name(team_id: Optional[int], comp_id: int) -> str:
    if team_id is None:
        return ""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT home_name AS n FROM matches WHERE home_id = ? AND competition_id = ? "
            "UNION SELECT away_name FROM matches WHERE away_id = ? AND competition_id = ? LIMIT 1",
            (team_id, comp_id, team_id, comp_id),
        ).fetchone()
    finally:
        conn.close()
    return row["n"] if row else ""

@router.get("/api/teams/staff")
def get_team_staff(season: str = DEFAULT_SEASON, team_id: Optional[int] = None, competition: Optional[str] = None):
    """Return season staff, falling back to archived source data for older seasons."""
    comp_id = _competition_id(competition)
    if comp_id != PREMIER_LEAGUE_ID:
        from src.api.competition_squads import club_managers
        conn = get_db()
        try:
            managers = club_managers(conn, comp_id, season)
        finally:
            conn.close()
        if team_id is None:
            return {"season": season, "managers": {str(tid): name for tid, name in managers.items()}}
        manager = managers.get(team_id)
        officials = [{"id": f"mgr_{team_id}", "role": "Manager", "active": True, "name": {"display": manager}}] if manager else []
        return {
            "season": season,
            "team_id": team_id,
            "staff": {"team_name": _competition_team_name(team_id, comp_id), "officials": officials, "players": []},
        }

    staff_path = DATA_DIR / "processed" / "team_staff.json"
    raw_staff_path = DATA_DIR / "processed" / "team_staff_raw.json"
    manager_rosters_path = DATA_DIR / "processed" / "team_manager_rosters.json"
    if not staff_path.exists():
        raise HTTPException(status_code=404, detail="Team staff data not available")
    try:
        with staff_path.open("r", encoding="utf-8") as stream:
            staff_by_season = json.load(stream)
        raw_staff_by_season = {}
        if raw_staff_path.exists():
            with raw_staff_path.open("r", encoding="utf-8") as stream:
                raw_staff_by_season = json.load(stream)
        manager_rosters = {}
        if manager_rosters_path.exists():
            with manager_rosters_path.open("r", encoding="utf-8") as stream:
                manager_rosters = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read team staff data")
        raise HTTPException(status_code=500, detail="Could not read team staff data") from exc

    # The normalized file currently has complete coverage only for 2026/27;
    # archived PulseLive responses contain the older seasons.
    season_staff = {
        **raw_staff_by_season.get(season, {}),
        **staff_by_season.get(season, {}),
    }
    season_manager_roster = manager_rosters.get(season, {}).get("managers", {})
    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    season_changes = []
    if changes_path.exists():
        try:
            with changes_path.open("r", encoding="utf-8") as stream:
                season_changes = json.load(stream).get(season, {}).get("events", [])
        except (OSError, json.JSONDecodeError):
            logger.exception("Could not read manager change data for staff fallback")

    for event in season_changes:
        current_team_id = str(event.get("team_id", ""))
        if current_team_id and current_team_id not in season_staff:
            season_staff[current_team_id] = {"team_name": event.get("team_name", ""), "officials": []}
    for current_team_id, entry in season_manager_roster.items():
        season_staff.setdefault(current_team_id, {"team_name": entry.get("team_name", ""), "officials": []})

    def add_manager_fallback(current_team_id: str, staff: Dict[str, Any]) -> Dict[str, Any]:
        officials = list(staff.get("officials") or [])
        has_manager = any(
            str(official.get("role", "")).lower() == "manager"
            and (official.get("name") or {}).get("display")
            for official in officials
        )
        if not has_manager:
            roster_entry = season_manager_roster.get(current_team_id)
            manager_name = (roster_entry or {}).get("name")
            if not manager_name:
                appointments = [
                    event for event in season_changes
                    if str(event.get("team_id")) == current_team_id and event.get("incoming_manager")
                ]
                latest = max(appointments, key=lambda event: event.get("appointment_date", "")) if appointments else None
                manager_name = (latest or {}).get("incoming_manager")
            if manager_name:
                officials.append({
                    "role": "Manager",
                    "active": True,
                    "name": {"display": manager_name},
                    "inferred_from_manager_changes": not bool(roster_entry),
                })
        return {**staff, "officials": officials}

    if team_id is not None:
        staff = season_staff.get(str(team_id))
        if staff is None and not any(str(event.get("team_id")) == str(team_id) for event in season_changes):
            raise HTTPException(status_code=404, detail="Team staff not found for this season")
        staff = staff or {"officials": []}
        staff = add_manager_fallback(str(team_id), staff)
        return {"season": season, "team_id": team_id, "staff": staff}

    managers = {}
    for current_team_id, staff in season_staff.items():
        staff = add_manager_fallback(str(current_team_id), staff)
        officials = staff.get("officials") or []
        manager = next(
            (official for official in officials if official.get("role", "").lower() == "manager" and official.get("active")),
            next((official for official in officials if official.get("role", "").lower() == "manager"), None),
        )
        name = (manager or {}).get("name") or {}
        display = name.get("display") or " ".join(
            part for part in (name.get("first"), name.get("last")) if part
        )
        if display:
            managers[str(current_team_id)] = display

    return {"season": season, "managers": managers}


@router.get("/api/teams")
def get_teams(season: Optional[str] = None, competition: Optional[str] = None):
    """Returns sorted list of teams, optionally filtered by season and competition."""
    from src.competitions.registry import get_competition
    comp = get_competition(competition) if competition else None
    comp_id = comp.id if comp else 39

    if comp_id != 39:
        from src.db.database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT home_id AS id, home_name AS name, home_abbr AS abbr, MAX(ground_name) AS ground_name, MAX(home_logo) AS logo
            FROM matches
            WHERE competition_id = ? AND (? IS NULL OR ? = 'all' OR season = ?)
            GROUP BY home_id
            ORDER BY home_name ASC
        """, (comp_id, season, season, season))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return {"teams": rows, "count": len(rows)}

    if season == DEFAULT_SEASON:
        current_teams = {}
        for fixture in state.raw_fixtures_2627:
            for entry in fixture.get("teams", []):
                team = entry.get("team") or {}
                team_id = team.get("id")
                if team_id is None:
                    continue
                club = team.get("club") or {}
                current_teams[int(team_id)] = {
                    "id": int(team_id),
                    "name": team.get("name") or club.get("name") or "",
                    "abbr": club.get("abbr") or "",
                }

        if current_teams:
            result = sorted(current_teams.values(), key=lambda team: team["name"])
            return {"teams": result, "count": len(result)}

    if state.df_matches.empty:
        return {"teams": state.teams_list}

    df = state.df_matches
    if season and "season" in df.columns:
        df = df[df["season"] == season]

    filtered_teams = {}
    for _, r in df.iterrows():
        filtered_teams[int(r["home_id"])] = {"id": int(r["home_id"]), "name": r["home_name"], "abbr": r["home_abbr"]}
        filtered_teams[int(r["away_id"])] = {"id": int(r["away_id"]), "name": r["away_name"], "abbr": r["away_abbr"]}

    result = sorted(list(filtered_teams.values()), key=lambda x: x["name"])
    return {"teams": result, "count": len(result)}


@router.get("/api/teams/manager-changes")
def get_manager_changes(season: str = DEFAULT_SEASON):
    """Place verified appointment events on each team's first subsequent league fixture."""
    if season not in (DEFAULT_SEASON, "all") and season in state._historical_manager_changes_cache:
        return state._historical_manager_changes_cache[season]

    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    if not changes_path.exists():
        return {"season": season, "events_by_match": {}}
    try:
        with changes_path.open("r", encoding="utf-8") as stream:
            changes_by_season = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not read manager change data")
        raise HTTPException(status_code=500, detail="Could not read manager change data") from exc

    seasons = list(changes_by_season) if season == "all" else [season]
    all_events_by_match: Dict[str, List[Dict[str, Any]]] = {}
    for current_season in seasons:
      season_changes = changes_by_season.get(current_season, {}).get("events", [])
      fixtures = get_all_grouped_fixtures(current_season)
      fixtures_by_team: Dict[int, List[Tuple[datetime, Dict[str, Any]]]] = {}
      for fixture in fixtures:
        kickoff = state.parse_kickoff_datetime(fixture.get("kickoff_label", ""))
        if kickoff == datetime.min:
          continue
        for current_team_id in (int(fixture["home_id"]), int(fixture["away_id"])):
          fixtures_by_team.setdefault(current_team_id, []).append((kickoff, fixture))
      for team_fixtures in fixtures_by_team.values():
        team_fixtures.sort(key=lambda item: item[0])

      for event in season_changes:
        try:
            appointment_date = datetime.strptime(event["appointment_date"], "%Y-%m-%d").date()
            team_id = int(event["team_id"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Skipping malformed manager change record: %s", event)
            continue

        # Appointment sources provide dates, not times. The first fixture on a
        # later calendar date is the first one after the announcement.
        next_match = next(
            ((kickoff, fixture) for kickoff, fixture in fixtures_by_team.get(team_id, [])
             if kickoff.date() > appointment_date),
            None,
        )
        if next_match is None:
            continue
        _, next_fixture = next_match
        match_id = str(next_fixture["match_id"])
        all_events_by_match.setdefault(match_id, []).append({
            **event,
            "season": current_season,
            "gameweek": next_fixture.get("gameweek"),
            "effective_match_date": next_fixture.get("kickoff_label", ""),
        })

    response_data = {"season": season, "events_by_match": all_events_by_match}
    if season not in (DEFAULT_SEASON, "all"):
        state._historical_manager_changes_cache[season] = response_data
    return response_data


@router.get("/api/teams/manager-performance")
def get_manager_performance(team_id: int, manager_name: str, season: str = "all"):
    """Summarize a manager's completed league matches against each opponent."""
    changes_path = DATA_DIR / "processed" / "manager_changes.json"
    rosters_path = DATA_DIR / "processed" / "team_manager_rosters.json"
    staff_path = DATA_DIR / "processed" / "team_staff.json"
    try:
        changes = json.loads(changes_path.read_text(encoding="utf-8")) if changes_path.exists() else {}
        rosters = json.loads(rosters_path.read_text(encoding="utf-8")) if rosters_path.exists() else {}
        staff_by_season = json.loads(staff_path.read_text(encoding="utf-8")) if staff_path.exists() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Could not read manager history") from exc

    df = state.df_matches.copy()
    if season != "all" and "season" in df.columns:
        df = df[df["season"] == season]
    matching = []
    for match_season, group in changes.items():
        if season != "all" and match_season != season:
            continue
        events = sorted(
            [event for event in group.get("events", []) if int(event.get("team_id", -1)) == team_id],
            key=lambda event: event.get("appointment_date", ""),
        )
        season_staff = staff_by_season.get(match_season, {}).get(str(team_id), {})
        listed_manager = next((
            official.get("name", {}).get("display")
            for official in season_staff.get("officials", [])
            if str(official.get("role", "")).lower() == "manager"
            and (official.get("name", {}).get("display") or "").casefold() == manager_name.casefold()
        ), None)
        baseline = (
            listed_manager
            or rosters.get(match_season, {}).get("managers", {}).get(str(team_id), {}).get("name")
            or (events[0].get("outgoing_manager") if events else None)
        )
        # If this season has no change record or roster entry, a continuing
        # manager listed for the following season is a useful baseline.
        if not baseline:
            later_staff = staff_by_season.get(DEFAULT_SEASON, {}).get(str(team_id), {})
            baseline = next((
                official.get("name", {}).get("display")
                for official in later_staff.get("officials", [])
                if str(official.get("role", "")).lower() == "manager"
                and (official.get("name", {}).get("display") or "").casefold() == manager_name.casefold()
            ), None)
        for _, row in df[df["season"] == match_season].iterrows():
            home = int(row["home_id"]) == team_id
            if not home and int(row["away_id"]) != team_id:
                continue
            kickoff = str(row.get("kickoff_label", ""))
            try:
                match_date = datetime.strptime(kickoff.split(",")[0].strip(), "%a %d %b %Y").date().isoformat()
            except ValueError:
                millis = row.get("kickoff_millis")
                match_date = datetime.fromtimestamp(float(millis) / 1000).date().isoformat() if pd.notnull(millis) else ""
            coach = baseline
            for event in events:
                if event.get("appointment_date", "") <= match_date:
                    coach = event.get("incoming_manager")
                else:
                    break
            if coach and coach.casefold() == manager_name.casefold():
                matching.append((row, home))

    summary = {}
    total = {"matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    for row, home in matching:
        opponent_id = int(row["away_id"] if home else row["home_id"])
        opponent = str(row["away_name"] if home else row["home_name"])
        scored = row["home_score"] if home else row["away_score"]
        conceded = row["away_score"] if home else row["home_score"]
        if pd.isnull(scored) or pd.isnull(conceded):
            continue
        scored, conceded = int(scored), int(conceded)
        item = summary.setdefault(opponent_id, {"opponent_id": opponent_id, "opponent": opponent, "matches": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0})
        item["matches"] += 1
        item["gf"] += scored
        item["ga"] += conceded
        item["wins" if scored > conceded else "losses" if scored < conceded else "draws"] += 1
        total["matches"] += 1
        total["gf"] += scored
        total["ga"] += conceded
        total["wins" if scored > conceded else "losses" if scored < conceded else "draws"] += 1
    return {"team_id": team_id, "manager_name": manager_name, "season": season, "total": total,
            "opponents": sorted(summary.values(), key=lambda item: item["opponent"].casefold())}


def _build_team_match_history(
    team_id: int,
    season: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, int], Optional[Dict[str, Any]]]:
    df = state.df_matches.copy()
    if season and season != "all" and "season" in df.columns:
        df = df[df["season"] == season]

    team_matches_df = df[(df["home_id"] == team_id) | (df["away_id"] == team_id)].copy()
    if "kickoff_millis" in team_matches_df.columns:
        team_matches_df = team_matches_df.sort_values(by="kickoff_millis")

    matches_list: List[Dict[str, Any]] = []
    wins = draws = losses = gf = ga = 0

    for _, r in team_matches_df.iterrows():
        is_home = int(r["home_id"]) == team_id
        opp_id = int(r["away_id"]) if is_home else int(r["home_id"])
        opp_name = str(r["away_name"]) if is_home else str(r["home_name"])
        t_score = r["home_score"] if is_home else r["away_score"]
        o_score = r["away_score"] if is_home else r["home_score"]

        res = "-"
        if pd.notnull(t_score) and pd.notnull(o_score):
            t_score_int, o_score_int = int(t_score), int(o_score)
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
            t_score, o_score = t_score_int, o_score_int
        else:
            t_score = o_score = None

        kickoff_ms = None
        if "kickoff_millis" in r and pd.notnull(r["kickoff_millis"]):
            try:
                kickoff_ms = int(r["kickoff_millis"])
            except (ValueError, TypeError):
                kickoff_ms = None

        matches_list.append({
            "match_id": int(r["match_id"]),
            "season": str(r.get("season", "")),
            "status": "COMPLETED" if pd.notnull(t_score) else "UNPLAYED",
            "gameweek": r.get("gameweek"),
            "kickoff_label": r.get("kickoff_label"),
            "kickoff_millis": kickoff_ms,
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

    next_match = None
    for m in matches_list:
        if m["status"] == "UNPLAYED":
            next_match = {
                "match_id": m["match_id"],
                "gameweek": m["gameweek"],
                "kickoff_label": m["kickoff_label"],
                "kickoff_millis": m.get("kickoff_millis"),
                "opponent_id": m["opponent_id"],
                "opponent_name": m["opponent_name"],
                "is_home": m["is_home"],
            }
            break

    record = {
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "played": len(matches_list),
        "gf": gf,
        "ga": ga,
    }
    return matches_list, record, next_match


def _load_team_market_values(team_id: int, season: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    tm_team_data = None
    player_values_map: Dict[str, Dict[str, Any]] = {}
    try:
        conn = get_db()
        try:
            t_row = conn.execute(
                "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? AND season = ?",
                (team_id, season),
            ).fetchone()
            if not t_row:
                t_row = conn.execute(
                    "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? ORDER BY season DESC LIMIT 1",
                    (team_id,),
                ).fetchone()

            hist_rows = conn.execute(
                "SELECT season, market_value_eur, avg_market_value_eur, squad_size FROM team_market_values WHERE team_id = ? ORDER BY season ASC",
                (team_id,),
            ).fetchall()

            history_list = []
            for hr in hist_rows:
                s_val = hr["season"]
                mv_val = hr["market_value_eur"]
                avg_val = hr["avg_market_value_eur"]
                history_list.append({
                    "season": s_val,
                    "season_label": s_val.replace("_", "/"),
                    "market_value_eur": mv_val,
                    "avg_market_value_eur": avg_val,
                    "squad_size": hr["squad_size"],
                    "formatted": f"€{mv_val/1000:.2f}B" if mv_val >= 1000 else f"€{mv_val:,.1f}M",
                    "avg_formatted": f"€{avg_val:.2f}M" if avg_val else "-",
                })

            if t_row:
                mv_eur = t_row["market_value_eur"]
                tm_team_data = {
                    "season": t_row["season"],
                    "market_value_eur": mv_eur,
                    "avg_market_value_eur": t_row["avg_market_value_eur"],
                    "squad_size": t_row["squad_size"],
                    "formatted": f"€{mv_eur/1000:.2f}B" if mv_eur >= 1000 else f"€{mv_eur:,.1f}M",
                    "avg_formatted": f"€{t_row['avg_market_value_eur']:.2f}M",
                    "history": history_list,
                }

            p_rows = conn.execute(
                "SELECT player_id, name, market_value_eur FROM player_market_values WHERE team_id = ? AND season = ?",
                (team_id, season),
            ).fetchall()
            if not p_rows:
                p_rows = conn.execute(
                    "SELECT player_id, name, market_value_eur FROM player_market_values WHERE team_id = ? ORDER BY season DESC",
                    (team_id,),
                ).fetchall()

            for pr in p_rows:
                norm_name = pr["name"].lower().strip()
                val_obj = {"eur": pr["market_value_eur"], "tm_id": pr["player_id"]}
                player_values_map[norm_name] = val_obj
                parts = norm_name.split()
                if len(parts) > 1:
                    player_values_map[parts[-1]] = val_obj
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Could not load market values for team {team_id}: {e}")
    return tm_team_data, player_values_map


def _build_team_squad(
    team_id: int,
    season: Optional[str],
    player_values_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    all_logs = state._player_logs_dict or {}
    if not all_logs and state.players_logs_file.exists():
        state.get_player_match_logs(0)
        all_logs = state._player_logs_dict or {}
    cards_dict = state.get_player_cards_dict()

    pids_season = set()
    for pid_str, plist in all_logs.items():
        for l in plist:
            if (season == "all" or l.get("season") == season) and l.get("team_id") == team_id:
                try:
                    pids_season.add(int(pid_str))
                except (ValueError, TypeError):
                    pass

    roster_players = []
    if season == DEFAULT_SEASON:
        staff_path = DATA_DIR / "processed" / "team_staff.json"
        if staff_path.exists():
            try:
                with staff_path.open("r", encoding="utf-8") as sf:
                    staff_data = json.load(sf)
                    roster_players = staff_data.get(DEFAULT_SEASON, {}).get(str(team_id), {}).get("players", [])
            except Exception:
                roster_players = []
        roster_pids = {int(p["id"]) for p in roster_players if "id" in p}
        all_team_pids = roster_pids.union(pids_season)
    else:
        all_team_pids = pids_season

    squad: List[Dict[str, Any]] = []
    for pid in all_team_pids:
        p = state.player_registry_map.get(pid)
        if not p:
            roster_match = next((x for x in roster_players if x.get("id") == pid), None)
            if roster_match:
                n = roster_match.get("name", {})
                dname = n.get("display") or f"{n.get('first', '')} {n.get('last', '')}".strip()
                p = {
                    "id": pid,
                    "name": dname,
                    "position": roster_match.get("info", {}).get("position") or roster_match.get("latestPosition"),
                    "shirt": roster_match.get("info", {}).get("shirtNum"),
                    "country": roster_match.get("nationalTeam", {}).get("country"),
                    "captain": False,
                }
            else:
                p = next((x for x in state.all_players if x.get("id") == pid), {"id": pid, "name": f"Oyuncu {pid}", "position": "M", "shirt": None})

        p_logs = all_logs.get(str(pid), all_logs.get(pid, []))
        if season == "all":
            team_logs = [l for l in p_logs if l.get("team_id") == team_id]
            yc = sum(v.get("yellow", 0) for k, v in cards_dict.items() if k.endswith(f"_{pid}"))
            rc = sum(v.get("red", 0) for k, v in cards_dict.items() if k.endswith(f"_{pid}"))
        else:
            team_logs = [l for l in p_logs if l.get("season") == season and l.get("team_id") == team_id]
            card_info = cards_dict.get(f"{season}_{pid}", {})
            yc = card_info.get("yellow", 0)
            rc = card_info.get("red", 0)

        apps = len(team_logs)
        starts = sum(1 for l in team_logs if l.get("started"))
        goals = sum(int(l.get("goals") or 0) for l in team_logs)
        assists = sum(int(l.get("assists") or 0) for l in team_logs)

        if season != "all" and season != DEFAULT_SEASON and apps == 0:
            continue

        photo_url = state.resolve_player_photo(pid, p)
        p_name_lower = (p.get("name") or "").lower().strip()
        last_name = p_name_lower.split()[-1] if p_name_lower else ""
        p_val_entry = player_values_map.get(p_name_lower) or player_values_map.get(last_name)
        if isinstance(p_val_entry, dict):
            p_mv = p_val_entry.get("eur")
            p_tm_id = p_val_entry.get("tm_id")
        else:
            p_mv = p_val_entry
            p_tm_id = None
        p_mv_fmt = f"€{p_mv:.1f}M" if p_mv is not None and p_mv >= 1.0 else (f"€{int(p_mv*1000)}k" if p_mv is not None and p_mv > 0 else None)

        squad.append({
            "id": pid,
            "tm_id": p_tm_id,
            "name": p.get("name"),
            "shirt": p.get("shirt"),
            "position": p.get("position"),
            "photo_url": photo_url,
            "appearances": apps,
            "starts": starts,
            "goals": goals,
            "assists": assists,
            "yellow_cards": yc,
            "red_cards": rc,
            "country": p.get("country"),
            "captain": p.get("captain", False),
            "market_value_eur": p_mv,
            "market_value_formatted": p_mv_fmt,
        })

    pos_order = {"G": 0, "GK": 0, "D": 1, "DF": 1, "M": 2, "MF": 2, "F": 3, "FW": 3}
    squad.sort(key=lambda x: (
        pos_order.get(x.get("position", ""), 4),
        -(x.get("market_value_eur") or 0),
        -(x.get("appearances") or 0),
        -(x.get("goals") or 0),
        x.get("shirt") if x.get("shirt") is not None else 999,
    ))
    return squad


def _build_competition_team_profile(team_id: int, season: str, comp_id: int) -> Dict[str, Any]:
    """Team profile for non-Premier-League competitions, built only from stored match rows.

    Squad, market value and player totals come from stored TheStatsAPI payloads and stay empty
    (never estimated) for clubs that have not been synced.
    """
    conn = get_db()
    try:
        params: List[Any] = [team_id, team_id, comp_id]
        season_clause = ""
        if season and season != "all":
            season_clause = "AND season = ?"
            params.append(season)
        m_rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM matches WHERE (home_id = ? OR away_id = ?) AND competition_id = ? {season_clause} "
            "ORDER BY match_date ASC, match_id ASC",
            params,
        ).fetchall()]
    finally:
        conn.close()

    if not m_rows:
        raise HTTPException(status_code=404, detail="Team not found in this competition")

    first = m_rows[0]
    is_home_first = int(first["home_id"]) == team_id
    team_info = {
        "id": team_id,
        "name": first["home_name"] if is_home_first else first["away_name"],
        "abbr": (first["home_abbr"] if is_home_first else first["away_abbr"]) or "",
        "badge": (first.get("home_logo") if is_home_first else first.get("away_logo")) or None,
        "ground": next((m["ground_name"] for m in m_rows if int(m["home_id"]) == team_id and m["ground_name"]), ""),
        "market_value": None,
    }

    matches_list: List[Dict[str, Any]] = []
    next_match = None
    w = d = l = gf = ga = 0
    for m in m_rows:
        is_home = int(m["home_id"]) == team_id
        completed = m["status"] == "COMPLETED" and m["home_score"] is not None and m["away_score"] is not None
        item = {
            "match_id": m["match_id"],
            "gameweek": m["gameweek"],
            "stage": m.get("stage") or "league",
            "kickoff_label": m["kickoff_label"],
            "status": "COMPLETED" if completed else "UPCOMING",
            "is_home": is_home,
            "home_id": int(m["home_id"]),
            "home_name": m["home_name"],
            "home_abbr": m["home_abbr"],
            "home_logo": m.get("home_logo"),
            "home_score": m["home_score"],
            "away_id": int(m["away_id"]),
            "away_name": m["away_name"],
            "away_abbr": m["away_abbr"],
            "away_logo": m.get("away_logo"),
            "away_score": m["away_score"],
            "opponent_id": int(m["away_id"]) if is_home else int(m["home_id"]),
            "opponent_name": m["away_name"] if is_home else m["home_name"],
            "opponent_logo": m.get("away_logo") if is_home else m.get("home_logo"),
            "ground_name": m["ground_name"],
            "home_xg": m["home_xg"],
            "away_xg": m["away_xg"],
            "team_score": None,
            "opp_score": None,
            "result": None,
        }
        if completed:
            ts = int(m["home_score"] if is_home else m["away_score"])
            os_ = int(m["away_score"] if is_home else m["home_score"])
            gf, ga = gf + ts, ga + os_
            item["team_score"], item["opp_score"] = ts, os_
            if ts > os_:
                w, item["result"] = w + 1, "W"
            elif ts < os_:
                l, item["result"] = l + 1, "L"
            else:
                d, item["result"] = d + 1, "D"
        elif next_match is None:
            next_match = item
        matches_list.append(item)

    from src.api.competition_squads import build_squad_profile
    squad_season = season if season and season != "all" else first["season"]
    conn = get_db()
    try:
        squad, market_value, provider_stats = build_squad_profile(conn, comp_id, squad_season, team_id, team_info["name"])
    finally:
        conn.close()
    team_info["market_value"] = market_value

    return {
        "team": team_info,
        "season": season,
        "record": {"played": w + d + l, "won": w, "drawn": d, "lost": l, "gf": gf, "ga": ga, "gd": gf - ga, "points": w * 3 + d},
        "market_value": market_value,
        "matches": matches_list,
        "next_match": next_match,
        "squad": squad,
        "provider_season_stats": (provider_stats or {}).get("data"),
    }


def _with_european_matches(
    matches_list: List[Dict[str, Any]],
    next_match: Optional[Dict[str, Any]],
    club_name: str,
    season: Optional[str],
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Add the club's Champions League and Europa League matches to its Premier League fixture list.

    The record stays Premier League only; the merged list is ordered by kick-off and every match carries its
    competition so the page can sort and label by it."""
    from src.api.european_fixtures import COMPETITIONS, european_matches
    for match in matches_list:
        match["competition"] = COMPETITIONS[39]
    conn = get_db()
    try:
        european = european_matches(conn, club_name, season)
    finally:
        conn.close()
    if not european:
        return matches_list, next_match

    merged = sorted(matches_list + european, key=lambda m: (m.get("kickoff_millis") is None, m.get("kickoff_millis") or 0, m["match_id"]))
    upcoming = next((m for m in merged if m["status"] == "UNPLAYED"), None)
    if upcoming is not None:
        next_match = {
            "match_id": upcoming["match_id"],
            "gameweek": upcoming["gameweek"],
            "kickoff_label": upcoming["kickoff_label"],
            "kickoff_millis": upcoming.get("kickoff_millis"),
            "opponent_id": upcoming["opponent_id"],
            "opponent_name": upcoming["opponent_name"],
            "is_home": upcoming["is_home"],
            "competition": upcoming["competition"],
        }
    return merged, next_match


@router.get("/api/teams/profile")
def get_team_profile(team_id: int, season: Optional[str] = "all", competition: Optional[str] = None):
    """Returns team profile with match previews, W/D/L record, and squad roster."""
    comp_id = _competition_id(competition)
    if comp_id != PREMIER_LEAGUE_ID:
        return _build_competition_team_profile(team_id, season or "all", comp_id)

    team_meta = state.teams_dict.get(team_id)
    if not team_meta:
        p_team = next((p for p in state.all_players if p.get("teamId") == team_id), None)
        if not p_team:
            raise HTTPException(status_code=404, detail="Team not found")
        team_meta = {"id": team_id, "name": p_team.get("teamName", ""), "abbr": ""}

    matches_list, record, next_match = _build_team_match_history(team_id, season)
    matches_list, next_match = _with_european_matches(matches_list, next_match, team_meta.get("name", ""), season)
    tm_team_data, player_values_map = _load_team_market_values(team_id, season)
    squad = _build_team_squad(team_id, season, player_values_map)

    team_resp = dict(team_meta)
    team_resp["market_value"] = tm_team_data

    return {
        "team": team_resp,
        "season": season,
        "record": record,
        "market_value": tm_team_data,
        "matches": matches_list,
        "next_match": next_match,
        "squad": squad,
    }


TEAM_ID_TO_TM_CLUB_ID = {
    1: 11,    # Arsenal
    2: 405,   # Aston Villa
    4: 631,   # Chelsea
    5: 990,   # Coventry City
    6: 873,   # Crystal Palace
    7: 29,    # Everton
    8: 677,   # Ipswich Town
    9: 399,   # Leeds United
    10: 31,   # Liverpool
    11: 281,  # Manchester City
    12: 985,  # Manchester United
    13: 1003, # Leicester City
    15: 703,  # Nottingham Forest
    18: 350,  # Sheffield United
    20: 180,  # Southampton
    21: 148,  # Tottenham Hotspur
    23: 762,  # Newcastle United
    25: 379,  # West Ham United
    26: 1003, # Leicester City
    29: 289,  # Sunderland
    34: 931,  # Fulham
    38: 543,  # Wolverhampton Wanderers
    41: 3008, # Hull City
    43: 1132, # Burnley
    90: 1132, # Burnley
    127: 989, # Bournemouth
    130: 1148,# Brentford
    131: 1237,# Brighton & Hove Albion
    163: 1031,# Luton Town
}


def _parse_tm_fee(fee_str: str) -> Tuple[float, str, str]:
    if not fee_str:
        return 0.0, "-", "Bilinmiyor"
    s = fee_str.strip().lower()
    if "free" in s or "ablösefrei" in s:
        return 0.0, "Bedelsiz", "Serbest"
    if "end of loan" in s or "leih-ende" in s:
        return 0.0, "Kira Sonu", "Kiradan Geri Dönüş"
    if s.startswith("loan") or "leihe" in s:
        m = re.search(r"€([\d\.]+)\s*(m|k|th)", s)
        if m:
            val = float(m.group(1))
            unit = m.group(2)
            eur = round(val if unit == "m" else val / 1000.0, 2)
            return eur, f"Kiralık (€{eur:.1f}M)", "Kiralık"
        return 0.0, "Kiralık", "Kiralık"

    m = re.search(r"€([\d\.]+)\s*(m|k|th)", s)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        eur = round(val if unit == "m" else val / 1000.0, 2)
        fmt = f"€{eur:.1f}M" if eur >= 1.0 else f"€{int(eur*1000)}k"
        return eur, fmt, "Bonservis"

    return 0.0, fee_str.strip(), "Diğer"


def fetch_club_transfers_from_tm(tm_club_id: int, season_year: int, team_id: int, team_name: str) -> Dict[str, Any]:
    url = f"https://www.transfermarkt.com/club/transfers/verein/{tm_club_id}/saison_id/{season_year}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })
    try:
        html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error downloading Transfermarkt transfers HTML for tm_club_id={tm_club_id}, season={season_year}: {e}")
        return {
            "team_id": team_id,
            "tm_club_id": tm_club_id,
            "team_name": team_name,
            "season": f"{season_year}_{str(season_year+1)[2:]}",
            "summary": {
                "total_spent_eur": 0, "total_spent_formatted": "€0",
                "total_income_eur": 0, "total_income_formatted": "€0",
                "net_balance_eur": 0, "net_balance_formatted": "€0",
                "arrivals_count": 0, "departures_count": 0
            },
            "arrivals": [],
            "departures": []
        }

    soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
    arrivals, departures = [], []
    season_str = f"{str(season_year)[2:]}/{str(season_year+1)[2:]}"

    conn = get_db()

    if soup:
        for b in soup.select(".box"):
            h2 = b.select_one("h2")
            if not h2:
                continue
            title = h2.get_text(strip=True)
            is_arr = "Arrivals" in title
            is_dep = "Departures" in title
            if not (is_arr or is_dep):
                continue

            target_list = arrivals if is_arr else departures
            direction = "in" if is_arr else "out"

            for r in b.select("table.items > tbody > tr"):
                name_el = r.select_one(".hauptlink a")
                if not name_el:
                    continue
                player_name = name_el.get_text(strip=True)
                p_href = name_el.get("href", "")
                pid_m = re.search(r"/spieler/(\d+)", p_href)
                player_id = pid_m.group(1) if pid_m else None

                # Position
                tables = r.select("table.inline-table")
                pos = "-"
                if tables:
                    tds = tables[0].select("tr td")
                    if len(tds) >= 2:
                        pos = tds[-1].get_text(strip=True)

                # Age
                age_el = r.select_one("td.zentriert")
                age_val = None
                if age_el and age_el.get_text(strip=True).isdigit():
                    age_val = int(age_el.get_text(strip=True))

                # Counterpart
                counterpart = "Bilinmiyor"
                counterpart_cid = None
                counterpart_badge = None
                if len(tables) > 1:
                    cp_a = tables[1].select_one(".hauptlink a")
                    if cp_a:
                        counterpart = cp_a.get_text(strip=True)
                        cid_m = re.search(r"/verein/(\d+)", cp_a.get("href", ""))
                        if cid_m:
                            counterpart_cid = int(cid_m.group(1))
                    cp_img = tables[1].select_one("img.tiny_wappen")
                    if cp_img:
                        counterpart_badge = cp_img.get("src")

                fee_el = r.select_one(".rechts a, .rechts")
                fee_str = fee_el.get_text(strip=True) if fee_el else "-"
                fee_eur, fee_fmt, t_type = _parse_tm_fee(fee_str)

                # Look up market value if exists in db
                mv_eur = 0.0
                mv_fmt = "—"
                if player_id:
                    try:
                        row = conn.execute("SELECT market_value_eur FROM player_market_values WHERE player_id = ? ORDER BY season DESC LIMIT 1", (player_id,)).fetchone()
                        if row and row["market_value_eur"]:
                            mv_eur = round(row["market_value_eur"] / 1000.0, 2)
                            mv_fmt = f"€{mv_eur:.1f}M" if mv_eur >= 1.0 else f"€{int(mv_eur*1000)}k"
                    except Exception:
                        pass

                transfer_id = None
                if fee_el and fee_el.name == "a":
                    t_href = fee_el.get("href", "")
                    t_m = re.search(r"/transfer_id/(\d+)", t_href)
                    if t_m:
                        transfer_id = t_m.group(1)

                target_list.append({
                    "id": transfer_id or f"{player_id or 0}_{direction}_{season_year}",
                    "player_id": player_id,
                    "player_name": player_name,
                    "position": pos,
                    "age": age_val,
                    "counterpart_club_name": counterpart,
                    "counterpart_club_id": counterpart_cid,
                    "counterpart_club_badge": counterpart_badge,
                    "direction": direction,
                    "transfer_type": t_type,
                    "fee_eur": fee_eur,
                    "fee_formatted": fee_fmt,
                    "market_value_eur": mv_eur,
                    "market_value_formatted": mv_fmt,
                    "date": f"{season_year}-07-01",
                    "date_formatted": f"1 Tem {season_year}",
                    "season": season_str
                })

    conn.close()

    spent = round(sum(x["fee_eur"] for x in arrivals), 2)
    income = round(sum(x["fee_eur"] for x in departures), 2)
    net = round(income - spent, 2)

    team_info = state.teams_dict.get(team_id, {})
    return {
        "team_id": team_id,
        "tm_club_id": tm_club_id,
        "team_name": team_name or team_info.get("name"),
        "team_badge": team_info.get("badge") or f"/badges/{team_id}.svg",
        "season": f"{season_year}_{str(season_year+1)[2:]}",
        "summary": {
            "total_spent_eur": spent,
            "total_spent_formatted": f"€{spent:.1f}M" if spent >= 1.0 else f"€{int(spent*1000)}k",
            "total_income_eur": income,
            "total_income_formatted": f"€{income:.1f}M" if income >= 1.0 else f"€{int(income*1000)}k",
            "net_balance_eur": net,
            "net_balance_formatted": f"+€{net:.1f}M" if net > 0 else (f"-€{abs(net):.1f}M" if net < 0 else "€0"),
            "arrivals_count": len(arrivals),
            "departures_count": len(departures)
        },
        "arrivals": arrivals,
        "departures": departures
    }


@router.get("/api/teams/{team_id}/transfers")
def get_team_transfers(team_id: int, season: Optional[str] = None):
    """
    Returns verified Transfermarkt transfer history (arrivals and departures)
    with fees, loan types, and counterparty clubs for the requested season.
    """
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_season_transfers_cache (
                team_id INTEGER,
                season TEXT,
                tm_club_id INTEGER,
                data_json TEXT,
                updated_at TEXT,
                PRIMARY KEY (team_id, season)
            )
        """)
        conn.commit()

        season_key = (season or DEFAULT_SEASON).strip()
        if season_key == "all":
            season_key = DEFAULT_SEASON

        # Check season cache
        cache_row = conn.execute(
            "SELECT data_json FROM team_season_transfers_cache WHERE team_id = ? AND season = ?",
            (team_id, season_key)
        ).fetchone()
        if cache_row and cache_row["data_json"]:
            try:
                return json.loads(cache_row["data_json"])
            except Exception:
                pass

        # Resolve tm_club_id
        tm_row = conn.execute(
            "SELECT tm_club_id FROM team_market_values WHERE team_id = ? LIMIT 1",
            (team_id,)
        ).fetchone()
        tm_club_id = tm_row["tm_club_id"] if tm_row else TEAM_ID_TO_TM_CLUB_ID.get(team_id)
        if not tm_club_id:
            raise HTTPException(status_code=404, detail="Transfermarkt club ID not found for team")

        team_info = state.teams_dict.get(team_id, {})
        team_name = team_info.get("name", "")

        # If 2026_27 and already in team_transfers_cache, use it!
        if season_key == DEFAULT_SEASON:
            old_row = conn.execute("SELECT data_json FROM team_transfers_cache WHERE team_id = ?", (team_id,)).fetchone()
            if old_row and old_row["data_json"]:
                data = json.loads(old_row["data_json"])
                conn.execute(
                    "INSERT OR REPLACE INTO team_season_transfers_cache (team_id, season, tm_club_id, data_json, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
                    (team_id, season_key, tm_club_id, old_row["data_json"])
                )
                conn.commit()
                return data

        # Scrape and cache for requested season
        try:
            season_year = int(season_key.split("_")[0])
        except Exception:
            season_year = 2026

        result = fetch_club_transfers_from_tm(tm_club_id, season_year, team_id, team_name)
        conn.execute(
            "INSERT OR REPLACE INTO team_season_transfers_cache (team_id, season, tm_club_id, data_json, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (team_id, season_key, tm_club_id, json.dumps(result))
        )
        conn.commit()
        return result
    finally:
        conn.close()


@router.get("/api/teams/tactics")
def get_team_tactics(team_id: int, season: Optional[str] = "all"):
    """Returns a team-level tactical profile and same-season league benchmarks."""
    if team_id not in state.teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_tactical_profile(team_id, season or "all")


@router.get("/api/teams/attacking-leaders")
def get_team_attacking_leaders_endpoint(team_id: int, season: Optional[str] = "all"):
    """Return the team's top three players by explainable attacking rating."""
    if team_id not in state.teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_attacking_leaders(team_id, season or "all")


@router.get("/api/teams/scenarios")
def get_team_scenarios(team_id: int, season: Optional[str] = "all"):
    """Returns shot and corner rates split by the live score state."""
    if team_id not in state.teams_dict:
        raise HTTPException(status_code=404, detail="Team not found")
    return get_team_scenario_profile(team_id, season or "all")
