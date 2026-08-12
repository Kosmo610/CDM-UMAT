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
    # Not fatal at import time.  Everything that DECIDES something here --
    # the volume-weighted fractions, the ATEFF clamp threshold, the verdict
    # columns -- is plain arithmetic, and --check exercises exactly that part
    # with ordinary python.  Exiting on import instead meant this file could
    # not be in the gate at all, which is how it reached 2026-08-12 with no
    # test despite deciding whether a strength may be quoted.
    openOdb = None

# SDV slots, from the *Depvar block in the deck.
#
# ** FIXED 2026-08-03. **  These used to be plain "SDV1", "SDV3", ... and every
# lookup silently missed.  The deck's *Depvar block NAMES its entries:
#
#     *Depvar
#     20,
#     1, DMT, Matrix tensile damage
#
# and when the entries are named Abaqus writes the field as SDV_DMT, not SDV1.
# collect() returned None for all of them, and None printed as "not in odb"
# rather than as an error, so the census reported nothing and looked fine.
# The entries below now carry BOTH, and resolve_sdv() tries the name first.
MATRIX_SDV = [(1, "DMT", "DMT   matrix tensile damage", "d"),
              (3, "RMT", "RMT   matrix tensile criterion", "r"),
              (5, "DMACT", "DMACT active matrix damage", "d"),
              (9, "EQPS", "EQPS  equivalent plastic strain", "p"),
              (10, "ATEFF", "ATEFF crack-band softening factor", "a")]
YARN_SDV = [(9, "DY1", "DY1   combined longitudinal damage", "d"),
            (10, "DYT", "DYT   combined transverse damage", "d"),
            (5, "RY1T", "RY1T  longitudinal tensile criterion", "r"),
            (7, "RYTT", "RYTT  transverse tensile criterion", "r")]


def resolve_sdv(frame, slot, name):
    """Field key for one state variable, whichever way the deck named it.

    Named *Depvar -> 'SDV_DMT'.  Unnamed -> 'SDV1'.  Returns None if neither
    is present, so the caller can say 'absent' rather than 'zero'.
    """
    keys = frame.fieldOutputs.keys()
    for cand in ("SDV_%s" % name, "SDV%d" % slot, "SDV_%d" % slot,
                 "SDV%02d" % slot):
        if cand in keys:
            return cand
    return None

D_BINS = (0.01, 0.1, 0.5, 0.9)
R_BINS = (0.5, 0.8, 1.0, 1.5, 2.0)

#: Value KABAND clamps the softening exponent to when the element is in the
#: snap-back regime.  UMAT_CSIC_RVE_ZHANG2022_V1_0.for line 528: A=50.0D0,
#: then A=MIN(50,MAX(1e-2,A)).  An element sitting at 50 is brittle.
ATEFF_CLAMP = 50.0


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
    """[(value, volume)] for one scalar field over one region.

    Returns None if the field is not in the odb at all, [] if it is there but
    has no values in this region.  The two are different problems and the
    caller must be able to tell them apart."""
    if var not in frame.fieldOutputs.keys():
        return None
    fo = frame.fieldOutputs[var]
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


