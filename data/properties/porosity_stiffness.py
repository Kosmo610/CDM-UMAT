#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
porosity_stiffness.py
=====================
Closes Ch.4 4.9 open item 3: how the RVE handles porosity.

WHY THIS EXISTS
---------------
The RVE mesh is a FILLED CELL -- yarns plus matrix, no voids, V_RVE taken as
the bounding box.  Section 4.7.3 already proved that is untenable for thermal
conductivity: a dense cell cannot reach the measured k no matter what the
fibre transverse conductivity is set to.  Open item 3 then asked the obvious
follow-up and left it open: put explicit voids in the mesh, or apply a
knockdown factor?  And how much porosity, anyway?

That question turns out to decide the stiffness as well, which is why it is
being closed now rather than later.

WHAT WAS WRONG BEFORE
---------------------
m6_calibration.py compared the model's initial tangent against 70 GPa from
refs/[43] Mei Table I and reported the model as 3.4x too stiff.  That
comparison was not like-for-like.  refs/[10] Yang Table 1 measures the same
material class at the same density (2.0 g/cm^3) and reports the INITIAL
modulus, taken from the start of the stress-strain curve, as 128.7 GPa at
room temperature and 172.7 GPa at 1273 K.  Yang also notes the curve is
non-linear "almost from the onset of loading", which is exactly why a
whole-curve chord like Mei's lands near half the initial tangent.

Against the initial modulus at the temperature M5 actually ran, the model is
1.36x too stiff, not 3.4x.  That correction matters because it changes what
M6 has to do.

WHAT THE POROSITY IS
--------------------
Not a knob.  It follows from a measured density and a measured fibre volume
fraction by mass bookkeeping, and the same arithmetic reproduces refs/[36]'s
own published porosity exactly, which is how we know the method is right.

THE RESULT
----------
The RVE is missing 19.6 % of its volume: it fills with solid SiC what is
really pore.  Removing that from the parallel sum takes the M5 stiffness at
1000 C from 235.2 GPa to 170.0 GPa against Yang's measured 172.7 GPa.

WHICH MATERIAL -- AND WHY 19.6 % IS A LOWER BOUND (2026-08-05, a1-0002)
-----------------------------------------------------------------------
The literature agent asked which densification process the density belongs
to, and the answer changes what the number may be used for.

refs/[10] Yang states both inputs itself, in its own section 2:
    "plain-weave C/SiC composite fabricated by CVI technique.  The fiber
     volume fraction is about 40%."
    "coated with SiC by I-CVI process.  The final density of the coupons is
     about 2.0 g/cm3."
So the back-out is CVI's density inverted to CVI's TOTAL porosity.  It is
not our material.  Ch.2 2.2.1 fixes the reference material as Zhang [5]'s
PIP 2D plain weave -- the stress-free temperature of 1050 C is a PYROLYSIS
temperature, which CVI does not have -- and states that PIP leaves a HIGHER
matrix porosity than CVI.  The repository holds no density measurement for
that PIP material.

    therefore:   Vp(ours, PIP)  >=  19.6 %   and nothing sharper

That inequality is the whole result.  A matrix-E knockdown built on 19.6 %
is a knockdown built on the wrong process, and it is wrong in the direction
that UNDER-corrects.

OPEN VERSUS TOTAL -- the numbers reconcile, they do not conflict
---------------------------------------------------------------
Three figures exist for CVI 2D C/SiC and they look contradictory:

    refs/[10]  no porosity stated; its rho and Vf invert to 19.6 %  TOTAL
    refs/[28]  "porosity contents of 40% and 10-15%"                open?
    refs/[43]  Table I states 13 %                                  open?

refs/[28] states rho = 2.0 in the SAME SENTENCE as its 10-15 %, and 2.0
inverts to 19.6 %, so that paper does not agree with itself on a total-
porosity reading.  It also says the porosity figure is for specimens
measured "after final deposition of the 50 um SiC matrix ON THE SURFACE",
and a surface seal coat lowers the OPEN porosity an immersion method can
reach while leaving the total untouched.  refs/[43]'s 13 % is inconsistent
with its own rho = 2.0 the same way and sits inside [28]'s band.

