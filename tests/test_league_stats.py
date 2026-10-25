"""Statistics page rankings on a four-team, two-gameweek league built by hand."""

import pandas as pd
import pytest

from src.analytics.league_stats import build_league_stats, goal_bucket, pos_group

TEAMS = {i: {"name": f"Team {i}", "abbr": f"T{i}"} for i in (1, 2, 3, 4)}


def _match(match_id, gw, home, away, hs, a_s, kickoff, referee="Ref A", yellow=2, red=0):
    return {
        "match_id": match_id, "season": "2026_27", "gameweek": float(gw), "home_id": home, "away_id": away,
        "home_score": float(hs), "away_score": float(a_s), "kickoff_millis": float(kickoff),
        "referee_name": referee, "total_yellow_cards": yellow, "total_red_cards": red,
        "home_total_scoring_att": 10, "away_total_scoring_att": 5,
        "home_ontarget_scoring_att": 4, "away_ontarget_scoring_att": 2,
        "home_saves": 2, "away_saves": 3,
        "home_fk_foul_lost": 10, "away_fk_foul_lost": 12,
        "home_total_yel_card": 1, "away_total_yel_card": 2,
    }


MATCHES = pd.DataFrame([
    _match(1, 1, 1, 2, 2, 0, 1),
    _match(2, 1, 3, 4, 1, 1, 2),
    _match(3, 2, 3, 1, 0, 3, 3, referee="Ref B", red=1),
    _match(4, 2, 4, 2, 1, 0, 4, referee="Ref B"),
    {**_match(5, 3, 1, 4, 0, 0, 5), "home_score": float("nan"), "away_score": float("nan")},  # unplayed
])


def _log(match_id, gw, team, opp, team_score, opp_score, position, goals=0, assists=0, minutes=90):
    return {
        "match_id": match_id, "season": "2026_27", "gameweek": float(gw), "team_id": team, "team_name": TEAMS[team]["name"],
        "opponent_id": opp, "team_score": team_score, "opp_score": opp_score, "started": True,
        "position": position, "minutes_played": minutes, "goals": goals, "assists": assists,
    }


LOGS = {
    "10": [_log(1, 1, 1, 2, 2, 0, "F", goals=2), _log(3, 2, 1, 3, 3, 0, "F", goals=1, assists=1)],
    "11": [_log(1, 1, 1, 2, 2, 0, "G"), _log(3, 2, 1, 3, 3, 0, "G")],
    "20": [_log(2, 1, 4, 3, 1, 1, "M", goals=1)],
}
REGISTRY = {10: {"name": "Striker One"}, 11: {"name": "Keeper One"}, 20: {"name": "Mid Four"}}
GOAL_EVENTS = pd.DataFrame([
    {"match_id": 1, "event_id": 1, "event_type": "goal", "minute": "10", "seconds": 600, "text": "Goal!  Team 1 1, Team 2 0. Striker One (Team 1) shot."},
    {"match_id": 1, "event_id": 2, "event_type": "goal", "minute": "90+2", "seconds": 5500, "text": "Goal!  Team 1 2, Team 2 0. Striker One (Team 1) shot."},
])


def _build(scope, gameweek=None):
    return build_league_stats(
        season="2026_27", scope=scope, gameweek=gameweek, matches=MATCHES, logs=LOGS, registry=REGISTRY,
        bookings={}, goal_events=GOAL_EVENTS, audit_rows=[], ages={20: 19}, teams=TEAMS,
    )


@pytest.mark.parametrize("minute, bucket", [("01", 0), ("15", 0), ("16", 1), ("45+3", 2), ("46", 3), ("90+11", 5), ("", None)])
def test_goal_bucket_groups_minutes_and_stoppage_time(minute, bucket):
    assert goal_bucket(minute) == bucket


def test_pos_group_defaults_unknown_labels_to_midfield():
    assert [pos_group(p) for p in ("G", "DEF", "forward", None, "?")] == ["G", "D", "F", "M", "M"]


def test_week_scope_covers_one_gameweek_and_ignores_unplayed_matches():
    stats = _build("week", 2)
    assert stats["gameweek"] == 2 and stats["gameweeks"] == [1, 2] and stats["matches_in_scope"] == 2
    assert [row["team"]["id"] for row in stats["attack"][:1]] == [1]
    assert stats["top_scorers"][0]["id"] == 10 and stats["top_scorers"][0]["goals"] == 1
    assert stats["top_scorers"][0]["season_goals"] == 3  # cumulative total travels with the week row


