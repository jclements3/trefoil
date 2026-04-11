#!/usr/bin/env python3
"""Build Tchaikovsky-style harp drills from OpenHymnal lead sheets.

Each measure renders a continuous chord-tone sweep across the full
33-string harp (C2 to G6), up and down, as GRACE NOTES on the grand
staff. Grace notes take zero bar time so barlines always align with
the melody regardless of how many chord tones the sweep hits.

For 1-4 chord phases per bar:
  A = start (bottom going up)
  B = top going up
  C = top going down
  D = end (bottom going down)

The sweep walks string 1..33 and emits every string that is a chord
tone of the current phase's chord. The divide between the bottom
(LH bass) and top (RH treble) halves is at string 16 (~middle C).

Chord annotations are placed on the melody voice (V:1) in roman-numeral
form from CHORD_NAMES, with bold roman-numeral parts via $1/$0.
"""

import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_drill import (
    PAT_MAP, CHORD_NAMES, VALID, NOTES_PER_OCT,
    pattern_strings, string_to_abc, is_rh,
)

LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
OUTPUT = ROOT / 'app' / 'tchaikovsky_data.json'

HARP_LOW = 1
HARP_HIGH = 33
STAFF_DIVIDE = 14  # strings 1..14 → LH (bass), 15..33 → RH (treble, middle C = string 15)

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

# Phase chord-index mapping: (bot-asc, top-asc, top-dsc, bot-dsc)
SWEEP_PHASES = {
    1: (0, 0, 0, 0),
    2: (0, 1, 1, 0),
    3: (0, 1, 1, 2),
    4: (0, 1, 2, 3),
}


def deg_to_first_string(key, deg_1based):
    scale_note = SCALES[key][deg_1based - 1]
    letter = scale_note[0]
    return NOTES_PER_OCT.index(letter) + 1


def _pick_row_deg(chord_deg, has_7th, inv):
    """Map (chord_deg, 7th-ness, inversion) → (handout_pattern_str, row_deg).

    The handout chord table is keyed by pattern row and row-deg (which is the
    Ionian "mode-index" of the pattern's first voicing tone, not always the
    chord's own scale degree). For inverted rows the row_deg is rotated away
    from chord_deg by a fixed offset — formulas verified against the 14×7
    entries in CHORD_NAMES (see handout_chord_table.tex).
    """
    cd = chord_deg
    if has_7th:
        if inv == 0: return ('333', cd)
        if inv == 1: return ('233', ((cd - 2) % 7) + 1)
        if inv == 2: return ('323', ((cd - 4) % 7) + 1)
        if inv == 3 and cd in (1, 4, 5):
            return ('332', ((cd + 1) % 7) + 1)
        # 3rd-inv 7ths on other degrees don't exist in the handout; fall back
        return ('333', cd)
    if inv == 0: return ('33', cd)
    if inv == 1: return ('43', ((cd + 3) % 7) + 1)
    if inv == 2: return ('34', ((cd + 1) % 7) + 1)
    return ('33', cd)


def chord_to_spec(chord_str, key, inv_hint=None):
    """Map 'D7' in 'G' to (start_string, pattern_str, deg, label).

    Returns None for non-diatonic chords. When `inv_hint` is given, it is a
    dict {'inv': 0..3, 'seventh': None|'min'|'maj'} derived from SATB
    analysis (see scripts/build_satb_chord_index.py); the function then
    selects an inverted handout row instead of the default root-position
    row 33 / 333. The sweep start_string comes from the row_deg returned
    by _pick_row_deg, so inversions drive different runs.
    """
    m = re.match(r'^([A-G][#b]?)(.*)$', chord_str)
    if not m:
        return None
    root, qual = m.group(1), m.group(2).strip()

    pc = NOTE_SEMI.get(root)
    if pc is None:
        return None
    chord_deg = None
    for i, name in enumerate(SCALES.get(key, [])):
        if NOTE_SEMI[name] == pc:
            chord_deg = i + 1
            break
    if chord_deg is None:
        return None

    # Prefer SATB-derived 7th-ness over parsing the chord-string suffix —
    # the SATB view catches "C" that actually sounds with a B (→ CΔ7) while
    # the string suffix from lead_sheets would miss it. Either path
    # detects 7ths correctly for the common cases.
    str_has_7th = qual in ('7', 'm7', 'Δ7', 'ø7', '°7')
    sat_has_7th = bool(inv_hint and inv_hint.get('seventh'))
    has_7th = str_has_7th or sat_has_7th
    inv = int(inv_hint['inv']) if (inv_hint and 'inv' in inv_hint) else 0

    pat, row_deg = _pick_row_deg(chord_deg, has_7th, inv)

    # Fall back along: (row_deg valid in requested pat) → root pos 333 / 33
    # → return None (non-handout-mappable chord, caller emits letter-name).
    if row_deg not in VALID.get(pat, []):
        pat, row_deg = ('333' if has_7th else '33', chord_deg)
        if row_deg not in VALID.get(pat, []):
            return None

    label = CHORD_NAMES.get((pat, row_deg))
    if label is None or label == '—':
        return None

    # start_string is anchored to the row's voicing-first-tone degree, so
    # inverted rows sweep different harp positions than root-pos rows even
    # when the underlying chord is the same.
    start = deg_to_first_string(key, row_deg)
    return (start, pat, row_deg, label)


