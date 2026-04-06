#!/usr/bin/env python3
"""
SATB → SSAATTBB+PB pipeline with verified stages.

Each stage is a separate function that transforms data and returns
a result + validation report. Stages can be run independently and
their outputs inspected.

Stages:
  1. parse       — ABC text → MIDI pitches with durations per voice
  2. transpose   — shift non-lever keys (Ab→G, Db→D)
  3. chords      — identify abstract chord at each measure downbeat
  4. second      — generate second voices (S2, A2, T2, B2)
  5. pedal       — generate pedal bass from chord roots
  6. verify      — check all voice leading rules
  7. format      — output as ABC (full score or grand staff)

Usage:
    python3.10 scripts/pipeline.py --hymn 22
    python3.10 scripts/pipeline.py --hymn 22 --stage parse    # stop after parse
    python3.10 scripts/pipeline.py --hymn 22 --validate       # show all validations
    python3.10 scripts/pipeline.py --stats
    python3.10 scripts/pipeline.py --hymn 22 --format grand   # grand staff output
"""

import music21
import re
import sys
import json
import warnings
from collections import defaultdict, Counter
from itertools import combinations, permutations
from fractions import Fraction

warnings.filterwarnings('ignore')

# Import core functions from satb2ssaattbb (reuse, don't duplicate)
sys.path.insert(0, 'scripts')
from satb2ssaattbb import (
    parse_voice_lines, abc_note_to_midi, build_key_accidentals,
    build_diatonic_triads, identify_chord, get_leading_tone,
    get_chord_tone_label, has_forbidden_parallel, has_hidden_fifths_or_octaves,
    generate_candidates, generate_second_voice,
    midi_to_abc, extract_all_notes, group_notes_by_measure,
    RANGES, PERFECT_FIFTH, PERFECT_OCTAVE,
)


# ============================================================
# Stage 1: Parse
# ============================================================

def stage_parse(tune_abc):
    """Parse ABC into MIDI pitches with durations per voice.

    Returns:
        data: {
            'key': str, 'meter': str, 'default_len': str,
            'voice_raw': {voice_name: [(midi, dur_str, meas_idx), ...]},
            'n_measures': int,
        }
        report: list of validation messages
    """
    voice_data, key_str, meter, default_len = parse_voice_lines(tune_abc)
    report = []

    # Validate: all 4 voices present
    for v in ['S1V1', 'S1V2', 'S2V1', 'S2V2']:
        if not voice_data[v]:
            report.append(f'FAIL: Missing voice {v}')
            return None, report

    # Build key accidentals for correct ABC parsing
    key_acc = build_key_accidentals(key_str)

    voice_raw = {
        'S1': extract_all_notes(voice_data['S1V1'], key_acc),
        'A1': extract_all_notes(voice_data['S1V2'], key_acc),
        'T1': extract_all_notes(voice_data['S2V1'], key_acc),
        'B1': extract_all_notes(voice_data['S2V2'], key_acc),
    }

    # Validate: all voices have notes
    for v, raw in voice_raw.items():
        if not raw:
            report.append(f'FAIL: {v} has no notes')
            return None, report
        report.append(f'OK: {v} has {len(raw)} notes')

    # Validate: measure counts are consistent
    voice_meas = {v: group_notes_by_measure(raw) for v, raw in voice_raw.items()}
    meas_counts = {v: len(m) for v, m in voice_meas.items()}
    n_measures = min(meas_counts.values())

    if len(set(meas_counts.values())) > 1:
        report.append(f'WARN: Unequal measure counts: {meas_counts} (using min={n_measures})')
    else:
        report.append(f'OK: All voices have {n_measures} measures')

    # Validate: soprano is highest, bass is lowest at each downbeat
    crossing_count = 0
    for m in range(n_measures):
        midis = {}
        for v in ['S1', 'A1', 'T1', 'B1']:
            for midi, dur, idx in voice_raw[v]:
                if idx == m and midi is not None:
                    midis[v] = midi
                    break
        if all(v in midis for v in ['S1', 'A1', 'T1', 'B1']):
            if midis['S1'] < midis['A1'] or midis['A1'] < midis['T1'] or midis['T1'] < midis['B1']:
                crossing_count += 1
    if crossing_count:
        report.append(f'WARN: {crossing_count} measures with voice crossing in original SATB')
    else:
        report.append(f'OK: No voice crossing in original SATB')

    data = {
        'key': key_str,
        'meter': meter,
        'default_len': default_len,
        'voice_raw': voice_raw,
        'n_measures': n_measures,
    }
    return data, report


