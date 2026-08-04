#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_pbc_check.py
=================
Build the two Abaqus decks that *prove* the periodic boundary conditions of a
TexGen RVE actually work, before any damage physics is switched on.

    <prefix>_PATCH.inp     patch test    -- one isotropic material everywhere
    <prefix>_ELASTIC.inp   homogenisation -- the real two-phase RVE, damage off

Why a patch test first
----------------------
Give an RVE a single homogeneous material and impose a macroscopic strain through
correct PBC, and the exact answer is known in closed form: the strain field is
uniform, equal to the macro strain, everywhere; the periodic fluctuation is
identically zero; and the homogenised stiffness is the material's own stiffness.
C3D4 tets represent constant strain exactly, so a correct deck reproduces this to
machine precision.  Any PBC defect -- an unpaired face node, a stale lattice
length, a missing shear term -- shows up immediately as a non-uniform stress
field.  There is no calibration and no judgement call involved: it either is
uniform or the constraints are wrong.

Only once that passes does the two-phase ELASTIC deck mean anything.  It runs the
same six macro-strain load cases on the real yarn/matrix RVE plus a unit thermal
load case, giving the full 6x6 homogenised stiffness and the homogenised CTE --
the numbers to compare against EasyPBC, and the numbers a thermal-shock coupon
model needs.

Both decks are plain *Elastic (no UMAT), so they run in minutes and need no
Fortran compiler.  PATCH additionally needs no .ori file.

Load cases (steps) in both decks
--------------------------------
    LC1_exx  LC2_eyy  LC3_ezz  LC4_gxy  LC5_gxz  LC6_gyz     all six drivers
                                                             prescribed, five at 0
    LC7_dT   all drivers held at 0, uniform +1 degC -> homogenised CTE

Usage
-----
    python3 abaqus/make_pbc_check.py abaqus/ZHANG2022_RT23_V1_0.inp
    python3 abaqus/make_pbc_check.py mesh.inp --prefix PBC_coarse --temp 23 --eps 1e-3
    python3 abaqus/make_pbc_check.py mesh.inp --only patch

Then:
    abaqus job=PBC_PATCH   input=PBC_PATCH.inp   double interactive
    abaqus job=PBC_ELASTIC input=PBC_ELASTIC.inp double interactive
    abaqus python postprocess/extract_stiffness.py PBC_PATCH.odb   --patch
    abaqus python postprocess/extract_stiffness.py PBC_ELASTIC.odb
