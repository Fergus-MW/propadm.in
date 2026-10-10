# Propadmin design system

The colour system, interface principles and component library the whole app
follows. Read this before building or changing any screen.
[`DESIGN-GUIDE.md`](DESIGN-GUIDE.md) is the earlier design guide; where the
two differ, this file wins.

## Colour

The platform has one global colour system. Its single source of truth is the
palette block at the top of `frontend/app/globals.css`: the `--palette-*` custom
properties on `:root`, with the neutrals redefined under `.dark`. That block is
the only place a colour value is chosen. This document deliberately does not copy
the values. Read them in `globals.css`, and never change them to match a
document.

The palette has eight knobs:

| Knob | Job |
|---|---|
| `--palette-brand` | primary accent, chart series 1, graph nodes |
| `--palette-info` | informational state, series 2 |
| `--palette-success` | healthy / complete, series 3 |
| `--palette-warning` | degraded / needs attention, series 4 |
| `--palette-danger` | failed / destructive, series 5 |
| `--palette-canvas` | every background |
| `--palette-ink` | every word of text |
| `--palette-line` | every border and input edge |

Everything else derives from these: the semantic tokens (`--brand`, `--success`,
`--muted`, `--foreground`, …) and their Tailwind utilities (`bg-brand`,
`text-success`, `bg-muted`, …). **Never put a colour on an element:** no hex,
`rgb()` or palette class on a `div`, a chart or a canvas. Always use a semantic
token, which resolves to the palette.

Changing the palette in `globals.css` re-themes the entire product — badges, status text, alerts,
charts, the knowledge-graph canvas, the lead-scoring visualisations, every
surface, every border and every word of text. Nothing else should need to
change. **If a re-theme would require editing any file other than `globals.css`,
that is the bug to fix.**

Tenant Settings can override the five hues for one tenant. The app writes those
values onto the same `--palette-*` variables. A blank field keeps the default
from `globals.css`. That override is not a second palette, and it must not touch the
neutrals — `TenantBrandProvider` iterates `PALETTE_KEYS`, which is the five hues
only.

### One ink, one canvas, one line

The neutrals are knobs like everything else, and there is exactly **one text
colour**. `--foreground` and `--muted-foreground` resolve to the same
`--palette-ink`: text hierarchy comes from size and weight, never from a second
grey. Every other neutral in `globals.css` is a `color-mix` of ink into canvas —
`--muted` (the surface tint), `--accent` (one step above it, for hover and
active), `--ring`, `--primary`, `--card` in dark mode. There is no third surface
grey to reach for, because none is declared: a hover steps `bg-muted` →
`bg-accent`, it never fades the fill with `/80`.

Three derived neutrals exist for jobs a full-strength ink cannot do. They are
declared once in `globals.css` and are not knobs:

- `--ink-soft` — placeholder text (`text-placeholder`) and the "no data" colour
  in charts (`--viz-muted`). Never for prose.
- `--scrim` — the modal/sheet overlay (`bg-scrim`). Dark in both schemes, since
  a scrim that inverted with the theme would stop dimming anything.

If you want a second text grey back, change `--muted-foreground` in
`globals.css` and nowhere else. Do not reintroduce it per component.

For a whole-sentence notice on a `-subtle` tint, the readable text colours are
`--success-text`, `--info-text`, `--warning-text` and `--destructive-text`
(`text-success-text` and so on); the `Notice` component uses them.

### Fewer borders

Surfaces are separated by whitespace and, where that is not enough, by the
single `--muted` tint. A border is a last resort, not a default:

- **Tables have no outer box and no header fill.** `Table` renders straight onto
  the canvas; the only rules are the one under the header and the ones between
  rows. Do not re-add `rounded-lg border` around a table or `bg-muted` behind a
  `TableHeader`.
- **Never both a tint and an outline** on the same element. A filter bar on
  `bg-muted`, a status banner on `bg-warning-subtle`, an empty state — each is
  already delimited; an outline on top of it is the second border the design
  does not want.
- **No alpha on a neutral.** `bg-muted/30`, `bg-muted/50`, `border-border/60`
  and friends are how a palette of three greys became a palette of twelve. Use
  the bare token.

