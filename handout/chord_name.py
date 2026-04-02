"""
Terse chord naming for harp voicings.
Format: root + quality + inversion¹²³ + stack-level + removals(-n) + additions(+n) + octave(+8)

Symbols:
  uppercase   = major triad (C F G)
  m           = minor triad (Dm Em Am)
  °           = diminished (B°)
  Δ           = major 7th
  7           = dominant or minor 7th
  ø7          = half diminished
  s           = sus4 (4 replaces 3)
  s2          = sus2 (2 replaces 3)
  ¹ ² ³       = inversion superscript
  -n          = remove scale degree n from stack
  +n          = add scale degree n (not part of stack)
  +8          = octave doubling
"""

SCALE = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
SUP = ['', '¹', '²', '³', '⁴', '⁵', '⁶']

CHORD_QUALITY = {
    'C': 'maj', 'D': 'min', 'E': 'min',
    'F': 'maj', 'G': 'dom', 'A': 'min', 'B': 'dim'
}

def degrees_from_root(notes, root):
    ri = SCALE.index(root)
    return [(SCALE.index(n) - ri) % 7 + 1 for n in notes]

def name_voicing(notes, root):
    quality = CHORD_QUALITY[root]

    # Unique notes preserving order
    seen = set(); unique = []
    for n in notes:
        if n not in seen: seen.add(n); unique.append(n)

    has_oct = len(notes) > len(unique)

    degs = degrees_from_root(unique, root)
    deg_set = set(degs)
    has = lambda d: d in deg_set

    bass = unique[0]
    ri = SCALE.index(root)
    bass_deg = (SCALE.index(bass) - ri) % 7 + 1

    # Determine which degrees appear above the octave (i.e. as 9th, 11th, 13th)
    # A degree is "upper" if it appears in the voicing after the root reappears,
    # or if the root doesn't reappear, after any note whose degree < previous note's degree
    # (i.e. we wrapped around the octave)
    upper_degs = set()
    wrapped = False
    prev_deg = 0
    for d in degs:
        if d < prev_deg:
            wrapped = True
        if wrapped:
            upper_degs.add(d)
        prev_deg = d

    def display_deg(d):
        """Return display degree: 2->9, 4->11, 6->13 if in upper register."""
        if d in upper_degs:
            if d == 2: return 9
            if d == 4: return 11
            if d == 6: return 13
        return d

    # Base quality string
    if quality == 'maj':   q = root
    elif quality == 'min': q = root + 'm'
    elif quality == 'dom': q = root
    elif quality == 'dim': q = root + '°'

    # --- Build candidate stacks ---
    candidate_stacks = []
    candidate_stacks.append(('triad', [1, 3, 5]))
    if has(7):
        candidate_stacks.append(('7th', [1, 3, 5, 7]))
        if has(2):
            candidate_stacks.append(('9th', [1, 3, 5, 7, 2]))
            if has(4):
                candidate_stacks.append(('11th', [1, 3, 5, 7, 2, 4]))
                if has(6):
                    candidate_stacks.append(('13th', [1, 3, 5, 7, 2, 4, 6]))

    sus_stacks = []
    if has(4):
        sus_stacks.append(('sus4', [1, 4, 5]))
        if has(7):
            sus_stacks.append(('7sus4', [1, 4, 5, 7]))
            if has(2):
                sus_stacks.append(('9sus4', [1, 4, 5, 7, 2]))
    if has(2) and not has(4):
        sus_stacks.append(('sus2', [1, 2, 5]))
        if has(7):
            sus_stacks.append(('7sus2', [1, 2, 5, 7]))

    all_candidates = []
    for sname, sdegs in candidate_stacks + sus_stacks:
        removals = [d for d in sdegs if d not in deg_set]
        additions = [d for d in deg_set if d not in set(sdegs)]
        score = len(removals) + len(additions)
        all_candidates.append((score, sname, sdegs, removals, additions))

    all_candidates.sort(key=lambda x: x[0])
    best_score = all_candidates[0][0]
    tied = [c for c in all_candidates if c[0] == best_score]

    def build_base(sname, q, root, quality):
        if sname == 'triad':    return q
        elif sname == '7th':
            if quality == 'maj':   return root + 'Δ'
            elif quality == 'dim': return root + 'ø7'
            else:                  return q + '7'
        elif sname == '9th':
            if quality == 'maj':   return root + 'Δ9'
            elif quality == 'dim': return root + 'ø9'
            else:                  return q + '9'
        elif sname == '11th':
            if quality == 'maj':   return root + 'Δ11'
            else:                  return q + '11'
        elif sname == '13th':
            if quality == 'maj':   return root + 'Δ13'
            else:                  return q + '13'
        elif sname == 'sus4':   return q + 's'
        elif sname == '7sus4':
            if quality == 'maj':   return root + 'Δs'
            elif quality == 'dim': return root + 'ø7s'
            else:                  return q + '7s'
        elif sname == '9sus4':
            if quality == 'maj':   return root + 'Δ9s'
            else:                  return q + '9s'
        elif sname == 'sus2':   return q + 's2'
        elif sname == '7sus2':
            if quality == 'maj':   return root + 'Δs2'
            else:                  return q + '7s2'
        return q

    best_len = 999
    best_stack_name = tied[0][1]; best_stack = tied[0][2]
    for score, sname, sdegs, removals, additions in tied:
        base = build_base(sname, q, root, quality)
        stack_set_t = set(sdegs)
        inv_t = sdegs.index(bass_deg) if bass_deg in sdegs else 0
        rem_t = sorted([d for d in sdegs if d not in deg_set])
        add_t = sorted([display_deg(d) for d in deg_set if d not in stack_set_t])
        name_t = base
        if inv_t > 0: name_t += SUP[inv_t]
        for r in rem_t: name_t += f'-{r}'
        for a in add_t: name_t += f'+{a}'
        if has_oct: name_t += '+8'
        if len(name_t) < best_len:
            best_len = len(name_t)
            best_stack_name = sname; best_stack = sdegs

    stack = best_stack; stack_name = best_stack_name; stack_set = set(stack)
    removals = sorted([d for d in stack if d not in deg_set])
    additions = sorted([display_deg(d) for d in deg_set if d not in stack_set])
    base = build_base(stack_name, q, root, quality)

    inv = stack.index(bass_deg) if bass_deg in stack else 0

    name = base
    if inv > 0:         name += SUP[inv]
    for r in removals:  name += f'-{r}'
    for a in additions: name += f'+{a}'
    if has_oct:         name += '+8'

    return name


