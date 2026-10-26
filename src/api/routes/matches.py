"""Match detail and odds routes."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter

from src.analytics.player_ratings import calculate_detailed_match_score, get_player_dynamic_rating
from src.api import state
from src.config import MATCHES_RAW_DIR
from src.db.database import get_db

router = APIRouter()
logger = logging.getLogger("api_server")


def _fetch_match_xg_info(
    match_id: int,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[str], Optional[str]]:
    """Query SQLite for match xG and quality metadata if available."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT x.provider, x.home_xg, x.away_xg, x.xg_quality
               FROM matches m LEFT JOIN external_match_xg x ON x.match_id = m.match_id
               WHERE m.match_id = ?""",
            (match_id,),
        )
        db_match = cursor.fetchone()
        conn.close()
        if db_match:
            h_xg = round(float(db_match["home_xg"]), 2) if db_match["home_xg"] is not None else None
            a_xg = round(float(db_match["away_xg"]), 2) if db_match["away_xg"] is not None else None
            tot_xg = round(h_xg + a_xg, 2) if h_xg is not None and a_xg is not None else None
            xg_source = db_match["provider"] if h_xg is not None and a_xg is not None else None
            xg_quality = db_match["xg_quality"]
            return h_xg, a_xg, tot_xg, xg_source, xg_quality
    except Exception as e:
        logger.warning(f"Error fetching match {match_id} from SQLite: {e}")
    return None, None, None, None, None


def _parse_detail_events(det_events: List[Dict[str, Any]]) -> Dict[str, Dict[int, int]]:
    """Parse match events (goals, assists, cards, subs) from details JSON."""
    sub_on: Dict[int, int] = {}
    sub_off: Dict[int, int] = {}
    goals: Dict[int, int] = {}
    assists: Dict[int, int] = {}
    yc: Dict[int, int] = {}
    rc: Dict[int, int] = {}
    for ev in det_events:
        etype = ev.get("type")
        pid = ev.get("personId")
        clk = ev.get("clock", {}).get("label", "")
        min_v = 0
        if clk:
            try:
                min_v = int(clk.split("'")[0].split("+")[0])
            except Exception:
                pass
        if etype == "G" and pid:
            goals[pid] = goals.get(pid, 0) + 1
        elif etype == "AS" and pid:
            assists[pid] = assists.get(pid, 0) + 1
        elif etype == "S" and pid:
            if ev.get("description") == "ON":
                sub_on[pid] = min_v
            elif ev.get("description") == "OFF":
                sub_off[pid] = min_v
        elif etype == "B" and pid:
            if ev.get("description") == "Y":
                yc[pid] = yc.get(pid, 0) + 1
            elif ev.get("description") == "R":
                rc[pid] = rc.get(pid, 0) + 1
    return {
        "sub_on": sub_on,
        "sub_off": sub_off,
        "goals": goals,
        "assists": assists,
        "yc": yc,
        "rc": rc,
    }


def _parse_stream_events(
    raw_stream: Path, team_lists: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[int, int]]]:
    """Parse play-by-play stream events for player shot, foul, penalty, offside, and save counts."""
    fouls_lost: Dict[int, int] = {}
    fouls_won: Dict[int, int] = {}
    shots: Dict[int, int] = {}
    shots_ot: Dict[int, int] = {}
    offsides: Dict[int, int] = {}
    pens_won: Dict[int, int] = {}
    pens_conceded: Dict[int, int] = {}
    pens_missed: Dict[int, int] = {}
    saves: Dict[int, int] = {}

    stream_events: List[Dict[str, Any]] = []
    if raw_stream.exists():
        try:
            with open(raw_stream, "r", encoding="utf-8") as f:
                st = json.load(f)
                stream_events = st.get("events", {}).get("content", [])
        except Exception:
            stream_events = []

    player_team_map: Dict[int, Any] = {}
    team_gk_map: Dict[Any, int] = {}
    for tl in team_lists:
        if not tl or not isinstance(tl, dict):
            continue
        tid = tl.get("teamId")
        for p in tl.get("lineup", []):
            pid = p.get("id")
            if pid:
                player_team_map[pid] = tid
                pos = p.get("matchPosition") or p.get("info", {}).get("position") or "M"
                if pos in ("G", "GK") and tid not in team_gk_map:
                    team_gk_map[tid] = pid
        for p in tl.get("substitutes", []):
            pid = p.get("id")
            if pid:
                player_team_map[pid] = tid

    team_ids_list = list(team_gk_map.keys())
    for se in stream_events:
        stype = se.get("type", "")
        stext = se.get("text", "")
        pids = se.get("playerIds", [])
        if not pids:
            continue
        p0 = pids[0]
        if stype == "free kick lost":
            fouls_lost[p0] = fouls_lost.get(p0, 0) + 1
        elif stype == "free kick won":
            fouls_won[p0] = fouls_won.get(p0, 0) + 1
        elif stype in ["goal", "attempt saved", "miss", "attempt blocked"]:
            shots[p0] = shots.get(p0, 0) + 1
            if stype in ["goal", "attempt saved"]:
                shots_ot[p0] = shots_ot.get(p0, 0) + 1
            if stype == "attempt saved":
                shooter_tid = player_team_map.get(p0)
                opp_tid = next((t for t in team_ids_list if t != shooter_tid), None)
                if opp_tid and opp_tid in team_gk_map:
                    opp_gk_id = team_gk_map[opp_tid]
                    saves[opp_gk_id] = saves.get(opp_gk_id, 0) + 1
        elif stype == "offside":
            offsides[p0] = offsides.get(p0, 0) + 1
        elif stype == "penalty lost":
            pens_conceded[p0] = pens_conceded.get(p0, 0) + 1
        elif stype == "penalty won":
            pens_won[p0] = pens_won.get(p0, 0) + 1
        elif stype in ["penalty miss", "penalty saved"] or "penalty missed" in stext.lower():
            pens_missed[p0] = pens_missed.get(p0, 0) + 1

    return stream_events, {
        "fouls_lost": fouls_lost,
        "fouls_won": fouls_won,
        "shots": shots,
        "shots_ot": shots_ot,
        "offsides": offsides,
        "pens_won": pens_won,
        "pens_conceded": pens_conceded,
        "pens_missed": pens_missed,
        "saves": saves,
    }


def _build_player_match_stats_dict(
    pid: Any,
    mins: int,
    ev_counts: Dict[str, Dict[int, int]],
    st_counts: Dict[str, Dict[int, int]],
) -> Dict[str, int]:
    """Assemble per-player match counting stats dictionary."""
    return {
        "minutes": mins,
        "goals": ev_counts["goals"].get(pid, 0),
        "assists": ev_counts["assists"].get(pid, 0),
        "shots": st_counts["shots"].get(pid, 0),
        "shots_ontarget": st_counts["shots_ot"].get(pid, 0),
        "fouls_committed": st_counts["fouls_lost"].get(pid, 0),
        "fouls_won": st_counts["fouls_won"].get(pid, 0),
        "offsides": st_counts["offsides"].get(pid, 0),
        "yellow_cards": ev_counts["yc"].get(pid, 0),
        "red_cards": ev_counts["rc"].get(pid, 0),
        "penalties_won": st_counts["pens_won"].get(pid, 0),
        "penalties_conceded": st_counts["pens_conceded"].get(pid, 0),
        "penalties_missed": st_counts["pens_missed"].get(pid, 0),
        "saves": st_counts["saves"].get(pid, 0),
    }


def _build_match_lineups(
    match_id: int,
    d: Dict[str, Any],
    is_match_completed: bool,
    ev_counts: Dict[str, Dict[int, int]],
    st_counts: Dict[str, Dict[int, int]],
) -> List[Dict[str, Any]]:
    """Build team lineup cards, starter/substitute lists, and team ratings."""
    lineups: List[Dict[str, Any]] = []
    teams_info = d.get("teams", [])
    sub_on = ev_counts["sub_on"]
    sub_off = ev_counts["sub_off"]
    pens_conceded = st_counts["pens_conceded"]
    pens_won = st_counts["pens_won"]
    pens_missed = st_counts["pens_missed"]

    for idx, tl in enumerate(d.get("teamLists", [])):
        if not tl or not isinstance(tl, dict):
            continue
        t_obj = teams_info[idx].get("team", {}) if idx < len(teams_info) else {}
        score_val = teams_info[idx].get("score") if idx < len(teams_info) else None
        opp_score_val = (
            teams_info[1 - idx].get("score")
            if len(teams_info) > 1 and (1 - idx) < len(teams_info)
            else 0
        )

        starters = []
        team_overall_sum = 0.0
        team_attack_sum = 0.0
        team_defense_sum = 0.0
        team_cards_risk_sum = 0.0
        starter_count = 0

        for p in tl.get("lineup", []):
            pid = p.get("id")
            reg_p = state.player_registry_map.get(int(pid), {}) if pid else {}
            photo = state.resolve_player_photo(pid, reg_p)
            pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"

            p_rat = {}
            if pid:
                try:
                    p_rat = get_player_dynamic_rating(pid, as_of_match_id=match_id)
                except Exception:
                    p_rat = {}

            p_mins = sub_off.get(pid, 90)
            p_stats = _build_player_match_stats_dict(pid, p_mins, ev_counts, st_counts)

            if is_match_completed:
                perf = calculate_detailed_match_score(
                    p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0
                )
                overall_r = perf["overall"]
                att_r = perf["attack"]
                def_r = perf["defense"]
                match_r = perf["overall"]
            else:
                overall_r = p_rat.get("overall_rating", 6.0)
                att_r = p_rat.get("attack_rating", 6.0)
                def_r = p_rat.get("defense_rating", 6.0)
                match_r = None

            cards_r = p_rat.get("cards_risk", 3.0)
            team_overall_sum += overall_r
            team_attack_sum += att_r
            team_defense_sum += def_r
            team_cards_risk_sum += cards_r
            starter_count += 1

            starters.append({
                "id": pid,
                "name": p.get("name", {}).get("display"),
                "shirt": p.get("matchShirtNumber"),
                "position": pos,
                "captain": p.get("captain", False),
                "country": p.get("nationalTeam", {}).get("country"),
                "photo_url": photo,
                "rating": overall_r,
                "match_rating": match_r,
                "form_rating": p_rat.get("overall_rating", 6.0),
                "is_match_rating": is_match_completed,
                "attack_rating": att_r,
                "defense_rating": def_r,
                "cards_risk": cards_r,
                "form_label": p_rat.get("form_label", "Normal"),
                "trend": p_rat.get("trend", "stable"),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
            })

        subs = []
        for p in tl.get("substitutes", []):
            pid = p.get("id")
            reg_p = state.player_registry_map.get(int(pid), {}) if pid else {}
            photo = state.resolve_player_photo(pid, reg_p)
            pos = p.get("matchPosition") or p.get("info", {}).get("position") or reg_p.get("position") or "M"

            p_rat = {}
            if pid:
                try:
                    p_rat = get_player_dynamic_rating(pid, as_of_match_id=match_id)
                except Exception:
                    p_rat = {}

            p_mins = (90 - sub_on.get(pid, 75)) if pid in sub_on else 0
            p_stats = _build_player_match_stats_dict(pid, p_mins, ev_counts, st_counts)

            if is_match_completed and p_mins > 0:
                perf = calculate_detailed_match_score(
                    p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0
                )
                sub_r = perf["overall"]
                match_r = perf["overall"]
            else:
                sub_r = p_rat.get("overall_rating", 6.0)
                match_r = None

            subs.append({
                "id": pid,
                "name": p.get("name", {}).get("display"),
                "shirt": p.get("matchShirtNumber"),
                "position": pos,
                "photo_url": photo,
                "rating": sub_r,
                "match_rating": match_r,
                "form_rating": p_rat.get("overall_rating", 6.0),
                "is_match_rating": is_match_completed,
                "cards_risk": p_rat.get("cards_risk", 3.0),
                "form_label": p_rat.get("form_label", "Normal"),
                "trend": p_rat.get("trend", "stable"),
                "penalties_conceded": pens_conceded.get(pid, 0),
                "penalties_won": pens_won.get(pid, 0),
                "penalties_missed": pens_missed.get(pid, 0),
            })

        starters.sort(key=lambda x: (state.get_position_order(x.get("position")), x.get("shirt") or 99))
        subs.sort(key=lambda x: (state.get_position_order(x.get("position")), x.get("shirt") or 99))

        formation_obj = tl.get("formation") or {}
        if isinstance(formation_obj, dict):
            form_label = formation_obj.get("label", "4-3-3")
            form_matrix = formation_obj.get("players", [])
        else:
            form_label = str(formation_obj) if formation_obj else "4-3-3"
            form_matrix = []

        divisor = starter_count if starter_count > 0 else 1
        lineups.append({
            "team_id": tl.get("teamId"),
            "team_name": t_obj.get("name"),
            "score": score_val,
            "formation": form_label,
            "formation_matrix": form_matrix,
            "team_ratings": {
                "overall": round(team_overall_sum / divisor, 2),
                "attack": round(team_attack_sum / divisor, 2),
                "defense": round(team_defense_sum / divisor, 2),
                "cards_risk": round(team_cards_risk_sum / divisor, 2),
            },
            "starters": starters,
            "substitutes": subs,
        })
    return lineups


def _build_comparative_team_stats(
    raw_stats: Path,
    d: Dict[str, Any],
    h_xg: Optional[float],
    a_xg: Optional[float],
) -> List[Dict[str, Any]]:
    """Build comparative team statistics across 5 tactical categories."""
    if raw_stats.exists():
        with open(raw_stats, "r", encoding="utf-8") as f:
            s_data = json.load(f)

        t_data = s_data.get("data", {})
        teams_info = d.get("teams", [])
        h_id_str = str(int(teams_info[0].get("team", {}).get("id", 0))) if len(teams_info) > 0 else "0"
        a_id_str = str(int(teams_info[1].get("team", {}).get("id", 0))) if len(teams_info) > 1 else "0"

        hm = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(h_id_str, {}).get("M", [])}
        am = {it.get("name"): float(it.get("value", 0)) for it in t_data.get(a_id_str, {}).get("M", [])}

        def m_pair(key: str, def_val: float = 0.0) -> Tuple[float, float]:
            return hm.get(key, def_val), am.get(key, def_val)

        h_pass, a_pass = m_pair("total_pass")
        h_acc_p, a_acc_p = m_pair("accurate_pass")
        h_pass_pct = round((h_acc_p / max(1.0, h_pass)) * 100, 1) if h_pass > 0 else 0.0
        a_pass_pct = round((a_acc_p / max(1.0, a_pass)) * 100, 1) if a_pass > 0 else 0.0

        return [
            {
                "category": "Şut & Hücum Hacmi",
                "items": [
                    {
                        "label": "TheStatsAPI Beklenen Gol (xG)",
                        "home": h_xg if h_xg is not None else "Not Found",
                        "away": a_xg if a_xg is not None else "Not Found",
                        "rawHome": h_xg,
                        "rawAway": a_xg,
                        "isXg": True,
                        "notFound": (h_xg is None and a_xg is None),
                    },
                    {"label": "Toplam Şut", "home": hm.get("total_scoring_att", 0), "away": am.get("total_scoring_att", 0)},
                    {"label": "İsabetli Şut", "home": hm.get("ontarget_scoring_att", 0), "away": am.get("ontarget_scoring_att", 0)},
                    {"label": "İsabetsiz Şut", "home": hm.get("shot_off_target", 0), "away": am.get("shot_off_target", 0)},
                    {"label": "Bloklanan Şut", "home": hm.get("blocked_scoring_att", 0), "away": am.get("blocked_scoring_att", 0)},
                    {"label": "Ceza Sahası İçi Şut", "home": hm.get("attempts_ibox", 0), "away": am.get("attempts_ibox", 0)},
                    {"label": "Ceza Sahası Dışı Şut", "home": hm.get("attempts_obox", 0), "away": am.get("attempts_obox", 0)},
                    {"label": "Yaratılan Net Fırsat", "home": hm.get("big_chance_created", 0), "away": am.get("big_chance_created", 0)},
                    {"label": "Kaçan Net Fırsat", "home": hm.get("big_chance_missed", 0), "away": am.get("big_chance_missed", 0)},
                    {"label": "Rakip Ceza Sahasında Topla Buluşma", "home": hm.get("touches_in_opp_box", 0), "away": am.get("touches_in_opp_box", 0)},
                    {"label": "Kilit Pas / Şut Pası", "home": hm.get("total_att_assist", 0), "away": am.get("total_att_assist", 0)},
                ]
            },
            {
                "category": "Top Hakimiyeti & Pas",
                "items": [
                    {"label": "Topa Sahip Olma", "home": hm.get("possession_percentage", 0), "away": am.get("possession_percentage", 0), "suffix": "%"},
                    {"label": "Toplam Pas", "home": h_pass, "away": a_pass},
                    {"label": "İsabetli Pas", "home": h_acc_p, "away": a_acc_p},
                    {"label": "Pas İsabet Oranı", "home": h_pass_pct, "away": a_pass_pct, "suffix": "%"},
                    {"label": "3. Bölge (Final Third) Pasları", "home": hm.get("total_final_third_passes", 0), "away": am.get("total_final_third_passes", 0)},
                    {"label": "Başarılı 3. Bölge Pasları", "home": hm.get("successful_final_third_passes", 0), "away": am.get("successful_final_third_passes", 0)},
                    {"label": "Toplam Orta / İsabet", "home": f"{int(hm.get('total_cross',0))} ({int(hm.get('accurate_cross',0))})", "away": f"{int(am.get('total_cross',0))} ({int(am.get('accurate_cross',0))})", "rawHome": hm.get("total_cross", 0), "rawAway": am.get("total_cross", 0)},
                    {"label": "Uzun Toplar", "home": hm.get("total_long_balls", 0), "away": am.get("total_long_balls", 0)},
                ]
            },
            {
                "category": "Duran Top & Baskı",
                "items": [
                    {"label": "Kazanılan Korner", "home": hm.get("won_corners", 0), "away": am.get("won_corners", 0)},
                    {"label": "Ceza Sahasına İsabetli Korner", "home": hm.get("accurate_corners_intobox", 0), "away": am.get("accurate_corners_intobox", 0)},
                    {"label": "Toplam Taç", "home": hm.get("total_throws", 0), "away": am.get("total_throws", 0)},
                    {"label": "İsabetli Taç", "home": hm.get("accurate_throws", 0), "away": am.get("accurate_throws", 0)},
                    {"label": "PPDA (Pres Baskı İndeksi)", "home": hm.get("ppda", 0), "away": am.get("ppda", 0)},
                ]
            },
            {
                "category": "Savunma & İkili Mücadele",
                "items": [
                    {"label": "Top Kapma (Kazanılan)", "home": f"{int(hm.get('total_tackle',0))} ({int(hm.get('won_tackle',0))})", "away": f"{int(am.get('total_tackle',0))} ({int(am.get('won_tackle',0))})", "rawHome": hm.get("total_tackle", 0), "rawAway": am.get("total_tackle", 0)},
                    {"label": "Pas Arası (Interception)", "home": hm.get("interception", 0), "away": am.get("interception", 0)},
                    {"label": "Tehlike Uzaklaştırma (Clearance)", "home": hm.get("total_clearance", 0), "away": am.get("total_clearance", 0)},
                    {"label": "Bloklanan Şut & Pas", "home": hm.get("outfielder_block", 0) + hm.get("blocked_pass", 0), "away": am.get("outfielder_block", 0) + am.get("blocked_pass", 0)},
                    {"label": "Sahipsiz Top Kazanma", "home": hm.get("ball_recovery", 0), "away": am.get("ball_recovery", 0)},
                    {"label": "Kazanılan İkili Mücadele", "home": hm.get("duel_won", 0), "away": am.get("duel_won", 0)},
                    {"label": "Kazanılan Hava Topu", "home": hm.get("aerial_won", 0), "away": am.get("aerial_won", 0)},
                ]
            },
            {
                "category": "Disiplin & Kaleci",
                "items": [
                    {"label": "Toplam Kurtarış", "home": hm.get("saves", 0), "away": am.get("saves", 0)},
                    {"label": "Ceza Sahası İçi Kurtarış", "home": hm.get("saved_ibox", 0), "away": am.get("saved_ibox", 0)},
                    {"label": "Yapılan Faul", "home": hm.get("fk_foul_lost", 0), "away": am.get("fk_foul_lost", 0)},
                    {"label": "Alınan Faul", "home": hm.get("fk_foul_won", 0), "away": am.get("fk_foul_won", 0)},
                    {"label": "Ofsayt", "home": hm.get("total_offside", 0), "away": am.get("total_offside", 0)},
                    {"label": "Sarı Kart", "home": hm.get("total_yel_card", 0), "away": am.get("total_yel_card", 0)},
                    {"label": "Kırmızı Kart", "home": hm.get("total_red_card", 0), "away": am.get("total_red_card", 0)},
                ]
            }
        ]

    if h_xg is not None or a_xg is not None:
        return [
            {
                "category": "Şut & Hücum Hacmi",
                "items": [
                    {
                        "label": "TheStatsAPI Beklenen Gol (xG)",
                        "home": h_xg if h_xg is not None else "Not Found",
                        "away": a_xg if a_xg is not None else "Not Found",
                        "rawHome": h_xg,
                        "rawAway": a_xg,
                        "isXg": True,
                        "notFound": (h_xg is None and a_xg is None),
                    }
                ]
            }
        ]
    return []


def _build_match_player_stats(
    d: Dict[str, Any],
    is_match_completed: bool,
    ev_counts: Dict[str, Dict[int, int]],
    st_counts: Dict[str, Dict[int, int]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Populate home and away player performance cards for starters and played substitutes."""
    player_stats: Dict[str, List[Dict[str, Any]]] = {"home": [], "away": []}
    teams_info = d.get("teams", [])
    sub_on = ev_counts["sub_on"]
    sub_off = ev_counts["sub_off"]

    def _build_player_entry(
        p: Dict[str, Any],
        mins: int,
        is_starter: bool,
        score_val: Any,
        opp_score_val: Any,
    ) -> Dict[str, Any]:
        pid = p.get("id")
        reg_p = state.player_registry_map.get(int(pid), {}) if pid else {}
        photo = state.resolve_player_photo(pid, reg_p)
        pos = p.get("matchPosition") or p.get("info", {}).get("position", "M")
        p_stats = _build_player_match_stats_dict(pid, mins, ev_counts, st_counts)

        p_rating = 6.0
        p_attack = 6.0
        p_defense = 6.0
        if is_match_completed:
            perf = calculate_detailed_match_score(
                p_stats, pos, team_score=score_val or 0, opp_score=opp_score_val or 0
            )
            p_rating = perf["overall"]
            p_attack = perf.get("attack")
            p_defense = perf.get("defense")

        return {
            "id": pid,
            "name": p.get("name", {}).get("display", "Unknown"),
            "shirt": p.get("matchShirtNumber"),
            "position": pos,
            "is_starter": is_starter,
            "captain": p.get("captain", False) if is_starter else False,
            "photo_url": photo,
            **p_stats,
            "rating": p_rating,
            "attack_rating": p_attack,
            "defense_rating": p_defense,
            "team_score": score_val or 0,
            "opp_score": opp_score_val or 0,
            "match_rating": p_rating if is_match_completed else None,
            "is_match_rating": is_match_completed,
        }

    for idx, tl in enumerate(d.get("teamLists", [])):
        if not tl or not isinstance(tl, dict):
            continue
        side = "home" if idx == 0 else "away"
        lineup_p = tl.get("lineup", [])
        subs_p = tl.get("substitutes", [])
        score_val = teams_info[idx].get("score") if idx < len(teams_info) else None
        opp_score_val = (
            teams_info[1 - idx].get("score")
            if len(teams_info) > 1 and (1 - idx) < len(teams_info)
            else 0
        )

        for p in lineup_p:
            pid = p.get("id")
            if not pid:
                continue
            mins = sub_off.get(pid, 90)
            player_stats[side].append(_build_player_entry(p, mins, True, score_val, opp_score_val))

        for p in subs_p:
            pid = p.get("id")
            if not pid or pid not in sub_on:
                continue
            mins = max(1, 90 - sub_on[pid])
            player_stats[side].append(_build_player_entry(p, mins, False, score_val, opp_score_val))

        player_stats[side].sort(
            key=lambda x: (
                0 if x.get("is_starter") else 1,
                state.get_position_order(x.get("position")),
                x.get("shirt") or 99,
            )
        )
    return player_stats


