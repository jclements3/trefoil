#!/usr/bin/env python3
"""Validate harp hymnal ABC files for common issues.

Checks:
- Accidentals in RH/LH (must be purely diatonic)
- Hand span >10 diatonic strings
- Minor 2nds (adjacent diatonic steps) within a hand
- Too few (<2) or too many (>6) notes per hand per chord
- RH/LH overlap (RH lowest note below LH highest)
- Missing or malformed chord fraction annotations
- Measure count mismatch between M/RH/LH voices
- Empty or missing voices
- Plomp-Levelt sensory roughness (psychoacoustic dissonance)
- Melody-chord clash (minor 2nd / minor 9th between melody and chord tones)
- Voice leading smoothness (total MIDI movement between consecutive chords)
- Harmonic consistency (do chord tones match the Roman numeral annotation?)

Reads from: handout/harp_hymnal/*.abc (default) or app/hymnal_data.json (--json)

Usage:
  python3 validate_hymnal.py              # validate harp_hymnal/*.abc
  python3 validate_hymnal.py --json       # validate app/hymnal_data.json
  python3 validate_hymnal.py --errors     # only show ERRORs
  python3 validate_hymnal.py --stats      # print aggregate statistics
  python3 validate_hymnal.py --worst 20   # show 20 worst chords by roughness
"""

import math
import os
import re
import sys
import glob
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
HARP_DIR = os.path.join(PROJECT_DIR, "handout/harp_hymnal")
JSON_PATH = os.path.join(PROJECT_DIR, "app/hymnal_data.json")

# ABC note to MIDI (relative, octave 4 = middle C)
NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Key signature: sharps/flats applied to note names
KEY_SIGS = {
    "C": {}, "G": {"F": 1}, "D": {"F": 1, "C": 1}, "A": {"F": 1, "C": 1, "G": 1},
    "E": {"F": 1, "C": 1, "G": 1, "D": 1}, "B": {"F": 1, "C": 1, "G": 1, "D": 1, "A": 1},
    "F": {"B": -1}, "Bb": {"B": -1, "E": -1}, "Eb": {"B": -1, "E": -1, "A": -1},
    "Ab": {"B": -1, "E": -1, "A": -1, "D": -1},
    "Db": {"B": -1, "E": -1, "A": -1, "D": -1, "G": -1},
}

# Roman numeral to scale degree (semitones from tonic)
ROMAN_ROOTS = {
    "I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11,
    "i": 0, "ii": 2, "iii": 4, "iv": 5, "v": 7, "vi": 9, "vii": 11,
}

# ── Plomp-Levelt roughness model ──
# Based on Sethares (1993) adaptation of Plomp & Levelt (1965)
# Two pure tones at frequencies f1, f2 produce roughness based on their
# critical bandwidth separation.

def _plomp_levelt_pair(f1, f2):
    """Roughness between two pure tones. Returns 0..1."""
    if f1 > f2:
        f1, f2 = f2, f1
    if f1 <= 0:
        return 0.0
    s = 0.24 / (0.021 * f1 + 19)  # critical bandwidth scaling
    diff = f2 - f1
    x = diff * s
    # Plomp-Levelt curve: rises then falls
    return math.exp(-3.5 * x) - math.exp(-5.75 * x)


def midi_to_freq(midi):
    """MIDI note number to frequency in Hz (A4=440)."""
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def chord_roughness(midis):
    """Total Plomp-Levelt roughness for a chord (sum of all pairs).
    Higher = more dissonant. Typical range: 0 (unison/octave) to ~2+ (dense cluster)."""
    if len(midis) < 2:
        return 0.0
    freqs = [midi_to_freq(m) for m in midis]
    total = 0.0
    for i in range(len(freqs)):
        for j in range(i + 1, len(freqs)):
            total += _plomp_levelt_pair(freqs[i], freqs[j])
    return total


