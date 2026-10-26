"""Train and audit the match-outcome and goals model of a league fed by TheStatsAPI (LaLiga and leagues added the same way).

Usage: python3 -m src.models.train_league_model --competition la_liga [--no-save]

What it does:
1. builds the pre-match feature table (``build_league_features``) from the database;
2. walk-forward evaluation: every outer season is predicted by a model fitted only on the seasons before it. The model
   (candidate chosen by chronological cross-validation, then a temperature/bias calibrator fitted on out-of-fold
   predictions) is scored against honest baselines on the same matches: league base rates, Elo with home advantage, and
   - from 2024/25 - the bookmakers' closing odds. Paired bootstrap (10,000 draws, seed 42), Benjamini-Hochberg across the
   comparisons, power analysis for the differences that are within noise;
3. goals: independent Poisson rates -> Dixon-Coles matrix aligned to the calibrated 1X2 -> over/under and both-teams-to-score,
   against base rates and the training mean;
4. gate: the model is served only if it beats the base rate significantly and is not worse than the Elo baseline;
   otherwise the Elo baseline is served and labelled as such;
5. writes the report (docs/reports/models/<key>_walk_forward.json) and, unless --no-save, the production artifact
   (models/production/<key>/outcome_models_v1.joblib) fitted on every played match.

Reads:  data/football.db (matches, TheStatsAPI statistics and odds). Writes: the report and the artifact of that competition only.
Needs:  no key. The locked season (config.LOCKED_SEASONS) is never used for any choice; it is scored once as monitoring.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.competitions.registry import get_competition
from src.config import LOCKED_SEASONS, REPORTS_DIR, competition_paths, configure_logging
from src.models.dixon_coles import align_to_outcome_probs, matrix_from_lambdas
from src.models.eval_utils import apply_fdr, multiclass_report, per_match_log_loss, with_inference
from src.db.database import get_db
from src.features.build_league_features import build_league_features, feature_columns, load_league_matches
from src.models.model_utils import apply_probability_calibrator
from src.models.train_match_outcome import (
    candidate_models,
    chronological_oof_predictions,
    fit_model,
    fit_probability_calibrator,
    forward_time_splits,
    ordered_probabilities,
    select_model,
)

logger = logging.getLogger("train_league_model")
LABELS = [0, 1, 2]
WARM_UP_SEASON = "2022_23"
OUTER_SEASONS = ("2024_25", "2025_26")
ODDS_FIRST_SEASON = "2024_25"
RHO = -0.04
POISSON_ALPHAS = (0.3, 1.0, 3.0, 10.0)
MAX_GOALS = 12
LOW_C_GRID = (0.0003, 0.0001)
GOAL_MARKETS = ("over_15", "over_25", "over_35", "btts")
MIN_ELO_NON_INFERIORITY = 0.0  # the model's mean log-loss may not exceed the Elo baseline's


def outcome_label(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(np.select([frame["home_score"] > frame["away_score"], frame["home_score"] == frame["away_score"]], [0, 1], default=2), index=frame.index)


def market_probabilities(conn: sqlite3.Connection, competition_id: int) -> Dict[int, np.ndarray]:
    """Bookmaker-averaged, margin-free 1X2 probabilities per match (closing odds where stored)."""
    rows = conn.execute(
        """SELECT o.match_id, COALESCE(o.home_last_seen, o.home_open), COALESCE(o.draw_last_seen, o.draw_open), COALESCE(o.away_last_seen, o.away_open)
           FROM external_match_odds o JOIN matches m ON m.match_id = o.match_id WHERE m.competition_id = ?""",
        (competition_id,),
    ).fetchall()
    grouped: Dict[int, List[np.ndarray]] = {}
    for match_id, h, d, a in rows:
        if h and d and a and min(h, d, a) > 1.0:
            raw = np.array([1 / h, 1 / d, 1 / a])
            grouped.setdefault(int(match_id), []).append(raw / raw.sum())
    return {m: np.mean(v, axis=0) for m, v in grouped.items()}


def base_rate(y_train: np.ndarray, n: int) -> np.ndarray:
    counts = np.bincount(y_train, minlength=3) + np.array([0.47, 0.22, 0.31]) * 20.0
    return np.tile(counts / counts.sum(), (n, 1))


def elo_baseline(train: pd.DataFrame, test: pd.DataFrame, y_train: np.ndarray) -> np.ndarray:
    """Elo difference (overall and by venue) with a home advantage, fitted on the same history as the model."""
    columns = ["elo_diff", "elo_venue_diff"]
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    model.fit(train[columns], y_train)
    return ordered_probabilities(model, test[columns], LABELS)


def league_candidates(low_c: bool = False) -> Dict[str, Any]:
    """The Premier League candidate grid; with ``low_c`` it also holds logistic regressions with stronger penalties (C below the old grid edge)."""
    candidates = candidate_models()
    if low_c:
        candidates = {**{f"logreg_C{c}": make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                                                       LogisticRegression(C=c, max_iter=5000)) for c in LOW_C_GRID}, **candidates}
    return candidates


def fit_outcome(train: pd.DataFrame, columns: List[str], candidates: Optional[Dict[str, Any]] = None) -> Tuple[Any, Dict[str, Any], str, Dict[str, float]]:
    """Candidate by chronological CV, calibrator from out-of-fold predictions; uses only ``train``."""
    candidates = candidates or candidate_models()
    X, y, times = train[columns], outcome_label(train), train["kickoff_millis"]
    best, scores = select_model("1x2", X, y, LABELS, times, candidates)
    oof, targets = chronological_oof_predictions(candidates[best], X, y, LABELS, kickoff_times=times)
    calibrator = fit_probability_calibrator(oof, pd.Series(targets), LABELS)
    return fit_model(candidates[best], X, y), calibrator, best, scores


def predict_outcome(model: Any, calibrator: Dict[str, Any], frame: pd.DataFrame, columns: List[str]) -> np.ndarray:
    return apply_probability_calibrator(ordered_probabilities(model, frame[columns], LABELS), calibrator)


def poisson_pipeline(alpha: float):
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), PoissonRegressor(alpha=alpha, max_iter=1000))


def fit_goals(train: pd.DataFrame, columns: List[str]) -> Tuple[Any, Any, float]:
    """One Poisson rate model per side; the penalty is chosen by chronological CV on ``train``."""
    X = train[columns]
    times = train["kickoff_millis"]
    best_alpha, best_loss = POISSON_ALPHAS[0], np.inf
    for alpha in POISSON_ALPHAS:
        loss = []
        for tr, va in forward_time_splits(len(X), times):
            for target in ("home_score", "away_score"):
                model = poisson_pipeline(alpha).fit(X.iloc[tr], train[target].iloc[tr])
                rate = np.clip(model.predict(X.iloc[va]), 0.05, None)
                actual = train[target].iloc[va].to_numpy()
                loss.append(float(np.mean(rate - actual * np.log(rate))))
        if np.mean(loss) < best_loss:
            best_alpha, best_loss = alpha, float(np.mean(loss))
    home = poisson_pipeline(best_alpha).fit(X, train["home_score"])
    away = poisson_pipeline(best_alpha).fit(X, train["away_score"])
    return home, away, best_alpha


def goal_markets(home: Any, away: Any, frame: pd.DataFrame, columns: List[str], outcome: np.ndarray) -> Dict[str, np.ndarray]:
    lam_h = np.clip(home.predict(frame[columns]), 0.15, 5.5)
    lam_a = np.clip(away.predict(frame[columns]), 0.15, 5.5)
    matrices = align_to_outcome_probs(matrix_from_lambdas(lam_h, lam_a, rho=RHO, max_goals=MAX_GOALS), outcome)
    totals = np.arange(MAX_GOALS + 1)[:, None] + np.arange(MAX_GOALS + 1)[None, :]
    return {
        "lam_home": lam_h, "lam_away": lam_a,
        "over_15": (matrices * (totals > 1)).sum(axis=(1, 2)), "over_25": (matrices * (totals > 2)).sum(axis=(1, 2)),
        "over_35": (matrices * (totals > 3)).sum(axis=(1, 2)), "btts": matrices[:, 1:, 1:].sum(axis=(1, 2)),
    }


def binary_log_loss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def score_block(probabilities: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    report = multiclass_report(probabilities, y)
    return {k: report[k] for k in ("n", "log_loss", "brier", "rps", "accuracy_pct")}


def walk_forward(frame: pd.DataFrame, columns: List[str], market: Dict[int, np.ndarray], candidates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    played = frame[frame["home_score"].notna()].copy()
    played["y"] = outcome_label(played)
    seasons = sorted(played["season"].unique())
    locked = [s for s in seasons if s in LOCKED_SEASONS]
    folds = [s for s in (*OUTER_SEASONS, *locked) if s in seasons]
    rows: Dict[str, List[pd.DataFrame]] = {"model": [], "base_rate": [], "elo": [], "market": []}
    detail: Dict[str, Any] = {}
    goal_rows: List[pd.DataFrame] = []
    for season in folds:
        train = played[(played["season"] < season) & ~played["season"].isin(LOCKED_SEASONS)].reset_index(drop=True)
        test = played[played["season"] == season].reset_index(drop=True)
        y_train, y_test = train["y"].to_numpy(), test["y"].to_numpy()
        model, calibrator, name, scores = fit_outcome(train, columns, candidates)
        probs = predict_outcome(model, calibrator, test, columns)
        pool = {"model": probs, "base_rate": base_rate(y_train, len(test)), "elo": elo_baseline(train, test, y_train)}
        has_odds = test["match_id"].map(lambda m: m in market)
        pool["market"] = np.vstack([market.get(m, np.full(3, np.nan)) for m in test["match_id"]])
        for key, value in pool.items():
            rows[key].append(pd.DataFrame(value, columns=["p_home", "p_draw", "p_away"]).assign(match_id=test["match_id"].values, season=season, y=y_test))
        home, away, alpha = fit_goals(train, columns)
        markets = goal_markets(home, away, test, columns, probs)
        total = (test["home_score"] + test["away_score"]).to_numpy()
        goal_rows.append(pd.DataFrame({
            "season": season, "match_id": test["match_id"].values, "total": total, "btts": ((test["home_score"] > 0) & (test["away_score"] > 0)).astype(int).values,
            "lam_home": markets["lam_home"], "lam_away": markets["lam_away"], "lam_total": markets["lam_home"] + markets["lam_away"], "over_15": markets["over_15"], "over_25": markets["over_25"], "over_35": markets["over_35"], "btts_p": markets["btts"],
            "train_total_mean": float((train["home_score"] + train["away_score"]).mean()), "train_over_15": float(((train["home_score"] + train["away_score"]) > 1).mean()),
            "train_over_25": float(((train["home_score"] + train["away_score"]) > 2).mean()), "train_over_35": float(((train["home_score"] + train["away_score"]) > 3).mean()),
            "train_btts": float(((train["home_score"] > 0) & (train["away_score"] > 0)).mean()),
        }))
        detail[season] = {"train_matches": int(len(train)), "selected_model": name, "cv_log_loss": scores, "poisson_alpha": alpha,
                          "locked_monitoring": season in LOCKED_SEASONS, "market_coverage": int(has_odds.sum())}
        logger.info("%s: trained on %d matches, selected %s", season, len(train), name)
    return {"rows": {k: pd.concat(v, ignore_index=True) for k, v in rows.items()}, "goals": pd.concat(goal_rows, ignore_index=True), "detail": detail}


def summarize(result: Dict[str, Any]) -> Dict[str, Any]:
    rows, goals = result["rows"], result["goals"]
    per_season: Dict[str, Any] = {}
    seasons = list(result["detail"])
    for season in seasons:
        entry: Dict[str, Any] = {}
        for key, table in rows.items():
            part = table[table["season"] == season].dropna(subset=["p_home"])
            if len(part):
                entry[key] = score_block(part[["p_home", "p_draw", "p_away"]].to_numpy(), part["y"].to_numpy(dtype=int))
        per_season[season] = entry

    def losses(key: str, ids: Optional[set] = None, scope: Optional[List[str]] = None) -> pd.DataFrame:
        table = rows[key].dropna(subset=["p_home"])
        table = table[table["season"].isin(scope or OUTER_SEASONS)]
        if ids is not None:
            table = table[table["match_id"].isin(ids)]
        return table.set_index("match_id")

    def compare(other: str, scope: List[str], need_market: bool = False) -> Optional[Dict[str, Any]]:
        model = losses("model", scope=scope)
        rival = losses(other, scope=scope)
        ids = sorted(set(model.index) & set(rival.index))
        if not ids:
            return None
        y = model.loc[ids, "y"].to_numpy(dtype=int)
        a = per_match_log_loss(model.loc[ids, ["p_home", "p_draw", "p_away"]].to_numpy(), y)
        b = per_match_log_loss(rival.loc[ids, ["p_home", "p_draw", "p_away"]].to_numpy(), y)
        return with_inference(a, b)

    outer = list(OUTER_SEASONS)
    comparisons = {
        "vs_base_rate": {"pooled_outer": compare("base_rate", outer), "hold_out": compare("base_rate", [outer[-1]])},
        "vs_elo": {"pooled_outer": compare("elo", outer), "hold_out": compare("elo", [outer[-1]])},
        "vs_market": {"pooled_outer": compare("market", outer), "hold_out": compare("market", [outer[-1]])},
    }
    apply_fdr({k: v["pooled_outer"] for k, v in comparisons.items()})

    played_goals = goals[goals["season"].isin(OUTER_SEASONS)]
    goal_summary = {
        "n": int(len(played_goals)),
        "total_goals_mae": {"model": round(float(np.abs(played_goals["lam_total"] - played_goals["total"]).mean()), 4),
                            "training_mean": round(float(np.abs(played_goals["train_total_mean"] - played_goals["total"]).mean()), 4)},
    }
    family: Dict[str, Optional[Dict[str, Any]]] = {}
    for market, actual in (("over_15", played_goals["total"] > 1), ("over_25", played_goals["total"] > 2), ("over_35", played_goals["total"] > 3), ("btts", played_goals["btts"] == 1)):
        y = actual.astype(int).to_numpy()
        probability, prior = played_goals["btts_p" if market == "btts" else market].to_numpy(), played_goals[f"train_{market}"].to_numpy()
        model_loss, prior_loss = binary_log_loss(probability, y), binary_log_loss(prior, y)
        goal_summary[market] = {"model_log_loss": round(float(model_loss.mean()), 4), "base_rate_log_loss": round(float(prior_loss.mean()), 4)}
        family[market] = goal_summary[market]["vs_base_rate"] = with_inference(model_loss, prior_loss)
    family["total_goals_mae"] = goal_summary["total_goals_mae"]["vs_training_mean"] = with_inference(
        np.abs(played_goals["lam_total"] - played_goals["total"]).to_numpy(), np.abs(played_goals["train_total_mean"] - played_goals["total"]).to_numpy())
    apply_fdr(family)  # one family: four markets and the total-goals error
    return {"per_season": per_season, "comparisons": comparisons, "goals": goal_summary}


def save_predictions(result: Dict[str, Any], path: Path) -> None:
    """Every out-of-sample prediction of the walk-forward run, for the model-audit page."""
    rows = result["rows"]
    table = None
    for key, frame in rows.items():
        part = frame.rename(columns={"p_home": f"{key}_p_home", "p_draw": f"{key}_p_draw", "p_away": f"{key}_p_away"}).drop(columns=["y"] if table is not None else [])
        table = part if table is None else table.merge(part.drop(columns=["season"]), on="match_id", how="outer")
    goals = result["goals"][["match_id", "lam_home", "lam_away"]]
    table = table.merge(goals, on="match_id", how="left")
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(path, index=False)


def goal_market_gates(goals: Dict[str, Any]) -> Dict[str, str]:
    """``model`` for a goal market whose log-loss beats the training base rate (negative paired difference, FDR-adjusted q < 0.05), else ``baseline``."""
    gates = {}
    for market in GOAL_MARKETS:
        test = (goals.get(market) or {}).get("vs_base_rate")
        gates[market] = "model" if test and test["mean_delta"] < 0 and test.get("significant_fdr_05") else "baseline"
    return gates


def decide(summary: Dict[str, Any]) -> Dict[str, Any]:
    base = summary["comparisons"]["vs_base_rate"]["pooled_outer"]
    elo = summary["comparisons"]["vs_elo"]["pooled_outer"]
    beats_base = bool(base and base["mean_delta"] < 0 and base.get("significant_fdr_05"))
    not_worse_than_elo = bool(elo and elo["mean_delta"] <= MIN_ELO_NON_INFERIORITY)
    serving = "model" if beats_base and not_worse_than_elo else "elo_baseline"
    return {"serving": serving, "goal_markets": goal_market_gates(summary.get("goals", {})),
            "beats_base_rate_significantly": beats_base, "not_worse_than_elo": not_worse_than_elo,
            "rule": "serve the model only if it beats the base rate (FDR-adjusted) and its mean log-loss is not above the Elo baseline's; otherwise serve the Elo baseline, labelled as a baseline"}


def goal_base_rates(frame: pd.DataFrame) -> Dict[str, float]:
    """Share of played matches with over 1.5 / 2.5 / 3.5 goals and both teams scoring; what a gated-out goal market serves."""
    total = frame["home_score"] + frame["away_score"]
    return {"over_15": float((total > 1).mean()), "over_25": float((total > 2).mean()), "over_35": float((total > 3).mean()),
            "btts": float(((frame["home_score"] > 0) & (frame["away_score"] > 0)).mean())}


def final_fit(frame: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
    played = frame[frame["home_score"].notna()].copy().reset_index(drop=True)
    played["y"] = outcome_label(played)
    dev = played[~played["season"].isin(LOCKED_SEASONS)].reset_index(drop=True)
    model, calibrator, name, scores = fit_outcome(dev, columns)  # the choice uses unlocked seasons only
    X, y = played[columns], played["y"]
    final_model = fit_model(candidate_models()[name], X, y)  # the locked season's played matches may still train the final fit
    elo = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(played[["elo_diff", "elo_venue_diff"]], played["y"])
    home, away, alpha = fit_goals(dev, columns)
    home = poisson_pipeline(alpha).fit(X, played["home_score"])
    away = poisson_pipeline(alpha).fit(X, played["away_score"])
    return {"model_1x2": final_model, "calibrator": calibrator, "elo_baseline": elo, "elo_columns": ["elo_diff", "elo_venue_diff"],
            "goals_home": home, "goals_away": away, "rho": RHO, "selected_model": name, "cv_log_loss": scores, "poisson_alpha": alpha,
            "base_rates": goal_base_rates(dev), "training_matches": int(len(played))}


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml (a TheStatsAPI league)")
    parser.add_argument("--no-save", action="store_true", help="only write the report, not the production artifact")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    conn = get_db()
    try:
        matches = load_league_matches(conn, comp.id)
        market = market_probabilities(conn, comp.id)
    finally:
        conn.close()
    frame = build_league_features(matches)
    columns = [c for c in feature_columns(frame) if frame[c].notna().any()]
    result = walk_forward(frame, columns, market)
    summary = summarize(result)
    decision = decide(summary)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "competition": comp.key,
        "protocol": {"warm_up_season": WARM_UP_SEASON, "outer_seasons": list(OUTER_SEASONS), "locked_monitoring": sorted(LOCKED_SEASONS),
                     "bootstrap_draws": 10000, "seed": 42, "feature_count": len(columns), "feature_set": "src/features/build_league_features.py"},
        "folds": result["detail"], **summary, "decision": decision,
    }
    out = REPORTS_DIR / "models" / f"{comp.key}_walk_forward.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Report: %s | serving: %s", out, decision["serving"])
    save_predictions(result, competition_paths(comp.key).processed / "walk_forward_predictions.parquet")  # scoring rates feed the audit page
    if not args.no_save:
        artifact = final_fit(frame, columns)
        artifact.update(feature_names=columns, decision=decision, report=str(out.name), trained_at_utc=report["generated_at_utc"])
        target = competition_paths(comp.key).models / "outcome_models_v1.joblib"
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, target)
        logger.info("Artifact: %s", target)
    goal_tests = {k: summary["goals"][k]["vs_base_rate"] for k in GOAL_MARKETS}
    goal_tests["total_goals_mae"] = summary["goals"]["total_goals_mae"]["vs_training_mean"]
    print(json.dumps({"decision": decision, "per_season": {s: v.get("model") for s, v in summary["per_season"].items()},
                      "goals_vs_base_rate": {k: {x: v[x] for x in ("mean_delta", "ci_low", "ci_high", "q_fdr")} for k, v in goal_tests.items()}}, indent=2, default=float))


if __name__ == "__main__":
    main()
