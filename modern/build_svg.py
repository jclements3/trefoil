#!/usr/bin/env python3.10
"""Build per-hymn inline SVG assets for the Trefoil app's "Modern" mode.

This is a parallel, fallback rendering path to the Verovio/MEI pipeline
wired through `modern_mei.json`. Here we go ABC -> abc2ly -> LilyPond
(-dbackend=svg) -> one SVG per hymn, then pack them into a single
`modern_svg.json` keyed by cleaned title (matching the JS app's key
scheme in index.html).

Outputs:
    modern/svg_out/<NNNN>_<slug>.svg    -- per-hymn debug SVGs
    modern/modern_svg.json              -- combined JSON, cleanTitle -> svg
    app/modern_svg.json                 -- asset copy for local preview
    app/app/src/main/assets/modern_svg.json -- asset copy for Android build

Usage:
    python3.10 -m modern.build_svg                   # process all hymns
    python3.10 -m modern.build_svg --smoke           # 5 hardcoded hymns

Python 3.10, stdlib + modern.* only.  ASCII-only source.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODERN_DIR = os.path.join(REPO_ROOT, "modern")
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_VOICINGS = os.path.join(REPO_ROOT, "handout.tex")

SVG_OUT_DIR = os.path.join(MODERN_DIR, "svg_out")
COMBINED_JSON_LOCAL = os.path.join(MODERN_DIR, "modern_svg.json")
APP_JSON = os.path.join(REPO_ROOT, "app", "modern_svg.json")
ASSETS_JSON = os.path.join(
    REPO_ROOT, "app", "app", "src", "main", "assets", "modern_svg.json"
)

# Hardcoded smoke subset: diverse keys/meters. These hymn numbers are
# known-processable (appear in modern/all_hymns_manifest.json).
# 4114 ("The Cloud Received Christ...") is a 3/2 meter, skipped by the
# pipeline -- swap to 4191 ("Abide With Me", Eb 4/4) to keep 5 diverse
# hymns in the smoke set.
SMOKE_NUMBERS = {4051, 4068, 4084, 4146, 4191}


# ---------------------------------------------------------------------------
# cleanTitle -- mirrors the JS form used throughout index.html:
#     drill.t.replace(/^\d+\s*/, '').trim()
# ---------------------------------------------------------------------------

_LEADING_NUM_RE = re.compile(r"^\d+\s*")


def clean_title(t: str) -> str:
    """Python mirror of the app's JS title cleaner.

    index.html uses `drill.t.replace(/^\\d+\\s*/, '').trim()` consistently
    when keying MEI/SVG maps.
    """
    if not t:
        return ""
    return _LEADING_NUM_RE.sub("", t).strip()


def slugify(t: str) -> str:
    """Filesystem-safe slug for debug artifacts (NOT used as JSON key)."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return s[:60] if s else "untitled"


# ---------------------------------------------------------------------------
# Per-hymn .ly generation
# ---------------------------------------------------------------------------

# A paper block sized for ONE hymn on US Letter portrait with ragged-bottom,
# so the SVG crops naturally to just the height we need. No page breaks --
# we want one SVG page out.
SINGLE_HYMN_PAPER = r"""\version "2.22.0"

#(set-default-paper-size "letter")

\paper {
  top-margin = 0.8\cm
  bottom-margin = 0.8\cm
  left-margin = 1.2\cm
  right-margin = 1.2\cm
  between-system-space = 0.8\cm
  between-system-padding = 0.2\cm
  markup-system-spacing.padding = 0.4
  score-markup-spacing.padding = 0.3
  score-system-spacing.padding = 0.4
  system-system-spacing.padding = 0.5
  ragged-bottom = ##t
  ragged-last-bottom = ##t
  print-page-number = ##f
  #(define fonts
    (make-pango-font-tree
      "TeX Gyre Pagella"
      "TeX Gyre Pagella"
      "TeX Gyre Cursor"
      (/ staff-height pt 20)))
}
"""


