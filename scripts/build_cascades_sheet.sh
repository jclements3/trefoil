#!/bin/bash
# Build handout/cascades_sheet.pdf from cascades.tex via MEI + Verovio.
# Pipeline: cascades.tex -> cascades.mei -> SVG pages -> PDF pages -> concat.
set -e
cd "$(dirname "$0")/.."
python3 scripts/build_cascades_mei.py
python3 <<'PY'
import os, verovio
tk = verovio.toolkit()
tk.setOptions({
    'pageWidth': 2100,        # ~letter width in MEI units
    'pageHeight': 2970,       # ~letter height
    'scale': 40,
    'breaks': 'auto',
    'spacingLinear': 0.25,
    'spacingNonLinear': 0.5,
    'justificationSystem': 0.5,
    'systemMaxPerPage': 8,
})
tk.loadFile('handout/cascades.mei')
n = tk.getPageCount()
os.makedirs('handout/.cascades_pages', exist_ok=True)
for p in range(1, n+1):
    tk.renderToSVGFile(f'handout/.cascades_pages/p{p:02d}.svg', p)
print(f'Rendered {n} page(s)')
PY
cd handout/.cascades_pages
for svg in p*.svg; do
    rsvg-convert -f pdf -o "${svg%.svg}.pdf" "$svg"
done
pdfunite p*.pdf ../cascades_sheet.pdf
cd ..
rm -rf .cascades_pages
echo "Built handout/cascades_sheet.pdf: $(pdfinfo cascades_sheet.pdf | awk '/Pages:/ {print $2} /Page size:/ {print $3,$4,$5}' | paste -sd ' ')"
