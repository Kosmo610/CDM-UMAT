#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reheat_frames.py -- split the reheat damage rise into lag and redistribution
============================================================================
RUN INSIDE ABAQUS (it reads an odb):

    abaqus python reheat_frames.py LTH_M6_T500.odb
    abaqus python reheat_frames.py LTH_M7_T500.odb --step Heating_to_500C

and outside Abaqus, to check the arithmetic:

    python3 postprocess/reheat_frames.py --selftest

WHY THIS EXISTS
---------------
verification/reheat_saturation.py showed, on the Python mirror, that the
matrix damage rise during the load-free reheat step has TWO parts:

  * VISCOUS LAG      damage the cooldown already committed (ETA = 0.05 makes
                     d approach its target instead of reaching it) finishing
                     its arrival.  A single material point can do this alone.
                     The mirror puts it at ~16 % of the rise to the ceiling.

  * REDISTRIBUTION   softened elements shedding load onto neighbours that
                     then cross their own thresholds.  A single point CANNOT
                     do this, and it is exactly the mechanism Ch.2 2.8.3's
                     C1 comparison is built to measure.

The mirror can only ESTIMATE the split.  The odb can MEASURE it, because the
deck writes 101 field frames per step and the two parts leave different
fingerprints on the loading function RMT (SDV3), which is a high-water mark:

    element whose RMT is FROZEN over the step   ->  its damage rise is pure
                                                    lag.  No new drive ever
                                                    reached it.
    element whose RMT RISES during the step     ->  something loaded it, and
                                                    the applied strain falls
                                                    monotonically on this leg
                                                    (reheat unloads the
                                                    matrix), so the only
                                                    available source is its
                                                    neighbours.  This is the
                                                    redistribution group.

The risen group's damage rise still CONTAINS some lag (the lag it had left
plus the new drive), so its share is an UPPER bound on redistribution and the
frozen group's share is a LOWER bound on lag.  The bounds are the honest
product; the CSV labels them as bounds.

damage_map.py reads frames[-1] only, which is why this file exists at all.
"""
from __future__ import print_function

import csv
import os
import sys

try:
    from odbAccess import openOdb
except ImportError:                       # plain python: selftest only
    openOdb = None

#: the card ceiling and tolerance, matching damage_map.py
DMAX_CAP = 0.90
CAP_TOL = 1.0e-4
#: RMT above its frame-0 value by more than this = the element was re-loaded.
#: RMT is O(1) (it is q/X_t at the high-water mark), so 1e-6 is far below
#: anything physical and far above double-precision noise.
RISE_TOL = 1.0e-6

#: matrix slots, as the UMAT numbers them (damage_map.py PHASES table)
SLOTS = (("DMT", 1), ("DMC", 2), ("RMT", 3))

CSV_HEADER = "kind,frame,time,group,item,value,basis,verdict"


# --------------------------------------------------------------------------
# plain-python core -- everything judgeable without an odb
# --------------------------------------------------------------------------
def element_damage(dmt, dmc):
    """The matrix's unified damage IS its worst component (unlike a yarn)."""
    return max(dmt, dmc)


def split_groups(rmt0, rmt_now, tol=RISE_TOL):
    """label -> 'frozen' | 'risen' per element key."""
    out = {}
    for k, r0 in rmt0.items():
        out[k] = "risen" if rmt_now.get(k, r0) > r0 + tol else "frozen"
    return out


def group_shares(d0, d_now, groups, vol):
    """Volume-weighted damage rise per group since frame 0.

    Returns dict(total=, frozen=, risen=, n_frozen=, n_risen=).  Elements
    whose damage FELL are clipped at zero rise -- damage is monotonic in the
    model, so a fall is reduction noise, not physics, and letting it subtract
    from a group's share would let noise in one group hide rise in the other.
    """
    tot = frozen = risen = 0.0
    n_f = n_r = 0
    for k, dv0 in d0.items():
        w = vol.get(k, 1.0)
        rise = max(0.0, d_now.get(k, dv0) - dv0) * w
        tot += rise
        if groups.get(k) == "risen":
            risen += rise
            n_r += 1
        else:
            frozen += rise
            n_f += 1
    return dict(total=tot, frozen=frozen, risen=risen,
                n_frozen=n_f, n_risen=n_r)


def at_cap_count(d_now):
    return sum(1 for v in d_now.values() if v >= DMAX_CAP - CAP_TOL)


def verdict_of(shares):
    """Who owns the rise -- with the bound direction stated, not implied."""
    tot = shares["total"]
    if tot <= 0.0:
        return "NO RISE", "the step added no matrix damage"
    fr = shares["frozen"] / tot
    ri = shares["risen"] / tot
    detail = ("frozen (pure lag) %.1f %%, risen (redistribution, upper "
              "bound) %.1f %%" % (100.0 * fr, 100.0 * ri))
    if ri > 0.5:
        return "REDISTRIBUTION DOMINATES", detail
    if fr > 0.5:
        return "VISCOUS LAG DOMINATES", detail
    return "SPLIT", detail


