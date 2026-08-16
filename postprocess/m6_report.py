#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m6_report.py   (plain python3 -- NOT abaqus python)
===================================================
Read the *_ss.csv files written by extract_ss_curve.py and answer the two
questions M6 exists to answer.  One pass over the same files gives both.

  1. DID A PEAK HAPPEN, AND WHERE?   The T1000 sweep varies the yarn
     longitudinal fracture energy G1t.  M5 ran at 12.5 N/mm, where the
     crack-band exponent is A = 0.239 -- 8.4x gentler than the fixed default
     -- and produced 313 monotonically increasing points with no peak at all
     (Ch.4 4.9-0).  If G1t is the cause, the peak should appear as it comes
     down and the peak stress should fall towards Zhang Table 3's 199.15 MPa.

  2. WHAT IS THE MODULUS AFTER THE COOLDOWN?   This is the number 4.9-0
     needs and does not have.  The 235.2 GPa it quotes is M5_c26k_T1000's
     UNDAMAGED tangent, measured where the cooldown span is 50 K; every
     published value it was compared against is room-temperature material
     that went through the full 1027 K.  The like-for-like number is RT23's
     tangent at the START of the tension step, which is the RVE after the
     cooldown has done its damage.

Both come from the initial slope and the peak of the same curve, so the two
jobs share one reader.

The initial tangent is fitted by least squares through the origin over the
first TANGENT_WINDOW of macroscopic strain, and the fit's own R^2 is printed
-- a tangent quoted from a curve that is not straight there is meaningless,
and the reader should be able to see that rather than trust it.

Usage
    python3 m6_report.py *_ss.csv
    python3 m6_report.py --window 5e-5 M6_T1000_g2p664_ss.csv
    python3 m6_report.py --selftest
