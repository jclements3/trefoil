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

- **Save inline scripts**: The lead sheet builder and hymnal builder (v5g) are inline python in the conversation history. Save as `scripts/build_lead_sheets.py` and `scripts/build_hymnal_v5.py`. The pattern drill builder is also inline — save as `scripts/build_pattern_drills.py`.
- **Voicing variety (next step)**: Current v5g cycles through C-to-C windows when same chord repeats at measure boundaries. Future: assign unique (LH shape, RH shape) pairs so no voicing repeats across the entire hymnal. See memory file `project_lead_sheet_voicings.md` for the full design.
- **Legacy pipeline**: Do not use. v5 pipeline replaces it entirely.
- **Build the APK**: The laptop can't build or deploy to tablet. Run `cd app && ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug && adb install app/build/outputs/apk/debug/app-debug.apk`

## App structure changes (2026-04-05)

### Drills are now hymnal entries
All drills moved from embedded JS `DRILLS` array and external JSON files into `hymnal_data.json` with n < 4000. The `DRILLS` array in index.html is empty. External drill JSON files (`advanced_drills.json`, `lever_drills.json`, `thomas_280.json`) are emptied.

- Threshold in index.html: n < 4000 = drills tab, n >= 4000 = hymns tab
- Drills tab uses two-column layout (`drill-col-left`, `drill-col-right` inside `drill-list`)

### Pattern drills (53 voicing patterns)
- `app/pattern_index.json` — master list of 53 unique (LH, RH) voicing patterns with diatonic spacings, gap, key, count, and hex IDs (XXXX-XXXX format: 4 digits per hand, 0=unused finger)
- Drill n=3200: "53 Patterns" — all patterns in key of G starting at G2, grand staff, triple fraction annotations (abstract chord / RH voicing name / LH voicing name)
- Drills n=3100-3107: per-key pattern drills — **only patterns that actually appear in hymns of that key**, sorted by frequency. E.g. "G (40 patterns)" = the 40 hand shapes you'll encounter in G-key hymns.
- Pattern counts per key: Eb(26) Bb(28) F(36) C(31) G(40) D(34) A(21) E(13). 42 shared across keys, 11 unique to one key.
- All pattern drills use 3/4 time, half-note chord + quarter rest per measure (gives room for annotations)
- Sorted: 53 Patterns first, then Eb→Bb→F→C→G→D→A→E (lever harp progression)

### LH voicing rules
- Bottom intervals: P4/P5/P8+ only (no 2nds or 3rds in bass — too muddy)
- Top note of LH may form m3/M3 with note below (acceptable near middle C)
- Target 3-4 notes. Open voicing: root-5th-octave-3rd typical.
- LH intervals verified: P4 32%, P5 33%, zero 2nds, 3rds only 13% (top note only)

## Current Pipeline (v5g — 2026-04-05)

Algorithm:
1. Parse all SATB voices from OpenHymnal with music21 (`python3.10` required)
2. Transpose Ab→G, Db→D for lever harp range (Eb to E, 3 flats to 4 sharps)
3. At beat 1 of each measure, collect all SATB pitches → `music21.chord.Chord` → absolute chord name (D, Am, G7)
4. **C-to-C voicing**: filter diatonic scale for chord PCs within harp range (C2=36 to G5=79)
5. **Open LH** (bass clef, up to D4=62): bottom 2-3 notes spaced by P4/P5+ only (no 2nds or 3rds in bass). 4th note allowed as m3/M3 from top note only (less muddy near middle C). Typical: root-5th-octave-3rd.
6. **Close RH** (treble clef): 3 consecutive chord tones above LH top. 3rds OK in treble register.
7. **One chord per measure**: harp plays downbeat harmony only, no mid-measure voice leading.
8. **Measure-boundary shift**: when same chord repeats into next measure, advance voicing window up the harp. Resets to center when chord changes.
9. Melody preserves fractional ABC durations (3/2, /2); harp snaps to whole L-units only (no slashes).

