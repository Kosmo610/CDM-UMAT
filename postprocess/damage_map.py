# -*- coding: utf-8 -*-
"""
damage_map.py -- WHERE is the damage worst, and what kind is it?

Two products from one pass over an odb:

  1. NEW FIELD OUTPUTS written into the odb, so the Viewer can contour damage
     over the WHOLE model in one picture:

         DAMG   the largest fractional stiffness loss at this point, whatever
                phase it is in and whatever mode caused it.  0 = intact.
         DMODE  an integer that says which phase AND which mechanism owns that
                number (11/12 matrix, 21..24 yarn, 31..34 macro).
         DADD   DAMG minus DAMG at a reference frame -- the damage THIS step
                added, with the manufacturing cooldown subtracted out.

  2. A CSV, <job>_damage_map.csv, carrying the same information as numbers:
     per-phase distribution, the worst N elements with their coordinates, and
     a slice-by-slice profile along one axis.

RUN INSIDE ABAQUS (it needs odbAccess):

    abaqus python damage_map.py <job.odb>
    abaqus python damage_map.py <job.odb> --axis z --top 30
    abaqus python damage_map.py <job.odb> --no-write-field      # csv only

and outside Abaqus, to check the arithmetic:

    python3 postprocess/damage_map.py --selftest


WHY THIS EXISTS -- the trap it removes
--------------------------------------
The three materials in this project number their state variables DIFFERENTLY:

    matrix   SDV1 DMT   SDV2 DMC    SDV7 MMODE    SDV9  EQPS
    yarn     SDV1 DY1T  SDV2 DY1C   SDV9 DY1      SDV10 DYT    SDV11 YMODE
    macro    SDV9 D1    SDV10 DT    SDV11 MODE    SDV17 DCYC   SDV29 TWMAX

So contouring "SDV9" over an RVE draws YARN LONGITUDINAL DAMAGE inside the
yarns and EQUIVALENT PLASTIC STRAIN inside the matrix, on one colour bar, with
no warning.  The picture looks plausible and is meaningless.  A script that
subsets by element set first is immune to this; a human dragging a variable
out of the Viewer's dropdown is not.  DAMG exists so that the human is too.

WHAT DAMG IS, EXACTLY, AND WHAT IT IS NOT
-----------------------------------------
DAMG is defined as the largest value of d that multiplies a stiffness at this
integration point:

    matrix   max(DMT, DMC)          both scale the matrix modulus
    yarn     max(DY1, DYT)          E1*(1-DY1), E2*(1-DYT), E3*(1-DYT)
    macro    max(D1, DT)            same structure at the macro scale

so "DAMG = 0.6" means the same thing everywhere: the worst-hit stiffness at
this point has lost 60 % of its value.  That is a real common currency, and it
is the only one these three materials share.

It is NOT "fraction of the way to failure".  A matrix at DAMG = 0.9 with sound
yarns is a cracked-matrix composite that still carries most of its load; a yarn
at DAMG = 0.9 in the longitudinal mode is a broken tow.  ALWAYS read the phase
column with the number.  This is why the CSV reports per phase and never gives
a single model-wide "damage" figure.

Nor is DAMG mesh-objective by itself.  Damage localises into one element row,
so its PEAK value depends on element size; what the crack band keeps invariant
is the ENERGY, not d.  Compare DAMG maps between meshes only through the
volume fractions and the profile, never through the peak.

DMODE is derived from the damage components (which d is biggest), while the
UMAT's own MODE slot records which CRITERION is biggest.  They usually agree.
Where they do not, the CSV shows both in the same row -- a point whose largest
damage and largest criterion disagree is a point that changed mode partway
through, and it is worth looking at.
"""
from __future__ import print_function

import os
import sys
import argparse

try:
    from odbAccess import openOdb
    from abaqusConstants import SCALAR, CENTROID, INTEGRATION_POINT
except ImportError:                       # plain python: selftest only
    openOdb = None
    SCALAR = CENTROID = INTEGRATION_POINT = None


# --------------------------------------------------------------------------
# the phase table -- the whole point of the file is that this differs per phase
# --------------------------------------------------------------------------
#: For each phase:
#:   base      DMODE = base + mode index
#:   mag       (slot, name) pairs whose max IS the stiffness loss
#:   comp      (slot, name, mode index, label) of the components that say WHICH
#:   umatmode  (slot, name) where the UMAT wrote its own criterion-based mode
PHASES = {
    "Matrix": dict(
        base=10,
        mag=[(1, "DMT"), (2, "DMC")],
        comp=[(1, "DMT", 1, "matrix_tension"),
              (2, "DMC", 2, "matrix_compression")],
        umatmode=(7, "MMODE"),
    ),
    "Yarn": dict(
        base=20,
        mag=[(9, "DY1"), (10, "DYT")],
        comp=[(1, "DY1T", 1, "yarn_long_tension"),
              (2, "DY1C", 2, "yarn_long_compression"),
              (3, "DYTT", 3, "yarn_trans_tension"),
              (4, "DYTC", 4, "yarn_trans_compression")],
        umatmode=(11, "YMODE"),
    ),
    "Macro": dict(
        base=30,
        mag=[(9, "D1"), (10, "DT")],
        comp=[(1, "D1T", 1, "macro_warp_tension"),
              (2, "D1C", 2, "macro_warp_compression"),
              (3, "DTT", 3, "macro_trans_tension"),
              (4, "DTC", 4, "macro_trans_compression")],
        umatmode=(11, "MODE"),
    ),
}

