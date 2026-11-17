---
name: restrained-ui-design-standard
description: >-
  Use this skill before creating, modifying, styling, or reviewing any frontend UI
  component, view, modal, table, chart, or stylesheet. Enforces the Apple/Spotify-tier
  restrained design standard, semantic tokens, four-state data discipline, and mandatory
  pre-completion regex/lint checks.
---

# Restrained Frontend UI/UX Design Standard

Enforce every rule below when writing, styling, or editing components, screens, modals, tables, or stylesheets under `frontend/src/` and `frontend/index.html`. Visual hierarchy comes from typography scale, weight, spacing, alignment, and crisp 1px borders (`border-border`, `border-border-light`).

> **References (read on demand):**
> - [`references/tokens-and-components.md`](references/tokens-and-components.md) — Semantic CSS token mappings, typography/spacing scales, and shared primitive specs.
> - Canonical token definitions: `frontend/src/index.css` and `frontend/tailwind.config.js`.

## 1. Hard Prohibitions ("Never" List)
1. **No Emojis Anywhere:** Zero emojis in JSX, SVG data URIs (`frontend/index.html`), labels, buttons, badges, empty states, comments, or data files. Use `lucide-react` icons (`16px` or `20px`, stroke `1.5`, `currentColor`) or plain text.
2. **No Oversized Border Radius:** Strict ceiling: `rounded-sm` (6px tags/badges), `rounded` (8px buttons/inputs/cards/dropdowns), `rounded-md` (12px max for modals/panels), `rounded-full` (avatars, logos, dots). **Forbidden:** `rounded-lg`, `rounded-xl`, `rounded-2xl`, `rounded-3xl`, `rounded-[...]`, or pill cards.
3. **No Arbitrary Tailwind Brackets or Raw Hex Codes in Markup:** Never write `text-[13px]`, `p-[18px]`, `rounded-[...]`, or inline `#...` hex colors in component markup; use semantic tokens from `tailwind.config.js` and CSS variables in `index.css`.
4. **No Heavy Font Weights:** Use Plus Jakarta Sans / Inter (`font-sans`). Allow only `font-normal` (400), `font-medium` (500), and `font-semibold` (600). **Forbidden:** `font-extrabold`, `font-black`, and decorative all-caps tracking.
5. **No Gradients, Blur, Neon Glows, or Resting Card Shadows:** **Forbidden:** `bg-gradient-*`, `backdrop-blur*`, glowing rings (`glow-*`), decorative body blobs, bounce animations, or `hover:scale-*`. Resting cards use flat `bg-background-primary` + `border-border`; shadows (`shadow-sm`, `shadow-md`) are reserved strictly for floating overlays and modals.
6. **Tabular Numerals & Sentence Case:** Apply `tabular-nums` to every score, probability, odds value, count, rating, percentage, date, or metric cell. Use sentence case for headings and buttons.

## 2. Core Rules & Four-State Data Discipline
- **Shared Primitives First:** Consume `frontend/src/components/common/` (`Skeleton`, `EmptyState`, `InlineError`, `TabBar`, `CompetitionSelector`) consistently across tabs.
- **Purposeful Contextual Color:** Competition accents (`accent`, `accent-soft`) and team/pitch visuals stay clean and accessible (`>= 4.5:1` contrast) across light and dark modes.
- **Mandatory Four Data States:** Every data-driven view must handle:
  1. **Loading:** Layout-matching `Skeleton` blocks (`animate-pulse bg-background-tertiary rounded`) preventing CLS.
  2. **Empty:** Clean `EmptyState` with `lucide-react` icon, concise sentence, and optional single retry/reset CTA.
  3. **Error:** `InlineError` (`role="alert"`) with concise message and `onRetry` action.
  4. **Disabled / Pending:** Preserve button/control width, reduce contrast, and reflect progress in the label.

## 3. Pre-Completion Verification Checklist
Run from `frontend/` before concluding any UI change:

```bash
npm run lint:design
npm run lint
npm run build
```

Also run `python3 scripts/check_no_emoji.py` and `python3 scripts/check_api_endpoints.py` from repository root.
