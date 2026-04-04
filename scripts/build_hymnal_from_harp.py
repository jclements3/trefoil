#!/usr/bin/env python3
"""Convert handout/harp_hymnal ABC files to stripchart format for the app.

Reads each .abc file as-is (voicings untouched), injects stripchart layout
directives, extracts chord annotations and key, writes hymnal_data.json.
"""

import json
import os
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
HYMNAL_DIR = PROJECT_DIR / 'handout' / 'harp_hymnal'
OUT_PATH = PROJECT_DIR / 'abc2stripchart' / 'hymnal_data.json'

STRIPCHART_DIRECTIVES = [
    '%%pagewidth 200cm',
    '%%continueall 1',
    '%%leftmargin 0.5cm',
    '%%rightmargin 0.5cm',
    '%%topspace 0',
    '%%musicspace 0',
    '%%writefields Q 0',
]


def extract_chords_from_melody(melody_line):
    """Extract "^..." chord annotations from [V: M] line.

    Returns list of {beat, abs, rhn, lhn} dicts.
    Each beat position corresponds to a note/rest in the melody.
    The annotations appear as "^abstract""^RH""^LH" before each note.
    """
    chords = []
    # Find all annotation clusters: one or more "^..." before a note
    # Walk through tokens counting notes/rests for beat index
    beat = 0
    i = 0
    text = melody_line
    # Strip voice prefix
    if text.startswith('[V:'):
        text = text.split(']', 1)[1] if ']' in text else text

    pending_annos = []
    pos = 0
    while pos < len(text):
        ch = text[pos]
        if ch == '"':
            # Read annotation string
            end = text.index('"', pos + 1) if '"' in text[pos+1:] else len(text)
            anno = text[pos+1:end]
            if anno.startswith('^'):
                pending_annos.append(anno[1:])
            pos = end + 1
        elif ch in 'ABCDEFGabcdefgz':
            # This is a note or rest — assign pending annotations
            if pending_annos:
                abs_name = pending_annos[0] if len(pending_annos) >= 1 else ''
                rh_name = pending_annos[1] if len(pending_annos) >= 2 else ''
                lh_name = pending_annos[2] if len(pending_annos) >= 3 else ''
                chords.append({'beat': beat, 'abs': abs_name, 'rhn': rh_name, 'lhn': lh_name})
                pending_annos = []
            beat += 1
            # Skip rest of note token (accidentals handled by leading ^_= before letter)
            pos += 1
            # Skip octave marks and duration
            while pos < len(text) and text[pos] in ",'0123456789/":
                pos += 1
        elif ch in '^_=' and pos + 1 < len(text) and text[pos+1] in 'ABCDEFGabcdefg':
            # Accidental before note — skip, the note letter follows
            pos += 1
        elif ch == '(' and pos + 1 < len(text) and text[pos+1] in ' "^_=ABCDEFGabcdefg':
            # Slur/tie open — skip
            pos += 1
        elif ch == ')':
            pos += 1
        else:
            pos += 1

    return chords


def convert_abc_to_stripchart(abc_text, hymn_number):
    """Add stripchart directives to ABC, return (abc_string, key, title, chords)."""
    lines = abc_text.strip().split('\n')

    title = ''
    key = ''
    meter = ''
    header_lines = []
    voice_lines = []
    melody_line = ''
    in_header = True

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('X:'):
            header_lines.append(f'X: {hymn_number}')
            continue
        if stripped.startswith('T:'):
            title = stripped[2:].strip()
            header_lines.append(stripped)
            continue
        if stripped.startswith('M:'):
            meter = stripped[2:].strip()
            header_lines.append(stripped)
            continue
        if stripped.startswith('L:'):
            header_lines.append(stripped)
            continue
        if stripped.startswith('Q:'):
            # We'll keep Q in the voice line, strip from header
            header_lines.append(stripped)
            continue
        if stripped.startswith('K:'):
            key = stripped[2:].strip()
            header_lines.append(stripped)
            in_header = False
            continue
        if stripped.startswith('%%staves'):
            header_lines.append(stripped)
            continue
        if stripped.startswith('%%'):
            # Skip existing format directives — we'll replace them
            continue
        if stripped.startswith('V:'):
            header_lines.append(stripped)
            continue
        if stripped.startswith('[V:'):
            voice_lines.append(stripped)
            if '[V: M]' in stripped or '[V:M]' in stripped:
                melody_line = stripped
            continue
        # Anything else (continuation of voice lines, etc.)
        voice_lines.append(stripped)

    # Build stripchart ABC
    # Insert stripchart directives after M/L/Q and before staves/V/K
    out_lines = []
    for hl in header_lines:
        out_lines.append(hl)
        # Insert directives right after Q line (before staves)
        if hl.startswith('Q:'):
            out_lines.extend(STRIPCHART_DIRECTIVES)

    # If there was no Q: line, insert after L:
    if not any(hl.startswith('Q:') for hl in header_lines):
        new_out = []
        inserted = False
        for ol in out_lines:
            new_out.append(ol)
            if ol.startswith('L:') and not inserted:
                new_out.extend(STRIPCHART_DIRECTIVES)
                inserted = True
        out_lines = new_out

    for vl in voice_lines:
        out_lines.append(vl)

    abc_out = '\n'.join(out_lines) + '\n'

    # Extract chords from melody
    chords = extract_chords_from_melody(melody_line) if melody_line else []

    return abc_out, key, title, chords


def main():
    abc_files = sorted(f for f in os.listdir(HYMNAL_DIR) if f.endswith('.abc'))
    print(f"Found {len(abc_files)} ABC files in {HYMNAL_DIR}")

    output = []
    for fname in abc_files:
        # Extract hymn number from filename: 001_Title.abc -> 3001
        num_match = re.match(r'(\d+)_', fname)
        if not num_match:
            print(f"  Skipping {fname} (no number prefix)")
            continue
        hymn_num = 3000 + int(num_match.group(1))

        with open(HYMNAL_DIR / fname) as f:
            abc_text = f.read()

        abc_out, key, title, chords = convert_abc_to_stripchart(abc_text, hymn_num)

        output.append({
            'n': str(hymn_num),
            't': title,
            'key': key,
            'abc': abc_out,
        })

    # Sort by number
    output.sort(key=lambda x: int(x['n']))

    with open(OUT_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    # Summary
    keys = {}
    for h in output:
        keys.setdefault(h['key'], 0)
        keys[h['key']] += 1
    print(f"Wrote {len(output)} hymns to {OUT_PATH}")
    for k in sorted(keys):
        print(f"  {k}: {keys[k]}")


if __name__ == '__main__':
    main()
