---
name: Modern Wealth & Financial Planning
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3e4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6e7977'
  outline-variant: '#bdc9c6'
  surface-tint: '#006a63'
  primary: '#005c55'
  on-primary: '#ffffff'
  primary-container: '#0f766e'
  on-primary-container: '#a3faef'
  inverse-primary: '#80d5cb'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#005e3f'
  on-tertiary: '#ffffff'
  tertiary-container: '#007952'
  on-tertiary-container: '#99ffcd'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#9cf2e8'
  primary-fixed-dim: '#80d5cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Manrope
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-numeric:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  label-currency-lg:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system delivers a calm, poised, and exceptionally clear interface for personal wealth management and long-term investment planning. It balances institutional reliability with the warmth and approachability of modern consumer technology. The aesthetic departs sharply from both archaic corporate banking interfaces and erratic, hyper-gamified crypto exchanges.

### Aesthetic Foundation
- **Style:** High-clarity Scandinavian-influenced fintech minimalism combined with structural data density.
- **Tone:** Methodical, transparent, encouraging, and financially literate.
- **Key Sensations:** Stability through generous whitespace, confidence via razor-sharp numerical hierarchy, and visual relief through soft ambient lighting and balanced slate surfaces.

## Colors

The palette is engineered around organic financial security, readability under bright natural light, and cognitive comfort during long analytical sessions.

### Core Swatches
- **Primary (`#0f766e` - Deep Pine Teal):** Anchors primary calls to action, active navigation states, selected tabs, and core brand identifiers. It carries institutional maturity without feeling heavy or conservative.
- **Secondary (`#0f172a` - Midnight Slate):** Applied to high-emphasis typographic layers, prominent monetary values, critical metrics, and structural iconography.
- **Tertiary (`#10b981` - Emerald Growth):** Expresses upward net-worth trajectory, compound yields, completed savings goals, and system confirmation states.
- **Neutral (`#64748b` - Slate Muted):** Used for supporting microcopy, secondary labels, disabled borders, and inactive track indicators.

### Functional & Surface Applications
- **Canvas Base:** Soft warm slate (`#f8fafc` grading into `#f1f5f9`) minimizes eye strain over long periods compared to harsh uncalibrated white.
- **Surface Elevation:** Crisp pure white (`#ffffff`) reserved for cards, floating drawers, context menus, and elevated metric hubs.
- **Borders & Rules:** Ultra-subtle slate border (`#e2e8f0`) ensures clear spatial separation without creating heavy geometric boxes.
- **Warning & Attention:** Warm amber (`#f59e0b`) identifies underfunded targets, approaching budget limits, or pending clearing states.
- **Deficit & Debt:** Gentle rose (`#f43f5e`) communicates portfolio over-allocation, recurring liability spikes, and market downswings without evoking panic.

## Typography

The typographic hierarchy implements three distinct roles:
1. **Manrope (Display & Structural Headings):** Built with open geometric proportions and refined legibility. It handles portfolio summaries, asset balance aggregates, and major section headings.
2. **Inter (Interface & Continuous Reading):** Supplies neutral, friction-free readability across tables, input forms, tooltips, and transaction descriptions.
3. **JetBrains Mono (Precision Financial Metrics):** Dedicated to ledger balances, transaction hashes, tabular rates, currency codes (KES, USD, EUR), and growth percentages. Tabular lining figures are mandatory to prevent layout jitter across active charts and tables.

Always isolate currency indicators (e.g., `KES`, `$`) with muted secondary weight, allowing the actual numeric amount to command immediate visual hierarchy.

## Layout & Spacing

This design system uses a 12-column responsive fluid grid anchored by strict 8pt spatial rhythmic intervals.

### Screen Adaptations
- **Desktop (1280px+):** 12-column configuration with `gutter: 1.5rem` and outer canvas margins of `2rem` (max content envelope capped at `1440px`). Side-by-side dashboard views place visualization matrices on the left 8 columns and ledger breakdowns on the right 4 columns.
- **Tablet (768px - 1024px):** 8-column layout. Multi-column financial tables collapse secondary columns into drill-down accordions; metrics panels flow in 2x2 grids.
- **Mobile (320px - 640px):** Single-column stack with `gutter-mobile: 1rem` and `margin-mobile: 1rem`. Sticky top-level asset summary bar anchors portfolio value during vertical scroll.

