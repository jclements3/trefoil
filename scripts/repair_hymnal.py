#!/usr/bin/env python3
"""Auto-repair melody-chord clashes in harp hymnal ABC files.

For each chord where a RH/LH note is a minor 2nd or major 7th from the melody:
1. Remove the clashing note
2. If the hand drops below 3 notes, add the best non-clashing diatonic note
   within 10-string span

Reads/writes: handout/harp_hymnal/*.abc
Then rebuilds: app/hymnal_data.json

Usage:
  python3 repair_hymnal.py          # repair and rebuild
  python3 repair_hymnal.py --dry    # report only, don't write
"""

import os
import re
import sys
import glob
import json
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
HARP_DIR = os.path.join(PROJECT_DIR, "handout/harp_hymnal")
JSON_PATH = os.path.join(PROJECT_DIR, "app/hymnal_data.json")
ASSETS_PATH = os.path.join(PROJECT_DIR, "app/app/src/main/assets/hymnal_data.json")

NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
NOTE_NAMES = ["C", "D", "E", "F", "G", "A", "B"]

KEY_SIGS = {
    "C": {}, "G": {"F": 1}, "D": {"F": 1, "C": 1}, "A": {"F": 1, "C": 1, "G": 1},
    "E": {"F": 1, "C": 1, "G": 1, "D": 1},
    "F": {"B": -1}, "Bb": {"B": -1, "E": -1}, "Eb": {"B": -1, "E": -1, "A": -1},
    "Ab": {"B": -1, "E": -1, "A": -1, "D": -1},
}

MAX_SPAN = 10
MIN_NOTES = 3


def get_diatonic_pcs(key):
    ks = KEY_SIGS.get(key, {})
    return set((NOTE_BASE[n] + ks.get(n, 0)) % 12 for n in NOTE_BASE)


def get_diatonic_midis(key, lo=24, hi=96):
    dpcs = get_diatonic_pcs(key)
    return sorted(m for m in range(lo, hi + 1) if m % 12 in dpcs)


def diatonic_span(midis, scale=None, key=None):
    """Count diatonic strings spanned (inclusive). Matches validate_hymnal.py."""
    if len(midis) < 2:
        return len(midis)
    lo, hi = min(midis), max(midis)
    if scale is not None:
        return sum(1 for m in scale if lo <= m <= hi)
    # Fallback: compute from key
    ks = KEY_SIGS.get(key, {})
    dpcs = set((NOTE_BASE[n] + ks.get(n, 0)) % 12 for n in NOTE_BASE)
    return sum(1 for m in range(lo, hi + 1) if m % 12 in dpcs)


def midi_to_abc(midi, key):
    """Convert MIDI number to ABC note string (diatonic, no accidentals).
    Uses same octave convention as abc_note_to_midi: uppercase=octave 4, lowercase=octave 5."""
    ks = KEY_SIGS.get(key, {})
    pc = midi % 12
    name = None
    for n in NOTE_NAMES:
        if (NOTE_BASE[n] + ks.get(n, 0)) % 12 == pc:
            name = n
            break
    if name is None:
        return None

    # Base MIDI for this note at uppercase (octave 4)
    base_upper = NOTE_BASE[name] + ks.get(name, 0) + 12 * 4
    diff = midi - base_upper

    if diff < 0:
        commas = (-diff + 11) // 12
        return name + "," * commas
    elif diff < 12:
        return name
    elif diff < 24:
        ticks = (diff - 12) // 12
        return name.lower() + "'" * ticks if ticks else name.lower()
    else:
        ticks = (diff - 12) // 12
        return name.lower() + "'" * ticks


def abc_note_to_midi(s, ks):
    acc = None
    i = 0
    while i < len(s) and s[i] in "^_=":
        if s[i] == "^": acc = (acc or 0) + 1
        elif s[i] == "_": acc = (acc or 0) - 1
        elif s[i] == "=": acc = 0
        i += 1
    if i >= len(s) or s[i].upper() not in NOTE_BASE:
        return None
    name = s[i].upper()
    octave = 5 if s[i].islower() else 4
    i += 1
    while i < len(s):
        if s[i] == "'": octave += 1
        elif s[i] == ",": octave -= 1
        else: break
        i += 1
    if acc is None:
        acc = ks.get(name, 0)
    return NOTE_BASE[name] + acc + 12 * octave


def parse_chord_tokens(chord_str):
    """Parse a chord into list of (token_str, midi) pairs."""
    inner = chord_str.strip("[]")
    inner = re.sub(r"[\d/]+$", "", inner)
    tokens = []
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
        tokens.append(inner[start:i])
    return tokens


def parse_melody_midis(mel_line, ks):
    music = re.sub(r'"[^"]*"', '', mel_line)
    music = re.sub(r'^\[V: M\]\s*', '', music)
    music = re.sub(r'\[Q:[^\]]*\]', '', music)
    midis = []
    for m in re.finditer(r'(z)|([\^_=]*[A-Ga-g][,\']*)', music):
        if m.group(1):
            midis.append(None)
        else:
            midis.append(abc_note_to_midi(m.group(2), ks))
    return midis


