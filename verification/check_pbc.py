#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_pbc.py
============
Static (no-Abaqus) audit of the periodic boundary conditions in a TexGen-exported
Abaqus deck.  Everything Abaqus would only tell you *after* a failed job -- unpaired
faces, a missing shear term, a double-eliminated DOF, a boundary node nobody
constrains -- is decided here from the .inp text alone, in a few seconds.

What it checks
--------------
1. MESH        bounding box -> lattice vectors Lx, Ly, Lz; driver nodes are free
               floating (attached to no element).
2. PAIRING     every set pair that appears in an *Equation (FaceA/FaceB,
               Edge2/Edge1, MasterNode7/MasterNode1, ...) has equal length and the
               k-th node of the slave set sits exactly one lattice vector away from
               the k-th node of the master set.  Abaqus pairs set members *by
               position*, so this ordering is the whole ballgame.
3. EQUATIONS   each equation is re-derived from the measured offset d and the
               TexGen driver convention

                   u_s - u_m = H . d ,
                   H = [[e_x , e_xy, e_xz],
                        [0   , e_y , e_yz],
                        [0   , 0   , e_z ]]         (CD0..CD5 = e_x,e_y,e_z,e_xy,e_xz,e_yz)

               and compared term by term with what the deck actually says.  A
               missing driver term, a wrong sign or a stale lattice length (the
               classic bug after a mesh regeneration) shows up here.
4. ELIMINATION Abaqus eliminates the FIRST DOF of every *Equation.  That DOF must
               appear as "first" exactly once in the whole deck and must not carry
               a *Boundary.  Violations are Abaqus "overconstraint" aborts.
5. COVERAGE    every node on the RVE surface belongs to exactly one of the
               face/edge/vertex sets, and no interior node is constrained.
6. RIGID BODY  exactly one corner is pinned in 1/2/3 (otherwise the stiffness
               matrix is singular).

Usage
-----
    python3 verification/check_pbc.py abaqus/ZHANG2022_RT23_V1_0.inp
    python3 verification/check_pbc.py <mesh.inp> --tol 1e-5 --json report.json

Exit status is 0 when every check passes, 1 otherwise -- so it can gate a run:

    python3 verification/check_pbc.py new_mesh.inp && abaqus job=... input=new_mesh.inp
