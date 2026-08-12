#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
card_gap_triage.py
==================
Answers a2-0005: of the 14 card slots that check_card_ranges.py grades GUESS,
which are calibration knobs that never had a measurable counterpart, and which
are real material properties we simply failed to source?

a2 asked because the two are not the same defect.  A knob with no source is
fine -- calibration is what it is for, and the thesis reports it as an
identified parameter.  A property with no source is a hole, and the thesis has
to either fill it or declare it.  Only the literature side can tell them apart,
so the triage lives here.

The verdicts
------------
    KNOB     no measurable counterpart exists, even in principle.  Either a
             numerical device (a cap, a viscosity) or an auxiliary variable of
             a published equation whose authors did not publish its value.
             Requirement: declared in CALIBRATION_GUIDE.md.  Nothing else.

    DERIVED  not independently sourced, but not guessed either -- it follows
             from a sourced number by a stated rule.  Requirement: the rule is
             written down and reproduces the card value.

    GAP      a real, measurable material property with no source found.
             Requirement: the thesis declares it, and the calibrated value is
             reported as identified, not as measured.

Result: 6 KNOB, 2 DERIVED, 6 GAP.  (rF moved KNOB -> DERIVED on 2026-08-11
after the Ge original was read -- see refs/GE2018_EXTRACTION.md.)

What this cost us to find out
-----------------------------
Two tow-level property cards were sitting unread in refs/ the whole time.
Neither is our material, but both are independent, and until now the audit
table said "no tow-level source found" for Yt/Yc/S12/S23 without either of
them having been opened.

  refs/[17]  P. Zhang, Zhu, Tong, Li, Xing, Lan, Sun, Liang,
             J. Mater. Res. Technol. 29 (2024) 2016-2034,
             doi:10.1016/j.jmrt.2024.01.260.
             Table 5, "RVE-F" = the FIBRE TOW model of a 3D needled C/C-SiC.
             Right scale, ceramic matrix.  But the values are computed
             ("acquired with the analytical approach and FEM"), not measured,
             so they anchor a range -- they are not a measurement.

  refs/[25]  C. Zhang, Curiel-Sosa, Bui, Compos. Struct. 201 (2018) 62-71,
             doi:10.1016/j.compstruct.2018.06.021.
             Table 1, braiding yarn.  Right scale, WRONG matrix: the companion
             matrix is E = 3.5 GPa, nu = 0.35, Xt = 80 MPa, which is an epoxy.
             Filed under "3D C-SiC 물성 B02"; it is not a C/SiC paper.

Why the four tow strengths still cannot be promoted
---------------------------------------------------
The two independent cards disagree with EACH OTHER by 4.1x to 11x, which is
more than either disagrees with us.  A quantity bracketed that loosely by
sources differing only in matrix cannot be pinned, so none of the four can be
promoted out of GAP.

But the bracket is not useless, and it does not treat the four alike:

    Yt  = 80   inside  [13.80,  86.0]   not sourced, not contradicted
    S12 = 120  inside  [16.96, 186.0]   not sourced, not contradicted
    Yc  = 350  ABOVE   [60.83, 249.0]   1.41x the highest independent value
    S23 = 100  ABOVE   [13.55,  55.0]   1.82x the highest independent value

Yc and S23 exceed EVERY independent tow value found, including the epoxy card
whose matrix is four times weaker than ours.  That is not proof they are
wrong -- a SiC matrix should give a stronger tow than an epoxy one -- but it
means they are the two the thesis has to defend, and Yt and S12 are not.

Note how Yc got there.  Yc/Yt is pinned to refs/[17] within 0.8 % (below), and
Yt sits at the very top of its own bracket.  A ratio that is corroborated,
applied to a level that is at its ceiling, lands Yc past the ceiling.  The two
observations are the same observation.

The physical reason it stays open, stated so the thesis can say it once:
transverse tow strength in C/SiC is controlled by the pyrocarbon interphase,
which is engineered WEAK so the composite can debond and stay tough.  So Yt,
Yc, S12, S23 are interface properties, not matrix properties.

CORRECTION (2026-08-05).  This paragraph originally continued "and no
interfacial normal or shear strength for our material exists anywhere in the
repository".  That was wrong.  refs/[15] Table 1 carries PyC interphase
properties -- Ei = 20.0 GPa, nu = 0.23, Xti = 140 MPa, Xci = 200 MPa -- and
that paper was already on the shelf; it is the one the thesis cites for the
XRD-measured TRS.  It had not been opened for this purpose.

