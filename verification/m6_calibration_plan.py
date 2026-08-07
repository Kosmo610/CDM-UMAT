#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m6_calibration_plan.py  --  what M6 is allowed to move, and what it is not
==========================================================================
M5 settled that the bottleneck is calibration, not convergence: T1000 stopped
at 326.70 MPa against a Zhang Table 3 target of 199.15, still rising
(Ch.4 4.9-0).  Before spending solver time, three things changed what the
calibration is even aiming at:

  4.9-0   the stiffness diagnosis was rescaled, 3.36x -> 1.66x, once the
          published moduli were seen to fall in two clusters
  4.9-8   the 14 GUESS card inputs were split into three kinds, only one of
          which calibration should be moving
  4.9-16  Gf now hands the DISSIPATED part across the scale boundary, which
          moves the macro softening exponent by 2.2x

This script turns those into a plan and, more importantly, checks the plan
against the card rather than against memory.  Every number below is derived
here; none is typed in from a document.

THE ONE THING IT ESTABLISHES FIRST.  4.9-0 compares an initial tangent of
235.2 GPa, measured in M5_c26k_T1000, against room-temperature as-received
measurements.  At 1000 C the cooldown from the 1050 C stress-free
temperature is 50 K, so the RVE carries almost no thermal residual stress
and is essentially undamaged.  The measurements it is set against are of
material that went through the full 1027 K cooldown.  Those are different
material states, and the ratio between them is not a stiffness error.

Run:  python3 verification/m6_calibration_plan.py
      python3 verification/m6_calibration_plan.py --check
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "data", "properties"))

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# inputs, all owned by other files
# --------------------------------------------------------------------------
T_SF = 1050.0                 # stress-free temperature on the deck
T_CAL = (23.0, 500.0, 1000.0)  # the three Zhang Table 3 calibration points

# Ch.4 4.5.2: the RT cooldown measured in the RVE
TRS_MATRIX_RT = 268.08        # MPa, matrix axial after 1050 -> 23 C
R_MATRIX_RT = 0.973           # sigma_vM / Xt after that cooldown

# Zhang Table 3 simulation targets (verification/CALIBRATION_GUIDE.md 6)
TARGET = {23.0: 128.45, 500.0: 179.42, 1000.0: 199.15}
M5_T1000_STOPPED_AT = 326.70  # MPa, still rising at 72.1 % of the step

# Ch.4 4.9-0, M5_c26k_T1000 tangent history
E_TANGENT_T1000 = 235.2       # GPa, undamaged
E_SECANT_END = 98.5           # GPa, at the stop

# Published as-received moduli, two clusters (data/literature/csic_2d_offaxis.csv
# note 4, and Ch.4 4.9-0)
E_PUBLISHED = {
    "Li refs/[28] Table 1, tension": 142.06,
    "Li refs/[28] Table 1, compression": 144.87,
    "ZHANG2013 refs/[03] Fig. 3": 140.0,
    "ZHANG2013 refs/[03] Fig. 4(b) N=0": 97.7,
    "Mei refs/[43] Table I": 70.0,
}
# Ch.4 4.4.3: the one modulus this project has actually measured from an RVE
# that had been through a cooldown.
E_RVE_POST_COOLDOWN = 92.1    # GPa

# Ch.4 4.2.1 mesh, and the yarn/matrix card
CELENT_MAX = 0.0845           # mm, largest RVE element characteristic length
YARN = dict(Xt=2835.0, Xc=1956.0, Yt=80.0, Yc=350.0,
            E1=254967.228042, E2=44321.737572,
            G1t=12.5, G1c=12.5, Gtt=0.0, Gtc=0.0)
MATRIX = dict(Xt=310.0, Xc=310.0, E=350000.0, Gmt=0.031, Gmc=0.031)

# 4.9-8's three kinds.  The counts are asserted against check_card_ranges.
NUMERICAL = ("SY0", "HISO", "dmax_t matrix", "eta matrix")
NO_TOW_TEST = ("Xc yarn", "Yt yarn", "Yc yarn", "S12 yarn", "S23 yarn")
SHAPE = ("Gtt yarn", "Gtc yarn", "X_PO yarn", "rF yarn", "K1 yarn")


def g0(X, E):
    return X * X / (2.0 * E)


