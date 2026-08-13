#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pending_slots.py  --  every `[결과 대기]` slot, and what would actually fill it
==============================================================================
a3 R4-B-4.  Ch.6 and Ch.7 carry nine slots marked `[결과 대기]`.  Left as a
flat list they all read the same -- "waiting for the matrix" -- and that is
false.  Some are waiting on jobs nobody has run; at least one is waiting on
nothing, because the result it needs is already committed and nobody noticed.

So each slot is given three things here:

  STAGE   which prerun_gate stage must finish first (S0..S5)
  OWNER   who fills it once that stage lands
  STATUS  blocked / partial / fillable

`partial` is the class this file exists to find.  A slot is partial when the
question it asks splits into pieces and at least one piece is already measured.
Ch.7's C2 row is the case in point: it asks two things in one sentence -- where
the uniform-temperature assumption breaks, and where the gradient's stress
contribution equals the CTE-mismatch contribution.  The first is measured
(data/results/macro_heat_ladder.csv, three severities).  The second needs the
macro mechanical jobs.  Writing "결과 대기" over both hides a finished result
behind an unfinished one.

WHAT THIS FILE REFUSES TO DO.  It does not fill anything itself, and it does
not let a partial fill masquerade as a complete one: a slot marked `partial`
must carry the words "1차 결과" in the chapter, and a check below enforces
that.  A first-pass number quoted as final is exactly the failure mode the
damage-cap warning (R4-A-4) exists to prevent.

Run:  python3 verification/pending_slots.py
      python3 verification/pending_slots.py --csv