#: The card's damage cap (D_DMAX in abaqus/retune_deck.py).  An element sitting
#: on it has been taken as far as the card allows, so the "worst" element is a
#: plateau rather than a point and the ranking below it is what matters.
DMAX_CAP = 0.99
CAP_TOL = 1.0e-4

#: Volume-fraction thresholds reported for every phase.
D_BINS = (0.01, 0.10, 0.50, 0.90)

#: A phase is called "localised" rather than "distributed" when less than this
#: fraction of its volume is past d = 0.5.  Below it the softening lives in a
#: band; above it the whole phase is coming apart and a peak location is not
#: meaningful on its own.
LOCALISED_MAX_VOLFRAC = 0.05

#: Outer fraction of the axis counted as "surface" in the profile verdict.
#: 0.2 = the outermost 10 % at each end, which for the macro thermal-shock
#: specimen is the region the quench boundary layer actually occupies.
SURFACE_SPAN = 0.20

#: How much hotter the surface has to be than the interior before the profile
#: is called surface-dominant rather than uniform.
PROFILE_RATIO = 1.5

N_PROFILE_BINS = 10


def mode_name(code):
    """'yarn_trans_tension' for 23, and so on.  '' for an unknown code."""
    for ph, spec in PHASES.items():
        for _slot, _nm, idx, label in spec["comp"]:
            if spec["base"] + idx == code:
                return label
    return ""


def unify(phase, mag_vals, comp_vals):
    """(DAMG, DMODE) for one point.

    mag_vals   values of this phase's 'mag' slots, in table order
    comp_vals  values of this phase's 'comp' slots, in table order

    DAMG is the biggest stiffness loss; DMODE names the biggest COMPONENT.
    They come from different slots on purpose: DY1 already merges DY1T and
    DY1C, so it is the honest magnitude, but it cannot say which of the two
    it was.
    """
    spec = PHASES[phase]
    damg = max(mag_vals) if mag_vals else 0.0
    if damg <= 0.0 or not comp_vals:
        return damg, 0
    best = 0
    bestv = -1.0
    for k, v in enumerate(comp_vals):
        if v > bestv:
            bestv, best = v, k
    if bestv <= 0.0:
        return damg, 0
    return damg, spec["base"] + spec["comp"][best][2]


def stats(pairs):
    """mean / percentiles / max of (value, volume) pairs, volume-weighted mean.

    Percentiles are on the VALUE list, unweighted, which is what you want when
    the mesh is near-uniform and what damage_census.py already does.  The mean
    is volume-weighted because it is compared with volume fractions.
    """
    if not pairs:
        return None
    tot = sum(w for _, w in pairs)
    if tot <= 0.0:
        return None
    vals = sorted(v for v, _ in pairs)
    n = len(vals)

    def q(f):
        return vals[min(n - 1, int(f * n))]

    return dict(n=n, vol=tot,
                mean=sum(v * w for v, w in pairs) / tot,
                p50=q(0.50), p90=q(0.90), p99=q(0.99),
                mx=vals[-1], mn=vals[0])


def volfrac(pairs, thr):
    tot = sum(w for _, w in pairs)
    if tot <= 0.0:
        return 0.0
    return sum(w for v, w in pairs if v >= thr) / tot


def phase_verdict(st, f50):
    """One word for the state of a phase, from its own distribution.

    The order matters: 'saturated' is tested before 'distributed' because a
    phase whose MEAN is past 0.5 is not merely widely damaged, it is gone, and
    no peak location taken from it means anything.
    """
    if st is None:
        return "no_data"
    if st["mx"] < 0.01:
        return "intact"
    if st["mean"] >= 0.5:
        return "saturated"
    if f50 >= LOCALISED_MAX_VOLFRAC:
        return "distributed"
    if st["p99"] >= 0.5 or st["mx"] >= 0.5:
        return "localised"
    return "subcritical"


def hotspot_verdict(damg, at_cap_count):
    """Whether the top of the ranking is a point or a plateau."""
    if damg >= DMAX_CAP - CAP_TOL:
        if at_cap_count > 1:
            return "at_cap_plateau"
        return "at_cap"
    if damg >= 0.5:
        return "softening"
    if damg >= 0.01:
        return "initiated"
    return "negligible"


