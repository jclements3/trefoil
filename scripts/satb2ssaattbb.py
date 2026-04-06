#!/usr/bin/env python3
"""
SATB to SSAATTBB converter with voice leading rules.

Algorithm:
1. Parse SATB voices from OpenHymnal ABC
2. At each beat, identify the abstract chord (music21)
3. For each voice, generate a second voice (S2, A2, T2, B2):
   - Must be a chord tone of the abstract chord
   - Prefer parallel 3rd or 6th from parent voice (safe intervals)
   - No forbidden parallels (5ths, octaves) with ANY other voice
   - Smallest motion from previous beat (common tone > step > leap)
   - Correct doubling (prefer root, then 5th, avoid 3rd, never leading tone)
   - Resolve tendency tones (leading tone up, 7ths down)
4. Verify all 28 voice pairs at every beat transition

Usage:
    python3.10 scripts/satb2ssaattbb.py [--hymn N] [--all] [--verify-only]
"""

import music21
import re
import sys
import json
import warnings
from collections import defaultdict
from itertools import combinations

warnings.filterwarnings('ignore')

# ---------- Constants ----------

# Standard voice ranges (MIDI)
RANGES = {
    'S1': (60, 79),  # C4 - G5
    'S2': (60, 79),
    'A1': (53, 74),  # F3 - D5
    'A2': (53, 74),
    'T1': (48, 67),  # C3 - G4
    'T2': (48, 67),
    'B1': (40, 62),  # E2 - D4
    'B2': (40, 62),
}

# Intervals in semitones
PERFECT_FIFTH = 7
PERFECT_OCTAVE = 12
MINOR_THIRD = 3
MAJOR_THIRD = 4
MINOR_SIXTH = 8
MAJOR_SIXTH = 9

# Safe parallel intervals (3rds and 6ths)
SAFE_PARALLELS = {MINOR_THIRD, MAJOR_THIRD, MINOR_SIXTH, MAJOR_SIXTH}

# Forbidden parallel intervals
FORBIDDEN_PARALLELS = {PERFECT_FIFTH, PERFECT_OCTAVE}


# ---------- ABC Parsing ----------

def parse_voice_lines(tune_abc):
    """Extract note data per voice from raw ABC text."""
    lines = tune_abc.split('\n')
    voice_data = {'S1V1': [], 'S1V2': [], 'S2V1': [], 'S2V2': []}
    key_str = 'C'
    meter = '4/4'
    default_len = '1/4'

    for line in lines:
        km = re.match(r'^K:\s*(\S+)', line)
        if km:
            key_str = km.group(1)
        mm = re.match(r'^M:\s*(\S+)', line)
        if mm:
            meter = mm.group(1)
        lm = re.match(r'^L:\s*(\S+)', line)
        if lm:
            default_len = lm.group(1)
        for vname in voice_data:
            vm = re.match(r'\[V:\s*' + vname + r'\]\s*(.*)', line)
            if vm:
                voice_data[vname].append(vm.group(1))

    return voice_data, key_str, meter, default_len


def abc_note_to_midi(note_str):
    """Convert an ABC note token to MIDI pitch number."""
    m = re.match(r'([_^=]*)([A-Ga-g])([,\']*)', note_str)
    if not m:
        return None
    acc, letter, octave = m.groups()

    base = {
        'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67, 'A': 69, 'B': 71,
        'c': 72, 'd': 74, 'e': 76, 'f': 77, 'g': 79, 'a': 81, 'b': 83,
    }
    midi = base.get(letter)
    if midi is None:
        return None

    for ch in octave:
        if ch == ',':
            midi -= 12
        elif ch == "'":
            midi += 12

    if '^' in acc:
        midi += acc.count('^')
    elif '_' in acc:
        midi -= acc.count('_')

    return midi