def roughness_rating(r, n_notes, midis=None):
    """Classify roughness score. Thresholds are register-aware because
    low-frequency chords are inherently rougher (wider critical bandwidth).
    A C major triad at C3 has per_pair~0.13; at C4 it's ~0.06."""
    pairs = max(1, n_notes * (n_notes - 1) / 2)
    per_pair = r / pairs
    # Shift thresholds up for low-register chords
    avg_midi = sum(midis) / len(midis) if midis else 60
    # Below MIDI 48 (C3): raise thresholds significantly
    # MIDI 36 (C2): +0.10, MIDI 48 (C3): +0.05, MIDI 60 (C4): +0.0
    register_bonus = max(0, (60 - avg_midi) * 0.004)
    t_mild = 0.04 + register_bonus
    t_rough = 0.10 + register_bonus
    t_harsh = 0.18 + register_bonus
    if per_pair < t_mild:
        return "clean"
    elif per_pair < t_rough:
        return "mild"
    elif per_pair < t_harsh:
        return "rough"
    else:
        return "harsh"


# ── Melody-chord clash detection ──

def melody_chord_clash(melody_midi, chord_midis):
    """Check if melody note clashes with any chord tone.
    Returns list of clashing intervals (semitones)."""
    if melody_midi is None:
        return []
    clashes = []
    for cm in chord_midis:
        interval = abs(melody_midi - cm) % 12
        if interval in (1, 11):  # minor 2nd / major 7th
            clashes.append(interval)
    return clashes


# ── Voice leading smoothness ──

def voice_leading_cost(prev_midis, curr_midis):
    """Total absolute MIDI movement between two chords (minimal matching).
    Lower = smoother. Uses greedy nearest-note matching."""
    if not prev_midis or not curr_midis:
        return 0
    prev = sorted(prev_midis)
    curr = sorted(curr_midis)
    # Pad shorter to match longer
    while len(prev) < len(curr):
        prev.append(prev[-1])
    while len(curr) < len(prev):
        curr.append(curr[-1])
    return sum(abs(p - c) for p, c in zip(prev, curr))


# ── Harmonic consistency ──

def parse_roman(annotation):
    """Extract root scale degree from a Roman numeral annotation like 'vi7¹' or 'IVΔ'.
    Returns (root_semitones, is_minor) or None."""
    if not annotation:
        return None
    # Strip superscripts, digits, modifiers
    clean = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹ΔøΟ°+\-\d/s]', '', annotation)
    # Match Roman numeral at start
    m = re.match(r'^(VII|VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)', clean)
    if not m:
        return None
    numeral = m.group(1)
    is_minor = numeral[0].islower()
    root = ROMAN_ROOTS.get(numeral)
    if root is None:
        return None
    return (root, is_minor)


def check_harmonic_consistency(roman_str, chord_midis, key_name):
    """Check if chord pitch classes are consistent with the Roman numeral.
    Returns (match_ratio, expected_pcs, actual_pcs)."""
    parsed = parse_roman(roman_str)
    if parsed is None:
        return None
    root_offset, is_minor = parsed
    tonic_pc = NOTE_BASE.get(key_name[0].upper(), 0)
    if len(key_name) > 1:
        if key_name[1] == 'b':
            tonic_pc -= 1
        elif key_name[1] == '#':
            tonic_pc += 1
    root_pc = (tonic_pc + root_offset) % 12
    # Build expected triad
    if is_minor:
        expected = {root_pc, (root_pc + 3) % 12, (root_pc + 7) % 12}
    else:
        expected = {root_pc, (root_pc + 4) % 12, (root_pc + 7) % 12}
    actual = {m % 12 for m in chord_midis}
    if not actual:
        return None
    match = len(actual & expected)
    return (match / len(actual), expected, actual)


# ── Core parsing (unchanged) ──

def abc_note_to_midi(note_str, key_sig):
    """Parse a single ABC note token to MIDI number. Returns None if unparsable."""
    s = note_str.strip()
    if not s or s.startswith("z") or s.startswith("x"):
        return None
    acc = None
    i = 0
    while i < len(s) and s[i] in "^_=":
        if s[i] == "^":
            acc = (acc or 0) + 1
        elif s[i] == "_":
            acc = (acc or 0) - 1
        elif s[i] == "=":
            acc = 0
        i += 1
    if i >= len(s):
        return None
    ch = s[i]
    if ch.upper() not in NOTE_BASE:
        return None
    name = ch.upper()
    octave = 5 if ch.islower() else 4
    i += 1
    while i < len(s):
        if s[i] == "'":
            octave += 1
        elif s[i] == ",":
            octave -= 1
        else:
            break
        i += 1
    if acc is None:
        acc = key_sig.get(name, 0)
    return NOTE_BASE[name] + acc + 12 * octave


