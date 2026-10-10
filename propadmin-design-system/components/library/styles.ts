/** Small labels above fields and figures: smaller and medium weight, same ink. */
export const CAPTION_CLASS = "text-xs font-medium";

/** Pin through the page gutter so scrolling cells cannot show at the left edge. */
export const STICKY_CELL_CLASS =
  "sticky left-[calc(-1*var(--page-gutter,0px))] z-10 bg-background group-data-[state=selected]:bg-brand-subtle";

/** An item or field marked by a thick black rule on its left, never a grey fill. */
export const LEFT_RULE_CLASS =
  "rounded-none border-0 border-l-4 border-foreground bg-transparent shadow-none hover:bg-transparent";

/** A secondary action as text with the drawn hover underline, never a grey pill. */
export const TEXT_ACTION_CLASS =
  "draw-underline h-auto rounded-none bg-transparent px-0 shadow-none hover:bg-transparent";

/** An icon-only action (rename, remove, more): no grey hover, the drawn line instead. */
export const ICON_ACTION_CLASS =
  "draw-underline rounded-none hover:bg-transparent";

/**
 * Keeps an element's drawn line drawn while it is selected, open or current:
 * the chosen filter, an open menu's trigger, the current item in a list.
 */
export const SELECTED_LINE_CLASS =
  "aria-expanded:after:[transform:scaleX(1)] aria-pressed:after:[transform:scaleX(1)] aria-[current=true]:after:[transform:scaleX(1)] aria-[current=page]:after:[transform:scaleX(1)] aria-selected:after:[transform:scaleX(1)]";

/** A text action that opens a menu: its line stays drawn while the menu is open. */
export const MENU_TRIGGER_CLASS = `${TEXT_ACTION_CLASS} aria-expanded:after:[transform:scaleX(1)]`;

/** Full-width divided rows; also the base of the two-column fact grid. */
export const DIVIDED_LIST_CLASS = "grid [&>*]:border-b [&>*]:border-border";

/**
 * Two columns of divided rows (score and fact cells): no column gap, and each
 * grid cell carries the divider and pads its content apart, so the dividers
 * meet across the columns and run unbroken to the edges.
 */
export const DIVIDED_GRID_CLASS = `${DIVIDED_LIST_CLASS} sm:grid-cols-2 sm:[&>*:nth-child(odd)]:pr-4 sm:[&>*:nth-child(even)]:pl-4`;
