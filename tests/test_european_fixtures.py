"""Champions League and Europa League matches inside a Premier League club's fixture list."""

import sqlite3

from fastapi.testclient import TestClient

from src.api.european_fixtures import _kickoff_millis, european_matches, round_label, uefa_club_ids
from src.api.server import app


def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE matches (match_id INTEGER PRIMARY KEY, competition_id INT, season TEXT, stage TEXT, group_name TEXT, leg INT, gameweek INT,"
        " match_date TEXT, time_label TEXT, kickoff_label TEXT, status TEXT, ground_name TEXT,"
        " home_id INT, home_name TEXT, home_logo TEXT, home_score REAL, away_id INT, away_name TEXT, away_logo TEXT, away_score REAL,"
        " home_penalties REAL, away_penalties REAL)"
    )
    rows = [
        (1, 2, "2025_26", "league", None, None, 1, "2025-09-16", "17:45 BST", "Tue 16 Sep 2025, 17:45 BST", "COMPLETED", "Emirates", 52280, "Arsenal", "h.png", 2, 99, "Athletic Club", "a.png", 0),
        (2, 2, "2025_26", "r16", None, 2, 10, "2026-03-17", "20:00 GMT", "Tue 17 Mar 2026, 20:00 GMT", "COMPLETED", "Allianz", 50037, "Bayern München", "b.png", 1, 52280, "Arsenal", "h.png", 3),
        (3, 3, "2025_26", "league", None, None, 4, "2025-10-23", "20:00 BST", "Thu 23 Oct 2025, 20:00 BST", "UPCOMING", "Villa Park", 52683, "Aston Villa", "v.png", None, 98, "Salzburg", "s.png", None),
        (4, 2, "2025_26", "league", None, None, 1, "2025-09-17", "20:00 BST", "Wed 17 Sep 2025, 20:00 BST", "COMPLETED", "Etihad", 52919, "Man City", "m.png", 1, 97, "Napoli", "n.png", 1),
    ]
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)", rows)
    return conn


def test_clubs_are_paired_by_name_across_the_two_id_systems():
    conn = _db()
    assert uefa_club_ids(conn, "Arsenal", "2025_26") == {52280}
    assert uefa_club_ids(conn, "Manchester City", "2025_26") == {52919}  # "Man City" in the UEFA data
    assert uefa_club_ids(conn, "Coventry City", "2025_26") == set()


def test_matches_are_oriented_to_the_club_and_flagged_with_their_competition():
    first, second = european_matches(_db(), "Arsenal", "2025_26")

    assert first["competition"]["abbr"] == "ŞL" and first["is_home"] and first["result"] == "W" and (first["team_score"], first["opp_score"]) == (2, 0)
    assert second["is_home"] is False and (second["team_score"], second["opp_score"]) == (3, 1) and second["result"] == "W"
    assert second["round_label"] == "Son 16 · 2. maç" and second["home_name"] == "Bayern München"  # real UEFA sides for the match page
    assert first["opponent_logo"] == "a.png"


def test_unplayed_matches_have_no_result_and_kickoffs_are_london_time():
    (match,) = european_matches(_db(), "Aston Villa", "2025_26")
    assert match["status"] == "UNPLAYED" and match["result"] == "-" and match["team_score"] is None
    assert match["competition"]["abbr"] == "AL"
    # 20:00 BST on 23 Oct 2025 is 19:00 UTC
    assert _kickoff_millis("2025-10-23", "20:00 BST") == 1761246000000
    assert _kickoff_millis("2026-03-17", "20:00 GMT") == 1773777600000


def test_round_labels_cover_both_formats():
    assert round_label({"stage": "group", "group_name": "C", "gameweek": 4}) == "Grup C · 4. hafta"
    assert round_label({"stage": "league", "gameweek": 3}) == "Lig aşaması · 3. hafta"
    assert round_label({"stage": "final", "leg": None, "gameweek": 13}) == "Final"


def test_premier_league_profile_lists_european_matches_in_kickoff_order():
    client = TestClient(app)
    profile = client.get("/api/teams/profile?team_id=1&season=2025_26").json()  # Arsenal

    matches = profile["matches"]
    competitions = {m["competition"]["abbr"] for m in matches}
    assert {"PL", "ŞL"} <= competitions
    assert sum(m["competition"]["abbr"] == "PL" for m in matches) == 38
    assert profile["record"]["played"] == 38  # the league record is not mixed with European matches
    kickoffs = [m["kickoff_millis"] for m in matches if m["kickoff_millis"]]
    assert kickoffs == sorted(kickoffs)

    domestic_only = client.get("/api/teams/profile?team_id=5&season=2026_27").json()  # Coventry: no European football
    assert {m["competition"]["abbr"] for m in domestic_only["matches"]} == {"PL"}


