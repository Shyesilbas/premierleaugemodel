"""Champions League and Europa League matches of a Premier League club, for its team profile.

The competitions are stored per UEFA club id while Premier League clubs have their own ids, so the two are
paired by club name. Nothing is fetched: the matches already sit in the ``matches`` table.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from src.ingest.sync_thestatsapi_competition import club_similarity, fold_text

LONDON = ZoneInfo("Europe/London")
MATCH_THRESHOLD = 0.95
COMPETITIONS = {
    39: {"key": "premier_league", "name": "Premier League", "abbr": "PL"},
    2: {"key": "champions_league", "name": "UEFA Şampiyonlar Ligi", "abbr": "ŞL"},
    3: {"key": "europa_league", "name": "UEFA Avrupa Ligi", "abbr": "AL"},
}
STAGE_LABELS = {"playoff": "Play-off", "r16": "Son 16", "qf": "Çeyrek final", "sf": "Yarı final", "final": "Final"}


def uefa_club_ids(conn: sqlite3.Connection, club_name: str, season: Optional[str]) -> Set[int]:
    """UEFA ids of the clubs whose name matches ``club_name`` (restricted to one season unless it is 'all')."""
    scope = "" if not season or season == "all" else "AND season = ?"
    params = () if not scope else (season,)
    rows = conn.execute(
        f"SELECT home_id AS id, home_name AS name FROM matches WHERE competition_id IN (2, 3) {scope} "
        f"UNION SELECT away_id, away_name FROM matches WHERE competition_id IN (2, 3) {scope}",
        params * 2,
    ).fetchall()
    return {int(r["id"]) for r in rows if club_similarity(club_name, r["name"]) >= MATCH_THRESHOLD}


def _kickoff_millis(match_date: Optional[str], time_label: Optional[str]) -> Optional[int]:
    """UEFA kick-offs are stored as a London-time label plus the date; turn them into epoch milliseconds."""
    if not match_date:
        return None
    clock = (time_label or "").split(" ")[0]
    try:
        hour, minute = (int(part) for part in clock.split(":")[:2])
    except ValueError:
        hour, minute = 0, 0
    local = datetime.fromisoformat(match_date).replace(hour=hour, minute=minute, tzinfo=LONDON)
    return int(local.timestamp() * 1000)


def round_label(row: Dict[str, Any]) -> str:
    stage = row.get("stage") or "league"
    if stage == "group":
        return f"Grup {row.get('group_name')} · {row['gameweek']}. hafta" if row.get("group_name") else f"Grup aşaması · {row['gameweek']}. hafta"
    if stage == "league":
        return f"Lig aşaması · {row['gameweek']}. hafta"
    label = STAGE_LABELS.get(stage, stage)
    return f"{label} · {row['leg']}. maç" if row.get("leg") else label


def european_matches(conn: sqlite3.Connection, club_name: str, season: Optional[str]) -> List[Dict[str, Any]]:
    """The club's UCL and UEL matches in the same shape as its Premier League matches, plus competition info."""
    ids = uefa_club_ids(conn, club_name, season)
    if not ids:
        return []
    marks = ", ".join("?" * len(ids))
    scope = "" if not season or season == "all" else "AND season = ?"
    params = [*ids, *ids] + ([season] if scope else [])
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM matches WHERE competition_id IN (2, 3) AND (home_id IN ({marks}) OR away_id IN ({marks})) {scope} "
        "ORDER BY match_date, match_id",
        params,
    )]

    matches = []
    for row in rows:
        is_home = int(row["home_id"]) in ids
        mine, theirs = ("home", "away") if is_home else ("away", "home")
        played = row["status"] == "COMPLETED" and row["home_score"] is not None and row["away_score"] is not None
        team_score = int(row[f"{mine}_score"]) if played else None
        opp_score = int(row[f"{theirs}_score"]) if played else None
        result = "-" if not played else "W" if team_score > opp_score else "L" if team_score < opp_score else "D"
        matches.append({
            "match_id": row["match_id"],
            "season": row["season"],
            "status": "COMPLETED" if played else "UNPLAYED",
            "gameweek": row["gameweek"],
            "kickoff_label": row["kickoff_label"],
            "kickoff_millis": _kickoff_millis(row.get("match_date"), row.get("time_label")),
            "is_home": is_home,
            "opponent_id": int(row[f"{theirs}_id"]),
            "opponent_name": row[f"{theirs}_name"],
            "opponent_logo": row.get(f"{theirs}_logo"),
            "team_score": team_score,
            "opp_score": opp_score,
            "result": result,
            "competition": COMPETITIONS[row["competition_id"]],
            "stage": row.get("stage") or "league",
            "group": row.get("group_name"),
            "leg": row.get("leg"),
            "round_label": round_label(row),
            "home_penalties": row.get("home_penalties"),
            "away_penalties": row.get("away_penalties"),
            "ground_name": row.get("ground_name"),
            # the real UEFA ids and names, so the match page can pair lineups with the right side
            "home_id": int(row["home_id"]), "home_name": row["home_name"], "home_score": row["home_score"], "home_logo": row.get("home_logo"),
            "away_id": int(row["away_id"]), "away_name": row["away_name"], "away_score": row["away_score"], "away_logo": row.get("away_logo"),
        })
    return matches


# ---------------------------------------------------------------------------
# People: referees and players appear under slightly different spellings in the two sources
# ---------------------------------------------------------------------------

import json
import re


