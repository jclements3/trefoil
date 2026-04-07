#!/usr/bin/env python3
"""
Compute smooth scroll curves for each hymn.

1. Run abc2svg (via Node) to get exact SVG pixel positions of melody notes
2. Pair with melody note timestamps from pipeline
3. Fit a smooth monotonic cubic spline (like Blender IPO curves)
4. Sample at 50ms intervals for the runtime scroll lookup table

Output: updates ssaattbb_data.json with 'sc' field = [[time_ms, x_fraction], ...]
"""

import json
import subprocess
import sys
import os
import numpy as np
from scipy.interpolate import PchipInterpolator  # monotonic cubic hermite

def get_melody_note_positions(abc_text):
    """Run abc2svg in Node to get melody note X positions."""
    node_script = r"""
    var abc2svg = require('./app/app/src/main/assets/abc2svg/abc2svg-1.js');
    var abcText = JSON.parse(process.argv[1]);
    var notes = [];
    var user = {
        img_out: function() {},
        anno_stop: function(type, start, stop, x, y, w, h) {
            if (type === 'note' || type === 'rest') {
                notes.push({x: x, y: Math.round(y)});
            }
        },
        errmsg: function() {},
        read_file: function() { return ''; }
    };
    try {
        var abc = new abc2svg.Abc(user);
        abc.tosvg('hymn', abcText);
    } catch(e) {}
    // Filter to melody voice: topmost Y (smallest Y value)
    if (notes.length === 0) { console.log('[]'); process.exit(0); }
    var melY = notes[0].y;
    var tolerance = 30;
    var melNotes = notes.filter(function(n) { return Math.abs(n.y - melY) < tolerance; });
    console.log(JSON.stringify(melNotes.map(function(n) { return n.x; })));
    """

    result = subprocess.run(
        ['node', '-e', node_script, json.dumps(abc_text)],
        capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout.strip())
    except:
        return None


def compute_scroll_curve(note_times_ms, note_xs, duration_ms, sample_interval_ms=50):
    """
    Compute a smooth monotonic scroll curve using PCHIP interpolation.

    PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) is like
    Blender's IPO curves — smooth, monotonic, no overshooting.

    Args:
        note_times_ms: list of int, time of each melody note in ms
        note_xs: list of float, SVG X position of each melody note
        duration_ms: total hymn duration in ms
        sample_interval_ms: output sampling rate

    Returns:
        list of [time_ms, x_fraction] pairs, sampled every sample_interval_ms
    """
    if len(note_times_ms) < 2 or len(note_xs) < 2:
        return []

    n = min(len(note_times_ms), len(note_xs))
    times = np.array(note_times_ms[:n], dtype=float)
    xs = np.array(note_xs[:n], dtype=float)

    # Normalize X to 0.0 - 1.0
    x_min, x_max = xs[0], xs[-1]
    x_range = x_max - x_min
    if x_range <= 0:
        return []
    x_frac = (xs - x_min) / x_range

    # Ensure monotonicity in both time and x_fraction
    # Remove any points where time doesn't increase or x doesn't increase
    clean_t = [times[0]]
    clean_x = [x_frac[0]]
    for i in range(1, len(times)):
        if times[i] > clean_t[-1] and x_frac[i] >= clean_x[-1]:
            clean_t.append(times[i])
            clean_x.append(x_frac[i])

    if len(clean_t) < 2:
        return []

    clean_t = np.array(clean_t)
    clean_x = np.array(clean_x)

    # Add endpoint at duration
    if clean_t[-1] < duration_ms:
        clean_t = np.append(clean_t, duration_ms)
        clean_x = np.append(clean_x, 1.0)

    # PCHIP interpolation: monotonic cubic hermite (like Blender IPO)
    interpolator = PchipInterpolator(clean_t, clean_x)

    # Sample at regular intervals
    sample_times = np.arange(0, duration_ms + sample_interval_ms, sample_interval_ms)
    pchip_x = interpolator(sample_times)

    # Constant-speed line (perfectly linear)
    linear_x = sample_times / duration_ms

    # Blend: 90% linear + 10% PCHIP = very smooth with subtle note tracking
    blend = 0.90
    sample_x = blend * linear_x + (1.0 - blend) * pchip_x

    # Smooth the velocity (derivative), then reintegrate
    # This prevents position jumps while making speed changes gradual
    from scipy.ndimage import gaussian_filter1d
    dx = np.diff(sample_x)
    dx_smooth = gaussian_filter1d(dx, sigma=12)
    # Ensure non-negative velocities
    dx_smooth = np.maximum(dx_smooth, 0)
    # Reintegrate and normalize to [0, 1]
    sample_x = np.concatenate([[0], np.cumsum(dx_smooth)])
    if sample_x[-1] > 0:
        sample_x = sample_x / sample_x[-1]
    sample_x = np.clip(sample_x, 0.0, 1.0)
    for i in range(1, len(sample_x)):
        if sample_x[i] < sample_x[i-1]:
            sample_x[i] = sample_x[i-1]

    # Build output: [[time_ms, x_frac], ...]
    curve = []
    for i in range(len(sample_times)):
        t = int(sample_times[i])
        x = round(float(sample_x[i]), 4)
        curve.append([t, x])

    return curve


def main():
    data_path = 'app/ssaattbb_data.json'
    with open(data_path) as f:
        data = json.load(f)

    print(f'Processing {len(data)} hymns...')

    processed = 0
    failed = 0

    for i, hymn in enumerate(data):
        abc_text = hymn.get('abc', '')
        note_times = hymn.get('nt', [])
        duration = hymn.get('dur', 0)

        if not abc_text or not note_times or not duration:
            failed += 1
            continue

        # Get melody note X positions from abc2svg
        note_xs = get_melody_note_positions(abc_text)

        if not note_xs or len(note_xs) < 2:
            failed += 1
            continue

        # Compute smooth scroll curve
        curve = compute_scroll_curve(note_times, note_xs, duration)

        if not curve:
            failed += 1
            continue

        hymn['sc'] = curve
        processed += 1

        if (i + 1) % 50 == 0:
            print(f'  {i + 1}/{len(data)}...')

    # Write back
    for path in [data_path, 'app/app/src/main/assets/ssaattbb_data.json']:
        with open(path, 'w') as f:
            json.dump(data, f)

    print(f'Done: {processed} processed, {failed} failed')

    # Print analysis for first hymn
    if data[0].get('sc'):
        sc = data[0]['sc']
        speeds = []
        for i in range(1, len(sc)):
            dt = sc[i][0] - sc[i-1][0]
            dx = sc[i][1] - sc[i-1][1]
            if dt > 0:
                speeds.append(dx / dt * 1000)
        if speeds:
            print(f'\nHymn 001 scroll analysis:')
            print(f'  Points: {len(sc)} (sampled at 50ms)')
            print(f'  Speed range: {min(speeds):.4f} to {max(speeds):.4f} frac/s')
            print(f'  Speed ratio: {max(speeds)/max(min(speeds),0.0001):.1f}x')
            avg = sum(speeds) / len(speeds)
            std = (sum((s - avg) ** 2 for s in speeds) / len(speeds)) ** 0.5
            print(f'  Average: {avg:.4f}, std: {std:.4f} (CV={std/avg:.2f})')


if __name__ == '__main__':
    main()