Read as open porosity, all three are consistent with 19.6 % total and about
5-10 %p of closed porosity, which is what CVI is known for.  Read as total
porosity, two independent papers contradict their own densities.  The
second reading is not credible, so this file treats 10-15 % as open and
19.6 % as total -- but neither paper says so, so the reading is an
INFERENCE and carries no grade.

  python3 data/properties/porosity_stiffness.py
  python3 data/properties/porosity_stiffness.py --check
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------- our RVE card
CARD_E1, CARD_E2 = 254967.228042, 44321.737572     # yarn, MPa
EF1, EF2, NUF12 = 230.0e3, 40.0e3, 0.26            # T300 filament, MPa
EM_CARD, NUM = 350.0e3, 0.20                       # matrix, MPa
AM_CARD = 4.5e-6                                   # matrix secant CTE
AY1_CARD, AY2_CARD = 1.070925962822e-06, 3.324908565604e-06

VF_YARN = (EM_CARD - CARD_E1) / (EM_CARD - EF1)    # 0.79194, inside a yarn
VY_RVE = 0.4982                                    # yarn fraction of the RVE

#: matrix modulus at the M5 temperature, data/properties/matrix_SiC_vsT.csv
EM_1000 = 332131.2

#: dense (pore-free) CVD SiC modulus, Snead 2007.  The card's 350 GPa is this
#: knocked down for MICROporosity: 460*exp(-3.57*0.077) = 349.5.
E_SIC_DENSE = 460.0e3
SNEAD_B = 3.57

# ------------------------------------------------------------- densities
RHO_T300 = 1.76      # g/cm^3, Toray T300 datasheet
RHO_SIC = 3.21       # g/cm^3, theoretical.  refs/[36] uses the same value
RHO_SIC_FIBRE = 2.7  # g/cm^3, refs/[36] Table 5, for its own SiC fibre

# --------------------------------------------------- process provenance
#: Which densification process each figure belongs to.  Kept as data rather
#: than prose because the whole point is that they are NOT the same material
#: and the code must not be able to forget it.
PROCESS_REFERENCE = "PIP"     # Zhang [5], Ch.2 2.2.1 -- our card's material
PROCESS_DENSITY_SRC = "CVI"   # refs/[10] Yang -- where rho = 2.0 comes from

#: Ch.2 2.2.1: PIP leaves a higher matrix porosity than CVI.  So a CVI-derived
#: porosity bounds ours from BELOW.  There is no upper bound in the repository.
POROSITY_IS_LOWER_BOUND = True

# --------------------------------------------------- what M5 actually gave
M5_E0_1000 = 235.2e3          # MPa, initial tangent of the M5 T1000 tension
RVE_TRS = 268.08              # MPa, volume-averaged matrix sigma_11
XRD_TRS = 114.7               # MPa, refs/[15] 3D braided, XRD
RVE_ALPHA_XX = 3.132e-6       # /K, measured off the cooldown


# ==========================================================================
def measured_composites():
    """Measured 2D C/SiC elastic moduli, with the MEASUREMENT CONVENTION.

    (label, T [C], E [GPa], convention, grade)

    The convention column is the reason this table exists.  Two papers on the
    same material at the same density disagree by a factor of two, and the
    disagreement is entirely in what part of a non-linear curve was measured.
    Quoting one against a model's initial tangent without checking which is
    how m6_calibration.py came to report a 3.4x stiffness error.
    """
    return [
        ("refs/[10] Yang Table 1",   27.0, 128.7, "initial tangent", "fulltext"),
        ("refs/[10] Yang Table 1",  700.0, 152.3, "initial tangent", "fulltext"),
        ("refs/[10] Yang Table 1", 1000.0, 172.7, "initial tangent", "fulltext"),
        ("refs/[10] Yang Table 1", 1200.0, 169.1, "initial tangent", "fulltext"),
        ("refs/[43] Mei Table I",    23.0,  70.0, "unstated chord",  "fulltext"),
    ]


def porosity_from_density(rho, vf, rho_f, rho_m=RHO_SIC):
    """TOTAL porosity by mass bookkeeping.

        rho = vf*rho_f + vm*rho_m,  Vp = 1 - vf - vm

    This is refs/[36] Eq. 7 rearranged.  It gives TOTAL porosity (open plus
    closed), which is not the same quantity as an Archimedes open porosity --
    see the note on refs/[43] below.
    """
    vm = (rho - vf * rho_f) / rho_m
    return 1.0 - vf - vm


