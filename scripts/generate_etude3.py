#!/usr/bin/env python3
"""Generate the chord table etude as ABC → HTML (one-page sheet music)."""

import os, sys

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
KEY_LETTER = {-3:2, -1:6, 0:0, 2:1, 4:2, 5:3, 7:4, 9:5}
# Correct pitch classes for MIDI (the select values -3,-1 are wrong for MIDI)
KEY_PC = {-3:3, -1:10, 0:0, 2:2, 4:4, 5:5, 7:7, 9:9}
KEY_ABC = {-3:'Eb', -1:'Bb', 0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A'}

_S = '\u2009'
CHORD_NAMES = {
    ('24',1):'①s2',('24',2):'②s2',('24',4):'④s2',('24',5):'⑤s2',('24',6):'⑥s2',
    ('33',1):'①',('33',2):'②m',('33',3):'③m',('33',4):'④',('33',5):'⑤',('33',6):'⑥m',('33',7):'⑦°',
    ('34',1):f'⑥m²',('34',2):f'⑦°²',('34',3):f'①²',('34',4):f'②m²',('34',5):f'③m²',('34',6):f'④²',('34',7):f'⑤²',
    ('42',1):'①s4',('42',2):'②s4',('42',3):'③s4',('42',5):'⑤s4',('42',6):'⑥s4',
    ('43',1):f'④¹',('43',2):f'⑤¹',('43',3):f'⑥m¹',('43',4):f'⑦°¹',('43',5):f'①¹',('43',6):f'②m¹',('43',7):f'③m¹',
    ('44',2):'②q',('44',3):'③q',('44',5):'⑤q',('44',6):'⑥q',('44',7):'⑦q',
    ('233',1):f'②m7¹',('233',2):f'③m7¹',('233',3):f'④Δ¹',('233',4):f'⑤7¹',('233',5):f'⑥m7¹',('233',6):f'⑦ø7¹',('233',7):f'①Δ¹',
    ('323',1):f'④Δ²',('323',2):f'⑤7²',('323',3):f'⑥m7²',('323',4):f'⑦ø7²',('323',5):f'①Δ²',('323',6):f'②m7²',('323',7):f'③m7²',
    ('332',1):'①6',('332',2):'②m6',('332',3):f'①Δ³',('332',4):'④6',('332',5):'⑤6',('332',6):f'④Δ³',('332',7):f'⑤7³',
    ('333',1):'①Δ',('333',2):'②m7',('333',3):'③m7',('333',4):'④Δ',('333',5):'⑤7',('333',6):'⑥m7',('333',7):'⑦ø7',
    ('334',1):'①+8',('334',2):'②m+8',('334',3):'③m+8',('334',4):'④+8',('334',5):'⑤+8',('334',6):'⑥m+8',('334',7):'⑦+8',
    ('424',1):'①s4+8',('424',2):'②s4+8',('424',5):'⑤s4+8',
    ('434',1):f'④6¹',('434',2):f'⑤6¹',('434',3):f'④Δ³',('434',4):f'⑤7³',('434',5):f'①6¹',('434',6):f'②m6¹',('434',7):f'①Δ³',
    ('444',2):'②q7',('444',3):'③q7',('444',6):'⑥q7',('444',7):'⑦q7',
}

# ETUDE3: Strictly alternating LH/RH (odd beats=LH, even=RH).
# Each beat plays a DIFFERENT chord in just one hand.
# Within each round, chord roots follow the circle of fifths: 1→4→7→3→6→2→5.
# 85 beats covering all 85 cells exactly once.
ETUDE = [
    # ── Round 1: Triads root pos (+33) ──
    {'l':('33',0)}, {'r':('33',3)}, {'l':('33',6)}, {'r':('33',2)},
    {'l':('33',5)}, {'r':('33',1)}, {'l':('33',4)},
    # ── Round 2: Triads 1st inv (+43) ──
    {'r':('43',4)}, {'l':('43',0)}, {'r':('43',3)}, {'l':('43',6)},
    {'r':('43',2)}, {'l':('43',5)}, {'r':('43',1)},
    # ── Round 3: Triads 2nd inv (+34) ──
    {'l':('34',2)}, {'r':('34',5)}, {'l':('34',1)}, {'r':('34',4)},
    {'l':('34',0)}, {'r':('34',3)}, {'l':('34',6)},
    # ── Round 4: Triads +8 doubled (+334) ──
    {'r':('334',0)}, {'l':('334',3)}, {'r':('334',6)}, {'l':('334',2)},
    {'r':('334',5)}, {'l':('334',1)}, {'r':('334',4)},
    # ── Round 5: 7ths root pos (+333) ──
    {'l':('333',0)}, {'r':('333',3)}, {'l':('333',6)}, {'r':('333',2)},
    {'l':('333',5)}, {'r':('333',1)}, {'l':('333',4)},
    # ── Round 6: 7ths 1st inv (+233) ──
    {'r':('233',6)}, {'l':('233',2)}, {'r':('233',5)}, {'l':('233',1)},
    {'r':('233',4)}, {'l':('233',0)}, {'r':('233',3)},
    # ── Round 7: 7ths 2nd inv (+323) ──
    {'l':('323',4)}, {'r':('323',0)}, {'l':('323',3)}, {'r':('323',6)},
    {'l':('323',2)}, {'r':('323',5)}, {'l':('323',1)},
    # ── Round 8: 7ths 3rd inv + 6ths (+332) ──
    {'r':('332',0)}, {'l':('332',3)}, {'r':('332',6)}, {'l':('332',2)},
    {'r':('332',5)}, {'l':('332',1)}, {'r':('332',4)},
    # ── Round 9: 7th/6th alt inv (+434) ──
    {'l':('434',4)}, {'r':('434',0)}, {'l':('434',3)}, {'r':('434',6)},
    {'l':('434',2)}, {'r':('434',5)}, {'l':('434',1)},
    # ── Round 10: Sus2 (+24) — 5 cells ──
    {'r':('24',0)}, {'l':('24',3)}, {'r':('24',5)}, {'l':('24',1)}, {'r':('24',4)},
    # ── Round 11: Sus4 (+42) — 5 cells ──
    {'l':('42',0)}, {'r':('42',2)}, {'l':('42',5)}, {'r':('42',1)}, {'l':('42',4)},
    # ── Round 12: Sus4+8 (+424) — 3 cells ──
    {'r':('424',0)}, {'l':('424',1)}, {'r':('424',4)},
    # ── Round 13: Quartal (+44) — 5 cells ──
    {'l':('44',6)}, {'r':('44',2)}, {'l':('44',5)}, {'r':('44',1)}, {'l':('44',4)},
    # ── Round 14: Quartal 7ths (+444) — 4 cells ──
    {'r':('444',6)}, {'l':('444',2)}, {'r':('444',5)}, {'l':('444',1)},
]

def intervals_to_offsets(pat):
    offsets = [0]; acc = 0
    for ch in pat:
        acc += int(ch) - 1; offsets.append(acc)
    return offsets

def chord_midi(kpc, deg, pat, oct):
    return [12*(oct + (deg+off)//7 + 1) + kpc + MAJOR_SCALE[(deg+off)%7]
            for off in intervals_to_offsets(pat)]

def pick_oct(kpc, deg, pat, prefer):
    valid = []
    for o in range(2, 6):
        midis = chord_midi(kpc, deg, pat, o)
        if all(36 <= m <= 91 for m in midis):
            avg = sum(midis)/len(midis)
            valid.append((o, avg))
    if not valid:
        return 2 if prefer == 'low' else 4
    if prefer == 'low':
        below = [v for v in valid if v[1] <= 62]
        return (below[-1] if below else valid[0])[0]
    else:
        above = [v for v in valid if v[1] >= 58]
        return (above[0] if above else valid[-1])[0]

def fix_crossing(lh_midi, rh_midi, kpc, lh_pat, lh_deg, rh_pat, rh_deg, lh_oct, rh_oct):
    for _ in range(4):
        if not lh_midi or not rh_midi:
            break
        if max(lh_midi) < min(rh_midi):
            break
        new_lo = lh_oct - 1
        test = chord_midi(kpc, lh_deg, lh_pat, new_lo)
        if new_lo >= 2 and all(36 <= m <= 91 for m in test):
            lh_oct = new_lo
            lh_midi = test
            continue
        new_hi = rh_oct + 1
        test = chord_midi(kpc, rh_deg, rh_pat, new_hi)
        if new_hi <= 5 and all(36 <= m <= 91 for m in test):
            rh_oct = new_hi
            rh_midi = test
            continue
        break
    return lh_midi, rh_midi, lh_oct, rh_oct

def midi_to_abc(midi, kpc, key_root):
    pc = midi % 12
    actual_oct = midi // 12 - 1
    scale_pcs = [(kpc + s) % 12 for s in MAJOR_SCALE]
    if pc not in scale_pcs:
        return '?'
    deg = scale_pcs.index(pc)
    rl = KEY_LETTER[key_root]
    li = (rl + deg) % 7
    name = 'CDEFGAB'[li]
    if actual_oct <= 3:
        return name + ',' * (4 - actual_oct)
    elif actual_oct == 4:
        return name
    elif actual_oct == 5:
        return name.lower()
    else:
        return name.lower() + "'" * (actual_oct - 5)

def midis_to_abc_chord(midis, kpc, key_root):
    if not midis:
        return 'z'
    notes = [midi_to_abc(m, kpc, key_root) for m in sorted(midis)]
    if any(n == '?' for n in notes):
        return 'z'
    if len(notes) == 1:
        return notes[0]
    return '[' + ''.join(notes) + ']'

def label(pat, deg_0based):
    return CHORD_NAMES.get((pat, deg_0based + 1), '?')

def generate_abc(key_root=7):
    kpc = KEY_PC[key_root]
    key_name = KEY_ABC[key_root]

    rh_notes = []  # list of (abc_chord_str, annotation_above)
    lh_notes = []  # list of (abc_chord_str, annotation_below)

    for beat in ETUDE:
        has_l = 'l' in beat
        has_r = 'r' in beat
        lp, ld = beat.get('l', (None, None)) if has_l else (None, None)
        rp, rd = beat.get('r', (None, None)) if has_r else (None, None)
        # Handle tuple unpacking for cells
        if has_l:
            lp, ld = beat['l']
        if has_r:
            rp, rd = beat['r']

        # Pick octaves
        lh_oct = pick_oct(kpc, ld, lp, 'low') if has_l else None
        rh_oct = pick_oct(kpc, rd, rp, 'high') if has_r else None

        # Compute MIDI
        lh_midi = chord_midi(kpc, ld, lp, lh_oct) if has_l else []
        rh_midi = chord_midi(kpc, rd, rp, rh_oct) if has_r else []

        # Fix crossing
        if has_l and has_r:
            lh_midi, rh_midi, lh_oct, rh_oct = fix_crossing(
                lh_midi, rh_midi, kpc, lp, ld, rp, rd, lh_oct, rh_oct)

        # Convert to ABC
        rh_abc = midis_to_abc_chord(rh_midi, kpc, key_root)
        lh_abc = midis_to_abc_chord(lh_midi, kpc, key_root)

        # Annotations — RH label on top, LH label below (two separate annotations)
        rl = label(rp, rd) if has_r else ''
        ll = label(lp, ld) if has_l else ''
        # Pattern annotation: <degree><pattern>, RH on top, LH below (1-based degree)
        rp_str = f'{rd+1}{rp}' if has_r else ''
        lp_str = f'{ld+1}{lp}' if has_l else ''
        if rp_str and lp_str:
            pat_ann = f'{rp_str}\\n{lp_str}'
        else:
            pat_ann = rp_str or lp_str

        rh_notes.append((rh_abc, rl, ll))
        lh_notes.append((lh_abc, pat_ann))

    # Pad to full measures (multiple of 4)
    while len(rh_notes) % 4 != 0:
        rh_notes.append(('z', '', ''))
        lh_notes.append(('z', ''))

    num_measures = len(rh_notes) // 4

    # Build ABC
    lines = []
    lines.append('X:1')
    lines.append('T:Chord Table Etude — 85 Voicings')
    lines.append(f'T:Key of {key_name}')
    lines.append('M:4/4')
    lines.append('L:1/4')
    lines.append(f'K:{key_name}')
    lines.append('%%score {1 2}')
    lines.append('%%pagewidth 27.94cm')
    lines.append('%%pageheight 21.59cm')
    lines.append('%%topmargin 0.7cm')
    lines.append('%%botmargin 0.7cm')
    lines.append('%%leftmargin 1.0cm')
    lines.append('%%rightmargin 1.0cm')
    lines.append('%%scale 0.85')
    lines.append('%%staffsep 60')
    lines.append('%%sysstaffsep 25')
    lines.append('%%barsperstaff 5')
    lines.append('%%notespacingfactor 1.6')
    lines.append('%%gchordfont DejaVu Sans 16')
    lines.append('%%annotationfont DejaVu Sans 14')
    lines.append('%%barnumbers 0')
    lines.append('V:1 clef=treble name="RH"')
    lines.append('V:2 clef=bass name="LH"')

    # Track sections for rehearsal marks
    prev_section = ''

    # Generate measures
    for m in range(num_measures):
        # RH voice
        rh_bar = []
        for b in range(4):
            idx = m * 4 + b
            note, rh_label, lh_label = rh_notes[idx]
            prefix = ''
            # Stacked chord fraction: RH on top, LH below, single annotation with \n
            if rh_label and lh_label:
                prefix = f'"^{rh_label}\\n{lh_label}"'
            elif rh_label:
                prefix = f'"^{rh_label}"'
            elif lh_label:
                prefix = f'"^{lh_label}"'
            rh_bar.append(prefix + note)
        lines.append(f'[V:1] {" ".join(rh_bar)} |')

        # LH voice with pattern annotations below
        lh_bar = []
        for b in range(4):
            idx = m * 4 + b
            note, pat = lh_notes[idx]
            prefix = f'"_{pat}"' if pat else ''
            lh_bar.append(prefix + note)
        lines.append(f'[V:2] {" ".join(lh_bar)} |')

    return '\n'.join(lines)

from _etude_shared import generate_html as _shared_generate_html
def generate_html(abc_text, key_root=7):
    return _shared_generate_html(abc_text, key_root, ETUDE, title='Etude (v3)')

if __name__ == '__main__':
    key_root = 7  # G major default
    if len(sys.argv) > 1:
        key_map = {'Eb':-3,'Bb':-1,'F':5,'C':0,'G':7,'D':2,'A':9,'E':4}
        key_root = key_map.get(sys.argv[1], 7)

    abc = generate_abc(key_root)

    abc_path = os.path.join(os.path.dirname(__file__), '..', 'handout', 'etude3.abc')
    with open(abc_path, 'w') as f:
        f.write(abc)
    print(f'Written {abc_path}')

    html_path = os.path.join(os.path.dirname(__file__), '..', 'handout', 'etude3.html')
    with open(html_path, 'w') as f:
        f.write(generate_html(abc, key_root))
    print(f'Written {html_path}')

    # Print stats
    print(f'Key: {KEY_ABC[key_root]}, Beats: {len(ETUDE)}, Measures: {(len(ETUDE)+3)//4}')
