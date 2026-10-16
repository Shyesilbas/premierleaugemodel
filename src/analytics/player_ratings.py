#!/usr/bin/env python3
"""
Dynamic Player Rating & Lineup Impact Engine
Computes 0-10 player performance ratings (Overall, Attack, Defense, Cards Risk)
using 70% Recent Form (EWMA last 5 games) + 30% Season Baseline.
Provides projected & official lineup aggregations and transparent model modulators.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("player_ratings")

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MATCHES_RAW_DIR = DATA_DIR / "raw" / "matches"

# Global module caches
_bookings_cache: Optional[Dict[int, Dict[int, Dict[str, int]]]] = None
_player_logs_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None
_player_reg_cache: Optional[Dict[int, Dict[str, Any]]] = None


def get_match_bookings_map() -> Dict[int, Dict[int, Dict[str, int]]]:
    """
    Returns map: match_id -> player_id -> {'yellow': int, 'red': int}.
    Loaded from cached json or extracted once from raw match details.
    """
    global _bookings_cache
    if _bookings_cache is not None:
        return _bookings_cache

    cache_file = PROCESSED_DIR / "match_player_bookings_cache.json"
    if cache_file.exists():
        try:
            with cache_file.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)
                _bookings_cache = {
                    int(mid): {int(pid): b for pid, b in pmap.items()}
                    for mid, pmap in raw_data.items()
                }
                return _bookings_cache
        except Exception as e:
            logger.warning(f"Error reading match_player_bookings_cache.json: {e}")

    # Build from raw match details
    bookings_map: Dict[int, Dict[int, Dict[str, int]]] = {}
    if MATCHES_RAW_DIR.exists():
        for f in MATCHES_RAW_DIR.glob("*_details.json"):
            try:
                mid_str = f.stem.replace("_details", "")
                if not mid_str.isdigit():
                    continue
                mid = int(mid_str)
                d = json.loads(f.read_text(encoding="utf-8"))
                b_map: Dict[int, Dict[str, int]] = {}
                for e in d.get("events", []):
                    if e.get("type") == "B":
                        pid = e.get("personId")
                        desc = e.get("description", "Y")
                        if pid:
                            pid_int = int(pid)
                            if pid_int not in b_map:
                                b_map[pid_int] = {"yellow": 0, "red": 0}
                            if desc in ("R", "Y2R"):
                                b_map[pid_int]["red"] += 1
                            else:
                                b_map[pid_int]["yellow"] += 1
                if b_map:
                    bookings_map[mid] = b_map
            except Exception:
                continue

    _bookings_cache = bookings_map
    try:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in bookings_map.items()}, f)
    except Exception as e:
        logger.warning(f"Could not persist bookings cache: {e}")

    return _bookings_cache


def get_all_player_logs() -> Dict[str, List[Dict[str, Any]]]:
    """Returns player match logs indexed by player ID string."""
    global _player_logs_cache
    if _player_logs_cache is not None:
        return _player_logs_cache
    logs_file = PROCESSED_DIR / "player_match_logs.json"
    if logs_file.exists():
        with logs_file.open("r", encoding="utf-8") as f:
            _player_logs_cache = json.load(f)
    else:
        _player_logs_cache = {}
    return _player_logs_cache


def get_all_players_registry() -> Dict[int, Dict[str, Any]]:
    """Returns players registry indexed by int player ID."""
    global _player_reg_cache
    if _player_reg_cache is not None:
        return _player_reg_cache
    reg_file = PROCESSED_DIR / "players_registry.json"
    if reg_file.exists():
        with reg_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            _player_reg_cache = {int(p["id"]): p for p in data if "id" in p}
    else:
        _player_reg_cache = {}
    return _player_reg_cache


def calculate_single_match_score(
    log: Dict[str, Any],
    pos: str,
    bookings_map: Dict[int, Dict[int, Dict[str, int]]],
    player_id: int
) -> Optional[Dict[str, float]]:
    """
    Computes a calibrated 0-10 rating for a player in a single match.
    Returns: {'overall': float, 'attack': float, 'defense': float, 'cards_cost': float} or None if not qualified.
    """
    mins = int(log.get("minutes_played") or log.get("minutes") or 0)
    mid = int(log.get("match_id") or 0)
    b_info = bookings_map.get(mid, {}).get(player_id, {"yellow": 0, "red": 0})
    y_cards = int(b_info.get("yellow") or log.get("yellow_cards") or log.get("yellow") or 0)
    r_cards = int(b_info.get("red") or log.get("red_cards") or log.get("red") or 0)

    g = int(log.get("goals") or 0)
    a = int(log.get("assists") or 0)
    t_score = int(log.get("team_score") or 0)
    o_score = int(log.get("opp_score") or 0)

    pens_won = int(log.get("penalties_won") or 0)
    pens_conceded = int(log.get("penalties_conceded") or 0)
    pens_missed = int(log.get("penalties_missed") or 0)
    shots_ot = int(log.get("shots_ontarget") or 0)
    saves = int(log.get("saves") or 0)

    pos_upper = str(pos or "M").upper()
    is_gk_def = pos_upper in ("G", "GK", "D", "CB", "LB", "RB", "LWB", "RWB")
    is_mid = pos_upper in ("M", "CM", "DM", "AM", "LM", "RM")
    is_fwd = pos_upper in ("F", "FW", "CF", "ST", "RW", "LW")

    has_impact = (
        g > 0 or a > 0 or y_cards > 0 or r_cards > 0
        or pens_won > 0 or pens_conceded > 0 or pens_missed > 0
        or shots_ot > 0 or saves > 0
    )
    # If played less than 10 mins and had no decisive impact, do not score
    if mins < 10 and not has_impact:
        return None

    # Base match rating is 6.0
    base_overall = 6.0
    base_attack = 6.0
    base_defense = 6.0

    # 1. Goal & Assist Impact by Position
    if is_fwd:
        att_add = (g * 1.25) + (a * 0.70)
    elif is_mid:
        att_add = (g * 1.40) + (a * 0.80)
    else:  # Def / GK
        att_add = (g * 1.65) + (a * 0.90)

    base_attack += att_add
    base_overall += att_add

    # 2. Additional micro-metrics if present
    base_overall += (pens_won * 0.75)
    base_overall -= (pens_conceded * 1.10)
    base_overall -= (pens_missed * 1.15)
    if shots_ot > g:
        base_overall += (shots_ot - g) * 0.20
    if pos_upper in ("G", "GK"):
        base_overall += (saves * 0.35)

    # 3. Defense additions / penalties based on position
    if is_gk_def:
        if o_score == 0 and mins >= 60:
            def_bonus = 0.85
        elif o_score == 1:
            def_bonus = 0.15
        elif o_score >= 3:
            def_bonus = -0.35 * (o_score - 2)
        else:
            def_bonus = 0.0
        base_defense += def_bonus
        base_overall += def_bonus
    elif is_mid:
        if o_score == 0 and mins >= 60:
            def_bonus = 0.35
        elif o_score >= 4:
            def_bonus = -0.3
        else:
            def_bonus = 0.0
        base_defense += def_bonus
        base_overall += def_bonus * 0.5
    else:  # Attackers
        if o_score >= 4:
            base_overall -= 0.15

    # 4. Bookings penalty from match events
    cards_penalty = (y_cards * 0.5) + (r_cards * 1.8)
    base_overall -= cards_penalty

    # 5. Result adjustment
    if t_score > o_score:
        base_overall += 0.25
    elif t_score < o_score:
        base_overall -= 0.25

    return {
        "overall": max(3.0, min(10.0, round(base_overall, 1))),
        "attack": max(3.0, min(10.0, round(base_attack, 1))),
        "defense": max(3.0, min(10.0, round(base_defense, 1))),
        "cards_cost": round(cards_penalty, 2),
        "yellow": y_cards,
        "red": r_cards,
    }


def calculate_detailed_match_score(
    stats: Dict[str, Any],
    pos: str,
    team_score: int = 0,
    opp_score: int = 0,
) -> Dict[str, float]:
    """
    Computes a comprehensive 0-10 single match performance rating for an actual completed match.
    Considers goals, assists, shots, fouls won, fouls committed, offsides, cards,
    penalties won, penalties conceded, penalties missed, saves, and clean sheets.
    """
    mins = int(stats.get("minutes") or stats.get("minutes_played") or 0)
    g = int(stats.get("goals") or 0)
    a = int(stats.get("assists") or 0)
    shots_ot = int(stats.get("shots_ontarget") or 0)
    shots_total = int(stats.get("shots") or 0)
    shots_off = max(0, shots_total - shots_ot)
    fouls_won = int(stats.get("fouls_won") or 0)
    fouls_lost = int(stats.get("fouls_committed") or 0)
    offs = int(stats.get("offsides") or 0)
    yc = int(stats.get("yellow_cards") or stats.get("yellow") or 0)
    rc = int(stats.get("red_cards") or stats.get("red") or 0)
    pens_won = int(stats.get("penalties_won") or 0)
    pens_conceded = int(stats.get("penalties_conceded") or 0)
    pens_missed = int(stats.get("penalties_missed") or 0)
    saves = int(stats.get("saves") or 0)

    pos_upper = str(pos or "M").upper()
    is_gk_def = pos_upper in ("G", "GK", "D", "CB", "LB", "RB", "LWB", "RWB")
    is_mid = pos_upper in ("M", "CM", "DM", "AM", "LM", "RM")
    is_fwd = pos_upper in ("F", "FW", "CF", "ST", "RW", "LW")

    has_impact = (
        g > 0 or a > 0 or yc > 0 or rc > 0 
        or pens_won > 0 or pens_conceded > 0 or pens_missed > 0 
        or shots_ot > 0 or saves > 0
    )
    if mins < 10 and not has_impact:
        return {"overall": None, "attack": None, "defense": None, "qualified": False}

    base = 6.0

    # 1. Goal & Assist Impact by Position
    if is_fwd:
        base += (g * 1.25) + (a * 0.70)
    elif is_mid:
        base += (g * 1.40) + (a * 0.80)
    else:  # Def / GK
        base += (g * 1.65) + (a * 0.90)

    # 2. Shots on target & attempts
    non_goal_sot = max(0, shots_ot - g)
    base += (non_goal_sot * 0.20) + (shots_off * 0.05)

    # 3. Penalties (Conceded / Missed / Won)
    base += (pens_won * 0.75)
    base -= (pens_conceded * 1.10)  # Penalty conceded penalty
    base -= (pens_missed * 1.15)    # Penalty missed penalty

    # 4. Fouls won / lost / offsides
    base += (fouls_won * 0.10)
    base -= (fouls_lost * 0.08)
    base -= (offs * 0.10)

    # 5. Goalkeeper Saves
    if pos_upper in ("G", "GK"):
        base += (saves * 0.35)

    # 6. Clean Sheet & Defense Resilience
    if is_gk_def:
        if opp_score == 0 and mins >= 60:
            base += 0.85
        elif opp_score == 1:
            base += 0.15
        elif opp_score >= 3:
            base -= (opp_score - 2) * 0.35
    elif is_mid:
        if opp_score == 0 and mins >= 60:
            base += 0.35
        elif opp_score >= 4:
            base -= 0.30

    # 7. Disciplinary Cards
    base -= (yc * 0.50) + (rc * 1.80)

    # 8. Team Result
    if team_score > opp_score:
        base += 0.25
    elif team_score < opp_score:
        base -= 0.25

    final_score = max(3.0, min(10.0, round(base, 1)))
    return {
        "overall": final_score,
        "attack": round(max(3.0, min(10.0, base + (g * 0.3) + (a * 0.2))), 1),
        "defense": round(max(3.0, min(10.0, base - (g * 0.2))), 1),
    }


def get_player_dynamic_rating(
    player_id: int,
    season: Optional[str] = None,
    as_of_match_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Computes a player's dynamic 0-10 rating using 70% Recent Form (EWMA last 5)
    + 30% Season Baseline, strictly prior to as_of_match_id (no future data leakage).
    """
    all_logs = get_all_player_logs()
    reg = get_all_players_registry()
    bookings_map = get_match_bookings_map()

    p_info = reg.get(player_id, {})
    p_pos = p_info.get("position") or "M"
    p_name = p_info.get("name") or f"Oyuncu #{player_id}"
    shirt = p_info.get("shirt")

    p_logs = all_logs.get(str(player_id), [])
    if not p_logs:
        return {
            "player_id": player_id,
            "name": p_name,
            "position": p_pos,
            "shirt": shirt,
            "overall_rating": 6.0,
            "attack_rating": 6.0,
            "defense_rating": 6.0,
            "cards_risk": 3.0,
            "form_label": "Yeterli Veri Yok",
            "trend": "stable",
            "recent_scores": [],
        }

    # Filter logs prior to as_of_match_id if specified
    valid_logs: List[Dict[str, Any]] = []
    for l in p_logs:
        if as_of_match_id and int(l.get("match_id", 0)) == as_of_match_id:
            break
        valid_logs.append(l)

    # Filter by season if requested
    season_logs = [l for l in valid_logs if not season or l.get("season") == season]
    if not season_logs and valid_logs:
        season_logs = valid_logs

    # Compute scores for qualified matches (>= 10 mins or decisive impact)
    scored_matches: List[Dict[str, Any]] = []
    for l in valid_logs:
        m_score = calculate_single_match_score(l, p_pos, bookings_map, player_id)
        if m_score is not None:
            scored_matches.append({**l, **m_score})

    if not scored_matches:
        return {
            "player_id": player_id,
            "name": p_name,
            "position": p_pos,
            "shirt": shirt,
            "overall_rating": 6.0,
            "attack_rating": 6.0,
            "defense_rating": 6.0,
            "cards_risk": 3.0,
            "form_label": "Lig Ortalaması",
            "trend": "stable",
            "recent_scores": [6.0],
        }

    # 1. Season Baseline (%30 weight)
    season_scored = [m for m in scored_matches if not season or m.get("season") == season]
    if len(season_scored) < 3:
        season_scored = scored_matches

    season_avg_overall = sum(m["overall"] for m in season_scored) / len(season_scored)
    season_avg_att = sum(m["attack"] for m in season_scored) / len(season_scored)
    season_avg_def = sum(m["defense"] for m in season_scored) / len(season_scored)

    # 2. Recent Form - Son 5 Maç EWMA (%70 weight)
    recent_5 = scored_matches[-5:]
    n_recent = len(recent_5)
    if n_recent == 5:
        weights = [0.10, 0.15, 0.20, 0.25, 0.30]
    else:
        # Normalized linear progression
        raw_w = [i + 1 for i in range(n_recent)]
        w_sum = sum(raw_w)
        weights = [w / w_sum for w in raw_w]

    recent_ewma_overall = sum(w * m["overall"] for w, m in zip(weights, recent_5))
    recent_ewma_att = sum(w * m["attack"] for w, m in zip(weights, recent_5))
    recent_ewma_def = sum(w * m["defense"] for w, m in zip(weights, recent_5))

    # 3. Composite 70/30 Ratings
    composite_overall = round(0.70 * recent_ewma_overall + 0.30 * season_avg_overall, 2)
    composite_att = round(0.70 * recent_ewma_att + 0.30 * season_avg_att, 2)
    composite_def = round(0.70 * recent_ewma_def + 0.30 * season_avg_def, 2)

    # 4. Cards & Aggression Risk (0 to 10 scale)
    total_mins = sum(int(m.get("minutes_played") or 0) for m in scored_matches)
    total_y = sum(m.get("yellow", 0) for m in scored_matches)
    total_r = sum(m.get("red", 0) for m in scored_matches)
    cards_per_90 = ((total_y + 2.0 * total_r) / max(90, total_mins)) * 90.0

    # Scale cards_per_90: 0.18 is league average (~4.0), 0.35+ is elite aggressive (7.5 - 9.5)
    cards_risk = min(10.0, max(0.5, round(cards_per_90 * 22.0, 1)))

    # Trend (Son 2 maç vs önceki 3 maç)
    if len(recent_5) >= 4:
        last2_avg = sum(m["overall"] for m in recent_5[-2:]) / 2.0
        prev_avg = sum(m["overall"] for m in recent_5[:-2]) / len(recent_5[:-2])
        if last2_avg - prev_avg > 0.4:
            trend = "up"
        elif prev_avg - last2_avg > 0.4:
            trend = "down"
        else:
            trend = "stable"
    else:
        trend = "stable"

    form_label = (
        "Yıldız Formda" if composite_overall >= 7.8 else (
            "Formda" if composite_overall >= 6.8 else (
                "Normal" if composite_overall >= 5.8 else "Düşüşte"
            )
        )
    )

    return {
        "player_id": player_id,
        "name": p_name,
        "position": p_pos,
        "shirt": shirt,
        "overall_rating": composite_overall,
        "attack_rating": composite_att,
        "defense_rating": composite_def,
        "cards_risk": cards_risk,
        "form_label": form_label,
        "trend": trend,
        "recent_scores": [m["overall"] for m in recent_5],
    }


