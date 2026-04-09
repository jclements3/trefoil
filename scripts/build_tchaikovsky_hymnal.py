#!/usr/bin/env python3
"""Build Tchaikovsky-style harp drills from OpenHymnal lead sheets.

Algorithm:
1. Read chord symbols from lead_sheets.json (already identified per measure)
2. Map each chord to scale degree in key
3. Pick patterns from chord table for each degree
4. Build 4-chord runs: A(bass up) → B(treble up) → C(treble down) → D(bass down)
   - A,B from current measure's chord + color pairing
   - C,D from next measure's chord + current chord
5. Expand pattern tones across harp range, build one continuous sweep
6. Label with chord table names as fractions

Output: app/tchaikovsky_data.json
"""

import json, re, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAD_SHEETS = ROOT / "app" / "lead_sheets.json"
OUTPUT = ROOT / "app" / "tchaikovsky_data.json"

# ── Scales ──
SCALES = {
    'Eb': ['Eb','F','G','Ab','Bb','C','D'],
    'Bb': ['Bb','C','D','Eb','F','G','A'],
    'F':  ['F','G','A','Bb','C','D','E'],
    'C':  ['C','D','E','F','G','A','B'],
    'G':  ['G','A','B','C','D','E','F#'],
    'D':  ['D','E','F#','G','A','B','C#'],
    'A':  ['A','B','C#','D','E','F#','G#'],
    'E':  ['E','F#','G#','A','B','C#','D#'],
}
NOTE_SEMI = {
    'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,
    'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,
}
KEY_ACC = {k: {n for n in sc if '#' in n or 'b' in n} for k, sc in SCALES.items()}

# Harp range: C2 (MIDI 36) to G6 (MIDI 91) — 33 strings
HARP_LOW = 36; HARP_HIGH = 91
# Middle C for grand staff split
MID_C = 60

# ── Chord table ──
PATTERNS = {
    '3-3':   (2,2),   '3-4':   (2,3),   '4-2':   (3,1),   '4-3':   (3,2),
    '4-4':   (3,3),   '2-4':   (1,3),
    '3-3-3': (2,2,2), '3-3-2': (2,2,1), '3-3-4': (2,2,3),
    '3-2-3': (2,1,2), '2-3-3': (1,2,2), '3-4-2': (2,3,1),
    '4-3-3': (3,2,2), '4-4-4': (3,3,3),
}
TABLE_NAMES = {
    '3-3':   ['I',      'iim',     'iiim',    'IV',      'V',       'vim',     'vii°'],
    '3-4':   ['I¹',     'iim¹',    'iiim¹',   'IV¹',     'V¹',      'vim¹',    'vii°¹'],
    '4-3':   ['I²',     'iim²',    'iiim²',   'IV²',     'V²',      'vim²',    'vii°²'],
    '4-2':   ['IV¹',    'V¹',      'vim¹',    'vii°¹',   'I¹',      'iim¹',    'iiim²'],
    '4-4':   ['Iq',     'iiq',     'iiiq',    'IVq',     'Vq',      'viq',     'vii°q'],
    '2-4':   ['IM7-5²', 'iim7-5²', 'iiim7-5²','IVM7-5²', 'V7-5²',   'vim7-5²', 'Vq²'],
    '3-3-3': ['IM7',    'iim7',    'iiim7',   'IVM7',    'V7',      'vim7',    'viiø7'],
    '3-3-2': ['I6',     'iim6',    'iiim6',   'IV6',     'V6',      'vim6',    'vii°6'],
    '3-3-4': ['I+9',    'ii+9',    'iii+9',   'IV+9',    'V+9',     'vi+9',    'vii°+9'],
    '3-2-3': ['IM7²',   'iim7²',   'iiim7²',  'IVM7²',   'V7²',     'vim7²',   'viiø7²'],
    '2-3-3': ['IM7³',   'iim7³',   'iiim7³',  'IVM7³',   'V7³',     'vim7³',   'viiø7³'],
    '3-4-2': ['I9-5',   'ii9-5',   'iii9-5',  'IV9-5',   'V9-5',    'vi9-5',   'vii°9-5'],
    '4-3-3': ['I9-3',   'ii9-3',   'iii9-3',  'IV9-3',   'V9-3',    'vi9-3',   'vii°9-3'],
    '4-4-4': ['Iq7',    'iiq7',    'iiiq7',   'IVq7',    'Vq7',     'viq7',    'vii°q7'],
}

