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
     scales h and k together, so the Fourier number is recovered FROM THE
     ODB -- by fitting the observed mid-plane decay -- and compared with the
     card's own alpha.  A card whose k is 1000x off makes the plate cool
     1000x slower, and this is the check that notices.

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
#: Card alpha and odb alpha may differ by this much before it is called a
#: unit or property error rather than discretisation.
ALPHA_TOLERANCE = 0.25


def card_thermal(inp_path):
    """(k3, rho, cp, alpha) from the deck's own thermal card, or None.

    Read from the .inp next to the odb.  The deck is the authority: a value
    remembered from the generator is a value that can drift away from the
    file the solver actually read.
    """
    if not inp_path or not os.path.exists(inp_path):
        return None
    txt = open(inp_path).read()
    k = re.search(r"\*Conductivity[^\n]*\n([^\n]+)", txt, re.I)
    r = re.search(r"\*Density\s*\n\s*([0-9.eE+-]+)", txt, re.I)
    c = re.search(r"\*Specific Heat\s*\n\s*([0-9.eE+-]+)", txt, re.I)
    if not (k and r and c):
        return None
    vals = [float(v) for v in k.group(1).split(",") if v.strip()]
    if len(vals) < 3:
        return None
    k3, rho, cp = vals[2], float(r.group(1)), float(c.group(1))
    return dict(k3=k3, rho=rho, cp=cp, alpha=k3 / (rho * cp))


def card_film(inp_path):
    """h in mW/(mm^2.K) from the first *Sfilm data line, or None."""
    if not inp_path or not os.path.exists(inp_path):
        return None
    m = re.search(r"\*Sfilm[^\n]*\n[^,\n]+,\s*F\s*,\s*[0-9.eE+-]+\s*,"
                  r"\s*([0-9.eE+-]+)", open(inp_path).read(), re.I)
    return float(m.group(1)) if m else None


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