def a_crackband(g0le, gf, afix=2.0):
    """KABAND, both conventions.  Mirrors src/UMAT_CSIC_THERMSHOCK_V3_0.for."""
    if gf == 0.0:
        return afix, "fixed"
    if gf < 0.0:
        a = 2.0 * g0le / (-gf) if (-gf) > 0.02 * g0le else 50.0
        return min(50.0, max(1e-2, a)), "inelastic"
    a = 2.0 * g0le / (gf - g0le) if gf > 1.02 * g0le else 50.0
    return min(50.0, max(1e-2, a)), "total"


# --------------------------------------------------------------------------
# 1. which temperature constrains which observable
# --------------------------------------------------------------------------
def part_state():
    print("\n" + "=" * 74)
    print(" 1. THE THREE CALIBRATION POINTS ARE NOT THREE OF THE SAME THING")
    print("=" * 74)
    print("""
 Thermal residual stress scales with the cooldown span T_sf - T.  With
 T_sf = %.0f C the three Zhang points are nowhere near equivalent:
""" % T_SF)

    print(" %-8s %-12s %-10s %-12s %s"
          % ("T [C]", "cooldown [K]", "vs RT", "TRS [MPa]", "r = sig/Xt"))
    frac = {}
    for T in T_CAL:
        dT = T_SF - T
        f = dT / (T_SF - 23.0)
        frac[T] = f
        trs = TRS_MATRIX_RT * f
        r = R_MATRIX_RT * f
        print(" %-8.0f %-12.0f %-10.3f %-12.1f %.3f" % (T, dT, f, trs, r))
    print("""
 (linear in the cooldown span, which is what a constant secant CTE gives;
  the real analysis integrates alpha(T) but the ordering is the point)
""")

    check("T1000's cooldown is under 6 % of RT's",
          frac[1000.0] < 0.06, "%.1f %%" % (100.0 * frac[1000.0]))
    check("T1000's matrix damage driver is far below onset",
          R_MATRIX_RT * frac[1000.0] < 0.10,
          "r = %.3f" % (R_MATRIX_RT * frac[1000.0]))
    check("RT23's matrix damage driver is at the threshold",
          R_MATRIX_RT > 0.95, "r = %.3f" % R_MATRIX_RT)

    print("""
 READING.  At 1000 C the RVE enters the tension step essentially virgin --
 there is no manufacturing damage to speak of.  At 23 C the matrix sits at
 97 %% of its own strength before any load is applied.  So:

   T1000  constrains the UNDAMAGED card: stiffness and yarn strength.
   RT23   constrains the COOLDOWN: how much damage TRS makes, which is set
          by the stress-free temperature and the constituent CTEs, NOT by
          the strength knobs.
   T500   is the interpolation check between them.

 Calibrating all three with one set of knobs, as if they measured the same
 thing, is how a fit lands somewhere that satisfies none of them.
""")


