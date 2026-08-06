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


def driver_history(step, k):
    """(U, RF) time series of ConstraintsDriver`k` dof 1 in `step`."""
    want = "CONSTRAINTSDRIVER%d" % k
    hr = None
    for key, hp in step.historyRegions.items():
        if want in key.upper().replace(" ", ""):
            hr = hp
            break
    if hr is None:
        # fall back on the node label behind the set
        raise RuntimeError("history region for %s not found in step %s; "
                           "keys=%s" % (want, step.name,
                                        list(step.historyRegions.keys())))
    uk = sorted(k2 for k2 in hr.historyOutputs.keys()
                if k2.upper().startswith("U"))[0]
    rk = sorted(k2 for k2 in hr.historyOutputs.keys()
                if k2.upper().startswith("RF"))[0]
    u = [v for _, v in hr.historyOutputs[uk].data]
    r = [v for _, v in hr.historyOutputs[rk].data]
    return np.array(u), np.array(r)


def macro_state(step, V):
    """Final macro strain and stress vectors of `step`."""
    eps = np.zeros(6)
    sig = np.zeros(6)
    for k in range(6):
        u, rf = driver_history(step, k)
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

    C = np.zeros((6, 6))
    seen = set()
    for name, step in odb.steps.items():
        up = name.upper()
        if up.startswith("CBAR_MODE"):
            k = int(up.replace("CBAR_MODE", ""))
            _, sig = macro_state(step, V)
            C[:, k] = sig / UNIT_STRAIN
            seen.add(k)
    odb.close()
    if len(seen) != 6:
        raise RuntimeError("%s: expected 6 Cbar_mode steps, found %s"
                           % (path, sorted(seen)))

    # The two halves differ only by discretisation error, so the asymmetry is
    # a useful mesh-quality indicator -- report it, then symmetrise.
    asym = np.max(np.abs(C - C.T)) / max(1e-30, np.max(np.abs(C)))
    return 0.5 * (C + C.T), (Lx, Ly, Lz), asym


def cte_from(path, C):
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
    base = None
    hot = None
    dT = None
    for name, step in odb.steps.items():
        up = name.upper()
        if up.startswith("ALPHABAR_BASE"):
            _, base = macro_state(step, V)
        elif up.startswith("ALPHABAR_DT"):
            _, hot = macro_state(step, V)
            dT = float(name.upper().replace("ALPHABAR_DT", ""))
    odb.close()
    if base is None or hot is None or not dT:
        raise RuntimeError("%s: need steps alphabar_base and alphabar_dT<x>"
                           % path)
    return -np.linalg.solve(C, hot - base) / dT


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
def strength_curve(path, mode):
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
    u, rf = driver_history(step, comp)
    odb.close()

    eps = sign * np.asarray(u)
    sig = sign * (-np.asarray(rf) / V)
    ipk = int(np.argmax(sig))
    peak = float(sig[ipk])

    # Crack-band fracture energy: area under the whole curve x the RVE length
    # along the loading direction.  For shear modes the length is ambiguous;
    # the in-plane size is used and the choice is recorded in the CSV.
    Lchar = (Lx, Ly, Lz, Lx, Lx, Ly)[comp]
    area = float(np.trapz(sig, eps))
    Gf = area * Lchar
    return dict(peak=peak, eps_peak=float(eps[ipk]), Gf=Gf,
                Lchar=Lchar, npts=len(eps))


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


def _unit_of(key):
    """Unit for one strength-block CSV row."""
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
    the fixed exponent.
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
    slots[21] = slots[22] = 0.99                          # dmax
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
        C, box, asym = elastic_from(path)
        eng = engineering_constants(C, shear_order)
        cpath = "%s_CTE_T%g.odb" % (prefix, T)
        if os.path.exists(cpath):
            alpha = cte_from(cpath, C)
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
            r = strength_curve(sp, mode)
            strength[slot] = abs(r["peak"])
            if mode in ("1t", "1c", "2t", "2c"):
                strength["Gf_" + mode] = r["Gf"]
                strength["Lchar_" + mode] = r["Lchar"]
            print("  %-4s peak = %8.2f MPa at eps = %.4f %%   Gf = %.4g N/mm"
                  % (mode, r["peak"], 100.0 * r["eps_peak"], r["Gf"]))
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
