#!/usr/bin/env python3
"""Build harp-trefoil-hymnal v3: extract soprano, identify chords from SATB.

1. Parse each voice (S1V1, S1V2, S2V1, S2V2) separately with music21
2. Use S1V1 as melody
3. At each beat, combine all 4 voices to identify the sounding chord
4. Match chord to trefoil voicing pool
5. Output ABC with melody + trefoil RH/LH chords
"""

import json
import sys
import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import music21

# Add handout to path for chord_name
sys.path.insert(0, str(Path(__file__).parent.parent / 'handout'))
from chord_name import best_name, roman_name

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent

# ── Load trefoil voicing table ──
with open(PROJECT_DIR / 'handout/trefoil_C.json') as f:
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
KEY_OFF = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
           'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6}

for v in voicings:
    v['pcs'] = set(SCALE_PC[ch] for ch in v['lhNotes']+v['rhNotes'] if ch in SCALE_PC)

# ── Helpers ──
_current_key_accidentals = {}  # set per hymn: {'F': 1.0, 'C': 1.0} etc.

def set_key_for_abc(key_name):
    """Set the current key so pitch_to_abc can omit key-signature accidentals."""
    global _current_key_accidentals
    import music21
    try:
        k = music21.key.Key(key_name)
        _current_key_accidentals = {p.step: p.accidental.alter for p in k.alteredPitches}
    except:
        _current_key_accidentals = {}

def pitch_to_abc(pitch, ql):
    name = pitch.step
    octave = pitch.octave if pitch.octave is not None else 4
    acc = ''
    if pitch.accidental:
        a = pitch.accidental.alter
        # Only write accidental if it differs from key signature
        key_acc = _current_key_accidentals.get(name, 0)
        if a != key_acc:
            if a == 1: acc = '^'
            elif a == -1: acc = '_'
            elif a == 2: acc = '^^'
            elif a == -2: acc = '__'
            elif a == 0: acc = '='  # natural cancels key sig
    if octave >= 5:
        abc = acc + name.lower() + "'" * (octave - 5)
    elif octave == 4:
        abc = acc + name
    else:
        abc = acc + name + ',' * (4 - octave)
    abc += dur_to_abc(ql)
    return abc

def dur_to_abc(ql):
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
    frac = Fraction(ql).limit_denominator(8)
    if frac.denominator == 1: return str(frac.numerator)
    return f'{frac.numerator}/{frac.denominator}'

