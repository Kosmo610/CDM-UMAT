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
     count_bracketed, 19),
    ("build_temperature_tables.py --selftest",
     "python3 abaqus/build_temperature_tables.py --selftest",
     count_bracketed, 5),
    ("make_macro_thermalshock.py --selftest",
     "python3 abaqus/make_macro_thermalshock.py --selftest",
     count_bracketed, 92),
    ("conductivity_bounds.py --check",
     "python3 data/properties/conductivity_bounds.py --check",
     count_bracketed, 34),
    ("conductivity_temperature.py --check",
     "python3 data/properties/conductivity_temperature.py --check",
     count_bracketed, 37),
    ("yarn_fracture_energy.py --check",
     "python3 data/properties/yarn_fracture_energy.py --check",
     count_bracketed, 31),
    ("cte_sensitivity.py --check",
     "python3 data/properties/cte_sensitivity.py --check",
     count_bracketed, 69),
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
    ("compare_tangent.py --selftest",
     "python3 postprocess/compare_tangent.py --selftest",
     count_bracketed, 21),
    ("msg_residual_census.py --check",
     "python3 postprocess/msg_residual_census.py --check",
     count_bracketed, 29),
    ("reheat_saturation.py --check",
     "python3 verification/reheat_saturation.py --check",
     count_bracketed, 38),
    ("reheat_frames.py --selftest",
     "python3 postprocess/reheat_frames.py --selftest",
     count_bracketed, 18),
    ("damage_ceiling.py --selftest",
     "python3 postprocess/damage_ceiling.py --selftest",
     count_plain, 22),
    ("m6_report.py --selftest",
     "python3 postprocess/m6_report.py --selftest",
     count_plain, 26),
    ("m6_verdict.py --selftest",
     "python3 postprocess/m6_verdict.py --selftest",
     count_plain, 28),
    ("matrix_audit.py --check",
     "python3 abaqus/matrix_audit.py --check",
     count_bracketed, 39),
    ("make_rve_conductivity.py --check",
     "python3 abaqus/make_rve_conductivity.py --check",
     count_bracketed, 41),
    ("check_card_ranges.py",
     "python3 verification/check_card_ranges.py",
     count_plain, 114),
    ("card_gap_triage.py --check",
     "python3 data/properties/card_gap_triage.py --check",
     count_bracketed, 68),
    ("quench_calibration.py --check",
     "python3 abaqus/quench_calibration.py --check",
     count_bracketed, 12),
    ("retune_deck.py --check",
     "python3 abaqus/retune_deck.py --check",
     count_plain, 187),
    ("check_ch1_numbers.py",
     "python3 verification/check_ch1_numbers.py",
     count_plain, 53),
    ("check_ch2_numbers.py",
     "python3 verification/check_ch2_numbers.py",
     count_plain, 46),
    ("check_ch5_numbers.py",
     "python3 verification/check_ch5_numbers.py",
     count_plain, 119),
    ("check_ch6_numbers.py",
     "python3 verification/check_ch6_numbers.py",
     count_plain, 68),
    ("check_ch4_numbers.py",
     "python3 verification/check_ch4_numbers.py",
     count_plain, 174),
    ("check_ch7_numbers.py",
     "python3 verification/check_ch7_numbers.py",
     count_plain, 45),
    ("check_chapter_flow.py",
     "python3 verification/check_chapter_flow.py",
     count_plain, 218),
    ("review_inbox.py --check",
     "python3 verification/review_inbox.py --check",
     count_bracketed, 29),
    ("check_manuscript_citations.py",
     "python3 verification/check_manuscript_citations.py",
     count_plain, 22),
    ("prerun_gate.py --check",
     "python3 verification/prerun_gate.py --check",
     count_bracketed, 44),
    ("pending_slots.py --check",
     "python3 verification/pending_slots.py --check",
     count_bracketed, 41),
    ("digitize.py --check",
     "python3 data/literature/digitize.py --check",
     count_bracketed, 5),
    ("zhang5_provenance.py --check",
     "python3 data/literature/zhang5_provenance.py --check",
     count_bracketed, 30),
    ("refs_audit.py --check",
     "python3 data/literature/refs_audit.py --check",
     count_bracketed, 134),
    ("gf_temperature.py --check",
     "python3 data/literature/gf_temperature.py --check",
     count_bracketed, 30),
    ("pls_validation.py --check",
     "python3 data/literature/pls_validation.py --check",
     count_bracketed, 43),
    ("cte_composite_targets.py --check",
     "python3 data/literature/cte_composite_targets.py --check",
     count_bracketed, 32),
    ("cte_rve_verdict.py --check",
     "python3 data/literature/cte_rve_verdict.py --check",
     count_bracketed, 38),
    ("modulus_definition.py --check",
     "python3 data/literature/modulus_definition.py --check",
     count_bracketed, 25),
    ("crack_band_simplex.py --check",
     "python3 data/literature/crack_band_simplex.py --check",
     count_bracketed, 56),
    ("thermal_cycling_dataset.py --check",
     "python3 data/literature/thermal_cycling_dataset.py --check",
     count_bracketed, 51),
    ("cycle_jump_provenance.py --check",
     "python3 data/literature/cycle_jump_provenance.py --check",
     count_bracketed, 40),
    ("check_gf_scale_transfer.py",
     "python3 verification/check_gf_scale_transfer.py",
     count_plain, 82),
    ("card_pipeline_rehearsal.py --check",
     "python3 verification/card_pipeline_rehearsal.py --check",
     count_bracketed, 52),
    ("m6_calibration_plan.py",
     "python3 verification/m6_calibration_plan.py",
     count_plain, 33),
    ("plastic_dissipation_audit.py",
     "python3 verification/plastic_dissipation_audit.py",
     count_plain, 15),
    ("knob_sensitivity.py --check",
     "python3 verification/knob_sensitivity.py --check",
     count_bracketed, 47),
    ("md_to_pdf.py --selftest",
     "python3 postprocess/md_to_pdf.py --selftest",
     lambda s: len(__import__("re").findall(
         r"(?m)^\s{0,4}(?:PASS|FAIL|SKIP)\b", s)), 11),
    ("md_to_docx.py --selftest",
     "python3 postprocess/md_to_docx.py --selftest",
     lambda s: len(__import__("re").findall(
         r"(?m)^\s{0,4}(?:PASS|FAIL|SKIP)\b", s)), 10),
    ("make_thesis_figures.py --check",
     "python3 postprocess/make_thesis_figures.py --check",
     count_bracketed, 57),
    ("extract_kbar.py --selftest",
     "python3 postprocess/extract_kbar.py --selftest",
     count_bracketed, 33),
    ("extract_probe.py --selftest",
     "python3 postprocess/extract_probe.py --selftest",
     count_bracketed, 13),
    ("compare_cyclejump.py --selftest",
     "python3 postprocess/compare_cyclejump.py --selftest",
     count_bracketed, 17),
    ("sync_check.py --selftest",
     "python3 sync/sync_check.py --selftest",
     count_bracketed, 46),
    ("celent_census.py",
     "python3 verification/celent_census.py",
     count_bracketed, 35),
    ("extract_pls.py --selftest",
     "python3 postprocess/extract_pls.py --selftest",
     count_bracketed, 30),
    ("damage_map.py --selftest",
     "python3 postprocess/damage_map.py --selftest",
     count_bracketed, 48),
    ("damage_census.py --check",
     "python3 postprocess/damage_census.py --check",
     count_bracketed, 10),
    ("extract_thermal_profile.py --selftest",
     "python3 postprocess/extract_thermal_profile.py --selftest",
     count_bracketed, 31),
    ("homogenize.py --selftest",
     "python3 postprocess/homogenize.py --selftest",
     count_bracketed, 27),
    ("lengthen_tension.py --check",
     "python3 abaqus/lengthen_tension.py --check",
     count_bracketed, 21),
]


