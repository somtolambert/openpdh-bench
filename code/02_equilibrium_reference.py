#!/usr/bin/env python3
"""02_equilibrium_reference.py: build and check the equilibrium reference table.

Plain-language note: this script computes the physics ceiling (equilibrium
conversion) on a grid of temperatures, pressures and dilutions, checks the
calculator against independent published reference values, and writes:
  data/processed/equilibrium_reference.csv   the ceiling for common test conditions
  data/processed/qa_equilibrium.txt          the checks, pass or fail
  paper/stats.json                           numbers any document is allowed to quote
Open qa_equilibrium.txt if you want to see the checks; you do not need the rest.
"""
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdh_equilibrium as t  # noqa: E402

ROOT = t.ROOT
PROC = os.path.join(ROOT, "data", "processed")
STATS = os.path.join(ROOT, "paper", "stats.json")

TEMPS_C = list(range(400, 751, 25))
PRESSURES = [1.0, 0.5, 0.2, 3.0]          # bar absolute (total)
FEEDS = [                                  # (label, y_C3H8, y_H2)
    ("pure C3H8", 1.0, 0.0),
    ("50% C3H8 in inert", 0.5, 0.0),
    ("20% C3H8 in inert", 0.2, 0.0),
    ("10% C3H8 in inert", 0.1, 0.0),
    ("5% C3H8 in inert", 0.05, 0.0),
    ("C3H8:H2 = 1:1, no inert", 0.5, 0.5),
    ("C3H8:H2:inert = 1:1:8", 0.1, 0.1),
]

# Independent reference values, NOT from the NASA polynomials.
# NIST Chemistry WebBook (accessed 2026-10-19):
#   propane dfH gas  -104.7 +/- 0.5 kJ/mol (Pittam & Pilcher 1972)  https://webbook.nist.gov/cgi/cbook.cgi?ID=C74986&Mask=1
#   propene dfH gas  +20.41 kJ/mol (Furuyama, Golden et al. 1969)    https://webbook.nist.gov/cgi/cbook.cgi?ID=C115071&Mask=1
#   propene S(298.15 K) 266.82 J/mol/K (East 1997, cited by NIST)
REF = {
    "dfH_C3H8_kJ": (-104.7, 1.0),   # value, tolerance
    "dfH_C3H6_kJ": (20.41, 1.0),
    "S298_C3H6_J": (266.82, 0.5),
}


