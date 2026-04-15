"""Unit tests for modern/reharm_rules.py.

Run: python3.10 -m unittest modern.test_reharm_rules -v
"""

from __future__ import annotations

import unittest

from modern.reharm_rules import (
    ChordEvent,
    chord_tones,
    clashes,
    parse_chord_name,
    reharmonize,
)


def mk(beat, dur, chord, melody=None, strong=False, cadence=False, dest=False):
    return ChordEvent(
        beat=beat,
        duration=dur,
        chord=chord,
        melody_pitches=list(melody or []),
        is_strong_beat=strong,
        is_cadence=cadence,
        is_destination=dest,
    )


def chords(events):
    return [e.chord for e in events]


class TestChordTones(unittest.TestCase):

    def test_I_triad_in_C(self):
        self.assertEqual(chord_tones((1, ""), "C"), [0, 4, 7])

    def test_V7_in_C(self):
        self.assertEqual(chord_tones((5, "7"), "C"), [7, 11, 2, 5])

    def test_vii_dim_in_C(self):
        self.assertEqual(chord_tones((7, "dim"), "C"), [11, 2, 5])

    def test_ii_m7_in_G(self):
        # ii in G is A-minor7 -> A C E G = pcs 9, 0, 4, 7.
        self.assertEqual(chord_tones((2, "m7"), "G"), [9, 0, 4, 7])


class TestClashes(unittest.TestCase):

    def test_minor_second_above_root_clashes(self):
        # C triad + Db (pc 1) is a half-step above C (pc 0).
        self.assertTrue(clashes((1, ""), "C", 1))

    def test_major_seventh_below_root_clashes(self):
        # C triad + B (pc 11) is a half-step below C.
        self.assertTrue(clashes((1, ""), "C", 11))

    def test_consonant_fifth_does_not_clash(self):
        self.assertFalse(clashes((1, ""), "C", 7))

    def test_chord_tone_does_not_clash(self):
        # Melody on E (pc 4) is the 3rd of C major -- consonant.
        self.assertFalse(clashes((1, ""), "C", 4))


class TestParseChordName(unittest.TestCase):

    def test_plain_major(self):
        self.assertEqual(parse_chord_name("C", "C"), (1, ""))

    def test_minor(self):
        self.assertEqual(parse_chord_name("Am", "C"), (6, "m"))

    def test_dominant_seventh(self):
        self.assertEqual(parse_chord_name("G7", "C"), (5, "7"))

    def test_maj7(self):
        self.assertEqual(parse_chord_name("Fmaj7", "C"), (4, "maj7"))

    def test_sharp_minor_in_G(self):
        # F#m is the vii chord of G (parsed as minor triad, not dim).
        self.assertEqual(parse_chord_name("F#m", "G"), (7, "m"))

    def test_non_diatonic_returns_none(self):
        # F#m is NOT diatonic to C (F# is not in C major).
        self.assertIsNone(parse_chord_name("F#m", "C"))

    def test_bb_in_bb_key(self):
        self.assertEqual(parse_chord_name("Bb", "Bb"), (1, ""))

    def test_bb_not_diatonic_to_c(self):
        self.assertIsNone(parse_chord_name("Bb", "C"))

    def test_slash_chord_uses_root(self):
        # Slash-chord bass is ignored; we key off the root letter.
        self.assertEqual(parse_chord_name("E/C", "C"), (3, ""))

    def test_bdim(self):
        self.assertEqual(parse_chord_name("Bdim", "C"), (7, "dim"))


