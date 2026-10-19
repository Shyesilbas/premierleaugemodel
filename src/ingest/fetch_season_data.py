#!/usr/bin/env python3
"""
Premier League Season Data Ingestion Pipeline (PulseLive API)
Fetches fixtures, team match statistics, play-by-play text streams, and match details.
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from tqdm import tqdm
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets `python3 src/...py` import src.config
from src.config import DATA_DIR, configure_logging  # noqa: E402

logger = logging.getLogger("fetch_season_data")

BASE_API_URL = "https://footballapi.pulselive.com/football"
DEFAULT_HEADERS = {
    "Origin": "https://www.premierleague.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "*/*",
}


def build_session(retries: int = 5, backoff_factor: float = 0.5) -> requests.Session:
    """Creates a requests Session with automatic retry strategy."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def is_valid_json_file(file_path: Path) -> bool:
    """Checks if a file exists, is non-empty, and contains valid JSON."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False


def fetch_fixtures(session: requests.Session, comp_season_id: int, comps: int = 1) -> List[Dict[str, Any]]:
    """
    Fetches the complete fixture list for a given season.
    Returns list of fixture dicts (expected: 380 for a full Premier League season).
    """
    url = f"{BASE_API_URL}/fixtures"
    params = {
        "comps": comps,
        "compSeasons": comp_season_id,
        "pageSize": 500,
        "sort": "asc",
    }
    logger.info(f"Fetching fixtures from {url} (compSeasons={comp_season_id}, comps={comps})...")
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    fixtures = data.get("content", [])
    logger.info(f"Retrieved {len(fixtures)} fixtures for season {comp_season_id}.")
    return fixtures


def fetch_match_stats(session: requests.Session, match_id: int) -> Optional[Dict[str, Any]]:
    """Fetches detailed match statistics (150+ metrics) for both teams."""
    url = f"{BASE_API_URL}/stats/match/{match_id}"
    resp = session.get(url, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    logger.warning(f"Failed to fetch stats for match {match_id}: HTTP {resp.status_code}")
    return None


def fetch_match_details(session: requests.Session, match_id: int) -> Optional[Dict[str, Any]]:
    """Fetches match details including lineups, referee, stadium."""
    url = f"{BASE_API_URL}/fixtures/{match_id}"
    resp = session.get(url, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    logger.warning(f"Failed to fetch details for match {match_id}: HTTP {resp.status_code}")
    return None


def fetch_match_stream(session: requests.Session, match_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches full play-by-play text stream (shots, cards, corners, commentary).
    Handles pagination automatically if numPages > 1.
    """
    url = f"{BASE_API_URL}/fixtures/{match_id}/textstream/en"
    params = {"pageSize": 500, "page": 0}
    resp = session.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        logger.warning(f"Failed to fetch stream for match {match_id}: HTTP {resp.status_code}")
        return None

    data = resp.json()
    events_obj = data.get("events", {})
    if isinstance(events_obj, dict):
        page_info = events_obj.get("pageInfo", {})
        num_pages = page_info.get("numPages", 1)
        all_events = list(events_obj.get("content", []))

        if num_pages > 1:
            for page in range(1, num_pages):
                time.sleep(0.05)
                params["page"] = page
                page_resp = session.get(url, params=params, timeout=15)
                if page_resp.status_code == 200:
                    page_data = page_resp.json()
                    p_events = page_data.get("events", {}).get("content", [])
                    all_events.extend(p_events)
            data["events"]["content"] = all_events
            data["events"]["pageInfo"]["numPages"] = 1
            data["events"]["pageInfo"]["numEntries"] = len(all_events)

    return data


