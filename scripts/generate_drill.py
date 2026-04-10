#!/usr/bin/env python3
# generate_drill.py
# Generates ABC notation drill for diatonic harp chord table
# Eb major tuning, 33 strings starting C2
# Each measure: 3x run up and down for one pattern address

NOTES_PER_OCT = ['C','D','E','F','G','A','B']  # K:Eb, flats implicit

PAT_MAP = {
    "24":(2,4),"33":(3,3),"34":(3,4),"42":(4,2),"43":(4,3),"44":(4,4),
    "233":(2,3,3),"323":(3,2,3),"332":(3,3,2),"333":(3,3,3),"334":(3,3,4),
    "433":(4,3,3),"434":(4,3,4),"444":(4,4,4)
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
    "433": [1,2,5],
    "434": [1,2,3,4,5,6,7],
    "444": [2,3,6,7],
}

# Chord names from corrected table
CHORD_NAMES = {
    ("24",1):"Is2",    ("24",2):"iis2",   ("24",4):"IVs2",   ("24",5):"Vs2",    ("24",6):"vis2",   ("24",7):"—",
    ("33",1):"I",      ("33",2):"ii",     ("33",3):"iii",    ("33",4):"IV",     ("33",5):"V",      ("33",6):"vi",     ("33",7):"vii°",
    ("34",1):"vi²",    ("34",2):"vii°²",  ("34",3):"I²",     ("34",4):"ii²",    ("34",5):"iii²",   ("34",6):"IV²",    ("34",7):"V²",
    ("42",1):"Is4",    ("42",2):"iis4",   ("42",3):"iiis4",  ("42",5):"Vs4",    ("42",6):"vis4",
    ("43",1):"IV¹",    ("43",2):"V¹",     ("43",3):"vi¹",    ("43",4):"vii°¹",  ("43",5):"I¹",     ("43",6):"ii¹",    ("43",7):"iii¹",
    ("44",2):"iiq",    ("44",3):"iiiq",   ("44",5):"Vq",     ("44",6):"viq",    ("44",7):"viiq",
    ("233",1):"iim7¹", ("233",2):"iiim7¹",("233",3):"IVΔ¹",  ("233",4):"V7¹",   ("233",5):"vim7¹", ("233",6):"viiø7¹",("233",7):"IΔ¹",
    ("323",1):"IVΔ²",  ("323",2):"V7²",   ("323",3):"vim7²", ("323",4):"viiø7²",("323",5):"IΔ²",   ("323",6):"iim7²", ("323",7):"iiim7²",
    ("332",1):"I6",    ("332",2):"iim6",  ("332",3):"IΔ³",   ("332",4):"IV6",   ("332",5):"V6",    ("332",6):"IVΔ³",  ("332",7):"V7³",
    ("333",1):"IΔ",    ("333",2):"iim7",  ("333",3):"iiim7", ("333",4):"IVΔ",   ("333",5):"V7",    ("333",6):"vim7",  ("333",7):"viiø7",
    ("334",1):"I+8",   ("334",2):"ii+8",  ("334",3):"iii+8", ("334",4):"IV+8",  ("334",5):"V+8",   ("334",6):"vi+8",  ("334",7):"vii+8",
    ("433",1):"Is4+8", ("433",2):"iis4+8",("433",5):"Vs4+8",
    ("434",1):"IV6¹",  ("434",2):"V6¹",   ("434",3):"IVΔ³",  ("434",4):"V7³",   ("434",5):"I6¹",   ("434",6):"iim6¹", ("434",7):"IΔ³",
    ("444",2):"iiq7",  ("444",3):"iiiq7", ("444",6):"viq7",  ("444",7):"viiq7",
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
        for pat_str in ["24","33","34","42","43","44","233","323","332","333","334","433","434","444"]:
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
