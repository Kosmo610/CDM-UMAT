# -*- coding: utf-8 -*-
"""
damage_census.py -- what state is the RVE actually in?

RUN INSIDE ABAQUS (it needs odbAccess):

    abaqus python damage_census.py <job.odb>

Works on a PARTIAL odb.  Abaqus writes every converged increment, so a job that
died still has everything up to the last converged one -- which is exactly what
you want to look at after a failed run.  Nothing here needs the job to have
finished.

For every step in the odb it reports, at the last available frame:

  * the volume-weighted mean and the distribution of the damage criterion r
    (SDV3 = RMT for the matrix, SDV5..8 for the yarn).  r >= 1 means that
    integration point is ON the softening branch.
  * the same for the damage variable itself (SDV1 = DMT, SDV5 = DMACT).
  * the volume fraction of each phase that is over r = 1, and over
    d = 0.1 / 0.5 / 0.9.
  * the volume-averaged stress in each phase -- the number to compare with the
    XRD thermal-residual-stress measurement in refs/[15].

Why this matters: the M1 post-mortem predicted from a mean-field estimate that
the matrix leaves the 1050 -> 23 C cooldown at r = 0.97, i.e. with almost no
margin left before it starts softening.  This script measures the real number.
"""
from __future__ import print_function

import sys
import os

try:
    from odbAccess import openOdb
except ImportError:
    sys.exit("odbAccess not found -- run this with 'abaqus python', "
             "not with plain python.")

# SDV slots, from the *Depvar block in the deck
MATRIX_SDV = [("SDV1", "DMT   matrix tensile damage", "d"),
              ("SDV3", "RMT   matrix tensile criterion", "r"),
              ("SDV5", "DMACT active matrix damage", "d"),
              ("SDV9", "EQPS  equivalent plastic strain", "p")]
YARN_SDV = [("SDV9", "DY1   combined longitudinal damage", "d"),
            ("SDV10", "DYT   combined transverse damage", "d"),
            ("SDV5", "RY1T  longitudinal tensile criterion", "r"),
            ("SDV7", "RYTT  transverse tensile criterion", "r")]

D_BINS = (0.01, 0.1, 0.5, 0.9)
R_BINS = (0.5, 0.8, 1.0, 1.5, 2.0)


def find_sets(odb):
    """Return {label: elementSet} for Matrix and the yarns, plus the instance."""
    inst = None
    for name, i in odb.rootAssembly.instances.items():
        if len(i.elements):
            inst = i
            break
    if inst is None:
        sys.exit("no instance with elements in this odb")
    sets = {}
    for name, es in inst.elementSets.items():
        up = name.upper()
        if up == "MATRIX":
            sets["Matrix"] = es
        elif up.startswith("YARN"):
            sets.setdefault("Yarn", []).append(es)
    return inst, sets


def collect(frame, region, var):
    """[(value, volume)] for one scalar field over one region."""
    try:
        fo = frame.fieldOutputs[var]
    except KeyError:
        return None
    try:
        ivol = frame.fieldOutputs["IVOL"]
    except KeyError:
        ivol = None
    sub = fo.getSubset(region=region)
    vals = [(v.data, v.elementLabel, v.integrationPoint) for v in sub.values]
    if ivol is None:
        return [(d, 1.0) for d, _, _ in vals]
    vsub = ivol.getSubset(region=region)
    vmap = {}
    for v in vsub.values:
        vmap[(v.elementLabel, v.integrationPoint)] = v.data
    out = []
    for d, el, ip in vals:
        out.append((d, vmap.get((el, ip), 1.0)))
    return out


def stats(pairs):
    tot = sum(w for _, w in pairs)
    if tot <= 0.0:
        return None
    mean = sum(d * w for d, w in pairs) / tot
    ds = sorted(d for d, _ in pairs)
    n = len(ds)

    def q(f):
        return ds[min(n - 1, int(f * n))]
    return dict(mean=mean, vol=tot, n=n, mn=ds[0], mx=ds[-1],
                p50=q(0.50), p90=q(0.90), p99=q(0.99))