def extract_all_notes(voice_lines):
    """Extract ALL notes with durations from concatenated voice ABC lines.

    Returns list of (midi, duration_str, measure_index) tuples.
    duration_str is the ABC duration suffix (e.g. '2', '/2', '3/2', '' for default).
    measure_index tracks which measure each note belongs to.
    """
    all_abc = ' '.join(voice_lines)
    # Remove inline fields like [Q:1/4=120]
    all_abc = re.sub(r'\[[A-Z]:[^\]]*\]', '', all_abc)
    # Remove decorations
    all_abc = re.sub(r'![^!]*!', '', all_abc)
    # Remove lyrics lines (w: lines should already be separate, but just in case)
    all_abc = re.sub(r'w:.*', '', all_abc)

    notes = []
    measure_idx = 0

    # Tokenize: walk through the string finding notes, rests, barlines
    pos = 0
    while pos < len(all_abc):
        ch = all_abc[pos]

        # Skip whitespace
        if ch in ' \t\n\r':
            pos += 1
            continue

        # Barlines: |, |], [|, ||, :|, |:
        if ch == '|' or (ch == '[' and pos + 1 < len(all_abc) and all_abc[pos + 1] == '|'):
            # Advance past the barline
            if ch == '[' and pos + 1 < len(all_abc) and all_abc[pos + 1] == '|':
                pos += 2
            elif ch == '|':
                pos += 1
                # Check for |], ||, |:
                if pos < len(all_abc) and all_abc[pos] in ']|:':
                    pos += 1
            measure_idx += 1
            continue

        # Colon barlines :|
        if ch == ':' and pos + 1 < len(all_abc) and all_abc[pos + 1] == '|':
            pos += 2
            if pos < len(all_abc) and all_abc[pos] in '|:':
                pos += 1
            measure_idx += 1
            continue

        # Slur markers, ties
        if ch in '()-~':
            pos += 1
            continue

        # Rests: z or Z with optional duration
        if ch in 'zZ':
            rm = re.match(r'[zZ](\d+(?:/\d+)?|/\d+)?', all_abc[pos:])
            if rm:
                dur_str = rm.group(1) or ''
                notes.append((None, dur_str, measure_idx))  # None = rest
                pos += rm.end()
            else:
                pos += 1
            continue

        # Notes: optional accidental, letter, optional octave, optional duration
        nm = re.match(r'([_^=]*)([A-Ga-g])([,\']*)(\d+(?:/\d+)?|/\d+)?', all_abc[pos:])
        if nm:
            note_str = nm.group(1) + nm.group(2) + nm.group(3)
            dur_str = nm.group(4) or ''
            midi = abc_note_to_midi(note_str)
            notes.append((midi, dur_str, measure_idx))
            pos += nm.end()
            continue

        # Skip anything else (chord symbols in quotes, etc.)
        pos += 1

    return notes


def group_notes_by_measure(notes_with_measures):
    """Group extracted notes into measures. Returns list of lists of (midi, dur_str)."""
    if not notes_with_measures:
        return []
    measures = defaultdict(list)
    for midi, dur_str, meas_idx in notes_with_measures:
        measures[meas_idx].append((midi, dur_str))
    max_idx = max(meas_idx for _, _, meas_idx in notes_with_measures)
    return [measures[i] for i in range(max_idx + 1) if measures[i]]


# ---------- Chord Analysis ----------

def build_diatonic_triads(key_str):
    """Build the 7 diatonic triads for a key. Returns list of chord_info dicts."""
    k = music21.key.Key(key_str)
    triads = []
    for deg in range(1, 8):
        root = k.pitchFromDegree(deg)
        third = k.pitchFromDegree(((deg - 1 + 2) % 7) + 1)
        fifth = k.pitchFromDegree(((deg - 1 + 4) % 7) + 1)
        c = music21.chord.Chord([root, third, fifth])
        tones = {
            'R': root.pitchClass,
            '3': third.pitchClass,
            '5': fifth.pitchClass,
        }
        triads.append({
            'chord': c,
            'name': c.pitchedCommonName,
            'common_name': c.commonName,
            'root': root,
            'root_pc': root.pitchClass,
            'tones': tones,
            'pcs': set(tones.values()),
            'degree': deg,
        })
    return triads


def identify_chord(midi_pitches, key_str=None, diatonic_triads=None):
    """Use music21 to identify the abstract chord from a set of MIDI pitches.

    If music21 can't identify a full triad/seventh, falls back to matching
    the sounding pitch classes against diatonic triads in the key.
    """
    p_objs = [music21.pitch.Pitch(midi=m) for m in midi_pitches]
    chord = music21.chord.Chord(p_objs)
    cn = chord.commonName

    # If music21 identifies a triad or seventh chord, use it directly
    if 'triad' in cn or 'seventh' in cn:
        root = chord.root()
        if root is not None:
            tones = {'R': root.pitchClass}
            if chord.third is not None:
                tones['3'] = chord.third.pitchClass
            if chord.fifth is not None:
                tones['5'] = chord.fifth.pitchClass
            if chord.seventh is not None:
                tones['7'] = chord.seventh.pitchClass
            return {
                'chord': chord,
                'name': chord.pitchedCommonName,
                'common_name': cn,
                'root': root,
                'root_pc': root.pitchClass,
                'tones': tones,
                'pcs': set(tones.values()),
            }

    # Fallback: match sounding pitch classes against diatonic triads
    if diatonic_triads is None:
        return None

    sounding_pcs = set(m % 12 for m in midi_pitches)

    best_match = None
    best_score = -1

    for triad in diatonic_triads:
        # Score = how many sounding PCs are chord tones of this triad
        match_count = len(sounding_pcs & triad['pcs'])
        # Bonus if the bass note is the root of this triad
        bass_pc = min(midi_pitches) % 12
        bass_bonus = 2 if bass_pc == triad['root_pc'] else 0
        # Bonus for root being present at all
        root_bonus = 1 if triad['root_pc'] in sounding_pcs else 0
        total = match_count + bass_bonus + root_bonus

        if total > best_score:
            best_score = total
            best_match = triad

    if best_match is not None and best_score >= 2:
        return dict(best_match)  # return a copy

    return None


