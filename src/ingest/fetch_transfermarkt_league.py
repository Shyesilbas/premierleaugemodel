"""Download Transfermarkt squad and player market values of a league, season by season, and load them.

Usage:
  python3 -m src.ingest.fetch_transfermarkt_league --competition <league_key> [--seasons 2023_24 2024_25]
      [--skip-history] [--offline] [--download-only]

What it does, for every season the database holds for the competition:
  1. the league overview page: each club's squad size, total and average market value;
  2. each club's squad page of that season: players with position, age, nationality and market value;
  3. each player's dated market value history (every valuation with its date), once per player.

The value on a past season's pages is the valuation at the end of that season (checked: Courtois 2022/23 shows the
13/06/2023 value), so it already knows the season it describes. A pre-match feature must instead take the latest
dated valuation before kick-off, from step 3 (``player_market_value_history_cache``).

Clubs are matched to the competition's teams by name, season by season; a club without a unique match stops the run
instead of being guessed.

Reads:  the competition's teams per season from ``matches`` (data/football.db) and www.transfermarkt.com.
Writes: raw pages and history JSON under ``data/competitions/<key>/raw/transfermarkt/``
        (``competition/<season>_clubs.html``, ``competition/<season>_squad_<tm club id>.html``,
        ``players/<tm player id>_market_value.json``, ``squads.json``, ``club_mapping.json``) and the tables ``team_market_values``, ``player_market_values``
        (both with ``competition_id``) and ``player_market_value_history_cache``.
        Files that already exist are not fetched again, so a run can be repeated or resumed; --offline only loads them.
Needs:  no key. Requests are spaced (about 2.5 s) because the site blocks fast clients; a full league of five seasons
        is about 100 pages plus one history request per player (roughly an hour).
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.db.database import ensure_market_value_tables, get_db
from src.ingest.raw_store import provider_dir, write_json

logger = logging.getLogger("fetch_transfermarkt_league")

PROVIDER = "transfermarkt"
BASE = "https://www.transfermarkt.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_INTERVAL = 2.5
# Words that only mark the club form ("FC", "CF", "de"), dropped before two names are compared.
NAME_NOISE = {"fc", "cf", "ud", "cd", "rcd", "ca", "sd", "rc", "sad", "club", "de", "del", "la", "balompie"}

CLUB_ROW = re.compile(
    r'/kader/verein/(\d+)/saison_id/(\d{4})"[^>]*>(\d+)</a>.*?<td class="rechts">([^<]*)</td>'
    r'<td class="rechts"><a title="([^"]+)"[^>]*>([^<]*)</a>',
    re.DOTALL,
)


def fold(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()).strip()


def name_tokens(name: str) -> frozenset:
    return frozenset(token for token in fold(name).split() if token not in NAME_NOISE)


def parse_money(text: str) -> Optional[int]:
    """'€45.00m' / '€1.05bn' / '€500k' -> euros; '-' or empty -> None."""
    found = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(bn|m|k|Th\.)", html.unescape(text or ""))
    if not found:
        return None
    value = float(found.group(1).replace(",", "."))
    return int(round(value * {"bn": 1e9, "m": 1e6, "k": 1e3, "Th.": 1e3}[found.group(2)]))


def parse_clubs(page: str, start_year: int) -> List[Dict[str, Any]]:
    """Clubs of one season from the league overview page."""
    clubs = []
    for tm_id, year, squad, average, title, total in CLUB_ROW.findall(page):
        if int(year) != start_year:
            continue
        clubs.append({"tm_club_id": int(tm_id), "tm_name": html.unescape(title), "squad_size": int(squad),
                      "avg_market_value": parse_money(average), "market_value": parse_money(total)})
    return list({club["tm_club_id"]: club for club in clubs}.values())


def parse_squad(page: str) -> List[Dict[str, Any]]:
    """Players of one club-season from the squad page (detailed view, ``/plus/1``)."""
    start = page.find('class="items"')
    if start < 0:
        return []
    players = []
    for row in re.split(r'<tr class="(?:odd|even)">', page[start:])[1:]:
        player = re.search(r'/profil/spieler/(\d+)">\s*([^<]+?)\s*<', row)
        if not player:
            continue
        position = re.search(r"<tr>\s*<td>\s*([^<]+?)\s*</td>\s*</tr>", row)
        birth = re.search(r'<td class="zentriert">(\d\d)/(\d\d)/(\d{4}) \((\d+)\)</td>', row)
        joined = re.search(r'<td class="zentriert">(\d\d)/(\d\d)/(\d{4})</td>', row)  # first plain date: joined the club
        value = re.search(r'marktwertverlauf/spieler/\d+">([^<]*)</a>', row)
        players.append({
            "tm_player_id": player.group(1),
            "name": html.unescape(player.group(2)),
            "position": html.unescape(position.group(1)) if position else None,
            "birth_date": f"{birth.group(3)}-{birth.group(2)}-{birth.group(1)}" if birth else None,
            "age": int(birth.group(4)) if birth else None,
            "joined": f"{joined.group(3)}-{joined.group(2)}-{joined.group(1)}" if joined else None,
            "nationality": ", ".join(html.unescape(n) for n in re.findall(r'title="([^"]+)" alt="[^"]*" class="flaggenrahmen"', row)),
            "market_value": parse_money(value.group(1)) if value else None,
        })
    return list({p["tm_player_id"]: p for p in players}.values())


def history_record(tm_player_id: str, graph: Dict[str, Any]) -> Dict[str, Any]:
    """The site's value graph in the shape the player page reads (``marketValueHistory`` with ISO dates)."""
    points = []
    for point in graph.get("list") or []:
        day, month, year = str(point.get("datum_mw", "")).split("/") if point.get("datum_mw") else ("", "", "")
        club = re.search(r"/wappen/\w+/(\d+)", point.get("wappen") or "")
        points.append({"date": f"{year}-{month}-{day}" if year else None, "marketValue": point.get("y"),
                       "clubName": point.get("verein"), "clubId": club.group(1) if club else None,
                       "age": int(point["age"]) if str(point.get("age", "")).isdigit() else None})
    points = [p for p in points if p["date"] and p["marketValue"] is not None]
    return {"id": str(tm_player_id), "marketValue": parse_money(graph.get("current") or ""), "marketValueHistory": points,
            "source": "transfermarkt.com marketValueDevelopment"}


