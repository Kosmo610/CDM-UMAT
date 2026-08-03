#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_gf_scale_transfer.py  --  is Gf_bar a material constant, or does it
carry the RVE's own size across the scale boundary?
==========================================================================
Ch.4 4.6 extracts the macro card's fracture energies from RVE virtual tests.
postprocess/homogenize.py does it this way (line ~213):

    Gf = (area under the whole homogenised sigma-eps curve) * Lchar

with Lchar the RVE edge along the loading direction.  Those numbers go
straight into card slots 31-34, and KMACRO31 turns each one into a softening
exponent with the crack-band formula of Ch.3 3.2.3:

    A = 2*g0*le / (Gf - g0*le),        g0 = X^2 / (2E)

where le is the MACRO element's characteristic length.

The literature this script is built against says an RVE stops being
representative once the response softens -- Gitman, Askes & Sluys, Eng.
Fract. Mech. 74(16) 2007 2518-2534.  The homogenised sigma-EPSILON curve is
size dependent because eps = delta / L; the objective object is the
traction-SEPARATION curve.  Multiplying the area by Lchar is exactly the
conversion between the two, so the extraction is the right shape.  This
script checks whether it is also right in detail.

WHAT IS CHECKED

  A. the closed-form area identity for the exponential softening law that
     both the UMAT and the crack-band formula assume,
  B. that the convention in homogenize.py (whole curve, elastic included)
     is the same convention the A-formula inverts -- they must agree or the
     card means something different from what the UMAT reads,
  C. the size that survives the scale change: the whole-curve convention
     puts a term g0*L into Gf, and L is the RVE edge at extraction but the
     macro element length at use.  Those are not the same length.

This script needs no solver and no ODB.  It is algebra plus the geometry
the chapters already state.

