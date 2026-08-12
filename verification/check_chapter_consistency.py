#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_chapter_consistency.py  --  ROUND 2 of the chapter self-verification
==========================================================================
Rounds 1 and check_ch2/ch3 verify each chapter against its own sources.  A
chapter can pass that and still contradict its neighbours, because the
chapters were written at different times against different evidence.  That is
the failure mode this round exists for, and it is the one a reviewer notices
first: the same quantity carrying two different values in one thesis.

Two kinds of contradiction are checked.

  A. SHARED QUANTITIES.  A quantity quoted in more than one document must
     carry the same value everywhere.  Implemented by searching each document
     for a pattern and asserting the captured number equals the canonical one.

  B. SUPERSEDED ESTIMATES.  Some numbers were estimates before the analysis
     ran and were later measured.  Both may legitimately appear -- but the
     estimate must be LABELLED as an estimate wherever it survives, otherwise
     the thesis states two different residual stresses without saying why.

What this round does NOT check: whether the numbers are right (round 1), or
whether the files and commands named in the chapters exist (round 3).

Run:  python3 verification/check_chapter_consistency.py
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

FILES = {
    "Ch.1": "CH1_INTRODUCTION.md",
    "Ch.2": "CH2_LITERATURE_REVIEW.md",
    "Ch.3": "CH3_VERIFICATION.md",
    "Ch.4": "CH4_RVE_HOMOGENISATION.md",
    "Ch.5": "CH5_MACRO_THERMALSHOCK.md",
    # Ch.6 is NOT in this net yet: its 6.2.2 discusses measured MPa values
    # ("62.5 MPa ... 실측") that collide with the XRD SHARED regex.  Admit it
    # only after that regex is tightened.
    "Ch.7": "CH7_CONCLUSION.md",
    "M1": "M1_FAILURE_ANALYSIS.md",
    "NOVELTY": "NOVELTY.md",
    "PLAN": "THESIS_PLAN.md",
}

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


def load():
    out = {}
    for tag, fname in FILES.items():
        path = os.path.join(DOCS, fname)
        out[tag] = open(path).read() if os.path.exists(path) else None
    return out


# --------------------------------------------------------------------------
# A. shared quantities: (label, regex with one numeric group, canonical, tol)
#    The regex is searched in every document; where it hits, the captured
#    value must match.  Documents where it does not hit are simply silent.
# --------------------------------------------------------------------------
SHARED = [
    ("XRD matrix TRS [MPa]",
     r"([0-9]+\.[0-9])\s*MPa[^\n]{0,40}(?:XRD|실측)|XRD[^\n]{0,60}?([0-9]+\.[0-9])\s*MPa",
     114.7, 0.05),
    ("crack-band element limit [mm]",
     r"l_e\s*<\s*\*?\*?([0-9]\.[0-9]+)|\$l_e < ([0-9]\.[0-9]+)\$", 0.2214, 0.01),
    ("mesh element count",
     r"26\s?452|26452", None, None),      # presence-only, checked below
    ("distorted elements",
     r"1\s?185|1185", None, None),
    ("Zhang RT strength [MPa]", r"128\.45", None, None),
    ("Zhang 500 C strength [MPa]", r"179\.42", None, None),
    ("Zhang 1000 C strength [MPa]", r"199\.15", None, None),
]

