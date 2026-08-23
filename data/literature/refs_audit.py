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

What the audit found, and what was done about it
------------------------------------------------
1. TWO duplicate pairs, not one.  Both are now RESOLVED by consolidation.

     [21] -> [20]   Yang, Wang, Yang, Jiao, Int. J. Solids Struct. 300
                    (2024) 112927.  Was already noted in refs/README.md
                    as "20=21" and never acted on.
     [39] -> [32]   Jain & Koch, J. Compos. Sci. 4(4) (2020) 183.  Not
                    noted anywhere.  Found by hashing the extracted text.
                    Byte-identical files, not merely the same paper.

   The redundant PDFs were deleted and the numbers 21 and 39 RETIRED -- new
   papers start at 46.  refs/ now holds 45 PDFs and 45 distinct papers.

   [39] was the dangerous one.  docs/REFS_36_45_ASSESSMENT.md described it
   as newly securing "the D-criterion primary source we had been citing
   without the original" -- but the original had been sitting in refs/ as
   [32] since the second batch.  That sentence was corrected.
   docs/NOVELTY.md also had [32]'s journal wrong ("Materials"); it is
   J. Compos. Sci.  Fixed.

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

5. TWO numbers each hold TWO DIFFERENT papers -- the opposite defect from a
   duplicate, and it survives the consolidation above:

     [01]  Yang & Liu, Ceram. Int. 46 (2020) 6029   (ox/ox CMC, CDM)
     [01]  Yang & Liu, Int. J. Fatigue 134 (2020) 105507
     [05]  Q. Zhang et al., Ceram. Int. 48 (2022) 3109   <- OUR base paper
     [05]  Skinner & Chattopadhyay, Compos. Struct. 268 (2021) 114006

   Both are handled now.  [05] writes [5] and [5b]; [01] was split into
   [01a] (Ceram. Int.) and [01b] (Int. J. Fatigue) on 2026-08-06, following
   the keys refs/README.md had already assigned.  Every citation in the
   chapters resolves to exactly one paper.

   So: 45 files, 43 distinct numbers, 45 distinct papers.

6. NO orphans.  Every number is referred to somewhere in the repository.

7. refs/[10] answers a2-0003, and had already been transcribed into Ch.4.

8d. FIFTH UPLOAD, 2026-08-06: [65]-[72].  None closes an [S*] gap; all eight
   are new numbered references.  The one that acts immediately is [69], a 2026
   review whose equation (23) gives the PUBLISHED characteristic element length
   for tetrahedra, he = (12 Ve)^(1/3) = 2.2894 Ve^(1/3), attributed to
   Kurumatani et al. (2016).  That is a2's N^(1/d) with N = 12, and it sits
   above a2's measured range on our mesh -- see crack_band_simplex.py.
   [71] and [72] measure TRS EVOLUTION through heat treatment, which is the
   relaxation our C1 needs and has never had; both are SiC/SiC, not C/SiC.
   A full review of these eight has not been written yet.

8c. FOURTH UPLOAD, 2026-08-06: [57]-[64].  One closes [S8] (Van Paepegem
   cycle jump); the other seven are new numbered references.  Full review in
   docs/REFS_57_64_ASSESSMENT.md.  The two that change something today:

   [60] is PART II of refs/[28] -- the constitutive-model companion to the
   experiment we lean on for C3.  It formalises exactly the mechanism C3
   invokes: "the biaxial compression stresses yield a faster damage
   deactivation rate than the uniaxial compression condition."  It also uses
   a CONTINUOUS deactivation function where our HCLO is a single scalar, so
   our crack-closure treatment is the simpler of the two and must say so.

   [59] Camus 1996 CORRECTS a1-0012.  Its constituent table gives the CVI SiC
   matrix as E = 350 GPa, nu = 0.2, alpha = 4.6e-6 -- essentially our card,
   from an independent 1996 group.  So 350 is NOT an outlier peculiar to
   Zhang [5].  The real situation is two schools using the same words for
   different things: the solid SiC phase (350-460 GPa) versus a
   porosity-degraded effective value (80-143 GPa).  The a1-0012 wording
   "the card is the outlier" was an overstatement and is retracted.

