"""Stitch per-page MusicXML output from oemer into a single licks_omr.abc.

Uses omr_a4_mapping.json to know which lick indices are on each page.
Each lick's source image is typically 3 bars of content + 1 bar rest = 4 bars,
but some are 2-staff = 8 bars. We carve the per-page MusicXML measure stream
into per-lick segments using the expected bar counts.

Chord symbols from the existing licks.abc are re-attached bar-by-bar.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from fractions import Fraction

HERE = Path(__file__).parent
WORK = HERE / "omr_work"
MAPPING = json.loads((HERE / "omr_a4_mapping.json").read_text())
LICKS_ABC = HERE / "licks.abc"
OUT = HERE / "licks_omr.abc"

# Lick indices known to be 2-staff in the source image set
TWO_STAFF = {13, 19, 40, 59, 60, 62, 65, 66, 70, 71, 72, 73, 74, 75, 77}

def bars_per_lick(idx: int) -> int:
    return 8 if idx in TWO_STAFF else 4

# --- MusicXML mini-parser ---------------------------------------------------
def parse_page(mxl_path: Path):
    """Return list of measures. Each measure is list of events.
    Event: ('note', duration_qL, midi, accidental) or ('rest', duration_qL).
    """
    from music21 import converter
    score = converter.parse(str(mxl_path))
    measures = []
    # Flatten all parts: collect measures in order from each part sequentially.
    # oemer often splits into multiple parts when it misreads staff grouping.
    for part in score.parts:
        for m in part.getElementsByClass('Measure'):
            evs = []
            for el in m.notesAndRests:
                ql = float(el.quarterLength)
                if hasattr(el, 'isRest') and el.isRest:
                    evs.append(("rest", ql))
                else:
                    if el.isChord:
                        top = max(el.pitches, key=lambda p: p.midi)
                    else:
                        top = el.pitch
                    acc = top.accidental.name if top.accidental else None
                    evs.append(("note", ql, top.midi, acc))
            measures.append(evs)
    return measures

# --- ABC output helpers ------------------------------------------------------
PC_SHARP = {0:"C",1:"^C",2:"D",3:"^D",4:"E",5:"F",6:"^F",7:"G",8:"^G",9:"A",10:"^A",11:"B"}
PC_FLAT  = {0:"C",1:"_D",2:"D",3:"_E",4:"E",5:"F",6:"_G",7:"G",8:"_A",9:"A",10:"_B",11:"B"}

def midi_to_abc(midi: int, prefer_flat: bool = False) -> str:
    letter_map = PC_FLAT if prefer_flat else PC_SHARP
    pc = midi % 12
    octave = midi // 12 - 1
    tok = letter_map[pc]
    if tok[0] in "^_=":
        acc = tok[0]; letter = tok[1]
    else:
        acc = ""; letter = tok
    if octave >= 5:
        letter = letter.lower()
        note_str = letter + ("'" * (octave - 5))
    else:
        note_str = letter + ("," * (4 - octave))
    return acc + note_str

def dur_to_abc(ql: float) -> str:
    """Quarter-length → ABC duration string (L:1/8 base)."""
    eighths = Fraction(ql).limit_denominator(4) * 2
    # eighths might be e.g. 1 (=8th), 2 (=4th), 4 (=half), 8 (=whole), 1/2 (=16th)
    if eighths == 1: return ""
    if eighths == Fraction(1, 2): return "/2"
    if eighths == Fraction(1, 4): return "/4"
    if eighths == 2: return "2"
    if eighths == 3: return "3"
    if eighths == 4: return "4"
    if eighths == 6: return "6"
    if eighths == 8: return "8"
    if eighths == Fraction(3, 2): return "3/2"
    # fallback
    if eighths.denominator == 1:
        return str(eighths.numerator)
    return f"{eighths.numerator}/{eighths.denominator}"

def measure_to_abc(events, chord_prefix: str = "") -> str:
    toks = []
    for ev in events:
        if ev[0] == "rest":
            toks.append(f"z{dur_to_abc(ev[1])}")
        else:
            _, ql, midi, acc = ev
            prefer_flat = (acc == "flat")
            toks.append(midi_to_abc(int(midi), prefer_flat) + dur_to_abc(ql))
    body = "".join(toks) if toks else "z8"
    return chord_prefix + body

# --- chord symbols extraction ------------------------------------------------
def load_chord_progressions():
    """Parse existing licks.abc → dict: lick_idx → [chord_per_bar (up to 4)]."""
    src = LICKS_ABC.read_text()
    tunes = re.split(r"(?=^X:\d+)", src, flags=re.MULTILINE)
    result = {}
    for tune in tunes[1:]:
        m = re.match(r"X:(\d+)", tune)
        if not m: continue
        idx = int(m.group(1))
        k_match = re.search(r"^K:.*$", tune, re.M)
        if not k_match: continue
        body = tune[k_match.end():]
        # split into bars at |
        first_line = body.strip().split("\n")[0] if body.strip() else ""
        bars = [b.strip() for b in first_line.split("|") if b.strip()]
        chords = []
        for bar in bars:
            cm = re.match(r'"([^"]+)"', bar)
            chords.append(cm.group(1) if cm else "")
        result[idx] = chords
    return result

# --- main --------------------------------------------------------------------
def main():
    chord_progs = load_chord_progressions()

    out_lines = [
        "%abc-2.1",
        "% 100 Jazz Licks — PITCHES FROM OEMER (OMR on A4 pages)",
        "% Chord symbols preserved from licks.abc (per-bar).",
        "",
    ]

    successful = 0
    failed = []
    for page_idx, lick_ids in enumerate(MAPPING, start=1):
        mxl = WORK / f"page_{page_idx:02d}.musicxml"
        if not mxl.exists():
            failed.append(page_idx)
            # Emit placeholders so lick numbering is preserved
            for lid in lick_ids:
                out_lines.append(f"X:{lid}\nT:Lick {lid:02d} (OMR failed)\n"
                                 "M:4/4\nL:1/8\nK:C\nz8 |\n")
            continue
        try:
            measures = parse_page(mxl)
        except Exception as e:
            print(f"[warn] parse fail page {page_idx}: {e}")
            failed.append(page_idx)
            for lid in lick_ids:
                out_lines.append(f"X:{lid}\nT:Lick {lid:02d} (OMR parse fail)\n"
                                 "M:4/4\nL:1/8\nK:C\nz8 |\n")
            continue

        # Walk measures, assigning bars to each lick
        cursor = 0
        for lid in lick_ids:
            n_bars = bars_per_lick(lid)
            bars = measures[cursor:cursor + n_bars]
            cursor += n_bars
            if not bars:
                out_lines.append(f"X:{lid}\nT:Lick {lid:02d} (empty)\n"
                                 "M:4/4\nL:1/8\nK:C\nz8 |\n")
                continue
            # Stitch ABC: for 4-bar licks use per-bar chord prefix; for 8-bar
            # (double-staff), repeat chord prefix on bars 1,3 (second stave).
            chords = chord_progs.get(lid, [])
            bar_strs = []
            for bi, bar_evs in enumerate(bars[:n_bars]):
                chord_idx = bi % 4 if n_bars == 8 else bi
                chord = chords[chord_idx] if chord_idx < len(chords) else ""
                prefix = f'"{chord}"' if chord else ""
                bar_strs.append(measure_to_abc(bar_evs, prefix))
            tune = (f"X:{lid}\nT:Lick {lid:02d}\nM:4/4\nL:1/8\nK:C\n"
                    + " | ".join(bar_strs) + " |")
            out_lines.append(tune)
            out_lines.append("")
            successful += 1

    OUT.write_text("\n".join(out_lines))
    print(f"[stitch] wrote {OUT}: {successful}/100 licks transcribed")
    if failed:
        print(f"[stitch] failed pages: {failed}")

if __name__ == "__main__":
    main()