# ============================================================
# Stage 2: Transpose
# ============================================================

TRANSPOSE_MAP = {'Ab': ('G', -1), 'Db': ('D', 1)}

def stage_transpose(data):
    """Transpose non-lever keys to lever harp range.

    Returns:
        data: updated with transposed pitches and new key
        report: list of validation messages
    """
    report = []
    key_str = data['key']

    if key_str in TRANSPOSE_MAP:
        new_key, semitones = TRANSPOSE_MAP[key_str]
        report.append(f'OK: Transposing {key_str} → {new_key} ({semitones:+d} semitones)')

        for v in data['voice_raw']:
            data['voice_raw'][v] = [
                (midi + semitones if midi is not None else None, dur, meas)
                for midi, dur, meas in data['voice_raw'][v]
            ]
        data['key'] = new_key
    else:
        report.append(f'OK: Key {key_str} is a lever harp key, no transposition needed')

    # Validate: all pitches in harp range (C2=36 to G5=79)
    out_of_range = 0
    for v, raw in data['voice_raw'].items():
        for midi, dur, meas in raw:
            if midi is not None and (midi < 36 or midi > 79):
                out_of_range += 1

    if out_of_range:
        report.append(f'WARN: {out_of_range} notes outside harp range (C2-G5)')
    else:
        report.append(f'OK: All notes within harp range')

    # Validate: key is now a lever harp key
    lever_keys = {'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E'}
    if data['key'] in lever_keys:
        report.append(f'OK: Key {data["key"]} is a valid lever harp key')
    else:
        report.append(f'FAIL: Key {data["key"]} is NOT a lever harp key')

    return data, report


# ============================================================
# Stage 3: Chord Identification
# ============================================================

def stage_chords(data):
    """Identify the abstract chord at each measure downbeat.

    Returns:
        data: updated with 'measure_chords' and 'voice_meas'
        report: list of validation messages
    """
    report = []
    key_str = data['key']
    voice_raw = data['voice_raw']
    n_measures = data['n_measures']

    diatonic_triads = build_diatonic_triads(key_str)
    voice_meas = {v: group_notes_by_measure(raw) for v, raw in voice_raw.items()}

    measure_chords = []
    unidentified = 0
    for m in range(n_measures):
        pitches = []
        for v in ['B1', 'T1', 'A1', 'S1']:
            if m < len(voice_meas[v]):
                for midi, dur in voice_meas[v][m]:
                    if midi is not None:
                        pitches.append(midi)
                        break
        if pitches:
            info = identify_chord(pitches, key_str, diatonic_triads)
            if info is None:
                unidentified += 1
        else:
            info = None
            unidentified += 1
        measure_chords.append(info)

    if unidentified:
        report.append(f'WARN: {unidentified}/{n_measures} measures with unidentified chords')
    else:
        report.append(f'OK: All {n_measures} measures have identified chords')

    # Validate: chord names are reasonable for the key
    chord_names = [c['name'] if c else '?' for c in measure_chords]
    report.append(f'OK: Chords: {", ".join(chord_names[:10])}{"..." if len(chord_names) > 10 else ""}')

    data['measure_chords'] = measure_chords
    data['voice_meas'] = voice_meas
    return data, report


# ============================================================
# Stage 4: Generate Second Voices
# ============================================================