Spacing tokens must never be mixed with component border widths or drop-shadow offsets. Use `space-sm` for inline metric tags, `space-md` for internal card padding, and `space-xl` for block-level module separation.

## Elevation & Depth

Visual depth is achieved through quiet, layered surfaces and soft ambient shadows rather than harsh borders or dramatic drop shadows.

### Elevation Levels
- **Canvas Base (Level 0):** Background surface (`#f8fafc` or `#f1f5f9`). Entirely non-elevated.
- **Flat Containers (Level 1):** Pure white surface (`#ffffff`) surrounded by a 1px border (`#e2e8f0`). Box shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03)`. Used for content modules, asset category cards, and historical tables.
- **Interactive Surfaces (Level 2 - Hover / Focus):** Subtle elevation translation (`translateY(-1px)`). Box shadow: `0 4px 12px -2px rgba(15, 23, 42, 0.08), 0 2px 6px -2px rgba(15, 23, 42, 0.04)`. Applied to active investment cards, goal progress pods, and clickable ledger rows.
- **Overlays & Modals (Level 3):** Frosted ambient backdrop (`rgba(15, 23, 42, 0.4)` with `backdrop-filter: blur(4px)`). Card shadow: `0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 8px 10px -6px rgba(15, 23, 42, 0.06)`. Reserved for fund deposit slips, withdrawal dialogues, and rebalancing wizards.

## Shapes

The interface balances crisp geometric precision with soft, accessible curvature (Level 2 roundedness).

- **Standard Elements (`0.5rem` / 8px):** Form inputs, buttons, table cell badges, tooltips, and status chips.
- **Containers (`1rem` / 16px):** Standard dashboard cards, performance analytics modules, and bottom sheets.
- **Accent Modules (`1.5rem` / 24px):** High-level summary banners, financial wellness scorecards, and floating promotional modules.
- **Circular Elements (`9999px`):** Profile initials, contextual status indicators, tag pills, and radial progress tracks.

## Components

### Buttons
- **Primary:** Solid Deep Pine Teal (`#0f766e`) with white text. Height: 40px (desktop), 44px (touch target mobile). Transition: 150ms ease. Focus state displays a 2px offset ring in `#10b981`.
- **Secondary / Outline:** Background transparent, 1px border `#e2e8f0`, text `#0f172a`. Hover state switches surface to `#f8fafc`.
- **Tertiary / Ghost:** No border, text `#0f766e`. Hover background `#f0fdfa`.

### Metric Cards & Investment Blocks
- Rendered on pure `#ffffff` with an outer border in `#e2e8f0`.
- Includes a dedicated header row (metric title in `label-sm` uppercase slate, accompanied by an optional info-popover), followed by the numerical value in `label-currency-lg`, ending with a trend badge showing delta indicators (`+X.XX%` with emerald tint `#ecfdf5` and text `#059669`).

### Input Fields & Selects
- Height 40px, rounded-md (8px), 1px solid `#cbd5e1`, background `#ffffff`.
- Prefix and suffix containers (e.g., currency pickers: `KES`, `USD`) use subtle `#f1f5f9` background with divider lines, styled using `JetBrains Mono` for rapid recognition.
- Active focus state: border shifts to `#0f766e` with an ambient glow (`box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15)`).

### Progress Bars & Goal Meters
- Track background: `#e2e8f0` with height 6px or 8px, border-radius 9999px.
- Progress fill: `#0f766e` for on-track plans; `#10b981` upon reaching 100%; amber `#f59e0b` if deposits are past-due.

### Financial Donut & Portfolio Distribution Charts
- Thin stroke width (18px - 24px) to retain airiness.
- High-contrast segmented hues: Pine Teal (`#0f766e`), Emerald (`#10b981`), Amber (`#f59e0b`), Midnight Slate (`#334155`), and Rose (`#f43f5e`).
- Central empty space displays total aggregate portfolio balance (`Manrope` Bold, 20px).

### Data Lists & Ledger Tables
- Alternating subtle rows avoided in favor of crisp horizontal dividers (`1px solid #f1f5f9`).
- Hover row surface transitions to `#f8fafc`.
- Amounts aligned strictly flush-right utilizing `JetBrains Mono` tabular lining figures.