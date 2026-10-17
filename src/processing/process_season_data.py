#!/usr/bin/env python3
"""
Premier League Data Processing & Tabulation Pipeline
Converts cached provider JSON into season and combined Parquet tables.
Outputs:
  - data/processed/matches_summary_{season}.parquet
  - data/processed/shots_events_{season}.parquet
  - data/processed/matches_summary_all.parquet
  - data/processed/shots_events_all.parquet
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("process_season_data")


METRIC_FIELDS = [
    # Corners
    "won_corners", "lost_corners", "corner_taken", "total_corners_intobox",
    # Throws
    "total_throws", "accurate_throws",
    # Goal Kicks
    "goal_kicks", "accurate_goal_kicks",
    # Shots & Accuracy
    "total_scoring_att", "ontarget_scoring_att", "blocked_scoring_att", "shot_off_target",
    "att_ibox_target", "att_obox_target", "att_ibox_miss", "att_obox_miss",
    # Goalkeeper Saves
    "saves", "saved_obox", "saved_ibox", "diving_save",
    # Passing & Possession
    "possession_percentage", "total_pass", "accurate_pass",
    "total_fwd_zone_pass", "accurate_fwd_zone_pass",
    "total_final_third_passes", "successful_final_third_passes",
    # Defense & Fouls
    "fk_foul_lost", "fk_foul_won", "total_yel_card", "total_red_card",
    "total_tackle", "won_tackle", "interception", "clearance_effective",
    # Offsides & Disciplinary
    "total_offside",
    # Advanced Attack & Big Chances
    "big_chance_created", "big_chance_missed", "big_chance_scored",
    "touches_in_opp_box", "touches_in_final_third", "total_fastbreak", "shot_fastbreak",
    "total_att_assist",
    # Pressing, Recoveries & Duels
    "ppda", "ball_recovery", "duel_won", "duel_lost", "aerial_won", "aerial_lost",
    "total_clearance", "head_clearance", "outfielder_block", "blocked_pass",
]
SPARSE_ZERO_METRICS = {"total_red_card"}


def _sum_if_complete(left: Any, right: Any) -> float:
    if pd.isna(left) or pd.isna(right):
        return np.nan
    return float(left) + float(right)


def _threshold_if_known(value: Any, threshold: float) -> Any:
    return np.nan if pd.isna(value) else int(float(value) > threshold)


def _event_counts_by_team(fixture: Dict[str, Any], stream_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Count team-attributed match events from a valid textstream."""
    if not isinstance(stream_data, dict) or not isinstance(stream_data.get("events"), dict):
        return None
    events = stream_data["events"].get("content")
    if not isinstance(events, list):
        return None
    teams = fixture.get("teams") or []
    if len(teams) < 2:
        return None
    names = [str(team.get("team", {}).get("name") or "") for team in teams[:2]]

    def normalize(name: str) -> str:
        # Normalize punctuation, accents, and the provider's "and" / "&" variants.
        value = unicodedata.normalize("NFKD", name.lower().replace("&", " and "))
        value = value.encode("ascii", "ignore").decode("ascii")
        value = re.sub(r"\band\b", " ", value)
        return "".join(char for char in value if char.isalnum())

    normalized_names = [normalize(name) for name in names]
    counts = {
        metric: {"home": 0, "away": 0}
        for metric in ("corners", "yellow_cards", "red_cards", "offsides", "saves")
    }
    saves_attribution_complete = True
    for event in events:
        event_type = event.get("type")
        text = str(event.get("text") or "")
        if event_type in ("attempt saved", "penalty saved"):
            # The event identifies the shooter and their team in parentheses.
            # The saved shot belongs to the opposing goalkeeper's team.
            match = re.search(r"\(([^()]*)\)", text)
            shooter_team = normalize(match.group(1)) if match else ""
            matched_sides = [i for i, name in enumerate(normalized_names) if name and name == shooter_team]
            if len(matched_sides) == 1:
                keeper_side = "away" if matched_sides[0] == 0 else "home"
                counts["saves"][keeper_side] += 1
            else:
                saves_attribution_complete = False
            continue
        if event_type == "corner":
            match = re.match(r"corner\s+(.+?)\s+conceded by", text, flags=re.IGNORECASE)
            team_name = match.group(1) if match else ""
            metric = "corners"
        elif event_type == "offside":
            match = re.match(r"Offside, (.+?)\.", text)
            metric = "offsides"
            team_name = match.group(1) if match else ""
        elif event_type in ("yellow card", "red card", "secondyellow card"):
            match = re.search(r"\((.+?)\)", text)
            team_name = match.group(1) if match else ""
            metric = "yellow_cards" if event_type == "yellow card" else "red_cards"
        else:
            continue
        normalized_event_team = normalize(team_name)
        matched_sides = [i for i, name in enumerate(normalized_names) if name and name == normalized_event_team]
        if len(matched_sides) == 1:
            side = "home" if matched_sides[0] == 0 else "away"
            counts[metric][side] += 1
    counts["_saves_attribution_complete"] = saves_attribution_complete
    return counts