def clashes_with_melody(midi, mel_midi):
    if mel_midi is None:
        return False
    return abs(midi - mel_midi) % 12 in (1, 11)


def find_replacement(remaining_midis, mel_midi, scale, key, max_span=MAX_SPAN):
    """Find the best diatonic note to add that doesn't clash with melody,
    stays within max_span, and fills out the chord nicely (prefer 3rds/5ths)."""
    if not remaining_midis:
        return None
    lo, hi = min(remaining_midis), max(remaining_midis)
    # Candidate range: within a few strings of existing chord
    candidates = []
    for m in scale:
        if m in remaining_midis:
            continue
        if clashes_with_melody(m, mel_midi):
            continue
        test = sorted(remaining_midis + [m])
        if diatonic_span(test, scale) > max_span:
            continue
        # Score: prefer notes that form consonant intervals with existing notes
        score = 0
        for existing in remaining_midis:
            iv = abs(m - existing) % 12
            if iv in (3, 4): score += 3   # 3rd
            elif iv in (7, 5): score += 3  # 5th/4th
            elif iv == 0: score += 1       # octave doubling (ok but not ideal)
            elif iv in (8, 9): score += 2  # 6th
            elif iv in (1, 11): score -= 5  # avoid semitones within chord
            elif iv in (2, 10): score -= 1  # whole tone
        # Strongly prefer notes near the chord's range (same register)
        mid = (lo + hi) / 2
        dist = abs(m - mid)
        score -= dist * 0.5  # heavy penalty for distant notes
        candidates.append((score, m))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def repair_voice_line(voice_line, mel_midis, key, hand_name):
    """Repair a single voice line. Returns (new_line, n_removed, n_added)."""
    ks = KEY_SIGS.get(key, {})
    scale = get_diatonic_midis(key)

    # Split line into prefix and music
    prefix_match = re.match(r'(\[V: [A-Z]+\]\s*)', voice_line)
    if not prefix_match:
        return voice_line, 0, 0
    prefix = prefix_match.group(1)
    music = voice_line[len(prefix):]

    # Find all chord positions in the music string
    chord_re = re.compile(r"\[[A-Ga-g,'^_= ]+\]")
    n_removed = 0
    n_added = 0
    chord_idx = 0

    def replace_chord(match):
        nonlocal chord_idx, n_removed, n_added
        chord_str = match.group(0)
        mel_midi = mel_midis[chord_idx] if chord_idx < len(mel_midis) else None
        chord_idx += 1

        tokens = parse_chord_tokens(chord_str)
        midis = [abc_note_to_midi(t, ks) for t in tokens]
        pairs = list(zip(tokens, midis))

        # Find clashing notes
        clashers = set()
        for tok, midi in pairs:
            if midi is not None and mel_midi is not None:
                if clashes_with_melody(midi, mel_midi):
                    clashers.add(tok)

        if not clashers:
            return chord_str

        # Remove clashers
        kept = [(tok, midi) for tok, midi in pairs if tok not in clashers]
        n_removed += len(clashers)

        remaining_midis = [midi for _, midi in kept if midi is not None]

        # Add replacement if below minimum
        while len(remaining_midis) < MIN_NOTES:
            replacement = find_replacement(remaining_midis, mel_midi, scale, key)
            if replacement is None:
                break
            abc_note = midi_to_abc(replacement, key)
            if abc_note is None:
                break
            # Round-trip check: verify the ABC note parses back correctly
            rt_midi = abc_note_to_midi(abc_note, ks)
            if rt_midi != replacement:
                # Bad conversion — skip this replacement
                break
            # Verify span after adding
            test_midis = sorted(remaining_midis + [rt_midi])
            if diatonic_span(test_midis, scale) > MAX_SPAN:
                break
            kept.append((abc_note, rt_midi))
            remaining_midis.append(rt_midi)
            n_added += 1

        # Sort by MIDI (low to high) for consistent ordering
        kept.sort(key=lambda x: x[1] if x[1] is not None else 0)

        # Reconstruct chord string, preserving duration suffix
        duration = re.search(r'\]([\d/]*)', chord_str)
        dur_str = duration.group(1) if duration else ""
        inner = "".join(tok for tok, _ in kept)
        return f"[{inner}]{dur_str}"

    new_music = chord_re.sub(replace_chord, music)
    return prefix + new_music, n_removed, n_added


