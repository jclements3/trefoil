#!/usr/bin/env python3
"""Helper: print the full composition prompt for a given hymn number.
Usage: python3.10 scripts/compose_hymn.py 4022
"""
import json, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ls_data = json.loads((ROOT / 'app' / 'lead_sheets.json').read_text())
prompt = (ROOT / 'handout' / 'tch_ssaattbbp_prompt.md').read_text()

n = sys.argv[1]
hymn = next((h for h in ls_data if str(h['n']) == n), None)
if not hymn:
    print(f'Hymn {n} not found', file=sys.stderr)
    sys.exit(1)

abc = hymn['abc']
key = hymn['key']

# Determine key sig and accid.ges needs
KEY_SIG = {'C':'0','G':'1s','D':'2s','A':'3s','E':'4s','F':'1f','Bb':'2f','Eb':'3f'}
KEY_ACCID = {
    'C': {}, 'G': {'f':'s'}, 'D': {'f':'s','c':'s'}, 'A': {'f':'s','c':'s','g':'s'},
    'E': {'f':'s','c':'s','g':'s','d':'s'}, 'F': {'b':'f'}, 'Bb': {'b':'f','e':'f'},
    'Eb': {'b':'f','e':'f','a':'f'},
}

ks = KEY_SIG.get(key, '0')
accid_notes = KEY_ACCID.get(key, {})
accid_desc = ', '.join(f'{k.upper()}→accid.ges="{v}"' for k,v in accid_notes.items()) if accid_notes else 'none'

# Get time sig
ts_match = re.search(r'M:\s*(\d+/\d+)', abc)
ts = ts_match.group(1) if ts_match else '4/4'
ts_num, ts_den = ts.split('/')
beats = int(ts_num) * 4 // int(ts_den)

# Count measures
bars = [b.strip() for b in re.split(r'\|', abc.split('K:')[1]) if b.strip() and any(c in b for c in 'ABCDEFGabcdefg')]

print(f"""COMPOSE: {hymn['t']} (n={n})
Key: {key} ({ks}), accid.ges needed: {accid_desc}
Time: {ts}, {len(bars)} measures
Beats per measure: {beats} quarter notes

ABC:
{abc}
""")
