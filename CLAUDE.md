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

**Lab → Home (2026-04-11, late session):**
- **BIG CHANGE: Tch mode now uses the full handout chord table (inversions!).** Previously every Tch chord was either row `33` (plain triad) or row `333` (root-pos 7th) — only 14 of 82 handout entries ever appeared. Now 75 of 82 appear, with 2,418 of 10,891 labels (22%) carrying an inversion superscript. See "Inversion detection pipeline" below for the full architecture.
- **ALSO this session (earlier):** circled-digit chord labels, minor `m` markers, thin-space kerning, nested `<keySig>` fix, 220px label font, CSS font-family override. All in one APK on the tablet now.

### Inversion detection pipeline (new 2026-04-11)

**`scripts/build_satb_chord_index.py`** (~250 lines, new):
- Parses `data/OpenHymnal.abc` per-voice with music21. OpenHymnal uses `%%combinevoices 1` which defeats music21's automatic voice splitter — you MUST manually extract [V: S1V1] / [V: S1V2] / [V: S2V1] / [V: S2V2] blocks and feed each voice as a separate ABC stream. `split_voices()` does this: walks header lines until `K:`, then for each voice filters body lines matching `[V: <vid>]`, strips the tag, feeds to `converter.parse(abc_text, format='abc')`.
- For each hymn, detects original SATB key via `parts[0].analyze('key')`, computes `transpose_off = (lead_key_pc - orig_key_pc) % 12` (normalised to ±6 semitones) so the 22 Ab→G / Db→D hymns get transposed consistently.
- Walks every unique note onset across all 4 voices. At each onset uses **binary search** per voice for the "most recent note ≤ offset" (the `sounding_at()` closure inside `analyze_hymn`) to build a 4-voice slice. Builds a `music21.chord.Chord` from the slice and computes `{root_pc, bass_pc, quality, seventh, inv}` from pitch-class intervals:
  - third: 3rd = `m`, 4th = `M`
  - fifth: 7 = `P`, 6 = `d`, 8 = `A`
  - seventh: 10 = `min`/dom, 11 = `maj`/Δ
  - inv: `bass_pc - root_pc mod 12` → 0/3-4/6-7-8/10-11 maps to inversion 0/1/2/3
- Dedupe consecutive events with identical `(root, bass, quality, seventh)` tuple.
- Computes `deg` = Ionian scale degree of root in the **lead-sheet key** (transposed pc).
- Output: `app/satb_chord_index.json` keyed by `str(hymn.n)` → list of event dicts. ~1.3 MB. **280/287 hymns** analyzed; 7 skipped for title mismatches against OpenHymnal (whitespace/punct differences — low priority to fix).
- Rerun: `python3.10 scripts/build_satb_chord_index.py` (takes ~2 minutes, music21 parsing dominates).

**`scripts/build_tchaikovsky_hymnal.py::chord_to_spec` — extended:**
- New helper `_pick_row_deg(chord_deg, has_7th, inv)` returns `(pattern_str, row_deg)` for the handout table. Formulas verified against the 14×7 entries in `CHORD_NAMES`:
  - triad root: `('33', cd)`
  - triad 1st inv: `('43', ((cd + 3) % 7) + 1)`
  - triad 2nd inv: `('34', ((cd + 1) % 7) + 1)`
  - 7th root: `('333', cd)`
  - 7th 1st inv: `('233', ((cd - 2) % 7) + 1)`
  - 7th 2nd inv: `('323', ((cd - 4) % 7) + 1)`
  - 7th 3rd inv (cd ∈ {1,4,5} only): `('332', ((cd + 1) % 7) + 1)`
  - Fallthrough: root pos of matching family
- `chord_to_spec(chord_str, key, inv_hint=None)` now accepts an optional `{'inv': 0..3, 'seventh': None|'min'|'maj'}` dict. CRITICAL: `start_string = deg_to_first_string(key, row_deg)` — it's anchored to the *row_deg*, not *chord_deg*, so inversions drive **different sweeps**, not just different labels. This is the mechanism by which the Tch runs re-voice per the user's spec.
- Falls back along: `row_deg not in VALID[pat]` → root-pos of matching family → return None (caller emits letter-name fallthrough). `inv_hint=None` reproduces the old behavior exactly.

