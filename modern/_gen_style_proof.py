"""Generate modern/style_proof.ly -- a visual sanity proof showing 12
sample chord fractions rendered with the current chord_overlay styling.

python3.10; ASCII source. The output .ly file is UTF-8 and may contain
Unicode glyphs in markup strings (via escape sequences routed through
chord_overlay).

Usage:
    python3.10 -m modern._gen_style_proof
    lilypond -o modern/style_proof modern/style_proof.ly
"""

from __future__ import annotations

import os
from modern.chord_overlay import fraction_markup

OUT_PATH = os.path.join(os.path.dirname(__file__), "style_proof.ly")

PAIRS = [
    ("V7",    "I"),
    ("iim7",  "V"),
    ("vii07", "vi"),
    ("IM7",   "ii"),
    ("IV",    "I"),
    ("Is4",   "V"),
    ("iiim7", "IV"),
    ("viio",  "I"),
    ("IVM7",  "V7"),
    ("iim11", "V7"),
    ("vi",    "iii"),
    ("V",     "I"),
]


def build() -> str:
    out = []
    out.append('\\version "2.22.0"')
    out.append('')
    out.append('#(set-default-paper-size "letter")')
    out.append('')
    out.append('\\paper {')
    out.append('  top-margin = 1.5\\cm')
    out.append('  bottom-margin = 1.5\\cm')
    out.append('  left-margin = 2.0\\cm')
    out.append('  right-margin = 2.0\\cm')
    out.append('  between-system-padding = 0.4\\cm')
    out.append('  #(define fonts')
    out.append('     (make-pango-font-tree')
    out.append('       "TeX Gyre Pagella"')
    out.append('       "TeX Gyre Pagella"')
    out.append('       "TeX Gyre Cursor"')
    out.append('       (/ staff-height pt 20)))')
    out.append('}')
    out.append('')
    out.append(
        '\\markup { \\override #\'(font-name . "TeX Gyre Pagella Bold") '
        '\\fontsize #4 "Chord-fraction style proof" }'
    )
    out.append(
        '\\markup { \\vspace #0.4 '
        '\\override #\'(font-name . "TeX Gyre Pagella") '
        '\\fontsize #0 "Navy RH over burgundy LH; TeX Gyre Pagella Bold; '
        'Unicode quality glyphs (Delta, degree, o-slash); tightened kern." }'
    )
    out.append('\\markup { \\vspace #1.2 }')

    for rh, lh in PAIRS:
        fm = fraction_markup(rh, lh)
        # fm looks like '\markup { ... }' -- strip the outer wrapper so
        # we can concat a label next to it.
        assert fm.startswith('\\markup { ') and fm.endswith(' }')
        inner = fm[len('\\markup { '):-len(' }')]

        ascii_label = '%s / %s' % (rh, lh)
        out.append(
            '\\markup { \\hspace #2 \\line { '
            '\\override #\'(font-name . "TeX Gyre Pagella") '
            '\\fontsize #0 "%s   " '
            '%s '
            '} \\vspace #0.6 }' % (ascii_label, inner)
        )

    return '\n'.join(out) + '\n'


def main():
    src = build()
    with open(OUT_PATH, 'w', encoding='utf-8') as fh:
        fh.write(src)
    print('wrote %s (%d bytes)' % (OUT_PATH, len(src)))


if __name__ == '__main__':
    main()
