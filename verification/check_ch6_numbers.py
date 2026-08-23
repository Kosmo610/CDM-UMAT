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
    # T5 was CORRECTED on 2026-08-06: 62.5 MPa is the saw-tooth range (an
    # elastic quantity), the MEAN drifts 0 -> -14 MPa, and the old "swing
    # 76.5 MPa" mixed the two.  The chapter must carry the corrected picture
    # and must not resurrect the old one.
    check("T5: 62.5 is the range and the chapter says so",
          abs(tcd.R68["range_mpa"] - 62.5) < 1e-9 and "톱니 진폭" in txt)
    check("T5: the mean drift 0 -> -14 MPa is the first-rank verdict",
          tcd.R68["mean_start_mpa"] == 0.0
          and tcd.R68["mean_end_mpa"] == -14.0
          and "평균응력" in txt and "−14" in txt)
    check("T5: the elastic theory value 65.283 survives into the chapter",
          abs(tcd.R68["range_theory_mpa"] - 65.283) < 1e-9
          and "65.283" in txt)
    check("T5: damage strain 0.06 % quoted",
          abs(tcd.R68["damage_strain"] - 0.06) < 1e-9 and "0.06 %" in txt)
    # 76.5 may survive only inside the retraction sentence that explains it.
    lines765 = [l for l in txt.splitlines() if "76.5" in l]
    check("T5: 76.5 survives only as a recorded misreading",
          bool(lines765) and all("오독" in l for l in lines765),
          "%d line(s), all retraction" % len(lines765) if lines765 else "gone")
    check("T5: saturation Nc = 25 / D_E ~ 0.1 quoted",
          tcd.R68["Nc"] == 25 and "$N_c$" in txt and "0.1" in txt)
    check("T5: retention rows exist and are quoted",
          {d[6] for d in tcd.DATA if d[0] == "[68]"} == {86.5, 88.9}
          and "86.5" in txt and "88.9" in txt)
    check("T5: the deck facts are in the chapter (gauge-only hot zone)",
          "40 × 3 × 3" in txt and "185 mm" in txt and "120 s" in txt)
    check("T5: the timing contradiction is flagged, not resolved",
          "주기와\n  모순" in txt or "주기와 모순" in txt)
    check("T5: the correction is declared as a correction",
          "정정(2026-08-06" in txt)
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

    # ------------------------------------------------------------------ D2
    print("\n D2. the 6.2.3 settlement table is complete and honest")
    m = re.search(r"(?ms)^### 6\.2\.3 .*?(?=^## 6\.3 )", txt)
    seg = m.group(0) if m else ""
    check("6.2.3 exists", bool(seg))
    for tgt in ("T1", "T2", "T2′", "T3", "T3′", "T4", "T5", "T6",
                "PLS", "H_{clo}", "cycle-jump"):
        check("  row for %s" % tgt, tgt in seg)
    # the two known gaps must be DECLARED as gaps, with an owner
    check("exactly two rows are marked unresolved",
          seg.count("미확정 1건") == 2)
    check("  the bending-probe gap names 5.9-3 and a2",
          "굽힘 프로브 미구현" in seg and "담당 a2" in seg)
    check("  the H_clo control-job gap names the matrix hole",
          "계상되어 있지 않다" in seg)
    check("T1 is barred from reappearing in the validation table",
          "검증표에 재등장 금지" in seg)
    check("the independence caveat is stated, not hidden",
          "완전한 독립은 아니다" in seg and "같은 연구그룹" in seg)
    check("T2' shape target carries the two-regime numbers",
          "−21 %" in seg and "+3.6 %" in seg)
    check("T4 is qualitative-only with the SiC/SiC reason",
          "SiC/SiC" in seg and "정량 부적법" in seg)
    check("the tolerance anchor for T2 is [10], not [3]",
          "[3]은 산포를 싣지 않는다" in seg)

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

    # ------------------------------------------------------------------ F
    print("\n F. section 6.6.2's inequality is re-derived, not asserted")
    seg = txt.split("### 6.6.2")[1].split("## 6.7")[0] \
        if "### 6.6.2" in txt else ""
    check("section 6.6.2 exists", bool(seg))
    if seg:
        sys.path.insert(0, HERE)
        sys.path.insert(0, os.path.join(ROOT, "postprocess"))
        sys.path.insert(0, os.path.join(ROOT, "abaqus"))
        import card_pipeline_rehearsal as R      # noqa: E402
        import make_macro_thermalshock as MT     # noqa: E402

        zs = MT.graded(12, 3.0, 0.55)
        dzs = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
        dx, dy = 40.0 / 20.0, 10.0 / 6.0
        le_hi = (dx * dy * max(dzs)) ** (1.0 / 3.0)
        le_lo = (dx * dy * min(dzs)) ** (1.0 / 3.0)
        check("the macro element range is the chapter's %.3f-%.3f mm"
              % (le_lo, le_hi),
              "0.781" in seg and "1.231" in seg,
              "le %.3f - %.3f mm" % (le_lo, le_hi))

        bound = {}
        for T, fn in R.CURVES:
            eps, sig = R.read_curve(os.path.join(R.CURVE_DIR, fn))
            f = R.curve_facts(eps, sig)
            post = f["inel"] * (1.0 - f["prepeak"])
            bound[int(round(T))] = (f["g0"] * le_hi, post,
                                    (2.0 * f["g0"] * le_hi / post)
                                    if post > 0 else None)

        # RT23 carries NO post-peak evidence -- the chapter must say so and
        # must not put a bound on it.  This is the one that would be easiest
        # to sweep in with the other two.
        check("RT23 has exactly zero post-peak dissipation",
              abs(bound[23][1]) < 1e-12 and bound[23][2] is None,
              "post %.4g N/mm" % bound[23][1])
        check("...and the chapter refuses to bound RT23",
              "RT23은 예외" in seg and "어느 쪽으로도" in seg)

        # The two temperatures that DO carry evidence: A lands below the
        # declared 2, so the measured branch is SHALLOWER, not steeper.
        for T, txt_a in ((500, "0.72"), (1000, "0.25")):
            g0le, post, A = bound[T]
            check("T%d: post-peak %.3f N/mm already exceeds g0*le %.3f"
                  % (T, post, g0le), post > g0le,
                  "ratio %.1fx" % (post / g0le))
            check("T%d: therefore A <= %.3f, BELOW the declared 2"
                  % (T, A), A < 2.0)
            check("T%d: and the chapter quotes that bound" % T,
                  txt_a in seg, txt_a)

        # The sign of the conclusion.  a2-0045 proposed the opposite one and
        # the chapter carried it for one commit; this pins the correction.
        check("the chapter says residual strength is a LOWER bound",
              "**하한**" in seg and "**상한**" not in seg)
        check("...and says softening gets SHALLOWER, not steeper",
              "더 완만해지며" in seg)
        check("the closing names M8, and says M7 cannot do it",
              "M8" in seg and "M7로는 안 된다" in seg)
        check("the M8 bundle is named by file",
              "LTH_M8_0818_1231.zip" in seg)

        # a3 R23-1.  The ban above is scoped to 6.6.2's BODY, because seg
        # stops at the 6.6.2-a heading.  A subsection written on the old
        # baseline slipped through exactly there: 6.6.2-a cited "the
        # limitation in 6.6.2's body (residual strength = UPPER bound)" while
        # the body says LOWER.  a1's ruling: widen the ban to the subsection,
        # but do not ban the WORD -- 6.6.2-a has to be able to say what it
        # used to say and why that was wrong.  Ban the CLAIM: the subsection
        # may not attribute an upper bound to 6.6.2, and must attribute a
        # lower one.
        sub = txt.split("#### 6.6.2-a")[1].split("## 6.7")[0] \
            if "#### 6.6.2-a" in txt else ""
        check("subsection 6.6.2-a exists", bool(sub))
        check("6.6.2-a does not attribute an UPPER bound to 6.6.2's body",
              "잔여강도 **상한**) 하나다" not in sub,
              "the R23-1 gap")
        check("...and attributes the LOWER bound instead",
              "잔여강도 **하한**) 하나다" in sub)
        check("...while still recording that it once said the other thing",
              "「상한」이라 적었던" in sub,
              "a correction that erases its own history repeats itself")

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
