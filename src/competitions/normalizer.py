"""Cross-league strength normalization and adjustment framework.

Provides mathematical adjustments when comparing or pairing teams across
different domestic leagues in continental tournaments (Champions League, Europa League).
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple



class CrossLeagueNormalizer:
    """Normalizes domestic team statistics using league coefficients and relative strength."""

    # Baseline UEFA country/league coefficients (England = 1.0 baseline)
    DEFAULT_LEAGUE_COEFFICIENTS: Dict[str, float] = {
        "England": 1.000,
        "Italy": 0.940,
        "Spain": 0.910,
        "Germany": 0.890,
        "France": 0.720,
        "Netherlands": 0.650,
        "Portugal": 0.620,
        "Belgium": 0.540,
        "Turkey": 0.490,
        "Czechia": 0.460,
        "Scotland": 0.410,
        "Austria": 0.400,
        "Switzerland": 0.380,
        "Greece": 0.370,
        "Denmark": 0.350,
        "Croatia": 0.320,
        "Serbia": 0.300,
        "Norway": 0.300,
        "Poland": 0.280,
        "Sweden": 0.270,
    }

    def __init__(
        self,
        league_coefficients: Optional[Dict[str, float]] = None,
        damping_factor: float = 0.5,
    ) -> None:
        """Initialize the normalizer.

        Args:
            league_coefficients: Optional mapping of country/league name to relative coefficient.
            damping_factor: Exponent gamma in (coeff_team / coeff_target) ** gamma to prevent over-shrinkage.
        """
        self.coefficients = dict(league_coefficients or self.DEFAULT_LEAGUE_COEFFICIENTS)
        self.damping_factor = max(0.1, min(1.0, float(damping_factor)))

    def get_coefficient(self, country_or_league: str) -> float:
        """Return the relative strength coefficient for a given country or league."""
        name = country_or_league.strip()
        if name in self.coefficients:
            return self.coefficients[name]
        # Match case-insensitively
        for k, v in self.coefficients.items():
            if k.lower() == name.lower():
                return v
        return 0.300  # Default floor for unlisted leagues

    def compute_strength_multiplier(
        self,
        team_country: str,
        opponent_country: str,
        target_competition_coefficient: float = 1.0,
    ) -> Tuple[float, float]:
        """Compute relative strength multipliers for a match between two clubs from different nations.

        Returns:
            Tuple of (home_multiplier, away_multiplier)
        """
        c_home = self.get_coefficient(team_country)
        c_away = self.get_coefficient(opponent_country)

        # Baseline adjustment relative to the tournament standard
        home_mult = (c_home / target_competition_coefficient) ** self.damping_factor
        away_mult = (c_away / target_competition_coefficient) ** self.damping_factor

        return float(home_mult), float(away_mult)

    def normalize_stat(
        self,
        value: float,
        source_country: str,
        target_coefficient: float = 1.0,
    ) -> float:
        """Scale a domestic counting or rate statistic to continental standard.

        Example: A team producing 2.80 npxG in a league with coefficient 0.30
        will have its expected attacking rate scaled down when projected against
        continental elite competition.
        """
        coeff = self.get_coefficient(source_country)
        mult = (coeff / target_coefficient) ** self.damping_factor
        return float(value * mult)

    @staticmethod
    def adjust_by_market_value_ratio(
        base_rate: float,
        team_market_value_m: float,
        opponent_market_value_m: float,
        elasticity: float = 0.15,
    ) -> float:
        """Smoothly adjust goal or chance expectation based on logarithmic market value differential.

        Protects against domestic rate distortion when a dominant domestic team
        (e.g., Red Star Belgrade, Dinamo Zagreb) plays a European heavyweight.
        """
        if team_market_value_m <= 0 or opponent_market_value_m <= 0:
            return base_rate

        log_ratio = math.log(team_market_value_m / opponent_market_value_m)
        adjusted = base_rate * math.exp(elasticity * log_ratio)
        return float(adjusted)