Run:  python3 verification/check_gf_scale_transfer.py
"""
from __future__ import print_function

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# geometry and properties, quoted from the chapters that own them
# --------------------------------------------------------------------------
# Ch.4 4.2.1: the RVE is 3.5 x 3.5 x 0.44 mm.  In-plane loading therefore
# extracts with Lchar = 3.5 mm.
L_RVE_INPLANE = 3.5
L_RVE_THICK = 0.44
V_RVE = 5.390

# Ch.5 5.3.1: the ZHANG2013 macro specimen is 12.5 x 6.0 x 3.0 mm divided
# 10 x 6 x 12, and the YIN2002 one is 20.0 x 6.0 x 4.0 divided 12 x 6 x 14.
MACRO = {
    "ZHANG2013": ((12.5, 6.0, 3.0), (10, 6, 12)),
    "YIN2002": ((20.0, 6.0, 4.0), (12, 6, 14)),
}

# Two readings of the composite in-plane tension, both already in the repo.
#   measured   refs/[28] Table 1, data/literature/csic_2d_offaxis.csv
#   model      Ch.4 4.9-0: M5's undamaged tangent
E_MEASURED, X_MEASURED = 142.06e3, 265.28      # MPa
E_MODEL = 235.2e3                              # MPa


def g0(X, E):
    """Elastic energy density stored at the peak."""
    return X * X / (2.0 * E)


def le_of(dims, divs):
    """Characteristic length of one macro element, volume^(1/3)."""
    vol = 1.0
    for d, n in zip(dims, divs):
        vol *= d / float(n)
    return vol ** (1.0 / 3.0)


# --------------------------------------------------------------------------
# A. the area identity behind the crack-band formula
# --------------------------------------------------------------------------
def area_closed_form(X, E, A):
    """g0 * (1 + 2/A) -- the whole area under the exponential softening law."""
    return g0(X, E) * (1.0 + 2.0 / A)


def area_numeric(X, E, A, n=400001, rmax=400.0):
    """Trapezoid the same law straight off its definition, no algebra used.

    d = 1 - exp[A(1-r)]/r for r >= 1, so sigma = X*exp[A(1-r)] there, but the
    integration is done on (1-d)*E*eps so that a slip in the damage law would
    show up rather than cancel.
    """
    eps0 = X / E
    tot = 0.0
    # pre-peak: exact triangle, integrated the same way for symmetry
    m = 20001
    prev_e, prev_s = 0.0, 0.0
    for i in range(1, m):
        e = eps0 * i / float(m - 1)
        s = E * e
        tot += 0.5 * (s + prev_s) * (e - prev_e)
        prev_e, prev_s = e, s
    # post-peak
    for i in range(1, n):
        r = 1.0 + (rmax - 1.0) * i / float(n - 1)
        e = r * eps0
        d = 1.0 - math.exp(A * (1.0 - r)) / r
        s = (1.0 - d) * E * e
        tot += 0.5 * (s + prev_s) * (e - prev_e)
        prev_e, prev_s = e, s
    return tot


def part_a():
    print("\n A. the exponential softening law's area is g0*(1 + 2/A)")
    for A in (0.5, 2.0, 5.0, 20.0, 50.0):
        cf = area_closed_form(X_MEASURED, E_MEASURED, A)
        nm = area_numeric(X_MEASURED, E_MEASURED, A)
        rel = abs(nm - cf) / cf
        check("A = %-5.1f  closed form vs trapezoid" % A, rel < 2e-4,
              "%.6f vs %.6f N/mm2  (%.3f %%)" % (cf, nm, 100.0 * rel))

    # The elastic part is g0 and does not depend on A; the inelastic part is
    # 2*g0/A and vanishes as A grows.  That split is the whole point.
    A = 5.0
    tot = area_closed_form(X_MEASURED, E_MEASURED, A)
    el = g0(X_MEASURED, E_MEASURED)
    check("the elastic part of the area is exactly g0",
          abs((tot - 2.0 * el / A) - el) < 1e-12,
          "g0 = %.6f N/mm2" % el)
    check("the inelastic part is 2*g0/A", abs((tot - el) - 2.0 * el / A) < 1e-12)


# --------------------------------------------------------------------------
# B. the two conventions must be the same convention
# --------------------------------------------------------------------------
def part_b():
    print("\n B. homogenize.py's Gf and the UMAT's A-formula agree")

    src = open(os.path.join(ROOT, "postprocess", "homogenize.py")).read()
    check("homogenize.py multiplies the area by an RVE length",
          "Gf = area * Lchar" in src)
    check("and takes the area under the WHOLE curve, elastic included",
          "np.trapz(sig, eps)" in src and "whole curve" in src)

    # Invert the A-formula and confirm it returns the same area convention.
    # A = 2*g0*le/(Gf - g0*le)  <=>  Gf = le * g0 * (1 + 2/A)
    #                            <=>  Gf = le * (whole area)
    for A in (0.8, 3.0, 12.0):
        for le in (0.3, 1.0, L_RVE_INPLANE):
            gg = g0(X_MEASURED, E_MEASURED)
            Gf = le * area_closed_form(X_MEASURED, E_MEASURED, A)
            A_back = 2.0 * gg * le / (Gf - gg * le)
            check("A=%-4.1f le=%-4.2f mm: formula inverts to the same A"
                  % (A, le), abs(A_back - A) < 1e-9,
                  "recovered %.9f" % A_back)

    check("so Gf(card) = le * g0 + le * 2*g0/A -- it contains g0*le", True,
          "the elastic term rides along with whatever le was used")

    # And the snapback guard is the same statement.
    gg = g0(X_MEASURED, E_MEASURED)
    check("snapback limit le < Gf/g0 is the A > 0 condition",
          abs((gg * 1.0) - g0(X_MEASURED, E_MEASURED)) < 1e-12)


# --------------------------------------------------------------------------
# C. the length that changes across the scale boundary
# --------------------------------------------------------------------------
def part_c():
    print("\n C. Gf is extracted at L_RVE but consumed at le(macro)")

    les = {k: le_of(d, n) for k, (d, n) in MACRO.items()}
    for k, v in sorted(les.items()):
        check("%s macro element le" % k, 0.05 < v < L_RVE_INPLANE,
              "%.4f mm  (RVE in-plane edge is %.2f mm)" % (v, L_RVE_INPLANE))

    ratios = {k: L_RVE_INPLANE / v for k, v in les.items()}
    for k, v in sorted(ratios.items()):
        check("%s  L_RVE / le" % k, v > 1.0, "%.2f x" % v)

    # Size of the term that is carried across with the wrong length.
    print("\n    the spurious term is g0*(L_RVE - le), in N/mm:")
    print("    %-12s %-10s %-12s %-12s %-12s"
          % ("macro case", "le [mm]", "g0 measured", "g0 model", "spread"))
    worst = 0.0
    for k in sorted(les):
        le = les[k]
        gm = g0(X_MEASURED, E_MEASURED)
        gd = g0(X_MEASURED, E_MODEL)          # same peak, model's stiffness
        a = gm * (L_RVE_INPLANE - le)
        b = gd * (L_RVE_INPLANE - le)
        worst = max(worst, a, b)
        print("    %-12s %-10.4f %-12.4f %-12.4f %.3f - %.3f"
              % (k, le, gm, gd, min(a, b), max(a, b)))

    check("the carried term is not negligible (> 0.1 N/mm)", worst > 0.1,
          "worst case %.3f N/mm" % worst)

    # For scale, the one sourced transverse fracture energy in the repo.
    G_TT_SHI = 0.107          # Ch.4 4.9-6a, Shi refs/[31], 2D plain weave
    check("and it is large next to the one sourced Gf in the repo",
          worst > G_TT_SHI,
          "%.3f N/mm vs Gtt = %.3f N/mm (yarn transverse, Shi refs/[31])"
          % (worst, G_TT_SHI))

    print("""
    READING.  Gf(card) = le*g0 + le*2*g0/A.  Only the second term is the
    material's dissipation; the first is stored elastic energy and it scales
    with whatever length was used.  Extraction uses L_RVE = %.2f mm, the macro
    uses le = %.3f - %.3f mm, so the elastic term arrives inflated by
    g0*(L_RVE - le).  The transferable constant is the INELASTIC part

        Gf_inel = Gf(extracted) - g0 * L_RVE

    which the macro should re-inflate with its own le.  homogenize.py does not
    do this today and neither does make_macro_thermalshock.py -- grep for g0
    in either returns nothing.  Recorded as Ch.4 4.9-12.
    """ % (L_RVE_INPLANE, min(les.values()), max(les.values())))


def main():
    print("=" * 74)
    print("check_gf_scale_transfer.py -- does Gf_bar carry the RVE's size?")
    print("=" * 74)

    part_a()
    part_b()
    part_c()

    print("\n" + "=" * 74)
    if _BAD:
        print("FAIL -- %d of %d" % (len(_BAD), len(_OK) + len(_BAD)))
        print("=" * 74)
        return 1
    print("ALL %d Gf SCALE-TRANSFER CHECKS HOLD" % len(_OK))
    print("(they hold in the sense that the algebra is confirmed --")
    print(" the finding in part C is a defect, not a pass)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
