#!/usr/bin/env python3
"""Build the harp-trefoil-hymnal: 293 hymns with melody + trefoil RH/LH chords.

Two-pass voicing assignment:
  Pass 1: Place dissonant voicings in accidental measures
  Pass 2: Fill remaining with best consonant voicings

Output: JSON array of hymn entries for the abc2stripchart app.
"""

import re
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

# ── Load trefoil table ──
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
KEY_OFF = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
           'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6}
NOTE_NAMES = ['C','D','E','F','G','A','B']

for v in voicings:
    v['pcs'] = set(SCALE_PC[ch] for ch in v['lhNotes']+v['rhNotes'] if ch in SCALE_PC)

# ── ABC parsing ──
note_pat = re.compile(r'([_^=]*)([A-Ga-g])([\',]*)([\d/]*)')

def parse_dur(s):
    if not s or s == '/': return 0.5
    try:
        if s.startswith('/'):
            d = s[1:]
            return 1.0/float(d) if d else 0.5
        if '/' in s:
            p = s.split('/')
            return float(p[0])/float(p[1])
        return float(s)
    except: return 1.0

def parse_voice_fragment(music):
    """Parse a fragment of ABC music (no [V:] prefix) into notes."""
    notes = []
    for m in note_pat.finditer(music):
        acc = m.group(1)
        letter = m.group(2)
        mods = m.group(3)
        dur_str = m.group(4)
        oct = 4 if letter.isupper() else 5
        for ch in mods:
            if ch == ',': oct -= 1
            elif ch == "'": oct += 1
        midi = SCALE_PC[letter.upper()] + (oct+1)*12
        if '^' in acc: midi += acc.count('^')
        elif '_' in acc: midi -= acc.count('_')
        has_acc = bool(acc and acc != '=')
        notes.append((midi, parse_dur(dur_str), has_acc, letter + mods))
    return notes

def parse_voice(line):
    music = line[line.index(']')+1:] if ']' in line else line
    notes = []
    for m in note_pat.finditer(music):
        acc = m.group(1)
        letter = m.group(2)
        mods = m.group(3)
        dur_str = m.group(4)
        oct = 4 if letter.isupper() else 5
        for ch in mods:
            if ch == ',': oct -= 1
            elif ch == "'": oct += 1
        midi = SCALE_PC[letter.upper()] + (oct+1)*12
        if '^' in acc: midi += acc.count('^')
        elif '_' in acc: midi -= acc.count('_')
        has_acc = bool(acc and acc != '=')
        notes.append((midi, parse_dur(dur_str), has_acc, letter + mods))
    return notes

# ── Consonance scoring ──
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

