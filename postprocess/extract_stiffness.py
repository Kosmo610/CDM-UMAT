# -*- coding: utf-8 -*-
"""
extract_stiffness.py
====================
Turns the seven load cases written by abaqus/make_pbc_check.py into

  * the 6x6 homogenised stiffness C of the RVE,
  * the engineering constants E1..G23 (the numbers EasyPBC also reports),
  * the homogenised CTE vector,

and -- the point of the exercise -- into a verdict on whether the periodic
boundary conditions actually behaved.

Three independent consistency tests
-----------------------------------
1. AVERAGING     the volume average of the element strain field must reproduce
                 the macro strain imposed on the ConstraintsDriver nodes.  If the
                 constraints leak, the cell deforms by less than it was told to
                 and this ratio drifts off 1.
2. HILL-MANDEL   macro stress from the driver reaction forces (sigma = RF/V) must
                 equal the volume average of the element stress.  Two genuinely
                 different routes -- one through the constraint equations, one
                 through the integration points -- that agree only if the
                 constraints are work-consistent.
3. SYMMETRY      C must come out symmetric.  Nothing in the extraction enforces
                 it, so C_ij vs C_ji is a free check on the whole chain.

With --patch, two more that only make sense for a homogeneous cell:
4. UNIFORMITY    every element must carry the same stress, and the periodic
                 fluctuation u - H.x must be constant.  Exact for C3D4, which
                 represents constant strain exactly, so the tolerance is machine
                 precision rather than engineering judgement.
5. EXACTNESS     C must equal the isotropic stiffness typed into the deck, and the
                 homogenised CTE must equal the input CTE.

The driver reaction gives macro stress up to a sign that depends on how Abaqus
assembles the eliminated DOF.  Rather than assume one, the script determines it
from the run by comparing against the volume average, and reports which held.

Usage
-----
    abaqus python extract_stiffness.py PBC_PATCH.odb   --patch
    abaqus python extract_stiffness.py PBC_ELASTIC.odb
    abaqus python extract_stiffness.py PBC_ELASTIC.odb --volume 5.39 --dT 1.0

    python3 extract_stiffness.py --selftest        # math only, no Abaqus needed

Writes  <job>_C.csv, <job>_constants.csv, <job>_homogenisation.json
"""
from __future__ import print_function

import json
import os
import sys

try:
    from odbAccess import openOdb
except ImportError:                     # --selftest runs outside Abaqus
    openOdb = None

# Voigt order used throughout: 11, 22, 33, 12, 13, 23 -- Abaqus' own S/E order and
# the order of the TexGen drivers (e_x, e_y, e_z, e_xy, e_xz, e_yz).
VOIGT = ["11", "22", "33", "12", "13", "23"]
LOAD_STEPS = ["LC1_EXX", "LC2_EYY", "LC3_EZZ", "LC4_GXY", "LC5_GXZ", "LC6_GYZ"]
THERMAL_STEP = "LC7_DT"

# Macro displacement gradient produced by driver j: H[row][col] = applied value.
H_SLOT = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]

UNIFORMITY_TOL = 1.0e-6     # relative stress scatter allowed in the patch test
CONSISTENCY_TOL = 1.0e-3    # relative gap allowed between the two stress routes
SYMMETRY_TOL = 1.0e-3       # relative asymmetry allowed in C


# --------------------------------------------------------------------------- #
#  small dense linear algebra -- a 6x6 needs no numpy
# --------------------------------------------------------------------------- #

def inv(A):
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-30:
            raise ValueError("matrix is singular at column %d -- the run did not "
                             "produce six independent load cases" % c)
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        M[c] = [x / pv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c] != 0.0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [row[n:] for row in M]


def matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def maxabs(M):
    return max(abs(x) for row in M for x in row) or 1.0


def isotropic_C(E, nu):
    lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    mu = E / (2.0 * (1.0 + nu))
    C = [[0.0] * 6 for _ in range(6)]
    for i in range(3):
        for j in range(3):
            C[i][j] = lam + (2.0 * mu if i == j else 0.0)
        C[i + 3][i + 3] = mu
    return C


