# Integration

## Copy into an existing application

This is a source kit, not a published npm package. It targets React 19, TypeScript and Tailwind CSS 4. Next.js is required by the original route-link patterns; most primitives do not depend on Next.js.

1. Copy `components/`, `hooks/` and `lib/` into your source root. Keep `@/*` pointing at that root, or rewrite the imports to your existing alias. Merge helpers rather than overwriting an existing `lib/utils.ts`.
2. Merge the relevant dependencies from `package.json` into your app and install them with your package manager. Versions match the source project's lockfile at extraction. The full manifest supports every included component; direct component imports let you choose a smaller set. Luxon is only needed for `lib/date.ts`, Recharts for charts, Embla for carousels, and Sonner for copy notifications.
3. Copy `styles/globals.css` and import it once through your app's global stylesheet or entry point. It already imports Tailwind, `tw-animate-css`, and the typography plugin; avoid duplicate Tailwind imports. Use `@tailwindcss/postcss` as shown in `postcss.config.mjs`.
4. Ensure Tailwind scans the copied sources. When the library is outside automatically scanned application files, add `@source "../path/to/components";` in your stylesheet. Paths are relative to the stylesheet. Register `lib/` as well if it remains outside the scan: the markdown typography classes are in `components/ai-elements/prose.ts`.
5. Define font variables. For a fallback, use `:root { --font-geist-sans: Arial, sans-serif; --font-geist-mono: monospace; }`. To match the original, load Geist and Geist Mono with your font loader under those names.
6. Add `.dark` to `<html>` for dark mode. `lib/theme.ts` and `lib/theme-context.tsx` supply automatic/system, light and dark preferences; the storage key is `propadmin-theme`, which you may rename for your app. A Next.js host can use the supplied `THEME_INIT_SCRIPT` before hydration and wrap the client tree in `ThemeProvider`.
7. Mount a Sonner `<Toaster />` if using `CopyField`, and a `TooltipProvider` for tooltip patterns. Retain their accessible labels.

## Layout variables

Set `--page-gutter` on the padded `<main>` that owns a full-page table. Set `--table-sticky-top` for a fixed header and `--page-pad-y` where your layout needs it. The CSS bleeds table rules through the gutter and pads the first/last cells back into alignment. Avoid an overflow wrapper unless you intend a bounded scrolling table. Set `--page-gutter: 0px` for tables inside sections that should not bleed.

## Use the components

```tsx
import { Button, Table, Progress } from "@/components/ui";
import { EmptyState, StatusText } from "@/components/library";

<Button onClick={save}>Save</Button>
<StatusText variant="success">Complete</StatusText>
<Progress value={60} active aria-label="Processing" />
<EmptyState message="No records" />
// Table supports density="standard" | "dense" and stickyHeader.
```

Follow each file's actual props. For example, `SearchInput` requires `label`, `value` and `onChange`; `StatGrid` takes `stats`, and `KeyValueGrid` takes `items`.

## Framework adaptations

`PageHeader.tsx`, `RowMenu.tsx`, `SectionTabs.tsx` and `Tile.tsx` use Next.js Link or pathname APIs. In a Vite/other React app, replace those imports with your router's equivalents. Avoid the library barrel until those adaptations are made; import unrelated patterns directly. The style guide and CSS can be used in any framework, but TSX components are React sources.

`styles/design-system.css` is a precompiled stylesheet for the included classes and preview. It can be used directly in plain HTML. It cannot generate utilities you add later; rebuild with `npm run build:css` or compile `styles/globals.css` in your host app.

## Inspect and verify the kit

```sh
npm install
npm run check:imports
npm run typecheck
npm run lint:colors
npm run build:css
```

Open `preview/index.html` directly in a browser for the visual reference. It is a static reference, not a React app; its demo actions do not submit or mutate data. All real React components are included separately.

Tailwind setup and external source scanning were checked against the official Tailwind v4 docs: https://tailwindcss.com/docs/installation/using-postcss and https://tailwindcss.com/docs/detecting-classes-in-source-files.

The copied `components.json` points at `styles/globals.css`. Running a shadcn generator may overwrite the customised primitives with upstream defaults; review its output against this kit's style guide.
