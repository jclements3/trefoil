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
from generate_drill import PAT_MAP, CHORD_NAMES, pattern_strings, string_to_abc, NOTES_PER_OCT
from build_tchaikovsky_mei import KEY_ACCID_GES, abc_to_pitch

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


# 8va threshold: C6 (string 29) and above get an "8va" bracket so readers
# don't have to count 4+ ledger lines above the treble staff.
OCTAVE_UP_THRESHOLD = 29  # C6


def build_cascade_measure(cascade, measure_id, key='Eb'):
    """Build MEI for one cascade: a measure with hidden-bracket tuplet across both staves.

    Returns XML string for <section> containing <measure>.
    """
    # Collect all sweep strings. Each arpeggio's first note carries the
    # authoritative chord label from CHORD_NAMES[(pattern, starting_deg)].
    events = []  # list of {'string': s, 'label': str or None}
    for row in cascade['rows']:
        start = pos_to_string(row['pos'])
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

    # Figure out which treble events sit in the 8va zone (sounding C6+).
    # Notes inside a contiguous 8va run are written one octave lower so
    # they fit on the staff; a <octave> element over startid..endid draws
    # the "8" bracket.
    octave_up_runs = []  # list of (start_idx, end_idx, startid, endid)
    current = None
    for idx, ev in enumerate(events):
        if ev['string'] >= OCTAVE_UP_THRESHOLD:
            if current is None:
                current = [idx, idx]
            else:
                current[1] = idx
        else:
            if current is not None:
                octave_up_runs.append(tuple(current))
                current = None
    if current is not None:
        octave_up_runs.append(tuple(current))
    in_octave_up = set()
    for a, b in octave_up_runs:
        for k in range(a, b + 1):
            in_octave_up.add(k)

    # Build parallel streams: each sweep note goes on its pitch-appropriate
    # staff; the opposite staff gets <space/>. Each event consumes one
    # "slot" (one nominal eighth before tuplet scaling). Each note gets an
    # xml:id so <octave> elements can reference its startid/endid.
    note_ids = {}  # event_idx -> xml:id string
    for idx, ev in enumerate(events):
        s = ev['string']
        abc = string_to_abc(s)
        pp = abc_to_pitch(abc)
        if pp is None:
            continue
        pname, octnum = pp
        # Shift written octave down for notes inside an 8va bracket.
        if idx in in_octave_up:
            written_oct = octnum - 1
        else:
            written_oct = octnum
        ges_attr = f' accid.ges="{ges_map[pname]}"' if pname in ges_map else ''
        hidden = f'<space dur="{note_dur}"/>'
        on_treble = is_treble_string(s)
        nid = f'c{measure_id}n{idx}'
        note_ids[idx] = nid
        id_attr = f' xml:id="{nid}"'
        if on_treble:
            note = (f'<note{id_attr} pname="{pname}" oct="{written_oct}" dur="{note_dur}"'
                    f'{ges_attr} stem.dir="down"/>')
            treble_parts.append((True, note, s))
            bass_parts.append((False, hidden, s))
        else:
            note = (f'<note{id_attr} pname="{pname}" oct="{written_oct}" dur="{note_dur}"'
                    f'{ges_attr} stem.dir="up"/>')
            treble_parts.append((False, hidden, s))
            bass_parts.append((True, note, s))

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

    n = len(events)
    numbase = note_dur * 4 // 4  # 4/4 time: 8 eighths per bar
    # Tuplet: N notes in the time of numbase eighths
    tuplet_open = (f'<tuplet num="{n}" numbase="{numbase}" '
                   f'num.visible="false" bracket.visible="false">')
    tuplet_close = '</tuplet>'

    treble_layer = f'<staff n="1"><layer n="1">{tuplet_open}{treble_inner}{tuplet_close}</layer></staff>'
    bass_layer = f'<staff n="2"><layer n="1">{tuplet_open}{bass_inner}{tuplet_close}</layer></staff>'

    # Chord labels from CHORD_NAMES (circled-digit official names).
    harm_xml = ''
    for idx, ev in enumerate(events):
        if ev['label']:
            tstamp = 1 + idx * 4.0 / n
            harm_xml += (f'<harm tstamp="{tstamp:.4f}" staff="1" place="above">'
                         f'{ev["label"]}</harm>')

    # 8va brackets (octave up) over contiguous runs of high treble notes.
    octave_xml = ''
    for a, b in octave_up_runs:
        if a in note_ids and b in note_ids:
            octave_xml += (f'<octave staff="1" dis="8" dis.place="above" '
                           f'startid="#{note_ids[a]}" endid="#{note_ids[b]}"/>')

    # Rehearsal mark with cascade title above the measure
    title_txt = cascade['title']
    subtitle_txt = cascade['subtitle']
    tempo_xml = (f'<tempo tstamp="1" staff="1" place="above">'
                 f'<rend fontweight="bold" fontsize="large">{title_txt}</rend>'
                 f' <rend fontstyle="italic" fontsize="small">({subtitle_txt})</rend>'
                 f'</tempo>')

    measure = (f'<measure n="{measure_id}" right="end">'
               f'{treble_layer}{bass_layer}{tempo_xml}{harm_xml}{octave_xml}</measure>')
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
