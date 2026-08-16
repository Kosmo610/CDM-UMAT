#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch7_numbers.py  --  ROUND 1 for Chapter 7 (skeleton stage)
================================================================
Chapter 7 is the conclusions chapter, drafted before any result exists.  Its
failure mode is unique: a conclusions chapter quietly converts pending results
into settled findings.  So beyond the usual restatement checks, this round
polices the BOUNDARY the chapter itself declares -- section 7.2.1 may contain
only conclusions that hold without analysis results, and everything
result-dependent must live in an explicit pending slot.

  A. every number Ch.7 restates equals the value its owning chapter pins
  B. the six no-result conclusions are each actually result-free, verified
     against the artefact that establishes them
  C. result-dependent content is fenced: pending slots exist, and no
     completion language leaks into them
  D. the limitations list is complete against the sections it cites
  E. citations resolve against Chapter 2's reference table

Run:  python3 verification/check_ch7_numbers.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, os.path.join(ROOT, "data", "literature"))

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def read(name):
    p = os.path.join(DOCS, name)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def main():
    print("=" * 78)
    print("ROUND 1 -- check_ch7_numbers.py: does Ch.7 conclude only what it may?")
    print("=" * 78)

    txt = read("CH7_CONCLUSION.md")
    check("chapter file exists", bool(txt))
    if not txt:
        return 1

    # ------------------------------------------------------------------ A
    print("\n A. restated numbers match their owning chapters")
    import thermal_cycling_dataset as tcd
    ch3 = read("CH3_VERIFICATION.md")
    m = re.search(r"\*\*합계\*\*[^|]*\|[^|]*\|\s*\*\*(\d+)\*\*", ch3)
    total = m.group(1) if m else "?"
    check("verification grand total matches Ch.3", ("%s개" % total) in txt,
          total)
    y = [d for d in tcd.DATA if d[0] == "[02]"][0]
    z = [d for d in tcd.DATA if d[0] == "[03]"
         and d[7] == "tensile strength"][0]
    ry = (100 - y[6]) / y[5] / (y[3] - y[2])
    rz = (100 - z[6]) / z[5] / (z[3] - z[2])
    check("the 6.0x severity ratio re-derives", abs(rz / ry - 6.05) < 0.1
          and "6.0배" in txt, "%.2fx" % (rz / ry))
    check("argon 98.90 % is the dataset's value",
          any(d[4] == "argon" and d[6] == 98.90 for d in tcd.DATA)
          and "98.90 %" in txt)
    check("XRD 114.7 / ratio 2.34 quoted as owned by Ch.4",
          "114.7" in txt and "2.34배" in txt)
    check("kappa exposure numbers match 4.9-17",
          "0.0702 mm" in txt and "10.6 %" in txt and "1.92" in txt)
    check("cycle-jump tolerances match 5.5.2-a",
          "0.10 대 0.01" in txt and "10배" in txt)
    check("band-width range matches 6.6.1",
          "1.20–5.25 mm" in txt and "0.68–0.94 mm" in txt)
    check("threshold bracket matches Ch.1/Ch.2",
          "900–1200 °C" in txt and "1000 °C" in txt)

    # ------------------------------------------------------------------ B
    print("\n B. the six 'no-result' conclusions are actually result-free")
    sec = re.search(r"(?ms)^### 7\.2\.1 .*?(?=^### 7\.2\.2 )", txt)
    s = sec.group(0) if sec else ""
    check("7.2.1 exists with exactly six numbered conclusions",
          len(re.findall(r"(?m)^\d\. \*\*", s)) == 6)
    check("  1: drift-zero is a unit-test fact, not an analysis result",
          "정확히 0" in s and "단위시험" in s)
    check("  2: severity paradox rests on literature only",
          "문헌 데이터만으로" in s)
    check("  3: TRS reversibility cites the two in-situ papers",
          "[71]" in s and "[72]" in s)
    check("  4: the 2.34x is a completed cooldown measurement",
          "2.34배" in s)
    check("  5: the L1/L2 separation claim carries no counter snapshot",
          "원인" in s and "전수 통과" in s
          and not re.search(r"\d{3,}\s*항목", s))
    check("  6: band width is declared macro-only via 6.6.1",
          "6.6.1" in s)
    check("no pending slot inside 7.2.1", "[결과 대기" not in s)

    # ------------------------------------------------------------------ C
    print("\n C. result-dependent content is fenced")
    slots = re.findall(r"\[결과 대기[^\]]*\]", txt)
    check("at least 3 pending slots", len(slots) >= 3, "%d" % len(slots))
    check("7.2.2 is a table of PLACES, and each row has a criterion",
          "자리와 판정 기준만 확정" in txt)
    sec22 = re.search(r"(?ms)^### 7\.2\.2 .*?(?=^## 7\.3 )", txt)
    s22 = sec22.group(0) if sec22 else ""
    check("  its six rows cover C1-C4, k-sign and T5",
          all(k in s22 for k in ("C1", "C2", "C3", "C4", "$k$", "T5")))
    check("  and it carries the either-way clause from 1.3.1",
          "어느 쪽이든 결론 성립" in s22)
    check("7.5 defers the final statement instead of faking one",
          "최종 종합 진술은" in txt and "공동 작성" in txt)
    # Completion verbs are forbidden only in the RESULT-DEPENDENT zones
    # (7.2.2, 7.5, and every pending slot).  In 7.2.1 they are legitimate
    # when they report finished artefacts (the drift-zero unit test), so a
    # blanket ban would flag truthful sentences -- it did, on first run.
    zones = s22 + (re.search(r"(?ms)^## 7\.5 .*", txt) or
                   re.match(r"^$", "")).group(0)
    zones += " ".join(slots)
    check("no completion verbs inside result-dependent zones",
          not re.search(r"(재현|일치|확인)하였다", zones))

    # ------------------------------------------------------------------ D
    print("\n D. the limitations list is honest and complete")
    lim = re.search(r"(?ms)^## 7\.3 .*?(?=^## 7\.4 )", txt)
    L = lim.group(0) if lim else ""
    # 2026-08-11: 11 -> 12.  The crack band regularises the DAMAGE
    # dissipation only; the matrix plastic work is dissipated in the same
    # band and stays proportional to l_e, so the TOTAL is mesh-dependent
    # even when the band is perfect.  Measured by
    # verification/plastic_dissipation_audit.py.
    check("thirteen numbered limitations", len(
        re.findall(r"(?m)^\d+\. ", L)) == 13)
    for needle, why in (
            ("분위기 변수가 없다", "one-atmosphere model"),
            ("미측정", "the 900-1200 hole"),
            ("잔류변형률을 표현하지 않는다", "interface sliding"),
            ("상수 계수 하나", "H_clo simplicity vs [60]/[54]"),
            ("결정론적", "no scatter"),
            ("고정 간격", "cycle jump"),
            ("켤 수 없다", "kappa vs coarse mesh"),
            ("예측이 아니다", "band width"),
            ("빌려온", "borrowed matrix card"),
            ("PIP인데", "process mismatch"),
            ("독립성이 완전하지 않다", "target independence"),
            ("공개되어 있지 않다", "transverse compression: absent, not unfound"),
            ("소성 소산은 놓아준다", "plastic work is outside the crack band")):
        check("  covers: %s" % why, needle in L)
    check("the two unresolved 6.2.3 rows surface here too",
          "굽힘" in L)
    # R10-2 (a3 recommends, a1 rules): "not published" is a stronger claim
    # than "not found", so the chapter must carry BOTH legs it stands on --
    # the three dated literature sweeps and the zero damage volume -- or the
    # wording degrades back to an unsupported absolute.
    check("limitation 13 names the three sweeps",
          "2026-08-03" in L and "08-11" in L and "08-15" in L)
    check("limitation 13 names the second, independent leg",
          "손상 부피가 0" in L and "4.9-0c" in L)
    check("limitation 13 does not promote the slot out of GUESS",
          "GUESS" in L and "재판정" in L)
    # The plastic-share numbers must be the audit's, not typed ones.
    sys.path.insert(0, HERE)
    import plastic_dissipation_audit as pda
    _ge = pda.g_elastic(pda.XT_M, pda.E_M)
    _gp = pda.g_plastic(pda.XT_M, pda.SY0, pda.HISO)[0]
    for le, want in ((pda.LE_RVE_MEAN, "16.1"), (pda.LE_RVE_MAX, "42.3")):
        share = 100.0 * (_gp * le) / ((pda.GMT - _ge * le) + _gp * le)
        check("  plastic share at le=%.4f mm is re-derived, not typed" % le,
              abs(share - float(want)) < 0.05 and want + " %" in L,
              "%.1f %% (text says %s %%)" % (share, want))

    # ------------------------------------------------------------------ E
    print("\n E. citations resolve against Ch.2's table")
    ch2 = read("CH2_LITERATURE_REVIEW.md")
    listed = {k.lstrip("0") for k in re.findall(
        r"^\|\s*[~*]{0,4}\[(\d{1,2}[a-b]?|[SC]\d{1,2})\][~*]{0,4}\s*\|",
        ch2, re.M)}
    cited = {m.group(2) for m in
             re.finditer(r"(refs/)?\[(\d{1,2}[a-b]?)\]", txt)
             if not m.group(1)}
    orphans = sorted(k for k in cited if k.lstrip("0") not in listed)
    check("no Ch.7 citation is missing from Ch.2's table", not orphans,
          ", ".join("[%s]" % k for k in orphans))
    check("the chapter declares it introduces no new sources",
          "새 문헌을 도입하지 않으며" in txt)

    print("\n" + "=" * 78)
    if _BAD:
        print("ROUND 1 (CH.7) FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ROUND 1 (CH.7) PASS -- ALL %d CLAIMS HOLD" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