def transpose_voicing_notes(notes_str, key):
    offset = 0
    for k, off in KEY_OFF.items():
        if k == key:
            for dn, di in {'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}.items():
                if SCALE_PC[dn] == off:
                    offset = di; break
            break
    return ''.join(NOTE_NAMES[(NOTE_NAMES.index(ch) + offset) % 7] for ch in notes_str if ch in NOTE_NAMES)

def voicing_to_abc(voicing, key, melody_midi):
    """Compute ABC from the voicing's actual string pattern and gap.
    Uses lhPat/rhPat intervals to build absolute diatonic positions,
    then transposes to the target key. Range: C, to d'."""
    lh_notes = list(transpose_voicing_notes(voicing['lhNotes'], key))
    rh_notes = list(transpose_voicing_notes(voicing['rhNotes'], key))
    lh_pat = [int(x) for x in voicing['lhPat'].split('-')]
    rh_pat = [int(x) for x in voicing['rhPat'].split('-')]
    gap = voicing['gap']

    # Build absolute diatonic positions from patterns
    # LH: start at position 0, each interval adds to position
    lh_positions = [0]
    for p in lh_pat:
        lh_positions.append(lh_positions[-1] + p)
    # RH: starts gap+1 above LH top
    rh_start = lh_positions[-1] + gap + 1
    rh_positions = [rh_start]
    for p in rh_pat:
        rh_positions.append(rh_positions[-1] + p)

    # Total span
    total_span = rh_positions[-1]

    # Center the voicing in the C, to d' range (23 strings: positions 0-22)
    # Position 0 = C,  position 7 = C  position 14 = c  position 21 = c'  position 22 = d'
    available = 22  # 0 to 22
    offset = (available - total_span) // 2  # center it
    offset = max(0, min(offset, available - total_span))  # clamp

    def pos_to_abc(note_letter, pos):
        """Convert a note letter + absolute diatonic position to ABC."""
        abs_pos = pos + offset
        octave = abs_pos // 7  # 0=C,, 1=C, 2=C 3=c etc
        # Map to handout octave system: +1 because position 0-6 = octave 1 (C, range)
        octave += 1
        name = note_letter
        if octave <= 0: return name + ',,' + ','*(-octave)
        elif octave == 1: return name + ','
        elif octave == 2: return name
        elif octave == 3: return name.lower()
        else: return name.lower() + "'" * (octave - 3)

    la = ''.join(pos_to_abc(lh_notes[i], lh_positions[i]) for i in range(len(lh_notes)))
    ra = ''.join(pos_to_abc(rh_notes[i], rh_positions[i]) for i in range(len(rh_notes)))
    return la, ra

def con_score(vpcs, mpcs):
    """Score consonance between voicing pitch classes and melody pitch classes.
    Higher = more consonant."""
    total = 0
    for mpc in mpcs:
        for vpc in vpcs:
            iv = (mpc - vpc) % 12
            if iv == 0: total += 3      # unison
            elif iv in (3,4): total += 2  # major/minor 3rd
            elif iv in (5,7): total += 2  # 4th/5th
            elif iv in (8,9): total += 1  # 6th
            elif iv in (1,11): total -= 3 # semitone clash
            elif iv == 6: total -= 1      # tritone
    return total / len(mpcs) if mpcs else 0

def acc_score(vpcs, mpcs, acc_pcs):
    """Score for accidental measures: favor voicings that compensate for
    the chromatic note by being consonant with the non-accidental melody
    notes and adding color that supports the accidental's tension."""
    base = con_score(vpcs, mpcs)
    # Bonus for voicings that contain the accidental pitch class
    # (supports the chromatic note rather than clashing)
    for apc in acc_pcs:
        for vpc in vpcs:
            iv = (apc - vpc) % 12
            if iv == 0: base += 2      # voicing contains the accidental
            elif iv in (3,4,5,7): base += 1  # consonant with accidental
            elif iv in (1,11): base -= 1     # semitone against accidental
    return base

# ── Parse OpenHymnal ──
print("Parsing OpenHymnal voices...", file=sys.stderr)

abc_path = str(PROJECT_DIR / 'data/OpenHymnal.abc')
with open(abc_path, encoding='utf-8') as f:
    text = f.read()

# Split into tunes
tune_chunks = {}
for m in re.finditer(r'(^X:\s*(\d+)\s*\n.*?)(?=^X:|\Z)', text, re.MULTILINE | re.DOTALL):
    tune_chunks[int(m.group(2))] = m.group(1)

print(f"Found {len(tune_chunks)} tunes", file=sys.stderr)

hymns = []
for ti, (tnum, chunk) in enumerate(sorted(tune_chunks.items())):
    # Extract header
    header_lines = []
    voice_music = {'S1V1':[], 'S1V2':[], 'S2V1':[], 'S2V2':[]}
    title = f"Hymn {tnum}"
    key = 'C'
    meter = '4/4'
    tempo = 100

    for line in chunk.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith('T:') and title == f"Hymn {tnum}":
            title = line_stripped[2:].strip()
        if line_stripped.startswith('M:'):
            meter = line_stripped[2:].split('%')[0].strip()
        if line_stripped.startswith('K:'):
            key = line_stripped[2:].split('%')[0].strip().split()[0]
            header_lines.append(line_stripped.split('%')[0].strip())
        if line_stripped.startswith(('X:', 'M:', 'L:')):
            header_lines.append(line_stripped.split('%')[0].strip())
        if line_stripped.startswith('Q:') or '[Q:' in line_stripped:
            qm = re.search(r'=(\d+)', line_stripped)
            if qm: tempo = int(qm.group(1))

        for v in voice_music:
            if f'[V: {v}]' in line_stripped:
                music = line_stripped[line_stripped.index(']')+1:].strip()
                music = re.sub(r'![^!]*!', '', music)
                music = re.sub(r'\[Q:[^\]]*\]', '', music)
                voice_music[v].append(music)

    if not voice_music['S1V1']:
        continue

    # Clean key (remove minor suffix for lookup)
    key_clean = key.replace('m','') if key.endswith('m') else key
    if key_clean not in KEY_OFF:
        key_clean = 'C'

    header = '\n'.join(header_lines)

    # Parse soprano with music21 for correct melody
    sop_abc = header + '\n' + ' '.join(voice_music['S1V1'])
    try:
        set_key_for_abc(key_clean)
        sop_score = music21.converter.parse(sop_abc, format='abc')
    except Exception as e:
        print(f"  Skip X:{tnum} soprano parse: {e}", file=sys.stderr)
        continue

    # Extract measures from soprano
    sop_part = sop_score.parts[0] if sop_score.parts else sop_score
    measures = []
    for m_obj in sop_part.getElementsByClass('Measure'):
        m_notes = []
        m_midis = []
        has_acc = False
        acc_pcs = []  # pitch classes of accidental notes
        total_ql = 0
        for n in m_obj.recurse().getElementsByClass(['Note', 'Rest']):
            if isinstance(n, music21.note.Note):
                m_midis.append(n.pitch.midi)
                m_notes.append(pitch_to_abc(n.pitch, n.duration.quarterLength))
                if n.pitch.accidental and n.pitch.accidental.alter != 0:
                    key_acc = _current_key_accidentals.get(n.pitch.step, 0)
                    if n.pitch.accidental.alter != key_acc:
                        has_acc = True
                        acc_pcs.append(n.pitch.midi % 12)
                total_ql += n.duration.quarterLength
            elif isinstance(n, music21.note.Rest):
                m_notes.append(f'z{dur_to_abc(n.duration.quarterLength)}')
                total_ql += n.duration.quarterLength
        if m_notes:
            measures.append({
                'notes': m_notes, 'midis': m_midis if m_midis else [67],
                'has_acc': has_acc, 'acc_pcs': acc_pcs, 'beats': total_ql,
            })

    if not measures:
        continue

    # Parse all 4 SATB voices for abstract chord extraction
    satb_parts = {}
    for vname in ['S1V1', 'S1V2', 'S2V1', 'S2V2']:
        if voice_music[vname]:
            vabc = header + '\n' + ' '.join(voice_music[vname])
            try:
                vsc = music21.converter.parse(vabc, format='abc')
                satb_parts[vname] = (vsc.parts[0] if vsc.parts else vsc)
            except:
                pass
    has_satb = len(satb_parts) == 4

    # Extract abstract chords per measure from SATB
    abstract_chords = []  # one roman_name per measure
    if has_satb:
        PC_TO_C = {0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A', 11:'B'}
        ko = KEY_OFF.get(key_clean, 0)
        satb_measures = {v: list(satb_parts[v].getElementsByClass('Measure')) for v in satb_parts}
        n_satb = min(len(satb_measures[v]) for v in satb_measures)
        for smi in range(n_satb):
            # Get pitch classes from all 4 voices at the first beat
            pitches_midi = []
            for v in ['S2V2', 'S2V1', 'S1V2', 'S1V1']:
                notes = list(satb_measures[v][smi].recurse().getElementsByClass('Note'))
                if notes:
                    pitches_midi.append(notes[0].pitch.midi)
            pcs = []; seen = set()
            for midi in sorted(pitches_midi):
                pc = (midi - ko) % 12
                if pc not in seen: seen.add(pc); pcs.append(pc)
            note_names = [PC_TO_C[pc] for pc in pcs if pc in PC_TO_C]
            if len(note_names) >= 3:
                try:
                    abstract_chords.append(roman_name(note_names))
                except:
                    abstract_chords.append('')
            else:
                abstract_chords.append('')

    hymns.append({
        'title': title, 'xnum': tnum, 'key': key_clean,
        'meter': meter, 'tempo': tempo, 'measures': measures,
        'abstract_chords': abstract_chords,
    })

    if (ti+1) % 50 == 0:
        print(f"  Parsed {ti+1}/{len(tune_chunks)}...", file=sys.stderr)

print(f"Parsed {len(hymns)} hymns, {sum(len(h['measures']) for h in hymns)} measures", file=sys.stderr)

# ── Voicing assignment (same two-pass as before) ──
all_measures = []
for hi, h in enumerate(hymns):
    for mi, m in enumerate(h['measures']):
        all_measures.append((hi, mi, m, h['key']))

total_m = len(all_measures)
print(f"Scoring {total_m} measures...", file=sys.stderr)

scores = []
for hi, mi, m, key in all_measures:
    ko = KEY_OFF.get(key, 0)
    mpcs = [n % 12 for n in m['midis']]
    if m['has_acc'] and m['acc_pcs']:
        # Use accidental-aware scoring that compensates for chromatic notes
        row = [acc_score(set((pc+ko)%12 for pc in v['pcs']), mpcs, m['acc_pcs']) for v in voicings]
    else:
        row = [con_score(set((pc+ko)%12 for pc in v['pcs']), mpcs) for v in voicings]
    scores.append(row)

measure_assigned = [None] * total_m
voicing_usage = defaultdict(list)
target_uses = max(1, total_m // len(voicings))

voicing_avg = sorted([(vi, sum(scores[mi][vi] for mi in range(total_m))/total_m) for vi in range(len(voicings))], key=lambda x: x[1])

acc_measures = [i for i,(h,m,md,k) in enumerate(all_measures) if md['has_acc']]
for vi, avg in voicing_avg:
    if len(voicing_usage[vi]) >= target_uses: continue
    cands = sorted([(mi, scores[mi][vi]) for mi in acc_measures if measure_assigned[mi] is None], key=lambda x: -x[1])
    for mi, sc in cands[:target_uses-len(voicing_usage[vi])]:
        measure_assigned[mi] = vi; voicing_usage[vi].append(mi)

for mi in range(total_m):
    if measure_assigned[mi] is not None: continue
    best_vi = None; best_sc = -999
    for vi in range(len(voicings)):
        if len(voicing_usage[vi]) >= target_uses+2: continue
        sc = scores[mi][vi] + (target_uses-len(voicing_usage[vi]))*0.1
        if sc > best_sc: best_sc = sc; best_vi = vi
    if best_vi is not None:
        measure_assigned[mi] = best_vi; voicing_usage[best_vi].append(mi)

print(f"Assigned {sum(1 for a in measure_assigned if a is not None)}/{total_m}", file=sys.stderr)

# ── Generate output ──
hymn_assignments = defaultdict(list)
for fi, (hi,mi,m,k) in enumerate(all_measures):
    hymn_assignments[hi].append(measure_assigned[fi])

output = []
for hi, h in enumerate(hymns):
    assignments = hymn_assignments[hi]
    key = h['key']; meter_str = h['meter']; measures = h['measures']

    mel_parts = []; rh_parts = []; lh_parts = []; chords = []
    note_idx = 0

    for mi, (m, vi) in enumerate(zip(measures, assignments)):
        v = voicings[vi] if vi is not None else voicings[0]
        beats = m['beats']
        melody_midi = m['midis'][0] if m['midis'] else 67

        lh_abc, rh_abc = voicing_to_abc(v, key, melody_midi)
        mel_parts.append(' '.join(m['notes']))
        d = dur_to_abc(beats)
        rh_parts.append(f'[{rh_abc}]{d}')
        lh_parts.append(f'[{lh_abc}]{d}')

        # Trefoil voicing names for LH and RH
        lh_name = best_name(list(v['lhNotes']))
        rh_name = best_name(list(v['rhNotes']))
        # Abstract chord from SATB (composer's chord)
        abs_chord = h['abstract_chords'][mi] if mi < len(h.get('abstract_chords', [])) else ''
        chords.append({'beat':note_idx,'abs':abs_chord,'rhn':rh_name,'lhn':lh_name})
        note_idx += len(m['notes'])

    mel_line = ' | '.join(mel_parts) + ' |]'
    rh_line = ' | '.join(rh_parts) + ' |]'
    lh_line = ' | '.join(lh_parts) + ' |]'

    rh_notes_all = re.findall(r'[A-G][,\']*', rh_line)
    low_count = sum(1 for n in rh_notes_all if ',,' in n)
    rh_clef = 'bass' if low_count > len(rh_notes_all)*0.3 else 'treble'

    abc = (
        f'X: {3000+h["xnum"]}\nT: {h["title"]}\nM: {meter_str}\nL: 1/4\n'
        f'%%pagewidth 200cm\n%%continueall 1\n%%leftmargin 0.5cm\n%%rightmargin 0.5cm\n'
        f'%%topspace 0\n%%musicspace 0\n%%writefields Q 0\n'
        f'%%staves M | {{RH LH}}\n'
        f'V: M clef=treble name="Melody"\nV: RH clef={rh_clef} name="RH"\nV: LH clef=bass name="LH"\n'
        f'K: {key}\n'
        f'[V: M] [Q:1/4={h["tempo"]}] {mel_line}\n'
        f'[V: RH] {rh_line}\n[V: LH] {lh_line}\n'
    )
    output.append({'n':str(3000+h['xnum']),'t':h['title'],'abc':abc,'chords':chords})

outpath = PROJECT_DIR / 'abc2stripchart/hymnal_data.json'
with open(outpath, 'w') as f:
    json.dump(output, f, separators=(',',':'))

usage = [len(voicing_usage[vi]) for vi in range(len(voicings))]
asc = [scores[mi][measure_assigned[mi]] for mi in range(total_m) if measure_assigned[mi] is not None]
dis = sum(1 for s in asc if s < 0)
print(f"Wrote {len(output)} hymns to {outpath}", file=sys.stderr)
print(f"Usage: {min(usage)}-{max(usage)}, Consonance: {sum(asc)/len(asc):.1f}, Dissonant: {dis} ({dis/len(asc)*100:.1f}%)", file=sys.stderr)
