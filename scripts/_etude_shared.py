"""Shared HTML template for etude*.html — derived from harpdrills.html.

Each etude HTML is a clone of handout/harpdrills.html with:
- The ETUDE array replaced with the variant's sequence
- Default key changed to Eb (from G)
- Title updated

All rendering (canvas grand staff) and audio (Web Audio, strum/gliss/block)
comes from harpdrills.html unchanged — no abc2svg dependency.
"""

import os
import re

KEY_PC = {-3: 3, -1: 10, 0: 0, 2: 2, 4: 4, 5: 5, 7: 7, 9: 9}
KEY_ABC = {-3: 'Eb', -1: 'Bb', 0: 'C', 2: 'D', 4: 'E', 5: 'F', 7: 'G', 9: 'A'}

HARPDRILLS_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'handout', 'harpdrills.html'
)


def _etude_to_js(etude):
    """Convert Python ETUDE list to harpdrills-style JS array source."""
    lines = ['const ETUDE = [']
    for e in etude:
        parts = []
        if 's' in e:
            # Escape ' and \ in section labels
            s = e['s'].replace('\\', '\\\\').replace("'", "\\'")
            # Encode non-ASCII as \uXXXX so the JS source remains ASCII-safe
            s = ''.join(
                c if ord(c) < 128 else f'\\u{ord(c):04x}' for c in s
            )
            parts.append(f"s:'{s}'")
        if 'l' in e:
            p, d = e['l']
            parts.append(f"l:{{p:'{p}',d:{d}}}")
        if 'r' in e:
            p, d = e['r']
            parts.append(f"r:{{p:'{p}',d:{d}}}")
        lines.append('  {' + ', '.join(parts) + '},')
    lines.append('];')
    return '\n'.join(lines)


def generate_html(abc_text, key_root, etude, title='Etude'):
    """Generate an etude HTML by templating harpdrills.html."""
    with open(HARPDRILLS_PATH) as f:
        content = f.read()

    # Replace ETUDE array
    etude_js = _etude_to_js(etude)
    new_content, n = re.subn(
        r'const ETUDE = \[.*?\n\];',
        lambda _: etude_js,
        content,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise RuntimeError(
            f'Could not find ETUDE array in {HARPDRILLS_PATH}'
        )
    content = new_content

    # Change key selection: remove existing 'selected' and add to the target key
    content = content.replace(' selected>G</option>', '>G</option>')
    content = content.replace('<option value="7">G</option>',
                              '<option value="7">G</option>')
    target_opt = f'<option value="{key_root}">'
    target_new = f'<option value="{key_root}" selected>'
    # Only replace the first occurrence to avoid touching any other option lists
    content = content.replace(target_opt, target_new, 1)

    # Update page title
    content = re.sub(
        r'<title>[^<]*</title>',
        f'<title>{title}</title>',
        content,
        count=1,
    )

    return content
