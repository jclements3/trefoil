"""Build a LilyPond \\book source combining multiple hymns with
stacked-fraction RH/LH chord labels above each chord change.

Pipeline for each hymn:
  1. Rewrite the hymn's ABC chord annotations `"^Xyz"` with unique
     sentinels `"^@@CHORDn@@"` (n indexes into chord_labels).
  2. Run abc2ly on the sentinelled ABC. The resulting LilyPond has
     `^"@@CHORDn@@"` after each note that originally had a chord.
  3. Substitute `^"@@CHORDn@@"` -> `^\\markup { ... }` using
     chord_overlay.fraction_markup_attached(rh, lh).
  4. Wrap the resulting music body in a \\score block with a
     \\bookpart header (title + key).
  5. Concatenate all bookparts into one \\book preceded by a shared
     \\paper / \\layout block.

The \\paper block sets US Letter portrait with margins sized so
`per_page` hymns fit per page.

ASCII-only Python source. python3.10.
"""

from __future__ import annotations

import re
from typing import Optional

from modern import abc_rewriter
from modern import abc_to_ly
from modern import chord_overlay


LETTER_PORTRAIT_CM = (21.59, 27.94)  # (w, h)

# per_page -> (system-height, staff-size, paper-top, paper-bottom, scale)
# Tuned so the melody + chord labels per hymn fit comfortably; the
# chord-label fraction sits about 10mm above the staff.
LAYOUT_TABLE = {
    2: {
        "staff_size": 20,
        "top_margin_cm": 1.2,
        "bottom_margin_cm": 1.2,
        "left_margin_cm": 1.4,
        "right_margin_cm": 1.4,
        "between_bookpart_cm": 1.2,
        "title_font_pt": 18,
    },
    3: {
        "staff_size": 15,
        "top_margin_cm": 0.9,
        "bottom_margin_cm": 0.9,
        "left_margin_cm": 1.2,
        "right_margin_cm": 1.2,
        "between_bookpart_cm": 0.6,
        "title_font_pt": 14,
    },
    4: {
        "staff_size": 13,
        "top_margin_cm": 0.8,
        "bottom_margin_cm": 0.8,
        "left_margin_cm": 1.0,
        "right_margin_cm": 1.0,
        "between_bookpart_cm": 0.5,
        "title_font_pt": 13,
    },
}


SENTINEL_PREFIX = "@@CHORD"
SENTINEL_SUFFIX = "@@"


def _ascii_safe(s: str) -> str:
    return "".join(c if ord(c) < 128 else "?" for c in s)


def _rewrite_with_sentinels(abc: str, n_chords: int) -> tuple[str, int]:
    """Replace each `"^chord"` annotation in abc with `"^@@CHORDi@@"`.

    Uses abc_rewriter.iter_chord_annotations for the same tokenization.
    Returns (new_abc, n_matched).
    """
    spans = list(abc_rewriter.iter_chord_annotations(abc))
    if not spans:
        return (abc, 0)

    out = []
    cursor = 0
    for i, (start, end, _name) in enumerate(spans):
        out.append(abc[cursor:start])
        tag = "%s%d%s" % (SENTINEL_PREFIX, i, SENTINEL_SUFFIX)
        out.append('"^%s"' % tag)
        cursor = end
    out.append(abc[cursor:])
    return ("".join(out), len(spans))


_SENTINEL_RE = re.compile(
    r'\^"%s(\d+)%s"' % (re.escape(SENTINEL_PREFIX), re.escape(SENTINEL_SUFFIX))
)


def _substitute_markups(ly_body: str, labels: list) -> str:
    """Replace `^"@@CHORDi@@"` in ly_body with `^\\markup { rh / lh }`.

    labels: list[(rh, lh, dur_q)] -- only rh and lh are used here;
            the duration is informational.
    Any sentinel whose index is out of range is silently dropped.
    """
    def repl(m: re.Match) -> str:
        idx = int(m.group(1))
        if idx < 0 or idx >= len(labels):
            return ""
        rh, lh, _dur = labels[idx]
        return chord_overlay.fraction_markup_attached(rh, lh)

    return _SENTINEL_RE.sub(repl, ly_body)


def _strip_leading_score_config(body: str) -> str:
    """abc2ly emits `\\set Score.defaultBarType = ""` at the top of
    voicedefault. We keep this (it silences dangling-bar warnings)
    and also keep \\time / \\key so our Voice has a correct context.
    Just normalise whitespace.
    """
    return body.strip() + "\n"


