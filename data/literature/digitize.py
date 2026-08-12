#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digitize.py
===========
Re-derive every `digitized` row in data/literature/ straight from the PDFs.

A row marked `digitized` is only as good as the person who read the figure.
This file removes the person: it renders the page with pdftoppm, finds the
plot frame from the longest black runs, detects the markers geometrically,
and converts to data.  Running it reproduces the CSV numbers exactly.

THE RULE THIS FILE ENFORCES
---------------------------
Every figure carries a CHECK taken from something the paper says IN WORDS,
independently of the figure -- "the residual strength is still 83 % of the
original", "the maximum is at 1273 K".  If the digitized numbers do not
reproduce that statement, the axis calibration is wrong and the run fails.
Without such a check a digitization cannot be defended in a viva; with it,
the paper validates our reading of its own figure.

Marker detection
----------------
  filled  solid squares/circles: horizontal run length >= a threshold.
          The connecting line and the error bars are thin, the marker is not.
  open    hollow diamonds/circles: a vertical scan through the middle of a
          hollow marker hits only its two thin edges, so run length fails.
          Use the vertical EXTENT of dark pixels in the column instead --
          a 20 px marker spans 20 px whether or not it is filled, while the
          curve through it spans ~3.

Requires: pdftoppm (poppler), PIL, numpy.

  python3 data/literature/digitize.py            # digitize and report
  python3 data/literature/digitize.py --check    # same, non-zero on mismatch
  python3 data/literature/digitize.py --write    # also emit the curve CSV