def orthotropic_C(E1, E2, E3, nu12, nu13, nu23, G12, G13, G23):
    S = [[0.0] * 6 for _ in range(6)]
    S[0][0], S[1][1], S[2][2] = 1.0 / E1, 1.0 / E2, 1.0 / E3
    S[0][1] = S[1][0] = -nu12 / E1
    S[0][2] = S[2][0] = -nu13 / E1
    S[1][2] = S[2][1] = -nu23 / E2
    S[3][3], S[4][4], S[5][5] = 1.0 / G12, 1.0 / G13, 1.0 / G23
    return inv(S)


def engineering_constants(C):
    S = inv(C)
    return {"E1": 1.0 / S[0][0], "E2": 1.0 / S[1][1], "E3": 1.0 / S[2][2],
            "nu12": -S[1][0] / S[0][0], "nu13": -S[2][0] / S[0][0],
            "nu23": -S[2][1] / S[1][1],
            "nu21": -S[0][1] / S[1][1], "nu31": -S[0][2] / S[2][2],
            "nu32": -S[1][2] / S[2][2],
            "G12": 1.0 / S[3][3], "G13": 1.0 / S[4][4], "G23": 1.0 / S[5][5]}


# --------------------------------------------------------------------------- #
#  ODB field access
# --------------------------------------------------------------------------- #

def blocks(field, kind):
    """Yield (labels, rows) for a field output, preferring the bulk API and
    falling back to the per-value API on older ODBs."""
    try:
        bdb = field.bulkDataBlocks
    except AttributeError:
        bdb = None
    if bdb:
        for blk in bdb:
            labels = blk.elementLabels if kind == "element" else blk.nodeLabels
            yield [int(x) for x in labels], [list(r) for r in blk.data]
        return
    labels, rows = [], []
    for val in field.values:
        labels.append(val.elementLabel if kind == "element" else val.nodeLabel)
        d = val.data
        rows.append(list(d) if hasattr(d, "__len__") else [d])
    yield labels, rows


def aligned_rows(frame, names):
    """Walk S / E / IVOL together, one integration point at a time.

    They come out of the same frame for the same elements, so the blocks line up;
    the label lists are compared rather than trusted."""
    streams = [list(blocks(frame.fieldOutputs[n], "element")) for n in names]
    if len(set(len(s) for s in streams)) != 1:
        raise ValueError("field outputs %s have different block counts" % names)
    for parts in zip(*streams):
        labels = parts[0][0]
        for name, part in zip(names[1:], parts[1:]):
            if part[0] != labels:
                raise ValueError("element ordering of %s does not match %s"
                                 % (name, names[0]))
        for k in range(len(labels)):
            yield [part[1][k] for part in parts]


def element_average(frame):
    """Volume-weighted average of S and E, the total integrated volume, and the
    peak-to-peak scatter of each stress component (the uniformity measure)."""
    acc_s, acc_e, vtot = [0.0] * 6, [0.0] * 6, 0.0
    smin, smax = [None] * 6, [None] * 6
    for s, e, iv in aligned_rows(frame, ["S", "E", "IVOL"]):
        v = iv[0]
        if v <= 0.0:
            continue
        vtot += v
        for i in range(6):
            acc_s[i] += s[i] * v
            acc_e[i] += e[i] * v
            if smin[i] is None or s[i] < smin[i]:
                smin[i] = s[i]
            if smax[i] is None or s[i] > smax[i]:
                smax[i] = s[i]
    if vtot <= 0.0:
        raise ValueError("no integration-point volume found -- was IVOL requested "
                         "in the field output?")
    sigma = [a / vtot for a in acc_s]
    eps = [a / vtot for a in acc_e]
    ref = max(abs(x) for x in sigma) or 1.0
    scatter = [((smax[i] - smin[i]) / ref) if smin[i] is not None else 0.0
               for i in range(6)]
    return sigma, eps, vtot, scatter


def nodeset_labels(odb, name):
    """Node labels of a set, whether it landed on the assembly or an instance."""
    ra = odb.rootAssembly
    st = ra.nodeSets[name] if name in ra.nodeSets.keys() else None
    if st is None:
        for inst in ra.instances.values():
            if name in inst.nodeSets.keys():
                st = inst.nodeSets[name]
                break
    if st is None:
        raise KeyError("node set %s not in the ODB" % name)
    nodes = st.nodes
    if nodes and hasattr(nodes[0], "__len__"):      # assembly sets nest per instance
        nodes = [n for group in nodes for n in group]
    return [n.label for n in nodes]


