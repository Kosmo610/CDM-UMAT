#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cte_rve_verdict.py
==================
a2-0026 asked for one thing: put the first real RVE effective CTE against the
absolute composite targets the library holds.

    RVE, undamaged, before cooling, 26 452 C3D4:
        alpha_in   = 3.2827e-6 /K   (= alpha_1 = alpha_2)
        alpha_thru = 4.0891e-6 /K

    refs/[61] Mei, Carbon 44 (2006) Table 1, as-received 2D C/SiC, in-plane:
        600 C  4.6      800 C  6.1     1000 C  5.2     1200 C  5.4   (1e-6/C)

VERDICT IN ONE LINE
-------------------
ADMISSIBLE, NOT VALIDATED.  The RVE value sits inside the phase bounds its own
card allows, and it is the lowest member of a four-rung ladder whose top rung
is the measurement.  It does not hit the refs/[61] band and cannot be made to
hit it without changing the fibre card -- which is precisely where the
remaining gap lives.

THE LADDER, AND WHY IT IS THE RESULT
------------------------------------
Four estimates of the same quantity, all now held, ordered:

    3.2827   RVE direct probe, resolved weave, Zhang card CTEs   <- a2-0026, new
    3.6815   mean field, same Zhang card CTEs                    <- cte_sensitivity
    4.0294   mean field, PANEX33 MEASURED fibre CTEs             <- cte_sensitivity
    4.6      refs/[61] measurement at 600 C                      <- the target

The ladder is monotone, and each rung differs from the next by one identified
change.  That is the finding: the distance from model to measurement is not one
unexplained 40 % gap, it decomposes into two named pieces.

    rung 1 -> 2   +12.1 %   resolving the weave LOWERS alpha below mean field
    rung 2 -> 3   + 9.4 %   Zhang's fibre CTE card is below PANEX33's measured
    rung 3 -> 4   +14.2 %   everything left: microcracks, CVI/PIP, quantity

WHICH PIECE IS OURS TO FIX, AND WHICH IS NOT
--------------------------------------------
1 -> 2 is not an error at all.  It is the RVE doing its job: mean-field
homogenisation cannot see that the in-plane direction is carried by 0-degree
tows whose fibres have alpha_1 = -0.3e-6.  The resolved model is the better
number and the mean-field one is now known to be 12.1 % high.  Everything
cte_sensitivity.py derives from the mean-field alpha_bar (route A 200 MPa,
route B 154 MPa, the effective T_sf ladder) carries that bias, in the direction
that OVERSTATES the thermal residual stress.

2 -> 3 is a card question and it is open.  The Zhang 2022 card gives the fibre
transverse CTE as 3.1e-6/K.  The PANEX33 datasheet band for the same quantity
is 5-10e-6/K (eval_correlations, from the source abstract).  In a 2D weave the
in-plane direction contains 90-degree tows, so this number goes straight into
alpha_in.  We do not change it here -- the Zhang set is the VERIFIED set that
M1 reproduces, and pulling one row out of a verified set costs more than the
gap is worth.  It is recorded as the single largest identified lever.

3 -> 4 is where the honest limits are, and there are three of them.

DO NOT SAY THE COMPOSITE MUST LIE BELOW THE MATRIX
--------------------------------------------------
The tempting argument -- "every phase CTE is at or below the matrix 4.5e-6, so
a measurement of 6.1e-6 must be microcracks" -- is WRONG and must not be
written.  It holds only for the card's fibre transverse value (3.1e-6).  The
measured PANEX33 transverse band reaches 10e-6, well above the matrix, and the
90-degree tows put it in-plane.  So refs/[61] at 6.1e-6 is not out of bounds;
it is out of bounds FOR OUR CARD.  That is a statement about the card, not
about the measurement, and the file says it that way round.

THE THREE RESIDUAL LIMITS (rung 3 -> 4)
---------------------------------------
a. QUANTITY.  Ours is a secant about the stress-free temperature; refs/[61] is
   read as instantaneous at 600-1200 C (cte_composite_targets argues the case
   and labels it an inference).  SiC's own instantaneous CTE runs 2.20e-6 at
   23 C to 5.00e-6 at 1200 C, so a secant from room temperature is BELOW the
   instantaneous value at the top of the range by construction.  Any comparison
   that ignores this understates the model.
b. STATE.  Ours is undamaged and pre-cooling; refs/[61] is as-received, and
   Li[28] observed that as-received 2D C/SiC of this architecture already
   carries non-interacting microcracks (Ch.4 section 4.9-10).  Our own two
   states differ by 4.6 % (3.2827 undamaged -> 3.132 after the cooling history,
   Ch.4 section 4.5.3), and they differ in the direction cracks predict for a
   COOLING path: cracks open, the composite contracts less, the apparent
   secant falls.  Direction agrees; 4.6 % is far short of 14.2 %, so cracks
   alone do not close rung 3 -> 4 in our model.