What survives the correction is narrower and still true: what refs/[15] gives
is the interphase LAYER's own strength, not a fibre/matrix debond stress, so
it does not by itself fix Yt.  It does bound it, and our Yt = 80 MPa sits
below Xti = 140 MPa, which is at least consistent.  See
data/literature/pls_validation.py.

The one thing that IS corroborated
----------------------------------
The RATIO.  Our card has Yc/Yt = 350/80 = 4.375.  refs/[17] independently has
60.83/13.80 = 4.408, which is 0.8 % away.  The absolute level is unsupported;
the anisotropy of the transverse plane is supported.  That distinction is
worth stating because Yc/Yt is what drives the crack-band admissibility of
Gtc (g0 scales as Yc^2, so the ratio squared is the penalty).

An admissibility window nobody had written down
-----------------------------------------------
Hashin's transverse criterion, as coded in the UMAT, constrains S23 against Yt
and Yc whether or not anyone sourced them:

    tensile branch   FI^2 = ((s22+s33)/Yt)^2 + (s23^2 - s22*s33)/S23^2 + ...

    Under EQUIBIAXIAL transverse tension s22 = s33 = s the second term goes
    NEGATIVE.  The criterion stays meaningful only if the first term dominates:
        4/Yt^2 > 1/S23^2   ->   S23 > Yt/2.
    Below that bound equibiaxial transverse tension has unbounded strength.

    compressive branch  FI^2 = ((Yc/(2*S23))^2 - 1)*SUMT/Yc + ...

    The linear coefficient must not change sign, or transverse compression
    becomes stronger as it is loaded:
        S23 <= Yc/2.

So the admissible window is  Yt/2 < S23 <= Yc/2.  All three cards sit inside
it, ours with a wide margin (40 < 100 <= 175).

This was checked because S23 = 100 > Yt = 80 looks wrong at a glance and a
reviewer will say so.  It is not wrong: under pure transverse shear Hashin's
tensile branch reduces to FI = s23/S23 exactly, with no Yt term, and the
criterion is properly invariant in the 2-3 plane.  Recorded so the answer
exists before the question is asked.

Two filing defects found while doing this
-----------------------------------------
  * refs/[20] and refs/[21] were THE SAME PAPER -- Yang, Wang, Yang, Jiao,
    Int. J. Solids Struct. 300 (2024) 112927, doi:10.1016/j.ijsolstr.2024.112927.
    Identical extracted text (md5 match).  Reported here first; the full sweep
    in data/literature/refs_audit.py then found a SECOND pair ([32]=[39]) and
    both were consolidated -- [21] and [39] are retired.  Note the count given
    here originally ("46 distinct papers") was wrong for that reason.
  * refs/[25] is a carbon/EPOXY paper filed under a C-SiC name (above).