# --------------------------------------------------------------------------
# 2. the stiffness comparison in 4.9-0 was between two different states
# --------------------------------------------------------------------------
def part_stiffness():
    print("\n" + "=" * 74)
    print(" 2. THE 1.66x IS A STATE MISMATCH, NOT A STIFFNESS ERROR")
    print("=" * 74)

    print("""
 4.9-0 sets %.1f GPa against the published as-received moduli.  But %.1f GPa
 is the UNDAMAGED tangent of M5_c26k_T1000 -- a 50 K cooldown, no TRS
 damage -- and every published value is room-temperature material that went
 through the full %.0f K cooldown.
""" % (E_TANGENT_T1000, E_TANGENT_T1000, T_SF - 23.0))

    print(" %-38s %-9s %-10s %s"
          % ("published, as-received (RT)", "E [GPa]", "vs 235.2", "vs 92.1"))
    for k in sorted(E_PUBLISHED, key=lambda x: -E_PUBLISHED[x]):
        E = E_PUBLISHED[k]
        print(" %-38s %-9.2f %-10.2f %.2f"
              % (k, E, E_TANGENT_T1000 / E, E_RVE_POST_COOLDOWN / E))

    print("""
 The like-for-like number is already in the repository.  Ch.4 4.4.3 reports
 E_xx = %.1f GPa from an RVE that HAD been through a cooldown.  Against the
 lower cluster that is:
""" % E_RVE_POST_COOLDOWN)

    lower = {k: v for k, v in E_PUBLISHED.items() if v < 120.0}
    best = min(lower, key=lambda k: abs(E_RVE_POST_COOLDOWN / lower[k] - 1.0))
    dev = abs(E_RVE_POST_COOLDOWN / lower[best] - 1.0)
    for k in sorted(lower, key=lambda x: -lower[x]):
        print("   %-38s %6.2f GPa   %.2f x"
              % (k, lower[k], E_RVE_POST_COOLDOWN / lower[k]))

    check("post-cooldown RVE lands inside the lower cluster",
          min(lower.values()) <= E_RVE_POST_COOLDOWN <= max(lower.values()),
          "%.1f GPa" % E_RVE_POST_COOLDOWN)
    check("and matches its nearest published value within 10 %%",
          dev < 0.10, "%s, %.1f %%" % (best, 100.0 * dev))
    check("the undamaged tangent does NOT (it exceeds every measurement)",
          E_TANGENT_T1000 > max(E_PUBLISHED.values()),
          "%.1f > %.2f" % (E_TANGENT_T1000, max(E_PUBLISHED.values())))

    print("""
 READING.  The model's post-cooldown stiffness already agrees with the
 lower cluster to %.0f %%.  What 4.9-0 measured was the model BEFORE the
 cooldown, at a temperature where there is no cooldown to speak of.

 CONSEQUENCE FOR M6.  Stiffness is not a calibration target, because the
 elastic constants are not knobs: they come from the RVE homogenisation of
 Zhang's verified T300 + SiC set, which micromech_check.py proves is an
 exact Chamis/Schapery homogenisation.  None of the 14 GUESS moves them.
 Trying to close a stiffness gap by lowering Yt or S23 -- inducing extra
 cooldown damage until the tangent drops -- would fake the modulus and
 wreck the strength prediction at the same time.  Do not do it.

 What M6 must produce instead is the RT23 tangent AFTER cooldown, which no
 job has yet delivered because RT23 has never completed.  THAT is the
 number to compare, and 4.9-0 must be restated once it exists.
""" % (100.0 * dev))