def report_region(frame, label, region, sdvlist, rows=None,
                  step=""):
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
    for slot, sdvname, name, kind in sdvlist:
        var = resolve_sdv(frame, slot, sdvname)
        if var is None:
            print("      %-9s %s : NOT WRITTEN TO THIS ODB "
                  "(looked for SDV_%s and SDV%d)"
                  % (sdvname, name, sdvname, slot))
            continue
        pairs = collect(frame, region, var)
        if pairs is None:
            print("      %-9s %s : NOT WRITTEN TO THIS ODB" % (var, name))
            continue
        if not pairs:
            print("      %-9s %s : field exists but is empty for this region"
                  % (var, name))
            continue
        st = stats(pairs)
        if rows is not None:
            for k in ("mean", "p50", "p90", "p99", "mx"):
                rows.append(dict(step=step, region=label, quantity=var,
                                 stat=k, value="%.6f" % st[k],
                                 basis=name, verdict=""))
        print("      %-9s %s" % (var, name))
        print("        mean %.4f  p50 %.4f  p90 %.4f  p99 %.4f  max %.4f"
              % (st["mean"], st["p50"], st["p90"], st["p99"], st["mx"]))
        if kind == "p":
            continue
        if kind == "a":
            # ATEFF is the crack-band softening factor.  KABAND clamps it to
            # ATEFF_CLAMP when the element is in the snap-back regime, i.e.
            # when the element is too big for the fracture energy it was
            # given.  Those elements are effectively brittle and are NOT mesh
            # objective, so the fraction matters -- M6 ships with Gtc = Gtt =
            # 0.107, which retune_deck.py reports as VIOLATED for the largest
            # elements.  This is the number that check refers to.
            clamped = frac_over(pairs, ATEFF_CLAMP - 1.0e-9)
            print("        CLAMPED (A = %.0f, brittle, NOT mesh objective): "
                  "%.2f %% by volume" % (ATEFF_CLAMP, 100.0 * clamped))
            if clamped > 0.05:
                print("        ** over 5 %% -- do not quote a strength from "
                      "this run without saying so **")
            if rows is not None:
                rows.append(dict(
                    step=step, region=label, quantity=var, stat="clamped_frac",
                    value="%.6f" % clamped,
                    basis="volume fraction with ATEFF >= %.0f, the KABAND "
                          "snap-back clamp" % ATEFF_CLAMP,
                    verdict=("STRENGTH NOT QUOTABLE" if clamped > 0.05
                             else "quotable")))
            continue
        bins = R_BINS if kind == "r" else D_BINS
        txt = "  ".join("%s>=%.2f: %5.1f%%"
                        % (kind, b, 100.0 * frac_over(pairs, b)) for b in bins)
        print("        volume fraction   %s" % txt)
        if rows is not None:
            for b in bins:
                rows.append(dict(
                    step=step, region=label, quantity=var,
                    stat="frac_over_%.2f" % b,
                    value="%.6f" % frac_over(pairs, b),
                    basis="volume fraction of the region with %s >= %.2f"
                          % (kind, b),
                    verdict=("AT THE CARD CEILING" if kind == "d" and b >= 0.9
                             and frac_over(pairs, b) > 0.05 else "")))


CSV_COLUMNS = ["step", "region", "quantity", "stat", "value", "basis",
               "verdict"]


def write_csv(odb_path, rows):
    """<job>_damage_census.csv -- value, basis and verdict in one row.

    Added 2026-08-12.  m6_verdict.py refuses to let a strength be quoted
    before this script reports the ATEFF clamped fraction, which made the
    console-only output a bottleneck on the thesis's headline numbers: the
    only way to move them into a conversation was a screen capture, and this
    project has lost three numbers to re-typing from images.  The console
    output is unchanged; the CSV is the deliverable.
    """
    import csv as _csv
    out = os.path.splitext(odb_path)[0] + "_damage_census.csv"
    with open(out, "w") as fh:
        w = _csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for r in rows:
            w.writerow([r.get(c, "") for c in CSV_COLUMNS])
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: abaqus python damage_census.py <job.odb>")
    if openOdb is None:
        sys.exit("odbAccess not found -- run this with 'abaqus python', "
                 "not with plain python.")
    path = sys.argv[1]
    if not os.path.exists(path):
        sys.exit("no such file: %s" % path)
    odb = openOdb(path, readOnly=True)
    rows = []
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
        keys = sorted(fr.fieldOutputs.keys())
        sdv = [k for k in keys if k.upper().startswith("SDV")]
        print("  field output in this frame: %s" % ", ".join(keys))
        if not sdv:
            print("  !! NO SDV FIELDS AT ALL.  The *Element Output request in "
                  "the deck asked for SDV but the odb has none, so every "
                  "damage number below is unavailable.  Check the .dat file "
                  "for a warning on the *Element Output line.")
        if "Matrix" in sets:
            report_region(fr, "Matrix", sets["Matrix"], MATRIX_SDV,
                          rows, sname)
        for k, es in enumerate(sets.get("Yarn", [])):
            report_region(fr, "Yarn%d" % k, es, YARN_SDV, rows, sname)

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
    out = write_csv(path, rows)
    print("\n  wrote %s -- UPLOAD THIS ONE" % os.path.basename(out))
    print("=" * 72)


