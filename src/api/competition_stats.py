"""League statistics for UEFA competitions, assembled from stored TheStatsAPI payloads.

The shared builder (``src.analytics.league_stats.build_league_stats``) expects Premier League style
columns and per-player match logs; this module translates the stored payloads into that shape.
Player ratings are the provider's own, never recomputed.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.analytics.league_stats import build_league_stats

PROVIDER = "TheStatsAPI"


def _pid(provider_id: str) -> int:
    return int(provider_id.rsplit("_", 1)[-1])


def _side(group: Dict[str, Any], key: str, side: str) -> Optional[float]:
    value = (group or {}).get(key) or {}
    value = value.get("all", value) if isinstance(value, dict) and "all" in value else value
    return value.get(side) if isinstance(value, dict) else None


def _kickoff_ms(row: Dict[str, Any]) -> float:
    try:
        return datetime.fromisoformat(str(row.get("match_date"))).timestamp() * 1000 + int(row["match_id"] % 1000)
    except (TypeError, ValueError):
        return float(row["match_id"])


def _payloads(conn: sqlite3.Connection, comp_id: int, season: str, kind: str) -> Dict[int, Dict[str, Any]]:
    rows = conn.execute(
        "SELECT p.match_id, p.payload FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND m.season = ? AND p.provider = ? AND p.kind = ?",
        (comp_id, season, PROVIDER, kind),
    ).fetchall()
    return {r["match_id"]: json.loads(r["payload"]) for r in rows}


def build_competition_stats(conn: sqlite3.Connection, comp_id: int, season: str, scope: str, gameweek: Optional[int]) -> Dict[str, Any]:
    matches = pd.read_sql_query("SELECT * FROM matches WHERE competition_id = ? AND season = ? AND stage IN ('league', 'group')", conn, params=(comp_id, season))
    if matches.empty:
        return build_league_stats(season=season, scope=scope, gameweek=gameweek, matches=matches, logs={}, registry={}, bookings={},
                                  goal_events=pd.DataFrame(), audit_rows=[], ages={}, teams={})

    stats_by_match = _payloads(conn, comp_id, season, "stats")
    for side in ("home", "away"):
        for column in (f"statsapi_{side}_xg", f"{side}_total_scoring_att", f"{side}_ontarget_scoring_att", f"{side}_saves", f"{side}_fk_foul_lost"):
            matches[column] = None
    for index, row in matches.iterrows():
        data = (stats_by_match.get(int(row["match_id"])) or {}).get("data")
        if not data:
            continue
        overview, shots = data.get("overview") or {}, data.get("shots") or {}
        for side in ("home", "away"):
            matches.at[index, f"statsapi_{side}_xg"] = _side(overview, "expected_goals", side)
            matches.at[index, f"{side}_total_scoring_att"] = _side(overview, "total_shots", side)
            matches.at[index, f"{side}_ontarget_scoring_att"] = _side(shots, "shots_on_target", side)
            matches.at[index, f"{side}_saves"] = _side(overview, "goalkeeper_saves", side)
            matches.at[index, f"{side}_fk_foul_lost"] = _side(overview, "fouls", side)
    matches["kickoff_millis"] = [_kickoff_ms(r) for r in matches.to_dict("records")]

    teams: Dict[int, Dict[str, Any]] = {}
    for r in matches.to_dict("records"):
        teams[int(r["home_id"])] = {"name": r["home_name"], "abbr": r["home_abbr"], "badge": r.get("home_logo")}
        teams[int(r["away_id"])] = {"name": r["away_name"], "abbr": r["away_abbr"], "badge": r.get("away_logo")}

    from src.api.competition_squads import _competition_payloads, _local_team_ids
    local_by_provider = _local_team_ids(conn, comp_id, season)
    registry: Dict[int, Dict[str, Any]] = {}
    ages: Dict[int, int] = {}
    for squad in _competition_payloads(conn, comp_id, season, "squad"):
        local_id, local_name = local_by_provider.get(squad["team"]["id"], (None, squad["team"]["name"]))
        for p in squad.get("data") or []:
            registry[_pid(p["id"])] = {"name": p.get("name"), "position": p.get("position"), "teamId": local_id, "teamName": local_name}
            if p.get("age"):
                ages[_pid(p["id"])] = int(p["age"])

    from src.api.competition_squads import stats_roster
    for player_id, info in stats_roster(conn, comp_id, season).items():  # players who left since are not in today's squads
        local_id, local_name = local_by_provider.get(info["provider_team_id"], (None, None))
        registry.setdefault(_pid(player_id), {"name": info["name"], "position": info["position"], "teamId": local_id, "teamName": local_name})

    row_by_match = {int(r["match_id"]): r for r in matches.to_dict("records")}
    logs: Dict[str, List[Dict[str, Any]]] = {}
    bookings: Dict[int, Dict[int, Dict[str, int]]] = {}
    for match_id, payload in _payloads(conn, comp_id, season, "player_stats").items():
        row = row_by_match.get(match_id)
        if row is None:
            continue
        for entry in payload.get("data") or []:
            if not entry.get("played"):
                continue
            pid = _pid(entry["player_id"])
            local_id, local_name = local_by_provider.get(entry.get("team_id"), (None, None))
            is_home = local_id == int(row["home_id"])
            general, shooting, passing = entry.get("general") or {}, entry.get("shooting") or {}, entry.get("passing") or {}
            logs.setdefault(str(pid), []).append({
                "season": season, "match_id": match_id, "gameweek": int(row["gameweek"]),
                "team_id": local_id, "team_name": local_name, "position": entry.get("position"),
                "started": bool(entry.get("started")), "minutes_played": entry.get("minutes_played") or 0,
                "goals": shooting.get("goals") or 0, "assists": passing.get("assists") or 0,
                "team_score": int(row["home_score"] if is_home else row["away_score"]),
                "opp_score": int(row["away_score"] if is_home else row["home_score"]),
                "provider_rating": entry.get("rating"),
            })
            if general.get("yellow_cards") or general.get("red_cards"):
                bookings.setdefault(match_id, {})[pid] = {"yellow": general.get("yellow_cards") or 0, "red": general.get("red_cards") or 0}

    return build_league_stats(
        season=season, scope=scope, gameweek=gameweek, matches=matches, logs=logs, registry=registry,
        bookings=bookings, goal_events=pd.DataFrame(), audit_rows=[], ages=ages, teams=teams,
    )
