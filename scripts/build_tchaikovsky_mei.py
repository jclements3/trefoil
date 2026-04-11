#!/usr/bin/env python3
"""Build Tchaikovsky-style harp drills as MEI for Verovio rendering.

Same chord-tone sweep algorithm as build_tchaikovsky_hymnal.py (ABC),
but emits MEI directly. The harp cadenza is one <graceGrp> per bar
placed on staff 2 (treble), with individual bass-register notes
marked with @staff="3" so Verovio renders them on the bass staff.
This produces one visual cadenza sweep crossing both staves of the
grand staff, in proper small-note cadenza style.

Output: app/tchaikovsky_mei.json — list of {n, t, key, tempo, mei, npb}
"""

import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_drill import (
    PAT_MAP, CHORD_NAMES, VALID, NOTES_PER_OCT,
    pattern_strings, string_to_abc, is_rh,
)
from build_tchaikovsky_hymnal import (
    SCALES, NOTE_SEMI, SWEEP_PHASES, STAFF_DIVIDE,
    HARP_LOW, HARP_HIGH,
    deg_to_first_string, chord_to_spec, chord_tone_strings,
    build_sweep_strings, parse_lead_sheet, extract_chords,
    clamp_chords, full_bar_length,
)

LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
OUTPUT = ROOT / 'app' / 'tchaikovsky_mei.json'


# ── ABC pitch → (pname, oct) for MEI ──

def abc_to_pitch(abc_note):
    """Parse an ABC note like 'C,,', 'c\\'' into (pname_lower, oct)."""
    m = re.match(r"^([A-Ga-g])([',]*)$", abc_note)
    if not m:
        return None
    letter = m.group(1)
    marks = m.group(2)
    if letter.isupper():
        # Uppercase with commas: C = 4, C, = 3, C,, = 2
        oct = 4 - marks.count(',')
    else:
        # Lowercase with apostrophes: c = 5, c' = 6, c'' = 7
        oct = 5 + marks.count("'")
    return letter.lower(), oct


# ── Key signature translation ──

KEY_SIG = {
    'C':  ('0', ''),
    'G':  ('1', 's'),
    'D':  ('2', 's'),
    'A':  ('3', 's'),
    'E':  ('4', 's'),
    'F':  ('1', 'f'),
    'Bb': ('2', 'f'),
    'Eb': ('3', 'f'),
}


# ── MEI element helpers ──

def mei_note(pname, oct, dur, staff=None, grace=False, extra=''):
    """Return a <note> element string."""
    attrs = f'pname="{pname}" oct="{oct}" dur="{dur}"'
    if staff is not None:
        attrs += f' staff="{staff}"'
    if grace:
        attrs += ' grace="unacc"'
    if extra:
        attrs += ' ' + extra
    return f'<note {attrs}/>'


def mei_rest(dur, staff=None):
    attrs = f'dur="{dur}"'
    if staff is not None:
        attrs += f' staff="{staff}"'
    return f'<rest {attrs}/>'


# ── Melody parsing (ABC-ish) ──

TOKEN_RE = re.compile(
    r'"(?P<ann>[^"]*)"'              # annotation
    r'|(?P<acc>[_^=]{1,2})'          # accidental
    r"|(?P<note>[A-Ga-g])(?P<oct>[',]*)(?P<num>\d*)(?:/(?P<den>\d*))?"
    r'|(?P<rest>[zx])(?P<rnum>\d*)(?:/(?P<rden>\d*))?'
)


