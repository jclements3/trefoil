#!/usr/bin/env python3.10
"""Build the complete modern-reharm PDF for all lever-harp hymns.

Scales the verify_samples.py pipeline from 10 diverse samples to every
hymn in app/lead_sheets.json that has a supported meter. Skipped meters
(M:none, 3/2, 8/4) are logged to a sidecar JSON.

Outputs:
    modern/all_hymns.ly                -- combined LilyPond source
    modern/all_hymns.pdf               -- rendered PDF (via build_pdf.sh)
    modern/all_hymns_manifest.json     -- per-hymn manifest
    modern/all_hymns_skipped.json      -- meter-skipped sidecar

Run:
    python3.10 -m modern.build_all

ASCII-only, standard library + modern.* modules only.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_VOICINGS = os.path.join(REPO_ROOT, "handout.tex")
OUT_DIR = os.path.join(REPO_ROOT, "modern")
PER_HYMN_DIR = os.path.join(OUT_DIR, "per_hymn")
COMBINED_LY = os.path.join(OUT_DIR, "all_hymns.ly")
COMBINED_PDF = os.path.join(OUT_DIR, "all_hymns.pdf")
MANIFEST_PATH = os.path.join(OUT_DIR, "all_hymns_manifest.json")
SKIPPED_PATH = os.path.join(OUT_DIR, "all_hymns_skipped.json")
BUILD_PDF_SCRIPT = os.path.join(OUT_DIR, "build_pdf.sh")

SKIP_METERS = {"none", "3/2", "8/4"}

REQUIRED_MODULES = [
    "modern.reharm_rules",
    "modern.voicing_picker",
    "modern.abc_rewriter",
    "modern.layout",
]


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

def load_modules() -> dict[str, Any]:
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    for name in REQUIRED_MODULES:
        try:
            loaded[name] = importlib.import_module(name)
        except Exception as exc:
            missing.append(f"{name} ({type(exc).__name__}: {exc})")
    if missing:
        print("ERROR: required modern.* modules missing:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(2)
    return loaded


# ---------------------------------------------------------------------------
# ABC utilities (subset of verify_samples.py, trimmed for build)
# ---------------------------------------------------------------------------

METER_RE = re.compile(r"(?m)^M:\s*([^\n]+)")
LEN_RE = re.compile(r"(?m)^L:\s*(\d+)\s*/\s*(\d+)")
NOTE_RE = re.compile(r"(\^|=|_)?([A-Ga-gz])([\',]*)(\d+)?(/\d*)?")
TEMPO_RE = re.compile(r"(?m)^Q:\s*(.+)$")


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else "?"


def parse_meter_fraction(abc: str) -> tuple[int, int]:
    meter = parse_meter(abc)
    if meter in ("C", "c"):
        return (4, 4)
    if meter in ("C|", "c|"):
        return (2, 2)
    m = re.match(r"(\d+)\s*/\s*(\d+)", meter)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (4, 4)


def parse_default_length(abc: str) -> float:
    m = LEN_RE.search(abc)
    if not m:
        return 1.0 / 8.0
    return int(m.group(1)) / int(m.group(2))


def parse_tempo(abc: str) -> str:
    m = TEMPO_RE.search(abc)
    return m.group(1).strip() if m else ""


def note_duration(token: str, default_l: float) -> float:
    m = NOTE_RE.match(token)
    if not m:
        return 0.0
    num_str = m.group(4)
    div_str = m.group(5)
    mult = float(num_str) if num_str else 1.0
    if div_str:
        if div_str == "/":
            div = 2.0
        else:
            div = float(div_str[1:]) if len(div_str) > 1 else 2.0
        mult = mult / div
    return default_l * mult


def iter_chord_events(abc: str) -> list[tuple[float, str]]:
    default_l = parse_default_length(abc)
    lines = abc.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("K:"):
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:])
    events: list[tuple[float, str]] = []
    pos_whole = 0.0
    i = 0
    pending_chord = None
    while i < len(body):
        ch = body[i]
        if ch == '"':
            j = body.find('"', i + 1)
            if j < 0:
                break
            inside = body[i + 1:j]
            if inside.startswith("^"):
                pending_chord = inside[1:]
            i = j + 1
            continue
        m = NOTE_RE.match(body, i)
        if m and body[i] not in ("|", "[", "]"):
            tok = m.group(0)
            dur_whole = note_duration(tok, default_l)
            if pending_chord is not None:
                beat_q = pos_whole * 4.0
                events.append((beat_q, pending_chord))
                pending_chord = None
            pos_whole += dur_whole
            i = m.end()
            continue
        i += 1
    return events


# ---------------------------------------------------------------------------
# Pipeline -- runs on one hymn, produces {abc, chord_labels, voicings, subs}
# ---------------------------------------------------------------------------

def run_pipeline_for_hymn(hymn: dict, modules: dict[str, Any],
                          voicings_cache: list) -> dict:
    reharm = modules["modern.reharm_rules"]
    voicing_pkg = modules["modern.voicing_picker"]
    rewriter = modules["modern.abc_rewriter"]

    abc = hymn["abc"]
    key = hymn.get("key", "C")
    meter = parse_meter_fraction(abc)
    num, den = meter
    beats_per_bar = num * (4.0 / den)

    parse_chord_name = getattr(reharm, "parse_chord_name")
    ChordEvent = getattr(reharm, "ChordEvent")
    iter_anns = getattr(rewriter, "iter_chord_annotations")
    rewrite_abc = getattr(rewriter, "rewrite_abc")
    labels_from_voicing = getattr(rewriter, "labels_from_voicing")
    pick_sequence = getattr(voicing_pkg, "pick_sequence")

    raw_anns = list(iter_anns(abc))
    beat_events = iter_chord_events(abc)
    beats_by_idx: list[float | None] = []
    bi = 0
    for (_s, _e, name) in raw_anns:
        b = None
        while bi < len(beat_events):
            bb, bn = beat_events[bi]
            bi += 1
            if bn == name:
                b = bb
                break
        beats_by_idx.append(b)

    events: list = []
    parse_idx_map: list[int] = []
    fallback_names = [name for (_s, _e, name) in raw_anns]
    for idx, (_s, _e, name) in enumerate(raw_anns):
        try:
            roman = parse_chord_name(name, key)
        except TypeError:
            roman = parse_chord_name(name)
        except Exception:
            roman = None
        if roman is None:
            continue
        beat = beats_by_idx[idx] if beats_by_idx[idx] is not None else 0.0
        next_beat = None
        for j in range(idx + 1, len(raw_anns)):
            if beats_by_idx[j] is not None:
                next_beat = beats_by_idx[j]
                break
        if next_beat is None:
            next_beat = beat + beats_per_bar
        dur = max(0.25, next_beat - beat)
        bar_pos = beat % beats_per_bar
        is_strong = (abs(bar_pos) < 1e-6) or (
            beats_per_bar >= 4 and abs(bar_pos - 2.0) < 1e-6
        )
        is_cadence = (idx >= len(raw_anns) - 2)
        is_destination = is_strong and (
            idx == 0 or fallback_names[idx - 1] != name
        )
        try:
            ev = ChordEvent(
                beat=beat, duration=dur, chord=roman,
                is_strong_beat=is_strong, is_cadence=is_cadence,
                is_destination=is_destination,
            )
        except TypeError:
            ev = ChordEvent(
                beat=beat, chord=roman,
                is_strong_beat=is_strong, is_cadence=is_cadence,
                is_destination=is_destination,
            )
        events.append(ev)
        parse_idx_map.append(idx)

    # Reharmonize parseable events.
    try:
        new_events = reharm.reharmonize(events, key)
    except Exception as exc:
        raise RuntimeError(f"reharmonize() failed: {exc}")

    if len(new_events) != len(events):
        if len(new_events) < len(events):
            new_events = list(new_events) + events[len(new_events):]
        else:
            new_events = list(new_events)[:len(events)]

    # Use pick_sequence for per-hymn diversity.
    chord_seq = [getattr(ev, "chord", None) for ev in new_events]
    chord_seq_clean = [c for c in chord_seq if c is not None]
    if chord_seq_clean:
        try:
            picked = pick_sequence(chord_seq_clean, voicings_cache)
        except Exception:
            picked = []
    else:
        picked = []
    # Re-map picked back into voicing_seq aligned with new_events.
    voicing_seq: list = []
    pi = 0
    for c in chord_seq:
        if c is None:
            voicing_seq.append(None)
        else:
            voicing_seq.append(picked[pi] if pi < len(picked) else None)
            pi += 1

    labels_per_event: list[tuple[str, str]] = []
    for v in voicing_seq:
        if v is None:
            labels_per_event.append(("I", "I"))
            continue
        try:
            rh_deg, rh_qual = v.rh
            lh_deg, lh_qual = v.lh
            rh, lh = labels_from_voicing(rh_deg, rh_qual, lh_deg, lh_qual)
        except Exception:
            rh, lh = "I", "I"
        labels_per_event.append((rh, lh))

    # Build replacements for rewrite_abc (1 per original annotation).
    # The rewriter's label validator forbids '#' and 'b', so fallback
    # names for unparseable originals must drop those too.
    def _safe_fallback(name: str) -> str:
        s = re.sub(r"[^A-Za-z0-9/+\- ]", "", name)
        return s or "I"

    replacements: list[tuple[str, str]] = []
    ev_iter = iter(zip(parse_idx_map, labels_per_event, new_events))
    next_pair = next(ev_iter, None)
    for idx, (_s, _e, name) in enumerate(raw_anns):
        if next_pair is not None and next_pair[0] == idx:
            _i, (rh, lh), _ev = next_pair
            replacements.append((rh, lh))
            next_pair = next(ev_iter, None)
        else:
            safe = _safe_fallback(name)
            replacements.append((safe, safe))

    new_abc = rewrite_abc(abc, replacements)

    # chord_labels for layout: one tuple per ORIGINAL annotation.
    chord_labels: list[tuple[str, str, float]] = []
    ev_idx2 = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        if ev_idx2 < len(parse_idx_map) and parse_idx_map[ev_idx2] == idx:
            rh, lh = labels_per_event[ev_idx2]
            ev = new_events[ev_idx2]
            dur_q = float(getattr(ev, "duration", 1.0) or 1.0)
            chord_labels.append((rh, lh, dur_q))
            ev_idx2 += 1
        else:
            safe = _safe_fallback(name)
            chord_labels.append((safe, safe, 1.0))

    subs = 0
    ei = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        if ei < len(parse_idx_map) and parse_idx_map[ei] == idx:
            # compare by display roman/qual vs original name (best-effort)
            orig_chord = events[ei].chord if hasattr(events[ei], "chord") else None
            new_chord = getattr(new_events[ei], "chord", None)
            if orig_chord != new_chord:
                subs += 1
            ei += 1

    return {
        "new_abc": new_abc,
        "chord_labels": chord_labels,
        "labels": labels_per_event,
        "voicings": [v for v in voicing_seq if v is not None],
        "subs": subs,
        "meter_str": parse_meter(abc),
        "chord_count": len(raw_anns),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    modules = load_modules()

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    # Sort alphabetically by title.
    hymns.sort(key=lambda h: (h.get("t", "") or "").lower())

    # Partition into processable vs meter-skipped.
    skipped: list[dict] = []
    processable: list[dict] = []
    for h in hymns:
        meter = parse_meter(h.get("abc", ""))
        if meter in SKIP_METERS:
            skipped.append({
                "n": h.get("n"),
                "t": h.get("t"),
                "key": h.get("key"),
                "meter": meter,
                "reason": "skipped_meter",
            })
        else:
            processable.append(h)

    print(f"Loaded {len(hymns)} hymns; "
          f"{len(skipped)} meter-skipped, "
          f"{len(processable)} to process.")

    # Load voicings once.
    voicing_pkg = modules["modern.voicing_picker"]
    voicings_cache = voicing_pkg.load_voicings(HANDOUT_VOICINGS)
    print(f"Loaded {len(voicings_cache)} voicings from handout.tex")

    os.makedirs(PER_HYMN_DIR, exist_ok=True)

    manifest: list[dict] = []
    combined_input: list[dict] = []
    crashes: list[dict] = []
    voicing_counter: Counter = Counter()

    total = len(processable)
    for i, h in enumerate(processable, start=1):
        try:
            result = run_pipeline_for_hymn(h, modules, voicings_cache)
        except Exception as exc:
            crashes.append({
                "n": h.get("n"),
                "t": h.get("t"),
                "error": f"{type(exc).__name__}: {exc}",
            })
            if i % 50 == 0 or i == total:
                print(f"  {i}/{total} processed (last crash: "
                      f"{h.get('n')} -- {type(exc).__name__})")
            continue

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
            "meter": result["meter_str"],
            "chord_labels": result["chord_labels"],
        })

        # Track voicings used for top-5 report.
        for v in result["voicings"]:
            try:
                sig = (v.rh_fig, v.lh_fig)
            except AttributeError:
                sig = (str(v), "")
            voicing_counter[sig] += 1

        tempo = parse_tempo(h.get("abc", ""))
        manifest.append({
            "n": h.get("n"),
            "title": h.get("t"),
            "key": h.get("key"),
            "tempo": tempo,
            "meter": result["meter_str"],
            "chord_count": result["chord_count"],
            "substitutions": result["subs"],
        })

        if i % 50 == 0 or i == total:
            print(f"  {i}/{total} processed...")

    print(f"Pipeline done. {len(combined_input)} hymns ready, "
          f"{len(crashes)} crashed.")

    # Build combined LilyPond.
    layout = modules["modern.layout"]
    ly_src = layout.build_combined_ly(combined_input, per_page=3)
    with open(COMBINED_LY, "w", encoding="utf-8") as fh:
        fh.write(ly_src)
    print(f"Wrote {COMBINED_LY} ({len(ly_src)//1024} KB)")

    # Write manifest.
    # Pages filled in after the PDF is produced.
    with open(MANIFEST_PATH, "w", encoding="ascii", errors="replace") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=True)
    print(f"Wrote {MANIFEST_PATH}")

    # Write skipped sidecar.
    skipped_full = list(skipped) + [
        {**c, "reason": "pipeline_error"} for c in crashes
    ]
    with open(SKIPPED_PATH, "w", encoding="ascii", errors="replace") as fh:
        json.dump(skipped_full, fh, indent=2, ensure_ascii=True)
    print(f"Wrote {SKIPPED_PATH} ({len(skipped_full)} entries)")

    # Render PDF.
    print("Invoking lilypond via build_pdf.sh ...")
    t_render = time.time()
    try:
        subprocess.run(
            [BUILD_PDF_SCRIPT, COMBINED_LY, COMBINED_PDF],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: build_pdf.sh failed: {exc}", file=sys.stderr)
        return 4
    except FileNotFoundError:
        print(f"ERROR: {BUILD_PDF_SCRIPT} not found", file=sys.stderr)
        return 4
    render_sec = time.time() - t_render

    # Page count.
    pages = None
    try:
        out = subprocess.check_output(["pdfinfo", COMBINED_PDF],
                                      text=True, errors="replace")
        for line in out.splitlines():
            if line.startswith("Pages:"):
                pages = int(line.split(":")[1].strip())
                break
    except Exception:
        pass

    top5 = voicing_counter.most_common(5)

    total_sec = time.time() - t0

    print()
    print("=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"  Hymns processed:   {len(combined_input)} / {total}")
    print(f"  Meter-skipped:     {len(skipped)}")
    print(f"  Pipeline crashes:  {len(crashes)}")
    print(f"  Pages:             {pages}")
    print(f"  PDF:               {COMBINED_PDF}")
    print(f"  Render time:       {render_sec:.1f}s")
    print(f"  Total time:        {total_sec:.1f}s")
    print(f"  Top-5 voicings:")
    for sig, cnt in top5:
        print(f"    {sig[0]:>6} / {sig[1]:<6}  {cnt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
