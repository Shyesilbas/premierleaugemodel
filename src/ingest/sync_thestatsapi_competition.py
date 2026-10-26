"""Sync TheStatsAPI match data for UEFA competitions into SQLite.

Usage:
    THESTATSAPI_API_KEY=... python3 -m src.ingest.sync_thestatsapi_competition \
        --competition champions_league --season 2026_27

For every finished match it can map to a local fixture it stores the raw payloads (team stats, lineups,
player stats, timeline), writes xG and odds into their existing tables and copies headline team
totals onto the ``matches`` row. It also stores the season standings and each club's squad. The API key is
read from the environment only. Runs are resumable: stored payloads are skipped unless --refresh is given.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sqlite3
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.config import DB_PATH
from src.ingest.raw_store import competition_payload_path, match_payload_path, write_json
from src.db.database import ensure_external_payload_tables, ensure_external_xg_table, get_db, init_db
from src.ingest.import_thestatsapi_odds import store_bookmaker_odds
from src.ingest.import_thestatsapi_xg import API_BASE, PROVIDER, TheStatsApiClient, fetch_all_matches

FETCH_WORKERS = 6
# Bookmaker odds are only collected for seasons starting in this year or later (a project decision: they cost one
# request per match and feed nothing for older seasons). --include-odds overrides it.
ODDS_FIRST_SEASON_START_YEAR = 2024
REQUEST_TIMEOUT = 20  # seconds; a normal response takes under one
MAX_RETRIES = 3
STATSAPI_COMPETITIONS = {"champions_league": "comp_3498", "europa_league": "comp_7739"}
MATCH_ENDPOINTS = {
    "stats": "/stats",
    "lineups": "/lineups",
    "player_stats": "/player-stats",
    "timeline": "/timeline",
    "odds": "/odds",
}
CLUB_ALIASES = {
    "manutd": "manchesterunited", "mancity": "manchestercity", "atleti": "atleticomadrid",
    "paris": "parissaintgermain", "sbratislava": "slovanbratislava", "bayernmunchen": "bayernmunich",
    "spurs": "tottenhamhotspur", "bdortmund": "borussiadortmund",
    "nottmforest": "nottinghamforest", "rennes": "staderennais", "hbeersheva": "hapoelbeersheva",
    "copenhagen": "kobenhavn", "mtelaviv": "maccabitelaviv", "unionsg": "royaleunionsaintgilloise", "inter": "internazionale", "intermilano": "internazionale",
}
CLUB_NOISE = re.compile(r"\b(fc|cf|sk|fk|ac|as|sc|afc|bk|ssc|rb|sl|nk|ks|vfb|vfl|tsg|sv|us|ud|rc|ca|club|gnk|aik|aif|kv|cd)\b")


# Letters Unicode decomposition cannot reduce to ASCII (it only strips combining accents).
_TRANSLITERATION = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ß": "ss", "ł": "l", "Ł": "L",
                                  "đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th", "ı": "i"})


def fold_text(text: str) -> str:
    """Lower-case ASCII form of a name: 'København' -> 'kobenhavn', 'Ødegaard' -> 'odegaard'."""
    return unicodedata.normalize("NFKD", (text or "").translate(_TRANSLITERATION)).encode("ascii", "ignore").decode().casefold()


def normalize_club(name: str) -> str:
    value = fold_text(name)
    value = re.sub(r"[^a-z0-9]+", "", CLUB_NOISE.sub(" ", value))
    return CLUB_ALIASES.get(value, value)


def club_similarity(a: str, b: str) -> float:
    left, right = normalize_club(a), normalize_club(b)
    if left == right:
        return 1.0
    if min(len(left), len(right)) >= 3 and (left in right or right in left):
        return 0.95
    return difflib.SequenceMatcher(None, left, right).ratio()


def _parse_date(value: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def map_fixtures(api_matches: List[Dict[str, Any]], local_rows: List[Dict[str, Any]], minimum: float = 1.7) -> Tuple[List[Tuple[Dict[str, Any], Dict[str, Any]]], List[Dict[str, Any]]]:
    """Pair provider fixtures with local rows by club names; dates (+-1 day) break ties between two legs."""
    used: set = set()
    pairs, unmapped = [], []
    for api in api_matches:
        api_day = _parse_date(api.get("utc_date"))
        best_score, best = 0.0, None
        for local in local_rows:
            if local["match_id"] in used:
                continue
            score = club_similarity(api["home_team"]["name"], local["home_name"]) + club_similarity(api["away_team"]["name"], local["away_name"])
            local_day = _parse_date(local.get("match_date"))
            if api_day and local_day and abs((api_day - local_day).days) > 1:
                continue
            if score > best_score:
                best_score, best = score, local
        if best is not None and best_score >= minimum:
            used.add(best["match_id"])
            pairs.append((api, best))
        else:
            unmapped.append(api)
    return pairs, unmapped


def _pair(group: Dict[str, Any], key: str) -> Tuple[Optional[float], Optional[float]]:
    value = (group or {}).get(key) or {}
    value = value.get("all", value) if isinstance(value, dict) and "all" in value else value
    if not isinstance(value, dict):  # the provider sends {"all": null} when a stat was not recorded
        return None, None
    return value.get("home"), value.get("away")


def team_totals(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Headline totals in the shape of the legacy ``matches`` columns."""
    overview, shots, attack, passes = (stats.get(k) or {} for k in ("overview", "shots", "attack", "passes"))
    corners, fouls = _pair(overview, "corner_kicks"), _pair(overview, "fouls")
    yellow, red = _pair(overview, "yellow_cards"), _pair(overview, "red_cards")
    throws, xg = _pair(passes, "throw_ins"), _pair(overview, "expected_goals")

    def total(pair: Tuple[Optional[float], Optional[float]]) -> Optional[float]:
        return None if pair[0] is None or pair[1] is None else pair[0] + pair[1]

    return {
        "home_won_corners": corners[0], "away_won_corners": corners[1], "total_corners": total(corners),
        "home_total_throws": throws[0], "away_total_throws": throws[1], "total_throws": total(throws),
        "total_shots": total(_pair(overview, "total_shots")),
        "total_shots_ontarget": total(_pair(overview, "shots_on_target")),
        "total_saves": total(_pair(overview, "goalkeeper_saves")),
        "home_total_yel_card": yellow[0], "away_total_yel_card": yellow[1], "total_yellow_cards": total(yellow),
        "home_total_red_card": red[0], "away_total_red_card": red[1], "total_red_cards": total(red),
        "total_cards": None if total(yellow) is None or total(red) is None else total(yellow) + total(red),
        "total_fouls": total(fouls),
        "home_xg": xg[0], "away_xg": xg[1], "total_xg": total(xg),
    }


