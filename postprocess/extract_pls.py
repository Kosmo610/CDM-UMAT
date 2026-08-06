"""Proportional limit stress from a stress-strain curve.

WHY (a1-0012, 2026-08-06)
-------------------------
We were going to validate the TRS treatment against the composite modulus.
refs/[15] -- the same paper we cite for the XRD residual stress -- says
plainly:

    "TRSs do not affect the composite moduli, unless matrix cracking has
     occurred."

So the modulus is, by our own source, blind to the quantity we want to see.
The proportional limit is not: it is set by when matrix cracking starts,
which is exactly what a residual tension in the matrix moves.  refs/[10]
Table 1 measures both on one material at four temperatures, and the
sensitivity is not close:

    300 -> 1273 K     PLS +167 %     E +34 %      4.9x
    300 -> 1473 K     PLS +233 %     E +31 %      7.4x

PLS is a COMPOSITE measurement, so under the card rule in CLAUDE.md it can
never be a card input.  It is a validation target only.  This file extracts
it; it does not calibrate to it.

SCOPE, NARROWED TWICE (2026-08-06)
----------------------------------
a1-0018: for CYCLE damage the modulus is the first-rank metric, not PLS --
refs/[03] measured both on one specimen (modulus 45 % vs strength 63 %
after 60 cycles) and says so.  PLS belongs to TRS relaxation only.
And there, only as a COMPARATOR between TRS treatments: the definition
spread on our curve exceeds Yang's whole temperature effect (section 4 of
the selftest), so an absolute PLS-vs-Yang verdict would be decided by the
threshold, not the physics.

THE LINEAR FRACTION (a1-0015's proposal, implemented here)
----------------------------------------------------------
A target that survives the threshold problem better: divide the PLS by the
initial modulus to get the proportional-limit STRAIN, then by the failure
strain --

    linear fraction = (PLS / E0) / eps_fail

Two things cancel.  Any CONVENTION error in the stress scale (tangent vs
secant, machine compliance) multiplies PLS and E0 alike and drops out
exactly -- the selftest proves invariance under a pure stress rescale.
What remains is the threshold choice inside PLS itself, which is why the
fraction is reported per definition, like PLS.  On Yang's own numbers the
fraction rises monotonically 4.2 % -> 23.7 % from 300 to 1473 K while his
modulus KINKS at 1273 K -- it is the cleanest dimensionless signature of
TRS relaxation the dataset offers, and refs/[30] (same group as Zhang [5])
prints a 51.47 % model error on the absolute matrix-cracking stress while
holding modulus and strength to 5 %, which is the same lesson from the
other side.

WHY THREE DEFINITIONS AND NOT ONE
---------------------------------
"Where the curve stops being straight" is not a measurement until someone
fixes a threshold, and different thresholds give different answers on the
same curve.  Quoting one number would hide that.  This file reports three
independent definitions and their spread, so a comparison between TRS
treatments can be checked against the spread it has to beat:

    offset     the curve meets sigma = E0*(eps - delta),  delta = 0.005 %
    tangent    the smoothed tangent first falls to f*E0,  f = 0.95, 0.90
    deviation  (E0*eps - sigma)/(E0*eps) first exceeds 2 %

E0 ITSELF IS A TRAP HERE
------------------------
The first solver increment of M5 reports 466 GPa across a strain step of
2.3e-6 -- an artefact of one tiny increment, not a modulus.  Taking the
first slope as E0 would inflate every PLS below.  E0 is instead the
least-squares slope over the longest initial window that still fits a
straight line to R^2 >= R2_MIN, and the window is printed so the choice is
visible rather than implied.

    python3 postprocess/extract_pls.py <curve.csv> [more.csv ...]
    python3 postprocess/extract_pls.py --selftest
"""
from __future__ import print_function

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: refs/[10] Yang, J. Eur. Ceram. Soc. 37 (2017) 1281-1290, Table 1.
#: One material, one test series, four temperatures -- which is what makes
#: it a slope rather than a comparison of two papers.  CVI, not our PIP, so
#: the LEVEL does not transfer; the trend does.
YANG_TABLE1 = (
    # T (K), PLS (MPa), E (GPa), UTS (MPa), failure strain (%)
    (300.0, 30.0, 128.7, 225.8, 0.55),
    (973.0, 50.0, 152.3, 240.5, 0.24),
    (1273.0, 80.0, 172.7, 268.2, 0.32),
    (1473.0, 100.0, 169.1, 240.9, 0.25),
)