class TestReharmonizeEdgeCases(unittest.TestCase):

    def test_empty_event_list(self):
        self.assertEqual(reharmonize([], "C"), [])

    def test_single_chord_destination_unchanged(self):
        evs = [mk(0.0, 2.0, (1, ""), melody=[60], strong=True, dest=True)]
        out = reharmonize(evs, "C")
        self.assertEqual(len(out), 1)
        # Destination I with root in melody may be promoted to maj7 by rule 6.
        self.assertEqual(out[0].chord[0], 1)
        self.assertIn(out[0].chord[1], ("", "maj7"))

    def test_single_non_destination_IV_becomes_ii(self):
        # Rule 1 always runs when not a destination.
        evs = [mk(0.0, 1.0, (4, ""), melody=[65])]
        self.assertEqual(chords(reharmonize(evs, "C")), [(2, "m7")])

    def test_unsupported_key_raises(self):
        with self.assertRaises(ValueError):
            reharmonize([], "F#")

    def test_returns_new_list_not_mutating_input(self):
        evs = [mk(0.0, 1.0, (4, ""), melody=[65])]
        before = evs[0].chord
        reharmonize(evs, "C")
        # Input event still has the original chord.
        self.assertEqual(evs[0].chord, before)


class TestReharmSubstitutionRules(unittest.TestCase):

    def test_rule1_IV_to_ii_on_journey(self):
        evs = [
            mk(0.0, 1.0, (4, ""), melody=[65]),
            mk(1.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # The journey IV should become ii(m7).
        self.assertEqual(out[0].chord, (2, "m7"))

    def test_rule1_IV_blocked_by_melody_clash(self):
        # Melody on E (pc 4) is a half-step from F (pc 5), the root of IV/ii.
        evs = [
            mk(0.0, 1.0, (4, ""), melody=[64]),
            mk(1.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # IV stays IV -- ii candidate also clashes with E, so no sub.
        self.assertEqual(out[0].chord, (4, ""))

    def test_rule1_skipped_on_destination(self):
        # IV as a destination is NOT subbed to ii by rule 1.
        evs = [mk(0.0, 2.0, (4, ""), melody=[65], strong=True, dest=True)]
        out = reharmonize(evs, "C")
        self.assertEqual(out[0].chord[0], 4)

    def test_rule2_I_to_vi_on_weak_beat(self):
        # Non-dest I followed by non-dest V: rule 2 fires.
        evs = [
            mk(0.0, 1.0, (1, ""), melody=[67]),   # G consonant w/ vi
            mk(1.0, 1.0, (5, ""), melody=[67]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        self.assertEqual(out[0].chord, (6, "m7"))

    def test_rule2_blocked_by_melody_clash(self):
        # Melody F (pc 5) clashes with vi chord tone E (pc 4).
        evs = [
            mk(0.0, 1.0, (1, ""), melody=[65]),   # F
            mk(1.0, 1.0, (5, ""), melody=[67]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # Stays I -- vi would clash with F.
        self.assertEqual(out[0].chord, (1, ""))

    def test_rule2_skipped_before_destination_I(self):
        # Non-dest I immediately before destination I -> rule 2 skips.
        evs = [
            mk(0.0, 1.0, (1, ""), melody=[67]),
            mk(1.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        self.assertEqual(out[0].chord[0], 1)

    def test_rule3_vii_dim_insertion_before_destination_I(self):
        # IV prior (not V, not vii-dim) -> vii-dim splice fires.
        evs = [
            mk(0.0, 2.0, (4, ""), melody=[65]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        inserted_vii = any(e.chord == (7, "dim") for e in out)
        self.assertTrue(inserted_vii)

    def test_rule3_blocked_by_vii_melody_clash(self):
        # Melody on C (pc 0) is a half-step from B (pc 11), root of vii-dim.
        # Prior IV with this melody -> rule 3 blocked; also rule 1 blocked.
        evs = [
            mk(0.0, 2.0, (4, ""), melody=[60]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        inserted_vii = any(e.chord == (7, "dim") for e in out)
        self.assertFalse(inserted_vii)

    def test_rule4_V_to_V7_before_I(self):
        evs = [
            mk(0.0, 1.0, (1, ""), melody=[60], strong=True, dest=True),
            mk(1.0, 1.0, (5, ""), melody=[67]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # Find the V-ish chord; it should have been promoted to V7 somewhere.
        has_v7 = any(e.chord == (5, "7") for e in out)
        self.assertTrue(has_v7)

    def test_rule4_blocked_by_V7_melody_clash(self):
        # Melody A (pc 9) is a half-step from V7's seventh F (pc 5)? no.
        # V7 tones = {G, B, D, F} = {7, 11, 2, 5}. Half-step pcs: {6,8,10,1,3,4}.
        # Use melody E (pc 4) which clashes F (pc 5).
        evs = [
            mk(0.0, 1.0, (5, ""), melody=[64]),  # E clashes F
            mk(1.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # V did not become V7 because the 7th (F) clashes with melody E.
        # However rule 5 may wrap it in sus4 -- find any remaining V (plain).
        v_remains = any(e.chord == (5, "") for e in out)
        v7_added = any(e.chord == (5, "7") for e in out)
        self.assertTrue(v_remains)
        self.assertFalse(v7_added)

    def test_rule5_Vsus4_delay_on_cadence(self):
        # Final V -> I cadence inserts a Vsus4 before the V.
        evs = [
            mk(0.0, 2.0, (5, ""), melody=[67], strong=True),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        has_sus4 = any(e.chord == (5, "sus4") for e in out)
        self.assertTrue(has_sus4)

    def test_rule5_not_triggered_without_cadence_flag(self):
        evs = [
            mk(0.0, 2.0, (5, ""), melody=[67]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        has_sus4 = any(e.chord == (5, "sus4") for e in out)
        self.assertFalse(has_sus4)

    def test_rule6_I_to_Imaj7_when_safe(self):
        # Destination I with 3rd in melody; no 4 and no half-step rub with B.
        evs = [mk(0.0, 2.0, (1, ""), melody=[64], strong=True, dest=True)]
        out = reharmonize(evs, "C")
        self.assertEqual(out[0].chord, (1, "maj7"))

    def test_rule6_I_maj7_blocked_by_fourth_in_melody(self):
        # F (pc 5) = scale degree 4 in C -> guard blocks maj7 extension.
        evs = [mk(0.0, 2.0, (1, ""), melody=[60, 65],
                  strong=True, dest=True)]
        out = reharmonize(evs, "C")
        self.assertEqual(out[0].chord, (1, ""))

    def test_all_destination_sequence_leaves_journey_rules_idle(self):
        # With every event a destination, rules 1 and 2 cannot fire.
        evs = [
            mk(0.0, 2.0, (1, ""),  melody=[60], strong=True, dest=True),
            mk(2.0, 2.0, (4, ""),  melody=[65], strong=True, dest=True),
            mk(4.0, 2.0, (1, ""),  melody=[60], strong=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        # No ii-m7 and no vi-m7 -- rules 1 and 2 are journey-only.
        has_ii = any(e.chord == (2, "m7") for e in out)
        has_vi = any(e.chord == (6, "m7") for e in out)
        self.assertFalse(has_ii)
        self.assertFalse(has_vi)


class TestReharmPriority(unittest.TestCase):

    def test_rule1_runs_before_rule3_insertion(self):
        # Non-dest IV before dest-I: rule 1 converts IV->ii, then rule 3
        # inserts vii-dim. Final sequence has ii at index 0, vii-dim at 1.
        evs = [
            mk(0.0, 2.0, (4, ""), melody=[65]),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        seq = chords(out)
        self.assertEqual(seq[0], (2, "m7"))
        self.assertEqual(seq[1], (7, "dim"))

    def test_rule4_and_rule5_compose(self):
        # V before final cadential I: rule 4 promotes to V7; rule 5 inserts
        # a Vsus4 immediately before it.
        evs = [
            mk(0.0, 2.0, (5, ""), melody=[67], strong=True),
            mk(2.0, 2.0, (1, ""), melody=[60], strong=True,
               cadence=True, dest=True),
        ]
        out = reharmonize(evs, "C")
        seq = chords(out)
        # Expect sus4 THEN V7 THEN I (or maj7 of I).
        self.assertEqual(seq[0], (5, "sus4"))
        self.assertEqual(seq[1], (5, "7"))
        self.assertEqual(seq[-1][0], 1)


if __name__ == "__main__":
    unittest.main()
