#!/bin/bash
# Impose handout.pdf (4 letter pages) as a 2-sheet portrait tabloid booklet.
# Output: booklet.pdf at repo root. Print 11x17, fold in half horizontally.
set -e
cd "$(dirname "$0")/.."
pdftops -paper letter handout/handout.pdf handout/handout.ps
pstops '2:0L(792,0)+1L(792,612)' handout/handout.ps handout/booklet.ps
ps2pdf -sPAPERSIZE=tabloid handout/booklet.ps booklet.pdf
rm -f handout/handout.ps handout/booklet.ps
echo "Built booklet.pdf: $(pdfinfo booklet.pdf | awk '/Pages:/ {print $2} /Page size:/ {print $3,$4,$5}' | paste -sd ' ')"
