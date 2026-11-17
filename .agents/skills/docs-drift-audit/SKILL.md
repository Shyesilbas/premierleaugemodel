---
name: docs-drift-audit
description: Use when auditing or editing docs, READMEs, reports, skills or AGENTS.md: stale content, broken links, drifted symbol names, word budgets, generated blocks. Runs scripts/check_docs.py.
---

# Docs Drift Audit

Docs describe intent; code, production artifacts, and generated JSONs are the truth. A doc claim counts as correct only after you verify it in source code or generated evaluation outputs.

## 1. Run the Mechanical Checks
Run all three checks before concluding any documentation or API contract change:

```bash
python3 scripts/check_no_emoji.py
python3 scripts/check_docs.py
python3 scripts/check_api_endpoints.py
pytest tests/test_docs.py tests/test_cli_help.py -q
```

`scripts/check_docs.py` (exit 1 on any issue; `--no-class` skips the symbol scan) reports:

| Code | Meaning | Usual fix |
|---|---|---|
| `MAP` | a `.md` file under `docs/` is not linked from `docs/README.md` | add it to the right section in `docs/README.md`, or move/remove if obsolete |
| `LINK` | a relative markdown link points to a missing file | point to the moved file or remove the link |
| `SYMBOL` | a backticked CamelCase name matches no Python/JS/JSX symbol or allowlist term | rename to the real class/component/function, or rewrite without backticks |
| `SIZE` | `src/*/README.md` (>450 words), `frontend/src/*/README.md` (>450), `AGENTS.md` (>600) or `SKILL.md` (>700) exceeds budget | move narratives, token tables, or examples to `docs/` or `references/` |
| `STALE` | reference to retired root docs (`AI_CONTEXT.md`, `ARTIFACT_REGISTRY.md`, `PROJECT_STATUS.md`, `GOAL_MODELS_ANALYSIS.md`, `VERI_VE_GOSTERIM_KATALOGU.md`) or moved `docs/reports/` outputs | point to `docs/artifact_registry.md`, `docs/project_status.md`, `docs/data_and_ui_catalog.md`, or `reports/` |

- **Backtick Discipline for SYMBOL:** Reserve backticks strictly for real Python classes, JS components, source filenames, or identifiers. Never backtick informal conceptual CamelCase phrases.

## 2. Module Hub Template & One-Home-Per-Fact
Module `README.md` files (`<= 450` words) route agents to code; `docs/` deep dives explain cross-module flows:
1. `# <Name> Domain` (or `# <Name> Module`) + 1-2 sentence scope.
2. `> [!NOTE] **Related Documentation & Runbooks:**` block linking to `docs/*.md`, counterpart frontend/backend READMEs, and **Key Entry Points** (relative file links).
3. `## Business Rules & Invariants` (or `## Component Rules`) — terse bullets, one rule each, plus `**Change rule:**` bullets.
4. `## API` (for `src/api/README.md`) — one line per route group (`METHOD /path` — purpose).
- Never duplicate metric tables inside module hubs; keep metrics in `docs/reports/models/*.md` or `reports/`.

## 3. Script, Tool & Registry Synchronization
When adding, renaming, or deleting source files, tests, competitions, or models:
- Keep `docs/scripts_reference.md` and `src/ingest/__main__.py:TOOLS` synchronized (`tests/test_docs.py` verifies both).
- Keep `docs/data_sources.md` synchronized with `config/competitions.yaml`.
- Keep `docs/artifact_registry.md`, `docs/project_status.md` (including real pytest collected count `**Testler:** N/N geçiyor`), `docs/README.md`, and `reports/README.md` up to date.
