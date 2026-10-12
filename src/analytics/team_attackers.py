"""Team-season attacking leaders from player logs and shot event descriptions."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PLAYER_REGISTRY_PATH = ROOT / "data" / "processed" / "players_registry.json"
PLAYER_LOGS_PATH = ROOT / "data" / "processed" / "player_match_logs.json"
SHOT_EVENTS_PATH = ROOT / "data" / "processed" / "shots_events_all.parquet"
SHOT_EVENT_TYPES = {"goal", "miss", "attempt blocked", "attempt saved"}
MIN_MINUTES = 180


@lru_cache(maxsize=1)
def _load_inputs() -> tuple[pd.DataFrame, dict[str, Any], dict[int, dict[str, Any]]]:
    events = pd.read_parquet(SHOT_EVENTS_PATH) if SHOT_EVENTS_PATH.exists() else pd.DataFrame()
    logs: dict[str, Any] = {}
    if PLAYER_LOGS_PATH.exists():
        with PLAYER_LOGS_PATH.open("r", encoding="utf-8") as handle:
            logs = json.load(handle)
    registry: dict[int, dict[str, Any]] = {}
    if PLAYER_REGISTRY_PATH.exists():
        with PLAYER_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            registry_rows = json.load(handle)
        registry = {
            int(row["id"]): row
            for row in registry_rows
            if isinstance(row, dict) and row.get("id") is not None
        }
    return events, logs, registry


def _player_ids(value: Any) -> list[int]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []
    if not isinstance(value, (list, tuple)):
        return []
    ids: list[int] = []
    for item in value:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def get_team_attacking_leaders(team_id: int, season: str = "all") -> dict[str, Any]:
    """Return three players ranked by an explainable, team-relative attack score.

    Shot assists come from the direct "Assisted by" participant in shot event
    descriptions. The source does not include every assisting pass, so its
    coverage is reported with the result and the count is labeled as shot assists.
    """
    events, player_logs, registry = _load_inputs()
    players: dict[int, dict[str, Any]] = {}
    players_by_match: dict[int, set[int]] = {}

    selected_seasons = {season} if season and season != "all" else None
    for raw_player_id, logs in player_logs.items():
        try:
            player_id = int(raw_player_id)
        except (TypeError, ValueError):
            continue
        for log in logs:
            if int(log.get("team_id") or 0) != int(team_id):
                continue
            log_season = str(log.get("season") or "")
            if selected_seasons is not None and log_season not in selected_seasons:
                continue
            try:
                match_id = int(log.get("match_id"))
            except (TypeError, ValueError):
                continue
            stats = players.setdefault(
                player_id,
                {"minutes": 0, "appearances": 0, "goals": 0, "assists": 0, "shots": 0, "shot_assists": 0},
            )
            minutes = max(0, int(float(log.get("minutes_played") or 0)))
            stats["minutes"] += minutes
            stats["appearances"] += int(minutes > 0)
            stats["goals"] += max(0, int(float(log.get("goals") or 0)))
            stats["assists"] += max(0, int(float(log.get("assists") or 0)))
            players_by_match.setdefault(match_id, set()).add(player_id)

    match_ids = set(players_by_match)
    if events.empty or not players or not match_ids:
        return {
            "team_id": int(team_id),
            "season": season or "all",
            "available": False,
            "reason": "Bu sezon için oyuncu maç bazlı dakika ve katkı kaydı bulunamadı.",
            "players": [],
            "minimum_minutes": MIN_MINUTES,
            "shot_assist_coverage_pct": None,
        }

    shot_rows = events[
        events["event_type"].isin(SHOT_EVENT_TYPES)
        & events["match_id"].astype("int64").isin(match_ids)
    ]
    team_shots = described_assists = 0
    for row in shot_rows.itertuples(index=False):
        match_id = int(row.match_id)
        ids = _player_ids(row.player_ids)
        if not ids or ids[0] not in players_by_match.get(match_id, set()):
            continue
        players[ids[0]]["shots"] += 1
        team_shots += 1
        if "assisted by" not in str(row.text).lower() or len(ids) < 2:
            continue
        described_assists += 1
        if ids[1] in players_by_match.get(match_id, set()):
            players[ids[1]]["shot_assists"] += 1

    eligible = [
        (player_id, stats)
        for player_id, stats in players.items()
        if stats["minutes"] >= MIN_MINUTES and player_id in registry
    ]
    per90: dict[int, dict[str, float]] = {}
    fields = ("shot_assists", "shots", "assists", "goals")
    for player_id, stats in eligible:
        per90[player_id] = {
            field: stats[field] * 90 / stats["minutes"]
            for field in fields
        }
    maxima = {
        field: max((rates[field] for rates in per90.values()), default=0)
        for field in fields
    }
    active_fields = [field for field in fields if maxima[field] > 0]

    rated: list[dict[str, Any]] = []
    for player_id, stats in eligible:
        rates = per90[player_id]
        score = (
            sum(rates[field] / maxima[field] for field in active_fields) / len(active_fields) * 100
            if active_fields
            else 0
        )
        meta = registry[player_id]
        rated.append(
            {
                "id": player_id,
                "name": meta.get("name") or f"Oyuncu {player_id}",
                "photo_url": meta.get("photo_url"),
                "position": meta.get("position"),
                "rating": round(score, 1),
                "minutes": stats["minutes"],
                "appearances": stats["appearances"],
                "shots": stats["shots"],
                "shot_assists": stats["shot_assists"],
                "assists": stats["assists"],
                "goals": stats["goals"],
            }
        )
    rated.sort(
        key=lambda row: (
            -row["rating"],
            -row["goals"],
            -row["assists"],
            -row["shots"],
            row["name"],
        )
    )
    selected = rated[:3]
    return {
        "team_id": int(team_id),
        "season": season or "all",
        "available": bool(selected),
        "reason": None if selected else "En az 180 dakika oynayan oyuncu bulunamadı.",
        "players": selected,
        "minimum_minutes": MIN_MINUTES,
        "shot_assist_coverage_pct": round(described_assists / team_shots * 100, 1) if team_shots else None,
    }
