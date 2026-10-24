---
name: restrained-ui-design-standard
description: >-
  Use this skill before creating, modifying, styling, or reviewing any frontend UI
  component, view, modal, table, chart, or stylesheet. Enforces the Apple/Spotify-tier
  restrained design standard, semantic tokens, four-state data discipline, and mandatory
  pre-completion regex/lint checks.
---

# Restrained Frontend UI/UX Design Standard

Enforce every rule below when writing, styling, or editing frontend components, screens, modals, tables, or stylesheets. UI/UX quality, consistency, accessibility, data clarity, and performance take priority over speed of delivery.

## 1. Core Design Philosophy

- **Quiet, Deliberate & Fast**: Build interfaces at a premium consumer-product standard (Apple / Spotify tier). Hierarchy comes from typography scale, weight, spacing, alignment, and 1px hairline borders—never from stacked shadows, loud backgrounds, or arbitrary decoration.
- **Purposeful Contextual Color**: Use semantic tokens for surfaces, text, and borders. Contextual colors (team identities, win probabilities, status indicators, chart series) are encouraged when restrained, balanced, and meaningful—never neon, loud, or tacky.

## 2. Hard Visual Prohibitions (Zero Exceptions)

1. **No Emojis Anywhere**: Zero emojis in JSX, UI strings, buttons, badges, empty states, toasts, comments, or test fixtures. Use `lucide-react` icons (`16px` or `20px`, stroke `1.5`, `currentColor`) or plain text.
2. **No Oversized Border Radius**:
   - Tags, badges, checkboxes, small indicators: `rounded-sm` (6px)
   - Buttons, inputs, selects, cards, dropdowns, toasts: `rounded` (8px)
   - Modals, drawers, large overlay panels (the ceiling): `rounded-md` (12px)
   - Avatars, logos, status dots, switches: `rounded-full`
   - **Forbidden**: `rounded-lg`, `rounded-xl`, `rounded-2xl`, `rounded-3xl`, `rounded-[...]`, or pill-shaped buttons/cards.
3. **No Arbitrary Tailwind Brackets or Hex Codes**: Never write `text-[13px]`, `p-[18px]`, `w-[342px]`, or hardcoded hex values (`#1a2b3c`) in component markup when a scale class or semantic token exists.
4. **No Heavy Font Weights**: Font is Plus Jakarta Sans (`font-sans`). Use only `font-normal` (400), `font-medium` (500), and `font-semibold` (600). **Forbidden**: `font-extrabold`, `font-black`, and decorative all-caps tracking.
5. **No Gradients, Blur, or Resting Card Shadows**:
   - **Forbidden**: `bg-gradient-*`, `backdrop-blur*`, glowing rings, decorative blobs, bounce animations, or scale-up hover lifts (`hover:scale-*`).
   - Resting cards use flat surfaces (`bg-background-primary`) with a 1px border (`border-border`). Shadows (`shadow-sm`, `shadow-md`) are reserved **exclusively** for floating overlays (dropdowns, popovers, modals).
6. **Tabular Numerals & Casing**:
   - Every score, probability, odds value, count, percentage, date, or metric cell must include `tabular-nums`.
   - Use sentence case for headings and buttons ("Save changes", not "SAVE CHANGES" or "Submit!").

## 3. Semantic Tokens, Typography & Layout Grid

