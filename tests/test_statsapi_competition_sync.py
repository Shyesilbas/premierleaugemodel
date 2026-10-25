"""Offline tests for the TheStatsAPI UEFA sync and the match-detail overlay (no network)."""

import sqlite3

from src.api.uefa_match_details import apply_statsapi_payloads, build_statsapi_team_stats
from src.db.database import ensure_external_payload_tables
from src.ingest.sync_thestatsapi_competition import club_similarity, map_fixtures, normalize_club, team_totals

STATS = {
    "overview": {
        "ball_possession": {"all": {"home": 47, "away": 53}},
        "expected_goals": {"all": {"home": 2.14, "away": 0.78}},
        "total_shots": {"all": {"home": 23, "away": 12}},
        "shots_on_target": {"all": {"home": 10, "away": 2}},
        "goalkeeper_saves": {"all": {"home": 2, "away": 9}},
        "corner_kicks": {"all": {"home": 4, "away": 4}},
        "fouls": {"all": {"home": 8, "away": 10}},
        "yellow_cards": {"all": {"home": 1, "away": 2}},
        "red_cards": {"all": {"home": 0, "away": 0}},
    },
    "passes": {"throw_ins": {"all": {"home": 13, "away": 15}}},
}


def test_club_names_from_both_providers_resolve_to_the_same_club():
    assert normalize_club("Man Utd") == normalize_club("Manchester United")
    assert club_similarity("Atleti", "Atlético Madrid") == 1.0
    assert club_similarity("PSV", "PSV Eindhoven") >= 0.95
    assert club_similarity("Club Brugge", "Club Brugge KV") >= 0.95
    assert club_similarity("B. Dortmund", "Borussia Dortmund") == 1.0
    assert club_similarity("Rennes", "Stade Rennais") == 1.0
    assert club_similarity("FC København", "Copenhagen") == 1.0
    assert normalize_club("FC København") == "kobenhavn"  # not "kbenhavn": the slashed o is transliterated
    assert club_similarity("Maccabi Tel Aviv", "M. Tel-Aviv") == 1.0
    assert club_similarity("H. Beer-Sheva", "Hapoel Be'er Sheva") == 1.0
    assert club_similarity("Union SG", "Royale Union Saint-Gilloise") == 1.0
    assert club_similarity("Lille", "Galatasaray") < 0.5


def test_two_legs_of_the_same_tie_are_paired_by_date():
    local = [
        {"match_id": 1, "home_name": "Man City", "away_name": "Napoli", "match_date": "2027-02-17"},
        {"match_id": 2, "home_name": "Man City", "away_name": "Napoli", "match_date": "2027-03-10"},
    ]
    api = [
        {"id": "b", "utc_date": "2027-03-10T20:00:00Z", "home_team": {"name": "Manchester City"}, "away_team": {"name": "Napoli"}},
        {"id": "a", "utc_date": "2027-02-17T20:00:00Z", "home_team": {"name": "Manchester City"}, "away_team": {"name": "Napoli"}},
    ]
    pairs, unmapped = map_fixtures(api, local)
    assert {(a["id"], l["match_id"]) for a, l in pairs} == {("a", 1), ("b", 2)} and not unmapped


def test_unrelated_fixture_is_left_unmapped():
    local = [{"match_id": 1, "home_name": "Lille", "away_name": "Roma", "match_date": "2026-10-01"}]
    api = [{"id": "x", "utc_date": "2026-10-01T19:00:00Z", "home_team": {"name": "Bodø/Glimt"}, "away_team": {"name": "Celtic"}}]
    pairs, unmapped = map_fixtures(api, local)
    assert not pairs and len(unmapped) == 1


def test_team_totals_use_the_legacy_match_columns():
    totals = team_totals(STATS)
    assert totals["total_corners"] == 8 and totals["total_shots"] == 35 and totals["total_saves"] == 11
    assert totals["total_cards"] == 3 and totals["total_fouls"] == 18 and totals["total_throws"] == 28
    assert totals["home_xg"] == 2.14 and totals["total_xg"] == 2.92


def test_team_stats_skip_missing_values_instead_of_inventing_them():
    categories = {c["category"]: c["items"] for c in build_statsapi_team_stats(STATS)}
    labels = {i["label"]: (i["home"], i["away"]) for items in categories.values() for i in items}
    assert labels["Topa Sahip Olma"] == (47, 53) and labels["Korner"] == (4, 4)
    assert "Toplam Pas" not in labels and "Düello Kazanma" not in labels