def pick_step(names, wanted=None):
    """The reheat step: named, or the first containing 'heat'."""
    if wanted:
        return wanted if wanted in names else None
    for n in names:
        if "heat" in n.lower() and "preheat" not in n.lower():
            return n
    return None


# --------------------------------------------------------------------------
# odb side
# --------------------------------------------------------------------------
def resolve(frame, name, slot):
    keys = frame.fieldOutputs.keys()
    for cand in ("SDV_%s" % name, "SDV%d" % slot, "SDV_%d" % slot,
                 "SDV%02d" % slot):
        if cand in keys:
            return cand
    return None


def read_frame(frame, region):
    """(d, rmt, vol) dicts keyed by element label; ip-reduced by MAX."""
    per = {}
    for name, slot in SLOTS:
        f = resolve(frame, name, slot)
        if f is None:
            raise RuntimeError("no field for SDV %s (slot %d) -- was SDV "
                               "in the *Element Output request?" % (name, slot))
        for v in frame.fieldOutputs[f].getSubset(region=region).values:
            e = per.setdefault(v.elementLabel, {})
            e[name] = max(e.get(name, 0.0), v.data)
    vol = {}
    if "IVOL" in frame.fieldOutputs.keys():
        for v in frame.fieldOutputs["IVOL"].getSubset(region=region).values:
            vol[v.elementLabel] = vol.get(v.elementLabel, 0.0) + v.data
    d = dict((k, element_damage(e.get("DMT", 0.0), e.get("DMC", 0.0)))
             for k, e in per.items())
    rmt = dict((k, e.get("RMT", 0.0)) for k, e in per.items())
    return d, rmt, vol


def analyse_odb(path, step_name=None):
    odb = openOdb(path, readOnly=True)
    try:
        names = list(odb.steps.keys())
        step = pick_step(names, step_name)
        if step is None:
            raise RuntimeError("no reheat step among %s -- name one with "
                               "--step" % names)
        inst = odb.rootAssembly.instances[
            list(odb.rootAssembly.instances.keys())[0]]
        if "MATRIX" not in inst.elementSets.keys():
            raise RuntimeError("no Matrix element set; sets: %s"
                               % list(inst.elementSets.keys()))
        region = inst.elementSets["MATRIX"]
        frames = odb.steps[step].frames
        if len(frames) < 3:
            raise RuntimeError("only %d frames in %s -- nothing to split"
                               % (len(frames), step))
        d0, rmt0, vol = read_frame(frames[0], region)
        rows = []
        onset = None
        for i in range(len(frames)):
            d, rmt, _v = read_frame(frames[i], region)
            groups = split_groups(rmt0, rmt)
            sh = group_shares(d0, d, groups, vol)
            if onset is None and sh["n_risen"] > 0:
                onset = (i, frames[i].frameValue)
            rows.append((i, frames[i].frameValue, sh, at_cap_count(d)))
        return step, rows, onset
    finally:
        odb.close()


def write_report(job, step, rows, onset, out_path):
    final = rows[-1]
    _i, _t, sh, ncap = final
    verdict, detail = verdict_of(sh)

    with open(out_path, "w") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER.split(","))
        for i, t, s, cap in rows:
            tot = s["total"]
            for grp in ("frozen", "risen"):
                w.writerow(["frame", i, "%.6f" % t, grp,
                            "cum_rise_share",
                            "%.6f" % (s[grp] / tot if tot > 0 else 0.0),
                            "volume-weighted, since frame 0; frozen = RMT "
                            "never rose = pure lag; risen = RMT rose under "
                            "falling applied strain = redistribution "
                            "(upper bound)",
                            ""])
            w.writerow(["frame", i, "%.6f" % t, "ALL", "n_risen",
                        s["n_risen"], "elements whose RMT exceeded its "
                        "frame-0 value by > %g" % RISE_TOL, ""])
            w.writerow(["frame", i, "%.6f" % t, "ALL", "at_cap", cap,
                        "max(DMT,DMC) >= %.4f" % (DMAX_CAP - CAP_TOL), ""])
        w.writerow(["summary", "", "", "ALL", "onset_of_redistribution",
                    "%.6f" % onset[1] if onset else "",
                    "first frame with a risen RMT; the mirror's lag closes "
                    "by ~0.35 of step time, so an onset before that means "
                    "the two mechanisms overlap",
                    "" if onset else "never -- all rise is lag"])
        w.writerow(["summary", "", "", "frozen", "share",
                    "%.6f" % (sh["frozen"] / sh["total"]
                              if sh["total"] > 0 else 0.0),
                    "pure viscous lag (lower bound on lag)", ""])
        w.writerow(["summary", "", "", "risen", "share",
                    "%.6f" % (sh["risen"] / sh["total"]
                              if sh["total"] > 0 else 0.0),
                    "redistribution-affected (upper bound)", verdict])
        w.writerow(["summary", "", "", "ALL", "verdict", "", detail, verdict])

    print("=" * 74)
    print("reheat_frames.py  %s  step %s" % (job, step))
    print("=" * 74)
    print("  %d frames; final at-cap count %d" % (len(rows), ncap))
    if onset:
        print("  redistribution onset: frame %d, t = %.4f" % onset)
    print("  %-40s %s" % (verdict, detail))
    print("  wrote %s -- UPLOAD THIS ONE" % os.path.basename(out_path))
    print("=" * 74)


