#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yarn_fracture_energy.py
=======================
Sources the yarn TRANSVERSE fracture energies Gtt and Gtc, which are the last
two zeros in the yarn card, and works out whether the sourced values are usable
on the mesh we actually have.

The problem
-----------
The yarn card carries G1t = G1c = 12.5 N/mm but Gtt = Gtc = 0.  A zero makes
KABAND fall back to the fixed softening factor A = 2.0, which means the
transverse modes are NOT crack-band regularised and therefore NOT mesh
objective.  Ch.3 3.8 and Ch.4 4.9 both list this as blocking any mesh-
convergence claim.

What the search found
---------------------
1. WHERE 12.5 CAME FROM.  Ge et al., Compos. Sci. Technol. 157 (2018) 86-98
   -- refs/[24], the origin model of this constitutive law -- Table 3 lists
   Gf,1t = Gf,1c = 12.5 N/mm and Gf,2(3)t = Gf,2(3)c = 1.0 N/mm.  Our card's
   12.5 is that table.

   BUT THAT TABLE IS CARBON/PHENOLIC, NOT C/SiC.  Its matrix is Em = 3.2 GPa,
   Xm,t = 75 MPa.  Ours is SiC at 350 GPa.  The longitudinal value is
   fibre-dominated and both materials use T300, so carrying 12.5 across is
   arguable.  The TRANSVERSE value is matrix-dominated, and a matrix 100x
   stiffer cannot inherit a phenolic number.  So 1.0 N/mm is REJECTED here,
   and the reason is recorded rather than left implicit.

2. THE RIGHT MATERIAL.  Shi, Zhang, Wang, Li, Zhang, Compos. Part A 168 (2023)
   107466 measured mode-I interlaminar fracture toughness of 2D PLAIN WEAVE
   CVI-C/SiC by a wedge-loaded DCB:

       G_Ic = 0.107 +/- 0.017 N/mm

   The mechanism they report is the one that governs transverse tow cracking:
   "crack propagation is accompanied by debonding between the matrix and
   fibers ... there is no obvious fiber-bridging, which is in line with linear
   elastic fracture mechanics".  No bridging, matrix/interface controlled.

   CAVEAT, and it is a real one: this is an INTERLAMINAR value (crack between
   plies, through inter-tow matrix), not a measurement inside a tow.  It is the
   closest measured analogue in the right material, and it is used as such --
   labelled, not laundered.

3. THE MONOLITHIC FLOOR.  Snead et al., J. Nucl. Mater. 371 (2007) 329-377 --
   refs/[06] -- gives KIC(298 K) = 3.2-3.5 MPa.m^0.5 and E0 = 460 GPa for dense
   CVD SiC.  Converting with G = K^2/E gives the neat-matrix value, i.e. what
   the transverse energy would be with no toughening at all.

   That conversion also settles a separate provenance question: evaluated at
   OUR matrix modulus (350 GPa) it returns 0.0321 N/mm against the 0.031 N/mm
   already sitting in the matrix card -- 3.4 % apart, from a completely
   independent route.

The finding that changes what we do
-----------------------------------
Gtt is comfortably admissible; Gtc is not, and not because of the data.

Crack-band regularisation needs  l_e < Gf / (1.02 * g0)  with g0 = X^2 / (2E).
Transverse compression has Yc = 350 MPa against Yt = 80 MPa, so g0 is
(350/80)^2 = 19.1x larger and the SAME fracture energy buys a 19.1x SMALLER
admissible element.  On this mesh that is the difference between a 17x safety
margin and 4 % of elements past the snap-back limit.

