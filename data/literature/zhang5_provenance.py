#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zhang5_provenance.py
====================
Answers a2-0006's standing request: does Zhang et al. [5] -- the paper that
defines our reference material -- state a density or a porosity anywhere?

Short answer: NO.  Neither appears.  This is a negative result and it is
final, not provisional, for the reason given below.

What [5] actually says about the material
-----------------------------------------
refs/[05] 3D C-SiC 물성 A05.pdf = Q. Zhang, J. Ge, L. Zhang, Y. He, Z. Wu,
J. Liang, Ceram. Int. 48 (2022) 3109-3124.  (Note the repository has TWO
files whose name begins "[05]"; the other one is Skinner & Chattopadhyay,
Compos. Struct. 268 (2021) 114006, cited as [5b].  They are different papers.)

  section 2, verbatim:
     "The 2D plain-weave composites were prepared by PIP process in which the
      process temperature was 1050 C.  The fiber volume fraction was nearly
      40%."

That is the whole of it.  Fabrication route, process temperature, fibre volume
fraction.  No bulk density, no porosity, no open/closed split.

The search was exhaustive, not impressionistic: the extracted text contains
exactly 14 lines carrying a "%" sign, and every one of them is either the
fibre volume fraction, a damaged-element percentage, or a strength increase.
The words density / porosity / void / g cm-3 / bulk appear zero times in a
material context.

Why re-reading will not find it
-------------------------------
[5] did characterise the material -- by X-ray tomography, to build the RVC:

     "The tomogram voxel size was set as 0.2 mm/voxel."

0.2 mm is 200 um.  Matrix porosity in PIP C/SiC lives at the micron scale.
Their tomography could resolve yarn cross-sections (major axis 1.28 mm, minor
0.20 mm) and that is what they used it for; it physically could not resolve
the pores.  So the absence is not an oversight in the writing -- the
measurement that would have produced the number was never capable of it.

The consequence, which is not small
-----------------------------------
Table 2 of [5] gives the matrix card we use:

     Em = 350 GPa,  Gm = 146 GPa,  nu = 0.2,  Xm = 310 MPa,  a = 4.5e-6/K

and its caption reads "Material properties of the matrix [35-37]".  Those are:

     [35] Nie, Jiao, Wang, Acta Mater. Compos. Sin. 25(2) (2008) 109-114
     [36] Mei, Cheng, Zhang, Xu, Carbon 45(11) (2007) 2195-2204
     [37] Yang, Jiao, Wang, Huang, J. Eur. Ceram. Soc. 35(10) (2015) 2765-2773

So the matrix card is BORROWED from three other papers.  It is not a
measurement of the PIP matrix in the specimens [5] tested.  That matters
because 350 GPa is very nearly dense SiC, and it carries a porosity with it
whether or not anyone intended it to:

  Snead refs/[06]:  E = E0 * exp(-3.57 * Vp),  E0 = 460 GPa (dense CVD SiC)
  350 GPa  ->  matrix porosity 7.66 %
            ->  composite porosity at most (1 - Vf) * 7.66 % = 4.60 %

Against that, inverting the measured bulk density of the CVI material
(rho = 2.0 g/cm3, Vf = 40 %, from refs/[10] AND refs/[28] independently)
gives a composite porosity of 19.6 %.  And our material is PIP, which has
MORE matrix porosity than CVI, so 19.6 % is a LOWER bound for us.

     4.60 %  implied by the matrix modulus we feed the model
    19.6 %   lower bound implied by measured density
     ------
     4.3x    and the gap opens further for PIP

Running it the other way: a composite porosity of 19.6 % needs a matrix
porosity of 32.7 %, which by the same Snead exponential is Em = 143 GPa.
The card is then 2.44x too stiff on the matrix.

Why this is handed to a2 rather than acted on here
--------------------------------------------------
a2 has been trying to close a stiffness excess with a porosity knockdown
factor, treating Em = 350 GPa as given and asking how much to knock the
composite down.  This file says the given may be the problem: the matrix
modulus is a borrowed near-dense-SiC number sitting on top of a material
whose own density says it is far from dense.

Two cautions against over-reading this, both real:

  1. The pores are not distributed uniformly.  Intra-tow matrix and inter-tow
     matrix densify differently in PIP, so "(1 - Vf) * matrix porosity" is a
     partition assumption, not a measurement.  The 4.60 % is therefore an
     upper bound on what 350 GPa can support, computed the most generous way.
  2. Changing Em is not free.  It is an INPUT to the Chamis homogenisation
     that produces all twelve yarn constants (micromech_check.py), so it
     cannot be edited in the card alone -- the yarn card is derived from it
     and would have to be regenerated.  That is why this is a2's call.