# Harmonic color pairings: degree → list of good partner degrees
# Used when a single chord needs a Tchaikovsky transition partner
COLOR_PAIRS = {
    0: [5, 3, 4],    # I → vim, IV, V
    1: [3, 4, 5],    # iim → IV, V, vim
    2: [0, 5, 4],    # iiim → I, vim, V
    3: [0, 1, 4],    # IV → I, iim, V
    4: [0, 2, 5],    # V → I, iiim, vim
    5: [0, 3, 2],    # vim → I, IV, iiim
    6: [4, 0, 3],    # viideg → V, I, IV
}

# Pattern pools for variety
# Bass (lower half): prefer wider intervals
BASS_PATTERNS = ['3-3', '4-3', '3-4', '4-4', '3-3-3']
# Treble (upper half): prefer richer voicings
TREBLE_PATTERNS = ['3-3-3', '3-3', '3-3-2', '3-2-3', '3-3-4', '4-3-3', '2-3-3']


def chord_to_degree(chord_str, key):
    """Map chord symbol to 0-based scale degree. Returns None if unmappable."""
    m = re.match(r'^([A-G][#b]?)', chord_str)
    if not m: return None
    root_pc = NOTE_SEMI.get(m.group(1))
    if root_pc is None: return None
    for deg, name in enumerate(SCALES.get(key, [])):
        if NOTE_SEMI[name] == root_pc:
            return deg
    return None


def pattern_tones(degree, pattern_name, key, low, high):
    """Get sorted MIDI pitches for a pattern at a degree, across a range."""
    intervals = PATTERNS[pattern_name]
    # Compute which scale degrees are in this chord
    degs = {degree}
    cur = degree
    for step in intervals:
        cur = (cur + step) % 7
        degs.add(cur)
    # Get pitch classes for those degrees
    scale = SCALES[key]
    pcs = set(NOTE_SEMI[scale[d]] for d in degs)
    # Expand across range
    return sorted(m for m in range(low, high + 1) if m % 12 in pcs)


def pick_pattern(pool, seed):
    """Pick a pattern from a pool using a seed for variety."""
    return pool[seed % len(pool)]


def table_label(pattern_name, degree):
    """Look up Roman numeral name from chord table."""
    if pattern_name in TABLE_NAMES:
        return TABLE_NAMES[pattern_name][degree]
    return f'd{degree+1}_{pattern_name}'


# ── ABC formatting ──