Run:  python3 data/properties/card_gap_triage.py --check
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GUIDE = os.path.join(ROOT, "verification", "CALIBRATION_GUIDE.md")
RANGES = os.path.join(ROOT, "verification", "check_card_ranges.py")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# The triage.  One row per slot that check_card_ranges.py grades GUESS.
#
#   card    which card the slot lives on
#   name    the slot
#   value   what the deck carries
#   verdict KNOB / DERIVED / GAP
#   why     the reason the verdict is what it is
# --------------------------------------------------------------------------
TRIAGE = [
    # ---- matrix card -----------------------------------------------------
    ("matrix", "SY0", 250.0, "KNOB",
     "SiC is brittle.  The plasticity exists to reproduce the paper's "
     "pseudo-ductility, so there is no measured yield point to find -- not "
     "for our material and not for any SiC."),
    ("matrix", "HISO", 100000.0, "KNOB",
     "linear isotropic hardening slope of that same fictitious plasticity"),
    ("matrix", "dmax_t", 0.90, "KNOB",
     "numerical cap that keeps the stiffness off the d = 1 singularity"),
    ("matrix", "eta", 0.05, "KNOB",
     "viscous regularisation; a solver parameter, not a material one"),

    # ---- yarn card, softening-law shape ----------------------------------
    ("yarn", "X_PO", 700.0, "KNOB",
     "auxiliary variable of Ge Eq.16-17.  The authors published the equation "
     "and not the constant, so there is nothing to source"),
    ("yarn", "rF", 3.0, "DERIVED",
     "NOT an independent input.  Ge refs/[24] Eq.(17), third line, fixes the "
     "transition point r^F_f,1t from X_PO and X_1t, so rF is computed from "
     "slots 36/38 rather than tuned.  Leaving it free lets slots 36/37/38 "
     "specify three mutually inconsistent transition points.  Regraded "
     "2026-08-11 from KNOB after reading the Ge original "
     "(refs/GE2018_EXTRACTION.md, sent to a1 as a2-0028)"),
    ("yarn", "K1", 8000.0, "KNOB",
     "linear softening slope of the same unpublished equation"),

    # ---- yarn card, derived ----------------------------------------------
    ("yarn", "Xc", 1956.0, "DERIVED",
     "rule of mixtures Vf*2470 from the fibre compressive strength in Zhang "
     "2022 Table 1, the same table Xt comes from.  Not independent, but the "
     "rule is stated and reproduces the card to 0.05 %"),

    # ---- yarn card, real gaps --------------------------------------------
    ("yarn", "Yt", 80.0, "GAP",
     "transverse tensile strength of the tow is a real measurable property.  "
     "Interface-controlled in C/SiC; two independent tow cards bracket it "
     "13.8-86 MPa and neither is our matrix"),
    ("yarn", "Yc", 350.0, "GAP",
     "independent tow cards give 60.83 (ceramic) and 249 (epoxy).  Ours is "
     "1.41x ABOVE both -- one of the two slots the thesis has to defend"),
    ("yarn", "S12", 120.0, "GAP",
     "independent tow cards give 16.96 (ceramic) and 186 (epoxy) -- an 11x "
     "spread, so this is the least constrained of the four, but ours is "
     "inside it"),
    ("yarn", "S23", 100.0, "GAP",
     "independent tow cards give 13.55 (ceramic) and 55 (epoxy).  Ours is "
     "1.82x ABOVE both, the largest unexplained excess of the four"),
    ("yarn", "Gtt", 0.0, "GAP",
     "a sourced value now EXISTS -- Shi refs/[31] 0.107 N/mm on 2D plain "
     "weave C/SiC -- and the card still carries 0, which switches the crack "
     "band off.  This is the one GAP that is closable today"),
    ("yarn", "Gtc", 0.0, "GAP",
     "transverse compressive fracture energy; nothing found, and the "
     "crack-band audit shows the mesh could not carry it even if it were "
     "found, because g0 scales as Yc^2"),
]

# --------------------------------------------------------------------------
# The two independent tow-level cards found in refs/.
# Values transcribed from the PDFs, with the material recorded so nobody
# re-uses them without seeing what matrix they came from.
# --------------------------------------------------------------------------
OURS = dict(
    key="OURS", what="this study, 2D plain-weave C/SiC yarn card",
    matrix="SiC (PIP), E = 350 GPa, Xt = 310 MPa",
    E1=254967.2, E2=44321.7, G12=26431.5, G23=15876.7,
    Yt=80.0, Yc=350.0, S12=120.0, S23=100.0)

R17 = dict(
    key="refs/[17]",
    what="P. Zhang et al., J. Mater. Res. Technol. 29 (2024) 2016-2034, "
         "Table 5 'RVE-F' (fibre tow model)",
    doi="10.1016/j.jmrt.2024.01.260",
    matrix="3D needled C/C-SiC -- ceramic, but carbon-rich inside the tow",
    provenance="COMPUTED (analytical + FEM), not measured",
    E1=119400.0, E2=19000.0, G12=7540.0, G23=7400.0,
    Yt=13.80, Yc=60.83, S12=16.96, S23=13.55)

R25 = dict(
    key="refs/[25]",
    what="C. Zhang, Curiel-Sosa, Bui, Compos. Struct. 201 (2018) 62-71, "
         "Table 1 (braiding yarn)",
    doi="10.1016/j.compstruct.2018.06.021",
    matrix="EPOXY -- companion matrix is E = 3.5 GPa, nu = 0.35, Xt = 80 MPa",
    provenance="card input of a fatigue model; material is NOT C/SiC",
    E1=138000.0, E2=10200.0, G12=5700.0, G23=3000.0,
    Yt=86.0, Yc=249.0, S12=186.0, S23=55.0)

