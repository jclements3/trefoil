# CLAUDE.md

Guidance for Claude Code working in this repo.

## Overview

Trefoil — lever harp hymnal app. 288 OpenHymnal hymns, rendered in an Android WebView app with three display modes:

- **Tch-SSAATTBB** (default) — AI-composed pedal harp arrangements (270 hymns, MEI via Verovio). 3 staves: melody + RH + LH.
- **Tch** — melody + Tchaikovsky-style arpeggio cadenza runs over grand staff (288 hymns, MEI via Verovio).
- **SSAATTBB** — 8-voice score from the legacy pipeline (ABC via abc2svg).

Plus a drill handout toolchain (`handout/`) and a set of lead-sheet/etude PDF generators (`scripts/generate_*.py`).

## Structure

- `app/` — Android WebView app (`com.harp.trefoil`). Assets mirrored to `app/app/src/main/assets/`.
  - `tch_ssaattbbp_mei.json` (10 MB) — composed MEI arrangements
  - `tchaikovsky_mei.json` (~16 MB) — Tch cadenza MEI
  - `ssaattbb_data.json`, `tch_ssaattbb_data.json` — ABC fallbacks
  - `lead_sheets.json` — 288 lead sheets (melody + absolute chord symbols)
  - `satb_chord_index.json` — per-onset SATB chord analysis (root/bass/quality/inv)
  - `pattern_index.json`, `pattern_drills.json` — 53 voicing patterns for drills
- `scripts/` — build pipeline. Canonical builders:
  - `build_tchaikovsky_mei.py` — Tch mode MEI (melody + cadenza, 3 staves)
  - `build_tchaikovsky_hymnal.py` — shared `chord_to_spec` for cadenza specs
  - `build_satb_chord_index.py` — per-voice SATB analysis → `satb_chord_index.json`
  - `split_mei_layers.py` — post-processes composed Tch-SSAATTBBP raw MEI into moving/sustained layers
  - `generate_drill.py` — 14×7 chord table (`CHORD_NAMES`, `VALID`)
  - Legacy pipeline (`build_harp_hymnal*.py`, `build_hymnal_v3.py`, `optimize_harp_voicings.py`, v4/v5g work) is not used by the current app. Keep for reference only.
- `handout/` — LaTeX handout sources + PDFs (chord table, finger drills, leadsheets, etudes), plus `tch_ssaattbbp_out/*.mei` (raw + split composed MEI) and `tch_ssaattbbp_prompt.md` (composition prompt for Claude subagents).
- `data/OpenHymnal.abc` — SATB source (288 hymns).

## Build / install