"""
from __future__ import print_function

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_inp import (split_blocks, kwname, kw_option, filter_mesh,   # noqa: E402
                          emit_blocks, allnodes_block)

# Six load cases: (step name, driver index, comment).  Driver order follows
# TexGen: 0..5 = e_x, e_y, e_z, e_xy, e_xz, e_yz.
LOAD_CASES = [("LC1_exx", 0, "macroscopic normal strain eps_xx"),
              ("LC2_eyy", 1, "macroscopic normal strain eps_yy"),
              ("LC3_ezz", 2, "macroscopic normal strain eps_zz"),
              ("LC4_gxy", 3, "macroscopic engineering shear gamma_xy"),
              ("LC5_gxz", 4, "macroscopic engineering shear gamma_xz"),
              ("LC6_gyz", 5, "macroscopic engineering shear gamma_yz")]


# --------------------------------------------------------------------------- #
#  pull the elastic constants out of the source deck's UMAT cards
# --------------------------------------------------------------------------- #

def _numbers(data):
    out = []
    for line in data:
        s = line.strip()
        if not s or s.startswith("**"):
            continue
        for tok in s.split(","):
            tok = tok.strip()
            if tok:
                out.append(float(tok))
    return out


def read_materials(text):
    """Return {'MATRIX': {...}, 'YARN': {...}} with elastic constants and CTEs
    read from the ZHANG2022 *User Material cards.

    Card layout (see the deck comments):
      matrix PROPS  2 = E, 3 = nu
      yarn   PROPS  2..10 = E1 E2 E3 nu12 nu13 nu23 G12 G13 G23
    """
    mats, cur = {}, None
    for kw, data in split_blocks(text):
        name = kwname(kw)
        if name == "material":
            cur = (kw_option(kw, "Name") or "").upper()
            mats[cur] = {"name": kw_option(kw, "Name")}
        elif cur is None:
            continue
        elif name == "user material":
            mats[cur]["props"] = _numbers(data)
        elif name == "elastic":
            mats[cur]["elastic"] = _numbers(data)
            mats[cur]["elastic_type"] = (kw_option(kw, "type") or "ISO").upper()
        elif name == "expansion":
            mats[cur]["alpha"] = _numbers(data)
            mats[cur]["alpha_type"] = (kw_option(kw, "type") or "ISO").upper()
            z = kw_option(kw, "zero")
            mats[cur]["zero"] = float(z) if z else None

    def pick(token):
        hits = [v for k, v in mats.items() if token in k]
        if not hits:
            sys.exit("ERROR: no *Material whose name contains '%s' in the source "
                     "deck" % token)
        return hits[0]

    matrix, yarn = pick("MATRIX"), pick("YARN")

    if "elastic" in matrix:
        E, nu = matrix["elastic"][0], matrix["elastic"][1]
    else:
        p = matrix.get("props", [])
        if len(p) < 3:
            sys.exit("ERROR: matrix card has %d constants, need at least 3 "
                     "(phase, E, nu)" % len(p))
        E, nu = p[1], p[2]
    matrix["iso"] = (E, nu)

    if "elastic" in yarn and yarn.get("elastic_type", "").startswith("ENGINEERING"):
        yarn["eng"] = yarn["elastic"][:9]
    else:
        p = yarn.get("props", [])
        if len(p) < 10:
            sys.exit("ERROR: yarn card has %d constants, need at least 10 "
                     "(phase + 9 elastic)" % len(p))
        yarn["eng"] = p[1:10]

    return {"MATRIX": matrix, "YARN": yarn}


def fmt(x):
    """Compact but full-precision number formatting for .inp data lines."""
    return repr(float(x)) if abs(x) >= 1e-4 or x == 0.0 else "%.12e" % x


# --------------------------------------------------------------------------- #
#  material blocks
# --------------------------------------------------------------------------- #

def patch_materials(matrix_es, yarn_elsets, E, nu, alpha, Tref, expansion=True):
    """One isotropic material on every element set -- no orientation, no UMAT."""
    L = ["** PATCH TEST MATERIAL",
         "** A single homogeneous isotropic solid on every element set.  With",
         "** correct PBC the strain field must come out exactly uniform, so any",
         "** scatter in S/E across the mesh is a constraint defect, not physics.",
         "*Material, Name=PATCH_ISO",
         "*Elastic",
         "%s, %s" % (fmt(E), fmt(nu))]
    if expansion:
        L += ["*Expansion, zero=%s" % fmt(Tref), "%s," % fmt(alpha)]
    for es in [matrix_es or "Matrix"] + list(yarn_elsets):
        L.append("*Solid Section, ElSet=%s, Material=PATCH_ISO" % es)
        L.append("1.0,")
    return "\n".join(L)


def elastic_materials(matrix_es, yarn_elsets, orient, mats, Tref, expansion=True):
    """The real two-phase RVE with damage removed: matrix isotropic, yarn
    orthotropic in the TexGen fibre frame.  Same constants as the UMAT cards."""
    E, nu = mats["MATRIX"]["iso"]
    a_m = mats["MATRIX"].get("alpha", [0.0])[0]
    eng = mats["YARN"]["eng"]
    a_y = mats["YARN"].get("alpha", [0.0, 0.0, 0.0])
    if len(a_y) < 3:
        a_y = [a_y[0]] * 3

    L = ["** ELASTIC HOMOGENISATION MATERIALS",
         "** Identical constants to the ZHANG2022 UMAT cards, with the damage and",
         "** plasticity machinery removed, so the run is linear and the extracted",
         "** stiffness is the undamaged homogenised stiffness of the RVE.",
         "*Material, Name=SIC_MATRIX_ELASTIC",
         "*Elastic",
         "%s, %s" % (fmt(E), fmt(nu))]
    if expansion:
        L += ["*Expansion, zero=%s" % fmt(Tref), "%s," % fmt(a_m)]
    L += ["*Material, Name=CSIC_YARN_ELASTIC",
          "*Elastic, type=ENGINEERING CONSTANTS",
          ", ".join(fmt(v) for v in eng[:8]),
          fmt(eng[8]) + ","]
    if expansion:
        L += ["*Expansion, type=ORTHO, zero=%s" % fmt(Tref),
              ", ".join(fmt(v) for v in a_y[:3])]
    L += ["*Solid Section, ElSet=%s, Material=SIC_MATRIX_ELASTIC"
          % (matrix_es or "Matrix"), "1.0,"]
    for es in yarn_elsets:
        L.append("*Solid Section, ElSet=%s, Material=CSIC_YARN_ELASTIC, Orientation=%s"
                 % (es, orient))
        L.append("1.0,")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
#  steps
# --------------------------------------------------------------------------- #

def _driver_bc(active, eps):
    """Prescribe all six drivers: `active` at eps, the rest clamped at zero.

    Clamping the other five is what makes the answer a *column of the stiffness
    matrix*.  Leave them free and Abaqus relaxes them to zero macro stress, which
    is a column of the compliance matrix instead -- a different experiment.

    Deliberately NOT op=NEW: that would also drop the model-level corner pin on
    MasterNode1 and leave the cell free to float.  The default op=MOD overwrites
    the six driver magnitudes, which is exactly the reset each load case needs
    since all six are respecified every step."""
    lines = ["*Boundary"]
    for i in range(6):
        lines.append("ConstraintsDriver%d, 1, 1, %s"
                     % (i, fmt(eps if i == active else 0.0)))
    return "\n".join(lines)


OUTPUT_BLOCK = "\n".join(
    ["** One frame at the end of each step is all the postprocessor needs.",
     "*Output, field, number interval=1",
     "*Element Output, directions=YES",
     "S, E, IVOL",
     "*Node Output",
     "U, RF",
     "*Output, history, frequency=1"] +
    ["*Node Output, nset=ConstraintsDriver%d\nU, RF" % i for i in range(6)])


def steps(eps, Tref, dT):
    S = []
    for name, drv, note in LOAD_CASES:
        S.append("*Step, Name=%s, nlgeom=NO" % name)
        S.append("Unit load case: %s applied through ConstraintsDriver%d" % (note, drv))
        S.append("*Static")
        S.append("1.0, 1.0, 1.0E-08, 1.0")
        S.append(_driver_bc(drv, eps))
        # Held at the reference temperature so these six cases are purely
        # mechanical.  Stated explicitly rather than relying on carry-over.
        S.append("*Temperature")
        S.append("AllNodes, %s" % fmt(Tref))
        S.append(OUTPUT_BLOCK)
        S.append("*End Step")

    # thermal load case: macro strain fully clamped, uniform temperature rise
    S.append("*Step, Name=LC7_dT, nlgeom=NO")
    S.append("Unit thermal load case: all macro strains clamped, uniform +%g degC"
             % dT)
    S.append("*Static")
    S.append("1.0, 1.0, 1.0E-08, 1.0")
    S.append("*Boundary")
    for i in range(6):
        S.append("ConstraintsDriver%d, 1, 1, 0.0" % i)
    S.append("*Temperature")
    S.append("AllNodes, %s" % fmt(Tref + dT))
    S.append(OUTPUT_BLOCK)
    S.append("*End Step")
    return "\n".join(S)


# --------------------------------------------------------------------------- #

def strip_pbc(kept):
    """Drop our own periodic constraints: the *Equation set, the driver nodes and
    their sets, and the corner pin.

    EasyPBC builds its own constraint equations and its own reference points, so
    it must be handed a bare mesh.  Leaving ours in place would double-constrain
    every boundary node and abort the job."""
    drivers = set()
    for kw, data in kept:
        if kwname(kw) == "nset" and \
                (kw_option(kw, "NSet") or "").upper().startswith("CONSTRAINTSDRIVER"):
            for line in data:
                for tok in line.split(","):
                    tok = tok.strip()
                    if tok.isdigit():
                        drivers.add(int(tok))

    out = []
    for kw, data in kept:
        name = kwname(kw)
        if name in ("equation", "boundary"):
            continue
        if name == "nset" and \
                (kw_option(kw, "NSet") or "").upper().startswith("CONSTRAINTSDRIVER"):
            continue
        if name == "node":
            labels = set()
            for line in data:
                tok = line.split(",")[0].strip()
                if tok.isdigit():
                    labels.add(int(tok))
            if labels and labels <= drivers:        # a driver-only *Node block
                continue
        out.append((kw, data))
    return out


def build(mesh_text, kind, mats, eps, Tref, dT, source):
    """kind is one of patch | elastic | patch_cae | elastic_cae."""
    homogeneous = kind.startswith("patch")
    for_cae = kind.endswith("_cae")

    kept, matrix_es, yarn_es, orient, max_node, seen = filter_mesh(
        mesh_text, drop_orientation=homogeneous)
    orient = orient or "TexGenOrientations"
    if for_cae:
        kept = strip_pbc(kept)

    if homogeneous:
        E, nu = mats["MATRIX"]["iso"]
        alpha = mats["MATRIX"].get("alpha", [0.0])[0]
        matsec = patch_materials(matrix_es, yarn_es, E, nu, alpha, Tref,
                                 expansion=not for_cae)
        what = "homogeneous isotropic"
    else:
        matsec = elastic_materials(matrix_es, yarn_es, orient, mats, Tref,
                                   expansion=not for_cae)
        what = "two-phase RVE, damage off"

    if for_cae:
        title = ("EasyPBC INPUT (%s) -- mesh + materials only, no constraints, "
                 "no steps" % what)
    else:
        title = "PBC %s (%s)" % ("PATCH TEST" if homogeneous
                                 else "HOMOGENISATION", what)

    parts = ["*Heading", " %s" % title,
             " source mesh: %s" % os.path.basename(source),
             " generated by make_pbc_check.py"]
    if for_cae:
        parts.append(" import into CAE, then run the EasyPBC plug-in on the "
                     "instance")
    else:
        parts.append(" 6 macro-strain load cases + 1 thermal;"
                     " applied strain %g, reference T %g degC" % (eps, Tref))
    parts.append(" units mm, N, MPa, degC")
    parts.append(emit_blocks(kept))

    extra = allnodes_block(max_node, seen)
    if extra:
        parts.append(extra)
    parts.append(matsec)
    if not for_cae:
        parts.append("*Initial Conditions, type=TEMPERATURE")
        parts.append("AllNodes, %s" % fmt(Tref))
        parts.append(steps(eps, Tref, dT))
    return "\n".join(parts) + "\n", (matrix_es, yarn_es, orient)


def main():
    ap = argparse.ArgumentParser(
        description="Build PBC patch-test and homogenisation decks from a TexGen RVE.")
    ap.add_argument("mesh", help="TexGen-exported .inp with PBC (e.g. a ZHANG2022 deck)")
    ap.add_argument("--prefix", default="PBC", help="output filename prefix (default PBC)")
    ap.add_argument("--eps", type=float, default=1.0e-3,
                    help="applied macro strain per load case (default 1e-3)")
    ap.add_argument("--temp", type=float, default=23.0,
                    help="reference/analysis temperature in degC (default 23)")
    ap.add_argument("--dT", type=float, default=1.0,
                    help="temperature rise for the CTE load case (default 1)")
    ap.add_argument("--only", choices=["patch", "elastic", "patch_cae",
                                       "elastic_cae"], default=None,
                    help="build only one deck instead of all of them")
    ap.add_argument("--no-cae", action="store_true",
                    help="skip the two EasyPBC input decks")
    ap.add_argument("--outdir", default=".", help="output directory (default .)")
    args = ap.parse_args()

    with open(args.mesh) as fh:
        text = fh.read()

    mats = read_materials(text)
    E, nu = mats["MATRIX"]["iso"]
    print("source deck : %s" % args.mesh)
    print("matrix      : E=%g MPa, nu=%g, alpha=%g /K"
          % (E, nu, mats["MATRIX"].get("alpha", [0])[0]))
    print("yarn        : E1=%g, E2=%g, E3=%g MPa; G12=%g, G13=%g, G23=%g MPa"
          % tuple(mats["YARN"]["eng"][i] for i in (0, 1, 2, 6, 7, 8)))
    print("              nu12=%g, nu13=%g, nu23=%g" % tuple(mats["YARN"]["eng"][3:6]))

    if args.only:
        kinds = [args.only]
    else:
        kinds = ["patch", "elastic"]
        if not args.no_cae:
            kinds += ["patch_cae", "elastic_cae"]

    for kind in kinds:
        body, (mes, yes_, orient) = build(text, kind, mats, args.eps,
                                          args.temp, args.dT, args.mesh)
        out = os.path.join(args.outdir, "%s_%s.inp" % (args.prefix, kind.upper()))
        with open(out, "w") as fh:
            fh.write(body)
        print("wrote %s  (matrix ElSet=%s, %d yarn ElSets%s)"
              % (out, mes or "Matrix", len(yes_),
                 ", orientation=%s" % orient if not kind.startswith("patch") else ""))

    print("")
    print("next -- our own PBC:")
    print("  abaqus job=%s_PATCH input=%s_PATCH.inp double interactive"
          % (args.prefix, args.prefix))
    print("  abaqus python postprocess/extract_stiffness.py %s_PATCH.odb --patch"
          % args.prefix)
    print("  (the ELASTIC deck needs the TexGen .ori file beside it; PATCH does not)")
    if any(k.endswith("_cae") for k in kinds):
        print("")
        print("next -- EasyPBC cross-check:")
        print("  abaqus cae noGUI=abaqus/make_easypbc_model.py -- %s_PATCH_CAE.inp"
              % args.prefix)


if __name__ == "__main__":
    main()
