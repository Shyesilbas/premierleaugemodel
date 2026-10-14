#!/usr/bin/env python3
"""Rebuild processed data, train all prediction families, and refresh reports.

This pipeline uses the existing local raw-data cache; it does not contact the provider.
"""

import json
import logging
from pathlib import Path

from src.processing.process_season_data import main as run_processing
from src.features.build_features import build_feature_dataset
from src.models.train_corners import train_corners_model
from src.models.train_throws import train_throws_model
from src.models.train_saves import train_saves_model
from src.models.train_cards import train_cards_model
from src.models.train_offsides import train_offsides_model
from src.models.train_match_outcome import train_match_outcome_models
from src.models.evaluate_goal_models import main as evaluate_goal_model_candidates
from src.models.train_goals import train_goals_models
from src.analytics.data_quality_report import main as run_data_quality_report
from src.analytics.team_data_audit import main as run_team_data_audit
from src.analytics.audit_team_scenarios import main as run_team_scenario_audit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("master_pipeline")


def generate_outer_validation_sections() -> list[str]:
    """Render goal-market and 1X2 ensemble outer-season tables from eval JSONs."""
    lines: list[str] = []
    goal_eval_path = Path("data/processed/goal_model_outer_eval.json")
    if goal_eval_path.exists():
        goal_eval = json.loads(goal_eval_path.read_text(encoding="utf-8"))
        goal_rows = goal_eval.get("outer_season_results", [])
        gate_rows = goal_eval.get("o25_candidate_gates", {})
        selected_goal_model = "blend_dc_feat" if "blend_dc_feat" in gate_rows else next(iter(gate_rows), "blend_dc_feat")
        selected_names = {"prior", selected_goal_model}
        if any(row.get("model") == "logreg_o25" for row in goal_rows):
            selected_names.add("logreg_o25")
        lines.extend([
            "",
            "## Goal-market outer-season log loss",
            "",
            "Whole-season holdouts from `goal_model_outer_eval.json`; negative Δ favors the candidate over the season prior.",
            "",
            "| Market | Holdout season | Model | Matches | Log loss | Δ vs season prior | 95% CI |",
            "|---|---|---|---:|---:|---:|---:|",
        ])
        for result in goal_rows:
            if result.get("model") not in selected_names:
                continue
            lines.append(
                f"| {result['target']} | {result['season']} | `{result['model']}` | {result['n']} | "
                f"{result['log_loss']:.4f} | {result['delta_vs_prior']:+.4f} | "
                f"[{result['ci_low']:+.4f}, {result['ci_high']:+.4f}] |"
            )

    ensemble_eval_path = Path("data/processed/1x2_ensemble_outer_eval.json")
    if ensemble_eval_path.exists():
        ensemble_eval = json.loads(ensemble_eval_path.read_text(encoding="utf-8"))
        lines.extend([
            "",
            "## 1X2 ensemble outer-season comparison",
            "",
            "Evaluation only; the ensemble did not pass its production gate and is not in the current API artifact.",
            "",
            "| Holdout season | Matches | DC weight | Logistic log loss | Ensemble log loss | Δ ensemble − logistic | 95% paired CI |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for result in ensemble_eval.get("season_holdouts", []):
            bootstrap = result.get("bootstrap_vs_logreg", {})
            lines.append(
                f"| {result['season']} | {result['test_samples']} | {result['weight_logreg']:.2f} | "
                f"{result['logreg_log_loss']:.4f} | {result['ensemble_log_loss']:.4f} | "
                f"{result['delta_log_loss']:+.4f} | "
                f"[{bootstrap.get('ci_low', float('nan')):+.4f}, {bootstrap.get('ci_high', float('nan')):+.4f}] |"
            )
        lines.append(
            f"\nGate: {'passed' if ensemble_eval.get('gate_passed') else 'failed'}; "
            f"{ensemble_eval.get('seasons_better_than_logreg', 0)}/"
            f"{ensemble_eval.get('full_seasons', 0)} seasons improved; mean log-loss Δ "
            f"{ensemble_eval.get('mean_delta_log_loss', float('nan')):+.4f}."
        )
    return lines


def generate_benchmark_report(corner_res, throws_res, saves_res, cards_res, offsides_res, outcome_res, output_path: Path):
    """Write the single benchmark report from the current training run."""
    rows = [
        ("Corners", corner_res),
        ("Throw-ins", throws_res),
        ("Saves", saves_res),
        ("Cards", cards_res.get("metrics", cards_res)),
        ("Offsides", offsides_res),
    ]
    played_rows = int(outcome_res.get("played_matches_total", max(
        int(corner_res["train_samples"]) + int(corner_res["test_samples"]),
        int(outcome_res["model_1x2"]["n_train_final"]),
    )))
    season_count = sum(1 for _ in Path("data/raw").glob("fixtures_*.json"))
    lines = [
        "# Model Benchmark Report",
        "",
        f"Current local dataset snapshot: {played_rows:,} completed matches across {season_count} seasons.",
        "This report is regenerated by `python3 run_full_pipeline.py`.",
        "",
        "## Evaluation protocol",
        "",
        "- Matches are sorted by kickoff. The first 80% form the development period; the final 20% are a chronological holdout.",
        "- Candidate models are selected only within the development period using four expanding-window time-series folds.",
        "- A feature-based regression candidate is used only if its CV RMSE beats the fold-fitted training mean by at least 0.5% and wins at least 3 of 4 folds; otherwise the final estimator is `training_mean`.",
        f"- For the 1X2 and Over 2.5 classifiers, locked seasons are excluded from model selection, calibration, and evaluation: `{outcome_res.get('locked_seasons_excluded', [])}` ({outcome_res.get('locked_season_matches_excluded', 0)} played matches). These played matches may be used to fit the final production estimators.",
        "- Regression-family holdouts still follow their existing protocol and include the latest partial season; do not treat those rows as locked-season validation.",
        "- The selected candidate is evaluated once on the holdout. Regression preprocessing is fitted inside each fold; Ridge candidates standardize features.",
        "- The production 1X2 fit currently excludes 2022-23 labels; those matches remain in rolling feature history. An outer-season comparison measures that rule, recent windows, recency weights, and draw-balance features. Other model families refit on all eligible completed rows.",
        "- The 1X2 and Over 2.5 production probability calibrators use forward-only out-of-fold predictions from eligible unlocked seasons; the locked season is not used to calibrate them.",
        "- The holdout scores describe the selected training procedure, not the all-data production artifact.",
        "",
        "## Regression results",
        "",
        "| Target | Raw CV winner | Selected model | Skill decision | Features | Dev rows | Holdout rows | CV RMSE | Holdout RMSE | Mean baseline RMSE | Holdout MAE | Mean baseline MAE | R² |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in rows:
        baseline_rmse = metrics["baseline_test_rmse"]
        baseline_mae = metrics["baseline_test_mae"]
        selected_cv = metrics["cv_rmse"][metrics["selected_model"]]
        raw_selected = metrics.get("raw_selected_model", metrics["selected_model"])
        if metrics["selected_model"] == "training_mean":
            skill_decision = "gate fallback to mean" if metrics.get("skill_gate_applied") else "mean won CV"
        elif metrics.get("skill_gate_applied"):
            skill_decision = "failed → mean"
        else:
            skill_decision = "gate passed"
        lines.append(
            f"| {name} | `{raw_selected}` | `{metrics['selected_model']}` | {skill_decision} | "
            f"{metrics['n_features']} | {metrics['train_samples']} | "
            f"{metrics['test_samples']} | {selected_cv:.4f} | "
            f"{metrics['test_rmse']:.4f} | {baseline_rmse:.4f} | {metrics['test_mae']:.4f} | "
            f"{baseline_mae:.4f} | {metrics['test_r2']:.4f} |"
        )

    lines.extend([
        "",
        "## Season-by-season regression holdouts",
        "",
        "Each row trains on all earlier seasons only. The current incomplete season is provisional.",
        "",
        "| Target | Holdout season | Raw CV winner | Selected model | Gate fallback | Matches | Prior training matches | RMSE | Mean baseline RMSE | MAE | Mean baseline MAE |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, metrics in rows:
        for result in metrics.get("season_holdouts", []):
            season_label = result["season"] + (" (partial)" if result["partial_season"] else "")
            lines.append(
                f"| {name} | {season_label} | `{result.get('raw_selected_model', result['selected_model'])}` | "
                f"`{result['selected_model']}` | {'yes' if result.get('skill_gate_applied') else 'no'} | "
                f"{result['test_samples']} | {result['train_samples']} | "
                f"{result['rmse']:.4f} | {result['baseline_rmse']:.4f} | {result['mae']:.4f} | "
                f"{result['baseline_mae']:.4f} |"
            )

    lines.extend([
        "",
        "## Classification results",
        "",
        "| Target | Selected model | Dev rows | Holdout rows | CV log loss | Raw holdout log loss | Calibrated holdout log loss | Prior baseline log loss | Raw accuracy | Calibrated accuracy | Brier | Prior baseline Brier |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for key, label in (("model_1x2", "1X2 result"), ("model_over_2_5", "Over 2.5 goals")):
        m = outcome_res[key]
        lines.append(
            f"| {label} | `{m['selected_model']}` | {m['development_samples']} | {m['test_samples']} | "
            f"{m['cv_log_loss']:.4f} | {m['raw_log_loss']:.4f} | "
            f"{m['log_loss']:.4f} | {m['baseline_log_loss']:.4f} | {m['raw_test_accuracy_pct']:.2f}% | "
            f"{m['test_accuracy_pct']:.2f}% | "
            f"{m['brier_score']:.4f} | {m['baseline_brier_score']:.4f} |"
        )

    lines.extend(generate_outer_validation_sections())

    lines.extend([
        "",
        "## Paired bootstrap and reliability",
        "",
        "Bootstrap deltas use calibrated holdout probabilities and paired per-match log loss. Negative mean delta favors the model; a 95% interval that crosses zero does not establish a clear improvement over the class-prior baseline.",
        "",
        "| Target | Mean Δ loss | 95% CI low | 95% CI high | P(model better) | Matches | ECE |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for key, label, ece_key in (
        ("model_1x2", "1X2 result", "draw_expected_calibration_error"),
        ("model_over_2_5", "Over 2.5 goals", "expected_calibration_error"),
    ):
        metrics = outcome_res[key]
        bootstrap = metrics["bootstrap_vs_prior"]
        lines.append(
            f"| {label} | {bootstrap['mean_delta']:.4f} | {bootstrap['ci_low']:.4f} | "
            f"{bootstrap['ci_high']:.4f} | {bootstrap['p_a_better']:.3f} | {bootstrap['n']} | "
            f"{metrics[ece_key]:.4f} |"
        )

    reliability_tables = (
        ("Over 2.5 event probability", outcome_res["model_over_2_5"]["reliability"]),
        ("1X2 draw probability", outcome_res["model_1x2"]["reliability_draw"]),
    )
    for title, reliability in reliability_tables:
        lines.extend([
            "",
            f"### Reliability: {title}",
            "",
            "| Predicted-probability bin | Matches | Mean predicted | Observed rate |",
            "|---|---:|---:|---:|",
        ])
        for row in reliability:
            lines.append(
                f"| {row['bin']} | {row['n']} | {row['mean_predicted']:.4f} | {row['observed_rate']:.4f} |"
            )

    draw_metrics = outcome_res["model_1x2"]
    lines.extend([
        "",
        "### 1X2 draw-specific holdout diagnostics",
        "",
        "These metrics use calibrated probabilities from the same untouched chronological holdout.",
        "",
        "| Actual P(D) | Mean P(D) | Mean P(D) on draws | Mean P(D) on other matches | Draw Brier | Draw AUC | Argmax draw picks |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {draw_metrics['actual_draw_rate']:.1%} | {draw_metrics['mean_draw_probability']:.1%} | "
        f"{draw_metrics['mean_draw_probability_on_draws']:.1%} | "
        f"{draw_metrics['mean_draw_probability_on_non_draws']:.1%} | "
        f"{draw_metrics['draw_brier_score']:.4f} | {draw_metrics['draw_auc']:.4f} | "
        f"{draw_metrics['pred_distribution'].get(1, 0)} |",
    ])

    dc = outcome_res["dixon_coles_1x2"]
    lines.extend([
        "",
        "## Dixon–Coles 1X2 baseline",
        "",
        "This scoreline model estimates team attack/defence strengths and home advantage, then applies the low-score Dixon–Coles correction. It is fitted on prior matches only and evaluated on the same chronological holdouts as the classifier. Calibration uses forward-only development predictions.",
        "",
        "| Holdout | Matches | Raw log loss | Calibrated log loss | Prior log loss | Raw accuracy | Calibrated accuracy | Raw Brier | Calibrated Brier | Calibrated draw picks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Main chronological | {dc['test_samples']} | {dc['raw']['log_loss']:.4f} | {dc['calibrated']['log_loss']:.4f} | {dc['prior_log_loss']:.4f} | {dc['raw']['accuracy_pct']:.2f}% | {dc['calibrated']['accuracy_pct']:.2f}% | {dc['raw']['brier']:.4f} | {dc['calibrated']['brier']:.4f} | {dc['calibrated']['pred_distribution'].get(1, 0)} |",
        "",
        f"Fitted parameters: {dc['model_parameters']}.",
        "",
        "| Holdout season | Matches | Prior training matches | Raw log loss | Calibrated log loss | Prior log loss | Raw accuracy | Calibrated accuracy | Calibrated draw picks |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for result in dc["season_holdouts"]:
        season_label = result["season"] + (" (partial)" if result["partial_season"] else "")
        lines.append(
            f"| {season_label} | {result['test_samples']} | {result['train_samples']} | "
            f"{result['raw']['log_loss']:.4f} | {result['calibrated']['log_loss']:.4f} | "
            f"{result['prior_log_loss']:.4f} | {result['raw']['accuracy_pct']:.2f}% | "
            f"{result['calibrated']['accuracy_pct']:.2f}% | {result['calibrated']['pred_distribution'].get(1, 0)} |"
        )

    lines.extend([
        "",
        "## Season-by-season classification holdouts",
        "",
        "Each season is evaluated using only earlier seasons for candidate selection, calibration, and fitting.",
        "",
        "| Target | Holdout season | Matches | Prior training matches | Raw log loss | Calibrated log loss | Prior baseline log loss | Raw accuracy | Calibrated accuracy |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for key, label in (("model_1x2", "1X2 result"), ("model_over_2_5", "Over 2.5 goals")):
        for result in outcome_res[key].get("season_holdouts", []):
            season_label = result["season"] + (" (partial)" if result["partial_season"] else "")
            lines.append(
                f"| {label} | {season_label} | {result['test_samples']} | {result['train_samples']} | "
                f"{result['raw_log_loss']:.4f} | {result['calibrated_log_loss']:.4f} | {result['prior_log_loss']:.4f} | "
                f"{result['raw_accuracy_pct']:.2f}% | {result['calibrated_accuracy_pct']:.2f}% |"
            )

    variant_results = outcome_res.get("1x2_variant_outer_holdouts", [])
    policy_labels = {
        "all_prior": "All prior seasons",
        "exclude_2022_23": "Exclude 2022/23 labels",
        "latest_two_seasons": "Latest two prior seasons",
        "recency_half_life_1_5": "Recency weights (1.5-season half-life)",
    }
    lines.extend([
        "",
        "## 1X2 history-window and draw-feature comparison",
        "",
        "Each row is a whole-season outer holdout. The estimator is fixed at `logreg_C0.003` to isolate training-window/weighting and feature changes; calibration is fitted from forward OOF predictions in that row's training period. The draw-balance ablation measures whether absolute team-strength gaps and expected scoring balance add signal. The 2026/27 sample is partial. These are diagnostics, not an automatic production-policy selection.",
        "",
        "| Holdout | Training policy | Features | Train rows | Log loss | Multiclass Brier | Draw Brier | Draw AUC | Actual P(D) | Mean P(D) | Draw picks |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for result in variant_results:
        season_label = result["season"] + (" (partial)" if result["partial_season"] else "")
        feature_label = {
            "all_features": "All",
            "without_xg_proxy": "Without legacy xG proxy features",
            "without_draw_balance": "Without draw-balance features",
        }.get(result["features"], result["features"])
        lines.append(
            f"| {season_label} | {policy_labels.get(result['policy'], result['policy'])} | {feature_label} | "
            f"{result['train_samples']} | {result['log_loss']:.4f} | {result['multiclass_brier']:.4f} | "
            f"{result['draw_brier']:.4f} | {result['draw_auc']:.4f} | {result['actual_draw_rate']:.1%} | "
            f"{result['mean_draw_probability']:.1%} | {result['predicted_draws']} |"
        )

    lines.extend([
        "",
        "## Count-threshold probability scores",
        "",
        "Threshold probabilities are evaluated on the main holdout using dispersion estimated only from development targets.",
        "",
        "| Target | Event | NB2 log loss | Poisson log loss | Prior log loss | NB2 Brier | Poisson Brier | Prior Brier |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for name, metrics in rows:
        for event, scores in metrics.get("count_threshold_metrics", {}).items():
            nb = scores["negative_binomial"]
            poi = scores["poisson"]
            prior = scores["prior"]
            lines.append(
                f"| {name} | {event} | {nb['log_loss']:.4f} | {poi['log_loss']:.4f} | {prior['log_loss']:.4f} | "
                f"{nb['brier']:.4f} | {poi['brier']:.4f} | {prior['brier']:.4f} |"
            )

    lines.extend([
        "",
        "## Read this before using the scores",
        "",
        "- The primary results are from one chronological holdout. Season-by-season results above are repeated out-of-time checks; the latest partial season is provisional.",
        "- Regression candidate selection includes a training-period mean predictor in every expanding-window fold. A feature model is selected only when it beats that baseline on development CV; this avoids choosing a more complex model when the available signals do not generalize.",
        "- The low-coverage aggregate xG proxy was removed from active features and API output in F7. The outer-season report retains earlier proxy-ablation results as historical diagnostics, not as a statement about current production features.",
        "- Count-threshold predictions use an NB2 distribution with dispersion estimated on training data. Holdout scores compare NB2 and Poisson probabilities with the training-rate baseline; larger samples are still needed to judge calibration.",
        f"- 1X2 holdout predicted-class counts: `{outcome_res['model_1x2']['pred_distribution']}`; observed counts: `{outcome_res['model_1x2']['actual_distribution']}`. The classifier's argmax rarely selects draws, so inspect draw-specific scores alongside overall proper scores.",
        f"- On the same main holdout, calibrated Dixon–Coles log loss was {dc['calibrated']['log_loss']:.4f} versus {outcome_res['model_1x2']['log_loss']:.4f} for the current classifier and {dc['prior_log_loss']:.4f} for the class-prior baseline. It beats the prior but does not replace the current model.",
        "- There is no trained xG model in this repository. The `home_xg` / `away_xg` fields are a hand-built proxy from aggregate shot counts and big chances, not Opta shot-level xG; the old MAE claim was unsupported and has been removed.",
        "- Curated feature names live in each `src/models/train_*.py` file. Missing declared features now stop training instead of being silently dropped.",
        "",
        "## Production artifacts",
        "",
        f"The API loads the current `.joblib` files from `models/production/`. Holdout metrics use a development-only calibrator. Production calibrators use forward OOF predictions from all eligible training matches (1X2: {outcome_res['model_1x2']['production_calibration_oof_samples']}/{outcome_res['model_1x2']['n_train_final']}; Over 2.5: {outcome_res['model_over_2_5']['production_calibration_oof_samples']}/{outcome_res['model_over_2_5']['n_train_final']}). Run the full pipeline after data changes to rebuild features, retrain models, and refresh this report.",
        "",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Model benchmark report written to %s", output_path)


def main():
    logger.info("=== Starting Master Pipeline Execution ===")

    # Step 1: Processing & Audit
    logger.info("--- Running Phase 2: Processing & Audit ---")
    run_processing()

    # Step 2: Feature Engineering
    logger.info("--- Running Phase 3: Feature Engineering ---")
    matches_parquet = Path("data/processed/matches_summary_all.parquet")
    features_parquet = Path("data/processed/features_matches_all.parquet")
    build_feature_dataset(matches_parquet, features_parquet)

    logger.info("--- Refreshing current data and event audits ---")
    run_data_quality_report()
    run_team_data_audit()
    run_team_scenario_audit()

    # Step 3: Model Training
    logger.info("--- Running Phase 4: Model Training ---")
    corner_res = train_corners_model()
    throws_res = train_throws_model()
    saves_res = train_saves_model()
    cards_res = train_cards_model()
    offsides_res = train_offsides_model()
    outcome_res = train_match_outcome_models()
    logger.info("--- Evaluating and training the production goal-matrix model ---")
    evaluate_goal_model_candidates()
    train_goals_models()

    # Step 4: Benchmark Report
    bench_report = Path("reports/model_benchmarks.md")
    generate_benchmark_report(corner_res, throws_res, saves_res, cards_res, offsides_res, outcome_res, bench_report)

    logger.info("=== Master Pipeline Complete! ===")


if __name__ == "__main__":
    main()
