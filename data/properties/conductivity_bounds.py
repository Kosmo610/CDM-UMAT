#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conductivity_bounds.py
======================
Close the k2 gap ANALYTICALLY before spending an RVE conductivity job.

`data/properties/fibre_T300_vsT.csv` deliberately leaves the transverse fibre
conductivity k2 empty rather than inventing it, because the through-thickness
homogenised conductivity kbar3 sets the temperature gradient of the quench,
and the quench gradient is the whole point of the thesis.

The question this file answers is NOT "what is k2".  It is:

    HOW MUCH DOES kbar3 ACTUALLY MOVE WHEN k2 MOVES?

If the answer is "hardly at all", the gap closes with a sentence.  If it is
"a lot", we learn exactly what precision is needed and what to calibrate
against.  Either way it costs no solver time.

Two-level homogenisation, matching the RVE the thesis uses
----------------------------------------------------------
  level 1  yarn   = carbon fibre (Vf = 0.79194) in SiC matrix, UD
  level 2  RVE    = plain weave, yarn volume fraction 0.4982 (the measured
                    value of abaqus/meshes/CSiC_RVE_0135.inp)

Through the thickness (z) BOTH warp and weft yarns present their TRANSVERSE
face, so kbar3 depends on k2 through the yarn transverse conductivity and on
nothing else in the fibre.  That is what makes this a clean one-parameter
sensitivity study.

Bounds used
-----------
  Voigt / parallel   upper bound, heat paths in parallel
  Reuss / series     lower bound, heat paths in series
  Hashin-Shtrikman   the tightest bounds available without geometry
  Rayleigh           exact for a periodic array of cylinders, i.e. the right
                     model for the fibre-in-matrix level.  Coincides with one
                     HS bound (lower if k_incl < k_mat, upper if greater).

Run:  python3 data/properties/conductivity_bounds.py
      python3 data/properties/conductivity_bounds.py --check    (self-tests)
