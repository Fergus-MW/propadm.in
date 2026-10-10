# Propadmin design guide

The rules every new screen in the Propadmin platform follows. Read this before
designing or building UI. Lead scoring's redesign is in
[`lead-scoring-v2/DESIGN-PLAN.md`](lead-scoring-v2/DESIGN-PLAN.md) (built).

> **Status:** Platform v2 (the `/next` UI and its `platform.ui_v2` flag) is
> retired and removed: do not rebuild it. Old `/next` links redirect to the
> classic pages. The whole app follows [`DESIGN-SYSTEM.md`](DESIGN-SYSTEM.md). Where this guide and that file
> disagree (buttons, fills, borders, corners, inks, tabs), `DESIGN-SYSTEM.md`
> describes what is built.

The platform is used by investment teams to find, check and act on company
information. Every design decision serves one goal: **an analyst understands
what they are looking at, and what to do next, within a few seconds.**

## 1. Principles

### 1.1 One next step per screen

Each screen has at most one primary (brand-filled) button: the next thing the
user should do. Everything else is secondary, quiet, or inside a menu.

- Row actions live in a `⋯` menu on the row. A list may show one frequent
  action inline ("Sync now" on a connector), revealed on hover and always
  reachable by keyboard; the rest stay in the menu.
- Actions on several items appear in a selection bar once items are selected.
- Configuration and admin controls live on their own settings page, not as a
  toggle on the working page.
- One way to open a thing. If a row click opens the company, there is no extra
  "open" button or chevron doing the same.

### 1.2 Separate with space and tone, not lines

No borders or divider lines to structure a page. Structure comes from:

- **Ground and surface.** The page sits on the ground tone; content groups sit
  on white surfaces. The contrast between the two replaces card outlines.
- **Spacing.** Related things are close; unrelated groups get a clear gap.
- **Tint for state.** Hover, selected and "needs attention" rows get a tint,
  never an outline.

Borders are allowed only where they carry meaning a tint cannot: the focus
ring, and an input edge when an input sits directly on a white surface and has
no fill.

### 1.3 One colour system, set in one file

Every colour comes from the eight palette knobs in `frontend/app/globals.css`
(five hues, plus canvas, ink and line) and the tokens derived from them. A
tenant can re-theme the five hues, so a hard-coded colour breaks tenant
theming.

- Never write a hex, `rgb()` or Tailwind palette colour (`zinc-500`, `gray-200`)
  in a component.
- Never put an opacity modifier on a neutral (`bg-muted/30`,
  `border-border/60`). The file defines exactly the greys the product uses; a
  modifier invents a new one. This is the main reason the current UI has so
  many greys.
- **Brand** means "act here" or "selected". It is not decoration.
- **Status hues** (success, info, warning, destructive) mean state only, always
  as a soft tint with its matching text: the `Badge` variants `success`,
  `info`, `warning`, `error`, `brand`.
- **Charts** use the brand hue for a single series and shades of it for
  ordered data (for example tiers). The five `chart-*` hues are only for
  categories that really differ.

### 1.4 Two inks

Content is the ink colour (`--foreground`). Meta text that sits beside
content, such as captions, timestamps, "started by", table headers and help
text, is the second ink `--muted-foreground` (62% ink on canvas). The token
has that value inside a v2 page (the `.v2` scope in `globals.css`); the
classic UI keeps one ink until it is retired. Nothing else is grey.
Hierarchy within content still comes from **size and weight**. `--placeholder` / `--ink-soft`
exists only for placeholder text and "no data" in charts, never for prose.

Why two: analysts read dense tables all day, and one ink at a smaller size
does not separate a label from its value at a glance. The guide used to say
one ink; it changed after the lead scoring v2 mockups needed a
grey the tokens did not have.

### 1.5 Numbers lead

This is an analysis tool. Scores, counts and money are the content.

- Show the important number large and let its label be small.
- Use tabular numerals (`tabular-nums`) wherever numbers line up in columns.
- Show a score with its scale ("40 / 45"), and a change with its sign ("+3").
- Keep colour out of plain numbers. Only a meaningful exception (a negative
  margin, a failed gate) gets a status colour.

### 1.6 Show the evidence

Anything an agent produced (a score, a finding, a decision) links to where it
came from: the source document, the agent trace, or the person who decided.
Users trust a number they can check.