def bold_roman(label):
    m = re.match(r'^([IVXLivxl]+)(.*)$', label)
    if not m:
        return label
    return f'$1{m.group(1)}$0{m.group(2)}'


def chord_tone_strings(chord_spec):
    """Return a set of all harp string positions (1..33) that are chord tones."""
    start, pat_str, _deg, _label = chord_spec
    pat = PAT_MAP[pat_str]
    tones = set()
    for oct_off in range(-14, 42, 7):
        for s in pattern_strings(start + oct_off, pat):
            if HARP_LOW <= s <= HARP_HIGH:
                tones.add(s)
    return tones


def build_sweep_strings(chord_specs):
    """Continuous up-and-down sweep — returns the ordered list of string positions."""
    n = len(chord_specs)
    if n < 1 or n > 4:
        return None
    phases = SWEEP_PHASES[n]

    tones_by_ci = [chord_tone_strings(spec) for spec in chord_specs]

    asc_strings = []
    for s in range(HARP_LOW, HARP_HIGH + 1):
        ci = phases[0] if s <= STAFF_DIVIDE else phases[1]
        if s in tones_by_ci[ci]:
            asc_strings.append(s)

    top_ascended = asc_strings[-1] if asc_strings else None
    dsc_strings = []
    peak_skipped = False
    for s in range(HARP_HIGH, HARP_LOW - 1, -1):
        if not peak_skipped and s == top_ascended:
            peak_skipped = True
            continue
        ci = phases[2] if s > STAFF_DIVIDE else phases[3]
        if s in tones_by_ci[ci]:
            dsc_strings.append(s)

    return asc_strings + dsc_strings


def build_sweep(chord_specs):
    """Cross-staff alternation sweep.

    Returns (rh_tokens, lh_tokens, total) — parallel lists where at each
    step one voice has the real note and the other has 'x', so only one
    staff plays at a time (unified cross-staff sweep).
    """
    strings = build_sweep_strings(chord_specs)
    if not strings:
        return None

    rh_tokens = []
    lh_tokens = []
    for s in strings:
        abc = string_to_abc(s)
        if is_rh(abc):
            rh_tokens.append(abc)
            lh_tokens.append('x')
        else:
            rh_tokens.append('x')
            lh_tokens.append(abc)
    return rh_tokens, lh_tokens, len(strings)


def fmt_run_tokens(tokens):
    """Beam notes together; space between rest groups and note groups."""
    result = []
    prev_is_rest = None
    for t in tokens:
        is_rest = (t == 'x')
        if prev_is_rest is not None and is_rest != prev_is_rest:
            result.append(' ')
        result.append(t)
        prev_is_rest = is_rest
    return ''.join(result)


# ── Lead sheet parsing ──

def parse_lead_sheet(abc_str):
    lines = abc_str.split('\n')
    time_sig = '4/4'
    note_len = '1/8'
    tempo = 100
    mel_body = ''
    for i, line in enumerate(lines):
        if line.startswith('M:'):
            time_sig = line.split(':', 1)[1].strip()
        elif line.startswith('L:'):
            note_len = line.split(':', 1)[1].strip()
        elif line.startswith('Q:'):
            qm = re.search(r'=(\d+)', line)
            if qm:
                tempo = int(qm.group(1))
        elif line.startswith('K:'):
            mel_body = ' '.join(lines[i + 1:]).strip()
            break
    bars = [b.strip() for b in re.split(r'\|+', mel_body) if b.strip()]
    return bars, time_sig, note_len, tempo


def extract_chords(bar_raw):
    return re.findall(r'"\^([^"]+)"', bar_raw)


def rewrite_chord_annotations(bar_raw, key):
    def repl(m):
        chord = m.group(1)
        spec = chord_to_spec(chord, key)
        if spec is None:
            return m.group(0)
        _, _, _, label = spec
        return f'"^{bold_roman(label)}"'
    return re.sub(r'"\^([^"]+)"', repl, bar_raw)


