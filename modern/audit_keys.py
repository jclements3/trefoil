#!/usr/bin/env python3.10
"""Audit OpenHymnal lead sheets for lever-harp pipeline readiness.

For each hymn in app/lead_sheets.json, check:
  1. Key is one of the 8 lever-harp keys (Eb, Bb, F, C, G, D, A, E).
  2. All melody notes are within MIDI 36 (C2) .. 91 (G6).
  3. Meter is "simple" (2/4, 3/4, 4/4, 6/8, 9/8, 12/8, 2/2, 3/8, 6/4, C, C|).
  4. At least one chord annotation ("^...").
  5. Q: tempo is present and parseable as BPM.

Writes a markdown report to modern/key_range_audit.md and prints a one-line
summary to stdout. ASCII only.

Run: python3.10 -m modern.audit_keys
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
REPORT_PATH = os.path.join(REPO_ROOT, "modern", "key_range_audit.md")

LEVER_HARP_KEYS = ["Eb", "Bb", "F", "C", "G", "D", "A", "E"]
MIDI_MIN = 36  # C2
MIDI_MAX = 91  # G6

# ABC note-name -> semitone offset within an octave. "C" = 0 -> C4 when
# octave-number is 4 in our scheme.
PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Key signature -> {pitch-letter: accidental-in-semitones}.
# Only the 8 lever-harp keys (plus Ab, Db as fallbacks we might see).
KEY_SIG = {
    "C":  {},
    "G":  {"F": 1},
    "D":  {"F": 1, "C": 1},
    "A":  {"F": 1, "C": 1, "G": 1},
    "E":  {"F": 1, "C": 1, "G": 1, "D": 1},
    "B":  {"F": 1, "C": 1, "G": 1, "D": 1, "A": 1},
    "F":  {"B": -1},
    "Bb": {"B": -1, "E": -1},
    "Eb": {"B": -1, "E": -1, "A": -1},
    "Ab": {"B": -1, "E": -1, "A": -1, "D": -1},
    "Db": {"B": -1, "E": -1, "A": -1, "D": -1, "G": -1},
    # minor-key spellings we might see
    "Am": {},
    "Em": {"F": 1},
    "Bm": {"F": 1, "C": 1},
    "F#m": {"F": 1, "C": 1, "G": 1},
    "Dm": {"B": -1},
    "Gm": {"B": -1, "E": -1},
    "Cm": {"B": -1, "E": -1, "A": -1},
}

SIMPLE_METERS = {"2/4", "3/4", "4/4", "6/8", "9/8", "12/8",
                 "2/2", "3/8", "6/4", "C", "C|"}

KEY_RE = re.compile(r"(?m)^K:\s*([^\s%]+)")
METER_RE = re.compile(r"(?m)^M:\s*([^\s%]+)")
TEMPO_RE = re.compile(r"(?m)^Q:\s*([^\n]+)")
CHORD_RE = re.compile(r'"\^([^"]+)"')

# Accidental? note-letter (A-G, a-g), octave marks (' or ,), length (n/d).
NOTE_RE = re.compile(
    r'(?P<acc>\^\^|__|\^|=|_)?'
    r'(?P<letter>[A-Ga-gz])'
    r'(?P<oct>[\',]*)'
    r'(?P<num>\d+)?'
    r'(?P<den>/\d*)?'
)


def parse_tempo_bpm(abc: str) -> float | None:
    """Extract tempo in BPM (quarter-note beats per minute) from Q: line.

    Handles:
        Q: 1/4=120
        Q: 100
        Q: "Andante" 1/4=96
        Q: 1/8=240
        Q: C=120
    """
    m = TEMPO_RE.search(abc)
    if not m:
        return None
    q = m.group(1).strip()
    # Try unit=bpm form.
    mm = re.search(r'(\d+)\s*/\s*(\d+)\s*=\s*(\d+(?:\.\d+)?)', q)
    if mm:
        num = int(mm.group(1))
        den = int(mm.group(2))
        bpm = float(mm.group(3))
        # Convert so result is in quarter-note BPM.
        return bpm * (num / den) / (1 / 4)
    # Plain number.
    mm = re.search(r'(?<![\d/])(\d+(?:\.\d+)?)\s*$', q)
    if mm:
        return float(mm.group(1))
    return None


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else ""


def parse_key_header(abc: str) -> str:
    m = KEY_RE.search(abc)
    return m.group(1).strip() if m else ""


def count_annotations(abc: str) -> int:
    return len(CHORD_RE.findall(abc))


def abc_body(abc: str) -> str:
    lines = abc.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("K:"):
            return "\n".join(lines[i + 1:])
    return abc


def note_to_midi(letter: str, oct_marks: str, acc: str | None,
                 key_sig: dict[str, int],
                 measure_accidentals: dict[str, int]) -> int:
    """Convert one ABC note token to a MIDI number.

    Uppercase letter -> octave 4 (so C = C4 = 60). Lowercase -> octave 5.
    Each "'" adds an octave, each "," subtracts one.

    Accidentals: explicit accidental from the token, else per-measure
    accidental carry-over, else key-signature accidental.
    """
    if letter.isupper():
        base_oct = 4
    else:
        base_oct = 5
    up = oct_marks.count("'")
    down = oct_marks.count(",")
    octave = base_oct + up - down
    pc_letter = letter.upper()
    pc = PITCH_CLASS[pc_letter]

    if acc == "^":
        alter = 1
        measure_accidentals[pc_letter] = 1
    elif acc == "^^":
        alter = 2
        measure_accidentals[pc_letter] = 2
    elif acc == "_":
        alter = -1
        measure_accidentals[pc_letter] = -1
    elif acc == "__":
        alter = -2
        measure_accidentals[pc_letter] = -2
    elif acc == "=":
        alter = 0
        measure_accidentals[pc_letter] = 0
    else:
        if pc_letter in measure_accidentals:
            alter = measure_accidentals[pc_letter]
        else:
            alter = key_sig.get(pc_letter, 0)

    return (octave + 1) * 12 + pc + alter


def extract_midi_range(abc: str, key: str) -> tuple[int | None, int | None,
                                                   list[tuple[int, str]]]:
    """Walk the body, return (min_midi, max_midi, [(midi, token)...]) for
    notes that fall outside the harp range (for the report)."""
    key_sig = KEY_SIG.get(key, {})
    body = abc_body(abc)

    min_m: int | None = None
    max_m: int | None = None
    out_of_range: list[tuple[int, str]] = []

    measure_accidentals: dict[str, int] = {}

    i = 0
    while i < len(body):
        ch = body[i]
        if ch == '"':
            # Skip the chord/decoration string entirely.
            j = body.find('"', i + 1)
            if j < 0:
                break
            i = j + 1
            continue
        if ch == '|':
            # Barline -> reset measure-local accidentals.
            measure_accidentals = {}
            i += 1
            continue
        if ch == '%':
            # Line comment -> skip to end of line.
            j = body.find('\n', i)
            if j < 0:
                break
            i = j + 1
            continue
        m = NOTE_RE.match(body, i)
        if m and m.group("letter") != "z":
            letter = m.group("letter")
            oct_marks = m.group("oct") or ""
            acc = m.group("acc")
            try:
                midi = note_to_midi(letter, oct_marks, acc,
                                    key_sig, measure_accidentals)
            except KeyError:
                i = m.end()
                continue
            if min_m is None or midi < min_m:
                min_m = midi
            if max_m is None or midi > max_m:
                max_m = midi
            if midi < MIDI_MIN or midi > MIDI_MAX:
                out_of_range.append((midi, m.group(0)))
            i = m.end()
            continue
        if m and m.group("letter") == "z":
            # Rest -> no pitch.
            i = m.end()
            continue
        i += 1

    return min_m, max_m, out_of_range


def midi_to_name(midi: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def audit_hymn(h: dict) -> dict:
    abc = h.get("abc", "")
    key = (h.get("key") or "").strip()
    n = h.get("n", "?")
    title = h.get("t", "?")
    meter = parse_meter(abc)
    header_key = parse_key_header(abc)
    # Prefer the K: header when present; fall back to the JSON 'key'.
    effective_key = header_key or key
    ann_count = count_annotations(abc)
    tempo_bpm = parse_tempo_bpm(abc)

    failures: list[str] = []
    if effective_key not in LEVER_HARP_KEYS:
        failures.append(f"key={effective_key!r} not in lever-harp set")
    if meter not in SIMPLE_METERS:
        failures.append(f"meter={meter!r} not simple")
    if ann_count == 0:
        failures.append("zero chord annotations")
    if tempo_bpm is None:
        failures.append("tempo missing/unparseable")

    min_m, max_m, oor = extract_midi_range(abc, effective_key)
    if oor:
        failures.append(
            f"{len(oor)} notes out of range "
            f"(first: {midi_to_name(oor[0][0])}={oor[0][0]})"
        )

    return {
        "n": n,
        "t": title,
        "json_key": key,
        "header_key": header_key,
        "effective_key": effective_key,
        "meter": meter,
        "ann_count": ann_count,
        "tempo_bpm": tempo_bpm,
        "min_midi": min_m,
        "max_midi": max_m,
        "out_of_range": oor,
        "failures": failures,
    }


def histogram_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n < 5:
        return "1-4"
    if n < 10:
        return "5-9"
    if n < 20:
        return "10-19"
    if n < 40:
        return "20-39"
    if n < 80:
        return "40-79"
    return "80+"


def main() -> int:
    if not os.path.exists(LEAD_SHEETS_PATH):
        print(f"ERROR: {LEAD_SHEETS_PATH} not found", file=sys.stderr)
        return 1

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    reports = [audit_hymn(h) for h in hymns]
    total = len(reports)
    ready = [r for r in reports if not r["failures"]]
    exceptions = [r for r in reports if r["failures"]]

    # Key distribution (effective_key).
    key_counts = Counter(r["effective_key"] for r in reports)
    # Meter distribution.
    meter_counts = Counter(r["meter"] or "(none)" for r in reports)
    # Annotation histogram.
    ann_hist = Counter(histogram_bucket(r["ann_count"]) for r in reports)
    # Tempo distribution.
    tempos = [r["tempo_bpm"] for r in reports if r["tempo_bpm"] is not None]
    # Range.
    mins = [r["min_midi"] for r in reports if r["min_midi"] is not None]
    maxs = [r["max_midi"] for r in reports if r["max_midi"] is not None]

    # Categorise failures.
    fail_key = [r for r in exceptions
                if any("key=" in f for f in r["failures"])]
    fail_meter = [r for r in exceptions
                  if any("meter=" in f for f in r["failures"])]
    fail_ann = [r for r in exceptions
                if any("chord annotations" in f for f in r["failures"])]
    fail_tempo = [r for r in exceptions
                  if any("tempo" in f for f in r["failures"])]
    fail_range = [r for r in exceptions
                  if any("out of range" in f for f in r["failures"])]

    # --- Write report -----------------------------------------------------
    lines: list[str] = []
    lines.append("# Key / Range Audit -- OpenHymnal Lead Sheets")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total hymns: {total}")
    lines.append(f"- Pipeline-ready (pass all 5 checks): {len(ready)}")
    lines.append(f"- Exceptions: {len(exceptions)}")
    lines.append("")
    lines.append(f"{total} hymns audited: {len(ready)} pipeline-ready, "
                 f"{len(exceptions)} exceptions.")
    lines.append("")

    # Key distribution.
    lines.append("## Key distribution")
    lines.append("")
    lines.append("| key | count |")
    lines.append("| :-- | ----: |")
    for k in LEVER_HARP_KEYS:
        lines.append(f"| {k} | {key_counts.get(k, 0)} |")
    other_keys = [k for k in key_counts if k not in LEVER_HARP_KEYS]
    for k in sorted(other_keys):
        lines.append(f"| {k} (OTHER) | {key_counts[k]} |")
    lines.append("")

    # Range distribution.
    lines.append("## Range distribution")
    lines.append("")
    if mins and maxs:
        gmin = min(mins)
        gmax = max(maxs)
        lines.append(f"- Global min MIDI: {gmin} ({midi_to_name(gmin)})")
        lines.append(f"- Global max MIDI: {gmax} ({midi_to_name(gmax)})")
        lines.append(f"- Harp range (enforced): {MIDI_MIN} "
                     f"({midi_to_name(MIDI_MIN)}) .. "
                     f"{MIDI_MAX} ({midi_to_name(MIDI_MAX)})")
    else:
        lines.append("- (no pitch data extracted)")
    lines.append("")
    if fail_range:
        lines.append("### Hymns with out-of-range notes")
        lines.append("")
        lines.append("| n | title | min | max | n_bad | first_bad |")
        lines.append("| :-- | :-- | ---: | ---: | ---: | :-- |")
        for r in fail_range:
            mn = r["min_midi"]
            mx = r["max_midi"]
            mn_s = f"{mn} ({midi_to_name(mn)})" if mn is not None else "-"
            mx_s = f"{mx} ({midi_to_name(mx)})" if mx is not None else "-"
            fb = r["out_of_range"][0]
            fb_s = f"{fb[1]} -> {fb[0]} ({midi_to_name(fb[0])})"
            lines.append(
                f"| {r['n']} | {r['t'][:40]} | {mn_s} | {mx_s} | "
                f"{len(r['out_of_range'])} | {fb_s} |"
            )
        lines.append("")

    # Meter distribution.
    lines.append("## Meter distribution")
    lines.append("")
    lines.append("| meter | count |")
    lines.append("| :-- | ----: |")
    for meter, cnt in sorted(meter_counts.items(),
                             key=lambda kv: (-kv[1], kv[0])):
        tag = "" if meter in SIMPLE_METERS else " (EXOTIC)"
        lines.append(f"| {meter}{tag} | {cnt} |")
    lines.append("")

    # Annotation distribution.
    lines.append("## Chord annotation counts")
    lines.append("")
    lines.append("| bucket | hymns |")
    lines.append("| :-- | ----: |")
    for bucket in ["0", "1-4", "5-9", "10-19", "20-39", "40-79", "80+"]:
        lines.append(f"| {bucket} | {ann_hist.get(bucket, 0)} |")
    lines.append("")

    # Tempo.
    lines.append("## Tempo distribution (quarter-note BPM)")
    lines.append("")
    if tempos:
        tempos_sorted = sorted(tempos)
        lines.append(f"- Hymns with parseable tempo: {len(tempos)} / {total}")
        lines.append(f"- Min: {min(tempos):.1f}")
        lines.append(f"- Median: {statistics.median(tempos):.1f}")
        lines.append(f"- Max: {max(tempos):.1f}")
        # Note: tempo values encode Q:1/4=bpm directly, so if the common
        # "tempo fix" has landed we should see values in a plausible range
        # (e.g. 60-180). Flag any suspicious values.
        suspicious = [r for r in reports
                      if r["tempo_bpm"] is not None
                      and (r["tempo_bpm"] < 30 or r["tempo_bpm"] > 300)]
        if suspicious:
            lines.append(f"- Suspicious tempo values (<30 or >300): "
                         f"{len(suspicious)}")
            for r in suspicious[:10]:
                lines.append(f"    - {r['n']} {r['t'][:40]}: "
                             f"{r['tempo_bpm']:.1f}")
    else:
        lines.append("- No parseable tempo values found (tempo fix not "
                     "landed yet?).")
    lines.append("")

    # Exception lists.
    lines.append("## Exception lists")
    lines.append("")

    def emit_bucket(title: str, rows: list[dict]) -> None:
        lines.append(f"### {title} ({len(rows)})")
        lines.append("")
        if not rows:
            lines.append("_(none)_")
            lines.append("")
            return
        lines.append("| n | title | key | meter | anns | tempo | failures |")
        lines.append("| :-- | :-- | :-- | :-- | ---: | ---: | :-- |")
        for r in rows:
            tempo_s = (f"{r['tempo_bpm']:.0f}"
                       if r["tempo_bpm"] is not None else "-")
            fails = "; ".join(r["failures"])
            lines.append(
                f"| {r['n']} | {r['t'][:40]} | {r['effective_key']} | "
                f"{r['meter']} | {r['ann_count']} | {tempo_s} | {fails} |"
            )
        lines.append("")

    emit_bucket("Key not in lever-harp set", fail_key)
    emit_bucket("Exotic meter", fail_meter)
    emit_bucket("Zero chord annotations", fail_ann)
    emit_bucket("Missing/unparseable tempo", fail_tempo)
    emit_bucket("Notes out of harp range", fail_range)

    # All-exceptions list for cross-reference.
    if exceptions:
        lines.append("### All exceptions (combined)")
        lines.append("")
        lines.append("| n | title | failures |")
        lines.append("| :-- | :-- | :-- |")
        for r in exceptions:
            lines.append(
                f"| {r['n']} | {r['t'][:40]} | "
                f"{'; '.join(r['failures'])} |"
            )
        lines.append("")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="ascii", errors="replace") as fh:
        fh.write("\n".join(lines))

    print(f"{total} hymns audited: {len(ready)} pipeline-ready, "
          f"{len(exceptions)} exceptions "
          f"(see modern/key_range_audit.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