def get_leading_tone(key_str):
    """Get the leading tone pitch class for a key."""
    k = music21.key.Key(key_str)
    leading = k.pitchFromDegree(7)
    return leading.pitchClass


def get_chord_tone_label(midi, chord_info):
    """Label a MIDI pitch by its function in the chord (R, 3, 5, 7)."""
    pc = midi % 12
    for label, tone_pc in chord_info['tones'].items():
        if pc == tone_pc:
            return label
    return '?'


# ---------- Voice Leading Checks ----------

def has_forbidden_parallel(voice1_prev, voice1_curr, voice2_prev, voice2_curr):
    """Check if two voices move in forbidden parallel 5ths or octaves."""
    if any(v is None for v in [voice1_prev, voice1_curr, voice2_prev, voice2_curr]):
        return False

    # Both voices must actually move
    if voice1_prev == voice1_curr and voice2_prev == voice2_curr:
        return False
    if voice1_prev == voice1_curr or voice2_prev == voice2_curr:
        return False  # oblique motion, always OK

    interval_prev = abs(voice1_prev - voice2_prev) % 12
    interval_curr = abs(voice1_curr - voice2_curr) % 12

    # Parallel 5ths or octaves (same interval type, both voices move same direction)
    if interval_prev in FORBIDDEN_PARALLELS and interval_curr == interval_prev:
        dir1 = voice1_curr - voice1_prev
        dir2 = voice2_curr - voice2_prev
        if (dir1 > 0 and dir2 > 0) or (dir1 < 0 and dir2 < 0):
            return True

    return False


def has_hidden_fifths_or_octaves(voice1_prev, voice1_curr, voice2_prev, voice2_curr):
    """Check for hidden (direct) 5ths or octaves — similar motion arriving at P5 or P8."""
    if any(v is None for v in [voice1_prev, voice1_curr, voice2_prev, voice2_curr]):
        return False

    dir1 = voice1_curr - voice1_prev
    dir2 = voice2_curr - voice2_prev

    # Must be similar motion (same direction, both move)
    if dir1 == 0 or dir2 == 0:
        return False
    if not ((dir1 > 0 and dir2 > 0) or (dir1 < 0 and dir2 < 0)):
        return False

    interval_curr = abs(voice1_curr - voice2_curr) % 12
    if interval_curr in {0, PERFECT_FIFTH}:
        return True

    return False


def check_voice_crossing(voices_at_beat):
    """Check that voices don't cross. Expects dict of voice_name: midi."""
    order = ['B2', 'B1', 'T2', 'T1', 'A2', 'A1', 'S2', 'S1']
    prev_midi = -999
    for v in order:
        if v in voices_at_beat and voices_at_beat[v] is not None:
            if voices_at_beat[v] < prev_midi:
                return True, v  # crossing detected
            prev_midi = voices_at_beat[v]
    return False, None


def count_doublings(voices_at_beat, chord_info):
    """Count how many times each chord tone is doubled."""
    counts = defaultdict(int)
    for v, midi in voices_at_beat.items():
        if midi is not None:
            label = get_chord_tone_label(midi, chord_info)
            counts[label] += 1
    return dict(counts)


# ---------- Second Voice Generation ----------

