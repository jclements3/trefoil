#!/usr/bin/env python3
"""Build Tch-SSAATTBBP MEI algorithmically from lead sheets + handout chord table.

Produces clean MEI with:
- Staff 1: Melody (from lead sheet, treble clef)
- Staff 2: Treble accompaniment (chord tones >= C4, treble clef)
- Staff 3: Bass accompaniment (chord tones < C4, bass clef)

Each accompaniment staff has 2 layers:
  Layer 1 (stems up): notes that CHANGED from previous chord
  Layer 2 (stems down): notes SUSTAINED from previous chord

Chord voicings come from the handout chord table (14 patterns x 7 degrees)
with inversions from SATB analysis.
"""

import json, re, sys
from pathlib import Path
from fractions import Fraction

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

from generate_drill import (
    PAT_MAP, CHORD_NAMES, VALID, NOTES_PER_OCT,
    pattern_strings, string_to_abc, is_rh,
)
from build_tchaikovsky_hymnal import (
    SCALES, NOTE_SEMI, HARP_LOW, HARP_HIGH, STAFF_DIVIDE,
    chord_to_spec, chord_tone_strings,
)
from build_tchaikovsky_mei import (
    KEY_SIG, KEY_ACCID_GES, SatbAligner,
    parse_lead_sheet, parse_melody_bar, events_to_mei,
)

LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
SATB_INDEX = ROOT / 'app' / 'satb_chord_index.json'
OUTPUT = ROOT / 'app' / 'tch_ssaattbbp_mei.json'

# String 15 = C4 (middle C). Above = treble, below = bass.
MIDDLE_C_STRING = 15

# Map string number to (pname, oct) for MEI
def string_to_mei_pitch(s):
    idx = s - 1
    oct_num = 2 + idx // 7
    pname = NOTES_PER_OCT[idx % 7].lower()
    return pname, str(oct_num)


def extract_chords(bar_raw):
    return [m.group(1) for m in re.finditer(r'"\^([^"]+)"', bar_raw)]


def mei_note_str(pname, oct, dur, dots=0, xml_id=None, ges_map=None, extra=''):
    attrs = f'pname="{pname}" oct="{oct}" dur="{dur}"'
    if dots:
        attrs += f' dots="{dots}"'
    if ges_map and pname in ges_map:
        attrs += f' accid.ges="{ges_map[pname]}"'
    if xml_id:
        attrs += f' xml:id="{xml_id}"'
    if extra:
        attrs += ' ' + extra
    return f'<note {attrs}/>'


def mei_chord_str(note_strs, dur, dots=0, xml_id=None):
    attrs = f'dur="{dur}"'
    if dots:
        attrs += f' dots="{dots}"'
    if xml_id:
        attrs += f' xml:id="{xml_id}"'
    return f'<chord {attrs}>' + ''.join(note_strs) + '</chord>'


def mei_rest_str(dur, dots=0, visible=True):
    attrs = f'dur="{dur}"'
    if dots:
        attrs += f' dots="{dots}"'
    if not visible:
        attrs += ' visible="false"'
    return f'<rest {attrs}/>'


def dur_to_mei(ts_num, ts_den):
    """Return (dur_str, dots) for one full measure."""
    beats = Fraction(ts_num, ts_den) * 4  # in quarter notes
    table = [
        (Fraction(6), '1', 1),   # dotted whole
        (Fraction(4), '1', 0),   # whole
        (Fraction(3), '2', 1),   # dotted half
        (Fraction(2), '2', 0),   # half
        (Fraction(3,2), '4', 1), # dotted quarter
        (Fraction(1), '4', 0),   # quarter
    ]
    for val, dur, dots in table:
        if beats == val:
            return dur, dots
    return '2', 1  # fallback dotted half


