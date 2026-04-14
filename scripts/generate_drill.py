#!/usr/bin/env python3
# generate_drill.py
# Generates ABC notation drill for diatonic harp chord table
# Eb major tuning, 33 strings starting C2
# Each measure: 3x run up and down for one pattern address

NOTES_PER_OCT = ['C','D','E','F','G','A','B']  # K:Eb, flats implicit

PAT_MAP = {
    "24":(2,4),"33":(3,3),"34":(3,4),"42":(4,2),"43":(4,3),"44":(4,4),
    "233":(2,3,3),"323":(3,2,3),"332":(3,3,2),"333":(3,3,3),"334":(3,3,4),
    "424":(4,2,4),"434":(4,3,4),"444":(4,4,4)
}

# Valid cells from corrected table (no — cells)
VALID = {
    "24":  [1,2,4,5,6,7],
    "33":  [1,2,3,4,5,6,7],
    "34":  [1,2,3,4,5,6,7],
    "42":  [1,2,3,5,6],
    "43":  [1,2,3,4,5,6,7],
    "44":  [2,3,5,6,7],
    "233": [1,2,3,4,5,6,7],
    "323": [1,2,3,4,5,6,7],
    "332": [1,2,3,4,5,6,7],
    "333": [1,2,3,4,5,6,7],
    "334": [1,2,3,4,5,6,7],
    "424": [1,2,5],
    "434": [1,2,3,4,5,6,7],
    "444": [2,3,6,7],
}

# Chord names — circled digit for scale degree, ornament suffixes preserved.
#
# Quality rules (major-mode reference):
#   I IV V               → major, no marker
#   ii iii vi            → minor, explicit "m" after the circled digit
#                          (circled digits have no case, so we need "m" to
#                          disambiguate from the major degrees)
#   vii                  → diminished, "°"
#   7-chord suffixes     → Δ (maj7), 7 (dom7), m7, ø7 (half-dim), m6, 6
#   sus/quartal/+8       → s2, s4, q, q7, +8 (no maj/min distinction)
#   ¹ ² ³                → inversion
#
# Thin space (\u2009) inserted before every inversion superscript so the
# raised-digit glyph doesn't collide with the body of the label when rendered.
_S = '\u2009'
CHORD_NAMES = {
    ("24",1):"①s2",         ("24",2):"②s2",         ("24",4):"④s2",         ("24",5):"⑤s2",         ("24",6):"⑥s2",         ("24",7):"—",
    ("33",1):"①",            ("33",2):"②m",           ("33",3):"③m",          ("33",4):"④",            ("33",5):"⑤",            ("33",6):"⑥m",           ("33",7):"⑦°",
    ("34",1):f"⑥m{_S}²",    ("34",2):f"⑦°{_S}²",    ("34",3):f"①{_S}²",     ("34",4):f"②m{_S}²",    ("34",5):f"③m{_S}²",    ("34",6):f"④{_S}²",     ("34",7):f"⑤{_S}²",
    ("42",1):"①s4",         ("42",2):"②s4",         ("42",3):"③s4",         ("42",5):"⑤s4",         ("42",6):"⑥s4",
    ("43",1):f"④{_S}¹",     ("43",2):f"⑤{_S}¹",     ("43",3):f"⑥m{_S}¹",    ("43",4):f"⑦°{_S}¹",    ("43",5):f"①{_S}¹",     ("43",6):f"②m{_S}¹",    ("43",7):f"③m{_S}¹",
    ("44",2):"②q",          ("44",3):"③q",          ("44",5):"⑤q",          ("44",6):"⑥q",          ("44",7):"⑦q",
    ("233",1):f"②m7{_S}¹", ("233",2):f"③m7{_S}¹", ("233",3):f"④Δ{_S}¹",  ("233",4):f"⑤7{_S}¹",  ("233",5):f"⑥m7{_S}¹", ("233",6):f"⑦ø7{_S}¹", ("233",7):f"①Δ{_S}¹",
    ("323",1):f"④Δ{_S}²",  ("323",2):f"⑤7{_S}²",  ("323",3):f"⑥m7{_S}²", ("323",4):f"⑦ø7{_S}²", ("323",5):f"①Δ{_S}²",  ("323",6):f"②m7{_S}²", ("323",7):f"③m7{_S}²",
    ("332",1):"①6",          ("332",2):"②m6",         ("332",3):f"①Δ{_S}³",  ("332",4):"④6",          ("332",5):"⑤6",          ("332",6):f"④Δ{_S}³",  ("332",7):f"⑤7{_S}³",
    ("333",1):"①Δ",          ("333",2):"②m7",         ("333",3):"③m7",        ("333",4):"④Δ",          ("333",5):"⑤7",          ("333",6):"⑥m7",         ("333",7):"⑦ø7",
    ("334",1):"①+8",         ("334",2):"②m+8",        ("334",3):"③m+8",       ("334",4):"④+8",         ("334",5):"⑤+8",         ("334",6):"⑥m+8",        ("334",7):"⑦+8",
    ("424",1):"①s4+8",       ("424",2):"②s4+8",       ("424",5):"⑤s4+8",
    ("434",1):f"④6{_S}¹",  ("434",2):f"⑤6{_S}¹",  ("434",3):f"④Δ{_S}³",  ("434",4):f"⑤7{_S}³",  ("434",5):f"①6{_S}¹",  ("434",6):f"②m6{_S}¹", ("434",7):f"①Δ{_S}³",
    ("444",2):"②q7",         ("444",3):"③q7",         ("444",6):"⑥q7",        ("444",7):"⑦q7",
}

