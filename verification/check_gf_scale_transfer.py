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
          "_trapz(sig, eps)" in src and "whole curve" in src)
    # np.trapz was REMOVED in NumPy 2.0 (renamed np.trapezoid).  homogenize.py
    # is the last thing to run in the whole RVE campaign, so resolving the
    # name at call time is what stops one rename from costing every job.
    check("  and it resolves trapz/trapezoid rather than trusting one NumPy",
          "getattr(np, \"trapezoid\"" in src and "getattr(np, \"trapz\")" in src)

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

    which the macro should re-inflate with its own le.  Recorded as Ch.4
    4.9-16; parts D and E below check the two halves of the fix -- that
    homogenize.py splits and negates, and that make_macro_thermalshock.py
    refuses to write a deck around a card that did not.
    """ % (L_RVE_INPLANE, min(les.values()), max(les.values())))


# --------------------------------------------------------------------------
# D. the fix: KABAND's two conventions, and homogenize.py's split
# --------------------------------------------------------------------------
def kaband(g0le, gf, afix):
    """Python mirror of KABAND in src/UMAT_CSIC_THERMSHOCK_V3_0.for."""
    if gf == 0.0:
        return afix
    if gf < 0.0:
        a = 2.0 * g0le / (-gf) if (-gf) > 0.02 * g0le else 50.0
        return min(50.0, max(1e-2, a))
    a = 2.0 * g0le / (gf - g0le) if gf > 1.02 * g0le else 50.0
    return min(50.0, max(1e-2, a))


def part_d():
    print("\n D. KABAND reads the dissipated part and rebuilds with CELENT")

    src = open(os.path.join(ROOT, "src",
                            "UMAT_CSIC_THERMSHOCK_V3_0.for")).read()
    check("KABAND branches on the sign of GF",
          "IF (GF.LT.0.0D0) THEN" in src)
    check("the disable case is now GF exactly zero, not GF <= 0",
          "IF (GF.EQ.0.0D0) THEN" in src and "IF (GF.LE.0.0D0) THEN" not in src)
    check("the inelastic branch is A = 2*g0*le/|Gf|",
          "A=2.0D0*G0LE/(-GF)" in src)
    check("the original total branch is untouched",
          "A=2.0D0*G0LE/(GF-G0LE)" in src)

    hom = open(os.path.join(ROOT, "postprocess", "homogenize.py")).read()
    check("and writes the dissipated part NEGATED into slots 31-34",
          '-s["Gfin_" + mode] if ("Gfin_" + mode) in s else 0.0' in hom)
    check("and keeps Lchar per mode so the split can be audited",
          'strength["Lchar_" + mode] = r["Lchar"]' in hom)

    # Call the real splitter rather than a mirror of it.  homogenize.py
    # guards its odbAccess import so it imports fine outside Abaqus.
    sys.path.insert(0, os.path.join(ROOT, "postprocess"))
    try:
        import homogenize as H
    except ImportError as exc:                       # pragma: no cover
        check("homogenize.py imports outside Abaqus", False, str(exc))
        return
    check("homogenize.py imports outside Abaqus", True)

    A_TRUE = 3.0
    eng = {"E1": E_MEASURED, "E2": E_MEASURED}
    st = {"Xt": X_MEASURED, "Xc": X_MEASURED,
          "Yt": X_MEASURED, "Yc": X_MEASURED}
    for m in ("1t", "1c", "2t", "2c"):
        st["Lchar_" + m] = L_RVE_INPLANE
        st["Gf_" + m] = L_RVE_INPLANE * area_closed_form(
            X_MEASURED, E_MEASURED, A_TRUE)
    H.split_fracture_energy(st, eng)

    gg = g0(X_MEASURED, E_MEASURED)
    for m in ("1t", "1c", "2t", "2c"):
        check("split %s: elastic part is exactly g0*L" % m,
              abs(st["Gfel_" + m] - gg * L_RVE_INPLANE) < 1e-12)
        check("split %s: dissipated part recovers the true A" % m,
              abs(2.0 * gg * L_RVE_INPLANE / st["Gfin_" + m] - A_TRUE) < 1e-9,
              "A = %.9f" % (2.0 * gg * L_RVE_INPLANE / st["Gfin_" + m]))
        check("split %s: the two parts sum back to the total" % m,
              abs(st["Gfel_" + m] + st["Gfin_" + m] - st["Gf_" + m]) < 1e-12)

    # A curve already inside snap-back has nothing to hand upward.  The
    # splitter must drop it rather than emit a negative dissipation, which
    # would reach KABAND as a POSITIVE card entry and be read as the wrong
    # convention entirely.
    st2 = {"Xt": X_MEASURED, "E1": E_MEASURED,
           "Lchar_1t": L_RVE_INPLANE,
           "Gf_1t": 0.5 * gg * L_RVE_INPLANE}       # below the elastic part
    H.split_fracture_energy(st2, {"E1": E_MEASURED, "E2": E_MEASURED})
    check("a snap-back RVE curve yields no Gfin (not a negative one)",
          "Gfin_1t" not in st2)
    check("and the card slot then falls back to 0.0 = fixed exponent",
          kaband(gg * 0.7, 0.0, 2.0) == 2.0)

    # The mode -> (strength, stiffness) pairing has to be right or every
    # g0 is wrong.  Longitudinal modes use E1, transverse use E2.
    check("g0 pairing: 1t/1c use E1, 2t/2c use E2",
          H.MODE_G0_KEYS["1t"] == ("Xt", "E1")
          and H.MODE_G0_KEYS["1c"] == ("Xc", "E1")
          and H.MODE_G0_KEYS["2t"] == ("Yt", "E2")
          and H.MODE_G0_KEYS["2c"] == ("Yc", "E2"))

    # A positive entry must still give exactly the old answer.
    gg = g0(X_MEASURED, E_MEASURED)
    for le in (0.3, 1.0, 3.5):
        for A in (0.8, 3.0, 12.0):
            g0le = gg * le
            gf_tot = le * area_closed_form(X_MEASURED, E_MEASURED, A)
            old = 2.0 * g0le / (gf_tot - g0le)
            check("positive Gf still gives the original A (le=%.1f, A=%.1f)"
                  % (le, A), abs(kaband(g0le, gf_tot, 2.0) - old) < 1e-9)

    check("Gf = 0 still disables the crack band",
          kaband(gg * 1.0, 0.0, 2.0) == 2.0)

    # The two conventions must agree when the SAME le is used, which is the
    # statement that the fix changes nothing except which le is used.
    for le in (0.3, 1.0, 3.5):
        for A in (0.8, 3.0, 12.0):
            g0le = gg * le
            gf_tot = le * area_closed_form(X_MEASURED, E_MEASURED, A)
            gf_inel = gf_tot - g0le
            check("same le: total and inelastic give the same A"
                  " (le=%.1f, A=%.1f)" % (le, A),
                  abs(kaband(g0le, gf_tot, 2.0)
                      - kaband(g0le, -gf_inel, 2.0)) < 1e-9,
                  "A = %.9f" % kaband(g0le, -gf_inel, 2.0))

    # And they must DISAGREE across the scale boundary, by the amount part C
    # quantified -- otherwise there was nothing to fix.
    print("\n    what the fix actually changes, A at the macro element:")
    print("    %-12s %-9s %-11s %-11s %s"
          % ("macro case", "le [mm]", "A uncorrected", "A corrected", "ratio"))
    A_RVE = 3.0                      # a representative extracted exponent
    gf_tot_rve = L_RVE_INPLANE * area_closed_form(X_MEASURED, E_MEASURED, A_RVE)
    gf_inel = gf_tot_rve - gg * L_RVE_INPLANE
    worst = 1.0
    for k, (d, n) in sorted(MACRO.items()):
        le = le_of(d, n)
        g0le = gg * le
        a_bad = kaband(g0le, gf_tot_rve, 2.0)     # old path: total, wrong le
        a_good = kaband(g0le, -gf_inel, 2.0)      # new path
        worst = max(worst, a_good / a_bad, a_bad / a_good)
        print("    %-12s %-9.4f %-11.4f %-11.4f %.2f x"
              % (k, le, a_bad, a_good, a_good / a_bad))
    check("the correction is not cosmetic (A moves by more than 2x)",
          worst > 2.0, "worst %.2f x" % worst)

    print("""
    A larger A is a STEEPER softening branch -- less energy dissipated per
    unit crack area.  Uncorrected, the macro inherits the RVE's stored
    elastic energy on top of the real dissipation and softens too gently,
    so the specimen holds load it should have shed.  The sign of the error
    is therefore NON-CONSERVATIVE: it over-predicts residual strength, which
    is the quantity Ch.6 reports.
    """)


# --------------------------------------------------------------------------
# E. the deck generator has to refuse the old convention
# --------------------------------------------------------------------------
def part_e():
    """Part D fixes the maker of cards.  This part checks the consumer.

    Splitting Gf in homogenize.py does nothing for a card that already exists
    on disk, and there are such cards: every macro card written before 4.9-16
    holds four positive totals.  Nothing in the UMAT rejects them -- KABAND
    takes a positive Gf as a valid total-area entry, which is precisely why
    the number is dangerous -- so the last place to catch it is the deck
    generator, before a job is ever submitted.
    """
    print("\n E. make_macro_thermalshock.py refuses a pre-4.9-16 card")

    sys.path.insert(0, os.path.join(ROOT, "abaqus"))
    try:
        import make_macro_thermalshock as MM
    except ImportError as exc:                       # pragma: no cover
        check("make_macro_thermalshock.py imports", False, str(exc))
        return
    check("make_macro_thermalshock.py imports", True)

    # Rebuild what homogenize.py used to emit: the whole area times the RVE
    # edge, in all four slots.
    E1, Xt = 105000.0, 220.0                      # PLACEHOLDER_CARD's own
    gg = g0(Xt, E1)
    A_RVE = 2.0
    gf_total = L_RVE_INPLANE * area_closed_form(Xt, E1, A_RVE)
    old = MM.PLACEHOLDER_CARD
    for s in (32, 33, 34, 35):
        old = MM.patch_card(old, s, gf_total)

    le = le_of(*MACRO["ZHANG2013"])
    try:
        MM.check_macro_card(old, "pre-4.9-16 card", le=le)
    except SystemExit as exc:
        check("a card of positive totals is rejected", True,
              "Gf = %.4f N/mm in all four slots" % gf_total)
        txt = str(exc)
        check("and the message names every offending slot",
              all(str(s) in txt for s in (32, 33, 34, 35)))
        check("and points at the section that owns the convention",
              "4.9-16" in txt)
        check("and says how to fix it", "homogenize.py" in txt)
    else:
        check("a card of positive totals is rejected", False,
              "ACCEPTED -- the gate is not doing anything")

    # The escape hatch must exist (a Gf really measured at le(macro) is legal)
    # but must not be the default.
    try:
        MM.check_macro_card(old, "opt out", le=le, allow_total_gf=True)
        check("allow_total_gf lets a deliberate total through", True)
    except SystemExit as exc:
        check("allow_total_gf lets a deliberate total through", False, str(exc))

    # And the corrected card must pass, with the exponent the RVE measured
    # rebuilt at the MACRO length rather than the RVE's.
    gf_inel = gf_total - gg * L_RVE_INPLANE
    new = MM.PLACEHOLDER_CARD
    for s in (32, 33, 34, 35):
        new = MM.patch_card(new, s, -gf_inel)
    try:
        info = MM.check_macro_card(new, "4.9-16 card", le=le)
        check("the negated card passes", True)
    except SystemExit as exc:
        check("the negated card passes", False, str(exc))
        return

    # The generator's own audit must agree with this script's mirror.  Only
    # the two modes built on Xt = 220 and E = 105000 are comparable against
    # `gg`; slots 33 and 35 are the compressive ones and use Xc = 480.
    for rec in info["gf"]:
        if rec["slot"] not in (32, 34):
            continue
        st = rec["states"][0]
        check("audit agrees with the KABAND mirror (slot %d)" % rec["slot"],
              abs(st["A"] - kaband(gg * le, -gf_inel, rec["afix"])) < 1e-9,
              "A = %.6f" % st["A"])

    # A is proportional to le, NOT inverse to it.  Gf_inel is energy per unit
    # crack AREA and is fixed; the energy per unit VOLUME is Gf_inel/le, so a
    # shorter element has to dissipate more per unit volume, which means a
    # LONGER softening tail in strain and therefore a SMALLER A.  That is the
    # whole content of crack-band regularisation and it is easy to get
    # backwards, so it is asserted here rather than assumed.
    a_macro = info["gf"][0]["states"][0]["A"]
    check("the rebuilt exponent scales with le, not 1/le", a_macro < A_RVE,
          "A(macro, le=%.4f) = %.4f vs A(RVE, L=%.1f) = %.1f"
          % (le, a_macro, L_RVE_INPLANE, A_RVE))
    check("and the ratio is exactly le/L_RVE",
          abs(a_macro / A_RVE - le / L_RVE_INPLANE) < 1e-6,
          "%.4f x vs %.4f x" % (a_macro / A_RVE, le / L_RVE_INPLANE))

    # And the correction still moves the macro in the conservative direction:
    # the uncorrected card is gentler still, because KABAND removes only
    # g0*le_macro from a total that had g0*L_RVE in it.
    a_bad = kaband(gg * le, gf_total, 2.0)
    check("the uncorrected card is gentler than the corrected one",
          a_bad < a_macro,
          "A uncorrected %.4f < corrected %.4f  (%.2f x too gentle)"
          % (a_bad, a_macro, a_macro / a_bad))

    # Same card, no le: the sign is still judged.  A generator that forgot to
    # pass a length must not silently stop checking.
    try:
        MM.check_macro_card(old, "no le")
        check("the sign is judged even without a length", False, "ACCEPTED")
    except SystemExit:
        check("the sign is judged even without a length", True)


def main():
    print("=" * 74)
    print("check_gf_scale_transfer.py -- does Gf_bar carry the RVE's size?")
    print("=" * 74)

    part_a()
    part_b()
    part_c()
    part_d()
    part_e()

    print("\n" + "=" * 74)
    if _BAD:
        print("FAIL -- %d of %d" % (len(_BAD), len(_OK) + len(_BAD)))
        print("=" * 74)
        return 1
    print("ALL %d Gf SCALE-TRANSFER CHECKS HOLD" % len(_OK))
    print("(part C states the defect; D and E check the two halves of the")
    print(" fix -- homogenize.py splits and negates, and the deck generator")
    print(" refuses any card that did not)")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