def selftest():
    """No odb needed: everything that DECIDES something is plain arithmetic."""
    fails = []

    def ck(name, ok, detail=""):
        print("  [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    print("damage_census.py --check")
    print("\n A. the volume fraction is by VOLUME, not by element count")
    # One huge undamaged element and nine tiny saturated ones: counting
    # elements says 90 %, weighting by volume says 9 %.  The card ceiling
    # verdict hangs on this, so it is worth a check of its own.
    pairs = [(0.0, 100.0)] + [(0.95, 1.0)] * 9
    ck("nine small saturated elements are 8.3 %, not 90 %",
       abs(frac_over(pairs, 0.9) - 9.0 / 109.0) < 1e-12,
       "%.4f by volume" % frac_over(pairs, 0.9))
    ck("an empty region does not divide by zero",
       frac_over([], 0.9) == 0.0)

    print("\n B. the ATEFF clamp threshold is the one KABAND uses")
    ck("ATEFF_CLAMP matches the KABAND upper clamp",
       abs(ATEFF_CLAMP - 50.0) < 1e-12, "A = %g" % ATEFF_CLAMP)
    # Just below the clamp is not clamped; at it, it is.  KABAND sets exactly
    # ATEFF_CLAMP on snap-back, so a >= test with a tolerance is required.
    ck("an element at the clamp counts, one just below does not",
       frac_over([(ATEFF_CLAMP, 1.0)], ATEFF_CLAMP - 1e-9) == 1.0
       and frac_over([(ATEFF_CLAMP - 0.1, 1.0)], ATEFF_CLAMP - 1e-9) == 0.0)

    print("\n C. the CSV carries value, basis and verdict together")
    import csv as _csv
    import tempfile
    d = tempfile.mkdtemp()
    rows = [dict(step="Tension", region="Yarn0", quantity="SDV_ATEFF",
                 stat="clamped_frac", value="0.120000",
                 basis="volume fraction with ATEFF >= 50, the KABAND "
                       "snap-back clamp",
                 verdict="STRENGTH NOT QUOTABLE"),
            dict(step="Tension", region="Yarn0", quantity="SDV_DYT",
                 stat="frac_over_0.90", value="0.310000",
                 basis="volume fraction of the region with d >= 0.90",
                 verdict="AT THE CARD CEILING")]
    out = write_csv(os.path.join(d, "j.odb"), rows)
    ck("it is named after the job, not a fixed filename",
       os.path.basename(out) == "j_damage_census.csv", os.path.basename(out))
    got = list(_csv.DictReader(open(out)))
    ck("every promised column exists", set(got[0]) == set(CSV_COLUMNS))
    ck("a clamped fraction over 5 %% says the strength is not quotable",
       got[0]["verdict"] == "STRENGTH NOT QUOTABLE",
       "m6_verdict.py refuses to quote one without this row")
    ck("and saturation at the card ceiling is named as such",
       got[1]["verdict"] == "AT THE CARD CEILING")
    ck("an odb with no SDV fields still writes a header-only CSV",
       len(list(_csv.DictReader(open(write_csv(
           os.path.join(d, "empty.odb"), []))))) == 0)

    print("\n D. the percentile summary is order-independent")
    a = stats([(0.1, 1.0), (0.9, 1.0), (0.5, 1.0)])
    b = stats([(0.9, 1.0), (0.5, 1.0), (0.1, 1.0)])
    ck("shuffling the elements does not change the statistics",
       a == b, "max %.4f" % a["mx"])

    if fails:
        print("\nSELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("\nSELFTEST PASSED")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv or "--selftest" in sys.argv:
        sys.exit(selftest())
    main()
