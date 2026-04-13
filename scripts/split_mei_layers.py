#!/usr/bin/env python3
"""Split single-layer harp MEI into moving (L1) + sustained (L2) layers.

For each accompaniment staff (2=RH, 3=LH), walks beat by beat:
- Notes unchanged from previous beat → sustained layer (stems down)
- Notes that changed → moving layer (stems up)
- Sustained notes get merged into longer held notes spanning their duration

Input:  single-layer MEI (staff 2 and 3 each have one layer)
Output: two-layer MEI (layer 1 = moving, layer 2 = sustained)
"""

import json, sys, copy
from pathlib import Path
from xml.etree import ElementTree as ET
from fractions import Fraction

ROOT = Path(__file__).resolve().parent.parent
LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
OUTPUT_DIR = ROOT / 'handout' / 'tch_ssaattbbp_out'
COMBINED_OUTPUT = ROOT / 'app' / 'tch_ssaattbbp_mei.json'

NS = 'http://www.music-encoding.org/ns/mei'
ET.register_namespace('', NS)

def ns(tag):
    return f'{{{NS}}}{tag}'

DUR_TO_Q = {'1': Fraction(4), '2': Fraction(2), '4': Fraction(1),
            '8': Fraction(1,2), '16': Fraction(1,4), '32': Fraction(1,8)}

def elem_dur(el):
    """Duration in quarter notes."""
    d = DUR_TO_Q.get(el.get('dur', '4'), Fraction(1))
    dots = int(el.get('dots', '0'))
    add = d
    for _ in range(dots):
        add = add / 2
        d += add
    return d

def pitch_key(note_el):
    return (note_el.get('pname',''), note_el.get('oct',''), note_el.get('accid.ges',''))

def pitches_of(el):
    """Set of pitch keys from a note or chord element."""
    tag = el.tag.replace(f'{{{NS}}}', '')
    if tag == 'chord':
        return set(pitch_key(n) for n in el.findall(ns('note')))
    elif tag == 'note':
        return {pitch_key(el)}
    return set()

Q_TO_DUR = [
    (Fraction(6), '1', 1),
    (Fraction(4), '1', 0),
    (Fraction(3), '2', 1),
    (Fraction(2), '2', 0),
    (Fraction(3,2), '4', 1),
    (Fraction(1), '4', 0),
    (Fraction(3,4), '8', 1),
    (Fraction(1,2), '8', 0),
    (Fraction(3,8), '16', 1),
    (Fraction(1,4), '16', 0),
    (Fraction(1,8), '32', 0),
]

def q_to_dur(q):
    for val, dur, dots in Q_TO_DUR:
        if q == val:
            return dur, dots
    # Closest match
    best = min(Q_TO_DUR, key=lambda c: abs(q - c[0]))
    return best[1], best[2]

id_counter = [0]
def next_id():
    id_counter[0] += 1
    return f'sp{id_counter[0]}'

def make_note(pk, dur_str, dots, xml_id=None):
    n = ET.Element(ns('note'))
    n.set('pname', pk[0])
    n.set('oct', pk[1])
    if pk[2]:
        n.set('accid.ges', pk[2])
    n.set('dur', dur_str)
    if dots:
        n.set('dots', str(dots))
    n.set('{http://www.w3.org/XML/1998/namespace}id', xml_id or next_id())
    return n

def make_chord(pks, dur_str, dots, xml_id=None):
    ch = ET.Element(ns('chord'))
    ch.set('dur', dur_str)
    if dots:
        ch.set('dots', str(dots))
    ch.set('{http://www.w3.org/XML/1998/namespace}id', xml_id or next_id())
    for pk in sorted(pks, key=lambda p: (int(p[1]), p[0])):
        ch.append(make_note(pk, dur_str, 0))  # notes inside chord don't need dur
    # Actually chord notes shouldn't have dur — remove it
    for n in ch.findall(ns('note')):
        if 'dur' in n.attrib:
            del n.attrib['dur']
        if 'dots' in n.attrib:
            del n.attrib['dots']
    return ch

def make_rest(dur_str, dots, visible=True):
    if not visible:
        # Use <space> instead of <rest> — Verovio renders <space> as
        # invisible duration (no glyph). Verovio ignores visible="false"
        # on <rest> elements and draws them anyway.
        r = ET.Element(ns('space'))
        r.set('dur', dur_str)
        if dots:
            r.set('dots', str(dots))
        return r
    r = ET.Element(ns('rest'))
    r.set('dur', dur_str)
    if dots:
        r.set('dots', str(dots))
    return r

def make_note_or_chord(pks, dur_str, dots):
    pks = sorted(pks, key=lambda p: (int(p[1]), p[0]))
    if len(pks) == 0:
        return make_rest(dur_str, dots)
    elif len(pks) == 1:
        return make_note(pks[0], dur_str, dots)
    else:
        return make_chord(pks, dur_str, dots)