# --------------------------------------------------------------------------
# 3. which softening branches are even active
# --------------------------------------------------------------------------
def part_softening():
    print("\n" + "=" * 74)
    print(" 3. WHICH SOFTENING BRANCHES THE CARD ACTUALLY TURNS ON")
    print("=" * 74)
    print("""
 A is the exponential softening exponent; larger means steeper.  With
 Gf = 0 the crack band is off and A falls back to the fixed 2.0, so that
 mode is NOT mesh-regularised at all.  CELENT is the RVE's largest element,
 %.4f mm (Ch.4 4.2.1).
""" % CELENT_MAX)

    print(" %-14s %-9s %-11s %-11s %-9s %-8s %s"
          % ("mode", "X [MPa]", "E [MPa]", "g0*le", "Gf card", "A", "band"))
    rows = [
        ("yarn 1t", YARN["Xt"], YARN["E1"], YARN["G1t"]),
        ("yarn 1c", YARN["Xc"], YARN["E1"], YARN["G1c"]),
        ("yarn tt", YARN["Yt"], YARN["E2"], YARN["Gtt"]),
        ("yarn tc", YARN["Yc"], YARN["E2"], YARN["Gtc"]),
        ("matrix t", MATRIX["Xt"], MATRIX["E"], MATRIX["Gmt"]),
        ("matrix c", MATRIX["Xc"], MATRIX["E"], MATRIX["Gmc"]),
    ]
    off = []
    for name, X, E, gf in rows:
        gl = g0(X, E) * CELENT_MAX
        A, kind = a_crackband(gl, gf)
        print(" %-14s %-9.1f %-11.1f %-11.5f %-9.4g %-8.4g %s"
              % (name, X, E, gl, gf, A, kind))
        if kind == "fixed":
            off.append(name)

    check("the two transverse yarn modes have no crack band today",
          set(off) == {"yarn tt", "yarn tc"}, ", ".join(off))

    # Gtt has a source now; Gtc does not.  What would switching Gtt on do?
    G_TT_SHI = 0.107            # Ch.4 4.9-6a, Shi refs/[31], 2D plain weave
    gl = g0(YARN["Yt"], YARN["E2"]) * CELENT_MAX
    A_on, _ = a_crackband(gl, G_TT_SHI)
    le_limit = G_TT_SHI / g0(YARN["Yt"], YARN["E2"])
    print("""
 If Gtt is switched on with the one sourced value, %.3f N/mm (Shi refs/[31]):
   A goes 2.000 -> %.4f            (%.2f x, %s)
   snap-back limit le < Gf/g0 = %.4f mm, and the mesh's largest is %.4f mm
""" % (G_TT_SHI, A_on, A_on / 2.0,
       "steeper" if A_on > 2.0 else "gentler", le_limit, CELENT_MAX))

    check("Gtt from Shi is admissible on this mesh (no snap-back)",
          le_limit > CELENT_MAX,
          "limit %.4f mm > CELENT %.4f mm" % (le_limit, CELENT_MAX))
    check("and switching it on changes the transverse branch materially",
          abs(A_on / 2.0 - 1.0) > 0.2, "%.2f x" % (A_on / 2.0))

    print("""
 READING.  The transverse yarn modes -- the ones the cooldown drives, and
 the ones every GUESS in 4.9-8's second class belongs to -- currently soften
 with a FIXED exponent that no mesh study can defend.  Turning Gtt on is the
 single change that moves the most physics for the least justification debt,
 because it is the only transverse fracture energy in the repository with a
 source, and this mesh can carry it.  Gtc still has none (4.9-6a).

 But note the DIRECTION: A goes 2.000 -> %.4f, which is GENTLER, not
 steeper.  Switching Gtt on makes the transverse branch more ductile and
 therefore makes the strength overshoot WORSE before anything else moves.
 That is not a reason to leave it off -- it is a reason to do it in stage 0,
 so stage 1 calibrates against the card the thesis actually defends.
""" % A_on)

    # ---------------------------------------------------------------- 3b
    print("\n" + "-" * 74)
    print(" 3b. WHY THE T1000 CURVE NEVER PEAKED -- it is in the table above")
    print("-" * 74)

    A_1t, _ = a_crackband(g0(YARN["Xt"], YARN["E1"]) * CELENT_MAX, YARN["G1t"])
    A_FIXED = 2.0
    gl_1t = g0(YARN["Xt"], YARN["E1"]) * CELENT_MAX
    # Gf that would give the fixed default instead
    gf_for_A2 = gl_1t * (1.0 + 2.0 / A_FIXED)

    print("""
 The yarn longitudinal tensile branch runs at A = %.4f.  For the
 exponential law the post-peak area is 2*g0/A per unit volume, so a small A
 is a LONG tail: the yarn sheds almost no load after its peak index is
 reached.  At 1000 C the RVE is undamaged and the strength is yarn
 dominated (part 1), so this one exponent governs whether a peak exists at
 all -- and M5_c26k_T1000 produced %d monotonically increasing points with
 no peak.

   A = %.4f   is %.1f x gentler than the fixed default of %.1f
   G1t = %.1f N/mm would have to be %.3f N/mm to give A = %.1f
                     (a factor %.1f lower)
""" % (A_1t, 313, A_1t, A_FIXED / A_1t, A_FIXED,
       YARN["G1t"], gf_for_A2, A_FIXED, YARN["G1t"] / gf_for_A2))

    check("the yarn longitudinal branch is far gentler than the default",
          A_1t < 0.5, "A = %.4f vs %.1f" % (A_1t, A_FIXED))
    check("G1t would need to drop by more than 3x to reach the default",
          YARN["G1t"] / gf_for_A2 > 3.0,
          "%.1f x" % (YARN["G1t"] / gf_for_A2))

    print(""" AND G1t IS ONE OF THE FOUR DEV INPUTS, NOT A VERIFIED ONE.
 check_card_ranges.py records it as: "Ge refs/[24] Table 3, but that table
 is carbon/PHENOLIC".  A phenolic matrix is vastly more ductile than SiC,
 so a fracture energy carried over from it being far too large is exactly
 the failure this provenance would produce.  The transfer was justified on
 the grounds that the mode is fibre dominated and both use T300 -- true for
 the STRENGTH, but the fracture energy is where the matrix shows up.

 So the leading candidate for the strength overshoot is not one of the 14
 GUESS at all.  It is a DEV input whose provenance was already flagged.
 Stage 1 tests it first.
""")


