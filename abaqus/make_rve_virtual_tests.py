#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_rve_virtual_tests.py
=========================
Turn the C/SiC RVE into a VIRTUAL TESTING MACHINE: generate every Abaqus deck
needed to extract the homogenised macro-scale properties that the macro CDM
(KMACRO31 in src/UMAT_CSIC_THERMSHOCK_V3_0.for) needs as its card.

Why this exists
---------------
"Extract effective properties from the RVE and put them into the macro model"
does NOT work for a damage problem: homogenised elastic constants alone carry
no damage, so a macro model built from them can never lose stiffness under
repeated thermal shock.  What the macro CDM actually needs from the RVE is a
FULL CARD:

    Cbar(T)                 -> E1 E2 E3 nu12 nu13 nu23 G12 G13 G23
    alphabar(T)             -> *Expansion, type=ORTHO on the macro material
    Xt Xc Yt Yc S12 S13 S23 -> from virtual tests taken to failure
    A / Gf                  -> from the post-peak softening branch
    kbar(T), rho, cp        -> for the transient heat-transfer step of the
                               thermal-shock analysis

This script writes the decks for all of it.  postprocess/homogenize.py reads
the resulting ODBs and assembles the macro card.

Decks written
-------------
  <prefix>_ELAS_T<T>.inp    6 unit macro-strain modes, damage DISABLED and
                            NO expansion, isothermal at T  -> Cbar(T)
  <prefix>_CTE_T<T>.inp     two clamped steps differing by dT, expansion ON;
                            the STRESS DIFFERENCE gives alphabar(T)
  <prefix>_STR_<mode>_T<T>_TRS<on|off>.inp
                            manufacturing cooling (1050 -> T) with damage ON,
                            then monotonic loading of one macro mode to
                            failure -> homogenised strength + softening
                            modes: 1t 1c 2t 2c 3t s12 s13 s23
  <prefix>_COND.inp         steady-state heat transfer, 3 directions
                            -> kbar  (needed for the quench analysis)

Periodic-BC convention (TexGen / Xia unified PBC, same as the existing decks)
    U (ConstraintsDriverK, dof 1) = macro strain component K
    RF(ConstraintsDriverK, dof 1) = -sigma_K * V_RVE
Component order is 0,1,2 = 11,22,33 and 3,4,5 = the three shears.  The SHEAR
ORDER differs between TexGen versions, so it is configurable (--shear-order)
and postprocess/homogenize.py prints the raw Cbar so it can be confirmed on
the first run.  Do not assume it -- check it once, then fix the flag.

Usage
  python3 make_rve_virtual_tests.py mesh.inp
  python3 make_rve_virtual_tests.py mesh.inp --temps 23 500 1000 --trs on
  python3 make_rve_virtual_tests.py mesh.inp --only ELAS
