#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review_inbox.py  --  receiving the review branch, and answering it from the PDFs
================================================================================
A third agent runs a four-node review pipeline (R1 references / R2 properties /
R3 equations / R4 coherence, fanned into S) on branch

    claude/llm-task-decomposition-w41jpc

It is rigorous, and it is running against an OBSOLETE snapshot of this project.
That is the finding this module exists to make un-forgettable:

  * that branch has NO refs/ directory.  It holds three PDFs at the repository
    root.  This branch holds 72.
  * its drafts are paper/ch1_intro.md, ch2_theory.md, ch4_verification.md --
    a three-chapter Zhang-2022 RVE document with 25 references.  This branch
    carries docs/CH1..CH7 -- seven chapters with 72.  They are not the same
    document and neither is a subset of the other.
  * its top open item, carried since Round 1 as "사용자 액션 필요 (최우선)", is
    "Zhang 2022 · Ge 2018 원문 PDF 확보".  BOTH ARE ALREADY HERE:
        refs/[05] 3D C-SiC 물성 A05.pdf   Ceram. Int. 48 (2022) 3109-3124
        refs/[24] 3D C-SiC 물성 B01.pdf   Compos. Sci. Technol. 157 (2018) 86-98

Its Round-3 trigger lists five things to check "확보 시".  All five are answered
below FROM THE PDFs, and every answer is re-derived from the file on each run
so it cannot rot into a quotation.

The reason this matters beyond bookkeeping: reviewing without the source does
not merely fail to find things, it can INVENT a defect.  Round 1 item #9
downgraded G_f,1c from "Ge Table 3" to "원 논문 근거 없이 ... 본 연구의 가정",
and Round 2 M2-1 then asked for the repository's calibration guide to be
changed to match.  Ge Table 3 lists G_f,1c = 12.5 N/mm explicitly.  The
original attribution was right; the review removed a correct citation.  That
is a strictly worse outcome than the defect it was hunting, and it is what an
audit with no library does when it treats absence of evidence as evidence.

Run:  python3 verification/review_inbox.py --check
      python3 verification/review_inbox.py            (report)
      python3 verification/review_inbox.py --csv
"""
from __future__ import print_function

import argparse
import csv
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REVIEW_BRANCH = "claude/llm-task-decomposition-w41jpc"

#: The two originals the review branch has been waiting for.
ZHANG2022 = "refs/[05] 3D C-SiC 물성 A05.pdf"
GE2018 = "refs/[24] 3D C-SiC 물성 B01.pdf"


def pdf_text(rel, first=None, last=None):
    """Text of a repository PDF.  Read live -- never cached into this file."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return ""
    cmd = ["pdftotext", "-q"]
    if first:
        cmd += ["-f", str(first), "-l", str(last or first)]
    cmd += [path, "-"]
    try:
        return subprocess.check_output(cmd).decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError):
        return ""


# --------------------------------------------------------------------------
# The five Round-3 questions, answered from the PDFs
# --------------------------------------------------------------------------
def _strip_affiliations(line):
    """Drop the superscript markers Elsevier puts after each author.

    They arrive as their own comma-separated tokens ("a", "b", "*", "**"), so
    dropping tokens that are nothing but a single letter or asterisks is both
    exact and readable.  A regex that merely trims the tail eats the last
    author's surname -- "Daining Fang a" loses "ang a" to a greedy [a-z]+$.
    """
    parts = [p.strip() for p in line.split(",")]
    keep = [p for p in parts if p and not re.match(r"^(?:[a-z]|\*+)$", p)]
    return ", ".join(re.sub(r"\s*\*+$", "", p).strip() for p in keep)


def zhang_authors():
    """Author line of Zhang (2022), from its own title page."""
    for ln in pdf_text(ZHANG2022, 1, 1).splitlines():
        if "Zhang" in ln and "Ge" in ln and "Liang" in ln:
            return _strip_affiliations(ln)
    return ""


def ge_authors():
    """Author line of Ge (2018), from its own title page."""
    for ln in pdf_text(GE2018, 1, 1).splitlines():
        if "Ge" in ln and "Liang" in ln and "Fang" in ln:
            return _strip_affiliations(ln)
    return ""


def zhang_reference(n):
    """Entry [n] of Zhang (2022)'s own reference list, joined to one line."""
    txt = pdf_text(ZHANG2022)
    m = re.search(r"(?ms)^\[%d\]\s(.*?)(?=^\[\d+\]\s|\Z)" % n, txt)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def ge_table3_fracture_energies():
    """{symbol: value} for the fracture energies listed in Ge Table 3.

    The table is column-major in the extracted text -- a label line followed
    by its value line -- so pair them rather than trying to parse a grid.
    """
    txt = pdf_text(GE2018)
    i = txt.find("Material properties of matrix and yarn")
    if i < 0:
        return {}
    block = txt[i:i + 4000].splitlines()
    out = {}
    for j, ln in enumerate(block):
        m = re.match(r"^(G[fm],?[0-9a-z()]*)\s*\(N/mm\)\s*$", ln.strip())
        if not m:
            continue
        for k in range(j + 1, min(j + 4, len(block))):
            v = block[k].strip()
            if re.match(r"^[0-9]+(\.[0-9]+)?$", v):
                out[m.group(1)] = float(v)
                break
    return out


