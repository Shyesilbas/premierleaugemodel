"""League-agnostic mathematical models and evaluation utilities."""

from src.core.models.dixon_coles import DixonColesModel, matrix_from_lambdas, outcome_probs
from src.core.models.goals_model import FeatureGoalModel, fit_rho_from_lambdas
from src.core.models.eval_utils import per_match_log_loss, per_match_rps, multiclass_report

__all__ = [
    "DixonColesModel",
    "matrix_from_lambdas",
    "outcome_probs",
    "FeatureGoalModel",
    "fit_rho_from_lambdas",
    "per_match_log_loss",
    "per_match_rps",
    "multiclass_report",
]
