"""Generate the current, compact data inventory used by model training."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "data_quality.md"

TRACKED_METRICS = {
    "corners": "won_corners",
    "throw-ins": "total_throws",
    "saves": "saves",
    "yellow cards": "total_yel_card",
    "red cards": "total_red_card",
    "offsides": "total_offside",
    "shots": "total_scoring_att",
    "possession": "possession_percentage",
    "xG proxy: inside-box shots on target": "att_ibox_target",
    "xG proxy: outside-box shots on target": "att_obox_target",
    "xG proxy: big chances": "big_chance_created",
}


def _fixtures(season: str) -> list[dict[str, Any]]:
    path = RAW / f"fixtures_{season}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("content", [])


def _completed(fixture: dict[str, Any]) -> bool:
    teams = fixture.get("teams") or []
    return len(teams) >= 2 and all(team.get("score") is not None for team in teams[:2])


def _raw_metric_coverage(fixtures: list[dict[str, Any]]) -> tuple[dict[str, int], int]:
    counts = {metric: 0 for metric in TRACKED_METRICS.values()}
    denominator = 0
    for fixture in fixtures:
        if not _completed(fixture):
            continue
        denominator += 2
        stats_path = RAW / "matches" / f"{int(fixture['id'])}_stats.json"
        if not stats_path.exists():
            continue
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
        stats = payload.get("data") or {}
        for team in fixture["teams"][:2]:
            team_id = str(int(team.get("team", {}).get("id", 0)))
            metrics = stats.get(team_id, {}).get("M", [])
            present_names = {
                row.get("name") for row in metrics
                if isinstance(row, dict) and row.get("value") is not None
            }
            for metric in counts:
                counts[metric] += int(metric in present_names)
    return counts, denominator


def build_report() -> str:
    seasons = tuple(sorted(
        path.stem.removeprefix("fixtures_")
        for path in RAW.glob("fixtures_*.json")
    ))
    season_rows: list[tuple[str, int, int, int, int, int, int]] = []
    all_fixtures: list[dict[str, Any]] = []
    duplicate_ids = 0
    seen_ids: set[int] = set()

    for season in seasons:
        fixtures = _fixtures(season)
        completed = sum(_completed(fixture) for fixture in fixtures)
        for fixture in fixtures:
            match_id = int(fixture["id"])
            duplicate_ids += int(match_id in seen_ids)
            seen_ids.add(match_id)
        all_fixtures.extend(fixtures)
        stats_count = sum(
            (RAW / "matches" / f"{int(fixture['id'])}_stats.json").exists()
            for fixture in fixtures if _completed(fixture)
        )
        stream_count = sum(
            (RAW / "matches" / f"{int(fixture['id'])}_stream.json").exists()
            for fixture in fixtures if _completed(fixture)
        )
        details_count = sum(
            (RAW / "matches" / f"{int(fixture['id'])}_details.json").exists()
            for fixture in fixtures if _completed(fixture)
        )
        season_rows.append((season, len(fixtures), completed, stats_count, stream_count, details_count, len(fixtures) - completed))

    summary_path = PROCESSED / "matches_summary_all.parquet"
    summary = pd.read_parquet(summary_path) if summary_path.exists() else pd.DataFrame()
    if not summary.empty:
        played = summary[
            summary["home_score"].notna() & summary["away_score"].notna()
        ].copy()
    else:
        played = pd.DataFrame()

    feature_path = PROCESSED / "features_matches_all.parquet"
    feature_rows = int(pd.read_parquet(feature_path).shape[0]) if feature_path.exists() else 0
    unknown_referees = 0
    if not played.empty and "referee_name" in played:
        unknown_referees = int(
            played["referee_name"].fillna("Unknown").astype(str).str.strip().str.lower().isin(["", "unknown"]).sum()
        )

    lines = [
        "# Data Quality and Coverage",
        "",
        f"Snapshot generated {date.today().isoformat()} from the local fixture cache and processed tables.",
        "Run `python3 -m src.analytics.data_quality_report` to refresh this report.",
        "",
        "## Match and source coverage",
        "",
        "| Season | Fixtures | Completed | Upcoming | Stats files | Event streams | Details files |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for season, total, completed, stats, streams, details, upcoming in season_rows:
        lines.append(
            f"| {season.replace('_', '-')} | {total} | {completed} | {upcoming} | {stats}/{completed} | "
            f"{streams}/{completed} | {details}/{completed} |"
        )

    lines.extend([
        "",
        f"- Combined match table: {len(summary):,} rows; {len(played):,} rows have both final scores.",
        f"- Combined feature table: {feature_rows:,} rows.",
        f"- Duplicate fixture IDs across the {len(seasons)} season files: {duplicate_ids}.",
        f"- Completed matches with referee name `Unknown`: {unknown_referees}/{len(played)}.",
        "",
        "## Raw provider field coverage",
        "",
        "Coverage counts team-match rows where the raw stats response contains a non-null value. `_reported` flags describe this stats endpoint only. Missing yellow-card, red-card, and offside values are filled from the match event stream when available; source values remain in `_raw` columns. If no stream is available, an omitted red-card value retains the sparse-event zero convention.",
        "",
        "| Raw metric | Present team-match rows | Coverage |",
        "|---|---:|---:|",
    ])
    coverage, denominator = _raw_metric_coverage(all_fixtures)
    for label, metric in TRACKED_METRICS.items():
        present = coverage[metric]
        pct = f"{present / denominator:.1%}" if denominator else "—"
        lines.append(f"| `{metric}` ({label}) | {present}/{denominator} | {pct} |")

    target_columns = [
        "total_corners", "total_throws", "total_saves", "total_cards", "total_offsides", "total_goals"
    ]
    lines.extend([
        "",
        "## Event-based label recovery",
        "",
        "The PulseLive match event stream contains team-attributed yellow-card, red-card, and offside events. For a missing stats-endpoint value, processing fills the effective metric from that match's event stream and records an `_event_reconstructed` flag; the original provider value remains in a `_raw` column and `_reported` continues to indicate stats-endpoint coverage. Existing reported stats values take precedence.",
        "",
        "| Target | Stats API complete match labels | Reconstructed team values | Usable match labels |",
        "|---|---:|---:|---:|",
    ])
    if not played.empty:
        recovery_rows = [
            ("Cards", ("home_total_yel_card_event_reconstructed", "away_total_yel_card_event_reconstructed", "home_total_red_card_event_reconstructed", "away_total_red_card_event_reconstructed"), "total_yellow_cards_reported", "total_cards_target_usable"),
            ("Offsides", ("home_total_offside_event_reconstructed", "away_total_offside_event_reconstructed"), "total_offsides_reported", "total_offsides_target_usable"),
        ]
        for label, reconstructed_columns, source_flag, usable_flag in recovery_rows:
            reconstructed = sum(
                int(played[column].fillna(False).astype(bool).sum())
                for column in reconstructed_columns
                if column in played
            )
            source_complete = int(played[source_flag].fillna(False).astype(bool).sum()) if source_flag in played else 0
            usable_labels = int(played[usable_flag].fillna(False).astype(bool).sum()) if usable_flag in played else 0
            lines.append(f"| {label} | {source_complete} | {reconstructed} | {usable_labels} |")

    lines.extend([
        "",
        "## Current target distributions",
        "",
        "| Target | Complete-label rows | Mean | Variance / mean |",
        "|---|---:|---:|---:|",
    ])
    if not played.empty:
        for column in target_columns:
            if column not in played:
                continue
            values = pd.to_numeric(played[column], errors="coerce").dropna()
            mean = float(values.mean()) if len(values) else float("nan")
            variance_ratio = float(values.var() / mean) if len(values) and mean > 0 else float("nan")
            lines.append(
                f"| `{column}` | {len(values)} | {mean:.3f} | {variance_ratio:.3f} |"
            )

    missingness_targets = {
        "Corners": ("total_corners_reported", "home_won_corners_reported", "away_won_corners_reported"),
        "Throw-ins": ("total_throws_reported", "home_total_throws_reported", "away_total_throws_reported"),
        "Saves": ("total_saves_reported", "home_saves_reported", "away_saves_reported"),
        "Cards": ("total_cards_target_usable", "home_total_cards_usable", "away_total_cards_usable"),
        "Offsides": ("total_offsides_target_usable", "home_total_offside_usable", "away_total_offside_usable"),
    }
    lines.extend([
        "",
        "## Missing-stat selection audit",
        "",
        "For each target, complete and incomplete match samples are compared by season and by match outcome. Team rates include home and away appearances; teams need at least 20 appearances to enter the ranking. The team table includes only targets with at least one missing team value.",
        "",
        "| Target | Season | Played matches | Complete labels | Missing labels | Missing rate |",
        "|---|---|---:|---:|---:|---:|",
    ])
    if not played.empty:
        for target, (match_flag, _, _) in missingness_targets.items():
            if match_flag in played:
                complete_mask = played[match_flag].fillna(False).astype(bool)
            else:
                target_column = {
                    "Corners": "total_corners", "Throw-ins": "total_throws", "Saves": "total_saves",
                    "Cards": "total_cards", "Offsides": "total_offsides",
                }[target]
                complete_mask = played[target_column].notna()
            for season, season_rows in played.groupby(played["season"].astype(str), sort=True):
                n = len(season_rows)
                complete_n = int(complete_mask.loc[season_rows.index].sum())
                missing_n = n - complete_n
                lines.append(
                    f"| {target} | {season.replace('_', '-')} | {n} | {complete_n} | {missing_n} | "
                    f"{missing_n / n:.1%} |" if n else
                    f"| {target} | {season.replace('_', '-')} | 0 | 0 | 0 | — |"
                )

        lines.extend([
            "",
            "### Missingness versus match outcome",
            "",
            "| Target | Label coverage | Sample | Home win | Draw | Away win | Mean total goals |",
            "|---|---:|---|---:|---:|---:|---:|",
        ])
        for target, (match_flag, _, _) in missingness_targets.items():
            if match_flag in played:
                complete_mask = played[match_flag].fillna(False).astype(bool)
            else:
                target_column = {
                    "Corners": "total_corners", "Throw-ins": "total_throws", "Saves": "total_saves",
                    "Cards": "total_cards", "Offsides": "total_offsides",
                }[target]
                complete_mask = played[target_column].notna()
            for label, mask in (("Complete", complete_mask), ("Missing", ~complete_mask)):
                sample = played.loc[mask]
                if sample.empty:
                    continue
                total = (sample["home_score"] + sample["away_score"]).mean()
                home_win = (sample["home_score"] > sample["away_score"]).mean()
                draw = (sample["home_score"] == sample["away_score"]).mean()
                away_win = (sample["home_score"] < sample["away_score"]).mean()
                coverage_pct = float(complete_mask.mean())
                lines.append(
                    f"| {target} | {coverage_pct:.1%} | {label} ({len(sample)}) | {home_win:.1%} | "
                    f"{draw:.1%} | {away_win:.1%} | {total:.3f} |"
                )

        lines.extend([
            "",
            "### Teams with the highest missing rates",
            "",
            "| Target | Team | Appearances | Missing | Missing rate |",
            "|---|---|---:|---:|---:|",
        ])
        for target, (_, home_flag, away_flag) in missingness_targets.items():
            team_rows = []
            for name_column, flag_column in (("home_name", home_flag), ("away_name", away_flag)):
                if name_column not in played or flag_column not in played:
                    continue
                side_rows = played[[name_column, flag_column]].rename(
                    columns={name_column: "team", flag_column: "reported"}
                )
                side_rows["reported"] = side_rows["reported"].fillna(False).astype(bool)
                team_rows.append(side_rows)
            if not team_rows:
                continue
            team_coverage = pd.concat(team_rows, ignore_index=True).groupby("team")["reported"].agg(
                appearances="size", complete="sum"
            )
            team_coverage["missing"] = team_coverage["appearances"] - team_coverage["complete"]
            team_coverage = team_coverage[team_coverage["appearances"] >= 20].copy()
            if team_coverage.empty or int(team_coverage["missing"].sum()) == 0:
                continue
            team_coverage["missing_rate"] = team_coverage["missing"] / team_coverage["appearances"]
            for team, row in team_coverage.sort_values(
                ["missing_rate", "missing", "appearances"], ascending=[False, False, False]
            ).head(5).iterrows():
                lines.append(
                    f"| {target} | {team} | {int(row['appearances'])} | {int(row['missing'])} | "
                    f"{row['missing_rate']:.1%} |"
                )

    lines.extend([
        "",
        "## Known data limits",
        "",
        "- Training excludes rows when a target remains unavailable. Cards and offsides now use event-derived fallbacks for missing stats values; corners and saves still have incomplete target coverage and can select for matches with better provider coverage.",
        "- Event-derived values fill only missing yellow-card, red-card, and offside stats. The source metric remains available in a `_raw` column, and provider coverage remains visible through `_reported` flags. A match without a usable event stream and without the provider value can still have a missing target.",
        "- The historical `home_xg`, `away_xg`, and `total_xg` columns are an aggregate-stat proxy. It is produced only when all required inputs are present; it is not official Opta shot-level xG or a trained xG model.",
        "- The current season is incomplete. Its season holdout is marked partial and should not be compared as if it were a full-season result.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(), encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