### Use the semantic tokens, never a raw colour

Each of the five roles exposes two tokens, both usable as Tailwind utilities:

| Token | Utility | Use for |
|---|---|---|
| `--brand` / `--brand-subtle` | `text-brand`, `bg-brand`, `bg-brand-subtle`, `border-brand` | product accent, personal-scope tint |
| `--info` / `--info-subtle` | `text-info`, `bg-info-subtle`, … | in-progress, informational |
| `--success` / `--success-subtle` | `text-success`, `bg-success-subtle`, … | complete, healthy |
| `--warning` / `--warning-subtle` | `text-warning`, `bg-warning-subtle`, … | degraded, needs attention |
| `--destructive` / `--destructive-subtle` | `text-destructive`, `bg-destructive-subtle`, … | failed, destructive actions |

`--chart-1..5` and `--viz-1..4` are aliases of the same five, in that order.

Rules:

- **`-subtle` is the tinted surface, the bare token is the readable colour.**
  A tint is for a whole-sentence notice, never a short status label; a status is
  `StatusText` (see Interface principles).
- **Content sitting on a solid `bg-<role>` fill is white** (`text-white`,
  `text-white/80`, `bg-white/20`) — not the role token, which would be invisible
  against its own background. This is the one place `white` is still correct,
  and only on a coloured fill.
- **An inverted neutral panel is `bg-primary text-primary-foreground`**, not a
  hand-picked dark grey. It flips correctly with the theme; `bg-slate-900
  text-white` does not.
- **Never write `dark:` variants for colour.** The tokens are already
  mode-aware: `-subtle` mixes against `--background`, the solid tokens lift
  toward `--palette-ink` under `.dark`, and the neutrals swap knobs. A `dark:`
  colour class is a sign someone bypassed the system.
- **Show a status with `StatusText`** (or a `Badge`, which renders the same way):
  the tone is an underline, the text stays ink. Never hand-roll a coloured chip.

### Banned in application code

- Hex, `rgb()`, `hsl()` or `oklch()` colour literals in `.ts`/`.tsx`.
- Tailwind palette classes for **any** hue, including the greys:
  `bg-amber-50`, `text-blue-600`, `border-emerald-300`, and every
  `{slate,gray,zinc,neutral,stone,red,orange,amber,yellow,lime,green,emerald,teal,cyan,sky,blue,indigo,violet,purple,fuchsia,pink,rose}-<shade>`.
  The tinted greys (`slate-*`, `zinc-*`, `stone-*`) are colours, and `gray-*` /
  `neutral-*` are a second neutral ramp competing with the knobs.
- `bg-black` / `text-black` / `bg-white` on a neutral surface. Use `bg-scrim`
  for an overlay, `bg-background`/`bg-card`/`bg-popover` for a surface, and
  `text-foreground` for text. `text-white` survives only on a solid `bg-<role>`
  fill.
- Any alpha modifier on a neutral token (`bg-muted/40`, `border-border/60`,
  `text-muted-foreground/70`).
- A second definition of a brand colour anywhere outside `globals.css`.

Run `npm run lint:colors` in `frontend/` before opening a PR. It must pass;
it runs `frontend/scripts/lint-colors.sh`.

### The two documented exceptions

Everything else is a violation. There is no third case, and no file in
`frontend/` is exempt "because it is internal".

1. **`lib/graph/entityTypeColors.ts`** — the graph canvas paints through
   WebGL/2D contexts that take literal colour strings and cannot read a CSS
   custom property. It mirrors the five hue knobs in `PALETTE` and the neutral
   knobs, in both schemes, in `NEUTRALS`; everything else is derived from them —
   the fifteen categorical stops, node fills, edge colours, legend chips, the
   unknown-type grey, the chunk-node grey, the canvas ground, the label ink.
   `entityTypeColors.test.ts` parses `globals.css` and **fails if either mirror
   drifts**; that test is the enforcement, do not weaken it.

   Every other file that paints to a canvas imports from here rather than
   declaring its own literal — `graphCanvasColor(isDark)` / `graphInkColor(isDark)`
   for the ground and labels, `resolvePalette()` and `graphEdgeColors()` for hues
   that must honour a tenant override, `withAlpha()` for a translucent
   `rgba()` string, `toGlRgba()` for cosmos.gl's normalised `[r,g,b,a]`. That
   includes the benchmark harness under `components/graph/benchmark/` and
   `components/reports/GraphTraversalAnimation.tsx`. Adding a graph colour means
   adding a derivation, never a new hex.