def repair_abc_file(filepath, dry=False):
    """Repair a single ABC file. Returns (title, n_removed, n_added)."""
    with open(filepath) as f:
        content = f.read()

    # Extract key
    key = "C"
    km = re.search(r"^K:\s*(\S+)", content, re.MULTILINE)
    if km:
        key = km.group(1).strip()

    # Extract title
    tm = re.search(r"^T:\s*(.+)", content, re.MULTILINE)
    title = tm.group(1).strip() if tm else os.path.basename(filepath)

    ks = KEY_SIGS.get(key, {})

    # Find voice lines
    lines = content.split("\n")
    mel_line = ""
    rh_idx = lh_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("[V: M]"):
            mel_line = line
        elif line.startswith("[V: RH]"):
            rh_idx = i
        elif line.startswith("[V: LH]"):
            lh_idx = i

    if not mel_line or rh_idx < 0 or lh_idx < 0:
        return title, 0, 0

    mel_midis = parse_melody_midis(mel_line, ks)

    total_removed = 0
    total_added = 0

    # Repair RH
    new_rh, rem, add = repair_voice_line(lines[rh_idx], mel_midis, key, "RH")
    lines[rh_idx] = new_rh
    total_removed += rem
    total_added += add

    # Repair LH
    new_lh, rem, add = repair_voice_line(lines[lh_idx], mel_midis, key, "LH")
    lines[lh_idx] = new_lh
    total_removed += rem
    total_added += add

    if not dry and total_removed > 0:
        with open(filepath, "w") as f:
            f.write("\n".join(lines))

    return title, total_removed, total_added


def rebuild_json():
    """Rebuild hymnal_data.json from harp_hymnal/*.abc files."""
    abc_files = sorted(glob.glob(os.path.join(HARP_DIR, "*.abc")))

    # Load existing JSON to preserve chords metadata
    old_data = {}
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            for h in json.load(f):
                old_data[h["t"]] = h

    output = []
    for abc_file in abc_files:
        with open(abc_file) as f:
            content = f.read().strip()

        tm = re.search(r"^T:\s*(.+)", content, re.MULTILINE)
        title = tm.group(1).strip() if tm else os.path.basename(abc_file)

        km = re.search(r"^K:\s*(\S+)", content, re.MULTILINE)
        key = km.group(1).strip() if km else "C"

        num_m = re.match(r"(\d+)_", os.path.basename(abc_file))
        xnum = int(num_m.group(1)) if num_m else 0
        n = str(3000 + xnum)

        # Rewrite with strip chart formatting
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("X:"):
                new_lines.append(f"X: {n}")
            elif line.startswith("%%staves"):
                new_lines.append("%%pagewidth 200cm")
                new_lines.append("%%continueall 1")
                new_lines.append("%%leftmargin 0.5cm")
                new_lines.append("%%rightmargin 0.5cm")
                new_lines.append("%%topspace 0")
                new_lines.append("%%musicspace 0")
                new_lines.append("%%writefields Q 0")
                new_lines.append(line)
            else:
                new_lines.append(line)

        abc = "\n".join(new_lines)

        # Strip any remaining accidentals from RH/LH (belt and suspenders)
        acc_re = re.compile(r"[\^_=](?=[A-Ga-g])")
        abc_lines = abc.split("\n")
        final_lines = []
        for l in abc_lines:
            if l.startswith("[V: RH]") or l.startswith("[V: LH]"):
                final_lines.append(acc_re.sub("", l))
            else:
                final_lines.append(l)
        abc = "\n".join(final_lines)

        entry = {"n": n, "t": title, "abc": abc, "key": key}
        old = old_data.get(title)
        if old and "chords" in old:
            entry["chords"] = old["chords"]

        output.append(entry)

    output.sort(key=lambda x: int(x["n"]))

    with open(JSON_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    # Copy to assets
    if os.path.exists(os.path.dirname(ASSETS_PATH)):
        with open(ASSETS_PATH, "w") as f:
            json.dump(output, f, separators=(",", ":"))

    return len(output)


def main():
    dry = "--dry" in sys.argv

    abc_files = sorted(glob.glob(os.path.join(HARP_DIR, "*.abc")))
    print(f"{'DRY RUN: ' if dry else ''}Repairing {len(abc_files)} hymns...\n")

    total_removed = 0
    total_added = 0
    hymns_fixed = 0
    note_counts_before = Counter()
    note_counts_after = Counter()

    for fp in abc_files:
        title, removed, added = repair_abc_file(fp, dry=dry)
        if removed > 0:
            hymns_fixed += 1
            print(f"  {title}: removed {removed}, added {added}")
        total_removed += removed
        total_added += added

    print(f"\n{'=' * 60}")
    print(f"Hymns repaired: {hymns_fixed}/{len(abc_files)}")
    print(f"Notes removed (clashing): {total_removed}")
    print(f"Notes added (replacements): {total_added}")
    print(f"Net change: {total_added - total_removed:+d}")

    if not dry:
        print(f"\nRebuilding hymnal_data.json...")
        n = rebuild_json()
        print(f"Written {n} hymns to {JSON_PATH}")
        print(f"Copied to {ASSETS_PATH}")
        print(f"\nRun validate_hymnal.py --json to verify.")
    else:
        print(f"\nDry run — no files modified. Remove --dry to apply.")


if __name__ == "__main__":
    main()
