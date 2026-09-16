#!/usr/bin/env python3
"""Build the searchable airport list embedded in index.html.

Source: OurAirports (public domain), downloaded once and cached in /tmp.
Keeps large airports that have an IATA code and scheduled service - the set a
traveller would actually recognise - and writes a compact JS array.

Usage:  python3 tools/build_airports.py [out_path]
"""
import csv
import json
import os
import sys
import urllib.request

URL = "https://cdn.jsdelivr.net/gh/davidmegginson/ourairports-data@master/airports.csv"
CACHE = "/tmp/airports.csv"


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "airports.js")

    if not (os.path.exists(CACHE) and os.path.getsize(CACHE) > 1_000_000):
        with urllib.request.urlopen(URL, timeout=120) as r:
            open(CACHE, "wb").write(r.read())

    rows = []
    with open(CACHE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["type"] != "large_airport" or not (r["iata_code"] or "").strip():
                continue
            if r["scheduled_service"] != "yes":
                continue
            try:
                lat = float(r["latitude_deg"]); lon = float(r["longitude_deg"])
            except (TypeError, ValueError):
                continue
            # [iata, city, name, country, lat, lon] - name trimmed for size
            rows.append([r["iata_code"].strip(), (r["municipality"] or "").strip(),
                         (r["name"] or "").strip()[:26], r["iso_country"],
                         round(lat, 2), round(lon, 2)])
    rows.sort()
    payload = json.dumps(rows, separators=(",", ":"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("window.AIRPORTS_DB=%s;\n" % payload)
    print("airports: %d | %.1f KB | written: %s" % (len(rows), len(payload) / 1024.0, out_path))


if __name__ == "__main__":
    main()
