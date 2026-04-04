#!/usr/bin/env python3
"""Convert SSAATTBB abc files to harp hymnal format:
   Melody (S1) on top with chord fraction annotations,
   RH and LH as chord brackets, split by register (LH=bottom, RH=top).
   Uses music21 to parse voices."""

import os, re, sys, glob, json, warnings
warnings.filterwarnings('ignore')
import music21

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'handout'))
from chord_name import best_name, roman_name

IN_DIR = os.path.join(os.path.dirname(__file__), '..', 'handout/ssaattbb_out')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'handout/harp_hymnal')
ABC2SVG_REL = '../../abc2stripchart/app/src/main/assets/abc2svg/abc2svg-1.js'
os.makedirs(OUT_DIR, exist_ok=True)

KEY_PC = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
          'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6,'Cb':11,'C#':1}
PC_TO_C = {0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A', 11:'B'}
SCALE = ['C','D','E','F','G','A','B']

def extract_voices(abc_text):
    lines = abc_text.split('\n')
    header = []; voices = {}; cv = None
    for line in lines:
        ls = line.strip()
        if not ls: continue
        vm = re.match(r'\[V:(\d+)\]\s*(.*)', ls)
        if vm:
            cv = vm.group(1); m = vm.group(2).strip()
            if cv not in voices: voices[cv] = []
            if m: voices[cv].append(m)
            continue
        if cv and not ls.startswith(('X:','T:','C:','M:','L:','K:','Q:','V:','%%')):
            voices[cv].append(ls); continue
        if ls.startswith(('X:','T:','M:','L:','K:','Q:')):
            header.append(ls); cv = None
        elif ls.startswith('C:') and any(h.startswith('T:') for h in header):
            header.append(ls)
    return header, voices

def get_val(header, prefix, default=''):
    for h in header:
        if h.startswith(prefix):
            return h[len(prefix):].split('%')[0].strip()
    return default

def get_key_accidentals(key_name):
    try:
        k = music21.key.Key(key_name)
        return {p.step: p.accidental.alter for p in k.alteredPitches}
    except:
        return {}

def pitch_to_abc(p, key_acc):
    name = p.step
    octave = p.octave if p.octave else 4
    acc = ''
    if p.accidental:
        a = p.accidental.alter
        ka = key_acc.get(name, 0)
        if a != ka:
            if a == 1: acc = '^'
            elif a == -1: acc = '_'
            elif a == 2: acc = '^^'
            elif a == -2: acc = '__'
            elif a == 0: acc = '='
    if octave >= 5:
        return acc + name.lower() + "'" * (octave - 5)
    elif octave == 4:
        return acc + name
    else:
        return acc + name + "," * (4 - octave)

def dur_to_abc(ql):
    if ql == 1.0: return ''
    if ql == 2.0: return '2'
    if ql == 3.0: return '3'
    if ql == 4.0: return '4'
    if ql == 0.5: return '/'
    if ql == 0.25: return '//'
    if ql == 1.5: return '3/2'
    if ql == 0.75: return '3/4'
    if ql == 6.0: return '6'
    # General fraction
    from fractions import Fraction
    f = Fraction(ql).limit_denominator(16)
    if f.denominator == 1:
        return str(f.numerator)
    return f'{f.numerator}/{f.denominator}'

def process_file(filepath, outpath):
    with open(filepath) as f:
        abc = f.read()

    if '[V:8]' not in abc and 'V:8' not in abc:
        return False

    header, voices = extract_voices(abc)
    if len(voices) < 8:
        return False

    key = get_val(header, 'K:', 'C').split()[0]
    meter = get_val(header, 'M:', '4/4')
    length = get_val(header, 'L:', '1/4')
    title = get_val(header, 'T:', 'Hymn')
    tempo = get_val(header, 'Q:', '1/4=100')
    ko = KEY_PC.get(key, 0)
    key_acc = get_key_accidentals(key)

    base_header = ['X: 1', f'M: {meter}', f'L: {length}', f'K: {key}']

    # Parse each voice into note timeline
    voice_notes = {}  # vid -> [(abs_offset, duration, midi, pitch)]
    for vid in ['1','2','3','4','5','6','7','8']:
        if vid not in voices: continue
        vmusic = re.sub(r'![a-zA-Z]+!', '', ' '.join(voices[vid]))
        abc_v = '\n'.join(base_header) + '\n' + vmusic + '\n'
        try:
            sc = music21.converter.parse(abc_v, format='abc')
            part = sc.parts[0] if sc.parts else sc
            notes = []
            for n in part.recurse().getElementsByClass('Note'):
                abs_off = float(n.offset + n.activeSite.offset)
                notes.append((abs_off, n.duration.quarterLength, n.pitch.midi, n.pitch))
            voice_notes[vid] = sorted(notes)
        except:
            pass

    if '1' not in voice_notes:
        return False

    # Build melody onsets
    mel_notes = voice_notes['1']

    # For each melody note, collect all voice pitches starting at that offset
    mel_abc_parts = []  # list of ABC strings for melody line
    rh_abc_parts = []
    lh_abc_parts = []

    # Track bar positions from melody
    mel_music = re.sub(r'![a-zA-Z]+!', '', ' '.join(voices['1']))
    mel_tokens = re.findall(r"z[0-9/]*|[_^=]*[A-Ga-g][,']*[0-9/]*|\|]|\||\(|\)", mel_music)

    # Build beat-by-beat: for each melody note, find concurrent voices
    beat_data = []  # [(mel_pitch, mel_dur, all_pitches_sorted)]
    for onset, dur, midi, pitch in mel_notes:
        concurrent = set()
        for vid in voice_notes:
            for off, ndur, nmidi, npitch in voice_notes[vid]:
                if abs(off - onset) < 0.05:
                    concurrent.add((nmidi, npitch))
                    break
                if off > onset + 0.1:
                    break

        sorted_pitches = sorted(concurrent, key=lambda x: x[0])
        # Deduplicate by midi
        seen = set(); unique = []
        for m, p in sorted_pitches:
            if m not in seen:
                seen.add(m); unique.append((m, p))

        beat_data.append((pitch, dur, unique))

    # Now rebuild ABC: walk through melody tokens, replacing notes with annotated versions
    beat_idx = 0
    measure_idx = 0
    note_in_measure = 0
    mel_out = []
    rh_out = []
    lh_out = []

    for tok in mel_tokens:
        if tok in ('|', '|]'):
            mel_out.append(tok)
            rh_out.append(tok)
            lh_out.append(tok)
            if tok == '|':
                measure_idx += 1
                note_in_measure = 0
            continue
        if tok in ('(', ')'):
            mel_out.append(tok)
            rh_out.append(tok)
            lh_out.append(tok)
            continue
        if re.match(r'^z', tok):
            mel_out.append(tok)
            rh_out.append(tok)
            lh_out.append(tok)
            beat_idx += 1
            note_in_measure += 1
            continue
        if re.match(r'^[_^=]*[A-Ga-g]', tok):
            if beat_idx < len(beat_data):
                mel_pitch, mel_dur, all_pitches = beat_data[beat_idx]
                dur_str = dur_to_abc(mel_dur)

                # Split pitches: LH = bottom half (≥), RH = top half
                n = len(all_pitches)
                lh_count = (n + 1) // 2
                lh_pitches = all_pitches[:lh_count]
                rh_pitches = all_pitches[lh_count:]

                # Chord fraction annotations (first note of each measure only)
                annotation = ''
                if note_in_measure == 0:
                    # Abstract chord
                    pcs = []; seen_pc = set()
                    for midi, p in all_pitches:
                        pc = (midi - ko) % 12
                        if pc not in seen_pc: seen_pc.add(pc); pcs.append(pc)
                    c_names = [PC_TO_C.get(pc) for pc in pcs]
                    abs_ch = ''
                    if all(c_names) and len(c_names) >= 3:
                        try: abs_ch = roman_name(c_names)
                        except: pass

                    # RH voicing name
                    rh_letters = []
                    for midi, p in rh_pitches:
                        nm = PC_TO_C.get((midi - ko) % 12)
                        if nm and nm not in rh_letters: rh_letters.append(nm)
                    rh_name = ''
                    if len(rh_letters) >= 3:
                        try: rh_name = best_name(rh_letters)
                        except: pass

                    # LH voicing name
                    lh_letters = []
                    for midi, p in lh_pitches:
                        nm = PC_TO_C.get((midi - ko) % 12)
                        if nm and nm not in lh_letters: lh_letters.append(nm)
                    lh_name = ''
                    if len(lh_letters) >= 3:
                        try: lh_name = best_name(lh_letters)
                        except: pass

                    if abs_ch: annotation += f'"^{abs_ch}"'
                    if rh_name: annotation += f'"^{rh_name}"'
                    if lh_name: annotation += f'"^{lh_name}"'

                # Melody note
                mel_out.append(f'{annotation}{tok}')

                # RH chord
                if rh_pitches:
                    rh_abc = '[' + ''.join(pitch_to_abc(p, key_acc) for _, p in rh_pitches) + ']' + dur_str
                else:
                    rh_abc = 'z' + dur_str
                rh_out.append(rh_abc)

                # LH chord
                if lh_pitches:
                    lh_abc = '[' + ''.join(pitch_to_abc(p, key_acc) for _, p in lh_pitches) + ']' + dur_str
                else:
                    lh_abc = 'z' + dur_str
                lh_out.append(lh_abc)
            else:
                mel_out.append(tok)
                rh_out.append(tok)
                lh_out.append(tok)

            beat_idx += 1
            note_in_measure += 1
            continue

        # Other tokens
        mel_out.append(tok)
        rh_out.append(tok)
        lh_out.append(tok)

    mel_line = ' '.join(mel_out)
    rh_line = ' '.join(rh_out)
    lh_line = ' '.join(lh_out)

    abc_out = f"""X: 1
T: {title}
M: {meter}
L: {length}
Q: {tempo}
%%staves M | {{RH LH}}
V: M clef=treble name="Melody"
V: RH clef=treble name="RH"
V: LH clef=bass name="LH"
K: {key}
[V: M] {mel_line}
[V: RH] {rh_line}
[V: LH] {lh_line}
"""

    with open(outpath, 'w') as f:
        f.write(abc_out)

    # HTML
    htmlpath = outpath.replace('.abc', '.html')
    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title} — Harp Hymnal</title>
