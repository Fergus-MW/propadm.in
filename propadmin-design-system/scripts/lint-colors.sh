#!/usr/bin/env bash
# Fail when frontend code uses a Tailwind palette colour or an alpha modifier on a
# neutral token. The colour rules and their two exceptions are in
# docs/design/DESIGN-SYSTEM.md.
set -euo pipefail

cd "$(dirname "$0")/.."

palette='\b(bg|text|border|ring|fill|stroke|from|to|via|decoration|outline|caret|accent|divide|shadow)-(slate|gray|grey|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}\b'
neutral_alpha='\b(bg|text|border|ring|fill|stroke|divide)-(muted|accent|secondary|border|foreground|muted-foreground)/[0-9]+\b'

if grep -rnE "${palette}|${neutral_alpha}" \
  --include='*.tsx' --include='*.ts' \
  --exclude-dir=node_modules --exclude-dir=.next .; then
  echo "lint:colors: use the semantic tokens instead (docs/design/DESIGN-SYSTEM.md)" >&2
  exit 1
fi
