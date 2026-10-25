"""Offline tests for knockout tie aggregation and bracket layout."""

from src.api.knockout import build_bracket, build_ties, tie_summaries


def _leg(match_id, stage, leg, home, away, hs, as_, advancing=None, reason=None, date="2026-03-01", hp=None, ap=None, status="COMPLETED"):
    return {
        "match_id": match_id, "stage": stage, "leg": leg, "status": status, "match_date": date,
        "home_id": home[0], "home_name": home[1], "away_id": away[0], "away_name": away[1],
        "home_score": hs, "away_score": as_, "advancing_team_id": advancing, "advance_reason": reason,
        "home_penalties": hp, "away_penalties": ap,
    }


A, B, C, D = (1, "Alpha"), (2, "Bravo"), (3, "Charlie"), (4, "Delta")


def test_two_legs_are_aggregated_and_the_advancing_team_is_reported():
    rows = [
        _leg(1, "r16", 1, A, B, 2, 0, advancing=1, reason="WIN_ON_AGGREGATE", date="2026-03-01"),
        _leg(2, "r16", 2, B, A, 3, 1, advancing=2, reason="WIN_ON_AGGREGATE", date="2026-03-08"),
    ]
    rows[0]["advancing_team_id"] = rows[1]["advancing_team_id"] = 2  # provider repeats the tie winner on both legs

    (tie,) = build_ties(rows)
    assert tie["aggregate"] == {1: 3, 2: 3} and tie["winner_id"] == 2 and tie["completed"]

    summary = tie_summaries(rows)
    assert summary[1]["aggregate"] == {"home": 3, "away": 3} and summary[1]["advanced_team_name"] == "Bravo"
    assert summary[2]["leg"] == 2 and summary[2]["advance_label"] == "toplam skorla"


def test_unplayed_second_leg_leaves_the_tie_undecided():
    rows = [
        _leg(1, "qf", 1, A, B, 1, 1),
        _leg(2, "qf", 2, B, A, None, None, status="UPCOMING", date="2026-04-08"),
    ]
    (tie,) = build_ties(rows)
    assert not tie["completed"] and tie["aggregate"] is None and tie["winner_id"] is None
    assert tie_summaries(rows)[1]["decided"] is False


def test_shootout_is_kept_and_a_single_match_final_has_a_winner():
    rows = [_leg(9, "final", None, A, B, 1, 1, advancing=1, reason="WIN_ON_PENALTIES", hp=4, ap=3)]
    (tie,) = build_ties(rows)
    assert tie["penalties"] == {1: 4, 2: 3} and tie["winner_id"] == 1 and tie["aggregate"] is None


def test_league_phase_rows_are_not_part_of_a_tie():
    assert build_ties([_leg(1, "league", None, A, B, 1, 0)]) == []


def test_bracket_places_feeder_ties_next_to_the_tie_they_feed():
    rows = [
        _leg(1, "sf", 1, A, C, 1, 0, advancing=1, reason="WIN_ON_AGGREGATE"),
        _leg(2, "sf", 1, B, D, 1, 0, advancing=2, reason="WIN_ON_AGGREGATE"),
        _leg(3, "final", None, A, B, 2, 1, advancing=1, reason="WIN_REGULAR"),
        # quarter-finals listed in the opposite order to the semi-finals they feed
        _leg(4, "qf", 1, B, D, 1, 0, advancing=2, reason="WIN_ON_AGGREGATE", date="2026-02-01"),
        _leg(5, "qf", 1, A, C, 1, 0, advancing=1, reason="WIN_ON_AGGREGATE", date="2026-02-02"),
    ]
    bracket = build_bracket(rows)

    assert [r["stage"] for r in bracket["rounds"]] == ["qf", "sf", "final"]
    qf = bracket["rounds"][0]["ties"]
    sf = bracket["rounds"][1]["ties"]
    assert {t["id"] for t in qf[0]["teams"]} == {t["id"] for t in sf[0]["teams"]}
    assert bracket["champion"]["name"] == "Alpha"
