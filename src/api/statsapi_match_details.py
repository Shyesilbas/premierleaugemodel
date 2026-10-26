"""Match detail payload for leagues whose only source is TheStatsAPI (LaLiga and leagues added the same way).

Lineups and the event timeline come from the provider's lineup and timeline payloads; statistics, ratings, shots and
odds are layered on by ``apply_statsapi_payloads``, the same overlay the UEFA competitions use. The timeline lists
one event per substitute (not an in/out pair) and no assists, so substitutions are paired from who was on the pitch
and goals carry no assister. Nothing is estimated.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from src.api.uefa_match_details import apply_statsapi_payloads
from src.ingest.providers.thestatsapi_league import local_team_id

SOURCE_LABEL = "TheStatsAPI olay akışı"
GOAL_TYPES = {"goal", "penalty_scored"}
CARD_TYPES = {"yellow_card": "yellow_card", "red_card": "red_card", "yellow_red_card": "red_card"}


def _number(provider_id: Optional[str]) -> Optional[int]:
    digits = re.sub(r"\D", "", provider_id or "")
    return int(digits) if digits else None


def _player(entry: Dict[str, Any], captain: bool = False) -> Dict[str, Any]:
    return {
        "id": _number(entry.get("id")),
        "name": entry.get("name", ""),
        "shirt": entry.get("jersey_number"),
        "position": entry.get("position") or "M",
        "captain": captain,
        "country": None,
        "photo_url": None,
        "rating": None,
        "is_match_rating": False,
    }


def build_lineups(lineup_payload: Optional[Dict[str, Any]], match: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = (lineup_payload or {}).get("data") or {}
    lineups = []
    for side in ("home", "away"):
        team = data.get(side) or {}
        starters = [_player(p) for p in team.get("starting_xi") or []]
        if not starters:
            continue
        is_home = side == "home"
        lineups.append({
            "team_id": match["home_id"] if is_home else match["away_id"],
            "team_name": match["home_name"] if is_home else match["away_name"],
            "score": match["home_score"] if is_home else match["away_score"],
            "formation": team.get("formation") or "",
            "formation_matrix": [],
            "team_ratings": None,
            "starters": starters,
            "substitutes": [_player(p) for p in team.get("substitutes") or []],
            "coaches": [],
        })
    return lineups


def _label(event: Dict[str, Any]) -> Tuple[str, float]:
    minute, extra = int(event.get("minute") or 0), int(event.get("extra_time") or 0)
    return (f"{minute}+{extra}'" if extra else f"{minute}'"), minute + extra / 100.0


def build_timeline(timeline_payload: Optional[Dict[str, Any]], lineups: List[Dict[str, Any]], match: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = ((timeline_payload or {}).get("data") or {}).get("events") or []
    names = {match["home_id"]: match["home_name"], match["away_id"]: match["away_name"]}
    people = {p["id"]: p for lu in lineups for p in lu["starters"] + lu["substitutes"]}
    on_field = {p["id"] for lu in lineups for p in lu["starters"]}
    running = {match["home_id"]: 0, match["away_id"]: 0}
    pending: Dict[Tuple[int, int, int], Dict[str, List[Dict[str, Any]]]] = {}
    items: List[Tuple[float, int, Dict[str, Any]]] = []

    for event in sorted(events, key=lambda e: (e.get("minute") or 0, e.get("extra_time") or 0, e.get("sequence") or 0)):
        kind = event.get("type", "")
        label, key = _label(event)
        team = event.get("team") or {}
        team_id = local_team_id(team["id"]) if team.get("id") else None
        player = event.get("player") or {}
        player_id = _number(player.get("id"))

        if kind in GOAL_TYPES or kind.startswith("own_goal"):
            own = kind.startswith("own_goal")
            opponent = match["away_id"] if team_id == match["home_id"] else match["home_id"]
            credited = opponent if own else team_id
            running[credited] = running.get(credited, 0) + 1
            items.append((key, 2, {
                "type": "goal", "goal_type": "Penalty" if kind == "penalty_scored" else ("Own goal" if own else "Goal"),
                "is_penalty": kind == "penalty_scored", "is_own_goal": own, "minute": label,
                "team_id": credited, "team_name": names.get(credited, ""), "player_id": player_id,
                "player_name": player.get("name", ""), "photo_url": None, "assist_id": None, "assist_name": None,
                "score": f"{running[match['home_id']]} - {running[match['away_id']]}",
            }))
        elif kind in CARD_TYPES:
            items.append((key, 2, {
                "type": CARD_TYPES[kind], "minute": label, "team_id": team_id, "team_name": names.get(team_id, ""),
                "player_id": player_id, "player_name": player.get("name", ""), "photo_url": None,
            }))
        elif kind == "added_time" and event.get("extra_time"):
            items.append((key, 1, {"type": "added_time", "minute": label, "label": "Uzatma Süresi", "description": f"+{event['extra_time']} dakika"}))
        elif kind == "substitution" and player_id is not None:
            going_off = player_id in on_field
            (on_field.discard if going_off else on_field.add)(player_id)
            slot = pending.setdefault((team_id, int(event.get("minute") or 0), int(event.get("extra_time") or 0)), {"off": [], "on": []})
            slot["off" if going_off else "on"].append({"id": player_id, "name": player.get("name", ""), "key": key})
            if slot["off"] and slot["on"]:
                out, incoming = slot["off"].pop(0), slot["on"].pop(0)
                items.append((key, 3, {
                    "type": "substitution", "minute": label, "team_id": team_id, "team_name": names.get(team_id, ""),
                    "player_in_id": incoming["id"], "player_in_name": incoming["name"], "player_in_photo": None,
                    "player_out_id": out["id"], "player_out_name": out["name"], "player_out_photo": None,
                }))
    items.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in items]


def build_statsapi_match_details(match: Dict[str, Any], payloads: Dict[str, Dict[str, Any]], odds: List[Dict[str, Any]]) -> Dict[str, Any]:
    lineups = build_lineups(payloads.get("lineups"), match)
    detail = (payloads.get("match") or {}).get("data") or {}
    result = {
        "metadata": {
            "match_id": match["match_id"], "kickoff_label": match["kickoff_label"], "ground": match["ground_name"],
            "referee": match["referee_name"], "attendance": detail.get("attendance"), "weather": None,
            "home_xg": None, "away_xg": None, "total_xg": None,
            "stats_source": SOURCE_LABEL if "timeline" in payloads else None,
        },
        "lineups": lineups,
        "team_stats": [],
        "player_stats": {"home": [], "away": []},
        "events": [],
        "timeline": build_timeline(payloads.get("timeline"), lineups, match) if "timeline" in payloads else [],
        "odds": [],
    }
    return apply_statsapi_payloads(result, payloads, match, odds)
