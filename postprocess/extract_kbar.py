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

import re

try:
    from odbAccess import openOdb
except ImportError:
    # Not fatal at import time.  Everything below the odb reader is plain
    # arithmetic, and --selftest exercises exactly that part with ordinary
    # python so the verdict logic is checked BEFORE the jobs are run rather
    # than discovered to be wrong afterwards.
    openOdb = None

#: Measured through-thickness conductivity of 2D C/SiC, refs/[12] [W/(m.K)].
MEASURED_K3 = 6.29
#: Architecture anisotropy for a 2D weave, refs/[13].
TARGET_ANISO = 2.0
#: Card conductivity -> W/(m.K), for a deck built BEFORE 2026-08-11.
#: Those decks are in the "W/(mm.K)" set, k_card = k_SI/1000.  Decks built
#: after carry a UNITSTAMP naming their own factor, and `unit_factor` reads
#: it, so an odb from either era is read correctly without anyone having to
#: remember which one produced it.  Steady-state kbar is a ratio and is
#: therefore RIGHT in both eras -- only the label on the axis changes.
TO_WMK_LEGACY = 1000.0

#: Written by abaqus/make_rve_virtual_tests.py as UNIT_STAMP.
_STAMP = re.compile(r"UNITSTAMP:\s*k_card_per_WmK\s*=\s*([0-9.eE+-]+)")


def unit_factor(inp_path):
    """(multiplier from card units to W/(m.K), how it was decided).

    A missing stamp is not an error: it means the deck predates the stamp,
    which pins it to the legacy set exactly as surely as a stamp would.
    """
    if inp_path and os.path.exists(inp_path):
        m = _STAMP.search(open(inp_path).read())
        if m:
            per = float(m.group(1))
            if per > 0:
                return 1.0 / per, "UNITSTAMP k_card_per_WmK=%g" % per
    return TO_WMK_LEGACY, "no UNITSTAMP: pre-2026-08-11 W/(mm.K) deck"

#: Matrix porosity the STIFFNESS route needs, Ch.4 4.9-13.  Since a1-0002 this
#: is a LOWER bound, not a value: it comes from refs/[10]'s CVI density, and
#: the reference material is PIP, which leaves more porosity than CVI.  So the
#: two routes are only compatible if conductivity also wants >= this.
STIFFNESS_MATRIX_POROSITY = 0.324


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


def deck_variant(odb_path):
    """(matrix porosity, fibre transverse k) for one deck.

    Read from the .inp's own header comment when it is sitting next to the
    odb, which it always is in the job directory:

        **   SiC    k = 25 dense -> 12.7786 W/(m.K) at 32.4 % MATRIX porosity

    The file is the authority, not the file NAME: the decks are called P05 but
    that one carries 4.5 %, and interpolating on 5 % would put the answer in
    the wrong place.  The name is only a fallback for a renamed odb.
    """
    stem = os.path.splitext(odb_path)[0]
    porosity, kf = None, None
    inp = stem + ".inp"
    if os.path.exists(inp):
        # THE WHOLE FILE, not the first 4 kB.  make_rve_conductivity.py emits
        # the thermal card -- and this comment with it -- next to the
        # *Material blocks, which sit AFTER the mesh: line 60814 of a 2.4 MB
        # deck.  Reading a 4 kB window found only nodes, so this silently fell
        # through to the file NAME and reported the P05 deck as 5.0 % when it
        # carries 4.5 %, and P32 as 32.0 % against its real 32.4 % (caught in
        # the 2026-08-10 run).  That is precisely the failure the docstring
        # below says cannot happen.
        head = open(inp).read()
        m = re.search(r"at\s+([0-9.]+)\s*%\s*MATRIX porosity", head)
        if m:
            porosity = float(m.group(1)) / 100.0
        m = re.search(r"yarn transverse[^\n]*?k[^0-9\n]*([0-9.]+)", head)
        if m:
            kf = float(m.group(1))
    name = os.path.basename(stem)
    if porosity is None:
        m = re.search(r"_P(\d+)", name)
        if m:
            porosity = float(m.group(1)) / 100.0
    if kf is None:
        m = re.search(r"_k(\d+)", name)
        if m:
            kf = float(m.group(1))
    return porosity, kf


