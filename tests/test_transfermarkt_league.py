"""Transfermarkt values for a national league: page parsing, club matching and the shared tables."""

import json
import sqlite3

import pytest

from src.db.database import ensure_market_value_tables
from src.ingest.fetch_transfermarkt_league import history_record, load, match_clubs, parse_clubs, parse_money, parse_squad

OVERVIEW = (
    '<tr class="odd"><td><a title="Real Madrid" href="/real-madrid/kader/verein/418/saison_id/2022">36</a></td>'
    '<td class="zentriert">27.4</td><td class="rechts">€25.65m</td><td class="rechts">'
    '<a title="Real Madrid" href="/real-madrid/startseite/verein/418/saison_id/2022">€923.45m</a></td></tr>'
    '<tr class="even"><td><a title="RCD Espanyol Barcelona" href="/x/kader/verein/714/saison_id/2022">34</a></td>'
    '<td class="rechts">€3.43m</td><td class="rechts"><a title="RCD Espanyol Barcelona" href="/x">€116.50m</a></td></tr>'
    '<tr class="odd"><td><a title="FC Barcelona" href="/x/kader/verein/131/saison_id/2022">41</a></td>'
    '<td class="rechts">€20.41m</td><td class="rechts"><a title="FC Barcelona" href="/x">€1.05bn</a></td></tr>'
)

SQUAD = (
    '<table class="items"><tbody><tr class="odd"><td class="zentriert rueckennummer" title="Goalkeeper"></td><td class="posrela">'
    '<table class="inline-table"><tr><td rowspan="2"></td><td class="hauptlink">'
    '<a href="/thibaut-courtois/profil/spieler/108390">\n  Thibaut Courtois<span class="verletzt-table">&nbsp;</span></a></td></tr>'
    '<tr><td>\n  Goalkeeper  </td></tr></table></td><td class="zentriert">11/05/1992 (31)</td>'
    '<td class="zentriert"><img src="f.png" title="Belgium" alt="Belgium" class="flaggenrahmen" /></td>'
    '<td class="rechts hauptlink"><a href="/thibaut-courtois/marktwertverlauf/spieler/108390">€45.00m</a></td></tr>'
    '<tr class="even"><td class="posrela"><table class="inline-table"><tr><td class="hauptlink">'
    '<a href="/x/profil/spieler/926850">Diego Pi&ntilde;eiro</a></td></tr><tr><td>Goalkeeper</td></tr></table></td>'
    '<td class="zentriert">13/02/2004 (19)</td><td class="rechts hauptlink"><a href="/x/marktwertverlauf/spieler/926850">-</a></td></tr>'
    '</tbody></table>'
)


def test_money_strings_become_euros():
    assert parse_money("€45.00m") == 45_000_000
    assert parse_money("€1.05bn") == 1_050_000_000
    assert parse_money("€500k") == 500_000
    assert parse_money("-") is None and parse_money("") is None


def test_overview_page_gives_every_club_of_that_season():
    clubs = parse_clubs(OVERVIEW, 2022)
    assert [c["tm_club_id"] for c in clubs] == [418, 714, 131]
    assert clubs[0] == {"tm_club_id": 418, "tm_name": "Real Madrid", "squad_size": 36,
                        "avg_market_value": 25_650_000, "market_value": 923_450_000}
    assert parse_clubs(OVERVIEW, 2023) == []  # links of another season are not that season's clubs


def test_squad_page_rows_carry_id_position_birth_nationality_and_value():
    courtois, pineiro = parse_squad(SQUAD)
    assert courtois == {"tm_player_id": "108390", "name": "Thibaut Courtois", "position": "Goalkeeper", "birth_date": "1992-05-11",
                        "age": 31, "joined": None, "nationality": "Belgium", "market_value": 45_000_000}
    assert pineiro["name"] == "Diego Piñeiro" and pineiro["market_value"] is None


def test_clubs_match_teams_exactly_first_then_by_unique_subset():
    teams = {1: "Real Madrid", 2: "Espanyol", 3: "Barcelona"}
    assert match_clubs(parse_clubs(OVERVIEW, 2022), teams) == {418: 1, 131: 3, 714: 2}
    assert match_clubs(parse_clubs(OVERVIEW, 2022), {9: "Getafe"}) == {}  # no match is left out, never guessed


def test_value_graph_becomes_dated_history():
    graph = {"current": "€15.00m", "list": [
        {"y": 45000000, "datum_mw": "13/06/2023", "verein": "Real Madrid", "age": "31", "wappen": "https://img/wappen/profil/418.png?lm=1"},
        {"y": 35000000, "datum_mw": "22/12/2023", "verein": "Real Madrid", "age": "31", "wappen": ""},
    ]}
    record = history_record("108390", graph)
    assert record["marketValue"] == 15_000_000
    assert record["marketValueHistory"][0] == {"date": "2023-06-13", "marketValue": 45000000, "clubName": "Real Madrid", "clubId": "418", "age": 31}
    assert record["marketValueHistory"][1]["date"] == "2023-12-22"


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    ensure_market_value_tables(connection)
    yield connection
    connection.close()


def test_load_writes_league_rows_and_leaves_another_competitions_player_alone(conn):
    conn.execute("INSERT INTO player_market_values (player_id, team_id, name, market_value, market_value_eur, season, updated_at) "
                 "VALUES ('926850', 7, 'Diego Pineiro', 1000000, 1.0, '2022_23', 'x')")  # a Premier League row (default id 39)
    squad = parse_squad(SQUAD)
    squad[1]["market_value"] = 2_000_000
    parsed = {"2022_23": {"clubs": parse_clubs(OVERVIEW, 2022)[:1], "mapping": {418: 10073673}, "squads": {418: squad}}}
    counts = load(conn, 140, {"2022_23": {10073673: "Real Madrid"}}, parsed, {"108390": {"list": []}}, {"108390": "Thibaut Courtois"})
    assert counts["teams"] == 1 and counts["players"] == 1 and counts["players_held_by_other_competition"] == 1
    assert conn.execute("SELECT team_id, name, market_value_eur, competition_id FROM team_market_values").fetchall() == [
        (10073673, "Real Madrid", 923.45, 140)]
    assert conn.execute("SELECT team_id, competition_id FROM player_market_values WHERE player_id = '926850'").fetchone() == (7, 39)
    assert conn.execute("SELECT competition_id FROM player_market_values WHERE player_id = '108390'").fetchone() == (140,)
    cached = json.loads(conn.execute("SELECT data_json FROM player_market_value_history_cache WHERE tm_id = '108390'").fetchone()[0])
    assert cached["marketValueHistory"] == []


def test_older_tables_get_the_competition_column():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE player_market_values (player_id TEXT, team_id INTEGER, name TEXT, position TEXT, market_value INTEGER, "
                       "market_value_eur REAL, age INTEGER, nationality TEXT, season TEXT, updated_at TEXT, PRIMARY KEY (player_id, season))")
    connection.execute("INSERT INTO player_market_values (player_id, team_id, name, market_value, market_value_eur, season, updated_at) "
                       "VALUES ('1', 1, 'A', 1, 1.0, '2024_25', 'x')")
    ensure_market_value_tables(connection)
    assert connection.execute("SELECT competition_id FROM player_market_values").fetchone() == (39,)