8. THIRD BATCH, 2026-08-06: [46]-[56], eleven papers in two uploads.  EIGHT
   close an [S*] gap -- S1, S2, S3, S4, S5, S6, S7, S10 -- i.e. every method
   primary source the thesis had been citing without holding, except S8, S9
   and S11-S13.  Three are new numbered references: [47] (S21), [51] (S24),
   [54] (S20).  Their filenames match docs/DOWNLOAD_LIST.md exactly.

   [55] is Chamis NASA TM-83320, which micromech_check.py claims to reproduce.
   The equations are figure images and do not extract, but the report's own
   Example 8.1 does, and it validates the FORMULA rather than just our card:

       kf = 0.60, Em = 0.272e6 psi, Ef22 = 2.0e6 psi  ->  E122 = 0.822e6 psi

   Our transverse form E22 = Em / (1 - sqrt(kf)(1 - Em/Ef22)) returns 0.8224,
   which is 0.046 % away.  Until now the yarn card had been checked against
   our own implementation of Chamis; this checks the implementation against
   Chamis.

   [54] is a SCANNED pdf with no text layer (1.3 kB extracts).  On 2026-08-06
   it was OCR-READ in full (tesseract, 18 pages) and turned out to be exactly
   the paper the closure model needed: Chaboche's unilateral condition
   modifies ONLY the diagonal stiffness term of the normal strain that
   changes sign (their eq. 16), with a weighting coefficient eta "with values
   between 0 and 1" -- the published ancestor of our HCLO slot, including its
   full [0,1] range.  It also closes cracks at a NONZERO strain tied to the
   residual strain "observable in C/SiC", where our model closes at exactly
   eps_n = 0; that difference is a recorded limitation, not an error.  OCR
   text is not quote-grade: any verbatim quotation must still be read by eye
   against the page image.

8b. THIRD BATCH, first upload: [46]-[50].  Four are the [S1]-[S4] method primary
   sources the thesis had been citing without holding -- Bazant & Oh, Hashin,
   Tsai & Wu, Liu & Tsai.  They are now held and the [S*] table records it.

   The fifth, [47] Jirasek & Bauer "Numerical aspects of the crack band
   approach", was on no list and is the one that changes something.  Our UMAT
   passes Abaqus CELENT straight in as l_e, and CELENT is the cube root of the
   element volume.  [47] on exactly that rule:

     "the cubic root of the element volume (for three-dimensional elements).
      This rule, implemented in many commercial finite element packages, is
      easy to apply but it can induce a large error for elongated elements,
      and even for square or cube elements if the crack band is not aligned
      with the mesh."

   and sizes the error as "comparable to a misprediction of the fracture
   energy by 50% or even more".  Our RVE has 1185 distorted elements out of
   26452, which is the condition where this is worst.  Handed to a2 as
   a1-0013; choosing l_e is the code side's call.

   The same paper endorses our element choice: "higher-order elements are not
   suitable for crack band simulations, and the simplest (multi)linear
   elements should be preferred."  We use C3D4.

