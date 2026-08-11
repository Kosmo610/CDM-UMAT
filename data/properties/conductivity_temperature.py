#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conductivity_temperature.py  --  the SHAPE of kbar(T), and where it comes from
==============================================================================
a2-0027 (2)) asked a1 to adjudicate one number.  The macro thermal card carried
k(T) as a ratio borrowed from refs/[20] -- 2.04/3.49 = 0.5845 over 296-1473 K --
with the honest note that refs/[20] is a DIFFERENT material (8HSW laminate,
rho 2.64, Vf 46.4 %) and that a1 owns card legitimacy.  The three options put
to a1 were: find a primary source for 2D C/SiC k(T), approve the borrowing, or
declare constant k.

The ruling is none of the three: the shape is DERIVABLE from the card's own
constituent inputs, so nothing has to be borrowed.  This module derives it.

--------------------------------------------------------------------------
THE ARGUMENT, IN THE ORDER IT HAS TO BE READ
--------------------------------------------------------------------------
1.  The functional form is not a choice.  Snead Eq. (12) -- already in
    eval_correlations.sic_k_upper, already in the gate -- is

        1/k(T) = R0 + c.T          R0 = 3.0e-4,  c = 1.05e-5  [m.K/W]

    i.e. thermal RESISTIVITY linear in temperature.  R0 is the temperature
    INDEPENDENT part (defects, boundaries, interfaces); c.T is the Umklapp
    phonon term, the only part that falls with heating.

2.  A second primary source uses the same form for our own architecture.
    refs/[13], Katoh et al., Fusion Eng. Des. 81 (2006) 937-944, p. 941,
    modelling 2D CVI WOVEN composites:

        "linearly temperature dependent reciprocal thermal diffusivity was
         assumed for both matrix and fibers ... and the coefficient of
         thermal resistance was taken to be 0.01 s/cm2 K to fit the
         experimental data"

    So the form is not borrowed from anybody -- two independent primary
    sources agree on it, one of them on a 2D CVI woven composite.

3.  The card's matrix is NOT single-crystal SiC.  make_rve_conductivity.py
    builds the RVE on refs/[17]'s CVI SiC matrix, k_dense = 25 W/(m.K), and
    its own checker pins that value with the words "not Snead's 293".  Snead's
    single crystal is 293.4 W/(m.K) at 296 K.  Under the additive-resistance
    model of (1), a CVI matrix that conducts 11.7x worse than the single
    crystal does so because 91.5 % of its resistance is the T-INDEPENDENT
    term.  Only the remaining 8.5 % falls with temperature, so

        k_matrix(1473 K) / k_matrix(296 K) = 0.764

    NOT the 0.216 the single crystal would give.

4.  Push that through the same homogenisation that produced kbar_3 and the
    composite ratio is 0.78-0.84 across all four estimators.  The route
    validates itself: at 296 K the analytic hs_lo estimate is 5.514 W/(m.K)
    against the 5.449 the RVE_COND job actually computed -- 1.2 %.

5.  And now the borrowed number can be diagnosed instead of judged.  Running
    the same derivation with refs/[13]'s DENSER CVI matrix (70 W/(m.K))
    gives 0.55-0.61, which brackets the borrowed 0.5845 almost exactly.  So
    the borrowed shape is the shape of a composite whose matrix conducts
    2.8x better than the one our own card carries.  It is not merely from
    another material -- it CONTRADICTS our card from the inside.

6.  The direction is the bad one.  At 900 C, where the quench starts and the
    gradient peaks, the borrowed ratio puts kbar_3 at 3.76 against the
    derived 4.67, which raises Biot by 24 %.  A larger Biot means a larger
    predicted gradient, and "gradients matter" is exactly what contribution
    C2 sets out to show.  Borrowing therefore biases the thesis TOWARD its
    own claim, which is worse than a conservative error.

    Constant k (--no-kt) errs the other way by 14 %.  It is the smaller of
    the two errors -- a2's instinct that constant k is "not a neutral
    default" is right, but it is much less wrong than the borrowing.  With
    a derived shape available neither is needed.