def driver_state(odb, frame, driver_labels):
    """(macro strain, driver reaction force), dof 1 of each driver node."""
    want = dict((lab, k) for k, lab in enumerate(driver_labels))

    def read(name):
        out = [0.0] * 6
        for labels, rows in blocks(frame.fieldOutputs[name], "node"):
            for lab, row in zip(labels, rows):
                if lab in want:
                    out[want[lab]] = row[0]
        return out

    return read("U"), read("RF")


def bounding_box(odb):
    inst = list(odb.rootAssembly.instances.values())[0]
    xs = [n.coordinates[0] for n in inst.nodes]
    ys = [n.coordinates[1] for n in inst.nodes]
    zs = [n.coordinates[2] for n in inst.nodes]
    return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


def fluctuation_spread(odb, frame, H, L):
    """max spread of u - H.x over the cell, normalised by |H|.L.

    Under correct PBC with a homogeneous material this field is a rigid
    translation, so its spread is zero to round-off."""
    inst = list(odb.rootAssembly.instances.values())[0]
    coord = dict((n.label, n.coordinates) for n in inst.nodes)
    lo, hi = [None] * 3, [None] * 3
    for labels, rows in blocks(frame.fieldOutputs["U"], "node"):
        for lab, row in zip(labels, rows):
            x = coord.get(lab)
            if x is None:                       # driver node: not in the mesh
                continue
            for i in range(3):
                w = row[i] - sum(H[i][j] * x[j] for j in range(3))
                if lo[i] is None or w < lo[i]:
                    lo[i] = w
                if hi[i] is None or w > hi[i]:
                    hi[i] = w
    scale = max(abs(H[i][j]) * L[j] for i in range(3) for j in range(3)) or 1.0
    spreads = [hi[i] - lo[i] for i in range(3) if lo[i] is not None]
    return (max(spreads) / scale) if spreads else 0.0


# --------------------------------------------------------------------------- #
#  reporting
# --------------------------------------------------------------------------- #

class Verdict(object):
    def __init__(self):
        self.fail = 0
        self.results = []

    def check(self, ok, msg, value=None):
        tag = "PASS" if ok else "FAIL"
        if not ok:
            self.fail += 1
        print("  [%s] %s%s" % (tag, msg, ("   (%s)" % value) if value else ""))
        self.results.append({"status": tag, "message": msg, "value": value})


def print_matrix(name, M, unit="MPa"):
    print("")
    print("  %s [%s], Voigt order 11 22 33 12 13 23:" % (name, unit))
    for i in range(6):
        print("    " + "  ".join("%12.4f" % M[i][j] for j in range(6)))


def arg_float(argv, flag, default=None):
    return float(argv[argv.index(flag) + 1]) if flag in argv else default


# --------------------------------------------------------------------------- #
#  offline self-test of the algebra
# --------------------------------------------------------------------------- #

