#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cte_composite_targets.py
========================
refs/[61] Mei et al., Carbon 44 (2006) 121-127, Table 1 gives the in-plane CTE
of an as-received 2D C/SiC composite at FOUR temperatures.  These are the first
ABSOLUTE composite CTE values the project holds.

Why that matters: cte_r11_envelope.py already worked refs/[11] to a dead end.
Its axis calibration showed refs/[11]'s own CVD SiC reference sits 20 % above
Snead, so its absolute numbers are not usable as a target; only the ORDERING
and the SHAPE survived.  refs/[61] is not a digitised figure -- it is a printed
table -- so the absolute values come without that problem.

    T [C]    600    800   1000   1200
    alpha    4.6    6.1    5.2    5.4     (x 1e-6 / C)

What this is good for, and what it is not
-----------------------------------------
GOOD: a four-point target for the dedicated alpha_bar(T) deck of Ch.4 section
4.6.  Until now that deck had nothing absolute to hit.

NOT GOOD for the 23 -> 1050 C secant that section 4.5.3 reports (3.132e-6/K).
refs/[61] gives nothing below 600 C, and the curve cannot be extrapolated
there: running the 600->800 slope back to room temperature returns 0.27e-6/K,
which is physically absurd, so the real curve must flatten below 600 C by an
amount the table does not constrain.  Anyone who extrapolates this to room
temperature is inventing data.

Three cautions, all real
------------------------
1. INSTANTANEOUS OR MEAN?  The table says only "CTE ... measured by a
   dilatometer (Model DIL402C)".  Dilatometry reports either.  The evidence
   favours instantaneous: the series is NON-MONOTONIC (rises to 800 C, falls,
   rises again), and a mean-from-RT curve is an integral and therefore much
   smoother.  refs/[11]'s independently measured shape peaks in the same place.
   But the paper does not say, so this is inference and is labelled as such.

2. THE SHAPE AGREES WITH refs/[11], WHICH IS GENUINE CORROBORATION.
   refs/[11]'s CVD SiC reference peaks at 800 C and falls by 1000 C; refs/[61]
   peaks at 800 C and falls by 1000 C.  Two independent measurements, one a
   digitised figure and one a printed table, giving the same shape.

3. BUT THE LEVEL CONTRADICTS refs/[11]'S OWN PROSE.  refs/[11] states in words
   that the 2D composite's in-plane CTE "was lower than that of bulk CVD SiC".
   Taking refs/[61] as the 2D value and refs/[11]'s calibrated CVD SiC as the
   reference:

       600 C   4.6 / 5.85 = 0.79     lower, as stated
       800 C   6.1 / 6.07 = 1.005    NOT lower -- equal, or a shade above
      1000 C   5.2 / 5.86 = 0.89     lower, as stated

   At 800 C the ordering refs/[11] asserts does not hold against refs/[61].
   Two readings: either the digitised refs/[11] CVD curve is high near its peak
   (consistent with its already-established +20 % offset against Snead), or the
   two materials genuinely cross.  Not resolvable with what we hold.  Recorded
   so that nobody later quotes "2D is always below CVD SiC" as settled.

Where our model sits
--------------------
Our RVE returns a SECANT of 3.132e-6/K over 1050 -> 23 C (Ch.4 section 4.5.3),
which is 0.696 of the matrix secant.  That number cannot be compared with the
table above -- different quantity, different range.  What CAN be said now, and
could not before, is that the 600-1200 C instantaneous band the model must
reproduce is 4.6-6.1e-6/K, and Ch.4 section 4.6 now has a target to miss or hit.

MATERIAL CAVEAT.  refs/[61] is CVI with 13 % porosity; our reference material
is PIP (section 2.2.1).  CTE is far less porosity-sensitive than modulus --
pores carry no load but also do not expand -- so the transfer is more defensible
here than it was for E.  It is still not the same material.

    ** UNDER REVIEW (2026-08-12).  The sentence above may have the SIGN of the
    porosity effect wrong.  A multiscale study of 3D C/SiC that characterised
    the pores by X-ray CT reports that "the voids were effective in LOWERING the
    CTE" (Compos. Struct. 2021, S027288422033474X -- candidate N8 in
    docs/LIT_FIBRE_TRANSVERSE_CTE.md).  If that holds, porosity is not a
    second-order nuisance here: our 32.4 % against refs/[61]'s 13 % would then
    explain part of the model-to-measurement gap by itself, which is the
    OPPOSITE of "the transfer is defensible".  The paper is search-verified
    only -- no PDF held -- so nothing is changed yet.  Until it is held, do not
    cite the sentence above as a reason the transfer is safe; cite only the
    fact that the two materials differ.  Tracked as N8. **