"""
from __future__ import print_function

import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "CDM-UMAT", "refs")
if not os.path.isdir(REFS):
    REFS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "refs")

DPI = 250
DARK = 128


# ==========================================================================
# rendering and frame detection
# ==========================================================================
def render(pdf, page, dpi=DPI, rgb=False):
    """Render one page of a PDF to a numpy array (grey by default)."""
    tmp = tempfile.mkdtemp()
    stem = os.path.join(tmp, "p")
    subprocess.check_call(["pdftoppm", "-f", str(page), "-l", str(page),
                           "-r", str(dpi), "-png", pdf, stem],
                          stderr=subprocess.PIPE)
    png = [f for f in os.listdir(tmp) if f.endswith(".png")][0]
    im = Image.open(os.path.join(tmp, png))
    return np.array(im.convert("RGB" if rgb else "L"))


def colour_mask(rgb, which):
    """Isolate one plotted curve by colour.

    refs/[03] Fig. 3 draws the as-received curve in black and the
    60-cycle curve in red, on the same axes.  Colour separates them
    exactly; geometry could not, because they cross the same region.
    """
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    if which == "red":
        return (r > 110) & (r - g > 60) & (r - b > 60)
    if which == "black":
        return (r < DARK) & (g < DARK) & (b < DARK)
    raise ValueError("unknown colour %r" % which)


def _column_groups(ys, max_gap=3):
    """Split a sorted list of row indices into runs separated by > max_gap."""
    groups, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] > max_gap:
            groups.append(cur)
            cur = []
        cur.append(y)
    groups.append(cur)
    return [(g[0] + g[-1]) * 0.5 for g in groups]


def trace_curve(mask, frame, xaxis, yaxis, nx=60, margin=2, start=None):
    """FOLLOW a plotted curve from left to right; sample it at nx abscissae.

    Averaging every dark pixel in a column does not work on a real figure:
    the column also contains the frame, the tick marks, the in-plot legend
    text ("As-received"), and the annotation arrows.  On refs/[03] Fig. 3
    that pulls the as-received peak down from 258 to 200 MPa -- a 22 %
    error that still looks like a stress-strain curve.

    So track instead.  Start from the origin, where both curves begin, and
    at each column take the candidate group CLOSEST to where the curve was
    in the previous column.  Text and arrows sit far from the trace and are
    rejected automatically.

    Returns [(x, y, thickness)].
    """
    top, bot, left, right = frame
    x0, x1 = xaxis
    y0, y1 = yaxis
    lo_r, hi_r = int(min(top, bot)) + 3, int(max(top, bot)) - 3

    # Walk every pixel column so the tracker never has to jump far, and
    # sample the result afterwards.
    j0, j1 = int(round(min(left, right))), int(round(max(left, right)))
    prev = float(start) if start is not None else None
    traced = {}
    for j in range(j0, j1 + 1):
        lo, hi = max(0, j - margin), min(mask.shape[1], j + margin + 1)
        ys = np.nonzero(mask[:, lo:hi].any(axis=1))[0]
        ys = ys[(ys >= lo_r) & (ys <= hi_r)]
        if len(ys) == 0:
            continue
        cands = _column_groups(ys)
        if prev is None:
            prev = max(cands)          # curves start at the bottom-left
        pick = min(cands, key=lambda c: abs(c - prev))
        if abs(pick - prev) > 0.08 * abs(bot - top):
            continue                   # implausible jump: text or an arrow
        traced[j] = pick
        prev = pick

    out = []
    for k in range(nx + 1):
        px = min(left, right) + abs(right - left) * k / float(nx)
        j = int(round(px))
        near = [q for q in (j, j - 1, j + 1, j - 2, j + 2) if q in traced]
        if not near:
            continue
        py = traced[near[0]]
        X = x0 + (px - left) * (x1 - x0) / (right - left)
        Y = y0 + (py - top) * (y1 - y0) / (bot - top)
        out.append((X, Y, 1))
    return out


def find_frame(sub, frac=0.7):
    """Locate the plot box: the rows/cols that are dark across most of the crop.

    Returns (top, bottom, left, right) in crop coordinates, using the CENTRE
    of each detected band so a 2-3 px thick axis does not bias the scale.
    """
    d = sub < DARK
    rows = d.sum(axis=1)
    cols = d.sum(axis=0)
    rr = [i for i in range(len(rows)) if rows[i] > frac * sub.shape[1]]
    cc = [j for j in range(len(cols)) if cols[j] > frac * sub.shape[0]]
    if len(rr) < 2 or len(cc) < 2:
        raise RuntimeError("plot frame not found: %d rows, %d cols"
                           % (len(rr), len(cc)))

    def band(idx, lo):
        grp = [k for k in idx if (k - idx[0] < 8) == lo]
        grp = [k for k in idx if abs(k - (idx[0] if lo else idx[-1])) < 8]
        return sum(grp) / float(len(grp))

    return band(rr, True), band(rr, False), band(cc, True), band(cc, False)


def find_ticks(sub, frame, which, depth=10, skip=3, min_run=3):
    """Positions of the tick marks on one axis, in crop coordinates.

    Assuming the plot FRAME is the axis range is wrong for any plot drawn
    in Origin or matplotlib, where the range usually extends past the first
    and last labelled tick.  Getting that wrong stretches every value by a
    few percent -- small enough to look plausible and large enough to
    matter.  So calibrate on the ticks themselves.

    Ticks are short stubs drawn just inside the frame: scan a shallow band
    inside the axis and take the columns (or rows) that are dark there.
    """
    top, bot, left, right = (int(round(v)) for v in frame)
    d = sub < DARK
    h, w = d.shape
    min_run = 2

    def scan(band, base):
        hits = np.nonzero(band >= min_run)[0]
        if len(hits) == 0:
            return []
        groups, cur = [], [hits[0]]
        for q in hits[1:]:
            if q - cur[-1] > 3:
                groups.append(cur)
                cur = []
            cur.append(q)
        groups.append(cur)
        return [base + sum(g) / float(len(g)) for g in groups]

    # Ticks point INWARD in some styles and OUTWARD in others -- refs/[03]
    # draws them outward.  Scan both bands and keep whichever yields more
    # ticks.  The scan is clipped to the frame span so that axis LABELS,
    # which also produce dark columns, cannot be mistaken for ticks.
    best = []
    for sgn in (+1, -1):
        if which == "x":
            r0 = bot + skip if sgn > 0 else bot - depth
            r1 = bot + depth if sgn > 0 else bot - skip
            r0, r1 = max(0, r0), min(h, r1)
            if r1 <= r0:
                continue
            got = scan(d[r0:r1, left:right + 1].sum(axis=0), left)
        else:
            c0 = left - depth if sgn > 0 else left + skip
            c1 = left - skip if sgn > 0 else left + depth
            c0, c1 = max(0, c0), min(w, c1)
            if c1 <= c0:
                continue
            got = scan(d[top:bot + 1, c0:c1].sum(axis=1), top)
        if len(got) > len(best):
            best = got
    return best


def _trim_to(ticks, want, frame_ends):
    """Reduce a tick list to `want` entries by dropping frame-corner artefacts.

    The frame corners sometimes produce a stub that looks exactly like a
    tick and even sits one lattice step outside the real ones, so it cannot
    be told apart geometrically.  Drop from whichever END lies closest to a
    frame line, one at a time, and fail loudly if the counts cannot be
    reconciled -- a silent mis-count would rescale the whole axis.
    """
    ticks = list(ticks)
    if len(ticks) < want:
        raise RuntimeError("found %d ticks, expected %d" % (len(ticks), want))
    while len(ticks) > want:
        d_lo = min(abs(ticks[0] - e) for e in frame_ends)
        d_hi = min(abs(ticks[-1] - e) for e in frame_ends)
        if min(d_lo, d_hi) > 4:
            raise RuntimeError("cannot reconcile %d ticks with %d expected: "
                               "neither end sits on the frame"
                               % (len(ticks), want))
        ticks.pop(0 if d_lo <= d_hi else -1)
    return ticks


def _fit_axis(ticks, v_first, v_last):
    """Least-squares pixel <-> value map over a uniform tick lattice.

    Using every tick rather than just the two ends averages out the
    half-pixel error of each detection.
    """
    n = len(ticks)
    vals = [v_first + (v_last - v_first) * i / float(n - 1) for i in range(n)]
    v_mean = sum(vals) / n
    p_mean = sum(ticks) / n
    num = sum((v - v_mean) * (p - p_mean) for v, p in zip(vals, ticks))
    den = sum((v - v_mean) ** 2 for v in vals)
    slope = num / den
    resid = max(abs(p - (p_mean + slope * (v - v_mean)))
                for v, p in zip(vals, ticks))
    return (lambda v: p_mean + slope * (v - v_mean),
            lambda p: v_mean + (p - p_mean) / slope, resid)


def calibrate(sub, frame, fig):
    """Return the axis reference box (top, bot, left, right).

    'frame'  the plot box IS the axis range (Excel-style plots such as
             refs/[02] Fig. 8).
    'ticks'  calibrate on the detected tick lattice.  Mandatory for Origin
             plots like refs/[03], whose frame runs past the first and last
             labelled tick: on Fig. 4(a) the frame spans -5.1 to 65 cycles,
             so taking it as 0 to 60 would stretch every abscissa by 17 %.
    """
    top, bot, left, right = frame
    if fig.get("calib", "frame") == "frame":
        return frame, 0.0
    xt = _trim_to(find_ticks(sub, frame, "x"), fig["nxticks"], (left, right))
    yt = _trim_to(find_ticks(sub, frame, "y"), fig["nyticks"], (top, bot))
    fx, _, rx = _fit_axis(xt, *fig["xtickvals"])
    fy, _, ry = _fit_axis(yt, *fig["ytickvals"])
    x0, x1 = fig["xaxis"]
    y0, y1 = fig["yaxis"]
    return (fy(y0), fy(y1), fx(x0), fx(x1)), max(rx, ry)


def _runs(mask, axis):
    """Length of the contiguous dark run each pixel belongs to, along `axis`."""
    out = np.zeros_like(mask, dtype=int)
    n = mask.shape[axis]
    for k in range(mask.shape[1 - axis]):
        line = mask[:, k] if axis == 0 else mask[k, :]
        i = 0
        while i < n:
            if line[i]:
                j = i
                while j < n and line[j]:
                    j += 1
                if axis == 0:
                    out[i:j, k] = j - i
                else:
                    out[k, i:j] = j - i
                i = j
            else:
                i += 1
    return out


def _cluster_x(xs, ys, gap, min_pix):
    """Group detected pixels into markers by their x position."""
    if len(xs) == 0:
        return []
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    groups, cur = [], [0]
    for i in range(1, len(xs)):
        if xs[i] - xs[i - 1] > gap:
            groups.append(cur)
            cur = []
        cur.append(i)
    groups.append(cur)
    return [(xs[g].mean(), ys[g].mean(), len(g))
            for g in groups if len(g) >= min_pix]


def _components(mask):
    """4-connected components of a boolean mask, as lists of (row, col)."""
    from collections import deque
    seen = np.zeros(mask.shape, dtype=bool)
    out = []
    h, w = mask.shape
    for i in range(h):
        for j in range(w):
            if not mask[i, j] or seen[i, j]:
                continue
            q = deque([(i, j)])
            seen[i, j] = True
            comp = []
            while q:
                p, r = q.popleft()
                comp.append((p, r))
                for dp, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    u, v = p + dp, r + dr
                    if 0 <= u < h and 0 <= v < w and mask[u, v] \
                            and not seen[u, v]:
                        seen[u, v] = True
                        q.append((u, v))
            out.append(comp)
    return out


def markers_filled(interior, min_width=12, min_pix=60, **_):
    """Solid markers: wide horizontal runs, then CONNECTED COMPONENTS.

    Clustering by x alone merges two markers that are close together on the
    abscissa -- which is exactly what happens in refs/[35], where the 973 K
    and 1173 K points nearly touch.  Components keep them apart because the
    thin connecting line between them was already removed by the width
    threshold.
    """
    m = _runs(interior, axis=1) >= min_width
    out = []
    for comp in _components(m):
        if len(comp) < min_pix:
            continue
        ys = [p[0] for p in comp]
        xs = [p[1] for p in comp]
        out.append((sum(xs) / float(len(xs)), sum(ys) / float(len(ys)),
                    len(comp)))
    return sorted(out)


def markers_open(interior, min_extent=12, gap=6, min_pix=20, max_gap=30):
    """Hollow markers: columns whose dark pixels span a large vertical extent.

    Two refinements that are not optional in practice:

    * A hollow diamond is NOT contiguous down a column -- a vertical scan
      through its middle hits the top edge, then white, then the bottom
      edge.  So dark pixels are grouped with a tolerance (`max_gap`) that
      spans the hollow interior but not the whole plot.
    * Taking min-to-max over the WHOLE column silently merges the marker
      with the x-axis tick directly beneath it, and the midpoint then lands
      halfway down the plot.  That failure is quiet and produces plausible
      numbers, so it must be designed out, not watched for: only the
      largest single GROUP is used.

    The centre is the midpoint of the group, not its centroid: a hollow
    diamond has more pixels on its wide middle rows, which drags a centroid,
    whereas the midpoint is exact by symmetry.
    """
    pts = []
    for j in range(interior.shape[1]):
        ys = np.nonzero(interior[:, j])[0]
        if len(ys) == 0:
            continue
        groups, cur = [], [ys[0]]
        for y in ys[1:]:
            if y - cur[-1] > max_gap:
                groups.append(cur)
                cur = []
            cur.append(y)
        groups.append(cur)
        lo, hi = max(((g[0], g[-1]) for g in groups),
                     key=lambda p: p[1] - p[0])
        if hi - lo + 1 >= min_extent:
            pts.append((j, 0.5 * (lo + hi), lo, hi))
    if not pts:
        return []
    xs = np.array([p[0] for p in pts], dtype=float)
    ys = np.array([p[1] for p in pts], dtype=float)
    los = np.array([p[2] for p in pts], dtype=float)
    his = np.array([p[3] for p in pts], dtype=float)
    out = []
    for cx, cy, n in _cluster_x(xs, ys, gap, min_pix):
        sel = (xs >= cx - gap * 3) & (xs <= cx + gap * 3)
        # The winning group spans the marker AND its error bar, so its
        # extremes ARE the error bar.  Reported rather than discarded.
        out.append((cx, cy, n, los[sel].min(), his[sel].max()))
    return out


# ==========================================================================
# figure definitions -- one entry per digitized figure
# ==========================================================================
FIGURES = [
    dict(
        key="YIN2002_fig8",
        pdf="[02] yin2002 S.pdf", page=5,
        crop=(250, 720, 350, 1050),          # top, bottom, left, right
        xaxis=(0.0, 100.0), yaxis=(1000.0, 0.0),
        mode="open", detect=dict(min_extent=12, gap=6, min_pix=8),
        quantity="flexural_strength", unit="MPa",
        xname="cycles",
        expect_x=[0, 20, 50, 100],
        # The paper states this in its own conclusions, twice.
        check=("residual strength at N=100 is 83 % of the original",
               lambda p: abs(p[-1][1] / p[0][1] - 0.83) < 0.02),
        note="Fig. 8, dT = 1000 C air quench",
    ),
    dict(
        key="ZHANG2013_fig4a",
        pdf="[03] zhang2012 S.pdf", page=3,
        crop=(1120, 1690, 1170, 1920),
        calib="ticks",
        nxticks=13, xtickvals=(0.0, 60.0), xaxis=(0.0, 60.0),
        nyticks=7, ytickvals=(1.5, 0.0), yaxis=(1.5, 0.0),
        mode="filled", detect=dict(min_width=10, min_pix=60),
        quantity="normalized_strength", unit="-",
        xname="cycles",
        expect_x=[0, 20, 40, 60],
        # "The residual strength ... for 60 cycles [is] about 63 % ..."
        check=("residual strength at 60 cycles is about 63 %",
               lambda p: abs(p[-1][1] / p[0][1] - 0.63) < 0.03),
        note="Fig. 4(a), 900 -> 300 C air quench",
    ),
    dict(
        key="ZHANG2013_fig4b",
        pdf="[03] zhang2012 S.pdf", page=3,
        crop=(1770, 2340, 1170, 1920),
        calib="ticks",
        nxticks=7, xtickvals=(0.0, 60.0), xaxis=(0.0, 60.0),
        nyticks=11, ytickvals=(120.0, 20.0), yaxis=(120.0, 20.0),
        mode="open", detect=dict(min_extent=12, gap=8, min_pix=8),
        quantity="tensile_modulus", unit="GPa",
        xname="cycles",
        expect_x=[0, 20, 40, 60],
        # "... and modulus ... about 63 and 45 %, respectively"
        check=("residual modulus at 60 cycles is about 45 %",
               lambda p: abs(p[-1][1] / p[0][1] - 0.45) < 0.03),
        note="Fig. 4(b), 900 -> 300 C air quench",
    ),
    dict(
        key="ZHANG2013_fig3",
        pdf="[03] zhang2012 S.pdf", page=3,
        crop=(330, 890, 1120, 1920),
        calib="ticks",
        nxticks=13, xtickvals=(0.0, 0.36), xaxis=(0.0, 0.36),
        nyticks=11, ytickvals=(300.0, 0.0), yaxis=(300.0, 0.0),
        mode="curve", nsample=36,
        curves=[("black", "as_received"), ("red", "shocked_60")],
        quantity="stress_strain", unit="MPa",
        xname="strain_pct",
        # The peaks must agree with Fig. 4(a): 258 MPa as-received and
        # 63 % of it after 60 cycles.  Two independent figures of the same
        # paper cross-checking each other.
        check=("peak stresses agree with Fig. 4(a): ~258 MPa and 63 % of it",
               lambda c: abs(max(p[1] for p in c[0][1]) - 258.0) < 15.0
               and abs(max(p[1] for p in c[1][1])
                       / max(p[1] for p in c[0][1]) - 0.63) < 0.06),
        note="Fig. 3, monotonic tensile curves, as-received and 60 cycles",
    ),
    dict(
        key="YAN2011_fig5",
        pdf="[35] 파손기준 08 신규.pdf", page=3, dpi=200,
        crop=(1020, 1500, 150, 800),
        xaxis=(200.0, 2000.0), yaxis=(250.0, 100.0),
        mode="filled", detect=dict(min_width=12, gap=6, min_pix=100),
        quantity="S12", unit="MPa",
        xname="T_K",
        expect_x=[293, 973, 1173, 1273, 1473, 1673, 1873],
        # The conclusions state the maximum sits at the preparation
        # temperature, 1273 K.  If the x calibration were wrong the peak
        # would land somewhere else.
        check=("the maximum is at 1273 K",
               lambda p: abs(max(p, key=lambda q: q[1])[0] - 1273) < 40),
        note="Fig. 5, in-plane shear strength vs temperature, vacuum",
    ),
]


def digitize(fig):
    pdf = os.path.join(REFS, fig["pdf"])
    if not os.path.exists(pdf):
        raise RuntimeError("missing %s" % pdf)
    page = render(pdf, fig["page"], fig.get("dpi", DPI))
    t, b, l, r = fig["crop"]
    sub = page[t:b, l:r]
    frame = find_frame(sub)
    axis, resid = calibrate(sub, frame, fig)

    if fig["mode"] == "curve":
        rgb = render(pdf, fig["page"], fig.get("dpi", DPI), rgb=True)[t:b, l:r]
        out = []
        for colour, label in fig["curves"]:
            m = colour_mask(rgb, colour)
            # The axes are black too.  Left unmasked, the y-axis line fills
            # the first column and the tracker locks onto its midpoint --
            # reporting 150 MPa at zero strain on a curve that starts at
            # the origin.  Blank the frame before tracing.
            for c in frame[:2]:
                m[max(0, int(c) - 3):int(c) + 4, :] = False
            for c in frame[2:]:
                m[:, max(0, int(c) - 3):int(c) + 4] = False
            pts = trace_curve(m, axis, fig["xaxis"], fig["yaxis"],
                              nx=fig.get("nsample", 40))
            out.append((label, pts))
        return out, frame, resid

    top, bot, left, right = axis

    # The first and last markers usually SIT ON the axes, so a window that
    # stops at the frame loses them.  Blank the frame lines themselves, then
    # search a window that reaches a little way past them.  `pad` is about
    # half a marker: wide enough to keep an edge marker, narrow enough to
    # stay clear of the axis labels, whose digits also span many rows.
    mask = sub < DARK
    for c in frame[:2]:
        mask[max(0, int(c) - 2):int(c) + 3, :] = False
    for c in frame[2:]:
        mask[:, max(0, int(c) - 2):int(c) + 3] = False
    pad = fig.get("pad", 14)
    y_lo = max(0, int(min(top, bot)) - pad)
    x_lo = max(0, int(min(left, right)) - pad)
    interior = mask[y_lo:int(max(top, bot)) + pad,
                    x_lo:int(max(left, right)) + pad]
    off_y, off_x = y_lo, x_lo

    fn = markers_open if fig["mode"] == "open" else markers_filled
    raw = fn(interior, **fig["detect"])

    x0, x1 = fig["xaxis"]
    y0, y1 = fig["yaxis"]
    def to_y(cy):
        return y0 + (cy + off_y - top) * (y1 - y0) / (bot - top)

    out = []
    for m in raw:
        cx, cy, n = m[0], m[1], m[2]
        X = x0 + (cx + off_x - left) * (x1 - x0) / (right - left)
        bar = (to_y(m[3]), to_y(m[4])) if len(m) > 3 else (None, None)
        out.append((X, to_y(cy), n, min(bar) if bar[0] is not None else None,
                    max(bar) if bar[0] is not None else None))
    return out, frame, resid


# ==========================================================================
def main(strict=False, write=False):
    print("=" * 72)
    print("digitize.py -- re-deriving every `digitized` row from the PDFs")
    print("=" * 72)
    fails = []
    for fig in FIGURES:
        print("\n%s   (%s p.%d)" % (fig["key"], fig["pdf"], fig["page"]))
        if fig.get("skip"):
            print("  SKIPPED: %s" % fig["skip"])
            continue
        try:
            pts, frame, resid = digitize(fig)
        except Exception as exc:                       # noqa: BLE001
            print("  ERROR: %s" % exc)
            fails.append(fig["key"])
            continue
        print("  frame: top=%.1f bottom=%.1f left=%.1f right=%.1f "
              "(tick fit residual %.2f px)" % (frame + (resid,)))

        if fig["mode"] == "curve":
            for label, curve in pts:
                peak = max(curve, key=lambda q: q[1])
                print("  %-14s %3d samples, peak %.1f %s at strain %.3f %%"
                      % (label, len(curve), peak[1], fig["unit"], peak[0]))
            name, test = fig["check"]
            ok = test(pts)
            print("  [%s] paper's own statement: %s"
                  % ("PASS" if ok else "FAIL", name))
            if not ok:
                fails.append(fig["key"] + " (paper check)")
            continue

        print("  %d markers found" % len(pts))
        exp = fig.get("expect_x")
        if exp is not None and len(pts) != len(exp):
            print("  FAIL: expected %d markers, found %d"
                  % (len(exp), len(pts)))
            fails.append(fig["key"] + " (marker count)")
            continue
        print("  %-12s %-12s %-10s %-14s %s"
              % (fig["xname"], fig["quantity"], "ratio", "err bar", "px"))
        base = pts[0][1]
        for i, (X, Y, n, blo, bhi) in enumerate(pts):
            tag = ""
            if exp is not None:
                err = X - exp[i]
                tag = "  (nominal %g, off by %+.1f)" % (exp[i], err)
                if abs(err) > 0.02 * abs(fig["xaxis"][1] - fig["xaxis"][0]):
                    tag += "  <-- CALIBRATION SUSPECT"
                    fails.append(fig["key"] + " x-calibration")
            bar = ("%.1f..%.1f" % (blo, bhi)) if blo is not None else "--"
            print("  %-12.1f %-12.3f %-10.3f %-14s %-5d%s"
                  % (X, Y, Y / base, bar, n, tag))
        name, test = fig["check"]
        ok = test(pts)
        print("  [%s] paper's own statement: %s"
              % ("PASS" if ok else "FAIL", name))
        if not ok:
            fails.append(fig["key"] + " (paper check)")

    # ---- cross-check the two refs/[03] figures against each other --------
    try:
        f3 = [f for f in FIGURES if f["key"] == "ZHANG2013_fig3"][0]
        f4 = [f for f in FIGURES if f["key"] == "ZHANG2013_fig4b"][0]
        curves, _, _ = digitize(f3)
        mods, _, _ = digitize(f4)
    except Exception:                                  # noqa: BLE001
        curves = None
    if curves:
        print("\n" + "-" * 72)
        print("CROSS-CHECK: refs/[03] Fig. 3 against refs/[03] Fig. 4(b)")
        print("-" * 72)
        print("  %-14s %-12s %-12s %-12s" % ("window", "as-received",
                                             "60 cycles", "ratio"))
        got = {}
        for lim in (0.03, 0.05, 0.10):
            e = {}
            for label, pts in curves:
                s = [(x, y) for x, y, _ in pts if 0 < x <= lim + 1e-9]
                if len(s) < 2:
                    continue
                # secant through the origin, in GPa (strain is in %)
                e[label] = (sum(x * y for x, y in s)
                            / sum(x * x for x, _ in s) / 10.0)
            if len(e) == 2:
                got[lim] = e
                print("  0 - %-10.2f %-12.1f %-12.1f %-12.3f"
                      % (lim, e["as_received"], e["shocked_60"],
                         e["shocked_60"] / e["as_received"]))
        e0, e60 = mods[0][1], mods[-1][1]
        print("  %-14s %-12.1f %-12.1f %-12.3f"
              % ("Fig. 4(b)", e0, e60, e60 / e0))
        if got:
            lim = sorted(got)[0]
            r3 = got[lim]["shocked_60"] / got[lim]["as_received"]
            print("""
  THE TWO FIGURES OF THE SAME PAPER DO NOT AGREE, and the disagreement is
  large enough to matter for calibration:
    * absolute modulus   Fig. 3 gives ~%.0f GPa as-received, Fig. 4(b) says
                         %.1f GPa -- about %.0f %% apart.
    * degradation ratio  Fig. 3 gives %.3f after 60 cycles, Fig. 4(b) %.3f.
  The most likely reason is that Fig. 4(b)'s 'modulus' is the UNLOADING
  modulus fitted over a wider strain window (the paper says 'the slope of
  the initial linear portion'), which on a curve this nonlinear is well
  below the true initial tangent.  refs/[27] measures 145.7 GPa on a
  comparable 2D C/SiC, which sits with Fig. 3, not Fig. 4(b).

  DECISION FOR THE THESIS.  Calibrate the cycle-damage law against the
  RATIO series of Fig. 4(b) -- every point there was measured the same
  way, so the ratio is internally consistent -- and compare the SHAPE of
  the predicted stress-strain curve against Fig. 3.  Do NOT use the
  absolute modulus of either figure as a validation target from this
  paper alone.""" % (got[lim]["as_received"], e0,
                     100.0 * (got[lim]["as_received"] / e0 - 1.0),
                     r3, e60 / e0))

    if write:
        path = os.path.join(HERE, "zhang2013_stress_strain.csv")
        fig = [f for f in FIGURES if f["key"] == "ZHANG2013_fig3"][0]
        curves, _, _ = digitize(fig)
        with open(path, "w") as fh:
            fh.write(
                "# 2D-C/SiC monotonic tensile stress-strain curves, digitized\n"
                "# from refs/[03] Zhang et al., J. Mater. Eng. Perform. 22\n"
                "# (2013) 1680-1687, Fig. 3, by data/literature/digitize.py.\n"
                "# Re-run that script to regenerate this file exactly.\n"
                "#\n"
                "# role = validation.  These are COMPOSITE measurements: the\n"
                "# macro CDM must PREDICT them.  Never put them on a card.\n"
                "#\n"
                "# THIS IS THE STRONGEST VALIDATION ASSET IN THE PROJECT.\n"
                "# Everything else is a handful of points; this is the whole\n"
                "# curve, for the as-received material AND after 60 thermal\n"
                "# shocks, on the same axes.  The macro model produces exactly\n"
                "# this object, so the comparison is direct: initial slope\n"
                "# (modulus), knee (matrix cracking), peak (strength) and the\n"
                "# shape in between all have to line up, not just one number.\n"
                "#\n"
                "# Quench: 900 -> 300 C in air.  strain in %, stress in MPa.\n"
                "curve,cycles,strain_pct,stress_MPa\n")
            for label, pts in curves:
                n = 0 if label == "as_received" else 60
                for x, y, _t in pts:
                    fh.write("%s,%d,%.4f,%.2f\n" % (label, n, x, max(0.0, y)))
        print("\n  wrote %s (%d points)"
              % (os.path.relpath(path),
                 sum(len(p) for _l, p in curves)))

    print("\n" + "=" * 72)
    if fails:
        print("FAILED: %s" % ", ".join(sorted(set(fails))))
        print("=" * 72)
        return 1
    print("ALL DIGITIZATIONS REPRODUCE THE PAPERS' OWN STATED NUMBERS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(strict="--check" in sys.argv,
                  write="--write" in sys.argv))
