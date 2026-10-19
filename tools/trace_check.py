#!/usr/bin/env python3
"""trace_check.py: confirm each entered number actually appears in the paper's text.

Plain-language note: a typing slip (34.9 entered as 39.4) is the most likely
extraction error. For every paper whose full text was downloaded from Europe
PMC (data/raw/literature/<PMCID>.txt, not published), this script checks that
each conversion and selectivity value in measurements.csv appears somewhere in
that paper's text or tables. It cannot prove a number is attached to the right
catalyst; that is what the hand spot-checks are for. It only catches numbers
that are not in the paper at all.

Usage: python tools/trace_check.py
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIT = os.path.join(ROOT, "data", "raw", "literature")


def variants(v):
    f = float(v)
    out = {v, f"{f:g}", f"{f:.1f}", f"{f:.2f}"}
    if f == int(f):
        out.add(str(int(f)))
    return {o for o in out if o}


def main():
    src = {r["source_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/extraction/sources.csv"), encoding="utf-8"))}
    cat = {r["catalyst_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/extraction/catalysts.csv"), encoding="utf-8"))}
    texts = {}
    checked = missing = skipped = 0
    for r in csv.DictReader(open(os.path.join(ROOT, "data/extraction/measurements.csv"), encoding="utf-8")):
        sid = cat[r["catalyst_id"]]["source_id"]
        m = re.search(r"PMC\d+", src[sid]["notes"])
        path = os.path.join(LIT, f"{m.group(0)}.txt") if m else None
        if not path or not os.path.exists(path):
            skipped += 1
            continue
        if path not in texts:
            texts[path] = open(path, encoding="utf-8").read().replace(",", ".")
        t = texts[path]
        for col in ("conversion_pct", "selectivity_C3H6_pct"):
            v = r[col]
            if not v:
                continue
            checked += 1
            if not any(re.search(r"(?<![\d.])" + re.escape(x) + r"(?![\d])", t) for x in variants(v)):
                missing += 1
                print(f"NOT FOUND  {r['measurement_id']} {col}={v}  ({m.group(0)})")
    print(f"\n{checked} values checked against paper text, {missing} not found, "
          f"{skipped} rows skipped (no downloaded full text)")


if __name__ == "__main__":
    main()
