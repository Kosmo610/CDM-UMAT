#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_pbc.py
=================
Fault injection for check_pbc.py.

A validator that never fails is worthless, so this takes a *known-good* deck,
breaks it in the specific ways a periodic-BC deck actually breaks in practice,
and asserts that the audit catches each one.  Every case below has bitten
someone: a stale lattice length after a mesh regeneration, an editor that
re-sorted a node set, a hand-pruned shear term, a lost corner pin.

Run:
    python3 verification/test_check_pbc.py [abaqus/ZHANG2022_RT23_V1_0.inp]
"""
from __future__ import print_function

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_pbc import (parse_inp, check_mesh, check_pairing, check_equations,   # noqa: E402
                       check_elimination, check_coverage, check_rigid_body,
                       Report)

DEFAULT_INP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "abaqus", "ZHANG2022_RT23_V1_0.inp")
TOL = 1e-5


class Quiet(object):
    """Swallow the audit's stdout -- only the verdict matters here."""

    def __enter__(self):
        self._old = sys.stdout
        sys.stdout = open(os.devnull, "w")
        return self

    def __exit__(self, *exc):
        sys.stdout.close()
        sys.stdout = self._old


def audit(deck):
    """Run the full audit on a parsed deck, return the failure count."""
    with Quiet():
        rep = Report()
        geo = check_mesh(deck, rep)
        if geo is None:
            return 99
        offsets = check_pairing(deck, geo, rep, TOL)
        check_equations(deck, geo, offsets, rep, TOL)
        check_elimination(deck, rep)
        check_coverage(deck, geo, rep, TOL)
        check_rigid_body(deck, geo, rep)
    return rep.failures


# --------------------------------------------------------------------------- #
#  fault injectors -- each returns a broken copy of the deck
# --------------------------------------------------------------------------- #

def fault_stale_lattice(deck):
    """Mesh was rebuilt at a different size but the equations kept the old Lx."""
    d = copy.deepcopy(deck)
    for eq in d["equations"]:
        for i, (ref, dof, coef) in enumerate(eq["terms"]):
            if ref == "CONSTRAINTSDRIVER0":
                eq["terms"][i] = (ref, dof, coef * 1.02)
    return d


def fault_unequal_face_sets(deck):
    """A node dropped out of one face set -- Abaqus pairs by position, so every
    pair after the hole is silently wrong."""
    d = copy.deepcopy(deck)
    d["nsets"]["FACEA"] = d["nsets"]["FACEA"][:-1]
    return d


def fault_scrambled_face_set(deck):
    """Set membership is right but the order is not.  Abaqus pairs *Equation set
    members by position, so this silently glues the wrong nodes together -- the
    reason TexGen writes these sets with the Unsorted flag."""
    d = copy.deepcopy(deck)
    s = list(d["nsets"]["FACEB"])
    s[0], s[-1] = s[-1], s[0]
    d["nsets"]["FACEB"] = s
    return d


def fault_missing_shear_term(deck):
    """The e_xy driver term deleted from the FaceC/FaceD dof-1 equation."""
    d = copy.deepcopy(deck)
    for eq in d["equations"]:
        t = eq["terms"]
        if t and t[0][0] == "FACEC" and t[0][1] == 1:
            eq["terms"] = [x for x in t if x[0] != "CONSTRAINTSDRIVER3"]
            eq["nterm"] = len(eq["terms"])
    return d


def fault_sign_flip(deck):
    """Driver coefficient sign flipped -- applies the opposite macro strain."""
    d = copy.deepcopy(deck)
    for eq in d["equations"]:
        t = eq["terms"]
        if t and t[0][0] == "FACEE" and t[0][1] == 3:
            eq["terms"] = [(r, f, -c) if r == "CONSTRAINTSDRIVER2" else (r, f, c)
                           for (r, f, c) in t]
    return d


def fault_double_elimination(deck):
    """The same DOF eliminated twice -> Abaqus overconstraint abort."""
    d = copy.deepcopy(deck)
    src = None
    for eq in d["equations"]:
        if eq["terms"] and eq["terms"][0][0] == "FACEA" and eq["terms"][0][1] == 2:
            src = eq
            break
    d["equations"].append(copy.deepcopy(src))
    return d


def fault_bc_on_eliminated_dof(deck):
    """A *Boundary put on a face that an equation already eliminates."""
    d = copy.deepcopy(deck)
    d["boundaries"].append(("FACEA", 1, 1, 0.0))
    return d


def fault_no_rigid_body_pin(deck):
    """Corner pin removed -> singular stiffness matrix."""
    d = copy.deepcopy(deck)
    d["boundaries"] = []
    return d


def fault_uncovered_surface_node(deck):
    """A surface node left out of every PBC set -> a free (non-periodic) patch."""
    d = copy.deepcopy(deck)
    d["nsets"]["FACEE"] = d["nsets"]["FACEE"][:-1]
    d["nsets"]["FACEF"] = d["nsets"]["FACEF"][:-1]
    return d


def fault_driver_in_mesh(deck):
    """A driver node number that collides with a real mesh node."""
    d = copy.deepcopy(deck)
    d["nsets"]["CONSTRAINTSDRIVER0"] = [1]
    return d


def fault_nonperiodic_mesh(deck):
    """Opposite surfaces carry different node counts -- the mesh was generated
    without periodic meshing enabled."""
    d = copy.deepcopy(deck)
    nodes = d["nodes"]
    xmax = max(p[0] for p in nodes.values())
    victim = next(n for n, p in nodes.items()
                  if abs(p[0] - xmax) < 1e-9 and n in d["nsets"]["FACEA"])
    x, y, z = nodes[victim]
    nodes[victim] = (x - 0.01, y, z)          # pull it off the +x plane
    return d


CASES = [
    ("stale lattice length in the equations", fault_stale_lattice),
    ("face sets of unequal length", fault_unequal_face_sets),
    ("two nodes swapped in a face set", fault_scrambled_face_set),
    ("e_xy driver term deleted", fault_missing_shear_term),
    ("driver coefficient sign flipped", fault_sign_flip),
    ("same DOF eliminated by two equations", fault_double_elimination),
    ("*Boundary on an eliminated DOF", fault_bc_on_eliminated_dof),
    ("rigid-body pin removed", fault_no_rigid_body_pin),
    ("surface node left out of every PBC set", fault_uncovered_surface_node),
    ("driver node collides with a mesh node", fault_driver_in_mesh),
    ("mesh not periodic across x", fault_nonperiodic_mesh),
]


def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INP
    if not os.path.isfile(inp):
        print("error: %s not found" % inp)
        return 2
    print("fault injection against %s" % os.path.relpath(inp))
    print("")

    deck = parse_inp(inp)

    base = audit(deck)
    ok = (base == 0)
    print("  [%s] baseline deck audits clean (%d failures)"
          % ("PASS" if ok else "FAIL", base))
    if not ok:
        print("\n  cannot fault-inject against a deck that is already broken.")
        return 1

    bad = 0
    for name, injector in CASES:
        n = audit(injector(deck))
        caught = n > 0
        bad += 0 if caught else 1
        print("  [%s] caught: %-42s (%d failure(s) raised)"
              % ("PASS" if caught else "FAIL", name, n))

    print("")
    if bad == 0:
        print("ALL %d FAULTS DETECTED -- the audit has teeth." % len(CASES))
        return 0
    print("%d FAULT(S) SLIPPED THROUGH -- check_pbc.py has a blind spot." % bad)
    return 1


if __name__ == "__main__":
    sys.exit(main())
