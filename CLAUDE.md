# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Trefoil — harp practice strip chart app with trefoil chord voicing system. WebView Android tablet app (abc2svg) plus drill handout generation.

## Structure

- `abc2stripchart/` — WebView Android app. Package: `com.harp.stripchart`.
- `handout/` — Trefoil drill generation: chord_name.py (terse naming algorithm), trefoil.tex (TiKZ diagram), trefoil_all_keys_local.py (ReportLab tables + abcm2ps notation), trefoil_C.json (voicing table).
- `data/` — OpenHymnal SATB ABC source (293 hymns).
- `scripts/` — build_hymnal_v3.py (music21), build_thomas_280.py, build_advanced_drills.py, build_lever_drills.py.

## App Build

```bash
cd abc2stripchart
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Handout Build

```bash
cd handout
pdflatex trefoil.tex
python3 trefoil_all_keys_local.py
# Output in handout/output/
```

## Hymnal Rebuild

```bash
python3 scripts/build_hymnal_v3.py
# Outputs abc2stripchart/hymnal_data.json
```

## Key Concepts

- **Trefoil voicing table**: 48 LH/RH chord pairs, all asymmetric patterns, all 12 finger patterns used. `handout/chord_name.py` is the authoritative terse naming algorithm.
- **Two-pass voicing assignment**: Dissonant voicings placed in accidental measures first.
- **Music21**: For proper ABC parsing (barlines, pickups, compound meters).
- **Key signature**: pitch_to_abc omits accidentals already in key signature.
- **Pedal harp range**: A2 to D6 (hymns), C1 to G7 (instrument). 29-string span for trefoil voicings.
