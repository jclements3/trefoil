#!/usr/bin/env python3
"""Post-process harp hymnal ABC files to optimize chord voicings.

Goals:
- Enforce max hand span per hand (diatonic steps)
- Target 6-8 unique notes per chord
- Spread notes using wider intervals (3rds, 5ths) instead of clusters
- Penalize minor 2nds (adjacent diatonic notes) within a hand
- Recalculate chord fraction annotations (abstract roman, RH name, LH name)

Reads from and writes to handout/harp_hymnal/*.abc
"""

import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")
import music21

sys.path.insert(0, os.path.dirname(__file__))
from chord_name import best_name, roman_name

HARP_DIR = os.path.join(os.path.dirname(__file__), "..", "handout/harp_hymnal")
MAX_HAND_SPAN = 12  # max diatonic strings reachable in one hand

KEY_PC = {
    "C": 0, "G": 7, "D": 2, "A": 9, "E": 4, "B": 11, "F": 5,
    "Bb": 10, "Eb": 3, "Ab": 8, "Db": 1, "F#": 6, "Gb": 6, "Cb": 11, "C#": 1,
}
PC_TO_C = {0: "C", 2: "D", 4: "E", 5: "F", 7: "G", 9: "A", 11: "B"}


def get_key_accidentals(key_name):
    try:
        k = music21.key.Key(key_name)
        return {p.step: p.accidental.alter for p in k.alteredPitches}
    except Exception:
        return {}


def get_scale_midis(key_name):
    """All diatonic MIDI values for a key in the harp range."""
    try:
        sc = music21.key.Key(key_name).getScale()
        return sorted(set(p.midi for p in sc.getPitches("C1", "C7")))
    except Exception:
        return sorted(
            set(p.midi for p in music21.scale.MajorScale("C").getPitches("C1", "C7"))
        )


def get_scale_pitches(key_name):
    """All diatonic music21 pitches for a key."""
    try:
        sc = music21.key.Key(key_name).getScale()
        pitches = sc.getPitches("C1", "C7")
        lookup = {}
        for p in pitches:
            lookup[p.midi] = p
        return lookup
    except Exception:
        sc = music21.scale.MajorScale("C")
        pitches = sc.getPitches("C1", "C7")
        lookup = {}
        for p in pitches:
            lookup[p.midi] = p
        return lookup


def diatonic_span(midi_lo, midi_hi, scale_midis):
    """Count diatonic strings between two MIDI values (inclusive)."""
    return sum(1 for m in scale_midis if midi_lo <= m <= midi_hi)


def pitch_to_abc(p, key_acc):
    name = p.step
    octave = p.octave if p.octave else 4
    acc = ""
    if p.accidental:
        a = p.accidental.alter
        ka = key_acc.get(name, 0)
        if a != ka:
            if a == 1: acc = "^"
            elif a == -1: acc = "_"
            elif a == 2: acc = "^^"
            elif a == -2: acc = "__"
            elif a == 0: acc = "="
    if octave >= 5:
        return acc + name.lower() + "'" * (octave - 5)
    elif octave == 4:
        return acc + name
    else:
        return acc + name + "," * (4 - octave)


def dur_to_abc(ql):
    if ql == 1.0: return ""
    if ql == 2.0: return "2"
    if ql == 3.0: return "3"
    if ql == 4.0: return "4"
    if ql == 0.5: return "/"
    if ql == 0.25: return "//"
    if ql == 1.5: return "3/2"
    if ql == 0.75: return "3/4"
    if ql == 6.0: return "6"
    from fractions import Fraction
    f = Fraction(ql).limit_denominator(16)
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def parse_abc_note(token, key_acc):
    """Parse a single ABC note token to a music21 pitch, or None for rest."""
    if token.startswith("z"):
        return None
    m = re.match(r"([_^=]*)([A-Ga-g])([,']*)", token)
    if not m:
        return None
    acc_str, note_char, oct_str = m.group(1), m.group(2), m.group(3)
    step = note_char.upper()
    base_midi = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]

    if acc_str:
        if "^^" in acc_str: alter = 2
        elif "^" in acc_str: alter = 1
        elif "__" in acc_str: alter = -2
        elif "_" in acc_str: alter = -1
        elif "=" in acc_str: alter = 0
        else: alter = key_acc.get(step, 0)
    else:
        alter = key_acc.get(step, 0)

    if note_char.islower():
        octave = 5 + oct_str.count("'")
    else:
        octave = 4 - oct_str.count(",")

    midi = base_midi + int(alter) + 12 * (octave + 1)
    return music21.pitch.Pitch(midi=midi)


