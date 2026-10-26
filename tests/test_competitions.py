"""Tests for the competition registry and cross-league normalizer."""

from __future__ import annotations

import pytest

from src.competitions.normalizer import CrossLeagueNormalizer
from src.competitions.registry import (
    CompetitionRegistry,
    get_competition,
    get_priors,
)
from src.models.dixon_coles import matrix_from_lambdas, outcome_probs
from src.models.eval_utils import per_match_log_loss, per_match_rps
import numpy as np


def test_competition_registry_defaults():
    default_comp = CompetitionRegistry.default()
    assert default_comp.key == "premier_league"
    assert default_comp.id == 39
    assert default_comp.uefa_coefficient == 1.0
    assert default_comp.is_domestic is True
    assert default_comp.is_continental is False


def test_competition_registry_lookups():
    # By key
    pl = get_competition("premier_league")
    assert pl.id == 39

    # By ID
    ucl = get_competition(2)
    assert ucl.key == "champions_league"
    assert ucl.is_continental is True
    assert ucl.format == "swiss_league_and_knockout"

    # By display name
    uel = get_competition("UEFA Europa League")
    assert uel.id == 3
    assert uel.uefa_coefficient == pytest.approx(0.820)


def test_competition_priors_retrieval():
    priors = get_priors("premier_league")
    assert "corners_for" in priors
    assert priors["corners_for"] == pytest.approx(5.15)
    assert priors["goals_for"] == pytest.approx(1.45)

    ucl_priors = get_priors("champions_league")
    assert ucl_priors["goals_for"] == pytest.approx(1.55)


def test_cross_league_normalizer():
    normalizer = CrossLeagueNormalizer(damping_factor=0.5)

    # England vs England in UCL -> 1.0 multiplier
    m_home, m_away = normalizer.compute_strength_multiplier("England", "England")
    assert m_home == pytest.approx(1.0)
    assert m_away == pytest.approx(1.0)

    # Serbia (coeff 0.30) vs England (coeff 1.0)
    # sqrt(0.30 / 1.0) = sqrt(0.30) ~= 0.5477
    norm_stat = normalizer.normalize_stat(2.0, "Serbia", target_coefficient=1.0)
    assert norm_stat < 2.0
    assert norm_stat == pytest.approx(2.0 * np.sqrt(0.30))

    # Market value ratio adjustment
    adj = normalizer.adjust_by_market_value_ratio(
        base_rate=1.5,
        team_market_value_m=1000.0,
        opponent_market_value_m=100.0,
        elasticity=0.15,
    )
    assert adj > 1.5


def test_core_models_equivalence():
    lam_h = np.array([1.5, 2.0])
    lam_a = np.array([1.1, 0.8])
    matrices = matrix_from_lambdas(lam_h, lam_a, rho=0.05, max_goals=5)
    assert matrices.shape == (2, 6, 6)
    probs = outcome_probs(matrices)
    assert probs.shape == (2, 3)
    assert np.allclose(probs.sum(axis=1), 1.0)

    # Test proper scoring rules
    labels = np.array([0, 2])
    ll = per_match_log_loss(probs, labels)
    rps = per_match_rps(probs, labels)
    assert len(ll) == 2
    assert len(rps) == 2
    assert (ll > 0).all()
    assert (rps >= 0).all()
