#!/usr/bin/env python3
"""
Build Player Registry & Match Logs Index
Parses all 760 match details JSON files to compute exact:
  - Player appearances
  - Minutes played
  - Goals scored
  - Assists provided
  - Team match log preview
Outputs:
  - data/processed/players_registry.json
  - data/processed/player_match_logs.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from tqdm import tqdm
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `python3 src/...py` import src.config
from src.config import PROCESSED_DIR, RAW_DIR  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_player_index")


def parse_player_data():
    raw_dir = RAW_DIR
    matches_dir = raw_dir / "matches"
    processed_dir = PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Load all seasons' fixtures to map match_id to season & gameweek
    match_meta = {}
    for season in ["2022_23", "2023_24", "2024_25", "2025_26", "2026_27"]:
        fix_path = raw_dir / f"fixtures_{season}.json"
        if fix_path.exists():
            with open(fix_path, "r", encoding="utf-8") as f:
                fixes = json.load(f)
            for fix in fixes:
                mid = int(fix["id"])
                gw = fix.get("gameweek", {}).get("gameweek")
                kickoff = fix.get("kickoff", {}).get("label", "")
                teams = fix.get("teams", [])
                h_name = teams[0].get("team", {}).get("name", "") if len(teams) > 0 else ""
                h_id = teams[0].get("team", {}).get("id", 0) if len(teams) > 0 else 0
                h_score = teams[0].get("score") if len(teams) > 0 else None
                a_name = teams[1].get("team", {}).get("name", "") if len(teams) > 1 else ""
                a_id = teams[1].get("team", {}).get("id", 0) if len(teams) > 1 else 0
                a_score = teams[1].get("score") if len(teams) > 1 else None

                match_meta[mid] = {
                    "match_id": mid,
                    "season": season,
                    "gameweek": gw,
                    "kickoff": kickoff,
                    "home_id": h_id,
                    "home_name": h_name,
                    "home_score": h_score,
                    "away_id": a_id,
                    "away_name": a_name,
                    "away_score": a_score,
                }

    detail_files = list(matches_dir.glob("*_details.json"))
    logger.info(f"Processing {len(detail_files)} detail files...")

    players: Dict[int, Dict[str, Any]] = {}
    player_logs: Dict[int, List[Dict[str, Any]]] = {}

    for fp in tqdm(detail_files, desc="Parsing player match logs"):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue

        raw_mid = d.get("id")
        if raw_mid is None:
            continue
        mid = int(raw_mid)
        meta = match_meta.get(mid)
        if meta is None:
            # Fallback: derive from the details file itself
            dt = d.get("teams") or []
            def _t(i, k, default=None):
                return (dt[i].get("team") or {}).get(k, default) if len(dt) > i else default
            gw_d = (d.get("gameweek") or {}).get("gameweek") if isinstance(d.get("gameweek"), dict) else d.get("gameweek")
            meta = {
                "season": "unknown", "gameweek": gw_d or 0,
                "kickoff": (d.get("kickoff") or {}).get("label", ""),
                "home_id": _t(0, "id", 0), "home_name": _t(0, "name", ""),
                "home_score": dt[0].get("score") if len(dt) > 0 else None,
                "away_id": _t(1, "id", 0), "away_name": _t(1, "name", ""),
                "away_score": dt[1].get("score") if len(dt) > 1 else None,
            }

        events = d.get("events", [])

        # Parse goals and assists from events
        goals_count: Dict[int, int] = {}
        assists_count: Dict[int, int] = {}
        sub_off: Dict[int, int] = {}  # pid -> minute subbed off
        sub_on: Dict[int, int] = {}   # pid -> minute subbed on

        for ev in events:
            ev_type = ev.get("type")
            clock_label = ev.get("clock", {}).get("label", "0'")
            try:
                min_val = int(clock_label.split("'")[0].split("+")[0])
            except Exception:
                min_val = 45

            if ev_type == "G":
                pid = ev.get("personId")
                if pid:
                    goals_count[pid] = goals_count.get(pid, 0) + 1
                aid = ev.get("assistId")
                if aid:
                    assists_count[aid] = assists_count.get(aid, 0) + 1
            elif ev_type == "S":
                # Substitution: sub on / sub off
                desc = ev.get("description", "")
                pid = ev.get("personId")
                if pid:
                    if desc == "ON":
                        sub_on[pid] = min_val
                    elif desc == "OFF":
                        sub_off[pid] = min_val

        teams_info = d.get("teams", [])
        team_lists = d.get("teamLists") or []
        if not isinstance(team_lists, list) or len(team_lists) == 0:
            continue

        for idx, tl in enumerate(team_lists):
            if not tl or not isinstance(tl, dict):
                continue
            tid = tl.get("teamId")
            tname = teams_info[idx].get("team", {}).get("name", "") if idx < len(teams_info) else ""
            is_home = (tid == meta["home_id"])
            opp_name = meta["away_name"] if is_home else meta["home_name"]
            opp_id = meta["away_id"] if is_home else meta["home_id"]
            team_score = meta["home_score"] if is_home else meta["away_score"]
            opp_score = meta["away_score"] if is_home else meta["home_score"]

            # Lineup players (starters)
            for p in tl.get("lineup", []):
                pid = p.get("id")
                if not pid:
                    continue

                if pid not in players:
                    alt = p.get("altIds") or {}
                    opta = alt.get("opta")
                    players[pid] = {
                        "id": pid,
                        "name": p.get("name", {}).get("display", "Unknown"),
                        "position": p.get("matchPosition") or p.get("info", {}).get("position", "M"),
                        "shirt": p.get("matchShirtNumber") or (p.get("info") or {}).get("shirtNum", 0),
                        "teamId": tid,
                        "teamName": tname,
                        "country": p.get("nationalTeam", {}).get("country", ""),
                        "opta_code": opta,
                        "photo_url": f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png" if opta else None,
                        "total_goals": 0,
                        "total_assists": 0,
                        "total_appearances": 0,
                        "total_minutes": 0,
                    }
                else:
                    if not players[pid].get("opta_code"):
                        alt = p.get("altIds") or {}
                        opta = alt.get("opta")
                        if opta:
                            players[pid]["opta_code"] = opta
                            players[pid]["photo_url"] = f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png"
                    if not players[pid].get("shirt"):
                        shirt = p.get("matchShirtNumber") or (p.get("info") or {}).get("shirtNum", 0)
                        if shirt:
                            players[pid]["shirt"] = shirt

                # Minutes played calculation: 90 or subbed off minute
                mins = sub_off.get(pid, 90)
                g = goals_count.get(pid, 0)
                a = assists_count.get(pid, 0)

                players[pid]["total_appearances"] += 1
                players[pid]["total_minutes"] += mins
                players[pid]["total_goals"] += g
                players[pid]["total_assists"] += a

                if pid not in player_logs:
                    player_logs[pid] = []

                player_logs[pid].append({
                    "match_id": mid,
                    "season": meta["season"],
                    "gameweek": meta["gameweek"],
                    "kickoff": meta["kickoff"],
                    "is_home": is_home,
                    "team_id": tid,
                    "team_name": tname,
                    "opponent_id": opp_id,
                    "opponent_name": opp_name,
                    "team_score": team_score,
                    "opp_score": opp_score,
                    "started": True,
                    "minutes_played": mins,
                    "goals": g,
                    "assists": a,
                })

            # Substitute players who came on
            for p in tl.get("substitutes", []):
                pid = p.get("id")
                if not pid:
                    continue

                if pid in sub_on or pid in goals_count or pid in assists_count:
                    min_on = sub_on.get(pid, 65)
                    mins = max(1, 90 - min_on)
                    g = goals_count.get(pid, 0)
                    a = assists_count.get(pid, 0)

                    if pid not in players:
                        alt = p.get("altIds") or {}
                        opta = alt.get("opta")
                        players[pid] = {
                            "id": pid,
                            "name": p.get("name", {}).get("display", "Unknown"),
                            "position": p.get("matchPosition") or p.get("info", {}).get("position", "M"),
                            "shirt": p.get("matchShirtNumber") or (p.get("info") or {}).get("shirtNum", 0),
                            "teamId": tid,
                            "teamName": tname,
                            "country": p.get("nationalTeam", {}).get("country", ""),
                            "opta_code": opta,
                            "photo_url": f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png" if opta else None,
                            "total_goals": 0,
                            "total_assists": 0,
                            "total_appearances": 0,
                            "total_minutes": 0,
                        }
                    else:
                        if not players[pid].get("opta_code"):
                            alt = p.get("altIds") or {}
                            opta = alt.get("opta")
                            if opta:
                                players[pid]["opta_code"] = opta
                                players[pid]["photo_url"] = f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png"
                        if not players[pid].get("shirt"):
                            shirt = p.get("matchShirtNumber") or (p.get("info") or {}).get("shirtNum", 0)
                            if shirt:
                                players[pid]["shirt"] = shirt

                    players[pid]["total_appearances"] += 1
                    players[pid]["total_minutes"] += mins
                    players[pid]["total_goals"] += g
                    players[pid]["total_assists"] += a

                    if pid not in player_logs:
                        player_logs[pid] = []

                    player_logs[pid].append({
                        "match_id": mid,
                        "season": meta["season"],
                        "gameweek": meta["gameweek"],
                        "kickoff": meta["kickoff"],
                        "is_home": is_home,
                        "team_id": tid,
                        "team_name": tname,
                        "opponent_id": opp_id,
                        "opponent_name": opp_name,
                        "team_score": team_score,
                        "opp_score": opp_score,
                        "started": False,
                        "minutes_played": mins,
                        "goals": g,
                        "assists": a,
                    })

    # Sort player logs chronologically and set latest team
    season_order = {'2022_23': -1, '2023_24': 0, '2024_25': 1, '2025_26': 2, '2026_27': 3}
    for pid in player_logs:
        player_logs[pid] = sorted(
            player_logs[pid], 
            key=lambda x: (season_order.get(x.get("season", ""), 0), float(x.get("gameweek") or 0))
        )
        if player_logs[pid] and pid in players:
            latest = player_logs[pid][-1]
            if latest.get("team_id"):
                players[pid]["teamId"] = latest["team_id"]
                players[pid]["teamName"] = latest["team_name"]

    players_list = sorted(list(players.values()), key=lambda x: x["name"])

    reg_path = processed_dir / "players_registry.json"
    logs_path = processed_dir / "player_match_logs.json"

    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(players_list, f, ensure_ascii=False, indent=2)

    with open(logs_path, "w", encoding="utf-8") as f:
        json.dump(player_logs, f, ensure_ascii=False)

    logger.info(f"Saved {len(players_list)} players to {reg_path}")
    logger.info(f"Saved match logs for {len(player_logs)} players to {logs_path}")


if __name__ == "__main__":
    parse_player_data()
