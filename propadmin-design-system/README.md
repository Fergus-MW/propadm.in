# Propadmin design system — reusable source kit

Start with `docs/STYLE-GUIDE.md`, then `docs/INTEGRATION.md`. Open `preview/index.html` for a light/dark visual reference.

Includes the current design specification, palette and semantic tokens, reusable React UI primitives and interface patterns, required helpers, a component catalogue, pinned dependency manifest, and compiled CSS. The component sources are extracted from the workspace's canonical `platform/` checkout, not an alternate worktree.

| Path | Contents |
| --- | --- |
| `docs/STYLE-GUIDE.md` | Portable current style guide, type and spacing reference |
| `docs/COMPONENT-SYSTEM.md` | Component catalogue and exported APIs |
| `docs/INTEGRATION.md` | Setup, fonts, theming, layout and router adapters |
| `docs/reference/` | Original current specification and explicitly historical guide |
| `styles/globals.css` | Original Tailwind v4 token definitions and shared interactions |
| `styles/design-system.css` | Compiled CSS for the supplied classes |
| `tokens/design-tokens.json` | Machine-readable CSS variable definitions, including dark overrides |
| `components/ui/` | React primitives, tables, fields, dialogs and charts |
| `components/library/` | Shared interface patterns |
| `lib/`, `hooks/`, `components/ai-elements/prose.ts` | Required helpers and theme utilities |
| `preview/` | Static visual reference |
| `manifest.json` | Source revision, file provenance and checksums |
| `VALIDATION.md` | Checks run on the exported kit |

This is a source kit rather than a standalone application. React components use TypeScript, Tailwind 4 and Radix; some route patterns use Next.js. Source dependency versions are retained. Application routes, API clients, authentication, tenant providers, data and environment files are outside the kit.

The current guide supersedes the historical one. Font binaries are not bundled; use the integration instructions to load Geist or a fallback.