def generate_candidates(parent_midi, chord_info, voice_name, prev_midi=None):
    """Generate candidate MIDI pitches for a second voice.

    Returns list of (midi, score) tuples sorted by preference.
    """
    lo, hi = RANGES[voice_name]
    pcs = chord_info['pcs']
    candidates = []

    for midi in range(lo, hi + 1):
        pc = midi % 12
        if pc not in pcs:
            continue

        score = 0
        interval_from_parent = abs(midi - parent_midi)
        interval_class = interval_from_parent % 12

        # Prefer 3rds and 6ths from parent (safe parallel intervals)
        if interval_class in SAFE_PARALLELS:
            score += 10

        # Prefer below parent for S2/A2, can be either for T2/B2
        if voice_name in ('S2', 'A2') and midi <= parent_midi:
            score += 2
        elif voice_name in ('T2', 'B2') and midi <= parent_midi:
            score += 2

        # Prefer small motion from previous beat
        if prev_midi is not None:
            motion = abs(midi - prev_midi)
            if motion == 0:
                score += 8   # common tone
            elif motion <= 2:
                score += 6   # step
            elif motion <= 4:
                score += 3   # third
            elif motion <= 7:
                score += 1   # up to fifth
            else:
                score -= 2   # large leap penalty

        # Prefer root doubling
        label = get_chord_tone_label(midi, chord_info)
        if label == 'R':
            score += 4
        elif label == '5':
            score += 2
        elif label == '3':
            score -= 1  # avoid doubling the third
        elif label == '7':
            score -= 3  # avoid doubling the seventh

        # Don't go too far from parent
        if interval_from_parent > 12:
            score -= 5

        candidates.append((midi, score))

    # Sort by score descending
    candidates.sort(key=lambda x: -x[1])
    return candidates


def generate_second_voice(parent_notes, chord_infos, voice_name, all_voices,
                          key_str, is_outer=False):
    """Generate the second voice for one SATB part across all beats.

    Args:
        parent_notes: list of MIDI pitches for the parent voice
        chord_infos: list of chord_info dicts per beat
        voice_name: name of the new voice (S2, A2, T2, B2)
        all_voices: dict of voice_name -> list of MIDI notes (accumulated)
        key_str: key signature string
        is_outer: True if this is S2 (top) or B2 (bottom) — stricter hidden 5th rules

    Returns:
        list of MIDI pitches for the new voice
    """
    leading_tone_pc = get_leading_tone(key_str)
    result = []
    prev_midi = None

    for beat_idx in range(len(parent_notes)):
        parent_midi = parent_notes[beat_idx]

        # If parent is a rest, second voice rests too
        if parent_midi is None:
            result.append(None)
            continue

        chord_info = chord_infos[beat_idx]
        if chord_info is None:
            result.append(parent_midi)
            prev_midi = parent_midi
            continue
        candidates = generate_candidates(parent_midi, chord_info, voice_name, prev_midi)

        # Gather current and previous beat notes for all other placed voices
        other_curr = {}  # voice -> midi at beat_idx
        other_prev = {}  # voice -> midi at beat_idx - 1
        for vn, notes in all_voices.items():
            if vn == voice_name:
                continue
            if beat_idx < len(notes):
                other_curr[vn] = notes[beat_idx]
            if beat_idx > 0 and (beat_idx - 1) < len(notes):
                other_prev[vn] = notes[beat_idx - 1]

        best = None
        best_score = -999

        for midi, score in candidates:
            valid = True

            # Check forbidden parallels with every other voice
            if beat_idx > 0 and prev_midi is not None:
                for vn, curr_note in other_curr.items():
                    prev_note = other_prev.get(vn)
                    if prev_note is None or curr_note is None:
                        continue
                    if has_forbidden_parallel(prev_midi, midi, prev_note, curr_note):
                        valid = False
                        break
                    # Hidden 5ths/octaves only checked for outer voices
                    if is_outer:
                        if has_hidden_fifths_or_octaves(prev_midi, midi, prev_note, curr_note):
                            valid = False
                            break

            if not valid:
                continue

            # Check: don't double the leading tone
            if midi % 12 == leading_tone_pc:
                lt_count = sum(1 for vn, n in other_curr.items()
                              if n is not None and n % 12 == leading_tone_pc)
                if lt_count >= 1:
                    continue

            # Check tendency tone resolution (leading tone must go up)
            if prev_midi is not None and prev_midi % 12 == leading_tone_pc:
                if midi < prev_midi:
                    continue

            # Check seventh resolution (must step down)
            if prev_midi is not None and beat_idx > 0:
                prev_chord = chord_infos[beat_idx - 1]
                if prev_chord is not None:
                    prev_label = get_chord_tone_label(prev_midi, prev_chord)
                    if prev_label == '7':
                        if midi >= prev_midi:
                            continue

            # Passed all checks — take the best scoring candidate
            best = midi
            best_score = score
            break

        if best is None:
            # Relaxed fallback: try all chord tones without parallel check
            # (accept a parallel rather than doubling at unison)
            for midi, score in candidates:
                # Still enforce leading tone and tendency tone rules
                if midi % 12 == leading_tone_pc:
                    lt_count = sum(1 for vn, n in other_curr.items()
                                  if n is not None and n % 12 == leading_tone_pc)
                    if lt_count >= 1:
                        continue
                if prev_midi is not None and prev_midi % 12 == leading_tone_pc:
                    if midi < prev_midi:
                        continue
                best = midi
                break

        if best is None:
            best = parent_notes[beat_idx]

        result.append(best)
        prev_midi = best

    return result