| Role | Semantic Token | Intended Usage |
|---|---|---|
| Page Background | `bg-background-secondary` (`#f8fafc`) | Canvas background for application pages |
| Content Surfaces | `bg-background-primary` (`#ffffff`) | Cards, tables, modals, input backgrounds |
| Subtle Fills | `bg-background-tertiary` (`#f1f5f9`) | Table headers, secondary buttons, hover/active fills |
| Primary Text | `text-text-primary` (`#0f172a`) | Titles, headings, values, primary labels |
| Supporting Text | `text-text-secondary` (`#475569`) | Subtitles, descriptions, table cell text |
| Metadata & Muted | `text-text-muted` (`#94a3b8`) | Timestamps, secondary metadata (verify 4.5:1 contrast) |
| Outer Borders | `border-border` (`#e2e8f0`) | Card perimeter, input borders, button borders |
| Inner Dividers | `border-border-light` (`#f1f5f9`) | Table row dividers, subtle internal section dividers |
| Focus Ring | `border-border-focus` (`#0f172a`) | Accessible keyboard focus state (`focus-visible`) |
| Primary Action | `bg-primary` / `hover:bg-primary-hover` | Dominant CTAs and active navigation states |
| Status States | `status-success`, `status-error`, `status-warning`, `status-info` | Positive/negative metrics, cautions, neutral badges |

- **Typography Hierarchy**: At most 3 levels per screen. Page title `text-2xl font-semibold`, section title `text-lg font-semibold`, card title `text-sm font-semibold`, body `text-sm`, supporting meta `text-xs text-text-secondary`. Minimum text size is `12px` (`text-xs`).
- **Spacing & Responsiveness**: 4px grid (`p-4` or `p-5` on cards—never mix padding across sibling cards; `gap-3`/`gap-4` for elements; `gap-6`/`gap-8` for sections). Mobile-first (`360px`, `768px`, `1280px`), min `44px` touch targets on mobile.
- **Motion**: `150–200ms`, `ease-out`, opacity and small translate (`1–2px`) only. Respect `prefers-reduced-motion` (`motion-reduce:`).

## 4. Shared Primitives & Component Rules (`src/components/common/`)

1. **Button**: Variants `primary`, `secondary`, `ghost`, `danger`. One primary per view. `36–40px` desktop height, `rounded`, preserves width during loading.
2. **Input & Select**: Visible `<label>` above (`htmlFor`), `40px` height, `rounded`, `1px border-border`, focus ring `border-border-focus`, error text below (`role="alert"`).
3. **Card**: Flat `bg-background-primary`, `border border-border`, `rounded`, hover changes border to `border-card-border-hover` only.
4. **Lists & Tables**: Dense rows (`py-2` to `py-3`), dividers `border-border-light`, right-align numbers with `tabular-nums`.
5. **Modal & Drawer**: Solid `bg-black/40` backdrop (no blur), `rounded-md`, focus trapped, `Escape` closes, primary action on the right. No nested modals.

## 5. Mandatory Four-State Data Discipline

Every data-driven component or screen must implement all four states:
1. **Loading**: Layout-matching `Skeleton` blocks (`animate-pulse bg-background-tertiary rounded`) that prevent layout shift (CLS). No page-level spinners.
2. **Empty**: Clean `EmptyState` with a `lucide-react` icon (`24px` or `32px`), one concise explanation sentence, and at most one primary CTA.
3. **Error**: `InlineError` (`role="alert"`) with a clear explanation and a retry action callback.
4. **Disabled / Pending**: Preserve button/card dimensions, reduce contrast, and reflect progress in the label.

## 6. Pre-Completion Verification Checklist

Before concluding any frontend task, run these checks against the modified files from `frontend/`:

```bash
# 1. Scan touched files for forbidden Tailwind classes and hex codes
grep -nE "rounded-(lg|xl|2xl|3xl)|rounded-\[|bg-gradient|backdrop-blur|font-(black|extrabold)|text-\[[0-9]|#[0-9a-fA-F]{3,6}\b" <touched_files>

# 2. Scan touched files for emojis
python3 -c '
import re, sys
pat = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
for path in sys.argv[1:]:
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        if pat.search(line):
            print(f"{path}:{i}: {line.strip()}")
' <touched_files>

# 3. Run design lint / ESLint and production build
npm run lint:design 2>/dev/null || npm run lint
npm run build
```

Fix every violation in the files you touched before reporting completion.