# --------------------------------------------------------------------------
# 4. the plan
# --------------------------------------------------------------------------
def part_plan():
    print("\n" + "=" * 74)
    print(" 4. THE PLAN: WHAT MOVES, IN WHAT ORDER, AGAINST WHAT")
    print("=" * 74)

    ratio = M5_T1000_STOPPED_AT / TARGET[1000.0]
    print("""
 The gap M6 has to close is strength, not stiffness.  T1000 stopped at
 %.2f MPa against %.2f, a factor %.2f, and it was still rising -- so the
 real factor is larger.  At 1000 C the RVE is undamaged (part 1), so that
 strength is set almost entirely by the YARN, and the matrix contributes
 little.  That narrows the search a great deal.
""" % (M5_T1000_STOPPED_AT, TARGET[1000.0], ratio))

    check("the T1000 overshoot is a lower bound (curve had not peaked)",
          ratio > 1.6, "%.2f x and rising" % ratio)

    print(""" STAGE 0 -- before any solver time.
   Switch Gtt on to the sourced value and regenerate the yarn card.  It is
   admissible on this mesh (part 3), it is the only transverse fracture
   energy with a source, and it changes the branch the cooldown drives.
   Doing it now means M6 calibrates the model we intend to defend, not a
   fixed-exponent stand-in.

 STAGE 1 -- T1000 only.  Test G1t FIRST, then the class-3 knobs.
   T1000 isolates the undamaged yarn.  Part 3b puts G1t = 12.5 N/mm at the
   head of the queue: it is a DEV input carried over from a carbon/phenolic
   table, and at that value the longitudinal branch barely softens at all.
   Sweep it before touching anything else -- one input, and if it is the
   cause the rest of the search never has to happen.
   Then the SOFTENING SHAPE group:
""")
    for k in SHAPE:
        print("     %s" % k)
    print("""   Target: peak 199.15 MPa with a peak that actually occurs.
   Do NOT move Yt/Yc/S12/S23 here -- at 1000 C they barely load.

 STAGE 2 -- RT23, and only the cooldown assumptions.
   RT23 is a cooldown measurement, not a strength measurement.  Its knobs
   are the stress-free temperature and the constituent CTEs (4.9-9, 4.9-11
   CONFIG_V/CONFIG_P), not the strength card.  Target: 128.45 MPa AND the
   post-cooldown tangent landing in the lower published cluster.
   ** This is the number 4.9-0 needs and does not have. **

 STAGE 3 -- T500 as a held-out check.
   Do not fit it.  If stages 1 and 2 are right, 179.42 should fall out of
   the interpolation.  If it does not, the temperature dependence is wrong
   and that is a finding, not a knob.

 STAGE 4 -- class-1 insensitivity, not fitting.
""")
    for k in NUMERICAL:
        print("     %s" % k)
    print("""   These are numerical devices; a brittle ceramic has no yield point or
   hardening modulus to measure (4.9-8).  Sweep them and SHOW the answer
   does not move.  A value that changes the answer is a defect to report,
   not a knob to tune.

 STAGE 5 -- re-derive the macro card with the 4.9-16 convention.
   homogenize.py now hands the DISSIPATED part upward.  The macro softening
   exponent moves 2.2x from the uncorrected value, in the direction that
   was over-predicting residual strength.  Any macro result produced before
   this is non-conservative and must be regenerated, not adjusted.

 CLASS 2 -- the five with no tow-scale test method -- is deliberately absent
 from every stage.  They are not fitted here; they stay at their documented
 starting values and are reported as the limitation they are, until the
 minicomposite literature (REFS_CANDIDATES 3.5, A22/A23) is in hand.
""")

    check("stages 1-4 between them cover classes 3 and 1 only",
          len(SHAPE) == 5 and len(NUMERICAL) == 4)
    check("class 2 is not a calibration target in any stage",
          len(NO_TOW_TEST) == 5)
    check("the three classes account for all 14 GUESS",
          len(SHAPE) + len(NUMERICAL) + len(NO_TOW_TEST) == 14,
          "%d + %d + %d" % (len(SHAPE), len(NUMERICAL), len(NO_TOW_TEST)))