"""
from __future__ import print_function

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble_inp as ai   # mesh filtering + material cards are reused verbatim

# --------------------------------------------------------------------------
# Constituent THERMAL properties (for the conductivity/quench decks).
#
# NO LONGER PLACEHOLDERS.  The yarn conductivities are COMPUTED from sourced
# constituent values by data/properties/conductivity_bounds.py rather than
# typed in here, per the project rule that property numbers live in code, not
# in hand-copied tables.
#
#   fibre  k11 = 8, k22 = 1 W/(m.K)   refs/[22] Table 1 and refs/[17] Table 1
#                                     (two independent papers, same numbers)
#   SiC    k   = 25 W/(m.K)           refs/[17] Table 3
#   yarn   -> rule of mixtures along the fibre, Rayleigh across it,
#            at the yarn-level Vf of 0.79194
#
# WHY NOT SNEAD.  data/properties/matrix_SiC_vsT.csv carries the Snead Eq.12
# single-crystal conductivity (293 W/(m.K) at RT).  conductivity_bounds.py
# proves that value cannot reproduce the measured composite conductivity of
# 6.29 W/(m.K) (refs/[12]) even with a zero-conductivity fibre.  It is the
# documented upper sensitivity endpoint, not the input.
#
# STILL MISSING: POROSITY.  Our mesh is 100 % dense, so this deck will
# OVERPREDICT kbar and make the quench gradient too shallow -- the
# non-conservative direction.  Run --porosity to bracket it.
#
# Units: conductivity mW/(mm.K), density tonne/mm^3, specific heat mJ/(tonne.K)
# (the Abaqus mm-N-tonne-s-MPa system the rest of the model already uses).
# mW/(mm.K) is NUMERICALLY EQUAL to W/(m.K); the derivation, and the 1000x
# error that reading it as W/(mm.K) causes, is in eval_correlations.py under
# "THE DECK'S THERMAL UNIT".  Every deck carries the stamp below so a reader
# never has to remember which convention produced the odb in front of it.
# --------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "data", "properties"))
import conductivity_bounds as cb          # noqa: E402

#: W/(m.K) -> mW/(mm.K), the conductivity unit of the tonne-mm-s-mJ system.
#: The factor is ONE: 1 mW/(mm.K) = 1e-3 W / (1e-3 m . K) = 1 W/(m.K).  It was
#: 1.0e-3 until 2026-08-11, which is the "W/(mm.K)" convention -- self-
#: consistent with nothing, because cp on the next two lines is mJ/(tonne.K).
#: The mismatch is exactly 1000 and it lands on the thermal diffusivity.
#: Steady-state conduction (every job run so far) divides it out, so the kbar
#: results are untouched; a transient would have cooled 1000x too slowly.
#: eval_correlations.py derives the unit and checks it on the card triple.
_WMK = 1.0

#: Stamped into every deck that carries a thermal card, so a post-processor
#: reads the convention off the deck instead of remembering it.  A deck
#: without this line predates 2026-08-11 and is in the old W/(mm.K) set.
UNIT_STAMP = "** UNITSTAMP: k_card_per_WmK = 1.0  (mW/(mm.K), tonne-mm-s-mJ)"


def thermal_properties(porosity=0.0, k_matrix=25.0, k1_f=8.0, k2_f=1.0):
    """Constituent thermal card values, derived not typed.

    SIMPLIFICATION TO DECLARE: `porosity` is applied to the SAME SiC for both
    the inter-yarn matrix and the matrix inside a yarn.  In a real CVI or PIP
    composite the intra-yarn matrix is usually denser than the inter-yarn
    pockets, because infiltration reaches the tow interior first and the large
    inter-tow voids close last.  Treating them alike therefore UNDERSTATES the
    yarn conductivity and OVERSTATES the matrix-pocket conductivity; the two
    errors partly cancel in kbar3.  Splitting them needs a porosity
    measurement per region, which we do not have.
    """
    km = cb.porous_matrix(k_matrix, porosity) if porosity > 0.0 else k_matrix
    k_long, k_trans = cb.yarn_conductivity(k1_f, k2_f, km)
    return {
        "matrix": dict(k=km * _WMK, rho=3.21e-9, cp=6.7e8),
        "yarn_axial": dict(k=k_long * _WMK, rho=1.76e-9, cp=7.1e8),
        "yarn_trans": k_trans * _WMK,
        "_meta": dict(porosity=porosity, k_matrix_dense=k_matrix,
                      k_matrix_eff=km, k1_f=k1_f, k2_f=k2_f,
                      k_long=k_long, k_trans=k_trans),
    }

SHEAR_ORDERS = {
    "xy-xz-yz": (3, 4, 5),   # driver3=g12, driver4=g13, driver5=g23
    "xy-yz-xz": (3, 5, 4),   # driver3=g12, driver4=g23, driver5=g13
}

#: macro strain component index -> (label, unit strain sign)
MODES = {
    "1t": (0, +1.0), "1c": (0, -1.0),
    "2t": (1, +1.0), "2c": (1, -1.0),
    "3t": (2, +1.0),
    "s12": (3, +1.0), "s13": (4, +1.0), "s23": (5, +1.0),
}

#: how far each mode is driven in the strength tests (macro strain)
STRENGTH_LIMIT = {
    "1t": 0.010, "1c": 0.010, "2t": 0.010, "2c": 0.010,
    "3t": 0.010, "s12": 0.020, "s13": 0.020, "s23": 0.020,
}

STRESS_FREE_T = 1050.0
UNIT_STRAIN = 1.0e-6          # linear-range probe for Cbar
THERMAL_PROBE_DT = 100.0      # magnitude of the DT probe for alphabar


# ==========================================================================
# card helpers -- the V1_0/V2_0 cards with the damage switch flipped
# ==========================================================================
def _card_lines(card_text):
    """Split a '*User Material, constants=N' block into (header, [values])."""
    lines = card_text.strip().splitlines()
    vals = []
    for ln in lines[1:]:
        vals.extend([v.strip() for v in ln.split(",") if v.strip() != ""])
    return lines[0], vals


def _reflow(header, vals, per_line=8):
    out = [header]
    for i in range(0, len(vals), per_line):
        out.append(", ".join(vals[i:i + per_line]))
    return "\n".join(out)


def usermat_with_damage(card_text, slot, enable):
    """Return the card with the `enable` switch at 1-based `slot` set."""
    header, vals = _card_lines(card_text)
    vals = list(vals)
    vals[slot - 1] = "1.0" if enable else "0.0"
    return _reflow(header, vals)


#: 1-based matrix card slot holding E, cross-read from retune_deck.py so the
#: two generators cannot drift apart.  ELAS and CTE must stand on the SAME
#: matrix card the calibration lineage uses -- a Cbar measured on the dense
#: 350 GPa card does not belong to the RVE that M6 calibrates on the
#: porosity-knocked 213110 one, and nothing downstream would notice.
def _matrix_e_slot():
    import re as _re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "retune_deck.py")).read()
    m = _re.search(r"MATRIX_SLOTS = dict\(e=(\d+)", src)
    if not m:
        raise SystemExit("retune_deck.py no longer declares MATRIX_SLOTS[e]")
    return int(m.group(1))


def with_matrix_e(card_text, e):
    """Return the matrix card with Young's modulus replaced."""
    header, vals = _card_lines(card_text)
    vals = list(vals)
    vals[_matrix_e_slot() - 1] = "%.10g" % e
    return _reflow(header, vals)


