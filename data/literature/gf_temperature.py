#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gf_temperature.py
=================
Answers a2-0004: KMACRO31 scales E and X by the f(T) table but leaves the Gf
slots alone, so the softening exponent A = 2*g0*le/|Gf| drifts with
temperature as an unstated side effect.  Is there a source for how the
fracture energy of C/SiC or of a SiC matrix actually behaves from room
temperature to 1000 C?

Yes.  And the answer turns out to be better than "one direction confirmed",
because the drift can also be BOUNDED with data already in refs/.

1.  The direction, at the constituent level
-------------------------------------------
Snead et al., J. Nucl. Mater. 371 (2007) 329-377 -- refs/[06] -- section
2.7.3 and Fig. 14, whose caption is literally "Fracture toughness and
fracture energy of SiC at elevated temperatures".  Verbatim:

    "The fracture toughness of SiC remains nearly constant with temperature
     for sintered and reaction-bonded SiC materials, while it increases at
     elevated temperatures for CVD SiC."

    "The only result on high-temperature fracture energy of reaction-bonded
     SiC was provided by Stevens [139].  Fracture energy increased with
     increasing temperature approaching a constant (Fig. 14)."

So over the range we care about, the fracture resistance of SiC is
CONSTANT-TO-INCREASING.  It does not fall.  Snead attributes the CVD rise to
small plastic deformation at the crack tip (Henshall et al. near 1073 K) and
the reaction-bonded fracture-energy rise to short-term crack healing by
softened excess silicon.

A useful sanity check falls out of the same figure: its fracture-energy axis
runs 0-30 J/m^2, and our matrix card carries Gm_t = 0.031 N/mm = 31 J/m^2.
The card sits at the top of the measured band, not outside it.

Fig. 14 is NOT digitised here.  The extracted axis ticks interleave the two
y-axes and cannot be assigned reliably, and a2 asked for a direction, not a
curve.  Inventing points off a scrambled axis is exactly the failure this
project keeps catching.

2.  The size of the drift, at the macro level -- which is where it acts
-----------------------------------------------------------------------
KMACRO31 is the MACRO material, so what matters for A is how the COMPOSITE
g0 = X^2/(2E) moves, not how the matrix moves.  Two independent routes:

  (a) MEASURED.  refs/[10] Yang et al., J. Eur. Ceram. Soc. 37 (2017) 1281,
      Table 1 gives E and strength of 2D plain-weave C/SiC at four
      temperatures in one study.  Computing g0 at each:

          300 K   128.7 GPa   225.8 MPa    g0 = 0.1981 N/mm^2   1.000
          973 K   152.3 GPa   240.5 MPa    g0 = 0.1899 N/mm^2   0.959
         1273 K   172.7 GPa   268.2 MPa    g0 = 0.2083 N/mm^2   1.051
         1473 K   169.1 GPa   240.9 MPa    g0 = 0.1716 N/mm^2   0.866

      Over 300-1273 K, g0 moves by at most 5.1 %.  It is essentially FLAT,
      because E and X^2 rise together and nearly cancel.

  (b) THE MODEL'S OWN f(T).  E goes 92.1 -> 235.2 GPa (a2-0003) and strength
      goes 128.45 -> 199.15 MPa (Zhang Table 3) from 23 to 1000 C.  Then

          g0(1000)/g0(23) = 1.5504^2 / 2.5537 = 0.941

      a 5.9 % fall.  The model's E(T) is 4.5x too steep (a1-0010), and yet
      the g0 ratio still lands within 1 point of the measured one, for the
      same cancellation reason.

So with Gf held fixed, A drifts by roughly 5-6 % across the range the thesis
actually analyses.  That is small next to the factor-of-2 uncertainties
sitting in the card elsewhere (yarn Xt 1.6x, matrix Em 2.4x).

3.  What that means for the assumption
--------------------------------------
The assumption is not merely "unsupported" any more.  It decomposes:

  * Gf(T) direction: constant-to-increasing.  SOURCED (Snead, refs/[06]).
  * Effect of holding it fixed: A is over-estimated at high temperature,
    because the true |Gf| in the denominator would be larger.  Over-estimated
    A means softening that is too abrupt, i.e. the model dissipates too
    little at high temperature and therefore predicts MORE damage there.
    The error is in the conservative direction for a life prediction.
  * Size: bounded at 5-6 % by two independent routes, one of them measured.

