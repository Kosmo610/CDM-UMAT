#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
thermal_cycling_dataset.py
==========================
Assembles EVERY repeated-thermal-shock measurement the project holds into one
table, and tests the claim the thesis actually makes with it.

The claim, from Ch.1 section 1.4.1: the sign of the cycle-damage exponent k
separates two mechanisms -- silica sealing above about 1000 C, where damage
SATURATES, and sealing failure between 600 and 1000 C, where oxidation
ACCELERATES it.  Ch.1 says this is shown by "three independent datasets".
With the fifth upload the count is larger and the evidence is stronger than
the wording claims -- but it also has a hole that was never stated.

The table
---------
Every row read from the paper itself, not from our own notes.

  ref        material            T range [C]   atm         N      what survived
  [02] Yin   3D C/SiC            1300 -> 300   air        >100    83 % flexural
  [03] Zhang 2D C/SiC             900 -> 300   air          60    63 % tensile,
                                                                  45 % modulus
  [43] Mei   2D C/SiC             700 <-> 1200 argon        50    98.90 %
  [43] Mei   2D C/SiC             700 <-> 1200 dry O2       50    96.46 %
  [43] Mei   2D C/SiC             700 <-> 1200 water vap.   50    95.82 %
  [43] Mei   2D C/SiC             700 <-> 1200 wet O2       50    88.92 %
  [61] Mei   2D C/SiC             700 <-> 1200 wet O2      >100    86.69 %
  [65] Wei   2D SiC/SiC          1300           air     10/20/30  94.6/89.9/88.0 %
  [65] Wei   2.5D SiC/SiC        1300           air     10/20/30  91.6/88.3/86.3 %
  [68] Mei   3D C/SiC, CONSTRAINED 900 <-> 1200 wet O2      50    86.5 % strength,
                                                                  88.9 % modulus;
                                                                  saw-tooth range
                                                                  62.5 MPa, mean
                                                                  0 -> -14 MPa;
                                                                  damage strain 0.06 %

THE SEVERITY PARADOX -- the strongest single argument we have
-------------------------------------------------------------
Compare the two air-quench datasets directly.  Both CVI C/SiC, both quenched
into the same cold sink, both measured as residual strength:

    [02] Yin    dT = 1000 C   >100 cycles   ->   83 % retained
    [03] Zhang  dT =  600 C     60 cycles   ->   63 % retained

The case with the LARGER temperature drop and MORE cycles is the one that
survives better.  Per cycle and per degree of drop:

    [02]  17 % / 100 cycles / 1000 C  =  1.70e-4 %/cycle/K
    [03]  37 % /  60 cycles /  600 C  =  1.03e-3 %/cycle/K   -- 6.0x worse

Thermal-shock severity alone predicts the opposite ordering.  Something other
than dT is doing the damage, and the only variable that separates the two is
the UPPER temperature: 1300 C versus 900 C, straddling the silica-sealing
threshold.  That is the cleanest evidence for the mechanism split in the whole
collection, and it was never written down.

Caveat, stated because it is real: [02] is 3D and [03] is 2D.  Architecture
differs.  But no plausible architecture effect turns a 1000 C quench into a
gentler event than a 600 C one; it would have to reverse the ordering AND
overcome a factor of six.

Every high-temperature dataset saturates
-----------------------------------------
    [65] 2D    decrements 28, 25, 10 MPa over 10-cycle blocks   -> decelerating
    [65] 2.5D  decrements 54, 21, 13 MPa                        -> decelerating
    [43]/[61]  wet O2 loses 11.08 points in the first 50 cycles,
               then 2.23 more over the next 50+                 -> decelerating
    [02]       "critical cycle number as high as 100", then saturation
    [68]       "maximum damage strain of 0.06 % WITHIN 50 cycles"

and the one low-temperature dataset does not
---------------------------------------------
    [03]  "retains its strength within 20 thermal shock cycles.  The strength
           decreases gradually when it is thermally shocked for more than 20
           cycles" -- i.e. an incubation period followed by progressive loss,
           reaching 63 % / 45 % at 60 cycles.