class PacedClient(TheStatsApiClient):
    """Thread-safe client that spaces request *starts* by ``minimum_interval``.

    The base client sleeps relative to when the previous response finished and is strictly serial, so with
    ~0.4 s of latency per call it only reached about half of the 100 requests/minute the API allows. Here
    several requests can be in flight at once while their start times still respect the limit; a 429 pauses
    every thread until the server's Retry-After has passed."""

    def __init__(self, api_key: str, minimum_interval: float) -> None:
        super().__init__(api_key, minimum_interval)
        self._lock = threading.Lock()
        self._next_start = 0.0

    def _reserve_slot(self) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_start)
            self._next_start = start + self.minimum_interval
        if start > now:
            time.sleep(start - now)

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{API_BASE}{path}" + (f"?{urlencode(params)}" if params else "")
        failures = 0
        while True:
            self._reserve_slot()
            request = Request(url, headers={"Authorization": f"Bearer {self.api_key}"})
            try:
                with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                    return json.loads(response.read())
            except HTTPError as exc:
                if exc.code == 429:
                    delay = int(exc.headers.get("Retry-After", "30")) + 1
                    with self._lock:  # everyone waits, not just this thread
                        self._next_start = max(self._next_start, time.monotonic() + delay)
                    print(f"Rate limit hit; pausing {delay}s.", flush=True)
                    continue
                if exc.code >= 500 and failures < MAX_RETRIES:
                    failures += 1
                    continue
                raise RuntimeError(f"TheStatsAPI returned HTTP {exc.code} for {path}") from exc
            except (URLError, TimeoutError, OSError, ValueError) as exc:  # stalled or dropped connection, truncated body
                failures += 1
                if failures > MAX_RETRIES:
                    raise RuntimeError(f"TheStatsAPI request failed for {path}: {exc}") from exc
                print(f"Retry {failures}/{MAX_RETRIES} for {path}: {exc}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fetch(client: TheStatsApiClient, path: str) -> Optional[Dict[str, Any]]:
    """GET a payload; a 404/409 means the provider has nothing (yet) and yields None."""
    try:
        return client.get_json(path)
    except RuntimeError as exc:
        if "HTTP 404" in str(exc) or "HTTP 409" in str(exc):
            return None
        raise


def fetches_odds(season: str, include_odds: bool = False) -> bool:
    """Odds are skipped for seasons before 2024/25 unless explicitly requested."""
    return include_odds or int(season.split("_")[0]) >= ODDS_FIRST_SEASON_START_YEAR


def sync_matches(client: TheStatsApiClient, conn: sqlite3.Connection, comp_key: str, comp_id: int, season: str, refresh: bool, limit: Optional[int], include_odds: bool = False) -> Dict[str, int]:
    provider_comp = STATSAPI_COMPETITIONS[comp_key]
    seasons = client.get_json(f"/football/competitions/{provider_comp}/seasons").get("data", [])
    target = next((s for s in seasons if f"{s.get('start_year')}_{int(s.get('end_year') or 0) % 100:02d}" == season), None)
    if target is None:
        raise RuntimeError(f"Season {season} not offered by TheStatsAPI for {provider_comp}")

    api_matches = [m for m in fetch_all_matches(client, provider_comp, target["id"]) if m.get("stage_name") != "qualifying"]
    local = [dict(r) for r in conn.execute("SELECT * FROM matches WHERE competition_id = ? AND season = ?", (comp_id, season))]
    first_day = min((d for d in (_parse_date(r.get("match_date")) for r in local) if d), default=None)
    if first_day:  # the provider also lists qualifying play-offs played before the league phase
        api_matches = [m for m in api_matches if (_parse_date(m.get("utc_date")) or first_day) >= first_day - timedelta(days=1)]
    pairs, unmapped = map_fixtures(api_matches, local)
    counts = {"listed": len(api_matches), "mapped": len(pairs), "unmapped": len(unmapped), "payloads": 0, "unavailable": 0, "skipped_existing": 0}
    for api in unmapped:
        print(f"Unmapped: {api['home_team']['name']} v {api['away_team']['name']} ({str(api.get('utc_date'))[:10]})", flush=True)

    wanted = []  # (api match, local row, [kinds still to fetch])
    for api, row in pairs:
        if api.get("status") != "finished":
            continue
        have = {r[0] for r in conn.execute("SELECT kind FROM external_match_payloads WHERE match_id = ? AND provider = ?", (row["match_id"], PROVIDER))}
        kinds = []
        for kind in MATCH_ENDPOINTS:
            if kind == "odds" and not fetches_odds(season, include_odds):
                continue
            if kind in have and not refresh:
                counts["skipped_existing"] += 1
            elif (kind == "odds" and api.get("odds_available") is False):
                continue
            else:
                kinds.append(kind)
        if kinds:
            wanted.append((api, row, kinds))
    if limit is not None:
        wanted = wanted[:limit]

    # Fetch concurrently (the client keeps request starts within the rate limit), write from this thread only.
    remaining = {row["match_id"]: len(kinds) for _, row, kinds in wanted}
    done = 0
    pool = ThreadPoolExecutor(max_workers=FETCH_WORKERS)
    try:
        futures = {
            pool.submit(_fetch, client, f"/football/matches/{api['id']}{MATCH_ENDPOINTS[kind]}"): (api, row, kind)
            for api, row, kinds in wanted for kind in kinds
        }
        for future in as_completed(futures):
            api, row, kind = futures[future]
            payload = future.result()
            stored = payload if payload is not None else {"unavailable": True}
            write_json(match_payload_path(comp_key, PROVIDER, row["match_id"], kind), stored)
            conn.execute(
                "INSERT OR REPLACE INTO external_match_payloads (match_id, provider, kind, provider_match_id, payload, fetched_at_utc) VALUES (?,?,?,?,?,?)",
                (row["match_id"], PROVIDER, kind, api["id"], json.dumps(stored, ensure_ascii=False), _now()),
            )
            counts["payloads" if payload is not None else "unavailable"] += 1
            if payload is not None and kind == "stats":
                try:
                    _apply_stats(conn, row["match_id"], api, target["id"], payload.get("data") or {})
                except (AttributeError, TypeError, ValueError) as exc:
                    print(f"Could not derive totals for {row['home_name']} v {row['away_name']}: {exc}", flush=True)
            elif payload is not None and kind == "odds":
                store_bookmaker_odds(conn, row["match_id"], api["id"], target["id"], (payload.get("data") or {}).get("bookmakers") or [], _now())
            conn.commit()
            remaining[row["match_id"]] -= 1
            if remaining[row["match_id"]] == 0:
                done += 1
                print(f"[{done}/{len(wanted)}] {row['home_name']} v {row['away_name']} stored", flush=True)
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)  # do not keep spending requests after a failure
        raise
    else:
        pool.shutdown()
    return counts