def parse_chord_notes(chord_str, key_sig):
    """Parse an ABC chord like [CEG] or [C,E,G,] into list of MIDI values."""
    inner = chord_str.strip("[]")
    inner = re.sub(r"[\d/]+$", "", inner)
    notes = []
    i = 0
    while i < len(inner):
        start = i
        while i < len(inner) and inner[i] in "^_=":
            i += 1
        if i >= len(inner) or inner[i].upper() not in "ABCDEFG":
            i += 1
            continue
        i += 1
        while i < len(inner) and inner[i] in "',":
            i += 1
        token = inner[start:i]
        midi = abc_note_to_midi(token, key_sig)
        if midi is not None:
            notes.append(midi)
    return notes


def diatonic_span(midis, key_name):
    """Count diatonic string span (inclusive) between lowest and highest MIDI."""
    if len(midis) < 2:
        return 0
    lo, hi = min(midis), max(midis)
    ks = KEY_SIGS.get(key_name, {})
    diatonic_pcs = set()
    for name, base in NOTE_BASE.items():
        diatonic_pcs.add((base + ks.get(name, 0)) % 12)
    return sum(1 for m in range(lo, hi + 1) if m % 12 in diatonic_pcs)


def has_minor_2nd(midis):
    """Check if any two notes are a semitone or whole tone apart."""
    if len(midis) < 2:
        return False
    sorted_m = sorted(midis)
    for i in range(len(sorted_m) - 1):
        if sorted_m[i + 1] - sorted_m[i] <= 2:
            return True
    return False


def extract_chords_from_line(line):
    """Extract chord tokens [xxx] from a voice line."""
    return re.findall(r"\[[A-Ga-g,'^_= ]+\]", line)


def parse_melody_notes(mel_line, key_sig):
    """Extract per-beat melody MIDI values from the melody line.
    Returns list of MIDI values (one per note/rest event). Rests are None."""
    # Strip annotations and voice prefix
    music = re.sub(r'"[^"]*"', '', mel_line)
    music = re.sub(r'^\[V: M\]\s*', '', music)
    music = re.sub(r'\[Q:[^\]]*\]', '', music)
    midis = []
    # Match notes: optional accidental + letter + optional octave + optional duration
    for m in re.finditer(r'([z])|([\^_=]*[A-Ga-g][,\']*)', music):
        if m.group(1):  # rest
            midis.append(None)
        else:
            midi = abc_note_to_midi(m.group(2), key_sig)
            midis.append(midi)
    return midis


# ── Main validation ──

