"""Match detail payload for UEFA competitions, built from the public UEFA lineup and event feeds.

Everything here is read from the feeds; nothing is estimated. The feeds carry no xG, passing or
possession data, so those statistics are simply absent. Shot, corner, foul, offside, save and card
counts are tallies of the logged events and are labelled as such in the response.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

POSITION_CODES = {"GOALKEEPER": "G", "DEFENDER": "D", "MIDFIELDER": "M", "FORWARD": "F"}
SOURCE_LABEL = "UEFA olay akışı"


def _name(person: Dict[str, Any]) -> str:
    return person.get("internationalName") or person.get("clubShirtName") or ""


def _is_own_goal(event: Dict[str, Any]) -> bool:
    return str(event.get("subType") or "").startswith("OWN")


def _minute(time: Dict[str, Any]) -> Tuple[str, float]:
    minute, injury = int(time.get("minute", 0)), int(time.get("injuryMinute", 0) or 0)
    label = f"{minute}+{injury}'" if injury else f"{minute}'"
    return label, minute + injury / 100.0


def _player(entry: Dict[str, Any], starter: bool) -> Dict[str, Any]:
    person = entry.get("player", {})
    return {
        "id": int(person["id"]),
        "name": _name(person),
        "shirt": entry.get("jerseyNumber"),
        "position": POSITION_CODES.get(person.get("fieldPosition", ""), "M"),
        "captain": bool(entry.get("captain", False)),
        "country": person.get("countryCode"),
        "photo_url": person.get("imageUrl"),
        "rating": None,
        "is_match_rating": False,
    }


def _formation(starters: List[Dict[str, Any]]) -> str:
    outfield = [p["position"] for p in starters if p["position"] != "G"]
    counts = [outfield.count(code) for code in ("D", "M", "F")]
    return "-".join(str(c) for c in counts if c) if sum(counts) == 10 else ""


def build_lineups(lineup_feed: Optional[Dict[str, Any]], match: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not lineup_feed:
        return []
    lineups = []
    for side in ("homeTeam", "awayTeam"):
        team = lineup_feed.get(side) or {}
        starters = [_player(e, True) for e in team.get("field", [])]
        if not starters:
            continue
        is_home = side == "homeTeam"
        lineups.append({
            "team_id": match["home_id"] if is_home else match["away_id"],
            "team_name": match["home_name"] if is_home else match["away_name"],
            "score": match["home_score"] if is_home else match["away_score"],
            "formation": _formation(starters),
            "formation_matrix": [],
            "team_ratings": None,
            "starters": starters,
            "substitutes": [_player(e, False) for e in team.get("bench", [])],
            "coaches": [_name(c.get("person", {})) or c.get("person", {}).get("translations", {}).get("name", {}).get("EN", "")
                        for c in team.get("coaches", [])],
        })
    return lineups


def _team_of(event: Dict[str, Any]) -> Optional[int]:
    team = (event.get("primaryActor") or {}).get("team") or event.get("team") or {}
    return int(team["id"]) if team.get("id") else None


def build_team_stats(events: List[Dict[str, Any]], home_id: int, away_id: int) -> List[Dict[str, Any]]:
    def count(*types: str, only_goalkeepers: bool = False, skip_own_goals: bool = False) -> Tuple[int, int]:
        tally = {home_id: 0, away_id: 0}
        for e in events:
            if e.get("type") not in types:
                continue
            if skip_own_goals and _is_own_goal(e):
                continue
            if only_goalkeepers and ((e.get("primaryActor") or {}).get("person") or {}).get("fieldPosition") != "GOALKEEPER":
                continue
            team = _team_of(e)
            if team in tally:
                tally[team] += 1
        return tally[home_id], tally[away_id]

    goals = count("GOAL", skip_own_goals=True)
    on_target = _sum_tuples(count("SHOT_ON_GOAL"), goals)  # the feed logs a goal separately from a saved shot
    off_target, blocked = count("SHOT_WIDE"), count("SHOT_BLOCKED")
    shots = _sum_tuples(on_target, off_target, blocked)

    def pair(label: str, values: Tuple[int, int]) -> Dict[str, Any]:
        return {"label": label, "home": values[0], "away": values[1]}

    return [{
        "category": f"Maç istatistikleri ({SOURCE_LABEL})",
        "items": [
            pair("Toplam Şut", shots),
            pair("İsabetli Şut", on_target),
            pair("İsabetsiz Şut", off_target),
            pair("Bloklanan Şut", blocked),
            pair("Kaleci Kurtarışı", count("SAVE", only_goalkeepers=True)),
            pair("Korner", count("CORNER")),
            pair("Faul", count("FOUL")),
            pair("Ofsayt", count("OFFSIDE")),
            pair("Sarı Kart", count("YELLOW_CARD")),
            pair("Kırmızı Kart", count("RED_CARD", "YELLOW_RED_CARD")),
        ],
    }]


def _sum_tuples(*tuples: Tuple[int, int]) -> Tuple[int, int]:
    return sum(t[0] for t in tuples), sum(t[1] for t in tuples)


def build_timeline(events: List[Dict[str, Any]], lineups: List[Dict[str, Any]], match: Dict[str, Any]) -> List[Dict[str, Any]]:
    teams = {match["home_id"]: match["home_name"], match["away_id"]: match["away_name"]}
    on_field = {p["id"] for lu in lineups for p in lu["starters"]}
    photos = {p["id"]: p["photo_url"] for lu in lineups for p in lu["starters"] + lu["substitutes"]}
    timeline: List[Tuple[float, int, Dict[str, Any]]] = []

    ordered = sorted((e for e in events if "time" in e), key=lambda e: (e["time"].get("minute", 0), e["time"].get("injuryMinute", 0) or 0, e["time"].get("second", 0), e.get("timestamp", "")))
    running = {match["home_id"]: 0, match["away_id"]: 0}
    for e in ordered:
        etype = e.get("type")
        label, sort_key = _minute(e["time"])
        actor = (e.get("primaryActor") or {}).get("person") or {}
        team_id = _team_of(e)

        if etype == "GOAL":
            # totalScore on a goal event is the final score of the match, not the running score, and the
            # secondary actor is the goalkeeper who conceded. The scorer's team gets the goal; an own goal
            # counts for the opponent.
            own_goal = _is_own_goal(e)
            opponent = match["away_id"] if team_id == match["home_id"] else match["home_id"]
            credited = opponent if own_goal else team_id
            running[credited] = running.get(credited, 0) + 1
            timeline.append((sort_key, 2, {
                "type": "goal",
                "goal_type": e.get("subType") or "Goal",
                "is_penalty": e.get("subType") == "PENALTY",
                "is_own_goal": own_goal,
                "minute": label,
                "team_id": credited,
                "team_name": teams.get(credited, ""),
                "player_id": int(actor["id"]) if actor.get("id") else None,
                "player_name": _name(actor),
                "photo_url": actor.get("imageUrl"),
                "assist_id": None,
                "assist_name": None,
                "score": f"{running[match['home_id']]} - {running[match['away_id']]}",
            }))
        elif etype in ("YELLOW_CARD", "RED_CARD", "YELLOW_RED_CARD"):
            timeline.append((sort_key, 2, {
                "type": "yellow_card" if etype == "YELLOW_CARD" else "red_card",
                "minute": label,
                "team_id": team_id,
                "team_name": teams.get(team_id, ""),
                "player_id": int(actor["id"]) if actor.get("id") else None,
                "player_name": _name(actor),
                "photo_url": actor.get("imageUrl"),
            }))
        elif etype == "INJURY_TIME" and e.get("injuryTimeMinutesAdded"):
            timeline.append((sort_key, 1, {
                "type": "added_time",
                "minute": label,
                "label": "Uzatma Süresi",
                "description": f"+{e['injuryTimeMinutesAdded']} dakika",
            }))
        elif etype == "SUBSTITUTION":
            first = actor
            second = ((e.get("secondaryActor") or {}).get("person")) or {}
            first_id = int(first["id"]) if first.get("id") else None
            # Whoever is currently on the pitch is the player going off.
            off, on = (first, second) if first_id in on_field else (second, first)
            for person, entering in ((off, False), (on, True)):
                if person.get("id"):
                    (on_field.add if entering else on_field.discard)(int(person["id"]))
            timeline.append((sort_key, 3, {
                "type": "substitution",
                "minute": label,
                "team_id": team_id,
                "team_name": teams.get(team_id, ""),
                "player_in_id": int(on["id"]) if on.get("id") else None,
                "player_in_name": _name(on),
                "player_in_photo": photos.get(int(on["id"])) if on.get("id") else None,
                "player_out_id": int(off["id"]) if off.get("id") else None,
                "player_out_name": _name(off),
                "player_out_photo": photos.get(int(off["id"])) if off.get("id") else None,
            }))
    timeline.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in timeline]


def _weather(match_feed: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    condition = (match_feed or {}).get("condition") or {}
    if not condition:
        return None
    names = condition.get("translations", {})
    return {
        "temperature_c": condition.get("temperature"),
        "humidity_pct": condition.get("humidity"),
        "wind_speed": condition.get("windSpeed"),
        "weather": (names.get("weatherConditionName") or {}).get("EN"),
        "pitch": (names.get("pitchConditionName") or {}).get("EN"),
    }


def build_uefa_match_details(
    match: Dict[str, Any],
    lineup_feed: Optional[Dict[str, Any]],
    event_feed: Optional[Dict[str, Any]],
    match_feed: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    events = (event_feed or {}).get("events", [])
    lineups = build_lineups(lineup_feed, match)
    completed = match["status"] == "COMPLETED"
    return {
        "metadata": {
            "match_id": match["match_id"],
            "kickoff_label": match["kickoff_label"],
            "ground": match["ground_name"],
            "referee": match["referee_name"],
            "attendance": (match_feed or {}).get("matchAttendance"),
            "weather": _weather(match_feed),
            "home_xg": None,
            "away_xg": None,
            "total_xg": None,
            "stats_source": SOURCE_LABEL if events else None,
        },
        "lineups": lineups,
        "team_stats": build_team_stats(events, match["home_id"], match["away_id"]) if events and completed else [],
        "player_stats": {"home": [], "away": []},
        "events": [],
        "timeline": build_timeline(events, lineups, match) if events else [],
        "odds": [],
    }


# ---------------------------------------------------------------------------
# TheStatsAPI overlay: possession, xG, passing, duels, player ratings and shots
# ---------------------------------------------------------------------------

STATSAPI_SOURCE = "TheStatsAPI"


def _both(group: Optional[Dict[str, Any]], key: str) -> Optional[Tuple[Any, Any]]:
    value = ((group or {}).get(key) or {})
    value = value.get("all", value) if isinstance(value, dict) and "all" in value else value
    if not isinstance(value, dict) or value.get("home") is None or value.get("away") is None:
        return None
    return value["home"], value["away"]


def build_statsapi_team_stats(stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comparative team statistics in the same category layout the Premier League view uses."""
    sections = {name: stats.get(name) or {} for name in ("overview", "shots", "attack", "passes", "duels", "defending", "goalkeeping")}
    ov = sections["overview"]
    spec = [
        ("Şut & Hücum Hacmi", [
            ("Beklenen Gol (xG)", ov, "expected_goals", {"isXg": True}),
            ("Toplam Şut", sections["shots"], "total_shots", {}),
            ("İsabetli Şut", sections["shots"], "shots_on_target", {}),
            ("İsabetsiz Şut", sections["shots"], "shots_off_target", {}),
            ("Bloklanan Şut", sections["shots"], "blocked_shots", {}),
            ("Ceza Sahası İçi Şut", sections["shots"], "shots_inside_box", {}),
            ("Ceza Sahası Dışı Şut", sections["shots"], "shots_outside_box", {}),
            ("Direkten Dönen Şut", sections["shots"], "hit_woodwork", {}),
            ("Net Fırsat", ov, "big_chances", {}),
            ("Kaçan Net Fırsat", sections["attack"], "big_chances_missed", {}),
            ("Rakip Ceza Sahasında Topla Buluşma", sections["attack"], "touches_in_penalty_area", {}),
            ("Ofsayt", sections["attack"], "offsides", {}),
        ]),
        ("Top Hakimiyeti & Pas", [
            ("Topa Sahip Olma", ov, "ball_possession", {"suffix": "%"}),
            ("Toplam Pas", ov, "passes", {}),
            ("İsabetli Pas", ov, "accurate_passes", {}),
            ("İsabetli Orta", sections["passes"], "accurate_crosses", {}),
            ("İsabetli Uzun Top", sections["passes"], "accurate_long_balls", {}),
            ("Son Üçüncü Bölgeye Giriş", sections["passes"], "final_third_entries", {}),
            ("Taç", sections["passes"], "throw_ins", {}),
        ]),
        ("Düello & Savunma", [
            ("Düello Kazanma", sections["duels"], "duels_won_percentage", {"suffix": "%"}),
            ("Yer Düellosu", sections["duels"], "ground_duels_percentage", {"suffix": "%"}),
            ("Hava Düellosu", sections["duels"], "aerial_duels_percentage", {"suffix": "%"}),
            ("Dribling Başarısı", sections["duels"], "dribbles_percentage", {"suffix": "%"}),
            ("Top Kaybettirilme", sections["duels"], "dispossessed", {}),
            ("Top Çalma (Tackle)", sections["defending"], "tackles", {}),
            ("Tackle Başarısı", sections["defending"], "tackles_won_percentage", {"suffix": "%"}),
            ("Pas Arası", sections["defending"], "interceptions", {}),
            ("Uzaklaştırma", sections["defending"], "clearances", {}),
            ("Top Kazanma", sections["defending"], "ball_recoveries", {}),
        ]),
        ("Kaleci", [
            ("Kurtarış", sections["goalkeeping"], "saves", {}),
            ("Önlenen Gol", sections["goalkeeping"], "goals_prevented", {}),
            ("Aut Atışı", sections["goalkeeping"], "goal_kicks", {}),
            ("Yüksek Top Çıkışı", sections["goalkeeping"], "high_claims", {}),
        ]),
        ("Disiplin", [
            ("Faul", ov, "fouls", {}),
            ("Serbest Vuruş", ov, "free_kicks", {}),
            ("Korner", ov, "corner_kicks", {}),
            ("Sarı Kart", ov, "yellow_cards", {}),
            ("Kırmızı Kart", ov, "red_cards", {}),
        ]),
    ]
    categories = []
    for title, rows in spec:
        items = []
        for label, group, key, extra in rows:
            pair = _both(group, key)
            if pair is None:
                continue
            item = {"label": label, "home": pair[0], "away": pair[1], **extra}
            if extra.get("isXg"):
                item.update({"rawHome": pair[0], "rawAway": pair[1], "notFound": False})
            items.append(item)
        if items:
            categories.append({"category": title, "items": items})
    return categories