def test_every_premier_league_club_has_a_bundled_badge_entry():
    """A club missing from teams.js loses its logo everywhere (this happened to Liverpool once)."""
    import re
    from pathlib import Path

    from src.db.database import get_db

    teams_js = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "teams.js").read_text(encoding="utf-8")
    bundled = {int(i) for i in re.findall(r"^\s*\{ id: (\d+),", teams_js, re.M)}
    conn = get_db()
    try:
        used = {r[0] for r in conn.execute("SELECT home_id FROM matches WHERE competition_id = 39 UNION SELECT away_id FROM matches WHERE competition_id = 39")}
    finally:
        conn.close()
    assert not used - bundled, f"clubs without a teams.js entry: {sorted(used - bundled)}"
    badge_files = {p.stem for p in (Path(__file__).resolve().parents[1] / "frontend" / "public" / "badges").glob("*.svg")}
    assert not {str(i) for i in used} - badge_files, "clubs without a badge file"


def test_people_are_paired_across_spelling_differences():
    from src.api.european_fixtures import same_person

    assert same_person("Michael Oliver", "Michael Oliver")
    assert same_person("Martin Ødegaard", "Martin Odegaard")  # accents
    assert same_person("M. Oliver", "Michael Oliver")  # initial + surname
    assert not same_person("Michael Oliver", "Mike Dean")
    assert not same_person("Gabriel Jesus", "Gabriel")  # a single name is never guessed into a full one


def _people_db():
    import json

    conn = _db()
    conn.executescript(
        "ALTER TABLE matches ADD COLUMN referee_name TEXT; ALTER TABLE matches ADD COLUMN total_yellow_cards REAL;"
        "ALTER TABLE matches ADD COLUMN total_red_cards REAL; ALTER TABLE matches ADD COLUMN total_cards REAL; ALTER TABLE matches ADD COLUMN total_fouls REAL;"
        "CREATE TABLE external_match_payloads (match_id INT, provider TEXT, kind TEXT, provider_match_id TEXT, payload TEXT, fetched_at_utc TEXT);"
        "UPDATE matches SET referee_name = 'Michael Oliver' WHERE match_id IN (1, 2, 3);"
        "UPDATE matches SET total_yellow_cards = 4, total_red_cards = 1, total_cards = 5, total_fouls = 24 WHERE match_id = 1;"  # match 2 has no statistics
    )
    stats = [
        {"player_id": "pl_1", "player_name": "Declan Rice", "team_id": "tm_1", "played": True, "started": True, "minutes_played": 90, "rating": 7.4,
         "shooting": {"goals": 1}, "passing": {"assists": 0}},
        {"player_id": "pl_2", "player_name": "Someone Else", "team_id": "tm_2", "played": True, "started": True, "minutes_played": 90, "rating": 6.0},
    ]
    for match_id in (1, 2):
        conn.execute("INSERT INTO external_match_payloads VALUES (?, 'TheStatsAPI', 'player_stats', 'mt', ?, 'now')", (match_id, json.dumps({"data": stats})))
    return conn


def test_referee_european_stats_only_count_matches_that_have_statistics():
    from src.api.european_fixtures import referee_european_matches

    result = referee_european_matches(_people_db(), "Michael Oliver", "2025_26")

    assert [m["match_id"] for m in result["matches"]] == [2, 1]  # completed only, newest first; the upcoming match 3 is excluded
    stats = result["stats"]
    assert stats["matches_count"] == 2 and stats["matches_with_stats"] == 1
    assert stats["avg_cards"] == 5.0 and stats["total_yellow_cards"] == 4  # not diluted by the match without data
    assert referee_european_matches(_people_db(), "Nobody Known", "2025_26") == {"matches": [], "stats": None}


def test_player_european_log_matches_by_name_inside_the_players_club():
    from src.api.european_fixtures import player_european_log

    log = player_european_log(_people_db(), "Declan Rice", {"2025_26": {"Arsenal"}})

    assert [m["match_id"] for m in log["matches"]] == [1, 2] or [m["match_id"] for m in log["matches"]] == [1]
    assert log["stats"]["goals"] == len(log["matches"]) and log["matches"][0]["competition"]["abbr"] == "ŞL"
    assert player_european_log(_people_db(), "Declan Rice", {"2025_26": {"Chelsea"}})["matches"] == []  # a different club's games are not his


def test_league_referee_detail_keeps_european_games_out_of_the_league_numbers():
    client = TestClient(app)
    detail = client.get("/api/referees/Michael Oliver?season=2025_26").json()

    assert detail["european"]["matches"], "expected Champions League games for a Premier League referee"
    league_ids = {m["match_id"] for m in detail["matches"]}
    assert league_ids.isdisjoint({m["match_id"] for m in detail["european"]["matches"]})
    assert all(m["match_id"] < 2_000_000 for m in detail["matches"])  # UEFA match ids are all above this
