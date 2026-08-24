#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
insitu_yarn_strength.py
=======================
Where yarn Xt should come from, with a source for every number.

WHY THIS EXISTS
---------------
m6_calibration.py named yarn Xt = 2835 MPa as the knob with leverage: the
rule-of-mixtures bound it implies for the composite is 706 MPa, which is 3.5x
the Zhang Table 3 target and above every measured 2D C/SiC strength.  It
stopped there on purpose -- "the output is an ORDER and a LEVERAGE, not a
value".  Lowering Xt to whatever makes M6 land on 199.15 MPa would be fitting
a constituent card to a composite measurement, which this project forbids:
only constituent data goes in cards, composite measurements are validation.

So the replacement has to be derived from constituent data alone.  This does
that, and then checks the answer against the composite measurement WITHOUT
using it.

THE CHAIN, IN ONE PARAGRAPH
---------------------------
The card's 3580 MPa is a strand/datasheet figure.  refs/[08] (Sauder, Lamon,
Pailler, Compos. Sci. Technol. 62 (2002) 499) measured T300 single filaments
directly at temperature, and Table 1 reports BOTH the mean strength sigma_R
at a 50 mm gauge AND the Weibull parameters (m, sigma_0 at V_0 = 1 mm^3).
Those two columns are mutually consistent to 2 % (checked below), so the
statistics are usable.  The stressed fibre volume in our RVE's load-aligned
yarns is 1.063 mm^3 -- within 6 % of Sauder's own reference volume -- so
sigma_0 transfers with a 1.2 % size correction and no extrapolation.
refs/[10] (Yang et al., J. Eur. Ceram. Soc. 37 (2017) 1281) independently
made the same choice: its Table 2 fibre strength column IS Sauder's sigma_0.

THE RESULT
----------
Xt should be about 474 MPa at 23 C rising to 696 MPa at 1000 C, not a flat
2835.  The temperature SHAPE matters as much as the anchor: sigma_R rises
9 % from RT to 1000 C, sigma_0 rises 44 %, and the measured composite
strength rises 55 %.  The card currently uses the sigma_R shape, which
cannot account for what is measured; the sigma_0 shape nearly can.

  python3 data/properties/insitu_yarn_strength.py
  python3 data/properties/insitu_yarn_strength.py --check
"""
from __future__ import print_function

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- geometry
#: RVE bounding box volume [mm^3].  postprocess/driver_audit.py, retune_deck.py
V_RVE = 5.390
#: yarn volume fraction of the RVE, from the mesh (Ch.4 4.6)
VY_RVE = 0.4982
#: fibre volume fraction INSIDE a yarn, recovered from E1 (micromech_check.py)
VF_YARN = 0.79194

#: T300 filament radius [mm].  refs/[10] Yang Table 3: r = 3.5 um
R_FIBRE = 3.5e-3
#: Sauder's gauge length [mm].  refs/[08] section 2: "Gauge length was 50 mm"
GAUGE = 50.0
#: Sauder's Weibull reference volume [mm^3].  refs/[08] Table 1 footnote a
V0_SAUDER = 1.0

# ------------------------------------------------------------ the card now
CARD_XT = 2835.0            # = VF_YARN * 3580
CARD_FIBRE_XT = 3580.0      # Zhang 2022 Table 1 / Ge 2018 Table 2, a STRAND value
TORAY_T300 = 3530.0         # Toray datasheet, also a strand value

# ------------------------------------------------- the calibration targets
#: Zhang 2022 Table 3, composite tensile strength [MPa].  VALIDATION ONLY.
ZHANG_TABLE3 = [(23.0, 128.45), (500.0, 179.42), (1000.0, 199.15)]


# ==========================================================================
def sauder_table():
    """refs/[08] Sauder, Lamon & Pailler (2002) Table 1, PAN-based fibre.

    (T [C], E/E0 [%], sigma_R [MPa], eps_R [%], m, sigma_0 [MPa] at 1 mm^3)

    sigma_R is the MEAN of the measured single-filament strengths at the
    50 mm gauge; sigma_0 is the Weibull scale parameter normalised to a 1 mm^3
    reference volume.  They are different quantities and the difference is the
    entire point of this file.  Grade: fulltext.
    """
    return [
        (  24.0, 100.0, 2107.0, 0.71, 5.1,  660.0),
        (1000.0,  98.5, 2292.0, 0.80, 6.5,  950.0),
        (1200.0,  97.7, 2401.0, 0.86, 5.2,  890.0),
        (1400.0,  95.7, 2386.0, 0.85, 5.4,  810.0),
        (1600.0,  91.6, 2359.0, 0.91, 5.4,  800.0),
        (1800.0,  81.8, 2857.0, 1.53, 5.6, 1020.0),
        (2000.0,  69.5, 2348.0, 3.71, 5.9,  850.0),
    ]


def yang_table2():
    """refs/[10] Yang et al. (2017) Table 2.

    (T [K], matrix strength [MPa], Weibull m, statistical strength [MPa],
     tested composite UTS [MPa], predicted composite UTS [MPa])

    Two things to notice.  The matrix strength column is 310 MPa, which is
    EXACTLY our card's matrix Xt -- an independent confirmation we did not
    have.  And the statistical strength column is Sauder's sigma_0, reused
    verbatim (1273 K = 1000 C -> 950, 1473 K = 1200 C -> 890, 300 K -> 660,
    973 K linearly interpolated to 860).  Grade: fulltext.
    """
    return [
        ( 300.0, 310.0, 5.1, 660.0, 225.8, 241.5),
        ( 973.0, 310.0, 6.5, 860.0, 240.5, 272.3),
        (1273.0, 310.0, 6.5, 950.0, 268.2, 294.1),
        (1473.0, 310.0, 5.2, 890.0, 240.9, 320.3),
    ]


# ------------------------------------------------------------- Weibull kit
def filament_volume(gauge=GAUGE, r=R_FIBRE):
    """Stressed volume of one filament in Sauder's rig [mm^3]."""
    return math.pi * r * r * gauge