def parse_chord_bracket(bracket_str, key_acc):
    """Parse '[CEG]2' -> (list of pitches, duration_str)."""
    m = re.match(r"\[([^\]]+)\]([0-9/]*)", bracket_str)
    if not m:
        # Could be a rest like 'z2'
        dm = re.match(r"z([0-9/]*)", bracket_str)
        dur_str = dm.group(1) if dm else ""
        return [], dur_str

    inner = m.group(1)
    dur_str = m.group(2)
    tokens = re.findall(r"[_^=]*[A-Ga-g][,']*", inner)
    pitches = []
    for tok in tokens:
        p = parse_abc_note(tok, key_acc)
        if p is not None:
            pitches.append(p)
    return pitches, dur_str


def voicing_score(midis, scale_midis):
    """Score a voicing. Higher = better.
    Rewards: wider intervals (3rds, 5ths), good spread.
    Penalizes: clusters, minor 2nds, span > MAX_HAND_SPAN."""
    if len(midis) < 2:
        return 0
    score = 0
    sorted_m = sorted(midis)

    # Interval quality between adjacent notes
    for i in range(len(sorted_m) - 1):
        interval = sorted_m[i + 1] - sorted_m[i]
        span = diatonic_span(sorted_m[i], sorted_m[i + 1], scale_midis)
        if span == 2:  # adjacent strings = minor/major 2nd
            score -= 3
        elif span == 3:  # 3rd
            score += 2
        elif span == 4:  # 4th
            score += 1
        elif span == 5:  # 5th
            score += 2
        elif span >= 6:  # 6th+
            score += 1

    # Check for 3-note clusters (3 notes within 4 diatonic steps)
    for i in range(len(sorted_m) - 2):
        span = diatonic_span(sorted_m[i], sorted_m[i + 2], scale_midis)
        if span <= 4:
            score -= 5

    # Total hand span penalty
    total_span = diatonic_span(sorted_m[0], sorted_m[-1], scale_midis)
    if total_span > MAX_HAND_SPAN:
        score -= (total_span - MAX_HAND_SPAN) * 10  # heavy penalty

    return score


def optimize_hand(midis, melody_midi, scale_midis, midi_to_pitch, is_lh,
                  target_notes=4, max_span=MAX_HAND_SPAN):
    """Optimize a hand's voicing by selecting the best subset/respacing of notes.

    Args:
        midis: current MIDI values for this hand
        melody_midi: the melody note (must not be duplicated in hand)
        scale_midis: all diatonic MIDI values
        midi_to_pitch: dict midi -> music21.pitch.Pitch
        is_lh: True if left hand (prefer lower register)
        target_notes: desired number of notes in this hand
        max_span: max diatonic string span
    Returns:
        list of optimized MIDI values
    """
    if len(midis) <= 1:
        return midis

    sorted_m = sorted(midis)
    span = diatonic_span(sorted_m[0], sorted_m[-1], scale_midis)

    # If already good, just check for clusters
    if span <= max_span and voicing_score(sorted_m, scale_midis) >= 0:
        return sorted_m

    # Strategy 1: If span > max_span, trim notes from the extremes
    # Keep the core and find best subset within span
    best = None
    best_score = -9999

    # Try all possible anchor points (lowest note)
    anchors = [m for m in scale_midis if sorted_m[0] - 5 <= m <= sorted_m[-1]]
    for anchor in anchors:
        # Find all available notes within max_span from anchor
        upper = None
        count = 0
        for sm in scale_midis:
            if sm >= anchor:
                count += 1
                if count == max_span:
                    upper = sm
                    break
        if upper is None:
            continue

        # Select notes from our pool that fit in [anchor, upper]
        candidates = [m for m in sorted_m if anchor <= m <= upper]
        if len(candidates) < 2:
            continue

        # If too many notes, pick best spaced subset
        if len(candidates) > target_notes:
            candidates = _select_spaced_subset(candidates, target_notes, scale_midis)

        # If too few, try adding diatonic fill notes
        if len(candidates) < target_notes:
            candidates = _add_fill_notes(
                candidates, anchor, upper, scale_midis, melody_midi, target_notes
            )

        sc = voicing_score(candidates, scale_midis)
        # Bonus for hitting target note count
        sc += 2 * min(len(candidates), target_notes)
        if sc > best_score:
            best_score = sc
            best = candidates

    if best is None:
        # Fallback: just trim to fit
        best = _trim_to_span(sorted_m, scale_midis, max_span)

    return sorted(best)


