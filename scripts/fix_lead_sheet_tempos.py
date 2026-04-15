#!/usr/bin/env python3.10
"""
One-shot fixer: replace hard-coded `Q: 1/4=100` in app/lead_sheets.json
with the real per-hymn tempo from data/OpenHymnal.abc.

Mapping: lead_sheets `n` == OpenHymnal `X:` + 4000.
Authoritative tempo: first `[Q:1/4=N]` inline tag in the hymn body.
"""
import json
import re
import sys
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENHYMNAL = ROOT / 'data' / 'OpenHymnal.abc'
LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
MIRROR = ROOT / 'app' / 'app' / 'src' / 'main' / 'assets' / 'lead_sheets.json'


def parse_openhymnal_tempos(path):
    """Return {X_number: first_Q_bpm}."""
    tempos = {}
    current_x = None
    x_re = re.compile(r'^X:\s*(\d+)\s*$')
    q_re = re.compile(r'\[Q:1/4=(\d+)\]')
    text = path.read_text()
    for line in text.splitlines():
        m = x_re.match(line)
        if m:
            current_x = int(m.group(1))
            continue
        if current_x is None:
            continue
        if current_x in tempos:
            continue
        qm = q_re.search(line)
        if qm:
            tempos[current_x] = int(qm.group(1))
    return tempos


def patch_entry_abc(abc, new_tempo):
    """Replace the `Q: 1/4=NNN` line in an ABC body."""
    pattern = re.compile(r'^Q:\s*1/4=\d+\s*$', re.MULTILINE)
    replacement = f'Q: 1/4={new_tempo}'
    new_abc, n = pattern.subn(replacement, abc, count=1)
    return new_abc, n


def main():
    print(f'Reading {OPENHYMNAL}...', flush=True)
    x_to_tempo = parse_openhymnal_tempos(OPENHYMNAL)
    print(f'  {len(x_to_tempo)} hymns with [Q:1/4=...] tags', flush=True)

    print(f'Reading {LEAD_SHEETS}...', flush=True)
    data = json.loads(LEAD_SHEETS.read_text())
    print(f'  {len(data)} lead sheet entries', flush=True)

    updated = 0
    unchanged = 0
    no_match = []
    no_q_line = []
    tempos_applied = []
    default_used = []

    for entry in data:
        n = int(entry['n'])
        x = n - 4000
        if x in x_to_tempo:
            tempo = x_to_tempo[x]
        else:
            tempo = 100
            default_used.append(n)
            no_match.append(n)
        new_abc, count = patch_entry_abc(entry['abc'], tempo)
        if count == 0:
            no_q_line.append(n)
            continue
        if new_abc != entry['abc']:
            entry['abc'] = new_abc
            updated += 1
        else:
            unchanged += 1
        tempos_applied.append(tempo)

    print(f'\nUpdated: {updated}')
    print(f'Unchanged (already correct): {unchanged}')
    print(f'No Q: line in ABC (skipped): {len(no_q_line)} {no_q_line[:10]}')
    print(f'No X-match in OpenHymnal (defaulted to 100): {len(default_used)} {default_used}')

    if tempos_applied:
        t = sorted(tempos_applied)
        print('\nTempo distribution:')
        print(f'  min={t[0]} median={statistics.median(t)} max={t[-1]} mean={statistics.mean(t):.1f}')
        # histogram buckets
        buckets = [(40, 60), (60, 80), (80, 100), (100, 120), (120, 140), (140, 160), (160, 200), (200, 260)]
        print('  Histogram:')
        for lo, hi in buckets:
            c = sum(1 for v in t if lo <= v < hi)
            bar = '#' * c
            print(f'    [{lo:3d}-{hi:3d}): {c:3d} {bar}')

    # write back
    LEAD_SHEETS.write_text(json.dumps(data, ensure_ascii=False))
    print(f'\nWrote {LEAD_SHEETS}')

    # mirror
    if MIRROR.exists() or MIRROR.parent.exists():
        MIRROR.parent.mkdir(parents=True, exist_ok=True)
        MIRROR.write_text(json.dumps(data, ensure_ascii=False))
        print(f'Mirrored to {MIRROR}')


if __name__ == '__main__':
    main()
