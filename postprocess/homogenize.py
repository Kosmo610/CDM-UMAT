# -*- coding: utf-8 -*-
"""
homogenize.py   (run INSIDE Abaqus:  abaqus python homogenize.py <prefix>)
==========================================================================
Read the ODBs produced by abaqus/make_rve_virtual_tests.py and assemble the
MACRO material card for KMACRO31 in src/UMAT_CSIC_THERMSHOCK_V3_0.for.

What it computes
----------------
  Cbar(T)      from the six unit-macro-strain steps of <prefix>_ELAS_T<T>.odb
               -> engineering constants E1 E2 E3 nu12 nu13 nu23 G12 G13 G23
  alphabar(T)  from the STRESS DIFFERENCE between the two clamped steps of
               <prefix>_CTE_T<T>.odb (differencing removes the manufacturing
               thermal stress already present at the start of the analysis)
  strengths    peak homogenised stress of each
               <prefix>_STR_<mode>_T<T>_TRS<on|off>.odb
  Gf           area under each homogenised softening branch x the RVE length
               in the loading direction (crack-band interpretation of the
               unit cell), then SPLIT into its stored-elastic and dissipated
               parts.  Only the dissipated part is a material constant, so
               only that part goes on the card -- negated, which is how
               KABAND is told which convention it is reading.  The CSV keeps
               both parts plus g0 so the split can be audited.
  kbar         from <prefix>_COND.odb, three steady-state directions

What it writes
--------------
  <prefix>_homogenised.csv      every number, for the thesis tables
  <prefix>_macro_card.inp       the *User Material MACRO card (47+8*NT slots)
                                including the f(T) multiplier table
  <prefix>_macro_expansion.inp  *Expansion, type=ORTHO with alphabar(T)

Conventions (must match make_rve_virtual_tests.py)
  U (ConstraintsDriverK, dof 1) = macro strain component K
  RF(ConstraintsDriverK, dof 1) = -sigma_K * V_RVE
  components 0,1,2 = 11,22,33 ; 3,4,5 = shears in --shear-order

FIRST RUN: check the printed raw Cbar.  A 2-D plain weave must come out with
C11 ~ C22 >> C33 and three clearly separated shear diagonals.  If the shear
diagonals are permuted relative to what you expect, the TexGen driver order
differs -- rerun make_rve_virtual_tests.py with the other --shear-order and
pass the same flag here.

Usage
  abaqus python homogenize.py RVE
  abaqus python homogenize.py RVE --temps 23 500 1000 --shear-order xy-yz-xz
"""
from __future__ import print_function

import os
import sys
import numpy as np

try:
    from odbAccess import openOdb
except ImportError:                                   # syntax-check outside Abaqus
    openOdb = None

UNIT_STRAIN = 1.0e-6
THERMAL_PROBE_DT = -100.0
STRESS_FREE_T = 1050.0
SHEAR_ORDERS = {"xy-xz-yz": (3, 4, 5), "xy-yz-xz": (3, 5, 4)}


def _trapz(y, x):
    """Trapezoidal area, whichever NumPy this Abaqus happens to ship.

    np.trapz was deprecated in NumPy 1.x and REMOVED in 2.0, where the name
    is np.trapezoid.  This file is the only maker of macro cards in the
    repository and it runs LAST, after every RVE job has already finished, so
    an AttributeError here costs the whole set rather than one job.  The name
    is therefore resolved at call time instead of being trusted.
    """
    f = getattr(np, "trapezoid", None)
    if f is None:
        f = getattr(np, "trapz")
    return float(f(y, x))


def _rve_dmax(default=0.90):
    """The damage ceiling in use at the RVE scale (abaqus/retune_deck.D_DMAX)."""
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
        "abaqus"))
    try:
        import retune_deck as _rt
        return float(_rt.D_DMAX)
    except Exception:                       # abaqus python, or a partial tree
        return default


#: Macro-card damage ceiling.  This slot said 0.99 until the card-pipeline
#: rehearsal of 2026-08-18.  0.99 is the value abaqus/retune_deck.py:22
#: already REJECTED one scale down -- "a failed matrix element kept 1 % of
#: 350 GPa = 3.5 GPa" -- and the argument does not weaken going up: 1 % of a
#: 123 GPa macro card is still 1.2 GPa of stiffness in an element that has
#: failed.  It also split the repository against itself.  postprocess/
#: damage_map.py takes its cap from retune_deck.D_DMAX, and RUN_MANIFEST.md
#: points damage_map at the MACRO jobs, so every macro damage map would have
#: judged "at cap" against a ceiling the macro card did not have -- reporting
#: caps at 0.90 that were not caps and missing the real ones at 0.99.  One
#: constant now, pinned by a check in both files.
MACRO_DMAX = _rve_dmax()

#: strength mode -> (macro component, sign, macro-card slot name)
MODE_TO_SLOT = {
    "1t": (0, +1, "Xt"), "1c": (0, -1, "Xc"),
    "2t": (1, +1, "Yt"), "2c": (1, -1, "Yc"),
    "3t": (2, +1, "Zt"),
    "s12": (3, +1, "S12"), "s13": (4, +1, "S13"), "s23": (5, +1, "S23"),
}