def extract_team_metrics(raw_team_data: Dict[str, Any]) -> Dict[str, float]:
    """Extracts known metrics dictionary from team stats M list."""
    out = {}
    metrics_list = raw_team_data.get("M", [])
    for item in metrics_list:
        name = item.get("name")
        val = item.get("value")
        if name and val is not None:
            out[name] = float(val)
    return out


def parse_match(
    fixture: Dict[str, Any],
    stats_data: Optional[Dict[str, Any]],
    details_data: Optional[Dict[str, Any]],
    stream_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Combines fixture info and raw team stats into a single flat match record."""
    match_id = int(fixture["id"])
    kickoff = fixture.get("kickoff", {})
    kickoff_label = kickoff.get("label", "")
    kickoff_millis = kickoff.get("millis", 0)
    gameweek = fixture.get("gameweek", {}).get("gameweek")

    ground_info = fixture.get("ground", {})
    ground_name = ground_info.get("name", "")
    ground_city = ground_info.get("city", "")

    teams = fixture.get("teams", [])
    if len(teams) < 2:
        return None

    home_team = teams[0].get("team", {})
    away_team = teams[1].get("team", {})

    is_completed = str(fixture.get("status") or "C").upper() == "C"
    home_id = int(home_team.get("id", 0))
    home_name = home_team.get("name", "")
    home_abbr = home_team.get("club", {}).get("abbr", "")
    home_score = teams[0].get("score") if is_completed else None

    away_id = int(away_team.get("id", 0))
    away_name = away_team.get("name", "")
    away_abbr = away_team.get("club", {}).get("abbr", "")
    away_score = teams[1].get("score") if is_completed else None

    # Match outcome
    home_win = 1 if home_score is not None and away_score is not None and home_score > away_score else 0
    away_win = 1 if home_score is not None and away_score is not None and away_score > home_score else 0
    draw = 1 if home_score is not None and away_score is not None and home_score == away_score else 0
    if home_score is None or away_score is None:
        match_result = None  # Unplayed or in-play fixture: no final outcome yet
    else:
        match_result = "H" if home_win else ("A" if away_win else "D")

    record: Dict[str, Any] = {
        "match_id": match_id,
        "gameweek": gameweek,
        "kickoff_label": kickoff_label,
        "kickoff_millis": kickoff_millis,
        "ground_name": ground_name,
        "ground_city": ground_city,
        "home_id": home_id,
        "home_name": home_name,
        "home_abbr": home_abbr,
        "home_score": home_score,
        "away_id": away_id,
        "away_name": away_name,
        "away_abbr": away_abbr,
        "away_score": away_score,
        "total_goals": (home_score + away_score) if (home_score is not None and away_score is not None) else None,
        "over_2_5_goals": int((home_score + away_score) > 2.5) if (home_score is not None and away_score is not None) else None,
        "match_result": match_result,
        "home_win": home_win,
        "draw": draw,
        "away_win": away_win,
    }

    # Keep omitted provider values missing and retain a separate raw-presence flag.
    # Red cards are the one sparse count treated as zero when omitted; its source flag
    # remains available so downstream analysis can distinguish observed from inferred.
    stats_by_team = ((stats_data or {}).get("data") or {}) if is_completed else {}
    home_metrics = extract_team_metrics(stats_by_team.get(str(home_id), {}))
    away_metrics = extract_team_metrics(stats_by_team.get(str(away_id), {}))
    for fld in METRIC_FIELDS:
        for side, metrics in (("home", home_metrics), ("away", away_metrics)):
            present = fld in metrics
            fallback = 0.0 if (is_completed and fld in SPARSE_ZERO_METRICS) else np.nan
            record[f"{side}_{fld}"] = metrics.get(fld, fallback)
            record[f"{side}_{fld}_reported"] = bool(present)

    # Preserve raw provider values and fill only omissions from the same provider's
    # event stream. Source flags continue to describe the stats endpoint itself.
    event_counts = _event_counts_by_team(fixture, stream_data) if is_completed else None
    event_fields = {
        "home_saves": ("saves", "home"),
        "away_saves": ("saves", "away"),
        "home_won_corners": ("corners", "home"),
        "away_won_corners": ("corners", "away"),
        "home_total_yel_card": ("yellow_cards", "home"),
        "away_total_yel_card": ("yellow_cards", "away"),
        "home_total_red_card": ("red_cards", "home"),
        "away_total_red_card": ("red_cards", "away"),
        "home_total_offside": ("offsides", "home"),
        "away_total_offside": ("offsides", "away"),
    }
    for field, (metric, side) in event_fields.items():
        raw_value = record[field]
        source_reported = bool(record[f"{field}_reported"])
        record[f"{field}_raw"] = raw_value if source_reported else np.nan
        reconstructed = bool(
            not source_reported
            and event_counts is not None
            and metric in event_counts
            and (
                metric != "saves"
                or event_counts.get("_saves_attribution_complete", False)
            )
        )
        record[f"{field}_event_reconstructed"] = reconstructed
        if reconstructed:
            record[field] = float(event_counts[metric][side])
        record[f"{field}_usable"] = bool(pd.notna(record[field]))

    # A match total is usable only when both teams have a reported value.
    for target, field in (
        ("total_corners", "won_corners"),
        ("total_throws", "total_throws"),
        ("total_saves", "saves"),
        ("total_offsides", "total_offside"),
        ("total_yellow_cards", "total_yel_card"),
        ("total_fouls", "fk_foul_lost"),
        ("total_shots", "total_scoring_att"),
        ("total_shots_ontarget", "ontarget_scoring_att"),
    ):
        home_value = record[f"home_{field}"]
        away_value = record[f"away_{field}"]
        record[target] = _sum_if_complete(home_value, away_value)
        record[f"{target}_reported"] = bool(
            record[f"home_{field}_reported"] and record[f"away_{field}_reported"]
        )

    # Red-card omissions are treated as zero, but the raw presence flags above remain.
    record["total_red_cards"] = _sum_if_complete(
        record["home_total_red_card"], record["away_total_red_card"]
    )
    record["total_cards"] = _sum_if_complete(
        record["total_yellow_cards"], record["total_red_cards"]
    )
    record["total_yellow_cards_target_usable"] = bool(
        record["home_total_yel_card_usable"] and record["away_total_yel_card_usable"]
    )
    record["total_offsides_target_usable"] = bool(
        record["home_total_offside_usable"] and record["away_total_offside_usable"]
    )
    record["total_corners_target_usable"] = bool(
        record["home_won_corners_usable"] and record["away_won_corners_usable"]
    )
    record["total_cards_target_usable"] = bool(
        record["total_yellow_cards_target_usable"]
        and record["home_total_red_card_usable"]
        and record["away_total_red_card_usable"]
    )
    record["total_saves_target_usable"] = bool(
        record["home_saves_usable"] and record["away_saves_usable"]
    )
    record["total_saves_event_reconstructed"] = bool(
        record["home_saves_event_reconstructed"]
        or record["away_saves_event_reconstructed"]
    )
    for side in ("home", "away"):
        record[f"{side}_total_cards_usable"] = bool(
            record[f"{side}_total_yel_card_usable"]
            and record[f"{side}_total_red_card_usable"]
        )

    for target, value, thresholds in (
        ("corners", record["total_corners"], (8.5, 9.5, 10.5)),
        ("throws", record["total_throws"], (33.5, 36.5)),
        ("offsides", record["total_offsides"], (2.5, 3.5, 4.5)),
        ("cards", record["total_cards"], (3.5, 4.5, 5.5)),
    ):
        for threshold in thresholds:
            cutoff = str(threshold).replace(".", "_")
            record[f"over_{cutoff}_{target}"] = _threshold_if_known(value, threshold)


    # Referee & Match Officials
    referee_id = None
    referee_name = "Unknown"
    def find_main_official(officials):
        for entry in officials or []:
            official = entry.get("official") or entry.get("matchOfficial") or entry
            role = entry.get("role") or entry.get("type") or official.get("role")
            name = official.get("name") or {}
            display = name.get("display") if isinstance(name, dict) else name
            if role in {"MAIN", "Referee"} and display:
                return official
        return None

    # The refreshed fixture cache carries the current appointment from the PL
    # officials feed. Prefer it over any older cached match-details response.
    main_official = find_main_official(fixture.get("matchOfficials"))
    if main_official is None:
        main_official = find_main_official((details_data or {}).get("matchOfficials"))
    if main_official:
        referee_id = main_official.get("id")
        referee_name = (main_official.get("name") or {}).get("display") or "Unknown"
    record["referee_id"] = referee_id
    record["referee_name"] = referee_name

    return record


def parse_stream_events(match_id: int, stream_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts structured shot and match events from textstream."""
    events = stream_data.get("events", {}).get("content", [])
    records = []
    for ev in events:
        ev_type = ev.get("type", "")
        # Keep shots, goals, saves, corners, cards
        target_types = {
            "goal", "attempt saved", "penalty saved", "miss", "attempt blocked",
            "corner", "yellow card", "red card", "secondyellow card", "offside"
        }
        if ev_type in target_types:
            t_info = ev.get("time", {})
            records.append({
                "match_id": match_id,
                "event_id": ev.get("id"),
                "event_type": ev_type,
                "minute": t_info.get("label"),
                "seconds": t_info.get("secs"),
                "text": ev.get("text", ""),
                "player_ids": json.dumps(ev.get("playerIds", [])),
            })
    return records


def process_season(season_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    fixtures_file = raw_dir / f"fixtures_{season_name}.json"
    if not fixtures_file.exists():
        logger.error(f"Fixtures file not found: {fixtures_file}")
        return pd.DataFrame(), pd.DataFrame()

    with open(fixtures_file, "r", encoding="utf-8") as f:
        fixtures_data = json.load(f)
        fixtures = fixtures_data if isinstance(fixtures_data, list) else fixtures_data.get("content", [])

    logger.info(f"Loaded {len(fixtures)} fixtures for {season_name} from {fixtures_file}")

    matches_rows = []
    events_rows = []
    matches_dir = raw_dir / "matches"

    for fix in tqdm(fixtures, desc=f"Parsing {season_name}"):
        match_id = int(fix["id"])
        stats_file = matches_dir / f"{match_id}_stats.json"
        stream_file = matches_dir / f"{match_id}_stream.json"
        details_file = matches_dir / f"{match_id}_details.json"

        stats_data = None
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                stats_data = json.load(f)

        details_data = None
        if details_file.exists():
            with open(details_file, "r", encoding="utf-8") as f:
                details_data = json.load(f)

        stream_data = None
        if stream_file.exists():
            with open(stream_file, "r", encoding="utf-8") as f:
                stream_data = json.load(f)

        match_record = parse_match(fix, stats_data, details_data, stream_data)
        if match_record:
            match_record["season"] = season_name
            matches_rows.append(match_record)

        if stream_data is not None:
            stream_events = parse_stream_events(match_id, stream_data)
            events_rows.extend(stream_events)

    df_matches = pd.DataFrame(matches_rows)
    df_events = pd.DataFrame(events_rows)

    if "kickoff_millis" in df_matches.columns:
        df_matches = df_matches.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)

    # Save season parquet
    matches_parquet = processed_dir / f"matches_summary_{season_name}.parquet"
    events_parquet = processed_dir / f"shots_events_{season_name}.parquet"
    df_matches.to_parquet(matches_parquet, index=False)
    df_events.to_parquet(events_parquet, index=False)

    logger.info(f"Saved {len(df_matches)} matches to {matches_parquet}")
    return df_matches, df_events


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--season-name", type=str, default="all", help="Season name or 'all' to process and merge every cached season")
    args = parser.parse_args()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    if args.season_name == "all":
        seasons = sorted(
            path.stem.removeprefix("fixtures_")
            for path in raw_dir.glob("fixtures_*.json")
        )
        if not seasons:
            logger.error("No cached season fixture files found in %s", raw_dir)
            return
        all_matches = []
        all_events = []
        for s in seasons:
            m_df, e_df = process_season(s)
            if not m_df.empty:
                all_matches.append(m_df)
            if not e_df.empty:
                all_events.append(e_df)

        if all_matches:
            df_combined_matches = pd.concat(all_matches, ignore_index=True)
            if "kickoff_millis" in df_combined_matches.columns:
                df_combined_matches = df_combined_matches.sort_values(by=["kickoff_millis", "match_id"]).reset_index(drop=True)
            combined_matches_path = processed_dir / "matches_summary_all.parquet"
            df_combined_matches.to_parquet(combined_matches_path, index=False)
            logger.info(f"Saved combined {len(df_combined_matches)} matches to {combined_matches_path}")

        if all_events:
            df_combined_events = pd.concat(all_events, ignore_index=True)
            combined_events_path = processed_dir / "shots_events_all.parquet"
            df_combined_events.to_parquet(combined_events_path, index=False)
            logger.info(f"Saved combined {len(df_combined_events)} events to {combined_events_path}")

    else:
        process_season(args.season_name)


if __name__ == "__main__":
    main()