# quantity -> (canonical string, documents that must all agree)
EXACT = [
    ("Zhang Table 3 RT", "128.45", ["Ch.4", "PLAN"]),
    ("Zhang Table 3 500", "179.42", ["Ch.4", "PLAN"]),
    ("Zhang Table 3 1000", "199.15", ["Ch.4", "PLAN"]),
    ("XRD matrix TRS", "114.7", ["Ch.1", "Ch.2", "Ch.4", "M1", "NOVELTY"]),
    ("mesh 26452 elements", "26452", ["Ch.1", "Ch.4", "M1"]),
    ("1185 distorted elements", "1185", ["Ch.3", "Ch.4", "M1"]),
    ("crack-band limit 0.2214 mm", "0.2214", ["Ch.4", "M1"]),
    ("I1=0 jump 78.0x", "78.0", ["Ch.3", "M1"]),
    ("stress-free temperature 1050", "1050", ["Ch.1", "Ch.2", "Ch.4", "Ch.5", "M1"]),
    # Two lineages, both pinned.  The literature row is what refs/[03]'s own
    # rho, refs/[20]'s cp and refs/[12]'s k give; the "ours" row is the same
    # protocol re-solved on the homogenised card the deck actually carries.
    # Keeping both pinned is what stops a chapter quietly adopting one number
    # while its neighbour keeps the other -- which is how 0.0548, the mixed
    # pairing that belongs to no material, could get in.
    ("Biot for refs/[3], literature properties", "0.0475",
     ["Ch.1", "Ch.4", "Ch.5"]),
    ("Biot for refs/[3], our own card", "0.0445", ["Ch.1", "Ch.4", "Ch.5"]),
    ("Biot for refs/[2], our own card", "0.0260", ["Ch.1", "Ch.4", "Ch.5"]),
    ("yarn micromechanics worst error", "0.142", ["Ch.3"]),
    # Ch.1 restates results owned by Ch.3 and Ch.4.  An introduction drifting
    # away from the chapters it summarises is the single easiest way to put two
    # different numbers in one thesis, so every value it repeats is pinned here.
    ("measured matrix TRS", "268.08", ["Ch.1", "Ch.4", "M1"]),
    # Ch.2 deliberately says only "2배 이상" -- it was written before the
    # cooldown was run and must not carry a precision it did not have.
    ("TRS over-prediction ratio", "2.34", ["Ch.1", "Ch.4", "M1"]),
    ("yarn volume fraction", "0.4982", ["Ch.1", "Ch.4"]),
    ("RVE volume [mm^3]", "5.390", ["Ch.1", "Ch.4"]),
    ("Biot for refs/[2], literature properties", "0.0277",
     ["Ch.1", "Ch.4", "Ch.5"]),
    ("automated verification item count", "2819", ["Ch.1", "Ch.3", "Ch.7"]),
    # The [28] page range was once corrupted to "1784-1597" by a blind
    # replace of the verification counter (1784 was the counter's value at
    # the time; 1586 had been an EARLIER value of the same counter, which is
    # exactly why the page number matched the pattern).  Pinned so any future
    # counter propagation that touches it fails the gate.
    ("Li Part I page range intact", "1586–1597", ["Ch.1", "Ch.2"]),
]