def test_overlay_attaches_ratings_by_shirt_number_and_formation():
    match = {"home_id": 10, "away_id": 20, "home_score": 1.0, "away_score": 0.0}
    result = {
        "metadata": {},
        "lineups": [
            {"team_id": 10, "formation": "4-3-3", "team_ratings": None,
             "starters": [{"id": 111, "name": "Home Keeper", "shirt": 1, "position": "G", "photo_url": None, "rating": None}], "substitutes": []},
            {"team_id": 20, "formation": "4-4-2", "team_ratings": None, "starters": [], "substitutes": []},
        ],
        "team_stats": [], "player_stats": {"home": [], "away": []}, "odds": [],
    }
    payloads = {
        "stats": {"data": STATS},
        "lineups": {"data": {"home": {"formation": "4-2-3-1", "starting_xi": [{"id": "pl_1", "jersey_number": 1}], "substitutes": []}, "away": {}}},
        "player_stats": {"data": [{"player_id": "pl_1", "rating": 7.4, "played": True, "minutes_played": 90, "goalkeeping": {"saves": 2}}]},
    }
    out = apply_statsapi_payloads(result, payloads, match, odds=[])

    home = out["lineups"][0]
    assert home["formation"] == "4-2-3-1" and home["starters"][0]["rating"] == 7.4
    assert home["team_ratings"]["overall"] == 7.4 and out["lineups"][1]["team_ratings"] is None
    assert out["player_stats"]["home"][0]["saves"] == 2 and out["metadata"]["home_xg"] == 2.14


def test_payload_tables_are_created_idempotently():
    conn = sqlite3.connect(":memory:")
    ensure_external_payload_tables(conn)
    ensure_external_payload_tables(conn)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"external_match_payloads", "external_competition_payloads"} <= names


def _squad_db():
    import json
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE matches (match_id INTEGER PRIMARY KEY, competition_id INT, season TEXT, gameweek INT, match_date TEXT, kickoff_label TEXT,"
        " home_id INT, home_name TEXT, home_score REAL, away_id INT, away_name TEXT, away_score REAL, status TEXT);"
    )
    ensure_external_payload_tables(conn)
    conn.execute("INSERT INTO matches VALUES (1, 2, '2026_27', 1, '2026-09-08', 'Tue', 52280, 'Arsenal', 2, 50138, 'Inter', 1, 'COMPLETED')")
    squad = {"team": {"id": "tm_1", "name": "Arsenal FC"}, "data": [
        {"id": "pl_9", "name": "Striker", "position": "F", "age": 24, "nationality": "England", "market_value": 90000000, "current_team": {"jersey_number": 9}},
        {"id": "pl_2", "name": "Bench Guy", "position": "D", "age": 31, "nationality": "Spain", "market_value": None, "current_team": {"jersey_number": 22}},
    ]}
    conn.execute("INSERT INTO external_competition_payloads VALUES (2, '2026_27', 'TheStatsAPI', 'squad', 'tm_1', ?, 'now')", (json.dumps(squad),))
    stats = [{"player_id": "pl_9", "team_id": "tm_1", "played": True, "started": True, "minutes_played": 90, "rating": 8.0,
              "shooting": {"goals": 2, "expected_goals": 1.1}, "passing": {"assists": 1}, "general": {"yellow_cards": 1}}]
    conn.execute("INSERT INTO external_match_payloads VALUES (1, 'TheStatsAPI', 'player_stats', 'mt_1', ?, 'now')", (json.dumps({"data": stats}),))
    return conn


def test_squad_profile_uses_real_values_and_leaves_unknowns_empty():
    from src.api.competition_squads import build_squad_profile
    squad, market_value, _ = build_squad_profile(_squad_db(), 2, "2026_27", 52280, "Arsenal")

    assert [p["name"] for p in squad] == ["Striker", "Bench Guy"]
    assert squad[0]["goals"] == 2 and squad[0]["assists"] == 1 and squad[0]["yellow_cards"] == 1 and squad[0]["avg_rating"] == 8.0
    assert squad[1]["market_value_eur"] is None and squad[1]["appearances"] == 0
    assert market_value["market_value_eur"] == 90000000 and market_value["squad_size"] == 1


def test_unsynced_club_returns_nothing():
    from src.api.competition_squads import build_squad_profile
    assert build_squad_profile(_squad_db(), 2, "2026_27", 1, "Totally Different FC") == ([], None, None)