def _select_spaced_subset(midis, target, scale_midis):
    """From a sorted list of midis, select `target` notes that are well-spaced."""
    if len(midis) <= target:
        return midis

    # Always keep lowest and highest
    must_keep = {midis[0], midis[-1]}

    # Score all subsets of size `target` that include endpoints
    # For efficiency, use greedy selection based on spacing
    selected = [midis[0]]
    remaining = [m for m in midis[1:-1]]
    remaining_set = list(remaining)

    while len(selected) < target - 1 and remaining_set:
        best_m = None
        best_min_gap = -1
        for m in remaining_set:
            # Minimum gap to any already-selected note
            min_gap = min(abs(m - s) for s in selected)
            if min_gap > best_min_gap:
                best_min_gap = min_gap
                best_m = m
        if best_m is not None:
            selected.append(best_m)
            remaining_set.remove(best_m)
        else:
            break

    selected.append(midis[-1])
    return sorted(selected)[:target]


def _add_fill_notes(midis, lo, hi, scale_midis, melody_midi, target):
    """Add diatonic notes in gaps to reach target count."""
    current = set(midis)
    available = [m for m in scale_midis if lo <= m <= hi
                 and m not in current and m != melody_midi]

    result = list(midis)

    while len(result) < target and available:
        # Score each candidate by how well it fits with current notes
        best_candidate = None
        best_score = -999
        for a in available:
            if a in set(result):
                continue
            # Compute minimum diatonic distance to any existing note
            diat_dists = [diatonic_span(min(a, m), max(a, m), scale_midis) for m in result]
            min_diat = min(diat_dists) if diat_dists else 0

            score = 0
            # Strongly prefer 3rds (3 diatonic steps apart)
            if min_diat == 3:
                score += 5
            elif min_diat == 4:
                score += 3  # 4th
            elif min_diat == 5:
                score += 4  # 5th
            elif min_diat == 6:
                score += 2  # 6th
            elif min_diat == 2:
                score -= 3  # adjacent = bad
            elif min_diat == 1:
                score -= 5  # unison-ish
            elif min_diat >= 7:
                score += 1  # octave+

            # Bonus for being in the middle of the range (fills gaps)
            if result:
                center = (min(result) + max(result)) / 2
                score -= abs(a - center) * 0.01  # slight preference for center

            if score > best_score:
                best_score = score
                best_candidate = a

        if best_candidate is not None:
            result.append(best_candidate)
            available.remove(best_candidate)
        else:
            break

    return sorted(result)


def _trim_to_span(midis, scale_midis, max_span):
    """Trim notes from a sorted list so span <= max_span strings."""
    sorted_m = sorted(midis)
    while len(sorted_m) > 2:
        span = diatonic_span(sorted_m[0], sorted_m[-1], scale_midis)
        if span <= max_span:
            break
        # Remove whichever extreme is farther from center
        center = (sorted_m[0] + sorted_m[-1]) / 2
        if abs(sorted_m[0] - center) >= abs(sorted_m[-1] - center):
            sorted_m = sorted_m[1:]
        else:
            sorted_m = sorted_m[:-1]
    return sorted_m


