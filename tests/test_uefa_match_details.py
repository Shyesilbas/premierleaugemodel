"""Offline tests for the UEFA match detail builder (no network)."""

from src.api.uefa_match_details import build_team_stats, build_timeline, build_uefa_match_details

MATCH = {
    "match_id": 1, "status": "COMPLETED", "kickoff_label": "Wed 21 Oct 2026, 20:00 BST", "ground_name": "Ground",
    "referee_name": "Ref", "home_id": 10, "home_name": "Home FC", "home_score": 1.0, "away_id": 20, "away_name": "Away FC", "away_score": 0.0,
}


def _event(etype, team, minute=10, person=None, **extra):
    actor = {"person": person or {"id": "900", "internationalName": "Player", "fieldPosition": "MIDFIELDER"}, "team": {"id": str(team)}}
    return {"type": etype, "time": {"minute": minute}, "timestamp": f"2026-10-21T20:{minute:02d}:00Z", "primaryActor": actor, **extra}


def _stats(events):
    items = build_team_stats(events, 10, 20)[0]["items"]
    return {i["label"]: (i["home"], i["away"]) for i in items}


def test_shot_tallies_count_a_goal_as_an_on_target_shot_and_skip_own_goals():
    events = [
        _event("SHOT_ON_GOAL", 10), _event("SHOT_WIDE", 10), _event("SHOT_BLOCKED", 20),
        _event("GOAL", 10, minute=30), _event("GOAL", 20, minute=40, subType="OWN"),
    ]
    stats = _stats(events)
    assert stats["Toplam Şut"] == (3, 1)
    assert stats["İsabetli Şut"] == (2, 0)


def test_saves_are_only_goalkeeper_actions():
    keeper = {"id": "1", "internationalName": "Keeper", "fieldPosition": "GOALKEEPER"}
    events = [_event("SAVE", 20, person=keeper), _event("SAVE", 20)]
    assert _stats(events)["Kaleci Kurtarışı"] == (0, 1)


def test_goal_goes_to_the_scorers_team_and_totalscore_is_ignored():
    # UEFA stamps the FINAL score on every goal event; the running score must be counted instead.
    final = {"home": 2, "away": 1}
    events = [
        _event("GOAL", 20, minute=5, totalScore=final),
        _event("GOAL", 10, minute=30, totalScore=final),
        _event("GOAL", 10, minute=70, totalScore=final),
    ]
    goals = [t for t in build_timeline(events, [{"starters": [], "substitutes": []}], MATCH) if t["type"] == "goal"]

    assert [g["team_id"] for g in goals] == [20, 10, 10]
    assert [g["score"] for g in goals] == ["0 - 1", "1 - 1", "2 - 1"]


def test_own_goal_counts_for_the_opponent_and_the_goalkeeper_is_not_an_assist():
    keeper = {"person": {"id": "1", "internationalName": "Keeper", "fieldPosition": "GOALKEEPER"}, "team": {"id": "20"}}
    events = [_event("GOAL", 10, minute=52, subType="OWN", secondaryActor=keeper, totalScore={"home": 0, "away": 1})]
    goal = build_timeline(events, [{"starters": [], "substitutes": []}], MATCH)[0]

    assert goal["is_own_goal"] and goal["team_id"] == 20 and goal["score"] == "0 - 1"
    assert goal["assist_name"] is None and goal["assist_id"] is None


def test_substitution_direction_follows_the_pitch():
    lineups = [{"starters": [{"id": 900, "photo_url": None}], "substitutes": [{"id": 901, "photo_url": None}]}]
    events = [_event("SUBSTITUTION", 10, minute=60, secondaryActor={"person": {"id": "901", "internationalName": "Bench"}})]
    sub = build_timeline(events, lineups, MATCH)[0]
    assert sub["player_out_name"] == "Player" and sub["player_in_name"] == "Bench"


def test_missing_feeds_still_return_the_basic_payload():
    result = build_uefa_match_details(MATCH, None, None)
    assert result["metadata"]["referee"] == "Ref" and result["metadata"]["stats_source"] is None
    assert result["lineups"] == [] and result["team_stats"] == [] and result["timeline"] == []


def test_attendance_weather_and_added_time_come_from_the_feeds():
    feed = {"matchAttendance": 67524, "condition": {"temperature": 17, "humidity": 63, "windSpeed": 3,
            "translations": {"weatherConditionName": {"EN": "clear night"}, "pitchConditionName": {"EN": "excellent"}}}}
    events = [{"type": "INJURY_TIME", "injuryTimeMinutesAdded": 4, "time": {"minute": 90}, "timestamp": "2026-10-21T20:46:00Z"}]

    result = build_uefa_match_details(MATCH, None, {"events": events}, feed)

    assert result["metadata"]["attendance"] == 67524
    assert result["metadata"]["weather"] == {"temperature_c": 17, "humidity_pct": 63, "wind_speed": 3, "weather": "clear night", "pitch": "excellent"}
    assert result["timeline"][0]["type"] == "added_time" and result["timeline"][0]["description"] == "+4 dakika"
