#!/usr/bin/env python3.10
"""Build a SATB chord-index sidecar for the Tchaikovsky pipeline.

Parses data/OpenHymnal.abc per-voice via music21, walks every unique
note onset across SATB, identifies the sounding chord (root, bass,
quality, 7th, inversion) and emits app/satb_chord_index.json keyed by
hymn number.

The Tch MEI builder then aligns lead_sheet chord annotations to these
SATB events by root-matching in traversal order, and uses the resulting
inversion info to pick the correct handout-table row for each chord.
"""
import json
import re
import sys
from pathlib import Path

from music21 import converter, pitch as m21pitch, chord as m21chord

ROOT = Path(__file__).resolve().parent.parent
OPENHYMNAL = ROOT / 'data' / 'OpenHymnal.abc'
LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
OUTPUT = ROOT / 'app' / 'satb_chord_index.json'

# Ionian scale degrees in semitones from tonic
IONIAN = [0, 2, 4, 5, 7, 9, 11]

# 8 lever-harp keys → tonic pitch class
KEY_PC = {'C': 0, 'G': 7, 'D': 2, 'A': 9, 'E': 4, 'F': 5, 'Bb': 10, 'Eb': 3}


def load_openhymnal_by_title(src_text):
    """Parse OpenHymnal.abc into {title: raw_hymn_abc}."""
    hymns = {}
    # Match lines starting with X: <number> + trailing body up to next X: or EOF.
    # Use a lookahead \nX: anchored at line start.
    for m in re.finditer(r'(?:\A|\n)(X:\s*\d+\s*\nT:[^\n]+.*?)(?=\nX:\s*\d|\Z)', src_text, re.DOTALL):
        block = m.group(1)
        tm = re.search(r'\nT:\s*([^\n]+)', '\n' + block)
        if tm:
            hymns[tm.group(1).strip()] = block
    return hymns


def split_voices(hymn_abc):
    """Parse the hymn's multi-voice ABC into per-voice music21 streams.

    OpenHymnal uses %%combinevoices 1 which defeats music21's automatic
    voice split, so we strip the directive and extract per-voice bodies
    by scanning [V:VID] prefixed lines.
    """
    lines = hymn_abc.split('\n')
    header, body, past_K = [], [], False
    for ln in lines:
        if ln.startswith(('X:', 'T:', 'M:', 'L:', 'Q:')):
            header.append(ln)
        elif ln.startswith('K:'):
            header.append(ln)
            past_K = True
        elif past_K and not ln.startswith('%%combinevoices'):
            body.append(ln)

    voices = sorted(set(re.findall(r'\[V:\s*([^\]]+)\]', '\n'.join(body))))
    parts = {}
    for v in voices:
        v_lines = []
        for ln in body:
            s = ln.strip()
            if re.match(rf'^\[V:\s*{re.escape(v)}\s*\]', s):
                content = re.sub(r'^\[V:\s*[^\]]+\]\s*', '', s)
                if content.startswith('w:'):
                    continue
                v_lines.append(content)
        if not v_lines:
            continue
        full_abc = '\n'.join(header + v_lines)
        try:
            parts[v] = converter.parse(full_abc, format='abc')
        except Exception:
            parts[v] = None
    return parts, voices


def detect_chord(sounding_pitches):
    """Identify chord quality/inv from a set of sounding music21 Pitch objects.

    Returns dict {root_pc, bass_pc, quality, seventh, inv} or None.
    """
    if len(sounding_pitches) < 3:
        return None
    pcs = set(int(p.ps) % 12 for p in sounding_pitches)
    bass_ps = min(p.ps for p in sounding_pitches)
    bass_pc = int(bass_ps) % 12

    try:
        ch = m21chord.Chord(sounding_pitches)
        root_pc = ch.root().pitchClass
    except Exception:
        return None

    # Quality from intervals above root
    third_m = (root_pc + 3) % 12 in pcs
    third_M = (root_pc + 4) % 12 in pcs
    fifth_P = (root_pc + 7) % 12 in pcs
    fifth_d = (root_pc + 6) % 12 in pcs
    fifth_A = (root_pc + 8) % 12 in pcs

    if third_M and fifth_P:
        quality = 'major'
    elif third_m and fifth_P:
        quality = 'minor'
    elif third_m and fifth_d:
        quality = 'diminished'
    elif third_M and fifth_A:
        quality = 'augmented'
    elif third_M:
        quality = 'major'
    elif third_m:
        quality = 'minor'
    else:
        quality = 'major'

    # Seventh interval from root
    seventh = None
    if (root_pc + 10) % 12 in pcs:
        seventh = 'min'  # dom7 / m7
    elif (root_pc + 11) % 12 in pcs:
        seventh = 'maj'  # Δ7

    # Inversion from bass interval
    bass_interval = (bass_pc - root_pc) % 12
    if bass_interval == 0:
        inv = 0
    elif bass_interval in (3, 4):
        inv = 1  # 3rd in bass
    elif bass_interval in (6, 7, 8):
        inv = 2  # 5th in bass
    elif bass_interval in (10, 11) and seventh:
        inv = 3  # 7th in bass
    else:
        inv = 0

    return {
        'root': root_pc,
        'bass': bass_pc,
        'quality': quality,
        'seventh': seventh,
        'inv': inv,
    }


