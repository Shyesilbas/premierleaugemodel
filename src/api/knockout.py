"""Knockout ties for UEFA competitions: leg aggregation, who went through, and the bracket layout."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

BRACKET_STAGES = [("playoff", "Play-off"), ("r16", "Son 16"), ("qf", "Çeyrek Final"), ("sf", "Yarı Final"), ("final", "Final")]
KNOCKOUT_STAGES = {stage for stage, _ in BRACKET_STAGES}
REASON_LABELS = {
    "WIN_ON_AGGREGATE": "toplam skorla",
    "WIN_ON_EXTRA_TIME": "uzatmalarda",
    "WIN_ON_PENALTIES": "penaltılarla",
    "WIN_REGULAR": "90 dakikada",
}


def _completed(row: Dict[str, Any]) -> bool:
    return row.get("status") == "COMPLETED" and row.get("home_score") is not None and row.get("away_score") is not None


def _team(row: Dict[str, Any], side: str) -> Dict[str, Any]:
    return {"id": int(row[f"{side}_id"]), "name": row[f"{side}_name"], "abbr": row.get(f"{side}_abbr") or "", "logo": row.get(f"{side}_logo")}


def build_ties(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group knockout matches into ties (one or two legs) with aggregate score and the team that went through."""
    groups: Dict[Tuple[str, frozenset], List[Dict[str, Any]]] = {}
    for row in rows:
        stage = row.get("stage") or "league"
        if stage in KNOCKOUT_STAGES:
            groups.setdefault((stage, frozenset((int(row["home_id"]), int(row["away_id"])))), []).append(row)

    ties = []
    for (stage, _), legs in groups.items():
        legs.sort(key=lambda r: (r.get("leg") or 0, str(r.get("match_date") or ""), r["match_id"]))
        first = legs[0]
        teams = [_team(first, "home"), _team(first, "away")]
        goals = {t["id"]: 0 for t in teams}
        for leg in legs:
            if _completed(leg):
                goals[int(leg["home_id"])] += int(leg["home_score"])
                goals[int(leg["away_id"])] += int(leg["away_score"])
        completed = all(_completed(leg) for leg in legs)
        decided = next((leg for leg in reversed(legs) if leg.get("advancing_team_id")), None)
        penalties = None
        shootout = next((leg for leg in legs if leg.get("home_penalties") is not None), None)
        if shootout:
            penalties = {int(shootout["home_id"]): int(shootout["home_penalties"]), int(shootout["away_id"]): int(shootout["away_penalties"])}
        ties.append({
            "stage": stage,
            "teams": teams,
            "legs": [{
                "match_id": leg["match_id"], "leg": leg.get("leg"), "status": leg["status"],
                "kickoff_label": leg.get("kickoff_label"), "match_date": leg.get("match_date"),
                "home": _team(leg, "home"), "away": _team(leg, "away"),
                "home_score": leg.get("home_score"), "away_score": leg.get("away_score"),
                "home_penalties": leg.get("home_penalties"), "away_penalties": leg.get("away_penalties"),
            } for leg in legs],
            "aggregate": goals if completed and len(legs) > 1 else None,
            "completed": completed,
            "winner_id": int(decided["advancing_team_id"]) if decided else None,
            "reason": decided.get("advance_reason") if decided else None,
            "penalties": penalties,
            "first_kickoff": str(first.get("match_date") or ""),
        })
    return ties


def tie_summaries(rows: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Per-match tie info for the fixture cards (relative to each match's home and away side)."""
    summaries: Dict[int, Dict[str, Any]] = {}
    for tie in build_ties(rows):
        names = {t["id"]: t["name"] for t in tie["teams"]}
        for leg in tie["legs"]:
            home_id, away_id = leg["home"]["id"], leg["away"]["id"]
            summaries[leg["match_id"]] = {
                "leg": leg["leg"],
                "legs": len(tie["legs"]),
                "aggregate": {"home": tie["aggregate"][home_id], "away": tie["aggregate"][away_id]} if tie["aggregate"] else None,
                "advanced_team_id": tie["winner_id"],
                "advanced_team_name": names.get(tie["winner_id"]),
                "advance_reason": tie["reason"],
                "advance_label": REASON_LABELS.get(tie["reason"] or ""),
                "decided": tie["winner_id"] is not None,
            }
    return summaries


def build_bracket(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rounds left to right (play-off .. final) with ties ordered so each round lines up with the next."""
    by_stage: Dict[str, List[Dict[str, Any]]] = {stage: [] for stage, _ in BRACKET_STAGES}
    for tie in build_ties(rows):
        by_stage[tie["stage"]].append(tie)

    rounds = [(stage, title, sorted(by_stage[stage], key=lambda t: t["first_kickoff"])) for stage, title in BRACKET_STAGES if by_stage[stage]]
    # Order backwards: a tie sits next to the tie of the following round that its winner (or, failing that, either team) plays in.
    for index in range(len(rounds) - 2, -1, -1):
        following = rounds[index + 1][2]
        position = {}
        for slot, nxt in enumerate(following):
            for team in nxt["teams"]:
                position[team["id"]] = slot
        stage, title, ties = rounds[index]
        ties.sort(key=lambda t: (position.get(t["winner_id"], position.get(t["teams"][0]["id"], 99)), t["first_kickoff"]))
        rounds[index] = (stage, title, ties)

    return {
        "rounds": [{"stage": stage, "title": title, "ties": ties} for stage, title, ties in rounds],
        "champion": next((t["teams"][0] if t["teams"][0]["id"] == t["winner_id"] else t["teams"][1] for t in (rounds[-1][2] if rounds and rounds[-1][0] == "final" else []) if t["winner_id"]), None),
    }
