#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
msg_residual_census.py -- where is the solver actually stuck?

RUN WITH PLAIN PYTHON (it reads .msg and .inp, never the odb):

    python msg_residual_census.py <job.msg> <deck.inp>
    python msg_residual_census.py --check

WHY THIS EXISTS
---------------
A job that dies with "TOO MANY ATTEMPTS MADE FOR THIS INCREMENT" tells you
nothing by itself.  The .msg does say which NODE carried the largest residual
at every iteration, and the deck says which ElSet every node belongs to, so
the two together say which PHASE the solver is fighting.  That turns a bare
failure into a diagnosis.

It has already been wrong once in this project and the lesson is baked in
here: in M3 the nodes 5681-5686 were read as mesh nodes and the conclusion
"the through-thickness direction is the problem" was drawn from it.  They are
the periodic-BC DUMMY DRIVERS, and their "DOF 1" is a macro strain component,
not a global direction.  This script knows the difference and reports drivers
as their own category, by name.

WHAT THE TWO CATEGORIES MEAN
----------------------------
  * A residual on a MACRO DRIVER is a macro stress error: R = sigma * V_RVE,
    so divide by V_RVE to judge it.  On a traction-free driver it is the
    error in "this stress component is zero".
  * A residual on a MESH NODE is a genuine local force imbalance and the
    R/V conversion does NOT apply to it.  Reporting one as the other is the
    mistake this file exists to prevent.
