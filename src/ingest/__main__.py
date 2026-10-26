"""Index of the data-ingestion tools: ``python3 -m src.ingest --help``.

Every tool below has its own ``--help`` with what it reads, what it writes and what it needs. The map of which competition
gets which data from which source is in docs/data_sources.md.
"""

from __future__ import annotations

import argparse

TOOLS = (
    ("Premier League (PulseLive)", (
        ("fetch_season_data", "download one season's fixtures, team stats, event streams and match details"),
        ("sync_season_data", "incremental season sync (what the update button runs for the Premier League) and rebuild"),
        ("sync_prematch_lineups", "official starting XIs before kick-off, compared with the model"),
        ("fetch_team_staff", "team officials and squads"),
        ("import_thestatsapi_xg", "match xG from TheStatsAPI"),
        ("import_thestatsapi_odds", "bookmaker odds from TheStatsAPI"),
        ("fetch_transfermarkt_market_values", "squad and player market values"),
    )),
    ("Other competitions (UEFA cups, national leagues)", (
        ("sync_competition", "bring one competition up to date (what the update button runs outside the Premier League)"),
        ("sync_competition_data", "write a season's fixtures, results and official table into the database"),
        ("sync_thestatsapi_competition", "TheStatsAPI statistics, lineups, player data for a UEFA cup"),
        ("fetch_thestatsapi_league", "download a national league from TheStatsAPI into data/competitions/<key>/raw"),
        ("load_thestatsapi_league", "load those raw files into the database (no network)"),
        ("fetch_openfootball_schedule", "full-season calendar for weeks the provider has not published"),
        ("fetch_team_badges", "club badges and league emblem from TheSportsDB"),
        ("export_competition_raw", "one-off: archive what the database holds for the UEFA cups as raw files"),
    )),
)


def main() -> None:
    epilog = ["Run any of them as: python3 -m src.ingest.<tool> --help", ""]
    for group, tools in TOOLS:
        epilog.append(group)
        epilog.extend(f"  {name:<34}{purpose}" for name, purpose in tools)
        epilog.append("")
    epilog.append("Which source feeds which competition: docs/data_sources.md")
    parser = argparse.ArgumentParser(
        prog="python3 -m src.ingest", description="Data-ingestion tools of the project.",
        epilog="\n".join(epilog), formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
