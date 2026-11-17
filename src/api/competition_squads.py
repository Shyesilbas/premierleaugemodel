"""Squad, market value and player season totals for UEFA clubs, read from stored TheStatsAPI payloads."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.ingest.sync_thestatsapi_competition import club_similarity

PROVIDER = "TheStatsAPI"
MATCH_THRESHOLD = 0.95


def _competition_payloads(conn: sqlite3.Connection, comp_id: int, season: str, kind: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT payload FROM external_competition_payloads WHERE competition_id = ? AND season = ? AND provider = ? AND kind = ?",
        (comp_id, season, PROVIDER, kind),
    ).fetchall()
    return [json.loads(r["payload"]) for r in rows]


def find_club_payload(conn: sqlite3.Connection, comp_id: int, season: str, kind: str, club_name: str) -> Optional[Dict[str, Any]]:
    best, best_score = None, 0.0
    for payload in _competition_payloads(conn, comp_id, season, kind):
        score = club_similarity(payload.get("team", {}).get("name", ""), club_name)
        if score > best_score:
            best, best_score = payload, score
    return best if best_score >= MATCH_THRESHOLD else None


def _season_totals(conn: sqlite3.Connection, comp_id: int, season: str, provider_team_id: str) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute(
        "SELECT p.payload FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND m.season = ? AND p.provider = ? AND p.kind = 'player_stats'",
        (comp_id, season, PROVIDER),
    ).fetchall()
    totals: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for entry in json.loads(row["payload"]).get("data") or []:
            if entry.get("team_id") != provider_team_id or not entry.get("played"):
                continue
            t = totals.setdefault(entry["player_id"], {"appearances": 0, "starts": 0, "minutes": 0, "goals": 0, "assists": 0, "yellow": 0, "red": 0, "ratings": []})
            t["appearances"] += 1
            t["starts"] += 1 if entry.get("started") else 0
            t["minutes"] += entry.get("minutes_played") or 0
            t["goals"] += (entry.get("shooting") or {}).get("goals") or 0
            t["assists"] += (entry.get("passing") or {}).get("assists") or 0
            t["yellow"] += (entry.get("general") or {}).get("yellow_cards") or 0
            t["red"] += (entry.get("general") or {}).get("red_cards") or 0
            if entry.get("rating") is not None:
                t["ratings"].append(entry["rating"])
    return totals


def _money(eur: float) -> str:
    return f"€{eur / 1e9:.2f}B" if eur >= 1e9 else f"€{eur / 1e6:.1f}M"


def _is_past_season(comp_id: int, season: str) -> bool:
    """The provider's squad endpoint returns today's registered players, so it only describes the current season."""
    from src.competitions.registry import get_competition
    return season != get_competition(comp_id).default_season


def build_squad_profile(conn: sqlite3.Connection, comp_id: int, season: str, team_id: int, team_name: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (squad, team market value, provider season stats); empty when nothing was synced.

    For a past season only players who actually played that season are listed, with their current market
    value, and no team total is given (the roster the provider returns is today's, not that season's)."""
    squad_payload = find_club_payload(conn, comp_id, season, "squad", team_name)
    stats_payload = find_club_payload(conn, comp_id, season, "team_stats", team_name)
    if not squad_payload:
        return [], None, stats_payload

    provider_team_id = squad_payload["team"]["id"]
    totals = _season_totals(conn, comp_id, season, provider_team_id)
    squad, values = [], []
    for p in squad_payload.get("data") or []:
        value = p.get("market_value")
        if value:
            values.append(float(value))
        t = totals.get(p["id"], {})
        ratings = t.get("ratings") or []
        squad.append({
            "id": p["id"],
            "tm_id": p["id"],
            "name": p.get("name"),
            "position": p.get("position") or "M",
            "shirt": (p.get("current_team") or {}).get("jersey_number"),
            "country": p.get("nationality"),
            "age": p.get("age"),
            "contract_until": p.get("contract_until"),
            "market_value_eur": round(float(value) / 1e6, 1) if value else None,
            "market_value_formatted": _money(float(value)) if value else None,
            "appearances": t.get("appearances", 0),
            "starts": t.get("starts", 0),
            "minutes": t.get("minutes", 0),
            "goals": t.get("goals", 0),
            "assists": t.get("assists", 0),
            "yellow_cards": t.get("yellow", 0),
            "red_cards": t.get("red", 0),
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "captain": False,
            "photo_url": None,
        })
    past = _is_past_season(comp_id, season)
    if past:
        known = {p["id"] for p in squad}
        for player_id, info in stats_roster(conn, comp_id, season).items():
            if info["provider_team_id"] != provider_team_id or player_id in known:
                continue
            t = totals.get(player_id, {})
            ratings = t.get("ratings") or []
            squad.append({
                "id": player_id, "tm_id": player_id, "name": info["name"], "position": info["position"] or "M", "shirt": None,
                "country": None, "age": None, "contract_until": None, "market_value_eur": None, "market_value_formatted": None,
                "appearances": t.get("appearances", 0), "starts": t.get("starts", 0), "minutes": t.get("minutes", 0),
                "goals": t.get("goals", 0), "assists": t.get("assists", 0), "yellow_cards": t.get("yellow", 0), "red_cards": t.get("red", 0),
                "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None, "captain": False, "photo_url": None,
            })
        squad = [p for p in squad if p["appearances"] > 0]
    squad.sort(key=lambda p: -(p["market_value_eur"] or 0))

    market_value = None
    if values and not past:
        total, average = sum(values), sum(values) / len(values)
        market_value = {
            "team_id": team_id, "name": team_name, "season": season,
            "market_value_eur": total, "avg_market_value_eur": average, "squad_size": len(values),
            "formatted": _money(total), "avg_formatted": _money(average),
            "history": [{"season": season, "season_label": season.replace("_", "/"), "market_value_eur": total,
                         "avg_market_value_eur": average, "squad_size": len(values),
                         "formatted": _money(total), "avg_formatted": _money(average)}],
        }
    return squad, market_value, stats_payload


