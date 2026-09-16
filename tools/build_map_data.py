#!/usr/bin/env python3
"""Build the world-map data embedded in index.html.

Fetches Natural Earth 50m country polygons (TopoJSON, via jsDelivr), decodes the
quantised delta arcs, simplifies each ring with Douglas-Peucker, and emits
`window.MAPDATA = {...}` into src/mapdata.js.

Rings are stored as flat [lon*Q, lat*Q, lon*Q, lat*Q, ...] integer arrays to keep
the file small; the app divides by Q at load. Q=20 is ~0.05 deg, finer than one
screen pixel at the maximum zoom the app allows.

Usage:  python3 tools/build_map_data.py [out_path]
"""
import json
import math
import os
import sys
import urllib.request

SRC = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"
TOL_LAND = 0.05      # deg, ~5.5 km
TOL_BORDER = 0.08
Q = 20               # quantisation: 20 units per degree


def fetch(url, cache="/tmp/countries50.json"):
    if os.path.exists(cache) and os.path.getsize(cache) > 100_000:
        return json.load(open(cache))
    with urllib.request.urlopen(url, timeout=60) as r:
        raw = r.read()
    open(cache, "wb").write(raw)
    return json.loads(raw)


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def rdp(pts, tol):
    """Iterative Douglas-Peucker on a (lon, lat) polyline."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        den = math.hypot(dx, dy)
        best, bi = -1.0, -1
        for k in range(i + 1, j):
            x, y = pts[k]
            d = math.hypot(x - x1, y - y1) if den == 0 else abs(dy * x - dx * y + x2 * y1 - y2 * x1) / den
            if d > best:
                best, bi = d, k
        if best > tol:
            keep[bi] = True
            stack += [(i, bi), (bi, j)]
    return [p for p, k in zip(pts, keep) if k]


def rings_for(topo, arcs, obj):
    out = []
    for g in topo["objects"][obj]["geometries"]:
        c = g["arcs"]
        polys = [c] if g["type"] == "Polygon" else (c if g["type"] == "MultiPolygon" else [])
        for poly in polys:
            for r in poly:
                pts = []
                for i in r:
                    seg = arcs[i] if i >= 0 else arcs[~i][::-1]
                    pts.extend(seg if not pts else seg[1:])
                if len(pts) >= 4:
                    out.append(pts)
    return out


def border_arcs(topo, arcs):
    used, out = set(), []
    for g in topo["objects"]["countries"]["geometries"]:
        idxs = []

        def walk(a):
            if isinstance(a[0], list):
                for s in a:
                    walk(s)
            else:
                idxs.extend(a)

        walk(g["arcs"])
        for i in idxs:
            k = abs(i) if i >= 0 else ~i
            if k in used:
                continue
            used.add(k)
            out.append(arcs[k])
    return out


# NOTE: do NOT split rings at the antimeridian. The source rings are whole
# closed "belt" polygons that cross +-180 exactly once, through a horizontal
# edge at constant latitude. Splitting them leaves two OPEN sub-paths, and a
# canvas fill() then closes each one with a straight line from the seam back to
# the ring's start point - which paints a wide diagonal band across the map.
# Filling the ring whole is correct: the wrap edge is horizontal at the seam.


def quant(pts):
    out = []
    for lon, lat in pts:
        a, b = int(round(lon * Q)), int(round(lat * Q))
        if len(out) >= 2 and out[-2] == a and out[-1] == b:
            continue
        out.append(a)
        out.append(b)
    return out


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "mapdata.js")
    topo = fetch(SRC)
    arcs = decode_arcs(topo)

    # Fill from the COUNTRIES object, not "land". The land object joins Eurasia
    # to Alaska across the Bering Strait into one globe-wrapping belt polygon;
    # once such a ring is cut at the antimeridian its interior is ambiguous and
    # the fill paints a band across the map. Country rings are simple regions
    # (plus their lake holes), so a cut piece always fills as the right land.
    # The same rings serve as the coastline + border strokes.
    rings = []
    for r in rings_for(topo, arcs, "countries"):
        q = quant(rdp(r, TOL_LAND))
        if len(q) >= 6:
            rings.append(q)
    payload = json.dumps({"q": Q, "l": rings, "b": []}, separators=(",", ":"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("window.MAPDATA=%s;\n" % payload)
    pts = sum(len(r) for r in rings) // 2
    print("rings: %d | points: %d | %.1f KB" % (len(rings), pts, len(payload) / 1024.0))
    print("written: %s" % out_path)


if __name__ == "__main__":
    main()
