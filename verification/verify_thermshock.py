#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_thermshock.py
====================
Single-material-point re-implementation and verification of the THREE features
added in

    src/UMAT_CSIC_THERMSHOCK_V3_0.for

over the verified replication UMAT (UMAT_CSIC_RVE_ZHANG2022_V1_0.for):

  (1) KPROP_INTERP  -- temperature-dependent property multipliers,
  (2) KUNILAT       -- unilateral damage (crack closure),
  (3) KMACRO31      -- homogenised macro CDM with cycle-dependent damage.

Why this file exists
--------------------
No Abaqus solver is available here, so the RVE and the macro thermal-shock
models cannot be run.  What CAN be checked rigorously, and is checked here, is
that the point constitutive law behaves as designed:

  T1  interpolation is exact at the table nodes, linear between them, and
      CLAMPED outside (never extrapolated)
  T2  REGRESSION: with NT=0 and HCLO=0 the V3_0 yarn law reproduces the
      verified V1_0 yarn law to machine precision -- the new code cannot have
      broken the already-published verification
  T3  temperature multipliers scale stiffness and strength as documented
  T4  crack closure recovers exactly the HCLO fraction of stiffness in
      compression and leaves the stored damage history untouched
  T5  THE CENTRAL POINT OF THE THESIS MODEL: a history-variable CDM SHAKES
      DOWN -- after the first thermal cycle the damage stops growing, so
      N=1 and N=100 are indistinguishable.  With the cycle-damage law
      enabled the degradation continues.  Both are asserted numerically.
  T6  cycle damage is monotonic, bounded by DCYMAX, and the cycle-jump
      scheme (one increment representing many cycles) gives the same
      accumulated damage as explicitly resolved cycles.

It also runs a small CALIBRATION of the cycle-damage constant C against the
published residual-strength-after-thermal-shock data collected in
data/literature/, and writes the fitted value for use in the macro card.

Run:  python3 verification/verify_thermshock.py
Out:  verification/figures/cycle_damage_shakedown.png
      verification/figures/unilateral_closure.png
      PASS/FAIL report on stdout (exit code 1 on any failure)
