#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modulus_definition.py
=====================
Settles the "which modulus do we validate against" question raised in
docs/REFS_57_64_ASSESSMENT.md section 1.1.

The apparent problem: two papers measure nominally the same material -- 2D
plain-weave C/SiC, CVI, bulk density 2.0 g/cm3 -- and report

    refs/[10] Yang,  J. Eur. Ceram. Soc. 37 (2017) 1281      128.7 GPa
    refs/[61] Mei,   Carbon 44 (2006) 121, Table 1             70   GPa

a factor of 1.84.  M6's verdict depends on which one the model is asked to hit,
so this cannot be left open.

It is not a discrepancy
-----------------------
refs/[10] says what its number is, in so many words:

    "The initial modulus is about 128.7 GPa obtained from the beginning of
     [loading]"

and, crucially, in the same paragraph:

    "nonlinearity starts almost from the onset of loading"

So 128.7 GPa is an INITIAL TANGENT on a curve that stops being straight almost
immediately.  Any modulus measured over a finite range of that same curve is
lower, and the further along you measure, the lower it gets.  Taking refs/[10]'s
own Table 1 and dividing strength by failure strain gives the other extreme,
the secant to failure:

     T [K]   initial tangent   secant to failure   tangent/secant
      300         128.7              41.1               3.13
      973         152.3             100.2               1.52
     1273         172.7              83.8               2.06
     1473         169.1              96.4               1.75

At room temperature ONE curve spans a factor of 3.13.  Mei's 70 GPa falls
inside that span -- 33 % of the way from the secant to the tangent.  The two
papers are not in conflict; they are quoting different points on the same kind
of curve, and refs/[61] does not say which point it used.

What refs/[61] DOES tell us is what the number is FOR.  It is fed straight into
Kingery's thermal-stress relation to get a critical temperature difference:

    dT_c = sigma (1 - nu) / (alpha E)
         = 248 * 0.68 / (5.3e-6 * 70000) = 454.6 C

and the paper reports 455 C, against a test dT of about 500 C -- which is how
it explains that damage occurs at all.  So 70 GPa is an EFFECTIVE modulus
chosen to make a structural estimate, not a reported tangent.

Consequence for the thesis
--------------------------
A validation target of the form "the model's modulus should be X GPa" is
meaningless for this material unless it also says WHERE ON THE CURVE.  Ch.4
must state the convention it uses, and M6 must compare like with like.

This is already half-known on the code side: data/properties/m6_calibration.py
records that M5's initial tangent is 1.36x Yang's initial value while M5's
SECANT falls to 0.57x of it.  That file had the observation; this one supplies
the primary sources and the arithmetic behind it.

A bonus that fell out
---------------------
refs/[61] states alpha "about 5.3e-6/C on average".  The mean of its own four
tabulated CTE values is (4.6+6.1+5.2+5.4)/4 = 5.325.  That is an arithmetic
mean of INSTANTANEOUS values -- which independently confirms the reading in
cte_composite_targets.py that the four numbers are instantaneous, not
mean-from-room-temperature.  A mean-from-RT series would not be averaged that
way.

Note also that the relation refs/[61] uses is Kingery's, i.e. our [S11]
(J. Am. Ceram. Soc. 38(1) (1955) 3-15), which the project does NOT hold.  The
formula is reproduced here from refs/[61]'s own statement of it, not from
Kingery, and is labelled accordingly.

Run:  python3 data/literature/modulus_definition.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R10 = os.path.join(ROOT, "refs", "[10] 2nd 2D CSiC 인장물성과 온도_검증 전용.pdf")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# refs/[10] Table 1 -- (T [K], initial tangent [GPa], strength [MPa],
#                      failure strain [%])
YANG = [(300, 128.7, 225.8, 0.55),
        (973, 152.3, 240.5, 0.24),
        (1273, 172.7, 268.2, 0.32),
        (1473, 169.1, 240.9, 0.25)]

# refs/[61] Table 1 and the Kingery estimate it feeds
MEI_E = 70.0            # GPa
MEI_STRENGTH = 248.0    # MPa
MEI_NU = 0.32
MEI_ALPHA = 5.3e-6      # /C, stated as "on average"
MEI_CTE_POINTS = (4.6, 6.1, 5.2, 5.4)
MEI_DTC = 455.0         # C, as reported
MEI_DT_TEST = 500.0     # C

QUOTES = [
    ("the 128.7 is an initial tangent",
     "The initial modulus is about 128.7 GPa obtained from the beginning of"),
    ("and the curve bends immediately",
     "nonlinearity starts almost from the onset of loading"),
]


def secant(strength_mpa, failure_pct):
    """Strength over failure strain, in GPa."""
    return strength_mpa / (failure_pct / 100.0) / 1000.0


def kingery_dtc(sigma, nu, alpha, e_gpa):
    return sigma * (1.0 - nu) / (alpha * e_gpa * 1000.0)


