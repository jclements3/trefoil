#!/usr/bin/env python3
"""Insert the 20 cascades into the Trefoil app as individual hymns.

For each cascade we emit one standalone MEI document (one <measure>,
grand staff, hidden-bracket tuplet -- same machinery as the handout
booklet's cascades_sheet), paired with a minimal ABC fallback entry in
ssaattbb_data.json. Titles get a zero-padded prefix like "000 ..." so
they sort before the hymnal in the navigator.

Updates in place:
  app/ssaattbb_data.json                 (+ app/app/src/main/assets/)
  app/tch_ssaattbbp_mei.json             (+ app/app/src/main/assets/)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_cascades_mei import (
    parse_cascades, build_cascade_measure,
)

N_START = 901            # cascades occupy n=901..920 in ssaattbb_data
N_MEI_START = 4901       # n=4901..4920 in tch_ssaattbbp_mei.json
KEY = 'Eb'
TEMPO = 100
KEY_SIG_MAP = {'C': '0', 'G': '1s', 'D': '2s', 'A': '3s', 'E': '4s',
               'F': '1f', 'Bb': '2f', 'Eb': '3f'}


def make_cascade_mei_doc(cascade, measure_id, key=KEY):
    """Wrap build_cascade_measure in a standalone <mei> document."""
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


def placeholder_abc(title, key):
    """Minimal ABC shown only if the MEI fails to load."""
    return (
        f'X: 1\nT: {title}\nM: 4/4\nL: 1/8\nQ: 1/4={TEMPO}\n'
        f'K: {key}\n'
        '%%score (1 2)\n'
        'V:1 clef=treble\nV:2 clef=bass\n'
        '[V:1] z8 |]\n[V:2] z8 |]\n'
    )


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))


def upsert(data, entry, key_field='n'):
    """Replace any existing entry with the same n, then append new ones."""
    existing_ns = {e[key_field] for e in data}
    if entry[key_field] in existing_ns:
        for i, e in enumerate(data):
            if e[key_field] == entry[key_field]:
                data[i] = entry
                return
    data.append(entry)


def main():
    root = os.path.abspath(os.path.join(HERE, '..'))
    tex_path = os.path.join(root, 'handout', 'cascades.tex')
    cascades = parse_cascades(tex_path)
    if len(cascades) != 20:
        print(f"WARN: expected 20 cascades, got {len(cascades)}")

    ssaattbb_path = os.path.join(root, 'app', 'ssaattbb_data.json')
    mei_path = os.path.join(root, 'app', 'tch_ssaattbbp_mei.json')
    ssaattbb = load_json(ssaattbb_path)
    mei_list = load_json(mei_path)

    def n_of(e):
        try:
            return int(e.get('n', 0))
        except (ValueError, TypeError):
            return 0
    # Strip any previous cascade entries so re-running is idempotent.
    ssaattbb = [e for e in ssaattbb if not (N_START <= n_of(e) <= N_START + 99)]
    mei_list = [e for e in mei_list if not (N_MEI_START <= n_of(e) <= N_MEI_START + 99)]

    for i, c in enumerate(cascades):
        # 4-digit zero-pad: "0001 ..."..."0020 ...". Existing hymn titles
        # use 3-digit prefixes ("001 ..."), so ANY 4-digit cascade prefix
        # sorts before all of them (char 2: '0' < '1'..'3').
        num = f"{i + 1:04d}"
        title = f"{num} {c['title']}"
        clean_title = c['title']
        ssaattbb_entry = {
            'n': N_START + i,
            't': title,
            'abc': placeholder_abc(title, KEY),
            'key': KEY,
            'violations': 0,
            'bars': 1,
            'bpb': 4,
            'tempo': TEMPO,
        }
        mei_entry = {
            'n': N_MEI_START + i,
            't': title,
            'key': KEY,
            'tempo': TEMPO,
            'mei': make_cascade_mei_doc(c, measure_id=i + 1, key=KEY),
        }
        upsert(ssaattbb, ssaattbb_entry)
        upsert(mei_list, mei_entry)

    save_json(ssaattbb_path, ssaattbb)
    save_json(mei_path, mei_list)

    # Mirror to app/app/src/main/assets for the APK.
    assets_dir = os.path.join(root, 'app', 'app', 'src', 'main', 'assets')
    for src in (ssaattbb_path, mei_path):
        dst = os.path.join(assets_dir, os.path.basename(src))
        with open(src, 'rb') as fi, open(dst, 'wb') as fo:
            fo.write(fi.read())

    print(f"Added {len(cascades)} cascades to ssaattbb_data.json and tch_ssaattbbp_mei.json")
    print(f"Titles: {ssaattbb[-20]['t']} ... {ssaattbb[-1]['t']}")


if __name__ == '__main__':
    main()
