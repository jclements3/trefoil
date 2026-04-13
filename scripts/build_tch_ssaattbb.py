#!/usr/bin/env python3
"""Build Tch-SSAATTBB hymnal: handout chord table voicings as block chords.

Uses the same chord lookup pipeline as the Tchaikovsky cadenza builder
(chord_to_spec with SATB inversion hints) but outputs ABC notation with
3 voices: Melody + RH chord + LH chord, rendered via abc2svg.

The voicing for each measure comes from the handout chord table (14 patterns
× 7 degrees, with inversions). Chord tones are placed as block chords:
  - LH: 2-4 notes in bass register (strings 1-14, C2-B3)
  - RH: 2-3 notes in treble register (strings 15-33, C4-G6)
"""

import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_drill import (
    PAT_MAP, CHORD_NAMES, VALID, NOTES_PER_OCT,
    pattern_strings, string_to_abc, is_rh,
)
from build_tchaikovsky_hymnal import (
    SCALES, NOTE_SEMI, HARP_LOW, HARP_HIGH, STAFF_DIVIDE,
    chord_to_spec, chord_tone_strings,
)

LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
SATB_INDEX = ROOT / 'app' / 'satb_chord_index.json'
OUTPUT = ROOT / 'app' / 'tch_ssaattbb_data.json'

# ── Reuse SatbAligner from the MEI builder ──

NOTE_LETTER_PC = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11,
}

def _chord_root_pc(chord_str):
    m = re.match(r'^([A-G])([#b]?)', chord_str)
    if not m:
        return None
    pc = NOTE_LETTER_PC[m.group(1)]
    if m.group(2) == '#': pc = (pc + 1) % 12
    elif m.group(2) == 'b': pc = (pc - 1) % 12
    return pc


class SatbAligner:
    LOOKAHEAD = 6
    def __init__(self, events):
        self.events = events or []
        self.idx = 0
    def hint_for(self, chord_str):
        if not self.events:
            return None
        root_pc = _chord_root_pc(chord_str)
        if root_pc is None:
            return None
        look_end = min(len(self.events), self.idx + self.LOOKAHEAD)
        for j in range(self.idx, look_end):
            if self.events[j]['root'] == root_pc:
                ev = self.events[j]
                self.idx = j + 1
                return {'inv': ev.get('inv', 0), 'seventh': ev.get('seventh')}
        return None


def extract_chords(bar_raw):
    """Pull chord symbols from ABC annotations like "^D7" """
    return [m.group(1) for m in re.finditer(r'"\^([^"]+)"', bar_raw)]


def spec_to_voices(spec, key):
    """Distribute chord tones across 8 voices (S1 S2 A1 A2 T1 T2 B1 B2) + Pedal.

    Returns (voices, pedal) where voices is a list of 8 string numbers (or None
    for rests) ordered S1..B2 high-to-low, and pedal is the lowest root string.
    """
    tones = sorted(chord_tone_strings(spec))  # low to high
    if not tones:
        return [None]*8, None

    # Pedal: lowest instance of the chord root in the bass octave (strings 1-7)
    start_string = spec[0]
    root_letter_idx = (start_string - 1) % 7  # which scale degree position
    pedal = None
    for s in tones:
        if (s - 1) % 7 == root_letter_idx and s <= 7:
            pedal = s
            break
    # Fallback: lowest tone if no root in bottom octave
    if pedal is None:
        for s in tones:
            if (s - 1) % 7 == root_letter_idx:
                pedal = s
                break

    # Distribute tones across 8 voices, high to low: S1 S2 A1 A2 T1 T2 B1 B2
    # Use all tones (typically 5-10 across the harp range)
    desc = sorted(tones, reverse=True)  # highest first
    voices = [None] * 8
    for i in range(min(8, len(desc))):
        voices[i] = desc[i]

    return voices, pedal


def abc_note(string_num, dur):
    """Format a single string number as ABC note, or rest if None."""
    if string_num is None:
        return f'z{dur}'
    return f'{string_to_abc(string_num)}{dur}'


def parse_lead_sheet(abc_text):
    """Extract bars, time signature, note length, and tempo from lead sheet ABC."""
    ts = '4/4'
    note_len = '1/8'
    tempo = 100
    melody_lines = []

    for line in abc_text.split('\n'):
        line = line.strip()
        if line.startswith('M:'):
            ts = line.split(':', 1)[1].strip()
        elif line.startswith('L:'):
            note_len = line.split(':', 1)[1].strip()
        elif line.startswith('Q:'):
            qm = re.search(r'(\d+)/(\d+)=(\d+)', line)
            if qm:
                tempo = int(qm.group(3))
        elif line.startswith('K:'):
            continue
        elif not line.startswith(('%', 'X:', 'T:', 'V:', 'W:', 'w:')):
            # Melody line
            if any(c in line for c in 'ABCDEFGabcdefg'):
                melody_lines.append(line)

    raw = ' '.join(melody_lines)
    # Split on barlines
    bars = [b.strip() for b in re.split(r'\|', raw) if b.strip()]
    return bars, ts, note_len, tempo