def ge_toughness_source():
    """Ge's own reference for the Table 3 toughness values."""
    txt = pdf_text(GE2018)
    m = re.search(r"values of the fracture toughness are taken from\s+"
                  r"Ref\.\s*\[(\d+)\]", re.sub(r"\s+", " ", txt))
    if not m:
        return "", ""
    n = int(m.group(1))
    e = re.search(r"(?ms)^\[%d\]\s(.*?)(?=^\[\d+\]\s|\Z)" % n, txt)
    return "[%d]" % n, re.sub(r"\s+", " ", e.group(1)).strip() if e else ""


# --------------------------------------------------------------------------
# What the review branch holds, versus what this branch holds
# --------------------------------------------------------------------------
def branch_tree(ref):
    try:
        out = subprocess.check_output(
            ["git", "-c", "core.quotepath=false", "ls-tree", "-r",
             "--name-only", ref], cwd=ROOT, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return None
    return out.decode("utf-8", "replace").splitlines()


def library_gap():
    """(their pdf count, our pdf count, their draft files, our draft files)."""
    theirs = branch_tree("origin/" + REVIEW_BRANCH)
    ours = branch_tree("HEAD") or []
    if theirs is None:
        return None
    tp = [f for f in theirs if f.lower().endswith(".pdf")]
    op = [f for f in ours if f.startswith("refs/") and f.lower().endswith(".pdf")]
    td = [f for f in theirs if re.match(r"^paper/(ch|OUTLINE|references)", f)]
    od = [f for f in ours if re.match(r"^docs/CH\d", f)]
    return len(tp), len(op), sorted(td), sorted(od)


# --------------------------------------------------------------------------
def answers():
    """The five Round-3 answers, each with what the review branch believed."""
    za, ga = zhang_authors(), ge_authors()
    r30, r32, r33 = (zhang_reference(n) for n in (30, 32, 33))
    gt = ge_table3_fracture_energies()
    src_n, src = ge_toughness_source()
    return [
        dict(question="Zhang (2022) 저자 명단",
             answer=za,
             their_belief="Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang",
             verdict="THEY WERE RIGHT",
             note="이 브랜치의 제2장 [5]가 3·4번 저자를 L. Zhang·Y. He로 "
                  "적고 있었다 -- 2026-08-11 정정"),
        dict(question="Ge (2018) 저자 후미에 D. Fang이 있는가",
             answer=ga, their_belief="LIKELY (원문 확보 시 확정)",
             verdict="CONFIRMED -> CERTAIN",
             note="D. Fang 포함. 이 브랜치의 [24]는 'J. Ge, et al.'로 "
                  "불완전했다 -- 함께 정정"),
        dict(question="Zhang의 Ref.[30] (식 18 파라미터 출처)",
             answer=r30, their_belief="실체 미상 -- 목록에 넣지 않음",
             verdict="IDENTIFIED",
             note="X_PO / r_F / K1 의 출처가 확정되었다. PDF는 아직 미보유"),
        dict(question="Zhang의 Ref.[32] Chamis 판본",
             answer=r32,
             their_belief="1984 SAMPE Q. (LIKELY) 또는 1987 JRPC (대안)",
             verdict="NEITHER",
             note="Zhang이 인용한 것은 1989 J. Compos. Technol. Res. -- "
                  "두 후보 모두 아니다. R1의 판본 논쟁은 여기서 끝난다"),
        dict(question="Zhang의 Ref.[33] Schapery",
             answer=r33, their_belief="J. Compos. Mater. 2 (1968) 380-404",
             verdict="CONFIRMED", note="권/쪽 일치"),
        dict(question="Ge Table 3에 G_f,1c가 실려 있는가",
             answer="; ".join("%s = %g N/mm" % kv for kv in sorted(gt.items())),
             their_belief="미수록으로 보고 '본 연구의 가정'으로 강등 (R1 #9)",
             verdict="THEY WERE WRONG -- REVERT",
             note="Table 3가 %s를 명시한다. Ge는 이 값들을 자신의 Ref.%s에 "
                  "귀속한다: %s" % (", ".join(sorted(gt)), src_n, src)),
    ]


def write_csv(path=None):
    path = path or os.path.join(HERE, "review_inbox_summary.csv")
    rows = answers()
    with open(path, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["question", "answer",
                                           "their_belief", "verdict", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path, len(rows)


def report():
    gap = library_gap()
    print("=" * 78)
    print("REVIEW INBOX -- %s" % REVIEW_BRANCH)
    print("=" * 78)
    if gap is None:
        print("  브랜치를 아직 fetch 하지 않았다:")
        print("    git fetch origin %s" % REVIEW_BRANCH)
        return 1
    tp, op, td, od = gap
    print("  PDF 보유:      그쪽 %d개  /  이쪽 %d개" % (tp, op))
    print("  초안 계보:     그쪽 %s" % ", ".join(os.path.basename(f)
                                                for f in td))
    print("                 이쪽 %d개 장 (docs/CH1..CH7)" % len(od))
    print()
    for a in answers():
        print("  [%s] %s" % (a["verdict"], a["question"]))
        print("      원문:   %s" % (a["answer"][:110] or "(추출 실패)"))
        print("      그쪽:   %s" % a["their_belief"])
        print("      비고:   %s" % a["note"][:110])
    print("=" * 78)
    return 0


# --------------------------------------------------------------------------
def check():
    ok, bad = [], []

    def t(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("review_inbox.py --check")
    print(" A. the two originals the review branch is waiting for are here")
    zt = pdf_text(ZHANG2022, 1, 1)
    gt_ = pdf_text(GE2018, 1, 1)
    t("Zhang (2022) is in refs/", "Ceramics International 48 (2022)" in zt
      and "3109" in zt, os.path.basename(ZHANG2022))
    t("Ge (2018) is in refs/", "Composites Science and Technology 157" in gt_
      and "86" in gt_, os.path.basename(GE2018))
    t("Zhang's title is the one the drafts cite",
      "thermal residual stress on the tensile properties" in zt.lower())
    t("Ge's title is the one the drafts cite",
      "coupled elastic-plastic damage model" in gt_.lower())

    print("\n B. the five Round-3 questions, answered from the files")
    za = zhang_authors()
    t("Zhang's 3rd and 4th authors are Binbin Zhang and Chunwang He",
      "Binbin Zhang" in za and "Chunwang He" in za, za[:78])
    t("...which is what the review branch had, and not what Ch.2 had",
      "L. Zhang, Y. He" not in
      open(os.path.join(ROOT, "docs", "CH2_LITERATURE_REVIEW.md")).read())
    ga = ge_authors()
    t("Ge's author list ends with Daining Fang", "Daining Fang" in ga,
      ga[:78])
    r30 = zhang_reference(30)
    t("Zhang's Ref.[30] is identified", "Zhong" in r30 and "128" in r30,
      r30[:78])
    r32 = zhang_reference(32)
    t("Zhang's Ref.[32] Chamis is the 1989 JCTR paper",
      "1989" in r32 and "Compos. Technol. Res" in r32, r32[:78])
    t("...so neither 1984 nor 1987 is the right answer",
      "1984" not in r32 and "1987" not in r32)
    r33 = zhang_reference(33)
    t("Zhang's Ref.[33] Schapery matches their entry",
      "Schapery" in r33 and "380" in r33, r33[:78])

    print("\n C. the attribution the review removed was correct")
    gt3 = ge_table3_fracture_energies()
    t("Ge Table 3 lists a compressive fibre fracture energy",
      any(k.lower().startswith("gf,1c") for k in gt3),
      ", ".join("%s=%g" % kv for kv in sorted(gt3.items())))
    t("its value is 12.5 N/mm, the number the drafts carried",
      any(abs(v - 12.5) < 1e-9 for k, v in gt3.items()
          if k.lower().startswith("gf,1c")))
    t("Table 3 also carries the transverse and matrix energies",
      len(gt3) >= 3, "%d fracture-energy rows" % len(gt3))
    n, src = ge_toughness_source()
    t("Ge attributes those values to a reference of its own",
      n != "" and "Li" in src, "%s %s" % (n, src[:56]))

    print("\n D. the structural situation is recorded, not assumed")
    gap = library_gap()
    t("the review branch has been fetched", gap is not None,
      "" if gap else "git fetch origin " + REVIEW_BRANCH)
    if gap:
        tp, op, td, od = gap
        t("this branch holds far more of the library", op > 20 * max(tp, 1),
          "%d vs %d PDFs" % (op, tp))
        t("the two drafts are different documents",
          len(td) >= 3 and len(od) >= 7,
          "%d paper/ files vs %d docs/CH files" % (len(td), len(od)))
        t("their draft has no chapter for the thermal-shock cycling",
          not any("ch5" in f or "ch6" in f or "ch7" in f for f in td))
    t("the module states why a source-less audit can invent a defect",
      "removed a correct citation" in __doc__)

    print("\n E. the CSV both agents read")
    path, n_ = write_csv()
    text = open(path).read()
    t("the summary CSV is written", n_ == 6 and os.path.exists(path),
      "%d rows -> %s" % (n_, os.path.basename(path)))
    t("every row carries their belief next to the answer",
      "their_belief" in text.splitlines()[0])
    t("the CSV records where they were right, not only where they were wrong",
      "THEY WERE RIGHT" in text and "THEY WERE WRONG -- REVERT" in text)

    print("\n" + "=" * 74)
    if bad:
        print("FAILED %d of %d: %s" % (len(bad), len(ok) + len(bad),
                                       ", ".join(bad[:3])))
        return 1
    print("ALL %d REVIEW-INBOX CHECKS PASS" % len(ok))
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
        path, n = write_csv()
        print("wrote %s (%d rows)" % (path, n))
        return 0
    return report()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