"""
from __future__ import print_function

import glob
import os
import sys

#: strain window over which the initial tangent is fitted.
#:
#: THIS IS THE PROJECT'S ONE TANGENT DEFINITION.  m6_verdict.py imports the
#: function below rather than carrying its own, because it used to carry its
#: own and the two disagreed by 10.6 % on the same file (122.9 vs 111.1 GPa at
#: RT23) with nothing in either output saying which was which.
#:
#: The window is ABSOLUTE (a fixed strain) and not a fraction of the curve's
#: own span, and that is the whole point.  A fractional window makes the
#: answer depend on HOW FAR THE JOB GOT: truncating the real RT23 curve to a
#: quarter of its length moves the fractional-window answer 111.1 -> 121.2 GPa
#: (+9.1 %) while this one does not move at all.  A modulus that rises when a
#: job dies early is not a material property, it is a completion meter -- and
#: T500 is exactly a job that died early, so the bias is not hypothetical.
#:
#: data/literature/modulus_definition.py settles what we are comparing against:
#: refs/[10] Yang's 128.7 GPa is an INITIAL TANGENT on a curve whose own text
#: says "nonlinearity starts almost from the onset of loading".  Like-for-like
#: therefore means the narrowest window on which the fit is still straight --
#: which is why R^2 is reported and floored rather than assumed.
TANGENT_WINDOW = 1.0e-4
#: below this the curve is not straight in the window and the slope is not a
#: tangent; quote it and you are quoting a chord you did not mean to take.
TANGENT_R2_FLOOR = 0.999
#: fewer points than this and a "least squares fit" is a two-point slope
#: wearing a hat, and R^2 near 1 means nothing.
TANGENT_MIN_POINTS = 5
#: Zhang Table 3 simulation targets, MPa (verification/CALIBRATION_GUIDE.md)
TARGET = {"RT23": 128.45, "T500": 179.42, "T1000": 199.15}
#: published as-received moduli, GPa -- the two clusters of Ch.4 4.9-0
CLUSTER_HI = ("Li refs/[28] 142.06 / ZHANG2013 Fig.3 ~140", 140.0, 145.0)
CLUSTER_LO = ("ZHANG2013 Fig.4(b) 97.7 / Mei refs/[43] 70", 70.0, 98.0)


def ss_columns(header):
    """(eps_index, sigma_index) resolved BY NAME from an _ss.csv header.

    By name, not by position: a1's figure gate went quietly wrong when a
    column was inserted into a table read by position (2026-08-16), and the
    same failure was latent here -- extract_ss_curve.py writes
    eps_xx,sigma_xx_MPa first today, but nothing stops a future version
    prepending a time column, and a positional reader would then fit a
    tangent to time against strain without erroring.
    """
    names = [h.strip().lower() for h in header.split(",")]
    ei = next((i for i, n in enumerate(names) if n.startswith("eps")), None)
    si = next((i for i, n in enumerate(names) if n.startswith("sig")), None)
    if ei is None or si is None:
        raise ValueError("not an _ss.csv header: %r (need eps*, sig*)"
                         % header.strip())
    return ei, si


def read_ss(path):
    """Return (eps, sig) from an extract_ss_curve.py CSV."""
    eps, sig = [], []
    with open(path) as f:
        ei, si = ss_columns(f.readline())
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            eps.append(float(parts[ei]))
            sig.append(float(parts[si]))
    return eps, sig


def initial_tangent(eps, sig, window=TANGENT_WINDOW):
    """Least squares slope through the origin over the first `window`.

    Returns (E_MPa, r2, n_points).  Through the origin because the curve is
    referred to the start of the tension step, where both are zero by
    construction; fitting an intercept would absorb exactly the cooldown
    offset this measurement is trying to see.
    """
    xs = [(e, s) for e, s in zip(eps, sig) if 0.0 < e <= window]
    if len(xs) < 3:
        return None, None, len(xs)
    sxx = sum(e * e for e, _ in xs)
    sxy = sum(e * s for e, s in xs)
    if sxx <= 0.0:
        return None, None, len(xs)
    k = sxy / sxx
    sst = sum(s * s for _, s in xs)
    sse = sum((s - k * e) ** 2 for e, s in xs)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    return k, r2, len(xs)


def tangent_verdict(E, r2, npt):
    """Is this slope quotable as an initial tangent?

    Returns (quotable, reason).  The two ways it fails are opposite: too few
    points means the fit is not a fit, and a low R^2 means the window has run
    past the straight part and the number is a chord.  Both produce a slope
    that looks perfectly reasonable printed to one decimal, which is why the
    judgement has to be attached to the number rather than left to the reader.
    """
    if E is None:
        return False, "no points inside the window"
    if npt < TANGENT_MIN_POINTS:
        return False, ("only %d points in the window (need %d)"
                       % (npt, TANGENT_MIN_POINTS))
    if r2 is None or r2 != r2 or r2 < TANGENT_R2_FLOOR:
        return False, ("R^2 = %s is below %.3f -- not straight here"
                       % ("nan" if r2 is None or r2 != r2 else "%.5f" % r2,
                          TANGENT_R2_FLOOR))
    return True, "R^2 = %.5f over %d points" % (r2, npt)


def fractional_tangent(eps, sig, frac=0.10):
    """The REJECTED definition, kept so the rejection stays testable.

    Least squares over the first `frac` of the curve's own strain span, with
    the first point shifted to the origin -- what m6_verdict.py used to do.
    Nothing calls this except the selftest, which uses it to show that the
    answer moves when the job is truncated.  Do not quote it.
    """
    pts = [(e, s) for e, s in zip(eps, sig)]
    if len(pts) < 4:
        return None
    lim = pts[0][0] + frac * (pts[-1][0] - pts[0][0])
    win = [p for p in pts if p[0] <= lim] or pts[:3]
    if len(win) < 3:
        win = pts[:3]
    e0, s0 = win[0]
    den = sum((e - e0) ** 2 for e, _ in win)
    if den <= 0.0:
        return None
    return sum((e - e0) * (s - s0) for e, s in win) / den


def peak(eps, sig):
    """Return (sigma_peak, eps_peak, index, peaked?).

    `peaked` is False when the maximum is the LAST point, i.e. the curve was
    still rising when the job stopped and the peak is only a lower bound.
    """
    i = max(range(len(sig)), key=lambda j: sig[j])
    return sig[i], eps[i], i, i < len(sig) - 1


def secant_at_end(eps, sig):
    if not eps or eps[-1] == 0.0:
        return None
    return sig[-1] / eps[-1]


def cluster_of(E_GPa):
    for name, lo, hi in (CLUSTER_HI, CLUSTER_LO):
        if lo <= E_GPa <= hi:
            return name
    return "outside both clusters"


def case_of(name):
    for k in ("RT23", "T500", "T1000"):
        if k in name:
            return k
    return None


def report(paths, window=TANGENT_WINDOW):
    print("=" * 78)
    print("m6_report.py -- peak, and the modulus after the cooldown")
    print("=" * 78)
    print("\ntangent fitted through the origin over eps <= %.1e\n" % window)

    print("%-26s %-9s %-11s %-8s %-9s %-9s"
          % ("job", "n pts", "E_init[GPa]", "R^2", "peak[MPa]", "peaked?"))
    rows = []
    for p in paths:
        try:
            eps, sig = read_ss(p)
        except Exception as exc:
            print("%-26s  !! %s" % (os.path.basename(p), exc))
            continue
        if len(eps) < 3:
            print("%-26s  !! only %d points" % (os.path.basename(p), len(eps)))
            continue
        E, r2, npt = initial_tangent(eps, sig, window)
        sp, ep, ip, peaked = peak(eps, sig)
        tag = os.path.basename(p).replace("_ss.csv", "")
        print("%-26s %-9d %-11s %-8s %-9.2f %-9s"
              % (tag, len(eps),
                 "%.1f" % (E / 1000.0) if E else "-",
                 "%.5f" % r2 if r2 is not None else "-",
                 sp, "yes" if peaked else "NO, still rising"))
        rows.append((tag, eps, sig, E, r2, sp, ep, peaked))

    # ---- question 1: the sweep -----------------------------------------
    sweep = [r for r in rows if case_of(r[0]) == "T1000"]
    if sweep:
        print("\n" + "-" * 78)
        print(" 1. DID LOWERING G1t PRODUCE A PEAK?   target %.2f MPa"
              % TARGET["T1000"])
        print("-" * 78)
        print("\n %-26s %-11s %-9s %-10s %s"
              % ("job", "peak[MPa]", "vs target", "eps_peak[%]", "peaked?"))
        for tag, eps, sig, E, r2, sp, ep, peaked in sweep:
            print(" %-26s %-11.2f %-9.2f %-10.4f %s"
                  % (tag, sp, sp / TARGET["T1000"], 100.0 * ep,
                     "yes" if peaked else "NO -- lower bound only"))
        npeaked = sum(1 for r in sweep if r[7])
        print("""
 READING.  A run that did not peak reports a LOWER BOUND, not a strength.
 %d of %d peaked.  If the ones that peaked are the low-G1t ones, G1t is the
 cause and the rest of the 14-knob search never has to happen.  If none
 peaked even at G1t = 2.664, the softening exponent is not what is holding
 the curve up and the next suspect is the pull-out tail (X_PO, rF, K1).
