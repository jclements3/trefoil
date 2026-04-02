#!/usr/bin/env python3
"""Convert harp leadsheets to trefoil stripchart format.

Reads ../harp/data/harp_leadsheets.abc, maps Roman numeral chords to trefoil
voicing table entries, outputs ABC + chord fraction data for the stripchart app.
"""

import json
import re
import sys
from pathlib import Path

# ── Trefoil voicing table (Roman numeral, key-independent) ──

TREFOIL_TABLE = json.loads(Path(__file__).parent.parent.joinpath(
    'trefoil/trefoil_voicings.json').read_text())

# Build lookup: root → list of (lhName, lhNotes_pattern, gap, rhName, rhNotes_pattern, section)
# Notes patterns are relative to C major; we transpose at runtime
VOICINGS_BY_ROOT = {}
C_SCALE = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

for section, rows in TREFOIL_TABLE['sections'].items():
    for row in rows:
        root = row['root']
        if root not in VOICINGS_BY_ROOT:
            VOICINGS_BY_ROOT[root] = []
        VOICINGS_BY_ROOT[root].append({
            'lh': row['lh'],
            'rh': row['rh'],
            'lhPat': row['lhPat'],
            'rhPat': row['rhPat'],
            'gap': row['gap'],
            'section': section,
        })

# ── Roman numeral parsing ──

def parse_roman(sym):
    """Parse a Roman numeral chord symbol to (root_degree, quality_info).
    Returns the diatonic degree 1-7 (or 0 if unparseable).
    Maps chromatic alterations to nearest diatonic root.
    """
    s = sym.strip('"')

    # Handle chromatic prefixes
    chromatic = 0
    if s.startswith('b'):
        chromatic = -1
        s = s[1:]
    elif s.startswith('#'):
        chromatic = 1
        s = s[1:]

    # Extract Roman numeral root
    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
        'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
    }

    # Try longest match first
    for numeral in ['VII', 'VII', 'III', 'vii', 'iii', 'IV', 'VI', 'II',
                    'iv', 'vi', 'ii', 'V', 'I', 'v', 'i']:
        if s.startswith(numeral):
            degree = roman_map[numeral]
            is_minor = numeral[0].islower()
            rest = s[len(numeral):]
            return degree, is_minor, rest, chromatic

    return 0, False, s, 0

def degree_to_trefoil_root(degree):
    """Map degree (1-7) to trefoil table root symbol."""
    return {1: 'I', 2: 'ii', 3: 'iii', 4: 'IV', 5: 'V', 6: 'vi', 7: 'vii'}.get(degree, 'I')

# ── Key transposition ──

NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

KEY_OFFSETS = {
    'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6,
    'Db': 0, 'Eb': 2, 'F#': 3, 'Gb': 3, 'Ab': 5, 'Bb': 6,
}

def transpose_note_name(note, key):
    """Transpose a note name from C major to the given key.
    E.g., transpose_note_name('E', 'G') -> 'B' (3rd degree of G)
    """
    offset = KEY_OFFSETS.get(key, 0)
    idx = NOTE_NAMES.index(note)
    return NOTE_NAMES[(idx + offset) % 7]

def transpose_notes(notes_str, key):
    """Transpose a string of note names like 'ACE' from C to the given key."""
    return ''.join(transpose_note_name(n, key) for n in notes_str)

# ── ABC parsing ──