def profile(items, axis, nbins=N_PROFILE_BINS):
    """Volume-weighted mean DAMG in nbins slices along one axis.

    items: (damg, volume, (x, y, z)) .  Returns (bins, lo, hi) where bins is a
    list of dicts with frac_lo/frac_hi/mean/vol/n.  Empty slices are kept, so
    the list is always nbins long and a gap is visible as n = 0.
    """
    pts = [(c[axis], d, w) for d, w, c in items]
    if not pts:
        return [], 0.0, 0.0
    lo = min(p[0] for p in pts)
    hi = max(p[0] for p in pts)
    span = hi - lo
    bins = [dict(frac_lo=k / float(nbins), frac_hi=(k + 1) / float(nbins),
                 acc=0.0, vol=0.0, n=0) for k in range(nbins)]
    for c, d, w in pts:
        if span <= 0.0:
            k = 0
        else:
            k = int(nbins * (c - lo) / span)
            if k >= nbins:
                k = nbins - 1
        b = bins[k]
        b["acc"] += d * w
        b["vol"] += w
        b["n"] += 1
    for b in bins:
        b["mean"] = b["acc"] / b["vol"] if b["vol"] > 0.0 else 0.0
    return bins, lo, hi


def profile_verdict(bins, span=SURFACE_SPAN, ratio=PROFILE_RATIO):
    """Is the damage at the surface, in the interior, or spread evenly?

    'Surface' is the outermost `span` of the axis SPLIT BETWEEN THE TWO ENDS,
    because a quenched plate is cooled on both faces.  The verdict is the one
    number this whole profile exists to produce: for thermal shock, surface
    damage is the quench tension and interior damage is the reheat reversal,
    and they are different physics.
    """
    if not bins:
        return "no_data"
    nb = len(bins)
    k = max(1, int(round(0.5 * span * nb)))
    surf = bins[:k] + bins[nb - k:]
    core = bins[k:nb - k]
    if not core:
        return "no_data"

    def m(bs):
        v = sum(b["vol"] for b in bs)
        return sum(b["mean"] * b["vol"] for b in bs) / v if v > 0.0 else 0.0

    ms, mc = m(surf), m(core)
    if ms <= 0.0 and mc <= 0.0:
        return "intact"
    if mc <= 0.0:
        return "surface_dominant"
    if ms <= 0.0:
        return "interior_dominant"
    if ms / mc >= ratio:
        return "surface_dominant"
    if mc / ms >= ratio:
        return "interior_dominant"
    return "uniform"


# --------------------------------------------------------------------------
# csv
# --------------------------------------------------------------------------
CSV_HEADER = ["kind", "step", "phase", "item", "value",
              "x", "y", "z", "basis", "verdict"]


def row(kind, step, phase, item, value, basis, verdict,
        x="", y="", z=""):
    def f(v):
        return "" if v == "" else "%.6g" % v
    return [kind, step, phase, item, f(value), f(x), f(y), f(z),
            basis, verdict]


def write_csv(path, rows):
    """Write the report.  ALWAYS written, even when a section is empty --
    a reader has to be able to see that a phase produced nothing, which is
    different from the script not having run."""
    fh = open(path, "w")
    try:
        fh.write(",".join(CSV_HEADER) + "\n")
        for r in rows:
            out = []
            for c in r:
                c = "" if c is None else str(c)
                if "," in c or '"' in c:
                    c = '"' + c.replace('"', '""') + '"'
                out.append(c)
            fh.write(",".join(out) + "\n")
    finally:
        fh.close()
    return path


