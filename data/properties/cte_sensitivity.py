#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cte_sensitivity.py
==================
How much of the 2.34x thermal-residual-stress over-prediction is the fibre CTE?

check_card_ranges.py found that BOTH fibre CTEs on the card sit outside the
range independent measurements report:

    axial       card -0.3e-6/K   vs  Pradere refs/[07] 1.6-2.1e-6 (mean to
                                     2500 K), our own PANEX 33 secant +1.237e-6,
                                     and Yan refs/[35] 1.0e-6 -- three
                                     independent sources, all POSITIVE
    transverse  card  3.1e-6/K   vs  Pradere refs/[07] 5-10e-6, our PANEX 33
                                     secant 5.630e-6 -- the card is BELOW the
                                     measured band

Both deviations lower the composite CTE, which raises the matrix TRS -- the
same direction as the over-prediction already on record.  That is a coincidence
worth pricing before another RVE job is queued, because the project has so far
blamed the whole 2.34x on the stress-free temperature.

WHAT THIS SCRIPT DOES NOT DO.  It does not predict the matrix TRS.  The TRS is
driven by (alpha_composite - alpha_matrix), a difference between two numbers
that agree to within 20 %, so a mean-field model with a 17 % error in
alpha_composite has a ~100 % error in the TRS.  Any absolute mean-field TRS
here would be worthless.

WHAT IT DOES.  It transfers the CHANGE.  The RVE has already measured the
absolute anchor (alpha_xx = 3.132e-6/K, matrix TRS = 268.08 MPa, Ch.4 4.5).
The mean field is used only to compute d(alpha_composite)/d(alpha_fibre), a
DIFFERENCE between two mean-field evaluations in which the systematic model
error cancels to first order.  Two independent transfer routes are reported
and their spread is quoted as the uncertainty:

    route A  keep the RVE's absolute CTE mismatch, shift it by the mean-field
             delta:      sigma = 268.08 * |mismatch_RVE + d_alpha| / |mismatch_RVE|
    route B  scale the whole mean field by one constant kappa calibrated so
             the card case reproduces 268.08 MPa

Run:  python3 data/properties/cte_sensitivity.py
      python3 data/properties/cte_sensitivity.py --check