def build_hymn(ls, satb_events=None):
    """Build one Tch-SSAATTBB hymn with 10 voices:
    Melody + S1 S2 A1 A2 T1 T2 B1 B2 + P (pedal).

    Each SSAATTBB voice carries a single note from the handout chord table.
    Voices are distributed high-to-low: S1=highest, B2=lowest.
    P = lowest root note for bass reinforcement.
    """
    key = ls['key']
    if key not in SCALES:
        return None

    bars, ts, note_len, tempo = parse_lead_sheet(ls['abc'])
    aligner = SatbAligner(satb_events or [])

    ts_m = re.match(r'(\d+)/(\d+)', ts)
    if not ts_m:
        return None  # skip M:none hymns for now
    ts_num, ts_den = int(ts_m.group(1)), int(ts_m.group(2))
    dur = ts_num * 8 // ts_den  # measure duration in L:1/8 units

    mel_bars = []
    chord_labels = []
    # 8 SSAATTBB voices + pedal, per measure
    voice_bars = [[] for _ in range(8)]  # S1 S2 A1 A2 T1 T2 B1 B2
    pedal_bars = []

    prev_spec = None
    for bar_raw in bars:
        mel_clean = re.sub(r'"[^"]*"', '', bar_raw).strip()
        mel_bars.append(mel_clean)

        chords = extract_chords(bar_raw)
        spec = None
        if chords:
            hint = aligner.hint_for(chords[0])
            spec = chord_to_spec(chords[0], key, inv_hint=hint)

        if spec is None:
            spec = prev_spec
        if spec is not None:
            prev_spec = spec
            voices, pedal = spec_to_voices(spec, key)
            for v in range(8):
                voice_bars[v].append(abc_note(voices[v], dur))
            pedal_bars.append(abc_note(pedal, dur))
            chord_labels.append(spec[3])
        else:
            for v in range(8):
                voice_bars[v].append(f'z{dur}')
            pedal_bars.append(f'z{dur}')
            chord_labels.append(None)

    # Voice names and score layout
    # S1 S2 on treble stem up/down, A1 A2 on treble stem up/down
    # T1 T2 on bass stem up/down, B1 B2 on bass stem up/down
    # P on bass
    vnames = ['S1', 'S2', 'A1', 'A2', 'T1', 'T2', 'B1', 'B2']

    header = f"""X: {ls['n']}
T: {ls['t']}
M: {ts}
L: 1/8
Q: 1/4={tempo}
%%pagewidth 200cm
%%continueall 1
%%equalbars 1
%%scale 1.2
%%leftmargin 0.5cm
%%rightmargin 0.5cm
%%topspace 0
%%titlespace 0
%%musicspace 0
%%writefields T 0
%%annotationfont * 14
%%score M | (S1 S2) | (A1 A2) | (T1 T2) | (B1 B2) | P
V: M clef=treble name="Melody"
V: S1 clef=treble stem=up
V: S2 clef=treble stem=down
V: A1 clef=treble stem=up
V: A2 clef=treble stem=down
V: T1 clef=bass stem=up
V: T2 clef=bass stem=down
V: B1 clef=bass stem=up
V: B2 clef=bass stem=down
V: P clef=bass name="Pedal"
K: {key}"""

    # Add chord annotations to melody voice
    mel_annotated = []
    for mel, label in zip(mel_bars, chord_labels):
        if label:
            mel_annotated.append(f'"^{label}"{mel}')
        else:
            mel_annotated.append(mel)

    lines = ['[V: M] ' + ' | '.join(mel_annotated) + ' |]']
    for v in range(8):
        lines.append(f'[V: {vnames[v]}] ' + ' | '.join(voice_bars[v]) + ' |]')
    lines.append('[V: P] ' + ' | '.join(pedal_bars) + ' |]')

    abc = header + '\n' + '\n'.join(lines) + '\n'

    return {
        'n': ls['n'],
        't': ls['t'],
        'abc': abc,
        'key': key,
        'tempo': tempo,
    }


def main():
    print('Loading lead sheets...')
    lead_sheets = json.loads(LEAD_SHEETS.read_text())
    print(f'  {len(lead_sheets)} hymns')

    satb_index = {}
    if SATB_INDEX.exists():
        print('Loading SATB chord index...')
        satb_index = json.loads(SATB_INDEX.read_text())
        print(f'  {len(satb_index)} hymns with SATB analysis')

    results = []
    failed = 0
    for ls in lead_sheets:
        n = ls['n']
        satb_events = satb_index.get(str(n))
        hymn = build_hymn(ls, satb_events)
        if hymn:
            results.append(hymn)
        else:
            failed += 1

    print(f'\nWriting {len(results)} hymns to {OUTPUT} ({failed} failed)')
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False))
    print(f'Done. {OUTPUT.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
