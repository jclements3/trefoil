# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Trefoil — lever harp hymnal app. 282 OpenHymnal hymns arranged for melody + diatonic RH/LH chord accompaniment. WebView Android tablet app (abc2svg) plus drill handout generation.

## Structure

- `app/` — Android WebView app. Package: `com.harp.trefoil`. (Renamed from `abc2stripchart/` and `com.harp.stripchart` on 2026-04-04. Uninstall old package before installing: `adb uninstall com.harp.stripchart`.)
- `scripts/` — Build pipeline and shared code:
  - `chord_name.py` — Authoritative terse chord naming (symlinked from handout/ for compatibility)
  - `build_ssaattbb.py` — SATB → 8-voice SSAATTBB (Claude API, Sonnet)
  - `build_harp_hymnal.py` — SSAATTBB → melody + RH/LH harp hymnal (music21)
  - `optimize_harp_voicings.py` — Post-process: enforce 10-string span, strip accidentals from RH/LH, reduce dissonance, wider intervals, recalculate chord fraction annotations
  - `build_hymnal_v3.py` — Harp hymnal → app JSON (hymnal_data.json)
  - `build_thomas_280.py`, `build_advanced_drills.py`, `build_lever_drills.py` — Drill JSON builders
  - `render_ssaattbb_html.py` — HTML preview renderer for SSAATTBB
- `handout/` — Outputs: harp_hymnal/ (282 ABC+HTML), ssaattbb_out/ (8-voice ABC), harp_hymnal.tmd (packed archive), trefoil_C.json (voicing table), trefoil.tex (TiKZ), output/ (PDFs).
- `data/` — OpenHymnal SATB ABC source (293 hymns).

## App Build

```bash
cd app
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Harp Hymnal Build Pipeline

```bash
# Full pipeline: SSAATTBB → harp hymnal → optimize → archive
python3 scripts/build_harp_hymnal.py       # reads ssaattbb_out/, writes harp_hymnal/
python3 scripts/optimize_harp_voicings.py  # post-processes harp_hymnal/ in-place
ai-tar handout/harp_hymnal/ --include-ext .abc --output handout/harp_hymnal.tmd
```

## Hymnal App JSON Rebuild

```bash
python3 scripts/build_hymnal_v3.py
# Outputs app/hymnal_data.json
```

## Handout Build

```bash
cd handout
pdflatex trefoil.tex
python3 trefoil_all_keys_local.py
# Output in handout/output/
```

## Key Concepts

- **Harp voicing pipeline**: OpenHymnal SATB → SSAATTBB (8-voice, Claude API) → sort all concurrent pitches by MIDI → split bottom half to LH, top half to RH (LH gets extra on odd count) → optimize (max 10-string span, no accidentals in RH/LH, wider intervals, 6-8 notes per chord).
- **SSAATTBB purpose**: The 8 voices exist to create 6-8 note diatonic chord stacks. Voice crossing is allowed — they're compositional, not register-bound. The voices get re-sorted by pitch before the RH/LH split.
- **Diatonic only**: RH/LH accompaniment uses only diatonic notes in the key. Melody staff may have accidentals. The optimizer strips any accidentals that leak into RH/LH from the SSAATTBB.
- **Hand constraints**: Max 10-string span per hand (diatonic steps, inclusive). No adjacent-step clusters within a hand. Target 3-4 notes per hand (6-8 total).
- **Chord fraction annotations**: Each measure's first beat is annotated with three labels above the melody: abstract Roman numeral chord name, RH voicing name, LH voicing name. Computed by `chord_name.py` functions `roman_name()` and `best_name()`.
- **Chord naming**: `scripts/chord_name.py` is the authoritative terse naming algorithm. Roman numerals + inversions + modifications. Used by build_harp_hymnal.py, build_hymnal_v3.py, optimize_harp_voicings.py.
- **Music21**: Required for ABC parsing (barlines, pickups, compound meters). Install: `pip install music21`. Use `python3.10` if default python lacks it.
- **ai-tar**: Archive tool at `~/.local/bin/ai-tar`. Creates `.tmd` files using FS/RS delimiters. Usage: `ai-tar <dir> --include-ext .abc --output file.tmd`.
- **Key signature**: pitch_to_abc omits accidentals already in key signature.
- **Lever harp range**: Practical range for hymns. Max 10-string span per hand.

## Recent Changes (2026-04-04)

- Fixed 5 truncated SSAATTBB hymns (Be Thou My Vision, For All The Saints, Faith of Our Fathers, Blest Be The Tie That Binds, All Who Believe and Are Baptized) — measures were dropped by Claude API generation
- Added `optimize_harp_voicings.py` post-processor: enforces 10-string span, strips RH/LH accidentals, reduces cluster dissonance, recalculates chord annotations
- Renamed `abc2stripchart/` → `app/`, package `com.harp.stripchart` → `com.harp.trefoil`
- Major cleanup: deleted stale scripts (v0/v1/v2 builders), broken Python files, redundant directories (harphymnal/, ssaa_ttbb/, ssaattbb/), debug logs, LaTeX artifacts
- Moved `chord_name.py` from handout/ to scripts/ (symlink remains for compatibility)