def aligned_fibre_volume():
    """Stressed fibre volume in the load-aligned yarns of one RVE [mm^3].

    Half the yarns carry an on-axis pull; the other half are transverse.
    This is the volume that decides the composite's tensile strength, so it
    is the volume at which the fibre strength has to be quoted.
    """
    return 0.5 * VY_RVE * V_RVE * VF_YARN


def weibull_scale_at(sig0, m, vol, v0=V0_SAUDER):
    """Weibull scale parameter transferred from v0 to vol.

    sigma_0(V) = sigma_0(V_0) * (V_0/V)^(1/m).  This is the stress at which
    63.2 % of specimens of volume V have failed.
    """
    return sig0 * (v0 / vol) ** (1.0 / m)


def weibull_mean_at(sig0, m, vol, v0=V0_SAUDER):
    """Mean strength of a specimen of volume vol.

    mean = sigma_0(V) * Gamma(1 + 1/m).  For m ~ 5-6 the gamma factor is
    about 0.92, so the mean sits ~8 % below the scale parameter.
    """
    return weibull_scale_at(sig0, m, vol, v0) * math.gamma(1.0 + 1.0 / m)


def daniels_bundle_at(sig0, m, vol, v0=V0_SAUDER):
    """Dry-bundle strength (Daniels): sigma_0(V) * (m*e)^(-1/m).

    A LOWER bound for our yarn, because a dry bundle has no matrix to
    redistribute the load off a broken filament.  Our yarn does, so the
    truth is above this.
    """
    return weibull_scale_at(sig0, m, vol, v0) * (m * math.e) ** (-1.0 / m)


def interp_sauder(T):
    """(m, sigma_0) at temperature T, linearly interpolated in T.

    Linear interpolation is not a modelling choice here -- it is what
    refs/[10] did.  Yang's 973 K row (m = 6.5, sigma_0 = 860) is exactly the
    linear interpolate of Sauder's 24 C and 1000 C rows at 700 C, which is
    how we know that is the rule Yang used.
    """
    tab = [(r[0], r[4], r[5]) for r in sauder_table()]
    if T <= tab[0][0]:
        return tab[0][1], tab[0][2]
    if T >= tab[-1][0]:
        return tab[-1][1], tab[-1][2]
    for i in range(len(tab) - 1):
        a, b = tab[i], tab[i + 1]
        if a[0] <= T <= b[0]:
            w = (T - a[0]) / (b[0] - a[0])
            return a[1] + w * (b[1] - a[1]), a[2] + w * (b[2] - a[2])
    return tab[-1][1], tab[-1][2]


