# Design

This project uses the extracted [Propadmin design system](propadmin-design-system/README.md).
It is a reusable source kit, with components and visual references, rather than
a standalone application.

## Source of truth

Read the [current style guide](propadmin-design-system/docs/STYLE-GUIDE.md) before
making UI changes. Use the [component catalogue](propadmin-design-system/docs/COMPONENT-SYSTEM.md)
to choose existing primitives and patterns, and the [integration guide](propadmin-design-system/docs/INTEGRATION.md)
when incorporating them into the application.

The [full current specification](propadmin-design-system/docs/reference/DESIGN-SYSTEM.md)
provides further detail. `docs/reference/DESIGN-GUIDE.md` is historical; the
current style guide and specification take precedence over it. Component props
and defaults are authoritative for their implementation.

## Core rules

- Use one canvas, one ink, and one divider colour. Build hierarchy through
  typography, whitespace, and position.
- Resolve UI colours through the semantic tokens in
  [globals.css](propadmin-design-system/styles/globals.css). Rebrand through the
  palette variables; preserve light and dark mode semantics.
- Keep controls and floating surfaces square, cards flat, and fields and option
  lists marked by the shared thick left rule. Avoid decorative shadows, grey
  control fills, and added outlines.
- Use one ink-filled primary action per step. Secondary actions use text and
  the drawn hover line. Use verbs for buttons and a confirmation dialog for
  destructive actions.
- Keep short status text in ink with a tone-coloured underline using `StatusText`
  or `Badge`. Never communicate status through colour alone.
- Use Geist for text and Geist Mono for code and identifiers when available.
  Keep text at least 12px and use the 4px spacing scale.
- Keep copy concise. Empty states have one line and at most one action. Remove
  redundant headings, subtitles, repeated counts, and zero-value facts.
- Use the supplied table and list patterns: edge-to-edge dividers, no outer box
  or header fill, tabular numbers, `RowMenu` for row actions, and `SelectionBar`
  for bulk actions.
- Reuse existing components and shared interaction styles instead of duplicating
  status text, left rules, hover lines, divided grids, or progress shimmer.
- Preserve accessible labels, keyboard access, visible focus, and reduced-motion
  support. Check mobile layouts, light/dark themes, hover/focus, and clipping.

## Reference assets

- [Interactive visual reference](propadmin-design-system/preview/index.html)
- [Light preview](propadmin-design-system/preview/light.png),
  [dark preview](propadmin-design-system/preview/dark.png), and
  [mobile preview](propadmin-design-system/preview/mobile.png)
- [Machine-readable tokens](propadmin-design-system/tokens/design-tokens.json)
- [Export validation](propadmin-design-system/VALIDATION.md)
