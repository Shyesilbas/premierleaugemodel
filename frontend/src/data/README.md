# Frontend Data Module (`frontend/src/data/`)

Competition season lists and runtime club metadata / crest lookup helpers.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Competition Config:** [`src/competitions/README.md`](../../../src/competitions/README.md) · [`frontend/src/context/README.md`](../context/README.md)
> - **Key Entry Points:** [`seasons.js`](seasons.js) · [`teams.js`](teams.js)

## Business Rules & Invariants
- **Competition Season Lists (`seasons.js`):** Defines `PREMIER_LEAGUE_SEASONS` (includes `'all'`), `UEFA_SEASONS`, and `NATIONAL_LEAGUE_SEASONS` exposed via `seasonsFor`.
- **Dynamic Badge Registry (`teams.js`):** Seeds `TEAMS` / `TEAM_MAP` and dynamically populates additional competition clubs via `registerTeamLogo`, `registerTeamInfo`, and `registerLogosFrom` resolved by `getTeam`.
- **Change rule:** Update `seasonsFor` whenever a new season or league is onboarded in `config/competitions.yaml`.