def _ly_key_mode(key: str) -> tuple[str, str]:
    """Convert 'Eb' / 'C' / 'F#m' etc. into LilyPond key syntax.

    We only pass through; abc2ly already emits the correct \\key directive
    inside the music body, so our \\score doesn't need to set one.
    Returned for the title markup only.
    """
    return (key, "major")  # only used for display


_SAFE_TITLE_RE = re.compile(r'[^\x20-\x7E]')


def _safe_title(s: str) -> str:
    s = _ascii_safe(s)
    s = _SAFE_TITLE_RE.sub(" ", s)
    # Escape double-quotes for inclusion in LilyPond strings.
    return s.replace("\\", "").replace("\"", "'")


def _force_breaks_every_n_bars(body: str, n: int = 4) -> str:
    """Insert `\\break` after every Nth \\bar "|" in the music body so
    LilyPond wraps to a new system every N bars (standard lead-sheet look).
    Skips the very last bar line to avoid a dangling empty system."""
    parts = body.split('\\bar "|"')
    if len(parts) <= n:
        return body
    out = []
    for i, part in enumerate(parts):
        out.append(part)
        if i == len(parts) - 1:
            continue
        # Insert bar line back, plus \break every n-th bar (but not at the end).
        if (i + 1) % n == 0 and i < len(parts) - 1:
            out.append('\\bar "|" \\break ')
        else:
            out.append('\\bar "|"')
    return "".join(out)


def _bookpart(h: dict, body: str, layout: dict) -> str:
    """Wrap one hymn's music body in a title markup + \\score pair.

    NOTE: despite the name, this does NOT emit a separate \\bookpart
    (which would force a page break per hymn). Instead it emits a
    title \\markup followed by a \\score, both at the top level of the
    containing \\book -- LilyPond packs multiple (markup, score) pairs
    onto the same page.
    """
    title = _safe_title(str(h.get("t", "Untitled")))
    key = _safe_title(str(h.get("key", "")))
    n = h.get("X", h.get("n", "?"))

    title_pt = layout["title_font_pt"]
    staff_pt = layout["staff_size"]

    # Header markup: bold Palatino title on the left, key + number
    # on the right. Title may be long -- we cap it at 50 chars.
    if len(title) > 50:
        title = title[:47] + "..."
    header_markup = (
        "\\markup {\n"
        "    \\override #'(font-name . \"TeX Gyre Pagella Bold\")\n"
        "    \\fontsize #%d\n"
        "    \\fill-line { \"%s\" \"%s (%s)\" }\n"
        "}\n"
    ) % (max(2, title_pt - 14), "%s" % title, "key: %s" % key, str(n))

    score = (
        "%s"
        "\\score {\n"
        "  \\new Staff \\with {\n"
        "    \\override VerticalAxisGroup.staff-staff-spacing.padding = 3\n"
        "  } {\n"
        "    \\override Score.BarNumber.break-visibility = ##(#f #f #f)\n"
        "    %s\n"
        "  }\n"
        "  \\layout {\n"
        "    #(layout-set-staff-size %d)\n"
        "    ragged-right = ##f\n"
        "    ragged-last = ##t\n"
        "    \\context {\n"
        "      \\Score\n"
        "      \\override TextScript.outside-staff-priority = #100\n"
        "      \\override TextScript.padding = #1.5\n"
        "      \\override TextScript.staff-padding = #3.0\n"
        "      \\override MetronomeMark.outside-staff-priority = #1000\n"
        "      \\override MetronomeMark.padding = #2.0\n"
        "      \\override TextScript.direction = #UP\n"
        "      \\override TextScript.avoid-slur = #'outside\n"
        "      \\override SpacingSpanner.base-shortest-duration ="
        " #(ly:make-moment 1/8)\n"
        "      \\override SpacingSpanner.uniform-stretching = ##t\n"
        "    }\n"
        "  }\n"
        "}\n"
    ) % (header_markup, body, staff_pt)
    return score