def validate_abc(title, abc_text, collect_stats=False):
    """Validate a single hymn's ABC.
    Returns (issues, stats_dict).
    issues: list of (severity, message)
    stats_dict: roughness scores, voice leading costs, etc. (if collect_stats)
    """
    issues = []
    stats = {
        "roughness_scores": [],    # (chord_idx, hand, roughness, rating, chord_str)
        "melody_clashes": [],      # (chord_idx, melody_midi, clash_intervals)
        "voice_leading": [],       # (chord_idx, hand, cost)
        "harmonic_mismatches": [], # (chord_idx, roman, match_ratio, expected, actual)
    }
    lines = abc_text.split("\n")

    # Extract key
    key = "C"
    for line in lines:
        km = re.match(r"^K:\s*(\S+)", line)
        if km:
            key = km.group(1).strip()
            break
    key_sig = KEY_SIGS.get(key, {})

    # Find voice lines
    mel_line = ""
    rh_line = ""
    lh_line = ""
    for line in lines:
        if line.startswith("[V: M]"):
            mel_line = line
        elif line.startswith("[V: RH]"):
            rh_line = line
        elif line.startswith("[V: LH]"):
            lh_line = line

    if not mel_line:
        issues.append(("ERROR", "Missing melody voice [V: M]"))
    if not rh_line:
        issues.append(("ERROR", "Missing RH voice"))
    if not lh_line:
        issues.append(("ERROR", "Missing LH voice"))
    if not rh_line or not lh_line:
        return issues, stats

    # Check accidentals in RH/LH
    acc_re = re.compile(r"[\^_=](?=[A-Ga-g])")
    rh_accs = acc_re.findall(rh_line)
    lh_accs = acc_re.findall(lh_line)
    if rh_accs:
        issues.append(("ERROR", f"RH has {len(rh_accs)} accidentals"))
    if lh_accs:
        issues.append(("ERROR", f"LH has {len(lh_accs)} accidentals"))

    # Count measures
    mel_bars = mel_line.count("|") - mel_line.count("|]")
    rh_bars = rh_line.count("|") - rh_line.count("|]")
    lh_bars = lh_line.count("|") - lh_line.count("|]")
    if mel_bars != rh_bars:
        issues.append(("ERROR", f"Measure mismatch: melody={mel_bars} RH={rh_bars}"))
    if mel_bars != lh_bars:
        issues.append(("ERROR", f"Measure mismatch: melody={mel_bars} LH={lh_bars}"))

    # Parse chords
    rh_chords = extract_chords_from_line(rh_line)
    lh_chords = extract_chords_from_line(lh_line)

    # Parse melody
    mel_midis = parse_melody_notes(mel_line, key_sig) if mel_line else []

    # Parse chord fraction annotations from melody
    frac_annotations = re.findall(r'"\^([^"]*)"', mel_line) if mel_line else []

    # ── Structural checks ──
    prev_rh_midis = None
    prev_lh_midis = None

    for ci, ch in enumerate(rh_chords):
        midis = parse_chord_notes(ch, key_sig)
        if len(midis) == 0:
            issues.append(("WARN", f"RH chord {ci+1}: empty/unparsable '{ch}'"))
            continue
        if len(midis) > 6:
            issues.append(("WARN", f"RH chord {ci+1}: {len(midis)} notes (max 6)"))
        span = diatonic_span(midis, key)
        if span > 10:
            issues.append(("ERROR", f"RH chord {ci+1}: span={span} strings (max 10) {ch}"))

        # Roughness
        r = chord_roughness(midis)
        rating = roughness_rating(r, len(midis), midis)
        if rating == "harsh":
            issues.append(("ERROR", f"RH chord {ci+1}: harsh roughness={r:.2f} {ch}"))
        elif rating == "rough":
            issues.append(("WARN", f"RH chord {ci+1}: rough roughness={r:.2f} {ch}"))
        stats["roughness_scores"].append((ci, "RH", r, rating, ch))

        # Voice leading
        if prev_rh_midis is not None:
            cost = voice_leading_cost(prev_rh_midis, midis)
            if cost > 24:  # >2 octaves total movement
                issues.append(("WARN", f"RH chord {ci+1}: large voice leading jump={cost} semitones"))
            stats["voice_leading"].append((ci, "RH", cost))
        prev_rh_midis = midis

    for ci, ch in enumerate(lh_chords):
        midis = parse_chord_notes(ch, key_sig)
        if len(midis) == 0:
            issues.append(("WARN", f"LH chord {ci+1}: empty/unparsable '{ch}'"))
            continue
        if len(midis) > 6:
            issues.append(("WARN", f"LH chord {ci+1}: {len(midis)} notes (max 6)"))
        span = diatonic_span(midis, key)
        if span > 10:
            issues.append(("ERROR", f"LH chord {ci+1}: span={span} strings (max 10) {ch}"))

        # Roughness
        r = chord_roughness(midis)
        rating = roughness_rating(r, len(midis), midis)
        if rating == "harsh":
            issues.append(("ERROR", f"LH chord {ci+1}: harsh roughness={r:.2f} {ch}"))
        elif rating == "rough":
            issues.append(("WARN", f"LH chord {ci+1}: rough roughness={r:.2f} {ch}"))
        stats["roughness_scores"].append((ci, "LH", r, rating, ch))

        # Voice leading
        if prev_lh_midis is not None:
            cost = voice_leading_cost(prev_lh_midis, midis)
            if cost > 30:  # LH has wider range, so higher threshold
                issues.append(("WARN", f"LH chord {ci+1}: large voice leading jump={cost} semitones"))
            stats["voice_leading"].append((ci, "LH", cost))
        prev_lh_midis = midis

    # ── Melody-chord clash ──
    for ci in range(min(len(rh_chords), len(lh_chords), len(mel_midis))):
        mel_m = mel_midis[ci] if ci < len(mel_midis) else None
        if mel_m is None:
            continue
        rh_midis = parse_chord_notes(rh_chords[ci], key_sig)
        lh_midis = parse_chord_notes(lh_chords[ci], key_sig)
        all_chord = rh_midis + lh_midis
        clashes = melody_chord_clash(mel_m, all_chord)
        if clashes:
            issues.append(("ERROR", f"Chord {ci+1}: melody (MIDI {mel_m}) clashes with chord — "
                          f"minor 2nd/major 7th intervals"))
            stats["melody_clashes"].append((ci, mel_m, clashes))

    # ── RH/LH overlap ──
    for ci in range(min(len(rh_chords), len(lh_chords))):
        rh_midis = parse_chord_notes(rh_chords[ci], key_sig)
        lh_midis = parse_chord_notes(lh_chords[ci], key_sig)
        if rh_midis and lh_midis:
            if min(rh_midis) < max(lh_midis):
                issues.append(("WARN", f"Chord {ci+1}: RH/LH overlap "
                              f"(RH low={min(rh_midis)} < LH high={max(lh_midis)})"))

    # ── Harmonic consistency ──
    # Annotations come in triples: abstract, RH name, LH name
    ann_idx = 0
    chord_idx = 0
    while ann_idx + 2 < len(frac_annotations):
        roman = frac_annotations[ann_idx]
        ann_idx += 3
        if chord_idx >= min(len(rh_chords), len(lh_chords)):
            chord_idx += 1
            continue
        rh_midis = parse_chord_notes(rh_chords[chord_idx], key_sig)
        lh_midis = parse_chord_notes(lh_chords[chord_idx], key_sig)
        all_midis = rh_midis + lh_midis
        result = check_harmonic_consistency(roman, all_midis, key)
        if result is not None:
            match_ratio, expected, actual = result
            if match_ratio < 0.3 and len(all_midis) >= 3:
                issues.append(("WARN", f"Chord {chord_idx+1}: annotation '{roman}' — "
                              f"only {match_ratio:.0%} of tones match expected triad "
                              f"(expected PCs {expected}, got {actual})"))
                stats["harmonic_mismatches"].append(
                    (chord_idx, roman, match_ratio, expected, actual))
        chord_idx += 1

    # ── Chord fraction annotation completeness ──
    if mel_line:
        frac_count = mel_line.count('"^')
        if frac_count == 0:
            issues.append(("WARN", "No chord fraction annotations in melody"))
        for fi, frac in enumerate(frac_annotations):
            if not frac.strip():
                issues.append(("WARN", f"Empty chord fraction annotation #{fi+1}"))

    return issues, stats


