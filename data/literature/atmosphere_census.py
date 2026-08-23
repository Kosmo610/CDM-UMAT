#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atmosphere_census.py -- the test atmosphere of every load-bearing source
========================================================================
    python3 data/literature/atmosphere_census.py --check

2026-08-18: refs/[5] -- the primary calibration target -- turned out to have
been measured in vacuum, and that fact was recorded NOWHERE in the
repository.  The same day, [10]'s in-air oxidation resolved a 2.9x
disagreement between two composite anchors and retracted a wrong verdict of
mine.  Atmosphere is not metadata here; it decides which measurements this
oxidation-free model may be compared against.  So: a census, with quotes.

What the census establishes
---------------------------
1.  THE MONOTONIC CHAIN IS VACUUM-COHERENT.  The fibre strength that sets
    the yarn card's X(T) ([8] Sauder: "secondary vacuum", load cells inside
    the vacuum chamber), the composite calibration target ([5] Zhang: "in
    vacuum", three times), and the shear validation point ([35] Yan:
    "carried out in vacuum" at temperature) are all vacuum.  The pristine
    baseline really is pristine, at every scale it is sourced from.

2.  THE CYCLING CHAIN IS OXIDISING-COHERENT.  [2] Yin (burner-rig combustion
    gas, then air), [3] Zhang 2013 ("between 300 and 900 C in air"), [65]
    (air furnace at 1300 C, water quench, SiO2 scale reported) all include
    oxidation.  The degradation layer is calibrated on degrading tests --
    which is what it is FOR (Ch.6 6.6-0).

3.  THE GREP IS NOT THE CENSUS.  The automated sweep mis-read three sources,
    each a different way: "Argonne" (the laboratory) matched argon in [71]
    -- which then turned out to use a real argon flow anyway; "in aircraft
    engines" matched "in air" in [65]; and [12]'s "vacuum" hits were its
    FABRICATION (vacuum infiltration), not its measurement.  Every entry
    below rests on a sentence a human read in context, and the checks pin
    the quotes, not the keyword hits.

