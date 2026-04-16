"""Build LilyPond \\markup fragments for the stacked RH/LH chord fractions.

Each chord annotation in the lead sheet is rendered as a two-line stack:

    navy RH label     (e.g. V7)
    burgundy LH label (e.g. I)

Both lines use TeX Gyre Pagella Bold (the Palatino clone shipped with
TeX Live). Quality markers after the Roman numeral are rendered as
smaller superscripts, matching the handout styling in handout.tex
(\\Ro / \\osf macros). Unicode quality glyphs that TeX Gyre Pagella
Bold supports:

    U+0394 "Greek Capital Delta"         => maj7  (handout: $\\Delta$)
    U+00B0 "Degree Sign"                 => dim   (handout: $^\\circ$)
    U+00F8 "Latin Small O w/ Stroke"     => hdim7 (handout: varnothing
                                                   fallback -- the
                                                   Palatino slashed-o
                                                   glyph is our closest
                                                   bold-Palatino match.)

All three glyphs are present in the fc-list charset for
"TeX Gyre Pagella:style=Bold" (verified at build time).

Public API:
    label_to_markup(label: str, color_tuple: tuple) -> str
        Return a LilyPond \\markup block for a single Roman-numeral label.

    fraction_markup(rh: str, lh: str) -> str
        Return a LilyPond \\markup block stacking rh above lh with the
        navy/burgundy colors.

    make_chord_voice(labels) -> str
        (Unused by the current pipeline but kept per the spec.)
        Returns a LilyPond voice that renders each chord at its beat.

Python source is pure ASCII. Unicode quality glyphs are emitted into
the LilyPond source via "\\uXXXX" escape sequences; LilyPond accepts
UTF-8 in markup strings.
"""

from __future__ import annotations

# RH = navy from the handout (#1F4E79 -> rgb 0.122, 0.306, 0.475)
RH_COLOR = (0.122, 0.306, 0.475)
# LH = burgundy from the handout (#7B2B2B -> rgb 0.482, 0.169, 0.169)
LH_COLOR = (0.482, 0.169, 0.169)

# Unicode glyphs. Kept as escape sequences so the source stays ASCII.
_DELTA = "\u0394"   # maj7
_DEG   = "\u00b0"   # diminished
_HDIM  = "\u00f8"   # half-diminished (o-slash)

# Baseline skip between RH (navy) and LH (burgundy) rows of the
# fraction. Handout uses \arraystretch{0.8} with Palatino at ~13pt;
# LilyPond fontsize #2 is ~13pt, and 2.8 gives a visibly-separated
# stack that still reads as a fraction. Lower values (2.2) collide
# the ascenders/descenders across the two rows.
_BASELINE_SKIP = 2.0

# Set of ASCII characters that end the Roman-numeral "base" portion.
# Everything after the first such character is treated as quality.
_ROMAN_CHARS = set("IVXivx")


def _split_base_quality(label):
    """Split label into (base, quality).

    "V7"    -> ("V",  "7")
    "iim7"  -> ("ii", "m7")
    "IM7"   -> ("I",  "M7")
    "viio7" -> ("vii","o7")
    "vii07" -> ("vii","07")   # 0 used as half-dim stand-in
    """
    if not label:
        return ("", "")
    i = 0
    while i < len(label) and label[i] in _ROMAN_CHARS:
        i += 1
    # Guard: if no Roman chars detected (odd label), leave the whole
    # string as the base.
    if i == 0:
        return (label, "")
    return (label[:i], label[i:])


def _color_cmd(rgb):
    r, g, b = rgb
    return "#(rgb-color %.3f %.3f %.3f)" % (r, g, b)


def _translate_quality(quality):
    """Turn the ASCII quality suffix into the Unicode-enriched form we
    want to display in the superscript.

    Examples (all strings — left is ASCII input, right is the Unicode
    output, shown here with Python escapes):

        "7"   -> "7"
        "m7"  -> "m7"
        "M7"  -> "\\u0394"              (Delta)
        "o"   -> "\\u00b0"              (degree)
        "o7"  -> "\\u00b07"
        "07"  -> "\\u00f87"             (o-slash + 7)
        "0"   -> "\\u00f8"
        "s2"  -> "s2"
        "s4"  -> "s4"
        "m9"  -> "m9"
        "m11" -> "m11"
        "m13" -> "m13"
        "9"   -> "9"
        "11"  -> "11"
        "13"  -> "13"
        "6"   -> "6"
        "m6"  -> "m6"
    """
    if not quality:
        return ""
    # Whole-token substitutions first (handle composites cleanly).
    whole = {
        "M7":  _DELTA,
        "maj7": _DELTA,
        "o":   _DEG,
        "o7":  _DEG + "7",
        "0":   _HDIM,
        "07":  _HDIM + "7",
        "hdim7": _HDIM + "7",
        "dim": _DEG,
        "dim7": _DEG + "7",
    }
    if quality in whole:
        return whole[quality]
    return quality


