# Data Quality and Coverage

Snapshot generated 2026-10-24 from the local fixture cache and processed tables.
Run `python3 -m src.analytics.data_quality_report` to refresh this report.

## Match and source coverage

| Season | Fixtures | Completed | Upcoming | Stats files | Event streams | Details files |
|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2023-24 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2024-25 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2025-26 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2026-27 | 380 | 75 | 305 | 75/75 | 75/75 | 75/75 |

- Combined match table: 1,900 rows; 1,595 rows have both final scores.
- Combined feature table: 1,900 rows.
- Duplicate fixture IDs across the 5 season files: 0.
- Completed matches with referee name `Unknown`: 0/1595.

## Raw provider field coverage

Coverage counts team-match rows where the raw stats response contains a non-null value. `_reported` flags describe this stats endpoint only. Missing saves, corners, yellow-card, red-card, and offside values are filled from the match event stream when available; source values remain in `_raw` columns. If no stream is available, an omitted red-card value retains the sparse-event zero convention.

| Raw metric | Present team-match rows | Coverage |
|---|---:|---:|
| `won_corners` (corners) | 3122/3190 | 97.9% |
| `total_throws` (throw-ins) | 3190/3190 | 100.0% |
| `saves` (saves) | 2971/3190 | 93.1% |
| `total_yel_card` (yellow cards) | 2733/3190 | 85.7% |
| `total_red_card` (red cards) | 191/3190 | 6.0% |
| `total_offside` (offsides) | 2503/3190 | 78.5% |
| `total_scoring_att` (shots) | 3190/3190 | 100.0% |
| `possession_percentage` (possession) | 3190/3190 | 100.0% |
| `att_ibox_target` (xG proxy: inside-box shots on target) | 2742/3190 | 86.0% |
| `att_obox_target` (xG proxy: outside-box shots on target) | 1887/3190 | 59.2% |
| `big_chance_created` (xG proxy: big chances) | 2513/3190 | 78.8% |

## Event-based label recovery

The PulseLive match event stream contains team-attributed corner, yellow-card, red-card, and offside events, plus saved-shot events. For saves, the shooter's team is read from the event text and the save is attributed to the opposing goalkeeper's team. For a missing stats-endpoint value, processing fills the effective metric from that match's event stream and records an `_event_reconstructed` flag; the original provider value remains in a `_raw` column and `_reported` continues to indicate stats-endpoint coverage. Existing reported stats values take precedence.

| Target | Stats API complete match labels | Reconstructed team values | Usable match labels |
|---|---:|---:|---:|
| Saves | 1381 | 219 | 1595 |
| Corners | 1527 | 68 | 1595 |
| Cards | 1194 | 3456 | 1595 |
| Offsides | 980 | 687 | 1595 |

## Current target distributions

| Target | Complete-label rows | Mean | Variance / mean |
|---|---:|---:|---:|
| `total_corners` | 1595 | 10.276 | 1.116 |
| `total_throws` | 1595 | 35.485 | 1.939 |
| `total_saves` | 1595 | 6.024 | 1.076 |
| `total_cards` | 1595 | 4.048 | 1.115 |
| `total_offsides` | 1595 | 3.436 | 1.255 |
| `total_goals` | 1595 | 2.949 | 0.952 |

## Missing-stat selection audit

For each target, complete and incomplete match samples are compared by season and by match outcome. Team rates include home and away appearances; teams need at least 20 appearances to enter the ranking. The team table includes only targets with at least one missing team value.

| Target | Season | Played matches | Complete labels | Missing labels | Missing rate |
|---|---|---:|---:|---:|---:|
| Corners | 2022-23 | 380 | 367 | 13 | 3.4% |
| Corners | 2023-24 | 380 | 362 | 18 | 4.7% |
| Corners | 2024-25 | 380 | 356 | 24 | 6.3% |
| Corners | 2025-26 | 380 | 369 | 11 | 2.9% |
| Corners | 2026-27 | 75 | 73 | 2 | 2.7% |
| Throw-ins | 2022-23 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2023-24 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2024-25 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2025-26 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2026-27 | 75 | 75 | 0 | 0.0% |
| Saves | 2022-23 | 380 | 380 | 0 | 0.0% |
| Saves | 2023-24 | 380 | 380 | 0 | 0.0% |
| Saves | 2024-25 | 380 | 380 | 0 | 0.0% |
| Saves | 2025-26 | 380 | 380 | 0 | 0.0% |
| Saves | 2026-27 | 75 | 75 | 0 | 0.0% |
| Cards | 2022-23 | 380 | 380 | 0 | 0.0% |
| Cards | 2023-24 | 380 | 380 | 0 | 0.0% |
| Cards | 2024-25 | 380 | 380 | 0 | 0.0% |
| Cards | 2025-26 | 380 | 380 | 0 | 0.0% |
| Cards | 2026-27 | 75 | 75 | 0 | 0.0% |
| Offsides | 2022-23 | 380 | 380 | 0 | 0.0% |
| Offsides | 2023-24 | 380 | 380 | 0 | 0.0% |
| Offsides | 2024-25 | 380 | 380 | 0 | 0.0% |
| Offsides | 2025-26 | 380 | 380 | 0 | 0.0% |
| Offsides | 2026-27 | 75 | 75 | 0 | 0.0% |

### Missingness versus match outcome

| Target | Usable label coverage | Sample | Home win | Draw | Away win | Mean total goals |
|---|---:|---|---:|---:|---:|---:|
| Corners | 95.7% | Complete (1527) | 44.0% | 24.4% | 31.6% | 2.955 |
| Corners | 95.7% | Missing (68) | 50.0% | 20.6% | 29.4% | 2.794 |
| Throw-ins | 100.0% | Complete (1595) | 44.3% | 24.3% | 31.5% | 2.949 |
| Saves | 100.0% | Complete (1595) | 44.3% | 24.3% | 31.5% | 2.949 |
| Cards | 100.0% | Complete (1595) | 44.3% | 24.3% | 31.5% | 2.949 |
| Offsides | 100.0% | Complete (1595) | 44.3% | 24.3% | 31.5% | 2.949 |

### Teams with the highest missing rates

| Target | Team | Appearances | Missing | Missing rate |
|---|---|---:|---:|---:|
| Corners | Leicester City | 76 | 4 | 5.3% |
| Corners | Southampton | 76 | 4 | 5.3% |
| Corners | Wolverhampton Wanderers | 152 | 7 | 4.6% |
| Corners | Ipswich Town | 46 | 2 | 4.3% |
| Corners | Newcastle United | 159 | 6 | 3.8% |

## Known data limits

- Training excludes rows when a target remains unavailable. Saves, corners, cards, and offsides use event-derived fallbacks for missing stats values, so provider coverage no longer determines whether a saves match label is usable when a complete event stream is available.
- Event-derived values fill only missing stats values. The source metric remains available in a `_raw` column, and provider coverage remains visible through `_reported` flags. A match without a usable event stream and without the provider value can still have a missing target.
- The historical `home_xg`, `away_xg`, and `total_xg` columns are an aggregate-stat proxy. It is produced only when all required inputs are present; it is not official Opta shot-level xG or a trained xG model.
- The current season is incomplete. Its season holdout is marked partial and should not be compared as if it were a full-season result.
