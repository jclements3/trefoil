"""Extract 100 unique music-notation stills from 100JazzLicks.mp4.

Strategy: sample 2 fps, compute dHash on the music-band crop + a white-ratio
score (music band is mostly white; pink background / transitions are not).
Find stable runs = consecutive frames where dHash hamming distance stays small
AND white-ratio is high. Each run = one lick. Emit center frame.
"""
from __future__ import annotations
import subprocess, sys, os, json
from pathlib import Path
import cv2
import numpy as np

VIDEO = Path(os.environ.get("LICKS_VIDEO",
    "/home/clementsj/projects/trefoil/images/100JazzLicks.mp4"))
WORK = Path(os.environ.get("LICKS_WORK",
    "/home/clementsj/projects/trefoil/images/100jazzlicks_work"))
FRAMES = WORK / "frames"
OUT_DIR = Path(os.environ.get("LICKS_OUT",
    "/home/clementsj/projects/trefoil/images"))  # final {NN}licks.jpg

FPS_SAMPLE = 2.0               # sample rate for detection
# Music-band crop. Tuned as ratios of video height so we work on any resolution.
# On the original 1392x788 source this was y=180..560 (center band, skipping
# the wings-badge above and the keyboard below).
def _probe_dims():
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", str(VIDEO),
    ], text=True).strip()
    w, h = out.split("x")
    return int(w), int(h)
VIDEO_W, VIDEO_H = _probe_dims()
CROP_Y0 = int(VIDEO_H * 180 / 788)
CROP_Y1 = int(VIDEO_H * 560 / 788)
CROP_X0, CROP_X1 = 0, VIDEO_W
WHITE_THRESH = 220             # pixel >= this counts as "white"
MIN_WHITE_RATIO = 0.20         # music band threshold (tuned for 1080p compression)
DHASH_SIZE = 16                # 16x16 dHash → 240-bit fingerprint
STABLE_HAMMING = 20            # <= this = same lick (tuned for 1080p frames)
MIN_RUN_FRAMES = 3             # >= 1.5s of stable content to count as a lick

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def extract_frames():
    FRAMES.mkdir(parents=True, exist_ok=True)
    # Clean prior frames
    for f in FRAMES.glob("f_*.jpg"):
        f.unlink()
    # Extract at FPS_SAMPLE, cropped on-the-fly to save disk
    crop_w = CROP_X1 - CROP_X0
    crop_h = CROP_Y1 - CROP_Y0
    vf = f"fps={FPS_SAMPLE},crop={crop_w}:{crop_h}:{CROP_X0}:{CROP_Y0}"
    cmd = [
        "ffmpeg", "-y", "-i", str(VIDEO),
        "-vf", vf, "-q:v", "4",
        str(FRAMES / "f_%05d.jpg"),
        "-loglevel", "error",
    ]
    print(f"[extract] {' '.join(cmd)}")
    run(cmd)
    frames = sorted(FRAMES.glob("f_*.jpg"))
    print(f"[extract] wrote {len(frames)} frames")
    return frames