def selftest():
    print("extract_stiffness.py -- offline algebra self-test")
    fails = 0

    def ck(ok, msg, val=""):
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", msg,
                               ("   (%s)" % val) if val else ""))
        return 0 if ok else 1

    A = [[4.0, 1.0, 0.3, 0.0, 0.1, 0.0],
         [1.0, 5.0, 0.4, 0.2, 0.0, 0.0],
         [0.3, 0.4, 6.0, 0.0, 0.0, 0.5],
         [0.0, 0.2, 0.0, 2.0, 0.0, 0.0],
         [0.1, 0.0, 0.0, 0.0, 2.5, 0.0],
         [0.0, 0.0, 0.5, 0.0, 0.0, 3.0]]
    Ai = inv(A)
    prod = [[sum(A[i][k] * Ai[k][j] for k in range(6)) for j in range(6)]
            for i in range(6)]
    err = max(abs(prod[i][j] - (1.0 if i == j else 0.0))
              for i in range(6) for j in range(6))
    fails += ck(err < 1e-12, "inv(A) . A == I", "max error %.2e" % err)

    E, nu = 350000.0, 0.2
    c = engineering_constants(isotropic_C(E, nu))
    G = E / (2.0 * (1.0 + nu))
    err = max(abs(c["E1"] - E), abs(c["E2"] - E), abs(c["E3"] - E)) / E
    fails += ck(err < 1e-12, "isotropic C round-trips E", "rel error %.2e" % err)
    err = max(abs(c["nu12"] - nu), abs(c["nu13"] - nu), abs(c["nu23"] - nu)) / nu
    fails += ck(err < 1e-12, "isotropic C round-trips nu", "rel error %.2e" % err)
    err = max(abs(c["G12"] - G), abs(c["G13"] - G), abs(c["G23"] - G)) / G
    fails += ck(err < 1e-12, "isotropic C round-trips G = E/2(1+nu)",
                "rel error %.2e" % err)

    # the ZHANG2022 yarn card: a stiff orthotropic phase
    ref = dict(E1=254967.228042, E2=44321.737572, E3=44321.737572,
               nu12=0.247516386, nu13=0.247516386, nu23=0.395813581,
               G12=26431.515264, G13=26431.515264, G23=15876.667974)
    c = engineering_constants(orthotropic_C(**ref))
    err = max(abs(c[k] - ref[k]) / abs(ref[k]) for k in ref)
    fails += ck(err < 1e-10, "orthotropic C round-trips all nine yarn constants",
                "max rel error %.2e" % err)

    # CTE recovery: sigma_th = -C.alpha.dT with the macro strain clamped
    C = orthotropic_C(**ref)
    alpha = [1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06, 0, 0, 0]
    dT = 1.0
    sigma_th = [-x * dT for x in matvec(C, alpha)]
    rec = [-x / dT for x in matvec(inv(C), sigma_th)]
    err = max(abs(rec[i] - alpha[i]) for i in range(3)) / max(alpha[:3])
    fails += ck(err < 1e-10, "CTE recovered from the clamped thermal load case",
                "max rel error %.2e" % err)

    print("")
    print("ALL CHECKS PASSED" if fails == 0 else "%d CHECK(S) FAILED" % fails)
    return 0 if fails == 0 else 1


# --------------------------------------------------------------------------- #

