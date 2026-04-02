"""
Full trefoil traversal: CCW4 CCW3 CCW2 CW2 CW3 CW4
Two tunes on one page: Eb (top) and C (bottom)
8th notes, grand staff, hymn style.
"""
import sys, subprocess, shutil
sys.path.insert(0, '/home/claude')

from lh_trefoil import (all_voicings_for_root, all_voicings_above,
    score_voicing, score_rh_voicing, ROOT_MAP, TREFOIL, ALL_PATTERNS)

SCALE = ['C','D','E','F','G','A','B']
TRANS_EB = {'C':'E','D':'F','E':'G','F':'A','G':'B','A':'C','B':'D'}
TRAVERSAL = ['CCW4','CCW3','CCW2','CW2','CW3','CW4']

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

def to_abc_pitch(note, ob):
    if ob <= 0:    return note + ',,' + ','*(-ob)
    elif ob == 1:  return note + ','
    elif ob == 2:  return note
    elif ob == 3:  return note.lower()
    elif ob == 4:  return note.lower() + "'"
    else:          return note.lower() + "'"*(ob-3)

def notes_to_abc_chord(note_names, base_octave, trans=None):
    if trans: note_names = [trans[n] for n in note_names]
    abc=[]; prev_idx=-1; octave=base_octave
    for note in note_names:
        idx = SCALE.index(note)
        if prev_idx != -1 and idx < prev_idx: octave += 1
        abc.append(to_abc_pitch(note, octave))
        prev_idx = idx
    return '[' + ''.join(abc) + ']' if len(abc) > 1 else abc[0]

def rh(notes, trans=None): return notes_to_abc_chord(notes, 2, trans)
def lh(notes, trans=None): return notes_to_abc_chord(notes, 1, trans)

def build_voice(tokens):
    """48 quarter notes: 4 per bar, 6 bars per source line.
    Double bar at segment boundaries every 8 chords (2 bars)."""
    bars = []
    for bar_idx in range(12):
        start = bar_idx * 4
        bar = ' '.join(tokens[start:start+4])
        pos = (bar_idx + 1) * 4
        if pos == 48:      sep = ' |]'
        elif pos % 8 == 0: sep = ' ||'
        else:              sep = ' |'
        bars.append(bar + sep)
    # Group 6 bars per line
    lines = []
    for i in range(0, len(bars), 6):
        lines.append(' '.join(bars[i:i+6]))
    return '\n'.join(lines)

def make_tune(num, title, key, trans, results):
    rh_tokens = []
    lh_tokens = []
    for seg_name in TRAVERSAL:
        for row in [r for r in results if r['seg'] == seg_name]:
            rh_tokens.append(rh(row['rh_notes'], trans))
            lh_tokens.append(lh(row['lh_notes'], trans))

    rh_line = build_voice(rh_tokens)
    lh_line = build_voice(lh_tokens)

    return '\n'.join([
        f'X:{num}',
        f'T:{title}',
        'M:4/4',
        'L:1/4',
        'Q:1/4=60',
        f'K:{key}',
        '%%MIDI program 46',
        '%%staves {RH LH}',
        'V:RH clef=treble stem=up',
        'V:LH clef=bass stem=down',
        f'[V:RH]\n{rh_line}',
        f'[V:LH]\n{lh_line}',
    ])

def generate():
    results = build_results()
    abc_path = '/home/claude/trefoil_full.abc'
    ps_path  = '/home/claude/trefoil_full.ps'

    preamble = '\n'.join([
        '%%encoding utf-8',
        '%%staffsep 35',
        '%%sysstaffsep 0',
        '%%topmargin 0.5cm',
        '%%botmargin 0.5cm',
        '%%leftmargin 0.8cm',
        '%%rightmargin 0.8cm',
        '%%pagewidth 21cm',
        '%%pageheight 29.7cm',
        '%%titlefont Times-Bold 16',
        '%%titlespace 3',
        '%%musicspace 2',
        '%%barsperline 8',
    ])

    tune_eb = make_tune(1, 'Trefoil  Eb  CCW4-CCW3-CCW2-CW2-CW3-CW4', 'Eb', TRANS_EB, results)
    tune_c  = make_tune(2, 'Trefoil  C   CCW4-CCW3-CCW2-CW2-CW3-CW4', 'C',  None,     results)

    full_abc = preamble + '\n\n' + tune_eb + '\n\n' + tune_c + '\n'

    with open(abc_path, 'w') as f:
        f.write(full_abc)
    print(f"Saved ABC: {abc_path}")

    # Render notation
    r = subprocess.run(['abcm2ps', '-O', ps_path, abc_path],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    pages = r.stdout.count('page')
    if r.stderr.strip():
        errs = [l for l in r.stderr.strip().split('\n') if 'error' in l.lower()]
        if errs: print("errors:", errs)

    hd = open(ps_path).read().count(' hd ')
    print(f"Noteheads: {hd}")

    pdf_path = '/home/claude/trefoil_full_music.pdf'
    r2 = subprocess.run(
        ['gs', '-dNOPAUSE', '-dBATCH', '-sDEVICE=pdfwrite',
         f'-sOutputFile={pdf_path}', ps_path],
        capture_output=True, text=True)
    if r2.returncode == 0:
        print(f"Music PDF: {pdf_path}")

    # Composite trefoil image at bottom of music page using pypdf
    from pypdf import PdfReader, PdfWriter, PageObject
    from pypdf.generic import RectangleObject
    import struct

    # Render trefoil PDF to a page we can stamp
    trefoil_pdf = '/home/claude/trefoil.pdf'

    # Use ghostscript to place trefoil as a stamp at the bottom
    # Strategy: use pypdf to overlay trefoil page onto music page, scaled down
    music_reader   = PdfReader(pdf_path)
    trefoil_reader = PdfReader(trefoil_pdf)

    writer = PdfWriter()

    # Get music page dimensions
    music_page = music_reader.pages[0]
    mw = float(music_page.mediabox.width)
    mh = float(music_page.mediabox.height)

    # Trefoil page dimensions
    tpage = trefoil_reader.pages[0]
    tw = float(tpage.mediabox.width)
    th = float(tpage.mediabox.height)

    # Scale trefoil to fill available whitespace (~400pt)
    # Music ends ~437pt from top, page is 842pt, leaving ~400pt
    # Trefoil is wide (640x496pt) so constrain by width too
    margin = 15.0
    avail_h = mh - 437 - margin * 2   # ~390pt
    avail_w = mw - margin * 2

    scale = min(avail_h / th, avail_w / tw)
    target_w = tw * scale
    target_h = th * scale
    x_offset = (mw - target_w) / 2
    y_offset = margin - 36

    # Merge: stamp trefoil onto music page
    music_page.merge_transformed_page(
        tpage,
        [scale, 0, 0, scale, x_offset, y_offset]
    )

    writer.add_page(music_page)
    out_path = '/mnt/user-data/outputs/trefoil_full_notation.pdf'
    with open(out_path, 'wb') as f:
        writer.write(f)
    print(f"Final PDF: {out_path}")

    # MIDI files
    for num, name in [(1, 'eb'), (2, 'c')]:
        mid_path = f'/mnt/user-data/outputs/trefoil_{name}_full.mid'
        r3 = subprocess.run(
            ['abc2midi', abc_path, str(num), '-o', mid_path],
            capture_output=True, text=True)
        print(f"MIDI {name}: {r3.stdout.strip()}")

    shutil.copy(abc_path, '/mnt/user-data/outputs/trefoil_full.abc')

if __name__ == '__main__':
    generate()