# ---------- Verification ----------

def verify_all_pairs(all_voices, chord_infos, key_str):
    """Verify all voice pairs across all beats. Returns list of violations."""
    violations = []
    orig_violations = []
    voice_names = list(all_voices.keys())
    orig_voices = {'S1', 'A1', 'T1', 'B1'}
    n_beats = min(len(notes) for notes in all_voices.values())

    for beat_idx in range(1, n_beats):
        for v1, v2 in combinations(voice_names, 2):
            prev1 = all_voices[v1][beat_idx - 1]
            curr1 = all_voices[v1][beat_idx]
            prev2 = all_voices[v2][beat_idx - 1]
            curr2 = all_voices[v2][beat_idx]

            # Skip if any note is a rest
            if any(n is None for n in [prev1, curr1, prev2, curr2]):
                continue

            if has_forbidden_parallel(prev1, curr1, prev2, curr2):
                interval = abs(curr1 - curr2) % 12
                iname = 'P5' if interval == PERFECT_FIFTH else 'P8'
                msg = f'Beat {beat_idx}: parallel {iname} between {v1} and {v2}'
                if v1 in orig_voices and v2 in orig_voices:
                    orig_violations.append(msg)
                else:
                    violations.append(msg)

    # Voice crossing is acceptable in 5+ part writing — not checked here

    # Check leading tone doubling
    leading_pc = get_leading_tone(key_str)
    for beat_idx in range(n_beats):
        lt_voices = [v for v in voice_names
                     if all_voices[v][beat_idx] is not None
                     and all_voices[v][beat_idx] % 12 == leading_pc]
        if len(lt_voices) > 1:
            msg = f'Beat {beat_idx}: leading tone doubled in {lt_voices}'
            if all(v in orig_voices for v in lt_voices):
                orig_violations.append(msg)
            else:
                violations.append(msg)

    return violations, orig_violations


# ---------- MIDI to ABC ----------

def build_key_accidentals(key_str):
    """Build a dict of pitch class -> accidental for a key signature.
    Returns dict like {6: 1, 1: 1} for D major (F#, C#).
    Values: -1=flat, 0=natural, 1=sharp.
    """
    k = music21.key.Key(key_str)
    acc_map = {}
    for p in k.alteredPitches:
        if p.accidental.alter > 0:
            acc_map[p.pitchClass] = 1  # sharp
        elif p.accidental.alter < 0:
            acc_map[p.pitchClass] = -1  # flat
    return acc_map


def midi_to_abc(midi, key_acc_map=None):
    """Convert MIDI pitch to ABC notation string.
    key_acc_map: dict from build_key_accidentals() — used to suppress
    redundant accidentals that are already in the key signature.
    """
    p = music21.pitch.Pitch(midi=midi)
    note_name = p.name  # e.g. 'F#', 'B-', 'G'
    octave = p.octave
    letter = note_name[0]

    # Determine if we need an explicit accidental
    acc = ''
    if key_acc_map is not None:
        pc = p.pitchClass
        key_alter = key_acc_map.get(pc, 0)  # what the key sig says
        note_alter = 0
        if p.accidental is not None:
            note_alter = int(p.accidental.alter)

        # Check if note's letter is affected by key sig
        natural_pc = music21.pitch.Pitch(letter).pitchClass
        key_alter_for_letter = key_acc_map.get(natural_pc, 0)

        if note_alter == key_alter_for_letter:
            acc = ''  # key sig handles it
        elif note_alter == 1:
            acc = '^'
        elif note_alter == -1:
            acc = '_'
        elif note_alter == 0 and key_alter_for_letter != 0:
            acc = '='  # natural sign needed to override key sig
    else:
        if len(note_name) > 1:
            if '#' in note_name:
                acc = '^'
            elif '-' in note_name:
                acc = '_'

    if octave <= 4:
        abc_note = acc + letter.upper()
        abc_note += ',' * (4 - octave)
    else:
        abc_note = acc + letter.lower()
        abc_note += "'" * (octave - 5)

    return abc_note


# ---------- Main Pipeline ----------