def parse_melody_bar(bar_raw, key, chord_rewrite=True):
    """Parse a melody bar into a list of {'type','pname','oct','dur_num','dur_den','accid','chord'}.

    dur_num/dur_den are expressed in units of the lead sheet's L (1/8 typically).
    MEI dur values are derived by the caller from the L and the numerator/denominator.
    Returns (events, pending_chord) where pending_chord is attached to the next note.
    """
    events = []
    pending_chord = None
    pending_accid = None
    i = 0
    s = bar_raw
    while i < len(s):
        c = s[i]
        if c == '"':
            end = s.find('"', i + 1)
            if end == -1:
                break
            ann = s[i + 1:end]
            if ann.startswith('^'):
                pending_chord = ann[1:]
            i = end + 1
            continue
        if c in ' \t()~.':
            i += 1
            continue
        if c in '^_=':
            pending_accid = c
            i += 1
            if i < len(s) and s[i] in '^_':
                pending_accid += s[i]
                i += 1
            continue
        if c.upper() in 'ABCDEFG':
            letter = c
            i += 1
            oct_marks = ''
            while i < len(s) and s[i] in "',":
                oct_marks += s[i]
                i += 1
            # duration
            num_s = ''
            while i < len(s) and s[i].isdigit():
                num_s += s[i]; i += 1
            den_s = ''
            if i < len(s) and s[i] == '/':
                i += 1
                while i < len(s) and s[i].isdigit():
                    den_s += s[i]; i += 1
                if not den_s:
                    den_s = '2'
            num = int(num_s) if num_s else 1
            den = int(den_s) if den_s else 1
            # pitch
            pp = abc_to_pitch(letter + oct_marks)
            if pp is None:
                continue
            pname, octnum = pp
            ev = {
                'type': 'note',
                'pname': pname,
                'oct': octnum,
                'num': num,
                'den': den,
                'accid': pending_accid,
                'chord': pending_chord,
            }
            events.append(ev)
            pending_accid = None
            pending_chord = None
            continue
        if c in 'zx':
            i += 1
            num_s = ''
            while i < len(s) and s[i].isdigit():
                num_s += s[i]; i += 1
            den_s = ''
            if i < len(s) and s[i] == '/':
                i += 1
                while i < len(s) and s[i].isdigit():
                    den_s += s[i]; i += 1
                if not den_s:
                    den_s = '2'
            num = int(num_s) if num_s else 1
            den = int(den_s) if den_s else 1
            events.append({
                'type': 'rest',
                'num': num,
                'den': den,
                'chord': pending_chord,
            })
            pending_chord = None
            continue
        i += 1
    return events


# ── Duration conversion ──

def l_units_to_mei_dur(num, den, mel_l_num, mel_l_den):
    """Convert (num/den) L-units at L:mel_l_num/mel_l_den to an MEI @dur string.

    MEI dur values: 1=whole, 2=half, 4=quarter, 8=eighth, 16=16th, etc.
    For dotted/non-standard durations, MEI supports @dots="1" etc.

    Returns (dur_value, dots) where dur_value is an MEI dur string or None if fractional.
    """
    # Total duration in whole-notes:
    # num / den units × (mel_l_num / mel_l_den) whole-notes per unit
    # = num * mel_l_num / (den * mel_l_den)
    # MEI dur = 1 / (num * mel_l_num / (den * mel_l_den)) = den * mel_l_den / (num * mel_l_num)
    from fractions import Fraction
    whole_notes = Fraction(num * mel_l_num, den * mel_l_den)
    # dur = 1/whole_notes
    if whole_notes == 0:
        return (None, 0)
    dur_frac = Fraction(1, 1) / whole_notes
    # Try standard dur values: 1, 2, 4, 8, 16, 32, 64 (with dots)
    for base in [1, 2, 4, 8, 16, 32, 64, 128]:
        if dur_frac == Fraction(base, 1):
            return (str(base), 0)
        # single dot: 1.5 × base_length → 2/3 of dur_frac
        # base.5 duration: note length = 1/base + 1/(2*base) = 3/(2*base)
        # dur_frac = 2*base/3
        if dur_frac == Fraction(2 * base, 3):
            return (str(base), 1)
        # double dot: 7/(4*base) duration → dur_frac = 4*base/7
        if dur_frac == Fraction(4 * base, 7):
            return (str(base), 2)
    return (None, 0)


# ── Melody to MEI ──

