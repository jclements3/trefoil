#!/bin/bash
# Build a multi-hymn PDF from a LilyPond source file.
# Usage:
#   modern/build_pdf.sh [INPUT_LY] [OUTPUT_PDF]
# Defaults:
#   INPUT_LY   = modern/samples.ly
#   OUTPUT_PDF = modern/samples.pdf

set -e

INPUT="${1:-modern/samples.ly}"
OUTPUT="${2:-modern/samples.pdf}"

cd "$(dirname "$0")/.."

if [ ! -f "$INPUT" ]; then
    echo "ERROR: input LilyPond source not found: $INPUT" >&2
    exit 1
fi

if ! command -v lilypond >/dev/null 2>&1; then
    echo "ERROR: lilypond not installed. Run: apt install lilypond" >&2
    exit 2
fi

OUT_DIR="$(dirname "$OUTPUT")"
OUT_STEM="$(basename "$OUTPUT" .pdf)"

# LilyPond --output takes a stem, not a full .pdf path.
lilypond --output="$OUT_DIR/$OUT_STEM" "$INPUT" 2>&1 | tail -20

if [ ! -f "$OUTPUT" ]; then
    echo "ERROR: lilypond did not produce $OUTPUT" >&2
    exit 3
fi

ls -la "$OUTPUT"
if command -v pdfinfo >/dev/null 2>&1; then
    pdfinfo "$OUTPUT" | grep -Ei "pages|file size" || true
fi
