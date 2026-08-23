#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atmosphere_verdicts.py -- a1's CLASSIFICATION verdicts on top of a2's census.

a2 built data/literature/atmosphere_census.py: it pins, from the PDFs, WHICH
ATMOSPHERE each load-bearing source was measured in.  Those are facts and this
file does not re-litigate them.  a2 then handed three classification questions
to a1 (a2-0052) and asked a1 to confirm one arbitration (a2-0050/0051):

    confirm  a2-0050  the "+39 % non-conservative" withdrawal
    confirm  a2-0051  demoting [10] from "primary anchor" to "in-air floor"
    (a)      a2-0052  does [12]'s unstated LFA atmosphere change its grade?
    (b)      a2-0052  is [67]'s lean oxidation (10.4 % O2) a cycle TARGET
                      or a SENSITIVITY case?

Per CLAUDE.md the split is: a2 owns how a value is USED (solver, deck, card
arithmetic); a1 owns a value's PROVENANCE, its TRUST GRADE, whether a card may
legally take it, and the citation.  All four questions above are a1's.

The verdicts, and the one place a2 over-reached:

  A. CONFIRMED -- the withdrawal.  a2's three quotations are verbatim; this
     file re-reads them from the PDFs rather than trusting the transcription.

  B. CORRECTED -- "in air, about 2/3 of the high-temperature gain disappears".
     The DIRECTION is right and stays.  The ATTRIBUTION does not: the 36.2 %p
     gap between [5]'s +55.0 % and [10]'s +18.8 % is not an atmosphere
     measurement.  Two independent readings of the same PDFs say so:

       - the ROOM-TEMPERATURE control.  [5] measures 128.45 MPa at 23 C,
         [10] measures 225.8 MPa at 300 K.  A factor of 1.76 -- at the one
         temperature where oxidation cannot act at all.  Whatever separates
         these two materials was already there before the furnace was lit.

       - [10]'s OWN oxidation-free model.  Its Table 2 predicts the strength
         from pristine constituents, with no oxidation term (the paper says
         so explicitly when its 1473 K point misses).  That prediction rises
         21.8 % over 300 -> 1273 K against the 18.8 % measured.  So removing
         oxidation from [10] buys 3.0 %p of the 36.2 %p gap -- 8 %.  The other
         92 % is not atmosphere.

     What IS different: same architecture (both 2D plain weave, Vf ~ 40 %,
     both stated in the originals), different matrix route -- [5] is PIP at
     1050 C, [10] is CVI with an I-CVI SiC overcoat at rho ~ 2.0 g/cm3.

     This is the R18-1 failure class ("a direction does not exist without a
     baseline") in its quantitative form: the direction was sound, the
     denominator was borrowed from a different material.

  C. CONFIRMED -- [10] is the in-air floor, not the primary anchor.  a2's
     demotion stands, and B does not weaken it.  B only forbids reading the
     GAP as the price of air; the ordering (in-air <= in-vacuum) survives
     both readings because oxidation has one sign.

  D. (a) [12]: grade UNCHANGED at fulltext.  The grade records how WE got the
     number -- full text, digitised figure, abstract, secondary -- not whether
     the measurement suits our model.  Downgrading for an unstated test
     condition would make one tag mean two things, and then `fulltext` would
     no longer tell a reader whether a value was transcribed or eyeballed.
     Applicability belongs in the census and in a scope note, which is where
     a2 correctly put it.

     But [12] has a LARGER unstated thing than its atmosphere, and this audit
     found it while checking a2's: the paper never states the TEMPERATURE of
     the 6.29 W/(m.K) either.  conductivity_bounds.py compares it against
     room-temperature matrix values (Zhang [17] 25.0, Pradere [09] @296 K), so
     the repository is already reading it as room temperature -- as an
     assumption nobody wrote down.  For k-bar that is the bigger exposure:
     C/SiC conductivity roughly halves from RT to 1273 K, so a mis-set anchor
     temperature moves the porosity solve, not a decimal.  Recorded here as an
     assumption so it stops being invisible.

     Also checked, because the paper's whole point is RAISING conductivity:
     6.29 is the BASELINE C/SiC, not the CNT-enhanced 19.25.  The repository
     took the right one.

  E. (b) [67]: SENSITIVITY, not target -- and the deciding reason is not the
     oxygen.  [67] is a 3D four-step BRAIDED preform at a ~20 deg braid angle.
     Our model is 2D plain weave.  Architecture disqualifies it as a primary
     cycle target before atmosphere is even reached, so the 10.4 % O2 question
     never becomes load-bearing.  It stays a direction-and-magnitude witness
     for the cycle law, alongside [43] Mei's four-atmosphere series.

Run:  python3 data/literature/atmosphere_verdicts.py --check
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REFS = os.path.join(ROOT, "refs")
DOCS = os.path.join(ROOT, "docs")

_FAILED = []
_N = 0


def t(label, ok, detail=""):
    global _N
    _N += 1
    print("  [%s] %-62s %s" % ("PASS" if ok else "FAIL", label, detail))
    if not ok:
        _FAILED.append(label)


def pdf(tag):
    """Full text of the refs/ PDF whose filename starts with the tag."""
    for name in sorted(os.listdir(REFS)):
        if name.startswith(tag) and name.lower().endswith(".pdf"):
            out = subprocess.run(["pdftotext", "-q", os.path.join(REFS, name), "-"],
                                 capture_output=True, text=True).stdout
            return re.sub(r"[ \t\n]+", " ", out)
    return ""


def chapter(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as fh:
        return fh.read()


# ==========================================================================
# The measured numbers.  Re-derived here, never re-typed into prose.
# ==========================================================================

#: refs/[05] Zhang Table 3, tensile strength [MPa] at 23 / 500 / 1000 C, vacuum
ZHANG_T3 = {23: 128.45, 500: 179.42, 1000: 199.15}

#: refs/[10] Yang Table 1, tensile strength [MPa] at 300/973/1273/1473 K, in air
YANG_T1_STRENGTH = {300: 225.8, 973: 240.5, 1273: 268.2, 1473: 240.9}

#: refs/[10] Yang Table 2, the paper's OWN prediction from pristine
#: constituents -- Eq. (33), no oxidation term.  Same four temperatures.
YANG_T2_PREDICTED = {300: 241.5, 973: 272.3, 1273: 294.1, 1473: 320.3}


def rise(d, lo, hi):
    """Fractional rise of d from key lo to key hi."""
    return d[hi] / d[lo] - 1.0


def gap_decomposition():
    """Return (zhang_rise, yang_rise, yang_pristine_rise, gap, oxidation_share)."""
    z = rise(ZHANG_T3, 23, 1000)
    y = rise(YANG_T1_STRENGTH, 300, 1273)
    yp = rise(YANG_T2_PREDICTED, 300, 1273)
    gap = z - y
    return z, y, yp, gap, yp - y


# ==========================================================================
def section_a():
    print("\n A. a2-0050's quotations, re-read from the PDFs (not trusted)")
    z = pdf("[05]")
    y = pdf("[10]")
    t("[05] is readable", len(z) > 5000, "%d chars" % len(z))
    t("[10] is readable", len(y) > 5000, "%d chars" % len(y))

    t("[05] says its tensile tests were in vacuum",
      "in vacuum" in z,
      '"tested at three different temperatures in vacuum"')
    t("[10] says its tensile tests were in air",
      re.search(r"tensile experiments were performed in air", y) is not None,
      '"The uniaxial tensile experiments were performed in air"')
    t("[10] reports specimen oxidation, worsening with temperature",
      "obviously oxidized" in y and "oxidation recession is worse" in y)
    t("[10] reports internal erosion at 1273 K, our own top point",
      "internal erosion" in y and "1273 K" in y)

    # a2 flagged a worry against itself: "slight" might mean a1 should read
    # the oxidation down.  Read the sentence and the worry inverts -- "slight"
    # qualifies the INTERNAL erosion, and the same sentence excepts the
    # near-surface oxidation, which the previous sentence calls "obvious".
    t("  'slight' qualifies INTERNAL erosion, not the surface oxidation",
      re.search(r"Slight internal erosion[^.]*except for the near-surface oxidation",
                y) is not None,
      "a2's self-doubt reads the wrong way round; the surface is 'obviously oxidized'")


def section_b():
    print("\n B. the 2/3 statement -- direction holds, attribution does not")
    z, y, yp, gap, oxid = gap_decomposition()

    t("[5] rises 55.0 % over 23 -> 1000 C", abs(z - 0.550) < 0.005,
      "%.1f %%" % (100 * z))
    t("[10] rises 18.8 % over 300 -> 1273 K", abs(y - 0.188) < 0.005,
      "%.1f %%" % (100 * y))
    t("  so the gap is 36.2 %p", abs(gap - 0.362) < 0.005,
      "%.1f %%p" % (100 * gap))

    # --- reading 1: the room-temperature control -------------------------
    ratio = YANG_T1_STRENGTH[300] / ZHANG_T3[23]
    t("at ROOM temperature the two anchors already differ 1.76x",
      abs(ratio - 1.757) < 0.01,
      "%.1f vs %.2f MPa = %.2fx" % (YANG_T1_STRENGTH[300], ZHANG_T3[23], ratio))
    t("  and oxidation cannot act at room temperature",
      True, "so that factor is material, not atmosphere -- it precedes the furnace")

    # --- reading 2: [10]'s own oxidation-free model ----------------------
    t("[10]'s Table 2 predicts from pristine constituents, no oxidation term",
      abs(yp - 0.218) < 0.005, "%.1f %% predicted vs %.1f %% measured"
      % (100 * yp, 100 * y))
    ytxt = pdf("[10]")
    t("  and the paper says so where its 1473 K point misses",
      "oxidation damage" in ytxt and "has not been taken into account" in ytxt)
    t("removing oxidation from [10] recovers only 3.0 of the 36.2 %p",
      abs(oxid - 0.030) < 0.005,
      "%.1f %%p = %.0f %% of the gap" % (100 * oxid, 100 * oxid / gap))
    t("  so >= 90 %% of the gap is NOT atmosphere",
      (gap - oxid) / gap > 0.90,
      "%.0f %%" % (100 * (gap - oxid) / gap))

    # --- what the difference actually is ---------------------------------
    ztxt = pdf("[05]")
    t("both originals state 2D plain weave", "plain-weave" in ztxt.lower()
      and "plain-weave" in ytxt.lower())
    t("both originals state Vf ~ 40 %",
      "volume fraction was nearly 40" in ztxt and "volume fraction is about 40" in ytxt,
      "same architecture -- the control is tight")
    t("[5] is PIP at 1050 C", "PIP process" in ztxt and "1050" in ztxt)
    t("[10] is CVI with an I-CVI overcoat", "CVI technique" in ytxt
      and "I-CVI" in ytxt, "different matrix route -- that is the variable")


def section_c():
    print("\n C. the chapters state the corrected attribution")
    ch2 = chapter("CH2_LITERATURE_REVIEW.md")
    ch6 = chapter("CH6_RESULTS_DISCUSSION.md")

    for nm, txt in (("Ch.2", ch2), ("Ch.6", ch6)):
        t("%s no longer says the 2/3 is what air costs" % nm,
          not re.search(r"대기 중에서는\s*(고온 강도 이득의\s*)?약?\s*2/3\s*가?\s*사라진다", txt),
          "the bare form is the over-attribution")

    t("Ch.2 2.6.3-a carries the room-temperature control",
      "128.45" in ch2 and "225.8" in ch2 and "1.76" in ch2,
      "the one fact that settles it")
    t("Ch.2 2.6.3-a carries [10]'s own pristine prediction",
      "21.8" in ch2, "3.0 of 36.2 %p")
    t("Ch.2 names the real variable (PIP vs CVI)",
      "PIP" in ch2 and "CVI" in ch2)
    t("Ch.6 6.6 states the ordering, not the size",
      "하한" in ch6 and "산화는" in ch6)
    t("  and Ch.6 no longer sells the gap as quantitative evidence",
      "최초의 정량 근거" not in ch6)

    # The demotion itself is CONFIRMED, so it must survive.
    t("[10] is still the in-air floor, in Ch.2 and in the index",
      "대기 중 성능의 하한" in ch2)


def section_d():
    print("\n D. (a) [12] -- grade unchanged, two things unstated")
    z12 = pdf("[12]")
    t("[12] is readable", len(z12) > 5000, "%d chars" % len(z12))
    t("[12]'s LFA atmosphere is not stated",
      "LFA 427" in z12 and not re.search(
          r"LFA 427[^.]{0,200}\b(in air|argon|nitrogen|vacuum|helium)\b", z12),
      "a2-0052 (iii) confirmed")
    t("  nor is the temperature of the 6.29 value",
      not re.search(r"6\.29 W/m[^.]{0,80}(room temperature|at \d+ ?(K|°C))", z12),
      "the LARGER exposure -- k halves from RT to 1273 K")

    t("6.29 is the BASELINE C/SiC, not the CNT-enhanced 19.25",
      "thermal conductivity of C/SiC composites measured as 6.29" in z12,
      "the repository took the right sample")
    t("  and 19.25 is the paper's enhanced figure, not ours",
      "19.25" in z12)

    src = open(os.path.join(ROOT, "data", "properties",
                            "conductivity_bounds.py"), encoding="utf-8").read()
    t("conductivity_bounds.py records the room-temperature reading as an assumption",
      "KBAR3_TARGET_TEMPERATURE_ASSUMED" in src
      and "does not state the temperature" in src,
      "so it stops being invisible")
    t("  and says plainly that it is an assumption, not a measurement",
      "assumption, " in src and "not a measurement" in src)
    t("  while the trust grade is explicitly NOT changed",
      "does NOT change [12]'s trust grade" in src,
      "the grade records how we got a number, not whether it suits us")

    census = open(os.path.join(HERE, "atmosphere_census.py"), encoding="utf-8").read()
    t("the census still marks [12] not stated rather than guessing",
      "not stated" in census, "a1 does not overturn that")


def section_e():
    print("\n E. (b) [67] -- sensitivity, and architecture decides it")
    z67 = pdf("[67]")
    t("[67] is readable", len(z67) > 3000, "%d chars" % len(z67))
    t("[67] is a 3D four-step BRAIDED preform",
      "braided" in z67 and "four step" in z67.lower())
    t("  at a ~20 deg braid angle", "braiding angle" in z67)
    t("our model is 2D plain weave, so architecture disqualifies it as a target",
      True, "the 10.4 % O2 question never becomes load-bearing")
    t("[67]'s oxygen fraction is on the record anyway",
      re.search(r"10.4\s*%\s*O2|O2\s*.\s*89.6\s*%\s*Ar", z67) is not None
      or "oxygen–argon mixture" in z67 or "oxygen-argon mixture" in z67,
      "lean oxidising, not inert -- it is not a vacuum control either")


def main():
    print("=" * 76)
    print(" a1 CLASSIFICATION VERDICTS on a2's atmosphere census")
    print(" (a2-0050 / a2-0051 confirmations + a2-0052 (a),(b))")
    print("=" * 76)
    section_a()
    section_b()
    section_c()
    section_d()
    section_e()
    print()
    print("=" * 76)
    if _FAILED:
        print("FAIL -- %d of %d: %s" % (len(_FAILED), _N, ", ".join(_FAILED)))
        print("=" * 76)
        return 1
    print("ALL %d a1 VERDICT CLAIMS HOLD" % _N)
    print("=" * 76)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv or len(sys.argv) == 1:
        sys.exit(main())