def build_hymn_mei(ls, satb_events=None):
    key = ls['key']
    if key not in SCALES or key not in KEY_SIG:
        return None

    bars, ts, note_len, tempo = parse_lead_sheet(ls['abc'])
    aligner = SatbAligner(satb_events or [])

    ts_m = re.match(r'(\d+)/(\d+)', ts)
    if not ts_m:
        return None
    ts_num, ts_den = int(ts_m.group(1)), int(ts_m.group(2))

    mel_m = re.match(r'(\d+)/(\d+)', note_len)
    mel_num = int(mel_m.group(1)) if mel_m else 1
    mel_den = int(mel_m.group(2)) if mel_m else 8

    full_bar_mel = Fraction(ts_num * mel_den, ts_den * mel_num)
    measure_dur, measure_dots = dur_to_mei(ts_num, ts_den)

    key_sig_num, key_sig_acc = KEY_SIG[key]
    key_sig_val = f'{key_sig_num}{key_sig_acc}' if key_sig_acc else '0'
    key_sig_elem = f'<keySig sig="{key_sig_val}"/>'
    ges_map = KEY_ACCID_GES.get(key, {})

    header = f'''<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei">
<meiHead><fileDesc><titleStmt><title>{ls["t"]}</title></titleStmt>
<pubStmt/></fileDesc></meiHead>
<music><body><mdiv><score>
<scoreDef meter.count="{ts_num}" meter.unit="{ts_den}" key.sig="{key_sig_val}">
<staffGrp symbol="bracket">
<staffDef n="1" lines="5" clef.shape="G" clef.line="2">{key_sig_elem}</staffDef>
<staffGrp symbol="brace">
<staffDef n="2" lines="5" clef.shape="G" clef.line="2">{key_sig_elem}</staffDef>
<staffDef n="3" lines="5" clef.shape="F" clef.line="4">{key_sig_elem}</staffDef>
</staffGrp>
</staffGrp>
</scoreDef>
<section>
'''

    measures = []
    prev_treble = set()  # set of string numbers
    prev_bass = set()
    prev_spec = None
    id_ctr = [0]

    def next_id():
        id_ctr[0] += 1
        return f'n{id_ctr[0]}'

    for mi, bar_raw in enumerate(bars):
        # Parse melody
        mel_events = parse_melody_bar(bar_raw, key)
        mel_notes, chord_labels = events_to_mei(mel_events, mel_num, mel_den, key=key,
                                                 id_prefix=f'm{mi}n')

        bar_dur_l = sum(Fraction(ev['num'], ev['den']) for ev in mel_events)
        is_pickup = full_bar_mel > 0 and bar_dur_l < full_bar_mel

        # Get chord spec for this measure
        chords = extract_chords(bar_raw)
        spec = None
        label = None
        if chords:
            hint = aligner.hint_for(chords[0])
            spec = chord_to_spec(chords[0], key, inv_hint=hint)
        if spec is None:
            spec = prev_spec
        if spec is not None:
            prev_spec = spec
            label = spec[3]

        # Get chord tones and split at middle C
        # Limit to 4 notes per staff for readable notation
        if spec:
            tones = sorted(chord_tone_strings(spec))
            treble_all = sorted(s for s in tones if s >= MIDDLE_C_STRING)
            bass_all = sorted(s for s in tones if s < MIDDLE_C_STRING)
            # RH: lowest 4 treble tones (close to middle C, comfortable range)
            treble = set(treble_all[:4])
            # LH: lowest (pedal) + top 3 (close to middle C for readability)
            if len(bass_all) > 4:
                bass = set([bass_all[0]] + bass_all[-3:])
            else:
                bass = set(bass_all)
        else:
            treble = set()
            bass = set()

        # Determine pickup duration vs full measure duration
        if is_pickup:
            # Compute pickup duration from melody events
            pickup_quarters = bar_dur_l * Fraction(mel_num, mel_den) * 4
            # Find best MEI duration
            p_dur, p_dots = measure_dur, measure_dots
            for val, d, dt in [(Fraction(3), '2', 1), (Fraction(2), '2', 0),
                               (Fraction(3,2), '4', 1), (Fraction(1), '4', 0),
                               (Fraction(1,2), '8', 0), (Fraction(3,4), '8', 1)]:
                if pickup_quarters == val:
                    p_dur, p_dots = d, dt
                    break
            chord_dur, chord_dots = p_dur, p_dots
        else:
            chord_dur, chord_dots = measure_dur, measure_dots

        # Build accompaniment staves with moving/sustained split
        def build_acc_staff(cur_strings, prev_strings, staff_n):
            moving = sorted(cur_strings - prev_strings)
            sustained = sorted(cur_strings & prev_strings)

            # First measure or pickup: everything is moving
            if not prev_strings:
                moving = sorted(cur_strings)
                sustained = []

            layer1_parts = []  # moving
            layer2_parts = []  # sustained

            if moving:
                notes = []
                for s in moving:
                    pname, oct = string_to_mei_pitch(s)
                    notes.append(mei_note_str(pname, oct, chord_dur, chord_dots,
                                              xml_id=next_id(), ges_map=ges_map))
                if len(notes) == 1:
                    layer1_parts.append(notes[0])
                else:
                    layer1_parts.append(mei_chord_str(notes, chord_dur, chord_dots,
                                                       xml_id=next_id()))
            else:
                layer1_parts.append(mei_rest_str(chord_dur, chord_dots))

            if sustained:
                notes = []
                for s in sustained:
                    pname, oct = string_to_mei_pitch(s)
                    notes.append(mei_note_str(pname, oct, chord_dur, chord_dots,
                                              xml_id=next_id(), ges_map=ges_map))
                if len(notes) == 1:
                    layer2_parts.append(notes[0])
                else:
                    layer2_parts.append(mei_chord_str(notes, chord_dur, chord_dots,
                                                       xml_id=next_id()))
            else:
                layer2_parts.append(mei_rest_str(chord_dur, chord_dots, visible=False))

            # Build staff XML
            layer1 = '<layer n="1">' + ''.join(layer1_parts) + '</layer>'
            has_sustained = bool(sustained)
            if has_sustained:
                layer2 = '<layer n="2">' + ''.join(layer2_parts) + '</layer>'
                return f'<staff n="{staff_n}">{layer1}{layer2}</staff>'
            else:
                return f'<staff n="{staff_n}">{layer1}</staff>'

        staff1 = '<staff n="1"><layer n="1">' + ''.join(mel_notes) + '</layer></staff>'
        staff2 = build_acc_staff(treble, prev_treble, 2)
        staff3 = build_acc_staff(bass, prev_bass, 3)

        # Chord label
        harm = ''
        if label:
            harm = f'<harm staff="1" tstamp="1">{label}</harm>'

        measures.append(f'<measure n="{mi+1}">{staff1}{staff2}{staff3}{harm}</measure>')

        prev_treble = treble
        prev_bass = bass

    footer = '</section></score></mdiv></body></music></mei>'
    mei = header + '\n'.join(measures) + '\n' + footer
    return {
        'n': ls['n'],
        't': ls['t'],
        'key': key,
        'tempo': tempo,
        'mei': mei,
    }


def main():
    print('Loading lead sheets...')
    lead_sheets = json.loads(LEAD_SHEETS.read_text())
    print(f'  {len(lead_sheets)} hymns')

    satb_index = {}
    if SATB_INDEX.exists():
        print('Loading SATB chord index...')
        satb_index = json.loads(SATB_INDEX.read_text())
        print(f'  {len(satb_index)} hymns with SATB analysis')

    results = []
    failed = 0
    for ls in lead_sheets:
        n = ls['n']
        satb_events = satb_index.get(str(n))
        hymn = build_hymn_mei(ls, satb_events)
        if hymn:
            results.append(hymn)
        else:
            failed += 1

    print(f'\nWriting {len(results)} hymns to {OUTPUT} ({failed} failed)')
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False))
    print(f'Done. {OUTPUT.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
