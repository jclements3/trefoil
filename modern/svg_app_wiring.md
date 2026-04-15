# Modern-mode inline-SVG wiring (sketch, not yet applied)

Parallel fallback path alongside the Verovio/MEI pipeline for the
Trefoil app's **Modern** mode. Triggered when `modern_mei.json` does
not have an entry for the current hymn but `modern_svg.json` does.

Asset file: `app/app/src/main/assets/modern_svg.json` --
top-level object `{ <cleanTitle>: <svg-string>, ... }`, produced by
`python3.10 -m modern.build_svg`.

## Required additions to `app/app/src/main/assets/index.html`

### 1. Global declaration (near the `MODERN_MEI = {}` line)

```js
var MODERN_SVG = {};
```

### 2. Fetch on startup (insert after the existing `xhr_modern` block
that loads `modern_mei.json`, ~line 2282)

```js
var xhr_modern_svg = new XMLHttpRequest();
xhr_modern_svg.open('GET', 'modern_svg.json?v=' + Date.now(), true);
xhr_modern_svg.onload = function() {
  if (xhr_modern_svg.status === 200) {
    try {
      MODERN_SVG = JSON.parse(xhr_modern_svg.responseText) || {};
      console.log('Loaded ' + Object.keys(MODERN_SVG).length +
                  ' Modern inline SVGs');
    } catch (e) { console.warn('modern_svg.json parse failed:', e); }
  }
};
xhr_modern_svg.onerror = function() {
  console.warn('modern_svg.json fetch failed');
};
xhr_modern_svg.send();
```

### 3. Render branch (inside `if (modernMode && !tchMei) { ... }`,
~line 885, BEFORE the placeholder text)

```js
if (modernMode && !tchMei) {
  var cleanT = drill.t.replace(/^\d+\s*/, '').trim();
  var svgStr = MODERN_SVG[cleanT];
  if (svgStr) {
    $title.textContent = drill.t;
    $container.innerHTML = svgStr;
    var svgs = $container.getElementsByTagName('svg');
    var totalH = 0;
    for (var i = 0; i < svgs.length; i++) {
      totalH += parseFloat(svgs[i].getAttribute('height') || 0);
    }
    var areaH = $area.offsetHeight - 50;
    svgScale = (areaH > 0 && totalH > 0) ? (areaH * 0.95) / totalH : 1;
    if (svgScale > 3) svgScale = 3;
    $container.style.transformOrigin = '0 0';
    $container.style.transform = 'scale(' + svgScale + ')';
    positionPlayhead();
    abc = null;
    tchMidiData = null;
    return;
  }
  // Fall through to existing "not yet available" placeholder.
  ...
}
```

## Caveats for the follow-up patch

- The SVG path exports no timemap or MIDI -- playhead sync and audio
  should be disabled (or use a bar-position fallback) when MODERN_SVG
  is the active renderer.
- MEI still wins when both are available: the outer `tchMei &&` guard
  above this branch remains intact.
- LilyPond-emitted SVGs are standalone (viewBox + width/height) and
  inject cleanly via `innerHTML` after `strip_xml_preamble` has
  stripped the `<?xml?>` / `<!DOCTYPE>` preamble (done by the Python
  builder before packing into JSON).