def _player_entry(base: Dict[str, Any], ps: Dict[str, Any], is_starter: bool, team_score: Any, opp_score: Any) -> Dict[str, Any]:
    shooting, passing = ps.get("shooting") or {}, ps.get("passing") or {}
    defending, general, duels = ps.get("defending") or {}, ps.get("general") or {}, ps.get("duels") or {}
    return {
        "id": base["id"], "name": base["name"], "shirt": base["shirt"], "position": base["position"],
        "is_starter": is_starter, "captain": base.get("captain", False), "photo_url": base.get("photo_url"),
        "minutes": ps.get("minutes_played") or 0,
        "goals": shooting.get("goals") or 0, "assists": passing.get("assists") or 0,
        "shots": shooting.get("total_shots") or 0, "shots_ontarget": shooting.get("shots_on_target") or 0,
        "fouls_committed": general.get("fouls") or 0, "fouls_won": general.get("was_fouled") or 0,
        "offsides": general.get("offsides") or 0,
        "yellow_cards": general.get("yellow_cards") or 0, "red_cards": general.get("red_cards") or 0,
        "penalties_won": 0, "penalties_conceded": 0, "penalties_missed": 0,
        "saves": (ps.get("goalkeeping") or {}).get("saves") or 0,
        "expected_goals": shooting.get("expected_goals"), "expected_assists": shooting.get("expected_assists"),
        "passes": passing.get("total_passes"), "accurate_passes": passing.get("accurate_passes"),
        "key_passes": passing.get("key_passes"), "touches": general.get("touches"),
        "tackles": defending.get("tackles"), "interceptions": defending.get("interceptions"),
        "clearances": defending.get("clearances"), "ball_recoveries": defending.get("ball_recoveries"),
        "duels_won": duels.get("duel_won"), "duels_lost": duels.get("duel_lost"),
        "rating": ps.get("rating"), "attack_rating": None, "defense_rating": None,
        "team_score": team_score or 0, "opp_score": opp_score or 0,
        "match_rating": ps.get("rating"), "is_match_rating": ps.get("rating") is not None,
    }


