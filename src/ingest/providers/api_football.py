"""API-Football ingestion provider for UEFA Champions League, Europa League, and global leagues."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from src.ingest.base_provider import BaseIngestionProvider

logger = logging.getLogger("ingest.api_football")

DEFAULT_API_URL = "https://v3.football.api-sports.io"


class ApiFootballProvider(BaseIngestionProvider):
    """Client and schema transformer for the API-Football (api-sports.io) v3 REST API."""

    def __init__(
        self,
        competition_id: int,
        competition_key: str,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_API_URL,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(competition_id=competition_id, competition_key=competition_key)
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY") or os.environ.get("RAPIDAPI_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.session = session or self._build_session()

    def _build_session(self) -> requests.Session:
        sess = requests.Session()
        headers = {
            "Accept": "application/json",
            "User-Agent": "PremierLeagueModelApp/1.0",
        }
        if self.api_key:
            # Detect whether it is API-Sports native key or RapidAPI key
            if len(self.api_key) == 32 and self.api_key.isalnum():
                headers["x-apisports-key"] = self.api_key
            else:
                headers["x-rapidapi-key"] = self.api_key
                headers["x-rapidapi-host"] = "v3.football.api-sports.io"
        sess.headers.update(headers)

        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=5)
        sess.mount("https://", adapter)
        sess.mount("http://", adapter)
        return sess

    def fetch_fixtures(self, season: str) -> List[Dict[str, Any]]:
        """Fetch all fixtures for league/competition and season year."""
        year = self._parse_season_to_year(season)
        url = f"{self.base_url}/fixtures"
        params = {"league": self.competition_id, "season": year}

        logger.info(f"API-Football fetching fixtures for competition {self.competition_id}, season {year}...")
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        fixtures = data.get("response", [])
        logger.info(f"Retrieved {len(fixtures)} fixtures from API-Football.")
        return fixtures

    def fetch_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch team statistics for a specific fixture."""
        url = f"{self.base_url}/fixtures/statistics"
        params = {"fixture": match_id}

        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("response", [])
            return {"match_id": match_id, "teams": items} if items else None
        logger.warning(f"Failed to fetch statistics for match {match_id}: HTTP {resp.status_code}")
        return None

    def fetch_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch lineups and coaches for a specific fixture."""
        url = f"{self.base_url}/fixtures/lineups"
        params = {"fixture": match_id}

        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            lineups = data.get("response", [])
            return {"match_id": match_id, "lineups": lineups} if lineups else None
        logger.warning(f"Failed to fetch lineups for match {match_id}: HTTP {resp.status_code}")
        return None

    def fetch_match_stream(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch key events (goals, substitutions, cards, VAR) for a match."""
        url = f"{self.base_url}/fixtures/events"
        params = {"fixture": match_id}

        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            events = data.get("response", [])
            return {"match_id": match_id, "events": events} if events else None
        logger.warning(f"Failed to fetch events for match {match_id}: HTTP {resp.status_code}")
        return None

    def normalize_fixture_record(self, raw_fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API-Football fixture payload into internal canonical match structure."""
        fixture = raw_fixture.get("fixture", {})
        teams = raw_fixture.get("teams", {})
        goals = raw_fixture.get("goals", {})
        score = raw_fixture.get("score", {})

        home_team = teams.get("home", {})
        away_team = teams.get("away", {})

        status_short = fixture.get("status", {}).get("short", "")
        is_completed = status_short in ("FT", "AET", "PEN")

        date_str = fixture.get("date", "")
        kickoff_label = date_str[:16].replace("T", " ") if date_str else ""

        h_score = goals.get("home")
        a_score = goals.get("away")

        # Referees in API-Football often have a comma and country: e.g. "C. Turpin, France"
        ref_raw = fixture.get("referee") or "Unknown"
        ref_name = ref_raw.split(",")[0].strip() if "," in ref_raw else ref_raw.strip()

        return {
            "match_id": int(fixture.get("id", 0)),
            "competition_id": self.competition_id,
            "season": str(raw_fixture.get("league", {}).get("season", "")),
            "gameweek": self._extract_round_number(raw_fixture.get("league", {}).get("round", "")),
            "match_date": date_str[:10] if date_str else "",
            "kickoff_label": kickoff_label,
            "day_label": "",
            "time_label": kickoff_label.split(" ")[1] if " " in kickoff_label else "",
            "ground_name": fixture.get("venue", {}).get("name") or "",
            "home_id": int(home_team.get("id", 0)),
            "home_name": str(home_team.get("name", "")),
            "home_abbr": str(home_team.get("code") or ""),
            "home_score": float(h_score) if h_score is not None else None,
            "away_id": int(away_team.get("id", 0)),
            "away_name": str(away_team.get("name", "")),
            "away_abbr": str(away_team.get("code") or ""),
            "away_score": float(a_score) if a_score is not None else None,
            "status": "COMPLETED" if is_completed else "UPCOMING",
            "referee_name": ref_name,
        }

    def normalize_stats_record(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API-Football match statistics array into canonical metrics."""
        teams_stats = raw_stats.get("teams", [])
        if len(teams_stats) < 2:
            return {}

        def _parse_team(item: Dict[str, Any]) -> Dict[str, float]:
            res: Dict[str, float] = {}
            for stat in item.get("statistics", []):
                t = stat.get("type", "")
                val = stat.get("value")
                if val is None:
                    continue
                if isinstance(val, str) and "%" in val:
                    val = float(val.replace("%", "").strip())
                elif isinstance(val, str):
                    try:
                        val = float(val)
                    except ValueError:
                        continue
                else:
                    val = float(val)

                if t == "Shots on Goal":
                    res["shots_ontarget"] = val
                elif t in ("Total Shots", "Shots Total"):
                    res["total_shots"] = val
                elif t == "Corner Kicks":
                    res["won_corners"] = val
                elif t == "Fouls":
                    res["fouls"] = val
                elif t == "Ball Possession":
                    res["possession"] = val
                elif t == "Goalkeeper Saves":
                    res["saves"] = val
                elif t == "Offsides":
                    res["offsides"] = val
                elif t == "Yellow Cards":
                    res["yellow_cards"] = val
                elif t == "Red Cards":
                    res["red_cards"] = val
                elif t in ("expected_goals", "Expected Goals", "xG"):
                    res["xg"] = val
            return res

        home_metrics = _parse_team(teams_stats[0])
        away_metrics = _parse_team(teams_stats[1])

        h_corners = home_metrics.get("won_corners", 0.0)
        a_corners = away_metrics.get("won_corners", 0.0)
        h_shots = home_metrics.get("total_shots", 0.0)
        a_shots = away_metrics.get("total_shots", 0.0)
        h_ontarget = home_metrics.get("shots_ontarget", 0.0)
        a_ontarget = away_metrics.get("shots_ontarget", 0.0)
        h_saves = home_metrics.get("saves", 0.0)
        a_saves = away_metrics.get("saves", 0.0)
        h_yc = home_metrics.get("yellow_cards", 0.0)
        a_yc = away_metrics.get("yellow_cards", 0.0)
        h_rc = home_metrics.get("red_cards", 0.0)
        a_rc = away_metrics.get("red_cards", 0.0)
        h_xg = home_metrics.get("xg")
        a_xg = away_metrics.get("xg")

        return {
            "home_won_corners": h_corners,
            "away_won_corners": a_corners,
            "total_corners": h_corners + a_corners,
            "home_shots": h_shots,
            "away_shots": a_shots,
            "total_shots": h_shots + a_shots,
            "home_shots_ontarget": h_ontarget,
            "away_shots_ontarget": a_ontarget,
            "total_shots_ontarget": h_ontarget + a_ontarget,
            "home_saves": h_saves,
            "away_saves": a_saves,
            "total_saves": h_saves + a_saves,
            "home_total_yel_card": h_yc,
            "away_total_yel_card": a_yc,
            "total_yellow_cards": h_yc + a_yc,
            "home_total_red_card": h_rc,
            "away_total_red_card": a_rc,
            "total_red_cards": h_rc + a_rc,
            "total_cards": h_yc + a_yc + h_rc + a_rc,
            "home_xg": h_xg,
            "away_xg": a_xg,
            "total_xg": (h_xg + a_xg) if (h_xg is not None and a_xg is not None) else None,
        }

    @staticmethod
    def _parse_season_to_year(season_str: str) -> int:
        """Convert '2024_25' or '2024-2025' or '2024' to starting year integer (2024)."""
        clean = season_str.replace("-", "_").split("_")[0]
        try:
            return int(clean)
        except ValueError:
            return 2024

    @staticmethod
    def _extract_round_number(round_str: str) -> int:
        """Extract round/gameweek number from strings like 'Regular Season - 1' or 'Matchday 4'."""
        digits = "".join(ch for ch in round_str if ch.isdigit())
        try:
            return int(digits) if digits else 1
        except ValueError:
            return 1
