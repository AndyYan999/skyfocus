#!/usr/bin/env python3
"""Assemble index.html from src/template.html + the generated data files.

The template carries <script>/*__MAPDATA__*/</script> and
<script>/*__AIRPORTS__*/</script> placeholders; the world map polygons and the
airport list are injected there so the shipped index.html stays a single
self-contained file with no network access at runtime.

Usage:  python3 tools/build.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "src", "template.html")
OUT = os.path.join(ROOT, "index.html")
PARTS = {"/*__MAPDATA__*/": ("mapdata.js", "window.MAPDATA={q:20,l:[],b:[]};"),
         "/*__AIRPORTS__*/": ("airports.js", "window.AIRPORTS_DB=[];")}


def main():
    tpl = open(TPL).read()
    sizes = []
    for placeholder, (name, fallback) in PARTS.items():
        if placeholder not in tpl:
            sys.exit("placeholder %s not found in %s" % (placeholder, TPL))
        path = os.path.join(ROOT, "src", name)
        data = open(path).read().strip() if os.path.exists(path) else fallback
        tpl = tpl.replace(placeholder, data)
        sizes.append("%s %.1f KB" % (name, len(data) / 1024.0))
    open(OUT, "w").write(tpl)
    print("built %s (%.1f KB) | %s" % (OUT, len(tpl) / 1024.0, ", ".join(sizes)))


if __name__ == "__main__":
    main()
