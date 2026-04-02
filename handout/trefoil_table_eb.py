"""
Harp Trefoil Drill Table — C and Eb on one page, single table.
Shared columns: # Root LH-Pat Gap RH-Pat
Paired columns: LH(C) LH(Eb) LH-Notes(C) LH-Notes(Eb) | RH(C) RH(Eb) RH-Notes(C) RH-Notes(Eb)
"""

import sys
sys.path.insert(0, '/home/claude')

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from lh_trefoil import (all_voicings_for_root, all_voicings_above,
    score_voicing, score_rh_voicing, ROOT_MAP, TREFOIL, ALL_PATTERNS)
from chord_name import name_voicing

FONT_PATH = '/usr/share/fonts/truetype/dejavu/'
pdfmetrics.registerFont(TTFont('DejaVu',     FONT_PATH + 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuBold', FONT_PATH + 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuMono', FONT_PATH + 'DejaVuSansMono.ttf'))

SUP_MAP = {'¹':'1','²':'2','³':'3','⁴':'4'}
TRANS_EB = {'C':'E','D':'F','E':'G','F':'A','G':'B','A':'C','B':'D'}

# Trefoil colors matching the diagram
SEG_COLORS = {
    'CW4':  colors.HexColor('#BE9B1E'),  # yellow — 4ths
    'CCW4': colors.HexColor('#BE9B1E'),
    'CW3':  colors.HexColor('#DC4B4B'),  # red — 3rds
    'CCW3': colors.HexColor('#DC4B4B'),
    'CW2':  colors.HexColor('#28B4BE'),  # cyan — 2nds
    'CCW2': colors.HexColor('#28B4BE'),
}

SEG_TEXT_COLORS = {
    'CW4':  colors.black,
    'CCW4': colors.black,
    'CW3':  colors.white,
    'CCW3': colors.white,
    'CW2':  colors.black,
    'CCW2': colors.black,
}

# Alternating row tints per segment
SEG_ALT_COLORS = {
    'CW4':  colors.HexColor('#FDF8E1'),
    'CCW4': colors.HexColor('#FDF8E1'),
    'CW3':  colors.HexColor('#FDE8E8'),
    'CCW3': colors.HexColor('#FDE8E8'),
    'CW2':  colors.HexColor('#E0F7F8'),
    'CCW2': colors.HexColor('#E0F7F8'),
}

def strip_sup(s):
    for u, d in SUP_MAP.items():
        if u in s: return s.replace(u,''), d
    return s, None

def draw_chord_name(c, x, y, name, font='DejaVu', size=10):
    base, sup = strip_sup(name)
    c.setFont(font, size)
    c.drawString(x, y, base)
    if sup:
        w = pdfmetrics.stringWidth(base, font, size)
        c.setFont(font, size * 0.65)
        c.drawString(x + w, y + size * 0.4, sup)

def build_results():
    lh_used = []; rh_used = []
    lh_prev = None; rh_prev = None
    results = []
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
            eb_root = TRANS_EB[root]
            lh_eb = [TRANS_EB[n] for n in lh_best['notes']]
            rh_eb = [TRANS_EB[n] for n in rh_best['notes']]
            results.append({
                'seg': seg_name, 'root': root,
                'lh':        name_voicing(lh_best['notes'], root),
                'rh':        name_voicing(rh_best['notes'], root),
                'lh_eb':     name_voicing(lh_eb, eb_root),
                'rh_eb':     name_voicing(rh_eb, eb_root),
                'lh_notes':  ''.join(lh_best['notes']),
                'rh_notes':  ''.join(rh_best['notes']),
                'lh_notes_eb': ''.join(lh_eb),
                'rh_notes_eb': ''.join(rh_eb),
                'lh_pat': lh_best['pattern'],
                'rh_pat': rh_best['pattern'],
                'gap': rh_best['gap'],
            })
    return results