def material_section(model, matrix_es, yarn_es, orient, damage=True,
                     expansion=True, matrix_e=None):
    """Material block; damage=False gives the purely elastic probe material."""
    mat = ai.MATRIX_USERMAT[model]
    yrn = ai.YARN_USERMAT[model]
    if matrix_e is not None:
        mat = with_matrix_e(mat, matrix_e)
    if not damage:
        mat = usermat_with_damage(mat, 14, False)    # matrix ENABLE = slot 14
        yrn = usermat_with_damage(yrn, 28, False)    # yarn   ENABLE = slot 28
    L = ["*Material, Name=SIC_MATRIX_DAMAGE", ai.MATRIX_DEPVAR, mat]
    if expansion:
        L.append(ai.MATRIX_EXPANSION)
    L += ["*Material, Name=CSIC_YARN_DAMAGE", ai.YARN_DEPVAR, yrn]
    if expansion:
        L.append(ai.YARN_EXPANSION)
    L.append("*Solid Section, ElSet=%s, Material=SIC_MATRIX_DAMAGE"
             % (matrix_es or "Matrix"))
    L.append("1.0,")
    for es in yarn_es:
        L.append("*Solid Section, ElSet=%s, Material=CSIC_YARN_DAMAGE, "
                 "Orientation=%s" % (es, orient))
        L.append("1.0,")
    return "\n".join(L)


def driver_boundary(values):
    """*Boundary block prescribing ALL SIX macro strain components.

    Prescribing every component (not just the driven one) is what makes each
    step a pure mode: the RVE cannot relax into the other components, so the
    reaction forces give one full column of Cbar.
    """
    L = ["*Boundary, type=displacement"]
    for k, v in enumerate(values):
        L.append("ConstraintsDriver%d, 1, 1, %.10g" % (k, v))
    return "\n".join(L)


def _output_blocks(history_only=False):
    hist = "\n".join("*Node Output, nset=ConstraintsDriver%d\nU, RF" % i
                     for i in range(6))
    field = ("*Output, field, number interval=%d, time marks=NO\n"
             "*Element Output, directions=YES\n"
             "S, E, EE, THE, IVOL, SDV\n"
             "*Node Output\nU, RF\n" % (2 if history_only else 51))
    return field + "*Output, history, frequency=1\n" + hist


CTRL = """*Controls, parameters=time incrementation
 8, 10, , 30, , , , 20, , ,
*Controls, parameters=field, field=displacement
 , 0.08
*Controls, parameters=line search
5
"""


