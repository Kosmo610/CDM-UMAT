#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch5_numbers.py  --  ROUND 1 for Chapter 5
===============================================
Chapter 5 describes decks that a script generates.  That makes its failure mode
specific and nasty: the prose can be perfectly self-consistent and still
describe a deck the script no longer writes.  Nothing in rounds 2 or 3 would
catch it -- round 2 compares chapters to each other, round 3 only checks that
named files exist and named commands exit 0.

So this round reads the numbers out of abaqus/make_macro_thermalshock.py and
abaqus/quench_calibration.py and asserts the chapter quotes those, not numbers
that were true when the chapter was written.

  A. severity ladder: film coefficients and Biot numbers match SEVERITIES
  B. specimen geometry, mesh and checkpoints match SPECIMENS
  C. the calibrated film coefficients match what quench_calibration.py solves
  D. deck mechanics the chapter claims -- probe strain, cycle-jump field,
     freeze_step slot, restart, SDV history list -- are really in the generator
  E. cycle-jump accuracy figures match verify_thermshock.py T6
  F. the chapter does not claim any of it has been run

Run:  python3 verification/check_ch5_numbers.py
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def run(cmd):
    p = subprocess.Popen(cmd, cwd=ROOT, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return out.decode("utf-8", "replace"), p.returncode


def main():
    print("=" * 78)
    print("ROUND 1 -- check_ch5_numbers.py: does Ch.5 describe the real decks?")
    print("=" * 78)

    path = os.path.join(DOCS, "CH5_MACRO_THERMALSHOCK.md")
    if not os.path.exists(path):
        check("CH5_MACRO_THERMALSHOCK.md exists", False)
        return 1
    ch5 = open(path).read()
    check("CH5_MACRO_THERMALSHOCK.md exists", True)
    flat = re.sub(r"(?<=\d)[  ](?=\d)", "", ch5)

    gen_path = os.path.join(ROOT, "abaqus", "make_macro_thermalshock.py")
    gen = open(gen_path).read()

    # Import the generator so the dicts are read as data, not scraped as text.
    sys.path.insert(0, os.path.join(ROOT, "abaqus"))
    import importlib
    mts = importlib.import_module("make_macro_thermalshock")

    # ------------------------------------------------------------------ A
    print("\n A. the severity ladder matches SEVERITIES in the generator")
    sev = mts.SEVERITIES
    check("generator defines 5 severities (3 ladder + 2 validation)",
          len(sev) == 5, ", ".join(sorted(sev)))

    for key, bi_txt, h_txt in (("L", "0.05", "2.10"),
                               ("M", "1", "4.19"),
                               ("H", "5", "2.10")):
        s = sev[key]
        check("severity %s Bi = %s in both" % (key, bi_txt),
              abs(s["bi"] - float(bi_txt)) < 1e-9 and bi_txt in flat,
              "generator %g" % s["bi"])
        # h is quoted in the chapter in scientific notation with 3 sig figs
        mant = "%.2f" % (s["h"] / 10 ** int(("%e" % s["h"]).split("e")[1]))
        check("severity %s film coefficient %s in the chapter" % (key, mant),
              mant in flat, "generator h=%g" % s["h"])

    check("the ladder is stated as 0.05 / 1 / 5 in the chapter",
          bool(re.search(r"0\.05\s*/\s*1\s*/\s*5", flat)))
    # The whole point of the ladder is that only h changes.
    check("all three ladder levels share one temperature amplitude",
          len({(sev[k]["T_hi"], sev[k]["T_lo"]) for k in "LMH"}) == 1,
          "%g -> %g" % (sev["L"]["T_hi"], sev["L"]["T_lo"]))
    check("chapter says the amplitude is held fixed",
          "온도 진폭을 고정" in ch5 or "진폭을 고정" in ch5)

    # ------------------------------------------------------------------ B
    print("\n B. specimen geometry and checkpoints match SPECIMENS")
    for name, dims, mesh, cps in (
            ("ZHANG2013", (12.5, 6.0, 3.0), (10, 6, 12), (20, 40, 60)),
            ("YIN2002", (20.0, 6.0, 4.0), (12, 6, 14), (20, 50, 100))):
        sp = mts.SPECIMENS[name]
        check("%s dims match the generator" % name,
              tuple(sp["dims"]) == dims, str(sp["dims"]))
        check("%s mesh matches the generator" % name,
              tuple(sp["mesh"]) == mesh, str(sp["mesh"]))
        check("%s checkpoints match the generator" % name,
              tuple(sp["checkpoints"]) == cps, str(sp["checkpoints"]))
        for v in cps:
            check("%s checkpoint %d quoted in Ch.5" % (name, v),
                  str(v) in flat)
    # the through-thickness dimension is the quenched one -- if the chapter
    # quotes the wrong one the whole Biot discussion is wrong
    check("Ch.5 marks 3.0 mm as ZHANG2013 thickness", "**3.0**" in ch5)
    check("Ch.5 marks 4.0 mm as YIN2002 thickness", "**4.0**" in ch5)

    # ------------------------------------------------------------------ C
    print("\n C. calibrated film coefficients match quench_calibration.py")
    out, rc = run("python3 abaqus/quench_calibration.py")
    check("quench_calibration.py runs", rc == 0)
    for label, h_si, bi in (("ZHANG2013", "199.0", "0.0475"),
                            ("YIN2002", "87.0", "0.0277")):
        check("%s h = %s W/(m^2.K) solved" % (label, h_si), h_si in out)
        check("%s Bi = %s solved" % (label, bi), bi in out)
        check("%s h = %s quoted in Ch.5" % (label, h_si), h_si in flat)
        check("%s Bi = %s quoted in Ch.5" % (label, bi), bi in flat)
    # and the generator's own annotation must agree with the solver
    check("generator severity Z carries Bi 0.0475",
          abs(sev["Z"]["bi"] - 0.0475) < 1e-9, "%g" % sev["Z"]["bi"])
    check("generator severity Y carries Bi 0.0277 (not a rounded 0.028)",
          abs(sev["Y"]["bi"] - 0.0277) < 1e-9, "%g" % sev["Y"]["bi"])
    # the gradient percentages the chapter uses to justify C2
    for frac in ("3.3", "1.7"):
        check("gradient fraction %s %% appears in both" % frac,
              frac in out and frac in flat)

    # ------------------------------------------------------------------ D
    print("\n D. deck mechanics claimed by the chapter exist in the generator")
    check("probe strain 1e-6 in the generator",
          abs(mts.PROBE_STRAIN - 1.0e-6) < 1e-15, "%g" % mts.PROBE_STRAIN)
    check("probe strain quoted as 1e-6 in Ch.5",
          "10^{-6}" in ch5 or "1e-6" in ch5 or "10⁻⁶" in ch5)
    check("residual-strength target 1 %% in the generator",
          abs(mts.FAIL_STRAIN - 0.010) < 1e-12, "%g" % mts.FAIL_STRAIN)
    check("stress-free temperature 1050 in the generator",
          abs(mts.STRESS_FREE_C - 1050.0) < 1e-9)
    check("mesh grading bias defaults below 1 (refines at the surfaces)",
          "bias=0.55" in gen)
    check("Ch.5 quotes the grading bias 0.55", "0.55" in flat)
    check("generator rejects bias >= 1", "bias must be < 1" in gen)
    check("Ch.5 says bias >= 1 is rejected",
          "거부" in ch5 and "0.55" in ch5)

    check("cycle rate is field variable 1", "*Field, variable=1" in gen)
    check("Ch.5 shows the field-variable card",
          "*Field, variable=1" in ch5)
    check("probe zeroes the cycle rate", "_mech_field(0.0)" in gen)
    check("probe uses op=NEW", "*Boundary, op=NEW" in gen)
    check("Ch.5 explains why op=NEW is needed",
          "op=NEW" in ch5 and ("유지" in ch5 or "살아남" in ch5))

    check("freeze_step is card slot 26 in the generator",
          "patch_card(card, 26, 1.0) if trs ==" in gen)
    check("Ch.5 names slot 26 as freeze_step",
          "PROPS(26)" in ch5 and "freeze_step" in ch5)
    check("only case B is patched", 'if trs == "B" else card' in gen)
    check("Ch.5 says only B is patched",
          "케이스 B에" in ch5 or "B에\n   대해서만" in ch5 or
          "B에 대해서만" in ch5.replace("\n", " ").replace("  ", " "))

    check("restart written at probes", "*Restart, write, overlay" in gen)
    check("restart read by the residual job", "*Restart, read, step=" in gen)
    check("temperature is read from the shared heat odb",
          "*Temperature, file=%s.odb" in gen)
    check("Ch.5 shows the temperature mapping card",
          "*Temperature, file=" in ch5)
    check("deltmx=25 in the heat steps", "deltmx=25." in gen)
    check("Ch.5 quotes deltmx = 25", "deltmx" in ch5 and "25" in flat)

    # the SDV history list -- C4 needs all three indices every frame
    m = re.search(r"SDV9, SDV10, SDV17, SDV18, SDV19, SDV23, SDV24, SDV25",
                  gen)
    check("generator writes the 8 history SDVs", bool(m))
    # The chapter groups 23/24 into one row ("23 / 24"), so test the SDV table
    # region for each number rather than assuming one row per variable.
    tbl = ch5[ch5.find("| SDV |"):] if "| SDV |" in ch5 else ""
    tbl = tbl[:tbl.find("\n\n")] if "\n\n" in tbl else tbl
    check("Ch.5 has an SDV table", bool(tbl.strip()))
    for s in ("9", "10", "17", "18", "19", "23", "24", "25"):
        check("Ch.5 lists SDV%s" % s,
              bool(re.search(r"(?<![0-9])%s(?![0-9])" % s, tbl)))

    # ------------------------------------------------------------------ E
    print("\n E. cycle-jump accuracy matches verify_thermshock.py T6")
    out6, rc6 = run("python3 verification/verify_thermshock.py")
    check("verify_thermshock.py runs", rc6 == 0)
    check("T5 shakedown drift is exactly zero", "drift=0.00e+00" in out6)
    check("Ch.5 quotes the zero drift",
          "0.00e+00" in ch5 or "정확히 0" in ch5)
    check("T6 linear-case jump error 1.53e-16 reported", "1.53e-16" in out6)
    check("Ch.5 quotes 1.53e-16", "1.53" in flat and "10⁻¹⁶" in ch5)
    check("T6 nonlinear jump error 0.03 %% reported",
          "rel.err=0.03 %" in out6)
    check("Ch.5 quotes 0.03 %", "0.03 %" in ch5 or "0.03 %" in ch5)

    # ------------------------------------------------------------------ F
    print("\n F. the chapter does not claim results it does not have")
    check("Ch.5 states no deck has been run yet",
          "아직 실행되지 않았다" in ch5)
    check("Ch.5 defers the macro card to Ch.4's calibration",
          "확정되기 전에는" in ch5 and "실행하지 않는다" in ch5)
    check("Ch.5 lists the cycle-damage coefficients as uncalibrated",
          "미보정" in ch5)
    check("Ch.5 flags the YIN2002 flexural-probe gap",
          "굽힘" in ch5 and ("구현되어 있지 않" in ch5
                            or "구현되지 않았다" in ch5))
    check("Ch.5 does not present a residual-strength number",
          not re.search(r"잔여강도[^\n]{0,40}[0-9]+\.[0-9]+\s*MPa", ch5))
    check("Ch.5 declares the three pre-run checks",
          all(s in ch5 for s in ("열경계층", "온도 매핑", "사이클 점프")))

    # the generator's own list-checks must still name those three
    outc, rcc = run("python3 abaqus/make_macro_thermalshock.py --list-checks")
    check("--list-checks runs", rcc == 0)
    for k in ("THERMAL BOUNDARY LAYER", "TEMPERATURE MAPPING",
              "CYCLE-JUMP ERROR"):
        check("--list-checks still names %s" % k, k in outc)

    print("\n" + "=" * 78)
    if _BAD:
        print("ROUND 1 FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ROUND 1 PASS -- ALL %d CH.5 CLAIMS MATCH THE GENERATOR" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