# --------------------------------------------------------------------------
# report assembly -- pure, so the selftest can drive it with synthetic points
# --------------------------------------------------------------------------
def build_rows(step_name, per_phase, axis_name, axis, top_n):
    """per_phase: {phase: [(damg, dmode, umatmode, volume, (x,y,z), label)]}"""
    rows = []
    allitems = []

    for phase in sorted(per_phase.keys()):
        pts = per_phase[phase]
        pairs = [(d, w) for d, _m, _u, w, _c, _l in pts]
        st = stats(pairs)
        f50 = volfrac(pairs, 0.50)
        vd = phase_verdict(st, f50)
        spec = PHASES.get(phase.rstrip("0123456789"), None) or \
            PHASES.get(phase, None)
        basis = "max of %s" % "/".join(
            n for _s, n in (spec["mag"] if spec else [])) or "n/a"
        if st is None:
            rows.append(row("phase", step_name, phase, "points", 0,
                            basis, "no_data"))
            continue
        rows.append(row("phase", step_name, phase, "volume_mm3", st["vol"],
                        "sum of IVOL over the phase", vd))
        for k in ("mean", "p50", "p90", "p99", "mx"):
            rows.append(row("phase", step_name, phase,
                            "damg_" + ("max" if k == "mx" else k), st[k],
                            basis, vd))
        for b in D_BINS:
            rows.append(row("phase", step_name, phase,
                            "volfrac_damg_ge_%.2f" % b, volfrac(pairs, b),
                            basis + ", volume-weighted", vd))
        # which mechanism owns the damaged volume
        tally = {}
        for d, m, _u, w, _c, _l in pts:
            if d > 0.0 and m:
                tally[m] = tally.get(m, 0.0) + w
        tot = sum(tally.values())
        for m in sorted(tally, key=lambda k: -tally[k]):
            rows.append(row("phase", step_name, phase,
                            "modefrac_%d_%s" % (m, mode_name(m)),
                            tally[m] / tot if tot > 0 else 0.0,
                            "DMODE %d = %s, volume-weighted"
                            % (m, mode_name(m)), vd))
        allitems += [(d, w, c) for d, _m, _u, w, c, _l in pts]

    # ---- worst elements, ranked, across every phase at once
    flat = []
    for phase in per_phase:
        for d, m, u, w, c, lab in per_phase[phase]:
            flat.append((d, phase, m, u, c, lab))
    flat.sort(key=lambda t: -t[0])
    ncap = sum(1 for t in flat if t[0] >= DMAX_CAP - CAP_TOL)
    for rank, (d, phase, m, u, c, lab) in enumerate(flat[:top_n], 1):
        umat = ""
        if u is not None and m:
            spec = PHASES.get(phase.rstrip("0123456789")) or PHASES.get(phase)
            declared = spec["base"] + int(round(u)) if spec else 0
            # "CONFLICTS", not "DISAGREES": the latter contains "AGREES" as a
            # substring, so anything grepping the csv for agreement matches
            # both.  This bit the selftest before it could bite a reader.
            umat = "; UMAT mode %d %s" % (
                declared, "AGREES" if declared == m else "CONFLICTS")
        rows.append(row("hotspot", step_name, phase,
                        "rank%d_element%s" % (rank, lab), d,
                        "DMODE %d = %s%s" % (m, mode_name(m), umat),
                        hotspot_verdict(d, ncap),
                        x=c[0], y=c[1], z=c[2]))
    rows.append(row("hotspot", step_name, "ALL", "elements_at_cap", ncap,
                    "DAMG >= %.4f, the card's DMAX" % DMAX_CAP,
                    "at_cap_plateau" if ncap > 1 else "single_point"))

    # ---- profile along the chosen axis
    bins, lo, hi = profile(allitems, axis)
    pv = profile_verdict(bins)
    for b in bins:
        rows.append(row("profile", step_name, "ALL",
                        "%s_%03d_%03dpct" % (axis_name,
                                             int(100 * b["frac_lo"]),
                                             int(100 * b["frac_hi"])),
                        b["mean"],
                        "volume-weighted mean DAMG, %s in [%.4g, %.4g] mm"
                        % (axis_name, lo + b["frac_lo"] * (hi - lo),
                           lo + b["frac_hi"] * (hi - lo)),
                        pv))
    return rows


# --------------------------------------------------------------------------
# odb side
# --------------------------------------------------------------------------
def resolve_sdv(frame, slot, name):
    keys = frame.fieldOutputs.keys()
    for cand in ("SDV_%s" % name, "SDV%d" % slot, "SDV_%d" % slot,
                 "SDV%02d" % slot):
        if cand in keys:
            return cand
    return None


def find_regions(odb):
    """{label: (phase, elementSet)} plus the instance.

    An RVE has Matrix + Yarn0..3 element sets; the macro specimen has one set
    called ALL.  Anything else is reported so the user can see what was found
    rather than getting a silent empty report.
    """
    inst = None
    for _n, i in odb.rootAssembly.instances.items():
        if len(i.elements):
            inst = i
            break
    if inst is None:
        sys.exit("no instance with elements in this odb")
    out = []
    for name, es in inst.elementSets.items():
        up = name.upper()
        if up == "MATRIX":
            out.append((name, "Matrix", es))
        elif up.startswith("YARN"):
            out.append((name, "Yarn", es))
        elif up == "ALL":
            out.append((name, "Macro", es))
    return inst, out


def centroids(inst):
    """{element label: (x, y, z)} from the nodal coordinates."""
    nc = {}
    for n in inst.nodes:
        nc[n.label] = n.coordinates
    out = {}
    for e in inst.elements:
        con = e.connectivity
        sx = sy = sz = 0.0
        k = 0
        for lab in con:
            c = nc.get(lab)
            if c is None:
                continue
            sx += c[0]
            sy += c[1]
            sz += c[2]
            k += 1
        if k:
            out[e.label] = (sx / k, sy / k, sz / k)
    return out


