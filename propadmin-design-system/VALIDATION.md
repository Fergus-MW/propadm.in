# Export validation

Verified on 10 October 2026 using the source workspace's installed dependencies and the extracted kit's strict TypeScript configuration.

- TypeScript: `npm run typecheck` passed.
- Import closure: 272 source imports/exports checked, zero missing local modules or undeclared packages.
- Colour lint: `npm run lint:colors` passed.
- CSS: `npm run build:css` produced the standalone `styles/design-system.css` successfully.
- Static preview rendered from the extracted React components.
- Chromium: light and dark at 1280px, dark at 375px; no page script errors and no horizontal page overflow. Screenshots inspected visually and included in `preview/`.
- Computed styles confirmed square buttons, 4px field left rules, theme-aware canvas/ink and ink progress fills in both themes.
- Original copied source files verified against their recorded SHA-256 hashes. The exported archive was checked for integrity and excluded dependency directories, environment files, caches and symlinks.

The preview is a static visual reference. Interactive React dialogs, routing and application-specific integration should be verified in the destination application. Font binaries are not bundled, and the preview uses system-font fallbacks.

## Propadmin rename validation

The kit was renamed for Propadmin after export. Product names, documentation
links, the package name, and the theme storage key were updated. Adapted source
entries retain their original hashes in `sourceSha256`; current file hashes
reflect the renamed kit.

Local rename checks cover theme initialisation in light, dark and automatic
modes, absence of previous branding in filenames and contents, portable documentation
links, manifest checksums, colour lint, the 1,000-line limit, and ZIP integrity
and equality with the extracted files.
