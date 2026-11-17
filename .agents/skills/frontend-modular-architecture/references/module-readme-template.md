# Frontend Module README Template

`frontend/src/<module>/README.md` routes agents to code; keep it under 450 words. Only module-specific facts that were verified in source code. Generic rules (four data states, tokens, radii, emoji ban) live in the skills and are never repeated here.

1. `# <Name> Module` + 1-2 sentence scope.
2. `> [!NOTE]` block linking backend counterparts (if any), `docs/*.md`, `frontend/README.md`, and `**Key Entry Points:**`.
3. `## Business Rules & Invariants` (or `## Component Rules`) — terse bullets covering actual exports, caches, capability flags, storage keys, or route/tab responsibilities.
4. `**Change rule:**` — exact verification command (`npm run lint:design && npm run lint && npm run build`).

Never include metric tables, speculative behavior, or unverified file paths.