<style>body {{ font-family: sans-serif; margin: 20px; }} h1 {{ font-size: 18px; }}
p.legend {{ font-size: 12px; color: #555; }}</style>
</head><body>
<h1>{title}</h1>
<p class="legend">Above melody: Abstract / RH voicing / LH voicing.
RH = upper notes, LH = lower notes (no hand crossing).</p>
<div id="music"></div>
<script src="{ABC2SVG_REL}"></script>
<script>
var abc_src = {json.dumps(abc_out)};
var user = {{
  img_out: function(str) {{ document.getElementById("music").innerHTML += str; }},
  errmsg: function(msg) {{ console.warn("abc2svg:", msg); }},
  read_file: function() {{ return ""; }}
}};
var abc = new abc2svg.Abc(user);
abc.tosvg("score", abc_src);
</script></body></html>'''

    with open(htmlpath, 'w') as f:
        f.write(html)

    return True

# Process all
input_files = sorted(glob.glob(os.path.join(IN_DIR, '*.abc')))
count = 0; errors = 0

for filepath in input_files:
    fname = os.path.basename(filepath)
    outpath = os.path.join(OUT_DIR, fname)
    try:
        if process_file(filepath, outpath):
            count += 1
        else:
            errors += 1
    except Exception as e:
        print(f"Error {fname}: {e}", file=sys.stderr)
        errors += 1
    if (count + errors) % 50 == 0:
        print(f"  Processed {count + errors}...", file=sys.stderr)

print(f"Done: {count} converted, {errors} errors", file=sys.stderr)