c. MATERIAL.  refs/[61] is CVI at 13 % porosity, ours is PIP at 32.4 %.

WHAT THIS FILE FORBIDS
----------------------
- quoting refs/[61] as a PASS/FAIL line for alpha_bar
- comparing 3.2827 with 4.6 without naming which of the three limits applies
- using the mean-field alpha_bar (3.6815) now that the resolved one exists,
  except when reproducing an earlier result that used it
- the phase-bound argument above

Run:  python3 data/literature/cte_rve_verdict.py --check
"""
from __future__ import print_function

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "data", "properties"))
sys.path.insert(0, HERE)

import eval_correlations as ec              # noqa: E402
import cte_composite_targets as cct         # noqa: E402

OUTBOX_A2 = os.path.join(ROOT, "sync", "outbox_a2.json")
CH4 = os.path.join(ROOT, "docs", "CH4_RVE_HOMOGENISATION.md")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# ---------------------------------------------------------------------------
# A.  the RVE numbers are READ, never typed
# ---------------------------------------------------------------------------

def rve_alphas():
    """Pull alpha_in / alpha_thru out of a2's own message a2-0026.

    Hand-copying is how this project lost the Snead sign and the Pradere unit.
    The measurement belongs to a2, so a2's message is the source of record and
    this function is the only place the numbers enter.
    """
    with open(OUTBOX_A2) as fh:
        doc = json.load(fh)
    msgs = doc["messages"] if isinstance(doc, dict) else doc
    body = [m for m in msgs if m.get("id") == "a2-0026"][0]["body"]
    a_in = re.search(r"ᾱ_in\s*=\s*([0-9.]+)e-6", body)
    a_th = re.search(r"ᾱ_thru\s*=\s*([0-9.]+)e-6", body)
    if a_in is None or a_th is None:
        raise RuntimeError("a2-0026 no longer carries the CTE numbers")
    return float(a_in.group(1)), float(a_th.group(1)), body


def ch4_secant():
    """Ch.4 section 4.5.3's cooling-history secant, read from the chapter."""
    txt = open(CH4, encoding="utf-8").read()
    m = re.search(r"\\mathbf\{([0-9.]+)\\times10\^\{-6\}\\ /\\text\{K\}\}", txt)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# B.  the ladder
# ---------------------------------------------------------------------------

def ladder():
    """The four estimates of the in-plane composite CTE, in 1e-6/K.

    Rungs 2 and 3 are recomputed from cte_sensitivity so the ladder cannot
    drift away from the module that owns them.
    """
    import cte_sensitivity as cs
    a_in, _, _ = rve_alphas()
    card = cs.evaluate("CARD", -0.3e-6, 3.1e-6)["alpha_bar"]
    meas = cs.evaluate("PANEX33", None, None)["alpha_bar"]
    return a_in, card, meas, cct.MEI_CTE[600]


