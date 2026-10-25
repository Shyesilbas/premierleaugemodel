"""Data ingestion provider implementations for domestic and continental football competitions."""

from src.ingest.base_provider import BaseIngestionProvider
from src.ingest.providers.api_football import ApiFootballProvider
from src.ingest.providers.pulselive import PulseLiveProvider

__all__ = [
    "BaseIngestionProvider",
    "ApiFootballProvider",
    "PulseLiveProvider",
]
