"""pdh_equilibrium.py: equilibrium limit for direct propane dehydrogenation (PDH).

Plain-language note: this is the "physics ceiling" calculator. Give it a
temperature, a pressure, and the feed mix (how much propane, hydrogen and inert
gas), and it returns the highest propane conversion thermodynamics allows for
the reaction  C3H8 <-> C3H6 + H2.  Other scripts import it; you never need to
edit it.

Basis and assumptions (also stated in docs/LIMITATIONS.md):
  * Single reaction C3H8 = C3H6 + H2. Cracking, oligomerisation and coke are not
    included, so this is the dehydrogenation-only limit, the standard reference in
    the PDH literature.
  * Ideal-gas mixture, standard state p0 = 1 bar (NASA convention).
  * Inert diluents (N2, Ar, He, steam treated as inert) only change partial pressures.
  * Thermodynamic data: NASA 7-term polynomials, McBride, Gordon & Reno,
    NASA TM-4513 (1993), read from data/raw/thermo_nasa7.csv.
Standard library only, so it runs anywhere.
"""
import csv
import math
import os

R = 8.314462618  # J/(mol K), CODATA 2018 exact
P0_BAR = 1.0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THERMO_CSV = os.path.join(ROOT, "data", "raw", "thermo_nasa7.csv")

_COEF = None


def _load():
    global _COEF
    if _COEF is None:
        _COEF = {}
        with open(THERMO_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                _COEF[r["species"]] = {
                    "tlo": float(r["T_low_K"]), "tmid": float(r["T_mid_K"]), "thi": float(r["T_high_K"]),
                    "low": [float(r[f"low_a{i}"]) for i in range(1, 8)],
                    "high": [float(r[f"high_a{i}"]) for i in range(1, 8)],
                }
    return _COEF


def _a(sp, T):
    c = _load()[sp]
    if not (c["tlo"] <= T <= c["thi"]):
        raise ValueError(f"T={T} K outside data range for {sp}")
    return c["low"] if T <= c["tmid"] else c["high"]


def cp_R(sp, T):
    a = _a(sp, T)
    return a[0] + a[1] * T + a[2] * T**2 + a[3] * T**3 + a[4] * T**4


def h_RT(sp, T):
    a = _a(sp, T)
    return a[0] + a[1] * T / 2 + a[2] * T**2 / 3 + a[3] * T**3 / 4 + a[4] * T**4 / 5 + a[5] / T


def s_R(sp, T):
    a = _a(sp, T)
    return a[0] * math.log(T) + a[1] * T + a[2] * T**2 / 2 + a[3] * T**3 / 3 + a[4] * T**4 / 4 + a[6]


def g_RT(sp, T):
    return h_RT(sp, T) - s_R(sp, T)


# Reaction C3H8 -> C3H6 + H2
NU = {"C3H8": -1, "C3H6": 1, "H2": 1}


def delta_h_kJ(T):
    """Standard reaction enthalpy, kJ/mol."""
    return sum(n * h_RT(s, T) for s, n in NU.items()) * R * T / 1000


def delta_g_kJ(T):
    """Standard reaction Gibbs energy, kJ/mol."""
    return sum(n * g_RT(s, T) for s, n in NU.items()) * R * T / 1000


def Kp(T):
    """Equilibrium constant (dimensionless, p0 = 1 bar)."""
    return math.exp(-sum(n * g_RT(s, T) for s, n in NU.items()))


def eq_conversion(T_C, P_bar=1.0, y_C3H8=1.0, y_H2=0.0, y_C3H6=0.0):
    """Equilibrium propane conversion (fraction, 0-1).

    T_C      temperature, degrees Celsius
    P_bar    total absolute pressure, bar
    y_*      inlet mole fractions; whatever is left (1 - sum) is inert diluent
    """
    if not (0 < y_C3H8 <= 1) or y_H2 < 0 or y_C3H6 < 0 or y_C3H8 + y_H2 + y_C3H6 > 1 + 1e-9:
        raise ValueError("invalid feed composition")
    if P_bar <= 0:
        raise ValueError("pressure must be positive")
    K = Kp(T_C + 273.15)
    a, b, c, p = y_C3H8, y_C3H6, y_H2, P_bar / P0_BAR

    # Basis: 1 mol inlet gas; extent xi. f(xi) is monotonic increasing in xi.
    def f(xi):
        return (b + xi) * (c + xi) * p - K * (a - xi) * (1 + xi)

    lo, hi = -min(b, c), a
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return ((lo + hi) / 2) / a


def approach_to_equilibrium(X_reported, X_eq):
    """Reported conversion as a fraction of the equilibrium limit (1.0 = at the limit)."""
    if X_eq is None or X_eq <= 0:
        return None
    return X_reported / X_eq
