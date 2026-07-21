#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_constitutive.py
======================
Stand-alone, single-material-point re-implementation of the ZHANG2022 UMAT
routines KYARN30 (yarn) and KMTRX30 (matrix) from

    src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for

Its only purpose is *code verification*: it reproduces, in Python, exactly the
same equations the Fortran UMAT evaluates, so that

  (1) the damage-initiation criteria (Hashin Eqs. 11-14, von Mises Eqs. 15-16),
  (2) the damage-evolution laws (exponential Eqs. 17/19, mixed-law Eq. 18), and
  (3) the compliance-based stiffness degradation,

can be exercised, unit-checked against the closed-form paper equations, and
plotted as constituent stress-strain curves *without* needing Abaqus.

This is NOT the RVE homogenisation - the macroscopic composite response of the
paper (Table 3) comes from the woven RVE solved in Abaqus with the UMAT. Here we
verify that the *point constitutive law* the UMAT applies is the paper's law.

Reference: Q. Zhang et al., Ceramics International 48 (2022) 3109-3124.
Model equations deferred by Zhang to Ref.[17] = Ge et al., CST 157 (2018) 86-98.

Run:  python3 verify_constitutive.py
Out:  verification/figures/*.png   and a PASS/FAIL unit-test report on stdout.
"""
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(HERE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

# Abaqus 3-D solid strain/stress order: (11, 22, 33, 12, 13, 23), engineering shears.

# ----------------------------------------------------------------------------
# Low-level kernels -- 1:1 translation of the Fortran helper subroutines.
# ----------------------------------------------------------------------------
def kortho(E1, E2, E3, n12, n13, n23, G12, G13, G23):
    """Orthotropic stiffness from the compliance inverse (KORTHO)."""
    S = np.zeros((6, 6))
    s11, s22, s33 = 1.0 / E1, 1.0 / E2, 1.0 / E3
    s12, s13, s23 = -n12 / E1, -n13 / E1, -n23 / E2
    det = (s11 * s22 * s33 + 2.0 * s12 * s13 * s23
           - s11 * s23 * s23 - s22 * s13 * s13 - s33 * s12 * s12)
    if det <= 1.0e-30:
        raise ValueError("Invalid orthotropic elastic constants; det=%g" % det)
    C = np.zeros((6, 6))
    C[0, 0] = (s22 * s33 - s23 * s23) / det
    C[1, 1] = (s11 * s33 - s13 * s13) / det
    C[2, 2] = (s11 * s22 - s12 * s12) / det
    C[0, 1] = C[1, 0] = (s13 * s23 - s12 * s33) / det
    C[0, 2] = C[2, 0] = (s12 * s23 - s13 * s22) / det
    C[1, 2] = C[2, 1] = (s12 * s13 - s11 * s23) / det
    C[3, 3] = G12
    C[4, 4] = G13
    C[5, 5] = G23
    return C


def kmises(s):
    """von Mises equivalent stress (KMISES)."""
    return math.sqrt(max(0.0, 0.5 * ((s[0] - s[1]) ** 2 + (s[1] - s[2]) ** 2
                                     + (s[2] - s[0]) ** 2)
                         + 3.0 * (s[3] ** 2 + s[4] ** 2 + s[5] ** 2)))


def kdamage_target(r, A, dmax):
    """Exponential damage evolution  d = 1 - exp[A(1-r)]/r  (Zhang Eqs. 17 & 19)."""
    if r <= 1.0:
        return 0.0
    d = 1.0 - math.exp(A * (1.0 - r)) / r
    return min(dmax, max(0.0, d))


def kmix1t(r, A, E1, Xt, Xpo, rF, K1):
    """Mixed linear-exponential law for yarn longitudinal tension (Zhang Eq. 18
    with the auxiliary variables of Ge Eqs. 16-17)."""
    if r <= 1.0:
        return 0.0
    c1 = 1.0 + K1 / E1
    rL = max(1.0, min(r, rF))
    dL = c1 * (1.0 - 1.0 / rL)
    dF = c1 * (1.0 - 1.0 / rF)
    rE = max(1.0, (1.0 - dF) * (Xt / Xpo) * r)
    d = 1.0 - (1.0 - dL) / rE * math.exp(A * (1.0 - rE))
    return min(0.999, max(0.0, d))


def kaband(g0le, Gf, Afix):
    """Crack-band softening factor (Ge Eqs. 19-21 closed form)."""
    if Gf <= 0.0:
        return Afix
    if Gf > 1.02 * g0le:
        A = 2.0 * g0le / (Gf - g0le)
    else:
        A = 50.0
    return min(50.0, max(1.0e-2, A))


# ----------------------------------------------------------------------------
# Yarn point routine -- faithful translation of KYARN30.
# ----------------------------------------------------------------------------
def yarn_point(eps, sv, P, dtime=1.0, celent=0.03, enable=True, kstep=3):
    E1, E2, E3 = P[1], P[2], P[3]
    n12, n13, n23 = P[4], P[5], P[6]
    G12, G13, G23 = P[7], P[8], P[9]
    XT, XC, YT, YC = P[10], P[11], P[12], P[13]
    S12, S13, S23 = P[14], P[15], P[16]
    A1T, A1C, ATT, ATC = P[17], P[18], P[19], P[20]
    DMAX1, DMAXT = P[21], P[22]
    ETA = P[23]
    FREEZE = P[25]
    G1T, G1C, GTT, GTC = P[31], P[32], P[33], P[34]
    XPO, RFT, XK1 = P[35], P[36], P[37]

    C0 = kortho(E1, E2, E3, n12, n13, n23, G12, G13, G23)
    SE = C0.dot(eps)                       # effective stress  s~ = C0 : eps

    # 3-D Hashin criteria on the effective stress (Zhang Eqs. 11-14).
    FI1T = FI1C = FITT = FITC = 0.0
    if SE[0] >= 0.0:
        FI1T = math.sqrt((SE[0] / XT) ** 2 + (SE[3] / S12) ** 2 + (SE[4] / S13) ** 2)
    else:
        FI1C = abs(SE[0]) / XC
    sumt = SE[1] + SE[2]
    if sumt >= 0.0:
        term = ((sumt / YT) ** 2 + (SE[5] * SE[5] - SE[1] * SE[2]) / (S23 * S23)
                + (SE[3] / S12) ** 2 + (SE[4] / S13) ** 2)
        FITT = math.sqrt(max(0.0, term))
    else:
        term = (((YC / (2.0 * S23)) ** 2 - 1.0) * sumt / YC + (sumt / (2.0 * S23)) ** 2
                + (SE[5] * SE[5] - SE[1] * SE[2]) / (S23 * S23)
                + (SE[3] / S12) ** 2 + (SE[4] / S13) ** 2)
        FITC = math.sqrt(max(0.0, term))

    d1t0 = max(0.0, min(DMAX1, sv[0]))
    d1c0 = max(0.0, min(DMAX1, sv[1]))
    dtt0 = max(0.0, min(DMAXT, sv[2]))
    dtc0 = max(0.0, min(DMAXT, sv[3]))
    R1T = max(sv[4], FI1T)
    R1C = max(sv[5], FI1C)
    RTT = max(sv[6], FITT)
    RTC = max(sv[7], FITC)
    d1t, d1c, dtt, dtc = d1t0, d1c0, dtt0, dtc0

    B1T = kaband(XT * XT / (2.0 * E1) * celent, G1T, A1T)
    B1C = kaband(XC * XC / (2.0 * E1) * celent, G1C, A1C)
    BTT = kaband(YT * YT / (2.0 * E2) * celent, GTT, ATT)
    BTC = kaband(YC * YC / (2.0 * E2) * celent, GTC, ATC)

    if enable and float(kstep) <= FREEZE:
        gam = dtime / (ETA + dtime) if ETA > 0.0 else 1.0
        if XPO > 0.0:
            tar = kmix1t(R1T, B1T, E1, XT, XPO, RFT, XK1)
        else:
            tar = kdamage_target(R1T, B1T, 1.0)
        tar = min(DMAX1, tar)
        d1t = max(d1t0, d1t0 + gam * (tar - d1t0))
        tar = kdamage_target(R1C, B1C, DMAX1); d1c = max(d1c0, d1c0 + gam * (tar - d1c0))
        tar = kdamage_target(RTT, BTT, DMAXT); dtt = max(dtt0, dtt0 + gam * (tar - dtt0))
        tar = kdamage_target(RTC, BTC, DMAXT); dtc = max(dtc0, dtc0 + gam * (tar - dtc0))

    d1 = 1.0 - (1.0 - d1t) * (1.0 - d1c)
    dT = 1.0 - (1.0 - dtt) * (1.0 - dtc)
    d1 = min(0.999, max(0.0, d1))
    dT = min(0.999, max(0.0, dT))
    ds12 = 1.0 - (1.0 - d1) * (1.0 - dT)
    ds23 = 1.0 - (1.0 - dT) * (1.0 - dT)
    ds31 = 1.0 - (1.0 - dT) * (1.0 - d1)

    CD = kortho(E1 * (1.0 - d1), E2 * (1.0 - dT), E3 * (1.0 - dT),
                n12 * (1.0 - d1), n13 * (1.0 - d1), n23 * (1.0 - dT),
                G12 * (1.0 - ds12), G13 * (1.0 - ds31), G23 * (1.0 - ds23))
    stress = CD.dot(eps)

    sv_new = sv.copy()
    sv_new[0:8] = [d1t, d1c, dtt, dtc, R1T, R1C, RTT, RTC]
    sv_new[8], sv_new[9] = d1, dT
    diag = dict(FI1T=FI1T, FI1C=FI1C, FITT=FITT, FITC=FITC,
                d1t=d1t, d1c=d1c, dtt=dtt, dtc=dtc, d1=d1, dT=dT, SE=SE.copy())
    return stress, CD, sv_new, diag


# ----------------------------------------------------------------------------
# Matrix point routine -- faithful translation of KMTRX30.
# ----------------------------------------------------------------------------
def matrix_point(eps, sv, P, dtime=1.0, celent=0.03, enable=True, kstep=3):
    E, nu = P[1], P[2]
    XT, XC = P[3], P[4]
    AT, AC = P[5], P[6]
    DMAXT, DMAXC = P[7], P[8]
    ETA = P[9]
    FREEZE = P[11]
    GMT, GMC = P[14], P[15]
    SY0, HISO = P[16], P[17]
    G = E / (2.0 * (1.0 + nu))

    epl = sv[14:20].copy()
    pbar = sv[8]
    C0 = kortho(E, E, E, nu, nu, nu, G, G, G)
    eel = eps - epl
    STR = C0.dot(eel)

    # von Mises radial return in effective-stress space (Ge Eqs. 8-9).
    if SY0 > 0.0 and enable and float(kstep) <= FREEZE:
        qtr = kmises(STR)
        sy = SY0 + HISO * pbar
        if qtr > sy:
            dlam = (qtr - sy) / (3.0 * G + HISO)
            pbar += dlam
            pm = (STR[0] + STR[1] + STR[2]) / 3.0
            sd = np.array([STR[0] - pm, STR[1] - pm, STR[2] - pm, STR[3], STR[4], STR[5]])
            fac = 1.5 * dlam / qtr
            for i in range(3):
                epl[i] += fac * sd[i]
            for i in range(3, 6):
                epl[i] += 2.0 * fac * sd[i]
            eel = eps - epl
            STR = C0.dot(eel)

    q = kmises(STR)
    ai1 = STR[0] + STR[1] + STR[2]
    FIT = q / XT if ai1 >= 0.0 else 0.0
    FIC = q / XC if ai1 < 0.0 else 0.0

    dt0 = max(0.0, min(DMAXT, sv[0]))
    dc0 = max(0.0, min(DMAXC, sv[1]))
    RT = max(sv[2], FIT)
    RC = max(sv[3], FIC)
    dtn, dcn = dt0, dc0
    BT = kaband(XT * XT / (2.0 * E) * celent, GMT, AT)
    BC = kaband(XC * XC / (2.0 * E) * celent, GMC, AC)
    if enable and float(kstep) <= FREEZE:
        gam = dtime / (ETA + dtime) if ETA > 0.0 else 1.0
        tar = kdamage_target(RT, BT, DMAXT); dtn = max(dt0, dt0 + gam * (tar - dt0))
        tar = kdamage_target(RC, BC, DMAXC); dcn = max(dc0, dc0 + gam * (tar - dc0))

    dact = dtn if ai1 >= 0.0 else dcn
    dact = min(0.999, max(0.0, dact))
    CD = kortho(E * (1 - dact), E * (1 - dact), E * (1 - dact),
                nu * (1 - dact), nu * (1 - dact), nu * (1 - dact),
                G * (1 - dact), G * (1 - dact), G * (1 - dact))
    stress = CD.dot(eel)

    sv_new = sv.copy()
    sv_new[0], sv_new[1], sv_new[2], sv_new[3] = dtn, dcn, RT, RC
    sv_new[4] = dact
    sv_new[8] = pbar
    sv_new[14:20] = epl
    diag = dict(FIT=FIT, FIC=FIC, dact=dact, q=q, I1=ai1, pbar=pbar)
    return stress, CD, sv_new, diag


# ----------------------------------------------------------------------------
# Uniaxial-stress driver (lateral strains solved so sigma_j = 0, j != load dir).
# ----------------------------------------------------------------------------
def uniaxial_stress(point_fn, P, load_dir, eps_target, nsteps, nsv):
    free = [j for j in range(6) if j != load_dir]
    eps = np.zeros(6)
    sv = np.zeros(nsv)
    hist = {"eps": [0.0], "sig": [0.0], "sv": [sv.copy()], "diag": [None]}
    for k in range(1, nsteps + 1):
        eps[load_dir] = eps_target * k / nsteps
        # Newton on the free strains so that stress[free] == 0.
        for _ in range(30):
            stress, CT, sv_new, diag = point_fn(eps, sv, P)
            r = stress[free]
            if np.linalg.norm(r) < 1.0e-8 * (1.0 + abs(stress[load_dir])):
                break
            Kff = CT[np.ix_(free, free)]
            try:
                deps = np.linalg.solve(Kff, -r)
            except np.linalg.LinAlgError:
                deps = -r / (np.diag(Kff) + 1.0e-12)
            eps[free] += deps
        sv = sv_new
        hist["eps"].append(eps[load_dir])
        hist["sig"].append(stress[load_dir])
        hist["sv"].append(sv.copy())
        hist["diag"].append(diag)
    return hist


# ----------------------------------------------------------------------------
# Material cards -- read straight from the V1_0 Abaqus input file.
# PROPS are 0-indexed here (P[0] = phase id), matching props[k]=P(k+1) in Fortran.
# ----------------------------------------------------------------------------
YARN = [1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.247516386,
        0.395813581, 26431.515264, 26431.515264, 15876.667974, 1200.0, 1500.0,
        80.0, 350.0, 120.0, 120.0, 100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02,
        0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
MATRIX = [2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99, 0.99, 0.02, 0.10,
          3.0, 0.25, 1.0, 0.031, 0.031, 0.0, 0.0, 1.15, 0.75, 0.50, 30.0]


# ----------------------------------------------------------------------------
# Unit tests: the coded kernels must equal the closed-form paper equations.
# ----------------------------------------------------------------------------
def unit_tests():
    print("=" * 70)
    print("UNIT TESTS  (coded UMAT kernels  vs  closed-form paper equations)")
    print("=" * 70)
    ok = True

    # (1) Exponential law Eq.17/19: d = 1 - exp[A(1-r)]/r
    for A, r in [(2.0, 1.5), (0.32, 3.0), (5.0, 1.01)]:
        ref = 1.0 - math.exp(A * (1.0 - r)) / r
        got = kdamage_target(r, A, 0.999)
        ref = min(0.999, max(0.0, ref))
        good = abs(got - ref) < 1e-12
        ok &= good
        print(f"  Eq.17/19 A={A:4} r={r:4}:  code={got:.6f} ref={ref:.6f}  "
              f"{'PASS' if good else 'FAIL'}")

    # (2) von Mises Eq.15/16 numerator against explicit tensor form.
    s = np.array([120.0, -40.0, 15.0, 30.0, -10.0, 22.0])
    ref = math.sqrt(s[0]**2 + s[1]**2 + s[2]**2 - s[0]*s[1] - s[1]*s[2] - s[0]*s[2]
                    + 3*(s[3]**2 + s[4]**2 + s[5]**2))
    got = kmises(s)
    good = abs(got - ref) < 1e-9
    ok &= good
    print(f"  Eq.15/16 vonMises        :  code={got:.5f} ref={ref:.5f}  "
          f"{'PASS' if good else 'FAIL'}")

    # (3) Hashin fiber tension Eq.11 at a known effective-stress state.
    P = YARN
    se = np.array([1000.0, 0, 0, 60.0, 30.0, 0.0])
    ref = math.sqrt((se[0]/P[10])**2 + (se[3]/P[14])**2 + (se[4]/P[15])**2)
    C0 = kortho(P[1], P[2], P[3], P[4], P[5], P[6], P[7], P[8], P[9])
    eps = np.linalg.solve(C0, se)                       # strain giving this s~
    _, _, _, diag = yarn_point(eps, np.zeros(16), P, enable=False)
    good = abs(diag["FI1T"] - ref) < 1e-6 * ref
    ok &= good
    print(f"  Eq.11 Hashin fiber-tens  :  code={diag['FI1T']:.6f} ref={ref:.6f}  "
          f"{'PASS' if good else 'FAIL'}")

    # (4) Hashin transverse tension Eq.13.
    se = np.array([0.0, 60.0, 20.0, 15.0, 10.0, 25.0])
    ref = math.sqrt(((se[1]+se[2])/P[12])**2 + (se[5]**2 - se[1]*se[2])/P[16]**2
                    + (se[3]/P[14])**2 + (se[4]/P[15])**2)
    eps = np.linalg.solve(C0, se)
    _, _, _, diag = yarn_point(eps, np.zeros(16), P, enable=False)
    good = abs(diag["FITT"] - ref) < 1e-6 * ref
    ok &= good
    print(f"  Eq.13 Hashin trans-tens  :  code={diag['FITT']:.6f} ref={ref:.6f}  "
          f"{'PASS' if good else 'FAIL'}")

    # (5) Crack-band factor closed form Eq.19-21 (Ge): A = 2 g0 le /(Gf - g0 le).
    g0le, Gf = 0.00428, 0.031
    ref = 2.0 * g0le / (Gf - g0le)
    got = kaband(g0le, Gf, 2.0)
    good = abs(got - ref) < 1e-9
    ok &= good
    print(f"  Eq.19-21 crack-band A     :  code={got:.6f} ref={ref:.6f}  "
          f"{'PASS' if good else 'FAIL'}")

    print("-" * 70)
    print("OVERALL:", "ALL KERNELS REPRODUCE THE PAPER EQUATIONS  ->  PASS"
          if ok else "  ***  FAIL  ***")
    print("=" * 70 + "\n")
    return ok


# ----------------------------------------------------------------------------
# Constituent stress-strain curves (single material point, uniaxial stress).
# ----------------------------------------------------------------------------
def constituent_curves():
    # --- Yarn: longitudinal (1) and transverse (2) tension + compression ---
    cases = [
        ("Yarn longitudinal tension  (mode 1t, Hashin Eq.11 + Eq.17)", YARN, 0,  0.010, yarn_point, 16, "d1"),
        ("Yarn transverse tension    (mode 2t, Hashin Eq.13 + Eq.17)", YARN, 1,  0.010, yarn_point, 16, "dT"),
        ("Yarn longitudinal compress (mode 1c, Hashin Eq.12 + Eq.17)", YARN, 0, -0.012, yarn_point, 16, "d1"),
        ("Yarn transverse compress   (mode 2c, Hashin Eq.14 + Eq.17)", YARN, 1, -0.012, yarn_point, 16, "dT"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (title, P, d, em, fn, nsv, dkey) in zip(axes.flat, cases):
        h = uniaxial_stress(fn, P, d, em, 400, nsv)
        eps = np.array(h["eps"]) * 100.0                 # %
        sig = np.array(h["sig"])
        dvar = [0.0] + [dg[dkey] for dg in h["diag"][1:]]
        ax.plot(eps, sig, "b-", lw=2, label=r"$\sigma$")
        ax.set_xlabel("strain (%)"); ax.set_ylabel("stress (MPa)", color="b")
        ax.tick_params(axis="y", colors="b")
        ax.set_title(title, fontsize=9)
        ax2 = ax.twinx()
        ax2.plot(eps, dvar, "r--", lw=1.5, label="damage d")
        ax2.set_ylabel("damage variable", color="r"); ax2.set_ylim(0, 1.05)
        ax2.tick_params(axis="y", colors="r")
        peak = sig[np.argmax(np.abs(sig))]
        ax.axhline(0, color="k", lw=0.5)
        ax.text(0.03, 0.92, f"peak = {peak:8.1f} MPa", transform=ax.transAxes,
                fontsize=8, va="top",
                bbox=dict(boxstyle="round", fc="w", ec="0.7"))
    fig.suptitle("Yarn constituent constitutive response (UMAT KYARN30, single point)\n"
                 "elastic-brittle with 3-D Hashin initiation + exponential softening",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(FIGDIR, "yarn_constitutive.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("wrote", p)

    # --- Matrix: uniaxial tension and compression ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for ax, (title, d, em) in zip(
            axes, [("Matrix tension  (Eq.15 + Eq.19, Xm,t=310)", 0, 0.004),
                   ("Matrix compression  (Eq.16 + Eq.19, Xm,c=310)", 0, -0.004)]):
        h = uniaxial_stress(matrix_point, MATRIX, d, em, 400, 20)
        eps = np.array(h["eps"]) * 100.0
        sig = np.array(h["sig"])
        dvar = [0.0] + [dg["dact"] for dg in h["diag"][1:]]
        ax.plot(eps, sig, "b-", lw=2)
        ax.set_xlabel("strain (%)"); ax.set_ylabel("stress (MPa)", color="b")
        ax.tick_params(axis="y", colors="b"); ax.set_title(title, fontsize=9)
        ax.axhline(0, color="k", lw=0.5)
        ax2 = ax.twinx(); ax2.plot(eps, dvar, "r--", lw=1.5)
        ax2.set_ylabel("damage d", color="r"); ax2.set_ylim(0, 1.05)
        ax2.tick_params(axis="y", colors="r")
        peak = sig[np.argmax(np.abs(sig))]
        ax.text(0.03, 0.92, f"peak = {peak:7.1f} MPa", transform=ax.transAxes,
                fontsize=8, va="top", bbox=dict(boxstyle="round", fc="w", ec="0.7"))
    fig.suptitle("SiC matrix constitutive response (UMAT KMTRX30, single point)\n"
                 "isotropic von-Mises-initiated damage (plasticity off: SY0=0 in card)",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    p = os.path.join(FIGDIR, "matrix_constitutive.png")
    fig.savefig(p, dpi=130); plt.close(fig)
    print("wrote", p)


def main():
    ok = unit_tests()
    constituent_curves()
    print("Verification figures in:", FIGDIR)
    print("Constitutive-law verification:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