def _build_single_ly(hymn_in: dict, layout_mod, abc_to_ly_mod, abc_rewriter_mod,
                     chord_overlay_mod) -> str:
    """Build a standalone single-hymn LilyPond source."""
    # Sentinel-rewrite + abc2ly, then splice in the stacked-fraction markups.
    abc_src = hymn_in.get("abc") or ""
    sentinelled, n_anns = layout_mod._rewrite_with_sentinels(abc_src, 0)
    try:
        body = abc_to_ly_mod.abc_to_lilypond(sentinelled)
    except Exception as exc:
        body = (
            "\\relative c' { \\time 4/4 c1 "
            "^\\markup { \\italic \"abc2ly failed: %s\" } }"
        ) % str(exc).replace('"', "'")

    labels = layout_mod._chord_labels_for_hymn(hymn_in, n_anns)
    body = layout_mod._substitute_markups(body, labels)
    body = layout_mod._strip_leading_score_config(body)
    body = layout_mod._force_breaks_every_n_bars(body, n=4)

    # Use the 3-per-page layout (medium staff, nice proportions for
    # single-hymn screen display as well as debugging).
    layout_cfg = layout_mod.LAYOUT_TABLE[3]
    score_block = layout_mod._bookpart(hymn_in, body, layout_cfg)

    book = "\\book {\n\\bookpart {\n" + score_block + "\n}\n}\n"
    return SINGLE_HYMN_PAPER + "\n" + book


# ---------------------------------------------------------------------------
# SVG post-processing
# ---------------------------------------------------------------------------

_XML_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>\s*", re.DOTALL)
_DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>\s*", re.DOTALL)


def strip_xml_preamble(svg: str) -> str:
    """Remove <?xml ...?> and <!DOCTYPE ...> so the string can be
    injected directly via innerHTML."""
    svg = _XML_DECL_RE.sub("", svg, count=1)
    svg = _DOCTYPE_RE.sub("", svg, count=1)
    return svg.strip()


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def _load_modern_modules():
    import importlib
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    return {
        "layout": importlib.import_module("modern.layout"),
        "abc_to_ly": importlib.import_module("modern.abc_to_ly"),
        "abc_rewriter": importlib.import_module("modern.abc_rewriter"),
        "chord_overlay": importlib.import_module("modern.chord_overlay"),
        "build_all": importlib.import_module("modern.build_all"),
        "voicing_picker": importlib.import_module("modern.voicing_picker"),
        "reharm_rules": importlib.import_module("modern.reharm_rules"),
    }


