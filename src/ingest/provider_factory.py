"""Factory for instantiating competition-appropriate ingestion providers."""

from __future__ import annotations

from typing import Optional, Union

from src.competitions.registry import CompetitionRegistry, get_competition
from src.ingest.base_provider import BaseIngestionProvider
from src.ingest.providers.api_football import ApiFootballProvider
from src.ingest.providers.pulselive import PulseLiveProvider
from src.ingest.providers.thestatsapi_league import TheStatsApiLeagueProvider
from src.ingest.providers.uefa import UefaProvider


def get_provider(
    competition_key_or_id: Optional[Union[str, int]] = None,
    api_key: Optional[str] = None,
) -> BaseIngestionProvider:
    """Instantiate and return the appropriate provider client for a given competition."""
    comp = get_competition(competition_key_or_id) if competition_key_or_id else CompetitionRegistry.default()

    if comp.provider == "pulselive":
        return PulseLiveProvider(
            competition_id=comp.id,
            competition_key=comp.key,
        )
    elif comp.provider == "uefa":
        return UefaProvider(competition_id=comp.id, competition_key=comp.key)
    elif comp.provider == "thestatsapi":
        return TheStatsApiLeagueProvider(competition_id=comp.id, competition_key=comp.key)
    elif comp.provider == "api_football":
        return ApiFootballProvider(
            competition_id=comp.id,
            competition_key=comp.key,
            api_key=api_key,
        )
    else:
        raise ValueError(f"Unsupported provider '{comp.provider}' for competition '{comp.key}'")
