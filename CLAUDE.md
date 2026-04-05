# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Trefoil — lever harp hymnal app. 288 OpenHymnal hymns: melody + diatonic RH/LH chord accompaniment from SATB. WebView Android tablet app (abc2svg) plus drill handout generation.

## Architecture (v4 — 2026-04-05)

Two-pipeline system:
1. **Lead sheets** (`app/lead_sheets.json`): melody + absolute chord symbols from SATB. Built by inline python3.10 script (music21). Chords computed using music21 chord recognition (not best_name). Keys outside lever harp range (Ab, Db) transposed to G, D.
2. **Harp hymnal** (`app/hymnal_data.json`): melody staff + RH/LH grand staff. SA voices → RH (treble clef, C4+), TB voices → LH (bass clef, below C4). One fill note per hand from chord tones. Beat-quantized: harp re-articulates only on beat boundaries, sustains when notes are identical. Pickup measures use actual duration from music21.

### Key design decisions
- **Absolute chord names**: music21 `chord.Chord.commonName` gives D, Am, G7 etc. (NOT relative/transposed-to-C).
- **Lever harp keys**: Eb, Bb, F, C, G, D, A, E only. 22 hymns transposed.
- **No crossing**: RH always above LH. SA octave-shifted up if below C4, TB shifted down if above B3.
- **Duration syntax**: melody preserves fractional ABC durations (3/2, /2). Harp snaps to whole L-units only (no slashes).
- **Sustain**: harp only re-articulates when the actual MIDI pitch set changes, not on repeated notes.
- **Voice formats handled**: S1V1/S1V2/S2V1/S2V2, S1/S2 (chord brackets), S1/S2V1/S2V2, 5-voice layouts.

## Structure

- `app/` — Android WebView app. Package: `com.harp.trefoil`.
  - `lead_sheets.json` — 288 lead sheets: melody + chord symbols (no RH/LH)
  - `lead.html` — Local browser viewer for lead sheets
  - `hymnal_data.json` — 288 hymns: melody + RH/LH grand staff + chord symbols
- `scripts/` — Build pipeline and shared code:
  - `chord_name.py` — Terse chord naming for voicing labels (symlinked from handout/)
  - `build_harp_hymnal_v4.py` — Lead sheets → hymnal JSON with voicing pairs (STALE — current build is inline in conversation, needs to be saved to this file)
  - `build_ssaattbb.py` — SATB → 8-voice SSAATTBB (Claude API, Sonnet) — legacy pipeline
  - `build_harp_hymnal.py` — SSAATTBB → harp hymnal — legacy pipeline, has LH/RH duration bug (RH/LH durations at L:1/4 but header says L:1/8)
  - `optimize_harp_voicings.py` — Post-processor — legacy pipeline, has melody-chord clash fix
  - `build_hymnal_v3.py` — Trefoil voicing table builder — DO NOT USE for hymnal rebuild (destroys SSAATTBB voicings, wrong L: unit, missing key field)
  - `build_thomas_280.py`, `build_advanced_drills.py`, `build_lever_drills.py` — Drill JSON builders
  - `render_ssaattbb_html.py` — HTML preview renderer for SSAATTBB
- `handout/` — Outputs: harp_hymnal/ (288 ABC+HTML), ssaattbb_out/ (8-voice ABC), harp_hymnal.tmd (packed archive), trefoil_C.json (voicing table), trefoil.tex (TiKZ), output/ (PDFs).
- `data/` — OpenHymnal SATB ABC source (288 hymns).

## App Build

```bash
cd app
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Harp Hymnal Build Pipeline (v4 — current)

```bash
# Step 1: Build lead sheets from OpenHymnal SATB (requires python3.10 + music21)
# Currently an inline script — needs to be saved to scripts/build_lead_sheets.py
# Reads data/OpenHymnal.abc, writes app/lead_sheets.json
# Transposes Ab→G, Db→D for lever harp range
# Uses music21 chord recognition for absolute chord names