# ==========================================================================
# deck A: Cbar(T) and alphabar(T)
# ==========================================================================
def steps_elastic(T):
    """Six unit macro-strain modes, isothermal at T.

    The deck that carries these steps is built WITHOUT *Expansion.  That is
    essential: with *Expansion, zero=1050 active, a model whose initial
    temperature is T != 1050 already carries the manufacturing thermal strain
    at increment 0, and the driver reactions would be
    sigma_thermal + Cbar : eps_unit.  Since eps_unit is 1e-6, the thermal term
    would swamp the elastic one and Cbar would come out as noise.  No
    expansion -> the UMAT sees pure mechanical strain and each column of Cbar
    is exact.  alphabar is measured separately (steps_cte).
    """
    S = []
    for k in range(6):
        v = [0.0] * 6
        v[k] = UNIT_STRAIN
        S.append("*Step, Name=Cbar_mode%d, nlgeom=NO, inc=100" % k)
        S.append("Unit macro strain in component %d at %g degC "
                 "(damage OFF, no expansion -> linear probe)" % (k, T))
        S.append("*Static")
        S.append("1.0, 1.0, 1.0E-12, 1.0")
        S.append(CTRL + driver_boundary(v))
        S.append("*Temperature\nAllNodes, %.6g" % T)
        S.append(_output_blocks(history_only=True))
        S.append("*End Step")
    return "\n".join(S)


def probe_dt(T):
    """Signed temperature probe that stays inside [0, stress-free]."""
    dT = THERMAL_PROBE_DT
    if T + dT > STRESS_FREE_T:
        dT = -abs(dT)
    if T + dT < 0.0:
        dT = abs(dT)
    return dT


def steps_cte(T):
    """Two clamped steps whose STRESS DIFFERENCE gives alphabar.

    Step 1 holds the macro strain at zero at temperature T and establishes the
    baseline stress -- which is NOT zero, because *Expansion, zero=1050 means
    the cell is already thermally loaded at T.  Step 2 changes the temperature
    by dT with the macro strain still clamped.  Then

        d(sigma_bar) = -Cbar : alphabar * dT   ->   alphabar

    Taking the difference is what removes the manufacturing thermal stress
    from the measurement.
    """
    dT = probe_dt(T)
    S = []
    S.append("*Step, Name=alphabar_base, nlgeom=NO, inc=1000")
    S.append("Macro strain clamped at zero, hold at %g degC (baseline)" % T)
    S.append("*Static")
    S.append("0.05, 1.0, 1.0E-12, 0.5")
    S.append(CTRL + driver_boundary([0.0] * 6))
    S.append("*Temperature\nAllNodes, %.6g" % T)
    S.append(_output_blocks(history_only=True))
    S.append("*End Step")
    S.append("*Step, Name=alphabar_dT%+g, nlgeom=NO, inc=1000" % dT)
    S.append("Macro strain still clamped, dT = %+g K" % dT)
    S.append("*Static")
    S.append("0.05, 1.0, 1.0E-12, 0.5")
    S.append(CTRL + driver_boundary([0.0] * 6))
    S.append("*Temperature\nAllNodes, %.6g" % (T + dT))
    S.append(_output_blocks(history_only=True))
    S.append("*End Step")
    return "\n".join(S)


# ==========================================================================
# deck B: homogenised strengths
# ==========================================================================
def steps_strength(mode, T, trs):
    """Manufacturing cooling (optional) then one macro mode to failure."""
    idx, sign = MODES[mode]
    lim = sign * STRENGTH_LIMIT[mode]
    S = []
    if trs:
        S.append("*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=10000")
        S.append("Cool %g -> %g degC: thermal residual stress + initial damage"
                 % (STRESS_FREE_T, T))
        S.append("*Static")
        S.append("0.001, 1.0, 1.0E-12, 0.0025")
        S.append(CTRL + driver_boundary([0.0] * 6))
        S.append("*Temperature\nAllNodes, %.6g" % T)
        S.append(_output_blocks())
        S.append("*End Step")
    v = [0.0] * 6
    v[idx] = lim
    S.append("*Step, Name=Strength_%s, nlgeom=NO, inc=100000" % mode)
    S.append("Monotonic macro mode %s to failure at %g degC" % (mode, T))
    S.append("*Static")
    S.append("0.0005, 1.0, 1.0E-12, 0.0025")
    S.append(CTRL + driver_boundary(v))
    S.append("*Temperature\nAllNodes, %.6g" % T)
    S.append(_output_blocks())
    S.append("*End Step")
    return "\n".join(S)


