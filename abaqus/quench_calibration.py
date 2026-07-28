#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quench_calibration.py
=====================
Turn the published thermal-shock protocols into film coefficients, and say
how big the through-thickness gradient they actually produce is.

Why this exists
---------------
`make_macro_thermalshock.py` had three severity levels whose film
coefficients h were round numbers picked to look plausible, and one of them
was labelled "ZHANG2013 reference" without anyone having checked it against
what refs/[03] did.  h is not a free parameter: both validation papers state
their cooling protocol precisely enough to solve for it.

  refs/[03] Zhang 2013   2D C/SiC, 122 x 6(gauge) x 3 mm, tensile
                         900 C hold 10 min -> 300 C in 15 s ON AN IRON
                         PLATE, "estimated cooling rate about 40 C/s",
                         static air, repeat.  NOTE: contact cooling, not
                         free convection -- h here is a contact conductance
                         standing in for the plate, and no air-convection
                         correlation applies.
  refs/[02] Yin 2002     3D C/SiC, 4 x 6 x 140 mm, 3-point bend span 20 mm
                         burner rig 30 s, then 60 s cooling in air,
                         dT = 1000 C (1300 -> 300).

What comes out of it -- and it reframes the thesis
--------------------------------------------------
Solving for h and then evaluating the Biot number shows that the refs/[03]
test runs at Bi ~ 0.05.  At that Biot number the plate is very nearly
isothermal: the centre-to-surface difference is a couple of tens of degrees
out of a 600 C drop.  So for the experiment we validate against, damage is
driven mostly by the UNIFORM temperature change acting on the constituent
CTE mismatch, not by a spatial gradient.

That is worth knowing BEFORE running anything, because it changes the
claim.  "We resolve the spatial gradient that others assume away" is weak
if the gradient is 20 C.  The defensible version is:

    the uniform-temperature assumption used by refs/[17] is quantitatively
    fine at low Biot number and fails above some Bi -- we find where.

which turns the severity ladder from three arbitrary h values into a sweep
in Bi that brackets the crossover.  That is a stronger contribution and it
is measurable.

Run:  python3 abaqus/quench_calibration.py
      python3 abaqus/quench_calibration.py --check
