"""Rewrite ABC lead-sheet chord annotations into paired RH/LH labels.

ABC chord annotations look like `"^C"` or `"_Am"` attached to a melody note.
This module tokenizes them with a hand-written character scanner (no regex),
then replaces each with a pair: `"^RH-label""_LH-label"`.
"""

from typing import Iterator


# Allowed characters inside ASCII chord-name labels we emit.
# Includes '#' and 'b' so non-diatonic source-ABC chord symbols (e.g. 'F#7',
# 'Bb', 'C#m') pass through unchanged. Parentheses allow parenthetical
# qualifiers like 'V7(b9)'. Still strictly ASCII: no quotes, backslashes, or
# control characters.
_ALLOWED_LABEL_CHARS = set(
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "+/- #()"
)


def iter_chord_annotations(abc: str) -> Iterator[tuple[int, int, str]]:
    """Yield (start_index, end_index_exclusive, chord_name) for each
    `"^X"` or `"_X"` annotation.

    The chord_name has the leading '^' or '_' stripped. start_index points at
    the opening quote; end_index_exclusive points one past the closing quote.

    Ignores quoted text inside header/lyric lines (lines starting with one of
    the ABC info fields like `X:`, `T:`, `w:` etc.). In OpenHymnal ABC, body
    `"..."` regions are chord annotations only.
    """
    n = len(abc)
    i = 0
    at_line_start = True
    in_header_line = False

    while i < n:
        ch = abc[i]

        if at_line_start:
            # Detect ABC info field line: a single letter followed by ':' at
            # column 0. Also skip stylesheet directive lines `%%...` and
            # comment lines `%...`.
            in_header_line = False
            if ch == "%":
                in_header_line = True
            elif (
                i + 1 < n
                and (("A" <= ch <= "Z") or ("a" <= ch <= "z"))
                and abc[i + 1] == ":"
            ):
                in_header_line = True
            at_line_start = False

        if ch == "\n":
            at_line_start = True
            in_header_line = False
            i += 1
            continue

        if ch == '"' and not in_header_line:
            # Scan until the matching closing quote. ABC has no backslash
            # escape inside annotations, so a plain scan is correct.
            start = i
            j = i + 1
            while j < n and abc[j] != '"' and abc[j] != "\n":
                j += 1
            if j >= n or abc[j] != '"':
                # Unterminated — bail out without yielding.
                i = j
                continue
            inner = abc[start + 1 : j]
            end_excl = j + 1
            if inner and inner[0] in ("^", "_", "<", ">", "@"):
                placement = inner[0]
                name = inner[1:]
                if placement in ("^", "_"):
                    yield (start, end_excl, name)
                # '<', '>', '@' are positioned annotations — treat as
                # annotation but skip (not chords). For OpenHymnal we don't
                # expect these; ignore silently.
            else:
                # No leading placement marker => standard ABC chord-symbol
                # annotation (e.g. `"C"`). Yield it as a chord too.
                yield (start, end_excl, inner)
            i = end_excl
            continue

        i += 1


def _validate_label(label: str) -> None:
    for c in label:
        if c not in _ALLOWED_LABEL_CHARS:
            raise ValueError(
                "label contains disallowed character %r in %r" % (c, label)
            )


def rewrite_abc(abc: str, replacements: list[tuple[str, str]]) -> str:
    """Replace each chord annotation with a `"^RH""_LH"` pair, in order.

    Raises ValueError if `len(replacements)` does not match the number of
    annotations found, or if any label contains non-ASCII / disallowed chars.
    """
    spans = list(iter_chord_annotations(abc))
    if len(spans) != len(replacements):
        raise ValueError(
            "annotation count mismatch: abc has %d, replacements has %d"
            % (len(spans), len(replacements))
        )

    for rh, lh in replacements:
        if not rh.isascii() or not lh.isascii():
            raise ValueError("labels must be ASCII: %r %r" % (rh, lh))
        _validate_label(rh)
        _validate_label(lh)

    out_parts: list[str] = []
    cursor = 0
    for (start, end_excl, _name), (rh, lh) in zip(spans, replacements):
        out_parts.append(abc[cursor:start])
        # Both above the staff, stacked: LH first (closer to staff = denominator),
        # RH second (farther from staff = numerator). abcm2ps stacks '^' annotations
        # in reverse order -- later ones go higher.
        out_parts.append('"^%s""^%s"' % (lh, rh))
        cursor = end_excl
    out_parts.append(abc[cursor:])
    return "".join(out_parts)


# Roman-numeral mapping. Lowercase for the "minor-ish" diatonic degrees.
_ROMAN_UPPER = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
_ROMAN_LOWER = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi", 7: "vii"}
_LOWERCASE_DEGREES = {2, 3, 6, 7}

_QUALITY_SUFFIX = {
    "":      "",
    "m":     "",      # case is carried by the roman numeral
    "m7":    "m7",
    "7":     "7",
    "maj7":  "M7",
    "dim":   "o",
    "dim7":  "o7",
    "hdim7": "07",
    "sus2":  "s2",
    "sus4":  "s4",
    "6":     "6",
    "m6":    "m6",
}