"""
from __future__ import print_function

import os
import re
import sys
from collections import Counter

#: RVE bounding-box volume [mm^3].  Only ever applied to DRIVER residuals.
V_RVE = 5.390

#: Periodic-BC dummy drivers, in the order assemble_inp.py writes them.
DRIVER_NAMES = {0: "eps_xx", 1: "eps_yy", 2: "eps_zz",
                3: "eps_xy", 4: "eps_xz", 5: "eps_yz"}

RES_RE = re.compile(
    r"LARGEST RESIDUAL FORCE\s+([0-9.E+-]+)\s+AT NODE\s+(\d+)\s+DOF\s+(\d+)")


def parse_deck(path):
    """(node -> [elset, ...], driver node -> label) from an assembled deck."""
    text = open(path, errors="replace").read() if sys.version_info[0] >= 3 \
        else open(path).read()

    m = re.search(r"\*Element, Type=C3D4\n(.*?)(?=\n\*)", text, re.S)
    if not m:
        raise ValueError("no C3D4 element block in %s" % path)
    el2nodes = {}
    for ln in m.group(1).splitlines():
        p = [x.strip() for x in ln.split(",") if x.strip()]
        if len(p) == 5:
            el2nodes[int(p[0])] = [int(x) for x in p[1:]]

    sets = {}
    for mm in re.finditer(
            r"\*ElSet, ElSet=([A-Za-z0-9_]+)(, Generate)?\n(.*?)(?=\n\*)",
            text, re.S):
        name, gen, body = mm.group(1), mm.group(2), mm.group(3)
        ids = set()
        for ln in body.splitlines():
            p = [x.strip() for x in ln.split(",") if x.strip()]
            if gen and len(p) == 3:
                a, b, c = int(p[0]), int(p[1]), int(p[2])
                ids.update(range(a, b + 1, c))
            else:
                for x in p:
                    if x.isdigit():
                        ids.add(int(x))
        sets.setdefault(name, set()).update(ids)

    el2set = {}
    for name, ids in sets.items():
        if name.lower() == "all":          # the catch-all is not a phase
            continue
        for e in ids:
            el2set[e] = name
    node2sets = {}
    for e, ns in el2nodes.items():
        s = el2set.get(e)
        if s is None:
            continue
        for n in ns:
            node2sets.setdefault(n, set()).add(s)

    drivers = {}
    for mm in re.finditer(
            r"\*NSet, NSet=ConstraintsDriver(\d+)\s*\n\s*(\d+)", text):
        k, node = int(mm.group(1)), int(mm.group(2))
        drivers[node] = "ConstraintsDriver%d (%s)" % (
            k, DRIVER_NAMES.get(k, "?"))
    return node2sets, drivers, sets


def yarn_axis(deck_path, sets):
    """{elset: 'axial'|'transverse'} from each yarn's own bounding box.

    Which yarns are transverse is a property of the MESH, so it is measured
    rather than assumed from the set name.  The load is along x.
    """
    text = open(deck_path, errors="replace").read() if sys.version_info[0] >= 3 \
        else open(deck_path).read()
    m = re.search(r"(?m)^\*Node\n(.*?)(?=\n\*)", text, re.S)
    coord = {}
    for ln in m.group(1).splitlines():
        p = [x.strip() for x in ln.split(",") if x.strip()]
        if len(p) == 4:
            coord[int(p[0])] = (float(p[1]), float(p[2]))
    me = re.search(r"\*Element, Type=C3D4\n(.*?)(?=\n\*)", text, re.S)
    el2nodes = {}
    for ln in me.group(1).splitlines():
        p = [x.strip() for x in ln.split(",") if x.strip()]
        if len(p) == 5:
            el2nodes[int(p[0])] = [int(x) for x in p[1:]]
    out = {}
    for name, ids in sets.items():
        if not name.lower().startswith("yarn"):
            continue
        ns = set()
        for e in ids:
            ns.update(el2nodes.get(e, []))
        xs = [coord[n][0] for n in ns if n in coord]
        ys = [coord[n][1] for n in ns if n in coord]
        if not xs:
            continue
        dx, dy = max(xs) - min(xs), max(ys) - min(ys)
        out[name] = "axial" if dx > dy else "transverse"
    return out


def classify(node, node2sets, axis):
    s = node2sets.get(node, set())
    trans = any(axis.get(x) == "transverse" for x in s)
    ax = any(axis.get(x) == "axial" for x in s)
    mx = any(x.lower() == "matrix" for x in s)
    if trans and ax:
        return "yarn/yarn crossover"
    if trans:
        return "TRANSVERSE yarn" + (" + matrix" if mx else " only")
    if ax:
        return "axial yarn" + (" + matrix" if mx else " only")
    if mx:
        return "matrix only"
    return "unclassified"


def census(msg_path, deck_path, window=400):
    node2sets, drivers, sets = parse_deck(deck_path)
    axis = yarn_axis(deck_path, sets)
    text = open(msg_path, errors="replace").read() if sys.version_info[0] >= 3 \
        else open(msg_path).read()
    rows = RES_RE.findall(text)
    if not rows:
        raise ValueError("no 'LARGEST RESIDUAL FORCE' lines in %s" % msg_path)
    tail = rows[-window:]

    cats, drv_mag, mesh_mag = Counter(), [], []
    drv_which = Counter()
    for mag, node, _dof in tail:
        n, v = int(node), abs(float(mag))
        if n in drivers:
            cats["MACRO DRIVER"] += 1
            drv_which[drivers[n]] += 1
            drv_mag.append(v)
        else:
            cats[classify(n, node2sets, axis)] += 1
            mesh_mag.append(v)
    return dict(total=len(rows), window=len(tail), cats=cats,
                drivers=drv_which, drv_mag=drv_mag, mesh_mag=mesh_mag,
                axis=axis)


def report(msg_path, deck_path, window=400):
    r = census(msg_path, deck_path, window)
    print("=" * 74)
    print("msg_residual_census.py  %s" % os.path.basename(msg_path))
    print("=" * 74)
    print("  %d residual reports; the last %d analysed" % (r["total"], r["window"]))
    print("  yarn axes measured from the mesh: %s"
          % ", ".join("%s=%s" % kv for kv in sorted(r["axis"].items())))

    print("\n  WHERE THE SOLVER IS STUCK")
    tot = sum(r["cats"].values())
    for k, v in r["cats"].most_common():
        print("    %-28s %4d  %5.1f %%" % (k, v, 100.0 * v / tot))
    trans = sum(v for k, v in r["cats"].items() if k.startswith("TRANSVERSE"))
    print("    -> transverse-yarn involvement %.1f %%" % (100.0 * trans / tot))

    if r["drivers"]:
        print("\n  WHICH DRIVERS (a driver residual IS a macro stress error)")
        for k, v in r["drivers"].most_common():
            print("    %-38s %4d" % (k, v))
        print("    worst driver residual %.3e N.mm = %.2e MPa of macro stress"
              % (max(r["drv_mag"]), max(r["drv_mag"]) / V_RVE))
    else:
        print("\n  no driver ever carried the largest residual in this window")

    if r["mesh_mag"]:
        m = sorted(r["mesh_mag"])
        print("\n  MESH-NODE residuals [N.mm] -- R/V does NOT apply to these")
        print("    median %.3e   max %.3e" % (m[len(m) // 2], m[-1]))
    out = write_csv(msg_path, r)
    print("\n  wrote %s -- UPLOAD THIS ONE" % os.path.basename(out))
    print("=" * 74)
    return 0


def write_csv(msg_path, r):
    """<job>_residuals.csv -- value, basis and verdict in the same row.

    Added 2026-08-12.  This file printed its census to the console only, which
    meant the one way to get the answer into a conversation was a screen
    capture -- and this project has lost three numbers to re-typing from
    images (the Snead sign, the Pradere unit, the refs/[28] page range).  The
    console stays; the CSV is the deliverable.
    """
    import csv as _csv
    out = os.path.splitext(msg_path)[0] + "_residuals.csv"
    tot = float(sum(r["cats"].values())) or 1.0
    trans = sum(v for k, v in r["cats"].items() if k.startswith("TRANSVERSE"))
    rows = []
    for k, v in r["cats"].most_common():
        rows.append(dict(kind="phase", label=k, count=v,
                         pct="%.2f" % (100.0 * v / tot), value="", basis="",
                         verdict=""))
    rows.append(dict(
        kind="summary", label="transverse-yarn involvement", count=trans,
        pct="%.2f" % (100.0 * trans / tot), value="", basis="41-57 % was the "
        "M5 signature that motivated turning the yarn crack band on",
        verdict="dominant" if trans > 0.4 * tot else "minor"))
    for k, v in r["drivers"].most_common():
        rows.append(dict(kind="driver", label=k, count=v, pct="", value="",
                         basis="", verdict=""))
    if r["drv_mag"]:
        w = max(r["drv_mag"])
        rows.append(dict(
            kind="summary", label="worst driver residual", count="",
            pct="", value="%.6e" % (w / V_RVE),
            basis="MPa of macro stress = R/V_RVE, V=%.4f mm^3" % V_RVE,
            verdict="negligible" if w / V_RVE < 1.0e-2 else "significant"))
    if r["mesh_mag"]:
        m = sorted(r["mesh_mag"])
        rows.append(dict(
            kind="summary", label="mesh-node residual median", count="",
            pct="", value="%.6e" % m[len(m) // 2],
            basis="N.mm; R/V does NOT apply to a mesh node", verdict=""))
        rows.append(dict(
            kind="summary", label="mesh-node residual max", count="", pct="",
            value="%.6e" % m[-1], basis="N.mm", verdict=""))
    cols = ["kind", "label", "count", "pct", "value", "basis", "verdict"]
    with open(out, "w") as fh:
        w = _csv.writer(fh)
        w.writerow(cols)
        for row in rows:
            w.writerow([row.get(c, "") for c in cols])
    return out


# ==========================================================================
_OK, _BAD = [], []


def ck(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-54s %s" % ("PASS" if cond else "FAIL", name, detail))


def selftest():
    """Builds a tiny deck and msg in memory, so the check needs no run."""
    import tempfile
    print("=" * 74)
    print("msg_residual_census.py --check")
    print("=" * 74)
    d = tempfile.mkdtemp()
    deck = os.path.join(d, "t.inp")
    msg = os.path.join(d, "t.msg")
    with open(deck, "w") as f:
        f.write("\n".join([
            "*Node",
            "1, 0., 0., 0.", "2, 1., 0., 0.", "3, 0., 1., 0.", "4, 0., 0., 1.",
            "5, 2., 0., 0.", "6, 0., 2., 0.",
            "7, 0., 0., 0.", "8, 0., 0., 0.", "9, 0., 0., 0.",
            "*Element, Type=C3D4",
            "1, 1, 5, 3, 4",        # dx=2 > dy=1 -> axial yarn
            "2, 1, 2, 6, 4",        # dy=2 > dx=1 -> transverse yarn
            "3, 1, 2, 5, 4",        # matrix
            "*ElSet, ElSet=Yarn0", "1",
            "*ElSet, ElSet=Yarn2", "2",
            "*ElSet, ElSet=Matrix", "3",
            "*ElSet, ElSet=All", "1, 2, 3",
            "*NSet, NSet=ConstraintsDriver0", "7",
            "*NSet, NSet=ConstraintsDriver3", "8",
            "*End",
        ]) + "\n")
    lines = []
    # node 5: elements 1 (Yarn0, axial) + 3 (Matrix)   -> axial yarn + matrix
    # node 6: element 2 (Yarn2, transverse) only         -> TRANSVERSE only
    # node 3: element 1 only                             -> axial yarn only
    for node in (5, 5, 5, 6, 6, 3, 7, 8):
        lines.append("   LARGEST RESIDUAL FORCE  1.000E-02 AT NODE %d DOF 1"
                     % node)
    with open(msg, "w") as f:
        f.write("\n".join(lines) + "\n")

    # The CSV is the deliverable (CLAUDE.md 3-2), so it is checked here and
    # not left to the first real run to discover.
    r = census(msg, deck)
    out = write_csv(msg, r)
    import csv as _csv
    got = list(_csv.DictReader(open(out)))
    ck("the census writes a CSV, not just a console log", bool(got),
       "%d rows -> %s" % (len(got), os.path.basename(out)))
    ck("  every row carries kind, label and a basis column",
       all(set(g) == {"kind", "label", "count", "pct", "value", "basis",
                      "verdict"} for got_ in [got] for g in got_))
    ck("  the transverse share appears as a summary row with its verdict",
       any(g["label"].startswith("transverse-yarn") and g["verdict"]
           for g in got))
    ck("  and a driver residual is reported in MPa, not in N.mm",
       any("MPa of macro stress" in g["basis"] for g in got))

    n2s, drv, sets = parse_deck(deck)
    ck("element sets parsed, 'All' excluded as a phase",
       set(sets) == {"Yarn0", "Yarn2", "Matrix", "All"}
       and "All" not in set().union(*n2s.values()),
       ", ".join(sorted(sets)))
    ck("drivers found and named by their macro strain component",
       drv == {7: "ConstraintsDriver0 (eps_xx)",
               8: "ConstraintsDriver3 (eps_xy)"}, str(sorted(drv)))
    axis = yarn_axis(deck, sets)
    ck("yarn axis measured from the mesh, not the name",
       axis == {"Yarn0": "axial", "Yarn2": "transverse"}, str(axis))

    r = census(msg, deck, window=100)
    ck("driver nodes are NOT counted as mesh nodes",
       r["cats"]["MACRO DRIVER"] == 2, str(dict(r["cats"])))
    ck("a node shared by matrix and an axial yarn is classified as such",
       r["cats"]["axial yarn + matrix"] == 3,
       "node 5 sits in elements 1 (Yarn0) and 3 (Matrix)")
    ck("a transverse-yarn node is flagged as transverse",
       r["cats"]["TRANSVERSE yarn only"] == 2, "node 6")
    ck("a pure axial-yarn node is not confused with a transverse one",
       r["cats"]["axial yarn only"] == 1, "node 3")
    ck("every report is classified, none dropped",
       sum(r["cats"].values()) == 8, str(sum(r["cats"].values())))
    ck("no report is 'unclassified'", r["cats"]["unclassified"] == 0)
    ck("driver and mesh magnitudes are kept apart",
       len(r["drv_mag"]) == 2 and len(r["mesh_mag"]) == 6)

    print("\n  the M3 lesson this file encodes")
    src = open(os.path.abspath(__file__)).read()
    for phrase, why in (
            ("They are\nthe periodic-BC DUMMY DRIVERS",
             "must name the M3 misreading"),
            ("R/V conversion does NOT apply",
             "must say the driver conversion is driver-only")):
        ck("source states: %s" % why, phrase in src)

    print("\n" + "=" * 74)
    if _BAD:
        print("FAIL -- %d of %d" % (len(_BAD), len(_OK) + len(_BAD)))
        print("=" * 74)
        return 1
    print("ALL %d RESIDUAL-CENSUS CHECKS PASS" % len(_OK))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(report(args[0], args[1]))