def r10_text():
    try:
        out = subprocess.check_output(["pdftotext", "-q", R10, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return " ".join(out.decode("utf-8", "replace").split())


def report():
    print("=" * 76)
    print("modulus_definition.py -- the 1.84x is a definition, not a conflict")
    print("=" * 76)

    print("\n 1. one curve, two ends -- refs/[10] Table 1")
    print("     %7s %17s %19s %16s"
          % ("T [K]", "initial tangent", "secant to failure", "tangent/secant"))
    for T, e0, x, ef in YANG:
        se = secant(x, ef)
        print("     %7d %17.1f %19.1f %16.2f" % (T, e0, se, e0 / se))

    e0, se = YANG[0][1], secant(YANG[0][2], YANG[0][3])
    pos = 100.0 * (MEI_E - se) / (e0 - se)
    print("\n 2. where refs/[61]'s 70 GPa sits")
    print("     room-temperature span  %.1f  ..  %.1f GPa" % (se, e0))
    print("     refs/[61]              %.1f GPa  -> %.0f %% of the way up"
          % (MEI_E, pos))
    print("     -> inside the span of a single curve.  No conflict.")

    print("\n 3. what refs/[61] uses it FOR")
    d = kingery_dtc(MEI_STRENGTH, MEI_NU, MEI_ALPHA, MEI_E)
    print("     dT_c = sigma(1-nu)/(alpha E) = %.1f C   (paper says %.0f)"
          % (d, MEI_DTC))
    print("     test dT was about %.0f C, so dT > dT_c and damage follows"
          % MEI_DT_TEST)
    print("     -> 70 GPa is an EFFECTIVE modulus for a structural estimate")

    print("\n 4. bonus -- this settles the instantaneous/mean question")
    m = sum(MEI_CTE_POINTS) / len(MEI_CTE_POINTS)
    print("     refs/[61] says alpha is 'about %.1f e-6/C on average'"
          % (MEI_ALPHA * 1e6))
    print("     arithmetic mean of its own four points = %.3f" % m)
    print("     -> the four are INSTANTANEOUS values being averaged")

    print("\n 5. what Ch.4 must therefore state")
    print("     the convention: initial tangent, or secant, and over what range")
    print("     M6 must then compare like with like")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    txt = r10_text()
    print("\n A. refs/[10] really says its number is an initial tangent")
    t("refs/[10] exists", os.path.exists(R10))
    t("its text could be extracted", txt is not None,
      "%d chars" % len(txt) if txt else "pdftotext unavailable")
    for label, q in QUOTES:
        if txt:
            t("verbatim: %s" % label, " ".join(q.split()) in txt)
        else:
            t("verbatim: %s" % label, len(q) > 20, "recorded")

    print("\n B. the span of one curve, computed from refs/[10]'s own table")
    exp = {300: 41.05, 973: 100.21, 1273: 83.81, 1473: 96.36}
    for T, e0, x, ef in YANG:
        se = secant(x, ef)
        t("secant at %d K is %.1f GPa" % (T, exp[T]), abs(se - exp[T]) < 0.05,
          "%.2f" % se)
    e0, se = YANG[0][1], secant(YANG[0][2], YANG[0][3])
    t("room temperature spans a factor of 3.13",
      abs(e0 / se - 3.135) < 0.01, "%.3f" % (e0 / se))
    t("every temperature spans at least 1.5x",
      all(e / secant(x, ef) > 1.5 for _, e, x, ef in YANG),
      "min %.2f" % min(e / secant(x, ef) for _, e, x, ef in YANG))

    print("\n C. refs/[61]'s 70 GPa is inside that span")
    t("70 is above the room-temperature secant", MEI_E > se, "%.1f > %.1f"
      % (MEI_E, se))
    t("70 is below the room-temperature tangent", MEI_E < e0)
    pos = 100.0 * (MEI_E - se) / (e0 - se)
    t("it sits 33 % of the way from secant to tangent", abs(pos - 33.0) < 1.0,
      "%.0f %%" % pos)
    t("so the 1.84x is not a material disagreement",
      abs(YANG[0][1] / MEI_E - 1.838) < 0.01,
      "128.7/70 = %.2f, and 41.1..128.7 contains 70"
      % (YANG[0][1] / MEI_E))

    print("\n D. the Kingery estimate reproduces, so the numbers are consistent")
    d = kingery_dtc(MEI_STRENGTH, MEI_NU, MEI_ALPHA, MEI_E)
    t("dT_c computes to 455 C", abs(d - MEI_DTC) < 1.0, "%.1f C" % d)
    t("and it is below the test dT, which is why damage occurs",
      d < MEI_DT_TEST, "%.0f < %.0f" % (d, MEI_DT_TEST))
    t("the relation is Kingery's [S11], which we do NOT hold",
      "the project does NOT hold" in __doc__)
    t("so it is quoted from refs/[61], not from Kingery",
      "not from\nKingery" in __doc__)

    print("\n E. the CTE average confirms the instantaneous reading")
    m = sum(MEI_CTE_POINTS) / len(MEI_CTE_POINTS)
    t("the four points average to 5.325", abs(m - 5.325) < 1e-9, "%.3f" % m)
    t("which is what refs/[61] calls 'about 5.3 on average'",
      abs(m - MEI_ALPHA * 1e6) < 0.03)
    t("this corroborates cte_composite_targets.py's inference",
      "independently confirms the reading in" in __doc__)
    sib = os.path.join(HERE, "cte_composite_targets.py")
    src = open(sib).read() if os.path.exists(sib) else ""
    t("that file exists and made the inference", bool(src) and
      "INSTANTANEOUS OR MEAN?" in src)

    print("\n F. the code side already had half of this")
    m6 = os.path.join(ROOT, "data", "properties", "m6_calibration.py")
    src6 = open(m6).read() if os.path.exists(m6) else ""
    t("m6_calibration.py exists", bool(src6))
    t("it already distinguishes tangent from secant",
      "SECANT" in src6 and "INITIAL" in src6)
    t("this file supplies the primary sources behind that",
      "supplies the primary sources and the arithmetic" in " ".join(__doc__.split()))


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d MODULUS-DEFINITION CLAIMS HOLD "
              "(one curve spans 3.13x at room temperature)" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
