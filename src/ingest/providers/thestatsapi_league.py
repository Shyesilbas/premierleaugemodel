"""TheStatsAPI as the fixture source of a national league (LaLiga and any league added the same way).

The feed lists matches with string ids (``mt_733716933``) and teams as ``tm_20116``. The local store has one integer
primary key for matches across all competitions, so provider ids are shifted into ranges no other feed uses:
``match_id = 100_000_000 + number`` and ``team_id = 10_000_000 + number``. The fixture list is read from the raw file
saved by ``fetch_thestatsapi_league`` and is never fetched here.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from src.ingest.base_provider import BaseIngestionProvider
from src.ingest.raw_store import match_payload_path, season_file_path

logger = logging.getLogger("thestatsapi_league")
PROVIDER = "TheStatsAPI"
MATCH_ID_OFFSET = 100_000_000
SCHEDULE_ID_OFFSET = 300_000_000  # placeholder matches taken from the published calendar (see missing_fixtures)
TEAM_ID_OFFSET = 10_000_000
DISPLAY_TZ = ZoneInfo("Europe/London")  # same clock as the Premier League and UEFA labels
LOCAL_TZ = {"la_liga": ZoneInfo("Europe/Madrid")}  # clock of the calendar's kick-off times
SCHEDULE_MIN_SIMILARITY = 0.85

# Three-letter codes for the clubs seen in LaLiga since 2022/23; unknown clubs get a derived code.
ABBREVIATIONS = {
    "almeria": "ALM", "athletic club": "ATH", "atletico madrid": "ATM", "barcelona": "BAR", "cadiz": "CAD",
    "celta vigo": "CEL", "deportivo alaves": "ALA", "deportivo la coruna": "DEP", "elche": "ELC", "espanyol": "ESP",
    "getafe": "GET", "girona": "GIR", "girona fc": "GIR", "granada": "GRA", "las palmas": "LPA", "leganes": "LEG",
    "levante ud": "LEV", "mallorca": "MLL", "malaga": "MAL", "osasuna": "OSA", "racing de santander": "RAC",
    "rayo vallecano": "RAY", "real betis": "BET", "real madrid": "RMA", "real oviedo": "OVI", "real sociedad": "RSO",
    "real valladolid": "VLL", "sevilla": "SEV", "valencia": "VAL", "villarreal": "VIL",
}


def _number(provider_id: str) -> int:
    return int(re.sub(r"\D", "", provider_id))


def local_match_id(provider_id: str) -> int:
    return MATCH_ID_OFFSET + _number(provider_id)


def local_team_id(provider_id: str) -> int:
    return TEAM_ID_OFFSET + _number(provider_id)


def schedule_match_id(season: str, home_team_id: int, away_team_id: int) -> int:
    """Stable id of a calendar placeholder: a pair of clubs meets once at home per season, so the pair identifies the match."""
    return SCHEDULE_ID_OFFSET + zlib.crc32(f"{season}|{home_team_id}|{away_team_id}".encode()) % 90_000_000


def provider_match_id(local_id: int) -> str:
    return f"mt_{int(local_id) - MATCH_ID_OFFSET:09d}"


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower().strip()


def abbreviation(name: str) -> str:
    known = ABBREVIATIONS.get(_fold(name))
    if known:
        return known
    letters = re.sub(r"[^A-Za-z]", "", _fold(name))
    return letters[:3].upper()


def badge_url(competition_key: str, team_id: int) -> Optional[str]:
    """Public path of a club badge downloaded by ``fetch_team_badges``; None until it exists."""
    from src.config import ROOT

    return f"/badges/{competition_key}/{team_id}.png" if (ROOT / "frontend" / "public" / "badges" / competition_key / f"{team_id}.png").exists() else None


def season_label(season_year: str) -> str:
    """'26/27' -> '2026_27'."""
    start, end = season_year.split("/")
    return f"{2000 + int(start)}_{end}"


class TheStatsApiLeagueProvider(BaseIngestionProvider):
    """Reads the saved fixture list and the per-match detail files of one competition."""

    stores_raw_fixtures = False  # the fixture list is itself read from a raw file

    def __init__(self, competition_id: int, competition_key: str) -> None:
        super().__init__(competition_id=competition_id, competition_key=competition_key)
        self._details: Dict[str, Dict[str, Any]] = {}

    def _schedule_placeholders(self, season: str, fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from src.ingest.fetch_openfootball_schedule import schedule_path

        path = schedule_path(self.competition_key, season)
        if not path.exists():
            return []
        return missing_fixtures(season, fixtures, json.loads(path.read_text(encoding="utf-8")), LOCAL_TZ.get(self.competition_key, DISPLAY_TZ))

    def fetch_fixtures(self, season: str) -> List[Dict[str, Any]]:
        path = season_file_path(self.competition_key, PROVIDER, "fixtures", season)
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing; run fetch_thestatsapi_league for {self.competition_key} {season} first")
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        self._details = {}
        for fixture in fixtures:
            detail = match_payload_path(self.competition_key, PROVIDER, local_match_id(fixture["id"]), "match")
            if detail.exists():
                self._details[fixture["id"]] = (json.loads(detail.read_text(encoding="utf-8")).get("data")) or {}
        return fixtures + self._schedule_placeholders(season, fixtures)

    def fetch_standings(self, season: str) -> List[Dict[str, Any]]:
        """The league table is computed from the results; the provider's own table is not stored."""
        return []

    def fetch_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        return self._payload(match_id, "stats")

    def fetch_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        return self._payload(match_id, "lineups")

    def fetch_match_stream(self, match_id: int) -> Optional[Dict[str, Any]]:
        return self._payload(match_id, "timeline")

    def normalize_stats_record(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        return raw_stats

    def _payload(self, match_id: int, kind: str) -> Optional[Dict[str, Any]]:
        path = match_payload_path(self.competition_key, PROVIDER, match_id, kind)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def normalize_fixture_record(self, raw_fixture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Canonical match row; cancelled fixtures are dropped."""
        if raw_fixture.get("status") == "cancelled":
            return None
        kickoff = raw_fixture.get("utc_date") or ""
        local = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).astimezone(DISPLAY_TZ) if kickoff else None
        day_label = local.strftime("%a %d %b %Y") if local else ""
        time_label = "" if raw_fixture.get("_time_unknown") else (local.strftime("%H:%M %Z") if local else "")  # a calendar date without a kick-off time
        score = raw_fixture.get("score") or {}
        regulation = score.get("regulation") or {}
        home_goals = regulation.get("home", score.get("home"))
        away_goals = regulation.get("away", score.get("away"))
        finished = raw_fixture.get("status") == "finished" and home_goals is not None and away_goals is not None
        detail = self._details.get(raw_fixture["id"], {})
        home, away = raw_fixture["home_team"], raw_fixture["away_team"]
        season_year = detail.get("season_year")
        return {
            "match_id": raw_fixture["_local_id"] if raw_fixture.get("_schedule_only") else local_match_id(raw_fixture["id"]),
            "competition_id": self.competition_id,
            "season": raw_fixture.get("_season") or (season_label(season_year) if season_year else ""),
            "gameweek": int(raw_fixture.get("matchday") or 1),
            "stage": "league",
            "match_date": local.date().isoformat() if local else "",
            "kickoff_label": (f"{day_label}, {time_label}" if time_label else day_label) if local else "",
            "day_label": day_label,
            "time_label": time_label,
            "ground_name": ((detail.get("venue") or {}).get("name")) or "",
            "home_id": local_team_id(home["id"]),
            "home_name": home["name"],
            "home_abbr": abbreviation(home["name"]),
            "home_logo": badge_url(self.competition_key, local_team_id(home["id"])),
            "home_score": float(home_goals) if finished else None,
            "away_id": local_team_id(away["id"]),
            "away_name": away["name"],
            "away_abbr": abbreviation(away["name"]),
            "away_logo": badge_url(self.competition_key, local_team_id(away["id"])),
            "away_score": float(away_goals) if finished else None,
            "status": "COMPLETED" if finished else "UPCOMING",
            "referee_name": (detail.get("referee") or {}).get("name"),
            "group_name": None,
            "leg": None,
            "advancing_team_id": None,
            "advance_reason": None,
            "home_penalties": None,
            "away_penalties": None,
        }


def _map_names(schedule_names: List[str], teams: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Calendar club name -> provider club name, one to one (best pairs first, so "Espanyol de Barcelona" cannot take
    "Barcelona"); None unless every calendar club finds its own club."""
    from src.ingest.sync_thestatsapi_competition import club_similarity

    pairs = sorted(((club_similarity(n, t), n, t) for n in schedule_names for t in teams), key=lambda p: (-p[0], p[1], p[2]))
    mapping: Dict[str, str] = {}
    taken = set()
    for similarity, name, team in pairs:
        if name in mapping or team in taken or similarity < SCHEDULE_MIN_SIMILARITY:
            continue
        mapping[name] = team
        taken.add(team)
    missing = [n for n in schedule_names if n not in mapping]
    if missing:
        logger.warning("Calendar clubs without a provider club %s; calendar placeholders skipped", missing)
        return None
    return mapping


def missing_fixtures(season: str, fixtures: List[Dict[str, Any]], schedule: Dict[str, Any], clock: ZoneInfo) -> List[Dict[str, Any]]:
    """Provider-shaped placeholders for every calendar match the provider has not listed (by home/away pair).

    A provider fixture always wins over the calendar, except a cancelled (postponed) one, which stays on the calendar
    until the provider lists a new date. Once the provider publishes a match its placeholder disappears at the next
    sync because its id is no longer listed."""
    teams = {f[side]["name"]: f[side]["id"] for f in fixtures for side in ("home_team", "away_team")}
    matches = schedule.get("matches") or []
    mapping = _map_names(sorted({m[s] for m in matches for s in ("team1", "team2")}), teams) if teams else None
    if mapping is None:
        return []
    listed = {(f["home_team"]["name"], f["away_team"]["name"]) for f in fixtures if f.get("status") != "cancelled"}
    placeholders = []
    for match in matches:
        home, away = mapping[match["team1"]], mapping[match["team2"]]
        if (home, away) in listed:
            continue
        number = int("".join(ch for ch in match.get("round", "") if ch.isdigit()) or 0)
        date = match["date"]
        if match.get("time"):
            kickoff = datetime.fromisoformat(f"{date}T{match['time']}:00").replace(tzinfo=clock).astimezone(timezone.utc)
            utc_date, time_unknown = kickoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"), False
        else:
            utc_date, time_unknown = f"{date}T00:00:00.000Z", True
        home_id, away_id = local_team_id(teams[home]), local_team_id(teams[away])
        placeholders.append({
            "id": f"schedule_{season}_{number}_{home_id}_{away_id}", "_schedule_only": True, "_local_id": schedule_match_id(season, home_id, away_id),
            "_season": season, "_time_unknown": time_unknown, "status": "scheduled", "matchday": number, "utc_date": utc_date,
            "home_team": {"id": teams[home], "name": home}, "away_team": {"id": teams[away], "name": away},
            "score": {"home": None, "away": None, "regulation": None},
        })
    return placeholders