def _local_team_ids(conn: sqlite3.Connection, comp_id: int, season: str) -> Dict[str, Tuple[int, str]]:
    """Map provider team ids to the local (UEFA) team id and name by matching club names."""
    local: Dict[int, str] = {}
    for row in conn.execute("SELECT home_id, home_name, away_id, away_name FROM matches WHERE competition_id = ? AND season = ?", (comp_id, season)):
        local[row["home_id"]], local[row["away_id"]] = row["home_name"], row["away_name"]
    mapping: Dict[str, Tuple[int, str]] = {}
    for payload in _competition_payloads(conn, comp_id, season, "squad"):
        name = payload["team"]["name"]
        best = max(local.items(), key=lambda item: club_similarity(name, item[1]), default=None)
        if best and club_similarity(name, best[1]) >= MATCH_THRESHOLD:
            mapping[payload["team"]["id"]] = best
    return mapping


def _market_value(raw: Any) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    millions = round(float(raw) / 1e6, 1)
    return {"market_value_eur": millions, "formatted": _money(float(raw))}


def stats_roster(conn: sqlite3.Connection, comp_id: int, season: str) -> Dict[str, Dict[str, Any]]:
    """Everyone who played in the season, from the match player stats (covers players who have since left)."""
    rows = conn.execute(
        "SELECT p.payload FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND m.season = ? AND p.provider = ? AND p.kind = 'player_stats'",
        (comp_id, season, PROVIDER),
    ).fetchall()
    roster: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for e in json.loads(row["payload"]).get("data") or []:
            if e.get("played") and e.get("player_id"):
                roster.setdefault(e["player_id"], {"name": e.get("player_name"), "position": e.get("position"), "provider_team_id": e.get("team_id")})
    return roster


def _appeared_player_ids(conn: sqlite3.Connection, comp_id: int, season: str) -> set:
    rows = conn.execute(
        "SELECT p.payload FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND m.season = ? AND p.provider = ? AND p.kind = 'player_stats'",
        (comp_id, season, PROVIDER),
    ).fetchall()
    return {e["player_id"] for r in rows for e in json.loads(r["payload"]).get("data") or [] if e.get("played")}


