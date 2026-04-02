"""
Generate trefoil drill for all 8 keys (storage order: Eb Bb F C G D A E)
4 music pages (2 keys each) + 4 table pages (2 keys each)
"""
import sys, subprocess, shutil
sys.path.insert(0, '.')

from lh_trefoil import (all_voicings_for_root, all_voicings_above,
    score_voicing, score_rh_voicing, ROOT_MAP, TREFOIL, ALL_PATTERNS)
from chord_name import name_voicing
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
import mido, os

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_PATH = '/usr/share/fonts/truetype/dejavu/'
pdfmetrics.registerFont(TTFont('DejaVu',     FONT_PATH + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuBold', FONT_PATH + 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuMono', FONT_PATH + 'DejaVuSansMono.ttf'))

# ── Key definitions ───────────────────────────────────────────────────────────
SCALE = ['C','D','E','F','G','A','B']
SEMITONES = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11,
             'C#':1,'D#':3,'F#':6,'G#':8,'A#':10,
             'Cb':11,'Db':1,'Eb':3,'Ab':8,'Bb':10,'Gb':6}

KEYS = [
    ('Eb','Eb',{'C':'Eb','D':'F', 'E':'G', 'F':'Ab','G':'Bb','A':'C', 'B':'D' }),
    ('Bb','Bb',{'C':'Bb','D':'C', 'E':'D', 'F':'Eb','G':'F', 'A':'G', 'B':'Ab'}),
    ('F', 'F', {'C':'F', 'D':'G', 'E':'A', 'F':'Bb','G':'C', 'A':'D', 'B':'Eb'}),
    ('C', 'C', {'C':'C', 'D':'D', 'E':'E', 'F':'F', 'G':'G', 'A':'A', 'B':'B' }),
    ('G', 'G', {'C':'G', 'D':'A', 'E':'B', 'F':'C', 'G':'D', 'A':'E', 'B':'F#'}),
    ('D', 'D', {'C':'D', 'D':'E', 'E':'F#','F':'G', 'G':'A', 'A':'B', 'B':'C#'}),
    ('A', 'A', {'C':'A', 'D':'B', 'E':'C#','F':'D', 'G':'E', 'A':'F#','B':'G#'}),
    ('E', 'E', {'C':'E', 'D':'F#','E':'G#','F':'A', 'G':'B', 'A':'C#','B':'D#'}),
]

TRAVERSAL = ['CCW4','CCW3','CCW2','CW2','CW3','CW4']

SEG_COLORS     = {'CW4':colors.HexColor('#BE9B1E'),'CCW4':colors.HexColor('#BE9B1E'),
                  'CW3':colors.HexColor('#DC4B4B'),'CCW3':colors.HexColor('#DC4B4B'),
                  'CW2':colors.HexColor('#28B4BE'),'CCW2':colors.HexColor('#28B4BE')}
SEG_TEXT       = {'CW4':colors.black,'CCW4':colors.black,
                  'CW3':colors.white,'CCW3':colors.white,
                  'CW2':colors.black,'CCW2':colors.black}
SEG_ALT        = {'CW4':colors.HexColor('#FDF8E1'),'CCW4':colors.HexColor('#FDF8E1'),
                  'CW3':colors.HexColor('#FDE8E8'),'CCW3':colors.HexColor('#FDE8E8'),
                  'CW2':colors.HexColor('#E0F7F8'),'CCW2':colors.HexColor('#E0F7F8')}

# ── Build voicing results ─────────────────────────────────────────────────────
def build_results():
    lh_used=[]; rh_used=[]; lh_prev=None; rh_prev=None; results=[]
    for seg_name, roots in TREFOIL:
        for root in roots:
            root_idx = ROOT_MAP[root]
            lh_voicings = all_voicings_for_root(root_idx)
            lh_best = max(lh_voicings, key=lambda v: score_voicing(v, lh_prev, lh_used, ALL_PATTERNS))
            lh_used.append(lh_best['pattern'])
            lh_prev = lh_best['strings']
            lh_top  = lh_best['strings'][-1]
            rh_voicings = all_voicings_above(lh_top, root_idx, lh_best['pattern'])
            if not rh_voicings:
                rh_voicings = all_voicings_above(lh_top, root_idx, None)
            rh_best = max(rh_voicings, key=lambda v: score_rh_voicing(v, rh_prev, rh_used))
            rh_used.append(rh_best['pattern'])
            rh_prev = rh_best['strings']
            results.append({'seg':seg_name,'lh_notes':lh_best['notes'],'rh_notes':rh_best['notes']})
    return results

