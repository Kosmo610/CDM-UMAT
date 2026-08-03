# -*- coding: utf-8 -*-
"""
extract_kbar.py -- homogenised conductivity from an RVE_COND odb.

RUN INSIDE ABAQUS (it needs odbAccess):

    abaqus python extract_kbar.py RVE_COND_P32_k8.odb [more.odb ...]

WHAT IT COMPUTES

    kbar_i = Q_i * L_i / (A_i * dT)

Q_i is the summed reaction flux RFL on the HOT face of step kbar_dir<i>,
L_i the cell length along that axis and A_i the face area.  Everything comes
out of the odb -- the box is measured from the node coordinates, not typed.

WHAT TO LOOK AT FIRST
  1. kbar1 vs kbar2.  The weave is balanced, so they must agree.  They are
     computed from two independent solves, so a disagreement means the mesh
     or the face sets are wrong and nothing else in the file can be trusted.
  2. kbar3 against the measured 6.29 W/(m.K) for 2D C/SiC (refs/[12]).
  3. the anisotropy kbar1/kbar3 against about 2 (refs/[13], architecture
     effect, transfers even though the magnitudes do not).

Repository note: odb historyOutputs and steps are Abaqus Repository objects.
They support keys()/[]/in but NOT .get() -- calling .get() on one is what
broke patch_report.py, so this file indexes explicitly.
"""
from __future__ import print_function

import os
import sys

try:
    from odbAccess import openOdb
except ImportError:
    sys.exit("odbAccess not found -- run this with 'abaqus python', "
             "not with plain python.")

#: Measured through-thickness conductivity of 2D C/SiC, refs/[12] [W/(m.K)].
MEASURED_K3 = 6.29
#: Architecture anisotropy for a 2D weave, refs/[13].
TARGET_ANISO = 2.0
#: W/(mm.K) -> W/(m.K)
TO_WMK = 1000.0


def rve_box(odb):
    lo = [1e30] * 3
    hi = [-1e30] * 3
    for inst in odb.rootAssembly.instances.values():
        for n in inst.nodes:
            c = n.coordinates
            for k in range(3):
                if c[k] < lo[k]:
                    lo[k] = c[k]
                if c[k] > hi[k]:
                    hi[k] = c[k]
    return [hi[k] - lo[k] for k in range(3)]


def flux_sum(step):
    """Summed RFL over every history region of one step."""
    q, n = 0.0, 0
    for rname in step.historyRegions.keys():
        hr = step.historyRegions[rname]
        for key in hr.historyOutputs.keys():
            if not key.upper().startswith("RFL"):
                continue
            data = hr.historyOutputs[key].data
            if data:
                q += data[-1][1]
                n += 1
    return q, n


def kbar(path, dT=1.0):
    odb = openOdb(path, readOnly=True)
    try:
        L = rve_box(odb)
        A = (L[1] * L[2], L[0] * L[2], L[0] * L[1])
        out = [None, None, None]
        counts = [0, 0, 0]
        for sname in odb.steps.keys():
            up = sname.upper()
            if not up.startswith("KBAR_DIR"):
                continue
            try:
                ax = int(up.replace("KBAR_DIR", "")) - 1
            except ValueError:
                continue
            if not 0 <= ax < 3:
                continue
            q, n = flux_sum(odb.steps[sname])
            counts[ax] = n
            if n == 0:
                continue
            out[ax] = abs(q) * L[ax] / (A[ax] * dT)
        return L, out, counts
    finally:
        odb.close()


def report(paths, dT=1.0):
    print("=" * 76)
    print("extract_kbar.py -- homogenised conductivity")
    print("=" * 76)
    rows = []
    for p in paths:
        if not os.path.exists(p):
            print("\n  MISSING: %s" % p)
            continue
        try:
            L, k, counts = kbar(p, dT)
        except Exception as exc:                       # noqa: BLE001
            print("\n  %s: could not be read -- %s" % (p, exc))
            continue
        name = os.path.basename(p)
        print("\n--- %s" % name)
        print("    box  Lx=%.4f Ly=%.4f Lz=%.4f mm" % tuple(L))
        if not any(counts):
            print("    NO RFL HISTORY IN ANY STEP.  The deck must carry")
            print("      *Output, history / *Node Output, nset=FACE_?HI / RFL")
            continue
        for ax in range(3):
            if k[ax] is None:
                print("    kbar%d   not computed (%d RFL outputs found)"
                      % (ax + 1, counts[ax]))
            else:
                print("    kbar%d = %8.4f W/(m.K)   from %d nodal fluxes"
                      % (ax + 1, k[ax] * TO_WMK, counts[ax]))
        rows.append((name, [None if v is None else v * TO_WMK for v in k]))

    if not rows:
        print("\n  nothing to compare.")
        return 1

    print("\n" + "=" * 76)
    print("  %-28s %9s %9s %9s %9s" % ("deck", "kbar1", "kbar2", "kbar3",
                                       "k1/k3"))
    for name, k in rows:
        a = "%9.4f" % k[0] if k[0] is not None else "%9s" % "-"
        b = "%9.4f" % k[1] if k[1] is not None else "%9s" % "-"
        c = "%9.4f" % k[2] if k[2] is not None else "%9s" % "-"
        r = ("%9.2f" % (k[0] / k[2])) if (k[0] and k[2]) else "%9s" % "-"
        print("  %-28s %s %s %s %s" % (name[:28], a, b, c, r))

    print("\n  CHECK 1 -- the balanced weave: kbar1 must equal kbar2")
    worst, worst_at = -1.0, "nothing comparable"
    for name, k in rows:
        if k[0] and k[1]:
            rel = abs(k[0] - k[1]) / max(k[0], k[1])
            if rel > worst:
                worst, worst_at = rel, name
    if worst < 0.0:
        print("    NOT CHECKED -- no deck produced both kbar1 and kbar2.")
    elif worst < 0.05:
        print("    OK: worst in-plane asymmetry %.2f %% (%s)"
              % (100.0 * worst, worst_at))
        print("    Two independent solves agree, so the face sets and the")
        print("    mesh symmetry are both sound.")
    else:
        print("    ** FAILED: %.1f %% asymmetry in %s **"
              % (100.0 * worst, worst_at))
        print("    A balanced plain weave cannot do this.  Suspect the face")
        print("    node sets before believing any number in this table.")

    print("\n  CHECK 2 -- kbar3 against the measurement, refs/[12] %.2f W/(m.K)"
          % MEASURED_K3)
    for name, k in rows:
        if k[2] is None:
            continue
        print("    %-28s %8.4f   %+6.1f %%"
              % (name[:28], k[2], 100.0 * (k[2] - MEASURED_K3) / MEASURED_K3))
    print("    A filled-cell deck SHOULD read high -- that is why the")
    print("    porosity variants exist.  What matters is which porosity")
    print("    lands on the measurement, and whether it is the same one the")
    print("    stiffness needed (32.4 % matrix porosity, Ch.4 4.9-13).")

    print("\n  CHECK 3 -- anisotropy, refs/[13] gives about %.1f" % TARGET_ANISO)
    for name, k in rows:
        if k[0] and k[2]:
            print("    %-28s %8.2f" % (name[:28], k[0] / k[2]))
    print("=" * 76)

    csv = "kbar_summary.csv"
    with open(csv, "w") as f:
        f.write("deck,kbar1_WmK,kbar2_WmK,kbar3_WmK\n")
        for name, k in rows:
            f.write("%s,%s,%s,%s\n" % tuple(
                [name] + ["" if v is None else "%.6g" % v for v in k]))
    print("  wrote %s" % csv)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(report(args))