def render_hymn_to_svg(hymn_in: dict, modules: dict, tmp_dir: str) -> str | None:
    """Run LilyPond on a single-hymn .ly and return the combined SVG string.

    If LilyPond produces multiple .svg files (multi-page), concatenates
    them inside a wrapping <div>. On failure returns None.
    """
    layout_mod = modules["layout"]
    abc_to_ly_mod = modules["abc_to_ly"]
    abc_rewriter_mod = modules["abc_rewriter"]
    chord_overlay_mod = modules["chord_overlay"]

    ly_src = _build_single_ly(
        hymn_in, layout_mod, abc_to_ly_mod, abc_rewriter_mod, chord_overlay_mod
    )

    n = hymn_in.get("n") or hymn_in.get("X") or "tmp"
    stem = "hymn_%s" % str(n)
    ly_path = os.path.join(tmp_dir, stem + ".ly")
    with open(ly_path, "w", encoding="utf-8") as fh:
        fh.write(ly_src)

    cmd = [
        "lilypond",
        "--svg",
        "-dno-point-and-click",
        "-dbackend=svg",
        "--output=" + os.path.join(tmp_dir, stem),
        ly_path,
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=tmp_dir, capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        # Print last few lines of stderr for debugging.
        err_tail = (proc.stderr or proc.stdout or "")[-800:]
        sys.stderr.write("  lilypond failed for n=%s:\n%s\n" % (n, err_tail))
        return None

    # LilyPond SVG backend writes either `<stem>.svg` (single page) or
    # `<stem>-1.svg`, `<stem>-2.svg`, ... for multi-page.
    svg_files = []
    primary = os.path.join(tmp_dir, stem + ".svg")
    if os.path.exists(primary):
        svg_files.append(primary)
    else:
        idx = 1
        while True:
            p = os.path.join(tmp_dir, "%s-%d.svg" % (stem, idx))
            if not os.path.exists(p):
                break
            svg_files.append(p)
            idx += 1
    if not svg_files:
        sys.stderr.write("  lilypond produced no SVGs for n=%s\n" % n)
        return None

    pieces = []
    for sp in svg_files:
        with open(sp, "r", encoding="utf-8") as fh:
            pieces.append(strip_xml_preamble(fh.read()))
    if len(pieces) == 1:
        return pieces[0]
    # Multi-page: wrap in a div so innerHTML injection remains a single node.
    return "<div class=\"modern-svg-pages\">\n" + "\n".join(pieces) + "\n</div>"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true",
                        help="Only build the 5 hardcoded smoke hymns.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N hymns (0 = all).")
    args = parser.parse_args(argv)

    if shutil.which("lilypond") is None:
        print("ERROR: lilypond not on PATH", file=sys.stderr)
        return 2

    modules = _load_modern_modules()
    build_all = modules["build_all"]
    voicing_picker = modules["voicing_picker"]

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    # Filter out skipped meters (match build_all's rules).
    filtered = []
    for h in hymns:
        meter = build_all.parse_meter(h.get("abc", ""))
        if meter in build_all.SKIP_METERS:
            continue
        filtered.append(h)

    if args.smoke:
        filtered = [h for h in filtered
                    if int(str(h.get("n", 0) or 0)) in SMOKE_NUMBERS]
        print("Smoke mode: %d hymns selected" % len(filtered))
    elif args.limit > 0:
        filtered = filtered[:args.limit]

    # Load voicings once (shared by run_pipeline_for_hymn).
    voicings_cache = voicing_picker.load_voicings(HANDOUT_VOICINGS)

    os.makedirs(SVG_OUT_DIR, exist_ok=True)

    combined: dict[str, str] = {}
    failures: list[dict] = []
    total_bytes = 0
    t0 = time.time()

    with tempfile.TemporaryDirectory(prefix="modern_svg_") as tmp_dir:
        for i, h in enumerate(filtered, start=1):
            title = h.get("t", "Untitled")
            ctitle = clean_title(title)
            n = h.get("n")

            # 1. Run the reharm pipeline so we get rewritten ABC + chord_labels.
            try:
                result = build_all.run_pipeline_for_hymn(
                    h, {
                        "modern.reharm_rules": modules["reharm_rules"],
                        "modern.voicing_picker": voicing_picker,
                        "modern.abc_rewriter": modules["abc_rewriter"],
                        "modern.layout": modules["layout"],
                    },
                    voicings_cache,
                )
            except Exception as exc:
                failures.append({"n": n, "t": title,
                                 "stage": "pipeline",
                                 "error": "%s: %s" % (type(exc).__name__, exc)})
                print("  [%d/%d] PIPELINE FAIL n=%s: %s"
                      % (i, len(filtered), n, exc), file=sys.stderr)
                continue

            try:
                x = int(n)
            except (TypeError, ValueError):
                x = 0

            hymn_in = {
                "X": x, "n": n, "t": title,
                "abc": result.get("new_abc", h.get("abc", "")),
                "key": h.get("key", "C"),
                "meter": result.get("meter_str", ""),
                "chord_labels": result.get("chord_labels", []),
            }

            # 2. Render this single hymn to SVG.
            svg = render_hymn_to_svg(hymn_in, modules, tmp_dir)
            if svg is None:
                failures.append({"n": n, "t": title,
                                 "stage": "lilypond", "error": "render failed"})
                print("  [%d/%d] RENDER FAIL n=%s" % (i, len(filtered), n),
                      file=sys.stderr)
                continue

            # 3. Persist debug copy + in-memory dict.
            debug_path = os.path.join(
                SVG_OUT_DIR, "%s_%s.svg" % (str(n), slugify(ctitle))
            )
            with open(debug_path, "w", encoding="utf-8") as fh:
                fh.write(svg)

            combined[ctitle] = svg
            total_bytes += len(svg)
            print("  [%d/%d] OK n=%s  %s  (%d KB)"
                  % (i, len(filtered), n, ctitle, len(svg) // 1024))

    # Write combined JSON in three spots.
    payload_json = json.dumps(combined, ensure_ascii=True)
    for out in (COMBINED_JSON_LOCAL, APP_JSON, ASSETS_JSON):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="ascii") as fh:
            fh.write(payload_json)

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print("modern_svg build complete")
    print("=" * 60)
    print("  Hymns built: %d / %d" % (len(combined), len(filtered)))
    print("  Failures:    %d" % len(failures))
    print("  Total SVG:   %.1f KB (%.2f MB)"
          % (total_bytes / 1024.0, total_bytes / (1024.0 * 1024.0)))
    if combined:
        avg = total_bytes / len(combined)
        print("  Mean / hymn: %.1f KB" % (avg / 1024.0))
    print("  Elapsed:     %.1fs" % elapsed)
    print("  Wrote:       %s" % COMBINED_JSON_LOCAL)
    print("               %s" % APP_JSON)
    print("               %s" % ASSETS_JSON)
    if failures:
        fpath = os.path.join(MODERN_DIR, "modern_svg_failures.json")
        with open(fpath, "w", encoding="ascii") as fh:
            json.dump(failures, fh, indent=2, ensure_ascii=True)
        print("  Failures:    %s" % fpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ===========================================================================
# JS-patch outline (DO NOT apply yet -- this is a sketch for a follow-up
# change to app/app/src/main/assets/index.html, once this asset is built
# and reviewed).
#
# See modern/svg_app_wiring.md for the same outline in prose.
#
#   // 1) Near the top (with MODERN_MEI / TCHAIKOVSKY_MEI declarations):
#   var MODERN_SVG = {};
#
#   // 2) In the asset-loading block (after xhr_modern succeeds, ~line 2282):
#   var xhr_modern_svg = new XMLHttpRequest();
#   xhr_modern_svg.open('GET', 'modern_svg.json?v=' + Date.now(), true);
#   xhr_modern_svg.onload = function() {
#     if (xhr_modern_svg.status === 200) {
#       try {
#         MODERN_SVG = JSON.parse(xhr_modern_svg.responseText) || {};
#         console.log('Loaded ' + Object.keys(MODERN_SVG).length +
#                     ' Modern inline SVGs');
#       } catch (e) { console.warn('modern_svg.json parse failed:', e); }
#     }
#   };
#   xhr_modern_svg.onerror = function() {
#     console.warn('modern_svg.json fetch failed');
#   };
#   xhr_modern_svg.send();
#
#   // 3) In the "Modern mode has no ABC fallback" branch (around line 885,
#   //    the `if (modernMode && !tchMei) { ... }` block), BEFORE falling
#   //    through to the "not yet available" placeholder, try SVG:
#   if (modernMode && !tchMei) {
#     var cleanT = drill.t.replace(/^\d+\s*/, '').trim();
#     var svgStr = MODERN_SVG[cleanT];
#     if (svgStr) {
#       $title.textContent = drill.t;
#       $container.innerHTML = svgStr;
#       // Fit-to-area scaling, same strategy as the Verovio branch:
#       var svgs = $container.getElementsByTagName('svg');
#       var totalH = 0;
#       for (var i = 0; i < svgs.length; i++) {
#         totalH += parseFloat(svgs[i].getAttribute('height') || 0);
#       }
#       var areaH = $area.offsetHeight - 50;
#       svgScale = (areaH > 0 && totalH > 0) ? (areaH * 0.95) / totalH : 1;
#       if (svgScale > 3) svgScale = 3;
#       $container.style.transformOrigin = '0 0';
#       $container.style.transform = 'scale(' + svgScale + ')';
#       positionPlayhead();
#       abc = null;       // we're not in the abc2svg path
#       tchMidiData = null;
#       return;
#     }
#     // else: existing placeholder text.
#     ...
#   }
#
# Notes for the follow-up patch:
#   * This path does NOT give us a timemap or a MIDI export. Playhead
#     scroll sync and audio would need a separate layer (or simply disable
#     them in Modern-SVG mode for now).
#   * If both MEI and SVG are available for a title, MEI wins (handled by
#     the existing `tchMei &&` guard above this branch).
# ===========================================================================
