#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eval_correlations.py
====================
Evaluate the published constituent-property correlations at chosen temperatures
and emit the CSV rows for fibre_T300_vsT.csv and matrix_SiC_vsT.csv.

Every correlation below is transcribed from the paper PDFs in refs/ and carries
its source.  The point of putting them in code rather than typing numbers into
the CSVs is that the transcription is then auditable and re-runnable -- and two
of these were mis-read by automatic text extraction before being checked
against the rendered page (see the WARNINGs).

Run:  python3 data/properties/eval_correlations.py
      python3 data/properties/eval_correlations.py --temps 23 500 1000
      python3 data/properties/eval_correlations.py --check      # sanity checks

WHY THE CTE IS PRE-REBASED HERE
-------------------------------
Both CTE sources are referenced near room temperature, and our table includes a
row AT room temperature.  Rebasing a secant CTE onto the stress-free
temperature involves dividing by (T - T0); doing that inside
build_temperature_tables.py with only 3 table rows would also mean integrating
a cubic with 3-point trapezoid.  Both are avoided by evaluating the EXACT
thermal-strain functions here and dividing once:

    alpha_secant(T | T0) = [eps_th(T) - eps_th(T0)] / (T - T0)

The rows are therefore written with cte_type=secant and cte_ref_C = the
stress-free temperature, which makes the downstream conversion an identity.
"""
from __future__ import print_function

import argparse
import math
import sys

K = 273.15
STRESS_FREE_C = 1050.0

# ==========================================================================
# SiC MATRIX -- Snead et al., J. Nucl. Mater. 371 (2007) 329-377
#               refs/[06] 1st SiC 매트릭스 열물성.pdf
# ==========================================================================

def sic_cp(T_K):
    """Eq. (10), J/(kg.K), valid 200-2400 K.  +-7 % (200-1000 K), +-4 % above."""
    return (925.65 + 0.3772 * T_K - 7.9259e-5 * T_K ** 2
            - 3.1946e7 / T_K ** 2)


def sic_k_upper(T_K):
    """Eq. (12), W/(m.K).  UPPER LIMIT -- single-crystal fit above 300 K.

    WARNING: this is NOT the conductivity of the PIP matrix in our composite.
    A porous PIP matrix is far lower.  Treated as an upper bound and a
    sensitivity-study endpoint, never as the value.
    """
    return 1.0 / (0.0003 + 1.05e-5 * T_K)


def sic_alpha_inst(T_K):
    """Eq. (16), instantaneous CTE in 1/K, valid 125-1273 K.

    WARNING: pdftotext dropped the leading MINUS on the constant term.  The
    rendered page reads
        alpha = -1.8276 + 0.0178 T - 1.5544e-5 T^2 + 4.5246e-9 T^3  (1e-6/K)
    Check: T=298 K -> 2.216e-6, T=1273 K -> 4.975e-6, matching the paper's own
    statement of "about 2.2e-6/K at 298 K to 5.0e-6/K at 1273 K".  With the
    sign dropped the value at 298 K would be 5.87e-6, i.e. 2.6x too large, and
    the thermal residual stress with it.
    Above 1273 K the paper prescribes a constant 5.0e-6/K.
    """
    if T_K > 1273.0:
        return 5.0e-6
    a = (-1.8276 + 0.0178 * T_K - 1.5544e-5 * T_K ** 2
         + 4.5246e-9 * T_K ** 3)
    return a * 1.0e-6


def sic_alpha_integral(T_K):
    """Thermal strain of SiC from 298 K, by exact integration of Eq. (16)."""
    def prim(t):
        return (-1.8276 * t + 0.0178 * t ** 2 / 2.0
                - 1.5544e-5 * t ** 3 / 3.0 + 4.5246e-9 * t ** 4 / 4.0) * 1e-6
    lo = 298.0
    if T_K <= 1273.0:
        return prim(T_K) - prim(lo)
    return prim(1273.0) - prim(lo) + 5.0e-6 * (T_K - 1273.0)


def sic_E_GPa(T_K):
    """Eq. (18), Wachtman form: E = E0 - B T exp(-T0/T).

    E0 = 460 GPa, B = 0.04 GPa/K, T0 = 962 K.
    Uncertainty +-2 % (0-1000 K), +-5 % (1000-1800 K).
    Used only as a RATIO -- our matrix is PIP with E = 350 GPa at RT
    (Zhang 2022 Table 2), not 460 GPa CVD.
    """
    return 460.0 - 0.04 * T_K * math.exp(-962.0 / T_K)


SIC_RHO = 3.21e-9          # tonne/mm^3, theoretical density 3.21 g/cm^3

# ==========================================================================
# THE DECK'S THERMAL UNIT, DERIVED RATHER THAN CHOSEN
# ==========================================================================
# The mechanical side already pins the unit system past argument: stress is
# MPa = N/mm^2, so force is N and length is mm, and density 2.1e-09 is
# tonne/mm^3.  That is the Abaqus tonne-mm-s set, in which
#
#     ENERGY = N.mm = mJ = 1e-3 J        POWER = mJ/s = mW
#
# Abaqus solves  rho*cp*dT/dt = d/dx(k dT/dx), so the two sides must carry
# the same energy:
#
#     [rho][cp] = (tonne/mm^3)(mJ/(tonne.K)) = mJ/(mm^3.K)
#     [k]       = mJ/(s.mm.K) = mW/(mm.K)
#
# and  1 mW/(mm.K) = 1e-3 W / (1e-3 m . K) = 1 W/(m.K)  EXACTLY.  So the deck
# number for conductivity IS the SI number -- the conversion factor is one.
#
# Until 2026-08-11 both k rows were divided by 1000 ("W/(m.K) -> W/(mm.K)")
# while cp was multiplied by 1e6 into mJ/(tonne.K).  Those two conventions
# differ by exactly 1000, and the product they feed is the thermal
# diffusivity:  a = k/(rho.cp) came out 1000x too small.  Nothing had gone
# wrong yet only because every conduction job run so far is STEADY STATE,
# where a cancels; the first transient -- the macro quench -- would have
# produced a plate that barely cools and looks perfectly converged doing it.
# `checks()` now derives the diffusivity from the card triple instead of
# trusting the comment.
K_SI_TO_CARD = 1.0         # W/(m.K) -> mW/(mm.K), the deck's conductivity
CP_SI_TO_CARD = 1.0e6      # J/(kg.K) -> mJ/(tonne.K)


def card_diffusivity(k_card, rho_card, cp_card):
    """Thermal diffusivity in mm^2/s from the three numbers a deck carries.

    This is the only honest test of the unit set: k, rho and cp are each
    plausible on their own and only their combination can be wrong.
    """
    return k_card / (rho_card * cp_card)


def si_diffusivity_mm2s(k_si, rho_si, cp_si):
    """The same quantity computed entirely in SI, in mm^2/s."""
    return k_si / (rho_si * cp_si) * 1.0e6

# ==========================================================================
# CARBON FIBRE
# ==========================================================================
# CTE: Pradere & Sauder, Carbon 46 (2008) 1874-1884, Tables 3 and 4.
#      refs/[07] 1st T300 탄소섬유 열팽창 물성.pdf
#
# Their Eq. (1) defines the "specific CTE" as the CUMULATIVE THERMAL STRAIN in
# PERCENT relative to T0 = 300 K -- not a CTE rate.  Tables 3/4 are the
# polynomial coefficients of that strain.
#
# FIBRE CHOICE: PANEX 33 is ex-PAN with E = 230 GPa, the same precursor and the
# same modulus as the T300 of Zhang 2022 Table 1.  It is NOT T300 itself; that
# substitution is the single largest assumption in the fibre data.
# (HTA 5131, also ex-PAN but E = 248 GPa, is the sensitivity alternative.)
PANEX33_TRANS = [-1.860e-01, 5.850e-04, -1.360e-08, 1.059e-22]   # a0..a3
PANEX33_LONG = [2.529e-02, -1.569e-04, 2.228e-07, -1.877e-11, -1.288e-14]
HTA5131_TRANS = [-4.669e-02, -6.197e-05, 7.772e-07, -2.315e-10]
HTA5131_LONG = [7.955e-02, -4.753e-04, 8.481e-07, -5.226e-10, 1.223e-13]


def fibre_strain(T_K, coeffs):
    """Thermal strain (dimensionless) from the % polynomial, ref 300 K."""
    return sum(c * T_K ** i for i, c in enumerate(coeffs)) / 100.0


# THERMAL: Pradere, Batsale, Goyheneche, Pailler, Dilhaire, Carbon 47 (2009)
#          737-743.  refs/[09].  PANEX 33, "as received" (HTT 1600 K).
#
# Table 1 gives, measured directly:  rho = 1.75 g/cm3 (helium pycnometer),
#                                    k_longitudinal = 75 W/(m.K) AT 1500 K.
# Fig. 5a gives Cp(T) and Fig. 5b the longitudinal thermal diffusivity, both
# digitised below from the rendered figure.
#
# THREE LIMITATIONS, all of which matter for the quench analysis:
#  (1) MEASURED RANGE IS 800-2000 K.  Our analysis starts at 296 K.  Below
#      800 K the values here are NOT measurements.  The paper states that the
#      fibre specific heat is "quite close" to bulk graphite, so bulk graphite
#      is used as the low-temperature anchor and the rows are flagged.
#  (2) TRANSVERSE CONDUCTIVITY IS NOT MEASURED.  Only the longitudinal
#      diffusivity is.  k2 is therefore left EMPTY rather than invented -- see
#      the note in fibre_T300_vsT.csv for the inverse-calibration route.
#  (3) k_long ~ 60-75 W/(m.K) is far above the ~8-10 W/(m.K) usually quoted for
#      standard-modulus PAN fibre at room temperature.  Single-filament
#      measurement in a dedicated rig, and the paper reports conductivity
#      RISING with temperature for raw PAN fibre.  Treat as a sensitivity
#      parameter, not a settled value.
#
# Cp of PANEX 33 raw, digitised from Fig. 5a (J/(kg.K)):
P33_CP_T = [300.0, 800.0, 1000.0, 1200.0, 1400.0, 1500.0]
P33_CP = [710.0, 1480.0, 2100.0, 2230.0, 2290.0, 2360.0]
#         ^ 300 K entry is BULK GRAPHITE, not a fibre measurement (see (1))
P33_RHO = 1.75e-9            # tonne/mm^3, Table 1
P33_K_AT_1500K = 75.0        # W/(m.K), Table 1


def fibre_cp(T_K):
    """Specific heat, J/(kg.K).  Below 800 K this is bulk graphite."""
    return interp(T_K, P33_CP_T, P33_CP)


def fibre_k_long(T_K):
    """Longitudinal conductivity, W/(m.K).

    Fig. 5b shows the diffusivity of raw P33 flat within its scatter over
    860-1370 K (15-19e-6 m^2/s), so with k = a.rho.Cp the temperature
    dependence is carried by Cp.  Anchored on the one directly tabulated
    value, 75 W/(m.K) at 1500 K.
    """
    return P33_K_AT_1500K * fibre_cp(T_K) / fibre_cp(1500.0)


# Mechanical: Sauder, Lamon, Pailler, Compos. Sci. Technol. 62 (2002) 499-504,
#             Table 1, PAN-based fibre.  refs/[08].
#             E/E0 in %, sigma_R in MPa.  Used as RATIOS.
SAUDER_T_C = [24.0, 1000.0, 1200.0, 1400.0, 1600.0, 1800.0, 2000.0]
SAUDER_E_REL = [100.0, 98.5, 97.7, 95.7, 91.6, 81.8, 69.5]
SAUDER_SIG = [2107.0, 2292.0, 2401.0, 2386.0, 2359.0, 2857.0, 2348.0]


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            w = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + w * (ys[i + 1] - ys[i])
    return ys[-1]


# ==========================================================================
# Room-temperature anchors -- the VERIFIED Zhang 2022 card values.
# The correlations above supply only the temperature RATIO; the absolute
# values stay those of the paper the RVE card was verified against.
# ==========================================================================
Z_EF1, Z_EF2, Z_GF12, Z_GF23, Z_NUF12 = 230000.0, 40000.0, 24000.0, 14300.0, 0.26
Z_XFT, Z_XFC = 3580.0, 2470.0        # Ge 2018 Table 2
Z_EM, Z_NUM, Z_XM = 350000.0, 0.20, 310.0


def secant_alpha(T_C, strain_fn, T0_C=STRESS_FREE_C):
    """Secant CTE about T0, from an exact thermal-strain function."""
    T, T0 = T_C + K, T0_C + K
    if abs(T - T0) < 1.0e-9:
        h = 1.0
        return (strain_fn(T + h) - strain_fn(T - h)) / (2.0 * h)
    return (strain_fn(T) - strain_fn(T0)) / (T - T0)


#: Zhang 2022 Table 1 fibre CTEs -- the values the RVE card was verified with
Z_AF1, Z_AF2 = -0.3e-6, 3.1e-6


def fibre_row(T_C, trans=PANEX33_TRANS, long_=PANEX33_LONG, anchor=True):
    """One fibre CSV row.

    `anchor=True` (default) keeps the VERIFIED Zhang 2022 room-temperature CTE
    and takes only the SHAPE of the temperature variation from Pradere &
    Sauder, by an additive offset:

        alpha(T) = alpha_PANEX(T) + [alpha_Zhang(23 C) - alpha_PANEX(23 C)]

    Additive, not multiplicative, because the longitudinal fibre CTE changes
    sign -- a ratio would be meaningless across the zero crossing.  This is the
    same principle already used for E and X (absolute value from the verified
    card, temperature dependence from the literature).

    `anchor=False` uses the PANEX 33 values as measured.  The two differ a lot
    -- the secant longitudinal CTE about 1050 C is +1.24e-6/K measured versus
    -0.30e-6/K on the card -- because PANEX 33 is not T300 and because Zhang's
    single number is a room-temperature value, not a secant to 1050 C.  That
    gap is the largest single uncertainty in the fibre data and belongs in the
    sensitivity study, not hidden behind a default.
    """
    fE = interp(T_C, SAUDER_T_C, SAUDER_E_REL) / 100.0
    fX = interp(T_C, SAUDER_T_C, SAUDER_SIG) / SAUDER_SIG[0]
    a1 = secant_alpha(T_C, lambda t: fibre_strain(t, long_))
    a2 = secant_alpha(T_C, lambda t: fibre_strain(t, trans))
    if anchor:
        a1 += Z_AF1 - secant_alpha(23.0, lambda t: fibre_strain(t, long_))
        a2 += Z_AF2 - secant_alpha(23.0, lambda t: fibre_strain(t, trans))
    T = T_C + K
    return dict(T_C=T_C, E1=Z_EF1 * fE, E2=Z_EF2, G12=Z_GF12, G23=Z_GF23,
                nu12=Z_NUF12, alpha1=a1, alpha2=a2,
                Xt=Z_XFT * fX, Xc=Z_XFC * fX,
                k1=fibre_k_long(T) * K_SI_TO_CARD,   # W/(m.K) -> mW/(mm.K)
                cp=fibre_cp(T) * CP_SI_TO_CARD,     # J/(kg.K) -> mJ/(tonne.K)
                rho=P33_RHO)


# ==========================================================================
# SiC STRENGTH vs TEMPERATURE -- Snead 2007 Fig. 15.  refs/[06].
#
# The figure plots STRENGTH RETENTION, defined by its own caption as the
# high-temperature strength normalised by the room-temperature strength.
# That is exactly the fX multiplier the UMAT card wants, so it can be used
# directly with no conversion -- which is why it closes the gap that
# matrix_SiC_vsT.csv had been carrying as "no source yet".
#
# The figure draws THREE trend curves through the scatter, one per process
# route, and they diverge violently above ~1300 K:
#   Sintered / CVD / fluidized bed   flat, then rises to 1.27
#   Hot-pressed / HIP                declines, oxide grain-boundary phases
#   Reaction-bonded / CVD + excess Si rises then COLLAPSES to 0.2 by 1700 K
#
# WHICH ONE APPLIES TO US.  Our matrix is PIP (1050 C pyrolysis), which is
# none of these.  Reaction-bonded is excluded on chemistry -- it fails
# because of free silicon, which a PIP matrix does not contain.  That
# leaves sintered/CVD as the baseline and hot-pressed/HIP as the pessimistic
# bound, and the two bracket our whole analysis range within +-7 %.
#
# Digitized from the rendered figure; values carry about +-0.02 of reading
# scatter where markers overlap the trend line.
SNEAD_RET_T = [300.0, 700.0, 900.0, 1000.0, 1100.0, 1200.0, 1300.0,
               1400.0, 1500.0, 1600.0, 1700.0, 1800.0]
#: baseline: the sintered / CVD / fluidized-bed trend curve
SNEAD_RET_CVD = [1.000, 1.001, 1.005, 1.010, 1.019, 1.045, 1.065,
                 1.111, 1.192, 1.242, 1.260, 1.267]
#: pessimistic bound: the hot-pressed / HIP trend curve
SNEAD_RET_HP_T = [300.0, 900.0, 1100.0, 1200.0, 1300.0, 1400.0]
SNEAD_RET_HP = [1.000, 0.962, 0.946, 0.930, 0.900, 0.860]

#: above this the three process routes disagree by more than a factor of
#: four, so no single multiplier is defensible.  It is also above our
#: stress-free temperature, so the card never needs to go there.
SIC_STRENGTH_T_LIMIT_K = 1400.0


def sic_strength_retention(T_K, route="cvd"):
    """SiC strength / SiC strength at room temperature.  Snead Fig. 15."""
    if route == "hp":
        return interp(T_K, SNEAD_RET_HP_T, SNEAD_RET_HP)
    return interp(T_K, SNEAD_RET_T, SNEAD_RET_CVD)


#: Zhang 2022 Table 2 matrix CTE
Z_AM = 4.5e-6


def matrix_row(T_C, anchor=True):
    """One matrix CSV row.  `anchor` as in fibre_row.

    Here the anchoring barely matters: Snead's secant CTE at 23 C about 1050 C
    is 4.397e-6/K against the card's 4.5e-6/K, a 2.3 % difference between two
    fully independent sources.  That agreement is itself a useful check.
    """
    T = T_C + K
    fE = sic_E_GPa(T) / sic_E_GPa(23.0 + K)
    a = secant_alpha(T_C, sic_alpha_integral)
    if anchor:
        a += Z_AM - secant_alpha(23.0, sic_alpha_integral)
    fX = sic_strength_retention(T)          # Snead Fig. 15, sintered/CVD
    return dict(T_C=T_C, E=Z_EM * fE, nu=Z_NUM, alpha=a,
                Xt=Z_XM * fX, Xc=Z_XM * fX,
                k=sic_k_upper(T) * K_SI_TO_CARD,      # W/(m.K) -> mW/(mm.K)
                cp=sic_cp(T) * CP_SI_TO_CARD,        # J/(kg.K) -> mJ/(tonne.K)
                rho=SIC_RHO)


# ==========================================================================
def checks():
    """Sanity checks against statements made in the papers themselves."""
    print("sanity checks against the papers' own numbers")
    bad = []

    def ck(name, got, ref, tol, unit=""):
        ok = abs(got - ref) <= tol
        print("  [%s] %-52s %.4g vs %.4g %s"
              % ("PASS" if ok else "FAIL", name, got, ref, unit))
        if not ok:
            bad.append(name)

    ck("Snead a(298 K) = 2.2e-6/K (stated in text)",
       sic_alpha_inst(298.0) * 1e6, 2.2, 0.05, "1e-6/K")
    ck("Snead a(1273 K) = 5.0e-6/K (stated in text)",
       sic_alpha_inst(1273.0) * 1e6, 5.0, 0.05, "1e-6/K")
    ck("Snead mean a over 298-1273 K = 4.4e-6/K (stated)",
       sic_alpha_integral(1273.0) / (1273.0 - 298.0) * 1e6, 4.4, 0.1, "1e-6/K")
    ck("Snead Cp(298 K) = 671 J/(kg.K) (stated)",
       sic_cp(298.0), 671.0, 5.0, "J/(kg.K)")
    ck("Snead E(298 K) ~ E0 = 460 GPa", sic_E_GPa(298.0), 460.0, 1.0, "GPa")
    # The fibre strain polynomials must vanish at their own reference, 300 K.
    ck("PANEX33 longitudinal strain(300 K) = 0",
       fibre_strain(300.0, PANEX33_LONG), 0.0, 1.0e-4)
    ck("PANEX33 transverse strain(300 K) = 0",
       fibre_strain(300.0, PANEX33_TRANS), 0.0, 3.0e-4)
    # Paper abstract: mean transverse CTE 5e-6 to 10e-6 /K.
    ck("PANEX33 k_long(1500 K) = 75 W/(m.K) (Table 1)",
       fibre_k_long(1500.0), 75.0, 0.01, "W/(m.K)")

    # --- the unit set, derived from the card triple, not from the comment ---
    # Each of k, rho and cp is plausible alone; only the diffusivity they
    # form together can expose a mismatched energy unit, and it is the
    # diffusivity that drives every transient conduction job.
    for label, row, k_key, k_si, rho_si, cp_si in (
            ("SiC matrix", matrix_row(23.0), "k",
             sic_k_upper(296.15), 3210.0, sic_cp(296.15)),
            ("PANEX33 fibre", fibre_row(23.0), "k1",
             fibre_k_long(296.15), 1750.0, fibre_cp(296.15))):
        ck("%s card diffusivity = its own SI value [mm^2/s]" % label,
           card_diffusivity(row[k_key], row["rho"], row["cp"]),
           si_diffusivity_mm2s(k_si, rho_si, cp_si), 1.0e-6, "mm^2/s")
    ck("PANEX33 Cp(1000 K) ~ 2100 J/(kg.K) (Fig. 5a)",
       fibre_cp(1000.0), 2100.0, 1.0, "J/(kg.K)")
    at = (fibre_strain(1200.0, PANEX33_TRANS) / (1200.0 - 300.0)) * 1e6
    ck("PANEX33 mean transverse CTE in 5-10e-6/K band (abstract)",
       max(5.0, min(10.0, at)), at, 1.0e-9, "1e-6/K")

    # --- SiC strength retention, Snead Fig. 15 ---------------------------
    # The paper states in words: "no significant degradation of strength for
    # CVD SiC occurs up to a temperature of 1773 K, in fact an increase
    # above 1373 K is apparent".  The digitized curve must say the same.
    ck("Snead retention(298 K) = 1 by definition",
       sic_strength_retention(298.0), 1.0, 1.0e-9)
    ck("Snead: NO significant degradation up to 1773 K (stated)",
       min(sic_strength_retention(t) for t in range(300, 1774, 25)),
       1.0, 0.01)
    ck("Snead: an INCREASE is apparent above 1373 K (stated)",
       sic_strength_retention(1600.0) - sic_strength_retention(1373.0),
       0.14, 0.06)
    mono = min(sic_strength_retention(t + 25) - sic_strength_retention(t)
               for t in range(300, 1775, 25))
    ok = mono >= -1.0e-12
    print("  [%s] %-52s min step %+.2e"
          % ("PASS" if ok else "FAIL",
             "Snead: retention never decreases below 1773 K", mono))
    if not ok:
        bad.append("retention monotonic")

    # THE result of this section: over OUR range the multiplier is 1 within
    # a few percent, whichever of the two candidate process routes applies.
    hi = max(sic_strength_retention(t) for t in (296.0, 773.0, 1323.0))
    lo = min(sic_strength_retention(t, "hp") for t in (296.0, 773.0, 1323.0))
    print("\n  SiC strength retention over OUR range 296-1323 K:")
    print("    sintered/CVD baseline   1.000 -> %.3f" % hi)
    print("    hot-pressed/HIP bound   1.000 -> %.3f" % lo)
    print("    so fX = 1.0 is right to within %+.0f / %+.0f %%"
          % (100.0 * (hi - 1.0), 100.0 * (lo - 1.0)))
    print("    -> the placeholder was DEFENSIBLE, and now has a bound on it.")
    ck("fX = 1.0 is within 12 % across our range, either route",
       max(abs(hi - 1.0), abs(lo - 1.0)), 0.0, 0.12)
    ck("above 1400 K the routes disagree by more than 20 %",
       sic_strength_retention(1400.0) - sic_strength_retention(1400.0, "hp"),
       0.25, 0.06)

    # --- what the constituents alone CANNOT explain ----------------------
    # Both constituents gain strength with temperature, but only a little.
    # refs/[35] measures the COMPOSITE in-plane shear strength rising 39 %
    # from room temperature to 1273 K.  The difference is a quantitative,
    # falsifiable prediction the model has to make from TRS relaxation --
    # it is not something that can be put on a card.
    f_m = sic_strength_retention(1273.0) - 1.0
    f_f = interp(1000.0, SAUDER_T_C, SAUDER_SIG) / SAUDER_SIG[0] - 1.0
    print("\n  strength gain at ~1273 K, constituents vs composite:")
    print("    SiC matrix   (Snead Fig. 15)        %+.1f %%" % (100 * f_m))
    print("    carbon fibre (Sauder Table 1)       %+.1f %%" % (100 * f_f))
    print("    2D C/SiC in-plane shear, MEASURED   %+.1f %%   [refs/[35]]"
          % 38.9)
    print("""    -> the constituents account for %.0f-%.0f of the 39 points.  The
       remaining ~%.0f MUST come from relaxation of the interfacial thermal
       residual stress, which is what refs/[35] itself concludes.  That is
       a number our TRS-resolved model has to produce WITHOUT being told,
       and the TRS-off case (A) cannot produce at all."""
          % (100 * f_m, 100 * f_f, 38.9 - 100 * f_f))
    ck("the constituents alone cannot explain the composite gain",
       38.9 - 100.0 * max(f_m, f_f), 30.0, 6.0, "percentage points")

    # Cross-check the two independent sources against the verified card.
    am = secant_alpha(23.0, sic_alpha_integral) * 1e6
    print("\n  cross-check against the verified Zhang 2022 card:")
    print("    SiC matrix secant CTE(23 C about 1050 C) = %.3f e-6/K"
          "   card: 4.500" % am)
    a1 = secant_alpha(23.0, lambda t: fibre_strain(t, PANEX33_LONG)) * 1e6
    a2 = secant_alpha(23.0, lambda t: fibre_strain(t, PANEX33_TRANS)) * 1e6
    print("    fibre longitudinal                        = %.3f e-6/K"
          "   card: -0.300" % a1)
    print("    fibre transverse                          = %.3f e-6/K"
          "   card:  3.100" % a2)
    print("    (the card values are Zhang's own T300 numbers; these come from"
          "\n     a different ex-PAN fibre and a different reference frame, so"
          "\n     agreement in ORDER and SIGN is what to look for, not equality)")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--temps", type=float, nargs="+",
                    default=[23.0, 500.0, 1000.0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-anchor", action="store_true",
                    help="use the literature CTEs as measured, instead of "
                         "offsetting them onto the verified card value")
    args = ap.parse_args()
    if args.check:
        return checks()

    print("# fibre_T300_vsT.csv rows  (cte_type=secant, cte_ref_C=%g)"
          % STRESS_FREE_C)
    for T in args.temps:
        r = fibre_row(T, anchor=not args.no_anchor)
        print("%g,%.1f,%.1f,%.1f,%.1f,%.2f,%.6e,%.6e,%.1f,%.1f,"
              "%.6e,,%.6e,%.6e,secant,%g,literature,"
              "\"see eval_correlations.py\""
              % (r["T_C"], r["E1"], r["E2"], r["G12"], r["G23"], r["nu12"],
                 r["alpha1"], r["alpha2"], r["Xt"], r["Xc"],
                 r["k1"], r["cp"], r["rho"], STRESS_FREE_C))
    print()
    print("# matrix_SiC_vsT.csv rows")
    for T in args.temps:
        r = matrix_row(T, anchor=not args.no_anchor)
        print("%g,%.1f,%.2f,%.6e,%.1f,%.1f,%.6e,%.6e,%.6e,"
              "secant,%g,PIP,literature,\"see eval_correlations.py\""
              % (r["T_C"], r["E"], r["nu"], r["alpha"], r["Xt"], r["Xc"],
                 r["k"], r["cp"], r["rho"], STRESS_FREE_C))
    return 0


if __name__ == "__main__":
    sys.exit(main())
