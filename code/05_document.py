#!/usr/bin/env python3
"""05_document.py: write the README headline numbers from paper/stats.json.

Plain-language note: no number in the README is typed by hand. This script
reads the numbers the pipeline computed and writes them between the
headline markers, so the text and the data can never disagree.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = json.load(open(os.path.join(ROOT, "paper", "stats.json"), encoding="utf-8"))
e, d = s["equilibrium"], s.get("dataset", {})
text = (f"Equilibrium calculator: {e['qa_checks_passed']} of {e['qa_checks_total']} checks pass "
        f"(`data/processed/qa_equilibrium.txt`). Reaction enthalpy at 25 °C: {e['dH_rxn_298_kJ']} kJ/mol. "
        f"For pure propane at 1 bar the ceiling is {e['X_eq_pure_1bar']['550']}% at 550 °C, "
        f"{e['X_eq_pure_1bar']['600']}% at 600 °C and {e['X_eq_pure_1bar']['650']}% at 650 °C; "
        f"diluting to 10% propane raises the 600 °C ceiling to {e['X_eq_10pct_1bar']['600']}%.\n\n")
if d.get("n_measurements"):
    text += (f"Catalyst data: {d['n_measurements']} test points for {d['n_catalysts']} catalysts from "
             f"{d['n_sources']} papers ({d['n_sources_verified']} of {d['n_sources']} checked against the paper by the curator). "
             f"{d['n_above_eq_flags']} points sit above the equilibrium ceiling and are flagged.")
else:
    text += "Catalyst data: none extracted yet."
p = os.path.join(ROOT, "README.md")
r = open(p, encoding="utf-8").read()
r = re.sub(r"<!-- headline:start -->.*?<!-- headline:end -->",
           "<!-- headline:start -->\n" + text + "\n<!-- headline:end -->", r, flags=re.S)
open(p, "w", encoding="utf-8").write(r)
print(text)
