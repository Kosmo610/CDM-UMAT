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


def finite(x):
    """True for a real number.  Abaqus ships Python 2.7, where math.isfinite
    does not exist, and `nan > 0.0` is False -- which is exactly how a missing
    reaction used to slip through the comparison below as a PASS."""
    return x == x and x not in (float("inf"), float("-inf"))


def hist(hr, prefix):
    """History series whose name starts with `prefix`, or [] if absent.

    `historyOutputs` is an Abaqus Repository, NOT a dict: it supports `in`,
    `[]` and `.keys()` but has NO `.get()`.  Calling .get() on it raises
    AttributeError, which is what killed the crack-band section.
    """
    if hr is None:
        return []
    keys = sorted(k for k in hr.historyOutputs.keys()
                  if k.upper().startswith(prefix))
    if not keys:
        return []
    return list(hr.historyOutputs[keys[0]].data)


def set_label(odb, setname):
    """First node label of a node set, or None.

    THE DECK IS FLAT.  make_patch_tests.py writes `*Node`/`*Element`/`*NSet`
    at model level with no `*Assembly`/`*Instance`, so Abaqus wraps it in an
    auto-generated instance and every `*NSet` lands in
    `rootAssembly.instances[<auto>].nodeSets`, NOT in
    `rootAssembly.nodeSets`.  Looking only at the assembly found nothing, so
    every driver reaction came back missing.  driver_audit.py already searched
    both; this now does too.  Names are stored upper case in the odb.
    """
    want = setname.upper()
    ra = odb.rootAssembly
    for repo in [ra.nodeSets] + [i.nodeSets for i in ra.instances.values()]:
        try:
            keys = repo.keys()
        except AttributeError:
            continue
        if want not in keys:
            continue
        nodes = repo[want].nodes
        if not len(nodes):
            continue
        first = nodes[0]
        # assembly-level sets give one tuple per instance; instance sets do not
        if hasattr(first, "__len__"):
            if not len(first):
                continue
            first = first[0]
        return first.label
    return None


def available(odb, step):
    """What the odb actually contains -- printed only when a lookup fails.

    Guessing twice about the same odb is one time too many.  When the drivers
    cannot be found, say what IS there instead of just reporting nan.
    """
    ra = odb.rootAssembly
    L = ["    odb contents (printed because a driver lookup failed):"]
    try:
        L.append("      assembly node sets : %s"
                 % sorted(ra.nodeSets.keys())[:12])
    except Exception:
        L.append("      assembly node sets : <none>")
    for nm, inst in ra.instances.items():
        try:
            L.append("      instance %-12s: %s"
                     % (nm, sorted(inst.nodeSets.keys())[:12]))
        except Exception:
            pass
    L.append("      history regions    : %s"
             % sorted(step.historyRegions.keys())[:12])
    for key in sorted(step.historyRegions.keys())[:3]:
        L.append("        %-28s outputs %s"
                 % (key, sorted(step.historyRegions[key].historyOutputs.keys())))
    return "\n".join(L)


def region_for(step, odb, setname):
    """The historyRegion belonging to a node set.

    Requesting `*Node Output, nset=Foo` does NOT put "Foo" in the ODB region
    key -- Abaqus names it 'Node ASSEMBLY.5681'.  Matching on the set name
    alone therefore found nothing and every stiffness entry came back nan.
    Fall back to the node label, the way driver_audit.py already does.
    """
    flat = setname.upper().replace(" ", "")
    for key, hr in step.historyRegions.items():
        if flat in key.upper().replace(" ", ""):
            return hr
    label = set_label(odb, setname)
    if label is not None:
        for key, hr in step.historyRegions.items():
            if str(label) in key.replace(".", " ").split():
                return hr
    return None


def field_at_node(step, odb, label, var, comp=0):
    """Last-frame nodal value of `var` at node `label`, or None.

    A fallback for when history output is missing or unmatched.  The patch
    deck also writes RF and U as FIELD output, so the driver reactions are
    recoverable from the last frame even with no historyRegion at all --
    which means a lookup failure never has to cost a re-run.
    """
    fr = step.frames[-1]
    if var not in fr.fieldOutputs.keys():
        return None
    for v in fr.fieldOutputs[var].values:
        if v.nodeLabel == label:
            d = v.data
            return d[comp] if hasattr(d, "__len__") else d
    return None