--------------------------------------------------------------------------
WHAT IS ASSUMED, STATED SO IT CAN BE ATTACKED
--------------------------------------------------------------------------
* The resistance decomposition (step 3) assumes the whole 25-vs-293 gap is
  temperature independent.  This is the field's standard treatment -- Snead's
  review and refs/[13]'s irradiation fit (1/Krd = 0.119 - 1.13e-4 T) both add
  defect resistance to the lattice term.  If the assumption failed completely
  and the gap were all lattice, the ratio would be 0.216 instead of 0.82.
  That is the full span of the assumption, and it is reported, not hidden.
* Fibre transverse conductivity is held constant: no source gives its
  temperature dependence.  Fibre longitudinal follows refs/[09] through Cp
  and RISES 3.3x, which the derivation does include.
* Pore conduction is held at 0.025 W/(m.K).  Radiative transfer across pores
  grows as T^3 and would make the composite FLATTER still, so the derived
  ratio is a lower bound on flatness -- the true curve lies between the
  derived value and constant k, not below it.

Run:  python3 data/properties/conductivity_temperature.py --check
      python3 data/properties/conductivity_temperature.py --csv
"""
from __future__ import print_function

import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(os.path.dirname(HERE), "..", "abaqus")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "abaqus"))

import conductivity_bounds as cb          # noqa: E402
import eval_correlations as ec            # noqa: E402

# --------------------------------------------------------------------------
# Anchors.  Every one of these is a CONSTITUENT number or a value this repo
# already computes.  No composite measurement enters the derived path.
# --------------------------------------------------------------------------
#: The two temperatures refs/[20] tabulates.  Used ONLY to state the ratio we
#: are replacing, and to keep the comparison on the same interval.
T_COLD_K, T_HOT_K = 296.0, 1473.0

#: refs/[20] Table 1, YANG2024.  The number under adjudication.  It appears
#: here so it can be compared and rejected -- never on the derived path.
REF20_RATIO = 2.04 / 3.49

#: refs/[17] ZHANG2024 Table 3, the dense CVI SiC matrix the RVE deck is
#: actually built on (make_rve_conductivity.py --check pins it).
K_MATRIX_CVI = 25.0
#: refs/[13] KATOH2006 Table 2, a denser CVI SiC matrix.  Carried as the
#: other end of the matrix-value spread, not as our card.
K_MATRIX_CVI_DENSE = 70.0
#: Fibre, refs/[22]/[17] Table 1 -- axial and transverse, W/(m.K) at 296 K.
K_FIBRE_AXIAL, K_FIBRE_TRANS = 8.0, 1.0
#: The RVE_COND job's answer, W/(m.K) at 23 C.  Our own FE result, quoted
#: here only so the analytic route can be checked against it.
KBAR3_FE = 5.4490

MODELS = ("derived", "derived_dense_matrix", "ref20_linear_k",
          "ref20_resistance", "constant")


# --------------------------------------------------------------------------
# Snead's correlation, read back as a resistivity line
# --------------------------------------------------------------------------
def snead_resistivity_line():
    """(R0, c) of 1/k = R0 + c.T, recovered from eval_correlations.

    Recovered rather than re-typed: sic_k_upper is the single source of
    truth for those coefficients and a transcription here could drift from
    it silently.  Two points determine the line exactly because the form is
    known to be affine.
    """
    t1, t2 = 300.0, 1300.0
    r1, r2 = 1.0 / ec.sic_k_upper(t1), 1.0 / ec.sic_k_upper(t2)
    c = (r2 - r1) / (t2 - t1)
    return r1 - c * t1, c


def lattice_resistivity_ratio(T_K, T_ref_K=T_COLD_K):
    """R_lattice(T) / R_lattice(T_ref) for the SiC lattice."""
    r0, c = snead_resistivity_line()
    return (r0 + c * T_K) / (r0 + c * T_ref_K)


def t_independent_share(k_dense_296):
    """Fraction of a real matrix's 296 K resistance that does NOT fall with T.

    A matrix measured at k_dense_296 conducts worse than the single crystal.
    Under the additive model of the docstring the excess resistance is the
    temperature-independent term, so

        x = 1 - R_singlecrystal(296) / R_matrix(296)
          = 1 - k_dense_296 / k_singlecrystal(296)
    """
    return 1.0 - k_dense_296 / ec.sic_k_upper(T_COLD_K)


def matrix_k(T_K, k_dense_296=K_MATRIX_CVI):
    """Dense-matrix conductivity at T, W/(m.K), from the split above."""
    x = t_independent_share(k_dense_296)
    r_rel = x + (1.0 - x) * lattice_resistivity_ratio(T_K)
    return k_dense_296 / r_rel


# --------------------------------------------------------------------------
# Composite
# --------------------------------------------------------------------------
def matrix_porosity():
    """The RVE deck's own matrix porosity -- imported, never re-typed."""
    import make_rve_conductivity as mrc
    return mrc.matrix_porosity_from_composite()


