# -*- coding: utf-8 -*-
"""
extract_thermal_profile.py -- read a macro HEAT odb and decide whether the
thermal boundary layer was actually resolved.

RUN INSIDE ABAQUS (it needs odbAccess):

    abaqus python extract_thermal_profile.py LTH_TS_HEAT_SL.odb [more.odb ...]

WHAT IT ANSWERS

The macro thermal-shock claim of this thesis rests on ONE observable: the
through-thickness temperature gradient during the quench, and how it grows
with the Biot number.  Three separate things can make that number wrong
while the job converges beautifully, so all three are checked here:

  1. IS THE GRADIENT RESOLVED IN SPACE?  The quench front penetrates
     sqrt(alpha*t) from the surface.  At the moment the gradient peaks, that
     depth has to contain several elements.  If the first two nodes are
     already sitting at the bath temperature, the reported peak gradient is
     a property of the mesh, not the material.

  2. IS IT RESOLVED IN TIME?  The gradient peaks after about one diffusion
     time and then decays.  A first increment longer than that samples the
     answer after the event -- which is exactly what the deck did until
     2026-08-11 (t_quench/50 = 0.600 s against a peak at 0.30 s).  So the
     time of the peak is compared against the first frame available.

  3. IS THE CARD THE ONE WE THINK IT IS?  Biot cannot see a unit error that
     scales h and k together, so the diffusivity is recovered FROM THE ODB --
     by fitting the observed mid-plane decay -- and compared with the card's
     own alpha.  A card whose k is 1000x off makes the plate cool 1000x
     slower, and this is the check that notices.

     The first version of this check called all three real runs
     CARD_MISMATCH on 2026-08-11, and all three were false alarms.  It got
     three things wrong, and each is worth stating because each is a way to
     misread a perfectly good cooling curve:

       * theta was normalised by the COLDEST NODE EVER SEEN instead of the
         bath the film blows against.  At Bi = 0.05 the plate never reaches
         the bath in one quench, so that denominator was 283 K instead of
         600 K and the fitted decay came out seven times too fast.
       * the eigenvalue was pinned at the Bi -> infinity limit, lam^2 =
         2.4674.  The real lam solves lam*tan(lam) = Bi and runs from 0.0492
         at Bi = 0.05 to 1.7262 at Bi = 5 -- a factor of 35 across our own
         ladder, applied as if it were a constant.
       * alpha was compared against its value at 23 C while the quench runs
         between 900 C and 300 C, where the card's own alpha is 1.23 to 2.45
         rather than 3.98.

     Fixed, the same three runs read 1.81 / 2.10 / 1.43 mm^2/s against a card
     range of 1.23-2.45.  A 1000x unit error is still three orders outside
     that window, so the check keeps all of its power and none of its bite.

Everything is written to <job>_thermal.csv, one row per quench step, with the
value, the basis it was judged against and the verdict in the same row.  The
console is a log; the CSV is the deliverable.
"""
from __future__ import print_function

import math
import os
import re
import sys

try:
    from odbAccess import openOdb
except ImportError:
    # Every judgement below is plain arithmetic on lists, and --selftest
    # exercises exactly that with ordinary python.  The verdict logic is
    # therefore checked BEFORE the jobs run, not after.
    openOdb = None

#: A quench front that has reached this many elements is resolved.  Three is
#: the minimum that can show curvature at all; below it the "gradient" is a
#: straight line between two nodes and its magnitude is set by the spacing.
MIN_ELEMENTS_IN_LAYER = 3
#: The first frame must land this far inside the diffusion time, or the peak
#: has already passed before anything was recorded.
PEAK_FRAME_FRACTION = 0.5
#: The odb's fitted alpha may sit this far outside the card's own alpha
#: RANGE over the quench before it is called a unit or property error.  A
#: factor of 2 is loose on purpose: the fit is a one-term series against a
#: temperature-dependent card, so a tight window would only ever produce
#: false alarms.  The failure it exists to catch is a factor of 1000.
ALPHA_FACTOR = 2.0


