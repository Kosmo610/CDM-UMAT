# -*- coding: utf-8 -*-
"""
patch_report.py   (run INSIDE Abaqus:  abaqus python patch_report.py)
=====================================================================
Read the ODBs written by abaqus/make_patch_tests.py and print the verdict.

  abaqus python patch_report.py PATCH_PBC.odb
  abaqus python patch_report.py CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb
  abaqus python patch_report.py PATCH_PBC.odb CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb

A. PATCH_PBC -- periodic boundary conditions against the exact answer
---------------------------------------------------------------------
Both phases carry the same isotropic elastic material and the UMAT is not
called, so the answer is analytic and any deviation is the PBC implementation.

  steps 1-6  the six driver reactions of step k are column k of the effective
             stiffness.  The assembled 6x6 must equal the isotropic C.
  step 7     uniform heating with the drivers free: every stress component
             must be zero and the normal drivers must read alpha*dT.

Tolerances are loose enough to absorb the direct solver's round-off on ~13000
equations and tight enough that a wrong or missing periodic equation fails.

B. CBAND_N* -- crack-band mesh objectivity
------------------------------------------
The three bars are geometrically identical and differ only in element size, so
their force-displacement curves are directly comparable.  Crack-band
regularisation recomputes the softening factor from the element size -- here
A = 15.500, 1.590, 0.569, a spread of 27x -- so that the dissipated energy
stays fixed.  If it works the three curves coincide.  If it were absent, the
softening area would scale with the localising element size and fall by 4x
from N=5 to N=20.

Also prints ALLSD/ALLIE for each bar: the stabilisation is only admissible
while that stays below about 5 %.
"""
from __future__ import print_function

import os
import sys

try:
    from odbAccess import openOdb
except ImportError:
    sys.exit("odbAccess not found -- run with 'abaqus python', not python.")

E_ISO, NU_ISO, ALPHA_ISO = 100000.0, 0.30, 5.0e-6
UNIT_STRAIN = 1.0e-3
DT = 100.0
GF_MATRIX = 0.031            # N/mm
BAR_AREA = 0.2 * 0.2         # mm^2

RTOL_C = 2.0e-4              # relative, on the stiffness entries
ATOL_ZERO = 1.0e-6           # MPa, on stresses that must vanish

_FAIL = []


def verdict(name, ok, detail=""):
    if not ok:
        _FAIL.append(name)
    print("    %s  %-46s %s" % ("PASS" if ok else "FAIL", name, detail))


def isotropic_C():
    lam = E_ISO * NU_ISO / ((1.0 + NU_ISO) * (1.0 - 2.0 * NU_ISO))
    mu = E_ISO / (2.0 * (1.0 + NU_ISO))
    C = [[0.0] * 6 for _ in range(6)]
    for i in range(3):
        for j in range(3):
            C[i][j] = lam + (2.0 * mu if i == j else 0.0)
    for i in range(3, 6):
        C[i][i] = mu
    return C


def rve_volume(odb):
    inst = list(odb.rootAssembly.instances.values())[0]
    xs = [n.coordinates[0] for n in inst.nodes]
    ys = [n.coordinates[1] for n in inst.nodes]
    zs = [n.coordinates[2] for n in inst.nodes]
    return ((max(xs) - min(xs)) * (max(ys) - min(ys)) * (max(zs) - min(zs)))


def driver_series(step, k):
    """(U1, RF1) at the end of the step for ConstraintsDriver<k>."""
    want = "CONSTRAINTSDRIVER%d" % k
    for key, hr in step.historyRegions.items():
        if want not in key.upper():
            continue
        u = hr.historyOutputs.get("U1")
        rf = hr.historyOutputs.get("RF1")
        if u is None or rf is None:
            continue
        return u.data[-1][1], rf.data[-1][1]
    return None, None


