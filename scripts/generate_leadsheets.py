#!/usr/bin/env python3
"""Generate 8 lead-sheet etudes, each with a distinct character.

Collectively covers all 85 cells of the chord table. Within a sheet, some
labels may repeat for musical phrasing (hymn-style, ballad tonic returns).

Outputs:
  handout/leadsheet1.html .. leadsheet8.html  — playable harpdrills-style
  handout/leadsheets.abc                       — combined ABC (8 tunes)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _etude_shared import generate_html, KEY_PC, KEY_ABC

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
KEY_LETTER = {-3: 2, -1: 6, 0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5}


# ═══════════════════════════════════════════════════════════════
# 8 lead sheets — chord progressions as (pattern, 0-based degree) cells
# ═══════════════════════════════════════════════════════════════

SHEETS = [
    {
        'n': 1, 'title': 'Hymn',
        'subtitle': 'Plain triads, root position',
        'meter': '4/4', 'beats_per_bar': 4,
        # ① ④ ⑤ ① ⑥m ③m ②m ⑦° ④ ⑤ ⑥m ①
        'cells': [
            ('33', 0), ('33', 3), ('33', 4), ('33', 0),
            ('33', 5), ('33', 2), ('33', 1), ('33', 6),
            ('33', 3), ('33', 4), ('33', 5), ('33', 0),
        ],
    },
    {
        'n': 2, 'title': 'Modal Drift',
        'subtitle': 'Sus voicings',
        'meter': '4/4', 'beats_per_bar': 4,
        # Is2 iis2 IVs2 Vs2 vis2 | Is4 iis4 iiis4 Vs4 vis4 | Is4+8 iis4+8 Vs4+8
        'cells': [
            ('24', 0), ('24', 1), ('24', 3), ('24', 4), ('24', 5),
            ('42', 0), ('42', 1), ('42', 2), ('42', 4), ('42', 5),
            ('424', 0), ('424', 1), ('424', 4),
        ],
    },
    {
        'n': 3, 'title': 'First-Inv Rounds',
        'subtitle': 'Triads in 1st and 2nd inversions',
        'meter': '4/4', 'beats_per_bar': 4,
        # +43 row (1st inv): IV¹ V¹ I¹ vi¹ ii¹ iii¹ vii°¹
        # +34 row (2nd inv): I² ii² iii² IV² V² vi² vii°²
        'cells': [
            ('43', 0), ('43', 1), ('43', 4), ('43', 2),
            ('43', 5), ('43', 6), ('43', 3),
            ('34', 2), ('34', 3), ('34', 4), ('34', 5),
            ('34', 6), ('34', 0), ('34', 1),
        ],
    },
    {
        'n': 4, 'title': 'Quartal / Open',
        'subtitle': 'Quartal stacks and quartal 7ths',
        'meter': '3/4', 'beats_per_bar': 3,
        # ②q ③q ⑤q ⑥q ⑦q | ②q7 ③q7 ⑥q7 ⑦q7
        'cells': [
            ('44', 1), ('44', 2), ('44', 4),
            ('44', 5), ('44', 6),
            ('444', 1), ('444', 2), ('444', 5), ('444', 6),
        ],
    },
    {
        'n': 5, 'title': 'Jazz Ballad',
        'subtitle': '7ths, root position',
        'meter': '4/4', 'beats_per_bar': 4,
        # IΔ iim7 iiim7 IVΔ V7 vim7 viiø7 IΔ iim7 V7 IΔ  (ballad with returns)
        'cells': [
            ('333', 0), ('333', 1), ('333', 2), ('333', 3),
            ('333', 4), ('333', 5), ('333', 6), ('333', 0),
            ('333', 1), ('333', 4), ('333', 0),
        ],
    },
    {
        'n': 6, 'title': 'Jazz Inversions',
        'subtitle': '7ths, 1st and 2nd inversions',
        'meter': '4/4', 'beats_per_bar': 4,
        # +233 row (1st inv): iim7¹ iiim7¹ IVΔ¹ V7¹ vim7¹ viiø7¹ IΔ¹
        # +323 row (2nd inv): IVΔ² V7² vim7² viiø7² IΔ² iim7² iiim7²
        'cells': [
            ('233', 0), ('233', 1), ('233', 2), ('233', 3),
            ('233', 4), ('233', 5), ('233', 6),
            ('323', 0), ('323', 1), ('323', 2), ('323', 3),
            ('323', 4), ('323', 5), ('323', 6),
        ],
    },
    {
        'n': 7, 'title': 'Sixths & Color',
        'subtitle': '6ths and 7th 3rd inversions, both voicing pairs',
        'meter': '4/4', 'beats_per_bar': 4,
        # +332 row: I6 iim6 IΔ³ IV6 V6 IVΔ³ V7³
        # +434 row: IV6¹ V6¹ IVΔ³(alt) V7³(alt) I6¹ iim6¹ IΔ³(alt)
        'cells': [
            ('332', 0), ('332', 1), ('332', 3), ('332', 4),
            ('332', 2), ('332', 5), ('332', 6),
            ('434', 0), ('434', 1), ('434', 4), ('434', 5),
            ('434', 6), ('434', 2), ('434', 3),
        ],
    },
    {
        'n': 8, 'title': 'Wide Open',
        'subtitle': 'Octave-doubled triads',
        'meter': '4/4', 'beats_per_bar': 4,
        # +334 row: I+8 ii+8 iii+8 IV+8 V+8 vi+8 vii°+8
        'cells': [
            ('334', 0), ('334', 1), ('334', 2), ('334', 3),
            ('334', 4), ('334', 5), ('334', 6),
        ],
    },
]


# ═══════════════════════════════════════════════════════════════
# Build an ETUDE list for a sheet: each beat plays one chord in both hands
# (LH at low octave, RH at high octave — natural doubling for harp practice)
# ═══════════════════════════════════════════════════════════════

def sheet_to_etude(sheet):
    """Return list of ETUDE entries — each has LH + RH playing the same cell."""
    entries = []
    for pat, deg in sheet['cells']:
        entries.append({'l': (pat, deg), 'r': (pat, deg)})
    return entries


# ═══════════════════════════════════════════════════════════════
# ABC generation: one tune per sheet, all combined in one file
# ═══════════════════════════════════════════════════════════════

_S = '\u2009'
CHORD_NAMES = {
    ('24',1):'\u2460s2',('24',2):'\u2461s2',('24',4):'\u2463s2',('24',5):'\u2464s2',('24',6):'\u2465s2',
    ('33',1):'\u2460',('33',2):'\u2461m',('33',3):'\u2462m',('33',4):'\u2463',('33',5):'\u2464',('33',6):'\u2465m',('33',7):'\u2466\u00b0',
    ('34',1):f'\u2465m{_S}\u00b2',('34',2):f'\u2466\u00b0{_S}\u00b2',('34',3):f'\u2460{_S}\u00b2',('34',4):f'\u2461m{_S}\u00b2',('34',5):f'\u2462m{_S}\u00b2',('34',6):f'\u2463{_S}\u00b2',('34',7):f'\u2464{_S}\u00b2',
    ('42',1):'\u2460s4',('42',2):'\u2461s4',('42',3):'\u2462s4',('42',5):'\u2464s4',('42',6):'\u2465s4',
    ('43',1):f'\u2463{_S}\u00b9',('43',2):f'\u2464{_S}\u00b9',('43',3):f'\u2465m{_S}\u00b9',('43',4):f'\u2466\u00b0{_S}\u00b9',('43',5):f'\u2460{_S}\u00b9',('43',6):f'\u2461m{_S}\u00b9',('43',7):f'\u2462m{_S}\u00b9',
    ('44',2):'\u2461q',('44',3):'\u2462q',('44',5):'\u2464q',('44',6):'\u2465q',('44',7):'\u2466q',
    ('233',1):f'\u2461m7{_S}\u00b9',('233',2):f'\u2462m7{_S}\u00b9',('233',3):f'\u2463\u0394{_S}\u00b9',('233',4):f'\u24647{_S}\u00b9',('233',5):f'\u2465m7{_S}\u00b9',('233',6):f'\u2466\u00f87{_S}\u00b9',('233',7):f'\u2460\u0394{_S}\u00b9',
    ('323',1):f'\u2463\u0394{_S}\u00b2',('323',2):f'\u24647{_S}\u00b2',('323',3):f'\u2465m7{_S}\u00b2',('323',4):f'\u2466\u00f87{_S}\u00b2',('323',5):f'\u2460\u0394{_S}\u00b2',('323',6):f'\u2461m7{_S}\u00b2',('323',7):f'\u2462m7{_S}\u00b2',
    ('332',1):'\u24606',('332',2):'\u2461m6',('332',3):f'\u2460\u0394{_S}\u00b3',('332',4):'\u24636',('332',5):'\u24646',('332',6):f'\u2463\u0394{_S}\u00b3',('332',7):f'\u24647{_S}\u00b3',
    ('333',1):'\u2460\u0394',('333',2):'\u2461m7',('333',3):'\u2462m7',('333',4):'\u2463\u0394',('333',5):'\u24647',('333',6):'\u2465m7',('333',7):'\u2466\u00f87',
    ('334',1):'\u2460+8',('334',2):'\u2461m+8',('334',3):'\u2462m+8',('334',4):'\u2463+8',('334',5):'\u2464+8',('334',6):'\u2465m+8',('334',7):'\u2466+8',
    ('424',1):'\u2460s4+8',('424',2):'\u2461s4+8',('424',5):'\u2464s4+8',
    ('434',1):f'\u24636{_S}\u00b9',('434',2):f'\u24646{_S}\u00b9',('434',3):f'\u2463\u0394{_S}\u00b3',('434',4):f'\u24647{_S}\u00b3',('434',5):f'\u24606{_S}\u00b9',('434',6):f'\u2461m6{_S}\u00b9',('434',7):f'\u2460\u0394{_S}\u00b3',
    ('444',2):'\u2461q7',('444',3):'\u2462q7',('444',6):'\u2465q7',('444',7):'\u2466q7',
}


def intervals_to_offsets(pat):
    offsets = [0]
    acc = 0
    for ch in pat:
        acc += int(ch) - 1
        offsets.append(acc)
    return offsets


def chord_midi(kpc, deg, pat, oct):
    return [12 * (oct + (deg + off) // 7 + 1) + kpc + MAJOR_SCALE[(deg + off) % 7]
            for off in intervals_to_offsets(pat)]


def pick_oct(kpc, deg, pat, prefer):
    valid = []
    for o in range(2, 6):
        midis = chord_midi(kpc, deg, pat, o)
        if all(36 <= m <= 91 for m in midis):
            valid.append((o, sum(midis) / len(midis)))
    if not valid:
        return 2 if prefer == 'low' else 4
    if prefer == 'low':
        below = [v for v in valid if v[1] <= 62]
        return (below[-1] if below else valid[0])[0]
    above = [v for v in valid if v[1] >= 58]
    return (above[0] if above else valid[-1])[0]


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
    if actual_oct == 4:
        return name
    if actual_oct == 5:
        return name.lower()
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


def build_tune_abc(sheet, tune_number, key_root):
    kpc = KEY_PC[key_root]
    key_name = KEY_ABC[key_root]
    bpb = sheet['beats_per_bar']

    # Build beat list with LH + RH voicings
    beats = []
    for (pat, deg) in sheet['cells']:
        lh_oct = pick_oct(kpc, deg, pat, 'low')
        rh_oct = pick_oct(kpc, deg, pat, 'high')
        # Ensure no crossing
        lh_midis = chord_midi(kpc, deg, pat, lh_oct)
        rh_midis = chord_midi(kpc, deg, pat, rh_oct)
        if max(lh_midis) >= min(rh_midis):
            # Shift one or the other
            if lh_oct > 2:
                lh_oct -= 1
                lh_midis = chord_midi(kpc, deg, pat, lh_oct)
            elif rh_oct < 5:
                rh_oct += 1
                rh_midis = chord_midi(kpc, deg, pat, rh_oct)
        beats.append({
            'lh_abc': midis_to_abc_chord(lh_midis, kpc, key_root),
            'rh_abc': midis_to_abc_chord(rh_midis, kpc, key_root),
            'label': label(pat, deg),
            'pat': pat, 'deg': deg,
        })

    # Pad to full measures
    while len(beats) % bpb != 0:
        beats.append({'lh_abc': 'z', 'rh_abc': 'z', 'label': '', 'pat': '', 'deg': None})
    num_measures = len(beats) // bpb

    lines = []
    lines.append(f'X:{tune_number}')
    lines.append(f'T:Sheet {sheet["n"]} — {sheet["title"]}')
    lines.append(f'T:({sheet["subtitle"]})')
    lines.append(f'M:{sheet["meter"]}')
    lines.append('L:1/4')
    lines.append(f'K:{key_name}')
    lines.append('%%score {1 2}')
    lines.append('V:1 clef=treble name="RH"')
    lines.append('V:2 clef=bass name="LH"')

    for m in range(num_measures):
        rh_bar = []
        lh_bar = []
        for b in range(bpb):
            idx = m * bpb + b
            bd = beats[idx]
            ann = f'"^{bd["label"]}"' if bd['label'] else ''
            pat_ann = f'"_{bd["deg"]+1}{bd["pat"]}"' if bd['deg'] is not None else ''
            rh_bar.append(ann + bd['rh_abc'])
            lh_bar.append(pat_ann + bd['lh_abc'])
        lines.append(f'[V:1] {" ".join(rh_bar)} |')
        lines.append(f'[V:2] {" ".join(lh_bar)} |')

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    key_root = -3  # Eb default
    if len(sys.argv) > 1:
        key_map = {'Eb': -3, 'Bb': -1, 'F': 5, 'C': 0, 'G': 7, 'D': 2, 'A': 9, 'E': 4}
        key_root = key_map.get(sys.argv[1], -3)

    handout_dir = os.path.join(os.path.dirname(__file__), '..', 'handout')

    # Generate 8 HTML files (one per sheet)
    for sheet in SHEETS:
        etude = sheet_to_etude(sheet)
        title = f'Sheet {sheet["n"]} — {sheet["title"]}: {sheet["subtitle"]}'
        html = generate_html(None, key_root, etude, title=title)
        path = os.path.join(handout_dir, f'leadsheet{sheet["n"]}.html')
        with open(path, 'w') as f:
            f.write(html)
        print(f'Written {path} ({len(sheet["cells"])} chords)')

    # Generate combined ABC with all 8 tunes
    all_abc = [
        '%%pagewidth 27.94cm',
        '%%pageheight 21.59cm',
        '%%topmargin 0.8cm',
        '%%botmargin 0.8cm',
        '%%leftmargin 1.2cm',
        '%%rightmargin 1.0cm',
        '%%scale 0.62',
        '%%staffsep 50',
        '%%sysstaffsep 20',
        '%%notespacingfactor 1.3',
        '%%gchordfont DejaVu Sans 13',
        '%%annotationfont DejaVu Sans 11',
        '%%composerfont DejaVu Sans 10',
        '%%titlefont DejaVu Sans 14',
        '%%barnumbers 0',
        '',
    ]
    for i, sheet in enumerate(SHEETS, 1):
        all_abc.append(build_tune_abc(sheet, i, key_root))
        all_abc.append('')

    abc_path = os.path.join(handout_dir, 'leadsheets.abc')
    with open(abc_path, 'w') as f:
        f.write('\n'.join(all_abc))
    print(f'Written {abc_path}')
    print(f'\nKey: {KEY_ABC[key_root]}')
