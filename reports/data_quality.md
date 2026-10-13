# Data Quality and Coverage

Snapshot generated 2026-10-13 from the local fixture cache and processed tables.
Run `python3 -m src.analytics.data_quality_report` to refresh this report.

## Match and source coverage

| Season | Fixtures | Completed | Upcoming | Stats files | Event streams | Details files |
|---|---:|---:|---:|---:|---:|---:|
| 2022-23 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2023-24 | 380 | 380 | 0 | 380/380 | 380/380 | 379/380 |
| 2024-25 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2025-26 | 380 | 380 | 0 | 380/380 | 380/380 | 380/380 |
| 2026-27 | 380 | 60 | 320 | 60/60 | 60/60 | 60/60 |

- Combined match table: 1,900 rows; 1,580 rows have both final scores.
- Combined feature table: 1,900 rows.
- Duplicate fixture IDs across the 5 season files: 0.
- Completed matches with referee name `Unknown`: 1/1580.

## Raw provider field coverage

Coverage counts team-match rows where the raw stats response contains a non-null value. `_reported` flags describe this stats endpoint only. Missing yellow-card, red-card, and offside values are filled from the match event stream when available; source values remain in `_raw` columns. If no stream is available, an omitted red-card value retains the sparse-event zero convention.

| Raw metric | Present team-match rows | Coverage |
|---|---:|---:|
| `won_corners` (corners) | 3093/3160 | 97.9% |
| `total_throws` (throw-ins) | 3160/3160 | 100.0% |
| `saves` (saves) | 2946/3160 | 93.2% |
| `total_yel_card` (yellow cards) | 2704/3160 | 85.6% |
| `total_red_card` (red cards) | 187/3160 | 5.9% |
| `total_offside` (offsides) | 2475/3160 | 78.3% |
| `total_scoring_att` (shots) | 3160/3160 | 100.0% |
| `possession_percentage` (possession) | 3160/3160 | 100.0% |
| `att_ibox_target` (xG proxy: inside-box shots on target) | 2718/3160 | 86.0% |
| `att_obox_target` (xG proxy: outside-box shots on target) | 1869/3160 | 59.1% |
| `big_chance_created` (xG proxy: big chances) | 2494/3160 | 78.9% |

## Event-based label recovery

The PulseLive match event stream contains team-attributed yellow-card, red-card, and offside events. For a missing stats-endpoint value, processing fills the effective metric from that match's event stream and records an `_event_reconstructed` flag; the original provider value remains in a `_raw` column and `_reported` continues to indicate stats-endpoint coverage. Existing reported stats values take precedence.

| Target | Stats API complete match labels | Reconstructed team values | Usable match labels |
|---|---:|---:|---:|
| Cards | 1180 | 3429 | 1580 |
| Offsides | 967 | 685 | 1580 |

## Current target distributions

| Target | Complete-label rows | Mean | Variance / mean |
|---|---:|---:|---:|
| `total_corners` | 1513 | 10.419 | 1.058 |
| `total_throws` | 1580 | 35.528 | 1.942 |
| `total_saves` | 1371 | 6.420 | 0.909 |
| `total_cards` | 1580 | 4.041 | 1.116 |
| `total_offsides` | 1580 | 3.431 | 1.261 |
| `total_goals` | 1580 | 2.954 | 0.953 |

## Missing-stat selection audit

For each target, complete and incomplete match samples are compared by season and by match outcome. Team rates include home and away appearances; teams need at least 20 appearances to enter the ranking. The team table includes only targets with at least one missing team value.

