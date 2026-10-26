"""Download club badges (and optionally the league emblem) for a competition from TheSportsDB.

Usage: python3 -m src.ingest.fetch_team_badges --competition la_liga [--league-id 4335] [--force]

What it does: takes the clubs from the competition's saved fixture lists, looks each one up on TheSportsDB (public test
key, country check) and saves a 160 px high PNG. Clubs without a confident match are listed instead of guessed. With
--league-id the league's emblem is saved too, for the competition selector.

Reads:  ``data/competitions/<key>/raw/thestatsapi/fixtures_*.json`` and TheSportsDB.
Writes: ``frontend/public/badges/<key>/<local team id>.png`` and, with --league-id, ``frontend/public/competitions/<key>.png``.
        The fixture sync picks the badges up as ``home_logo`` / ``away_logo``; re-run ``load_thestatsapi_league`` afterwards.
Needs:  no key. The free service is rate limited (about 30 requests per minute); the script waits when it is limited.
Note:   badges are third-party marks, shown only to identify the clubs.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import requests

from src.competitions.registry import get_competition
from src.config import ROOT, configure_logging
from src.ingest.providers.thestatsapi_league import PROVIDER, local_team_id
from src.ingest.raw_store import provider_dir

logger = logging.getLogger("fetch_team_badges")
API = "https://www.thesportsdb.com/api/v1/json/123"
MAX_HEIGHT = 160
SEARCH_ALIASES = {"girona fc": ["Girona"], "levante ud": ["Levante"], "athletic club": ["Athletic Bilbao", "Athletic Club"],
                  "deportivo alaves": ["Deportivo Alavés", "Alaves"], "deportivo la coruna": ["Deportivo de La Coruña", "Deportivo La Coruna"]}


def fold(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower()).strip()


def club_list(competition_key: str) -> Dict[int, str]:
    clubs: Dict[int, str] = {}
    for path in sorted(provider_dir(competition_key, PROVIDER).glob("fixtures_*.json")):
        for fixture in json.loads(path.read_text(encoding="utf-8")):
            for side in ("home_team", "away_team"):
                clubs[local_team_id(fixture[side]["id"])] = fixture[side]["name"]
    return clubs


def find_badge(session: requests.Session, name: str, country: str) -> Optional[str]:
    for query in [name, *SEARCH_ALIASES.get(fold(name), [])]:
        for attempt in range(4):
            response = session.get(f"{API}/searchteams.php", params={"t": query}, timeout=30)
            if response.status_code != 429:
                break
            logger.warning("Rate limited; waiting %ds", 45 * (attempt + 1))
            time.sleep(45 * (attempt + 1))
        if response.status_code != 200:
            continue
        teams = [t for t in (response.json().get("teams") or []) if t.get("strSport") == "Soccer" and t.get("strCountry") == country]
        exact = [t for t in teams if fold(t["strTeam"]) in {fold(query), fold(name)} or fold(t.get("strTeamShort") or "") == fold(query)]
        pick = (exact or teams[:1] if len(teams) == 1 else exact)
        if pick and pick[0].get("strBadge"):
            return pick[0]["strBadge"]
        time.sleep(4)  # the free key is rate limited
    return None


def save_png(session: requests.Session, url: str, target: Path) -> None:
    data = session.get(url, timeout=60).content
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data)).convert("RGBA")
        if image.height > MAX_HEIGHT:
            image = image.resize((max(1, round(image.width * MAX_HEIGHT / image.height)), MAX_HEIGHT), Image.LANCZOS)
        image.save(target, optimize=True)
    except ImportError:
        target.write_bytes(data)


def fetch_league_logo(session: requests.Session, league_id: str, target: Path) -> bool:
    """The competition emblem shown in the competition selector (TheSportsDB league badge)."""
    for attempt in range(4):
        response = session.get(f"{API}/lookupleague.php", params={"id": league_id}, timeout=30)
        if response.status_code != 429:
            break
        time.sleep(45 * (attempt + 1))
    leagues = response.json().get("leagues") if response.status_code == 200 else None
    url = (leagues or [{}])[0].get("strBadge")
    if not url:
        return False
    save_png(session, url, target)
    return True


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--competition", required=True, help="competition key from config/competitions.yaml")
    parser.add_argument("--force", action="store_true", help="download again even if the badge file exists")
    parser.add_argument("--league-id", help="TheSportsDB league id; also saves the emblem to frontend/public/competitions/<key>.png")
    args = parser.parse_args()
    comp = get_competition(args.competition)
    out = ROOT / "frontend" / "public" / "badges" / comp.key
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 PremierLeagueModelApp/1.0"
    if args.league_id:
        target = ROOT / "frontend" / "public" / "competitions" / f"{comp.key}.png"
        logger.info("league emblem %s: %s", target.name, "saved" if fetch_league_logo(session, args.league_id, target) else "not found")
    missing: List[str] = []
    for team_id, name in sorted(club_list(comp.key).items(), key=lambda kv: kv[1]):
        target = out / f"{team_id}.png"
        if target.exists() and not args.force:
            continue
        url = find_badge(session, name, comp.country)
        if not url:
            missing.append(name)
            continue
        save_png(session, url, target)
        logger.info("%s -> %s", name, target.name)
        time.sleep(4)
    logger.info("badges in %s: %d, without a match: %s", out, len(list(out.glob("*.png"))), missing or "none")


if __name__ == "__main__":
    main()