# ── ABC helpers ───────────────────────────────────────────────────────────────
def to_abc_pitch(note, ob):
    # Strip accidentals for octave lookup, add them back
    base = note[0]
    acc  = note[1:].replace('#','#').replace('b','b')
    abc_acc = '^' if '#' in acc else ('_' if 'b' in acc else '')
    if ob <= 0:   return abc_acc + base + ',,' + ','*(-ob)
    elif ob == 1: return abc_acc + base + ','
    elif ob == 2: return abc_acc + base
    elif ob == 3: return abc_acc + base.lower()
    else:         return abc_acc + base.lower() + "'"*(ob-3)

def notes_to_abc_chord(note_names, base_octave):
    abc=[]; prev_idx=-1; octave=base_octave
    for note in note_names:
        base = note[0]
        idx  = SCALE.index(base)
        if prev_idx != -1 and idx < prev_idx: octave += 1
        abc.append(to_abc_pitch(note, octave))
        prev_idx = idx
    return '[' + ''.join(abc) + ']' if len(abc) > 1 else abc[0]

def rh_abc(notes): return notes_to_abc_chord(notes, 2)
def lh_abc(notes): return notes_to_abc_chord(notes, 1)

def build_voice(tokens):
    bars = []
    for bar_idx in range(12):
        start = bar_idx * 4
        bar   = ' '.join(tokens[start:start+4])
        pos   = (bar_idx + 1) * 4
        if pos == 48:      sep = ' |]'
        elif pos % 8 == 0: sep = ' ||'
        else:              sep = ' |'
        bars.append(bar + sep)
    lines = []
    for i in range(0, len(bars), 6):
        lines.append(' '.join(bars[i:i+6]))
    return '\n'.join(lines)

def make_abc_tune(num, key_name, abc_key, trans, results):
    rh_tokens = []
    lh_tokens = []
    for seg in TRAVERSAL:
        for row in [r for r in results if r['seg']==seg]:
            lh = [trans[n] for n in row['lh_notes']]
            rh = [trans[n] for n in row['rh_notes']]
            rh_tokens.append(rh_abc(rh))
            lh_tokens.append(lh_abc(lh))
    return '\n'.join([
        f'X:{num}',
        f'T:Trefoil  {key_name}  CCW4-CCW3-CCW2-CW2-CW3-CW4',
        'M:4/4','L:1/4','Q:1/4=60',
        f'K:{abc_key}',
        '%%MIDI program 46',
        '%%staves {RH LH}',
        'V:RH clef=treble stem=up',
        'V:LH clef=bass stem=down',
        f'[V:RH]\n{build_voice(rh_tokens)}',
        f'[V:LH]\n{build_voice(lh_tokens)}',
    ])

# ── MIDI helpers ──────────────────────────────────────────────────────────────
NOTE_BASE = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def note_midi(note, octave):
    base = note[0]
    acc  = note[1:]
    semi = NOTE_BASE[base] + (1 if '#' in acc else -1 if 'b' in acc else 0)
    return (octave+1)*12 + semi

def assign_octaves(notes, base_octave=3):
    octaves=[]; octave=base_octave; prev_idx=-1
    for note in notes:
        idx = SCALE.index(note[0])
        if prev_idx != -1 and idx <= prev_idx: octave += 1
        octaves.append((note, octave))
        prev_idx = idx
    return octaves

def chord_midi_notes(lh_notes, rh_notes, trans):
    lh = [trans[n] for n in lh_notes]
    rh = [trans[n] for n in rh_notes]
    lh_oct = assign_octaves(lh, 3)
    last_note, last_oct = lh_oct[-1]
    first_rh_idx = SCALE.index(rh[0][0])
    last_lh_idx  = SCALE.index(last_note[0])
    rh_base = last_oct if first_rh_idx > last_lh_idx else last_oct + 1
    rh_oct  = assign_octaves(rh, rh_base)
    return [note_midi(n,o) for n,o in lh_oct + rh_oct]

