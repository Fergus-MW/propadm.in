# Reusable style guide

Use this guide and the supplied components when bringing the system into another project. The current system takes precedence over the historical guide in `reference/`.

## Visual foundations

One canvas, one ink, one divider colour. Establish hierarchy with size, weight, whitespace and position. Every UI colour resolves through the semantic tokens in `styles/globals.css`. Change the eight `--palette-*` variables there to rebrand; the five hue roles are brand, info, success, warning and danger. Canvas, ink and line change under `.dark`.

Controls and floating surfaces are square. Cards are flat. Fields and option lists have a thick ink rule on the left. Avoid grey fills, shadows and added outlines on controls. Skeletons and progress tracks can use the muted fill.

One ink-filled primary action per step. Secondary actions are text with the drawn hover line. Destructive actions use the same ink primary and explain the consequence in a confirmation dialog. Buttons use verbs.

Short statuses stay in ink; only their underline carries the tone. Use `StatusText` or `Badge`. Sentence notices can use a subtle role tint through `Notice`. Never communicate status through colour alone.

## Type and spacing

The original product uses Geist for text and Geist Mono for code and identifiers. Supply `--font-geist-sans` and `--font-geist-mono` in your host application. A system-font fallback is demonstrated in the preview; font binaries are not included.

| Role | Reference size / line height | Weight |
| --- | --- | --- |
| Page title, when a visible title is needed | 30 / 36 px | 600 |
| Hero number | 48–64 px | 600 |
| Section heading | 18 / 24 px | 600 |
| Subheading | 15 / 22 px | 600 |
| Body | 14 / 20 px | 400 |
| Caption | 12 / 16 or 13 / 19 px | 400–500 |
| Table number | 13–14 px | 500, tabular numerals |

This reference scale is retained from the earlier guide. Component defaults are authoritative for actual controls and tables. Use at least 12px text; no faded caption ink. Use the 4px spacing scale: 4, 8, 12, 16, 20, 24, 32, 40px. Allow 20–24px between sections. Adapt gutters to the host layout, typically 16px on mobile and 24–40px on desktop.

## Layout and interaction

Say less: remove redundant headings, explanatory subtitles, repeated counts and zero-value facts. Empty states are one line and at most one action. Keep useful accessible labels when a visual heading is omitted.

Use `Table density="standard"` for record lists and `density="dense"` for numerical grids. Dividers run edge to edge; tables have no outer box or header fill. Long tables use `stickyHeader`. Align figures with tabular numerals. Put filters and view controls in one row, row actions in `RowMenu`, and bulk actions in `SelectionBar`.

The drawn hover/focus line is `draw-underline`; it animates left to right over 0.3 seconds. Current or selected controls keep the line drawn. Progress fills are ink with square ends; `active` work shimmers continuously. The supplied CSS respects reduced motion for these effects.

Use angular Lucide glyphs, square stroke caps and sharp joins. Prefer full-strength icons and explicit `aria-label` on icon-only actions. A round glyph is acceptable when it is the clearest meaning.

Filters, open records and dialogs should live in the URL when they need to be shared. Reserve space for late-loading content. Preserve keyboard access, focus visibility and labels; check light/dark, hover/focus, mobile layout and clipping in a browser.

## Choose an implementation

Primitives are in `components/ui/`; interface patterns are in `components/library/`. Read `COMPONENT-SYSTEM.md` and each component's props. Reuse their defaults. A second hand-rolled implementation of status text, the left rule, hover line, divided grid or progress shimmer creates drift.

`reference/DESIGN-SYSTEM.md` is the full original specification. `reference/DESIGN-GUIDE.md` is historical: its coloured primaries, rounded controls, two inks, pills and hover fills have been superseded and should not be carried into a new project.