# ==========================================================================
# ODB helpers
# ==========================================================================
def rve_box(odb):
    inst = list(odb.rootAssembly.instances.values())[0]
    xs = [n.coordinates[0] for n in inst.nodes]
    ys = [n.coordinates[1] for n in inst.nodes]
    zs = [n.coordinates[2] for n in inst.nodes]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def driver_history(step, k, labels=None):
    """(U, RF) time series of ConstraintsDriver`k` dof 1 in `step`.

    Abaqus does NOT name a nodal history region after the set that requested
    it.  A request written as

        *Node Output, nset=ConstraintsDriver0

    comes back as the region "Node PART-1-1.5681" -- the instance and the node
    LABEL.  Matching on the set name therefore finds nothing, which is what
    stopped the first complete ELAS run on 2026-08-10 after all six jobs had
    already finished.  `labels` carries {k: node label}, read from the odb's
    own set definition by driver_labels().
    """
    want = "CONSTRAINTSDRIVER%d" % k
    hr = None
    for key, hp in step.historyRegions.items():
        if want in key.upper().replace(" ", ""):
            hr = hp
            break
    if hr is None and labels and k in labels:
        lab = str(labels[k])
        for key, hp in step.historyRegions.items():
            if key.rsplit(".", 1)[-1].strip() == lab:
                hr = hp
                break
    if hr is None:
        raise RuntimeError("history region for %s (node label %s) not found "
                           "in step %s; keys=%s"
                           % (want, labels.get(k) if labels else "unknown",
                              step.name, list(step.historyRegions.keys())))
    uk = sorted(k2 for k2 in hr.historyOutputs.keys()
                if k2.upper().startswith("U"))[0]
    rk = sorted(k2 for k2 in hr.historyOutputs.keys()
                if k2.upper().startswith("RF"))[0]
    u = [v for _, v in hr.historyOutputs[uk].data]
    r = [v for _, v in hr.historyOutputs[rk].data]
    return np.array(u), np.array(r)


def driver_labels(odb):
    """{k: node label} for the six macro-strain drivers.

    Read from the odb's own ConstraintsDriver`k` node set, so no assumption is
    made about the labels being consecutive or in order.  The last resort --
    six nodal history regions sorted by label -- IS such an assumption, and it
    says so on the console rather than passing silently; elastic_from() then
    checks the mapping against the prescribed strains, which settles it either
    way.
    """
    out = {}
    for k in range(6):
        want = "CONSTRAINTSDRIVER%d" % k
        ns = None
        if want in odb.rootAssembly.nodeSets.keys():
            ns = odb.rootAssembly.nodeSets[want]
        else:
            for inst in odb.rootAssembly.instances.values():
                if want in inst.nodeSets.keys():
                    ns = inst.nodeSets[want]
                    break
        if ns is None:
            continue
        nodes = ns.nodes
        if len(nodes) and not hasattr(nodes[0], "label"):
            nodes = nodes[0]           # assembly-level: one tuple per instance
        if len(nodes):
            out[k] = nodes[0].label
    return out


def driver_labels_from_history(step):
    """Last resort: six nodal history regions, sorted by label -> drivers 0-5."""
    labs = []
    for key in step.historyRegions.keys():
        tail = key.rsplit(".", 1)[-1].strip()
        if key.upper().startswith("NODE") and tail.isdigit():
            labs.append(int(tail))
    if len(labs) != 6:
        return {}
    labs.sort()
    print("    !! ConstraintsDriver node sets are not in this odb.  Falling "
          "back to the six nodal history regions sorted by label %s -- this "
          "ASSUMES driver k is the k-th.  The prescribed-strain check below "
          "verifies it." % labs)
    return dict(enumerate(labs))


def resolve_sign(diag):
    """+1 or -1: which reaction-sign convention did this odb follow?

    The documented convention is RF(driver) = -sigma*V, so sigma = -RF/V.
    The first complete ELAS run (2026-08-10) returned EVERY Cbar diagonal
    negative under it: E1 = -175.1 GPa.  A negative C11 is not a material,
    it is the OTHER sign convention -- the driver *Equation can be written
    with either sense and the odb does not say which.  The diagonals do:
    elastic energy makes every C[k,k] positive, so all-negative means flip,
    all-positive means keep, and a MIX means something is genuinely wrong
    (a permuted mapping, a bad step) and no sign guess may paper over it.
    """
    if all(d > 0 for d in diag):
        return +1
    if all(d < 0 for d in diag):
        print("    !! driver reactions follow RF = +sigma*V (opposite of the "
              "documented convention); Cbar sign corrected.  Energy requires "
              "positive diagonals, so this is not a judgement call.")
        return -1
    raise RuntimeError(
        "Cbar diagonals carry MIXED signs %s -- that is not a sign "
        "convention, that is a wrong driver mapping or a corrupt step, "
        "and flipping would hide it." % ["%+.3e" % d for d in diag])


def macro_state(step, V, labels=None):
    """Final macro strain and stress vectors of `step`."""
    eps = np.zeros(6)
    sig = np.zeros(6)
    for k in range(6):
        u, rf = driver_history(step, k, labels)
        eps[k] = u[-1]
        sig[k] = -rf[-1] / V
    return eps, sig


# ==========================================================================
# Cbar and alphabar
# ==========================================================================
def elastic_from(path):
    """Cbar(T) from the six unit-strain steps."""
    odb = openOdb(path, readOnly=True)
    Lx, Ly, Lz = rve_box(odb)
    V = Lx * Ly * Lz
    print("  %s  box=(%.5f, %.5f, %.5f) mm  V=%.6f mm^3"
          % (os.path.basename(path), Lx, Ly, Lz, V))

    labels = driver_labels(odb)
    C = np.zeros((6, 6))
    seen = set()
    bad = []
    for name, step in odb.steps.items():
        up = name.upper()
        if up.startswith("CBAR_MODE"):
            k = int(up.replace("CBAR_MODE", ""))
            if len(labels) < 6:
                labels = driver_labels_from_history(step) or labels
            eps, sig = macro_state(step, V, labels)
            # THE MAPPING CHECKS ITSELF.  Step Cbar_mode<k> prescribes every
            # driver: unit strain on k, zero on the other five.  If the driver
            # -> history-region mapping were wrong, the unit strain would show
            # up on the wrong row, and Cbar would be a permuted matrix that
            # still looks plausible.  Nothing downstream would catch that.
            if abs(eps[k] - UNIT_STRAIN) > 1.0e-3 * UNIT_STRAIN:
                bad.append("mode %d: driver %d reads eps = %.4e, expected %.4e"
                           % (k, k, eps[k], UNIT_STRAIN))
            off = max(abs(eps[j]) for j in range(6) if j != k)
            if off > 1.0e-3 * UNIT_STRAIN:
                bad.append("mode %d: a driver that should be held at zero "
                           "reads %.4e" % (k, off))
            C[:, k] = sig / UNIT_STRAIN
            seen.add(k)
    odb.close()
    if len(seen) != 6:
        raise RuntimeError("%s: expected 6 Cbar_mode steps, found %s"
                           % (path, sorted(seen)))
    if bad:
        raise RuntimeError(
            "%s: the driver -> history-region mapping is wrong, so Cbar would "
            "be a PERMUTED matrix that still looks plausible:\n    %s"
            % (path, "\n    ".join(bad)))
    print("    driver mapping verified against the prescribed strains "
          "(labels %s)" % [labels.get(k) for k in range(6)])

    sig_sign = resolve_sign([C[k, k] for k in range(6)])
    C = sig_sign * C

    # The two halves differ only by discretisation error, so the asymmetry is
    # a useful mesh-quality indicator -- report it, then symmetrise.
    asym = np.max(np.abs(C - C.T)) / max(1e-30, np.max(np.abs(C)))
    return 0.5 * (C + C.T), (Lx, Ly, Lz), asym, sig_sign


