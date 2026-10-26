"""Download a league's full-season calendar from openfootball (public domain, no key).

Usage: python3 -m src.ingest.fetch_openfootball_schedule --competition la_liga [--seasons 2026_27]

What it does: TheStatsAPI lists only the next few weeks of a running season; openfootball publishes the whole calendar.
The fixture provider uses it for the weeks TheStatsAPI has not published (placeholder matches, with a date and, when the
calendar has one, a kick-off time). When TheStatsAPI lists a match, its placeholder is replaced at the next load. The league
must have ``schedule_source: "openfootball:<code>"`` in config/competitions.yaml.

Reads:  https://raw.githubusercontent.com/openfootball/football.json (public domain, CC0).
Writes: ``data/competitions/<key>/raw/openfootball/fixtures_<season>.json``, saved untouched.
Needs:  no key. Run ``load_thestatsapi_league`` afterwards to turn the calendar into rows.
"""

from __future__ import annotations

import argparse
import json
import logging
import urllib.request
from typing import List, Optional

from src.competitions.registry import get_competition
from src.config import configure_logging
from src.ingest.raw_store import provider_dir, write_json

logger = logging.getLogger("fetch_openfootball_schedule")
BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"
PROVIDER = "openfootball"


def schedule_code(competition_key: str) -> Optional[str]:
    source = get_competition(competition_key).schedule_source or ""
    return source.split(":", 1)[1] if source.startswith("openfootball:") else None


def schedule_path(competition_key: str, season: str):
    return provider_dir(competition_key, PROVIDER) / f"fixtures_{season}.json"


def fetch_schedule(competition_key: str, seasons: Optional[List[str]] = None) -> List[str]:
    """Save the calendar of each requested season; returns the seasons that were saved."""
    code = schedule_code(competition_key)
    if not code:
        return []
    from src.ingest.providers.thestatsapi_league import PROVIDER as TSA_PROVIDER

    wanted = seasons or sorted(p.stem.removeprefix("fixtures_") for p in provider_dir(competition_key, TSA_PROVIDER).glob("fixtures_*.json"))
    saved = []
    for season in wanted:
        url = f"{BASE_URL}/{season.replace('_', '-')[:4]}-{season[-2:]}/{code}.json"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as response:
                payload = json.loads(response.read())
        except Exception as exc:  # a missing season file is normal for old or future seasons
            logger.warning("No calendar for %s %s: %s", competition_key, season, exc)
            continue
        write_json(schedule_path(competition_key, season), payload)
        saved.append(season)
        logger.info("%s %s: %d matches in the calendar", competition_key, season, len(payload.get("matches", [])))
    return saved


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml")
    parser.add_argument("--seasons", nargs="+", help="season labels such as 2026_27; default: every season with saved fixtures")
    args = parser.parse_args()
    fetch_schedule(args.competition, args.seasons)


if __name__ == "__main__":
    main()
