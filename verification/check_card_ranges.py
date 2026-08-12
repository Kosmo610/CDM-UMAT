#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_card_ranges.py  --  is every card input inside an independent range?
==========================================================================
The existing checks all answer "is this number what its own source says".
None of them answers the question you ask before committing solver time:

    is this number PLAUSIBLE against literature that is not its source?

Those are different failures.  A value transcribed perfectly from one paper can
still be an outlier against every other measurement of the same quantity, and
re-deriving it from that same paper will never reveal it.  This round compares
each card input against INDEPENDENT literature and sorts it into one of four
verdicts:

  IN     the value sits inside a range measured by a source that is not where
         the value came from
  DEV    the value sits OUTSIDE that range.  Allowed, but only with a written
         reason; the reason is asserted to exist, so it cannot be dropped
  GUESS  no independent value was found and the number is a calibration
         starting guess, recorded as such in verification/CALIBRATION_GUIDE.md
  DERIV  no independent value either, but the number is NOT free: a published
         equation fixes it from other slots, so tuning it is over-parameter-
         isation.  Written as "DERIVED" in the table

A GUESS is not a defect -- some of these are knobs that calibration is supposed
to move.  It IS a defect to run the matrix without knowing which numbers are
guesses, which is what this list is for.

The audit table is asserted against the SHIPPED DECK, so it cannot go stale: if
a card value changes and this table does not, the check fails.