def compute_annotations(all_midis, rh_midis, lh_midis, ko):
    """Compute chord fraction annotations: abstract roman, RH name, LH name."""
    # Abstract chord (all pitches)
    pcs = []
    seen_pc = set()
    for midi in sorted(all_midis):
        pc = (midi - ko) % 12
        if pc not in seen_pc:
            seen_pc.add(pc)
            pcs.append(pc)
    c_names = [PC_TO_C.get(pc) for pc in pcs]
    abs_ch = ""
    if all(c_names) and len(c_names) >= 3:
        try:
            abs_ch = roman_name(c_names)
        except Exception:
            pass

    # RH voicing name
    rh_letters = []
    for midi in sorted(rh_midis):
        nm = PC_TO_C.get((midi - ko) % 12)
        if nm and nm not in rh_letters:
            rh_letters.append(nm)
    rh_name = ""
    if len(rh_letters) >= 2:
        try:
            rh_name = best_name(rh_letters)
        except Exception:
            pass

    # LH voicing name
    lh_letters = []
    for midi in sorted(lh_midis):
        nm = PC_TO_C.get((midi - ko) % 12)
        if nm and nm not in lh_letters:
            lh_letters.append(nm)
    lh_name = ""
    if len(lh_letters) >= 2:
        try:
            lh_name = best_name(lh_letters)
        except Exception:
            pass

    annotation = ""
    if abs_ch:
        annotation += f'"^{abs_ch}"'
    if rh_name:
        annotation += f'"^{rh_name}"'
    if lh_name:
        annotation += f'"^{lh_name}"'
    return annotation


