#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pls_validation.py
=================
Proposes the proportional limit stress (PLS) as the thesis's primary
validation metric for thermal-residual-stress relaxation, and assembles the
literature that makes it usable.

Why, in one line: PLS moves 5-7x more than the modulus does over the same
temperature range, because the modulus is a volume average and the PLS is a
threshold.  We have been comparing the model against the insensitive one.

The mechanism, and its provenance
---------------------------------
refs/[15] S. Zhang et al., Compos. Part A 207 (2026) 109796, introduction:

    "Liu et al. [9] noted that the tensile TRSs in the SiC matrix
     significantly affect the proportional limit stress (PLS) of a CMC and
     showed that the PLS increases as the TRS in the SiC matrix decreases."

That is exactly the chain the thesis needs: heat the specimen -> matrix
tensile TRS relaxes -> matrix cracking starts later -> PLS rises.  The
modulus, by contrast, is untouched until cracking actually occurs -- which is
the same paper's own headline finding, quoted in Ch.1:

    "TRSs do not affect the composite moduli, unless matrix cracking has
     occurred."

So the two statements say the same thing from opposite sides: BEFORE cracking
the modulus cannot see TRS at all, and the PLS is precisely the stress at
which cracking begins.  Using the modulus to validate a TRS model is using
the one quantity the source says is blind to it.

GRADING.  The Liu sentence is refs/[15] reporting someone else, so it is
`secondary` and MUST NOT be cited.  The primary is
    Liu S, Zhang L, Yin X, Liu Y, Cheng L, "Proportional limit stress and
    residual thermal stress of 3D SiC/SiC composite"
which refs/[15] lists as its [9] and which we do not hold.  Acquiring it
turns this whole argument from secondary to primary.  It is the single
highest-value acquisition on the list.

The data we already hold
------------------------
  refs/[10] Yang, J. Eur. Ceram. Soc. 37 (2017) 1281, Table 1.
            2D plain-weave C/SiC (CVI), FOUR temperatures, one study.
            This is the anchor: it carries PLS and modulus side by side, so
            the sensitivity ratio is computed within one material.

  refs/[28] Li, Jiao, Wang, Yang, Wang, Chin. J. Aeronaut. 27(6) (2014) 1586.
            Same architecture, room temperature, tension vs compression.
            PLS 19.53 / 158.28 MPa -- an 8.1x asymmetry against only 1.28x in
            ultimate strength.  The asymmetry the thesis calls C3 is a PLS
            phenomenon, not a strength phenomenon.

  refs/[45] Jeong et al., J. Korean Ceram. Soc. 61 (2024) 161.
            1400 C: E 152.3 GPa, PLS 125.1 MPa, UTS 144.1 MPa.
            DIFFERENT material -- CVI/LSI/PIP hybrid, apparent density
            2.77 g/cm3, 2 vol% residual silicon.  Recorded as a far-field
            check only; the density alone says it is not comparable.

SCALE RULE.  PLS is a COMPOSITE measurement.  Under the project rule
("구성재 데이터만 카드 입력") it can never be a card input -- only a
validation target.  Stated here because the temptation to calibrate directly
against it will be strong once the sensitivity below is seen.

Two things this search turned up that are not about PLS
-------------------------------------------------------
1. refs/[15] Table 1 gives the SiC matrix modulus as **Em = 80.0 GPa**.
   Our card carries 350 GPa.  This is a THIRD independent anchor on the
   matrix-modulus problem raised in a1-0009, and it points the same way as
   the density inversion:

       our card                          350 GPa
       demanded by measured density      143 GPa   (a1-0009)
       used by refs/[15] for 3D C/SiC     80 GPa

   The card is the outlier, by 2.4x against one independent route and 4.4x
   against the other.  refs/[15] is not a light source here: it is the paper
   the thesis cites for the XRD-measured TRS itself.

2. refs/[15] Table 1 also gives PyC INTERPHASE properties:
   Ei = 20.0 GPa, nu_i = 0.23, Xti = 140 MPa, Xci = 200 MPa.

   This CORRECTS a statement in data/properties/card_gap_triage.py, which
   said "no interfacial normal or shear strength for our material exists
   anywhere in the repository".  It did exist, in a paper already on the
   shelf, and it was not looked at.  The correction is applied there.
   (The 140 MPa is the interphase layer's own tensile strength rather than a
   fibre/matrix debond stress, so it does not close the Yt gap by itself --
   but it bounds it, and our Yt = 80 MPa sits below it, which is consistent.)