def rescale_melody(mel_abc, scale_num, scale_den):
    """Multiply note/rest durations by scale_num/scale_den. Pass quoted strings through."""
    if scale_num == 1 and scale_den == 1:
        return mel_abc
    result = []
    i = 0
    s = mel_abc
    while i < len(s):
        c = s[i]
        if c == '"':
            end = s.find('"', i + 1)
            if end == -1:
                result.append(s[i:])
                break
            result.append(s[i:end + 1])
            i = end + 1
            continue
        if c in ' \t()~.':
            result.append(c); i += 1; continue
        if c in '^_=':
            result.append(c); i += 1
            if i < len(s) and s[i] in '^_':
                result.append(s[i]); i += 1
            continue
        if c in 'zx' or c.upper() in 'ABCDEFG':
            result.append(c); i += 1
            while i < len(s) and s[i] in "',":
                result.append(s[i]); i += 1
            start = i
            while i < len(s) and s[i].isdigit():
                i += 1
            if i < len(s) and s[i] == '/':
                i += 1
                while i < len(s) and s[i].isdigit():
                    i += 1
            result.append(_scale_dur(s[start:i], scale_num, scale_den))
            continue
        result.append(c); i += 1
    return ''.join(result)


def _scale_dur(dur_str, sn, sd):
    from math import gcd
    if not dur_str:
        num, den = 1, 1
    elif '/' in dur_str:
        parts = dur_str.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
    else:
        num, den = int(dur_str), 1
    new_num = num * sn
    new_den = den * sd
    g = gcd(new_num, new_den)
    new_num //= g
    new_den //= g
    if new_den == 1:
        return str(new_num) if new_num != 1 else ''
    return f'{new_num}/{new_den}'


def compute_bar_duration(bar_str):
    """Return total duration in L-units, skipping quoted annotations."""
    total = 0.0
    i = 0
    s = bar_str
    while i < len(s):
        c = s[i]
        if c == '"':
            end = s.find('"', i + 1)
            if end == -1:
                break
            i = end + 1
            continue
        if c in ' \t()~.^_=':
            i += 1; continue
        if c in 'zx' or c.upper() in 'ABCDEFG':
            i += 1
            while i < len(s) and s[i] in "',":
                i += 1
            start = i
            while i < len(s) and s[i].isdigit():
                i += 1
            if i < len(s) and s[i] == '/':
                i += 1
                while i < len(s) and s[i].isdigit():
                    i += 1
            total += _dur_val(s[start:i])
            continue
        i += 1
    return int(round(total)) if total > 0 else 0


def _dur_val(d):
    if not d:
        return 1.0
    if '/' in d:
        parts = d.split('/')
        num = int(parts[0]) if parts[0] else 1
        den = int(parts[1]) if parts[1] else 2
        return num / den if den else 1.0
    return float(d)


def clamp_chords(chord_list):
    """Collapse consecutive duplicates, keep first 4."""
    out = []
    for c in chord_list:
        if not out or out[-1] != c:
            out.append(c)
    return out[:4]


def full_bar_length(time_sig, note_len):
    """Return the full-bar duration in L-units (used to detect pickups)."""
    tm = re.match(r'(\d+)/(\d+)', time_sig)
    if not tm:
        return 0
    ts_num, ts_den = int(tm.group(1)), int(tm.group(2))
    nm = re.match(r'(\d+)/(\d+)', note_len)
    if not nm:
        return 0
    ln_num, ln_den = int(nm.group(1)), int(nm.group(2))
    # L-units per bar = (ts_num / ts_den) / (ln_num / ln_den)
    return (ts_num * ln_den) // (ts_den * ln_num)


