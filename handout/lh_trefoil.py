"""
LH Trefoil Path Generator
Assigns LH voicings to 42 chord positions along the trefoil path,
prioritizing smooth voice leading while exhausting all 12 patterns.
"""

SCALE = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

def note_at(s):
    return SCALE[(s - 1) % 7]

def pattern_str(strings):
    gaps = [strings[i+1] - strings[i] for i in range(len(strings)-1)]
    return '-'.join(str(g) for g in gaps)

def fits_lh(strings, max_span=10):
    return (strings[-1] - strings[0] + 1) <= max_span

def build_voicing(root_idx, intervals, base_octave=1):
    """root_idx: 0=C,1=D,...,6=B. intervals: 1-indexed scale degrees."""
    root_str = root_idx + 1 + (base_octave - 1) * 7
    strings = sorted(root_str + (i - 1) for i in intervals)
    return strings

def all_voicings_for_root(root_idx):
    """Return all valid LH voicings for a given root, across octaves and chord types."""
    CHORD_TYPES = [
        ('triad',        [1, 3, 5]),
        ('7th',          [1, 3, 5, 7]),
        ('add6no5',      [1, 3, 6]),
        ('add8',         [1, 3, 5, 8]),
        ('7thno5no3',    [1, 4, 7]),
        ('9thno5no7',    [1, 3, 6, 9]),
        ('9thno5no3',    [1, 4, 6, 9]),
        ('7thno3no5',    [1, 4, 7, 10]),
        ('add6oct',      [1, 3, 6, 8]),    # 2-3-2
        ('inv1oct',      [1, 4, 6, 8]),    # 3-2-2: 1st inv triad + octave
        ('7thno3no5v2',  [1, 4, 7, 9]),    # 3-3-2: 7th inv no3no5
    ]

    voicings = []
    for oct in range(1, 5):  # try base octaves 1-4 to cover full RH range
        for chord_type, intervals in CHORD_TYPES:
            # root position
            strings = build_voicing(root_idx, intervals, base_octave=oct)
            if fits_lh(strings):
                pat = pattern_str(strings)
                if all(g in (2, 3) for g in [strings[i+1]-strings[i] for i in range(len(strings)-1)]):
                    notes = [note_at(s) for s in strings]
                    voicings.append({
                        'strings': strings,
                        'notes': notes,
                        'pattern': pat,
                        'type': chord_type,
                        'inv': 0,
                        'span': strings[-1] - strings[0] + 1,
                    })

            # inversions: rotate bottom note up an octave
            s = list(strings)
            for inv in range(1, len(intervals)):
                s[0] += 7
                s_sorted = sorted(s)
                if fits_lh(s_sorted):
                    pat = pattern_str(s_sorted)
                    gaps = [s_sorted[i+1]-s_sorted[i] for i in range(len(s_sorted)-1)]
                    if all(g in (2, 3) for g in gaps):
                        notes = [note_at(x) for x in s_sorted]
                        voicings.append({
                            'strings': s_sorted,
                            'notes': notes,
                            'pattern': pat,
                            'type': chord_type,
                            'inv': inv,
                            'span': s_sorted[-1] - s_sorted[0] + 1,
                        })
                s = s_sorted

    # deduplicate by frozenset of strings
    seen = set()
    unique = []
    for v in voicings:
        key = tuple(v['strings'])
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return unique

# Trefoil path: 6 segments, each visits 7 chords + return to C
# Chord roots as indices into SCALE (0=C,1=D,...,6=B)
ROOT_MAP = {r: i for i, r in enumerate(SCALE)}

CHORD_QUALITY = {
    'C': 'maj', 'D': 'min', 'E': 'min',
    'F': 'maj', 'G': 'maj', 'A': 'min', 'B': 'dim'
}

