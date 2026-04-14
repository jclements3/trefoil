#!/bin/bash
# Build handout/cascades_sheet.pdf from cascades.tex via ABC + abcm2ps.
set -e
cd "$(dirname "$0")/.."
python3.10 scripts/generate_cascades.py
cd handout
abcm2ps cascades_sheet.abc -O cascades_sheet.ps
ps2pdf cascades_sheet.ps cascades_sheet.pdf
rm -f cascades_sheet.ps
echo "Built handout/cascades_sheet.pdf: $(pdfinfo cascades_sheet.pdf | awk '/Pages:/ {print $2} /Page size:/ {print $3,$4,$5}' | paste -sd ' ')"
