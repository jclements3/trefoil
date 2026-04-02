#!/usr/bin/env python3
"""Build harp-trefoil-hymnal using music21 for proper ABC parsing.

Replaces the broken hand-written ABC parser with music21, which correctly
handles all durations, barlines, pickups, ties, tuplets, and time signatures.
"""

import json
import sys
import re
from collections import defaultdict
from pathlib import Path

import music21

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

# ── Load trefoil voicing table ──
with open(PROJECT_DIR / 'trefoil/trefoil_C.json') as f:
    trefoil = json.load(f)

voicings = []
for section, rows in trefoil['sections'].items():
    for i, r in enumerate(rows):
        voicings.append({
            'id': f"{section}_{i+1}",
            'root': r['root'], 'lh': r['lh'], 'rh': r['rh'],
            'lhNotes': r['lhNotes'], 'rhNotes': r['rhNotes'],
            'lhPat': r['lhPat'], 'rhPat': r['rhPat'], 'gap': r['gap'],
        })

SCALE_PC = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
NOTE_NAMES = ['C','D','E','F','G','A','B']

for v in voicings:
    v['pcs'] = set(SCALE_PC[ch] for ch in v['lhNotes']+v['rhNotes'] if ch in SCALE_PC)

# ── Voicing helpers ──
def con_score(vpcs, mpcs):
    total = 0
    for mpc in mpcs:
        for vpc in vpcs:
            iv = (mpc - vpc) % 12
            if iv == 0: total += 3
            elif iv in (3,4): total += 2
            elif iv in (5,7): total += 2
            elif iv in (8,9): total += 1
            elif iv in (1,11): total -= 3
            elif iv == 6: total -= 1
    return total / len(mpcs) if mpcs else 0