def _table(txt, keyword, ncol):
    """[(value, T), ...] from a keyword's data block.  T is None if absent."""
    m = re.search(r"\*%s[^\n]*\n((?:[^*\n][^\n]*\n?)+)" % keyword, txt, re.I)
    if not m:
        return []
    rows = []
    for ln in m.group(1).splitlines():
        v = [float(x) for x in ln.split(",") if x.strip()]
        if len(v) >= ncol:
            rows.append((v[ncol - 1], v[ncol] if len(v) > ncol else None))
    return rows


def _at(rows, T):
    """Linear interpolation of a (value, temperature) table, flat outside."""
    pts = sorted((t, v) for v, t in rows if t is not None)
    if not pts:
        return rows[0][0] if rows else None
    if T <= pts[0][0]:
        return pts[0][1]
    for (ta, va), (tb, vb) in zip(pts, pts[1:]):
        if ta <= T <= tb:
            return va + (vb - va) * (T - ta) / (tb - ta)
    return pts[-1][1]


def card_thermal(inp_path):
    """The deck's own thermal card, with alpha as a function of temperature.

    Read from the .inp next to the odb.  The deck is the authority: a value
    remembered from the generator is a value that can drift away from the
    file the solver actually read.  The card is temperature dependent, so
    `alpha_at` is a function and `alpha` is only its value at the first row.
    """
    if not inp_path or not os.path.exists(inp_path):
        return None
    txt = open(inp_path).read()
    ks = _table(txt, "Conductivity", 3)
    rs = _table(txt, "Density", 1)
    cs = _table(txt, "Specific Heat", 1)
    if not (ks and rs and cs):
        return None
    rho = rs[0][0]

    def alpha_at(T):
        return _at(ks, T) / (rho * _at(cs, T))

    return dict(k3=ks[0][0], rho=rho, cp=cs[0][0], alpha=alpha_at(ks[0][1] or 0.0),
                alpha_at=alpha_at, k_rows=ks, cp_rows=cs)


def card_film(inp_path):
    """(h, T_sink) from the first *Sfilm data line, or (None, None).

    T_sink is the BATH the film blows against, and it is the denominator of
    every normalised temperature below.  Taking it from the coldest node
    instead -- which this file did until 2026-08-11 -- silently rescales the
    whole decay whenever the plate does not reach the bath within one
    quench, which is exactly what happens at low Biot number.
    """
    if not inp_path or not os.path.exists(inp_path):
        return None, None
    m = re.search(r"\*Sfilm[^\n]*\n[^,\n]+,\s*F\s*,\s*([0-9.eE+-]+)\s*,"
                  r"\s*([0-9.eE+-]+)", open(inp_path).read(), re.I)
    if not m:
        return None, None
    return float(m.group(2)), float(m.group(1))


def eigenvalue(bi):
    """lam solving lam*tan(lam) = Bi, the first root in (0, pi/2).

    This is the whole temperature-decay problem in one number, and it is NOT
    a constant: lam^2 runs 0.0492 -> 1.7262 across our own Bi = 0.05 -> 5
    ladder and only reaches 2.4674 as Bi -> infinity.
    """
    if bi <= 0:
        return 0.0
    lo, hi = 1.0e-12, 0.5 * math.pi - 1.0e-12
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if m * math.tan(m) < bi:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def profile_resolution(zs, temps, t_hot, alpha, t):
    """(elements inside the front, front depth mm, verdict).

    `zs` are through-thickness coordinates sorted low to high and `temps` the
    matching nodal temperatures.  The front depth is sqrt(alpha*t), the
    classical penetration depth; elements are counted from the cold surface
    inward until that depth is passed.
    """
    depth = math.sqrt(max(alpha * t, 0.0))
    lo = zs[0]
    n = 0
    for a, b in zip(zs, zs[1:]):
        if a - lo > depth:
            break
        n += 1
        if b - lo > depth:
            break
    # A front deeper than the half-thickness means the plate is equilibrating,
    # not developing a boundary layer, and counting elements is meaningless.
    half = 0.5 * (zs[-1] - zs[0])
    if depth >= half:
        return n, depth, "equilibrating"
    return n, depth, ("resolved" if n >= MIN_ELEMENTS_IN_LAYER
                      else "UNRESOLVED")


