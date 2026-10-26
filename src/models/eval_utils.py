"""Shared helpers for probabilistic model evaluation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def _validated_rows(probabilities: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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
    return p, labels


def per_match_log_loss(probabilities: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Return each row's negative log probability for its observed class.

    ``probabilities`` must have shape ``(n_matches, n_classes)`` and ``y``
    must contain integer class indices from zero to ``n_classes - 1``.
    """
    p, labels = _validated_rows(probabilities, y)
    p = np.clip(p, 1e-12, 1.0)
    return -np.log(p[np.arange(len(labels)), labels])


def per_match_rps(probabilities: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Ranked probability score per row; columns must be in outcome order (home, draw, away)."""
    p, labels = _validated_rows(probabilities, y)
    if p.shape[1] < 2:
        raise ValueError("RPS needs at least two ordered classes")
    cumulative_error = np.cumsum(p - np.eye(p.shape[1])[labels], axis=1)[:, :-1]
    return (cumulative_error ** 2).sum(axis=1) / (p.shape[1] - 1)


def multiclass_report(probabilities: np.ndarray, y: np.ndarray, bins: int = 10) -> dict[str, Any]:
    """Proper scores plus one-vs-rest AUC and calibration error for every class."""
    p, labels = _validated_rows(probabilities, y)
    onehot = np.eye(p.shape[1])[labels]
    auc_by_class: dict[str, float | None] = {}
    ece_by_class: dict[str, float] = {}
    for k in range(p.shape[1]):
        event = onehot[:, k]
        # AUC is undefined when the class never (or always) occurs in this sample.
        auc_by_class[str(k)] = (
            round(float(roc_auc_score(event, p[:, k])), 4) if 0 < event.sum() < len(event) else None
        )
        ece_by_class[str(k)] = round(expected_calibration_error(p[:, k], event, bins), 4)
    return {
        "n": int(len(labels)),
        "log_loss": round(float(per_match_log_loss(p, labels).mean()), 4),
        "brier": round(float(((p - onehot) ** 2).sum(axis=1).mean()), 4),
        "rps": round(float(per_match_rps(p, labels).mean()), 4),
        "accuracy_pct": round(float((p.argmax(axis=1) == labels).mean() * 100), 2),
        "auc_by_class": auc_by_class,
        "ece_by_class": ece_by_class,
    }


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


Z_ALPHA = 1.96
Z_BETA = 0.8416


def with_inference(loss_a: np.ndarray, loss_b: np.ndarray, n_boot: int = 10000, seed: int = 42) -> dict[str, float | int | None]:
    """``paired_bootstrap_delta`` plus a two-sided p-value and the sample size that would give 80% power.

    A negative ``mean_delta`` means A has the lower loss."""
    result = paired_bootstrap_delta(loss_a, loss_b, n_boot=n_boot, seed=seed)
    delta = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    result["p_two_sided"] = float(min(1.0, 2.0 * min(result["p_a_better"], 1.0 - result["p_a_better"])))
    mean = abs(result["mean_delta"])
    sigma = float(delta.std(ddof=1)) if len(delta) > 1 else 0.0
    result["n_required_80_power"] = int(np.ceil(((Z_ALPHA + Z_BETA) ** 2) * sigma ** 2 / mean ** 2)) if mean > 1e-9 else None
    return result


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted p-values, in the input order."""
    order = np.argsort(p_values)
    ranked = np.asarray(p_values, dtype=float)[order]
    m = len(ranked)
    adjusted = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adjusted, 1.0)
    return out.tolist()


def apply_fdr(entries: dict[str, dict | None]) -> None:
    """Add ``q_fdr`` and ``significant_fdr_05`` (in place) across a family of comparisons."""
    live = {k: v for k, v in entries.items() if v}
    if not live:
        return
    for (_, value), q in zip(live.items(), benjamini_hochberg([v["p_two_sided"] for v in live.values()])):
        value["q_fdr"] = q
        value["significant_fdr_05"] = bool(q < 0.05)