2. **Third-party brand marks** — `components/auth/SocialSignInButton.tsx`
   carries Microsoft's official logo colours. Vendor logos are reproduced as
   specified and are not themeable. No other file qualifies.

## Interface principles

General rules for designing interface screens. They sit on top of the colour
system above and never contradict it. When a screen and these rules disagree,
change the screen. When you build something, look for an existing shared
implementation of the pattern first, and reuse it.

### Say less

- **No heading on something that names itself.** A table of companies needs no
  "Companies" title. Keep a heading only where two sections would otherwise be
  confused. Keep the name for screen readers as an accessible label.
- **No explanatory sentence under a heading.** If a heading needs explaining,
  rename it.
- **Show each number once.** A count lives in one place, not in a badge, a pager
  and a summary line. A header does not repeat a count the panel below it shows.
- **Hide zeroes and non-events.** Don't show "0 excluded". Show a note only when
  it is true for that item, and never repeat the same note on every row.
- **Empty states are one line and at most one action.** Don't explain why it is
  empty.
- **Buttons are verbs** ("Score 12 companies"), with no reassurance sentence beside
  them.
- **Offer an option only when it does something different.** If "Use all" would do
  the same as "Use 38", show one button.

### Colour marks status with an underline, never a fill

- **Do:** show a status, verdict, count or flagged value in normal text with a
  coloured underline. Neutral states are plain text.
- **Don't:** use coloured pills, filled badges, tinted backgrounds or coloured text
  on short labels.
- **Exceptions:**
  - notices and error messages that are whole sentences
  - links
  - data shading the user switches on deliberately (a heat map)
  - the tint on a selected row

### No grey fills

- **Don't:** put a grey background behind a tile, card, filter bar, chip, button,
  field, tab or row, or turn something grey on hover.
- **Items and fields:** no fill; mark them with a thick rule in the text colour on
  the left. A list gets one rule, not one per row.
- **Secondary actions:** plain text with the hover line.
- **Primary actions:** one filled action per step, in the text colour, never a
  brand or danger colour.
- **Exceptions:** loading skeletons and the empty track of a progress bar.

### Square corners

- **Every control and pop-up is square:** buttons, checkboxes, inputs, text areas,
  selects and their menus, dialogs, side sheets, dropdown menus, tooltips and
  floating action bars.
- **Apply it at the component level for the whole area,** pop-ups included. A
  hand-built floating element needs it set separately.

### Icons are angular

- **Choose glyphs drawn only with straight lines and rectangles:** no curves, circles
  or rounded corners. Squaring off line ends alone does not fix a round glyph, so
  check how the glyph is drawn, not just how it is styled.
- **Prefer a straight metaphor to a round literal one.** Filter lines for a saved
  search instead of a magnifying glass, a browser window for websites instead of a
  globe, an asterisk instead of a medal, a list instead of a folder.
- **Draw with square line ends, sharp joins and square rectangles,** set once for the
  whole area, pop-ups included, not per icon.