#: Straightness the initial window must keep to count as the elastic branch.
R2_MIN = 0.99995
#: Never trust fewer than this many points.
MIN_WINDOW = 6
#: LOADED points to drop before fitting -- the origin is dropped anyway.
#: M5's first loaded point sits at 1.086 MPa over a strain step of 2.3e-6,
#: a slope of 466 GPa.  No combination of our constituents can reach that
#: (the stiffest phase is the matrix at 332 GPa), so it is the solver's
#: first-increment elastic prediction, not a modulus.  One point.
SKIP_LOADED = 1

OFFSET_STRAIN = 5.0e-5          # 0.005 %
TANGENT_FRACTIONS = (0.95, 0.90)
DEVIATION_TOL = 0.02


# ==================================================================== load
def load_curve(path):
    """(strain, stress) pairs from a *_ss.csv, strain increasing, from 0."""
    eps, sig = [], []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            keys = {k.lower(): k for k in row}
            ek = next((keys[k] for k in keys if k.startswith("eps")), None)
            sk = next((keys[k] for k in keys if k.startswith("sigma")), None)
            if ek is None or sk is None:
                raise ValueError("%s: need eps* and sigma* columns" % path)
            eps.append(float(row[ek]))
            sig.append(float(row[sk]))
    pts = sorted(zip(eps, sig))
    return [(e, s) for e, s in pts if e >= 0.0]


# ================================================================== slopes
def _fit(pts):
    """Least-squares slope AND intercept, with R^2.

    The intercept is free on purpose.  Forcing the line through the origin
    looks tidier but it is wrong here: the discarded first increment leaves
    the curve carrying about +0.5 MPa that no later point removes, and a
    through-origin fit answers that by tilting -- it reported 273 GPa for
    M5, above the stiffest phase in the material.  A free intercept puts
    the offset where it belongs and returns the slope.
    """
    n = float(len(pts))
    if n < 2:
        return 0.0, 0.0, 0.0
    mx = sum(e for e, _ in pts) / n
    my = sum(s for _, s in pts) / n
    sxx = sum((e - mx) ** 2 for e, _ in pts)
    sxy = sum((e - mx) * (s - my) for e, s in pts)
    if sxx <= 0.0:
        return 0.0, 0.0, 0.0
    k = sxy / sxx
    b = my - k * mx
    ss_res = sum((s - (b + k * e)) ** 2 for e, s in pts)
    ss_tot = sum((s - my) ** 2 for _, s in pts)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0
    return k, b, r2


def initial_modulus(pts, r2_min=R2_MIN):
    """E0, the elastic-line intercept, and the window they came from."""
    body = [p for p in pts if p[0] > 0.0][SKIP_LOADED:]
    best, straight = None, True
    for n in range(MIN_WINDOW, len(body) + 1):
        k, b, r2 = _fit(body[:n])
        if r2 >= r2_min:
            best = (k, b, n, r2)
        else:
            break
    if best is None:
        # Not a fallback to be quiet about: it means the curve is already
        # bending inside the shortest window we are willing to fit, so
        # there is no proportional branch to take a limit off.
        k, b, r2 = _fit(body[:MIN_WINDOW])
        best, straight = (k, b, MIN_WINDOW, r2), False
    k, b, n, r2 = best
    return k, b, dict(n=n, r2=r2, eps_hi=body[n - 1][0],
                      sig_hi=body[n - 1][1], intercept=b, straight=straight)


def tangents(pts, half=2):
    """Centred finite-difference tangent, one per interior point."""
    out = []
    for i in range(len(pts)):
        a = max(0, i - half)
        b = min(len(pts) - 1, i + half)
        de = pts[b][0] - pts[a][0]
        out.append((pts[i][0], pts[i][1],
                    (pts[b][1] - pts[a][1]) / de if de > 0 else float("nan")))
    return out


def _cross(pts, f):
    """First point where f(eps, sig) turns non-negative, linearly bracketed."""
    prev = None
    for e, s in pts:
        v = f(e, s)
        if prev is not None and prev[1] < 0.0 <= v:
            pe, pv = prev
            w = -pv / (v - pv) if (v - pv) != 0.0 else 0.0
            eps = pe[0] + w * (e - pe[0])
            sig = pe[1] + w * (s - pe[1])
            return eps, sig
        prev = ((e, s), v)
    return None


# =================================================================== rules
def pls_offset(pts, e0, b, delta=OFFSET_STRAIN):
    """Where the curve meets the elastic line shifted by delta strain."""
    hit = _cross(pts, lambda e, s: b + e0 * (e - delta) - s)
    return None if hit is None else hit[1]


