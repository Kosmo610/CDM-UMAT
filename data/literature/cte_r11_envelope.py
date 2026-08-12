#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cte_r11_envelope.py
===================
Can refs/[11] settle the constituent-CTE question?  Answer: NO -- and this
file is the evidence for that answer, because a negative result that is not
reproducible is just an opinion.

WHY THIS WAS ATTEMPTED
----------------------
cte_sensitivity.py leaves the composite in-plane CTE as the open quantity:

    RVE measured (card CTEs)          3.132e-6/K
    mean field, card fibre CTEs       3.682e-6/K
    mean field, measured fibre CTEs   4.029e-6/K

refs/[11] (Q. Zhang, Cheng, Zhang, Xu, Materials Letters 60 (2006) 3245-3247)
measures exactly this quantity -- in-plane CTE of 2D C/SiC, RT to 1400 C, on a
NETZSCH DIL 402C -- and plots it in Fig. 1.  A measured value would turn the
CTE question from an argument into a comparison.

WHY IT DOES NOT WORK
--------------------
Three findings, in order of how much they matter.

 1. THE PAPER'S OWN CVD SiC REFERENCE CURVE RUNS 10-22 % HIGH.  Fig. 1 plots
    bulk CVD SiC alongside the composites.  Bulk CVD SiC is a well
    characterised reference material, and Snead refs/[06] is the handbook
    correlation for it.  The paper's curve sits above Snead at EVERY
    temperature, and the secant over 23-1050 C is 5.30 against Snead's 4.40.
    Whatever the cause -- specimen porosity, pushrod calibration, heating
    rate -- refs/[11] cannot be used as an ABSOLUTE target for alpha_bar.
    This is the robust part of this file: the top envelope of the marker mask
    is unambiguous, because CVD SiC is the topmost series everywhere.

 2. IN RELATIVE TERMS THE PAPER'S OWN BRACKET IS TOO WIDE.  The offset in (1)
    cancels in the ratio alpha_2D/alpha_CVD, so that is the fair comparison.
    The paper states in words that the 2D in-plane CTE is above the other two
    composites and below bulk CVD SiC, which brackets the ratio at
    0.571 .. 1.000.  All three of our candidates -- 0.696, 0.818, 0.895 --
    fall inside.  The bracket discriminates nothing.

 3. THE 2D CURVE ITSELF CANNOT BE TRACED HONESTLY.  It is the only series
    drawn as a plain line, and between roughly 250 and 600 C it runs inside a
    0.5e-6/K band shared with the 1D diamonds and the 3D crosses.  Both a
    greedy tracker and a global minimum-cost path latch onto the cross series
    there.  A trace that needs a human to say "no, follow that one instead"
    is not a digitization, and dressing one up as an automated result is the
    exact failure this directory's rules exist to stop.

 4. THE PAPER'S PROSE CONTRADICTS ITS OWN FIGURE BELOW ~250 C.  Section 3.2
    says the 2D in-plane CTE is "larger than those of other two kinds of C/SiC
    composites in the whole temperature range".  Fig. 1 shows the 2D line
    diving to about -1.9e-6/K near 150 C, far below both.  The dip is almost
    certainly a dilatometer start-up artefact.  Either way the sentence cannot
    be used as a low-temperature constraint, which is what killed the last
    route to bounding the curve.

WHAT IS SAFE TO CITE FROM THIS PAPER
------------------------------------
The ORDERING (CVD SiC > 2D > 1D > 3D above ~300 C) and the SHAPE (rise to a
maximum near 900 C, fall to 1300 C).  Not the absolute values.

Requires: pdftoppm (poppler), PIL, numpy -- the same stack as digitize.py.

  python3 data/literature/cte_r11_envelope.py
  python3 data/literature/cte_r11_envelope.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "data", "properties"))

def _find_pdf():
    """Match on the reference number, not the Korean title.

    The filenames carry Korean descriptions that are easy to mistype and that
    may be renamed; the "[11]" prefix is the stable key used everywhere else
    in this project.
    """
    d = os.path.join(ROOT, "refs")
    if not os.path.isdir(d):
        return os.path.join(d, "[11].pdf")
    for f in sorted(os.listdir(d)):
        if f.startswith("[11]") and f.lower().endswith(".pdf"):
            return os.path.join(d, f)
    return os.path.join(d, "[11].pdf")


