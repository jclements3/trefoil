#!/usr/bin/env python3
"""Build harp hymnal v4: lead sheet melody + unique RH/LH chord voicings.

Reads lead_sheets.json. For each chord annotation on the melody, picks a
unique (LH, RH) voicing pair, adds voicing names to the annotation stack,
and writes RH/LH as block chords. Outputs hymnal_data.json and HTML files.
"""

import json
import re
import os
import sys
from itertools import combinations
from collections import defaultdict
from fractions import Fraction

sys.path.insert(0, os.path.dirname(__file__))
from chord_name import best_name

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')

SCALE = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
NOTE_POS = {n: i for i, n in enumerate(SCALE)}
POS_NOTE = {i: n for i, n in enumerate(SCALE)}


# ── Chord name → note letters ──

def chord_notes_from_name(name):
    """Parse chord name to note letters. Brute force + fallback parser."""
    for size in [3, 4, 5, 6, 7]:
        for combo in combinations('CDEFGAB', size):
            try:
                full = best_name(list(combo))
                root = re.sub(r'[\u00b9\u00b2\u00b3\u2074\u2075-]+$', '', full)
                if root == name:
                    return set(combo)
            except:
                pass
    # Fallback parser
    m = re.match(r'^([A-G])', name)
    if not m:
        return None
    root = m.group(1)
    ri = NOTE_POS[root]
    degrees = {1, 3, 5}
    rest = name[len(root):]
    if 'ø' in rest or '\u00f8' in rest:
        degrees.add(7)
    if 'Δ' in rest or '\u0394' in rest:
        degrees.add(7)
    if '7' in rest:
        degrees.add(7)
    if '9' in rest:
        degrees |= {7, 9}
    if '11' in rest:
        degrees |= {7, 9, 11}
    if '13' in rest:
        degrees |= {7, 9, 11, 13}
    if 's2' in rest:
        degrees.discard(3); degrees.add(2)
    elif 's' in rest:
        degrees.discard(3); degrees.add(4)
    for rm in re.findall(r'-(\d+)', rest):
        degrees.discard(int(rm))
    for add in re.findall(r'\+(\d+)', rest):
        d = int(add)
        if d != 8:
            degrees.add(d)
    notes = set()
    for d in degrees:
        notes.add(SCALE[(ri + (d - 1)) % 7])
    return notes


# ── Hand shape generator ──

def get_hand_shapes(note_letters, max_span=12):
    """All 3-4 note shapes within max_span from 2-octave pool."""
    positions = sorted(NOTE_POS[n] for n in note_letters)
    pool = positions + [p + 7 for p in positions]
    seen = {}
    for size in [3, 4]:
        for combo in combinations(pool, size):
            s = sorted(combo)
            if s[-1] - s[0] + 1 > max_span:
                continue
            shape = tuple(p - s[0] for p in s)
            if shape not in seen:
                seen[shape] = [POS_NOTE[p % 7] for p in s]
    return list(seen.items())


def get_voicing_pairs(note_letters):
    """All asymmetric (LH, RH) pairs. LH biased toward 4 notes."""
    shapes = get_hand_shapes(note_letters)
    pairs_4lh = []  # LH has 4 notes
    pairs_3lh = []  # LH has 3 notes
    for lh_shape, lh_letters in shapes:
        for rh_shape, rh_letters in shapes:
            if lh_shape == rh_shape:
                continue
            if len(lh_shape) == 4:
                pairs_4lh.append((lh_shape, lh_letters, rh_shape, rh_letters))
            else:
                pairs_3lh.append((lh_shape, lh_letters, rh_shape, rh_letters))
    # Put 4-note LH pairs first so they get used first
    return pairs_4lh + pairs_3lh


# ── ABC helpers ──

def shape_to_abc(shape, letters, base_pos, dur_str):
    """Convert hand shape to ABC chord at base_pos (0=C2, 7=C3, 14=C4...)."""
    parts = []
    for i, offset in enumerate(shape):
        pos = base_pos + offset
        octave = pos // 7 + 2
        name = letters[i]
        if octave >= 5:
            parts.append(name.lower() + "'" * (octave - 5))
        elif octave == 4:
            parts.append(name)
        else:
            parts.append(name + ',' * (4 - octave))
    return '[' + ''.join(parts) + ']' + dur_str


def dur_to_abc(units):
    """Duration in L: units to ABC string."""
    if abs(units - round(units)) < 0.01 and round(units) >= 1:
        n = round(units)
        return '' if n == 1 else str(n)
    frac = Fraction(units).limit_denominator(16)
    if frac.denominator == 1:
        return '' if frac.numerator == 1 else str(frac.numerator)
    if frac.numerator == 1:
        return '/' + str(frac.denominator)
    return f'{frac.numerator}/{frac.denominator}'


# ── Main ──