def labels_from_voicing(
    rh_rom: int, rh_qual: str, lh_rom: int, lh_qual: str
) -> tuple[str, str]:
    """Convert (degree, quality) for both hands to ASCII labels."""

    def one(deg: int, qual: str) -> str:
        if deg not in _ROMAN_UPPER:
            raise ValueError("degree out of range 1-7: %r" % (deg,))
        if qual not in _QUALITY_SUFFIX:
            raise ValueError("unknown quality %r" % (qual,))
        if deg in _LOWERCASE_DEGREES:
            base = _ROMAN_LOWER[deg]
        else:
            base = _ROMAN_UPPER[deg]
        return base + _QUALITY_SUFFIX[qual]

    return (one(rh_rom, rh_qual), one(lh_rom, lh_qual))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> int:
    failures = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        if cond:
            print("PASS  %s" % name)
        else:
            failures += 1
            print("FAIL  %s  %s" % (name, detail))

    # 1. Parse 1 annotation.
    abc1 = 'X: 1\nK: C\n"^C"D'
    spans1 = list(iter_chord_annotations(abc1))
    expected_start = abc1.index('"^C"')
    check(
        "parse_1_annotation",
        spans1 == [(expected_start, expected_start + 4, "C")],
        detail=repr(spans1),
    )

    # 2. Parse 3 annotations.
    abc2 = '"^C"D "^Am"E "^G7"F'
    spans2 = list(iter_chord_annotations(abc2))
    check(
        "parse_3_annotations",
        len(spans2) == 3
        and [s[2] for s in spans2] == ["C", "Am", "G7"],
        detail=repr(spans2),
    )

    # 3. Rewrite roundtrip.
    abc3 = '...\"^C\"D...\"^G\"E...'
    new3 = rewrite_abc(abc3, [("V", "I"), ("ii", "V")])
    check(
        "rewrite_first_pair",
        '"^V""_I"' in new3,
        detail=new3,
    )
    check(
        "rewrite_second_pair",
        '"^ii""_V"' in new3,
        detail=new3,
    )
    check(
        "rewrite_preserves_text",
        new3.startswith("...") and new3.endswith("...") and "D..." in new3 and "E..." in new3,
        detail=new3,
    )

    # 4. Length mismatch raises.
    abc4 = '"^C"D "^G"E'
    raised = False
    try:
        rewrite_abc(abc4, [("a", "b")])
    except ValueError:
        raised = True
    check("length_mismatch_raises", raised)

    # 5. Labels conversion.
    labels = labels_from_voicing(5, "7", 2, "m7")
    check(
        "labels_V7_iim7",
        labels == ("V7", "iim7"),
        detail=repr(labels),
    )

    # Extra: spec examples from the docstring.
    check(
        "labels_vii_hdim7",
        labels_from_voicing(7, "hdim7", 1, "")[0] == "vii07",
    )
    check(
        "labels_vi_plain",
        labels_from_voicing(6, "", 1, "")[0] == "vi",
    )

    # Extra: header line with a colon shouldn't parse as a chord.
    abc6 = 'T: My "Tune"\nK: C\n"^F"G'
    spans6 = list(iter_chord_annotations(abc6))
    check(
        "header_quotes_ignored",
        len(spans6) == 1 and spans6[0][2] == "F",
        detail=repr(spans6),
    )

    # Extra: below-placed annotation rewrites to RH-above/LH-below pair.
    abc7 = '"_Am"D'
    new7 = rewrite_abc(abc7, [("vi", "I")])
    check(
        "below_rewrites_to_pair",
        new7 == '"^vi""_I"D',
        detail=new7,
    )

    # Extra: accidentals (# and b) and parens allowed in labels so that
    # non-diatonic source chord symbols can pass through unchanged.
    abc_acc = '"^F#7"D "^Bb"E "^V7(b9)"F'
    new_acc = rewrite_abc(abc_acc, [("F#7", "F#7"), ("Bb", "Bb"),
                                     ("V7(b9)", "V7(b9)")])
    check(
        "accidentals_and_parens_allowed",
        '"^F#7""^F#7"' in new_acc and '"^Bb""^Bb"' in new_acc
        and '"^V7(b9)""^V7(b9)"' in new_acc,
        detail=new_acc,
    )

    # Disallowed characters still rejected: quote, backslash, '!' etc.
    for bad_char in ("!", "\\", "*"):
        raised = False
        try:
            rewrite_abc('"^C"D', [("I" + bad_char, "I")])
        except ValueError:
            raised = True
        check("reject_char_%s" % repr(bad_char), raised)

    # Extra: rewrite preserves bytes outside annotations exactly.
    abc8 = 'X: 1\nT: Hymn\nM: 4/4\nL: 1/4\nK: G\n|"^G"G2 "^D"A2|\nw: a-men\n'
    new8 = rewrite_abc(abc8, [("I", "I"), ("V", "V")])
    # Strip the two annotations from each and compare the residue.
    def strip_anns(s: str) -> str:
        out = []
        i = 0
        in_hdr = False
        line_start = True
        while i < len(s):
            c = s[i]
            if line_start:
                in_hdr = c == "%" or (
                    i + 1 < len(s)
                    and (("A" <= c <= "Z") or ("a" <= c <= "z"))
                    and s[i + 1] == ":"
                )
                line_start = False
            if c == "\n":
                line_start = True
                in_hdr = False
                out.append(c)
                i += 1
                continue
            if c == '"' and not in_hdr:
                j = i + 1
                while j < len(s) and s[j] != '"':
                    j += 1
                i = j + 1
                continue
            out.append(c)
            i += 1
        return "".join(out)

    check(
        "rewrite_preserves_non_annotation_bytes",
        strip_anns(abc8) == strip_anns(new8),
    )

    print()
    if failures:
        print("FAILURES: %d" % failures)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_run_tests())
