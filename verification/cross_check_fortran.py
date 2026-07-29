#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross_check_fortran.py
======================
Compile the REAL Fortran of src/UMAT_CSIC_THERMSHOCK_V3_0.for and check that
it agrees with the Python mirror in verify_thermshock.py, material point by
material point.

Why this matters
----------------
verify_thermshock.py verifies a Python re-implementation.  That proves the
MODEL is right; it does not prove the FORTRAN is right.  The two are separate
pieces of code and can disagree -- a swapped card slot, a wrong sign, a typo in
an index would pass every Python test and still be wrong in Abaqus.  This
script closes that gap by driving the compiled Fortran subroutines directly
(verification/kmacro_driver.f) and comparing:

    STRESS(6), the damaged secant stiffness diagonal, and every STATEV

for randomised but physically sensible states, across all three material
routines and with the temperature table, crack closure and cycle damage all
active.

Requires gfortran.  Skips (exit 0, clearly reported) if gfortran is absent, so
it can live in a CI step on a machine without a Fortran compiler.

Run:  python3 verification/cross_check_fortran.py
"""
from __future__ import print_function

import os
import random
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
UMAT = os.path.join(ROOT, "src", "UMAT_CSIC_THERMSHOCK_V3_0.for")
DRIVER = os.path.join(HERE, "kmacro_driver.f")

import verify_thermshock as vt

RTOL = 1.0e-10
ATOL = 1.0e-9
_FAILS = []


def build(workdir):
    """Compile the UMAT + driver into a stand-alone executable."""
    with open(os.path.join(workdir, "ABA_PARAM.INC"), "w") as f:
        f.write("      IMPLICIT REAL*8(A-H,O-Z)\n")
    shutil.copy(UMAT, os.path.join(workdir, "umat.f"))
    shutil.copy(DRIVER, os.path.join(workdir, "driver.f"))
    exe = os.path.join(workdir, "kmacro_driver")
    cmd = ["gfortran", "-ffixed-form", "-std=legacy", "-O1",
           "-I", workdir, "-o", exe, "driver.f", "umat.f"]
    p = subprocess.Popen(cmd, cwd=workdir, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate()
    if p.returncode != 0:
        print(out.decode("utf-8", "replace"))
        raise SystemExit("gfortran failed to build the driver")
    return exe


def run_fortran(exe, kind, props, statev, eps, temp, dtemp, dtime, fldv,
                celent, kstep):
    def fmt(seq):
        return " ".join("%.17g" % v for v in seq)
    inp = "\n".join([
        str(kind),
        str(len(props)),
        fmt(props),
        str(len(statev)),
        fmt(statev),
        fmt(eps),
        "%.17g %.17g %.17g %.17g %.17g %d"
        % (temp, dtemp, dtime, fldv, celent, kstep),
    ]) + "\n"
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    out, _ = p.communicate(inp.encode())
    txt = out.decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError("driver failed:\n" + txt)
    lines = [l for l in txt.strip().splitlines() if l.strip()]
    stress = [float(v) for v in lines[0].split()]
    sv = [float(v) for v in lines[1].split()]
    cdiag = [float(v) for v in lines[2].split()]
    return np.array(stress), sv, np.array(cdiag)


def cmp_arrays(name, a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    scale = np.maximum(np.abs(a), np.abs(b))
    err = np.abs(a - b) / np.where(scale > 0, scale, 1.0)
    absd = np.abs(a - b)
    ok = bool(np.all((err <= RTOL) | (absd <= ATOL)))
    if not ok:
        j = int(np.argmax(np.where(scale > 0, err, absd)))
        print("      %-8s MISMATCH at %d: fortran=%.17g python=%.17g"
              % (name, j, a[j], b[j]))
    return ok, float(np.max(np.where(scale > 0, err, absd)))


# ==========================================================================
# card builders -> flat 1-based-ordered lists for the driver
# ==========================================================================
def flat(P, n):
    return [P[i + 1] for i in range(n)]


def macro_props(hclo, cycon, C, n, k, rth, dcymax, w1, cycrate, ttab,
                **crit):
    P, _ = vt.macro_card(hclo=hclo, cycon=cycon, C=C, n=n, k=k, rth=rth,
                         dcymax=dcymax, w1=w1, cycrate=cycrate, predefn=0,
                         ttab=ttab, **crit)
    n_slot = 47 + 8 * len(ttab) + (9 if crit.get("icrit") else 0)
    return flat(P, n_slot), P


def yarn_props(hclo, ttab):
    P = vt.yarn_card_v2()
    vals = flat(P, 38)
    if hclo or ttab:
        vals = vals + [hclo, float(len(ttab))]
        for row in ttab:
            vals.extend(row)
    return vals, P


# ==========================================================================
def case_macro(exe, rng):
    """Randomised macro points with T-table + closure + cycle damage on."""
    ttab = [[23.0, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
            [500.0, 0.94, 0.88, 0.90, 0.96, 0.83, 0.86, 1.60],
            [1000.0, 0.86, 0.72, 0.78, 0.91, 0.64, 0.70, 3.20]]
    # The failure-criterion block is switched ON here: it appends nine card
    # slots AFTER the temperature table, which is exactly the kind of layout
    # change that a Python-only test cannot police.
    props, P = macro_props(0.7, 1.0, 3.0e-2, 3.0, -1.0, 0.30, 0.95, 0.30,
                           2.0, ttab, icrit=1, fs12=-0.45, fs23=-0.60,
                           idmode=2, dc1=0.52, dct=0.48, dcs=0.54, di12=0.3)
    worst = 0.0
    npass = 0
    for it in range(24):
        eps = np.array([rng.uniform(-2.5e-3, 3.0e-3) for _ in range(3)]
                       + [rng.uniform(-2.0e-3, 2.0e-3) for _ in range(3)])
        sv = [0.0] * 28
        # start from a partly damaged state on half the cases
        if it % 2:
            sv[0] = rng.uniform(0.0, 0.5)
            sv[2] = rng.uniform(0.0, 0.5)
            sv[4] = rng.uniform(1.0, 2.0)
            sv[6] = rng.uniform(1.0, 2.0)
            sv[16] = rng.uniform(0.0, 0.4)
            sv[17] = rng.uniform(0.0, 50.0)
            # Pre-set some latch bits so the "fire only once" logic is
            # exercised from a non-zero state, not just from rest.
            sv[24] = float(rng.choice([0, 1, 2, 4, 3, 5, 6, 7]))
            sv[25] = rng.uniform(0.0, 20.0)
            sv[26] = rng.uniform(0.0, 20.0)
            sv[27] = rng.uniform(0.0, 20.0)
        temp = rng.choice([23.0, 260.0, 500.0, 780.0, 1000.0, 1400.0, -50.0])
        dtime = rng.choice([0.01, 0.1, 1.0])

        sF, svF, cF = run_fortran(exe, 1, props, sv, eps, temp, 0.0, dtime,
                                  0.0, 1.0, 3)
        # The driver passes TEMP with DTEMP=0, so the mirror uses temp
        # directly.  rate=None makes it fall back on CYCRATE = PROPS(45),
        # which is what the Fortran does when PREDEFN = 0.
        sP, CP, svP = vt.macro_point(eps, sv, P, ttab, temp=temp,
                                     dtime=dtime, rate=None, celent=1.0)
        o1, e1 = cmp_arrays("STRESS", sF, sP)
        o2, e2 = cmp_arrays("Cdiag", cF, [CP[i, i] for i in range(6)])
        o3, e3 = cmp_arrays("STATEV", svF, svP)
        worst = max(worst, e1, e2, e3)
        if o1 and o2 and o3:
            npass += 1
    return npass, 24, worst


def case_yarn(exe, rng):
    ttab = [[23.0, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
            [1000.0, 0.83, 0.71, 0.76, 0.90, 0.62, 0.68]]
    props, P = yarn_props(0.6, ttab)
    worst = 0.0
    npass = 0
    for it in range(24):
        eps = np.array([rng.uniform(-1.5e-3, 2.0e-3) for _ in range(6)])
        sv = [0.0] * 17
        if it % 2:
            sv[0] = rng.uniform(0.0, 0.4)
            sv[2] = rng.uniform(0.0, 0.4)
            sv[4] = rng.uniform(1.0, 1.8)
            sv[6] = rng.uniform(1.0, 1.8)
        temp = rng.choice([23.0, 400.0, 1000.0, 1300.0])
        sF, svF, cF = run_fortran(exe, 2, props, sv, eps, temp, 0.0, 1.0,
                                  0.0, 0.03, 3)
        sP, CP, svP = vt.yarn_point31(eps, sv, P, ttab=ttab, hclo=0.6,
                                      temp=temp, celent=0.03)
        o1, e1 = cmp_arrays("STRESS", sF, sP)
        o2, e2 = cmp_arrays("Cdiag", cF, [CP[i, i] for i in range(6)])
        o3, e3 = cmp_arrays("STATEV", svF, svP)
        worst = max(worst, e1, e2, e3)
        if o1 and o2 and o3:
            npass += 1
    return npass, 24, worst


def case_yarn_v10_regression(exe, rng):
    """The 38-slot V1_0 card must still give the V1_0 answer in FORTRAN."""
    import verify_constitutive as vc
    P = vt.yarn_card_v2()
    props = flat(P, 38)
    Pv = [P[i + 1] for i in range(38)]
    worst = 0.0
    npass = 0
    for _ in range(16):
        eps = np.array([rng.uniform(-1.5e-3, 2.0e-3) for _ in range(6)])
        sF, _, _ = run_fortran(exe, 2, props, [0.0] * 16, eps, 23.0, 0.0,
                               1.0, 0.0, 0.03, 3)
        sP = vc.yarn_point(eps, [0.0] * 16, Pv)[0]
        ok, e = cmp_arrays("STRESS", sF, sP)
        worst = max(worst, e)
        npass += int(ok)
    return npass, 16, worst


MATRIX_V10 = [2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.90, 0.90, 0.05,
              0.03, 3.0, 0.25, 1.0, 0.031, 0.031, 250.0, 100000.0, 1.15, 0.75,
              0.50, 30.0]


def matrix_point_hsmo(eps, sv, P, hsmo, celent=0.03):
    """Python mirror of KMTRX31 with the I1 blend.  Reuses the verified V1_0
    point routine for everything except the d_act selection, so any drift in
    the base model shows up as a mismatch rather than being hidden here."""
    import math
    import numpy as _np
    import verify_constitutive as vc
    stress, CD, sv_new, diag = vc.matrix_point(eps, sv, P, celent=celent,
                                               kstep=1)
    if hsmo <= 0.0:
        return stress, CD, sv_new, diag
    E, nu, XT = P[1], P[2], P[3]
    G = E / (2.0 * (1.0 + nu))
    arg = diag["I1"] / (hsmo * XT)
    if arg > 30.0:
        w = 1.0
    elif arg < -30.0:
        w = 0.0
    else:
        w = 0.5 * (1.0 + math.tanh(arg))
    dact = w * sv_new[0] + (1.0 - w) * sv_new[1]
    dact = min(0.999, max(0.0, dact))
    CD = vc.kortho(E * (1 - dact), E * (1 - dact), E * (1 - dact),
                   nu * (1 - dact), nu * (1 - dact), nu * (1 - dact),
                   G * (1 - dact), G * (1 - dact), G * (1 - dact))
    eel = _np.asarray(eps) - sv_new[14:20]
    sv_new = sv_new.copy()
    sv_new[4] = dact
    return CD.dot(eel), CD, sv_new, diag


def case_matrix_v10_regression(exe, rng):
    """The 22-slot V1_0 matrix card must still give the V1_0 answer, and the
    25-slot card with HSMO=0 must give the SAME answer -- otherwise the new
    block is not a superset."""
    import verify_constitutive as vc
    worst, npass, ntot = 0.0, 0, 0
    p22 = list(MATRIX_V10)
    p25 = list(MATRIX_V10) + [0.0, 0.0, 32.0]      # NT=0, HSMO=0, key
    for _ in range(14):
        eps = np.array([rng.uniform(-2.0e-3, 2.5e-3) for _ in range(6)])
        sv = [0.0] * 20
        sP = vc.matrix_point(eps, np.zeros(20), p22, celent=0.03, kstep=1)[0]
        for props in (p22, p25):
            sF, _, _ = run_fortran(exe, 3, props, sv, eps, 23.0, 0.0, 1.0,
                                   0.0, 0.03, 1)
            ok, e = cmp_arrays("STRESS", sF, sP)
            worst = max(worst, e)
            npass += int(ok)
            ntot += 1
    return npass, ntot, worst


def case_matrix_hsmo(exe, rng):
    """HSMO > 0: the Fortran blend must match the Python blend, and the blend
    must actually remove the jump."""
    worst, npass, ntot = 0.0, 0, 0
    for _ in range(20):
        hsmo = rng.choice([0.05, 0.1, 0.2, 0.5])
        props = list(MATRIX_V10) + [0.0, hsmo, 32.0]
        eps = np.array([rng.uniform(-2.5e-3, 2.5e-3) for _ in range(6)])
        sv = [0.0] * 20
        # pre-damage in tension so d_t > 0 while d_c = 0 -- the state that
        # makes the published switch discontinuous
        sv[0] = rng.uniform(0.2, 0.85)
        sv[2] = rng.uniform(1.2, 2.5)
        sF, svF, cF = run_fortran(exe, 3, props, sv, eps, 23.0, 0.0, 1.0,
                                  0.0, 0.03, 1)
        sP, CP, svP, _ = matrix_point_hsmo(eps, np.array(sv), MATRIX_V10,
                                           hsmo, celent=0.03)
        o1, e1 = cmp_arrays("STRESS", sF, sP)
        o2, e2 = cmp_arrays("Cdiag", cF, [CP[i, i] for i in range(6)])
        worst = max(worst, e1, e2)
        npass += int(o1 and o2)
        ntot += 1
    return npass, ntot, worst


def case_matrix_continuity(exe, rng):
    """The point of the whole exercise: sweep I1 through zero and check that
    the stress is continuous with HSMO > 0 and discontinuous without it."""
    worst, npass, ntot = 0.0, 0, 0
    dt = 0.80                       # tensile damage carried into the sweep
    for hsmo, want_smooth in ((0.0, False), (0.1, True)):
        props = list(MATRIX_V10) + ([] if hsmo == 0.0 else [0.0, hsmo, 32.0])
        if hsmo == 0.0:
            props = list(MATRIX_V10)
        jumps = []
        prev = None
        # Fixed deviatoric part, hydrostatic part swept through zero, so I1
        # changes sign while the stress stays well away from zero.  A purely
        # hydrostatic sweep would be useless: it has Q = 0, so the stress
        # vanishes at the crossing and the jump hides itself.
        adev = 2.0e-4
        for k in range(-60, 61):
            ev = k * 1.0e-6
            eps = np.array([ev + adev, ev - adev, ev, 0.0, 0.0, 0.0])
            sv = [0.0] * 20
            sv[0] = dt
            sv[2] = 3.0
            sF, _, _ = run_fortran(exe, 3, props, sv, eps, 23.0, 0.0, 1.0,
                                   0.0, 0.03, 1)
            if prev is not None:
                jumps.append(abs(sF[0] - prev))
            prev = sF[0]
        big = max(jumps)
        typ = sorted(jumps)[len(jumps) // 2]
        ratio = big / max(typ, 1e-30)
        ok = (ratio < 5.0) if want_smooth else (ratio > 50.0)
        ntot += 1
        npass += int(ok)
        worst = max(worst, 0.0)
        print("        HSMO=%-4g  largest stress step across I1=0 is %6.1fx "
              "the typical one -> %s" % (hsmo, ratio,
                                         "smooth" if ratio < 5 else "JUMP"))
    return npass, ntot, worst


def main():
    print("=" * 72)
    print("cross_check_fortran.py -- compiled UMAT vs the Python mirror")
    print("=" * 72)
    if shutil.which("gfortran") is None:
        print("\n  gfortran not found -- SKIPPED (not a failure).")
        return 0

    work = tempfile.mkdtemp(prefix="umatxcheck_")
    try:
        exe = build(work)
        print("\n  built %s" % os.path.basename(exe))
        rng = random.Random(20260727)

        for label, fn in (("MACRO  (KMACRO31: T-table + closure + d_cyc)",
                           case_macro),
                          ("YARN   (KYARN31: T-table + closure)", case_yarn),
                          ("YARN   (38-slot V1_0 card -> V1_0 answer)",
                           case_yarn_v10_regression),
                          ("MATRIX (22- and 25-slot cards -> V1_0 answer)",
                           case_matrix_v10_regression),
                          ("MATRIX (KMTRX31: I1 smoothing, HSMO>0)",
                           case_matrix_hsmo),
                          ("MATRIX (I1=0 continuity: the reason for HSMO)",
                           case_matrix_continuity)):
            npass, ntot, worst = fn(exe, rng)
            tag = "PASS" if npass == ntot else "FAIL"
            print("  [%s] %-46s %d/%d  worst rel. dev. %.2e"
                  % (tag, label, npass, ntot, worst))
            if npass != ntot:
                _FAILS.append(label)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\n" + "=" * 72)
    if _FAILS:
        print("OVERALL: FORTRAN AND PYTHON DISAGREE -> %s" % ", ".join(_FAILS))
        print("=" * 72)
        return 1
    print("OVERALL: THE COMPILED UMAT MATCHES THE VERIFIED PYTHON MODEL")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