### 1.7 Progressive disclosure

Show the answer first and the detail on demand. An overview first, a detail
page on click, the agent trace one more click away. Do not put every available
panel on one screen because the data exists.

### 1.8 Plain words

- Name things by what the user understands, not how the system is built:
  "Add companies", not "Create cohort"; "Send to DealCloud", not "Execute
  delivery".
- Buttons say exactly what happens ("Score 108 companies", "Keep in ranking"),
  and the same action keeps the same name through the flow and in toasts.
- Sentence case everywhere. No all-caps labels.
- Errors say what went wrong and how to fix it. Empty states say what to do
  next and offer the button to do it.

## 2. Foundations

### 2.1 Colour tokens and their jobs

| Job | Token / utility |
| --- | --- |
| Page ground (behind surfaces) | `bg-muted` |
| Surface (content groups, menus, dialogs) | `bg-card` (`bg-background` in light) |
| Hover / pressed on a surface | `bg-accent` |
| Selected row, active filter, highlighted cell | `bg-brand-subtle` |
| Text, content | `text-foreground` |
| Text, meta (captions, timestamps, table headers, help) | `text-muted-foreground` |
| Placeholder, "no data" | `placeholder:text-(--placeholder)` on inputs, `--ink-soft` / `--viz-muted` in charts |
| Status text on its tint | `text-success-text`, `text-info-text`, `text-warning-text`, `text-destructive-text` (defined under `.v2`, each hue mixed into ink so it passes 4.5:1 on its subtle tint: 60% hue for success, info and warning in light mode, since 70% measured 4.0, 4.4 and 4.3 to 1; 80% for destructive, and 80% for all four in dark mode). The v2 `StatusChip` uses these; dots, bars and charts keep the plain hue |
| Top bar | `bg-background`; active area `bg-muted`; hover `bg-accent` |
| Primary button | `Button variant="brand"` (brand fill, canvas text). Add this variant to `Button.tsx`; the existing `default` (near-black) stays until the whole app switches |
| Secondary button on ground | `bg-card` |
| Secondary button on a surface | `bg-muted` |
| Status | `Badge` variants `success` / `info` / `warning` / `error` / `brand` |
| Focus | `ring` (keep the existing focus-visible ring) |
| Modal backdrop | `--scrim` |

If a design needs a colour that is not in this table, change `globals.css`
deliberately (with a reason in the PR), never locally.

### 2.2 Type

One family: **Geist** (already loaded as `--font-sans`). Geist Mono only for
code and IDs, never for labels.

| Role | Size / line height | Weight |
| --- | --- | --- |
| Page title | 30 / 36 | 600, tracking -0.025em |
| Hero number (a score) | 48–64 | 600, tracking -0.04em |
| Section heading | 18 / 24 | 600 |
| Sub-heading | 15 / 22 | 600 |
| Body | 14 / 20 | 400 |
| Secondary (meta, captions) | 13 / 19 or 12 / 16 | 400 |
| Numbers in tables | 13–14 | 500, `tabular-nums` |

Minimum text size is 12px. Do not use arbitrary sizes like `text-[11px]`.

### 2.3 Space, shape, depth

- **Spacing** on a 4px base: 4, 8, 12, 16, 20, 24, 32, 40. Page gutters 40px
  on desktop, 16px on mobile. 20–24px between sections.
- **Radius** by hierarchy, not one radius for everything:
  - surfaces: `rounded-2xl` / `rounded-3xl` (about 20px)
  - rows, tiles, inputs: `rounded-xl`
  - buttons, tabs, chips: `rounded-full`
- **Depth**: surfaces are flat (no shadow). Only floating things get a shadow:
  menus, popovers, dialogs, the selection bar.

### 2.4 Motion

Motion only answers an action: a menu opening, a row expanding, a toast
confirming. No looping or decorative animation (no shimmer, pulse or blur).
Respect `prefers-reduced-motion`.

## 3. Components

Build with `frontend/components/ui` (shadcn/ui on Radix). Do not add a second
component library, and do not hand-roll a control that exists there.

