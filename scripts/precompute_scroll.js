#!/usr/bin/env node
/**
 * Precompute scroll curves for each hymn by rendering ABC through abc2svg
 * and capturing note X positions. Pairs with precomputed note times (nt).
 *
 * Input:  app/ssaattbb_data.json (with 'abc', 'nt' fields)
 * Output: same file with added 'scrollCurve' field: [[time_ms, x_fraction], ...]
 *         where x_fraction = 0.0 (first note) to 1.0 (last note)
 */

var fs = require('fs');
var path = require('path');

// Load abc2svg
var abc2svg = require(path.join(__dirname, '../app/app/src/main/assets/abc2svg/abc2svg-1.js'));

var dataPath = path.join(__dirname, '../app/ssaattbb_data.json');
var data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

console.log('Processing ' + data.length + ' hymns...');

var processed = 0, failed = 0;

for (var h = 0; h < data.length; h++) {
  var hymn = data[h];
  var abcText = hymn.abc;
  var noteTimes = hymn.nt || [];

  if (!abcText || noteTimes.length === 0) {
    failed++;
    continue;
  }

  // Render through abc2svg, capture note positions with Y for voice filtering
  var allNotes = [];
  try {
    var user = {
      img_out: function() {},
      anno_stop: function(type, start, stop, x, y, w, h) {
        if (type === 'note' || type === 'rest') {
          allNotes.push({x: x, y: y});
        }
      },
      errmsg: function() {},
      read_file: function() { return ''; }
    };

    var abc = new abc2svg.Abc(user);
    abc.tosvg('hymn', abcText);
  } catch(e) {
    failed++;
    continue;
  }

  if (allNotes.length === 0) {
    failed++;
    continue;
  }

  // Filter to melody voice only: melody is the topmost staff (smallest y)
  // Find the Y range of the first few notes (they're melody = voice 0)
  var melNotes = noteTimes.length;
  var melY = allNotes[0].y;  // first note is always melody
  var yTolerance = 30;  // notes within 30 units of melY are melody voice

  var melXs = [];
  for (var i = 0; i < allNotes.length; i++) {
    if (Math.abs(allNotes[i].y - melY) < yTolerance) {
      melXs.push(allNotes[i].x);
    }
  }

  // melXs should now have only melody note X positions
  // Match count with noteTimes
  var useXs = melXs;
  if (melXs.length < melNotes) {
    // Fallback: widen tolerance
    useXs = [];
    var yMin = melY - 50, yMax = melY + 50;
    for (var i = 0; i < allNotes.length; i++) {
      if (allNotes[i].y >= yMin && allNotes[i].y <= yMax) {
        useXs.push(allNotes[i].x);
      }
    }
  }

  // Build scroll curve from melody X positions
  var nPoints = Math.min(useXs.length, melNotes);
  if (nPoints < 2) { failed++; continue; }

  var firstX = useXs[0];
  var lastX = useXs[nPoints - 1];
  var melRange = lastX - firstX;

  var scrollCurve = [];
  for (var i = 0; i < nPoints; i++) {
    var xFrac = melRange > 0 ? (useXs[i] - firstX) / melRange : 0;
    scrollCurve.push([noteTimes[i], Math.round(xFrac * 10000) / 10000]);
  }
  // Add endpoint
  scrollCurve.push([hymn.dur || noteTimes[nPoints - 1] + 1000, 1.0]);

  // Smooth the x_fraction values with a weighted moving average
  // This prevents jerky speed changes between dense and sparse passages
  // Keep first and last points fixed (0.0 and 1.0)
  var smoothed = scrollCurve.slice();
  var windowSize = 10;
  for (var pass = 0; pass < 10; pass++) {  // heavy smoothing
    var prev = smoothed.slice();
    for (var i = 1; i < smoothed.length - 1; i++) {
      var sum = 0, count = 0;
      for (var j = Math.max(0, i - windowSize); j <= Math.min(smoothed.length - 1, i + windowSize); j++) {
        var weight = windowSize + 1 - Math.abs(j - i);
        sum += prev[j][1] * weight;
        count += weight;
      }
      smoothed[i] = [smoothed[i][0], Math.round(sum / count * 10000) / 10000];
    }
    // Enforce monotonicity after smoothing
    for (var i = 1; i < smoothed.length; i++) {
      if (smoothed[i][1] < smoothed[i-1][1]) smoothed[i][1] = smoothed[i-1][1];
    }
  }

  hymn.sc = smoothed;
  processed++;
}

// Write back
var outPaths = [
  path.join(__dirname, '../app/ssaattbb_data.json'),
  path.join(__dirname, '../app/app/src/main/assets/ssaattbb_data.json')
];

for (var p = 0; p < outPaths.length; p++) {
  fs.writeFileSync(outPaths[p], JSON.stringify(data));
}

console.log('Done: ' + processed + ' processed, ' + failed + ' failed');