def pls_tangent(pts, e0, frac):
    """Where the smoothed tangent first falls to frac*E0."""
    tan = tangents(pts)
    target = frac * e0
    prev = None
    for e, s, t in tan:
        if t != t:
            continue
        if prev is not None and prev[2] >= target > t:
            w = (prev[2] - target) / (prev[2] - t)
            return prev[1] + w * (s - prev[1])
        prev = (e, s, t)
    return None


def pls_deviation(pts, e0, b, tol=DEVIATION_TOL):
    """Where the curve falls tol below the elastic line, in relative terms."""
    def f(e, s):
        el = b + e0 * e
        if el <= 0.0:
            return -1.0
        return (el - s) / el - tol
    hit = _cross(pts, f)
    return None if hit is None else hit[1]


def analyse(pts):
    e0, b, win = initial_modulus(pts)
    out = dict(e0=e0, b=b, window=win, n=len(pts),
               eps_max=pts[-1][0], sig_max=max(s for _, s in pts))
    vals = {}
    vals["offset 0.005 %"] = pls_offset(pts, e0, b)
    for f in TANGENT_FRACTIONS:
        vals["tangent %d %%" % round(100 * f)] = pls_tangent(pts, e0, f)
    vals["deviation 2 %"] = pls_deviation(pts, e0, b, DEVIATION_TOL)
    out["pls"] = vals
    out["linfrac"] = dict(
        (k, linear_fraction(v, e0, out["eps_max"]))
        for k, v in vals.items())
    got = [v for v in vals.values() if v is not None]
    out["spread"] = (min(got), max(got)) if got else None
    return out


# ================================================================== report
_PASS = [0]
_FAIL = [0]


