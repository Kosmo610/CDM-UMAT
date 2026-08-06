#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch6_numbers.py  --  ROUND 1 for Chapter 6 (skeleton stage)
================================================================
Chapter 6 is the results-and-discussion chapter, drafted BEFORE any result
exists.  Everything quantitative in it today is a VALIDATION TARGET copied
from the literature, and every one of those targets already lives in
data/literature/thermal_cycling_dataset.py.  A restated chapter is the
easiest chapter to get wrong -- every number arrived by being copied -- so
this round re-derives each target from the dataset module and asserts the
chapter quotes it exactly.

It also checks the two structural promises the skeleton makes:

  A. every literature target (T1-T6) matches thermal_cycling_dataset.py
  B. the severity-paradox arithmetic in section 6.3 is the dataset's own
  C. every result slot is explicitly marked pending -- the chapter must not
     read as if a number exists before the analysis ran
  D. the metric assignment (modulus = cycle damage, PLS = TRS) is stated,
     and matches the correction that narrowed a1-0012
  E. citations use keys that Chapter 2's reference table actually lists

Run:  python3 verification/check_ch6_numbers.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, os.path.join(ROOT, "data", "literature"))

import thermal_cycling_dataset as tcd  # noqa: E402

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def main():
    print("=" * 78)
    print("ROUND 1 -- check_ch6_numbers.py: are Ch.6's targets the dataset's?")
    print("=" * 78)

    path = os.path.join(DOCS, "CH6_RESULTS_DISCUSSION.md")
    check("chapter file exists", os.path.exists(path), path)
    if not os.path.exists(path):
        return 1
    txt = open(path, encoding="utf-8").read()

    # ------------------------------------------------------------------ A
    print("\n A. every target is the dataset's value, re-derived not re-typed")
    rows = {(r[0], r[7], r[5]): r for r in tcd.DATA}

    def row(ref, what, n):
        return rows.get((ref, what, n))

    z_str = row("[03]", "tensile strength", 60)
    z_mod = row("[03]", "tensile modulus", 60)
    y_str = row("[02]", "flexural strength", 100)
    check("T1: Zhang modulus 45 % is in the dataset and the chapter",
          z_mod is not None and abs(z_mod[6] - 45.0) < 1e-9 and "45 %" in txt)
    check("T2: Zhang strength 63 % is in the dataset and the chapter",
          z_str is not None and abs(z_str[6] - 63.0) < 1e-9 and "63 %" in txt)
    check("T3: Yin strength 83 % is in the dataset and the chapter",
          y_str is not None and abs(y_str[6] - 83.0) < 1e-9 and "83 %" in txt)
    check("T4: Wei 2D curve quoted exactly",
          "526" in txt and "498" in txt and "473" in txt and "463" in txt
          and tuple(tcd.WEI_2D) == (526.0, 498.0, 473.0, 463.0))
    check("T5: constrained stresses match R68",
          abs(tcd.R68["constraint_start"] - 62.5) < 1e-9
          and abs(tcd.R68["constraint_end"] - (-14.0)) < 1e-9
          and "62.5" in txt and "14.0" in txt)
    check("T5: damage strain 0.06 % quoted",
          abs(tcd.R68["damage_strain"] - 0.06) < 1e-9 and "0.06 %" in txt)
    check("T5: swing 76.5 MPa is start minus end",
          "76.5" in txt and abs((tcd.R68["constraint_start"]
                                 - tcd.R68["constraint_end"]) - 76.5) < 1e-9)
    atm = {r[4]: r[6] for r in tcd.DATA if r[0] == "[43]"}
    check("T6: all four [43] atmospheres quoted with dataset values",
          all(("%.2f" % v) in txt for v in atm.values()) and len(atm) == 4)
    check("T6: atmosphere ordering argon > dry O2 > water vapour > wet O2",
          atm["argon"] > atm["dry O2"] > atm["water vapour"] > atm["wet O2"])

    # ------------------------------------------------------------------ B
    print("\n B. the severity-paradox arithmetic is the dataset's own")
    ry = (100.0 - y_str[6]) / y_str[5] / (y_str[3] - y_str[2]) if y_str else 0
    rz = (100.0 - z_str[6]) / z_str[5] / (z_str[3] - z_str[2]) if z_str else 0
    check("per-cycle-per-K rates re-derive to 1.70e-4 and 1.03e-3",
          abs(ry - 1.70e-4) < 1e-6 and abs(rz - 1.03e-3) < 1e-5,
          "%.2e / %.2e" % (ry, rz))
    check("the 6.0x ratio in the chapter is the derived ratio",
          "6.0" in txt and abs(rz / ry - 6.05) < 0.1, "%.2fx" % (rz / ry))
    for needle in ("1.70", "1.03"):
        check("chapter quotes the rate %s" % needle, needle in txt)

    # ------------------------------------------------------------------ C
    print("\n C. no result is stated before it exists")
    slots = re.findall(r"\[결과 대기[^\]]*\]", txt)
    check("at least 4 explicit pending-result slots", len(slots) >= 4,
          "%d found" % len(slots))
    check("the header says the chapter has no result numbers yet",
          "결과 수치는 아직 없다" in txt)
    for sec in ("6.2.2", "6.3", "6.4", "6.5", "6.7"):
        # sections that promise results must each carry a pending slot
        body = re.search(r"#+ %s.*?(?=\n#+ |\Z)" % re.escape(sec), txt, re.S)
        check("section %s carries its pending slot" % sec,
              bool(body) and "[결과 대기" in body.group(0))

    # ------------------------------------------------------------------ D
    print("\n D. the metric assignment survived intact")
    check("modulus is the primary cycle-damage target",
          "1차 정량 표적" in txt and "$E(N)$" in txt)
    check("PLS is confined to the TRS comparison",
          "TRS" in txt and "PLS" in txt and "같은 목적함수에 넣지 않는다" in txt)
    check("the stress-free temperature is held constant, citing [71][72]",
          "[71]" in txt and "[72]" in txt and "무응력" in txt)
    check("the 900-1200 C hole is admitted, not papered over",
          "데이터가 없다" in txt and "1000 °C" in txt)
    check("the one-atmosphere limitation is stated",
          "분위기" in txt and "재보정" in txt)

    # ------------------------------------------------------------------ E
    print("\n E. every bare citation is listed in Chapter 2's table")
    ch2 = open(os.path.join(DOCS, "CH2_LITERATURE_REVIEW.md"),
               encoding="utf-8").read()
    listed = set(re.findall(
        r"^\|\s*\*{0,2}\[(\d{1,2}[a-b]?|[SC]\d{1,2})\]\*{0,2}\s*\|",
        ch2, re.M))
    listed = {k.lstrip("0") for k in listed}
    cited = {m.group(2) for m in
             re.finditer(r"(refs/)?\[(\d{1,2}[a-b]?)\]", txt)
             if not m.group(1)}
    orphans = sorted(k for k in cited if k.lstrip("0") not in listed)
    check("no Ch.6 citation is missing from Ch.2's reference table",
          not orphans, ", ".join("[%s]" % k for k in orphans))

    print("\n" + "=" * 78)
    if _BAD:
        print("ROUND 1 (CH.6) FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ROUND 1 (CH.6) PASS -- ALL %d TARGET CLAIMS HOLD" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
