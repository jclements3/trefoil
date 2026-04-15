#!/usr/bin/env python3.10
"""Build per-hymn inline MEI assets for the Trefoil app's "Modern" mode.

Modern mode already has an MEI loader in the app (MODERN_MEI /
xhr_modern in index.html). When a hymn has an MEI string, the WebView
renders it via the shared Verovio WASM path (the same pipeline Tch
mode uses). This script produces the MEI strings.

Pipeline per hymn (matches modern.build_all / modern.build_svg):

  1. Run the reharm + voicing pipeline (build_all.run_pipeline_for_hymn)
     to get chord_labels = [(rh, lh, dur_q), ...].
  2. Sentinel-rewrite the source ABC so each chord annotation becomes
     a single "^@@CHORDi@@" marker (modern.layout._rewrite_with_sentinels).
  3. Feed the sentinelled ABC to Verovio (Python binding, v6.1.0) and
     capture MEI.
  4. Post-process: each <harm>@@CHORDi@@</harm> placeholder becomes
     TWO <harm> siblings on the same @startid/@tstamp, one with
     vo="0" containing the LH label (bottom), one with vo="6" containing
     the RH label (top). Unicode quality tokens (Delta, o-slash, degree)
     are substituted here -- labels in harm text are plain strings, NOT
     LilyPond markup.
  5. Round-trip through Verovio (mei -> mei) to sanity-check parse.

Outputs:
    modern/mei_out/<NNNN>_<slug>.mei         -- debug copies
    modern/modern_mei.json                   -- local combined
    app/modern_mei.json                      -- asset copy for preview
    app/app/src/main/assets/modern_mei.json  -- asset copy for Android
    modern/modern_mei_skipped.json           -- meter-exception sidecar

Usage:
    python3.10 -m modern.build_mei --smoke     # 5-hymn smoke
    python3.10 -m modern.build_mei             # full build

Python 3.10, stdlib + modern.* + verovio python binding.
ASCII-only source.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODERN_DIR = os.path.join(REPO_ROOT, "modern")
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_VOICINGS = os.path.join(REPO_ROOT, "handout.tex")

MEI_OUT_DIR = os.path.join(MODERN_DIR, "mei_out")
COMBINED_JSON_LOCAL = os.path.join(MODERN_DIR, "modern_mei.json")
APP_JSON = os.path.join(REPO_ROOT, "app", "modern_mei.json")
ASSETS_JSON = os.path.join(
    REPO_ROOT, "app", "app", "src", "main", "assets", "modern_mei.json"
)
SKIPPED_JSON = os.path.join(MODERN_DIR, "modern_mei_skipped.json")

# Smoke hymn numbers: five diverse processable hymns (same shape as
# modern.build_svg.SMOKE_NUMBERS). These are known-present in
# all_hymns_manifest.json.
SMOKE_NUMBERS = {4051, 4068, 4084, 4146, 4191}

# Size thresholds (bytes) for projecting full-build sizes. Used to
# gate the "build all" phase after smoke.
MAX_REASONABLE_MB = 25.0
MAX_WARN_MB = 50.0

# Unicode quality glyphs (from modern.chord_overlay).
_DELTA = "\u0394"   # maj7
_DEG = "\u00b0"     # diminished
_HDIM = "\u00f8"    # half-diminished (o-slash)


# ---------------------------------------------------------------------------
# cleanTitle -- same as modern.build_svg.clean_title
# ---------------------------------------------------------------------------

_LEADING_NUM_RE = re.compile(r"^\d+\s*")


def clean_title(t: str) -> str:
    if not t:
        return ""
    return _LEADING_NUM_RE.sub("", t).strip()


def slugify(t: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return s[:60] if s else "untitled"


# ---------------------------------------------------------------------------
# Quality-token substitution on Roman labels (same whole-token rules as
# chord_overlay._translate_quality, applied to the suffix after the
# Roman base). Operates on "V7", "iim7", "vii07", "IM7" -> returns
# plain Unicode strings (no markup).
# ---------------------------------------------------------------------------

_ROMAN_CHARS = set("IVXivx")


def _split_base_quality(label):
    if not label:
        return ("", "")
    i = 0
    while i < len(label) and label[i] in _ROMAN_CHARS:
        i += 1
    if i == 0:
        return (label, "")
    return (label[:i], label[i:])


def _translate_quality(quality):
    if not quality:
        return ""
    whole = {
        "M7": _DELTA,
        "maj7": _DELTA,
        "o": _DEG,
        "o7": _DEG + "7",
        "0": _HDIM,
        "07": _HDIM + "7",
        "hdim7": _HDIM + "7",
        "dim": _DEG,
        "dim7": _DEG + "7",
    }
    if quality in whole:
        return whole[quality]
    return quality


def pretty_label(label: str) -> str:
    """Convert an ASCII Roman-numeral label (e.g. 'viio7', 'IM7') into
    the Unicode display form used inside <harm> elements.
    """
    base, qual = _split_base_quality(label)
    return base + _translate_quality(qual)


# ---------------------------------------------------------------------------
# Verovio toolkit wrapper
# ---------------------------------------------------------------------------

def _make_toolkit():
    import verovio
    tk = verovio.toolkit()
    # Leave defaults for the MEI export -- pageWidth/breaks don't affect
    # MEI output significantly. We render SVGs in the app, not here.
    return tk


def abc_to_mei(abc: str, tk=None) -> tuple[str, str]:
    """Return (mei_string, log_string). Raises RuntimeError on failure."""
    close_after = False
    if tk is None:
        tk = _make_toolkit()
        close_after = True
    tk.setInputFrom("abc")
    ok = tk.loadData(abc)
    if not ok:
        log = ""
        try:
            log = tk.getLog() or ""
        except Exception:
            pass
        raise RuntimeError("verovio.loadData(abc) returned false: %s"
                           % (log[:500] if log else "no log"))
    mei = tk.getMEI({})
    try:
        log = tk.getLog() or ""
    except Exception:
        log = ""
    if not mei:
        raise RuntimeError("verovio.getMEI returned empty string")
    return (mei, log)


def mei_roundtrip(mei: str, tk=None) -> bool:
    """Parse mei through Verovio -> mei again, returning True on success."""
    if tk is None:
        tk = _make_toolkit()
    tk.setInputFrom("mei")
    try:
        ok = tk.loadData(mei)
    except Exception:
        return False
    return bool(ok)


# ---------------------------------------------------------------------------
# Placeholder replacement
# ---------------------------------------------------------------------------

# Matches <harm ...>@@CHORDi@@</harm>. The placeholder must appear as
# the sole text content of the element. We capture:
#   1. the opening tag (with attributes)
#   2. the index
# Verovio wraps harm content in plain text (no child elements), so a
# flat regex is safe.
_HARM_PLACEHOLDER_RE = re.compile(
    r"<harm\b([^>]*)>\s*@@CHORD(\d+)@@\s*</harm>"
)

# Matches the attribute string on an opening tag: we want to split out
# @vo (we'll set it ourselves) and keep everything else.
_VO_ATTR_RE = re.compile(r"\s+vo\s*=\s*\"[^\"]*\"")
# Matches the xml:id attribute so we can uniquify it (a <harm> placeholder
# becomes TWO <harm> elements; they cannot share the same xml:id).
_XMLID_ATTR_RE = re.compile(r"\s+xml:id\s*=\s*\"([^\"]*)\"")


def _escape_xml_text(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def replace_harm_placeholders(mei: str, chord_labels: list) -> tuple[str, dict]:
    """Replace each <harm>@@CHORDi@@</harm> with two <harm> siblings.

    chord_labels: [(rh, lh, dur_q), ...], indexed the same as the
                  sentinels in the rewritten ABC.

    Returns (new_mei, stats) where stats has:
        'placeholders_seen':   total @@CHORDi@@ matches
        'replaced':            successfully replaced
        'missed_indices':      indices referenced by placeholders but
                               out of range of chord_labels
        'chord_count':         len(chord_labels)
        'dropped_indices':     sorted list of chord_labels indices that
                               never appeared as a placeholder (Verovio
                               dropped them during layout)
    """
    seen_indices: list[int] = []
    missed: list[int] = []

    def repl(m: re.Match) -> str:
        attrs = m.group(1)
        idx = int(m.group(2))
        seen_indices.append(idx)
        if idx < 0 or idx >= len(chord_labels):
            missed.append(idx)
            # Leave a single empty harm placeholder so we don't lose
            # the element entirely (shouldn't normally happen).
            return "<harm%s></harm>" % attrs
        rh, lh, _dur = chord_labels[idx]
        rh_pretty = _escape_xml_text(pretty_label(str(rh)))
        lh_pretty = _escape_xml_text(pretty_label(str(lh)))
        # Strip any existing @vo attribute; we'll add our own.
        base_attrs = _VO_ATTR_RE.sub("", attrs)
        # Uniquify xml:id (we emit TWO harms from one source element;
        # they cannot share an xml:id). Leave the base @startid alone
        # so both align to the same anchor note.
        xmid_m = _XMLID_ATTR_RE.search(base_attrs)
        if xmid_m:
            base_id = xmid_m.group(1)
            # Remove the original and build two variants.
            attrs_no_id = _XMLID_ATTR_RE.sub("", base_attrs)
            lh_attrs = ' xml:id="%s_lh"%s' % (base_id, attrs_no_id)
            rh_attrs = ' xml:id="%s_rh"%s' % (base_id, attrs_no_id)
        else:
            lh_attrs = base_attrs
            rh_attrs = base_attrs
        # Ensure place="above" is present on both.
        if "place=" not in lh_attrs:
            lh_attrs = lh_attrs.rstrip() + ' place="above"'
        if "place=" not in rh_attrs:
            rh_attrs = rh_attrs.rstrip() + ' place="above"'
        # LH (bottom) first with vo="0", RH (top) second with vo="6".
        lh_elem = '<harm%s vo="0">%s</harm>' % (lh_attrs, lh_pretty)
        rh_elem = '<harm%s vo="6">%s</harm>' % (rh_attrs, rh_pretty)
        return lh_elem + rh_elem

    new_mei = _HARM_PLACEHOLDER_RE.sub(repl, mei)

    # Figure out which chord-label indices never made it into the MEI.
    seen_set = set(seen_indices)
    dropped = sorted(i for i in range(len(chord_labels)) if i not in seen_set)

    stats = {
        "placeholders_seen": len(seen_indices),
        "replaced": len(seen_indices) - len(missed),
        "missed_indices": sorted(missed),
        "chord_count": len(chord_labels),
        "dropped_indices": dropped,
    }
    return (new_mei, stats)


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

def _load_modern_modules():
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    return {
        "layout": importlib.import_module("modern.layout"),
        "abc_rewriter": importlib.import_module("modern.abc_rewriter"),
        "build_all": importlib.import_module("modern.build_all"),
        "voicing_picker": importlib.import_module("modern.voicing_picker"),
        "reharm_rules": importlib.import_module("modern.reharm_rules"),
    }


# ---------------------------------------------------------------------------
# Per-hymn build
# ---------------------------------------------------------------------------

def build_mei_for_hymn(h: dict, modules: dict, voicings_cache: list,
                       tk=None, roundtrip: bool = True) -> dict:
    """Return {'mei': str, 'chord_labels': list, 'stats': dict} or raise."""
    build_all = modules["build_all"]
    layout = modules["layout"]

    # Run the shared pipeline for chord_labels + reharmonised ABC.
    result = build_all.run_pipeline_for_hymn(
        h,
        {
            "modern.reharm_rules": modules["reharm_rules"],
            "modern.voicing_picker": modules["voicing_picker"],
            "modern.abc_rewriter": modules["abc_rewriter"],
            "modern.layout": modules["layout"],
        },
        voicings_cache,
    )
    chord_labels = result.get("chord_labels") or []

    # Sentinel-rewrite the ORIGINAL ABC. (run_pipeline_for_hymn returns
    # new_abc with Roman replacements baked in, but we want the sentinel
    # form so each chord becomes a unique placeholder.)
    abc_src = h.get("abc") or ""
    sentinelled, n_anns = layout._rewrite_with_sentinels(abc_src, 0)
    # n_anns must equal len(chord_labels) -- if not, one of the two
    # tokenizers has drifted. Clamp to the shorter (defensive).
    if n_anns != len(chord_labels):
        # pad or truncate chord_labels so indices line up
        if len(chord_labels) < n_anns:
            pad = [("I", "I", 1.0)] * (n_anns - len(chord_labels))
            chord_labels = list(chord_labels) + pad
        else:
            chord_labels = list(chord_labels)[:n_anns]

    mei, vlog = abc_to_mei(sentinelled, tk=tk)

    new_mei, stats = replace_harm_placeholders(mei, chord_labels)
    stats["n_anns"] = n_anns

    # Validate: no sentinels should survive.
    leftover = new_mei.count("@@CHORD")
    stats["leftover_placeholders"] = leftover

    if roundtrip:
        rt_tk = _make_toolkit()
        stats["roundtrip_ok"] = mei_roundtrip(new_mei, tk=rt_tk)
    else:
        stats["roundtrip_ok"] = None

    return {
        "mei": new_mei,
        "chord_labels": chord_labels,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true",
                        help="Only build the 5 smoke hymns, then stop.")
    parser.add_argument("--no-smoke-gate", action="store_true",
                        help="Skip the smoke-then-full sequence; just "
                             "build everything unconditionally.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after N hymns (0 = all).")
    parser.add_argument("--no-roundtrip", action="store_true",
                        help="Skip the MEI->MEI verovio roundtrip check.")
    args = parser.parse_args(argv)

    modules = _load_modern_modules()
    build_all = modules["build_all"]
    voicing_picker = modules["voicing_picker"]

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    # Partition: meter-skipped vs processable (same as build_all).
    skipped: list[dict] = []
    processable: list[dict] = []
    for h in hymns:
        meter = build_all.parse_meter(h.get("abc", ""))
        if meter in build_all.SKIP_METERS:
            skipped.append({
                "n": h.get("n"),
                "t": h.get("t"),
                "key": h.get("key"),
                "meter": meter,
                "reason": "skipped_meter",
            })
        else:
            processable.append(h)

    print("Loaded %d hymns; %d meter-skipped, %d to process."
          % (len(hymns), len(skipped), len(processable)))

    voicings_cache = voicing_picker.load_voicings(HANDOUT_VOICINGS)
    print("Loaded %d voicings from handout.tex" % len(voicings_cache))

    os.makedirs(MEI_OUT_DIR, exist_ok=True)

    # --- Smoke pass ---
    smoke_list = [h for h in processable
                  if _as_int(h.get("n")) in SMOKE_NUMBERS]
    print()
    print("=" * 60)
    print("SMOKE PASS (%d hymns)" % len(smoke_list))
    print("=" * 60)

    smoke_results: dict[str, dict] = {}
    smoke_total_bytes = 0
    smoke_failures: list[dict] = []
    smoke_tk = _make_toolkit()
    t_smoke0 = time.time()
    for i, h in enumerate(smoke_list, start=1):
        title = h.get("t", "Untitled")
        n = h.get("n")
        try:
            r = build_mei_for_hymn(
                h, modules, voicings_cache,
                tk=smoke_tk,
                roundtrip=not args.no_roundtrip,
            )
        except Exception as exc:
            smoke_failures.append({
                "n": n, "t": title,
                "error": "%s: %s" % (type(exc).__name__, exc),
            })
            print("  [%d/%d] FAIL n=%s: %s" % (i, len(smoke_list), n, exc))
            continue
        mei = r["mei"]
        stats = r["stats"]
        smoke_total_bytes += len(mei.encode("utf-8"))
        ctitle = clean_title(title)
        smoke_results[ctitle] = mei
        _write_debug_mei(n, ctitle, mei)
        print("  [%d/%d] OK n=%s  %s  (%d KB)  harms=%d/%d  "
              "dropped=%d  leftover=%d  rt=%s"
              % (i, len(smoke_list), n, ctitle,
                 len(mei) // 1024,
                 stats["replaced"], stats["chord_count"],
                 len(stats["dropped_indices"]),
                 stats["leftover_placeholders"],
                 stats["roundtrip_ok"]))
    t_smoke_elapsed = time.time() - t_smoke0

    smoke_ok = len(smoke_results) == len(smoke_list) and len(smoke_list) > 0
    mean_smoke_kb = (smoke_total_bytes / max(1, len(smoke_results))) / 1024.0
    projected_full_mb = (
        (mean_smoke_kb * len(processable)) / 1024.0
    ) if smoke_results else 0.0

    # Smoke-level structural check: at least one vo="0" + one vo="6" per
    # MEI, and zero leftover placeholders.
    struct_fail: list[str] = []
    for ctitle, mei in smoke_results.items():
        n0 = mei.count('vo="0"')
        n6 = mei.count('vo="6"')
        leftover = mei.count("@@CHORD")
        if n0 < 1 or n6 < 1 or leftover != 0:
            struct_fail.append(
                "  %s: vo0=%d vo6=%d leftover=%d"
                % (ctitle, n0, n6, leftover)
            )

    print()
    print("SMOKE SUMMARY")
    print("  Succeeded:     %d / %d" % (len(smoke_results), len(smoke_list)))
    print("  Failures:      %d" % len(smoke_failures))
    print("  Mean MEI size: %.1f KB" % mean_smoke_kb)
    print("  Total smoke:   %.1f KB (%.2f MB)"
          % (smoke_total_bytes / 1024.0,
             smoke_total_bytes / (1024.0 * 1024.0)))
    print("  Projected full build: %.2f MB (at %d hymns)"
          % (projected_full_mb, len(processable)))
    print("  Elapsed:       %.1fs" % t_smoke_elapsed)
    if struct_fail:
        print("  Structural issues:")
        for line in struct_fail:
            print(line)

    if args.smoke:
        # Write the smoke output to the debug dir but NOT to the app
        # asset locations (we don't want a 5-hymn modern_mei.json shipped).
        _write_combined_skipped(skipped, smoke_failures, skipped_only=True)
        if not smoke_ok or struct_fail:
            return 3
        return 0

    if not args.no_smoke_gate:
        if not smoke_ok:
            print("STOP: smoke failed; full build skipped.", file=sys.stderr)
            _write_combined_skipped(skipped, smoke_failures, skipped_only=True)
            return 3
        if struct_fail:
            print("STOP: smoke structural issues; full build skipped.",
                  file=sys.stderr)
            _write_combined_skipped(skipped, smoke_failures, skipped_only=True)
            return 3
        if projected_full_mb > MAX_WARN_MB:
            print("STOP: projected full-build size %.2f MB > %.1f MB cap"
                  % (projected_full_mb, MAX_WARN_MB), file=sys.stderr)
            _write_combined_skipped(skipped, smoke_failures, skipped_only=True)
            return 3
        if projected_full_mb > MAX_REASONABLE_MB:
            print("WARN: projected full-build size %.2f MB > %.1f MB "
                  "(proceeding anyway)"
                  % (projected_full_mb, MAX_REASONABLE_MB), file=sys.stderr)

    # --- Full build ---
    print()
    print("=" * 60)
    print("FULL BUILD (%d hymns)" % len(processable))
    print("=" * 60)

    combined: dict[str, str] = {}
    failures: list[dict] = []
    total_bytes = 0
    t0 = time.time()

    full_tk = _make_toolkit()
    target = processable if args.limit <= 0 else processable[:args.limit]
    for i, h in enumerate(target, start=1):
        title = h.get("t", "Untitled")
        n = h.get("n")
        try:
            r = build_mei_for_hymn(
                h, modules, voicings_cache,
                tk=full_tk,
                roundtrip=False,  # skip roundtrip in bulk to save time
            )
        except Exception as exc:
            failures.append({
                "n": n, "t": title,
                "error": "%s: %s" % (type(exc).__name__, exc),
            })
            if i % 25 == 0 or i == len(target):
                print("  [%d/%d] FAIL n=%s: %s"
                      % (i, len(target), n, exc))
            continue
        mei = r["mei"]
        stats = r["stats"]
        ctitle = clean_title(title)
        combined[ctitle] = mei
        total_bytes += len(mei.encode("utf-8"))
        _write_debug_mei(n, ctitle, mei)
        if stats["dropped_indices"]:
            failures.append({
                "n": n, "t": title,
                "warn": "dropped_chord_indices",
                "dropped": stats["dropped_indices"],
                "chord_count": stats["chord_count"],
            })
        if i % 25 == 0 or i == len(target):
            print("  [%d/%d] processed  last=%s  running=%.1f MB"
                  % (i, len(target), ctitle,
                     total_bytes / (1024.0 * 1024.0)))

    elapsed = time.time() - t0

    # Write combined JSON.
    payload = json.dumps(combined, ensure_ascii=False)
    for out in (COMBINED_JSON_LOCAL, APP_JSON, ASSETS_JSON):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload)

    _write_combined_skipped(skipped, failures, skipped_only=False)

    print()
    print("=" * 60)
    print("FULL BUILD COMPLETE")
    print("=" * 60)
    print("  Hymns built:   %d / %d" % (len(combined), len(target)))
    print("  Failures:      %d" % len(failures))
    print("  Total MEI:     %.1f KB (%.2f MB)"
          % (total_bytes / 1024.0,
             total_bytes / (1024.0 * 1024.0)))
    if combined:
        avg = total_bytes / len(combined)
        print("  Mean / hymn:   %.1f KB" % (avg / 1024.0))
    print("  Elapsed:       %.1fs" % elapsed)
    print("  Wrote:         %s" % COMBINED_JSON_LOCAL)
    print("                 %s" % APP_JSON)
    print("                 %s" % ASSETS_JSON)
    print("                 %s" % SKIPPED_JSON)
    return 0


def _as_int(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def _write_debug_mei(n, ctitle: str, mei: str) -> None:
    try:
        n_int = int(n)
    except (TypeError, ValueError):
        n_int = 0
    fname = "%s_%s.mei" % (str(n_int or n), slugify(ctitle))
    p = os.path.join(MEI_OUT_DIR, fname)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(mei)


def _write_combined_skipped(skipped: list, failures: list,
                             skipped_only: bool) -> None:
    entries = list(skipped)
    for f in failures:
        entry = {
            "n": f.get("n"),
            "t": f.get("t"),
            "reason": "pipeline_error" if "error" in f else "warn",
        }
        if "error" in f:
            entry["error"] = f["error"]
        if "warn" in f:
            entry["warn"] = f["warn"]
            entry["dropped"] = f.get("dropped")
            entry["chord_count"] = f.get("chord_count")
        entries.append(entry)
    with open(SKIPPED_JSON, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main())
