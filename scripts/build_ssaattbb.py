#!/usr/bin/env python3
"""Expand SATB hymns to SSAATTBB using Claude API and the arranging prompt."""

import os
import sys
import glob
import time
import re
from pathlib import Path

import anthropic

PROJECT = Path(__file__).parent.parent
INPUT_DIR = PROJECT / 'handout/ssaattbb'
OUTPUT_DIR = PROJECT / 'handout/ssaattbb_out'
PROMPT_FILE = PROJECT / 'handout/ssaattbb_prompt.md'

OUTPUT_DIR.mkdir(exist_ok=True)

# Load the arranging prompt
with open(PROMPT_FILE) as f:
    base_prompt = f.read()

# Get all input files sorted
input_files = sorted(glob.glob(str(INPUT_DIR / '*.abc')))
print(f"Found {len(input_files)} hymns to process", file=sys.stderr)

client = anthropic.Anthropic()

done = 0
errors = 0

for i, filepath in enumerate(input_files):
    fname = os.path.basename(filepath)
    outpath = OUTPUT_DIR / fname

    # Skip if already processed
    if outpath.exists() and outpath.stat().st_size > 100:
        done += 1
        continue

    with open(filepath) as f:
        abc_input = f.read()

    # Build the full prompt with the ABC appended
    full_prompt = base_prompt.replace(
        '[PASTE ABC CONTENT HERE]',
        abc_input
    )
    # If placeholder wasn't found, just append
    if abc_input not in full_prompt:
        full_prompt = base_prompt + '\n\n' + abc_input

    print(f"[{i+1}/{len(input_files)}] {fname}...", end='', flush=True, file=sys.stderr)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[{"role": "user", "content": full_prompt}]
        )

        response_text = message.content[0].text

        # Extract ABC block from response
        # Look for ABC between ```abc or ``` markers, or starting with X:
        abc_match = re.search(r'```(?:abc)?\s*\n(X:.*?)```', response_text, re.DOTALL)
        if abc_match:
            abc_out = abc_match.group(1).strip()
        else:
            # Try to find raw ABC starting with X:
            abc_match = re.search(r'^(X:\s*\d+.*?)(?=\n[A-Z]{2,}:|\nTRANSPOSITION|\nHARMONIC|\nDIATONIC|\nTEXTURE|\nUNISON|\nRANGE|\nRULE|\Z)',
                                  response_text, re.MULTILINE | re.DOTALL)
            if abc_match:
                abc_out = abc_match.group(1).strip()
            else:
                abc_out = response_text  # save full response

        # Save ABC output
        with open(outpath, 'w') as f:
            f.write(abc_out + '\n')

        # Save full response (with arranger notes) alongside
        notes_path = OUTPUT_DIR / fname.replace('.abc', '_notes.txt')
        with open(notes_path, 'w') as f:
            f.write(response_text)

        done += 1
        print(f" done ({message.usage.input_tokens}+{message.usage.output_tokens} tokens)", file=sys.stderr)

    except anthropic.RateLimitError:
        print(" rate limited, waiting 60s...", file=sys.stderr)
        time.sleep(60)
        continue
    except Exception as e:
        print(f" ERROR: {e}", file=sys.stderr)
        errors += 1
        continue

    # Small delay to avoid rate limits
    time.sleep(1)

print(f"\nDone: {done} processed, {errors} errors", file=sys.stderr)
