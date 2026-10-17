"""Feature-driven goal rates and score-matrix predictions."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.models.dixon_coles import DixonColesModel, matrix_from_lambdas, outcome_probs


RHO_GRID = np.linspace(-0.15, 0.15, 31)


class FeatureGoalModel:
    """Two Poisson regressions plus a Dixon–Coles low-score correction."""

    def __init__(self, features: Sequence[str], alpha: float = 30.0, max_goals: int = 12):
        self.features = list(features)
        self.alpha = float(alpha)
        self.max_goals = int(max_goals)
        if not self.features:
            raise ValueError("At least one feature is required")
        if self.alpha < 0:
            raise ValueError("alpha must be non-negative")
        if self.max_goals < 1:
            raise ValueError("max_goals must be at least 1")
        self.rho_ = 0.0
        self.fitted_ = False

    def _pipe(self):
        return make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            PoissonRegressor(alpha=self.alpha, max_iter=3000),
        )

    def _features(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.features if column not in df.columns]
        if missing:
            raise KeyError(f"Goal model features missing from data: {missing}")
        return df[self.features].replace([np.inf, -np.inf], np.nan)

    def fit(
        self,
        df: pd.DataFrame,
        sample_weight: np.ndarray | None = None,
    ) -> "FeatureGoalModel":
        required = {"home_score", "away_score"}
        missing = required.difference(df.columns)
        if missing:
            raise KeyError(f"Goal model training data missing columns: {sorted(missing)}")
        if df.empty:
            raise ValueError("FeatureGoalModel requires at least one completed match")

        home_goals = df["home_score"].to_numpy(dtype=float)
        away_goals = df["away_score"].to_numpy(dtype=float)
        if not np.isfinite(home_goals).all() or not np.isfinite(away_goals).all():
            raise ValueError("Goal targets must be finite")
        if (home_goals < 0).any() or (away_goals < 0).any():
            raise ValueError("Goal targets must be non-negative")

        weights = None if sample_weight is None else np.asarray(sample_weight, dtype=float)
        if weights is not None:
            if weights.ndim != 1 or len(weights) != len(df):
                raise ValueError("sample_weight must contain one value per match")
            if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
                raise ValueError("sample_weight must be finite, non-negative, and have a positive sum")
        fit_kwargs = {} if weights is None else {"poissonregressor__sample_weight": weights}
        X = self._features(df)
        self.home_ = self._pipe().fit(X, home_goals, **fit_kwargs)
        self.away_ = self._pipe().fit(X, away_goals, **fit_kwargs)
        self.fitted_ = True
        self.rho_ = self._fit_rho(df)
        return self

    def lambdas(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if not self.fitted_:
            raise RuntimeError("FeatureGoalModel must be fitted before prediction")
        X = self._features(df)
        home_rate = np.clip(self.home_.predict(X), 0.05, 6.0)
        away_rate = np.clip(self.away_.predict(X), 0.05, 6.0)
        return home_rate, away_rate

    def _fit_rho(self, df: pd.DataFrame) -> float:
        home_rate, away_rate = self.lambdas(df)
        home_goals = df["home_score"].to_numpy(dtype=int)
        away_goals = df["away_score"].to_numpy(dtype=int)
        best_rho, best_log_likelihood = 0.0, -np.inf

        for rho in RHO_GRID:
            tau = np.ones(len(df), dtype=float)
            zero_zero = (home_goals == 0) & (away_goals == 0)
            zero_one = (home_goals == 0) & (away_goals == 1)
            one_zero = (home_goals == 1) & (away_goals == 0)
            one_one = (home_goals == 1) & (away_goals == 1)
            tau[zero_zero] = 1 - home_rate[zero_zero] * away_rate[zero_zero] * rho
            tau[zero_one] = 1 + home_rate[zero_one] * rho
            tau[one_zero] = 1 + away_rate[one_zero] * rho
            tau[one_one] = 1 - rho
            if np.any(tau <= 1e-8):
                continue
            log_likelihood = float(np.log(tau).sum())
            if log_likelihood > best_log_likelihood:
                best_rho, best_log_likelihood = float(rho), log_likelihood
        return best_rho

    def predict_matrices(self, df: pd.DataFrame) -> np.ndarray:
        home_rate, away_rate = self.lambdas(df)
        return matrix_from_lambdas(home_rate, away_rate, self.rho_, self.max_goals)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return outcome_probs(self.predict_matrices(df))


def blend_lambdas(lam_a: np.ndarray, lam_b: np.ndarray, weight_a: float) -> np.ndarray:
    """Geometrically blend positive goal rates, with ``weight_a`` on A."""
    a = np.asarray(lam_a, dtype=float)
    b = np.asarray(lam_b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("Goal-rate arrays must have matching shapes")
    if not 0.0 <= weight_a <= 1.0:
        raise ValueError("weight_a must be between 0 and 1")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or (a <= 0).any() or (b <= 0).any():
        raise ValueError("Goal rates must be finite and strictly positive")
    return np.exp(weight_a * np.log(a) + (1.0 - weight_a) * np.log(b))


class BlendedGoalModel:
    """Geometric blend of recency-weighted Dixon–Coles and feature Poisson rates."""

    def __init__(
        self,
        features: Sequence[str],
        dc_half_life_days: float = 365.0,
        feature_alpha: float = 100.0,
        dc_weight: float = 0.5,
        max_goals: int = 12,
    ):
        if not 0.0 <= dc_weight <= 1.0:
            raise ValueError("dc_weight must be between 0 and 1")
        self.features = list(features)
        self.dc_half_life_days = float(dc_half_life_days)
        self.feature_alpha = float(feature_alpha)
        self.dc_weight = float(dc_weight)
        self.max_goals = int(max_goals)
        self.fitted_ = False

    def fit(self, df: pd.DataFrame) -> "BlendedGoalModel":
        self.dc_model_ = DixonColesModel(
            half_life_days=self.dc_half_life_days,
            max_goals=self.max_goals,
        ).fit(df)
        if not self.dc_model_.fit_ok_:
            raise RuntimeError("Dixon-Coles optimizer did not converge; refusing to blend")
        self.feature_model_ = FeatureGoalModel(
            self.features,
            alpha=self.feature_alpha,
            max_goals=self.max_goals,
        ).fit(df)
        self.rho_ = 0.5 * (self.dc_model_.rho_ + self.feature_model_.rho_)
        self.fitted_ = True
        return self

    def lambdas(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if not self.fitted_:
            raise RuntimeError("BlendedGoalModel must be fitted before prediction")
        dc_home, dc_away = self.dc_model_.lambdas(df)
        feature_home, feature_away = self.feature_model_.lambdas(df)
        return (
            blend_lambdas(dc_home, feature_home, self.dc_weight),
            blend_lambdas(dc_away, feature_away, self.dc_weight),
        )

    def predict_matrices(self, df: pd.DataFrame) -> np.ndarray:
        home_rate, away_rate = self.lambdas(df)
        return matrix_from_lambdas(home_rate, away_rate, self.rho_, self.max_goals)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return outcome_probs(self.predict_matrices(df))
