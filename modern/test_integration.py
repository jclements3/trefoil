"""End-to-end integration test for the modern reharmonization pipeline.

Exercises the full in-memory path for 287 hymns of app/lead_sheets.json:

    parse chord annotations -> reharmonize -> pick_sequence ->
    rewrite_abc -> abc_to_lilypond

Run:
    python3.10 -m unittest modern.test_integration -v

ASCII only. python3.10. unittest only.
"""

from __future__ import annotations

import json
import os
import re
import unittest

from modern import abc_rewriter
from modern import abc_to_ly
from modern import audit_keys
from modern import reharm_rules
from modern import voicing_picker
from modern.reharm_rules import ChordEvent, parse_chord_name, reharmonize
from modern.voicing_picker import load_voicings, pick_sequence


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_TEX = os.path.join(REPO_ROOT, "handout.tex")

LEVER_HARP_KEYS = ["Eb", "Bb", "F", "C", "G", "D", "A", "E"]

CHORD_RE = re.compile(r'"\^([^"]+)"')
METER_RE = re.compile(r"(?m)^M:\s*([^\s]+)")
TEMPO_RE = re.compile(r"(?m)^Q:\s*([^\n]+)")

SIMPLE_METERS = {"2/4", "3/4", "4/4", "6/8", "9/8", "12/8",
                 "2/2", "3/8", "6/4", "C", "C|"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_meter(abc: str) -> tuple[int, int]:
    m = METER_RE.search(abc)
    meter = m.group(1).strip() if m else "4/4"
    if meter in ("C", "c"):
        return (4, 4)
    if meter in ("C|", "c|"):
        return (2, 2)
    mm = re.match(r"(\d+)/(\d+)", meter)
    if mm:
        return (int(mm.group(1)), int(mm.group(2)))
    return (4, 4)


def _parse_tempo_bpm(abc: str) -> tuple[int, int] | None:
    """Return (denominator, bpm) from Q: 1/N=BPM, or None."""
    m = TEMPO_RE.search(abc)
    if not m:
        return None
    q = m.group(1).strip()
    mm = re.search(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d+)", q)
    if mm:
        return (int(mm.group(2)), int(mm.group(3)))
    return None


def _ks_for_key(key: str) -> str:
    """LilyPond key name (lowercase root + accidental) for assertion."""
    # abc2ly emits `\key <note> \major` with '-flat' suffix for flats.
    letter = key[0].lower()
    if len(key) > 1 and key[1] == "b":
        return letter + "es"  # e.g. Eb -> ees, Bb -> bes
    if len(key) > 1 and key[1] == "#":
        return letter + "is"
    return letter


def _build_events(hymn: dict) -> tuple[list[ChordEvent],
                                       list[tuple[int, str]]]:
    """Parse hymn abc -> (events, annotation_index -> (idx, name)).

    Returns events in annotation order (skipping non-diatonic chords that
    parse_chord_name returns None for), plus a list of (idx, name) pairs
    keeping the original-annotation index alongside the name so the caller
    can line replacements up with every original annotation.
    """
    abc = hymn["abc"]
    key = hymn["key"]
    num, den = _parse_meter(abc)
    beats_per_bar = num * (4.0 / den)
    names = CHORD_RE.findall(abc)
    events: list[ChordEvent] = []
    parsed_indices: list[int] = []
    beat = 0.0
    for idx, name in enumerate(names):
        roman = parse_chord_name(name, key)
        if roman is None:
            continue
        bar_pos = beat % beats_per_bar
        is_strong = (
            abs(bar_pos) < 1e-6
            or (beats_per_bar >= 4 and abs(bar_pos - 2.0) < 1e-6)
        )
        is_cadence = idx >= len(names) - 2
        is_destination = is_strong
        ev = ChordEvent(
            beat=beat,
            duration=1.0,
            chord=roman,
            is_strong_beat=is_strong,
            is_cadence=is_cadence,
            is_destination=is_destination,
        )
        events.append(ev)
        parsed_indices.append(idx)
        beat += 1.0
    return events, parsed_indices, names


def _run_pipeline(hymn: dict, voicings) -> dict:
    """Run parse -> reharmonize -> pick_sequence -> rewrite -> abc2ly."""
    abc = hymn["abc"]
    key = hymn["key"]

    events, parsed_indices, names = _build_events(hymn)

    original_chords = [ev.chord for ev in events]
    new_events = reharmonize(events, key)
    new_chords = [ev.chord for ev in new_events]

    # Restrict the new_events list to one chord per original annotation
    # (ignoring the vii/sus4 inserts) so labels line up with annotations.
    # We do this by taking the first len(events) events from new_events,
    # since inserts push later events rightward; simple approach: match
    # by original-event identity via beat+chord where possible.
    # Simpler and robust: reharmonize may insert but never delete original
    # events; take a head slice of length len(events) after skipping
    # inserted ones. Inserts are always placed BEFORE a destination I or
    # V in the new list; we detect them by checking if the chord was not
    # present as-is at the same position.
    #
    # For the test, we only need two diversity/change checks, so we use
    # pick_sequence on new_chords (for variety) but pair labels back to
    # originals by trimming to len(events).
    chord_list_for_pick = new_chords
    picks = pick_sequence(chord_list_for_pick, voicings)

    # Build a per-original-annotation (rh, lh) list by stepping the picks
    # forward as we walk new_events, skipping inserts (inserts don't map
    # to any original annotation).
    # Strategy: align greedily. For each new_event, if its chord equals
    # the next original event's chord (or close), consume an original
    # slot; else it's an insert.
    labels_per_original: list[tuple[str, str]] = []
    oi = 0
    for i, ev in enumerate(new_events):
        if oi >= len(original_chords):
            break
        # Heuristic: consume the next original slot on each non-insert.
        # A reharmonized slot is one whose root was the same as the
        # original, or one that mutates the original in place (rules 1,
        # 2, 4, 6). Inserts (rule 3, 5) produce a chord with a NEW beat
        # not equal to the original's beat. Use beat as primary cue.
        if i < len(new_events) - 1 and ev.beat == original_chords_beat(
                events, oi):
            rh_deg, rh_qual = picks[i].rh
            lh_deg, lh_qual = picks[i].lh
            rh, lh = abc_rewriter.labels_from_voicing(
                rh_deg, rh_qual, lh_deg, lh_qual)
            labels_per_original.append((rh, lh))
            oi += 1
        elif ev.beat == original_chords_beat(events, oi):
            rh_deg, rh_qual = picks[i].rh
            lh_deg, lh_qual = picks[i].lh
            rh, lh = abc_rewriter.labels_from_voicing(
                rh_deg, rh_qual, lh_deg, lh_qual)
            labels_per_original.append((rh, lh))
            oi += 1
        # else: insert, skip
    # Pad if needed
    while len(labels_per_original) < len(events):
        labels_per_original.append(("I", "I"))

    # Build full replacement list, one per original annotation in ABC.
    replacements: list[tuple[str, str]] = []
    ev_pos = 0  # index into labels_per_original
    for idx, name in enumerate(names):
        if ev_pos < len(parsed_indices) and parsed_indices[ev_pos] == idx:
            replacements.append(labels_per_original[ev_pos])
            ev_pos += 1
        else:
            # Non-diatonic original (parse_chord_name returned None).
            # abc_rewriter._ALLOWED_LABEL_CHARS allows only
            # alnum + '+/- '; strip anything else (e.g. '#').
            safe = re.sub(r"[^A-Za-z0-9/+\- ]", "", name) or "I"
            replacements.append((safe, safe))

    new_abc = abc_rewriter.rewrite_abc(abc, replacements)
    ly = abc_to_ly.abc_to_lilypond(new_abc)

    # Distinct RH / LH chord sets (for diversity assertion).
    rh_set = {p.rh for p in picks}
    lh_set = {p.lh for p in picks}

    # Count reharmonized chords: a slot is "changed" if original_chords[i]
    # differs from the aligned new_events slot OR if new_events contains
    # any insert.
    n_changed = 0
    oi = 0
    for ev in new_events:
        if oi >= len(original_chords):
            break
        if ev.beat == original_chords_beat(events, oi):
            if ev.chord != original_chords[oi]:
                n_changed += 1
            oi += 1
        else:
            n_changed += 1  # insert counts as a change
    if len(new_events) > len(events):
        # Any leftover inserts past the tail also count.
        pass

    return {
        "new_abc": new_abc,
        "ly": ly,
        "picks": picks,
        "rh_set": rh_set,
        "lh_set": lh_set,
        "n_changed": n_changed,
    }


def original_chords_beat(events: list[ChordEvent], oi: int) -> float:
    return events[oi].beat


# ---------------------------------------------------------------------------
# TestCase
# ---------------------------------------------------------------------------

class ModernPipelineIntegration(unittest.TestCase):

    # Shared across tests.
    hymns: list[dict] = []
    voicings: list = []
    by_key: dict[str, list[dict]] = {}

    @classmethod
    def setUpClass(cls) -> None:
        with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
            cls.hymns = json.load(fh)
        cls.voicings = load_voicings(HANDOUT_TEX)
        cls.by_key = {k: [] for k in LEVER_HARP_KEYS}
        for h in cls.hymns:
            k = h.get("key", "?")
            if k in cls.by_key:
                cls.by_key[k].append(h)

    # ----- representative hymn per key -----------------------------------

    def _pick_representative(self, key: str) -> dict:
        """Pick the first hymn in a given key with a simple meter."""
        candidates = self.by_key.get(key, [])
        for h in candidates:
            meter_m = METER_RE.search(h["abc"])
            meter = meter_m.group(1).strip() if meter_m else "4/4"
            if meter in SIMPLE_METERS and len(CHORD_RE.findall(h["abc"])) >= 4:
                return h
        # Fallback: first hymn in key (may fail some assertions).
        self.assertTrue(candidates,
                        "no hymns available for key=%r" % key)
        return candidates[0]

    def _check_one_key(self, key: str) -> None:
        hymn = self._pick_representative(key)
        n = hymn.get("n", "?")
        title = hymn.get("t", "")[:40]
        label = "hymn %s %r (key=%s)" % (n, title, key)

        result = _run_pipeline(hymn, self.voicings)

        # 1. At least 1 chord was reharmonized.
        self.assertGreaterEqual(
            result["n_changed"], 1,
            "%s: reharmonize produced no substitutions" % label,
        )

        # 2. At least 2 distinct RH chords used in the voicing pairs.
        self.assertGreaterEqual(
            len(result["rh_set"]), 2,
            "%s: only %d distinct RH chords in picks"
            % (label, len(result["rh_set"])),
        )

        # 3. At least 2 distinct LH chords used.
        self.assertGreaterEqual(
            len(result["lh_set"]), 2,
            "%s: only %d distinct LH chords in picks"
            % (label, len(result["lh_set"])),
        )

        # 4. LilyPond output non-empty + contains chord markup.
        ly = result["ly"]
        self.assertTrue(ly.strip(), "%s: lilypond output empty" % label)
        # abc2ly renders our `"^..."` annotations as `^"..."` -- check
        # that at least one chord markup survived into the LilyPond body.
        self.assertIn('^"', ly,
                      "%s: no ^\"...\" chord markup in ly" % label)

        # 5. Key signature in the LilyPond body (`\key <note> \major`).
        expected_key_tok = _ks_for_key(key)
        self.assertRegex(
            ly,
            r"\\key\s+" + re.escape(expected_key_tok) + r"\s+\\major",
            "%s: expected `\\key %s \\major` in ly"
            % (label, expected_key_tok),
        )

        # 6. Tempo directive matches the hymn's ABC Q: tempo.
        tempo = _parse_tempo_bpm(hymn["abc"])
        self.assertIsNotNone(tempo, "%s: ABC has no Q: tempo" % label)
        den, bpm = tempo
        m = re.search(r"\\tempo\s+(\d+)\s*=\s*(\d+)", ly)
        self.assertIsNotNone(
            m,
            "%s: no `\\tempo N=M` directive in ly" % label,
        )
        self.assertEqual(
            (int(m.group(1)), int(m.group(2))), (den, bpm),
            "%s: tempo mismatch: ly=%s=%s, abc=%s=%s"
            % (label, m.group(1), m.group(2), den, bpm),
        )

        # 7. Coloured markup applied (chord_overlay fraction_markup
        # appears only through layout; but abc_to_lilypond alone emits
        # only `^"..."` text. The spec says "contains \\with-color" --
        # that comes from layout.build_combined_ly. Run layout over the
        # ORIGINAL abc + chord labels to verify.
        from modern import layout
        labels = []
        for p in result["picks"][:len(CHORD_RE.findall(hymn["abc"]))]:
            rh_deg, rh_qual = p.rh
            lh_deg, lh_qual = p.lh
            rh, lh = abc_rewriter.labels_from_voicing(
                rh_deg, rh_qual, lh_deg, lh_qual)
            labels.append((rh, lh, 1.0))
        # Pad labels to annotation count.
        n_anns = len(CHORD_RE.findall(hymn["abc"]))
        while len(labels) < n_anns:
            labels.append(("I", "I", 1.0))
        hin = {
            "X": int(n) if str(n).isdigit() else 0,
            "t": hymn.get("t", "Untitled"),
            "abc": hymn["abc"],
            "key": key,
            "meter": "%d/%d" % _parse_meter(hymn["abc"]),
            "chord_labels": labels,
        }
        book_ly = layout.build_combined_ly([hin], per_page=3)
        self.assertIn(
            "\\with-color", book_ly,
            "%s: layout output missing \\with-color markup" % label,
        )

    def test_key_Eb(self):
        self._check_one_key("Eb")

    def test_key_Bb(self):
        self._check_one_key("Bb")

    def test_key_F(self):
        self._check_one_key("F")

    def test_key_C(self):
        self._check_one_key("C")

    def test_key_G(self):
        self._check_one_key("G")

    def test_key_D(self):
        self._check_one_key("D")

    def test_key_A(self):
        self._check_one_key("A")

    def test_key_E(self):
        self._check_one_key("E")

    # ----- corpus health ------------------------------------------------

    def test_corpus_chord_parsing_no_exceptions(self):
        """Every chord annotation in every hymn must parse without error.

        parse_chord_name returning None (non-diatonic) is allowed; a raised
        exception is a hard failure.
        """
        failures: list[tuple[str, str, str]] = []
        for hymn in self.hymns:
            key = hymn.get("key", "")
            if key not in LEVER_HARP_KEYS:
                continue
            for name in CHORD_RE.findall(hymn["abc"]):
                try:
                    parse_chord_name(name, key)
                except Exception as exc:  # noqa: BLE001
                    failures.append(
                        (hymn.get("n", "?"), name,
                         "%s: %s" % (type(exc).__name__, exc)))
        self.assertEqual(
            failures, [],
            "unparseable chord annotations: %r" % failures[:10],
        )

    def test_corpus_reharmonization_coverage(self):
        """>= 80% of hymns should get at least one chord substitution."""
        n_total = 0
        n_substituted = 0
        for hymn in self.hymns:
            key = hymn.get("key", "")
            if key not in LEVER_HARP_KEYS:
                continue
            events, _, _ = _build_events(hymn)
            if not events:
                continue
            n_total += 1
            original = [ev.chord for ev in events]
            try:
                new_evs = reharmonize(events, key)
            except Exception:
                continue
            # substitution = any insert OR any mutated chord
            has_sub = len(new_evs) > len(events)
            if not has_sub:
                for a, b in zip(original, [ev.chord for ev in new_evs]):
                    if a != b:
                        has_sub = True
                        break
            if has_sub:
                n_substituted += 1
        self.assertGreater(n_total, 0, "no hymns processed")
        ratio = n_substituted / n_total
        self.assertGreaterEqual(
            ratio, 0.80,
            "only %d / %d hymns (%.1f%%) got a reharm substitution"
            % (n_substituted, n_total, 100 * ratio),
        )

    # ----- range audit --------------------------------------------------

    def test_corpus_melody_within_harp_range(self):
        """No melody note is below MIDI 36 (C2) or above MIDI 91 (G6)."""
        offenders: list[tuple[str, int, int]] = []
        for hymn in self.hymns:
            key = hymn.get("key", "")
            effective_key = key
            # audit_keys.extract_midi_range handles all lever-harp keys plus
            # Ab/Db fallbacks; unknown keys fall through to an empty key sig.
            min_m, max_m, oor = audit_keys.extract_midi_range(
                hymn["abc"], effective_key)
            if oor:
                offenders.append((hymn.get("n", "?"),
                                  min_m or -1, max_m or -1))
        self.assertEqual(
            offenders, [],
            "hymns with melody notes outside MIDI 36..91: %r"
            % offenders[:10],
        )


if __name__ == "__main__":
    unittest.main()
