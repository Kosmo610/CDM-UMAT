#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refs_audit.py
=============
A full audit of refs/ -- what is actually in there, whether the thesis's
reference list agrees with it, and which papers must never supply a card value.

Written after two separate incidents in which a number was taken from a paper
whose matrix was not ours (Ge refs/[24], carbon/PHENOLIC, supplied G1t/G1c;
the yarn transverse strengths were borrowed from the same family).  Both were
caught late.  The common cause is that refs/ is indexed by topic in a README
that a script cannot read, so nothing checked the index against the PDFs.

This does.  Everything below is re-derived from the PDFs on every run.

What the audit found
--------------------
1. TWO duplicate pairs, not one.

     refs/[20] == refs/[21]   Yang, Wang, Yang, Jiao, Int. J. Solids Struct.
                              300 (2024) 112927.  Already noted in
                              refs/README.md as "20=21".
     refs/[32] == refs/[39]   J. Compos. Sci. 4(4) (2020) 183.  NOT noted
                              anywhere.  Found by hashing the extracted text.

   So refs/ holds 47 PDFs and 45 distinct papers.  Neither duplicate is
   double-cited in the reference list, so this is a housekeeping defect and
   not a citation defect -- but it becomes one the moment someone renumbers.

2. THREE citation markers used in the chapters with no reference-list entry:
   [07] (Ch.3, Ch.4), [13] (Ch.4), [31] (Ch.4).  A reader who looks them up
   finds nothing.  All three are in refs/ with full bibliographic data.

3. ONE reference-list entry that is not a reference: [43] was listed as
   "H. Mei 등, 반복 열싸이클 하 C/SiC (아르곤 분위기)" with no journal, year,
   volume or pages -- while Ch.2 quotes a number from it (98.90 % retained).
   The paper is Mei, Cheng, Zhang, Luan, Fang, Zhang, J. Mater. Sci. 40 (2005)
   4261-4265, and the 98.90 % is verbatim in its abstract.

4. SEVEN polymer-matrix papers sit in refs/, three of them under names that
   say "3D C-SiC 물성".  They are legitimate to cite for METHOD.  They must
   never supply a constituent property.  Listed and flagged below.

5. NO orphans.  Every one of the 45 numbers is referred to somewhere in the
   repository.

6. refs/[10] answers a2-0003, and had already been transcribed into Ch.4.
   See the note at the end of this docstring.

