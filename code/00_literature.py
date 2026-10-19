#!/usr/bin/env python3
"""00_literature.py: find open-access papers and download their full text for extraction.

Plain-language note: this searches Europe PMC (a free archive of research papers),
logs the search in data/extraction/search_log.csv so it can be repeated, and
downloads the full text of selected open-access papers into
data/raw/literature/. Those full texts are for reading only; they are NOT
published with the benchmark (they belong to their authors and publishers).
Only their fingerprints (SHA-256) go into data/raw/PROVENANCE.txt.

It also writes a plain-text reading copy of each paper's tables and methods
(data/raw/literature/<PMCID>.txt) to make hand extraction faster.

Usage:
  python code/00_literature.py search
  python code/00_literature.py fetch PMC123 PMC456 ...
"""
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIT = os.path.join(ROOT, "data", "raw", "literature")
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
QUERY = '(TITLE:"propane dehydrogenation" OR ABSTRACT:"propane dehydrogenation") AND OPEN_ACCESS:y AND HAS_FT:y'


def get(url):
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read()


def search():
    url = API + "search?" + urllib.parse.urlencode({"query": QUERY, "format": "json", "pageSize": 1000,
                                                      "resultType": "core"})
    d = json.loads(get(url))
    rows = d["resultList"]["result"]
    os.makedirs(LIT, exist_ok=True)
    out = os.path.join(LIT, "europepmc_hits.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pmcid", "doi", "year", "journal", "title", "license"])
        for r in rows:
            w.writerow([r.get("pmcid"), (r.get("doi") or "").lower(), r.get("pubYear"),
                        (r.get("journalInfo") or {}).get("journal", {}).get("title", ""),
                        re.sub(r"<[^>]+>", "", r.get("title", "")), r.get("license", "")])
    log = os.path.join(ROOT, "data", "extraction", "search_log.csv")
    with open(log, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([datetime.date.today().isoformat(), "Europe PMC REST API", QUERY,
                                "open access with full text", d["hitCount"], "", "",
                                "hit list in data/raw/literature/europepmc_hits.csv (not published)"])
    print(f"{d['hitCount']} hits -> {os.path.relpath(out, ROOT)}")


def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def reading_copy(xml_bytes):
    """Tables (cell by cell) and body sections, as plain text."""
    root = ET.fromstring(xml_bytes)
    out = []
    title = root.find(".//article-title")
    out.append("TITLE: " + (text_of(title) if title is not None else ""))
    for sec in root.iter("sec"):
        t = sec.find("title")
        heading = text_of(t) if t is not None else ""
        paras = [text_of(p) for p in sec.findall("p")]
        if paras:
            out.append(f"\n## {heading}")
            out.extend(paras)
    for tw in root.iter("table-wrap"):
        lab = tw.find("label")
        cap = tw.find("caption")
        out.append(f"\n### TABLE {text_of(lab) if lab is not None else ''}: {text_of(cap) if cap is not None else ''}")
        for tr in tw.iter("tr"):
            out.append(" | ".join(text_of(c) for c in tr if c.tag in ("td", "th")))
        for fn in tw.iter("fn"):
            out.append("  note: " + text_of(fn))
    for fig in root.iter("fig"):
        lab = fig.find("label")
        cap = fig.find("caption")
        out.append(f"\n### FIGURE {text_of(lab) if lab is not None else ''}: {text_of(cap) if cap is not None else ''}")
    return "\n".join(out)


def fetch(pmcids):
    os.makedirs(LIT, exist_ok=True)
    prov = os.path.join(ROOT, "tools", "provenance.py")
    log = os.path.join(ROOT, "data", "raw", "PROVENANCE.txt")
    for p in pmcids:
        url = API + f"{p}/fullTextXML"
        dest = os.path.join(LIT, f"{p}.xml")
        try:
            data = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"{p}: download failed ({e})")
            continue
        with open(dest, "wb") as f:
            f.write(data)
        with open(os.path.join(LIT, f"{p}.txt"), "w", encoding="utf-8") as f:
            f.write(reading_copy(data))
        subprocess.run([sys.executable, prov, dest, url, "--log", log,
                        "--note", "full text for extraction only; not redistributed"], check=True,
                       stdout=subprocess.DEVNULL)
        print(f"{p}: {len(data)} bytes")


if __name__ == "__main__":
    if sys.argv[1:2] == ["search"]:
        search()
    elif sys.argv[1:2] == ["fetch"]:
        fetch(sys.argv[2:])
    else:
        sys.exit(__doc__)