def porosity_for_target(points, target=MEASURED_K3):
    """Matrix porosity at which kbar3 would equal `target`.

    `points` is [(porosity, kbar3), ...] from decks that differ ONLY in
    porosity.  Two or more are needed; the two bracketing the target are used,
    and if none bracket it the outermost pair is extrapolated and the result
    is flagged, because an extrapolated porosity of 60 % is not a measurement
    of anything -- it is a statement that pores alone cannot get there.

    Returns (porosity, bracketed) or (None, False).
    """
    pts = sorted((p, k) for p, k in points if p is not None and k is not None)
    if len(pts) < 2:
        return None, False
    for (p0, k0), (p1, k1) in zip(pts, pts[1:]):
        if (k0 - target) * (k1 - target) <= 0.0 and k0 != k1:
            return p0 + (p1 - p0) * (target - k0) / (k1 - k0), True
    (p0, k0), (p1, k1) = pts[0], pts[-1]
    if k0 == k1:
        return None, False
    return p0 + (p1 - p0) * (target - k0) / (k1 - k0), False


def kbar(path, dT=1.0):
    if openOdb is None:
        sys.exit("odbAccess not found -- run this with 'abaqus python', "
                 "not with plain python.")
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


#: RVE phase fractions, from data/properties/porosity_stiffness.py.
VY_RVE = 0.4982                 # yarn volume fraction of the cell
#: Dense-phase conductivities the decks are built from (W/(m.K)).
K_MATRIX_DENSE = 25.0
K_YARN_LONG_DENSE = 11.5370     # P00 header
K_YARN_TRANS_DENSE = 3.8847     # P00 header


def deck_conductivities(odb_path):
    """(k_matrix, k_yarn_long, k_yarn_trans) in W/(m.K) read from the DECK.

    The bound has to be built from the card the solver actually ran, not from
    this file's defaults.  LTH2_COND_P32K60 is exactly why: it is the yarn
    sensitivity deck and carries k_long = 50.175, while the defaults below say
    11.537.  Built from the defaults, its bound came out at 11.14 and the run's
    perfectly sound kbar1 = 19.12 was reported as IMPOSSIBLE (2026-08-10).

    A false NO costs as much as a missed one -- it throws away a good run.

    Returns None if the deck is not next to the odb, in which case the caller
    falls back to the defaults AND SAYS SO.
    """
    inp = os.path.splitext(odb_path)[0] + ".inp"
    if not os.path.exists(inp):
        return None
    txt = open(inp).read()
    ks = {}
    for m in re.finditer(r"\*Material,\s*Name=(\S+)\s*\n\*Conductivity"
                         r"[^\n]*\n([^\n*]+)", txt, re.I):
        vals = [float(v) for v in m.group(2).split(",") if v.strip()]
        if vals:
            ks[m.group(1).strip().upper()] = vals
    mat = ks.get("SIC_MATRIX_THERMAL")
    yrn = ks.get("CSIC_YARN_THERMAL")
    if not mat or not yrn:
        return None
    # The bound and the measurement must be read in the SAME unit set, so the
    # factor comes from this deck's own stamp -- not from a module constant.
    f = unit_factor(inp)[0]
    return (mat[0] * f, yrn[0] * f,
            yrn[1] * f if len(yrn) > 1 else yrn[0] * f)


