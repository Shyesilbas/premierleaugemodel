"""Team-level tactical summaries built from raw match statistics.

Raw Opta match files are used here so an omitted metric is not silently
converted to zero by the processed match-summary pipeline.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache
from typing import Any


from src.config import MATCHES_RAW_DIR as RAW_MATCHES

TACTICAL_METRICS = {
    "possession": {
        "label": "Topa sahip olma",
        "unit": "%",
        "description": "Takımın maçlardaki ortalama topa sahip olma oranı.",
    },
    "forward_pass_share": {
        "label": "İleri bölge pas payı",
        "unit": "%",
        "description": "İleri bölge paslarının toplam paslar içindeki payı.",
    },
    "final_third_entries": {
        "label": "Son bölgeye giriş",
        "unit": "maç başına",
        "description": "Maç başına rakip kaleye yakın son hücum bölgesine giriş sayısı.",
    },
    "mid_third_recoveries": {
        "label": "Orta bölgede top kazanımı",
        "unit": "maç başına",
        "description": "Maç başına orta bölgede kazanılan top sayısı.",
    },
    "defensive_third_recoveries": {
        "label": "Savunma bölgesinde top kazanımı",
        "unit": "maç başına",
        "description": "Takımın kendi savunma üçte birlik bölgesinde maç başına kazandığı top sayısı.",
    },
    "attacking_third_recoveries": {
        "label": "Hücum bölgesinde top kazanımı",
        "unit": "maç başına",
        "description": "Takımın rakip kaleye yakın hücum üçte birlik bölgede maç başına kazandığı top sayısı. Sık kazanım, yüksek presin sonucu olabilir ancak tek başına pres denemelerini ölçmez.",
    },
    "pressing_intensity": {
        "label": "Pres yoğunluğu (PPDA)",
        "unit": "PPDA",
        "description": "Rakibin savunma aksiyonu başına yaptığı pas sayısıdır. Düşük PPDA daha yoğun baskıya işaret eder; yalnızca yeterli veri kapsamı olan dönemlerde gösterilir.",
    },
    "outside_box_shot_share": {
        "label": "Ceza sahası dışı şut payı",
        "unit": "%",
        "description": "Ceza sahası dışı şutların tüm şutlar içindeki payı.",
    },
    "inside_box_shot_share": {
        "label": "Ceza sahası içi şut payı",
        "unit": "%",
        "description": "Ceza sahası içinden çekilen şutların tüm şutlar içindeki payı. Şut konumunu gösterir; şut kalitesini göstermez.",
    },
    "shots_per_match": {
        "label": "Şut",
        "unit": "maç başına",
        "description": "Maç başına toplam şut denemesi.",
    },
    "shots_on_target_share": {
        "label": "İsabetli şut oranı",
        "unit": "%",
        "description": "Kaleyi bulan şutların tüm şutlara oranı. Şutların gol olma olasılığını ölçmez.",
    },
    "corners_into_box_share": {
        "label": "Ceza sahasına gönderilen korner",
        "unit": "%",
        "description": "Ceza sahasına gönderilen kornerlerin kullanılan kornerlere oranı.",
    },
    "opposition_box_touches": {
        "label": "Rakip ceza sahası dokunuşu",
        "unit": "maç başına",
        "description": "Maç başına rakip ceza sahasında yapılan dokunuş sayısı.",
    },
    "final_third_passes": {
        "label": "Son bölgede pas",
        "unit": "maç başına",
        "description": "Maç başına son hücum bölgesinde denenen pas sayısı.",
    },
    "final_third_pass_accuracy": {
        "label": "Son bölge pas isabeti",
        "unit": "%",
        "description": "Son hücum bölgesindeki isabetli pasların toplam denemelere oranı.",
    },
    "long_ball_share": {
        "label": "Uzun pas payı",
        "unit": "%",
        "description": "Uzun pasların toplam paslar içindeki payı. Yüksek oran daha sık uzun pas kullanıldığını gösterir; pasın hedefini veya hücum başarısını göstermez.",
    },
    "long_ball_accuracy": {
        "label": "Uzun pas isabeti",
        "unit": "%",
        "description": "İsabetli uzun pasların toplam uzun paslara oranı.",
    },
    "crosses_per_match": {
        "label": "Orta denemesi",
        "unit": "maç başına",
        "description": "Maç başına yapılan orta denemesi. Tek başına orta kalitesini veya oluşan fırsatı göstermez.",
    },
    "cross_accuracy": {
        "label": "Orta isabeti",
        "unit": "%",
        "description": "İsabetli ortaların toplam orta denemelerine oranı.",
    },
    "ball_recoveries": {
        "label": "Topu geri kazanma",
        "unit": "maç başına",
        "description": "Maç başına topun yeniden kazanıldığı aksiyon sayısı.",
    },
    "possession_losses": {
        "label": "Top kaybı (tüm türler)",
        "unit": "maç başına",
        "description": "Kaynak istatistikteki poss_lost_all değeri, maç başına. Topa sahip olma ve aksiyon hacmiyle birlikte okunmalıdır.",
    },
    "controlled_possession_losses": {
        "label": "Kontrollü top kaybı",
        "unit": "maç başına",
        "description": "Kaynak istatistikteki poss_lost_ctrl değeri, maç başına. Tek başına pas hatası sayısı olarak yorumlanmamalıdır.",
    },
    "interceptions": {
        "label": "Pas arası",
        "unit": "maç başına",
        "description": "Maç başına yapılan pas arası sayısı.",
    },
    "tackle_success": {
        "label": "Müdahale başarısı",
        "unit": "%",
        "description": "Kazanılan müdahalelerin toplam müdahale denemelerine oranı.",
    },
    "aerial_duel_success": {
        "label": "Hava topu kazanma oranı",
        "unit": "%",
        "description": "Kazanılan hava topu mücadelelerinin kazanılan ve kaybedilen mücadeleler toplamına oranı.",
    },
    "clearances": {
        "label": "Uzaklaştırma",
        "unit": "maç başına",
        "description": "Maç başına yapılan toplam uzaklaştırma sayısı.",
    },
    "shots_conceded_per_match": {
        "label": "İzin verilen şut",
        "unit": "maç başına",
        "description": "Maç başına rakibe izin verilen toplam şut sayısı.",
    },
}


def normalize_season(label: str) -> str:
    match = re.search(r"(20\d{2})\s*[/_-]\s*(\d{2,4})", label or "")
    if not match:
        return label or "unknown"
    start = int(match.group(1))
    end_text = match.group(2)
    end = int(end_text) if len(end_text) == 4 else (start // 100) * 100 + int(end_text)
    return f"{start}_{str(end)[-2:]}"


@lru_cache(maxsize=1)
def load_team_match_rows() -> tuple[dict[int, list[dict[str, Any]]], dict[int, str]]:
    """Load played team-match rows and team names from raw match-stat files."""
    by_team: dict[int, list[dict[str, Any]]] = defaultdict(list)
    team_names: dict[int, str] = {}

    for path in sorted(RAW_MATCHES.glob("*_stats.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        entity = payload.get("entity", {})
        fixture_id = entity.get("id")
        if fixture_id is None:
            continue
        season_label = entity.get("gameweek", {}).get("compSeason", {}).get("label", "")
        season = normalize_season(season_label)
        fixture_teams = {
            int(entry.get("team", {}).get("id")): entry.get("team", {})
            for entry in entity.get("teams", [])
            if entry.get("team", {}).get("id") is not None
        }

        fixture_data = payload.get("data", {})
        fixture_metrics_by_team: dict[int, dict[str, Any]] = {}
        for raw_team_id, team_stats in fixture_data.items():
            try:
                team_id = int(raw_team_id)
            except (TypeError, ValueError):
                continue
            fixture_metrics_by_team[team_id] = {
                item.get("name"): item.get("value")
                for item in team_stats.get("M", [])
                if isinstance(item, dict) and item.get("name") and item.get("value") is not None
            }

        for team_id, metrics in fixture_metrics_by_team.items():
            meta = fixture_teams.get(team_id, {})
            team_names[team_id] = meta.get("name") or meta.get("shortName") or team_names.get(team_id, str(team_id))
            opp_id = next((tid for tid in fixture_metrics_by_team if tid != team_id), None)
            if opp_id is not None:
                opp_shots = fixture_metrics_by_team[opp_id].get("total_scoring_att")
                if opp_shots is not None:
                    metrics["shots_conceded"] = opp_shots

            by_team[team_id].append(
                {
                    "match_id": int(fixture_id),
                    "season": season,
                    "metrics": metrics,
                }
            )

    return dict(by_team), team_names


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_shot_split(metrics: dict[str, Any]) -> tuple[float, float, float] | None:
    """Return (inside, outside, total) when the raw shot split is consistent.

    A missing side is inferred as zero only if the other side exactly equals
    the reported total. When both sides exist, they must add to the total.
    """
    total = _number(metrics.get("total_scoring_att"))
    inside = _number(metrics.get("attempts_ibox"))
    outside = _number(metrics.get("attempts_obox"))
    if total is None:
        return None
    if inside is None and outside is not None and outside == total:
        inside = 0.0
    elif outside is None and inside is not None and inside == total:
        outside = 0.0
    if inside is None or outside is None or inside + outside != total:
        return None
    return inside, outside, total


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    possession: list[float] = []
    forward_passes = total_passes = 0.0
    forward_pass_matches = 0
    final_entries: list[float] = []
    middle_wins: list[float] = []
    defensive_third_wins: list[float] = []
    attacking_third_wins: list[float] = []
    ppda_values: list[float] = []
    obox_shots = total_shots = 0.0
    shot_split_matches = 0
    inside_shots = 0.0
    total_shot_attempts = 0.0
    total_shot_matches = 0
    shots_on_target = shots_for_target_rate = 0.0
    target_rate_matches = 0
    corners_into_box = corners_won = 0.0
    corner_matches = 0
    box_touches: list[float] = []
    final_third_passes = final_third_accurate_passes = 0.0
    final_third_pass_matches = 0
    long_balls = total_passes_for_long_ball_share = 0.0
    accurate_long_balls = total_long_balls_for_accuracy = 0.0
    long_ball_share_matches = long_ball_accuracy_matches = 0
    crosses_per_match: list[float] = []
    accurate_crosses = total_crosses = 0.0
    cross_accuracy_matches = 0
    ball_recoveries: list[float] = []
    possession_losses: list[float] = []
    controlled_possession_losses: list[float] = []
    interceptions: list[float] = []
    tackles_won = tackles_total = 0.0
    tackle_matches = 0
    aerial_won = aerial_lost = 0.0
    aerial_matches = 0
    clearances: list[float] = []
    total_shots_conceded = 0.0
    total_shots_conceded_matches = 0

    for row in rows:
        metrics = row["metrics"]
        value = _number(metrics.get("possession_percentage"))
        if value is not None:
            possession.append(value)

        forward = _number(metrics.get("total_fwd_zone_pass"))
        passes = _number(metrics.get("total_pass"))
        if forward is not None and passes is not None and passes > 0:
            forward_passes += forward
            total_passes += passes
            forward_pass_matches += 1

        value = _number(metrics.get("final_third_entries"))
        if value is not None:
            final_entries.append(value)
        value = _number(metrics.get("poss_won_mid_3rd"))
        if value is not None:
            middle_wins.append(value)
        value = _number(metrics.get("poss_won_def_3rd"))
        if value is not None:
            defensive_third_wins.append(value)
        value = _number(metrics.get("poss_won_att_3rd"))
        if value is not None:
            attacking_third_wins.append(value)
        value = _number(metrics.get("ppda"))
        if value is not None and value > 0:
            ppda_values.append(value)

        split = _safe_shot_split(metrics)
        if split is not None:
            inside, outside, total = split
            inside_shots += inside
            obox_shots += outside
            total_shots += total
            shot_split_matches += 1

        total_attempts = _number(metrics.get("total_scoring_att"))
        if total_attempts is not None and total_attempts >= 0:
            total_shot_attempts += total_attempts
            total_shot_matches += 1
        on_target = _number(metrics.get("ontarget_scoring_att"))
        if (
            total_attempts is not None
            and on_target is not None
            and 0 <= on_target <= total_attempts
        ):
            shots_on_target += on_target
            shots_for_target_rate += total_attempts
            target_rate_matches += 1

        won = _number(metrics.get("won_corners"))
        into_box = _number(metrics.get("total_corners_intobox"))
        if won is not None and into_box is not None and won >= into_box and won >= 0:
            corners_won += won
            corners_into_box += into_box
            corner_matches += 1

        value = _number(metrics.get("touches_in_opp_box"))
        if value is not None:
            box_touches.append(value)

        final_passes = _number(metrics.get("total_final_third_passes"))
        accurate_final_passes = _number(metrics.get("successful_final_third_passes"))
        if (
            final_passes is not None
            and accurate_final_passes is not None
            and final_passes >= accurate_final_passes >= 0
        ):
            final_third_passes += final_passes
            final_third_accurate_passes += accurate_final_passes
            final_third_pass_matches += 1

        passes_for_long_share = _number(metrics.get("total_pass"))
        total_long = _number(metrics.get("total_long_balls"))
        accurate_long = _number(metrics.get("accurate_long_balls"))
        if (
            passes_for_long_share is not None
            and total_long is not None
            and passes_for_long_share > 0
            and 0 <= total_long <= passes_for_long_share
        ):
            long_balls += total_long
            total_passes_for_long_ball_share += passes_for_long_share
            long_ball_share_matches += 1
        if (
            total_long is not None
            and accurate_long is not None
            and total_long >= 0
            and 0 <= accurate_long <= total_long
        ):
            accurate_long_balls += accurate_long
            total_long_balls_for_accuracy += total_long
            long_ball_accuracy_matches += 1

        total_cross = _number(metrics.get("total_cross"))
        accurate_cross = _number(metrics.get("accurate_cross"))
        if total_cross is not None and total_cross >= 0:
            crosses_per_match.append(total_cross)
        if (
            total_cross is not None
            and accurate_cross is not None
            and total_cross >= 0
            and 0 <= accurate_cross <= total_cross
        ):
            accurate_crosses += accurate_cross
            total_crosses += total_cross
            cross_accuracy_matches += 1

        value = _number(metrics.get("ball_recovery"))
        if value is not None:
            ball_recoveries.append(value)
        value = _number(metrics.get("poss_lost_all"))
        if value is not None:
            possession_losses.append(value)
        value = _number(metrics.get("poss_lost_ctrl"))
        if value is not None:
            controlled_possession_losses.append(value)
        value = _number(metrics.get("interception"))
        if value is not None:
            interceptions.append(value)

        total_tackles = _number(metrics.get("total_tackle"))
        won_tackles = _number(metrics.get("won_tackle"))
        if (
            total_tackles is not None
            and won_tackles is not None
            and total_tackles >= won_tackles >= 0
        ):
            tackles_total += total_tackles
            tackles_won += won_tackles
            tackle_matches += 1

        won_aerials = _number(metrics.get("aerial_won"))
        lost_aerials = _number(metrics.get("aerial_lost"))
        if (
            won_aerials is not None
            and lost_aerials is not None
            and won_aerials >= 0
            and lost_aerials >= 0
        ):
            aerial_won += won_aerials
            aerial_lost += lost_aerials
            aerial_matches += 1

        value = _number(metrics.get("total_clearance"))
        if value is not None:
            clearances.append(value)
        conceded = _number(metrics.get("shots_conceded"))
        if conceded is not None and conceded >= 0:
            total_shots_conceded += conceded
            total_shots_conceded_matches += 1

    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    values = {
        "possession": (mean(possession), len(possession)),
        "forward_pass_share": (
            forward_passes / total_passes * 100 if total_passes else None,
            forward_pass_matches,
        ),
        "final_third_entries": (mean(final_entries), len(final_entries)),
        "mid_third_recoveries": (mean(middle_wins), len(middle_wins)),
        "defensive_third_recoveries": (mean(defensive_third_wins), len(defensive_third_wins)),
        "attacking_third_recoveries": (mean(attacking_third_wins), len(attacking_third_wins)),
        "pressing_intensity": (mean(ppda_values), len(ppda_values)),
        "outside_box_shot_share": (
            obox_shots / total_shots * 100 if total_shots else None,
            shot_split_matches,
        ),
        "inside_box_shot_share": (
            inside_shots / total_shots * 100 if total_shots else None,
            shot_split_matches,
        ),
        "shots_per_match": (
            total_shot_attempts / total_shot_matches if total_shot_matches else None,
            total_shot_matches,
        ),
        "shots_on_target_share": (
            shots_on_target / shots_for_target_rate * 100 if shots_for_target_rate else None,
            target_rate_matches,
        ),
        "corners_into_box_share": (
            corners_into_box / corners_won * 100 if corners_won else None,
            corner_matches,
        ),
        "opposition_box_touches": (mean(box_touches), len(box_touches)),
        "final_third_passes": (
            final_third_passes / final_third_pass_matches if final_third_pass_matches else None,
            final_third_pass_matches,
        ),
        "final_third_pass_accuracy": (
            final_third_accurate_passes / final_third_passes * 100 if final_third_passes else None,
            final_third_pass_matches,
        ),
        "long_ball_share": (
            long_balls / total_passes_for_long_ball_share * 100 if total_passes_for_long_ball_share else None,
            long_ball_share_matches,
        ),
        "long_ball_accuracy": (
            accurate_long_balls / total_long_balls_for_accuracy * 100 if total_long_balls_for_accuracy else None,
            long_ball_accuracy_matches,
        ),
        "crosses_per_match": (mean(crosses_per_match), len(crosses_per_match)),
        "cross_accuracy": (
            accurate_crosses / total_crosses * 100 if total_crosses else None,
            cross_accuracy_matches,
        ),
        "ball_recoveries": (mean(ball_recoveries), len(ball_recoveries)),
        "possession_losses": (mean(possession_losses), len(possession_losses)),
        "controlled_possession_losses": (mean(controlled_possession_losses), len(controlled_possession_losses)),
        "interceptions": (mean(interceptions), len(interceptions)),
        "tackle_success": (tackles_won / tackles_total * 100 if tackles_total else None, tackle_matches),
        "aerial_duel_success": (
            aerial_won / (aerial_won + aerial_lost) * 100 if aerial_won + aerial_lost else None,
            aerial_matches,
        ),
        "clearances": (mean(clearances), len(clearances)),
        "shots_conceded_per_match": (
            total_shots_conceded / total_shots_conceded_matches
            if total_shots_conceded_matches
            else None,
            total_shots_conceded_matches,
        ),
    }
    return {
        name: {"value": value, "matches": count}
        for name, (value, count) in values.items()
    }


def _percentile(value: float | None, comparison: list[float]) -> int | None:
    if value is None or not comparison:
        return None
    below = sum(candidate < value for candidate in comparison)
    equal = sum(candidate == value for candidate in comparison)
    return round((below + equal / 2) / len(comparison) * 100)


@lru_cache(maxsize=128)
def get_team_tactical_profile(team_id: int, season: str = "all") -> dict[str, Any]:
    by_team, team_names = load_team_match_rows()
    selected = [
        row
        for row in by_team.get(team_id, [])
        if season in ("", "all") or row["season"] == season
    ]
    if not selected:
        return {
            "team_id": team_id,
            "team_name": team_names.get(team_id),
            "season": season,
            "matches": 0,
            "metrics": {},
        }

    selected_seasons = {row["season"] for row in selected}
    league_rows_by_team: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for other_id, rows in by_team.items():
        league_rows_by_team[other_id] = [
            row
            for row in rows
            if row["season"] in selected_seasons
        ]

    team_values = _aggregate(selected)
    team_row_count = len(selected)
    league_values = {
        other_id: _aggregate(rows)
        for other_id, rows in league_rows_by_team.items()
        if rows
    }

    response_metrics: dict[str, dict[str, Any]] = {}
    for key, definition in TACTICAL_METRICS.items():
        value = team_values[key]["value"]
        league_coverage_pct = None
        if key == "pressing_intensity":
            # PPDA coverage is inconsistent across historical seasons. Hide it unless
            # both this team and at least 16 league teams have >=80% match coverage.
            team_coverage = team_values[key]["matches"] / team_row_count if team_row_count else 0
            eligible = {
                other_id: aggregate
                for other_id, aggregate in league_values.items()
                if aggregate[key]["matches"] / len(league_rows_by_team[other_id]) >= 0.8
            }
            total_league_rows = sum(len(rows) for rows in league_rows_by_team.values())
            total_ppda_rows = sum(aggregate[key]["matches"] for aggregate in league_values.values())
            league_coverage = total_ppda_rows / total_league_rows if total_league_rows else 0
            league_coverage_pct = round(league_coverage * 100, 1)
            if team_coverage < 0.8 or league_coverage < 0.8 or len(eligible) < 16:
                value = None
                comparison = []
            comparison = [
                float(aggregate[key]["value"])
                for aggregate in eligible.values()
                if aggregate[key]["value"] is not None
            ] if value is not None else []
        else:
            comparison = [
                float(aggregate[key]["value"])
                for aggregate in league_values.values()
                if aggregate[key]["value"] is not None
            ]
        response_metrics[key] = {
            **definition,
            "value": round(float(value), 1) if value is not None else None,
            "league_average": round(sum(comparison) / len(comparison), 1) if comparison else None,
            "percentile": _percentile(float(value), comparison) if value is not None else None,
            "matches": int(team_values[key]["matches"]),
            "coverage_pct": round(team_values[key]["matches"] / team_row_count * 100, 1) if team_row_count else 0.0,
            "league_teams": len(comparison),
            **({"league_coverage_pct": league_coverage_pct} if league_coverage_pct is not None else {}),
        }

    return {
        "team_id": team_id,
        "team_name": team_names.get(team_id),
        "season": season,
        "matches": len({row["match_id"] for row in selected}),
        "metrics": response_metrics,
    }
