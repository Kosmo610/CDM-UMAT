#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digitize_ref28_fig17.py
=======================
Read the thermal residual stress of 2D C/SiC straight out of refs/[28] Fig. 17(a).

WHY THIS FILE EXISTS SEPARATELY FROM digitize.py
------------------------------------------------
`digitize.py` renders pages with pdftoppm (poppler).  refs/[28] stores its
figures as embedded JPEGs, so they can be pulled out of the PDF byte stream
directly -- no poppler, no rasterisation, and no resampling loss.  This file
does that, and is therefore runnable wherever Python + PIL are.

WHAT IS BEING READ
------------------
Li, Jiao, Wang, Yang & Wang, *Damage characteristics and constitutive modeling
of the 2D C/SiC composite: Part I -- Experiment and analysis*,
Chinese Journal of Aeronautics 27(6) (2014) 1586-1597, doi:10.1016/j.cja.2014.10.026

Section 3.3, of the on-axis tension-compression test:

    "the hysteresis loops approximately intersect at O'(sigma_r, eps_r), and
     sigma_r and eps_r are generally considered to be the THERMAL RESIDUAL
     STRESS AND STRAIN in the as-received material"

O' is marked on Fig. 17(a) by a dashed box whose other corner is the origin O.
The paper never prints the numbers, so they have to come off the figure.

Material: 2D C/SiC, CVI, T-300 plain weave -- the same architecture and process
as this thesis.  This is therefore the only same-architecture measurement
available to compare against the RVE cool-down result.

THE INDEPENDENT CHECK (the rule digitize.py enforces)
-----------------------------------------------------
A digitization is only defensible if something the paper states IN WORDS,
away from the figure, reproduces it.  Here that is Table 1.

If O' really is the stress-free origin, then the material is elastic along
O'->O, so the secant modulus between them must equal the measured initial
modulus.  Table 1 gives E0 = 142.06 +- 13.69 GPa (tension) and
144.87 +- 1.35 GPa (compression).  The secant computed from the digitized
O' has to land there.  It does, to about 6 %.

That check ties the axis calibration to a printed table.  Get the calibration
wrong and the secant misses by the same factor.

    python3 data/literature/digitize_ref28_fig17.py
    python3 data/literature/digitize_ref28_fig17.py --check    # non-zero on failure
