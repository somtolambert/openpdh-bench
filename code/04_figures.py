#!/usr/bin/env python3
"""04_figures.py: figures for the benchmark.

Plain-language note: draws the charts. Figure 1 shows the physics ceiling
(equilibrium conversion) against temperature for three common test conditions.
Later versions add the catalyst results on top. Every figure carries a DRAFT
stamp until you approve the release; run with --final only after that.

Usage: python code/04_figures.py [--final]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdh_equilibrium as t  # noqa: E402

FINAL = "--final" in sys.argv
OUT = os.path.join(t.ROOT, "paper", "figures")

# Categorical slots 1-3 of the validated reference palette (dataviz skill).
# Legend order matches top-to-bottom curve order.
SERIES = [
    ("10% propane in inert gas", dict(y_C3H8=0.1), "#2a78d6"),
    ("Pure propane", dict(y_C3H8=1.0), "#eb6834"),
    ("Propane:H$_2$ = 1:1, no inert", dict(y_C3H8=0.5, y_H2=0.5), "#1baf7a"),
]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def fig_equilibrium():
    temps = [400 + i for i in range(0, 351, 5)]
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for label, feed, color in SERIES:
        xs = [t.eq_conversion(T, 1.0, **feed) * 100 for T in temps]
        ax.plot(temps, xs, color=color, lw=2, solid_capstyle="round", zorder=3, label=label)
    # Annotate the single most-quoted value: pure propane, 600 C
    x600 = t.eq_conversion(600) * 100
    ax.plot([600], [x600], "o", ms=5, color="#eb6834", mec="#fcfcfb", mew=1.5, zorder=5)
    ax.annotate(f"{x600:.0f}% at 600 °C", (600, x600), xytext=(-14, 14), textcoords="offset points",
                ha="right", fontsize=8.5, color=INK2,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK, handlelength=1.6)
    ax.set_xlim(400, 750)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Temperature (°C)", color=INK2, fontsize=9)
    ax.set_ylabel("Equilibrium propane conversion (%)", color=INK2, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5)
    ax.set_title("The equilibrium ceiling for propane dehydrogenation at 1 bar",
                 loc="left", fontsize=10.5, color=INK, pad=10)
    fig.text(0.01, 0.01, "Reaction C$_3$H$_8$ = C$_3$H$_6$ + H$_2$ only, ideal gas, total pressure 1 bar. "
             "Thermodynamic data: NASA TM-4513 (1993).", fontsize=7, color=INK2)
    if not FINAL:
        ax.text(0.5, 0.5, "DRAFT", transform=ax.transAxes, fontsize=60, color="#e9e8e4",
                ha="center", va="center", rotation=25, zorder=0)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=0.17)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "fig1_equilibrium_ceiling.png")
    fig.savefig(p, facecolor=fig.get_facecolor())
    print("wrote", os.path.relpath(p, t.ROOT))


def fig_parity():
    """Figure 2: each reported conversion against its own equilibrium ceiling."""
    import csv
    rows = list(csv.DictReader(open(os.path.join(t.ROOT, "data", "processed", "openpdh_measurements.csv"), encoding="utf-8")))
    rows = [r for r in rows if r["X_eq_pct"] and r["conversion_pct"]
            and float(r["time_on_stream_h"]) <= 0.5]          # initial activity only
    groups = [("Pt-Sn", lambda r: r["family"] == "Pt-Sn", "#2a78d6"),
              ("Other Pt-based", lambda r: r["family"].startswith("Pt") and r["family"] != "Pt-Sn", "#eb6834"),
              ("Pt-free", lambda r: not r["family"].startswith("Pt"), "#1baf7a")]
    fig, ax = plt.subplots(figsize=(6.4, 5.0), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    ax.plot([0, 100], [0, 100], color=INK2, lw=1, ls="--", zorder=1)
    ax.annotate("conversion = equilibrium ceiling", (70, 73), rotation=45, fontsize=7.5, color=INK2, ha="center")
    for label, f, color in groups:
        g = [r for r in rows if f(r)]
        conv = [r for r in g if r["heating_mode"] == "conventional"]
        elec = [r for r in g if r["heating_mode"] != "conventional"]
        ax.scatter([float(r["X_eq_pct"]) for r in conv], [float(r["conversion_pct"]) for r in conv], s=22, color=color,
                   edgecolor="#fcfcfb", linewidth=0.8, zorder=3, label=f"{label} ({len(g)})")
        if elec:
            ax.scatter([float(r["X_eq_pct"]) for r in elec], [float(r["conversion_pct"]) for r in elec], s=46, marker="D",
                       facecolor="none", edgecolor=color, linewidth=1.4, zorder=4)
    ax.scatter([], [], s=46, marker="D", facecolor="none", edgecolor=INK2, linewidth=1.4, label="Electrified heating (RF, induction)")
    flagged = [r for r in rows if r["above_eq_flag"] == "TRUE"]
    if flagged:
        r0 = max(flagged, key=lambda r: float(r["conversion_pct"]) - float(r["X_eq_pct"]))
        ax.annotate(f"{len(flagged)} results above the ceiling\n(flagged for checking)", (float(r0["X_eq_pct"]), float(r0["conversion_pct"])),
                    xytext=(-80, 18), textcoords="offset points", fontsize=7.5, color=INK2,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.set_xlabel("Equilibrium ceiling at the reported conditions (%)", color=INK2, fontsize=9)
    ax.set_ylabel("Reported initial propane conversion (%)", color=INK2, fontsize=9)
    ax.grid(color=GRID, lw=0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5)
    ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor=INK)
    ax.set_title("How close each catalyst came to its own ceiling", loc="left", fontsize=10.5, color=INK, pad=10)
    n_src = len({r["source_id"] for r in rows})
    fig.text(0.01, 0.01, f"{len(rows)} initial-activity results from {n_src} papers (time on stream 0.5 h or less). "
             "Ceiling: C$_3$H$_8$ = C$_3$H$_6$ + H$_2$, ideal gas, NASA TM-4513 data.", fontsize=6.5, color=INK2)
    if not FINAL:
        ax.text(0.5, 0.5, "DRAFT", transform=ax.transAxes, fontsize=60, color="#e9e8e4",
                ha="center", va="center", rotation=25, zorder=0)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.12)
    p = os.path.join(OUT, "fig2_approach_to_equilibrium.png")
    fig.savefig(p, facecolor=fig.get_facecolor())
    print("wrote", os.path.relpath(p, t.ROOT))


if __name__ == "__main__":
    fig_equilibrium()
    fig_parity()