# Step 2: Build hymnal from lead sheets
# Currently an inline script — needs to be saved to scripts/build_hymnal_v4.py
# Reads lead_sheets.json + OpenHymnal.abc, writes hymnal_data.json + HTML
# SA→RH, TB→LH, +1 fill note, beat-quantized, sustain on identical
```

## Legacy Pipeline (SSAATTBB — do not use without fixes)

```bash
# KNOWN BUGS: build_harp_hymnal.py has L:1/8 vs L:1/4 duration mismatch in RH/LH
# KNOWN BUGS: build_hymnal_v3.py destroys voicings, use only for trefoil table approach
python3 scripts/build_harp_hymnal.py       # SSAATTBB → harp hymnal (duration bug)
python3 scripts/optimize_harp_voicings.py  # post-process (melody-chord clash fix applied)
```

## Handout Build

```bash
cd handout
pdflatex trefoil.tex
python3 trefoil_all_keys_local.py
# Output in handout/output/
```

## Key Concepts

- **v4 pipeline**: OpenHymnal SATB → music21 parse → transpose to lever key → SA→RH, TB→LH → fill +1 chord tone per hand → beat-quantize → sustain identical chords → ABC output. No SSAATTBB step needed.
- **Diatonic only**: RH/LH accompaniment uses only diatonic notes in the key. Melody staff may have accidentals.
- **Hand constraints**: Max 12-string span per hand (diatonic steps). Target 3 notes RH, 3-4 notes LH. LH carries heavier voicing. Hands never cross — LH always bass clef (C2-B3), RH always treble clef (C4+).
- **Chord annotations**: Absolute chord names (D, Am, G7) above melody at measure boundaries using music21 chord recognition. NOT roman numerals, NOT transposed-to-C.
- **C-to-C frame**: chord tones fall on fixed string positions within each C-to-C octave on the harp. 21 chord shapes cover 95% of all instances. With inversions and 12-string span, 4,760+ unique voicings per triad — enough to never repeat across the hymnal.
- **Voicing variety goal**: infinite variety for practice. Every chord instance should ideally get a unique (LH, RH) voicing. The point of the hymnal is drilling all possible chord shapes, not settling into one habit.
- **Music21**: Required. Use `python3.10` on this machine. Install: `pip install music21`.
- **Chord naming**: `scripts/chord_name.py` for terse voicing labels (best_name, roman_name). Used for RH/LH voicing names, NOT for abstract chord symbols (those come from music21).
- **Lever harp keys**: Eb, Bb, F, C, G, D, A, E only (3 flats to 4 sharps). Hymns in Ab/Db transposed.
- **Local preview**: `cd app && python3 -m http.server 8080` then open `localhost:8080` (hymnal) or `localhost:8080/lead.html` (lead sheets).

## TODO for lab (Claude AI)

- **Save inline scripts**: The lead sheet builder and hymnal builder (v5d) are inline python in the conversation. Save as `scripts/build_lead_sheets.py` and `scripts/build_hymnal_v5.py`.
- **Voicing variety (next step)**: Current v5d cycles through C-to-C windows when same chord repeats at measure boundaries. Future: assign unique (LH shape, RH shape) pairs so no voicing repeats across the entire hymnal. See memory file `project_lead_sheet_voicings.md` for the full design — 21 chord shapes, 4,760+ voicings per triad, 435K total available vs 9K needed.
- **Legacy pipeline**: Do not use. Has duration bugs, melody-chord clashes, wrong rebuild script. v5 pipeline replaces it entirely.

## Current Pipeline (v5d — 2026-04-05)

Algorithm:
1. Parse all SATB voices from OpenHymnal with music21
2. Transpose Ab→G, Db→D for lever harp range
3. At each beat, collect all SATB pitches → music21 chord recognition → absolute chord name
4. **C-to-C voicing**: filter scale for chord PCs, find 7 consecutive chord tones centered near middle C, bottom 4 → LH, top 3 → RH. Hands 0-3 strings apart, never crossing.
5. Beat-quantize: one chord per beat max, sustain when pitches identical
6. **Measure-boundary shift**: when same chord repeats into next measure, advance to next voicing window (shifts up the harp). Resets to center when chord changes.
7. Melody preserves fractional ABC durations; harp snaps to whole L-units only.

Stats: 288 hymns, 2.2 chords/measure, 0 crossings, avg 1.5 string gap, 3% consecutive dupes.

## Recent Changes (2026-04-05)

- **New v5d pipeline**: SATB → music21 chord ID → C-to-C voicing, bypassing SSAATTBB
- C-to-C frame: 7 consecutive chord tones centered near middle C, split bottom 4 LH / top 3 RH
- Zero hand crossings, 0-3 string gap between hands (avg 1.5)
- Measure-boundary voicing shift: same chord in consecutive measures gets different window position
- 288 lead sheets with absolute chord names (D, Am, G7 not roman numerals)
- 22 hymns transposed from Ab/Db to lever harp range (G/D)
- Beat-quantized harp, clean integer durations (no slashes), sustain on identical pitches
- Pickup measure alignment from actual music21 measure duration
- Local preview: `cd app && python3 -m http.server 8080` → localhost:8080