def peak_gradient(frames):
    """(peak centre-to-surface difference K, the time it happened, index).

    `frames` is [(time, [(z, T), ...]), ...].  The gradient is measured as
    mid-plane minus coldest surface, which is the quantity quench_calibration
    solves for, so the two are directly comparable.
    """
    best, t_best, i_best = 0.0, 0.0, -1
    for i, (t, pts) in enumerate(frames):
        if not pts:
            continue
        zs = [z for z, _ in pts]
        mid = 0.5 * (min(zs) + max(zs))
        centre = min(pts, key=lambda p: abs(p[0] - mid))[1]
        surface = min(p[1] for p in pts)
        if centre - surface > best:
            best, t_best, i_best = centre - surface, t, i
    return best, t_best, i_best


def alpha_from_decay(frames, t_hi, t_sink, half, bi):
    """Thermal diffusivity implied by the mid-plane cooling history, mm^2/s.

    Once the transient has settled the series collapses to its first term,

        theta = A exp(-lam^2 Fo),   Fo = alpha t / L^2,   lam tan lam = Bi

    so a straight line through ln(theta) against t has slope lam^2 alpha/L^2
    and alpha = slope L^2 / lam^2.

    Both `t_sink` and `bi` matter and both were wrong here once:
    `t_sink` must be the film's bath, not the coldest node, or a plate that
    has not finished cooling reports a decay many times too fast; and lam
    must come from this run's own Bi, not from the Bi -> infinity limit.

    Returns None if the history is too short or never cools -- an honest
    None beats a number that looks like a measurement.
    """
    if bi is None or bi <= 0 or t_hi <= t_sink:
        return None
    pts = []
    for t, fr in frames:
        if not fr or t <= 0:
            continue
        zs = [z for z, _ in fr]
        mid = 0.5 * (min(zs) + max(zs))
        centre = min(fr, key=lambda p: abs(p[0] - mid))[1]
        theta = (centre - t_sink) / float(t_hi - t_sink)
        if theta > 1.0e-4:
            pts.append((t, math.log(theta)))
    if len(pts) < 4:
        return None
    (t0, y0), (t1, y1) = pts[len(pts) // 2], pts[-1]
    if t1 <= t0 or y1 >= y0:
        return None
    slope = (y0 - y1) / (t1 - t0)          # positive decay rate
    lam = eigenvalue(bi)
    if lam <= 0:
        return None
    return slope * half * half / (lam * lam)


def alpha_window(card, t_lo, t_hi):
    """(lo, hi) card diffusivity across the temperatures the quench visits.

    The card is temperature dependent and the quench spans hundreds of
    degrees, so there is no single "the card's alpha" to compare against --
    comparing against its 23 C value while the plate sits at 900 C is a
    factor of three before anything is even wrong.
    """
    if not card or "alpha_at" not in card:
        return None
    vals = [card["alpha_at"](t_lo + (t_hi - t_lo) * i / 8.0)
            for i in range(9)]
    return min(vals), max(vals)


def judge(row):
    """Fill the verdict columns.  Value, basis and verdict travel together."""
    v = []
    if row["space_verdict"] == "UNRESOLVED":
        v.append("mesh")
    if row["time_verdict"] == "PEAK_MISSED":
        v.append("increment")
    if row["alpha_verdict"] == "CARD_MISMATCH":
        v.append("card")
    row["verdict"] = "ok" if not v else "SUSPECT: " + "+".join(v)
    return row


def read(path):
    if openOdb is None:
        sys.exit("odbAccess not found -- run this with 'abaqus python', "
                 "not with plain python.")
    inp = os.path.splitext(path)[0] + ".inp"
    card = card_thermal(inp)
    h, t_sink_card = card_film(inp)
    odb = openOdb(path, readOnly=True)
    rows = []
    try:
        inst = list(odb.rootAssembly.instances.values())[0]
        coord = dict((n.label, n.coordinates) for n in inst.nodes)
        zall = [c[2] for c in coord.values()]
        zlo, zhi = min(zall), max(zall)
        half = 0.5 * (zhi - zlo)
        # One through-thickness line, at the node column closest to the
        # centre of the plate: a corner column sees the edge and would report
        # a gradient the interior never had.
        xs = [c[0] for c in coord.values()]
        ys = [c[1] for c in coord.values()]
        xc, yc = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys))
        best = min(coord.values(),
                   key=lambda c: (c[0] - xc) ** 2 + (c[1] - yc) ** 2)
        tol = 1.0e-6 + 1.0e-3 * max(1.0, abs(best[0]) + abs(best[1]))
        line = sorted(lbl for lbl, c in coord.items()
                      if abs(c[0] - best[0]) < tol and abs(c[1] - best[1]) < tol)
        zs = [coord[l][2] for l in line]

        for sname in odb.steps.keys():
            if not sname.upper().startswith("QUENCH"):
                continue
            step = odb.steps[sname]
            frames = []
            for fr in step.frames:
                fo = fr.fieldOutputs
                if "NT11" not in fo.keys() and "NT" not in fo.keys():
                    continue
                key = "NT11" if "NT11" in fo.keys() else "NT"
                vals = dict((v.nodeLabel, v.data) for v in fo[key].values)
                pts = [(coord[l][2], vals[l]) for l in line if l in vals]
                frames.append((fr.frameValue, sorted(pts)))
            if not frames:
                print("  %s: no NT field output" % sname)
                continue
            t_hi = max(t for _, pts in frames[:1] for _, t in pts)
            # The bath is the film's own sink temperature.  Falling back to
            # the coldest node is only right when the plate actually reaches
            # the bath, so the fallback is announced rather than assumed.
            t_bath = (t_sink_card if t_sink_card is not None
                      else min(t for _, pts in frames for _, t in pts))
            reached = min(t for _, pts in frames for _, t in pts)
            g, tg, ig = peak_gradient(frames)
            bi = (h * half / card["k3"]) if (h and card) else None
            # The front is judged on the alpha the material HAS while it is
            # cooling, not on its room-temperature value.
            win = alpha_window(card, t_bath, t_hi)
            alpha_mid = (0.5 * (win[0] + win[1])) if win else None
            n_el, depth, sv = (profile_resolution(
                zs, None, t_hi, alpha_mid, tg) if alpha_mid
                else (0, 0.0, "no card"))
            t_first = frames[1][0] if len(frames) > 1 else frames[0][0]
            tv = ("PEAK_MISSED" if ig <= 1 and t_first > 0 else "sampled")
            a_odb = alpha_from_decay(frames, t_hi, t_bath, half, bi)
            if a_odb is None or win is None:
                av, aratio = "not testable", ""
            else:
                # Judged against the WINDOW, loosened by ALPHA_FACTOR.  The
                # ratio reported is against the nearest edge, so 1.0 means
                # "inside" and 0.001 means the thermal unit error.
                lo, hi = win[0] / ALPHA_FACTOR, win[1] * ALPHA_FACTOR
                aratio = (1.0 if lo <= a_odb <= hi
                          else (a_odb / lo if a_odb < lo else a_odb / hi))
                av = "consistent" if lo <= a_odb <= hi else "CARD_MISMATCH"
            rows.append(judge(dict(
                odb=os.path.basename(path), step=sname,
                h_card=("" if h is None else "%.6g" % h),
                bi=("" if bi is None else "%.4f" % bi),
                peak_grad_K="%.3f" % g, peak_time_s="%.4g" % tg,
                drop_K="%.1f" % (t_hi - t_bath),
                grad_pct=("%.2f" % (100.0 * g / (t_hi - t_bath))
                          if t_hi > t_bath else ""),
                reached_K="%.1f" % reached, bath_K="%.1f" % t_bath,
                front_depth_mm="%.4f" % depth, elements_in_front=str(n_el),
                min_elements=str(MIN_ELEMENTS_IN_LAYER), space_verdict=sv,
                first_frame_s="%.4g" % t_first,
                peak_frame_index=str(ig), time_verdict=tv,
                alpha_card=("" if win is None else "%.4f-%.4f" % win),
                alpha_odb=("" if a_odb is None else "%.4f" % a_odb),
                alpha_ratio=("" if aratio == "" else "%.3f" % aratio),
                alpha_verdict=av)))
    finally:
        odb.close()
    return rows