def interp_sigma_r(T):
    """Mean measured filament strength sigma_R at temperature T [MPa]."""
    tab = [(r[0], r[2]) for r in sauder_table()]
    if T <= tab[0][0]:
        return tab[0][1]
    if T >= tab[-1][0]:
        return tab[-1][1]
    for i in range(len(tab) - 1):
        a, b = tab[i], tab[i + 1]
        if a[0] <= T <= b[0]:
            w = (T - a[0]) / (b[0] - a[0])
            return a[1] + w * (b[1] - a[1])
    return tab[-1][1]


# --------------------------------------------------------------- the routes
def routes(T):
    """Every defensible yarn Xt at temperature T, with its grade.

    Returns a list of (label, fibre stress [MPa], yarn Xt [MPa], admissible).
    'admissible' is False for anything that used a COMPOSITE measurement --
    those may be compared against, never typed into a card.
    """
    m, s0 = interp_sauder(T)
    va = aligned_fibre_volume()
    out = [
        ("CARD    strand datasheet", CARD_FIBRE_XT, VF_YARN * CARD_FIBRE_XT, True),
        ("FILAMENT Sauder sigma_R, 50 mm gauge",
         interp_sigma_r(T), VF_YARN * interp_sigma_r(T), True),
        ("SCALE   Weibull sigma_0 at the RVE volume",
         weibull_scale_at(s0, m, va), VF_YARN * weibull_scale_at(s0, m, va), True),
        ("MEAN    Weibull mean at the RVE volume",
         weibull_mean_at(s0, m, va), VF_YARN * weibull_mean_at(s0, m, va), True),
        ("BUNDLE  dry bundle, Daniels (floor)",
         daniels_bundle_at(s0, m, va), VF_YARN * daniels_bundle_at(s0, m, va), True),
    ]
    uts = target_uts(T)
    if uts is not None:
        xt = uts / (0.5 * VY_RVE)
        out.append(("BACKOUT from Zhang Table 3  <-- NOT ADMISSIBLE",
                    xt / VF_YARN, xt, False))
    return out


def rom_bound(xt):
    """Rule-of-mixtures upper bound on composite strength, as in
    m6_calibration.py: the load-aligned yarns are half the yarn volume."""
    return 0.5 * VY_RVE * xt


def target_uts(T):
    """Zhang Table 3 at T, linearly interpolated.  VALIDATION ONLY."""
    tab = ZHANG_TABLE3
    if T < tab[0][0] or T > tab[-1][0]:
        return None
    for i in range(len(tab) - 1):
        a, b = tab[i], tab[i + 1]
        if a[0] <= T <= b[0]:
            w = (T - a[0]) / (b[0] - a[0])
            return a[1] + w * (b[1] - a[1])
    return None


def admissible_band(T):
    """(low, high) yarn Xt at T from constituent data alone [MPa].

    Both ends are the same Weibull parameters at the same volume; they differ
    only in which statistic of that distribution a deterministic X_t should
    stand for -- the mean, or the scale parameter (the 63.2 % quantile).  The
    gamma factor separates them, so the band is only about 8 % wide.

    This is the whole point of the file: M6's yarn Xt is not a free knob but
    a bounded search over an 8 % interval, with both ends sourced.
    """
    m, s0 = interp_sauder(T)
    va = aligned_fibre_volume()
    return (VF_YARN * weibull_mean_at(s0, m, va),
            VF_YARN * weibull_scale_at(s0, m, va))


def recommended(T):
    """Where M6 should START inside that band: the low end, the Weibull mean.

    The rule-of-mixtures bound ignores the matrix and the transverse yarns
    completely, so it must sit STRICTLY below the measured composite strength
    -- if it does not, the card cannot reproduce the measurement no matter
    what the rest of the model does.  The mean end satisfies that at all three
    calibration temperatures.  The scale end does not: at 23 C its bound is
    128.6 MPa against a measured 128.45.

    That margin is 0.1 %, which is smaller than the uncertainty in either
    number, so this is not a claim that the scale end is wrong.  It is a
    reason to start at the end that cannot be wrong and walk up if M6
    under-predicts -- an 8 % walk, with the far end already sourced.
    """
    return admissible_band(T)[0]


