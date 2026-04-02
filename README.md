# Trefoil — Harp Practice Strip Chart App

A WebView Android tablet app for practicing harp with scrolling music notation (strip chart style), trefoil chord voicings, and technical exercises.

## Contents

- **abc2stripchart/** — Android app (WebView + abc2svg)
  - 279 hymns with trefoil RH/LH chord voicings
  - 291 Thomas 280 technical exercises
  - 102 Rodriguez advanced scale exercises  
  - 35 lever harp technique exercises
  - 24 Grossi/Rodriguez/trefoil drills
- **handout/** — Trefoil drill reference materials
  - Voicing tables for all 8 keys (ReportLab PDF)
  - Music notation (abc2svg + abcm2ps)
  - TiKZ trefoil diagram
  - chord_name.py — terse naming algorithm
- **data/** — Source ABC files (OpenHymnal SATB)
- **scripts/** — Build scripts (music21, Python)

## Build

```bash
# App
cd abc2stripchart
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk

# Handout
cd handout
pdflatex trefoil.tex
python3 trefoil_all_keys_local.py
```