def kbar3(T_K, estimator="hs_lo", k_dense_296=K_MATRIX_CVI, porosity=None):
    """Through-thickness composite conductivity at T, W/(m.K).

    Same homogenisation chain as conductivity_bounds: porous matrix -> yarn
    transverse (Rayleigh) -> plain-weave bracket.  Only the temperature
    enters here that the constituents themselves carry.
    """
    p = matrix_porosity() if porosity is None else porosity
    km = cb.porous_matrix(matrix_k(T_K, k_dense_296), p)
    k1 = K_FIBRE_AXIAL * ec.fibre_k_long(T_K) / ec.fibre_k_long(T_COLD_K)
    _k_long, k_trans = cb.yarn_conductivity(k1, K_FIBRE_TRANS, km)
    return cb.rve_kbar3(k_trans, km)[estimator]


def derived_ratio(estimator="hs_lo", k_dense_296=K_MATRIX_CVI):
    """kbar3(1473 K) / kbar3(296 K) from the constituents alone."""
    return kbar3(T_HOT_K, estimator, k_dense_296) / \
        kbar3(T_COLD_K, estimator, k_dense_296)


def derived_bracket(k_dense_296=K_MATRIX_CVI):
    """(min, max) of the ratio over the four homogenisation estimators."""
    r = [derived_ratio(e, k_dense_296)
         for e in ("series", "hs_lo", "hs_hi", "parallel")]
    return min(r), max(r)


# --------------------------------------------------------------------------
# The card scale factor -- what the deck generator should call
# --------------------------------------------------------------------------
def k_scale(T_C, model="derived", estimator="hs_lo"):
    """k(T) / k(23 C) for the macro thermal card.

    `derived` is the ruling.  The others exist so the sensitivity table in
    Ch.5 section 5.4.3 can be produced from one function instead of four
    hand-written columns:

      derived               ours, refs/[17] matrix          -> 0.82 at 1200 C
      derived_dense_matrix  ours, refs/[13] matrix          -> 0.55
      ref20_linear_k        what the deck carried, linear in k
      ref20_resistance      the same endpoint, resistivity-linear
      constant              --no-kt, the x = 1 end of the bracket
    """
    T_K = T_C + 273.15
    if model == "constant":
        return 1.0
    if model in ("derived", "derived_dense_matrix"):
        kd = K_MATRIX_CVI if model == "derived" else K_MATRIX_CVI_DENSE
        return kbar3(T_K, estimator, kd) / kbar3(23.0 + 273.15, estimator, kd)
    # the borrowed endpoint, interpolated the two possible ways
    f = (T_C - 23.0) / (T_HOT_K - T_COLD_K)
    if model == "ref20_linear_k":
        return 1.0 + f * (REF20_RATIO - 1.0)
    if model == "ref20_resistance":
        return 1.0 / (1.0 + f * (1.0 / REF20_RATIO - 1.0))
    raise ValueError("unknown model %r" % (model,))


