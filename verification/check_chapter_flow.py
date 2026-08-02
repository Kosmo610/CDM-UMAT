#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_chapter_flow.py  --  ROUND 4: do Chapters 1-5 hold together as one thesis?
================================================================================
The three existing rounds each answer a narrow question.

  round 1 (check_chN_numbers.py)      is each number right against its source?
  round 2 (check_chapter_consistency) does a shared number agree everywhere?
  round 3 (check_chapter_claims)      do the named files and commands exist?

All three can pass on a set of chapters that still does not read as one thesis.
A contribution can be promised in Chapter 1 and executed nowhere.  Chapter 1 can
describe a chapter that has since changed subject.  A cross-reference can point
at a section number that was renumbered.  One chapter can report a result that
another still lists as pending.  None of that is a wrong number, a disagreeing
number, or a missing file, so nothing above sees it.

This round follows the THREADS instead -- the arguments that have to survive
from the chapter that raises them to the chapter that settles them.

  A. CONTRIBUTION THREAD.  Each of C1-C4 must be motivated in Ch.2's gap
     analysis, stated in Ch.1, and EXECUTED in a named later chapter.
  B. CHAPTER MAP.  What Ch.1 section 1.7 says a chapter contains must be what
     that chapter contains.
  C. CROSS-REFERENCES.  Every "제N장 §x.y" in any chapter must resolve to a
     heading that exists in chapter N.
  D. THE V&V LADDER.  Ch.1 assigns L1/L2/L3 to chapters; each chapter must
     claim its own level and not another's.
  E. NAMED THREADS.  The shakedown argument, the TRS argument and the Biot
     argument each have to appear at every station of their route, agreeing.
  F. PENDING VS DONE.  No chapter may present as finished a result that another
     chapter lists as outstanding.
  G. DISCLAIMERS.  Where Ch.1 and Ch.2 explicitly refuse a novelty claim, no
     later chapter may quietly make it.

Run:  python3 verification/check_chapter_flow.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

CH = {
    1: "CH1_INTRODUCTION.md",
    2: "CH2_LITERATURE_REVIEW.md",
    3: "CH3_VERIFICATION.md",
    4: "CH4_RVE_HOMOGENISATION.md",
    5: "CH5_MACRO_THERMALSHOCK.md",
}

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-60s %s" % ("PASS" if cond else "FAIL", name, detail))


def headings(text):
    """Every numbered section heading declared in a chapter."""
    return set(re.findall(r"(?m)^#+\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-z]?)\s",
                          text))


