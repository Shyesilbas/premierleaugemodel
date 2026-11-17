# Utilities Module (`frontend/src/utils/`)

Pure helper functions for date sorting, badge image fallbacks, knockout tie notes, model eligibility checks, and localStorage data-version cache invalidation.

> [!NOTE]
> **Related Documentation & Runbooks:**
> - **Frontend Hub:** [`frontend/README.md`](../../README.md) · [`frontend/src/services/README.md`](../services/README.md)
> - **Key Entry Points:** [`dateFormatters.js`](dateFormatters.js) · [`imageFallbacks.js`](imageFallbacks.js) · [`knockout.js`](knockout.js) · [`matchModel.js`](matchModel.js) · [`router.js`](router.js) · [`teamProfileCache.js`](teamProfileCache.js)

## Business Rules & Invariants
- **URL Routing (`router.js`):** `parseUrlRoute`, `navigateTo`, and `updateUrlRoute` synchronize `?tab=...&matchId=...&playerId=...&team=...&p1=...&p2=...` with browser history (`popstate`) and legacy `#match-` hashes.
- **Model Prediction Eligibility (`matchModel.js`):** `hasModelPrediction` checks competition model support and match validity so cup/unsupported fixtures skip prediction fetches cleanly.
- **Versioned Cache (`teamProfileCache.js`):** Caches team profile slices (`getCachedTeamData`, `setCachedTeamData`, `calculateTeamExpiry`, `clearTeamCache`, `clearAllCaches`) and polls `/api/data-version` via `syncDataVersion` (`cache: 'no-store'`) to flush both localStorage and in-memory `apiCache` after rebuilds/refreshes.
- **Image Fallback Handling (`imageFallbacks.js`):** `handleImageFallback` and `handleTeamBadgeError` swap broken CDN/local image URLs to local fallback SVG assets cleanly without infinite `onerror` loops.
- **Change rule:** Keep utility functions pure and framework-agnostic; re-verify with `npm run lint && npm run build`.
