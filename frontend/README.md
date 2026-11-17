# Frontend (`frontend/`)

React 19 + Vite + Tailwind CSS client for multi-competition football fixtures, standings, team/player/referee analytics, match detail timelines, and ML prediction / model audit exploration.

> [!NOTE]
> **Documentation & Standards:**
> - **Architecture & API Mapping:** [`docs/model_api_integration.md`](../docs/model_api_integration.md) · [`docs/data_and_ui_catalog.md`](../docs/data_and_ui_catalog.md) · [`docs/README.md`](../docs/README.md)
> - **Design System & Modular Architecture:** [`restrained-ui-design-standard`](../.agents/skills/restrained-ui-design-standard/SKILL.md) · [`frontend-modular-architecture`](../.agents/skills/frontend-modular-architecture/SKILL.md)

## Module Layout (`frontend/src/`)
| Directory | Scope |
|---|---|
| [`components/README.md`](src/components/README.md) | Top-level tabs (including `PlayerCompareTab`), shared `common/` primitives (`CommandPalette`, `ErrorBoundary`, `ThemeToggle`), and domain UI subpackages |
| [`context/README.md`](src/context/README.md) | `CompetitionContext` registry, capability flags, and `ThemeContext` light/dark toggle |
| [`services/README.md`](src/services/README.md) | `fetch` / in-memory ETag transport (`apiClient.js`) and `/api/*` endpoint wrappers |
| [`utils/README.md`](src/utils/README.md) | URL query-string `router.js`, date formatters, badge fallbacks, knockout helpers, model gating, versioned cache |
| [`data/README.md`](src/data/README.md) | Competition season lists (`seasons.js`) and dynamic club badge registry (`teams.js`) |

## Dev & Verification Commands
```bash
npm run dev          # Vite dev server (http://localhost:5173, proxies /api -> :8000)
npm run lint:design  # Enforce radius ceiling, zero emojis, no gradients/blur/heavy weights
npm run lint         # oxlint static checks
npm run build        # Production Vite bundle -> dist/
```