def stage_second_voices(data):
    """Generate S2, A2, T2, B2 from the original SATB.

    Returns:
        data: updated with voice_notes, voice_chords, voice_meas_idx,
              second_voices, downbeat_midi
        report: list of validation messages
    """
    report = []
    key_str = data['key']
    voice_raw = data['voice_raw']
    voice_meas = data['voice_meas']
    measure_chords = data['measure_chords']
    n_measures = data['n_measures']

    # Flatten notes with chord info
    def flatten_with_chords(measures, n_meas):
        notes = []
        chord_indices = []
        for m in range(n_meas):
            for midi, dur in measures[m]:
                notes.append((midi, dur))
                chord_indices.append(m)
        return notes, chord_indices

    voice_notes = {}
    voice_chords = {}
    voice_meas_idx = {}

    for v in ['S1', 'A1', 'T1', 'B1']:
        notes, cidx = flatten_with_chords(voice_meas[v], n_measures)
        voice_notes[v] = notes
        voice_chords[v] = [measure_chords[i] for i in cidx]
        voice_meas_idx[v] = cidx

    # Extract downbeat MIDI for cross-voice checking
    downbeat_midi = {}
    for v in ['S1', 'A1', 'T1', 'B1']:
        downbeat_midi[v] = []
        for m in range(n_measures):
            first = None
            if m < len(voice_meas[v]):
                for midi, dur in voice_meas[v][m]:
                    if midi is not None:
                        first = midi
                        break
            downbeat_midi[v].append(first)

    # Generate second voices
    parent_map = {'S2': 'S1', 'A2': 'A1', 'T2': 'T1', 'B2': 'B1'}
    outer_voices = {'S2', 'B2'}

    def gen_second_voices(order):
        all_db = dict(downbeat_midi)
        result_voices = {}
        for vname in order:
            parent = parent_map[vname]
            parent_midi_list = [n[0] for n in voice_notes[parent]]
            chords_list = voice_chords[parent]
            meas_indices = voice_meas_idx[parent]

            expanded = {}
            for ov, db_list in all_db.items():
                if ov == vname:
                    continue
                expanded[ov] = [db_list[mi] if mi < len(db_list) else None
                                for mi in meas_indices]
            expanded[parent] = parent_midi_list

            second = generate_second_voice(
                parent_midi_list, chords_list, vname, expanded, key_str,
                is_outer=(vname in outer_voices)
            )
            result_voices[vname] = second

            # Update downbeat_midi
            db = []
            note_idx = 0
            for m in range(n_measures):
                n_in_meas = len(voice_meas[parent][m]) if m < len(voice_meas[parent]) else 0
                first = None
                for j in range(n_in_meas):
                    if note_idx + j < len(second) and second[note_idx + j] is not None:
                        first = second[note_idx + j]
                        break
                db.append(first)
                note_idx += n_in_meas
            all_db[vname] = db
        return result_voices, all_db

    second_voices, all_db = gen_second_voices(['S2', 'A2', 'T2', 'B2'])

    # Validate: count unison (fallback) notes
    unison_count = 0
    total_notes = 0
    for v2, parent in parent_map.items():
        parent_midis = [n[0] for n in voice_notes[parent]]
        for i, (gen, orig) in enumerate(zip(second_voices[v2], parent_midis)):
            total_notes += 1
            if gen == orig:
                unison_count += 1

    report.append(f'OK: Generated {total_notes} second-voice notes')
    if unison_count:
        report.append(f'WARN: {unison_count} notes at unison with parent ({100*unison_count/total_notes:.1f}%)')
    else:
        report.append(f'OK: No unison fallbacks')

    # Try permutation repair
    from satb2ssaattbb import verify_all_pairs
    db_chords = measure_chords[:n_measures]
    new_violations, orig_violations = verify_all_pairs(all_db, db_chords, key_str)

    if new_violations:
        best_second = second_voices
        best_count = len(new_violations)
        best_new = new_violations
        best_db = all_db

        for perm in permutations(['S2', 'A2', 'T2', 'B2']):
            trial_second, trial_db = gen_second_voices(list(perm))
            nv, ov = verify_all_pairs(trial_db, db_chords, key_str)
            if len(nv) < best_count:
                best_count = len(nv)
                best_second = trial_second
                best_new = nv
                best_db = trial_db
                if best_count == 0:
                    break

        second_voices = best_second
        new_violations = best_new
        all_db = best_db

    report.append(f'OK: {len(new_violations)} new violations after repair pass')

    data['voice_notes'] = voice_notes
    data['voice_chords'] = voice_chords
    data['voice_meas_idx'] = voice_meas_idx
    data['second_voices'] = second_voices
    data['downbeat_midi'] = all_db
    data['parent_map'] = parent_map
    data['new_violations'] = new_violations
    data['orig_violations'] = orig_violations
    return data, report


