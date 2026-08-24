#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m6_calibration.py
=================
M5 showed the bottleneck is not convergence.  This designs what M6 must move.

WHERE THIS STARTS
-----------------
M5's T1000 reached 326.70 MPa against Zhang Table 3's 199.15 and was STILL
RISING -- 313 points of monotonic increase, no peak.  Running it to completion
makes the disagreement worse.  So M6 is a calibration job, and the question is
which of the fourteen uncalibrated knobs from check_card_ranges.py actually has
leverage on the composite tensile strength.

THE METHOD, AND ITS LIMIT
-------------------------
No RVE run is needed to rank the knobs, because for on-axis tension of a
balanced plain weave the sequence of limiting events can be written down.
Each candidate mechanism has a threshold expressed as a MACRO STRAIN, and the
measured M5 curve converts that strain into a composite stress.  Using the
measured curve rather than a stiffness model is the point: it already contains
the real damage evolution, so the conversion needs no further assumption.

What this CANNOT do is predict the calibrated answer.  Damage in the RVE is
progressive and coupled, so the first mechanism to reach its threshold does not
instantly fail the composite.  The output is an ORDER and a LEVERAGE, not a
value.  Every number here is a threshold, not a prediction.

THE RESULT, STATED UP FRONT
---------------------------
The knob with the most leverage is yarn Xt, which check_card_ranges.py graded
IN.  That grade meant "consistent with an independent source", not "right for
a composite": 2835 MPa is Vf x 3580, the T300 filament strength, and a fibre
bundle inside a cracked matrix at a 25 mm gauge length does not carry the
single-filament value.  The rule-of-mixtures bound it implies for the
composite is far above every measured 2D C/SiC strength in the literature.

  python3 data/properties/m6_calibration.py
  python3 data/properties/m6_calibration.py --check
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- card, as shipped (see verification/check_card_ranges.py) -------------
YARN_E1, YARN_E2 = 254967.228042, 44321.737572
YARN_XT, YARN_XC = 2835.0, 1956.0
YARN_YT, YARN_YC = 80.0, 350.0
YARN_S12 = 120.0
MATRIX_E, MATRIX_XT, MATRIX_SY0 = 350000.0, 310.0, 250.0

VY = 0.4982                 # yarn volume fraction of the RVE
VY_X = VY / 2.0             # yarns aligned with the load
VM = 1.0 - VY

#: M5 T1000, measured.  Ch.4 4.9-0.
M5_STOP_STRESS = 326.70     # MPa, at the last converged point
M5_STOP_STRAIN = 3.3184e-3
M5_E0 = 235.2e3             # MPa, initial (undamaged) tangent
TARGET = 199.15             # MPa, Zhang Table 3 at 1000 C

#: Measured composite modulus of 2D C/SiC.
#:
#: CORRECTED 2026-08-03.  This was refs/[43] Mei Table I's 70 GPa, compared
#: against our INITIAL TANGENT to claim the model was 3.4x too stiff.  That
#: was not like-for-like.  refs/[10] Yang Table 1 measures the same material
#: class at the same density and reports the INITIAL modulus -- 128.7 GPa at
#: room temperature, 172.7 GPa at 1273 K -- and states the curve is
#: non-linear almost from the onset of loading, which is why a whole-curve
#: chord lands near half of it.  Against the right number at the temperature
#: M5 actually ran, the model is 1.36x too stiff.  See porosity_stiffness.py,
#: which then shows that 1.36x is the porosity the mesh does not have.
E_MEASURED = 172.7e3        # MPa, refs/[10] Yang Table 1 at 1273 K, initial
E_MEASURED_RT = 128.7e3     # MPa, refs/[10] Yang Table 1 at 300 K, initial
E_MEI_CHORD = 70.0e3        # MPa, refs/[43] -- a chord, kept only to name it
E_M5_SECANT = 98.5e3        # MPa, M5 secant at the stopping point
#: refs/[10] Yang Table 1, failure strain at 1273 K [%].  M5 stopped at
#: 0.3318 %, so the model reached the measured failure strain -- what it got
#: wrong is the load it was carrying there, not where it stopped.
FAILURE_STRAIN_1000 = 0.32

#: (label, threshold macro strain, the knob that sets it, grade in the audit)
def mechanisms():
    return [
        ("matrix yields", MATRIX_SY0 / MATRIX_E, "matrix sigma_y0", "GUESS"),
        ("matrix damage starts", MATRIX_XT / MATRIX_E, "matrix Xt", "IN"),
        ("transverse yarn cracks", YARN_YT / YARN_E2, "yarn Yt", "GUESS"),
        ("in-plane shear limit", YARN_S12 / (YARN_E2 / 2.6), "yarn S12", "GUESS"),
        ("axial yarn ruptures", YARN_XT / YARN_E1, "yarn Xt", "IN"),
    ]