def test_player_directory_and_profile_come_from_the_same_payloads():
    from src.api.competition_squads import build_player_profile, list_squad_players
    conn = _squad_db()

    listing = list_squad_players(conn, 2, "2026_27", None, "strik", 10)
    assert listing["total"] == 1 and listing["players"][0]["teamId"] == 52280

    profile = build_player_profile(conn, 2, "2026_27", "pl_9")
    assert profile["season_stats"]["goals"] == 2 and profile["matches"][0]["opponent_name"] == "Inter"
    assert profile["player"]["market_value"]["formatted"] == "€90.0M"
    assert build_player_profile(conn, 2, "2026_27", "pl_404") is None


def test_competition_stats_use_provider_ratings_and_logos():
    import json
    from src.api.competition_stats import build_competition_stats

    conn = _squad_db()
    conn.executescript(
        "ALTER TABLE matches ADD COLUMN stage TEXT; ALTER TABLE matches ADD COLUMN home_abbr TEXT; ALTER TABLE matches ADD COLUMN away_abbr TEXT;"
        "ALTER TABLE matches ADD COLUMN home_logo TEXT; ALTER TABLE matches ADD COLUMN away_logo TEXT;"
        "UPDATE matches SET stage = 'league', home_abbr = 'ARS', away_abbr = 'INT', home_logo = 'https://img/ars.png', away_logo = 'https://img/int.png';"
    )
    stats = {"overview": {"expected_goals": {"all": {"home": 1.5, "away": 0.4}}, "total_shots": {"all": {"home": 14, "away": 5}},
                          "goalkeeper_saves": {"all": {"home": 2, "away": 5}}, "fouls": {"all": {"home": 9, "away": 11}}},
             "shots": {"shots_on_target": {"all": {"home": 6, "away": 2}}}}
    conn.execute("INSERT INTO external_match_payloads VALUES (1, 'TheStatsAPI', 'stats', 'mt_1', ?, 'now')", (json.dumps({"data": stats}),))

    result = build_competition_stats(conn, 2, "2026_27", "season", None)

    assert result["gameweeks"] == [1] and result["matches_in_scope"] == 1
    attack = {row["team"]["name"]: row for row in result["attack"]}
    assert attack["Arsenal"]["xg"] == 1.5 and attack["Arsenal"]["shots"] == 14
    assert attack["Arsenal"]["team"]["badge"] == "https://img/ars.png"


def test_managers_are_mapped_to_local_team_ids():
    import json
    from src.api.competition_squads import club_managers

    conn = _squad_db()
    managers = {"managers": {"tm_1": {"name": "Mikel Arteta", "team": "Arsenal FC"}, "tm_x": {"name": "Nobody", "team": "Totally Different FC"}}}
    conn.execute("INSERT INTO external_competition_payloads VALUES (2, '2026_27', 'TheStatsAPI', 'managers', '', ?, 'now')", (json.dumps(managers),))

    assert club_managers(conn, 2, "2026_27") == {52280: "Mikel Arteta"}


def test_past_season_squad_lists_only_players_who_played_and_gives_no_team_total():
    from src.api.competition_squads import build_squad_profile, list_squad_players
    conn = _squad_db()
    conn.execute("UPDATE matches SET season = '2025_26'")
    conn.execute("UPDATE external_competition_payloads SET season = '2025_26'")

    squad, market_value, _ = build_squad_profile(conn, 2, "2025_26", 52280, "Arsenal")
    assert [p["name"] for p in squad] == ["Striker"] and market_value is None
    assert [p["name"] for p in list_squad_players(conn, 2, "2025_26", None, None, 10)["players"]] == ["Striker"]


def test_past_season_keeps_players_who_have_since_left_the_club():
    import json
    from src.api.competition_squads import build_player_profile, build_squad_profile, list_squad_players

    conn = _squad_db()
    conn.execute("UPDATE matches SET season = '2025_26'")
    conn.execute("UPDATE external_competition_payloads SET season = '2025_26'")
    stats = [
        {"player_id": "pl_9", "team_id": "tm_1", "played": True, "started": True, "minutes_played": 90, "rating": 8.0, "shooting": {"goals": 1}},
        {"player_id": "pl_gone", "player_name": "Departed Winger", "position": "F", "team_id": "tm_1", "played": True, "started": True,
         "minutes_played": 70, "rating": 6.5, "shooting": {"goals": 1}},
    ]
    conn.execute("UPDATE external_match_payloads SET payload = ? WHERE kind = 'player_stats'", (json.dumps({"data": stats}),))

    squad, _, _ = build_squad_profile(conn, 2, "2025_26", 52280, "Arsenal")
    assert {p["name"] for p in squad} == {"Striker", "Departed Winger"}
    assert "Departed Winger" in {p["name"] for p in list_squad_players(conn, 2, "2025_26", None, None, 10)["players"]}
    profile = build_player_profile(conn, 2, "2025_26", "pl_gone")
    assert profile["player"]["name"] == "Departed Winger" and profile["season_stats"]["goals"] == 1