| Need | Use |
| --- | --- |
| Buttons | `Button` (`default`, `secondary`, `ghost`, `destructive`, sizes incl. `sm`, `icon`) |
| Status and tags | `Badge` variants |
| Menus on rows and headers | `DropdownMenu` |
| Switching views within a page | `Tabs`, styled as pills |
| Dialogs and confirmations | `Dialog` |
| Side detail without leaving the page | `Sheet` |
| Search and quick jump | `Command` |
| Inputs with icons | `Input`, `InputGroup` |
| Pickers | `Select`, `SearchSelect` |
| Tables | `Table`, `TablePager` |
| Loading | `Skeleton`, `Spinner` |
| Charts | `chart.tsx` (Recharts) with `--chart-*` / `--viz-*` tokens |

Use real `<button>` / `<a>` elements through these components. Do not add raw
`<button>` elements with ad-hoc classes; there are already too many.

When a pattern repeats across pages (a page header with section tabs, a
surface, a selection bar), make it a shared component in `components/ui` or
`components/layout` instead of copying classes.

## 4. Page patterns

### 4.1 Page anatomy

```
Top bar: workspace | Home Chat Companies Scoring Outputs Sources | Manage   ⌘K  ? avatar
Breadcrumb (detail pages only)
Page title                                   [one primary action, far right]
[Section tabs: Overview | Review 6 | Add …]
Filters / views row                          [secondary controls]
Surfaces with content …
```

- The breadcrumb shows the path, not a repeat of the title.
- Section tabs switch between the main jobs of a feature. Counts on a tab only
  when they ask for action (for example "Review 6").
- The primary action is always at the far right of the title row. A user
  who has learned one page knows where the next step is on every page.
- A short detail (a tag, a client, a connector's settings) opens as a `Sheet`
  and keeps the list; a rich detail (a company, an output, a file, a job) is
  its own page with a breadcrumb.
- Destructive actions live in the row's `⋯` menu, in the destructive colour,
  and confirm in a dialog that names the thing ("Delete 3 files?").

### 4.2 Tables and lists

- No row dividers and no header background. Rows are separated by height and
  hover tint.
- Clicking a row opens the item. Extra actions go in the row's `⋯` menu.
- Selection uses checkboxes and shows a floating selection bar with the bulk
  actions.
- Sortable columns show the active sort on the header only.
- Numbers are right-aligned and tabular.
- Rows are 44px. A list the user scans all day offers a compact 36px density
  that is remembered per list.
- `j` and `k` move the row focus, `Enter` opens, `x` selects, `Esc` closes a
  sheet or dialog, `⌘K` opens search. These are the only shortcuts.

### 4.2a Settings areas use a rail

An area made of many small pages (Manage, Account) gets an in-page rail on
the left with grouped links, not a second global navigation and not tabs.
The rail is on the ground; the current page is a `bg-card` pill. Under
1100px the rail becomes a row of pills above the content.

### 4.3 Empty, loading and error states

- **Empty:** one sentence on what would be here, and the button that fills it.
- **Loading:** `Skeleton` in the shape of the content. No spinner-only pages.
- **Error:** what failed, what to do. Keep what did load on screen.

### 4.4 Feedback

Toasts (`sonner`) confirm completed actions using the same verb as the button
("Archived Norvik Systems", with Undo when reversible).

## 5. Accessibility

- Contrast at least 4.5:1 for text (3:1 at 24px and above). Check status text
  on its tint; raise the text shade if it fails.
- Every interactive element is keyboard reachable with a visible focus ring.
- Icon-only buttons have an `aria-label`.
- Do not tell states apart by colour alone: pair colour with a label or icon.

## 6. Review checklist

Before opening a PR with UI changes, confirm:

- [ ] One primary button on the screen at most, at the far right of the
      title row.
- [ ] Meta text uses `text-muted-foreground`; nothing else is grey.
- [ ] No borders or dividers used for layout.
- [ ] No hex, `rgb()`, Tailwind palette colours or opacity modifiers on
      neutrals in the diff (`rg "#[0-9a-fA-F]{3,6}|bg-(gray|zinc|slate|neutral)|/[0-9]{2}\\b"`).
- [ ] No `text-[Npx]` sizes.
- [ ] Row actions are in a menu; no duplicate ways to open the same thing.
- [ ] Every agent-produced value links to its evidence.
- [ ] Empty, loading and error states designed.
- [ ] Works at 375px width and with the keyboard.
- [ ] Copy is sentence case, verbs match their result.