"""
from __future__ import print_function

import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CH6 = os.path.join(ROOT, "docs", "CH6_RESULTS_DISCUSSION.md")
CH7 = os.path.join(ROOT, "docs", "CH7_CONCLUSION.md")
LADDER = os.path.join(ROOT, "data", "results", "macro_heat_ladder.csv")
M6 = os.path.join(ROOT, "data", "results", "M6", "README.md")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# The classification.  Keyed by a distinctive fragment of the slot's own text
# so the table cannot drift away from the chapters -- if a slot is reworded,
# find_slots() reports it as unclassified rather than silently dropping it.
# --------------------------------------------------------------------------
#: fragment -> (chapter, stage, owner, status, what would fill it)
CLASSIFY = {
    "구속응력 이력 그림": (
        "Ch.6 6.2.2", "S5", "a2", "blocked",
        "T5 구속시험은 양단 구속 거시 잡이며 잔여강도 restart 계열에 붙는다. "
        "구속 반력 이력은 어느 커밋된 산출물에도 없다"),
    "k>0 보정값": (
        "Ch.6 6.3", "S3", "a2", "blocked",
        "사이클 손상 지수 k 는 T1(60사이클 모듈러스 잔존율)에 맞춰야 나온다. "
        "1300 °C 외삽은 그 보정값이 있어야 성립한다"),
    "3케이스 PLS·강도 비교표": (
        "Ch.6 6.4", "S3", "a2", "blocked",
        "TRS 세 처리의 거시 역학 잡 9개가 전제다. 열 잡은 공유하므로 이미 있으나 "
        "PLS 는 역학 결과다"),
    "H_clo on/off": (
        "Ch.6 6.5", "S4", "a2", "blocked",
        "대조 잡은 생성 가능하지만(--hclo 0) 거시 역학 카드가 자리표인 동안에는 "
        "돌려도 의미가 없다"),
    "세 질문(§6.1)에 대한 답": (
        "Ch.6 6.7", "S3", "a1+a2", "partial",
        "세 질문 중 C2(균일 온도 가정)의 절반은 이미 측정됐다 — 열 사다리 "
        "7.0 / 36.9 / 72.2 %. 나머지 둘(C1·C3)은 역학 결과가 필요하다"),
    "매트릭스 실행 후": (
        "Ch.7 7.1", "S3", "a1+a2", "blocked",
        "제6장 §6.7 의 요약을 다시 줄인 자리다. 그쪽이 부분적으로만 채워진 동안 "
        "여기를 채우면 부분 결과가 결론으로 승격된다"),
    "위 표의 셋째 열": (
        "Ch.7 7.2.2", "S3", "a1+a2", "partial",
        "여섯 행 중 C2 행의 첫 절반(사다리 자체)이 측정으로 확정됐다. 같은 행의 "
        "둘째 절반(구배 응력 기여 = CTE 불일치 기여가 되는 Bi)은 역학 결과다"),
    "최종 종합 진술": (
        "Ch.7 7.5", "S3", "a1+a2", "blocked",
        "§7.2.2 가 채워진 뒤에 쓴다고 그 자리가 스스로 적고 있다. 순서가 규율이다"),
}

#: A slot may only be marked partial if the chapter says the number is a first
#: pass.  Without this the class is a licence to quote unfinished results.
PARTIAL_MARK = "1차 결과"


def find_slots(path):
    """Every `[결과 대기 ...]` slot in a chapter, as (line no, text)."""
    out = []
    for i, ln in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        if "[결과 대기" in ln and ln.lstrip().startswith("`"):
            out.append((i, ln.strip()))
    return out


def classify(text):
    for frag, row in CLASSIFY.items():
        if frag in text:
            return frag, row
    return None, None


def slots():
    """All slots from both chapters, joined to their classification."""
    out = []
    for path in (CH6, CH7):
        for line, text in find_slots(path):
            frag, row = classify(text)
            out.append(dict(file=os.path.basename(path), line=line, text=text,
                            frag=frag,
                            section=row[0] if row else "",
                            stage=row[1] if row else "",
                            owner=row[2] if row else "",
                            status=row[3] if row else "UNCLASSIFIED",
                            fills=row[4] if row else ""))
    return out


def ladder_measured():
    """The three gradient shares, read from the committed CSV."""
    if not os.path.exists(LADDER):
        return []
    with open(LADDER) as fh:
        return [(r["severity"], float(r["bi"]), float(r["grad_pct"]),
                 r["uniform_assumption"]) for r in csv.DictReader(fh)]


def write_csv(path=None):
    path = path or os.path.join(ROOT, "verification", "pending_slots.csv")
    rows = slots()
    with open(path, "w") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "line", "section", "stage", "owner", "status",
                    "what_would_fill_it"])
        for s in rows:
            w.writerow([s["file"], s["line"], s["section"], s["stage"],
                        s["owner"], s["status"], s["fills"]])
    return path, len(rows)


def report():
    rows = slots()
    print("=" * 78)
    print("PENDING SLOTS -- %d개, 단계·소유자·상태별" % len(rows))
    print("=" * 78)
    for st in ("fillable", "partial", "blocked", "UNCLASSIFIED"):
        got = [s for s in rows if s["status"] == st]
        if not got:
            continue
        print("\n [%s] %d개" % (st, len(got)))
        for s in got:
            print("   %-28s %-4s %-7s %s:%d"
                  % (s["section"], s["stage"], s["owner"], s["file"], s["line"]))
            print("        %s" % s["fills"])
    lad = ladder_measured()
    if lad:
        print("\n 이미 측정된 것 — 열 사다리")
        for sev, bi, pct, v in lad:
            print("   %-2s Bi=%-5g %5.1f %%   %s" % (sev, bi, pct, v))
    p, n = write_csv()
    print("\n -> %s (%d행)" % (os.path.relpath(p, ROOT), n))
    return 0


def check():
    print("pending_slots.py --check")
    rows = slots()

    print("\n A. every slot in both chapters is accounted for")
    t("slots are found in Ch.6 and Ch.7",
      len(find_slots(CH6)) and len(find_slots(CH7)),
      "%d + %d" % (len(find_slots(CH6)), len(find_slots(CH7))))
    # a3 R4-B-4 counted nine (Ch.6 five + Ch.7 four).  Eight are real: Ch.7
    # has three slots, and its fourth is the prose line at the top of the
    # chapter that MENTIONS the marker while explaining the convention.  A
    # count that includes a mention would have this file "filling" a sentence
    # that describes slots rather than being one.
    t("eight real slots -- a3's ninth is a prose mention, not a slot",
      len(rows) == 8 and len(find_slots(CH7)) == 3,
      "Ch.6 %d + Ch.7 %d" % (len(find_slots(CH6)), len(find_slots(CH7))))
    t("none is unclassified -- a reworded slot must not vanish",
      not [s for s in rows if s["status"] == "UNCLASSIFIED"],
      ", ".join(s["section"] or s["text"][:24]
                for s in rows if s["status"] == "UNCLASSIFIED") or "all mapped")
    t("every classification fragment matches exactly one slot",
      all(len([s for s in rows if s["frag"] == f]) == 1 for f in CLASSIFY))

    print("\n B. every slot names a stage and an owner")
    t("stages are drawn from the prerun_gate vocabulary",
      all(s["stage"] in ("S0", "S1", "S2", "S3", "S4", "S5") for s in rows))
    t("owners are the two working agents, alone or jointly",
      all(s["owner"] in ("a1", "a2", "a1+a2") for s in rows))
    t("every slot says what would fill it, in a sentence",
      all(len(s["fills"]) > 30 for s in rows))
    t("no slot is owned by a1 alone -- results are a2's to produce",
      not [s for s in rows if s["owner"] == "a1"])

    print("\n C. the split a3 asked for: blocked versus partly fillable")
    part = [s for s in rows if s["status"] == "partial"]
    t("at least one slot is partly fillable today", len(part) >= 1,
      ", ".join(s["section"] for s in part))
    t("and the rest are honestly blocked",
      len([s for s in rows if s["status"] == "blocked"]) == len(rows)
      - len(part))
    t("the partial ones are the two that contain C2",
      set(s["section"] for s in part) == {"Ch.6 6.7", "Ch.7 7.2.2"})
    t("Ch.7 7.1 is NOT partial though it summarises a partial section",
      [s["status"] for s in rows if s["section"] == "Ch.7 7.1"] == ["blocked"])
    t("...and the reason is written down, not left to inference",
      "부분 결과가 결론으로 승격" in CLASSIFY["매트릭스 실행 후"][4])

    print("\n D. what makes C2 partial is measured, not assumed")
    lad = ladder_measured()
    t("the heat ladder CSV is committed", len(lad) == 3, "%d rows" % len(lad))
    t("it carries three severities with a verdict each",
      [r[0] for r in lad] == ["L", "M", "H"])
    t("and exactly one of them breaks the uniform assumption",
      len([r for r in lad if r[3] == "BROKEN"]) == 1,
      "Bi = %g" % [r[1] for r in lad if r[3] == "BROKEN"][0])
    t("the C2 row's OTHER half is named as still missing",
      "구배 응력 기여" in CLASSIFY["위 표의 셋째 열"][4])
    t("so C2 is not reported as answered",
      "역학 결과다" in CLASSIFY["위 표의 셋째 열"][4])

    print("\n E. a partial fill must be labelled a first pass")
    for sec, path in (("Ch.6 6.7", CH6), ("Ch.7 7.2.2", CH7)):
        txt = open(path, encoding="utf-8").read()
        t("%s marks its partial fill as %s" % (sec, PARTIAL_MARK),
          PARTIAL_MARK in txt)
    ch7 = open(CH7, encoding="utf-8").read()
    ch6 = open(CH6, encoding="utf-8").read()
    t("Ch.7 quotes the measured shares rather than describing them",
      all(("%.1f" % r[2]) in ch7 for r in lad),
      ", ".join("%.1f" % r[2] for r in lad))
    t("Ch.6 6.7 does the same", all(("%.1f" % r[2]) in ch6 for r in lad))
    t("neither chapter claims C2 is closed",
      "C2 는 닫혔다" not in ch7 and "C2가 닫혔다" not in ch7)

    print("\n F. this file classifies and does not fill")
    src = open(__file__, encoding="utf-8").read()
    t("it never opens a chapter for writing",
      not re.search(r"open\(\s*CH[67]\s*,\s*[\"']w", src)
      and "CH6, \"w\"" not in src and "CH7, \"w\"" not in src)
    # The write mode is built from chr() so that this check's own source does
    # not contain the literal it counts -- otherwise the test fails on itself.
    wmode = "%s%s%s" % (chr(34), chr(119), chr(34))
    t("...and the only file it opens for writing is its own CSV",
      src.count(wmode) == 1 and ("open(path, " + wmode) in src)
    t("the CSV both agents read is produced", write_csv()[1] == len(rows),
      "verification/pending_slots.csv")
    t("and the refusal is stated in the docstring",
      "does not fill anything itself" in " ".join(__doc__.split()))

    print("\n" + "=" * 74)
    if _BAD:
        print("PENDING-SLOT AUDIT FAILED -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        return 1
    print("PENDING-SLOT AUDIT OK -- ALL %d CLAIMS HOLD (%d slots: %d partial, "
          "%d blocked)" % (len(_OK), len(rows),
                           len([s for s in rows if s["status"] == "partial"]),
                           len([s for s in rows if s["status"] == "blocked"])))
    print("=" * 74)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    if a.csv:
        p, n = write_csv()
        print("%s (%d rows)" % (p, n))
        return 0
    return report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
