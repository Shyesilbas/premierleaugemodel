"""Score-state shot and corner rates from chronological match event streams."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.analytics.team_tactics import normalize_season


ROOT = Path(__file__).resolve().parents[2]
RAW_MATCHES = ROOT / "data" / "raw" / "matches"
SCORING_TYPES = {"goal", "penalty goal", "own goal"}
SHOT_TYPES = {
    "goal",
    "penalty goal",
    "miss",
    "attempt blocked",
    "attempt saved",
    "post",
    "penalty miss",
    "penalty saved",
}
STATES = ("level", "leading", "trailing")


def _normalize(value: str | None) -> str:
    text = str(value or "").lower().replace("&", " and ")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()


def _minute(label: str | None, seconds: Any = None, first_half_end: float | None = None) -> float | None:
    match = re.fullmatch(r"\s*(\d+)(?:\+(\d+))?\s*", str(label or ""))
    if not match:
        return None
    base = int(match.group(1))
    if seconds is not None:
        elapsed_seconds = float(seconds)
        is_second_half = base >= 46
        if is_second_half and first_half_end is not None:
            # Opta's second-half seconds restart from 45:00. Add the actual
            # first-half duration so stoppage time is counted chronologically.
            elapsed_seconds = first_half_end + max(0.0, elapsed_seconds - 45 * 60)
        return elapsed_seconds / 60
    added = int(match.group(2) or 0)
    if base == 45 and added:
        return float(base + added - 1)
    if base >= 46 and first_half_end is not None:
        return first_half_end / 60 + max(0, base - 46) + (added if added else 0)
    return float(max(0, base - 1))


def _state_for(team_index: int, score: list[int]) -> str:
    difference = score[team_index] - score[1 - team_index]
    return "leading" if difference > 0 else "trailing" if difference < 0 else "level"


def _team_aliases(team: dict[str, Any]) -> set[str]:
    club = team.get("club") or {}
    return {
        _normalize(value)
        for value in (
            team.get("name"),
            team.get("shortName"),
            club.get("name"),
            club.get("shortName"),
            club.get("abbr"),
        )
        if value
    }


def _score_after(text: str, home_name: str, away_name: str) -> tuple[int, int] | None:
    normalized = _normalize(text)
    pattern = re.compile(
        re.escape(_normalize(home_name))
        + r"\s+(\d+)\s+"
        + re.escape(_normalize(away_name))
        + r"\s+(\d+)"
    )
    match = pattern.search(normalized)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _event_team(event: dict[str, Any], aliases: list[set[str]]) -> int | None:
    text = event.get("text", "")
    if event.get("type") == "corner":
        normalized = _normalize(text)
        match = re.match(r"corner\s+(.+?)\s+conceded by", normalized)
        candidate = match.group(1).strip() if match else ""
    else:
        parentheses = re.findall(r"\(([^()]*)\)", text)
        candidate = _normalize(parentheses[0]) if parentheses else ""
    if not candidate:
        return None
    matches = [index for index, team_aliases in enumerate(aliases) if candidate in team_aliases]
    return matches[0] if len(matches) == 1 else None


def _blank_state() -> dict[str, float | int]:
    return {"minutes": 0.0, "shots": 0, "corners": 0}


@lru_cache(maxsize=1)
def load_team_match_scenarios() -> tuple[dict[int, list[dict[str, Any]]], dict[int, str], Counter[str]]:
    """Parse score states, shots, and corners for every available match stream."""
    by_team: dict[int, list[dict[str, Any]]] = defaultdict(list)
    names: dict[int, str] = {}
    audit: Counter[str] = Counter()

    for path in sorted(RAW_MATCHES.glob("*_stream.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            audit["unreadable_streams"] += 1
            continue

        fixture = payload.get("fixture", {})
        team_entries = fixture.get("teams", [])
        teams = [item.get("team", {}) for item in team_entries]
        if len(teams) < 2 or fixture.get("id") is None:
            audit["invalid_streams"] += 1
            continue

        team_ids = [int(team["id"]) for team in teams]
        team_names = [team.get("name") or team.get("shortName") or str(team_ids[i]) for i, team in enumerate(teams)]
        aliases = [_team_aliases(team) for team in teams]
        season_label = fixture.get("gameweek", {}).get("compSeason", {}).get("label")
        season = normalize_season(season_label) if season_label else (_season_for_match(int(fixture["id"])) or "unknown")

        first_half_end = next(
            (
                float(event.get("time", {}).get("secs"))
                for event in payload.get("events", {}).get("content", [])
                if event.get("type") == "end 1" and event.get("time", {}).get("secs") is not None
            ),
            None,
        )
        if first_half_end is None:
            for event in payload.get("events", {}).get("content", []):
                if event.get("type") == "end 1":
                    first_half_end = _minute(event.get("time", {}).get("label"))
                    if first_half_end is not None:
                        first_half_end *= 60
                    break

        for team_id, team_name in zip(team_ids, team_names):
            names[team_id] = team_name

        events: list[tuple[float, int, dict[str, Any], int | None, tuple[int, int] | None]] = []
        max_minute = 0.0
        for index, event in enumerate(payload.get("events", {}).get("content", [])):
            event_minute = _minute(
                event.get("time", {}).get("label"),
                event.get("time", {}).get("secs"),
                first_half_end,
            )
            if event_minute is None:
                if event.get("type") in SHOT_TYPES | SCORING_TYPES | {"corner"}:
                    audit["timed_action_missing_clock"] += 1
                continue
            max_minute = max(max_minute, event_minute)
            event_type = event.get("type", "")
            if event_type not in SHOT_TYPES | SCORING_TYPES | {"corner"}:
                continue
            actor_team = _event_team(event, aliases) if event_type in SHOT_TYPES | {"corner"} else None
            if event_type in SHOT_TYPES:
                audit["shot_events"] += 1
                if actor_team is None:
                    audit["shot_team_unassigned"] += 1
            if event_type == "corner":
                audit["corner_events"] += 1
                if actor_team is None:
                    audit["corner_team_unassigned"] += 1
            after = _score_after(event.get("text", ""), team_names[0], team_names[1]) if event_type in SCORING_TYPES else None
            if event_type in SCORING_TYPES:
                audit["scoring_events"] += 1
                if after is None:
                    audit["score_text_unparsed"] += 1
            events.append((event_minute, index, event, actor_team, after))

        events.sort(key=lambda item: (item[0], item[1]))
        score = [0, 0]
        state_data = {team_id: {state: _blank_state() for state in STATES} for team_id in team_ids}
        previous_minute = 0.0
        for event_minute, _, event, actor_team, after in events:
            current_minute = max(previous_minute, event_minute)
            duration = current_minute - previous_minute
            if duration:
                for team_index, team_id in enumerate(team_ids):
                    state_data[team_id][_state_for(team_index, score)]["minutes"] += duration
            previous_minute = current_minute

            event_type = event.get("type", "")
            if actor_team is not None:
                actor_index = actor_team
                actor_team_id = team_ids[actor_index]
                state = _state_for(actor_index, score)
                if event_type in SHOT_TYPES:
                    state_data[actor_team_id][state]["shots"] += 1
                elif event_type == "corner":
                    state_data[actor_team_id][state]["corners"] += 1

            if event_type in SCORING_TYPES and after is not None:
                score[:] = after

        fixture_scores = [entry.get("score") for entry in team_entries]
        if all(value is not None for value in fixture_scores) and tuple(map(int, fixture_scores)) == tuple(score):
            audit["score_reconstructed_matches"] += 1
        elif all(value is not None for value in fixture_scores):
            audit["score_reconstruction_match_mismatch"] += 1

        match_id = int(fixture["id"])
        for team_id in team_ids:
            by_team[team_id].append(
                {
                    "match_id": match_id,
                    "season": season,
                    "states": state_data[team_id],
                }
            )
        audit["matches"] += 1

    return dict(by_team), names, audit


@lru_cache(maxsize=1)
def _match_seasons() -> dict[int, str]:
    """Fallback season labels for stream fixtures whose fixture object omits it."""
    seasons: dict[int, str] = {}
    for suffix in ("stats", "details"):
        for path in RAW_MATCHES.glob(f"*_{suffix}.json"):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue
            fixture = payload.get("entity", payload)
            match_id = fixture.get("id")
            label = fixture.get("gameweek", {}).get("compSeason", {}).get("label")
            if match_id is not None and label:
                seasons[int(match_id)] = normalize_season(label)
    return seasons


def _season_for_match(match_id: int) -> str | None:
    return _match_seasons().get(match_id)


def _state_rates(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    output: dict[str, dict[str, float | int | None]] = {}
    for state in STATES:
        minutes = sum(float(row["states"][state]["minutes"]) for row in rows)
        shots = sum(int(row["states"][state]["shots"]) for row in rows)
        corners = sum(int(row["states"][state]["corners"]) for row in rows)
        output[state] = {
            "minutes": round(minutes, 1),
            "shots": shots,
            "shots_per_90": round(shots * 90 / minutes, 2) if minutes > 0 else None,
            "corners": corners,
            "corners_per_90": round(corners * 90 / minutes, 2) if minutes > 0 else None,
            "matches_with_state": sum(float(row["states"][state]["minutes"]) > 0 for row in rows),
        }
    return output


@lru_cache(maxsize=128)
def get_team_scenario_profile(team_id: int, season: str = "all") -> dict[str, Any]:
    by_team, names, audit = load_team_match_scenarios()
    selected = [
        row
        for row in by_team.get(team_id, [])
        if season in ("", "all") or row["season"] == season
    ]
    if not selected:
        return {"team_id": team_id, "team_name": names.get(team_id), "season": season, "matches": 0, "states": {}}

    selected_seasons = {row["season"] for row in selected}
    league_rows = {
        other_id: [row for row in rows if row["season"] in selected_seasons]
        for other_id, rows in by_team.items()
    }
    team_states = _state_rates(selected)
    league_states = {
        other_id: _state_rates(rows)
        for other_id, rows in league_rows.items()
        if rows
    }

    for state in STATES:
        for rate_key in ("shots_per_90", "corners_per_90"):
            rates = [
                float(values[state][rate_key])
                for values in league_states.values()
                if values[state][rate_key] is not None and float(values[state]["minutes"]) >= 90
            ]
            value = team_states[state][rate_key]
            team_states[state][f"{rate_key}_league_average"] = round(sum(rates) / len(rates), 2) if rates else None
            team_states[state][f"{rate_key}_league_teams"] = len(rates)
            team_states[state][f"{rate_key}_qualified"] = bool(value is not None and team_states[state]["minutes"] >= 90)

    return {
        "team_id": team_id,
        "team_name": names.get(team_id),
        "season": season,
        "matches": len({row["match_id"] for row in selected}),
        "score_reconstructed_matches": audit["score_reconstructed_matches"],
        "states": team_states,
    }
