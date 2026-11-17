# Context Module (`frontend/src/context/`)

Global competition selection state and capability-flag registry (`hasModel`, `hasAudit`, `richData`, `syncKinds`).

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Backend Registry:** [`src/competitions/README.md`](../../../src/competitions/README.md) · [`docs/data_sources.md`](../../../docs/data_sources.md)
> - **Key Entry Points:** [`CompetitionContext.jsx`](CompetitionContext.jsx) · [`competitionState.js`](competitionState.js) · [`ThemeContext.jsx`](ThemeContext.jsx) · [`themeState.js`](themeState.js)

## Business Rules & Invariants
- **Theme State (`ThemeContext.jsx`, `themeState.js`):** Persists light/dark mode (`pl-intel-theme` in `localStorage`) and toggles `:root.light` / `:root.dark` classes seamlessly.
- **Single Capability Registry (`COMPETITIONS`):** Defines `premier_league`, `champions_league`, and `europa_league` (plus national leagues when configured) flags:
  - `hasModel`: `true` for `premier_league`; `false` for UEFA cups.
  - `hasAudit`: `true` strictly for `premier_league` (`ModelAuditTab`).
  - `richData`: `true` for `premier_league`; `false` elsewhere (pre-loads club badges on mount via `getTeams`).
- **Persistence & Theme Attribute:** Persists selected competition key in `localStorage` (`plm_competition`) and mirrors `activeCompetition.key` onto `document.documentElement.dataset.competition`.
- **Change rule:** Keep capability flags aligned with `config/competitions.yaml` and `src/api/routes/predict.py`.
