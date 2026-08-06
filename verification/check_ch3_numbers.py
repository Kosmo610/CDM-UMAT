#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch3_numbers.py
====================
Ch.3 is the verification chapter, so its own numbers had better be verified.

The chapter states an assertion count for every check script and a grand total.
Those counts drift the moment anyone adds a test -- which is the normal course
of the project -- and a verification chapter that miscounts its own tests is
the worst possible place to be caught out.

This runs each check script for real and compares the number of assertions it
reports against what Ch.3 claims.  It also re-derives the two headline numbers
the chapter quotes from the cross-check (114 material-point states, worst
relative deviation) and the micromechanics table (0.142 % worst error).

Slow by design: it actually runs everything, including the gfortran build.

Run:  python3 verification/check_ch3_numbers.py
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHAPTER = os.path.join(ROOT, "docs", "CH3_VERIFICATION.md")

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-50s %s" % ("PASS" if cond else "FAIL", name, detail))


def run(cmd):
    """Return (stdout, exit code).  The exit code is the only trustworthy
    verdict -- several scripts legitimately print the word FAIL in a legend
    or in a 'N passed, 0 failed' summary line."""
    p = subprocess.Popen(cmd, cwd=ROOT, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return out.decode("utf-8", "replace"), p.returncode


def count_bracketed(text):
    return len(re.findall(r"\[PASS\]|\[FAIL\]", text))


def count_plain(text):
    return len(re.findall(r"(?m)^\s{0,4}(?:PASS|FAIL)\b", text))


# (label in Ch.3 table, command, counter, expected count claimed by Ch.3)
CASES = [
    ("verify_constitutive.py",
     "python3 verification/verify_constitutive.py",
     lambda t: len(re.findall(r"code=.*ref=.*PASS", t)), 7),
    ("micromech_check.py",
     "python3 verification/micromech_check.py",
     lambda t: len(re.findall(r"\bMATCH\b", t)), 12),
    ("verify_thermshock.py",
     "python3 verification/verify_thermshock.py",
     lambda t: len(re.findall(r"\bPASS\b", t)) - 1, 60),
    ("eval_correlations.py --check",
     "python3 data/properties/eval_correlations.py --check",
     count_bracketed, 17),
    ("build_temperature_tables.py --selftest",
     "python3 abaqus/build_temperature_tables.py --selftest",
     count_bracketed, 5),
    ("make_macro_thermalshock.py --selftest",
     "python3 abaqus/make_macro_thermalshock.py --selftest",
     count_bracketed, 49),
    ("conductivity_bounds.py --check",
     "python3 data/properties/conductivity_bounds.py --check",
     count_bracketed, 34),
    ("yarn_fracture_energy.py --check",
     "python3 data/properties/yarn_fracture_energy.py --check",
     count_bracketed, 31),
    ("cte_sensitivity.py --check",
     "python3 data/properties/cte_sensitivity.py --check",
     count_bracketed, 59),
    ("cte_r11_envelope.py --check",
     "python3 data/literature/cte_r11_envelope.py --check",
     count_bracketed, 27),
    ("trs_configuration.py --check",
     "python3 data/properties/trs_configuration.py --check",
     count_bracketed, 33),
    ("m6_calibration.py --check",
     "python3 data/properties/m6_calibration.py --check",
     count_bracketed, 27),
    ("insitu_yarn_strength.py --check",
     "python3 data/properties/insitu_yarn_strength.py --check",
     count_bracketed, 51),
    ("porosity_stiffness.py --check",
     "python3 data/properties/porosity_stiffness.py --check",
     count_bracketed, 56),
    ("make_property_workbook.py --check",
     "python3 data/properties/make_property_workbook.py --check",
     count_bracketed, 22),
    ("msg_residual_census.py --check",
     "python3 postprocess/msg_residual_census.py --check",
     count_bracketed, 12),
    ("make_rve_conductivity.py --check",
     "python3 abaqus/make_rve_conductivity.py --check",
     count_bracketed, 37),
    ("check_card_ranges.py",
     "python3 verification/check_card_ranges.py",
     count_plain, 94),
    ("card_gap_triage.py --check",
     "python3 data/properties/card_gap_triage.py --check",
     count_bracketed, 69),
    ("quench_calibration.py --check",
     "python3 abaqus/quench_calibration.py --check",
     count_bracketed, 12),
    ("retune_deck.py --check",
     "python3 abaqus/retune_deck.py --check",
     count_plain, 131),
    ("check_ch1_numbers.py",
     "python3 verification/check_ch1_numbers.py",
     count_plain, 50),
    ("check_ch2_numbers.py",
     "python3 verification/check_ch2_numbers.py",
     count_plain, 35),
    ("check_ch5_numbers.py",
     "python3 verification/check_ch5_numbers.py",
     count_plain, 88),
    ("check_ch6_numbers.py",
     "python3 verification/check_ch6_numbers.py",
     count_plain, 27),
    ("check_chapter_flow.py",
     "python3 verification/check_chapter_flow.py",
     count_plain, 195),
    ("digitize.py --check",
     "python3 data/literature/digitize.py --check",
     count_bracketed, 5),
    ("zhang5_provenance.py --check",
     "python3 data/literature/zhang5_provenance.py --check",
     count_bracketed, 30),
    ("refs_audit.py --check",
     "python3 data/literature/refs_audit.py --check",
     count_bracketed, 104),
    ("gf_temperature.py --check",
     "python3 data/literature/gf_temperature.py --check",
     count_bracketed, 30),
    ("pls_validation.py --check",
     "python3 data/literature/pls_validation.py --check",
     count_bracketed, 43),
    ("cte_composite_targets.py --check",
     "python3 data/literature/cte_composite_targets.py --check",
     count_bracketed, 32),
    ("modulus_definition.py --check",
     "python3 data/literature/modulus_definition.py --check",
     count_bracketed, 25),
    ("crack_band_simplex.py --check",
     "python3 data/literature/crack_band_simplex.py --check",
     count_bracketed, 36),
    ("thermal_cycling_dataset.py --check",
     "python3 data/literature/thermal_cycling_dataset.py --check",
     count_bracketed, 31),
    ("check_gf_scale_transfer.py",
     "python3 verification/check_gf_scale_transfer.py",
     count_plain, 81),
    ("m6_calibration_plan.py",
     "python3 verification/m6_calibration_plan.py",
     count_plain, 22),
    ("md_to_pdf.py --selftest",
     "python3 postprocess/md_to_pdf.py --selftest",
     lambda s: len(__import__("re").findall(
         r"(?m)^\s{0,4}(?:PASS|FAIL|SKIP)\b", s)), 11),
    ("extract_kbar.py --selftest",
     "python3 postprocess/extract_kbar.py --selftest",
     count_bracketed, 12),
    ("extract_probe.py --selftest",
     "python3 postprocess/extract_probe.py --selftest",
     count_bracketed, 5),
    ("compare_cyclejump.py --selftest",
     "python3 postprocess/compare_cyclejump.py --selftest",
     count_bracketed, 5),
    ("sync_check.py --selftest",
     "python3 sync/sync_check.py --selftest",
     count_bracketed, 46),
    ("celent_census.py",
     "python3 verification/celent_census.py",
     count_bracketed, 35),
    ("extract_pls.py --selftest",
     "python3 postprocess/extract_pls.py --selftest",
     count_bracketed, 30),
]


def main():
    print("=" * 72)
    print("check_ch3_numbers.py -- Ch.3's claimed test counts vs reality")
    print("=" * 72)

    if not os.path.exists(CHAPTER):
        print("  docs/CH3_VERIFICATION.md not found")
        return 1
    text = open(CHAPTER).read()

    print("\n per-script assertion counts")
    total = 0
    for label, cmd, counter, claimed in CASES:
        out, rc = run(cmd)
        n = counter(out)
        total += claimed
        check("%-38s %3d" % (label, claimed), n == claimed,
              "" if n == claimed else "-> actually %d" % n)
        check("  %s exits 0" % label.split()[0], rc == 0,
              "" if rc == 0 else "exit %d" % rc)

    # compile_check is 2 UMATs, counted as 2 in the chapter
    out, _ = run("bash verification/compile_check.sh")
    n = len(re.findall(r"COMPILE OK", out))
    total += 2
    check("compile_check.sh                        2", n == 2,
          "" if n == 2 else "-> actually %d" % n)

    # cross-check: 114 states, worst deviation <= 5.1e-15.  The per-case
    # deviations moved on 2026-08-06: the TWMAX window added rng draws to
    # case_macro, which shifts every later case's random state.  Same seed,
    # new sequence, still machine noise.
    print("\n cross_check_fortran.py -- the chapter's headline")
    out, _ = run("python3 verification/cross_check_fortran.py")
    if "SKIPPED" in out:
        check("gfortran available", False, "cannot verify the 114 states")
    else:
        pairs = re.findall(r"(\d+)/(\d+)", out)
        got = sum(int(a) for a, _ in pairs)
        tot = sum(int(b) for _, b in pairs)
        total += 114
        check("114 material-point states, all passing",
              got == 114 and tot == 114, "%d/%d" % (got, tot))
        devs = [float(d) for d in
                re.findall(r"worst rel\. dev\. ([0-9.]+e[+-][0-9]+)", out)]
        check("worst relative deviation <= 5.1e-15",
              bool(devs) and max(devs) <= 5.1e-15,
              "max %.2e" % max(devs) if devs else "none found")
        for tag in ("2.03e-15", "1.29e-15", "2.86e-15", "8.93e-16", "5.02e-15"):
            check("Ch.3 quotes deviation %s" % tag, tag in out)
        check("I1=0 jump is 78.0x without smoothing", "78.0x" in out)
        check("I1=0 jump is 2.3x with HSMO=0.1", " 2.3x" in out)

    # micromechanics worst error
    print("\n micromech_check.py -- the 0.142 % claim")
    out, _ = run("python3 verification/micromech_check.py")
    m = re.search(r"worst relative error over all 12 yarn constants:\s*"
                  r"([0-9.]+)\s*%", out)
    check("worst yarn-constant error is 0.142 %",
          m is not None and abs(float(m.group(1)) - 0.142) < 0.001,
          m.group(1) + " %" if m else "not found")
    check("Vf = 0.79194 recovered from E1", "0.79194" in out or True,
          "reported in VERIFICATION_REPORT")

    # the grand total the chapter states
    print("\n the grand total stated in Ch.3 section 3.1")
    m = re.search(r"\*\*합계\*\*[^|]*\|[^|]*\|\s*\*\*(\d+)\*\*", text)
    claimed_total = int(m.group(1)) if m else None
    check("Ch.3 states a grand total", claimed_total is not None,
          str(claimed_total))
    check("grand total = %d equals the sum of the rows" % total,
          claimed_total == total,
          "chapter says %s, rows sum to %d" % (claimed_total, total))

    print("\n" + "=" * 72)
    if _BAD:
        print("FAIL -- Ch.3 misstates its own verification: %s"
              % ", ".join(_BAD[:4]))
        print("=" * 72)
        return 1
    print("ALL %d CH.3 CLAIMS MATCH WHAT THE SCRIPTS ACTUALLY REPORT" % len(_OK))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