"""
from __future__ import print_function

import math
import sys

# ==========================================================================
# Geometry of OUR material (verified numbers, not assumptions)
# ==========================================================================
VF_YARN = 0.79194      # fibre volume fraction INSIDE a yarn (yarn-level Vf)
VY_RVE = 0.4982        # yarn volume fraction in the RVE, from the 26k mesh
# -> overall fibre volume fraction 0.4982 * 0.79194 = 39.46 %

# ==========================================================================
# Literature values.  Every number here is traceable; see the table printed
# by main() and data/literature/README.md.
# ==========================================================================
#: transverse carbon-fibre conductivity, W/(m.K)
K2_LITERATURE = {
    "Sun 2021 refs/[22] Table 1": 1.0,
    "Zhang 2024 refs/[17] Table 1": 1.0,
    "isotropic fibre (k2 = k1)": 8.0,
}
#: longitudinal carbon-fibre conductivity, W/(m.K)
K1_LITERATURE = {
    "Sun 2021 refs/[22] Table 1": 8.0,
    "Zhang 2024 refs/[17] Table 1": 8.0,
    "Pradere 2009 refs/[09] @1500 K": 75.0,
    "Pradere 2009 refs/[09] @296 K": 22.6,
}
#: SiC matrix conductivity, W/(m.K)
KM_LITERATURE = {
    "Zhang 2024 refs/[17], CVI SiC": 25.0,
    "Katoh 2006 refs/[13], matrix SiC": 70.0,
    "Snead 2007 Eq.12 @296 K (SINGLE CRYSTAL)": 293.0,
    "Snead 2007 Eq.12 @1273 K (SINGLE CRYSTAL)": 73.2,
}
#: MEASURED composite through-thickness conductivity -- the calibration target
KBAR3_TARGET = 6.29        # W/(m.K), refs/[12], stated in the text
KBAR3_TARGET_NOTE = ("refs/[12]: 'Kcs is thermal conductivity of C/SiC "
                     "composites measured as 6.29 W/m.k' (through-thickness)")

#: ASSUMPTION, a1 2026-08-23 (atmosphere_verdicts.py section D).  refs/[12]
#: states neither the ATMOSPHERE nor the TEMPERATURE of the 6.29 measurement.
#: Everything it is compared against here is room temperature -- Zhang [17]
#: CVI SiC 25.0, Pradere [09] @296 K -- so this file has always read 6.29 as a
#: room-temperature value.  That reading was never written down.  It is
#: written down now, because it is load-bearing: C/SiC conductivity roughly
#: halves from RT to 1273 K, so a mis-set anchor temperature moves the
#: porosity solve rather than a decimal place.  The atmosphere, by contrast,
#: is the smaller exposure -- an LFA shot is short and the value is read at
#: the low-temperature end of the sweep.
#:
#: This does NOT change [12]'s trust grade.  The grade records how WE got a
#: number (fulltext / digitized / abstract / secondary), not whether the
#: measurement suits our model; folding applicability into it would make one
#: tag mean two things.  Scope lives here and in the census.
KBAR3_TARGET_TEMPERATURE_ASSUMED = 296.0   # K
KBAR3_TARGET_TEMPERATURE_NOTE = (
    "refs/[12] does not state the temperature of 6.29 W/(m.K); read as room "
    "temperature because every comparison value in this file is. assumption, "
    "not a measurement -- see data/literature/atmosphere_verdicts.py section D")


# ==========================================================================
# Two-phase bounds
# ==========================================================================
def voigt(f, ka, kb):
    """Parallel / rule of mixtures.  Upper bound.  f is the fraction of a."""
    return f * ka + (1.0 - f) * kb


def reuss(f, ka, kb):
    """Series.  Lower bound."""
    return 1.0 / (f / ka + (1.0 - f) / kb)


def hs_bound(f, k_incl, k_mat, dim=3):
    """Hashin-Shtrikman estimate with `k_mat` as the enveloping phase.

    dim = 3 spheres in 3-D, dim = 2 cylinders transverse to their axis.
    Taking k_mat as the stiffer phase gives the upper bound and vice versa,
    so calling it both ways brackets the answer.
    """
    if abs(k_incl - k_mat) < 1.0e-14:      # identical phases, no contrast
        return k_mat
    return k_mat + f / (1.0 / (k_incl - k_mat)
                        + (1.0 - f) / (dim * k_mat))


def rayleigh_transverse(f, k_f, k_m):
    """Transverse conductivity of a periodic array of cylinders in a matrix.

    Exact to first order in the fibre volume fraction and the standard choice
    for a fibre tow.  Identical to the Hashin-Shtrikman bound taken with the
    matrix as the enveloping phase, which is physically right here: the SiC
    is continuous and the filaments are discrete.
    """
    a = (k_f - k_m) / (k_f + k_m)
    return k_m * (1.0 + 2.0 * f * a / (1.0 - f * a))


# ==========================================================================
# Level 1 -- yarn
# ==========================================================================
def yarn_conductivity(k1_f, k2_f, k_m, vf=VF_YARN):
    """Return (k_long, k_trans) of a yarn, W/(m.K).

    Longitudinal is the rule of mixtures and is EXACT: the phases are
    genuinely in parallel along the fibre.  Transverse is the Rayleigh
    cylinder result.
    """
    return voigt(vf, k1_f, k_m), rayleigh_transverse(vf, k2_f, k_m)


# ==========================================================================
# Level 2 -- plain-weave RVE, through the thickness
# ==========================================================================
def rve_kbar3(k_yarn_trans, k_m, vy=VY_RVE):
    """Bracket the through-thickness conductivity of the plain weave.

    Through the thickness every yarn -- warp and weft alike -- is crossed
    TRANSVERSELY, so only the yarn transverse conductivity enters.  The
    weave is neither pure series nor pure parallel, so return both plus the
    HS bracket; the RVE_COND job will land inside.
    """
    lo = reuss(vy, k_yarn_trans, k_m)
    hi = voigt(vy, k_yarn_trans, k_m)
    hs_lo = hs_bound(vy, k_yarn_trans, k_m, dim=3)
    hs_hi = hs_bound(1.0 - vy, k_m, k_yarn_trans, dim=3)
    return dict(series=lo, hs_lo=min(hs_lo, hs_hi), hs_hi=max(hs_lo, hs_hi),
                parallel=hi)


def rve_kbar1(k_yarn_long, k_yarn_trans, k_m, vy=VY_RVE):
    """In-plane conductivity.  Half the yarns run along x, half across.

    Reported only as a cross-check against the published in-plane /
    through-thickness ANISOTROPY, which is a much more robust observable
    than either value on its own.
    """
    k_eff_yarn = 0.5 * (k_yarn_long + k_yarn_trans)
    return dict(series=reuss(vy, k_eff_yarn, k_m),
                parallel=voigt(vy, k_eff_yarn, k_m))


#: air in the pores, W/(m.K).  refs/[22] Table 1 treats voids as air.
K_VOID = 0.025
#: matrix porosity of the material refs/[22] characterised by X-ray CT
POROSITY_REF22 = 0.24
#: constituent densities, g/cm3, for the rule-of-mixtures inversion below
RHO_FIBRE_T300, RHO_SIC = 1.76, 3.21
#: refs/[28] section 2.1 also states the bulk density: "about 2.0 g/cm3"
RHO_REF28 = 2.0
#: COMPOSITE-level porosity of the SAME architecture as this thesis --
#: refs/[28] section 2.1 (full text, 2026-08-04): "the bulk density of the
#: as-received specimens is about 2.0 g/cm3, with fibre and porosity
#: contents of 40% and 10-15%, respectively."  2D plain-woven CVI C/SiC,
#: T300, PyC interphase.  NOTE the unit basis differs from POROSITY_REF22:
#: this is pore volume over TOTAL volume, not over matrix volume.
POROSITY_REF28_COMPOSITE = (0.10, 0.15)


def porous_matrix(k_dense, p, k_void=K_VOID):
    """Conductivity of the SiC matrix once its pores are accounted for.

    Rayleigh again, with the (nearly insulating) pores as the inclusions.
    A PIP or CVI matrix is porous by construction -- refs/[22] measures
    24 % on the material it characterised by X-ray CT -- and pores knock
    the conductivity down hard because air conducts ~1000x worse than SiC.
    """
    return rayleigh_transverse(p, k_void, k_dense)


# --------------------------------------------------------------------------
# Which porosity model?  It is not a free choice -- it is set by whether the
# pores are closed or open, and C/SiC's are open.
# --------------------------------------------------------------------------
# Smith, D.S., Alzina, A., Bourret, J., Nait-Ali, B., Pennec, F.,
# Tessier-Doyen, N., "Thermal conductivity of porous materials",
# J. Mater. Res. 28(17) (2013) 2260-2272, doi:10.1557/jmr.2013.179,
# surveys pore fractions from 4 % to 95 % and reports that below about
# p = 0.65 the Maxwell-Eucken relation fits CLOSED porosity and the
# Landauer (effective-medium) relation fits OPEN porosity, checked against
# alumina, zirconia and tin oxide.  The unifying treatment of the five
# structural models is Wang, J., Carson, J.K., North, M.F., Cleland, D.J.,
# Int. J. Heat Mass Transfer 49 (2006) 3075-3083.
#
# THE CHOICE IS ALREADY MADE BY THE REST OF THE THESIS.  A CVI or PIP matrix
# is porous because the infiltrant cannot reach everywhere, and the pores it
# leaves are interconnected -- which is exactly why oxygen reaches the PyC
# interphase and the carbon fibres, the mechanism Ch.2 2.5.4 uses to explain
# the sign of k in the cycle damage law.  Open porosity is not an assumption
# here; it is a premise the damage model already depends on.
#
# So Landauer is the branch, and Maxwell-Eucken is carried only to show what
# assuming closed pores would have cost.


def maxwell_eucken(k_dense, p, k_void=K_VOID):
    """Closed, non-touching pores dispersed in a continuous solid.

        k = k_s * [2k_s + k_p - 2p(k_s - k_p)] / [2k_s + k_p + p(k_s - k_p)]

    Biased towards the matrix phase by construction: the pores never touch,
    so they cannot form a barrier however many there are.
    """
    num = 2.0 * k_dense + k_void - 2.0 * p * (k_dense - k_void)
    den = 2.0 * k_dense + k_void + p * (k_dense - k_void)
    return k_dense * num / den


def landauer(k_dense, p, k_void=K_VOID):
    """Landauer / Bruggeman effective medium: neither phase is continuous.

    Solves  (1-p)(k_s - k)/(k_s + 2k) + p(k_p - k)/(k_p + 2k) = 0,
    the positive root of the quadratic

        2k^2 + k[(3p-1)k_s + (2-3p)k_p] - k_s*k_p = 0

    With insulating pores this reduces to k = k_s(2 - 3p)/2, so the
    conductivity reaches zero at p = 2/3 -- the percolation threshold, which
    is the physical content the Maxwell-Eucken form does not have.
    """
    b = -((2.0 - 3.0 * p) * k_dense + (3.0 * p - 1.0) * k_void)
    c = -k_dense * k_void
    return (-b + math.sqrt(b * b - 8.0 * c)) / 4.0


def landauer_insulating(k_dense, p):
    """The k_p -> 0 limit of landauer(), for checking the general form."""
    return max(0.0, k_dense * (2.0 - 3.0 * p) / 2.0)


def kbar3_with_model(model, k_dense, p, k2_f=1.0, k1_f=8.0,
                     estimator="series"):
    """kbar3 with the matrix porosity handled by `model`.

    Same pipeline as kbar3_from_k2, but the porosity model is a parameter
    rather than hard-wired to Rayleigh.  The porosity lives in the MATRIX,
    which is where infiltration leaves it; the two-level homogenisation then
    carries it up to the composite.
    """
    km = model(k_dense, p) if p > 0.0 else k_dense
    _, kt = yarn_conductivity(k1_f, k2_f, km)
    return rve_kbar3(kt, km)[estimator]


def porosity_for(model, target, k_dense, k2_f=1.0, k1_f=8.0,
                 estimator="series"):
    """Which matrix porosity brings kbar3 down to `target` under `model`?

    Returns None when the model cannot reach the target at any admissible
    porosity -- which is itself a result, not a failure.
    """
    lo, hi = 0.0, 0.65
    if kbar3_with_model(model, k_dense, lo, k2_f, k1_f, estimator) < target:
        return None
    if kbar3_with_model(model, k_dense, hi, k2_f, k1_f, estimator) > target:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if kbar3_with_model(model, k_dense, mid, k2_f, k1_f,
                            estimator) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def kbar3_from_k2(k2_f, k_m, k1_f=8.0, estimator="series", porosity=0.0):
    """The one-line pipeline: k2 -> kbar3, for sweeping."""
    km = porous_matrix(k_m, porosity) if porosity > 0.0 else k_m
    _, kt = yarn_conductivity(k1_f, k2_f, km)
    return rve_kbar3(kt, km)[estimator]


def solve_porosity(target, k_dense, k2_f=1.0, k1_f=8.0, estimator="series"):
    """Inverse: what porosity brings kbar3 down to a measured value?"""
    lo, hi = 0.0, 0.60
    if kbar3_from_k2(k2_f, k_dense, k1_f, estimator, lo) < target:
        return None
    if kbar3_from_k2(k2_f, k_dense, k1_f, estimator, hi) > target:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if kbar3_from_k2(k2_f, k_dense, k1_f, estimator, mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def solve_k2(target, k_m, k1_f=8.0, estimator="series"):
    """Inverse: which k2 reproduces a measured kbar3?  None if unreachable."""
    lo, hi = 1.0e-4, 1.0e4
    if not (kbar3_from_k2(lo, k_m, k1_f, estimator) <= target
            <= kbar3_from_k2(hi, k_m, k1_f, estimator)):
        return None
    for _ in range(200):
        mid = (lo * hi) ** 0.5
        if kbar3_from_k2(mid, k_m, k1_f, estimator) < target:
            lo = mid
        else:
            hi = mid
    return (lo * hi) ** 0.5


# ==========================================================================
def main():
    print("=" * 74)
    print("k2 SENSITIVITY -- does the transverse fibre conductivity matter?")
    print("=" * 74)
    print("RVE: yarn Vf = %.5f, yarn fraction in RVE = %.4f "
          "-> overall Vf = %.2f %%"
          % (VF_YARN, VY_RVE, 100.0 * VF_YARN * VY_RVE))

    print("\n--- literature values found in refs/ " + "-" * 36)
    print("  transverse fibre k2, W/(m.K)")
    for k, v in sorted(K2_LITERATURE.items(), key=lambda x: x[1]):
        print("    %-42s %8.3g" % (k, v))
    print("  longitudinal fibre k1, W/(m.K)")
    for k, v in sorted(K1_LITERATURE.items(), key=lambda x: x[1]):
        print("    %-42s %8.3g" % (k, v))
    print("  SiC matrix k, W/(m.K)")
    for k, v in sorted(KM_LITERATURE.items(), key=lambda x: x[1]):
        print("    %-42s %8.3g" % (k, v))
    print("  MEASURED composite kbar3 = %.2f W/(m.K)" % KBAR3_TARGET)
    print("    %s" % KBAR3_TARGET_NOTE)

    # ---- sweep 1: k2 at a fixed, physically sensible matrix -------------
    km = 25.0
    print("\n--- sweep 1: k2 over its whole literature range, k_m = %g "
          % km + "-" * 12)
    print("  %-8s %-12s %-32s" % ("k2", "yarn k_T", "RVE kbar3 (series..parallel)"))
    base = None
    for k2 in (0.5, 1.0, 2.0, 4.0, 8.0):
        _, kt = yarn_conductivity(8.0, k2, km)
        b = rve_kbar3(kt, km)
        if base is None:
            base = b["series"]
        print("  %-8.2f %-12.3f %6.2f .. %6.2f   (series x%.2f)"
              % (k2, kt, b["series"], b["parallel"], b["series"] / base))
    lo = kbar3_from_k2(1.0, km)
    hi = kbar3_from_k2(8.0, km)
    print("\n  k2 = 1 -> 8 (the full literature range) moves kbar3 by "
          "%.0f %%" % (100.0 * (hi / lo - 1.0)))

    # ---- sweep 2: the matrix, at fixed k2 --------------------------------
    print("\n--- sweep 2: the SAME question for the MATRIX, k2 = 1 " + "-" * 20)
    print("  %-42s %-10s %-10s" % ("k_m source", "yarn k_T", "kbar3(series)"))
    vals = []
    for name, kmv in sorted(KM_LITERATURE.items(), key=lambda x: x[1]):
        _, kt = yarn_conductivity(8.0, 1.0, kmv)
        b = rve_kbar3(kt, kmv)
        vals.append(b["series"])
        print("  %-42s %-10.2f %-10.2f" % (name, kt, b["series"]))
    print("\n  the matrix choice moves kbar3 by a factor of %.1f"
          % (max(vals) / min(vals)))

    # ---- the verdict -----------------------------------------------------
    r_k2 = hi / lo
    r_km = max(vals) / min(vals)
    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    print("  k2  over its full literature range   -> kbar3 x %.2f" % r_k2)
    print("  k_m over its full literature range   -> kbar3 x %.2f" % r_km)
    print("  ratio of the two sensitivities       -> %.1f x" % (r_km / r_k2))
    print("""
  k2 is NOT negligible, but it is the SECOND-order uncertainty.  The matrix
  conductivity is first order and is currently the single-crystal upper
  limit (Snead Eq.12), which is the wrong number for a PIP/CVI matrix by
  roughly an order of magnitude.  Fixing k_m before k2 is not a preference,
  it is the only order that makes sense.""")

    # ---- inverse calibration --------------------------------------------
    print("\n--- inverse calibration against the measured kbar3 " + "-" * 22)
    print("  target: kbar3 = %.2f W/(m.K)   [refs/[12], through-thickness]"
          % KBAR3_TARGET)
    print("  %-14s %-14s %-32s" % ("k_m", "k2 required", "verdict"))
    for name, kmv in sorted(KM_LITERATURE.items(), key=lambda x: x[1]):
        k2 = solve_k2(KBAR3_TARGET, kmv)
        if k2 is None:
            reach = kbar3_from_k2(1.0e-4, kmv)
            note = ("IMPOSSIBLE: kbar3 >= %.1f even with k2 -> 0" % reach)
        elif 0.5 <= k2 <= 8.0:
            note = "consistent with the literature range"
        else:
            note = "outside the literature range 0.5-8"
        print("  %-14.4g %-14s %-32s"
              % (kmv, ("%.3f" % k2) if k2 else "--", note))
    print("""
  Only a matrix conductivity in the 25 W/(m.K) class can reproduce the
  measured composite value at ALL.  With the Snead single-crystal number
  the composite cannot be brought down to 6.29 even by setting the fibre
  transverse conductivity to zero -- the matrix alone short-circuits it.
  That is a proof, not an estimate, and it does not need Abaqus.""")

    # ---- porosity: what the two-phase model is missing -------------------
    print("\n--- the residual gap: POROSITY " + "-" * 43)
    print("""  At k_m = 25 and k2 = 1 the SERIES estimate is %.2f W/(m.K), and series
  is a LOWER bound -- the real weave must sit above it.  But the measured
  value is %.2f.  A dense two-phase model therefore cannot reach the
  measurement from the right side: something is missing, and for a PIP or
  CVI matrix that something is porosity.""" % (kbar3_from_k2(1.0, 25.0),
                                               KBAR3_TARGET))
    print("\n  %-12s %-14s %-14s %-12s" % ("porosity", "k_matrix", "yarn k_T",
                                           "kbar3(series)"))
    for p in (0.0, 0.05, 0.10, 0.15, 0.20, POROSITY_REF22):
        km_p = porous_matrix(25.0, p)
        _, kt = yarn_conductivity(8.0, 1.0, km_p)
        print("  %-12s %-14.2f %-14.2f %-12.2f"
              % ("%.0f %%" % (100 * p), km_p, kt,
                 rve_kbar3(kt, km_p)["series"]))
    p_need = solve_porosity(KBAR3_TARGET, 25.0)
    print("\n  porosity that reproduces the measured %.2f W/(m.K): %s"
          % (KBAR3_TARGET,
             "%.1f %%" % (100 * p_need) if p_need else "unreachable"))
    print("""  refs/[22] measured 24 % matrix porosity by X-ray CT and ran a 5-24 %
  study, so the porosity needed here is BELOW the range these materials
  actually have.  Read that the right way round: it does not confirm a
  porosity of 4.5 %, it shows the gap is SMALL and that porosity covers it
  several times over.  Two readings survive, and only the RVE job can
  separate them:
    (a) refs/[12]'s composite is denser than refs/[22]'s, and the true
        porosity correction is close to this small value;
    (b) porosity is larger and something in the other direction offsets
        it -- most plausibly that the real weave sits well ABOVE the
        series bound, which is only a lower limit.
  Nothing here was tuned: k2 = 1, k_m = 25 and k_void = 0.025 are all
  literature values, and 6.29 is a measurement.

  CONSEQUENCE FOR THE RVE.  Our mesh has 100 % fill -- zero porosity (see
  abaqus/meshes/README.md).  RVE_COND will therefore OVERPREDICT kbar3,
  and an overpredicted conductivity makes the quench gradient too
  SHALLOW, which is the non-conservative direction.  Either put porosity
  into the matrix phase or apply a stated knock-down.  This has to be
  decided before M4, not explained away after it.""")

    # ---- anisotropy cross-check -----------------------------------------
    print("\n--- cross-check: in-plane / through-thickness anisotropy "
          + "-" * 17)
    kl, kt = yarn_conductivity(8.0, 1.0, 25.0)
    b3 = rve_kbar3(kt, 25.0)
    b1 = rve_kbar1(kl, kt, 25.0)
    print("  yarn: k_long = %.2f, k_trans = %.2f W/(m.K)" % (kl, kt))
    print("  RVE : kbar1 = %.2f .. %.2f, kbar3 = %.2f .. %.2f"
          % (b1["series"], b1["parallel"], b3["series"], b3["parallel"]))
    print("  predicted anisotropy kbar1/kbar3 = %.2f (series) .. %.2f "
          "(parallel)" % (b1["series"] / b3["series"],
                          b1["parallel"] / b3["parallel"]))
    print("""  refs/[13] measures, for a 2D architecture, in-plane ~35 against
  through-thickness 15-20 W/(m.K), i.e. an anisotropy of about 2.  That is
  a SiC/SiC composite, so the magnitudes do not transfer -- but the
  anisotropy is an architecture effect and does.  Our bracket contains it.""")

    print("\n" + "=" * 74)
    print("WHAT THIS BUYS")
    print("=" * 74)
    print("""  1. k2 = 1.0 W/(m.K) can now go on the card with two independent
     citations (refs/[22] and refs/[17] Table 1, same value), instead of
     being left empty or invented.
  2. The k_m row is the one that has to change: the Snead single-crystal
     conductivity is an upper bound, not a property of our matrix.
  3. RVE_COND is still needed -- it decides where inside the series-parallel
     bracket the weave actually sits -- but it is now a ONE-parameter
     confirmation instead of a two-parameter fishing trip.""")
    return 0


# ==========================================================================
def check():
    """Self-tests.  A bounds calculation that is not ordered is worthless."""
    fails = []

    def ck(name, ok, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("  " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    # 1. identical phases -> every estimator collapses to the same number
    for est in (voigt, reuss):
        ck("%s: identical phases give the phase value" % est.__name__,
           abs(est(0.4, 7.0, 7.0) - 7.0) < 1e-12)
    ck("rayleigh: identical phases give the phase value",
       abs(rayleigh_transverse(0.4, 7.0, 7.0) - 7.0) < 1e-12)
    ck("hs: identical phases give the phase value",
       abs(hs_bound(0.4, 7.0, 7.0) - 7.0) < 1e-9)

    # 2. bound ordering must hold for every combination
    bad = []
    for f in (0.05, 0.3, 0.5, 0.79194, 0.95):
        for ka in (0.1, 1.0, 8.0, 300.0):
            for kb in (0.1, 1.0, 25.0, 293.0):
                r, v = reuss(f, ka, kb), voigt(f, ka, kb)
                ray = rayleigh_transverse(f, ka, kb)
                if not (r - 1e-9 <= ray <= v + 1e-9):
                    bad.append((f, ka, kb, r, ray, v))
    ck("Reuss <= Rayleigh <= Voigt for all 100 combinations",
       not bad, "%d violations" % len(bad))

    bad = []
    for f in (0.1, 0.4982, 0.9):
        for ki in (0.5, 4.0, 40.0):
            for km in (1.0, 25.0, 293.0):
                b = rve_kbar3(ki, km, f)
                if not (b["series"] - 1e-9 <= b["hs_lo"] <= b["hs_hi"]
                        <= b["parallel"] + 1e-9):
                    bad.append((f, ki, km, b))
    ck("series <= HS_lo <= HS_hi <= parallel", not bad,
       "%d violations" % len(bad))

    # 3. monotonicity: more conductive fibre can never lower kbar3
    seq = [kbar3_from_k2(k2, 25.0) for k2 in (0.1, 0.5, 1, 2, 4, 8, 20)]
    ck("kbar3 increases monotonically with k2",
       all(b > a for a, b in zip(seq[:-1], seq[1:])))

    # 4. the inverse solver must invert the forward map
    worst = 0.0
    for km in (10.0, 25.0, 50.0):
        for tgt in (3.0, 5.0, 6.29):
            k2 = solve_k2(tgt, km)
            if k2 is not None:
                worst = max(worst, abs(kbar3_from_k2(k2, km) - tgt) / tgt)
    ck("solve_k2 inverts kbar3_from_k2", worst < 1e-8,
       "worst rel. err = %.2e" % worst)

    # 5. THE physical claim of this file, asserted so it cannot rot
    ck("Snead single-crystal k_m cannot reach the measured kbar3",
       solve_k2(KBAR3_TARGET, 293.0) is None,
       "kbar3 >= %.1f even at k2 -> 0" % kbar3_from_k2(1e-4, 293.0))
    k2_needed = solve_k2(KBAR3_TARGET, 25.0)
    ck("k_m = 25 needs a k2 inside the literature range",
       k2_needed is not None and 0.5 <= k2_needed <= 8.0,
       "k2 = %.3f" % k2_needed if k2_needed else "unreachable")

    # 6. the sensitivity ratio the verdict is built on
    r_k2 = kbar3_from_k2(8.0, 25.0) / kbar3_from_k2(1.0, 25.0)
    v = [kbar3_from_k2(1.0, km) for km in KM_LITERATURE.values()]
    r_km = max(v) / min(v)
    ck("the matrix is the larger uncertainty", r_km > r_k2,
       "k_m x%.2f vs k2 x%.2f" % (r_km, r_k2))

    # 7. porosity
    ck("zero porosity is a no-op",
       abs(porous_matrix(25.0, 0.0) - 25.0) < 1e-12)
    seq = [porous_matrix(25.0, p) for p in (0.0, 0.05, 0.1, 0.2, 0.3)]
    ck("porosity lowers the matrix conductivity monotonically",
       all(b < a for a, b in zip(seq[:-1], seq[1:])))
    p_need = solve_porosity(KBAR3_TARGET, 25.0)
    ck("solve_porosity inverts the forward map",
       p_need is not None
       and abs(kbar3_from_k2(1.0, 25.0, porosity=p_need)
               - KBAR3_TARGET) / KBAR3_TARGET < 1e-8,
       "p = %.4f" % p_need if p_need else "unreachable")
    ck("the gap needs LESS porosity than these materials actually have "
       "(so porosity comfortably covers it)",
       p_need is not None and 0.0 < p_need < POROSITY_REF22,
       "p = %.1f %% needed vs %.0f %% measured by refs/[22]"
       % (100 * p_need, 100 * POROSITY_REF22) if p_need else "unreachable")
    ck("the dense two-phase lower bound EXCEEDS the measurement "
       "(so porosity is required, not optional)",
       kbar3_from_k2(1.0, 25.0) > KBAR3_TARGET,
       "series %.2f > measured %.2f"
       % (kbar3_from_k2(1.0, 25.0), KBAR3_TARGET))

    # 8. WHICH porosity model.  Ch.4 4.9-3.
    KD = 25.0
    ck("Maxwell-Eucken and Landauer are both no-ops at p = 0",
       abs(maxwell_eucken(KD, 0.0) - KD) < 1e-9
       and abs(landauer(KD, 0.0) - KD) < 1e-9)
    ck("the general Landauer root matches its insulating-pore limit",
       abs(landauer(KD, 0.20, 1e-9) - landauer_insulating(KD, 0.20)) < 1e-6,
       "%.6f vs %.6f" % (landauer(KD, 0.20, 1e-9),
                         landauer_insulating(KD, 0.20)))
    ck("Landauer reaches zero at the p = 2/3 percolation threshold",
       abs(landauer_insulating(KD, 2.0 / 3.0)) < 1e-12)
    ck("Maxwell-Eucken has no percolation threshold (still conducts at 2/3)",
       maxwell_eucken(KD, 2.0 / 3.0) > 0.2 * KD,
       "%.2f W/(m.K) at p = 0.667" % maxwell_eucken(KD, 2.0 / 3.0))
    ck("open-pore Landauer always predicts less than closed-pore M-E",
       all(landauer(KD, p) < maxwell_eucken(KD, p)
           for p in (0.05, 0.1, 0.2, 0.3, 0.4)))
    ck("the two diverge only as porosity grows",
       (maxwell_eucken(KD, 0.40) / landauer(KD, 0.40))
       > 5.0 * (maxwell_eucken(KD, 0.05) / landauer(KD, 0.05) - 1.0) + 1.0,
       "ratio %.3f at p=0.05, %.3f at p=0.40"
       % (maxwell_eucken(KD, 0.05) / landauer(KD, 0.05),
          maxwell_eucken(KD, 0.40) / landauer(KD, 0.40)))

    p_me = porosity_for(maxwell_eucken, KBAR3_TARGET, KD)
    p_la = porosity_for(landauer, KBAR3_TARGET, KD)
    p_ra = solve_porosity(KBAR3_TARGET, KD)
    ck("all three porosity models reach the measured kbar3",
       None not in (p_me, p_la, p_ra),
       "M-E %.2f %%, Landauer %.2f %%, Rayleigh %.2f %%"
       % (100 * p_me, 100 * p_la, 100 * p_ra))
    spread = max(p_me, p_la, p_ra) / min(p_me, p_la, p_ra)
    ck("and at THIS porosity the choice barely matters (spread under 1.5x)",
       spread < 1.5, "%.2f x" % spread)
    ck("every one of them stays well under the 24 %% refs/[22] measured",
       max(p_me, p_la, p_ra) < 0.5 * POROSITY_REF22,
       "max %.2f %% vs %.0f %%" % (100 * max(p_me, p_la, p_ra),
                                   100 * POROSITY_REF22))
    print("""
  WHICH BRANCH, AND WHETHER IT MATTERS.  Smith et al., J. Mater. Res. 28(17)
  (2013) 2260-2272, find Maxwell-Eucken fits CLOSED porosity and Landauer
  fits OPEN porosity below p = 0.65; Wang et al., Int. J. Heat Mass Transfer
  49 (2006) 3075-3083, unify the five structural models these come from.

  The branch is already chosen by the rest of the thesis.  A CVI or PIP
  matrix leaves INTERCONNECTED pores -- which is precisely why oxygen
  reaches the PyC interphase and the carbon fibres, the mechanism Ch.2 2.5.4
  uses to set the sign of k in the cycle damage law.  Open porosity is a
  premise the damage model already rests on, so Landauer is the branch.

  But the honest result is that it does not matter here.  Reaching the
  measured kbar3 = %.2f needs %.2f %% (Landauer), %.2f %% (Maxwell-Eucken) or
  %.2f %% (Rayleigh) matrix porosity -- a spread of %.2f x, and all three far
  under the %.0f %% refs/[22] measured by X-ray CT.  At single-digit porosity
  the models have not yet separated: they differ by %.1f %% at p = 0.05 and
  only reach %.0f %% at p = 0.40.

  So 4.9-3 closes without a model argument.  What would have made the choice
  matter is a material needing tens of percent porosity, and this one does
  not.  The citation is still worth carrying, because "we checked and it did
  not matter" is a different statement from "we did not check".
