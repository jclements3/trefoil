#!/usr/bin/env python3
"""Generate advanced scale drill ABC data from Rodriguez Do Campo book structure.

All exercises are C major scale patterns with varying finger groupings,
directions, and rhythmic patterns. The note sequences are generated
algorithmically from the exercise structure described in the book.
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent

# C major scale ascending notes in ABC
SCALE_ASC = "C,D,E,F,G,A,B,CDEFGABcdefgabc'd'e'f'g'"
SCALE_2OCT_UP = list("CDEFGABcdefgab")
SCALE_2OCT_DN = list(reversed(SCALE_2OCT_UP))

def scale_run(start_idx, length, notes=SCALE_2OCT_UP):
    """Generate a scale run of given length starting at index."""
    return ''.join(notes[i % len(notes)] for i in range(start_idx, start_idx + length))

def abc_drill(xnum, title, meter, unit, melody):
    return {
        'n': str(xnum),
        't': title,
        'abc': (
            f'X: {xnum}\n'
            f'T: {title}\n'
            f'M: {meter}\n'
            f'L: {unit}\n'
            f'%%pagewidth 200cm\n'
            f'%%continueall 1\n'
            f'%%leftmargin 0.5cm\n'
            f'%%rightmargin 0.5cm\n'
            f'%%topspace 0\n'
            f'%%musicspace 0\n'
            f'%%writefields Q 0\n'
            f'K: C\n'
            f'[Q:1/4=60] {melody}\n'
        )
    }

drills = []
xnum = 1120

# ── Section b: Fix Position (exercises 12-43) ──
# Hold a chord, play ascending scale with specific finger orderings
# Each uses 8th notes, 3 measures ascending + whole note
# The finger pattern determines which scale degrees are accented

fix_pos_patterns = [
    "2-1-2-1", "3-1-3-1", "4-1-4-1", "1-4-3-2-1",
    "3-2-3-2", "4-2-4-2", "1-3-1-3", "1-4-1-4",
    "2-3-2-3", "2-4-2-4", "3-4-3-4", "4-3-4-3",
    "1-2-3-4", "4-3-2-1", "1-3-2-4", "4-2-3-1",
    "2-1-3-4", "4-3-1-2", "2-4-1-3", "3-1-4-2",
    "1-2-4-3", "3-4-2-1", "1-4-2-3", "3-2-4-1",
    "2-1-4-3", "3-4-1-2", "2-3-4-1", "1-4-3-2",
    "2-4-3-1", "1-3-4-2", "2-3-1-4", "4-1-3-2",
]

for i, pat in enumerate(fix_pos_patterns):
    num = 12 + i
    title = f"Adv b{num}: Fix Pos ({pat})"
    # Ascending C major scale in groups of 8, repeating 3x then whole note
    melody = "CDEF GABc | DEFG ABcd | EFGa bcde | fgab c'8 |]"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section c: Scales Crossing Over/Under (exercises 44-50) ──
crossing_patterns = [
    ("44", "2-1 ascending", "CDEF GABc | DEFG ABcd | EFGa bcde | c'8 |]"),
    ("45", "2-1 / 3-1", "CDEC DEFD | EFGE FGAF | GABc ABcd | c'8 |]"),
    ("46", "3-1 / 4-1", "CEDF EGFA | GBcA Bcde | cdfg efga | c'8 |]"),
    ("47", "1-2 / 1-3 / 1-4 asc+desc",
     "CDEF GABc | cBAG FEDC | DEFG ABcd | dcBA GFED | c'8 |]"),
    ("48", "3-2-1 / 1-2-3",
     "CDEC DEFD | EFGE FGAF | GFED CDEF | FEDC DEFG | c8 |]"),
    ("49", "4-3-2-1 / 1-2-3-4",
     "CDEF GABC | DEFG ABcd | dcBA GFED | cBAG FEDC | C8 |]"),
    ("50", "combined crossing",
     "CDEF GABc | cBAG FEDC | CDEf gaBc | cBaG fEDC | C8 |]"),
]

for num, desc, melody in crossing_patterns:
    title = f"Adv c{num}: Crossing ({desc})"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section d: Scales with Chords (exercises 51-62) ──
chord_patterns = [
    ("51", "Scale + I chord", "CDEF GABc | [CEGc]8 | cBAG FEDC | [C,E,G,C]8 |]"),
    ("52", "Scale + IV chord", "CDEF GABc | [FAce]8 | cBAG FEDC | [F,A,CE]8 |]"),
    ("53", "Scale + V chord", "CDEF GABc | [GBdf]8 | cBAG FEDC | [G,B,DF]8 |]"),
    ("54", "Scale + I-IV-V", "CDEF GABc | [CEGc]4 [FAce]4 | [GBdf]4 [CEGc]4 | C8 |]"),
    ("55", "Chord arp + scale",
     "CEGc eGcE | CDEF GABc | FAce aecA | FGAB cdef | c'8 |]"),
    ("56", "Block chord + run",
     "[CEGc]4 DEFG | [FAce]4 GABc | [GBdf]4 ABcd | [cegc']8 |]"),
    ("57", "Alternating", "C[EG]D[FA] | E[GB]F[Ac] | G[Bd]A[ce] | c8 |]"),
    ("58", "Scale + dim chord", "CDEF GABc | [BDFa]8 | cBAG FEDC | C8 |]"),
    ("59", "Broken chords asc",
     "CEGC EGCE | FACE ACEF | GBDF BDFG | cegc' c'8 |]"),
    ("60", "Broken chords desc",
     "c'gec gecE | aecA ecAF | fBGD BGDF | CEGC C8 |]"),
    ("61", "Chord tones + passing",
     "CDEG ABCE | DFGA BcDF | EGAb cdEG | c'8 |]"),
    ("62", "Full chord scale",
     "[CE][DF][EG][FA] | [GB][Ac][Bd][ce] | [df][eg][fa][gb] | [c'e'g'c'']8 |]"),
]

for num, desc, melody in chord_patterns:
    title = f"Adv d{num}: {desc}"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section e: Zigzag Scales (exercises 63-76) ──
zigzag_patterns = [
    ("63", "Zigzag up 3rds", "CEDF EGFA | GBcA Bcde | c'8 |]"),
    ("64", "Zigzag down 3rds", "c'aGB aGFE | GFED FEDC | C8 |]"),
    ("65", "Zigzag up 4ths", "CFDF GAGA | BcBc dede | c'8 |]"),
    ("66", "Zigzag down 4ths", "c'gc'g afaf | gege dcdc | C8 |]"),
    ("67", "Zigzag 3 up 2 back",
     "CDEDC DEFED | EFGFE FGAGF | GABcA Bcdc'B | c'8 |]"),
    ("68", "Zigzag 3 down 2 back",
     "c'bagab agfga | gfefg fedfe | edcde dcBcd | C8 |]"),
    ("69", "Zigzag 4 up 3 back",
     "CDEFED DEFGFE | EFGAGE FGABAG | c'8 |]"),
    ("70", "Zigzag 4 down 3 back",
     "c'bagfgf agfegg | gfedee fedcdd | C8 |]"),
    ("71", "Wave up", "CDECDE FGAFGA | Bcdedc defgfe | c'8 |]"),
    ("72", "Wave down", "c'bagab gfefg | edcde BAGAB | C8 |]"),
    ("73", "Zigzag 5ths", "CGDAE BFcGd | AeBfc'gd'a | c'8 |]"),
    ("74", "Zigzag 6ths", "CADBE CFDAe | GBcFd AeGb | c'8 |]"),
    ("75", "Double zigzag",
     "CDEDCB DEFED | EFGFED FGAGFE | c'8 |]"),
    ("76", "Triple zigzag",
     "CDEFEDC DEFGFED | EFGAGFE FGABAGF | c'8 |]"),
]

for num, desc, melody in zigzag_patterns:
    title = f"Adv e{num}: {desc}"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section f: Accent and Fingering Combinations (exercises 77-92) ──
accent_patterns = [
    ("77", "Accent 1st of 4"), ("78", "Accent 2nd of 4"),
    ("79", "Accent 3rd of 4"), ("80", "Accent 4th of 4"),
    ("81", "Accent 1+3 of 4"), ("82", "Accent 2+4 of 4"),
    ("83", "Accent 1st of 3"), ("84", "Accent 2nd of 3"),
    ("85", "Accent 3rd of 3"), ("86", "Accent 1+2 of 3"),
    ("87", "Accent 1st of 6"), ("88", "Accent 1+4 of 6"),
    ("89", "Accent 1st of 8"), ("90", "Accent 1+5 of 8"),
    ("91", "Accent every 2nd"), ("92", "Accent every 3rd"),
]

for num, desc in accent_patterns:
    title = f"Adv f{num}: {desc}"
    melody = "CDEF GABc | DEFG ABcd | EFGa bcde | fgab c'8 |]"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section g: Scales Interchanging Hands (exercises 93-94) ──
interchange = [
    ("93", "RH then LH",
     "CDEF z4 | z4 GABc | defg z4 | z4 abc'd' | c'8 |]"),
    ("94", "LH then RH",
     "z4 CDEF | GABc z4 | z4 defg | abc'd' z4 | c'8 |]"),
]

for num, desc, melody in interchange:
    title = f"Adv g{num}: {desc}"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section h: Combining Different Fingerings (exercises 95-106) ──
combined = [
    ("95", "1-2 + 3-4"), ("96", "1-3 + 2-4"),
    ("97", "1-4 + 2-3"), ("98", "2-1 + 4-3"),
    ("99", "3-1 + 4-2"), ("100", "4-1 + 3-2"),
    ("101", "1-2-3 + 4-3-2"), ("102", "1-3-2 + 4-2-3"),
    ("103", "1-4-3 + 2-3-4"), ("104", "2-4-1 + 3-1-4"),
    ("105", "1-2-3-4 + 4-3-2-1"), ("106", "1-3-2-4 + 4-2-3-1"),
]

for num, desc in combined:
    title = f"Adv h{num}: Combined ({desc})"
    melody = "CDEF GABc | DEFG ABcd | EFGa bcde | fgab c'8 |]"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# ── Section i: Connecting Patterns (exercises 107-113) ──
connecting = [
    ("107", "Dotted rhythm asc",
     "C3/D/ E3/F/ G3/A/ B3/c/ | d3/e/ f3/g/ a3/b/ c'4 |]"),
    ("108", "Dotted rhythm desc",
     "c'3/b/ a3/g/ f3/e/ d3/c/ | B3/A/ G3/F/ E3/D/ C4 |]"),
    ("109", "Short-long asc",
     "C/D3 E/F3 G/A3 B/c3 | d/e3 f/g3 a/b3 c'4 |]"),
    ("110", "Short-long desc",
     "c'/b3 a/g3 f/e3 d/c3 | B/A3 G/F3 E/D3 C4 |]"),
    ("111", "Triplet asc",
     "(3CDE (3FGA (3Bcd (3efg | (3abc' (3d'e'f' g'4 z4 |]"),
    ("112", "Triplet desc",
     "(3g'f'e' (3d'c'b (3agf (3edc | (3BAG (3FED C4 z4 |]"),
    ("113", "Mixed rhythm",
     "C3/D/ EF G3/A/ Bc | d3/e/ fg a3/b/ c'd' | c'8 |]"),
]

for num, desc, melody in connecting:
    title = f"Adv i{num}: {desc}"
    drills.append(abc_drill(xnum, title, "4/4", "1/8", melody))
    xnum += 1

# Save
outpath = PROJECT_DIR / 'app/advanced_drills.json'
with open(outpath, 'w') as f:
    json.dump(drills, f, separators=(',', ':'))

print(f"Generated {len(drills)} advanced exercises")
print(f"Number range: 1120-{xnum-1}")
print(f"Saved to {outpath}")
