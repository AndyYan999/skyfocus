#!/usr/bin/env python3
"""Assemble index.html from src/template.html + src/mapdata.js.

The template carries a `<script>/*__MAPDATA__*/</script>` placeholder; the world
map data is injected there so the shipped index.html stays a single
self-contained file with no network access at runtime.

Usage:  python3 tools/build.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "src", "template.html")
DATA = os.path.join(ROOT, "src", "mapdata.js")
OUT = os.path.join(ROOT, "index.html")
PLACEHOLDER = "/*__MAPDATA__*/"


def main():
    tpl = open(TPL).read()
    data = open(DATA).read().strip() if os.path.exists(DATA) else "window.MAPDATA={q:20,l:[],b:[]};"
    if PLACEHOLDER not in tpl:
        sys.exit("placeholder %s not found in %s" % (PLACEHOLDER, TPL))
    html = tpl.replace(PLACEHOLDER, data)
    open(OUT, "w").write(html)
    print("built %s  (%.1f KB, map data %.1f KB)" % (OUT, len(html) / 1024.0, len(data) / 1024.0))


if __name__ == "__main__":
    main()