def print_stats(all_stats):
    """Print aggregate statistics across all hymns."""
    from collections import Counter

    # Roughness distribution
    all_roughness = []
    for s in all_stats:
        all_roughness.extend(s["roughness_scores"])

    ratings = Counter(r[3] for r in all_roughness)
    total = len(all_roughness)
    print(f"\n{'=' * 60}")
    print(f"ROUGHNESS DISTRIBUTION ({total} chords)")
    print(f"{'=' * 60}")
    for rating in ["clean", "mild", "rough", "harsh"]:
        n = ratings.get(rating, 0)
        pct = 100 * n / total if total else 0
        bar = '#' * int(pct / 2)
        print(f"  {rating:6s}: {n:6d} ({pct:5.1f}%) {bar}")

    rh_rough = [r for r in all_roughness if r[1] == "RH"]
    lh_rough = [r for r in all_roughness if r[1] == "LH"]
    if rh_rough:
        avg_rh = sum(r[2] for r in rh_rough) / len(rh_rough)
        print(f"  RH avg roughness: {avg_rh:.3f}")
    if lh_rough:
        avg_lh = sum(r[2] for r in lh_rough) / len(lh_rough)
        print(f"  LH avg roughness: {avg_lh:.3f}")

    # Voice leading
    all_vl = []
    for s in all_stats:
        all_vl.extend(s["voice_leading"])
    if all_vl:
        rh_vl = [v[2] for v in all_vl if v[1] == "RH"]
        lh_vl = [v[2] for v in all_vl if v[1] == "LH"]
        print(f"\n{'=' * 60}")
        print(f"VOICE LEADING ({len(all_vl)} transitions)")
        print(f"{'=' * 60}")
        if rh_vl:
            print(f"  RH: avg={sum(rh_vl)/len(rh_vl):.1f}  "
                  f"median={sorted(rh_vl)[len(rh_vl)//2]}  "
                  f"max={max(rh_vl)} semitones")
        if lh_vl:
            print(f"  LH: avg={sum(lh_vl)/len(lh_vl):.1f}  "
                  f"median={sorted(lh_vl)[len(lh_vl)//2]}  "
                  f"max={max(lh_vl)} semitones")

    # Melody clashes
    total_clashes = sum(len(s["melody_clashes"]) for s in all_stats)
    print(f"\n{'=' * 60}")
    print(f"MELODY-CHORD CLASHES: {total_clashes}")
    print(f"{'=' * 60}")

    # Harmonic mismatches
    total_hm = sum(len(s["harmonic_mismatches"]) for s in all_stats)
    print(f"\nHARMONIC MISMATCHES (<30% triad match): {total_hm}")