"""
from __future__ import print_function

import argparse
import json
import os
import sys
from collections import OrderedDict, defaultdict

# --------------------------------------------------------------------------- #
#  .inp parsing
# --------------------------------------------------------------------------- #

DRIVER_NAMES = ["CONSTRAINTSDRIVER%d" % i for i in range(6)]
# H[row][col] = driver index supplying that component (None -> must be absent).
# row = dof-1 of the constrained displacement, col = direction of the offset d.
H_DRIVER = [[0, 3, 4],
            [None, 1, 5],
            [None, None, 2]]
DRIVER_LABEL = ["e_x", "e_y", "e_z", "e_xy", "e_xz", "e_yz"]


def _split(line):
    return [t.strip() for t in line.split(",")]


def parse_inp(path):
    """Minimal Abaqus deck reader: nodes, element connectivity, nsets, equations,
    boundary cards.  Keyword and set names are upper-cased (Abaqus is case
    insensitive); everything else is kept verbatim."""
    nodes = OrderedDict()
    nsets = OrderedDict()
    elsets = OrderedDict()
    elements = OrderedDict()
    equations = []
    boundaries = []

    mode = None            # NODE | ELEMENT | NSET | ELSET | EQUATION | BOUNDARY
    ctx = None             # per-mode scratch

    with open(path, "r") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            if line.lstrip().startswith("**"):          # comment
                continue

            if line.lstrip().startswith("*"):
                toks = _split(line.lstrip())
                kw = toks[0].lstrip("*").strip().upper()
                opts = {}
                flags = set()
                for t in toks[1:]:
                    if "=" in t:
                        k, v = t.split("=", 1)
                        opts[k.strip().upper()] = v.strip()
                    elif t:
                        flags.add(t.strip().upper())

                if kw == "NODE":
                    mode, ctx = "NODE", None
                elif kw == "ELEMENT":
                    mode, ctx = "ELEMENT", {"buf": []}
                elif kw == "NSET":
                    name = opts.get("NSET", "").upper()
                    nsets.setdefault(name, [])
                    mode = "NSET"
                    ctx = {"name": name, "generate": "GENERATE" in flags}
                elif kw == "ELSET":
                    name = opts.get("ELSET", "").upper()
                    elsets.setdefault(name, [])
                    mode = "ELSET"
                    ctx = {"name": name, "generate": "GENERATE" in flags}
                elif kw == "EQUATION":
                    mode = "EQUATION"
                    ctx = {"nterm": None, "terms": []}
                    equations.append(ctx)
                elif kw == "BOUNDARY":
                    mode, ctx = "BOUNDARY", None
                else:
                    mode, ctx = None, None
                continue

            # ---- data lines ------------------------------------------------
            if mode == "NODE":
                t = _split(line)
                if len(t) >= 4:
                    nodes[int(t[0])] = (float(t[1]), float(t[2]), float(t[3]))
            elif mode == "ELEMENT":
                t = [x for x in _split(line) if x != ""]
                cont = line.rstrip().endswith(",")
                ctx["buf"].extend(t)
                if not cont:
                    vals = [int(x) for x in ctx["buf"]]
                    elements[vals[0]] = vals[1:]
                    ctx["buf"] = []
            elif mode in ("NSET", "ELSET"):
                store = nsets if mode == "NSET" else elsets
                t = [x for x in _split(line) if x != ""]
                if ctx["generate"]:
                    lo, hi = int(t[0]), int(t[1])
                    step = int(t[2]) if len(t) > 2 else 1
                    store[ctx["name"]].extend(range(lo, hi + 1, step))
                else:
                    for x in t:
                        try:
                            store[ctx["name"]].append(int(x))
                        except ValueError:      # a set of sets
                            store[ctx["name"]].append(x.upper())
            elif mode == "EQUATION":
                t = [x for x in _split(line) if x != ""]
                if ctx["nterm"] is None:
                    ctx["nterm"] = int(t[0])
                    continue
                # terms come in triples (set-or-node, dof, coefficient)
                for i in range(0, len(t) - 2, 3):
                    ref = t[i].upper()
                    ctx["terms"].append((ref, int(t[i + 1]), float(t[i + 2])))
            elif mode == "BOUNDARY":
                t = [x for x in _split(line) if x != ""]
                if len(t) >= 2:
                    try:
                        dof1 = int(t[1])
                    except ValueError:
                        continue            # named BC type (ENCASTRE etc.)
                    dof2 = int(t[2]) if len(t) > 2 else dof1
                    mag = float(t[3]) if len(t) > 3 else 0.0
                    boundaries.append((t[0].upper(), dof1, dof2, mag))

    return {"nodes": nodes, "elements": elements, "nsets": nsets,
            "elsets": elsets, "equations": equations, "boundaries": boundaries}


def resolve(deck, ref):
    """A term reference is either a node set name or a bare node number."""
    if ref in deck["nsets"]:
        return list(deck["nsets"][ref])
    try:
        return [int(ref)]
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
#  report plumbing
# --------------------------------------------------------------------------- #

class Report(object):
    def __init__(self):
        self.sections = []
        self.failures = 0
        self.warnings = 0

    def section(self, title):
        print("")
        print("=" * 78)
        print(title)
        print("=" * 78)
        self.sections.append({"title": title, "checks": []})

    def _log(self, tag, msg, detail):
        print("  [%s] %s" % (tag, msg))
        if tag != "PASS":                       # detail explains a problem only
            for d in (detail or [])[:12]:
                print("         %s" % d)
            if detail and len(detail) > 12:
                print("         ... (%d more)" % (len(detail) - 12))
        if self.sections:
            self.sections[-1]["checks"].append(
                {"status": tag, "message": msg,
                 "detail": (detail or []) if tag != "PASS" else []})

    def ok(self, msg, detail=None):
        self._log("PASS", msg, None)

    def fail(self, msg, detail=None):
        self.failures += 1
        self._log("FAIL", msg, detail)

    def warn(self, msg, detail=None):
        self.warnings += 1
        self._log("WARN", msg, detail)

    def info(self, msg):
        print("       %s" % msg)

    def check(self, cond, msg, detail=None):
        (self.ok if cond else self.fail)(msg, detail)
        return cond


# --------------------------------------------------------------------------- #
#  checks
# --------------------------------------------------------------------------- #

def check_mesh(deck, rep):
    rep.section("1. MESH AND LATTICE")
    nodes = deck["nodes"]
    used = set()
    for conn in deck["elements"].values():
        used.update(conn)
    mesh_nodes = {n: xyz for n, xyz in nodes.items() if n in used}
    if not mesh_nodes:
        rep.fail("no element-attached nodes found -- is this an Abaqus mesh file?")
        return None

    xs = [p[0] for p in mesh_nodes.values()]
    ys = [p[1] for p in mesh_nodes.values()]
    zs = [p[2] for p in mesh_nodes.values()]
    box = {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys),
           "zmin": min(zs), "zmax": max(zs)}
    L = (box["xmax"] - box["xmin"], box["ymax"] - box["ymin"],
         box["zmax"] - box["zmin"])

    rep.info("nodes = %d (%d attached to elements), elements = %d"
             % (len(nodes), len(mesh_nodes), len(deck["elements"])))
    rep.info("bounding box  x[%.6f, %.6f]  y[%.6f, %.6f]  z[%.6f, %.6f]"
             % (box["xmin"], box["xmax"], box["ymin"], box["ymax"],
                box["zmin"], box["zmax"]))
    rep.info("lattice       Lx=%.6f  Ly=%.6f  Lz=%.6f  mm" % L)
    rep.info("V_RVE (bounding box) = %.6f mm^3" % (L[0] * L[1] * L[2]))

    missing = [n for n in DRIVER_NAMES if n not in deck["nsets"]]
    rep.check(not missing, "all six ConstraintsDriver node sets present",
              ["missing: %s" % m for m in missing])

    drv_nodes = set()
    for n in DRIVER_NAMES:
        drv_nodes.update(x for x in deck["nsets"].get(n, []) if isinstance(x, int))
    bad = sorted(drv_nodes & used)
    rep.check(not bad, "driver nodes carry no elements (they are pure DOF carriers)",
              ["node %d is in the mesh" % b for b in bad])

    return {"box": box, "L": L, "mesh_nodes": mesh_nodes, "used": used,
            "drivers": drv_nodes}


def check_volume_fractions(deck, geo, rep):
    """Phase volume fractions from the tet mesh itself.

    Cheap, and it catches two things the constraint audit cannot: a mesh that does
    not actually fill its own bounding box (so every macro stress divided by the
    box volume would be wrong), and a weave whose fibre content has drifted away
    from the paper's."""
    rep.section("7. RVE VOLUME FRACTIONS")
    nodes = deck["nodes"]

    def tet_volume(conn):
        try:
            a, b, c, d = [nodes[i] for i in conn[:4]]
        except KeyError:
            return None
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        w = [d[i] - a[i] for i in range(3)]
        cr = [v[1] * w[2] - v[2] * w[1],
              v[2] * w[0] - v[0] * w[2],
              v[0] * w[1] - v[1] * w[0]]
        return abs(sum(u[i] * cr[i] for i in range(3))) / 6.0

    vols, total, degenerate = {}, 0.0, 0
    for eid, conn in deck["elements"].items():
        if len(conn) != 4:
            rep.warn("mesh is not all 4-node tets -- volume fractions skipped")
            return None
        v = tet_volume(conn)
        if v is None:
            continue
        if v <= 0.0:
            degenerate += 1
        vols[eid] = v
        total += v
    if total <= 0.0:
        rep.warn("could not integrate the mesh volume")
        return None

    box = geo["L"][0] * geo["L"][1] * geo["L"][2]
    rep.info("mesh volume = %.6f mm^3, bounding box = %.6f mm^3" % (total, box))
    rep.check(abs(total / box - 1.0) < 1e-3,
              "mesh fills its bounding box, so V_box is the homogenisation volume",
              ["fill = %.4f %% -- macro stress from RF/V_box would be wrong by "
               "that factor" % (100.0 * total / box)])
    rep.check(degenerate == 0, "no degenerate (zero-volume) elements",
              ["%d element(s) have non-positive volume" % degenerate])

    per = {}
    for name, members in deck["elsets"].items():
        if name == "ALL":
            continue
        per[name] = sum(vols.get(e, 0.0) for e in members if isinstance(e, int))
    yarn = sum(v for k, v in per.items() if k.startswith("YARN"))
    for name in sorted(per):
        rep.info("  %-10s %10.6f mm^3   %6.2f %%"
                 % (name, per[name], 100.0 * per[name] / total))
    if yarn > 0:
        rep.info("yarn total %.2f %%, matrix %.2f %% of the cell"
                 % (100.0 * yarn / total, 100.0 * (total - yarn) / total))
        rep.info("overall fibre Vf = yarn fraction x Vf_in_yarn(0.792) = %.4f"
                 % (yarn / total * 0.792))
    return {"total": total, "box": box, "per_elset": per, "yarn_fraction": yarn / total}


