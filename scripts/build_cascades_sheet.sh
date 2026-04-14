#!/bin/bash
# Build handout/cascades_sheet.pdf (letter, 1-up) and handout/cascades_booklet.pdf
# (tabloid, 2-up fold-booklet) from cascades.tex via MEI + Verovio.
set -e
cd "$(dirname "$0")/.."
python3 scripts/build_cascades_mei.py
python3 <<'PY'
import os, verovio
tk = verovio.toolkit()
# Letter paper: 8.5x11 in. Verovio uses 1/100 mm -> letter = 2159 x 2794.
tk.setOptions({
    'pageWidth': 2159,
    'pageHeight': 2794,
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
    rsvg-convert -f pdf -o "${svg%.svg}_raw.pdf" "$svg"
    # Scale whatever rsvg produced up to letter (8.5x11 in / 612x792 pt)
    gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sPAPERSIZE=letter \
       -dFIXEDMEDIA -dPDFFitPage -dCompatibilityLevel=1.4 \
       -o "${svg%.svg}.pdf" "${svg%.svg}_raw.pdf"
    rm "${svg%.svg}_raw.pdf"
done
pdfunite p*.pdf ../cascades_sheet.pdf
cd ..
rm -rf .cascades_pages

# Pad to a multiple of 4 pages for saddle-stitch booklet imposition.
PAGES=$(pdfinfo cascades_sheet.pdf | awk '/^Pages:/ {print $2}')
REM=$((PAGES % 4))
if [ "$REM" -ne 0 ]; then
    NEEDED=$((4 - REM))
    # Simple blank letter page via a tiny .tex wrapper
    cat > /tmp/_blank.tex <<'TEX'
\documentclass[letterpaper]{article}\usepackage[margin=0in]{geometry}\pagestyle{empty}\begin{document}\null\newpage\end{document}
TEX
    (cd /tmp && pdflatex -interaction=nonstopmode _blank.tex >/dev/null)
    BLANKS=""
    for i in $(seq 1 $NEEDED); do BLANKS="$BLANKS /tmp/_blank.pdf"; done
    pdfunite cascades_sheet.pdf $BLANKS _padded.pdf && mv _padded.pdf cascades_sheet.pdf
fi

# Saddle-stitch signature ordering: sheet K has outer={N-2K, 2K+1} and
# inner={2K+2, N-2K-1}, K=0..N/4-1.
PAGES=$(pdfinfo cascades_sheet.pdf | awk '/^Pages:/ {print $2}')
ORDER=$(python3 -c "
n=$PAGES; parts=[]
for i in range(n//4):
    parts += [n-2*i, 2*i+1, 2*i+2, n-2*i-1]
print(','.join(str(p) for p in parts))
")

pdftops -paper letter cascades_sheet.pdf cascades_sheet.ps
psselect -p$ORDER cascades_sheet.ps cascades_reordered.ps
pstops '2:0L(792,0)+1L(792,612)' cascades_reordered.ps cascades_booklet.ps
ps2pdf -sPAPERSIZE=tabloid cascades_booklet.ps cascades_booklet.pdf
rm -f cascades_sheet.ps cascades_reordered.ps cascades_booklet.ps

echo "Built handout/cascades_sheet.pdf (letter, 1-up): $(pdfinfo cascades_sheet.pdf | awk '/Pages:/ {print $2}') pages"
echo "Built handout/cascades_booklet.pdf (tabloid, fold-booklet): $(pdfinfo cascades_booklet.pdf | awk '/Pages:/ {print $2}') sheets"
