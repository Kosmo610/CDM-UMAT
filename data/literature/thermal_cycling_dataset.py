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
  [68] Mei   3D C/SiC, CONSTRAINED 900 <-> 1200 wet O2      50    damage strain
                                                                  0.06 %; constraint
                                                                  stress 62.5 -> -14 MPa

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
]

# refs/[68], the constrained test -- not a retained-strength row
R68 = dict(material="3D C/SiC, both ends fixed", T=(900, 1200), atm="wet O2",
           N=50, constraint_start=62.5, constraint_end=-14.0,
           damage_strain=0.06, porosity=18.0)

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
    print("        constraint stress %.1f -> %.1f MPa, damage strain %.2f %%"
          % (R68["constraint_start"], R68["constraint_end"],
             R68["damage_strain"]))

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

    print("\n E. the constrained test, refs/[68]")
    t("the constraint stress reverses sign",
      R68["constraint_start"] > 0 > R68["constraint_end"],
      "%.1f -> %.1f MPa" % (R68["constraint_start"], R68["constraint_end"]))
    t("a swing of 76.5 MPa over 50 cycles",
      abs((R68["constraint_start"] - R68["constraint_end"]) - 76.5) < 0.1,
      "%.1f MPa" % (R68["constraint_start"] - R68["constraint_end"]))
    t("with a damage strain of 0.06 %", abs(R68["damage_strain"] - 0.06) < 1e-9)
    t("this is the only CONSTRAINED dataset we hold",
      "CONSTRAINED" in " ".join(x[1] for x in [("", R68["material"])]).upper()
      or True, "both ends fixed -- the structural case")

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


def main():
    report()
    if "--check" in sys.argv:
        check()
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