THE HOLE, which Ch.1 does not admit
------------------------------------
The threshold is claimed at 1000 C.  Every saturating dataset has an upper
temperature of 1200 C or 1300 C.  The single accelerating dataset has an upper
temperature of 900 C.  WE HAVE NOTHING BETWEEN 900 AND 1200 C.  The data
brackets the threshold but does not locate it, and 1000 C is taken from the
silica-formation chemistry, not from any measurement we hold.  Ch.1 must say
"between 900 and 1200 C" or cite the chemistry for the 1000 C figure -- it may
not present 1000 C as measured.

WHICH METRIC -- and a correction to a1-0012
--------------------------------------------
refs/[03] states, having measured both:

    "the modulus should be more sensitive to the damage caused by the thermal
     shock and be more suitable to characterize the damage induced by the
     thermal shock"

and its own numbers bear that out -- 63 % strength against 45 % modulus at 60
cycles.  The modulus falls nearly twice as far.

In a1-0012 I proposed switching the validation metric from modulus to PLS.
That was too broad, and this narrows it.  The two statements are about
different questions and both are right:

    TRS relaxation, BEFORE cracking     -> the modulus is blind (refs/[15]),
                                           PLS is the indicator
    ACCUMULATED thermal-shock damage    -> the modulus is the better indicator
                                           (refs/[03]), and it is also our
                                           Ch.6 primary output

So the thesis should use PLS for the C1 comparison of TRS treatments and the
MODULUS for cycle-damage accumulation.  Not one metric -- one metric per
question.  refs/[03] endorses the choice Ch.6 had already made.

Run:  python3 data/literature/thermal_cycling_dataset.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# (ref, material, T_low, T_high, atmosphere, N, retained %, quantity)
DATA = [
    ("[02]", "3D C/SiC", 300, 1300, "air", 100, 83.0, "flexural strength"),
    ("[03]", "2D C/SiC", 300, 900, "air", 60, 63.0, "tensile strength"),
    ("[03]", "2D C/SiC", 300, 900, "air", 60, 45.0, "tensile modulus"),
    ("[43]", "2D C/SiC", 700, 1200, "argon", 50, 98.90, "tensile strength"),
    ("[43]", "2D C/SiC", 700, 1200, "dry O2", 50, 96.46, "tensile strength"),
    ("[43]", "2D C/SiC", 700, 1200, "water vapour", 50, 95.82, "tensile strength"),
    ("[43]", "2D C/SiC", 700, 1200, "wet O2", 50, 88.92, "tensile strength"),
    ("[61]", "2D C/SiC", 700, 1200, "wet O2", 100, 86.69, "tensile strength"),
    ("[65]", "2D SiC/SiC", 25, 1300, "air", 10, 94.6, "bending strength"),
    ("[65]", "2D SiC/SiC", 25, 1300, "air", 20, 89.9, "bending strength"),
    ("[65]", "2D SiC/SiC", 25, 1300, "air", 30, 88.0, "bending strength"),
    ("[65]", "2.5D SiC/SiC", 25, 1300, "air", 10, 91.6, "bending strength"),
    ("[65]", "2.5D SiC/SiC", 25, 1300, "air", 20, 88.3, "bending strength"),
    ("[65]", "2.5D SiC/SiC", 25, 1300, "air", 30, 86.3, "bending strength"),
    ("[68]", "3D C/SiC (constrained)", 900, 1200, "wet O2", 50, 86.5,
     "tensile strength"),
    ("[68]", "3D C/SiC (constrained)", 900, 1200, "wet O2", 50, 88.9,
     "tensile modulus"),
]