def build_hymn(ls):
    key = ls['key']
    if key not in SCALES:
        return None
    bars, ts, note_len, tempo = parse_lead_sheet(ls['abc'])

    # Melody keeps its original L. Harp voices set their own inline L.
    # Try L:1/32 first (3 beam lines — thinner); fall back to L:1/64 per-bar
    # if the sweep doesn't fit (24-note bar at 3/4, etc.).
    ts_m = re.match(r'(\d+)/(\d+)', ts)
    ts_num, ts_den = (int(ts_m.group(1)), int(ts_m.group(2))) if ts_m else (4, 4)
    nl_m = re.match(r'(\d+)/(\d+)', note_len)
    mel_num, mel_den = (int(nl_m.group(1)), int(nl_m.group(2))) if nl_m else (1, 8)
    full_bar_mel = full_bar_length(ts, note_len)

    header = (
        f"X: {ls['n']}\nT: {ls['t']}\nM: {ts}\nL: {note_len}\n"
        f"Q: 1/4={tempo}\n"
        f"%%pagewidth 2000cm\n%%continueall 1\n%%scale 0.85\n%%maxshrink 1\n"
        f"%%writefields T 0\n"
        f"%%staffsep 0.5cm\n%%sysstaffsep 0.3cm\n"
        f"%%leftmargin 0.5cm\n%%rightmargin 0.5cm\n"
        f"%%topspace 0\n%%musicspace 0\n"
        f"%%gchordfont Times 14\n"
        f"%%setfont-1 Times-Bold 14\n"
        f"%%score 1 {{2 3}}\n"
        f"V:1 clef=treble name=\"Mel\"\n"
        f"V:2 clef=treble staffscale=0.5\n"
        f"V:3 clef=bass staffscale=0.5\n"
        f"K: {key}\n"
    )

    mel_line = '[V:1] '
    rh_line = '[V:2] [L:1/32]'
    lh_line = '[V:3] [L:1/32]'
    cur_harp_l = 32
    npb = []
    prev_specs = None

    for bar_raw in bars:
        npb.append(len(re.findall(r'[A-Ga-g]', re.sub(r'"[^"]*"', '', bar_raw))))

        bar_mel = rewrite_chord_annotations(bar_raw, key)
        bar_dur_mel = compute_bar_duration(bar_mel)
        if bar_dur_mel <= 0:
            bar_dur_mel = 1
        mel_line += bar_mel + ' | '

        is_pickup = full_bar_mel > 0 and bar_dur_mel < full_bar_mel

        chord_list = clamp_chords(extract_chords(bar_raw))
        specs = []
        for c in chord_list:
            s = chord_to_spec(c, key)
            if s is not None:
                specs.append(s)
        if not specs:
            specs = prev_specs
        else:
            prev_specs = specs

        def harp_rest_for(harp_l_denom):
            return bar_dur_mel * mel_num * harp_l_denom // mel_den

        if is_pickup or not specs:
            rest_dur = harp_rest_for(cur_harp_l)
            rh_line += f' x{rest_dur} | '
            lh_line += f' x{rest_dur} | '
            continue

        result = build_sweep(specs)
        if result is None:
            rest_dur = harp_rest_for(cur_harp_l)
            rh_line += f' x{rest_dur} | '
            lh_line += f' x{rest_dur} | '
            continue
        rh_tokens, lh_tokens, note_count = result

        bar_32 = harp_rest_for(32)
        bar_64 = harp_rest_for(64)
        if note_count <= bar_32:
            target_l = 32
            bar_units = bar_32
        elif note_count <= bar_64:
            target_l = 64
            bar_units = bar_64
        else:
            rest_dur = harp_rest_for(cur_harp_l)
            rh_line += f' x{rest_dur} | '
            lh_line += f' x{rest_dur} | '
            continue

        prefix = ''
        if target_l != cur_harp_l:
            prefix = f'[L:1/{target_l}]'
            cur_harp_l = target_l

        pad = bar_units - note_count
        pad_str = f' x{pad}' if pad > 0 else ''
        rh_line += ' ' + prefix + fmt_run_tokens(rh_tokens) + pad_str + ' | '
        lh_line += ' ' + prefix + fmt_run_tokens(lh_tokens) + pad_str + ' | '

    mel_line = mel_line.rstrip(' | ') + ' |]'
    rh_line = rh_line.rstrip(' | ') + ' |]'
    lh_line = lh_line.rstrip(' | ') + ' |]'

    abc = header + mel_line + '\n' + rh_line + '\n' + lh_line + '\n'

    return {
        'n': ls['n'],
        't': ls['t'],
        'abc': abc,
        'key': key,
        'npb': npb,
        'tempo': tempo,
    }


def main():
    print('Loading lead sheets...')
    with open(LEAD_SHEETS) as f:
        lead_sheets = json.load(f)
    print(f'  {len(lead_sheets)} hymns')

    print('Building Tchaikovsky sweeps...')
    output = []
    failed = 0
    for ls in lead_sheets:
        try:
            r = build_hymn(ls)
            if r:
                output.append(r)
            else:
                failed += 1
        except Exception as e:
            print(f"  FAIL {ls.get('n','?')} {ls.get('t','?')}: {e}")
            failed += 1

    print(f'\nWriting {len(output)} drills to {OUTPUT} ({failed} failed)')
    with open(OUTPUT, 'w') as f:
        json.dump(output, f)
    print(f'Done. {os.path.getsize(OUTPUT) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