def match_clubs(clubs: List[Dict[str, Any]], teams: Dict[int, str]) -> Dict[int, int]:
    """Transfermarkt club id -> local team id. Same words after dropping club-form words first; then, among the teams
    still free, a unique subset match ("RCD Espanyol Barcelona" -> Espanyol once Barcelona is taken)."""
    tokens = {team_id: name_tokens(name) for team_id, name in teams.items()}
    mapping: Dict[int, int] = {}
    for exact in (True, False):
        for club in clubs:
            if club["tm_club_id"] in mapping:
                continue
            club_tokens = name_tokens(club["tm_name"])
            free = {t: words for t, words in tokens.items() if t not in mapping.values() and words}
            pick = [t for t, words in free.items()
                    if (words == club_tokens if exact else (words <= club_tokens or club_tokens <= words))]
            if len(pick) == 1:
                mapping[club["tm_club_id"]] = pick[0]
    if len(set(mapping.values())) != len(mapping):
        raise ValueError(f"two Transfermarkt clubs matched one team: {mapping}")
    return mapping


class Client:
    """Spaced requests with a browser user agent; the site answers fast clients with 403 or 429."""

    def __init__(self, interval: float = REQUEST_INTERVAL):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
        self.interval = interval
        self.last = 0.0
        self.requests = 0

    def get(self, url: str, as_json: bool = False) -> Any:
        for attempt in range(5):
            wait = self.interval - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.requests += 1
            try:
                response = self.session.get(url, timeout=40, headers={"Accept": "application/json"} if as_json else None)
            except requests.RequestException as exc:
                logger.warning("%s: %s (attempt %d)", url, exc, attempt + 1)
                time.sleep(10 * (attempt + 1))
                continue
            if response.status_code == 200:
                return response.json() if as_json else response.text
            if response.status_code == 404:
                return None
            logger.warning("%s: HTTP %d (attempt %d)", url, response.status_code, attempt + 1)
            time.sleep(30 * (attempt + 1))
        raise RuntimeError(f"Transfermarkt did not answer {url}; stopping so nothing half-fetched is loaded")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def cached_page(client: Optional[Client], path: Path, url: str) -> Optional[str]:
    if path.exists():
        return path.read_text(encoding="utf-8")
    if client is None:
        return None
    page = client.get(url)
    if page:
        write_text(path, page)
    return page