def equation_pairs(deck):
    """Group equations by (slave set, master set).  Returns
    {(slave, master): [(dof, {driver_index: coefficient}), ...]}."""
    groups = OrderedDict()
    for eq in deck["equations"]:
        terms = eq["terms"]
        if len(terms) < 2:
            continue
        slave, sdof, scoef = terms[0]
        master, mdof, mcoef = terms[1]
        drivers = {}
        for ref, dof, coef in terms[2:]:
            if ref in DRIVER_NAMES:
                drivers[DRIVER_NAMES.index(ref)] = coef
            else:
                drivers.setdefault("OTHER", []).append((ref, dof, coef))
        groups.setdefault((slave, master), []).append(
            {"dof": sdof, "sdof": sdof, "mdof": mdof, "scoef": scoef,
             "mcoef": mcoef, "drivers": drivers, "nterm": eq["nterm"],
             "raw": terms})
    return groups


def check_pairing(deck, geo, rep, tol):
    rep.section("2. SET PAIRING  (slave[k] must be master[k] + one lattice vector)")
    nodes = deck["nodes"]
    offsets = {}
    for (slave, master) in equation_pairs(deck):
        sn, mn = resolve(deck, slave), resolve(deck, master)
        if sn is None or mn is None:
            rep.fail("equation references unknown set(s): %s / %s" % (slave, master))
            continue
        if len(sn) != len(mn):
            rep.fail("%s (%d nodes) and %s (%d nodes) differ in size -- Abaqus "
                     "pairs by position, so the deck is wrong"
                     % (slave, len(sn), master, len(mn)))
            continue

        d0 = None
        bad = []
        for k, (a, b) in enumerate(zip(sn, mn)):
            if a not in nodes or b not in nodes:
                bad.append("index %d: node %s or %s undefined" % (k, a, b))
                continue
            d = tuple(nodes[a][i] - nodes[b][i] for i in range(3))
            if d0 is None:
                d0 = d
            elif max(abs(d[i] - d0[i]) for i in range(3)) > tol:
                bad.append("index %d: node %d - node %d = (%.6g, %.6g, %.6g), "
                           "expected (%.6g, %.6g, %.6g)"
                           % (k, a, b, d[0], d[1], d[2], d0[0], d0[1], d0[2]))
        offsets[(slave, master)] = d0
        rep.check(not bad,
                  "%-12s <- %-12s : %4d node pairs, offset (%.4f, %.4f, %.4f)"
                  % (slave, master, len(sn), d0[0], d0[1], d0[2]),
                  bad)

    # the offsets must be integer combinations of the lattice vectors
    Lx, Ly, Lz = geo["L"]
    bad = []
    for key, d in offsets.items():
        if d is None:
            continue
        for comp, Lc, name in ((d[0], Lx, "x"), (d[1], Ly, "y"), (d[2], Lz, "z")):
            n = comp / Lc if Lc else 0.0
            if abs(n - round(n)) > 1e-3:
                bad.append("%s <- %s: %s-offset %.6f is not a multiple of L%s=%.6f"
                           % (key[0], key[1], name, comp, name, Lc))
    rep.check(not bad, "every pair offset is a lattice translation", bad)
    return offsets


