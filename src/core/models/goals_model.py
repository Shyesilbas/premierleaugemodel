"""Feature-driven goal rates and score-matrix predictions."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.core.models.dixon_coles import DixonColesModel, matrix_from_lambdas, outcome_probs


RHO_GRID = np.linspace(-0.15, 0.15, 31)


def fit_rho_from_lambdas(
    home_rate: np.ndarray,
    away_rate: np.ndarray,
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> float:
    """Estimate the Dixon-Coles low-score dependency parameter rho from goal rates."""
    hr = np.asarray(home_rate, dtype=float)
    ar = np.asarray(away_rate, dtype=float)
    hg = np.asarray(home_goals, dtype=int)
    ag = np.asarray(away_goals, dtype=int)
    weights = None if sample_weight is None else np.asarray(sample_weight, dtype=float)

    best_rho, best_log_likelihood = 0.0, -np.inf
    zero_zero = (hg == 0) & (ag == 0)
    zero_one = (hg == 0) & (ag == 1)
    one_zero = (hg == 1) & (ag == 0)
    one_one = (hg == 1) & (ag == 1)

    for rho in RHO_GRID:
        tau = np.ones(len(hg), dtype=float)
        tau[zero_zero] = 1 - hr[zero_zero] * ar[zero_zero] * rho
        tau[zero_one] = 1 + hr[zero_one] * rho
        tau[one_zero] = 1 + ar[one_zero] * rho
        tau[one_one] = 1 - rho
        if np.any(tau <= 1e-8):
            continue
        log_tau = np.log(tau)
        log_likelihood = float(np.sum(weights * log_tau) if weights is not None else np.sum(log_tau))
        if log_likelihood > best_log_likelihood:
            best_rho, best_log_likelihood = float(rho), log_likelihood
    return best_rho


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
        self.rho_ = self._fit_rho(df, weights)
        return self

    def lambdas(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if not self.fitted_:
            raise RuntimeError("FeatureGoalModel must be fitted before prediction")
        X = self._features(df)
        home_rate = np.clip(self.home_.predict(X), 0.05, 6.0)
        away_rate = np.clip(self.away_.predict(X), 0.05, 6.0)
        return home_rate, away_rate

    def _fit_rho(self, df: pd.DataFrame, sample_weight: np.ndarray | None = None) -> float:
        X = self._features(df)
        home_goals = df["home_score"].to_numpy(dtype=float)
        away_goals = df["away_score"].to_numpy(dtype=float)
        n = len(df)
        if n >= 20:
            n_splits = 4
            fold_size = n // (n_splits + 1)
            if fold_size >= 4:
                oof_hr: list[np.ndarray] = []
                oof_ar: list[np.ndarray] = []
                oof_hg: list[np.ndarray] = []
                oof_ag: list[np.ndarray] = []
                oof_w: list[np.ndarray] = []
                for split_idx in range(1, n_splits + 1):
                    tr_end = split_idx * fold_size
                    va_end = n if split_idx == n_splits else (split_idx + 1) * fold_size
                    X_tr, X_va = X.iloc[:tr_end], X.iloc[tr_end:va_end]
                    fit_kwargs = (
                        {}
                        if sample_weight is None
                        else {"poissonregressor__sample_weight": sample_weight[:tr_end]}
                    )
                    h_pipe = self._pipe().fit(X_tr, home_goals[:tr_end], **fit_kwargs)
                    a_pipe = self._pipe().fit(X_tr, away_goals[:tr_end], **fit_kwargs)
                    oof_hr.append(np.clip(h_pipe.predict(X_va), 0.05, 6.0))
                    oof_ar.append(np.clip(a_pipe.predict(X_va), 0.05, 6.0))
                    oof_hg.append(home_goals[tr_end:va_end].astype(int))
                    oof_ag.append(away_goals[tr_end:va_end].astype(int))
                    if sample_weight is not None:
                        oof_w.append(sample_weight[tr_end:va_end])
                return fit_rho_from_lambdas(
                    np.concatenate(oof_hr),
                    np.concatenate(oof_ar),
                    np.concatenate(oof_hg),
                    np.concatenate(oof_ag),
                    np.concatenate(oof_w) if oof_w else None,
                )

        home_rate, away_rate = self.lambdas(df)
        return fit_rho_from_lambdas(
            home_rate,
            away_rate,
            home_goals.astype(int),
            away_goals.astype(int),
            sample_weight,
        )

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
        if self.dc_weight > 0.0:
            self.dc_model_: DixonColesModel | None = DixonColesModel(
                half_life_days=self.dc_half_life_days,
                max_goals=self.max_goals,
            ).fit(df)
            if not self.dc_model_.fit_ok_:
                raise RuntimeError("Dixon-Coles optimizer did not converge; refusing to blend")
        else:
            self.dc_model_ = None
        self.feature_model_ = FeatureGoalModel(
            self.features,
            alpha=self.feature_alpha,
            max_goals=self.max_goals,
        ).fit(df)
        self.fitted_ = True
        blend_home, blend_away = self.lambdas(df)
        self.rho_ = fit_rho_from_lambdas(
            blend_home,
            blend_away,
            df["home_score"].to_numpy(dtype=int),
            df["away_score"].to_numpy(dtype=int),
        )
        return self

    def lambdas(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if not self.fitted_:
            raise RuntimeError("BlendedGoalModel must be fitted before prediction")
        feature_home, feature_away = self.feature_model_.lambdas(df)
        if self.dc_weight <= 0.0 or self.dc_model_ is None:
            return feature_home, feature_away
        dc_home, dc_away = self.dc_model_.lambdas(df)
        return (
            blend_lambdas(dc_home, feature_home, self.dc_weight),
            blend_lambdas(dc_away, feature_away, self.dc_weight),
        )

    def predict_matrices(self, df: pd.DataFrame) -> np.ndarray:
        home_rate, away_rate = self.lambdas(df)
        return matrix_from_lambdas(home_rate, away_rate, self.rho_, self.max_goals)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return outcome_probs(self.predict_matrices(df))