def parse_leadsheet(abc_text):
    """Parse a single leadsheet ABC into melody notes and chord symbols per beat."""
    lines = abc_text.strip().split('\n')
    title = ''
    key = 'C'
    meter = '4/4'
    tempo = 120
    unit_len = 0.25  # L:1/4

    music_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith('T:'):
            title = line[2:].strip()
        elif line.startswith('K:'):
            key = line[2:].strip().split()[0]
            # Remove minor mode suffix
            if key.endswith('m'):
                key = key[:-1]
        elif line.startswith('M:'):
            meter = line[2:].strip()
        elif line.startswith('L:'):
            parts = line[2:].strip().split('/')
            if len(parts) == 2:
                unit_len = float(parts[0]) / float(parts[1])
        elif line.startswith('Q:') or line.startswith('[Q:'):
            m = re.search(r'=(\d+)', line)
            if m:
                tempo = int(m.group(1))
        elif not line.startswith('%') and not line.startswith('X:'):
            music_lines.append(line)

    music = ' '.join(music_lines)

    # Extract chord symbols and melody notes
    # Chords are in "..." before notes
    beats = []
    current_chord = None
    beat_idx = 0

    # Tokenize: chords and notes
    i = 0
    while i < len(music):
        ch = music[i]

        if ch == '"':
            # Chord symbol
            j = music.index('"', i + 1)
            current_chord = music[i+1:j]
            i = j + 1
        elif ch == '[' and music[i:i+3] == '[Q:':
            # Inline tempo
            j = music.index(']', i)
            m = re.search(r'=(\d+)', music[i:j])
            if m:
                tempo = int(m.group(1))
            i = j + 1
        elif ch == '|' or ch == ']' or ch == '[' or ch == ':':
            i += 1
        elif ch == 'z' or ch == 'Z':
            # Rest
            i += 1
            dur_str = ''
            while i < len(music) and (music[i].isdigit() or music[i] == '/'):
                dur_str += music[i]
                i += 1
            dur = parse_duration(dur_str) * unit_len * 4
            beats.append({'chord': current_chord, 'note': None, 'dur': dur, 'idx': beat_idx})
            beat_idx += 1
        elif ch.isalpha() and ch not in 'xXwWhH':
            # Note
            note_str = ''
            dur_str = ''
            # Accidentals before
            while i < len(music) and music[i] in '^_=':
                i += 1
            if i < len(music) and music[i].isalpha():
                note_str = music[i]
                i += 1
                while i < len(music) and music[i] in ",'":
                    i += 1
                while i < len(music) and (music[i].isdigit() or music[i] == '/'):
                    dur_str += music[i]
                    i += 1
            dur = parse_duration(dur_str) * unit_len * 4
            beats.append({'chord': current_chord, 'note': note_str.upper(), 'dur': dur, 'idx': beat_idx})
            beat_idx += 1
        elif ch == ' ' or ch == '\n' or ch == '\t':
            i += 1
        else:
            i += 1

    return {
        'title': title,
        'key': key,
        'meter': meter,
        'tempo': tempo,
        'beats': beats,
    }

def parse_duration(s):
    if not s:
        return 1.0
    if s.startswith('/'):
        den = float(s[1:]) if len(s) > 1 else 2.0
        return 1.0 / den
    if '/' in s:
        parts = s.split('/')
        return float(parts[0]) / float(parts[1])
    return float(s)

# ── Voicing selection ──

def select_voicing(root_degree, melody_note, key, prev_voicing=None):
    """Select a trefoil voicing for the given root and melody note.

    Picks a voicing where the RH pattern can accommodate the melody note
    on the thumb (highest RH note). Prefers variety from prev_voicing.
    """
    trefoil_root = degree_to_trefoil_root(root_degree)
    voicings = VOICINGS_BY_ROOT.get(trefoil_root, [])

    if not voicings:
        # Fallback: use I
        voicings = VOICINGS_BY_ROOT.get('I', [])
        trefoil_root = 'I'

    # For now, pick based on variety: rotate through available voicings
    # In a real implementation, we'd match melody note to RH top note

    # Simple selection: pick voicing that's different from previous
    if prev_voicing and len(voicings) > 1:
        for v in voicings:
            if v['lh'] != prev_voicing['lh'] or v['rh'] != prev_voicing['rh']:
                return v

    return voicings[0] if voicings else None

# ── Generate chord fractions per measure ──

def generate_chord_fractions(hymn, key):
    """From parsed hymn beats, generate one chord fraction per measure."""
    beats = hymn['beats']
    if not beats:
        return []

    fractions = []
    current_beat_time = 0
    measure_beats = 4  # assume 4/4
    if hymn['meter'] == '3/4':
        measure_beats = 3
    elif hymn['meter'] == '6/8':
        measure_beats = 6

    # Group by measure and pick one chord per measure
    measure_start = 0
    note_idx = 0
    prev_voicing = None
    prev_chord = None

    for beat in beats:
        chord_sym = beat['chord']

        # Only emit a fraction at chord changes
        if chord_sym and chord_sym != prev_chord:
            degree, is_minor, rest, chromatic = parse_roman(chord_sym)
            if degree > 0:
                voicing = select_voicing(degree, beat.get('note'), key, prev_voicing)
                if voicing:
                    # Transpose terse name: replace Roman root with letter
                    scale_degrees = {
                        1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6
                    }
                    root_idx = scale_degrees.get(degree, 0)
                    root_note = NOTE_NAMES[(root_idx + KEY_OFFSETS.get(key, 0)) % 7]

                    # Build display terse name from the voicing's lh+rh combined
                    # For now use the voicing's terse name transposed
                    lh_name = voicing['lh']
                    rh_name = voicing['rh']

                    # The LH chord name IS the terse name for the left hand voicing
                    # Transpose Roman to letter: replace I/ii/iii/IV/V/vi/vii with note
                    terse = transpose_terse_name(lh_name, rh_name, key, degree)

                    fractions.append({
                        'beat': beat['idx'],
                        'name': terse,
                        'rh': rh_name,  # Will be properly transposed
                        'lh': lh_name,  # Will be properly transposed
                    })
                    prev_voicing = voicing
            prev_chord = chord_sym
        note_idx += 1

    return fractions

