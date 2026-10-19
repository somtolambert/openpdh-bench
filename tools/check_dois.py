#!/usr/bin/env python3
"""check_dois.py: confirm every paper's DOI, first author, year and journal against Crossref.

Plain-language note: typing mistakes in a citation are easy to make. This
script looks up each DOI in data/extraction/sources.csv in Crossref (the
official DOI registry) and reports any mismatch. With --fill it writes the
Crossref values into empty cells.

Usage: python tools/check_dois.py [--fill]
"""
import csv
import html
import unicodedata
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "extraction", "sources.csv")


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={"User-Agent": "OpenPDH-Bench (mailto:somto.lambert@gmail.com)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        m = json.load(r)["message"]
    auth = [a for a in m.get("author", []) if a.get("sequence") == "first"] or m.get("author", [])
    year = None
    for k in ("published-print", "published-online", "issued"):
        if m.get(k, {}).get("date-parts"):
            year = m[k]["date-parts"][0][0]
            break
    def norm(x):
        return unicodedata.normalize("NFC", html.unescape(x or ""))
    return {"first_author": norm(auth[0].get("family", "")) if auth else "",
            "year": str(year or ""),
            "journal": norm((m.get("container-title") or [""])[0])}


def main():
    fill = "--fill" in sys.argv
    rows = list(csv.DictReader(open(P, encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else []
    problems = 0
    for r in rows:
        try:
            c = crossref(r["doi"])
        except Exception as e:  # noqa: BLE001
            print(f"{r['source_id']} {r['doi']}: lookup failed ({e})")
            problems += 1
            continue
        for k in ("first_author", "year", "journal"):
            mine = unicodedata.normalize("NFC", r[k].strip())
            if fill and mine == "":
                r[k] = c[k]
                print(f"{r['source_id']} {k}: filled '{c[k]}'")
            elif mine.lower() != c[k].lower():
                print(f"{r['source_id']} {k}: sheet '{mine}' vs Crossref '{c[k]}'")
                problems += 1
        time.sleep(0.2)
    if fill:
        with open(P, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print(f"{len(rows)} DOIs checked, {problems} mismatches")


if __name__ == "__main__":
    main()
