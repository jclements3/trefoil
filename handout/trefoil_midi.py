import sys, mido
sys.path.insert(0, '/home/claude')
from lh_trefoil import (all_voicings_for_root, all_voicings_above,
    score_voicing, score_rh_voicing, ROOT_MAP, TREFOIL, ALL_PATTERNS)

SCALE = ['C','D','E','F','G','A','B']
TRANS_EB = {'C':'E','D':'F','E':'G','F':'A','G':'B','A':'C','B':'D'}
TRAVERSAL = ['CCW4','CCW3','CCW2','CW2','CW3','CW4']
NOTE_BASE = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def note_midi(letter, octave):
    return (octave+1)*12 + NOTE_BASE[letter]

def build_results():
    lh_used=[]; rh_used=[]; lh_prev=None; rh_prev=None; results=[]
    for seg_name, roots in TREFOIL:
        for root in roots:
            root_idx = ROOT_MAP[root]
            lh_voicings = all_voicings_for_root(root_idx)
            lh_best = max(lh_voicings, key=lambda v: score_voicing(v, lh_prev, lh_used, ALL_PATTERNS))
            lh_used.append(lh_best['pattern'])
            lh_prev = lh_best['strings']
            lh_top = lh_best['strings'][-1]
            rh_voicings = all_voicings_above(lh_top, root_idx, lh_best['pattern'])
            if not rh_voicings:
                rh_voicings = all_voicings_above(lh_top, root_idx, None)
            rh_best = max(rh_voicings, key=lambda v: score_rh_voicing(v, rh_prev, rh_used))
            rh_used.append(rh_best['pattern'])
            rh_prev = rh_best['strings']
            results.append({'seg': seg_name,
                            'lh_notes': lh_best['notes'],
                            'rh_notes': rh_best['notes']})
    return results

def assign_octaves(notes, base_octave=3):
    octaves=[]; octave=base_octave; prev_idx=-1
    for note in notes:
        idx = SCALE.index(note)
        if prev_idx != -1 and idx <= prev_idx:
            octave += 1
        octaves.append((note, octave))
        prev_idx = idx
    return octaves

def chord_midi_notes(lh_notes, rh_notes, trans=None):
    lh = [trans[n] for n in lh_notes] if trans else list(lh_notes)
    rh = [trans[n] for n in rh_notes] if trans else list(rh_notes)
    lh_oct = assign_octaves(lh, base_octave=3)
    last_lh_note, last_lh_oct = lh_oct[-1]
    first_rh_idx = SCALE.index(rh[0])
    last_lh_idx  = SCALE.index(last_lh_note)
    rh_base = last_lh_oct if first_rh_idx > last_lh_idx else last_lh_oct + 1
    rh_oct = assign_octaves(rh, base_octave=rh_base)
    return [note_midi(n, o) for n, o in lh_oct + rh_oct]

def make_midi(results, trans, filename, tempo_bpm=60):
    mid = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo_bpm), time=0))
    track.append(mido.Message('program_change', program=46, time=0))  # harp

    beat       = 480   # ticks per quarter note
    strum_gap  = 24    # ticks between each strum note (~30ms at 60bpm)
    seg_pause  = 240   # half-beat pause between segments

    prev_seg = None
    pending_offs = []  # list of (time_remaining, pitch)

    abs_tick = 0  # track absolute time for scheduling

    events = []  # (abs_tick, type, pitch, velocity)

    for seg in TRAVERSAL:
        if prev_seg is not None:
            abs_tick += seg_pause  # gap between segments
        prev_seg = seg

        for row in [r for r in results if r['seg'] == seg]:
            notes = chord_midi_notes(row['lh_notes'], row['rh_notes'], trans)
            n = len(notes)

            # Strum on: ascending, strum_gap apart
            for i, pitch in enumerate(notes):
                events.append((abs_tick + i * strum_gap, 'on', pitch, 80))

            # All note-offs at end of beat
            note_off_tick = abs_tick + beat
            for pitch in notes:
                events.append((note_off_tick, 'off', pitch, 0))

            abs_tick += beat

    # Sort events by time, note_offs before note_ons at same tick
    events.sort(key=lambda e: (e[0], 0 if e[1]=='off' else 1))

    # Convert to delta times
    prev_tick = 0
    for tick, etype, pitch, vel in events:
        delta = tick - prev_tick
        if etype == 'on':
            track.append(mido.Message('note_on',  note=pitch, velocity=vel, time=delta))
        else:
            track.append(mido.Message('note_off', note=pitch, velocity=0,   time=delta))
        prev_tick = tick

    mid.save(filename)
    print(f"Saved: {filename}")

results = build_results()
make_midi(results, TRANS_EB, '/mnt/user-data/outputs/trefoil_eb_strum.mid')
make_midi(results, None,     '/mnt/user-data/outputs/trefoil_c_strum.mid')