if __name__ == '__main__':
    tests = [
        # Triads
        ('C', ['C','E','G'],               'C'),
        ('C', ['E','G','C'],               'C¹'),
        ('C', ['G','C','E'],               'C²'),
        ('D', ['D','F','A'],               'Dm'),
        ('D', ['F','A','D'],               'Dm¹'),
        ('D', ['A','D','F'],               'Dm²'),
        ('B', ['B','D','F'],               'B°'),
        # 7th chords
        ('C', ['C','E','G','B'],           'CΔ'),
        ('D', ['D','F','A','C'],           'Dm7'),
        ('G', ['G','B','D','F'],           'G7'),
        ('B', ['B','D','F','A'],           'Bø7'),
        # Octave doubling
        ('C', ['C','E','G','C'],           'C+8'),
        ('C', ['E','G','C','E'],           'C¹+8'),
        ('C', ['G','C','E','G'],           'C²+8'),
        ('F', ['C','F','A','C'],           'F²+8'),
        ('G', ['D','G','B','D'],           'G²+8'),
        # Drop voicings
        ('C', ['C','E','A'],               'C-5+6'),
        ('C', ['C','F','B','E'],           'CΔ-5+4'),   # 7th stack shortest: CΔ-5+4=6 vs CΔs-5+3=7
        ('C', ['C','F','B'],               'CΔs-5'),
        ('C', ['C','E','A','D'],           'C-5+6+9'),
        # Extensions
        ('C', ['C','E','G','B','D'],       'CΔ9'),
        ('C', ['C','E','B','D'],           'CΔ9-5'),
        ('C', ['C','G','B','D'],           'CΔs2'),     # sus2 stack shortest: CΔs2=4 vs CΔ9-3=5
        ('C', ['C','F','B','E','A','D'],   'CΔ13-5'),
        # Sus chords
        ('C', ['C','F','G'],               'Cs'),
        ('C', ['C','D','G'],               'Cs2'),
        ('G', ['G','C','D','F'],           'G7s'),
        ('C', ['C','F','G','B'],           'CΔs'),
        ('C', ['C','D','G','B'],           'CΔs2'),
    ]

    print(f"{'Notes':<30} {'Expected':<22} {'Got':<22} {'Match'}")
    print('-' * 82)
    ok = 0
    for root, notes, expected in tests:
        got = name_voicing(notes, root)
        match = '✓' if got == expected else '✗'
        if got == expected: ok += 1
        print(f"{' '.join(notes):<30} {expected:<22} {got:<22} {match}")
    print(f"\n{ok}/{len(tests)} passing")