def ck(name, cond, detail=""):
    ok = bool(cond)
    _PASS[0] += ok
    _FAIL[0] += not ok
    print("   [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                            ("   " + detail) if detail else ""))
    return ok


def show(path, res):
    print("\n  %s" % os.path.basename(path))
    w = res["window"]
    print("     %d points, eps to %.4f %%, sigma to %.2f MPa"
          % (res["n"], 100 * res["eps_max"], res["sig_max"]))
    print("     E0 = %.1f GPa  from %d points up to eps %.4f %% "
          "(sigma %.2f MPa), R^2 %.6f"
          % (res["e0"] / 1e3, w["n"], 100 * w["eps_hi"], w["sig_hi"], w["r2"]))
    print("     elastic line intercept %+.3f MPa  (the discarded first"
          " increment)" % res["b"])
    if not w["straight"]:
        print("     !! NO straight branch: R^2 %.6f is under %.5f even over"
              % (w["r2"], R2_MIN))
        print("        the shortest window allowed (%d points).  The curve is"
              % MIN_WINDOW)
        print("        already bending there, so E0 above is a shortest-window")
        print("        slope and the numbers below are threshold choices, not")
        print("        a limit the curve actually has.")
    for k in sorted(res["pls"]):
        v = res["pls"][k]
        lf = res["linfrac"].get(k)
        print("     PLS  %-16s %s%s"
              % (k, "%8.2f MPa" % v if v is not None else "   not reached",
                 "   lin.frac %5.1f %%" % (100.0 * lf)
                 if lf is not None else ""))
    if res["spread"]:
        lo, hi = res["spread"]
        print("     spread %.2f .. %.2f MPa  (%.0f %% of the low value)"
              % (lo, hi, 100.0 * (hi - lo) / lo if lo > 0 else float("nan")))


def linear_fraction(pls, e0, eps_fail):
    """(PLS/E0)/eps_fail -- dimensionless, stress-rescale invariant."""
    if pls is None or e0 <= 0.0 or eps_fail <= 0.0:
        return None
    return (pls / e0) / eps_fail


def yang_table():
    print("\n  refs/[10] Table 1 -- what the model has to be compared with")
    print("     %8s %8s %8s %8s %10s" % ("T (K)", "PLS", "E (GPa)", "UTS",
                                         "lin.frac"))
    for t, pls, e, uts, ef in YANG_TABLE1:
        lf = linear_fraction(pls, e * 1e3, ef / 100.0)
        print("     %8.0f %8.0f %8.1f %8.1f %9.1f %%"
              % (t, pls, e, uts, 100.0 * lf))
    p0, e0 = YANG_TABLE1[0][1], YANG_TABLE1[0][2]
    for t, pls, e, _, _ in YANG_TABLE1[1:]:
        dp = 100.0 * (pls / p0 - 1.0)
        de = 100.0 * (e / e0 - 1.0)
        print("     300 -> %-6.0f K   PLS %+6.1f %%   E %+6.1f %%   ratio %.1fx"
              % (t, dp, de, abs(dp / de) if de else float("nan")))


def main(argv):
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        d = os.path.join(ROOT, "data", "properties", "M5_c26k_T1000_ss.csv")
        if os.path.exists(d):
            paths = [d]
        else:
            print(__doc__)
            return 2
    print("=" * 74)
    print("extract_pls.py  --  proportional limit, three ways")
    print("=" * 74)
    yang_table()
    for p in paths:
        show(p, analyse(load_curve(p)))
    print("")
    return 0


# ================================================================ selftest
def selftest():
    print("=" * 74)
    print("extract_pls.py --selftest")
    print("=" * 74)

    print("\n 1. a curve whose PLS is known by construction")
    # bilinear: E0 = 200 GPa to 100 MPa, then 50 GPa.  Every definition
    # must land on 100 MPa, because the knee is exact.
    e0, e1, knee = 200.0e3, 50.0e3, 100.0
    ek = knee / e0
    pts = [(ek * i / 60.0, e0 * ek * i / 60.0) for i in range(61)]
    pts += [(ek + 3 * ek * i / 60.0, knee + e1 * 3 * ek * i / 60.0)
            for i in range(1, 61)]
    res = analyse(pts)
    ck("E0 is recovered to 0.1 %", abs(res["e0"] / e0 - 1.0) < 1e-3,
       "%.1f GPa" % (res["e0"] / 1e3))
    ck("the straight window stops at the knee, not past it",
       abs(res["window"]["sig_hi"] - knee) < 0.05 * knee,
       "%.2f MPa" % res["window"]["sig_hi"])
    for k, v in sorted(res["pls"].items()):
        ck("%s finds the knee within 25 %%" % k,
           v is not None and abs(v - knee) < 0.25 * knee,
           "%.2f MPa" % v if v is not None else "none")

    print("\n 2. a purely linear curve has no proportional limit to find")
    lin = [(1e-5 * i, 200.0e3 * 1e-5 * i) for i in range(200)]
    r = analyse(lin)
    ck("E0 is exact on a straight line", abs(r["e0"] - 200.0e3) < 1e-6,
       "%.3f GPa" % (r["e0"] / 1e3))
    ck("the tangent rules report nothing rather than a number",
       all(r["pls"]["tangent %d %%" % round(100 * f)] is None
           for f in TANGENT_FRACTIONS))
    ck("the deviation rule reports nothing too",
       r["pls"]["deviation 2 %"] is None)
    ck("the offset rule reports nothing either -- the offset line is",
       r["pls"]["offset 0.005 %"] is None)
    print("      parallel to a straight curve, so it never catches it.  A")
    print("      rule that invented a number here would invent one anywhere.")

    print("\n 3. the first-increment artefact must not become E0")
    # M5's real shape: a spurious stiff first step, then a clean 200 GPa
    # branch that carries the offset that step left behind.
    spike = [(0.0, 0.0), (2.3e-6, 1.086)] + \
            [(2.3e-6 + 1e-5 * i, 1.086 + 200.0e3 * 1e-5 * i)
             for i in range(1, 120)]
    r = analyse(spike)
    ck("a 466 GPa first step does not set E0",
       abs(r["e0"] / 200.0e3 - 1.0) < 1e-6, "%.1f GPa" % (r["e0"] / 1e3))
    # the branch is sigma = 1.086 + 200e3*(eps - 2.3e-6), so its intercept
    # at eps = 0 is 1.086 - 200e3*2.3e-6 = 0.626
    ck("the offset it left is reported, not absorbed into the slope",
       abs(r["b"] - 0.626) < 1e-3, "%+.3f MPa" % r["b"])
    ck("dropping the origin alone would not have been enough",
       SKIP_LOADED >= 1)
    # The bias from forcing the line through the origin shrinks as the
    # window lengthens, so it has to be measured on a SHORT window -- which
    # is the case that matters, because a short window is all a bending
    # curve like M5 ever offers.
    loaded = [p for p in spike if p[0] > 0.0][SKIP_LOADED:]
    for n, floor in ((MIN_WINDOW, 1.02), (len(loaded), 1.0)):
        win = loaded[:n]
        k_org = sum(e * s for e, s in win) / sum(e * e for e, _ in win)
        ck("through-origin over %3d points overstates E0" % n,
           k_org > 200.0e3 * floor,
           "%.1f GPa, %+.1f %% high" % (k_org / 1e3,
                                        100 * (k_org / 200.0e3 - 1.0)))

    print("\n 4. the real M5 curve")
    m5 = os.path.join(ROOT, "data", "properties", "M5_c26k_T1000_ss.csv")
    if os.path.exists(m5):
        pts = load_curve(m5)
        r = analyse(pts)
        ck("the committed curve loads", len(pts) > 300, "%d points" % len(pts))
        ck("E0 is a plausible composite modulus, not the 466 GPa spike",
           200.0e3 < r["e0"] < 300.0e3, "%.1f GPa" % (r["e0"] / 1e3))
        ck("every definition returns a value on this curve",
           all(v is not None for v in r["pls"].values()))
        ck("M5 has NO straight branch at all", not r["window"]["straight"],
           "R^2 %.6f over the shortest window" % r["window"]["r2"])
        ck("E0 agrees with m6_calibration.py's 235.2 GPa to within 5 %",
           abs(r["e0"] / 235.2e3 - 1.0) < 0.05,
           "%.1f vs 235.2 GPa -- a definition gap, not a disagreement"
           % (r["e0"] / 1e3))
        ck("softening has begun by 2 MPa (tangent already off 5 %)",
           r["pls"]["tangent 95 %"] < 5.0,
           "%.2f MPa" % r["pls"]["tangent 95 %"])
        yang_lo = min(t[1] for t in YANG_TABLE1)
        yang_hi = max(t[1] for t in YANG_TABLE1)
        span = r["spread"][1] - r["spread"][0]
        ck("the definition spread is wider than Yang's whole PLS range",
           span > yang_hi - yang_lo,
           "%.0f MPa spread vs %.0f MPa across 300-1473 K"
           % (span, yang_hi - yang_lo))
        print("      -> so PLS cannot be quoted against Yang as an absolute")
        print("         number: the threshold would decide the verdict.")
        print("         It CAN compare TRS treatments to each other, where")
        print("         one fixed threshold cancels.  That is the scope")
        print("         a1-0012 gets: relative comparator, not target.")
    else:
        ck("M5 curve committed", False, m5)

    print("\n 5. the linear fraction (a1-0015)")
    # Yang's own published columns, computed the same way we compute ours.
    lf = [100.0 * linear_fraction(pls, e * 1e3, ef / 100.0)
          for _, pls, e, _, ef in YANG_TABLE1]
    ck("Yang 300 K linear fraction is 4.2 %", abs(lf[0] - 4.24) < 0.05,
       "%.2f %%" % lf[0])
    ck("Yang 1473 K linear fraction is 23.7 %", abs(lf[3] - 23.65) < 0.1,
       "%.2f %%" % lf[3])
    ck("the fraction rises monotonically with T, unlike E which kinks",
       all(b > a for a, b in zip(lf, lf[1:])),
       " -> ".join("%.1f" % v for v in lf))
    # The invariance that makes it worth having: rescale every stress by a
    # constant (a convention error, a compliance error) and the fraction
    # must not move, because PLS and E0 scale together.
    if os.path.exists(m5):
        pts = load_curve(m5)
        r1 = analyse(pts)
        r2x = analyse([(e, 0.61 * s) for e, s in pts])
        pairs = [(r1["linfrac"][k], r2x["linfrac"][k])
                 for k in r1["linfrac"] if r1["linfrac"][k] is not None]
        worst = max(abs(a / b - 1.0) for a, b in pairs if b)
        ck("a pure stress rescale (x0.61) leaves every fraction unchanged",
           worst < 1e-9, "worst drift %.2e" % worst)
        ck("M5's fractions land below Yang's 1273 K value of 14.5 %",
           all(100.0 * v < 14.5 for v in r1["linfrac"].values()
               if v is not None),
           ", ".join("%.1f" % (100 * v)
                     for v in sorted(vv for vv in r1["linfrac"].values()
                                     if vv is not None)))
        print("      -> same reading as the PLS itself: the model begins")
        print("         softening earlier than the measurement, now in a")
        print("         number a stress-convention error cannot fake.")

    print("\n 6. the scale rule is not quietly broken")
    src = open(os.path.join(HERE, "extract_pls.py")).read()
    ck("the file says PLS is validation-only, never a card input",
       "never be a card input" in src)
    ck("Yang's table is carried with its temperatures, not just deltas",
       len(YANG_TABLE1) == 4 and YANG_TABLE1[0][0] == 300.0)
    ck("the CVI/PIP level caveat travels with the table",
       "CVI, not our PIP" in src)

    print("\n" + "=" * 74)
    print("  %d passed, %d failed" % (_PASS[0], _FAIL[0]))
    print("=" * 74)
    return 1 if _FAIL[0] else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv or "--check" in sys.argv:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