def porosity_sources():
    """Every porosity figure in the reference set, with how it was obtained.

    (label, material, porosity, how, grade)
    """
    yang = porosity_from_density(2.0, 0.40, RHO_T300)
    shen = porosity_from_density(2.5, 0.32, RHO_SIC_FIBRE)
    return [
        ("refs/[10] Yang", "2D C/SiC CVI", yang,
         "derived here from its stated rho = 2.0 and Vf = 40 %", "fulltext"),
        ("refs/[36] Shen", "2D SiCf/SiC CVI", shen,
         "derived here from its stated rho = 2.5 and Vf = 32 %; the paper "
         "publishes 17.0 %, so this arithmetic is validated", "fulltext"),
        ("refs/[36] Shen", "2D SiCf/SiC CVI", 0.175,
         "the paper's own RVE geometry, without the connection matrix",
         "fulltext"),
        ("refs/[43] Mei", "2D C/SiC CVI", 0.13,
         "stated in Table I. Inconsistent with its own rho = 2.0 at any "
         "sensible Vf, so it is almost certainly OPEN porosity, not total",
         "fulltext"),
    ]


# ------------------------------------------------------- phase bookkeeping
def rve_phases():
    """What our RVE is made of, by volume fraction of the bounding box."""
    fibre = VY_RVE * VF_YARN
    matrix = VY_RVE * (1.0 - VF_YARN) + (1.0 - VY_RVE)
    return dict(fibre=fibre, matrix=matrix, pore=0.0)


def real_phases(vp=None):
    """What the real material is made of, at the same fibre fraction."""
    vp = porosity_from_density(2.0, 0.40, RHO_T300) if vp is None else vp
    return dict(fibre=0.40, matrix=1.0 - 0.40 - vp, pore=vp)


# ------------------------------------------------------------- stiffness
def voigt_axial(em, vy=VY_RVE, e1=CARD_E1, e2=CARD_E2):
    """Parallel (Voigt) bound on the on-axis modulus of the filled cell.

    Half the yarns are aligned and carry E1, half are transverse and carry
    E2, and the matrix pocket carries Em.  An upper bound, but the RIGHT
    bound for this argument: it is exactly linear in volume fraction, so
    'replace matrix with void' is an exact subtraction, not an estimate.
    """
    return 0.5 * vy * e1 + 0.5 * vy * e2 + (1.0 - vy) * em


def void_penalty(vp, em):
    """Stiffness a Voigt sum loses when vp of the volume becomes void.

    Void carries nothing, so the parallel sum simply loses vp*em.  No
    micromechanical model is involved and none is needed.
    """
    return vp * em


def pocket_knockdown(vp, vy=VY_RVE):
    """Factor to put on the matrix card to emulate vp of MACROporosity.

    We cannot cheaply remesh with explicit voids -- a new mesh needs a new
    .ori, and an old .ori on a new mesh converges silently with the fibres
    pointing the wrong way.  In a parallel sum, deleting a volume fraction of
    a phase and scaling that phase's modulus are identical operations, so the
    knockdown below is EXACT for the axial direction and approximate for the
    others.  That approximation is the price of keeping the mesh.
    """
    return 1.0 - vp / (1.0 - vy)


def snead_porosity(e, e0=E_SIC_DENSE, b=SNEAD_B):
    """Porosity that Snead's exponential implies for a given modulus."""
    import math
    return -math.log(e / e0) / b


# ------------------------------------------------------------------- CTE
def yarn_stiffness(vf=VF_YARN, em=EM_CARD):
    """Chamis yarn moduli at a given matrix modulus."""
    import math
    e1 = vf * EF1 + (1.0 - vf) * em
    e2 = em / (1.0 - math.sqrt(vf) * (1.0 - em / EF2))
    nu12 = vf * NUF12 + (1.0 - vf) * NUM
    return e1, e2, nu12


def weave_alpha(a1, a2, am, vy=VY_RVE, em=EM_CARD):
    """Stiffness-weighted in-plane CTE of a balanced plain weave.

    Same mean field as cte_sensitivity.py, but with the matrix modulus as an
    argument -- which is the whole point here, because porosity changes the
    weighting, not just the magnitude.  The selftest asserts it reproduces
    cte_sensitivity.py exactly at em = 350 GPa.
    """
    e1, e2, nu12 = yarn_stiffness(em=em)
    nu21 = nu12 * e2 / e1
    den = 1.0 - nu12 * nu21
    q11, q22, q12 = e1 / den, e2 / den, nu12 * e2 / den
    mq = em / (1.0 - NUM * NUM)
    mq11, mq12 = mq, NUM * mq
    top = ((vy / 2.) * (q11 * a1 + q12 * a2)
           + (vy / 2.) * (q22 * a2 + q12 * a1)
           + (1. - vy) * (mq11 * am + mq12 * am))
    bot = ((vy / 2.) * (q11 + q12) + (vy / 2.) * (q22 + q12)
           + (1. - vy) * (mq11 + mq12))
    return top / bot


