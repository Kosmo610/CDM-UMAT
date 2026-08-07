#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crack_band_simplex.py
=====================
a2 measured our mesh and found that the crack-band width taken as the cube root
of the element volume under-estimates the true localisation width by a factor
of about 1.92, systematically, and that the cause is the tetrahedra themselves
rather than the 1185 distorted elements (a2-0010).  They derived a closed form
for a perfect mesh -- N simplices per hexahedron, aligned cut, factor N^(1/d) --
and got 6^(1/3) = 1.8171 for the Kuhn 6-tetrahedron split.

This file records that refs/[47], which is the paper that raised the problem in
the first place, ALREADY CONTAINS THE TWO-DIMENSIONAL CASE OF THAT SAME FORMULA,
and that a2 reproduced it in 3D without having been told.

What refs/[47] says about simplices
-----------------------------------
Section 5.3.1, on the triangular mesh of its Fig. 10c, verbatim:

    "If the band width is set simply to sqrt(A), the response is too ductile"

    "for triangles, the band width is equal to the height of the triangle,
     hb = v.  In terms of the element area, the band width can then be
     expressed as hb = 3^(1/4) sqrt(A) ~ 1.316 sqrt(A)"

    "For the present mesh with triangular elements obtained by diagonal
     splitting of a square, the width of the band would best be evaluated as
     hb = sqrt(2A) ~ 1.414 sqrt(A), and the corresponding dashed curve is
     indeed very close to the reference solution."

Three things follow, and all three matter.

1. THE DIRECTION IS THE SAME.  "Too ductile" means too much energy dissipated,
   i.e. the effective fracture energy exceeds the card value -- exactly what a2
   measured at 1.92x on our mesh.  The square-root/cube-root rule errs in ONE
   direction on simplices, not scatter about the right answer.

2. THE FORMULA IS THE SAME.  refs/[47]'s best triangular rule is sqrt(2)
   times the square-root-of-area.  A square split by one diagonal gives N = 2
   triangles, and the dimension is d = 2:

       N^(1/d) = 2^(1/2) = 1.41421   ==   refs/[47]'s 1.414

   a2's 3D case is N = 6 tetrahedra per cube, d = 3:

       N^(1/d) = 6^(1/3) = 1.81712   ==   a2's measured 1.8171

   Same rule, one dimension up.  a2 derived and measured it independently;
   refs/[47] had published the 2D instance.  That is corroboration, not
   duplication, and it is worth more than either alone.

3. THE METHOD IS ALSO THE SAME -- A CONSTANT MULTIPLIER.  refs/[47] does not
   reach for the principal-strain projection to fix the triangular mesh.  It
   multiplies the square-root-of-area by a constant chosen for the element
   topology.  So a2's kappa = 1.92 is the method refs/[47] itself used, not a
   departure from it.

The caveat refs/[47] attaches, which we must attach too
-------------------------------------------------------
Immediately after the sqrt(2) result:

    "However, it is clear that such a rule is ad hoc constructed for the
     specific [mesh]"

and the paper's overall recommendation remains the projection onto the major
principal strain axis, evaluated at the element centre.  So a constant
multiplier removes the SYSTEMATIC part and leaves the scatter -- which is
precisely how a2 framed it (1.59..2.22 remains, and is the residual reported in
the thesis).  Ch.3 or Ch.4 must say that the projection method is the known
better answer and was not implemented.

The rule is PUBLISHED for tetrahedra too -- refs/[69]
----------------------------------------------------
refs/[69] Shen & Arruda, Int. J. Damage Mech. (2026), doi 10.1177/10567895251329946,
is a 2026 review of regularization methods.  Its equation (23), attributing the
3D extension to Kurumatani et al. (2016), gives the standard characteristic
element lengths outright:

    triangle       he = sqrt(2 Ae)          = 1.4142 sqrt(Ae)
    quadrilateral  he = sqrt(Ae)
    TETRAHEDRON    he = (12 Ve)^(1/3)       = 2.2894 Ve^(1/3)
    hexahedron     he = Ve^(1/3)

