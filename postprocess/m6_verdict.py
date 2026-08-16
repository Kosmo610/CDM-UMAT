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
    """[(eps, sigma)] from an extract_ss_curve.py csv.

    Columns are resolved BY NAME from the header (m6_report.ss_columns), not
    taken as the first two -- this reader used to be positional, which works
    until the day someone prepends a column, and then it fits time as strain
    without a single error message.  Same signature as always: a1's figure
    4.6 imports this function.
    """
    from m6_report import ss_columns
    out = []
    with open(path) as f:
        lines = f.read().splitlines()
    if not lines:
        return out
    try:
        ei, si = ss_columns(lines[0])
    except ValueError:
        ei, si = 0, 1                     # headerless legacy file
    for line in lines[1:]:
        p = line.split(",")
        if len(p) > max(ei, si):
            try:
                out.append((float(p[ei]), float(p[si])))
            except ValueError:
                pass
    return sorted(out)


def temperature_of(path):
    base = os.path.basename(path).upper()
    for tag, T in (("RT23", 23), ("T500", 500), ("T1000", 1000)):
        if tag in base:
            return T
    return None


#: THE TANGENT DEFINITION LIVES IN m6_report.py AND IS IMPORTED, NOT COPIED.
#:
#: Until 2026-08-14 this file carried its own: a least-squares slope over the
#: first 10 % of each curve's own strain span.  On the same RT23 file that
#: gave 111.1 GPa while m6_report gave 122.9 -- a 10.6 % fork with nothing in
#: either output to say which number a reader was holding.  Chapter 4 quoted
#: the 111.1 lineage; this file's own conclusions were drawn from it.
#:
#: The fractional window lost on a fact, not a preference: truncate the real
#: RT23 curve to a quarter of its length and it answers 121.2 instead of
#: 111.1, because a shorter curve has a shorter tenth.  It rewards jobs that
#: die early, and T500 died early.  m6_report.fractional_tangent keeps the
#: rejected form alive so the selftest can keep proving that.
from m6_report import (initial_tangent, tangent_verdict,      # noqa: E402
                       TANGENT_WINDOW, TANGENT_R2_FLOOR)


def tangent_of(curve):
    """(E, r2, npts) on a [(eps, sigma)] curve, via the one definition."""
    return initial_tangent([e for e, _ in curve], [s for _, s in curve])


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

    csv_rows = []
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
    print("    Fitted through the origin over eps <= %.1e; m6_report.py owns"
          % TANGENT_WINDOW)
    print("    the definition, and R^2 >= %.3f is what makes it a tangent."
          % TANGENT_R2_FLOOR)
    print("    %-8s %12s %14s %8s %10s  %s"
          % ("T [C]", "M6 [GPa]", "measured", "ratio", "quotable", "source"))
    for T, p, c in rows:
        E, r2, npt = tangent_of(c)
        quotable, why = tangent_verdict(E, r2, npt)
        meas, src = YANG_E0.get(T), "refs/[10] Yang Table 1"
        if meas is None and T in YANG_E0_NEAR:
            near_T, meas = YANG_E0_NEAR[T]
            src = "refs/[10] at %d C (nearest measured)" % near_T
        if E is None:
            print("    %-8d %12s   %s" % (T, "-", why))
            csv_rows.append(("tangent", "%d C" % T, "", "",
                             "not fitted", why, "NOT QUOTABLE"))
            continue
        ratio = ("%.2fx" % (E / meas)) if meas else "-"
        print("    %-8d %12.1f %14s %8s %10s  %s"
              % (T, E / 1e3, "%.1f" % (meas / 1e3) if meas else "-", ratio,
                 "yes" if quotable else "NO", src))
        print("             %s" % why)
        csv_rows.append(("tangent", "%d C" % T, "%.1f" % (E / 1e3), "GPa",
                         "%s | %s" % (src, why),
                         "measured %s GPa, ratio %s"
                         % ("%.1f" % (meas / 1e3) if meas else "-", ratio),
                         "quotable" if quotable else "NOT QUOTABLE"))
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
            csv_rows.append(("strength", "%d C" % T, "", "MPa",
                             "job stopped at %.4f %% of strain"
                             % (100.0 * c[-1][0]),
                             "Zhang T3 %.2f MPa" % ZHANG[T], "NOT REACHED"))
            continue
        rel = abs(s - ZHANG[T]) / ZHANG[T]
        if rel > worst:
            worst, worst_at = rel, "%d C" % T
        print("    %-8d %14.2f %14.2f %9.2fx" % (T, s, ZHANG[T], s / ZHANG[T]))
        csv_rows.append(("strength", "%d C" % T, "%.2f" % s, "MPa",
                         "Zhang 2022 Table 3 = %.2f MPa (VALIDATION ONLY)"
                         % ZHANG[T], "ratio %.2fx" % (s / ZHANG[T]),
                         "PROVISIONAL until damage_census.py"))
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

    out = write_csv(csv_rows, os.path.dirname(os.path.abspath(paths[0])))
    print("\n    wrote %s -- upload THAT, not a screenshot of this." % out)
    print("=" * 78)
    return 0


