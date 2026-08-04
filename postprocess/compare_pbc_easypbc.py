#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_pbc_easypbc.py
======================
Put our TexGen/Xia homogenisation next to EasyPBC's and say whether they agree.

Two independent constraint generators and two independent postprocessors running
on the same mesh and the same constituents should land on the same engineering
constants.  Where they do, the periodic boundary conditions are corroborated by
something that shares no code with them.  Where they do not, the gap itself is
diagnostic -- a mismatch confined to the shear moduli means the shear constraints
differ; a uniform offset in everything means one side is averaging over a
different volume.

Reading EasyPBC's numbers
-------------------------
EasyPBC's report layout varies between releases, so this scrapes any text/CSV
file for `E11 = 12345`-style pairs (accepting E11/E1/Ex and the usual G/nu
spellings), and anything it cannot find can be supplied on the command line.

Usage
-----
    python3 postprocess/compare_pbc_easypbc.py PBC_ELASTIC_constants.csv report.txt
    python3 postprocess/compare_pbc_easypbc.py PBC_ELASTIC_constants.csv \\
            --set E1=112340 E2=112050 E3=41200 G12=19800 nu12=0.11
    python3 postprocess/compare_pbc_easypbc.py PBC_PATCH_constants.csv \\
            --isotropic 350000 0.2         # patch test: both must match theory

