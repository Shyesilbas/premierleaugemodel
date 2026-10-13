"""Compact Dixon–Coles score model used as a chronological 1X2 baseline."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson


class DixonColesModel:
    """Team attack/defence Poisson model with the Dixon–Coles low-score term."""

    def __init__(self, ridge: float = 1.0, max_goals: int = 12):
        self.ridge = float(ridge)
        self.max_goals = int(max_goals)
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
            penalty = self.ridge * (float(np.square(attack).sum()) + float(np.square(defence).sum()))
            penalty += 10.0 * rho * rho
            return float(-np.log(tau).sum() - log_likelihood.sum() + penalty)

        bounds = [(-1.5, 1.5)] * (2 * n_free) + [(-1.5, 1.5), (-0.5, 0.8), (-0.15, 0.15)]
        result = minimize(objective, initial, method="L-BFGS-B", bounds=bounds, options={"maxiter": 1500})
        params = result.x if np.isfinite(result.fun) and np.isfinite(result.x).all() else initial
        attack, defence, self.intercept_, self.home_advantage_, self.rho_ = unpack(params)
        self.attack_ = dict(zip(self.teams_, attack.tolist()))
        self.defence_ = dict(zip(self.teams_, defence.tolist()))
        self.fit_ok_ = bool(result.success)
        return self

    def predict_proba(self, matches: pd.DataFrame) -> np.ndarray:
        home_id = matches["home_id"].astype(int).to_numpy()
        away_id = matches["away_id"].astype(int).to_numpy()
        attack_h = np.asarray([self.attack_.get(team_id, 0.0) for team_id in home_id])
        attack_a = np.asarray([self.attack_.get(team_id, 0.0) for team_id in away_id])
        defence_h = np.asarray([self.defence_.get(team_id, 0.0) for team_id in home_id])
        defence_a = np.asarray([self.defence_.get(team_id, 0.0) for team_id in away_id])
        lam_h = np.exp(np.clip(self.intercept_ + self.home_advantage_ + attack_h - defence_a, -4, 4))
        lam_a = np.exp(np.clip(self.intercept_ + attack_a - defence_h, -4, 4))

        goals = np.arange(self.max_goals + 1)
        probs = np.zeros((len(matches), 3), dtype=float)
        for row_idx, (home_mean, away_mean) in enumerate(zip(lam_h, lam_a)):
            home_pmf = poisson.pmf(goals, home_mean)
            away_pmf = poisson.pmf(goals, away_mean)
            matrix = np.outer(home_pmf, away_pmf)
            matrix[0, 0] *= 1.0 - home_mean * away_mean * self.rho_
            matrix[0, 1] *= 1.0 + home_mean * self.rho_
            matrix[1, 0] *= 1.0 + away_mean * self.rho_
            matrix[1, 1] *= 1.0 - self.rho_
            matrix = np.clip(matrix, 0.0, None)
            total = float(matrix.sum())
            if total <= 0:
                probs[row_idx] = 1.0 / 3.0
                continue
            matrix /= total
            probs[row_idx, 0] = float(np.tril(matrix, -1).sum())  # home goals > away goals
            probs[row_idx, 1] = float(np.trace(matrix))
            probs[row_idx, 2] = float(np.triu(matrix, 1).sum())  # away goals > home goals
        return np.clip(probs, 1e-12, 1.0) / np.clip(probs, 1e-12, 1.0).sum(axis=1, keepdims=True)


def model_summary(model: DixonColesModel) -> dict[str, Any]:
    return {
        "team_count": len(model.teams_),
        "intercept": model.intercept_,
        "home_advantage": model.home_advantage_,
        "rho": model.rho_,
        "optimizer_converged": model.fit_ok_,
    }