def process_file(filepath, key_name, scale_midis, midi_to_pitch, key_acc, ko):
    """Process a single harp hymnal ABC file."""
    with open(filepath) as f:
        txt = f.read()

    lines = txt.split("\n")
    header = []
    mel_line = rh_line = lh_line = ""
    for line in lines:
        if line.startswith("[V: M]"):
            mel_line = line
        elif line.startswith("[V: RH]"):
            rh_line = line
        elif line.startswith("[V: LH]"):
            lh_line = line
        else:
            header.append(line)

    if not mel_line or not rh_line or not lh_line:
        return 0, 0  # skip malformed

    # Parse melody into tokens (preserving annotations and barlines)
    mel_prefix = "[V: M] "
    mel_body = mel_line[len(mel_prefix):]

    rh_prefix = "[V: RH] "
    rh_body = rh_line[len(rh_prefix):]

    lh_prefix = "[V: LH] "
    lh_body = lh_line[len(lh_prefix):]

    # Split all three voices by barlines to stay in sync
    mel_bars = re.split(r"(\|]|\|)", mel_body)
    rh_bars = re.split(r"(\|]|\|)", rh_body)
    lh_bars = re.split(r"(\|]|\|)", lh_body)

    # Process each bar
    new_mel_parts = []
    new_rh_parts = []
    new_lh_parts = []

    fixes = 0
    total = 0

    for bar_idx in range(0, len(mel_bars)):
        mel_bar = mel_bars[bar_idx] if bar_idx < len(mel_bars) else ""
        rh_bar = rh_bars[bar_idx] if bar_idx < len(rh_bars) else ""
        lh_bar = lh_bars[bar_idx] if bar_idx < len(lh_bars) else ""

        # Barline separators pass through unchanged
        if mel_bar in ("|", "|]", ""):
            new_mel_parts.append(mel_bar)
            new_rh_parts.append(rh_bar if rh_bar in ("|", "|]", "") else rh_bar)
            new_lh_parts.append(lh_bar if lh_bar in ("|", "|]", "") else lh_bar)
            continue

        # Extract RH/LH chord tokens and melody note tokens
        rh_tokens = re.findall(r"\[[^\]]+\][0-9/]*|z[0-9/]*", rh_bar)
        lh_tokens = re.findall(r"\[[^\]]+\][0-9/]*|z[0-9/]*", lh_bar)
        # Melody tokens: annotations + notes + barlines
        mel_tokens = re.findall(
            r'(?:"[^"]*")*[_^=]*[A-Ga-g][,\']*[0-9/]*\.?|z[0-9/]*\.?|\(|\)',
            mel_bar,
        )
        # Filter to just notes and rests (not slurs)
        mel_note_tokens = [t for t in mel_tokens if re.match(r"[_^=]*[A-Ga-g]|z", t)]

        is_first_note = bar_idx <= 1  # first bar in the piece

        new_rh_tok = []
        new_lh_tok = []
        new_mel_tok_list = list(mel_tokens)  # start with existing
        mel_note_idx = 0
        annotation_replacements = {}  # mel_note_idx -> new annotation

        for note_idx, (rh_tok, lh_tok) in enumerate(
            zip(rh_tokens, lh_tokens)
        ):
            rh_pitches, rh_dur = parse_chord_bracket(rh_tok, key_acc)
            lh_pitches, lh_dur = parse_chord_bracket(lh_tok, key_acc)

            rh_midis = sorted(set(p.midi for p in rh_pitches))
            lh_midis = sorted(set(p.midi for p in lh_pitches))

            # Get melody midi for this beat
            melody_midi = None
            if mel_note_idx < len(mel_note_tokens):
                mp = parse_abc_note(
                    re.sub(r'"[^"]*"', "", mel_note_tokens[mel_note_idx]), key_acc
                )
                if mp:
                    melody_midi = mp.midi

            total += 1
            needs_fix = False
            has_accidentals = False

            # Check for accidentals (non-diatonic notes) in RH/LH
            # Replace with nearest diatonic note — ALWAYS, regardless of needs_fix
            scale_set = set(scale_midis)
            for hand_list in [rh_midis, lh_midis]:
                for idx_h in range(len(hand_list)):
                    if hand_list[idx_h] not in scale_set:
                        m = hand_list[idx_h]
                        candidates = [(abs(sm - m), sm) for sm in scale_midis]
                        candidates.sort()
                        hand_list[idx_h] = candidates[0][1]
                        has_accidentals = True
                        needs_fix = True

            # Deduplicate after accidental replacement
            rh_midis = sorted(set(rh_midis))
            lh_midis = sorted(set(lh_midis))
            all_midis = sorted(set(rh_midis + lh_midis))

            # Check if either hand exceeds span
            if rh_midis and diatonic_span(min(rh_midis), max(rh_midis), scale_midis) > MAX_HAND_SPAN:
                needs_fix = True
            if lh_midis and diatonic_span(min(lh_midis), max(lh_midis), scale_midis) > MAX_HAND_SPAN:
                needs_fix = True

            # Check total note count (target: 6-8, avg 7)
            if len(all_midis) < 6 or len(all_midis) > 9:
                needs_fix = True

            # Check for bad clusters (3 notes within 3 diatonic steps)
            for i in range(len(all_midis) - 2):
                span = diatonic_span(all_midis[i], all_midis[i + 2], scale_midis)
                if span <= 3:
                    needs_fix = True
                    break

            # Always rewrite RH/LH to clean up accidentals and normalize ABC
            always_rewrite = True

            if (needs_fix or has_accidentals) and (rh_midis or lh_midis):
                fixes += 1
                # Pool all available midis
                pool = sorted(set(rh_midis + lh_midis))
                if melody_midi and melody_midi not in pool:
                    pool.append(melody_midi)
                    pool.sort()

                # Target: avg 7 notes per chord (3-4 per hand), max 10-span each
                # Split: LH gets bottom notes, RH gets top notes
                # First, optimize the full pool
                target_total = 7

                # Select well-spaced notes from the pool, adding fills if needed
                lo = min(pool)
                hi = max(pool)

                # Find a good center and work outward
                if melody_midi:
                    # Keep melody pitch out of the hand pools
                    hand_pool = [m for m in pool if m != melody_midi]
                else:
                    hand_pool = list(pool)

                # Optimize: remove adjacent-step notes, prefer wider intervals
                optimized = _optimize_pool(hand_pool, scale_midis, midi_to_pitch,
                                           melody_midi, target_total)

                # Split into LH (lower) and RH (upper)
                optimized.sort()
                n = len(optimized)
                lh_count = (n + 1) // 2
                new_lh = optimized[:lh_count]
                new_rh = optimized[lh_count:]

                # Verify spans and trim if needed, then refill to maintain density
                for _ in range(3):  # iterate to converge
                    if new_rh and diatonic_span(min(new_rh), max(new_rh), scale_midis) > MAX_HAND_SPAN:
                        new_rh = _trim_to_span(new_rh, scale_midis, MAX_HAND_SPAN)
                    if new_lh and diatonic_span(min(new_lh), max(new_lh), scale_midis) > MAX_HAND_SPAN:
                        new_lh = _trim_to_span(new_lh, scale_midis, MAX_HAND_SPAN)

                # Refill hands if too thin (< 3 notes) and span allows
                for hand, is_lh_flag in [(new_rh, False), (new_lh, True)]:
                    if len(hand) < 3 and hand:
                        lo = min(hand)
                        hi = max(hand)
                        # Find span limit
                        count = 0
                        upper = lo
                        for sm in scale_midis:
                            if sm >= lo:
                                count += 1
                                if count == MAX_HAND_SPAN:
                                    upper = sm
                                    break
                        hi_cap = min(hi, upper)
                        filled = _add_fill_notes(
                            hand, lo, hi_cap, scale_midis, melody_midi, 3
                        )
                        if is_lh_flag:
                            new_lh = filled
                        else:
                            new_rh = filled

                rh_midis = new_rh
                lh_midis = new_lh

                # Compute new annotation for first note of each bar
                if note_idx == 0:
                    all_new = sorted(set(rh_midis + lh_midis))
                    if melody_midi:
                        all_new = sorted(set(all_new + [melody_midi]))
                    annotation_replacements[mel_note_idx] = compute_annotations(
                        all_new, rh_midis, lh_midis, ko
                    )

            # Rebuild RH/LH tokens
            dur_str = rh_dur if rh_dur else lh_dur
            if rh_midis:
                rh_abc = (
                    "["
                    + "".join(
                        pitch_to_abc(midi_to_pitch[m], key_acc)
                        for m in sorted(rh_midis)
                        if m in midi_to_pitch
                    )
                    + "]"
                    + dur_str
                )
            else:
                rh_abc = "z" + dur_str
            if lh_midis:
                lh_abc = (
                    "["
                    + "".join(
                        pitch_to_abc(midi_to_pitch[m], key_acc)
                        for m in sorted(lh_midis)
                        if m in midi_to_pitch
                    )
                    + "]"
                    + dur_str
                )
            else:
                lh_abc = "z" + dur_str

            new_rh_tok.append(rh_abc)
            new_lh_tok.append(lh_abc)
            mel_note_idx += 1

        # Rebuild melody with updated annotations
        if annotation_replacements:
            note_count = 0
            rebuilt_mel = []
            for tok in new_mel_tok_list:
                if re.match(r'(?:"[^"]*")*[_^=]*[A-Ga-g]', tok):
                    # Find this token's note index among mel_note_tokens
                    if note_count in annotation_replacements:
                        # Strip old annotations, add new
                        bare = re.sub(r'"[^"]*"', "", tok)
                        tok = annotation_replacements[note_count] + bare
                    note_count += 1
                elif re.match(r"z", tok):
                    note_count += 1
                rebuilt_mel.append(tok)
            new_mel_tok_list = rebuilt_mel

        new_mel_parts.append(" ".join(new_mel_tok_list))
        new_rh_parts.append(" ".join(new_rh_tok) if new_rh_tok else rh_bar)
        new_lh_parts.append(" ".join(new_lh_tok) if new_lh_tok else lh_bar)

    # Reassemble
    new_mel = mel_prefix + "".join(new_mel_parts)
    new_rh = rh_prefix + "".join(new_rh_parts)
    new_lh = lh_prefix + "".join(new_lh_parts)

    output = "\n".join(header) + "\n"
    output = output.rstrip("\n") + "\n"
    # Find where voice lines were and replace
    new_lines = []
    for line in output.split("\n"):
        if not line.startswith("[V:"):
            new_lines.append(line)
    output = "\n".join(new_lines)
    if not output.endswith("\n"):
        output += "\n"
    # Final cleanup: strip all accidentals from RH/LH lines
    # (these voices must be purely diatonic)
    new_rh = re.sub(r'[\^_=](?=[A-Ga-g])', '', new_rh)
    new_lh = re.sub(r'[\^_=](?=[A-Ga-g])', '', new_lh)

    output += new_mel + "\n" + new_rh + "\n" + new_lh + "\n"

    with open(filepath, "w") as f:
        f.write(output)

    return fixes, total


