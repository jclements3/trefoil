#!/usr/bin/env python3
"""Convert SSAATTBB abc files to harp hymnal format:
   Melody (S1) on top with chord fraction annotations,
   RH=SSAA treble, LH=TTBB bass grand staff.
   Uses music21 to parse voices for chord analysis."""

import os, re, sys, glob, json, warnings
warnings.filterwarnings('ignore')
import music21

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'handout'))
from chord_name import best_name, roman_name

IN_DIR = os.path.join(os.path.dirname(__file__), '..', 'handout/ssaattbb_out')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'handout/harphymnal')
ABC2SVG_REL = '../../abc2stripchart/app/src/main/assets/abc2svg/abc2svg-1.js'
os.makedirs(OUT_DIR, exist_ok=True)

KEY_PC = {'C':0,'G':7,'D':2,'A':9,'E':4,'B':11,'F':5,
          'Bb':10,'Eb':3,'Ab':8,'Db':1,'F#':6,'Gb':6,'Cb':11,'C#':1}
PC_TO_C = {0:'C', 2:'D', 4:'E', 5:'F', 7:'G', 9:'A', 11:'B'}

def extract_voices(abc_text):
    lines = abc_text.split('\n')
    header = []; voices = {}; current_voice = None
    for line in lines:
        ls = line.strip()
        if not ls: continue
        vm = re.match(r'\[V:(\d+)\]\s*(.*)', ls)
        if vm:
            current_voice = vm.group(1)
            music = vm.group(2).strip()
            if current_voice not in voices: voices[current_voice] = []
            if music: voices[current_voice].append(music)
            continue
        if current_voice and not ls.startswith(('X:','T:','C:','M:','L:','K:','Q:','V:','%%')):
            voices[current_voice].append(ls)
            continue
        if ls.startswith(('X:','T:','M:','L:','K:','Q:')):
            header.append(ls); current_voice = None
        elif ls.startswith('C:') and any(h.startswith('T:') for h in header):
            header.append(ls)
    return header, voices

def get_val(header, prefix, default=''):
    for h in header:
        if h.startswith(prefix):
            return h[len(prefix):].split('%')[0].strip()
    return default

def parse_single_voice(base_header, voice_music):
    abc = '\n'.join(base_header) + '\n' + voice_music + '\n'
    try:
        sc = music21.converter.parse(abc, format='abc')
        return sc.parts[0] if sc.parts else sc
    except:
        return None

def compute_chord_fractions(parts, key, n_meas):
    """Compute chord fraction annotations per measure."""
    ko = KEY_PC.get(key, 0)
    all_measures = {vid: list(parts[vid].getElementsByClass('Measure')) for vid in parts}
    fractions = {}

    # Use melody measure count as the reference (don't let a short-parsing voice limit us)
    mel_count = len(all_measures.get('1', []))
    n_meas = mel_count if mel_count > 0 else n_meas

    for mi in range(n_meas):
        rh_midis = []
        lh_midis = []
        for vid in ['1','2','3','4']:
            if vid not in all_measures or mi >= len(all_measures[vid]): continue
            notes = list(all_measures[vid][mi].recurse().getElementsByClass('Note'))
            if notes: rh_midis.append(notes[0].pitch.midi)
        for vid in ['5','6','7','8']:
            if vid not in all_measures or mi >= len(all_measures[vid]): continue
            notes = list(all_measures[vid][mi].recurse().getElementsByClass('Note'))
            if notes: lh_midis.append(notes[0].pitch.midi)

        # Abstract chord
        all_midis = rh_midis + lh_midis
        pcs = []; seen = set()
        for midi in sorted(all_midis):
            pc = (midi - ko) % 12
            if pc not in seen: seen.add(pc); pcs.append(pc)
        c_names = [PC_TO_C.get(pc) for pc in pcs]
        abs_chord = ''
        if all(c_names) and len(c_names) >= 3:
            try: abs_chord = roman_name(c_names)
            except: pass

        # RH voicing name
        rh_letters = []
        for midi in sorted(set(rh_midis)):
            name = PC_TO_C.get((midi - ko) % 12)
            if name and name not in rh_letters: rh_letters.append(name)
        rh_name = ''
        if len(rh_letters) >= 3:
            try: rh_name = best_name(rh_letters)
            except: pass

        # LH voicing name
        lh_letters = []
        for midi in sorted(set(lh_midis)):
            name = PC_TO_C.get((midi - ko) % 12)
            if name and name not in lh_letters: lh_letters.append(name)
        lh_name = ''
        if len(lh_letters) >= 3:
            try: lh_name = best_name(lh_letters)
            except: pass

        fractions[mi] = (abs_chord, rh_name, lh_name)

    return fractions

