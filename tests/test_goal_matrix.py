import numpy as np

from src.models.dixon_coles import (
    btts_prob,
    matrix_from_lambdas,
    outcome_probs,
    over_prob,
    team_over_prob,
)


def test_score_matrix_is_normalized_and_outputs_have_matchwise_shapes():
    matrices = matrix_from_lambdas(
        np.array([1.2, 2.1]), np.array([0.8, 1.4]), rho=-0.05, max_goals=8
    )

    assert matrices.shape == (2, 9, 9)
    np.testing.assert_allclose(matrices.sum(axis=(1, 2)), np.ones(2), atol=1e-12)
    assert outcome_probs(matrices).shape == (2, 3)
    assert over_prob(matrices, 2.5).shape == (2,)
    assert btts_prob(matrices).shape == (2,)
    assert team_over_prob(matrices, "home", 1.5).shape == (2,)
    assert team_over_prob(matrices, "away", 1.5).shape == (2,)


def test_over_probabilities_are_monotone_across_goal_lines():
    matrices = matrix_from_lambdas(np.array([1.5]), np.array([1.1]), rho=0.0)
    p15 = over_prob(matrices, 1.5)
    p25 = over_prob(matrices, 2.5)
    p35 = over_prob(matrices, 3.5)

    assert p15[0] >= p25[0] >= p35[0]


def test_team_over_probabilities_are_monotone_across_goal_lines():
    matrices = matrix_from_lambdas(np.array([2.5]), np.array([0.9]), rho=-0.03)
    h05 = team_over_prob(matrices, "home", 0.5)
    h15 = team_over_prob(matrices, "home", 1.5)
    h25 = team_over_prob(matrices, "home", 2.5)
    assert h05[0] >= h15[0] >= h25[0]

    a05 = team_over_prob(matrices, "away", 0.5)
    a15 = team_over_prob(matrices, "away", 1.5)
    a25 = team_over_prob(matrices, "away", 2.5)
    assert a05[0] >= a15[0] >= a25[0]

