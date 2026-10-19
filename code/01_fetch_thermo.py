#!/usr/bin/env python3
"""01_fetch_thermo.py: collect the open thermodynamic data the equilibrium calculator uses.

Plain-language note: this script copies the NASA reference numbers for propane,
propylene, hydrogen and a few light gases into one small table
(data/raw/thermo_nasa7.csv) and records exactly where they came from in
data/raw/PROVENANCE.txt. You do not need to open this file.

Original source (public domain, US government work):
  B.J. McBride, S. Gordon, M.A. Reno, "Coefficients for Calculating Thermodynamic
  and Transport Properties of Individual Species", NASA TM-4513, 1993.
  https://ntrs.nasa.gov/citations/19940013151
Distributed copy read here: nasa_gas.yaml shipped with the Cantera package
(BSD-3-Clause), converted by Cantera from the NASA file at
https://shepherd.caltech.edu/EDL/PublicResources/sdt/thermo.html

Coefficients are NASA 7-term polynomials (Cp/R, H/RT, S/R), two temperature ranges.
"""
import csv
import os
import subprocess
import sys

import yaml  # PyYAML
import cantera  # only used to locate the distributed data file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(RAW, "thermo_nasa7.csv")

# Cantera species name -> short name used in this project
SPECIES = {
    "C3H8": "C3H8",
    "C3H6,propylene": "C3H6",
    "H2": "H2",
    "CH4": "CH4",
    "C2H4": "C2H4",
    "C2H6": "C2H6",
}


def main():
    src = os.path.join(os.path.dirname(cantera.__file__), "data", "nasa_gas.yaml")
    with open(src, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    rows = []
    for sp in doc["species"]:
        if sp["name"] not in SPECIES:
            continue
        th = sp["thermo"]
        assert th["model"] == "NASA7", sp["name"]
        tlo, tmid, thi = th["temperature-ranges"]
        low, high = th["data"]
        rows.append([SPECIES[sp["name"]], sp["name"], tlo, tmid, thi, *low, *high, th.get("note", "")])
    missing = set(SPECIES.values()) - {r[0] for r in rows}
    if missing:
        sys.exit(f"missing species: {missing}")
    os.makedirs(RAW, exist_ok=True)
    header = (["species", "source_name", "T_low_K", "T_mid_K", "T_high_K"]
              + [f"low_a{i}" for i in range(1, 8)] + [f"high_a{i}" for i in range(1, 8)] + ["source_note"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {len(rows)} species to {os.path.relpath(OUT, ROOT)}")

    # Provenance: log both the distributed source file and the extracted table.
    prov = os.path.join(ROOT, "tools", "provenance.py")
    log = os.path.join(RAW, "PROVENANCE.txt")
    if not os.path.exists(log) or "nasa_gas.yaml" not in open(log, encoding="utf-8").read():
        note = (f"Cantera {cantera.__version__} distribution of NASA TM-4513 (McBride, Gordon, Reno 1993) "
                "polynomials; original https://ntrs.nasa.gov/citations/19940013151")
        subprocess.run([sys.executable, prov, src, "pip:cantera==" + cantera.__version__ + "/data/nasa_gas.yaml",
                        "--log", log, "--note", note], check=True)
        subprocess.run([sys.executable, prov, OUT, "derived from nasa_gas.yaml by code/01_fetch_thermo.py",
                        "--log", log, "--note", "species: " + ", ".join(SPECIES.values())], check=True)


if __name__ == "__main__":
    main()