def report_patch(path):
    print("\n" + "=" * 74)
    print("A. PERIODIC BOUNDARY CONDITIONS -- patch test: %s" % path)
    print("=" * 74)
    odb = openOdb(path, readOnly=True)
    V = rve_volume(odb)
    print("  V_RVE = %.6f mm^3   %d steps" % (V, len(odb.steps)))

    Cref = isotropic_C()
    names = [s for s in odb.steps.keys() if not s.upper().endswith("FREE")]
    names = names[:6]

    print("\n  effective stiffness from the driver reactions [MPa]")
    print("        %s" % "  ".join("%11s" % ("col%d" % (j + 1))
                                   for j in range(6)))
    Cnum = [[0.0] * 6 for _ in range(6)]
    for k, sname in enumerate(names):
        step = odb.steps[sname]
        for i in range(6):
            u, rf = driver_series(step, i)
            if rf is None:
                Cnum[i][k] = float("nan")
            else:
                Cnum[i][k] = -rf / V / UNIT_STRAIN
    for i in range(6):
        print("  row%d %s" % (i + 1,
                              "  ".join("%11.4f" % Cnum[i][j]
                                        for j in range(6))))

    worst, worst_at = 0.0, ""
    for i in range(6):
        for j in range(6):
            ref = Cref[i][j]
            got = Cnum[i][j]
            scale = max(abs(ref), Cref[0][0])
            err = abs(got - ref) / scale
            if err > worst:
                worst, worst_at = err, "C[%d][%d] %.4f vs %.4f" % (
                    i + 1, j + 1, got, ref)
    print()
    verdict("the whole 6x6 matches the analytic isotropic C",
            worst < RTOL_C, "worst rel. dev. %.2e  (%s)" % (worst, worst_at))
    sym = max(abs(Cnum[i][j] - Cnum[j][i])
              for i in range(6) for j in range(6))
    verdict("the recovered stiffness is symmetric",
            sym / Cref[0][0] < RTOL_C, "worst %.3e MPa" % sym)

    # uniformity of the strain field
    fr = odb.steps[names[0]].frames[-1]
    if "E" in fr.fieldOutputs.keys():
        vals = [v.data[0] for v in fr.fieldOutputs["E"].values]
        spread = max(vals) - min(vals)
        verdict("strain field is uniform in step 1",
                spread < 1.0e-9,
                "E11 spread %.3e over %d points" % (spread, len(vals)))

    # thermal step
    tname = [s for s in odb.steps.keys() if s.upper().endswith("FREE")]
    if tname:
        step = odb.steps[tname[0]]
        fr = step.frames[-1]
        smax = 0.0
        if "S" in fr.fieldOutputs.keys():
            for v in fr.fieldOutputs["S"].values:
                smax = max(smax, max(abs(x) for x in v.data))
        verdict("free thermal expansion develops zero stress",
                smax < ATOL_ZERO, "max |S| = %.3e MPa" % smax)
        for i in range(3):
            u, _ = driver_series(step, i)
            if u is None:
                continue
            want = ALPHA_ISO * DT
            verdict("driver %d reads alpha*dT" % i,
                    abs(u - want) < 1.0e-9,
                    "%.6e vs %.6e" % (u, want))
    odb.close()


def bar_curve(path):
    """(delta[], force[], allsd/allie) from a CBAND bar odb."""
    odb = openOdb(path, readOnly=True)
    step = odb.steps[list(odb.steps.keys())[-1]]
    disp, force = {}, {}
    for key, hr in step.historyRegions.items():
        u = hr.historyOutputs.get("U1")
        rf = hr.historyOutputs.get("RF1")
        if u is None or rf is None:
            continue
        for t, val in u.data:
            disp[round(t, 10)] = val
        for t, val in rf.data:
            force[round(t, 10)] = force.get(round(t, 10), 0.0) + val
    ts = sorted(set(disp) & set(force))
    d = [disp[t] for t in ts]
    f = [force[t] for t in ts]

    ratio = None
    for key, hr in step.historyRegions.items():
        ie = hr.historyOutputs.get("ALLIE")
        sd = hr.historyOutputs.get("ALLSD")
        if ie is not None and sd is not None:
            a, b = sd.data[-1][1], ie.data[-1][1]
            ratio = a / b if b else None
    odb.close()
    return d, f, ratio