def gather(frame, phase, region, cent):
    """Collapse one region of one frame to per-ELEMENT points.

    Integration points inside an element are reduced by MAX, not by average:
    the question is where damage is worst, and averaging 8 points of a C3D8
    hides exactly the localised band that is being looked for.  C3D4 has one
    point, so on the RVE mesh this is a no-op.
    """
    spec = PHASES[phase]
    need = [(s, n) for s, n in spec["mag"]]
    need += [(s, n) for s, n, _i, _l in spec["comp"]]
    need.append(spec["umatmode"])
    fields = {}
    for slot, name in need:
        v = resolve_sdv(frame, slot, name)
        fields[(slot, name)] = v
    ivol = "IVOL" if "IVOL" in frame.fieldOutputs.keys() else None

    acc = {}

    def take(key, col):
        var = fields[key]
        if var is None:
            return
        for v in frame.fieldOutputs[var].getSubset(region=region).values:
            e = acc.setdefault(v.elementLabel, {})
            e[col] = max(e.get(col, 0.0), v.data)

    for k, (slot, name) in enumerate(spec["mag"]):
        take((slot, name), "m%d" % k)
    for k, (slot, name, _i, _l) in enumerate(spec["comp"]):
        take((slot, name), "c%d" % k)
    take(spec["umatmode"], "u")

    vol = {}
    if ivol:
        for v in frame.fieldOutputs[ivol].getSubset(region=region).values:
            vol[v.elementLabel] = vol.get(v.elementLabel, 0.0) + v.data

    pts = []
    nmag = len(spec["mag"])
    ncmp = len(spec["comp"])
    for lab, e in acc.items():
        mag = [e.get("m%d" % k, 0.0) for k in range(nmag)]
        cmp_ = [e.get("c%d" % k, 0.0) for k in range(ncmp)]
        d, m = unify(phase, mag, cmp_)
        pts.append((d, m, e.get("u"), vol.get(lab, 1.0),
                    cent.get(lab, (0.0, 0.0, 0.0)), lab))
    missing = [n for (s, n), v in fields.items() if v is None]
    return pts, sorted(missing)


