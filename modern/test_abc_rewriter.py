"""Unit tests for modern/abc_rewriter.py.

Run: python3.10 -m unittest modern.test_abc_rewriter -v
"""

from __future__ import annotations

import unittest

from modern.abc_rewriter import (
    iter_chord_annotations,
    labels_from_voicing,
    rewrite_abc,
)


class TestIterChordAnnotations(unittest.TestCase):

    def test_single_annotation(self):
        abc = 'X: 1\nK: C\n"^C"D'
        spans = list(iter_chord_annotations(abc))
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "C")

    def test_three_annotations(self):
        abc = '"^C"D "^Am"E "^G7"F'
        spans = list(iter_chord_annotations(abc))
        self.assertEqual([s[2] for s in spans], ["C", "Am", "G7"])

    def test_header_quotes_ignored(self):
        # Title line with quoted word must not be parsed as a chord.
        abc = 'X: 1\nT: "Holy" Hymn\nC: composer\nK: C\n"^C"D "^Am"E "^G7"F'
        spans = list(iter_chord_annotations(abc))
        self.assertEqual(len(spans), 3)
        self.assertEqual([s[2] for s in spans], ["C", "Am", "G7"])

    def test_below_annotation_is_captured(self):
        # "_Am" (below-staff annotation) is still a chord annotation.
        abc = '"_Am"D'
        spans = list(iter_chord_annotations(abc))
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "Am")

    def test_comment_line_quotes_ignored(self):
        abc = '% a "quoted" comment\nK: C\n"^F"G'
        spans = list(iter_chord_annotations(abc))
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0][2], "F")

    def test_start_end_indices_are_correct(self):
        abc = 'X: 1\nK: C\n"^C"D'
        spans = list(iter_chord_annotations(abc))
        start, end, _ = spans[0]
        self.assertEqual(abc[start:end], '"^C"')

    def test_no_annotations(self):
        abc = "X: 1\nK: C\nCDEF|GABc|"
        self.assertEqual(list(iter_chord_annotations(abc)), [])


class TestRewriteAbc(unittest.TestCase):

    def test_three_replacements_produce_three_pairs(self):
        abc = '"^C"D "^Am"E "^G7"F'
        out = rewrite_abc(
            abc,
            [("I", "I"), ("vi", "I"), ("V7", "I")],
        )
        # Each replacement yields a single "^LH""^RH" pair.
        self.assertIn('"^I""^I"', out)
        self.assertIn('"^I""^vi"', out)
        self.assertIn('"^I""^V7"', out)
        # Exactly three emitted pair-starts.
        self.assertEqual(out.count('""^'), 3)

    def test_mismatched_replacement_count_raises(self):
        abc = '"^C"D "^G"E'
        with self.assertRaises(ValueError):
            rewrite_abc(abc, [("a", "b")])

    def test_too_many_replacements_raises(self):
        abc = '"^C"D'
        with self.assertRaises(ValueError):
            rewrite_abc(abc, [("a", "b"), ("c", "d")])

    def test_zero_annotations_passthrough(self):
        abc = "X: 1\nK: C\nCDEF|GABc|"
        self.assertEqual(rewrite_abc(abc, []), abc)

    def test_non_ascii_label_rejected(self):
        abc = '"^C"D'
        with self.assertRaises(ValueError):
            rewrite_abc(abc, [("I\u0394", "I")])

    def test_disallowed_char_rejected(self):
        abc = '"^C"D'
        # '!' is not in the label alphabet.
        with self.assertRaises(ValueError):
            rewrite_abc(abc, [("I!", "I")])

    def test_accidentals_in_labels_are_allowed(self):
        # Non-diatonic source chord symbols (e.g. 'F#7', 'C#m', 'Bb')
        # must pass through the rewriter unchanged.
        abc = '"^F#7"D "^C#m"E "^Bb"F'
        out = rewrite_abc(abc, [("F#7", "F#7"), ("C#m", "C#m"),
                                ("Bb", "Bb")])
        self.assertIn('"^F#7""^F#7"', out)
        self.assertIn('"^C#m""^C#m"', out)
        self.assertIn('"^Bb""^Bb"', out)

    def test_parens_in_labels_are_allowed(self):
        # Parenthetical qualifiers like '(b9)' should pass validation.
        abc = '"^C"D'
        out = rewrite_abc(abc, [("V7(b9)", "I")])
        self.assertIn('"^V7(b9)"', out)

    def test_backslash_and_quote_still_rejected(self):
        abc = '"^C"D'
        for bad in ("I\\", 'I"', "I*"):
            with self.assertRaises(ValueError):
                rewrite_abc(abc, [(bad, "I")])

    def test_preserves_surrounding_text_byte_for_byte(self):
        abc = 'X: 1\nT: Hymn\nM: 4/4\nL: 1/4\nK: G\n|"^G"G2 "^D"A2|\n'
        out = rewrite_abc(abc, [("I", "I"), ("V", "V")])
        # Text before the first annotation should be identical.
        self.assertTrue(out.startswith('X: 1\nT: Hymn\nM: 4/4\nL: 1/4\nK: G\n|'))
        # Trailing newline preserved.
        self.assertTrue(out.endswith("|\n"))

    def test_pair_order_LH_first_RH_second(self):
        # Docstring says '"^LH""^RH"' ordering (LH numerator-side first).
        abc = '"^C"D'
        out = rewrite_abc(abc, [("V", "I")])
        # rh="V", lh="I" -> emits "^I""^V"
        self.assertIn('"^I""^V"', out)

    def test_below_annotation_rewrites_to_pair(self):
        abc = '"_Am"D'
        out = rewrite_abc(abc, [("vi", "I")])
        self.assertEqual(out, '"^I""^vi"D')


class TestLabelsFromVoicing(unittest.TestCase):

    def test_V7_I(self):
        self.assertEqual(labels_from_voicing(5, "7", 1, ""), ("V7", "I"))

    def test_ii_m7_label(self):
        # Degree 2 is lowercase; m7 suffix retained -> "iim7".
        self.assertEqual(labels_from_voicing(2, "m7", 1, ""), ("iim7", "I"))

    def test_vii_hdim7_label_is_vii07(self):
        # Per _QUALITY_SUFFIX, hdim7 -> "07"; degree 7 lowercases -> "vii07".
        self.assertEqual(
            labels_from_voicing(7, "hdim7", 1, ""),
            ("vii07", "I"),
        )

    def test_vi_plain_minor(self):
        # Case carries the minor quality, no suffix for plain triad.
        self.assertEqual(labels_from_voicing(6, "", 1, "")[0], "vi")

    def test_IV_maj7_is_IVM7(self):
        self.assertEqual(
            labels_from_voicing(4, "maj7", 1, ""),
            ("IVM7", "I"),
        )

    def test_bad_degree_raises(self):
        with self.assertRaises(ValueError):
            labels_from_voicing(8, "", 1, "")

    def test_bad_quality_raises(self):
        with self.assertRaises(ValueError):
            labels_from_voicing(1, "bogus", 1, "")

    def test_lowercase_m_for_minor_ii(self):
        # Degree 2 always lowercases; "m" quality adds no extra suffix.
        self.assertEqual(labels_from_voicing(2, "m", 1, "")[0], "ii")


if __name__ == "__main__":
    unittest.main()
