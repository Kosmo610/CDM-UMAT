#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
knob_sensitivity.py -- the GUIDE 2 table, made quantitative, and what it pins
==============================================================================
The calibration has more free directions than targets: 8 knobs (Yt, Yc, S12,
S23, X_PO, K1, SY0, HISO) plus the two switched-off transverse fracture
energies (Gtt, Gtc) against 3 strength targets (128.45 / 179.42 / 199.15 MPa)
and curve-shape features.  verification/CALIBRATION_GUIDE.md 2 says WHICH knob
moves WHICH observable, qualitatively.  This script computes the actual
numbers at the material-point level, using the verified Python mirror
(verify_constitutive.py) as the only constitutive engine, and then runs an
SVD on the resulting Jacobian so that under-determination becomes a measured,
regression-gated finding instead of a hidden weakness.

WHAT IS COMPUTED
  Part 1  12 single-point observables that proxy the macro ones of GUIDE 2
          (each carries its proxy mapping and the RVE-redistribution caveat).
  Part 2  normalized sensitivities S_ij = (dO_i/dp_j) * (p_j / O_i), central
          finite differences at the V2_0 starting card, TWO relative steps
          (1e-3 and 2e-3) so FD noise is itself measured.  Written to
          verification/knob_sensitivity.csv with value+basis+verdict columns.
  Part 3  SVD of the Jacobian, (a) restricted to the 3 strength-proxy rows,
          (b) all rows: singular values, numerical rank, condition number of
          the live subspace, per-knob pinned fraction, and the 4-dim
          (rF derived) vs 5-dim (rF free) comparison.
  Part 4  --check: the regression gate (structural zeros, GUIDE-2 sign
          directions, Ge Eq.(17) rF derivation, CSV/guide-snapshot
          regeneration, FD-step stability).

rF IS NOT A COLUMN.  Ge refs/[24] Eq. (17) fixes the linear-to-exponential
transition from X_PO and K1 (refs/GE2018_EXTRACTION.md B-2; check_card_ranges
slot 37 verdict DERIVED).  On the linear branch sigma = Xt*(1+K1/E1) - K1*eps
*E1/Xt ... i.e. stress falls from Xt with slope -K1 in strain, so it reaches
X_PO exactly at

    rF = 1 + (E1/K1) * (1 - X_PO/Xt)

and this script computes rF from the perturbed X_PO and K1 on every
evaluation (chain rule included).  The old card's free rF = 3.0 contradicts
that transition point and makes the damage law JUMP at onset; both facts are
demonstrated numerically in the checks.

Run:  python3 verification/knob_sensitivity.py            # tables + CSV
      python3 verification/knob_sensitivity.py --check    # regression gate