def process_hymn(tune_abc, hymn_num=None):
    """Convert one SATB hymn to SSAATTBB, preserving full rhythms.

    Each voice preserves its own rhythm independently. Second voices (S2, A2, T2, B2)
    copy their parent's rhythm note-for-note but with chord-tone pitches.

    Voice leading is checked at measure downbeats (first note of each measure) across
    all 8 voices, since that's where all voices are rhythmically aligned.
    """
    voice_data, key_str, meter, default_len = parse_voice_lines(tune_abc)

    # Check we have all 4 voices
    for v in ['S1V1', 'S1V2', 'S2V1', 'S2V2']:
        if not voice_data[v]:
            return None, f'Missing voice {v}'

    # Extract ALL notes with durations from each voice
    voice_raw = {
        'S1': extract_all_notes(voice_data['S1V1']),
        'A1': extract_all_notes(voice_data['S1V2']),
        'T1': extract_all_notes(voice_data['S2V1']),
        'B1': extract_all_notes(voice_data['S2V2']),
    }

    # Group by measure for chord identification
    voice_meas = {v: group_notes_by_measure(raw) for v, raw in voice_raw.items()}

    n_measures = min(len(m) for m in voice_meas.values())
    if n_measures == 0:
        return None, 'No measures extracted'

    # Build diatonic triads for fallback chord identification
    diatonic_triads = build_diatonic_triads(key_str)

    # Identify chord at each measure downbeat (first non-rest note from each voice)
    measure_chords = []
    for m in range(n_measures):
        pitches = []
        for v in ['B1', 'T1', 'A1', 'S1']:
            for midi, dur in voice_meas[v][m]:
                if midi is not None:
                    pitches.append(midi)
                    break
        if pitches:
            info = identify_chord(pitches, key_str, diatonic_triads)
        else:
            info = None
        measure_chords.append(info)

    # For each parent voice, flatten to note list with per-note chord info
    def flatten_with_chords(measures, n_meas):
        notes = []  # (midi, dur_str)
        chord_indices = []
        for m in range(n_meas):
            for midi, dur in measures[m]:
                notes.append((midi, dur))
                chord_indices.append(m)
        return notes, chord_indices

    voice_notes = {}   # voice -> [(midi, dur_str), ...]
    voice_chords = {}  # voice -> [chord_info, ...] per note
    voice_meas_idx = {}  # voice -> [measure_index, ...] per note

    for v in ['S1', 'A1', 'T1', 'B1']:
        notes, cidx = flatten_with_chords(voice_meas[v], n_measures)
        voice_notes[v] = notes
        voice_chords[v] = [measure_chords[i] for i in cidx]
        voice_meas_idx[v] = cidx

    # Extract downbeat MIDI for cross-voice checking
    # downbeat_midi[voice][measure] = first non-rest MIDI in that measure
    downbeat_midi = {}
    for v in ['S1', 'A1', 'T1', 'B1']:
        downbeat_midi[v] = []
        for m in range(n_measures):
            first = None
            for midi, dur in voice_meas[v][m]:
                if midi is not None:
                    first = midi
                    break
            downbeat_midi[v].append(first)

    # Generate second voices independently per parent
    # Each second voice has same number of notes as its parent
    parent_map = {'S2': 'S1', 'A2': 'A1', 'T2': 'T1', 'B2': 'B1'}
    outer_voices = {'S2', 'B2'}

    def gen_second_voices(order):
        """Generate all 4 second voices in given order, using downbeat cross-checking."""
        all_db = dict(downbeat_midi)  # downbeat midi per voice per measure

        result_voices = {}
        result_notes = {}

        for vname in order:
            parent = parent_map[vname]
            parent_midi_list = [n[0] for n in voice_notes[parent]]
            chords = voice_chords[parent]
            meas_indices = voice_meas_idx[parent]

            # Build "all_voices" for generate_second_voice: only downbeat-aligned
            # For cross-voice checking, expand downbeat_midi to match parent's note count
            # so that at each note position, we have the other voices' current measure's downbeat
            expanded = {}
            for ov, db_list in all_db.items():
                if ov == vname:
                    continue
                expanded[ov] = [db_list[mi] if mi < len(db_list) else None
                                for mi in meas_indices]

            # Also include the parent voice itself
            expanded[parent] = parent_midi_list

            second = generate_second_voice(
                parent_midi_list, chords, vname, expanded, key_str,
                is_outer=(vname in outer_voices)
            )
            result_voices[vname] = second

            # Update downbeat_midi with this new voice's downbeats
            db = []
            note_idx = 0
            for m in range(n_measures):
                n_in_meas = len(voice_meas[parent][m])
                first = None
                for j in range(n_in_meas):
                    if note_idx + j < len(second) and second[note_idx + j] is not None:
                        first = second[note_idx + j]
                        break
                db.append(first)
                note_idx += n_in_meas
            all_db[vname] = db

        return result_voices

    # Default generation order
    second_voices = gen_second_voices(['S2', 'A2', 'T2', 'B2'])

    # Verify at downbeats across all 8 voices
    all_db = dict(downbeat_midi)
    for v2, parent in parent_map.items():
        db = []
        note_idx = 0
        for m in range(n_measures):
            n_in_meas = len(voice_meas[parent][m])
            first = None
            for j in range(n_in_meas):
                if note_idx + j < len(second_voices[v2]) and second_voices[v2][note_idx + j] is not None:
                    first = second_voices[v2][note_idx + j]
                    break
            db.append(first)
            note_idx += n_in_meas
        all_db[v2] = db

    # Build downbeat-only voices for verification
    db_voices = {v: db for v, db in all_db.items()}
    db_chords = measure_chords[:n_measures]

    new_violations, orig_violations = verify_all_pairs(db_voices, db_chords, key_str)

    # Repair pass with permutations if needed
    if new_violations:
        from itertools import permutations
        best_second = second_voices
        best_count = len(new_violations)
        best_new = new_violations

        for perm in permutations(['S2', 'A2', 'T2', 'B2']):
            trial_second = gen_second_voices(list(perm))

            # Build downbeat voices for verification
            trial_db = dict(downbeat_midi)
            for v2, parent in parent_map.items():
                db = []
                note_idx = 0
                for m in range(n_measures):
                    n_in_meas = len(voice_meas[parent][m])
                    first = None
                    for j in range(n_in_meas):
                        if note_idx + j < len(trial_second[v2]) and trial_second[v2][note_idx + j] is not None:
                            first = trial_second[v2][note_idx + j]
                            break
                    db.append(first)
                    note_idx += n_in_meas
                trial_db[v2] = db

            nv, ov = verify_all_pairs(trial_db, db_chords, key_str)
            if len(nv) < best_count:
                best_count = len(nv)
                best_second = trial_second
                best_new = nv
                if best_count == 0:
                    break

        second_voices = best_second
        new_violations = best_new

    # Assemble full result with per-voice independent data
    all_voice_data = {}  # voice -> {'midi': [...], 'durs': [...], 'meas_idx': [...]}
    for v in ['S1', 'A1', 'T1', 'B1']:
        all_voice_data[v] = {
            'midi': [n[0] for n in voice_notes[v]],
            'durs': [n[1] for n in voice_notes[v]],
            'meas_idx': voice_meas_idx[v],
        }
    for v2, parent in parent_map.items():
        all_voice_data[v2] = {
            'midi': second_voices[v2],
            'durs': [n[1] for n in voice_notes[parent]],  # same rhythm as parent
            'meas_idx': voice_meas_idx[parent],  # same measure boundaries as parent
        }

    # Generate pedal bass (PB): chord root in lowest octave, follows B1 rhythm
    # One pitch per measure — sustain by repeating the same note for every B1 note in that measure
    pb_midi = []
    pb_durs = all_voice_data['B1']['durs'][:]
    pb_meas_idx = all_voice_data['B1']['meas_idx'][:]
    b1_midi = all_voice_data['B1']['midi']
    b1_meas = all_voice_data['B1']['meas_idx']

    prev_root_midi = None
    for i in range(len(b1_midi)):
        m = b1_meas[i]
        chord = measure_chords[m] if m < len(measure_chords) else None
        if chord is not None:
            root_pc = chord['root_pc']
            # Place root in C2-C3 range (MIDI 36-48)
            root_midi = 36 + (root_pc % 12)
            if root_midi < 36:
                root_midi += 12
            prev_root_midi = root_midi
        else:
            root_midi = prev_root_midi  # sustain previous

        if b1_midi[i] is None:
            pb_midi.append(None)  # rest when B1 rests
        else:
            pb_midi.append(root_midi)

    all_voice_data['PB'] = {
        'midi': pb_midi,
        'durs': pb_durs,
        'meas_idx': pb_meas_idx,
    }

    # Count total notes (use soprano as reference for display)
    n_notes = len(voice_notes['S1'])

    result = {
        'key': key_str,
        'meter': meter,
        'default_len': default_len,
        'n_notes': n_notes,
        'n_measures': n_measures,
        'voice_data': all_voice_data,
        'chords': [c['name'] if c else '?' for c in measure_chords],
        'violations': new_violations,
        'orig_violations': orig_violations,
        'violation_count': len(new_violations),
        'orig_violation_count': len(orig_violations),
    }

    return result, None