def main():
    with open(os.path.join(PROJECT_DIR, 'app/lead_sheets.json')) as f:
        lead_sheets = json.load(f)

    print(f"Loaded {len(lead_sheets)} lead sheets", file=sys.stderr)

    # Collect all chord names and pre-compute voicing pairs
    all_names = set()
    for h in lead_sheets:
        for m in re.findall(r'"\^([^"]+)"', h['abc']):
            all_names.add(m)

    chord_pairs = {}
    chord_usage = defaultdict(int)
    unmapped = []
    for name in sorted(all_names):
        notes = chord_notes_from_name(name)
        if not notes or len(notes) < 3:
            unmapped.append(name)
            continue
        pairs = get_voicing_pairs(notes)
        if not pairs:
            unmapped.append(name)
            continue
        chord_pairs[name] = pairs

    fallback_pairs = get_voicing_pairs({'C', 'E', 'G'})
    if unmapped:
        print(f"Unmapped: {len(unmapped)}: {unmapped[:10]}", file=sys.stderr)

    output = []
    total_chords = 0

    for hi, h in enumerate(lead_sheets):
        abc_src = h['abc']
        title = h['t']
        key = h['key']

        # Split header from melody
        header_lines = []
        mel_line = ''
        for line in abc_src.strip().split('\n'):
            if line.startswith(('X:', 'T:', 'M:', 'L:', 'Q:', '%%', 'K:')):
                header_lines.append(line)
            else:
                mel_line += line

        if not mel_line:
            continue

        # Get meter info for measure duration
        meter = '4/4'
        length_str = '1/4'
        for line in header_lines:
            if line.startswith('M:'):
                meter = line[2:].strip()
            if line.startswith('L:'):
                length_str = line[2:].strip()

        try:
            ln, ld = length_str.split('/')
            unit_ql = float(ln) / float(ld) * 4
        except:
            unit_ql = 1.0
        try:
            mn, md = meter.split('/')
            measure_units = (float(mn) / float(md) * 4) / unit_ql
        except:
            measure_units = 4.0

        measure_dur_abc = dur_to_abc(measure_units)

        # Split into measures
        raw_bars = mel_line.split('|')
        measures = []
        for b in raw_bars:
            b = b.strip()
            if b and b != ']':
                measures.append(b)

        # For each measure, find chord annotations, assign voicings,
        # rewrite melody annotations to stack 3 names, build RH/LH
        new_mel_measures = []
        rh_measures = []
        lh_measures = []

        last_rh_shape = None
        last_lh_shape = None

        for measure in measures:
            # Compute actual duration of this measure from melody tokens
            meas_dur = 0.0
            for tok in re.findall(r'[_^=]*[A-Ga-g][\',]*[0-9/]*\.?|z[0-9/]*\.?', re.sub(r'"[^"]*"', '', measure)):
                dm = re.search(r'([0-9]+/[0-9]+|[0-9]+|/[0-9]+|/)', tok)
                if dm:
                    ds = dm.group(1)
                    if ds == '/':
                        d = 0.5
                    elif ds.startswith('/'):
                        d = 1.0 / float(ds[1:])
                    elif '/' in ds:
                        p = ds.split('/')
                        d = float(p[0]) / float(p[1])
                    else:
                        d = float(ds)
                else:
                    d = 1.0
                meas_dur += d
            if meas_dur <= 0:
                meas_dur = measure_units
            this_measure_dur_abc = dur_to_abc(meas_dur)

            # Walk melody tokens to find chord positions and durations
            tokens = re.findall(
                r'"[^"]*"[_^=]*[A-Ga-g][\',]*[0-9/]*\.?'
                r'|[_^=]*[A-Ga-g][\',]*[0-9/]*\.?'
                r'|z[0-9/]*\.?'
                r'|\(|\)',
                measure
            )

            # Build list of (chord_name_or_None, beat_position) for each note
            chord_beats = []  # [(chord_name, start_beat, duration)]
            current_chord = None
            current_start = 0.0
            current_dur = 0.0
            beat_pos = 0.0

            for tok in tokens:
                if tok in ('(', ')'):
                    continue
                # Check for chord annotation
                cm = re.match(r'"(\^[^"]+)"', tok)
                if cm:
                    new_chord = cm.group(1)[1:]
                    if current_chord is not None and current_dur > 0:
                        chord_beats.append((current_chord, current_start, current_dur))
                    current_chord = new_chord
                    current_start = beat_pos
                    current_dur = 0.0

                # Parse note/rest duration
                clean = re.sub(r'"[^"]*"', '', tok)
                if re.match(r'[_^=]*[A-Ga-g]|z', clean):
                    dm = re.search(r'([0-9]+/[0-9]+|[0-9]+|/[0-9]+|/)', clean)
                    if dm:
                        ds = dm.group(1)
                        if ds == '/': d = 0.5
                        elif ds.startswith('/'): d = 1.0 / float(ds[1:])
                        elif '/' in ds:
                            p = ds.split('/'); d = float(p[0]) / float(p[1])
                        else: d = float(ds)
                    else:
                        d = 1.0
                    current_dur += d
                    beat_pos += d

            if current_chord is not None and current_dur > 0:
                chord_beats.append((current_chord, current_start, current_dur))
            elif current_dur > 0 and not chord_beats:
                # No chord in this measure — sustain previous
                chord_beats = []

            # Merge short chords (< 1 unit) into their predecessor
            # A chord lasting less than 1 L-unit is a passing tone, not a real change
            if len(chord_beats) > 1:
                merged = [chord_beats[0]]
                for cb in chord_beats[1:]:
                    if cb[2] < 1.0:
                        # Too short — extend previous chord
                        prev = merged[-1]
                        merged[-1] = (prev[0], prev[1], prev[2] + cb[2])
                    else:
                        merged.append(cb)
                # Also check if last chord is too short
                if len(merged) > 1 and merged[-1][2] < 1.0:
                    prev = merged[-2]
                    merged[-2] = (prev[0], prev[1], prev[2] + merged[-1][2])
                    merged.pop()
                chord_beats = merged

            if not chord_beats:
                new_mel_measures.append(measure)
                if last_rh_shape and last_lh_shape:
                    rh_measures.append(shape_to_abc(last_rh_shape[0], last_rh_shape[1], 14, this_measure_dur_abc))
                    lh_measures.append(shape_to_abc(last_lh_shape[0], last_lh_shape[1], 7, this_measure_dur_abc))
                else:
                    rh_measures.append('z' + this_measure_dur_abc)
                    lh_measures.append('z' + this_measure_dur_abc)
                continue

            rh_parts = []
            lh_parts = []

            for ci, (chord_name, start, dur) in enumerate(chord_beats):
                total_chords += 1
                pairs = chord_pairs.get(chord_name, fallback_pairs)
                idx = chord_usage[chord_name] % len(pairs)
                chord_usage[chord_name] += 1
                lh_shape, lh_letters, rh_shape, rh_letters = pairs[idx]

                chord_dur_abc = dur_to_abc(dur)
                rh_abc = shape_to_abc(rh_shape, rh_letters, 14, chord_dur_abc)
                lh_abc = shape_to_abc(lh_shape, lh_letters, 7, chord_dur_abc)
                rh_parts.append(rh_abc)
                lh_parts.append(lh_abc)

                last_rh_shape = (rh_shape, rh_letters)
                last_lh_shape = (lh_shape, lh_letters)

            new_mel_measures.append(measure)
            rh_measures.append(' '.join(rh_parts))
            lh_measures.append(' '.join(lh_parts))

        mel_out = '|'.join(new_mel_measures) + '|]'
        rh_out = '|'.join(rh_measures) + '|]'
        lh_out = '|'.join(lh_measures) + '|]'

        # Build header with staves
        new_header = []
        for line in header_lines:
            if line.startswith('K:'):
                new_header.append('%%staves M | {RH LH}')
                new_header.append('V: M clef=treble name="Melody"')
                new_header.append('V: RH clef=treble name="RH"')
                new_header.append('V: LH clef=bass name="LH"')
                new_header.append(line)
            else:
                new_header.append(line)

        full_abc = '\n'.join(new_header) + '\n'
        full_abc += f'[V: M] {mel_out}\n'
        full_abc += f'[V: RH] {rh_out}\n'
        full_abc += f'[V: LH] {lh_out}\n'

        output.append({
            'n': h['n'], 't': title, 'abc': full_abc, 'key': key,
        })

        # Write HTML
        html_dir = os.path.join(PROJECT_DIR, 'handout/harp_hymnal')
        os.makedirs(html_dir, exist_ok=True)
        safe_title = re.sub(r'[^\w]', '_', title)
        fname = f"{int(h['n']) - 4000:03d}_{safe_title}"
        escaped_abc = full_abc.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title} — Harp Hymnal</title>
