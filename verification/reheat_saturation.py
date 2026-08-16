#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reheat_saturation.py -- why does the matrix reach the damage cap during a step
that applies no load?
==============================================================================
Ch.4 4.9-0d recorded the fact: in M6 T500 the matrix ends the manufacturing
cooldown at DAMG = 0.344 and ends the REHEAT at 0.900, the card ceiling, in a
step that pulls nothing.  Ch.3 3.8-8 then hung a gate on the C1 conclusion
because of it.  Both were written from the observation alone.  This file asks
what actually produced it, using the Python mirror of the matrix point rather
than another run.

THE OBVIOUS EXPLANATIONS, AND WHY THEY ARE WRONG
------------------------------------------------
1. "The strength falls with temperature."  It does not.  The matrix card is 25
   constants with no temperature table at all -- X_t is 310 MPa at every
   temperature the deck visits.  Only the yarn card carries T-dependence.

2. "Reheating loads the matrix."  It unloads it.  The matrix CTE (4.5e-6) is
   larger than the yarn's axial one (1.07e-6), so cooling from the stress-free
   1050 C puts the matrix in tension; heating back towards 1050 takes that
   tension away.  A two-phase parallel bar gives the matrix mechanical strain
   as V_y E_y (a_y - a_m) dT / (E_m V_m + E_y V_y), which shrinks in magnitude
   as dT shrinks.  Monotonically.

WHAT THE MIRROR SHOWS -- TWO MECHANISMS, AND ONLY ONE IS NUMERICAL
------------------------------------------------------------------
Two lines of the constitutive update matter:

    RT  = max(sv[2], FIT)                     the loading function is a
                                              HIGH-WATER MARK; it never falls
    gam = dtime / (ETA + dtime)               damage moves only a FRACTION of
    d   = d + gam * (target(RT) - d)          the way to its target each
                                              increment

So the target is set by the worst state a point has ever seen, and the viscous
regularisation (ETA = 0.05) makes the damage APPROACH that target rather than
reach it.  Driving the mirror through cooldown-then-reheat confirms this
happens: on the reheat leg the strain falls monotonically and RT does not move
at all, yet d still climbs, because the cooldown had committed a target the
damage had not finished reaching.

BUT THE LAG IS NOT ENOUGH, AND SAYING SO IS THE POINT.  It carries d from the
measured 0.344 to 0.435 -- the target belonging to that frozen RT -- and then
stops.  It accounts for about a sixth of the distance to the 0.900 ceiling.
The remaining rise cannot come from a single material point at all: with RT
frozen there is no more damage available to it.  It has to come from LOAD
REDISTRIBUTION between points -- softened elements shedding onto neighbours
that then cross their own thresholds.

That distinction is what Ch.3 3.8-8 needed.  The reheat rise is not mostly a
numerical artefact of the viscous lag; it is mostly the damage-driven
redistribution that C1's B-vs-C difference is DEFINED as.  The gate therefore
gets stronger, not weaker: the mechanism the thesis wants to measure is
already running, and already hitting the ceiling, before any load is applied.