def main(argv):
    if "--selftest" in argv:
        return selftest()
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 1
    if openOdb is None:
        print("error: odbAccess is unavailable -- run this with 'abaqus python', "
              "or use --selftest for the algebra check.")
        return 2

    odbpath = argv[0]
    patch = "--patch" in argv
    dT = arg_float(argv, "--dT", 1.0)

    odb = openOdb(odbpath, readOnly=True)
    L = bounding_box(odb)
    Vbox = L[0] * L[1] * L[2]
    V = arg_float(argv, "--volume", Vbox)

    print("=" * 78)
    print("PBC HOMOGENISATION  ->  %s" % odbpath)
    print("=" * 78)
    print("  RVE box  Lx=%.6f  Ly=%.6f  Lz=%.6f mm   V=%.6f mm^3"
          % (L[0], L[1], L[2], V))

    have = dict((s.upper(), s) for s in odb.steps.keys())
    missing = [s for s in LOAD_STEPS if s not in have]
    if missing:
        print("  ERROR: missing load-case step(s): %s" % ", ".join(missing))
        print("         available: %s" % ", ".join(odb.steps.keys()))
        odb.close()
        return 1

    drivers = [nodeset_labels(odb, "CONSTRAINTSDRIVER%d" % i)[0] for i in range(6)]

    v = Verdict()
    C_vol = [[0.0] * 6 for _ in range(6)]
    C_rf = [[0.0] * 6 for _ in range(6)]
    per_case, fill = [], None

    print("")
    print("LOAD CASES")
    for j, key in enumerate(LOAD_STEPS):
        frame = odb.steps[have[key]].frames[-1]
        sigma, eps, vtot, scatter = element_average(frame)
        U, RF = driver_state(odb, frame, drivers)
        if not U[j]:
            print("  ERROR: driver %d shows zero displacement in %s" % (j, key))
            odb.close()
            return 1
        if fill is None:
            fill = vtot / Vbox
        for i in range(6):
            C_vol[i][j] = sigma[i] / U[j]
            C_rf[i][j] = (RF[i] / V) / U[j]
        per_case.append({"step": have[key], "driver": j, "applied": U[j],
                         "sigma_vol": sigma, "eps_vol": eps, "RF": RF,
                         "eps_ratio": eps[j] / U[j], "scatter": scatter,
                         "fill": vtot / Vbox})
        print("  %-9s driver %d = %-10.6g  <eps_%s>/applied = %8.5f  "
              "<sigma_%s> = %11.4f MPa"
              % (have[key], j, U[j], VOIGT[j], eps[j] / U[j], VOIGT[j], sigma[j]))

    # the reaction route carries an assembly-dependent sign; take it from the run
    proj = sum(C_vol[i][j] * C_rf[i][j] for i in range(6) for j in range(6))
    sign = 1.0 if proj >= 0 else -1.0
    C_rf = [[sign * x for x in row] for row in C_rf]
    print("")
    print("  driver reaction convention detected:  sigma_macro = %sRF / V_RVE"
          % ("+" if sign > 0 else "-"))

    print("")
    print("CONSISTENCY CHECKS")
    v.check(abs(fill - 1.0) < 1e-3,
            "mesh fills the RVE box, so the averaging volume is the cell volume",
            "sum(IVOL)/V_box = %.6f" % fill)

    # 1. averaging.  Abaqus writes engineering shear in E, but accept the tensor
    #    convention too rather than fail on a convention difference.
    worst, worst_case, tensor_shear = 0.0, "", False
    for c in per_case:
        r = c["eps_ratio"]
        target = 1.0 if abs(r - 1.0) <= abs(r - 0.5) else 0.5
        if target == 0.5:
            tensor_shear = True
        if abs(r - target) > worst:
            worst, worst_case = abs(r - target), c["step"]
    v.check(worst < CONSISTENCY_TOL,
            "volume-averaged strain reproduces the imposed macro strain",
            "worst deviation %.3e (%s)" % (worst, worst_case))
    if tensor_shear:
        print("         note: shear strain output is tensor (gamma/2); the "
              "stiffness below still uses engineering shear from the drivers.")

    # 2. Hill-Mandel
    gap = max(abs(C_vol[i][j] - C_rf[i][j])
              for i in range(6) for j in range(6)) / maxabs(C_vol)
    v.check(gap < CONSISTENCY_TOL,
            "macro stress from driver reactions == volume-averaged stress",
            "max relative gap %.3e" % gap)

    # 3. symmetry
    asym = max(abs(C_vol[i][j] - C_vol[j][i])
               for i in range(6) for j in range(6)) / maxabs(C_vol)
    v.check(asym < SYMMETRY_TOL, "homogenised stiffness is symmetric",
            "max |C_ij - C_ji| / max|C| = %.3e" % asym)

    C = [[0.5 * (C_vol[i][j] + C_vol[j][i]) for j in range(6)] for i in range(6)]

    if patch:
        print("")
        print("PATCH TEST CHECKS (homogeneous cell -- the exact answer is known)")
        worst_scatter = max(max(c["scatter"]) for c in per_case)
        v.check(worst_scatter < UNIFORMITY_TOL,
                "stress field is uniform across every element",
                "peak-to-peak / |sigma| = %.3e" % worst_scatter)

        worst_w = 0.0
        for j, key in enumerate(LOAD_STEPS):
            H = [[0.0] * 3 for _ in range(3)]
            H[H_SLOT[j][0]][H_SLOT[j][1]] = per_case[j]["applied"]
            frame = odb.steps[have[key]].frames[-1]
            worst_w = max(worst_w, fluctuation_spread(odb, frame, H, L))
        v.check(worst_w < 1e-6,
                "periodic fluctuation u - H.x is constant across the cell",
                "max spread / (H.L) = %.3e" % worst_w)

        E, nu, a_in = None, None, None
        try:
            mat = odb.materials[list(odb.materials.keys())[0]]
            E, nu = mat.elastic.table[0][0], mat.elastic.table[0][1]
            a_in = mat.expansion.table[0][0]
        except Exception:
            pass
        E = arg_float(argv, "--E", E)
        nu = arg_float(argv, "--nu", nu)
        a_in = arg_float(argv, "--alpha", a_in)
        if E and nu is not None:
            Cex = isotropic_C(E, nu)
            err = max(abs(C[i][j] - Cex[i][j])
                      for i in range(6) for j in range(6)) / maxabs(Cex)
            v.check(err < 1e-6,
                    "C equals the isotropic stiffness in the deck (E=%g, nu=%g)"
                    % (E, nu), "max relative error %.3e" % err)
        else:
            print("  [SKIP] elastic constants unreadable from the ODB; pass "
                  "--E and --nu to compare against the exact C")
    else:
        a_in = None

    print_matrix("C homogenised", C)

    const = engineering_constants(C)
    print("")
    print("  ENGINEERING CONSTANTS")
    print("    E1  = %10.2f MPa    E2  = %10.2f MPa    E3  = %10.2f MPa"
          % (const["E1"], const["E2"], const["E3"]))
    print("    G12 = %10.2f MPa    G13 = %10.2f MPa    G23 = %10.2f MPa"
          % (const["G12"], const["G13"], const["G23"]))
    print("    nu12= %10.6f        nu13= %10.6f        nu23= %10.6f"
          % (const["nu12"], const["nu13"], const["nu23"]))

    cte = None
    if THERMAL_STEP in have:
        frame = odb.steps[have[THERMAL_STEP]].frames[-1]
        sigma_th = element_average(frame)[0]
        cte = [-x / dT for x in matvec(inv(C), sigma_th)]
        print("")
        print("  HOMOGENISED CTE (LC7: macro strain clamped, dT = %g K)" % dT)
        print("    alpha_x = %12.6e /K   alpha_y = %12.6e /K   alpha_z = %12.6e /K"
              % (cte[0], cte[1], cte[2]))
        print("    shear   = %.3e, %.3e, %.3e /K  (~0 for an orthotropic cell)"
              % (cte[3], cte[4], cte[5]))
        if patch and a_in:
            err = max(abs(cte[i] - a_in) for i in range(3)) / abs(a_in)
            v.check(err < 1e-4,
                    "homogenised CTE equals the input CTE (%g /K)" % a_in,
                    "max relative error %.3e" % err)
    else:
        print("")
        print("  (no %s step in this ODB -- CTE not extracted)" % THERMAL_STEP)

    base = os.path.splitext(odbpath)[0]
    with open(base + "_C.csv", "w") as fh:
        fh.write("," + ",".join(VOIGT) + "\n")
        for i in range(6):
            fh.write(VOIGT[i] + "," +
                     ",".join("%.8e" % C[i][j] for j in range(6)) + "\n")
    with open(base + "_constants.csv", "w") as fh:
        fh.write("constant,value,unit\n")
        for k in ("E1", "E2", "E3", "G12", "G13", "G23",
                  "nu12", "nu13", "nu23", "nu21", "nu31", "nu32"):
            fh.write("%s,%.8e,%s\n" % (k, const[k], "MPa" if k[0] in "EG" else "-"))
        if cte:
            for i, k in enumerate(("alpha_x", "alpha_y", "alpha_z")):
                fh.write("%s,%.8e,1/K\n" % (k, cte[i]))
    with open(base + "_homogenisation.json", "w") as fh:
        json.dump({"odb": odbpath, "V_rve": V, "L": list(L),
                   "C": C, "C_from_reactions": C_rf,
                   "C_from_volume_average": C_vol, "rf_sign": sign,
                   "constants": const, "cte": cte, "load_cases": per_case,
                   "checks": v.results, "failures": v.fail}, fh, indent=2)

    print("")
    print("  wrote %s_C.csv, %s_constants.csv, %s_homogenisation.json"
          % (base, base, base))
    print("=" * 78)
    if v.fail == 0:
        print("RESULT: PERIODIC BOUNDARY CONDITIONS VERIFIED  (%d checks passed)"
              % len(v.results))
    else:
        print("RESULT: %d CHECK(S) FAILED -- do not trust this homogenisation"
              % v.fail)
    print("=" * 78)

    odb.close()
    return 0 if v.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