COLUMNS = ["odb", "step", "h_card", "bi", "peak_grad_K", "peak_time_s",
           "drop_K", "grad_pct", "reached_K", "bath_K",
           "front_depth_mm", "elements_in_front",
           "min_elements", "space_verdict", "first_frame_s",
           "peak_frame_index", "time_verdict", "alpha_card", "alpha_odb",
           "alpha_ratio", "alpha_verdict", "verdict"]


def write_csv(path, rows):
    import csv as _csv
    with open(path, "w") as fh:
        w = _csv.writer(fh)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r.get(c, "") for c in COLUMNS])


def selftest():
    fails = []

    def ck(name, ok, detail=""):
        print("  [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    print("extract_thermal_profile.py selftest")
    print("\n A. the front depth decides whether the mesh resolved it")
    # The real deck: 3 mm plate, 12 graded layers, thinnest 0.1431 mm.
    zs = [0.0, 0.1431, 0.32, 0.55, 0.86, 1.22, 1.5, 1.78, 2.14, 2.45,
          2.68, 2.8569, 3.0]
    n, d, v = profile_resolution(zs, None, 900.0, 3.9825, 0.30)
    ck("the real mesh resolves the peak-time front", v == "resolved" and n >= 3,
       "%d elements inside %.3f mm" % (n, d))
    n2, d2, v2 = profile_resolution([0.0, 1.5, 3.0], None, 900.0, 3.9825, 0.30)
    ck("a 2-element mesh does not, and is called out", v2 == "UNRESOLVED",
       "%d elements inside %.3f mm" % (n2, d2))
    # Once the front passes the half-thickness there is no boundary layer to
    # resolve, and calling that UNRESOLVED would be a false alarm on every
    # late frame of every job.
    ck("a fully soaked plate is 'equilibrating', not 'UNRESOLVED'",
       profile_resolution(zs, None, 900.0, 3.9825, 10.0)[2] == "equilibrating")

    print("\n B. the peak gradient is found where it actually is")
    # Centre stays hot, surface drops, recovers: peak in the middle frame.
    frames = [(0.0, [(0.0, 900.0), (1.5, 900.0), (3.0, 900.0)]),
              (0.1, [(0.0, 700.0), (1.5, 890.0), (3.0, 700.0)]),
              (0.3, [(0.0, 500.0), (1.5, 800.0), (3.0, 500.0)]),
              (1.0, [(0.0, 400.0), (1.5, 450.0), (3.0, 400.0)])]
    g, t, i = peak_gradient(frames)
    ck("peak found at the right frame", abs(g - 300.0) < 1e-9 and t == 0.3,
       "%.1f K at t = %g s (frame %d)" % (g, t, i))
    ck("  and it is the mid-plane minus the COLDEST surface, not the mean",
       peak_gradient([(1.0, [(0.0, 500.0), (1.5, 800.0), (3.0, 700.0)])])[0]
       == 300.0)
    ck("a peak in the very first recorded frame is flagged, not trusted",
       peak_gradient(frames[2:])[2] == 0)

    print("\n C. the diffusivity is recovered from the odb, not trusted")
    ck("the eigenvalue is solved, not assumed",
       abs(eigenvalue(5.0) ** 2 - 1.7262) < 1e-3
       and abs(eigenvalue(0.05) ** 2 - 0.0492) < 1e-3,
       "lam^2 = %.4f at Bi=5, %.4f at Bi=0.05 (the old constant was 2.4674)"
       % (eigenvalue(5.0) ** 2, eigenvalue(0.05) ** 2))
    ck("  and it approaches (pi/2)^2 only as Bi -> infinity",
       abs(eigenvalue(1e9) ** 2 - 2.4674) < 1e-3)

    def decay(alpha, bi, half=1.5, t_hi=900.0, t_bath=300.0, n=12):
        """A synthetic first-term history with a KNOWN alpha and Bi.

        The SURFACE follows cos(lam) of the mid-plane rather than sitting at
        the bath, because that is what a real plate does: at Bi = 0.05 the
        surface is within 2.5 % of the centre and the whole plate is still
        hundreds of degrees above the bath when the quench ends.  A test
        whose surface is pinned at the bath cannot see the bug that
        normalising by the coldest node causes.
        """
        lam = eigenvalue(bi)
        out = []
        for k in range(n):
            t = 0.1 + 0.1 * k
            th = math.exp(-lam * lam * alpha * t / (half * half))
            c = t_bath + th * (t_hi - t_bath)
            srf = t_bath + th * math.cos(lam) * (t_hi - t_bath)
            out.append((t, [(0.0, srf), (1.5, c), (3.0, srf)]))
        return out

    alpha, half = 1.8, 1.5
    for bi in (0.05, 1.0, 5.0):
        got = alpha_from_decay(decay(alpha, bi), 900.0, 300.0, half, bi)
        ck("a known decay returns its alpha at Bi = %-4g" % bi,
           got is not None and abs(got / alpha - 1.0) < 0.02,
           "%.4f vs %.4f mm^2/s" % (got, alpha))
    # The bug that produced three false alarms: at low Bi the plate does not
    # reach the bath in one quench, and normalising by the coldest node seen
    # instead of the bath inflates the fitted decay several times over.
    fr = decay(alpha, 0.05)
    coldest = min(t for _, pts in fr for _, t in pts)
    wrong = alpha_from_decay(fr, 900.0, coldest, half, 0.05)
    right = alpha_from_decay(fr, 900.0, 300.0, half, 0.05)
    ck("normalising by the coldest node instead of the bath inflates alpha",
       wrong is not None and wrong > 3.0 * right,
       "%.3f vs the correct %.3f mm^2/s" % (wrong, right))
    # And the failure it exists for is still three orders away.
    slow = alpha_from_decay(decay(alpha / 1000.0, 5.0), 900.0, 300.0, half, 5.0)
    ck("a 1000x-slow quench still reads back 1000x smaller",
       slow is not None and abs(slow / (alpha / 1000.0) - 1.0) < 0.02,
       "%.6f mm^2/s" % slow)
    ck("a history that never cools returns None, not a fake number",
       alpha_from_decay([(t, [(0.0, 900.0), (1.5, 900.0), (3.0, 900.0)])
                         for t in (0.1, 0.2, 0.3, 0.4)],
                        900.0, 300.0, half, 1.0) is None)
    ck("too few frames returns None",
       alpha_from_decay(decay(alpha, 1.0, n=2), 900.0, 300.0, half, 1.0)
       is None)

    print("\n D. the card is read from the deck, never remembered")
    import tempfile
    d = tempfile.mkdtemp()
    inp = os.path.join(d, "j.inp")
    # The real card, all three temperature rows -- a one-row fixture cannot
    # test the very thing that produced the false alarms.
    open(inp, "w").write(
        "*Conductivity, type=ORTHO, dependencies=0\n"
        "8.8627, 8.8631, 5.449, 23\n"
        "7.37023, 7.37056, 4.53139, 500\n"
        "5.80579, 5.80606, 3.56954, 1000\n"
        "*Density\n2.00821e-09,\n"
        "*Specific Heat\n6.8132e+08, 23\n1.22787e+09, 500\n"
        "1.60149e+09, 1000\n"
        "*Sfilm\nSURF_LO, F, 300., 0.1816\n")
    c = card_thermal(inp)
    ck("k3 comes off the ORTHO card's THIRD slot", abs(c["k3"] - 5.449) < 1e-9,
       "%.4f mW/(mm.K)" % c["k3"])
    ck("and the diffusivity it implies is physical",
       1.0 < c["alpha"] < 100.0, "%.4f mm^2/s" % c["alpha"])
    h_got, sink_got = card_film(inp)
    ck("the film coefficient comes off *Sfilm, not from a constant",
       abs(h_got - 0.1816) < 1e-9)
    ck("  and so does the BATH temperature, the denominator of every theta",
       abs(sink_got - 300.0) < 1e-9, "%.1f C" % sink_got)
    ck("alpha is a temperature FUNCTION, not the 23 C value",
       abs(c["alpha_at"](23.0) - 3.9825) < 1e-3
       and abs(c["alpha_at"](900.0) - 1.2269) < 1e-3,
       "%.4f at 23 C, %.4f at 900 C" % (c["alpha_at"](23.0),
                                        c["alpha_at"](900.0)))
    lo, hi = alpha_window(c, 300.0, 900.0)
    ck("  so the quench is judged against a WINDOW, not a point",
       abs(lo - 1.2269) < 1e-3 and abs(hi - 2.4512) < 1e-3,
       "%.4f - %.4f mm^2/s over 300-900 C" % (lo, hi))
    # The three real runs of 2026-08-11, judged by the fixed rule.
    for name, a in (("SL", 1.809), ("SM", 2.100), ("SH", 1.427)):
        ck("  the real %s run sits inside that window" % name,
           lo / ALPHA_FACTOR <= a <= hi * ALPHA_FACTOR,
           "%.3f mm^2/s" % a)
    ck("  and a 1000x unit error still does not",
       not (lo / ALPHA_FACTOR <= 1.427e-3 <= hi * ALPHA_FACTOR))
    ck("a missing deck returns None so the caller can say so",
       card_thermal(os.path.join(d, "absent.inp")) is None)
    old = os.path.join(d, "old.inp")
    open(old, "w").write("*Conductivity, type=ORTHO\n0.015, 0.015, 0.004\n"
                         "*Density\n2.1e-09,\n*Specific Heat\n1.0e+09,\n")
    ck("the pre-2026-08-11 card reads back as unphysical",
       card_thermal(old)["alpha"] < 0.01,
       "%.6f mm^2/s" % card_thermal(old)["alpha"])

    print("\n E. the verdict column names what is wrong")
    ck("a clean row says ok",
       judge(dict(space_verdict="resolved", time_verdict="sampled",
                  alpha_verdict="consistent"))["verdict"] == "ok")
    r = judge(dict(space_verdict="UNRESOLVED", time_verdict="PEAK_MISSED",
                   alpha_verdict="CARD_MISMATCH"))["verdict"]
    ck("and a bad row names all three, not just the first",
       "mesh" in r and "increment" in r and "card" in r, r)
    f = os.path.join(d, "t.csv")
    write_csv(f, [judge(dict(odb="a.odb", step="Quench_1",
                             space_verdict="resolved", time_verdict="sampled",
                             alpha_verdict="consistent", peak_grad_K="18.7"))])
    import csv as _csv
    got = list(_csv.DictReader(open(f)))[0]
    ck("the CSV carries value, basis and verdict in one row",
       got["peak_grad_K"] == "18.7" and got["min_elements"] == ""
       and got["verdict"] == "ok")
    ck("  and every column the reader promises exists",
       set(got.keys()) == set(COLUMNS))

    if fails:
        print("\nSELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("\nSELFTEST PASSED")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = [a for a in argv if a.endswith(".odb")]
    if not paths:
        print(__doc__)
        return 1
    print("=" * 76)
    print("extract_thermal_profile.py -- did the quench resolve its gradient?")
    print("=" * 76)
    allrows = []
    for p in paths:
        print("\n--- %s" % os.path.basename(p))
        rows = read(p)
        for r in rows:
            print("  %-12s peak %7s K (%5s %% of %6s K) at t = %-8s "
                  "front %6s mm / %2s el  [%s]"
                  % (r["step"], r["peak_grad_K"], r["grad_pct"], r["drop_K"],
                     r["peak_time_s"], r["front_depth_mm"],
                     r["elements_in_front"], r["verdict"]))
            if r["alpha_verdict"] == "CARD_MISMATCH":
                print("      !! alpha from the odb is %s against the card's "
                      "%s (ratio %s).  A ratio near 1/1000 is the thermal "
                      "unit error; see eval_correlations.py."
                      % (r["alpha_odb"], r["alpha_card"], r["alpha_ratio"]))
        out = os.path.splitext(p)[0] + "_thermal.csv"
        write_csv(out, rows)
        print("  wrote %s" % os.path.basename(out))
        allrows.extend(rows)
    if allrows:
        write_csv("thermal_summary.csv", allrows)
        print("\nwrote thermal_summary.csv -- UPLOAD THIS ONE")
    bad = [r for r in allrows if r["verdict"] != "ok"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