# ==========================================================================
# deck C: homogenised conductivity
# ==========================================================================
def parse_nodes(kept):
    """Node label -> (x, y, z) from the kept mesh blocks."""
    coords = {}
    for kw, data in kept:
        if ai.kwname(kw) != "node":
            continue
        for d in data:
            d = d.strip()
            if not d or d.startswith("**"):
                continue
            parts = [p.strip() for p in d.split(",")]
            if len(parts) < 4:
                continue
            try:
                coords[int(parts[0])] = (float(parts[1]), float(parts[2]),
                                         float(parts[3]))
            except ValueError:
                continue
    return coords


def face_nsets(coords, tol_frac=1.0e-6):
    """Build the six bounding-box face NSets from the node coordinates.

    Done here rather than relying on the TexGen export, which does not always
    write face sets.  Returns (nset_text, box) with box = (lo, hi) per axis.
    """
    if not coords:
        return None, None
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    zs = [c[2] for c in coords.values()]
    box = [(min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))]
    span = max(hi - lo for lo, hi in box)
    tol = max(span * tol_frac, 1.0e-9)

    names = [("XLO", "XHI"), ("YLO", "YHI"), ("ZLO", "ZHI")]
    out = []
    for ax in range(3):
        lo, hi = box[ax]
        for bound, nm in ((lo, names[ax][0]), (hi, names[ax][1])):
            lbl = sorted(n for n, c in coords.items()
                         if abs(c[ax] - bound) <= tol)
            if not lbl:
                return None, box
            out.append("*NSet, NSet=FACE_%s" % nm)
            for i in range(0, len(lbl), 16):
                out.append(", ".join(str(v) for v in lbl[i:i + 16]))
    return "\n".join(out), box


def thermal_materials(matrix_es, yarn_es, orient, tp=None):
    tp = tp or thermal_properties()
    m = tp["_meta"]
    L = []
    L.append(UNIT_STAMP)
    L.append("** Thermal properties DERIVED by data/properties/"
             "conductivity_bounds.py")
    L.append("**   fibre  k11 = %g, k22 = %g W/(m.K)   refs/[22], refs/[17]"
             % (m["k1_f"], m["k2_f"]))
    L.append("**   SiC    k = %g W/(m.K) dense, %.3f effective at %.1f %% "
             "porosity" % (m["k_matrix_dense"], m["k_matrix_eff"],
                           100.0 * m["porosity"]))
    L.append("**   yarn   k_long = %.3f, k_trans = %.3f W/(m.K) at Vf = %.5f"
             % (m["k_long"], m["k_trans"], cb.VF_YARN))
    if m["porosity"] <= 0.0:
        L.append("** !! ZERO POROSITY -- this deck will OVERPREDICT kbar and "
                 "make the")
        L.append("**    quench gradient too shallow.  Use --porosity to "
                 "bracket it.")
    L.append("*Material, Name=SIC_MATRIX_THERMAL")
    L.append("*Conductivity\n%.6g," % tp["matrix"]["k"])
    L.append("*Density\n%.6g," % tp["matrix"]["rho"])
    L.append("*Specific Heat\n%.6g," % tp["matrix"]["cp"])
    L.append("*Material, Name=CSIC_YARN_THERMAL")
    L.append("*Conductivity, type=ORTHO\n%.6g, %.6g, %.6g"
             % (tp["yarn_axial"]["k"], tp["yarn_trans"], tp["yarn_trans"]))
    L.append("*Density\n%.6g," % tp["yarn_axial"]["rho"])
    L.append("*Specific Heat\n%.6g," % tp["yarn_axial"]["cp"])
    L.append("*Solid Section, ElSet=%s, Material=SIC_MATRIX_THERMAL"
             % (matrix_es or "Matrix"))
    L.append("1.0,")
    for es in yarn_es:
        L.append("*Solid Section, ElSet=%s, Material=CSIC_YARN_THERMAL, "
                 "Orientation=%s" % (es, orient))
        L.append("1.0,")
    return "\n".join(L)


