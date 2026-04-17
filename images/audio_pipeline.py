"""Audio → MIDI → ABC pipeline for the 100 Jazz Licks MP4.

Stages:
  extract   : ffmpeg extracts audio from MP4 to WAV
  slice     : split WAV into 100 per-lick segments using runs.json timings
  transcribe: run Spotify Basic Pitch on each segment → MIDI + note-events JSON
  merge     : combine audio-derived pitches with existing chord skeleton
              from licks.abc → licks_audio.abc (machine-verified pitches)
  all       : run all stages in order

Re-run after dropping in a new (higher-resolution) MP4 — just overwrite
VIDEO_PATH and re-run `all`.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from fractions import Fraction

HERE = Path(__file__).parent
VIDEO_PATH = Path(os.environ.get("LICKS_VIDEO", HERE / "100JazzLicks.mp4"))
RUNS_JSON = Path(os.environ.get("LICKS_RUNS",
    HERE / "100jazzlicks_work" / "runs.json"))
WORK = Path(os.environ.get("LICKS_AUDIO_WORK", HERE / "audio_work"))
WAV_FULL = WORK / "full.wav"
SEGMENTS_DIR = WORK / "segments"
MIDI_DIR = WORK / "midi"
NOTES_DIR = WORK / "notes"          # basic-pitch note-events JSON per lick
ABC_OUT = Path(os.environ.get("LICKS_ABC_OUT", HERE / "licks_audio.abc"))

LICKS_ABC = HERE / "licks.abc"      # skeleton of chord symbols + rhythm

def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)

# ---------------- stages ----------------

def stage_extract():
    WORK.mkdir(exist_ok=True)
    if not VIDEO_PATH.exists():
        raise SystemExit(f"[extract] missing {VIDEO_PATH}")
    if WAV_FULL.exists():
        print(f"[extract] {WAV_FULL} already exists (delete to re-extract)")
        return
    run([
        "ffmpeg", "-y", "-i", str(VIDEO_PATH),
        "-vn", "-ac", "1", "-ar", "22050", "-acodec", "pcm_s16le",
        str(WAV_FULL), "-loglevel", "error",
    ])
    print(f"[extract] wrote {WAV_FULL}")

def stage_slice():
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    for f in SEGMENTS_DIR.glob("*.wav"):
        f.unlink()
    if not RUNS_JSON.exists():
        raise SystemExit(f"[slice] missing {RUNS_JSON} — re-run extract_licks.py")
    runs = json.loads(RUNS_JSON.read_text())
    assert len(runs) == 100, f"expected 100 runs, got {len(runs)}"
    for r in runs:
        idx = r["i"]
        # Slightly tight trim: start 0.3s after run start, end 0.3s before
        # (avoids transition artifacts and hand-movement noise)
        s = r["start_s"] + 0.3
        e = r["end_s"] - 0.3
        dur = max(1.0, e - s)
        out = SEGMENTS_DIR / f"{idx:02d}.wav"
        run([
            "ffmpeg", "-y", "-ss", f"{s:.3f}", "-t", f"{dur:.3f}",
            "-i", str(WAV_FULL), "-ac", "1", "-ar", "22050",
            str(out), "-loglevel", "error",
        ])
    print(f"[slice] wrote 100 segments in {SEGMENTS_DIR}")

def stage_transcribe():
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    for f in MIDI_DIR.glob("*.mid"):
        f.unlink()
    for f in NOTES_DIR.glob("*.csv"):
        f.unlink()
    segments = sorted(SEGMENTS_DIR.glob("*.wav"))
    if not segments:
        raise SystemExit("[transcribe] no segments — run slice first")
    # basic-pitch accepts many paths at once; batching is fastest
    # We want --save-midi and --save-note-events
    bp = str(Path.home() / ".local" / "bin" / "basic-pitch")
    # Run in chunks to avoid OOM on long batches
    CHUNK = 20
    # Use the ONNX model — tflite-runtime's packaged file fails to load on
    # this system, and onnxruntime is already installed.
    bp_pkg = Path.home() / ".local/lib/python3.10/site-packages/basic_pitch"
    onnx_model = bp_pkg / "saved_models/icassp_2022/nmp.onnx"
    for i in range(0, len(segments), CHUNK):
        batch = segments[i : i + CHUNK]
        print(f"[transcribe] chunk {i//CHUNK + 1}/{(len(segments)+CHUNK-1)//CHUNK}")
        cmd = [bp, str(MIDI_DIR), *[str(p) for p in batch],
               "--model-path", str(onnx_model),
               "--model-serialization", "onnx",
               "--save-midi", "--save-note-events",
               "--minimum-note-length", "30",
               "--minimum-frequency", "130",
               "--maximum-frequency", "2100",
               "--no-melodia"]
        subprocess.run(cmd, check=True)
    # Move any note-events CSVs basic-pitch produces into NOTES_DIR for tidiness
    for csv in MIDI_DIR.glob("*.csv"):
        csv.rename(NOTES_DIR / csv.name)
    n_midi = len(list(MIDI_DIR.glob("*.mid")))
    print(f"[transcribe] wrote {n_midi} MIDI files")

def stage_merge():
    """Merge audio-derived pitches with existing chord/rhythm skeleton.
    Strategy: for each lick, take onset times + pitches from the MIDI,
    quantize to 8th/16th grid, and emit ABC bars with the ORIGINAL chord
    symbols from licks.abc preserved at their correct positions."""
    import re
    import pretty_midi
    if not LICKS_ABC.exists():
        raise SystemExit(f"[merge] missing {LICKS_ABC}")
    if not MIDI_DIR.exists() or not any(MIDI_DIR.glob("*.mid")):
        raise SystemExit("[merge] no MIDI — run transcribe first")
    # Pull chord symbols for each lick from licks.abc
    src = LICKS_ABC.read_text()
    tunes = re.split(r"(?=^X:\d+)", src, flags=re.MULTILINE)
    chord_progressions: dict[int, list[str]] = {}
    for tune in tunes[1:]:
        m = re.match(r"X:(\d+)", tune)
        if not m: continue
        idx = int(m.group(1))
        k_match = re.search(r"^K:.*$", tune, re.M)
        if not k_match: continue
        body = tune[k_match.end():]
        chords = re.findall(r'"([^"]+)"', body)
        chord_progressions[idx] = chords

    midi_files = sorted(MIDI_DIR.glob("*_basic_pitch.mid"),
                        key=lambda p: int(p.stem.split("_")[0]))
    out_lines = [
        "%abc-2.1",
        "% 100 Jazz Licks — PITCHES FROM AUDIO (Basic Pitch transcription)",
        "% Rhythm quantized to 1/8 grid; chord symbols from licks.abc preserved.",
        "",
    ]
    for mf in midi_files:
        idx = int(mf.stem.split("_")[0])
        pm = pretty_midi.PrettyMIDI(str(mf))
        # Flatten all notes, sort by start time
        notes = sorted(
            [(n.start, n.end, n.pitch) for inst in pm.instruments for n in inst.notes],
            key=lambda t: t[0],
        )
        if not notes:
            out_lines.append(f"X:{idx}\nT:Lick {idx:02d} (empty)\nM:4/4\nL:1/8\nK:C\nz8 |\n")
            continue
        # Assume the segment is 4 bars = 16 beats. Scale time → beat index.
        last_end = max(n[1] for n in notes)
        beats = 16  # 4 bars × 4 beats
        scale = beats / last_end if last_end > 0 else 1.0
        # Build note events in eighth-note slots (2 per beat = 32 slots).
        # Two-piano mixed-hands source: melody is always the HIGHEST voice, so
        # per slot keep the highest concurrent pitch, not the first. Basic
        # Pitch's "monophonic" output actually reports all simultaneous notes.
        SLOTS = 32
        slot_pitch: list[int | None] = [None] * SLOTS
        for start, end, pitch in notes:
            s_slot = int(round(start * scale * 2))
            e_slot = max(s_slot + 1, int(round(end * scale * 2)))
            for k in range(max(0, s_slot), min(SLOTS, e_slot)):
                if slot_pitch[k] is None or pitch > slot_pitch[k]:
                    slot_pitch[k] = pitch
        # Convert MIDI pitches to ABC notation (K:C)
        def midi_to_abc(p):
            pcs = p % 12
            oct = p // 12 - 1  # MIDI 60 = C4; ABC C = C4
            letter_map = {0:"C",1:"^C",2:"D",3:"^D",4:"E",5:"F",
                          6:"^F",7:"G",8:"^G",9:"A",10:"^A",11:"B"}
            token = letter_map[pcs]
            # Octave markers
            if oct <= 3:
                token = token.replace("C","C").replace("D","D")  # uppercase
                token += "," * (4 - oct)
            elif oct == 4:
                pass  # uppercase default
            else:
                token = token.lower()
                token += "'" * (oct - 5)
            return token
        # Emit ABC with chord symbols
        chords = chord_progressions.get(idx, [])
        chord_per_bar = chords[:4] + [""] * (4 - len(chords))
        bar_slots = [slot_pitch[i*8:(i+1)*8] for i in range(4)]
        tune_lines = [f"X:{idx}", f"T:Lick {idx:02d}",
                      "M:4/4", "L:1/8", "K:C"]
        bar_strs = []
        for b, bar in enumerate(bar_slots):
            tokens = []
            for p in bar:
                if p is None:
                    tokens.append("z")
                else:
                    tokens.append(midi_to_abc(p))
            chord_prefix = f'"{chord_per_bar[b]}"' if chord_per_bar[b] else ""
            bar_strs.append(chord_prefix + "".join(tokens))
        tune_lines.append(" | ".join(bar_strs) + " |")
        out_lines.append("\n".join(tune_lines))
        out_lines.append("")
    ABC_OUT.write_text("\n".join(out_lines))
    print(f"[merge] wrote {ABC_OUT}")

# ---------------- driver ----------------

STAGES = {
    "extract": stage_extract,
    "slice": stage_slice,
    "transcribe": stage_transcribe,
    "merge": stage_merge,
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=list(STAGES) + ["all"])
    args = ap.parse_args()
    if args.stage == "all":
        for s in ["extract", "slice", "transcribe", "merge"]:
            print(f"=== {s} ===")
            STAGES[s]()
    else:
        STAGES[args.stage]()

if __name__ == "__main__":
    main()