CARDS = [OURS, R17, R25]


def hashin_window(card):
    """Admissible S23 for Hashin's transverse criterion as coded in the UMAT.
    Returns (lo, hi, ok) with lo exclusive and hi inclusive."""
    lo = card["Yt"] / 2.0
    hi = card["Yc"] / 2.0
    return lo, hi, (card["S23"] > lo and card["S23"] <= hi)


def report():
    print("=" * 74)
    print("card_gap_triage.py -- which of the 14 GUESS slots are real holes")
    print("=" * 74)

    print("\n 1. the triage")
    for tag in ("KNOB", "DERIVED", "GAP"):
        rows = [r for r in TRIAGE if r[3] == tag]
        print("\n   %s  (%d)" % (tag, len(rows)))
        for card, name, val, _, why in rows:
            print("     %-6s %-7s %-10s %s" % (card, name, ("%g" % val), why[:52]))

    print("\n 2. the two independent tow-level cards")
    for c in (R17, R25):
        print("\n   %s  %s" % (c["key"], c["what"]))
        print("     doi        %s" % c["doi"])
        print("     matrix     %s" % c["matrix"])
        print("     provenance %s" % c["provenance"])
        print("     Yt %7.2f   Yc %7.2f   S12 %7.2f   S23 %7.2f"
              % (c["Yt"], c["Yc"], c["S12"], c["S23"]))

    print("\n 3. our card against them")
    print("     %-6s %10s %10s %10s %10s %10s"
          % ("", "ours", "r17", "ours/r17", "r25", "ours/r25"))
    for k in ("Yt", "Yc", "S12", "S23"):
        print("     %-6s %10.2f %10.2f %10.2f %10.2f %10.2f"
              % (k, OURS[k], R17[k], OURS[k] / R17[k], R25[k],
                 OURS[k] / R25[k]))

    print("\n     stiffness, for scale -- their tow is genuinely softer, so a")
    print("     strength gap of ~6x is NOT explained by stiffness alone")
    for k in ("E1", "E2", "G12", "G23"):
        print("     %-6s %10.0f %10.0f %10.2f" % (k, OURS[k], R17[k],
                                                  OURS[k] / R17[k]))

    print("\n 4. the ratio Yc/Yt -- the one thing that IS corroborated")
    for c in CARDS:
        print("     %-10s Yc/Yt = %.3f" % (c["key"], c["Yc"] / c["Yt"]))
    print("     ours vs refs/[17]: %.2f %% apart"
          % (100.0 * abs(OURS["Yc"] / OURS["Yt"] - R17["Yc"] / R17["Yt"])
             / (R17["Yc"] / R17["Yt"])))

    print("\n 5. Hashin transverse admissibility,  Yt/2 < S23 <= Yc/2")
    for c in CARDS:
        lo, hi, ok = hashin_window(c)
        print("     %-10s %7.2f < %7.2f <= %7.2f   %s"
              % (c["key"], lo, c["S23"], hi, "OK" if ok else "VIOLATED"))
    print("     (S23 > Yt is NOT a violation: under pure transverse shear the")
    print("      tensile branch reduces to FI = s23/S23 with no Yt term.)")