def voigt_bounds(vp_matrix, phases=None):
    """(bound1, bound2, bound3) W/(m.K).

    Parallel (Voigt) sum of the phases as the deck builds them: half the
    yarns run along x and half along y, so an in-plane direction sees one
    set axially and the other transversely, while z sees both
    transversely.

    `phases` is (k_matrix, k_yarn_long, k_yarn_trans) ALREADY at the deck's
    own porosity -- that is what deck_conductivities returns, because the
    generator knocks the matrix down with a Maxwell relation and then derives
    the yarn FROM the knocked-down matrix, so the three do not share one
    factor.  Scaling dense values by (1 - vp) reproduces neither.

    Without `phases` it falls back to the dense defaults scaled by (1 - vp),
    which is only ever right for a deck that uses the default yarn card.

    This is a CEILING, not a model.  Its whole job is to catch a number
    that cannot be right for any microstructure -- which is what the
    2026-08-07 run produced (kbar2 = 56.27 against a ceiling of 16.39).
    """
    if phases is not None:
        km, kl, kt = phases
    else:
        if vp_matrix is None:
            return None
        f = 1.0 - vp_matrix          # solid fraction of the matrix phase
        km = K_MATRIX_DENSE * f
        kl = K_YARN_LONG_DENSE * f
        kt = K_YARN_TRANS_DENSE * f
    inplane = 0.5 * VY_RVE * kl + 0.5 * VY_RVE * kt + (1.0 - VY_RVE) * km
    through = VY_RVE * kt + (1.0 - VY_RVE) * km
    return (inplane, inplane, through)


def write_csv(path, rows):
    """One row per deck.  The CSV is the deliverable, the console is a log."""
    import csv as _csv
    with open(path, "w") as fh:
        w = _csv.writer(fh)
        w.writerow(["deck", "matrix_porosity", "kbar1_WmK", "kbar2_WmK",
                    "kbar3_WmK", "k1_over_k3", "voigt_inplane", "voigt_through",
                    "kbar1_admissible", "kbar2_admissible", "kbar3_admissible",
                    "unit_basis"])
        for name, k, vp, _kf, ph, why in rows:
            hi = voigt_bounds(vp, ph)
            def adm(i):
                if k[i] is None or hi is None:
                    return ""
                return "yes" if k[i] <= hi[i] * 1.02 else "NO"
            w.writerow([
                name,
                "" if vp is None else "%.4f" % vp,
                "" if k[0] is None else "%.4f" % k[0],
                "" if k[1] is None else "%.4f" % k[1],
                "" if k[2] is None else "%.4f" % k[2],
                "" if not (k[0] and k[2]) else "%.4f" % (k[0] / k[2]),
                "" if hi is None else "%.4f" % hi[0],
                "" if hi is None else "%.4f" % hi[2],
                adm(0), adm(1), adm(2), why])


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
        to_wmk, why = unit_factor(os.path.splitext(p)[0] + ".inp")
        print("\n--- %s" % name)
        print("    box  Lx=%.4f Ly=%.4f Lz=%.4f mm" % tuple(L))
        print("    units: card x %g -> W/(m.K)   [%s]" % (to_wmk, why))
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
                      % (ax + 1, k[ax] * to_wmk, counts[ax]))
        vp, kf = deck_variant(p)
        if vp is not None:
            print("    variant: %.1f %% matrix porosity%s"
                  % (100.0 * vp, ", fibre k_t = %g" % kf if kf else ""))
        ph = deck_conductivities(p)
        if ph:
            print("    deck card: k_matrix = %.4f, k_yarn_long = %.4f, "
                  "k_yarn_trans = %.4f W/(m.K)" % ph)
        else:
            print("    !! no .inp beside the odb -- the bound below falls "
                  "back to the DEFAULT yarn card, which is wrong for any "
                  "sensitivity deck")
        rows.append((name, [None if v is None else v * to_wmk for v in k],
                     vp, kf, ph, why))

    if not rows:
        print("\n  nothing to compare.")
        return 1

    print("\n" + "=" * 76)
    print("  %-28s %9s %9s %9s %9s" % ("deck", "kbar1", "kbar2", "kbar3",
                                       "k1/k3"))
    for name, k, _vp, _kf, _ph in rows:
        a = "%9.4f" % k[0] if k[0] is not None else "%9s" % "-"
        b = "%9.4f" % k[1] if k[1] is not None else "%9s" % "-"
        c = "%9.4f" % k[2] if k[2] is not None else "%9s" % "-"
        r = ("%9.2f" % (k[0] / k[2])) if (k[0] and k[2]) else "%9s" % "-"
        print("  %-28s %s %s %s %s" % (name[:28], a, b, c, r))

    print("\n  CHECK 0 -- is the number even possible?  (Voigt upper bound)")
    print("    A composite cannot conduct better than a parallel bundle of")
    print("    its own phases.  This bound needs no symmetry argument and no")
    print("    literature: exceed it and the number is wrong, full stop.")
    nbad = 0
    for name, k, vp, _kf, ph in rows:
        hi = voigt_bounds(vp, ph)
        if hi is None:
            print("    %-28s  no variant header, bound not computed" % name[:28])
            continue
        for ax in range(3):
            if k[ax] is None:
                continue
            lim = hi[ax]
            if k[ax] > lim * 1.02:          # 2 % for discretisation
                nbad += 1
                print("    %-28s  kbar%d = %.4f  >  bound %.4f   ** IMPOSSIBLE"
                      " (%.2fx) **" % (name[:28], ax + 1, k[ax], lim,
                                       k[ax] / lim))
    if nbad == 0:
        print("    OK: every reported kbar is under its own Voigt bound.")
    else:
        print("    %d value(s) above the bound.  Nothing downstream of them" % nbad)
        print("    may be quoted -- not the anisotropy, not the porosity")
        print("    verdict.  Fix the deck or the extraction first.")
        print("    First suspect: boundary conditions carried over between")
        print("    steps (Abaqus keeps them unless *Boundary says op=NEW).")

    print("\n  CHECK 1 -- the balanced weave: kbar1 must equal kbar2")
    worst, worst_at = -1.0, "nothing comparable"
    for name, k, _vp, _kf, _ph in rows:
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
    for name, k, _vp, _kf, _ph in rows:
        if k[2] is None:
            continue
        print("    %-28s %8.4f   %+6.1f %%"
              % (name[:28], k[2], 100.0 * (k[2] - MEASURED_K3) / MEASURED_K3))
    print("    A filled-cell deck SHOULD read high -- that is why the")
    print("    porosity variants exist.  What matters is which porosity")
    print("    lands on the measurement, and whether it is the same one the")
    print("    stiffness needed (32.4 % matrix porosity, Ch.4 4.9-13).")

    print("\n  CHECK 3 -- anisotropy, refs/[13] gives about %.1f" % TARGET_ANISO)
    for name, k, _vp, _kf, _ph in rows:
        if k[0] and k[2]:
            print("    %-28s %8.2f" % (name[:28], k[0] / k[2]))

    verdict(rows)

    # The CSV is what gets sent on; the console text is a log of how it was
    # reached.  Written unconditionally, including when CHECK 0 failed --
    # the admissible columns are how a reader sees WHICH rows to ignore.
    out = os.path.join(os.path.dirname(os.path.abspath(paths[0])) or ".",
                       "kbar_summary.csv")
    write_csv(out, rows)
    print("\n  CSV written: %s" % out)
    print("  (send this file, not a screenshot -- it carries the Voigt")
    print("   bounds and an admissible yes/NO per direction)")
    print("=" * 76)