**`scripts/build_tchaikovsky_mei.py` — SatbAligner class:**
- Loads `app/satb_chord_index.json` at startup (gracefully degrades if missing — prints a NOTE and all hymns fall back to root-pos behavior).
- `SatbAligner(events)`: stateful cursor over one hymn's SATB event list. `hint_for(chord_str)` parses the root pitch-class from the chord string (`_chord_root_pc`) and scans forward in events (window of `LOOKAHEAD = 6`) for a matching root, returning `{'inv', 'seventh'}` and advancing the cursor. If no match in window: returns None and leaves cursor in place (so next call retries from the same position).
- `build_hymn_mei(ls, satb_events=None)` creates one aligner per hymn.
- **Critical restructure of the sub-measure loop:** the old code called `chord_to_spec` twice per chord — once for specs (clamped), once for harm labels. With a stateful aligner, double-consumption would skip events. Fix: walk `sub_events` ONCE to build `chord_hints_seq = [(chord_str, hint), ...]`, then apply `clamp_chords`-shaped logic to the PAIRS (preserving which hint belongs to which chord), and feed the same `chord_hints_seq` to the harms loop via `iter()`.
- **Known edge case:** if a bar has two consecutive same-root chords (`D` `D`), the SATB analyzer may have collapsed them into one event, so the second `D` in the bar scans forward past the match and pulls the *next* event. Usually harmless because successive `D`s would get the same inv anyway.

**Distribution after rebuild (verify with a quick script):**
```python
import json, re
from collections import Counter
d = json.load(open('app/app/src/main/assets/tchaikovsky_mei.json'))
all_labels = [l for h in d for l in re.findall(r'<harm[^>]*>([^<]+)</harm>', h['mei'])]
c = Counter(all_labels)
# Expect ~75 distinct, top 10 should include ①¹ ①² ⑤¹ ⑤² ②m¹ ⑥m² etc.
print(len(all_labels), len(c), c.most_common(10))
```

### Other fixes shipped this session (2026-04-11, earlier)