def frac_over(pairs, thr):
    tot = sum(w for _, w in pairs)
    if tot <= 0.0:
        return 0.0
    return sum(w for d, w in pairs if d >= thr) / tot


def mean_stress(frame, region):
    try:
        fo = frame.fieldOutputs["S"]
    except KeyError:
        return None
    try:
        ivol = frame.fieldOutputs["IVOL"]
    except KeyError:
        ivol = None
    sub = fo.getSubset(region=region)
    vmap = {}
    if ivol is not None:
        for v in ivol.getSubset(region=region).values:
            vmap[(v.elementLabel, v.integrationPoint)] = v.data
    acc = [0.0] * 6
    tot = 0.0
    for v in sub.values:
        w = vmap.get((v.elementLabel, v.integrationPoint), 1.0)
        for k in range(6):
            acc[k] += v.data[k] * w
        tot += w
    if tot <= 0.0:
        return None
    return [a / tot for a in acc], tot


def report_region(frame, label, region, sdvlist):
    print("  --- %s" % label)
    ms = mean_stress(frame, region)
    if ms:
        s, vol = ms
        i1 = s[0] + s[1] + s[2]
        print("      volume %.4f mm^3   volume-averaged stress [MPa]" % vol)
        print("        S11 %+9.2f  S22 %+9.2f  S33 %+9.2f" % (s[0], s[1], s[2]))
        print("        S12 %+9.2f  S13 %+9.2f  S23 %+9.2f" % (s[3], s[4], s[5]))
        print("        I1  %+9.2f   (sign of I1 selects tension vs "
              "compression damage in the matrix)" % i1)
    for var, name, kind in sdvlist:
        pairs = collect(frame, region, var)
        if not pairs:
            print("      %-6s %s : not in this odb" % (var, name))
            continue
        st = stats(pairs)
        print("      %-6s %s" % (var, name))
        print("        mean %.4f  p50 %.4f  p90 %.4f  p99 %.4f  max %.4f"
              % (st["mean"], st["p50"], st["p90"], st["p99"], st["mx"]))
        bins = R_BINS if kind == "r" else D_BINS
        if kind == "p":
            continue
        txt = "  ".join("%s>=%.2f: %5.1f%%"
                        % (kind, b, 100.0 * frac_over(pairs, b)) for b in bins)
        print("        volume fraction   %s" % txt)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: abaqus python damage_census.py <job.odb>")
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit("no such file: %s" % path)
    odb = openOdb(path, readOnly=True)
    inst, sets = find_sets(odb)
    print("=" * 72)
    print("damage census: %s" % path)
    print("  instance %s   %d elements   %d nodes"
          % (inst.name, len(inst.elements), len(inst.nodes)))

    for sname in odb.steps.keys():
        step = odb.steps[sname]
        nf = len(step.frames)
        if nf == 0:
            print("\nSTEP %s : no frames written" % sname)
            continue
        fr = step.frames[-1]
        done = 100.0 * fr.frameValue / max(step.timePeriod, 1e-30)
        print("\nSTEP %s   %d frames, last at step time %.5f of %.5f "
              "(%.1f %% of the step)"
              % (sname, nf, fr.frameValue, step.timePeriod, done))
        if done < 99.5:
            print("  *** THIS STEP DID NOT FINISH ***")
        if "Matrix" in sets:
            report_region(fr, "Matrix", sets["Matrix"], MATRIX_SDV)
        for k, es in enumerate(sets.get("Yarn", [])):
            report_region(fr, "Yarn%d" % k, es, YARN_SDV)

        # driver reaction, if the history is there
        for rname in step.historyRegions.keys():
            hr = step.historyRegions[rname]
            if "RF1" in hr.historyOutputs and "U1" in hr.historyOutputs:
                u = hr.historyOutputs["U1"].data[-1]
                rf = hr.historyOutputs["RF1"].data[-1]
                if abs(u[1]) > 1e-12 or abs(rf[1]) > 1e-12:
                    print("  driver %-22s U1 = %.6e   RF1 = %.6e"
                          % (rname, u[1], rf[1]))
    odb.close()
    print("=" * 72)


if __name__ == "__main__":
    main()
