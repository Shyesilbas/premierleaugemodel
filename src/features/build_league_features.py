"""Pre-match features for a league that is fed only by TheStatsAPI (LaLiga and leagues added the same way).

Every feature of a match uses information that existed before its kick-off: team histories are shifted by one match
(``shift(1)``) before any rolling or exponential average, Elo and the league table are updated only after a result is
recorded, and league-wide priors come from earlier days only. The same function builds the training table and the
rows of upcoming matches, so training and serving share one definition.

The set follows the Premier League model where the data allows it (Elo, points and goal difference per game, expected
goals, shots on target, big chances, possession, passing, touches in the box, rest days). It leaves out what the
provider cannot give for past seasons: squad market values (only today's roster is available) and
penalty-area entries.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.features.build_features import ELO_HOME_ADV, ELO_INIT, ELO_K, ELO_NEWCOMER, ELO_SEASON_REGRESS, PPG_PRIOR, PRIOR_GAMES

LONDON = ZoneInfo("Europe/London")
ROLL_WINDOWS = (5, 10)
EWMA_ALPHA = 0.2
MIN_HISTORY = 3

# json path inside the TheStatsAPI statistics payload -> (home column, away column)
STAT_PATHS = {
    "xg": "$.data.overview.expected_goals.all",
    "shots": "$.data.overview.total_shots.all",
    "sot": "$.data.overview.shots_on_target.all",
    "big_chances": "$.data.overview.big_chances.all",
    "possession": "$.data.overview.ball_possession.all",
    "passes": "$.data.overview.passes.all",
    "accurate_passes": "$.data.overview.accurate_passes.all",
    "touches_box": "$.data.attack.touches_in_penalty_area.all",
    "corners": "$.data.overview.corner_kicks.all",
    "offsides": "$.data.attack.offsides.all",
    "throws": "$.data.passes.throw_ins.all",
    "fouls": "$.data.overview.fouls.all",
    "yellow": "$.data.overview.yellow_cards.all",
    "red": "$.data.overview.red_cards.all",
    "saves": "$.data.overview.goalkeeper_saves.all",
}
# (feature stem, own-side stat, opponent-side stat or None)
TEAM_STATS = (
    ("goals_for", "goals", None), ("goals_against", "goals_opp", None),
    ("xg_for", "xg", None), ("xg_against", "xg_opp", None),
    ("sot_for", "sot", None), ("sot_against", "sot_opp", None),
    ("shots_for", "shots", None), ("shots_against", "shots_opp", None),
    ("big_chances_for", "big_chances", None), ("big_chances_against", "big_chances_opp", None),
    ("possession", "possession", None), ("pass_pct", "pass_pct", None), ("touches_box", "touches_box", None),
)
# Histories only the count models (corners, throws, offsides, cards, saves) read; the 1X2 model leaves them out.
COUNT_TEAM_STATS = (
    ("corners_for", "corners", None), ("corners_against", "corners_opp", None),
    ("offsides_for", "offsides", None), ("offsides_against", "offsides_opp", None),
    ("throws_for", "throws", None), ("throws_against", "throws_opp", None),
    ("fouls_committed", "fouls", None), ("fouls_drawn", "fouls_opp", None),
    ("cards_for", "cards", None), ("cards_against", "cards_opp", None),
    ("saves_for", "saves", None),
)
# Match totals the count models predict (sum of both sides).
COUNT_TARGETS = {"total_corners": "corners", "total_offsides": "offsides", "total_throws": "throws", "total_fouls": "fouls",
                 "total_cards": "cards", "total_saves": "saves"}
REFEREE_SHRINKAGE_MATCHES = 8
VENUE_STEMS = ("goals_for", "goals_against", "xg_for", "xg_against", "sot_for", "sot_against")
FALLBACK_PRIOR = {"goals_for": 1.4, "goals_against": 1.4, "xg_for": 1.4, "xg_against": 1.4, "sot_for": 4.6, "sot_against": 4.6,
                  "shots_for": 12.5, "shots_against": 12.5, "big_chances_for": 2.2, "big_chances_against": 2.2,
                  "possession": 50.0, "pass_pct": 82.0, "touches_box": 24.0,
                  "corners_for": 5.0, "corners_against": 5.0, "offsides_for": 2.0, "offsides_against": 2.0, "throws_for": 22.0,
                  "throws_against": 22.0, "fouls_committed": 12.5, "fouls_drawn": 12.5, "cards_for": 2.2, "cards_against": 2.2,
                  "saves_for": 3.0}


def kickoff(match_date: Optional[str], time_label: Optional[str]) -> pd.Timestamp:
    """Kick-off as a naive UTC timestamp; a date without a clock time counts as midnight."""
    clock = (time_label or "").split(" ")[0]
    try:
        hour, minute = (int(part) for part in clock.split(":")[:2])
    except ValueError:
        hour, minute = 0, 0
    local = datetime.fromisoformat(match_date).replace(hour=hour, minute=minute, tzinfo=LONDON)
    return pd.Timestamp(local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None))


def load_league_matches(conn: sqlite3.Connection, competition_id: int) -> pd.DataFrame:
    """Matches of one competition with the statistics both teams recorded, ordered by kick-off."""
    columns = ", ".join(
        f"json_extract(p.payload, '{path}.home') AS home_{name}, json_extract(p.payload, '{path}.away') AS away_{name}"
        for name, path in STAT_PATHS.items()
    )
    frame = pd.read_sql_query(
        f"""SELECT m.match_id, m.season, m.gameweek, m.match_date, m.time_label, m.home_id, m.away_id, m.home_name, m.away_name,
                   m.home_score, m.away_score, m.status, m.referee_name, {columns}
            FROM matches m
            LEFT JOIN external_match_payloads p ON p.match_id = m.match_id AND p.provider = 'TheStatsAPI' AND p.kind = 'stats'
            WHERE m.competition_id = ?""",
        conn, params=(competition_id,),
    )
    frame["kickoff"] = [kickoff(d, t) for d, t in zip(frame["match_date"], frame["time_label"])]
    frame["kickoff_millis"] = frame["kickoff"].astype("int64") // 1_000_000
    played = frame["status"].eq("COMPLETED") & frame["home_score"].notna() & frame["away_score"].notna()
    frame.loc[~played, ["home_score", "away_score"]] = np.nan
    return frame.sort_values(["kickoff", "match_id"], kind="mergesort").reset_index(drop=True)


def _long_table(matches: pd.DataFrame) -> pd.DataFrame:
    """One row per team and match with the team's own and opponent's numbers."""
    rows = []
    for side, other in (("home", "away"), ("away", "home")):
        part = pd.DataFrame({
            "match_id": matches["match_id"], "team_id": matches[f"{side}_id"], "kickoff": matches["kickoff"], "season": matches["season"],
            "is_home": side == "home",
            "goals": matches[f"{side}_score"], "goals_opp": matches[f"{other}_score"],
        })
        for stat in STAT_PATHS:
            part[stat] = matches[f"{side}_{stat}"]
            part[f"{stat}_opp"] = matches[f"{other}_{stat}"]
        part["pass_pct"] = 100.0 * part["accurate_passes"] / part["passes"].where(part["passes"] > 0)
        part["cards"] = part["yellow"] + part["red"]
        part["cards_opp"] = part["yellow_opp"] + part["red_opp"]
        rows.append(part)
    return pd.concat(rows, ignore_index=True).sort_values(["kickoff", "match_id", "is_home"], kind="mergesort").reset_index(drop=True)


def _expanding_daily_prior(long: pd.DataFrame, column: str) -> pd.Series:
    """League mean of a statistic over earlier days only, for each row (a stand-in for the first matches of a team)."""
    day = long["kickoff"].dt.normalize()
    daily = long.groupby(day)[column].agg(["sum", "count"]).sort_index()
    cumulative = daily.cumsum().shift(1)
    mean = (cumulative["sum"] / cumulative["count"].where(cumulative["count"] > 0))
    return day.map(mean)


def _history_features(long: pd.DataFrame, stats=TEAM_STATS) -> pd.DataFrame:
    """Rolling and exponential histories of every team, shifted so a match never sees itself."""
    out = pd.DataFrame(index=long.index)
    long = long.copy()
    for stem, column, _ in stats:
        series = long[column]
        grouped = series.groupby(long["team_id"])
        shifted = grouped.shift(1)
        prior = _expanding_daily_prior(long, column).fillna(FALLBACK_PRIOR[stem])
        for window in ROLL_WINDOWS:
            out[f"{stem}_roll_{window}"] = shifted.groupby(long["team_id"]).transform(lambda s, w=window: s.rolling(w, min_periods=MIN_HISTORY).mean())
        out[f"{stem}_ewma_02"] = shifted.groupby(long["team_id"]).transform(lambda s: s.ewm(alpha=EWMA_ALPHA, adjust=False, min_periods=1).mean())
        for name in [c for c in out.columns if c.startswith(f"{stem}_")]:
            out[name] = out[name].fillna(prior)
        if stem in VENUE_STEMS:  # the same average, but only over matches at the same venue type
            venue_key = [long["team_id"], long["is_home"]]
            venue_shifted = series.groupby(venue_key).shift(1)
            out[f"{stem}_venue_roll_5"] = venue_shifted.groupby(venue_key).transform(lambda s: s.rolling(5, min_periods=MIN_HISTORY).mean()).fillna(prior)
    return out


def _strength(matches: pd.DataFrame) -> pd.DataFrame:
    """Elo (overall and by venue) and season-to-date points and goal difference, exactly as the Premier League model defines them."""
    elo: Dict[int, float] = {}
    elo_home: Dict[int, float] = {}
    elo_away: Dict[int, float] = {}
    table: Dict[int, List[float]] = {}
    previous_teams: set = set()
    last_played: Dict[int, pd.Timestamp] = {}
    season = None
    first_season = matches["season"].iloc[0] if len(matches) else None
    rows = []
    for row in matches.itertuples(index=False):
        if row.season != season:
            previous_teams = set(table)
            for store in (elo, elo_home, elo_away):
                for team in store:
                    store[team] = (1 - ELO_SEASON_REGRESS) * store[team] + ELO_SEASON_REGRESS * ELO_INIT
            table, season = {}, row.season
        h, a = int(row.home_id), int(row.away_id)
        promoted = {}
        for team in (h, a):
            new = team not in elo or (season != first_season and team not in previous_teams and team not in table)
            if new:
                start = ELO_INIT if season == first_season else ELO_NEWCOMER
                elo[team], elo_home[team], elo_away[team] = start, start, start
            promoted[team] = float(season != first_season and team not in previous_teams)

        def form(team: int):
            points, goal_diff, played = table.get(team, [0.0, 0.0, 0.0])
            return (points + PPG_PRIOR * PRIOR_GAMES) / (played + PRIOR_GAMES), goal_diff / (played + PRIOR_GAMES)

        (hp, hg), (ap, ag) = form(h), form(a)
        rows.append({
            "elo_home": elo[h], "elo_away": elo[a], "elo_diff": elo[h] - elo[a],
            "elo_venue_home": elo_home[h], "elo_venue_away": elo_away[a], "elo_venue_diff": elo_home[h] - elo_away[a],
            "ppg_home": hp, "ppg_away": ap, "ppg_diff": hp - ap, "gdpg_home": hg, "gdpg_away": ag, "gdpg_diff": hg - ag,
            "is_promoted_home": promoted[h], "is_promoted_away": promoted[a],
            "home_rest_days": min((row.kickoff - last_played[h]).total_seconds() / 86400.0, 30.0) if h in last_played else 14.0,
            "away_rest_days": min((row.kickoff - last_played[a]).total_seconds() / 86400.0, 30.0) if a in last_played else 14.0,
        })
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        hs, as_ = float(row.home_score), float(row.away_score)
        last_played[h] = last_played[a] = row.kickoff
        expected = 1.0 / (1.0 + 10 ** ((elo[a] - (elo[h] + ELO_HOME_ADV)) / 400.0))
        result = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
        margin = abs(hs - as_)
        weight = np.log(margin + 1.0) + 1.0 if margin > 0 else 1.0
        delta = ELO_K * weight * (result - expected)
        elo[h] += delta
        elo[a] -= delta
        expected_venue = 1.0 / (1.0 + 10 ** ((elo_away[a] - (elo_home[h] + ELO_HOME_ADV)) / 400.0))
        delta_venue = ELO_K * weight * (result - expected_venue)
        elo_home[h] += delta_venue
        elo_away[a] -= delta_venue
        for team, points, diff in ((h, 3.0 if hs > as_ else (1.0 if hs == as_ else 0.0), hs - as_), (a, 3.0 if as_ > hs else (1.0 if hs == as_ else 0.0), as_ - hs)):
            record = table.setdefault(team, [0.0, 0.0, 0.0])
            record[0] += points
            record[1] += diff
            record[2] += 1.0
    return pd.DataFrame(rows, index=matches.index)


def _referee_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Cards and fouls per match the referee gave in earlier kick-off batches, shrunk toward the league mean of earlier days."""
    out = {"referee_avg_cards": [np.nan] * len(frame), "referee_avg_fouls": [np.nan] * len(frame), "referee_prior_matches": [0] * len(frame)}
    history: Dict[str, List[tuple]] = {}
    league = [0.0, 0.0, 0]  # cards, fouls, matches seen so far
    for _, batch in frame.groupby("kickoff", sort=True):
        prior_cards = league[0] / league[2] if league[2] else FALLBACK_PRIOR["cards_for"] * 2
        prior_fouls = league[1] / league[2] if league[2] else FALLBACK_PRIOR["fouls_committed"] * 2
        for index, row in batch.iterrows():
            seen = history.get(row["referee_name"] or "", [])
            n = len(seen)
            out["referee_avg_cards"][index] = (sum(c for c, _ in seen) + REFEREE_SHRINKAGE_MATCHES * prior_cards) / (n + REFEREE_SHRINKAGE_MATCHES)
            out["referee_avg_fouls"][index] = (sum(f for _, f in seen) + REFEREE_SHRINKAGE_MATCHES * prior_fouls) / (n + REFEREE_SHRINKAGE_MATCHES)
            out["referee_prior_matches"][index] = n
        for _, row in batch.iterrows():
            if row["referee_name"] and pd.notna(row["total_cards"]) and pd.notna(row["total_fouls"]):
                history.setdefault(row["referee_name"], []).append((float(row["total_cards"]), float(row["total_fouls"])))
                league[0] += float(row["total_cards"]); league[1] += float(row["total_fouls"]); league[2] += 1
    return pd.DataFrame(out, index=frame.index)


