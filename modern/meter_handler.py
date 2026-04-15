"""Meter preprocessing for the modern reharmonization pipeline.

The modern pipeline refuses to process hymns whose ABC carries an "exotic"
meter: `M:none` (free-meter chorale style, 17 hymns), `M:3/2` (7 hymns) and
`M:8/4` (2 hymns) in OpenHymnal.

This module normalises those cases before any downstream module sees the
ABC:

- `M:none` -> split the body into 4/4 sub-measures. Existing bar lines are
  honoured as phrase boundaries (we never cross one when grouping notes
  into a new measure).  Within each phrase we add bar lines every four
  quarter-note beats, splitting a note across a bar line with a tie when
  required.  The meter line is rewritten to `M: 4/4`.

- `M:3/2` and `M:8/4` pass through unchanged -- abc2ly / LilyPond accept
  both natively.

- Any other meter passes through unchanged.

The handler is idempotent: running it twice produces the same result
(`M:4/4` is already "simple", so the second call returns its input).

Standard library only, ASCII only, python3.10.
"""

from __future__ import annotations

import re
from fractions import Fraction


# Regex fragments shared with verify_samples.py -- kept local so that
# this module has no imports from the rest of the pipeline.
_METER_RE = re.compile(r"(?m)^(M:\s*)([^\n]+)$")
_LEN_RE = re.compile(r"(?m)^L:\s*(\d+)\s*/\s*(\d+)")