def _optimize_pool(pool, scale_midis, midi_to_pitch, melody_midi, target):
    """Select well-spaced notes from pool, targeting wider intervals."""
    if len(pool) <= target:
        # May need to add notes
        return _respaced_pool(pool, scale_midis, midi_to_pitch, melody_midi, target)

    # Too many notes: select best-spaced subset
    return _select_spaced_subset(pool, target, scale_midis)


def _respaced_pool(pool, scale_midis, midi_to_pitch, melody_midi, target):
    """Given a pool of notes, respace and fill to target count with wide intervals."""
    if not pool:
        return pool

    # Only remove adjacent-step notes if we have MORE than target
    # This prevents over-thinning
    cleaned = list(pool)
    if len(cleaned) > target:
        changed = True
        while changed and len(cleaned) > target:
            changed = False
            sorted_c = sorted(cleaned)
            # Find the worst adjacent pair (smallest gap to neighbors)
            worst_idx = None
            worst_score = 999
            for i in range(len(sorted_c) - 1):
                if diatonic_span(sorted_c[i], sorted_c[i + 1], scale_midis) == 2:
                    # Score: prefer removing notes with other close neighbors
                    if i == 0:
                        score = 0
                    elif i + 1 == len(sorted_c) - 1:
                        score = 1
                    else:
                        score = 2
                    if score < worst_score:
                        worst_score = score
                        worst_idx = i
            if worst_idx is not None:
                sorted_c_list = sorted(cleaned)
                i = worst_idx
                if i == 0:
                    cleaned.remove(sorted_c_list[i])
                elif i + 1 == len(sorted_c_list) - 1:
                    cleaned.remove(sorted_c_list[i + 1])
                else:
                    gap_left = sorted_c_list[i] - sorted_c_list[i - 1] if i > 0 else 999
                    gap_right = (
                        sorted_c_list[i + 2] - sorted_c_list[i + 1]
                        if i + 2 < len(sorted_c_list)
                        else 999
                    )
                    if gap_left <= gap_right:
                        cleaned.remove(sorted_c_list[i])
                    else:
                        cleaned.remove(sorted_c_list[i + 1])
                changed = True

    # Now add fill notes if needed
    if len(cleaned) < target:
        lo = min(cleaned)
        hi = max(cleaned)
        # Expand range slightly if needed
        lo_expanded = max(lo - 12, 36)  # don't go below C2
        hi_expanded = min(hi + 12, 84)  # don't go above C6
        cleaned = _add_fill_notes(
            cleaned, lo_expanded, hi_expanded, scale_midis, melody_midi, target
        )

    return sorted(cleaned)


# ── Main ──
def main():
    total_fixes = 0
    total_chords = 0
    files_processed = 0

    for fname in sorted(os.listdir(HARP_DIR)):
        if not fname.endswith(".abc"):
            continue

        filepath = os.path.join(HARP_DIR, fname)
        with open(filepath) as f:
            txt = f.read()

        key = "C"
        for line in txt.split("\n"):
            if line.startswith("K:"):
                key = line[2:].strip().split()[0]

        key_acc = get_key_accidentals(key)
        scale_midis = get_scale_midis(key)
        midi_to_pitch = get_scale_pitches(key)
        ko = KEY_PC.get(key, 0)

        fixes, chords = process_file(filepath, key, scale_midis, midi_to_pitch, key_acc, ko)
        total_fixes += fixes
        total_chords += chords
        files_processed += 1

        if files_processed % 50 == 0:
            print(f"  Processed {files_processed}...", file=sys.stderr)

    print(
        f"Done: {files_processed} files, {total_chords} chords, {total_fixes} fixed",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