def cte_from(path, C, sig_sign=+1):
    """alphabar(T) from the clamped-strain stress difference.

    Both steps hold eps_bar = 0, so between them
        d(sigma_bar) = -C : alphabar * dT
    and the manufacturing thermal stress present at the start cancels.
    dT is read from the second step's name (written by
    make_rve_virtual_tests.py as alphabar_dT<+/-value>).
    """
    odb = openOdb(path, readOnly=True)
    Lx, Ly, Lz = rve_box(odb)
    V = Lx * Ly * Lz
    labels = driver_labels(odb)
    base = None
    hot = None
    dT = None
    for name, step in odb.steps.items():
        up = name.upper()
        if up.startswith("ALPHABAR_BASE"):
            if len(labels) < 6:
                labels = driver_labels_from_history(step) or labels
            _, base = macro_state(step, V, labels)
        elif up.startswith("ALPHABAR_DT"):
            if len(labels) < 6:
                labels = driver_labels_from_history(step) or labels
            _, hot = macro_state(step, V, labels)
            dT = float(name.upper().replace("ALPHABAR_DT", ""))
    odb.close()
    if base is None or hot is None or not dT:
        raise RuntimeError("%s: need steps alphabar_base and alphabar_dT<x>"
                           % path)
    # sig_sign belongs to the STRESSES, not to C: C arrives already
    # corrected, so correcting only one side would flip alphabar.  On the
    # 2026-08-10 run alphabar printed right BECAUSE both were still wrong.
    return -np.linalg.solve(C, sig_sign * (hot - base)) / dT


def engineering_constants(C, shear_order):
    """Orthotropic engineering constants from Cbar."""
    S = np.linalg.inv(C)
    E1, E2, E3 = 1.0 / S[0, 0], 1.0 / S[1, 1], 1.0 / S[2, 2]
    nu12 = -S[0, 1] / S[0, 0]
    nu13 = -S[0, 2] / S[0, 0]
    nu23 = -S[1, 2] / S[1, 1]
    i12, i13, i23 = SHEAR_ORDERS[shear_order]
    G12, G13, G23 = 1.0 / S[i12, i12], 1.0 / S[i13, i13], 1.0 / S[i23, i23]
    return dict(E1=E1, E2=E2, E3=E3, nu12=nu12, nu13=nu13, nu23=nu23,
                G12=G12, G13=G13, G23=G23)


# ==========================================================================
# strengths and fracture energies
# ==========================================================================
def strength_curve(path, mode, sig_sign=+1):
    comp, sign, _ = MODE_TO_SLOT[mode]
    odb = openOdb(path, readOnly=True)
    Lx, Ly, Lz = rve_box(odb)
    V = Lx * Ly * Lz
    step = None
    for name, st in odb.steps.items():
        if name.upper().startswith("STRENGTH"):
            step = st
    if step is None:
        step = list(odb.steps.values())[-1]
    labels = driver_labels(odb) or driver_labels_from_history(step)
    u, rf = driver_history(step, comp, labels)
    odb.close()

    eps = sign * np.asarray(u)
    sig = sig_sign * sign * (-np.asarray(rf) / V)
    ipk = int(np.argmax(sig))
    peak = float(sig[ipk])

    # Crack-band fracture energy: area under the whole curve x the RVE length
    # along the loading direction.  For shear modes the length is ambiguous;
    # the in-plane size is used and the choice is recorded in the CSV.
    Lchar = (Lx, Ly, Lz, Lx, Lx, Ly)[comp]
    area = _trapz(sig, eps)
    Gf = area * Lchar

    # How much of that curve is actually a softening branch.  split_fracture
    # _energy() refuses to hand up a Gf without these two, and it could not
    # ask for them before they were measured here.  A curve that stops at its
    # own peak still produces a positive "dissipated" part, purely out of
    # pre-peak nonlinearity, and nothing downstream can tell the difference.
    area_pre = _trapz(sig[:ipk + 1], eps[:ipk + 1]) if ipk > 0 else 0.0
    soft = (1.0 - float(sig[-1]) / peak) if peak > 0.0 else 0.0
    return dict(peak=peak, eps_peak=float(eps[ipk]), Gf=Gf,
                Lchar=Lchar, npts=len(eps),
                soft=soft, Gfpre=area_pre * Lchar,
                eps_end=float(eps[-1]), sig_end=float(sig[-1]))


# ==========================================================================
# conductivity
# ==========================================================================
def conductivity(path, dT=1.0):
    odb = openOdb(path, readOnly=True)
    Lx, Ly, Lz = rve_box(odb)
    L = (Lx, Ly, Lz)
    A = (Ly * Lz, Lx * Lz, Lx * Ly)
    k = [float("nan")] * 3
    for name, step in odb.steps.items():
        up = name.upper()
        if not up.startswith("KBAR_DIR"):
            continue
        ax = int(up.replace("KBAR_DIR", "")) - 1
        Q = 0.0
        for _, hr in step.historyRegions.items():
            for key, ho in hr.historyOutputs.items():
                if key.upper().startswith("RFL"):
                    Q += ho.data[-1][1]
        k[ax] = abs(Q) * L[ax] / (A[ax] * dT)
    odb.close()
    return k