""" % (KBAR3_TARGET, 100 * p_la, 100 * p_me, 100 * p_ra, spread,
       100 * POROSITY_REF22,
       100 * (maxwell_eucken(KD, 0.05) / landauer(KD, 0.05) - 1.0),
       100 * (maxwell_eucken(KD, 0.40) / landauer(KD, 0.40) - 1.0)))

    # 9. SAME-MATERIAL porosity, refs/[28] full text.  Ch.4 4.7.3 used to
    #    rest on refs/[22]'s 24 % -- a DIFFERENT material.  refs/[28] states
    #    10-15 % at COMPOSITE level for the same architecture, so the unit
    #    bases have to be converted before comparing.
    MATRIX_VOL = (1.0 - VY_RVE) + VY_RVE * (1.0 - VF_YARN)
    ck("matrix fraction complements the fibre fraction",
       abs(MATRIX_VOL + VY_RVE * VF_YARN - 1.0) < 1e-12,
       "matrix %.4f + fibre %.4f" % (MATRIX_VOL, VY_RVE * VF_YARN))

    needs = {"Rayleigh": p_ra, "Landauer": p_la, "Maxwell-Eucken": p_me}
    comp = {k: v * MATRIX_VOL for k, v in needs.items()}
    ck("matrix-level need converts to 2-4 % at composite level",
       all(0.02 < v < 0.04 for v in comp.values()),
       ", ".join("%s %.2f %%" % (k, 100 * v) for k, v in sorted(comp.items())))
    lo28, hi28 = POROSITY_REF28_COMPOSITE
    margin = lo28 / max(comp.values())
    ck("refs/[28]'s own 10-15 % covers the need with margin",
       margin > 2.5, "%.1f x even against the LOWER bound" % margin)
    inv_lo, inv_hi = lo28 / MATRIX_VOL, hi28 / MATRIX_VOL
    ck("inverse: [28] composite range maps to matrix-hosted %.1f-%.1f %%"
       % (100 * inv_lo, 100 * inv_hi),
       inv_lo < inv_hi, "")
    ck("and refs/[22]'s CT-measured 24 % falls inside that band",
       inv_lo <= POROSITY_REF22 <= inv_hi,
       "%.1f <= 24.0 <= %.1f" % (100 * inv_lo, 100 * inv_hi))
    # 10. refs/[28] IS INTERNALLY INCONSISTENT, and the resolution matters.
    #     Its own density and fibre content imply a different porosity from
    #     the one its text states.  Found via the analysis branch's density
    #     inversion (commit 012dca1), checked here independently.
    def porosity_from_density(rho, vf=0.40, rf=RHO_FIBRE_T300, rm=RHO_SIC):
        """rho = Vf*rho_f + Vm*rho_m  ->  porosity = 1 - Vf - Vm."""
        return 1.0 - vf - (rho - vf * rf) / rm

    def density_for_porosity(p, vf=0.40, rf=RHO_FIBRE_T300, rm=RHO_SIC):
        return vf * rf + (1.0 - vf - p) * rm

    p_inv = porosity_from_density(RHO_REF28)
    ck("density inversion of [28]'s own rho = 2.0 gives ~19.6 percent",
       abs(p_inv - 0.196) < 0.005, "%.1f %%" % (100 * p_inv))
    lo28, hi28 = POROSITY_REF28_COMPOSITE
    ck("that EXCEEDS [28]'s own stated 10-15 percent", p_inv > hi28,
       "%.1f %% vs stated %.0f-%.0f %%" % (100 * p_inv, 100 * lo28, 100 * hi28))
    rho_lo, rho_hi = density_for_porosity(hi28), density_for_porosity(lo28)
    ck("and rounding cannot explain it -- 10-15 %% needs rho = %.2f-%.2f"
       % (rho_lo, rho_hi), rho_lo > RHO_REF28 * 1.05,
       "%.0f-%.0f %% above the stated 2.0" % (100 * (rho_lo / RHO_REF28 - 1),
                                              100 * (rho_hi / RHO_REF28 - 1)))
    ck("the two readings bracket rather than contradict the need",
       max(comp.values()) < lo28 < p_inv,
       "need %.1f %% < open %.0f %% < total %.1f %%"
       % (100 * max(comp.values()), 100 * lo28, 100 * p_inv))
    print("""
  ** refs/[28] STATES TWO POROSITIES THAT DO NOT AGREE. **  Its text says
  10-15 %%; inverting its own bulk density of 2.0 g/cm3 at 40 %% fibre gives
  %.1f %%.  Rounding does not close that -- 10-15 %% would need 2.15-2.31
  g/cm3.  The likely reading is OPEN versus TOTAL: 10-15 %% is what an
  Archimedes immersion measures (connected pores only), the inversion gives
  total (connected + closed).  The paper's own "final deposition of the
  50 um SiC matrix ON THE SURFACE" -- a seal coat -- would lower measured
  open porosity while leaving total untouched, which fits.

  WHICH ONE TO USE, AND WHERE:
    conductivity (this file, Ch.4 4.7.3)  -> TOTAL, %.1f %%.  Closed pores
        impede heat exactly as open ones do.
    oxidation / the sign of k (Ch.2 2.5.4) -> OPEN, 10-15 %%.  Oxygen needs
        a connected path; closed pores are irrelevant to it.

  Either way the conductivity conclusion holds and gets stronger: the need
  is %.1f-%.1f %% at composite level, below BOTH readings.
