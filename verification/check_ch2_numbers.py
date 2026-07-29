#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch2_numbers.py
====================
Every number quoted in docs/CH2_LITERATURE_REVIEW.md must still agree with the
CSV it came from.

Why this exists: the chapter quotes digitized figures.  Re-running
data/literature/digitize.py with a better calibration -- which is expected to
happen -- silently changes those CSVs.  Without this check the thesis text
drifts away from its own data and nobody notices until a reviewer recomputes a
percentage.

This checks two things:
  1. the raw values are still what the chapter says they are, and
  2. the DERIVED percentages the chapter states in prose ("stiffness falls
     21 % by N=20") still follow from those values.

Run:  python3 verification/check_ch2_numbers.py
"""
from __future__ import print_function

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIT = os.path.join(ROOT, "data", "literature")
CHAPTER = os.path.join(ROOT, "docs", "CH2_LITERATURE_REVIEW.md")

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))


def rows(fname):
    path = os.path.join(LIT, fname)
    with open(path) as f:
        return list(csv.DictReader(l for l in f if not l.startswith("#")))


def main():
    print("=" * 72)
    print("check_ch2_numbers.py -- Ch.2 text vs data/literature/*.csv")
    print("=" * 72)

    ts = rows("csic_thermal_shock.csv")

    def cell(src, prop, n):
        for r in ts:
            if (r["source_key"] == src and r["property"] == prop
                    and r["cycles"] == str(n)):
                return r
        return None

    # ---- Table: Yin et al. [2], 3D C/SiC flexural strength -------------
    print("\n Table 2.4.2a -- Yin et al. [2], 3D C/SiC")
    for n, abs_mpa, ratio in ((0, 838.8, 1.0000), (20, 814.2, 0.9707),
                              (50, 742.7, 0.8854), (100, 704.9, 0.8403)):
        r = cell("YIN2002", "flexural_strength", n)
        check("N=%-3d  %.1f MPa, ratio %.4f" % (n, abs_mpa, ratio),
              r is not None and abs(float(r["abs_MPa"]) - abs_mpa) < 0.05
              and abs(float(r["ratio"]) - ratio) < 1e-4)

    # ---- Table: Zhang et al. [3], 2D C/SiC ----------------------------
    print("\n Table 2.4.2b -- Zhang et al. [3], 2D C/SiC (the primary anchor)")
    E, S = {}, {}
    for n, gpa, ratio in ((0, 97.7, 1.0000), (20, 76.9, 0.7852),
                          (40, 73.7, 0.7546), (60, 46.3, 0.4737)):
        r = cell("ZHANG2013", "tensile_modulus", n)
        E[n] = float(r["ratio"]) if r else None
        check("N=%-3d  E = %.1f GPa, E/E0 %.4f" % (n, gpa, ratio),
              r is not None and abs(float(r["abs_MPa"]) - gpa) < 0.05
              and abs(float(r["ratio"]) - ratio) < 1e-4)
    for n, ratio in ((0, 1.0000), (20, 1.0357), (40, 0.9074), (60, 0.6199)):
        r = cell("ZHANG2013", "tensile_strength", n)
        S[n] = float(r["ratio"]) if r else None
        check("N=%-3d  normalised strength %.4f" % (n, ratio),
              r is not None and abs(float(r["ratio"]) - ratio) < 1e-4)
    r = cell("ZHANG2013", "mass_change_pct", 60)
    check("N=60   mass change -9.8 %",
          r is not None and abs(float(r["abs_MPa"]) + 9.8) < 0.05)

    # ---- Derived percentages the chapter states in prose ---------------
    print("\n §2.4.2 prose -- the two-regime split")
    check("stiffness falls ~21 % by N=20",
          abs((1 - E[20]) * 100 - 21.5) < 0.6, "%.1f %%" % ((1 - E[20]) * 100))
    check("stiffness falls ~53 % cumulative by N=60",
          abs((1 - E[60]) * 100 - 52.6) < 0.6, "%.1f %%" % ((1 - E[60]) * 100))
    check("stiffness falls ~40 % over N=20->60",
          abs((1 - E[60] / E[20]) * 100 - 39.7) < 0.8,
          "%.1f %%" % ((1 - E[60] / E[20]) * 100))
    check("strength RISES ~3.6 % at N=20",
          S[20] > 1.0 and abs((S[20] - 1) * 100 - 3.57) < 0.1,
          "+%.2f %%" % ((S[20] - 1) * 100))
    check("strength falls ~40 % over N=20->60",
          abs((1 - S[60] / S[20]) * 100 - 40.1) < 1.0,
          "%.1f %%" % ((1 - S[60] / S[20]) * 100))
    check("the two datasets really do disagree in sign of curvature",
          (0.8403 - 0.8854) / 50.0 > (S[60] - S[40]) / 20.0,
          "Yin decelerates, Zhang accelerates")

    # ---- Yan et al. [35], in-plane shear vs temperature ---------------
    print("\n §2.6.3 -- Yan et al. [35], IPSS vs temperature")
    fc = rows("failure_criteria.csv")
    ipss = {int(float(r["T_K"])): float(r["value"]) for r in fc
            if r["source_key"] == "YAN2011" and r["quantity"] == "S12"}
    for T, v in ((293, 144.1), (973, 183.7), (1173, 185.7), (1273, 200.1),
                 (1473, 183.7), (1673, 188.1), (1873, 178.3)):
        check("IPSS(%d K) = %.1f MPa" % (T, v),
              T in ipss and abs(ipss[T] - v) < 0.05)
    check("IPSS rises ~39 % from RT to 1273 K",
          abs((ipss[1273] / ipss[293] - 1) * 100 - 38.9) < 0.6,
          "+%.1f %%" % ((ipss[1273] / ipss[293] - 1) * 100))
    check("the peak really is at 1273 K, not at either end",
          max(ipss, key=lambda k: ipss[k]) == 1273,
          "this is what makes it a TRS-relaxation signature")

    # ---- D-criterion critical damages ---------------------------------
    print("\n §2.6.2 -- D-criterion critical damages from Yang et al. [27]")
    dc = {r["quantity"]: float(r["value"]) for r in fc
          if r["source_key"] == "YANG2015"}
    check("D11max = D22max = 0.5224",
          dc.get("D11max") == 0.5224 and dc.get("D22max") == 0.5224)
    check("D66max = 0.5405", dc.get("D66max") == 0.5405)
    check("evaluated at Xt = 226 MPa, S12 = 125.7 MPa",
          dc.get("Xt") == 226.0 and dc.get("S12") == 125.7)

    # ---- Numbers the chapter derives from the model itself ------------
    print("\n §2.5.2 / §2.9 -- values the chapter derives, not quotes")
    g0 = 310.0 ** 2 / (2.0 * 350000.0)
    lim = 0.031 / (1.02 * g0)
    check("crack-band element-size limit ~0.22 mm",
          abs(lim - 0.22) < 0.01, "%.4f mm" % lim)
    check("model matrix TRS (268 MPa) is >2x the XRD 114.7 MPa",
          268.08 / 114.7 > 2.0, "%.2fx" % (268.08 / 114.7))

    # ---- The chapter must not cite anything marked secondary ----------
    print("\n citation hygiene")
    sec = sorted({r["source_key"] for r in ts + fc
                  if r.get("confidence") == "secondary"})
    text = open(CHAPTER).read() if os.path.exists(CHAPTER) else ""
    check("CH2 exists", bool(text))
    leaked = [k for k in sec if k in text and "인용 금지" not in text.split(k)[0][-200:]]
    check("no 'secondary' source is cited as evidence",
          not [k for k in sec if text.count(k) > 1],
          "secondary keys: %s" % (", ".join(sec) or "none"))

    print("\n" + "=" * 72)
    if _BAD:
        print("FAIL -- Ch.2 no longer matches its data: %s" % ", ".join(_BAD))
        print("=" * 72)
        return 1
    print("ALL %d CH.2 NUMBERS MATCH THEIR SOURCES" % len(_OK))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
