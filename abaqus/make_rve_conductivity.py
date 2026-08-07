#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_rve_conductivity.py
========================
Builds the RVE_COND deck: steady-state conduction on the RVE, three
directions in ONE job.

WHY THIS IS WORTH RUNNING NOW
-----------------------------
It is the one job that is NOT blocked on the tension step.  Conduction is
linear, uses no UMAT and no damage, and does not care that M5/M6 stop at
70 % of their pull.  It runs in seconds and it unblocks the macro chain:
without kbar there is no quench analysis, and 4.7.3 already proved the
matrix conductivity row cannot simply be taken from Snead.

WHAT IT MEASURES, AND THE ONE THING IT CANNOT
---------------------------------------------
Hot and cold faces on one axis, the other four faces adiabatic, then

    kbar_i = Q_i * L_i / (A_i * dT)

with Q_i the summed reaction flux on the hot face.  This is the standard
1-D homogenisation, and it is NOT the rigorous periodic one: insulating the
sides suppresses the transverse heat flow a periodic medium would allow, so
a single cell reads slightly low.  conductivity_bounds.py brackets the
answer between series and parallel; this job says where inside that bracket
the real weave sits.  It cannot narrow the bracket itself.

WHY THE DECK IS SPLICED RATHER THAN GENERATED
---------------------------------------------
make_rve_virtual_tests.py builds this from a TexGen export, but the coarse
mesh source is not in the repository -- only the assembled decks are (the
same reason retune_deck.py exists).  So this reuses the assembled deck's
mesh, orientation and element sets verbatim and rewrites only what a
thermal analysis needs.

  ** The face node sets are REBUILT from coordinates. **  The deck's own
  FaceA..FaceF are TexGen's periodic-pairing sets and are NOT full faces:
  FaceA holds 58 nodes where the x = 2.625 plane actually has 122.  Driving
  a thermal BC with those would heat the yarn cross-sections only and
  silently report a wrong kbar.

  python3 make_rve_conductivity.py <assembled.inp> -o RVE_COND.inp \
          --matrix-porosity 0.324
  python3 make_rve_conductivity.py --check
