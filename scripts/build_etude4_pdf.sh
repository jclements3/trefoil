#!/bin/bash
# Build handout/etude4.pdf — L-R-R-L per 4-beat cycle
# Usage: scripts/build_etude4_pdf.sh [KEY]   (default Eb)
set -e
KEY="${1:-Eb}"
cd "$(dirname "$0")/.."
python3.10 scripts/generate_etude4.py "$KEY"
cd handout
abcm2ps etude4.abc -O etude4.ps
sed -i 's|%%BoundingBox: 0 0 612 792|%%BoundingBox: 0 0 792 612|' etude4.ps
sed -i 's|PageSize\[612 792\]|PageSize[792 612]|' etude4.ps
sed -i 's|^340.8 |396.0 |' etude4.ps
ps2pdf etude4.ps etude4.pdf
echo "Built handout/etude4.pdf ($(pdfinfo etude4.pdf 2>/dev/null | grep 'Page size' | awk '{print $3, $4, $5}'), $(pdfinfo etude4.pdf 2>/dev/null | grep Pages | awk '{print $2}') page(s))"
