# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Trefoil — lever harp hymnal app. 282 OpenHymnal hymns arranged for melody + diatonic RH/LH chord accompaniment. WebView Android tablet app (abc2svg) plus drill handout generation.

## Structure

- `app/` — Android WebView app. Package: `com.harp.trefoil`.
- `scripts/` — Build pipeline: chord_name.py (terse naming), build_harp_hymnal.py (SSAATTBB → harp), optimize_harp_voicings.py (span/dissonance), build_hymnal_v3.py (app JSON), build_ssaattbb.py (Claude API), drill builders.
- `handout/` — Outputs: harp_hymnal/ (282 ABC+HTML), ssaattbb_out/ (8-voice ABC), trefoil_C.json (voicing table), trefoil.tex (TiKZ), output/ (PDFs).
- `data/` — OpenHymnal SATB ABC source (293 hymns).

## App Build

```bash
cd app
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Harp Hymnal Build

```bash
# Full pipeline: SSAATTBB → harp hymnal → optimize → archive
python3 scripts/build_harp_hymnal.py
python3 scripts/optimize_harp_voicings.py
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

- **Harp voicing pipeline**: OpenHymnal SATB → SSAATTBB (8-voice, Claude API) → sort by pitch → split RH (upper) / LH (lower, comma notes) → optimize (max 10-string span, no accidentals in RH/LH, wider intervals).
- **Chord naming**: `scripts/chord_name.py` is the authoritative terse naming algorithm. Roman numerals + inversions + modifications.
- **Diatonic only**: RH/LH accompaniment uses only diatonic notes in the key. Melody may have accidentals.
- **Music21**: For proper ABC parsing (barlines, pickups, compound meters).
- **Key signature**: pitch_to_abc omits accidentals already in key signature.
- **Lever harp range**: Practical range for hymns. Max 10-string span per hand.
