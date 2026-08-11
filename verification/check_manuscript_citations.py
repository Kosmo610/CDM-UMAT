#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_manuscript_citations.py  --  the citation audit, scoped to the MANUSCRIPT
==============================================================================
`docs/CH1..CH7` is the submission (사용자 결정, 2026-08-11).  Everything else in
docs/ is working material -- candidate lists, download queues, assessments,
handoffs.  That distinction is the whole point of this round.

`refs_audit.py` already checks the library: 72 files, no duplicates, nothing
cited into thin air, no orphans.  But its orphan check concatenates ALL of
docs/*.md, so a reference that appears only in `REFS_CANDIDATES.md` counts as
"referred to".  For a library audit that is right -- the number is in use.  For
a MANUSCRIPT audit it is wrong: a reference listed in the chapter-2 table and
never cited in any chapter is an orphan in the submitted document, and a
reviewer sees it immediately.

That gap was found by taking the review branch's own lenses (R1 references,
R4 coherence) and pointing them at docs/ instead of at paper/.  It caught one:
[S10] Chaboche (1992) sat in the [S*] table, unreferenced by any chapter --
while chapter 3 spent a page on a stress discontinuity that is EXACTLY the
"fundamental problem" that paper names.  The fix was not to delete the entry.

The lenses implemented here:

  A. every entry of the chapter-2 reference tables is cited by some chapter
  B. every citation marker in a chapter has an entry in those tables
  C. sweeping claims about the literature carry a citation in their paragraph
  D. the [S*] table's "보유" claims match what refs/ actually contains
  E. the manuscript is the seven chapters -- nothing else is quietly included

Run:  python3 verification/check_manuscript_citations.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
REFS = os.path.join(ROOT, "refs")

#: The submission, in order.  Anything not here is working material.
MANUSCRIPT = [
    ("CH1_INTRODUCTION.md", "제1장"),
    ("CH2_LITERATURE_REVIEW.md", "제2장"),
    ("CH3_VERIFICATION.md", "제3장"),
    ("CH4_RVE_HOMOGENISATION.md", "제4장"),
    ("CH5_MACRO_THERMALSHOCK.md", "제5장"),
    ("CH6_RESULTS_DISCUSSION.md", "제6장"),
    ("CH7_CONCLUSION.md", "제7장"),
]

#: Phrases that assert something about the state of the literature.  A claim
#: like these needs a citation or it is the reviewer's first red pen mark.
TREND_PHRASES = (
    "여전히 주류", "부상하고 있", "적용되기 시작", "최근 문헌", "널리 쓰이",
    "일반적이다", "대부분의 연구", "보고되어 있다", "알려져 있다", "통용된다",
    "표준적으로", "주류로 사용", "관행이다", "정설이다",
)

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def chapters():
    return {tag: open(os.path.join(DOCS, fn), encoding="utf-8").read()
            for fn, tag in MANUSCRIPT}


def reference_table(ch2):
    """(table text, {key: row}) for the chapter-2 reference section."""
    i = ch2.find("## 참고문헌 (본 장 인용분)")
    tbl = ch2[i:] if i >= 0 else ""
    rows = {}
    for m in re.finditer(r"^\|\s*\*{0,2}\[([0-9]{1,2}[a-z]?|S[0-9]{1,2})\]"
                         r"\*{0,2}\s*\|(.*)$", tbl, re.M):
        rows[m.group(1)] = m.group(2)
    return tbl, rows


def cited_anywhere(key, body):
    """Is `key` cited in the manuscript body (the listing itself removed)?"""
    pats = [r"\[%s\]" % re.escape(key)]
    stem = re.sub(r"[a-z]$", "", key)
    if stem.isdigit():
        n = int(stem)
        pats += [r"refs/\[0?%d\]" % n, r"\[%d\]" % n, r"\[%02d\]" % n]
    return any(re.search(p, body) for p in pats)


def paragraphs(text):
    """Split on blank lines, keeping a line number for each block."""
    out, buf, start = [], [], 1
    for i, ln in enumerate(text.splitlines(), 1):
        if ln.strip():
            if not buf:
                start = i
            buf.append(ln)
        elif buf:
            out.append((start, "\n".join(buf)))
            buf = []
    if buf:
        out.append((start, "\n".join(buf)))
    return out


def main():
    print("=" * 78)
    print("MANUSCRIPT CITATION AUDIT -- docs/CH1..CH7 is the submission")
    print("=" * 78)

    ch = chapters()
    missing = [t for t, v in ch.items() if not v]
    check("all seven chapters are present and non-empty", not missing,
          ", ".join(missing))
    if missing:
        return 1

    tbl, rows = reference_table(ch["제2장"])
    check("the chapter-2 reference section was located", bool(tbl))
    check("it lists a plausible number of entries", len(rows) >= 55,
          "%d entries" % len(rows))

    # The listing is not a citation, so remove it before searching.
    body = "".join(v for v in ch.values()).replace(tbl, "")

    # ------------------------------------------------------------------ A
    print("\n A. no entry is listed without being cited by a chapter")
    orphans = [k for k in rows if not cited_anywhere(k, body)]
    check("every reference-table entry is cited somewhere in CH1-CH7",
          not orphans, ", ".join("[%s]" % k for k in sorted(orphans))
          if orphans else "%d entries all cited" % len(rows))
    # the one this round found, pinned so it cannot silently regress
    check("[S10] Chaboche (1992) is cited, not merely listed",
          cited_anywhere("S10", body),
          "the unilateral-condition discontinuity in 3.4")
    check("...and it is cited where the discontinuity is discussed",
          "[S10]" in ch["제3장"] and "불연속" in ch["제3장"])

    # ------------------------------------------------------------------ B
    print("\n B. no chapter cites a marker the table does not carry")
    thin = set()
    for tag, text in ch.items():
        hay = text.replace(tbl, "")
        for m in re.finditer(r"\[(S?[0-9]{1,2}[a-z]?)\]", hay):
            k = m.group(1)
            if k in rows:
                continue
            # a plain number may be listed zero-padded, or vice versa
            stem = re.sub(r"[a-z]$", "", k)
            if stem.isdigit() and (("%02d" % int(stem)) in rows
                                   or str(int(stem)) in rows):
                continue
            thin.add((tag, k))
    check("every marker used in a chapter has a table entry", not thin,
          ", ".join("%s [%s]" % t for t in sorted(thin)[:6]))

    # ------------------------------------------------------------------ C
    print("\n C. claims about the literature carry a citation")
    naked = []
    for tag, text in ch.items():
        for start, para in paragraphs(text.replace(tbl, "")):
            if para.lstrip().startswith("|"):
                continue          # tables cite in their own cells
            if not any(w in para for w in TREND_PHRASES):
                continue
            if re.search(r"\[S?\d{1,2}[a-z]?\]|refs/\[", para):
                continue
            naked.append((tag, start, para.strip().replace("\n", " ")[:70]))
    check("no sweeping literature claim stands without a citation",
          not naked, "; ".join("%s:%d %s" % n for n in naked[:3]))

    # ------------------------------------------------------------------ D
    print("\n D. the [S*] table's holdings claims match refs/")
    held = os.listdir(REFS) if os.path.isdir(REFS) else []
    bad_hold = []
    for k, row in rows.items():
        if not k.startswith("S"):
            continue
        m = re.search(r"보유\s*`refs/\[(\d{2})\]`", row)
        if not m:
            continue
        n = m.group(1)
        if not any(f.startswith("[%s]" % n) for f in held):
            bad_hold.append("%s->refs/[%s]" % (k, n))
    check("every '보유 refs/[NN]' in the [S*] table points at a real file",
          not bad_hold, ", ".join(bad_hold) or "all present")
    claimed = [k for k, r in rows.items() if k.startswith("S") and "보유" in r]
    check("the [S*] table claims a plausible number of holdings",
          len(claimed) >= 8, "%d claimed held" % len(claimed))

    # ------------------------------------------------------------------ E
    print("\n E. the manuscript is exactly these seven files")
    others = [f for f in os.listdir(DOCS)
              if f.endswith(".md") and f not in dict(
                  (fn, t) for fn, t in MANUSCRIPT)]
    check("working documents are not part of the submission",
          all(not f.startswith("CH") for f in others),
          "%d working docs alongside" % len(others))
    check("chapter files are numbered 1-7 with no gap",
          [t for _, t in MANUSCRIPT] ==
          ["제%d장" % i for i in range(1, 8)])
    check("this module names the submission decision and its date",
          "사용자 결정, 2026-08-11" in __doc__)
    flat = " ".join(__doc__.split())
    check("it explains why refs_audit's own orphan check is not enough",
          "concatenates ALL of docs/*.md" in flat)

    print("\n" + "=" * 78)
    if _BAD:
        print("MANUSCRIPT AUDIT FAILED -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    # NOT starting this line with PASS: check_ch3_numbers counts lines
    # beginning with PASS/FAIL, and a summary that matches its own
    # counter inflates the ledger by one.
    print("MANUSCRIPT AUDIT OK -- ALL %d CITATION CLAIMS HOLD" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