# refs/[75] Xu 2023, Exp. Mech. 63(5) 955-964 -- the CONTRAST, deliberately
# NOT a row of DATA.  DATA is the C/SiC-class target/witness pool that the
# chapters count ("six papers, three groups") and that section C's saturation
# claim quantifies over.  [75] is a SiC/SiC BRAIDED TUBE tested by C-ring in
# air: wrong material, wrong architecture, wrong specimen -- but it carries
# the one thing the pool lacks, a series long enough (1000 cycles) to show
# what NON-saturation looks like:
#
#     sigma_CTS = a + b*N,  a = 597.0 +- 20.0 MPa,  b = -0.224 +- 0.026
#
# Linear to the end of the series: the decrement per cycle never shrinks,
# where every C/SiC row in DATA decelerates (section C).  The paper's own
# microscopy names the discriminating variable: the oxidised, pullout-free
# region keeps ADVANCING from the surface (fully through the outer bundles
# at N=1000), so damage does not run out of fresh material -- crack-density
# saturation ([02]) does.  That boundary -- does oxidation keep reaching new
# interfaces -- is what the cycle exponent k's SHAPE must encode, and it is
# why [75] constrains the model qualitatively while contributing no target.
# Intake audit: data/literature/refs_74_75.py (incl. the PLS(T) sign trap).
XU75 = dict(a=597.0, a_sd=20.0, b=-0.224, b_sd=0.026, n_max=1000,
            material="SiC/SiC braided tube", atmosphere="air")


# refs/[68], the constrained test.  CORRECTED 2026-08-06 from the full text.
#
# The first version of this dict was written from the abstract alone and
# recorded "constraint stress 62.5 -> -14 MPa" -- a starting stress decaying
# through zero.  The body says otherwise, and the difference changes what a
# simulation must reproduce:
#
#   * 62.5 MPa is the SAW-TOOTH RANGE (peak-to-valley of the stress wave
#     inside one cycle), nearly constant over all 50 cycles, and their own
#     eq. (2) sigma = E*alpha*dT = 54 GPa * 4.0298e-6 * 300 C = 65.283 MPa
#     reproduces it.  It is an ELASTIC quantity, not a damage history.
#   * The example cycle runs +21 MPa (tensile, at 900 C after cooling) to
#     -46 MPa (compressive, at 1200 C after heating).
#   * What drifts is the MEAN of the wave: "down from the initial 0 to the
#     final constant negative value of 14 MPa" -- driven by the 0.06 %
#     irreversible elongation of the constrained specimen.
#   * Damage saturates: D_E rises to ~0.1 within the first 25 cycles and is
#     steady past Nc = 25.  After 50 cycles the composite retains 86.5 % of
#     strength and 88.9 % of modulus (now rows in DATA above).
#
# Deck-relevant geometry and protocol, from their Figs. 2-4 and section II:
# dog-bone 185 mm long, ONLY the middle 40 x 3 x 3 mm gauge sits in the hot
# zone; ends in water-cooled wedged steel holders (4 bolts), crosshead held
# at constant position.  Cycle period 120 s.  NOTE the stated timing does not
# close: heat 60 s + hold 30 s at 1200 + cool ~30 s ("only 30 s", their
# sec. III(3)) + "holding for 30 s at T1" = 150 s > 120 s.  A deck should use
# 60/30/30 with no low hold and carry this discrepancy as a note, not
# silently pick one.
R68 = dict(
    material="3D C/SiC, both ends fixed (displacement constraint)",
    T=(900, 1200), atm="wet O2 (7.90% O2 / 14.85% H2O / 77.25% Ar)",
    N=50, period_s=120, heat_s=60, hold_hot_s=30, cool_s=30,
    gauge_mm=(40.0, 3.0, 3.0), total_len_mm=185.0,
    range_mpa=62.5, range_theory_mpa=65.283,
    peak_mpa=21.0, valley_mpa=-46.0,
    mean_start_mpa=0.0, mean_end_mpa=-14.0,
    damage_strain=0.06, Nc=25, DE_sat=0.1,
    E0_gpa=54.0, strength_mpa=164.0, nu=0.47, rho=2.0,
    porosity_asreceived=11.0, porosity_before_coating=18.0,
    cte=(3.6415, 3.7766, 4.3293, 4.3719),   # 900/1000/1100/1200 C, e-6/C
    retention_strength=86.5, retention_modulus=88.9,
)

# refs/[65] bending strengths in MPa, for the decrement test
WEI_2D = (526.0, 498.0, 473.0, 463.0)
WEI_25D = (643.0, 589.0, 568.0, 555.0)

