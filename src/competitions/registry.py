"""Competition registry and priors configuration loader."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import yaml

from src.config import ROOT

logger = logging.getLogger("competitions.registry")

CONFIG_DIR = ROOT / "config"
COMPETITIONS_CONFIG_PATH = CONFIG_DIR / "competitions.yaml"
PRIORS_CONFIG_PATH = CONFIG_DIR / "priors.yaml"


@dataclass(frozen=True)
class CompetitionConfig:
    """Immutable specification for a football tournament or league."""

    key: str
    id: int
    name: str
    type: str
    country: str
    uefa_coefficient: float
    format: str
    default_season: str
    has_npxg: bool
    provider: str
    cross_league_normalization: bool = False
    legacy_db_name: Optional[str] = None
    provider_competition_id: Optional[str] = None
    has_model: bool = False
    zones: tuple = ()
    schedule_source: Optional[str] = None

    @property
    def is_continental(self) -> bool:
        return self.type == "continental_cup"

    @property
    def is_domestic(self) -> bool:
        return self.type == "domestic_league"

    @property
    def sync_kinds(self) -> tuple:
        """What the data-update button offers: the Premier League has three feeds, every other competition one."""
        return ("matches", "referees", "lineups") if self.provider == "pulselive" else ("matches",)

    def get_priors(self) -> Dict[str, float]:
        """Fetch cold-start statistical priors for this competition."""
        return CompetitionRegistry.get_priors_for(self.key)


class CompetitionRegistry:
    """Singleton registry loading competitions and historical priors."""

    _competitions: Dict[str, CompetitionConfig] = {}
    _id_to_key: Dict[int, str] = {}
    _priors: Dict[str, Dict[str, float]] = {}
    _default_key: str = "premier_league"
    _loaded: bool = False

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._loaded:
            return

        if not COMPETITIONS_CONFIG_PATH.exists():
            raise FileNotFoundError(f"Competitions config not found at {COMPETITIONS_CONFIG_PATH}")

        with open(COMPETITIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
            comp_data = yaml.safe_load(f) or {}

        cls._default_key = comp_data.get("default_competition", "premier_league")
        cls._competitions = {}
        cls._id_to_key = {}

        raw_competitions = comp_data.get("competitions", {})
        for key, info in raw_competitions.items():
            cfg = CompetitionConfig(
                key=key,
                id=int(info["id"]),
                name=info.get("name", key),
                type=info.get("type", "domestic_league"),
                country=info.get("country", "Unknown"),
                uefa_coefficient=float(info.get("uefa_coefficient", 1.0)),
                format=info.get("format", "round_robin"),
                default_season=info.get("default_season", "2026_27"),
                has_npxg=bool(info.get("has_npxg", True)),
                provider=info.get("provider", "pulselive"),
                cross_league_normalization=bool(info.get("cross_league_normalization", False)),
                legacy_db_name=info.get("legacy_db_name"),
                provider_competition_id=info.get("provider_competition_id"),
                has_model=bool(info.get("has_model", False)),
                zones=tuple(info.get("zones") or ()),
                schedule_source=info.get("schedule_source"),
            )
            cls._competitions[key] = cfg
            cls._id_to_key[cfg.id] = key

        if PRIORS_CONFIG_PATH.exists():
            with open(PRIORS_CONFIG_PATH, "r", encoding="utf-8") as f:
                cls._priors = yaml.safe_load(f) or {}
        else:
            cls._priors = {}

        cls._loaded = True

    @classmethod
    def get(cls, key_or_id: Union[str, int]) -> CompetitionConfig:
        """Retrieve competition configuration by its key name or numerical ID."""
        cls._ensure_loaded()
        if isinstance(key_or_id, int):
            key = cls._id_to_key.get(key_or_id)
            if not key:
                raise KeyError(f"Competition with id {key_or_id} not registered")
            return cls._competitions[key]

        key_normalized = str(key_or_id).lower().replace("-", "_").replace(" ", "_")
        if key_normalized in cls._competitions:
            return cls._competitions[key_normalized]

        # Try matching by name
        for cfg in cls._competitions.values():
            if cfg.name.lower() == str(key_or_id).lower():
                return cfg

        raise KeyError(f"Competition '{key_or_id}' not found in registry")

    @classmethod
    def get_or_default(cls, key_or_id: Optional[Union[str, int]] = None) -> CompetitionConfig:
        """Retrieve competition configuration or fallback to default competition."""
        if key_or_id is None:
            return cls.default()
        try:
            return cls.get(key_or_id)
        except KeyError:
            return cls.default()

    @classmethod
    def default(cls) -> CompetitionConfig:
        """Return the default competition (premier_league)."""
        cls._ensure_loaded()
        return cls._competitions[cls._default_key]

    @classmethod
    def list_all(cls) -> List[CompetitionConfig]:
        """List all registered competitions."""
        cls._ensure_loaded()
        return list(cls._competitions.values())

    @classmethod
    def get_priors_for(cls, key: str) -> Dict[str, float]:
        """Retrieve statistical priors for the specified competition."""
        cls._ensure_loaded()
        key_normalized = str(key).lower().replace("-", "_").replace(" ", "_")
        if key_normalized in cls._priors:
            return dict(cls._priors[key_normalized])
        # Fallback to default competition priors if not explicitly defined
        return dict(cls._priors.get(cls._default_key, {}))

    @classmethod
    def reload(cls) -> None:
        """Force reload from disk configuration files."""
        cls._loaded = False
        cls._ensure_loaded()


def get_competition(key_or_id: Optional[Union[str, int]] = None) -> CompetitionConfig:
    """Convenience helper to retrieve a competition configuration."""
    return CompetitionRegistry.get_or_default(key_or_id)


def list_competitions() -> List[CompetitionConfig]:
    """Convenience helper to list all registered competitions."""
    return CompetitionRegistry.list_all()


def get_priors(competition_key: Optional[str] = None) -> Dict[str, float]:
    """Convenience helper to get cold-start priors for a competition."""
    target_key = competition_key or CompetitionRegistry.default().key
    return CompetitionRegistry.get_priors_for(target_key)