def _apply_stats(conn: sqlite3.Connection, match_id: int, api: Dict[str, Any], season_id: str, stats: Dict[str, Any]) -> None:
    totals = {k: v for k, v in team_totals(stats).items() if v is not None}
    if totals:
        assignments = ", ".join(f"{col} = ?" for col in totals)
        conn.execute(f"UPDATE matches SET {assignments} WHERE match_id = ?", (*totals.values(), match_id))
    if totals.get("home_xg") is not None and totals.get("away_xg") is not None:
        conn.execute(
            "INSERT OR REPLACE INTO external_match_xg (match_id, provider, provider_match_id, provider_season_id, home_xg, away_xg, xg_quality, fetched_at_utc) VALUES (?,?,?,?,?,?,?,?)",
            (match_id, PROVIDER, api["id"], season_id, totals["home_xg"], totals["away_xg"], api.get("xg_quality"), _now()),
        )


def sync_competition_level(client: TheStatsApiClient, conn: sqlite3.Connection, comp_key: str, comp_id: int, season: str, season_id: str, refresh: bool) -> Dict[str, int]:
    """Season standings plus the squad of every club that appears in the local fixtures."""
    provider_comp = STATSAPI_COMPETITIONS[comp_key]
    counts = {"standings": 0, "squads": 0, "team_stats": 0, "managers": 0}

    def store(kind: str, ref: str, payload: Dict[str, Any]) -> None:
        write_json(competition_payload_path(comp_key, PROVIDER, season, kind, ref), payload)
        conn.execute(
            "INSERT OR REPLACE INTO external_competition_payloads (competition_id, season, provider, kind, ref, payload, fetched_at_utc) VALUES (?,?,?,?,?,?,?)",
            (comp_id, season, PROVIDER, kind, ref, json.dumps(payload, ensure_ascii=False), _now()),
        )

    standings = _fetch(client, f"/football/competitions/{provider_comp}/seasons/{season_id}/standings")
    if standings is not None:
        store("standings", "", standings)
        counts["standings"] = 1

    teams: Dict[str, str] = {}
    managers: Dict[str, Dict[str, str]] = {}
    listing = [m for m in fetch_all_matches(client, provider_comp, season_id) if m.get("stage_name") != "qualifying"]
    for api in sorted(listing, key=lambda m: str(m.get("utc_date"))):  # the latest fixture wins, i.e. the current manager
        for side in ("home", "away"):
            team = api[f"{side}_team"]
            teams[team["id"]] = team["name"]
            manager = api.get(f"{side}_manager") or {}
            if manager.get("name"):
                managers[team["id"]] = {"name": manager["name"], "team": team["name"]}
    store("managers", "", {"managers": managers})
    counts["managers"] = len(managers)
    have = {r[0] for r in conn.execute("SELECT ref FROM external_competition_payloads WHERE competition_id = ? AND season = ? AND provider = ? AND kind = 'squad'", (comp_id, season, PROVIDER))}
    for team_id, name in teams.items():
        if team_id in have and not refresh:
            continue
        squad = _fetch(client, f"/football/teams/{team_id}/players")
        if squad is not None:
            store("squad", team_id, {"team": {"id": team_id, "name": name}, **squad})
            counts["squads"] += 1
    have_stats = {r[0] for r in conn.execute("SELECT ref FROM external_competition_payloads WHERE competition_id = ? AND season = ? AND provider = ? AND kind = 'team_stats'", (comp_id, season, PROVIDER))}
    for team_id, name in teams.items():
        if team_id in have_stats and not refresh:
            continue
        team_stats = _fetch(client, f"/football/teams/{team_id}/stats?season_id={season_id}")
        if team_stats is not None:
            store("team_stats", team_id, {"team": {"id": team_id, "name": name}, **team_stats})
            counts["team_stats"] += 1
    conn.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, choices=sorted(STATSAPI_COMPETITIONS))
    parser.add_argument("--season", default="2026_27")
    parser.add_argument("--refresh", action="store_true", help="re-fetch payloads that are already stored")
    parser.add_argument("--limit", type=int, default=None, help="stop after this many matches (for trials)")
    parser.add_argument("--include-odds", action="store_true", help="also fetch odds for seasons before 2024/25 (skipped by default)")
    parser.add_argument("--skip-competition-data", action="store_true", help="skip standings and squads")
    parser.add_argument("--minimum-interval", type=float, default=0.65, help="seconds between requests (API limit: 100/min)")
    args = parser.parse_args()

    api_key = os.environ.get("THESTATSAPI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set THESTATSAPI_API_KEY in the process environment; it is never read from or written to a file.")

    init_db()
    conn = get_db(DB_PATH)
    ensure_external_xg_table(conn)
    ensure_external_payload_tables(conn)
    from src.competitions.registry import get_competition
    comp = get_competition(args.competition)
    client = PacedClient(api_key, args.minimum_interval)

    print(sync_matches(client, conn, args.competition, comp.id, args.season, args.refresh, args.limit, args.include_odds), flush=True)
    if not args.skip_competition_data:
        provider_comp = STATSAPI_COMPETITIONS[args.competition]
        seasons = client.get_json(f"/football/competitions/{provider_comp}/seasons").get("data", [])
        target = next(s for s in seasons if f"{s.get('start_year')}_{int(s.get('end_year') or 0) % 100:02d}" == args.season)
        print(sync_competition_level(client, conn, args.competition, comp.id, args.season, target["id"], args.refresh), flush=True)
    conn.close()


if __name__ == "__main__":
    main()