def competition_seasons(conn: sqlite3.Connection, competition_id: int) -> List[str]:
    rows = conn.execute("SELECT DISTINCT season FROM matches WHERE competition_id = ? ORDER BY season", (competition_id,))
    return [row[0] for row in rows]


def season_teams(conn: sqlite3.Connection, competition_id: int, season: str) -> Dict[int, str]:
    rows = conn.execute(
        "SELECT home_id, home_name FROM matches WHERE competition_id = ? AND season = ? "
        "UNION SELECT away_id, away_name FROM matches WHERE competition_id = ? AND season = ?",
        (competition_id, season, competition_id, season),
    )
    return {int(team_id): name for team_id, name in rows}


def fetch_season(client: Optional[Client], raw: Path, code: str, season: str, teams: Dict[int, str]) -> Dict[str, Any]:
    """Overview and squad pages of one season (fetched or read from disk), parsed and matched to the local teams."""
    start_year = int(season[:4])
    overview = cached_page(client, raw / "competition" / f"{season}_clubs.html",
                           f"{BASE}/league/startseite/wettbewerb/{code}/plus/?saison_id={start_year}")
    if not overview:
        raise RuntimeError(f"{season}: no league overview page (run without --offline)")
    clubs = parse_clubs(overview, start_year)
    mapping = match_clubs(clubs, teams)
    unmatched_teams = sorted(name for team_id, name in teams.items() if team_id not in mapping.values())
    if unmatched_teams:
        raise ValueError(f"{season}: no unique Transfermarkt club for {unmatched_teams}; "
                         f"clubs on the page: {sorted(c['tm_name'] for c in clubs)}")
    squads = {}
    for club in clubs:
        if club["tm_club_id"] not in mapping:
            continue
        page = cached_page(client, raw / "competition" / f"{season}_squad_{club['tm_club_id']}.html",
                           f"{BASE}/club/kader/verein/{club['tm_club_id']}/saison_id/{start_year}/plus/1")
        squads[club["tm_club_id"]] = parse_squad(page or "")
        if not squads[club["tm_club_id"]]:
            logger.warning("%s %s: squad page has no players", season, club["tm_name"])
    return {"clubs": clubs, "mapping": mapping, "squads": squads}


def stored_history(raw: Path, player_id: str) -> Optional[Path]:
    """A player's value graph already downloaded for this or another competition (a player moves between leagues)."""
    name = f"{player_id}_market_value.json"
    own = raw / "players" / name
    if own.exists():
        return own
    return next(raw.parents[2].glob(f"*/raw/{PROVIDER}/players/{name}"), None)