def midi_to_abc(midi, key):
    scale = SCALES.get(key, SCALES['C'])
    pc = midi % 12
    octave = (midi // 12) - 1
    for note in scale:
        if NOTE_SEMI[note] == pc:
            return _fmt(note, octave, key)
    names = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
    return _fmt(names[pc], octave, key)

def _fmt(name, octave, key='C'):
    """ABC note formatting. C4 = middle C = 'C' in ABC.
    C5 = 'c', C3 = 'C,', C2 = 'C,,', C6 = "c'" etc.
    """
    letter = name[0]
    acc = '' if name in KEY_ACC.get(key, set()) else ('^' if '#' in name else ('_' if 'b' in name else ''))
    if octave >= 6: return acc + letter.lower() + "'" * (octave - 5)
    elif octave == 5: return acc + letter.lower()
    elif octave == 4: return acc + letter.upper()
    else: return acc + letter.upper() + ',' * (4 - octave)

def run_to_abc(notes, key, voice=''):
    """Convert list of MIDI notes to beamed ABC with 8va/8vb markings.

    Notes above A5 (MIDI 81, ~3 ledger lines above treble) get 8va.
    Notes below E2 (MIDI 40, ~3 ledger lines below bass) get 8vb.
    """
    if not notes: return ''

    # Thresholds for 8va/8vb (about 3 ledger lines from staff)
    HIGH_THRESH = 81  # A5 — start 8va above here
    LOW_THRESH = 36   # C2 — only the very bottom gets 8vb

    parts = []
    in_8va = False
    in_8vb = False
    i = 0
    while i < len(notes):
        if notes[i] == 0:
            # Close any ottava before rests
            if in_8va:
                parts.append('!8va)!')
                in_8va = False
            if in_8vb:
                parts.append('!8vb)!')
                in_8vb = False
            j = i
            while j < len(notes) and notes[j] == 0: j += 1
            n = j - i
            # Use invisible rest (x) instead of visible rest (z) for grand staff spacers
            parts.append(f'x{n}' if n > 1 else 'x')
            i = j
        else:
            j = i
            beam = ''
            while j < len(notes) and notes[j] != 0:
                m = notes[j]
                # Check if we need to start/stop 8va or 8vb
                if m > HIGH_THRESH and not in_8va:
                    if in_8vb:
                        beam += '!8vb)!'
                        in_8vb = False
                    beam += '!8va(!'
                    in_8va = True
                elif m <= HIGH_THRESH and in_8va:
                    beam += '!8va)!'
                    in_8va = False
                if m < LOW_THRESH and not in_8vb:
                    if in_8va:
                        beam += '!8va)!'
                        in_8va = False
                    beam += '!8vb(!'
                    in_8vb = True
                elif m >= LOW_THRESH and in_8vb:
                    beam += '!8vb)!'
                    in_8vb = False
                beam += midi_to_abc(m, key)
                j += 1
            parts.append(beam)
            i = j

    # Close any open ottava
    if in_8va: parts.append('!8va)!')
    if in_8vb: parts.append('!8vb)!')

    return ' '.join(parts)


# ── Run builder ──

def build_4chord_run(deg_a, pat_a, deg_b, pat_b, deg_c, pat_c, deg_d, pat_d, key):
    """Build a Tchaikovsky 4-chord sweep across the full harp.

    Ascending: A tones (bottom half) → B tones (top half), every chord tone once.
    Descending: C tones (top half) → D tones (bottom half), every chord tone once.

    Returns: list of MIDI values (the complete run, no padding).
    """
    a_all = sorted(pattern_tones(deg_a, pat_a, key, HARP_LOW, HARP_HIGH))
    b_all = sorted(pattern_tones(deg_b, pat_b, key, HARP_LOW, HARP_HIGH))
    c_all = sorted(pattern_tones(deg_c, pat_c, key, HARP_LOW, HARP_HIGH))
    d_all = sorted(pattern_tones(deg_d, pat_d, key, HARP_LOW, HARP_HIGH))

    if not a_all: a_all = [48, 55, 60]
    if not b_all: b_all = a_all
    if not c_all: c_all = b_all
    if not d_all: d_all = a_all

    # ASCENDING: all of A, then B continues above where A ended — no repeated pitches
    a_top = a_all[-1] if a_all else HARP_LOW
    a_used = set(a_all)
    b_cont = [t for t in b_all if t > a_top and t not in a_used]
    ascending = a_all + b_cont

    # DESCENDING: all of C from peak down, then D continues below — no repeated pitches
    peak = ascending[-1] if ascending else HARP_HIGH
    c_desc = sorted([t for t in c_all if t <= peak], reverse=True)
    c_used = set(c_desc)
    c_bot = c_desc[-1] if c_desc else HARP_LOW
    d_cont = sorted([t for t in d_all if t < c_bot and t not in c_used], reverse=True)
    descending = c_desc + d_cont

    # One full sweep
    run = ascending + descending

    # If the run is too short for a full bar, repeat the sweep to fill
    # (Tchaikovsky often does multiple sweeps per measure)
    if len(run) > 0:
        full_sweep = list(run)
        while len(run) < 80:  # enough for any time sig (max 4/4 = 64)
            run += full_sweep

    return run


def _pick(pool, count):
    """Pick exactly `count` notes from pool — each note used once, in order.
    If pool is longer, take the first `count`. If shorter, return only
    what's available (caller handles the deficit).
    """
    if count <= 0: return []
    if not pool: return []
    if len(pool) >= count:
        return pool[:count]
    else:
        return list(pool)  # return what we have, no repeats


# ── Chord selection logic ──

def select_4chords(cur_deg, next_deg, measure_idx, hymn_idx):
    """Select 4 chords (degrees + patterns) for a Tchaikovsky run.

    cur_deg: current measure's chord degree
    next_deg: next measure's chord degree (or None)

    Returns: (deg_a, pat_a, deg_b, pat_b, deg_c, pat_c, deg_d, pat_d,
              label_a, label_b, label_c, label_d)
    """
    seed = hymn_idx * 17 + measure_idx * 7 + cur_deg * 3

    if next_deg is not None and next_deg != cur_deg:
        # Two different chords available: current up, next down
        deg_a = cur_deg
        deg_b = cur_deg  # same chord continues to treble
        deg_c = next_deg  # next chord starts descent
        deg_d = next_deg  # next chord finishes in bass

        # For extra color: sometimes use a color pair for B instead of same chord
        if seed % 3 == 0:
            partners = COLOR_PAIRS.get(cur_deg, [cur_deg])
            deg_b = partners[seed % len(partners)]
    else:
        # Single chord — pair with color partner
        partners = COLOR_PAIRS.get(cur_deg, [cur_deg])
        partner = partners[(seed // 3) % len(partners)]

        deg_a = cur_deg
        deg_b = partner    # color chord in treble going up
        deg_c = partner    # same color chord descending
        deg_d = cur_deg    # return to home chord in bass

    # Pick patterns for each phase
    pat_a = pick_pattern(BASS_PATTERNS, seed)
    pat_b = pick_pattern(TREBLE_PATTERNS, seed + 1)
    pat_c = pick_pattern(TREBLE_PATTERNS, seed + 2)
    pat_d = pick_pattern(BASS_PATTERNS, seed + 3)

    lab_a = table_label(pat_a, deg_a)
    lab_b = table_label(pat_b, deg_b)
    lab_c = table_label(pat_c, deg_c)
    lab_d = table_label(pat_d, deg_d)

    return (deg_a, pat_a, deg_b, pat_b, deg_c, pat_c, deg_d, pat_d,
            lab_a, lab_b, lab_c, lab_d)


# ── Lead sheet parsing ──

def parse_lead_sheet(abc_str):
    """Extract measures with chord symbols and melody from lead sheet ABC."""
    lines = abc_str.split('\n')
    time_sig = '4/4'; note_len = '1/8'; tempo = 100

    for line in lines:
        if line.startswith('M:'): time_sig = line.split(':',1)[1].strip()
        elif line.startswith('L:'): note_len = line.split(':',1)[1].strip()
        elif line.startswith('Q:'):
            qm = re.search(r'=(\d+)', line)
            if qm: tempo = int(qm.group(1))
        elif line.startswith('K:'):
            idx = lines.index(line)
            mel_body = ' '.join(lines[idx+1:]).strip()
            break
    else:
        mel_body = ''

    bars = re.split(r'\|+', mel_body)
    bars = [b.strip() for b in bars if b.strip()]

    measures = []
    for bar in bars:
        chords = re.findall(r'"\^([^"]+)"', bar)
        mel = re.sub(r'"\^[^"]*"', '', bar).strip()
        measures.append({'chords': chords, 'mel': mel})

    return measures, time_sig, note_len, tempo


def notes_per_bar(ts):
    """Number of 64th notes per bar."""
    m = re.match(r'(\d+)/(\d+)', ts)
    if not m: return 64
    return int(m.group(1)) * (64 // int(m.group(2)))


# ── Main pipeline ──

def rescale_melody(mel_abc, scale):
    """Rescale ABC melody durations by a factor.

    E.g., scale=8 turns L:1/8 notes into L:1/64 notes:
    'D' → 'D8', 'D2' → 'D16', 'D/2' → 'D4', 'D3/2' → 'D12'
    """
    if scale == 1:
        return mel_abc

    result = []
    i = 0
    s = mel_abc
    while i < len(s):
        # Skip non-note characters
        if s[i] in ' \t':
            result.append(s[i]); i += 1; continue
        if s[i] == 'z' or s[i] == 'Z' or s[i] == 'x':
            result.append(s[i]); i += 1
            # Parse duration after rest
            dur, i = _parse_dur(s, i)
            new_dur = _scale_dur(dur, scale)
            result.append(new_dur)
            continue
        if s[i] in '()~.':
            result.append(s[i]); i += 1; continue
        # Accidentals
        if s[i] in '^_=':
            result.append(s[i]); i += 1
            if i < len(s) and s[i] in '^_':
                result.append(s[i]); i += 1
            continue
        # Note letter
        if s[i].upper() in 'ABCDEFG':
            result.append(s[i]); i += 1
            # Octave modifiers
            while i < len(s) and s[i] in "',":
                result.append(s[i]); i += 1
            # Parse duration
            dur, i = _parse_dur(s, i)
            new_dur = _scale_dur(dur, scale)
            result.append(new_dur)
            continue
        # Anything else (brackets, etc.)
        result.append(s[i]); i += 1

    return ''.join(result)


def _parse_dur(s, i):
    """Parse an ABC duration starting at position i. Returns (dur_string, new_i)."""
    start = i
    # Numerator digits
    while i < len(s) and s[i].isdigit(): i += 1
    # Slash and denominator
    if i < len(s) and s[i] == '/':
        i += 1
        while i < len(s) and s[i].isdigit(): i += 1
    return s[start:i], i


def _scale_dur(dur_str, scale):
    """Scale an ABC duration string by a factor. Returns new duration string."""
    if not dur_str:
        # Bare note = duration 1
        return str(scale)

    if '/' in dur_str:
        parts = dur_str.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
        # num/den * scale
        new_num = num * scale
        # Simplify
        from math import gcd
        g = gcd(new_num, den)
        new_num //= g
        den //= g
        if den == 1:
            return str(new_num)
        return f'{new_num}/{den}'
    else:
        # Integer duration
        num = int(dur_str)
        return str(num * scale)


def compute_bar_duration(mel_abc, full_bar):
    """Compute actual duration of a melody bar in 64ths.
    Returns the melody's duration, which may be less than full_bar for pickups.
    """
    total = 0
    i = 0
    s = mel_abc.strip()
    while i < len(s):
        c = s[i]
        if c in ' \t': i += 1; continue
        if c in '()~.^_=': i += 1; continue
        if c == 'z' or c == 'x':
            i += 1
            dur, i = _parse_dur(s, i)
            total += _dur_to_64ths(dur)
            continue
        if c.upper() in 'ABCDEFG':
            i += 1
            while i < len(s) and s[i] in "',": i += 1
            dur, i = _parse_dur(s, i)
            total += _dur_to_64ths(dur)
            continue
        i += 1
    return total if total > 0 else full_bar


def _dur_to_64ths(dur_str):
    """Convert ABC duration string (already in L:1/64 units) to count."""
    if not dur_str:
        return 1
    if '/' in dur_str:
        parts = dur_str.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
        return num // den if den > 0 else 1
    return int(dur_str)


def build_hymn(ls, hymn_idx):
    key = ls['key']
    if key not in SCALES: return None

    measures, ts, nl, tempo = parse_lead_sheet(ls['abc'])
    spb = notes_per_bar(ts)

    header = (
        f"X: {ls['n']}\nT: {ls['t']}\nM: {ts}\nL: 1/64\n"
        f"Q: 1/4={tempo}\n"
        f"%%pagewidth 2000cm\n%%continueall 1\n%%scale 0.85\n%%writefields T 0\n"
        f"%%gchordfont Times-Roman 14\n"
        f"%%staffsep 0.5cm\n%%sysstaffsep 0.3cm\n"
        f"%%leftmargin 0.5cm\n%%rightmargin 0.5cm\n%%topspace 0\n%%musicspace 0\n"
        f"%%score 1 {{2 3}}\n"
        f"V:1 clef=treble name=\"Mel\"\n"
        f"V:2 clef=treble\n"
        f"V:3 clef=bass\n"
        f"K: {key}\n"
    )

    # Compute melody duration scale factor: original L to 1/64
    nl_m = re.match(r'(\d+)/(\d+)', nl)
    if nl_m:
        nl_num, nl_den = int(nl_m.group(1)), int(nl_m.group(2))
    else:
        nl_num, nl_den = 1, 8
    mel_scale = (64 * nl_num) // nl_den  # e.g., L:1/8 → scale=8, L:1/4 → scale=16

    mel_line = '[V:1] '
    rh_line = '[V:2] '
    lh_line = '[V:3] '
    npb = []
    prev_chords = None  # carry forward for measures with no chord annotation

    # Middle C = MIDI 60. Notes >= 60 go on RH staff, < 60 on LH staff.
    MID_C = 60

    for mi, meas in enumerate(measures):
        mel_raw = meas['mel']
        chords = meas['chords']
        npb.append(len(re.findall(r'[A-Ga-g]', mel_raw)))

        # Rescale melody durations from original L to L:1/64
        mel = rescale_melody(mel_raw, mel_scale)

        # Compute actual bar duration in 64ths for this measure
        bar_dur = compute_bar_duration(mel, spb)

        if not chords:
            chords = prev_chords  # carry forward previous chord
        if not chords:
            mel_line += mel + ' | '
            rh_line += f'x{bar_dur} | '
            lh_line += f'x{bar_dur} | '
            continue
        prev_chords = chords

        # Get current chord degree
        cur_deg = chord_to_degree(chords[0], key)
        if cur_deg is None:
            mel_line += mel + ' | '
            rh_line += f'x{bar_dur} | '
            lh_line += f'x{bar_dur} | '
            continue

        # Get next measure's chord for descent
        next_deg = None
        if mi + 1 < len(measures) and measures[mi + 1]['chords']:
            next_deg = chord_to_degree(measures[mi + 1]['chords'][0], key)

        # If measure has 2+ chords, use second chord as transition
        if len(chords) >= 2:
            deg2 = chord_to_degree(chords[1], key)
            if deg2 is not None:
                next_deg = deg2

        # Select 4 chords and patterns
        (da, pa, db, pb, dc, pc, dd, pd,
         la, lb, lc, ld) = select_4chords(cur_deg, next_deg, mi, hymn_idx)

        # Build the run — every chord tone on the harp, up then down
        harp_run = build_4chord_run(da, pa, db, pb, dc, pc, dd, pd, key)

        # Fit to measure: truncate if too long, pad if too short
        if len(harp_run) > bar_dur:
            harp_run = harp_run[:bar_dur]
        elif len(harp_run) < bar_dur:
            harp_run = harp_run + [0] * (bar_dur - len(harp_run))

        # Count actual notes AFTER truncation
        note_count = sum(1 for m in harp_run if m != 0)

        # Build label: up chords → down chords
        # Show each unique chord once, separated by arrows for transitions
        up_chords = [la] if la == lb else [la, lb]
        dn_chords = [lc] if lc == ld else [lc, ld]
        up_str = '>'.join(up_chords)
        dn_str = '>'.join(dn_chords)
        if up_str == dn_str:
            label = up_str
        else:
            label = f'{up_str} / {dn_str}'

        # Chord label goes ABOVE melody staff (gchord format for serif font)
        mel_line += f'"{label}" ' + mel + ' | '

        # Split into RH (>= middle C) and LH (< middle C) for grand staff
        rh_notes = []
        lh_notes = []
        for note in harp_run:
            if note == 0:
                rh_notes.append(0)
                lh_notes.append(0)
            elif note >= MID_C:
                rh_notes.append(note)
                lh_notes.append(0)
            else:
                rh_notes.append(0)
                lh_notes.append(note)

        rh_line += run_to_abc(rh_notes, key) + ' | '
        lh_line += f'"_{note_count}" ' + run_to_abc(lh_notes, key) + ' | '

    mel_line = mel_line.rstrip(' | ') + ' |]'
    rh_line = rh_line.rstrip(' | ') + ' |]'
    lh_line = lh_line.rstrip(' | ') + ' |]'

    abc = header + mel_line + '\n' + rh_line + '\n' + lh_line + '\n'

    return {
        'n': ls['n'], 't': ls['t'], 'abc': abc,
        'key': key, 'npb': npb, 'tempo': tempo,
    }


def main():
    print("Loading lead sheets...")
    with open(LEAD_SHEETS) as f:
        lead_sheets = json.load(f)
    print(f"  {len(lead_sheets)} hymns")

    print("Building Tchaikovsky drills...")
    output = []
    for idx, ls in enumerate(lead_sheets):
        result = build_hymn(ls, idx)
        if result:
            output.append(result)
            if len(output) <= 3:
                print(f"  [{len(output)}] {result['t']} key={result['key']} bars={len(result['npb'])}")
                for ln in result['abc'].split('\n'):
                    if ln.startswith('[V:'):
                        print(f"      {ln[:140]}...")

    print(f"\nWriting {len(output)} drills to {OUTPUT}...")
    with open(OUTPUT, 'w') as f:
        json.dump(output, f)
    print(f"Done. {os.path.getsize(OUTPUT) / 1024:.0f} KB")


if __name__ == '__main__':
    main()
