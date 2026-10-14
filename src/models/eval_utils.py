"""Shared helpers for probabilistic model evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def per_match_log_loss(probabilities: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Return each row's negative log probability for its observed class.

    ``probabilities`` must have shape ``(n_matches, n_classes)`` and ``y``
    must contain integer class indices from zero to ``n_classes - 1``.
    """
    p = np.asarray(probabilities, dtype=float)
    labels = np.asarray(y, dtype=int)
    if p.ndim != 2:
        raise ValueError("probabilities must be a 2D array")
    if labels.ndim != 1 or len(labels) != len(p):
        raise ValueError("y must be a 1D array with one label per probability row")
    if p.shape[1] == 0:
        raise ValueError("probabilities must contain at least one class")
    if not np.isfinite(p).all():
        raise ValueError("probabilities must contain only finite values")
    if labels.size and ((labels < 0).any() or (labels >= p.shape[1]).any()):
        raise ValueError("y contains a class index outside the probability columns")

    p = np.clip(p, 1e-12, 1.0)
    return -np.log(p[np.arange(len(labels)), labels])


def paired_bootstrap_delta(
    loss_a: np.ndarray,
    loss_b: np.ndarray,
    n_boot: int = 5000,
    seed: int = 42,
) -> dict[str, float | int]:
    """Bootstrap the paired mean difference ``loss_a - loss_b``.

    A negative delta means A has lower loss. The confidence interval and
    ``p_a_better`` are calculated by resampling match-level paired deltas.
    """
    a = np.asarray(loss_a, dtype=float)
    b = np.asarray(loss_b, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or len(a) != len(b):
        raise ValueError("loss arrays must be 1D and have equal lengths")
    if len(a) == 0:
        raise ValueError("Empty loss arrays")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("loss arrays must contain only finite values")
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")

    delta = a - b
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(delta), size=(n_boot, len(delta)))
    means = delta[indices].mean(axis=1)
    return {
        "mean_delta": float(delta.mean()),
        "ci_low": float(np.percentile(means, 2.5)),
        "ci_high": float(np.percentile(means, 97.5)),
        "p_a_better": float((means < 0).mean()),
        "n": int(len(delta)),
    }


def reliability_table(
    p_event: np.ndarray,
    actual: np.ndarray,
    bins: int = 10,
) -> list[dict[str, Any]]:
    """Return quantile-binned predicted and observed rates for a binary event."""
    probabilities = np.asarray(p_event, dtype=float)
    outcomes = np.asarray(actual, dtype=float)
    if probabilities.ndim != 1 or outcomes.ndim != 1 or len(probabilities) != len(outcomes):
        raise ValueError("p_event and actual must be 1D arrays with equal lengths")
    if len(probabilities) == 0:
        raise ValueError("Cannot build a reliability table from empty arrays")
    if bins < 1:
        raise ValueError("bins must be at least 1")
    if not np.isfinite(probabilities).all() or not np.isfinite(outcomes).all():
        raise ValueError("p_event and actual must contain only finite values")
    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("event probabilities must be between 0 and 1")
    if ((outcomes < 0) | (outcomes > 1)).any():
        raise ValueError("binary outcomes must be between 0 and 1")

    frame = pd.DataFrame({"p": probabilities, "actual": outcomes})
    quantiles = pd.qcut(frame["p"], q=bins, duplicates="drop")
    if quantiles.isna().all():
        # qcut cannot form intervals when every prediction is identical.
        frame["bin"] = "all predictions"
    else:
        frame["bin"] = quantiles.astype(str)

    rows: list[dict[str, Any]] = []
    for label, group in frame.groupby("bin", observed=True, sort=False):
        rows.append({
            "bin": str(label),
            "n": int(len(group)),
            "mean_predicted": round(float(group["p"].mean()), 4),
            "observed_rate": round(float(group["actual"].mean()), 4),
        })
    rows.sort(key=lambda row: row["mean_predicted"])
    return rows


def expected_calibration_error(
    p_event: np.ndarray,
    actual: np.ndarray,
    bins: int = 10,
) -> float:
    """Calculate weighted absolute calibration error over quantile bins."""
    rows = reliability_table(p_event, actual, bins)
    total = sum(row["n"] for row in rows)
    return float(
        sum(row["n"] * abs(row["mean_predicted"] - row["observed_rate"]) for row in rows)
        / total
    )