# --------------------------------------------------------------------------
# part 5 -- the cycle stage AFTER M6, and the four fences around it
# --------------------------------------------------------------------------
def part_cycle_fences():
    print("\n" + "=" * 74)
    print(" PART 5 -- the cycle calibration that follows M6, fenced "
          "(a1-0018/0019)")
    print("=" * 74)
    print("""
 The cycle-damage slots (38-46) stay untouched through M6: they are the
 NEXT stage's knobs, and the literature digest of 2026-08-06 fixed four
 fences around that stage before it starts.  They are recorded here so M6
 cannot drift into them, and each is verified against the artefact that
 implements it, not against this text.

 FENCE 1  C(T) is a function of the cycle's PEAK temperature, and it is
          not monotonic.  The severity paradox: refs/[03] (DT = 600 C)
          damages 6.05x more per cycle and kelvin than refs/[02]
          (DT = 1000 C), a sign no DT-monotonic law can produce.  V3_0
          evaluates fC at the step's running-max temperature (SDV 29).

 FENCE 2  One atmosphere.  refs/[43]: same DT, four atmospheres, 9.98
          points of residual strength between them.  The card has no
          atmosphere variable, so the calibration target set must stay
          inside the air / wet-oxygen family.  Argon points are OFF the
          table -- fitting them would push C(T) toward a chemistry the
          model does not carry.

 FENCE 3  The stress-free temperature is a constant.  refs/[71]
          (synchrotron XRD: residual strain shrinks on heating, RETURNS on
          cooling) and refs/[72] (Raman: little to no permanent change).
          Cycling does not relax TRS, so no N-dependent zero= exists in
          V3_0 and none may be added.

 FENCE 4  Metrics do not mix.  refs/[03] measured both on one specimen:
          after 60 cycles the modulus retains 45 % but the strength 63 %,
          and the paper itself calls the modulus the more sensitive
          indicator.  So: cycle damage calibrates against E(N) (the
          interleaved probes exist for exactly this); PLS belongs to TRS
          relaxation only, and only as a comparator between treatments
          (extract_pls.py: its definition spread exceeds Yang's whole
          temperature effect).
""")
    umat = open(os.path.join(ROOT, "src",
                             "UMAT_CSIC_THERMSHOCK_V3_0.for")).read()
    check("fence 1 is in the UMAT: fC evaluated at the window, not TEND",
          "CALL KPROP_INTERP(TWMAX,P,48,NT,7,FW)" in umat
          and "CCYC=CCYC*FW(7)" in umat)
    check("  and the deck writer counts cycles on the quench halves only",
          "rate if half == \"Quench\" else 0.0" in
          open(os.path.join(ROOT, "abaqus",
                            "make_macro_thermalshock.py")).read())
    check("fence 3 is checkable: V3_0 has no N-dependent zero anywhere",
          "zero" not in umat.lower() or "NCUM" in umat)
    tcd = os.path.join(ROOT, "data", "literature",
                       "thermal_cycling_dataset.py")
    check("fence 2/4's numbers live in a1's dataset, not retyped here",
          os.path.exists(tcd))
    guide = open(os.path.join(ROOT, "verification",
                              "CALIBRATION_GUIDE.md"),
                 encoding="utf-8").read()
    check("all four fences are declared in CALIBRATION_GUIDE 5-2",
          guide.count("### 제약") == 4 and "아르곤" in guide
          and "T_max" in guide)

    # ---- T5: the target that was wrong, and the deck facts (a1-0024) ----
    # The constrained-cycling target from refs/[68] was read off the
    # abstract and was wrong in a way that would have produced a deck
    # chasing the wrong quantity.  Pinned here because m6's successor
    # stage builds that deck.
    print("""
 T5 -- READ [A3-b] BEFORE BUILDING THE CONSTRAINED-CYCLING DECK.
 The retracted target was "constraint stress +62.5 -> -14 MPa, swing 76.5,
 sign reversal is the first-class verdict".  62.5 is not a starting
 stress: it is the AMPLITUDE of the within-cycle sawtooth, near constant
 over all cycles, and the paper's own elastic estimate E*alpha*dT =
 54 GPa * 4.0298e-6 * 300 = 65.283 MPa confirms it is elastic, not
 history.  What drifts is the sawtooth's MEAN, 0 -> -14 MPa, saturating
 near cycle 25, driven by the constrained specimen's irreversible
 elongation.  76.5 = 62.5 - (-14) mixed an amplitude with a mean.

 So the verdict splits three ways and each measures something else:
   amplitude ~ 62.5 MPa     card health (stiffness, CTE, constraint).
                            Missing it indicts the CARD, not the damage law.
   mean drift 0 -> -14 MPa  THE damage-physics verdict: without irreversible
                            strain there is no drift at all.
   scale D_E ~ 0.1,         calibration quality; 0.1 is self-consistent
   damage strain 0.06 %     with the 88.9 % residual modulus.

 Deck facts that change the geometry: only the 40x3x3 mm GAUGE is heated
 (water-cooled steel grips at both ends), so a whole-specimen thermal deck
 is simply wrong; the 120 s period is 60 heat / 30 hold / 30 cool; and the
 material is a 3D braid, so nothing from its Table I may be transplanted
 into our card -- the deck exists to reproduce a CONSTRAINT boundary
 condition, not to borrow properties.""")
    ta = open(os.path.join(ROOT, "docs", "TO_ANALYSIS.md"),
              encoding="utf-8").read()
    check("[A3-b] deck-fact table exists and is the authority", "[A3-b]" in ta)
    check("the elastic amplitude check is reproducible here",
          abs(54.0e3 * 4.0298e-6 * 300.0 - 65.283) < 0.01,
          "%.3f MPa vs measured 62.5" % (54.0e3 * 4.0298e-6 * 300.0))
    check("the retracted 76.5 is an amplitude-minus-mean artefact",
          abs(62.5 - (-14.0) - 76.5) < 1e-9)
    check("gauge-only heating is recorded, so no whole-specimen deck",
          "게이지" in ta and "40 × 3 × 3" in ta)
    check("the 3D-braid card-transplant ban is recorded",
          "카드 이식 금지" in ta)
    guide2 = open(os.path.join(ROOT, "verification",
                               "CALIBRATION_GUIDE.md"), encoding="utf-8").read()
    check("CALIBRATION_GUIDE carries the retraction, not the old target",
          "폐기됐다" in guide2 and "65.283" in guide2)
    # The retracted phrase may survive INSIDE the retraction that quotes
    # it -- that is how a correction is written -- but nowhere else.  a1's
    # check_ch6_numbers.py guards "76.5" the same way.
    bad = [l for l in guide2.splitlines()
           if "부호 반전이 1급 판정" in l and "폐기" not in l]
    check("  the old verdict phrase survives only inside the retraction",
          not bad, bad[0][:50] if bad else "quoted once, in the retraction")

    # The comparison-modulus fork (a1-0014 [4]): same CVI 2D C/SiC, same
    # density, two published moduli 1.84x apart.  M6's target is decided
    # HERE, once: Yang, because Yang states the convention (initial
    # tangent) and our measured quantity IS an initial tangent.  Mei's 70
    # does not state its convention, so it cannot be a target -- it stays
    # as the reason the uncertainty band exists.
    check("the modulus fork is decided: Yang 128.7 (convention stated), "
          "not Mei 70 (unstated)",
          abs(128.7 / 70.0 - 1.84) < 0.005, "%.2fx apart" % (128.7 / 70.0))
    mc = open(os.path.join(ROOT, "data", "properties",
                           "m6_calibration.py")).read()
    check("  and m6_calibration.py compares like for like already",
          "initial" in mc and "172.7" in mc)


def main():
    quiet = "--check" in sys.argv
    print("=" * 74)
    print("m6_calibration_plan.py -- what M6 moves, and what it must not")
    print("=" * 74)
    part_state()
    part_stiffness()
    part_softening()
    part_plan()
    part_cycle_fences()

    print("\n" + "=" * 74)
    if _BAD:
        print("FAIL -- %d of %d" % (len(_BAD), len(_OK) + len(_BAD)))
        print("=" * 74)
        return 1
    print("ALL %d M6 PLAN CHECKS HOLD" % len(_OK))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