def split_staff(staff_el, prev_sustained):
    """Split a staff's single layer into moving (L1) + sustained (L2).

    Returns the set of pitches sustained at the end of this measure.
    """
    layer = staff_el.find(ns('layer'))
    if layer is None:
        return prev_sustained

    # Extract beat events: list of (pitches_set, duration_quarters, original_element)
    events = []
    for child in list(layer):
        tag = child.tag.replace(f'{{{NS}}}', '')
        if tag in ('note', 'chord', 'rest', 'mRest'):
            pks = pitches_of(child)
            dur = elem_dur(child)
            events.append((pks, dur, child))

    if not events:
        return prev_sustained

    # Remove existing layer
    staff_el.remove(layer)

    # Walk beat by beat, building moving and sustained streams
    # Each stream entry: (pitch_set_or_None, duration)
    moving_stream = []   # (set_of_pitches | None, duration)
    sustained_stream = [] # (set_of_pitches | None, duration)

    current_sustained = set(prev_sustained)
    # Track all pitches seen so far — a pitch that appeared earlier in the
    # measure and reappears later is "returning" and should be sustained,
    # not re-articulated as moving.
    all_seen = set(prev_sustained)

    for pks, dur, orig in events:
        if not pks:
            # Rest
            moving_stream.append((None, dur))
            sustained_stream.append((None, dur))
            current_sustained = set()
            continue

        held = pks & current_sustained    # still sounding from previous beat
        returning = (pks & all_seen) - current_sustained  # was heard earlier, returning
        held = held | returning           # treat returning notes as sustained too
        moved = pks - held                # genuinely new notes

        # First event in measure with no prior context → everything is moving
        if not all_seen:
            moved = pks
            held = set()

        moving_stream.append((moved if moved else None, dur))
        sustained_stream.append((held if held else None, dur))

        current_sustained = pks
        all_seen |= pks

    # Merge consecutive sustained entries with identical pitches into longer notes
    def merge_stream(stream):
        if not stream:
            return stream
        merged = [stream[0]]
        for pks, dur in stream[1:]:
            prev_pks, prev_dur = merged[-1]
            if pks is not None and prev_pks is not None and pks == prev_pks:
                merged[-1] = (pks, prev_dur + dur)
            else:
                merged.append((pks, dur))
        return merged

    sustained_stream = merge_stream(sustained_stream)

    # Build Layer 1 (moving)
    # Hide rests in the moving layer — the sustained layer covers that time
    layer1 = ET.SubElement(staff_el, ns('layer'))
    layer1.set('n', '1')
    has_moving = False
    for pks, dur in moving_stream:
        dur_str, dots = q_to_dur(dur)
        if pks is None or len(pks) == 0:
            layer1.append(make_rest(dur_str, dots, visible=False))
        else:
            layer1.append(make_note_or_chord(pks, dur_str, dots))
            has_moving = True

    # Build Layer 2 (sustained)
    has_sustained = any(pks is not None and len(pks) > 0 for pks, dur in sustained_stream)
    if has_sustained:
        layer2 = ET.SubElement(staff_el, ns('layer'))
        layer2.set('n', '2')
        for pks, dur in sustained_stream:
            dur_str, dots = q_to_dur(dur)
            if pks is None or len(pks) == 0:
                layer2.append(make_rest(dur_str, dots, visible=False))
            else:
                layer2.append(make_note_or_chord(pks, dur_str, dots))

    return current_sustained


def process_mei(mei_text):
    root = ET.fromstring(mei_text)

    measures = list(root.iter(ns('measure')))
    prev_rh = set()
    prev_lh = set()

    for measure in measures:
        for staff in measure.findall(ns('staff')):
            sn = staff.get('n')
            if sn == '2':
                prev_rh = split_staff(staff, prev_rh)
            elif sn == '3':
                prev_lh = split_staff(staff, prev_lh)

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def main():
    raw_files = sorted(OUTPUT_DIR.glob('*_raw.mei'))
    if not raw_files:
        print('No *_raw.mei files found in', OUTPUT_DIR)
        return

    single_n = None
    for arg in sys.argv[1:]:
        if arg.isdigit():
            single_n = arg

    processed = 0
    for fp in raw_files:
        n = fp.stem.replace('_raw', '')
        if single_n and n != single_n:
            continue
        print(f'Splitting {fp.name}...', end=' ', flush=True)
        try:
            mei_text = fp.read_text()
            fixed = process_mei(mei_text)
            out_path = OUTPUT_DIR / f'{n}.mei'
            out_path.write_text(fixed)
            print(f'OK → {out_path.name} ({len(fixed)} chars)')
            processed += 1
        except Exception as e:
            import traceback
            print(f'ERROR: {e}')
            traceback.print_exc()

    print(f'\nSplit {processed} files')

    # Rebuild combined JSON
    print('Combining MEI files...')
    lead_sheets = json.loads(LEAD_SHEETS.read_text())
    ls_map = {str(ls['n']): ls for ls in lead_sheets}
    results = []
    for fp in sorted(OUTPUT_DIR.glob('*.mei')):
        if '_raw' in fp.name or '_notes' in fp.name:
            continue
        n = fp.stem
        if n not in ls_map:
            continue
        ls = ls_map[n]
        mei_text = fp.read_text()
        if len(mei_text) > 200:
            results.append({
                'n': n,
                't': ls['t'],
                'key': ls['key'],
                'tempo': 100,
                'mei': mei_text,
            })
    COMBINED_OUTPUT.write_text(json.dumps(results, ensure_ascii=False))
    print(f'Combined {len(results)} hymns → {COMBINED_OUTPUT} ({COMBINED_OUTPUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