def chord_name(root, inv=0, chord_type='triad'):
    q = {'maj': '', 'min': 'm', 'dim': '°'}[CHORD_QUALITY[root]]
    sup = ['', '¹', '²', '³', '⁴'][inv]
    type_label = {
        'triad': '', '7th': '7', 'add6no5': 'add6no5',
        'add8': 'add8', '7thno5no3': 'no3no5add7',
        '9thno5no7': 'add9no5no7', '9thno5no3': 'add9no5no3',
        '7thno3no5': 'add7no3no5', 'add6oct': 'add6oct',
        'inv1oct': 'inv1oct', '7thno3no5v2': 'no3no5add7v2',
    }.get(chord_type, chord_type)
    return f"{root}{q}{type_label}{sup}"

TREFOIL = [
    ('CW4',  ['C','G','D','A','E','B','F','C']),
    ('CW3',  ['C','E','G','B','D','F','A','C']),
    ('CW2',  ['C','D','E','F','G','A','B','C']),
    ('CCW2', ['C','B','A','G','F','E','D','C']),
    ('CCW3', ['C','A','F','D','B','G','E','C']),
    ('CCW4', ['C','F','B','E','A','D','G','C']),
]

# All 12 valid patterns
ALL_PATTERNS = [
    '2-2', '2-3', '3-2', '3-3',
    '2-2-2', '2-2-3', '2-3-2', '3-2-2',
    '2-3-3', '3-2-3', '3-3-2', '3-3-3'
]

def score_voicing(v, prev_strings, used_patterns, all_patterns):
    """
    Score a voicing for selection:
    - Strongly prefer unused patterns
    - Penalize overused patterns proportionally
    - Prefer smooth voice leading
    - Keep hand in strings 1-12
    """
    from collections import Counter
    counts = Counter(used_patterns)
    score = 0

    pat = v['pattern']
    use_count = counts.get(pat, 0)

    if use_count == 0:
        score += 10000          # strong preference for new pattern
    else:
        score -= use_count * 500  # heavy penalty for each repeat

    # Smooth voice leading: minimize movement of lowest note
    if prev_strings:
        movement = abs(v['strings'][0] - prev_strings[0])
        score -= movement * 20

    # Keep hand anchored in reasonable range (strings 1-12)
    low = v['strings'][0]
    high = v['strings'][-1]
    if low < 1 or high > 12:
        score -= 5000
    else:
        # prefer middle of range
        center = (low + high) / 2
        score -= abs(center - 6) * 5

    # Prefer smaller spans (simpler voicings)
    score -= v['span'] * 2

    return score

def all_voicings_above(lh_top_string, root_idx, rh_pattern_exclude, max_gap=3, max_span=10):
    """
    Return all valid RH voicings for a given root,
    starting within gap 0-max_gap strings above lh_top_string,
    excluding any voicing with pattern == rh_pattern_exclude.
    No upper string limit — RH can go as high as needed.
    """
    candidates = all_voicings_for_root(root_idx)
    valid = []
    for v in candidates:
        bottom = v['strings'][0]
        gap = bottom - lh_top_string - 1
        if gap < 0 or gap > max_gap:
            continue
        if v['pattern'] == rh_pattern_exclude:
            continue
        valid.append({**v, 'gap': gap})
    return valid

def score_rh_voicing(v, prev_strings, used_patterns):
    from collections import Counter
    counts = Counter(used_patterns)
    score = 0

    pat = v['pattern']
    use_count = counts.get(pat, 0)

    if use_count == 0:
        score += 10000
    else:
        score -= use_count * 500

    # Smooth voice leading
    if prev_strings:
        movement = abs(v['strings'][0] - prev_strings[0])
        score -= movement * 20

    # Prefer gap of 1-2 (3rd or 4th between hands) for consonance
    gap = v['gap']
    if gap in (1, 2):
        score += 200
    elif gap == 0:
        score += 50   # 2nd is crunchy but ok
    elif gap == 3:
        score += 100  # 5th is open but ok

    # Prefer smaller spans
    score -= v['span'] * 2

    return score

