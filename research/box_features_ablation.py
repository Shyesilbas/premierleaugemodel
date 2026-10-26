"""Ablation of the penalty-area features in the production 1X2 model.

Usage: python3 research/box_features_ablation.py
Question: how much do ``pa_entries`` (provider-specific) and ``touches_in_opp_box`` add to the 74-feature 1X2 model?
Reads:  the Premier League feature table and the production 1X2 artifact (never modified).
Writes: docs/reports/experiments/2026-10-25_box_features_ablation.json (or --output).
Needs:  no key; takes about a minute.
Protocol: the production estimator (logistic regression, C=0.003) is refitted for each outer season on the seasons
before it (2022/23 left out of the training history like production, except for the first outer season), calibrated
on forward out-of-fold predictions inside that history, and scored on the outer season. The locked 2026/27 season is
never read. Paired bootstrap on per-match log-loss, 10,000 draws, seed 42, Benjamini-Hochberg across the three
comparisons. Results go to docs/reports/experiments/, never to models/production/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import EXCLUDED_1X2_TRAINING_SEASONS, FEATURES_PATH, LOCKED_SEASONS, MODELS_DIR, REPORTS_DIR  # noqa: E402
from src.models.eval_utils import paired_bootstrap_delta, per_match_log_loss  # noqa: E402
from src.features.draw_features import add_draw_features  # noqa: E402
from src.models.train_match_outcome import (  # noqa: E402
    apply_probability_calibrator,
    candidate_models,
    chronological_oof_predictions,
    fit_model,
    fit_probability_calibrator,
    ordered_probabilities,
)

LABELS = [0, 1, 2]
OUTER_SEASONS = ("2023_24", "2024_25", "2025_26")
Z_ALPHA, Z_BETA = 1.96, 0.8416
OUT = REPORTS_DIR / "experiments" / "2026-10-25_box_features_ablation.json"


def benjamini_hochberg(p_values):
    order = np.argsort(p_values)
    ranked = np.asarray(p_values, dtype=float)[order]
    m = len(ranked)
    adjusted = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adjusted, 1.0)
    return out.tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=OUT, help="where the JSON result is written (default: %(default)s)")
    output = parser.parse_args().output
    features = list(joblib.load(MODELS_DIR / "outcome_models_v1.joblib")["feature_names"])
    df = add_draw_features(pd.read_parquet(FEATURES_PATH))
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df["target"] = np.select([df["home_score"] > df["away_score"], df["home_score"] == df["away_score"]], [0, 1], default=2)
    df = df.sort_values(["kickoff_millis", "match_id"], kind="mergesort").reset_index(drop=True)
    df = df[~df["season"].astype(str).isin(LOCKED_SEASONS)].reset_index(drop=True)
    seasons = df["season"].astype(str)

    variants = {
        "full": features,
        "without_pa_entries": [c for c in features if "pa_entries" not in c],
        "without_touches_in_opp_box": [c for c in features if "touches_in_opp_box" not in c],
        "without_both": [c for c in features if "pa_entries" not in c and "touches_in_opp_box" not in c],
    }
    removed = {name: sorted(set(features) - set(cols)) for name, cols in variants.items()}
    model = candidate_models()["logreg_C0.003"]

    losses = {name: [] for name in variants}
    y_all, season_all = [], []
    for season in OUTER_SEASONS:
        valid = np.flatnonzero(seasons.eq(season).to_numpy())
        train_end = int(valid[0])
        prior = seasons.iloc[:train_end]
        keep = ~prior.isin(EXCLUDED_1X2_TRAINING_SEASONS).to_numpy()
        if not keep.any():
            keep = np.ones(train_end, dtype=bool)
        train = df.iloc[:train_end].iloc[keep].reset_index(drop=True)
        test = df.iloc[valid]
        y_test = test["target"].to_numpy(dtype=int)
        y_all.append(y_test)
        season_all.extend([season] * len(y_test))
        for name, cols in variants.items():
            oof, targets = chronological_oof_predictions(model, train[cols], train["target"], LABELS, kickoff_times=train["kickoff_millis"])
            calibrator = fit_probability_calibrator(oof, pd.Series(targets), LABELS)
            fitted = fit_model(model, train[cols], train["target"])
            probs = apply_probability_calibrator(ordered_probabilities(fitted, test[cols], LABELS), calibrator)
            losses[name].append(per_match_log_loss(probs, y_test))
        print(season, {n: round(float(l[-1].mean()), 4) for n, l in losses.items()}, flush=True)

    flat = {name: np.concatenate(parts) for name, parts in losses.items()}
    season_idx = np.array(season_all)
    per_season = {s: {n: round(float(flat[n][season_idx == s].mean()), 4) for n in variants} for s in OUTER_SEASONS}
    comparisons = {}
    for name in variants:
        if name == "full":
            continue
        delta = paired_bootstrap_delta(flat[name], flat["full"], n_boot=10000, seed=42)  # positive: removing the feature hurts
        diff = flat[name] - flat["full"]
        p = float(min(1.0, 2.0 * min(delta["p_a_better"], 1.0 - delta["p_a_better"])))
        sigma, mean = float(diff.std(ddof=1)), abs(delta["mean_delta"])
        delta.update(p_two_sided=p, n_required_80_power=int(np.ceil(((Z_ALPHA + Z_BETA) ** 2) * sigma**2 / mean**2)) if mean > 1e-9 else None,
                     seasons_where_full_is_better=int(sum(1 for s in OUTER_SEASONS if per_season[s][name] > per_season[s]["full"])))
        comparisons[name] = delta
    for name, q in zip(comparisons, benjamini_hochberg([c["p_two_sided"] for c in comparisons.values()])):
        comparisons[name]["q_fdr"] = q
        comparisons[name]["significant_fdr_05"] = bool(q < 0.05)

    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": {"estimator": "logreg_C0.003", "outer_seasons": list(OUTER_SEASONS), "locked_excluded": sorted(LOCKED_SEASONS),
                     "bootstrap_draws": 10000, "seed": 42, "matches_scored": int(len(season_idx))},
        "feature_counts": {name: len(cols) for name, cols in variants.items()},
        "removed_features": removed,
        "log_loss_per_season": per_season,
        "log_loss_pooled": {name: round(float(v.mean()), 4) for name, v in flat.items()},
        "removal_minus_full": comparisons,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("feature_counts", "log_loss_pooled", "removal_minus_full")}, indent=2))


if __name__ == "__main__":
    main()