""" % (100 * p_inv, 100 * p_inv,
       100 * min(comp.values()), 100 * max(comp.values())))

    print("""
  SAME-MATERIAL CLOSURE.  The porosity argument of Ch.4 4.7.3 no longer
  rests on a borrowed number.  refs/[28] states 10-15 %% porosity for the
  same 2D plain-woven CVI C/SiC.  The conductivity needs %.1f-%.1f %%
  MATRIX porosity, which is %.1f-%.1f %% at composite level -- covered by
  the measured range with a factor %.1f to spare.  Running the conversion
  the other way, 10-15 %% composite maps to %.0f-%.0f %% matrix-hosted,
  and refs/[22]'s independently CT-measured 24 %% sits inside it: two
  measurements on two materials by two methods agree once the unit bases
  are matched.

  ONE ASSUMPTION REMAINS: [28]'s figure is TOTAL porosity, including the
  large inter-bundle voids CVI leaves, not only matrix micropores.  For
  the question this section asks -- is there enough porosity to bring the
  through-thickness conductivity down -- the total is the right quantity,
  since inter-bundle voids impede that path too.
""" % (100 * min(needs.values()), 100 * max(needs.values()),
       100 * min(comp.values()), 100 * max(comp.values()),
       margin, 100 * inv_lo, 100 * inv_hi))

    print("\n%s" % ("ALL CONDUCTIVITY CHECKS PASS" if not fails
                    else "FAILED: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    sys.exit(main())