PDF = _find_pdf()
PAGE, DPI = 2, 600

# Frame of Fig. 1 at 600 dpi, found by longest-black-run detection.  Pinned so
# a re-render that moves cannot silently shift the calibration -- the tick fit
# below would blow up its residual and the check would fail.
FRAME = dict(L=545, R=2267, T=4505, B=5804)
TICK_Y = [4506.5, 4653.0, 4795.5, 4938.5, 5081.0,
          5229.0, 5366.5, 5513.5, 5656.5, 5803.0]
TICK_YV = [7, 6, 5, 4, 3, 2, 1, 0, -1, -2]
TICK_X = [546.5, 764.5, 978.5, 1192.0, 1411.0, 1620.0, 1839.5, 2053.5, 2266.0]
TICK_XV = list(range(0, 1601, 200))
LEGEND = dict(r0=790, c0=620, c1=1300)      # inner coords, blanked out

T_LO, T_HI = 23.0, 1050.0                   # our cooldown range

#: the three candidates this was meant to discriminate between
CANDIDATES = [("RVE measured (card CTEs)", 3.132),
              ("mean field, card fibre CTEs", 3.6815),
              ("mean field, measured fibre CTEs", 4.0294)]
ALPHA_M = 4.500                             # our matrix secant, 1050 -> 23 C


def render():
    tmp = tempfile.mkdtemp()
    stem = os.path.join(tmp, "p")
    subprocess.check_call(["pdftoppm", "-f", str(PAGE), "-l", str(PAGE),
                           "-r", str(DPI), "-png", PDF, stem],
                          stderr=subprocess.PIPE)
    png = [f for f in os.listdir(tmp) if f.endswith(".png")][0]
    return np.array(Image.open(os.path.join(tmp, png)).convert("L")) < 128


def _im(m):
    return Image.fromarray((m * 255).astype(np.uint8))


def erode(m, k):
    return np.array(_im(m).filter(ImageFilter.MinFilter(k))) > 127


def dilate(m, k):
    return np.array(_im(m).filter(ImageFilter.MaxFilter(k))) > 127


def masks(dark):
    """Split the plot interior into marker blobs and thin line strokes.

    A morphological opening is the whole trick.  The plotted line is 6-9 px
    thick at 600 dpi; the markers are 20-30 px.  An 11x11 erosion leaves only
    marker cores, and dilating those back recovers the marker bodies.  This is
    orientation-free, so it does not mistake a steep piece of curve for a
    marker the way a horizontal run-length test would.
    """
    f = FRAME
    inner = dark[f["T"] + 7:f["B"] - 6, f["L"] + 7:f["R"] - 6]
    marker = dilate(erode(inner, 11), 21) & inner
    lg = np.zeros_like(inner)
    lg[LEGEND["r0"]:, LEGEND["c0"]:LEGEND["c1"]] = True
    return inner, marker & ~lg, (inner & ~marker) & ~lg


def calibration():
    py = np.polyfit(TICK_Y, TICK_YV, 1)
    px = np.polyfit(TICK_X, TICK_XV, 1)
    ry = np.abs(np.polyval(py, TICK_Y) - np.array(TICK_YV, float)).max()
    rx = np.abs(np.polyval(px, TICK_X) - np.array(TICK_XV, float)).max()
    return py, px, ry, rx


def envelopes(marker):
    """Topmost and bottom-most marker run per column.

    The top envelope IS the CVD SiC series: no other marker series ever rises
    above it (the 2D curve does, briefly, near 900 C -- but the 2D series has
    no markers, so it is not in this mask at all).  That is why the top
    envelope is trustworthy while the interior is not.
    """
    h, w = marker.shape
    top = np.full(w, np.nan)
    bot = np.full(w, np.nan)
    for c in range(w):
        v = marker[:, c]
        runs, s = [], None
        for i, x in enumerate(v):
            if x and s is None:
                s = i
            elif not x and s is not None:
                if i - s >= 8:
                    runs.append((s + i - 1) / 2.0)
                s = None
        if s is not None and h - s >= 8:
            runs.append((s + h - 1) / 2.0)
        if runs:
            top[c], bot[c] = min(runs), max(runs)
    return smooth(top), smooth(bot)