def annotate_melody(melody_abc, fractions):
    """Inject chord fraction annotations into melody ABC string."""
    # Tokenize melody
    tokens = re.findall(r"z[0-9/]*|[_^=]*[A-Ga-g][,']*[0-9/]*|\|]|\||\(|\)|![\w]+!", melody_abc)

    # Count bars to map measure index
    measure_idx = 0
    note_in_measure = 0
    annotated = []

    for tok in tokens:
        if tok == '|' or tok == '|]':
            annotated.append(tok)
            if tok == '|':
                measure_idx += 1
                note_in_measure = 0
            continue
        if re.match(r'^[_^=]*[A-Ga-g]', tok):
            # It's a note
            if note_in_measure == 0 and measure_idx in fractions:
                abs_ch, rhn, lhn = fractions[measure_idx]
                prefix = ''
                if abs_ch: prefix += f'"^{abs_ch}"'
                if rhn: prefix += f'"^{rhn}"'
                if lhn: prefix += f'"^{lhn}"'
                annotated.append(f'{prefix}{tok}')
            else:
                annotated.append(tok)
            note_in_measure += 1
        else:
            annotated.append(tok)

    return ' '.join(annotated)

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

    base_header = ['X: 1', f'M: {meter}', f'L: {length}', f'K: {key}']

    # Parse voices with music21
    parts = {}
    for vid in ['1','2','3','4','5','6','7','8']:
        if vid not in voices: continue
        vmusic = ' '.join(voices[vid])
        vmusic = re.sub(r'![a-zA-Z]+!', '', vmusic)
        part = parse_single_voice(base_header, vmusic)
        if part: parts[vid] = part

    if len(parts) < 6:
        return False

    # Compute chord fractions
    n_meas = min(len(list(parts[vid].getElementsByClass('Measure'))) for vid in parts)
    fractions = compute_chord_fractions(parts, key, n_meas)

    # Get voice music strings
    def clean(s):
        return re.sub(r'!sintro!|!eintro!|!fermata!|![a-z]+!', '', s).strip()

    v = {}
    for vid in ['1','2','3','4','5','6','7','8']:
        v[vid] = clean(' '.join(voices.get(vid, [])))

    # Annotate melody with chord fractions
    melody_annotated = annotate_melody(v['1'], fractions)

    abc_out = f"""X: 1
T: {title}
M: {meter}
L: {length}
Q: {tempo}
%%staves M | {{(RH1 RH2 RH3 RH4) (LH1 LH2 LH3 LH4)}}
V: M clef=treble name="Melody"
V: RH1 clef=treble name="RH"
V: RH2 clef=treble
V: RH3 clef=treble
V: RH4 clef=treble
V: LH1 clef=bass name="LH"
V: LH2 clef=bass
V: LH3 clef=bass
V: LH4 clef=bass
K: {key}
[V: M] {melody_annotated}
[V: RH1] {v['1']}
[V: RH2] {v['2']}
[V: RH3] {v['3']}
[V: RH4] {v['4']}
[V: LH1] {v['5']}
[V: LH2] {v['6']}
[V: LH3] {v['7']}
[V: LH4] {v['8']}
"""

    with open(outpath, 'w') as f:
        f.write(abc_out)

    # Also write HTML
    htmlpath = outpath.replace('.abc', '.html')
    html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{title} — Harp Hymnal</title>
<style>body {{ font-family: sans-serif; margin: 20px; }} h1 {{ font-size: 18px; }}
p.legend {{ font-size: 12px; color: #555; }}</style>
</head><body>
<h1>{title}</h1>
<p class="legend">Above melody: Abstract chord / RH voicing / LH voicing</p>
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

# Process all files
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

print(f"Done: {count} converted with chord fractions, {errors} errors", file=sys.stderr)