def make_midi_file(key_name, trans, results, filename, tempo_bpm=60):
    mid   = mido.MidiFile(type=0, ticks_per_beat=480)
    track = mido.MidiTrack(); mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo_bpm), time=0))
    track.append(mido.Message('program_change', program=46, time=0))
    beat=480; strum_gap=24; seg_pause=240
    events=[]; abs_tick=0; prev_seg=None
    for seg in TRAVERSAL:
        if prev_seg is not None: abs_tick += seg_pause
        prev_seg = seg
        for row in [r for r in results if r['seg']==seg]:
            notes = chord_midi_notes(row['lh_notes'], row['rh_notes'], trans)
            for i,pitch in enumerate(notes):
                events.append((abs_tick + i*strum_gap, 'on',  pitch, 80))
            for pitch in notes:
                events.append((abs_tick + beat,        'off', pitch, 0))
            abs_tick += beat
    events.sort(key=lambda e:(e[0], 0 if e[1]=='off' else 1))
    prev_tick=0
    for tick,etype,pitch,vel in events:
        delta = tick - prev_tick
        if etype=='on':  track.append(mido.Message('note_on',  note=pitch, velocity=vel, time=delta))
        else:            track.append(mido.Message('note_off', note=pitch, velocity=0,   time=delta))
        prev_tick = tick
    mid.save(filename)
    print(f"  MIDI: {filename}")

# ── Table helpers ─────────────────────────────────────────────────────────────
SUP_MAP = {'¹':'1','²':'2','³':'3','⁴':'4'}
def strip_sup(s):
    for u,d in SUP_MAP.items():
        if u in s: return s.replace(u,''), d
    return s, None

def draw_chord_name(cv, x, y, name, font='DejaVu', size=6):
    base, sup = strip_sup(name)
    cv.setFont(font, size)
    cv.drawString(x, y, base)
    if sup:
        w = pdfmetrics.stringWidth(base, font, size)
        cv.setFont(font, size*0.65)
        cv.drawString(x+w, y+size*0.4, sup)

def draw_table(cv, results, key1_name, key1_trans, key2_name, key2_trans,
               x_off, y_start, page_w, page_h, margin):
    col_min_pts = {
        '#':0.092,'Root':0.105,'LHpat':0.192,'Gap':0.092,'RHpat':0.192,
        f'LH {key1_name}':0.546, f'RH {key1_name}':0.591,
        f'LH Notes {key1_name}':0.242, f'RH Notes {key1_name}':0.242,
        f'LH {key2_name}':0.583, f'RH {key2_name}':0.591,
        f'LH Notes {key2_name}':0.242, f'RH Notes {key2_name}':0.242,
    }
    cols    = list(col_min_pts.keys())
    avail   = page_w - 2*margin
    scale   = avail / (sum(col_min_pts.values()) * inch)
    col_w   = {k: v*inch*scale for k,v in col_min_pts.items()}
    table_w = sum(col_w.values())

    seg_h=12; col_h=11; gap_h=3
    fixed     = (seg_h+col_h+gap_h)*6
    avail_rows= y_start - margin - fixed
    row_h     = avail_rows / 48
    font_size = max(5.0, row_h - 2.0)
    y = y_start

    for seg_name, roots in TREFOIL:
        seg_rows = [r for r in results if r['seg']==seg_name]

        # Segment header
        cv.setFillColor(SEG_COLORS[seg_name])
        cv.rect(x_off, y-seg_h, table_w, seg_h, fill=1, stroke=0)
        cv.setFillColor(SEG_TEXT[seg_name])
        cv.setFont('DejaVuBold', 7.5)
        cv.drawString(x_off+3, y-8, seg_name)
        y -= seg_h

        # Column header
        cv.setFillColor(colors.HexColor('#cccccc'))
        cv.rect(x_off, y-col_h, table_w, col_h, fill=1, stroke=0)
        cv.setFillColor(colors.black)
        col_labels = {
            '#':'#','Root':'Root','LHpat':'LH Pat','Gap':'G','RHpat':'RH Pat',
            f'LH {key1_name}':f'LH Chord {key1_name}',
            f'RH {key1_name}':f'RH Chord {key1_name}',
            f'LH Notes {key1_name}':f'LH Notes {key1_name}',
            f'RH Notes {key1_name}':f'RH Notes {key1_name}',
            f'LH {key2_name}':f'LH Chord {key2_name}',
            f'RH {key2_name}':f'RH Chord {key2_name}',
            f'LH Notes {key2_name}':f'LH Notes {key2_name}',
            f'RH Notes {key2_name}':f'RH Notes {key2_name}',
        }
        cv.setFont('DejaVu', 5.5)
        xi = x_off+2
        for col in cols:
            cv.drawString(xi, y-8, col_labels[col])
            xi += col_w[col]
        y -= col_h

        # Data rows
        for i, row in enumerate(seg_rows):
            if i % 2 == 0:
                cv.setFillColor(SEG_ALT[seg_name])
                cv.rect(x_off, y-row_h, table_w, row_h, fill=1, stroke=0)
            cv.setFillColor(colors.black)

            ty = y - row_h + (row_h - font_size)/2
            xi = x_off+2

            # row number
            cv.setFont('DejaVuMono', font_size-0.5)
            cv.setFillColor(colors.grey)
            cv.drawString(xi, ty, str(i+1))
            cv.setFillColor(colors.black)
            xi += col_w['#']

            # Root
            cv.setFont('DejaVuBold', font_size)
            cv.drawString(xi, ty, row['root'])
            xi += col_w['Root']

            # LH Pat
            cv.setFont('DejaVuMono', font_size-0.5)
            cv.setFillColor(colors.HexColor('#444444'))
            cv.drawString(xi, ty, row['lh_pat'].replace('-',''))
            cv.setFillColor(colors.black)
            xi += col_w['LHpat']

            # Gap
            cv.setFont('DejaVuBold', font_size)
            cv.drawString(xi, ty, str(row['gap']))
            xi += col_w['Gap']

            # RH Pat
            cv.setFont('DejaVuMono', font_size-0.5)
            cv.setFillColor(colors.HexColor('#444444'))
            cv.drawString(xi, ty, row['rh_pat'].replace('-',''))
            cv.setFillColor(colors.black)
            xi += col_w['RHpat']

            # Helper: translate notes and draw chord + notes columns
            def draw_key_cols(trans, lh_col, rh_col, lhn_col, rhn_col):
                nonlocal xi
                lh_eb = [trans[n] for n in row['lh_notes']]
                rh_eb = [trans[n] for n in row['rh_notes']]
                # name_voicing needs C-key root (diatonic degree letter)
                lh_name = name_voicing(row['lh_notes'], row['lh_notes'][0])
                rh_name = name_voicing(row['rh_notes'], row['rh_notes'][0])
                draw_chord_name(cv, xi, ty, lh_name, 'DejaVuBold', font_size)
                xi += col_w[lh_col]
                draw_chord_name(cv, xi, ty, rh_name, 'DejaVuBold', font_size)
                xi += col_w[rh_col]
                cv.setFont('DejaVuMono', font_size-0.5)
                cv.drawString(xi, ty, ''.join(lh_eb))
                xi += col_w[lhn_col]
                cv.drawString(xi, ty, ''.join(rh_eb))
                xi += col_w[rhn_col]

            draw_key_cols(key1_trans,
                f'LH {key1_name}', f'RH {key1_name}',
                f'LH Notes {key1_name}', f'RH Notes {key1_name}')
            draw_key_cols(key2_trans,
                f'LH {key2_name}', f'RH {key2_name}',
                f'LH Notes {key2_name}', f'RH Notes {key2_name}')

            y -= row_h

        y -= gap_h