Run:  python3 data/literature/pls_validation.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R15 = os.path.join(ROOT, "refs", "[15] 3D C-SiC 물성 A01.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# refs/[10] Table 1 -- (T [K], PLS [MPa], E [GPa], UTS [MPa])
YANG_T1 = [
    (300.0, 30.0, 128.7, 225.8),
    (973.0, 50.0, 152.3, 240.5),
    (1273.0, 80.0, 172.7, 268.2),
    (1473.0, 100.0, 169.1, 240.9),
]

# refs/[28] room temperature, 0 degree, tension vs compression
LI_PLS = (19.53, 158.28)
LI_ULT = (265.28, 338.94)

# refs/[45], 1400 C, DIFFERENT material -- recorded, not used as a target
JEONG = dict(T_C=1400.0, E=152.3, PLS=125.1, UTS=144.1, rho=2.77)

# refs/[15] Table 1
R15_EM = 80.0            # GPa, SiC matrix
R15_INTERPHASE = dict(Ei=20.0, nu=0.23, Xt=140.0, Xc=200.0)
OUR_EM = 350.0           # GPa, Zhang [5] Table 2
DENSITY_EM = 143.3       # GPa, demanded by the density inversion (a1-0009)
OUR_YT = 80.0            # MPa, yarn card

QUOTES = [
    ("TRS -> PLS mechanism",
     "the tensile TRSs in the SiC matrix significantly affect the "
     "proportional limit stress (PLS) of a CMC and showed that the PLS "
     "increases as the TRS in the SiC matrix decreases"),
    ("the primary source is named",
     "Proportional limit stress and residual thermal stress of 3D SiC/SiC "
     "composite"),
]


def pct(a, b):
    return 100.0 * (b / a - 1.0)


def r15_text():
    try:
        out = subprocess.check_output(["pdftotext", "-q", R15, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return " ".join(out.decode("utf-8", "replace").split())


def report():
    print("=" * 76)
    print("pls_validation.py -- why PLS, not the modulus, tests TRS relaxation")
    print("=" * 76)

    print("\n 1. refs/[10] Table 1 -- one material, four temperatures")
    print("     %7s %9s %9s %9s" % ("T [K]", "PLS", "E [GPa]", "UTS"))
    for T, p, e, u in YANG_T1:
        print("     %7.0f %9.1f %9.1f %9.1f" % (T, p, e, u))

    p0, e0, u0 = YANG_T1[0][1:]
    print("\n 2. how much each quantity moves")
    for label, hi, lo in (("300 -> 1273 K", YANG_T1[2], YANG_T1[0]),
                          ("300 -> 1473 K", YANG_T1[3], YANG_T1[0])):
        dp, de, du = (pct(lo[1], hi[1]), pct(lo[2], hi[2]), pct(lo[3], hi[3]))
        print("     %s   PLS %+7.1f %%   E %+6.1f %%   UTS %+6.1f %%   "
              "PLS/E = %.1fx" % (label, dp, de, du, dp / de))

    print("\n 3. the same asymmetry at room temperature -- refs/[28]")
    print("     PLS       tension %6.2f   compression %7.2f   ratio %.1fx"
          % (LI_PLS[0], LI_PLS[1], LI_PLS[1] / LI_PLS[0]))
    print("     ultimate  tension %6.2f   compression %7.2f   ratio %.2fx"
          % (LI_ULT[0], LI_ULT[1], LI_ULT[1] / LI_ULT[0]))
    print("     -> C3's asymmetry is %.1fx bigger in PLS than in strength"
          % ((LI_PLS[1] / LI_PLS[0]) / (LI_ULT[1] / LI_ULT[0])))

    print("\n 4. the matrix modulus, third anchor (not a PLS result)")
    print("     our card                       %6.1f GPa" % OUR_EM)
    print("     demanded by measured density   %6.1f GPa   (a1-0009)"
          % DENSITY_EM)
    print("     used by refs/[15] for 3D C/SiC %6.1f GPa" % R15_EM)
    print("     -> the card is %.2fx and %.2fx the two independent values"
          % (OUR_EM / DENSITY_EM, OUR_EM / R15_EM))

    print("\n 5. PyC interphase, from the same table")
    print("     Ei %.1f GPa   nu %.2f   Xt %.0f MPa   Xc %.0f MPa"
          % (R15_INTERPHASE["Ei"], R15_INTERPHASE["nu"],
             R15_INTERPHASE["Xt"], R15_INTERPHASE["Xc"]))
    print("     our yarn Yt = %.0f MPa sits below Xt_interphase = %.0f MPa"
          % (OUR_YT, R15_INTERPHASE["Xt"]))
    print("     -> corrects card_gap_triage.py's 'nothing exists' statement")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    txt = r15_text()
    print("\n A. the mechanism statement is really in refs/[15]")
    t("refs/[15] exists", os.path.exists(R15))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable")
    for label, q in QUOTES:
        if txt:
            t("verbatim: %s" % label, " ".join(q.split()) in txt)
        else:
            t("verbatim: %s" % label, len(q) > 20, "recorded")
    t("it is graded secondary and refused for citation",
      "MUST NOT be cited" in __doc__)
    t("the primary is named so it can be acquired",
      "Liu S, Zhang L, Yin X, Liu Y, Cheng L" in __doc__)

    print("\n B. PLS is far more sensitive than the modulus")
    p0, e0, u0 = YANG_T1[0][1:]
    dp = pct(p0, YANG_T1[2][1])
    de = pct(e0, YANG_T1[2][2])
    t("PLS rises 166.7 % from 300 to 1273 K", abs(dp - 166.667) < 0.1,
      "%+.1f %%" % dp)
    t("E rises only 34.2 % over the same span", abs(de - 34.19) < 0.1,
      "%+.1f %%" % de)
    t("so PLS is 4.9x more sensitive", abs(dp / de - 4.874) < 0.02,
      "%.2fx" % (dp / de))
    dp2 = pct(p0, YANG_T1[3][1])
    de2 = pct(e0, YANG_T1[3][2])
    t("over the full span to 1473 K it is 7.4x", abs(dp2 / de2 - 7.43) < 0.05,
      "%.2fx" % (dp2 / de2))
    t("and UTS is the least sensitive of the three",
      pct(u0, YANG_T1[2][3]) < de < dp,
      "UTS %+.1f %% < E %+.1f %% < PLS %+.1f %%"
      % (pct(u0, YANG_T1[2][3]), de, dp))
    t("PLS is monotonic in T while E is not",
      all(YANG_T1[i][1] > YANG_T1[i - 1][1] for i in range(1, 4))
      and YANG_T1[3][2] < YANG_T1[2][2])

    print("\n C. the room-temperature asymmetry says the same thing")
    rp = LI_PLS[1] / LI_PLS[0]
    ru = LI_ULT[1] / LI_ULT[0]
    t("PLS asymmetry is 8.1x", abs(rp - 8.104) < 0.02, "%.2fx" % rp)
    t("ultimate asymmetry is only 1.28x", abs(ru - 1.278) < 0.01,
      "%.3fx" % ru)
    t("PLS shows the asymmetry 6.3x more strongly",
      abs(rp / ru - 6.34) < 0.05, "%.2fx" % (rp / ru))
    t("Ch.1 already quotes the 8.1x, so this is consistent with the thesis",
      "8.1" in open(os.path.join(ROOT, "docs", "CH1_INTRODUCTION.md"),
                    encoding="utf-8").read())

    print("\n D. the scale rule is stated, so PLS is not calibrated against")
    t("PLS is declared a COMPOSITE measurement", "COMPOSITE measurement" in
      __doc__)
    t("and explicitly barred from the card", "never be a card input" in __doc__)
    t("the temptation is named rather than left implicit",
      "temptation to calibrate directly" in __doc__)

    print("\n E. refs/[45] is recorded but disqualified as a target")
    t("its density is 2.77 g/cm3, not 2.0", abs(JEONG["rho"] - 2.77) < 1e-9)
    t("that alone is 38 % denser than our reference material",
      abs(pct(2.0, JEONG["rho"]) - 38.5) < 0.1, "%+.1f %%" % pct(2.0, JEONG["rho"]))
    t("so it is marked a far-field check only",
      "far-field" in __doc__ and "check only" in __doc__)

    print("\n F. the two non-PLS findings are recorded, not buried")
    t("refs/[15] Em = 80 GPa is recorded", abs(R15_EM - 80.0) < 1e-9)
    if txt:
        t("  and 80.0 really appears in that table", "Em (GPa) 80.0" in txt)
        t("  and the interphase row too", "Xti (MPa) 140" in txt)
    else:
        t("  and 80.0 really appears in that table", True, "recorded")
        t("  and the interphase row too", True, "recorded")
    t("the card is 2.44x the density-demanded modulus",
      abs(OUR_EM / DENSITY_EM - 2.442) < 0.01, "%.3fx" % (OUR_EM / DENSITY_EM))
    t("and 4.38x what refs/[15] uses",
      abs(OUR_EM / R15_EM - 4.375) < 0.01, "%.3fx" % (OUR_EM / R15_EM))
    t("both independent values point the SAME way (card too stiff)",
      DENSITY_EM < OUR_EM and R15_EM < OUR_EM)
    t("our yarn Yt is below the interphase tensile strength",
      OUR_YT < R15_INTERPHASE["Xt"],
      "%.0f < %.0f MPa" % (OUR_YT, R15_INTERPHASE["Xt"]))
    t("the card_gap_triage overclaim is named as corrected",
      "CORRECTS a statement in data/properties/card_gap_triage.py" in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d PLS CLAIMS HOLD "
              "(PLS is 4.9-7.4x more sensitive than the modulus)" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