# ==========================================================================
def report():
    print("=" * 78)
    print("insitu_yarn_strength.py -- where yarn Xt should come from")
    print("=" * 78)

    va = aligned_fibre_volume()
    vf1 = filament_volume()

    print("\n 1. THE SIZE EFFECT IS NOT AN ISSUE HERE, AND THAT IS THE POINT")
    print("    Sauder's Weibull reference volume V_0        %.3f mm^3" % V0_SAUDER)
    print("    one filament at his 50 mm gauge              %.4e mm^3" % vf1)
    print("    load-aligned fibre volume in ONE RVE         %.3f mm^3" % va)
    print("      = 0.5 x VY %.4f x V_RVE %.3f x VF_YARN %.5f"
          % (VY_RVE, V_RVE, VF_YARN))
    print("    -> the RVE volume is %.3fx Sauder's reference, so sigma_0"
          % (va / V0_SAUDER))
    m24, s24 = interp_sauder(24.0)
    corr = (V0_SAUDER / va) ** (1.0 / m24)
    print("       transfers with a %.1f %% correction, not an extrapolation."
          % (100.0 * (1.0 - corr)))

    print("\n 2. SAUDER'S TWO COLUMNS ARE MUTUALLY CONSISTENT")
    print("    %-8s %10s %10s %10s   %s"
          % ("T [C]", "m", "sig0", "predicted", "measured sig_R"))
    for T, _e, sr, _er, m, s0 in sauder_table():
        pred = weibull_mean_at(s0, m, vf1)
        print("    %-8.0f %10.1f %10.0f %10.0f   %6.0f   (%+.1f %%)"
              % (T, m, s0, pred, sr, 100.0 * (pred - sr) / sr))
    print("    predicted = sigma_0 (V_0/V)^(1/m) Gamma(1+1/m) at V = %.3e mm^3"
          % vf1)
    print("    -> six of seven rows agree to within 3.2 %, so the Weibull")
    print("       parameters can be used at another volume with confidence.")
    print("    !! THE 1200 C ROW DOES NOT.  m = 5.2 with sigma_0 = 890 predicts")
    print("       2726 MPa against a measured 2401, +13.5 %.  Every neighbour")
    print("       agrees, so this is that row, not the method -- most likely")
    print("       its m is misprinted (m = 6.0 would reconcile it).  We do not")
    print("       repair it: our calibration temperatures are 23/500/1000 C,")
    print("       which are bracketed by the 24 C and 1000 C rows and never")
    print("       touch 1200 C.  Flagged so nobody interpolates through it.")

    print("\n 3. WHAT THE CARD USES, AND WHAT WAS MEASURED")
    print("    card fibre Xt (strand/datasheet)      %7.0f MPa" % CARD_FIBRE_XT)
    print("    Toray T300 datasheet                  %7.0f MPa" % TORAY_T300)
    print("    Sauder MEASURED filament, 24 C        %7.0f MPa  (card is %.2fx)"
          % (2107.0, CARD_FIBRE_XT / 2107.0))
    print("    Sauder MEASURED filament, 1000 C      %7.0f MPa  (card is %.2fx)"
          % (2292.0, CARD_FIBRE_XT / 2292.0))
    print("    -> even the honest single-filament value is far below the card,")
    print("       and the in-situ value is far below that again.")

    print("\n 4. THE ROUTES, AT THE THREE CALIBRATION TEMPERATURES")
    for T, uts in ZHANG_TABLE3:
        print("\n    --- %.0f C  (Zhang Table 3: %.2f MPa) ---" % (T, uts))
        print("    %-44s %9s %9s %8s"
              % ("route", "fibre", "yarn Xt", "ROM"))
        for label, sf, xt, ok in routes(T):
            rb = rom_bound(xt)
            mark = "" if ok else "  <-- validation only"
            print("    %-44s %9.0f %9.0f %8.1f%s"
                  % (label, sf, xt, rb, mark))
        print("    %-44s %9s %9s %8.2f"
              % ("Zhang Table 3 measured", "", "", uts))

    print("\n 5. THE TWO INDEPENDENT ROUTES AGREE")
    print("    %-8s %12s %12s %10s" % ("T [C]", "constituent", "back-out", "gap"))
    for T, _ in ZHANG_TABLE3:
        a = recommended(T)
        b = target_uts(T) / (0.5 * VY_RVE)
        print("    %-8.0f %12.0f %12.0f %9.1f %%"
              % (T, a, b, 100.0 * (b - a) / b))
    print("    left  column: Sauder Weibull statistics only, no composite data")
    print("    right column: Zhang Table 3 divided by the aligned yarn volume")
    print("    They were derived without reference to each other.  The left one")
    print("    is what may go in the card; the right one is then a CHECK.")

    print("\n 6. THE TEMPERATURE SHAPE, WHICH THE CARD ALSO HAS WRONG")
    r_sr = interp_sigma_r(1000.0) / interp_sigma_r(23.0)
    _m, s0a = interp_sauder(23.0)
    _m2, s0b = interp_sauder(1000.0)
    r_s0 = s0b / s0a
    r_uts = 199.15 / 128.45
    print("    sigma_R  (what the card scales by)   RT -> 1000 C  %+.0f %%"
          % (100.0 * (r_sr - 1.0)))
    print("    sigma_0  (Weibull scale)             RT -> 1000 C  %+.0f %%"
          % (100.0 * (r_s0 - 1.0)))
    print("    MEASURED composite strength          RT -> 1000 C  %+.0f %%"
          % (100.0 * (r_uts - 1.0)))
    print("    -> the card's shape cannot produce the measured rise; the")
    print("       Weibull-scale shape very nearly can, and the remainder is")
    print("       thermal residual stress relaxation, which the model has.")

    print("\n 7. WHAT M6 SHOULD USE -- A BOUNDED BAND, NOT A FREE KNOB")
    print("    %-8s %10s %10s %10s %9s %9s"
          % ("T [C]", "Xt now", "start", "walk-up to", "width", "factor"))
    for T, _ in ZHANG_TABLE3:
        lo, hi = admissible_band(T)
        print("    %-8.0f %10.0f %10.0f %10.0f %8.1f %% %8.2fx"
              % (T, CARD_XT, lo, hi, 100.0 * (hi - lo) / lo, CARD_XT / lo))
    print("    Both ends come from the same Sauder parameters at the same")
    print("    volume; they differ only in taking the mean or the 63.2 %")
    print("    quantile.  Start low -- the ROM bound must stay under the")
    print("    measurement -- and walk up at most 8 % if M6 under-predicts.")
    print("    Xc is NOT scaled with it.  refs/[42] (Ceram. Int. 44 (2018)")
    print("    14026) shows 2D C/SiC compressive failure is a 20-degree shear")
    print("    band with fibre-bundle kinking, not filament rupture, so the")
    print("    Weibull argument does not transfer.  Xc stays a GUESS knob.")
    print("=" * 78)


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("=" * 78)
    print("insitu_yarn_strength.py --check")
    print("=" * 78)

    print("\n A. the literature tables are transcribed as printed")
    s = dict((r[0], r) for r in sauder_table())
    ck("Sauder Table 1 has 7 temperatures", len(sauder_table()) == 7)
    ck("24 C row is sigma_R 2107, m 5.1, sigma_0 660",
       s[24.0][2] == 2107.0 and s[24.0][4] == 5.1 and s[24.0][5] == 660.0)
    ck("1000 C row is sigma_R 2292, m 6.5, sigma_0 950",
       s[1000.0][2] == 2292.0 and s[1000.0][4] == 6.5 and s[1000.0][5] == 950.0)
    ck("1200 C row is sigma_R 2401, m 5.2, sigma_0 890",
       s[1200.0][2] == 2401.0 and s[1200.0][4] == 5.2 and s[1200.0][5] == 890.0)
    ck("E/E0 falls monotonically above 1000 C",
       all(sauder_table()[i][1] > sauder_table()[i + 1][1]
           for i in range(1, 6)))
    y = yang_table2()
    ck("Yang Table 2 has 4 temperatures", len(y) == 4)
    ck("Yang's matrix strength column is constant at 310 MPa",
       all(r[1] == 310.0 for r in y))

    print("\n B. the two papers are the same chain, not two guesses")
    ck("Yang 300 K statistical strength = Sauder 24 C sigma_0",
       y[0][3] == s[24.0][5], "660")
    ck("Yang 1273 K = 1000 C, and its column = Sauder 1000 C sigma_0",
       abs(y[2][0] - 273.0 - 1000.0) < 1e-9 and y[2][3] == s[1000.0][5],
       "950")
    ck("Yang 1473 K = 1200 C, and its column = Sauder 1200 C sigma_0",
       abs(y[3][0] - 273.0 - 1200.0) < 1e-9 and y[3][3] == s[1200.0][5],
       "890")
    ck("Yang's Weibull moduli are Sauder's too",
       y[0][2] == s[24.0][4] and y[2][2] == s[1000.0][4]
       and y[3][2] == s[1200.0][4])
    _m, s0_700 = interp_sauder(700.0)
    ck("Yang's 973 K row is the LINEAR interpolate at 700 C",
       abs(s0_700 - y[1][3]) < 1.5, "%.1f vs 860" % s0_700)
    ck("Yang's matrix strength equals our card's matrix Xt",
       y[0][1] == 310.0, "independent confirmation of one card value")

    print("\n C. Sauder's own columns are mutually consistent")
    vf1 = filament_volume()
    ck("a 50 mm filament is about 1.9e-3 mm^3",
       abs(vf1 - 1.924e-3) / 1.924e-3 < 0.01, "%.4e mm^3" % vf1)
    # Six rows agree.  The 1200 C row does not, and pretending otherwise by
    # widening this tolerance to 15 % would bury the one row we must not use.
    worst, worst_at = -1.0, "nothing compared"
    for T, _e, sr, _er, m, s0 in sauder_table():
        if T == 1200.0:
            continue
        rel = abs(weibull_mean_at(s0, m, vf1) - sr) / sr
        if rel > worst:
            worst, worst_at = rel, "%.0f C" % T
    ck("sigma_0 reproduces sigma_R at every row EXCEPT 1200 C",
       worst >= 0.0 and worst < 0.04,
       "worst %.1f %% at %s" % (100.0 * worst, worst_at))
    dev = (weibull_mean_at(890.0, 5.2, vf1) - 2401.0) / 2401.0
    ck("the 1200 C row is the outlier, and is flagged not repaired",
       dev > 0.10, "%+.1f %%" % (100.0 * dev))
    ck("no calibration temperature interpolates through 1200 C",
       all(T <= 1000.0 for T, _u in ZHANG_TABLE3), "23 / 500 / 1000 C")
    ck("the 24 C and 1000 C rows -- the ones we use -- agree within 2 %",
       abs(weibull_mean_at(660.0, 5.1, vf1) - 2107.0) / 2107.0 < 0.02
       and abs(weibull_mean_at(950.0, 6.5, vf1) - 2292.0) / 2292.0 < 0.02)

    print("\n D. the RVE volume is where sigma_0 is already quoted")
    va = aligned_fibre_volume()
    ck("aligned fibre volume is 1.063 mm^3",
       abs(va - 1.0633) < 0.002, "%.4f mm^3" % va)
    ck("it is within 10 % of Sauder's 1 mm^3 reference",
       abs(va - V0_SAUDER) / V0_SAUDER < 0.10, "%.1f %%"
       % (100.0 * abs(va - V0_SAUDER) / V0_SAUDER))
    ck("so the size correction is under 2 %",
       abs(1.0 - (V0_SAUDER / va) ** (1.0 / 5.1)) < 0.02,
       "%.2f %%" % (100.0 * (1.0 - (V0_SAUDER / va) ** (1.0 / 5.1))))
    ck("mean sits below scale by the gamma factor",
       weibull_mean_at(660.0, 5.1, va) < weibull_scale_at(660.0, 5.1, va))
    ck("dry bundle is the floor of the three",
       daniels_bundle_at(660.0, 5.1, va) < weibull_mean_at(660.0, 5.1, va))

    print("\n E. the card is the outlier, by a factor this states out loud")
    ck("card fibre Xt is Zhang's 3580, not Toray's 3530",
       CARD_FIBRE_XT == 3580.0 and TORAY_T300 == 3530.0)
    ck("card fibre Xt is more than 1.5x the MEASURED filament strength",
       CARD_FIBRE_XT / 2107.0 > 1.5, "%.2fx at 24 C"
       % (CARD_FIBRE_XT / 2107.0))
    ck("card yarn Xt is VF_YARN x 3580",
       abs(CARD_XT - VF_YARN * CARD_FIBRE_XT) < 1.0)
    for T, _ in ZHANG_TABLE3:
        f = CARD_XT / recommended(T)
        ck("card is %.1fx the proposed value at %.0f C" % (f, T),
           2.5 < f < 7.0, "%.2fx" % f)

    print("\n F. the ROM bound now lands where it must -- BELOW the target")
    for T, uts in ZHANG_TABLE3:
        rb = rom_bound(recommended(T))
        ck("ROM bound at %.0f C is below the measured strength" % T,
           rb < uts, "%.1f vs %.2f MPa" % (rb, uts))
        ck("ROM bound at %.0f C is within 25 %% of it" % T,
           abs(rb - uts) / uts < 0.25, "%.1f %%" % (100.0 * (rb - uts) / uts))
    ck("the card's ROM bound is NOT below the target",
       rom_bound(CARD_XT) > 199.15, "%.0f MPa" % rom_bound(CARD_XT))
    ck("the card's ROM bound is the 706 MPa m6_calibration reported",
       abs(rom_bound(CARD_XT) - 706.0) < 2.0, "%.1f" % rom_bound(CARD_XT))

    print("\n G. the two independent routes agree")
    worst, worst_at = -1.0, "nothing compared"
    for T, _ in ZHANG_TABLE3:
        a, b = recommended(T), target_uts(T) / (0.5 * VY_RVE)
        rel = abs(a - b) / b
        if rel > worst:
            worst, worst_at = rel, "%.0f C" % T
    ck("constituent route and back-out agree to better than 25 %",
       worst >= 0.0 and worst < 0.25,
       "worst %.1f %% at %s" % (100.0 * worst, worst_at))
    ck("they agree to better than 10 % at room temperature",
       abs(recommended(23.0) - 128.45 / (0.5 * VY_RVE)) /
       (128.45 / (0.5 * VY_RVE)) < 0.10,
       "%.0f vs %.0f MPa" % (recommended(23.0), 128.45 / (0.5 * VY_RVE)))
    ck("the back-out route is marked NOT ADMISSIBLE",
       any(not ok for _l, _s, _x, ok in routes(1000.0)))
    ck("every admissible route used constituent data only",
       all(ok for l, _s, _x, ok in routes(1000.0) if "BACKOUT" not in l))

    print("\n H. the temperature shape is the second half of the finding")
    r_sr = interp_sigma_r(1000.0) / interp_sigma_r(23.0)
    _m1, a0 = interp_sauder(23.0)
    _m2, b0 = interp_sauder(1000.0)
    ck("sigma_R rises less than 15 % from RT to 1000 C",
       r_sr < 1.15, "%+.0f %%" % (100.0 * (r_sr - 1.0)))
    ck("sigma_0 rises more than 35 % over the same range",
       b0 / a0 > 1.35, "%+.0f %%" % (100.0 * (b0 / a0 - 1.0)))
    ck("the measured composite strength rises 55 %",
       abs(199.15 / 128.45 - 1.551) < 0.01,
       "%+.0f %%" % (100.0 * (199.15 / 128.45 - 1.0)))
    ck("the sigma_0 shape is closer to the measurement than sigma_R",
       abs(b0 / a0 - 199.15 / 128.45) < abs(r_sr - 199.15 / 128.45))

    print("\n J. the Yang counterfactual -- ripple computed BEFORE the verdict")
    # gf_temperature.py C2-C4 (2026-08-18) judged the card's X(T) 2.26x too
    # steep against refs/[10] Yang and traced the M6 card's +39.4 % g0
    # excursion to it.  Section H above anchors the same temperature shape on
    # Zhang Table 3's 55 % instead.  The two composite sources disagree on
    # the slope by 2.9x, the card (42.5 %) sits between them, and WHICH
    # anchor is right -- material, atmosphere, method -- is a1's judgement.
    # This section does not make that call.  It computes what moves under
    # each branch, so the verdict can be applied the day it arrives.
    yang = {23.0: 225.8, 500.0: 225.8 + (240.5 - 225.8) * (500.0 - 26.9)
            / (699.9 - 26.9), 1000.0: 268.2}
    fx5 = yang[500.0] / yang[23.0]
    fx10 = yang[1000.0] / yang[23.0]
    ck("Yang interpolated to OUR temperatures: 1.046 / 1.188",
       abs(fx5 - 1.0458) < 0.002 and abs(fx10 - 1.1878) < 0.002,
       "973 K is 700 C, not 500 C -- interpolation, not row-borrowing")
    # macro peak response to the yarn card value, two-point linear
    # (M6: yXt 474.71 -> peak 199.83 at 23 C; yXt 694.43 -> 284.71 at 1000 C)
    c_lin = (284.71 - 199.83) / (694.4297 - 474.7105)
    m_lin = 199.83 - c_lin * 474.7105
    ck("macro peak ~ 0.386*yXt + 16.4 (matrix share is small and constant)",
       abs(c_lin - 0.3863) < 0.001 and abs(m_lin - 16.4) < 0.3,
       "T500 back-check misses by 6.3 %% -- quote the ripple to 2 digits only")
    need5 = (199.83 * fx5 - m_lin) / c_lin
    need10 = (199.83 * fx10 - m_lin) / c_lin
    ck("Branch A (Yang right): yarn card would need 498 / 572 MPa",
       abs(need5 - 498.4) < 2.0 and abs(need10 - 571.8) < 2.0,
       "%.1f / %.1f" % (need5, need10))
    lo5, _hi5 = admissible_band(500.0)
    lo10, _hi10 = admissible_band(1000.0)
    ck("  those are OUTSIDE the sourced band -- 83 and 123 MPa below its "
       "LOW end", lo5 - need5 > 80.0 and lo10 - need10 > 120.0,
       "band %.0f-%.0f / %.0f-%.0f: not a walk, a re-sourcing"
       % (lo5, _hi5, lo10, _hi10))
    ck("  so Branch A cannot be executed as a knob move at all",
       need5 < lo5 and need10 < lo10,
       "Sauder's fibre data itself would have to be re-transferred "
       "(interface/in-situ mechanism at T), which is a1's area")
    ck("  its forecast peaks 209 / 237 MPa IMPROVE the Zhang ratios",
       abs(199.83 * fx5 / 179.42 - 1.16) < 0.01
       and abs(199.83 * fx10 / 199.15 - 1.19) < 0.01,
       "1.26x -> 1.16x at 500, 1.43x -> 1.19x at 1000")
    ck("  and the crack band only gets SAFER: le_max grows 1.36x / 1.47x",
       abs((581.401 / need5) ** 2 - 1.36) < 0.02
       and abs((694.4297 / need10) ** 2 - 1.47) < 0.02,
       "le_max ~ 1/Xt^2, so no admissibility is lost by adopting it")
    # Branch B: Zhang's slope is the anchor.  The card is then UNDER, not
    # over, and section H's sigma_0 rationale stands as written.
    ck("Branch B (Zhang right): the card UNDER-shoots the 55 % rise",
       (694.4297 / 474.7105 - 1.0) < (199.15 / 128.45 - 1.0),
       "card 46.3 %% vs Zhang 55.0 %% -- the a2-0047 '2.26x too steep' "
       "verdict was single-source and is qualified, not withdrawn")
    ck("the two composite anchors disagree on the slope by 2.9x",
       abs((199.15 / 128.45 - 1.0) / (fx10 - 1.0) - 2.9) < 0.1,
       "Zhang 55.0 %% vs Yang 18.8 %% on nominally the same material class")
    ck("  and the card sits BETWEEN them, nearer Zhang",
       (fx10 - 1.0) < (694.4297 / 474.7105 - 1.0) < (199.15 / 128.45 - 1.0))

    print("\n I. the rules this file must not break")
    src = open(os.path.join(HERE, "insitu_yarn_strength.py")).read()
    for phrase, why in (
            ("only constituent data goes in cards",
             "must name the rule it is obeying"),
            ("NOT ADMISSIBLE", "must mark the composite-derived route"),
            ("Xc is NOT scaled with it",
             "must refuse to scale the compressive strength"),
            ("a 20-degree shear", "must say why Xc is different"),
            ("Grade: fulltext", "must grade the literature it quotes")):
        ck("source states: %s" % why, phrase in src)
    ck("no route silently uses a composite measurement",
       all(("Zhang" not in l and "BACKOUT" not in l) or not ok
           for l, _s, _x, ok in routes(500.0)))

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d IN-SITU YARN STRENGTH CHECKS PASS" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    report()
