# Data Quality and Coverage

Snapshot generated 2026-11-17 from the local fixture cache and processed tables.
Run `python3 -m src.analytics.data_quality_report` to refresh this report.

## Match and source coverage

| Season | Fixtures | Completed | Upcoming | Stats files | Event streams | Details files |
|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2023-24 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2024-25 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2025-26 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2026-27 | 380 | 88 | 292 | 88/88 | 88/88 | 88/88 |

- Combined match table: 1,900 rows; 1,608 rows have both final scores.
- Combined feature table: 1,900 rows.
- Duplicate fixture IDs across the 5 season files: 0.
- Completed matches with referee name `Unknown`: 0/1608.

## Raw provider field coverage

Coverage counts team-match rows where the raw stats response contains a non-null value. `_reported` flags describe this stats endpoint only. Missing saves, corners, yellow-card, red-card, and offside values are filled from the match event stream when available; source values remain in `_raw` columns. If no stream is available, an omitted red-card value retains the sparse-event zero convention.

| Raw metric | Present team-match rows | Coverage |
|---|---:|---:|
| `won_corners` (corners) | 3147/3216 | 97.9% |
| `total_throws` (throw-ins) | 3216/3216 | 100.0% |
| `saves` (saves) | 2995/3216 | 93.1% |
| `total_yel_card` (yellow cards) | 2755/3216 | 85.7% |
| `total_red_card` (red cards) | 194/3216 | 6.0% |
| `total_offside` (offsides) | 2526/3216 | 78.5% |
| `total_scoring_att` (shots) | 3216/3216 | 100.0% |
| `possession_percentage` (possession) | 3216/3216 | 100.0% |
| `att_ibox_target` (xG proxy: inside-box shots on target) | 2760/3216 | 85.8% |
| `att_obox_target` (xG proxy: outside-box shots on target) | 1902/3216 | 59.1% |
| `big_chance_created` (xG proxy: big chances) | 2533/3216 | 78.8% |

## Event-based label recovery

The PulseLive match event stream contains team-attributed corner, yellow-card, red-card, and offside events, plus saved-shot events. For saves, the shooter's team is read from the event text and the save is attributed to the opposing goalkeeper's team. For a missing stats-endpoint value, processing fills the effective metric from that match's event stream and records an `_event_reconstructed` flag; the original provider value remains in a `_raw` column and `_reported` continues to indicate stats-endpoint coverage. Existing reported stats values take precedence.

| Target | Stats API complete match labels | Reconstructed team values | Usable match labels |
|---|---:|---:|---:|
| Saves | 1392 | 221 | 1608 |
| Corners | 1539 | 69 | 1608 |
| Cards | 1203 | 3483 | 1608 |
| Offsides | 990 | 690 | 1608 |

## Current target distributions

| Target | Complete-label rows | Mean | Variance / mean |
|---|---:|---:|---:|
| `total_corners` | 1608 | 10.277 | 1.117 |
| `total_throws` | 1608 | 35.495 | 1.939 |
| `total_saves` | 1608 | 6.018 | 1.080 |
| `total_cards` | 1608 | 4.047 | 1.110 |
| `total_offsides` | 1608 | 3.440 | 1.252 |
| `total_goals` | 1608 | 2.942 | 0.951 |

## Missing-stat selection audit

For each target, complete and incomplete match samples are compared by season and by match outcome. Team rates include home and away appearances; teams need at least 20 appearances to enter the ranking. The team table includes only targets with at least one missing team value.

| Target | Season | Played matches | Complete labels | Missing labels | Missing rate |
|---|---|---:|---:|---:|---:|
| Corners | 2022-23 | 380 | 367 | 13 | 3.4% |
| Corners | 2023-24 | 380 | 362 | 18 | 4.7% |
| Corners | 2024-25 | 380 | 356 | 24 | 6.3% |
| Corners | 2025-26 | 380 | 369 | 11 | 2.9% |
| Corners | 2026-27 | 88 | 85 | 3 | 3.4% |
| Throw-ins | 2022-23 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2023-24 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2024-25 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2025-26 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2026-27 | 88 | 88 | 0 | 0.0% |
| Saves | 2022-23 | 380 | 380 | 0 | 0.0% |
| Saves | 2023-24 | 380 | 380 | 0 | 0.0% |
| Saves | 2024-25 | 380 | 380 | 0 | 0.0% |
| Saves | 2025-26 | 380 | 380 | 0 | 0.0% |
| Saves | 2026-27 | 88 | 88 | 0 | 0.0% |
| Cards | 2022-23 | 380 | 380 | 0 | 0.0% |
| Cards | 2023-24 | 380 | 380 | 0 | 0.0% |
| Cards | 2024-25 | 380 | 380 | 0 | 0.0% |
| Cards | 2025-26 | 380 | 380 | 0 | 0.0% |
| Cards | 2026-27 | 88 | 88 | 0 | 0.0% |
| Offsides | 2022-23 | 380 | 380 | 0 | 0.0% |
| Offsides | 2023-24 | 380 | 380 | 0 | 0.0% |
| Offsides | 2024-25 | 380 | 380 | 0 | 0.0% |
| Offsides | 2025-26 | 380 | 380 | 0 | 0.0% |
| Offsides | 2026-27 | 88 | 88 | 0 | 0.0% |

### Missingness versus match outcome

| Target | Usable label coverage | Sample | Home win | Draw | Away win | Mean total goals |
|---|---:|---|---:|---:|---:|---:|
| Corners | 95.7% | Complete (1539) | 44.0% | 24.5% | 31.5% | 2.949 |
| Corners | 95.7% | Missing (69) | 50.7% | 20.3% | 29.0% | 2.783 |
| Throw-ins | 100.0% | Complete (1608) | 44.3% | 24.3% | 31.4% | 2.942 |
| Saves | 100.0% | Complete (1608) | 44.3% | 24.3% | 31.4% | 2.942 |
| Cards | 100.0% | Complete (1608) | 44.3% | 24.3% | 31.4% | 2.942 |
| Offsides | 100.0% | Complete (1608) | 44.3% | 24.3% | 31.4% | 2.942 |

### Teams with the highest missing rates

| Target | Team | Appearances | Missing | Missing rate |
|---|---|---:|---:|---:|
| Corners | Leicester City | 76 | 4 | 5.3% |
| Corners | Southampton | 76 | 4 | 5.3% |
| Corners | Wolverhampton Wanderers | 152 | 7 | 4.6% |
| Corners | Ipswich Town | 47 | 2 | 4.3% |
| Corners | Newcastle United | 160 | 6 | 3.8% |

## Known data limits

- Training excludes rows when a target remains unavailable. Saves, corners, cards, and offsides use event-derived fallbacks for missing stats values, so provider coverage no longer determines whether a saves match label is usable when a complete event stream is available.
- Event-derived values fill only missing stats values. The source metric remains available in a `_raw` column, and provider coverage remains visible through `_reported` flags. A match without a usable event stream and without the provider value can still have a missing target.
- The historical `home_xg`, `away_xg`, and `total_xg` columns are an aggregate-stat proxy. It is produced only when all required inputs are present; it is not official Opta shot-level xG or a trained xG model.
- The current season is incomplete. Its season holdout is marked partial and should not be compared as if it were a full-season result.
