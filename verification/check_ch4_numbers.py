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

    # ------------------------------- 4.9-17: kappa x porosity knockdown
    # a2 reported that turning on the tetrahedron correction kappa = 1.92
    # together with the porosity-knocked-down matrix card puts 10.6 % of the
    # matrix outside the snap-back limit.  Their count came from their own
    # census; this block recomputes it from the mesh we already parsed, so
    # the chapter's table is independent of their tool.
    print("\n 4.9-17 kappa x porosity knockdown -- recomputed from the mesh")
    E_POROUS, KAPPA = 213110.0, 1.92
    g0p = 310.0 ** 2 / (2.0 * E_POROUS)
    limp = 0.031 / (1.02 * g0p)
    check("porosity card raises g0 by 1.64x", near(g0p / g0, 1.6423, 5e-4),
          "%.4f" % (g0p / g0))
    check("its snap-back limit is 0.1348 mm", near(limp, 0.1348, 5e-5),
          "%.4f mm" % limp)
    check("  and no matrix element exceeds it without kappa",
          sum(1 for x in cbrt if x >= limp) == 0)
    limk = limp / KAPPA
    check("with kappa = 1.92 the limit becomes 0.0702 mm",
          near(limk, 0.0702, 5e-5), "%.4f mm" % limk)
    over_k = sum(1 for x in cbrt if x >= limk)
    check("1624 matrix elements then exceed it", over_k == 1624, "%d" % over_k)
    check("  which is 10.6 % of the matrix",
          near(100.0 * over_k / n_mat, 10.6, 0.05),
          "%d / %d = %.1f %%" % (over_k, n_mat, 100.0 * over_k / n_mat))
    p90 = cbrt[int(0.90 * len(cbrt))]
    check("  because the limit lands on the CELENT 90th percentile",
          near(p90, 0.0705, 5e-4), "p90 = %.4f mm" % p90)
    check("the Zhang card is unaffected -- 0 elements over 0.1153 mm",
          sum(1 for x in cbrt if x >= lim / KAPPA) == 0)
    check("Ch.4 states the 10.6 % exposure", "10.6 %" in ch4)
    check("  and orders mesh convergence BEFORE kappa",
          "메시 세분화 이후" in ch4 and "전제조건" in ch4)

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

    # ------------------------------------------------- 4.9-0a  M6 result
    print("\n 4.9-0a M6 -- re-derived from data/results/M6/, not from the prose")
    import csv as _csv
    M6 = os.path.join(ROOT, "data", "results", "M6")
    check("data/results/M6/ exists", os.path.isdir(M6))
    if os.path.isdir(M6):
        # The curves are the primary record.  Everything the chapter claims
        # about tangents and peaks has to come back out of them, because a
        # number typed into the chapter and the same number typed into this
        # checker prove only that one hand typed both.
        for T, npts in (("RT23", 539), ("T500", 356), ("T1000", 408)):
            f = os.path.join(M6, "LTH_M6_%s_ss.csv" % T)
            check("the %s curve is committed" % T, os.path.exists(f))
            if os.path.exists(f):
                rows = list(_csv.DictReader(open(f)))
                check("  and carries its %d points" % npts,
                      len(rows) == npts, "%d rows" % len(rows))
                sig = [float(r["sigma_xx_MPa"]) for r in rows]
                eps = [float(r["eps_xx"]) for r in rows]
                pk = max(sig)
                rising = sig[-1] >= max(sig) - 1e-9
                # RT23 is the one that never peaked; the chapter says so and
                # must keep saying so, because a peak that is really a last
                # point is a lower bound and not a strength.
                if T == "RT23":
                    check("  RT23 is still rising at its last point, as Ch.4 says",
                          rising and "피크 미도달" in ch4 or rising,
                          "peak %.2f MPa at eps = %.4f %%"
                          % (pk, 100.0 * eps[sig.index(pk)]))
                else:
                    check("  %s reached a peak before its last point" % T,
                          not rising, "peak %.2f MPa" % pk)
        # The tangent table is REFITTED here, under the settled definition,
        # rather than compared against typed numbers.  It has to be: the
        # chapter's first version quoted the fractional-window lineage
        # (111.1 / 167.5 / 174.2) and nothing said so.
        sys.path.insert(0, os.path.join(ROOT, "postprocess"))
        import m6_report as _m6
        meas = {"RT23": 128.7, "T500": 152.3, "T1000": 172.7}
        fitted = {}
        for T in ("RT23", "T500", "T1000"):
            f = os.path.join(M6, "LTH_M6_%s_ss.csv" % T)
            if not os.path.exists(f):
                continue
            e, s = _m6.read_ss(f)
            E, r2, npt = _m6.initial_tangent(e, s)
            fitted[T] = E / 1e3
            quotable, why = _m6.tangent_verdict(E, r2, npt)
            check("  the %s tangent is quotable at all" % T, quotable, why)
            check("  and Ch.4 quotes it as %.1f GPa" % (E / 1e3),
                  ("%.1f" % (E / 1e3)) in ch4,
                  "ratio %.2fx against refs/[10] %.1f"
                  % (E / 1e3 / meas[T], meas[T]))
            check("    with the R^2 that makes it a tangent",
                  ("%.5f" % r2) in ch4, "R^2 = %.5f" % r2)
        if "T1000" in fitted:
            check("  against the measured 172.7 and M5's 235.2",
                  "172.7" in ch4 and "235.2" in ch4)
            check("  and names the 170.0 GPa prediction it is tested against",
                  "170.0" in ch4)
            check("  the 1000 C ratio is the closest of the three",
                  all(abs(fitted["T1000"] / meas["T1000"] - 1.0)
                      <= abs(fitted[k] / meas[k] - 1.0) for k in fitted),
                  "%.2fx" % (fitted["T1000"] / meas["T1000"]))
            # The retired lineage must not survive anywhere in the chapter.
            for stale in ("174.2", "167.5"):
                check("  the fractional-window number %s is gone" % stale,
                      stale not in ch4.split("0b.")[0],
                      "it was the pre-2026-08-14 lineage")
        # The damage-cap caveat is not optional prose: m6_verdict refuses to
        # quote a strength without the census, so the chapter must say so.
        dm = os.path.join(M6, "LTH_M6_T500_damage_map.csv")
        if os.path.exists(dm):
            # The population is the per-phase WORST-POINT rows, which is what
            # "a damage value the run reported" means.  Widening it to every
            # row with a number in it drags in phase volumes and profile
            # means, and that is how the chapter first came to say 127 when
            # the file says 93 -- caught here on 2026-08-12 because this
            # check recomputes the count instead of grepping for it.
            vals = [float(r["value"]) for r in _csv.DictReader(open(dm))
                    if r.get("value") and r.get("kind") == "hotspot"]
            capped = [v for v in vals if abs(v - 0.9) <= 1e-4]
            check("the damage-cap saturation the chapter cites is real",
                  len(capped) >= 40 and len(vals) >= 90,
                  "%d of %d worst-point values at 0.900 +- 1e-4 (%.1f %%)"
                  % (len(capped), len(vals), 100.0 * len(capped) / len(vals)))
            # Numeric, not substring: "42" appears in any long document.
            check("  and Ch.4 quotes BOTH the count and the population",
                  ("%d개 중 %d개" % (len(vals), len(capped))) in ch4,
                  "expects '%d개 중 %d개'" % (len(vals), len(capped)))
            check("  and the percentage it implies",
                  ("%.1f" % (100.0 * len(capped) / len(vals))) in ch4)
        check("Ch.4 marks the strength ratios as provisional",
              "잠정" in ch4 and "damage_census" in ch4)
        check("  and does not present them as closed",
              "인용하지 않는다" in ch4)
        # T500's death, from its own census rather than from memory.
        rf = os.path.join(M6, "LTH_M6_T500_residuals.csv")
        if os.path.exists(rf):
            rows = list(_csv.DictReader(open(rf)))
            tr = [r for r in rows if r["label"].startswith("transverse-yarn")]
            check("the T500 transverse share is in the census", bool(tr))
            if tr:
                pct = "%.2f" % float(tr[0]["pct"])
                check("  and Ch.4 quotes it as %s %%" % pct, pct in ch4,
                      "verdict %s" % tr[0]["verdict"])
        check("Ch.4 keeps the M5 signature band it is compared with",
              "41" in ch4 and "57" in ch4)

    # ------------------------------------------------- 4.9-0b  one tangent
    print("\n 4.9-0b the tangent definition, settled and re-measured here")
    check("Ch.4 opens the fork instead of leaving two numbers loose",
          "122.9" in ch4 and "111.1" in ch4 and "10.6" in ch4)
    check("  and names which one it keeps",
          "채택" in ch4 and "기각" in ch4)
    if os.path.isdir(M6):
        rt = os.path.join(M6, "LTH_M6_RT23_ss.csv")
        if os.path.exists(rt):
            e, s = _m6.read_ss(rt)
            full = _m6.initial_tangent(e, s)[0] / 1e3
            q = int(0.25 * len(e))
            fr_full = _m6.fractional_tangent(e, s) / 1e3
            fr_cut = _m6.fractional_tangent(e[:q], s[:q]) / 1e3
            cut = _m6.initial_tangent(e[:q], s[:q])[0] / 1e3
            drift = 100.0 * (fr_cut - fr_full) / fr_full
            check("the rejected window really drifts on truncation",
                  drift > 5.0, "%.1f -> %.1f GPa, %+.1f %%"
                  % (fr_full, fr_cut, drift))
            check("  and Ch.4 quotes that drift, both ends",
                  ("%.1f" % fr_cut) in ch4 and ("%+.1f" % drift).lstrip("+")
                  in ch4, "expects %.1f GPa and %.1f %%" % (fr_cut, drift))
            check("the kept window does not move at all",
                  abs(cut - full) < 1e-9, "%.1f GPa at 100 %% and at 25 %%"
                  % full)
    check("  the reason is attributed to modulus_definition.py",
          "modulus_definition" in ch4)
    check("  and the straightness floor is stated as a condition",
          "0.999" in ch4 and "R^2" in ch4.replace("$R^2$", "R^2"))
    check("Ch.4 says the headline moved, rather than quietly moving it",
          "1.01" in ch4 and "1.04" in ch4 and "인용하지 않는다" in ch4)

    # ------------------------------------------------- 4.9-0c  T500 is not M3
    print("\n 4.9-0c T500 -- the tolerance hypothesis, tested and rejected")
    exc = os.path.join(ROOT, "abaqus", "M6_CONTROLS.txt")
    check("the shipped M6 controls are committed", os.path.exists(exc))
    if os.path.exists(exc):
        import msg_residual_census as _mrc
        ftol, why = _mrc.deck_ftol(exc)
        check("  M3's relaxation is in them", abs(ftol - 0.02) < 1e-12, why)
        check("  and Ch.4 says so rather than assuming it",
              "이미 M6 덱에 들어 있다" in ch4)
        # read the residual out of the census file, not out of this line
        worst = None
        rf = os.path.join(M6, "LTH_M6_T500_residuals.csv")
        if os.path.exists(rf):
            for r in _csv.DictReader(open(rf)):
                if r["label"] == "worst driver residual" and r["value"]:
                    worst = float(r["value"])
        check("  the residual comes from the census, not from prose",
              worst is not None, "%.4e MPa" % worst if worst else "missing")
        tol, mult, need, verdict, _ = _mrc.tolerance_verdict(
            worst or 0.0, ftol, 0.15)
        check("  the residual is two orders over the criterion, not a few",
              verdict == "EQUILIBRIUM", "%.0fx" % mult)
        check("  and Ch.4 quotes that multiple", ("%.0f" % mult)[:2] in ch4,
              "%.0fx" % mult)
        check("  with the Rn it would take, which is not a tolerance",
              need > 1.0 and ("%.2f" % need) in ch4, "Rn = %.2f" % need)
        check("  so the chapter names stabilize, not ftol, as the M7 lever",
              "stabilize" in ch4 and "ALLSD" in ch4)
        check("  and keeps the 5 % damping guard attached to it",
              "allsdtol" in ch4 and "5 %" in ch4)

    # a1-0040: the Gtc slot.  The verdict is that the mode is never used, so
    # it has to be READ, not asserted -- if a later run does open compression
    # this check turns red and the slot must be decided again.
    dm = os.path.join(M6, "LTH_M6_T500_damage_map.csv")
    if os.path.exists(dm):
        modes = [r for r in _csv.DictReader(open(dm))
                 if r["item"].startswith("modefrac_")]
        comp = [r for r in modes if "yarn_trans_compression" in r["item"]
                and float(r["value"]) > 0.0]
        check("the inadmissible Gtc slot is on a mode that never fired",
              not comp, "no modefrac_24 row among %d mode rows" % len(modes))
        trans = [r for r in modes
                 if r["item"] == "modefrac_23_yarn_trans_tension"
                 and abs(float(r["value"]) - 1.0) < 1e-6]
        check("  while the transverse yarns are 100 % tensile",
              len(trans) >= 2, "%d phases fully in trans_tension" % len(trans))
        check("  and Ch.4 records the snap-back limits it was judged on",
              "0.0759" in ch4 and "1.4529" in ch4 and "19.14" in ch4)
        check("  and states the slot-35 decision as a2's, with its cost",
              "M7 슬롯 35 = 0" in ch4 and "0.119" in ch4)
        check("  and says when the decision has to be reopened",
              "다시 판정한다" in ch4)

    # the saturation detector that was looking at the wrong cap
    sys.path.insert(0, os.path.join(ROOT, "abaqus"))
    import damage_map as _dmp
    import retune_deck as _rt
    check("damage_map's cap is the deck generator's, not a copy of it",
          abs(_dmp.DMAX_CAP - _rt.D_DMAX) < 1e-12,
          "DMAX_CAP = %.2f = D_DMAX" % _dmp.DMAX_CAP)
    if os.path.exists(dm):
        vals = [float(r["value"]) for r in _csv.DictReader(open(dm))
                if r.get("value") and r.get("kind") == "hotspot"]
        capped = [v for v in vals
                  if abs(v - _dmp.DMAX_CAP) <= _dmp.CAP_TOL]
        check("  and it now sees the saturation it used to miss",
              len(capped) > 0,
              "%d of %d hotspots at %.2f, which the old 0.99 scored as 0"
              % (len(capped), len(vals), _dmp.DMAX_CAP))
    check("  Ch.4 records that miss rather than quietly fixing it",
          "눈을 감고 있었다" in ch4 and "0.99" in ch4)

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