- **Icons are in the text colour at full strength.** A disabled item fades its words,
  not its icon, and a component must not dim its own icons (a select's chevron, a
  dialog's close button).
- **Exception:** a mark on a solid fill, such as a checked box's tick, takes the
  fill's contrasting colour.
- **Where no straight glyph carries the meaning,** keep the clearest round one rather
  than an obscure straight one.

### Dividers run edge to edge

- **A divider reaches the edges of the area it divides,** touching whatever sits
  beside it. For a full-page table, that means the sidebar and the window edge,
  not the edge of the content padding. Extend the table through the page gutter,
  and pad its first and last cells back in, so text still lines up with the rest of
  the page.
- **Two columns of divided rows** have no gap between the columns. Each cell carries
  the divider and pads its content apart, so the lines meet. The divider goes on
  the cell itself, not on something inside a padded cell.
- **Never wrap a table in a scrolling container** unless it truly must scroll within
  a box. Anything that scrolls clips what extends past it, and pinned headers
  stick to it instead of the page. Where a table does scroll in a box, extend the
  box instead of the table.
- **Check what is visible:** a measured position can look right while clipping
  hides the line. Look at a screenshot.

### Hover draws a line

- **The hover effect is a thin line in the text colour,** drawn left to right under
  the element in about 0.3 seconds and retracting the same way. Keyboard focus
  draws it too. With reduced motion it appears without animation.
- **Where the line goes:**
  - a text link or label: under the text
  - a tile, cell or list item: along the bottom of the whole item, just above its
    divider, across label, bar and figures
  - a clickable table row: the full width of the row, not just under the name
  - an item in a menu, a sidebar or a list in a panel: the full width of that menu,
    sidebar or panel, edge to edge, even where the item's text is inset by padding
- **Only the item under the pointer draws its line.** Hovering the container that
  holds the items (a sidebar, a menu, a list) must not draw every item's line.
- **Selected or current items keep the line drawn.** That includes the current tab,
  an open menu's trigger and the chosen filter. Tabs are plain labels, not pills.
- **Don't:** change the background on hover, or use the browser's plain underline.

### Progress bars

- **Square ends; the fill is in the text colour,** not a brand colour.
- **Shimmer:** a highlight sweeps across the filled part on a loop, clipped to the
  fill.
  - A bar showing a fixed amount shimmers only while the bar, or the item it sits
    in with its label and figures, is hovered.
  - A bar tracking work still in progress shimmers all the time.

### Tables

- **Two table designs, used everywhere:** a standard table for lists of records
  (one or two lines per row) and a denser table for grids of figures. Both have a
  rule under the header and a divider between rows. Pick the density; set only
  widths and alignment per column, never per-table borders, sizes or padding.
- **Short column labels,** with the full name on hover. Figures use aligned
  (tabular) numerals.
- **Optional columns are hidden by default,** behind a checkbox. Colour coding of
  scores is an option the user turns on.
- **All filters for a table sit in one row** above it, next to its view toggles.
- **Wherever the same data appears,** it uses the same columns and the same
  options.
- **A long table's column headers stay pinned** to the top of the window while its
  rows scroll beneath them, with the header rule still drawn and nothing showing
  above them.
  - Pin them to the page's own scroller, not to a box around the table. A header
    pinned inside a box scrolls away with the box when the page moves.
  - A table wider than the page then scrolls sideways with the page, and its
    identifying column stays pinned on the left.
  - A pinned element stops at its scroller's padding, so offset it by that
    padding or it leaves a strip where rows show through. Check this by scrolling
    in a real browser.

### Pages and navigation

- **Every top-level destination gets its own tab,** never a button tucked inside
  another tab.
- **Detail is one layer deep:** the page shows the score, and the reasoning,
  sources and documents open in a dialog.
- **Two columns of equal cells,** with label and value at the same size and weight.
- **State worth sharing lives in the URL:** filters, the open item, the open
  dialog.
- **Charts:**
  - no title, legend or axis label when hovering a mark already says what it is
  - marks are square
  - leave out items that were never scored on the chart's scale
  - put a summary chart between the headline counts and the filters it responds to
- **Downloads respect what the user is looking at:** an export includes exactly the
  items the current filters show, across every page, with the same detail per item
  as a full export.

### Defaults and flows

- **Starting from a source creates something new.** Adding to an existing item is
  an explicit choice, and nothing is silently appended to an old draft.
- **When the usual action is "use all", preselect everything.** Let the user
  deselect, and have one primary button state the count. A hand-off that names
  specific items preselects just those.
- **Reserve space for content that loads late,** so nothing below it jumps. A
  control the user is about to click must not move.
- **Evolve an existing workflow rather than regenerating a screen from scratch.**

### Build each pattern once

Status text, the left rule, text actions, the hover line, the shimmer, the icon
stroke style, divided grids, section tabs and view toggles are each one shared
implementation. A second hand-rolled copy of any of them is a bug under the DRY
policy in `AGENTS.md`: extract and reuse instead.

### Verify in a real browser

Unit tests don't see hover, colour, layering or clipping. Check new UI in a real
browser against the running app:
- hover and focus states, and computed styles on pseudo-elements
- screenshots, judged by eye

A CSS framework can silently drop selectors from a combined rule, so confirm the
compiled stylesheet contains what you wrote.

## Component library

Each interface pattern above has one implementation. Use it; never hand-roll a
second copy (DRY policy in `AGENTS.md`). Primitives live in
`frontend/components/ui/`, patterns in `frontend/components/library/` (one
barrel, `@/components/library`).

**Primitives already follow the principles**, so use their defaults:

- `Button`: `default` is the one ink filled action per step (`brand` and
  `destructive` are aliases of it: never a coloured primary). `outline`,
  `secondary`, `ghost` and `link` are all a text action with the drawn line.
  `loading` shimmers the button; no spinner.
- Fields (`Input`, `Textarea`, `SelectTrigger`, `FormInput`, `FormSelect`,
  `InputGroup`) carry the left rule.
- `Badge` renders as `StatusText`; `Card` is flat; `Tabs` are line tabs; `Modal` is
  built on `Dialog` (one dialog design: no border, no shadow, one ink primary).
- `Table` has two densities: `standard` for lists of records (one or two lines per
  row) and `dense` for grids of figures. Long tables set `stickyHeader`. Rows have
  no hover fill; a clickable row is `group draw-underline cursor-pointer`.
  `DataTable` passes both through; `Pagination` renders `TablePager`.
- `Progress` fills in ink and shimmers with `active`.
- Global CSS squares every control and pop-up, draws icons with square caps and
  mitred joins, and bleeds tables through the page gutter (`--page-gutter`), with
  pinned headers offset by `--table-sticky-top`.

**Patterns** (`@/components/library`):

| Need | Use |
|---|---|
| Page header | `PageHeader` (title for screen readers, actions, tabs); `SubpageHeader` for a detail page |
| Section tabs that are routes | `SectionTabs` |
| Section heading where two would be confused | `SurfaceHeader` inside a flat `Surface` |
| Status, verdict, flagged figure | `StatusText` |
| Sentence notice | `Notice` (tint, or the left rule when neutral) |
| Empty list | `EmptyState` (one line, at most one action) |
| Load failure | `LoadError` |
| No permission | `AccessDenied` |
| Facts, label and value | `KeyValueGrid` |
| Headline figures | `StatGrid`; a figure that links somewhere: `Tile` |
| Choice among sources or types | `OptionTile` |
| Checkbox / radio options | `OptionList` with `OptionRow` / `RadioRow` |
| Search a list | `SearchInput` |
| Filter a table | `FilterMenu`, all filters in one row with `ViewToggle`s |
| Sortable column | `SortableTableHead` |
| Row actions | `RowMenu` |
| Bulk actions on selected rows | `SelectionBar` |
| Confirm a destructive action | `ConfirmDialog` |
| Steps of a flow or pipeline | `Stepper` |
| Next page of a list | `LoadMore` (or `TablePager` for numbered pages) |
| Value to copy | `CopyField` (`useCopyToClipboard` for custom UI) |
| Link out | `ExternalLink` |
| Preformatted text | `CodeBlock` |
| Short help on hover | `InfoTip` (prefer a clearer label) |
| Class constants | `LEFT_RULE_CLASS`, `TEXT_ACTION_CLASS`, `ICON_ACTION_CLASS`, `MENU_TRIGGER_CLASS`, `SELECTED_LINE_CLASS`, `DIVIDED_GRID_CLASS`, `CAPTION_CLASS` |

Helpers: `lib/format.ts` (`plural`), `lib/nav.ts` (`isPathActive`), `lib/date.ts`
(the one date format), `lib/jobs.ts` (`getJobStatusBadge`, the one job status map).
