"""League-wide statistics for the Statistics page (week and season scopes).

`build_league_stats` is pure: every dataset is passed in, so it can be tested with small
synthetic frames. Two kinds of sections exist:

* scope sections (highlights, team of the scope, attack, defence, scorers, assists, discipline)
  describe only the selected gameweek, or the whole season in season scope;
* cumulative sections (goalkeepers, minutes, young players, referees, form, movers, home and
  away tables, goal minutes) describe everything up to and including the selected gameweek,
  because a single week is too small a sample for them.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from src.analytics.player_ratings import calculate_single_match_score

FORMATION = (("G", 1), ("D", 4), ("M", 3), ("F", 3))
FORMATION_LABEL = "4-3-3"
GOAL_BUCKETS = ("1-15", "16-30", "31-45", "46-60", "61-75", "76-90+")
MOVER_WINDOW = 5
YOUNG_MAX_AGE = 21
TOP_N = 10
SURPRISE_MAX_PROB = 30.0

_GOAL_SCORE_RE = re.compile(r"Goal!\s+.+?\s(\d+),\s+.+?\s(\d+)\.")


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _int(value: Any, default: int = 0) -> int:
    return default if _is_null(value) else int(value)


def _float(value: Any, default: float = 0.0) -> float:
    return default if _is_null(value) else float(value)


def _opt_float(value: Any, digits: int = 2) -> Optional[float]:
    return None if _is_null(value) else round(float(value), digits)


def pos_group(position: Any) -> str:
    """Collapse a position label to G, D, M or F (unknown labels count as midfield)."""
    first = str(position or "M").strip().upper()[:1]
    return first if first in {"G", "D", "M", "F"} else "M"


def goal_bucket(minute: Any) -> Optional[int]:
    """Index into GOAL_BUCKETS for a minute label such as '07', '45+2' or '90+11'."""
    match = re.match(r"\s*(\d+)", str(minute or ""))
    if not match:
        return None
    value = int(match.group(1))
    for index, upper in enumerate((15, 30, 45, 60, 75)):
        if value <= upper:
            return index
    return len(GOAL_BUCKETS) - 1


def _points(goals_for: int, goals_against: int) -> int:
    return 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0


def _team_rows(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    """One row per team per played match."""
    rows: List[Dict[str, Any]] = []
    for r in frame.to_dict("records"):
        for side, other in (("home", "away"), ("away", "home")):
            rows.append({
                "team_id": int(r[f"{side}_id"]),
                "opp_id": int(r[f"{other}_id"]),
                "is_home": side == "home",
                "match_id": int(r["match_id"]),
                "gw": int(r["gw"]),
                "kickoff": _float(r.get("kickoff_millis")),
                "gf": _int(r[f"{side}_score"]),
                "ga": _int(r[f"{other}_score"]),
                "xg": _opt_float(r.get(f"statsapi_{side}_xg")),
                "xga": _opt_float(r.get(f"statsapi_{other}_xg")),
                "shots": _int(r.get(f"{side}_total_scoring_att")),
                "sot": _int(r.get(f"{side}_ontarget_scoring_att")),
                "sot_faced": _int(r.get(f"{other}_ontarget_scoring_att")),
                "saves": _int(r.get(f"{side}_saves")),
                "yellow": _int(r.get(f"{side}_total_yel_card")),
                "red": _int(r.get(f"{side}_total_red_card")),
                "fouls": _int(r.get(f"{side}_fk_foul_lost")),  # fouls the team committed
            })
    return rows


def _standings(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    table: Dict[int, Dict[str, int]] = defaultdict(lambda: {"played": 0, "points": 0, "gf": 0, "ga": 0})
    for row in _team_rows(frame):
        t = table[row["team_id"]]
        t["played"] += 1
        t["points"] += _points(row["gf"], row["ga"])
        t["gf"] += row["gf"]
        t["ga"] += row["ga"]
    ranked = sorted(table.items(), key=lambda kv: (-kv[1]["points"], -(kv[1]["gf"] - kv[1]["ga"]), -kv[1]["gf"], kv[0]))
    return [{"team_id": tid, "rank": i + 1, **t} for i, (tid, t) in enumerate(ranked)]


def _sum_optional(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return round(sum(present), 2) if present else None


def build_league_stats(
    *,
    season: str,
    scope: str,
    gameweek: Optional[int],
    matches: pd.DataFrame,
    logs: Dict[str, List[Dict[str, Any]]],
    registry: Dict[int, Dict[str, Any]],
    bookings: Dict[int, Dict[int, Dict[str, int]]],
    goal_events: pd.DataFrame,
    audit_rows: List[Dict[str, Any]],
    ages: Dict[int, int],
    teams: Dict[int, Dict[str, Any]],
    photo_url: Callable[[int, Dict[str, Any]], Optional[str]] = lambda pid, reg: None,
) -> Dict[str, Any]:
    scope = "season" if scope == "season" else "week"

    played = matches[matches["season"] == season].copy() if not matches.empty else matches.copy()
    if not played.empty:
        played = played[played["home_score"].notna() & played["away_score"].notna()].copy()
        played["gw"] = played["gameweek"].astype(int)
    gameweeks = sorted(int(g) for g in played["gw"].unique()) if not played.empty else []

    payload: Dict[str, Any] = {
        "season": season,
        "scope": scope,
        "gameweek": None,
        "gameweeks": gameweeks,
        "latest_gameweek": gameweeks[-1] if gameweeks else None,
        "matches_in_scope": 0,
        "formation": FORMATION_LABEL,
    }
    if not gameweeks:
        return payload

    latest = gameweeks[-1]
    if scope == "week":
        gw = gameweek if gameweek in gameweeks else latest
        in_scope = played[played["gw"] == gw]
        cumulative = played[played["gw"] <= gw]
        basis_gw = gw
    else:
        gw = None
        in_scope = cumulative = played
        basis_gw = latest
    payload["gameweek"] = gw
    payload["basis_gameweek"] = basis_gw
    payload["matches_in_scope"] = int(len(in_scope))

    def team_meta(team_id: int) -> Dict[str, Any]:
        info = teams.get(int(team_id), {})
        return {
            "id": int(team_id),
            "name": info.get("name") or f"Takım #{team_id}",
            "abbr": info.get("abbr") or "",
            "badge": info.get("badge") or f"/badges/{int(team_id)}.svg",
        }

    scope_ids = set(in_scope["match_id"].astype(int))
    cum_ids = set(cumulative["match_id"].astype(int))
    scope_rows = _team_rows(in_scope)
    cum_rows = _team_rows(cumulative)

    # ----------------------------------------------------------------- player logs
    all_logs: List[Tuple[int, Dict[str, Any], int]] = []
    for pid_str, plist in logs.items():
        for entry in plist:
            if entry.get("season") != season or _is_null(entry.get("gameweek")):
                continue
            entry_gw = int(entry["gameweek"])
            if entry_gw > basis_gw:
                continue
            all_logs.append((int(pid_str), entry, entry_gw))
    all_logs.sort(key=lambda item: item[2])
    scope_logs = [item for item in all_logs if item[1].get("match_id") in scope_ids or (scope == "season")]

    last_team: Dict[int, Tuple[Optional[int], Optional[str]]] = {}
    for pid, entry, _ in all_logs:
        last_team[pid] = (entry.get("team_id"), entry.get("team_name"))

    def player_meta(pid: int, position: Any = None) -> Dict[str, Any]:
        reg = registry.get(pid, {})
        team_id, team_name = last_team.get(pid, (reg.get("teamId"), reg.get("teamName")))
        return {
            "id": pid,
            "name": reg.get("name") or f"Oyuncu #{pid}",
            "position": pos_group(position or reg.get("position")),
            "team_id": int(team_id) if team_id is not None else None,
            "team_name": team_name,
            "photo_url": photo_url(pid, reg),
        }

    def book(entry: Dict[str, Any], pid: int) -> Tuple[int, int]:
        info = bookings.get(int(entry.get("match_id") or 0), {}).get(pid, {})
        return int(info.get("yellow") or 0), int(info.get("red") or 0)

    cum_totals: Dict[int, Dict[str, int]] = defaultdict(lambda: {"goals": 0, "assists": 0, "minutes": 0, "apps": 0, "starts": 0})
    scope_totals: Dict[int, Dict[str, int]] = defaultdict(lambda: {"goals": 0, "assists": 0, "minutes": 0, "apps": 0, "yellow": 0, "red": 0})
    ratings: Dict[int, List[float]] = defaultdict(list)
    positions: Dict[int, str] = {}

    for pid, entry, _ in all_logs:
        minutes = _int(entry.get("minutes_played"))
        c = cum_totals[pid]
        c["goals"] += _int(entry.get("goals"))
        c["assists"] += _int(entry.get("assists"))
        c["minutes"] += minutes
        if minutes > 0:
            c["apps"] += 1
        if entry.get("started"):
            c["starts"] += 1
        positions[pid] = pos_group(entry.get("position") or registry.get(pid, {}).get("position"))

    for pid, entry, _ in scope_logs:
        minutes = _int(entry.get("minutes_played"))
        s = scope_totals[pid]
        s["goals"] += _int(entry.get("goals"))
        s["assists"] += _int(entry.get("assists"))
        s["minutes"] += minutes
        if minutes > 0:
            s["apps"] += 1
        yellow, red = book(entry, pid)
        s["yellow"] += yellow
        s["red"] += red
        if entry.get("provider_rating") is not None:  # competitions rated by their data provider
            scored = {"overall": entry["provider_rating"]}
        else:
            scored = calculate_single_match_score(entry, positions.get(pid, "M"), bookings, pid)
        if scored and minutes >= 45:
            ratings[pid].append(scored["overall"])

    # ------------------------------------------------------------------ team of scope
    min_apps = 1 if scope == "week" else max(2, round(0.5 * basis_gw))
    candidates = [
        (pid, sum(vals) / len(vals), len(vals))
        for pid, vals in ratings.items()
        if len(vals) >= min_apps
    ]
    lineup: List[Dict[str, Any]] = []
    for group, count in FORMATION:
        pool = [c for c in candidates if positions.get(c[0]) == group]
        pool.sort(key=lambda c: (-c[1], -(scope_totals[c[0]]["goals"] + scope_totals[c[0]]["assists"]), -scope_totals[c[0]]["minutes"], c[0]))
        for pid, avg, matches_played in pool[:count]:
            totals = scope_totals[pid]
            lineup.append({
                **player_meta(pid, group),
                "rating": round(avg, 1),
                "goals": totals["goals"],
                "assists": totals["assists"],
                "matches": matches_played,
            })
    payload["team_of_scope"] = {
        "formation": FORMATION_LABEL,
        "average_rating": round(sum(p["rating"] for p in lineup) / len(lineup), 2) if lineup else None,
        "players": lineup,
        "complete": len(lineup) == sum(n for _, n in FORMATION),
        "min_matches": min_apps,
    }

    # ------------------------------------------------------------ attack and defence
    per_team: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
        "matches": 0, "goals": 0, "conceded": 0, "clean_sheets": 0, "shots": 0, "sot": 0,
        "sot_faced": 0, "saves": 0, "yellow": 0, "red": 0, "fouls": 0, "xg": [], "xga": [],
    })
    for row in scope_rows:
        t = per_team[row["team_id"]]
        t["matches"] += 1
        t["goals"] += row["gf"]
        t["conceded"] += row["ga"]
        t["clean_sheets"] += 1 if row["ga"] == 0 else 0
        t["shots"] += row["shots"]
        t["sot"] += row["sot"]
        t["sot_faced"] += row["sot_faced"]
        t["saves"] += row["saves"]
        t["yellow"] += row["yellow"]
        t["red"] += row["red"]
        t["fouls"] += row["fouls"]
        t["xg"].append(row["xg"])
        t["xga"].append(row["xga"])

    attack = [{
        "team": team_meta(tid), "matches": t["matches"], "goals": t["goals"],
        "xg": _sum_optional(t["xg"]), "shots": t["shots"], "shots_on_target": t["sot"],
        "goals_per_match": round(t["goals"] / t["matches"], 2),
    } for tid, t in per_team.items()]
    attack.sort(key=lambda r: (-r["goals"], -(r["xg"] or 0), -r["shots_on_target"], r["team"]["name"]))

    defence = [{
        "team": team_meta(tid), "matches": t["matches"], "conceded": t["conceded"],
        "clean_sheets": t["clean_sheets"], "xga": _sum_optional(t["xga"]),
        "shots_on_target_faced": t["sot_faced"], "saves": t["saves"],
        "conceded_per_match": round(t["conceded"] / t["matches"], 2),
    } for tid, t in per_team.items()]
    defence.sort(key=lambda r: (r["conceded"], -r["clean_sheets"], r["xga"] if r["xga"] is not None else 99, r["shots_on_target_faced"], r["team"]["name"]))
    payload["attack"] = attack
    payload["defence"] = defence

    # ------------------------------------------------------ scorers, assists, cards
    def player_rows(key: str, tie_key: str) -> List[Dict[str, Any]]:
        rows = []
        for pid, totals in scope_totals.items():
            if totals[key] <= 0:
                continue
            rows.append({
                **player_meta(pid, positions.get(pid)),
                key: totals[key],
                tie_key: totals[tie_key],
                "minutes": totals["minutes"],
                "matches": totals["apps"],
                f"season_{key}": cum_totals[pid][key],
            })
        rows.sort(key=lambda r: (-r[key], -r[tie_key], r["minutes"], r["name"]))
        return rows[:TOP_N]

    payload["top_scorers"] = player_rows("goals", "assists")
    payload["top_assists"] = player_rows("assists", "goals")

    card_players = []
    for pid, totals in scope_totals.items():
        if totals["yellow"] + totals["red"] <= 0:
            continue
        card_players.append({**player_meta(pid, positions.get(pid)), "yellow": totals["yellow"], "red": totals["red"], "matches": totals["apps"]})
    card_players.sort(key=lambda r: (-(r["yellow"] + r["red"]), -r["red"], r["name"]))
    card_teams = [{
        "team": team_meta(tid), "matches": t["matches"], "yellow": t["yellow"], "red": t["red"],
        "fouls": t["fouls"], "fouls_per_match": round(t["fouls"] / t["matches"], 1),
    } for tid, t in per_team.items() if t["yellow"] + t["red"] > 0]
    card_teams.sort(key=lambda r: (-(r["yellow"] + r["red"]), -r["red"], r["team"]["name"]))
    payload["discipline"] = {"players": card_players[:TOP_N], "teams": card_teams[:TOP_N]}

    # ------------------------------------------------------------------- goalkeepers
    saves_by_side = {(r["match_id"], r["team_id"]): r["saves"] for r in cum_rows}
    keeper_minutes: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for pid, entry, _ in all_logs:
        if pos_group(entry.get("position")) != "G":
            continue
        key = (int(entry.get("match_id") or 0), int(entry.get("team_id") or 0))
        minutes = _int(entry.get("minutes_played"))
        if minutes > keeper_minutes.get(key, (0, 0))[0]:
            keeper_minutes[key] = (minutes, pid)
    keepers: Dict[int, Dict[str, int]] = defaultdict(lambda: {"matches": 0, "clean_sheets": 0, "conceded": 0, "saves": 0})
    for pid, entry, _ in all_logs:
        if pos_group(entry.get("position")) != "G" or not entry.get("started") or _int(entry.get("minutes_played")) < 45:
            continue
        k = keepers[pid]
        k["matches"] += 1
        k["conceded"] += _int(entry.get("opp_score"))
        if _int(entry.get("opp_score")) == 0 and _int(entry.get("minutes_played")) >= 60:
            k["clean_sheets"] += 1
        key = (int(entry.get("match_id") or 0), int(entry.get("team_id") or 0))
        if keeper_minutes.get(key, (0, None))[1] == pid:
            k["saves"] += saves_by_side.get(key, 0)
    min_keeper_matches = min(3, basis_gw)
    keeper_rows = [{**player_meta(pid, "G"), **k} for pid, k in keepers.items() if k["matches"] >= min_keeper_matches]
    keeper_rows.sort(key=lambda r: (-r["clean_sheets"], r["conceded"], -r["saves"], r["name"]))
    payload["goalkeepers"] = keeper_rows[:TOP_N]

    # ----------------------------------------------------------- minutes and youth
    minutes_rows = [{
        **player_meta(pid, positions.get(pid)), "minutes": c["minutes"], "matches": c["apps"], "starts": c["starts"],
    } for pid, c in cum_totals.items() if c["minutes"] > 0]
    minutes_rows.sort(key=lambda r: (-r["minutes"], r["name"]))
    payload["minutes"] = minutes_rows[:TOP_N]

    young_rows = [{
        **player_meta(pid, positions.get(pid)), "age": ages[pid], "minutes": c["minutes"], "matches": c["apps"],
        "goals": c["goals"], "assists": c["assists"],
    } for pid, c in cum_totals.items() if pid in ages and ages[pid] <= YOUNG_MAX_AGE and c["minutes"] > 0]
    young_rows.sort(key=lambda r: (-r["minutes"], -(r["goals"] + r["assists"]), r["name"]))
    payload["young_players"] = {"available": bool(ages), "max_age": YOUNG_MAX_AGE, "players": young_rows[:TOP_N]}

    # ---------------------------------------------------------------------- referees
    referees: Dict[str, Dict[str, int]] = defaultdict(lambda: {"matches": 0, "yellow": 0, "red": 0})
    for r in cumulative.to_dict("records"):
        name = r.get("referee_name")
        if _is_null(name) or not str(name).strip():
            continue
        entry = referees[str(name)]
        entry["matches"] += 1
        entry["yellow"] += _int(r.get("total_yellow_cards"))
        entry["red"] += _int(r.get("total_red_cards"))
    min_ref_matches = 2 if any(v["matches"] >= 2 for v in referees.values()) else 1
    referee_rows = [{
        "name": name, **v, "cards": v["yellow"] + v["red"],
        "cards_per_match": round((v["yellow"] + v["red"]) / v["matches"], 2),
    } for name, v in referees.items() if v["matches"] >= min_ref_matches]
    referee_rows.sort(key=lambda r: (-r["cards_per_match"], -r["matches"], r["name"]))
    payload["referees"] = referee_rows[:TOP_N]

    # -------------------------------------------------------- form table and movers
    by_team: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in cum_rows:
        by_team[row["team_id"]].append(row)
    form_rows = []
    for tid, rows in by_team.items():
        recent = sorted(rows, key=lambda r: (r["kickoff"], r["gw"]))[-MOVER_WINDOW:]
        results = ["W" if r["gf"] > r["ga"] else "D" if r["gf"] == r["ga"] else "L" for r in recent]
        form_rows.append({
            "team": team_meta(tid), "results": results, "matches": len(recent),
            "points": sum(_points(r["gf"], r["ga"]) for r in recent),
            "goal_difference": sum(r["gf"] - r["ga"] for r in recent),
        })
    form_rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], r["team"]["name"]))
    payload["form"] = form_rows

    current_table = _standings(cumulative)
    reference_gw = basis_gw - (1 if scope == "week" else MOVER_WINDOW)
    movers: Dict[str, Any] = {"reference_gameweek": reference_gw if reference_gw >= 1 else None, "risers": [], "fallers": []}
    if reference_gw >= 1:
        previous = {row["team_id"]: row["rank"] for row in _standings(cumulative[cumulative["gw"] <= reference_gw])}
        changes = []
        for row in current_table:
            before = previous.get(row["team_id"])
            if before is None:
                continue
            changes.append({
                "team": team_meta(row["team_id"]), "rank": row["rank"], "previous_rank": before,
                "change": before - row["rank"], "points": row["points"],
            })
        movers["risers"] = sorted((c for c in changes if c["change"] > 0), key=lambda c: (-c["change"], c["rank"]))[:5]
        movers["fallers"] = sorted((c for c in changes if c["change"] < 0), key=lambda c: (c["change"], c["rank"]))[:5]
    payload["movers"] = movers

    # --------------------------------------------------------------- home and away
    def venue_table(is_home: bool) -> List[Dict[str, Any]]:
        table: Dict[int, Dict[str, int]] = defaultdict(lambda: {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "points": 0})
        for row in cum_rows:
            if row["is_home"] != is_home:
                continue
            t = table[row["team_id"]]
            t["played"] += 1
            t["gf"] += row["gf"]
            t["ga"] += row["ga"]
            pts = _points(row["gf"], row["ga"])
            t["points"] += pts
            t["won" if pts == 3 else "drawn" if pts == 1 else "lost"] += 1
        rows = [{"team": team_meta(tid), **t, "goal_difference": t["gf"] - t["ga"]} for tid, t in table.items()]
        rows.sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["gf"], r["team"]["name"]))
        return rows

    home_rows = [r for r in cum_rows if r["is_home"]]
    payload["venue"] = {
        "home": venue_table(True),
        "away": venue_table(False),
        "home_wins": sum(1 for r in home_rows if r["gf"] > r["ga"]),
        "draws": sum(1 for r in home_rows if r["gf"] == r["ga"]),
        "away_wins": sum(1 for r in home_rows if r["gf"] < r["ga"]),
    }

    # ----------------------------------------------------------------- goal minutes
    sides = {int(r["match_id"]): (int(r["home_id"]), int(r["away_id"])) for r in cumulative.to_dict("records")}
    def empty_buckets() -> List[int]:
        return [0] * len(GOAL_BUCKETS)

    league_scored = empty_buckets()
    league_scope = empty_buckets()
    team_minutes: Dict[int, Dict[str, List[int]]] = defaultdict(lambda: {
        "scored": empty_buckets(), "conceded": empty_buckets(),
        "scope_scored": empty_buckets(), "scope_conceded": empty_buckets(),
    })
    if not goal_events.empty:
        goals = goal_events[goal_events["match_id"].isin(cum_ids) & (goal_events["event_type"] == "goal")]
        for match_id, group in goals.groupby("match_id"):
            home_id, away_id = sides[int(match_id)]
            in_selected_scope = int(match_id) in scope_ids
            home_goals = away_goals = 0
            for event in group.sort_values(["seconds", "event_id"]).to_dict("records"):
                parsed = _GOAL_SCORE_RE.search(str(event.get("text") or ""))
                bucket = goal_bucket(event.get("minute"))
                if not parsed or bucket is None:
                    continue
                new_home, new_away = int(parsed.group(1)), int(parsed.group(2))
                if new_home > home_goals:
                    scorer, conceder = home_id, away_id
                elif new_away > away_goals:
                    scorer, conceder = away_id, home_id
                else:
                    continue
                home_goals, away_goals = new_home, new_away
                league_scored[bucket] += 1
                team_minutes[scorer]["scored"][bucket] += 1
                team_minutes[conceder]["conceded"][bucket] += 1
                if in_selected_scope:
                    league_scope[bucket] += 1
                    team_minutes[scorer]["scope_scored"][bucket] += 1
                    team_minutes[conceder]["scope_conceded"][bucket] += 1
    payload["goal_minutes"] = {
        "labels": list(GOAL_BUCKETS),
        "league": league_scored,
        "league_scope": league_scope,
        "teams": [{"team": team_meta(tid), **v} for tid, v in sorted(team_minutes.items(), key=lambda kv: team_meta(kv[0])["name"])],
    }

    # ------------------------------------------------------------ model surprises
    meta_by_match = {int(r["match_id"]): r for r in in_scope.to_dict("records")}
    surprises = []
    for row in audit_rows:
        record = meta_by_match.get(int(row["match_id"]))
        actual = row.get("actual_result")
        prob = row.get({"home": "prob_home", "draw": "prob_draw", "away": "prob_away"}.get(actual, ""))
        if record is None or prob is None or prob > SURPRISE_MAX_PROB:
            continue
        surprises.append({
            "match_id": int(row["match_id"]), "gameweek": int(record["gw"]),
            "home": team_meta(int(record["home_id"])), "away": team_meta(int(record["away_id"])),
            "home_score": int(record["home_score"]), "away_score": int(record["away_score"]),
            "actual_result": actual, "probability": round(float(prob), 1),
        })
    surprises.sort(key=lambda r: (r["probability"], r["match_id"]))
    payload["surprises"] = surprises[:5]

    # -------------------------------------------------------------------- highlights
    highlights: List[Dict[str, Any]] = []
    records = in_scope.to_dict("records")
    records_by_id = {int(r["match_id"]): r for r in records}

    def match_ref(match_id: int) -> Optional[Dict[str, Any]]:
        record = records_by_id.get(int(match_id))
        if record is None:
            return None
        return {
            "match_id": int(record["match_id"]), "gameweek": int(record["gw"]),
            "home_id": int(record["home_id"]), "home_name": team_meta(record["home_id"])["name"],
            "away_id": int(record["away_id"]), "away_name": team_meta(record["away_id"])["name"],
            "home_score": _int(record["home_score"]), "away_score": _int(record["away_score"]),
        }

    if records:
        top_match = max(records, key=lambda r: (_int(r["home_score"]) + _int(r["away_score"]), abs(_int(r["home_score"]) - _int(r["away_score"]))))
        total = _int(top_match["home_score"]) + _int(top_match["away_score"])
        highlights.append({
            "kind": "most_goals", "title": "En çok gol atılan maç", "match": match_ref(top_match["match_id"]),
            "detail": f"{team_meta(top_match['home_id'])['name']} {_int(top_match['home_score'])}-{_int(top_match['away_score'])} {team_meta(top_match['away_id'])['name']} ({total} gol)",
        })
        margin_match = max(records, key=lambda r: abs(_int(r["home_score"]) - _int(r["away_score"])))
        margin = abs(_int(margin_match["home_score"]) - _int(margin_match["away_score"]))
        if margin >= 3 and margin_match["match_id"] != top_match["match_id"]:
            highlights.append({
                "kind": "biggest_win", "title": "En farklı sonuç", "match": match_ref(margin_match["match_id"]),
                "detail": f"{team_meta(margin_match['home_id'])['name']} {_int(margin_match['home_score'])}-{_int(margin_match['away_score'])} {team_meta(margin_match['away_id'])['name']}",
            })
    if lineup:
        best = max(lineup, key=lambda p: (p["rating"], p["goals"] + p["assists"]))
        highlights.append({
            "kind": "best_player", "title": "En yüksek model reytingi", "player_id": best["id"],
            "detail": f"{best['name']} ({best['team_name']}) {best['rating']:.1f}",
        })
    hat_tricks = []
    for pid, entry, _ in scope_logs:
        if _int(entry.get("goals")) >= 3:
            hat_tricks.append((pid, entry))
    for pid, entry in hat_tricks[:3]:
        highlights.append({
            "kind": "hat_trick", "title": "Hat-trick", "player_id": pid, "match": match_ref(entry.get("match_id") or 0),
            "detail": f"{player_meta(pid)['name']} ({entry.get('team_name')}) {_int(entry.get('goals'))} gol attı",
        })
    reds = [(pid, t["red"]) for pid, t in scope_totals.items() if t["red"] > 0]
    if reds:
        names = ", ".join(player_meta(pid)["name"] for pid, _ in sorted(reds, key=lambda x: x[0])[:4])
        highlights.append({"kind": "red_cards", "title": f"{sum(n for _, n in reds)} kırmızı kart", "detail": names})
    if surprises:
        s = surprises[0]
        highlights.append({
            "kind": "surprise", "title": "Modelin en büyük sürprizi", "match": match_ref(s["match_id"]),
            "detail": f"{s['home']['name']} {s['home_score']}-{s['away_score']} {s['away']['name']} (model ihtimali %{s['probability']:.0f})",
        })
    payload["highlights"] = highlights[:6]
    return payload