def _name_tokens(name: str) -> List[str]:
    return [token for token in re.split(r"[^a-z0-9]+", fold_text(name)) if token]


def same_person(left: str, right: str) -> bool:
    """Same full name, or same surname and first initial ('M. Oliver' / 'Michael Oliver')."""
    a, b = _name_tokens(left), _name_tokens(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return len(a) > 1 and len(b) > 1 and a[-1] == b[-1] and a[0][0] == b[0][0]


def _european_row_to_match(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "match_id": row["match_id"], "season": row["season"], "gameweek": row["gameweek"],
        "kickoff_label": row["kickoff_label"], "kickoff_millis": _kickoff_millis(row.get("match_date"), row.get("time_label")),
        "competition": COMPETITIONS[row["competition_id"]], "stage": row.get("stage") or "league", "group": row.get("group_name"),
        "round_label": round_label(row), "ground_name": row.get("ground_name"),
        "home_id": int(row["home_id"]), "home_name": row["home_name"], "home_logo": row.get("home_logo"), "home_score": row["home_score"],
        "away_id": int(row["away_id"]), "away_name": row["away_name"], "away_logo": row.get("away_logo"), "away_score": row["away_score"],
        "home_penalties": row.get("home_penalties"), "away_penalties": row.get("away_penalties"),
    }


def referee_european_matches(conn: sqlite3.Connection, referee_name: str, season: Optional[str]) -> Dict[str, Any]:
    """UCL/UEL matches a Premier League referee took charge of, with discipline totals where they are known."""
    scope = "" if not season or season == "all" else "AND season = ?"
    candidates = [r["referee_name"] for r in conn.execute(
        f"SELECT DISTINCT referee_name FROM matches WHERE competition_id IN (2, 3) AND referee_name IS NOT NULL {scope}",
        (season,) if scope else (),
    )]
    names = [name for name in candidates if same_person(referee_name, name)]
    if not names:
        return {"matches": [], "stats": None}

    marks = ", ".join("?" * len(names))
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM matches WHERE competition_id IN (2, 3) AND referee_name IN ({marks}) AND status = 'COMPLETED' {scope} "
        "ORDER BY match_date DESC, match_id DESC",
        (*names, *((season,) if scope else ())),
    )]
    matches = []
    for row in rows:
        entry = _european_row_to_match(row)
        for column in ("total_yellow_cards", "total_red_cards", "total_cards", "total_fouls"):
            entry[column] = row.get(column)  # None when the provider has no statistics for the match
        matches.append(entry)

    measured = [m for m in matches if m["total_cards"] is not None]
    count = len(measured)
    stats = {
        "matches_count": len(matches),
        "matches_with_stats": count,
        "total_yellow_cards": sum(m["total_yellow_cards"] or 0 for m in measured),
        "total_red_cards": sum(m["total_red_cards"] or 0 for m in measured),
        "total_cards": sum(m["total_cards"] for m in measured),
        "total_fouls": sum(m["total_fouls"] or 0 for m in measured),
        "avg_cards": round(sum(m["total_cards"] for m in measured) / count, 2) if count else None,
        "avg_fouls": round(sum(m["total_fouls"] or 0 for m in measured) / count, 2) if count else None,
    }
    return {"matches": matches, "stats": stats}


def player_european_log(conn: sqlite3.Connection, player_name: str, clubs_by_season: Dict[str, Set[str]]) -> Dict[str, Any]:
    """A Premier League player's UCL/UEL appearances, read from the stored provider player statistics.

    ``clubs_by_season`` says which club the player belonged to in each season (from his league match log), so a
    transfer does not credit a former club's European games to the new one."""
    logs: List[Dict[str, Any]] = []
    for season, clubs in clubs_by_season.items():
        for club in clubs:
            for match in european_matches(conn, club, season):
                payload = conn.execute(
                    "SELECT payload FROM external_match_payloads WHERE match_id = ? AND provider = 'TheStatsAPI' AND kind = 'player_stats'",
                    (match["match_id"],),
                ).fetchone()
                if payload is None:
                    continue
                entry = next((e for e in json.loads(payload["payload"]).get("data") or []
                              if e.get("played") and same_person(player_name, e.get("player_name") or "")), None)
                if entry is None:
                    continue
                shooting, passing = entry.get("shooting") or {}, entry.get("passing") or {}
                logs.append({
                    **{k: match[k] for k in ("match_id", "season", "gameweek", "kickoff_label", "is_home", "opponent_id", "opponent_name",
                                             "opponent_logo", "team_score", "opp_score", "competition", "stage", "group", "round_label",
                                             "home_id", "home_name", "home_score", "home_logo", "away_id", "away_name", "away_score", "away_logo",
                                             "ground_name")},
                    "kickoff": match["kickoff_label"], "team_name": club,
                    "started": bool(entry.get("started")), "minutes_played": entry.get("minutes_played") or 0,
                    "goals": shooting.get("goals") or 0, "assists": passing.get("assists") or 0,
                    "rating": entry.get("rating"),
                })
    logs.sort(key=lambda log: (log["season"], log["match_id"]))
    rated = [log["rating"] for log in logs if log["rating"] is not None]
    return {
        "matches": logs,
        "stats": {
            "appearances": len(logs), "minutes": sum(log["minutes_played"] for log in logs),
            "goals": sum(log["goals"] for log in logs), "assists": sum(log["assists"] for log in logs),
            "average_rating": round(sum(rated) / len(rated), 1) if rated else None,
        } if logs else None,
    }