def build_league_features(matches: pd.DataFrame) -> pd.DataFrame:
    """Feature table of ``load_league_matches`` output: one row per match, played or not."""
    matches = matches.sort_values(["kickoff", "match_id"], kind="mergesort").reset_index(drop=True)
    long = _long_table(matches)
    history = pd.concat([_history_features(long), _history_features(long, COUNT_TEAM_STATS)], axis=1)
    long = pd.concat([long[["match_id", "team_id", "is_home"]], history], axis=1)
    sides = {}
    for side, flag in (("home", True), ("away", False)):
        part = long[long["is_home"] == flag].drop(columns=["team_id", "is_home"]).set_index("match_id")
        sides[side] = part.add_prefix(f"{side}_")
    frame = matches.set_index("match_id").join(sides["home"]).join(sides["away"]).reset_index()
    strength = _strength(matches)
    frame = pd.concat([frame.reset_index(drop=True), strength.reset_index(drop=True)], axis=1)
    for stem in ("xg_for", "xg_against", "sot_for", "goals_for", "big_chances_for", "touches_box", "possession"):
        frame[f"diff_{stem}_roll_10"] = frame[f"home_{stem}_roll_10"] - frame[f"away_{stem}_roll_10"]
    frame["xg_diff_10"] = (frame["home_xg_for_roll_10"] - frame["home_xg_against_roll_10"]) - (frame["away_xg_for_roll_10"] - frame["away_xg_against_roll_10"])
    frame["venue_xg_diff"] = (frame["home_xg_for_venue_roll_5"] - frame["home_xg_against_venue_roll_5"]) - (frame["away_xg_for_venue_roll_5"] - frame["away_xg_against_venue_roll_5"])
    for target, stat in COUNT_TARGETS.items():
        home = frame[f"home_{stat}"] if stat != "cards" else frame["home_yellow"] + frame["home_red"]
        away = frame[f"away_{stat}"] if stat != "cards" else frame["away_yellow"] + frame["away_red"]
        frame[target] = home + away
    frame["is_played"] = frame["home_score"].notna() & frame["away_score"].notna()
    frame = pd.concat([frame, _referee_features(frame)], axis=1)
    frame["abs_elo_diff"] = frame["elo_diff"].abs()
    frame["abs_ppg_diff"] = frame["ppg_diff"].abs()
    frame["abs_xg_diff_10"] = frame["xg_diff_10"].abs()
    return frame


def _is_count_column(name: str) -> bool:
    stem = name.split("_", 1)[1] if name.startswith(("home_", "away_")) else name
    return name.startswith("referee_") or any(stem.startswith(f"{s}_") for s, _, _ in COUNT_TEAM_STATS)


def _raw_columns() -> set:
    raw = {"match_id", "season", "gameweek", "match_date", "time_label", "home_id", "away_id", "home_name", "away_name", "home_score",
           "away_score", "status", "referee_name", "kickoff", "kickoff_millis", "is_played", *COUNT_TARGETS}
    return raw | {f"{side}_{stat}" for side in ("home", "away") for stat in STAT_PATHS}


def feature_columns(frame: pd.DataFrame) -> List[str]:
    """1X2 and goal model inputs: everything the builder adds for them, none of the raw per-match numbers, identifiers or count-model histories."""
    raw = _raw_columns()
    return [c for c in frame.columns if c not in raw and not _is_count_column(c)]


def count_feature_columns(frame: pd.DataFrame) -> List[str]:
    """Count-model inputs added on top of the 1X2 set: team histories of corners, offsides, throws, fouls, cards, saves and referee tendencies."""
    raw = _raw_columns()
    return [c for c in frame.columns if c not in raw and _is_count_column(c)]