def _paper_preamble(per_page: int, layout: dict) -> str:
    pw_cm, ph_cm = LETTER_PORTRAIT_CM
    return (
        "\\version \"2.22.0\"\n"
        "\n"
        "#(set-default-paper-size \"letter\")\n"
        "\n"
        "\\paper {\n"
        "  top-margin = %.2f\\cm\n"
        "  bottom-margin = %.2f\\cm\n"
        "  left-margin = %.2f\\cm\n"
        "  right-margin = %.2f\\cm\n"
        "  between-system-space = 0.8\\cm\n"
        "  between-system-padding = 0.2\\cm\n"
        "  markup-system-spacing.padding = 0.4\n"
        "  score-markup-spacing.padding = 0.3\n"
        "  score-system-spacing.padding = 0.4\n"
        "  system-system-spacing.padding = 0.5\n"
        "  ragged-bottom = ##f\n"
        "  ragged-last-bottom = ##f\n"
        "  print-page-number = ##f\n"
        "  #(define fonts\n"
        "    (make-pango-font-tree\n"
        "      \"TeX Gyre Pagella\"\n"
        "      \"TeX Gyre Pagella\"\n"
        "      \"TeX Gyre Cursor\"\n"
        "      (/ staff-height pt 20)))\n"
        "}\n"
        "\n"
    ) % (
        layout["top_margin_cm"],
        layout["bottom_margin_cm"],
        layout["left_margin_cm"],
        layout["right_margin_cm"],
    )


def _chord_labels_for_hymn(h: dict, n_anns: int) -> list:
    """Return a list of (rh, lh, dur_q) of length n_anns.

    If the hymn dict supplies `chord_labels`, use it; otherwise fall
    back to ("I", "I", 1.0) for every annotation (non-fatal, keeps
    pipeline robust if a caller hasn't populated labels).
    """
    labels = h.get("chord_labels") or []
    if len(labels) < n_anns:
        pad = [("I", "I", 1.0)] * (n_anns - len(labels))
        labels = list(labels) + pad
    elif len(labels) > n_anns:
        labels = labels[:n_anns]
    # Normalise: every entry is a 3-tuple.
    normalised = []
    for item in labels:
        if isinstance(item, (list, tuple)):
            if len(item) >= 3:
                rh, lh, dur = item[0], item[1], float(item[2])
            elif len(item) == 2:
                rh, lh, dur = item[0], item[1], 1.0
            else:
                rh, lh, dur = "I", "I", 1.0
        else:
            rh, lh, dur = "I", "I", 1.0
        normalised.append((str(rh), str(lh), dur))
    return normalised


def build_combined_ly(hymns: list, per_page: int = 2) -> str:
    """Build a complete LilyPond \\book source for `hymns`.

    hymns: [{'X': int, 't': str, 'abc': str, 'key': str, 'meter': str,
             'chord_labels': [(rh, lh, dur_q), ...]}, ...]
    per_page: 2, 3, or 4 hymns per page (portrait letter).
    """
    if per_page not in LAYOUT_TABLE:
        raise ValueError("per_page must be one of %s"
                         % list(LAYOUT_TABLE.keys()))
    layout = LAYOUT_TABLE[per_page]

    preamble = _paper_preamble(per_page, layout)

    # Build per-hymn (header-markup, score) strings.
    hymn_blocks: list[str] = []
    for h in hymns:
        abc_src = h.get("abc") or ""
        if not abc_src:
            continue
        # 1. Sentinelise annotations.
        sentinelled, n_anns = _rewrite_with_sentinels(abc_src, 0)
        # 2. Convert to LilyPond.
        try:
            body = abc_to_ly.abc_to_lilypond(sentinelled)
        except Exception as exc:
            body = (
                "\\relative c' { \\time 4/4 c1 "
                "^\\markup { \\italic \"abc2ly failed: %s\" } }"
                % _safe_title(str(exc))
            )
        # 3. Replace sentinels with markup.
        labels = _chord_labels_for_hymn(h, n_anns)
        body = _substitute_markups(body, labels)
        body = _strip_leading_score_config(body)
        body = _force_breaks_every_n_bars(body, n=4)
        hymn_blocks.append(_bookpart(h, body, layout))

    # 5. Put all hymns in a single \bookpart so LilyPond flows them
    #    naturally across pages (a hymn's systems can break onto the next
    #    page when needed, rather than forcing exactly per_page hymns).
    book = (
        "\\book {\n"
        "\\bookpart {\n"
        + "\n".join(hymn_blocks)
        + "\n}\n"
        "}\n"
    )
    return preamble + book


# Backwards-compat shim -- old callers look for build_combined_abc.
def build_combined_abc(hymns, per_page: int = 2, orientation: str = "portrait"):
    raise RuntimeError(
        "build_combined_abc has been replaced by build_combined_ly; "
        "see modern/layout_abc.py.bak for the former implementation.")
