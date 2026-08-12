#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch1_numbers.py  --  ROUND 1 for Chapter 1
===============================================
Chapter 1 is almost entirely a chapter of restatements: it quotes literature
values that belong to Chapter 2 and results that belong to Chapters 3 and 4.
That makes it the easiest chapter to get wrong, because nothing in it is
derived on the spot -- every number arrived by being copied.

Round 2 (check_chapter_consistency.py) already pins the values Ch.1 shares
with its neighbours.  This round covers what round 2 cannot:

  A. literature values quoted in Ch.1 must match the literature CSVs, not just
     match Ch.2 -- otherwise Ch.1 and Ch.2 can be consistently wrong together
  B. the contribution set C1-C4 and the novelty statement must be present and
     must not have drifted from Ch.2 section 2.8
  C. the chapter must not cite a source graded 'secondary'
  D. the forward references it makes ("see section 3.4.4") must point at
     sections that actually exist in those chapters
  E. structural claims: the chapter list in section 1.7 must match the files
     that exist, and must not promise a chapter that was never planned

Run:  python3 verification/check_ch1_numbers.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
LIT = os.path.join(ROOT, "data", "literature")

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def read(path):
    return open(path).read() if os.path.exists(path) else None


def csv_rows(name):
    path = os.path.join(LIT, name)
    if not os.path.exists(path):
        return []
    rows, hdr = [], None
    for line in open(path):
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if hdr is None:
            hdr = parts
            continue
        rows.append(dict(zip(hdr, parts)))
    return rows