def generate():
    results = build_results()
    out_path = '/mnt/user-data/outputs/trefoil_drill_eb.pdf'
    page_w, page_h = letter
    margin = 0.18 * inch

    # Column definitions — proportional minimums, scaled to fill page
    # Exact minimum widths from worst-case content measurement at render font size
    col_min_pts = {
        '#':           0.092,
        'Root':        0.105,
        'LHpat':       0.192,
        'Gap':         0.092,
        'RHpat':       0.192,
        'LH C':        0.546,
        'RH C':        0.591,
        'LH Notes C':  0.242,
        'RH Notes C':  0.242,
        'LH Eb':       0.583,
        'RH Eb':       0.591,
        'LH Notes Eb': 0.242,
        'RH Notes Eb': 0.242,
    }
    cols = list(col_min_pts.keys())
    avail = page_w - 2 * margin
    scale = avail / (sum(col_min_pts.values()) * inch)
    col_w = {k: v * inch * scale for k, v in col_min_pts.items()}
    table_w = sum(col_w.values())
    x_off = margin

    # Row height calculation
    seg_h = 12; col_h = 11; gap_h = 3
    fixed = (seg_h + col_h + gap_h) * 6
    avail_rows = page_h - 2 * margin - fixed
    row_h = avail_rows / 48
    font_size = max(5.5, row_h - 2.0)

    cv = canvas.Canvas(out_path, pagesize=letter)
    cv.setTitle("Harp Trefoil Drill - C and Eb")

    y = page_h - margin

    for seg_name, roots in TREFOIL:
        seg_rows = [r for r in results if r['seg'] == seg_name]

        # Segment header
        seg_color = SEG_COLORS[seg_name]
        seg_text_color = SEG_TEXT_COLORS[seg_name]
        cv.setFillColor(seg_color)
        cv.rect(x_off, y - seg_h, table_w, seg_h, fill=1, stroke=0)
        cv.setFillColor(seg_text_color)
        cv.setFont('DejaVuBold', 7.5)
        cv.drawString(x_off + 3, y - 8, seg_name)
        cv.setFillColor(colors.black)
        y -= seg_h

        # Column header
        cv.setFillColor(colors.HexColor('#cccccc'))
        cv.rect(x_off, y - col_h, table_w, col_h, fill=1, stroke=0)
        cv.setFillColor(colors.black)
        col_labels = {
            '#': '#', 'Root': 'Root', 'LHpat': 'LH Pat', 'Gap': 'G', 'RHpat': 'RH Pat',
            'LH C': 'LH Chord C', 'RH C': 'RH Chord C', 'LH Notes C': 'LH Notes C', 'RH Notes C': 'RH Notes C',
            'LH Eb': 'LH Chord Eb', 'RH Eb': 'RH Chord Eb', 'LH Notes Eb': 'LH Notes Eb', 'RH Notes Eb': 'RH Notes Eb',
        }
        cv.setFont('DejaVu', 5.5)
        xi = x_off + 2
        for col in cols:
            cv.drawString(xi, y - 8, col_labels[col])
            xi += col_w[col]
        y -= col_h

        # Data rows
        alt = SEG_ALT_COLORS[seg_name]
        for i, row in enumerate(seg_rows):
            if i % 2 == 0:
                cv.setFillColor(alt)
                cv.rect(x_off, y - row_h, table_w, row_h, fill=1, stroke=0)
            cv.setFillColor(colors.black)

            ty = y - row_h + (row_h - font_size) / 2
            xi = x_off + 2

            # #
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.grey)
            cv.drawString(xi, ty, str(i + 1))
            cv.setFillColor(colors.black)
            xi += col_w['#']

            # Root
            cv.setFont('DejaVuBold', font_size)
            cv.drawString(xi, ty, row['root'])
            xi += col_w['Root']

            # LH Pat
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#444444'))
            cv.drawString(xi, ty, row['lh_pat'].replace('-',''))
            cv.setFillColor(colors.black)
            xi += col_w['LHpat']

            # Gap
            cv.setFont('DejaVuBold', font_size)
            cv.drawString(xi, ty, str(row['gap']))
            xi += col_w['Gap']

            # RH Pat
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#444444'))
            cv.drawString(xi, ty, row['rh_pat'].replace('-',''))
            cv.setFillColor(colors.black)
            xi += col_w['RHpat']

            # LH C
            draw_chord_name(cv, xi, ty, row['lh'], 'DejaVuBold', font_size)
            xi += col_w['LH C']

            # RH C
            draw_chord_name(cv, xi, ty, row['rh'], 'DejaVuBold', font_size)
            xi += col_w['RH C']

            # LH Notes C
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#666666'))
            cv.drawString(xi, ty, row['lh_notes'])
            cv.setFillColor(colors.black)
            xi += col_w['LH Notes C']

            # RH Notes C
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#666666'))
            cv.drawString(xi, ty, row['rh_notes'])
            cv.setFillColor(colors.black)
            xi += col_w['RH Notes C']

            # LH Eb
            draw_chord_name(cv, xi, ty, row['lh_eb'], 'DejaVuBold', font_size)
            xi += col_w['LH Eb']

            # RH Eb
            draw_chord_name(cv, xi, ty, row['rh_eb'], 'DejaVuBold', font_size)
            xi += col_w['RH Eb']

            # LH Notes Eb
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#666666'))
            cv.drawString(xi, ty, row['lh_notes_eb'])
            cv.setFillColor(colors.black)
            xi += col_w['LH Notes Eb']

            # RH Notes Eb
            cv.setFont('DejaVuMono', font_size - 0.5)
            cv.setFillColor(colors.HexColor('#666666'))
            cv.drawString(xi, ty, row['rh_notes_eb'])
            cv.setFillColor(colors.black)

            y -= row_h

        y -= gap_h

    # Bottom line
    cv.setStrokeColor(colors.black)
    cv.line(x_off, y, x_off + table_w, y)

    cv.showPage()
    cv.save()
    print(f"Saved: {out_path}")

if __name__ == '__main__':
    generate()