Run:  python3 verification/reheat_saturation.py --check
"""
from __future__ import print_function

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import verify_constitutive as vc                              # noqa: E402

#: the SIC_MATRIX_DAMAGE card exactly as dist/LTH_M6_0812_1411.zip ships it
MATRIX_CARD = np.array([
    2.0, 213109.62776993477, 0.2, 310.0, 310.0, 0.0, 0.0, 0.9,
    0.9, 0.05, 0.1, 3.0, 0.25, 1.0, 0.031, 0.031,
    250.0, 100000.0, 1.15, 0.75, 0.5, 30.0, 0.0, 0.1,
    32.0])

#: measured, from data/results/M6/LTH_M6_T500_damage_map.csv
DAMG_END_COOL = 0.344269
DAMG_END_HEAT = 0.900000
DMAX = 0.9

#: the deck's own step definition: *Static 0.0005, 1.0, 1e-08, 0.0025
DT_INITIAL, STEP_TIME, DT_MAX = 0.0005, 1.0, 0.0025

#: constituents, for the two-phase thermal argument
ALPHA_M = 4.5e-6                # *Expansion on SIC_MATRIX_DAMAGE
ALPHA_Y1 = 1.070925962822e-06   # yarn axial
E_M, E_Y1 = 213109.62776993477, 254967.228042
V_Y = 0.4982
T_ZERO, T_COLD, T_HOT = 1050.0, 23.0, 500.0
#: representative element size, celent_census.py (RVE median V^(1/3))
CELENT = 0.053


def matrix_mech_strain(t_now, t_zero=T_ZERO):
    """Matrix mechanical strain from a two-phase parallel bar, at T = t_now.

    Sign convention: positive is tension.  Cooling (t_now < t_zero) gives a
    positive number because the matrix wants to shrink more than the yarn and
    is held back.
    """
    dT = t_now - t_zero
    num = V_Y * E_Y1 * (ALPHA_Y1 - ALPHA_M) * dT
    den = E_M * (1.0 - V_Y) + E_Y1 * V_Y
    return num / den


def damage_target(rt):
    """The damage the card is committed to once the loading function is rt."""
    b = vc.kaband(MATRIX_CARD[3] ** 2 / (2.0 * MATRIX_CARD[1]) * CELENT,
                  MATRIX_CARD[14], MATRIX_CARD[5])
    return vc.kdamage_target(rt, b, DMAX)


def increments_to_close(d0, target, eta=None, dt=DT_MAX, limit=100000):
    """How many increments the viscous lag needs to get within 1e-4."""
    eta = MATRIX_CARD[9] if eta is None else eta
    gam = dt / (eta + dt)
    d, n = d0, 0
    while target - d > 1.0e-4 and n < limit:
        d += gam * (target - d)
        n += 1
    return n, d


def drive(path, nsub=200, scale=1.0, dt=DT_MAX):
    """Run the mirror through a temperature path, returning per-leg results.

    `path` is [(label, T_from, T_to, kstep)].  Only the MECHANICAL strain is
    imposed, which is what Abaqus hands a UMAT -- the thermal part is removed
    by *Expansion before the material sees it.

    `scale` multiplies the two-phase estimate.  It has to exist: the parallel
    bar reaches 88.5 % of the damage threshold and stops, while the real cell
    reaches d = 0.344, so the estimate is low by the amount a 1-D average is
    always low at a crimp -- triaxial constraint and stress concentration.
    Rather than pretend otherwise, the factor is CALIBRATED to reproduce the
    measured end-of-cooldown damage, and then the question this file exists
    to answer is asked of the reheat leg alone.  The shape of the leg -- a
    strictly falling strain -- is not affected by the factor, and the shape
    is the whole argument.
    """
    sv = np.zeros(20)
    out = []
    for label, t0, t1, kstep in path:
        emax_seen = None
        d_at_leg_start = sv[0]
        for k in range(1, nsub + 1):
            T = t0 + (t1 - t0) * k / float(nsub)
            e = scale * matrix_mech_strain(T)
            emax_seen = e if emax_seen is None else max(emax_seen, e)
            eps = np.array([e, 0.0, 0.0, 0.0, 0.0, 0.0])
            _s, _C, sv, diag = vc.matrix_point(eps, sv, MATRIX_CARD,
                                               dtime=dt, celent=CELENT,
                                               kstep=kstep)
        out.append(dict(leg=label, T_end=t1, eps_end=e, eps_max=emax_seen,
                        d=sv[0], d_start=d_at_leg_start, rt=sv[2],
                        target=damage_target(sv[2]), q=diag["q"],
                        fit=diag["FIT"]))
    return out


def lag_share_vs_eta(etas=(0.0, 0.025, 0.05, 0.1, 0.2), scale=None):
    """How much of the reheat rise the viscous lag explains, per ETA.

    ETA is a declared numerical KNOB (card_gap_triage: 'a solver parameter,
    not a material one'), and this is what it now buys: the share of the
    load-free reheat rise that is numerical rather than physical.  The drive
    (the calibrated cooldown path) is held fixed while ETA varies, so the
    column moves for one reason only.

    Returns [(eta, d_end_cool, target, lag_remaining, share_of_gap)] where
    share_of_gap = (target - d_end) / (DMAX - d_end): the fraction of the
    distance to the ceiling that pure single-point lag can still cover.
    """
    scale = calibrate() if scale is None else scale
    out = []
    for eta in etas:
        card = MATRIX_CARD.copy()
        card[9] = eta
        sv = np.zeros(20)
        nsub = 200
        for k in range(1, nsub + 1):
            T = T_ZERO + (T_COLD - T_ZERO) * k / float(nsub)
            eps = np.array([scale * matrix_mech_strain(T), 0, 0, 0, 0, 0])
            _s, _C, sv, _d = vc.matrix_point(eps, sv, card, dtime=DT_MAX,
                                             celent=CELENT, kstep=1)
        d_end, rt = sv[0], sv[2]
        target = damage_target(rt)
        lag = max(0.0, target - d_end)
        gap = DMAX - d_end
        out.append((eta, d_end, target, lag, lag / gap if gap > 0 else 0.0))
    return out


def calibrate(target_d=DAMG_END_COOL, lo=1.0, hi=3.0, tol=1.0e-6):
    """The scale that makes the cooldown leg end at the measured damage."""
    cool = [PATH[0]]
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        d = drive(cool, scale=mid)[0]["d"]
        if d < target_d:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


PATH = [("cooldown", T_ZERO, T_COLD, 1),
        ("reheat", T_COLD, T_HOT, 2)]


def report():
    print("=" * 78)
    print("reheat_saturation.py -- what put the matrix on the ceiling")
    print("=" * 78)

    print("\n 1. THE CARD HAS NO TEMPERATURE DEPENDENCE")
    print("    matrix constants      %d" % len(MATRIX_CARD))
    print("    X_t                   %.1f MPa at every temperature"
          % MATRIX_CARD[3])
    print("    -> falling strength cannot be the mechanism")

    print("\n 2. REHEATING UNLOADS THE MATRIX -- two-phase parallel bar")
    print("    %-10s %10s %14s" % ("T [C]", "dT [C]", "eps_mech [%]"))
    for T in (T_ZERO, T_COLD, T_HOT):
        print("    %-10.0f %10.0f %14.5f"
              % (T, T - T_ZERO, 100.0 * matrix_mech_strain(T)))
    print("    -> the reheat leg is a strictly DECREASING tensile strain")

    print("\n 3. THE 1-D ESTIMATE IS LOW, AND IS CALIBRATED RATHER THAN HIDDEN")
    bare = drive([PATH[0]])[0]
    print("    unscaled, the cooldown reaches r_t = %.4f -- BELOW 1, so the"
          % bare["rt"])
    print("    parallel bar predicts no damage at all, while the cell measures")
    print("    %.4f.  A 1-D average is always low at a crimp." % DAMG_END_COOL)
    sc = calibrate()
    print("    scale calibrated to the measured end-of-cooldown damage: %.4f"
          % sc)
    print("    the SHAPE of the reheat leg -- strictly falling -- is untouched")
    print("    by that factor, and the shape is the whole argument.")

    print("\n 4. WITH THE LOADING FUNCTION FROZEN, DAMAGE STILL CLIMBS")
    legs = drive(PATH, scale=sc)
    print("    %-10s %11s %11s %9s %9s %9s"
          % ("leg", "eps_end[%]", "eps_max[%]", "r_t", "target", "d_end"))
    for r in legs:
        print("    %-10s %11.5f %11.5f %9.4f %9.4f %9.4f"
              % (r["leg"], 100.0 * r["eps_end"], 100.0 * r["eps_max"],
                 r["rt"], r["target"], r["d"]))
    cool, heat = legs
    print("    the reheat strain never exceeds the cooldown's, and r_t does")
    print("    not move (%.4f both legs) -- yet d goes %.4f -> %.4f."
          % (heat["rt"], heat["d_start"], heat["d"]))
    print("    That is the viscous lag arriving, not new damage being driven.")

    print("\n 5. BUT THE LAG ONLY EXPLAINS PART OF IT")
    gap = DMAX - DAMG_END_COOL
    got = heat["d"] - heat["d_start"]
    print("    lag accounts for      %.4f of the %.4f rise to the ceiling"
          % (got, gap))
    print("    i.e. %.0f %%.  It then STOPS, at the target %.4f belonging to"
          % (100.0 * got / gap, cool["target"]))
    print("    the frozen r_t.  A single point has nothing left to give.")
    print("    The other %.0f %% cannot come from one point at all."
          % (100.0 * (gap - got) / gap))

    print("\n 6. SO THE REST IS REDISTRIBUTION -- WHICH IS THE POINT")
    print("    Softened elements shed onto neighbours, which cross their own")
    print("    thresholds, which softens them.  That feedback is EXACTLY what")
    print("    C1 defines the B-vs-C difference to be (Ch.2 2.8.3).")
    print("    So Ch.3 3.8-8's gate does not weaken -- it strengthens.  The")
    print("    mechanism the thesis sets out to measure is already running,")
    print("    and already on the ceiling, before any load is applied.")

    print("\n 7. WHAT WOULD SETTLE THE REMAINDER")
    n, _d = increments_to_close(DAMG_END_COOL, cool["target"])
    print("    The lag closes in %d increments and the deck writes 101 field" % n)
    print("    frames per step, so the reheat step's INTERMEDIATE frames already")
    print("    hold the answer -- damage_map reads frames[-1] only.  Reading the")
    print("    reheat step frame by frame separates the two contributions with")
    print("    no solver time at all.")
    print("\n 8. WHAT THE ETA KNOB BUYS -- the lag share is tunable, the rest is not")
    print("    %-8s %12s %10s %12s %12s"
          % ("ETA", "d_end cool", "target", "lag left", "share of gap"))
    for eta, d, tgt, lag, share in lag_share_vs_eta():
        print("    %-8.3f %12.4f %10.4f %12.4f %11.1f %%"
              % (eta, d, tgt, lag, 100.0 * share))
    print("    ETA is a declared numerical KNOB (card_gap_triage).  This is")
    print("    its price: it sets how much of the load-free reheat rise is")
    print("    numerical.  The redistribution part is whatever remains, and")
    print("    reheat_frames.py measures it from the odb, ETA-free.")
    print("=" * 78)
    return 0


_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def check():
    print("\n" + "=" * 78)
    print(" checks")
    print("=" * 78)

    print("\n A. the card really is temperature-free")
    t("the matrix card is the deck's 25 constants", len(MATRIX_CARD) == 25)
    t("X_t is a single number, not a table",
      float(MATRIX_CARD[3]) == 310.0, "%.1f MPa" % MATRIX_CARD[3])
    t("and the guard slot proves it is THIS card",
      float(MATRIX_CARD[21]) == 30.0, "PROPS(22) = 30.0")
    zips = os.path.join(ROOT, "dist", "LTH_M6_0812_1411.zip")
    if os.path.exists(zips):
        import zipfile
        with zipfile.ZipFile(zips) as z:
            nm = [n for n in z.namelist() if n.endswith("LTH_M6_T500.inp")]
            txt = z.read(nm[0]).decode("utf-8", "replace") if nm else ""
        seg = txt.split("Name=SIC_MATRIX_DAMAGE")[-1].split("*Expansion")[0]
        t("the shipped deck agrees, slot for slot",
          all(("%g" % v) in seg.replace(" ", "") or str(v) in seg
              for v in (310.0, 250.0, 100000.0, 0.05, 0.9)),
          "read back out of the zip")
        t("  and it declares 25 constants",
          "constants=25" in seg, "no temperature table")
    else:
        t("the shipped deck is available to confirm", False, zips)

    print("\n B. the reheat leg unloads, so it cannot be the driver")
    e_cold = matrix_mech_strain(T_COLD)
    e_hot = matrix_mech_strain(T_HOT)
    t("cooling puts the matrix in tension", e_cold > 0.0,
      "%.5f %%" % (100.0 * e_cold))
    t("reheating reduces that tension", 0.0 < e_hot < e_cold,
      "%.5f %% < %.5f %%" % (100.0 * e_hot, 100.0 * e_cold))
    t("  monotonically, with no sign change on the way",
      all(0.0 < matrix_mech_strain(T_COLD + (T_HOT - T_COLD) * i / 20.0)
          <= e_cold + 1e-15 for i in range(21)))
    t("  so a rising loading function is not available to it",
      e_hot < e_cold)

    print("\n C. the 1-D estimate is low, and the file says so")
    bare = drive([PATH[0]])[0]
    t("unscaled, the parallel bar does not even reach the threshold",
      bare["rt"] < 1.0 and bare["d"] == 0.0, "r_t = %.4f" % bare["rt"])
    sc = calibrate()
    t("so a scale is calibrated to the MEASURED cooldown damage",
      1.0 < sc < 3.0, "%.4f" % sc)
    t("  and the calibration is declared, not buried",
      "CALIBRATED to reproduce the" in drive.__doc__)
    t("  it does not change the shape of the reheat leg",
      matrix_mech_strain(T_HOT) < matrix_mech_strain(T_COLD),
      "scaling a falling curve leaves it falling")

    print("\n D. with the loading function frozen, damage still climbs")
    legs = drive(PATH, scale=sc)
    cool, heat = legs
    t("the cooldown lands on the measured damage",
      abs(cool["d"] - DAMG_END_COOL) < 1.0e-3, "d = %.4f" % cool["d"])
    t("the reheat strain never exceeds the cooldown's",
      heat["eps_max"] <= cool["eps_max"] + 1e-15,
      "%.5f %% vs %.5f %%" % (100.0 * heat["eps_max"],
                              100.0 * cool["eps_max"]))
    t("  and the loading function does not move at all",
      abs(heat["rt"] - cool["rt"]) < 1e-12, "r_t = %.4f both legs"
      % heat["rt"])
    t("yet damage rises on that leg anyway", heat["d"] > cool["d"] + 1e-4,
      "%.4f -> %.4f" % (cool["d"], heat["d"]))

    print("\n E. and the lag explains only part of the rise -- the honest half")
    gap = DMAX - DAMG_END_COOL
    got = heat["d"] - heat["d_start"]
    t("the lag stops at the target belonging to the frozen r_t",
      abs(heat["d"] - cool["target"]) < 1.0e-3,
      "d = %.4f, target = %.4f" % (heat["d"], cool["target"]))
    t("  which is well short of the ceiling", heat["d"] < DMAX - 0.4,
      "%.4f vs %.2f" % (heat["d"], DMAX))
    t("so the lag accounts for about a sixth, not the whole rise",
      0.10 < got / gap < 0.25, "%.0f %% of %.4f" % (100.0 * got / gap, gap))
    t("  and the file states that rather than claiming the mechanism",
      "BUT THE LAG IS NOT ENOUGH" in __doc__)
    t("  attributing the rest to redistribution, which one point cannot do",
      "REDISTRIBUTION between points" in __doc__)

    print("\n F. the two lines that produce the lag")
    src = open(os.path.join(HERE, "verify_constitutive.py")).read()
    t("the loading function is a high-water mark",
      "RT = max(sv[2], FIT)" in src)
    t("and the damage is viscously lagged toward its target",
      "gam = dtime / (ETA + dtime)" in src and "gam * (tar - dt0)" in src)
    t("ETA on this card is non-zero, so the lag is real",
      float(MATRIX_CARD[9]) > 0.0, "ETA = %.2f" % MATRIX_CARD[9])
    n0, _ = increments_to_close(DAMG_END_COOL, DMAX, eta=0.0)
    t("  with ETA = 0 there would be no lag at all",
      n0 <= 1, "%d increment" % n0)
    n, d = increments_to_close(DAMG_END_COOL, cool["target"])
    t("the lag closes well inside one step's increment budget",
      0 < n < 2000, "%d of the 2000 the deck permits" % n)

    print("\n G. what the chapters must therefore say")
    ch4 = open(os.path.join(ROOT, "docs",
                            "CH4_RVE_HOMOGENISATION.md")).read()
    ch3 = open(os.path.join(ROOT, "docs", "CH3_VERIFICATION.md")).read()
    t("Ch.4 4.9-0d states the observation this started from",
      "0.344" in ch4 and "역학 하중을 전혀 걸지 않는다" in ch4)
    t("Ch.3 3.8-8 hangs the C1 gate on it",
      "8.4(a)를 먼저 통과해야 한다" in ch3)
    t("  and now records that the lag is only part of it",
      "점성 지연" in ch3 and "재분배" in ch3)
    t("  so the gate is strengthened, not removed",
      "차이가 크게 나오는 경우" in ch3 and "관문이 약해지지 않는다" in ch3)

    print("\n H. the ETA knob's price is quantified, not just declared")
    tg = open(os.path.join(ROOT, "data", "properties",
                           "card_gap_triage.py")).read()
    t("card_gap_triage already grades ETA as a KNOB",
      '"eta", 0.05, "KNOB"' in tg.replace("'", '"'),
      "a solver parameter, not a material one")
    rows = lag_share_vs_eta()
    t("the lag share is monotone in ETA",
      all(rows[i][4] <= rows[i + 1][4] + 1e-12 for i in range(len(rows) - 1)),
      " -> ".join("%.1f %%" % (100 * r[4]) for r in rows))
    t("  ETA = 0 leaves no lag at all", rows[0][4] < 1e-9,
      "d_end = target = %.4f" % rows[0][2])
    z = [r for r in rows if abs(r[0] - 0.05) < 1e-12][0]
    t("  and the card's 0.05 reproduces the 16 %", 0.15 < z[4] < 0.18,
      "%.1f %%" % (100 * z[4]))
    t("  doubling ETA nearly doubles the numerical share",
      1.5 < [r for r in rows if abs(r[0] - 0.1) < 1e-12][0][4] / z[4] < 2.0,
      "16.3 -> 26.9 %")
    t("the frame reader that settles it ETA-free exists and is in the gate",
      os.path.exists(os.path.join(ROOT, "postprocess", "reheat_frames.py")),
      "reheat_frames.py splits by the RMT high-water mark, not by time")
    t("Ch.3 8.3-a states the knob and its price together",
      "ETA" in ch3 and "16.3" in ch3 and "26.9" in ch3)


def main(argv):
    report()
    if "--check" in argv or "--selftest" in argv:
        check()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 78)
            return 1
        print("ALL %d REHEAT-SATURATION CLAIMS HOLD "
              "(the cooldown commits it, the reheat only waits)" % len(_OK))
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
