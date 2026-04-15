"""Voicing picker for stacked-chord (RH/LH fraction) hymn arrangements.

Parses \\se{}{}{}{}{}{}{} entries from the StackedChords section of
handout.tex and provides utilities to pick a voicing per chord, with
basic voice-leading smoothing.

Standard library only. ASCII source. python3.10+.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal, Optional

Quality = Literal[
    "", "m", "m7", "7", "maj7", "dim", "dim7", "hdim7",
    "sus2", "sus4", "6", "m6",
]
RomanChord = tuple[int, Quality]


@dataclass
class Voicing:
    rh: RomanChord
    lh: RomanChord
    desc: str
    lh_fig: str
    rh_fig: str


# ---------------------------------------------------------------------------
# Roman / quality helpers
# ---------------------------------------------------------------------------

_ROMAN_TO_DEG = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
}


def _roman_to_deg(roman: str) -> int:
    r = roman.strip().upper()
    if r not in _ROMAN_TO_DEG:
        raise ValueError("unknown roman numeral: " + repr(roman))
    return _ROMAN_TO_DEG[r]


# Map raw 2nd/4th \se argument -> normalized Quality token used in this module.
# Empty string = "major triad" when the roman is upper-case, "minor triad"
# when the roman is lower-case. We resolve case BEFORE coming here.
# Keys include the literal unicode glyphs that appear in handout.tex
# (\u0394 = Greek capital Delta, \u00f8 = o-stroke half-dim, \u00b0 = degree).
_QUAL_RAW_MAP = {
    "":         "",        # placeholder; resolved by case
    "\u0394":   "maj7",   # Delta -> maj7
    "7":        "7",
    "m7":       "m7",
    "m":        "m",
    "m6":       "m6",
    "6":        "6",
    "\u00f8" + "7": "hdim7",  # o-stroke + 7 -> half-dim 7
    "o7":       "dim7",
    "dim7":     "dim7",
    "\u00b0":   "dim",    # degree sign -> dim
    "o":        "dim",
    "s2":       "sus2",
    "s4":       "sus4",
    "q":        "sus4",   # quartal, treat as a sus4 cousin for matching
    "+8":       "",       # bell-ring octave doubling; quality unchanged
}


def _normalize_quality(roman: str, raw_qual: str) -> Quality:
    """Resolve the (roman, raw qual) pair to a normalized Quality token."""
    raw = raw_qual.strip()
    if raw in _QUAL_RAW_MAP:
        mapped = _QUAL_RAW_MAP[raw]
    else:
        # Unrecognized -> drop to triad fallback by case.
        mapped = ""
    if mapped == "":
        # major triad if upper-case roman, minor triad if lower-case
        if roman.strip() and roman.strip()[0].islower():
            return "m"
        return ""
    return mapped  # type: ignore[return-value]


# Compatibility table: which voicing-LH qualities are acceptable for a
# requested chord quality. Higher-priority (earlier) is more specific.
_COMPAT: dict[str, list[str]] = {
    "":     ["", "maj7", "6", "sus2", "sus4"],
    "maj7": ["maj7", "", "6"],
    "6":    ["6", "", "maj7"],
    "m":    ["m", "m7", "m6"],
    "m7":   ["m7", "m", "m6"],
    "m6":   ["m6", "m", "m7"],
    "7":    ["7", ""],
    "dim":  ["dim", "dim7", "hdim7"],
    "dim7": ["dim7", "dim", "hdim7"],
    "hdim7":["hdim7", "dim", "dim7"],
    "sus2": ["sus2", "", "sus4"],
    "sus4": ["sus4", "", "sus2"],
}


def _quality_priority(want: str, got: str) -> int:
    """Lower = better. -1 if exact match, otherwise position in compat list."""
    if want == got:
        return 0
    options = _COMPAT.get(want, [want])
    if got in options:
        return 1 + options.index(got)
    return 99


# ---------------------------------------------------------------------------
# Brace-aware tokenizer for \se{...}{...}...
# ---------------------------------------------------------------------------

def _read_brace_group(s: str, i: int) -> tuple[str, int]:
    """Starting at s[i] == '{', read a balanced brace group.

    Returns (inner_text, index_after_closing_brace).
    """
    if s[i] != "{":
        raise ValueError("expected '{' at offset %d" % i)
    depth = 0
    start = i + 1
    j = i
    while j < len(s):
        c = s[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:j], j + 1
        j += 1
    raise ValueError("unbalanced braces starting at %d" % i)


def _parse_se_args(text: str, start: int) -> tuple[list[str], int]:
    """Parse the 7 brace groups of a \\se call beginning at text[start]."""
    args: list[str] = []
    j = start
    n = len(text)
    while len(args) < 7:
        # Skip whitespace between groups (none expected, but be safe).
        while j < n and text[j] in " \t":
            j += 1
        if j >= n or text[j] != "{":
            raise ValueError(
                "expected 7 brace groups for \\se, got %d at offset %d"
                % (len(args), start)
            )
        inner, j = _read_brace_group(text, j)
        args.append(inner)
    return args, j


# ---------------------------------------------------------------------------
# Description sanitizer (strip TeX macros for human display)
# ---------------------------------------------------------------------------

_DESC_PATTERNS = [
    (re.compile(r"\\rn\{([^{}]*)\}\{([^{}]*)\}"), r"\1\2"),
    (re.compile(r"\\Ro\{([^{}]*)\}"), r"\1"),
    (re.compile(r"\\osf\{([^{}]*)\}"), r"\1"),
    (re.compile(r"\\halfdim\b ?"), "o"),
    (re.compile(r"\\nd\{\}"), "-"),
    (re.compile(r"\\ "), " "),                # TeX escaped space
    (re.compile(r"\\[a-zA-Z]+\b ?"), ""),     # drop other macros
    (re.compile(r"[\$\{\}\\]"), ""),
    (re.compile(r"\s+"), " "),
]


def _clean_desc(s: str) -> str:
    out = s
    for pat, repl in _DESC_PATTERNS:
        out = pat.sub(repl, out)
    return out.strip()


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _section_bounds(text: str) -> tuple[int, int]:
    """Return (start, end) char offsets of the StackedChords block."""
    m = re.search(r"%\s*PAGE\s*2[^\n]*StackedChords", text)
    if not m:
        # Fallback: just find "% PAGE 2"
        m = re.search(r"%\s*PAGE\s*2\b", text)
    if not m:
        raise ValueError("could not find PAGE 2 / StackedChords marker")
    start = m.end()
    # End at the next \clearpage
    end_match = re.search(r"\\clearpage", text[start:])
    if not end_match:
        return start, len(text)
    return start, start + end_match.start()


def load_voicings(handout_path: str = "handout.tex") -> list[Voicing]:
    """Parse \\se{} calls from the StackedChords section of handout.tex."""
    if not os.path.isabs(handout_path):
        # Resolve relative to current working dir; fall back to repo root.
        if not os.path.exists(handout_path):
            here = os.path.dirname(os.path.abspath(__file__))
            cand = os.path.normpath(os.path.join(here, "..", "..", handout_path))
            if os.path.exists(cand):
                handout_path = cand
    with open(handout_path, "r", encoding="utf-8") as f:
        text = f.read()
    s_start, s_end = _section_bounds(text)
    section = text[s_start:s_end]

    voicings: list[Voicing] = []
    i = 0
    n = len(section)
    while i < n:
        # Find next \se{ at start-of-token (allow leading whitespace on line).
        idx = section.find("\\se{", i)
        if idx < 0:
            break
        # Make sure it isn't \senote or some longer macro: char after \se must be '{'.
        # (We searched for "\\se{" so this is already guaranteed.)
        args, after = _parse_se_args(section, idx + len("\\se"))
        rh_rom, rh_qual_raw, lh_rom, lh_qual_raw, desc_raw, lh_fig, rh_fig = args
        rh = (_roman_to_deg(rh_rom), _normalize_quality(rh_rom, rh_qual_raw))
        lh = (_roman_to_deg(lh_rom), _normalize_quality(lh_rom, lh_qual_raw))
        voicings.append(Voicing(
            rh=rh,
            lh=lh,
            desc=_clean_desc(desc_raw),
            lh_fig=lh_fig.strip(),
            rh_fig=rh_fig.strip(),
        ))
        i = after
    return voicings


# ---------------------------------------------------------------------------
# Picker utilities
# ---------------------------------------------------------------------------

def voicings_for_lh(chord: RomanChord, voicings: list[Voicing]) -> list[Voicing]:
    """All voicings whose LH chord matches exactly."""
    deg, qual = chord
    return [v for v in voicings if v.lh[0] == deg and v.lh[1] == qual]


# Diatonic scale-degree (1-7) -> pitch class in C major (semitones from C).
_DEG_TO_PC = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}

# Quality -> chord-tone interval set (semitones from root).
_QUAL_INTERVALS: dict[str, tuple[int, ...]] = {
    "":     (0, 4, 7),
    "m":    (0, 3, 7),
    "7":    (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "m7":   (0, 3, 7, 10),
    "dim":  (0, 3, 6),
    "dim7": (0, 3, 6, 9),
    "hdim7":(0, 3, 6, 10),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "6":    (0, 4, 7, 9),
    "m6":   (0, 3, 7, 9),
}


def _chord_pcs(chord: RomanChord) -> tuple[int, ...]:
    deg, qual = chord
    root = _DEG_TO_PC.get(deg, 0)
    ivals = _QUAL_INTERVALS.get(qual, _QUAL_INTERVALS[""])
    return tuple((root + i) % 12 for i in ivals)


def _pc_distance(a: int, b: int) -> int:
    """Shortest pitch-class distance, 0..6."""
    d = (a - b) % 12
    return min(d, 12 - d)


def voice_leading_cost(v1: Voicing, v2: Voicing) -> int:
    """Sum of greedy nearest-neighbor pitch-class distances between v1.rh and v2.rh."""
    a = list(_chord_pcs(v1.rh))
    b = list(_chord_pcs(v2.rh))
    total = 0
    # Greedy: for each tone in the smaller set, take its closest unused tone in the other.
    if len(a) > len(b):
        a, b = b, a
    used = [False] * len(b)
    for x in a:
        best = 99
        best_j = -1
        for j, y in enumerate(b):
            if used[j]:
                continue
            d = _pc_distance(x, y)
            if d < best:
                best = d
                best_j = j
        if best_j >= 0:
            used[best_j] = True
            total += best
    # Penalize unmatched extra tones (count them as half-an-octave each).
    leftover = used.count(False)
    total += leftover * 2
    return total


def _fig_pattern(fig: str) -> str:
    """Return the interval-string portion of a hex figure (everything after
    the first character / leading scale-degree).

    E.g., 'C33' -> '33'; '8333' -> '333'; '' -> ''.
    """
    if not fig:
        return ""
    return fig[1:]


def pick_voicing(
    chord: RomanChord,
    prior: Optional[Voicing],
    voicings: list[Voicing],
    history: Optional[list[Voicing]] = None,
) -> Voicing:
    """Pick the best Voicing whose LH matches `chord`.

    If `history` is given (a list of the last N picked voicings, oldest
    first, most-recent last), additional diversity penalties are applied
    to discourage over-use of the same RH / LH chord in a short window.
    `history` defaults to None for backward compatibility.
    """
    if not voicings:
        raise ValueError("no voicings available")
    deg, qual = chord

    # Group candidates by (quality-priority): exact match first, then compat.
    same_deg = [v for v in voicings if v.lh[0] == deg]
    if not same_deg:
        # No LH degree match at all -> hard fallback: return first overall.
        return voicings[0]

    # Build a window of the last up-to-3 voicings (most-recent last).
    window: list[Voicing] = []
    if history:
        window = list(history[-3:])
    # If caller didn't provide history but did provide a prior, treat prior
    # as a 1-element history so the pair-repeat penalty still fires.
    if not window and prior is not None:
        window = [prior]
    # The immediate prior used for voice-leading and pair-repeat checks.
    vl_prior = window[-1] if window else prior
    prior2 = window[-2] if len(window) >= 2 else None

    # Score each candidate: lower = better.
    scored: list[tuple[tuple[int, int, int, int, int], Voicing]] = []
    for v in same_deg:
        qprio = _quality_priority(qual, v.lh[1])

        # Penalty for repeating prior pair (LH, RH).
        repeat_pen = 0
        if vl_prior is not None and vl_prior.lh == v.lh and vl_prior.rh == v.rh:
            repeat_pen = 5

        # Same-RH penalty: any time cand.rh was used in the recent window,
        # add a variety penalty proportional to the number of recent hits.
        # If it also matches the immediate prior.rh, penalize harder.
        rh_pen = 0
        recent_rh_hits = sum(1 for h in window if h.rh == v.rh)
        if recent_rh_hits >= 1:
            rh_pen = 3 * recent_rh_hits
            if vl_prior is not None and v.rh == vl_prior.rh:
                rh_pen += 2

        # Same-LH penalty: LH matches prior AND prior2.
        lh_pen = 0
        if (
            vl_prior is not None
            and prior2 is not None
            and v.lh == vl_prior.lh
            and v.lh == prior2.lh
        ):
            lh_pen = 2

        # Pattern-variety bonus: prefer candidates whose LH or RH pattern
        # differs from the immediate prior's (small, tie-breaker scale).
        variety_bonus = 0
        if vl_prior is not None:
            if _fig_pattern(v.lh_fig) != _fig_pattern(vl_prior.lh_fig):
                variety_bonus -= 1
            if _fig_pattern(v.rh_fig) != _fig_pattern(vl_prior.rh_fig):
                variety_bonus -= 1

        # Voice-leading cost from prior.rh -> v.rh.
        if vl_prior is None:
            vl = 0
        else:
            vl = voice_leading_cost(vl_prior, v)

        # Ordering: quality first (hard), then diversity penalties, then
        # voice-leading, then variety bonus as final tie-breaker.
        total_div = repeat_pen + rh_pen + lh_pen
        scored.append(((qprio, total_div, vl, variety_bonus, 0), v))

    scored.sort(key=lambda t: t[0])
    best_score = scored[0][0]
    if best_score[0] >= 99:
        # No quality match at all -> fallback: first by deg, ignore quality.
        for v in voicings:
            if v.lh[0] == deg:
                return v
        return voicings[0]
    return scored[0][1]


def pick_sequence(
    chords: list[RomanChord],
    voicings: list[Voicing],
) -> list[Voicing]:
    """Pick voicings for a sequence, maintaining history of last 3 picks for
    RH/LH diversity. Returns one Voicing per chord.
    """
    picks: list[Voicing] = []
    history: list[Voicing] = []
    prior: Optional[Voicing] = None
    for ch in chords:
        v = pick_voicing(ch, prior, voicings, history=history if history else None)
        picks.append(v)
        prior = v
        history.append(v)
        if len(history) > 3:
            history = history[-3:]
    return picks


# ---------------------------------------------------------------------------
# Hex-figure -> harp string numbers
# ---------------------------------------------------------------------------

def _hex_first_char_to_int(c: str) -> int:
    """Convert a single character figure-leader to a 1-based scale degree.

    1-9 = 1..9, A-G = 10..16. (Lowercase accepted too.)
    """
    if "1" <= c <= "9":
        return int(c)
    cu = c.upper()
    if "A" <= cu <= "G":
        return 10 + (ord(cu) - ord("A"))
    raise ValueError("bad figure leader char: %r" % c)


def figure_to_strings(fig: str, key_tonic_string: int) -> list[int]:
    """Convert a hex figure like 'C33' to absolute harp string numbers.

    First char  = scale degree (1-9, A-G for 10..16).
    Remaining   = stacked diatonic intervals (3 = third = 2 steps, 4 = fourth
                  = 3 steps, etc.).
    `key_tonic_string` = harp-string number of degree-1 of the key.

    Range: harp strings 1..33 (C2..G6). Out-of-range strings are still
    returned so callers can detect/ clamp themselves.
    """
    if not fig:
        return []
    leader = _hex_first_char_to_int(fig[0])
    # First note = tonic_string + (leader - 1) diatonic steps.
    cur = key_tonic_string + (leader - 1)
    out = [cur]
    for ch in fig[1:]:
        if ch == "0":
            # 0 = unused finger; skip but keep position
            continue
        if not ch.isdigit():
            raise ValueError("bad interval digit: %r in %r" % (ch, fig))
        step = int(ch) - 1   # interval number -> diatonic steps (3rd=2 steps)
        cur = cur + step
        out.append(cur)
    return out


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _format_chord(c: RomanChord) -> str:
    deg, qual = c
    rom = ["", "I", "II", "III", "IV", "V", "VI", "VII"][deg]
    if qual in ("m", "m7", "m6"):
        rom = rom.lower()
        suf = qual[1:]  # drop the 'm' since lowercase implies minor
    elif qual == "":
        suf = ""
    elif qual == "dim":
        rom = rom.lower()
        suf = "o"
    elif qual == "hdim7":
        rom = rom.lower()
        suf = "o7(b5)"
    else:
        suf = qual
    return rom + suf


def _main() -> int:
    voicings = load_voicings("handout.tex")
    print("Loaded %d voicings from handout.tex" % len(voicings))
    assert len(voicings) >= 66, (
        "expected >= 66 voicings, got %d" % len(voicings)
    )

    # Sample 3 evenly spaced entries.
    print()
    print("Sample entries:")
    for idx in (0, len(voicings) // 2, len(voicings) - 1):
        v = voicings[idx]
        print("  [%2d] RH=%-7s LH=%-7s  fig=%s/%s  desc=%r" % (
            idx, _format_chord(v.rh), _format_chord(v.lh),
            v.rh_fig, v.lh_fig, v.desc,
        ))

    # Test 1: pick for (1, "")
    pick = pick_voicing((1, ""), None, voicings)
    print()
    print("pick_voicing((1, '')) -> RH=%s LH=%s desc=%r" % (
        _format_chord(pick.rh), _format_chord(pick.lh), pick.desc,
    ))
    assert pick.lh[0] == 1, "expected LH degree 1, got %r" % (pick.lh,)

    # Test 2: smooth voice-leading I -> IV -> V -> I
    print()
    print("Voice-leading sequence I -> IV -> V -> I:")
    sequence: list[RomanChord] = [(1, ""), (4, ""), (5, ""), (1, "")]
    prior: Optional[Voicing] = None
    picks: list[Voicing] = []
    for ch in sequence:
        cur = pick_voicing(ch, prior, voicings)
        picks.append(cur)
        print("  chord=%s -> RH=%s LH=%s  rh_pcs=%s" % (
            _format_chord(ch), _format_chord(cur.rh),
            _format_chord(cur.lh), list(_chord_pcs(cur.rh)),
        ))
        prior = cur

    # Confirm consecutive RH movement is "smooth" (no single tone jumps > 4 pc steps).
    for i in range(1, len(picks)):
        a = _chord_pcs(picks[i - 1].rh)
        b = _chord_pcs(picks[i].rh)
        # Greedy nearest-neighbor max distance.
        used = [False] * len(b)
        max_jump = 0
        for x in a:
            best = 99
            best_j = -1
            for j, y in enumerate(b):
                if used[j]:
                    continue
                d = _pc_distance(x, y)
                if d < best:
                    best = d
                    best_j = j
            if best_j >= 0:
                used[best_j] = True
                if best > max_jump:
                    max_jump = best
        print("  step %d->%d: max RH tone jump = %d pc-steps" % (i - 1, i, max_jump))
        assert max_jump <= 4, (
            "voice-leading too rough at step %d->%d: %d > 4"
            % (i - 1, i, max_jump)
        )

    # Test 3: figure_to_strings round-trip.
    # 'G33' = deg 16, then +2 +2 -> [16, 18, 20] starting from key_tonic_string.
    s = figure_to_strings("G33", 1)
    assert s == [16, 18, 20], "G33@1 -> %r" % s
    # 'C33' starting on C tonic at string 1 -> deg 12, then +2 +2.
    s = figure_to_strings("C33", 1)
    assert s == [12, 14, 16], "C33@1 -> %r" % s
    # Unused finger '0' -> skipped.
    s = figure_to_strings("8334", 8)
    # 8 -> 8+7=15; then 3 -> +2 -> 17; 3 -> +2 -> 19; 4 -> +3 -> 22.
    assert s == [15, 17, 19, 22], "8334@8 -> %r" % s
    print()
    print("figure_to_strings checks OK")

    # Test 4: pick_sequence gives RH variety over [I, IV, V, I, IV, V, I].
    print()
    print("pick_sequence RH-diversity test:")
    seq_chords: list[RomanChord] = [
        (1, ""), (4, ""), (5, ""), (1, ""), (4, ""), (5, ""), (1, ""),
    ]
    seq_picks = pick_sequence(seq_chords, voicings)
    for ch, v in zip(seq_chords, seq_picks):
        print("  %-4s -> RH=%-7s LH=%-7s" % (
            _format_chord(ch), _format_chord(v.rh), _format_chord(v.lh),
        ))
    distinct_rh = len(set(v.rh for v in seq_picks))
    print("  distinct RH chords across %d picks: %d"
          % (len(seq_picks), distinct_rh))
    assert distinct_rh >= 4, (
        "expected >= 4 distinct RH chords in [I,IV,V,I,IV,V,I], got %d"
        % distinct_rh
    )

    # Compare with old (no-history) behavior for the same sequence.
    prior_old: Optional[Voicing] = None
    old_picks: list[Voicing] = []
    for ch in seq_chords:
        p = pick_voicing(ch, prior_old, voicings)  # no history -> legacy
        old_picks.append(p)
        prior_old = p
    old_distinct = len(set(v.rh for v in old_picks))
    print("  (legacy no-history sequence would give %d distinct RH chords)"
          % old_distinct)

    # Test 5: history argument actually changes the picked voicing when
    # there are multiple LH-matching candidates.
    # Find a chord with several LH matches so the ranking has room to move.
    target: RomanChord = (1, "")
    pv_none = pick_voicing(target, None, voicings)
    pv_hist = pick_voicing(target, pv_none, voicings, history=[pv_none, pv_none])
    print()
    print("history-sensitivity test:")
    print("  pick (no history)      -> RH=%s" % _format_chord(pv_none.rh))
    print("  pick (history=[prev]*2)-> RH=%s" % _format_chord(pv_hist.rh))
    assert pv_hist.rh != pv_none.rh, (
        "expected a different RH when prior RH is in history, got same: %r"
        % (pv_hist.rh,)
    )

    print()
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