def events_to_mei(events, mel_l_num, mel_l_den, id_prefix='n'):
    """Render a list of melody events (dicts from parse_melody_bar) to a
    list of MEI element strings and a parallel list of (idx, chord) pairs.

    Events may carry 'tie_in' / 'tie_out' flags when they were split at a
    measure boundary — emit the corresponding MEI @tie attribute so
    Verovio draws a tie between the halves.
    """
    parts = []
    chords_out = []
    for ev in events:
        dur_val, dots = l_units_to_mei_dur(ev['num'], ev['den'], mel_l_num, mel_l_den)
        if dur_val is None:
            continue
        if ev['type'] == 'note':
            attrs = f'pname="{ev["pname"]}" oct="{ev["oct"]}" dur="{dur_val}"'
            if dots:
                attrs += f' dots="{dots}"'
            if ev.get('accid'):
                accid = {'^': 's', '_': 'f', '=': 'n', '^^': 'x', '__': 'ff'}.get(ev['accid'])
                if accid:
                    attrs += f' accid="{accid}"'
            tie_in = ev.get('tie_in', False)
            tie_out = ev.get('tie_out', False)
            if tie_in and tie_out:
                attrs += ' tie="m"'
            elif tie_in:
                attrs += ' tie="t"'
            elif tie_out:
                attrs += ' tie="i"'
            parts.append(f'<note xml:id="{id_prefix}{len(parts)}" {attrs}/>')
            if ev.get('chord'):
                chords_out.append((len(parts) - 1, ev['chord']))
        else:
            attrs = f'dur="{dur_val}"'
            if dots:
                attrs += f' dots="{dots}"'
            parts.append(f'<rest {attrs}/>')
    return parts, chords_out


def melody_to_mei(bar_raw, key, mel_l_num, mel_l_den):
    """Return the contents of <staff n="1"><layer n="1">...</layer></staff>."""
    events = parse_melody_bar(bar_raw, key)
    return events_to_mei(events, mel_l_num, mel_l_den)


def split_events_into_measures(events, beats_per_measure_L):
    """Split a flat event list into a list of event-lists, one per measure
    of beats_per_measure_L L-units. An event that crosses a measure
    boundary is split into two events, marked with tie_out / tie_in on
    notes so they can be tied together in MEI.
    """
    from fractions import Fraction
    limit = Fraction(beats_per_measure_L)
    measures = []
    current = []
    pos = Fraction(0)

    for ev in events:
        remaining = Fraction(ev['num'], ev['den'])
        tied_from_prev = False
        while remaining > 0:
            room = limit - pos
            take = min(remaining, room)
            new_ev = dict(ev)
            new_ev['num'] = take.numerator
            new_ev['den'] = take.denominator
            if tied_from_prev:
                new_ev['tie_in'] = True
            if take < remaining and ev['type'] == 'note':
                new_ev['tie_out'] = True
            current.append(new_ev)
            pos += take
            remaining -= take
            if pos >= limit:
                measures.append(current)
                current = []
                pos = Fraction(0)
                # Only the very first piece of an event carries its
                # chord annotation — subsequent tied halves must not
                # re-emit the chord label.
                if remaining > 0:
                    ev = dict(ev)
                    ev['chord'] = None
                tied_from_prev = (remaining > 0 and ev['type'] == 'note')
    if current:
        measures.append(current)
    return measures


# ── Cadenza to MEI (cross-staff alternation, example_624 algorithm) ──

