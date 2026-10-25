"""Abstract base class for match data providers (PulseLive, API-Football, etc.)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseIngestionProvider(ABC):
    """Abstract interface for football data ingestion providers."""

    def __init__(self, competition_id: int, competition_key: str) -> None:
        self.competition_id = competition_id
        self.competition_key = competition_key

    @abstractmethod
    def fetch_fixtures(self, season: str) -> List[Dict[str, Any]]:
        """Fetch fixture schedule for the specified season."""
        raise NotImplementedError

    @abstractmethod
    def fetch_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch match-level statistics for both teams."""
        raise NotImplementedError

    @abstractmethod
    def fetch_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch lineups, venue, referee, and match details."""
        raise NotImplementedError

    @abstractmethod
    def fetch_match_stream(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Fetch play-by-play events or commentary stream."""
        raise NotImplementedError

    @abstractmethod
    def normalize_fixture_record(self, raw_fixture: Dict[str, Any]) -> Dict[str, Any]:
        """Convert provider fixture payload into internal canonical representation."""
        raise NotImplementedError

    @abstractmethod
    def normalize_stats_record(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Convert provider match statistics into internal canonical representation."""
        raise NotImplementedError