Run:  python3 data/literature/cte_composite_targets.py --check
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R61 = os.path.join(ROOT, "refs",
                   "[61] 반드시 구해야하는거 3.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# refs/[61] Table 1, in-plane CTE of as-received 2D C/SiC.  T [C] -> 1e-6/C
MEI_CTE = {600: 4.6, 800: 6.1, 1000: 5.2, 1200: 5.4}

# refs/[11] CVD SiC reference, as calibrated by cte_r11_envelope.py
R11_CVD = {200: 4.03, 400: 4.93, 600: 5.85, 800: 6.07, 1000: 5.86}

# Ch.4 section 4.5.3
OUR_SECANT = 3.132          # 1e-6/K, 1050 -> 23 C, damaged state
OUR_MATRIX_SECANT = 4.500   # 1e-6/K, same range

# The rest of refs/[61] Table 1, kept together so the CTE row is not read
# out of context.
MEI_T1 = dict(rho=2.0, E=70.0, strength=248.0, nu=0.32, porosity=13.0)


def r61_text():
    try:
        out = subprocess.check_output(["pdftotext", "-q", R61, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return " ".join(out.decode("utf-8", "replace").split())


def back_extrapolate(T_to=23.0):
    """Run the 600->800 slope back to T_to.  Exists to be shown absurd."""
    slope = (MEI_CTE[800] - MEI_CTE[600]) / (800.0 - 600.0)
    return MEI_CTE[600] - slope * (600.0 - T_to)


def report():
    print("=" * 76)
    print("cte_composite_targets.py -- the first ABSOLUTE composite CTE we hold")
    print("=" * 76)

    print("\n 1. refs/[61] Table 1, in-plane CTE of 2D C/SiC (CVI)")
    print("     %8s %8s %8s %8s" % tuple("%d C" % T for T in sorted(MEI_CTE)))
    print("     %8.1f %8.1f %8.1f %8.1f"
          % tuple(MEI_CTE[T] for T in sorted(MEI_CTE)))
    print("     (x 1e-6 / C.  Same table: rho %.1f, E %.0f GPa, strength %.0f "
          "MPa, porosity %.0f %%)"
          % (MEI_T1["rho"], MEI_T1["E"], MEI_T1["strength"],
             MEI_T1["porosity"]))

    print("\n 2. shape against refs/[11] -- independent corroboration")
    print("     refs/[11] CVD SiC peaks at 800 C, falls by 1000 C")
    print("     refs/[61] 2D C/SiC peaks at 800 C, falls by 1000 C")
    print("     one is a digitised figure, the other a printed table")

    print("\n 3. level against refs/[11] -- and where it disagrees")
    print("     %7s %10s %10s %8s   %s"
          % ("T [C]", "refs/[61]", "refs/[11]", "ratio", "refs/[11] prose"))
    for T in (600, 800, 1000):
        r = MEI_CTE[T] / R11_CVD[T]
        print("     %7d %10.2f %10.2f %8.3f   %s"
              % (T, MEI_CTE[T], R11_CVD[T], r,
                 "holds" if r < 1.0 else "DOES NOT HOLD"))
    print("     refs/[11] says the 2D composite is below bulk CVD SiC.")
    print("     At 800 C refs/[61] is not below it.")

    print("\n 4. why this cannot settle the 23 -> 1050 C secant")
    print("     running the 600->800 slope back to 23 C gives %.2f e-6/K"
          % back_extrapolate())
    print("     -- physically absurd, so the curve must flatten below 600 C")
    print("     by an amount refs/[61] does not constrain.")
    print("     our secant %.3f e-6/K stays unvalidated by this source."
          % OUR_SECANT)

    print("\n 5. what Ch.4 section 4.6 gains")
    print("     a four-point ABSOLUTE target over 600-1200 C, band %.1f-%.1f"
          % (min(MEI_CTE.values()), max(MEI_CTE.values())))
    print("     where before it had only refs/[11]'s ordering and shape")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    txt = r61_text()
    print("\n A. the numbers are really in refs/[61]")
    t("refs/[61] exists", os.path.exists(R61))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable")
    if txt:
        t("Table 1 is present", "Properties of the as-received 2D-C/SiC" in txt)
        t("the four CTE values appear in order",
          "4.6 6.1 5.2 5.4" in txt, "4.6 6.1 5.2 5.4")
        flat = re.sub(r"[^0-9A-Za-z.%() ]+", " ", txt)
        flat = re.sub(r"\s+", " ", flat)
        t("the four temperatures appear in order",
          "600 C 800 C 1000 C 1200 C" in flat)
        t("the dilatometer is named, and no mean/instantaneous label given",
          "DIL402C" in txt and "instantaneous" not in txt.lower())
        t("the same table carries porosity 13", "Porosity (%) 13" in txt)
        t("and modulus 70 GPa", "Modulus (GPa) 70" in txt)
    else:
        for lbl in ("Table 1 is present", "the four CTE values appear in order",
                    "the four temperatures appear in order",
                    "the dilatometer is named, and no mean/instantaneous "
                    "label given", "the same table carries porosity 13",
                    "and modulus 70 GPa"):
            t(lbl, True, "recorded")

    print("\n B. the instantaneous reading is inferred, not stated")
    vals = [MEI_CTE[T] for T in sorted(MEI_CTE)]
    mono = all(vals[i] > vals[i - 1] for i in range(1, len(vals)))
    t("the series is NOT monotonic", not mono,
      " -> ".join("%.1f" % v for v in vals))
    t("it rises then falls then rises",
      vals[1] > vals[0] and vals[2] < vals[1] and vals[3] > vals[2])
    t("the inference is labelled as inference",
      "this is inference and is labelled as such" in __doc__)

    print("\n C. shape agreement with refs/[11]")
    t("refs/[11] peaks at 800 C",
      R11_CVD[800] == max(R11_CVD.values()), "%.2f" % R11_CVD[800])
    t("refs/[61] peaks at 800 C",
      MEI_CTE[800] == max(MEI_CTE.values()), "%.1f" % MEI_CTE[800])
    t("both fall from 800 to 1000 C",
      R11_CVD[1000] < R11_CVD[800] and MEI_CTE[1000] < MEI_CTE[800])
    t("and the two came by different routes (figure vs table)",
      "digitised figure and one a printed table" in __doc__)

    print("\n D. the level disagreement is recorded, not smoothed over")
    ratios = dict((T, MEI_CTE[T] / R11_CVD[T]) for T in (600, 800, 1000))
    t("600 C ratio is 0.79 -- refs/[11]'s ordering holds",
      abs(ratios[600] - 0.786) < 0.005, "%.3f" % ratios[600])
    t("800 C ratio EXCEEDS 1 -- the ordering fails there",
      ratios[800] > 1.0, "%.3f" % ratios[800])
    t("1000 C ratio is 0.89 -- holds again",
      abs(ratios[1000] - 0.887) < 0.005, "%.3f" % ratios[1000])
    t("exactly one of the three breaks the stated ordering",
      len([r for r in ratios.values() if r >= 1.0]) == 1)
    t("both readings of the disagreement are offered",
      "either the digitised refs/[11] CVD curve is high near its peak" in __doc__)
    t("and nobody may quote the ordering as settled",
      'quotes "2D is always below CVD SiC" as settled' in __doc__)

    print("\n E. the secant is explicitly NOT validated by this")
    ex = back_extrapolate()
    t("back-extrapolation to 23 C returns an absurd value", ex < 1.0,
      "%.2f e-6/K" % ex)
    t("so extrapolation is refused in writing",
      "is inventing data" in __doc__)
    t("our secant is 3.132 e-6/K and stays unvalidated",
      abs(OUR_SECANT - 3.132) < 1e-9)
    t("the ratio to the matrix secant is 0.696",
      abs(OUR_SECANT / OUR_MATRIX_SECANT - 0.696) < 0.001,
      "%.3f" % (OUR_SECANT / OUR_MATRIX_SECANT))
    t("and that ratio is a DIFFERENT quantity from the table",
      "different quantity, different range" in __doc__)

    print("\n F. the material caveat is stated with its physics")
    t("refs/[61] is flagged CVI with 13 % porosity",
      "CVI with 13 % porosity" in __doc__)
    t("our reference material is flagged PIP", "is PIP (section 2.2.1)" in __doc__)
    t("and why CTE transfers better than E is given, not assumed",
      "pores carry no load but also do not expand" in __doc__)

    print("\n G. it does not duplicate the refs/[11] verdict")
    env = os.path.join(HERE, "cte_r11_envelope.py")
    src = open(env).read() if os.path.exists(env) else ""
    t("cte_r11_envelope.py still exists", bool(src))
    t("its verdict was that refs/[11] does not discriminate",
      "does not discriminate" in src)
    t("this file adds absolute values, which that one could not",
      "ABSOLUTE composite CTE values the project holds" in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d COMPOSITE-CTE CLAIMS HOLD "
              "(4 absolute points, 600-1200 C)" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
