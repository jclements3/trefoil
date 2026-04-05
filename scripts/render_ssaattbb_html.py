#!/usr/bin/env python3
"""Render each SSAATTBB abc file as a standalone HTML using abc2svg."""

import glob
import os
import json
from pathlib import Path

PROJECT = Path(__file__).parent.parent
ABC_DIR = PROJECT / 'handout/ssaattbb_out'
ABC2SVG = 'app/app/src/main/assets/abc2svg/abc2svg-1.js'

# Relative path from ssaattbb_out to abc2svg
REL_ABC2SVG = os.path.relpath(PROJECT / ABC2SVG, ABC_DIR)

count = 0
for abcpath in sorted(glob.glob(str(ABC_DIR / '*.abc'))):
    htmlpath = abcpath.replace('.abc', '.html')

    # Skip if HTML already exists and is newer than ABC
    if os.path.exists(htmlpath) and os.path.getmtime(htmlpath) > os.path.getmtime(abcpath):
        continue

    with open(abcpath) as f:
        abc_content = f.read()

    title = 'SSAATTBB'
    for line in abc_content.split('\n'):
        if line.startswith('T:'):
            title = line[2:].strip()
            break

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title} — SSAATTBB</title>
<style>
body {{ font-family: sans-serif; margin: 20px; background: #fff; }}
h1 {{ font-size: 18px; }}
</style>
</head>
<body>
<h1>{title} — SSAATTBB</h1>
<div id="music"></div>
<script src="{REL_ABC2SVG}"></script>
<script>
var abc_src = {json.dumps(abc_content)};
var user = {{
  img_out: function(str) {{ document.getElementById("music").innerHTML += str; }},
  errmsg: function(msg) {{ console.warn("abc2svg:", msg); }},
  read_file: function() {{ return ""; }}
}};
var abc = new abc2svg.Abc(user);
abc.tosvg("score", abc_src);
</script>
</body>
</html>'''

    with open(htmlpath, 'w') as f:
        f.write(html)
    count += 1

print(f'Rendered {count} HTML files')