# ── Build row data for table ──────────────────────────────────────────────────
def build_table_rows(results):
    rows = []
    for seg_name, roots in TREFOIL:
        for row in [r for r in results if r['seg']==seg_name]:
            rows.append({
                'seg':      seg_name,
                'root':     row['lh_notes'][0],
                'lh_pat':   '-'.join(str(x) for x in
                            [row['lh_notes'][i+1] != row['lh_notes'][i]
                             and 2 or 2 for i in range(len(row['lh_notes'])-1)]),
                'rh_pat':   '',
                'gap':      0,
                'lh_notes': row['lh_notes'],
                'rh_notes': row['rh_notes'],
            })
    return rows

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    results = build_results()

    # Rebuild with pattern info from lh_trefoil
    from lh_trefoil import all_voicings_for_root, all_voicings_above
    lh_used=[]; rh_used=[]; lh_prev=None; rh_prev=None; table_rows=[]
    for seg_name, roots in TREFOIL:
        for root in roots:
            root_idx = ROOT_MAP[root]
            lh_voicings = all_voicings_for_root(root_idx)
            lh_best = max(lh_voicings, key=lambda v: score_voicing(v, lh_prev, lh_used, ALL_PATTERNS))
            lh_used.append(lh_best['pattern'])
            lh_prev = lh_best['strings']
            lh_top  = lh_best['strings'][-1]
            rh_voicings = all_voicings_above(lh_top, root_idx, lh_best['pattern'])
            if not rh_voicings:
                rh_voicings = all_voicings_above(lh_top, root_idx, None)
            rh_best = max(rh_voicings, key=lambda v: score_rh_voicing(v, rh_prev, rh_used))
            rh_used.append(rh_best['pattern'])
            rh_prev = rh_best['strings']
            gap = rh_best['strings'][0] - lh_best['strings'][-1] - 1
            table_rows.append({
                'seg':      seg_name,
                'root':     root,
                'lh_pat':   lh_best['pattern'],
                'rh_pat':   rh_best['pattern'],
                'gap':      gap,
                'lh_notes': lh_best['notes'],
                'rh_notes': rh_best['notes'],
            })

    out_dir = './output'
    trefoil_pdf = './trefoil.pdf'

    pairs = [(KEYS[i], KEYS[i+1]) for i in range(0, 8, 2)]

    music_pdfs = []
    table_pdfs = []

    for page_num, ((k1_name, k1_abc, k1_trans), (k2_name, k2_abc, k2_trans)) in enumerate(pairs, 1):
        print(f"\nPage {page_num}: {k1_name} + {k2_name}")

        # ── Music page ──────────────────────────────────────────────────────
        abc_path = f'./trefoil_{k1_name}_{k2_name}.abc'
        ps_path  = f'./trefoil_{k1_name}_{k2_name}.ps'

        preamble = '\n'.join([
            '%%encoding utf-8',
            '%%staffsep 35','%%sysstaffsep 0',
            '%%topmargin 0.5cm','%%botmargin 0.5cm',
            '%%leftmargin 0.8cm','%%rightmargin 0.8cm',
            '%%pagewidth 21cm','%%pageheight 29.7cm',
            '%%titlefont Times-Bold 16',
            '%%titlespace 3','%%musicspace 2','%%barsperline 8',
        ])

        tune1 = make_abc_tune(1, k1_name, k1_abc, k1_trans, results)
        tune2 = make_abc_tune(2, k2_name, k2_abc, k2_trans, results)
        full_abc = preamble + '\n\n' + tune1 + '\n\n' + tune2 + '\n'

        with open(abc_path, 'w') as f: f.write(full_abc)

        r = subprocess.run(['abcm2ps', '-O', ps_path, abc_path],
                           capture_output=True, text=True)
        errs = [l for l in r.stderr.split('\n') if 'error' in l.lower()]
        if errs: print(f"  ABC errors: {errs}")

        music_raw = f'./trefoil_music_{k1_name}_{k2_name}.pdf'
        subprocess.run(['gs','-dNOPAUSE','-dBATCH','-sDEVICE=pdfwrite',
                        f'-sOutputFile={music_raw}', ps_path],
                       capture_output=True)

        # Stamp trefoil at bottom
        music_reader   = PdfReader(music_raw)
        trefoil_reader = PdfReader(trefoil_pdf)
        music_page = music_reader.pages[0]
        tpage      = trefoil_reader.pages[0]
        mw = float(music_page.mediabox.width)
        mh = float(music_page.mediabox.height)
        tw = float(tpage.mediabox.width)
        th = float(tpage.mediabox.height)
        margin_pt = 15.0
        avail_h   = mh - 437 - margin_pt*2
        avail_w   = mw - margin_pt*2
        scale     = min(avail_h/th, avail_w/tw)
        x_offset  = (mw - tw*scale)/2
        y_offset  = margin_pt - 36

        music_page.merge_transformed_page(tpage,
            [scale,0,0,scale,x_offset,y_offset])

        writer = PdfWriter()
        writer.add_page(music_page)
        music_out = f'{out_dir}/trefoil_music_{k1_name}_{k2_name}.pdf'
        with open(music_out,'wb') as f: writer.write(f)
        music_pdfs.append(music_out)
        print(f"  Music: {music_out}")

        # MIDIs
        for k_name, k_trans in [(k1_name, k1_trans), (k2_name, k2_trans)]:
            midi_out = f'{out_dir}/trefoil_{k_name}_strum.mid'
            make_midi_file(k_name, k_trans, results, midi_out)

        # ── Table page ──────────────────────────────────────────────────────
        table_out = f'{out_dir}/trefoil_table_{k1_name}_{k2_name}.pdf'
        page_w, page_h = letter
        margin = 0.25*inch
        cv = rl_canvas.Canvas(table_out, pagesize=letter)
        cv.setTitle(f'Harp Trefoil Drill — {k1_name} and {k2_name}')
        draw_table(cv, table_rows, k1_name, k1_trans, k2_name, k2_trans,
                   margin, page_h-margin, page_w, page_h, margin)
        cv.save()
        table_pdfs.append(table_out)
        print(f"  Table: {table_out}")

    # ── Combine into 2 books: music book + table book ────────────────────────
    for label, pdfs in [('music', music_pdfs), ('tables', table_pdfs)]:
        writer = PdfWriter()
        for path in pdfs:
            for page in PdfReader(path).pages:
                writer.add_page(page)
        out = f'{out_dir}/trefoil_book_{label}.pdf'
        with open(out,'wb') as f: writer.write(f)
        print(f"\nBook: {out}")

if __name__ == '__main__':
    main()