# ============================================================
# Stage 5: Pedal Bass
# ============================================================

def stage_pedal(data):
    """Generate pedal bass — chord root in lowest octave, follows B1 rhythm.

    Returns:
        data: updated with 'all_voice_data' containing all 9 voices
        report: list of validation messages
    """
    report = []
    voice_notes = data['voice_notes']
    voice_meas_idx = data['voice_meas_idx']
    measure_chords = data['measure_chords']
    second_voices = data['second_voices']
    parent_map = data['parent_map']

    # Assemble all voice data
    all_voice_data = {}
    for v in ['S1', 'A1', 'T1', 'B1']:
        all_voice_data[v] = {
            'midi': [n[0] for n in voice_notes[v]],
            'durs': [n[1] for n in voice_notes[v]],
            'meas_idx': voice_meas_idx[v],
        }
    for v2, parent in parent_map.items():
        all_voice_data[v2] = {
            'midi': second_voices[v2],
            'durs': [n[1] for n in voice_notes[parent]],
            'meas_idx': voice_meas_idx[parent],
        }

    # Generate pedal bass
    b1_midi = all_voice_data['B1']['midi']
    b1_meas = all_voice_data['B1']['meas_idx']
    pb_midi = []
    prev_root_midi = None

    for i in range(len(b1_midi)):
        m = b1_meas[i]
        chord = measure_chords[m] if m < len(measure_chords) else None
        if chord is not None:
            root_pc = chord['root_pc']
            root_midi = 36 + (root_pc % 12)
            if root_midi < 36:
                root_midi += 12
            prev_root_midi = root_midi
        else:
            root_midi = prev_root_midi

        if b1_midi[i] is None:
            pb_midi.append(None)
        else:
            pb_midi.append(root_midi)

    all_voice_data['PB'] = {
        'midi': pb_midi,
        'durs': all_voice_data['B1']['durs'][:],
        'meas_idx': all_voice_data['B1']['meas_idx'][:],
    }

    # Validate: pedal bass is always the chord root
    wrong_root = 0
    for i in range(len(pb_midi)):
        if pb_midi[i] is None:
            continue
        m = b1_meas[i]
        chord = measure_chords[m] if m < len(measure_chords) else None
        if chord is not None:
            if pb_midi[i] % 12 != chord['root_pc']:
                wrong_root += 1

    if wrong_root:
        report.append(f'FAIL: {wrong_root} pedal bass notes not on chord root')
    else:
        report.append(f'OK: All pedal bass notes are chord roots')

    # Validate: pedal bass in range C2-C3
    out_of_range = sum(1 for m in pb_midi if m is not None and (m < 36 or m > 48))
    if out_of_range:
        report.append(f'WARN: {out_of_range} pedal bass notes outside C2-C3 range')
    else:
        report.append(f'OK: All pedal bass notes in C2-C3 range')

    report.append(f'OK: 9 voices assembled ({len(all_voice_data)} total)')

    data['all_voice_data'] = all_voice_data
    return data, report