def test_unknown_gameweek_falls_back_to_the_latest_played_one():
    assert _build("week", 30)["gameweek"] == 2


def test_season_scope_adds_up_every_played_match():
    stats = _build("season")
    attack = {row["team"]["id"]: row["goals"] for row in stats["attack"]}
    assert attack == {1: 5, 3: 1, 4: 2, 2: 0}
    assert stats["defence"][0]["team"]["id"] == 1 and stats["defence"][0]["clean_sheets"] == 2


def test_team_of_the_scope_picks_the_best_player_per_position():
    players = {p["id"] for p in _build("week", 1)["team_of_scope"]["players"]}
    assert {10, 11} <= players


def test_movers_compare_table_rank_with_the_previous_gameweek():
    movers = _build("week", 2)["movers"]
    assert movers["reference_gameweek"] == 1
    assert [row["team"]["id"] for row in movers["risers"]] == [4]
    assert [row["team"]["id"] for row in movers["fallers"]] == [3]


def test_venue_tables_split_home_and_away_points():
    venue = _build("season")["venue"]
    assert venue["home"][0]["team"]["id"] == 1 and venue["home"][0]["points"] == 3
    assert venue["away"][0]["team"]["id"] == 1 and venue["away"][0]["points"] == 3
    assert (venue["home_wins"], venue["draws"], venue["away_wins"]) == (2, 1, 1)


def test_goal_minutes_follow_the_score_line_not_the_scorer_name():
    minutes = _build("season")["goal_minutes"]
    assert minutes["league"] == [1, 0, 0, 0, 0, 1]
    team1 = next(row for row in minutes["teams"] if row["team"]["id"] == 1)
    team2 = next(row for row in minutes["teams"] if row["team"]["id"] == 2)
    assert team1["scored"] == [1, 0, 0, 0, 0, 1] and team2["conceded"] == [1, 0, 0, 0, 0, 1]


def test_referee_ranking_counts_cards_per_match():
    referees = _build("season")["referees"]
    assert referees[0]["name"] == "Ref B" and referees[0]["cards_per_match"] == 2.5


def test_young_players_use_the_age_map_and_report_missing_ages():
    young = _build("season")["young_players"]
    assert young["available"] and [p["id"] for p in young["players"]] == [20]
    empty = build_league_stats(
        season="2026_27", scope="season", gameweek=None, matches=MATCHES, logs=LOGS, registry=REGISTRY,
        bookings={}, goal_events=GOAL_EVENTS, audit_rows=[], ages={}, teams=TEAMS,
    )
    assert empty["young_players"]["available"] is False


def test_an_unplayed_season_returns_an_empty_payload():
    stats = build_league_stats(
        season="2030_31", scope="week", gameweek=None, matches=MATCHES, logs=LOGS, registry=REGISTRY,
        bookings={}, goal_events=GOAL_EVENTS, audit_rows=[], ages={}, teams=TEAMS,
    )
    assert stats["gameweeks"] == [] and stats["matches_in_scope"] == 0


def test_goal_minutes_carry_the_selected_week_next_to_the_cumulative_total():
    week_one = _build("week", 1)["goal_minutes"]
    assert week_one["league_scope"] == week_one["league"] == [1, 0, 0, 0, 0, 1]
    week_two = _build("week", 2)["goal_minutes"]
    assert week_two["league"] == [1, 0, 0, 0, 0, 1] and week_two["league_scope"] == [0] * 6
    team1 = next(row for row in week_two["teams"] if row["team"]["id"] == 1)
    assert team1["scored"] == [1, 0, 0, 0, 0, 1] and team1["scope_scored"] == [0] * 6
    season = _build("season")["goal_minutes"]
    assert season["league_scope"] == season["league"]


def test_team_discipline_reports_fouls_committed_per_team():
    teams = _build("week", 1)["discipline"]["teams"]
    assert teams, "yellow cards were reported in the match"
    by_id = {row["team"]["id"]: row for row in teams}
    assert by_id[1]["fouls"] == 10 and by_id[2]["fouls"] == 12 and by_id[2]["fouls_per_match"] == 12.0