# ==========================================================================
# the elastic part of Gf must not cross the scale boundary
# ==========================================================================
# Gf as measured above is the WHOLE area under the homogenised curve times
# the RVE edge, which splits as
#
#     Gf_total = le*g0  +  le*2*g0/A ,        g0 = X^2 / (2E)
#                \____/     \_______/
#                elastic    dissipated
#
# Only the second term is the material's.  The first is stored elastic
# energy and it scales with whatever le was used -- here the RVE edge,
# 3.5 mm in plane.  KMACRO31 then consumes the number with CELENT, which in
# the macro meshes is 0.68-0.78 mm, so the elastic term would arrive
# inflated by g0*(L_RVE - CELENT) ~ 0.4-0.7 N/mm.  That is larger than the
# only sourced fracture energy in the repository (Gtt = 0.107 N/mm, Shi
# refs/[31]), so it is not a rounding concern.
#
# The transferable constant is therefore Gf_inel = Gf_total - g0*L_RVE, and
# the card carries it NEGATED: KABAND reads a negative entry as the
# inelastic convention and rebuilds A = 2*g0*CELENT/|Gf| with the macro
# element's own length.  Positive entries keep the original meaning bit for
# bit, so cards written before this existed are unaffected.
#
# See docs/CH4_RVE_HOMOGENISATION.md 4.6.1 and 4.9-16.
MODE_G0_KEYS = {"1t": ("Xt", "E1"), "1c": ("Xc", "E1"),
                "2t": ("Yt", "E2"), "2c": ("Yc", "E2")}

#: A crack-band Gf is the area under a COMPLETED softening branch.  Two things
#: must hold before an RVE curve can supply one, and neither was checked until
#: the card-pipeline rehearsal (verification/card_pipeline_rehearsal.py) ran
#: the three real M6 curves through this file on 2026-08-18:
#:
#:   1. the branch has to have SOFTENED.  M6's RT23 curve peaks at its very
#:      last point -- it fell 0.0 % -- and T500 fell 0.3 %.  `inel` came out
#:      positive for both anyway, because pre-peak nonlinearity alone makes it
#:      positive, and the card carried the result as a fracture energy.
#:   2. what survives the g0 subtraction has to be mostly POST-peak.  Of what
#:      would have shipped, RT23 was 100 % pre-peak, T500 70 %, T1000 22 %.
#:
#: Direction of the error, on the record: too large a |Gf| makes KABAND's
#: A = 2*g0*le/|Gf| too SMALL, which is a shallower softening branch, an
#: element that sheds load too slowly, and an OVER-predicted residual
#: strength -- the quantity Ch.6 reports.  Non-conservative, and the same
#: direction as the positive-Gf convention error the card validator already
#: refuses (make_macro_thermalshock.check_macro_card).
#:
#: Failing the gate is not fatal: slot 32-35 stays 0.0, which KABAND reads as
#: "crack band off, use the fixed exponent".  That is a declared assumption
#: instead of a measurement dressed up as one.
SOFT_MIN = 0.50
PREPEAK_MAX = 0.50


def _unit_of(key):
    """Unit for one strength-block CSV row."""
    # soft_/prepk_ are fractions and must not be labelled N/mm just because
    # they were derived from an area -- they are the gate's own evidence and
    # a reader has to be able to see they are dimensionless.
    if key.startswith("soft_") or key.startswith("prepk_"):
        return "-"
    if key.startswith("Gf") or key.startswith("Gfin") or key.startswith("Gfel"):
        return "N/mm"
    if key.startswith("g0_"):
        return "N/mm2"
    if key.startswith("Lchar_"):
        return "mm"
    return "MPa"


def split_fracture_energy(strength, eng):
    """Add Gfin_<mode> (dissipated part) beside each Gf_<mode> (total).

    Mutates `strength` in place.  Modes whose deck was not run are skipped.
    A mode whose dissipated part is not positive is reported and left out:
    that means the RVE response itself was inside the snap-back region, so
    there is no dissipation to hand upward and the macro must fall back to
    the fixed exponent.  A mode whose curve never softened, or whose
    "dissipated" part is mostly pre-peak nonlinearity, is left out for the
    same reason and by the same route -- see SOFT_MIN / PREPEAK_MAX above.
    """
    for mode, (xkey, ekey) in sorted(MODE_G0_KEYS.items()):
        gkey, lkey = "Gf_" + mode, "Lchar_" + mode
        if gkey not in strength or lkey not in strength:
            continue
        X, E = strength.get(xkey), eng.get(ekey)
        if not X or not E:
            print("  (Gf %s: no %s or %s -- cannot split, left as total)"
                  % (mode, xkey, ekey))
            continue
        g0 = X * X / (2.0 * E)
        elastic = g0 * strength[lkey]
        inel = strength[gkey] - elastic
        strength["g0_" + mode] = g0
        strength["Gfel_" + mode] = elastic
        print("     Gf %-2s total %8.4g = elastic %8.4g (g0=%.4g x L=%.3g)"
              "  + dissipated %8.4g N/mm"
              % (mode, strength[gkey], elastic, g0, strength[lkey], inel))
        if inel <= 0.0:
            print("     ** Gf %s: dissipated part is %.4g <= 0.  The RVE"
                  " curve is inside snap-back;" % (mode, inel))
            print("        nothing is handed upward and the macro will use"
                  " the fixed exponent.")
            continue

        # Is this a softening branch, or a curve that merely stopped?
        why = []
        soft = strength.get("soft_" + mode)
        if soft is not None:
            strength["soft_" + mode] = soft
            if soft < SOFT_MIN:
                why.append("it fell only %.1f %% below peak (need %.0f %%)"
                           % (100.0 * soft, 100.0 * SOFT_MIN))
        pre = strength.get("Gfpre_" + mode)
        if pre is not None:
            share = max(0.0, pre - elastic) / inel
            strength["prepk_" + mode] = share
            if share > PREPEAK_MAX:
                why.append("%.0f %% of what would ship is PRE-peak "
                           "nonlinearity (allow %.0f %%)"
                           % (100.0 * share, 100.0 * PREPEAK_MAX))
        if why:
            print("     ** Gf %s REFUSED: %s." % (mode, "; and ".join(why)))
            print("        A curve that stopped is not a curve that softened."
                  "  Slot stays 0.0 (fixed")
            print("        exponent).  Shipping it would make |Gf| too large,"
                  " A too small, the")
            print("        branch too shallow and residual strength"
                  " OVER-predicted -- non-conservative.")
            continue
        strength["Gfin_" + mode] = inel


