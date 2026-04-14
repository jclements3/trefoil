#!/usr/bin/env python3
"""Parse handout/cascades.tex and render each cascade as arpeggiated
   practice sheet music (grand staff, Eb major). Writes cascades_sheet.abc."""
import re
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_drill import PAT_MAP, pattern_strings, string_to_abc

NOTE_OFFSET = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}


def pos_to_string(pos):
    """'E2', 'C4', etc. -> 1-indexed harp string number (C2 = 1)."""
    note = pos[0]
    octave = int(pos[1:])
    return (octave - 2) * 7 + NOTE_OFFSET[note] + 1


def parse_cascades(tex_path):
    with open(tex_path) as f:
        text = f.read()
    cascades = []
    for m in re.finditer(r'\\cascadetable\{(\w+)\}\{([^}]+)\}\{([^}]+)\}\{', text):
        cat, title, subtitle = m.group(1), m.group(2), m.group(3)
        # find matching closing brace for the 4th arg (rows body)
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
        for rm in re.finditer(
                r'\\row(up|dn)\{(LH|RH)\}\{(\w+)\}\{\\circled\{(\d)\}(\d+)\}\{([^}]+)\}',
                body):
            direction, hand, pos, deg, pat, chord = rm.groups()
            rows.append({
                'dir': direction, 'hand': hand, 'pos': pos,
                'deg': int(deg), 'pat': pat, 'chord': chord,
            })
        cascades.append({'cat': cat, 'title': title, 'subtitle': subtitle, 'rows': rows})
    return cascades


def chord_label_to_text(latex):
    """Convert cascade's LaTeX chord label to plain-text annotation."""
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


def note_octave(abc_note):
    """Return scientific octave of an ABC note like 'C,,', 'c', 'C', 'e\\''."""
    # Uppercase base = octave 4 (C..B). Each ',' drops an octave. Lowercase = oct 5. Each "'" raises.
    m = re.match(r"([A-Ga-g])([',]*)", abc_note)
    if not m:
        return 4
    name, marks = m.groups()
    base = 4 if name.isupper() else 5
    for ch in marks:
        if ch == ',':
            base -= 1
        elif ch == "'":
            base += 1
    return base


def is_treble(abc_note):
    """True if note sits on treble staff (octave 4+)."""
    return note_octave(abc_note) >= 4


def render_cascade(cascade, x_num):
    """Render one cascade as a single measure in 4/4, wrapping all note
       slots in a hidden-bracket tuplet (like the Tch cadenza)."""
    lines = [
        f"X:{x_num}",
        f"T:{cascade['title']}",
        f"T:{cascade['subtitle']}",
        "M:4/4",
        "L:1/8",
        "%%tuplets 0 0 0 0",
        "K:Eb",
        "%%score {1 | 2}",
        "V:1 clef=treble",
        "V:2 clef=bass",
    ]
    v1_slots, v2_slots = [], []
    for row in cascade['rows']:
        start = pos_to_string(row['pos'])
        pat = PAT_MAP[row['pat']]
        strings = pattern_strings(start, pat)
        notes = [string_to_abc(s) for s in strings]
        if row['dir'] == 'dn':
            notes = list(reversed(notes))
        hand_letter = row['hand'][0]
        chord_txt = chord_label_to_text(row['chord'])
        label = f'"^{hand_letter} {chord_txt}"'
        # split this row's notes between staves beat-by-beat
        row_v1, row_v2 = [], []
        for n in notes:
            if is_treble(n):
                row_v1.append(n)
                row_v2.append('z')
            else:
                row_v1.append('z')
                row_v2.append(n)
        # label goes on the first actual note on the staff that starts the arpeggio
        target = row_v1 if is_treble(notes[0]) else row_v2
        for i, tok in enumerate(target):
            if tok != 'z':
                target[i] = label + tok
                break
        v1_slots.extend(row_v1)
        v2_slots.extend(row_v2)
    n = len(v1_slots)
    # one measure of 4/4 = 8 eighths at L:1/8. Wrap all N slots in a tuplet
    # (N:8:N) so they squeeze into the measure width -- same idea as the Tch
    # cadenza's hidden-bracket tuplet.
    tuplet_prefix = f"({n}:8:{n}"
    lines.append(f"[V:1] {tuplet_prefix}{''.join(v1_slots)} |]")
    lines.append(f"[V:2] {tuplet_prefix}{''.join(v2_slots)} |]")
    return '\n'.join(lines)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    tex_path = os.path.join(here, '..', 'handout', 'cascades.tex')
    out_path = os.path.join(here, '..', 'handout', 'cascades_sheet.abc')
    cascades = parse_cascades(tex_path)
    header = [
        "%%pagewidth 21.59cm",
        "%%pageheight 27.94cm",
        "%%topmargin 1.0cm",
        "%%botmargin 1.0cm",
        "%%leftmargin 1.2cm",
        "%%rightmargin 1.2cm",
        "%%scale 0.70",
        "%%staffsep 40",
        "%%sysstaffsep 12",
        "%%barnumbers 0",
        "%%annotationfont DejaVu Sans 10",
        "%%titlefont DejaVu Sans 14 bold",
        "%%subtitlefont DejaVu Sans 10 italic",
        "%%tuplets 0 0 0 0",  # hide tuplet brackets and numbers
        "",
    ]
    blocks = [render_cascade(c, i) for i, c in enumerate(cascades, 1)]
    with open(out_path, 'w') as f:
        f.write('\n'.join(header))
        f.write('\n\n'.join(blocks) + '\n')
    print(f"Wrote {len(cascades)} cascades to {out_path}")


if __name__ == '__main__':
    main()
