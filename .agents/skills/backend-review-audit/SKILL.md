---
name: backend-review-audit
description: Use for Python/FastAPI/SQLite backend audits and reviews, tracing execution paths, checking security/data-consistency/performance findings (GV/VT/PF/DB/KK), and writing regression tests.
---

# Continuous Backend Review & Audit Standard

## 1. Finding Taxonomy & Priority Matrix
Classify every backend finding with canonical prefixes and sequential IDs:

| Prefix | Category | Target Areas in `src/` |
|---|---|---|
| `GV` | Security | `require_admin_token`, `cors_origins`, path traversal, untrusted query params, secret leakage, exception message leaks |
| `VT` | Data Consistency | Atomic file writes, SQLite transactions, pre-game `shift(1)` boundaries, train-serve parity, cache invalidation (`data_version`) |
| `PF` | Performance | Blocking sync subprocesses, N+1 SQLite queries inside loops, unindexed joins, repeated artifact reloads |
| `DB` | Database | `competition_id` isolation, FK/index coverage, safe migrations, UTC timestamp handling |
| `KK` | Code Quality | Deprecated stdlib calls (`datetime.utcnow`), HTTP status codes (`400`/`404`/`503` vs `500`), bare `except`, dead modules, ruff lint errors |

- **Priority Matrix:**
  - **P0:** Data corruption, cross-competition overwrite, authentication bypass, or pre-game target leakage.
  - **P1:** Runtime 500 crash on valid requests, unhandled upstream failure, or train-serve feature skew.
  - **P2:** Performance degradation, stale cache serving, or missing validation returning 500 instead of 400/404.
  - **P3:** Deprecated APIs, unused helpers, ruff warnings, or minor refactors.

## 2. Review Methodology
1. **Follow the Execution Path:** Trace `FastAPI Route (src/api/routes/*.py) -> Service/Prediction (src/api/, src/analytics/) -> State/Feature Builder (src/api/state.py, src/features/) -> DB/Artifacts (src/db/, models/)`.
2. **State Evidence Clearly:** Distinguish **Fact** (verified in code/test), **Hypothesis** (needs runtime reproduction), and **Not a Bug**.
3. **Every Reported Finding Includes:** file + line range, concrete trigger scenario, root cause, and minimal fix direction.

## 3. Fix & Verification Rules
1. **Test-Driven Fixes:** Every bug fix ships with a unit test (isolated synthetic fixture or FastAPI `TestClient`) that fails without the fix and passes with it.
2. **Parity Check:** Whenever an endpoint path or response shape changes, inspect consuming modules in `frontend/src/services/*.js` and run `python3 scripts/check_api_endpoints.py`.
3. **Run Gates:** `ruff check .`, `pytest -q`, and `./scripts/verify.sh`.