def verdict(rows):
    """CHECK 4 -- which porosity does the conductivity want, and does the
    stiffness route agree?

    This is the question the four decks were built to settle, so the answer is
    computed here rather than left to be eyeballed off the table.  Grouped by
    fibre transverse conductivity, because that is the other unknown: if the
    two groups disagree about the porosity, then porosity is not what the
    conductivity is actually sensitive to and neither answer means much.
    """
    print("\n  CHECK 4 -- the porosity verdict (Ch.4 4.9-13, sync a2-0006)")
    groups = {}
    for name, k, vp, kf, _ph in rows:
        if vp is None or k[2] is None:
            continue
        groups.setdefault(kf, []).append((vp, k[2], name))

    if not groups:
        print("    NOT CHECKED -- no deck declared its porosity.  The .inp")
        print("    files must sit next to the odbs for this to work.")
        return

    answers = []
    for kf in sorted(groups, key=lambda x: (x is None, x)):
        pts = [(vp, k3) for vp, k3, _ in groups[kf]]
        label = "fibre k_t = %g" % kf if kf is not None else "ungrouped"
        if len(pts) < 2:
            print("    %-18s only %d deck -- need two porosities to solve"
                  % (label, len(pts)))
            continue
        p, bracketed = porosity_for_target(pts)
        if p is None:
            print("    %-18s kbar3 did not move with porosity -- porosity is"
                  " not the sensitivity here" % label)
            continue
        answers.append((kf, p, bracketed))
        print("    %-18s kbar3 = %.2f W/(m.K) at %.1f %% matrix porosity  (%s)"
              % (label, MEASURED_K3, 100.0 * p,
                 "interpolated" if bracketed else "EXTRAPOLATED -- outside "
                 "the decks that were run"))

    if not answers:
        return

    print("\n    stiffness route needs >= %.1f %% matrix porosity"
          % (100.0 * STIFFNESS_MATRIX_POROSITY))
    print("    (a LOWER bound since a1-0002: the density is refs/[10]'s CVI")
    print("     and our reference material is PIP, which is more porous)")
    for kf, p, bracketed in answers:
        tag = "fibre k_t = %g" % kf if kf is not None else "ungrouped"
        if p >= STIFFNESS_MATRIX_POROSITY:
            print("    %-18s %.1f %% >= %.1f %%  -> CONSISTENT.  One porosity can"
                  % (tag, 100.0 * p, 100.0 * STIFFNESS_MATRIX_POROSITY))
            print("                       serve both, and 4.9-13's conflict closes.")
        else:
            print("    %-18s %.1f %% <  %.1f %%  -> INCOMPATIBLE by %.1fx."
                  % (tag, 100.0 * p, 100.0 * STIFFNESS_MATRIX_POROSITY,
                     STIFFNESS_MATRIX_POROSITY / p if p > 0 else float("inf")))
            print("                       No single porosity satisfies both, so at")
            print("                       least one of the two models is wrong about")
            print("                       WHAT the pores do -- not about how many.")
    if any(not b for _, _, b in answers):
        print("\n    ** an EXTRAPOLATED answer is not a measurement.  It says the")
        print("       decks that were run do not bracket the target, i.e. pores")
        print("       alone cannot take kbar3 to %.2f in the range tested."
              % MEASURED_K3)


