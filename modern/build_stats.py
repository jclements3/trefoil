#!/usr/bin/env python3.10
"""Build a markdown statistics dashboard for the modern reharmonization pipeline.

Runs the same pipeline as `modern.build_all` (minus the LilyPond render step)
across every hymn in `app/lead_sheets.json`, instruments `reharm_rules` to
count per-rule firings, and writes `modern/stats.md`.

Standard library + `modern.*` only. ASCII source (markdown output uses a
handful of Unicode music glyphs: degree / Greek delta / half-dim o-stroke).

Run:
    python3.10 -m modern.build_stats
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from copy import deepcopy

# Make sure repo-root imports resolve when invoked as a module OR directly.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from modern import reharm_rules  # noqa: E402
from modern import voicing_picker  # noqa: E402
from modern import abc_rewriter  # noqa: E402

LEAD_SHEETS_PATH = os.path.join(REPO_ROOT, "app", "lead_sheets.json")
HANDOUT_PATH = os.path.join(REPO_ROOT, "handout.tex")
OUT_DIR = os.path.join(REPO_ROOT, "modern")
STATS_MD = os.path.join(OUT_DIR, "stats.md")

SKIP_METERS = {"none", "3/2", "8/4"}

RULE_NAMES = [
    "IV->ii",
    "I->vi",
    "vii(dim) insert",
    "V->V7",
    "Vsus4 delay",
    "Extensions",
]


# ---------------------------------------------------------------------------
# ABC parsing helpers (subset of build_all.py)
# ---------------------------------------------------------------------------

METER_RE = re.compile(r"(?m)^M:\s*([^\n]+)")
LEN_RE = re.compile(r"(?m)^L:\s*(\d+)\s*/\s*(\d+)")
NOTE_RE = re.compile(r"(\^|=|_)?([A-Ga-gz])([\',]*)(\d+)?(/\d*)?")
TEMPO_RE = re.compile(r"(?m)^Q:\s*(.+)$")


def parse_meter(abc: str) -> str:
    m = METER_RE.search(abc)
    return m.group(1).strip() if m else "?"


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


def parse_tempo_bpm(abc: str) -> float | None:
    """Extract an integer BPM from a Q: line like `1/4=130` or `120`."""
    m = TEMPO_RE.search(abc)
    if not m:
        return None
    raw = m.group(1).strip()
    m2 = re.search(r"(\d+)\s*/\s*(\d+)\s*=\s*(\d+(?:\.\d+)?)", raw)
    if m2:
        num = int(m2.group(1))
        den = int(m2.group(2))
        bpm = float(m2.group(3))
        # Normalize to quarter-note BPM.
        quarter_bpm = bpm * (num / den) * 4.0
        return quarter_bpm
    m3 = re.search(r"(\d+(?:\.\d+)?)", raw)
    if m3:
        return float(m3.group(1))
    return None


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
    pending_chord = None
    while i < len(body):
        ch = body[i]
        if ch == '"':
            j = body.find('"', i + 1)
            if j < 0:
                break
            inside = body[i + 1:j]
            if inside.startswith("^"):
                pending_chord = inside[1:]
            i = j + 1
            continue
        m = NOTE_RE.match(body, i)
        if m and body[i] not in ("|", "[", "]"):
            tok = m.group(0)
            dur_whole = note_duration(tok, default_l)
            if pending_chord is not None:
                beat_q = pos_whole * 4.0
                events.append((beat_q, pending_chord))
                pending_chord = None
            pos_whole += dur_whole
            i = m.end()
            continue
        i += 1
    return events


# ---------------------------------------------------------------------------
# Instrumented reharmonize (rule-by-rule)
# ---------------------------------------------------------------------------

def reharmonize_with_counts(events, key: str):
    """Apply each reharm rule in isolation (stage by stage) and report how
    many events each one changed. Mirrors reharm_rules.reharmonize() exactly
    so the total matches what the production build does.
    """
    if key not in reharm_rules.KEY_PC:
        raise ValueError(f"Unsupported key {key!r}")

    out = [deepcopy(e) for e in events]
    counts = {name: 0 for name in RULE_NAMES}

    # ---- Rule 1: IV -> ii -------------------------------------------------
    for ev in out:
        if ev.is_destination:
            continue
        if reharm_rules._is_IV(ev.chord):
            cand = (2, "m7")
            if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
                ev.chord = cand
                counts["IV->ii"] += 1

    # ---- Rule 2: I -> vi --------------------------------------------------
    for i, ev in enumerate(out):
        if ev.is_destination:
            continue
        if not reharm_rules._is_I(ev.chord):
            continue
        nxt_i = reharm_rules._next_idx(out, i)
        next_is_dest_I = (
            nxt_i < len(out)
            and out[nxt_i].is_destination
            and reharm_rules._is_I(out[nxt_i].chord)
        )
        if next_is_dest_I:
            continue
        cand = (6, "m7")
        if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
            ev.chord = cand
            counts["I->vi"] += 1

    # ---- Rule 3: vii(dim) insertion --------------------------------------
    i = len(out) - 1
    while i >= 1:
        ev = out[i]
        if ev.is_destination and reharm_rules._is_I(ev.chord):
            prior = out[i - 1]
            if not (reharm_rules._is_vii_dim(prior.chord)
                    or reharm_rules._is_V(prior.chord)
                    or reharm_rules._is_V7(prior.chord)):
                ins_dur = min(0.5, prior.duration / 2.0)
                if ins_dur > 0:
                    cand = (7, "dim")
                    if not reharm_rules._any_clash(
                            cand, key, prior.melody_pitches):
                        prior.duration -= ins_dur
                        new_ev = reharm_rules.ChordEvent(
                            beat=prior.beat + prior.duration,
                            duration=ins_dur,
                            chord=cand,
                            melody_pitches=list(prior.melody_pitches),
                            is_strong_beat=False,
                            is_cadence=False,
                            is_destination=False,
                        )
                        out.insert(i, new_ev)
                        counts["vii(dim) insert"] += 1
        i -= 1

    # ---- Rule 4: V -> V7 --------------------------------------------------
    for i, ev in enumerate(out):
        if not reharm_rules._is_V(ev.chord):
            continue
        nxt_i = reharm_rules._next_idx(out, i)
        if nxt_i >= len(out):
            continue
        if reharm_rules._is_I(out[nxt_i].chord):
            cand = (5, "7")
            if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
                ev.chord = cand
                counts["V->V7"] += 1

    # ---- Rule 5: Vsus4 delay ----------------------------------------------
    i = len(out) - 1
    while i >= 0:
        ev = out[i]
        if reharm_rules._is_V7(ev.chord) or reharm_rules._is_V(ev.chord):
            nxt_i = reharm_rules._next_idx(out, i)
            if nxt_i < len(out) and reharm_rules._is_I(out[nxt_i].chord) \
                    and out[nxt_i].is_cadence:
                half = ev.duration / 2.0
                if half > 0:
                    cand = (5, "sus4")
                    if not reharm_rules._any_clash(
                            cand, key, ev.melody_pitches):
                        ev.duration -= half
                        sus_ev = reharm_rules.ChordEvent(
                            beat=ev.beat,
                            duration=half,
                            chord=cand,
                            melody_pitches=list(ev.melody_pitches),
                            is_strong_beat=ev.is_strong_beat,
                            is_cadence=False,
                            is_destination=False,
                        )
                        ev.beat += half
                        ev.is_strong_beat = False
                        out.insert(i, sus_ev)
                        counts["Vsus4 delay"] += 1
        i -= 1

    # ---- Rule 6: Extensions -----------------------------------------------
    for ev in out:
        if not ev.is_destination:
            continue
        if not ev.melody_pitches:
            continue
        chord_pcs = reharm_rules.chord_tones(ev.chord, key)
        triad_pcs = chord_pcs[:3]
        mel_pcs = {m % 12 for m in ev.melody_pitches}
        if not (mel_pcs & set(triad_pcs)):
            continue
        before = ev.chord
        if reharm_rules._is_I(ev.chord):
            four_pc = reharm_rules.degree_pc(4, key)
            seven_pc = (chord_pcs[0] + 11) % 12
            if not reharm_rules._has_pc_in_melody(ev.melody_pitches, four_pc) \
                    and not reharm_rules._ext_clash(
                        seven_pc, ev.melody_pitches):
                ev.chord = (1, "maj7")
        elif reharm_rules._is_IV(ev.chord):
            seven_of_iv_pc = (chord_pcs[0] + 11) % 12
            if not reharm_rules._has_pc_in_melody(
                    ev.melody_pitches, seven_of_iv_pc) \
                    and not reharm_rules._ext_clash(
                        seven_of_iv_pc, ev.melody_pitches):
                ev.chord = (4, "maj7")
        elif reharm_rules._is_V(ev.chord):
            cand = (5, "7")
            if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
                ev.chord = cand
        elif ev.chord[0] == 6 and ev.chord[1] == "m":
            cand = (6, "m7")
            if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
                ev.chord = cand
        elif ev.chord[0] == 2 and ev.chord[1] == "m":
            cand = (2, "m7")
            if not reharm_rules._any_clash(cand, key, ev.melody_pitches):
                ev.chord = cand
        if ev.chord != before:
            counts["Extensions"] += 1

    return out, counts


# ---------------------------------------------------------------------------
# Per-hymn pipeline
# ---------------------------------------------------------------------------

def process_hymn(hymn: dict, voicings_cache: list) -> dict | None:
    abc = hymn["abc"]
    key = hymn.get("key", "C")
    meter_num, meter_den = parse_meter_fraction(abc)
    beats_per_bar = meter_num * (4.0 / meter_den)

    raw_anns = list(abc_rewriter.iter_chord_annotations(abc))
    beat_events = iter_chord_events(abc)
    beats_by_idx: list[float | None] = []
    bi = 0
    for (_s, _e, name) in raw_anns:
        b = None
        while bi < len(beat_events):
            bb, bn = beat_events[bi]
            bi += 1
            if bn == name:
                b = bb
                break
        beats_by_idx.append(b)

    events = []
    parse_idx_map: list[int] = []
    fallback_names = [name for (_s, _e, name) in raw_anns]
    parseable = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        try:
            roman = reharm_rules.parse_chord_name(name, key)
        except Exception:
            roman = None
        if roman is None:
            continue
        parseable += 1
        beat = beats_by_idx[idx] if beats_by_idx[idx] is not None else 0.0
        next_beat = None
        for j in range(idx + 1, len(raw_anns)):
            if beats_by_idx[j] is not None:
                next_beat = beats_by_idx[j]
                break
        if next_beat is None:
            next_beat = beat + beats_per_bar
        dur = max(0.25, next_beat - beat)
        bar_pos = beat % beats_per_bar
        is_strong = (abs(bar_pos) < 1e-6) or (
            beats_per_bar >= 4 and abs(bar_pos - 2.0) < 1e-6
        )
        is_cadence = (idx >= len(raw_anns) - 2)
        is_destination = is_strong and (
            idx == 0 or fallback_names[idx - 1] != name
        )
        ev = reharm_rules.ChordEvent(
            beat=beat, duration=dur, chord=roman,
            is_strong_beat=is_strong, is_cadence=is_cadence,
            is_destination=is_destination,
        )
        events.append(ev)
        parse_idx_map.append(idx)

    try:
        new_events, rule_counts = reharmonize_with_counts(events, key)
    except Exception as exc:
        return {
            "error": f"{type(exc).__name__}: {exc}",
        }

    chord_seq = [ev.chord for ev in new_events if ev.chord is not None]
    if chord_seq:
        try:
            picked = voicing_picker.pick_sequence(chord_seq, voicings_cache)
        except Exception:
            picked = []
    else:
        picked = []

    # Count substitutions the same way build_all does.
    subs = 0
    ei = 0
    for idx, (_s, _e, name) in enumerate(raw_anns):
        if ei < len(parse_idx_map) and parse_idx_map[ei] == idx:
            orig = events[ei].chord
            new = new_events[ei].chord if ei < len(new_events) else None
            if orig != new:
                subs += 1
            ei += 1

    return {
        "key": key,
        "meter": parse_meter(abc),
        "tempo_bpm": parse_tempo_bpm(abc),
        "chord_count": len(raw_anns),
        "parseable_chord_count": parseable,
        "substitutions": subs,
        "rule_counts": rule_counts,
        "voicings": picked,
    }


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def text_hist(buckets: list[tuple[str, int]], width: int = 40) -> list[str]:
    maxv = max((v for _, v in buckets), default=0)
    if maxv == 0:
        return [f"`{label:<10}` 0" for label, _ in buckets]
    lines = []
    for label, v in buckets:
        bar = "#" * int(round(width * v / maxv))
        lines.append(f"`{label:<10}` `{bar:<{width}}` {v}")
    return lines


def fmt_chord(c: tuple[int, str]) -> str:
    deg, qual = c
    rom_upper = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}
    rom = rom_upper[deg]
    if qual in ("m", "m7", "m6"):
        rom = rom.lower()
        suf = qual[1:]
    elif qual == "dim":
        rom = rom.lower()
        suf = "\u00b0"  # degree
    elif qual == "dim7":
        rom = rom.lower()
        suf = "\u00b07"
    elif qual == "hdim7":
        rom = rom.lower()
        suf = "\u00f87"  # half-dim
    elif qual == "maj7":
        suf = "\u0394"  # Delta
    elif qual == "":
        suf = ""
    else:
        suf = qual
    return rom + suf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()

    with open(LEAD_SHEETS_PATH, "r", encoding="utf-8") as fh:
        hymns = json.load(fh)

    voicings_cache = voicing_picker.load_voicings(HANDOUT_PATH)

    total = len(hymns)
    processed = 0
    meter_skipped = []
    pipeline_errors = []

    key_counter: Counter = Counter()
    meter_counter: Counter = Counter()
    tempos: list[float] = []
    missing_tempos = 0

    total_chord_events = 0
    total_parseable = 0
    total_subs = 0
    rule_totals = {name: 0 for name in RULE_NAMES}

    # Voicing bookkeeping. Voicings are identified by (lh, rh, lh_fig, rh_fig)
    # - i.e., a full Voicing. We use the dataclass instance as the key.
    voicing_global = Counter()
    voicing_by_hymn: dict[str, Counter] = {}
    rh_by_hymn: dict[str, set] = {}

    # Build an index: each voicing -> stable id (index in catalog).
    voicing_to_id = {id(v): i for i, v in enumerate(voicings_cache)}

    per_hymn_metrics: list[dict] = []

    for h in hymns:
        n = h.get("n")
        title = h.get("t", "")
        abc = h.get("abc", "")
        key = h.get("key", "C")
        meter_str = parse_meter(abc)

        if meter_str in SKIP_METERS:
            meter_skipped.append({
                "n": n, "title": title, "key": key, "meter": meter_str,
            })
            continue

        res = process_hymn(h, voicings_cache)
        if res is None or res.get("error"):
            pipeline_errors.append({
                "n": n, "title": title, "key": key,
                "error": (res or {}).get("error", "unknown"),
            })
            continue

        processed += 1
        key_counter[res["key"]] += 1
        meter_counter[res["meter"]] += 1
        bpm = res["tempo_bpm"]
        if bpm is None:
            missing_tempos += 1
        else:
            tempos.append(bpm)

        total_chord_events += res["chord_count"]
        total_parseable += res["parseable_chord_count"]
        total_subs += res["substitutions"]
        for name, v in res["rule_counts"].items():
            rule_totals[name] += v

        hkey = str(n)
        v_counter = Counter()
        rhs = set()
        for v in res["voicings"]:
            vid = voicing_to_id.get(id(v))
            if vid is None:
                continue
            voicing_global[vid] += 1
            v_counter[vid] += 1
            rhs.add(v.rh)
        voicing_by_hymn[hkey] = v_counter
        rh_by_hymn[hkey] = rhs

        per_hymn_metrics.append({
            "n": n,
            "title": title,
            "distinct_voicings": len(v_counter),
            "distinct_rh": len(rhs),
            "chord_count": res["chord_count"],
            "substitutions": res["substitutions"],
        })

    elapsed = time.time() - t0
    print(f"Processed {processed}/{total} hymns in {elapsed:.1f}s "
          f"({len(meter_skipped)} meter-skipped, "
          f"{len(pipeline_errors)} pipeline errors).")

    # -----------------------------------------------------------------------
    # Build markdown document
    # -----------------------------------------------------------------------
    lines: list[str] = []

    lines.append("# Modern reharmonization pipeline -- statistics dashboard")
    lines.append("")
    lines.append(
        f"_Generated by `modern.build_stats` across all {total} hymns in "
        f"`app/lead_sheets.json`._")
    lines.append("")

    # ----- Section 1: Corpus overview --------------------------------------
    lines.append("## 1. Corpus overview")
    lines.append("")
    skipped_total = len(meter_skipped) + len(pipeline_errors)
    meter_cats: Counter = Counter(s["meter"] for s in meter_skipped)
    sub_rate = (100.0 * total_subs / total_parseable) if total_parseable else 0.0
    lines.append("| metric | value |")
    lines.append("|---|---|")
    lines.append(f"| Total hymns | {total} |")
    lines.append(f"| Processable hymns | {processed} |")
    lines.append(f"| Skipped (total) | {skipped_total} |")
    for meter, cnt in sorted(meter_cats.items()):
        lines.append(f"|   -- meter `M:{meter}` | {cnt} |")
    lines.append(f"|   -- pipeline errors | {len(pipeline_errors)} |")
    lines.append(f"| Total chord events (processable) | {total_chord_events} |")
    lines.append(f"| Parseable chord events | {total_parseable} |")
    lines.append(f"| Total substitutions | {total_subs} |")
    lines.append(f"| Substitution rate | {sub_rate:.1f}% "
                 "(of parseable events) |")
    lines.append("")

    # ----- Section 2: Key distribution -------------------------------------
    lines.append("## 2. Key distribution")
    lines.append("")
    key_order = ["Eb", "Bb", "F", "C", "G", "D", "A", "E"]
    key_buckets = [(k, key_counter.get(k, 0)) for k in key_order]
    # Include any extra keys that somehow slipped in.
    extras = sorted(set(key_counter) - set(key_order))
    for k in extras:
        key_buckets.append((k, key_counter[k]))
    for line in text_hist(key_buckets):
        lines.append(line)
    lines.append("")

    # ----- Section 3: Tempo distribution -----------------------------------
    lines.append("## 3. Tempo distribution")
    lines.append("")
    if tempos:
        lo = min(tempos)
        hi = max(tempos)
        tempos_sorted = sorted(tempos)
        mid = tempos_sorted[len(tempos_sorted) // 2]
        lines.append(f"- n = {len(tempos)} (missing Q: on {missing_tempos})")
        lines.append(f"- min / median / max: "
                     f"{lo:.0f} / {mid:.0f} / {hi:.0f} BPM")

        # Bucket in 10 BPM steps from 60 up to (at least) the max.
        bmin = 60
        bmax = max(200, int(hi) + 10)
        bmax = (bmax // 10) * 10 + 10
        buckets: list[tuple[str, int]] = []
        for lo_b in range(bmin, bmax, 10):
            label = f"{lo_b}-{lo_b + 10}"
            cnt = sum(1 for t in tempos if lo_b <= t < lo_b + 10)
            buckets.append((label, cnt))
        # Also show any stragglers below 60.
        below = sum(1 for t in tempos if t < bmin)
        if below:
            buckets.insert(0, (f"<{bmin}", below))

        lines.append("")
        for line in text_hist(buckets):
            lines.append(line)

        outliers = [t for t in tempos if t > 200]
        lines.append("")
        if outliers:
            lines.append(
                f"- Outliers >200 BPM: {len(outliers)} (max {hi:.0f})")
        else:
            lines.append("- No outliers above 200 BPM.")
    else:
        lines.append("_No tempo data found._")
    lines.append("")

    # ----- Section 4: Meter distribution -----------------------------------
    lines.append("## 4. Meter distribution")
    lines.append("")
    lines.append("Processed meters:")
    lines.append("")
    lines.append("| meter | count |")
    lines.append("|---|---|")
    for meter, cnt in sorted(
            meter_counter.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{meter}` | {cnt} |")
    if meter_cats:
        lines.append("")
        lines.append("Skipped meters (not yet supported):")
        lines.append("")
        lines.append("| meter | count |")
        lines.append("|---|---|")
        for meter, cnt in sorted(meter_cats.items(),
                                 key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| `M:{meter}` | {cnt} |")
    lines.append("")

    # ----- Section 5: Reharm rule usage ------------------------------------
    lines.append("## 5. Reharmonization rule usage")
    lines.append("")
    lines.append("| # | rule | fired | % of substitutions |")
    lines.append("|---|---|---|---|")
    rule_sum = sum(rule_totals.values()) or 1
    for i, name in enumerate(RULE_NAMES, start=1):
        n = rule_totals[name]
        pct = 100.0 * n / rule_sum
        lines.append(f"| {i} | {name} | {n} | {pct:.1f}% |")
    lines.append(f"| | **sum of rule firings** | **{sum(rule_totals.values())}** | 100% |")
    lines.append("")
    lines.append(
        f"_Note: total substitutions counted above ({total_subs}) counts "
        "events whose chord identity changed vs. the input. Rule firings "
        "can exceed this if a later rule overwrites an earlier rule's output "
        "on the same event, or can be less if a rule inserts a chord rather "
        "than replacing one._")
    lines.append("")

    # ----- Section 6: Voicing usage ----------------------------------------
    lines.append("## 6. Voicing usage")
    lines.append("")
    lines.append(
        f"Full catalog: {len(voicings_cache)} voicings parsed from "
        "`handout.tex`.")
    lines.append("")

    # Per-voicing per-hymn count. Count how many hymns use each voicing.
    hymn_usage_for_voicing: Counter = Counter()
    for _hkey, vc in voicing_by_hymn.items():
        for vid in vc:
            hymn_usage_for_voicing[vid] += 1

    # Catalog table.
    lines.append("### 6a. Full catalog")
    lines.append("")
    lines.append("| id | LH | RH | lh_fig | rh_fig | desc | uses | hymns |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, v in enumerate(voicings_cache):
        uses = voicing_global.get(i, 0)
        hymn_hits = hymn_usage_for_voicing.get(i, 0)
        desc = v.desc.replace("|", "/")
        lines.append(
            f"| {i} | {fmt_chord(v.lh)} | {fmt_chord(v.rh)} | "
            f"`{v.lh_fig}` | `{v.rh_fig}` | {desc} | {uses} | {hymn_hits} |")
    lines.append("")

    # Heatmap: row = LH chord, col = RH chord, cell = sum of usage over
    # all voicings matching that (LH, RH) pair.
    lines.append("### 6b. LH vs. RH heatmap (sum of voicing uses)")
    lines.append("")
    lh_set = []
    rh_set = []
    for v in voicings_cache:
        if v.lh not in lh_set:
            lh_set.append(v.lh)
        if v.rh not in rh_set:
            rh_set.append(v.rh)
    # Stable order: sort by (degree, quality).
    lh_set.sort(key=lambda c: (c[0], c[1]))
    rh_set.sort(key=lambda c: (c[0], c[1]))

    # Build cell counts.
    pair_count: dict[tuple, int] = defaultdict(int)
    for i, v in enumerate(voicings_cache):
        pair_count[(v.lh, v.rh)] += voicing_global.get(i, 0)

    header = "| LH \\ RH | " + " | ".join(fmt_chord(r) for r in rh_set) + " |"
    lines.append(header)
    lines.append("|---" * (len(rh_set) + 1) + "|")
    for lh in lh_set:
        cells = []
        for rh in rh_set:
            v = pair_count.get((lh, rh), 0)
            cells.append(str(v) if v else ".")
        lines.append(f"| **{fmt_chord(lh)}** | " + " | ".join(cells) + " |")
    lines.append("")

    # Top 10.
    sorted_by_use = sorted(
        range(len(voicings_cache)),
        key=lambda i: (-voicing_global.get(i, 0), i),
    )
    lines.append("### 6c. Top 10 most-used voicings")
    lines.append("")
    lines.append("| rank | id | LH | RH | lh_fig | rh_fig | desc | uses |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for rank, vid in enumerate(sorted_by_use[:10], start=1):
        v = voicings_cache[vid]
        lines.append(
            f"| {rank} | {vid} | {fmt_chord(v.lh)} | {fmt_chord(v.rh)} | "
            f"`{v.lh_fig}` | `{v.rh_fig}` | {v.desc.replace('|', '/')} | "
            f"{voicing_global.get(vid, 0)} |")
    lines.append("")

    # Bottom 10 (including unused).
    bottom = sorted(
        range(len(voicings_cache)),
        key=lambda i: (voicing_global.get(i, 0), i),
    )[:10]
    lines.append("### 6d. Bottom 10 least-used voicings")
    lines.append("")
    lines.append("| rank | id | LH | RH | lh_fig | rh_fig | desc | uses |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for rank, vid in enumerate(bottom, start=1):
        v = voicings_cache[vid]
        lines.append(
            f"| {rank} | {vid} | {fmt_chord(v.lh)} | {fmt_chord(v.rh)} | "
            f"`{v.lh_fig}` | `{v.rh_fig}` | {v.desc.replace('|', '/')} | "
            f"{voicing_global.get(vid, 0)} |")
    lines.append("")

    # Unused.
    unused = [i for i in range(len(voicings_cache))
              if voicing_global.get(i, 0) == 0]
    lines.append(f"### 6e. Unused voicings ({len(unused)})")
    lines.append("")
    if unused:
        lines.append("| id | LH | RH | lh_fig | rh_fig | desc |")
        lines.append("|---|---|---|---|---|---|")
        for vid in unused:
            v = voicings_cache[vid]
            lines.append(
                f"| {vid} | {fmt_chord(v.lh)} | {fmt_chord(v.rh)} | "
                f"`{v.lh_fig}` | `{v.rh_fig}` | "
                f"{v.desc.replace('|', '/')} |")
    else:
        lines.append("_None -- every voicing in the catalog was used "
                     "at least once._")
    lines.append("")

    # ----- Section 7: Per-hymn metrics -------------------------------------
    lines.append("## 7. Per-hymn metrics")
    lines.append("")
    if per_hymn_metrics:
        dvs = [p["distinct_voicings"] for p in per_hymn_metrics]
        drs = [p["distinct_rh"] for p in per_hymn_metrics]
        avg_dv = sum(dvs) / len(dvs)
        avg_dr = sum(drs) / len(drs)
        lines.append(f"- Avg distinct voicings per hymn: **{avg_dv:.2f}**")
        lines.append(f"- Avg distinct RH chords per hymn: **{avg_dr:.2f}**")
        lines.append(f"- Hymns measured: {len(per_hymn_metrics)}")
        lines.append("")

        # Fewest distinct voicings.
        sorted_fewest = sorted(
            per_hymn_metrics,
            key=lambda p: (p["distinct_voicings"], p["n"]),
        )
        lines.append("### 7a. 10 hymns with fewest distinct voicings")
        lines.append("")
        lines.append(
            "| n | title | chords | distinct voicings | distinct RH |")
        lines.append("|---|---|---|---|---|")
        for p in sorted_fewest[:10]:
            t = p["title"].replace("|", "/")
            lines.append(
                f"| {p['n']} | {t} | {p['chord_count']} | "
                f"{p['distinct_voicings']} | {p['distinct_rh']} |")
        lines.append("")

        # Most distinct voicings.
        sorted_most = sorted(
            per_hymn_metrics,
            key=lambda p: (-p["distinct_voicings"], p["n"]),
        )
        lines.append("### 7b. 10 hymns with most distinct voicings")
        lines.append("")
        lines.append(
            "| n | title | chords | distinct voicings | distinct RH |")
        lines.append("|---|---|---|---|---|")
        for p in sorted_most[:10]:
            t = p["title"].replace("|", "/")
            lines.append(
                f"| {p['n']} | {t} | {p['chord_count']} | "
                f"{p['distinct_voicings']} | {p['distinct_rh']} |")
        lines.append("")
    else:
        lines.append("_No hymns produced voicings._")
        lines.append("")

    # ----- Section 8: Known limitations ------------------------------------
    lines.append("## 8. Known limitations")
    lines.append("")
    lines.append(
        "- **Non-diatonic chord labels** -- when an original ABC `\"^X\"` "
        "annotation uses a chord root outside the lever-harp key, "
        "`parse_chord_name()` returns `None` and that event is skipped "
        "(the rewriter re-emits the original label unchanged). Currently "
        f"{total_parseable} of {total_chord_events} "
        f"({100.0 * total_parseable / max(total_chord_events, 1):.1f}%) "
        "chord events are parseable. Roughly 54 hymns ship with at least "
        "one non-diatonic label; another agent is expanding the parser to "
        "emit off-key roots as accidentals.")
    lines.append(
        "- **Meter exceptions** -- "
        f"{len(meter_skipped)} hymns are skipped today: "
        f"{meter_cats.get('none', 0)} `M:none`, "
        f"{meter_cats.get('3/2', 0)} `M:3/2`, and "
        f"{meter_cats.get('8/4', 0)} `M:8/4`. Another agent is extending "
        "the meter handler to cover the compound / irregular cases.")
    lines.append(
        "- **Melody + chord-fractions only** -- the current output is a "
        "lead sheet with stacked RH/LH Roman labels above the melody. "
        "The pipeline does not (yet) emit realized harp voicings onto "
        "separate staves. That is handled by the Tch-SSAATTBBP composed "
        "MEI pipeline, which is independent.")
    lines.append("")

    # Footer.
    lines.append("---")
    lines.append(f"_Build time: {elapsed:.1f}s._")
    lines.append("")

    with open(STATS_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"Wrote {STATS_MD} ({sum(len(l) for l in lines)} bytes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
