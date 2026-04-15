#!/bin/bash
# Saddle-stitch booklet imposition.
#
# Takes a letter-size PDF and produces a 2-up portrait-tabloid (11x17) PDF
# whose pages, when printed duplex (flip on long edge) on tabloid stock,
# stacked, and folded in half horizontally, yield a booklet with the
# input pages in reading order.
#
# Usage: modern/build_booklet.sh [INPUT.pdf] [OUTPUT.pdf]
# Defaults: INPUT  = modern/all_hymns.pdf
#           OUTPUT = modern/all_hymns_booklet.pdf
#
# Dependencies: psutils (pstops, psselect), poppler-utils (pdftops,
# pdfinfo), ghostscript (ps2pdf). Install on Debian/Ubuntu:
#   sudo apt install psutils poppler-utils ghostscript

set -e

# Resolve paths relative to the repo root (parent of this script's dir).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

INPUT="${1:-modern/all_hymns.pdf}"
OUTPUT="${2:-modern/all_hymns_booklet.pdf}"

if [ ! -f "$INPUT" ]; then
  echo "error: input PDF not found: $INPUT" >&2
  exit 1
fi

# Refuse to clobber the input, even via different relative paths.
if [ "$(readlink -f "$INPUT")" = "$(readlink -f "$OUTPUT" 2>/dev/null || echo "$OUTPUT")" ]; then
  echo "error: output path equals input path" >&2
  exit 1
fi

# Check tools.
for tool in pdftops pdfinfo pstops psselect ps2pdf; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: required tool '$tool' not found in PATH" >&2
    echo "hint: sudo apt install psutils poppler-utils ghostscript" >&2
    exit 1
  fi
done

# Workspace in a scratch dir next to the output.
OUT_DIR="$(dirname "$OUTPUT")"
mkdir -p "$OUT_DIR"
TMP="$(mktemp -d "${OUT_DIR}/.booklet.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# 1. PDF -> PostScript (letter).
pdftops -paper letter "$INPUT" "$TMP/input.ps"

# 2. Determine page count and round up to next multiple of 4.
N=$(pdfinfo "$INPUT" | awk '/^Pages:/ {print $2}')
if [ -z "$N" ] || [ "$N" -lt 1 ]; then
  echo "error: could not determine page count of $INPUT" >&2
  exit 1
fi

PAD=$(( (4 - N % 4) % 4 ))
TOTAL=$(( N + PAD ))

# 3. If padding is needed, make a blank letter-size PS page and append.
if [ "$PAD" -gt 0 ]; then
  # Generate one blank letter PS page via ghostscript.
  gs -q -dNOPAUSE -dBATCH -sDEVICE=ps2write \
     -sPAPERSIZE=letter -dFIXEDMEDIA \
     -o "$TMP/blank1.ps" \
     -c "showpage" >/dev/null

  # psselect the blank page PAD times to build a PAD-page blank PS.
  BLANK_SPEC="1"
  for ((i=1; i<PAD; i++)); do BLANK_SPEC="$BLANK_SPEC,1"; done
  psselect -p"$BLANK_SPEC" "$TMP/blank1.ps" "$TMP/blank.ps"

  # Concatenate input.ps + blank.ps by re-selecting pages from each.
  # Simplest reliable approach: use psselect to reorder into padded layout.
  # Build a combined PS by merging with a small helper: use psjoin-style
  # concatenation via pstops on each then cat won't work reliably for PS,
  # so instead convert back through pdf: pad via gs on the PDF.
  #
  # Reliable path: build a padded PDF using gs, then redo pdftops.
  # Create a blank letter PDF with PAD pages, then concat via gs.
  BLANK_PDF="$TMP/blank.pdf"
  gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
     -sPAPERSIZE=letter -dFIXEDMEDIA \
     -dDEVICEWIDTHPOINTS=612 -dDEVICEHEIGHTPOINTS=792 \
     -o "$BLANK_PDF" \
     -c "$(printf 'showpage %.0s' $(seq 1 "$PAD"))" >/dev/null

  PADDED_PDF="$TMP/padded.pdf"
  gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
     -sPAPERSIZE=letter \
     -o "$PADDED_PDF" "$INPUT" "$BLANK_PDF" >/dev/null

  pdftops -paper letter "$PADDED_PDF" "$TMP/input.ps"
fi

# 4. Build the saddle-stitch page order.
# For a booklet of TOTAL pages (multiple of 4), sheet k (1..TOTAL/4) has:
#   front side: page (TOTAL - 2k + 2), page (2k - 1)
#   back  side: page (2k),             page (TOTAL - 2k + 1)
# Reading order of the flat output (each PS page is one side of one sheet):
#   sheet1-front, sheet1-back, sheet2-front, sheet2-back, ...
# 2-up imposition will place the pair on a single tabloid sheet.
ORDER=""
SHEETS=$(( TOTAL / 4 ))
for ((k=1; k<=SHEETS; k++)); do
  FL=$(( TOTAL - 2*k + 2 ))   # front-left
  FR=$(( 2*k - 1 ))           # front-right
  BL=$(( 2*k ))               # back-left
  BR=$(( TOTAL - 2*k + 1 ))   # back-right
  if [ -z "$ORDER" ]; then
    ORDER="$FL,$FR,$BL,$BR"
  else
    ORDER="$ORDER,$FL,$FR,$BL,$BR"
  fi
done

psselect -p"$ORDER" "$TMP/input.ps" "$TMP/reordered.ps"

# 5. 2-up impose onto portrait tabloid (792 x 1224 pts = 11 x 17).
# Each letter page (612 x 792) is rotated left (becomes 792 x 612) and
# placed at x=792 with y-offset 0 (bottom) or 612 (top). Fold is the
# horizontal line at y=612 on the tabloid sheet.
pstops '2:0L(792,0)+1L(792,612)' "$TMP/reordered.ps" "$TMP/booklet.ps"

# 6. PS -> PDF at tabloid size.
ps2pdf -sPAPERSIZE=tabloid "$TMP/booklet.ps" "$OUTPUT"

OUT_PAGES=$(pdfinfo "$OUTPUT" | awk '/^Pages:/ {print $2}')
OUT_SIZE=$(pdfinfo "$OUTPUT" | awk '/^Page size:/ {print $3, $4, $5, $6, $7}')
echo "Built $OUTPUT: $OUT_PAGES pages @ $OUT_SIZE (input $N pages, padded to $TOTAL)"
