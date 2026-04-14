#!/bin/bash
# Build handout/etude3.pdf — alternating LH/RH sequence, each beat one hand
# Usage: scripts/build_etude3_pdf.sh [KEY]   (default Eb)
set -e
KEY="${1:-Eb}"
cd "$(dirname "$0")/.."
python3.10 scripts/generate_etude3.py "$KEY"
cd handout
abcm2ps etude3.abc -O etude3.ps
sed -i 's|%%BoundingBox: 0 0 612 792|%%BoundingBox: 0 0 792 612|' etude3.ps
sed -i 's|PageSize\[612 792\]|PageSize[792 612]|' etude3.ps
sed -i 's|^340.8 |396.0 |' etude3.ps
ps2pdf etude3.ps etude3.pdf
echo "Built handout/etude3.pdf ($(pdfinfo etude3.pdf 2>/dev/null | grep 'Page size' | awk '{print $3, $4, $5}'), $(pdfinfo etude3.pdf 2>/dev/null | grep Pages | awk '{print $2}') page(s))"
