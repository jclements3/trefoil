#!/bin/bash
# Overnight oemer batch on all 12 pages of omr_a4.pdf.
# Renders each page to PNG @ 300 DPI, runs oemer sequentially, logs progress.
set -e
HERE="$(dirname "$(realpath "$0")")"
WORK="$HERE/omr_work"
mkdir -p "$WORK"
cd "$WORK"

PDF="$HERE/omr_a4.pdf"
TOTAL=$(pdfinfo "$PDF" 2>/dev/null | awk '/^Pages:/ {print $2}')
echo "[batch] $TOTAL pages in $PDF"

for i in $(seq 1 "$TOTAL"); do
    PNG="$WORK/page_$(printf '%02d' "$i").png"
    MXL="$WORK/page_$(printf '%02d' "$i").musicxml"
    if [ -f "$MXL" ]; then
        echo "[skip] page $i already done"
        continue
    fi
    if [ ! -f "$PNG" ]; then
        gs -q -dNOPAUSE -dBATCH -sDEVICE=pngalpha -r300 \
           -dFirstPage=$i -dLastPage=$i \
           -sOutputFile="$PNG" "$PDF"
    fi
    echo "[oemer] page $i → $MXL ($(date))"
    START=$(date +%s)
    oemer -o "$WORK" --without-deskew "$PNG" \
        > "$WORK/page_$(printf '%02d' "$i").log" 2>&1 || {
        echo "[fail] page $i, see page_$(printf '%02d' "$i").log"
        continue
    }
    ELAPSED=$(( $(date +%s) - START ))
    # oemer writes page_NN.musicxml (same stem as input)
    echo "[ok]   page $i in ${ELAPSED}s"
done

echo "[batch] done at $(date)"
ls "$WORK"/*.musicxml 2>/dev/null | wc -l | xargs echo "[batch] musicxml count:"