def check_equations(deck, geo, offsets, rep, tol):
    rep.section("3. EQUATION COEFFICIENTS  (re-derived from the measured offsets)")
    groups = equation_pairs(deck)
    bad = []
    n_eq = 0
    for (slave, master), eqs in groups.items():
        d = offsets.get((slave, master))
        if d is None:
            continue
        seen_dofs = set()
        for eq in eqs:
            n_eq += 1
            dof = eq["dof"]
            tag = "%s <- %s dof %d" % (slave, master, dof)
            seen_dofs.add(dof)

            if abs(eq["scoef"] - 1.0) > 1e-12 or abs(eq["mcoef"] + 1.0) > 1e-12:
                bad.append("%s: slave/master coefficients are (%g, %g), expected "
                           "(+1, -1)" % (tag, eq["scoef"], eq["mcoef"]))
            if eq["mdof"] != dof:
                bad.append("%s: master DOF is %d, must match the slave DOF"
                           % (tag, eq["mdof"]))
            if "OTHER" in eq["drivers"]:
                bad.append("%s: unexpected non-driver term(s) %s"
                           % (tag, eq["drivers"]["OTHER"]))

            # expected: u_s - u_m = sum_col H[dof-1][col] * d[col]
            expect = {}
            for col in range(3):
                di = H_DRIVER[dof - 1][col]
                if di is None:
                    continue
                if abs(d[col]) > tol:
                    expect[di] = expect.get(di, 0.0) - d[col]   # moved to the LHS
            actual = {k: v for k, v in eq["drivers"].items() if k != "OTHER"}

            for di in sorted(set(list(expect) + list(actual))):
                e = expect.get(di, 0.0)
                a = actual.get(di, 0.0)
                if abs(e - a) > max(tol, 1e-9 * max(1.0, abs(e))):
                    if di not in actual:
                        bad.append("%s: MISSING %s term, expected coefficient %.6f"
                                   % (tag, DRIVER_LABEL[di], e))
                    elif di not in expect:
                        bad.append("%s: SPURIOUS %s term with coefficient %.6f"
                                   % (tag, DRIVER_LABEL[di], a))
                    else:
                        bad.append("%s: %s coefficient is %.6f, geometry demands "
                                   "%.6f" % (tag, DRIVER_LABEL[di], a, e))
        for dof in (1, 2, 3):
            if dof not in seen_dofs:
                bad.append("%s <- %s: no equation for dof %d -- that direction is "
                           "left unconstrained" % (slave, master, dof))

    rep.check(not bad, "all %d equations agree with the geometry and the TexGen "
                       "driver convention" % n_eq, bad)

    # Which macro strains are actually reachable?
    reachable = set()
    for eqs in groups.values():
        for eq in eqs:
            reachable.update(k for k in eq["drivers"] if k != "OTHER")
    missing = [DRIVER_LABEL[i] for i in range(6) if i not in reachable]
    rep.check(not missing,
              "all six macro strain components are driven by some equation",
              ["%s never appears -> that load case cannot be applied" % m
               for m in missing])
    return n_eq