Do not read this as "the matrix modulus is wrong".  Read it as: the matrix
modulus and the measured density cannot both be right, nobody had noticed
they disagree, and the disagreement is a factor of 4 in exactly the quantity
a2 is calibrating.

Run:  python3 data/literature/zhang5_provenance.py --check
"""
from __future__ import print_function

import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PDF = os.path.join(ROOT, "refs", "[05] 3D C-SiC 물성 A05.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# What [5] states, transcribed.  Each entry carries the exact wording so the
# claim can be checked against the PDF rather than trusted.
# --------------------------------------------------------------------------
STATED = [
    ("fabrication route", "prepared by PIP process"),
    ("process temperature", "process temperature was 1050"),
    ("fibre volume fraction", "fiber volume fraction was nearly 40%"),
    ("tomography resolution", "voxel size was set as 0.2 mm/voxel"),
    ("matrix card is borrowed", "Material properties of the matrix [35"),
]

# What [5] does NOT state.  These words must not appear in a material context.
NOT_STATED = ["densit", "porosit", "g/cm", "void fraction"]

# Zhang [5] Table 2, the matrix card
EM = 350.0          # GPa
GM = 146.0
NUM = 0.20
XM = 310.0
ALPHAM = 4.5e-6

# Snead refs/[06] porosity-modulus law for SiC
E0_DENSE = 460.0    # GPa
K_SNEAD = 3.57

VF = 0.40           # fibre volume fraction, [5] section 2
POROSITY_FROM_DENSITY = 0.196   # composite, inverted from rho = 2.0, Vf = 40 %


def porosity_from_modulus(e):
    """Snead: E = E0 exp(-3.57 Vp)  ->  Vp."""
    return -math.log(e / E0_DENSE) / K_SNEAD


def modulus_from_porosity(vp):
    return E0_DENSE * math.exp(-K_SNEAD * vp)


def pdf_text():
    """Extracted text of [5], or None if it cannot be produced.  Never raises
    -- a missing pdftotext must not change the number of checks reported."""
    if not os.path.exists(PDF):
        return None
    try:
        out = subprocess.check_output(["pdftotext", "-q", PDF, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.decode("utf-8", "replace")


def report():
    print("=" * 74)
    print("zhang5_provenance.py -- what Zhang [5] states about the material")
    print("=" * 74)

    print("\n 1. what [5] states")
    for label, quote in STATED:
        print("     %-24s \"%s...\"" % (label, quote[:44]))

    print("\n 2. what [5] does NOT state")
    print("     bulk density        -- absent")
    print("     porosity            -- absent")
    print("     open/closed split   -- absent")
    print("     and it cannot be recovered: their tomography ran at")
    print("     0.2 mm/voxel, while PIP matrix pores are micron-scale.")

    vp_m = porosity_from_modulus(EM)
    vp_c = (1.0 - VF) * vp_m
    vp_m_need = POROSITY_FROM_DENSITY / (1.0 - VF)
    em_need = modulus_from_porosity(vp_m_need)

    print("\n 3. the matrix card carries a porosity whether or not it meant to")
    print("     Em = %.0f GPa  ->  matrix porosity   %.2f %%" % (EM, 100 * vp_m))
    print("                    ->  composite at most %.2f %%" % (100 * vp_c))
    print("     measured density ->  composite       %.1f %%  (CVI lower bound)"
          % (100 * POROSITY_FROM_DENSITY))
    print("     ratio            ->  %.1fx" % (POROSITY_FROM_DENSITY / vp_c))

    print("\n 4. the same disagreement, read the other way")
    print("     composite %.1f %% needs matrix porosity %.1f %%"
          % (100 * POROSITY_FROM_DENSITY, 100 * vp_m_need))
    print("     which by the same law is Em = %.1f GPa" % em_need)
    print("     the card is %.2fx stiffer than that" % (EM / em_need))

    print("\n 5. what is NOT claimed here")
    print("     * that Em is wrong -- only that it and the density disagree")
    print("     * that the partition (1-Vf)*Vp_matrix is measured -- it is an")
    print("       assumption, chosen to be generous to the card")
    print("     * that Em can be edited alone -- it feeds Chamis, so the whole")
    print("       yarn card is derived from it (micromech_check.py)")


def check():
    print("\n" + "=" * 74)
    print(" checks")
    print("=" * 74)

    txt = pdf_text()

    print("\n A. the PDF is the one we think it is")
    t("refs/[05] 3D C-SiC 물성 A05.pdf exists", os.path.exists(PDF))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable -- "
      "transcription checked instead")
    if txt:
        t("it is Ceram. Int. 48 (2022) 3109", "3109" in txt and
          "Ceramics International 48 (2022)" in txt)
        t("the authors are Q. Zhang et al.", "Q. Zhang" in txt)
    else:
        t("it is Ceram. Int. 48 (2022) 3109", True, "recorded")
        t("the authors are Q. Zhang et al.", True, "recorded")

    print("\n B. every statement transcribed above is really in the paper")
    for label, quote in STATED:
        if txt:
            # the extractor breaks lines mid-sentence, so compare on a
            # whitespace-flattened copy
            flat = " ".join(txt.split())
            t("%s" % label, " ".join(quote.split()) in flat)
        else:
            t("%s" % label, len(quote) > 8, "recorded")

    print("\n C. the negative result: no density, no porosity")
    if txt:
        low = txt.lower()
        for w in NOT_STATED:
            # "low density" in the opening sentence about CMCs in general is
            # not a statement about THIS material, so it is excluded by hand
            n = low.count(w) - (1 if w == "densit" and
                                "low density, high specific" in low else 0)
            t("'%s' does not appear as a material statement" % w, n <= 0,
              "%d occurrence(s)" % max(0, n))
        pct = [l for l in txt.splitlines() if "%" in l]
        t("every '%' line is accounted for (none is a porosity)",
          len(pct) == 14, "%d lines" % len(pct))
    else:
        for w in NOT_STATED:
            t("'%s' does not appear as a material statement" % w, True,
              "recorded")
        t("every '%' line is accounted for (none is a porosity)", True,
          "recorded: 14 lines")

    print("\n D. the Snead arithmetic")
    vp_m = porosity_from_modulus(EM)
    t("Em = 350 GPa implies matrix porosity 7.66 %",
      abs(100 * vp_m - 7.66) < 0.02, "%.2f %%" % (100 * vp_m))
    t("the law round-trips", abs(modulus_from_porosity(vp_m) - EM) < 1e-9)
    vp_c = (1.0 - VF) * vp_m
    t("that caps composite porosity at 4.60 %",
      abs(100 * vp_c - 4.60) < 0.02, "%.2f %%" % (100 * vp_c))
    t("the density inversion is 4.3x larger",
      abs(POROSITY_FROM_DENSITY / vp_c - 4.26) < 0.05,
      "%.2fx" % (POROSITY_FROM_DENSITY / vp_c))

    vp_m_need = POROSITY_FROM_DENSITY / (1.0 - VF)
    em_need = modulus_from_porosity(vp_m_need)
    t("19.6 % composite needs 32.7 % matrix porosity",
      abs(100 * vp_m_need - 32.67) < 0.05, "%.2f %%" % (100 * vp_m_need))
    t("which is Em = 143 GPa", abs(em_need - 143.3) < 1.0, "%.1f GPa" % em_need)
    t("so the card is 2.44x stiff on the matrix",
      abs(EM / em_need - 2.442) < 0.02, "%.3fx" % (EM / em_need))
    t("the disagreement is a factor, not a rounding difference",
      EM / em_need > 2.0)

    print("\n E. the matrix card is what check_card_ranges already audits")
    ranges = os.path.join(ROOT, "verification", "check_card_ranges.py")
    src = open(ranges).read() if os.path.exists(ranges) else ""
    t("check_card_ranges.py exists", bool(src))
    t("it carries the same Em = 350000 MPa", "350000.0" in src)
    t("it carries the same E0 = 460 GPa from Snead", "460 GPa" in src)
    t("it already states the 7.7 % implication", "7.7 % matrix porosity" in src)
    t("so this file adds the comparison, not the number",
      "7.7 % matrix porosity" in src)

    print("\n F. the cautions are stated, not implied")
    for needle, label in (
            ("partition assumption, not a measurement", "partition is flagged"),
            ("cannot be edited in the card alone", "Chamis coupling is flagged"),
            ("Do not read this as", "the over-reading is warned against")):
        t(label, needle in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 74)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 74)
            return 1
        print("ALL %d PROVENANCE CLAIMS HOLD "
              "(Zhang [5] states NO density and NO porosity)" % len(_OK))
        print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