# ============================================================
# Stage 6: Verify
# ============================================================

def stage_verify(data):
    """Run all voice leading verification checks.

    Returns:
        data: unchanged
        report: list of validation messages
    """
    report = []

    new_v = data.get('new_violations', [])
    orig_v = data.get('orig_violations', [])

    report.append(f'OK: New violations: {len(new_v)}')
    report.append(f'INFO: Pre-existing SATB violations: {len(orig_v)}')

    for v in new_v:
        report.append(f'  VIOLATION: {v}')

    if len(new_v) == 0:
        report.append(f'OK: CLEAN — no new voice leading violations')

    return data, report


# ============================================================
# Stage 7: Vertical Consolidation (Grand Staff)
# ============================================================

def stage_vertical(data):
    """Stack all voices into RH (treble) and LH (bass) chord events per beat.

    Groups:
      RH: S1+S2 (soprano rhythm) + A1+A2 (alto rhythm)
      LH: T1+T2 (tenor rhythm) + B1+B2+PB (bass rhythm)

    At each time point within a measure, collects all sounding pitches,
    deduplicates, and produces (sorted_pitches_tuple, duration) events.

    Returns:
        data: updated with 'grand_staff' = {
            'rh_measures': [[(pitches_tuple, dur_fraction), ...], ...],
            'lh_measures': [[(pitches_tuple, dur_fraction), ...], ...],
        }
        report: validation messages
    """
    report = []
    vdata = data['all_voice_data']
    n_measures = data['n_measures']

    def parse_dur(dur_str):
        if not dur_str:
            return Fraction(1)
        if '/' in dur_str:
            parts = dur_str.split('/')
            num = int(parts[0]) if parts[0] else 1
            den = int(parts[1]) if len(parts) > 1 and parts[1] else 2
            return Fraction(num, den)
        return Fraction(int(dur_str))

    def build_measure_events(voice_groups):
        """Time-align voice groups and stack pitches per beat.

        Returns list of measures, each a list of (pitches_tuple, dur_fraction).
        """
        first_v = voice_groups[0][0]
        meas_indices = vdata[first_v]['meas_idx']
        n_notes = len(meas_indices)
        n_meas = max(meas_indices) + 1 if n_notes > 0 else 0

        raw_events = [[] for _ in range(n_meas)]

        for group in voice_groups:
            ref_voice = group[0]
            durs = vdata[ref_voice]['durs']
            midxs = vdata[ref_voice]['meas_idx']
            midis_lists = {v: vdata[v]['midi'] for v in group}

            cur_meas = -1
            t = Fraction(0)
            for i in range(len(durs)):
                m = midxs[i]
                if m != cur_meas:
                    t = Fraction(0)
                    cur_meas = m

                dur_frac = parse_dur(durs[i])
                pitches = set()
                for v in group:
                    mid = midis_lists[v][i]
                    if mid is not None:
                        pitches.add(mid)

                if m < n_meas:
                    raw_events[m].append((t, pitches, dur_frac))
                t += dur_frac

        # Merge events at same time point, compute durations from gaps
        result_measures = []
        for m in range(n_meas):
            events = raw_events[m]
            if not events:
                result_measures.append([])
                continue

            time_map = {}
            for t, pitches, dur in events:
                if t not in time_map:
                    time_map[t] = (set(), dur)
                time_map[t][0].update(pitches)
                if dur < time_map[t][1]:
                    time_map[t] = (time_map[t][0], dur)

            sorted_times = sorted(time_map.keys())
            measure_events = []
            for idx, t in enumerate(sorted_times):
                pitches, orig_dur = time_map[t]
                if idx + 1 < len(sorted_times):
                    dur_frac = sorted_times[idx + 1] - t
                else:
                    dur_frac = orig_dur
                measure_events.append((tuple(sorted(pitches)), dur_frac))

            result_measures.append(measure_events)

        return result_measures

    rh_measures = build_measure_events([['S2', 'S1'], ['A2', 'A1']])
    lh_measures = build_measure_events([['T2', 'T1'], ['PB', 'B2', 'B1']])

    # Validate: count total events and unique chord shapes
    rh_events = sum(len(m) for m in rh_measures)
    lh_events = sum(len(m) for m in lh_measures)
    rh_shapes = len(set(p for m in rh_measures for p, d in m))
    lh_shapes = len(set(p for m in lh_measures for p, d in m))

    report.append(f'OK: RH {rh_events} events, {rh_shapes} unique chord shapes')
    report.append(f'OK: LH {lh_events} events, {lh_shapes} unique chord shapes')

    data['grand_staff'] = {
        'rh_measures': rh_measures,
        'lh_measures': lh_measures,
    }
    return data, report