def dhash(img_gray, size=DHASH_SIZE):
    # Resize to (size+1, size) and compare horizontally
    r = cv2.resize(img_gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    diff = r[:, 1:] > r[:, :-1]
    # Pack as bytes
    return np.packbits(diff.flatten())

def hamming(a, b):
    return int(np.unpackbits(a ^ b).sum())

def analyze(frames):
    rows = []
    for i, f in enumerate(frames):
        img = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        white_ratio = float((gray >= WHITE_THRESH).mean())
        h = dhash(gray)
        rows.append({"idx": i, "path": str(f), "white": white_ratio, "hash": h})
        if (i + 1) % 200 == 0:
            print(f"[hash] {i+1}/{len(frames)}")
    return rows

def find_runs(rows):
    """Group consecutive frames that are both 'music-like' (white-rich) and
    similar to the previous frame. A run ends when white-ratio drops or hash
    diverges enough."""
    runs = []
    cur = None
    for r in rows:
        music = r["white"] >= MIN_WHITE_RATIO
        if not music:
            if cur is not None:
                runs.append(cur)
                cur = None
            continue
        if cur is None:
            cur = {"start": r["idx"], "end": r["idx"], "frames": [r]}
            continue
        # Compare to last frame in run
        d = hamming(cur["frames"][-1]["hash"], r["hash"])
        if d <= STABLE_HAMMING:
            cur["end"] = r["idx"]
            cur["frames"].append(r)
        else:
            runs.append(cur)
            cur = {"start": r["idx"], "end": r["idx"], "frames": [r]}
    if cur is not None:
        runs.append(cur)
    # Filter by minimum length
    runs = [r for r in runs if len(r["frames"]) >= MIN_RUN_FRAMES]
    # Split any run much longer than typical: two licks merged because the
    # hash change at the boundary sat just below STABLE_HAMMING. Within a
    # single lick the music notation is static, so the largest internal jump
    # IS the lick boundary.
    typical = sorted(len(r["frames"]) for r in runs)[len(runs)//2]
    long_thresh = int(typical * 1.4)
    out = []
    for r in runs:
        if len(r["frames"]) <= long_thresh:
            out.append(r); continue
        # Find largest internal hash jump
        fs = r["frames"]
        jumps = [(i, hamming(fs[i-1]["hash"], fs[i]["hash"])) for i in range(1, len(fs))]
        # Prefer split near the middle to avoid off-by-one tiny runs
        mid = len(fs) // 2
        ranked = sorted(jumps, key=lambda p: (-p[1], abs(p[0]-mid)))
        split_at = ranked[0][0]
        a = {"start": r["start"], "end": r["start"] + split_at - 1,
             "frames": fs[:split_at]}
        b = {"start": r["start"] + split_at, "end": r["end"],
             "frames": fs[split_at:]}
        out.extend([a, b])
    return out

def write_output(runs, frames):
    # Pick the center frame of each run, re-extract at full resolution from
    # the source video for crisp output.
    print(f"[pick] {len(runs)} stable runs found")
    # Cap / truncate to 100
    if len(runs) > 100:
        print(f"[pick] trimming {len(runs)} -> 100 (by longest duration)")
        runs = sorted(runs, key=lambda r: -len(r["frames"]))[:100]
        runs.sort(key=lambda r: r["start"])
    elif len(runs) < 100:
        print(f"[pick] WARNING only {len(runs)} runs — expected 100. "
              f"Consider loosening thresholds.")
    # For each run, midpoint timestamp
    picks = []
    for i, r in enumerate(runs):
        center_idx = (r["start"] + r["end"]) // 2
        t_sec = center_idx / FPS_SAMPLE
        picks.append((i, t_sec, r["start"] / FPS_SAMPLE, r["end"] / FPS_SAMPLE))

    (WORK / "runs.json").write_text(json.dumps(
        [{"i": i, "t": t, "start_s": s, "end_s": e} for i, t, s, e in picks],
        indent=2))

    # Clean old output files
    for f in OUT_DIR.glob("[0-9][0-9]licks.jpg"):
        f.unlink()

    # Re-extract full-res center frame with a FIXED ratio-based crop.
    # Ratios derived from sampling 12 frames of the lowres YT copy of this
    # same video (video ID 9GzIDnvDvkM): music band always sits in y=0.381..
    # 0.583 of the frame, covering both single-stave and double-stave layouts.
    # 3% pad each side → keep y=0.351..0.613. Simpler and more robust than
    # the previous adaptive white-band detector.
    CROP_TOP_RATIO = 0.310
    CROP_BOT_RATIO = 0.740
    y0 = int(VIDEO_H * CROP_TOP_RATIO)
    y1 = int(VIDEO_H * CROP_BOT_RATIO)
    crop_h = y1 - y0
    for i, t_sec, _, _ in picks:
        out = OUT_DIR / f"{i:02d}licks.jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", f"{t_sec:.3f}",
            "-i", str(VIDEO), "-vframes", "1",
            "-vf", f"crop={VIDEO_W}:{crop_h}:0:{y0}",
            "-q:v", "3",
            str(out), "-loglevel", "error",
        ]
        subprocess.run(cmd, check=True)
    print(f"[pick] wrote {len(picks)} lick images to {OUT_DIR}")

def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("extract", "all"):
        extract_frames()
    frames = sorted(FRAMES.glob("f_*.jpg"))
    if step == "extract":
        return
    if step in ("analyze", "all"):
        rows = analyze(frames)
        # Persist so we can retune without re-hashing
        np.savez(WORK / "hashes.npz",
                 idx=[r["idx"] for r in rows],
                 white=[r["white"] for r in rows],
                 hashes=np.stack([r["hash"] for r in rows]))
    data = np.load(WORK / "hashes.npz")
    rows = [{"idx": int(i), "path": str(frames[int(i)]),
             "white": float(w), "hash": h}
            for i, w, h in zip(data["idx"], data["white"], data["hashes"])]
    runs = find_runs(rows)
    print(f"[runs] {len(runs)} runs, lengths: "
          f"min={min(len(r['frames']) for r in runs)}, "
          f"max={max(len(r['frames']) for r in runs)}, "
          f"median={sorted(len(r['frames']) for r in runs)[len(runs)//2]}")
    if step in ("write", "all"):
        write_output(runs, frames)

if __name__ == "__main__":
    main()