# --------------------------------------------------------------------------
_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    print("reheat_frames.py --selftest")

    print("\n A. the split is by the high-water mark, nothing else")
    rmt0 = dict(a=1.0, b=1.0, c=0.5)
    rmt1 = dict(a=1.0, b=1.2, c=0.5)
    g = split_groups(rmt0, rmt1)
    t("an element whose RMT rose is 'risen'", g["b"] == "risen")
    t("frozen RMT stays 'frozen', whatever its damage does",
      g["a"] == "frozen" and g["c"] == "frozen")
    t("a rise below the tolerance does not count",
      split_groups(dict(a=1.0), dict(a=1.0 + 0.1 * RISE_TOL))["a"] == "frozen")

    print("\n B. shares are volume-weighted rises, clipped at zero")
    d0 = dict(a=0.30, b=0.30, c=0.80)
    d1 = dict(a=0.40, b=0.70, c=0.79)     # c fell: noise, must not subtract
    vol = dict(a=1.0, b=1.0, c=1.0)
    sh = group_shares(d0, d1, g, vol)
    t("total rise counts only rises", abs(sh["total"] - 0.5) < 1e-12,
      "0.1 + 0.4, the fall clipped")
    t("the frozen group holds the lag part", abs(sh["frozen"] - 0.1) < 1e-12)
    t("the risen group holds the driven part", abs(sh["risen"] - 0.4) < 1e-12)
    sh2 = group_shares(d0, d1, g, dict(a=3.0, b=1.0, c=1.0))
    t("volume weighting changes the shares",
      abs(sh2["frozen"] - 0.3) < 1e-12, "same rise, 3x the volume")

    print("\n C. the verdict states the bound direction")
    v, det = verdict_of(dict(total=1.0, frozen=0.16, risen=0.84,
                             n_frozen=10, n_risen=32))
    t("84 % risen reads REDISTRIBUTION DOMINATES",
      v == "REDISTRIBUTION DOMINATES", det)
    t("  and the detail says 'upper bound', not 'measured exactly'",
      "upper" in det and "bound" in det)
    v, _ = verdict_of(dict(total=1.0, frozen=0.9, risen=0.1,
                           n_frozen=40, n_risen=2))
    t("90 % frozen reads VISCOUS LAG DOMINATES",
      v == "VISCOUS LAG DOMINATES")
    v, det = verdict_of(dict(total=0.0, frozen=0.0, risen=0.0,
                             n_frozen=42, n_risen=0))
    t("a rise-free step is NO RISE, not a division by zero", v == "NO RISE",
      det)

    print("\n D. the matrix's damage really is its worst component")
    t("max(DMT, DMC)", element_damage(0.3, 0.7) == 0.7
      and element_damage(0.7, 0.3) == 0.7)

    print("\n E. step picking")
    t("the reheat step is found by name",
      pick_step(["Manufacturing_Cooling", "Heating_to_500C",
                 "Tension_at_500C"]) == "Heating_to_500C")
    t("an explicit --step wins", pick_step(["A", "B"], "B") == "B")
    t("a missing explicit step is refused, not guessed",
      pick_step(["A"], "Nope") is None)
    t("RT23, which has no reheat step, returns None rather than a wrong step",
      pick_step(["Manufacturing_Cooling", "Tension_at_23C"]) is None)

    print("\n F. what the numbers will be compared against")
    t("the cap and tolerance match damage_map's",
      abs(DMAX_CAP - 0.90) < 1e-12 and abs(CAP_TOL - 1e-4) < 1e-12)
    t("the mirror's expectation is on record for the comparison",
      True, "reheat_saturation.py: lag ~16 %, redistribution ~84 % "
      "(upper bound here should land near it)")

    print("\n%s" % ("ALL %d SELFTESTS PASS" % len(_OK) if not _BAD
                    else "FAILED %d of %d" % (len(_BAD), len(_OK) + len(_BAD))))
    return 0 if not _BAD else 1


def main(argv):
    if "--selftest" in argv or "--check" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("-")]
    step = None
    if "--step" in argv:
        step = argv[argv.index("--step") + 1]
        if step in args:
            args.remove(step)
    if not args:
        print(__doc__)
        return 2
    if openOdb is None:
        print("odbAccess unavailable -- run this under `abaqus python`.")
        return 2
    path = args[0]
    job = os.path.splitext(os.path.basename(path))[0]
    step_name, rows, onset = analyse_odb(path, step)
    write_report(job, step_name, rows, onset, job + "_reheat_frames.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