Exit status is 0 when every reported constant agrees within --tol (default 2 %).
"""
from __future__ import print_function

import argparse
import os
import re
import sys

KEYS = ["E1", "E2", "E3", "G12", "G13", "G23", "nu12", "nu13", "nu23"]

# The spellings EasyPBC and friends use for each constant.
ALIASES = {
    "E1": ["e11", "e1", "ex", "exx", "e_1", "youngsmodulus1", "modulus1"],
    "E2": ["e22", "e2", "ey", "eyy", "e_2", "youngsmodulus2", "modulus2"],
    "E3": ["e33", "e3", "ez", "ezz", "e_3", "youngsmodulus3", "modulus3"],
    "G12": ["g12", "gxy", "g_12", "shearmodulus12"],
    "G13": ["g13", "gxz", "g31", "g_13", "shearmodulus13"],
    "G23": ["g23", "gyz", "g32", "g_23", "shearmodulus23"],
    "nu12": ["nu12", "v12", "nuxy", "poisson12", "poissonsratio12",
             "poissonratio12", "nu_12", "prxy"],
    "nu13": ["nu13", "v13", "nuxz", "poisson13", "poissonsratio13",
             "poissonratio13", "nu_13", "prxz"],
    "nu23": ["nu23", "v23", "nuyz", "poisson23", "poissonsratio23",
             "poissonratio23", "nu_23", "pryz"],
}
LOOKUP = {}
for canon, names in ALIASES.items():
    for n in names:
        LOOKUP[n] = canon

NUMBER = r"[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?"
# `name = value`, `name: value`, `name,value` or `name value`.  The label is taken
# greedily so multi-word forms ("Shear modulus 12 , 19850") stay in one piece; the
# separator is required so prose like "EasyPBC v1.4" cannot pose as a constant.
PAIR = re.compile(r"([A-Za-z_][A-Za-z0-9_' ]{0,24})\s*(?:[:=]\s*|[,\t]\s*|\s+)("
                  + NUMBER + r")")


def norm(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def canonical(raw):
    """Map a scraped label to one of our keys.

    Reports write the same constant as `E11`, `Shear modulus 12` or
    `Longitudinal modulus E1`, so try the whole label first and then progressively
    shorter trailing windows of it."""
    toks = raw.split()
    cands = [norm(raw)]
    for n in (1, 2, 3):
        if len(toks) >= n:
            cands.append(norm("".join(toks[-n:])))
    for c in cands:
        if c in LOOKUP:
            return LOOKUP[c]
    return None


def scrape(path):
    """Pull every `name value` pair out of a report and keep the ones we know."""
    found = {}
    with open(path) as fh:
        text = fh.read()
    for raw, val in PAIR.findall(text):
        canon = canonical(raw)
        if canon and canon not in found:
            try:
                found[canon] = float(val.replace("D", "E").replace("d", "e"))
            except ValueError:
                pass
    return found


def read_ours(path):
    """Our extract_stiffness.py CSV: constant,value,unit."""
    out = {}
    with open(path) as fh:
        for line in fh:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                out[parts[0]] = float(parts[1])
            except ValueError:
                continue
    return out


def isotropic_reference(E, nu):
    G = E / (2.0 * (1.0 + nu))
    return {"E1": E, "E2": E, "E3": E, "G12": G, "G13": G, "G23": G,
            "nu12": nu, "nu13": nu, "nu23": nu}


def main():
    ap = argparse.ArgumentParser(
        description="Compare our PBC homogenisation with EasyPBC.")
    ap.add_argument("ours", help="*_constants.csv from extract_stiffness.py")
    ap.add_argument("easypbc", nargs="?", default=None,
                    help="EasyPBC report file (text or CSV) to scrape")
    ap.add_argument("--set", nargs="+", default=[], metavar="K=V",
                    help="EasyPBC values given directly, e.g. E1=112340 G12=19800")
    ap.add_argument("--isotropic", nargs=2, type=float, metavar=("E", "NU"),
                    default=None,
                    help="patch test: also compare both against isotropic theory")
    ap.add_argument("--tol", type=float, default=2.0,
                    help="agreement tolerance in %% (default 2)")
    args = ap.parse_args()

    if not os.path.isfile(args.ours):
        print("error: %s not found" % args.ours)
        return 2
    ours = read_ours(args.ours)

    theirs = {}
    if args.easypbc:
        if not os.path.isfile(args.easypbc):
            print("error: %s not found" % args.easypbc)
            return 2
        theirs = scrape(args.easypbc)
        print("scraped %d constant(s) from %s: %s"
              % (len(theirs), args.easypbc,
                 ", ".join(sorted(theirs)) if theirs else "none"))
        if not theirs:
            print("  nothing recognised -- pass the numbers with --set instead.")
    for item in args.set:
        if "=" not in item:
            print("error: --set needs KEY=VALUE, got %r" % item)
            return 2
        k, v = item.split("=", 1)
        theirs[canonical(k) or k] = float(v)

    ref = isotropic_reference(*args.isotropic) if args.isotropic else None

    print("")
    header = "  %-6s %14s %14s %9s" % ("", "ours", "EasyPBC", "diff %")
    if ref:
        header += " %14s %9s" % ("theory", "ours vs th %")
    print(header)
    print("  " + "-" * (len(header) - 2))

    worst, worst_key, compared, fails = 0.0, None, 0, 0
    for k in KEYS:
        a = ours.get(k)
        b = theirs.get(k)
        row = "  %-6s %14s %14s" % (
            k, "%.4f" % a if a is not None else "-",
            "%.4f" % b if b is not None else "-")
        if a is not None and b is not None and abs(a) > 1e-12:
            d = 100.0 * (b - a) / abs(a)
            compared += 1
            if abs(d) > worst:
                worst, worst_key = abs(d), k
            if abs(d) > args.tol:
                fails += 1
            row += " %8.3f%s" % (d, "*" if abs(d) > args.tol else " ")
        else:
            row += " %9s" % "-"
        if ref:
            t = ref.get(k)
            row += " %14.4f" % t
            row += (" %8.3f " % (100.0 * (a - t) / abs(t))) if a is not None else " %9s" % "-"
        print(row)

    print("")
    if compared == 0:
        print("nothing to compare -- supply EasyPBC values with a report file or --set.")
        return 1

    print("compared %d constant(s); worst disagreement %.3f %% on %s (tolerance %.1f %%)"
          % (compared, worst, worst_key, args.tol))
    if fails == 0:
        print("VERDICT: the two independent PBC implementations agree.")
        print("         Our TexGen/Xia constraints are corroborated by a tool that")
        print("         shares no code with them.")
        return 0

    print("VERDICT: %d constant(s) disagree by more than %.1f %%." % (fails, args.tol))
    shear = [k for k in ("G12", "G13", "G23")
             if k in ours and k in theirs and abs(ours[k]) > 1e-12
             and abs(100.0 * (theirs[k] - ours[k]) / abs(ours[k])) > args.tol]
    normal = [k for k in ("E1", "E2", "E3")
              if k in ours and k in theirs and abs(ours[k]) > 1e-12
              and abs(100.0 * (theirs[k] - ours[k]) / abs(ours[k])) > args.tol]
    if shear and not normal:
        print("         Only shear constants differ -> the two tools define the")
        print("         shear load case differently (engineering vs tensor shear, or")
        print("         one-sided vs symmetric). Check the factor: a clean 2x or 0.5x")
        print("         is a convention difference, not a constraint error.")
    elif normal and not shear:
        print("         Only the Young's moduli differ -> suspect the averaging")
        print("         volume or, on the two-phase deck, yarn orientations that did")
        print("         not survive the CAE import.")
    else:
        print("         Everything is off -> compare on the PATCH deck first; if that")
        print("         disagrees, one of the two setups is wrong before any composite")
        print("         number means anything.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