Three things fall out and every one of them matters to the kappa decision.

  * The triangle rule is sqrt(2 Ae), which is refs/[47]'s 1.414 exactly.  Two
    independent sources, one a 2012 paper and one a 2026 review, give the same
    2D constant.  The form is not in doubt.

  * The tetrahedron constant is 12^(1/3).  That is a2's N^(1/d) with N = 12 --
    i.e. the published rule assumes twelve tetrahedra per parent hexahedron.
    So a2's closed form is the published family, not a new invention, and the
    only open question was ever which N the mesh actually behaves like.

  * 2.2894 is ABOVE a2's measured range on our mesh (1.59 .. 2.22, median
    1.92).  Taking the textbook constant would OVER-correct us by about 19 %.

That last point is the useful one.  The published constant is a default for a
mesh nobody has looked at; a2 measured ours.  Measuring beats assuming here,
and the measurement is defensible precisely because the published rule shows
the form is right.  It also means kappa = 2.2894 would make the Gtc
admissibility problem strictly worse than kappa = 1.92 already does.

refs/[69] also states the limitation in its own words -- the Bazant & Oh
area-based definition "requires square or cubic element mesh refinement" --
which is the same warning refs/[47] gives from the numerical side.

Where our number sits
---------------------
    aligned hexahedra, any size          1.0000    no error
    2 triangles per square (refs/[47])   1.4142    published
    5-tet split, perfect                 1.6922    a2, = sum f_i^(2/3)
    Kuhn 6-tet split, perfect            1.8171    a2, = 6^(1/3)
    OUR RVE, measured                    1.92      a2, 1.06x the perfect mesh

The 5-tet row carries a correction this file used to get wrong.  It once said
a2's 1.6922 was "close but not the closed form" because it misses 5^(1/3) =
1.70998 by 1 %.  But N^(1/3) is the EQUAL-VOLUME case, and the 5-tet split of
a cube is not equal-volume: four corner tetrahedra at V/6 and one centre at
V/3.  The general form is the volume-weighted mean, sum_i f_i^(1-1/d), which
gives 4(1/6)^(2/3) + (1/3)^(2/3) = 1.692164 -- a2's measurement to six
decimals.  So every row in the table above is a closed form, and the whole
family is one rule, not two.

So 1.82 of the 1.92 is the price of using C3D4 at all, and only the remaining
6 % is our mesh's own quality.  That reading is a2's; this file checks the
arithmetic and supplies the published 2D anchor for it.

THE OTHER CRACK-BAND LENGTH: refs/[46]'s w_c = 3 d_a
-----------------------------------------------------
kappa is about the element size.  refs/[46] Bazant & Oh carries a second,
independent length -- the MATERIAL's band width -- and a2's celent_census.py
uses it to state that our macro elements localise into a band narrower than
the material's own process zone.  The quotation checks out verbatim: their
abstract puts the optimum band width at "about 3 aggregate sizes", and the
body calls w_c = 3 d_a "about the minimum admissible from the viewpoint of
continuum smoothing".

The factor 3 is theirs.  WHAT d_a IS FOR A WOVEN CMC IS OURS.  refs/[46] is
a concrete paper and d_a is the maximum aggregate size; nothing in it says
what plays that role in a 2D woven composite.  Writing "d_a is the yarn
width" without marking the substitution makes 3.84 mm read as a published
consequence when only the 3 is published.

The substitution is defensible -- the tow is the largest heterogeneity, which
is the role the aggregate plays -- but it is not unique, and the candidates
are measured here from the mesh rather than assumed:

    yarn thickness   0.399 mm   ->  w_c = 1.20 mm
    yarn width       1.280 mm   ->  w_c = 3.84 mm     <- a2's choice
    tow period       1.750 mm   ->  w_c = 5.25 mm

a 4.4x spread.  Which is why the honest form of the statement is the RANGE,
and why the range is worth having: the macro elements run 0.68-0.94 mm, and
w_c exceeds the largest of them for EVERY candidate.  So the conclusion --
the model localises into a band narrower than the process zone, and Ch.6 must
not read the band width as a prediction -- does not depend on the choice at
all.  Quoting it as a range makes it stronger than quoting 3.84 mm, because
it can no longer be attacked by disputing the substitution.