def run_pipeline(
    season_id: int,
    season_name: str,
    comps: int = 1,
    base_data_dir: str = str(DATA_DIR),
    limit: Optional[int] = None,
    delay: float = 0.05,
    force: bool = False,
    workers: int = 6,
) -> Dict[str, Any]:
    """
    Executes the ingestion pipeline for a given season.
    Saves:
      - data/raw/fixtures_{season_name}.json
      - data/raw/matches/{match_id}_stats.json
      - data/raw/matches/{match_id}_stream.json
      - data/raw/matches/{match_id}_details.json
    """
    raw_dir = Path(base_data_dir) / "raw"
    matches_dir = raw_dir / "matches"
    raw_dir.mkdir(parents=True, exist_ok=True)
    matches_dir.mkdir(parents=True, exist_ok=True)

    session = build_session()

    fixtures_path = raw_dir / f"fixtures_{season_name}.json"
    if not force and is_valid_json_file(fixtures_path):
        logger.info(f"Using cached fixtures from {fixtures_path}")
        with open(fixtures_path, "r", encoding="utf-8") as f:
            fixtures_data = json.load(f)
            fixtures = fixtures_data if isinstance(fixtures_data, list) else fixtures_data.get("content", [])
    else:
        fixtures = fetch_fixtures(session, comp_season_id=season_id, comps=comps)
        with open(fixtures_path, "w", encoding="utf-8") as f:
            json.dump(fixtures, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved fixtures to {fixtures_path}")

    if limit is not None and limit > 0:
        fixtures = fixtures[:limit]
        logger.info(f"Limiting execution to first {limit} fixtures.")

    stats_saved = 0
    stream_saved = 0
    details_saved = 0
    skipped = 0
    errors = []

    logger.info(f"Processing {len(fixtures)} matches...")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_single_fixture(fix):
        raw_match_id = fix.get("id")
        if raw_match_id is None:
            return None
        match_id = int(raw_match_id)

        stats_file = matches_dir / f"{match_id}_stats.json"
        stream_file = matches_dir / f"{match_id}_stream.json"
        details_file = matches_dir / f"{match_id}_details.json"

        is_completed = (fix.get("status") == "C") or (fix.get("outcome") is not None)
        need_stats = is_completed and (force or not is_valid_json_file(stats_file))
        need_stream = is_completed and (force or not is_valid_json_file(stream_file))
        need_details = force or not is_valid_json_file(details_file)

        if not (need_stats or need_stream or need_details):
            return {"match_id": match_id, "cached": True}

        res = {"match_id": match_id, "cached": False, "stats": 0, "stream": 0, "details": 0, "error": None}
        try:
            if need_stats:
                s_data = fetch_match_stats(session, match_id)
                if s_data:
                    with open(stats_file, "w", encoding="utf-8") as f:
                        json.dump(s_data, f, ensure_ascii=False)
                    res["stats"] = 1
                time.sleep(delay)

            if need_stream:
                st_data = fetch_match_stream(session, match_id)
                if st_data:
                    with open(stream_file, "w", encoding="utf-8") as f:
                        json.dump(st_data, f, ensure_ascii=False)
                    res["stream"] = 1
                time.sleep(delay)

            if need_details:
                d_data = fetch_match_details(session, match_id)
                if d_data:
                    with open(details_file, "w", encoding="utf-8") as f:
                        json.dump(d_data, f, ensure_ascii=False)
                    res["details"] = 1
                time.sleep(delay)

        except Exception as e:
            res["error"] = str(e)

        return res

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_fixture, f): f for f in fixtures}
        for future in tqdm(as_completed(futures), total=len(fixtures), desc=f"Season {season_name}", unit="match"):
            out = future.result()
            if out:
                if out.get("cached"):
                    skipped += 1
                else:
                    stats_saved += out.get("stats", 0)
                    stream_saved += out.get("stream", 0)
                    details_saved += out.get("details", 0)
                    if out.get("error"):
                        errors.append({"match_id": out["match_id"], "error": out["error"]})

    summary = {
        "season_id": season_id,
        "season_name": season_name,
        "total_fixtures": len(fixtures),
        "stats_saved": stats_saved,
        "stream_saved": stream_saved,
        "details_saved": details_saved,
        "cached_skipped": skipped,
        "errors_count": len(errors),
        "errors": errors,
    }

    logger.info("=== Ingestion Summary ===")
    logger.info(f"Total fixtures processed: {len(fixtures)}")
    logger.info(f"Matches skipped (already cached): {skipped}")
    logger.info(f"New stats saved: {stats_saved}")
    logger.info(f"New streams saved: {stream_saved}")
    logger.info(f"New details saved: {details_saved}")
    logger.info(f"Errors encountered: {len(errors)}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Fetch Premier League season data from PulseLive API.")
    parser.add_argument("--season", type=int, required=True, help="PulseLive CompSeason ID")
    parser.add_argument("--season-name", type=str, required=True, help="Local season label, for example 2026_27")
    parser.add_argument("--comps", type=int, default=1, help="PulseLive Comps ID (default: 1 for Premier League)")
    parser.add_argument("--output-dir", type=str, default=str(DATA_DIR), help="Output directory for raw data")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of fixtures to process (for testing)")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between API requests in seconds")
    parser.add_argument("--workers", type=int, default=6, help="Number of concurrent download worker threads")
    parser.add_argument("--force", action="store_true", help="Force overwrite cached files")

    args = parser.parse_args()

    summary = run_pipeline(
        season_id=args.season,
        season_name=args.season_name,
        comps=args.comps,
        base_data_dir=args.output_dir,
        limit=args.limit,
        delay=args.delay,
        force=args.force,
        workers=args.workers,
    )
    if summary["errors_count"]:
        # Cron and shell callers only see the exit code; a partial season must not look like success.
        logger.error("%d matches failed: %s", summary["errors_count"], [e["match_id"] for e in summary["errors"]])
        sys.exit(1)


if __name__ == "__main__":
    configure_logging()
    main()