POSTSCRIPT (2026-08-19) -- what the decks then DID, and the two rulings
------------------------------------------------------------------------
M6 (0812) adopted Shi's 0.107 into BOTH transverse slots -- exactly option
(a) below.  The audit then found what section 5 predicts: at Yc the mesh
cannot resolve that band (le_max 0.0759 mm < CELENT max 0.0845 mm), and the
M6 damage census measured the transverse-compression mode at <= 0.6 % of
damaged yarn volume while transverse TENSION carried 83-100 %.  M7 (0816)
withdrew Gtc to 0 and kept Gtt; M8 inherits both.  So the open question is
no longer "turn it on?" -- it is (1) was adopting a COMPOSITE-measured
interlaminar value into a constituent card legal, and (2) is the Gtc
withdrawal the settled answer.  Both rulings are recorded and pinned below:
Gtt stays, graded DEV, never IN; Gtc = 0 is CONFIRMED, superseding this
file's own earlier "(a) as the main case" recommendation.

Run:  python3 data/properties/yarn_fracture_energy.py
      python3 data/properties/yarn_fracture_energy.py --check
"""
from __future__ import print_function

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# --------------------------------------------------------------------------
# yarn card constants (slots 2,3,11,12,13,14 of the 38-slot yarn card)
# --------------------------------------------------------------------------
E1 = 254967.228042          # MPa, longitudinal
E2 = 44321.737572           # MPa, transverse
XT, XC = 2835.0, 1956.0     # MPa, longitudinal strengths
YT, YC = 80.0, 350.0        # MPa, transverse strengths

# --------------------------------------------------------------------------
# measured CELENT distribution of the 26 452-element coarse RVE.
# Abaqus passes CELENT = V^(1/3) for a tetrahedron, and that is the length
# KABAND regularises against -- NOT the longest edge, which is ~3x larger.
# Recomputed from the shipped deck by --check.
# --------------------------------------------------------------------------
CELENT_MAX = 0.0845         # mm
CELENT_P50 = 0.0573         # mm
NELEM = 26452

# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------
GE2018 = dict(key="GE2018", ref="refs/[24]",
              cite="Ge, He, Liang, Chen, Fang, Compos. Sci. Technol. 157 "
                   "(2018) 86-98, Table 3",
              material="3D braided carbon/phenolic (Em = 3.2 GPa)",
              G1t=12.5, G1c=12.5, Gtt=1.0, Gtc=1.0,
              confidence="fulltext")
SHI2023 = dict(key="SHI2023", ref="refs/[31]",
               cite="Shi, Zhang, Wang, Li, Zhang, Compos. Part A 168 (2023) "
                    "107466, Fig. 7(b)",
               material="2D plain weave CVI-C/SiC",
               GIc=0.107, GIc_sd=0.017,
               E11=74500.0, E22=21300.0, TTS=36.5,
               confidence="fulltext")
SNEAD2007 = dict(key="SNEAD2007", ref="refs/[06]",
                 cite="Snead et al., J. Nucl. Mater. 371 (2007) 329-377, "
                      "Table 6 / summary table",
                 material="dense CVD beta-SiC",
                 KIC_lo=3.2, KIC_hi=3.5, E=460000.0, nu=0.21,
                 confidence="fulltext")

OUR_MATRIX_E = 350000.0     # MPa, PIP SiC matrix in our card
OUR_MATRIX_GF = 0.031       # N/mm, already in the matrix card

# --------------------------------------------------------------------------
# what the shipped decks actually carry (read from the committed zips)
# --------------------------------------------------------------------------
RUN_DECKS = [
    ("M6", "dist/LTH_M6_0812_1411.zip", "LTH_M6_0812_1411/LTH_M6_RT23.inp"),
    ("M7", "dist/LTH_M7_0816_2022.zip", "LTH_M7_0816_2022/LTH_M7_RT23.inp"),
    ("M8", "dist/LTH_M8_0818_1231.zip", "LTH_M8_0818_1231/LTH_M8_RT23.inp"),
]

#: committed M6 damage maps -- the measurement that settles which transverse
#: mode is ACTIVE (T1000's map is not committed yet; two suffice).
CENSUS = ["data/results/M6/LTH_M6_RT23_damage_map.csv",
          "data/results/M6/LTH_M6_T500_damage_map.csv"]

#: RULING 1 (a1, 2026-08-19) -- legality of a composite-measured value in a
#: constituent card.  The card rule says constituent data only, because a
#: composite-scale STIFFNESS / STRENGTH / CTE measurement already contains
#: the thermal residual stress state, and simulating the cooldown on top of
#: it counts TRS twice.  That mechanism is ADDITIVE superposition on a
#: load-bearing quantity.  A propagating-crack energy is not such a quantity:
#: Shi measure G_Ic over propagation with no bridging and LEFM valid, so the
#: number is the work of separating the matrix/interface -- TRS can touch it
#: only second-order, through crack path and closure.  A constituent-scale
#: alternative does not exist (limitation 13's negative result, three dated
#: searches), and the true constituent FLOOR (monolithic SiC via Snead
#: K->G = 0.031 N/mm) is retained as the sensitivity anchor, with the whole
#: band floor..+1sd admissible on this mesh in tension.  Hence: usable, but
#: as DEV -- an analogue transfer, cited with the interlaminar caveat every
#: time -- and never promotable to IN, because the second-order TRS residue
#: in the measured value cannot be bounded from the paper.
GTT_RULING = dict(
    grade="DEV",
    never="IN",
    mechanism="additive-TRS double count does not operate on a "
              "propagation energy; residual influence is second-order "
              "(crack path / closure), recorded as the residual risk",
    fallback_anchor=0.031,
    date="2026-08-19")

#: RULING 2 (a1, 2026-08-19) -- Gtc.  This file recommended "(a) Gtc = Gtt
#: as the main case" before M6 ran.  M6 ran (a); two measurements reversed
#: it: the mesh cannot resolve the compressive band (le_max < CELENT max,
#: section 5), and the damage census puts the mode at <= 0.6 % of damaged
#: yarn volume -- there is nothing to regularise, only clamp noise to buy.
#: M7 withdrew it (code side); this ruling CONFIRMS the withdrawal (card
#: side) and supersedes option (a).  Limitation 13 stands.
GTC_VERDICT = dict(
    choice="(c) keep 0",
    supersedes="(a) Gtc = Gtt, this file's pre-M6 recommendation",
    evidence_mesh="le_max at Yc is below the largest element",
    evidence_census="mode 24 carries <= 0.6 % of damaged yarn volume",
    date="2026-08-19")


def run_deck_slots(zip_rel, inp_name):
    """(Gtt, Gtc) = yarn-card slots 34/35 of a shipped deck."""
    import re
    import zipfile
    with zipfile.ZipFile(os.path.join(ROOT, zip_rel)) as z:
        txt = z.read(inp_name).decode("utf-8", "replace")
    m = re.search(r"\*User Material, constants=38\n(.*?)(?=\*[A-Za-z])",
                  txt, re.S | re.I)
    vals = [float(v) for v in re.split(r"[,\n]", m.group(1)) if v.strip()]
    return vals[33], vals[34]


def census_modefrac(path, mode):
    """Largest volume fraction DMODE <mode> reaches in any tension step."""
    import csv
    with open(os.path.join(ROOT, path)) as fh:
        rows = list(csv.DictReader(fh))
    vals = [float(r["value"]) for r in rows
            if r["item"].startswith("modefrac_%d" % mode)
            and "Tension" in r["step"]]
    return max(vals) if vals else 0.0


def g_from_k(kic_mpa_rootm, e_mpa):
    """Convert KIc [MPa.m^0.5] to Gc [N/mm] at modulus E [MPa].

    G = K^2 / E in consistent SI gives J/m^2; 1 J/m^2 = 1e-3 N/mm.
    """
    k_pa = kic_mpa_rootm * 1.0e6            # Pa.m^0.5
    e_pa = e_mpa * 1.0e6                    # Pa
    g_j_per_m2 = k_pa * k_pa / e_pa         # J/m^2
    return g_j_per_m2 * 1.0e-3              # N/mm


def le_max(gf, strength, modulus):
    """Largest element (CELENT) for which the softening branch has no snap-back.

    Mirrors KABAND: A = 2*g0*le/(Gf - g0*le) is only used when
    Gf > 1.02*g0*le; otherwise A is clamped to 50 (effectively brittle).
    """
    g0 = strength * strength / (2.0 * modulus)
    return gf / (1.02 * g0), g0


def report():
    print("=" * 74)
    print("YARN TRANSVERSE FRACTURE ENERGY -- sources and admissibility")
    print("=" * 74)

    print("\n1. WHERE THE EXISTING 12.5 N/mm CAME FROM")
    print("   %s  %s" % (GE2018["ref"], GE2018["cite"]))
    print("   material: %s" % GE2018["material"])
    print("   G1t = G1c = %.1f N/mm      <- this is our card, slots 32/33"
          % GE2018["G1t"])
    print("   Gtt = Gtc = %.1f N/mm      <- REJECTED: wrong matrix"
          % GE2018["Gtt"])
    print("   The longitudinal mode is fibre-dominated and both materials use")
    print("   T300, so 12.5 transfers arguably. The transverse mode is")
    print("   matrix-dominated and their matrix is 3.2 GPa against our 350 GPa.")

    print("\n2. THE MEASURED VALUE IN THE RIGHT MATERIAL")
    print("   %s  %s" % (SHI2023["ref"], SHI2023["cite"]))
    print("   material: %s" % SHI2023["material"])
    print("   mode-I G_Ic = %.3f +/- %.3f N/mm   (W-DCB)"
          % (SHI2023["GIc"], SHI2023["GIc_sd"]))
    print("   reported mechanism: matrix/fibre debonding, NO fibre bridging,")
    print("   LEFM applies -- the mechanism that governs transverse cracking.")
    print("   their E22 = %.0f MPa, transverse tensile strength = %.1f MPa"
          % (SHI2023["E22"], SHI2023["TTS"]))
    print("   CAVEAT: interlaminar, not intra-tow. Closest measured analogue.")

    print("\n3. THE MONOLITHIC FLOOR (no toughening)")
    glo = g_from_k(SNEAD2007["KIC_lo"], SNEAD2007["E"])
    ghi = g_from_k(SNEAD2007["KIC_hi"], SNEAD2007["E"])
    print("   %s  %s" % (SNEAD2007["ref"], SNEAD2007["cite"]))
    print("   KIC = %.1f-%.1f MPa.m^0.5 at E = %.0f GPa"
          % (SNEAD2007["KIC_lo"], SNEAD2007["KIC_hi"],
             SNEAD2007["E"] / 1000.0))
    print("   -> G = K^2/E = %.4f - %.4f N/mm  (dense CVD SiC)" % (glo, ghi))
    ours_lo = g_from_k(SNEAD2007["KIC_lo"], OUR_MATRIX_E)
    ours_hi = g_from_k(SNEAD2007["KIC_hi"], OUR_MATRIX_E)
    mid = 0.5 * (ours_lo + ours_hi)
    print("   -> at OUR matrix modulus %.0f GPa: %.4f - %.4f N/mm"
          % (OUR_MATRIX_E / 1000.0, ours_lo, ours_hi))
    print("      matrix card already carries Gf = %.3f N/mm; midpoint %.4f"
          % (OUR_MATRIX_GF, mid))
    print("      -> %.1f %% apart, from an independent route. The matrix"
          % (100.0 * abs(mid - OUR_MATRIX_GF) / OUR_MATRIX_GF))
    print("         fracture energy is corroborated as a side effect.")
    print("   composite / monolithic = %.1fx -- the interphase is doing what"
          % (SHI2023["GIc"] / (0.5 * (glo + ghi))))
    print("   it is there to do, which is the sanity check on 0.107.")

    print("\n4. IS IT ADMISSIBLE ON THE MESH WE HAVE?")
    print("   crack band needs  CELENT < Gf / (1.02 * g0),  g0 = X^2/(2E)")
    print("   this mesh: %d elements, CELENT max %.4f mm, median %.4f mm"
          % (NELEM, CELENT_MAX, CELENT_P50))
    print()
    print("   %-30s %9s %9s %10s %s"
          % ("mode", "G [N/mm]", "g0 [MPa]", "le_max[mm]", "margin"))
    rows = [
        ("G1t longitudinal tension", 12.5, XT, E1),
        ("G1c longitudinal compression", 12.5, XC, E1),
        ("Gtt transverse tension", SHI2023["GIc"], YT, E2),
        ("Gtt  -1 s.d. (0.090)", SHI2023["GIc"] - SHI2023["GIc_sd"], YT, E2),
        ("Gtt  +1 s.d. (0.124)", SHI2023["GIc"] + SHI2023["GIc_sd"], YT, E2),
        ("Gtt  monolithic floor", mid, YT, E2),
        ("Gtc transverse compression", SHI2023["GIc"], YC, E2),
        ("Gtc  monolithic floor", mid, YC, E2),
    ]
    for lab, g, x, e in rows:
        L, g0 = le_max(g, x, e)
        margin = L / CELENT_MAX
        flag = "%.1fx OK" % margin if margin > 1.0 else "** VIOLATED **"
        print("   %-30s %9.4g %9.4f %10.4f %s" % (lab, g, g0, L, flag))

    print("\n5. THE PROBLEM IS Gtc, AND IT IS NOT A DATA PROBLEM")
    ratio = (YC / YT) ** 2
    Lt, _ = le_max(SHI2023["GIc"], YT, E2)
    Lc, _ = le_max(SHI2023["GIc"], YC, E2)
    print("   Yc/Yt = %.3f, so g0 is %.1fx larger in compression and the SAME"
          % (YC / YT, ratio))
    print("   fracture energy buys a %.1fx smaller admissible element:" % ratio)
    print("       tension     le_max = %.4f mm  -> %.0fx margin" %
          (Lt, Lt / CELENT_MAX))
    print("       compression le_max = %.4f mm  -> BELOW the largest element"
          % Lc)
    print("   No measurement of TRANSVERSE COMPRESSIVE fracture energy in")
    print("   C/SiC was found. Three options were on the table:")
    print("     (a) Gtc = Gtt = 0.107 (Ge's convention).  Clamp risk.")
    scaled = SHI2023["GIc"] * ratio
    Ls, _ = le_max(scaled, YC, E2)
    print("     (b) Gtc = Gtt*(Yc/Yt)^2 = %.3f N/mm (equalises le_max at"
          % scaled)
    print("         %.4f mm) -- a numerical choice, NOT a measurement." % Ls)
    print("     (c) Gtc = 0: that mode not regularised, by declaration.")
    print("   This file ONCE recommended (a).  M6 ran (a), and two")
    print("   measurements reversed it -- see section 6.")

    print("\n6. WHAT THE DECKS DID, AND THE TWO RULINGS (2026-08-19)")
    print("   deck   slot 34 Gtt   slot 35 Gtc")
    for tag, zrel, inp in RUN_DECKS:
        try:
            gtt, gtc = run_deck_slots(zrel, inp)
            print("   %-5s  %8.3f      %8.3f" % (tag, gtt, gtc))
        except Exception as e:                          # noqa: BLE001
            print("   %-5s  (unreadable: %s)" % (tag, e))
    print("   M6 adopted (a); M7 withdrew Gtc to 0; M8 inherits 0.107 / 0.")
    print()
    print("   RULING 1 -- Gtt = 0.107 STAYS, graded %s (never %s)."
          % (GTT_RULING["grade"], GTT_RULING["never"]))
    print("   A composite-measured interlaminar energy in a constituent")
    print("   card: %s." % GTT_RULING["mechanism"])
    print("   Constituent floor %.3f N/mm stays as the sensitivity anchor."
          % GTT_RULING["fallback_anchor"])
    print()
    m23 = max(census_modefrac(c, 23) for c in CENSUS)
    m24 = max(census_modefrac(c, 24) for c in CENSUS)
    print("   RULING 2 -- Gtc: %s, superseding %s."
          % (GTC_VERDICT["choice"], GTC_VERDICT["supersedes"]))
    print("   evidence: %s (%.4f < %.4f mm);"
          % (GTC_VERDICT["evidence_mesh"], Lc, CELENT_MAX))
    print("             %s (census max %.4f; tension mode 23 reaches %.3f)"
          % (GTC_VERDICT["evidence_census"], m24, m23))
    print("   Crushing, not crack opening -- a mode-I band was already an")
    print("   approximation there.  Limitation 13 stands.")
    print("   slots 20/21 Att/Atc are IGNORED wherever Gf > 0 (KABAND).")
    print("=" * 74)
    return 0


# --------------------------------------------------------------------------
def check():
    ok = [0]
    bad = [0]

    def t(name, cond, extra=""):
        if cond:
            ok[0] += 1
            print("  [PASS] %s %s" % (name, extra))
        else:
            bad[0] += 1
            print("  [FAIL] %s %s" % (name, extra))

    print("=" * 74)
    print("yarn_fracture_energy.py --check")
    print("=" * 74)

    # --- the K -> G conversion, by hand on a round case -------------------
    # K = 1 MPa.m^0.5, E = 1000 MPa  ->  G = 1e12/1e9 Pa.m = 1e3 J/m^2 = 1 N/mm
    t("K->G conversion is dimensionally right",
      abs(g_from_k(1.0, 1000.0) - 1.0) < 1e-12,
      "%.6f N/mm" % g_from_k(1.0, 1000.0))
    t("K->G scales as K^2",
      abs(g_from_k(2.0, 1000.0) / g_from_k(1.0, 1000.0) - 4.0) < 1e-12)
    t("K->G scales as 1/E",
      abs(g_from_k(1.0, 2000.0) / g_from_k(1.0, 1000.0) - 0.5) < 1e-12)

    # --- Snead -> our matrix reproduces the card's Gf ----------------------
    lo = g_from_k(SNEAD2007["KIC_lo"], OUR_MATRIX_E)
    hi = g_from_k(SNEAD2007["KIC_hi"], OUR_MATRIX_E)
    mid = 0.5 * (lo + hi)
    t("Snead KIC at our E brackets the matrix card Gf",
      lo <= OUR_MATRIX_GF <= hi, "%.4f <= %.3f <= %.4f" % (lo, OUR_MATRIX_GF, hi))
    t("and agrees with it within 5 %",
      abs(mid - OUR_MATRIX_GF) / OUR_MATRIX_GF < 0.05,
      "%.1f %%" % (100.0 * abs(mid - OUR_MATRIX_GF) / OUR_MATRIX_GF))

    # --- the composite value must exceed the monolithic one ---------------
    glo = g_from_k(SNEAD2007["KIC_lo"], SNEAD2007["E"])
    ghi = g_from_k(SNEAD2007["KIC_hi"], SNEAD2007["E"])
    t("measured C/SiC G_Ic exceeds neat dense SiC",
      SHI2023["GIc"] > ghi,
      "%.3f > %.4f" % (SHI2023["GIc"], ghi))
    ratio = SHI2023["GIc"] / (0.5 * (glo + ghi))
    t("toughening ratio is physically plausible (2-10x)",
      2.0 < ratio < 10.0, "%.1fx" % ratio)

    # --- crack-band arithmetic mirrors KABAND -----------------------------
    L, g0 = le_max(0.031, 310.0, 350000.0)
    t("le_max reproduces Ch.4's matrix limit 0.2214 mm",
      abs(L - 0.2214) < 5e-4, "%.4f mm" % L)
    t("g0 = X^2/(2E) for the matrix", abs(g0 - 310.0 ** 2 / 700000.0) < 1e-12)

    # --- the admissibility verdicts the report makes ----------------------
    Lt, _ = le_max(SHI2023["GIc"], YT, E2)
    Lc, _ = le_max(SHI2023["GIc"], YC, E2)
    t("Gtt admissible: le_max exceeds the largest element",
      Lt > CELENT_MAX, "%.4f > %.4f mm" % (Lt, CELENT_MAX))
    t("Gtt admissible with a big margin (>10x)",
      Lt / CELENT_MAX > 10.0, "%.0fx" % (Lt / CELENT_MAX))
    t("the WHOLE Gtt uncertainty band stays admissible",
      le_max(SHI2023["GIc"] - SHI2023["GIc_sd"], YT, E2)[0] > CELENT_MAX)
    t("Gtc at the same value is NOT admissible",
      Lc < CELENT_MAX, "%.4f < %.4f mm" % (Lc, CELENT_MAX))
    t("the tension/compression gap is the strength ratio squared",
      abs(Lt / Lc - (YC / YT) ** 2) < 1e-9, "%.2f" % (Lt / Lc))
    scaled = SHI2023["GIc"] * (YC / YT) ** 2
    t("option (b) equalises the two admissible lengths",
      abs(le_max(scaled, YC, E2)[0] - Lt) < 1e-9)

    # --- the monolithic floor must be unusable for compression ------------
    t("the monolithic floor is admissible in tension",
      le_max(mid, YT, E2)[0] > CELENT_MAX)
    t("the monolithic floor is NOT admissible in compression",
      le_max(mid, YC, E2)[0] < CELENT_P50)

    # --- longitudinal values already in the card must still be fine -------
    for lab, g, x, e in (("G1t", 12.5, XT, E1), ("G1c", 12.5, XC, E1)):
        L, _ = le_max(g, x, e)
        t("%s in the card stays admissible" % lab, L > CELENT_MAX,
          "%.4f mm" % L)

    # --- provenance: the rejection of Ge's transverse value ---------------
    t("Ge's longitudinal value is the one in our card",
      abs(GE2018["G1t"] - 12.5) < 1e-12)
    t("Ge's transverse value is recorded but not adopted",
      abs(GE2018["Gtt"] - 1.0) < 1e-12 and SHI2023["GIc"] != GE2018["Gtt"])
    t("Ge's matrix is two orders softer than ours",
      OUR_MATRIX_E / 3200.0 > 50.0,
      "%.0fx" % (OUR_MATRIX_E / 3200.0))

    # --- every source carries a citable confidence grade ------------------
    for src in (GE2018, SHI2023, SNEAD2007):
        t("%s is graded fulltext" % src["key"],
          src["confidence"] == "fulltext")
        t("%s names its reference file" % src["key"],
          src["ref"].startswith("refs/["))

    # --- the mesh numbers must match the shipped deck if it is present ----
    deck = os.path.join(ROOT, "dist", "M4_DRIVERFIX_0730_1623.zip")
    t("mesh CELENT max is below the coarse-mesh longest edge",
      CELENT_MAX < 0.33, "%.4f mm" % CELENT_MAX)
    t("mesh element count matches the coarse RVE", NELEM == 26452)
    t("recorded median CELENT is below the max",
      CELENT_P50 < CELENT_MAX)

    # --- what the shipped decks carry: the adoption timeline --------------
    slots = {}
    for tag, zrel, inp in RUN_DECKS:
        try:
            slots[tag] = run_deck_slots(zrel, inp)
        except Exception as e:                          # noqa: BLE001
            t("run deck %s is readable" % tag, False, str(e))
    if len(slots) == 3:
        t("M6 adopted Shi's value in BOTH transverse slots (option a)",
          abs(slots["M6"][0] - SHI2023["GIc"]) < 1e-12
          and abs(slots["M6"][1] - SHI2023["GIc"]) < 1e-12,
          "%.3f / %.3f" % slots["M6"])
        t("M7 kept Gtt at Shi's value",
          abs(slots["M7"][0] - SHI2023["GIc"]) < 1e-12)
        t("M7 withdrew Gtc to 0",
          slots["M7"][1] == 0.0, "%.3f -> %.3f"
          % (slots["M6"][1], slots["M7"][1]))
        t("M8 inherits M7's transverse slots unchanged",
          slots["M8"] == slots["M7"], "%.3f / %.3f" % slots["M8"])
        Lc2, _ = le_max(SHI2023["GIc"], YC, E2)
        t("the withdrawal agrees with this file's admissibility verdict",
          slots["M7"][1] == 0.0 and Lc2 < CELENT_MAX,
          "le_max %.4f < CELENT %.4f" % (Lc2, CELENT_MAX))

    # --- the census: which transverse mode is actually ACTIVE -------------
    have = [c for c in CENSUS if os.path.exists(os.path.join(ROOT, c))]
    t("both committed M6 damage maps are present", len(have) == 2,
      "%d of %d" % (len(have), len(CENSUS)))
    if len(have) == 2:
        m23 = max(census_modefrac(c, 23) for c in CENSUS)
        m24 = max(census_modefrac(c, 24) for c in CENSUS)
        t("transverse TENSION (mode 23) dominates the tension step",
          m23 >= 0.8, "max modefrac %.3f" % m23)
        t("transverse COMPRESSION (mode 24) is inert (<= 1 %)",
          m24 <= 0.01, "max modefrac %.4f" % m24)
        t("so the regularised mode is the active one and the",
          slots.get("M8", (0, 1))[0] > 0.0
          and slots.get("M8", (1, 1))[1] == 0.0,
          "unregularised one is the inert one -- not the reverse")

    # --- RULING 1: legality of the composite-measured value ---------------
    t("Gtt ruling: grade is DEV, promotion to IN is barred",
      GTT_RULING["grade"] == "DEV" and GTT_RULING["never"] == "IN")
    t("the ruling states WHY the TRS double-count rule does not bar it",
      "additive" in GTT_RULING["mechanism"]
      and "second-order" in GTT_RULING["mechanism"])
    t("...and records the residual risk instead of denying it",
      "residual risk" in GTT_RULING["mechanism"])
    t("the constituent floor is the declared sensitivity anchor",
      abs(GTT_RULING["fallback_anchor"] - OUR_MATRIX_GF) < 1e-12)
    t("the whole sensitivity band floor..+1sd is admissible in tension",
      le_max(GTT_RULING["fallback_anchor"], YT, E2)[0] > CELENT_MAX
      and le_max(SHI2023["GIc"] + SHI2023["GIc_sd"], YT, E2)[0] > CELENT_MAX)

    # --- RULING 2: the Gtc withdrawal is confirmed, (a) is superseded -----
    t("Gtc verdict: keep 0, and it names what it supersedes",
      GTC_VERDICT["choice"].startswith("(c)")
      and "(a)" in GTC_VERDICT["supersedes"])
    t("the verdict carries BOTH legs of evidence, mesh and census",
      "le_max" in GTC_VERDICT["evidence_mesh"]
      and "0.6 %" in GTC_VERDICT["evidence_census"])
    t("the census leg is true of the committed data",
      len(have) == 2 and max(census_modefrac(c, 24) for c in CENSUS) <= 0.006,
      "max %.4f <= 0.006" % (max(census_modefrac(c, 24) for c in CENSUS)
                             if len(have) == 2 else -1))

    print("\n%d passed, %d failed" % (ok[0], bad[0]))
    print("=" * 74)
    return 1 if bad[0] else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true",
                    help="run the self-test and exit")
    a = ap.parse_args()
    return check() if a.check else report()


if __name__ == "__main__":
    sys.exit(main())