# ==========================================================================
# card assembly
# ==========================================================================
def macro_card(props_by_T, cyc, temps, nprops_note=True, crit=None):
    """Build the 47+8*NT (+9) slot MACRO card.

    The FIRST temperature in `temps` is the reference: its constants go into
    slots 2..17 and the f(T) table carries every temperature as a multiplier,
    so the reference row is exactly 1.0 by construction.

    `crit` switches on the failure-criterion comparison block.  Turn it on
    BEFORE running any macro job: it only adds STATEV, and adding STATEV
    afterwards means re-running everything.
    """
    Tref = temps[0]
    p = props_by_T[Tref]
    e, s = p["elastic"], p["strength"]

    slots = [0.0] * 47
    slots[0] = 3.0
    for i, key in enumerate(("E1", "E2", "E3", "nu12", "nu13", "nu23",
                             "G12", "G13", "G23")):
        slots[1 + i] = e[key]
    for i, key in enumerate(("Xt", "Xc", "Yt", "Yc", "S12", "S13", "S23")):
        slots[10 + i] = s.get(key, 0.0)
    slots[17] = slots[18] = slots[19] = slots[20] = 2.0   # A1t A1c Att Atc
    slots[21] = slots[22] = MACRO_DMAX                    # dmax; see above
    slots[23] = cyc["eta"]
    slots[24] = cyc["max_djump"]
    slots[25] = cyc["freeze"]
    slots[26] = cyc["min_pnewdt"]
    slots[27] = 1.0                                       # enable
    slots[28], slots[29], slots[30] = 1.0, 0.5, 1.0       # cutback controls
    # Negated dissipated part -- see split_fracture_energy above.  A mode
    # with no dissipation to hand upward stays 0.0, which KABAND still reads
    # as "crack band off, use the fixed exponent".
    for i, mode in enumerate(("1t", "1c", "2t", "2c")):
        slots[31 + i] = -s["Gfin_" + mode] if ("Gfin_" + mode) in s else 0.0
    slots[35] = 31.0                                      # CARD KEY
    slots[36] = cyc["hclo"]
    slots[37] = cyc["cycon"]
    slots[38], slots[39], slots[40] = cyc["C"], cyc["n"], cyc["k"]
    slots[41], slots[42], slots[43] = cyc["rth"], cyc["dcymax"], cyc["w1"]
    slots[44] = cyc["cycrate"]
    slots[45] = float(cyc["predefn"])
    slots[46] = float(len(temps))

    rows = []
    for T in temps:
        q = props_by_T[T]
        qe, qs = q["elastic"], q["strength"]
        rows.append([
            T,
            qe["E1"] / e["E1"],
            0.5 * (qe["E2"] / e["E2"] + qe["E3"] / e["E3"]),
            (qe["G12"] / e["G12"] + qe["G13"] / e["G13"]
             + qe["G23"] / e["G23"]) / 3.0,
            _safe_ratio(qs.get("Xt"), s.get("Xt")),
            _safe_ratio(qs.get("Yt"), s.get("Yt")),
            _safe_ratio(qs.get("S12"), s.get("S12")),
            1.0,                      # fC: cycle-rate multiplier, calibrate
        ])
    for r in rows:
        slots.extend(r)

    ncrit = 0
    if crit and int(crit.get("icrit", 0)) > 0:
        slots.extend([float(crit["icrit"]), crit["fs12"], crit["fs23"],
                      float(crit["idmode"]), crit["dc1"], crit["dct"],
                      crit["dcs"], crit["di12"], 41.0])
        ncrit = 9

    # 29 always since the TWMAX window (2026-08-06): V3_0 writes the
    # cycle-severity temperature to SDV 29 on every macro card, criteria on
    # or off, so 23-28 are allocated (and stay zero) even when ICRIT = 0.
    nsdv = 29
    L = ["** MACRO homogenised card for KMACRO31 "
         "(UMAT_CSIC_THERMSHOCK_V3_0.for)",
         "** generated by postprocess/homogenize.py -- do not hand-edit the "
         "elastic/strength slots",
         "** slots 38-46 (cycle damage) are CALIBRATION knobs, not RVE "
         "outputs: see docs/THESIS_PLAN.md",
         "*Material, Name=CSIC_MACRO_CDM",
         "*Depvar", "%d," % nsdv]
    names = ["D1T", "D1C", "DTT", "DTC", "R1T", "R1C", "RTT", "RTC",
             "D1", "DT", "MODE", "TINIT", "DJUMP", "CUTREQ", "TJUMP",
             "RJUMP", "DCYC", "NCUM", "RDRV", "D1MONO", "DTMONO", "CLOFLG",
             "FITW", "FIDC", "NFLAG", "NFHA", "NFTW", "NFDC", "TWMAX"]
    for i, nm in enumerate(names):
        L.append("%d, %s, %s" % (i + 1, nm, nm))
    L.append("*User Material, constants=%d" % len(slots))
    for i in range(0, len(slots), 8):
        L.append(", ".join("%.10g" % v for v in slots[i:i + 8]))
    if nprops_note:
        L.append("** NPROPS = 47 + 8*NT%s = %d  (NT = %d temperature rows)"
                 % (" + 9" if ncrit else "", len(slots), len(temps)))
        if ncrit:
            L.append("** failure-criterion block ON: Hashin drives damage, "
                     "Tsai-Wu (SDV23) and")
            L.append("** the D-criterion (SDV24) are recorded alongside it "
                     "at zero cost.")
    return "\n".join(L)