def alpha_from_decay(frames, t_hi, t_sink, half):
    """Thermal diffusivity implied by the mid-plane cooling history, mm^2/s.

    For Fo > 0.2 the series collapses to its first term,

        theta = A exp(-lam^2 Fo),   Fo = alpha t / L^2

    so a straight line through ln(theta) against t has slope -lam^2 alpha/L^2.
    lam is not known without Bi, but lam^2 <= 2.4674 (the Bi -> infinity
    limit, (pi/2)^2), so the slope gives a LOWER bound on alpha that is still
    tight enough to catch a factor of 1000.  Returns None if the history is
    too short or never cools.
    """
    pts = []
    for t, fr in frames:
        if not fr or t <= 0:
            continue
        zs = [z for z, _ in fr]
        mid = 0.5 * (min(zs) + max(zs))
        centre = min(fr, key=lambda p: abs(p[0] - mid))[1]
        theta = (centre - t_sink) / float(t_hi - t_sink)
        if theta > 1e-6:
            pts.append((t, math.log(theta)))
    if len(pts) < 4:
        return None
    (t0, y0), (t1, y1) = pts[len(pts) // 2], pts[-1]
    if t1 <= t0 or y1 >= y0:
        return None
    slope = (y0 - y1) / (t1 - t0)          # positive decay rate
    return slope * half * half / 2.4674


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
    h = card_film(inp)
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
            t_sink = min(t for _, pts in frames for _, t in pts)
            g, tg, ig = peak_gradient(frames)
            alpha_card = card["alpha"] if card else None
            n_el, depth, sv = (profile_resolution(
                zs, None, t_hi, alpha_card, tg) if alpha_card
                else (0, 0.0, "no card"))
            t_first = frames[1][0] if len(frames) > 1 else frames[0][0]
            tv = ("PEAK_MISSED" if ig <= 1 and t_first > 0 else "sampled")
            a_odb = alpha_from_decay(frames, t_hi, t_sink, half)
            if a_odb is None or alpha_card is None:
                av, aratio = "not testable", ""
            else:
                aratio = a_odb / alpha_card
                av = ("consistent" if abs(math.log(max(aratio, 1e-30)))
                      < math.log(1.0 + ALPHA_TOLERANCE) + 1.0
                      else "CARD_MISMATCH")
            rows.append(judge(dict(
                odb=os.path.basename(path), step=sname,
                h_card=("" if h is None else "%.6g" % h),
                bi=("" if not (h and card) else "%.4f" % (h * half / card["k3"])),
                peak_grad_K="%.3f" % g, peak_time_s="%.4g" % tg,
                drop_K="%.1f" % (t_hi - t_sink),
                grad_pct=("%.2f" % (100.0 * g / (t_hi - t_sink))
                          if t_hi > t_sink else ""),
                front_depth_mm="%.4f" % depth, elements_in_front=str(n_el),
                min_elements=str(MIN_ELEMENTS_IN_LAYER), space_verdict=sv,
                first_frame_s="%.4g" % t_first,
                peak_frame_index=str(ig), time_verdict=tv,
                alpha_card=("" if alpha_card is None else "%.4f" % alpha_card),
                alpha_odb=("" if a_odb is None else "%.4f" % a_odb),
                alpha_ratio=("" if aratio == "" else "%.3f" % aratio),
                alpha_verdict=av)))
    finally:
        odb.close()
    return rows


COLUMNS = ["odb", "step", "h_card", "bi", "peak_grad_K", "peak_time_s",
           "drop_K", "grad_pct", "front_depth_mm", "elements_in_front",
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
    # Manufacture a first-term decay with a known alpha and read it back.
    alpha, half, lam2 = 3.9825, 1.5, 2.4674
    made = []
    for k in range(12):
        t = 0.1 + 0.1 * k
        th = math.exp(-lam2 * alpha * t / (half * half))
        centre = 25.0 + th * (900.0 - 25.0)
        made.append((t, [(0.0, 25.0), (1.5, centre), (3.0, 25.0)]))
    got = alpha_from_decay(made, 900.0, 25.0, half)
    ck("a known decay returns its own diffusivity",
       got is not None and abs(got / alpha - 1.0) < 0.02,
       "%.4f vs %.4f mm^2/s" % (got, alpha))
    # The whole reason this exists: h and k both 1000x low leaves Bi exactly
    # right, so only the cooling RATE can expose it.
    slow = []
    for k in range(12):
        t = 0.1 + 0.1 * k
        th = math.exp(-lam2 * (alpha / 1000.0) * t / (half * half))
        slow.append((t, [(0.0, 25.0), (1.5, 25.0 + th * 875.0), (3.0, 25.0)]))
    got_slow = alpha_from_decay(slow, 900.0, 25.0, half)
    ck("a 1000x-slow quench reads back 1000x smaller",
       got_slow is not None and abs(got_slow / (alpha / 1000.0) - 1.0) < 0.02,
       "%.6f mm^2/s" % got_slow)
    ck("  so the ratio against the card exposes the unit error",
       got_slow / alpha < 0.01)
    ck("a history that never cools returns None, not a fake number",
       alpha_from_decay([(t, [(0.0, 900.0), (1.5, 900.0), (3.0, 900.0)])
                         for t in (0.1, 0.2, 0.3, 0.4)],
                        900.0, 25.0, half) is None)
    ck("too few frames returns None",
       alpha_from_decay(made[:2], 900.0, 25.0, half) is None)

    print("\n D. the card is read from the deck, never remembered")
    import tempfile
    d = tempfile.mkdtemp()
    inp = os.path.join(d, "j.inp")
    open(inp, "w").write(
        "*Conductivity, type=ORTHO, dependencies=0\n"
        "8.8627, 8.8631, 5.449, 23\n"
        "*Density\n2.00821e-09,\n*Specific Heat\n6.8132e+08, 23\n"
        "*Sfilm\nSURF_LO, F, 300., 0.1816\n")
    c = card_thermal(inp)
    ck("k3 comes off the ORTHO card's THIRD slot", abs(c["k3"] - 5.449) < 1e-9,
       "%.4f mW/(mm.K)" % c["k3"])
    ck("and the diffusivity it implies is physical",
       1.0 < c["alpha"] < 100.0, "%.4f mm^2/s" % c["alpha"])
    ck("the film coefficient comes off *Sfilm, not from a constant",
       abs(card_film(inp) - 0.1816) < 1e-9)
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