def cadenza_to_mei(chord_specs, ts_num, ts_den, bar_eighths=None):
    """Build two parallel staff layers using the example_624 algorithm.

    bar_eighths overrides the default full-bar tuplet length. Pass it when
    rendering a pickup/partial measure so the cadenza fits that measure's
    actual duration instead of a full bar.

    Each sweep note appears exactly once on its natural staff (treble above
    middle C, bass below). At the same time position on the OPPOSITE staff
    we emit a <space/> — unsounded, unrendered time that holds the layer's
    tick so both staves stay bar-aligned.

    Because the rests naturally occur where the sweep crosses middle C,
    <beam> elements wrap only consecutive runs of same-staff notes. The
    beams break at the middle-C crossing automatically:
      bass asc → (beam1 bass) → (break) → treble asc+dsc → (beam2 treble)
                 → (break) → bass dsc → (beam3 bass)

    Notes are cue-sized so they read as an ornamental cadenza rather than
    full melody notes.

    Returns (treble_layer_xml, bass_layer_xml) or (None, None) if no sweep.
    """
    strings = build_sweep_strings(chord_specs)
    if not strings:
        return (None, None)

    # dur="8" gives a single-beam (1-level) beam stack, so the stems can be
    # as short as possible — no padding needed for extra sub-beams. A bar
    # can't literally contain 24 eighth notes of measured time, so we wrap
    # the whole cadenza in a hidden-bracket <tuplet> that scales N items
    # at nominal dur=8 to fit in exactly one bar.
    N = len(strings)
    note_dur = 8

    # Build parallel event streams: each entry is (is_note, xml, string_num).
    # string_num is used to detect direction changes within a run so beams
    # can be broken at peaks/troughs, keeping each beam monotonic (stems
    # stay short because the beam slopes naturally with the contour).
    treble_events = []
    bass_events = []
    # Track the previous register to detect middle-C crossings; at each
    # crossing we insert extra <space/> slots on both staves to open a
    # horizontal gap between the outgoing beam and the incoming beam.
    prev_rh = None
    EXTRA_GAP_SLOTS = 6  # extra <space/> pairs at each middle-C crossing
    # (needs to be visually wide AFTER the tuplet compresses the layer to
    # one bar — 2 slots got squashed to invisibility, 6 gives a clearly
    # readable gap between the outgoing and incoming beam groups).

    for s in strings:
        abc = string_to_abc(s)
        pp = abc_to_pitch(abc)
        if pp is None:
            continue
        pname, octnum = pp
        hidden = f'<space dur="{note_dur}"/>'

        rh_here = is_rh(abc)

        # Middle-C crossing: prev was in one register, now in the other.
        # Insert EXTRA_GAP_SLOTS hidden slots on BOTH staves so the beams
        # on either side of the crossing are pushed apart horizontally.
        if prev_rh is not None and prev_rh != rh_here:
            for _ in range(EXTRA_GAP_SLOTS):
                # Use a sentinel string number that won't match adjacent
                # notes for direction-detection (use -1 so direction
                # calculations on either side stay sane after the flush).
                treble_events.append((False, hidden, -1))
                bass_events.append((False, hidden, -1))

        if rh_here:
            # Treble notes: stem DOWN so the beam sits BELOW the treble
            # notes (between the staves, angled inward toward middle C).
            note_xml = (
                f'<note pname="{pname}" oct="{octnum}" dur="{note_dur}" '
                f'cue="true" stem.dir="down"/>'
            )
            treble_events.append((True, note_xml, s))
            bass_events.append((False, hidden, s))
        else:
            # Bass notes: stem UP so the beam sits ABOVE the bass notes
            # (between the staves, angled inward toward middle C).
            note_xml = (
                f'<note pname="{pname}" oct="{octnum}" dur="{note_dur}" '
                f'cue="true" stem.dir="up"/>'
            )
            treble_events.append((False, hidden, s))
            bass_events.append((True, note_xml, s))

        prev_rh = rh_here

    # Wrap runs of consecutive notes in <beam>. A <space/> breaks the beam
    # at middle-C crossings, and a direction change (peak or trough within
    # the run) also breaks the beam so each beam is monotonic.
    def emit(events):
        parts = []
        run = []        # list of note XML in current beam
        run_strs = []   # corresponding string numbers (for direction detection)

        def flush_run():
            if not run:
                return
            if len(run) > 1:
                parts.append('<beam>' + ''.join(run) + '</beam>')
            else:
                parts.append(run[0])
            run.clear()
            run_strs.clear()

        for is_note, xml, s in events:
            if not is_note:
                flush_run()
                parts.append(xml)
                continue
            # Check for direction change in the existing run: if the last
            # two notes moved in one direction and this new note reverses,
            # break the beam cleanly before this note so each beam is
            # monotonic.
            if len(run_strs) >= 2:
                prev_dir = run_strs[-1] - run_strs[-2]
                new_dir = s - run_strs[-1]
                if prev_dir != 0 and new_dir != 0 and (prev_dir > 0) != (new_dir > 0):
                    flush_run()
            run.append(xml)
            run_strs.append(s)
        flush_run()
        return ''.join(parts)

    treble_inner = emit(treble_events)
    bass_inner = emit(bass_events)

    # Wrap each staff's contents in a tuplet that compresses N items
    # (nominal dur=8 each) to fit exactly one bar. The tuplet semantics:
    # "num items play in the time of numbase items of the given dur".
    #
    #   actual_time = items * (1/note_dur) * (numbase/num)
    # Set items == num (one tuplet item per event), so:
    #   actual_time = numbase * (1/note_dur)
    # Choose numbase so actual_time == bar length (ts_num / ts_den):
    #   numbase = note_dur * ts_num / ts_den
    #
    # For dur=8: 3/4 → numbase=6, 4/4 → numbase=8, 2/4 → numbase=4,
    # 6/8 → numbase=6, etc. Bracket and number are hidden so the tuplet
    # is invisible to the reader — the cadenza just looks like an
    # ad-lib sweep of short-stemmed eighth notes.
    num = len(treble_events)  # treble and bass event lists are parallel
    if num == 0:
        return (None, None)
    if bar_eighths is not None:
        # Pickup / partial-bar override: numbase is already in 8ths.
        numbase = int(bar_eighths)
    else:
        numbase_num = note_dur * ts_num
        if numbase_num % ts_den != 0:
            # Can't build an integer tuplet ratio for this meter; skip.
            return (None, None)
        numbase = numbase_num // ts_den
    if numbase <= 0:
        return (None, None)

    tuplet_open = (
        f'<tuplet num="{num}" numbase="{numbase}" '
        f'num.visible="false" bracket.visible="false">'
    )
    tuplet_close = '</tuplet>'

    treble_layer = tuplet_open + treble_inner + tuplet_close
    bass_layer = tuplet_open + bass_inner + tuplet_close

    return (treble_layer, bass_layer)


