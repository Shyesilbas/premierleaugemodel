---
name: frontend-modular-architecture
description: Use when creating, refactoring, or auditing a frontend component, tab, hook, context, service, or utility in frontend/src/.
---

# Frontend Modular Architecture Playbook

> **References (read on demand):**
> - [`references/module-readme-template.md`](references/module-readme-template.md) — Template for `frontend/src/<module>/README.md` (`<= 450` words).
> - Architecture & UI contract docs: [`docs/model_api_integration.md`](../../../docs/model_api_integration.md) and [`docs/data_and_ui_catalog.md`](../../../docs/data_and_ui_catalog.md).
> - Visual and zero-emoji rules: `restrained-ui-design-standard`.

## 1. Stack & Module Layout (`frontend/src/`)
- **Stack:** React 19 + Vite, Tailwind CSS v3 (`frontend/tailwind.config.js` + CSS variables in `frontend/src/index.css`), `lucide-react` icons, native `fetch` wrappers in `src/services/apiClient.js`.
- **Module Directories:**
  - `components/`: Top-level views (`FixturesTab`, `TeamProfilesTab`, `PlayerProfilesTab`, `RefereesTab`, `MatchDetailPage`, `ModelAuditTab`, `StatsTab`, `Sidebar`) and domain folders (`common/`, `fixtures/`, `match-detail/`, `model-audit/`, `player-profile/`, `stats/`, `team-profile/`).
  - `context/`: `CompetitionContext.jsx` (active competition selection, `hasModel`, `hasAudit`, `richData`, `syncKinds`).
  - `services/`: Feature API wrappers (`apiClient.js`, `competitionService.js`, `matchService.js`, `teamService.js`, `playerService.js`, `refereeService.js`, `statsService.js`, `auditService.js`).
  - `utils/`: Pure formatters, badge fallbacks, knockout helpers, model gating (`matchModel.js`), and TTL cache (`teamProfileCache.js`).
  - `data/`: Static/hybrid competition seasons (`seasons.js`) and club badge registry (`teams.js`).

## 2. State, Effects & Code-Splitting Discipline
1. **Clean React Effects:** Never trigger cascading synchronous `setState` inside `useEffect` (`react-hooks/set-state-in-effect`), abort stale async fetches on dependency/unmount changes (`AbortController`), and keep dependency arrays complete (`exhaustive-deps`).
2. **Code-Splitting:** Lazy-load secondary top-level tabs and heavy detail views (`React.lazy` + `Suspense` with matching `Skeleton` fallback) to keep the initial JS chunk lean.
3. **Services Layer Only:** Keep all `fetch` calls inside `frontend/src/services/*.js` using `/api/...` paths so `scripts/check_api_endpoints.py` validates FastAPI route parity cleanly.
4. **Capability Flags:** Gate model UI via `hasModel` / `hasModelPrediction` and audit UI via `hasAudit` rather than hardcoding competition keys.

## 3. Pre-Completion Checklist
- [ ] Zero `oxlint` warnings/errors (`npm run lint`).
- [ ] Zero design-system violations (`npm run lint:design`).
- [ ] Production bundle builds cleanly (`npm run build`).
- [ ] API parity passes (`python3 scripts/check_api_endpoints.py`).
- [ ] Affected `frontend/src/<module>/README.md` hubs updated and within 450 words.