def fetch_histories(client: Optional[Client], raw: Path, player_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    histories = {}
    for index, player_id in enumerate(player_ids, 1):
        path = stored_history(raw, player_id) or raw / "players" / f"{player_id}_market_value.json"
        if path.exists():
            graph = json.loads(path.read_text(encoding="utf-8"))
        elif client is None:
            continue
        else:
            graph = client.get(f"{BASE}/ceapi/marketValueDevelopment/graph/{player_id}", as_json=True)
            if graph is None:
                continue
            write_json(path, graph)
            if index % 100 == 0:
                logger.info("value histories: %d / %d", index, len(player_ids))
        histories[player_id] = graph
    return histories


def load(conn: sqlite3.Connection, competition_id: int, teams_by_season: Dict[str, Dict[int, str]],
         seasons: Dict[str, Dict[str, Any]], histories: Dict[str, Dict[str, Any]], names: Dict[str, str]) -> Dict[str, int]:
    """Upsert the parsed rows. A player row another competition already holds for the season is left alone."""
    ensure_market_value_tables(conn)
    now = datetime.now(timezone.utc).isoformat()
    counts = {"teams": 0, "players": 0, "players_without_value": 0, "players_held_by_other_competition": 0, "histories": 0}
    for season, parsed in seasons.items():
        for club in parsed["clubs"]:
            team_id = parsed["mapping"].get(club["tm_club_id"])
            if team_id is None or club["market_value"] is None:
                continue
            conn.execute(
                """INSERT INTO team_market_values (team_id, tm_club_id, name, season, market_value, market_value_eur, squad_size,
                       avg_market_value_eur, updated_at, competition_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(team_id, season) DO UPDATE SET tm_club_id = excluded.tm_club_id, name = excluded.name,
                       market_value = excluded.market_value, market_value_eur = excluded.market_value_eur,
                       squad_size = excluded.squad_size, avg_market_value_eur = excluded.avg_market_value_eur,
                       updated_at = excluded.updated_at, competition_id = excluded.competition_id""",
                (team_id, club["tm_club_id"], teams_by_season[season][team_id], season, club["market_value"],
                 round(club["market_value"] / 1e6, 2), club["squad_size"],
                 round((club["avg_market_value"] or 0) / 1e6, 2), now, competition_id),
            )
            counts["teams"] += 1
            for player in parsed["squads"].get(club["tm_club_id"], []):
                if player["market_value"] is None:
                    counts["players_without_value"] += 1
                    continue
                cursor = conn.execute(
                    """INSERT INTO player_market_values (player_id, team_id, name, position, market_value, market_value_eur, age,
                           nationality, season, updated_at, competition_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(player_id, season) DO UPDATE SET team_id = excluded.team_id, name = excluded.name,
                           position = excluded.position, market_value = excluded.market_value,
                           market_value_eur = excluded.market_value_eur, age = excluded.age,
                           nationality = excluded.nationality, updated_at = excluded.updated_at
                       WHERE player_market_values.competition_id = excluded.competition_id""",
                    (player["tm_player_id"], team_id, player["name"], player["position"], player["market_value"],
                     round(player["market_value"] / 1e6, 2), player["age"], player["nationality"], season, now, competition_id),
                )
                counts["players" if cursor.rowcount else "players_held_by_other_competition"] += 1
    for player_id, graph in histories.items():
        conn.execute(
            "INSERT OR REPLACE INTO player_market_value_history_cache (tm_id, player_name, data_json, updated_at) VALUES (?, ?, ?, ?)",
            (player_id, names.get(player_id), json.dumps(history_record(player_id, graph), ensure_ascii=False), now),
        )
        counts["histories"] += 1
    conn.commit()
    return counts


def run(competition_key: str, seasons: Optional[List[str]] = None, skip_history: bool = False, offline: bool = False,
        download_only: bool = False) -> Dict[str, int]:
    comp = get_competition(competition_key)
    if not comp.transfermarkt_code:
        raise SystemExit(f"{comp.key} has no transfermarkt_code in config/competitions.yaml")
    raw = provider_dir(comp.key, PROVIDER)
    client = None if offline else Client()
    conn = get_db()
    try:
        wanted = seasons or competition_seasons(conn, comp.id)
        teams_by_season = {season: season_teams(conn, comp.id, season) for season in wanted}
        parsed = {}
        for season in wanted:
            parsed[season] = fetch_season(client, raw, comp.transfermarkt_code, season, teams_by_season[season])
            logger.info("%s: %d clubs, %d players", season, len(parsed[season]["mapping"]),
                        sum(len(s) for s in parsed[season]["squads"].values()))
        names = {p["tm_player_id"]: p["name"] for season in parsed.values() for squad in season["squads"].values() for p in squad}
        histories = {} if skip_history else fetch_histories(client, raw, sorted(names, key=int))
        mapping = {season: {str(tm): team for tm, team in p["mapping"].items()} for season, p in parsed.items()}
        write_json(raw / "club_mapping.json", {"competition": comp.key, "tm_club_id_to_team_id": mapping})
        write_json(raw / "squads.json", {season: {str(tm): squad for tm, squad in p["squads"].items()} for season, p in parsed.items()})
        if download_only:
            counts = {"teams": 0, "players": 0, "histories_on_disk": len(histories)}
        else:
            counts = load(conn, comp.id, teams_by_season, parsed, histories, names)
    finally:
        conn.close()
    counts["requests"] = client.requests if client else 0
    logger.info("%s Transfermarkt: %s", comp.key, counts)
    return counts


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (needs transfermarkt_code)")
    parser.add_argument("--seasons", nargs="+", help="season labels such as 2023_24; default: every season in the database")
    parser.add_argument("--skip-history", action="store_true", help="skip the per-player dated value histories")
    parser.add_argument("--offline", action="store_true", help="load the files already on disk, no network")
    parser.add_argument("--download-only", action="store_true",
                        help="write the raw files (and squads.json, club_mapping.json) but nothing to the database")
    args = parser.parse_args()
    run(args.competition, args.seasons, args.skip_history, args.offline, args.download_only)


if __name__ == "__main__":
    main()