- **CHORD_NAMES rewritten to circled digits** in `scripts/generate_drill.py`. Each degree is now a unicode circled digit (①-⑦), minor triads get an explicit `m` marker (circled digits have no case — the `m` disambiguates `⑥m` from `⑥`), and inversion superscripts `¹²³` have a preceding `\u2009` THIN SPACE to stop them colliding with the chord body. `_S = '\u2009'` constant used throughout the dict.
- **Key signatures rendering — ACTUAL fix (supersedes Home's earlier attempt).** Home Claude's commit 08207f4 added `key.sig="3f"` as an *attribute* on `<staffDef>`. Verovio 6.1 renders `<g class="keySig" />` empty from the attribute form — **the attribute is ignored**. Real fix: emit a nested `<keySig sig="3f"/>` *child element* inside each `<staffDef>`. Confirmed with direct verovio render: empty → 9 `<g class="keyAccid">` glyph groups (3 flats × 3 staves). Applied in `build_tchaikovsky_mei.py` header emission. `@key.sig` on `scoreDef` is gone now too — not needed.
- **Verovio harm text was rendering only the circled digit on Android**, stripping `m7`, `Δ`, `°`, `¹²³`, etc. Root cause: Verovio sets `font-family="Times, serif"` on the root SVG; Android WebView's Times fallback chain handles circled digits from a symbols fallback font but **breaks mid-tspan**, so the Latin/Greek suffix that follows disappears. Fix: CSS override in `app/app/src/main/assets/index.html`:
  ```css
  svg g.harm text, svg g.harm text tspan {
    font-family: "Noto Sans", "DejaVu Sans", sans-serif !important;
    font-size: 220px !important;
  }
  ```
  Noto Sans covers everything in a chord label, and 220px reads as a caption rather than a billboard.
- **Handout pages rebuilt (landscape letter, 2 pages):**
  - `handout/handout_chord_table.tex` — 14×7 chord table using circled-digit degrees. Requires **xelatex** (fontspec + DejaVu Sans).
  - `handout/handout_finger_drills.tex` (NEW) — 4-finger sequence drills + tikz rhythm-grid sidebar anchored to page's north-east corner. `remember picture, overlay` requires **two xelatex passes** to render the overlay — if you rebuild it, don't skip the second pass or the sidebar disappears.
  - `handout/handout.tex` — drastically slimmed to a 2-page wrapper that just `\includepdf[pages=-]`'s the two PDFs above. Old multi-page trefoil drill content is gone from this file. Build order: `xelatex handout_chord_table.tex`, `xelatex handout_finger_drills.tex` (twice), then `pdflatex handout.tex`.

### Build / install commands (reminder)

```bash
# Full Tch rebuild after chord-table or SATB index changes:
python3.10 scripts/build_satb_chord_index.py    # only if OpenHymnal changed (~2 min)
python3.10 scripts/build_tchaikovsky_mei.py     # always
cp app/tchaikovsky_mei.json app/app/src/main/assets/
cd app && ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Quick chord-label-only rebuild (no SATB re-analysis):
python3.10 scripts/build_tchaikovsky_mei.py && cp app/tchaikovsky_mei.json app/app/src/main/assets/
cd app && ./gradlew assembleDebug && adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Things still open / future work

- **7 hymns** skipped by the SATB analyzer because their titles don't match OpenHymnal exactly (punctuation, whitespace). Stats: if you run the analyzer, look for the "FAIL ..." lines. Low priority — those hymns still render with plain root-pos labels (fallback).
- **Label visual polish on the tablet**: the thin-space + superscript combination reads as `⑤ 2` rather than `⑤²` in some screenshots (the superscript isn't visually distinguished from a full-size digit). Possibly the WebView's Noto Sans metrics render U+00B2 at full size. If you want truer superscript typography, switch to wrapping the inversion digit in an inner `<tspan baseline-shift="super" font-size="70%">` via SVG post-processing in `index.html::renderDrill`. Not urgent.
- **Non-diatonic chromatic chords** (Eb, Bb, C#°, etc. — 256 fallthrough instances, 2.4%) still render as letter-name. This is Option A per user's instruction — "fall back to what the diatonic harp can play" — so probably don't touch unless the user asks.
- **Alignment heuristic** (SatbAligner root-match with 6-event lookahead) may mis-bind when a bar has same-root chords repeated. Low-impact because adjacent same-root events usually have the same inversion anyway.
- **Files touched this session**: `scripts/generate_drill.py`, `scripts/build_satb_chord_index.py` (new), `scripts/build_tchaikovsky_hymnal.py`, `scripts/build_tchaikovsky_mei.py`, `app/tchaikovsky_mei.json`, `app/app/src/main/assets/tchaikovsky_mei.json`, `app/app/src/main/assets/index.html`, `app/satb_chord_index.json` (new), `handout/handout.tex`, `handout/handout_chord_table.tex`, `handout/handout_chord_table.pdf`, `handout/handout_finger_drills.tex` (new), `handout/handout_finger_drills.pdf` (new), `handout/handout.pdf`.

---

**Home → Lab (2026-04-10, end of session):**
- **Bug fixed: Tch-mode hymns were rendering without key signatures.** The MEI from `build_tchaikovsky_mei.py` declared `key.sig` only on `<scoreDef>`, but Verovio does not cascade the scoreDef attribute through the nested `staffGrp` (`bracket { 1, brace { 2, 3 } }`) to draw the signature glyphs on each staff. Note pitches were logically correct (no `@accid` emitted, key sig applied internally) but no flats/sharps were ever drawn.
- **Fix**: added `key.sig` as an explicit attribute on all three `<staffDef>` elements in `build_tchaikovsky_mei.py` (line ~547-550). Rebuilt `app/tchaikovsky_mei.json` and mirrored to `app/app/src/main/assets/tchaikovsky_mei.json`. Verified Eb hymn MEI header now shows `key.sig="3f"` on each staffDef.
- **Confirmed SSAATTBB mode is unaffected** — it renders from ABC which embeds `K: Eb` etc. and abc2svg draws key sigs correctly from that. Only the Tch/Verovio path had this issue.
- **Action for Lab**: rebuild APK and push to tablet to pick up the fix:
  ```bash
  cd app && ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
  adb install -r app/build/outputs/apk/debug/app-debug.apk
  ```
- **Files touched**: `scripts/build_tchaikovsky_mei.py`, `app/tchaikovsky_mei.json`, `app/app/src/main/assets/tchaikovsky_mei.json`.

**Lab → Home (2026-04-11, end of session):**
- **M: none hymns now split into 4-beat sub-measures.** 18 hymns in `data/OpenHymnal.abc` have `M: none` with phrase-length "bars" (e.g. hymn 128 A Mighty Fortress has 16-beat source bars = 4 measures of 4/4 per `|`). Previously my builder defaulted to 4/4 and stuffed 16 beats into one visual 4/4 bar — wrong and unreadable.
- **Fix in `scripts/build_tchaikovsky_mei.py`**:
  1. New `events_to_mei(events, mel_num, mel_den, id_prefix='n')` — renders a flat event list (from `parse_melody_bar`) to MEI note/rest XML. Supports `tie_in` / `tie_out` flags on notes emitting `@tie="i"` / `@tie="t"` / `@tie="m"` so split notes tie across sub-measure barlines.
  2. New `split_events_into_measures(events, beats_per_measure_L)` — walks an event list and slices it into measures of exactly `beats_per_measure_L` L-units. Notes crossing a boundary are split into two halves, the first marked `tie_out` and the second `tie_in`. Uses `fractions.Fraction` for exact duration math. Clears `chord` on tied halves so the chord annotation only emits once.
  3. `build_hymn_mei`: for `M: none` hymns, default to `ts_num=4, ts_den=4`, compute `sub_measure_L = 4 * mel_den / mel_num`, parse each source bar into events, and call `split_events_into_measures`. Each sub-measure becomes its own `<measure>` in the MEI. Uses `id_prefix=f'm{measure_num}n'` for the unmetered path so xml:ids don't collide across sub-measures; metered hymns keep `id_prefix='n'` so their output stays byte-identical to commit 33e8fdc.
- **Metered hymns verified byte-identical to commit 33e8fdc** for the splitter change alone. The later pickup-cadenza change (below) does modify metered hymns with pickups.
- **Pickup bars now get cadenzas.** Previously `cadenza_to_mei` was skipped when `is_pickup`. Now we pass `bar_eighths` to override the tuplet's `numbase`, so a pickup of N eighths worth fits a tuplet of `num=len(events) numbase=N` instead of the full-bar default. Caller computes `pickup_eighths = bar_dur_l * mel_num * 8 / mel_den` (must divide cleanly or we fall back to no cadenza). `cadenza_to_mei(specs, ts_num, ts_den, bar_eighths=override_eighths)`.
- **Things I tried and reverted** (read before re-attempting):
  - Emitting `meter.sym="none"` for M:none hymns and skipping cadenza → honest but leaves phrases as one unsplit visual measure with 15 beats of content. Rejected in favor of splitting into 4/4 sub-measures.
  - Defaulting `ts_num/ts_den = (0,0)` sentinel → caused division-by-zero in tstamp calc and tuplet ratio. Replaced with `ts_num,ts_den=4,4` default for M:none.
  - `Fraction(16, 4)` reducing to `4/1` → produced weird "4 whole notes per bar" meter. Fixed by using direct quarter-note math with fixed `ts_den=4`.
- **Duplicate hymn titles**: 9 pairs of hymns share titles (A Mighty Fortress — 127 isorhythmic 4/4 vs 128 rhythmic M:none, plus 8 others). App lists both but only shows the title, so they look like duplicates. Consider adding a version suffix in the UI listing.
- **Source edition difference**: our `data/OpenHymnal.abc` is the 2006/2013 Edition with the *rhythmic* 1931 setting of Ein Feste Burg. User compared against the 2013 Edition's *isorhythmic* 1917 setting (M:4/4, quarter/eighth notes only, no half notes). The notes ARE the source — we just have the older-rhythm edition. Consider updating to 2013 Edition if it's worth the effort.
- **Still open**: Hymn 128 bar 1 pickup-cadenza discussion — hymn 128's bar 1 starts with a quarter rest but is a FULL 4-beat measure (1+1+2 beats), not a pickup. Verified cadenza is present in that measure in the current MEI.
- **Files touched this session**: `scripts/build_tchaikovsky_mei.py` (events_to_mei, split_events_into_measures, build_hymn_mei refactor, cadenza bar_eighths), `app/tchaikovsky_mei.json`, `app/app/src/main/assets/tchaikovsky_mei.json`.

**Lab → Home (2026-04-10, end of session):**
- **Tchaikovsky mode now renders via Verovio, not abc2svg.** The cadenza needs features (cross-staff beaming, cue notes, per-staff scale, hidden-bracket tuplets) that abc2svg cannot produce cleanly. Verovio bundled locally as `app/app/src/main/assets/verovio/verovio-toolkit-wasm.js` (~7MB, UMD wrapped, no network needed).
- **New builder**: `scripts/build_tchaikovsky_mei.py`. Reads `app/lead_sheets.json` + chord table from `generate_drill.py`, emits `app/tchaikovsky_mei.json` (288 hymns, ~16MB). Mirrored to `app/app/src/main/assets/tchaikovsky_mei.json`.
- **Cadenza architecture** (finalized after many iterations — don't drift):
  1. Cross-staff alternation (example_624 algorithm): each sweep note on its natural staff, opposite staff gets `<space/>` at same time slot.
  2. `dur="8"` (single-beam eighths) for shortest stems. 
  3. Entire layer wrapped in hidden-bracket `<tuplet num="N" numbase="8*ts_num/ts_den" num.visible="false" bracket.visible="false">` so the eighths scale to fit exactly one bar.
  4. `cue="true"` on cadenza notes.
  5. `stem.dir="down"` on treble notes, `stem.dir="up"` on bass notes → beams point INWARD toward middle C (outside the sweep pointing inward) so they don't overlap between staves.
  6. Beams break at direction changes (ascending→descending) so each beam slopes monotonically with contour.
  7. `EXTRA_GAP_SLOTS = 6` inserted at middle-C crossings (6 extra `<space/>` on BOTH staves) — needed because the tuplet compresses the layer, small gaps get squashed; 6 slots gives ~18% bar width of visible horizontal air at each crossing.
  8. Harp staves (2,3) rendered at `scale="50%"` via `<staffDef scale="50%"/>` so they're visibly smaller/subordinate to the melody staff. Verovio honors this — melody at full size, whole harp grand staff at half scale.
- **Verovio options in index.html `renderDrill`** (Tch-mode path): `noJustification: true` (ragged-right), `spacingBracketGroup: 6` (melody↔harp gap), `spacingBraceGroup: 0` (harp treble↔bass tight — middle C ledger bridges cleanly), `leftMarginNote: 0.0, rightMarginNote: 0.0, spacingLinear: 0.05, spacingNonLinear: 0.3` (aggressive horizontal compression), `beamMaxSlope: 20` (beams slope with contour), `scale: 40, pageWidth: 60000, breaks: 'none'` (single wide strip).
- **Things I tried and rejected** (don't re-attempt without reading this):
  - `@stem.len` on notes → **Verovio ignores it on beamed notes.** Dead code.
  - `@size="cue"` / `@size="grace"` / `@size="0.5"` on notes → **Verovio only honors `cue="true"` and `grace="unacc"` as boolean attrs**, not the string-valued `@size`.
  - Grace notes in a single layer with `@staff` → WORKS for cross-staff beaming but grace notes don't consume time, so can't do cross-staff alternation with `<space/>`. Also cluster per-staff visually.
  - Two parallel graceGrps (one per staff) → "two sets of notes" — user rejected.
  - `graceRightAlign: true` / `graceFactor: 0.5` → helped in grace-note approach but we're not using grace.
- **Algorithm the user gave us** (example_624.abc cross-staff alternation): this is sacred. Do not drift from it. Each sweep note at its natural position, opposite staff has invisible rest at same time position, beams break at middle-C crossings naturally. We use `<space/>` elements not `<rest visible="false"/>`.
- **Known limitations**: tuplet wrapping means the cadenza's musical TIME is proportionally stretched to the bar (not a real cadenza ad-lib) but visually it looks right. Scroll sync with playback is not wired up in Tch/Verovio mode (no `.abcr` rects).
- **Build pipeline** (runs clean locally):
  ```bash
  python3.10 scripts/build_tchaikovsky_mei.py                # rebuild MEI JSON
  cp app/tchaikovsky_mei.json app/app/src/main/assets/       # mirror to assets
  cd app && ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
  adb install -r app/build/outputs/apk/debug/app-debug.apk
  ```
- **Files touched this session**: `scripts/build_tchaikovsky_mei.py` (rewritten cadenza_to_mei several times), `app/app/src/main/assets/index.html` (Verovio init + render path + options), `app/tchaikovsky_mei.json` (regenerated), `app/app/src/main/assets/tchaikovsky_mei.json` (mirror), `app/app/src/main/assets/verovio/verovio-toolkit-wasm.js` (already bundled earlier).

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