def check():
    print("\n" + "=" * 74)
    print(" checks")
    print("=" * 74)

    # --- the triage itself is complete and matches check_card_ranges ------
    print("\n A. the triage covers exactly the GUESS set")
    t("triage has 14 rows", len(TRIAGE) == 14, "%d" % len(TRIAGE))
    n_knob = len([r for r in TRIAGE if r[3] == "KNOB"])
    n_der = len([r for r in TRIAGE if r[3] == "DERIVED"])
    n_gap = len([r for r in TRIAGE if r[3] == "GAP"])
    t("6 KNOB / 2 DERIVED / 6 GAP", (n_knob, n_der, n_gap) == (6, 2, 6),
      "%d / %d / %d" % (n_knob, n_der, n_gap))
    t("every row carries a written reason",
      all(len(r[4].strip()) > 20 for r in TRIAGE))
    t("no verdict outside {KNOB, DERIVED, GAP}",
      all(r[3] in ("KNOB", "DERIVED", "GAP") for r in TRIAGE))

    src = open(RANGES).read() if os.path.exists(RANGES) else ""
    t("check_card_ranges.py exists to compare against", bool(src))
    t("it still declares 13 GUESS", "EXPECTED_GUESS = 13" in src.replace(
        "EXPECTED_IN, EXPECTED_DEV, EXPECTED_GUESS, EXPECTED_DERIVED = "
        "7, 5, 13, 1", "EXPECTED_GUESS = 13"))
    for _, name, _, _, _ in TRIAGE:
        t("%s appears in the audit table" % name, name in src)

    # --- knobs must be declared where calibration can find them -----------
    print("\n B. every KNOB is declared in CALIBRATION_GUIDE.md")
    guide = open(GUIDE).read() if os.path.exists(GUIDE) else ""
    t("CALIBRATION_GUIDE.md exists", bool(guide))
    # the guide writes dmax without the mode suffix ("dmax1,dmaxt")
    NEEDLE = {"dmax_t": "dmax"}
    for _, name, _, verdict, _ in TRIAGE:
        if verdict == "KNOB":
            t("%s is in the guide" % name, NEEDLE.get(name, name) in guide)

    # The guide records a value as well as a name, and two of them are stale.
    # Reported, not asserted away -- the guide is a2's to correct, and a
    # passing assertion here would freeze the stale number in place.
    print("\n B2. CALIBRATION_GUIDE values vs what the deck now carries")
    STALE = [("dmax", "0.99", 0.90), ("eta", "0.02", 0.05)]
    drift = [(n, g, c) for n, g, c in STALE if g in guide]
    for n, g, c in drift:
        print("      DRIFT  %-6s guide says %s, deck carries %.2f  "
              "(retuned; guide not updated)" % (n, g, c))
    t("the guide's stale values are reported, not silently accepted",
      len(drift) == 2, "%d drifted: %s" % (len(drift),
                                           ", ".join(n for n, _, _ in drift)))

    # --- the DERIVED row must actually reproduce ---------------------------
    print("\n C. the DERIVED row reproduces from its stated rule")
    vf = 2835.0 / 3580.0
    t("Vf from Xt is the verified 0.79194", abs(vf - 0.79194) < 5e-5,
      "%.5f" % vf)
    t("Vf * 2470 reproduces Xc = 1956", abs(vf * 2470.0 - 1956.0) < 1.0,
      "%.1f" % (vf * 2470.0))
    t("the rule is within 0.05 % of the card",
      abs(vf * 2470.0 - 1956.0) / 1956.0 < 5e-4,
      "%.3f %%" % (100.0 * abs(vf * 2470.0 - 1956.0) / 1956.0))

    # --- the two independent cards -----------------------------------------
    print("\n D. the independent tow cards are recorded with their matrix")
    for c in (R17, R25):
        t("%s records its matrix" % c["key"], len(c["matrix"]) > 10)
        t("%s records its provenance" % c["key"], len(c["provenance"]) > 10)
        t("%s carries a DOI read off the PDF" % c["key"],
          c["doi"].startswith("10."), c["doi"])
    t("refs/[25] is flagged as the WRONG matrix", "EPOXY" in R25["matrix"])
    t("refs/[17] is flagged as computed, not measured",
      "COMPUTED" in R17["provenance"])
    t("neither is quietly treated as our material",
      "C/SiC" not in R25["matrix"] and "carbon-rich" in R17["matrix"])

    # --- the spread that keeps the four strengths open ---------------------
    print("\n E. the four tow strengths stay GAP because the spread is huge")
    # INSIDE = bracketed by the two independent cards.  ABOVE = past both.
    # This is the state as found; do not move it to make the run green.
    EXPECT = {"Yt": "INSIDE", "S12": "INSIDE", "Yc": "ABOVE", "S23": "ABOVE"}
    for k in ("Yt", "Yc", "S12", "S23"):
        spread = max(R17[k], R25[k]) / min(R17[k], R25[k])
        t("%s: the two sources disagree by %.1fx" % (k, spread), spread > 3.0)
        lo, hi = min(R17[k], R25[k]), max(R17[k], R25[k])
        where = ("INSIDE" if lo <= OURS[k] <= hi
                 else "ABOVE" if OURS[k] > hi else "BELOW")
        t("  our %s = %g is %s the bracket, as recorded"
          % (k, OURS[k], EXPECT[k]), where == EXPECT[k],
          "[%g, %g] -> %s" % (lo, hi, where))
    t("exactly two of the four exceed every independent value",
      len([k for k in EXPECT if EXPECT[k] == "ABOVE"]) == 2, "Yc, S23")
    t("Yc excess over the highest independent value is 1.41x",
      abs(OURS["Yc"] / max(R17["Yc"], R25["Yc"]) - 1.406) < 0.01,
      "%.2fx" % (OURS["Yc"] / max(R17["Yc"], R25["Yc"])))
    t("S23 excess over the highest independent value is 1.82x",
      abs(OURS["S23"] / max(R17["S23"], R25["S23"]) - 1.818) < 0.01,
      "%.2fx" % (OURS["S23"] / max(R17["S23"], R25["S23"])))
    t("S12 is the least constrained of the four",
      max(R17["S12"], R25["S12"]) / min(R17["S12"], R25["S12"]) ==
      max(max(R17[k], R25[k]) / min(R17[k], R25[k])
          for k in ("Yt", "Yc", "S12", "S23")),
      "%.1fx" % (R25["S12"] / R17["S12"]))

    # --- the ratio IS corroborated -----------------------------------------
    print("\n F. Yc/Yt is corroborated even though the level is not")
    r_ours = OURS["Yc"] / OURS["Yt"]
    r_17 = R17["Yc"] / R17["Yt"]
    t("our Yc/Yt = 4.375", abs(r_ours - 4.375) < 1e-6, "%.4f" % r_ours)
    t("refs/[17] Yc/Yt is within 1 % of ours",
      abs(r_ours - r_17) / r_17 < 0.01,
      "%.4f vs %.4f -> %.2f %%" % (r_ours, r_17,
                                   100.0 * abs(r_ours - r_17) / r_17))
    t("the epoxy card does NOT corroborate it (different failure physics)",
      abs(r_ours - R25["Yc"] / R25["Yt"]) / (R25["Yc"] / R25["Yt"]) > 0.3,
      "%.3f" % (R25["Yc"] / R25["Yt"]))

    # --- Hashin admissibility ---------------------------------------------
    print("\n G. Hashin transverse window  Yt/2 < S23 <= Yc/2")
    for c in CARDS:
        lo, hi, ok = hashin_window(c)
        t("%s is admissible" % c["key"], ok,
          "%.2f < %.2f <= %.2f" % (lo, c["S23"], hi))
    lo, hi, _ = hashin_window(OURS)
    t("our S23 has margin on both sides (>2x low, <0.6 high)",
      OURS["S23"] / lo > 2.0 and OURS["S23"] / hi < 0.6,
      "%.2fx above lo, %.2f of hi" % (OURS["S23"] / lo, OURS["S23"] / hi))
    t("S23 > Yt is not a violation of this criterion",
      OURS["S23"] > OURS["Yt"] and hashin_window(OURS)[2])

    # --- filing defects found on the way -----------------------------------
    print("\n H. filing defects found while reading refs/")
    refs = os.path.join(ROOT, "refs")
    have = os.path.isdir(refs)
    t("refs/ is present", have)
    if have:
        names = os.listdir(refs)
        t("refs/[21] is retired -- the duplicate was consolidated into [20]",
          any(n.startswith("[20]") for n in names) and
          not any(n.startswith("[21]") for n in names))
        t("refs/[25] exists and is the mis-filed epoxy paper",
          any(n.startswith("[25]") for n in names))
    t("the duplicate is named in this file so it is not re-cited twice",
      "112927" in __doc__ and "SAME PAPER" in __doc__)
    t("and the stale count in this file is corrected, not quietly dropped",
      "was wrong for that reason" in __doc__)
    t("the 'no interfacial strength exists' overclaim is retracted in place",
      "CORRECTION (2026-08-05)" in __doc__ and "That was wrong" in __doc__)
    t("  and what survives the retraction is stated, not just deleted",
      "What survives the correction is narrower" in __doc__)
    t("the mis-filing is named in this file",
      "carbon/EPOXY paper filed under a C-SiC name" in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 74)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 74)
            return 1
        print("ALL %d TRIAGE CLAIMS HOLD "
              "(6 KNOB / 2 DERIVED / 6 GAP)" % len(_OK))
        print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
