#!/usr/bin/env python3
"""Build Tch-SSAATTBBP arrangements via Claude API.

Sends each lead sheet (melody + chord annotations) through the
tch_ssaattbbp_prompt.md arranging prompt to produce MEI output
for Verovio rendering. The Claude API composes proper voice leading
using the handout chord table as the harmonic vocabulary.

Usage:
    python3.10 scripts/build_tch_ssaattbbp.py          # all hymns
    python3.10 scripts/build_tch_ssaattbbp.py 4001      # single hymn by n
    python3.10 scripts/build_tch_ssaattbbp.py --dry-run  # show what would be sent
"""

import json, os, re, sys, time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
LEAD_SHEETS = ROOT / 'app' / 'lead_sheets.json'
PROMPT_FILE = ROOT / 'handout' / 'tch_ssaattbbp_prompt.md'
OUTPUT_DIR = ROOT / 'handout' / 'tch_ssaattbbp_out'
COMBINED_OUTPUT = ROOT / 'app' / 'tch_ssaattbbp_mei.json'

OUTPUT_DIR.mkdir(exist_ok=True)

# Load the arranging prompt
prompt_template = PROMPT_FILE.read_text()

# Load lead sheets
lead_sheets = json.loads(LEAD_SHEETS.read_text())
print(f'Loaded {len(lead_sheets)} lead sheets')

# Parse args
dry_run = '--dry-run' in sys.argv
single_n = None
for arg in sys.argv[1:]:
    if arg.isdigit():
        single_n = int(arg)

client = anthropic.Anthropic()

done = 0
errors = 0
skipped = 0

for i, ls in enumerate(lead_sheets):
    n = ls['n']
    if single_n is not None and str(n) != str(single_n):
        continue

    outpath = OUTPUT_DIR / f'{n}.mei'

    # Skip if already processed
    if outpath.exists() and outpath.stat().st_size > 200 and single_n is None:
        done += 1
        continue

    # Build the full prompt with the ABC
    full_prompt = prompt_template.replace('[PASTE ABC CONTENT HERE]', ls['abc'])

    print(f'[{i+1}/{len(lead_sheets)}] {ls["t"]} (n={n})...', end='', flush=True)

    if dry_run:
        print(f' DRY RUN ({len(full_prompt)} chars)')
        # Show first hymn's full prompt
        if i == 0 or n == single_n:
            print('--- PROMPT ---')
            print(full_prompt[:500])
            print('...')
        continue

    try:
        message = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=16384,
            messages=[{'role': 'user', 'content': full_prompt}]
        )

        response_text = message.content[0].text

        # Extract MEI from response — look for <?xml or <mei tags
        mei_match = re.search(
            r'(<\?xml.*?</mei>|<mei\b.*?</mei>)',
            response_text,
            re.DOTALL
        )
        if mei_match:
            mei_out = mei_match.group(1)
        else:
            # Try code block
            code_match = re.search(r'```(?:xml|mei)?\s*\n(.*?)```', response_text, re.DOTALL)
            if code_match:
                mei_out = code_match.group(1).strip()
            else:
                mei_out = response_text
                print(' [WARNING: no MEI found, saving raw response]', end='')

        outpath.write_text(mei_out)

        # Also save arranger notes (everything after the MEI)
        notes_match = re.search(r'</mei>\s*(.*)', response_text, re.DOTALL)
        if notes_match and notes_match.group(1).strip():
            notes_path = OUTPUT_DIR / f'{n}_notes.txt'
            notes_path.write_text(notes_match.group(1).strip())

        done += 1
        tokens_in = message.usage.input_tokens
        tokens_out = message.usage.output_tokens
        print(f' OK ({tokens_in}+{tokens_out} tokens, {len(mei_out)} chars)')

        # Rate limit: ~1 request per 2 seconds
        time.sleep(2)

    except Exception as e:
        errors += 1
        print(f' ERROR: {e}')
        time.sleep(5)

print(f'\nDone: {done} processed, {errors} errors, {skipped} skipped')

# Combine all MEI files into a single JSON for the app
if not dry_run:
    print('\nCombining MEI files...')
    results = []
    for ls in lead_sheets:
        n = ls['n']
        outpath = OUTPUT_DIR / f'{n}.mei'
        if outpath.exists() and outpath.stat().st_size > 200:
            mei_text = outpath.read_text()
            results.append({
                'n': n,
                't': ls['t'],
                'key': ls['key'],
                'tempo': 100,
                'mei': mei_text,
            })
    COMBINED_OUTPUT.write_text(json.dumps(results, ensure_ascii=False))
    print(f'Combined {len(results)} hymns → {COMBINED_OUTPUT} ({COMBINED_OUTPUT.stat().st_size // 1024} KB)')