"""
from __future__ import print_function

import math
import sys

# ==========================================================================
# Material thermal properties, SI (W, m, K, kg, J).
# k3 is the through-thickness conductivity -- the one that matters here.
# See data/literature/thermal_conductivity.csv and
# data/properties/conductivity_bounds.py.
# ==========================================================================
MATERIALS = {
    "zhang2013": dict(
        rho=2050.0,        # refs/[03] states 2.05 g/cm3 for its 2D C/SiC
        cp=820.0,          # refs/[20] Table 1, CMC laminate at RT
        k3=6.29,           # refs/[12], measured C/SiC through-thickness
        note="refs/[03] density; cp from refs/[20]; k from refs/[12]"),
    "zhang2013_lowk": dict(
        rho=2050.0, cp=820.0, k3=3.49,
        note="same, but with the refs/[20] laminate conductivity -- the "
             "low end of the plausible range, kept as a sensitivity case"),
    "zhang2013_hot": dict(
        rho=2050.0, cp=1270.0, k3=2.04,
        note="refs/[20] values at 1473 K: cp rises and k falls with "
             "temperature, both of which SLOW the quench"),
}

# ==========================================================================
# Published protocols.  `t_target` and `T_target` are what the paper states.
# ==========================================================================
SPECIMENS = {
    "ZHANG2013": dict(
        material="zhang2013",
        thickness=3.0e-3,       # m, from Fig. 1
        width=6.0e-3,           # gauge width
        gauge=12.5e-3,          # parallel length
        overall=122.0e-3,
        T_hi=900.0, T_lo=300.0,
        T_sink=25.0,            # the iron plate starts at room temperature
        t_target=15.0,          # s, "cooled to 300 C within 15 s"
        T_target=300.0,
        t_hold_hot=600.0,       # 10 min in the furnace
        cooling="contact with an iron plate",
        test="tension, ASTM C1275, 0.5 mm/min, 25 mm extensometer",
        cycles=(0, 20, 40, 60),
        note="refs/[03] section 2.2; the paper's own estimate of the "
             "cooling rate is about 40 C/s"),
    "YIN2002": dict(
        material="zhang2013",   # 3D C/SiC; same class, properties not given
        thickness=4.0e-3,
        width=6.0e-3,
        gauge=20.0e-3,          # 3-point bend span
        overall=140.0e-3,
        T_hi=1300.0, T_lo=300.0,
        T_sink=25.0,
        t_target=60.0,          # "cooled in an air atmosphere for 60 s"
        T_target=300.0,
        t_hold_hot=30.0,        # 30 s in the burner
        cooling="free convection in air",
        test="3-point bend, span 20 mm, 0.5 mm/min",
        cycles=(0, 20, 50, 100),
        note="refs/[02] section 2.2.  Air cooling over 60 s is far gentler "
             "than the refs/[03] iron plate, so the two datasets sit at "
             "DIFFERENT Biot numbers -- they are not interchangeable"),
}


# ==========================================================================
# 1-D transient conduction in a plate cooled on both faces
# ==========================================================================
def _eigenvalues(bi, n=12):
    """Roots of  lambda * tan(lambda) = Bi  (symmetric plate, convection)."""
    out = []
    for k in range(n):
        lo = k * math.pi + 1.0e-9
        hi = lo + math.pi / 2.0 - 1.0e-9

        def f(x):
            return x * math.sin(x) - bi * math.cos(x)

        a, b = lo, hi
        fa = f(a)
        for _ in range(200):
            m = 0.5 * (a + b)
            fm = f(m)
            if fa * fm <= 0.0:
                b = m
            else:
                a, fa = m, fm
        out.append(0.5 * (a + b))
    return out


def theta(bi, fo, xi=0.0, n=12):
    """Dimensionless excess temperature (T-Tinf)/(T0-Tinf).

    xi = x/L, 0 at the mid-plane and 1 at the surface.
    """
    s = 0.0
    for lam in _eigenvalues(bi, n):
        c = 4.0 * math.sin(lam) / (2.0 * lam + math.sin(2.0 * lam))
        s += c * math.exp(-lam * lam * fo) * math.cos(lam * xi)
    return s


def solve_h(spec, mat, n=12):
    """Film coefficient that reproduces the paper's stated cooling time.

    Solved on the exact series solution rather than the lumped
    approximation, so it stays valid if the answer turns out to be a high
    Biot number.
    """
    L = 0.5 * spec["thickness"]
    alpha = mat["k3"] / (mat["rho"] * mat["cp"])
    fo = alpha * spec["t_target"] / (L * L)
    want = ((spec["T_target"] - spec["T_sink"])
            / (spec["T_hi"] - spec["T_sink"]))

    def mid(bi):
        return theta(bi, fo, 0.0, n)

    lo, hi = 1.0e-6, 1.0e6
    if mid(hi) > want:
        return None, fo          # even an infinite h is too slow
    for _ in range(300):
        m = math.sqrt(lo * hi)
        if mid(m) > want:
            lo = m
        else:
            hi = m
    bi = math.sqrt(lo * hi)
    return bi * mat["k3"] / L, fo


def gradient(spec, mat, h, n=12):
    """Peak centre-to-surface temperature difference during the quench, K."""
    L = 0.5 * spec["thickness"]
    alpha = mat["k3"] / (mat["rho"] * mat["cp"])
    bi = h * L / mat["k3"]
    dT = spec["T_hi"] - spec["T_sink"]
    worst, t_worst = 0.0, 0.0
    steps = 400
    for i in range(1, steps + 1):
        t = spec["t_target"] * i / float(steps)
        fo = alpha * t / (L * L)
        d = dT * (theta(bi, fo, 0.0, n) - theta(bi, fo, 1.0, n))
        if d > worst:
            worst, t_worst = d, t
    return worst, t_worst, bi


# ==========================================================================
def report():
    print("=" * 74)
    print("QUENCH CALIBRATION -- film coefficients from the published tests")
    print("=" * 74)

    results = {}
    for key in ("ZHANG2013", "YIN2002"):
        spec = SPECIMENS[key]
        mat = MATERIALS[spec["material"]]
        print("\n%s   %s" % (key, spec["cooling"]))
        print("  specimen  %.1f x %.1f x %.1f mm (thickness x width x length)"
              % (1e3 * spec["thickness"], 1e3 * spec["width"],
                 1e3 * spec["overall"]))
        print("  protocol  %.0f -> %.0f C, stated to reach %.0f C in %.0f s"
              % (spec["T_hi"], spec["T_lo"], spec["T_target"],
                 spec["t_target"]))
        print("  mean rate %.1f C/s" % ((spec["T_hi"] - spec["T_target"])
                                        / spec["t_target"]))
        h, fo = solve_h(spec, mat)
        if h is None:
            print("  !! no finite h reproduces this: conduction alone is "
                  "too slow (Fo = %.2f)" % fo)
            continue
        worst, t_worst, bi = gradient(spec, mat, h)
        results[key] = dict(h=h, bi=bi, fo=fo, grad=worst)
        print("  -> h  = %8.1f W/(m^2.K)   = %.4g W/(mm^2.K) for the deck"
              % (h, h * 1.0e-6))
        print("  -> Bi = %8.4f            Fo(at t_target) = %.1f" % (bi, fo))
        print("  -> peak centre-to-surface gradient %.1f K at t = %.2f s"
              % (worst, t_worst))
        print("     that is %.1f %% of the %.0f K total drop"
              % (100.0 * worst / (spec["T_hi"] - spec["T_lo"]),
                 spec["T_hi"] - spec["T_lo"]))

    # ---- sensitivity to the conductivity, which P2 left as a range ------
    print("\n" + "-" * 74)
    print("SENSITIVITY: the same protocol with the plausible range of k")
    print("-" * 74)
    spec = SPECIMENS["ZHANG2013"]
    print("  %-22s %-10s %-10s %-10s %-12s"
          % ("k3 W/(m.K)", "h", "Bi", "grad K", "source"))
    for name in ("zhang2013", "zhang2013_lowk", "zhang2013_hot"):
        mat = MATERIALS[name]
        h, _fo = solve_h(spec, mat)
        if h is None:
            continue
        worst, _t, bi = gradient(spec, mat, h)
        print("  %-22.2f %-10.1f %-10.4f %-10.1f %-12s"
              % (mat["k3"], h, bi, worst, name))
    print("""
  READ THIS ROW BY ROW, NOT AS AN AVERAGE.  The gradient runs from 20 K
  (3 % of the drop) on room-temperature properties to 92 K (15 %) on the
  1473 K properties of refs/[20] -- a factor of 4.6 from the property
  choice alone.  And the hot row is the physically relevant one at the
  START of the quench, which is exactly when the gradient peaks: the
  specimen leaves the furnace at 900 C.

  Two consequences, both of which change what we do:
  * The conclusion that survives the whole range is the WEAKER one --
    Bi < 0.25, so the gradient is a minority of the drop, never that it
    is negligible.  15 % of 600 K is 92 K and that is not nothing.
  * Temperature-dependent thermal properties change the predicted
    gradient by more than a factor of four.  That is an argument FOR the
    f(T) machinery already in the UMAT, and it means the heat-transfer
    job must use temperature-dependent k and cp, not RT constants.""")

    # ---- the severity ladder --------------------------------------------
    print("\n" + "=" * 74)
    print("SEVERITY LADDER -- sweep the Biot number, not arbitrary h")
    print("=" * 74)
    mat = MATERIALS["zhang2013"]
    L = 0.5 * spec["thickness"]
    print("  %-6s %-10s %-14s %-12s %-12s"
          % ("Bi", "h W/m2K", "h W/mm2K", "grad K", "% of drop"))
    ladder = []
    for bi in (0.05, 0.2, 1.0, 5.0, 20.0):
        h = bi * mat["k3"] / L
        worst, _t, _b = gradient(spec, mat, h)
        ladder.append((bi, h, worst))
        print("  %-6.2f %-10.1f %-14.4g %-12.1f %-12.1f"
              % (bi, h, h * 1.0e-6, worst,
                 100.0 * worst / (spec["T_hi"] - spec["T_lo"])))
    print("""
  Bi = 0.05 is where refs/[03] actually sits, and there the gradient is a
  few percent of the drop -- the uniform-field assumption of refs/[17] is
  essentially correct at that severity.  By Bi = 5 the gradient is a large
  fraction of the drop and the assumption cannot survive.  The crossover
  in between is the quantity worth reporting, and it is what the three
  macro severity levels should bracket.

  RECOMMENDED SEVERITIES for make_macro_thermalshock.py:
    L  Bi ~ 0.05   the refs/[03] validation point, essentially uniform
    M  Bi ~ 1      the crossover
    H  Bi ~ 5      gradient dominated
  Note the deck wants W/(mm^2.K): divide the SI value by 1e6.""")
    return results


# ==========================================================================
def check():
    fails = []

    def ck(name, ok, detail=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("  " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    # 1. the series solution must satisfy its own eigenvalue equation
    worst = 0.0
    for bi in (0.01, 0.1, 1.0, 10.0, 100.0):
        for lam in _eigenvalues(bi, 8):
            worst = max(worst, abs(lam * math.sin(lam) - bi * math.cos(lam)))
    ck("eigenvalues satisfy lambda tan(lambda) = Bi", worst < 1e-9,
       "worst residual %.2e" % worst)

    # 2. at t = 0 the plate is uniformly at T0 everywhere
    worst = max(abs(theta(bi, 1e-9, xi, 200) - 1.0)
                for bi in (0.05, 1.0) for xi in (0.0, 0.5, 1.0))
    ck("theta -> 1 as Fo -> 0", worst < 0.02, "worst %.4f" % worst)

    # 3. small Biot must agree with the lumped-capacitance answer
    bi, fo = 0.02, 3.0
    lumped = math.exp(-bi * fo)
    ck("small Bi reduces to the lumped solution",
       abs(theta(bi, fo, 0.0) - lumped) / lumped < 0.02,
       "series %.5f vs lumped %.5f" % (theta(bi, fo, 0.0), lumped))

    # 4. the surface is always colder than the mid-plane while cooling
    bad = [(bi, fo) for bi in (0.05, 1.0, 10.0)
           for fo in (0.01, 0.1, 0.5, 2.0)
           if theta(bi, fo, 1.0) > theta(bi, fo, 0.0) + 1e-12]
    ck("the surface leads the mid-plane at every Bi and Fo", not bad,
       "%d violations" % len(bad))

    # 5. the solver must invert its own forward model
    worst = 0.0
    for key, spec in SPECIMENS.items():
        mat = MATERIALS[spec["material"]]
        h, _fo = solve_h(spec, mat)
        if h is None:
            fails.append(key + " unsolvable")
            continue
        L = 0.5 * spec["thickness"]
        alpha = mat["k3"] / (mat["rho"] * mat["cp"])
        fo = alpha * spec["t_target"] / (L * L)
        got = (spec["T_hi"] - spec["T_sink"]) * theta(h * L / mat["k3"], fo)
        got += spec["T_sink"]
        worst = max(worst, abs(got - spec["T_target"]))
    ck("solve_h reproduces the stated cooling time", worst < 0.1,
       "worst error %.4f C" % worst)

    # 6. the gradient must grow with Bi -- the claim the ladder rests on
    mat = MATERIALS["zhang2013"]
    spec = SPECIMENS["ZHANG2013"]
    L = 0.5 * spec["thickness"]
    g = [gradient(spec, mat, bi * mat["k3"] / L)[0]
         for bi in (0.05, 0.2, 1.0, 5.0, 20.0)]
    ck("the through-thickness gradient increases with Bi",
       all(b > a for a, b in zip(g[:-1], g[1:])),
       "%s K" % ", ".join("%.0f" % v for v in g))

    # 7. THE finding, asserted so it cannot rot
    h, _ = solve_h(spec, mat)
    worst_g, _t, bi = gradient(spec, mat, h)
    frac = worst_g / (spec["T_hi"] - spec["T_lo"])
    ck("refs/[03] runs at low Biot number", bi < 0.1, "Bi = %.4f" % bi)
    ck("and its through-thickness gradient is a small part of the drop",
       frac < 0.10, "%.1f K = %.1f %% of %.0f K"
       % (worst_g, 100 * frac, spec["T_hi"] - spec["T_lo"]))
    # What survives the whole property range is the weaker claim: Bi stays
    # below ~0.25 and the gradient stays a minority of the drop.  It is NOT
    # true that the gradient is negligible on hot properties.
    bis, fracs = [], []
    for m in ("zhang2013", "zhang2013_lowk", "zhang2013_hot"):
        hh, _ = solve_h(SPECIMENS["ZHANG2013"], MATERIALS[m])
        g, _t, bb = gradient(SPECIMENS["ZHANG2013"], MATERIALS[m], hh)
        bis.append(bb)
        fracs.append(g / (spec["T_hi"] - spec["T_lo"]))
    ck("Bi stays below 0.25 across the conductivity range",
       max(bis) < 0.25 + 1e-9, "max Bi = %.4f" % max(bis))
    ck("the gradient stays a MINORITY of the drop across the range",
       max(fracs) < 0.25, "max %.1f %%" % (100 * max(fracs)))
    ck("but the property choice moves the gradient by more than 3x "
       "(so f(T) thermal properties are required, not optional)",
       max(fracs) / min(fracs) > 3.0,
       "%.1f %% .. %.1f %%" % (100 * min(fracs), 100 * max(fracs)))

    # 8. the two papers must NOT land at the same severity
    hz, _ = solve_h(SPECIMENS["ZHANG2013"], MATERIALS["zhang2013"])
    hy, _ = solve_h(SPECIMENS["YIN2002"], MATERIALS["zhang2013"])
    ck("the two validation tests sit at different severities",
       hz / hy > 2.0, "h(ZHANG2013) = %.0f vs h(YIN2002) = %.0f W/(m2.K)"
       % (hz, hy))

    print("\n%s" % ("ALL QUENCH CHECKS PASS" if not fails
                    else "FAILED: " + ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    report()
    sys.exit(0)