"""
from __future__ import print_function

import os
import re
import sys
import zlib

try:
    from PIL import Image
    import numpy as np
except ImportError:                                            # pragma: no cover
    sys.stderr.write("needs pillow and numpy:  pip install pillow numpy\n")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PDF = os.path.join(REPO, "refs", "[28] Part 1.pdf")

# Fig. 17 is the only 3-panel figure at this aspect ratio in the file.
FIG17_SIZE = (1810, 494)

# --- what Table 1 says, in print, independently of any figure ----------------
E0_TENSION_GPA = (142.06, 13.69)
E0_COMPRESSION_GPA = (144.87, 1.35)
SECANT_TOLERANCE = 0.10          # secant must be within 10 % of E0(compression)


# ----------------------------------------------------------------- extraction
def extract_figure(pdf_path, want_size):
    """Pull the embedded JPEG of the given pixel size out of the PDF."""
    with open(pdf_path, "rb") as fh:
        blob = fh.read()

    for m in re.finditer(rb"/Subtype\s*/Image", blob):
        start = blob.find(b"stream", m.start())
        if start < 0:
            continue
        header = blob[max(0, m.start() - 400):start]
        if b"DCTDecode" not in header:
            continue
        w = re.search(rb"/Width\s+(\d+)", header)
        h = re.search(rb"/Height\s+(\d+)", header)
        if not (w and h):
            continue
        if (int(w.group(1)), int(h.group(1))) != want_size:
            continue
        pos = start + len(b"stream")
        while blob[pos:pos + 1] in (b"\r", b"\n"):
            pos += 1
        data = blob[pos:blob.find(b"endstream", pos)]
        if data.startswith(b"\xff\xd8"):                        # JPEG SOI
            return data
    raise RuntimeError("Fig. 17 (%dx%d) not found in %s" % (want_size + (pdf_path,)))


# ---------------------------------------------------------------- calibration
def _runs_from(seq):
    n = 0
    for v in seq:
        if not v:
            break
        n += 1
    return n


def _cluster(values, gap=3):
    values = sorted(values)
    out, cur = [], [values[0]]
    for v in values[1:]:
        if v - cur[-1] <= gap:
            cur.append(v)
        else:
            out.append(cur)
            cur = [v]
    out.append(cur)
    return [float(np.mean(g)) for g in out]


def locate_frame(dark):
    """The plot box: the rows/columns that are dark across most of the panel."""
    h, w = dark.shape
    rows = np.where(dark.sum(axis=1) > 0.55 * w)[0]
    cols = np.where(dark.sum(axis=0) > 0.55 * h)[0]
    r = _cluster(rows)
    c = _cluster(cols)
    if len(r) < 2 or len(c) < 2:
        raise RuntimeError("could not find the plot frame")
    return c[0], c[-1], r[0], r[-1]          # left, right, top, bottom


def locate_ticks(dark, frame):
    """Inward tick marks on the left and bottom spines."""
    left, right, top, bottom = (int(round(v)) for v in frame)
    yrows = [r for r in range(top + 3, bottom - 2)
             if _runs_from(dark[r, left + 1:left + 15]) >= 4]
    xcols = [c for c in range(left + 3, right - 2)
             if _runs_from(dark[bottom - 1:bottom - 15:-1, c]) >= 4]
    return _cluster(yrows), _cluster(xcols)


# ------------------------------------------------------------------- the read
def digitize():
    jpeg = extract_figure(PDF, FIG17_SIZE)
    tmp = os.path.join(HERE, "_ref28_fig17.jpg")
    with open(tmp, "wb") as fh:
        fh.write(jpeg)
    try:
        grey = np.array(Image.open(tmp).convert("L"))
    finally:
        os.remove(tmp)

    panel = grey[:, :int(grey.shape[1] * 0.36)]        # (a) theta = 0 deg
    dark = (panel < 128).astype(np.uint8)

    left, right, top, bottom = locate_frame(dark)
    yticks, xticks = locate_ticks(dark, (left, right, top, bottom))

    # y: labelled 250 .. -150 in steps of 50.  250 sits on the frame top,
    #    -150 on the last detected tick.
    row_250, row_m150 = top, yticks[-1]
    # x: labelled -0.1 .. 0.5 in steps of 0.1.  The detected ticks are
    #    -0.1, 0, 0.1, 0.2, 0.3, 0.4 (0.5 coincides with the frame right edge).
    col_eps0, col_eps01 = xticks[1], xticks[2]

    def to_sigma(row):
        return 250.0 + (row - row_250) * (-400.0) / (row_m150 - row_250)

    def to_eps(col):
        return (col - col_eps0) * 0.1 / (col_eps01 - col_eps0)

    # The dashed box round O'.  Two clean bands, chosen to miss the curves:
    #   vertical   leg  -- rows 230..300, well below O and left of the loops
    #   horizontal leg  -- cols 168..207, below where the loops have climbed
    vband = dark[230:300, 135:180]
    vcols = vband.sum(axis=0)
    vsel = [135 + i for i, v in enumerate(vcols) if v >= 0.6 * vcols.max()]

    hband = dark[300:335, 168:207]
    hrows = hband.sum(axis=1)
    hsel = [300 + i for i, v in enumerate(hrows) if v >= 0.6 * hrows.max()]

    eps_r = to_eps(float(np.mean(vsel)))
    sigma_r = to_sigma(float(np.mean(hsel)))

    return {
        "frame": (left, right, top, bottom),
        "sigma_zero_row_check": to_sigma(yticks[len(yticks) // 2]),
        "eps_r_pct": eps_r,
        "sigma_r_MPa": sigma_r,
        "secant_GPa": (-sigma_r * 1e6) / (-eps_r / 100.0) / 1e9,
    }


# ---------------------------------------------------------------------- main
def main(argv):
    check = "--check" in argv
    r = digitize()

    print("refs/[28] Fig. 17(a)  --  2D C/SiC, CVI, T-300 plain weave, on-axis")
    print("  plot frame            left=%.1f right=%.1f top=%.1f bottom=%.1f" % r["frame"])
    print()
    print("  eps_r  = %+.4f %%" % r["eps_r_pct"])
    print("  sigma_r= %+.1f MPa      <- thermal residual stress, as-received"
          % r["sigma_r_MPa"])
    print()
    print("  CHECK  secant O'->O    = %.1f GPa" % r["secant_GPa"])
    print("         Table 1  E0(t)  = %.2f +- %.2f GPa" % E0_TENSION_GPA)
    print("         Table 1  E0(c)  = %.2f +- %.2f GPa" % E0_COMPRESSION_GPA)

    ref = E0_COMPRESSION_GPA[0]
    dev = abs(r["secant_GPa"] - ref) / ref
    ok = dev <= SECANT_TOLERANCE
    print("         deviation       = %.1f %%  (tolerance %.0f %%)  %s"
          % (100 * dev, 100 * SECANT_TOLERANCE, "PASS" if ok else "FAIL"))

    zero = r["sigma_zero_row_check"]
    zero_ok = abs(zero) < 3.0
    print("         sigma=0 gridline reads %.2f MPa  %s"
          % (zero, "PASS" if zero_ok else "FAIL"))
    print()
    print("  NOTE  This is a COMPOSITE-level axial value.  It is NOT comparable")
    print("        term-by-term with the 268 MPa MATRIX-phase tensile TRS from")
    print("        the RVE cool-down, nor with the XRD matrix value in refs/[15]")
    print("        -- different phase, opposite sign convention.  See")
    print("        docs/REFS_CANDIDATES.md 4.7.")

    if check and not (ok and zero_ok):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
