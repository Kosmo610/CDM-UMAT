#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m6_verdict.py -- did the three re-sourced card values do what they claimed?

RUN WITH PLAIN PYTHON (it reads csv, not the odb):

    python m6_verdict.py M6_c26k_RT23_ss.csv M6_c26k_T500_ss.csv M6_c26k_T1000_ss.csv

WHAT M6 CHANGED, AND WHAT EACH CHANGE PREDICTS
----------------------------------------------
M6 differs from M5 by three card entries and nothing else -- diff the decks
and exactly three lines move.  None of them was fitted:

  matrix E   350000 -> 213110 MPa   the porosity the filled-cell mesh lacks
  yarn Xt    2835   -> 475/581/694  the in-situ band, not a strand figure
  Gtt, Gtc   0      -> 0.107 N/mm   the crack band was OFF for those modes

The useful thing is that the first two are READ OFF DIFFERENT PARTS OF THE
SAME CURVE, so one job per temperature tests both and no extra job is needed:

  * the INITIAL TANGENT tests the porosity correction.  It is set before any
    damage, so Xt cannot reach it.
  * the STRESS AT THE MEASURED FAILURE STRAIN tests Xt.  The deck pulls to
    Zhang's own measured failure strain, so this is a like-for-like number
    against Zhang Table 3.