def _escape_ly_string(s):
    """Escape a string for inclusion inside a LilyPond "..." markup
    literal: escape backslashes and double-quotes. Unicode passes
    through unchanged (LilyPond reads source as UTF-8).
    """
    return s.replace("\\", "").replace("\"", "")


def _quality_markup(quality):
    """LilyPond markup for a quality suffix, matching handout.tex style.

    The handout renders quality inline at the same baseline as the Roman
    numeral, NOT as a raised superscript.  Specifics from \\rndqparse:
      - "m", "q", "s" prefix letters: italic (math-style)
      - "7","6","4","2","8" digits: same size, same baseline
      - "°" (dim): true superscript (raised, smaller)
      - "ø" (half-dim): true superscript
      - "Δ" (maj7): inline, same baseline
    """
    if not quality:
        return ""
    glyph = _translate_quality(quality)
    safe = _escape_ly_string(glyph)

    # Only ° and ø get raised as true superscripts
    if safe and safe[0] in ("\u00b0", "\u00f8"):
        # Raised portion (the symbol), rest (e.g. trailing "7") inline
        sup_char = safe[0]
        rest = safe[1:]
        out = (
            "\\hspace #-0.2 "
            "\\raise #0.8 \\fontsize #-2 \\bold \"%s\""
        ) % sup_char
        if rest:
            out += " \\bold \"%s\"" % rest
        return out

    # Everything else: inline at same baseline, same size
    return "\\bold \"%s\"" % safe


def label_to_markup(label, color_rgb):
    """Return a LilyPond \\markup { ... } fragment for one label.

    Renders as: <bold Palatino base><superscript quality> in `color_rgb`.
    The returned string is a *fragment* (no outer `\\markup { ... }`),
    suitable for inclusion inside a larger markup block.
    """
    base, quality = _split_base_quality(label)
    base_safe = _escape_ly_string(base) or "?"
    color = _color_cmd(color_rgb)
    if quality:
        inner = (
            "\\concat { \\bold \"%s\" %s }"
            % (base_safe, _quality_markup(quality))
        )
    else:
        inner = "\\bold \"%s\"" % base_safe
    # Wrap in overrides: bold Palatino at +2 font-size step, in color.
    return (
        "\\with-color %s "
        "\\override #'(font-name . \"TeX Gyre Pagella Bold\") "
        "\\fontsize #2 "
        "%s" % (color, inner)
    )


def fraction_markup(rh, lh):
    """Return a \\markup { ... } block stacking rh over lh."""
    rh_block = label_to_markup(rh, RH_COLOR)
    lh_block = label_to_markup(lh, LH_COLOR)
    return (
        "\\markup { "
        "\\override #'(baseline-skip . %.2f) "
        "\\left-column { "
        "%s "
        "%s "
        "} }"
    ) % (_BASELINE_SKIP, rh_block, lh_block)


def fraction_markup_attached(rh, lh):
    """Return `^\\markup {...}` ready to be placed after a note."""
    return "^" + fraction_markup(rh, lh)


def make_chord_voice(labels):
    """Return a LilyPond voice string placing each chord markup at
    duration `dur_q` quarter notes.

    labels: [(rh_text, lh_text, duration_in_quarters), ...]

    Produces a voice of invisible spacer notes (s4, s2, etc.) each
    tagged with the chord \\markup above. Meant for parallel-voice
    usage. NOT used by the current hymnal pipeline (the main path
    inlines markups into abc2ly output instead), but kept per spec.
    """
    out = ["\\new Voice \\with { \\remove \"Note_heading_engraver\" } {"]
    out.append("  \\override TextScript.outside-staff-priority = #100")
    for rh, lh, dur_q in labels:
        dur_token = _dur_to_ly(dur_q)
        mk = fraction_markup(rh, lh)
        out.append("  s%s^%s" % (dur_token, mk))
    out.append("}")
    return "\n".join(out)


def _dur_to_ly(dur_q):
    """Quarter notes -> LilyPond duration token (approximation)."""
    q = round(dur_q * 4) / 4.0
    table = [
        (0.25, "16"),
        (0.5, "8"),
        (0.75, "8."),
        (1.0, "4"),
        (1.5, "4."),
        (2.0, "2"),
        (3.0, "2."),
        (4.0, "1"),
    ]
    best = "4"
    best_err = 1e9
    for val, tok in table:
        err = abs(q - val)
        if err < best_err:
            best_err = err
            best = tok
    return best


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = ["I", "V7", "iim7", "IM7", "viio7", "vii07", "IVM7", "v",
               "iim11", "Is4", "IVs2"]
    for l in samples:
        print(l, "=>", label_to_markup(l, RH_COLOR))
    print()
    print("V7/I ->", fraction_markup("V7", "I"))