# ============================================================
# Stage 8: Horizontal Consolidation
# ============================================================

def stage_horizontal(data):
    """Merge consecutive identical chords within each measure.

    Operates on the grand_staff rh_measures and lh_measures.

    Returns:
        data: updated grand_staff with consolidated measures
        report: validation messages
    """
    report = []
    gs = data['grand_staff']

    def consolidate(measures):
        total_before = sum(len(m) for m in measures)
        result = []
        for meas_events in measures:
            merged = []
            for pitches, dur in meas_events:
                if merged and merged[-1][0] == pitches and pitches:
                    merged[-1] = (pitches, merged[-1][1] + dur)
                else:
                    merged.append((pitches, dur))
            result.append(merged)
        total_after = sum(len(m) for m in result)
        return result, total_before, total_after

    rh_cons, rh_before, rh_after = consolidate(gs['rh_measures'])
    lh_cons, lh_before, lh_after = consolidate(gs['lh_measures'])

    report.append(f'OK: RH {rh_before} → {rh_after} events ({rh_before - rh_after} merged)')
    report.append(f'OK: LH {lh_before} → {lh_after} events ({lh_before - lh_after} merged)')

    data['grand_staff']['rh_measures'] = rh_cons
    data['grand_staff']['lh_measures'] = lh_cons
    return data, report


# ============================================================
# Stage 9: Format
# ============================================================

