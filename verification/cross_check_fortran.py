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
                           case_yarn_v10_regression)):
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