```bash
# Rebuild Tch cadenzas:
python3.10 scripts/build_tchaikovsky_mei.py
cp app/tchaikovsky_mei.json app/app/src/main/assets/

# Re-split composed Tch-SSAATTBBP after raw MEI edits:
python3.10 scripts/split_mei_layers.py
cp app/tch_ssaattbbp_mei.json app/app/src/main/assets/

# Rebuild SATB chord index (only if OpenHymnal changes, ~2 min):
python3.10 scripts/build_satb_chord_index.py

# APK + install (lab machine only — laptop cannot build):
cd app && ANDROID_HOME=$HOME/Android/Sdk JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Local preview: `python3 -m http.server 9090 --directory app` → `localhost:9090`. (Port 8080 is Traefik.)

## Key constants

- **Lever harp keys**: Eb, Bb, F, C, G, D, A, E (3 flats to 4 sharps). 22 hymns in Ab/Db are transposed (Ab→G, Db→D).
- **Harp range**: C2 to G6 (MIDI 36–91, 33 strings). `C` in ABC = C4 = middle C.
- **Hand separation**: RH always above LH, no crossings. LH bass clef, RH treble clef.
- **LH voicing rules**: bottom intervals must be P4+ (no 2nds/3rds in bass). Top note may form m3/M3 with note below. Target 3–4 notes.
- **Chord symbols**: absolute names (D, Am, G7) from music21 — NOT Roman numerals, NOT transposed to C.
- **Drill labels**: circled digits `①–⑦` for degrees, `m` suffix for minor (disambiguates case), `¹²³` inversion superscripts prefixed with U+2009 thin space. Defined in `scripts/generate_drill.py::CHORD_NAMES`.
- **ASCII everything** in scripts is fine; MEI/SVG is UTF-8.
- **python3.10** is required (music21).

## Tch-SSAATTBBP (composed arrangements)

- Composed by Claude Sonnet subagents using `handout/tch_ssaattbbp_prompt.md`. Uses handout chord table voicings (14 patterns × 7 degrees + inversions).
- 3 staves: melody + RH (2–3 notes, lighter) + LH (3–4 notes, heavier) with pedal bass.
- Raw output: `handout/tch_ssaattbbp_out/NNNN_raw.mei`. After `split_mei_layers.py`: `NNNN.mei` with stems-up moving / stems-down sustained layers.
- Rests use `<space/>` (Verovio ignores `visible="false"` on `<rest>`).
- `accid.ges` emitted on every key-signature note (Verovio MIDI export bug workaround). `KEY_ACCID_GES` dict maps key → {pname: accid}.
- 17 `M:none` hymns excluded (no metered time signature).

## Tch (cadenza) architecture — don't drift

Cadenza is a cross-staff sweep through chord tones, one per bar, wrapped in a hidden-bracket tuplet so it fits the bar:

1. Cross-staff alternation: each sweep note on its natural staff, opposite staff gets `<space/>` at the same slot.
2. `dur="8"` eighths, `cue="true"`, stems pointing inward (`stem.dir="down"` on treble, `stem.dir="up"` on bass) so beams don't collide across middle C.
3. Layer wrapped in `<tuplet num="N" numbase="8*ts_num/ts_den" num.visible="false" bracket.visible="false">`.
4. Beams break at direction changes (ascending → descending).
5. `EXTRA_GAP_SLOTS = 6` inserted at middle-C crossings for visible air.
6. Harp staves 2/3 at `scale="50%"` so melody dominates.

**Things already tried and rejected** — do not re-attempt without reading this:
- `@stem.len` on beamed notes → Verovio ignores it.
- `@size="cue"`/`"grace"`/`"0.5"` → Verovio only honors `cue="true"` and `grace="unacc"` as booleans.
- Grace notes with `@staff` for cross-staff beaming → don't consume time, so can't alternate with `<space/>`.
- Two parallel graceGrps → user rejected ("two sets of notes").
- `meter.sym="none"` for `M:none` hymns → leaves 15-beat visual bars. Replaced with split into 4/4 sub-measures (`split_events_into_measures`, ties across barlines).

## Inversion detection (Tch labels + re-voicing)

`build_satb_chord_index.py` parses `data/OpenHymnal.abc` per-voice (manually splits `[V: S1V1]` etc. because `%%combinevoices 1` defeats music21's splitter). At each unique onset it builds a 4-voice slice via binary search (`sounding_at()`) and computes `{root_pc, bass_pc, quality, seventh, inv}` from pitch-class intervals. Dedupes consecutive identical events. ~1.3 MB, 280/287 hymns (7 skipped for title mismatches — low priority).

`chord_to_spec(chord_str, key, inv_hint=None)` uses `_pick_row_deg(chord_deg, has_7th, inv)` to pick a `(pattern, row_deg)` from the 14×7 table. **`start_string = deg_to_first_string(key, row_deg)`** — anchored to *row_deg*, so inversions drive different sweeps, not just different labels.

`SatbAligner` in `build_tchaikovsky_mei.py` walks events stateful-cursor-style (`LOOKAHEAD = 6`) and returns a hint per chord. Critical: walk `sub_events` ONCE to build `chord_hints_seq`, then apply clamping and emit harms from the same sequence — double-consuming the aligner skips events.

## Verovio + WebView gotchas

- **Key signatures**: `key.sig` must be emitted as a nested `<keySig sig="3f"/>` child element inside each `<staffDef>`. Verovio 6.1 ignores the `key.sig` attribute form on `<staffDef>` and will not cascade a `scoreDef`-level attribute through nested `staffGrp`s.
- **MIDI export**: `accid.ges` must be on every note affected by the key signature, or the synth plays naturals. Applies to both the Tch cadenza builder and the composed MEI.
- **Harm font on Android**: Verovio writes `font-family="Times, serif"`; WebView's Times chain drops Latin/Greek suffixes after circled digits. Override in `app/app/src/main/assets/index.html`:
  ```css
  svg g.harm text, svg g.harm text tspan {
    font-family: "Noto Sans", "DejaVu Sans", sans-serif !important;
    font-size: 220px !important;
  }
  ```
- **Render options** (Tch/Verovio path in `renderDrill`): `noJustification: true`, `spacingBracketGroup: 6`, `spacingBraceGroup: 0`, `leftMarginNote: 0`, `rightMarginNote: 0`, `spacingLinear: 0.05`, `spacingNonLinear: 0.3`, `beamMaxSlope: 20`, `scale: 40`, `pageWidth: 60000`, `breaks: 'none'`.
- **Audio**: `renderToMIDI()` → Web Audio triangle wave with pluck envelope. Tch cadenza notes are redistributed across the measure (Verovio bunches tuplet notes at the downbeat). Melody on ch 0 louder, cadenza on ch 1–2 quieter. Mute default on.
- **Scroll sync**: uses measure-boundary curve, not the timemap (timemap has non-monotonic x from multi-staff events).

## Drills (in-app, `n < 4000`)

Drills are hymnal entries with `n < 4000`; hymns are `n >= 4000`. Rendered as grand-staff strip charts; on-the-fly from `ssaattbb_data.json` brackets for some, pre-built for pattern drills.

- `n=3200` "53 Patterns" — all 53 unique (LH, RH) voicing patterns in G, starting at G2.
- `n=3100–3107` per-key pattern drills — only patterns that appear in that key's hymns, sorted by frequency. Counts: Eb 26, Bb 28, F 36, C 31, G 40, D 34, A 21, E 13.
- Pattern hex IDs: `XXXX-XXXX` (4 digits per hand, 0 = unused finger). First digit = scale degree of RH thumb; subsequent digits = interval from previous (3 = 3rd, 4 = 4th, etc.).

## Handout PDFs

Final output: `booklet.pdf` at the repo root — 2 portrait tabloid (11×17) sheets that fold in half into a 4-page 11×8.5 landscape booklet. Build with `scripts/build_booklet.sh` (uses `pdftops` + `psutils pstops` 2-up imposition + `ps2pdf`). Requires `psutils` package.
- Page 1 (`handout_page1.pdf`) — chord table + finger patterns
- Pages 2–3 (`cascades.pdf`) — inside spread
- Page 4 (`handout_page4.pdf`) — composition & voicing reference

Build order from `handout/`:
- `xelatex handout_chord_table.tex` (and/or `_portrait`) — fontspec + DejaVu Sans
- `xelatex handout_finger_patterns.tex`
- `xelatex handout_finger_drills.tex` — **run twice** (`remember picture, overlay` sidebar needs the second pass)
- `xelatex handout_page1.tex`, `xelatex handout_page4.tex`, `xelatex cascades.tex`
- `pdflatex handout.tex` assembles the booklet via `\includepdf`.

Leadsheets and etudes: `scripts/build_leadsheets_pdf.sh` and `scripts/build_etude[1-4]_pdf.sh` generate ABC → abc2svg HTML → PDF. Generators are `scripts/generate_leadsheets.py` and `scripts/generate_etude*.py` (shared code in `scripts/_etude_shared.py`).

## Lab/Home sync protocol

Two machines (lab + home laptop), separate Claude Code agents. **CLAUDE.md is the comm channel.**

Every session:
1. `git pull` before doing anything.
2. At end: `git add -A && git commit && git push` — always.
3. Write a sync note below describing what was done and what's pending.

Old sync-note backlog has been archived (see git log from 2026-04-05 through 2026-04-13 for session-by-session detail). Keep this section short: 1–2 most recent notes only.

### Pending sync notes (newest first)

**2026-04-16 night (lab):** 100 Jazz Licks OMR pipeline running overnight.
- Extracted 100 per-lick PNG crops from `images/100JazzLicks.mp4` via `images/100jazzlicks_work/extract_licks.py` (dHash + white-ratio stable-run detection, ratio-based crop, 1920px wide).
- Built `images/omr_a4.pdf` — 12 A4 pages packing all 100 licks with generous whitespace (sheet-music layout oemer can parse). Mapping of which lick sits on which page in `images/omr_a4_mapping.json`.
- Started `images/run_omr_batch.sh` at ~22:38 CDT. Each page runs oemer (CPU, ~10-15 min/page), then `stitch_omr.py` merges the 12 MusicXML outputs into `images/licks_omr.abc` with chord symbols re-attached from the existing `licks.abc`. Progress in `images/omr_work/batch.log`, final state logged as `=== ALL DONE <timestamp> ===` at end.
- Tested the stitch pipeline on the online OMR MusicXML (`images/1776395538740657_514.musicxml` — 39/100 licks captured because 20/page density was too tight) to confirm parser works: emits e.g. `"Gm7"zc/2B/2_BAGFD^D` for lick 00 bar 1 (1 8-rest, 2 16ths C5/B4, 6 8ths Bb4 A4 G4 F4 D4 D#4). Note oemer's octave reading may differ from the older hand-written `licks.abc`.
- Oemer fails on the bare 1920×~200 single-staff strips (empty staff-line detection); only works on full-page multi-lick images.

**Tomorrow's starting point:**
1. `tail images/omr_work/batch.log` — look for `=== ALL DONE ===` line.
2. If done, `head images/licks_omr.abc` to review; run `python3 images/build_review_pdf.py` (already updated to work with current `licks.abc` — update it to also accept `licks_omr.abc` as needed) to produce source+OMR-clone review PDF.
3. If some pages failed, stitch still emits placeholders (`(OMR failed)` titles) preserving numbering; individual pages can be re-run with `oemer -o images/omr_work images/omr_work/page_NN.png`.
4. Downstream use of `licks.abc` is `images/harp_reduce.py` which reduces to diatonic harp scale per-group (licks 00-19 F, 20-39 Eb, etc.) — pitch-class accuracy matters, octaves matter for C2-G6 harp range.

Pending follow-ups:
- Wire `licks_omr.abc` into `build_review_pdf.py` so user can pick source vs. clone source.
- Consider per-lick octave sanity check (melody should land in treble staff range; oemer's output in the test came out roughly an octave low vs. hand transcription — may be a systemic offset).
- `licks.abc` header still references old `{00..99}licks.jpg` — update after OMR result is accepted.

**2026-04-15 (lab):** Modern mode is live in the APK. Built end-to-end reharmonization pipeline at `modern/` (Schneider-style journey/destination, 6 rules, voicing picker hits handout's 14×7 table). Outputs:
- `modern/all_hymns.pdf` (115 pp, 6.5 MB) — printable lead sheets, 3-up portrait
- `modern/by_key/*.pdf` (8 keys, 94 pp total) — per-key bundles
- `modern/all_hymns_index.pdf` — 2-pp alphabetical TOC
- `app/app/src/main/assets/modern_mei.json` (4.88 MB, 253 hymns) — wired to existing `MODERN_MEI` loader, renders inline via Verovio with stacked RH/LH `<harm vo=0/6>` fractions. Verified bundled WASM is 6.1.0-682d606; rendering confirmed against actual asset before APK install.
- APK rebuilt + `adb install`-ed to tablet.

CLI: `python3.10 -m modern {samples,all,perkey,audit,test,index,find,clean,help}`. New helpers under `modern/`: `build_all.py`, `build_per_key.py`, `build_svg.py` (LilyPond→SVG, kept as research artifact), `build_mei.py` (ABC→Verovio→post-process to inject paired harms — the production path), `build_stats.py` (writes `stats.md`), `build_booklet.sh` (saddle-stitch any N-page PDF), `find.py` (fuzzy hymn search), `meter_handler.py` (handles 25/26 M:none/3/2/8/4 exceptions; **not yet wired into `build_all.process_hymn`** — TODO, ~10 lines at lines 369–380).

Pending follow-ups:
- Wire `meter_handler.preprocess_abc` into `build_all.process_hymn` to pick up the +25 meter-exception hymns currently still skipped.
- Stats finding worth investigating: Rule 6 (extensions) never fires because `melody_pitches` isn't populated on `ChordEvent` — easy color-on-destinations win. See `modern/stats.md`.
- 8 cleanTitle collisions in `lead_sheets.json` cause the MEI/SVG dicts to lose 8 entries (261→253). Pre-existing data issue; second member overwrites the first.
- `app/lead_sheets.json` had 196 hymns hardcoded to Q:1/4=100; `scripts/fix_lead_sheet_tempos.py` restored real tempos from `data/OpenHymnal.abc`. Backup at `app/lead_sheets.json.bak-pretempo` (gitignored).