A caution the report repeats: at 23 C the yarns are NOT expected to rupture.
Xt/E1 = 474.7/254967 = 0.186 % lies beyond the 0.150 % the RT deck pulls to,
and Zhang's RT specimen failed at 0.150 %.  So RT23 tests "what stress at the
measured failure strain", not "where is the peak".  A curve that ends without
a peak is the expected result there, not a failed run.
"""
from __future__ import print_function

import os
import sys

#: Zhang 2022 Table 3 -- the L2 validation target.  VALIDATION ONLY.
ZHANG = {23: 128.45, 500: 179.42, 1000: 199.15}

#: Strain each deck pulls to, which is Zhang's own measured failure strain.
EPS_TARGET = {23: 0.001500, 500: 0.003200, 1000: 0.004800}

#: refs/[10] Yang Table 1, INITIAL modulus [MPa].  The convention matters:
#: refs/[43] Mei's 70 GPa is a whole-curve chord on a curve that is non-linear
#: from the onset, and comparing an initial tangent against it is what
#: produced the retracted "3.4x too stiff" reading.  See porosity_stiffness.py.
YANG_E0 = {23: 128.7e3, 500: None, 1000: 172.7e3}
YANG_E0_NEAR = {500: (700, 152.3e3)}      # nearest measured temperature

#: What M5 gave with the old card, for the before/after column.
M5 = {1000: dict(e0=235.2e3, stop_eps=3.3184e-3, stop_sig=326.70)}

#: Card values M6 ships, per deck.
M6_XT = {23: 474.7105, 500: 581.4010, 1000: 694.4297}
YARN_E1 = 254967.228042
VY_X = 0.4982 / 2.0


def read_curve(path):
    """[(eps, sigma)] from an extract_ss_curve.py csv."""
    out = []
    with open(path) as f:
        for line in f.read().splitlines()[1:]:
            p = line.split(",")
            if len(p) >= 2:
                try:
                    out.append((float(p[0]), float(p[1])))
                except ValueError:
                    pass
    return sorted(out)


def temperature_of(path):
    base = os.path.basename(path).upper()
    for tag, T in (("RT23", 23), ("T500", 500), ("T1000", 1000)):
        if tag in base:
            return T
    return None


def initial_tangent(curve, frac=0.10):
    """Secant over the first `frac` of the strain range.

    Not a two-point slope: the first increment of a stabilised step carries
    the stabilisation transient, and two points would sit on top of it.
    Returns (E, n_points_used, eps_end) or None.
    """
    if len(curve) < 4:
        return None
    emax = curve[-1][0]
    lim = curve[0][0] + frac * (emax - curve[0][0])
    pts = [p for p in curve if p[0] <= lim]
    if len(pts) < 3:
        pts = curve[:3]
    # least squares through the origin-shifted first points
    e0, s0 = pts[0]
    num = sum((e - e0) * (s - s0) for e, s in pts)
    den = sum((e - e0) ** 2 for e, s in pts)
    if den <= 0.0:
        return None
    return num / den, len(pts), pts[-1][0]


def stress_at(curve, eps):
    if not curve or eps < curve[0][0] or eps > curve[-1][0]:
        return None
    for i in range(len(curve) - 1):
        a, b = curve[i], curve[i + 1]
        if a[0] <= eps <= b[0]:
            if b[0] == a[0]:
                return a[1]
            w = (eps - a[0]) / (b[0] - a[0])
            return a[1] + w * (b[1] - a[1])
    return curve[-1][1]


def peak(curve):
    if not curve:
        return None
    i = max(range(len(curve)), key=lambda k: curve[k][1])
    return curve[i][0], curve[i][1], i == len(curve) - 1


def report(paths):
    print("=" * 78)
    print("m6_verdict.py -- the three re-sourced card values, judged")
    print("=" * 78)

    rows = []
    for p in paths:
        if not os.path.exists(p):
            print("\n  MISSING: %s" % p)
            continue
        T = temperature_of(p)
        if T is None:
            print("\n  cannot tell the temperature from %r -- name the csv "
                  "M6_c26k_{RT23,T500,T1000}_ss.csv" % os.path.basename(p))
            continue
        curve = read_curve(p)
        if len(curve) < 3:
            print("\n  %s has %d points -- nothing to judge"
                  % (os.path.basename(p), len(curve)))
            continue
        rows.append((T, p, curve))

    if not rows:
        print("\n  no usable curves.  Run extract_ss_curve.py on the odbs "
              "first:\n    abaqus python extract_ss_curve.py M6_c26k_RT23.odb")
        return 1
    rows.sort()

    print("\n 1. HOW FAR EACH JOB GOT")
    print("    %-8s %8s %12s %12s %10s"
          % ("T [C]", "points", "eps end [%]", "target [%]", "completed"))
    for T, p, c in rows:
        tgt = EPS_TARGET[T]
        print("    %-8d %8d %12.4f %12.4f %9.1f %%"
              % (T, len(c), 100.0 * c[-1][0], 100.0 * tgt,
                 100.0 * c[-1][0] / tgt))

    print("\n 2. INITIAL TANGENT -- this tests the POROSITY correction")
    print("    Set before any damage, so yarn Xt cannot reach it.")
    print("    %-8s %14s %14s %10s  %s"
          % ("T [C]", "M6 [GPa]", "measured", "ratio", "source"))
    for T, p, c in rows:
        it = initial_tangent(c)
        if it is None:
            print("    %-8d %14s" % (T, "too few points"))
            continue
        e0 = it[0]
        meas, src = YANG_E0.get(T), "refs/[10] Yang Table 1"
        if meas is None and T in YANG_E0_NEAR:
            near_T, meas = YANG_E0_NEAR[T]
            src = "refs/[10] at %d C (nearest measured)" % near_T
        if meas:
            print("    %-8d %14.1f %14.1f %9.2fx  %s"
                  % (T, e0 / 1e3, meas / 1e3, e0 / meas, src))
        else:
            print("    %-8d %14.1f %14s %10s  %s"
                  % (T, e0 / 1e3, "-", "-", "no measurement"))
    if 1000 in [r[0] for r in rows]:
        print("    For reference, M5 with the OLD card gave %.1f GPa at "
              "1000 C," % (M5[1000]["e0"] / 1e3))
        print("    i.e. %.2fx the measurement.  The prediction was that "
              "removing" % (M5[1000]["e0"] / YANG_E0[1000]))
        print("    the missing 19.6 %% of void takes that to 170.0 GPa.")

    print("\n 3. STRESS AT THE MEASURED FAILURE STRAIN -- this tests yarn Xt")
    print("    %-8s %14s %14s %10s"
          % ("T [C]", "M6 [MPa]", "Zhang T3", "ratio"))
    worst, worst_at = -1.0, "nothing comparable"
    for T, p, c in rows:
        s = stress_at(c, EPS_TARGET[T])
        if s is None:
            print("    %-8d %14s %14.2f %10s   (job stopped at %.4f %%)"
                  % (T, "not reached", ZHANG[T], "-", 100.0 * c[-1][0]))
            continue
        rel = abs(s - ZHANG[T]) / ZHANG[T]
        if rel > worst:
            worst, worst_at = rel, "%d C" % T
        print("    %-8d %14.2f %14.2f %9.2fx" % (T, s, ZHANG[T], s / ZHANG[T]))
    if worst >= 0.0:
        print("    worst deviation %.1f %% at %s" % (100.0 * worst, worst_at))
        print("    M5 with the old card was 1.64x at 1000 C and still rising.")
    else:
        print("    No job reached its target strain, so Xt is NOT yet judged.")

    print("\n 4. PEAK, AND WHETHER THERE WAS ONE")
    for T, p, c in rows:
        pe, ps, at_end = peak(c)
        rupture = M6_XT[T] / YARN_E1
        note = ("no peak -- still rising at the last point" if at_end
                else "peak reached")
        print("    %-8d %8.2f MPa at eps = %.4f %%   %s"
              % (T, ps, 100.0 * pe, note))
        print("             yarn rupture strain Xt/E1 = %.4f %%, deck pulls "
              "to %.4f %%" % (100.0 * rupture, 100.0 * EPS_TARGET[T]))
        if rupture > EPS_TARGET[T]:
            print("             -> the aligned yarns are NOT expected to "
                  "rupture in this deck.")
            print("                That is the design, not a failure: the "
                  "deck stops at the")
            print("                strain the specimen failed at.")

    print("\n 5. THE CEILING THE CARD IMPLIES")
    print("    %-8s %10s %14s %12s" % ("T [C]", "Xt", "ROM bound", "Zhang T3"))
    for T in sorted(M6_XT):
        rb = VY_X * M6_XT[T]
        print("    %-8d %10.1f %14.1f %12.2f   %s"
              % (T, M6_XT[T], rb, ZHANG[T],
                 "below target, matrix must supply the rest"
                 if rb < ZHANG[T] else "ABOVE target"))
    print("    The old card's bound was 706 MPa -- 3.5x the target and above")
    print("    every measured 2D C/SiC strength.  That is what M6 removes.")

    print("\n 6. WHAT TO DO WITH THIS")
    print("    tangent right, stress right  -> both corrections land; write")
    print("                                    up 4.9-12 and 4.9-13 as closed")
    print("    tangent right, stress low    -> Xt is too low; walk up the 8 %")
    print("                                    band toward the scale end")
    print("                                    (516 / 628 / 745)")
    print("    tangent still high           -> the porosity is not all in the")
    print("                                    matrix pocket; revisit 4.9-13")
    print("    Before quoting ANY strength, run damage_census.py and read the")
    print("    ATEFF clamped fraction.  Gtc = 0.107 is knowingly inadmissible")
    print("    for the largest elements, and a clamped element is brittle.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(report(args))