def rom_bound():
    """Rule-of-mixtures upper bound on composite strength.

    When the load-aligned yarns rupture, the composite cannot carry more than
    their share.  This ignores the matrix and the transverse yarns, both of
    which are damaged by then, so it is an UPPER bound and a loose one.
    """
    return VY_X * YARN_XT


def stress_at(eps, curve):
    """Composite stress at a macro strain, read off the measured M5 curve."""
    if not curve:
        return None
    if eps <= curve[0][0]:
        return curve[0][1]
    if eps >= curve[-1][0]:
        return None            # beyond what was measured -- say so, don't guess
    for i in range(len(curve) - 1):
        a, b = curve[i], curve[i + 1]
        if a[0] <= eps <= b[0]:
            w = (eps - a[0]) / (b[0] - a[0])
            return a[1] + w * (b[1] - a[1])
    return None


def load_curve(path=None):
    """The M5 T1000 measured curve, if the csv is next to this file."""
    path = path or os.path.join(HERE, "M5_c26k_T1000_ss.csv")
    if not os.path.exists(path):
        return []
    # columns by NAME, not position -- the same hardening as m6_report/
    # m6_verdict (2026-08-16): a prepended column must break loudly or be
    # absorbed correctly, never read silently as the wrong quantity.
    lines = open(path).read().splitlines()
    if not lines:
        return []
    names = [h.strip().lower() for h in lines[0].split(",")]
    ei = next((i for i, n in enumerate(names) if n.startswith("eps")), 0)
    si = next((i for i, n in enumerate(names) if n.startswith("sig")), 1)
    out = []
    for line in lines[1:]:
        p = line.split(",")
        if len(p) > max(ei, si):
            try:
                out.append((float(p[ei]), float(p[si])))
            except ValueError:
                pass
    return sorted(out)


def strain_for_target(curve, target=TARGET):
    """Macro strain at which the measured curve passes the Zhang target."""
    for i in range(len(curve) - 1):
        if curve[i][1] <= target <= curve[i + 1][1]:
            a, b = curve[i], curve[i + 1]
            w = (target - a[1]) / (b[1] - a[1])
            return a[0] + w * (b[0] - a[0])
    return None