def run():
    lh_used = []
    rh_used = []
    lh_prev = None
    rh_prev = None
    results = []

    for seg_name, roots in TREFOIL:
        seg_results = []
        for root in roots:
            root_idx = ROOT_MAP[root]

            # --- LH ---
            lh_voicings = all_voicings_for_root(root_idx)
            if not lh_voicings:
                print(f"WARNING: no LH voicings for {root}")
                continue

            lh_best = max(lh_voicings, key=lambda v: score_voicing(
                v, lh_prev, lh_used, ALL_PATTERNS))

            lh_used.append(lh_best['pattern'])
            lh_prev = lh_best['strings']
            lh_top = lh_best['strings'][-1]

            # --- RH ---
            rh_voicings = all_voicings_above(
                lh_top, root_idx,
                rh_pattern_exclude=lh_best['pattern']
            )

            if not rh_voicings:
                # fallback: allow any pattern including LH pattern
                rh_voicings = all_voicings_above(
                    lh_top, root_idx,
                    rh_pattern_exclude=None
                )

            if rh_voicings:
                rh_best = max(rh_voicings, key=lambda v: score_rh_voicing(
                    v, rh_prev, rh_used))
                rh_used.append(rh_best['pattern'])
                rh_prev = rh_best['strings']
                rh_notes = rh_best['notes']
                rh_strings = rh_best['strings']
                rh_pattern = rh_best['pattern']
                rh_gap = rh_best['gap']
            else:
                rh_notes = []
                rh_strings = []
                rh_pattern = '?'
                rh_gap = -1

            seg_results.append({
                'seg': seg_name,
                'root': root,
                'lh_notes': lh_best['notes'],
                'lh_strings': lh_best['strings'],
                'lh_pattern': lh_best['pattern'],
                'rh_notes': rh_notes,
                'rh_strings': rh_strings,
                'rh_pattern': rh_pattern,
                'gap': rh_gap,
            })

        results.extend(seg_results)

    # Print results
    print(f"{'Seg':<6} {'Root':<4} {'LH Notes':<16} {'LH Pat':<8} {'Gap':<4} {'RH Notes':<16} {'RH Pat'}")
    print('-' * 75)

    for seg_name, roots in TREFOIL:
        seg_rows = [r for r in results if r['seg'] == seg_name]
        print(f"\n--- {seg_name} ---")
        for r in seg_rows:
            lh_str = ' '.join(r['lh_notes'])
            rh_str = ' '.join(r['rh_notes'])
            asym = '' if r['lh_pattern'] != r['rh_pattern'] else ' ← SAME'
            print(f"{'':6} {r['root']:<4} {lh_str:<16} {r['lh_pattern']:<8} {r['gap']:<4} {rh_str:<16} {r['rh_pattern']}{asym}")

    # Pattern coverage
    from collections import Counter
    lh_counts = Counter(lh_used)
    rh_counts = Counter(rh_used)

    print(f"\n--- Pattern Coverage ---")
    print(f"{'Pattern':<10} {'LH':>6} {'RH':>6}")
    print('-' * 24)
    for pat in ALL_PATTERNS:
        lh_c = lh_counts.get(pat, 0)
        rh_c = rh_counts.get(pat, 0)
        lh_mark = f"{lh_c}x" if lh_c else '✗'
        rh_mark = f"{rh_c}x" if rh_c else '✗'
        print(f"  {pat:<8} {lh_mark:>6} {rh_mark:>6}")

    lh_missing = [p for p in ALL_PATTERNS if p not in lh_counts]
    rh_missing = [p for p in ALL_PATTERNS if p not in rh_counts]
    if lh_missing: print(f"\nLH MISSING: {lh_missing}")
    if rh_missing: print(f"\nRH MISSING: {rh_missing}")
    if not lh_missing and not rh_missing:
        print(f"\nBoth hands cover all 12 patterns across {len(results)} positions!")
    
    # Check asymmetry
    same = sum(1 for r in results if r['lh_pattern'] == r['rh_pattern'])
    print(f"Symmetric positions: {same}/{len(results)}")

if __name__ == '__main__':
    run()
