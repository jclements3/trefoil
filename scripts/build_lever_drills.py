#!/usr/bin/env python3
"""Generate original lever harp technique exercises for the strip chart app.

Covers: crossing, scales, chords, inversions, intervals, dexterity,
repeated notes, ornaments, triplets, LH techniques, polyrhythms.
All exercises use grand staff (treble + bass clef).
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent

def drill(xnum, title, meter, unit, rh, lh, key='C', tempo=60):
    abc = (
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
        f'V: RH clef=treble name="RH"\n'
        f'V: LH clef=bass name="LH"\n'
        f'K: {key}\n'
        f'[V: RH] [Q:1/4={tempo}] {rh}\n'
        f'[V: LH] {lh}\n'
    )
    return {'n': str(xnum), 't': title, 'abc': abc}

drills = []
x = 1300  # number range for lever harp drills

# ── 1. Crossing Under and Over ──

drills.append(drill(x, "Lever: Cross Under 2-1", "4/4", "1/8",
    "CDEF GABc | DEFG ABcd | EFGa bcde | c'8 |]",
    "C,D,E,F, G,A,B,C | D,E,F,G, A,B,C,D | E,F,G,A, B,CDE | C8 |]"
)); x += 1

drills.append(drill(x, "Lever: Cross Over 1-2", "4/4", "1/8",
    "cBAG FEDC | dcBA GFED | edcB AGFE | C8 |]",
    "CB,A,G, F,E,D,C, | DC,B,,A,, G,,F,,E,,D,, | C,8 z8 |]"
)); x += 1

drills.append(drill(x, "Lever: Cross Under 3-1", "4/4", "1/8",
    "CEDF EGFA | GBcA Bcde | c'8 z8 |]",
    "C,E,D,F, E,G,F,A, | G,B,A,C B,DEF | C8 z8 |]"
)); x += 1

drills.append(drill(x, "Lever: Cross Over+Under alt", "4/4", "1/8",
    "CDEF EDCB, | DEFG FEDC | EFGa GFED | c8 |]",
    "C,D,E,F, E,D,C,B,, | D,E,F,G, F,E,D,C, | E,F,G,A, G,F,E,D, | C,8 |]"
)); x += 1

# ── 2. Scales (grand staff) ──

for key, name in [('C','C maj'), ('G','G maj'), ('D','D maj'), ('F','F maj'), ('Bb','Bb maj'), ('Am','A min')]:
    drills.append(drill(x, f"Lever: Scale {name} asc", "4/4", "1/8",
        "CDEF GABc | defg abc'd' | c'8 z8 |]",
        "C,D,E,F, G,A,B,C | DEFG ABcd | c8 z8 |]",
        key=key
    )); x += 1
    drills.append(drill(x, f"Lever: Scale {name} desc", "4/4", "1/8",
        "c'bagf edcB | AGFE DCB,A, | C,8 z8 |]",
        "dcBA GFED | C,B,,A,,G,, F,,E,,D,,C,, | C,,8 z8 |]",
        key=key
    )); x += 1

# ── 3. Chords (block chords, both hands) ──

drills.append(drill(x, "Lever: Block Chords I-IV-V-I", "4/4", "1/4",
    "[CEG]2 [FAc]2 | [GBd]2 [CEG]2 | [FAc]2 [GBd]2 | [ceg]4 |]",
    "[C,E,G,]2 [F,A,C]2 | [G,B,D]2 [C,E,G,]2 | [F,A,C]2 [G,B,D]2 | [C,E,G,]4 |]"
)); x += 1

drills.append(drill(x, "Lever: Block Chords diatonic", "4/4", "1/4",
    "[CEG]2 [DFA]2 | [EGB]2 [FAc]2 | [GBd]2 [Ace]2 | [Bdf]2 [ceg]2 |]",
    "[C,E,G,]2 [D,F,A,]2 | [E,G,B,]2 [F,A,C]2 | [G,B,D]2 [A,CE]2 | [B,DF]2 [CEG]2 |]"
)); x += 1

drills.append(drill(x, "Lever: Broken Chords asc", "4/4", "1/8",
    "CEGC EGCE | FACE ACEF | GBDF BDFG | cegc' c'8 |]",
    "C,E,G,C E,G,CE | F,A,CF A,CFA | G,B,DG B,DGB | CEGC C8 |]"
)); x += 1

# ── 4. Inversions ──

drills.append(drill(x, "Lever: C chord inversions", "4/4", "1/4",
    "[CEG]2 [EGc]2 | [Gce]2 [ceg]2 | [Gce]2 [EGc]2 | [CEG]4 |]",
    "[C,E,G,]2 [E,G,C]2 | [G,CE]2 [CEG]2 | [G,CE]2 [E,G,C]2 | [C,E,G,]4 |]"
)); x += 1

drills.append(drill(x, "Lever: All triads + inv", "4/4", "1/4",
    "[CEG] [EGc] [Gce] | [DFA] [FAd] [Adf] | [EGB] [GBe] [Beg] | [FAc] [Acf] [cfa] |]",
    "[C,E,G,] [E,G,C] [G,CE] | [D,F,A,] [F,A,D] [A,DF] | [E,G,B,] [G,B,E] [B,EG] | [F,A,C] [A,CF] [CFA] |]"
)); x += 1

# ── 5. Intervals ──

for interval, name, rh_pat, lh_pat in [
    (2, "2nds", "CD DE EF FG | GA AB Bc cd |]", "C,D, D,E, E,F, F,G, | G,A, A,B, B,C CD |]"),
    (3, "3rds", "CE DF EG FA | GB Ac Bd ce |]", "C,E, D,F, E,G, F,A, | G,B, A,C B,D CE |]"),
    (4, "4ths", "CF DG EA FB | Gc Ad Be cf |]", "C,F, D,G, E,A, F,B, | G,C A,D B,E CF |]"),
    (5, "5ths", "CG DA EB Fc | Gd Ae Bf cg |]", "C,G, D,A, E,B, F,C | G,D A,E B,F CG |]"),
    (6, "6ths", "CA DB EC FD | GE AF BG cA |]", "C,A, D,B, E,C F,D | G,E A,F B,G CA |]"),
]:
    drills.append(drill(x, f"Lever: Interval {name}", "4/4", "1/4",
        rh_pat, lh_pat
    )); x += 1

# ── 6. Dexterity and Finger Independence ──

drills.append(drill(x, "Lever: Finger Indep 4-3-2-1", "4/4", "1/8",
    "CDEF CDEF | GABC GABC | cdef cdef | c'8 |]",
    "C,D,E,F, C,D,E,F, | G,A,B,C G,A,B,C | CDEF CDEF | C8 |]"
)); x += 1

drills.append(drill(x, "Lever: Finger Indep 1-2-3-4", "4/4", "1/8",
    "FEDC FEDC | cBAG cBAG | gfed gfed | c8 |]",
    "F,E,D,C, F,E,D,C, | CBAG CBAG | gfed gfed | C,8 |]"
)); x += 1

drills.append(drill(x, "Lever: Alternating fingers", "4/4", "1/8",
    "CDCD EFEF | GAGA BcBc | dede fgfg | c'8 |]",
    "C,D,C,D, E,F,E,F, | G,A,G,A, B,CB,C | DEDE FGFG | C8 |]"
)); x += 1

# ── 7. Repeated Notes ──

drills.append(drill(x, "Lever: Repeated notes single", "4/4", "1/8",
    "CCCC DDDD | EEEE FFFF | GGGG AAAA | BBBc c8 |]",
    "C,C,C,C, D,D,D,D, | E,E,E,E, F,F,F,F, | G,G,G,G, A,A,A,A, | B,B,B,C C8 |]"
)); x += 1

drills.append(drill(x, "Lever: Repeated notes double", "4/4", "1/8",
    "CCDD EEFF | GGAA BBcc | ddee ffgg | c'8 z8 |]",
    "C,C,D,D, E,E,F,F, | G,G,A,A, B,B,CC | DDEE FFGG | C8 z8 |]"
)); x += 1

# ── 8. Ornaments (grace notes, rolls) ──

drills.append(drill(x, "Lever: Grace notes asc", "4/4", "1/4",
    "{B,}C {D}E {F}G {A}B | {c}d {e}f {g}a {b}c' | c'4 z4 |]",
    "{B,,}C, {D,}E, {F,}G, {A,}B, | {C}D {E}F {G}A {B}c | C4 z4 |]"
)); x += 1

drills.append(drill(x, "Lever: Turns", "4/4", "1/8",
    "CDCB, DEDC | EFED FGFE | GAGF ABcA | c8 |]",
    "C,D,C,B,, D,E,D,C, | E,F,E,D, F,G,F,E, | G,A,G,F, A,B,CA, | C8 |]"
)); x += 1

# ── 9. Triplets ──

drills.append(drill(x, "Lever: Triplets ascending", "4/4", "1/8",
    "(3CDE (3FGA (3Bcd (3efg | (3abc' z4 z4 |]",
    "(3C,D,E, (3F,G,A, (3B,CD (3EFG | (3ABc z4 z4 |]"
)); x += 1

drills.append(drill(x, "Lever: Triplets descending", "4/4", "1/8",
    "(3gfe (3dcB (3AGF (3EDC | C8 z8 |]",
    "(3GFE (3DCB, (3A,G,F, (3E,D,C, | C,8 z8 |]"
)); x += 1

drills.append(drill(x, "Lever: Triplets zigzag", "3/4", "1/8",
    "(3CEC (3DFD | (3EGE (3FAF | (3GBG (3AcA | c6 |]",
    "(3C,E,C, (3D,F,D, | (3E,G,E, (3F,A,F, | (3G,B,G, (3A,CA, | C6 |]"
)); x += 1

# ── 10. LH Techniques ──

drills.append(drill(x, "Lever: LH scale + RH held", "4/4", "1/8",
    "C8 | E8 | G8 | c8 |]",
    "C,D,E,F, G,A,B,C | D,E,F,G, A,B,CD | E,F,G,A, B,CDE | C,8 |]"
)); x += 1

drills.append(drill(x, "Lever: LH arpeggios", "4/4", "1/8",
    "C8 | F8 | G8 | C8 |]",
    "C,E,G,C E,G,CE | F,A,CF A,CFA | G,B,DG B,DGB | C,E,G,C C8 |]"
)); x += 1

drills.append(drill(x, "Lever: LH chord patterns", "4/4", "1/4",
    "C4 | E4 | G4 | c4 |]",
    "[C,E,G,] [D,F,A,] [E,G,B,] [F,A,C] | [G,B,D] [A,CE] [B,DF] [CEG] | [G,B,D] [F,A,C] [E,G,B,] [D,F,A,] | [C,E,G,]4 |]"
)); x += 1

# ── 11. Polyrhythms ──

drills.append(drill(x, "Lever: 2 against 3", "3/4", "1/8",
    "C2 E2 G2 | c2 E2 C2 | C2 E2 G2 | C6 |]",
    "(3C,E,G, (3C,E,G, (3C,E,G, | (3C,E,G, (3C,E,G, (3C,E,G, | (3C,E,G, (3C,E,G, (3C,E,G, | C,6 |]"
)); x += 1

drills.append(drill(x, "Lever: 3 against 4", "4/4", "1/8",
    "(3CEG (3CEG (3CEG (3CEG | (3ceg (3ceg (3ceg (3ceg | c8 |]",
    "C,E,G,C E,G,CE | G,B,DF G,B,DF | C,8 |]"
)); x += 1

# ── 12. Lever Changes (key changes mid-exercise) ──

drills.append(drill(x, "Lever: C to G transition", "4/4", "1/8",
    "CDEF GABc | defg abc'd' | c'BAG ^FEDC | DEFG ABcd | c8 |]",
    "C,D,E,F, G,A,B,C | DEFG ABcd | cBAG ^F,E,D,C, | D,E,F,G, A,B,CD | C,8 |]",
    key='C'
)); x += 1

drills.append(drill(x, "Lever: C to F transition", "4/4", "1/8",
    "CDEF GABc | cBAG FEDC | CDE_B AGFE | FGAB cdef | f8 |]",
    "C,D,E,F, G,A,B,C | CB,A,G, F,E,D,C, | C,D,E,_B, A,G,F,E, | F,G,A,B, CDEF | F,8 |]",
    key='C'
)); x += 1

drills.append(drill(x, "Lever: Circle of 5ths", "4/4", "1/4",
    "[CEG]2 [GBd]2 | [DAf]2 [EAc]2 | [Bdf]2 [FAc]2 | [CEG]4 |]",
    "[C,E,G,]2 [G,B,D]2 | [D,A,F]2 [E,A,C]2 | [B,DF]2 [F,A,C]2 | [C,E,G,]4 |]"
)); x += 1

# Save
outpath = PROJECT_DIR / 'app/lever_drills.json'
with open(outpath, 'w') as f:
    json.dump(drills, f, separators=(',', ':'))

print(f"Generated {len(drills)} lever harp exercises")
print(f"Number range: 1300-{x-1}")
print(f"Saved to {outpath}")
