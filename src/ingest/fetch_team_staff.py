#!/usr/bin/env python3
"""Fetch PulseLive team officials and squad data for a Premier League season."""

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_season_data import BASE_API_URL, build_session  # noqa: E402

logger = logging.getLogger("fetch_team_staff")


def load_fixtures(path: Path) -> List[Dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if isinstance(payload, dict):
        payload = payload.get("content", [])
    if not isinstance(payload, list):
        raise ValueError(f"Fixture file must contain a list: {path}")
    return payload


def get_season_and_teams(fixtures: List[Dict[str, Any]]) -> Tuple[int, Dict[int, str]]:
    teams: Dict[int, str] = {}
    season_ids = set()
    for fixture in fixtures:
        comp_season = (fixture.get("gameweek") or {}).get("compSeason") or {}
        if comp_season.get("id") is not None:
            season_ids.add(int(comp_season["id"]))
        for entry in fixture.get("teams", []):
            team = entry.get("team") or {}
            club = team.get("club") or {}
            raw_id = team.get("id", club.get("id"))
            if raw_id is not None:
                teams[int(raw_id)] = club.get("name") or team.get("name") or str(raw_id)
    if len(season_ids) != 1:
        raise ValueError(f"Expected one competition season in fixtures, found: {sorted(season_ids)}")
    if not teams:
        raise ValueError("No team IDs found in fixtures")
    return season_ids.pop(), teams


def fetch_team_staff(session: requests.Session, team_id: int, comp_season_id: int) -> Dict[str, Any]:
    url = f"{BASE_API_URL}/teams/{team_id}/compseasons/{comp_season_id}/staff"
    response = session.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected staff response for team {team_id}: expected an object")
    return data


def run(
    season_name: str,
    fixtures_path: Path,
    output_path: Path,
    comp_season_id: Optional[int] = None,
    delay: float = 0.1,
) -> Dict[str, Any]:
    fixtures = load_fixtures(fixtures_path)
    fixture_season_id, teams = get_season_and_teams(fixtures)
    season_id = comp_season_id or fixture_season_id

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        try:
            with output_path.open(encoding="utf-8") as stream:
                result = json.load(stream)
        except (OSError, json.JSONDecodeError):
            logger.warning("Existing output is unreadable; starting a fresh file")
            result = {}
    else:
        result = {}
    season_data = result.setdefault(season_name, {})

    session = build_session()
    errors = []
    for index, (team_id, team_name) in enumerate(sorted(teams.items()), start=1):
        try:
            staff = fetch_team_staff(session, team_id, season_id)
            # Keep the API response intact (including officials and players) while
            # adding a stable team name for consumers of the generated bundle.
            staff.setdefault("team_name", team_name)
            season_data[str(team_id)] = staff
            logger.info("[%d/%d] Fetched %s (%s)", index, len(teams), team_name, team_id)
        except (requests.RequestException, ValueError) as exc:
            errors.append({"team_id": team_id, "team_name": team_name, "error": str(exc)})
            logger.error("Failed to fetch %s (%s): %s", team_name, team_id, exc)
        if delay > 0 and index < len(teams):
            time.sleep(delay)

    result[season_name] = dict(sorted(season_data.items(), key=lambda item: int(item[0])))
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary_path.replace(output_path)
    logger.info("Saved %d team records to %s", len(season_data), output_path)
    if errors:
        raise RuntimeError(f"{len(errors)} of {len(teams)} team requests failed; see log above")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default="2026_27", help="Season label, for example 2025_26")
    parser.add_argument("--comp-season-id", type=int, help="Override the ID read from the fixture file")
    parser.add_argument("--fixtures", type=Path, help="Fixture JSON (defaults to data/raw/fixtures_{season}.json)")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/team_staff.json")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests in seconds")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    season = re.sub(r"[^0-9_-]", "", args.season)
    if not season:
        parser.error("--season must contain a valid season label")
    fixtures = args.fixtures or PROJECT_ROOT / "data/raw" / f"fixtures_{season}.json"
    try:
        run(season, fixtures, args.output, args.comp_season_id, args.delay)
    except Exception as exc:
        logger.error("Team staff ingestion failed: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