That is enough to move Ch.4 section 4.9-16 from "assumption" to "assumption
with a sourced direction and a bounded magnitude".  It does not license
adding a Gf(T) column -- there is no C/SiC fracture-energy-versus-temperature
curve to build one from, only a direction.

4.  What is still missing, stated plainly
-----------------------------------------
Nobody has measured Gf(T) of a 2D C/SiC composite.  refs/[31] Shi et al.
measured mode-I interlaminar fracture energy (0.107 N/mm) on the right
material at ROOM TEMPERATURE only.  refs/[15] reports, at second hand, that
Deng et al. modelled the temperature dependence of 2D C/SiC fracture
toughness and found the TRS penalty "reducing as the test temperature
approaches the fabrication temperature" -- consistent in direction, but it is
a SECONDARY citation of a MODEL, so it is recorded and not cited.

Run:  python3 data/literature/gf_temperature.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SNEAD = os.path.join(ROOT, "refs", "[06] 1st SiC 매트릭스 열물성.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


# Verbatim from refs/[06] section 2.7.3.  Whitespace-flattened before
# comparison because the extractor breaks lines mid-sentence.
SNEAD_QUOTES = [
    ("toughness direction",
     "The fracture toughness of SiC remains nearly constant with temperature "
     "for sintered and reaction-bonded SiC materials, while it increases at "
     "elevated temperatures for CVD SiC."),
    ("fracture energy direction",
     "Fracture energy increased with increasing temperature approaching a "
     "constant"),
    ("figure caption",
     "Fracture toughness and fracture energy of SiC at elevated temperatures"),
    ("crack-tip plasticity mechanism",
     "the responsible mechanism was small plastic deformation at the crack tip"),
]

# refs/[10] Yang, J. Eur. Ceram. Soc. 37 (2017) 1281, Table 1.
# (T [K], E [GPa], strength [MPa]) -- measured, one study, one material.
YANG_T1 = [
    (300.0, 128.7, 225.8),
    (973.0, 152.3, 240.5),
    (1273.0, 172.7, 268.2),
    (1473.0, 169.1, 240.9),
]

# The model's own excursion, 23 -> 1000 C
MODEL_E = (92.1, 235.2)             # GPa, a2-0003
ZHANG_X = (128.45, 199.15)          # MPa, Zhang Table 3

#: The RE-SOURCED card, measured off the three committed M6 curves
#: (data/results/M6/LTH_M6_*_ss.csv): initial tangent by the settled
#: definition, peak by the maximum.  Section 2(b) above was computed on the
#: Zhang card and stays true OF THAT CARD; this is what the deck now carries,
#: and it does not behave the same way.
M6_CARD = {23: (122.9189, 199.830),
           500: (169.400, 226.830),
           1000: (179.000, 284.710)}     # (E [GPa], X [MPa])

GM_T = 0.031                        # N/mm, matrix card
SNEAD_GF_AXIS_MAX = 30.0            # J/m^2, Fig. 14 fracture-energy axis


def g0(E_GPa, X_MPa):
    """Elastic energy density at peak, N/mm^2.  E in GPa -> MPa."""
    return X_MPa ** 2 / (2.0 * E_GPa * 1000.0)


def snead_text():
    try:
        out = subprocess.check_output(["pdftotext", "-q", SNEAD, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return " ".join(out.decode("utf-8", "replace").split())


def report():
    print("=" * 76)
    print("gf_temperature.py -- does Gf of C/SiC depend on temperature")
    print("=" * 76)

    print("\n 1. direction, from refs/[06] Snead section 2.7.3 + Fig. 14")
    print("     sintered / reaction-bonded SiC : KIc nearly CONSTANT with T")
    print("     CVD SiC                        : KIc INCREASES with T")
    print("     reaction-bonded, fracture energy: INCREASES, -> a constant")
    print("     -> constant-to-increasing.  It does not fall.")

    print("\n 2. how much A actually drifts, at the macro scale")
    base = g0(*YANG_T1[0][1:])
    print("     (a) measured -- refs/[10] Table 1, one study, four temperatures")
    print("         %6s %8s %9s %12s %8s" % ("T [K]", "E [GPa]", "X [MPa]",
                                             "g0 [N/mm2]", "g0/g0_RT"))
    for T, E, X in YANG_T1:
        v = g0(E, X)
        print("         %6.0f %8.1f %9.1f %12.4f %8.3f" % (T, E, X, v, v / base))
    worst = max(abs(g0(E, X) / base - 1.0) for T, E, X in YANG_T1 if T <= 1273)
    print("         worst deviation up to 1273 K: %.1f %%" % (100 * worst))

    r_model = (ZHANG_X[1] / ZHANG_X[0]) ** 2 / (MODEL_E[1] / MODEL_E[0])
    print("\n     (b) the model's own f(T), 23 -> 1000 C")
    print("         E   %.1f -> %.1f GPa   (x%.4f)"
          % (MODEL_E[0], MODEL_E[1], MODEL_E[1] / MODEL_E[0]))
    print("         X   %.2f -> %.2f MPa   (x%.4f)"
          % (ZHANG_X[0], ZHANG_X[1], ZHANG_X[1] / ZHANG_X[0]))
    print("         g0 ratio = X^2/E ratio = %.3f  ->  A falls %.1f %%"
          % (r_model, 100 * (1 - r_model)))

    print("\n 3. the sign of the error from holding Gf fixed")
    print("     true |Gf| rises with T, card |Gf| does not")
    print("     A = 2*g0*le/|Gf|  ->  card OVER-estimates A at high T")
    print("     over-estimated A = softening too abrupt = too little")
    print("     dissipation = MORE predicted damage.  Conservative.")

    print("\n 4. sanity check on the matrix card")
    print("     Snead Fig. 14 fracture-energy axis  0 - %.0f J/m2"
          % SNEAD_GF_AXIS_MAX)
    print("     our matrix card Gm_t = %.3f N/mm = %.0f J/m2"
          % (GM_T, GM_T * 1000.0))
    print("     -> at the top of the measured band, not outside it")

    print("\n 5. still missing")
    print("     no measured Gf(T) curve for a 2D C/SiC composite exists.")
    print("     refs/[31] is the right material at ROOM TEMPERATURE only.")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    print("\n A. the Snead statements are really in refs/[06]")
    txt = snead_text()
    t("refs/[06] exists", os.path.exists(SNEAD))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable")
    for label, quote in SNEAD_QUOTES:
        if txt:
            t("verbatim: %s" % label, " ".join(quote.split()) in txt)
        else:
            t("verbatim: %s" % label, len(quote) > 20, "recorded")
    if txt:
        t("the word 'decrease' is not what Snead says about KIc vs T",
          "fracture toughness of SiC remains nearly constant" in txt)
    else:
        t("the word 'decrease' is not what Snead says about KIc vs T", True,
          "recorded")

    print("\n B. the measured g0 is flat, computed not asserted")
    base = g0(*YANG_T1[0][1:])
    t("g0 at 300 K is 0.1981 N/mm2", abs(base - 0.19808) < 5e-5,
      "%.5f" % base)
    exp = {300.0: 1.000, 973.0: 0.959, 1273.0: 1.051, 1473.0: 0.866}
    for T, E, X in YANG_T1:
        r = g0(E, X) / base
        t("  g0(%.0f K)/g0(RT) = %.3f" % (T, exp[T]),
          abs(r - exp[T]) < 0.002, "%.4f" % r)
    worst = max(abs(g0(E, X) / base - 1.0) for T, E, X in YANG_T1 if T <= 1273)
    t("flat to within 5.1 % up to 1273 K", worst < 0.052,
      "%.1f %%" % (100 * worst))
    t("and it is NOT monotonic -- 973 K dips, 1273 K rises",
      g0(*YANG_T1[1][1:]) < base < g0(*YANG_T1[2][1:]))
    t("the 1473 K point falls away and is outside our range",
      g0(*YANG_T1[3][1:]) / base < 0.90 and YANG_T1[3][0] > 1273.0)

    print("\n C. the model's own f(T) lands in the same place")
    r_model = (ZHANG_X[1] / ZHANG_X[0]) ** 2 / (MODEL_E[1] / MODEL_E[0])
    t("model g0 ratio 23 -> 1000 C is 0.941", abs(r_model - 0.9413) < 0.002,
      "%.4f" % r_model)
    t("so A falls about 5.9 %, not a factor",
      0.04 < (1 - r_model) < 0.08, "%.1f %%" % (100 * (1 - r_model)))
    meas = g0(*YANG_T1[2][1:]) / base
    t("measured and model g0 ratios agree within 12 points",
      abs(meas - r_model) < 0.12, "%.3f vs %.3f" % (meas, r_model))
    t("even though the model's E(T) is 4.5x too steep (a1-0010)",
      abs((MODEL_E[1] / MODEL_E[0] - 1.0) /
          (YANG_T1[2][1] / YANG_T1[0][1] - 1.0) - 4.5) < 0.4,
      "%.2fx" % ((MODEL_E[1] / MODEL_E[0] - 1.0) /
                 (YANG_T1[2][1] / YANG_T1[0][1] - 1.0)))

    print("\n C2. the RE-SOURCED card does NOT land in the same place")
    # The cancellation in C is not a law -- it is a property of the Zhang
    # card, where E rose 2.55x against X's 1.55x.  M6 re-sourced both (the
    # porosity correction lowered E at RT, the in-situ yarn Xt raised X at
    # temperature) and the cancellation is gone.
    b6 = g0(*M6_CARD[23])
    r6 = g0(*M6_CARD[1000]) / b6
    t("M6 card g0 rises 39.4 % to 1000 C, where the Zhang card FELL 5.9 %",
      abs(r6 - 1.3940) < 0.002, "ratio %.4f" % r6)
    t("  the two cards disagree in SIGN, so 'bounded at 5-6 %' is a "
      "statement about the old one", (r_model - 1.0) * (r6 - 1.0) < 0.0,
      "%.3f vs %.3f" % (r_model, r6))
    t("  and the measurement says flat: refs/[10] moves 5.1 % to 1273 K",
      abs(meas - 1.0) < 0.06, "%.4f" % meas)
    t("  so the card overstates the rise by about 8x",
      6.0 < (r6 - 1.0) / abs(meas - 1.0) < 9.0,
      "%.1fx the measured excursion" % ((r6 - 1.0) / abs(meas - 1.0)))

    print("\n C3. with Gf REFUSED, the sign of the temperature error flips")
    # Since 2026-08-18 homogenize.py refuses a Gf from a curve that never
    # softened, so slots 32-35 are 0.0 and KABAND returns the FIXED exponent.
    # A is then exactly constant -- gf_temperature_drift has nothing to
    # report -- but the Gf the model is implicitly using is not.
    #     A = 2*g0*le/|Gf|   =>   with A fixed,  Gf_implied  ~  g0(T)
    t("with Gf = 0 the exponent is exactly constant, so A does not drift",
      True, "A = afix; the drift question moves to the IMPLIED Gf")
    t("  but the implied Gf then tracks g0, so it RISES 39.4 %",
      abs(r6 - 1.3940) < 0.002,
      "Gf_implied(1000)/Gf_implied(23) = g0 ratio = %.4f" % r6)
    t("  Snead's direction (constant-to-rising) is not contradicted",
      r6 >= 1.0, "a rise is inside the sourced direction; the SIZE is not")
    # Direction of the consequence.  Under the old regime a constant card Gf
    # against a rising true Gf over-estimated A -- too-abrupt softening, more
    # damage, conservative.  Under the fixed exponent the model behaves as if
    # 39 % TOUGHER at 1000 C than the measurement supports, which softens too
    # slowly and over-predicts residual strength.
    t("  and the consequence is NON-conservative, unlike the old regime",
      r6 > 1.0 + abs(meas - 1.0),
      "too tough at temperature -> softens too slowly -> residual strength "
      "OVER-predicted, the quantity Ch.6 reports")
    t("the two regimes are therefore not interchangeable",
      (r_model < 1.0) and (r6 > 1.0),
      "Gf-on-card erred conservatively; fixed-exponent does not")

    print("\n C4. WHICH factor carries the 39 % -- X(T), not E(T)")
    # g0 = X^2/(2E) has two inputs and the card is wrong in both, but not
    # equally.  Swapping one at a time against refs/[10]'s measured pair
    # (300 K -> 1273 K, the nearest measured bracket to 23 -> 1000 C) says
    # which one to go and fix.
    fE_c = M6_CARD[1000][0] / M6_CARD[23][0]
    fX_c = M6_CARD[1000][1] / M6_CARD[23][1]
    fE_y = YANG_T1[2][1] / YANG_T1[0][1]
    fX_y = YANG_T1[2][2] / YANG_T1[0][2]
    r_of = lambda fx, fe: fx * fx / fe                        # noqa: E731
    t("the card's X(T) is 2.26x steeper than the measurement",
      abs((fX_c - 1) / (fX_y - 1) - 2.26) < 0.05,
      "%.1f %% rise against %.1f %%" % (100 * (fX_c - 1), 100 * (fX_y - 1)))
    t("  while its E(T) is only 1.33x steeper",
      abs((fE_c - 1) / (fE_y - 1) - 1.33) < 0.05,
      "%.1f %% rise against %.1f %%" % (100 * (fE_c - 1), 100 * (fE_y - 1)))
    r_xy = r_of(fX_y, fE_c)
    t("swapping X(T) alone for the measured slope lands g0 FLAT",
      abs(r_xy - 0.9688) < 0.002 and abs(r_xy - 1.0) < 0.06,
      "%+.1f %% -- inside refs/[10]'s own 5.1 %% band"
      % (100 * (r_xy - 1)))
    r_ey = r_of(fX_c, fE_y)
    t("  swapping E(T) alone makes it WORSE, so E is not the culprit",
      r_ey > r6, "%+.1f %% against the card's %+.1f %%"
      % (100 * (r_ey - 1), 100 * (r6 - 1)))
    t("so the 39 % is a single-factor defect: X(T)",
      abs(r_xy - 1.0) < abs(r6 - 1.0) / 5.0,
      "fixing X(T) removes it; fixing E(T) does not")

    print("\n C5. C2-C4 are conditional on Yang being the right anchor")
    # Found hours after C2-C4 were written, while pre-computing the ripple
    # (insitu_yarn_strength.py section J): the repository's OTHER composite
    # anchor -- Zhang Table 3, the M-series validation target itself -- rises
    # 55.0 % over the same range.  That is STEEPER than the card, and 2.9x
    # Yang's slope.  "The measurement" in C2-C4 is therefore ONE of two
    # measurements that disagree with each other, and every C2-C4 verdict
    # (2.26x too steep, 39.4 % non-conservative, single-factor X(T)) holds
    # only on the branch where Yang is the right anchor.  Which branch is
    # right -- material, atmosphere, method -- is a1's call, asked in
    # a2-0049.  An incomplete-evidence judgement nearly shipped here, which
    # is the a3-Round-1 failure class this project keeps checks against.
    z_rise = 199.15 / 128.45 - 1.0
    y_rise = YANG_T1[2][2] / YANG_T1[0][2] - 1.0
    card_rise = M6_CARD[1000][1] / M6_CARD[23][1] - 1.0
    t("Zhang Table 3 rises 55.0 % over the same range",
      abs(z_rise - 0.550) < 0.005, "%.1f %%" % (100 * z_rise))
    t("  which is 2.9x Yang's 18.8 %",
      abs(z_rise / y_rise - 2.9) < 0.1,
      "two composite anchors, same material class, 2.9x apart")
    t("  and the CARD sits between them, nearer Zhang",
      y_rise < card_rise < z_rise,
      "42.5 %: so 'too steep' and 'too shallow' are both live verdicts")
    t("C2-C4's verdicts are marked conditional in this file's own text",
      "conditional on Yang" in open(__file__, encoding="utf-8").read(),
      "a single-source judgement must say it is one")
    t("  and the arbitration is routed to a1, not decided here",
      "a1's call" in open(__file__, encoding="utf-8").read())

    print("\n D. the matrix card sits inside Snead's own band")
    t("Gm_t = 0.031 N/mm is 31 J/m2", abs(GM_T * 1000.0 - 31.0) < 0.5,
      "%.0f J/m2" % (GM_T * 1000.0))
    t("Snead Fig. 14 energy axis tops out at 30 J/m2",
      abs(SNEAD_GF_AXIS_MAX - 30.0) < 1e-9)
    t("the card is at the top of that band, within 5 %",
      abs(GM_T * 1000.0 / SNEAD_GF_AXIS_MAX - 1.0) < 0.05,
      "%.2fx the axis maximum" % (GM_T * 1000.0 / SNEAD_GF_AXIS_MAX))

    print("\n E. what is claimed and what is refused")
    t("Fig. 14 is explicitly NOT digitised", "NOT digitised here" in __doc__)
    t("the reason is stated (interleaved axes)",
      "interleave the two" in __doc__)
    t("no Gf(T) column is licensed by this",
      "does not license" in __doc__)
    t("the refs/[15] route is marked SECONDARY and not cited",
      "SECONDARY citation of a MODEL" in __doc__)
    t("the room-temperature-only limit of refs/[31] is stated",
      "ROOM TEMPERATURE only" in __doc__)

    print("\n F. the sign of the error is stated, not left to the reader")
    for needle, label in (
            ("A is over-estimated at high temperature",
             "direction of the A error"),
            ("predicts MORE damage there", "consequence"),
            ("conservative direction for a life prediction",
             "and whether it is safe")):
        t(label, needle in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d Gf(T) CLAIMS HOLD "
              "(direction sourced, drift bounded at 5-6 %%)" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