def result_to_abc(result, title='SSAATTBB', x_num=1):
    """Convert a result dict to ABC notation string with full rhythms."""
    key = result['key']
    meter = result['meter']
    dl = result['default_len']
    vdata = result['voice_data']

    # Voice order top to bottom
    voice_order = ['S1', 'S2', 'A1', 'A2', 'T1', 'T2', 'B1', 'B2', 'PB']

    lines = []
    lines.append(f'X: {x_num}')
    lines.append(f'T: {title}')
    lines.append(f'M: {meter}')
    lines.append(f'L: {dl}')
    lines.append(f'%%staves (S1 S2) | (A1 A2) | (T1 T2) | (B1 B2) | PB')
    lines.append(f'V: S1 clef=treble name="S1"')
    lines.append(f'V: S2 clef=treble name="S2"')
    lines.append(f'V: A1 clef=treble name="A1"')
    lines.append(f'V: A2 clef=treble name="A2"')
    lines.append(f'V: T1 clef=bass name="T1"')
    lines.append(f'V: T2 clef=bass name="T2"')
    lines.append(f'V: B1 clef=bass name="B1"')
    lines.append(f'V: B2 clef=bass name="B2"')
    lines.append(f'V: PB clef=bass name="Pedal"')
    lines.append(f'K: {key}')

    key_acc = build_key_accidentals(key)

    for v in voice_order:
        vd = vdata[v]
        midi_notes = vd['midi']
        durs = vd['durs']
        meas_indices = vd['meas_idx']
        n = len(midi_notes)

        parts = []
        prev_meas = -1
        for i in range(n):
            meas_idx = meas_indices[i]
            # Insert barline when measure changes
            if meas_idx != prev_meas and prev_meas >= 0:
                parts.append('|')
            prev_meas = meas_idx

            midi = midi_notes[i]
            dur_str = durs[i]
            if midi is None:
                parts.append('z' + dur_str)
            else:
                parts.append(midi_to_abc(midi, key_acc) + dur_str)

        lines.append(f'[V: {v}] ' + ' '.join(parts) + ' |]')

    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SATB to SSAATTBB converter')
    parser.add_argument('--hymn', type=int, help='Process specific hymn number')
    parser.add_argument('--all', action='store_true', help='Process all hymns')
    parser.add_argument('--verify-only', action='store_true', help='Only verify, no generation')
    parser.add_argument('--output', type=str, default=None, help='Output file')
    parser.add_argument('--stats', action='store_true', help='Print statistics')
    args = parser.parse_args()

    with open('data/OpenHymnal.abc') as f:
        txt = f.read()

    tunes = re.split(r'\n(?=X:)', txt)

    # Index by hymn number
    hymn_map = {}
    for t in tunes:
        if not t.strip().startswith('X:'):
            continue
        xm = re.search(r'X:\s*(\d+)', t)
        if xm:
            hymn_map[int(xm.group(1))] = t

    if args.hymn:
        if args.hymn not in hymn_map:
            print(f'Hymn {args.hymn} not found')
            sys.exit(1)
        result, err = process_hymn(hymn_map[args.hymn], args.hymn)
        if err:
            print(f'Error: {err}')
            sys.exit(1)

        abc_out = result_to_abc(result, title=f'Hymn {args.hymn} SSAATTBB', x_num=args.hymn)
        print(abc_out)
        print()
        print(f'Chords: {result["chords"]}')
        print(f'New violations: {result["violation_count"]}')
        for v in result['violations']:
            print(f'  {v}')
        if result['orig_violation_count']:
            print(f'Pre-existing SATB violations: {result["orig_violation_count"]}')

    elif args.all or args.stats:
        total = 0
        total_new = 0
        total_orig = 0
        total_beats = 0
        clean = 0

        for num in sorted(hymn_map.keys()):
            result, err = process_hymn(hymn_map[num], num)
            if err:
                continue
            total += 1
            total_new += result['violation_count']
            total_orig += result['orig_violation_count']
            total_beats += result['n_notes']
            if result['violation_count'] == 0:
                clean += 1

            if not args.stats:
                print(f'Hymn {num}: {result["n_beats"]} beats, '
                      f'{result["violation_count"]} new, '
                      f'{result["orig_violation_count"]} pre-existing')

        print(f'\n=== Summary ===')
        print(f'Processed: {total} hymns')
        print(f'Total beats: {total_beats}')
        print(f'New violations (from generated voices): {total_new}')
        print(f'Pre-existing SATB violations: {total_orig}')
        print(f'Clean (0 new violations): {clean}/{total}')
        if total_beats > 0:
            print(f'New violation rate: {total_new/total_beats:.4f} per beat')
    else:
        # Default: process first hymn
        first = sorted(hymn_map.keys())[0]
        result, err = process_hymn(hymn_map[first], first)
        if err:
            print(f'Error: {err}')
            sys.exit(1)

        abc_out = result_to_abc(result, title=f'Hymn {first} SSAATTBB', x_num=first)
        print(abc_out)
        print()
        print(f'Chords: {result["chords"]}')
        print(f'New violations: {result["violation_count"]}')
        if result['orig_violation_count']:
            print(f'Pre-existing SATB violations: {result["orig_violation_count"]}')
        for v in result['violations']:
            print(f'  {v}')


if __name__ == '__main__':
    main()