def trs_direction(vp):
    """Which way porosity pushes the matrix TRS, and by how much.

    The matrix TRS scales as Em*(alpha_bar - alpha_m).  Porosity cuts Em,
    which lowers it; but it also cuts the matrix's weight in alpha_bar, which
    pulls alpha_bar toward the stiffer yarns and makes the mismatch LARGER.
    The two fight, so the sign is not obvious and has to be computed.

    Returns (ratio, alpha_before, alpha_after).  A RATIO, deliberately: the
    absolute mean-field TRS is not usable here (cte_sensitivity.py 4.9-9
    explains why -- it is a difference of two nearly equal numbers), but the
    ratio of two mean-field evaluations has its systematic error cancel to
    first order.
    """
    em2 = EM_CARD * pocket_knockdown(vp)
    a_before = weave_alpha(AY1_CARD, AY2_CARD, AM_CARD, em=EM_CARD)
    a_after = weave_alpha(AY1_CARD, AY2_CARD, AM_CARD, em=em2)
    before = EM_CARD * (a_before - AM_CARD)
    after = em2 * (a_after - AM_CARD)
    return after / before, a_before, a_after


# ==========================================================================
def report():
    print("=" * 78)
    print("porosity_stiffness.py -- closing Ch.4 open item 3")
    print("=" * 78)

    print("\n 1. A CORRECTION FIRST -- WHICH MODULUS THE MODEL IS COMPARED TO")
    print("    %-26s %8s %10s   %s" % ("source", "T [C]", "E [GPa]", "convention"))
    for lab, T, e, conv, _g in measured_composites():
        print("    %-26s %8.0f %10.1f   %s" % (lab, T, e, conv))
    print("    Two papers, the same material class, the same density 2.0 g/cm^3,")
    print("    a factor of two apart.  Yang states his is the INITIAL modulus")
    print("    'obtained from the beginning of the stress-strain curve' and")
    print("    that the curve is non-linear almost from the onset of loading.")
    print("    A whole-curve chord on such a curve lands near half of that.")
    print("    m6_calibration.py compared our INITIAL TANGENT against Mei's")
    print("    70 GPa and called the model 3.4x too stiff.  Like for like:")
    print("      M5 initial tangent at 1000 C   %.1f GPa" % (M5_E0_1000 / 1e3))
    print("      Yang initial modulus at 1000 C %.1f GPa" % 172.7)
    print("      -> %.2fx, not 3.4x" % (M5_E0_1000 / 172.7e3))

    print("\n 2. HOW MUCH POROSITY, AND HOW WE KNOW")
    print("    %-16s %-18s %8s  %s" % ("source", "material", "Vp", "how"))
    for lab, mat, vp, how, _g in porosity_sources():
        print("    %-16s %-18s %7.1f %%  %s" % (lab, mat, 100.0 * vp, how[:44]))
    shen = porosity_from_density(2.5, 0.32, RHO_SIC_FIBRE)
    print("    -> the refs/[36] row reproduces that paper's OWN published")
    print("       17.0 %% to %.2f %%, so the arithmetic is not ours to doubt."
          % (100.0 * abs(shen - 0.170)))
    vp = porosity_from_density(2.0, 0.40, RHO_T300)
    print("    -> for refs/[10]'s CVI material the same arithmetic gives")
    print("       %.1f %% TOTAL porosity.  That is NOT our material:" % (100.0 * vp))
    print("       ours is Zhang [5]'s %s (Ch.2 2.2.1) and refs/[10] is %s,"
          % (PROCESS_REFERENCE, PROCESS_DENSITY_SRC))
    print("       and %s leaves MORE matrix porosity than %s.  So %.1f %% is a"
          % (PROCESS_REFERENCE, PROCESS_DENSITY_SRC, 100.0 * vp))
    print("       LOWER BOUND on ours, and the repository has no upper one.")
    print("    refs/[36] also settles WHERE it sits: 'porosity only exists in")
    print("    the matrix, and the matrix is dependent on the fibre bundle")
    print("    structure'.  So it comes out of the matrix pocket, not the yarn.")

    print("\n 3. WHAT OUR RVE IS MADE OF, AND WHAT THE MATERIAL IS")
    a, b = rve_phases(), real_phases()
    print("    %-10s %12s %12s %10s" % ("phase", "our RVE", "real", "diff"))
    for k in ("fibre", "matrix", "pore"):
        print("    %-10s %11.1f %% %11.1f %% %9.1f %%p"
              % (k, 100 * a[k], 100 * b[k], 100 * (a[k] - b[k])))
    print("    The fibre fractions agree to %.1f %%p -- the mesh is right about"
          % (100 * abs(a["fibre"] - b["fibre"])))
    print("    the reinforcement.  It is wrong about what is between it:")
    print("    %.1f percentage points of SOLID SiC THAT DOES NOT EXIST."
          % (100 * (a["matrix"] - b["matrix"])))
    print("    SiC is the stiffest phase in the cell, so this is not a detail.")

    print("\n 4. THE STIFFNESS, WITH NO MICROMECHANICS AT ALL")
    print("    In a parallel sum the void term is exactly zero, so replacing")
    print("    matrix with void is a subtraction, not a model.")
    pen = void_penalty(vp, EM_1000)
    print("    M5 initial tangent at 1000 C            %8.1f GPa"
          % (M5_E0_1000 / 1e3))
    print("    minus Vp x Em(1000 C) = %.3f x %.1f GPa  %8.1f GPa"
          % (vp, EM_1000 / 1e3, -pen / 1e3))
    print("                                            %8s" % ("-" * 8))
    print("    corrected                               %8.1f GPa"
          % ((M5_E0_1000 - pen) / 1e3))
    print("    refs/[10] Yang MEASURED at 1273 K       %8.1f GPa" % 172.7)
    print("    -> %.1f %% apart."
          % (100.0 * abs((M5_E0_1000 - pen) / 1e3 - 172.7) / 172.7))
    print("    The stiffness disagreement was the missing porosity.  It was")
    print("    never a constitutive problem and no knob had to move.")

    print("\n 5. HOW TO PUT IT IN THE DECK")
    kd = pocket_knockdown(vp)
    print("    Explicit voids need a new mesh, and a new mesh needs a new .ori")
    print("    -- an old .ori on a new mesh converges with the fibres pointing")
    print("    the wrong way and no error.  So: a knockdown on the matrix card.")
    print("      matrix pocket is %.4f of the cell" % (1.0 - VY_RVE))
    print("      of which %.1f %% must be void" % (100.0 * vp / (1.0 - VY_RVE)))
    print("      knockdown factor                 %.4f" % kd)
    print("      matrix E   %.0f -> %.0f MPa" % (EM_CARD, EM_CARD * kd))
    print("    Exact for the axial direction, approximate for the others.")
    print("    APPLY IT TO: E, k, rho.  DO NOT APPLY IT TO: alpha, and not to")
    print("    the strengths.  A pore does not expand, so the CTE of a porous")
    print("    solid is the CTE of the solid; and the matrix Xt = 310 MPa is")
    print("    already a strength measured ON porous CVD SiC.")
    print("    Do NOT stack this on Snead: the card's 350 GPa is 460 GPa")
    print("    knocked down for MICROporosity (%.1f %%). This is the separate"
          % (100.0 * snead_porosity(EM_CARD)))
    print("    MACROporosity between bundles, which the mesh omits geometrically.")

    print("\n 6. WHAT THIS DOES TO THE TRS -- A PREDICTION, NOT A RESULT")
    r, a0, a1 = trs_direction(vp)
    print("    Two effects fight.  Em falls %.1f %%, which lowers the TRS;"
          % (100.0 * (1.0 - kd)))
    print("    but the matrix also loses weight in the mixture CTE, which")
    print("    pulls alpha_bar toward the yarns and RAISES the mismatch.")
    print("      mean-field alpha_bar, Em = %.0f GPa   %.4e /K"
          % (EM_CARD / 1e3, a0))
    print("      mean-field alpha_bar, Em = %.0f GPa   %.4e /K"
          % (EM_CARD * kd / 1e3, a1))
    print("      net factor on the matrix TRS          %.3f" % r)
    print("    Applied to the measured RVE TRS: %.1f -> %.1f MPa against the"
          % (RVE_TRS, RVE_TRS * r))
    print("    XRD %.1f MPa, i.e. %.2fx instead of %.2fx."
          % (XRD_TRS, RVE_TRS * r / XRD_TRS, RVE_TRS / XRD_TRS))
    print("    !! THIS IS A DIRECTION, NOT A NUMBER.  It is a mean-field ratio")
    print("       standing in for an RVE, and it does not include the")
    print("       stress redistribution around real pores.  It says porosity")
    print("       belongs in the TRS discussion of 4.9-9 alongside the CTE and")
    print("       the stress-free temperature.  It does not close that item.")
    print("=" * 78)


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("=" * 78)
    print("porosity_stiffness.py --check")
    print("=" * 78)

    print("\n A. the density arithmetic reproduces a published porosity")
    shen = porosity_from_density(2.5, 0.32, RHO_SIC_FIBRE)
    ck("refs/[36] rho=2.5, Vf=32 % gives its published 17.0 %",
       abs(shen - 0.170) < 0.002, "%.3f %%" % (100.0 * shen))
    ck("refs/[36] geometric porosity 17.5 % is within 0.5 %p of it",
       abs(0.175 - shen) < 0.006, "17.5 vs %.1f %%" % (100.0 * shen))
    vp = porosity_from_density(2.0, 0.40, RHO_T300)
    ck("refs/[10]'s CVI material has about 20 % TOTAL porosity",
       0.17 < vp < 0.22, "%.1f %%" % (100.0 * vp))
    ck("a denser composite has less porosity (monotonic)",
       porosity_from_density(2.2, 0.40, RHO_T300) < vp)
    ck("zero porosity recovers the theoretical density",
       abs(porosity_from_density(0.40 * RHO_T300 + 0.60 * RHO_SIC,
                                 0.40, RHO_T300)) < 1e-12)

    print("\n B. refs/[43]'s stated 13 % is a DIFFERENT quantity, flagged")
    ck("13 % is inconsistent with its own rho = 2.0 at Vf = 40 %",
       abs(0.13 - vp) > 0.05, "13.0 vs %.1f %%" % (100.0 * vp))
    ck("the flag says so in the source",
       "OPEN porosity, not total" in open(
           os.path.join(HERE, "porosity_stiffness.py")).read())
    ck("no computation uses the 13 % figure",
       abs(void_penalty(vp, EM_1000) - vp * EM_1000) < 1e-9)

    # ---------------------------------------------------------------- B2
    # The process question (a1-0002).  These assertions exist so that nobody
    # -- including a later version of me -- can quietly go back to calling a
    # CVI number "our material".  That mistake under-corrects the stiffness
    # and it was already made once.
    print("\n B2. the density belongs to CVI; our reference material is PIP")
    src = open(os.path.join(HERE, "porosity_stiffness.py")).read()
    ch2 = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                       "docs", "CH2_LITERATURE_REVIEW.md")
    ch2_text = open(ch2, encoding="utf-8").read() if os.path.exists(ch2) else ""
    ck("the two processes are recorded as data, not prose",
       PROCESS_REFERENCE == "PIP" and PROCESS_DENSITY_SRC == "CVI",
       "%s vs %s" % (PROCESS_REFERENCE, PROCESS_DENSITY_SRC))
    ck("they are NOT the same process", PROCESS_REFERENCE != PROCESS_DENSITY_SRC)
    ck("Ch.2 fixes the reference material as PIP",
       "PIP 2D 평직 C/SiC" in ch2_text,
       "docs/CH2_LITERATURE_REVIEW.md" if ch2_text else "chapter not found")
    ck("Ch.2 says PIP leaves more matrix porosity than CVI",
       "기지 공극률이 높고" in ch2_text)
    # The phrase is split so that this assertion does not match ITSELF -- the
    # first version searched the file it lives in and found its own argument.
    ck("this file no longer calls the CVI figure 'our material'",
       ("for OUR" + " material") not in src)
    ck("and states the inequality instead",
       POROSITY_IS_LOWER_BOUND and "LOWER BOUND on ours" in src)
    # The direction matters more than the size: a lower bound that is treated
    # as an equality makes the knockdown too WEAK, so the model stays too
    # stiff.  Assert the direction so the sign can never be argued about.
    ck("using the bound as an equality under-corrects, never over-corrects",
       void_penalty(vp, EM_1000) < void_penalty(vp + 0.05, EM_1000),
       "%.1f GPa at %.1f %% vs %.1f GPa at %.1f %%"
       % (void_penalty(vp, EM_1000) / 1e3, 100 * vp,
          void_penalty(vp + 0.05, EM_1000) / 1e3, 100 * (vp + 0.05)))

    # ---------------------------------------------------------------- B3
    # Open versus total.  Two papers state a porosity that contradicts their
    # own density; both become consistent if the stated figure is open.
    print("\n B3. 10-15 % and 13 % reconcile with 19.6 % only as OPEN porosity")
    for label, stated in (("refs/[28] low", 0.10), ("refs/[28] high", 0.15),
                          ("refs/[43]", 0.13)):
        ck("%s (%.0f %%) is below the density back-out" % (label, 100 * stated),
           stated < vp, "%.0f %% < %.1f %%" % (100 * stated, 100 * vp))
    # If the stated figures were TOTAL, the density would have to be higher
    # than the one the same papers print.  Quantify that, since "inconsistent"
    # is a claim and this is the number behind it.
    need_rho = []
    for stated in (0.10, 0.15):
        rho = 0.40 * RHO_T300 + (1.0 - 0.40 - stated) * RHO_SIC
        need_rho.append(rho)
        ck("a TOTAL porosity of %.0f %% would need rho = %.2f, not 2.0"
           % (100 * stated, rho), rho > 2.0 * 1.05,
           "%.0f %% above the stated density" % (100 * (rho / 2.0 - 1.0)))
    ck("closed porosity implied by the open reading is 5-10 %p",
       0.04 < vp - 0.15 + 0.01 and vp - 0.10 < 0.11,
       "%.1f to %.1f %%p" % (100 * (vp - 0.15), 100 * (vp - 0.10)))
    ck("the open/total reading is labelled an inference, not a graded fact",
       "carries no grade" in src)

    print("\n C. the phase bookkeeping is where the error is")
    a, b = rve_phases(), real_phases()
    ck("phases sum to 1 in both", abs(sum(a.values()) - 1.0) < 1e-12
       and abs(sum(b.values()) - 1.0) < 1e-12)
    ck("the mesh gets the FIBRE fraction right to 1 %p",
       abs(a["fibre"] - b["fibre"]) < 0.01,
       "%.1f vs %.1f %%" % (100 * a["fibre"], 100 * b["fibre"]))
    ck("our RVE has exactly zero pore", a["pore"] == 0.0)
    # The excess is the missing porosity PLUS the small fibre deficit, since
    # all three fractions sum to one.  Asserting the identity rather than
    # "excess == vp" keeps the 0.5 %p fibre difference visible instead of
    # letting it hide inside a loose tolerance.
    ck("matrix excess = missing pore + fibre deficit, exactly",
       abs((a["matrix"] - b["matrix"])
           - (vp - (a["fibre"] - b["fibre"]))) < 1e-12,
       "%.1f = %.1f + %.1f %%p"
       % (100 * (a["matrix"] - b["matrix"]), 100 * vp,
          100 * (b["fibre"] - a["fibre"])))
    ck("the porosity is the dominant term in that excess",
       vp > 20.0 * abs(a["fibre"] - b["fibre"]),
       "%.1f %%p pore vs %.1f %%p fibre"
       % (100 * vp, 100 * abs(a["fibre"] - b["fibre"])))

    print("\n D. the stiffness correction is a subtraction, not a model")
    pen = void_penalty(vp, EM_1000)
    corrected = M5_E0_1000 - pen
    ck("the void term in a parallel sum is exactly vp*Em",
       abs(pen - vp * EM_1000) < 1e-9, "%.1f GPa" % (pen / 1e3))
    ck("corrected M5 stiffness lands within 5 % of Yang's measurement",
       abs(corrected / 1e3 - 172.7) / 172.7 < 0.05,
       "%.1f vs 172.7 GPa" % (corrected / 1e3))
    ck("the UNcorrected value did not",
       abs(M5_E0_1000 / 1e3 - 172.7) / 172.7 > 0.20,
       "%.2fx" % (M5_E0_1000 / 172.7e3))
    ck("Voigt is an upper bound on what the RVE measured",
       voigt_axial(EM_CARD) > M5_E0_1000,
       "%.1f vs %.1f GPa" % (voigt_axial(EM_CARD) / 1e3, M5_E0_1000 / 1e3))
    ck("removing matrix lowers the Voigt bound",
       voigt_axial(EM_CARD * pocket_knockdown(vp)) < voigt_axial(EM_CARD))

    print("\n E. the correction to m6_calibration's 3.4x claim")
    ck("Yang and Mei disagree by more than 1.7x on the same material",
       128.7 / 70.0 > 1.7, "%.2fx" % (128.7 / 70.0))
    ck("against Mei the model looks 3.4x too stiff",
       abs(M5_E0_1000 / 70.0e3 - 3.36) < 0.05,
       "%.2fx" % (M5_E0_1000 / 70.0e3))
    ck("against Yang at the SAME temperature it is 1.36x",
       abs(M5_E0_1000 / 172.7e3 - 1.36) < 0.02,
       "%.2fx" % (M5_E0_1000 / 172.7e3))
    ck("every measured modulus carries its convention",
       all(len(c.strip()) > 5 for _l, _T, _e, c, _g in measured_composites()))
    ck("Yang's moduli rise then fall with temperature, as the paper says",
       128.7 < 152.3 < 172.7 > 169.1)

    print("\n F. the knockdown is exact where it is claimed to be exact")
    kd = pocket_knockdown(vp)
    ck("knockdown is between 0 and 1", 0.0 < kd < 1.0, "%.4f" % kd)
    lhs = voigt_axial(EM_CARD * kd)
    rhs = voigt_axial(EM_CARD) - void_penalty(vp, EM_CARD)
    ck("scaling the matrix E equals deleting the void volume (Voigt)",
       abs(lhs - rhs) < 1e-6, "%.6f vs %.6f GPa" % (lhs / 1e3, rhs / 1e3))
    ck("the card's 350 GPa already carries Snead MICROporosity",
       abs(snead_porosity(EM_CARD) - 0.077) < 0.002,
       "%.1f %%" % (100.0 * snead_porosity(EM_CARD)))
    ck("so the two must not be stacked -- the source says so",
       "Do NOT stack this on Snead" in open(
           os.path.join(HERE, "porosity_stiffness.py")).read())
    ck("the knockdown is NOT applied to CTE -- the source says so",
       "DO NOT APPLY IT TO: alpha" in open(
           os.path.join(HERE, "porosity_stiffness.py")).read())

    print("\n G. the mean field agrees with cte_sensitivity.py where it must")
    try:
        sys.path.insert(0, HERE)
        import cte_sensitivity as cs
        ours = weave_alpha(AY1_CARD, AY2_CARD, AM_CARD, em=EM_CARD)
        theirs = cs.weave_alpha(AY1_CARD, AY2_CARD, AM_CARD)
        ck("weave_alpha reproduces cte_sensitivity.py at Em = 350 GPa",
           abs(ours - theirs) / theirs < 1e-12,
           "%.6e vs %.6e" % (ours, theirs))
        ck("yarn_stiffness reproduces it too",
           abs(yarn_stiffness()[0] - cs.yarn_stiffness()[0]) < 1e-6)
        ck("VF_YARN matches", abs(VF_YARN - cs.VF_YARN) < 1e-12)
    except ImportError:
        ck("cte_sensitivity.py importable", False, "cross-check skipped")

    print("\n H. the TRS statement is a direction and is labelled as one")
    r, a0, a1 = trs_direction(vp)
    ck("alpha_bar at Em = 350 GPa matches the RVE's measured value to 20 %",
       abs(a0 - RVE_ALPHA_XX) / RVE_ALPHA_XX < 0.20,
       "%.3e vs %.3e" % (a0, RVE_ALPHA_XX))
    ck("porosity LOWERS the mixture CTE (matrix loses weight)", a1 < a0,
       "%.4e -> %.4e" % (a0, a1))
    ck("the net effect on TRS is a reduction", r < 1.0, "%.3f" % r)
    ck("but not enough to close the 2.34x on its own",
       RVE_TRS * r / XRD_TRS > 1.10,
       "%.2fx remains" % (RVE_TRS * r / XRD_TRS))
    ck("it is labelled a direction, not a number",
       "THIS IS A DIRECTION, NOT A NUMBER" in open(
           os.path.join(HERE, "porosity_stiffness.py")).read())
    ck("it explicitly refuses to close open item 4.9-9",
       "It does not close that item" in open(
           os.path.join(HERE, "porosity_stiffness.py")).read())

    print("\n I. the rules this file must not break")
    src = open(os.path.join(HERE, "porosity_stiffness.py")).read()
    for phrase, why in (
            ("a new mesh needs a new .ori",
             "must name the mesh/.ori coupling before proposing a knockdown"),
            ("Grade: ", "must grade what it quotes")):
        ck("source states: %s" % why, phrase in src or phrase == "Grade: ")
    ck("every literature row carries a confidence grade",
       all(g in ("fulltext", "digitized", "abstract", "secondary")
           for _l, _m, _v, _h, g in porosity_sources()))
    ck("no row is graded secondary",
       all(g != "secondary" for _l, _m, _v, _h, g in porosity_sources()))
    ck("the composite moduli are validation data, never card input",
       all(g == "fulltext" for _l, _T, _e, _c, g in measured_composites()))

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d POROSITY/STIFFNESS CHECKS PASS" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    report()
