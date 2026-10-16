"""Compact Dixon–Coles score model used as a chronological 1X2 baseline."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson


def matrix_from_lambdas(
    lam_h: np.ndarray,
    lam_a: np.ndarray,
    rho: float,
    max_goals: int = 12,
) -> np.ndarray:
    """Build normalized home-goal by away-goal score matrices.

    The returned shape is ``(n_matches, max_goals + 1, max_goals + 1)``.
    Poisson tails above ``max_goals`` are omitted and the retained cells are
    renormalized, matching the historical ``predict_proba`` behavior.
    """
    home_rate = np.atleast_1d(np.asarray(lam_h, dtype=float)).reshape(-1)
    away_rate = np.atleast_1d(np.asarray(lam_a, dtype=float)).reshape(-1)
    if home_rate.shape != away_rate.shape:
        raise ValueError("Home and away goal rates must have matching shapes")
    if max_goals < 1:
        raise ValueError("max_goals must be at least 1")
    if not np.isfinite(home_rate).all() or not np.isfinite(away_rate).all():
        raise ValueError("Goal rates must contain only finite values")
    if (home_rate <= 0).any() or (away_rate <= 0).any():
        raise ValueError("Goal rates must be strictly positive")
    if not np.isfinite(rho):
        raise ValueError("rho must be finite")

    goals = np.arange(max_goals + 1)
    home_pmf = poisson.pmf(goals[None, :], home_rate[:, None])
    away_pmf = poisson.pmf(goals[None, :], away_rate[:, None])
    matrices = home_pmf[:, :, None] * away_pmf[:, None, :]
    matrices[:, 0, 0] *= 1.0 - home_rate * away_rate * rho
    matrices[:, 0, 1] *= 1.0 + home_rate * rho
    matrices[:, 1, 0] *= 1.0 + away_rate * rho
    matrices[:, 1, 1] *= 1.0 - rho
    matrices = np.clip(matrices, 0.0, None)

    totals = matrices.sum(axis=(1, 2), keepdims=True)
    invalid = (totals <= 0).reshape(-1)
    matrices = matrices / np.where(totals > 0, totals, 1.0)
    if invalid.any():
        matrices[invalid] = 1.0 / (matrices.shape[1] * matrices.shape[2])
    return matrices


def _validate_score_matrices(matrices: np.ndarray) -> np.ndarray:
    values = np.asarray(matrices, dtype=float)
    if values.ndim != 3 or values.shape[1] != values.shape[2] or values.shape[1] < 2:
        raise ValueError("Score matrices must have shape (n, goals, goals), with goals >= 2")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Score matrices must contain finite, non-negative probabilities")
    return values


def outcome_probs(matrices: np.ndarray) -> np.ndarray:
    """Return home-win, draw, and away-win probabilities per score matrix."""
    values = _validate_score_matrices(matrices)
    goal_count = values.shape[1]
    home_goals, away_goals = np.indices((goal_count, goal_count))
    probabilities = np.stack([
        (values * (home_goals > away_goals)).sum(axis=(1, 2)),
        (values * (home_goals == away_goals)).sum(axis=(1, 2)),
        (values * (home_goals < away_goals)).sum(axis=(1, 2)),
    ], axis=1)
    probabilities = np.clip(probabilities, 1e-12, 1.0)
    return probabilities / probabilities.sum(axis=1, keepdims=True)


def over_prob(matrices: np.ndarray, line: float) -> np.ndarray:
    """Return the probability that total goals exceed a half-goal line."""
    values = _validate_score_matrices(matrices)
    if not np.isfinite(line):
        raise ValueError("Goal line must be finite")
    goal_count = values.shape[1]
    home_goals, away_goals = np.indices((goal_count, goal_count))
    return np.clip(
        (values * ((home_goals + away_goals) > line)).sum(axis=(1, 2)),
        0.0,
        1.0,
    )


def btts_prob(matrices: np.ndarray) -> np.ndarray:
    """Return the probability that both teams score at least one goal."""
    values = _validate_score_matrices(matrices)
    goal_count = values.shape[1]
    home_goals, away_goals = np.indices((goal_count, goal_count))
    return np.clip(
        (values * ((home_goals >= 1) & (away_goals >= 1))).sum(axis=(1, 2)),
        0.0,
        1.0,
    )


def team_over_prob(matrices: np.ndarray, side: str, line: float) -> np.ndarray:
    """Return the probability that a specific team's goals exceed a half-goal line."""
    if side not in ("home", "away"):
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")
    if not np.isfinite(line):
        raise ValueError("Goal line must be finite")
    values = _validate_score_matrices(matrices)
    goal_count = values.shape[1]
    home_goals, away_goals = np.indices((goal_count, goal_count))
    goals = home_goals if side == "home" else away_goals
    return np.clip(
        (values * (goals > line)).sum(axis=(1, 2)),
        0.0,
        1.0,
    )