"""
from __future__ import print_function

import os
import sys
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FIGDIR = os.path.join(HERE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

# Reuse the already-verified V1_0 kernels for the regression test (T2).
import verify_constitutive as vc

TOL = 1.0e-12
_FAILS = []


def check(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print("  [%s] %s%s" % (tag, name, ("  " + detail) if detail else ""))
    if not ok:
        _FAILS.append(name)
    return ok


def close(a, b, rtol=1.0e-10, atol=1.0e-12):
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


# ===========================================================================
# 1:1 translations of the new Fortran kernels
# ===========================================================================
def kprop_interp(Tq, table, nv):
    """KPROP_INTERP: piecewise-linear, CLAMPED outside the table.

    `table` is a list of rows [T, f1, ..., f_nv] with ascending T.
    An empty table (NT=0) returns all-ones, i.e. V1_0 behaviour.
    """
    f = [1.0] * nv
    nt = len(table)
    if nt <= 0:
        return f
    if nt == 1 or Tq <= table[0][0]:
        return [max(1.0e-6, v) for v in table[0][1:1 + nv]]
    if Tq >= table[-1][0]:
        return [max(1.0e-6, v) for v in table[-1][1:1 + nv]]
    for j in range(nt - 1):
        Ta, Tb = table[j][0], table[j + 1][0]
        if Ta <= Tq <= Tb:
            w = 0.0 if (Tb - Ta) <= 1.0e-12 else (Tq - Ta) / (Tb - Ta)
            return [max(1.0e-6, table[j][1 + k]
                        + w * (table[j + 1][1 + k] - table[j][1 + k]))
                    for k in range(nv)]
    return f


def _cutback(svn, dj, djmax, cuttrg, cutsaf, cutmxf, pmin, islot):
    """Mirror of the PNEWDT cutback bookkeeping (STATEV `islot`, 0-based).

    Inactive when max_djump <= 0, which is how the single-point cards are set;
    it is mirrored anyway so the Python and Fortran STATEV vectors can be
    compared element by element (see cross_check_fortran.py).
    """
    if djmax > 0.0 and dj > cuttrg * djmax:
        req = cutsaf * djmax / dj
        if cutmxf > 0.0:
            req = min(req, cutmxf)
        req = max(pmin, req)
        creq = svn[islot]
        if creq <= 0.0:
            creq = 1.0
        svn[islot] = min(creq, req)


def kunilat(epsn, d, hclo):
    """KUNILAT: damage deactivation when the crack closes."""
    deff = d if epsn >= 0.0 else d * (1.0 - hclo)
    return min(0.999, max(0.0, deff))


# ===========================================================================
# Yarn point law of V3_0 (KYARN31) = V1_0 + T-table + closure
# ===========================================================================
def yarn_point31(eps, sv, P, ttab=None, hclo=0.0, temp=23.0,
                 dtime=1.0, celent=0.03, enable=True, kstep=3):
    """Mirror of KYARN31.  `P` is the 38-slot V1_0 base card (1-based dict)."""
    E1, E2, E3 = P[2], P[3], P[4]
    n12, n13, n23 = P[5], P[6], P[7]
    G12, G13, G23 = P[8], P[9], P[10]
    Xt, Xc, Yt, Yc = P[11], P[12], P[13], P[14]
    S12, S13, S23 = P[15], P[16], P[17]
    A1t, A1c, Att, Atc = P[18], P[19], P[20], P[21]
    dmax1, dmaxt = P[22], P[23]
    eta = P[24]
    G1t, G1c, Gtt, Gtc = P[32], P[33], P[34], P[35]
    Xpo, rF, K1 = P[36], P[37], P[38]

    f = kprop_interp(temp, ttab or [], 6)
    E1 *= f[0]
    E2 *= f[1]
    E3 *= f[1]
    G12 *= f[2]
    G13 *= f[2]
    G23 *= f[2]
    Xt *= f[3]
    Xc *= f[3]
    Xpo *= f[3]
    K1 *= f[0]
    Yt *= f[4]
    Yc *= f[4]
    S12 *= f[5]
    S13 *= f[5]
    S23 *= f[5]

    C0 = vc.kortho(E1, E2, E3, n12, n13, n23, G12, G13, G23)
    se = C0.dot(eps)

    fi1t = fi1c = fitt = fitc = 0.0
    if se[0] >= 0.0:
        fi1t = math.sqrt((se[0] / Xt) ** 2 + (se[3] / S12) ** 2
                         + (se[4] / S13) ** 2)
    else:
        fi1c = abs(se[0]) / Xc
    sumt = se[1] + se[2]
    if sumt >= 0.0:
        term = ((sumt / Yt) ** 2 + (se[5] * se[5] - se[1] * se[2]) / S23 ** 2
                + (se[3] / S12) ** 2 + (se[4] / S13) ** 2)
        fitt = math.sqrt(max(0.0, term))
    else:
        term = (((Yc / (2.0 * S23)) ** 2 - 1.0) * sumt / Yc
                + (sumt / (2.0 * S23)) ** 2
                + (se[5] * se[5] - se[1] * se[2]) / S23 ** 2
                + (se[3] / S12) ** 2 + (se[4] / S13) ** 2)
        fitc = math.sqrt(max(0.0, term))

    d1t0 = min(dmax1, max(0.0, sv[0]))
    d1c0 = min(dmax1, max(0.0, sv[1]))
    dtt0 = min(dmaxt, max(0.0, sv[2]))
    dtc0 = min(dmaxt, max(0.0, sv[3]))
    r1t = max(sv[4], fi1t)
    r1c = max(sv[5], fi1c)
    rtt = max(sv[6], fitt)
    rtc = max(sv[7], fitc)
    d1t, d1c, dtt, dtc = d1t0, d1c0, dtt0, dtc0

    b1t = vc.kaband(Xt * Xt / (2.0 * E1) * celent, G1t, A1t)
    b1c = vc.kaband(Xc * Xc / (2.0 * E1) * celent, G1c, A1c)
    btt = vc.kaband(Yt * Yt / (2.0 * E2) * celent, Gtt, Att)
    btc = vc.kaband(Yc * Yc / (2.0 * E2) * celent, Gtc, Atc)

    if enable:
        gam = dtime / (eta + dtime) if eta > 0.0 else 1.0
        if Xpo > 0.0:
            tar = vc.kmix1t(r1t, b1t, E1, Xt, Xpo, rF, K1)
        else:
            tar = vc.kdamage_target(r1t, b1t, 1.0)
        tar = min(dmax1, tar)
        d1t = max(d1t0, d1t0 + gam * (tar - d1t0))
        d1c = max(d1c0, d1c0 + gam * (vc.kdamage_target(r1c, b1c, dmax1) - d1c0))
        dtt = max(dtt0, dtt0 + gam * (vc.kdamage_target(rtt, btt, dmaxt) - dtt0))
        dtc = max(dtc0, dtc0 + gam * (vc.kdamage_target(rtc, btc, dmaxt) - dtc0))

    d1 = min(0.999, max(0.0, 1.0 - (1.0 - d1t) * (1.0 - d1c)))
    dt = min(0.999, max(0.0, 1.0 - (1.0 - dtt) * (1.0 - dtc)))

    ds12 = 1.0 - (1.0 - d1) * (1.0 - dt)
    ds23 = 1.0 - (1.0 - dt) * (1.0 - dt)
    ds31 = 1.0 - (1.0 - dt) * (1.0 - d1)

    d1e = kunilat(eps[0], d1, hclo)
    dt2e = kunilat(eps[1], dt, hclo)
    dt3e = kunilat(eps[2], dt, hclo)

    CD = vc.kortho(E1 * (1 - d1e), E2 * (1 - dt2e), E3 * (1 - dt3e),
                   n12 * (1 - d1e), n13 * (1 - d1e), n23 * (1 - dt2e),
                   G12 * (1 - ds12), G13 * (1 - ds31), G23 * (1 - ds23))
    stress = CD.dot(eps)

    mode = 1 + int(np.argmax([r1t, r1c, rtt, rtc]))
    rfac = max(r1t, r1c, rtt, rtc)
    nclo = sum(1 for i in range(3) if eps[i] < 0.0)

    svn = list(sv)
    svn[0:4] = [d1t, d1c, dtt, dtc]
    svn[4:8] = [r1t, r1c, rtt, rtc]
    svn[8], svn[9] = d1, dt
    svn[10] = float(mode)
    if sv[11] == 0.0 and rfac >= 1.0:
        svn[11] = temp
    if len(svn) >= 17:
        svn[16] = float(nclo)
    dj = max(abs(d1t - d1t0), abs(d1c - d1c0),
             abs(dtt - dtt0), abs(dtc - dtc0))
    _cutback(svn, dj, P[25], max(1.0, P[29]), P[30], P[31], P[27], 13)
    if dj > sv[12]:
        svn[12] = dj
        svn[14] = temp
        svn[15] = rfac
    return stress, CD, svn


# ===========================================================================
# Macro point law (KMACRO31)
# ===========================================================================
def macro_card(E1=105000.0, E2=105000.0, E3=52000.0,
               n12=0.10, n13=0.25, n23=0.25,
               G12=36000.0, G13=22000.0, G23=22000.0,
               Xt=220.0, Xc=480.0, Yt=220.0, Yc=480.0,
               S12=110.0, S13=90.0, S23=90.0,
               A=2.0, dmax1=0.99, dmaxt=0.99, eta=0.0,
               hclo=0.0, cycon=0.0, C=0.0, n=4.0, k=1.0,
               rth=0.30, dcymax=0.95, w1=0.30,
               cycrate=0.0, predefn=0, ttab=None):
    """Build the 47+8*NT slot MACRO card as a 1-based dict.

    DEFAULT ELASTIC/STRENGTH VALUES ARE PLACEHOLDERS.  They are of the right
    order for a 2D plain-weave C/SiC laminate but are NOT yet the homogenised
    values -- those come from the RVE virtual tests (abaqus/make_rve_virtual_
    tests.py -> postprocess/homogenize.py) once Abaqus has run the RVE.
    """
    ttab = ttab or []
    P = {}
    P[1] = 3.0
    P[2], P[3], P[4] = E1, E2, E3
    P[5], P[6], P[7] = n12, n13, n23
    P[8], P[9], P[10] = G12, G13, G23
    P[11], P[12], P[13], P[14] = Xt, Xc, Yt, Yc
    P[15], P[16], P[17] = S12, S13, S23
    P[18] = P[19] = P[20] = P[21] = A
    P[22], P[23] = dmax1, dmaxt
    P[24] = eta
    P[25] = 0.0          # max_djump (cutback control; inactive at a point)
    P[26] = 1.0e6        # freeze_step
    P[27] = 0.01         # min PNEWDT
    P[28] = 1.0          # enable
    P[29], P[30], P[31] = 1.0, 0.5, 1.0
    P[32] = P[33] = P[34] = P[35] = 0.0   # Gf = 0 -> fixed A
    P[36] = 31.0         # card key
    P[37] = hclo
    P[38] = cycon
    P[39], P[40], P[41] = C, n, k
    P[42], P[43], P[44] = rth, dcymax, w1
    P[45] = cycrate
    P[46] = float(predefn)
    P[47] = float(len(ttab))
    slot = 48
    for row in ttab:
        for v in row:
            P[slot] = v
            slot += 1
    return P, ttab


def macro_point(eps, sv, P, ttab=None, temp=23.0, dtime=1.0, rate=None,
                celent=1.0, enable=True):
    """Mirror of KMACRO31.  Returns (stress, C_secant, sv_new)."""
    E1, E2, E3 = P[2], P[3], P[4]
    n12, n13, n23 = P[5], P[6], P[7]
    G12, G13, G23 = P[8], P[9], P[10]
    Xt, Xc, Yt, Yc = P[11], P[12], P[13], P[14]
    S12, S13, S23 = P[15], P[16], P[17]
    A1t, A1c, Att, Atc = P[18], P[19], P[20], P[21]
    dmax1, dmaxt = P[22], P[23]
    eta = P[24]
    G1t, G1c, Gtt, Gtc = P[32], P[33], P[34], P[35]
    hclo = min(1.0, max(0.0, P[37]))
    cycon = P[38]
    C, nexp, kexp = P[39], P[40], P[41]
    rth = P[42]
    dcymax = min(0.99, max(0.0, P[43]))
    w1 = min(1.0, max(0.0, P[44]))
    cycrat = P[45]

    f = kprop_interp(temp, ttab or [], 7)
    E1 *= f[0]
    E2 *= f[1]
    E3 *= f[1]
    G12 *= f[2]
    G13 *= f[2]
    G23 *= f[2]
    Xt *= f[3]
    Xc *= f[3]
    Yt *= f[4]
    Yc *= f[4]
    S12 *= f[5]
    S13 *= f[5]
    S23 *= f[5]
    C *= f[6]

    C0 = vc.kortho(E1, E2, E3, n12, n13, n23, G12, G13, G23)
    se = C0.dot(eps)

    fi1t = fi1c = fitt = fitc = 0.0
    if se[0] >= 0.0:
        fi1t = math.sqrt((se[0] / Xt) ** 2 + (se[3] / S12) ** 2
                         + (se[4] / S13) ** 2)
    else:
        fi1c = abs(se[0]) / Xc
    sumt = se[1] + se[2]
    if sumt >= 0.0:
        term = ((sumt / Yt) ** 2 + (se[5] * se[5] - se[1] * se[2]) / S23 ** 2
                + (se[3] / S12) ** 2 + (se[4] / S13) ** 2)
        fitt = math.sqrt(max(0.0, term))
    else:
        term = (((Yc / (2.0 * S23)) ** 2 - 1.0) * sumt / Yc
                + (sumt / (2.0 * S23)) ** 2
                + (se[5] * se[5] - se[1] * se[2]) / S23 ** 2
                + (se[3] / S12) ** 2 + (se[4] / S13) ** 2)
        fitc = math.sqrt(max(0.0, term))

    d1t0 = min(dmax1, max(0.0, sv[0]))
    d1c0 = min(dmax1, max(0.0, sv[1]))
    dtt0 = min(dmaxt, max(0.0, sv[2]))
    dtc0 = min(dmaxt, max(0.0, sv[3]))
    r1t = max(sv[4], fi1t)
    r1c = max(sv[5], fi1c)
    rtt = max(sv[6], fitt)
    rtc = max(sv[7], fitc)
    d1t, d1c, dtt, dtc = d1t0, d1c0, dtt0, dtc0
    dcy0 = min(dcymax, max(0.0, sv[16]))
    dcy = dcy0

    b1t = vc.kaband(Xt * Xt / (2.0 * E1) * celent, G1t, A1t)
    b1c = vc.kaband(Xc * Xc / (2.0 * E1) * celent, G1c, A1c)
    btt = vc.kaband(Yt * Yt / (2.0 * E2) * celent, Gtt, Att)
    btc = vc.kaband(Yc * Yc / (2.0 * E2) * celent, Gtc, Atc)

    if enable:
        gam = dtime / (eta + dtime) if eta > 0.0 else 1.0
        d1t = max(d1t0, d1t0 + gam * (vc.kdamage_target(r1t, b1t, dmax1) - d1t0))
        d1c = max(d1c0, d1c0 + gam * (vc.kdamage_target(r1c, b1c, dmax1) - d1c0))
        dtt = max(dtt0, dtt0 + gam * (vc.kdamage_target(rtt, btt, dmaxt) - dtt0))
        dtc = max(dtc0, dtc0 + gam * (vc.kdamage_target(rtc, btc, dmaxt) - dtc0))

    d1m = min(0.999, max(0.0, 1.0 - (1.0 - d1t) * (1.0 - d1c)))
    dtm = min(0.999, max(0.0, 1.0 - (1.0 - dtt) * (1.0 - dtc)))

    rfac = max(r1t, r1c, rtt, rtc)
    rdrv = max(fi1t, fi1c, fitt, fitc)

    dninc = 0.0
    if cycon > 0.5 and enable:
        rr = rate if rate is not None else cycrat
        if rr is not None and rr > 0.0 and dtime > 0.0:
            dninc = rr * dtime
            exc = rdrv - rth
            if exc > 0.0 and C > 0.0:
                ddcy = C * (exc ** nexp) * ((1.0 - dcy0) ** (-kexp)) * dninc
                ddcy = max(0.0, min(ddcy, dcymax))
                dcy = min(dcymax, dcy0 + ddcy)

    d1 = min(0.999, max(0.0, 1.0 - (1.0 - d1m) * (1.0 - w1 * dcy)))
    dt = min(0.999, max(0.0, 1.0 - (1.0 - dtm) * (1.0 - dcy)))

    ds12 = 1.0 - (1.0 - d1) * (1.0 - dt)
    ds23 = 1.0 - (1.0 - dt) * (1.0 - dt)
    ds31 = 1.0 - (1.0 - dt) * (1.0 - d1)

    d1e = kunilat(eps[0], d1, hclo)
    dt2e = kunilat(eps[1], dt, hclo)
    dt3e = kunilat(eps[2], dt, hclo)

    CD = vc.kortho(E1 * (1 - d1e), E2 * (1 - dt2e), E3 * (1 - dt3e),
                   n12 * (1 - d1e), n13 * (1 - d1e), n23 * (1 - dt2e),
                   G12 * (1 - ds12), G13 * (1 - ds31), G23 * (1 - ds23))
    stress = CD.dot(eps)

    svn = list(sv)
    svn[0:4] = [d1t, d1c, dtt, dtc]
    svn[4:8] = [r1t, r1c, rtt, rtc]
    svn[8], svn[9] = d1, dt
    svn[10] = float(1 + int(np.argmax([r1t, r1c, rtt, rtc])))
    if sv[11] == 0.0 and rfac >= 1.0:
        svn[11] = temp
    svn[16] = dcy
    svn[17] = sv[17] + dninc
    svn[18] = rdrv
    svn[19], svn[20] = d1m, dtm
    svn[21] = float(sum(1 for i in range(3) if eps[i] < 0.0))
    dj = max(abs(d1t - d1t0), abs(d1c - d1c0), abs(dtt - dtt0),
             abs(dtc - dtc0), abs(dcy - dcy0))
    _cutback(svn, dj, P[25], max(1.0, P[29]), P[30], P[31], P[27], 13)
    if dj > sv[12]:
        svn[12] = dj
        svn[14] = temp
        svn[15] = rfac
    return stress, CD, svn


def new_sv(n=22):
    return [0.0] * n


# ===========================================================================
# Drivers
# ===========================================================================
def thermal_cycle(P, ttab, ncycle, eps_hot, eps_cold, sv=None,
                  nsub=20, rate=None, dtime_cycle=1.0, temp_hot=1000.0,
                  temp_cold=200.0, record=True):
    """Drive the macro point through `ncycle` biaxial thermal-strain cycles.

    One cycle ramps the in-plane biaxial mechanical strain from `eps_cold`
    (compressive, hot/reheated state) up to `eps_hot` (tensile, quenched
    surface) and back, with the temperature ramped in step.  This is the
    single-point stand-in for the surface of a quenched specimen; the real
    strain history comes from the transient heat-transfer analysis.

    `rate` is cycles per unit time: rate*dtime_cycle = cycles represented by
    one simulated cycle.  rate = 1/dtime_cycle -> explicitly resolved cycles;
    larger -> CYCLE JUMP.
    """
    sv = list(sv) if sv is not None else new_sv()
    hist = {"N": [], "dcyc": [], "dt": [], "d1": [], "Esec": []}
    dt_inc = dtime_cycle / (2.0 * nsub)
    E2_0 = P[3]
    for c in range(ncycle):
        legs = (np.linspace(eps_cold, eps_hot, nsub + 1)[1:],
                np.linspace(eps_hot, eps_cold, nsub + 1)[1:])
        temps = (np.linspace(temp_cold, temp_hot, nsub + 1)[1:],
                 np.linspace(temp_hot, temp_cold, nsub + 1)[1:])
        for leg, tl in zip(legs, temps):
            for e, T in zip(leg, tl):
                eps = np.array([e, e, 0.0, 0.0, 0.0, 0.0])
                _, CD, sv = macro_point(eps, sv, P, ttab, temp=T,
                                        dtime=dt_inc, rate=rate)
        if record:
            hist["N"].append(sv[17] if sv[17] > 0 else float(c + 1))
            hist["dcyc"].append(sv[16])
            hist["dt"].append(sv[9])
            hist["d1"].append(sv[8])
            # secant transverse modulus probed at zero strain state
            hist["Esec"].append(E2_0 * (1.0 - sv[9]) / E2_0)
    return sv, hist


def residual_strength(P, ttab, sv, direction=1, temp=23.0,
                      eps_max=0.02, nsteps=400):
    """Virtual monotonic tension to failure from the current damage state.

    Cycle damage is frozen during the test (rate=0): a strength test is
    instantaneous compared with the thermal-shock history.
    """
    svl = list(sv)
    peak = 0.0
    for e in np.linspace(0.0, eps_max, nsteps + 1)[1:]:
        eps = np.zeros(6)
        eps[direction] = e
        s, _, svl = macro_point(eps, svl, P, ttab, temp=temp,
                                dtime=1.0, rate=0.0)
        peak = max(peak, s[direction])
    return peak


# ===========================================================================
# Tests
# ===========================================================================
def t1_interpolation():
    print("\nT1  KPROP_INTERP -- nodes, linearity, clamping")
    tab = [[23.0, 1.00, 1.00],
           [500.0, 0.90, 0.80],
           [1000.0, 0.75, 0.55]]
    ok = True
    ok &= check("NT=0 returns unity", kprop_interp(500.0, [], 3) == [1.0] * 3)
    f = kprop_interp(23.0, tab, 2)
    ok &= check("exact at first node", close(f[0], 1.00) and close(f[1], 1.00))
    f = kprop_interp(500.0, tab, 2)
    ok &= check("exact at interior node", close(f[0], 0.90) and close(f[1], 0.80))
    f = kprop_interp(1000.0, tab, 2)
    ok &= check("exact at last node", close(f[0], 0.75) and close(f[1], 0.55))
    f = kprop_interp(750.0, tab, 2)
    ok &= check("linear midway", close(f[0], 0.825) and close(f[1], 0.675),
                "f=(%.4f, %.4f) ref=(0.8250, 0.6750)" % (f[0], f[1]))
    f = kprop_interp(-200.0, tab, 2)
    ok &= check("CLAMPED below table (no extrapolation)",
                close(f[0], 1.00) and close(f[1], 1.00))
    f = kprop_interp(3000.0, tab, 2)
    ok &= check("CLAMPED above table (no extrapolation)",
                close(f[0], 0.75) and close(f[1], 0.55))
    return ok


def t2_v10_regression():
    print("\nT2  REGRESSION -- V3_0 yarn law == verified V1_0 yarn law "
          "(NT=0, HCLO=0)")
    P = yarn_card_v2()
    # verify_constitutive.py indexes PROPS 0-based (P[k] = Fortran P(k+1)).
    Pv = [P[i + 1] for i in range(38)]
    worst = 0.0
    for eps_amp in (2.0e-4, 8.0e-4, 2.0e-3, -1.5e-3):
        for mode in range(6):
            eps = np.zeros(6)
            eps[mode] = eps_amp
            s_ref = vc.yarn_point(eps, [0.0] * 16, Pv)[0]
            s_new, _, _ = yarn_point31(eps, [0.0] * 16, P, ttab=[], hclo=0.0)
            for a, b in zip(s_ref, s_new):
                worst = max(worst, abs(a - b))
    return check("V1_0 stresses reproduced to machine precision",
                 worst < 1.0e-9, "max |dsigma| = %.3e MPa" % worst)


def yarn_card_v2():
    """V2_0 yarn card, 1-based like the Fortran PROPS (CALIBRATION_GUIDE.md)."""
    P = {}
    P[1] = 2.0
    P[2], P[3], P[4] = 254967.228042, 44321.737572, 44321.737572
    P[5], P[6], P[7] = 0.247516386, 0.247516386, 0.395813581
    P[8], P[9], P[10] = 26431.515264, 26431.515264, 15876.667974
    P[11], P[12], P[13], P[14] = 2835.0, 1956.0, 80.0, 350.0
    P[15], P[16], P[17] = 120.0, 120.0, 100.0
    P[18] = P[19] = P[20] = P[21] = 2.0
    P[22], P[23] = 0.99, 0.99
    P[24], P[25] = 0.02, 0.0
    P[26], P[27], P[28] = 1.0e6, 0.01, 1.0
    P[29], P[30], P[31] = 1.0, 0.5, 1.0
    P[32], P[33] = 12.5, 12.5
    P[34], P[35] = 0.0, 0.0
    P[36], P[37], P[38] = 700.0, 3.0, 8000.0
    return P


def _scaled_yarn_card(fE1, fE2, fG, fX, fY, fS):
    """The V2_0 yarn card with the multipliers applied BY HAND.

    The temperature table must produce exactly this card.  Comparing against a
    hand-scaled card is the right test: checking a stress ratio would not work
    because C11 is not proportional to E1 alone (the compliance inversion mixes
    all nine constants).
    """
    P = dict(yarn_card_v2())
    P[2] *= fE1
    P[3] *= fE2
    P[4] *= fE2
    P[8] *= fG
    P[9] *= fG
    P[10] *= fG
    P[11] *= fX
    P[12] *= fX
    P[13] *= fY
    P[14] *= fY
    P[15] *= fS
    P[16] *= fS
    P[17] *= fS
    P[36] *= fX          # X_PO is a stress
    P[38] *= fE1         # K1 is a stiffness
    return P


def t3_temperature_scaling():
    print("\nT3  temperature multipliers == hand-scaled card")
    P = yarn_card_v2()
    f1000 = (0.80, 0.70, 0.75, 0.90, 0.60, 0.65)
    ttab = [[23.0, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
            [1000.0] + list(f1000)]
    # T = 511.5 is exactly halfway between the two table nodes.
    fmid = tuple(1.0 + 0.5 * (v - 1.0) for v in f1000)

    ok = True
    for T, f, lab in ((23.0, (1.0,) * 6, "at the first node"),
                      (1000.0, f1000, "at the last node"),
                      (511.5, fmid, "interpolated midway"),
                      (2500.0, f1000, "clamped above the table")):
        Pref = _scaled_yarn_card(*f)
        worst = 0.0
        for eps_amp in (3.0e-4, 1.2e-3, -9.0e-4):
            for mode in range(6):
                eps = np.zeros(6)
                eps[mode] = eps_amp
                a = yarn_point31(eps, [0.0] * 16, Pref, ttab=[], temp=T)[0]
                b = yarn_point31(eps, [0.0] * 16, P, ttab=ttab, temp=T)[0]
                worst = max(worst, max(abs(x - y) for x, y in zip(a, b)))
        ok &= check("f(T) applied exactly %s (T=%.1f C)" % (lab, T),
                    worst < 1.0e-9, "max |dsigma| = %.3e MPa" % worst)
    return ok


def t4_unilateral():
    print("\nT4  unilateral crack closure")
    P, ttab = macro_card(hclo=0.8)
    # Damage the point in transverse tension.
    sv = new_sv()
    for e in np.linspace(0.0, 4.0e-3, 200)[1:]:
        eps = np.array([0.0, e, 0.0, 0.0, 0.0, 0.0])
        _, _, sv = macro_point(eps, sv, P, ttab)
    dt_stored = sv[9]
    ok = check("damage was generated", dt_stored > 0.05,
               "d_T = %.4f" % dt_stored)

    epr = np.array([0.0, +1.0e-4, 0.0, 0.0, 0.0, 0.0])
    _, C_open, sv_o = macro_point(epr, sv, P, ttab, rate=0.0)
    epc = np.array([0.0, -1.0e-4, 0.0, 0.0, 0.0, 0.0])
    _, C_clo, sv_c = macro_point(epc, sv, P, ttab, rate=0.0)

    # Direct check on the deactivation rule itself.
    d_open = kunilat(+1.0, dt_stored, 0.8)
    d_clos = kunilat(-1.0, dt_stored, 0.8)
    ok &= check("closed-crack damage = d*(1-HCLO)",
                close(d_clos, dt_stored * 0.2),
                "d_open=%.6f  d_closed=%.6f" % (d_open, d_clos))
    ok &= check("closing recovers stiffness", C_clo[1, 1] > C_open[1, 1],
                "C22 open=%.1f closed=%.1f MPa" % (C_open[1, 1], C_clo[1, 1]))
    ok &= check("damage history unchanged by closure",
                close(sv_c[9], sv_o[9]) and close(sv_c[2], sv_o[2]),
                "d_T stored = %.6f both ways" % sv_c[9])

    P0, _ = macro_card(hclo=0.0)
    _, C_clo0, _ = macro_point(epc, sv, P0, ttab, rate=0.0)
    ok &= check("HCLO=0 gives no recovery (V1_0 behaviour)",
                close(C_clo0[1, 1], C_open[1, 1]),
                "C22 = %.1f MPa" % C_clo0[1, 1])
    return ok


#: Equibiaxial in-plane strain amplitudes standing in for the quenched-surface
#: state.  eps_hot gives a peak failure index of ~1.17, i.e. just past static
#: initiation, which is the regime a thermal shock actually produces.
EPS_HOT, EPS_COLD, NCYC_DEMO = 2.05e-3, -0.6e-3, 60
C_DEMO = 2.0e-2

#: Under equibiaxial strain the 3-D Hashin transverse-tension index is largely
#: cancelled by its (sig6^2 - sig2*sig3)/S23^2 term, so the LONGITUDINAL mode
#: dominates.  d1 (STATEV 9) is therefore the mode to watch in this demo.


def t5_shakedown():
    print("\nT5  SHAKEDOWN vs CYCLE DAMAGE  (the reason KMACRO31 exists)")
    ncyc = NCYC_DEMO

    P_off, tt = macro_card(cycon=0.0)
    _, h_off = thermal_cycle(P_off, tt, ncyc, EPS_HOT, EPS_COLD,
                             rate=1.0, dtime_cycle=1.0)
    P_on, tt = macro_card(cycon=1.0, C=C_DEMO, n=3.0, k=1.0, rth=0.30)
    _, h_on = thermal_cycle(P_on, tt, ncyc, EPS_HOT, EPS_COLD,
                            rate=1.0, dtime_cycle=1.0)

    d_off, d_on = h_off["d1"], h_on["d1"]
    drift_off = abs(d_off[-1] - d_off[1])
    growth_on = d_on[-1] - d_on[1]

    ok = check("monotonic CDM damages on cycle 1", d_off[0] > 1.0e-3,
               "d_1(N=1) = %.4f" % d_off[0])
    ok &= check("monotonic CDM SHAKES DOWN after cycle 1 "
                "(N=2..%d identical)" % ncyc,
                drift_off < 1.0e-12,
                "d_1(N=2)=%.6f  d_1(N=%d)=%.6f  drift=%.2e"
                % (d_off[1], ncyc, d_off[-1], drift_off))
    ok &= check("cycle law keeps degrading", growth_on > 0.02,
                "d_1: %.4f (N=2) -> %.4f (N=%d)"
                % (d_on[1], d_on[-1], ncyc))
    ok &= check("cycle damage is monotonically increasing",
                all(b >= a - 1e-15 for a, b in zip(h_on["dcyc"][:-1],
                                                   h_on["dcyc"][1:])))
    ok &= check("cycle damage respects the DCYMAX cap",
                max(h_on["dcyc"]) <= 0.95 + 1e-12,
                "max d_cyc = %.4f" % max(h_on["dcyc"]))
    return ok, h_off, h_on


def t6_cycle_jump():
    print("\nT6  cycle jump -- one increment representing many cycles")
    eps_hot, eps_cold = EPS_HOT, EPS_COLD
    kw = dict(cycon=1.0, C=6.0e-3, n=3.0, k=0.0, rth=0.30)
    P, tt = macro_card(**kw)

    # 40 explicitly resolved cycles.
    sv_ex, _ = thermal_cycle(P, tt, 40, eps_hot, eps_cold,
                             rate=1.0, dtime_cycle=1.0)
    # 4 simulated cycles, each representing 10 -> same 40 cycles.
    sv_jp, _ = thermal_cycle(P, tt, 4, eps_hot, eps_cold,
                             rate=10.0, dtime_cycle=1.0)

    ok = check("both routes accumulate 40 cycles",
               close(sv_ex[17], 40.0, rtol=1e-9)
               and close(sv_jp[17], 40.0, rtol=1e-9),
               "N_explicit=%.3f  N_jump=%.3f" % (sv_ex[17], sv_jp[17]))
    rel = abs(sv_jp[16] - sv_ex[16]) / max(1e-12, sv_ex[16])
    ok &= check("k=0 -> cycle jump is EXACT (linear accumulation)",
                rel < 1.0e-10,
                "d_cyc explicit=%.6f jump=%.6f  rel.err=%.2e"
                % (sv_ex[16], sv_jp[16], rel))

    # With k>0 the law is nonlinear in d_cyc, so a jump introduces a
    # controllable integration error -- quantify it rather than assert zero.
    P2, tt2 = macro_card(cycon=1.0, C=6.0e-3, n=3.0, k=1.0, rth=0.30)
    sv_ex2, _ = thermal_cycle(P2, tt2, 40, eps_hot, eps_cold,
                              rate=1.0, dtime_cycle=1.0)
    sv_jp2, _ = thermal_cycle(P2, tt2, 4, eps_hot, eps_cold,
                              rate=10.0, dtime_cycle=1.0)
    rel2 = abs(sv_jp2[16] - sv_ex2[16]) / max(1e-12, sv_ex2[16])
    ok &= check("k>0 -> jump error stays small and is reported",
                rel2 < 0.05,
                "d_cyc explicit=%.6f jump(x10)=%.6f  rel.err=%.2f %%"
                % (sv_ex2[16], sv_jp2[16], 100.0 * rel2))
    return ok


LITDIR = os.path.join(os.path.dirname(HERE), "data", "literature")


def load_literature():
    """Read the published anchors from data/literature/csic_thermal_shock.csv.

    Only rows the source was actually checked for (`confidence` != secondary)
    are used as calibration anchors.
    """
    path = os.path.join(LITDIR, "csic_thermal_shock.csv")
    rows = []
    with open(path) as fh:
        header = None
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = _split_csv(line)
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    anchors = {"modulus": []}
    for r in rows:
        if r.get("confidence") == "secondary":
            continue
        # PRIMARY target: 2D C/SiC residual MODULUS vs cycles (same material and
        # same observable as the macro model).  Everything else is secondary.
        if (r.get("source_key") == "ZHANG2013"
                and r.get("property") == "tensile_modulus" and r.get("ratio")):
            anchors["modulus"].append((int(r["cycles"]), float(r["ratio"])))
        if r.get("property") == "flexural_strength" and r.get("ratio"):
            anchors["ratio"] = float(r["ratio"])
            anchors["ratio_N"] = int(r["cycles"])
            anchors["ratio_src"] = r["source_key"]
        if r.get("property") == "critical_cycles":
            anchors["Ncrit"] = int(r["cycles"])
            anchors["Ncrit_src"] = r["source_key"]
    anchors["modulus"].sort()
    return anchors, rows


def _split_csv(line):
    out, cur, q = [], "", False
    for ch in line:
        if ch == '"':
            q = not q
        elif ch == "," and not q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def modulus_curve(P, tt, checkpoints):
    """Residual in-plane modulus ratio E1(N)/E1(0) = 1 - d1 at each checkpoint."""
    sv = new_sv()
    done = 0
    out = []
    for N in checkpoints:
        if N > done:
            sv, _ = thermal_cycle(P, tt, N - done, EPS_HOT, EPS_COLD,
                                  rate=1.0, dtime_cycle=1.0, sv=sv,
                                  record=False)
            done = N
        out.append(1.0 - sv[8])
    return out


def calibrate_to_literature():
    """Calibrate the cycle-damage law against the 2D C/SiC modulus data.

    PRIMARY TARGET CHANGED (2026-07).  The earlier two-anchor fit used YIN2002,
    which is 3-D C/SiC air-quenched 1300->300 C and SATURATES after ~50 cycles.
    ZHANG2013 (refs/[03]) is the better target for this thesis: 2-D C/SiC, CVI,
    T-300 plain weave -- the same material -- and it reports the residual
    MODULUS, which is what the macro model predicts.  Its behaviour is the
    opposite of YIN2002:

        N      0     20     40     60
        E/E0  1.00  0.821  0.755  0.474      <- accelerating, no plateau
        mass   0    -0.5%  -3.3%  -9.8%      <- oxidation, accelerating

    The paper attributes the mass loss to oxidation of the carbon fibres and
    PyC interphase and notes it tracks the strength loss.  So the SIGN of the
    cycle-damage exponent is not a free choice, it is set by which mechanism
    dominates:

        k < 0  saturating   crack-density saturation   YIN2002, 3-D, no mass loss
        k > 0  accelerating oxidation ingress          ZHANG2013, 2-D, -9.8 % mass

    Both regimes are real and the model spans them.  The 2-D case is ours, so
    the default flips to k > 0.

    Fit procedure: ONE parameter (C) to ONE point (N=60), then the N=20 and
    N=40 points are PREDICTIONS, not fits, and are reported as such.
    """
    print("\nCALIBRATION  cycle-damage law vs the 2D C/SiC modulus data")
    anchors, _ = load_literature()
    data = anchors["modulus"]
    if not data:
        print("    no ZHANG2013 modulus rows found -- skipped")
        return None
    Nfit, Rfit = data[-1]
    print("    target: E/E0 = %.3f at N = %d  [ZHANG2013, 2D C/SiC]"
          % (Rfit, Nfit))
    print("    (YIN2002 3D saturates instead -- see the docstring; both are in"
          "\n     data/literature/csic_thermal_shock.csv)")

    NEXP, KEXP, RTH = 3.0, 1.0, 0.30      # k > 0: oxidation-driven acceleration

    def ratio_at(C, N):
        P, t2 = macro_card(cycon=1.0, C=C, n=NEXP, k=KEXP, rth=RTH,
                           dcymax=0.95)
        sv, _ = thermal_cycle(P, t2, N, EPS_HOT, EPS_COLD, rate=1.0,
                              dtime_cycle=1.0, record=False)
        return 1.0 - sv[8]

    lo, hi = 1.0e-5, 5.0
    if ratio_at(hi, Nfit) > Rfit:
        print("    WARNING: target not reachable in the bracket; using its end.")
        C = hi
    else:
        for _ in range(30):
            mid = math.sqrt(lo * hi)
            if ratio_at(mid, Nfit) > Rfit:
                lo = mid
            else:
                hi = mid
        C = math.sqrt(lo * hi)

    print("    fitted C     = %.4e   (n = %.1f, k = %+.1f, RTH = %.2f held)"
          % (C, NEXP, KEXP, RTH))
    print("    N     model   data    (only N=%d was fitted)" % Nfit)
    for N, R in data:
        m = ratio_at(C, N)
        tag = "  <- fitted" if N == Nfit else ""
        print("    %3d   %.3f   %.3f%s" % (N, m, R, tag))
    print("    NOTE: this is a SINGLE-POINT calibration with an assumed strain")
    print("    amplitude, so the level is indicative only.  The real fit runs on")
    print("    the structural model where the strain history comes from the")
    print("    transient thermal analysis.")
    # The N=20 gap is informative rather than a failure: it says the assumed
    # single-point amplitude puts too much damage in on the FIRST cycle.
    m0 = ratio_at(C, 1)
    d20 = [r for n, r in data if n == 20]
    if d20:
        print("    DIAGNOSTIC: model loses %.0f %% of stiffness on cycle 1 alone,"
              % (100.0 * (1.0 - m0)))
        print("    while the data has lost only %.0f %% by N=20.  EPS_HOT = %.2e"
              % (100.0 * (1.0 - d20[0]), EPS_HOT))
        print("    is therefore too severe for this material.  Useful target for")
        print("    the structural model: the quenched-surface strain amplitude")
        print("    should give roughly 10-15 %% first-cycle stiffness loss.")
    return dict(C=C, n=NEXP, k=KEXP, rth=RTH, dcymax=0.95,
                s0=None, anchors=anchors, data=data)


# ===========================================================================
# Figures
# ===========================================================================
def strength_curve(P, tt, checkpoints, s0):
    """Residual strength ratio at each N in `checkpoints` (ascending)."""
    sv = new_sv()
    done = 0
    out = []
    for N in checkpoints:
        if N > done:
            sv, _ = thermal_cycle(P, tt, N - done, EPS_HOT, EPS_COLD,
                                  rate=1.0, dtime_cycle=1.0, sv=sv,
                                  record=False)
            done = N
        out.append(residual_strength(P, tt, sv) / s0)
    return out


def figure_shakedown(h_off, h_on, cal):
    fig, ax = plt.subplots(1, 2, figsize=(11.4, 4.3))
    N = np.arange(1, len(h_off["d1"]) + 1)

    ax[0].plot(N, h_off["d1"], "o-", ms=3, color="#B04A3A",
               label="monotonic CDM only (CYCON=0)")
    ax[0].plot(N, h_on["d1"], "s-", ms=3, color="#2E6E8E",
               label="+ cycle damage (CYCON=1)")
    ax[0].set_xlabel("thermal cycle N")
    ax[0].set_ylabel(r"in-plane damage $d_1$")
    ax[0].set_title("(a) Shakedown of a history-variable CDM")
    ax[0].legend(fontsize=8, loc="center right")
    ax[0].grid(alpha=0.3)
    ax[0].annotate("damage frozen after cycle 1:\nN=1 and N=60 identical",
                   xy=(34, h_off["d1"][33]), xytext=(3, 0.3955),
                   fontsize=8, color="#B04A3A",
                   arrowprops=dict(arrowstyle="->", color="#B04A3A", lw=0.8))

    chk = [0, 2, 5, 10, 20, 30, 40, 50, 60, 70]
    P_off, tt = macro_card(cycon=0.0)
    P_on, tt2 = macro_card(cycon=1.0, C=cal["C"], n=cal["n"], k=cal["k"],
                           rth=cal["rth"], dcymax=cal["dcymax"])
    r_off = modulus_curve(P_off, tt, chk)
    r_on = modulus_curve(P_on, tt2, chk)

    ax[1].plot(chk, r_off, "o-", ms=3.5, color="#B04A3A",
               label="CYCON=0 (shakes down)")
    ax[1].plot(chk, r_on, "s-", ms=3.5, color="#2E6E8E",
               label="CYCON=1, calibrated (k>0, oxidation)")
    dN = [d[0] for d in cal["data"]]
    dR = [d[1] for d in cal["data"]]
    ax[1].plot(dN, dR, "k*", ms=13, ls="none", zorder=5,
               label="ZHANG2013 2D C/SiC (refs/[03])")
    ax[1].set_xlabel("thermal cycle N")
    ax[1].set_ylabel(r"residual modulus $\bar{E}_1(N)/\bar{E}_1(0)$")
    ax[1].set_title("(b) Calibration against 2D C/SiC data")
    ax[1].set_ylim(0.0, 1.05)
    ax[1].legend(fontsize=7.5, loc="lower left")
    ax[1].grid(alpha=0.3)

    fig.suptitle("Why the macro law needs cycle-dependent damage "
                 "(single material point)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = os.path.join(FIGDIR, "cycle_damage_shakedown.png")
    fig.savefig(p, dpi=130)
    plt.close(fig)
    print("\n  figure -> %s" % p)


def figure_unilateral():
    P, tt = macro_card(hclo=0.8)
    sv = new_sv()
    e_up = np.linspace(0.0, 4.0e-3, 200)
    rec_e, rec_s = [], []
    for e in e_up[1:]:
        eps = np.array([0.0, e, 0.0, 0.0, 0.0, 0.0])
        s, _, sv = macro_point(eps, sv, P, tt)
        rec_e.append(e)
        rec_s.append(s[1])
    sv_top = list(sv)

    e_dn = np.linspace(4.0e-3, -2.0e-3, 300)
    for hclo, col, lab in ((0.0, "#B04A3A", "HCLO = 0 (no closure)"),
                           (0.8, "#2E6E8E", "HCLO = 0.8"),
                           (1.0, "#3F7A4A", "HCLO = 1 (full recovery)")):
        Pc, _ = macro_card(hclo=hclo)
        svl = list(sv_top)
        ee, ss = [], []
        for e in e_dn:
            eps = np.array([0.0, e, 0.0, 0.0, 0.0, 0.0])
            s, _, svl = macro_point(eps, svl, Pc, tt, rate=0.0)
            ee.append(e)
            ss.append(s[1])
        plt.plot(np.array(ee) * 100.0, ss, color=col, lw=1.6, label=lab)

    plt.plot(np.array(rec_e) * 100.0, rec_s, color="0.35", lw=1.6,
             label="loading (damage generated)")
    plt.axhline(0.0, color="0.6", lw=0.8)
    plt.axvline(0.0, color="0.6", lw=0.8)
    plt.xlabel(r"transverse strain $\varepsilon_{22}$  [%]")
    plt.ylabel(r"$\sigma_{22}$  [MPa]")
    plt.title("Unilateral effect: stiffness recovery on crack closure")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    p = os.path.join(FIGDIR, "unilateral_closure.png")
    plt.savefig(p, dpi=130)
    plt.close()
    print("  figure -> %s" % p)


# ===========================================================================
def main():
    print("=" * 72)
    print("verify_thermshock.py -- V3_0 feature verification "
          "(no Abaqus required)")
    print("=" * 72)

    t1_interpolation()
    t2_v10_regression()
    t3_temperature_scaling()
    t4_unilateral()
    _, h_off, h_on = t5_shakedown()
    t6_cycle_jump()

    cal = calibrate_to_literature()

    figure_shakedown(h_off, h_on, cal)
    figure_unilateral()

    print("\n" + "=" * 72)
    if _FAILS:
        print("OVERALL: %d CHECK(S) FAILED -> %s" % (len(_FAILS),
                                                     ", ".join(_FAILS)))
        print("=" * 72)
        return 1
    print("OVERALL: ALL V3_0 FEATURE CHECKS PASS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