""" % (npeaked, len(sweep)))

    # ---- question 2: the cooldown modulus -------------------------------
    rt = [r for r in rows if case_of(r[0]) == "RT23"]
    if rt:
        print("-" * 78)
        print(" 2. THE MODULUS 4.9-0 NEEDS: RT23 AFTER THE COOLDOWN")
        print("-" * 78)
        for tag, eps, sig, E, r2, sp, ep, peaked in rt:
            if E is None:
                print("\n %s: too few points inside the window" % tag)
                continue
            EG = E / 1000.0
            print("""
 %s
   initial tangent after cooldown   %.1f GPa   (R^2 = %.5f over %d points)
   which cluster                    %s
   terminal secant                  %s
""" % (tag, EG, r2, initial_tangent(eps, sig, window)[2], cluster_of(EG),
            "%.1f GPa" % (secant_at_end(eps, sig) / 1000.0)
            if secant_at_end(eps, sig) else "-"))
        print(""" READING.  This is the number to set against the published as-received
 moduli, NOT the 235.2 GPa of M5_c26k_T1000 -- that was measured where the
 cooldown span is 50 K and the RVE is essentially virgin, while every
 published value is material that went through the full 1027 K.  If this
 lands in the lower cluster, the model's cooldown is doing what the real
 process does and 4.9-0 should be restated as agreement, not as a 1.66x
 error.  If it lands in the upper cluster, the cooldown is under-damaging
 and the stress-free temperature or the constituent CTEs are the reason
 (4.9-9, 4.9-11) -- still not a strength knob.
