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
    return dict(T_C=T_C, E1=Z_EF1 * fE, E2=Z_EF2, G12=Z_GF12, G23=Z_GF23,
                nu12=Z_NUF12, alpha1=a1, alpha2=a2,
                Xt=Z_XFT * fX, Xc=Z_XFC * fX)


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
    return dict(T_C=T_C, E=Z_EM * fE, nu=Z_NUM, alpha=a,
                Xt=Z_XM, Xc=Z_XM,                    # no strength(T) source yet
                k=sic_k_upper(T) / 1000.0,           # W/(m.K) -> W/(mm.K)
                cp=sic_cp(T) * 1.0e6,                # J/(kg.K) -> mJ/(tonne.K)
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
    at = (fibre_strain(1200.0, PANEX33_TRANS) / (1200.0 - 300.0)) * 1e6
    ck("PANEX33 mean transverse CTE in 5-10e-6/K band (abstract)",
       max(5.0, min(10.0, at)), at, 1.0e-9, "1e-6/K")

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
        print("%g,%.1f,%.1f,%.1f,%.1f,%.2f,%.6e,%.6e,%.1f,%.1f,,,,,"
              "secant,%g,literature,\"see eval_correlations.py\""
              % (r["T_C"], r["E1"], r["E2"], r["G12"], r["G23"], r["nu12"],
                 r["alpha1"], r["alpha2"], r["Xt"], r["Xc"], STRESS_FREE_C))
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