def analyze_hymn(hymn_abc, lead_key):
    """Return list of chord events for the hymn, pitches transposed to lead_key."""
    key_pc = KEY_PC.get(lead_key)
    if key_pc is None:
        return None

    parts, v_ids = split_voices(hymn_abc)
    if len(parts) < 3:
        return None
    if any(parts[v] is None for v in v_ids):
        return None

    # Detect original SATB key and compute transposition offset
    try:
        orig_key = parts[v_ids[0]].analyze('key')
        orig_key_pc = orig_key.tonic.pitchClass
    except Exception:
        orig_key_pc = key_pc
    transpose_off = (key_pc - orig_key_pc) % 12
    if transpose_off > 6:
        transpose_off -= 12

    # Collect (offset, voice_idx, transposed_Pitch) for every SATB note event
    all_notes = []
    for vi, v in enumerate(v_ids):
        for n in parts[v].flatten().notes:
            for p in n.pitches:
                tp = m21pitch.Pitch(ps=p.ps + transpose_off)
                all_notes.append((float(n.offset), vi, tp))
    if not all_notes:
        return None

    # Index notes by voice for fast sounding-at lookup
    by_voice = {vi: sorted([(n[0], n[2]) for n in all_notes if n[1] == vi])
                for vi in range(len(v_ids))}

    def sounding_at(beat):
        out = []
        for vi, vn in by_voice.items():
            # Most recent note ≤ beat
            lo, hi = 0, len(vn) - 1
            best = None
            while lo <= hi:
                mid = (lo + hi) // 2
                if vn[mid][0] <= beat:
                    best = vn[mid][1]
                    lo = mid + 1
                else:
                    hi = mid - 1
            if best is not None:
                out.append(best)
        return out

    # Unique onset beats
    beats = sorted(set(n[0] for n in all_notes))

    events = []
    prev_sig = None
    for bt in beats:
        sounding = sounding_at(bt)
        info = detect_chord(sounding)
        if info is None:
            continue
        sig = (info['root'], info['bass'], info['quality'], info['seventh'])
        if sig == prev_sig:
            continue
        prev_sig = sig

        # Chord degree in lead key
        deg_interval = (info['root'] - key_pc) % 12
        try:
            info['deg'] = IONIAN.index(deg_interval) + 1
        except ValueError:
            info['deg'] = None
        info['beat'] = round(bt, 4)
        events.append(info)
    return events


def main():
    print('Loading OpenHymnal...', flush=True)
    src = OPENHYMNAL.read_text()
    openhymnal = load_openhymnal_by_title(src)
    print(f'  {len(openhymnal)} hymns indexed', flush=True)

    print('Loading lead_sheets.json...', flush=True)
    lead = json.loads(LEAD_SHEETS.read_text())
    print(f'  {len(lead)} lead sheets', flush=True)

    results = {}
    failed = 0
    for i, ls_entry in enumerate(lead):
        t = ls_entry['t'].strip()
        hymn_abc = openhymnal.get(t)
        if not hymn_abc:
            failed += 1
            continue
        try:
            events = analyze_hymn(hymn_abc, ls_entry['key'])
        except Exception as e:
            print(f"  FAIL {ls_entry['n']} {t}: {type(e).__name__}: {e}", flush=True)
            failed += 1
            continue
        if events is None:
            failed += 1
            continue
        results[str(ls_entry['n'])] = events
        if (i + 1) % 25 == 0:
            print(f'  {i+1}/{len(lead)} processed', flush=True)

    print(f'\nWriting {len(results)} hymns to {OUTPUT} ({failed} failed)', flush=True)
    OUTPUT.write_text(json.dumps(results))
    print(f'Done. {OUTPUT.stat().st_size/1024:.0f} KB', flush=True)


if __name__ == '__main__':
    main()