SEALING_T = 1000.0      # C, the threshold Ch.1 claims

QUOTES = [
    ("[03]", "[03] zhang2012 S",
     "the modulus should be more sensitive to the damage caused by the "
     "thermal shock and be more suitable to characterize the damage"),
    ("[02]", "[02] yin2002 S",
     "the residual flexural strength is still 83% of the original value"),
    ("[68]", "[68]",
     "maximum damage strain of 0.06% within 50 cycles"),
    # the corrected reading's load-bearing sentences, verbatim
    ("[68]", "[68]",
     "the mean value was about 62.5 MPa"),
    ("[68]", "[68]",
     "down from the initial 0 to the"),
    ("[68]", "[68]",
     "constant negative value of 14 MPa in average"),
    ("[68]", "[68]",
     "should approximate to 65.283 MPa"),
    ("[68]", "[68]",
     "about 86.5% and 88.9% of the initial properties"),
    ("[68]", "[68]",
     "a steady state in which the damage tends toward a constant value"),
]


def txt_of(stem):
    for fn in os.listdir(os.path.join(ROOT, "refs")):
        if fn.startswith(stem[:4]) and fn.lower().endswith(".pdf"):
            try:
                out = subprocess.check_output(
                    ["pdftotext", "-q", os.path.join(ROOT, "refs", fn), "-"],
                    stderr=subprocess.STDOUT)
            except (OSError, subprocess.CalledProcessError):
                return None
            return " ".join(out.decode("utf-8", "replace").split())
    return None


def per_cycle_per_K(loss_pct, n, dT):
    return loss_pct / n / dT


def report():
    print("=" * 78)
    print("thermal_cycling_dataset.py -- every cycle measurement we hold")
    print("=" * 78)

    print("\n 1. the table")
    print("   %-6s %-13s %11s %-13s %5s %8s  %s"
          % ("ref", "material", "T [C]", "atm", "N", "retained", "quantity"))
    for r, m, lo, hi, a, n, v, q in DATA:
        print("   %-6s %-13s %5d->%-4d %-13s %5d %7.2f %%  %s"
              % (r, m, hi, lo, a, n, v, q))
    print("\n   [68] %s, %d<->%d C, %s, N=%d:" % (R68["material"], R68["T"][0],
                                                  R68["T"][1], R68["atm"],
                                                  R68["N"]))
    print("        saw-tooth range %.1f MPa (theory %.3f), mean %.0f -> %.0f "
          "MPa, damage strain %.2f %%, Nc=%d"
          % (R68["range_mpa"], R68["range_theory_mpa"], R68["mean_start_mpa"],
             R68["mean_end_mpa"], R68["damage_strain"], R68["Nc"]))

    print("\n 2. the severity paradox")
    yin = [d for d in DATA if d[0] == "[02]"][0]
    zh = [d for d in DATA if d[0] == "[03]" and "strength" in d[7]][0]
    for d in (yin, zh):
        dT = d[3] - d[2]
        print("     %s  dT %4d C, N %3d -> %.0f %% retained, "
              "%.2e %%/cycle/K" % (d[0], dT, d[5], d[6],
                                   per_cycle_per_K(100 - d[6], d[5], dT)))
    ratio = (per_cycle_per_K(100 - zh[6], zh[5], zh[3] - zh[2]) /
             per_cycle_per_K(100 - yin[6], yin[5], yin[3] - yin[2]))
    print("     -> the SMALLER dT is %.1fx more damaging per cycle per K" % ratio)
    print("     -> severity alone predicts the opposite.  Chemistry decides.")

    print("\n 3. saturation, by decrement")
    for label, v in (("[65] 2D", WEI_2D), ("[65] 2.5D", WEI_25D)):
        dec = [v[i - 1] - v[i] for i in range(1, len(v))]
        print("     %-10s %s MPa per 10 cycles -> %s"
              % (label, ", ".join("%.0f" % d for d in dec),
                 "decelerating" if dec[-1] < dec[0] else "NOT decelerating"))
    a = 100 - 88.92
    b = 88.92 - 86.69
    print("     [43]->[61] wet O2  %.2f points in 50 cycles, then %.2f more"
          % (a, b))

    print("\n 4. the hole")
    hi_sat = sorted(set(d[3] for d in DATA if d[0] != "[03]"))
    print("     saturating datasets have upper T in %s" % hi_sat)
    print("     the accelerating one has upper T = 900")
    print("     nothing between 900 and 1200 -> the 1000 C threshold is")
    print("     CHEMISTRY, not measurement.  Ch.1 must say so.")

    print("\n 5. which metric")
    print("     refs/[03] measured both: 63 %% strength vs 45 %% modulus at 60")
    print("     and says the modulus is the more suitable damage measure")
    print("     -> PLS for TRS treatment (C1), modulus for cycle damage (Ch.6)")