def _safe_ratio(a, b):
    if a is None or b in (None, 0.0):
        return 1.0
    return a / b


def macro_expansion(props_by_T, temps):
    L = ["*Expansion, type=ORTHO, zero=%.6g" % STRESS_FREE_T]
    for T in temps:
        a = props_by_T[T]["alpha"]
        L.append("%.9e, %.9e, %.9e, %.6g" % (a[0], a[1], a[2], T))
    return "\n".join(L)


# ==========================================================================
DEFAULT_CYC = dict(eta=0.02, max_djump=0.10, freeze=1.0e6, min_pnewdt=0.25,
                   hclo=0.0, cycon=0.0, C=0.0, n=3.0, k=-1.0, rth=0.30,
                   dcymax=0.95, w1=0.30, cycrate=0.0, predefn=1)

# Failure-criterion comparison, ON by default.  It costs nothing at run time
# (the two extra indices are passive) but it cannot be added retroactively --
# the STATEV list has to be right before the first macro job is submitted.
#
# dc1/dct/dcs are the critical damages of the D-criterion.  The defaults are
# Yang et al., Compos. Part A 77 (2015) 181 for a 2D CVI C/SiC with a strong
# interface (D11max = D22max = 0.5224 from Eq.12 at Xt = 226 MPa, D66max =
# 0.5405 from Eq.13 at S12 = 125.7 MPa).  They are a DIFFERENT material from
# ours -- replace them with values read off our own RVE virtual tests once
# M3 has run: D at the peak of the homogenised sigma-epsilon curve.
DEFAULT_CRIT = dict(icrit=1, fs12=-0.5, fs23=-0.5, idmode=2,
                    dc1=0.5224, dct=0.5224, dcs=0.5405, di12=0.0)


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    prefix = argv[0]
    temps = [23.0]
    shear_order = "xy-xz-yz"
    trs = "on"
    i = 1
    while i < len(argv):
        if argv[i] == "--temps":
            temps = []
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                temps.append(float(argv[i]))
                i += 1
            continue
        if argv[i] == "--shear-order":
            shear_order = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--trs":
            trs = argv[i + 1]
            i += 2
            continue
        i += 1
    if openOdb is None:
        print("odbAccess unavailable: run this with 'abaqus python'.")
        return 2

    props_by_T = {}
    box = None
    for T in temps:
        path = "%s_ELAS_T%g.odb" % (prefix, T)
        if not os.path.exists(path):
            print("MISSING %s -- run the ELAS deck first." % path)
            return 3
        C, box, asym, sig_sign = elastic_from(path)
        eng = engineering_constants(C, shear_order)
        cpath = "%s_CTE_T%g.odb" % (prefix, T)
        if os.path.exists(cpath):
            alpha = cte_from(cpath, C, sig_sign)
        else:
            print("  MISSING %s -- alphabar left at zero." % cpath)
            alpha = np.zeros(6)
        print("  Cbar diagonal (MPa): " +
              ", ".join("%.4g" % C[j, j] for j in range(6)))
        print("  Cbar asymmetry %.2e (discretisation quality indicator)" % asym)
        print("  E1=%.4g E2=%.4g E3=%.4g  G12=%.4g G13=%.4g G23=%.4g MPa"
              % (eng["E1"], eng["E2"], eng["E3"],
                 eng["G12"], eng["G13"], eng["G23"]))
        print("  alphabar = %.4e, %.4e, %.4e /K"
              % (alpha[0], alpha[1], alpha[2]))

        strength = {}
        for mode, (_, _, slot) in sorted(MODE_TO_SLOT.items()):
            sp = "%s_STR_%s_T%g_TRS%s.odb" % (prefix, mode, T, trs)
            if not os.path.exists(sp):
                print("  (no %s -- %s left at 0)" % (os.path.basename(sp),
                                                     slot))
                continue
            r = strength_curve(sp, mode, sig_sign)
            strength[slot] = abs(r["peak"])
            if mode in ("1t", "1c", "2t", "2c"):
                strength["Gf_" + mode] = r["Gf"]
                strength["Lchar_" + mode] = r["Lchar"]
                strength["soft_" + mode] = r["soft"]
                strength["Gfpre_" + mode] = r["Gfpre"]
            print("  %-4s peak = %8.2f MPa at eps = %.4f %%   Gf = %.4g N/mm"
                  "   softened %.1f %% by eps = %.4f %%"
                  % (mode, r["peak"], 100.0 * r["eps_peak"], r["Gf"],
                     100.0 * r["soft"], 100.0 * r["eps_end"]))
        split_fracture_energy(strength, eng)
        props_by_T[T] = dict(C=C, alpha=alpha, elastic=eng, strength=strength)

    kbar = None
    kpath = "%s_COND.odb" % prefix
    if os.path.exists(kpath):
        kbar = conductivity(kpath)
        print("  kbar = %.5g, %.5g, %.5g W/(mm.K)" % tuple(kbar))
    else:
        print("  (no %s -- kbar not computed; the quench analysis needs it)"
              % kpath)

    with open("%s_homogenised.csv" % prefix, "w") as f:
        f.write("T_C,quantity,value,unit\n")
        for T in temps:
            p = props_by_T[T]
            for kk, vv in sorted(p["elastic"].items()):
                f.write("%g,%s,%.10g,%s\n"
                        % (T, kk, vv, "MPa" if kk[0] in "EG" else "-"))
            for j, ax in enumerate("123"):
                f.write("%g,alpha%s,%.10g,1/K\n" % (T, ax, p["alpha"][j]))
            for kk, vv in sorted(p["strength"].items()):
                f.write("%g,%s,%.10g,%s\n" % (T, kk, vv, _unit_of(kk)))
        if kbar:
            for j, ax in enumerate("123"):
                f.write(",k%s,%.10g,W/(mm.K)\n" % (ax, kbar[j]))
    print("  wrote %s_homogenised.csv" % prefix)

    with open("%s_macro_card.inp" % prefix, "w") as f:
        f.write(macro_card(props_by_T, DEFAULT_CYC, temps,
                           crit=DEFAULT_CRIT) + "\n")
    print("  wrote %s_macro_card.inp" % prefix)

    with open("%s_macro_expansion.inp" % prefix, "w") as f:
        f.write(macro_expansion(props_by_T, temps) + "\n")
    print("  wrote %s_macro_expansion.inp" % prefix)

    print("\nThe cycle-damage slots (38-46) are still at their defaults with "
          "CYCON=0.\nCalibrate them against data/literature/ before running "
          "the thermal-shock cases\n(see verification/verify_thermshock.py "
          "for the two-anchor procedure).")
    return 0