def steps_conductivity(box, dT=1.0):
    """Three steady-state directions: hot/cold on opposite faces, rest adiabatic.

    kbar_i = Q_i * L_i / (A_i * dT), with Q_i the total reaction flux on the hot
    face.  The unloaded faces are left free, which is the adiabatic default --
    so this is the 'series' (Reuss-like) measurement in each direction, the
    standard 1-D conductivity homogenisation.
    """
    faces = (("XLO", "XHI"), ("YLO", "YHI"), ("ZLO", "ZHI"))
    S = []
    for ax, (flo, fhi) in enumerate(faces):
        S.append("*Step, Name=kbar_dir%d, inc=100" % (ax + 1))
        S.append("Steady conduction along axis %d" % (ax + 1))
        S.append("*Heat Transfer, steady state")
        S.append("1.0, 1.0")
        S.append("*Boundary")
        S.append("FACE_%s, 11, 11, 0.0" % flo)
        S.append("FACE_%s, 11, 11, %.6g" % (fhi, dT))
        S.append("*Output, field")
        S.append("*Node Output\nNT, RFL")
        S.append("*Output, history, frequency=1")
        S.append("*Node Output, nset=FACE_%s\nRFL" % fhi)
        S.append("*End Step")
    return "\n".join(S)


def to_heat_transfer_elements(blocks):
    """Swap C3D* stress elements for their DC3D* heat-transfer counterparts and
    drop the displacement PBC equations (meaningless in a thermal analysis)."""
    out = []
    for kw, data in blocks:
        name = ai.kwname(kw)
        if name == "equation":
            continue
        if name == "element":
            t = ai.kw_option(kw, "type")
            if t and t.upper().startswith("C3D"):
                kw = kw.replace(t, "DC3D" + t.upper()[3:])
        out.append((kw, data))
    return out


# ==========================================================================
def write(path, parts):
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print("  wrote %s" % path)