def list_squad_players(conn: sqlite3.Connection, comp_id: int, season: str, team_id: Optional[int], search: Optional[str], limit: int) -> Dict[str, Any]:
    teams = _local_team_ids(conn, comp_id, season)
    needle = (search or "").lower()
    appeared = _appeared_player_ids(conn, comp_id, season) if _is_past_season(comp_id, season) else None
    players = []
    for payload in _competition_payloads(conn, comp_id, season, "squad"):
        local_id, local_name = teams.get(payload["team"]["id"], (None, payload["team"]["name"]))
        if team_id is not None and local_id != team_id:
            continue
        for p in payload.get("data") or []:
            if appeared is not None and p["id"] not in appeared:
                continue
            if needle and needle not in (p.get("name") or "").lower() and needle not in local_name.lower():
                continue
            value = _market_value(p.get("market_value"))
            players.append({
                "id": p["id"], "teamId": local_id, "teamName": local_name, "name": p.get("name"),
                "position": p.get("position"), "age": p.get("age"), "nationality": p.get("nationality"),
                "market_value": p.get("market_value"), "market_value_eur": value["market_value_eur"] if value else None,
            })
    if appeared is not None:
        listed = {p["id"] for p in players}
        for player_id, info in stats_roster(conn, comp_id, season).items():
            if player_id in listed or (team_id is not None and teams.get(info["provider_team_id"], (None,))[0] != team_id):
                continue
            local_id, local_name = teams.get(info["provider_team_id"], (None, ""))
            if needle and needle not in (info["name"] or "").lower() and needle not in local_name.lower():
                continue
            players.append({"id": player_id, "teamId": local_id, "teamName": local_name, "name": info["name"], "position": info["position"],
                            "age": None, "nationality": None, "market_value": None, "market_value_eur": None})
    players.sort(key=lambda p: -(p["market_value"] or 0))
    return {"players": players[:limit], "total": len(players)}


def build_player_profile(conn: sqlite3.Connection, comp_id: int, season: str, player_id: str) -> Optional[Dict[str, Any]]:
    teams = _local_team_ids(conn, comp_id, season)
    found, provider_team_id = None, None
    for payload in _competition_payloads(conn, comp_id, season, "squad"):
        found = next((p for p in payload.get("data") or [] if p["id"] == player_id), None)
        if found:
            provider_team_id = payload["team"]["id"]
            break
    if not found:
        info = stats_roster(conn, comp_id, season).get(player_id)
        if info is None:
            return None
        provider_team_id = info["provider_team_id"]
        found = {"id": player_id, "name": info["name"], "position": info["position"], "current_team": {}}

    local_id, local_name = teams.get(provider_team_id, (None, found.get("current_team", {}).get("name", "")))
    matches, ratings = [], []
    rows = conn.execute(
        "SELECT m.*, p.payload FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND m.season = ? AND p.provider = ? AND p.kind = 'player_stats' ORDER BY m.match_date, m.match_id",
        (comp_id, season, PROVIDER),
    ).fetchall()
    for row in rows:
        entry = next((e for e in json.loads(row["payload"]).get("data") or [] if e["player_id"] == player_id), None)
        if not entry or not entry.get("played"):
            continue
        is_home = row["home_id"] == local_id
        shooting, passing = entry.get("shooting") or {}, entry.get("passing") or {}
        if entry.get("rating") is not None:
            ratings.append(entry["rating"])
        team_score = row["home_score"] if is_home else row["away_score"]
        opp_score = row["away_score"] if is_home else row["home_score"]
        matches.append({
            "match_id": row["match_id"], "gameweek": row["gameweek"], "season": row["season"], "kickoff": row["kickoff_label"],
            "is_home": is_home, "team_id": local_id, "team_name": local_name,
            "opponent_id": row["away_id"] if is_home else row["home_id"],
            "opponent_name": row["away_name"] if is_home else row["home_name"],
            "team_score": int(team_score) if team_score is not None else None,
            "opp_score": int(opp_score) if opp_score is not None else None,
            "started": bool(entry.get("started")), "minutes_played": entry.get("minutes_played") or 0,
            "goals": shooting.get("goals") or 0, "assists": passing.get("assists") or 0,
            "expected_goals": shooting.get("expected_goals"), "expected_assists": shooting.get("expected_assists"),
            "rating": entry.get("rating"),
        })
    return {
        "player": {
            "id": found["id"], "name": found.get("name"), "position": found.get("position"),
            "teamId": local_id, "teamName": local_name, "age": found.get("age"),
            "country": found.get("nationality"), "nationality": found.get("nationality"),
            "shirt": (found.get("current_team") or {}).get("jersey_number"),
            "contract_until": found.get("contract_until"), "preferred_foot": found.get("preferred_foot"),
            "height_cm": found.get("height_cm"),
            "market_value": _market_value(found.get("market_value")),
        },
        "season": season,
        "season_stats": {
            "appearances": len(matches), "minutes": sum(m["minutes_played"] for m in matches),
            "goals": sum(m["goals"] for m in matches), "assists": sum(m["assists"] for m in matches),
            "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
            "rated_matches_count": len(ratings),
        },
        "matches": matches,
    }