def stage_format(data, title='SSAATTBB', x_num=1, fmt='grand'):
    """Format as ABC notation.

    fmt: 'full' for 10-voice score, 'grand' for melody + grand staff
    """
    from satb2ssaattbb import (result_to_abc, midi_to_abc,
                                build_key_accidentals)

    if fmt == 'grand':
        # Use the pre-computed grand_staff data
        key = data['key']
        meter = data['meter']
        dl = data['default_len']
        vdata = data['all_voice_data']
        chords_list = [c['name'] if c else '?' for c in data['measure_chords']]
        gs = data['grand_staff']
        key_acc = build_key_accidentals(key)

        def format_dur(val):
            if val == 1:
                return ''
            if val == int(val):
                return str(int(val))
            f = Fraction(val).limit_denominator(16)
            if f.numerator == 1 and f.denominator == 2:
                return '/2'
            if f.denominator == 1:
                return str(f.numerator)
            return f'{f.numerator}/{f.denominator}'

        def chord_display_name(chord_str):
            if not chord_str or chord_str == '?':
                return ''
            m = re.match(r'^([A-G][b#]?)-?(.*)', chord_str)
            if not m:
                return chord_str
            root, qual = m.group(1), m.group(2)
            if 'major triad' in qual: return root
            elif 'minor triad' in qual: return root + 'm'
            elif 'diminished triad' in qual: return root + 'dim'
            elif 'augmented triad' in qual: return root + 'aug'
            elif 'dominant seventh' in qual: return root + '7'
            elif 'minor seventh' in qual: return root + 'm7'
            elif 'major seventh' in qual: return root + 'maj7'
            elif 'half-diminished seventh' in qual: return root + 'm7b5'
            elif 'diminished seventh' in qual: return root + 'dim7'
            else: return root

        def events_to_abc(measures, key_acc):
            parts = []
            for mi, meas_events in enumerate(measures):
                if mi > 0:
                    parts.append('|')
                for pitches, dur_frac in meas_events:
                    dur_out = format_dur(dur_frac)
                    if not pitches:
                        parts.append('z' + dur_out)
                    elif len(pitches) == 1:
                        parts.append(midi_to_abc(pitches[0], key_acc) + dur_out)
                    else:
                        notes = [midi_to_abc(p, key_acc) for p in pitches]
                        parts.append('[' + ''.join(notes) + ']' + dur_out)
            return ' '.join(parts) + ' |]'

        # Build melody line
        s1 = vdata['S1']
        mel_parts = []
        prev_meas = -1
        for i in range(len(s1['midi'])):
            meas_idx = s1['meas_idx'][i]
            if meas_idx != prev_meas and prev_meas >= 0:
                mel_parts.append('|')
            chord_ann = ''
            if meas_idx != prev_meas:
                cname = chord_display_name(chords_list[meas_idx]) if meas_idx < len(chords_list) else ''
                if cname:
                    chord_ann = f'"^{cname}"'
            prev_meas = meas_idx
            midi = s1['midi'][i]
            dur = s1['durs'][i]
            if midi is None:
                mel_parts.append(chord_ann + 'z' + dur)
            else:
                mel_parts.append(chord_ann + midi_to_abc(midi, key_acc) + dur)
        melody_abc = ' '.join(mel_parts) + ' |]'

        rh_abc = events_to_abc(gs['rh_measures'], key_acc)
        lh_abc = events_to_abc(gs['lh_measures'], key_acc)

        lines = []
        lines.append(f'X: {x_num}')
        lines.append(f'T: {title}')
        lines.append(f'M: {meter}')
        lines.append(f'L: {dl}')
        lines.append(f'%%staves M | {{RH LH}}')
        lines.append(f'V: M clef=treble name="Melody"')
        lines.append(f'V: RH clef=treble name="RH"')
        lines.append(f'V: LH clef=bass name="LH"')
        lines.append(f'K: {key}')
        lines.append(f'[V: M] {melody_abc}')
        lines.append(f'[V: RH] {rh_abc}')
        lines.append(f'[V: LH] {lh_abc}')
        return '\n'.join(lines)
    else:
        from satb2ssaattbb import result_to_abc
        result = {
            'key': data['key'],
            'meter': data['meter'],
            'default_len': data['default_len'],
            'n_notes': len(data['all_voice_data']['S1']['midi']),
            'n_measures': data['n_measures'],
            'voice_data': data['all_voice_data'],
            'chords': [c['name'] if c else '?' for c in data['measure_chords']],
            'violations': data.get('new_violations', []),
            'orig_violations': data.get('orig_violations', []),
            'violation_count': len(data.get('new_violations', [])),
            'orig_violation_count': len(data.get('orig_violations', [])),
        }
        return result_to_abc(result, title=title, x_num=x_num)


# ============================================================
# Full Pipeline
# ============================================================