def test_paced_client_overlaps_requests_but_keeps_start_times_apart():
    import io
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor
    from unittest import mock

    from src.ingest.sync_thestatsapi_competition import PacedClient

    starts = []

    def slow_urlopen(request, timeout=0):
        starts.append(time.monotonic())
        time.sleep(0.2)  # network latency, longer than the pacing interval
        return io.BytesIO(json.dumps({"ok": True}).encode())

    client = PacedClient("key", minimum_interval=0.05)
    began = time.monotonic()
    with mock.patch("src.ingest.sync_thestatsapi_competition.urlopen", slow_urlopen), ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda i: client.get_json(f"/x/{i}"), range(8)))
    elapsed = time.monotonic() - began

    assert all(r == {"ok": True} for r in results)
    starts.sort()
    # timers wake with some jitter, so check the average spacing rather than every single gap
    assert (starts[-1] - starts[0]) / (len(starts) - 1) >= 0.045  # never faster than the limit
    assert elapsed < 8 * 0.2 * 0.7  # a serial client would need 8 x 0.2 s


def test_paced_client_retries_a_stalled_request_instead_of_hanging():
    import io
    import json
    from unittest import mock

    from src.ingest.sync_thestatsapi_competition import PacedClient

    calls = {"n": 0}

    def flaky_urlopen(request, timeout=0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("read timed out")
        assert timeout <= 30  # every attempt is bounded
        return io.BytesIO(json.dumps({"ok": 1}).encode())

    client = PacedClient("key", minimum_interval=0.0)
    with mock.patch("src.ingest.sync_thestatsapi_competition.urlopen", flaky_urlopen):
        assert client.get_json("/x") == {"ok": 1}
    assert calls["n"] == 3

    with mock.patch("src.ingest.sync_thestatsapi_competition.urlopen", mock.Mock(side_effect=TimeoutError("down"))):
        try:
            client.get_json("/x")
        except RuntimeError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("expected a RuntimeError after the retries are exhausted")


def test_unrecorded_stats_do_not_break_totals():
    # The provider sends {"all": null} for a statistic it did not record.
    stats = {"overview": {"corner_kicks": {"all": None}, "fouls": {"all": {"home": 8, "away": 10}}, "goalkeeper_saves": None}}
    totals = team_totals(stats)
    assert totals["total_corners"] is None and totals["total_saves"] is None and totals["total_fouls"] == 18


def test_a_failure_stops_the_run_without_draining_the_queue():
    import time
    from unittest import mock

    from src.ingest import sync_thestatsapi_competition as sync

    fetched = []

    def fake_fetch(client, path):
        fetched.append(path)
        if len(fetched) == 1:
            raise RuntimeError("boom")
        time.sleep(0.05)
        return {"data": {}}

    api = {"id": "mt_1", "status": "finished", "home_team": {"name": "Arsenal"}, "away_team": {"name": "Inter"}, "utc_date": "2026-09-01T19:00:00Z"}
    conn = _squad_db()
    conn.execute("UPDATE matches SET match_date = '2026-09-01'")
    client = mock.Mock()
    client.get_json.return_value = {"data": [{"id": "s1", "start_year": 2026, "end_year": 2027}]}
    with mock.patch.object(sync, "fetch_all_matches", return_value=[api]), mock.patch.object(sync, "_fetch", fake_fetch), \
         mock.patch.object(sync, "MATCH_ENDPOINTS", {f"k{i}": f"/e{i}" for i in range(200)}):
        try:
            sync.sync_matches(client, conn, "champions_league", 2, "2026_27", False, None)
        except RuntimeError as exc:
            assert "boom" in str(exc)
        else:
            raise AssertionError("expected the failure to propagate")
    assert len(fetched) < 50  # 200 were queued; the rest must have been cancelled


def test_odds_are_skipped_before_the_2024_25_season_unless_requested():
    from src.ingest.sync_thestatsapi_competition import fetches_odds

    assert fetches_odds("2024_25") and fetches_odds("2025_26") and fetches_odds("2026_27")
    assert not fetches_odds("2023_24") and not fetches_odds("2020_21")
    assert fetches_odds("2023_24", include_odds=True)
