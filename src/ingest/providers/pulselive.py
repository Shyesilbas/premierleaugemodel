"""PulseLive ingestion provider for Premier League official match data."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from src.ingest.base_provider import BaseIngestionProvider
from src.ingest.fetch_season_data import (
    build_session,
    fetch_fixtures as pl_fetch_fixtures,
    fetch_match_details as pl_fetch_match_details,
    fetch_match_stats as pl_fetch_match_stats,
    fetch_match_stream as pl_fetch_match_stream,
)

logger = logging.getLogger("ingest.pulselive")

# Official PulseLive compSeasons mapping for Premier League
PULSELIVE_COMP_SEASONS = {
    "2022_23": 418,
    "2023_24": 578,
    "2024_25": 719,
    "2025_26": 859,
    "2026_27": 1000,
}


class PulseLiveProvider(BaseIngestionProvider):
    """PulseLive API provider for Premier League fixtures, stream events, and stats."""

    def __init__(
        self,
        competition_id: int = 39,
        competition_key: str = "premier_league",
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(competition_id=competition_id, competition_key=competition_key)
        self.session = session or build_session()

    def fetch_fixtures(self, season: str) -> List[Dict[str, Any]]:
        season_key = season.replace("-", "_")
        comp_season_id = PULSELIVE_COMP_SEASONS.get(season_key, 1000)
        return pl_fetch_fixtures(self.session, comp_season_id=comp_season_id, comps=1)

    def fetch_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        return pl_fetch_match_stats(self.session, match_id)

    def fetch_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        return pl_fetch_match_details(self.session, match_id)

    def fetch_match_stream(self, match_id: int) -> Optional[Dict[str, Any]]:
        return pl_fetch_match_stream(self.session, match_id)

    def normalize_fixture_record(self, raw_fixture: Dict[str, Any]) -> Dict[str, Any]:
        mid = int(raw_fixture.get("id", 0))
        teams = raw_fixture.get("teams", [])
        h_team = teams[0].get("team", {}) if len(teams) > 0 else {}
        a_team = teams[1].get("team", {}) if len(teams) > 1 else {}
        h_score = teams[0].get("score") if len(teams) > 0 else None
        a_score = teams[1].get("score") if len(teams) > 1 else None

        kickoff = raw_fixture.get("kickoff", {}).get("label", "")
        day_label = kickoff.split(",")[0].strip() if "," in kickoff else kickoff
        time_label = kickoff.split(",")[1].strip() if "," in kickoff else ""

        officials = raw_fixture.get("matchOfficials", [])
        ref_name = officials[0].get("matchOfficial", {}).get("name", {}).get("display", "Unknown") if officials else "Unknown"

        status = raw_fixture.get("status", "")
        is_completed = (status == "C") or (h_score is not None and a_score is not None)

        return {
            "match_id": mid,
            "competition_id": self.competition_id,
            "season": str(raw_fixture.get("gameweek", {}).get("compSeason", {}).get("label", "")).replace("/", "_"),
            "gameweek": int(raw_fixture.get("gameweek", {}).get("gameweek", 1)),
            "match_date": raw_fixture.get("kickoff", {}).get("millis", 0),
            "kickoff_label": kickoff,
            "day_label": day_label,
            "time_label": time_label,
            "ground_name": raw_fixture.get("ground", {}).get("name", ""),
            "home_id": int(h_team.get("id", 0)),
            "home_name": str(h_team.get("name", "")),
            "home_abbr": str(h_team.get("club", {}).get("abbr", "")),
            "home_score": float(h_score) if h_score is not None else None,
            "away_id": int(a_team.get("id", 0)),
            "away_name": str(a_team.get("name", "")),
            "away_abbr": str(a_team.get("club", {}).get("abbr", "")),
            "away_score": float(a_score) if a_score is not None else None,
            "status": "COMPLETED" if is_completed else "UPCOMING",
            "referee_name": ref_name,
        }

    def normalize_stats_record(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        # PulseLive returns data dictionary with entity stats
        return raw_stats.get("data", {})