MODES = {1:"Ionian",2:"Dorian",3:"Phrygian",4:"Lydian",5:"Mixolydian",6:"Aeolian",7:"Locrian"}
DEG_TO_FIRST_STRING = {6:1,7:2,1:3,2:4,3:5,4:6,5:7}

def string_to_abc(s):
    idx  = s - 1
    oct  = 2 + idx // 7
    name = NOTES_PER_OCT[idx % 7]
    if oct == 2: return name + ',,'
    if oct == 3: return name + ','
    if oct == 4: return name
    if oct == 5: return name.lower()
    if oct == 6: return name.lower() + "'"
    return name.lower() + "''"

def is_rh(note):
    if "'" in note: return True
    if note[0].islower(): return True
    if ',' not in note and note[0].isupper(): return True
    return False

def pattern_strings(start, pattern):
    strings = [start]
    pos = start
    for interval in pattern:
        pos += interval - 1
        strings.append(pos)
    return strings

def generate_measure(start_string, pattern):
    return generate_measure_multi([(start_string, pattern)])


# Phase map: which chord index to use for each of the 6 sub-arpeggios,
# given how many chords the caller supplied (1..4).
#
# Sub-arpeggio order in the run:
#   0 = up-low    (ascending, bottom octave)   \
#   1 = up-mid    (ascending, middle octave)    } 3 ascending
#   2 = up-high   (ascending, top octave)      /
#   3 = dn-high   (descending, top octave)     \
#   4 = dn-mid    (descending, middle octave)   } 3 descending
#   5 = dn-low    (descending, bottom octave)  /
#
# Phases: bot-up (sub 0), top-up (sub 1,2), top-dn (sub 3,4), bot-dn (sub 5)
#   1 chord : A A A A  -> all subs = 0
#   2 chords: A B B A  -> bottom (sub 0,5) = 0, top (sub 1-4) = 1
#   3 chords: A B B C  -> start 0, peak 1, end 2
#   4 chords: A B C D  -> start 0, top-up 1, top-dn 2, end 3
PHASE_MAP = {
    1: [0, 0, 0, 0, 0, 0],
    2: [0, 1, 1, 1, 1, 0],
    3: [0, 1, 1, 1, 1, 2],
    4: [0, 1, 1, 2, 2, 3],
}


def generate_measure_multi(chord_specs):
    """Build one measure of up-and-down run using 1..4 chord specs.

    chord_specs: list of (start_string, pattern) tuples, length 1..4.
      N=1: single chord, 3 octaves up and down.
      N=2: chord 1 = bottom (bass register), chord 2 = top (treble).
      N=3: chord 1 = start at bottom, chord 2 = up-and-down peak, chord 3 = end at bottom.
      N=4: chord 1 = start, chord 2 = top going up, chord 3 = top going down, chord 4 = end.

    Returns (rh_abc, lh_abc) or None if any chord would overrun the 33-string harp.
    """
    n = len(chord_specs)
    if n not in PHASE_MAP:
        raise ValueError(f"chord_specs must have length 1..4, got {n}")
    phase = PHASE_MAP[n]

    all_notes = []
    # 3 ascending sub-arpeggios (rep = 0, 1, 2)
    for sub in range(3):
        ci = phase[sub]
        start, pattern = chord_specs[ci]
        base = start + sub * 7
        span = sum(p - 1 for p in pattern)
        if base + span > 33:
            return None
        arp = [string_to_abc(s) for s in pattern_strings(base, pattern)]
        all_notes.extend(arp)
    # 3 descending sub-arpeggios (rep = 2, 1, 0)
    for k in range(3):
        sub = 3 + k
        ci = phase[sub]
        start, pattern = chord_specs[ci]
        rep = 2 - k
        base = start + rep * 7
        span = sum(p - 1 for p in pattern)
        if base + span > 33:
            return None
        arp = [string_to_abc(s) for s in pattern_strings(base, pattern)]
        all_notes.extend(reversed(arp))

    rh = [note if is_rh(note) else 'x' for note in all_notes]
    lh = [note if not is_rh(note) else 'x' for note in all_notes]

    def fmt(notes):
        result = []
        for i, note in enumerate(notes):
            if i > 0 and (notes[i - 1] == 'x') != (note == 'x'):
                result.append(' ')
            result.append(note)
        return ''.join(result)

    return fmt(rh), fmt(lh)

def generate_abc():
    lines = []
    lines.append("X:1")
    lines.append("T:Diatonic Harp Chord Drill")
    lines.append("M:none")
    lines.append("L:1/32")
    lines.append("%%staves {RH LH}")
    lines.append("V:RH clef=treble")
    lines.append("V:LH clef=bass")
    lines.append("K:Eb")

    measure_num = 1
    for deg in [6,7,1,2,3,4,5]:
        mode = MODES[deg]
        start = DEG_TO_FIRST_STRING[deg]
        lines.append(f"% === {mode} (deg {deg}) ===")
        for pat_str in ["24","33","34","42","43","44","233","323","332","333","334","424","434","444"]:
            if deg not in VALID.get(pat_str, []):
                continue
            pat    = PAT_MAP[pat_str]
            result = generate_measure(start, pat)
            if result is None:
                continue
            rh, lh = result
            chord  = CHORD_NAMES.get((pat_str, deg), "?")
            lines.append(f"% {measure_num}: {deg}{pat_str} = {chord}")
            lines.append(f"[V:RH] {rh}|")
            lines.append(f"[V:LH] {lh}|")
            measure_num += 1

    return '\n'.join(lines)

if __name__ == '__main__':
    abc = generate_abc()
    with open('drill.abc', 'w') as f:
        f.write(abc)
    print(f"Written drill.abc")
    for line in abc.split('\n')[:40]:
        print(line)
