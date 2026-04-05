# Trefoil — Lever Harp Hymnal App

A WebView Android tablet app for lever harp practice with scrolling music notation (strip chart style), diatonic chord voicings, and technical exercises.

## Contents

- **app/** — Android app (WebView + abc2svg). Package: `com.harp.trefoil`.
  - 282 hymns with melody + RH/LH diatonic chord accompaniment
  - 291 Thomas 280 technical exercises
  - 102 Rodriguez advanced scale exercises
  - 35 lever harp technique exercises
- **scripts/** — Build pipeline and utilities
  - chord_name.py — terse chord naming algorithm
  - build_harp_hymnal.py — SSAATTBB to harp RH/LH
  - optimize_harp_voicings.py — enforce 10-string span, reduce dissonance
  - build_hymnal_v3.py — generate app JSON
  - build_ssaattbb.py — SATB to 8-voice (Claude API)
  - Drill builders (thomas_280, advanced, lever)
- **handout/** — Output files and reference materials
  - harp_hymnal/ — 282 ABC+HTML hymn files
  - Voicing tables, TiKZ diagrams, PDFs
- **data/** — Source ABC files (OpenHymnal SATB)

## Build

```bash
# App
cd app
ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk

# Harp hymnal pipeline
python3 scripts/build_harp_hymnal.py
python3 scripts/optimize_harp_voicings.py
ai-tar handout/harp_hymnal/ --include-ext .abc --output handout/harp_hymnal.tmd

# Handout
cd handout
pdflatex trefoil.tex
python3 trefoil_all_keys_local.py
```
