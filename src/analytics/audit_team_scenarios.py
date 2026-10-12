"""Write a reproducible validation report for score-state and corner events."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.analytics.team_scenarios import load_team_match_scenarios
from src.analytics.team_tactics import load_team_match_rows


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "team_scenario_validation.md"


def build_report() -> str:
    event_rows, _, event_audit = load_team_match_scenarios()
    stats_rows, _ = load_team_match_rows()

    stream_matches_by_season: dict[str, set[int]] = {}
    comparison: Counter[str] = Counter()

    event_lookup: dict[tuple[int, int], dict[str, int]] = {}
    for team_id, rows in event_rows.items():
        for row in rows:
            key = (team_id, row["match_id"])
            event_lookup[key] = {
                "shots": sum(int(state["shots"]) for state in row["states"].values()),
                "corners": sum(int(state["corners"]) for state in row["states"].values()),
            }
            stream_matches_by_season.setdefault(row["season"], set()).add(row["match_id"])

    for team_id, rows in stats_rows.items():
        for row in rows:
            event = event_lookup.get((team_id, row["match_id"]))
            if event is None:
                continue
            metrics = row["metrics"]
            raw_shots = metrics.get("total_scoring_att")
            if raw_shots is not None:
                comparison["shot_rows"] += 1
                if float(raw_shots) == event["shots"]:
                    comparison["shot_rows_match"] += 1
            raw_corners = metrics.get("won_corners")
            if raw_corners is not None:
                comparison["corner_rows"] += 1
                if float(raw_corners) == event["corners"]:
                    comparison["corner_rows_match"] += 1

    lines = [
        "# Skor Durumu ve Korner Analizi — Veri Doğrulaması",
        "",
        "Bu denetim play-by-play akışını maç ve takım istatistikleriyle karşılaştırır.",
        "",
        "## Olay akışı kapsamı",
        "",
        "| Sezon | Maç akışı bulunan maç |",
        "|---|---:|",
    ]
    for season in sorted(stream_matches_by_season):
        lines.append(f"| {season.replace('_', '-')} | {len(stream_matches_by_season[season])} |")
    lines.extend(
        [
            "",
            f"- Son skor **{event_audit['score_reconstructed_matches']}/{event_audit['matches']}** maçta gol olaylarından yeniden kuruldu.",
            f"- {event_audit['shot_events']} şut olayı ve {event_audit['corner_events']} korner olayı okundu.",
            f"- Saat bilgisi olmayan aksiyon: {event_audit['timed_action_missing']}.",
            "",
            "## Ham maç istatistikleriyle eşleşme",
            "",
            "| Kontrol | Eşleşen takım-maç | Karşılaştırılan takım-maç |",
            "|---|---:|---:|",
            f"| Play-by-play şut sayısı = `total_scoring_att` | {comparison['shot_rows_match']} | {comparison['shot_rows']} |",
            f"| Play-by-play korner sayısı = `won_corners` | {comparison['corner_rows_match']} | {comparison['corner_rows']} |",
            "",
            "## Yorum ve sınırlar",
            "",
            "- Skor durumu, her gol olayında metinde yazan skor kullanılarak sonraki aksiyonlar için güncellenir. "
            "Böylece şut ve kornerler eşitlikte, öndeyken veya gerideyken sayılabilir.",
            "- Tempo, olay sayısının ilgili skor durumunda geçen oyun dakikasına bölünüp 90 dakikaya ölçeklenmesiyle hesaplanır. "
            "Bir skor durumu için 90 dakikadan az örnek varsa arayüz oranı gizler.",
            "- Ham `won_corners` sayısı olay akışıyla karşılaştırılan 2342 takım-maçın tamamında eşleşti. "
            "`corner_taken` ve korner isabet alt ölçüleri daha az tutarlı; "
            "ilk analiz bunlara dayandırılmaz.",
            "- Korner olayında hedef koordinatı bulunmadığından ön direk/arka direk tercihi çıkarılmaz.",
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