def apply_statsapi_payloads(result: Dict[str, Any], payloads: Dict[str, Dict[str, Any]], match: Dict[str, Any], odds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enrich a UEFA-feed match payload with TheStatsAPI statistics, ratings, xG and shots."""
    stats = (payloads.get("stats") or {}).get("data")
    if stats:
        result["team_stats"] = build_statsapi_team_stats(stats)
        xg = _both(stats.get("overview"), "expected_goals")
        if xg:
            result["metadata"].update({"home_xg": xg[0], "away_xg": xg[1], "total_xg": round(xg[0] + xg[1], 2), "xg_source": STATSAPI_SOURCE})
        result["metadata"]["stats_source"] = STATSAPI_SOURCE

    tsa_lineups = (payloads.get("lineups") or {}).get("data") or {}
    jersey_to_tsa_id: Dict[Tuple[str, Any], str] = {}
    for side in ("home", "away"):
        team = tsa_lineups.get(side) or {}
        for p in (team.get("starting_xi") or []) + (team.get("substitutes") or []):
            jersey_to_tsa_id[(side, p.get("jersey_number"))] = p["id"]
        for lineup in result["lineups"]:
            if lineup["team_id"] == (match["home_id"] if side == "home" else match["away_id"]) and team.get("formation"):
                lineup["formation"] = team["formation"]

    ps_by_tsa_id = {p["player_id"]: p for p in (payloads.get("player_stats") or {}).get("data") or []}
    player_stats: Dict[str, List[Dict[str, Any]]] = {"home": [], "away": []}
    for lineup in result["lineups"]:
        side = "home" if lineup["team_id"] == match["home_id"] else "away"
        team_score = match["home_score"] if side == "home" else match["away_score"]
        opp_score = match["away_score"] if side == "home" else match["home_score"]
        ratings = []
        for group, is_starter in ((lineup["starters"], True), (lineup["substitutes"], False)):
            for player in group:
                ps = ps_by_tsa_id.get(jersey_to_tsa_id.get((side, player["shirt"]), ""))
                if not ps:
                    continue
                player["rating"] = ps.get("rating")
                player["match_rating"] = ps.get("rating")
                player["is_match_rating"] = ps.get("rating") is not None
                if ps.get("played"):
                    player_stats[side].append(_player_entry(player, ps, is_starter, team_score, opp_score))
                    if is_starter and ps.get("rating") is not None:
                        ratings.append(ps["rating"])
        if ratings:
            lineup["team_ratings"] = {"overall": round(sum(ratings) / len(ratings), 2), "attack": None, "defense": None, "cards_risk": None}
    if player_stats["home"] or player_stats["away"]:
        result["player_stats"] = player_stats

    shots = (payloads.get("shotmap") or {}).get("data")
    if shots:
        result["shotmap"] = [
            {k: s.get(k) for k in ("player_name", "team_id", "minute", "x", "y", "expected_goals", "result", "situation", "body_part", "is_goal", "is_on_target")}
            for s in shots
        ]
    if odds:
        result["odds"] = odds
    return result