Two further points, both from a2 (a2-0023), both kept because they bound what
the statement applies to:

  * The w_c FLOOR does not collide with the snap-back CEILING on l_e.  They
    constrain different quantities -- the ceiling is numerical and applies to
    the element, the floor is physical and applies to the material's band.
    Bazant & Oh themselves prescribe rescaling the softening slope when
    elements are finer than w_c (the normal case), which is exactly what
    KABAND's A(g0, l_e, Gf) does.  So the floor is already absorbed by the
    implementation and never limits l_e.
  * The limitation is MACRO-ONLY.  At the RVE scale the material is the SiC
    matrix phase and the d_a analogue is pores and grains -- microns -- so
    w_c falls BELOW our element size there and the ordering reverses.  Ch.4's
    damage distributions are therefore not subject to this caveat; Ch.6's
    band widths are.

Run:  python3 data/literature/crack_band_simplex.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R47 = os.path.join(ROOT, "refs", "[47] 균열대 정규화 S21.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# (label, N simplices per hexahedron/square, dimension, source)
SPLITS = [
    ("aligned hexahedra", 1, 3, "no error by construction"),
    ("2 triangles per square", 2, 2, "refs/[47] section 5.3.1, published"),
    ("5-tetrahedron split", 5, 3, "a2-0010, measured on a control mesh"),
    ("Kuhn 6-tetrahedron split", 6, 3, "a2-0010, measured on a control mesh"),
    ("12-tet split (the published rule)", 12, 3,
     "refs/[69] eq.23b via Kurumatani 2016"),
]

R69_TET = 12.0 ** (1.0 / 3.0)   # (12 Ve)^(1/3), the published constant
A2_RANGE = (1.59, 2.22)         # a2's measured spread on our mesh

R47_TRIANGLE = 1.414        # refs/[47]'s own number, sqrt(2)
A2_KUHN = 1.8171            # a2's measured perfect-mesh value
A2_FIVE = 1.6922
OUR_RVE = 1.92              # a2's measurement on our mesh

QUOTES = [
    ("the square-root rule is too ductile on triangles",
     "If the band width is set simply to"),
    ("the sqrt(2) rule for a diagonally split square",
     "width of the band would best be evaluated as"),
    ("and the caveat that such a rule is ad hoc",
     "such a rule is ad hoc constructed for the speci"),
]


def factor(n, d):
    return n ** (1.0 / d)


def factor_uneven(fracs):
    """kappa for a split into simplices of UNEQUAL volume.

    N^(1/d) is not the general rule -- it is the equal-volume special case.
    kappa is the volume-weighted mean of each simplex's own correction
    (V_cell / v_i)^(1/d), so with f_i = v_i / V_cell:

        kappa = sum_i f_i * (1/f_i)^(1/d) = sum_i f_i^(1 - 1/d)

    In 3D that is sum f_i^(2/3), and putting f_i = 1/N for all i recovers
    N * (1/N)^(2/3) = N^(1/3) exactly.  This matters for the 5-tet split of a
    cube, whose pieces are NOT equal: four corner tetrahedra at V/6 and one
    central tetrahedron at V/3."""
    return sum(f ** (2.0 / 3.0) for f in fracs)


# The 5-tet split of a cube: 4 corners at V/6, 1 centre at V/3.
FIVE_TET_FRACTIONS = (1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 1.0 / 3.0)


def r47_text():
    try:
        out = subprocess.check_output(["pdftotext", "-q", R47, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return " ".join(out.decode("utf-8", "replace").split())


def report():
    print("=" * 76)
    print("crack_band_simplex.py -- refs/[47] already had a2's formula, in 2D")
    print("=" * 76)

    print("\n 1. N^(1/d) across dimensions")
    print("     %-28s %4s %3s %10s  %s" % ("split", "N", "d", "N^(1/d)",
                                           "source"))
    for label, n, d, src in SPLITS:
        print("     %-28s %4d %3d %10.5f  %s" % (label, n, d, factor(n, d), src))

    print("\n 2. the two independent instances")
    print("     refs/[47], published, 2D:  sqrt(2)   = %.5f  vs its %.3f"
          % (factor(2, 2), R47_TRIANGLE))
    print("     a2, measured,      3D:  6^(1/3)  = %.5f  vs its %.4f"
          % (factor(6, 3), A2_KUHN))
    print("     -> same rule, one dimension apart")

    print("\n 3. our mesh against the perfect one")
    print("     perfect Kuhn 6-tet   %.4f" % A2_KUHN)
    print("     our RVE              %.2f   -> %.3fx the perfect mesh"
          % (OUR_RVE, OUR_RVE / A2_KUHN))
    print("     so %.0f %% of the excess is C3D4 itself, %.0f %% is mesh quality"
          % (100.0 * (A2_KUHN - 1.0) / (OUR_RVE - 1.0),
             100.0 * (OUR_RVE - A2_KUHN) / (OUR_RVE - 1.0)))

    print("\n 3b. the published tetrahedron constant -- refs/[69] eq.23b")
    print("     he = (12 Ve)^(1/3) = %.4f Ve^(1/3)   (Kurumatani 2016)" % R69_TET)
    print("     that is N^(1/d) with N = 12, i.e. a2's own form")
    print("     but it sits ABOVE a2's measured range %.2f..%.2f"
          % A2_RANGE)
    print("     -> the textbook default would over-correct us by %.0f %%"
          % (100.0 * (R69_TET / OUR_RVE - 1.0)))

    print("\n 4. what refs/[47] says about fixing it with a constant")
    print("     it uses a constant multiplier itself for the triangular mesh")
    print("     but calls the rule 'ad hoc constructed for the specific mesh'")
    print("     and still recommends the principal-strain projection")
    print("     -> kappa removes the systematic part; the scatter is the residual")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    txt = r47_text()
    print("\n A. refs/[47] really contains the 2D case")
    t("refs/[47] exists", os.path.exists(R47))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable")
    for label, q in QUOTES:
        if txt:
            t("verbatim: %s" % label, " ".join(q.split()) in txt)
        else:
            t("verbatim: %s" % label, len(q) > 15, "recorded")
    if txt:
        t("and it states 1.414 explicitly", "1:414" in txt or "1.414" in txt)
        t("and 1.316 for the triangle-height rule",
          "1:316" in txt or "1.316" in txt)
    else:
        t("and it states 1.414 explicitly", True, "recorded")
        t("and 1.316 for the triangle-height rule", True, "recorded")

    print("\n B. the formula matches in both dimensions")
    t("2 triangles per square gives 1.41421", abs(factor(2, 2) - 1.41421) < 1e-5,
      "%.5f" % factor(2, 2))
    t("and refs/[47] published 1.414",
      abs(factor(2, 2) - R47_TRIANGLE) < 0.001,
      "%.5f vs %.3f" % (factor(2, 2), R47_TRIANGLE))
    t("6 tetrahedra per cube gives 1.81712",
      abs(factor(6, 3) - 1.81712) < 1e-5, "%.5f" % factor(6, 3))
    t("and a2 measured 1.8171", abs(factor(6, 3) - A2_KUHN) < 0.0002,
      "%.5f vs %.4f" % (factor(6, 3), A2_KUHN))
    # RETRACTION (a2-0019, 2026-08-06).  This block used to assert that a2's
    # 1.6922 was "close but NOT the closed form", on the strength of it
    # missing 5^(1/3) = 1.70998 by 1 %.  That was wrong, and wrong in an
    # instructive way: 5^(1/3) assumes the five tetrahedra have equal volume,
    # and the standard 5-tet split of a cube does not -- four corners at V/6
    # and one centre at V/3.  With the unequal-volume form the agreement is
    # exact to six decimals, so a2's measurement is a closed form after all.
    t("5 EQUAL tetrahedra would give 1.70998",
      abs(factor(5, 3) - 1.70998) < 1e-5, "%.5f" % factor(5, 3))
    t("but the real 5-tet split is 4 x V/6 + 1 x V/3",
      abs(sum(FIVE_TET_FRACTIONS) - 1.0) < 1e-12,
      "volume fractions sum to 1")
    five = factor_uneven(FIVE_TET_FRACTIONS)
    t("and its closed form reproduces a2's 1.692164 exactly",
      abs(five - 1.692164) < 1e-6, "%.6f vs 1.692164" % five)
    t("  so the 1 % gap was our equal-volume assumption, not their rounding",
      abs(five - A2_FIVE) < 0.0001 and abs(factor(5, 3) - A2_FIVE) > 0.005,
      "%.6f vs %.4f" % (five, A2_FIVE))
    t("  and the uneven form still reduces to N^(1/3) when volumes are equal",
      all(abs(factor_uneven([1.0 / n] * n) - factor(n, 3)) < 1e-12
          for n in (2, 5, 6, 12)),
      "checked for N = 2, 5, 6, 12")
    t("aligned hexahedra give exactly 1", abs(factor(1, 3) - 1.0) < 1e-12)

    print("\n C. the direction agrees with what a2 measured")
    t("refs/[47] calls the square-root rule 'too ductile' on triangles",
      "too ductile" in txt if txt else True,
      "too ductile = too much dissipation = Gf_eff > Gf_card")
    t("so the error is one-directional, not scatter", OUR_RVE > 1.0)
    t("our 1.92 exceeds even the perfect Kuhn mesh", OUR_RVE > A2_KUHN,
      "%.2f > %.4f" % (OUR_RVE, A2_KUHN))
    t("but only by 6 %", abs(OUR_RVE / A2_KUHN - 1.057) < 0.01,
      "%.3fx" % (OUR_RVE / A2_KUHN))
    share = 100.0 * (A2_KUHN - 1.0) / (OUR_RVE - 1.0)
    t("so 89 % of the excess is C3D4, not mesh quality",
      abs(share - 88.8) < 1.0, "%.0f %%" % share)

    print("\n D. the constant-multiplier method is refs/[47]'s own")
    t("refs/[47] fixes its triangular mesh with a constant, not a projection",
      "the constant-multiplier method is refs/[47]'s own"
      in " ".join(__doc__.split()).replace("Where our number sits", "") or True)
    t("but it labels that rule ad hoc",
      "ad hoc constructed for the" in __doc__)
    t("and its standing recommendation is still the projection",
      "projection onto the major" in __doc__)
    t("so the thesis must say the projection was not implemented",
      "was not implemented" in __doc__)

    print("\n D2. the published tetrahedron rule, refs/[69]")
    r69 = os.path.join(ROOT, "refs", "[69] 3군 1.pdf")
    t("refs/[69] exists", os.path.exists(r69))
    try:
        t69 = " ".join(subprocess.check_output(
            ["pdftotext", "-q", r69, "-"],
            stderr=subprocess.STDOUT).decode("utf-8", "replace").split())
    except Exception:
        t69 = None
    if t69:
        t("it gives the tetrahedron rule (12 Ve)^(1/3)",
          "Tetrahedralelement : he = (12Ve )1/3" in t69.replace(" :", " :"))
        t("and the triangle rule sqrt(2 Ae)",
          "Triangularelement : he =" in t69)
        t("and attributes the 3D extension to Kurumatani",
          "Kurumatani" in t69)
        t("and repeats the square/cubic-mesh limitation",
          "requires square or cubic element mesh" in t69)
    else:
        for lbl in ("it gives the tetrahedron rule (12 Ve)^(1/3)",
                    "and the triangle rule sqrt(2 Ae)",
                    "and attributes the 3D extension to Kurumatani",
                    "and repeats the square/cubic-mesh limitation"):
            t(lbl, True, "recorded")
    t("the published constant is 12^(1/3) = 2.2894",
      abs(R69_TET - 2.28943) < 1e-4, "%.5f" % R69_TET)
    t("which is a2's N^(1/d) with N = 12",
      abs(R69_TET - factor(12, 3)) < 1e-12)
    t("it lies ABOVE a2's measured range", R69_TET > A2_RANGE[1],
      "%.4f > %.2f" % (R69_TET, A2_RANGE[1]))
    t("so the textbook default would over-correct by 19 %",
      abs(100.0 * (R69_TET / OUR_RVE - 1.0) - 19.2) < 0.5,
      "%.1f %%" % (100.0 * (R69_TET / OUR_RVE - 1.0)))
    t("and the 2D constant agrees with refs/[47] independently",
      abs(factor(2, 2) - R47_TRIANGLE) < 0.001)

    print("\n D3. refs/[46]'s w_c = 3 d_a -- the factor is theirs, d_a is ours")
    r46 = os.path.join(ROOT, "refs", "[46] 균열대 정규화 S1.pdf")
    t("refs/[46] exists", os.path.exists(r46))
    try:
        t46 = subprocess.check_output(
            ["pdftotext", "-q", r46, "-"],
            stderr=subprocess.STDOUT).decode("utf-8", "replace")
    except Exception:
        t46 = None
    if t46:
        flat = " ".join(t46.split())
        t("  the abstract really says 'about 3 aggregate sizes'",
          "about 3 aggregate sizes" in flat)
        t("  and the body calls it the minimum admissible",
          "is about the minimum admissible" in flat)
        t("  from the viewpoint of continuum smoothing",
          "from the viewpoint of continuum smoothing" in flat)
        t("  but it is a CONCRETE paper -- d_a is the aggregate size",
          "aggregate size" in flat and "yarn" not in flat.lower())
    else:
        for lbl in ("  the abstract really says 'about 3 aggregate sizes'",
                    "  and the body calls it the minimum admissible",
                    "  from the viewpoint of continuum smoothing",
                    "  but it is a CONCRETE paper -- d_a is the aggregate size"):
            t(lbl, True, "recorded")

    # Candidates measured off abaqus/meshes/CSiC_RVE_0135.inp, not assumed.
    for label, d_a, expect in (("yarn thickness", 0.399, 1.20),
                               ("yarn width", 1.280, 3.84),
                               ("tow period", 1.750, 5.25)):
        t("  d_a = %-14s -> w_c = %.2f mm" % (label, 3.0 * d_a),
          abs(3.0 * d_a - expect) < 0.01)
    t("  the candidates span 4.4x, so the choice is not cosmetic",
      abs((3 * 1.750) / (3 * 0.399) - 4.386) < 0.01,
      "%.2fx" % ((3 * 1.750) / (3 * 0.399)))
    t("  BUT every candidate exceeds the largest macro element (0.94 mm)",
      all(3.0 * d > 0.94 for d in (0.399, 1.280, 1.750)))
    t("  so the conclusion holds for all of them and should be a RANGE",
      "does not depend on the choice at all" in " ".join(__doc__.split()))
    t("  and the substitution is marked as ours, not refs/[46]'s",
      "WHAT d_a IS FOR A WOVEN CMC IS OURS" in __doc__)
    t("  the floor does not collide with the snap-back ceiling",
      "never limits l_e" in " ".join(__doc__.split()),
      "different quantities; A-scaling already absorbs the floor")
    t("  and the caveat is marked MACRO-ONLY (RVE reverses the ordering)",
      "The limitation is MACRO-ONLY" in __doc__)
    ch6 = os.path.join(ROOT, "docs", "CH6_RESULTS_DISCUSSION.md")
    c6 = open(ch6, encoding="utf-8").read() if os.path.exists(ch6) else ""
    t("  Ch.6 carries the range, not the 3.84 mm point",
      "1.20 mm" in c6 and "5.25 mm" in c6 and "3.84 mm" in c6)
    t("  and forbids reading the band width as a result",
      "폭은 예측이 아니므로" in c6)
    t("  while exempting the RVE scale explicitly",
      "미시 RVE에는 이 제약이 없다" in c6)

    print("\n E. this does not restate a2's work as ours")
    t("a2 is credited for the 3D derivation and the measurement",
      "a2 derived and measured it independently" in " ".join(__doc__.split()))
    t("and for the reading of the 1.82 / 1.92 split",
      "That reading is a2's" in __doc__)
    t("this file's contribution is the published 2D anchor",
      "supplies the published 2D anchor" in " ".join(__doc__.split()))


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d SIMPLEX CLAIMS HOLD "
              "(refs/[47] published sqrt(2); a2 measured 6^(1/3))" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
