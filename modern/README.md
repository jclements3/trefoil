# modern/ -- Diatonic-jazz reharmonization pipeline

## Status

- [done] 10-hymn sample PDF renders cleanly (`modern/samples.pdf`, 2 hymns/page).
- [done] 6 medium-aggressiveness reharm rules pass their in-module self-tests.
- [done] Voicing picker parses 66-74 `\se{}` entries from `handout.tex` page 2.
- [todo] Full-hymnal build (all 288 hymns) not yet wired -- no CLI entry point.
- [todo] App's "Modern" mode pulldown not yet populated with data.
- [todo] All hymns render at 100 BPM because `app/lead_sheets.json` lacks per-hymn `Q:` tempos.

## Overview

A diatonic-jazz reharmonizer that takes OpenHymnal lead sheets (`app/lead_sheets.json`) and produces PDF lead sheets with stacked RH/LH chord-fraction labels above the melody, styled to match `handout.tex`. The reharmonization is inspired by Jeff Schneider's "Journey vs. Destination" framework (journey beats get substitution color, destination beats stay grounded) and uses the trefoil catalog of cycles of 2nds / 3rds / 4ths voicings from the handout. Output is strictly diatonic to the lead-harp key -- no secondary dominants, no accidentals, no lever changes mid-piece.

## Architecture

Data flow:

```
app/lead_sheets.json  +  handout.tex (page 2 \se{} voicings)
        |                       |
        v                       v
reharm_rules.reharmonize()   voicing_picker.load_voicings()
        |                       |
        +--- voicing_picker.pick_sequence() ---+
                      |
                      v
        abc_rewriter.rewrite_abc()   (sentinel "^@@CHORDn@@" per annotation)
                      |
                      v
        abc_to_ly.abc_to_lilypond()  (shell out to abc2ly)
                      |
                      v
        chord_overlay.fraction_markup_attached()  (sentinel -> \markup)
                      |
                      v
        layout.build_combined_ly()   (book + per-hymn bookparts)
                      |
                      v
        build_pdf.sh  ->  modern/samples.pdf
```

Module table:

| file | purpose | public API |
|------|---------|-----------|
| `reharm_rules.py` | 6 ordered diatonic reharm rules operating on `ChordEvent` lists; all arithmetic mod-12, no music21. | `reharmonize(events, key)`, `ChordEvent`, `parse_chord_name`, `chord_tones`, `clashes` |
| `voicing_picker.py` | Parses `\se{}{}{}{}{}{}{}` entries from the StackedChords section of `handout.tex` into `Voicing` records; picks a voicing per chord with voice-leading smoothing. | `load_voicings()`, `pick_voicing()`, `pick_sequence()`, `voicings_for_lh()`, `figure_to_strings()` |
| `abc_rewriter.py` | Hand-written scanner that finds `"^X"` / `"_X"` chord annotations in ABC body (skipping header/lyric lines) and replaces them with paired RH/LH labels. | `iter_chord_annotations()`, `rewrite_abc()`, `labels_from_voicing()` |
| `abc_to_ly.py` | Thin subprocess wrapper around LilyPond's `abc2ly`; extracts the music body from the generated `\voicedefault`. | `abc_to_lilypond(abc)` |
| `chord_overlay.py` | Builds LilyPond `\markup` fragments stacking navy RH / burgundy LH Roman-numeral labels in TeX Gyre Pagella Bold, with small superscript qualities. | `fraction_markup_attached(rh, lh)`, `label_to_markup`, `fraction_markup`, `make_chord_voice` |
| `layout.py` | Sentinel-rewrites ABC, runs abc2ly, substitutes `^"@@CHORDn@@"` -> `^\markup{...}`, wraps each hymn in a `\bookpart`, and emits a `\book` with shared `\paper`/`\layout`. | `build_combined_ly(hymns, per_page=2)`, `build_combined_abc` |
| `verify_samples.py` | End-to-end harness: picks 10 diverse hymns, runs reharm + voicing + rewrite, writes `samples.ly`, `samples_report.md`, and `per_hymn/*.abc`. | `python3.10 -m modern.verify_samples` |
| `build_pdf.sh` | Bash wrapper that invokes `lilypond` on an input `.ly` and sanity-checks the output. | `modern/build_pdf.sh [IN.ly] [OUT.pdf]` |