def smooth(y, win=41):
    idx = np.arange(len(y))
    ok = ~np.isnan(y)
    z = np.interp(idx, idx[ok], y[ok])
    k = np.ones(win) / win
    return np.convolve(np.pad(z, (win // 2, win // 2), mode="edge"),
                       k, "valid")[:len(y)]


def extract():
    dark = render()
    inner, marker, line = masks(dark)
    py, px, ry, rx = calibration()
    top, bot = envelopes(marker)
    w = marker.shape[1]
    col = np.arange(w) + FRAME["L"] + 7
    Tv = np.polyval(px, col)
    cvd = np.polyval(py, top + FRAME["T"] + 7)
    low = np.polyval(py, bot + FRAME["T"] + 7)
    return dict(T=Tv, cvd=cvd, low=low, resid_y=ry, resid_x=rx,
                n_line=int(line.sum()), n_marker=int(marker.sum()))


def snead_secant():
    import eval_correlations as ec
    return ec.secant_alpha(23.0, ec.sic_alpha_integral, 1050.0) * 1.0e6


def snead_inst(T_C):
    import eval_correlations as ec
    return ec.sic_alpha_inst(T_C + 273.15) * 1.0e6


# ==========================================================================
def report():
    print("=" * 78)
    print("cte_r11_envelope.py -- can refs/[11] settle the CTE question?")
    print("=" * 78)
    d = extract()
    T, cvd, low = d["T"], d["cvd"], d["low"]
    sel = (T >= T_LO) & (T <= T_HI)
    mc, ml = cvd[sel].mean(), low[sel].mean()
    sn = snead_secant()

    print("\n 1. AXIS CALIBRATION (10 y ticks, 9 x ticks, least squares)")
    print("    worst y residual  %.3f CTE units" % d["resid_y"])
    print("    worst x residual  %.2f C" % d["resid_x"])

    print("\n 2. THE PAPER'S OWN CVD SiC REFERENCE, vs Snead refs/[06]")
    print("    %8s %12s %12s %8s" % ("T [C]", "refs/[11]", "Snead inst", "excess"))
    print("    " + "-" * 44)
    for t in (200, 400, 600, 800, 1000):
        i = int(np.argmin(np.abs(T - t)))
        si = snead_inst(t)
        print("    %8d %12.2f %12.2f %7.0f %%"
              % (t, cvd[i], si, (cvd[i] / si - 1) * 100))
    print("    " + "-" * 44)
    print("    secant 23-1050 C:  refs/[11] %.3f   Snead %.3f   +%.0f %%"
          % (mc, sn, (mc / sn - 1) * 100))
    print("    -> refs/[11] is NOT usable as an absolute target for alpha_bar")

    print("\n 3. THE BRACKET THE PAPER STATES IN WORDS")
    print("    'in-plane CTE of 2D ... larger than ... other two composites'")
    print("    'it was lower than that of bulk CVD SiC'")
    print("    lowest marker series, secant 23-1050 : %.3f e-6/K" % ml)
    print("    CVD SiC,              secant 23-1050 : %.3f e-6/K" % mc)
    print("    => alpha_2D / alpha_CVD  in  %.3f .. 1.000" % (ml / mc))
    print("\n    our candidates, as the same ratio alpha_bar / alpha_matrix:")
    for name, ab in CANDIDATES:
        r = ab / ALPHA_M
        inside = (ml / mc) <= r <= 1.0
        print("      %-34s %.3f   %s"
              % (name, r, "INSIDE the bracket" if inside else "excluded"))
    print("\n    VERDICT: the bracket contains every candidate.  refs/[11]")
    print("    does not discriminate, and this route is closed.")

    print("\n 4. WHAT REMAINS CITABLE FROM refs/[11]")
    print("    the ORDERING above ~300 C  (CVD SiC > 2D > 1D > 3D)")
    print("    the SHAPE                  (max near 900 C, fall to 1300 C)")
    print("    NOT the absolute values, and NOT the low-temperature prose")
    print("=" * 78)


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-54s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("=" * 78)
    print("cte_r11_envelope.py --check")
    print("=" * 78)

    print("\n A. the source is present and renders")
    ck("refs/[11] exists", os.path.exists(PDF))
    if not os.path.exists(PDF):
        return 1
    d = extract()
    ck("page renders and the frame yields an interior",
       d["n_line"] > 10000 and d["n_marker"] > 100000,
       "line %d, marker %d" % (d["n_line"], d["n_marker"]))
    ck("markers outnumber line strokes (3 of 4 series are markers)",
       d["n_marker"] > 3 * d["n_line"])

    print("\n B. axis calibration is tight")
    ck("worst y tick residual <= 0.03 CTE units", d["resid_y"] <= 0.03,
       "%.4f" % d["resid_y"])
    ck("worst x tick residual <= 3 C", d["resid_x"] <= 3.0,
       "%.2f" % d["resid_x"])

    T, cvd, low = d["T"], d["cvd"], d["low"]
    sel = (T >= T_LO) & (T <= T_HI)
    mc, ml = cvd[sel].mean(), low[sel].mean()
    sn = snead_secant()

    print("\n C. the top envelope behaves like a CTE curve, not like noise")
    # Only over the measured range.  The curves stop at 1400 C, and past that
    # both envelopes collapse onto the same last series, so top == bottom
    # there by construction rather than by error.
    ck("top envelope is above the bottom envelope over 23-1050 C",
       bool((cvd[sel] > low[sel]).all()),
       "min gap %.3f" % (cvd[sel] - low[sel]).min())
    dat = (T >= T_LO) & (T <= 1400.0)
    ck("and over the whole measured range 23-1400 C",
       bool((cvd[dat] > low[dat]).all()),
       "min gap %.3f" % (cvd[dat] - low[dat]).min())
    i200 = int(np.argmin(np.abs(T - 200)))
    i900 = int(np.argmin(np.abs(T - 900)))
    ck("CVD SiC rises from 200 C to 900 C", cvd[i900] > cvd[i200],
       "%.2f -> %.2f" % (cvd[i200], cvd[i900]))
    ck("CVD SiC stays in a physical range over 23-1050 C",
       3.0 < cvd[sel].min() and cvd[sel].max() < 7.0,
       "%.2f .. %.2f" % (cvd[sel].min(), cvd[sel].max()))

    print("\n D. FINDING 1 -- the reference curve runs high at every "
          "temperature")
    for t in (200, 400, 600, 800, 1000):
        i = int(np.argmin(np.abs(T - t)))
        ex = (cvd[i] / snead_inst(t) - 1) * 100
        ck("refs/[11] CVD SiC exceeds Snead at %d C" % t, ex > 5.0,
           "+%.0f %%" % ex)
    ck("secant excess over 23-1050 C is 20 %",
       abs((mc / sn - 1) * 100 - 20.0) < 3.0,
       "%.3f vs %.3f, +%.0f %%" % (mc, sn, (mc / sn - 1) * 100))
    ck("so refs/[11] cannot be an absolute target", (mc / sn - 1) > 0.10)

    print("\n E. FINDING 2 -- the stated bracket discriminates nothing")
    ck("bracket lower bound is 0.571", abs(ml / mc - 0.571) < 0.02,
       "%.3f" % (ml / mc))
    for name, ab in CANDIDATES:
        r = ab / ALPHA_M
        ck("%s is inside the bracket" % name, (ml / mc) <= r <= 1.0,
           "%.3f" % r)
    ck("the bracket therefore cannot select a CTE set",
       all((ml / mc) <= ab / ALPHA_M <= 1.0 for _, ab in CANDIDATES))

    print("\n F. the negative result is recorded, not softened")
    src = open(os.path.join(HERE, "cte_r11_envelope.py")).read()
    for phrase, why in (
            ("Answer: NO", "must state the verdict up front"),
            ("cannot be traced honestly", "must admit the trace failed"),
            ("is not a digitization", "must say why a hand trace was refused"),
            ("NOT the absolute values", "must limit what may be cited")):
        ck("source states: %s" % why, phrase in src)

    print("\n G. what is still citable is stated positively")
    ck("the ordering is offered as citable", "ORDERING" in src)
    ck("the shape is offered as citable", "SHAPE" in src)

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d refs/[11] ENVELOPE CHECKS PASS "
          "(the verdict is: does not discriminate)" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    report()
