"""Convert a MusicXML file (from oemer OMR) to ABC for a single lick.

Takes the first part/voice, emits single-line ABC melody. Pitches preserved
including accidentals. Durations quantized to 1/8 grid (L:1/8).

Usage: python3 mxl_to_abc.py <in.musicxml> <lick_idx> > out.abc
"""
from __future__ import annotations
import sys
from fractions import Fraction
from music21 import converter, note, chord as m21chord, stream

# Map PC → ABC letter (using sharps for black keys by default; flat version
# chosen based on the accidental actually present)
PC_LETTER_SHARP = {0:"C",1:"^C",2:"D",3:"^D",4:"E",5:"F",6:"^F",7:"G",8:"^G",9:"A",10:"^A",11:"B"}
PC_LETTER_FLAT  = {0:"C",1:"_D",2:"D",3:"_E",4:"E",5:"F",6:"_G",7:"G",8:"_A",9:"A",10:"_B",11:"B"}

def midi_to_abc(midi_pitch: int, prefer_flat: bool) -> str:
    """Convert MIDI pitch → ABC token (e.g. 60→C, 72→c, 84→c', 48→C,).

    Middle C (MIDI 60) = C4 = 'C' in ABC default. 'c' = C5 = MIDI 72.
    """
    letter_map = PC_LETTER_FLAT if prefer_flat else PC_LETTER_SHARP
    pc = midi_pitch % 12
    octave = midi_pitch // 12 - 1   # MIDI 60 = octave 4
    tok = letter_map[pc]
    # Separate accidental prefix and letter
    if tok.startswith(("^","_","=")):
        acc = tok[0]; letter = tok[1]
    else:
        acc = ""; letter = tok
    # Octave mapping:
    # C4=octave 4 → 'C' (uppercase, no marks)
    # C5 → 'c'
    # C6 → "c'"
    # C3 → 'C,'
    # C2 → 'C,,'
    if octave >= 5:
        letter = letter.lower()
        note_str = letter + ("'" * (octave - 5))
    else:
        note_str = letter + ("," * (4 - octave))
    return acc + note_str

def quantize_dur(q: Fraction) -> str:
    """Convert music21 quarter-length to ABC duration suffix (L:1/8 base).

    Eighth note = 0.5 quarter = 1 unit. Quarter = 2, half = 4, 16th = 1/2.
    """
    eighths = q * 2   # quarter=2 eighths
    # Nearest 1/4 eighth (32nd note resolution)
    num = Fraction(eighths).limit_denominator(4)
    if num == 1: return ""
    if num == 2: return "2"
    if num == 3: return "3"
    if num == 4: return "4"
    if num == 6: return "6"
    if num == 8: return "8"
    if num == Fraction(1, 2): return "/2"
    if num == Fraction(3, 2): return "3/2"
    if num == Fraction(1, 4): return "/4"
    # Fallback
    if num.denominator == 1:
        return str(num.numerator)
    return f"{num.numerator}/{num.denominator}"

def convert(mxl_path: str, lick_idx: int = 0, key: str = "C") -> str:
    score = converter.parse(mxl_path)
    # Flatten to a single stream of notes/rests
    part = score.parts[0] if score.parts else score
    notes = []
    for el in part.flatten().notesAndRests:
        if isinstance(el, note.Rest):
            notes.append(("rest", el.quarterLength))
        elif isinstance(el, note.Note):
            notes.append(("note", el.quarterLength, el.pitch.midi,
                          el.pitch.accidental.name if el.pitch.accidental else None))
        elif isinstance(el, m21chord.Chord):
            # Take highest pitch of chord (melody-like reduction)
            top = max(el.pitches, key=lambda p: p.midi)
            acc = top.accidental.name if top.accidental else None
            notes.append(("note", el.quarterLength, top.midi, acc))

    # Emit as a single line. Split by bar using music21's barlines if possible.
    # For now, emit tokens back-to-back with bar-every-8-eighths heuristic.
    toks = []
    eighths_in_bar = 0
    BEATS_PER_BAR = 8  # 4/4 L:1/8
    bar_tokens = []
    for entry in notes:
        if entry[0] == "rest":
            q = entry[1]
            dur = quantize_dur(Fraction(q).limit_denominator(8))
            bar_tokens.append("z" + dur)
            eighths_in_bar += q * 2
        else:
            _, q, midi, acc = entry
            prefer_flat = (acc == "flat")
            tok = midi_to_abc(int(midi), prefer_flat)
            dur = quantize_dur(Fraction(q).limit_denominator(8))
            bar_tokens.append(tok + dur)
            eighths_in_bar += q * 2
        # Bar break when accumulated ~8 eighths
        if eighths_in_bar >= BEATS_PER_BAR - 0.001:
            toks.append(" ".join(bar_tokens))
            bar_tokens = []
            eighths_in_bar = 0
    if bar_tokens:
        toks.append(" ".join(bar_tokens))

    header = [
        f"X:{lick_idx}",
        f"T:Lick {lick_idx:02d}",
        "M:4/4",
        "L:1/8",
        f"K:{key}",
    ]
    body = " | ".join(toks) + " |"
    return "\n".join(header + [body])

if __name__ == "__main__":
    mxl = sys.argv[1]
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(convert(mxl, idx))