# ── Transpose voicing notes to a key ──
def transpose_voicing_notes(notes_str, key):
    """Transpose C-major note letters to target key."""
    offset = 0
    for k, off in KEY_OFF.items():
        if k == key:
            # offset = number of scale degrees to shift
            # C=0, D=1, E=2, F=3, G=4, A=5, B=6
            degree_map = {'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}
            # Find which degree corresponds to this key's offset
            for deg_name, deg_idx in degree_map.items():
                if SCALE_PC[deg_name] == off:
                    offset = deg_idx
                    break
            break

    result = []
    for ch in notes_str:
        if ch in NOTE_NAMES:
            idx = NOTE_NAMES.index(ch)
            result.append(NOTE_NAMES[(idx + offset) % 7])
    return ''.join(result)

def voicing_to_abc(voicing, key, melody_midi):
    """Convert a trefoil voicing to ABC notation, anchored below the melody.

    Places the RH top note 2 strings below the melody note, then builds
    downward through RH pattern, gap, and LH pattern.

    Returns (lh_abc, rh_abc) strings for ABC block chords.
    """
    lh_notes = transpose_voicing_notes(voicing['lhNotes'], key)
    rh_notes = transpose_voicing_notes(voicing['rhNotes'], key)
    lh_pat = [int(x) for x in voicing['lhPat'].split('-')]
    rh_pat = [int(x) for x in voicing['rhPat'].split('-')]
    gap = voicing['gap']

    # Total span of the voicing in diatonic strings
    rh_span = sum(rh_pat)  # strings from RH bottom to RH top
    lh_span = sum(lh_pat)  # strings from LH bottom to LH top
    total_span = lh_span + gap + 1 + rh_span  # LH bottom to RH top

    # Melody note as absolute diatonic position
    # MIDI to diatonic: octave * 7 + degree
    melody_oct = melody_midi // 12 - 1
    melody_pc = melody_midi % 12
    diatonic_in_oct = [0,0,1,1,2,3,3,4,4,5,5,6]
    melody_deg = diatonic_in_oct[melody_pc]
    melody_abs = melody_oct * 7 + melody_deg

    # RH top note = 2 strings below melody (leave room for melody)
    rh_top_abs = melody_abs - 2

    # RH bottom = rh_top - rh_span
    rh_bottom_abs = rh_top_abs - rh_span

    # LH top = rh_bottom - gap - 1
    lh_top_abs = rh_bottom_abs - gap - 1

    # LH bottom = lh_top - lh_span
    lh_bottom_abs = lh_top_abs - lh_span

    def abs_to_abc(abs_pos):
        oct = abs_pos // 7
        deg = abs_pos % 7
        note = NOTE_NAMES[deg]
        if oct >= 5:
            return note.lower() + "'" * (oct - 5)
        elif oct == 4:
            return note
        else:
            return note + ',' * (4 - oct)

    # Build LH notes ascending from bottom
    lh_positions = [0]
    for p in lh_pat:
        lh_positions.append(lh_positions[-1] + p)
    lh_abc = ''.join(abs_to_abc(lh_bottom_abs + p) for p in lh_positions)

    # Build RH notes ascending from bottom
    rh_positions = [0]
    for p in rh_pat:
        rh_positions.append(rh_positions[-1] + p)
    rh_abc = ''.join(abs_to_abc(rh_bottom_abs + p) for p in rh_positions)

    return lh_abc, rh_abc

# ── Parse all hymns ──
with open(PROJECT_DIR / 'data/OpenHymnal.abc', encoding='utf-8') as f:
    text = f.read()

tunes_raw = text.split('\nX:')
hymns = []

for i, chunk in enumerate(tunes_raw):
    if i == 0:
        if 'X:' not in chunk: continue
        chunk = chunk[chunk.index('X:'):]
    else:
        chunk = 'X:' + chunk

    title_m = re.search(r'T:\s*(.+)', chunk)
    title = title_m.group(1).strip() if title_m else '?'
    xnum_m = re.search(r'X:\s*(\d+)', chunk)
    xnum = int(xnum_m.group(1)) if xnum_m else 0
    key_m = re.search(r'K:\s*(\S+)', chunk)
    key_raw = key_m.group(1).strip() if key_m else 'C'
    key = key_raw.replace('m','')  # strip minor mode for now
    if key not in KEY_OFF:
        key = 'C'
    meter_m = re.search(r'M:\s*(\S+)', chunk)
    meter = meter_m.group(1) if meter_m else '4/4'
    tempo_m = re.search(r'Q:\s*\S+=(\d+)', chunk)
    tempo = int(tempo_m.group(1)) if tempo_m else 100
    # Beats per measure in the source ABC's unit length (typically 1/8 or 1/4)
    bpm_source = {'3/4':3, '6/8':6, '2/4':2, '2/2':2, '3/8':3, '6/4':6, '3/2':3, '9/8':9, '8/4':8}.get(meter, 4)
    # Our output uses L:1/4, so convert to quarter-note beats
    # For meters with /8 denominator, each source beat = half a quarter note
    # For meters with /4, source beats = quarter notes already
    # For meters with /2, source beats = 2 quarter notes each
    if '/8' in meter:
        bpm_quarter = bpm_source / 2  # 6/8 -> 3 quarter beats
    elif '/2' in meter:
        bpm_quarter = bpm_source * 2  # 3/2 -> 6 quarter beats
    else:
        bpm_quarter = bpm_source      # 4/4 -> 4 quarter beats
    bpm = bpm_source  # for source note grouping

    # Parse soprano melody — preserve original barlines
    soprano_lines = []
    for line in chunk.split('\n'):
        if '[V: S1V1]' in line:
            soprano_lines.append(line)
    if not soprano_lines: continue

    # Split by barlines to get measures, then parse each measure's notes
    measures = []
    for sop_line in soprano_lines:
        music = sop_line[sop_line.index(']')+1:] if ']' in sop_line else sop_line
        # Remove inline tempo
        music = re.sub(r'\[Q:[^\]]*\]\s*', '', music)
        # Remove decorations
        music = re.sub(r'![^!]*!', '', music)
        # Split on barlines
        bar_parts = re.split(r'\|+\]?', music)
        for part in bar_parts:
            part = part.strip()
            if not part: continue
            notes = parse_voice_fragment(part)
            if notes:
                m_notes = [n[3] for n in notes]  # abc_note tokens
                m_midis = [n[0] for n in notes]  # midi values
                m_acc = any(n[2] for n in notes)  # has accidental
                # Duration: sum of all note durations in this measure
                total_dur = sum(n[1] for n in notes)
                # Convert to quarter-note beats for chord duration
                if '/8' in meter:
                    chord_beats = total_dur / 2
                elif '/2' in meter:
                    chord_beats = total_dur * 2
                else:
                    chord_beats = total_dur
                measures.append({'notes': m_notes, 'midis': m_midis, 'has_acc': m_acc, 'beats': chord_beats})
    if not measures: continue

    hymns.append({
        'title': title, 'xnum': xnum, 'key': key, 'meter': meter,
        'tempo': tempo, 'measures': measures, 'raw_chunk': chunk,
    })

print(f"Parsed {len(hymns)} hymns, {sum(len(h['measures']) for h in hymns)} measures", file=sys.stderr)

# ── Build flat measure list and score matrix ──
all_measures = []
for hi, h in enumerate(hymns):
    for mi, m in enumerate(h['measures']):
        all_measures.append((hi, mi, m, h['key']))

total_m = len(all_measures)
scores = []
for hi, mi, m, key in all_measures:
    ko = KEY_OFF.get(key, 0)
    mpcs = [n % 12 for n in m['midis']]
    row = []
    for vi, v in enumerate(voicings):
        tpcs = set((pc + ko) % 12 for pc in v['pcs'])
        row.append(con_score(tpcs, mpcs))
    scores.append(row)

# ── Two-pass assignment ──
measure_assigned = [None] * total_m
voicing_usage = defaultdict(list)
target_uses = total_m // len(voicings)

# Sort voicings by average consonance (most dissonant first)
voicing_avg = [(vi, sum(scores[mi][vi] for mi in range(total_m)) / total_m) for vi in range(len(voicings))]
voicing_avg.sort(key=lambda x: x[1])

# Pass 1: dissonant voicings in accidental measures
acc_measures = [i for i, (hi,mi,m,k) in enumerate(all_measures) if m['has_acc']]
for vi, avg in voicing_avg:
    if len(voicing_usage[vi]) >= target_uses: continue
    candidates = [(mi, scores[mi][vi]) for mi in acc_measures if measure_assigned[mi] is None]
    candidates.sort(key=lambda x: -x[1])
    for mi, sc in candidates[:target_uses - len(voicing_usage[vi])]:
        measure_assigned[mi] = vi
        voicing_usage[vi].append(mi)

# Pass 2: fill remaining
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

# ── Generate ABC for each hymn ──
def build_melody_abc(soprano_notes, key, meter):
    """Build melody voice ABC from raw soprano note tokens."""
    # Re-extract from raw chunk to preserve original notation
    return ' '.join(soprano_notes)

def generate_hymn_abc(hymn, hymn_measures_assigned):
    """Generate 3-voice ABC for a hymn."""
    key = hymn['key']
    meter = hymn['meter']
    measures = hymn['measures']

    # Build melody line from original soprano
    melody_parts = []
    for m in measures:
        melody_parts.append(' '.join(m['notes']))
    melody_line = ' | '.join(melody_parts) + ' |]'

    # Build RH and LH chord lines
    rh_parts = []
    lh_parts = []

    measure_voicing_data = []  # (lh_letters, rh_letters, voicing) per measure
    import re as _re

    # Track RH clef state for inline changes
    # Determine register of each measure's RH notes
    # If RH bottom note is below C4 (has comma), it's "low"
    # If RH top note is above B4 (lowercase), it's "high"
    rh_registers = []  # 'treble', 'bass', or '8vb' per measure

    for mi, (m, vi) in enumerate(zip(measures, hymn_measures_assigned)):
        v = voicings[vi] if vi is not None else voicings[0]
        beats = m['beats']

        melody_midi = m['midis'][0] if m['midis'] else 67
        lh_abc, rh_abc = voicing_to_abc(v, key, melody_midi)

        # Determine RH register from the ABC notes
        rh_note_tokens = _re.findall(r'[A-Ga-g][,\']*', rh_abc)
        has_double_comma = any(',,' in n for n in rh_note_tokens)
        has_comma = any(',' in n for n in rh_note_tokens)
        has_lowercase = any(n[0].islower() for n in rh_note_tokens)

        if has_double_comma:
            # Very low — notes at octave 2 or below, use bass clef
            rh_registers.append('bass')
        elif has_comma and not has_lowercase:
            # Low — notes in octave 3, use 8vb (treble clef reads octave lower)
            rh_registers.append('8vb')
        else:
            # Normal treble range
            rh_registers.append('treble')

        rh_parts.append((rh_abc, int(beats)))
        lh_parts.append(f'[{lh_abc}]{int(beats)}')

        rh_letters = ''.join(c.upper() for c in reversed(_re.findall(r'[A-Ga-g]', rh_abc)))
        lh_letters = ''.join(c.upper() for c in reversed(_re.findall(r'[A-Ga-g]', lh_abc)))
        measure_voicing_data.append((lh_letters, rh_letters, v))

    # Build RH line with inline clef changes and 8vb markings
    rh_line_parts = []
    current_clef = 'treble'  # starting clef
    in_8vb = False

    for mi, (rh_abc_dur, reg) in enumerate(zip(rh_parts, rh_registers)):
        rh_abc, beats = rh_abc_dur
        prefix = ''

        if reg == 'bass' and current_clef != 'bass':
            # Close 8vb if active
            if in_8vb:
                prefix += '!8vb)! '
                in_8vb = False
            prefix += '[K: clef=bass] '
            current_clef = 'bass'
        elif reg == '8vb' and current_clef == 'treble' and not in_8vb:
            prefix += '!8vb(! '
            in_8vb = True
        elif reg == '8vb' and current_clef == 'bass':
            # Switch back to treble with 8vb
            prefix += '[K: clef=treble] !8vb(! '
            current_clef = 'treble'
            in_8vb = True
        elif reg == 'treble' and current_clef == 'bass':
            prefix += '[K: clef=treble] '
            current_clef = 'treble'
        elif reg == 'treble' and in_8vb:
            prefix += '!8vb)! '
            in_8vb = False

        rh_line_parts.append(f'{prefix}[{rh_abc}]{beats}')

    # Close any open 8vb
    if in_8vb:
        rh_line_parts[-1] += ' !8vb)!'

    rh_line = ' | '.join(rh_line_parts) + ' |]'
    lh_line = ' | '.join(lh_parts) + ' |]'

    # Starting clef for the voice declaration
    rh_clef = rh_registers[0] if rh_registers else 'treble'
    if rh_clef == '8vb':
        rh_clef = 'treble'  # 8vb is handled by decoration, not clef

    abc = (
        f'X: {3000 + hymn["xnum"]}\n'
        f'T: {hymn["title"]}\n'
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
        f'[V: M] [Q:1/4={hymn["tempo"]}] {melody_line}\n'
        f'[V: RH] {rh_line}\n'
        f'[V: LH] {lh_line}\n'
    )
    return {'abc': abc, 'voicing_data': measure_voicing_data}

# ── Build output ──
# Group assignments by hymn
hymn_assignments = defaultdict(list)
for flat_i, (hi, mi, m, key) in enumerate(all_measures):
    hymn_assignments[hi].append(measure_assigned[flat_i])

# Generate all hymn entries
output = []
for hi, h in enumerate(hymns):
    assignments = hymn_assignments[hi]
    abc_result = generate_hymn_abc(h, assignments)
    abc = abc_result['abc']

    # Build chord fraction data using the ABC-derived note letters
    chords = []
    note_idx = 0
    for mi, vi in enumerate(assignments):
        if vi is not None and mi < len(abc_result['voicing_data']):
            v = voicings[vi]
            lh_letters, rh_letters, _ = abc_result['voicing_data'][mi]
            chords.append({
                'beat': note_idx,
                'name': v['lh'],  # composer's chord (terse name)
                'rhn': v['rh'],   # RH terse name
                'lhn': v['lh'],   # LH terse name
                'rh': rh_letters,
                'lh': lh_letters,
            })
        note_idx += len(h['measures'][mi]['notes'])

    output.append({
        'n': str(3000 + h['xnum']),
        't': h['title'],
        'abc': abc,
        'chords': chords,
    })

# Write output
outpath = PROJECT_DIR / 'abc2stripchart/hymnal_data.json'
with open(outpath, 'w') as f:
    json.dump(output, f, separators=(',',':'))
print(f"Wrote {len(output)} hymns to {outpath}", file=sys.stderr)

# Also write a summary
print(f"\n=== Harp Trefoil Hymnal ===")
print(f"Hymns: {len(output)}")
print(f"Total measures: {total_m}")
print(f"Voicings used: {len(voicings)}")
print(f"Usage per voicing: {min(len(voicing_usage[vi]) for vi in range(len(voicings)))}-{max(len(voicing_usage[vi]) for vi in range(len(voicings)))}")
assigned_scores_list = [scores[mi][measure_assigned[mi]] for mi in range(total_m) if measure_assigned[mi] is not None]
dis = sum(1 for s in assigned_scores_list if s < 0)
print(f"Avg consonance: {sum(assigned_scores_list)/len(assigned_scores_list):.1f}")
print(f"Dissonant assignments: {dis} ({dis/len(assigned_scores_list)*100:.1f}%)")