class DixonColesModel:
    """Team attack/defence Poisson model with the Dixon–Coles low-score term."""

    def __init__(
        self,
        ridge: float = 1.0,
        max_goals: int = 12,
        half_life_days: float | None = 365.0,
    ):
        self.ridge = float(ridge)
        self.max_goals = int(max_goals)
        self.half_life_days = half_life_days
        self.teams_: list[int] = []
        self.attack_: dict[int, float] = {}
        self.defence_: dict[int, float] = {}
        self.intercept_: float = 0.0
        self.home_advantage_: float = 0.0
        self.rho_: float = 0.0
        self.fit_ok_: bool = False

    @staticmethod
    def _centered(values: np.ndarray) -> np.ndarray:
        if len(values) == 0:
            return values
        return np.concatenate([values, [-float(np.sum(values))]])

    def fit(self, matches: pd.DataFrame) -> "DixonColesModel":
        required = {"home_id", "away_id", "home_score", "away_score"}
        missing = required.difference(matches.columns)
        if missing:
            raise KeyError(f"Dixon-Coles training data missing columns: {sorted(missing)}")
        data = matches.dropna(subset=["home_id", "away_id", "home_score", "away_score"]).copy()
        data["home_id"] = data["home_id"].astype(int)
        data["away_id"] = data["away_id"].astype(int)
        data["home_score"] = data["home_score"].astype(int)
        data["away_score"] = data["away_score"].astype(int)
        if data.empty:
            raise ValueError("Dixon-Coles requires at least one completed match")

        self.teams_ = sorted(set(data["home_id"]) | set(data["away_id"]))
        team_index = {team_id: idx for idx, team_id in enumerate(self.teams_)}
        h_idx = data["home_id"].map(team_index).to_numpy(dtype=int)
        a_idx = data["away_id"].map(team_index).to_numpy(dtype=int)
        home_goals = data["home_score"].to_numpy(dtype=float)
        away_goals = data["away_score"].to_numpy(dtype=float)
        n_teams = len(self.teams_)
        n_free = max(0, n_teams - 1)

        weights = np.ones(len(data), dtype=float)
        if self.half_life_days is not None:
            if not np.isfinite(self.half_life_days) or self.half_life_days <= 0:
                raise ValueError("half_life_days must be finite and positive when provided")
            date_column = "match_date" if "match_date" in data.columns else None
            if date_column is not None:
                dates = pd.to_datetime(data[date_column], utc=True, errors="coerce")
            elif "kickoff_millis" in data.columns:
                dates = pd.to_datetime(data["kickoff_millis"], unit="ms", utc=True, errors="coerce")
            else:
                raise ValueError("A match_date or kickoff_millis column is required for time-decay weights")
            if dates.isna().any():
                raise ValueError("Match dates must be valid to apply time-decay weights")
            age_days = (dates.max() - dates).dt.total_seconds().to_numpy() / 86400.0
            weights = 0.5 ** (age_days / float(self.half_life_days))
            weights /= weights.mean()

        team_match_counts = np.zeros(n_teams, dtype=float)
        for t_i in h_idx:
            team_match_counts[t_i] += 1
        for t_i in a_idx:
            team_match_counts[t_i] += 1
        # Adaptive shrinkage: Teams with fewer than 10 matches receive up to 4x higher Ridge penalty
        ridge_mult = 1.0 + np.maximum(0.0, (10.0 - team_match_counts) / 2.5)

        initial = np.zeros(2 * n_free + 3, dtype=float)
        initial[2 * n_free] = float(np.log(max(data["home_score"].mean(), 0.2)))
        initial[2 * n_free + 1] = 0.15

        def unpack(params: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float, float]:
            attack = self._centered(params[:n_free])
            defence = self._centered(params[n_free:2 * n_free])
            return (
                attack, defence, float(params[2 * n_free]),
                float(params[2 * n_free + 1]), float(params[2 * n_free + 2]),
            )

        def objective(params: np.ndarray) -> float:
            attack, defence, intercept, home_adv, rho = unpack(params)
            log_h = np.clip(intercept + home_adv + attack[h_idx] - defence[a_idx], -4.0, 4.0)
            log_a = np.clip(intercept + attack[a_idx] - defence[h_idx], -4.0, 4.0)
            lam_h, lam_a = np.exp(log_h), np.exp(log_a)
            log_likelihood = (
                home_goals * log_h - lam_h - gammaln(home_goals + 1)
                + away_goals * log_a - lam_a - gammaln(away_goals + 1)
            )
            tau = np.ones(len(data), dtype=float)
            zero_zero = (home_goals == 0) & (away_goals == 0)
            zero_one = (home_goals == 0) & (away_goals == 1)
            one_zero = (home_goals == 1) & (away_goals == 0)
            one_one = (home_goals == 1) & (away_goals == 1)
            tau[zero_zero] = 1.0 - lam_h[zero_zero] * lam_a[zero_zero] * rho
            tau[zero_one] = 1.0 + lam_h[zero_one] * rho
            tau[one_zero] = 1.0 + lam_a[one_zero] * rho
            tau[one_one] = 1.0 - rho
            if np.any(tau <= 1e-8):
                return 1e8 + float(np.square(np.minimum(tau - 1e-8, 0.0)).sum()) * 1e8
            penalty = self.ridge * (float((ridge_mult * np.square(attack)).sum()) + float((ridge_mult * np.square(defence)).sum()))
            penalty += 10.0 * rho * rho
            return float(-(weights * np.log(tau)).sum() - (weights * log_likelihood).sum() + penalty)

        bounds = [(-1.5, 1.5)] * (2 * n_free) + [(-1.5, 1.5), (-0.5, 0.8), (-0.15, 0.15)]
        result = minimize(objective, initial, method="L-BFGS-B", bounds=bounds, options={"maxiter": 1500})
        params = result.x if np.isfinite(result.fun) and np.isfinite(result.x).all() else initial
        attack, defence, self.intercept_, self.home_advantage_, self.rho_ = unpack(params)
        self.attack_ = dict(zip(self.teams_, attack.tolist()))
        self.defence_ = dict(zip(self.teams_, defence.tolist()))
        self.fit_ok_ = bool(result.success)
        return self

    def lambdas(self, matches: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        home_id = matches["home_id"].astype(int).to_numpy()
        away_id = matches["away_id"].astype(int).to_numpy()
        attack_h = np.asarray([self.attack_.get(team_id, 0.0) for team_id in home_id])
        attack_a = np.asarray([self.attack_.get(team_id, 0.0) for team_id in away_id])
        defence_h = np.asarray([self.defence_.get(team_id, 0.0) for team_id in home_id])
        defence_a = np.asarray([self.defence_.get(team_id, 0.0) for team_id in away_id])
        lam_h = np.exp(np.clip(self.intercept_ + self.home_advantage_ + attack_h - defence_a, -4, 4))
        lam_a = np.exp(np.clip(self.intercept_ + attack_a - defence_h, -4, 4))
        return lam_h, lam_a

    def predict_matrices(self, matches: pd.DataFrame) -> np.ndarray:
        lam_h, lam_a = self.lambdas(matches)
        return matrix_from_lambdas(lam_h, lam_a, self.rho_, self.max_goals)

    def predict_proba(self, matches: pd.DataFrame) -> np.ndarray:
        return outcome_probs(self.predict_matrices(matches))


def model_summary(model: DixonColesModel) -> dict[str, Any]:
    return {
        "team_count": len(model.teams_),
        "intercept": model.intercept_,
        "home_advantage": model.home_advantage_,
        "rho": model.rho_,
        "optimizer_converged": model.fit_ok_,
    }