Run:  python3 verification/check_card_ranges.py
"""
from __future__ import print_function

import math
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DECK_ZIP = os.path.join(ROOT, "dist", "M4_DRIVERFIX_0730_1623.zip")
DECK_IN_ZIP = "M4_DRIVERFIX_0730_1623/M4_c26k_RT23.inp"
GUIDE = os.path.join(ROOT, "verification", "CALIBRATION_GUIDE.md")

#: Pinned verdict counts.  These are a FINDING, not a target: only 7 of the 26
#: audited inputs currently have support from a source other than the one they
#: came from.  Ch.4 4.9 quotes these three numbers, so they cannot drift.
#:
#: 2026-08-03: 8 -> 7 IN, 4 -> 5 DEV.  Yarn Xt was regraded.  An IN verdict is
#: only worth what its comparison source is worth, and that row's was a strand
#: datasheet figure being compared against another strand datasheet figure.
#: The count went DOWN because the audit got sharper, which is the only
#: direction this number is allowed to move for a good reason.
#: 2026-08-11: GUESS 14 -> 13, and a fourth verdict DERIVED appears with 1 row.
#: Slot 37 (rF) was regraded GUESS -> DERIVED: Ge refs/[24] Eq. (17) makes the
#: linear-to-exponential transition threshold a FUNCTION of X_PO (slot 36) and
#: K1 (slot 38), so it was never an independent knob.  See
#: refs/GE2018_EXTRACTION.md B-2 judgement 3.
EXPECTED_IN, EXPECTED_DEV, EXPECTED_GUESS, EXPECTED_DERIVED = 7, 5, 13, 1

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))


def deck_text():
    with zipfile.ZipFile(DECK_ZIP) as z:
        return z.read(DECK_IN_ZIP).decode("utf-8", "replace")


def card(text, nconst):
    head = "*User Material, constants=%d\n" % nconst
    i = text.index(head)
    j = text.index("*", i + len(head))
    return [float(x) for ln in text[i + len(head):j].strip().splitlines()
            for x in ln.split(",") if x.strip()]


def expansions(text):
    out = []
    for m in re.finditer(r"\*Expansion[^\n]*\n([^\*]+)", text):
        out.append([float(x) for x in m.group(1).replace("\n", ",").split(",")
                    if x.strip()])
    return out


# --------------------------------------------------------------------------
# Independent-range audit table.
#
#   slot   where the value lives (card, index) or a symbolic key
#   value  what the deck must contain
#   lo,hi  the INDEPENDENT range (None,None = none found)
#   src    the independent source -- must NOT be the source of the value
#   why    reason, required for DEV and GUESS
# --------------------------------------------------------------------------
E = lambda v: v          # noqa: E731  (readability in the table below)

MATRIX = [
    # (slot, name, value, lo, hi, verdict, independent source, note)
    (2, "E matrix [MPa]", 350000.0, 300000.0, 460000.0, "IN",
     "Snead refs/[06]: dense CVD SiC E0 = 460 GPa with E = E0*exp(-3.57*Vp)",
     "350 GPa implies 7.7 % matrix porosity, which is low but plausible for "
     "PIP; the value itself is Zhang 2022 Table 2"),
    (3, "nu matrix", 0.20, 0.14, 0.21, "IN",
     "Snead refs/[06]: 0.14-0.20 sintered/reaction-bonded, 0.21 pure CVD", ""),
    (4, "Xt matrix [MPa]", 310.0, 205.0, 532.0, "IN",
     "Snead refs/[06] Table 7: Weibull characteristic strength of bulk CVD "
     "SiC spans 205-532 MPa across test methods", ""),
    (5, "Xc matrix [MPa]", 310.0, 205.0, 532.0, "IN",
     "same as Xt; Zhang 2022 sets them equal", ""),
    (15, "Gm_t [N/mm]", 0.031, 0.0293, 0.0350, "IN",
     "Snead refs/[06] KIc = 3.2-3.5 MPa.m^0.5 converted at OUR E = 350 GPa",
     ""),
    (16, "Gm_c [N/mm]", 0.031, 0.0293, 0.0350, "IN",
     "same conversion", ""),
    (17, "SY0 [MPa]", 250.0, None, None, "GUESS",
     "no independent value: SiC is brittle and the plasticity is a numerical "
     "device, not a measured yield point",
     "calibration knob; 250 MPa is 81 % of Xt = 310"),
    (18, "HISO [MPa]", 100000.0, None, None, "GUESS",
     "no independent value: linear isotropic hardening of a brittle ceramic "
     "is a numerical device with no measured counterpart",
     "calibration knob, paired with SY0"),
    (8, "dmax_t matrix", 0.90, None, None, "GUESS",
     "numerical cap, not a material property", "retuned from 0.99 to 0.90"),
    (10, "eta matrix", 0.05, None, None, "GUESS",
     "viscous regularisation, not a material property", "retuned"),
]

YARN = [
    # REGRADED 2026-08-03, IN -> DEV.  The old range [2700, 2900] was built
    # from Toray's 3530 datasheet figure, which is a STRAND value -- the same
    # kind of number as the card's own 3580.  Agreeing with it demonstrated
    # nothing except that two strand figures agree.  The first genuinely
    # independent source is a direct measurement of the filament, and the card
    # is 1.70x above it.  See data/properties/insitu_yarn_strength.py.
    (11, "Xt yarn [MPa]", 2835.0, 475.0, 1815.0, "DEV",
     "refs/[08] Sauder, Lamon & Pailler, Compos. Sci. Technol. 62 (2002) 499 "
     "Table 1 MEASURED T300 single filaments: sigma_R = 2107 MPa at 24 C and "
     "2292 MPa at 1000 C on a 50 mm gauge, giving Vf*sigma_R = 1669-1815 MPa. "
     "The same table's Weibull parameters, evaluated at the RVE's own aligned "
     "fibre volume of 1.063 mm^3, give 475-745 MPa. refs/[10] Yang, J. Eur. "
     "Ceram. Soc. 37 (2017) 1281 Table 2 uses those same Weibull values as "
     "the fibre strength in a 2D C/SiC strength model",
     "the card is 1.6x the highest independent value and 6.0x the lowest. "
     "The rule-of-mixtures composite bound it implies is 706 MPa against a "
     "measured 248-259 MPa, so this is the M6 calibration target, not a "
     "tolerable deviation. Left in the SHIPPED deck because that deck is the "
     "audited artefact; M6 replaces it"),
    (12, "Xc yarn [MPa]", 1956.0, None, None, "GUESS",
     "no independent compressive strength for T300 filaments was found",
     "rule of mixtures Vf*2470 from Zhang 2022 Table 1"),
    (13, "Yt yarn [MPa]", 80.0, None, None, "GUESS",
     "no C/SiC tow transverse tensile strength found. Ge refs/[24] gives 70 "
     "MPa but for a PHENOLIC matrix; Shi refs/[31] gives 36.5 MPa but for the "
     "COMPOSITE, not a tow",
     "CALIBRATION_GUIDE lists this as a main knob"),
    (14, "Yc yarn [MPa]", 350.0, None, None, "GUESS",
     "no C/SiC tow transverse compressive strength found; Ge refs/[24] gives "
     "170 MPa for a phenolic matrix",
     "CALIBRATION_GUIDE lists this as a main knob"),
    (15, "S12 yarn [MPa]", 120.0, None, None, "GUESS",
     "Ge refs/[24] Table 3 gives 58 MPa but for a PHENOLIC matrix; "
     "no tow-level shear strength found for C/SiC. Composite-level in-plane shear is "
     "125.7 MPa (Yang refs/[27]) and 144.1 MPa (Yan refs/[35]), but for a 2D "
     "weave those load the tows AXIALLY, so they do not bound the tow's own "
     "shear strength",
     "CALIBRATION_GUIDE lists this as a main knob"),
    (17, "S23 yarn [MPa]", 100.0, None, None, "GUESS",
     "no independent value; Ge refs/[24] gives 46 MPa for a phenolic matrix",
     "CALIBRATION_GUIDE lists this as a main knob"),
    (32, "G1t yarn [N/mm]", 12.5, None, None, "DEV",
     "Ge refs/[24] Table 3, but that table is carbon/PHENOLIC",
     "fibre-dominated mode and both materials use T300, so the transfer is "
     "arguable; recorded in data/properties/yarn_fracture_energy.py"),
    (33, "G1c yarn [N/mm]", 12.5, None, None, "DEV",
     "Ge refs/[24] Table 3, the same carbon/PHENOLIC table that supplies G1t",
     "fibre-dominated and both materials use T300; same reasoning as G1t"),
    (34, "Gtt yarn [N/mm]", 0.0, None, None, "GUESS",
     "0 disables the crack band. A sourced value now exists -- Shi refs/[31] "
     "0.107 N/mm on 2D plain weave C/SiC -- but the card has not been "
     "regenerated",
     "see data/properties/yarn_fracture_energy.py"),
    (35, "Gtc yarn [N/mm]", 0.0, None, None, "GUESS",
     "0 disables the crack band; no transverse compressive fracture energy "
     "for C/SiC exists in the literature searched; Ge refs/[24] Table 3 does "
     "publish Gf,2(3)t = Gf,2(3)c = 1.0 N/mm for carbon/phenolic, so 0.0 is our "
     "switch-off, not a missing source",
     "see data/properties/yarn_fracture_energy.py"),
    (36, "X_PO yarn [MPa]", 700.0, None, None, "GUESS",
     "pull-out parameter of the mixed softening law.  NOT 'not yet found': "
     "a1-0035 read the lineage's primary source, refs/[73] Zhong 2015, and "
     "S_po is absent there too.  Declared knob, search closed",
     "roughly 0.25*Xt; CALIBRATION_GUIDE knob.  Lineage is epoxy-matrix -> "
     "DEV even if a number existed"),
    (37, "rF yarn", 3.0, None, None, "DERIVED",
     "Ge refs/[24] Eq.(17) fixes r^F_f,1t as the transition point implied by "
     "X_PO and K1 -- it is NOT an independent input.  refs/[73], the primary "
     "source of that lineage, says the same in words: r^F_f,1t and S_po lie "
     "on the intersection of the linear and exponential laws (a1-0035)",
     "should be computed from slots 36/38, not tuned"),
    (38, "K1 yarn [MPa]", 8000.0, None, None, "GUESS",
     "linear softening slope.  Absent from refs/[73] as well, so the trail "
     "is closed rather than open (a1-0035)",
     "declared knob; epoxy-matrix lineage -> DEV regardless"),
]

# Constituent CTEs, which live on *Expansion rather than in the cards.
# These are the ones that drive the thermal residual stress, so they get the
# closest look.
CTE = [
    ("alpha matrix [1/K]", 4.5e-6, 4.2e-6, 4.6e-6, "IN",
     "Snead refs/[06]: mean CTE over 298-1273 K = 4.4e-6/K, stated in the "
     "handbook summary; our correlation reproduces 4.397e-6",
     ""),
    ("alpha yarn axial [1/K]", 1.070925962822e-06, None, None, "DEV",
     "Schapery homogenisation of a fibre whose axial CTE is -0.3e-6 (Zhang "
     "2022 Table 1). Pradere refs/[07] measured 1.6-2.1e-6 as a MEAN to "
     "2500 K on ex-PAN and pitch fibres, and our own secant of PANEX 33 over "
     "23-1050 C gives +1.237e-6 against the card's -0.3e-6",
     "different fibre grade and a different reference convention; the "
     "disagreement is real and is why constituent CTE is a sensitivity "
     "parameter. It pushes TRS in the direction of the 2.34x over-prediction"),
    ("alpha yarn transverse [1/K]", 3.324908565604e-06, None, None, "DEV",
     "Pradere refs/[07] abstract: mean transverse CTE of carbon fibres is "
     "5e-6 to 10e-6 /K. The card's fibre value 3.1e-6 is BELOW that band, "
     "and our PANEX 33 secant gives 5.630e-6",
     "the yarn value 3.32e-6 follows from the fibre 3.1e-6, so it inherits "
     "the deviation. Flagged as a sensitivity parameter, not corrected, "
     "because the card is Zhang's own verified T300 set"),
]


def main():
    print("=" * 78)
    print("check_card_ranges.py -- card inputs vs INDEPENDENT literature")
    print("=" * 78)

    if not os.path.exists(DECK_ZIP):
        check("shipped deck present", False, DECK_ZIP)
        return 1
    text = deck_text()
    check("shipped deck readable", True, os.path.basename(DECK_ZIP))

    m = card(text, 25)
    y = card(text, 38)
    exps = expansions(text)
    check("matrix card has 25 slots", len(m) == 25, "%d" % len(m))
    check("yarn card has 38 slots", len(y) == 38, "%d" % len(y))
    check("two *Expansion blocks (matrix isotropic, yarn ortho)",
          len(exps) == 2, "%d" % len(exps))

    # ---------------------------------------------------------------- A
    print("\n A. the audit table matches the shipped deck (no stale rows)")
    for slot, name, val, lo, hi, verdict, src, why in MATRIX:
        got = m[slot - 1]
        check("matrix slot %-2d %s" % (slot, name), abs(got - val) < 1e-9,
              "deck %g vs table %g" % (got, val))
    for slot, name, val, lo, hi, verdict, src, why in YARN:
        got = y[slot - 1]
        check("yarn slot %-2d %s" % (slot, name), abs(got - val) < 1e-9,
              "deck %g vs table %g" % (got, val))
    check("matrix CTE matches the table",
          abs(exps[0][0] - CTE[0][1]) < 1e-12, "%g" % exps[0][0])
    check("yarn axial CTE matches the table",
          abs(exps[1][0] - CTE[1][1]) < 1e-15, "%g" % exps[1][0])
    check("yarn transverse CTE matches the table",
          abs(exps[1][1] - CTE[2][1]) < 1e-15, "%g" % exps[1][1])

    # ---------------------------------------------------------------- B
    print("\n B. every IN verdict really is inside its independent range")
    rows = ([("matrix", r) for r in MATRIX] + [("yarn", r) for r in YARN]
            + [("cte", ("-",) + r) for r in CTE])
    n_in = n_dev = n_guess = n_der = 0
    for grp, r in rows:
        slot, name, val, lo, hi, verdict, src, why = r
        if verdict == "IN":
            n_in += 1
            check("%s is in [%g, %g]" % (name, lo, hi),
                  lo is not None and lo <= val <= hi, "%g" % val)
        elif verdict == "DEV":
            n_dev += 1
            # A DEV row may leave the range unstated when the independent
            # source gives a qualitative bound only.  But if it DOES state
            # one, the value had better be outside it -- otherwise a row can
            # be moved IN -> DEV to dodge a failing comparison, which is the
            # same dishonesty as widening a tolerance.
            if lo is not None and hi is not None:
                check("%s is really OUTSIDE [%g, %g]" % (name, lo, hi),
                      not (lo <= val <= hi),
                      "%g, by %.2fx" % (val, val / hi if val > hi else lo / val))
        elif verdict == "DERIVED":
            n_der += 1
        else:
            n_guess += 1

    # ---------------------------------------------------------------- C
    print("\n C. every DEV, GUESS and DERIVED carries a written reason")
    for grp, r in rows:
        slot, name, val, lo, hi, verdict, src, why = r
        if verdict in ("DEV", "GUESS", "DERIVED"):
            check("%s has an independent-source note" % name,
                  len(src.strip()) > 20, "%d chars" % len(src.strip()))
            check("%s has a reason recorded" % name,
                  len(why.strip()) > 0 or verdict == "GUESS")
    check("no verdict outside {IN, DEV, GUESS, DERIVED}",
          all(r[5] in ("IN", "DEV", "GUESS", "DERIVED") for _, r in rows))

    # ---------------------------------------------------------------- D
    print("\n D. every GUESS is declared a knob in CALIBRATION_GUIDE.md")
    guide = open(GUIDE).read() if os.path.exists(GUIDE) else ""
    check("CALIBRATION_GUIDE.md exists", bool(guide))
    for label, needle in (("Yt", "Yt"), ("Yc", "Yc"), ("S12", "S12"),
                          ("SY0", "SY0"), ("HISO", "HISO"),
                          ("X_PO", "X_PO"), ("K1", "K1")):
        check("%s appears in CALIBRATION_GUIDE" % label, needle in guide)
    check("the guide marks the yarn transverse strengths as knobs",
          "주요 knob" in guide)

    # ---------------------------------------------------------------- E
    print("\n E. derived quantities that the ranges imply")
    # matrix porosity implied by E, via Snead's own exponential
    vp = -math.log(350000.0 / 460000.0) / 3.57
    check("E = 350 GPa implies a physically sensible matrix porosity",
          0.0 < vp < 0.30, "Vp = %.1f %%" % (100.0 * vp))
    # our yarn Vf must reproduce the card's Xt by rule of mixtures
    vf = 2835.0 / 3580.0
    check("Xt/3580 recovers the verified yarn Vf = 0.79194",
          abs(vf - 0.79194) < 5e-5, "%.5f" % vf)
    # the same Vf must also reproduce Xc
    check("the same Vf reproduces Xc = Vf*2470",
          abs(vf * 2470.0 - 1956.0) < 1.0, "%.1f" % (vf * 2470.0))
    # transverse compressive/tensile strength ratio
    check("Yc/Yt ratio is what the crack-band audit used",
          abs(350.0 / 80.0 - 4.375) < 1e-9)

    # ---------------------------------------------------------------- F
    print("\n F. summary")
    print("     IN    %2d  inside an independent range" % n_in)
    print("     DEV   %2d  outside it, with a written reason" % n_dev)
    print("     GUESS %2d  calibration knobs, no independent value found"
          % n_guess)
    print("     DERIV %2d  fixed by a published equation from other slots"
          % n_der)
    # NOT a quality bar.  8 of 26 is the actual state of the data, and moving
    # a threshold until it goes green is the exact dishonesty this suite
    # exists to prevent.  The counts are pinned instead, so that changing the
    # data forces a conscious update here and in Ch.4.
    check("IN count is the declared %d" % EXPECTED_IN, n_in == EXPECTED_IN,
          "%d" % n_in)
    check("DEV count is the declared %d" % EXPECTED_DEV, n_dev == EXPECTED_DEV,
          "%d" % n_dev)
    check("GUESS count is the declared %d" % EXPECTED_GUESS,
          n_guess == EXPECTED_GUESS, "%d" % n_guess)
    check("DERIVED count is the declared %d" % EXPECTED_DERIVED,
          n_der == EXPECTED_DERIVED, "%d" % n_der)
    print("     -> %d of %d audited inputs have independent support (%.0f %%)"
          % (n_in, len(rows), 100.0 * n_in / len(rows)))
    check("nothing is silently unclassified",
          n_in + n_dev + n_guess + n_der == len(rows))

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), "; ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ALL %d CARD-RANGE CLAIMS HOLD "
          "(%d IN / %d DEV / %d GUESS / %d DERIVED)"
          % (len(_OK), n_in, n_dev, n_guess, n_der))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