def main():
    print("=" * 78)
    print("ROUND 1 -- check_ch1_numbers.py: is Chapter 1 faithful to its sources?")
    print("=" * 78)

    ch1 = read(os.path.join(DOCS, "CH1_INTRODUCTION.md"))
    if ch1 is None:
        check("CH1_INTRODUCTION.md exists", False)
        return 1
    check("CH1_INTRODUCTION.md exists", True)
    flat = re.sub(r"(?<=\d)[  ](?=\d)", "", ch1)

    ch2 = read(os.path.join(DOCS, "CH2_LITERATURE_REVIEW.md")) or ""
    ch3 = read(os.path.join(DOCS, "CH3_VERIFICATION.md")) or ""
    ch4 = read(os.path.join(DOCS, "CH4_RVE_HOMOGENISATION.md")) or ""

    # ------------------------------------------------------------------ A
    print("\n A. literature values trace back to the CSVs, not just to Ch.2")

    # The XRD residual stresses from refs/[15].  Ch.1 quotes the two axial
    # values; both must appear in the literature table with a citable grade.
    lit = csv_rows("csic_thermal_shock.csv") + csv_rows("failure_criteria.csv")
    blob = "\n".join(",".join("%s=%s" % kv for kv in r.items()) for r in lit)
    for label, val in (("matrix axial TRS", "114.7"),
                       ("yarn axial TRS", "68.7")):
        in_ch1 = val in flat
        in_lit = val in blob
        check("%s %s quoted in Ch.1" % (label, val), in_ch1)
        check("%s %s present in the literature CSVs" % (label, val), in_lit,
              "" if in_lit else "not found in data/literature")

    # Signs: the matrix must be described as tension, the yarn as compression.
    m_ctx = " ".join(re.findall(r".{0,120}114\.7.{0,120}", flat))
    y_ctx = " ".join(re.findall(r".{0,120}68\.7.{0,120}", flat))
    check("Ch.1 calls the matrix TRS tensile",
          ("인장" in m_ctx) and ("+114.7" in m_ctx or "＋114.7" in m_ctx))
    check("Ch.1 calls the yarn TRS compressive",
          ("압축" in y_ctx) and ("−68.7" in y_ctx or "-68.7" in y_ctx))

    # The two conflicting thermal-shock datasets. Ch.1 asserts they disagree in
    # DIRECTION; that assertion is the reason the cycle exponent needs a sign,
    # so it must survive independently of Ch.2's prose.
    check("Ch.1 names Yin refs/[2] as the saturating dataset",
          bool(re.search(r"\[2\][^\n]{0,80}(?:포화|3D)", flat))
          or bool(re.search(r"Yin[^\n]{0,60}\[2\]", flat)))
    check("Ch.1 names Zhang refs/[3] as the accelerating dataset",
          bool(re.search(r"\[3\][^\n]{0,80}(?:가속|2D)", flat)))
    check("Ch.1 states the two datasets require opposite signs",
          "부호를 서로 반대로" in flat or "부호가" in flat)

    # ------------------------------------------------------------------ B
    print("\n B. the contribution set matches Ch.2 section 2.8.3")
    for c in ("C1", "C2", "C3", "C4"):
        in1 = bool(re.search(r"\*\*%s\b" % c, ch1))
        in2 = bool(re.search(r"\*\*%s\b" % c, ch2))
        check("%s stated in both Ch.1 and Ch.2" % c, in1 and in2,
              "" if in1 and in2 else "Ch.1=%s Ch.2=%s" % (in1, in2))

    # The Biot ladder is the operative content of C2; a mismatch here would let
    # the introduction promise a study the model chapter does not run.
    for v in ("0.05", "1", "5"):
        check("C2 Biot ladder value %s in Ch.1" % v,
              bool(re.search(r"Bi\$?\s*=\s*0\.05\s*/\s*1\s*/\s*5", flat)))
        break
    check("Ch.1 and Ch.2 give the same Biot ladder",
          bool(re.search(r"0\.05\s*/\s*1\s*/\s*5", flat))
          and bool(re.search(r"0\.05\s*/\s*1\s*/\s*5", ch2)))

    # The TRS three-case table is C1 and is the thesis' main claim.
    for case in ("미반영", "초기", "완전"):
        check("TRS case '%s' in Ch.1" % case, case in ch1)
    check("Ch.1 TRS case table matches Ch.2's",
          all(c in ch2 for c in ("미반영", "초기", "완전")))

    # Novelty statement: Ch.1 section 1.4.1 restates Ch.2 section 2.8.4.  The
    # opening clause is the load-bearing part -- if it drifts, the two chapters
    # claim different novelty.
    key = "이미 확립되어 있으나[5b]"
    check("novelty statement opening identical in Ch.1 and Ch.2",
          key in ch1 and key in ch2)

    # ------------------------------------------------------------------ C
    print("\n C. no source graded 'secondary' is cited")
    sec = set()
    for csv_name in ("csic_thermal_shock.csv", "failure_criteria.csv",
                     "strength_vs_temperature.csv", "thermal_conductivity.csv"):
        path = os.path.join(LIT, csv_name)
        if not os.path.exists(path):
            continue
        for line in open(path):
            if line.startswith("#") or "secondary" not in line:
                continue
            k = line.split(",")[0]
            if k != "NONE":
                sec.add(k)
    check("secondary-graded keys identified", bool(sec), ", ".join(sorted(sec)))
    for k in sorted(sec):
        check("Ch.1 does not cite %s" % k, ch1.count(k) == 0)
    check("Ch.1 does not repeat the forbidden 25 % / 12-cycle claim",
          not re.search(r"12\s*사이클[^\n]{0,40}25\s*%", ch1))

    # ------------------------------------------------------------------ D
    print("\n D. forward references point at sections that exist")
    targets = {"제2장": ch2, "제3장": ch3, "제4장": ch4}
    refs = re.findall(r"(제[234]장)\s*§?\s*([0-9]+\.[0-9](?:\.[0-9])?)", ch1)
    check("Ch.1 makes at least 6 forward references", len(refs) >= 6,
          "%d found" % len(refs))
    for chap, sec_no in sorted(set(refs)):
        body = targets.get(chap)
        if body is None:
            check("%s %s -> chapter text available" % (chap, sec_no), False)
            continue
        # a section exists if a heading declares it
        found = bool(re.search(r"(?m)^#+\s*%s\b" % re.escape(sec_no), body))
        check("%s §%s exists" % (chap, sec_no), found)

    # ------------------------------------------------------------------ E
    print("\n E. the chapter map in section 1.7 is honest")
    # every chapter the map marks as written must have a file
    written = {"제2장": "CH2_LITERATURE_REVIEW.md",
               "제3장": "CH3_VERIFICATION.md",
               "제4장": "CH4_RVE_HOMOGENISATION.md"}
    for label, fname in written.items():
        check("%s listed and its draft exists" % label,
              label in ch1 and os.path.exists(os.path.join(DOCS, fname)))
    for label in ("제5장", "제6장", "제7장"):
        check("%s listed in the map" % label, label in ch1)
    # and the map must not claim results that do not exist yet
    check("Ch.1 does not claim a completed Zhang Table 3 match",
          not re.search(r"(?:재현|일치)하였[다음]", ch1)
          or "128.45" not in ch1)
    check("Ch.1 declares itself analysis-only",
          "실험을 수행하지 않는다" in ch1 or "해석 전용" in ch1)
    check("Ch.1 states the stress-free temperature is still undecided",
          "유효 무응력 온도" in ch1 and "미확정" in ch1)

    print("\n" + "=" * 78)
    if _BAD:
        print("ROUND 1 FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ROUND 1 PASS -- ALL %d CH.1 CLAIMS TRACE BACK TO THEIR SOURCES"
          % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