def main():
    print("=" * 80)
    print("ROUND 4 -- check_chapter_flow.py: do Ch.1-5 hold together?")
    print("=" * 80)

    t = {}
    for n, fname in CH.items():
        p = os.path.join(DOCS, fname)
        if not os.path.exists(p):
            check("%s exists" % fname, False)
            return 1
        t[n] = open(p).read()
    check("all five chapter drafts exist", True, ", ".join(sorted(CH.values())))
    heads = {n: headings(v) for n, v in t.items()}

    # ------------------------------------------------------------------ A
    print("\n A. every contribution is motivated, stated, and executed")
    # (contribution, chapter that EXECUTES it, marker proving execution)
    EXEC = {
        "C1": (5, "freeze_step"),        # the 3 TRS cases are built in Ch.5
        "C2": (5, "0.05 / 1 / 5"),       # the Biot ladder is built in Ch.5
        "C3": (5, "균열 닫힘"),           # crack closure drives the asymmetry
        "C4": (5, "D-criterion"),        # three criteria evaluated in Ch.5
    }
    for c, (where, marker) in sorted(EXEC.items()):
        check("%s motivated in Ch.2 gap analysis" % c,
              bool(re.search(r"\*\*%s\b" % c, t[2])))
        check("%s stated in Ch.1 contributions" % c,
              bool(re.search(r"\*\*%s\b" % c, t[1])))
        check("%s executed in Ch.%d" % (c, where), marker in t[where],
              "marker %r" % marker)
    # Ch.5 must say which contribution each of its mechanisms serves, or the
    # reader cannot connect the deck back to the claim.
    for c in ("C1", "C2", "C3", "C4"):
        check("Ch.5 names %s at its execution site" % c, c in t[5])

    # ------------------------------------------------------------------ B
    print("\n B. Ch.1's chapter map matches what the chapters contain")
    MAP = {
        2: ["문헌", "공백"],
        3: ["검증", "구성모델"],
        4: ["RVE", "균질화"],
        5: ["거시", "열충격"],
    }
    for n, words in sorted(MAP.items()):
        row = [ln for ln in t[1].splitlines()
               if ln.startswith("| **제%d장**" % n)]
        check("Ch.1 map has a row for 제%d장" % n, bool(row))
        if not row:
            continue
        for w in words:
            check("Ch.1 map row %d mentions '%s'" % (n, w), w in row[0])
            check("Ch.%d itself uses '%s'" % (n, w), w in t[n])
    # Chapters the map promises but which are not written yet must be listed
    # as such somewhere, not silently implied to exist.
    for n in (6, 7):
        check("Ch.1 map lists 제%d장 (not yet written)" % n,
              ("제%d장" % n) in t[1])

    # ------------------------------------------------------------------ C
    print("\n C. every cross-reference resolves to a real section")
    total = 0
    for src in sorted(t):
        refs = re.findall(r"제([1-5])장\s*§?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-z]?)",
                          t[src])
        for tgt, sec in set(refs):
            tgt = int(tgt)
            total += 1
            ok = sec in heads[tgt]
            check("Ch.%d -> 제%d장 §%s" % (src, tgt, sec), ok,
                  "" if ok else "no such heading")
        # bare "§x.y" inside a chapter refers to itself
        for sec in set(re.findall(r"(?<!제[1-5]장 )§([0-9]+\.[0-9]+(?:\.[0-9]+)?[a-z]?)",
                                  t[src])):
            if not sec.startswith(str(src) + "."):
                continue          # handled by the cross-chapter pass above
            total += 1
            check("Ch.%d -> own §%s" % (src, sec), sec in heads[src])
    check("at least 30 cross-references checked", total >= 30, "%d" % total)

    # ------------------------------------------------------------------ D
    print("\n D. the V&V ladder is assigned consistently")
    check("Ch.1 defines the L1/L2/L3 ladder",
          all(x in t[1] for x in ("L1", "L2", "L3")))
    check("Ch.3 claims L1", "L1" in t[3])
    check("Ch.3 says it covers L1 only",
          "본 장은 L1만을 다룬다" in t[3] or "L1만" in t[3])
    check("Ch.4 claims L2", "L2" in t[4])
    check("Ch.3 does not claim to have done L2 validation",
          "본 장은 L1만" in t[3] or "L2" not in t[3].split("## 3.9")[0][:2000])
    # Ch.1 and Ch.3 must agree on which chapter owns which level
    for lvl, owner in (("L1", "제3장"), ("L2", "제4장")):
        row = [ln for ln in t[3].splitlines() if lvl in ln and owner in ln]
        check("Ch.3 ladder table assigns %s to %s" % (lvl, owner), bool(row))

    # ------------------------------------------------------------------ E
    print("\n E. the named threads survive from raise to resolution")

    # E1 -- shakedown: raised in Ch.1, proved in Ch.3, solved in Ch.5
    check("Ch.1 raises the shakedown problem",
          "손상이 자라지 않는다" in t[1])
    check("Ch.3 proves it numerically (drift exactly zero)",
          "정확히 0" in t[3] or "0.00e+00" in t[3])
    check("Ch.1 quotes the same zero-drift result",
          "정확히 0" in t[1])
    check("Ch.5 solves it with the cycle-damage law",
          "d_{cyc}" in t[5] or "d_cyc" in t[5])
    check("Ch.1 and Ch.5 agree on the two alternatives A/B",
          "재분배" in t[1] and "재분배" in t[5])
    # the sign of k is the thread's payoff -- it must be claimed identically
    for doc in (1, 2, 5):
        check("Ch.%d ties the two datasets to opposite behaviour" % doc,
              ("포화" in t[doc]) and ("가속" in t[doc]))
    check("Ch.5 makes the sign of k the discriminator",
          "부호" in t[5] and "$k$" in t[5])

    # E2 -- TRS: measured (Ch.2), reproduced too large (Ch.4), 3 cases (Ch.5)
    check("Ch.2 reports the XRD measurement", "114.7" in t[2])
    check("Ch.4 reports our over-prediction", "268.08" in t[4]
          and "2.34" in t[4])
    check("Ch.1 carries both numbers", "114.7" in t[1] and "268.08" in t[1])
    check("Ch.5 builds the three TRS cases",
          all(x in t[5] for x in ("미반영", "초기", "완전")))
    check("Ch.1 and Ch.5 give the same three TRS cases",
          all(x in t[1] for x in ("미반영", "초기", "완전")))
    check("Ch.5 states B-vs-C is the quantity of interest",
          "B와 C의 차이" in t[5])
    check("Ch.1 states the same",
          "B와 C의 차이" in t[1])
    # the stress-free temperature must be the same everywhere it is used
    for n in (1, 2, 4, 5):
        check("Ch.%d uses 1050 as the stress-free temperature" % n,
              "1050" in t[n])

    # E3 -- Biot: back-calculated in Ch.4, framed in Ch.1/2, swept in Ch.5
    check("Ch.4 back-calculates the Biot numbers",
          "0.0475" in t[4] and "0.0277" in t[4])
    check("Ch.5 uses the same calibrated values",
          "0.0475" in t[5] and "0.0277" in t[5])
    check("Ch.1 quotes them", "0.0475" in t[1] and "0.0277" in t[1])
    for n in (1, 2, 5):
        check("Ch.%d states the 0.05/1/5 ladder" % n,
              bool(re.search(r"0\.05\s*/\s*1\s*/\s*5",
                             re.sub(r"(?<=\d)[  ](?=\d)", "", t[n]))))
    # and every chapter that mentions it must agree the published tests are
    # in the near-uniform regime -- the honest framing of C2
    for n in (1, 5):
        check("Ch.%d says the published tests are near-uniform" % n,
              "균일" in t[n] and ("거의 옳" in t[n] or "정당" in t[n]))

    # ------------------------------------------------------------------ F
    print("\n F. nothing is presented as done that another chapter calls pending")
    # Ch.4 says the Zhang Table 3 comparison is unfinished.  Nobody may imply
    # otherwise, and Ch.5 must gate itself on it.
    check("Ch.4 still lists the Zhang Table 3 match as unfinished",
          "미완" in t[4])
    check("Ch.5 gates its matrix on that calibration",
          "확정되기 전에는" in t[5] and "실행하지 않는다" in t[5])
    check("Ch.1 does not claim the strengths are reproduced",
          not re.search(r"128\.45[^\n]{0,60}(?:재현하였|일치하였)", t[1]))
    check("Ch.5 states none of its decks has been run",
          "아직 실행되지 않았다" in t[5])
    # the mesh-convergence caveat has to travel with every strength claim
    for n in (3, 4):
        check("Ch.%d carries the mesh-sensitivity caveat" % n,
              "메시 민감" in t[n] or "메시 수렴성" in t[n])
    check("Ch.1 carries it too", "메시 수렴성" in t[1])
    # the retracted sliver-element hypothesis must not resurface
    # Look at the whole section that mentions the count, not a fixed character
    # window: in Ch.4 the retraction sits below a seven-row table, further from
    # the number than any window worth hard-coding.
    RETRACTED = ("원인은 아니", "반증", "위생", "원인 서술에서는 빼",
                 "원인으로 보아서는 안 된다")
    for n in (3, 4):
        flatn = re.sub(r"(?<=\d)[  ](?=\d)", "", t[n])
        if "1185" not in flatn:
            check("Ch.%d: retracted mesh hypothesis absent" % n, True)
            continue
        # the section containing the count, bounded by the surrounding headings
        idx = flatn.find("1185")
        start = flatn.rfind("\n### ", 0, idx)
        start = flatn.rfind("\n## ", 0, idx) if start < 0 else start
        nxt = flatn.find("\n## ", idx)
        ctx = flatn[max(start, 0):nxt if nxt > 0 else len(flatn)]
        ok = any(w in ctx for w in RETRACTED)
        check("Ch.%d labels the element-quality finding as not the cause" % n,
              ok, "" if ok else "no retraction near the count")

    # ------------------------------------------------------------------ G
    print("\n G. refused novelty claims stay refused")
    check("Ch.1 refuses 'multiscale + repeated thermal shock' as novelty",
          "기여가 될 수 없다" in t[1])
    check("Ch.1 credits refs/[17] with having done it", "[17]" in t[1])
    check("Ch.5 does not re-claim it as new",
          not re.search(r"본 연구[^\n]{0,40}최초", t[5]))
    for n in (1, 2, 4, 5):
        check("Ch.%d avoids the word 최초 (first-ever)" % n,
              "최초" not in t[n])
    check("Ch.1 describes refs/[17]'s simplification as deferred, not ignorant",
          "미뤄둔 것" in t[1])
    # the novelty statement must be identical in Ch.1 and Ch.2
    key = "이미 확립되어 있으나[5b]"
    check("novelty statement shared verbatim by Ch.1 and Ch.2",
          key in t[1] and key in t[2])

    print("\n" + "=" * 80)
    if _BAD:
        print("ROUND 4 FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), "; ".join(_BAD[:5])))
        print("=" * 80)
        return 1
    print("ROUND 4 PASS -- THE %d THREADS ACROSS CH.1-5 ARE CONTINUOUS"
          % len(_OK))
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
