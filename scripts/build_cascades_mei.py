#!/usr/bin/env python3
"""Build cascades as MEI + Verovio sheet music.

Reuses the Tch cadenza's hidden-bracket tuplet strategy: each cascade's
full sweep (all rows concatenated, descending rows reversed) is wrapped
in <tuplet num.visible="false" bracket.visible="false"> so the variable
note count fits exactly one 4/4 measure. Grand staff (treble + bass);
each note on its pitch-appropriate staff with <space/> on the opposite.

Output: handout/cascades.mei (single document, one <section> per cascade
separated by system breaks). Render with verovio.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_drill import PAT_MAP, CHORD_NAMES, DEG_TO_FIRST_STRING, pattern_strings, string_to_abc, NOTES_PER_OCT
from build_tchaikovsky_mei import KEY_ACCID_GES, abc_to_pitch

HARP_MAX_STRING = 33  # 33-string lever harp: C2 (1) to G6 (33)


def starts_for_deg(deg):
    """All valid starting string numbers on the harp for a given scale degree."""
    off = DEG_TO_FIRST_STRING[deg]
    return [off + 7 * k for k in range(5) if off + 7 * k <= HARP_MAX_STRING]


def plan_cascade(rows):
    """Compute start positions so the cascade rises through the 'up' rows
       and falls through the 'dn' rows. Preference is a monotonic sweep
       (each arp continues one string past the previous), but if no chord
       tone fits that rule we fall back to the nearest valid start so
       every row gets played. The table's written positions are ignored --
       the cascade is defined by its (chord, pattern, direction) sequence."""
    plan = []
    prev_end = None  # last-played string of previous arpeggio (dn: lowest; up: highest)
    for r in rows:
        pat = PAT_MAP[r['pat']]
        span = sum(p - 1 for p in pat)
        all_starts = [s for s in starts_for_deg(r['deg']) if s + span <= HARP_MAX_STRING]
        if not all_starts:
            plan.append(None)
            continue
        if r['dir'] == 'up':
            if prev_end is None:
                start = min(all_starts)
            else:
                above = [s for s in all_starts if s >= prev_end + 1]
                start = min(above) if above else min(all_starts, key=lambda s: abs(s - (prev_end + 1)))
            prev_end = start + span
        else:  # dn: first played = start + span (top of pattern)
            target_top = (prev_end - 1) if prev_end is not None else HARP_MAX_STRING
            below = [s for s in all_starts if s + span <= target_top]
            start = max(below) if below else min(all_starts, key=lambda s: abs((s + span) - target_top))
            prev_end = start  # lowest played note of this arpeggio
        plan.append(start)
    return plan

NOTE_OFFSET = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}


def pos_to_string(pos):
    note = pos[0]
    octave = int(pos[1:])
    return (octave - 2) * 7 + NOTE_OFFSET[note] + 1


def parse_cascades(tex_path):
    with open(tex_path) as f:
        text = f.read()
    cascades = []
    for m in re.finditer(r'\\cascadetable\{(\w+)\}\{([^}]+)\}\{([^}]+)\}\{', text):
        cat, title, subtitle = m.group(1), m.group(2), m.group(3)
        start = m.end()
        depth = 1
        i = start
        while depth > 0 and i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        body = text[start:i - 1]
        rows = []
        # Chord labels may contain inner {braces} (e.g. ^{\circ1}), so the
        # final group needs a brace-balanced match.
        chord_group = r'((?:[^{}]|\{[^{}]*\})*)'
        for rm in re.finditer(
                r'\\row(up|dn)\{(LH|RH)\}\{(\w+)\}\{\\circled\{(\d)\}(\d+)\}\{' + chord_group + r'\}',
                body):
            direction, hand, pos, deg, pat, chord = rm.groups()
            rows.append({'dir': direction, 'hand': hand, 'pos': pos,
                         'deg': int(deg), 'pat': pat, 'chord': chord})
        cascades.append({'cat': cat, 'title': title, 'subtitle': subtitle, 'rows': rows})
    return cascades


def chord_label_to_text(latex):
    t = latex
    t = t.replace('$^{\\circ1}$', '°¹').replace('$^{\\circ2}$', '°²').replace('$^{\\circ3}$', '°³')
    t = t.replace('$\\varnothing7^1$', 'ø7¹').replace('$\\varnothing7^2$', 'ø7²').replace('$\\varnothing7^3$', 'ø7³')
    t = t.replace('$\\varnothing7$', 'ø7').replace('\\varnothing7', 'ø7')
    t = t.replace('$\\varnothing$', 'ø').replace('\\varnothing', 'ø')
    t = t.replace('$\\Delta^1$', 'Δ¹').replace('$\\Delta^2$', 'Δ²').replace('$\\Delta^3$', 'Δ³')
    t = t.replace('$\\Delta$', 'Δ').replace('\\Delta', 'Δ')
    t = t.replace('$^\\circ$', '°').replace('^\\circ', '°')
    t = re.sub(r'\$\^(\d)\$', lambda m: '¹²³'[int(m.group(1)) - 1], t)
    t = re.sub(r'\^(\d)', lambda m: '¹²³'[int(m.group(1)) - 1], t)
    t = t.replace('$+$', '+').replace('$', '')
    return t


def is_treble_string(s):
    """String 15 (C4) and above sit on treble staff."""
    return s >= 15


def build_cascade_measure(cascade, measure_id, key='Eb'):
    """Build MEI for one cascade: a measure with hidden-bracket tuplet across both staves.

    Returns XML string for <section> containing <measure>.
    """
    # Starting positions are computed so the cascade rises monotonically
    # through the 'up' rows and falls monotonically through the 'dn' rows.
    # The positions written in cascades.tex are ignored -- the table's
    # real content is the (chord, pattern, direction, hand) sequence.
    plan = plan_cascade(cascade['rows'])

    events = []  # list of {'string': s, 'label': str or None}
    for row, start in zip(cascade['rows'], plan):
        if start is None:
            continue  # no valid position fits -- drop this row quietly
        pat = PAT_MAP[row['pat']]
        strs = pattern_strings(start, pat)
        if row['dir'] == 'dn':
            strs = list(reversed(strs))
        label = CHORD_NAMES.get((row['pat'], row['deg']), '?')
        for i, s in enumerate(strs):
            events.append({'string': s, 'label': label if i == 0 else None})

    note_dur = 8  # eighth note nominal duration
    ges_map = KEY_ACCID_GES.get(key, {})

    treble_parts = []  # event XML snippets for staff 1
    bass_parts = []    # event XML snippets for staff 2

    # Insert EXTRA_GAP_SLOTS hidden slots on BOTH staves at each middle-C
    # crossing so the two beam groups don't visually collide after the
    # tuplet compresses the layer to one bar. (Same trick as the Tch
    # cadenza; without it the last bass note crashes into the first
    # treble note and vice versa.)
    EXTRA_GAP_SLOTS = 12
    hidden = f'<space dur="{note_dur}"/>'
    prev_on_treble = None
    event_slot = []  # layer slot position for each event (after gap insertion)
    for idx, ev in enumerate(events):
        s = ev['string']
        abc = string_to_abc(s)
        pp = abc_to_pitch(abc)
        if pp is None:
            event_slot.append(None)
            continue
        pname, octnum = pp
        ges_attr = f' accid.ges="{ges_map[pname]}"' if pname in ges_map else ''
        on_treble = is_treble_string(s)
        # Open a gap when the cascade crosses middle C (staff change).
        if prev_on_treble is not None and prev_on_treble != on_treble:
            for _ in range(EXTRA_GAP_SLOTS):
                treble_parts.append((False, hidden, -1))
                bass_parts.append((False, hidden, -1))
        event_slot.append(len(treble_parts))
        if on_treble:
            note = (f'<note pname="{pname}" oct="{octnum}" dur="{note_dur}"'
                    f'{ges_attr} stem.dir="down"/>')
            treble_parts.append((True, note, s))
            bass_parts.append((False, hidden, s))
        else:
            note = (f'<note pname="{pname}" oct="{octnum}" dur="{note_dur}"'
                    f'{ges_attr} stem.dir="up"/>')
            treble_parts.append((False, hidden, s))
            bass_parts.append((True, note, s))
        prev_on_treble = on_treble

    # Wrap consecutive notes in <beam>, breaking at direction changes and rests.
    def emit(parts):
        out = []
        run = []
        run_strs = []

        def flush():
            if not run:
                return
            if len(run) > 1:
                out.append('<beam>' + ''.join(run) + '</beam>')
            else:
                out.append(run[0])
            run.clear()
            run_strs.clear()

        for is_note, xml, s in parts:
            if not is_note:
                flush()
                out.append(xml)
                continue
            if len(run_strs) >= 2:
                prev_dir = run_strs[-1] - run_strs[-2]
                new_dir = s - run_strs[-1]
                if prev_dir != 0 and new_dir != 0 and (prev_dir > 0) != (new_dir > 0):
                    flush()
            run.append(xml)
            run_strs.append(s)
        flush()
        return ''.join(out)

    treble_inner = emit(treble_parts)
    bass_inner = emit(bass_parts)

    n = len(treble_parts)  # includes gap slots so the tuplet ratio is right
    numbase = note_dur * 4 // 4  # 4/4 time: 8 eighths per bar
    tuplet_open = (f'<tuplet num="{n}" numbase="{numbase}" '
                   f'num.visible="false" bracket.visible="false">')
    tuplet_close = '</tuplet>'

    treble_layer = f'<staff n="1"><layer n="1">{tuplet_open}{treble_inner}{tuplet_close}</layer></staff>'
    bass_layer = f'<staff n="2"><layer n="1">{tuplet_open}{bass_inner}{tuplet_close}</layer></staff>'

    # Chord labels from CHORD_NAMES (circled-digit official names).
    # Anchor by layer-slot position (post gap insertion), not event index.
    harm_xml = ''
    for idx, ev in enumerate(events):
        if ev['label'] and event_slot[idx] is not None:
            tstamp = 1 + event_slot[idx] * 4.0 / n
            harm_xml += (f'<harm tstamp="{tstamp:.4f}" staff="1" place="above">'
                         f'{ev["label"]}</harm>')

    # Rehearsal mark with cascade title above the measure
    title_txt = cascade['title']
    subtitle_txt = cascade['subtitle']
    tempo_xml = (f'<tempo tstamp="1" staff="1" place="above">'
                 f'<rend fontweight="bold" fontsize="large">{title_txt}</rend>'
                 f' <rend fontstyle="italic" fontsize="small">({subtitle_txt})</rend>'
                 f'</tempo>')

    measure = (f'<measure n="{measure_id}" right="end">'
               f'{treble_layer}{bass_layer}{tempo_xml}{harm_xml}</measure>')
    return measure


def build_cascades_mei(cascades, key='Eb'):
    key_sig_map = {'C': '0', 'G': '1s', 'D': '2s', 'A': '3s', 'E': '4s',
                   'F': '1f', 'Bb': '2f', 'Eb': '3f'}
    key_sig_val = key_sig_map[key]

    # Build one measure per cascade, with system breaks between.
    measures = []
    for i, c in enumerate(cascades, 1):
        if i > 1:
            measures.append(f'<sb/>')  # system break before each new cascade
        measures.append(build_cascade_measure(c, i, key=key))

    mei = f'''<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei">
<meiHead><fileDesc><titleStmt><title>Cascade Reference Sheet</title></titleStmt>
<pubStmt/></fileDesc></meiHead>
<music><body><mdiv><score>
<scoreDef meter.count="4" meter.unit="4" key.sig="{key_sig_val}">
<staffGrp symbol="brace">
<staffDef n="1" lines="5" clef.shape="G" clef.line="2"><keySig sig="{key_sig_val}"/></staffDef>
<staffDef n="2" lines="5" clef.shape="F" clef.line="4"><keySig sig="{key_sig_val}"/></staffDef>
</staffGrp>
</scoreDef>
<section>
{"".join(measures)}
</section>
</score></mdiv></body></music>
</mei>
'''
    return mei


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    tex_path = os.path.join(here, '..', 'handout', 'cascades.tex')
    out_path = os.path.join(here, '..', 'handout', 'cascades.mei')
    cascades = parse_cascades(tex_path)
    mei = build_cascades_mei(cascades)
    with open(out_path, 'w') as f:
        f.write(mei)
    print(f"Wrote {len(cascades)} cascades to {out_path}")


if __name__ == '__main__':
    main()
