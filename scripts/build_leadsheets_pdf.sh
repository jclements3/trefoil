#!/bin/bash
# Build handout/leadsheets.pdf + handout/leadsheet{1..8}.html
# Usage: scripts/build_leadsheets_pdf.sh [KEY]   (default Eb)
set -e
KEY="${1:-Eb}"
cd "$(dirname "$0")/.."
python3.10 scripts/generate_leadsheets.py "$KEY"
cd handout
abcm2ps leadsheets.abc -O leadsheets.ps
# Flip to landscape page
sed -i 's|%%BoundingBox: 0 0 612 792|%%BoundingBox: 0 0 792 612|' leadsheets.ps
sed -i 's|PageSize\[612 792\]|PageSize[792 612]|' leadsheets.ps
# abcm2ps centers titles at 340.8 for 612-wide page; shift to 396 for 792-wide
sed -i 's|^340.8 |396.0 |g' leadsheets.ps
ps2pdf leadsheets.ps leadsheets.pdf
echo "Built handout/leadsheets.pdf ($(pdfinfo leadsheets.pdf 2>/dev/null | grep Pages | awk '{print $2}') page(s))"