## How to run

Regenerate the 10-hymn sample PDF:

```
cd /home/james.clements/projects/trefoil
python3.10 -m modern.verify_samples
bash modern/build_pdf.sh modern/samples.ly modern/samples.pdf
```

Full-hymnal build: not yet wired. Intended future entry point:
`python3.10 -m modern.build_all --out modern/all_hymns.pdf`.

## Reharmonization rules

Applied in order by `reharmonize(events, key)`:

1. **IV -> ii (journey only)** -- shared-tone swap preserves subdominant function with m7 color. Skipped on destination beats.
2. **I -> vi on weak beats** -- deceptive color; blocked when the immediately following event is a destination I (preserves final cadence).
3. **vii(dim) insertion before destination I** -- splices a leading-tone diminished chord into the tail of the prior bar (half its duration, capped at 0.5q). Skipped if prior is already V / V7 / vii.
4. **V -> V7 before cadential I** -- adds dominant-7 tension to any V that resolves to I.
5. **Vsus4 delay on final-cadence V -> I** -- splits a final-cadence V in half; the first half becomes Vsus4, creating a 4-3 suspension.
6. **Extensions on destination chords** -- I -> Imaj7, IV -> IVmaj7, vi -> vim7, ii -> iim7 when the melody sits on a chord tone and the added extension doesn't half-step clash.

Every rule runs a `_any_clash` guard first: a substitution is rejected if any chord tone of the candidate forms a minor 2nd or major 7th with any melody pitch in that span.

## Voicing selection

`voicing_picker.load_voicings()` parses the StackedChords section of `handout.tex` -- finds every `\se{rh}{rhQ}{desc}{lhFig}{rhFig}{lh}{lhQ}` entry on page 2 (66-74 entries depending on edits) and normalizes Greek delta / o-stroke / degree glyphs to our `Quality` tokens.

`pick_voicing(chord, prev_voicing, voicings)` scores each candidate by, in priority order:

1. **Quality match** -- LH quality must equal (or be close to) the required chord quality.
2. **Pair-repeat penalty** -- discourages reusing the same (rh_fig, lh_fig) pattern as the previous chord.
3. **Voice-leading smoothness** -- `voice_leading_cost()` sums pc distances between adjacent voicings.
4. **RH/LH diversity** -- mild bonus for varying figures across a passage.

`pick_sequence(roman_chords, voicings)` wraps this into a one-shot call for a whole hymn.

## Output format

- **PDF**: portrait US Letter, 2 hymns per page (tunable via `build_combined_ly(per_page=...)`). TeX Gyre Pagella throughout. RH label is navy `#1F4E79`, LH label is burgundy `#7B2B2B`; quality markers render as smaller superscripts.
- **Intermediate**: per-hymn ABC at `modern/per_hymn/NNNN.abc`; combined LilyPond at `modern/samples.ly`; human-readable before/after report at `modern/samples_report.md`.

## Known limitations

- All hymns currently render at 100 BPM because `app/lead_sheets.json` dropped the original `Q:` values. Fix in progress: regenerate lead sheets from `data/OpenHymnal.abc`, which still has per-hymn tempos.
- Strictly diatonic -- no secondary dominants, tritone subs, modal borrowing, or mid-piece lever changes.
- Not all 66 page-2 voicings get used; the quality-match gate biases toward a smaller working subset. Add more quality variants (especially for ii and vi) to broaden coverage.
- `pick_voicing` currently scores greedily (no dynamic programming); voice-leading is locally good but can miss a globally cheaper path.

## Extending

- **New reharm rule**: add to `reharm_rules.reharmonize()` in priority order. Always `_any_clash`-gate substitutions against `ev.melody_pitches`; use `is_destination` / `is_cadence` to gate journey-only rules.
- **New voicing**: add another `\se{...}` entry to page 2 of `handout.tex`. `load_voicings()` picks it up automatically -- no code change.
- **Different PDF layout**: edit `LAYOUT_TABLE` in `layout.py` and pass `per_page=` to `build_combined_ly()`. 2, 3, 4 hymns/page presets already exist.
- **Different colors**: `RH_COLOR` / `LH_COLOR` at the top of `chord_overlay.py`.