def check_elimination(deck, rep):
    rep.section("4. DOF ELIMINATION AND OVERCONSTRAINT")
    first = defaultdict(list)      # (node, dof) -> [equation index]
    for i, eq in enumerate(deck["equations"]):
        if not eq["terms"]:
            continue
        ref, dof, _ = eq["terms"][0]
        for n in (resolve(deck, ref) or []):
            first[(n, dof)].append((i, ref))

    dupes = {k: v for k, v in first.items() if len(v) > 1}
    rep.check(not dupes,
              "each eliminated DOF is the leading term of exactly one equation",
              ["node %d dof %d is eliminated by equations %s"
               % (k[0], k[1], [x[0] for x in v]) for k, v in sorted(dupes.items())])

    # a BC on an eliminated DOF is an overconstraint
    bc_dofs = set()
    for ref, d1, d2, _ in deck["boundaries"]:
        for n in (resolve(deck, ref) or []):
            for d in range(d1, d2 + 1):
                bc_dofs.add((n, d))
    clash = sorted(set(first) & bc_dofs)
    rep.check(not clash,
              "no *Boundary lands on a DOF that an equation already eliminates",
              ["node %d dof %d" % c for c in clash])
    return first, bc_dofs


def check_coverage(deck, geo, rep, tol):
    rep.section("5. SURFACE COVERAGE  (every boundary node constrained exactly once)")
    box, L = geo["box"], geo["L"]
    mesh_nodes = geo["mesh_nodes"]

    # classify by how many bounding-box planes a node touches
    surface = {}
    for n, p in mesh_nodes.items():
        hits = 0
        for v, lo, hi in ((p[0], box["xmin"], box["xmax"]),
                          (p[1], box["ymin"], box["ymax"]),
                          (p[2], box["zmin"], box["zmax"])):
            if abs(v - lo) <= tol or abs(v - hi) <= tol:
                hits += 1
        if hits:
            surface[n] = hits

    constrained = defaultdict(list)
    for name, members in deck["nsets"].items():
        if not (name.startswith("FACE") or name.startswith("EDGE")
                or name.startswith("MASTERNODE")):
            continue
        for m in members:
            if isinstance(m, int):
                constrained[m].append(name)

    rep.info("surface nodes: %d faces-only, %d on edges, %d at corners (total %d)"
             % (sum(1 for h in surface.values() if h == 1),
                sum(1 for h in surface.values() if h == 2),
                sum(1 for h in surface.values() if h == 3), len(surface)))
    rep.info("nodes named by Face*/Edge*/MasterNode* sets: %d" % len(constrained))

    uncovered = sorted(set(surface) - set(constrained))
    rep.check(not uncovered,
              "every node on the RVE surface belongs to a PBC set",
              ["node %d at (%.5f, %.5f, %.5f) -- free surface, not periodic"
               % (n, mesh_nodes[n][0], mesh_nodes[n][1], mesh_nodes[n][2])
               for n in uncovered])

    doubles = {n: s for n, s in constrained.items() if len(s) > 1}
    rep.check(not doubles,
              "no node is claimed by two different PBC sets",
              ["node %d in %s" % (n, ", ".join(s)) for n, s in sorted(doubles.items())])

    interior = sorted(n for n in constrained
                      if n in mesh_nodes and n not in surface)
    rep.check(not interior,
              "no interior node is dragged into a PBC set",
              ["node %d at (%.5f, %.5f, %.5f)"
               % (n, mesh_nodes[n][0], mesh_nodes[n][1], mesh_nodes[n][2])
               for n in interior])

    # A periodic mesh must have mirror-image node counts on opposite faces.
    for axis, name in ((0, "x"), (1, "y"), (2, "z")):
        lo = [n for n, p in mesh_nodes.items()
              if abs(p[axis] - box[name + "min"]) <= tol]
        hi = [n for n, p in mesh_nodes.items()
              if abs(p[axis] - box[name + "max"]) <= tol]
        rep.check(len(lo) == len(hi),
                  "%s- and %s+ surfaces hold the same number of nodes (%d)"
                  % (name, name, len(lo)),
                  ["%s-=%d, %s+=%d -> the mesh itself is not periodic; regenerate "
                   "it in TexGen with periodic meshing on"
                   % (name, len(lo), name, len(hi))])
    return surface, constrained


