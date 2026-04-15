#!/usr/bin/env python3.10
"""Build one PDF per lever-harp key from app/lead_sheets.json.

For each of the 8 lever-harp keys (Eb, Bb, F, C, G, D, A, E), filter
lead_sheets.json by hymn `key`, skip unsupported meter exceptions
(M:none, 3/2, 8/4), sort by cleaned title, run the full modern
reharmonization pipeline on each hymn, and emit:

    modern/by_key/<key>.ly
    modern/by_key/<key>.pdf

Each PDF opens with a cover-page markup page announcing the key and
count. Failures on individual hymns are logged and skipped.

Reuses modern.{reharm_rules, voicing_picker, abc_rewriter, abc_to_ly,
chord_overlay, layout} and the `run_pipeline` function from
modern.verify_samples. ASCII only. python3.10.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
OUT_DIR = os.path.join(REPO_ROOT, "modern", "by_key")
BUILD_PDF_SCRIPT = os.path.join(REPO_ROOT, "modern", "build_pdf.sh")

ALL_KEYS = ["Eb", "Bb", "F", "C", "G", "D", "A", "E"]
SKIP_METERS = {"none", "3/2", "8/4"}

METER_RE = re.compile(r"(?m)^M:\s*([^\n]+)")

KEY_DESCRIPTIONS = {
    "Eb": "Eb major (3 flats)",
    "Bb": "Bb major (2 flats)",
    "F":  "F major (1 flat)",
    "C":  "C major (no sharps or flats)",
    "G":  "G major (1 sharp)",
    "D":  "D major (2 sharps)",
    "A":  "A major (3 sharps)",
    "E":  "E major (4 sharps)",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else "?"


_CLEAN_TITLE_RE = re.compile(r"[^A-Za-z0-9 ]+")


def clean_title_key(title: str) -> str:
    """Return a lower-case, punctuation-stripped sort key for a title."""
    s = title.strip().lower()
    s = _CLEAN_TITLE_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_modules() -> dict[str, Any]:
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    names = [
        "modern.reharm_rules",
        "modern.voicing_picker",
        "modern.abc_rewriter",
        "modern.abc_to_ly",
        "modern.chord_overlay",
        "modern.layout",
        "modern.verify_samples",
    ]
    loaded: dict[str, Any] = {}
    for name in names:
        loaded[name] = importlib.import_module(name)
    return loaded


# ---------------------------------------------------------------------------
# Cover page markup injection
# ---------------------------------------------------------------------------


def _ascii(s: str) -> str:
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in s)


def cover_markup(key: str, count: int) -> str:
    desc = KEY_DESCRIPTIONS.get(key, "%s major" % key)
    title = "Hymns in %s major" % key
    count_line = "%d hymn%s" % (count, "" if count == 1 else "s")
    first_line = "Set your harp to %s to play these." % desc
    # Palatino bold centered. A trailing \\pageBreak forces the hymns to
    # start on a fresh page.
    return (
        "\\markup {\n"
        "  \\vspace #8\n"
        "  \\fill-line {\n"
        "    \\override #'(font-name . \"TeX Gyre Pagella Bold\")\n"
        "    \\fontsize #10\n"
        "    \"%s\"\n"
        "  }\n"
        "  \\vspace #2\n"
        "  \\fill-line {\n"
        "    \\override #'(font-name . \"TeX Gyre Pagella\")\n"
        "    \\fontsize #4\n"
        "    \"%s\"\n"
        "  }\n"
        "  \\vspace #1\n"
        "  \\fill-line {\n"
        "    \\override #'(font-name . \"TeX Gyre Pagella Italic\")\n"
        "    \\fontsize #2\n"
        "    \"%s\"\n"
        "  }\n"
        "}\n"
        "\\pageBreak\n"
    ) % (_ascii(title), _ascii(count_line), _ascii(first_line))


def inject_cover(ly_src: str, key: str, count: int) -> str:
    """Insert the cover markup immediately after the first '\\bookpart {'."""
    marker = "\\bookpart {\n"
    idx = ly_src.find(marker)
    if idx < 0:
        # Fallback: insert after '\\book {\n'
        marker = "\\book {\n"
        idx = ly_src.find(marker)
        if idx < 0:
            return ly_src
    insert_at = idx + len(marker)
    return ly_src[:insert_at] + cover_markup(key, count) + ly_src[insert_at:]


# ---------------------------------------------------------------------------
# Per-key build
# ---------------------------------------------------------------------------


def filter_and_sort(hymns: list[dict], key: str) -> tuple[list[dict], int]:
    """Return (kept_hymns, n_skipped_meter) for the requested key."""
    kept = []
    n_skipped = 0
    for h in hymns:
        if h.get("key") != key:
            continue
        meter = parse_meter(h.get("abc", ""))
        if meter in SKIP_METERS:
            n_skipped += 1
            continue
        kept.append(h)
    kept.sort(key=lambda h: clean_title_key(h.get("t", "")))
    return kept, n_skipped


def build_one_key(key: str, hymns: list[dict],
                  modules: dict[str, Any]) -> dict:
    run_pipeline = modules["modern.verify_samples"].run_pipeline
    layout = modules["modern.layout"]

    kept, n_skipped_meter = filter_and_sort(hymns, key)
    t0 = time.time()

    results: list[dict] = []
    errors: list[tuple[str, str]] = []
    for h in kept:
        try:
            results.append(run_pipeline(h, modules))
        except Exception as exc:
            errors.append((str(h.get("n", "?")),
                           "%s: %s" % (type(exc).__name__, exc)))

    # Build combined_input for layout.build_combined_ly.
    combined_input = []
    for r in results:
        h = r["hymn"]
        try:
            x = int(h.get("n", 0))
        except (TypeError, ValueError):
            x = 0
        combined_input.append({
            "X": x,
            "n": h.get("n"),
            "t": h.get("t", "Untitled"),
            "abc": h.get("abc", ""),
            "key": h.get("key", "C"),
            "meter": r["meter"],
            "chord_labels": r.get("chord_labels", []),
        })

    ly_src = layout.build_combined_ly(combined_input, per_page=4)
    ly_src = inject_cover(ly_src, key, len(combined_input))

    ly_path = os.path.join(OUT_DIR, "%s.ly" % key)
    pdf_path = os.path.join(OUT_DIR, "%s.pdf" % key)
    with open(ly_path, "w", encoding="utf-8") as fh:
        fh.write(ly_src)

    pdf_ok = False
    build_log = ""
    try:
        proc = subprocess.run(
            [BUILD_PDF_SCRIPT, ly_path, pdf_path],
            capture_output=True, text=True, check=False,
        )
        build_log = (proc.stdout or "") + (proc.stderr or "")
        pdf_ok = (proc.returncode == 0) and os.path.exists(pdf_path)
    except FileNotFoundError as exc:
        build_log = "build_pdf.sh missing: %s" % exc

    elapsed = time.time() - t0
    pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
    pages = pdf_page_count(pdf_path) if os.path.exists(pdf_path) else 0

    return {
        "key": key,
        "n_candidates": len(kept),
        "n_skipped_meter": n_skipped_meter,
        "n_processed": len(results),
        "errors": errors,
        "ly_path": ly_path,
        "pdf_path": pdf_path,
        "pdf_ok": pdf_ok,
        "pdf_size": pdf_size,
        "pages": pages,
        "elapsed_sec": elapsed,
        "build_log_tail": build_log[-500:] if not pdf_ok else "",
    }


def pdf_page_count(path: str) -> int:
    try:
        proc = subprocess.run(
            ["pdfinfo", path],
            capture_output=True, text=True, check=False,
        )
        for line in (proc.stdout or "").splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(":", 1)[1].strip())
    except FileNotFoundError:
        pass
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if not os.path.exists(LEAD_SHEETS_PATH):
        print("ERROR: %s not found" % LEAD_SHEETS_PATH, file=sys.stderr)
        return 2

    os.makedirs(OUT_DIR, exist_ok=True)

    try:
        modules = load_modules()
    except Exception as exc:
        print("ERROR: failed to load pipeline modules: %s" % exc,
              file=sys.stderr)
        return 3

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    summary: list[dict] = []
    t_start = time.time()
    for key in ALL_KEYS:
        print("=" * 60)
        print("Building %s ..." % key)
        result = build_one_key(key, hymns, modules)
        summary.append(result)
        status = "OK" if result["pdf_ok"] else "FAIL"
        print("  [%s] %s: candidates=%d skipped_meter=%d "
              "processed=%d errors=%d pages=%d size=%d bytes "
              "elapsed=%.1fs" % (
                  status, key,
                  result["n_candidates"],
                  result["n_skipped_meter"],
                  result["n_processed"],
                  len(result["errors"]),
                  result["pages"],
                  result["pdf_size"],
                  result["elapsed_sec"],
              ))
        for n, msg in result["errors"]:
            print("    error on hymn %s: %s" % (n, msg))
        if not result["pdf_ok"] and result["build_log_tail"]:
            print("  build log tail:")
            for line in result["build_log_tail"].splitlines()[-10:]:
                print("    %s" % line)

    total_elapsed = time.time() - t_start
    total_pages = sum(r["pages"] for r in summary)
    total_size = sum(r["pdf_size"] for r in summary)
    n_ok = sum(1 for r in summary if r["pdf_ok"])

    print("=" * 60)
    print("Totals: %d/%d PDFs built, %d pages, %d bytes, %.1fs elapsed" % (
        n_ok, len(summary), total_pages, total_size, total_elapsed))
    for r in summary:
        print("  %2s: %3d hymns -> %s (%d pages, %d bytes)" % (
            r["key"], r["n_processed"],
            os.path.basename(r["pdf_path"]),
            r["pages"], r["pdf_size"],
        ))

    return 0 if n_ok == len(summary) else 1


if __name__ == "__main__":
    sys.exit(main())
