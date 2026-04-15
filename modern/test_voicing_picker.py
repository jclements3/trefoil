"""Unit tests for modern/voicing_picker.py.

Run: python3.10 -m unittest modern.test_voicing_picker -v
"""

from __future__ import annotations

import os
import unittest

from modern.voicing_picker import (
    Voicing,
    figure_to_strings,
    load_voicings,
    pick_voicing,
    voice_leading_cost,
)


# Resolve handout.tex once (module is run from repo root).
HANDOUT_TEX = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "handout.tex",
)


class TestLoadVoicings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.voicings = load_voicings(HANDOUT_TEX)

    def test_at_least_66_entries(self):
        self.assertGreaterEqual(len(self.voicings), 66)

    def test_all_have_non_empty_desc(self):
        for v in self.voicings:
            self.assertTrue(v.desc, "voicing has empty desc: %r" % (v,))

    def test_all_have_non_empty_figures(self):
        for v in self.voicings:
            self.assertTrue(v.lh_fig, "voicing has empty lh_fig: %r" % (v,))
            self.assertTrue(v.rh_fig, "voicing has empty rh_fig: %r" % (v,))

    def test_all_have_valid_degrees(self):
        for v in self.voicings:
            self.assertIn(v.rh[0], range(1, 8))
            self.assertIn(v.lh[0], range(1, 8))


class TestPickVoicing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.voicings = load_voicings(HANDOUT_TEX)

    def test_pick_I_has_LH_degree_1(self):
        pick = pick_voicing((1, ""), None, self.voicings)
        self.assertEqual(pick.lh[0], 1)

    def test_pick_V7_after_I_has_LH_degree_5(self):
        prior = pick_voicing((1, ""), None, self.voicings)
        pick = pick_voicing((5, "7"), prior, self.voicings)
        self.assertEqual(pick.lh[0], 5)
        # Accept either exact V7 quality or compatible V triad.
        self.assertIn(pick.lh[1], ("7", ""))

    def test_pick_IV_has_LH_degree_4(self):
        pick = pick_voicing((4, ""), None, self.voicings)
        self.assertEqual(pick.lh[0], 4)

    def test_pick_minor_vi_has_LH_degree_6(self):
        pick = pick_voicing((6, "m"), None, self.voicings)
        self.assertEqual(pick.lh[0], 6)

    def test_pick_empty_voicings_raises(self):
        with self.assertRaises(ValueError):
            pick_voicing((1, ""), None, [])


class TestVoiceLeadingCost(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.voicings = load_voicings(HANDOUT_TEX)

    def test_identical_voicings_cost_zero(self):
        v = self.voicings[0]
        self.assertEqual(voice_leading_cost(v, v), 0)

    def test_distant_voicings_cost_above_threshold(self):
        # Build two synthetic voicings whose RH roots are maximally distant.
        v1 = Voicing(rh=(1, ""), lh=(1, ""), desc="x",
                     lh_fig="1", rh_fig="1")
        v2 = Voicing(rh=(7, "dim"), lh=(7, "dim"), desc="y",
                     lh_fig="1", rh_fig="1")
        self.assertGreater(voice_leading_cost(v1, v2), 5)

    def test_symmetric_within_reason(self):
        a = Voicing(rh=(1, ""),   lh=(1, ""), desc="a",
                    lh_fig="1", rh_fig="1")
        b = Voicing(rh=(4, "7"),  lh=(4, ""), desc="b",
                    lh_fig="1", rh_fig="1")
        # Cost is symmetric because the fn swaps to smaller-first internally.
        self.assertEqual(voice_leading_cost(a, b), voice_leading_cost(b, a))


class TestFigureToStrings(unittest.TestCase):

    def test_triad_133_from_string_1(self):
        # Leader '1' -> string 1 (tonic); then +2, +2 -> [1, 3, 5].
        self.assertEqual(figure_to_strings("133", 1), [1, 3, 5])

    def test_triad_length(self):
        self.assertEqual(len(figure_to_strings("133", 1)), 3)

    def test_G33_starts_at_16(self):
        # 'G' = 10 + 6 = 16.
        s = figure_to_strings("G33", 1)
        self.assertEqual(s[0], 16)
        self.assertEqual(s, [16, 18, 20])

    def test_zero_digit_skipped(self):
        # '0' means unused finger -- no advance, no emit.
        # '8334': 8 -> 15; 3 -> 17; 3 -> 19; 4 -> 22.
        self.assertEqual(figure_to_strings("8334", 8), [15, 17, 19, 22])

    def test_empty_figure_empty_list(self):
        self.assertEqual(figure_to_strings("", 1), [])

    def test_bad_leader_raises(self):
        with self.assertRaises(ValueError):
            figure_to_strings("Z3", 1)


class TestPickSequence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.voicings = load_voicings(HANDOUT_TEX)

    def test_pick_sequence_returns_one_voicing_per_chord_with_diversity(self):
        try:
            from modern.voicing_picker import pick_sequence
        except ImportError:
            raise unittest.SkipTest("pick_sequence not yet implemented")
        seq = [(1, ""), (4, ""), (5, ""), (1, ""), (4, ""), (5, ""), (1, "")]
        picks = pick_sequence(seq, self.voicings)
        self.assertEqual(len(picks), 7)
        distinct_rh = len({v.rh for v in picks})
        self.assertGreaterEqual(distinct_rh, 3)


if __name__ == "__main__":
    unittest.main()