def _build_key_timeline(
    d: Dict[str, Any],
    det_events: List[Dict[str, Any]],
    stream_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build chronologically sorted key match timeline events."""
    key_timeline: List[Dict[str, Any]] = []
    player_names: Dict[Any, str] = {}
    player_photos: Dict[Any, Any] = {}
    for tl in (d.get("teamLists") or []):
        if not tl or not isinstance(tl, dict):
            continue
        lineup_p = tl.get("lineup") or []
        subs_p = tl.get("substitutes") or []
        for p in (lineup_p + subs_p):
            if not p or not isinstance(p, dict):
                continue
            pid = p.get("id")
            if pid:
                pname = (p.get("name") or {}).get("display") or "Bilinmeyen Oyuncu"
                player_names[pid] = pname
                player_photos[pid] = state.resolve_player_photo(pid)

    team_names_map: Dict[int, str] = {}
    for t_item in d.get("teams", []):
        t_obj = t_item.get("team", {})
        if t_obj.get("id"):
            team_names_map[int(t_obj["id"])] = t_obj.get("name", "")

    sub_events: Dict[Any, Dict[str, Any]] = {}
    for ev in det_events:
        if ev.get("type") == "S":
            eid = ev.get("id")
            if eid not in sub_events:
                sub_events[eid] = {}
            if ev.get("description") == "ON":
                sub_events[eid]["on"] = ev.get("personId")
            elif ev.get("description") == "OFF":
                sub_events[eid]["off"] = ev.get("personId")

    seen_sub_ids = set()
    for ev in det_events:
        etype = ev.get("type")
        clock_lbl = ev.get("clock", {}).get("label", "")
        minute_display = clock_lbl.split("'")[0] + "'" if "'" in clock_lbl else clock_lbl
        tid = ev.get("teamId")
        tname = team_names_map.get(tid, "")

        if etype == "PS":
            phase = ev.get("phase")
            if phase == "1":
                key_timeline.append({
                    "type": "period_start",
                    "minute": "0'",
                    "label": "Maç Başlangıcı",
                    "description": "1. Yarı Başladı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
            elif phase == "2":
                key_timeline.append({
                    "type": "period_start",
                    "minute": "45'",
                    "label": "2. Yarı Başlangıcı",
                    "description": "2. Yarı Başladı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
        elif etype == "PE":
            phase = ev.get("phase")
            if phase == "1":
                key_timeline.append({
                    "type": "period_end",
                    "minute": minute_display,
                    "label": "İlk Yarı Sonu",
                    "description": "İlk Yarı Tamamlandı",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
            elif phase == "2":
                key_timeline.append({
                    "type": "period_end",
                    "minute": minute_display,
                    "label": "Maç Sonu (FT)",
                    "description": "Karşılaşma Sona Erdi",
                    "score": f"{ev.get('score', {}).get('homeScore', 0)} - {ev.get('score', {}).get('awayScore', 0)}"
                })
        elif etype in ["G", "P", "O"]:
            pid = ev.get("personId")
            aid = ev.get("assistId")
            desc = ev.get("description", "G")
            is_penalty = (etype == "P" or desc == "P")
            is_own_goal = (etype == "O" or desc in ["OG", "O"])
            goal_type = "Penaltı Golü" if is_penalty else ("Kendi Kalesine Gol" if is_own_goal else "Gol")
            h_s = ev.get("score", {}).get("homeScore", 0)
            a_s = ev.get("score", {}).get("awayScore", 0)
            credited_team_id = tid
            if is_own_goal and tid is not None:
                credited_team_id = next(
                    (team_id for team_id in team_names_map if team_id != tid),
                    tid,
                )
            key_timeline.append({
                "type": "goal",
                "goal_type": goal_type,
                "is_penalty": is_penalty,
                "is_own_goal": is_own_goal,
                "minute": minute_display,
                "team_id": credited_team_id,
                "team_name": team_names_map.get(credited_team_id, tname),
                "player_id": pid,
                "player_name": player_names.get(pid, "Bilinmeyen Oyuncu"),
                "photo_url": player_photos.get(pid),
                "assist_id": aid,
                "assist_name": player_names.get(aid) if aid else None,
                "score": f"{h_s} - {a_s}"
            })
        elif etype == "B":
            pid = ev.get("personId")
            card_desc = ev.get("description", "Y")
            key_timeline.append({
                "type": "yellow_card" if card_desc == "Y" else "red_card",
                "minute": minute_display,
                "team_id": tid,
                "team_name": tname,
                "player_id": pid,
                "player_name": player_names.get(pid, "Bilinmeyen Oyuncu"),
                "photo_url": player_photos.get(pid),
            })
        elif etype == "S":
            eid = ev.get("id")
            if eid and eid not in seen_sub_ids:
                seen_sub_ids.add(eid)
                sub_info = sub_events.get(eid, {})
                p_in = sub_info.get("on")
                p_out = sub_info.get("off")
                key_timeline.append({
                    "type": "substitution",
                    "minute": minute_display,
                    "team_id": tid,
                    "team_name": tname,
                    "player_in_id": p_in,
                    "player_in_name": player_names.get(p_in, "Giren Oyuncu"),
                    "player_in_photo": player_photos.get(p_in),
                    "player_out_id": p_out,
                    "player_out_name": player_names.get(p_out, "Çıkan Oyuncu"),
                    "player_out_photo": player_photos.get(p_out),
                })

    for se in stream_events:
        stype = se.get("type", "")
        stext = se.get("text", "")
        time_info = se.get("time", {})
        s_min = time_info.get("label", "")
        if s_min and "'" not in s_min:
            s_min = f"{s_min}'"

        if stype == "added time":
            key_timeline.append({
                "type": "added_time",
                "minute": s_min or "45+'",
                "label": "Uzatma Süresi",
                "description": stext or "Uzatma Süresi İlan Edildi",
            })
        elif stype == "penalty missed" or "penalty missed" in stext.lower() or "penalty saved" in stext.lower():
            pids = se.get("playerIds", [])
            pid = pids[0] if pids else None
            key_timeline.append({
                "type": "penalty_missed",
                "minute": s_min or "-",
                "label": "Kaçan Penaltı",
                "description": stext or "Penaltı Kaçtı",
                "player_id": pid,
                "player_name": player_names.get(pid) if pid else None,
                "photo_url": player_photos.get(pid) if pid else None,
            })

    def parse_minute_sort(item: Dict[str, Any]) -> Tuple[float, int]:
        m = str(item.get("minute", "0")).replace("'", "").strip()
        prio_map = {
            "period_start": 0,
            "added_time": 1,
            "goal": 2,
            "yellow_card": 2,
            "red_card": 2,
            "penalty_missed": 2,
            "substitution": 2,
            "period_end": 3,
        }
        prio = prio_map.get(str(item.get("type")), 2)
        if "+" in m:
            parts = m.split("+")
            try:
                return (float(parts[0]) + float(parts[1]) * 0.01, prio)
            except (ValueError, TypeError):
                pass
        try:
            return (float(m), prio)
        except (ValueError, TypeError):
            return (0.0, prio)

    key_timeline.sort(key=parse_minute_sort)
    return key_timeline


def _find_non_premier_league_match(match_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM matches WHERE match_id = ? AND competition_id != 39", (match_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _load_statsapi_payloads(match_id: int) -> Dict[str, Dict[str, Any]]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT kind, payload FROM external_match_payloads WHERE match_id = ? AND provider = 'TheStatsAPI'", (match_id,)).fetchall()
    finally:
        conn.close()
    payloads = {row["kind"]: json.loads(row["payload"]) for row in rows}
    return {kind: data for kind, data in payloads.items() if not data.get("unavailable")}


def _database_match_details(match: Dict[str, Any]) -> Dict[str, Any]:
    """Match page of a competition without PulseLive data: UEFA feeds for the cups, TheStatsAPI for national leagues."""
    from src.competitions.registry import get_competition

    comp = get_competition(match["competition_id"])
    payloads = _load_statsapi_payloads(match["match_id"])
    if comp.provider == "thestatsapi":
        from src.api.statsapi_match_details import build_statsapi_match_details

        result = build_statsapi_match_details(match, payloads, get_match_odds_list(match["match_id"]))
        if match["status"] == "COMPLETED" and "stats" in payloads and "timeline" in payloads:
            state._completed_match_details_cache[match["match_id"]] = result
        return result

    from src.api.uefa_match_details import build_uefa_match_details
    from src.ingest.provider_factory import get_provider

    provider = get_provider(comp.key)
    try:
        lineups = provider.fetch_match_details(match["match_id"])
        events = provider.fetch_match_stream(match["match_id"])
        match_feed = provider.fetch_match(match["match_id"])
    except Exception as exc:
        logger.warning("UEFA match feed unavailable for %s: %s", match["match_id"], exc)
        lineups = events = match_feed = None
    result = build_uefa_match_details(match, lineups, events, match_feed)
    if payloads:
        from src.api.uefa_match_details import apply_statsapi_payloads
        result = apply_statsapi_payloads(result, payloads, match, get_match_odds_list(match["match_id"]))
    if match["status"] == "COMPLETED" and events and "stats" in payloads:
        state._completed_match_details_cache[match["match_id"]] = result
    return result


@router.get("/api/match/{match_id}/details")
def get_match_full_details(match_id: int):
    """
    Returns full match lineup rosters, substitutes, tactical formations,
    and play-by-play events.
    """
    if match_id in state._completed_match_details_cache:
        return state._completed_match_details_cache[match_id]

    uefa_match = _find_non_premier_league_match(match_id)
    if uefa_match is not None:
        return _database_match_details(uefa_match)

    raw_details = MATCHES_RAW_DIR / f"{match_id}_details.json"
    raw_stream = MATCHES_RAW_DIR / f"{match_id}_stream.json"
    raw_stats = MATCHES_RAW_DIR / f"{match_id}_stats.json"

    h_xg, a_xg, tot_xg, xg_source, xg_quality = _fetch_match_xg_info(match_id)

    d: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    lineups: List[Dict[str, Any]] = []
    det_events: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    ev_counts = _parse_detail_events([])
    st_counts: Dict[str, Dict[int, int]] = {
        "fouls_lost": {},
        "fouls_won": {},
        "shots": {},
        "shots_ot": {},
        "offsides": {},
        "pens_won": {},
        "pens_conceded": {},
        "pens_missed": {},
        "saves": {},
    }
    is_match_completed = False

    if raw_details.exists():
        with open(raw_details, "r", encoding="utf-8") as f:
            d = json.load(f)

        metadata = {
            "match_id": match_id,
            "kickoff_label": d.get("kickoff", {}).get("label"),
            "ground": d.get("ground", {}).get("name"),
            "attendance": d.get("attendance"),
            "referee": (
                d.get("matchOfficials", [{}])[0].get("matchOfficial", {}).get("name", {}).get("display")
                if d.get("matchOfficials")
                else None
            ),
            "halfTimeScore": d.get("halfTimeScore"),
            "home_xg": h_xg,
            "away_xg": a_xg,
            "total_xg": tot_xg,
            "xg_source": xg_source,
            "xg_quality": xg_quality,
        }

        det_events = d.get("events", [])
        ev_counts = _parse_detail_events(det_events)
        events, st_counts = _parse_stream_events(raw_stream, d.get("teamLists", []))

        teams_info = d.get("teams", [])
        h_score_val = teams_info[0].get("score") if len(teams_info) > 0 else None
        a_score_val = teams_info[1].get("score") if len(teams_info) > 1 else None
        is_match_completed = (h_score_val is not None and a_score_val is not None)

        lineups = _build_match_lineups(match_id, d, is_match_completed, ev_counts, st_counts)

    team_stats = _build_comparative_team_stats(raw_stats, d, h_xg, a_xg)
    player_stats = _build_match_player_stats(d, is_match_completed, ev_counts, st_counts)
    key_timeline = _build_key_timeline(d, det_events, events)

    res = {
        "metadata": metadata,
        "lineups": lineups,
        "team_stats": team_stats,
        "player_stats": player_stats,
        "events": events,
        "timeline": key_timeline,
        "odds": get_match_odds_list(match_id),
    }
    if bool(team_stats or events):
        state._completed_match_details_cache[match_id] = res
    return res


def get_match_odds_list(match_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bookmaker,
                   home_last_seen, draw_last_seen, away_last_seen,
                   home_open, draw_open, away_open,
                   over_25_last_seen, under_25_last_seen,
                   btts_yes_last_seen, btts_no_last_seen,
                   corners_over_last_seen, corners_under_last_seen,
                   cards_over_last_seen, cards_under_last_seen,
                   fetched_at_utc
            FROM external_match_odds
            WHERE match_id = ?
            ORDER BY CASE 
                WHEN bookmaker = 'Bet365' THEN 1 
                WHEN bookmaker = 'Pinnacle' THEN 2 
                WHEN bookmaker = 'Betfair Exchange' THEN 3 
                WHEN bookmaker = 'Paddy Power' THEN 4 
                ELSE 5 
            END
        """, (match_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"Error fetching odds for match {match_id}: {e}")
        return []


@router.get("/api/match/{match_id}/odds")
def get_match_odds(match_id: int):
    """Returns stored pre-match & closing betting odds across bookmakers for this match."""
    return {"match_id": match_id, "odds": get_match_odds_list(match_id)}
