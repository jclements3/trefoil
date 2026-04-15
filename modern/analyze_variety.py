#!/usr/bin/env python3.10
"""Diagnostic: voicing-variety report for the modern reharm pipeline.

Runs the reharmonization + voicing-picker over every hymn in
app/lead_sheets.json and reports how evenly the StackedChords voicings
(the 66-74 \\se{} entries from handout.tex page 2) are consumed.

Output:
  - modern/variety_report.md
  - concise stdout summary

Standard library + modern.* only. ASCII only. python3.10+.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_TEX = os.path.join(REPO_ROOT, "handout.tex")
REPORT_PATH = os.path.join(REPO_ROOT, "modern", "variety_report.md")

from modern import reharm_rules
from modern import voicing_picker


# ---------------------------------------------------------------------------
# ABC helpers (lightweight; do not depend on abc_rewriter)
# ---------------------------------------------------------------------------

CHORD_RE = re.compile(r'"\^([^"]+)"')
METER_RE = re.compile(r"(?m)^M:\s*([^\n]+)")
LEN_RE = re.compile(r"(?m)^L:\s*(\d+)\s*/\s*(\d+)")
NOTE_RE = re.compile(r"(\^|=|_)?([A-Ga-gz])([\',]*)(\d+)?(/\d*)?")


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else "4/4"


def parse_meter_fraction(abc: str) -> tuple[int, int]:
    meter = parse_meter(abc)
    if meter in ("C", "c"):
        return (4, 4)
    if meter in ("C|", "c|"):
        return (2, 2)
    m = re.match(r"(\d+)\s*/\s*(\d+)", meter)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (4, 4)


def parse_default_length(abc: str) -> float:
    m = LEN_RE.search(abc)
    if not m:
        return 1.0 / 8.0
    return int(m.group(1)) / int(m.group(2))


def note_duration(token: str, default_l: float) -> float:
    m = NOTE_RE.match(token)
    if not m:
        return 0.0
    num_str = m.group(4)
    div_str = m.group(5)
    mult = float(num_str) if num_str else 1.0
    if div_str:
        if div_str == "/":
            div = 2.0
        else:
            div = float(div_str[1:]) if len(div_str) > 1 else 2.0
        mult = mult / div
    return default_l * mult


def iter_chord_events(abc: str) -> list[tuple[float, str]]:
    """Return [(beat_quarters_from_start, chord_name), ...] for the piece."""
    default_l = parse_default_length(abc)
    lines = abc.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("K:"):
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:])

    events: list[tuple[float, str]] = []
    pos_whole = 0.0
    i = 0
    pending: Optional[str] = None
    while i < len(body):
        ch = body[i]
        if ch == '"':
            j = body.find('"', i + 1)
            if j < 0:
                break
            inside = body[i + 1:j]
            if inside.startswith("^"):
                pending = inside[1:]
            i = j + 1
            continue
        m = NOTE_RE.match(body, i)
        if m and body[i] not in ("|", "[", "]"):
            tok = m.group(0)
            dur_whole = note_duration(tok, default_l)
            if pending is not None:
                events.append((pos_whole * 4.0, pending))
                pending = None
            pos_whole += dur_whole
            i = m.end()
            continue
        i += 1
    return events


# ---------------------------------------------------------------------------
# Pipeline on one hymn -- returns list of Voicing picks (or None per event)
# ---------------------------------------------------------------------------

def run_hymn(hymn: dict, voicings: list) -> dict:
    """Process one hymn. Returns stats + Voicing sequence."""
    abc = hymn.get("abc", "")
    key = hymn.get("key", "C")

    if key not in reharm_rules.KEY_PC:
        return {
            "skipped": True,
            "reason": "non-lever-harp key: %s" % key,
            "picks": [],
            "n_chords": 0,
            "n_unparseable": 0,
        }

    meter = parse_meter_fraction(abc)
    num, den = meter
    beats_per_bar = num * (4.0 / den)

    raw_events = iter_chord_events(abc)
    n_raw = len(raw_events)
    if n_raw == 0:
        return {
            "skipped": True,
            "reason": "no chord annotations",
            "picks": [],
            "n_chords": 0,
            "n_unparseable": 0,
        }

    # Parse each annotation; keep only parseable diatonic chords.
    parsed: list[tuple[float, Any, str]] = []
    n_unparseable = 0
    for beat, name in raw_events:
        try:
            roman = reharm_rules.parse_chord_name(name, key)
        except Exception:
            roman = None
        if roman is None:
            n_unparseable += 1
            continue
        parsed.append((beat, roman, name))

    if not parsed:
        return {
            "skipped": True,
            "reason": "no parseable chords (%d unparseable)" % n_unparseable,
            "picks": [],
            "n_chords": 0,
            "n_unparseable": n_unparseable,
        }

    # Build ChordEvent list with heuristics matching verify_samples.
    events = []
    n_p = len(parsed)
    for i, (beat, roman, name) in enumerate(parsed):
        next_beat = parsed[i + 1][0] if i + 1 < n_p else beat + beats_per_bar
        dur = max(0.25, next_beat - beat)
        bar_pos = beat % beats_per_bar
        is_strong = (abs(bar_pos) < 1e-6) or (
            beats_per_bar >= 4 and abs(bar_pos - 2.0) < 1e-6
        )
        is_cadence = (i >= n_p - 2)
        is_destination = is_strong and (
            i == 0 or parsed[i - 1][2] != name
        )
        events.append(reharm_rules.ChordEvent(
            beat=beat,
            duration=dur,
            chord=roman,
            is_strong_beat=is_strong,
            is_cadence=is_cadence,
            is_destination=is_destination,
        ))

    try:
        new_events = reharm_rules.reharmonize(events, key)
    except Exception as exc:
        return {
            "skipped": True,
            "reason": "reharm failed: %s" % exc,
            "picks": [],
            "n_chords": 0,
            "n_unparseable": n_unparseable,
        }

    # Pick voicings with rolling 3-deep history, same as verify_samples.
    picks: list = []
    prior = None
    last3: list = []
    for ev in new_events:
        chord = getattr(ev, "chord", None)
        try:
            v = voicing_picker.pick_voicing(
                chord, prior, voicings,
                history=last3 if last3 else None,
            )
        except Exception:
            v = None
        picks.append(v)
        if v is not None:
            prior = v
            last3.append(v)
            if len(last3) > 3:
                last3 = last3[-3:]

    return {
        "skipped": False,
        "reason": "",
        "picks": picks,
        "n_chords": len(picks),
        "n_unparseable": n_unparseable,
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def voicing_key(v) -> tuple[int, str, int, str]:
    rh_deg, rh_qual = v.rh
    lh_deg, lh_qual = v.lh
    return (rh_deg, rh_qual, lh_deg, lh_qual)


def fmt_chord(deg: int, qual: str) -> str:
    rom = ["", "I", "II", "III", "IV", "V", "VI", "VII"][deg]
    if qual in ("m", "m7", "m6"):
        return rom.lower() + (qual[1:] if len(qual) > 1 else "")
    if qual == "dim":
        return rom.lower() + "o"
    if qual == "dim7":
        return rom.lower() + "o7"
    if qual == "hdim7":
        return rom.lower() + "o7(b5)"
    if qual == "":
        return rom
    return rom + qual


def fmt_voicing_label(v) -> str:
    rh = fmt_chord(v.rh[0], v.rh[1])
    lh = fmt_chord(v.lh[0], v.lh[1])
    return "RH=%-7s LH=%-7s" % (rh, lh)


def fmt_voicing_short(v) -> str:
    return "%s/%s" % (fmt_chord(v.rh[0], v.rh[1]),
                      fmt_chord(v.lh[0], v.lh[1]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.path.exists(LEAD_SHEETS_PATH):
        print("ERROR: %s not found" % LEAD_SHEETS_PATH, file=sys.stderr)
        return 2

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    voicings = voicing_picker.load_voicings(HANDOUT_TEX)
    catalog_size = len(voicings)
    voicing_by_key: dict[tuple, Any] = {voicing_key(v): v for v in voicings}

    # Tallies.
    per_voicing = Counter()  # voicing_key -> count
    total_events = 0
    skipped_hymns = 0
    processed_hymns = 0
    unparseable_total = 0
    # Per-hymn diversity.
    per_hymn_stats: list[dict] = []

    for h in hymns:
        res = run_hymn(h, voicings)
        if res["skipped"]:
            skipped_hymns += 1
            unparseable_total += res["n_unparseable"]
            continue
        processed_hymns += 1
        unparseable_total += res["n_unparseable"]
        picks = [p for p in res["picks"] if p is not None]
        total_events += len(picks)

        rh_set = set()
        lh_set = set()
        vkey_set = set()
        for v in picks:
            k = voicing_key(v)
            per_voicing[k] += 1
            rh_set.add(v.rh)
            lh_set.add(v.lh)
            vkey_set.add(k)

        per_hymn_stats.append({
            "n": h.get("n"),
            "t": h.get("t", ""),
            "key": h.get("key", "?"),
            "n_events": len(picks),
            "distinct_voicings": len(vkey_set),
            "distinct_rh": len(rh_set),
            "distinct_lh": len(lh_set),
            "diversity_ratio": (len(vkey_set) / len(picks))
                if picks else 0.0,
        })

    if total_events == 0:
        print("ERROR: no events processed", file=sys.stderr)
        return 3

    # Metrics
    used_keys = set(per_voicing.keys())
    catalog_keys = set(voicing_by_key.keys())
    never_used_keys = sorted(catalog_keys - used_keys)
    distinct_used = len(used_keys)
    pct_used = 100.0 * distinct_used / catalog_size if catalog_size else 0.0

    # Averages.
    avg_rh = (sum(s["distinct_rh"] for s in per_hymn_stats)
              / len(per_hymn_stats)) if per_hymn_stats else 0.0
    avg_lh = (sum(s["distinct_lh"] for s in per_hymn_stats)
              / len(per_hymn_stats)) if per_hymn_stats else 0.0

    # Top / bottom
    # Include zero-use voicings in "bottom".
    all_usage: list[tuple[tuple, int]] = []
    for k, v in voicing_by_key.items():
        all_usage.append((k, per_voicing.get(k, 0)))
    # Sort: descending count, tiebreak by key tuple.
    all_usage_sorted_desc = sorted(all_usage, key=lambda t: (-t[1], t[0]))
    all_usage_sorted_asc = sorted(all_usage, key=lambda t: (t[1], t[0]))

    top10 = all_usage_sorted_desc[:10]
    bottom10 = all_usage_sorted_asc[:10]

    # Worst/best diversity hymn (require n_events >= 4 to be meaningful).
    meaningful = [s for s in per_hymn_stats if s["n_events"] >= 4]
    worst_hymn = min(meaningful, key=lambda s: s["diversity_ratio"]) \
        if meaningful else None
    best_hymn = max(meaningful, key=lambda s: s["diversity_ratio"]) \
        if meaningful else None

    # Overused: > 20% of events.
    overused_threshold = max(1, int(total_events * 0.20))
    overused = [(k, c) for (k, c) in all_usage if c >= overused_threshold]
    overused.sort(key=lambda t: -t[1])

    # 3 low-diversity example hymns (min ratio, require >= 6 events).
    examples_pool = [s for s in per_hymn_stats if s["n_events"] >= 6]
    examples_pool.sort(key=lambda s: (s["diversity_ratio"], -s["n_events"]))
    low_diversity_examples = examples_pool[:3]

    # ------------------------------------------------------------------
    # Write the report.
    # ------------------------------------------------------------------
    lines: list[str] = []
    lines.append("# Modern Pipeline -- Voicing Variety Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("- Hymns in lead_sheets.json: %d" % len(hymns))
    lines.append("- Hymns processed: %d" % processed_hymns)
    lines.append("- Hymns skipped: %d" % skipped_hymns)
    lines.append("- Unparseable chord annotations (total): %d"
                 % unparseable_total)
    lines.append("- Total chord events reharmonized: %d" % total_events)
    lines.append("- Voicing catalog size: %d" % catalog_size)
    lines.append("- Distinct voicings used: %d (%.1f%% of catalog)"
                 % (distinct_used, pct_used))
    lines.append("- Never-used voicings: %d" % len(never_used_keys))
    lines.append("- Avg distinct RH chords per hymn: %.2f" % avg_rh)
    lines.append("- Avg distinct LH chords per hymn: %.2f" % avg_lh)
    if worst_hymn:
        lines.append(
            "- Worst-case diversity: hymn %s (%s) -- "
            "%d distinct voicings / %d events = %.2f"
            % (worst_hymn["n"], worst_hymn["t"][:40],
               worst_hymn["distinct_voicings"], worst_hymn["n_events"],
               worst_hymn["diversity_ratio"]))
    if best_hymn:
        lines.append(
            "- Best-case diversity:  hymn %s (%s) -- "
            "%d distinct voicings / %d events = %.2f"
            % (best_hymn["n"], best_hymn["t"][:40],
               best_hymn["distinct_voicings"], best_hymn["n_events"],
               best_hymn["diversity_ratio"]))
    lines.append("")
    lines.append("### Interpretation")
    lines.append("")
    if pct_used < 50:
        interp = ("Catalog coverage is low: the picker only reaches "
                  "%.0f%% of available voicings. This suggests the "
                  "LH-must-match filter is too restrictive, or the "
                  "variety penalties do not escape the top-ranked "
                  "candidates often enough." % pct_used)
    elif pct_used < 75:
        interp = ("Catalog coverage is moderate (%.0f%%). A handful of "
                  "voicings dominate; increasing the rolling-history "
                  "window or boosting the pattern-variety bonus would "
                  "spread load to the tail." % pct_used)
    else:
        interp = ("Catalog coverage is good (%.0f%%)." % pct_used)
    lines.append(interp)
    lines.append("")

    # Top 10
    lines.append("## Top 10 Voicings by Usage")
    lines.append("")
    lines.append("| rank | RH | LH | count | %% of events | description |")
    lines.append("| ---: | :--- | :--- | ---: | ---: | :--- |")
    for rank, (k, c) in enumerate(top10, start=1):
        v = voicing_by_key[k]
        pct = 100.0 * c / total_events
        lines.append("| %d | %s | %s | %d | %.1f%% | %s |"
                     % (rank,
                        fmt_chord(v.rh[0], v.rh[1]),
                        fmt_chord(v.lh[0], v.lh[1]),
                        c, pct, (v.desc or "")[:50]))
    lines.append("")

    # Bottom 10 (including zeros).
    lines.append("## Bottom 10 Voicings (least used, zeros included)")
    lines.append("")
    lines.append("| rank | RH | LH | count | description |")
    lines.append("| ---: | :--- | :--- | ---: | :--- |")
    for rank, (k, c) in enumerate(bottom10, start=1):
        v = voicing_by_key[k]
        lines.append("| %d | %s | %s | %d | %s |"
                     % (rank,
                        fmt_chord(v.rh[0], v.rh[1]),
                        fmt_chord(v.lh[0], v.lh[1]),
                        c, (v.desc or "")[:50]))
    lines.append("")

    # Histogram
    lines.append("## Usage Histogram")
    lines.append("")
    max_count = max(c for (_k, c) in all_usage) if all_usage else 1
    bar_width = 40  # chars
    for (k, c) in all_usage_sorted_desc:
        v = voicing_by_key[k]
        bar_len = int(round(bar_width * c / max_count)) if max_count else 0
        bar = "#" * bar_len
        lines.append("%-18s %5d %s"
                     % (fmt_voicing_short(v), c, bar))
    lines.append("")

    # Full usage table
    lines.append("## Full Usage Table")
    lines.append("")
    lines.append("| RH | LH | count | lh_fig | rh_fig | description |")
    lines.append("| :--- | :--- | ---: | :--- | :--- | :--- |")
    for (k, c) in all_usage_sorted_desc:
        v = voicing_by_key[k]
        lines.append("| %s | %s | %d | %s | %s | %s |"
                     % (fmt_chord(v.rh[0], v.rh[1]),
                        fmt_chord(v.lh[0], v.lh[1]),
                        c, v.lh_fig, v.rh_fig, (v.desc or "")[:60]))
    lines.append("")

    # Never used
    lines.append("## Never-Used Voicings")
    lines.append("")
    if not never_used_keys:
        lines.append("_(none -- every catalog entry was selected at least once)_")
    else:
        lines.append("| RH | LH | lh_fig | rh_fig | description |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for k in never_used_keys:
            v = voicing_by_key[k]
            lines.append("| %s | %s | %s | %s | %s |"
                         % (fmt_chord(v.rh[0], v.rh[1]),
                            fmt_chord(v.lh[0], v.lh[1]),
                            v.lh_fig, v.rh_fig, (v.desc or "")[:60]))
    lines.append("")

    # Overused
    lines.append("## Overused Voicings (>= 20%% of events)")
    lines.append("")
    if not overused:
        lines.append("_(none -- no single voicing accounts for "
                     ">= 20%% of events)_")
    else:
        lines.append("| RH | LH | count | %% of events | description |")
        lines.append("| :--- | :--- | ---: | ---: | :--- |")
        for (k, c) in overused:
            v = voicing_by_key[k]
            pct = 100.0 * c / total_events
            lines.append("| %s | %s | %d | %.1f%% | %s |"
                         % (fmt_chord(v.rh[0], v.rh[1]),
                            fmt_chord(v.lh[0], v.lh[1]),
                            c, pct, (v.desc or "")[:50]))
    lines.append("")

    # Low-diversity example hymns
    lines.append("## Low-Diversity Example Hymns (developer eyeballing)")
    lines.append("")
    if not low_diversity_examples:
        lines.append("_(no hymns with >= 6 events)_")
    else:
        lines.append("| hymn | key | events | distinct voicings | "
                     "distinct RH | distinct LH | ratio | title |")
        lines.append("| ---: | :--- | ---: | ---: | ---: | ---: | ---: "
                     "| :--- |")
        for s in low_diversity_examples:
            lines.append(
                "| %s | %s | %d | %d | %d | %d | %.2f | %s |"
                % (s["n"], s["key"], s["n_events"],
                   s["distinct_voicings"], s["distinct_rh"],
                   s["distinct_lh"], s["diversity_ratio"],
                   s["t"][:40]))
    lines.append("")

    with open(REPORT_PATH, "w", encoding="ascii", errors="replace") as fh:
        fh.write("\n".join(lines))

    # ------------------------------------------------------------------
    # Stdout summary.
    # ------------------------------------------------------------------
    print("Voicing Variety Analysis")
    print("  Hymns processed:   %d / %d (skipped %d)"
          % (processed_hymns, len(hymns), skipped_hymns))
    print("  Total events:      %d" % total_events)
    print("  Catalog size:      %d" % catalog_size)
    print("  Distinct used:     %d (%.1f%%)"
          % (distinct_used, pct_used))
    print("  Never used:        %d" % len(never_used_keys))
    print("  Avg RH/hymn:       %.2f" % avg_rh)
    print("  Avg LH/hymn:       %.2f" % avg_lh)
    print()
    print("Top 3 voicings:")
    for (k, c) in top10[:3]:
        v = voicing_by_key[k]
        pct = 100.0 * c / total_events
        print("  %s  %5d  (%.1f%%)  %s"
              % (fmt_voicing_short(v), c, pct, (v.desc or "")[:40]))
    print()
    print("Bottom 3 voicings:")
    for (k, c) in bottom10[:3]:
        v = voicing_by_key[k]
        print("  %s  %5d         %s"
              % (fmt_voicing_short(v), c, (v.desc or "")[:40]))
    print()
    print("Report: %s" % REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