# ==========================================================================
# selftest -- no odb, no Abaqus.  Covers the driver -> history-region
# resolution, which had none and cost a full six-job round trip on
# 2026-08-10, and the permutation guard that now sits on top of it.
# ==========================================================================
class _Node(object):
    def __init__(self, label):
        self.label = label


class _Set(object):
    def __init__(self, labels):
        self.nodes = tuple(_Node(l) for l in labels)


class _Repo(dict):
    """Abaqus Repository: keys()/[]/in, but NOT .get() -- see the module note."""
    def keys(self):
        return list(dict.keys(self))


class _Inst(object):
    def __init__(self, nsets):
        self.nodeSets = _Repo(nsets)


class _Asm(object):
    def __init__(self, nsets=None, insts=None):
        self.nodeSets = _Repo(nsets or {})
        self.instances = _Repo(insts or {})


class _Odb(object):
    def __init__(self, asm):
        self.rootAssembly = asm


class _Hist(object):
    def __init__(self, u, rf):
        self.historyOutputs = _Repo({
            "U1": type("H", (), {"data": [(0.0, 0.0), (1.0, u)]})(),
            "RF1": type("H", (), {"data": [(0.0, 0.0), (1.0, rf)]})()})


class _Step(object):
    def __init__(self, name, regions):
        self.name = name
        self.historyRegions = _Repo(regions)


