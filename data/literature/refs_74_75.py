#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refs_74_75.py -- the two OA papers the open network finally let us fetch.

docs/DOWNLOAD_LIST_RECENT.md listed them as free and reachable; no session
could reach them until the network policy was opened.  Both are now in refs/,
both graded `fulltext`, and NEITHER may enter a card.  This file pins why,
re-reading the PDFs rather than trusting the assessment prose.

  [74] Li Longbiao, Ceramics-Silikaty 63(3) (2019) 330-337.
       Temperature-dependent proportional limit stress of C/SiC, by an energy
       balance approach.  This is the METHODOLOGICAL SOURCE for the way
       pls_validation.py uses PLS as a TRS indicator -- and the paper states
       the mechanism outright: PLS rises with temperature "due to the
       increasing of fiber/matrix interface shear stress and decreasing of
       the thermal residual stress".  Until now that premise stood only on
       this repository's own reasoning.

  [75] Xu et al., Exp. Mech. 63(5) (2023) 955-964, read from the Oxford ORA
       accepted manuscript (Springer returns access=No for this article, so
       the download list's "Springer PDF" was wrong).  Thermal-shock cycles
       against residual circumferential strength, with an explicit linear
       degradation law.  Trend comparison ONLY: SiC/SiC, braided tube,
       C-ring, in air.

The one finding that needed both papers, and the reason this file exists as a
gate rather than a note:

  ** PLS(T) CHANGES SIGN BETWEEN THE TWO MATERIAL SYSTEMS. **

      [74] C/SiC     973 -> 1273 K    48 -> 82 MPa     +71 %
      [75] SiC/SiC    25 -> 900 C    247 -> 170 MPa    -31 %

  C/SiC has a large fibre-matrix CTE mismatch, so heating releases the matrix
  tensile TRS and the proportional limit climbs.  SiC/SiC does not, so
  interface degradation wins instead.  A reader who imports [75] for its
  cycle curve and keeps reading down the page will find Table 1 and a PLS
  that falls -- and our validation target would acquire the wrong sign.
  That is the a3-Round-1 failure class inverted: not deleting a good
  citation, but importing a good paper's irrelevant half.  Checked here.

Run:  python3 data/literature/refs_74_75.py --check
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
    print("  [%s] %-60s %s" % ("PASS" if ok else "FAIL", label, detail))
    if not ok:
        _FAILED.append(label)


def pdf(tag):
    for name in sorted(os.listdir(REFS)):
        if name.startswith(tag) and name.lower().endswith(".pdf"):
            out = subprocess.run(["pdftotext", "-q", os.path.join(REFS, name), "-"],
                                 capture_output=True, text=True).stdout
            return re.sub(r"[ \t\n]+", " ", out)
    return ""


def doc(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as fh:
        return fh.read()


# --- the numbers, kept here so prose never re-types them ------------------

#: [74] Li 2019, 2D C/SiC, experiment + theory.  (T [K], PLS [MPa], ld/rf)
LI_PLS = [(973.0, 48.0, 2.7), (1273.0, 82.0, 6.3)]

#: [75] Xu 2023 Table 1.  (T [C], E [GPa], PLS [MPa])
XU_TABLE1 = [(25.0, 335.0, 247.0), (900.0, 327.0, 170.0)]

#: [75] Eq. (2): sigma_CTS = a + b*N  [MPa], N in cycles
XU_DEGRADATION = {"a": 597.0, "a_sd": 20.0, "b": -0.224, "b_sd": 0.026}


def li_rise():
    return LI_PLS[1][1] / LI_PLS[0][1] - 1.0


def xu_pls_change():
    return XU_TABLE1[1][2] / XU_TABLE1[0][2] - 1.0


def xu_retention(n):
    d = XU_DEGRADATION
    return (d["a"] + d["b"] * n) / d["a"]


# ==========================================================================
def section_a():
    print("\n A. both PDFs are here and readable")
    a, b = pdf("[74]"), pdf("[75]")
    t("[74] is readable", len(a) > 8000, "%d chars" % len(a))
    t("[75] is readable", len(b) > 8000, "%d chars" % len(b))
    t("[74] is the Ceramics-Silikaty PLS paper",
      "PROPORTIONAL LIMIT STRESS" in a.upper() and "10.13168/cs.2019.0028" in a)
    t("[75] is the SiC/SiC braided-tube thermal shock paper",
      "braided tubes" in b and "thermal shock" in b.lower())
    t("  and it is the ORA accepted manuscript, not the publisher PDF",
      "Oxford" in b, "Springer returns access=No for this article")


def section_b():
    print("\n B. [74] states the mechanism our PLS logic assumes")
    a = pdf("[74]")
    t("PLS increases with temperature, in the paper's own words",
      "proportional limit stress of C/SiC composite increases with temperature" in a)
    t("  and the reason is interface shear stress rising",
      "increasing of fiber/matrix interface shear stress" in a)
    t("  and thermal residual stress falling",
      "decreasing of the thermal residual stress" in a,
      "this is exactly why PLS reads TRS")
    t("the 2D C/SiC numbers are in the text",
      "48 MPa at T = 973 K" in a and "82 MPa" in a)
    t("  a %.0f %% rise over 973 -> 1273 K" % (100 * li_rise()),
      abs(li_rise() - 0.708) < 0.01)
    t("the interface debonded length rises with it",
      abs(LI_PLS[1][2] / LI_PLS[0][2] - 2.33) < 0.05,
      "ld/rf 2.7 -> 6.3")

    # provenance discipline: this is a model paper, so no card may take it
    src = open(os.path.join(HERE, "pls_validation.py"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(HERE, "pls_validation.py")) else ""
    t("pls_validation.py exists to receive the premise", bool(src))


def section_c():
    print("\n C. [75] gives a cycle law, and only a shape may be borrowed")
    b = pdf("[75]")
    d = XU_DEGRADATION
    t("the linear degradation law is in the text",
      "597.0" in b and "0.224" in b)
    t("  intercept %.1f MPa, gradient %.3f MPa/cycle" % (d["a"], d["b"]),
      d["b"] < 0 and d["a"] > 0)
    t("  so 1000 cycles retain %.1f %%" % (100 * xu_retention(1000)),
      abs(xu_retention(1000) - 0.625) < 0.005)
    t("the fracture mode turns pseudoplastic beyond 500 cycles",
      "pseudoplastic" in b and "500 cycles" in b)
    t("the outer bundles are fully oxidised by 1000 cycles",
      "completely oxidized after 1000 thermal shock cycles" in b)
    t("the test was in air",
      "in air" in b, "oxidation is part of the measured effect")


def section_d():
    print("\n D. the sign trap -- PLS(T) runs opposite in the two systems")
    t("[74] C/SiC PLS RISES with temperature",
      li_rise() > 0, "%+.0f %%" % (100 * li_rise()))
    t("[75] SiC/SiC PLS FALLS with temperature",
      xu_pls_change() < 0, "%+.0f %% (247 -> 170 MPa)" % (100 * xu_pls_change()))
    t("  so the two disagree in SIGN, not merely in size",
      li_rise() * xu_pls_change() < 0,
      "PLS(T) is a property of the material system, not of CMCs")

    b = pdf("[75]")
    t("[75]'s Table 1 really carries those numbers",
      "247" in b and "170" in b and "335" in b and "327" in b)

    a75 = doc("REFS_74_75_ASSESSMENT.md")
    t("the assessment warns against importing [75]'s PLS direction",
      "부호가 반대다" in a75 and "부호가 뒤집힌 표적" in a75)
    t("  and says why the physics differs (CTE mismatch)",
      "CTE" in a75)

    # and nothing may have quietly adopted it
    for name in ("CH2_LITERATURE_REVIEW.md", "CH6_RESULTS_DISCUSSION.md"):
        txt = doc(name)
        t("%s does not cite [75] as a PLS(T) target" % name,
          not re.search(r"\[75\][^\n]{0,120}(PLS|비례한도)[^\n]{0,40}(표적|target)", txt))


def section_e():
    print("\n E. both are indexed, graded, and fenced off from the cards")
    idx = open(os.path.join(REFS, "README.md"), encoding="utf-8").read()
    t("[74] is in the refs index", "[74]" in idx)
    t("[75] is in the refs index", "[75]" in idx)
    t("  and the index sends both to the assessment",
      "REFS_74_75_ASSESSMENT" in idx)

    a75 = doc("REFS_74_75_ASSESSMENT.md")
    t("the assessment forbids card entry for both",
      a75.count("**금지**") >= 2)
    t("  and records [75] as an accepted manuscript, not the published PDF",
      "저자수용본" in a75)
    t("  and records that Springer returns access=No",
      "access: No" in a75 and 'content="No"' in a75,
      "the download list said Springer OA; it is not")
    t("  and gives each an atmosphere row, since a2's census convention "
      "leaves no blanks",
      "공기" in a75 and "해당 없음" in a75)


def main():
    print("=" * 74)
    print(" refs [74] Li 2019 and [75] Xu 2023 -- intake assessment")
    print("=" * 74)
    section_a()
    section_b()
    section_c()
    section_d()
    section_e()
    print()
    print("=" * 74)
    if _FAILED:
        print("FAIL -- %d of %d: %s" % (len(_FAILED), _N, ", ".join(_FAILED)))
        print("=" * 74)
        return 1
    print("ALL %d INTAKE CLAIMS HOLD" % _N)
    print("=" * 74)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv or len(sys.argv) == 1:
        sys.exit(main())