"""
from __future__ import print_function

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "data", "properties"))

MAT_ANCHOR = "*Material, Name=SIC_MATRIX_DAMAGE"
TOL = 1.0e-6
DT = 1.0                       # K across the cell; kbar is linear in it

#: Matrix porosity consistent with Ch.4 4.9-13.  That section derives a
#: COMPOSITE porosity of 19.6 % from the measured density; the matrix (pocket
#: plus the SiC inside the yarns) is 0.60546 of the cell, so the matrix's own
#: porosity is 0.196/0.60546 = 0.324.  Passing the composite number here
#: instead would under-apply it by a factor 1.65.
COMPOSITE_POROSITY = 0.19626
MATRIX_VOLUME_FRACTION = 0.60546


def matrix_porosity_from_composite(vp=COMPOSITE_POROSITY,
                                   vm=MATRIX_VOLUME_FRACTION):
    return vp / vm


def parse_nodes(text):
    m = re.search(r"(?m)^\*Node\n(.*?)(?=\n\*)", text, re.S)
    if not m:
        raise ValueError("no *Node block")
    coord = {}
    for ln in m.group(1).splitlines():
        p = [x.strip() for x in ln.split(",") if x.strip()]
        if len(p) == 4:
            coord[int(p[0])] = tuple(float(x) for x in p[1:])
    return coord, m


def driver_nodes(text):
    return set(int(mm.group(2)) for mm in re.finditer(
        r"\*NSet, NSet=ConstraintsDriver(\d+)\s*\n\s*(\d+)", text))


def box(coord, drivers):
    mesh = dict((n, c) for n, c in coord.items() if n not in drivers)
    lo = [min(c[k] for c in mesh.values()) for k in range(3)]
    hi = [max(c[k] for c in mesh.values()) for k in range(3)]
    return mesh, lo, hi


def face_sets(mesh, lo, hi):
    """Full boundary-plane node sets, built from coordinates.

    Returns {name: sorted node list} for FACE_XLO..FACE_ZHI.  The counts are
    returned too so the caller can assert the pair sizes match -- an unequal
    pair means the mesh is not periodic in that direction and the whole
    measurement is suspect.
    """
    out = {}
    for k, ax in enumerate("XYZ"):
        for tag, v in (("LO", lo[k]), ("HI", hi[k])):
            out["FACE_%s%s" % (ax, tag)] = sorted(
                n for n, c in mesh.items() if abs(c[k] - v) < TOL)
    return out


def nset_block(name, nodes, per_line=8):
    L = ["*NSet, NSet=%s, Unsorted" % name]
    for i in range(0, len(nodes), per_line):
        L.append(", ".join(str(x) for x in nodes[i:i + per_line]))
    return "\n".join(L)


def strip_drivers(text, drivers):
    """Remove the dummy driver nodes from EVERY *Node block in `text`.

    There is more than one.  The assembled deck interleaves them:

        *NSet, NSet=ConstraintsDriver0
        5681
        *Node
        5682, 0, 0, 0
        *NSet, NSet=ConstraintsDriver1
        ...

    so each driver's coordinates live in a SEPARATE one-line *Node block, and
    editing only the first (the mesh) leaves all six behind.  That was the
    first version of this function and it silently did nothing: the drivers
    survived as orphan nodes.  Here they happen to sit at (0,0,0), inside the
    cell, so extract_kbar.py's bounding box came out right by luck -- put the
    drivers outside the box, as many generators do, and the box, the face
    areas and every kbar would have been wrong with no error anywhere.

    A *Node block left empty by the removal has its header dropped too, since
    a keyword with no data lines is not valid input.
    """
    def prune(m):
        body = [ln for ln in m.group(1).splitlines()
                if not (len(ln.split(",")) == 4
                        and ln.split(",")[0].strip().isdigit()
                        and int(ln.split(",")[0]) in drivers)]
        body = [ln for ln in body if ln.strip()]
        if not body:
            return ""                       # drop the orphaned *Node header
        return "*Node\n" + "\n".join(body) + "\n"

    return re.sub(r"(?m)^\*Node\s*$\n((?:[^*\n][^\n]*\n)+)", prune, text)


def remaining_driver_nodes(text, drivers):
    """Driver ids still defined in any *Node block -- 0 means clean."""
    found = set()
    for m in re.finditer(r"(?m)^\*Node\s*$\n((?:[^*\n][^\n]*\n)+)", text):
        for ln in m.group(1).splitlines():
            p = [x.strip() for x in ln.split(",") if x.strip()]
            if len(p) == 4 and p[0].isdigit() and int(p[0]) in drivers:
                found.add(int(p[0]))
    return sorted(found)


def thermal_materials(porosity, k_matrix, k1_f, k2_f):
    import make_rve_virtual_tests as mv
    tp = mv.thermal_properties(porosity=porosity, k_matrix=k_matrix,
                              k1_f=k1_f, k2_f=k2_f)
    m = tp["_meta"]
    L = ["**",
         "** THERMAL CONSTITUENT CARD -- every value derived, none typed.",
         "**   fibre  k11 = %g, k22 = %g W/(m.K)   refs/[22] and refs/[17]"
         % (m["k1_f"], m["k2_f"]),
         "**   SiC    k = %g dense -> %.4f W/(m.K) at %.1f %% MATRIX porosity"
         % (m["k_matrix_dense"], m["k_matrix_eff"], 100.0 * m["porosity"]),
         "**   yarn   k_long = %.4f, k_trans = %.4f W/(m.K)"
         % (m["k_long"], m["k_trans"]),
         "**"]
    if m["porosity"] <= 0.0:
        L += ["** !! ZERO POROSITY.  The mesh is a FILLED CELL, so this deck",
              "**    OVERPREDICTS kbar and makes the quench gradient too",
              "**    shallow -- the NON-CONSERVATIVE direction.  Kept only as",
              "**    the upper bracket; see Ch.4 4.7.3 and 4.9-13.", "**"]
    L += ["*Material, Name=SIC_MATRIX_THERMAL",
          "*Conductivity", "%.6g," % tp["matrix"]["k"],
          "*Density", "%.6g," % tp["matrix"]["rho"],
          "*Specific Heat", "%.6g," % tp["matrix"]["cp"],
          "*Material, Name=CSIC_YARN_THERMAL",
          "*Conductivity, type=ORTHO",
          "%.6g, %.6g, %.6g" % (tp["yarn_axial"]["k"], tp["yarn_trans"],
                                tp["yarn_trans"]),
          "*Density", "%.6g," % tp["yarn_axial"]["rho"],
          "*Specific Heat", "%.6g," % tp["yarn_axial"]["cp"]]
    return "\n".join(L), tp


def steps(dt=DT):
    """Three steady conductions, one per axis, each on a CLEAN slate.

    `op=NEW` is the whole point of this function.  Abaqus carries boundary
    conditions forward from step to step unless a step replaces them, so a
    bare `*Boundary` in step 2 does not remove step 1's x-gradient -- it
    ADDS a y-gradient on top of it, and step 3 then runs with all three
    imposed at once.  Corner nodes end up with two conflicting prescribed
    temperatures, and the reaction fluxes stop meaning what the extractor
    thinks they mean.

    That is not hypothetical.  The 2026-08-07 run produced kbar2 = 56.27
    W/(m.K) on a cell whose stiffest conducting phase is 25, which is
    impossible for any arrangement of the constituents -- and only kbar1,
    the FIRST step, was trustworthy.  make_macro_thermalshock.py already
    carried this rule in a comment; this file did not have it.
    """
    S = []
    for ax, name in enumerate("XYZ"):
        S += ["*Step, Name=kbar_dir%d, inc=100" % (ax + 1),
              "Steady conduction along %s; other four faces adiabatic" % name,
              "*Heat Transfer, steady state",
              "1.0, 1.0",
              # op=NEW: drop the PREVIOUS axis's gradient.  Without it the
              # second and third steps solve a superposition, not this axis.
              "*Boundary, op=NEW",
              "FACE_%sLO, 11, 11, 0.0" % name,
              "FACE_%sHI, 11, 11, %.6g" % (name, dt),
              "*Output, field",
              "*Node Output",
              "NT, RFL",
              "*Element Output",
              "HFL",
              "*Output, history, frequency=1",
              "*Node Output, nset=FACE_%sHI" % name,
              "RFL",
              "*End Step"]
    return "\n".join(S)


def build(text, a):
    i = text.find(MAT_ANCHOR)
    if i < 0:
        raise ValueError("anchor %r not found -- not an assembled ZHANG2022 "
                         "deck" % MAT_ANCHOR)
    coord, nm = parse_nodes(text)
    drivers = driver_nodes(text)
    if len(drivers) != 6:
        raise ValueError("expected 6 macro drivers, found %d" % len(drivers))
    mesh, lo, hi = box(coord, drivers)
    faces = face_sets(mesh, lo, hi)
    for ax in "XYZ":
        n1, n2 = len(faces["FACE_%sLO" % ax]), len(faces["FACE_%sHI" % ax])
        if n1 != n2:
            raise ValueError("FACE_%sLO has %d nodes but FACE_%sHI has %d -- "
                             "the mesh is not periodic in %s and kbar%s "
                             "cannot be trusted" % (ax, n1, ax, n2, ax, ax))
        if n1 == 0:
            raise ValueError("FACE_%sLO is empty" % ax)

    # everything up to the first *Equation: mesh, orientation, elsets, nsets
    j = text.find("*Equation")
    if j < 0 or j > i:
        raise ValueError("no *Equation block before the material anchor")
    head = text[:j].rstrip("\n")
    head = head.replace("*Element, Type=C3D4", "*Element, Type=DC3D4")
    if "DC3D4" not in head:
        raise ValueError("element type was not converted to DC3D4")
    # drop the driver nodes and the driver NSets
    head = strip_drivers(head, drivers)
    head = re.sub(r"\*NSet, NSet=ConstraintsDriver\d+\s*\n\s*\d+\s*\n", "",
                  head)
    left = remaining_driver_nodes(head, drivers)
    if left:
        raise ValueError("driver nodes %s survived in a *Node block; they "
                         "would become orphan nodes and can corrupt the "
                         "bounding box extract_kbar.py measures" % left)

    sections = re.findall(r"^\*Solid Section,.*\n.*$", text[i:], re.MULTILINE)
    if not sections:
        raise ValueError("no *Solid Section after the material anchor")
    sec = "\n".join(sections)
    sec = sec.replace("SIC_MATRIX_DAMAGE", "SIC_MATRIX_THERMAL")
    sec = sec.replace("CSIC_YARN_DAMAGE", "CSIC_YARN_THERMAL")

    mats, tp = thermal_materials(a.matrix_porosity, a.k_matrix, a.k1, a.k2)
    parts = [head,
             "\n".join(nset_block(k, v) for k, v in sorted(faces.items())),
             mats, sec, steps(a.dt)]
    L = [hi[k] - lo[k] for k in range(3)]
    return "\n".join(parts) + "\n", dict(
        faces=dict((k, len(v)) for k, v in faces.items()), L=L, tp=tp,
        drivers=sorted(drivers))


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))


def _fake_deck():
    """A 2-element cube-ish deck with the same structure as the real one."""
    nodes = []
    idx, coord = {}, {}
    n = 1
    for x in (0.0, 1.0):
        for y in (0.0, 1.0):
            for z in (0.0, 0.5):
                idx[(x, y, z)] = n
                coord[n] = (x, y, z)
                nodes.append("%d, %g, %g, %g" % (n, x, y, z))
                n += 1
    for k in range(6):
        nodes.append("%d, 0., 0., 0." % (5681 + k))
    return "\n".join(
        ["*Heading", " fake", "*Node"] + nodes +
        ["*Element, Type=C3D4",
         "1, 1, 2, 3, 5",
         "2, 4, 6, 7, 8",
         "*Distribution Table, Name=TexGenOrientationVectors",
         "COORD3D, COORD3D",
         "*Orientation, Name=TexGenOrientations, Definition=coordinates",
         "TexGenOrientationVectors",
         "1, 0",
         "*ElSet, ElSet=Matrix", "1",
         "*ElSet, ElSet=Yarn0", "2",
         "*NSet, NSet=AllNodes, Generate", "1, 8, 1"] +
        # Interleaved exactly as the assembled deck writes them: each
        # driver's coordinates sit in its OWN one-line *Node block.
        sum([["*NSet, NSet=ConstraintsDriver%d" % k, "%d" % (5681 + k),
              "*Node", "%d, 0, 0, 0" % (5681 + k)] for k in range(6)], []) +
        ["*NSet, NSet=FaceA, Unsorted", "1",
         "*Equation", "2", "FaceA, 1, 1.0, FaceB, 1, -1.0",
         MAT_ANCHOR,
         "*Depvar", "20,",
         "*User Material, constants=22", "2.0, 350000.0",
         "*Expansion, zero=1050.", "4.5e-06,",
         "*Material, Name=CSIC_YARN_DAMAGE",
         "*Depvar", "16,",
         "*User Material, constants=38", "1.0, 254967.0",
         "*Solid Section, ElSet=Matrix, Material=SIC_MATRIX_DAMAGE", "1.0,",
         "*Solid Section, ElSet=Yarn0, Material=CSIC_YARN_DAMAGE, "
         "Orientation=TexGenOrientations", "1.0,",
         "*Initial Conditions, type=TEMPERATURE", "AllNodes, 1050.",
         "*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=2000",
         "cool", "*Static", "0.001, 1.0, 1e-08, 0.0025",
         "*Temperature", "AllNodes, 23.", "*End Step"]) + "\n"


class _A(object):
    matrix_porosity = 0.0
    k_matrix, k1, k2 = 25.0, 8.0, 1.0
    dt = DT


def selftest():
    print("=" * 78)
    print("make_rve_conductivity.py --check")
    print("=" * 78)
    deck = _fake_deck()

    print("\n A. the porosity that goes in is the MATRIX's, not the cell's")
    mp = matrix_porosity_from_composite()
    ck("composite 19.6 % becomes matrix 32.4 %",
       abs(mp - 0.3242) < 0.001, "%.4f" % mp)
    ck("passing the composite number would under-apply it by 1.65x",
       abs(mp / COMPOSITE_POROSITY - 1.652) < 0.01,
       "%.3fx" % (mp / COMPOSITE_POROSITY))
    ck("matrix volume fraction matches porosity_stiffness.py",
       abs(MATRIX_VOLUME_FRACTION - (0.4982 * (1 - 0.79194) + 0.5018)) < 1e-4)

    print("\n B. the deck is converted to a thermal analysis")
    out, info = build(deck, _A())
    ck("elements are DC3D4, not C3D4",
       "*Element, Type=DC3D4" in out and "Type=C3D4" not in out)
    ck("the displacement PBC *Equation blocks are gone",
       "*Equation" not in out)
    # Check EVERY *Node block, not the first: the drivers live in separate
    # one-line blocks and the first version of strip_drivers missed all six.
    nb_in = len(re.findall(r"(?m)^\*Node\s*$", deck))
    nb_out = len(re.findall(r"(?m)^\*Node\s*$", out))
    ck("the fixture reproduces the interleaved driver layout",
       nb_in == 7 and remaining_driver_nodes(deck, set(range(5681, 5687)))
       == list(range(5681, 5687)),
       "%d *Node blocks in, all 6 drivers present" % nb_in)
    ck("the six macro drivers are gone from EVERY *Node block",
       remaining_driver_nodes(out, set(info["drivers"])) == [],
       "%d *Node blocks in -> %d out (6 one-line driver blocks dropped)"
       % (nb_in, nb_out))
    ck("a *Node block emptied by the removal loses its header too",
       "*Node\n*NSet" not in out and "*Node\n*Material" not in out)
    ck("the ConstraintsDriver NSets are removed",
       "ConstraintsDriver" not in out)
    ck("the orientation survives -- ORTHO conductivity needs it",
       "*Orientation, Name=TexGenOrientations" in out
       and "TexGenOrientationVectors" in out)
    ck("the solid sections point at the THERMAL materials",
       "Material=SIC_MATRIX_THERMAL" in out
       and "Material=CSIC_YARN_THERMAL" in out
       and "DAMAGE" not in out)
    ck("no *User Material, *Depvar or *Expansion survives",
       "*User Material" not in out and "*Depvar" not in out
       and "*Expansion" not in out)
    ck("no *Static step survives", "*Static" not in out)

    print("\n C. the face sets are rebuilt, not inherited")
    ck("six FACE_ sets are written",
       all("FACE_%s%s" % (a, b) in out
           for a in "XYZ" for b in ("LO", "HI")))
    ck("TexGen's partial FaceA is NOT used as a boundary",
       "FACE_XLO, 11, 11" in out and "FaceA, 11" not in out)
    for ax in "XYZ":
        ck("FACE_%sLO and FACE_%sHI have equal node counts" % (ax, ax),
           info["faces"]["FACE_%sLO" % ax] == info["faces"]["FACE_%sHI" % ax],
           "%d each" % info["faces"]["FACE_%sLO" % ax])

    print("\n D. three directions, one job")
    ck("three steps", out.count("*Step, Name=kbar_dir") == 3)
    ck("all steady state", out.count("*Heat Transfer, steady state") == 3)
    ck("each step drives its own axis pair",
       all(("FACE_%sLO, 11, 11, 0.0" % a) in out
           and ("FACE_%sHI, 11, 11, 1" % a) in out for a in "XYZ"))
    ck("RFL is written to HISTORY on the hot face -- homogenize.py reads it",
       out.count("*Node Output, nset=FACE_XHI\nRFL") == 1
       and out.count("*Output, history") == 3)
    ck("step names are what homogenize.py matches on",
       all(("kbar_dir%d" % k) in out for k in (1, 2, 3)),
       "conductivity() looks for KBAR_DIR<n>")
    ck("no face is both heated and insulated in the same step",
       out.count("11, 11,") == 6)
    # 2026-08-07: this is the check that was missing, and its absence cost a
    # whole run.  Abaqus carries boundary conditions across steps, so every
    # *Boundary after the first must REPLACE rather than add -- otherwise
    # step 2 solves x+y and step 3 solves x+y+z.  The run that exposed it
    # returned kbar2 = 56.27 W/(m.K) on a cell whose best conductor is 25.
    # Only STEP-level boundaries need op=NEW.  A model-data *Boundary (the
    # assembled deck fixes its PBC master node) must stay bare -- op= is a
    # step parameter -- so the check keys on the FACE_ data line, not on a
    # bare count, which would false-positive on that one.
    import re as _re
    step_bc = _re.findall(r"\*Boundary(, op=NEW)?\nFACE_", out)
    ck("every step-level *Boundary replaces the previous step's",
       len(step_bc) == 3 and all(b == ", op=NEW" for b in step_bc),
       "%d step boundaries, %d with op=NEW"
       % (len(step_bc), sum(1 for b in step_bc if b)))
    ck("  and the reason is written down where the steps are built",
       "carries boundary" in steps.__doc__
       and "conditions forward" in steps.__doc__)

    print("\n E. the physics inputs are the audited ones")
    tp = info["tp"]["_meta"]
    ck("dense matrix k = 25 W/(m.K), not Snead's 293",
       tp["k_matrix_dense"] == 25.0,
       "Snead's single-crystal value is PROVEN unusable (4.7.3)")
    ck("fibre k22 = 1.0 with two independent citations", tp["k2_f"] == 1.0)
    ck("zero porosity is loudly flagged as the upper bracket",
       "ZERO POROSITY" in out and "NON-CONSERVATIVE" in out)
    a2 = _A()
    a2.matrix_porosity = mp
    out2, info2 = build(deck, a2)
    ck("porosity lowers the matrix conductivity",
       info2["tp"]["matrix"]["k"] < info["tp"]["matrix"]["k"],
       "%.5g -> %.5g W/(mm.K)"
       % (info["tp"]["matrix"]["k"], info2["tp"]["matrix"]["k"]))
    ck("porosity lowers the yarn conductivity too",
       info2["tp"]["yarn_trans"] < info["tp"]["yarn_trans"])
    ck("the zero-porosity warning disappears when porosity is on",
       "ZERO POROSITY" not in out2)
    ck("conductivity is written in W/(mm.K), the deck's unit system",
       abs(info["tp"]["matrix"]["k"] - 0.025) < 1e-9,
       "25 W/(m.K) = 0.025 W/(mm.K)")

    print("\n F. it refuses to build something untrustworthy")
    bad = deck.replace(MAT_ANCHOR, "*Material, Name=OTHER")
    try:
        build(bad, _A())
        ck("a deck without the material anchor is rejected", False)
    except ValueError:
        ck("a deck without the material anchor is rejected", True)
    bad2 = deck.replace("*NSet, NSet=ConstraintsDriver5\n5686\n", "")
    try:
        build(bad2, _A())
        ck("a deck with the wrong driver count is rejected", False)
    except ValueError:
        ck("a deck with the wrong driver count is rejected", True)
    # an unequal face pair must be fatal, not a warning
    moved = deck.replace("8, 1, 1, 0.5", "8, 1, 1, 0.4")
    if moved != deck:
        try:
            build(moved, _A())
            ck("an unequal face pair is rejected", False)
        except ValueError:
            ck("an unequal face pair is rejected", True)
    else:
        ck("an unequal face pair is rejected", True, "(fixture unchanged)")

    print("\n G. the limitation is written down, not left to be discovered")
    src = open(os.path.join(HERE, "make_rve_conductivity.py")).read()
    for phrase, why in (
            ("NOT the rigorous periodic one",
             "must say the insulated-side method is an approximation"),
            ("are NOT full faces",
             "must say why TexGen's own face sets are unusable"),
            ("It cannot narrow the bracket itself",
             "must not claim more than the job delivers")):
        ck("source states: %s" % why, phrase in src)

    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:3])))
        print("=" * 78)
        return 1
    print("ALL %d RVE-CONDUCTIVITY CHECKS PASS" % len(_OK))
    print("=" * 78)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Build the RVE steady-state conductivity deck.")
    ap.add_argument("deck", nargs="?", help="assembled ZHANG2022 .inp")
    ap.add_argument("-o", "--out", help="output .inp")
    ap.add_argument("--matrix-porosity", dest="matrix_porosity", type=float,
                    default=0.0,
                    help="POROSITY OF THE MATRIX ITSELF, not of the cell. "
                         "Ch.4 4.9-13's composite 19.6 %% corresponds to "
                         "%.4f here. 0 keeps the filled cell, which "
                         "OVERPREDICTS kbar."
                         % matrix_porosity_from_composite())
    ap.add_argument("--k-matrix", dest="k_matrix", type=float, default=25.0,
                    help="dense SiC conductivity [W/(m.K)] (default 25). "
                         "NOT Snead's 293: 4.7.3 proves that value cannot "
                         "reproduce the measured composite k at any fibre "
                         "conductivity.")
    ap.add_argument("--k1", type=float, default=8.0,
                    help="fibre AXIAL conductivity [W/(m.K)] (default 8, "
                         "refs/[17] and refs/[22]). Pradere measures 46-72 "
                         "on a single filament; that conflict is UNRESOLVED "
                         "and is why this is a flag.")
    ap.add_argument("--k2", type=float, default=1.0,
                    help="fibre TRANSVERSE conductivity [W/(m.K)] "
                         "(default 1.0, two independent citations)")
    ap.add_argument("--dt", type=float, default=DT,
                    help="temperature difference across the cell [K]")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if a.check:
        sys.exit(selftest())
    if not a.deck:
        ap.error("give a deck, or --check")
    with open(a.deck) as f:
        text = f.read()
    out, info = build(text, a)
    dest = a.out or (os.path.splitext(a.deck)[0] + "_COND.inp")
    with open(dest, "w") as f:
        f.write(out)
    m = info["tp"]["_meta"]
    print("%s -> %s" % (a.deck, dest))
    print("  box        Lx=%.4f  Ly=%.4f  Lz=%.4f mm  (V=%.4f mm^3)"
          % tuple(info["L"] + [info["L"][0] * info["L"][1] * info["L"][2]]))
    print("  faces      " + "  ".join(
        "%s=%d" % (k.replace("FACE_", ""), v)
        for k, v in sorted(info["faces"].items())))
    print("  matrix     %.4f W/(m.K) at %.1f %% matrix porosity"
          % (m["k_matrix_eff"], 100.0 * m["porosity"]))
    print("  yarn       k_long=%.4f  k_trans=%.4f W/(m.K)"
          % (m["k_long"], m["k_trans"]))
    print("  steps      3 (kbar_dir1/2/3), steady state, dT=%g K" % a.dt)
    print("  READ WITH  abaqus python extract_kbar.py %s"
          % os.path.basename(dest).replace(".inp", ".odb"))


if __name__ == "__main__":
    main()
