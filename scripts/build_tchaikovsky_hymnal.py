#!/usr/bin/env python3
"""Build Tchaikovsky-style harp drills from OpenHymnal lead sheets.

Simplified notation: block chords with glissando lines.
Each measure shows 3 chord blocks: start → peak → end.
The player fills the measure by sweeping through chord tones.

Output: app/tchaikovsky_data.json
"""

import json, re, sys, os
from pathlib import Path
from math import gcd

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

HARP_LOW = 36; HARP_HIGH = 91  # C2 to G6, 33 strings
MID_C = 60

# ── Chord table ──
PATTERNS = {
    '3-3': (2,2), '3-4': (2,3), '4-2': (3,1), '4-3': (3,2),
    '4-4': (3,3), '2-4': (1,3),
    '3-3-3': (2,2,2), '3-3-2': (2,2,1), '3-3-4': (2,2,3),
    '3-2-3': (2,1,2), '2-3-3': (1,2,2), '3-4-2': (2,3,1),
    '4-3-3': (3,2,2), '4-4-4': (3,3,3),
}
TABLE_NAMES = {
    '3-3':   ['I',      'iim',     'iiim',    'IV',      'V',       'vim',     'vii\u00b0'],
    '3-4':   ['I\u00b9','iim\u00b9','iiim\u00b9','IV\u00b9','V\u00b9','vim\u00b9','vii\u00b0\u00b9'],
    '4-3':   ['I\u00b2','iim\u00b2','iiim\u00b2','IV\u00b2','V\u00b2','vim\u00b2','vii\u00b0\u00b2'],
    '4-2':   ['IV\u00b9','V\u00b9','vim\u00b9','vii\u00b0\u00b9','I\u00b9','iim\u00b9','iiim\u00b2'],
    '4-4':   ['Iq',     'iiq',     'iiiq',    'IVq',     'Vq',      'viq',     'vii\u00b0q'],
    '2-4':   ['IM7-5\u00b2','iim7-5\u00b2','iiim7-5\u00b2','IVM7-5\u00b2','V7-5\u00b2','vim7-5\u00b2','Vq\u00b2'],
    '3-3-3': ['IM7',    'iim7',    'iiim7',   'IVM7',    'V7',      'vim7',    'vii\u00f87'],
    '3-3-2': ['I6',     'iim6',    'iiim6',   'IV6',     'V6',      'vim6',    'vii\u00b06'],
    '3-3-4': ['I+9',    'ii+9',    'iii+9',   'IV+9',    'V+9',     'vi+9',    'vii\u00b0+9'],
    '3-2-3': ['IM7\u00b2','iim7\u00b2','iiim7\u00b2','IVM7\u00b2','V7\u00b2','vim7\u00b2','vii\u00f87\u00b2'],
    '2-3-3': ['IM7\u00b3','iim7\u00b3','iiim7\u00b3','IVM7\u00b3','V7\u00b3','vim7\u00b3','vii\u00f87\u00b3'],
    '3-4-2': ['I9-5',   'ii9-5',   'iii9-5',  'IV9-5',   'V9-5',    'vi9-5',   'vii\u00b09-5'],
    '4-3-3': ['I9-3',   'ii9-3',   'iii9-3',  'IV9-3',   'V9-3',    'vi9-3',   'vii\u00b09-3'],
    '4-4-4': ['Iq7',    'iiq7',    'iiiq7',   'IVq7',    'Vq7',     'viq7',    'vii\u00b0q7'],
}

COLOR_PAIRS = {
    0: [5, 3, 4], 1: [3, 4, 5], 2: [0, 5, 4], 3: [0, 1, 4],
    4: [0, 2, 5], 5: [0, 3, 2], 6: [4, 0, 3],
}
BASS_PATTERNS = ['3-3', '4-3', '3-4', '4-4', '3-3-3']
TREBLE_PATTERNS = ['3-3-3', '3-3', '3-3-2', '3-2-3', '3-3-4', '4-3-3', '2-3-3']


def chord_to_degree(chord_str, key):
    m = re.match(r'^([A-G][#b]?)', chord_str)
    if not m: return None
    root_pc = NOTE_SEMI.get(m.group(1))
    if root_pc is None: return None
    for deg, name in enumerate(SCALES.get(key, [])):
        if NOTE_SEMI[name] == root_pc: return deg
    return None


def pattern_tones(degree, pattern_name, key, low, high):
    intervals = PATTERNS[pattern_name]
    degs = {degree}; cur = degree
    for step in intervals: cur = (cur + step) % 7; degs.add(cur)
    scale = SCALES[key]
    pcs = set(NOTE_SEMI[scale[d]] for d in degs)
    return sorted(m for m in range(low, high + 1) if m % 12 in pcs)