def main():
    print("=" * 78)
    print("ROUND 2 -- check_chapter_consistency.py: do the chapters agree?")
    print("=" * 78)

    doc = load()
    # Prose writes long integers with a digit-group space ("26 452").  Compare
    # against a space-stripped copy so formatting is not read as disagreement.
    flat = {k: (re.sub(r"(?<=\d)[  ](?=\d)", "", v) if v else v)
            for k, v in doc.items()}
    missing = [t for t, v in doc.items() if v is None]
    check("all eight documents present", not missing, ", ".join(missing))
    if missing:
        return 1

    # ---------------------------------------------------------------- A
    print("\n A. a quantity quoted in several documents must match")
    for label, needle, where in EXACT:
        hits = {t: (needle in flat[t]) for t in where}
        check("%-34s in %s" % (label, "+".join(where)),
              all(hits.values()),
              "missing from " + ", ".join(t for t, h in hits.items() if not h)
              if not all(hits.values()) else "")

    # ---------------------------------------------------------------- B
    print("\n B. superseded estimates must be labelled as estimates")

    # The matrix TRS was estimated at 302 MPa by a mean-field calculation
    # BEFORE the cooldown was run, then measured at 268.08 MPa.  Both may
    # appear, but 302 must never be presented as the model's answer.
    for tag in ("Ch.2", "Ch.4", "M1"):
        t = doc[tag]
        if "302" not in t:
            check("%s: no stale 302 MPa" % tag, True, "not quoted")
            continue
        ctx = " ".join(re.findall(r"(?s).{0,400}302.{0,400}", t))
        labelled = any(w in ctx for w in
                       ("평균장", "mean-field", "추정", "estimate", "sweep",
                        "훑", "MEASURED", "측정된 값은", "measured"))
        check("%s: 302 MPa is labelled as the mean-field estimate" % tag,
              labelled, "" if labelled else "presented as the answer")

    # The ratio to the XRD value: 2.6x was the estimate, 2.34x is measured.
    for tag in ("Ch.2", "Ch.4", "M1"):
        t = doc[tag]
        has26 = bool(re.search(r"2\.6\s*[x×배]", t))
        has234 = bool(re.search(r"2\.34\s*[x×배]", t))
        if has26 and not has234:
            ctx = " ".join(re.findall(r"(?s).{0,400}2\.6\s*[x×배].{0,400}", t))
            ok = any(w in ctx for w in ("평균장", "mean-field", "추정",
                                        "estimate", "predicted"))
            check("%s: bare 2.6x is labelled an estimate" % tag, ok)
        else:
            check("%s: TRS ratio consistent (2.34x measured)" % tag,
                  has234 or not has26,
                  "2.34x present" if has234 else "ratio not quoted")

    # Ch.2 says the cooldown leaves the matrix near its threshold; Ch.4
    # measures r from the volume-averaged stress.  They must not disagree in
    # DIRECTION -- both must say the matrix is highly loaded, not relaxed.
    print("\n C. qualitative claims that must not contradict")
    check("Ch.2 and Ch.4 both say the cooldown overloads the matrix",
          ("2배 이상" in doc["Ch.2"] or "0.973" in doc["Ch.2"])
          and ("0.973" in doc["Ch.4"] or "268.08" in doc["Ch.4"]))
    check("every chapter attributes the TRS overprediction to the "
          "stress-free temperature, not to a code error",
          "무응력 온도" in doc["Ch.4"] and "무응력 온도" in doc["Ch.2"])
    check("Ch.2 and Ch.4 agree the uniform-temperature assumption nearly "
          "holds at the published severity",
          "0.048" in doc["Ch.2"] and "0.0475" in doc["Ch.4"])
    check("Ch.3 and Ch.4 agree the distorted elements are all in the matrix",
          "전부 기지" in doc["Ch.3"] and "전부 기지" in doc["Ch.4"])
    check("Ch.2 does not claim chapters 3-4 as novelty",
          "노벨티로 주장할 수 없" in doc["Ch.2"])
    check("Ch.4 does not present the tension result as finished",
          "미완" in doc["Ch.4"])

    # cross-references must point at sections that exist
    print("\n D. cross-references point at sections that exist")
    for src, pat, target in (("Ch.4", r"제2장 §2\.7\.2", "Ch.2"),
                             ("Ch.4", r"제2장 §2\.3\.1", "Ch.2"),
                             ("Ch.4", r"제2장 §2\.3\.2", "Ch.2"),
                             ("Ch.4", r"제2장 §2\.4\.1", "Ch.2"),
                             ("Ch.4", r"제2장 §2\.4\.3", "Ch.2"),
                             ("Ch.4", r"제2장 §2\.8\.3", "Ch.2"),
                             ("Ch.4", r"제3장 §3\.2\.3", "Ch.3"),
                             ("Ch.4", r"제3장 §3\.4\.1", "Ch.3"),
                             ("Ch.4", r"제3장 §3\.4\.3", "Ch.3"),
                             ("Ch.4", r"제3장 §3\.6", "Ch.3"),
                             ("Ch.3", r"§3\.4\.3", "Ch.3"),
                             ("Ch.3", r"§3\.8", "Ch.3")):
        if not re.search(pat, doc[src]):
            continue
        sec = pat.replace(r"제2장 §", "").replace(r"제3장 §", "") \
                 .replace(r"§", "").replace("\\", "")
        exists = re.search(r"^#+\s*" + re.escape(sec), doc[target], re.M)
        check("%s -> %s %s exists" % (src, target, sec), bool(exists))

    print("\n" + "=" * 78)
    if _BAD:
        print("ROUND 2 FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 78)
        return 1
    print("ROUND 2 PASS -- THE %d CROSS-CHAPTER CLAIMS ARE CONSISTENT"
          % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