"""
from __future__ import print_function

import os
import sys

import numpy as np

_trapz = getattr(np, "trapezoid", getattr(np, "trapz", None))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from verify_constitutive import (yarn_point, matrix_point, kortho, kaband,
                                 kmix1t)                        # noqa: E402
from verify_fullmodel import YARN_V2, MATRIX_V2                 # noqa: E402

CSV_PATH = os.path.join(HERE, "knob_sensitivity.csv")
GUIDE_PATH = os.path.join(HERE, "CALIBRATION_GUIDE.md")
SNAP_BEGIN = "<!-- knob_sensitivity:snapshot:begin -->"
SNAP_END = "<!-- knob_sensitivity:snapshot:end -->"

# --------------------------------------------------------------------------
# knob inventory (task order).  slot indices are 0-based mirror-card indices.
# S12 moves slots 14 AND 15: the card keeps S13 = S12 (transverse isotropy),
# so a calibration move of "S12" moves both -- documented in the CSV basis.
# Gtt/Gtc sit at 0 (crack band OFF): a RELATIVE step at p = 0 is the zero
# step, so their normalized (logarithmic) sensitivity at the card is zero BY
# STRUCTURE; the ON-state identifiability is measured separately (Part 3).
# --------------------------------------------------------------------------
KNOBS = [
    ("Yt", "yarn", (12,)), ("Yc", "yarn", (13,)),
    ("S12", "yarn", (14, 15)), ("S23", "yarn", (16,)),
    ("X_PO", "yarn", (35,)), ("K1", "yarn", (37,)),
    ("SY0", "matrix", (16,)), ("HISO", "matrix", (17,)),
    ("Gtt", "yarn", (33,)), ("Gtc", "yarn", (34,)),
]
KNOB_NAMES = [k[0] for k in KNOBS]

G_TT_SHI = 0.107        # N/mm, Shi refs/[31] -- the one sourced ON-value

# 12 observables, with the macro observable each one proxies (GUIDE 2).
# CAVEAT that applies to every row: a single material point cannot redistribute
# load.  RVE-level redistribution (matrix->yarn handoff after cooldown damage,
# crack-band localisation driving single elements deep past onset) is measured
# in the Stage runs, NOT here.  These rows rank knob leverage; they do not
# predict macro magnitudes.
OBSERVABLES = [
    ("y1t_peak",   "yarn 1t peak stress = stress at FI1T=1 corner [MPa]",
     "ultimate strength (T1000 undamaged limit, GUIDE 2 row 3)"),
    ("y1t_eps_pk", "yarn 1t strain at the peak corner [-]",
     "strain at which the macro curve tops out"),
    ("y1t_eps80",  "yarn 1t strain at 80% peak, post-peak [-]",
     "failure strain / tail length (GUIDE 2 row 4)"),
    ("y1t_Wd09",   "yarn 1t dissipated energy to d1t=0.9 [MPa]",
     "softening-tail energy -> ultimate strength + failure strain"),
    ("y2t_Wd05",   "yarn 2t dissipated energy to dT=0.5, "
                   "constrained (strain-controlled) [MPa]",
     "transverse softening -- the branch Gtt regularises when ON"),
    ("on2t_uni",   "yarn 2t uniaxial onset stress [MPa]",
     "nonlinearity onset (GUIDE 2 row 2)"),
    ("on2t_biax",  "yarn 2t equibiaxial onset stress [MPa]",
     "cooled-state pre-damage: TRS is near-equibiaxial transverse "
     "(GUIDE 2 row 1, initial slope)"),
    ("on12",       "yarn in-plane shear onset stress [MPa]",
     "shear-driven nonlinearity onset (GUIDE 2 row 2)"),
    ("on23",       "yarn transverse shear onset stress [MPa]",
     "transverse shear pre-damage (GUIDE 2 row 1)"),
    ("on2c",       "yarn transverse compression onset stress [MPa]",
     "compressive pre-damage after cooldown"),
    ("m_peak",     "matrix tension peak stress = stress at FIT=1 corner [MPa]",
     "matrix contribution to strength (GUIDE 2 row 5)"),
    ("m_eps_pk",   "matrix strain at the peak corner [-]",
     "curve-shape knee: where the matrix branch tops out (GUIDE 2 row 5)"),
    ("m_resid",    "matrix residual strain after load-unload [-]",
     "permanent strain of the unloading loop (GUIDE 2 row 5)"),
]
OBS_NAMES = [o[0] for o in OBSERVABLES]
STRENGTH_ROWS = ["y1t_peak", "on2t_biax", "m_peak"]

H1, H2 = 1.0e-3, 2.0e-3        # the two relative FD steps

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s]  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# rF derived from X_PO and K1 (Ge Eq. 17; refs/GE2018_EXTRACTION.md B-2)
# --------------------------------------------------------------------------
def rf_derived(E1, Xt, Xpo, K1):
    if Xpo <= 0.0 or Xpo >= Xt or K1 <= 0.0:
        return 1.0
    return 1.0 + (E1 / K1) * (1.0 - Xpo / Xt)


def yarn_card(pset, free_rf=None):
    P = list(YARN_V2)
    for name, phase, slots in KNOBS:
        if phase == "yarn":
            for s in slots:
                P[s] = pset[name]
    P[36] = rf_derived(P[1], P[10], P[35], P[37]) if free_rf is None else free_rf
    return P


def matrix_card(pset):
    P = list(MATRIX_V2)
    for name, phase, slots in KNOBS:
        if phase == "matrix":
            for s in slots:
                P[s] = pset[name]
    return P


def base_pset():
    p = {}
    for name, phase, slots in KNOBS:
        card = YARN_V2 if phase == "yarn" else MATRIX_V2
        p[name] = card[slots[0]]
    return p


# --------------------------------------------------------------------------
# drivers (reuse the mirror's point functions; only the path logic is here)
# --------------------------------------------------------------------------
def _path(point_fn, P, load_dir, targets, nsv):
    """Uniaxial-stress strain path: lateral strains Newton-solved to zero
    lateral stress at every step (same scheme as uniaxial_stress, but the
    loaded strain follows an arbitrary path so unloading is possible)."""
    eps = np.zeros(6)
    sv = np.zeros(nsv)
    free = [j for j in range(6) if j != load_dir]
    E, S, SV, DG = [0.0], [0.0], [sv.copy()], [None]
    for t in targets:
        eps[load_dir] = t
        for _ in range(40):
            stress, CT, sv_new, diag = point_fn(eps, sv, P)
            r = stress[free]
            if np.linalg.norm(r) < 1.0e-9 * (1.0 + abs(stress[load_dir])):
                break
            Kff = CT[np.ix_(free, free)]
            try:
                deps = np.linalg.solve(Kff, -r)
            except np.linalg.LinAlgError:
                deps = -r / (np.diag(Kff) + 1.0e-12)
            eps[free] += deps
        sv = sv_new
        E.append(eps[load_dir])
        S.append(stress[load_dir])
        SV.append(sv.copy())
        DG.append(diag)
    return np.array(E), np.array(S), SV, DG


def _sweep_strain(point_fn, P, load_dir, targets, nsv):
    """Fully strain-controlled sweep: only the loaded strain component moves,
    all others are held at zero (a constrained material point, as a yarn
    inside the RVE is).  No lateral Newton, hence no snap-back: the
    transverse-tension equilibrium path under uniaxial STRESS control jumps
    at onset (the softening branch snaps), which turns every derived
    observable into a staircase -- measured, not assumed, 2026-08-11."""
    eps = np.zeros(6)
    sv = np.zeros(nsv)
    E, S, SV = [0.0], [0.0], [sv.copy()]
    for t in targets:
        eps[load_dir] = t
        stress, _CT, sv, _diag = point_fn(eps, sv, P)
        E.append(t)
        S.append(stress[load_dir])
        SV.append(sv.copy())
    return np.array(E), np.array(S), SV


def _corner(E, S, DG, key):
    """Exact stress/strain at the damage-onset corner: the last pre-onset
    state is elastic( -proportional in FI for the yarn), so the FI = 1
    crossing is interpolated in FI -- smooth in the parameters, and free of
    the grid jitter a discrete argmax or parabola fit produces."""
    fi = np.array([0.0] + [d[key] for d in DG[1:]])
    idx = np.where(fi >= 1.0)[0]
    if len(idx) == 0:
        raise RuntimeError("criterion %s never reached 1 in sweep" % key)
    k = idx[0]
    f = (1.0 - fi[k - 1]) / (fi[k] - fi[k - 1])
    e_star = E[k - 1] + f * (E[k] - E[k - 1])
    s_star = S[k - 1] / fi[k - 1]      # elastic proportionality below onset
    return s_star, e_star


def _dissipated_to(E, S, dvals, dcrit):
    """Work integral minus recoverable (secant) energy, up to the interpolated
    strain where the damage variable crosses dcrit.  Both endpoint terms are
    interpolated, so the observable is continuous in the parameters."""
    d = np.array(dvals)
    idx = np.where(d >= dcrit)[0]
    if len(idx) == 0:
        raise RuntimeError("damage %.2f not reached in sweep (max %.3f)"
                           % (dcrit, d.max()))
    i = idx[0]
    if i == 0:
        raise RuntimeError("damage crossed dcrit at the first step")
    f = (dcrit - d[i - 1]) / (d[i] - d[i - 1])
    e_star = E[i - 1] + f * (E[i] - E[i - 1])
    s_star = S[i - 1] + f * (S[i] - S[i - 1])
    W = _trapz(S[:i], E[:i])
    W += 0.5 * (S[i - 1] + s_star) * (e_star - E[i - 1])
    return W - 0.5 * s_star * e_star, e_star


def _onset(P, sigma_dir, crit, probe=1.0):
    """Onset stress for a proportional stress path s * sigma_dir.
    The Hashin indices are quadratic polynomials in the load scale
    (FI^2 = a*lam + b*lam^2), so two elastic evaluations of the MIRROR's own
    criterion code give the exact crossing FI = 1 -- no stepping noise.
    `probe` is the first evaluation scale; compression needs a large one
    because its (clamped) quadratic goes positive only at finite load."""
    C0 = kortho(P[1], P[2], P[3], P[4], P[5], P[6], P[7], P[8], P[9])
    vals = []
    for lam in (probe, 2.0 * probe):
        eps = np.linalg.solve(C0, lam * np.asarray(sigma_dir, dtype=float))
        _s, _C, _sv, diag = yarn_point(eps, np.zeros(16), P)
        fi = max(diag[c] for c in crit)
        vals.append(fi * fi)
    a = (4.0 * vals[0] - vals[1]) / (2.0 * probe)
    b = (vals[1] - 2.0 * vals[0]) / (2.0 * probe * probe)
    if abs(b) < 1e-30:
        return 1.0 / a
    lam = (-a + np.sqrt(a * a + 4.0 * b)) / (2.0 * b)
    return lam                      # |sigma_dir| = 1 MPa, so onset = lam MPa


# --------------------------------------------------------------------------
# the 12 observables
# --------------------------------------------------------------------------
_MEMO = {}


def observables(pset, free_rf=None):
    Py = yarn_card(pset, free_rf=free_rf)
    Pm = matrix_card(pset)
    key = (tuple(Py), tuple(Pm))
    if key in _MEMO:
        return _MEMO[key]
    O = {}

    # yarn 1t sweep (600 steps to 12 % strain: covers eps80 and d=0.9)
    E, S, SV, DG = _path(yarn_point, Py, 0,
                         np.linspace(0.0, 0.12, 601)[1:], 16)
    s_pk, e_pk = _corner(E, S, DG, "FI1T")
    O["y1t_peak"] = float(s_pk)
    O["y1t_eps_pk"] = float(e_pk)
    i = int(np.argmax(S))
    post = np.where(S[i:] <= 0.80 * s_pk)[0]
    j = i + post[0]
    f = (0.80 * s_pk - S[j - 1]) / (S[j] - S[j - 1])
    O["y1t_eps80"] = float(E[j - 1] + f * (E[j] - E[j - 1]))
    Wd, _e = _dissipated_to(E, S, [sv[0] for sv in SV], 0.90)
    O["y1t_Wd09"] = float(Wd)

    # yarn 2t sweep: STRAIN-controlled transverse tension (see _sweep_strain
    # docstring: uniaxial-stress control snaps back at onset), dT to 0.5
    E, S, SV = _sweep_strain(yarn_point, Py, 1,
                             np.linspace(0.0, 0.008, 401)[1:], 16)
    Wd, _e = _dissipated_to(E, S, [sv[9] for sv in SV], 0.50)
    O["y2t_Wd05"] = float(Wd)

    # onsets (exact quadratic crossing of the mirror's own criteria)
    O["on2t_uni"] = _onset(Py, (0, 1, 0, 0, 0, 0), ("FITT",))
    O["on2t_biax"] = _onset(Py, (0, 1, 1, 0, 0, 0), ("FITT",))
    O["on12"] = _onset(Py, (0, 0, 0, 1, 0, 0), ("FI1T", "FITT"))
    O["on23"] = _onset(Py, (0, 0, 0, 0, 0, 1), ("FITT",))
    O["on2c"] = _onset(Py, (0, -1, 0, 0, 0, 0), ("FITC",), probe=250.0)

    # matrix load-unload cycle (plasticity + damage)
    up = np.linspace(0.0, 0.0025, 126)[1:]
    dn = np.linspace(0.0025, 0.0, 126)[1:]
    E, S, SV, DG = _path(matrix_point, Pm, 0, np.concatenate([up, dn]), 20)
    nup = len(up)
    s_pk, e_pk = _corner(E[:nup + 1], S[:nup + 1], DG[:nup + 1], "FIT")
    O["m_peak"] = float(s_pk)
    O["m_eps_pk"] = float(e_pk)
    Su, Eu = S[nup + 1:], E[nup + 1:]
    neg = np.where(Su <= 0.0)[0]
    if len(neg) == 0:
        raise RuntimeError("matrix unload never crossed zero stress")
    j = neg[0]
    if j == 0:
        O["m_resid"] = float(Eu[0])
    else:
        f = (0.0 - Su[j - 1]) / (Su[j] - Su[j - 1])
        O["m_resid"] = float(Eu[j - 1] + f * (Eu[j] - Eu[j - 1]))

    _MEMO[key] = O
    return O


# --------------------------------------------------------------------------
# Part 2: the normalized Jacobian
# --------------------------------------------------------------------------
def jacobian(base, O0, h):
    """S[i][j] = (dO_i/dp_j) * p_j / O_i, central differences, relative step h.
    At p_j = 0 the relative step is the zero step: S is 0 by structure."""
    S = np.zeros((len(OBS_NAMES), len(KNOB_NAMES)))
    D = np.zeros_like(S)            # raw dO/dp
    for j, name in enumerate(KNOB_NAMES):
        p = base[name]
        if p == 0.0:
            continue
        pp = dict(base); pp[name] = p * (1.0 + h)
        pm = dict(base); pm[name] = p * (1.0 - h)
        Op, Om = observables(pp), observables(pm)
        for i, on in enumerate(OBS_NAMES):
            d = (Op[on] - Om[on]) / (2.0 * h * p)
            D[i, j] = d
            S[i, j] = d * p / O0[on]
    return S, D


def fd_agree(s1, s2):
    return abs(s1 - s2) <= max(0.02, 0.05 * abs(s1))


def structure_class(obs, knob, p_base, s):
    _n, phase, _sl = KNOBS[KNOB_NAMES.index(knob)]
    yarn_obs = not obs.startswith("m_")
    if p_base == 0.0:
        return "STRUCTURAL_ZERO(p=0)"
    if yarn_obs != (phase == "yarn"):
        return "STRUCTURAL_ZERO(cross-phase)"
    if abs(s) >= 0.01:
        return "LIVE"
    return "NEAR_NULL"


def csv_text(base, O0, S1, S2, D1):
    lines = ["obs,knob,p_base,O_base,dO_dp_h1,S_h1em3,S_h2em3,dS_steps,"
             "structure,fd_verdict,basis"]
    for i, on in enumerate(OBS_NAMES):
        for j, kn in enumerate(KNOB_NAMES):
            s1, s2 = S1[i, j], S2[i, j]
            cls = structure_class(on, kn, base[kn], s1)
            verdict = ("OK" if (cls.startswith("STRUCTURAL") or
                                fd_agree(s1, s2)) else "FD_NOISY")
            basis = ("central FD; rel steps 1e-3/2e-3 at V2_0 card; "
                     "rF derived from X_PO+K1 (Ge Eq.17)"
                     + ("; S13 moved with S12" if kn == "S12" else "")
                     + ("; relative step at p=0 is the zero step" if
                        base[kn] == 0.0 else ""))
            lines.append("%s,%s,%.6g,%.9e,%.9e,%.9e,%.9e,%.2e,%s,%s,%s"
                         % (on, kn, base[kn], O0[on], D1[i, j], s1, s2,
                            abs(s1 - s2), cls, verdict, basis))
    return "\n".join(lines) + "\n"


def snapshot_text(O0, S1):
    """The generated quantitative summary table pasted into GUIDE 2."""
    lines = [SNAP_BEGIN,
             "| 관측량 (단일점) | 기준값 | 1위 knob | 2위 knob | 그 외 유효 knob |",
             "|---|---|---|---|---|"]
    for i, (on, desc, _proxy) in enumerate(OBSERVABLES):
        row = S1[i, :]
        order = np.argsort(-np.abs(row))
        tops = []
        for j in order[:2]:
            if abs(row[j]) >= 1e-3:
                tops.append("%s %+.3f" % (KNOB_NAMES[j], row[j]))
        while len(tops) < 2:
            tops.append("—")
        rest = [KNOB_NAMES[j] for j in order[2:] if abs(row[j]) > 0.01]
        val = ("%.4g" % O0[on])
        lines.append("| `%s` | %s | %s | %s | %s |"
                     % (on, val, tops[0], tops[1],
                        ", ".join(rest) if rest else "없음"))
    lines.append(SNAP_END)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Part 3: identifiability
# --------------------------------------------------------------------------
def svd_report(S, rows, title, tol_rel=1.0e-3):
    idx = [OBS_NAMES.index(r) for r in rows]
    A = S[idx, :]
    U, sv, Vt = np.linalg.svd(A, full_matrices=False)
    rank = int(np.sum(sv > tol_rel * sv[0])) if sv[0] > 0 else 0
    cond = sv[0] / sv[rank - 1] if rank > 0 else float("inf")
    pinned = np.sqrt(np.sum(Vt[:rank, :] ** 2, axis=0)) if rank else \
        np.zeros(len(KNOB_NAMES))
    print("\n --- SVD: %s  (%d rows x %d knobs) ---" % (title, len(rows),
                                                        len(KNOB_NAMES)))
    print("   singular values : " + "  ".join("%.4g" % s for s in sv))
    print("   numerical rank  : %d   (tol %.0e * s1)" % (rank, tol_rel))
    print("   cond (live part): %.3g" % cond)
    print("   pinned fraction per knob (|proj on row space|, 1 = fully seen):")
    for j, kn in enumerate(KNOB_NAMES):
        bar = "#" * int(round(20 * min(1.0, pinned[j])))
        print("     %-5s %.3f  %s" % (kn, pinned[j], bar))
    for k in range(rank):
        load = ", ".join("%s %+0.2f" % (KNOB_NAMES[j], Vt[k, j])
                         for j in np.argsort(-np.abs(Vt[k, :]))[:3]
                         if abs(Vt[k, j]) > 0.05)
        print("   pinned direction v%d (s=%.3g): %s" % (k + 1, sv[k], load))
    return sv, rank, cond, pinned


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    do_check = "--check" in sys.argv
    base = base_pset()
    O0 = observables(base)

    print("=" * 74)
    print("knob_sensitivity.py -- GUIDE 2, quantitative, at the V2_0 card")
    print("=" * 74)

    # rF numbers used everywhere below
    E1, Xt = YARN_V2[1], YARN_V2[10]
    rf0 = rf_derived(E1, Xt, base["X_PO"], base["K1"])
    c1 = 1.0 + base["K1"] / E1
    B1T = kaband(Xt * Xt / (2.0 * E1) * 0.03, YARN_V2[31], 2.0)

    print("""
 PART 1 -- observables (single material point, uniaxial/biaxial stress)
 CAVEAT: a single point cannot redistribute load.  RVE redistribution
 (matrix->yarn handoff, crack-band localisation running single elements to
 large r) is measured in Stage runs, not here.  These rows rank knob
 leverage; they do not predict macro magnitudes.