def transpose_voicing_notes(notes_str, key):
    KEY_OFF = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
               'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6}
    offset = 0
    for k, off in KEY_OFF.items():
        if k == key:
            for deg_name, deg_idx in {'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}.items():
                if SCALE_PC[deg_name] == off:
                    offset = deg_idx
                    break
            break
    return ''.join(NOTE_NAMES[(NOTE_NAMES.index(ch) + offset) % 7] for ch in notes_str if ch in NOTE_NAMES)

def voicing_to_abc(voicing, key, melody_midi):
    lh_notes = transpose_voicing_notes(voicing['lhNotes'], key)
    rh_notes = transpose_voicing_notes(voicing['rhNotes'], key)
    lh_pat = [int(x) for x in voicing['lhPat'].split('-')]
    rh_pat = [int(x) for x in voicing['rhPat'].split('-')]
    gap = voicing['gap']
    rh_span = sum(rh_pat)
    lh_span = sum(lh_pat)

    melody_oct = melody_midi // 12 - 1
    melody_pc = melody_midi % 12
    diatonic_in_oct = [0,0,1,1,2,3,3,4,4,5,5,6]
    melody_deg = diatonic_in_oct[melody_pc]
    melody_abs = melody_oct * 7 + melody_deg
    rh_top_abs = melody_abs - 2
    rh_bottom_abs = rh_top_abs - rh_span
    lh_top_abs = rh_bottom_abs - gap - 1
    lh_bottom_abs = lh_top_abs - lh_span
    first_note_idx = NOTE_NAMES.index(lh_notes[0]) if lh_notes[0] in NOTE_NAMES else 0
    base_abs = lh_bottom_abs

    def abs_to_abc(abs_pos):
        oct = abs_pos // 7
        deg = abs_pos % 7
        note = NOTE_NAMES[deg]
        if oct >= 5: return note.lower() + "'" * (oct - 5)
        elif oct == 4: return note
        else: return note + ',' * (4 - oct)

    lh_positions = [0]
    for p in lh_pat: lh_positions.append(lh_positions[-1] + p)
    rh_positions = [0]
    for p in rh_pat: rh_positions.append(rh_positions[-1] + p)

    lh_abc = ''.join(abs_to_abc(base_abs + p) for p in lh_positions)
    rh_abc = ''.join(abs_to_abc(rh_bottom_abs + p) for p in rh_positions)
    return lh_abc, rh_abc

def pitch_to_abc(pitch, quarter_length):
    """Convert music21 pitch to ABC note token."""
    name = pitch.step
    octave = pitch.octave if pitch.octave is not None else 4
    acc = ''
    if pitch.accidental:
        if pitch.accidental.alter == 1: acc = '^'
        elif pitch.accidental.alter == -1: acc = '_'
        elif pitch.accidental.alter == 2: acc = '^^'
        elif pitch.accidental.alter == -2: acc = '__'
        elif pitch.accidental.alter == 0: acc = '='
    if octave >= 5:
        abc = acc + name.lower() + "'" * (octave - 5)
    elif octave == 4:
        abc = acc + name
    else:
        abc = acc + name + ',' * (4 - octave)
    abc += duration_to_abc(quarter_length)
    return abc

def duration_to_abc(ql):
    """Convert quarter-note length to ABC duration suffix. L:1/4 assumed."""
    if ql == 1.0: return ''
    if ql == 0.5: return '/'
    if ql == 0.25: return '/4'
    if ql == 2.0: return '2'
    if ql == 3.0: return '3'
    if ql == 4.0: return '4'
    if ql == 1.5: return '3/2'
    if ql == 0.75: return '3/4'
    if ql == 6.0: return '6'
    if ql == 8.0: return '8'
    if ql == int(ql): return str(int(ql))
    from fractions import Fraction
    frac = Fraction(ql).limit_denominator(8)
    if frac.denominator == 1: return str(frac.numerator)
    return f'{frac.numerator}/{frac.denominator}'

# ── Parse hymns using music21 ──
print("Parsing OpenHymnal with music21...", file=sys.stderr)

abc_path = str(PROJECT_DIR / 'data/OpenHymnal.abc')

# Get list of tune numbers
with open(abc_path, encoding='utf-8') as f:
    text = f.read()
tune_numbers = [int(m.group(1)) for m in re.finditer(r'^X:\s*(\d+)', text, re.MULTILINE)]
print(f"Found {len(tune_numbers)} tunes", file=sys.stderr)

hymns = []
for ti, tnum in enumerate(tune_numbers):
    try:
        score = music21.converter.parse(abc_path, number=tnum)
    except Exception as e:
        print(f"  Skip X:{tnum}: {e}", file=sys.stderr)
        continue

    title = score.metadata.title or f"Hymn {tnum}"
    key_obj = score.analyze('key')
    key_name = key_obj.tonic.name.replace('-', 'b') if key_obj else 'C'

    ts_list = score.getTimeSignatures()
    meter = str(ts_list[0]) if ts_list else '4/4'
    meter_str = ts_list[0].ratioString if ts_list else '4/4'

    tempo_marks = score.flatten().getElementsByClass('MetronomeMark')
    tempo = int(tempo_marks[0].number) if tempo_marks else 100

    if not score.parts:
        continue

    part = score.parts[0]

    # Extract measures with notes
    measures = []
    for m in part.getElementsByClass('Measure'):
        m_notes = []
        m_midis = []
        m_abc_tokens = []
        has_acc = False
        total_ql = 0

        for n in m.recurse().getElementsByClass(['Note', 'Rest']):
            if isinstance(n, music21.note.Note):
                m_midis.append(n.pitch.midi)
                # Convert to ABC token
                abc_token = pitch_to_abc(n.pitch, n.duration.quarterLength)
                m_abc_tokens.append(abc_token)
                m_notes.append(abc_token)
                if n.pitch.accidental and n.pitch.accidental.alter != 0:
                    has_acc = True
                total_ql += n.duration.quarterLength
            elif isinstance(n, music21.note.Rest):
                dur_abc = duration_to_abc(n.duration.quarterLength)
                m_abc_tokens.append(f'z{dur_abc}')
                total_ql += n.duration.quarterLength

        if m_midis or m_abc_tokens:
            measures.append({
                'notes': m_abc_tokens,
                'midis': m_midis if m_midis else [67],
                'has_acc': has_acc,
                'beats': total_ql,  # in quarter-note beats
            })

    if not measures:
        continue

    hymns.append({
        'title': title, 'xnum': tnum, 'key': key_name,
        'meter': meter_str, 'tempo': tempo, 'measures': measures,
    })

    if (ti + 1) % 50 == 0:
        print(f"  Parsed {ti+1}/{len(tune_numbers)}...", file=sys.stderr)

print(f"Parsed {len(hymns)} hymns, {sum(len(h['measures']) for h in hymns)} measures", file=sys.stderr)




# ── Consonance scoring and voicing assignment (same as before) ──
KEY_OFF = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
           'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6}

all_measures = []
for hi, h in enumerate(hymns):
    for mi, m in enumerate(h['measures']):
        all_measures.append((hi, mi, m, h['key']))

total_m = len(all_measures)
print(f"Scoring {total_m} measures x {len(voicings)} voicings...", file=sys.stderr)

scores = []
for hi, mi, m, key in all_measures:
    ko = KEY_OFF.get(key, 0)
    mpcs = [n % 12 for n in m['midis']]
    row = []
    for vi, v in enumerate(voicings):
        tpcs = set((pc + ko) % 12 for pc in v['pcs'])
        row.append(con_score(tpcs, mpcs))
    scores.append(row)

# Two-pass assignment
measure_assigned = [None] * total_m
voicing_usage = defaultdict(list)
target_uses = total_m // len(voicings)

voicing_avg = [(vi, sum(scores[mi][vi] for mi in range(total_m)) / total_m) for vi in range(len(voicings))]
voicing_avg.sort(key=lambda x: x[1])

acc_measures = [i for i, (hi,mi,m,k) in enumerate(all_measures) if m['has_acc']]
for vi, avg in voicing_avg:
    if len(voicing_usage[vi]) >= target_uses: continue
    candidates = [(mi, scores[mi][vi]) for mi in acc_measures if measure_assigned[mi] is None]
    candidates.sort(key=lambda x: -x[1])
    for mi, sc in candidates[:target_uses - len(voicing_usage[vi])]:
        measure_assigned[mi] = vi
        voicing_usage[vi].append(mi)

for mi in range(total_m):
    if measure_assigned[mi] is not None: continue
    best_vi = None; best_score = -999
    for vi in range(len(voicings)):
        if len(voicing_usage[vi]) >= target_uses + 2: continue
        sc = scores[mi][vi] + (target_uses - len(voicing_usage[vi])) * 0.1
        if sc > best_score:
            best_score = sc; best_vi = vi
    if best_vi is not None:
        measure_assigned[mi] = best_vi
        voicing_usage[best_vi].append(mi)

print(f"Assigned {sum(1 for a in measure_assigned if a is not None)}/{total_m} measures", file=sys.stderr)

# ── Generate ABC output ──
hymn_assignments = defaultdict(list)
for flat_i, (hi, mi, m, key) in enumerate(all_measures):
    hymn_assignments[hi].append(measure_assigned[flat_i])

output = []
for hi, h in enumerate(hymns):
    assignments = hymn_assignments[hi]
    key = h['key']
    meter = h['meter']
    measures = h['measures']

    melody_parts = []
    rh_parts = []
    lh_parts = []
    chords = []
    note_idx = 0

    for mi, (m, vi) in enumerate(zip(measures, assignments)):
        v = voicings[vi] if vi is not None else voicings[0]
        beats = m['beats']
        melody_midi = m['midis'][0] if m['midis'] else 67

        lh_abc, rh_abc = voicing_to_abc(v, key, melody_midi)

        # Melody
        melody_parts.append(' '.join(m['notes']))

        # Chords with correct duration
        dur_abc = duration_to_abc(beats)
        rh_parts.append(f'[{rh_abc}]{dur_abc}')
        lh_parts.append(f'[{lh_abc}]{dur_abc}')

        # Chord fraction data
        rh_letters = ''.join(c.upper() for c in reversed(re.findall(r'[A-Ga-g]', rh_abc)))
        lh_letters = ''.join(c.upper() for c in reversed(re.findall(r'[A-Ga-g]', lh_abc)))
        chords.append({
            'beat': note_idx,
            'name': v['lh'],
            'rhn': v['rh'],
            'lhn': v['lh'],
            'rh': rh_letters,
            'lh': lh_letters,
        })
        note_idx += len(m['notes'])

    melody_line = ' | '.join(melody_parts) + ' |]'
    rh_line = ' | '.join(rh_parts) + ' |]'
    lh_line = ' | '.join(lh_parts) + ' |]'

    # Detect RH clef
    rh_notes_all = re.findall(r'[A-G][,\']*', rh_line)
    low_count = sum(1 for n in rh_notes_all if ',,' in n)
    rh_clef = 'bass' if low_count > len(rh_notes_all) * 0.3 else 'treble'

    abc = (
        f'X: {3000 + h["xnum"]}\n'
        f'T: {h["title"]}\n'
        f'M: {meter}\n'
        f'L: 1/4\n'
        f'%%pagewidth 200cm\n'
        f'%%continueall 1\n'
        f'%%leftmargin 0.5cm\n'
        f'%%rightmargin 0.5cm\n'
        f'%%topspace 0\n'
        f'%%musicspace 0\n'
        f'%%writefields Q 0\n'
        f'%%staves M | {{RH LH}}\n'
        f'V: M clef=treble name="Melody"\n'
        f'V: RH clef={rh_clef} name="RH"\n'
        f'V: LH clef=bass name="LH"\n'
        f'K: {key}\n'
        f'[V: M] [Q:1/4={h["tempo"]}] {melody_line}\n'
        f'[V: RH] {rh_line}\n'
        f'[V: LH] {lh_line}\n'
    )

    output.append({
        'n': str(3000 + h['xnum']),
        't': h['title'],
        'abc': abc,
        'chords': chords,
    })

outpath = PROJECT_DIR / 'abc2stripchart/hymnal_data.json'
with open(outpath, 'w') as f:
    json.dump(output, f, separators=(',',':'))
print(f"Wrote {len(output)} hymns to {outpath}", file=sys.stderr)

usage_counts = [len(voicing_usage[vi]) for vi in range(len(voicings))]
assigned_scores_list = [scores[mi][measure_assigned[mi]] for mi in range(total_m) if measure_assigned[mi] is not None]
dis = sum(1 for s in assigned_scores_list if s < 0)
print(f"Usage per voicing: {min(usage_counts)}-{max(usage_counts)}", file=sys.stderr)
print(f"Avg consonance: {sum(assigned_scores_list)/len(assigned_scores_list):.1f}", file=sys.stderr)
print(f"Dissonant: {dis} ({dis/len(assigned_scores_list)*100:.1f}%)", file=sys.stderr)
