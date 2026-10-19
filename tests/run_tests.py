#!/usr/bin/env python3
"""Self-test: the QA script must catch every planted problem in tests/synthetic/.

Plain language: tests/synthetic/ holds INVENTED rows with deliberate mistakes.
They are not real papers and never enter the dataset. This test proves the
quality checks catch each mistake. Run: python tests/run_tests.py
"""
import csv, json, math, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import pdh_equilibrium as eq

r = subprocess.run([sys.executable, os.path.join(ROOT, "code", "03_build_and_qa.py"), "--extraction",
                    os.path.join(ROOT, "tests", "synthetic")], capture_output=True, text=True)
out = r.stdout
expect = ["does not look like a DOI", "not in catalysts.csv", "exceed 1", "exceeds equilibrium",
          "reported yield", "unreported temperature basis"]
fails = [e for e in expect if e not in out]
assert r.returncode == 1, "QA should exit 1 when errors exist"
rows = {x["measurement_id"]: x for x in csv.DictReader(open(os.path.join(ROOT, "data/processed/openpdh_measurements.csv")))}
kd = float(rows["T0001-C01-M01"]["kd_std_h-1"])
kd_hand = (math.log(0.7 / 0.3) - math.log(0.6 / 0.4)) / 9.5
if abs(kd - kd_hand) > 1e-4: fails.append(f"kd {kd} vs hand {kd_hand}")
if rows["T0001-C01-M03"]["kd_std_h-1"]: fails.append("kd leaked into an unlabelled point")
if abs(float(rows["T0001-C01-M01"]["X_eq_pct"]) - round(eq.eq_conversion(600, 1.01325, 0.1) * 100, 2)) > 1e-6:
    fails.append("X_eq mismatch")
if abs(float(rows["T0001-C01-M01"]["whsv_calc_h-1"]) - 5.9) > 0.01: fails.append("WHSV calc")
# restore real (empty) outputs so the fixture never lingers in data/processed
subprocess.run([sys.executable, os.path.join(ROOT, "code", "03_build_and_qa.py")], capture_output=True)
print("FAILED: " + "; ".join(fails) if fails else "all self-tests passed")
sys.exit(1 if fails else 0)
