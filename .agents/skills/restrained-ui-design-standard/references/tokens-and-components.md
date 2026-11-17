# Restrained UI Design Tokens & Component Specs

Detailed token mappings and component anatomy referenced by `SKILL.md`. Canonical CSS variables and Tailwind mappings live in `frontend/src/index.css` and `frontend/tailwind.config.js`.

## 1. Surfaces, Borders & Text Hierarchy
- **Surfaces:**
  - Primary content surface (cards, tables, modals): `bg-background-primary`
  - Page canvas background: `bg-background-secondary`
  - Subtle fill / table headers / secondary hovers: `bg-background-tertiary`
  - Separate cards and section boundaries with 1px `border-border`; inner dividers with `border-border-light`.
- **Text Hierarchy:**
  - Primary titles, headings, key numbers: `text-text-primary`
  - Supporting copy, descriptions, table cells: `text-text-secondary`
  - Tertiary labels / metadata: `text-text-tertiary` / `text-text-muted` (verify >= 4.5:1 contrast).
- **Competition Accent & Status Anchors:**
  - Primary action / active tab underline or pill: `bg-primary` / `text-text-primary` or competition `accent` CSS variable (`rgb(var(--accent))`).
  - Status states: `status-success`, `status-error`, `status-warning`, `status-info`.

## 2. Typography, Elevation & Layout Scales
- **Fonts:** Plus Jakarta Sans (`font-sans`) + JetBrains Mono (`font-mono`). Weights: `font-normal` (400), `font-medium` (500), `font-semibold` (600) only.
- **Scale:** Page title `text-2xl font-semibold`, Section title `text-lg font-semibold`, Card title `text-sm font-semibold`, Body `text-sm`, Meta `text-xs text-text-secondary`, minimum `text-xs`.
- **Numerals:** Apply `tabular-nums` to all scores, xG values, probabilities, odds, percentages, ratings, and metric cells.
- **Shadows & Radii:** Resting cards use flat surfaces (`border border-border rounded`) with no shadow. `shadow-sm` / `shadow-md` are reserved for floating overlays and dialogs (`rounded-md`). Radii ceiling: `rounded-sm` (badges/chips), `rounded` (cards/buttons/inputs), `rounded-md` (modals/panels), `rounded-full` (badges/crests/status dots).

## 3. Shared Primitives (`frontend/src/components/common/`)
- `CompetitionSelector.jsx`: Tournament selector respecting `Competitions` registry and capability flags.
- `Skeleton.jsx`: Layout-matching loading placeholders (`animate-pulse bg-background-tertiary rounded`).
- `EmptyState.jsx`: Clean empty feedback with `lucide-react` icon and concise guidance.
- `InlineError.jsx`: Accessible `role="alert"` error container with optional retry callback.
- `TabBar.jsx`: Flat bordered tab switcher following typography and border rules.