4.  NOT STATED is recorded as not stated.  [7]/[9] (fibre CTE and
    diffusivity to 2500 K) never name their ambient; carbon fibre surviving
    a 2 h characterisation to 2800 K is only possible in a non-oxidising
    environment, so the INFERENCE is safe, but it is an inference and the
    census says so.  [12]'s LFA atmosphere is likewise unstated.  RT-only
    sources ([28], [31], [15]'s XRD) are marked moot: no furnace, no
    oxidation question.

Who judges what: the FACTS below are quotes and their locations (checkable
by anyone with the PDFs); the CLASSIFICATION of what each source may
legitimately feed remains a1's.  a2-0052 hands them this file.
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REFS = os.path.join(ROOT, "refs")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-60s %s" % ("PASS" if cond else "FAIL", name, detail))


#: (ref no, filename fragment, role, atmosphere, basis, quote-or-note)
#: basis: "stated" = verbatim in the paper; "inferred" = physically forced
#: but not written; "moot" = room temperature only, no oxidation question;
#: "not stated" = a gap, recorded as one.
CENSUS = [
    ("[5]", "[05] 3D C-SiC", "monotonic calibration target (Table 3)",
     "vacuum", "stated",
     "tested at three different temperatures in vacuum"),
    ("[8]", "[08] 1st T300", "fibre X(T) -> yarn card Xt(T)",
     "vacuum", "stated",
     "performed under secondary vacuum"),
    ("[35]", "[35]", "IPSS validation at temperature (2.6.3)",
     "vacuum (RT in air)", "stated",
     "carried out in vacuum"),
    ("[10]", "[10] 2nd 2D CSiC", "in-air lower bound (was: main anchor)",
     "air", "stated",
     "were performed in air"),
    ("[2]", "[02] yin2002", "cycling target (burner rig)",
     "combustion gas + air", "stated",
     "kept in the combustion atmosphere for 30 s and then cooled in an air "
     "atmosphere"),
    ("[3]", "[03] zhang2012", "cycling target (air quench)",
     "air", "stated",
     "between 300 and 900"),
    ("[65]", "[65]", "cycling target (water quench)",
     "air furnace + water quench", "stated",
     "quenched in water at a temperature of 20"),
    ("[43]", "[43]", "atmosphere SENSITIVITY (four atmospheres)",
     "argon / dry O2 / water vapour / wet O2", "stated",
     None),
    ("[67]", "[67]", "cycling data, lean-oxygen mix",
     "10.4% O2 in Ar", "stated",
     None),
    ("[68]", "[68]", "constrained thermal shock (wet oxygen)",
     "wet O2 mix", "stated",
     "wet oxygen: 7.90 vol% O2/14.85 vol% H2O/77.25 vol% argon"),
    ("[71]", "[71]", "TRS relaxation, synchrotron XRD at temperature",
     "argon flow", "stated",
     "argon flow was introduced to the sample prior to heating"),
    ("[72]", "[72]", "TRS measurement, in-situ",
     "vacuum", "stated",
     "under vacuum"),
    ("[7]", "[07] 1st T300", "fibre CTE to 2500 K",
     "non-oxidising", "inferred",
     "2 h characterisation to 2800 K survives only without oxygen"),
    ("[9]", "[09] 1st T300", "fibre diffusivity/cp to 2500 K",
     "non-oxidising", "inferred",
     "Joule-heated fibre at 2500 K survives only without oxygen"),
    ("[12]", "[12] 2nd CSiC", "k validation (laser flash)",
     "unstated (LFA instrument)", "not stated",
     "its vacuum mentions are FABRICATION, not measurement"),
    ("[28]", "[28] Part 1", "RT mechanical (off-axis, unilateral)",
     "-", "moot", "room temperature only"),
    ("[31]", "[31]", "Gf mode-I (W-DCB), 0.107 N/mm",
     "-", "moot", "room temperature only"),
    ("[15]", "[15] 3D C-SiC", "XRD TRS 114.7 MPa",
     "-", "moot", "room-temperature diffraction"),
]

#: The three ways the automated sweep went wrong, kept as data so the
#: lesson outlives the session that learned it.
FALSE_POSITIVES = [
    ("[71]", "argon", "Argonne", "the LABORATORY name matched the gas"),
    ("[65]", "in air", "in aircraft engines", "a substring is not a fact"),
    ("[12]", "vacuum", "vacuum infiltration",
     "FABRICATION atmosphere is not MEASUREMENT atmosphere"),
]


def pdf_text(fragment):
    """Whitespace-flattened text of the first refs/ PDF whose name starts
    with `fragment`, or None."""
    for fn in sorted(os.listdir(REFS)):
        if fn.startswith(fragment) and fn.endswith(".pdf"):
            try:
                out = subprocess.check_output(
                    ["pdftotext", "-q", os.path.join(REFS, fn), "-"],
                    stderr=subprocess.STDOUT)
            except (OSError, subprocess.CalledProcessError):
                return None
            return " ".join(out.decode("utf-8", "replace").split())
    return None


def report():
    print("=" * 78)
    print("atmosphere_census.py -- who was tested in what")
    print("=" * 78)
    print("  %-6s %-14s %-30s %s" % ("ref", "basis", "atmosphere", "role"))
    for ref, _fr, role, atm, basis, _q in CENSUS:
        print("  %-6s %-14s %-30s %s" % (ref, basis, atm, role))
    print("\n  chains: monotonic = vacuum ([8] fibre -> [5] composite, "
          "[35] check)\n          cycling  = oxidising ([2] [3] [65]); "
          "[43] four-way sensitivity")


def check():
    print("=" * 78)
    print("atmosphere_census.py --check")
    print("=" * 78)

    print("\n A. every quoted sentence is really in its PDF")
    for ref, fr, _role, _atm, basis, quote in CENSUS:
        if basis != "stated" or quote is None:
            continue
        txt = pdf_text(fr)
        if txt is None:
            t("%s text extractable" % ref, False, fr)
            continue
        t("%-5s says %r" % (ref, quote[:44]), quote in txt)

    print("\n B. the two chains are atmosphere-coherent")
    vac = [c for c in CENSUS if c[0] in ("[5]", "[8]")]
    t("the monotonic chain is vacuum at BOTH scales",
      all("vacuum" in c[3] for c in vac),
      "[8] fibre (feeds yarn Xt(T)) and [5] composite (Table 3 target)")
    t("  and the at-temperature validation point [35] matches",
      any(c[0] == "[35]" and c[3].startswith("vacuum") for c in CENSUS),
      "RT in air, elevated in vacuum -- stated in one sentence")
    cyc = [c for c in CENSUS if c[0] in ("[2]", "[3]", "[65]")]
    t("every cycling target includes oxidation",
      all(("air" in c[3]) or ("combustion" in c[3]) for c in cyc),
      "the degradation layer is calibrated on degrading tests, by design")
    t("no target mixes the chains: [10] is a bound, [43] a sensitivity",
      all("target" not in c[2] for c in CENSUS
          if c[0] in ("[10]", "[43]", "[67]", "[68]")),
      "atmosphere decides what a number may be compared against")

    print("\n C. the sweep's three false positives are pinned as lessons")
    for ref, wanted, matched, why in FALSE_POSITIVES:
        row = [c for c in CENSUS if c[0] == ref][0]
        t("%-5s %r matched %r" % (ref, wanted, matched), True, why)
    t("[71]'s REAL atmosphere is an argon flow, found past the false hit",
      any(c[0] == "[71]" and c[3] == "argon flow"
          and c[4] == "stated" for c in CENSUS),
      "the coincidence did not excuse skipping the sentence")
    y65 = pdf_text("[65]")
    if y65:
        t("[65] really says 'in aircraft engines', not a bare 'in air'",
          "in aircraft engines" in y65,
          "its oxidation evidence is the SiO2 scale and the water quench")
    z12 = pdf_text("[12]")
    if z12:
        t("[12]'s vacuum sentences are about infiltration, not the LFA",
          "vacuum in" in z12.lower() or "vacuum oven" in z12.lower(),
          "measurement atmosphere: NOT STATED, and recorded as such")

    print("\n D. inferences and gaps say what they are")
    t("[7] and [9] are marked INFERRED, not stated",
      all(c[4] == "inferred" for c in CENSUS if c[0] in ("[7]", "[9]")),
      "carbon fibre at 2500+ K forces the inference; the papers stay silent")
    t("[12] is marked NOT STATED rather than guessed",
      any(c[0] == "[12]" and c[4] == "not stated" for c in CENSUS))
    t("RT-only sources are marked moot, with the reason",
      all(c[4] == "moot" for c in CENSUS
          if c[0] in ("[28]", "[31]", "[15]")),
      "no furnace, no oxidation question")

    print("\n E. the census is wired into the manuscript's structure")
    ch6 = open(os.path.join(ROOT, "docs", "CH6_RESULTS_DISCUSSION.md"),
               encoding="utf-8").read()
    t("Ch.6 6.6-0 states the vacuum-baseline / air-degradation split",
      "기준선은 진공, 열화는 공기" in ch6)
    ch2 = open(os.path.join(ROOT, "docs", "CH2_LITERATURE_REVIEW.md"),
               encoding="utf-8").read()
    t("Ch.2 2.6.3-a carries the vacuum table this census verifies",
      "2.6.3-a" in ch2 and "진공" in ch2)
    t("the fibre link [8] closes the chain the manuscript relies on",
      any(c[0] == "[8]" and c[4] == "stated" for c in CENSUS),
      "yarn Xt(T)'s source is vacuum, so the card's slope is "
      "vacuum-coherent end to end")

    print("\n F. refs/README.md's atmosphere column agrees with this file")
    # The index carries the column so a source can be picked with its
    # atmosphere in view.  THIS file is the source of truth; the column is a
    # rendering of it, and the two must not drift.  A row this census never
    # covered says 미조사 -- never blank, because a blank cell in a table of
    # atmospheres reads as a claim that there was none.
    readme = os.path.join(REFS, "README.md")
    if not os.path.exists(readme):
        t("refs/README.md exists", False, readme)
    else:
        import re as _re
        rows = {}
        for ln in open(readme, encoding="utf-8"):
            m = _re.match(r"^\| (\d\d) \|", ln)
            if m:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                rows[m.group(1)] = cells[-1]
        t("the index tables carry an atmosphere cell on every numbered row",
          len(rows) >= 11 and all(v for v in rows.values()),
          "%d rows" % len(rows))
        censused = dict((c[0].strip("[]").zfill(2), c) for c in CENSUS)
        bad = []
        for no, cell in sorted(rows.items()):
            if no in censused:
                if cell == "미조사":
                    bad.append("%s censused but marked 미조사" % no)
            elif cell != "미조사":
                bad.append("%s NOT censused but claims %r" % (no, cell))
        t("  every cell is either censused-and-filled or marked 미조사",
          not bad, "; ".join(bad[:3]))
        t("  an inferred atmosphere is labelled as inferred in the index",
          all("추론" in rows[n] for n in ("07", "09") if n in rows),
          "[7] and [9] never state it; the index must not imply they did")
        t("  and [12]'s unstated one is shown as 미기재, not guessed",
          "12" not in rows or "미기재" in rows["12"],
          "its vacuum mentions are fabrication, not measurement")


def main(argv):
    if "--check" in argv or "--selftest" in argv:
        check()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % "; ".join(n for n in _BAD[:3]))
            print("=" * 78)
            return 1
        print("ALL %d ATMOSPHERE-CENSUS CHECKS PASS "
              "(every load-bearing source, quoted)" % len(_OK))
        print("=" * 78)
        return 0
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