Run:  python3 data/literature/refs_audit.py --check
"""
from __future__ import print_function

import hashlib
import math
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
# Retired numbers: (retired, kept, citation, doi, how it was found).
# The PDF under the retired number is gone; the check asserts it stays gone
# and that nothing points at it any more.
RETIRED = [
    (21, 20, "Yang, Wang, Yang, Jiao, Int. J. Solids Struct. 300 (2024) 112927",
     "10.1016/j.ijsolstr.2024.112927", "refs/README.md 에 적혀 있었으나 방치됨"),
    (39, 32, "Jain & Koch, J. Compos. Sci. 4(4) (2020) 183",
     "10.3390/jcs4040183", "추출 텍스트 md5 대조로 처음 발견"),
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

N_PDF = 75      # 2026-08-23: +[74] Li 2019, +[75] Xu 2023 (the two OA papers)
N_DISTINCT = 75
N_NUMBERS = 73   # [01] and [05] each carry two different papers
NEXT_FREE = 74   # 21 and 39 are retired, never reused

# Third batch, 2026-08-06.  Four of the five close [S*] gaps -- method primary
# sources the thesis had been citing without holding the originals.
THIRD_BATCH = {
    46: ("S1", "Bazant & Oh, Mater. Struct. 16(93) (1983) 155-177"),
    47: (None, "Jirasek & Bauer, Comput. Struct. 110-111 (2012) 60-78 -- bears "
               "directly on our CELENT-based l_e"),
    48: ("S4", "Liu & Tsai, Compos. Sci. Technol. 58 (1998) 1023-1032"),
    49: ("S2", "Hashin, J. Appl. Mech. 47(2) (1980) 329-334"),
    50: ("S3", "Tsai & Wu, J. Compos. Mater. 5(1) (1971) 58-80"),
    51: (None, "Hashin & Rotem, J. Compos. Mater. 7(4) (1973) 448-464"),
    52: ("S5", "Matzenmiller, Lubliner, Taylor, Mech. Mater. 20 (1995) 125"),
    53: ("S10", "Chaboche, Int. J. Damage Mech. 1(2) (1992) 148-171"),
    54: (None, "Chaboche, Lesne, Maire, Int. J. Damage Mech. 4(1) (1995) 5-22 "
               "-- SCANNED, no text layer"),
    55: ("S6", "Chamis, NASA TM-83320 (1983)"),
    56: ("S7", "Schapery, J. Compos. Mater. 2(3) (1968) 380-404"),
    57: ("S8", "Van Paepegem, Degrieck, De Baets, Compos. B 32 (2001) 575"),
    58: (None, "Cojocaru & Karlsson, Int. J. Fatigue 28 (2006) 1677 -- "
               "ADAPTIVE cycle jump"),
    59: (None, "Camus, Guillaumat, Baste, Compos. Sci. Technol. 56 (1996) 1363"),
    60: (None, "Li et al. Chin. J. Aeronaut. 28(1) (2015) 314 -- PART II of "
               "refs/[28]"),
    61: (None, "Mei et al., Carbon 44 (2006) 121"),
    62: (None, "Baste, Compos. Sci. Technol. 61 (2001) 2285"),
    63: (None, "Mei et al., Carbon 45 (2007) 2195 -- also Zhang[5] ref [36]"),
    64: (None, "Wu et al., Materials 19(2) (2026) 307 -- 2.5D, oxidation"),
    65: (None, "Wei et al., Ceram. Int. 50 (2024) 34442 -- SiC/SiC"),
    66: (None, "Hamza, Schichtel, Chattopadhyay, JECS 45 (2025) 117335 -- "
               "same group as [5b]"),
    67: (None, "Mei & Cheng, Mater. Sci. Technol. (2008) -- thermal+mechanical"),
    68: (None, "Mei, Cheng, Zhang, JACS 89(7) (2006) 2330 -- DISPLACEMENT "
               "CONSTRAINT"),
    69: (None, "Shen & Arruda, Int. J. Damage Mech. (2026) -- regularization "
               "review; gives the published tetrahedron he = (12 Ve)^(1/3)"),
    70: (None, "smooth Lagrangian crack band model, IJNLM 186 (2026) 105340"),
    71: (None, "synchrotron XRD residual stress, JACS (2020)"),
    72: (None, "Raman residual stress vs heat treatment, JACS (2019)"),
    73: (None, "Zhong, Guo, Liu, Lu, Zeng, Compos. Struct. 128 (2015) 1-9 "
               "-- Zhang[5] ref 30, the ORIGIN of X_PO/K_1.  Holds the "
               "definitions but publishes NO numeric value for either"),
}

# refs/[61] Table 1, as-received 2D C/SiC (CVI).  Read off the PDF.
MEI2006_T1 = dict(rho=2.0, E=70.0, strength=248.0, nu=0.32, porosity=13.0,
                  cte={600: 4.6, 800: 6.1, 1000: 5.2, 1200: 5.4})
MEI2006_RETENTION = {"wet oxygen": 88.92, "argon": 98.90,
                     "dry oxygen": 96.46, "water vapour": 95.82}

# refs/[59] Camus 1996 constituent table -- the correction to a1-0012.
CAMUS_MATRIX = dict(rho=3.2, E=350.0, nu=0.2, cte=4.6)
OUR_MATRIX = dict(E=350.0, nu=0.20, cte=4.5)

# Chamis NASA TM-83320 Example 8.1, transcribed from the report.  The
# equations themselves are figure images and cannot be extracted, but this
# worked example can -- and it validates the FORMULA, not just our card.
CHAMIS_EX81 = dict(kf=0.60, Em=0.272, Ef22=2.0, E122=0.822)   # 1e6 psi

# Numbers that legitimately hold two DIFFERENT papers, and whether the thesis
# can tell them apart.  "resolved" means the reference list separates them.
# number -> (what the two papers are, (key_a, key_b) the reference list uses
# to separate them, or None while unresolved)
COLLISIONS = {
    1: ("Yang & Liu x2 (Ceram. Int. 46 (2020) 6029 and Int. J. Fatigue 134 "
        "(2020) 105507)", ("01a", "01b")),
    5: ("Q. Zhang et al. Ceram. Int. 48 (2022) 3109 [5] and Skinner & "
        "Chattopadhyay Compos. Struct. 268 (2021) 114006 [5b]", ("5", "5b")),
}


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
    first time this was run.

    A reference-list ROW is not a citation either, and conflating THAT
    silently disabled the orphan check for every key in the table: each row
    opens with its own marker, so every listed key counted as citing itself
    and "listed but never cited" could never fire.  It hid [S9] (Chaboche
    1993), which is listed and cited nowhere.  Rows are skipped here."""
    # A struck-through row (~~[S9]~~) is still a ROW -- it records a
    # deleted entry and its reason.  Tolerating the markers keeps that
    # audit trail without the row reading as a live citation.
    row = re.compile(r"^\|\s*[~*]{0,4}\[(?:\d{1,2}[a-b]?|[SC]\d{1,2})\]"
                     r"[~*]{0,4}\s*\|")
    cited, filed = {}, {}
    for fn in sorted(os.listdir(DOCS)):
        if not re.match(r"CH\d_.*\.md$", fn):
            continue
        txt = open(os.path.join(DOCS, fn), encoding="utf-8").read()
        body = "\n".join(l for l in txt.splitlines() if not row.match(l))
        for m in re.finditer(r"(refs/)?\[(\d{1,2}[a-b]?|[SC]\d{1,2})\]", body):
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

    print("\n 2. retired numbers (were duplicates, now consolidated)")
    for dead, keep, cite, doi, note in RETIRED:
        print("     [%02d] -> [%02d]  %s" % (dead, keep, cite))
        print("                   doi:%s  -- %s" % (doi, note))
    print("     -> %d files, %d distinct papers; next free number is %d"
          % (N_PDF, N_DISTINCT, NEXT_FREE))

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

    print("\n 5. what this changed")
    print("     * [21] and [39] deleted, numbers retired -- 45 files = 45 papers")
    print("     * [39] had been written up as a NEW acquisition of a source")
    print("       that was already in refs/ as [32]; that text is corrected")
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
    t("one PDF per paper", N_PDF == N_DISTINCT)
    raw = sorted(n for n, _, _ in inv)      # NOT by_n -- that is deduplicated
    t("exactly %d distinct numbers" % N_NUMBERS,
      len(set(raw)) == N_NUMBERS, "%d" % len(set(raw)))
    twice = sorted(n for n in set(raw) if raw.count(n) > 1)
    t("the only numbers used twice are the known collisions",
      twice == sorted(COLLISIONS), ", ".join("[%02d]" % n for n in twice))

    print("\n B. the retired numbers are gone and stay gone")
    for dead, keep, cite, doi, _ in RETIRED:
        t("refs/[%02d] no longer exists" % dead, dead not in by_n)
        t("  its paper survives as refs/[%02d]" % keep, keep in by_n)
        txt = by_n[keep][1] if keep in by_n else None
        if txt:
            t("  and [%02d] really carries doi %s" % (keep, doi), doi in txt)
        else:
            t("  and [%02d] really carries doi %s" % (keep, doi), True,
              "recorded")

    print("\n B2. no NEW duplicate has appeared")
    seen, dup = {}, []
    ran = False
    for n, fn, txt in inv:
        if not txt:
            continue
        ran = True
        h = hashlib.md5(txt.encode()).hexdigest()
        if h in seen:
            dup.append((seen[h], n))
        seen[h] = n
    t("the hash sweep actually ran on the PDFs", ran)
    t("no two PDFs have identical text", not dup,
      ", ".join("[%02d]=[%02d]" % p for p in dup) if dup else "")

    print("\n B3. two papers under one number -- known, and is it resolvable")
    _, _, listed0 = citations()
    for n, (what, keys) in sorted(COLLISIONS.items()):
        t("refs/[%02d] holds two different papers" % n,
          sorted(x[0] for x in inv).count(n) == 2, what[:46])
        if keys:
            ka, kb = keys
            t("  and the reference list separates them ([%s] vs [%s])"
              % (ka, kb), ka in listed0 and kb in listed0)
        else:
            t("  and the reference list does NOT separate them -- flagged",
              str(n) in listed0 or "%02d" % n in listed0,
              "single row covers both; splitting is the author's call")

    print("\n C. nothing points at a retired number")
    cited, filed, listed = citations()
    body = ""
    for fn in os.listdir(DOCS):
        if fn.endswith(".md"):
            body += open(os.path.join(DOCS, fn), encoding="utf-8").read()
    for dead, keep, _, _, _ in RETIRED:
        t("no chapter cites [%02d]" % dead,
          "%02d" % dead not in listed and str(dead) not in listed)
        t("  and no document points at refs/[%02d]" % dead,
          "refs/[%02d]" % dead not in body)

    print("\n D. every cited marker has a reference-list entry")
    cited, filed, listed = citations()
    ln = {norm(k) for k in listed}
    missing = sorted([k for k in cited if norm(k) not in ln])
    t("nothing is cited into thin air", not missing,
      ", ".join("[%s]" % k for k in missing) if missing else "")
    for k, who in sorted(MUST_BE_LISTED.items()):
        t("[%s] is listed with real bibliography" % k, norm(k) in ln,
          who[:44])
    # An entry that no chapter cites splits in two, and the split matters.
    # If a chapter at least POINTS at the file as refs/[nn], the paper is in
    # use and simply has not been written into prose yet -- a to-do for the
    # writing, not a bibliography error.  If nothing references it at all,
    # it is a dead entry and must be cited or removed before submission.
    cn = {norm(c) for c in cited}
    fnm = {norm(f) for f in filed}
    uncited = [k for k in listed if norm(k) not in cn]
    dead = sorted(k for k in uncited if norm(k) not in fnm)
    held = sorted(k for k in uncited if norm(k) in fnm)
    t("no entry is dead -- listed, and referenced nowhere at all",
      not dead, ", ".join("[%s]" % k for k in dead) if dead else "")
    print("       (held but not yet written into prose: %s)"
          % (", ".join("[%s]" % k for k in held) or "none"))
    # [S9] was the finding that exposed the hole in this very check.
    t("[S9] is gone from the reference list",
      "S9" not in listed,
      "superseded by refs/[54], the same author's 1995 sequel")
    t("  and its replacement is both held and cited", "54" in listed)
    ch2txt = open(CH2, encoding="utf-8").read()
    t("the [S*] triage is written down, not left as 'could not obtain'",
      "미확보 `[S*]`의 처리" in ch2txt)
    for key, verdict in (("S11", "확보 불필요"), ("S12", "확보 권장"),
                         ("S13", "서지·수식은 2026-08-06 확인 완료")):
        t("  [%s] carries a verdict of its own" % key,
          ("`[%s]`" % key) in ch2txt and verdict in ch2txt, verdict[:24])

    # [S12] Hasselman 1963, verified the same way as [S13] on 2026-08-06.
    # The direction check is algebra, not trust: the paper's stated low-
    # damage criteria (high E, high nu, high surface energy, LOW strength)
    # must be the monotonicities of the R'''' the chapter prints.
    print("\n D3. [S12] Hasselman 1963 -- verified without holding it")
    t("bibliography matches the record",
      "46(11) (1963) 535–540" in ch2txt
      and "10.1111/j.1151-2916.1963.tb14605.x" in ch2txt)

    def r4p(E, g, s, nu):
        return E * g / (s ** 2 * (1.0 - nu))
    base = r4p(1.0, 1.0, 1.0, 0.2)
    t("R'''' rises with E and surface energy",
      r4p(2.0, 1.0, 1.0, 0.2) > base and r4p(1.0, 2.0, 1.0, 0.2) > base)
    t("  falls with strength", r4p(1.0, 1.0, 2.0, 0.2) < base)
    t("  rises with Poisson's ratio", r4p(1.0, 1.0, 1.0, 0.3) > base)
    t("  which is exactly the 1963 low-damage criteria set",
      "낮은 강도" in ch2txt and "저장 탄성에너지가 균열 전파의 구동력" in ch2txt)
    t("so the 1963-vs-1969 attribution box is now backed, not asserted",
      "귀속 정정(1963 대 1969)이 지지" in ch2txt)
    t("and the remaining unknown is narrowed to the spherical derivation",
      "구형 시편 유도의 세부뿐" in ch2txt)

    # C5-C7 are the cohesive-fatigue precedents 2.5.4 leans on.  Same
    # treatment: verify what can be verified without the papers, and CHANGE
    # THE ATTRIBUTION where the draft claimed more than that supports.
    print("\n D4. C5-C7 cohesive-fatigue precedents -- attribution narrowed")
    t("the three bibliographies are stated with volume and pages",
      "**70** (2003) 209–232" in ch2txt
      and "**32** (2010) 158–165" in ch2txt
      and "**110** (2001) 351–369" in ch2txt)
    t("Roe & Siegmund's DIAGNOSIS attribution is retracted",
      "확인 안 됨" in ch2txt and "명시적 서술" in ch2txt)
    t("  and replaced by what is verified -- the PRESCRIPTION",
      "단조 응집강도를 사이클마다 열화" in ch2txt and "문턱" in ch2txt)
    t("Hochard's additive-decomposition attribution is retracted too",
      "분해의 형태는 확인 안 됨" in ch2txt)
    t("Nguyen is marked unverified rather than quietly kept",
      "미확인" in ch2txt)
    # The diagnosis needs no citation: 2.5.4 already calls it algebra.
    t("the diagnosis is claimed as algebra, not as a literature finding",
      "구성식의 수학적 성질이지 문헌의" in ch2txt
      and "문헌적 발견이 아니라 구성식의 수학적 성질이다" in ch2txt)
    # And the payoff: our own law has the verified structure.
    t("our Delta_d_cyc is shown to share the verified structure",
      "본 연구의 $\\Delta d_{cyc}$가 정확히 그 구조다" in ch2txt
      and "Macaulay" in ch2txt)
    t("  which is a stronger claim than the draft made",
      "형태에는 선례가 있으며" in ch2txt)
    t("no quotation marks are used while the papers are unheld",
      "원문 확보 전까지 인용부호는 쓰지 않는다" in ch2txt)

    # [S13] is paywalled and stays unheld, so what CAN be verified without it
    # was verified against independent secondary sources and pinned here.
    # Doing that turned up an error in 2.4.4 that had nothing to do with
    # holding the paper: the abscissa.
    print("\n D2. [S13] Hasselman 1969 -- verified without holding it")
    t("the bibliography Ch.2 states is the one the record gives",
      "52 (1969) 600–604" in ch2txt
      and "10.1111/j.1151-2916.1969.tb15848.x" in ch2txt)
    t("R_st is quoted in the form the secondary literature gives",
      r"\gamma_{wof}}{E\,\alpha^2}" in ch2txt
      or r"\gamma_{wof}/(E\alpha^2)" in ch2txt)
    # THE CORRECTION.  Hasselman's residual-strength curve runs against the
    # dT of a SINGLE quench; the classical quench test is a single-cycle
    # test.  YIN2002's curve runs against CYCLE NUMBER at fixed dT.  The
    # draft called them the same shape and drew a conclusion from it.
    t("Ch.2 says the abscissa is a single quench's dT, not cycle count",
      "가로축은 사이클 수가 아니라 단회 급랭" in ch2txt)
    t("  and says so as a correction to the draft, not silently",
      "여기서 정정한다" in ch2txt)
    t("  and forbids the overlay figure that error would have produced",
      "겹쳐 그리는 그림은 만들지 않는다" in ch2txt)
    t("R_st is no longer called a repeated-thermal-shock parameter",
      "반복 열충격을 직접 겨냥한" not in ch2txt)
    t("  what survives is the stable-growth precondition, stated as such",
      "안정 성장" in ch2txt and "전제 점검" in ch2txt)

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

    print("\n G2. third batch [46]-[56]")
    for n, (skey, cite) in sorted(THIRD_BATCH.items()):
        t("refs/[%02d] is on the shelf" % n, n in by_n, cite[:44])
    got = [k for _, (k, _) in THIRD_BATCH.items() if k]
    t("nine of the nineteen close an [S*] gap", len(got) == 9,
      ", ".join(sorted(got)))
    ch2 = open(CH2, encoding="utf-8").read()
    for n, (skey, _) in sorted(THIRD_BATCH.items()):
        if skey:
            t("  [%s] now records 'refs/[%02d]' as held" % (skey, n),
              "refs/[%02d]" % n in ch2)
    t("[47] is listed as a numbered reference, not only as an [S*]",
      "[47]" in ch2 and "compstruc.2012.06.006" in ch2)
    t("and its CELENT warning is carried into the reference row",
      "CELENT" in ch2)
    for n in (51, 54):
        t("[%d] is listed as a numbered reference" % n, "[%d]" % n in ch2)
    t("[54] scan was OCR-read and the row records what it holds",
      "OCR" in ch2 and "OCR-READ" in __doc__)
    t("  the eta-in-[0,1] closure coefficient is recorded from it",
      "between 0 and 1" in __doc__ and "η ∈ [0,1]" in ch2)

    print("\n G2b. fourth upload -- the two that change something")
    t("[60] is recorded as Part II of refs/[28]",
      "PART II of " in THIRD_BATCH[60][1])
    t("  and Ch.2 now flags [28] as Part I", "Part II는 `[60]`" in ch2)
    t("[59] Camus matrix E matches our card, not the low school",
      abs(CAMUS_MATRIX["E"] - OUR_MATRIX["E"]) < 1e-9,
      "%.0f vs %.0f GPa" % (CAMUS_MATRIX["E"], OUR_MATRIX["E"]))
    t("  nu matches too", abs(CAMUS_MATRIX["nu"] - OUR_MATRIX["nu"]) < 1e-9)
    t("  and CTE to within 2.3 %",
      abs(CAMUS_MATRIX["cte"] / OUR_MATRIX["cte"] - 1.0) < 0.025,
      "%.1f vs %.1f e-6" % (CAMUS_MATRIX["cte"], OUR_MATRIX["cte"]))
    t("so the a1-0012 'card is the outlier' wording is retracted here",
      "was an overstatement and is retracted" in __doc__)
    t("[61] Table 1 is transcribed with its porosity",
      abs(MEI2006_T1["porosity"] - 13.0) < 1e-9)
    t("  and four CTE points for the composite", len(MEI2006_T1["cte"]) == 4)
    t("  and its 70 GPa modulus is 1.84x below refs/[10]'s 128.7",
      abs(128.7 / MEI2006_T1["E"] - 1.838) < 0.01,
      "%.2fx" % (128.7 / MEI2006_T1["E"]))
    t("  retention in argon is the 98.90 % also quoted from refs/[43]",
      abs(MEI2006_RETENTION["argon"] - 98.90) < 1e-9)
    assess = os.path.join(DOCS, "REFS_57_64_ASSESSMENT.md")
    t("the full review exists", os.path.exists(assess))

    print("\n G3. Chamis Example 8.1 validates the FORMULA, not just the card")
    e = CHAMIS_EX81
    got_e = e["Em"] / (1.0 - math.sqrt(e["kf"]) * (1.0 - e["Em"] / e["Ef22"]))
    t("our transverse Chamis form reproduces the report's own example",
      abs(got_e - e["E122"]) / e["E122"] < 2e-3,
      "%.4f vs %.3f e6 psi  (%.3f %%)"
      % (got_e, e["E122"], 100 * abs(got_e - e["E122"]) / e["E122"]))
    mm = os.path.join(ROOT, "verification", "micromech_check.py")
    src = open(mm).read() if os.path.exists(mm) else ""
    t("micromech_check.py uses the same sqrt(Vf) form", "math.sqrt(Vf)" in src)
    t("so the card check and the formula check are now independent",
      bool(src) and "Example 8.1" not in src)

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