def pick_pattern(pool, seed):
    return pool[seed % len(pool)]


def table_label(pattern_name, degree):
    if pattern_name in TABLE_NAMES: return TABLE_NAMES[pattern_name][degree]
    return f'd{degree+1}_{pattern_name}'


# ── ABC formatting ──

def _fmt(name, octave, key='C'):
    letter = name[0]
    acc = '' if name in KEY_ACC.get(key, set()) else ('^' if '#' in name else ('_' if 'b' in name else ''))
    if octave >= 6: return acc + letter.lower() + "'" * (octave - 5)
    elif octave == 5: return acc + letter.lower()
    elif octave == 4: return acc + letter.upper()
    else: return acc + letter.upper() + ',' * (4 - octave)


def midi_to_abc(midi, key):
    scale = SCALES.get(key, SCALES['C'])
    pc = midi % 12; octave = (midi // 12) - 1
    for note in scale:
        if NOTE_SEMI[note] == pc: return _fmt(note, octave, key)
    names = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
    return _fmt(names[pc], octave, key)


def block_chord_abc(midis, key, dur=''):
    """Build ABC block chord from sorted MIDI list. e.g. [CEG]4"""
    if not midis: return f'z{dur}'
    if len(midis) == 1: return midi_to_abc(midis[0], key) + dur
    notes = ''.join(midi_to_abc(m, key) for m in sorted(midis))
    return f'[{notes}]{dur}'


# ── Build block chords for each measure ──

def select_4chords(cur_deg, next_deg, measure_idx, hymn_idx):
    seed = hymn_idx * 17 + measure_idx * 7 + cur_deg * 3
    if next_deg is not None and next_deg != cur_deg:
        deg_a, deg_b = cur_deg, cur_deg
        deg_c, deg_d = next_deg, next_deg
        if seed % 3 == 0:
            partners = COLOR_PAIRS.get(cur_deg, [cur_deg])
            deg_b = partners[seed % len(partners)]
    else:
        partners = COLOR_PAIRS.get(cur_deg, [cur_deg])
        partner = partners[(seed // 3) % len(partners)]
        deg_a, deg_b = cur_deg, partner
        deg_c, deg_d = partner, cur_deg

    pat_a = pick_pattern(BASS_PATTERNS, seed)
    pat_b = pick_pattern(TREBLE_PATTERNS, seed + 1)
    pat_c = pick_pattern(TREBLE_PATTERNS, seed + 2)
    pat_d = pick_pattern(BASS_PATTERNS, seed + 3)

    return (deg_a, pat_a, deg_b, pat_b, deg_c, pat_c, deg_d, pat_d,
            table_label(pat_a, deg_a), table_label(pat_b, deg_b),
            table_label(pat_c, deg_c), table_label(pat_d, deg_d))


def build_measure_chords(deg_a, pat_a, deg_b, pat_b, deg_c, pat_c, deg_d, pat_d, key):
    """Build 3 block chords for a measure: start, peak, end.

    Start = A chord tones in bass (bottom 3-4 notes)
    Peak  = B chord tones in treble (top 3-4 notes)
    End   = D chord tones in bass (bottom 3-4 notes)

    Returns: (start_midis, peak_midis, end_midis)
    """
    a_all = pattern_tones(deg_a, pat_a, key, HARP_LOW, MID_C)
    b_all = pattern_tones(deg_b, pat_b, key, MID_C, HARP_HIGH)
    d_all = pattern_tones(deg_d, pat_d, key, HARP_LOW, MID_C)

    # Take bottom 3-4 notes for start/end, top 3-4 for peak
    start = a_all[:4] if len(a_all) >= 4 else a_all[:3]
    peak = b_all[-4:] if len(b_all) >= 4 else b_all[-3:]
    end = d_all[:4] if len(d_all) >= 4 else d_all[:3]

    if not start: start = [HARP_LOW]
    if not peak: peak = [HARP_HIGH]
    if not end: end = start

    return start, peak, end


# ── Lead sheet parsing ──

def parse_lead_sheet(abc_str):
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


def rescale_melody(mel_abc, scale):
    if scale == 1: return mel_abc
    result = []; i = 0; s = mel_abc
    while i < len(s):
        if s[i] in ' \t': result.append(s[i]); i += 1; continue
        if s[i] in '()~.': result.append(s[i]); i += 1; continue
        if s[i] in '^_=':
            result.append(s[i]); i += 1
            if i < len(s) and s[i] in '^_': result.append(s[i]); i += 1
            continue
        if s[i] == 'z' or s[i] == 'x':
            result.append(s[i]); i += 1
            dur, i = _parse_dur(s, i)
            result.append(_scale_dur(dur, scale))
            continue
        if s[i].upper() in 'ABCDEFG':
            result.append(s[i]); i += 1
            while i < len(s) and s[i] in "',": result.append(s[i]); i += 1
            dur, i = _parse_dur(s, i)
            result.append(_scale_dur(dur, scale))
            continue
        result.append(s[i]); i += 1
    return ''.join(result)

def _parse_dur(s, i):
    start = i
    while i < len(s) and s[i].isdigit(): i += 1
    if i < len(s) and s[i] == '/':
        i += 1
        while i < len(s) and s[i].isdigit(): i += 1
    return s[start:i], i

def _scale_dur(dur_str, scale):
    if not dur_str: return str(scale)
    if '/' in dur_str:
        parts = dur_str.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
        new_num = num * scale
        g = gcd(new_num, den)
        new_num //= g; den //= g
        if den == 1: return str(new_num)
        return f'{new_num}/{den}'
    return str(int(dur_str) * scale)

def compute_bar_duration(mel_abc, full_bar):
    total = 0; i = 0; s = mel_abc.strip()
    while i < len(s):
        c = s[i]
        if c in ' \t': i += 1; continue
        if c in '()~.^_=': i += 1; continue
        if c in 'zx':
            i += 1; dur, i = _parse_dur(s, i)
            total += _dur_val(dur); continue
        if c.upper() in 'ABCDEFG':
            i += 1
            while i < len(s) and s[i] in "',": i += 1
            dur, i = _parse_dur(s, i)
            total += _dur_val(dur); continue
        i += 1
    return int(round(total)) if total > 0 else full_bar

def _dur_val(dur_str):
    """Return duration as a float in L units."""
    if not dur_str: return 1.0
    if '/' in dur_str:
        parts = dur_str.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
        return num / den if den > 0 else 1.0
    return float(dur_str)


def beats_per_bar(ts):
    m = re.match(r'(\d+)/(\d+)', ts)
    if not m: return 4
    return int(m.group(1))


# ── Main pipeline ──

def build_hymn(ls, hymn_idx):
    key = ls['key']
    if key not in SCALES: return None
    measures, ts, nl, tempo = parse_lead_sheet(ls['abc'])
    bpb = beats_per_bar(ts)

    # Melody uses original L, harp uses half notes / quarter notes for block chords
    # Each measure = 3 block chords: start (1/3), peak (1/3), end (1/3)
    # Use the original L unit for melody, same for harp chords
    # Time sig denominator tells us the beat unit
    ts_m = re.match(r'(\d+)/(\d+)', ts)
    beat_unit = int(ts_m.group(2)) if ts_m else 4

    header = (
        f"X: {ls['n']}\nT: {ls['t']}\nM: {ts}\nL: 1/{beat_unit}\n"
        f"Q: 1/4={tempo}\n"
        f"%%pagewidth 2000cm\n%%continueall 1\n%%scale 0.85\n%%writefields T 0\n"
        f"%%staffsep 0.5cm\n%%sysstaffsep 0.3cm\n"
        f"%%gchordfont Times-Roman 14\n"
        f"%%leftmargin 0.5cm\n%%rightmargin 0.5cm\n%%topspace 0\n%%musicspace 0\n"
        f"%%score 1 {{2 3}}\n"
        f"V:1 clef=treble name=\"Mel\"\n"
        f"V:2 clef=treble\n"
        f"V:3 clef=bass\n"
        f"K: {key}\n"
    )

    # Compute melody rescale: original L to 1/beat_unit
    nl_m = re.match(r'(\d+)/(\d+)', nl)
    if nl_m:
        nl_num, nl_den = int(nl_m.group(1)), int(nl_m.group(2))
    else:
        nl_num, nl_den = 1, 8
    mel_scale = (beat_unit * nl_num) // nl_den  # e.g. L:1/8 to L:1/4 = scale 0.5... hmm

    # Actually simpler: keep melody at its own L unit via inline [L:]
    # and harp at the same L unit. Both use the header L.
    # If header L = 1/4 and melody was L:1/8, melody notes need dur/2

    # Simplest: set header L = original melody L, and give harp chords explicit durations
    header = (
        f"X: {ls['n']}\nT: {ls['t']}\nM: {ts}\nL: {nl}\n"
        f"Q: 1/4={tempo}\n"
        f"%%pagewidth 2000cm\n%%continueall 1\n%%scale 0.85\n%%writefields T 0\n"
        f"%%staffsep 0.5cm\n%%sysstaffsep 0.3cm\n"
        f"%%gchordfont Times-Roman 14\n"
        f"%%leftmargin 0.5cm\n%%rightmargin 0.5cm\n%%topspace 0\n%%musicspace 0\n"
        f"%%score 1 {{2 3}}\n"
        f"V:1 clef=treble name=\"Mel\"\n"
        f"V:2 clef=treble\n"
        f"V:3 clef=bass\n"
        f"K: {key}\n"
    )

    # In the header L unit, how many units per bar?
    ts_num = int(ts_m.group(1)) if ts_m else 4
    ts_den = int(ts_m.group(2)) if ts_m else 4
    # L units per bar = ts_num * (nl_den / ts_den) * nl_num
    # e.g. 3/4 with L:1/8 = 3 * (8/4) * 1 = 6 eighth notes per bar
    units_per_bar = ts_num * nl_den // ts_den * nl_num

    mel_line = '[V:1] '
    rh_line = '[V:2] '
    lh_line = '[V:3] '
    npb = []
    prev_chords = None

    for mi, meas in enumerate(measures):
        mel_raw = meas['mel']
        chords = meas['chords']
        npb.append(len(re.findall(r'[A-Ga-g]', mel_raw)))

        if not chords:
            chords = prev_chords
        if not chords:
            mel_line += mel_raw + ' | '
            rh_line += f'x{units_per_bar} | '
            lh_line += f'x{units_per_bar} | '
            continue
        prev_chords = chords

        cur_deg = chord_to_degree(chords[0], key)
        if cur_deg is None:
            mel_line += mel_raw + ' | '
            rh_line += f'x{units_per_bar} | '
            lh_line += f'x{units_per_bar} | '
            continue

        next_deg = None
        if mi + 1 < len(measures) and measures[mi + 1]['chords']:
            next_deg = chord_to_degree(measures[mi + 1]['chords'][0], key)
        if len(chords) >= 2:
            deg2 = chord_to_degree(chords[1], key)
            if deg2 is not None: next_deg = deg2

        (da,pa,db,pb,dc,pc,dd,pd,la,lb,lc,ld) = select_4chords(cur_deg, next_deg, mi, hymn_idx)
        start, peak, end = build_measure_chords(da,pa,db,pb,dc,pc,dd,pd, key)

        # Build chord label
        up_chords = [la] if la == lb else [la, lb]
        dn_chords = [lc] if lc == ld else [lc, ld]
        up_str = '>'.join(up_chords)
        dn_str = '>'.join(dn_chords)

        # Stacked fraction: ascending chords above, descending chords below melody
        if up_str == dn_str:
            mel_line += f'"^{up_str}" ' + mel_raw + ' | '
        else:
            mel_line += f'"^{up_str}" "_{dn_str}" ' + mel_raw + ' | '

        # Compute actual bar duration from melody
        mel_dur = compute_bar_duration(mel_raw, units_per_bar)

        # 3 chords per bar: start, peak, end
        # Divide the bar into 3 roughly equal parts
        d1 = mel_dur // 3
        d2 = mel_dur // 3
        d3 = mel_dur - d1 - d2

        # Split start/end into LH (below mid C) and peak into RH (above mid C)
        start_lh = [m for m in start if m < MID_C]
        start_rh = [m for m in start if m >= MID_C]
        peak_lh = [m for m in peak if m < MID_C]
        peak_rh = [m for m in peak if m >= MID_C]
        end_lh = [m for m in end if m < MID_C]
        end_rh = [m for m in end if m >= MID_C]

        # RH: invisible rest for start, peak chord, invisible rest for end
        if start_rh:
            rh_line += f'!arpeggio!{block_chord_abc(start_rh, key, str(d1))} '
        else:
            rh_line += f'x{d1} '

        if peak_rh:
            rh_line += f'!arpeggio!{block_chord_abc(peak_rh, key, str(d2))} '
        else:
            rh_line += f'x{d2} '

        if end_rh:
            rh_line += f'!arpeggio!{block_chord_abc(end_rh, key, str(d3))} | '
        else:
            rh_line += f'x{d3} | '

        # LH: start chord, invisible rest for peak, end chord
        if start_lh:
            lh_line += f'!arpeggio!{block_chord_abc(start_lh, key, str(d1))} '
        else:
            lh_line += f'x{d1} '

        if peak_lh:
            lh_line += f'!arpeggio!{block_chord_abc(peak_lh, key, str(d2))} '
        else:
            lh_line += f'x{d2} '

        if end_lh:
            lh_line += f'!arpeggio!{block_chord_abc(end_lh, key, str(d3))} | '
        else:
            lh_line += f'x{d3} | '

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