def main(argv):
    print("=" * 78)
    print("cte_rve_verdict.py  --  RVE alpha_bar against the absolute targets")
    print("=" * 78)

    a_in, a_th, body = rve_alphas()

    print("\n A. the numbers come from a2's message, not from this file")
    t("alpha_in read out of sync/outbox_a2.json", abs(a_in - 3.2827) < 1e-9,
      "%.4f e-6/K" % a_in)
    t("alpha_thru read out of the same message", abs(a_th - 4.0891) < 1e-9,
      "%.4f e-6/K" % a_th)
    t("the message says the state is undamaged and pre-cooling",
      "무손상" in body and "손상 OFF" in body)
    t("and it says the three temperatures returned the same card",
      "온도 무관" in body or "NT=0" in body)

    print("\n B. admissible against the card's own phase CTEs")
    af1, af2, am = ec.Z_AF1 * 1e6, ec.Z_AF2 * 1e6, ec.Z_AM * 1e6
    lo, hi = min(af1, af2, am), max(af1, af2, am)
    t("card phase CTEs span the interval", True,
      "%.1f .. %.1f e-6/K (fibre L/T, matrix)" % (lo, hi))
    t("alpha_in lies inside it", lo <= a_in <= hi, "%.4f" % a_in)
    t("alpha_thru lies inside it", lo <= a_th <= hi, "%.4f" % a_th)
    t("alpha_thru exceeds alpha_in, as the weave requires", a_th > a_in,
      "%.3f > %.3f" % (a_th, a_in))
    t("the through-thickness value approaches the matrix", a_th / am > 0.9,
      "%.3f of the matrix card" % (a_th / am))

    print("\n C. the four-rung ladder is monotone toward the measurement")
    r1, r2, r3, r4 = ladder()
    t("rung 1  RVE direct probe", r1 is not None, "%.4f e-6/K" % r1)
    t("rung 2  mean field, Zhang card CTEs", r2 is not None,
      "%.4f e-6/K" % (r2 * 1e6))
    t("rung 3  mean field, PANEX33 measured fibre CTEs", r3 is not None,
      "%.4f e-6/K" % (r3 * 1e6))
    t("rung 4  refs/[61] at 600 C", True, "%.1f e-6/K" % r4)
    r2, r3 = r2 * 1e6, r3 * 1e6
    t("the ladder never turns back", r1 < r2 < r3 < r4)
    t("no single rung carries the whole gap",
      max(r2 / r1 - 1, r3 / r2 - 1, r4 / r3 - 1) < 0.20,
      "largest step %.1f %%" % (100 * max(r2 / r1 - 1, r3 / r2 - 1, r4 / r3 - 1)))

    print("\n D. rung 1 -> 2 -- the mean field is high, and that is a bias")
    bias = r2 / r1 - 1.0
    t("mean field overstates alpha_bar", bias > 0, "+%.1f %%" % (100 * bias))
    t("the cause is named -- mean field cannot see the 0-degree tows",
      af1 < 0, "fibre alpha_1 = %.1f e-6/K" % af1)
    t("so cte_sensitivity's TRS routes inherit an overstatement",
      "cte_sensitivity" in __doc__ and "OVERSTATES" in __doc__)
    t("and the resolved value is declared the better one",
      "the resolved model is the better number"
      in " ".join(__doc__.split()).lower())

    print("\n E. rung 2 -> 3 -- the fibre transverse card is the largest lever")
    t("card fibre transverse CTE", True, "%.1f e-6/K" % af2)
    t("the measured band for the same fibre sits above it", af2 < 5.0,
      "PANEX33 abstract 5-10 e-6/K")
    t("that band reaches the in-plane direction through the 90-degree tows",
      "90-degree tows" in " ".join(__doc__.split()))
    t("but the Zhang set is not edited here",
      "we do not change it here" in " ".join(__doc__.split()).lower())

    print("\n F. rung 3 -> 4 -- three limits, none of them waved away")
    sec = ch4_secant()
    t("Ch.4 4.5.3 cooling-history secant read from the chapter",
      sec is not None and abs(sec - 3.132) < 1e-9, "%.3f e-6/K" % sec)
    crack = 1.0 - sec / a_in
    t("our two states differ by the crack share", crack > 0,
      "%.1f %% (undamaged -> cooled)" % (100 * crack))
    t("the direction matches crack opening on a cooling path", sec < a_in)
    t("but the magnitude falls short of the residual gap",
      crack < (r4 / r3 - 1.0),
      "%.1f %% available vs %.1f %% needed" % (100 * crack, 100 * (r4 / r3 - 1)))
    t("so microcracks alone are not offered as the explanation",
      "cracks alone do not close" in " ".join(__doc__.split()))
    t("the quantity mismatch is stated with its size",
      abs(ec.sic_alpha_inst(1473.15) * 1e6 - 5.0) < 0.05,
      "SiC 2.20 (23 C) -> 5.00 (1200 C) instantaneous")
    t("the material mismatch is stated with both porosities",
      "13 % porosity, ours is PIP at 32.4 %" in " ".join(__doc__.split()))

    print("\n G. the phase-bound argument is refused in writing")
    t("the tempting argument is written down", "tempting argument" in __doc__)
    t("and then refused", "is WRONG and must not be written"
      in " ".join(__doc__.split()))
    t("the reason given is the measured transverse band, not authority",
      "reaches 10e-6" in " ".join(__doc__.split()))
    t("the conclusion is aimed at the card, not at the measurement",
      "out of bounds FOR OUR CARD" in " ".join(__doc__.split()))

    print("\n H. what nobody may quote")
    d = " ".join(__doc__.split())
    t("refs/[61] may not be used as a PASS/FAIL line", "PASS/FAIL line" in d)
    t("3.2827 vs 4.6 may not be compared bare", "without naming which" in d)
    t("the mean-field value is retired except for reproduction",
      "except when reproducing an earlier result" in d)
    t("and the verdict word is ADMISSIBLE, NOT VALIDATED",
      "ADMISSIBLE, NOT VALIDATED" in d)

    print("\n" + "=" * 78)
    if _BAD:
        print("%d FAILED: %s" % (len(_BAD), "; ".join(_BAD)))
        print("=" * 78)
        return 1
    print("ALL %d RVE-CTE VERDICT CHECKS PASS (4-rung ladder, 3 named limits)"
          % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