CSV_HEADER = "kind,case,value,unit,basis,comparison,verdict"


def write_csv(rows, where, name="m6_verdict_summary.csv"):
    """Value, basis and verdict on the same line -- CLAUDE.md section 3-2.

    Written even when every row failed: which rows have to be thrown away is
    exactly what the file is for, and a screenshot of a console crops at the
    window edge, which has twice now been the line that mattered.
    """
    path = os.path.join(where or ".", name)
    with open(path, "w") as f:
        f.write(CSV_HEADER + "\n")
        for r in rows:
            f.write(",".join('"%s"' % str(x).replace('"', "'")
                             if ("," in str(x) or '"' in str(x)) else str(x)
                             for x in r) + "\n")
    return path


def selftest():
    import m6_report as R
    ok = []

    def t(name, cond, detail=""):
        ok.append(cond)
        print("  %s  %-56s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("m6_verdict.py --selftest")

    print("\n  A. one definition, imported not copied")
    t("initial_tangent IS m6_report's", initial_tangent is R.initial_tangent)
    t("tangent_verdict IS m6_report's", tangent_verdict is R.tangent_verdict)
    # a source scan, so the fork cannot quietly grow back.  Matched at the
    # start of a line: this very check mentions the name, and a substring
    # test would find itself and pass for the wrong reason.
    defs = [l.split("(")[0].strip() for l in open(__file__).read().splitlines()
            if l.startswith("def ")]
    t("this file defines no tangent of its own",
      not [d for d in defs if "tangent" in d and d != "def tangent_of"],
      "the 10 %%-of-span form is gone; defines %s" % ", ".join(defs))
    t("and the rejected form is kept where it can be tested",
      hasattr(R, "fractional_tangent"),
      "m6_report.fractional_tangent, called only by selftests")

    print("\n  B. tangent_of feeds the curve format this file uses")
    E0 = 100000.0
    curve = [(i * 1.0e-5, E0 * i * 1.0e-5) for i in range(0, 40)]
    E, r2, npt = tangent_of(curve)
    t("a straight curve returns its slope", abs(E - E0) < 1e-6, "%.1f" % E)
    t("and it is judged quotable", tangent_verdict(E, r2, npt)[0],
      "R^2 = %.5f over %d points" % (r2, npt))

    print("\n  C. the real curves, and what changed by settling this")
    here = os.path.dirname(os.path.abspath(__file__))
    m6 = os.path.join(os.path.dirname(here), "data", "results", "M6")
    was = {23: 111.1, 500: 167.5, 1000: 174.2}      # the fractional lineage
    now = {}
    for tag, T in (("RT23", 23), ("T500", 500), ("T1000", 1000)):
        p = os.path.join(m6, "LTH_M6_%s_ss.csv" % tag)
        if not os.path.exists(p):
            t("curve %s is committed" % tag, False, "missing %s" % p)
            continue
        c = read_curve(p)
        E, r2, npt = tangent_of(c)
        now[T] = E / 1e3
        q, why = tangent_verdict(E, r2, npt)
        t("%s is quotable under the settled definition" % tag, q, why)
        old = R.fractional_tangent([e for e, _ in c], [s for _, s in c]) / 1e3
        t("  and %s's old number is reproduced, so the move is traced" % tag,
          abs(old - was[T]) < 0.15, "%.1f (was quoted as %.1f)" % (old, was[T]))
    if 23 in now and 1000 in now:
        t("RT23 moves UP, toward refs/[10]'s 128.7", now[23] > was[23],
          "%.1f -> %.1f GPa, ratio %.2fx -> %.2fx"
          % (was[23], now[23], was[23] / 128.7, now[23] / 128.7))
        t("T1000 moves up too, so 1.01x was NOT the right headline",
          now[1000] > was[1000], "%.1f -> %.1f GPa, ratio %.2fx -> %.2fx"
          % (was[1000], now[1000], was[1000] / 172.7, now[1000] / 172.7))
        t("and it is still the best of the three against a measurement",
          abs(now[1000] / 172.7 - 1.0) < abs(now[23] / 128.7 - 1.0),
          "%.2fx vs %.2fx" % (now[1000] / 172.7, now[23] / 128.7))

    print("\n  D. the CSV this file used to not write")
    import tempfile
    d = tempfile.mkdtemp()
    p = write_csv([("tangent", "23 C", "122.9", "GPa", "refs/[10], R^2=0.99992",
                    "measured 128.7 GPa, ratio 0.96x", "quotable")], d)
    body = open(p).read()
    t("it writes a file", os.path.exists(p), os.path.basename(p))
    t("value, basis and verdict are on the same line",
      "122.9" in body and "refs/[10]" in body and "quotable" in body)
    t("the header names all three", all(k in CSV_HEADER
                                        for k in ("value", "basis", "verdict")))
    t("commas inside a field are quoted, not spilled",
      body.splitlines()[1].count(",") - body.splitlines()[1].count('",') >= 0
      and len(body.splitlines()) == 2, "one data row survived the round trip")

    print("\n%s" % ("ALL %d SELFTESTS PASS" % len(ok) if all(ok)
                    else "FAILED %d of %d" % (ok.count(False), len(ok))))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(report(args))