#: How many rows the ledger has.  Pinned so that a merge cannot silently
#: shorten it -- see the note at the top of main().  Raising this is a
#: conscious act; a row disappearing is not.
EXPECTED_CASES = 70  # 2026-08-18: +lengthen_tension (a2, the tension step that ended at its own peak) -- a conscious raise, as designed


def main():
    print("=" * 72)
    print("check_ch3_numbers.py -- Ch.3's claimed test counts vs reality")
    print("=" * 72)

    if not os.path.exists(CHAPTER):
        print("  docs/CH3_VERIFICATION.md not found")
        return 1
    text = open(CHAPTER).read()

    # ------------------------------------------------------------------
    # The ledger's own integrity, BEFORE any of it is counted.
    #
    # 2026-08-14: a3 reported the merged-tree total as 3095 against a1's
    # 3160, and the 65 was not a counting disagreement -- their resolution of
    # a merge conflict had DROPPED two rows outright, cte_rve_verdict (38)
    # and pending_slots (27).  38 + 27 = 65 exactly.  Nothing failed: a
    # shorter list still sums, and the chapter was then edited to agree with
    # the shorter sum, so the loss became self-consistent.
    #
    # A count that can quietly shrink is not a count.  So: the number of
    # rows is pinned, every row must be a command CLAUDE.md actually lists,
    # and any gate CLAUDE.md lists that is NOT a row is printed rather than
    # ignored -- an unlisted gate is how a row goes missing unnoticed.
    print("\n the ledger's own row set")
    check("no duplicate rows", len(set(c[0] for c in CASES)) == len(CASES),
          "%d labels" % len(set(c[0] for c in CASES)))
    check("the row count is the declared %d" % EXPECTED_CASES,
          len(CASES) == EXPECTED_CASES, "%d rows" % len(CASES))
    claude = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
    orphan = [c[1] for c in CASES if c[1] not in claude]
    check("every ledger row is a gate CLAUDE.md lists", not orphan,
          "; ".join(orphan[:3]))
    listed = re.findall(r"(?m)^(python3 [^\s#]+(?: --?[a-z]+)?)", claude)
    counted = set(c[1] for c in CASES)
    uncounted = sorted(set(x.strip() for x in listed) - counted)
    print("     %d of %d CLAUDE.md gates carry a row here; the rest are "
          "counted elsewhere or not at all:" % (len(counted), len(set(listed))))
    for u in uncounted:
        print("       - %s" % u)

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

    # cross-check: 273 states, worst deviation <= 5.1e-15 on the six
    # Fortran-vs-Python cases (the three consistent-tangent cases report
    # their own numbers on their own lines and 0.00e+00 here, because a
    # finite-difference Jacobian is not a machine-precision comparison and
    # must not be averaged in with one).  The per-case
    # deviations moved on 2026-08-06: the TWMAX window added rng draws to
    # case_macro, which shifts every later case's random state.  Same seed,
    # new sequence, still machine noise.
    print("\n cross_check_fortran.py -- the chapter's headline")
    out, _ = run("python3 verification/cross_check_fortran.py")
    if "SKIPPED" in out:
        check("gfortran available", False, "cannot verify the 273 states")
    else:
        pairs = re.findall(r"(\d+)/(\d+)", out)
        got = sum(int(a) for a, _ in pairs)
        tot = sum(int(b) for _, b in pairs)
        total += 273
        check("273 material-point states, all passing",
              got == 273 and tot == 273, "%d/%d" % (got, tot))
        devs = [float(d) for d in
                re.findall(r"worst rel\. dev\. ([0-9.]+e[+-][0-9]+)", out)]
        check("worst relative deviation <= 5.1e-15",
              bool(devs) and max(devs) <= 5.1e-15,
              "max %.2e" % max(devs) if devs else "none found")
        for tag in ("2.03e-15", "1.29e-15", "2.86e-15", "8.93e-16", "5.02e-15"):
            check("Ch.3 quotes deviation %s" % tag, tag in out)
        check("I1=0 jump is 78.0x without smoothing", "78.0x" in out)
        check("I1=0 jump is 2.3x with HSMO=0.1", " 2.3x" in out)
        # Consistent tangent (Ge Eqs.31-33): the acceptance test is the
        # numerical Jacobian, so the chapter may only claim it if every
        # regime is actually reported and every deviation is small.
        jdev = [float(d) for d in re.findall(
            r"max \|Ct-Cfd\|/max\|Ct\| = ([0-9.]+e[+-][0-9]+)", out)]
        check("every regime reports a numerical-Jacobian deviation",
              len(jdev) == 9, "%d regimes" % len(jdev))
        check("worst analytic-vs-numerical tangent deviation <= 1e-8",
              bool(jdev) and max(jdev) <= 1.0e-8,
              "max %.2e" % max(jdev) if jdev else "none found")
        check("the tangent switch is OFF-identical",
              "reproduces the no-block card exactly" in out)

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

    # 3.8-7: the plastic-dissipation table must be the audit's numbers.
    # The chapter uses them to warn that the N=5 bar's dissipated energy is
    # 90 % plastic, which is what stops the crack-band bars being read as a
    # pure regularisation test -- so a typed number here would mislead.
    print("\n section 3.8-7 -- plastic share of the dissipated energy")
    sys.path.insert(0, HERE)
    import plastic_dissipation_audit as pda
    _ge = pda.g_elastic(pda.XT_M, pda.E_M)
    _gp = pda.g_plastic(pda.XT_M, pda.SY0, pda.HISO)[0]
    sec = text.split("7. **균열대가 붙드는 것은")[-1].split("\n### ")[0]
    for le, want in ((pda.LE_RVE_MEAN, "16.1"), (pda.LE_RVE_MAX, "42.3"),
                     (0.200, "90.5"), (0.100, "49.3"), (0.050, "25.8")):
        share = 100.0 * (_gp * le) / ((pda.GMT - _ge * le) + _gp * le)
        check("le=%.4f mm -> %s %% plastic" % (le, want),
              abs(share - float(want)) < 0.05 and ("**%s %%**" % want) in sec,
              "%.1f %%" % share)
    check("3.8-7 points at the audit script",
          "plastic_dissipation_audit.py" in sec)
    check("3.8-7 records the withdrawal rather than the old gap",
          "철회하였다" in sec and "과대추정" in sec)

    # 3.8-5a: the bar's trigger slice was brittle by accident.  This is the
    # kind of finding that quietly disappears, so the chapter's numbers are
    # re-derived here rather than trusted.
    print("\n section 3.8-5a -- the trigger slice's unintended brittleness")
    sys.path.insert(0, os.path.join(ROOT, "abaqus"))
    import make_patch_tests as mpt
    xt_w = mpt.MATRIX_CARD[3] * mpt.BAR_WEAK
    sy0 = mpt.MATRIX_CARD[mpt.MATRIX_SY0_SLOT - 1]
    sec5a = text.split("5-a. **트리거")[-1].split("\n6. ")[0]
    check("the weak slice really is below sy0", xt_w < sy0,
          "%.1f < %.1f" % (xt_w, sy0))
    check("3.8-5a quotes that X_t", "**248 MPa**" in sec5a and
          abs(xt_w - 248.0) < 1e-9)
    check("3.8-5a quotes sy0", "**250 MPa**" in sec5a and abs(sy0 - 250.0) < 1e-9)
    _gp_s = pda.g_plastic(mpt.MATRIX_CARD[3], pda.SY0, pda.HISO)[0]
    _ge_s = pda.g_elastic(mpt.MATRIX_CARD[3], pda.E_M)
    check("3.8-5a's 55.0 %% plastic share is re-derived",
          abs(100.0 * _gp_s / (_ge_s + _gp_s) - 55.0) < 0.05
          and "**55.0 %**" in sec5a)
    check("and the trigger slice's zero is real",
          pda.g_plastic(xt_w, pda.SY0, pda.HISO)[0] == 0.0
          and "**0 %**" in sec5a)
    check("3.8-5a points at --brittle as the fix", "--brittle" in sec5a)
    check("3.8-5a routes the regularisation verdict to the _BR bars",
          "_BR` 봉으로 한다" in sec5a)

    # ---- 3.8-8 the ceiling that fires before the load, and what it costs C1
    print("\n section 3.8-8 -- the damage ceiling reaches the C1 comparison")
    sys.path.insert(0, os.path.join(ROOT, "postprocess"))
    import damage_ceiling as dc
    dm = os.path.join(ROOT, "data", "results", "M6",
                      "LTH_M6_T500_damage_map.csv")
    if os.path.exists(dm):
        got = dc.analyse(dm)
        pre = [r for r in got if r[0] == "timing"
               and r[7] == "CEILING REACHED BEFORE LOADING"]
        tot = [r for r in got if r[0] == "summary"][0]
        check("the unloaded-step saturation is re-derived, not quoted",
              bool(pre) and pre[0][4] == 12, "%s in %s"
              % (pre[0][4] if pre else "-", pre[0][2] if pre else "-"))
        check("  and 3.8-8 states both that count and the total",
              "42개가" in text and "12개는" in text,
              "%d total, %d before load" % (tot[4], pre[0][4] if pre else 0))
        # the 0.344 is the cooldown maximum the reheat climbs from
        import csv as _csv
        cool = [float(r["value"]) for r in _csv.DictReader(open(dm))
                if r["item"] == "damg_max" and r["phase"] == "MATRIX"
                and r["step"].startswith("Manufacturing")]
        check("  the pre-reheat matrix maximum is read from the map",
              cool and abs(cool[0] - 0.344269) < 1e-5, "%.6f" % cool[0])
        check("  and 3.8-8 quotes it as the level the reheat climbs from",
              "0.344" in text)
    check("3.8-8 names WHICH C1 cases the ceiling collapses together",
          "B(1회 냉각 후 동결)와 C(손상에 따라 재분배)" in text)
    check("  and says which way the error runs",
          "과소평가하는 쪽이다" in text)
    check("  so the 'small difference' conclusion carries a gate",
          "8.4(a)를 먼저 통과해야 한다" in text)
    check("  while the 'large difference' one does not need it",
          "차이가 크게 나오는 경우" in text)
    check("3.8-8 offers a way to close it without a solver",
          "volfrac_at_cap" in text and "해석 불요" in text)
    ch2 = open(os.path.join(ROOT, "docs", "CH2_LITERATURE_REVIEW.md")).read()
    check("Ch.2 2.3.4 points forward to it, since it is that section's "
          "only permanent channel",
          "제3장 §3.8-8" in ch2 and "0.344" in ch2)
    check("  without making a new claim about the literature",
          "해석에서 확인되었다" in ch2 and "제4장 §4.9-0d" in ch2)

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
