#!/usr/bin/env python3
"""Insert the 20 cascades into the Trefoil app as a separate "Drills"
library, not mixed in with the hymns.

Outputs:
  app/cascades_data.json            - list entry per cascade (n, t, key, tempo)
                                      drives the library when mode = "drills"
  app/tch_ssaattbbp_mei.json        - contains the per-cascade MEI at n=4901..4920
                                      (rendered via Verovio when mode = "drills"
                                       or "tch-ssaattbb")
  app/ssaattbb_data.json            - cascades STRIPPED from here; hymns only

Both data files mirrored to app/app/src/main/assets/.

Per-cascade MEI is a standalone <mei> doc with one measure, hidden-bracket
tuplet, grand staff, Eb key.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_cascades_mei import parse_cascades, build_cascade_measure

N_MEI_START = 4901            # cascade MEI n=4901..4920 in tch_ssaattbbp_mei.json
KEY = 'Eb'
TEMPO = 100
KEY_SIG_MAP = {'C': '0', 'G': '1s', 'D': '2s', 'A': '3s', 'E': '4s',
               'F': '1f', 'Bb': '2f', 'Eb': '3f'}


def make_cascade_mei_doc(cascade, measure_id, key=KEY):
    key_sig = KEY_SIG_MAP[key]
    measure = build_cascade_measure(cascade, measure_id, key=key)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<mei xmlns="http://www.music-encoding.org/ns/mei">\n'
        f'<meiHead><fileDesc><titleStmt><title>{cascade["title"]}</title></titleStmt>\n'
        '<pubStmt/></fileDesc></meiHead>\n'
        '<music><body><mdiv><score>\n'
        f'<scoreDef meter.count="4" meter.unit="4" key.sig="{key_sig}">\n'
        '<staffGrp symbol="brace">\n'
        f'<staffDef n="1" lines="5" clef.shape="G" clef.line="2"><keySig sig="{key_sig}"/></staffDef>\n'
        f'<staffDef n="2" lines="5" clef.shape="F" clef.line="4"><keySig sig="{key_sig}"/></staffDef>\n'
        '</staffGrp>\n</scoreDef>\n'
        f'<section>{measure}</section>\n'
        '</score></mdiv></body></music>\n</mei>\n'
    )


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))


def n_int(e):
    try:
        return int(e.get('n', 0))
    except (ValueError, TypeError):
        return 0


def main():
    root = os.path.abspath(os.path.join(HERE, '..'))
    tex_path = os.path.join(root, 'handout', 'cascades.tex')
    cascades = parse_cascades(tex_path)

    ssaattbb_path = os.path.join(root, 'app', 'ssaattbb_data.json')
    mei_path = os.path.join(root, 'app', 'tch_ssaattbbp_mei.json')
    cascades_path = os.path.join(root, 'app', 'cascades_data.json')

    ssaattbb = load_json(ssaattbb_path)
    mei_list = load_json(mei_path)

    # Purge cascades from hymns (previous placement at n=901..920)
    ssaattbb = [e for e in ssaattbb if not (900 <= n_int(e) <= 999)]
    # Purge previous cascade MEI entries
    mei_list = [e for e in mei_list if not (4900 <= n_int(e) <= 4999)]

    cascades_data = []
    for i, c in enumerate(cascades):
        # Drill-library entry: plain title, ordered by n.
        cascades_data.append({
            'n': i + 1,
            't': c['title'],
            'subtitle': c['subtitle'],
            'key': KEY,
            'tempo': TEMPO,
        })
        # MEI entry (looked up by cleaned title when rendering)
        mei_list.append({
            'n': N_MEI_START + i,
            't': c['title'],
            'key': KEY,
            'tempo': TEMPO,
            'mei': make_cascade_mei_doc(c, measure_id=i + 1, key=KEY),
        })

    save_json(ssaattbb_path, ssaattbb)
    save_json(mei_path, mei_list)
    save_json(cascades_path, cascades_data)

    # Mirror to the APK assets dir
    assets_dir = os.path.join(root, 'app', 'app', 'src', 'main', 'assets')
    for src in (ssaattbb_path, mei_path, cascades_path):
        dst = os.path.join(assets_dir, os.path.basename(src))
        with open(src, 'rb') as fi, open(dst, 'wb') as fo:
            fo.write(fi.read())

    print(f"Wrote {len(cascades)} cascades to cascades_data.json")
    print(f"Added MEI for {len(cascades)} cascades to tch_ssaattbbp_mei.json (n={N_MEI_START}..)")
    print(f"Removed any prior cascade entries from ssaattbb_data.json")


if __name__ == '__main__':
    main()