### LH voicing rules (critical)
- **Bottom intervals must be P4(5), P5(7), m6(8), M6(9), m7(10), P8(12) or wider**
- **No m2(1), M2(2), m3(3), M3(4) between bottom notes** — too muddy in bass register
- **Top note of LH may form m3/M3 with note below** — acceptable near middle C
- Target 3-4 notes per LH hand. If only root+5th pass the filter, that's 2 notes (acceptable).

Stats: 288 hymns, 1 chord/measure, 0 crossings, LH intervals: P4 32%, P5 33%, m6 11%, 3rds only 13% (top note only), zero 2nds.

## Lab/Home Sync Protocol

This repo is worked on from two machines (lab and home laptop) with separate Claude Code agents. **CLAUDE.md is the communication channel between agents.**

### Rules for EVERY session (both machines):
1. **At session end**: `git add -A && git commit && git push` — always. No exceptions.
2. **Write a sync note below** describing what was done, what's pending, and any instructions for the other agent.
3. **At session start**: `git pull` before doing anything.

### Pending sync notes (newest first):

**Home → Lab (2026-04-10):**
- **drill.tar.gz is incomplete.** User said it would contain a chord table page + composition notes page alongside `drill.abc`/`drill.pdf`/`generate_drill.py`, but only the drill music (13 pages of chord drill) is in there. No chord table, no composition notes.
- **Action for Home Claude next session**: rebuild `drill.tar.gz` to include the corrected chord table (as PDF or ABC) AND the composition notes page. Lab needs these to generate a new handout.pdf.
- **The corrected chord table** lives in `generate_drill.py` inside the tarball — `CHORD_NAMES` and `VALID` dicts. This is the authoritative version and should replace `data/diatonic_chord_table.md`. Please also export a typeset 1-page PDF of it.
- **Composition notes**: whatever page of notes goes with the chord table — user referred to "two pages of chord table and composition notes" so there's a second page I don't have. Please include it.
- Once the tarball has all three pieces (chord table PDF, composition notes PDF, drill PDF), Lab can assemble `handout.pdf`.

