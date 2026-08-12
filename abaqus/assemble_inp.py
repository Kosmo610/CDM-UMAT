#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_inp.py
===============
Splice the ZHANG2022 material cards + 3-step analysis onto a *new* TexGen mesh so
you can run a coarser RVE (e.g. 20k-40k C3D4) for quick trend checks, then re-run
this on a finer mesh later - WITHOUT hand-editing 8 MB files.

Why this works: with the crack-band regularisation in the UMAT, only the mesh and
the per-element fibre orientation change with refinement; the material cards and
the cooling/heating/tension steps do NOT. This script keeps the TexGen topology
(nodes, elements, orientation, ElSets, NSets, PBC equations) and replaces only the
material/section/step definitions.

INPUT : a TexGen-exported Abaqus .inp of the plain-weave RVE (any mesh density),
        flat model (no *Part/*Assembly), with:
          - *ElSet Matrix and *ElSet Yarn0..YarnN
          - an *Orientation (fibre direction)  [+ its .ori file kept alongside]
          - NSets ConstraintsDriver0..5 (Xia PBC dummy nodes) and the *Equation PBC
        The current V1_0/V2_0 decks are exactly this format.

OUTPUT: <prefix>_RT23.inp, <prefix>_T500.inp, <prefix>_T1000.inp
        (cool 1050->23, [heat 23->T], tension) using the chosen material card set.

Usage:
  python3 assemble_inp.py  my_coarse_mesh.inp
  python3 assemble_inp.py  my_coarse_mesh.inp --model v1 --prefix ZHANG2022_coarse
  python3 assemble_inp.py  my_coarse_mesh.inp --only RT23

Notes:
  * Keep the TexGen .ori file (per-element orientation) next to the output .inp.
  * The UMAT reads material by CMNAME: names MUST contain 'MATRIX' / 'YARN'.
  * double precision is required at run time:  abaqus ... double
"""
from __future__ import print_function
import sys
import os
import argparse

# ------------------------------------------------------------------ material cards
MATRIX_DEPVAR = """*Depvar
20,
1, DMT, Matrix tensile damage
2, DMC, Matrix compressive damage
3, RMT, Matrix maximum tensile criterion
4, RMC, Matrix maximum compressive criterion
5, DMACT, Stress-state-active matrix damage
6, I1SGN, Sign of first effective-stress invariant
7, MMODE, Dominant matrix mode: 1 tension, 2 compression
8, TMINIT, First matrix damage-initiation temperature
9, EQPS, Equivalent plastic strain
10, ATEFF, Effective softening factor (crack band)
11, MDJUMP, Matrix maximum historical damage jump
12, MCUTREQ, Matrix minimum historical PNEWDT factor
13, MTJUMP, Temperature at maximum matrix damage jump
14, MRJUMP, Criterion at maximum matrix damage jump
15, EP11, Plastic strain 11
16, EP22, Plastic strain 22
17, EP33, Plastic strain 33
18, EP12, Plastic strain 12 (engineering)
19, EP13, Plastic strain 13 (engineering)
20, EP23, Plastic strain 23 (engineering)"""

YARN_DEPVAR = """*Depvar
16,
1, DY1T, Yarn longitudinal tensile damage
2, DY1C, Yarn longitudinal compressive damage
3, DYTT, Yarn transverse tensile damage
4, DYTC, Yarn transverse compressive damage
5, RY1T, Maximum longitudinal tensile criterion
6, RY1C, Maximum longitudinal compressive criterion
7, RYTT, Maximum transverse tensile criterion
8, RYTC, Maximum transverse compressive criterion
9, DY1, Combined longitudinal yarn damage
10, DYT, Combined transverse yarn damage
11, YMODE, Dominant yarn mode: 1 1T, 2 1C, 3 TT, 4 TC
12, TYINIT, First yarn damage-initiation temperature
13, YDJUMP, Yarn maximum historical damage jump
14, YCUTREQ, Yarn minimum historical PNEWDT factor
15, YTEND, Temperature at maximum yarn damage jump
16, YRFAC, Criterion at maximum yarn damage jump"""

# 22-constant matrix cards.  v2 = full model (plasticity ON: SY0=250, HISO=1e5).
MATRIX_USERMAT = {
"v1": """*User Material, constants=22
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
0.0, 0.0, 1.15, 0.75, 0.50, 30.0""",
"v2": """*User Material, constants=22
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
250.0, 100000.0, 1.15, 0.75, 0.50, 30.0""",
}

# 38-constant yarn cards.  v2 = full model (Eq.18 ON, crack-band G1t=G1c=12.5,
# longitudinal strengths from T300 rule of mixtures at Vf=0.792).
YARN_USERMAT = {
"v1": """*User Material, constants=38
1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.247516386, 0.395813581, 26431.515264
26431.515264, 15876.667974, 1200.0, 1500.0, 80.0, 350.0, 120.0, 120.0
100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02
0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 0.0
0.0, 0.0, 0.0, 0.0, 0.0, 0.0""",
"v2": """*User Material, constants=38
1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.247516386, 0.395813581, 26431.515264
26431.515264, 15876.667974, 2835.0, 1956.0, 80.0, 350.0, 120.0, 120.0
100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02
0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 12.5
12.5, 0.0, 0.0, 700.0, 3.0, 8000.0""",
}

MATRIX_EXPANSION = """*Expansion, zero=1050.
4.5e-06,"""
YARN_EXPANSION = """*Expansion, type=ORTHO, zero=1050.
1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06"""

# ------------------------------------------------------------------ per-temperature setup
# (name, initial->final temp of each thermal step, testing temp, applied eps_xx)
CASES = {
    "RT23":  dict(test=23,   heat=None, eps=0.001500),
    "T500":  dict(test=500,  heat=500,  eps=0.003200),
    "T1000": dict(test=1000, heat=1000, eps=0.004800),
}

# Keywords whose whole block (keyword + data) must be DROPPED from the TexGen file
# because this script regenerates them. Everything else at model level is kept.
DROP = ("material", "depvar", "user material", "elastic", "density", "expansion",
        "plastic", "solid section", "shell section", "section", "initial conditions",
        "orientation")  # orientation handled specially below (kept, name captured)


def split_blocks(text):
    """Yield (keyword_line, [data_lines]) blocks. Comment-only (**) lines attach to
    the current block's data. A line starting with a single '*' opens a new block."""
    kw, data = None, []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith("*") and not s.startswith("**"):
            if kw is not None:
                yield kw, data
            kw, data = line, []
        else:
            if kw is None:      # preamble before first keyword (skip)
                continue
            data.append(line)
    if kw is not None:
        yield kw, data


def kwname(kw_line):
    return kw_line.lstrip().lstrip("*").split(",")[0].strip().lower()


def kw_option(kw_line, key):
    for tok in kw_line.split(",")[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k.strip().lower() == key.lower():
                return v.strip()
    return None


def filter_mesh(text):
    """Keep TexGen topology; drop material/section/step; capture elset+orientation."""
    kept, yarn_elsets, matrix_elset, orient_name = [], [], None, None
    in_step = False
    max_node = 0
    seen_allnodes = False
    for kw, data in split_blocks(text):
        name = kwname(kw)
        if name == "step":
            in_step = True
            continue
        if name == "end step":
            in_step = False
            continue
        if in_step:
            continue
        if name == "heading":
            continue                        # replaced by our own heading
        if name == "orientation":
            orient_name = kw_option(kw, "Name") or "TexGenOrientations"
            kept.append((kw, data))         # keep the orientation definition
            continue
        if name in ("elset", "el set"):
            es = kw_option(kw, "ElSet") or kw_option(kw, "elset")
            if es and es.lower().startswith("yarn"):
                yarn_elsets.append(es)
            elif es and es.lower() == "matrix":
                matrix_elset = es
            kept.append((kw, data))
            continue
        if name in ("nset", "n set"):
            if (kw_option(kw, "NSet") or "").lower() == "allnodes":
                seen_allnodes = True
            kept.append((kw, data))
            continue
        if name == "node":
            for d in data:
                d = d.strip()
                if d and not d.startswith("**"):
                    try:
                        max_node = max(max_node, int(d.split(",")[0]))
                    except ValueError:
                        pass
            kept.append((kw, data))
            continue
        if any(name.startswith(d) for d in DROP):
            continue
        kept.append((kw, data))             # node/element/distribution/boundary/equation/...
    return kept, matrix_elset, yarn_elsets, orient_name, max_node, seen_allnodes


def inline_ori(blocks, meshdir):
    """Paste the TexGen .ori contents into the deck instead of referencing it.

    TexGen writes the per-element fibre orientation to a separate file and the
    .inp points at it with `*Distribution, ..., Input=<name>.ori`.  That file
    is easy to lose when a deck is copied or zipped, and Abaqus then dies
    immediately.  Inlining makes the deck self-contained: one file to move,
    nothing to forget.

    Costs one extra line per element in the .inp, which is why it pairs
    naturally with the coarse trial meshes (20-40k elements).
    """
    out = []
    for kw, data in blocks:
        if kwname(kw) == "distribution":
            src = kw_option(kw, "Input")
            if src:
                path = src if os.path.isabs(src) else os.path.join(meshdir, src)
                if not os.path.exists(path):
                    sys.exit("ERROR: --inline-ori needs %s, which is missing.\n"
                             "       TexGen writes it next to the mesh .inp."
                             % path)
                toks = [t for t in kw.split(",")
                        if not t.strip().lower().startswith("input=")]
                kw = ",".join(toks)
                with open(path) as f:
                    extra = [l.rstrip("\n") for l in f
                             if l.strip() and not l.lstrip().startswith("**")]
                print("  inlined %s (%d rows)" % (src, len(extra)))
                data = list(data) + extra
        out.append((kw, data))
    return out


def emit_blocks(blocks):
    out = []
    for kw, data in blocks:
        out.append(kw)
        out.extend(data)
    return "\n".join(out)


def material_section(model, matrix_elset, yarn_elsets, orient):
    L = []
    L.append("*Material, Name=SIC_MATRIX_DAMAGE")
    L.append(MATRIX_DEPVAR)
    L.append(MATRIX_USERMAT[model])
    L.append(MATRIX_EXPANSION)
    L.append("*Material, Name=CSIC_YARN_DAMAGE")
    L.append(YARN_DEPVAR)
    L.append(YARN_USERMAT[model])
    L.append(YARN_EXPANSION)
    L.append("*Solid Section, ElSet=%s, Material=SIC_MATRIX_DAMAGE" % (matrix_elset or "Matrix"))
    L.append("1.0,")
    for es in yarn_elsets:
        L.append("*Solid Section, ElSet=%s, Material=CSIC_YARN_DAMAGE, Orientation=%s"
                 % (es, orient))
        L.append("1.0,")
    return "\n".join(L)


def _controls_and_output():
    hist = "\n".join(
        "*Node Output, nset=ConstraintsDriver%d\nU, RF" % i for i in range(6))
    return ("""*Controls, parameters=time incrementation
 8, 10, , 30, , , , 20, , ,
*Controls, parameters=field, field=displacement
 , 0.08
*Controls, parameters=line search
5
""", """*Output, field, number interval=101, time marks=NO
*Element Output, directions=YES
S, E, EE, THE, IVOL, SDV
*Node Output
U, RF
*Output, history, frequency=1
%s
*Restart, write, number interval=20, time marks=NO""" % hist)


def steps(case):
    ctrl, out = _controls_and_output()
    S = []
    # Step 1: cooling 1050 -> 23
    S.append("*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=10000")
    S.append("Uniform cooling from 1050 degC to 23 degC with progressive damage")
    S.append("*Static")
    S.append("0.001, 1.0, 1.0E-12, 0.0025")
    S.append(ctrl + "*Temperature\nAllNodes, 23.")
    S.append(out)
    S.append("*End Step")
    # Step 2 (optional): heating 23 -> T
    if case["heat"] is not None:
        T = case["heat"]
        S.append("*Step, Name=Heating_to_%dC, nlgeom=NO, inc=10000" % T)
        S.append("Uniform reheating from 23 degC to %d degC before tension" % T)
        S.append("*Static")
        S.append("0.001, 1.0, 1.0E-12, 0.0025")
        S.append(ctrl + "*Temperature\nAllNodes, %d." % T)
        S.append(out)
        S.append("*End Step")
    # Final step: tension via ConstraintsDriver0
    T = case["test"]
    S.append("*Step, Name=Tension_at_%dC, nlgeom=NO, inc=10000" % T)
    S.append("Uniaxial x tension at %d degC via ConstraintsDriver0" % T)
    S.append("*Static")
    S.append("0.0005, 1.0, 1.0E-12, 0.0025")
    S.append(ctrl + "*Boundary\nConstraintsDriver0, 1, 1, %.6f" % case["eps"])
    S.append(out)
    S.append("*End Step")
    return "\n".join(S)


def allnodes_block(max_node, seen):
    if seen or max_node <= 0:
        return None
    return "*NSet, NSet=AllNodes, Generate\n1, %d, 1" % max_node


def main():
    ap = argparse.ArgumentParser(description="Assemble ZHANG2022 decks from a TexGen mesh.")
    ap.add_argument("mesh", help="TexGen-exported Abaqus .inp (any mesh density)")
    ap.add_argument("--model", choices=["v1", "v2"], default="v2",
                    help="v2 = full model (default); v1 = verified elastic-damage baseline")
    ap.add_argument("--prefix", default="ZHANG2022", help="output filename prefix")
    ap.add_argument("--only", choices=list(CASES), default=None,
                    help="assemble only one temperature case")
    ap.add_argument("--inline-ori", action="store_true",
                    help="paste the TexGen .ori orientation data into the deck "
                         "so it is self-contained (no external file to lose)")
    args = ap.parse_args()

    with open(args.mesh) as f:
        text = f.read()
    kept, matrix_es, yarn_es, orient, max_node, seen = filter_mesh(text)
    if not yarn_es:
        sys.exit("ERROR: no 'Yarn*' ElSet found - is this a TexGen plain-weave export?")
    orient = orient or "TexGenOrientations"
    print("detected: matrix ElSet=%s, %d yarn ElSets %s, orientation=%s, max node=%d"
          % (matrix_es or "Matrix", len(yarn_es), yarn_es, orient, max_node))

    if args.inline_ori:
        kept = inline_ori(kept, os.path.dirname(os.path.abspath(args.mesh)))
    mesh_txt = emit_blocks(kept)
    extra = allnodes_block(max_node, seen)
    matsec = material_section(args.model, matrix_es, yarn_es, orient)

    cases = {args.only: CASES[args.only]} if args.only else CASES
    for tag, case in cases.items():
        parts = ["*Heading",
                 " ZHANG2022 C/SiC RVE - %s - model %s (assembled by assemble_inp.py)"
                 % (tag, args.model.upper()),
                 mesh_txt]
        if extra:
            parts.append(extra)
        parts.append(matsec)
        parts.append("*Initial Conditions, type=TEMPERATURE\nAllNodes, 1050.")
        parts.append(steps(case))
        out = args.prefix + "_" + tag + ".inp"
        with open(out, "w") as f:
            f.write("\n".join(parts) + "\n")
        print("wrote", out)
    if args.inline_ori:
        print("Done. Decks are SELF-CONTAINED (.ori inlined); "
              "run with 'abaqus ... double'.")
    else:
        print("Done. Keep the TexGen .ori file beside the outputs; "
              "run with 'abaqus ... double'.")


if __name__ == "__main__":
    main()