def check_rigid_body(deck, geo, rep):
    rep.section("6. RIGID-BODY SUPPRESSION")
    pinned = defaultdict(set)
    for ref, d1, d2, mag in deck["boundaries"]:
        if abs(mag) > 0:
            continue
        for n in (resolve(deck, ref) or []):
            for d in range(d1, min(d2, 3) + 1):
                pinned[n].add(d)
    full = [n for n, dofs in pinned.items() if {1, 2, 3} <= dofs]
    rep.check(len(full) >= 1,
              "a reference corner is pinned in all three translations (nodes %s)"
              % full,
              ["nothing is fully pinned -> the global stiffness matrix is singular "
               "and Abaqus will report numerical singularity on 3 DOF"])
    if len(full) > 1:
        rep.warn("more than one node is fully pinned (%s) -- that over-restrains "
                 "the cell unless they are the same physical point" % full)
    return full


# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp", help="Abaqus input deck exported by TexGen")
    ap.add_argument("--tol", type=float, default=1e-5,
                    help="geometric tolerance in mm (default 1e-5)")
    ap.add_argument("--json", default=None, help="also write the report as JSON")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.inp):
        print("error: %s not found" % args.inp)
        return 2

    print("PBC AUDIT  ->  %s" % args.inp)
    deck = parse_inp(args.inp)

    rep = Report()
    geo = check_mesh(deck, rep)
    if geo is None:
        return 1
    offsets = check_pairing(deck, geo, rep, args.tol)
    check_equations(deck, geo, offsets, rep, args.tol)
    check_elimination(deck, rep)
    check_coverage(deck, geo, rep, args.tol)
    check_rigid_body(deck, geo, rep)
    vf = check_volume_fractions(deck, geo, rep)

    print("")
    print("=" * 78)
    if rep.failures == 0:
        print("RESULT: PBC DEFINITION IS CONSISTENT  (%d warning(s))" % rep.warnings)
        print("        -> the constraint set is sound; run the Abaqus patch test")
        print("           (abaqus/make_pbc_check.py) to confirm it numerically.")
    else:
        print("RESULT: %d CHECK(S) FAILED  (%d warning(s))" % (rep.failures, rep.warnings))
    print("=" * 78)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"input": args.inp,
                       "lattice": {"Lx": geo["L"][0], "Ly": geo["L"][1],
                                   "Lz": geo["L"][2],
                                   "V": geo["L"][0] * geo["L"][1] * geo["L"][2]},
                       "volume_fractions": vf,
                       "failures": rep.failures, "warnings": rep.warnings,
                       "sections": rep.sections}, fh, indent=2)
        print("wrote %s" % args.json)

    return 0 if rep.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
