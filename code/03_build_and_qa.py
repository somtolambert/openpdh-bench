#!/usr/bin/env python3
"""03_build_and_qa.py: check the hand-extracted tables, add the comparison layer, write the release table.

Plain-language note: this reads the three spreadsheets in data/extraction/
(papers, catalysts, test results), checks every value against the rules in
code/schema.py, adds the equilibrium ceiling and the other computed columns,
and writes:
  data/processed/openpdh_measurements.csv   the release table (one row per test point)
  data/processed/qa_report.txt              every problem found, row by row
  docs/CODEBOOK.md                          regenerated from schema.py
  paper/stats.json                          counts any document may quote
Read qa_report.txt after every batch of new papers.

Usage: python code/03_build_and_qa.py [--extraction DIR]
"""
import csv
import datetime
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdh_equilibrium as eq  # noqa: E402
import schema  # noqa: E402

ROOT = eq.ROOT
ABOVE_EQ_TOL_PP = 2.0      # percentage points of tolerance before flagging conversion above the ceiling
YIELD_TOL_PP = 2.0         # reported yield vs conversion x selectivity
M_C3H8 = 44.097            # g/mol
V_M_STP = 22.414           # L/mol at 0 C, 1 atm


def parse(value, typ):
    v = (value or "").strip()
    if v == "":
        return None
    if typ == "float":
        return float(v)
    if typ == "int":
        return int(v)
    if typ == "bool":
        if v.upper() in ("TRUE", "1", "YES"):
            return True
        if v.upper() in ("FALSE", "0", "NO"):
            return False
        raise ValueError("expected TRUE or FALSE")
    if typ == "date":
        datetime.date.fromisoformat(v)
        return v
    return v


def load(path, cols, issues, table):
    rows = []
    if not os.path.exists(path):
        issues.append(("ERROR", table, "-", f"file missing: {os.path.relpath(path, ROOT)}"))
        return rows
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        expected = [c[0] for c in cols]
        if reader.fieldnames != expected:
            missing = set(expected) - set(reader.fieldnames or [])
            extra = set(reader.fieldnames or []) - set(expected)
            issues.append(("ERROR", table, "header", f"columns differ from schema; missing={sorted(missing)} extra={sorted(extra)}"))
        for i, raw in enumerate(reader, start=2):
            rid = raw.get(expected[0], f"line {i}")
            row = {}
            for name, typ, unit, req, _defn, allowed in cols:
                try:
                    val = parse(raw.get(name), "str" if typ == "enum" else typ)
                except ValueError as e:
                    issues.append(("ERROR", table, rid, f"{name}: cannot read '{raw.get(name)}' ({e})"))
                    val = None
                if val is None and req:
                    issues.append(("ERROR", table, rid, f"{name}: required but empty"))
                if val is not None and allowed is not None:
                    if typ == "enum" and val not in allowed:
                        issues.append(("ERROR", table, rid, f"{name}: '{val}' not one of {allowed}"))
                    if typ in ("float", "int") and not (allowed[0] <= val <= allowed[1]):
                        issues.append(("ERROR", table, rid, f"{name}: {val} outside plausible range {allowed}"))
                row[name] = val
            row["_line"] = i
            rows.append(row)
    return rows


def kd_std(x0, xf, hours):
    """Common first-order deactivation constant. x in percent."""
    if None in (x0, xf, hours) or hours <= 0:
        return None
    a, b = x0 / 100, xf / 100
    if not (0 < a < 1 and 0 < b < 1):
        return None
    return (math.log((1 - b) / b) - math.log((1 - a) / a)) / hours


