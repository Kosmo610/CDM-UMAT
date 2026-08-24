#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
card_pipeline_rehearsal.py -- walk the macro card across every seam, now
=======================================================================
    python3 verification/card_pipeline_rehearsal.py --check

Stage 8 (the 9-case matrix) begins with one hand-off:

    RVE odbs -> homogenize.macro_card() -> <prefix>_macro_card.inp
             -> make_macro_thermalshock.py --card -> 9 decks
             -> matrix_audit.audit()

Every piece of that chain has its own selftest.  None of them had ever been
run END TO END, because the chain needs a card and a card needs RVE odbs that
do not exist yet.  That is the wrong reason to leave a seam untested: the
seams are exactly where a selftest cannot look, and this one opens on the day
the RVE campaign finishes -- the most expensive possible moment to discover
that the two halves disagree.

So the rehearsal builds the card from the M6 curves that ARE committed
(data/results/M6/*_ss.csv, three temperatures, real solver output) and walks
it the whole way.  The elastic off-axis terms and the CTEs are placeholders
and this file says so loudly; what is real is the PATH, and the three
findings below came out of walking it on 2026-08-18:

  1. none of the three M6 curves may legally supply a fracture energy, and
     the pipeline shipped all three anyway.  RT23 peaks at its last point --
     it softened 0.0 % -- yet split_fracture_energy() returned a positive
     "dissipated" part (pre-peak nonlinearity alone makes it positive) and
     check_macro_card() accepted the negated result as a measurement.
  2. the macro card's damage ceiling was 0.99 while every RVE card, and
     postprocess/damage_map.py, use 0.90.
  3. homogenize.py called np.trapz, removed in NumPy 2.0.

The first is the one that mattered.  Fixed at source in postprocess/
homogenize.py; this file holds the fixes down.
"""
from __future__ import print_function

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "postprocess"))
sys.path.insert(0, os.path.join(ROOT, "abaqus"))

import numpy as np                                            # noqa: E402
import homogenize as H                                        # noqa: E402
import make_macro_thermalshock as MT                          # noqa: E402
import matrix_audit as MA                                     # noqa: E402
from m6_report import ss_columns, initial_tangent             # noqa: E402

#: real solver output, committed, three temperatures
CURVE_DIR = os.path.join(ROOT, "data", "results", "M6")
CURVES = ((23.0, "LTH_M6_RT23_ss.csv"),
          (500.0, "LTH_M6_T500_ss.csv"),
          (1000.0, "LTH_M6_T1000_ss.csv"))

#: RVE in-plane edge -- the length homogenize.py extracts Gf at
L_RVE = 3.5

#: the macro mesh's real CELENT range, printed by make_macro_thermalshock.py
#: for the 40 x 10 x 3 mm plate at 20 x 6 x 12 with the 0.55 grading
LE_MACRO = (0.68, 0.94)

#: what walking the seam found on 2026-08-18, kept as numbers so a future
#: change to any of the three files has to explain itself here.  softened is
#: 1 - sigma_end/peak; prepeak is the share of the would-be Gf that lies
#: BEFORE the peak.
M6_EXPECTED = {
    23.0: dict(softened=0.000, prepeak=1.000, ships=False),
    500.0: dict(softened=0.003, prepeak=0.697, ships=False),
    1000.0: dict(softened=0.166, prepeak=0.216, ships=False),
}

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-64s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
def read_curve(path):
    """(eps, sig) by COLUMN NAME -- the same resolver the figure code uses."""
    lines = open(path).read().splitlines()
    ei, si = ss_columns(lines[0])
    eps, sig = [], []
    for ln in lines[1:]:
        c = ln.split(",")
        if len(c) <= max(ei, si):
            continue
        eps.append(float(c[ei]))
        sig.append(float(c[si]))
    return eps, sig


def curve_facts(eps, sig):
    """Everything the Gf gate needs, computed here independently of
    homogenize.py so the two can be compared rather than assumed equal."""
    peak = max(sig)
    ipk = sig.index(peak)
    E, _r2, _n = initial_tangent(eps, sig)
    g0 = peak * peak / (2.0 * E)
    area = float(np.trapezoid(sig, eps)) if hasattr(np, "trapezoid") \
        else float(np.trapz(sig, eps))
    pre = float(np.trapezoid(sig[:ipk + 1], eps[:ipk + 1])) \
        if hasattr(np, "trapezoid") else float(np.trapz(sig[:ipk + 1],
                                                        eps[:ipk + 1]))
    elastic = g0 * L_RVE
    inel = area * L_RVE - elastic
    return dict(peak=peak, E=E, g0=g0, Gf_total=area * L_RVE,
                Gf_pre=pre * L_RVE, elastic=elastic, inel=inel,
                softened=1.0 - sig[-1] / peak,
                prepeak=max(0.0, pre * L_RVE - elastic) / inel if inel > 0
                else 0.0)


def build_props():
    """props_by_T from the real curves.  Off-axis elasticity and alpha are
    PLACEHOLDERS -- the rehearsal tests the path, not the material."""
    props, facts = {}, {}
    for T, fn in CURVES:
        eps, sig = read_curve(os.path.join(CURVE_DIR, fn))
        f = curve_facts(eps, sig)
        facts[T] = f
        E, peak = f["E"], f["peak"]
        eng = dict(E1=E, E2=E, E3=0.45 * E, nu12=0.15, nu13=0.20, nu23=0.20,
                   G12=0.30 * E, G13=0.25 * E, G23=0.25 * E)
        st = {"Xt": peak, "Xc": 3.0 * peak, "Yt": peak, "Yc": 3.0 * peak,
              "S12": 0.5 * peak, "S13": 0.5 * peak, "S23": 0.5 * peak}
        for mode in ("1t", "1c", "2t", "2c"):
            # 1c/2c reuse the tensile curve's SHAPE against the compressive
            # strength, which is a placeholder like the rest -- but it keeps
            # all four crack-band slots exercised instead of only two.
            scale = 1.0 if mode.endswith("t") else 6.0
            st["Gf_" + mode] = f["Gf_total"] * scale
            st["Lchar_" + mode] = L_RVE
            st["soft_" + mode] = f["softened"]
            st["Gfpre_" + mode] = f["Gf_pre"] * scale
        H.split_fracture_energy(st, eng)
        props[T] = dict(elastic=eng, strength=st, alpha=np.array([2.0e-6] * 6))
    return props, facts


# --------------------------------------------------------------------------
def part_a(facts):
    print("\n A. the three real M6 curves, measured independently")
    print("      %-6s %8s %9s %9s %10s" %
          ("T", "peak", "softened", "pre-peak", "would-ship"))
    for T, _fn in CURVES:
        f = facts[T]
        print("      %-6g %8.2f %8.1f %% %8.1f %% %8.4g N/mm" %
              (T, f["peak"], 100 * f["softened"], 100 * f["prepeak"],
               f["inel"]))
    for T, _fn in CURVES:
        e, f = M6_EXPECTED[T], facts[T]
        t("T%-4g curve softened %.1f %% of peak" % (T, 100 * f["softened"]),
          abs(f["softened"] - e["softened"]) < 5.0e-3,
          "expected %.1f %%" % (100 * e["softened"]))
        t("  and %.0f %% of its would-be Gf is PRE-peak" % (100 * f["prepeak"]),
          abs(f["prepeak"] - e["prepeak"]) < 5.0e-3,
          "expected %.0f %%" % (100 * e["prepeak"]))
    t("RT23 peaks at its LAST point -- there is no softening branch at all",
      facts[23.0]["softened"] < 1.0e-9,
      "sigma_end / peak = 1.000000; a curve that stopped, not one that fell")
    t("  yet its 'dissipated' part is POSITIVE, which is the whole trap",
      facts[23.0]["inel"] > 0.0,
      "%.4g N/mm of pure pre-peak nonlinearity" % facts[23.0]["inel"])


def part_b(props):
    print("\n B. the gate refuses what it should refuse")
    for T, _fn in CURVES:
        st = props[T]["strength"]
        shipped = [m for m in ("1t", "1c", "2t", "2c")
                   if ("Gfin_" + m) in st]
        t("T%-4g ships no fracture energy" % T,
          shipped == M6_EXPECTED[T].get("shipped", []),
          "slots stay 0.0 -> KABAND uses the fixed exponent, declared "
          "rather than measured")
        t("  and the evidence is kept, not just the verdict" ,
          ("soft_1t" in st and "prepk_1t" in st),
          "soft = %.4f, prepk = %.4f" % (st.get("soft_1t", -1),
                                         st.get("prepk_1t", -1)))

    # The gate must PASS a curve that really softened, or it is just an
    # off switch.  Synthesise one: linear to peak at eps = 1e-3, then
    # exponential down.  The rise is sampled at 2e-5 so that the tangent
    # window (eps <= 1e-4) holds more than its five-point minimum.
    eps = [2.0e-5 * i for i in range(51)]
    sig = [100.0 * e / 1.0e-3 for e in eps]
    for i in range(1, 60):
        eps.append(1.0e-3 + 2.0e-4 * i)
        sig.append(100.0 * float(np.exp(-0.05 * i)))
    f = curve_facts(eps, sig)
    eng = dict(E1=100.0 / 1.0e-3, E2=100.0 / 1.0e-3)
    st = {"Xt": f["peak"], "Yt": f["peak"],
          "Gf_1t": f["Gf_total"], "Lchar_1t": L_RVE,
          "soft_1t": f["softened"], "Gfpre_1t": f["Gf_pre"]}
    H.split_fracture_energy(st, eng)
    t("a curve that DID soften passes the gate", "Gfin_1t" in st,
      "softened %.1f %%, pre-peak share %.1f %% -> Gf = %.4g N/mm"
      % (100 * f["softened"], 100 * f["prepeak"], st.get("Gfin_1t", 0.0)))
    t("  the thresholds are the documented ones, not ad hoc",
      abs(H.SOFT_MIN - 0.50) < 1e-12 and abs(H.PREPEAK_MAX - 0.50) < 1e-12,
      "SOFT_MIN = %.2f, PREPEAK_MAX = %.2f" % (H.SOFT_MIN, H.PREPEAK_MAX))
    # and the two conditions are independent: soften plenty but keep most of
    # the area pre-peak, and it must still be refused.
    st2 = dict(st)
    st2.pop("Gfin_1t", None)
    st2["Gfpre_1t"] = st["Gf_1t"] * 0.99
    H.split_fracture_energy(st2, eng)
    t("  a well-softened curve that is mostly PRE-peak is still refused",
      "Gfin_1t" not in st2,
      "the two conditions are independent, not one dressed as two")


def part_c(props):
    print("\n C. the card that comes out is one the deck generator accepts")
    temps = [T for T, _ in CURVES]
    card = H.macro_card(props, H.DEFAULT_CYC, temps, crit=H.DEFAULT_CRIT)
    try:
        info = MT.check_macro_card(card, "rehearsal", le=list(LE_MACRO))
        ok, err = True, ""
    except SystemExit as exc:
        info, ok, err = None, False, str(exc)
    t("check_macro_card accepts the homogenize.py card unchanged", ok,
      err.splitlines()[0] if err else
      "NPROPS = %d, NT = %d, Depvar = %d, criteria on"
      % (info["nprops"], info["nt"], info["ndepvar"]))
    if not ok:
        return card
    t("  NPROPS is 47 + 8*NT + 9, the criterion-block length",
      info["nprops"] == 47 + 8 * info["nt"] + 9,
      "%d slots" % info["nprops"])
    t("  every crack-band slot is off, because the gate refused all four",
      all(g["sign"] == "off" for g in info["gf"]),
      "a refused mode reaches the card as 0.0, not as a small number")

    print("\n D. the damage ceiling is ONE number across the two scales")
    props_list = info["props"]
    t("the macro card's dmax equals the RVE card's D_DMAX",
      abs(props_list[21] - H.MACRO_DMAX) < 1e-12
      and abs(props_list[22] - H.MACRO_DMAX) < 1e-12,
      "%.2f on both slots 22 and 23" % H.MACRO_DMAX)
    import retune_deck as RT
    t("  and that constant IS retune_deck.D_DMAX, not a copy of it",
      abs(H.MACRO_DMAX - RT.D_DMAX) < 1e-12,
      "0.99 here would have made every MACRO damage map misjudge its cap")
    try:
        import damage_map as DM
        t("  postprocess/damage_map.py reads the same ceiling",
          abs(DM.DMAX_CAP - H.MACRO_DMAX) < 1e-12,
          "damage_map is pointed at the MACRO jobs by RUN_MANIFEST.md")
    except Exception as exc:                                  # pragma: no cover
        t("  postprocess/damage_map.py reads the same ceiling", False, str(exc))
    return card


def part_e(card, props):
    print("\n E. the card survives the deck generator and the axis audit")
    d = tempfile.mkdtemp(prefix="card_rehearsal_")
    cpath = os.path.join(d, "REH_macro_card.inp")
    with open(cpath, "w") as f:
        f.write(card + "\n")
    epath = os.path.join(d, "REH_macro_expansion.inp")
    with open(epath, "w") as f:
        f.write(H.macro_expansion(props, [T for T, _ in CURVES]) + "\n")

    rc, out = MA.generate(d, ["--card", cpath, "--expansion", epath])
    t("make_macro_thermalshock.py --card runs on the real card", rc == 0,
      (out.strip().splitlines() or ["(no output)"])[-1] if rc else
      "9 mech + 3 heat decks")
    if rc != 0:
        return
    t("  and it no longer announces a placeholder card",
      "PLACEHOLDER macro card" not in out,
      "--card was actually consumed, not silently ignored")

    before = len(_BAD)
    MA.audit(d, t)
    t("the 9-case axis audit passes on decks built from a REAL card",
      len(_BAD) == before,
      "the card changes material numbers, never deck structure")


# --------------------------------------------------------------------------
def check():
    print("=" * 78)
    print("card_pipeline_rehearsal.py -- RVE curves -> macro card -> 9 decks")
    print("=" * 78)
    print("  NOTE: off-axis elastic terms and alpha are PLACEHOLDERS.  What "
          "is being\n        rehearsed is the PATH; only E1, the strengths "
          "and the Gf inputs are real.")
    props, facts = build_props()
    part_a(facts)
    part_b(props)
    card = part_c(props)
    part_e(card, props)


def main(argv):
    if "--check" in argv or "--selftest" in argv:
        check()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % ", ".join(n.strip() for n in _BAD[:3]))
            print("=" * 78)
            return 1
        print("ALL %d CARD-PIPELINE CHECKS PASS "
              "(the seam holds, and the Gf gate is closed)" % len(_OK))
        print("=" * 78)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