def selftest():
    """Check the verdict arithmetic without Abaqus, before the jobs are run."""
    print("extract_kbar.py selftest  (no odb needed)")
    fails = []

    def ck(name, cond, detail=""):
        if cond:
            print("  [PASS] %-54s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %-54s %s" % (name, detail))

    # ---- deck_variant reads the file, not the misleading name ----
    here = os.path.dirname(os.path.abspath(__file__))
    tmp = os.path.join(here, "_kbar_selftest.inp")
    with open(tmp, "w") as f:
        f.write("*Heading\n**   SiC    k = 25 dense -> 12.7786 W/(m.K) "
                "at 32.4 % MATRIX porosity\n")
    try:
        vp, _kf = deck_variant(os.path.join(here, "_kbar_selftest.odb"))
        ck("porosity is read from the .inp header", abs(vp - 0.324) < 1e-9,
           "%.3f" % vp)
    finally:
        os.remove(tmp)
    vp, kf = deck_variant("RVE_COND_P05_k8.odb")
    ck("with no .inp the name is the fallback", abs(vp - 0.05) < 1e-9
       and kf == 8.0, "P05 -> %.2f, k8 -> %g" % (vp, kf))
    ck("and the fallback is KNOWN to be wrong for P05 (really 4.5 %)",
       abs(vp - 0.045) > 1e-6,
       "which is why the header is preferred, not the name")

    # ---- the root find ----
    pts = [(0.0, 12.0), (0.045, 10.0), (0.324, 4.0)]
    p, br = porosity_for_target(pts, target=6.29)
    ck("interpolates inside the bracket", br and 0.045 < p < 0.324,
       "%.4f" % p)
    exact = 0.045 + (0.324 - 0.045) * (6.29 - 10.0) / (4.0 - 10.0)
    ck("and matches the closed form", abs(p - exact) < 1e-12, "%.6f" % p)
    p, br = porosity_for_target([(0.0, 12.0), (0.324, 8.0)], target=6.29)
    ck("flags an answer outside the decks that were run", not br and p > 0.324,
       "%.3f, extrapolated" % p)
    p, br = porosity_for_target([(0.0, 6.29), (0.324, 4.0)], target=6.29)
    ck("a target hit exactly at an endpoint still counts as bracketed",
       br and abs(p) < 1e-12, "%.3f" % p)
    ck("one deck cannot solve for a porosity",
       porosity_for_target([(0.1, 5.0)])[0] is None)
    ck("a flat response is reported, not divided by zero",
       porosity_for_target([(0.0, 5.0), (0.3, 5.0)])[0] is None)
    ck("points are sorted, so deck order on the command line cannot matter",
       porosity_for_target([(0.324, 4.0), (0.0, 12.0), (0.045, 10.0)])[0]
       == porosity_for_target(pts)[0])

    # ---- the comparison the whole exercise is for ----
    ck("the stiffness requirement is the 4.9-13 number",
       abs(STIFFNESS_MATRIX_POROSITY - 0.324) < 1e-9)
    ck("4.5 % would be incompatible with it by more than 7x",
       STIFFNESS_MATRIX_POROSITY / 0.045 > 7.0,
       "%.1fx" % (STIFFNESS_MATRIX_POROSITY / 0.045))

    print("\n CHECK 0's bound, and the CSV that carries it")
    hi = voigt_bounds(0.0)
    ck("a zero-porosity cell's in-plane ceiling is 16.39 W/(m.K)",
       abs(hi[0] - 16.3865) < 1e-3, "%.4f" % hi[0])
    ck("through-thickness ceiling is lower than in-plane",
       hi[2] < hi[0], "%.4f < %.4f" % (hi[2], hi[0]))
    ck("the 2026-08-07 kbar2 = 56.27 is caught by it",
       56.2701 > hi[0] * 1.02, "%.2fx the bound" % (56.2701 / hi[0]))
    ck("  while kbar1 = 15.47 and kbar3 = 12.70 pass",
       15.4686 <= hi[0] * 1.02 and 12.7047 <= hi[2] * 1.02)
    ck("porosity lowers the ceiling", voigt_bounds(0.324)[0] < hi[0],
       "%.4f at 32.4 %%" % voigt_bounds(0.324)[0])
    ck("no bound without a variant header", voigt_bounds(None) is None)

    # ---- the two defects the 2026-08-10 run exposed --------------------
    # (1) the bound must come from the DECK's card, not from the defaults.
    #     LTH2_COND_P32K60 ships k_long = 50.175; against the default 11.537
    #     its sound kbar1 = 19.1182 was reported IMPOSSIBLE.
    K60 = (12.7786, 50.1751, 2.46134)
    P32 = (12.7786, 8.99423, 2.46134)
    b_deck, b_dflt = voigt_bounds(0.324, K60), voigt_bounds(0.324)
    ck("the yarn sensitivity deck's kbar1 clears its OWN bound",
       19.1182 <= b_deck[0] * 1.02,
       "19.1182 vs %.4f (%.1f %% of it)" % (b_deck[0],
                                            100 * 19.1182 / b_deck[0]))
    ck("  and would have been called impossible against the defaults",
       19.1182 > b_dflt[0] * 1.02,
       "default bound %.4f -- this was the false alarm" % b_dflt[0])
    ck("a raised yarn conductivity raises the in-plane bound",
       voigt_bounds(0.324, K60)[0] > voigt_bounds(0.324, P32)[0])
    ck("but not the through-thickness one, which no axial yarn crosses",
       abs(voigt_bounds(0.324, K60)[2]
           - voigt_bounds(0.324, P32)[2]) < 1e-12,
       "%.4f both" % voigt_bounds(0.324, K60)[2])

    # (2) the porosity must be read from the whole deck, not a 4 kB window.
    import tempfile as _tf
    _d = _tf.mkdtemp()
    _f = os.path.join(_d, "Z_COND_P05.inp")
    with open(_f, "w") as fh:
        fh.write("*Heading\n test\n*Node\n")
        for i in range(1, 900):          # push the card past 4 kB of mesh
            fh.write("%d, 0.0, 0.0, 0.0\n" % i)
        fh.write("**   SiC    k = 25 dense -> 22.8510 W/(m.K) at 4.5 % "
                 "MATRIX porosity\n"
                 "*Material, Name=SIC_MATRIX_THERMAL\n"
                 "*Conductivity\n0.022851,\n"
                 "*Material, Name=CSIC_YARN_THERMAL\n"
                 "*Conductivity, type=ORTHO\n"
                 "0.0110899, 0.00363473, 0.00363473\n")
    vpz, _k = deck_variant(os.path.join(_d, "Z_COND_P05.odb"))
    ck("porosity is read past a mesh longer than the old 4 kB window",
       vpz is not None and abs(vpz - 0.045) < 1e-9,
       "%.4f -- the file says 4.5 %%, the NAME says 5 %%" % vpz)
    phz = deck_conductivities(os.path.join(_d, "Z_COND_P05.odb"))
    ck("and the phases come off the *Conductivity cards themselves",
       phz is not None and abs(phz[0] - 22.851) < 1e-9
       and abs(phz[1] - 11.0899) < 1e-9 and abs(phz[2] - 3.63473) < 1e-9,
       "%.4f / %.4f / %.4f W/(m.K)" % phz)
    ck("a missing deck returns None so the caller can say it fell back",
       deck_conductivities(os.path.join(_d, "nosuch.odb")) is None)

    # 4.5 vs 5.0 is not cosmetic: it moves the answer this file exists for.
    real = porosity_for_target([(0.0, 9.5251), (0.045, 8.8121),
                                (0.324, 5.4490)], target=MEASURED_K3)[0]
    named = porosity_for_target([(0.0, 9.5251), (0.05, 8.8121),
                                 (0.32, 5.4490)], target=MEASURED_K3)[0]
    ck("using the name instead of the file moves the porosity verdict",
       abs(real - named) > 0.001,
       "%.4f from the file vs %.4f from the name" % (real, named))
    import csv as _csv
    import tempfile
    f = os.path.join(tempfile.mkdtemp(), "t.csv")
    write_csv(f, [("A.odb", [15.4686, 56.2701, 12.7047], 0.0, None,
                   None, "unit basis under test")])
    got = list(_csv.DictReader(open(f)))[0]
    ck("the CSV marks the impossible column NO and the others yes",
       got["kbar1_admissible"] == "yes" and got["kbar2_admissible"] == "NO"
       and got["kbar3_admissible"] == "yes")
    ck("  and carries the bounds so a reader can re-check the call",
       abs(float(got["voigt_inplane"]) - hi[0]) < 1e-3)
    ck("  and says which unit set produced the numbers",
       got["unit_basis"] == "unit basis under test")

    print("\n G. the unit set is read off the deck, never remembered")
    # A deck built before 2026-08-11 is in the W/(mm.K) set and a deck built
    # after is in mW/(mm.K).  Both are readable, and which one applied has to
    # end up in the CSV -- reporting kbar 1000x wrong would look entirely
    # plausible (5.4 vs 5449 is obvious; 0.0054 vs 5.4 is not, and the
    # verdict against the Voigt ceiling would flip either way).
    d = tempfile.mkdtemp()
    legacy = os.path.join(d, "legacy.inp")
    open(legacy, "w").write("*Heading\n old deck, no stamp\n")
    f_leg, why_leg = unit_factor(legacy)
    ck("a deck with no stamp reads as the legacy W/(mm.K) set",
       f_leg == 1000.0 and "pre-2026" in why_leg, why_leg)
    stamped = os.path.join(d, "stamped.inp")
    open(stamped, "w").write(
        "*Heading\n**  UNITSTAMP: k_card_per_WmK = 1.0  (mW/(mm.K))\n")
    f_new, why_new = unit_factor(stamped)
    ck("a stamped deck reads its own factor", f_new == 1.0, why_new)
    ck("the two eras disagree by exactly the 1000 that caused this",
       abs(f_leg / f_new - 1000.0) < 1e-9)
    ck("a deck that is not there falls back rather than crashing",
       unit_factor(os.path.join(d, "absent.inp"))[0] == 1000.0)

    if fails:
        print("\nSELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("\nSELFTEST PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(report(args))