def write_codebook():
    out = ["# Codebook", "",
           "*Plain language: this explains every column in the benchmark, its unit, and whether it is required. "
           "It is generated automatically from `code/schema.py`, so do not edit it by hand.*", ""]
    for table, cols in schema.TABLES.items():
        out += [f"## {table}.csv", "", "| Column | Type | Unit | Required | Definition | Allowed |", "|---|---|---|---|---|---|"]
        for name, typ, unit, req, defn, allowed in cols:
            if isinstance(allowed, list):
                al = ", ".join(f"`{a}`" for a in allowed if a)
            elif isinstance(allowed, tuple):
                al = f"{allowed[0]} to {allowed[1]}"
            else:
                al = ""
            out.append(f"| `{name}` | {typ} | {unit} | {'yes' if req else 'no'} | {defn} | {al} |")
        out.append("")
    out += ["## Computed columns (added by the pipeline, release table only)", "",
            "| Column | Type | Unit | Definition |", "|---|---|---|---|"]
    for name, typ, unit, defn in schema.DERIVED:
        out.append(f"| `{name}` | {typ} | {unit} | {defn} |")
    out += ["", "## Release table", "",
            "`data/processed/openpdh_measurements.csv` contains every measurements column, the catalyst "
            "columns `family`, `label_in_paper`, `active_elements`, `support`, the source columns `source_id`, "
            "`doi`, `first_author`, `year`, and the computed columns above.", ""]
    with open(os.path.join(ROOT, "docs", "CODEBOOK.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def main():
    ext = os.path.join(ROOT, "data", "extraction")
    if "--extraction" in sys.argv:
        ext = os.path.abspath(sys.argv[sys.argv.index("--extraction") + 1])
    issues = []
    src = load(os.path.join(ext, "sources.csv"), schema.SOURCES, issues, "sources")
    cat = load(os.path.join(ext, "catalysts.csv"), schema.CATALYSTS, issues, "catalysts")
    mea = load(os.path.join(ext, "measurements.csv"), schema.MEASUREMENTS, issues, "measurements")
    qeq = load(os.path.join(ext, "quoted_equilibria.csv"), schema.QUOTED_EQ, issues, "quoted_equilibria")

    # Uniqueness and links
    for table, rows, key in (("sources", src, "source_id"), ("catalysts", cat, "catalyst_id"),
                             ("measurements", mea, "measurement_id")):
        for k, n in Counter(r[key] for r in rows).items():
            if n > 1:
                issues.append(("ERROR", table, k, f"duplicate {key} ({n} rows)"))
    for k, n in Counter((r["doi"] or "").lower() for r in src).items():
        if k and n > 1:
            issues.append(("ERROR", "sources", k, "same DOI entered twice"))
    for r in src:
        if r["doi"] and not re.match(r"^10\.\d{4,9}/\S+$", r["doi"]):
            issues.append(("ERROR", "sources", r["source_id"], f"doi '{r['doi']}' does not look like a DOI"))
    S = {r["source_id"]: r for r in src}
    C = {r["catalyst_id"]: r for r in cat}
    for r in cat:
        if r["source_id"] not in S:
            issues.append(("ERROR", "catalysts", r["catalyst_id"], f"source_id {r['source_id']} not in sources.csv"))
        if r["active_elements"] and r["active_elements"] != "na":
            for part in r["active_elements"].split(";"):
                if not re.match(r"^[A-Z][a-z]?:(\d+(\.\d+)?|na)$", part.strip()):
                    issues.append(("ERROR", "catalysts", r["catalyst_id"], f"active_elements part '{part}' not 'El:wt%'"))
    for r in mea:
        if r["catalyst_id"] not in C:
            issues.append(("ERROR", "measurements", r["measurement_id"], f"catalyst_id {r['catalyst_id']} not in catalysts.csv"))

    # Equilibrium values quoted by papers vs this calculator
    qrows = []
    for q in qeq:
        if q["source_id"] not in S:
            issues.append(("ERROR", "quoted_equilibria", q["quote_id"], f"source_id {q['source_id']} not in sources.csv"))
        try:
            ours = eq.eq_conversion(q["temperature_C"], q["pressure_bar"], q["y_C3H8_in"], q["y_H2_in"]) * 100
        except (ValueError, TypeError):
            continue
        diff = q["X_eq_quoted_pct"] - ours
        qrows.append({**{k: q[k] for k, *_ in schema.QUOTED_EQ}, "X_eq_this_calc_pct": round(ours, 2),
                      "difference_pp": round(diff, 2)})
        if abs(diff) > 2:
            issues.append(("INFO", "quoted_equilibria", q["quote_id"],
                           f"paper quotes {q['X_eq_quoted_pct']}% but single-reaction equilibrium is {ours:.1f}% "
                           f"({q['temperature_C']} C, {q['pressure_bar']} bar, y_C3H8={q['y_C3H8_in']}, y_H2={q['y_H2_in']})"))

    # Derived columns and physics checks
    out_rows = []
    runs = defaultdict(list)
    for r in mea:
        rid = r["measurement_id"]
        y3, yh = r["y_C3H8_in"], r["y_H2_in"]
        if y3 is not None and yh is not None and y3 + yh + (r["y_C3H6_in"] or 0) > 1 + 1e-6:
            issues.append(("ERROR", "measurements", rid, "inlet mole fractions (C3H8 + H2 + C3H6) exceed 1"))
        if r["diluent"] == "none" and y3 is not None and yh is not None and abs(y3 + yh - 1) > 0.01:
            issues.append(("WARN", "measurements", rid, "diluent 'none' but propane + H2 fractions do not sum to 1"))
        d = {k: r[k] for k, *_ in schema.MEASUREMENTS}
        c = C.get(r["catalyst_id"], {})
        s = S.get(c.get("source_id"), {})
        for k in ("family", "label_in_paper", "active_elements", "support"):
            d[k] = c.get(k)
        for k in ("source_id", "doi", "first_author", "year"):
            d[k] = s.get(k)
        xeq = None
        try:
            if None not in (r["temperature_C"], r["pressure_bar"], y3, yh):
                xeq = eq.eq_conversion(r["temperature_C"], r["pressure_bar"], y3, yh, r["y_C3H6_in"] or 0.0) * 100
        except ValueError as e:
            issues.append(("ERROR", "measurements", rid, f"equilibrium not computable: {e}"))
        d["X_eq_pct"] = None if xeq is None else round(xeq, 2)
        X = r["conversion_pct"]
        d["approach_to_eq"] = round(X / xeq, 3) if (xeq and X is not None) else None
        d["above_eq_flag"] = bool(xeq is not None and X is not None and X > xeq + ABOVE_EQ_TOL_PP)
        if d["above_eq_flag"]:
            issues.append(("FLAG", "measurements", rid,
                           f"conversion {X:.1f}% exceeds equilibrium {xeq:.1f}% at {r['temperature_C']} C "
                           f"(basis: {r['temperature_basis']}, heating: {r['heating_mode']}"
                           + (f"; propylene yield {X * r['selectivity_C3H6_pct'] / 100:.1f}%"
                              if r['selectivity_C3H6_pct'] is not None else "") + ")"))
        sel = r["selectivity_C3H6_pct"]
        d["yield_C3H6_calc_pct"] = round(X * sel / 100, 2) if (X is not None and sel is not None) else None
        if r["yield_C3H6_pct"] is not None and d["yield_C3H6_calc_pct"] is not None:
            if abs(r["yield_C3H6_pct"] - d["yield_C3H6_calc_pct"]) > YIELD_TOL_PP:
                issues.append(("WARN", "measurements", rid,
                               f"reported yield {r['yield_C3H6_pct']} vs conversion x selectivity {d['yield_C3H6_calc_pct']}"))
        whsv = None
        if None not in (r["total_flow_mL_min"], y3, r["catalyst_mass_mg"]):
            g_per_h = r["total_flow_mL_min"] * y3 / 1000 / V_M_STP * M_C3H8 * 60
            whsv = g_per_h / (r["catalyst_mass_mg"] / 1000)
            if r["whsv_h-1"] is not None and abs(whsv - r["whsv_h-1"]) / r["whsv_h-1"] > 0.15:
                issues.append(("WARN", "measurements", rid,
                               f"stated WHSV {r['whsv_h-1']} vs computed {whsv:.2f} from flow and mass (>15% apart)"))
        d["whsv_calc_h-1"] = None if whsv is None else round(whsv, 3)
        if r["temperature_basis"] == "unreported" and r["heating_mode"] != "conventional":
            issues.append(("WARN", "measurements", rid, "electrified heating with unreported temperature basis"))
        d["kd_std_h-1"] = None
        out_rows.append(d)
        if r["run_label"]:
            runs[(r["catalyst_id"], r["run_label"], r["regeneration_cycle"])].append(d)

    # kd on a common definition, per run: first and last time-on-stream points
    n_kd = 0
    for pts in runs.values():
        pts = [p for p in pts if p["time_on_stream_h"] is not None and p["conversion_pct"] is not None]
        if len(pts) < 2:
            continue
        pts.sort(key=lambda p: p["time_on_stream_h"])
        k = kd_std(pts[0]["conversion_pct"], pts[-1]["conversion_pct"],
                   pts[-1]["time_on_stream_h"] - pts[0]["time_on_stream_h"])
        if k is not None:
            n_kd += 1
            for p in pts:
                p["kd_std_h-1"] = round(k, 5)
            rep = next((p["kd_reported_h-1"] for p in pts if p["kd_reported_h-1"] not in (None, 0)), None)
            if rep and k > 0 and not (1 / 3 < k / rep < 3):
                issues.append(("WARN", "measurements", pts[0]["measurement_id"],
                               f"reported kd {rep} h-1 vs {k:.4f} h-1 recomputed from the run's first and last points "
                               f"(ratio {k / rep:.0f}); check the paper's units and time basis"))

    # Write release table
    proc = os.path.join(ROOT, "data", "processed")
    os.makedirs(proc, exist_ok=True)
    order = (["source_id", "doi", "first_author", "year", "catalyst_id", "label_in_paper", "family",
              "active_elements", "support"]
             + [k for k, *_ in schema.MEASUREMENTS if k != "catalyst_id"]
             + [k for k, *_ in schema.DERIVED])
    with open(os.path.join(proc, "openpdh_measurements.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=order, extrasaction="ignore")
        w.writeheader()
        for d in out_rows:
            w.writerow({k: ("" if d.get(k) is None else ("TRUE" if d.get(k) is True else
                                                         "FALSE" if d.get(k) is False else d.get(k))) for k in order})

    if qrows:
        with open(os.path.join(proc, "quoted_equilibrium_check.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(qrows[0]))
            w.writeheader()
            for q in qrows:
                w.writerow({k: ("TRUE" if v is True else "FALSE" if v is False else "" if v is None else v) for k, v in q.items()})

    counts = Counter(level for level, *_ in issues)
    stats = {
        "n_sources": len(src), "n_catalysts": len(cat), "n_measurements": len(mea),
        "n_errors": counts["ERROR"], "n_warnings": counts["WARN"], "n_above_eq_flags": counts["FLAG"],
        "n_runs_with_kd_std": n_kd,
        "by_heating_mode": dict(Counter(r["heating_mode"] for r in mea)),
        "by_family": dict(Counter(C[r["catalyst_id"]]["family"] for r in mea if r["catalyst_id"] in C)),
        "n_sources_verified": sum(1 for r in src if r["verified_by"]),
        "n_quoted_equilibria": len(qrows),
        "n_quoted_equilibria_off_by_more_than_2pp": counts["INFO"],
    }
    with open(os.path.join(proc, "qa_report.txt"), "w", encoding="utf-8") as f:
        f.write("QA report: extracted catalyst data\n")
        f.write("Plain language: ERROR must be fixed before release. WARN needs a look. "
                "FLAG means a result sits above the physics ceiling; check the paper. "
                "INFO means a paper quotes an equilibrium value that differs from the single-reaction ceiling.\n\n")
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
        f.write("\n")
        for level, table, rid, msg in sorted(issues, key=lambda x: ("ERROR", "FLAG", "WARN", "INFO").index(x[0])):
            f.write(f"{level:5s} {table}/{rid}: {msg}\n")
        if not issues:
            f.write("No issues found.\n")

    sp = os.path.join(ROOT, "paper", "stats.json")
    allstats = json.load(open(sp)) if os.path.exists(sp) else {}
    allstats["dataset"] = stats
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(allstats, f, indent=2)
    write_codebook()
    print(open(os.path.join(proc, "qa_report.txt"), encoding="utf-8").read())
    sys.exit(1 if counts["ERROR"] else 0)


if __name__ == "__main__":
    main()