def run_pipeline(tune_abc, hymn_num=None, stop_after=None, fmt='grand', title=None):
    """Run the full pipeline with validation at each stage.

    Args:
        tune_abc: raw ABC text
        hymn_num: hymn number for output
        stop_after: stage name to stop after (None = run all)
        fmt: 'full' or 'grand'
        title: display title for ABC output

    Returns:
        data: pipeline data dict
        all_reports: dict of stage_name -> report list
        abc_output: formatted ABC string (or None if stopped early)
    """
    stages = [
        ('parse', stage_parse),
        ('transpose', stage_transpose),
        ('chords', stage_chords),
        ('second', stage_second_voices),
        ('pedal', stage_pedal),
        ('verify', stage_verify),
        ('vertical', stage_vertical),
        ('horizontal', stage_horizontal),
    ]

    all_reports = {}
    data = tune_abc  # first stage takes raw ABC

    for stage_name, stage_fn in stages:
        if stage_name == 'parse':
            data, report = stage_fn(data)
        else:
            data, report = stage_fn(data)

        all_reports[stage_name] = report

        if data is None:
            return None, all_reports, None

        if stop_after == stage_name:
            return data, all_reports, None

    # Format stage
    if title is None:
        title = f'{hymn_num:03d}' if hymn_num else 'SSAATTBB'
    abc_output = stage_format(data, title=title, x_num=hymn_num or 1, fmt=fmt)

    return data, all_reports, abc_output


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='SATB→SSAATTBB verified pipeline')
    parser.add_argument('--hymn', type=int, help='Process specific hymn number')
    parser.add_argument('--stage', type=str, help='Stop after this stage')
    parser.add_argument('--validate', action='store_true', help='Show all validation reports')
    parser.add_argument('--stats', action='store_true', help='Run all hymns and show stats')
    parser.add_argument('--format', type=str, default='grand', choices=['full', 'grand'],
                        help='Output format')
    parser.add_argument('--build-json', action='store_true', help='Build JSON data file')
    args = parser.parse_args()

    with open('data/OpenHymnal.abc') as f:
        txt = f.read()

    tunes = re.split(r'\n(?=X:)', txt)
    hymn_map = {}
    titles = {}
    for t in tunes:
        if not t.strip().startswith('X:'):
            continue
        xm = re.search(r'X:\s*(\d+)', t)
        tm = re.search(r'T:\s*(.*)', t)
        if xm:
            num = int(xm.group(1))
            hymn_map[num] = t
            titles[num] = tm.group(1).strip() if tm else f'Hymn {num}'

    if args.hymn:
        if args.hymn not in hymn_map:
            print(f'Hymn {args.hymn} not found')
            sys.exit(1)

        data, reports, abc_out = run_pipeline(
            hymn_map[args.hymn], args.hymn,
            stop_after=args.stage, fmt=args.format
        )

        if args.validate or args.stage:
            for stage_name, report in reports.items():
                print(f'\n=== Stage: {stage_name} ===')
                for msg in report:
                    print(f'  {msg}')

        if abc_out:
            print()
            print(abc_out)

    elif args.stats:
        total = 0
        clean = 0
        total_new_v = 0
        stage_fails = Counter()

        for num in sorted(hymn_map.keys()):
            data, reports, abc_out = run_pipeline(hymn_map[num], num, fmt=args.format)
            if data is None:
                for stage, report in reports.items():
                    for msg in report:
                        if msg.startswith('FAIL'):
                            stage_fails[stage] += 1
                continue
            total += 1
            nv = len(data.get('new_violations', []))
            total_new_v += nv
            if nv == 0:
                clean += 1

        print(f'\n=== Pipeline Stats ===')
        print(f'Processed: {total} hymns')
        print(f'Clean (0 new violations): {clean}/{total}')
        print(f'Total new violations: {total_new_v}')
        if stage_fails:
            print(f'Stage failures: {dict(stage_fails)}')

    elif args.build_json:
        results = []
        for num in sorted(hymn_map.keys()):
            title = titles.get(num, f'Hymn {num}')
            full_title = f'{num:03d} {title}'
            data, reports, abc_out = run_pipeline(
                hymn_map[num], num, fmt=args.format, title=full_title
            )
            if abc_out is None:
                continue
            results.append({
                'n': num,
                't': f'{num:03d} {title}',
                'abc': abc_out,
                'key': data['key'],
                'violations': len(data.get('new_violations', [])),
            })

        for path in ['app/ssaattbb_data.json', 'app/app/src/main/assets/ssaattbb_data.json']:
            with open(path, 'w') as f:
                json.dump(results, f)
        print(f'Wrote {len(results)} hymns')


if __name__ == '__main__':
    main()
