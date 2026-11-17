# Services Module (`frontend/src/services/`)

REST client wrappers connecting frontend views to FastAPI `/api/*` endpoints.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Backend Routes:** [`src/api/README.md`](../../../src/api/README.md) · [`scripts/check_api_endpoints.py`](../../../scripts/check_api_endpoints.py)
> - **Key Entry Points:** [`apiClient.js`](apiClient.js) · [`competitionService.js`](competitionService.js) · [`matchService.js`](matchService.js) · [`teamService.js`](teamService.js) · [`playerService.js`](playerService.js) · [`refereeService.js`](refereeService.js) · [`statsService.js`](statsService.js) · [`auditService.js`](auditService.js)

## Business Rules & Invariants
- **Shared Transport ([`apiClient.js`](apiClient.js)):** Exports `getJson`, `getJsonChecked`, `requestJson`, `loadApi` (in-memory deduplicated promise cache), `loadApiFresh` (`cache: 'no-cache'` ETag revalidation for volatile fixtures/standings/matches), `postApi`, `invalidateApiCache`, and `withQuery`. Never scatter raw `/api/` fetches inside presentation components; add callers here so endpoint parity stays auditable.
- **Logo Registration Hook:** `competitionService`, `teamService`, `playerService`, and `refereeService` pass payloads through `registerLogosFrom` so dynamic club badges resolve seamlessly.
- **Admin Header Convention:** `competitionService` reads `localStorage.getItem('plm_admin_token')` into `X-Admin-Token` for `/api/admin/*` sync and single/batch match refresh endpoints.
- **Change rule:** After modifying any endpoint path or query param, verify parity with `python3 scripts/check_api_endpoints.py`.