def biot(T_C, h=161.7, half_thickness_m=1.5e-3, model="derived"):
    """Biot number at temperature, on our own card's h.

    h = 161.7 W/(m2.K) is what quench_calibration solves for refs/[03]'s
    cooling time ON OUR CARD.  Pairing it with anybody else's kbar_3 gives a
    number belonging to no material -- a2-0027 flags exactly that trap.
    """
    return h * half_thickness_m / (KBAR3_FE * k_scale(T_C, model))


# --------------------------------------------------------------------------
def summary_rows():
    """Rows for the CSV: value, basis, verdict, side by side."""
    lo, hi = derived_bracket()
    lo7, hi7 = derived_bracket(K_MATRIX_CVI_DENSE)
    b_der, b_r20, b_con = (biot(900.0, model=m)
                           for m in ("derived", "ref20_linear_k", "constant"))
    rows = [
        dict(quantity="k_matrix ratio 296->1473 K", value="%.4f"
             % (matrix_k(T_HOT_K) / K_MATRIX_CVI),
             basis="refs/[17] CVI SiC 25 W/(m.K) + Snead resistivity split",
             verdict="CARD", note="x = %.4f of resistance is T-independent"
             % t_independent_share(K_MATRIX_CVI)),
        dict(quantity="kbar3 ratio 296->1473 K (derived)",
             value="%.4f-%.4f" % (lo, hi),
             basis="same, through the RVE homogenisation, 4 estimators",
             verdict="CARD",
             note="spread %.4f -- robust to the estimator" % (hi - lo)),
        dict(quantity="kbar3(296 K) analytic vs FE",
             value="%.4f vs %.4f" % (kbar3(T_COLD_K), KBAR3_FE),
             basis="hs_lo estimator against LTH2_COND_P32",
             verdict="ROUTE VALIDATED",
             note="%.2f %% -- the derivation reproduces the FE job"
             % (100.0 * abs(kbar3(T_COLD_K) - KBAR3_FE) / KBAR3_FE)),
        dict(quantity="kbar3 ratio if the matrix were refs/[13]'s 70 W/(m.K)",
             value="%.4f-%.4f" % (lo7, hi7),
             basis="same derivation, denser CVI matrix",
             verdict="DIAGNOSIS",
             note="brackets the borrowed %.4f -- that shape assumes a matrix "
                  "our card does not carry" % REF20_RATIO),
        dict(quantity="refs/[20] borrowed ratio", value="%.4f" % REF20_RATIO,
             basis="refs/[20] Table 1, a composite measurement, 8HSW laminate",
             verdict="REJECTED FOR THE CARD",
             note="keep as a sensitivity row in Ch.5 5.4.3 only"),
        dict(quantity="Biot at 900 C, derived", value="%.4f" % b_der,
             basis="h = 161.7 W/(m2.K) solved on our own card",
             verdict="REFERENCE", note="kbar3 = %.3f W/(m.K)"
             % (KBAR3_FE * k_scale(900.0))),
        dict(quantity="Biot at 900 C, borrowed shape", value="%.4f" % b_r20,
             basis="same h, refs/[20] ratio",
             verdict="BIASED TOWARD C2",
             note="%+.1f %% vs derived -- over-predicts the gradient"
             % (100.0 * (b_r20 / b_der - 1.0))),
        dict(quantity="Biot at 900 C, constant k", value="%.4f" % b_con,
             basis="same h, --no-kt",
             verdict="SMALLER ERROR, STILL AN ERROR",
             note="%+.1f %% vs derived" % (100.0 * (b_con / b_der - 1.0))),
        dict(quantity="ratio if the T-independent split failed entirely",
             value="%.4f" % lattice_resistivity_ratio(T_HOT_K) ** -1,
             basis="all resistance treated as lattice (single crystal)",
             verdict="ASSUMPTION SPAN",
             note="the far end of the one assumption this derivation makes"),
    ]
    return rows