def driver_series(step, odb, k):
    """(U1, RF1) at the end of the step for ConstraintsDriver<k>."""
    name = "ConstraintsDriver%d" % k
    hr = region_for(step, odb, name)
    u, rf = hist(hr, "U1"), hist(hr, "RF1")
    if u and rf:
        return u[-1][1], rf[-1][1]
    label = set_label(odb, name)
    if label is None:
        return None, None
    fu = field_at_node(step, odb, label, "U", 0)
    frf = field_at_node(step, odb, label, "RF", 0)
    if fu is None or frf is None:
        return None, None
    return fu, frf


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
            u, rf = driver_series(step, odb, i)
            if rf is None:
                Cnum[i][k] = float("nan")
            else:
                # sigma = +RF/V.  The patch test settles the sign: with a
                # minus, step 1 returns C11 = -134615.38 against the analytic
                # +134615.38 -- right magnitude to 1e-8, wrong sign.  The
                # driver reaction is the generalised force conjugate to the
                # macro strain, R = dW/d(eps) = sigma*V, so it carries the
                # sign of the stress already.
                Cnum[i][k] = rf / V / UNIT_STRAIN
    for i in range(6):
        print("  row%d %s" % (i + 1,
                              "  ".join("%11.4f" % Cnum[i][j]
                                        for j in range(6))))

    print()
    # Presence FIRST.  Without this the loop below compares nan, every
    # `err > worst` is False because nan compares False against everything,
    # `worst` stays 0.0, and a matrix that was never read at all reports
    # "worst rel. dev. 0.00e+00" -- a PASS on no data.  That is the single
    # most dangerous thing a verification script can do, so it is now a
    # separate, explicit gate that runs before any tolerance is applied.
    missing = [(i + 1, j + 1) for i in range(6) for j in range(6)
               if not finite(Cnum[i][j])]
    verdict("every entry of the 6x6 was recovered from the odb",
            not missing,
            "all 36 present" if not missing else
            "%d of 36 missing -- neither history nor field output for the "
            "drivers could be matched" % len(missing))
    if missing:
        print(available(odb, odb.steps[names[0]]))

    worst, worst_at = -1.0, "nothing comparable"
    for i in range(6):
        for j in range(6):
            if not finite(Cnum[i][j]):
                continue
            ref, got = Cref[i][j], Cnum[i][j]
            err = abs(got - ref) / max(abs(ref), Cref[0][0])
            if err > worst:
                worst, worst_at = err, "C[%d][%d] %.4f vs %.4f" % (
                    i + 1, j + 1, got, ref)
    verdict("the whole 6x6 matches the analytic isotropic C",
            (not missing) and 0.0 <= worst < RTOL_C,
            "worst rel. dev. %.2e  (%s)" % (worst, worst_at) if worst >= 0.0
            else "no entry could be compared")

    pairs = [(abs(Cnum[i][j] - Cnum[j][i]), i + 1, j + 1)
             for i in range(6) for j in range(6)
             if finite(Cnum[i][j]) and finite(Cnum[j][i])]
    verdict("the recovered stiffness is symmetric",
            bool(pairs) and (not missing)
            and max(p[0] for p in pairs) / Cref[0][0] < RTOL_C,
            "worst %.3e MPa at C[%d][%d]"
            % max(pairs) if pairs else "no comparable pair")

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
            u, _ = driver_series(step, odb, i)
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
        u, rf = hist(hr, "U1"), hist(hr, "RF1")
        if not u or not rf:
            continue
        for t, val in u:
            disp[round(t, 10)] = val
        for t, val in rf:
            force[round(t, 10)] = force.get(round(t, 10), 0.0) + val
    ts = sorted(set(disp) & set(force))
    d = [disp[t] for t in ts]
    f = [force[t] for t in ts]

    ratio = None
    for key, hr in step.historyRegions.items():
        ie, sd = hist(hr, "ALLIE"), hist(hr, "ALLSD")
        if ie and sd:
            a, b = sd[-1][1], ie[-1][1]
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