"""
from __future__ import print_function

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eval_correlations as ec          # noqa: E402

# --------------------------------------------------------------------------
# Constituents -- Zhang 2022 Tables 1 and 2, identical to micromech_check.py
# --------------------------------------------------------------------------
EF1, EF2, GF12, GF23, NUF12 = 230.0e3, 40.0e3, 24.0e3, 14.3e3, 0.26
EM, NUM = 350.0e3, 0.20
GM = EM / (2.0 * (1.0 + NUM))
AM_CARD = 4.5e-6                       # matrix secant CTE, 1050 -> 23 C

# Yarn card, as written in the .inp -- used only to recover Vf, exactly the
# way micromech_check.py does, so the two scripts cannot drift apart.
CARD_E1 = 254967.228042
CARD_A1 = 1.070925962822e-06
CARD_A2 = 3.324908565604e-06

VF_YARN = (EM - CARD_E1) / (EM - EF1)  # fibre fraction INSIDE a yarn, 0.79194
VY_RVE = 0.4982                        # yarn fraction of the RVE (Ch.4 4.1)

# --------------------------------------------------------------------------
# RVE anchors -- MEASURED, from the M3 cooldown (Ch.4 4.5.1 / 4.5.3)
# --------------------------------------------------------------------------
RVE_ALPHA_XX = 3.132e-6                # /K, secant 1050 -> 23 C, damaged
# The same quantity from the direct undamaged probe (a2-0026, ELAS+CTE run).
# The mean field below is itself undamaged, so THIS is the number it must be
# compared against; measuring a mean-field estimate against the damaged secant
# charged the mean field for microcracks it does not model (17.5 % instead of
# the true 12.1 %).  RVE_ALPHA_XX stays the anchor for the TRS transfer, where
# the damaged state is the right one.  Verdict: data/literature/cte_rve_verdict.py
RVE_ALPHA_XX_UNDAMAGED = 3.2827e-6     # /K, direct probe, damage OFF
RVE_TRS = 268.08                       # MPa, volume-averaged matrix sigma_11
XRD_TRS = 114.7                        # MPa, refs/[15] 3D braided, XRD
T_ROOM = 23.0
T_SF_DECK = 1050.0                     # what the deck ships with

# --------------------------------------------------------------------------
# Fibre CTE variants.  (label, axial, transverse, grade, source)
# `None` for the pair means "evaluate the Pradere polynomial as a secant about
# whatever stress-free temperature is being tested" -- see fibre_cte().
# --------------------------------------------------------------------------
VARIANTS = [
    ("CARD", -0.3e-6, 3.1e-6, "T300 (Zhang 2022 Table 1)",
     "the value the RVE card was verified against"),
    # PROVENANCE OF THE TRANSVERSE NUMBERS (2026-08-12).  refs/[07]'s transverse
    # CTEs are not a direct measurement.  The companion paper that produced them
    # is titled "ESTIMATION of the transverse coefficient of thermal expansion on
    # carbon fibers at very high temperature" and appeared in Inverse Problems in
    # Science and Engineering 15 (1) (2007) 77-89 -- an inverse identification,
    # not a dilatometer reading.  The 5-10e-6 band also mixes rayon-, PAN- and
    # pitch-based fibres over 300-2500 K.  An in-situ TEM study measured PAN
    # fibres over 20-1100 C, our own range, and reports a much tighter 3.8-5.6e-6
    # (candidate N1, docs/LIT_FIBRE_TRANSVERSE_CTE.md).  Both are search-verified
    # only; no PDF is held, so nothing here is changed on their account.  Do not
    # call the 5-10 band "measured" in the manuscript -- call it identified.
    ("PANEX33", None, None, "PANEX 33 ex-PAN, E = 230 GPa",
     "Pradere & Sauder refs/[07] Tables 3/4, evaluated as a secant"),
    ("HTA5131", None, None, "HTA 5131 ex-PAN, E = 248 GPa",
     "Pradere & Sauder refs/[07] Tables 3/4, the sensitivity alternative"),
    ("PRADERE_LO", 1.6e-6, 5.0e-6, "carbon fibre, low end of the band",
     "refs/[07] abstract: axial mean 1.6-2.1e-6, transverse 5-10e-6"),
    ("PRADERE_HI", 2.1e-6, 10.0e-6, "carbon fibre, high end of the band",
     "refs/[07] abstract: axial mean 1.6-2.1e-6, transverse 5-10e-6"),
    ("YAN2011", 1.0e-6, 3.1e-6, "2D C/SiC CVI, their Eq. 2",
     "refs/[35] Section 3.2 -- axial only; transverse left at the card value"),
]

POLY = {"PANEX33": (ec.PANEX33_LONG, ec.PANEX33_TRANS),
        "HTA5131": (ec.HTA5131_LONG, ec.HTA5131_TRANS)}


def fibre_cte(name, axial, trans, t_sf):
    """Fibre CTEs for one variant at one stress-free temperature.

    A constant pair is temperature-independent by construction -- that is what
    a single tabulated room-temperature number means, and it is what the deck
    would carry if the card values were entered directly.  The polynomial
    variants are evaluated as a true secant from t_sf down to room temperature,
    which is the only CTE definition that is consistent with how Abaqus applies
    `*Expansion, zero=`.
    """
    if axial is not None:
        return axial, trans
    lng, tr = POLY[name]
    a1 = ec.secant_alpha(T_ROOM, lambda t: ec.fibre_strain(t, lng), t_sf)
    a2 = ec.secant_alpha(T_ROOM, lambda t: ec.fibre_strain(t, tr), t_sf)
    return a1, a2


def matrix_cte(t_sf):
    """Matrix secant CTE from t_sf to room temperature.

    Anchored the same way eval_correlations.matrix_row does: the temperature
    SHAPE comes from Snead's integral, the absolute value from the verified
    card, so that t_sf = 1050 C returns exactly AM_CARD.
    """
    a = ec.secant_alpha(T_ROOM, ec.sic_alpha_integral, t_sf)
    return a + (AM_CARD - ec.secant_alpha(T_ROOM, ec.sic_alpha_integral,
                                          T_SF_DECK))


def yarn_cte(af1, af2, am, vf=VF_YARN):
    """Schapery yarn CTEs -- the same two lines as micromech_check.py."""
    sq = math.sqrt(vf)
    vm = 1.0 - vf
    a1 = (vf * EF1 * af1 + vm * EM * am) / (vf * EF1 + vm * EM)
    a2 = sq * af2 + (1.0 - sq) * ((1.0 + NUM) * am - a1 * NUM)
    return a1, a2


def yarn_stiffness(vf=VF_YARN):
    """Chamis in-plane yarn constants.  Temperature-independent here: the
    weave average below is a stiffness-WEIGHTED average, and the weights move
    by only a few percent over the cooldown while the CTEs move by tens."""
    sq = math.sqrt(vf)
    vm = 1.0 - vf
    e1 = vf * EF1 + vm * EM
    e2 = EM / (1.0 - sq * (1.0 - EM / EF2))
    nu12 = vf * NUF12 + vm * NUM
    return e1, e2, nu12


def weave_alpha(a1, a2, am, vy=VY_RVE):
    """In-plane CTE of the 2D plain weave by a cross-ply laminate analogy.

    Half the yarns run in x and half in y; the interstitial matrix is the
    balance.  All phases are forced to the same in-plane strain (the Voigt
    assumption for in-plane loading), and the in-plane force resultant of the
    free thermal expansion must vanish:

        alpha_bar = sum_i V_i (Q11_i a_x,i + Q12_i a_y,i)
                    / sum_i V_i (Q11_i + Q12_i)

    This IGNORES tow undulation, which is exactly why the absolute value is
    not used -- only its derivative with respect to the fibre CTE is.
    """
    e1, e2, nu12 = yarn_stiffness()
    nu21 = nu12 * e2 / e1
    den = 1.0 - nu12 * nu21
    q11, q22, q12 = e1 / den, e2 / den, nu12 * e2 / den
    mq = EM / (1.0 - NUM * NUM)
    mq11, mq12 = mq, NUM * mq

    top = (vy / 2.0) * (q11 * a1 + q12 * a2) \
        + (vy / 2.0) * (q22 * a2 + q12 * a1) \
        + (1.0 - vy) * (mq11 * am + mq12 * am)
    bot = (vy / 2.0) * (q11 + q12) \
        + (vy / 2.0) * (q22 + q12) \
        + (1.0 - vy) * (mq11 + mq12)
    return top / bot


def mean_field_trs(alpha_bar, am, t_sf):
    """Uncalibrated mean-field matrix TRS, biaxial in-plane.

    The measured matrix state is sigma_11 = sigma_22 = 268.08 with
    sigma_33 = 35.94 (Ch.4 4.5.1), i.e. very nearly equibiaxial, so the
    biaxial modulus E/(1-nu) is the right one.  Absolute value NOT used.
    """
    return EM / (1.0 - NUM) * (alpha_bar - am) * (T_ROOM - t_sf)


def evaluate(name, axial, trans, t_sf=T_SF_DECK):
    af1, af2 = fibre_cte(name, axial, trans, t_sf)
    am = matrix_cte(t_sf)
    a1, a2 = yarn_cte(af1, af2, am)
    ab = weave_alpha(a1, a2, am)
    return dict(name=name, af1=af1, af2=af2, am=am, ya1=a1, ya2=a2,
                alpha_bar=ab, sigma_mf=mean_field_trs(ab, am, t_sf))


def transfer(base, var):
    """Both transfer routes, returning (route_A, route_B, kappa).

    Route A keeps the RVE's measured mismatch and shifts it by the mean-field
    delta.  Route B rescales the mean field by one constant.  They answer the
    same question through different error paths; the spread is the honest bar.
    """
    mismatch_rve = RVE_ALPHA_XX - base["am"]        # negative
    d_alpha = var["alpha_bar"] - base["alpha_bar"]
    a = RVE_TRS * abs(mismatch_rve + d_alpha) / abs(mismatch_rve)
    kappa = RVE_TRS / base["sigma_mf"]
    b = kappa * var["sigma_mf"]
    return a, b, kappa


def effective_t_sf(name, axial, trans, target=XRD_TRS, lo=100.0,
                   hi=T_SF_DECK):
    """Stress-free temperature at which this CTE set reproduces the XRD value.

    Bisected on route B, which is the only one defined away from the anchor
    point (route A's delta is referenced to the card case at 1050 C).

    The upper bracket is the 1050 C pyrolysis temperature, not an arbitrary
    number: the material has no stress above the temperature at which it was
    formed, so a root beyond 1050 C would be unphysical.  `None` therefore
    means "this CTE set cannot reach the XRD value at any admissible
    stress-free temperature", which is a result, not a failure.

    NOTE ON THE MATRIX CTE.  alpha_m here is a TRUE SECANT recomputed about
    each trial t_sf, so lowering t_sf lowers alpha_m (Snead's instantaneous
    CTE rises with temperature, so a shorter range averages lower).  The
    mismatch therefore SHRINKS as t_sf falls, on top of the shrinking dT, and
    the TRS drops faster than linearly.  An earlier undocumented sweep in
    Ch.4 4.5.2 (1050->302, 800->270, 600->233, 307->114.7) falls SLOWER than
    linear, which is only possible if the CTE table stayed referenced to
    1050 C while `zero=` moved.  That is the trap build_temperature_tables.py
    exists to prevent: there a single T0 drives both `zero=T0` and
    to_secant_about(..., T0), so the two cannot disagree.  It only bites if
    `zero=` is hand-edited in a deck without regenerating the tables.  The two
    sweeps cannot both be right, and this is the one that can be re-run.
    """
    base = evaluate("CARD", -0.3e-6, 3.1e-6, T_SF_DECK)
    kappa = RVE_TRS / base["sigma_mf"]

    def f(t):
        return kappa * evaluate(name, axial, trans, t)["sigma_mf"] - target

    if f(lo) * f(hi) > 0.0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ==========================================================================
def report():
    print("=" * 78)
    print("cte_sensitivity.py -- how much of the 2.34x TRS excess is the")
    print("                      fibre CTE, and how much is the stress-free")
    print("                      temperature?")
    print("=" * 78)

    base = evaluate("CARD", -0.3e-6, 3.1e-6, T_SF_DECK)

    print("\n 1. FIBRE -> YARN -> WEAVE, all at the shipped T_sf = 1050 C")
    print("    %-11s %10s %10s | %10s %10s | %10s"
          % ("variant", "a_f axial", "a_f trans", "a_y axial", "a_y trans",
             "alpha_bar"))
    print("    " + "-" * 70)
    rows = []
    for name, ax, tr, grade, src in VARIANTS:
        r = evaluate(name, ax, tr, T_SF_DECK)
        rows.append((r, grade, src))
        print("    %-11s %10.3e %10.3e | %10.3e %10.3e | %10.3e"
              % (name, r["af1"], r["af2"], r["ya1"], r["ya2"], r["alpha_bar"]))
    print("    " + "-" * 70)
    print("    RVE measured alpha_xx (damaged secant, Ch.4 4.5.3): %10.3e"
          % RVE_ALPHA_XX)
    print("    RVE direct probe alpha_in (undamaged, a2-0026)    : %10.3e"
          % RVE_ALPHA_XX_UNDAMAGED)
    print("    matrix alpha at this T_sf                         : %10.3e"
          % base["am"])
    print("\n    The mean field puts alpha_bar %.1f %% above the RVE for the"
          % ((base["alpha_bar"] / RVE_ALPHA_XX_UNDAMAGED - 1.0) * 100.0))
    print("    card case -- compared like for like, undamaged against")
    print("    undamaged.  That is why only its DERIVATIVE is used below.")

    print("\n 2. MATRIX TRS, transferred onto the RVE measurement")
    print("    %-11s %9s %9s %9s | %8s  %s"
          % ("variant", "route A", "route B", "band", "vs XRD", "note"))
    print("    " + "-" * 70)
    for r, grade, src in rows:
        a, b, kappa = transfer(base, r)
        lo, hi = min(a, b), max(a, b)
        print("    %-11s %9.1f %9.1f %4.0f-%4.0f | %4.2f-%4.2fx  %s"
              % (r["name"], a, b, lo, hi, lo / XRD_TRS, hi / XRD_TRS, grade))
    print("    " + "-" * 70)
    print("    RVE measured %.2f MPa = %.2fx the XRD %.1f MPa"
          % (RVE_TRS, RVE_TRS / XRD_TRS, XRD_TRS))
    print("    kappa (route B calibration constant) = %.4f"
          % transfer(base, base)[2])

    print("\n 3. TRS vs STRESS-FREE TEMPERATURE, consistent secants "
          "(supersedes the\n    undocumented sweep in Ch.4 4.5.2 -- see "
          "effective_t_sf.__doc__)")
    sweep = [1050.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0]
    kappa = transfer(base, base)[2]
    print("    %8s %11s %11s %11s %10s"
          % ("T_sf [C]", "alpha_m", "alpha_bar", "mismatch", "TRS [MPa]"))
    print("    " + "-" * 58)
    for t in sweep:
        r = evaluate("CARD", -0.3e-6, 3.1e-6, t)
        print("    %8.0f %11.4e %11.4e %11.4e %10.1f"
              % (t, r["am"], r["alpha_bar"], r["alpha_bar"] - r["am"],
                 kappa * r["sigma_mf"]))
    print("    " + "-" * 58)

    print("\n 4. EFFECTIVE STRESS-FREE TEMPERATURE that reproduces the XRD")
    print("    %-11s %14s   %s" % ("variant", "T_sf [C]", "plausible?"))
    print("    " + "-" * 70)
    for name, ax, tr, grade, src in VARIANTS:
        t = effective_t_sf(name, ax, tr)
        if t is None:
            print("    %-11s %14s   %s"
                  % (name, "none <= 1050",
                     "already BELOW the XRD value at the process temperature"))
            continue
        # SiC creep and interface adjustment are credible over roughly
        # 600-1000 C.  Below ~500 C there is no mechanism that relaxes SiC,
        # so a root down there says the CTE set, not the temperature, is wrong.
        verdict = ("yes -- creep/interface relaxation range" if t >= 600.0
                   else "marginal -- at the bottom edge of any mechanism")
        print("    %-11s %14.0f   %s" % (name, t, verdict))
    print("    " + "-" * 70)

    print("\n 5. WHAT THIS MEANS")
    pan = [r for r, _, _ in rows if r["name"] == "PANEX33"][0]
    a, b, _ = transfer(base, pan)
    lo, hi = min(a, b), max(a, b)
    share_lo = (RVE_TRS - hi) / (RVE_TRS - XRD_TRS) * 100.0
    share_hi = (RVE_TRS - lo) / (RVE_TRS - XRD_TRS) * 100.0
    print("    Swapping the card's fibre CTE for the measured PANEX 33 secant")
    print("    moves the matrix TRS from %.1f to %.0f-%.0f MPa, which closes"
          % (RVE_TRS, lo, hi))
    print("    %.0f-%.0f %% of the gap to the XRD value." % (share_lo, share_hi))
    print("    The stress-free temperature is therefore NOT the whole story,")
    print("    and it is not innocent either -- it still has to supply the")
    print("    rest.  The two effects are of the same order.")
    print("=" * 78)


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("=" * 78)
    print("cte_sensitivity.py --check")
    print("=" * 78)

    print("\n A. the micromechanics reproduces the shipped yarn card")
    ck("Vf recovered from E1 is 0.79194",
       abs(VF_YARN - 0.79194) < 1.0e-5, "%.6f" % VF_YARN)
    a1, a2 = yarn_cte(-0.3e-6, 3.1e-6, AM_CARD)
    ck("yarn axial CTE reproduces the card 1.0709e-6",
       abs(a1 - CARD_A1) / CARD_A1 < 1.0e-4, "%.6e" % a1)
    ck("yarn transverse CTE reproduces the card 3.3249e-6",
       abs(a2 - CARD_A2) / CARD_A2 < 5.0e-3, "%.6e" % a2)
    e1, e2, nu12 = yarn_stiffness()
    ck("yarn E1 reproduces the card 254967",
       abs(e1 - CARD_E1) / CARD_E1 < 1.0e-6, "%.3f" % e1)

    print("\n B. the matrix CTE anchor is exact at the shipped T_sf")
    ck("matrix_cte(1050) == 4.5e-6 exactly",
       abs(matrix_cte(T_SF_DECK) - AM_CARD) < 1.0e-15,
       "%.8e" % matrix_cte(T_SF_DECK))
    ck("matrix CTE falls as the range shrinks (Snead alpha rises with T)",
       matrix_cte(600.0) < matrix_cte(T_SF_DECK),
       "%.3e < %.3e" % (matrix_cte(600.0), matrix_cte(T_SF_DECK)))

    print("\n C. the fibre secants match eval_correlations")
    for nm, ex1, ex2 in (("PANEX33", 1.2367e-6, 5.6298e-6),
                         ("HTA5131", 0.96567e-6, 6.8024e-6)):
        f1, f2 = fibre_cte(nm, None, None, T_SF_DECK)
        ck("%s axial secant 1050->23 is %.4e" % (nm, ex1),
           abs(f1 - ex1) / ex1 < 1.0e-3, "%.4e" % f1)
        ck("%s transverse secant 1050->23 is %.4e" % (nm, ex2),
           abs(f2 - ex2) / ex2 < 1.0e-3, "%.4e" % f2)
    ck("a constant variant ignores T_sf",
       fibre_cte("CARD", -0.3e-6, 3.1e-6, 600.0) == (-0.3e-6, 3.1e-6))

    print("\n D. every independent source disagrees with the card in the "
          "SAME direction")
    card = evaluate("CARD", -0.3e-6, 3.1e-6)
    for name, ax, tr, _, _ in VARIANTS:
        if name == "CARD":
            continue
        r = evaluate(name, ax, tr)
        ck("%s raises alpha_bar above the card" % name,
           r["alpha_bar"] > card["alpha_bar"],
           "%.4e vs %.4e" % (r["alpha_bar"], card["alpha_bar"]))
        ck("%s axial fibre CTE is positive, card is negative" % name,
           r["af1"] > 0.0 > card["af1"], "%.3e" % r["af1"])

    print("\n E. the transfer is anchored, not invented")
    a, b, kappa = transfer(card, card)
    ck("route A returns the measurement exactly for the card case",
       abs(a - RVE_TRS) < 1.0e-9, "%.4f" % a)
    ck("route B returns the measurement exactly for the card case",
       abs(b - RVE_TRS) < 1.0e-9, "%.4f" % b)
    ck("kappa is a reduction, not an amplification",
       0.5 < kappa < 1.0, "%.4f" % kappa)

    print("\n F. every variant LOWERS the TRS, and none reaches the XRD value")
    for name, ax, tr, _, _ in VARIANTS:
        if name == "CARD":
            continue
        r = evaluate(name, ax, tr)
        a, b, _ = transfer(card, r)
        ck("%s lowers the matrix TRS" % name,
           max(a, b) < RVE_TRS, "%.1f / %.1f MPa" % (a, b))
    pan = evaluate("PANEX33", None, None)
    a, b, _ = transfer(card, pan)
    ck("PANEX33 alone does NOT close the gap to the XRD value",
       min(a, b) > XRD_TRS,
       "%.1f MPa vs %.1f" % (min(a, b), XRD_TRS))
    ck("PANEX33 closes between a quarter and two thirds of the gap",
       0.25 < (RVE_TRS - max(a, b)) / (RVE_TRS - XRD_TRS) < 0.70,
       "%.0f-%.0f %%" % ((RVE_TRS - max(a, b)) / (RVE_TRS - XRD_TRS) * 100.0,
                         (RVE_TRS - min(a, b)) / (RVE_TRS - XRD_TRS) * 100.0))

    print("\n G. the stress-free temperature each CTE set demands")
    t_card = effective_t_sf("CARD", -0.3e-6, 3.1e-6)
    ck("the card needs T_sf at the bottom edge of any relaxation mechanism",
       t_card is not None and 450.0 < t_card < 600.0, "%.0f C" % t_card)
    t_pan = effective_t_sf("PANEX33", None, None)
    ck("the measured CTE needs a HIGHER, more comfortable T_sf",
       t_pan is not None and t_pan > t_card, "%.0f C vs %.0f" % (t_pan, t_card))
    ck("and that temperature is in the creep/relaxation range",
       600.0 <= t_pan <= 900.0, "%.0f C" % t_pan)
    ck("every root stays at or below the 1050 C process temperature",
       all(t is None or t <= T_SF_DECK
           for t in (effective_t_sf(n, a, b) for n, a, b, _, _ in VARIANTS)))
    ck("the top of the Pradere band overshoots -- no admissible T_sf",
       effective_t_sf("PRADERE_HI", 2.1e-6, 10.0e-6) is None,
       "already below 114.7 MPa at 1050 C")

    print("\n G2. the sweep is monotonic and falls FASTER than linear in dT")
    kappa = transfer(card, card)[2]
    prev, prev_lin = None, None
    for t in (1050.0, 900.0, 800.0, 700.0, 600.0, 500.0):
        s = kappa * evaluate("CARD", -0.3e-6, 3.1e-6, t)["sigma_mf"]
        lin = RVE_TRS * (t - T_ROOM) / (T_SF_DECK - T_ROOM)
        if prev is not None:
            ck("TRS falls as T_sf drops (%.0f C)" % t, s < prev,
               "%.1f < %.1f" % (s, prev))
        ck("TRS at %.0f C is below the linear extrapolation" % t,
           t == T_SF_DECK or s < lin, "%.1f vs %.1f linear" % (s, lin))
        prev, prev_lin = s, lin

    print("\n H. the model's own limits are stated, not hidden")
    src = open(os.path.join(HERE, "cte_sensitivity.py")).read()
    for phrase, why in (
            ("does not predict", "must disclaim absolute prediction"),
            ("IGNORES tow undulation", "must disclaim the weave model"),
            ("cancels to first order", "must state why a delta is used"),
            ("spread is the honest bar", "must state the uncertainty rule")):
        ck("source states: %s" % why, phrase in src)
    ck("alpha_bar error vs the RVE is reported, not buried",
       "above the RVE for the" in src)
    ck("the mean field is compared undamaged-to-undamaged",
       "RVE_ALPHA_XX_UNDAMAGED - 1.0" in src,
       "%.1f %% high" % ((card["alpha_bar"] / RVE_ALPHA_XX_UNDAMAGED - 1) * 100))
    ck("and the damaged anchor is kept for the TRS transfer",
       "RVE_ALPHA_XX - base" in src or "RVE_ALPHA_XX -" in src)

    print("\n I. the numbers Ch.4 will quote")
    r = evaluate("PANEX33", None, None)
    a, b, _ = transfer(card, r)
    ck("card alpha_bar is 3.68e-6", abs(card["alpha_bar"] - 3.68e-6) < 0.01e-6,
       "%.4e" % card["alpha_bar"])
    ck("PANEX33 alpha_bar is 4.03e-6", abs(r["alpha_bar"] - 4.03e-6) < 0.01e-6,
       "%.4e" % r["alpha_bar"])
    ck("route A gives 200 MPa", abs(a - 200.0) < 2.0, "%.1f" % a)
    ck("route B gives 154 MPa", abs(b - 154.0) < 2.0, "%.1f" % b)
    ck("the card's effective T_sf is 531 C", abs(t_card - 531.0) < 8.0,
       "%.0f" % t_card)
    ck("PANEX33's effective T_sf is 782 C", abs(t_pan - 782.0) < 8.0,
       "%.0f" % t_pan)
    ck("YAN2011 alone still leaves 1.75-1.99x",
       abs(min(transfer(card, evaluate("YAN2011", 1.0e-6, 3.1e-6))[:2])
           / XRD_TRS - 1.75) < 0.02)

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d CTE-SENSITIVITY CHECKS PASS" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    report()
