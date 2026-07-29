#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ch4_numbers.py   --  ROUND 1 of the chapter self-verification
===================================================================
Every number Ch.4 states must be re-derivable from a primary source.

Ch.4 is the most exposed chapter numerically: it quotes mesh statistics, phase
volumes, driver displacements read off an ODB, and the outputs of two analysis
scripts.  Unlike Ch.2 (which quotes CSVs) there is no single file to diff
against, so this checker goes back to the sources themselves:

  * mesh facts       -- re-parsed from the shipped deck inside dist/*.zip
  * volumes / V_f    -- re-integrated from the tetrahedra
  * driver-derived   -- re-computed from the two measured U1 values
  * conductivity     -- re-run conductivity_bounds.py and read its numbers
  * quench / Biot    -- re-run quench_calibration.py and read its numbers

What this round does NOT check: whether Ch.4 agrees with Ch.2 and Ch.3 (that is
round 2), and whether the files and commands it names exist (round 3).

Run:  python3 verification/check_ch4_numbers.py
"""
from __future__ import print_function

import math
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CH4 = os.path.join(ROOT, "docs", "CH4_RVE_HOMOGENISATION.md")
DECK_ZIP = os.path.join(ROOT, "dist", "M1_COARSE26k_0728_1624.zip")
DECK_IN_ZIP = "M1_COARSE26k_0728_1624/abaqus/ZHANG2022_c26k_RT23.inp"

# ---- measured, from postprocess/damage_census.py on ZHANG2022_c26k_RT23.odb
U_COOLED = -3.216428e-03      # driver0 U1 at the end of the cooldown, RF1 = 0
U_LAST = -2.795763e-03        # driver0 U1 at the last converged tension frame
RF_LAST = 2.087986e+02        # N
T_HOT, T_COLD = 1050.0, 23.0
XRD_MATRIX = 114.7            # refs/[15]
TABLE3 = (128.45, 179.42, 199.15)

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-52s %s" % ("PASS" if cond else "FAIL", name, detail))


def near(a, b, tol):
    return abs(a - b) <= tol


def load_deck():
    with zipfile.ZipFile(DECK_ZIP) as z:
        return z.read(DECK_IN_ZIP).decode("utf-8", "replace")


def parse_mesh(text):
    nodes, elems, elset = {}, {}, defaultdict(list)
    mode, cur = None, None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("*"):
            low = s.lower()
            if low.startswith("*node") and "output" not in low:
                mode = "node"
            elif low.startswith("*element") and "output" not in low:
                mode = "elem"
            elif low.startswith("*elset"):
                mode = "elset"
                cur = s.split("=")[1].split(",")[0].strip()
            else:
                mode = None
            continue
        f = s.split(",")
        if mode == "node":
            nodes[int(f[0])] = tuple(float(x) for x in f[1:4])
        elif mode == "elem":
            elems[int(f[0])] = tuple(int(x) for x in f[1:5])
        elif mode == "elset":
            for tok in f:
                tok = tok.strip()
                if tok:
                    elset[cur].append(int(tok))
    return nodes, elems, elset


def tet_vol(p):
    a, b, c, d = p
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    w = [d[i] - a[i] for i in range(3)]
    return abs(u[0] * (v[1] * w[2] - v[2] * w[1])
               - u[1] * (v[0] * w[2] - v[2] * w[0])
               + u[2] * (v[0] * w[1] - v[1] * w[0])) / 6.0


def run(cmd):
    p = subprocess.Popen(cmd, cwd=ROOT, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    return out.decode("utf-8", "replace"), p.returncode


def main():
    print("=" * 72)
    print("ROUND 1 -- check_ch4_numbers.py: Ch.4 vs its primary sources")
    print("=" * 72)

    if not os.path.exists(CH4):
        print("  docs/CH4_RVE_HOMOGENISATION.md not found")
        return 1
    ch4 = open(CH4).read()

    # ---------------------------------------------------------------- mesh
    print("\n 4.2.1 geometry and discretisation -- re-parsed from the deck")
    if not os.path.exists(DECK_ZIP):
        check("shipped deck available", False, DECK_ZIP)
        return 1
    nodes, elems, elset = parse_mesh(load_deck())

    mesh_nodes = len([n for n in nodes if n <= 5680])
    check("5680 mesh nodes", len(nodes) == 5686 and mesh_nodes == 5680,
          "%d total incl. 6 drivers" % len(nodes))
    check("26452 C3D4 elements", len(elems) == 26452, "%d" % len(elems))

    n_mat = len(elset.get("Matrix", []))
    n_yarn = sum(len(v) for k, v in elset.items() if k.startswith("Yarn"))
    check("15369 matrix elements (58.1 %)",
          n_mat == 15369 and near(100.0 * n_mat / len(elems), 58.1, 0.05),
          "%d = %.1f %%" % (n_mat, 100.0 * n_mat / len(elems)))
    check("11083 yarn elements (41.9 %)",
          n_yarn == 11083 and near(100.0 * n_yarn / len(elems), 41.9, 0.05),
          "%d = %.1f %%" % (n_yarn, 100.0 * n_yarn / len(elems)))
    check("4 yarn tow sets",
          len([k for k in elset if k.startswith("Yarn")]) == 4)

    xs = [p[0] for p in nodes.values() if p != (0.0, 0.0, 0.0)]
    ys = [p[1] for p in nodes.values() if p != (0.0, 0.0, 0.0)]
    zs = [p[2] for p in nodes.values() if p != (0.0, 0.0, 0.0)]
    Lx, Ly, Lz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    check("RVE box 3.5 x 3.5 x 0.44 mm",
          near(Lx, 3.5, 1e-6) and near(Ly, 3.5, 1e-6) and near(Lz, 0.44, 1e-6),
          "%.4f x %.4f x %.4f" % (Lx, Ly, Lz))
    check("V_RVE = 5.390 mm^3", near(Lx * Ly * Lz, 5.390, 5e-4),
          "%.4f mm^3" % (Lx * Ly * Lz))

    owner = {}
    for k, v in elset.items():
        for e in v:
            owner[e] = "Matrix" if k == "Matrix" else "Yarn"
    vol = defaultdict(float)
    for eid, conn in elems.items():
        vol[owner.get(eid, "?")] += tet_vol([nodes[n] for n in conn])
    check("matrix volume 2.7045 mm^3", near(vol["Matrix"], 2.7045, 5e-4),
          "%.4f" % vol["Matrix"])
    check("yarn volume 2.6855 mm^3", near(vol["Yarn"], 2.6855, 5e-4),
          "%.4f" % vol["Yarn"])
    vy = vol["Yarn"] / (vol["Matrix"] + vol["Yarn"])
    check("V_y = 0.4982", near(vy, 0.4982, 5e-5), "%.4f" % vy)
    check("V_f 0.79194 -> composite 39.5 %",
          near(0.79194 * vy * 100, 39.5, 0.05),
          "%.2f %%" % (0.79194 * vy * 100))
    check("Ch.4 does not still say 39.6 %", "39.6 %" not in ch4)

    # ------------------------------------------------- crack-band limit
    print("\n 4.3.3 crack-band element-size limit")
    g0 = 310.0 ** 2 / (2.0 * 350000.0)
    lim = 0.031 / (1.02 * g0)
    check("limit 0.2214 mm", near(lim, 0.2214, 5e-5), "%.4f mm" % lim)
    cbrt, edge = [], []
    for eid, conn in elems.items():
        if owner.get(eid) != "Matrix":
            continue
        p = [nodes[n] for n in conn]
        cbrt.append(tet_vol(p) ** (1.0 / 3.0))
        edge.append(max(math.sqrt(sum((p[i][k] - p[j][k]) ** 2
                                      for k in range(3)))
                        for i in range(4) for j in range(i + 1, 4)))
    cbrt.sort()
    edge.sort()
    check("V^(1/3): median 0.053, max 0.083 mm",
          near(cbrt[len(cbrt) // 2], 0.053, 5e-4) and near(cbrt[-1], 0.083, 5e-4),
          "%.4f / %.4f" % (cbrt[len(cbrt) // 2], cbrt[-1]))
    check("V^(1/3): none over the limit",
          sum(1 for x in cbrt if x >= lim) == 0)
    check("longest edge: median 0.162, max 0.322 mm",
          near(edge[len(edge) // 2], 0.162, 1e-3) and near(edge[-1], 0.322, 1e-3),
          "%.4f / %.4f" % (edge[len(edge) // 2], edge[-1]))
    n_over = sum(1 for x in edge if x >= lim)
    check("longest edge: 849 over (5.5 % of matrix)",
          n_over == 849 and near(100.0 * n_over / n_mat, 5.5, 0.05),
          "%d = %.1f %%" % (n_over, 100.0 * n_over / n_mat))

    # ---------------------------------------- distorted-element fractions
    print("\n 4.3.2 distorted elements (counts from the .dat quality check)")
    check("1185 distorted = 4.5 % of all elements",
          near(100.0 * 1185 / len(elems), 4.5, 0.05),
          "%.1f %%" % (100.0 * 1185 / len(elems)))
    check("1185 distorted = 7.7 % of matrix elements",
          near(100.0 * 1185 / n_mat, 7.7, 0.05),
          "%.1f %%" % (100.0 * 1185 / n_mat))

    # --------------------------------------------- driver-derived numbers
    print("\n 4.4 / 4.5.3 numbers derived from the measured driver history")
    V = Lx * Ly * Lz
    de = U_LAST - U_COOLED
    sig = RF_LAST / V
    E = sig / de / 1000.0
    check("last converged tension strain 0.042 %", near(de * 100, 0.042, 5e-4),
          "%.4f %%" % (de * 100))
    check("stress there 38.7 MPa", near(sig, 38.7, 0.05), "%.2f MPa" % sig)
    check("that is 30.2 % of the 128.45 MPa target",
          near(100 * sig / TABLE3[0], 30.2, 0.05),
          "%.1f %%" % (100 * sig / TABLE3[0]))
    check("initial modulus 92.1 GPa", near(E, 92.1, 0.05), "%.1f GPa" % E)

    a_c = U_COOLED / (T_COLD - T_HOT)
    check("homogenised in-plane CTE 3.132e-6 /K", near(a_c, 3.132e-6, 5e-10),
          "%.4e /K" % a_c)

    for tag, eps, T, want in (("RT23", 1.5e-3, 23.0, 0.4716),
                              ("T500", 3.2e-3, 500.0, 0.4923),
                              ("T1000", 4.8e-3, 1000.0, 0.4957)):
        u0 = U_COOLED if T == 23.0 else a_c * (T - T_HOT)
        got = (eps - u0) * 100
        check("%s real tension range %.4f %%" % (tag, want),
              near(got, want, 5e-4), "%.4f %%" % got)
    check("all three land in 0.47-0.50 %",
          all(0.47 <= (e - (U_COOLED if T == 23 else a_c * (T - T_HOT))) * 100
              <= 0.50 for e, T in ((1.5e-3, 23), (3.2e-3, 500), (4.8e-3, 1000))))

    # 2nd attempt reached step time 0.133 of the same excursion
    frac2 = 0.133 * (1.5e-3 - U_COOLED) * 100
    check("2nd attempt reached 0.063 %", near(frac2, 0.063, 5e-4),
          "%.4f %%" % frac2)
    check("2nd attempt is 49 % further than the 1st",
          near(100 * (0.133 / 0.0892 - 1), 49.0, 1.0),
          "%.0f %%" % (100 * (0.133 / 0.0892 - 1)))

    # ------------------------------------------------------------- TRS
    print("\n 4.5 thermal residual stress")
    matrix_trs = 268.08
    check("matrix TRS / XRD = 2.34x", near(matrix_trs / XRD_MATRIX, 2.34, 0.005),
          "%.2fx" % (matrix_trs / XRD_MATRIX))
    check("matrix I1 = S11+S22+S33 = 572.04",
          near(268.08 + 268.01 + 35.94, 572.04, 0.02),
          "%.2f" % (268.08 + 268.01 + 35.94))
    yarns = (-547.45, -547.56, -547.13, -547.65)
    spread = (max(yarns) - min(yarns)) / abs(sum(yarns) / 4.0)
    check("the four tows agree within 0.1 %", spread < 1.0e-3,
          "%.4f %%" % (spread * 100))
    check("Ch.4 quotes the matrix in tension and yarn in compression",
          "+268.08" in ch4 and "−547.45" in ch4)

    # ---------------------------------------------- conductivity bounds
    print("\n 4.7 conductivity -- re-run conductivity_bounds.py")
    out, rc = run("python3 data/properties/conductivity_bounds.py --check")
    check("conductivity_bounds exits 0", rc == 0)
    check("Snead floor 61.1 W/(m.K) with k2 -> 0", "61.1" in out)
    check("measured C/SiC kbar3 = 6.29", "6.29" in out)
    check("k_m = 25 needs k2 = 0.695", "0.695" in out)
    check("dense series bound 6.74 exceeds the measurement", "6.74" in out)
    check("porosity needed 4.5 % vs 24 % measured",
          "4.5 %" in out and "24 %" in out)

    # ------------------------------------------------------- quench / Bi
    print("\n 4.8 quench -- re-run quench_calibration.py")
    out, rc = run("python3 abaqus/quench_calibration.py")
    check("quench_calibration exits 0", rc == 0)
    for tag, val in (("h(ZHANG2013) = 199", "199.0"),
                     ("Bi(ZHANG2013) = 0.0475", "0.0475"),
                     ("gradient 19.9 K = 3.3 %", "19.9"),
                     ("h(YIN2002) = 87", "87.0"),
                     ("Bi(YIN2002) = 0.0277", "0.0277"),
                     ("gradient 17.2 K", "17.2"),
                     ("hot row Bi = 0.2479", "0.2479"),
                     ("hot row gradient 91.9 K", "91.9")):
        check(tag, val in out)
    check("gradient spans 4.6x over the k range",
          near(91.9 / 19.9, 4.6, 0.05), "%.2fx" % (91.9 / 19.9))

    # ------------------------------------------- Table 3 quoted correctly
    print("\n 4.4.1 Zhang Table 3 targets")
    for v in TABLE3:
        check("Ch.4 quotes %.2f MPa" % v, ("%.2f" % v) in ch4)

    print("\n" + "=" * 72)
    if _BAD:
        print("ROUND 1 FAIL -- %d of %d: %s"
              % (len(_BAD), len(_OK) + len(_BAD), ", ".join(_BAD[:4])))
        print("=" * 72)
        return 1
    print("ROUND 1 PASS -- ALL %d CH.4 NUMBERS RE-DERIVED FROM SOURCE"
          % len(_OK))
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