def write_csv(path=None):
    path = path or os.path.join(HERE, "conductivity_temperature_summary.csv")
    rows = summary_rows()
    with open(path, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["quantity", "value", "basis",
                                           "verdict", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path, len(rows)


# --------------------------------------------------------------------------
def check():
    ok, bad = [], []

    def t(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("conductivity_temperature.py --check")
    print(" A. the functional form is not a choice -- two primary sources")
    r0, c = snead_resistivity_line()
    t("Snead Eq.(12) is resistivity-linear, coefficients recovered",
      abs(r0 - 3.0e-4) < 1e-9 and abs(c - 1.05e-5) < 1e-12,
      "R0 = %.4e, c = %.4e" % (r0, c))
    worst = max(abs(1.0 / ec.sic_k_upper(T) - (r0 + c * T))
                for T in (300.0, 700.0, 1100.0, 1500.0, 2000.0))
    t("1/k is affine in T to machine precision over 300-2000 K",
      worst < 1e-15, "worst %.2e" % worst)
    t("the lattice term is what falls: R(1473)/R(296) > 4",
      lattice_resistivity_ratio(T_HOT_K) > 4.0,
      "%.4f" % lattice_resistivity_ratio(T_HOT_K))
    t("refs/[13] uses the same form on a 2D CVI WOVEN composite",
      "reciprocal thermal diffusivity" in __doc__
      and "937-944, p. 941" in __doc__)

    print("\n B. the card's matrix is CVI SiC, not the single crystal")
    t("the RVE deck is built on refs/[17]'s 25 W/(m.K)",
      _deck_matrix_k() == K_MATRIX_CVI, "%.1f W/(m.K)" % _deck_matrix_k())
    t("the single crystal is an order of magnitude above it",
      ec.sic_k_upper(T_COLD_K) / K_MATRIX_CVI > 10.0,
      "%.1fx" % (ec.sic_k_upper(T_COLD_K) / K_MATRIX_CVI))
    x = t_independent_share(K_MATRIX_CVI)
    t("so most of the matrix resistance is temperature-independent",
      0.90 < x < 0.93, "x = %.4f" % x)
    t("the matrix therefore falls only to ~0.76, not to 0.22",
      abs(matrix_k(T_HOT_K) / K_MATRIX_CVI - 0.764) < 0.005,
      "%.4f" % (matrix_k(T_HOT_K) / K_MATRIX_CVI))
    t("t_independent_share is 0 for the single crystal itself",
      abs(t_independent_share(ec.sic_k_upper(T_COLD_K))) < 1e-12)
    t("and the single crystal then reproduces Snead's own ratio",
      abs(matrix_k(T_HOT_K, ec.sic_k_upper(T_COLD_K))
          / ec.sic_k_upper(T_COLD_K) - 0.2162) < 5e-4,
      "%.4f" % (matrix_k(T_HOT_K, ec.sic_k_upper(T_COLD_K))
                / ec.sic_k_upper(T_COLD_K)))

    print("\n C. the composite ratio, and the route that validates itself")
    lo, hi = derived_bracket()
    t("derived ratio is 0.78-0.84 across all four estimators",
      0.77 < lo and hi < 0.85, "%.4f - %.4f" % (lo, hi))
    t("the estimator spread is small -- the shape is robust where the "
      "magnitude is not", hi - lo < 0.10, "spread %.4f" % (hi - lo))
    err = abs(kbar3(T_COLD_K) - KBAR3_FE) / KBAR3_FE
    t("the analytic route reproduces the RVE_COND job at 296 K",
      err < 0.02, "%.4f vs %.4f, %.2f %%"
      % (kbar3(T_COLD_K), KBAR3_FE, 100.0 * err))
    t("kbar3 falls monotonically with temperature",
      all(kbar3(a) > kbar3(b) for a, b in
          ((300.0, 600.0), (600.0, 900.0), (900.0, 1200.0), (1200.0, 1500.0))))
    t("the porosity comes from the RVE deck, not from this file",
      abs(matrix_porosity() - 0.3242) < 5e-4, "%.4f" % matrix_porosity())

    print("\n D. what the borrowed number actually was")
    lo7, hi7 = derived_bracket(K_MATRIX_CVI_DENSE)
    t("with refs/[13]'s denser matrix the derivation gives 0.55-0.61",
      0.54 < lo7 and hi7 < 0.62, "%.4f - %.4f" % (lo7, hi7))
    t("that range brackets the borrowed 0.5845",
      lo7 <= REF20_RATIO <= hi7, "%.4f in [%.4f, %.4f]"
      % (REF20_RATIO, lo7, hi7))
    t("so the borrowed shape presumes a matrix our card does not carry",
      not (lo <= REF20_RATIO <= hi),
      "0.5845 sits outside our own %.4f-%.4f" % (lo, hi))
    t("the two refs disagree on the CVI matrix by ~2.8x, which is the "
      "real source of the gap",
      abs(K_MATRIX_CVI_DENSE / K_MATRIX_CVI - 2.8) < 0.05)

    print("\n E. direction: which way each choice is wrong")
    b_der = biot(900.0, model="derived")
    b_r20 = biot(900.0, model="ref20_linear_k")
    b_con = biot(900.0, model="constant")
    t("the borrowed shape RAISES the 900 C Biot",
      b_r20 > b_der, "%.4f vs %.4f, %+.1f %%"
      % (b_r20, b_der, 100.0 * (b_r20 / b_der - 1.0)))
    t("and it does so by more than 20 % -- toward C2's own claim",
      b_r20 / b_der - 1.0 > 0.20, "%+.1f %%"
      % (100.0 * (b_r20 / b_der - 1.0)))
    t("constant k errs the other way and by less",
      b_con < b_der and abs(b_con / b_der - 1.0) < abs(b_r20 / b_der - 1.0),
      "%+.1f %% vs %+.1f %%" % (100.0 * (b_con / b_der - 1.0),
                                100.0 * (b_r20 / b_der - 1.0)))
    t("every model agrees at the reference temperature",
      all(abs(k_scale(23.0, m) - 1.0) < 1e-9 for m in MODELS))
    t_end = 23.0 + (T_HOT_K - T_COLD_K)      # where f = 1 exactly
    t("the two interpolations of the borrowed endpoint meet at both ends",
      abs(k_scale(t_end, "ref20_linear_k")
          - k_scale(t_end, "ref20_resistance")) < 1e-9
      and abs(k_scale(t_end, "ref20_linear_k") - REF20_RATIO) < 1e-9,
      "both %.4f at %.2f C" % (k_scale(t_end, "ref20_linear_k"), t_end))
    mid = abs(k_scale(500.0, "ref20_linear_k")
              - k_scale(500.0, "ref20_resistance"))
    t("but they differ in the middle -- the form is not cosmetic",
      mid > 0.04, "%.4f at 500 C" % mid)
    t("the derived shape lies between the borrowed one and constant k",
      k_scale(900.0, "ref20_linear_k") < k_scale(900.0, "derived")
      < k_scale(900.0, "constant"),
      "%.4f < %.4f < 1" % (k_scale(900.0, "ref20_linear_k"),
                           k_scale(900.0, "derived")))

    print("\n F. the derived path touches no composite measurement")
    import inspect
    src = "".join(inspect.getsource(f) for f in
                  (matrix_k, kbar3, derived_ratio, t_independent_share,
                   lattice_resistivity_ratio, snead_resistivity_line))
    t("no refs/[20] constant appears on the derived path",
      "REF20" not in src and "2.04" not in src and "3.49" not in src)
    t("no composite measurement appears on the derived path",
      "6.29" not in src and "KBAR3_FE" not in src)
    t("kbar3(23 C) is used only to check the route, never to build it",
      "KBAR3_FE" not in inspect.getsource(k_scale))
    t("the borrowed ratio is still named, so the rejection is auditable",
      abs(REF20_RATIO - 0.5845) < 1e-4, "%.4f" % REF20_RATIO)

    print("\n G. the assumption, and its full span")
    t("if the split failed entirely the ratio would be 0.216",
      abs(1.0 / lattice_resistivity_ratio(T_HOT_K) - 0.2162) < 5e-4,
      "%.4f" % (1.0 / lattice_resistivity_ratio(T_HOT_K)))
    t("the docstring states the assumption and its span",
      "0.216 instead of 0.82" in __doc__)
    t("the docstring states the two held-constant properties",
      "Fibre transverse conductivity is held constant" in __doc__
      and "Pore conduction is held" in __doc__)

    print("\n H. the CSV a1 and a2 both read")
    path, n = write_csv(os.path.join(HERE,
                                     "conductivity_temperature_summary.csv"))
    with open(path) as fh:
        text = fh.read()
    t("the summary CSV is written", n >= 9 and os.path.exists(path),
      "%d rows -> %s" % (n, os.path.basename(path)))
    t("every row carries value, basis and verdict side by side",
      all(c in text.splitlines()[0] for c in
          ("quantity", "value", "basis", "verdict")))
    t("the CSV states the ruling in a machine-readable column",
      "REJECTED FOR THE CARD" in text and "CARD" in text)
    t("the CSV records the route validation, not only the answer",
      "ROUTE VALIDATED" in text)

    print("\n" + "=" * 74)
    if bad:
        print("FAILED %d of %d: %s" % (len(bad), len(ok) + len(bad),
                                       ", ".join(bad[:3])))
        return 1
    print("ALL %d CONDUCTIVITY-SHAPE CHECKS PASS" % len(ok))
    print("=" * 74)
    return 0


def _deck_matrix_k():
    """The dense matrix conductivity the RVE deck actually defaults to.

    Read from the deck generator's own --k-matrix default rather than from
    its output, so that changing the default there fails this check here
    instead of silently re-basing the shape derived above.
    """
    import re
    import make_rve_conductivity as mrc
    src = open(mrc.__file__.replace(".pyc", ".py")).read()
    m = re.search(r'"--k-matrix"[^)]*?default=([0-9.]+)', src, re.S)
    return float(m.group(1))


def report():
    lo, hi = derived_bracket()
    print("=" * 74)
    print("k(T) SHAPE FOR THE MACRO THERMAL CARD -- a2-0027 (2)) adjudicated")
    print("=" * 74)
    print("  matrix (refs/[17] CVI SiC, 25 W/(m.K)):  "
          "T-independent share %.3f, ratio %.4f"
          % (t_independent_share(K_MATRIX_CVI),
             matrix_k(T_HOT_K) / K_MATRIX_CVI))
    print("  composite kbar3 ratio 296->1473 K:       %.4f - %.4f  (derived)"
          % (lo, hi))
    print("  route check at 296 K:                    %.4f analytic vs "
          "%.4f FE" % (kbar3(T_COLD_K), KBAR3_FE))
    print("  refs/[20] borrowed ratio:                %.4f  REJECTED"
          % REF20_RATIO)
    print()
    print("  %-9s %9s %9s %9s %9s" % ("T [C]", "derived", "refs[20]",
                                      "refs[20]R", "constant"))
    for T in (23.0, 300.0, 500.0, 900.0, 1200.0):
        print("  %-9.0f %9.4f %9.4f %9.4f %9.4f"
              % (T, k_scale(T, "derived"), k_scale(T, "ref20_linear_k"),
                 k_scale(T, "ref20_resistance"), 1.0))
    print()
    for m in ("derived", "ref20_linear_k", "constant"):
        print("  Biot at 900 C, %-16s %.4f" % (m, biot(900.0, model=m)))
    print("=" * 74)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    if a.csv:
        path, n = write_csv()
        print("wrote %s (%d rows)" % (path, n))
        return 0
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