**Lab → Home (2026-04-09, end of session):**
- **Tchaikovsky mode** is the main new feature. Tch checkbox (defaults checked) toggles between SSAATTBB score and Tchaikovsky arpeggio runs.
- **Simplified notation**: block chords with arpeggio marks (3 per measure: start, peak, end). NOT individual run notes — the player sweeps through chord tones to fill the measure. Like orchestral harp shorthand.
- **Chord fractions**: JS overlay (not ABC annotations). Ascending chords (bold blue 8px) over descending chords (gray 8px) with divider line. Positioned per-measure using barline gap detection.
- **4-chord runs**: Each measure picks 4 chords from the diatonic chord table (14 patterns × 7 degrees). A>B ascending, C>D descending. Chords labeled with proper notation: I¹, vii°, viiø7, Iq, I+9, I9-3/I9-5.
- **`%%score 1 {2 3}`** aligns melody + grand staff barlines. All voices at same L unit.
- **33-string harp range**: C2 to G6 (MIDI 36-91). Octave mapping fixed: C4 = middle C = `C` in ABC.
- **Landscape mode**: AndroidManifest `screenOrientation="unspecified"`.
- **Chord table PDF**: `data/diatonic_chord_table.pdf` — printable reference card.
- **New files**: `scripts/build_tchaikovsky_hymnal.py`, `app/tchaikovsky_data.json`, `data/diatonic_chord_table.md`, `data/diatonic_chord_table.pdf`, `MANTRA.md`
- **abc2stripchart/** dir was accidentally committed (build artifacts). Add to .gitignore if desired.
- **TODO**: First-measure fraction positioning still slightly off on pickup bars. Fraction font could be Times New Roman if serif doesn't render well on home laptop.

---

## Recent Changes (2026-04-09)

- **Tchaikovsky mode**: Checkbox "Tch" in toolbar toggles between regular SSAATTBB score and Tchaikovsky-style arpeggio runs. Runs sweep the full 33-string lever harp (C2 to G6) with 4-chord transitions per measure.
- **Tchaikovsky data**: `app/tchaikovsky_data.json` (288 hymns). Built by `scripts/build_tchaikovsky_hymnal.py` from `app/lead_sheets.json` chord annotations + diatonic chord table patterns.
- **Tchaikovsky run algorithm**: For each measure, picks 4 chords from the chord table pool: A (ascending bass) > B (ascending treble) / C (descending treble) > D (descending bass). Chord A from current measure, B from color pairing, C/D from next measure's chord. Uses `%%score 1 {2 3}` for melody + grand staff alignment. All voices at L:1/64 with melody durations rescaled. Runs repeat to fill the measure. Invisible rests (x) where one staff is idle.
- **Diatonic chord table**: `data/diatonic_chord_table.md` — 14 patterns x 7 degrees. Degree + finger pattern = chord address. Notation: I¹ (inversions), vii° (diminished), viiø7 (half-dim), Iq (quartal), I+9 (add9), I9-3/I9-5 (9th omissions).
- **Chord labels**: Times Roman font (`%%gchordfont`), above melody staff. Format: `I¹>vim / iim6>iiq` (ascending chords > descending chords). Slash separates up/down. `>` separates chord transitions within a direction.
- **8va/8vb**: Notes above A5 get 8va marking, notes at C2 get 8vb. Keeps notation readable across full harp range.
- **Note counts**: Below each bar on bass staff, showing actual notes in the run.
- **Landscape mode**: AndroidManifest changed from `portrait` to `unspecified`. Landscape works well for Tchaikovsky strip charts.
- **Harp range**: Updated from G5 to G6 (33 strings). Octave mapping fixed: C4 = middle C = `C` in ABC.
- **Pickup bar handling**: Harp runs truncated to match melody bar duration for barline alignment.
- **Equalbars removed**: Script tag removed, scroll sync is precomputed.
- **Practice mantra**: `MANTRA.md` — 15-point form checklist (height, posture, shoulders, arms, elbows, wrists, hands, thumbs, fingers, nails, breathing, harp angle, feet, closing, tension).

## Changes (2026-04-06)

- **App now loads SSAATTBB data** (`ssaattbb_data.json`, 276 hymns) instead of old `hymnal_data.json`. Five voices: Melody, RH1 (moving), RH2 (sustained), LH1 (moving), LH2 (sustained). Old hymnal data still on disk but not loaded.
- **On-the-fly drill generation**: No pre-built drill files. Parses RH2/LH2 brackets from each hymn, generates block/arpeggio/run/flip exercises as grand staff strip charts in the hymn's key. Renders in score area when clicked.
- **Hymns/Drills toggle**: Single button switches bottom panel between hymn TOC and drill list.
- **Chord fraction overlays**: Abstract chord (blue), RH chord (green), LH chord (gray) computed on-the-fly from ABC annotations and bracket notes. JS chord identifier handles major/minor/dim/aug/7th/sus chords.
- **Pattern hex encoding**: `pattern_index.json` updated. Digits = interval names (3rd=3, 4th=4). First digit = scale degree of RH thumb. E.g. `533-3333` = start on 5th, all thirds.
- **UI restructure**: Title on own row. Toolbar: [Hymns/Drills toggle] [key filters] [Search] [Recent dropdown]. |< >| scroll 3/4 screen. |<< >>| navigate drills or hymns by mode. Melody toggle. Score 45vh. Playhead line removed (scroll sync unreliable with multi-voice). Hymn TOC sorted by name (strips number prefix), headers start collapsed.
- **Local preview**: Port 8080 is Traefik — use `python3 -m http.server 9090 --directory app` → localhost:9090
- **Mic chroma scoring**: Still present, untested on real harp.

## Previous Changes (2026-04-05)

- v5g pipeline, Eb enharmonic fix, barline alignment, mic chroma scoring added. See git log for details.
