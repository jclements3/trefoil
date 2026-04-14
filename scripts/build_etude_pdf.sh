#!/bin/bash
# Build handout/etude.pdf from the ABC, forcing landscape page.
# Usage: scripts/build_etude_pdf.sh [KEY]   (default Eb)
set -e
KEY="${1:-Eb}"
cd "$(dirname "$0")/.."
python3.10 scripts/generate_etude.py "$KEY"
cd handout
abcm2ps etude.abc -O etude.ps
# Flip page dimensions from portrait (612x792) to landscape (792x612)
sed -i 's|%%BoundingBox: 0 0 612 792|%%BoundingBox: 0 0 792 612|' etude.ps
sed -i 's|PageSize\[612 792\]|PageSize[792 612]|' etude.ps
# Shift title from portrait center (340.8) to landscape center (396)
sed -i 's|^340.8 |396.0 |' etude.ps
ps2pdf etude.ps etude.pdf
echo "Built handout/etude.pdf ($(pdfinfo etude.pdf 2>/dev/null | grep 'Page size' | awk '{print $3, $4, $5}'))"