""")
    print(" %-10s %-14s %s" % ("name", "base value", "proxies (macro)"))
    for on, desc, proxy in OBSERVABLES:
        print(" %-10s %-14.6g %s" % (on, O0[on], proxy))
        print(" %10s   = %s" % ("", desc))
    print("\n derived rF at this card: rF = 1 + (E1/K1)(1 - X_PO/Xt) = %.3f"
          % rf0)
    print(" (old card had FREE rF = 3.0 -- see the discontinuity checks)")

    S1, D1 = jacobian(base, O0, H1)
    S2, _D2 = jacobian(base, O0, H2)

    print("\n PART 2 -- normalized sensitivities S_ij = dO_i/dp_j * p_j/O_i")
    print("           (central FD, rel step 1e-3; 0.000 printed for |S|<5e-4)")
    hdr = " %-10s" + " %8s" * len(KNOB_NAMES)
    print(hdr % tuple(["obs \\ knob"] + KNOB_NAMES))
    for i, on in enumerate(OBS_NAMES):
        cells = []
        for j in range(len(KNOB_NAMES)):
            v = S1[i, j]
            cells.append("%8.3f" % v if abs(v) >= 5e-4 else "%8s" % ".")
        print((" %-10s" % on) + "".join(cells))

    # ---- Part 3 ----------------------------------------------------------
    print("\n PART 3 -- identifiability (SVD of the normalized Jacobian)")
    sv3, rank3, cond3, pin3 = svd_report(
        S1, STRENGTH_ROWS, "3 strength-proxy rows (the Table 3 targets)")
    svA, rankA, condA, pinA = svd_report(
        S1, OBS_NAMES, "all 13 rows (strengths + shape features)")

    # rF free vs derived, on the yarn-1t block where Eq.18 acts
    y1_rows = ["y1t_peak", "y1t_eps80", "y1t_Wd09"]
    rf_col = np.zeros(len(y1_rows))
    for h in (H1,):
        Op = observables(base, free_rf=rf0 * (1.0 + h))
        Om = observables(base, free_rf=rf0 * (1.0 - h))
        for i, on in enumerate(y1_rows):
            d = (Op[on] - Om[on]) / (2.0 * h * rf0)
            rf_col[i] = d * rf0 / O0[on]
    print("\n --- 4-dim vs 5-dim: the freed-rF column on the yarn-1t rows ---")
    for i, on in enumerate(y1_rows):
        print("     S(%s, rF_free) = %+.3e" % (on, rf_col[i]))
    print("   below the transition (r < rF = %.1f) a free rF moves NOTHING:"
          % rf0)
    print("   freeing it adds an exact null direction to the shape group.")

    # Gtt switched ON at the sourced value: is it identifiable then?
    pset_on = dict(base); pset_on["Gtt"] = G_TT_SHI
    s_gtt_on = 0.0
    pp = dict(pset_on); pp["Gtt"] = G_TT_SHI * (1.0 + H1)
    pm = dict(pset_on); pm["Gtt"] = G_TT_SHI * (1.0 - H1)
    O_on = observables(pset_on)
    s_gtt_on = ((observables(pp)["y2t_Wd05"] - observables(pm)["y2t_Wd05"])
                / (2.0 * H1 * G_TT_SHI)) * G_TT_SHI / O_on["y2t_Wd05"]
    print("\n --- Gtt at the sourced ON value (Shi refs/[31], %.3f N/mm) ---"
          % G_TT_SHI)
    print("     S(y2t_Wd05, Gtt)|ON = %+.3f   (at the card, Gtt=0: exactly 0)"
          % s_gtt_on)

    # Stage D block: the matrix PEAK is pinned at Xm,t (no knob moves it),
    # so SY0/HISO separation must come from two SHAPE features.
    iD = [OBS_NAMES.index("m_eps_pk"), OBS_NAMES.index("m_resid")]
    jD = [KNOB_NAMES.index("SY0"), KNOB_NAMES.index("HISO")]
    AD = S1[np.ix_(iD, jD)]
    svD = np.linalg.svd(AD, compute_uv=False)
    condD = svD[0] / svD[-1] if svD[-1] > 0 else float("inf")
    print("\n --- Stage D block [m_eps_pk; m_resid] x [SY0, HISO] ---")
    print("     singular values %.4g / %.4g,  cond = %.3g" %
          (svD[0], svD[1], condD))

    # the old free-rF card's onset discontinuity, demonstrated
    d_old = kmix1t(1.001, B1T, E1, Xt, base["X_PO"], 3.0, base["K1"])
    d_new = kmix1t(1.001, B1T, E1, Xt, base["X_PO"], rf0, base["K1"])
    print("\n --- Ge Eq.(17) consistency at onset (r = 1.001) ---")
    print("     free rF=3.0 (old card): d = %.4f   <- JUMP at onset" % d_old)
    print("     derived rF=%.2f       : d = %.2e  <- continuous" % (rf0, d_new))

    if not do_check:
        with open(CSV_PATH, "w") as f:
            f.write(csv_text(base, O0, S1, S2, D1))
        print("\n wrote %s  (%d data rows)" %
              (CSV_PATH, len(OBS_NAMES) * len(KNOB_NAMES)))
        print("\n snapshot table for CALIBRATION_GUIDE.md 2:\n")
        print(snapshot_text(O0, S1))
        return 0

    # ---- Part 4: the gate ------------------------------------------------
    print("\n PART 4 -- regression gate")
    print("\n A. rF derivation (Ge Eq. 17)")
    check("derived rF at V2_0 card is ~25 (transition deep in the tail)",
          24.0 < rf0 < 26.0, "rF = %.3f" % rf0)
    dF = c1 * (1.0 - 1.0 / rf0)
    check("transition consistency: (1-dF)(Xt/X_PO)rF = 1",
          abs((1.0 - dF) * (Xt / base["X_PO"]) * rf0 - 1.0) < 1e-9)
    sig_tr = Xt * (c1 - (base["K1"] / E1) * rf0)
    check("linear branch reaches exactly X_PO at rF",
          abs(sig_tr - base["X_PO"]) < 1e-6 * base["X_PO"],
          "%.3f vs %.1f MPa" % (sig_tr, base["X_PO"]))
    check("old FREE rF=3.0 makes damage JUMP at onset",
          d_old > 0.2, "d(r=1.001) = %.4f" % d_old)
    d_lin = c1 * (1.0 - 1.0 / 1.001)     # the continuous linear-branch value
    check("derived rF removes the jump: d(1.001) = linear-branch value -> 0",
          d_new < 5e-3 and abs(d_new - d_lin) < 1e-9,
          "d = %.2e vs dL = %.2e (old card: %.2f)" % (d_new, d_lin, d_old))
    check("rF is not a Jacobian column (derived, not free)",
          "rF" not in KNOB_NAMES)

    print("\n B. coverage of the calibration spaces")
    sys.path.insert(0, HERE)
    import m6_calibration_plan as m6
    shape_map = {"Gtt yarn": "Gtt", "Gtc yarn": "Gtc",
                 "X_PO yarn": "X_PO", "K1 yarn": "K1"}
    check("every knob of the M6 SHAPE group is a Jacobian column",
          all(shape_map[k] in KNOB_NAMES for k in m6.SHAPE),
          ", ".join(sorted(shape_map[k] for k in m6.SHAPE)))
    check("Stage B knobs (Yt,Yc,S12,S23) are columns",
          all(k in KNOB_NAMES for k in ("Yt", "Yc", "S12", "S23")))
    check("Stage D knobs (SY0,HISO) are columns",
          all(k in KNOB_NAMES for k in ("SY0", "HISO")))
    check("CSV has 13 x 10 data rows",
          len(OBS_NAMES) * len(KNOB_NAMES) == 130)

    print("\n C. sensitivities that MUST be zero")
    col = {k: KNOB_NAMES.index(k) for k in KNOB_NAMES}
    row = {o: OBS_NAMES.index(o) for o in OBS_NAMES}
    y1 = [row[o] for o in ("y1t_peak", "y1t_eps_pk", "y1t_eps80", "y1t_Wd09")]
    check("yarn 1t rows vs Yc are zero (to lateral-Newton dust, 1e-9)",
          np.all(np.abs(S1[y1, col["Yc"]]) < 1e-9),
          "max |S| = %.2e" % np.max(np.abs(S1[y1, col["Yc"]])))
    check("yarn 1t rows vs S23 are zero (to lateral-Newton dust, 1e-9)",
          np.all(np.abs(S1[y1, col["S23"]]) < 1e-9),
          "max |S| = %.2e" % np.max(np.abs(S1[y1, col["S23"]])))
    yarn_rows = [row[o] for o in OBS_NAMES if not o.startswith("m_")]
    check("all yarn rows vs SY0 and HISO are zero (cross-phase)",
          np.all(np.abs(S1[np.ix_(yarn_rows,
                                  [col["SY0"], col["HISO"]])]) < 1e-15))
    m_rows = [row["m_peak"], row["m_eps_pk"], row["m_resid"]]
    yarn_cols = [col[k] for k in ("Yt", "Yc", "S12", "S23", "X_PO", "K1")]
    check("matrix rows vs all yarn knobs are zero (cross-phase)",
          np.all(np.abs(S1[np.ix_(m_rows, yarn_cols)]) < 1e-15))
    check("m_peak row is all zero: the corner peak IS Xm,t, no knob moves it",
          np.all(np.abs(S1[row["m_peak"], :]) < 1e-9),
          "max |S| = %.2e" % np.max(np.abs(S1[row["m_peak"], :])))
    check("m_peak equals the card Xm,t exactly",
          abs(O0["m_peak"] - MATRIX_V2[3]) < 1e-6 * MATRIX_V2[3],
          "%.6f vs %.1f" % (O0["m_peak"], MATRIX_V2[3]))
    check("Gtt and Gtc columns are zero at the card (p=0 -> zero rel. step)",
          np.all(np.abs(S1[:, [col["Gtt"], col["Gtc"]]]) < 1e-15))
    check("on2c vs S23 is zero (Hashin uniaxial-compression identity)",
          abs(S1[row["on2c"], col["S23"]]) < 1e-9,
          "S = %.2e" % S1[row["on2c"], col["S23"]])
    check("X_PO column on yarn-1t rows is zero (transition at r=%.0f "
          "is beyond every observable)" % rf0,
          np.all(np.abs(S1[y1, col["X_PO"]]) < 1e-9),
          "max |S| = %.2e" % np.max(np.abs(S1[y1, col["X_PO"]])))

    print("\n D. GUIDE-2 sign directions and exact magnitudes")
    check("on2t_uni: S(Yt) = 1 exactly (onset = Yt)",
          abs(S1[row["on2t_uni"], col["Yt"]] - 1.0) < 1e-6)
    check("on12: S(S12) = 1 exactly (onset = S12)",
          abs(S1[row["on12"], col["S12"]] - 1.0) < 1e-6)
    check("on23: S(S23) = 1 exactly (onset = S23)",
          abs(S1[row["on23"], col["S23"]] - 1.0) < 1e-6)
    check("on2c: S(Yc) = 1 exactly (onset = Yc)",
          abs(S1[row["on2c"], col["Yc"]] - 1.0) < 1e-6)
    sYt = S1[row["on2t_biax"], col["Yt"]]
    sS23 = S1[row["on2t_biax"], col["S23"]]
    check("on2t_biax: Yt UP -> onset UP, amplified past 1 (S > 1)",
          sYt > 1.0, "S(Yt) = %.3f" % sYt)
    check("on2t_biax: S23 UP -> onset DOWN (the -s22*s33/S23^2 term is "
          "favourable and shrinks)", sS23 < 0, "S(S23) = %.3f" % sS23)
    check("on2t_biax Euler identity: S(Yt)+S(S23) = 1 (homogeneity)",
          abs(sYt + sS23 - 1.0) < 1e-6, "%.6f" % (sYt + sS23))
    check("biaxial onset is below uniaxial (TRS-like state onsets earlier)",
          O0["on2t_biax"] < O0["on2t_uni"],
          "%.1f < %.1f MPa" % (O0["on2t_biax"], O0["on2t_uni"]))
    check("y1t_Wd09: K1 UP -> dissipated energy DOWN (steeper tail)",
          S1[row["y1t_Wd09"], col["K1"]] < 0,
          "S = %+.3f" % S1[row["y1t_Wd09"], col["K1"]])
    check("y1t_eps80: K1 UP -> failure-strain proxy DOWN",
          S1[row["y1t_eps80"], col["K1"]] < 0,
          "S = %+.3f" % S1[row["y1t_eps80"], col["K1"]])
    check("y1t_peak is Xt exactly (corner peak; NO knob in the set moves it)",
          abs(O0["y1t_peak"] / Xt - 1.0) < 1e-9,
          "%.3f vs Xt %.1f" % (O0["y1t_peak"], Xt))
    check("y1t_eps_pk is Xt/E1 within 0.1 % (pinned by verified constants)",
          abs(O0["y1t_eps_pk"] / (Xt / E1) - 1.0) < 1e-3,
          "%.6e vs %.6e" % (O0["y1t_eps_pk"], Xt / E1))
    check("y2t_Wd05: Yt UP -> transverse energy UP, ~quadratically (S ~ 2)",
          1.5 < S1[row["y2t_Wd05"], col["Yt"]] < 3.0,
          "S = %+.3f" % S1[row["y2t_Wd05"], col["Yt"]])
    check("matrix plasticity is active: residual strain > 0",
          O0["m_resid"] > 1e-5, "%.3e" % O0["m_resid"])
    check("m_resid: SY0 UP -> residual strain DOWN (GUIDE 2 direction)",
          S1[row["m_resid"], col["SY0"]] < 0,
          "S = %+.3f" % S1[row["m_resid"], col["SY0"]])
    check("m_resid: HISO UP -> residual strain DOWN",
          S1[row["m_resid"], col["HISO"]] < 0,
          "S = %+.3f" % S1[row["m_resid"], col["HISO"]])
    check("m_eps_pk: SY0 UP -> knee strain DOWN (less plastic run-up)",
          S1[row["m_eps_pk"], col["SY0"]] < 0,
          "S = %+.3f" % S1[row["m_eps_pk"], col["SY0"]])
    check("m_eps_pk and m_resid are linearly independent in (SY0,HISO)",
          np.isfinite(condD) and condD < 100.0, "cond = %.3g" % condD)
    check("Gtt at the sourced ON value IS identifiable from y2t energy",
          abs(s_gtt_on) > 0.02, "S|ON = %+.3f (vs exactly 0 at the card)"
          % s_gtt_on)

    print("\n E. FD robustness and identifiability verdicts")
    live = np.abs(S1) >= 0.01
    worst = 0.0
    for i in range(S1.shape[0]):
        for j in range(S1.shape[1]):
            if live[i, j]:
                worst = max(worst, abs(S1[i, j] - S2[i, j]))
    check("every LIVE entry agrees between steps 1e-3 and 2e-3",
          all(fd_agree(S1[i, j], S2[i, j])
              for i in range(S1.shape[0]) for j in range(S1.shape[1])
              if live[i, j]),
          "worst |dS| = %.2e" % worst)
    check("the 3 strength-proxy rows pin only ONE knob direction",
          rank3 == 1,
          "rank %d; sv = %s" % (rank3,
                                ", ".join("%.3g" % s for s in sv3)))
    check("all 13 rows pin 7 directions (Gtt,Gtc,X_PO stay free)",
          rankA == 7,
          "sv = " + ", ".join("%.3g" % s for s in svA[:8]))
    check("X_PO pinned fraction ~ 0 even with all shape rows",
          pinA[col["X_PO"]] < 1e-3, "%.2e" % pinA[col["X_PO"]])
    check("condition of the live part is finite",
          np.isfinite(condA) and condA < 1.0e3, "cond = %.3g" % condA)
    svA2 = np.linalg.svd(S2[[OBS_NAMES.index(o) for o in OBS_NAMES], :],
                         compute_uv=False)
    rankA2 = int(np.sum(svA2 > 1e-3 * svA2[0]))
    condA2 = svA2[0] / svA2[rankA2 - 1]
    check("rank and condition stable under the FD step (2e-3 gives same)",
          rankA2 == rankA and abs(condA2 / condA - 1.0) < 0.2,
          "rank %d cond %.3g" % (rankA2, condA2))
    check("freed rF adds an EXACT null direction (its column is zero)",
          np.all(np.abs(rf_col) < 1e-9),
          "max |S| = %.2e -> fixing rF removes a dead dimension" %
          np.max(np.abs(rf_col)))

    print("\n F. artefacts regenerate identically")
    want = csv_text(base, O0, S1, S2, D1)
    have = open(CSV_PATH).read() if os.path.exists(CSV_PATH) else ""
    check("knob_sensitivity.csv on disk regenerates byte-identical",
          have == want,
          "" if have == want else "stale -- rerun without --check")
    guide = open(GUIDE_PATH, encoding="utf-8").read()
    snap = snapshot_text(O0, S1)
    ok_snap = SNAP_BEGIN in guide and SNAP_END in guide
    if ok_snap:
        got = guide[guide.index(SNAP_BEGIN):
                    guide.index(SNAP_END) + len(SNAP_END)]
        ok_snap = got.strip() == snap.strip()
    check("CALIBRATION_GUIDE 2 snapshot table matches the computed one",
          ok_snap, "" if ok_snap else "guide snapshot is stale")

    print("\n" + "=" * 74)
    if _BAD:
        print("FAIL -- %d of %d: %s" % (len(_BAD), len(_OK) + len(_BAD),
                                        "; ".join(_BAD[:4])))
        print("=" * 74)
        return 1
    print("ALL %d KNOB-SENSITIVITY CHECKS HOLD" % len(_OK))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
