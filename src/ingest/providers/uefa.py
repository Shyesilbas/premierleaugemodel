"""UEFA public match API provider for Champions League and Europa League fixtures."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from src.ingest.base_provider import BaseIngestionProvider

logger = logging.getLogger("ingest.uefa")

UEFA_MATCH_API = "https://match.uefa.com/v5/matches"
UEFA_STANDINGS_API = "https://standings.uefa.com/v1/standings"
UEFA_COMPETITION_IDS = {"champions_league": 1, "europa_league": 14}
DISPLAY_TZ = ZoneInfo("Europe/London")
PAGE_SIZE = 200

# Qualifying rounds (including the API's PLAY_OFF, which is a qualifying round) are skipped.
# Knockout rounds get fixed gameweek numbers after the 8 league-phase matchdays.
STAGE_BY_ROUND_TYPE = {
    "GROUP_STANDINGS": ("league", None),
    "FINAL_TOURNAMENT_PLAY_OFF": ("playoff", 9),
    "ROUND_OF_16": ("r16", 10),
    "QUARTER_FINALS": ("qf", 11),
    "SEMIFINAL": ("sf", 12),
    "FINAL": ("final", 13),
}


class UefaProvider(BaseIngestionProvider):
    """Keyless client for the public UEFA match API (the same feed uefa.com renders)."""

    def __init__(
        self,
        competition_id: int,
        competition_key: str,
        session: Optional[requests.Session] = None,
    ) -> None:
        super().__init__(competition_id=competition_id, competition_key=competition_key)
        self.uefa_competition_id = UEFA_COMPETITION_IDS[competition_key]
        self.session = session or self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        sess = requests.Session()
        sess.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0 PremierLeagueModelApp/1.0"})
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        sess.mount("https://", HTTPAdapter(max_retries=retry))
        return sess

    @staticmethod
    def season_year(season: str) -> int:
        """'2026_27' -> 2027: UEFA names a season by the year it ends in."""
        start = int(season.replace("-", "_").split("_")[0])
        return start + 1

    def fetch_fixtures(self, season: str) -> List[Dict[str, Any]]:
        year = self.season_year(season)
        fixtures: List[Dict[str, Any]] = []
        offset = 0
        while True:
            resp = self.session.get(
                UEFA_MATCH_API,
                params={"competitionId": self.uefa_competition_id, "seasonYear": year, "limit": PAGE_SIZE, "offset": offset},
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
            fixtures.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        logger.info("UEFA %s %s: %d raw fixtures", self.competition_key, season, len(fixtures))
        return fixtures

    def fetch_standings(self, season: str) -> List[Dict[str, Any]]:
        """UEFA's official tables (one per group, or a single league table) with tie-breaks already applied."""
        resp = self.session.get(
            UEFA_STANDINGS_API,
            params={"competitionId": self.uefa_competition_id, "seasonYear": self.season_year(season)},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Per-match team statistics are derived from the event feed (see fetch_match_stream)."""
        return None

    def fetch_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """The match record itself: attendance, weather and pitch condition."""
        resp = self.session.get(f"{UEFA_MATCH_API}/{match_id}", timeout=30)
        return resp.json() if resp.status_code == 200 else None

    def fetch_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Official line-ups (starters, bench, coaches) for one match."""
        resp = self.session.get(f"{UEFA_MATCH_API}/{match_id}/lineups", timeout=30)
        if resp.status_code != 200:
            logger.warning("UEFA lineups for %s: HTTP %s", match_id, resp.status_code)
            return None
        return resp.json()

    def fetch_match_stream(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Every logged match event (goals, shots, corners, fouls, cards, substitutions...)."""
        events: List[Dict[str, Any]] = []
        offset = 0
        while True:
            resp = self.session.get(
                f"{UEFA_MATCH_API}/{match_id}/events",
                params={"filter": "ALL", "offset": offset, "limit": PAGE_SIZE},
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning("UEFA events for %s: HTTP %s", match_id, resp.status_code)
                return None
            page = resp.json()
            events.extend(page)
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return {"match_id": match_id, "events": events}

    def normalize_stats_record(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    @staticmethod
    def _stadium_name(stadium: Dict[str, Any]) -> str:
        names = stadium.get("translations", {})
        for key in ("mediaName", "name"):
            if isinstance(names.get(key), dict) and names[key].get("EN"):
                return names[key]["EN"].strip()
        return str(names.get("EN") or "").strip()

    def normalize_fixture_record(self, raw_fixture: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return the canonical match row, or None for qualifying-round matches."""
        round_type = raw_fixture.get("round", {}).get("metaData", {}).get("type")
        if round_type not in STAGE_BY_ROUND_TYPE:
            return None
        stage, fixed_gameweek = STAGE_BY_ROUND_TYPE[round_type]
        group_name = None
        if stage == "league" and int(raw_fixture.get("round", {}).get("groupCount") or 1) > 1:
            # Until 2023/24 the first phase was eight groups of four, not one 36-team league phase.
            stage = "group"
            raw_group = ((raw_fixture.get("group") or {}).get("metaData") or {}).get("groupName") or ""
            group_name = raw_group.replace("Group", "").strip() or None
        gameweek = fixed_gameweek or int(raw_fixture.get("matchday", {}).get("sequenceNumber") or 1)
        if stage in ("league", "group"):
            gameweek = int("".join(ch for ch in raw_fixture.get("matchday", {}).get("name", "") if ch.isdigit()) or 1)

        kickoff_utc = raw_fixture.get("kickOffTime", {}).get("dateTime", "")
        local = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00")).astimezone(DISPLAY_TZ) if kickoff_utc else None
        day_label = local.strftime("%a %d %b %Y") if local else ""
        time_label = local.strftime("%H:%M %Z") if local else ""

        score = raw_fixture.get("score", {}).get("total", {})
        h_score, a_score = score.get("home"), score.get("away")
        finished = raw_fixture.get("status") == "FINISHED" and h_score is not None and a_score is not None

        home, away = raw_fixture.get("homeTeam", {}), raw_fixture.get("awayTeam", {})
        referee = next((r for r in raw_fixture.get("referees", []) if r.get("role") == "REFEREE"), None)
        ref_name = referee["person"]["translations"]["name"].get("EN") if referee else None
        end_year = int(raw_fixture.get("seasonYear", 0) or 0)
        penalties = (raw_fixture.get("score") or {}).get("penalty") or {}
        winner = raw_fixture.get("winner") or {}
        # Both legs of a tie carry the aggregate winner; a one-off match (the final) only has a match winner.
        decided = winner.get("aggregate") or winner.get("match") or {}
        advancing = (decided.get("team") or {}).get("id")
        if stage in ("league", "group") or raw_fixture.get("status") != "FINISHED" or decided.get("reason") in (None, "DRAW"):
            advancing = None

        return {
            "match_id": int(raw_fixture["id"]),
            "competition_id": self.competition_id,
            "season": f"{end_year - 1}_{str(end_year)[2:]}" if end_year else "",
            "gameweek": gameweek,
            "stage": stage,
            "match_date": local.date().isoformat() if local else "",
            "kickoff_label": f"{day_label}, {time_label}" if local else "",
            "day_label": day_label,
            "time_label": time_label,
            "ground_name": self._stadium_name(raw_fixture.get("stadium", {})),
            "home_id": int(home["id"]),
            "home_name": home.get("internationalName", ""),
            "home_abbr": home.get("teamCode", ""),
            "home_logo": home.get("mediumLogoUrl") or home.get("logoUrl"),
            "home_score": float(h_score) if finished else None,
            "away_id": int(away["id"]),
            "away_name": away.get("internationalName", ""),
            "away_abbr": away.get("teamCode", ""),
            "away_logo": away.get("mediumLogoUrl") or away.get("logoUrl"),
            "away_score": float(a_score) if finished else None,
            "status": "COMPLETED" if finished else "UPCOMING",
            "referee_name": ref_name,
            "group_name": group_name,
            "leg": (raw_fixture.get("leg") or {}).get("number"),
            "advancing_team_id": int(advancing) if advancing else None,
            "advance_reason": decided.get("reason") if advancing else None,
            "home_penalties": float(penalties["home"]) if penalties.get("home") is not None else None,
            "away_penalties": float(penalties["away"]) if penalties.get("away") is not None else None,
        }