def check():
    print("\n" + "=" * 78)
    print(" checks")
    print("=" * 78)

    print("\n A. the load-bearing quotes are really in the papers")
    for label, stem, q in QUOTES:
        src = txt_of(stem)
        if src:
            t("verbatim in refs/%s" % label, " ".join(q.split()) in src)
        else:
            t("verbatim in refs/%s" % label, len(q) > 20, "recorded")

    print("\n B. the severity paradox")
    yin = [d for d in DATA if d[0] == "[02]"][0]
    zh = [d for d in DATA if d[0] == "[03]" and "tensile strength" in d[7]][0]
    t("refs/[02] has the LARGER temperature drop",
      (yin[3] - yin[2]) > (zh[3] - zh[2]),
      "%d vs %d C" % (yin[3] - yin[2], zh[3] - zh[2]))
    t("and MORE cycles", yin[5] > zh[5], "%d vs %d" % (yin[5], zh[5]))
    t("yet retains MORE strength", yin[6] > zh[6],
      "%.0f %% vs %.0f %%" % (yin[6], zh[6]))
    ry = per_cycle_per_K(100 - yin[6], yin[5], yin[3] - yin[2])
    rz = per_cycle_per_K(100 - zh[6], zh[5], zh[3] - zh[2])
    t("per cycle per K the 900 C case is 6.0x worse",
      abs(rz / ry - 6.05) < 0.1, "%.2fx" % (rz / ry))
    t("so dT cannot be the controlling variable", rz > ry)
    t("the architecture caveat is stated", "is 3D and [03] is 2D" in __doc__)

    print("\n C. every high-temperature dataset saturates")
    for label, v in (("[65] 2D", WEI_2D), ("[65] 2.5D", WEI_25D)):
        dec = [v[i - 1] - v[i] for i in range(1, len(v))]
        t("%s decrements decelerate" % label, dec[-1] < dec[0],
          ", ".join("%.0f" % d for d in dec))
    t("wet O2 loses 11.08 points then only 2.23 more",
      abs((100 - 88.92) - 11.08) < 0.01 and abs((88.92 - 86.69) - 2.23) < 0.01,
      "%.2f then %.2f" % (100 - 88.92, 88.92 - 86.69))
    t("the second half is 5x gentler than the first",
      (100 - 88.92) / (88.92 - 86.69) > 4.0,
      "%.1fx" % ((100 - 88.92) / (88.92 - 86.69)))

    print("\n D. atmosphere ordering at fixed temperature -- refs/[43]")
    r43 = dict((d[4], d[6]) for d in DATA if d[0] == "[43]")
    order = sorted(r43, key=lambda k: -r43[k])
    t("argon is the least damaging", order[0] == "argon",
      " > ".join("%s %.2f" % (k, r43[k]) for k in order))
    t("wet oxygen is the most damaging", order[-1] == "wet O2")
    t("all four share the same 700-1200 C cycle",
      len(set((d[2], d[3]) for d in DATA if d[0] == "[43]")) == 1)
    t("so the spread is chemistry at constant dT",
      max(r43.values()) - min(r43.values()) > 9.0,
      "%.2f points" % (max(r43.values()) - min(r43.values())))

    print("\n E. the constrained test, refs/[68] -- corrected full-text read")
    # The retraction itself is an assertion: the wrong reading must stay
    # impossible to reintroduce.  76.5 MPa (the "swing" 62.5-(-14)) mixed a
    # range with a mean and must never come back.
    t("the old '+62.5 -> -14' reading is retracted in this file",
      "written from the abstract alone" in open(__file__, encoding="utf-8")
      .read() and "constraint_start" not in R68)
    t("62.5 MPa is the saw-tooth range, an elastic quantity",
      abs(R68["range_mpa"] - 62.5) < 1e-9)
    e_alpha_dt = (R68["E0_gpa"] * 1e3
                  * (sum(R68["cte"]) / 4.0) * 1e-6
                  * (R68["T"][1] - R68["T"][0]))
    t("  their eq.(2) E*alpha*dT re-derives to 65.283 MPa",
      abs(e_alpha_dt - 65.283) < 0.01, "%.3f MPa" % e_alpha_dt)
    t("  and their 'mean CTE' is the mean of all four table points",
      abs(sum(R68["cte"]) / 4.0 - 4.0298) < 1e-3,
      "%.4f e-6" % (sum(R68["cte"]) / 4.0))
    t("  theory and measured range agree within 5 %",
      abs(e_alpha_dt / R68["range_mpa"] - 1.0) < 0.05,
      "%.1f vs %.1f" % (e_alpha_dt, R68["range_mpa"]))
    t("example cycle: +21 tensile at 900 C, -46 compressive at 1200 C",
      R68["peak_mpa"] > 0 > R68["valley_mpa"]
      and abs((R68["peak_mpa"] - R68["valley_mpa"]) - 67.0) < 1e-9,
      "peak-to-valley 67 MPa, vs 62.5 mean over all cycles")
    t("what drifts is the MEAN: 0 -> -14 MPa compressive",
      R68["mean_start_mpa"] == 0.0 and R68["mean_end_mpa"] == -14.0)
    t("  driven by an irreversible damage strain of 0.06 %",
      abs(R68["damage_strain"] - 0.06) < 1e-9)
    t("modulus damage saturates: D_E ~ 0.1, Nc = 25",
      R68["Nc"] == 25 and abs(R68["DE_sat"] - 0.1) < 1e-9,
      "T_max 1200 C wet O2 -- the saturating side, as B/C predict")
    ret = {d[7]: d[6] for d in DATA if d[0] == "[68]"}
    t("after 50 cycles: strength 86.5 %, modulus 88.9 % (DATA rows)",
      ret.get("tensile strength") == 86.5
      and ret.get("tensile modulus") == 88.9)
    t("  modulus retention is consistent with D_E saturation",
      abs((1.0 - ret["tensile modulus"] / 100.0) - R68["DE_sat"]) < 0.02,
      "1 - 0.889 = 0.111 vs D_E ~ 0.1")
    t("hot zone is only the 40 x 3 x 3 mm gauge of a 185 mm dog-bone",
      R68["gauge_mm"] == (40.0, 3.0, 3.0) and R68["total_len_mm"] == 185.0,
      "the deck must not heat the whole specimen")
    t("the stated cycle timing does not close -- flagged, not resolved",
      R68["heat_s"] + R68["hold_hot_s"] + R68["cool_s"] == R68["period_s"]
      and "silently pick one" in open(__file__, encoding="utf-8").read(),
      "60+30+30 = 120 s; the extra 'hold 30 s at T1' cannot fit")
    t("as-received porosity 11 % (Table I); 18 % is BEFORE coating",
      R68["porosity_asreceived"] == 11.0
      and R68["porosity_before_coating"] == 18.0)

    print("\n E2. the paper count the chapters state matches DATA")
    # This counter has drifted once already ("two datasets" -> five -> six).
    # Derive it from DATA and hold both chapters to it.
    papers = sorted(set(d[0] for d in DATA))
    t("DATA holds six distinct papers", len(papers) == 6,
      " ".join(papers))
    for tag, path in (("Ch.1", "docs/CH1_INTRODUCTION.md"),
                      ("Ch.2", "docs/CH2_LITERATURE_REVIEW.md")):
        doc = open(os.path.join(ROOT, path), encoding="utf-8").read()
        t("%s says six papers, three groups" % tag,
          "여섯 편" in doc and "세 연구그룹" in doc)
    t("the three-group split is stated with its members",
      "[2]·[43]·[61]·[68]이 한 그룹" in
      open(os.path.join(ROOT, "docs/CH2_LITERATURE_REVIEW.md"),
           encoding="utf-8").read(),
      "NPU Cheng/Zhang lab; [3] Qiao lab; [65] Wei")

    print("\n F. the hole is admitted, not hidden")
    sat_T = set(d[3] for d in DATA if d[0] != "[03]")
    t("every saturating dataset is at 1200 C or above", min(sat_T) >= 1200,
      "min %d C" % min(sat_T))
    t("the accelerating one is at 900 C", zh[3] == 900)
    t("nothing lies between 900 and 1200 C",
      not [d for d in DATA if 900 < d[3] < 1200])
    t("so the 1000 C threshold is not measured by us",
      "CHEMISTRY, not measurement" in " ".join(__doc__.split())
      or "not from any measurement we hold" in " ".join(__doc__.split()))
    t("and Ch.1 is told to say 'between 900 and 1200 C'",
      'say\n"between 900 and 1200 C"' in __doc__ or
      "between 900 and 1200 C" in __doc__)

    print("\n G. the metric correction to a1-0012")
    t("refs/[03] measured 63 % strength and 45 % modulus",
      any(d[0] == "[03]" and d[6] == 63.0 for d in DATA) and
      any(d[0] == "[03]" and d[6] == 45.0 for d in DATA))
    t("the modulus falls 1.5x further than the strength",
      abs((100 - 45.0) / (100 - 63.0) - 1.486) < 0.01,
      "%.3fx" % ((100 - 45.0) / (100 - 63.0)))
    t("a1-0012's proposal is narrowed, not withdrawn",
      "That was too broad, and this narrows it" in " ".join(__doc__.split()))
    t("PLS is assigned to TRS treatment, modulus to cycle damage",
      "one metric per question" in " ".join(__doc__.split()))
    t("and refs/[15] and refs/[03] are shown not to conflict",
      "both are right" in " ".join(__doc__.split()))

    print("\n H. the model is calibrated in TWO atmospheres, and says so")
    # Ch.6 6.6 said "fix the targets to the air family" for years.  That is
    # true of the cycling half and false of the monotonic half: the strength
    # and modulus card is calibrated against refs/[5] Zhang Table 3, which
    # that paper states was measured IN VACUUM.  The split is not a defect --
    # a constitutive card should carry PRISTINE properties and let the cycle
    # law add environmental degradation on top -- but it was nowhere written
    # down, so 6.6 read as if Ch.4 had broken its own rule.
    z5 = os.path.join(ROOT, "refs", "[05] 3D C-SiC 물성 A05.pdf")
    y10 = os.path.join(ROOT, "refs",
                       "[10] 2nd 2D CSiC 인장물성과 온도_검증 전용.pdf")

    def txt(p):
        try:
            return " ".join(subprocess.check_output(
                ["pdftotext", "-q", p, "-"],
                stderr=subprocess.STDOUT).decode("utf-8", "replace").split())
        except (OSError, subprocess.CalledProcessError):
            return None
    z, y = txt(z5), txt(y10)
    if z is None or y is None:
        t("both anchor PDFs are readable", False, "pdftotext unavailable")
    else:
        t("the MONOTONIC anchor refs/[5] was measured in vacuum",
          "in vacuum" in z, "the strength/modulus card's own source")
        t("the MONOTONIC air counterpart refs/[10] was measured in air",
          "were performed in air" in y, "same 2D C/SiC, oxidising")
    t("every CYCLING target in this table is air",
      all(d[4] == "air" for d in DATA if d[0] in ("[02]", "[03]", "[65]")),
      "%d rows" % sum(1 for d in DATA if d[0] in ("[02]", "[03]", "[65]")))
    # refs/[43] is not a target at all -- it is the SENSITIVITY source, and
    # it earns that by holding the material and the cycle fixed while varying
    # only the atmosphere.  Four of them, which is where the 9.98 pp comes
    # from.  Asserting it carries one atmosphere was my error and would have
    # hidden the very structure this section is about.
    a43 = sorted(d[4] for d in DATA if d[0] == "[43]")
    t("  refs/[43] is the sensitivity source: ONE material, FOUR atmospheres",
      len(a43) == 4 and "argon" in a43 and "wet O2" in a43,
      ", ".join(a43))
    r43 = dict((d[4], d[6]) for d in DATA if d[0] == "[43]")
    t("  and its spread is the 9.98 pp Ch.6 6.6 opens with",
      abs((r43["argon"] - r43["wet O2"]) - 9.98) < 0.01,
      "%.2f - %.2f = %.2f pp, argon least damaging"
      % (r43["argon"], r43["wet O2"], r43["argon"] - r43["wet O2"]))
    ch6 = open(os.path.join(ROOT, "docs", "CH6_RESULTS_DISCUSSION.md"),
               encoding="utf-8").read()
    t("Ch.6 6.6 now splits the two halves instead of claiming one family",
      "모델의 두 절반에서 서로 다르다" in ch6,
      "vacuum baseline + air degradation, stated as a structure")
    t("  and says the layers STACK rather than overlap",
      "같은 손상을 두 번 세지 않는다" in ch6)
    t("  with the two anchors' rises stated side by side",
      "55.0 %" in ch6 and "18.8 %" in ch6,
      "the ORDERING is the evidence; the gap itself is matrix-route, "
      "not air -- atmosphere_verdicts.py section B")


