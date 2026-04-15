#!/usr/bin/env python3.10
"""Verification harness for the modern reharmonization pipeline.

Picks 10 diverse hymns from app/lead_sheets.json, runs the full
reharmonization pipeline on each, and writes a markdown before/after
report to modern/samples_report.md plus rewritten ABC files.

The four pipeline modules are imported lazily via importlib:
    modern.reharm_rules
    modern.voicing_picker
    modern.abc_rewriter
    modern.layout

If any of them is missing, the harness prints which ones are absent
and exits non-zero with a readable message. ASCII only.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_DIR = os.path.join(REPO_ROOT, "handout")
HANDOUT_VOICINGS = os.path.join(REPO_ROOT, "handout.tex")
REPORT_PATH = os.path.join(REPO_ROOT, "modern", "samples_report.md")
SAMPLES_DIR = os.path.join(REPO_ROOT, "modern", "per_hymn")
COMBINED_ABC_PATH = os.path.join(REPO_ROOT, "modern", "samples.abc")
COMBINED_LY_PATH = os.path.join(REPO_ROOT, "modern", "samples.ly")
COMBINED_PDF_PATH = os.path.join(REPO_ROOT, "modern", "samples.pdf")
BUILD_PDF_SCRIPT = os.path.join(REPO_ROOT, "modern", "build_pdf.sh")

ALL_KEYS = ["Eb", "Bb", "F", "C", "G", "D", "A", "E"]
EXTRAS = ["G", "F"]  # most common keys -> 2 extras, total 10


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

REQUIRED_MODULES = [
    "modern.reharm_rules",
    "modern.voicing_picker",
    "modern.abc_rewriter",
    "modern.layout",
    "modern.meter_handler",
]


def load_modules() -> tuple[dict[str, Any], list[str]]:
    """Try to import every required module; return (loaded, missing)."""
    loaded: dict[str, Any] = {}
    missing: list[str] = []
    # Make sure repo root is on sys.path so 'modern.*' imports work.
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    for name in REQUIRED_MODULES:
        try:
            loaded[name] = importlib.import_module(name)
        except Exception as exc:  # ImportError or anything else
            missing.append(f"{name} ({type(exc).__name__}: {exc})")
    return loaded, missing


# ---------------------------------------------------------------------------
# Hymn selection
# ---------------------------------------------------------------------------

CHORD_RE = re.compile(r'"\^([^"]+)"')
METER_RE = re.compile(r"(?m)^M:\s*([^\n]+)")


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else "?"


def count_annotations(abc: str) -> int:
    return len(CHORD_RE.findall(abc))


def select_samples(hymns: list[dict]) -> list[dict]:
    """Diversity rubric: 1 hymn per key + 2 extras (G, F).

    Within each key, prefer 8-20 chord annotations, then prefer
    meters that diversify (3/4 and 4/4 represented at least once).
    """
    by_key: dict[str, list[dict]] = defaultdict(list)
    for h in hymns:
        k = h.get("key", "?")
        if k in ALL_KEYS:
            by_key[k].append(h)

    def score_for_key(h: dict, want_meters: set[str]) -> tuple:
        n_ann = count_annotations(h.get("abc", ""))
        meter = parse_meter(h.get("abc", ""))
        in_window = 8 <= n_ann <= 20
        meter_bonus = 1 if meter in want_meters else 0
        # higher is better -> negate distance from window center 14
        dist = -abs(n_ann - 14) if in_window else -100 - abs(n_ann - 14)
        return (in_window, meter_bonus, dist, -int(h.get("n", "0") or 0))

    selected: list[dict] = []
    seen_meters: set[str] = set()
    want = {"3/4", "4/4"}

    # First pass: 1 per key
    for key in ALL_KEYS:
        cands = by_key.get(key, [])
        if not cands:
            continue
        need = want - seen_meters
        cands_sorted = sorted(cands, key=lambda h: score_for_key(h, need),
                              reverse=True)
        pick = cands_sorted[0]
        selected.append(pick)
        seen_meters.add(parse_meter(pick.get("abc", "")))

    # Extras from G and F (skip already-selected n)
    chosen_ns = {h.get("n") for h in selected}
    for key in EXTRAS:
        cands = [h for h in by_key.get(key, []) if h.get("n") not in chosen_ns]
        if not cands:
            continue
        need = want - seen_meters
        cands_sorted = sorted(cands, key=lambda h: score_for_key(h, need),
                              reverse=True)
        pick = cands_sorted[0]
        selected.append(pick)
        chosen_ns.add(pick.get("n"))
        seen_meters.add(parse_meter(pick.get("abc", "")))

    return selected[:10]


# ---------------------------------------------------------------------------
# Beat / event extraction from ABC
# ---------------------------------------------------------------------------

# Match a chord annotation followed by a single note token (with optional
# accidentals, octave marks, length). We do NOT try to fully parse ABC --
# we only need beat positions for the report.

NOTE_RE = re.compile(r'(\^|=|_)?([A-Ga-gz])([\',]*)(\d+)?(/\d*)?')
LEN_RE = re.compile(r"(?m)^L:\s*(\d+)\s*/\s*(\d+)")
DEFAULT_L = (1, 8)


def parse_default_length(abc: str) -> float:
    m = LEN_RE.search(abc)
    if not m:
        return 1.0 / 8.0
    return int(m.group(1)) / int(m.group(2))


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


def note_duration(token: str, default_l: float) -> float:
    """Compute the duration (in whole notes) of a single note token."""
    # token like "G3/2" or "F" or "z2" -- we already stripped chord ann.
    m = NOTE_RE.match(token)
    if not m:
        return 0.0
    num_str = m.group(4)
    div_str = m.group(5)
    mult = float(num_str) if num_str else 1.0
    if div_str:
        # "/2" or "/" alone (means /2)
        if div_str == "/":
            div = 2.0
        else:
            div = float(div_str[1:]) if len(div_str) > 1 else 2.0
        mult = mult / div
    return default_l * mult


def iter_chord_events(abc: str) -> list[tuple[float, str]]:
    """Walk the music body, return [(beat_within_piece, chord_name), ...].

    Beats are expressed in quarter notes from the start of the piece
    (concatenated bars, ignoring repeats / voltas).
    """
    default_l = parse_default_length(abc)
    # Strip header lines until K:
    lines = abc.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("K:"):
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:])

    # Tokenize: chord annotations, notes, bar lines, decorations.
    events: list[tuple[float, str]] = []
    pos_whole = 0.0  # current position in whole notes
    i = 0
    pending_chord: str | None = None
    while i < len(body):
        ch = body[i]
        if ch == '"':
            # Find matching close quote
            j = body.find('"', i + 1)
            if j < 0:
                break
            inside = body[i + 1:j]
            if inside.startswith("^"):
                pending_chord = inside[1:]
            i = j + 1
            continue
        # Note?
        m = NOTE_RE.match(body, i)
        if m and body[i] not in ("|", "[", "]"):
            tok = m.group(0)
            dur_whole = note_duration(tok, default_l)
            if pending_chord is not None:
                # beat in quarters from start
                beat_q = pos_whole * 4.0
                events.append((beat_q, pending_chord))
                pending_chord = None
            pos_whole += dur_whole
            i = m.end()
            continue
        # Skip everything else (bars, decorations, whitespace)
        i += 1
    return events


# ---------------------------------------------------------------------------
# ChordEvent flag heuristics
# ---------------------------------------------------------------------------


def make_chord_events(events: list[tuple[float, str]],
                      meter: tuple[int, int],
                      key: str,
                      RomanChord, ChordEvent, parse_chord_name) -> list:
    """Build a list of ChordEvent objects with heuristic flags.

    Skips events whose chord name fails to parse into a diatonic
    RomanChord (parse_chord_name returns None for those).
    """
    num, den = meter
    beats_per_bar = num * (4.0 / den)
    parsed: list[tuple[float, float, Any, str]] = []
    for idx, (beat, name) in enumerate(events):
        try:
            roman = parse_chord_name(name, key)
        except TypeError:
            # Older signatures might be parse_chord_name(name)
            try:
                roman = parse_chord_name(name)
            except Exception:
                roman = None
        except Exception:
            roman = None
        if roman is None:
            continue
        # duration: span until next event (in quarters); last gets bar fill.
        next_beat = (events[idx + 1][0] if idx + 1 < len(events)
                     else beat + beats_per_bar)
        dur = max(0.0, next_beat - beat)
        parsed.append((beat, dur, roman, name))

    out = []
    n_events = len(parsed)
    for i, (beat, dur, roman, name) in enumerate(parsed):
        bar_pos = beat % beats_per_bar
        is_strong = (abs(bar_pos) < 1e-6) or (
            beats_per_bar >= 4 and abs(bar_pos - 2.0) < 1e-6
        )
        is_cadence = (i >= n_events - 2)
        next_name = parsed[i + 1][3] if i + 1 < n_events else None
        is_destination = (next_name is not None and next_name != name and
                          is_strong)
        try:
            ev = ChordEvent(
                beat=beat,
                duration=dur,
                chord=roman,
                is_strong_beat=is_strong,
                is_cadence=is_cadence,
                is_destination=is_destination,
            )
        except TypeError:
            # Try without duration.
            ev = ChordEvent(
                beat=beat,
                chord=roman,
                is_strong_beat=is_strong,
                is_cadence=is_cadence,
                is_destination=is_destination,
            )
        out.append((ev, name))
    return out


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def safe_call(fn, *args, **kwargs):
    """Call fn and return (ok, result_or_exc)."""
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:
        return False, exc


_ROM_UPPER = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
_ROM_LOWER = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi", 7: "vii"}


def chord_display_name(c: Any) -> str:
    """Best-effort string for a chord/RomanChord object."""
    if c is None:
        return "?"
    # Tuple form (deg, quality) used by voicing_picker.RomanChord.
    if isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], int):
        deg, qual = c
        is_minor = qual.startswith("m") and not qual.startswith("maj")
        is_dim = "dim" in qual or qual == "hdim7"
        base = (_ROM_LOWER if (is_minor or is_dim) else _ROM_UPPER).get(
            deg, str(deg))
        suffix = ""
        if qual == "7":
            suffix = "7"
        elif qual == "m7":
            suffix = "7"
        elif qual == "maj7":
            suffix = "M7"
        elif qual == "dim":
            suffix = "o"
        elif qual == "dim7":
            suffix = "o7"
        elif qual == "hdim7":
            suffix = "0"  # half-dim approximation
        elif qual == "sus4":
            suffix = "sus4"
        return base + suffix
    for attr in ("name", "label", "symbol"):
        if hasattr(c, attr):
            v = getattr(c, attr)
            if isinstance(v, str):
                return v
    return str(c)


def run_pipeline(hymn: dict, modules: dict[str, Any]) -> dict:
    """Run the full pipeline on one hymn. Returns a dict with results."""
    reharm = modules["modern.reharm_rules"]
    voicing_pkg = modules["modern.voicing_picker"]
    rewriter = modules["modern.abc_rewriter"]
    meter_handler = modules.get("modern.meter_handler")

    raw_abc = hymn["abc"]
    original_meter = parse_meter(raw_abc)
    # Preprocess meter exceptions (M:none, 3/2, 8/4). For non-exotic meters
    # the handler returns the ABC unchanged.
    if meter_handler is not None:
        abc, effective_meter = meter_handler.preprocess_abc(raw_abc)
    else:
        abc, effective_meter = raw_abc, original_meter
    preprocessed = (abc != raw_abc)
    # Make the preprocessed ABC visible to the rest of the function and to
    # callers (write_abcs feeds this into layout.build_combined_ly).
    hymn = dict(hymn)
    hymn["abc"] = abc
    key = hymn.get("key", "C")
    meter = parse_meter_fraction(abc)
    num, den = meter
    beats_per_bar = num * (4.0 / den)

    parse_chord_name = getattr(reharm, "parse_chord_name", None)
    RomanChord = getattr(reharm, "RomanChord", None)
    ChordEvent = getattr(reharm, "ChordEvent", None)
    if parse_chord_name is None or ChordEvent is None:
        raise RuntimeError(
            "reharm_rules missing parse_chord_name or ChordEvent")
    iter_anns = getattr(rewriter, "iter_chord_annotations", None)
    rewrite_abc = getattr(rewriter, "rewrite_abc", None)
    labels_from_voicing = getattr(rewriter, "labels_from_voicing", None)
    if iter_anns is None or rewrite_abc is None or labels_from_voicing is None:
        raise RuntimeError(
            "abc_rewriter missing required functions")
    load_voicings = getattr(voicing_pkg, "load_voicings", None)
    pick_voicing = getattr(voicing_pkg, "pick_voicing", None)
    if load_voicings is None or pick_voicing is None:
        raise RuntimeError(
            "voicing_picker missing load_voicings or pick_voicing")

    # 3a. Walk original abc annotations IN ORDER. We use the rewriter's
    # own iterator so our list aligns 1:1 with what rewrite_abc expects.
    raw_anns = list(iter_anns(abc))           # list[(start, end, name)]
    # Also compute beat-per-annotation from our own parser, for the report.
    beat_events = iter_chord_events(abc)      # list[(beat_q, name)]
    # Best-effort align beats to anns by sequential matching.
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

    # 3b/3c. For each annotation, parse to RomanChord. Track a parallel
    # list `parseable` of indices that produced a real ChordEvent.
    events: list = []
    parse_idx_map: list[int] = []  # event idx -> annotation idx
    fallback_names: list[str] = [name for (_s, _e, name) in raw_anns]
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
        # next beat = next annotation's beat (or +1 bar)
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
        # cadence: last 2 annotations
        is_cadence = (idx >= len(raw_anns) - 2)
        # destination: strong beat + name change vs prior annotation
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

    # 3d. Reharmonize the parseable subset.
    ok, result = safe_call(reharm.reharmonize, events, key)
    if not ok:
        raise RuntimeError(f"reharmonize() failed: {result}")
    new_events = result

    # If reharm returns a different count, fall back to original events
    # for the leftover slots.
    if len(new_events) != len(events):
        # Pad/truncate to match annotation slots we own.
        if len(new_events) < len(events):
            new_events = list(new_events) + events[len(new_events):]
        else:
            new_events = list(new_events)[:len(events)]

    # 3e. Pick voicings for each new event (in order).
    voicings = load_voicings(HANDOUT_VOICINGS)
    voicing_seq = []
    prior = None
    last3: list = []
    for ev in new_events:
        chord = getattr(ev, "chord", None)
        try:
            v = pick_voicing(
                chord, prior, voicings,
                history=last3 if last3 else None,
            )
        except Exception:
            v = prior  # keep last good voicing
        voicing_seq.append(v)
        if v is not None:
            prior = v
            last3.append(v)
            if len(last3) > 3:
                last3 = last3[-3:]

    # 3f. Voicing -> (rh_label, lh_label).
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

    # Build the full replacements list -- one per original annotation.
    # For unparseable original annotations, pass the original name as
    # both RH and LH (best-effort passthrough; abc_rewriter expects ASCII).
    replacements: list[tuple[str, str]] = []
    ev_iter = iter(zip(parse_idx_map, labels_per_event, new_events))
    next_pair = next(ev_iter, None)
    for idx, (_s, _e, name) in enumerate(raw_anns):
        if next_pair is not None and next_pair[0] == idx:
            _i, (rh, lh), _ev = next_pair
            replacements.append((rh, lh))
            next_pair = next(ev_iter, None)
        else:
            safe = re.sub(r"[^A-Za-z0-9#b/+\-]", "", name) or "I"
            replacements.append((safe, safe))

    new_abc = rewrite_abc(abc, replacements)

    # Build report rows -- one per original annotation.
    rows = []
    ev_idx = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        beat = beats_by_idx[idx]
        if ev_idx < len(parse_idx_map) and parse_idx_map[ev_idx] == idx:
            new_name = chord_display_name(
                getattr(new_events[ev_idx], "chord", None))
            rh, lh = labels_per_event[ev_idx]
            frac = f"{rh}/{lh}"
            ev_idx += 1
        else:
            new_name = name + " (skipped)"
            frac = ""
        rows.append((beat, name, new_name, frac))

    labels = labels_per_event

    # Build chord_labels for LilyPond overlay: one (rh, lh, dur_q) per
    # ORIGINAL annotation in the source ABC (so positions align 1:1 with
    # sentinels in layout._rewrite_with_sentinels). For unparseable
    # originals, reuse the raw name as both rh and lh; duration falls
    # back to one quarter note.
    chord_labels: list[tuple[str, str, float]] = []
    ev_idx2 = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        beat = beats_by_idx[idx]
        if ev_idx2 < len(parse_idx_map) and parse_idx_map[ev_idx2] == idx:
            rh, lh = labels_per_event[ev_idx2]
            ev = new_events[ev_idx2]
            dur_q = float(getattr(ev, "duration", 1.0) or 1.0)
            chord_labels.append((rh, lh, dur_q))
            ev_idx2 += 1
        else:
            safe = re.sub(r"[^A-Za-z0-9#b/+\-]", "", name) or "I"
            chord_labels.append((safe, safe, 1.0))

    subs = sum(1 for r in rows if r[1] and r[2] and r[1] != r[2])

    return {
        "hymn": hymn,
        "meter": parse_meter(abc),
        "original_meter": original_meter,
        "preprocessed": preprocessed,
        "rows": rows,
        "new_abc": new_abc,
        "voicings": voicing_seq,
        "labels": labels,
        "chord_labels": chord_labels,
        "subs": subs,
    }


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def write_report(results: list[dict], out_path: str) -> None:
    total_subs = sum(r["subs"] for r in results)
    distinct_pairs: set[tuple[str, str]] = set()
    for r in results:
        for rh, lh in r["labels"]:
            distinct_pairs.add((str(rh), str(lh)))

    lines: list[str] = []
    lines.append("# Modern Reharmonization -- Sample Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Hymns processed: {len(results)}")
    lines.append(f"- Total chord substitutions: {total_subs}")
    lines.append(f"- Distinct (RH, LH) voicing pairs used: "
                 f"{len(distinct_pairs)}")
    lines.append("")

    for r in results:
        h = r["hymn"]
        n = h.get("n", "?")
        title = h.get("t", "Untitled")
        key = h.get("key", "?")
        lines.append(f"## {n} -- {md_escape(title)}")
        lines.append("")
        lines.append(f"- Key: `{key}`")
        lines.append(f"- Meter: `{r['meter']}`")
        lines.append(f"- Substitutions: {r['subs']}")
        lines.append("")
        lines.append("| beat | original | reharm | RH/LH |")
        lines.append("| ---: | :--- | :--- | :--- |")
        for beat, orig, new_name, frac in r["rows"]:
            beat_s = f"{beat:.2f}" if isinstance(beat, (int, float)) else ""
            lines.append(
                f"| {beat_s} | {md_escape(str(orig))} | "
                f"{md_escape(str(new_name))} | {md_escape(str(frac))} |"
            )
        lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="ascii", errors="replace") as fh:
        fh.write("\n".join(lines))


def write_abcs(results: list[dict], modules: dict[str, Any]) -> None:
    """Write per-hymn reharmonized ABCs, the combined LilyPond source,
    and invoke build_pdf.sh to produce samples.pdf.
    """
    import subprocess

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    for r in results:
        n = r["hymn"].get("n", "x")
        path = os.path.join(SAMPLES_DIR, f"{n}.abc")
        with open(path, "w", encoding="ascii", errors="replace") as fh:
            fh.write(r["new_abc"] or "")

    layout = modules["modern.layout"]
    build_combined_ly = getattr(layout, "build_combined_ly", None)
    if build_combined_ly is None:
        print("warning: layout.build_combined_ly missing; "
              "skipping combined LilyPond", file=sys.stderr)
        return

    # layout.build_combined_ly wants {X, t, abc, key, meter, chord_labels}.
    combined_input = []
    for r in results:
        h = r["hymn"]
        try:
            x = int(h.get("n", 0))
        except (TypeError, ValueError):
            x = 0
        # Use the ORIGINAL abc so there is ONE annotation per chord
        # change -- layout sentinelises these 1:1 with the chord_labels
        # list (which carries the reharmonized RH/LH pair). The rewritten
        # ABC with its double `"^LH""^RH"` annotations is retained only
        # as per-hymn text output under modern/per_hymn/.
        combined_input.append({
            "X": x,
            "n": h.get("n"),
            "t": h.get("t", "Untitled"),
            "abc": h.get("abc", ""),
            "key": h.get("key", "C"),
            "meter": r["meter"],
            "chord_labels": r.get("chord_labels", []),
        })

    ly_src = build_combined_ly(combined_input, per_page=3)
    with open(COMBINED_LY_PATH, "w", encoding="utf-8") as fh:
        fh.write(ly_src)

    # Invoke the build script to produce samples.pdf.
    try:
        subprocess.run(
            [BUILD_PDF_SCRIPT, COMBINED_LY_PATH, COMBINED_PDF_PATH],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"WARNING: build_pdf.sh failed: {exc}", file=sys.stderr)
    except FileNotFoundError:
        print(f"WARNING: {BUILD_PDF_SCRIPT} not found", file=sys.stderr)


# ---------------------------------------------------------------------------
# Self-checks
# ---------------------------------------------------------------------------


def self_check(report_path: str, n_hymns_expected: int,
               total_subs: int) -> list[str]:
    """Return a list of failure messages (empty = all good)."""
    failures: list[str] = []
    with open(report_path, "r", encoding="ascii", errors="replace") as fh:
        text = fh.read()

    # Headers balanced (each ## hymn header has at least the table)
    h2 = re.findall(r"(?m)^## ", text)
    # 1 summary + N hymns
    if len(h2) != n_hymns_expected + 1:
        failures.append(
            f"expected {n_hymns_expected + 1} '## ' headers, got {len(h2)}"
        )

    # Tables well-formed: every header line followed by separator line
    table_headers = [
        i for i, ln in enumerate(text.splitlines())
        if ln.startswith("| beat |")
    ]
    if len(table_headers) != n_hymns_expected:
        failures.append(
            f"expected {n_hymns_expected} tables, got {len(table_headers)}"
        )

    if total_subs <= 30:
        failures.append(
            f"total substitutions = {total_subs}; expected > 30"
        )
    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    modules, missing = load_modules()
    if missing:
        print("ERROR: required pipeline modules are missing or failed to "
              "import. Cannot run the verification harness.", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("Add the missing modules under modern/ and rerun.",
              file=sys.stderr)
        return 2

    if not os.path.exists(LEAD_SHEETS_PATH):
        print(f"ERROR: {LEAD_SHEETS_PATH} not found", file=sys.stderr)
        return 3

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    samples = select_samples(hymns)
    if len(samples) < 10:
        print(f"warning: only {len(samples)} samples selected "
              "(need 10); continuing", file=sys.stderr)

    print(f"Selected {len(samples)} hymns:")
    for h in samples:
        print(f"  {h.get('n')} {h.get('key')} "
              f"{parse_meter(h.get('abc',''))} -- {h.get('t','?')[:40]}")

    results: list[dict] = []
    errors: list[tuple[str, str]] = []
    for h in samples:
        try:
            results.append(run_pipeline(h, modules))
        except Exception as exc:
            errors.append((h.get("n", "?"), f"{type(exc).__name__}: {exc}"))
            print(f"  pipeline failed on hymn {h.get('n')}: {exc}",
                  file=sys.stderr)

    if errors:
        print(f"ERROR: pipeline crashed on {len(errors)} hymn(s)",
              file=sys.stderr)
        for n, msg in errors:
            print(f"  - {n}: {msg}", file=sys.stderr)
        return 4

    write_report(results, REPORT_PATH)
    write_abcs(results, modules)

    total_subs = sum(r["subs"] for r in results)
    failures = self_check(REPORT_PATH, len(results), total_subs)
    if failures:
        print("Self-check FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 5

    distinct_pairs: set[tuple[str, str]] = set()
    for r in results:
        for rh, lh in r["labels"]:
            distinct_pairs.add((str(rh), str(lh)))

    print("OK")
    print(f"  hymns: {len(results)}")
    print(f"  substitutions: {total_subs}")
    print(f"  distinct voicing pairs: {len(distinct_pairs)}")
    print(f"  report: {REPORT_PATH}")
    print(f"  abcs: {SAMPLES_DIR}/")
    print(f"  lilypond: {COMBINED_LY_PATH}")
    print(f"  pdf: {COMBINED_PDF_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
