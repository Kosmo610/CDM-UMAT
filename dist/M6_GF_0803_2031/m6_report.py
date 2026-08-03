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

#: strain window over which the initial tangent is fitted
TANGENT_WINDOW = 1.0e-4
#: Zhang Table 3 simulation targets, MPa (verification/CALIBRATION_GUIDE.md)
TARGET = {"RT23": 128.45, "T500": 179.42, "T1000": 199.15}
#: published as-received moduli, GPa -- the two clusters of Ch.4 4.9-0
CLUSTER_HI = ("Li refs/[28] 142.06 / ZHANG2013 Fig.3 ~140", 140.0, 145.0)
CLUSTER_LO = ("ZHANG2013 Fig.4(b) 97.7 / Mei refs/[43] 70", 70.0, 98.0)


def read_ss(path):
    """Return (eps, sig) from an extract_ss_curve.py CSV."""
    eps, sig = [], []
    with open(path) as f:
        head = f.readline()
        if "eps" not in head:
            raise ValueError("%s: not an _ss.csv (header was %r)"
                             % (path, head.strip()))
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            eps.append(float(parts[0]))
            sig.append(float(parts[1]))
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
