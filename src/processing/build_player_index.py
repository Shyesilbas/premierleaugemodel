#!/usr/bin/env python3
"""
Build Player Registry & Match Logs Index
Parses match details JSON files across cached seasons to compute:
  - Player appearances
  - Minutes played
  - Goals scored
  - Assists provided
  - Team match log preview
Outputs:
  - data/competitions/premier_league/processed/players_registry.json
  - data/competitions/premier_league/processed/player_match_logs.json

Closed/unchanged seasons reuse per-season processed index caches when neither their
fixture file nor their ``*_details.json`` inputs are newer on disk.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `python3 src/...py` import src.config
from src.config import PROCESSED_DIR, RAW_DIR, SEASON_ORDER, SEASONS, configure_logging  # noqa: E402

logger = logging.getLogger("build_player_index")


def _extract_details_for_matches(
    detail_paths: List[Path],
    match_meta: Dict[int, Dict[str, Any]],
    season_label: str,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, List[Dict[str, Any]]]]:
    players: Dict[int, Dict[str, Any]] = {}
    player_logs: Dict[int, List[Dict[str, Any]]] = {}

    for fp in tqdm(detail_paths, desc=f"Parsing player logs ({season_label})"):
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
            dt = d.get("teams") or []

            def _t(i, k, default=None):
                return (dt[i].get("team") or {}).get(k, default) if len(dt) > i else default

            gw_d = (d.get("gameweek") or {}).get("gameweek") if isinstance(d.get("gameweek"), dict) else d.get("gameweek")
            meta = {
                "match_id": mid,
                "season": season_label,
                "gameweek": gw_d or 0,
                "kickoff": (d.get("kickoff") or {}).get("label", ""),
                "home_id": _t(0, "id", 0),
                "home_name": _t(0, "name", ""),
                "home_score": dt[0].get("score") if len(dt) > 0 else None,
                "away_id": _t(1, "id", 0),
                "away_name": _t(1, "name", ""),
                "away_score": dt[1].get("score") if len(dt) > 1 else None,
            }

        events = d.get("events", [])
        goals_count: Dict[int, int] = {}
        assists_count: Dict[int, int] = {}
        sub_off: Dict[int, int] = {}
        sub_on: Dict[int, int] = {}

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
            is_home = tid == meta["home_id"]
            opp_name = meta["away_name"] if is_home else meta["home_name"]
            opp_id = meta["away_id"] if is_home else meta["home_id"]
            team_score = meta["home_score"] if is_home else meta["away_score"]
            opp_score = meta["away_score"] if is_home else meta["home_score"]

            def _ensure_player(p_entry: Dict[str, Any]) -> int:
                pid_val = p_entry.get("id")
                alt = p_entry.get("altIds") or {}
                opta = alt.get("opta")
                shirt_val = p_entry.get("matchShirtNumber") or (p_entry.get("info") or {}).get("shirtNum", 0)
                if pid_val not in players:
                    players[pid_val] = {
                        "id": pid_val,
                        "name": p_entry.get("name", {}).get("display", "Unknown"),
                        "position": p_entry.get("matchPosition") or p_entry.get("info", {}).get("position", "M"),
                        "shirt": shirt_val,
                        "teamId": tid,
                        "teamName": tname,
                        "country": p_entry.get("nationalTeam", {}).get("country", ""),
                        "opta_code": opta,
                        "photo_url": f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png" if opta else None,
                        "total_goals": 0,
                        "total_assists": 0,
                        "total_appearances": 0,
                        "total_minutes": 0,
                    }
                else:
                    if not players[pid_val].get("opta_code") and opta:
                        players[pid_val]["opta_code"] = opta
                        players[pid_val]["photo_url"] = f"https://resources.premierleague.com/premierleague/photos/players/250x250/{opta}.png"
                    if not players[pid_val].get("shirt") and shirt_val:
                        players[pid_val]["shirt"] = shirt_val
                return pid_val

            for p in tl.get("lineup", []):
                pid = p.get("id")
                if not pid:
                    continue
                _ensure_player(p)
                mins = sub_off.get(pid, 90)
                g = goals_count.get(pid, 0)
                a = assists_count.get(pid, 0)
                players[pid]["total_appearances"] += 1
                players[pid]["total_minutes"] += mins
                players[pid]["total_goals"] += g
                players[pid]["total_assists"] += a
                player_logs.setdefault(pid, []).append({
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
                    "position": p.get("matchPosition") or (p.get("info") or {}).get("position", "M"),
                    "minutes_played": mins,
                    "goals": g,
                    "assists": a,
                })

            for p in tl.get("substitutes", []):
                pid = p.get("id")
                if not pid:
                    continue
                if pid in sub_on or pid in goals_count or pid in assists_count:
                    min_on = sub_on.get(pid, 65)
                    mins = max(1, 90 - min_on)
                    g = goals_count.get(pid, 0)
                    a = assists_count.get(pid, 0)
                    _ensure_player(p)
                    players[pid]["total_appearances"] += 1
                    players[pid]["total_minutes"] += mins
                    players[pid]["total_goals"] += g
                    players[pid]["total_assists"] += a
                    player_logs.setdefault(pid, []).append({
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
                        "position": p.get("matchPosition") or (p.get("info") or {}).get("position", "M"),
                        "minutes_played": mins,
                        "goals": g,
                        "assists": a,
                    })

    return players, player_logs


def _season_index_fresh(cache_path: Path, fixture_path: Path, detail_paths: List[Path]) -> bool:
    if not cache_path.exists() or cache_path.stat().st_size == 0:
        return False
    cache_mtime = cache_path.stat().st_mtime_ns
    if fixture_path.exists() and fixture_path.stat().st_mtime_ns > cache_mtime:
        return False
    return not any(p.exists() and p.stat().st_mtime_ns > cache_mtime for p in detail_paths)


def parse_player_data(force: bool = False):
    raw_dir = RAW_DIR
    matches_dir = raw_dir / "matches"
    processed_dir = PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)

    match_meta: Dict[int, Dict[str, Any]] = {}
    season_match_ids: Dict[str, List[int]] = {s: [] for s in SEASONS}
    for season in SEASONS:
        fix_path = raw_dir / f"fixtures_{season}.json"
        if fix_path.exists():
            with open(fix_path, "r", encoding="utf-8") as f:
                fixes = json.load(f)
            for fix in fixes:
                mid = int(fix["id"])
                season_match_ids[season].append(mid)
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

    known_mids = set(match_meta)
    detail_files = sorted(matches_dir.glob("*_details.json"))
    orphan_details: List[Path] = []
    season_details: Dict[str, List[Path]] = {s: [] for s in SEASONS}
    for fp in detail_files:
        stem_id = fp.stem.replace("_details", "")
        if stem_id.isdigit() and int(stem_id) in known_mids:
            season_details[match_meta[int(stem_id)]["season"]].append(fp)
        else:
            orphan_details.append(fp)

    players: Dict[int, Dict[str, Any]] = {}
    player_logs: Dict[int, List[Dict[str, Any]]] = {}

    def _merge_season_chunk(s_players: Dict[Any, Dict[str, Any]], s_logs: Dict[Any, List[Dict[str, Any]]]) -> None:
        for raw_pid, p_info in s_players.items():
            pid = int(raw_pid)
            if pid not in players:
                players[pid] = dict(p_info)
            else:
                players[pid]["total_goals"] += int(p_info.get("total_goals") or 0)
                players[pid]["total_assists"] += int(p_info.get("total_assists") or 0)
                players[pid]["total_appearances"] += int(p_info.get("total_appearances") or 0)
                players[pid]["total_minutes"] += int(p_info.get("total_minutes") or 0)
                if not players[pid].get("opta_code") and p_info.get("opta_code"):
                    players[pid]["opta_code"] = p_info["opta_code"]
                    players[pid]["photo_url"] = p_info.get("photo_url")
                if not players[pid].get("shirt") and p_info.get("shirt"):
                    players[pid]["shirt"] = p_info["shirt"]
                if p_info.get("teamId"):
                    players[pid]["teamId"] = p_info["teamId"]
                    players[pid]["teamName"] = p_info.get("teamName") or players[pid].get("teamName")
        for raw_pid, entries in s_logs.items():
            pid = int(raw_pid)
            player_logs.setdefault(pid, []).extend(entries)

    ordered_seasons = sorted(SEASONS, key=lambda s: SEASON_ORDER.get(s, 0))
    for season in ordered_seasons:
        paths = season_details.get(season, [])
        if not paths:
            continue
        fix_path = raw_dir / f"fixtures_{season}.json"
        cache_path = processed_dir / f".player_index_{season}.json"
        if not force and _season_index_fresh(cache_path, fix_path, paths):
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                _merge_season_chunk(cached.get("players", {}), cached.get("logs", {}))
                logger.info("Reused fresh player index cache for season %s (%d files)", season, len(paths))
                continue
            except (OSError, json.JSONDecodeError):
                pass
        s_players, s_logs = _extract_details_for_matches(paths, match_meta, season)
        cache_path.write_text(
            json.dumps({"players": {str(k): v for k, v in s_players.items()}, "logs": {str(k): v for k, v in s_logs.items()}}, ensure_ascii=False),
            encoding="utf-8",
        )
        _merge_season_chunk(s_players, s_logs)

    if orphan_details:
        o_players, o_logs = _extract_details_for_matches(orphan_details, match_meta, "unknown")
        _merge_season_chunk(o_players, o_logs)

    for pid in player_logs:
        player_logs[pid] = sorted(
            player_logs[pid],
            key=lambda x: (SEASON_ORDER.get(x.get("season", ""), 0), float(x.get("gameweek") or 0)),
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

    logger.info("Saved %d players to %s", len(players_list), reg_path)
    logger.info("Saved match logs for %d players to %s", len(player_logs), logs_path)


if __name__ == "__main__":
    configure_logging()
    parser = argparse.ArgumentParser(description="Build player registry and match logs index.")
    parser.add_argument("--force", action="store_true", help="Re-parse all seasons even when cached indexes are fresh")
    cli_args = parser.parse_args()
    parse_player_data(force=cli_args.force)