def get_team_starting_xi(
    team_id: int,
    match_id: Optional[int] = None,
    season: str = "2026_27",
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Returns (is_official, starters_list).
    If match_id has official teamLists lineup in raw matches, returns (True, starters).
    Otherwise returns (False, projected_starting_xi) computed from most frequent starters.
    """
    if match_id:
        path = MATCHES_RAW_DIR / f"{match_id}_details.json"
        if path.exists():
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                teams_info = d.get("teams", [])
                for idx, tl in enumerate(d.get("teamLists") or []):
                    if not tl or not isinstance(tl, dict):
                        continue
                    t_id = tl.get("teamId")
                    if not t_id and idx < len(teams_info):
                        t_id = teams_info[idx].get("team", {}).get("id")
                    
                    if t_id and int(t_id) == int(team_id):
                        lineup = tl.get("lineup") or []
                        if len(lineup) == 11:
                            starters = []
                            for p in lineup:
                                pid = int(p["id"])
                                ratings = get_player_dynamic_rating(pid, season, as_of_match_id=match_id)
                                starters.append({
                                    "id": pid,
                                    "name": p.get("name", {}).get("display") or ratings["name"],
                                    "matchPosition": p.get("matchPosition") or ratings["position"],
                                    "shirt": p.get("matchShirtNumber") or ratings["shirt"],
                                    "captain": p.get("captain", False),
                                    **ratings,
                                })
                            return True, starters
            except Exception as e:
                logger.warning(f"Error reading match details for match {match_id}: {e}")

    # Fallback to Projected Starting XI (Muhtemel 11)
    all_logs = get_all_player_logs()
    reg = get_all_players_registry()

    starter_counts: Dict[int, int] = defaultdict(int)
    for pid_str, logs in all_logs.items():
        pid = int(pid_str)
        t_logs = [l for l in logs if int(l.get("team_id") or 0) == team_id and (not season or l.get("season") == season)]
        for l in t_logs[-8:]:  # look at last 8 games
            if l.get("started"):
                starter_counts[pid] += 1

    # Sort candidates by start frequency
    sorted_candidates = sorted(starter_counts.items(), key=lambda x: x[1], reverse=True)

    # Pick 1 GK, 4 DEF, 3-4 MID, 2-3 FWD to form a sensible 11
    gks, defs, mids, fwds = [], [], [], []
    for pid, _ in sorted_candidates:
        p_info = reg.get(pid, {})
        pos = p_info.get("position", "M").upper()
        if pos in ("G", "GK"):
            if len(gks) < 1:
                gks.append(pid)
        elif pos in ("D", "CB", "LB", "RB", "LWB", "RWB"):
            if len(defs) < 4:
                defs.append(pid)
        elif pos in ("M", "CM", "DM", "AM", "LM", "RM"):
            if len(mids) < 4:
                mids.append(pid)
        else:
            if len(fwds) < 2:
                fwds.append(pid)

    chosen_pids = (gks + defs + mids + fwds)[:11]
    # Fill up if less than 11
    if len(chosen_pids) < 11:
        for pid, _ in sorted_candidates:
            if pid not in chosen_pids and len(chosen_pids) < 11:
                chosen_pids.append(pid)

    starters = []
    for pid in chosen_pids:
        ratings = get_player_dynamic_rating(pid, season)
        starters.append({
            "id": pid,
            "name": ratings["name"],
            "matchPosition": ratings["position"],
            "shirt": ratings["shirt"],
            "captain": False,
            **ratings,
        })

    return False, starters


def analyze_match_starting_xis(
    home_id: int,
    away_id: int,
    match_id: Optional[int] = None,
    season: str = "2026_27",
    referee_avg_cards: float = 4.15,
) -> Dict[str, Any]:
    """
    Analyzes starting XIs for both teams, computes team-level form aggregates,
    and returns transparent model impact modifiers.
    """
    is_home_official, home_starters = get_team_starting_xi(team_id=home_id, match_id=match_id, season=season)
    is_away_official, away_starters = get_team_starting_xi(team_id=away_id, match_id=match_id, season=season)
    is_official = is_home_official and is_away_official

    # Team aggregate metrics (mean of 11 starters)
    h_overall = round(sum(p["overall_rating"] for p in home_starters) / max(1, len(home_starters)), 2)
    a_overall = round(sum(p["overall_rating"] for p in away_starters) / max(1, len(away_starters)), 2)

    # Attackers + Midfielders attack rating
    h_att = round(sum(p["attack_rating"] for p in home_starters if p["position"] in ("F", "M")) / max(1, len([p for p in home_starters if p["position"] in ("F", "M")])), 2)
    a_att = round(sum(p["attack_rating"] for p in away_starters if p["position"] in ("F", "M")) / max(1, len([p for p in away_starters if p["position"] in ("F", "M")])), 2)

    # Defenders + Goalkeeper defense rating
    h_def = round(sum(p["defense_rating"] for p in home_starters if p["position"] in ("D", "G")) / max(1, len([p for p in home_starters if p["position"] in ("D", "G")])), 2)
    a_def = round(sum(p["defense_rating"] for p in away_starters if p["position"] in ("D", "G")) / max(1, len([p for p in away_starters if p["position"] in ("D", "G")])), 2)

    # Aggression / Cards Risk
    h_card_risk = round(sum(p["cards_risk"] for p in home_starters) / max(1, len(home_starters)), 1)
    a_card_risk = round(sum(p["cards_risk"] for p in away_starters) / max(1, len(away_starters)), 1)
    match_card_risk = round((h_card_risk + a_card_risk) / 2.0, 1)

    # Top in-form players
    h_top = sorted(home_starters, key=lambda x: x["overall_rating"], reverse=True)[:2]
    a_top = sorted(away_starters, key=lambda x: x["overall_rating"], reverse=True)[:2]

    # Calculate Modulators (Deviation from 6.2 league starting XI benchmark)
    BENCHMARK = 6.20

    # 1. Goal lambda modifiers
    # High attack form vs opposing weak defense yields positive goal delta
    delta_home_goals = round(((h_att - BENCHMARK) * 0.35) - ((a_def - BENCHMARK) * 0.20), 2)
    delta_away_goals = round(((a_att - BENCHMARK) * 0.35) - ((h_def - BENCHMARK) * 0.20), 2)

    # 2. 1X2 Win Probability Modifiers (swing percentage points)
    overall_diff = h_overall - a_overall
    delta_home_win_pct = round(overall_diff * 4.5, 1)
    delta_away_win_pct = round(-overall_diff * 4.5, 1)

    # 3. Cards Expectation Modifier
    # Average team card risk is ~4.0. If combined card risk is 6.5+, extra cards expected
    ref_factor = (referee_avg_cards / 4.15) if referee_avg_cards else 1.0
    cards_deviation = (match_card_risk - 4.0) * 0.45 * ref_factor
    delta_cards = round(cards_deviation, 1)

    # Summary label
    status_label = "Resmi Kadrolar Açıklandı" if is_official else "Muhtemel 11'ler Baz Alındı"
    impact_bullets = []
    if delta_home_goals != 0:
        sign = "+" if delta_home_goals > 0 else ""
        impact_bullets.append(f"Ev Gol Etkisi: {sign}{delta_home_goals}")
    if delta_away_goals != 0:
        sign = "+" if delta_away_goals > 0 else ""
        impact_bullets.append(f"Dep Gol Etkisi: {sign}{delta_away_goals}")
    if delta_cards != 0:
        sign = "+" if delta_cards > 0 else ""
        impact_bullets.append(f"Kart Beklentisi: {sign}{delta_cards} Kart")

    return {
        "is_official": is_official,
        "status_label": status_label,
        "summary_text": " · ".join(impact_bullets) if impact_bullets else "Dengeli İlk 11 Formu",
        "home_xi": {
            "overall_rating": h_overall,
            "team_overall": h_overall,
            "attack_rating": h_att,
            "team_attack": h_att,
            "defense_rating": h_def,
            "team_defense": h_def,
            "cards_risk": h_card_risk,
            "team_cards_risk": h_card_risk,
            "starters": home_starters,
            "top_performers": [{"name": p["name"], "rating": p["overall_rating"]} for p in h_top],
        },
        "away_xi": {
            "overall_rating": a_overall,
            "team_overall": a_overall,
            "attack_rating": a_att,
            "team_attack": a_att,
            "defense_rating": a_def,
            "team_defense": a_def,
            "cards_risk": a_card_risk,
            "team_cards_risk": a_card_risk,
            "starters": away_starters,
            "top_performers": [{"name": p["name"], "rating": p["overall_rating"]} for p in a_top],
        },
        "lineup_impact": {
            "delta_home_goals": delta_home_goals,
            "delta_away_goals": delta_away_goals,
            "delta_cards": delta_cards,
            "delta_home_win_pct": delta_home_win_pct,
            "delta_away_win_pct": delta_away_win_pct,
            "match_card_risk": match_card_risk,
            "impact_bullets": impact_bullets,
            "summary_text": " · ".join(impact_bullets) if impact_bullets else "Dengeli İlk 11 Formu",
        },
        "modulators": {
            "delta_home_goals": delta_home_goals,
            "delta_away_goals": delta_away_goals,
            "delta_cards": delta_cards,
            "delta_home_win_pct": delta_home_win_pct,
            "delta_away_win_pct": delta_away_win_pct,
            "match_card_risk": match_card_risk,
            "summary_text": " · ".join(impact_bullets) if impact_bullets else "Dengeli İlk 11 Formu",
        }
    }
