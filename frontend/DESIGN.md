# Design Standard

Read this before any UI change. Act as a senior frontend engineer at a premium consumer-product company (Apple / Spotify tier) in the era before generative AI: every screen is deliberate, quiet, consistent and fast. UI/UX quality is the first priority, ahead of speed of delivery.

**Principle: restraint & purposeful color.** Hierarchy primarily comes from type size, weight, spacing, alignment and hairline borders. Color is used deliberately where appropriate: rigid monochrome restrictions are replaced by thoughtful color choices suitable for the context (team identities, metrics, predictions), provided they remain restrained, balanced, and never exaggerated, loud, or tacky (abartı ve cıvık olmayan bir denge).

## Never (hard rules)
- **No emojis**, anywhere: UI text, buttons, toasts, alerts, empty states, placeholders, seed copy. Use `lucide-react` icons or nothing.
- **No tacky / loud decoration:** no arbitrary neon bubbles, floating blobs, glowing rings, or chaotic rainbow chips. Subtle, purposeful contextual badges, tags, or pills are allowed.
- **No big rounded shapes:** see the radius table. No `rounded-lg/xl/2xl/3xl`, no `rounded-[..]`, no pill-shaped buttons or cards.
- **No garish or screaming card backgrounds:** resting cards should remain clean and readable. Subtle contextual borders or gentle tinting for states/metrics/teams are allowed, but avoid loud, high-saturation fills.
- No heavy gradients, glassmorphism (`backdrop-blur`, translucent white), decorative blobs, glow, or heavy shadows.
- **Color usage:** Rigid single-accent / monochrome rules are lifted. Colors deemed appropriate by the model/context (e.g. contextual accents, team colors, data points, status indicators, subtle category tints) can be used freely, provided they remain restrained, cohesive, and mature—never noisy or flashy.
- No arbitrary values (`text-[13px]`, `p-[18px]`, `rounded-[2rem]`). Prefer Tailwind scale and cohesive design tokens.
- No `font-black` / `font-extrabold`, no all-caps micro labels with wide tracking used as decoration.
- No bounce, scale-up hover lifts, or looping decorative animation.

## Tokens (source: `tailwind.config.js`)
- **Surfaces:** page `bg-background-secondary`, content surfaces `bg-background-primary`, subtle fills `bg-background-tertiary`. Separate with 1px borders (`border-border` for edges, `border-border-light` for inner dividers), not shadows.
- **Text:** `text-text-primary` for content, `text-text-secondary` for supporting text, `text-text-tertiary` / `text-text-muted` for meta (never for essential info; check contrast).
- **Accent & Contextual Colors:** `primary` serves as the anchor primary action, but appropriate complementary accents (e.g. contextual indicators, metrics, team palettes, charts, tags) can be used where they enhance clarity and aesthetics without clutter.
- **Status:** `status-success|error|warning|info`. Contextual status tags, dots, or subtle badges are supported when they communicate meaningful state.
- **Metrics / Odds:** highlight tokens exist for emphasis; use purposefully where relevant.

### Radius (project scale is larger than Tailwind default)
In this repo `rounded-sm`=6px, `rounded`=8px, `rounded-md`=12px, `rounded-lg`=16px, `rounded-xl`=24px, `rounded-2xl`=32px.

| Use | Class |
|---|---|
| Tags, checkboxes, small badges | `rounded-sm` |
| Buttons, inputs, selects, cards, dropdowns, toasts | `rounded` |
| Modals, drawers, large panels (the ceiling) | `rounded-md` |
| Avatars, status dots, switches only | `rounded-full` |
| Everything else | not allowed |

### Shadows
Default is none. Allowed: `shadow-sm` on floating layers (dropdowns, popovers), `shadow-md` on modals. Never on resting cards.

### Typography
Font: Plus Jakarta Sans (already configured). Weights 400 / 500 / 600 only.
- At most 3 hierarchy levels per screen. Page title `text-2xl font-semibold`, section title `text-lg font-semibold`, body `text-sm`, meta `text-sm text-text-secondary`.
- Smallest text is 12px; avoid `text-caption` and anything below 12px for real content.
- Numbers, prices, counts, dates: `tabular-nums`. Sentence case, no exclamation marks, specific verbs ("Save changes", not "Submit").

### Spacing and layout
- 4px grid. Card padding `p-4` or `p-5`; stack gaps `gap-4` / `gap-6`; section gaps `gap-8`. Don't mix paddings between sibling cards.
- Pages use `PageContainer`. Limit reading width; align to a visible grid; generous whitespace beats borders and boxes.
- Mobile first. Verify 360, 768 and 1280 widths. Touch targets at least 44px on mobile. Sticky bars have solid backgrounds.

## Components
- **Buttons:** primary / secondary / ghost only. One primary per view. 36-40px high, `rounded`, label text only or icon + label. Destructive actions are text-colored `status-error` or a confirm step, not big red buttons.
- **Inputs:** visible label above, helper/error text below, 40px high, `rounded`, 1px `border-border`, focus ring 2px `border-border-focus`. Validate on blur/submit.
- **Cards:** flat, white, 1px border, `rounded`, no resting shadow. Hover changes border to `card-border-hover` only; no lift, no scale.
- **Lists / tables:** dense rows (`py-2` to `py-3`), dividers `border-border-light`, right-align numbers, paginate.
- **Status:** a dot, subtle tag or text badge, not an overly loud neon bubble.
- **Icons:** `lucide-react`, 16 or 20px, stroke 1.5, `currentColor`. Avoid arbitrary neon bubbles or loud circular frames behind icons.
- **Modals / drawers:** `bg-black/40` backdrop without blur, `rounded-md`, focus trapped, Esc closes, primary action on the right. Drawer for long forms. No nested modals.
- **Images:** fixed aspect ratio placeholders so nothing shifts; `rounded` at most.

## States (every data view needs all four)
- **Loading:** `Skeleton` shaped like the final layout; no layout shift; no spinners for page content.
- **Empty:** `EmptyState` with one sentence and one CTA. Plain, no illustration blobs, no emoji.
- **Error:** inline message with a retry action; `ErrorBoundary` only for fatal render errors.
- **Disabled / pending:** keep layout, reduce contrast, show progress on the button label.

## Motion
150-200ms, `ease-out`, opacity and small translate only. Respect `prefers-reduced-motion` via `motion-reduce:`. Motion explains a change; it is never decoration. Animation must not delay interaction.

## Accessibility
Contrast at least 4.5:1 for text, visible `focus-visible` states, labels on every control, full keyboard operation, `aria-*` on custom widgets, focus management in dialogs.

## Before you finish a UI change
Run from `frontend/` against the files you touched and fix every hit:
```bash
grep -nE "rounded-(lg|xl|2xl|3xl)|rounded-\[|bg-gradient|backdrop-blur|font-(black|extrabold)|text-\[[0-9]|#[0-9a-fA-F]{3,6}\b" <files>
grep -nP "[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]" <files>   # emojis
npm run lint
```
Existing code still contains violations. Fix them in files you are editing; don't mass-rewrite unrelated files unless asked. Note for the maintainer: because the theme radius scale is oversized, remapping it in `theme.js` to a smaller scale is the cleanest long-term fix.