# Full-note-token regex (accidentals, pitch, octave marks, length).  Does
# not cover chord brackets `[...]` -- those are handled separately.
_NOTE_HEAD_RE = re.compile(
    r"(?P<acc>\^{1,2}|_{1,2}|=)?"           # accidental
    r"(?P<pit>[A-Ga-gz])"                   # pitch or rest
    r"(?P<oct>[',]*)"                       # octave marks
    r"(?P<num>\d+)?"                         # numerator
    r"(?P<den>/\d*)?"                        # denominator (/ or /N)
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def preprocess_abc(abc: str) -> tuple[str, str]:
    """Normalise `abc` for the modern pipeline.

    Returns a pair ``(new_abc, effective_meter)``.  ``effective_meter`` is
    the meter string that downstream code should treat the piece as having
    (e.g. "4/4" for a split `M:none`, or the original meter otherwise).
    """
    meter = _extract_meter(abc)
    if meter in ("none", "None", "NONE"):
        return _split_mnone_to_4_4(abc), "4/4"
    # 3/2, 8/4, and everything else: pass through unchanged.
    return abc, meter


# ---------------------------------------------------------------------------
# Meter parsing helpers
# ---------------------------------------------------------------------------


def _extract_meter(abc: str) -> str:
    m = _METER_RE.search(abc)
    return m.group(2).strip() if m else "?"


def _parse_default_length(abc: str) -> Fraction:
    m = _LEN_RE.search(abc)
    if not m:
        return Fraction(1, 8)
    return Fraction(int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# Tokenizer for the music body
# ---------------------------------------------------------------------------


# Token kinds:
#   ('ann', text)    -- a `"..."` annotation (chord name or otherwise)
#   ('note', text, duration_wholes)
#   ('bar', text)    -- any bar-line construct
#   ('other', text)  -- decorations, whitespace, comments, brackets, etc.


def _duration_from_match(m: re.Match, default_l: Fraction) -> Fraction:
    num_s = m.group("num")
    den_s = m.group("den")
    mult = Fraction(int(num_s)) if num_s else Fraction(1)
    if den_s:
        if den_s == "/":
            div = Fraction(2)
        else:
            div = Fraction(int(den_s[1:])) if len(den_s) > 1 else Fraction(2)
        mult = mult / div
    return default_l * mult


def _tokenize_body(body: str, default_l: Fraction) -> list[tuple]:
    tokens: list[tuple] = []
    n = len(body)
    i = 0
    while i < n:
        ch = body[i]

        # Line continuations / whitespace / newlines: pass-through.
        if ch in " \t\r\n":
            j = i
            while j < n and body[j] in " \t\r\n":
                j += 1
            tokens.append(("other", body[i:j]))
            i = j
            continue

        # Comments: % to end of line.
        if ch == "%":
            j = body.find("\n", i)
            if j < 0:
                j = n
            tokens.append(("other", body[i:j]))
            i = j
            continue

        # Annotations / chord symbols inside double quotes.
        if ch == '"':
            j = body.find('"', i + 1)
            if j < 0:
                tokens.append(("other", body[i:]))
                i = n
                continue
            tokens.append(("ann", body[i:j + 1]))
            i = j + 1
            continue

        # Bar lines: ':|', '|:', '::', '|]', '[|', '|', possibly with
        # numeric voltas following like `|1` `|2`.
        if ch == "|":
            j = i + 1
            if j < n and body[j] in (":", "]"):
                j += 1
            # Optional volta digits.
            while j < n and body[j].isdigit():
                j += 1
            tokens.append(("bar", body[i:j]))
            i = j
            continue
        if ch == ":":
            j = i + 1
            if j < n and body[j] == "|":
                j += 1
            if j < n and body[j] == ":":
                j += 1
            tokens.append(("bar", body[i:j]))
            i = j
            continue
        if ch == "[":
            # Could be inline field [K:...], ABC chord [CEG], or start bar [|.
            if i + 1 < n and body[i + 1] == "|":
                tokens.append(("bar", body[i:i + 2]))
                i += 2
                continue
            # Inline field: [X:...]  -- single letter + colon.
            if (i + 2 < n and
                    (("A" <= body[i + 1] <= "Z") or
                     ("a" <= body[i + 1] <= "z")) and
                    body[i + 2] == ":"):
                j = body.find("]", i + 1)
                if j < 0:
                    tokens.append(("other", body[i:]))
                    i = n
                    continue
                tokens.append(("other", body[i:j + 1]))
                i = j + 1
                continue
            # ABC-style note chord: [CEG]dur.  Treat as a single note whose
            # duration is that of the chord's trailing length.
            j = body.find("]", i + 1)
            if j < 0:
                tokens.append(("other", body[i:]))
                i = n
                continue
            end = j + 1
            # Optional length after the chord, e.g. [CEG]2.
            tail = _NOTE_HEAD_RE.match("z", 0)  # reused shape, not used
            m = re.match(r"(?P<num>\d+)?(?P<den>/\d*)?", body[end:])
            if m:
                num_s = m.group("num")
                den_s = m.group("den")
                mult = Fraction(int(num_s)) if num_s else Fraction(1)
                if den_s:
                    if den_s == "/":
                        div = Fraction(2)
                    else:
                        div = (Fraction(int(den_s[1:]))
                               if len(den_s) > 1 else Fraction(2))
                    mult = mult / div
                end += m.end()
            else:
                mult = Fraction(1)
            dur = default_l * mult
            tokens.append(("note", body[i:end], dur))
            i = end
            continue

        # Decorations and ornament prefixes: '.', '~', 'H', 'L', 'M',
        # 'O', 'P', 'S', 'T', 'u', 'v', 'x' at a note position, `!..!`
        # for extended decorations, `+..+` (old style).
        if ch == "!":
            j = body.find("!", i + 1)
            if j < 0:
                tokens.append(("other", body[i:]))
                i = n
                continue
            tokens.append(("other", body[i:j + 1]))
            i = j + 1
            continue
        if ch == "+":
            j = body.find("+", i + 1)
            if j < 0:
                tokens.append(("other", body[i:]))
                i = n
                continue
            tokens.append(("other", body[i:j + 1]))
            i = j + 1
            continue

        # Tuplet opener `(3` -- keep as-is.  Also grace `{...}`.
        if ch == "(":
            # (N or (N:P:Q or plain slur open.
            j = i + 1
            while j < n and body[j].isdigit():
                j += 1
            if j == i + 1:
                # Plain slur open.
                tokens.append(("other", body[i:i + 1]))
                i += 1
                continue
            # Tuplet spec with optional :P:Q pieces.
            while j < n and body[j] == ":":
                j += 1
                while j < n and body[j].isdigit():
                    j += 1
            tokens.append(("other", body[i:j]))
            i = j
            continue
        if ch == "{":
            j = body.find("}", i + 1)
            if j < 0:
                tokens.append(("other", body[i:]))
                i = n
                continue
            tokens.append(("other", body[i:j + 1]))
            i = j + 1
            continue

        # Notes (including rests `z` and `x`).
        m = _NOTE_HEAD_RE.match(body, i)
        if m and m.group("pit"):
            dur = _duration_from_match(m, default_l)
            tokens.append(("note", body[i:m.end()], dur))
            i = m.end()
            continue

        # Anything else (slurs `)`, ties `-`, single punctuation): pass-through.
        tokens.append(("other", body[i]))
        i += 1

    return tokens


# ---------------------------------------------------------------------------
# M:none -> 4/4 splitter
# ---------------------------------------------------------------------------


def _split_mnone_to_4_4(abc: str) -> str:
    """Rewrite an M:none ABC so its body carries explicit 4/4 bar lines.

    Existing bar lines are preserved as phrase boundaries.  Within each
    phrase we accumulate notes until they fill four quarter-note beats,
    then emit a bar line.  If the final note of a phrase would straddle
    the boundary, we split it with a tie so that bar-line placement is
    rhythmically honest (downstream tools expect each 4/4 measure to be
    full).
    """
    # Separate header from body.
    lines = abc.splitlines(keepends=True)
    header_end = 0
    for idx, line in enumerate(lines):
        if line.startswith("K:"):
            header_end = idx + 1
            break
    header = "".join(lines[:header_end])
    body = "".join(lines[header_end:])

    # Swap the meter line.
    header = _METER_RE.sub(lambda m: f"{m.group(1)}4/4",
                           header, count=1)

    default_l = _parse_default_length(abc)
    tokens = _tokenize_body(body, default_l)

    # Strategy: ignore existing body bar lines (M:none sources treat them
    # as phrase hints only, not metric barlines).  Flow notes in order,
    # breaking every 4 quarters, splitting a note with a tie if it would
    # straddle a boundary.  Chord annotations and other non-timed tokens
    # ride with the NEXT note (deferred), so they never end up orphaned
    # on the far side of a bar line.  We preserve the final bar terminator
    # if the source had one (e.g. `|]`).
    bar_fill = Fraction(1)   # 4/4 in whole notes = 1 whole note.
    out_parts: list[str] = []
    pos = Fraction(0)

    # Strip trailing bar-like tokens for the terminator; keep the last
    # one for reattachment.
    final_bar = ""
    trailing_idx = len(tokens)
    while trailing_idx > 0:
        k = tokens[trailing_idx - 1][0]
        if k == "bar":
            final_bar = tokens[trailing_idx - 1][1]
            trailing_idx -= 1
            break
        if k == "other" and tokens[trailing_idx - 1][1].strip() == "":
            trailing_idx -= 1
            continue
        break

    # Anything attached to a note but not itself timed (annotations,
    # decorations, grace groups) is buffered until the next note is emitted,
    # so it can't be stranded on the wrong side of a bar line.
    pending: list[str] = []

    def flush_pending() -> None:
        out_parts.extend(pending)
        pending.clear()

    for tok in tokens[:trailing_idx]:
        kind = tok[0]
        if kind == "bar":
            # Swallow internal bar lines; we insert our own on the 4/4 grid.
            # Replace with a space so adjacent tokens don't collide visually.
            if out_parts and not out_parts[-1].endswith(" "):
                pending.insert(0, " ")
            continue
        if kind == "ann":
            pending.append(tok[1])
            continue
        if kind == "other":
            # Preserve whitespace verbatim (it helps readability), but
            # defer other inline markup so it stays with its note.
            text = tok[1]
            if text.strip() == "":
                # Whitespace after a bar line collapses naturally; keep a
                # single space between notes.
                if out_parts and not out_parts[-1].endswith(" "):
                    pending.append(" ")
            else:
                pending.append(text)
            continue
        if kind == "note":
            text, dur = tok[1], tok[2]
            remaining = dur
            first = True
            while remaining > 0:
                room = bar_fill - pos
                if room <= 0:
                    out_parts.append("|")
                    pos = Fraction(0)
                    room = bar_fill
                take = min(remaining, room)
                if first:
                    # Attach pending annotations to the first piece.
                    flush_pending()
                    if take == dur:
                        out_parts.append(text)
                    else:
                        out_parts.append(
                            _retime_note(text, take, default_l))
                else:
                    out_parts.append(_retime_note(text, take, default_l))
                pos += take
                remaining -= take
                if remaining > 0:
                    # Tie into next measure piece (rests don't tie).
                    head = _NOTE_HEAD_RE.match(text)
                    pit = head.group("pit") if head else ""
                    if pit and pit not in ("z", "x"):
                        out_parts.append("-")
                    out_parts.append("|")
                    pos = Fraction(0)
                first = False
            continue

    # Flush any trailing annotations / decorations that had no note to ride.
    if pending:
        # If the leftover is just whitespace, drop it; otherwise keep it.
        leftover = "".join(pending).strip()
        if leftover:
            out_parts.append(leftover)
        pending.clear()

    # Pad the final measure out to 4/4 with a rest so the last bar is
    # rhythmically complete, then restore the source's final barline.
    if pos > 0 and pos < bar_fill:
        remainder = bar_fill - pos
        mult = remainder / default_l
        out_parts.append("z" + _length_suffix(mult))
    if final_bar:
        out_parts.append(final_bar)
    elif pos > 0:
        out_parts.append("|")

    new_body = "".join(out_parts)
    # Append a newline if the original ended with one.
    if body.endswith("\n") and not new_body.endswith("\n"):
        new_body += "\n"
    return header + new_body


def _retime_note(text: str, new_dur_wholes: Fraction,
                 default_l: Fraction) -> str:
    """Return `text` with its trailing length multiplier replaced so that
    its duration equals `new_dur_wholes`.

    `text` is either a plain note (accidentals + pitch + octave + length)
    or an ABC note-chord `[CEG]len`.  The function rewrites the length
    suffix only; all pitch/accidental/octave content is preserved.
    """
    mult = new_dur_wholes / default_l  # in L-units
    len_suffix = _length_suffix(mult)

    if text.startswith("["):
        # Chord-note: find the ']' and replace whatever comes after.
        close = text.find("]")
        if close < 0:
            return text  # malformed; leave alone
        return text[:close + 1] + len_suffix

    # Plain note: use _NOTE_HEAD_RE to locate pitch+octave, then replace
    # everything after.
    m = _NOTE_HEAD_RE.match(text)
    if not m:
        return text
    prefix_end = m.start("num") if m.group("num") else (
        m.start("den") if m.group("den") else m.end())
    # If neither num nor den was present, prefix_end == m.end(); everything
    # after m.end() (impossible inside a single note token) is preserved.
    head = text[:prefix_end]
    tail = text[m.end():]
    return head + len_suffix + tail


def _length_suffix(mult: Fraction) -> str:
    """Render a length multiplier as an ABC length suffix.

    Examples:
        Fraction(1)     -> ''
        Fraction(2)     -> '2'
        Fraction(3, 2)  -> '3/2'
        Fraction(1, 2)  -> '/2'
        Fraction(3, 4)  -> '3/4'
    """
    if mult == 1:
        return ""
    num = mult.numerator
    den = mult.denominator
    if den == 1:
        return str(num)
    if num == 1:
        return f"/{den}"
    return f"{num}/{den}"


# ---------------------------------------------------------------------------
# __main__ demo
# ---------------------------------------------------------------------------


def _demo() -> None:
    import json
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "app", "lead_sheets.json")
    with open(path, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    # 5 sample exception hymns: M:none, 3/2, 8/4 mix.
    wanted = {"4041", "4126", "4269", "4173", "4120"}
    samples = [h for h in hymns if str(h.get("n")) in wanted]

    for h in samples:
        n = h.get("n")
        t = h.get("t", "?")
        abc = h.get("abc", "")
        new_abc, meter = preprocess_abc(abc)
        print(f"==== n={n} {t} ====")
        print(f"[meter in: {_extract_meter(abc)} -> out: {meter}]")
        print("--- BEFORE ---")
        print(abc)
        print("--- AFTER ---")
        print(new_abc)

        # Idempotency check.
        again, meter2 = preprocess_abc(new_abc)
        ok = (again == new_abc and meter2 == meter)
        print(f"[idempotent: {ok}]")
        print()


if __name__ == "__main__":
    _demo()
