#!/bin/bash
# Build handout/etude2.pdf — variant with root-triad LH under every singleton
# Usage: scripts/build_etude2_pdf.sh [KEY]   (default Eb)
set -e
KEY="${1:-Eb}"
cd "$(dirname "$0")/.."
python3.10 scripts/generate_etude2.py "$KEY"
cd handout
abcm2ps etude2.abc -O etude2.ps
sed -i 's|%%BoundingBox: 0 0 612 792|%%BoundingBox: 0 0 792 612|' etude2.ps
sed -i 's|PageSize\[612 792\]|PageSize[792 612]|' etude2.ps
sed -i 's|^340.8 |396.0 |' etude2.ps
ps2pdf etude2.ps etude2.pdf
echo "Built handout/etude2.pdf ($(pdfinfo etude2.pdf 2>/dev/null | grep 'Page size' | awk '{print $3, $4, $5}'))"