def trapz(x, y):
    return sum(0.5 * (y[i] + y[i + 1]) * (x[i + 1] - x[i])
               for i in range(len(x) - 1))


def report_bars(paths):
    print("\n" + "=" * 74)
    print("B. CRACK-BAND MESH OBJECTIVITY -- %d bars" % len(paths))
    print("=" * 74)
    rows = []
    for p in paths:
        d, f, ratio = bar_curve(p)
        if len(d) < 3:
            print("  %s: only %d history points, skipped" % (p, len(d)))
            continue
        fmax = max(f)
        kpk = f.index(fmax)
        rows.append(dict(name=os.path.basename(p), d=d, f=f, fmax=fmax,
                         dpk=d[kpk], work=trapz(d, f),
                         tail=trapz(d[kpk:], f[kpk:]), allsd=ratio))

    print("\n  %-14s %10s %10s %12s %12s %8s"
          % ("job", "F_max [N]", "d_pk [mm]", "work [Nmm]", "tail [Nmm]",
             "ALLSD/IE"))
    for r in rows:
        print("  %-14s %10.4f %10.3e %12.5e %12.5e %8s"
              % (r["name"], r["fmax"], r["dpk"], r["work"], r["tail"],
                 "%.3f" % r["allsd"] if r["allsd"] is not None else "n/a"))

    if len(rows) < 2:
        print("\n  need at least two meshes to judge objectivity")
        return

    print()
    for key, label, tol in (("fmax", "peak force", 0.05),
                            ("work", "total work", 0.05),
                            ("tail", "post-peak (softening) area", 0.15)):
        vals = [r[key] for r in rows]
        spread = (max(vals) - min(vals)) / (sum(vals) / len(vals))
        verdict("%s is mesh independent" % label, spread <= tol,
                "spread %.1f %% over %dx element-size range"
                % (spread * 100, 4))

    gf = GF_MATRIX * BAR_AREA
    print("\n  fracture energy expected from the card: "
          "Gf x area = %.3f x %.3f = %.4e N.mm" % (GF_MATRIX, BAR_AREA, gf))
    for r in rows:
        print("    %-14s post-peak area / (Gf x area) = %.2f"
              % (r["name"], r["tail"] / gf))
    print("  (a ratio of order one means the softening branch is dissipating "
         "the\n   fracture energy the card asked for; what matters for "
         "objectivity is\n   that the three ratios AGREE, not that they are "
         "exactly 1 -- the tail\n   also carries the elastic unloading of the "
         "rest of the bar)")

    for r in rows:
        if r["allsd"] is None:
            continue
        verdict("%s stabilisation energy below 5 %%" % r["name"],
                r["allsd"] < 0.05, "ALLSD/ALLIE = %.4f" % r["allsd"])

    out = "cband_curves.csv"
    with open(out, "w") as fh:
        fh.write("job,delta_mm,force_N\n")
        for r in rows:
            for x, y in zip(r["d"], r["f"]):
                fh.write("%s,%.8e,%.8e\n" % (r["name"], x, y))
    print("\n  wrote %s  (plot the three curves on one axis -- they should "
          "overlie)" % out)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    patch = [a for a in args if "PATCH" in os.path.basename(a).upper()]
    bars = [a for a in args if "CBAND" in os.path.basename(a).upper()]
    for p in patch:
        report_patch(p)
    if bars:
        report_bars(sorted(bars))

    print("\n" + "=" * 74)
    if _FAIL:
        print("VERDICT: %d CHECK(S) FAILED -> %s" % (len(_FAIL),
                                                     ", ".join(_FAIL)))
        print("=" * 74)
        return 1
    print("VERDICT: ALL CHECKS PASS")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