def transpose_terse_name(lh_name, rh_name, key, degree):
    """Convert a Roman numeral terse name to a letter-based terse name.
    E.g., in key G, degree 5 (V), lh='V²' → 'D²'
    """
    scale_degrees = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
    root_idx = scale_degrees.get(degree, 0)
    root_note = NOTE_NAMES[(root_idx + KEY_OFFSETS.get(key, 0)) % 7]

    # The terse name from the table uses Roman roots
    # Replace the Roman root prefix with the letter root
    # Handle: I, ii, iii, IV, V, vi, vii
    roman_roots = ['vii', 'iii', 'VII', 'III', 'vi', 'ii', 'VI', 'II', 'IV', 'iv', 'V', 'v', 'I', 'i']

    combined = lh_name  # Use LH as the representative terse name
    for rom in roman_roots:
        if combined.startswith(rom):
            suffix = combined[len(rom):]
            # Determine if we need lowercase for minor
            if rom[0].islower():
                return root_note + 'm' + suffix if 'm' not in suffix else root_note + suffix
            else:
                return root_note + suffix

    return root_note

# ── Main: process all hymns ──

def main():
    leadsheet_path = Path(__file__).parent.parent.parent / 'harp/data/harp_leadsheets.abc'
    text = leadsheet_path.read_text()

    # Split into individual tunes
    tunes = text.split('\nX:')
    hymns = []

    for i, chunk in enumerate(tunes):
        if i == 0:
            if 'X:' not in chunk:
                continue
            chunk = chunk[chunk.index('X:'):]
        else:
            chunk = 'X:' + chunk

        hymn = parse_leadsheet(chunk)
        if hymn['title'] and hymn['beats']:
            # Generate stripped melody ABC (no chord annotations)
            melody_abc = generate_melody_abc(chunk, hymn)
            fractions = generate_chord_fractions(hymn, hymn['key'])

            hymns.append({
                'title': hymn['title'],
                'key': hymn['key'],
                'tempo': hymn['tempo'],
                'abc': melody_abc,
                'chords': fractions,
            })

    print(f"Processed {len(hymns)} hymns", file=sys.stderr)

    # Output as JSON for embedding in the app
    json.dump(hymns[:5], sys.stdout, indent=2)  # First 5 for testing

def generate_melody_abc(raw_abc, hymn):
    """Generate clean melody-only ABC with stripchart formatting."""
    lines = raw_abc.strip().split('\n')
    out = []
    out.append(f'X: {3000 + len(out)}')
    out.append(f'T: {hymn["title"]}')
    out.append(f'M: {hymn["meter"]}')
    out.append('L: 1/4')
    out.append('%%pagewidth 200cm')
    out.append('%%continueall 1')
    out.append('%%leftmargin 0.5cm')
    out.append('%%rightmargin 0.5cm')
    out.append('%%topspace 0')
    out.append('%%musicspace 0')
    out.append('%%writefields Q 0')
    out.append(f'K: {hymn["key"]}')

    # Extract music lines and strip chord annotations
    for line in lines:
        line = line.strip()
        if line.startswith(('X:', 'T:', 'M:', 'L:', 'K:', 'Q:', '%', 'C:', 'V:')):
            continue
        if line.startswith('%%'):
            continue
        # Strip "chord" annotations
        clean = re.sub(r'"[^"]*"', '', line)
        # Keep [Q:...] but make it hidden
        if clean.strip():
            out.append(clean)

    return '\n'.join(out)

if __name__ == '__main__':
    main()
