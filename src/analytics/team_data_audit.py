"""Audit completeness of raw team-level Premier League match statistics.

Run from the repository root with:
    python3 -m src.analytics.team_data_audit

The report deliberately distinguishes a missing metric from a reported zero.
The current season is reported separately from completed seasons.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW_MATCHES = ROOT / "data" / "raw" / "matches"
REPORT = ROOT / "reports" / "team_tactical_data_audit.md"

CORE_METRICS = {
    "Topa sahip olma ve ilerleme": [
        "possession_percentage",
        "total_pass",
        "accurate_pass",
        "total_fwd_zone_pass",
        "accurate_fwd_zone_pass",
        "total_back_zone_pass",
        "accurate_back_zone_pass",
        "final_third_entries",
    ],
    "Üçüncü bölgelerde top kazanımı": [
        "poss_won_def_3rd",
        "poss_won_mid_3rd",
        "poss_won_att_3rd",
    ],
    "Şut": [
        "total_scoring_att",
        "attempts_ibox",
        "attempts_obox",
        "att_obox_target",
        "att_obox_blocked",
        "att_obox_miss",
    ],
    "Korner ve duran top": [
        "won_corners",
        "corner_taken",
        "total_corners_intobox",
        "accurate_corners_intobox",
        "att_corner",
        "att_assist_setplay",
    ],
    "Kapsaması sınırlı adaylar": [
        "ppda",
        "carries",
        "progressive_carries",
        "pen_area_entries_open_play",
    ],
}


def season_from_label(label: str) -> str:
    match = re.search(r"(20\d{2})\s*[/_-]\s*(\d{2,4})", label)
    if not match:
        return label or "unknown"
    start = int(match.group(1))
    end_text = match.group(2)
    end = int(end_text) if len(end_text) == 4 else (start // 100) * 100 + int(end_text)
    return f"{start}_{str(end)[-2:]}"


def load_stats() -> tuple[dict[str, dict[str, Any]], dict[str, Counter[str]], Counter[str]]:
    seasons: dict[str, dict[str, Any]] = {}
    metric_names_by_season: dict[str, Counter[str]] = defaultdict(Counter)
    all_metric_names: Counter[str] = Counter()

    for path in sorted(RAW_MATCHES.glob("*_stats.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        entity = payload.get("entity", {})
        gameweek = entity.get("gameweek", {})
        season_label = gameweek.get("compSeason", {}).get("label", "unknown")
        season = season_from_label(season_label)
        state = seasons.setdefault(
            season,
            {
                "label": season_label,
                "match_ids": set(),
                "team_rows": 0,
                "metric_present": Counter(),
                "metric_zero": Counter(),
                "metric_null": Counter(),
            },
        )

        match_id = entity.get("id")
        if match_id is not None:
            state["match_ids"].add(match_id)

        for team_id, team_stats in payload.get("data", {}).items():
            metric_rows = team_stats.get("M", []) if isinstance(team_stats, dict) else []
            state["team_rows"] += 1
            for metric in metric_rows:
                if not isinstance(metric, dict) or not metric.get("name"):
                    continue
                name = metric["name"]
                all_metric_names[name] += 1
                metric_names_by_season[season][name] += 1
                if "value" not in metric or metric["value"] is None:
                    state["metric_null"][name] += 1
                else:
                    state["metric_present"][name] += 1
                    try:
                        if float(metric["value"]) == 0:
                            state["metric_zero"][name] += 1
                    except (TypeError, ValueError):
                        pass

    return seasons, metric_names_by_season, all_metric_names


def format_pct(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "—"


def build_report() -> str:
    seasons, metric_names_by_season, all_metric_names = load_stats()
    ordered_seasons = sorted(seasons)
    shot_split = Counter()
    for path in sorted(RAW_MATCHES.glob("*_stats.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for team_stats in payload.get("data", {}).values():
            metrics = {
                item.get("name"): item.get("value")
                for item in team_stats.get("M", [])
                if isinstance(item, dict) and item.get("name")
            }
            try:
                total = float(metrics["total_scoring_att"])
                inside = float(metrics["attempts_ibox"]) if metrics.get("attempts_ibox") is not None else None
                outside = float(metrics["attempts_obox"]) if metrics.get("attempts_obox") is not None else None
            except (KeyError, TypeError, ValueError):
                shot_split["unresolved"] += 1
                continue
            if inside is not None and outside is not None:
                shot_split["complete"] += 1
                if inside + outside == total:
                    shot_split["consistent"] += 1
                else:
                    shot_split["mismatch"] += 1
            elif inside is not None and outside is None and inside == total:
                shot_split["infer_outside_zero"] += 1
            elif outside is not None and inside is None and outside == total:
                shot_split["infer_inside_zero"] += 1
            else:
                shot_split["unresolved"] += 1

    lines = [
        "# Takım Taktik Analizi — Veri Kapsamı Denetimi",
        "",
        "Bu rapor `data/raw/matches/*_stats.json` dosyalarındaki takım düzeyi `M` istatistiklerini inceler. "
        "Bir metriğin dosyada bulunmaması sıfır kabul edilmez.",
        "",
        "## Sezon kapsamı",
        "",
        "| Sezon | İstatistik dosyası olan maç | Takım-maç satırı | Farklı metrik adı |",
        "|---|---:|---:|---:|",
    ]
    for season in ordered_seasons:
        state = seasons[season]
        lines.append(
            f"| {season.replace('_', '-')} | {len(state['match_ids'])} | {state['team_rows']} | "
            f"{len(metric_names_by_season[season])} |"
        )
    lines.extend(
        [
            "",
            f"Tüm sezonlarda toplam **{len(all_metric_names)} farklı metrik adı** bulundu. "
            "2026-27 sezonu tamamlanmış sezonlarla aynı örneklem gibi değerlendirilmemelidir.",
            "",
            "## İlk sürüm için aday metriklerin kapsaması",
            "",
            "Kapsama, ilgili sezondaki takım-maç satırlarında metriğin sayısal değerinin bulunma oranıdır. "
            "Parantez içindeki değer, mevcut ve sıfır olmayan değerlerin sayısını gösterir.",
            "",
            "| Grup | Metrik | Sezon | Değer bulunan satır | Kapsama | Açıkça sıfır |",
            "|---|---|---|---:|---:|---:|",
        ]
    )

    for group, metrics in CORE_METRICS.items():
        for metric in metrics:
            for season in ordered_seasons:
                state = seasons[season]
                denominator = state["team_rows"]
                present = state["metric_present"][metric]
                zero = state["metric_zero"][metric]
                lines.append(
                    f"| {group} | `{metric}` | {season.replace('_', '-')} | {present}/{denominator} "
                    f"({present - zero} sıfır olmayan) | {format_pct(present, denominator)} | {zero} |"
                )

    lines.extend(
        [
            "",
            "## İlk sürüm için karar",
            "",
            "- İleri/geri bölge pasları, son üç bölgeye girişler ve orta bölge top kazanımı ana karşılaştırma setine adaydır; "
            "sezonlar arası kapsama ayrıca yukarıdaki tabloda gösterilir.",
            f"- Şut bölgesi toplamı, iki alanın da bulunduğu {shot_split['complete']} takım-maçın "
            f"{shot_split['consistent']}'inde `attempts_ibox + attempts_obox = total_scoring_att` eşitliğini sağladı "
            f"({shot_split['mismatch']} tutarsızlık). Bir taraf eksik ve diğer taraf toplam şuta eşitse eksik taraf güvenle sıfır alınabilir; "
            f"{shot_split['unresolved']} satır çözümsüz kaldı.",
            "- Ceza sahası dışı şut payı, yalnızca doğrulanmış şut bölgesi satırlarından hesaplanır; "
            "uzaktan isabet/blok/kaçan şut alt metrikleri belirgin biçimde daha seyrek olduğu için ilk sürümde kullanılmaz.",
            "- PPDA, top sürme ve açık oyunda ceza sahasına giriş metrikleri sezonlara göre değişken kapsamalıdır; "
            "kapsama denetimi yapılmadan çok sezonlu sıralamalara katılmamalıdır.",
            "- `total_corners_intobox / won_corners`, ceza sahasına gönderilen kornerlerin kullanılan kornerlere oranı olarak "
            "hesaplanabilir; bu, kısa korner veya hedef bölge bilgisini vermez.",
            "- `accurate_corners_intobox` pozitif `total_corners_intobox` değerleri varken de sıkça eksiktir; "
            "eksik değerleri sıfır varsayarak isabet oranı hesaplanmamalıdır.",
            "- Özet Parquet üretiminde bulunmayan metriklerin `0` ile doldurulduğu görülüyor. "
            "Taktiksel hesaplama ham JSON değerlerini kullanmalı veya işlenmiş tabloda eksikliği korumalıdır.",
            "",
            "## Yöntem notu",
            "",
            "Bu denetim metrik tanımlarının anlamsal doğruluğunu kanıtlamaz; ham dosyalardaki sayısal değer "
            "kapsamasını ve temel şut bölgesi eşitliğini ölçer. Ham alanın yokluğu yalnızca eşitlik koşulu "
            "sağlandığında sıfır olarak yorumlanır.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(), encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
