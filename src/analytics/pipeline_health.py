"""Data and model health check: coverage gaps, incomplete raw cache, stale artifacts.

Run after a sync or before a deploy:
``python3 -m src.analytics.pipeline_health [--strict] [--json]``.
Exit code 1 when a FAIL finding exists (with ``--strict`` also on WARN), so cron
and shell callers can act on it. Reads only; it never writes data or models.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_KINDS = ("stats", "stream", "details")
MIN_PAST_COVERAGE = 0.90   # xG / odds share of played matches expected for finished seasons
MODEL_STALE_DAYS = 8.0     # weekly retraining: older than this vs the newest played match is stale


def _ids(db_path: Path, sql: str) -> set[int]:
    with sqlite3.connect(db_path) as conn:
        return {int(row[0]) for row in conn.execute(sql)}


def collect(
    features_path: Path = ROOT / "data/processed/features_matches_all.parquet",
    db_path: Path = ROOT / "data/premier_league.db",
    raw_dir: Path = ROOT / "data/raw/matches",
    models_dir: Path = ROOT / "models/production",
) -> dict[str, Any]:
    """Gather coverage counts per season plus raw-file and model-age facts."""
    matches = pd.read_parquet(features_path, columns=["match_id", "season", "gameweek", "kickoff_millis", "home_score"])
    matches["season"] = matches["season"].astype(str)
    matches["played"] = matches["home_score"].notna()
    xg = _ids(db_path, "SELECT match_id FROM external_match_xg")
    odds = _ids(db_path, "SELECT match_id FROM external_match_odds WHERE bookmaker = 'Bet365'")
    db_matches = _ids(db_path, "SELECT match_id FROM matches")

    seasons: dict[str, dict[str, Any]] = {}
    for season, group in matches.groupby("season"):
        played = group[group["played"]]
        ids = set(played["match_id"].astype(int))
        missing_xg = played[~played["match_id"].astype(int).isin(xg)]
        seasons[season] = {
            "fixtures": int(len(group)),
            "played": int(len(played)),
            "with_xg": len(ids & xg),
            "with_odds": len(ids & odds),
            "xg_missing_gameweeks": sorted({int(g) for g in missing_xg["gameweek"].dropna()}),
        }

    played_ids = [int(m) for m in matches.loc[matches["played"], "match_id"]]
    raw_incomplete = [m for m in played_ids if not all((raw_dir / f"{m}_{kind}.json").exists() for kind in RAW_KINDS)]
    last_played_ms = matches.loc[matches["played"], "kickoff_millis"].max()
    last_played = pd.to_datetime(last_played_ms, unit="ms", utc=True)
    models = {
        path.name: (last_played - pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC")).total_seconds() / 86400.0
        for path in sorted(models_dir.glob("*.joblib")) if "backup" not in path.name
    }
    return {
        "seasons": seasons,
        "latest_season": max((s for s, v in seasons.items() if v["played"]), default=None),
        "last_played": last_played.isoformat(),
        "raw_incomplete": raw_incomplete,
        "features_not_in_db": sorted(set(matches["match_id"].astype(int)) - db_matches),
        "db_not_in_features": sorted(db_matches - set(matches["match_id"].astype(int))),
        "model_days_behind_last_match": models,
    }


def evaluate(report: dict[str, Any]) -> list[tuple[str, str]]:
    """Turn the collected facts into (level, message) findings; level is FAIL or WARN."""
    findings: list[tuple[str, str]] = []
    if report["raw_incomplete"]:
        sample = ", ".join(map(str, report["raw_incomplete"][:5]))
        findings.append(("FAIL", f"{len(report['raw_incomplete'])} played matches lack stats/stream/details files (e.g. {sample})"))
    for key, text in (("features_not_in_db", "in features but not in the database"), ("db_not_in_features", "in the database but not in features")):
        if report[key]:
            findings.append(("FAIL", f"{len(report[key])} matches {text} (e.g. {report[key][:3]})"))
    latest = report["latest_season"]
    for season, v in report["seasons"].items():
        if not v["played"]:
            continue
        for label, count in (("xG", v["with_xg"]), ("Bet365 odds", v["with_odds"])):
            share = count / v["played"]
            if label == "Bet365 odds" and count == 0 and season != latest:
                continue  # odds were never imported for this season (2022/23); nothing consumes them
            if season == latest and count < v["played"]:
                extra = f"; xG missing in gameweeks {v['xg_missing_gameweeks']}" if label == "xG" else ""
                findings.append(("WARN", f"{season}: {v['played'] - count} of {v['played']} played matches lack {label}{extra}"))
            elif season != latest and share < MIN_PAST_COVERAGE:
                findings.append(("WARN", f"{season}: {label} coverage {share:.0%} is below {MIN_PAST_COVERAGE:.0%}"))
    for name, days in report["model_days_behind_last_match"].items():
        if days > MODEL_STALE_DAYS:
            findings.append(("WARN", f"{name} was written {days:.1f} days before the newest played match; retrain"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 1 on WARN as well as FAIL")
    parser.add_argument("--json", action="store_true", help="print the raw report and findings as JSON")
    args = parser.parse_args()
    report = collect()
    findings = evaluate(report)
    if args.json:
        print(json.dumps({"report": report, "findings": findings}, indent=2, default=str))
    else:
        print(f"Newest played match: {report['last_played']}\n")
        print(f"{'season':8} {'fixtures':>8} {'played':>7} {'xG':>5} {'odds':>5}")
        for season, v in report["seasons"].items():
            print(f"{season:8} {v['fixtures']:>8} {v['played']:>7} {v['with_xg']:>5} {v['with_odds']:>5}")
        print()
        for level, message in findings:
            print(f"[{level}] {message}")
        print("OK: no findings" if not findings else f"{len(findings)} finding(s)")
    failed = any(level == "FAIL" for level, _ in findings) or (args.strict and bool(findings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