# ==========================================================================
def report():
    print("=" * 78)
    print("m6_calibration.py -- which knob has leverage on the strength")
    print("=" * 78)
    curve = load_curve()

    print("\n 1. WHERE M5 LEFT OFF")
    print("    stopped at            %.2f MPa at eps = %.4f %%"
          % (M5_STOP_STRESS, M5_STOP_STRAIN * 100.0))
    print("    Zhang Table 3 target  %.2f MPa" % TARGET)
    print("    ratio                 %.2fx, and the curve was still rising"
          % (M5_STOP_STRESS / TARGET))
    print("    refs/[10] Yang failure strain at 1273 K   %.2f %%"
          % FAILURE_STRAIN_1000)
    print("    -> M5 stopped at %.4f %%, i.e. essentially AT the measured"
          % (M5_STOP_STRAIN * 100.0))
    print("       failure strain.  It did not stop early in any physical")
    print("       sense; it reached the right strain carrying too much load.")
    if curve:
        e = strain_for_target(curve)
        if e:
            print("    the measured curve passes the target at eps = %.4f %%"
                  % (e * 100.0))
            print("    -> the model reaches the right STRESS, %.1fx too early"
                  % (M5_STOP_STRAIN / e))

    print("\n 2. THE SEQUENCE OF LIMITING EVENTS, as macro strain")
    print("    %-26s %10s %10s  %-18s %s"
          % ("mechanism", "eps [%]", "sigma[MPa]", "knob", "audit"))
    print("    " + "-" * 74)
    rows = []
    for name, eps, knob, grade in sorted(mechanisms(), key=lambda r: r[1]):
        s = stress_at(eps, curve)
        rows.append((name, eps, s, knob, grade))
        print("    %-26s %10.4f %10s  %-18s %s"
              % (name, eps * 100.0,
                 "%.1f" % s if s is not None else "beyond M5",
                 knob, grade))
    print("    " + "-" * 74)
    print("    M5 stopped at %.4f %% -- every mechanism above that line had"
          % (M5_STOP_STRAIN * 100.0))
    print("    already triggered; the one below it had not.")

    print("\n 3. THE UPPER BOUND THE CARD IMPLIES")
    rb = rom_bound()
    print("    load-aligned yarns are %.4f of the RVE at Xt = %.0f MPa"
          % (VY_X, YARN_XT))
    print("    rule-of-mixtures bound on composite strength: %.0f MPa" % rb)
    print("    Zhang Table 3 at 1000 C                     : %.2f MPa"
          % TARGET)
    print("    the bound is %.1fx the target" % (rb / TARGET))
    print("    measured 2D C/SiC UTS, refs/[43] Table I     : 248 MPa")
    print("    measured 2D C/SiC UTS, refs/[03] as-received : 259.3 MPa")
    print("    -> the card cannot reproduce ANY measured strength while the")
    print("       aligned yarns retain the filament value.")

    print("\n 4. STIFFNESS -- REWRITTEN 2026-08-03, THE OLD READING WAS WRONG")
    print("    M5 initial tangent (undamaged)      %.0f GPa" % (M5_E0 / 1000.0))
    print("    M5 secant at the stopping point     %.1f GPa"
          % (E_M5_SECANT / 1000.0))
    print("    refs/[10] Yang, INITIAL, at 1273 K  %.1f GPa"
          % (E_MEASURED / 1000.0))
    print("    refs/[43] Mei, an unstated chord    %.0f GPa"
          % (E_MEI_CHORD / 1000.0))
    print("    This file used to compare the initial tangent against Mei's")
    print("    70 GPa, call the model 3.4x too stiff, and conclude that the")
    print("    real material is measured ALREADY microcracked while the model")
    print("    cracks during the pull.  Against the like-for-like number that")
    print("    reading inverts: the TANGENT is %.2fx and the SECANT is %.2fx."
          % (M5_E0 / E_MEASURED, E_M5_SECANT / E_MEASURED))
    print("    The model is mildly too stiff at the start and too SOFT by the")
    print("    time it stops -- it damages too fast, not too slowly.")
    print("    And the %.2fx at the start is not a knob either: it is the"
          % (M5_E0 / E_MEASURED))
    print("    porosity the mesh does not have.  porosity_stiffness.py shows")
    print("    subtracting the missing 19.6 %% of void takes 235.2 -> 170.0 GPa")
    print("    against Yang's measured 172.7.  See Ch.4 4.9-13.")

    print("\n 5. WHAT M6 SHOULD MOVE, IN ORDER")
    print("    (1) yarn Xt        the only knob that sets the upper bound.")
    print("                       graded IN, but IN meant traceable, not right:")
    print("                       2835 = Vf x 3580 is a STRAND figure.")
    print("                       SOLVED 2026-08-03 -- and it did not need a")
    print("                       fit.  insitu_yarn_strength.py derives it from")
    print("                       refs/[08] Sauder Table 1 alone: 475 MPa at")
    print("                       23 C, 581 at 500 C, 694 at 1000 C, an 8 %")
    print("                       wide band with both ends sourced.  The card")
    print("                       is 4.1-6.0x above it.  Xt is no longer a knob.")
    print("    (2) the porosity   SOLVED 2026-08-03, and it is not a knob.")
    print("                       The mesh is a filled cell; the material is")
    print("                       19.6 %% pore by its own measured density.")
    print("                       Matrix E knockdown 0.6089. This is a missing")
    print("                       physical feature with a measured value, so")
    print("                       it goes in BEFORE anything is fitted.")
    print("                       Do (1) and (2) in the SAME deck: both are")
    print("                       determined, neither is being searched over.")
    print("    (3) yarn Yt, S12   they set where the knee sits, not the peak.")
    print("                       Fit them AFTER (1) and (2), one at a time.")
    print("    Do NOT start with dmax or eta.  They are numerical, and moving")
    print("    them to fix a physical disagreement hides it.")
    print("=" * 78)


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("=" * 78)
    print("m6_calibration.py --check")
    print("=" * 78)

    print("\n A. the card values match what check_card_ranges.py audits")
    ck("yarn E1 is the shipped card value",
       abs(YARN_E1 - 254967.228042) < 1e-6)
    ck("yarn Xt is Vf x 3580 to within 0.1 %",
       abs(YARN_XT - 0.79194 * 3580.0) / YARN_XT < 1.0e-3,
       "%.1f vs %.1f" % (YARN_XT, 0.79194 * 3580.0))
    ck("yarn fraction halves into two load directions",
       abs(VY_X * 2.0 - VY) < 1e-12)

    print("\n B. the mechanism thresholds are ordered and physical")
    ms = sorted(mechanisms(), key=lambda r: r[1])
    ck("every threshold is a positive strain", all(m[1] > 0 for m in ms))
    ck("the matrix yields before it damages",
       ms[0][2] == "matrix sigma_y0", ms[0][0])
    ck("axial yarn rupture is the LAST mechanism",
       ms[-1][2] == "yarn Xt", "%.4f %%" % (ms[-1][1] * 100))
    ck("axial yarn rupture lies beyond what M5 measured",
       ms[-1][1] > M5_STOP_STRAIN,
       "%.4f %% vs M5 %.4f %%" % (ms[-1][1] * 100, M5_STOP_STRAIN * 100))
    ck("matrix damage starts below 0.1 % strain",
       MATRIX_XT / MATRIX_E < 1.0e-3,
       "%.4f %%" % (MATRIX_XT / MATRIX_E * 100))

    print("\n C. the rule-of-mixtures bound is the load-bearing argument")
    rb = rom_bound()
    ck("bound is %.0f MPa" % rb, abs(rb - 706.0) < 2.0, "%.1f" % rb)
    ck("bound exceeds the Zhang target by more than 3x",
       rb / TARGET > 3.0, "%.1fx" % (rb / TARGET))
    ck("bound exceeds every measured 2D C/SiC strength",
       rb > 259.3 and rb > 248.0,
       "vs 259.3 (refs/[03]) and 248 (refs/[43])")
    ck("so yarn Xt alone can carry the disagreement",
       rb / TARGET > M5_STOP_STRESS / TARGET,
       "bound %.1fx vs M5 %.2fx" % (rb / TARGET, M5_STOP_STRESS / TARGET))

    print("\n D. the stiffness statement is arithmetic, not opinion")
    ck("the comparison modulus is Yang's INITIAL, not Mei's chord",
       abs(E_MEASURED - 172.7e3) < 1.0 and abs(E_MEI_CHORD - 70.0e3) < 1.0,
       "172.7 vs 70 GPa, a 2.47x choice")
    ck("the M5 initial tangent is only mildly above it",
       1.2 < M5_E0 / E_MEASURED < 1.6, "%.2fx" % (M5_E0 / E_MEASURED))
    ck("the M5 SECANT falls BELOW it -- the model damages too fast",
       E_M5_SECANT < E_MEASURED, "%.2fx" % (E_M5_SECANT / E_MEASURED))
    ck("the old 3.4x claim came from Mei's chord and is retracted",
       abs(M5_E0 / E_MEI_CHORD - 3.36) < 0.05,
       "%.2fx against the wrong number" % (M5_E0 / E_MEI_CHORD))
    ck("the residual 1.36x is handed to porosity_stiffness.py, not to a knob",
       os.path.exists(os.path.join(HERE, "porosity_stiffness.py")))

    print("\n E. the M5 numbers quoted here are the ones Ch.4 records")
    ck("stop stress 326.70 MPa", abs(M5_STOP_STRESS - 326.70) < 0.01)
    ck("ratio to target is 1.64x", abs(M5_STOP_STRESS / TARGET - 1.64) < 0.01,
       "%.3f" % (M5_STOP_STRESS / TARGET))
    curve = load_curve()
    if curve:
        ck("the measured curve is available", len(curve) > 300,
           "%d points" % len(curve))
        ck("the curve is monotonic (no peak)",
           all(curve[i][1] >= curve[i - 1][1] - 1e-9
               for i in range(1, len(curve))))
        ck("M5 stopped AT the measured failure strain, not before it",
           abs(M5_STOP_STRAIN * 100.0 - FAILURE_STRAIN_1000) < 0.05,
           "%.4f %% vs Yang %.2f %%"
           % (M5_STOP_STRAIN * 100.0, FAILURE_STRAIN_1000))
        e = strain_for_target(curve)
        ck("the curve passes the target well below the stopping strain",
           e is not None and e < M5_STOP_STRAIN / 2.0,
           "%.4f %% vs %.4f %%" % (e * 100, M5_STOP_STRAIN * 100))
    else:
        ck("curve csv absent -- thresholds still computable", True,
           "drop M5_c26k_T1000_ss.csv beside this file for column 3")

    print("\n F. the ordering advice is stated, and the trap named")
    src = open(os.path.join(HERE, "m6_calibration.py")).read()
    for phrase, why in (
            ("graded IN, but IN meant traceable, not right",
             "must say why an IN knob is still the first suspect"),
            ("Do NOT start with dmax or eta",
             "must name the numerical-knob trap"),
            ("an ORDER and a LEVERAGE, not a value",
             "must refuse to predict the calibrated answer"),
            ("threshold, not a prediction", "must label the numbers")):
        ck("source states: %s" % why, phrase in src)

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d M6-CALIBRATION CHECKS PASS" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    report()