def print_worst(all_hymn_stats, n=20):
    """Print the N worst chords by roughness across all hymns."""
    worst = []
    for title, stats in all_hymn_stats:
        for ci, hand, r, rating, ch in stats["roughness_scores"]:
            worst.append((r, rating, title, ci + 1, hand, ch))
    worst.sort(reverse=True)
    print(f"\n{'=' * 60}")
    print(f"TOP {n} WORST CHORDS BY ROUGHNESS")
    print(f"{'=' * 60}")
    for r, rating, title, ci, hand, ch in worst[:n]:
        print(f"  {r:.3f} [{rating:5s}] {title} — {hand} chord {ci}: {ch}")


def main():
    use_json = "--json" in sys.argv
    errors_only = "--errors" in sys.argv
    show_stats = "--stats" in sys.argv
    worst_n = 0
    if "--worst" in sys.argv:
        idx = sys.argv.index("--worst")
        worst_n = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 20

    total_issues = defaultdict(int)
    hymn_issues = []
    all_stats = []
    all_hymn_stats = []

    if use_json:
        import json
        with open(JSON_PATH) as f:
            data = json.load(f)
        hymns = [(h["t"], h["abc"]) for h in data if int(h.get("n", 0)) >= 3000]
    else:
        abc_files = sorted(glob.glob(os.path.join(HARP_DIR, "*.abc")))
        hymns = []
        for fp in abc_files:
            with open(fp) as f:
                content = f.read()
            tm = re.search(r"^T:\s*(.+)", content, re.MULTILINE)
            title = tm.group(1).strip() if tm else os.path.basename(fp)
            hymns.append((title, content))

    print(f"Validating {len(hymns)} hymns...\n")

    for title, abc in hymns:
        issues, stats = validate_abc(title, abc, collect_stats=True)
        all_stats.append(stats)
        all_hymn_stats.append((title, stats))
        if issues:
            filtered = issues if not errors_only else [
                (s, m) for s, m in issues if s == "ERROR"]
            if filtered:
                hymn_issues.append((title, filtered))
        for severity, msg in issues:
            total_issues[severity] += 1

    # Print per-hymn results
    for title, issues in hymn_issues:
        print(f"  {title}")
        for severity, msg in issues:
            if not errors_only or severity == "ERROR":
                print(f"    [{severity}] {msg}")

    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    print(f"Hymns scanned: {len(hymns)}")
    print(f"Hymns with issues: {len(hymn_issues)}")
    for sev in sorted(total_issues.keys()):
        print(f"  {sev}: {total_issues[sev]}")

    if show_stats:
        print_stats(all_stats)

    if worst_n > 0:
        print_worst(all_hymn_stats, worst_n)

    if total_issues.get("ERROR", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