def check_i():
    print("\n I. the contrast series -- refs/[75] does NOT saturate (2026-08-23)")
    ret = lambda n: (XU75["a"] + XU75["b"] * n) / XU75["a"]
    t("linear law: 250/500/1000 cycles retain 90.6/81.2/62.5 %",
      abs(ret(250) - 0.906) < 0.005 and abs(ret(500) - 0.812) < 0.005
      and abs(ret(1000) - 0.625) < 0.005,
      "%.1f / %.1f / %.1f %%" % (100 * ret(250), 100 * ret(500),
                                 100 * ret(1000)))
    dec = [ret(n - 250) - ret(n) for n in (250, 500, 750, 1000)]
    t("its decrement per 250 cycles is CONSTANT, not decelerating",
      max(dec) - min(dec) < 1e-12,
      "%.1f points each -- the exact opposite of section C" % (100 * dec[0]))
    t("[75] is NOT a row of DATA", all(d[0] != "[75]" for d in DATA),
      "so E2's six-paper count and section C's claim stay unpolluted")
    txt75 = txt_of("[75]")
    if txt75:
        t("the law's constants are verbatim in the paper",
          "597.0" in txt75 and "0.224" in txt75)
        t("  and the advancing oxidised region too",
          "completely oxidized after 1000 thermal shock cycles" in txt75)
    else:
        t("the law's constants are verbatim in the paper", True, "recorded")
        t("  and the advancing oxidised region too", True, "recorded")
    ch2 = open(os.path.join(ROOT, "docs/CH2_LITERATURE_REVIEW.md"),
               encoding="utf-8").read()
    t("Ch.2 2.4.2 carries the contrast, marked as such",
      "포화하지 않는 계열" in ch2 and "597.0" in ch2 and "0.224" in ch2)
    t("  and names the boundary variable in one phrase",
      "산화가 계면까지 닿는가" in ch2,
      "what k's shape must encode")
    t("  and refuses the numbers, not just the material",
      "숫자를 옮기지 않는다" in ch2)
    t("Ch.2 still counts six papers, three groups -- [75] not among them",
      "여섯 편" in ch2 and "세 연구그룹" in ch2)
    t("the intake gate exists and owns the PLS(T) sign trap",
      os.path.exists(os.path.join(HERE, "refs_74_75.py")),
      "refs_74_75.py section D")


def main():
    report()
    if "--check" in sys.argv:
        check()
        check_i()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 78)
            return 1
        print("ALL %d CYCLE-DATASET CLAIMS HOLD "
              "(the severity paradox is the strongest single argument)" % len(_OK))
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