def inject(frame, inst, labels, damg, dmode, dadd, suffix,
           position=None):
    """Write DAMG / DMODE / DADD into the frame.

    CENTROID by default, not INTEGRATION_POINT, on purpose.  A centroid field
    draws as a quilt -- one flat colour per element -- so the Viewer's default
    nodal averaging cannot smear the peak of a one-element-wide softening band
    into its neighbours.  That averaging is the single most common way a damage
    picture ends up understating its own hot spot.

    `--position integration` is the fallback for a Viewer that will not contour
    a centroid field.  It is only valid where each element has ONE integration
    point, which is true of the RVE's C3D4 tets and false of the macro model's
    C3D8 hexes, so main() refuses it rather than writing eight elements' worth
    of labels for one value.
    """
    made = []
    for name, data, desc in (
            ("DAMG" + suffix, damg,
             "largest fractional stiffness loss, any phase, any mode"),
            ("DMODE" + suffix, dmode,
             "phase and mechanism: 11/12 matrix, 21-24 yarn, 31-34 macro"),
            ("DADD" + suffix, dadd,
             "DAMG above the reference frame")):
        if data is None:
            continue
        if name in frame.fieldOutputs.keys():
            made.append((name, "exists, left alone"))
            continue
        fo = frame.FieldOutput(name=name, description=desc, type=SCALAR)
        fo.addData(position=position or CENTROID, instance=inst,
                   labels=labels, data=[[v] for v in data])
        made.append((name, "written"))
    return made


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("odb", nargs="?")
    ap.add_argument("--axis", default="z", choices=("x", "y", "z"),
                    help="axis for the depth profile (default z, the "
                         "through-thickness direction of both the RVE and "
                         "the quenched macro plate)")
    ap.add_argument("--top", type=int, default=20,
                    help="how many worst elements to list (default 20)")
    ap.add_argument("--ref-step", default=None,
                    help="step whose LAST frame is the reference for DADD "
                         "(default: the first step, i.e. the cooldown)")
    ap.add_argument("--no-write-field", action="store_true",
                    help="do not modify the odb; write the csv only")
    ap.add_argument("--position", default="centroid",
                    choices=("centroid", "integration"),
                    help="where the new fields live.  centroid (default) "
                         "draws as an unaveraged quilt; integration is the "
                         "fallback if the Viewer will not contour a centroid "
                         "field, and is refused on multi-point elements.")
    ap.add_argument("--suffix", default="",
                    help="append to the new field names, to re-run without "
                         "colliding with an earlier pass")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.odb:
        ap.error("give an odb, or --selftest")
    if openOdb is None:
        sys.exit("odbAccess not found -- run this with 'abaqus python', "
                 "not with plain python.")
    if not os.path.exists(a.odb):
        sys.exit("no such file: %s" % a.odb)

    axis = "xyz".index(a.axis)
    write = not a.no_write_field
    pos = INTEGRATION_POINT if a.position == "integration" else CENTROID
    odb = openOdb(a.odb, readOnly=not write)
    inst, regions = find_regions(odb)
    if a.position == "integration":
        multi = sorted(set(e.type for e in inst.elements
                           if not e.type.upper().startswith(("C3D4", "C3D6"))))
        if multi:
            sys.exit("--position integration writes one value per element, "
                     "which is only right where an element has one "
                     "integration point.  This instance holds %s.  Use the "
                     "default centroid position." % ", ".join(multi))
    cent = centroids(inst)

    print("=" * 74)
    print("damage map: %s" % a.odb)
    print("  instance %s   %d elements   %d nodes"
          % (inst.name, len(inst.elements), len(inst.nodes)))
    if not regions:
        print("  !! no Matrix / Yarn* / ALL element set found.  Sets present: "
              "%s" % ", ".join(sorted(inst.elementSets.keys())))
    named = [k for k in (odb.steps[list(odb.steps.keys())[0]].frames[-1]
                         .fieldOutputs.keys()) if k.startswith("SDV_")] \
        if odb.steps and len(odb.steps[list(odb.steps.keys())[0]].frames) \
        else []
    print("  *Depvar entries are %s"
          % ("NAMED (%d SDV_* fields)" % len(named) if named
             else "UNNAMED -- fields are SDV1, SDV2, ...; slot numbers below "
                  "are resolved per phase so this is safe here, but do NOT "
                  "contour a bare SDV number over more than one material"))

    steps = list(odb.steps.keys())
    ref_step = a.ref_step or (steps[0] if steps else None)
    refmap = {}
    if ref_step and ref_step in odb.steps and len(odb.steps[ref_step].frames):
        rf = odb.steps[ref_step].frames[-1]
        for _name, phase, es in regions:
            pts, _ = gather(rf, phase, es, cent)
            for d, _m, _u, _w, _c, lab in pts:
                refmap[lab] = d
        print("  DADD reference: last frame of step '%s'" % ref_step)

    rows = [row("meta", "", "", "odb", "", os.path.abspath(a.odb), "input"),
            row("meta", "", "", "elements", len(inst.elements),
                "instance %s" % inst.name, "input"),
            row("meta", "", "", "depvar_named", 1 if named else 0,
                "SDV_* fields present in the odb", "input"),
            row("meta", "", "", "profile_axis", axis,
                "0=x 1=y 2=z", "input"),
            row("meta", "", "", "dmax_cap", DMAX_CAP,
                "card D_DMAX in abaqus/retune_deck.py", "input")]

    for sname in steps:
        step = odb.steps[sname]
        if not len(step.frames):
            print("\nSTEP %s : no frames" % sname)
            continue
        fr = step.frames[-1]
        done = 100.0 * fr.frameValue / max(step.timePeriod, 1e-30)
        print("\nSTEP %s   %d frames, last at %.5f of %.5f (%.1f %%)"
              % (sname, len(step.frames), fr.frameValue, step.timePeriod,
                 done))
        if done < 99.5:
            print("  *** THIS STEP DID NOT FINISH -- the map below is the "
                  "state at the last CONVERGED increment, which is still "
                  "worth reading ***")
        per_phase = {}
        labels, dv, mv, av = [], [], [], []
        for name, phase, es in regions:
            pts, missing = gather(fr, phase, es, cent)
            if missing:
                print("  %-10s SDV not in this odb: %s"
                      % (name, ", ".join(missing)))
            if not pts:
                continue
            per_phase[name] = pts
            for d, m, _u, _w, _c, lab in pts:
                labels.append(lab)
                dv.append(d)
                mv.append(float(m))
                av.append(d - refmap.get(lab, 0.0))
        if not per_phase:
            print("  no damage state variables readable in this step")
            continue

        rows += build_rows(sname, per_phase, a.axis, axis, a.top)

        for name in sorted(per_phase):
            pairs = [(d, w) for d, _m, _u, w, _c, _l in per_phase[name]]
            st = stats(pairs)
            f50 = volfrac(pairs, 0.5)
            print("  %-10s mean %.4f  p99 %.4f  max %.4f   vol>=0.5 %5.2f %%"
                  "   %s" % (name, st["mean"], st["p99"], st["mx"],
                             100.0 * f50, phase_verdict(st, f50)))
        worst = max((d, n, m, c, l)
                    for n in per_phase
                    for d, m, _u, _w, c, l in per_phase[n])
        print("  worst point: %s element %s  DAMG %.4f  %s  at (%.3f, %.3f, "
              "%.3f) mm" % (worst[1], worst[4], worst[0],
                            mode_name(worst[2]), worst[3][0], worst[3][1],
                            worst[3][2]))
        bins, _lo, _hi = profile(
            [(d, w, c) for n in per_phase
             for d, _m, _u, w, c, _l in per_phase[n]], axis)
        print("  %s-profile: %s   -> %s"
              % (a.axis, " ".join("%.3f" % b["mean"] for b in bins),
                 profile_verdict(bins)))

        if write:
            for nm, what in inject(fr, inst, labels, dv, mv,
                                   av if refmap else None, a.suffix,
                                   position=pos):
                print("  field %-8s %s" % (nm, what))

    if write:
        odb.save()
        print("\n  odb saved with the new fields.  In the Viewer choose "
              "Result > Field Output > DAMG%s." % a.suffix)
    out = os.path.splitext(a.odb)[0] + "_damage_map.csv"
    write_csv(out, rows)
    odb.close()
    print("\n  CSV: %s   <- upload THIS file, not a screen capture" % out)
    print("=" * 74)
    return 0


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def selftest():
    ok, bad = [], []

    def ck(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-64s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("damage_map.py selftest")

    # ---- A. the unification is a common currency
    d, m = unify("Matrix", [0.30, 0.05], [0.30, 0.05])
    ck("matrix takes the larger of DMT/DMC", abs(d - 0.30) < 1e-12 and m == 11,
       "d=%.2f mode=%d" % (d, m))
    d, m = unify("Matrix", [0.05, 0.40], [0.05, 0.40])
    ck("and flips the mode when compression leads", m == 12, "mode=%d" % m)
    d, m = unify("Yarn", [0.10, 0.65], [0.10, 0.0, 0.65, 0.0])
    ck("yarn magnitude comes from DY1/DYT, not the components",
       abs(d - 0.65) < 1e-12 and m == 23, "d=%.2f mode=%d" % (d, m))
    d, m = unify("Macro", [0.0, 0.0], [0.0, 0.0, 0.0, 0.0])
    ck("an undamaged point has mode 0, not a spurious mode 1",
       d == 0.0 and m == 0)
    # DY1 merges DY1T and DY1C, so it can exceed either component.  The
    # magnitude must still come from DY1 -- that is the number that actually
    # multiplies E1.
    d, _ = unify("Yarn", [0.75, 0.0], [0.50, 0.50, 0.0, 0.0])
    ck("a merged DY1 above its own components is kept as the magnitude",
       abs(d - 0.75) < 1e-12, "d=%.3f from DY1, components were 0.50" % d)

    ck("every mode code decodes to a unique name",
       len(set(mode_name(b + i) for b in (10, 20, 30)
               for i in (1, 2, 3, 4) if mode_name(b + i))) == 10,
       "matrix has 2 modes, yarn and macro 4 each")
    ck("an unknown code decodes to blank, not to a wrong name",
       mode_name(99) == "")

    # ---- B. phase verdicts
    lo = [(0.0, 1.0)] * 100
    ck("all-zero damage reads intact", phase_verdict(stats(lo), 0.0)
       == "intact")
    band = [(0.0, 1.0)] * 99 + [(0.95, 1.0)]
    st = stats(band)
    ck("one hot element in 100 reads localised, not distributed",
       phase_verdict(st, volfrac(band, 0.5)) == "localised",
       "volfrac 0.5 = %.3f < %.2f" % (volfrac(band, 0.5),
                                      LOCALISED_MAX_VOLFRAC))
    wide = [(0.6, 1.0)] * 10 + [(0.0, 1.0)] * 90
    ck("ten in a hundred past 0.5 reads distributed",
       phase_verdict(stats(wide), volfrac(wide, 0.5)) == "distributed",
       "volfrac = %.2f" % volfrac(wide, 0.5))
    gone = [(0.8, 1.0)] * 100
    ck("a phase whose MEAN is past 0.5 reads saturated, not distributed",
       phase_verdict(stats(gone), volfrac(gone, 0.5)) == "saturated")
    ck("saturated wins over distributed by order, not by luck",
       volfrac(gone, 0.5) >= LOCALISED_MAX_VOLFRAC,
       "both tests would fire; the code checks saturated first")

    # ---- C. the volume weighting is real
    mixed = [(1.0, 1.0), (0.0, 99.0)]
    ck("the mean is volume-weighted, not point-weighted",
       abs(stats(mixed)["mean"] - 0.01) < 1e-12,
       "%.4f, a point-weighted mean would be 0.5" % stats(mixed)["mean"])
    ck("and so is the volume fraction",
       abs(volfrac(mixed, 0.5) - 0.01) < 1e-12)

    # ---- D. the cap verdict
    ck("an element on the card's DMAX is called out as capped",
       hotspot_verdict(DMAX_CAP, 1) == "at_cap")
    ck("several at the cap are called a plateau, so the ranking is not "
       "over-read", hotspot_verdict(DMAX_CAP, 7) == "at_cap_plateau")
    ck("just below the cap is ordinary softening",
       hotspot_verdict(0.90, 7) == "softening")

    # ---- E. the profile answers surface vs interior
    n = N_PROFILE_BINS
    surf = []
    for k in range(n):
        c = (k + 0.5) / n
        d = 0.9 if (k == 0 or k == n - 1) else 0.02
        surf.append((d, 1.0, (0.0, 0.0, c)))
    bins, lo_, hi_ = profile(surf, 2)
    ck("a two-sided surface band reads surface_dominant",
       profile_verdict(bins) == "surface_dominant",
       "means %s" % " ".join("%.2f" % b["mean"] for b in bins))
    core = [(0.9 if 4 <= k <= 5 else 0.02, 1.0, (0.0, 0.0, (k + 0.5) / n))
            for k in range(n)]
    ck("a mid-thickness band reads interior_dominant",
       profile_verdict(profile(core, 2)[0]) == "interior_dominant")
    flat = [(0.3, 1.0, (0.0, 0.0, (k + 0.5) / n)) for k in range(n)]
    ck("an even field reads uniform",
       profile_verdict(profile(flat, 2)[0]) == "uniform")
    ck("the profile keeps every bin, so a gap shows as n=0",
       len(profile([(0.5, 1.0, (0, 0, 0.05)),
                    (0.5, 1.0, (0, 0, 0.95))], 2)[0]) == n)
    ck("all points on one plane do not divide by zero",
       profile([(0.5, 1.0, (0, 0, 1.0))] * 3, 2)[0][0]["n"] == 3)

    # ---- F. the report itself
    pts_m = [(0.0, 0, 1.0, 1.0, (0.1 * k, 0.0, 0.1 * k), 100 + k)
             for k in range(9)]
    pts_m.append((0.99, 11, 1.0, 1.0, (0.9, 0.0, 0.9), 109))
    # Two yarn points: the first has the UMAT calling mode 1 (longitudinal
    # tension is the largest CRITERION) while the largest DAMAGE is transverse
    # -- a point that changed mode partway through.  The second agrees.
    pts_y = [(0.40, 23, 1.0, 2.0, (0.5, 0.5, 0.5), 200),
             (0.20, 21, 1.0, 2.0, (0.6, 0.5, 0.5), 201)]
    rows = build_rows("TENSION", {"Matrix": pts_m, "Yarn0": pts_y},
                      "z", 2, 5)
    kinds = set(r[0] for r in rows)
    ck("the report carries all three sections",
       kinds == set(("phase", "hotspot", "profile")), "%s" % sorted(kinds))
    ck("every row has the full schema",
       all(len(r) == len(CSV_HEADER) for r in rows),
       "%d columns" % len(CSV_HEADER))
    ck("every row carries a basis and a verdict, per CLAUDE.md 3-2",
       all(r[8] and r[9] for r in rows))
    hot = [r for r in rows if r[0] == "hotspot" and r[3].startswith("rank1")]
    ck("the worst element is ranked first across ALL phases at once",
       len(hot) == 1 and hot[0][2] == "Matrix" and "109" in hot[0][3],
       hot[0][3] if hot else "none")
    ck("and it carries its coordinates, so 'where' is answerable",
       hot and hot[0][5] and hot[0][6] != "" and hot[0][7])
    dis = [r for r in rows if "CONFLICTS" in r[8]]
    agr = [r for r in rows if "AGREES" in r[8]]
    ck("a point whose UMAT mode contradicts its biggest damage is flagged",
       len(dis) == 1 and "element200" in dis[0][3], "%d row(s)" % len(dis))
    ck("and a point where they match is marked as agreeing, not left blank",
       len(agr) == 2 and any("element201" in r[3] for r in agr),
       "%d row(s)" % len(agr))
    ck("a phase with one capped element does not read as a plateau",
       any(r[3] == "elements_at_cap" and r[4] == "1" for r in rows))
    ck("the yarn row names DY1/DYT as its basis, not DMT",
       any(r[2] == "Yarn0" and "DY1/DYT" in r[8] for r in rows))

    import tempfile
    p = os.path.join(tempfile.mkdtemp(), "t_damage_map.csv")
    write_csv(p, rows)
    txt = open(p).read().splitlines()
    ck("the csv survives commas inside the basis column",
       len(txt) == len(rows) + 1 and all(
           len(_split_csv(l)) == len(CSV_HEADER) for l in txt),
       "%d lines" % len(txt))
    ck("the header is the documented schema",
       txt[0] == ",".join(CSV_HEADER))

    # ---- G. the trap this file exists for
    ck("SDV9 really does mean different things per phase",
       dict(PHASES["Matrix"]["mag"] + PHASES["Matrix"]["comp"] and
            [(s, n) for s, n in PHASES["Matrix"]["mag"]]).get(9) is None
       and dict(PHASES["Yarn"]["mag"]).get(9) == "DY1",
       "matrix slot 9 is EQPS and is deliberately NOT in the matrix table")
    # ---- H. the odb-side behaviour, which no test here can exercise.
    # These pin the SOURCE instead: the fallback must stay optional, and the
    # guard that makes it safe must stay attached to it.
    src = open(__file__).read()
    ck("centroid is the position used when nothing is asked for",
       'default="centroid"' in src)
    ck("the integration fallback is refused on multi-point elements",
       "C3D4" in src.split("multi = ")[1][:220]
       and "sys.exit" in src.split("multi = ")[1][:600],
       "the guard names the one-point element types and stops the run")

    ck("no phase reuses another phase's DMODE codes",
       len(set(PHASES[p]["base"] + i
               for p in PHASES for _s, _n, i, _l in PHASES[p]["comp"]))
       == sum(len(PHASES[p]["comp"]) for p in PHASES))

    print("\n  %d passed, %d failed" % (len(ok), len(bad)))
    if bad:
        for b in bad:
            print("  FAILED: %s" % b)
        return 1
    return 0


def _split_csv(line):
    out, cur, q = [], "", False
    i = 0
    while i < len(line):
        c = line[i]
        if q:
            if c == '"' and i + 1 < len(line) and line[i + 1] == '"':
                cur += '"'
                i += 1
            elif c == '"':
                q = False
            else:
                cur += c
        else:
            if c == '"':
                q = True
            elif c == ",":
                out.append(cur)
                cur = ""
            else:
                cur += c
        i += 1
    out.append(cur)
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