<style>body {{ font-family: sans-serif; margin: 20px; }} h1 {{ font-size: 18px; }}</style>
</head><body>
<h1>{title}</h1>
<div id="music"></div>
<script src="../../app/app/src/main/assets/abc2svg/abc2svg-1.js"></script>
<script>
var abc_src = "{escaped_abc}";
var user = {{
  img_out: function(str) {{ document.getElementById("music").innerHTML += str; }},
  errmsg: function(msg) {{ console.warn("abc2svg:", msg); }},
  read_file: function() {{ return ''; }},
  anno_start: function(){{}}, anno_stop: function(){{}},
  get_abcmodel: function(){{}}
}};
var abc = new Abc(user);
abc.tosvg("hymn", abc_src);
</script>
</body></html>'''
        with open(os.path.join(html_dir, fname + '.html'), 'w') as f:
            f.write(html)

        if (hi + 1) % 50 == 0:
            print(f"  {hi+1}/{len(lead_sheets)}...", file=sys.stderr)

    # Write outputs
    out_path = os.path.join(PROJECT_DIR, 'app/hymnal_data.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    assets_path = os.path.join(PROJECT_DIR, 'app/app/src/main/assets/hymnal_data.json')
    with open(assets_path, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f"Wrote {len(output)} hymns, {total_chords} chord voicings", file=sys.stderr)
    if unmapped:
        print(f"Unmapped (fallback): {len(unmapped)}", file=sys.stderr)


if __name__ == '__main__':
    main()
