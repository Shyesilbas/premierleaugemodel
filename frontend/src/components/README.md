# UI Components Module

Top-level feature views, shared primitives (`common/`), and domain subpackages for multi-competition fixtures, profiles, statistics, match detail, and ML prediction / audit views.

> [!NOTE]
> **Related Documentation & Standards:**
> - **Design & Architecture:** [`restrained-ui-design-standard`](../../../.agents/skills/restrained-ui-design-standard/SKILL.md) · [`frontend-modular-architecture`](../../../.agents/skills/frontend-modular-architecture/SKILL.md) · [`frontend/README.md`](../../README.md)
> - **Backend Counterpart:** [`src/api/README.md`](../../../src/api/README.md) · [`docs/model_api_integration.md`](../../../docs/model_api_integration.md)
> - **Key Entry Points:** [`App.jsx`](../App.jsx) · [`Sidebar.jsx`](Sidebar.jsx) · [`FixturesTab.jsx`](FixturesTab.jsx) · [`MatchDetailPage.jsx`](MatchDetailPage.jsx) · [`PredictorTab.jsx`](PredictorTab.jsx) · [`ModelAuditTab.jsx`](ModelAuditTab.jsx) · [`TeamProfilesTab.jsx`](TeamProfilesTab.jsx) · [`PlayerProfilesTab.jsx`](PlayerProfilesTab.jsx) · [`PlayerCompareTab.jsx`](PlayerCompareTab.jsx) · [`RefereesTab.jsx`](RefereesTab.jsx) · [`StatsTab.jsx`](StatsTab.jsx)

## Business Rules & Invariants
- **Shared Primitives (`common/`):** `Badge`, `Button`, `Card`, `CommandPalette` (`Cmd+K` club/player quick jump), `CompetitionSelector`, `EmptyState`, `ErrorBoundary`, `InlineError`, `Input`, `KpiCard`, `ModalDialog` (`<dialog closedby="any">`), `Select`, `Skeleton`, `TabBar`, `ThemeToggle`. Data views should render consistent loading skeletons, empty states, and retryable error states rather than bespoke spinners.
- **Capability-Gated Navigation:** `ModelAuditTab` is shown only when `hasAudit` is true (`premier_league`), and prediction views check `hasModel` / `hasModelPrediction` so UCL/UEL never render model widgets.
- **Domain Subpackages:** `fixtures/` (`FixturesGameweeksView`, `FixturesStandingsView`, `FixtureMatchCard`, `FixtureMatchRow`, `KnockoutBracket`), `match-detail/` (`MatchPredictionTab`, `MatchEventsTab`, `MatchTimelineTab`, `MatchLineupsTab`, `MatchStatsTab`, `MatchOddsTab`, `MatchScoreboard`), `model-audit/` (`AuditMatchCard`, `AuditBaselinesSection`, `AuditChartsSection`, `AuditBacktestCalibration`), `player-profile/` (`PlayerSearchPanel`, `PlayerDiscoveryGrid`, `PlayerProfileHeader`, `PlayerFormTrend`, `PlayerMatchHistory`), `stats/`, and `team-profile/`.
- **Change rule:** Run `npm run lint:design && npm run lint && npm run build` inside `frontend/` after any component or CSS edit.