| Target | Season | Played matches | Complete labels | Missing labels | Missing rate |
|---|---|---:|---:|---:|---:|
| Corners | 2022-23 | 380 | 367 | 13 | 3.4% |
| Corners | 2023-24 | 380 | 362 | 18 | 4.7% |
| Corners | 2024-25 | 380 | 356 | 24 | 6.3% |
| Corners | 2025-26 | 380 | 369 | 11 | 2.9% |
| Corners | 2026-27 | 60 | 59 | 1 | 1.7% |
| Throw-ins | 2022-23 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2023-24 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2024-25 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2025-26 | 380 | 380 | 0 | 0.0% |
| Throw-ins | 2026-27 | 60 | 60 | 0 | 0.0% |
| Saves | 2022-23 | 380 | 315 | 65 | 17.1% |
| Saves | 2023-24 | 380 | 340 | 40 | 10.5% |
| Saves | 2024-25 | 380 | 335 | 45 | 11.8% |
| Saves | 2025-26 | 380 | 328 | 52 | 13.7% |
| Saves | 2026-27 | 60 | 53 | 7 | 11.7% |
| Cards | 2022-23 | 380 | 380 | 0 | 0.0% |
| Cards | 2023-24 | 380 | 380 | 0 | 0.0% |
| Cards | 2024-25 | 380 | 380 | 0 | 0.0% |
| Cards | 2025-26 | 380 | 380 | 0 | 0.0% |
| Cards | 2026-27 | 60 | 60 | 0 | 0.0% |
| Offsides | 2022-23 | 380 | 380 | 0 | 0.0% |
| Offsides | 2023-24 | 380 | 380 | 0 | 0.0% |
| Offsides | 2024-25 | 380 | 380 | 0 | 0.0% |
| Offsides | 2025-26 | 380 | 380 | 0 | 0.0% |
| Offsides | 2026-27 | 60 | 60 | 0 | 0.0% |

### Missingness versus match outcome

| Target | Label coverage | Sample | Home win | Draw | Away win | Mean total goals |
|---|---:|---|---:|---:|---:|---:|
| Corners | 95.8% | Complete (1513) | 44.0% | 24.6% | 31.5% | 2.960 |
| Corners | 95.8% | Missing (67) | 50.7% | 19.4% | 29.9% | 2.806 |
| Throw-ins | 100.0% | Complete (1580) | 44.2% | 24.4% | 31.4% | 2.954 |
| Saves | 86.8% | Complete (1371) | 44.9% | 24.3% | 30.8% | 2.975 |
| Saves | 86.8% | Missing (209) | 39.7% | 24.9% | 35.4% | 2.813 |
| Cards | 100.0% | Complete (1580) | 44.2% | 24.4% | 31.4% | 2.954 |
| Offsides | 100.0% | Complete (1580) | 44.2% | 24.4% | 31.4% | 2.954 |

### Teams with the highest missing rates

| Target | Team | Appearances | Missing | Missing rate |
|---|---|---:|---:|---:|
| Corners | Leicester City | 76 | 4 | 5.3% |
| Corners | Southampton | 76 | 4 | 5.3% |
| Corners | Wolverhampton Wanderers | 152 | 7 | 4.6% |
| Corners | Aston Villa | 158 | 6 | 3.8% |
| Corners | Newcastle United | 158 | 6 | 3.8% |
| Saves | Arsenal | 158 | 24 | 15.2% |
| Saves | Manchester City | 158 | 21 | 13.3% |
| Saves | Southampton | 76 | 10 | 13.2% |
| Saves | Crystal Palace | 158 | 15 | 9.5% |
| Saves | Leeds United | 82 | 7 | 8.5% |

## Known data limits

- Training excludes rows when a target remains unavailable. Cards and offsides now use event-derived fallbacks for missing stats values; corners and saves still have incomplete target coverage and can select for matches with better provider coverage.
- Event-derived values fill only missing yellow-card, red-card, and offside stats. The source metric remains available in a `_raw` column, and provider coverage remains visible through `_reported` flags. A match without a usable event stream and without the provider value can still have a missing target.
- The historical `home_xg`, `away_xg`, and `total_xg` columns are an aggregate-stat proxy. It is produced only when all required inputs are present; it is not official Opta shot-level xG or a trained xG model.
- The current season is incomplete. Its season holdout is marked partial and should not be compared as if it were a full-season result.