""")

    return 0


# --------------------------------------------------------------------------
def selftest():
    ok = []

    def t(name, cond, detail=""):
        ok.append(cond)
        print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("m6_report.py --selftest")

    # a straight line must return its own slope with R^2 = 1
    E0 = 92100.0
    eps = [i * 1.0e-5 for i in range(1, 40)]
    sig = [E0 * e for e in eps]
    E, r2, n = initial_tangent(eps, sig)
    t("a straight line returns its slope", abs(E - E0) < 1e-6, "%.3f" % E)
    t("and R^2 is 1", abs(r2 - 1.0) < 1e-12)
    t("the window really limits the fit", n == 10, "%d points" % n)

    # a softening curve: the tangent must come from the straight part only
    eps2 = [i * 1.0e-5 for i in range(1, 200)]
    sig2 = [E0 * e if e <= 1.0e-4 else E0 * 1.0e-4 + 0.2 * E0 * (e - 1.0e-4)
            for e in eps2]
    E2, r22, _ = initial_tangent(eps2, sig2)
    t("softening after the window does not drag the tangent down",
      abs(E2 - E0) / E0 < 1e-9, "%.1f vs %.1f" % (E2, E0))

    # peak detection, and the still-rising case
    sp, ep, ip, peaked = peak([1.0, 2.0, 3.0], [10.0, 30.0, 20.0])
    t("a real peak is found and flagged as peaked", sp == 30.0 and peaked)
    sp, ep, ip, peaked = peak([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
    t("a monotonic curve is flagged as NOT peaked",
      sp == 30.0 and not peaked, "reports a lower bound")

    t("the M5 T1000 tangent lands outside both clusters",
      cluster_of(235.2) == "outside both clusters")
    t("92.1 GPa lands in the lower cluster",
      cluster_of(92.1) == CLUSTER_LO[0])
    t("142.06 GPa lands in the upper cluster",
      cluster_of(142.06) == CLUSTER_HI[0])
    t("case_of reads the job name", case_of("M6_RT23_g2p664") == "RT23"
      and case_of("M6_T1000_g8p0") == "T1000")

    # ---- the tangent definition, and why the other one was rejected -------
    print("\n  the one tangent definition (A-5)")
    q, why = tangent_verdict(E0, 1.0, 10)
    t("a straight fit over enough points is quotable", q, why)
    q, why = tangent_verdict(E0, 1.0, TANGENT_MIN_POINTS - 1)
    t("a 'fit' over too few points is NOT quotable", not q, why)
    q, why = tangent_verdict(E0, 0.97, 20)
    t("a slope from a bent window is NOT quotable", not q, why)
    t("and the floor is stated, not implied",
      TANGENT_R2_FLOOR >= 0.999 and TANGENT_MIN_POINTS >= 5,
      "R^2 >= %.3f over >= %d points" % (TANGENT_R2_FLOOR, TANGENT_MIN_POINTS))

    here = os.path.dirname(os.path.abspath(__file__))
    rt = os.path.join(os.path.dirname(here), "data", "results", "M6",
                      "LTH_M6_RT23_ss.csv")
    if os.path.exists(rt):
        eR, sR = read_ss(rt)
        full = initial_tangent(eR, sR)[0]
        cut = [initial_tangent(eR[:k], sR[:k])[0]
               for k in (len(eR), int(0.75 * len(eR)), int(0.5 * len(eR)),
                         int(0.25 * len(eR)))]
        t("the absolute window is blind to where the job stopped",
          max(abs(c - full) for c in cut) < 1e-9,
          "%.1f GPa at 100/75/50/25 %% of the run" % (full / 1e3))
        fr = [fractional_tangent(eR[:k], sR[:k])
              for k in (len(eR), int(0.25 * len(eR)))]
        drift = abs(fr[1] - fr[0]) / fr[0]
        t("the fractional window is NOT -- this is why it was rejected",
          drift > 0.05, "%.1f -> %.1f GPa, %+.1f %% on truncation alone"
          % (fr[0] / 1e3, fr[1] / 1e3, 100.0 * drift))
        t("and it reads LOW on the full curve, being a chord not a tangent",
          fr[0] < full, "%.1f < %.1f GPa" % (fr[0] / 1e3, full / 1e3))
        q, why = tangent_verdict(*initial_tangent(eR, sR))
        t("the real RT23 curve passes the straightness floor", q, why)
    else:
        t("the real RT23 curve is committed for this test",
          False, "missing %s" % rt)

    # ---- column-name hardening (the a1-0041 failure class) ---------------
    print("\n  columns are resolved by name, not position")
    import tempfile
    d5 = tempfile.mkdtemp()
    normal = os.path.join(d5, "n_ss.csv")
    open(normal, "w").write("eps_xx,sigma_xx_MPa\n0.001,100.0\n0.002,180.0\n")
    shifted = os.path.join(d5, "s_ss.csv")
    open(shifted, "w").write("time,eps_xx,sigma_xx_MPa\n"
                             "0.5,0.001,100.0\n1.0,0.002,180.0\n")
    e1, s1 = read_ss(normal)
    e2, s2 = read_ss(shifted)
    t("a prepended column changes nothing", e1 == e2 and s1 == s2,
      "eps %s sig %s either way" % (e1, s1))
    t("  the positional reading of the shifted file would have been wrong",
      e1 != [0.5, 1.0], "position 0 is 'time' there")
    try:
        ss_columns("a,b,c")
        t("a header with neither eps nor sigma fails loudly", False)
    except ValueError as exc:
        t("a header with neither eps nor sigma fails loudly", True, str(exc))

    import m6_verdict as _v
    cs = _v.read_curve(shifted)
    t("m6_verdict.read_curve absorbs the shift the same way",
      cs == [(0.001, 100.0), (0.002, 180.0)], "%s" % cs)
    open(os.path.join(d5, "h_ss.csv"), "w").write("0.001,100.0\n0.002,180.0\n")
    t("  and a headerless legacy file still reads as columns 0/1",
      _v.read_curve(os.path.join(d5, "h_ss.csv")) == [(0.002, 180.0)],
      "first line consumed as header, by design -- legacy files had one")
    sys.path.insert(0, os.path.join(os.path.dirname(here), "data",
                                    "properties"))
    import m6_calibration as _cal
    t("m6_calibration's M5 reader is hardened the same way",
      _cal.measured_curve(shifted) == [(0.001, 100.0), (0.002, 180.0)]
      if hasattr(_cal, "measured_curve") else "startswith(\"eps\")"
      in open(os.path.join(os.path.dirname(here), "data", "properties",
                           "m6_calibration.py")).read(),
      "columns by name in all three curve readers")
    # NOT `is`: run as __main__ this module is loaded twice under two names,
    # so the two function objects differ while the definition does not.
    # Attribution plus the import line is what actually pins it.
    src = open(os.path.join(here, "m6_verdict.py")).read()
    t("m6_verdict's tangent is attributed to this file",
      _v.initial_tangent.__module__ in ("m6_report", "__main__")
      and _v.initial_tangent.__name__ == "initial_tangent",
      "%s.%s" % (_v.initial_tangent.__module__, _v.initial_tangent.__name__))
    t("and it gets there by importing, not by copying",
      any("initial_tangent" in seg.split(")")[0]
          for seg in src.split("from m6_report import")[1:]),
      "one definition, imported once")

    print("\n%s" % ("ALL %d SELFTESTS PASS" % len(ok) if all(ok)
                    else "FAILED %d of %d" % (ok.count(False), len(ok))))
    return 0 if all(ok) else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    window = TANGENT_WINDOW
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--window":
            window = float(argv[i + 1])
            i += 2
            continue
        args.append(argv[i])
        i += 1
    paths = []
    for a in args:
        paths.extend(sorted(glob.glob(a)) if any(c in a for c in "*?") else [a])
    if not paths:
        paths = sorted(glob.glob("*_ss.csv"))
    if not paths:
        print("no *_ss.csv found.  Run extract_ss_curve.py first:")
        print("  abaqus python extract_ss_curve.py <job>.odb")
        return 2
    return report(paths, window)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