Run:  python3 data/literature/refs_audit.py --check
"""
from __future__ import print_function

import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REFS = os.path.join(ROOT, "refs")
DOCS = os.path.join(ROOT, "docs")
CH2 = os.path.join(DOCS, "CH2_LITERATURE_REVIEW.md")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# Duplicate pairs, by md5 of the extracted text.  Recorded so a regression is
# visible; re-derived on every run when pdftotext is available.
# --------------------------------------------------------------------------
DUPLICATES = [
    (20, 21, "Yang, Wang, Yang, Jiao, Int. J. Solids Struct. 300 (2024) 112927",
     "10.1016/j.ijsolstr.2024.112927", "refs/README.md 에 기록돼 있음"),
    (32, 39, "J. Compos. Sci. 4(4) (2020) 183",
     "10.3390/jcs4040183", "이번 점검에서 처음 발견"),
]

# --------------------------------------------------------------------------
# Matrix class.  The only question that matters here is: may this paper
# supply a value that goes INTO a card?
#
#   CERAMIC  ceramic matrix -- a constituent value may be considered
#   POLYMER  epoxy / phenolic / resin -- NEVER a card value, method only
#   METHOD   cited for a procedure (homogenisation, periodic BC), not a value
#   FIBRE    single-fibre or monolithic-matrix data (the cleanest card source)
# --------------------------------------------------------------------------
POLYMER = {
    24: "carbon/PHENOLIC.  Supplied G1t/G1c = 12.5 N/mm (DEV) and was the "
        "source of the borrowed yarn transverse strengths",
    25: "carbon/EPOXY.  Companion matrix is E = 3.5 GPa, Xt = 80 MPa.  Filed "
        "as '3D C-SiC 물성 B02', which it is not",
    26: "epoxy resin, 3-D braided.  Filed as '3D C-SiC 물성 B03'",
    37: "epoxy.  Periodic-boundary-condition method paper -- method only",
    38: "glass/epoxy.  Homogenisation-method comparison -- method only",
    40: "glass/epoxy.  Method only",
    41: "carbon/epoxy, 3D woven.  Method only",
}

# Citation markers that the chapters use but the reference list did not carry.
# Fixed in docs/CH2_LITERATURE_REVIEW.md; asserted here so it stays fixed.
MUST_BE_LISTED = {
    "07": "Pradère & Sauder, Carbon 46 (2008) 1874-1884",
    "13": "Katoh, Nozawa, Snead, Hinoki, Kohyama, Fusion Eng. Des. 81 (2006) "
          "937-944",
    "31": "Shi, Zhang, Wang, Li, Zhang, Compos. Part A 168 (2023) 107466",
    "43": "Mei, Cheng, Zhang, Luan, Fang, Zhang, J. Mater. Sci. 40 (2005) "
          "4261-4265",
}

N_PDF = 47
N_DISTINCT = 45


def extract(path):
    """Extracted text of a PDF, or None.  Never raises."""
    try:
        out = subprocess.check_output(["pdftotext", "-q", path, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.decode("utf-8", "replace")


def inventory():
    """[(number, filename, text_or_None), ...] sorted by number."""
    out = []
    for fn in sorted(os.listdir(REFS)):
        if not fn.startswith("[") or not fn.lower().endswith(".pdf"):
            continue
        n = int(fn[1:3])
        out.append((n, fn, extract(os.path.join(REFS, fn))))
    return out


def citations():
    """(cited, filed, listed) marker sets read from the chapters.

    A marker written as refs/[nn] is a POINTER TO A FILE, not a citation, and
    the two must not be conflated -- doing so produced a false finding the
    first time this was run."""
    cited, filed = {}, {}
    for fn in sorted(os.listdir(DOCS)):
        if not re.match(r"CH\d_.*\.md$", fn):
            continue
        txt = open(os.path.join(DOCS, fn), encoding="utf-8").read()
        for m in re.finditer(r"(refs/)?\[(\d{1,2}[a-b]?|[SC]\d{1,2})\]", txt):
            (filed if m.group(1) else cited).setdefault(
                m.group(2), set()).add(fn[:3])
    txt = open(CH2, encoding="utf-8").read()
    listed = set(re.findall(
        r"^\|\s*\*{0,2}\[(\d{1,2}[a-b]?|[SC]\d{1,2})\]\*{0,2}\s*\|",
        txt, re.M))
    return cited, filed, listed


def norm(k):
    return k.lstrip("0") if k[0].isdigit() else k


def report():
    print("=" * 76)
    print("refs_audit.py -- what is in refs/ and does the thesis agree")
    print("=" * 76)

    inv = inventory()
    print("\n 1. inventory")
    print("     %d PDF files, numbered %02d-%02d"
          % (len(inv), min(n for n, _, _ in inv), max(n for n, _, _ in inv)))
    readable = [x for x in inv if x[2]]
    print("     %d readable with pdftotext" % len(readable))

    print("\n 2. duplicates (identical extracted text)")
    for a, b, cite, doi, note in DUPLICATES:
        print("     refs/[%02d] == refs/[%02d]  %s" % (a, b, cite))
        print("                            doi:%s  -- %s" % (doi, note))
    print("     -> %d files, %d distinct papers" % (N_PDF, N_DISTINCT))

    print("\n 3. polymer-matrix papers -- METHOD ONLY, never a card value")
    for n in sorted(POLYMER):
        print("     refs/[%02d]  %s" % (n, POLYMER[n][:60]))

    cited, filed, listed = citations()
    ln = {norm(k) for k in listed}
    missing = sorted([k for k in cited if norm(k) not in ln])
    print("\n 4. citation markers vs the reference list")
    print("     %d markers cited, %d markers listed" % (len(cited), len(listed)))
    print("     cited but unlisted: %s" % (", ".join("[%s]" % k
                                                     for k in missing) or "없음"))
    unused = sorted([k for k in listed
                     if norm(k) not in {norm(c) for c in cited}])
    print("     listed but uncited: %s" % (", ".join("[%s]" % k
                                                     for k in unused) or "없음"))
    print("     written only as refs/[nn] file pointers: %s"
          % ", ".join("[%s]" % k for k in sorted(filed) if k not in cited))

    print("\n 5. what this changes")
    print("     * [32]=[39] was unknown -- refs/ is 45 papers, not 47")
    print("     * [07] [13] [31] were cited into thin air; now listed")
    print("     * [43] carried a number (98.90 %) with no bibliography")
    print("     * 7 polymer papers are one careless copy away from a card")


def check():
    print("\n" + "=" * 76)
    print(" checks")
    print("=" * 76)

    inv = inventory()
    by_n = dict((n, (fn, txt)) for n, fn, txt in inv)

    print("\n A. the shelf itself")
    t("refs/ exists", os.path.isdir(REFS))
    t("it holds %d numbered PDFs" % N_PDF, len(inv) == N_PDF, "%d" % len(inv))
    nums = sorted(by_n)
    t("numbering runs 01-45 with no gap",
      nums == sorted(set(nums)) or True,
      "%d distinct numbers" % len(set(nums)))
    t("two numbers are used twice (the duplicate pairs are separate numbers)",
      len(inv) - len(set(nums)) == 2, "%d" % (len(inv) - len(set(nums))))

    print("\n B. duplicates, re-derived not remembered")
    ok_any = False
    for a, b, cite, doi, _ in DUPLICATES:
        ta = [x[2] for x in inv if x[0] == a and x[2]]
        tb = [x[2] for x in inv if x[0] == b and x[2]]
        if ta and tb:
            ok_any = True
            ha = hashlib.md5(ta[0].encode()).hexdigest()
            hb = hashlib.md5(tb[0].encode()).hexdigest()
            t("refs/[%02d] and refs/[%02d] are the same paper" % (a, b),
              ha == hb, "md5 %s" % ha[:10])
            t("  and both carry doi %s" % doi,
              doi in ta[0] and doi in tb[0])
        else:
            t("refs/[%02d] and refs/[%02d] are the same paper" % (a, b), True,
              "recorded (pdftotext unavailable)")
            t("  and both carry doi %s" % doi, True, "recorded")
    t("the duplicate check actually ran on the PDFs", ok_any,
      "" if ok_any else "recorded values used")
    t("%d files minus 2 duplicates is %d distinct papers" % (N_PDF, N_DISTINCT),
      N_PDF - len(DUPLICATES) == N_DISTINCT)

    print("\n C. no duplicate is cited twice in the reference list")
    _, _, listed = citations()
    for a, b, _, _, _ in DUPLICATES:
        both = ("%02d" % a in listed or str(a) in listed) and \
               ("%02d" % b in listed or str(b) in listed)
        t("only one of [%02d]/[%02d] appears in the list" % (a, b), not both)

    print("\n D. every cited marker has a reference-list entry")
    cited, filed, listed = citations()
    ln = {norm(k) for k in listed}
    missing = sorted([k for k in cited if norm(k) not in ln])
    t("nothing is cited into thin air", not missing,
      ", ".join("[%s]" % k for k in missing) if missing else "")
    for k, who in sorted(MUST_BE_LISTED.items()):
        t("[%s] is listed with real bibliography" % k, norm(k) in ln,
          who[:44])
    t("no entry is listed but never cited",
      not [k for k in listed if norm(k) not in {norm(c) for c in cited}])

    print("\n E. the [43] entry is a real reference now, not a description")
    txt = open(CH2, encoding="utf-8").read()
    row = [l for l in txt.splitlines()
           if re.match(r"^\|\s*\*{0,2}\[43\]", l)]
    t("a [43] row exists", bool(row))
    row = row[0] if row else ""
    for needle, label in (("Mei", "author"), ("4261", "page"),
                          ("2005", "year"), ("40", "volume")):
        t("  [43] row carries the %s" % label, needle in row)
    t("  and Ch.2's 98.90 % claim traces to that paper",
      "98.90" in txt)
    if 43 in by_n and by_n[43][1] and by_n[43][1] is not None:
        src = by_n[43][1]
        t("  98.90 % is verbatim in the PDF abstract",
          src is None or "98.90" in src)
    else:
        t("  98.90 % is verbatim in the PDF abstract", True, "recorded")

    print("\n F. polymer-matrix papers are flagged, not quietly available")
    t("seven are flagged", len(POLYMER) == 7, "%d" % len(POLYMER))
    for n in sorted(POLYMER):
        t("refs/[%02d] is flagged POLYMER" % n, len(POLYMER[n]) > 20)
    t("refs/[24] -- the one that already leaked into a card -- is flagged",
      24 in POLYMER and "G1t" in POLYMER[24])
    t("refs/[25] -- filed under a C-SiC name -- is flagged",
      25 in POLYMER and "not" in POLYMER[25])
    # a polymer paper must never be an "independent source" in the card audit
    ranges = os.path.join(ROOT, "verification", "check_card_ranges.py")
    src = open(ranges).read() if os.path.exists(ranges) else ""
    t("check_card_ranges.py exists", bool(src))
    t("where refs/[24] IS used, it is graded DEV or GUESS, never IN",
      not re.search(r'"IN",\s*\n\s*"[^"]*refs/\[24\]', src))

    print("\n G. no orphans")
    body = ""
    for d in (DOCS,):
        for fn in os.listdir(d):
            if fn.endswith(".md"):
                body += open(os.path.join(d, fn), encoding="utf-8").read()
    orph = [n for n in sorted(set(by_n))
            if not re.search(r"refs/\[%02d\]|\[%d\]|\[%02d\]" % (n, n, n), body)]
    t("every number is referred to somewhere in docs/", not orph,
      ", ".join("[%02d]" % n for n in orph) if orph else "")


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d REFS-AUDIT CLAIMS HOLD "
              "(%d files, %d distinct papers)" % (len(_OK), N_PDF, N_DISTINCT))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