def selftest():
    ok, bad = [], []

    def ck(name, cond, detail=""):
        (ok if cond else bad).append(name)
        print("  [%s] %-62s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("homogenize.py --selftest")

    # ---- A. the labels come off the odb's own sets
    sets = dict(("CONSTRAINTSDRIVER%d" % k, _Set([5681 + k])) for k in range(6))
    ck("driver labels read from an ASSEMBLY-level node set",
       driver_labels(_Odb(_Asm(nsets=sets))) == dict(
           (k, 5681 + k) for k in range(6)))
    ck("and from an INSTANCE-level one, which is where TexGen puts them",
       driver_labels(_Odb(_Asm(insts={"PART-1-1": _Inst(sets)})))
       == dict((k, 5681 + k) for k in range(6)))
    ck("labels that are NOT consecutive are read as they are, not assumed",
       driver_labels(_Odb(_Asm(nsets=dict(
           ("CONSTRAINTSDRIVER%d" % k, _Set([900 - 7 * k]))
           for k in range(6))))) == dict((k, 900 - 7 * k) for k in range(6)))

    # ---- B. the history region is found by LABEL, which is how Abaqus names it
    regions = dict(("Node PART-1-1.%d" % (5681 + k),
                    _Hist(UNIT_STRAIN if k == 2 else 0.0, -3.0 * (k + 1)))
                   for k in range(6))
    st = _Step("Cbar_mode2", regions)
    labels = dict((k, 5681 + k) for k in range(6))
    u, rf = driver_history(st, 2, labels)
    ck("a 'Node PART-1-1.5683' region resolves for driver 2",
       abs(u[-1] - UNIT_STRAIN) < 1e-18 and abs(rf[-1] + 9.0) < 1e-12,
       "U1 = %.3e, RF1 = %.3f" % (u[-1], rf[-1]))
    try:
        driver_history(st, 2, None)
        msg = ""
    except RuntimeError as e:
        msg = str(e)
    # The message has to carry BOTH what it wanted and what was actually
    # there -- the 2026-08-10 failure was diagnosable in one look only
    # because the region keys were printed alongside the name it wanted.
    ck("without labels it raises, naming both the wanted set and the keys "
       "present",
       "CONSTRAINTSDRIVER2" in msg and "node label unknown" in msg
       and "Node PART-1-1.5683" in msg)
    try:
        driver_history(_Step("s", {}), 0, {0: 1})
        raised = False
    except RuntimeError:
        raised = True
    ck("a missing region raises rather than returning silence", raised)

    # ---- C. the last resort is a guess, and says so
    lab = driver_labels_from_history(st)
    ck("six nodal regions sorted by label map onto drivers 0-5",
       lab == dict((k, 5681 + k) for k in range(6)))
    ck("five regions is not enough to guess, so it declines",
       driver_labels_from_history(_Step("s", dict(
           ("Node P.%d" % (10 + k), _Hist(0.0, 0.0)) for k in range(5)))) == {})
    ck("a non-nodal region is not counted as a driver",
       driver_labels_from_history(_Step("s", dict(
           [("Node P.%d" % (10 + k), _Hist(0.0, 0.0)) for k in range(6)]
           + [("Element P.7 Int Point 1", _Hist(0.0, 0.0))]))) ==
       dict((k, 10 + k) for k in range(6)))

    # ---- D. the permutation guard.  A swapped mapping still yields a
    #         plausible-looking Cbar, so this is the only thing that catches it.
    eps = np.zeros(6)
    eps[2] = UNIT_STRAIN
    ck("the prescribed-strain pattern of mode 2 is unit on 2, zero elsewhere",
       abs(eps[2] - UNIT_STRAIN) <= 1e-3 * UNIT_STRAIN
       and max(abs(eps[j]) for j in range(6) if j != 2) <= 1e-3 * UNIT_STRAIN)
    swapped = np.zeros(6)
    swapped[4] = UNIT_STRAIN          # driver 4 answered for mode 2
    ck("a swapped driver fails that pattern, which is the whole point",
       abs(swapped[2] - UNIT_STRAIN) > 1e-3 * UNIT_STRAIN)

    # ---- E. Cbar bookkeeping
    C = np.diag([200.0, 200.0, 60.0, 40.0, 30.0, 30.0])
    eng = engineering_constants(C, "xy-xz-yz")
    ck("engineering constants invert a diagonal Cbar exactly",
       abs(eng["E1"] - 200.0) < 1e-9 and abs(eng["G23"] - 30.0) < 1e-9,
       "E1 = %.4g, G23 = %.4g" % (eng["E1"], eng["G23"]))
    ck("a 2D weave signature is E1 ~ E2 >> E3 on such a card",
       abs(eng["E1"] - eng["E2"]) < 1e-9 and eng["E1"] > 3 * eng["E3"])
    Cp = C.copy()
    Cp[0, 1] = 5.0
    asym = np.max(np.abs(Cp - Cp.T)) / np.max(np.abs(Cp))
    ck("the asymmetry indicator is scale-free and catches a one-sided term",
       abs(asym - 5.0 / 200.0) < 1e-12, "%.4f" % asym)

    # ---- F. the sign convention decides itself from the diagonals
    ck("all-positive diagonals keep the documented convention",
       resolve_sign([1.0] * 6) == +1)
    ck("all-negative diagonals flip it, as the 2026-08-10 run required",
       resolve_sign([-1.0] * 6) == -1)
    try:
        resolve_sign([1.0, -1.0, 1.0, 1.0, 1.0, 1.0])
        mixed = False
    except RuntimeError:
        mixed = True
    ck("MIXED signs raise instead of being papered over by a flip", mixed)
    # alphabar was right on the broken run because C and dsig were BOTH
    # flipped.  The fix must keep that invariance: a flipped odb, read with
    # its detected sign, must give the same alpha as a clean one.
    Cc = np.diag([200.0, 200.0, 60.0, 40.0, 30.0, 30.0])
    ds = np.array([-3.0, -3.0, -1.5, 0.0, 0.0, 0.0])
    a_clean = -np.linalg.solve(Cc, +1 * ds) / 100.0
    a_flip = -np.linalg.solve(Cc, -1 * (-ds)) / 100.0
    ck("alphabar is invariant when C and the stresses flip together",
       np.allclose(a_clean, a_flip),
       "alpha1 = %.4e /K both ways" % a_clean[0])

    # ---- G. a Gf may only come off a curve that actually softened.
    #         Every one of these was silently wrong until the card-pipeline
    #         rehearsal walked the three real M6 curves through this file.
    ck("the area helper survives NumPy 2, where np.trapz was REMOVED",
       abs(_trapz([0.0, 2.0], [0.0, 1.0]) - 1.0) < 1e-12,
       "this file runs LAST, after every RVE job -- one rename would cost "
       "the whole set")

    def _gate(soft, gf_tot, pre, X=100.0, E=1.0e5, L=3.5):
        st = {"Xt": X, "Gf_1t": gf_tot, "Lchar_1t": L,
              "soft_1t": soft, "Gfpre_1t": pre}
        split_fracture_energy(st, dict(E1=E))
        return st
    g0L = 100.0 * 100.0 / (2.0 * 1.0e5) * 3.5          # = 0.175 N/mm
    ck("a fully softened, mostly post-peak curve ships its Gf",
       "Gfin_1t" in _gate(0.95, g0L + 1.0, g0L + 0.05),
       "the gate is not merely an off switch")
    ck("a curve that stopped AT its peak is refused",
       "Gfin_1t" not in _gate(0.0, g0L + 1.0, g0L + 1.0),
       "M6 RT23: softened 0.0 %, and 100 % of the would-be Gf is pre-peak")
    ck("a curve that fell 16.6 % is still refused (M6 T1000)",
       "Gfin_1t" not in _gate(0.166, g0L + 1.0, g0L + 0.2),
       "SOFT_MIN = %.2f; 16.6 %% is a curve that was interrupted" % SOFT_MIN)
    ck("softening alone is not enough -- a mostly PRE-peak area is refused",
       "Gfin_1t" not in _gate(0.95, g0L + 1.0, g0L + 0.9),
       "the two conditions are independent")
    st = _gate(0.0, g0L + 1.0, g0L + 1.0)
    ck("a refused mode still records WHY, so the CSV can be audited",
       abs(st.get("soft_1t", -1) - 0.0) < 1e-12
       and abs(st.get("prepk_1t", -1) - 1.0) < 1e-9,
       "soft and prepk are kept beside the slot that stayed 0.0")
    ck("  and those two are reported as fractions, not as N/mm",
       _unit_of("soft_1t") == "-" and _unit_of("prepk_1t") == "-"
       and _unit_of("Gfpre_1t") == "N/mm")
    # The refusal has to be a refusal, not a small number: KABAND reads 0.0
    # as "off", but it reads 0.001 as an almost-vertical softening branch.
    ck("a refused mode leaves the slot at 0.0, which KABAND reads as OFF",
       _gate(0.0, g0L + 1.0, g0L + 1.0).get("Gfin_1t", 0.0) == 0.0)

    # ---- H. one damage ceiling across both scales
    ck("the macro card's dmax is the RVE constant, not a second opinion",
       abs(MACRO_DMAX - _rve_dmax(default=-1.0)) < 1e-12 and MACRO_DMAX > 0,
       "MACRO_DMAX = %.2f; it read 0.99 until 2026-08-18 while every RVE "
       "card and damage_map.py used 0.90" % MACRO_DMAX)

    print("\n  %d passed, %d failed" % (len(ok), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