def club_managers(conn: sqlite3.Connection, comp_id: int, season: str) -> Dict[int, str]:
    """Local team id -> current manager, from the fixture list the provider returned at sync time."""
    stored = _competition_payloads(conn, comp_id, season, "managers")
    if not stored:
        return {}
    teams = _local_team_ids(conn, comp_id, season)
    managers: Dict[int, str] = {}
    for provider_team_id, entry in (stored[0].get("managers") or {}).items():
        local = teams.get(provider_team_id)
        if local is None:  # the squad sync maps ids by name; fall back to the club name stored with the manager
            candidates = conn.execute("SELECT DISTINCT home_id AS id, home_name AS name FROM matches WHERE competition_id = ? AND season = ?", (comp_id, season)).fetchall()
            best = max(candidates, key=lambda c: club_similarity(entry["team"], c["name"]), default=None)
            local = (best["id"], best["name"]) if best and club_similarity(entry["team"], best["name"]) >= MATCH_THRESHOLD else None
        if local is not None:
            managers[local[0]] = entry["name"]
    return managers


def _finalize_compare_bucket(acc: Dict[str, Any], market_value_eur: Optional[float]) -> Dict[str, Any]:
    apps = acc["appearances"]
    mins = acc["minutes"]
    goals = acc["goals"]
    assists = acc["assists"]
    ratings = acc["ratings"]
    per90 = lambda v: round((v * 90.0) / mins, 2) if mins > 0 else None
    opt_round = lambda v, dp=2: round(v, dp) if v is not None else None
    return {
        "appearances": apps,
        "starts": acc["starts"],
        "minutes": mins,
        "minutes_per_match": round(mins / apps, 1) if apps > 0 else None,
        "goals": goals,
        "assists": assists,
        "goals_plus_assists": goals + assists,
        "goals_per_90": per90(goals),
        "assists_per_90": per90(assists),
        "ga_per_90": per90(goals + assists),
        "clean_sheets": acc["clean_sheets"],
        "win_pct": round((acc["wins"] / apps) * 100.0, 1) if apps > 0 else None,
        "yellow_cards": acc["yellow"],
        "red_cards": acc["red"],
        "cards_per_90": per90(acc["yellow"] + acc["red"]),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "market_value_eur": market_value_eur,
        "expected_goals": opt_round(acc.get("xg")),
        "expected_assists": opt_round(acc.get("xa")),
        "shots": acc.get("shots"),
        "shots_ontarget": acc.get("shots_on_target"),
        "key_passes": acc.get("key_passes"),
        "tackles": acc.get("tackles"),
        "interceptions": acc.get("interceptions"),
        "saves": acc.get("saves"),
        "teams": acc["teams"],
        "team_names": acc["team_names"],
    }