# ── Full hymn to MEI ──

def build_hymn_mei(ls):
    key = ls['key']
    if key not in SCALES or key not in KEY_SIG:
        return None
    bars, ts, note_len, tempo = parse_lead_sheet(ls['abc'])

    ts_m = re.match(r'(\d+)/(\d+)', ts)
    unmetered = not ts_m  # source said M: none
    if ts_m:
        ts_num, ts_den = int(ts_m.group(1)), int(ts_m.group(2))
    else:
        # Source said M: none — phrases are separated by | but each
        # phrase is multiple measures of content. Default to 4/4 for
        # display and split each phrase into 4-beat sub-measures below.
        ts_num, ts_den = 4, 4
    nl_m = re.match(r'(\d+)/(\d+)', note_len)
    if not nl_m:
        # L: is required. If it's missing, the source is malformed — skip
        # the hymn loudly rather than silently inventing a unit length.
        return None
    mel_num, mel_den = int(nl_m.group(1)), int(nl_m.group(2))
    full_bar_mel = full_bar_length(f'{ts_num}/{ts_den}', note_len)

    # For M: none hymns, compute how many L-units make up one 4/4
    # sub-measure so we can split the phrase:
    #   beats_per_measure quarters * (mel_den / (mel_num * 4)) L-units
    from fractions import Fraction
    sub_measure_L = Fraction(ts_num * mel_den, ts_den * mel_num) if unmetered else None

    key_sig_num, key_sig_acc = KEY_SIG[key]
    key_sig_attr = f'key.sig="{key_sig_num}{key_sig_acc}"' if key_sig_acc else 'key.sig="0"'

    # Emit a real meter only when the source gave us one. If M: none,
    # use meter.sym="none" so Verovio draws no time signature (and does
    # not claim the bar is 4/4 when it contains 15 beats).
    if ts_num and ts_den:
        meter_attrs = f'meter.count="{ts_num}" meter.unit="{ts_den}"'
    else:
        meter_attrs = 'meter.sym="none"'

    header = f'''<?xml version="1.0" encoding="UTF-8"?>
<mei xmlns="http://www.music-encoding.org/ns/mei">
<meiHead><fileDesc><titleStmt><title>{ls["t"]}</title></titleStmt>
<pubStmt/></fileDesc></meiHead>
<music><body><mdiv><score>
<scoreDef {key_sig_attr} {meter_attrs}>
<staffGrp symbol="bracket">
<staffDef n="1" lines="5" clef.shape="G" clef.line="2" {key_sig_attr}/>
<staffGrp symbol="brace">
<staffDef n="2" lines="5" clef.shape="G" clef.line="2" scale="45%" {key_sig_attr}/>
<staffDef n="3" lines="5" clef.shape="F" clef.line="4" scale="45%" {key_sig_attr}/>
</staffGrp>
</staffGrp>
</scoreDef>
<section>
'''

    measures = []
    npb = []
    prev_specs = None
    measure_num = 0
    for mi, bar_raw in enumerate(bars):
        npb.append(len(re.findall(r'[A-Ga-g]', re.sub(r'"[^"]*"', '', bar_raw))))

        # Parse the full source "bar" (which for metered hymns is one
        # measure, and for M: none hymns is one phrase = many measures).
        all_events = parse_melody_bar(bar_raw, key)

        # Split into sub-measures. Metered hymns keep the source bar
        # exactly as-is (one sub-measure). Unmetered hymns get split
        # every sub_measure_L L-units, with ties across boundaries.
        if unmetered and sub_measure_L is not None:
            event_sub_measures = split_events_into_measures(all_events, sub_measure_L)
        else:
            event_sub_measures = [all_events]

        for sub_events in event_sub_measures:
            measure_num += 1

            # Preserve the original 'n' prefix for metered hymns so their
            # MEI output stays byte-identical to commit 33e8fdc. Only the
            # split unmetered hymns need a per-measure unique prefix
            # (their IDs must not collide across sub-measures).
            id_prefix = f'm{measure_num}n' if unmetered else 'n'
            mel_notes_mei, chord_labels = events_to_mei(
                sub_events, mel_num, mel_den, id_prefix=id_prefix
            )

            # Pickup detection: a sub-measure shorter than a full bar.
            bar_dur_l = sum(ev['num'] / ev['den'] for ev in sub_events)
            is_pickup = full_bar_mel > 0 and bar_dur_l < full_bar_mel

            # Chord specs live on the events themselves after splitting
            # (split_events_into_measures clears chord on tied halves).
            chord_list = clamp_chords([ev['chord'] for ev in sub_events if ev.get('chord')])
            specs = []
            for c in chord_list:
                spec = chord_to_spec(c, key)
                if spec is not None:
                    specs.append(spec)
            if not specs:
                specs = prev_specs
            else:
                prev_specs = specs

            staff1 = '<staff n="1"><layer n="1">' + ''.join(mel_notes_mei) + '</layer></staff>'

            # Pickup bars don't get a cadenza — the cadenza is the
            # downbeat flourish of the measure proper, not of the
            # anacrusis leading into it.
            if is_pickup or not specs:
                staff2 = '<staff n="2"><layer n="1"><mRest visible="false"/></layer></staff>'
                staff3 = '<staff n="3"><layer n="1"><mRest visible="false"/></layer></staff>'
            else:
                treble_layer, bass_layer = cadenza_to_mei(specs, ts_num, ts_den)
                if treble_layer is None:
                    staff2 = '<staff n="2"><layer n="1"><mRest visible="false"/></layer></staff>'
                    staff3 = '<staff n="3"><layer n="1"><mRest visible="false"/></layer></staff>'
                else:
                    staff2 = '<staff n="2"><layer n="1">' + treble_layer + '</layer></staff>'
                    staff3 = '<staff n="3"><layer n="1">' + bass_layer + '</layer></staff>'

            # Chord annotations (roman numerals above staff 1).
            harms = []
            beat_pos = 1.0
            ci = 0
            for ev in sub_events:
                if ev.get('chord') and ci < len(chord_labels):
                    abs_chord = ev['chord']
                    roman_label = abs_chord
                    spec = chord_to_spec(abs_chord, key)
                    if spec is not None:
                        roman_label = CHORD_NAMES.get((spec[1], spec[2]), abs_chord) or abs_chord
                    tstamp = round(beat_pos, 3)
                    harms.append(f'<harm staff="1" tstamp="{tstamp}" place="above">{roman_label}</harm>')
                    ci += 1
                dur_beats = ev['num'] / ev['den'] * (mel_num / mel_den) * ts_den
                beat_pos += dur_beats

            measures.append(
                f'<measure n="{measure_num}">' + staff1 + staff2 + staff3 + ''.join(harms) + '</measure>'
            )

    footer = '</section></score></mdiv></body></music></mei>\n'

    mei = header + '\n'.join(measures) + '\n' + footer

    return {
        'n': ls['n'],
        't': ls['t'],
        'key': key,
        'tempo': tempo,
        'mei': mei,
        'npb': npb,
    }


def main():
    print('Loading lead sheets...')
    with open(LEAD_SHEETS) as f:
        lead_sheets = json.load(f)
    print(f'  {len(lead_sheets)} hymns')

    print('Building MEI cadenzas...')
    output = []
    failed = 0
    for ls in lead_sheets:
        try:
            r = build_hymn_mei(ls)
            if r:
                output.append(r)
            else:
                failed += 1
        except Exception as e:
            print(f"  FAIL {ls.get('n', '?')} {ls.get('t', '?')}: {e}")
            failed += 1

    print(f'\nWriting {len(output)} drills to {OUTPUT} ({failed} failed)')
    with open(OUTPUT, 'w') as f:
        json.dump(output, f)
    print(f'Done. {os.path.getsize(OUTPUT) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
