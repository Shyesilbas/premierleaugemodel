"""Competition management layer for multi-league football modeling."""

from src.competitions.registry import (
    CompetitionConfig,
    CompetitionRegistry,
    get_competition,
    get_priors,
    list_competitions,
)

__all__ = [
    "CompetitionConfig",
    "CompetitionRegistry",
    "get_competition",
    "get_priors",
    "list_competitions",
]