def main():
    ap = argparse.ArgumentParser(
        description="Generate the RVE virtual-test decks for macro "
                    "homogenisation.")
    ap.add_argument("mesh", help="TexGen-exported Abaqus .inp of the RVE")
    ap.add_argument("--model", choices=["v1", "v2"], default="v2")
    ap.add_argument("--prefix", default="RVE")
    ap.add_argument("--temps", type=float, nargs="+", default=[23.0],
                    help="temperatures for Cbar/alphabar and the strength "
                         "tests (default: 23)")
    ap.add_argument("--trs", choices=["on", "off"], default="on",
                    help="include the 1050 degC manufacturing cooling before "
                         "the strength tests (default: on)")
    ap.add_argument("--matrix-e", type=float, default=None,
                    help="matrix Young's modulus in MPa, replacing the card's "
                         "own.  Use 213110 to stand on the porosity-knocked "
                         "card the M6 calibration lineage uses -- a Cbar "
                         "measured on the dense 350 GPa card belongs to a "
                         "different RVE than the one being calibrated, and "
                         "nothing downstream would catch the mismatch.")
    ap.add_argument("--porosity", type=float, default=0.0,
                    help="SiC matrix porosity for the COND deck (0-0.5). "
                         "The mesh is 100 %% dense, so leaving this at 0 "
                         "OVERPREDICTS kbar; refs/[22] measures 0.24.")
    ap.add_argument("--only", choices=["ELAS", "CTE", "STR", "COND"],
                    default=None)
    ap.add_argument("--modes", nargs="+", default=sorted(MODES),
                    help="which strength modes to write")
    ap.add_argument("--shear-order", choices=sorted(SHEAR_ORDERS),
                    default="xy-xz-yz",
                    help="driver 3/4/5 -> shear component mapping; CONFIRM "
                         "this on the first run (see module docstring)")
    args = ap.parse_args()

    with open(args.mesh) as f:
        text = f.read()
    kept, matrix_es, yarn_es, orient, max_node, seen = ai.filter_mesh(text)
    if not yarn_es:
        sys.exit("ERROR: no 'Yarn*' ElSet found -- is this a TexGen export?")
    orient = orient or "TexGenOrientations"
    mesh_txt = ai.emit_blocks(kept)
    allnodes = ai.allnodes_block(max_node, seen)
    print("detected: matrix ElSet=%s, %d yarn ElSets, orientation=%s, "
          "max node=%d" % (matrix_es or "Matrix", len(yarn_es), orient,
                           max_node))
    print("shear order: %s -> drivers 3,4,5 = %s"
          % (args.shear_order, SHEAR_ORDERS[args.shear_order]))

    def base(headline, matsec, init_T=None):
        parts = ["*Heading", " " + headline, mesh_txt]
        if allnodes:
            parts.append(allnodes)
        parts.append(matsec)
        if init_T is not None:
            parts.append("*Initial Conditions, type=TEMPERATURE\nAllNodes, "
                         "%.6g" % init_T)
        return parts

    want = lambda tag: args.only is None or args.only == tag

    # ---- deck A1: Cbar (no expansion -- see steps_elastic) ---------------
    if want("ELAS"):
        for T in args.temps:
            matsec = material_section(args.model, matrix_es, yarn_es, orient,
                                      damage=False, expansion=False,
                                      matrix_e=args.matrix_e)
            parts = base("RVE virtual test: Cbar at %g degC "
                         "(damage OFF, no expansion)" % T, matsec, init_T=T)
            parts.append(steps_elastic(T))
            write("%s_ELAS_T%g.inp" % (args.prefix, T), parts)

    # ---- deck A2: alphabar (expansion ON, differenced) -------------------
    if want("ELAS") or want("CTE"):
        for T in args.temps:
            matsec = material_section(args.model, matrix_es, yarn_es, orient,
                                      damage=False, expansion=True,
                                      matrix_e=args.matrix_e)
            parts = base("RVE virtual test: alphabar at %g degC "
                         "(damage OFF, dT = %+g K)" % (T, probe_dt(T)),
                         matsec, init_T=T)
            parts.append(steps_cte(T))
            write("%s_CTE_T%g.inp" % (args.prefix, T), parts)

    # ---- deck B ---------------------------------------------------------
    if want("STR"):
        trs = args.trs == "on"
        for T in args.temps:
            for mode in args.modes:
                if mode not in MODES:
                    sys.exit("unknown mode %s (have %s)"
                             % (mode, sorted(MODES)))
                # TRS off means no manufacturing thermal strain at all, so the
                # expansion block is dropped rather than merely skipping the
                # cooling step -- otherwise the cell would still start loaded.
                matsec = material_section(args.model, matrix_es, yarn_es,
                                          orient, damage=True,
                                          expansion=trs,
                                          matrix_e=args.matrix_e)
                parts = base("RVE virtual test: homogenised strength, mode %s "
                             "at %g degC, TRS %s"
                             % (mode, T, args.trs), matsec,
                             init_T=STRESS_FREE_T if trs else T)
                parts.append(steps_strength(mode, T, trs))
                write("%s_STR_%s_T%g_TRS%s.inp"
                      % (args.prefix, mode, T, args.trs), parts)

    # ---- deck C ---------------------------------------------------------
    if want("COND"):
        coords = parse_nodes(kept)
        nsets, box = face_nsets(coords)
        if nsets is None:
            print("  SKIPPED %s_COND.inp: could not build face NSets from the "
                  "node coordinates (empty face). Check the mesh export."
                  % args.prefix)
        else:
            print("  RVE bounding box: " + ", ".join(
                "%s=[%.6g, %.6g]" % (a, lo, hi)
                for a, (lo, hi) in zip("xyz", box)))
            th_blocks = to_heat_transfer_elements(kept)
            tprops = thermal_properties(porosity=args.porosity)
            tm = tprops["_meta"]
            print("  thermal: SiC %.2f W/(m.K) (%.0f %% porous), yarn "
                  "%.2f / %.2f W/(m.K)"
                  % (tm["k_matrix_eff"], 100.0 * tm["porosity"],
                     tm["k_long"], tm["k_trans"]))
            parts = ["*Heading",
                     " RVE virtual test: homogenised conductivity kbar "
                     "(porosity %.1f %%)" % (100.0 * args.porosity),
                     ai.emit_blocks(th_blocks)]
            if allnodes:
                parts.append(allnodes)
            parts.append(nsets)
            parts.append(thermal_materials(matrix_es, yarn_es, orient,
                                          tprops))
            parts.append(steps_conductivity(box))
            write("%s_COND.inp" % args.prefix, parts)

    print("\nNext: run these with the V3_0 UMAT, then\n"
          "  abaqus python ../postprocess/homogenize.py <prefix>\n"
          "to assemble the macro card.  Keep the TexGen .ori file beside the "
          "decks and run with 'abaqus ... double'.")


if __name__ == "__main__":
    main()