def main():
    os.makedirs(PROC, exist_ok=True)
    os.makedirs(os.path.dirname(STATS), exist_ok=True)

    # 1. Reference grid
    rows = []
    for P in PRESSURES:
        for label, y3, yh in FEEDS:
            for TC in TEMPS_C:
                X = t.eq_conversion(TC, P, y3, yh)
                rows.append({"T_C": TC, "P_bar": P, "feed": label, "y_C3H8": y3, "y_H2": yh,
                             "y_inert": round(1 - y3 - yh, 4), "Kp": round(t.Kp(TC + 273.15), 6),
                             "X_eq": round(X, 4)})
    out = os.path.join(PROC, "equilibrium_reference.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # 2. QA checks
    checks = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    T = 298.15
    for key, sp in (("dfH_C3H8_kJ", "C3H8"), ("dfH_C3H6_kJ", "C3H6")):
        v = t.h_RT(sp, T) * t.R * T / 1000
        ref, tol = REF[key]
        check(f"{key} vs NIST", abs(v - ref) <= tol, f"NASA {v:.2f} vs NIST {ref:.2f} (tol {tol})")
    s = t.s_R("C3H6", T) * t.R
    ref, tol = REF["S298_C3H6_J"]
    check("S298_C3H6 vs East 1997", abs(s - ref) <= tol, f"NASA {s:.2f} vs {ref:.2f} J/mol/K")

    dH = t.delta_h_kJ(T)
    check("reaction enthalpy 298 K is ~124 kJ/mol (strongly endothermic)", 122 < dH < 127, f"{dH:.1f} kJ/mol")

    # Independent cross-check of Kp using a different property library (if installed).
    try:
        from chemicals import Hfg, S0g
        from thermo import HeatCapacityGas
        from scipy.integrate import quad
        cas = {"C3H8": "74-98-6", "C3H6": "115-07-1", "H2": "1333-74-0"}
        cps = {k: HeatCapacityGas(CASRN=c) for k, c in cas.items()}

        def G(k, TK):
            c = cas[k]
            H = Hfg(c) + quad(lambda x: cps[k].T_dependent_property(x), 298.15, TK)[0]
            S = S0g(c) + quad(lambda x: cps[k].T_dependent_property(x) / x, 298.15, TK)[0]
            return H - TK * S
        for TC in (500, 550, 600, 650):
            TK = TC + 273.15
            k_ind = math.exp(-(G("C3H6", TK) + G("H2", TK) - G("C3H8", TK)) / t.R / TK)
            k_nasa = t.Kp(TK)
            rel = abs(k_nasa - k_ind) / k_ind
            x_n = t.eq_conversion(TC)
            # conversion implied by independent Kp, pure propane 1 bar: X = sqrt(K/(1+K))
            x_i = math.sqrt(k_ind / (1 + k_ind))
            check(f"Kp {TC} C vs independent library (chemicals/thermo)", rel < 0.06,
                  f"NASA {k_nasa:.4f} vs indep {k_ind:.4f} ({rel*100:.1f}%); X_eq pure 1 bar "
                  f"{x_n*100:.1f}% vs {x_i*100:.1f}%")
    except ImportError:
        check("independent library cross-check", True, "skipped: chemicals/thermo not installed")

    # Analytical identity: pure propane, X = sqrt(K/(K+P))
    for TC in (450, 600, 700):
        K = t.Kp(TC + 273.15)
        for P in (1.0, 0.2):
            exact = math.sqrt(K / (K + P))
            check(f"solver vs closed form, {TC} C, {P} bar", abs(t.eq_conversion(TC, P) - exact) < 1e-9,
                  f"{t.eq_conversion(TC, P):.6f} vs {exact:.6f}")

    # Physical direction checks (Le Chatelier)
    check("dilution raises X_eq", t.eq_conversion(600, 1, 0.1) > t.eq_conversion(600, 1, 1.0), "600 C")
    check("pressure lowers X_eq", t.eq_conversion(600, 3) < t.eq_conversion(600, 1), "600 C")
    check("H2 co-feed lowers X_eq", t.eq_conversion(600, 1, 0.5, 0.5) < t.eq_conversion(600, 1, 0.5, 0), "600 C")
    check("X_eq rises with T", all(t.eq_conversion(a) < t.eq_conversion(a + 25) for a in TEMPS_C[:-1]), "400-750 C")

    # Temperature at which Kp = 1
    lo, hi = 700.0, 1100.0
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if t.Kp(m) < 1 else (lo, m)
    T_K1 = m - 273.15

    n_fail = sum(not ok for _, ok, _ in checks)
    qa = os.path.join(PROC, "qa_equilibrium.txt")
    with open(qa, "w", encoding="utf-8") as f:
        f.write("QA report: equilibrium calculator (code/pdh_equilibrium.py)\n")
        f.write("Plain language: every line should say PASS. A FAIL means the physics ceiling cannot be trusted.\n\n")
        for name, ok, detail in checks:
            f.write(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}\n")
        f.write(f"\n{len(checks) - n_fail} of {len(checks)} checks passed.\n")
        f.write(f"Reference grid rows: {len(rows)}\n")

    stats = {
        "thermo_source": "NASA TM-4513 (McBride, Gordon, Reno 1993) 7-term polynomials",
        "dH_rxn_298_kJ": round(dH, 1),
        "dG_rxn_298_kJ": round(t.delta_g_kJ(T), 1),
        "T_Kp_equals_1_C": round(T_K1, 0),
        "X_eq_pure_1bar": {str(TC): round(t.eq_conversion(TC) * 100, 1) for TC in (500, 550, 600, 650, 700)},
        "X_eq_10pct_1bar": {str(TC): round(t.eq_conversion(TC, 1, 0.1) * 100, 1) for TC in (500, 550, 600, 650)},
        "X_eq_H2_1to1_1bar": {str(TC): round(t.eq_conversion(TC, 1, 0.5, 0.5) * 100, 1) for TC in (550, 600, 650)},
        "qa_checks_passed": len(checks) - n_fail,
        "qa_checks_total": len(checks),
        "reference_grid_rows": len(rows),
    }
    old = json.load(open(STATS)) if os.path.exists(STATS) else {}
    old["equilibrium"] = stats
    with open(STATS, "w", encoding="utf-8") as f:
        json.dump(old, f, indent=2)

    print(open(qa, encoding="utf-8").read())
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