def _new_compare_bucket(with_rich: bool = True) -> Dict[str, Any]:
    bucket: Dict[str, Any] = {
        "appearances": 0,
        "starts": 0,
        "minutes": 0,
        "goals": 0,
        "assists": 0,
        "clean_sheets": 0,
        "wins": 0,
        "yellow": 0,
        "red": 0,
        "ratings": [],
        "teams": [],
        "team_names": [],
    }
    if with_rich:
        bucket.update(xg=0.0, xa=0.0, has_xg=False, has_xa=False, shots=0, shots_on_target=0,
                      key_passes=0, tackles=0, interceptions=0, saves=0)
    return bucket


def build_compare_data(conn: sqlite3.Connection, comp_id: int, comp_key: str, default_season: str) -> Dict[str, Any]:
    """Aggregate player profiles and per-season statistics across all seasons of a competition."""
    season_rows = conn.execute(
        "SELECT DISTINCT season FROM matches WHERE competition_id = ? ORDER BY season DESC",
        (comp_id,),
    ).fetchall()
    seasons = [r["season"] for r in season_rows if r["season"]]
    if not seasons:
        seasons = [default_season]

    club_logos: Dict[int, Optional[str]] = {}
    local_teams_by_season: Dict[str, Dict[str, Tuple[int, str]]] = {}
    for row in conn.execute(
        "SELECT home_id, home_name, home_logo, away_id, away_name, away_logo FROM matches WHERE competition_id = ?",
        (comp_id,),
    ):
        if row["home_id"] is not None and row["home_logo"]:
            club_logos[int(row["home_id"])] = row["home_logo"]
        if row["away_id"] is not None and row["away_logo"]:
            club_logos[int(row["away_id"])] = row["away_logo"]

    for s in seasons:
        local_teams_by_season[s] = _local_team_ids(conn, comp_id, s)

    profiles_map: Dict[str, Dict[str, Any]] = {}
    squad_rows = conn.execute(
        "SELECT season, payload FROM external_competition_payloads WHERE competition_id = ? AND provider = ? AND kind = 'squad' ORDER BY season ASC",
        (comp_id, PROVIDER),
    ).fetchall()
    for r in squad_rows:
        s = r["season"]
        payload = json.loads(r["payload"])
        p_team = payload.get("team") or {}
        local_id, local_name = local_teams_by_season.get(s, {}).get(p_team.get("id", ""), (None, p_team.get("name", "")))
        for p in payload.get("data") or []:
            pid = str(p.get("id") or "")
            if not pid:
                continue
            mv = _market_value(p.get("market_value"))
            existing = profiles_map.get(pid, {})
            profiles_map[pid] = {
                "id": pid,
                "name": p.get("name") or existing.get("name") or "",
                "position": p.get("position") or existing.get("position") or "M",
                "teamId": local_id if local_id is not None else existing.get("teamId"),
                "teamName": local_name or existing.get("teamName") or "",
                "teamBadge": club_logos.get(local_id) if local_id is not None else existing.get("teamBadge"),
                "shirt": (p.get("current_team") or {}).get("jersey_number") or existing.get("shirt"),
                "country": p.get("nationality") or existing.get("country"),
                "age": p.get("age") or existing.get("age"),
                "photo_url": None,
                "market_value_eur": mv["market_value_eur"] if mv else existing.get("market_value_eur"),
                "market_value_formatted": mv["formatted"] if mv else existing.get("market_value_formatted"),
            }

    stats_rows = conn.execute(
        "SELECT m.season, m.home_id, m.home_name, m.home_score, m.away_id, m.away_name, m.away_score, p.payload "
        "FROM external_match_payloads p JOIN matches m ON m.match_id = p.match_id "
        "WHERE m.competition_id = ? AND p.provider = ? AND p.kind = 'player_stats' ORDER BY m.match_date ASC, m.match_id ASC",
        (comp_id, PROVIDER),
    ).fetchall()

    raw_acc: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in stats_rows:
        s = row["season"]
        teams_map = local_teams_by_season.get(s, {})
        for e in json.loads(row["payload"]).get("data") or []:
            if not e.get("played") or not e.get("player_id"):
                continue
            pid = str(e["player_id"])
            p_team_id = e.get("team_id")
            local_id, local_name = teams_map.get(p_team_id, (None, ""))
            if pid not in profiles_map:
                profiles_map[pid] = {
                    "id": pid,
                    "name": e.get("player_name") or "",
                    "position": e.get("position") or "M",
                    "teamId": local_id,
                    "teamName": local_name,
                    "teamBadge": club_logos.get(local_id) if local_id is not None else None,
                    "shirt": None,
                    "country": None,
                    "age": None,
                    "photo_url": None,
                    "market_value_eur": None,
                    "market_value_formatted": None,
                }

            is_home = local_id is not None and local_id == row["home_id"]
            is_away = local_id is not None and local_id == row["away_id"]
            team_score = row["home_score"] if is_home else (row["away_score"] if is_away else None)
            opp_score = row["away_score"] if is_home else (row["home_score"] if is_away else None)

            shooting = e.get("shooting") or {}
            passing = e.get("passing") or {}
            defending = e.get("defending") or {}
            general = e.get("general") or {}
            gk = e.get("goalkeeping") or {}
            mins = int(e.get("minutes_played") or 0)

            for bucket_key in (s, "all"):
                b = raw_acc.setdefault(pid, {}).setdefault(bucket_key, _new_compare_bucket(True))
                b["appearances"] += 1
                if e.get("started"):
                    b["starts"] += 1
                b["minutes"] += mins
                b["goals"] += int(shooting.get("goals") or 0)
                b["assists"] += int(passing.get("assists") or 0)
                b["yellow"] += int(general.get("yellow_cards") or 0)
                b["red"] += int(general.get("red_cards") or 0)
                if opp_score is not None and float(opp_score) == 0.0 and mins >= 60:
                    b["clean_sheets"] += 1
                if team_score is not None and opp_score is not None and float(team_score) > float(opp_score):
                    b["wins"] += 1
                if e.get("rating") is not None:
                    b["ratings"].append(float(e["rating"]))
                if shooting.get("expected_goals") is not None:
                    b["has_xg"] = True
                    b["xg"] += float(shooting["expected_goals"])
                if shooting.get("expected_assists") is not None or passing.get("expected_assists") is not None:
                    b["has_xa"] = True
                    b["xa"] += float(shooting.get("expected_assists") or passing.get("expected_assists") or 0)
                b["shots"] += int(shooting.get("total_shots") or 0)
                b["shots_on_target"] += int(shooting.get("shots_on_target") or 0)
                b["key_passes"] += int(passing.get("key_passes") or 0)
                b["tackles"] += int(defending.get("tackles") or 0)
                b["interceptions"] += int(defending.get("interceptions") or 0)
                b["saves"] += int(gk.get("saves") or 0)
                if local_id is not None and local_id not in b["teams"]:
                    b["teams"].append(local_id)
                if local_name and local_name not in b["team_names"]:
                    b["team_names"].append(local_name)

    averages: Dict[str, Dict[str, Any]] = {}
    for pid, season_buckets in raw_acc.items():
        mv = profiles_map.get(pid, {}).get("market_value_eur")
        averages[pid] = {}
        for skey, b in season_buckets.items():
            if not b.get("has_xg"):
                b["xg"] = None
            if not b.get("has_xa"):
                b["xa"] = None
            averages[pid][skey] = _finalize_compare_bucket(b, mv)

    def _sort_key(p: Dict[str, Any]) -> Tuple[int, float, int, int, str]:
        p_avgs = averages.get(str(p["id"]), {})
        active = 1 if (default_season in p_avgs or "all" in p_avgs) else 0
        mv = float(p.get("market_value_eur") or 0.0)
        ga = (p_avgs.get(default_season) or p_avgs.get("all") or {}).get("goals_plus_assists", 0)
        apps = (p_avgs.get(default_season) or p_avgs.get("all") or {}).get("appearances", 0)
        return (-active, -mv, -int(ga), -int(apps), str(p.get("name") or ""))

    profiles = sorted(profiles_map.values(), key=_sort_key)
    all_seasons = seasons + (["all"] if "all" not in seasons else [])
    return {
        "competition": comp_key,
        "seasons": all_seasons,
        "profiles": profiles,
        "averages": averages,
    }
