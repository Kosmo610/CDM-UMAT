#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_temperature_tables.py
===========================
Turn CONSTITUENT temperature-dependent data (data/properties/*.csv) into the
Abaqus blocks the V3_0 UMAT needs:

  * the yarn   f(T) multiplier table   (7 numbers per row) for the YARN card
  * the matrix f(T) multiplier table   (4 numbers per row) for the MATRIX card
  * `*Expansion, type=ORTHO, zero=1050` rows for the yarn
  * `*Expansion, zero=1050`             rows for the matrix

Why this script exists
----------------------
Three things are easy to get wrong by hand, and each of them corrupts the
thermal residual stress -- the main variable of this thesis.

1. THE YARN IS NOT A CONSTITUENT.  Its constants are a Chamis/Schapery
   homogenisation of the T300 filament and the SiC matrix (verified to 0.14 %
   by verification/micromech_check.py).  So the yarn's f(T) must be recomputed
   from the constituent properties AT EACH TEMPERATURE, not guessed.  This
   script runs the same Chamis/Schapery relations at every temperature row.

2. ABAQUS WANTS A SECANT CTE REFERENCED TO THE STRESS-FREE TEMPERATURE.
   Papers report either an instantaneous CTE, or a secant CTE referenced to
   room temperature.  Feeding either one straight into `*Expansion, zero=1050`
   is wrong.  This script converts, given `cte_type` and `cte_ref_C` in the CSV.

3. COMPOSITE-LEVEL DATA MUST NOT BE USED AS INPUT.  Measured C/SiC E(T) and
   sigma_u(T) rise with temperature largely BECAUSE the thermal residual stress
   relaxes as the material is heated back toward its processing temperature.
   The model already computes that from the cooling step.  Using composite
   E(T) as an input multiplier would count the same physics twice.  Composite
   data is VALIDATION -- see docs/PROPERTY_DATA_REQUEST.md.

Modelling assumptions that this script makes explicit
-----------------------------------------------------
  fX (yarn longitudinal strength)  <- fibre axial strength ratio
        because Xt_yarn = Vf * Xt_fibre (rule of mixtures, as in the V2_0 card)
  fY, fS (yarn transverse + shear) <- MATRIX strength ratio
        transverse and shear yarn failure is matrix/interface dominated; no
        transverse fibre strength data exists.  Documented assumption, flagged
        in the output header, and worth a sensitivity study.
  fSY (matrix yield)               <- matrix strength ratio

Self-test
---------
With only the verified 23 C row present, the script must reproduce the verified
V2_0 yarn card constants exactly.  That check runs on every invocation.

Usage
  python3 abaqus/build_temperature_tables.py
  python3 abaqus/build_temperature_tables.py --zero 1050 --out cards/
"""
from __future__ import print_function

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROPDIR = os.path.join(ROOT, "data", "properties")

#: yarn-level fibre volume fraction recovered and verified in
#: verification/micromech_check.py (composite Vf ~ 39.6 %, paper says "~40 %")
VF_YARN = 0.79194

#: the V2_0 yarn card, used as the self-test target
V2_YARN_CARD = dict(E1=254967.228042, E2=44321.737572,
                    nu12=0.247516386, nu23=0.395813581,
                    G12=26431.515264, G23=15876.667974,
                    a1=1.070925962822e-06, a2=3.324908565604e-06)


# ==========================================================================
# CSV reading
# ==========================================================================
def read_csv(path):
    rows = []
    header = None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = _split(line)
            if header is None:
                header = [p.strip() for p in parts]
                continue
            rows.append(dict(zip(header, [p.strip() for p in parts])))
    return rows


def _split(line):
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


def num(row, key, required=True, where=""):
    v = row.get(key, "")
    if v is None or v == "":
        if required:
            raise SystemExit("missing '%s' in row T=%s of %s"
                             % (key, row.get("T_C"), where))
        return None
    return float(v)


def load(path, allow_placeholder):
    rows = read_csv(path)
    keep = []
    for r in rows:
        st = r.get("status", "").strip()
        if st == "placeholder" and not allow_placeholder:
            print("  skipping placeholder row T=%s of %s"
                  % (r.get("T_C"), os.path.basename(path)))
            continue
        keep.append(r)
    keep.sort(key=lambda r: float(r["T_C"]))
    if not keep:
        raise SystemExit("no usable rows in %s" % path)
    return keep


# ==========================================================================
# Chamis / Schapery -- identical relations to verification/micromech_check.py
# ==========================================================================
def chamis_schapery(Vf, Ef1, Ef2, Gf12, Gf23, nuf12, af1, af2, Em, num_, am):
    sq = math.sqrt(Vf)
    Vm = 1.0 - Vf
    Gm = Em / (2.0 * (1.0 + num_))
    o = {}
    o["E1"] = Vf * Ef1 + Vm * Em
    o["E2"] = Em / (1.0 - sq * (1.0 - Em / Ef2))
    o["E3"] = o["E2"]
    o["G12"] = Gm / (1.0 - sq * (1.0 - Gm / Gf12))
    o["G13"] = o["G12"]
    o["G23"] = Gm / (1.0 - sq * (1.0 - Gm / Gf23))
    o["nu12"] = Vf * nuf12 + Vm * num_
    o["nu13"] = o["nu12"]
    o["nu23"] = o["E2"] / (2.0 * o["G23"]) - 1.0
    o["a1"] = ((Vf * Ef1 * af1 + Vm * Em * am) / (Vf * Ef1 + Vm * Em))
    o["a2"] = sq * af2 + (1.0 - sq) * ((1.0 + num_) * am - o["a1"] * num_)
    o["a3"] = o["a2"]
    return o


# ==========================================================================
# CTE conversion to the secant form Abaqus *Expansion expects
# ==========================================================================
def to_secant_about(Ts, alphas, cte_type, cte_ref, T0):
    """Convert a CTE curve to the SECANT CTE referenced to T0.

    Abaqus *Expansion, zero=T0 uses
        eps_th(T) = alpha_sec(T)*(T-T0) - alpha_sec(Ti)*(Ti-T0),
    so alpha_sec must be the secant value about T0.

    instantaneous -> alpha_sec(T) = (1/(T-T0)) * integral_{T0}^{T} alpha dT'
    secant@Tref   -> alpha_sec(T) = [a_ref(T)(T-Tref) - a_ref(T0)(T0-Tref)]
                                    / (T-T0)

    At T = T0 both forms are 0/0; the limit is the instantaneous value there,
    which is recovered by linear extrapolation from the two nearest rows.
    """
    if len(Ts) == 1:
        # A single row carries no temperature dependence: the secant CTE about
        # any reference is just that constant.
        return [alphas[0]]

    def interp(x, xs, ys):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        for i in range(len(xs) - 1):
            if xs[i] <= x <= xs[i + 1]:
                w = (x - xs[i]) / (xs[i + 1] - xs[i])
                return ys[i] + w * (ys[i + 1] - ys[i])
        return ys[-1]

    out = []
    if cte_type == "instantaneous":
        # cumulative integral of alpha_inst from Ts[0]
        cum = [0.0]
        for i in range(1, len(Ts)):
            cum.append(cum[-1] + 0.5 * (alphas[i] + alphas[i - 1])
                       * (Ts[i] - Ts[i - 1]))

        def cum_at(x):
            """Cumulative integral, EXTENDED past the table ends.

            The stress-free temperature is routinely outside the measured
            range (data often stops at 1000 C while T0 = 1050 C), so the
            integral must be continued with the end value of alpha, not
            clamped.  Clamping makes the integral flat and drives the secant
            CTE to zero at the last table point.
            """
            if x <= Ts[0]:
                return cum[0] + alphas[0] * (x - Ts[0])
            if x >= Ts[-1]:
                return cum[-1] + alphas[-1] * (x - Ts[-1])
            return interp(x, Ts, cum)

        I0 = cum_at(T0)
        for i, T in enumerate(Ts):
            dT = T - T0
            out.append(alphas[i] if abs(dT) < 1.0e-9 else (cum[i] - I0) / dT)
    else:
        Tref = cte_ref
        aT0 = interp(T0, Ts, alphas)
        for i, T in enumerate(Ts):
            dT = T - T0
            if abs(dT) < 1.0e-9:
                out.append(alphas[i])
            else:
                out.append((alphas[i] * (T - Tref) - aT0 * (T0 - Tref)) / dT)

    # Fix the T == T0 entry by extrapolating the neighbours (the raw value put
    # there above is the source's own reference-frame number, not the limit).
    for i, T in enumerate(Ts):
        if abs(T - T0) < 1.0e-9 and len(Ts) >= 3:
            j = i - 1 if i > 0 else i + 1
            k = i - 2 if i > 1 else (i + 2 if i + 2 < len(Ts) else j)
            if j != k:
                w = (T - Ts[j]) / (Ts[k] - Ts[j])
                out[i] = out[j] + w * (out[k] - out[j])
    return out


# ==========================================================================
def build(fib_rows, mat_rows, T0, allow_extrapolate=False):
    """Yarn/matrix multiplier tables and expansion rows."""
    fT = [float(r["T_C"]) for r in fib_rows]
    mT = [float(r["T_C"]) for r in mat_rows]

    # Both constituent tables must cover the same temperatures: the yarn is a
    # homogenisation of the two, so mixing different grids would silently pair
    # a 23 C matrix with a 1000 C fibre.
    temps = sorted(set(fT) & set(mT))
    if not temps:
        raise SystemExit(
            "fibre and matrix tables share no temperature.\n"
            "  fibre  : %s\n  matrix : %s\n"
            "Add matching rows -- the yarn card is a homogenisation of BOTH."
            % (fT, mT))
    dropped = sorted((set(fT) | set(mT)) - set(temps))
    if dropped:
        print("  NOTE: temperatures present in only one file were dropped: %s"
              % dropped)

    fib = {float(r["T_C"]): r for r in fib_rows}
    mat = {float(r["T_C"]): r for r in mat_rows}

    yarn, matx = [], []
    for T in temps:
        fr, mr = fib[T], mat[T]
        y = chamis_schapery(
            VF_YARN,
            num(fr, "E1", True, "fibre"), num(fr, "E2", True, "fibre"),
            num(fr, "G12", True, "fibre"), num(fr, "G23", True, "fibre"),
            num(fr, "nu12", True, "fibre"),
            num(fr, "alpha1", True, "fibre"), num(fr, "alpha2", True, "fibre"),
            num(mr, "E", True, "matrix"), num(mr, "nu", True, "matrix"),
            num(mr, "alpha", True, "matrix"))
        yarn.append(dict(T=T, y=y,
                         Xf=num(fr, "Xt", True, "fibre"),
                         Xm=num(mr, "Xt", True, "matrix"),
                         Em=num(mr, "E", True, "matrix"),
                         a_f1=num(fr, "alpha1", True, "fibre"),
                         a_m=num(mr, "alpha", True, "matrix")))
        matx.append(dict(T=T, E=num(mr, "E", True, "matrix"),
                         X=num(mr, "Xt", True, "matrix"),
                         a=num(mr, "alpha", True, "matrix"),
                         cte_type=mr.get("cte_type", "secant"),
                         cte_ref=float(mr.get("cte_ref_C") or T)))
    ref = yarn[0]
    refm = matx[0]

    yarn_rows = []
    for e in yarn:
        y, r = e["y"], ref["y"]
        yarn_rows.append([
            e["T"],
            y["E1"] / r["E1"],
            y["E2"] / r["E2"],
            y["G12"] / r["G12"],
            e["Xf"] / ref["Xf"],          # fX  <- fibre axial strength
            e["Xm"] / ref["Xm"],          # fY  <- matrix strength (assumption)
            e["Xm"] / ref["Xm"],          # fS  <- matrix strength (assumption)
        ])
    matrix_rows = [[e["T"], e["E"] / refm["E"], e["X"] / refm["X"],
                    e["X"] / refm["X"]] for e in matx]

    # Expansion: convert each CTE curve to the secant form about T0.
    ct = fib_rows[0].get("cte_type", "secant")
    cr = float(fib_rows[0].get("cte_ref_C") or temps[0])
    a1 = to_secant_about(temps, [e["y"]["a1"] for e in yarn], ct, cr, T0)
    a2 = to_secant_about(temps, [e["y"]["a2"] for e in yarn], ct, cr, T0)
    ctm = matx[0]["cte_type"]
    crm = matx[0]["cte_ref"]
    am = to_secant_about(temps, [e["a"] for e in matx], ctm, crm, T0)

    return temps, yarn_rows, matrix_rows, a1, a2, am, yarn, ct, ctm


def self_test(yarn):
    """At the verified 23 C row the Chamis output must equal the V2_0 card."""
    base = None
    for e in yarn:
        if abs(e["T"] - 23.0) < 1.0e-9:
            base = e["y"]
    if base is None:
        print("  self-test SKIPPED: no 23 C row present")
        return True
    worst, worstk = 0.0, ""
    for k, ref in V2_YARN_CARD.items():
        got = base[k]
        rel = abs(got - ref) / abs(ref)
        if rel > worst:
            worst, worstk = rel, k
    ok = worst < 2.0e-3
    print("  self-test: Chamis at 23 C vs the verified V2_0 yarn card -- "
          "%s (worst %.3f %% on %s)"
          % ("PASS" if ok else "FAIL", 100.0 * worst, worstk))
    return ok


# ==========================================================================
def emit(temps, yarn_rows, matrix_rows, a1, a2, am, T0, ct, ctm, nfib, nmat):
    L = []
    L.append("** ==================================================")
    L.append("** Temperature blocks for UMAT_CSIC_THERMSHOCK_V3_0")
    L.append("** generated by abaqus/build_temperature_tables.py")
    L.append("** from data/properties/*.csv -- do NOT hand-edit")
    L.append("**")
    L.append("** %d temperature point(s): %s"
             % (len(temps), ", ".join("%g" % t for t in temps)))
    L.append("** stress-free (zero) temperature: %g C" % T0)
    L.append("** fibre CTE reported as %s, matrix CTE as %s; both converted"
             % (ct, ctm))
    L.append("** to the SECANT CTE about %g C that *Expansion needs." % T0)
    L.append("** ASSUMPTION: yarn transverse/shear strength multipliers fY,fS")
    L.append("**   follow the MATRIX strength (matrix/interface dominated);")
    L.append("**   no transverse fibre strength data exists.  Sensitivity-test.")
    if len(temps) < 2:
        L.append("**")
        L.append("** WARNING: ONE temperature point only -> f(T) is constant")
        L.append("**   and the model is effectively temperature-independent.")
        L.append("**   Add at least one high-temperature row before drawing")
        L.append("**   any conclusion about thermal shock.")
    L.append("** ==================================================")
    L.append("")
    L.append("** --- append to the YARN card: slot 39 HCLO, 40 NT, then rows")
    L.append("**     of 7:  T, fE1, fE2, fG, fX, fY, fS")
    L.append("**     yarn NPROPS = 40 + 7*%d = %d" % (len(temps),
                                                      40 + 7 * len(temps)))
    L.append("%.10g," % len(temps))
    for r in yarn_rows:
        L.append(", ".join("%.10g" % v for v in r))
    L.append("")
    L.append("*Expansion, type=ORTHO, zero=%g" % T0)
    for T, x, y in zip(temps, a1, a2):
        L.append("%.9e, %.9e, %.9e, %.6g" % (x, y, y, T))
    L.append("")
    L.append("** --- append to the MATRIX card: slot 23 NT, then rows of 4:")
    L.append("**     T, fE, fX, fSY")
    L.append("**     matrix NPROPS = 23 + 4*%d = %d" % (len(temps),
                                                        23 + 4 * len(temps)))
    L.append("%.10g," % len(temps))
    for r in matrix_rows:
        L.append(", ".join("%.10g" % v for v in r))
    L.append("")
    L.append("*Expansion, zero=%g" % T0)
    for T, x in zip(temps, am):
        L.append("%.9e, %.6g" % (x, T))
    return "\n".join(L)


def cte_selftest():
    """Three checks on the CTE reference conversion.

    Getting this conversion wrong changes the thermal residual stress, which is
    the main variable of the thesis, so it is tested rather than trusted.
    """
    print("CTE reference-conversion self-test")
    fails = []
    Ts = [23.0, 500.0, 1050.0, 1400.0]

    # 1. A constant instantaneous CTE is its own secant, about any reference.
    s = to_secant_about(Ts, [4.5e-6] * 4, "instantaneous", 23.0, 1050.0)
    ok = all(abs(v - 4.5e-6) < 1.0e-14 for v in s)
    print("  [%s] constant alpha_inst -> constant secant" %
          ("PASS" if ok else "FAIL"))
    fails += [] if ok else ["constant"]

    # 2. For alpha_inst linear in T the secant about T0 has a closed form.
    a0, b = 1.0e-6, 3.0e-9
    s = to_secant_about(Ts, [a0 + b * (T - 23.0) for T in Ts],
                        "instantaneous", 23.0, 1050.0)
    ref = [a0 + b * ((T + 1050.0) / 2.0 - 23.0) for T in Ts]
    err = max(abs(x - y) for x, y in zip(s, ref))
    ok = err < 1.0e-15
    print("  [%s] linear alpha_inst -> analytic secant (max err %.2e)"
          % ("PASS" if ok else "FAIL", err))
    fails += [] if ok else ["linear"]

    # 3. The real requirement: rebasing a secant CTE must leave every THERMAL
    #    STRAIN DIFFERENCE unchanged.  This is the definitive check.
    a23 = [0.0, 2.0e-6, 3.0e-6, 3.4e-6]
    s = to_secant_about(Ts, a23, "secant", 23.0, 1050.0)
    bad = 0
    for i in range(len(Ts)):
        for j in range(len(Ts)):
            d_old = a23[i] * (Ts[i] - 23.0) - a23[j] * (Ts[j] - 23.0)
            d_new = s[i] * (Ts[i] - 1050.0) - s[j] * (Ts[j] - 1050.0)
            if abs(d_old - d_new) > 1.0e-12:
                bad += 1
    ok = bad == 0
    print("  [%s] secant@23 -> secant@1050 preserves every thermal-strain "
          "difference (%d/%d bad)" % ("PASS" if ok else "FAIL", bad,
                                      len(Ts) ** 2))
    fails += [] if ok else ["rebase"]

    # 4. T0 OUTSIDE the measured range (data to 1000 C, stress-free 1050 C).
    #    Clamping the cumulative integral here would silently give zero.
    Ts4 = [23.0, 500.0, 1000.0]
    a4 = [1.0e-6, 3.0e-6, 5.0e-6]
    s = to_secant_about(Ts4, a4, "instantaneous", 23.0, 1050.0)
    ok = all(abs(v) > 1.0e-9 for v in s) and all(v > 0.0 for v in s)
    print("  [%s] stress-free T outside the data range stays finite "
          "(%s)" % ("PASS" if ok else "FAIL",
                    ", ".join("%.3e" % v for v in s)))
    fails += [] if ok else ["outside-range"]

    # 5. Outside the range the documented behaviour is CONSTANT-alpha
    #    extension past the last data point.  Check that exactly, against a
    #    closed form built on the same assumption -- not against a linear
    #    extrapolation, which is a different (and unstated) choice.
    a0b, bb = 1.0e-6, 4.0e-9

    def a_lin(T):
        return a0b + bb * (min(T, Ts4[-1]) - 23.0)

    def cum_lin(T):
        # integral of the LINEAR part from 23 up to min(T, 1000) ...
        Tc = min(T, Ts4[-1])
        c = a0b * (Tc - 23.0) + 0.5 * bb * (Tc - 23.0) ** 2
        # ... then constant alpha(1000) beyond
        if T > Ts4[-1]:
            c += a_lin(Ts4[-1]) * (T - Ts4[-1])
        return c

    I0 = cum_lin(1050.0)
    ref = [(cum_lin(T) - I0) / (T - 1050.0) for T in Ts4]
    s = to_secant_about(Ts4, [a_lin(T) for T in Ts4],
                        "instantaneous", 23.0, 1050.0)
    err = max(abs(x - y) for x, y in zip(s, ref))
    ok = err < 1.0e-15
    print("  [%s] extension past the last point is exactly constant-alpha "
          "(max err %.2e)" % ("PASS" if ok else "FAIL", err))
    fails += [] if ok else ["outside-range-extension"]

    print("  OVERALL: %s" % ("PASS" if not fails else
                             "FAIL -> " + ", ".join(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(
        description="Build the V3_0 temperature blocks from constituent data.")
    ap.add_argument("--selftest", action="store_true",
                    help="run the CTE reference-conversion checks and exit")
    ap.add_argument("--fibre", default=os.path.join(PROPDIR,
                                                    "fibre_T300_vsT.csv"))
    ap.add_argument("--matrix", default=os.path.join(PROPDIR,
                                                     "matrix_SiC_vsT.csv"))
    ap.add_argument("--zero", type=float, default=1050.0,
                    help="stress-free temperature (default 1050 C)")
    ap.add_argument("--out", default=os.path.join(PROPDIR,
                                                  "temperature_blocks.inp"))
    ap.add_argument("--allow-placeholder", action="store_true",
                    help="use rows marked status=placeholder (NOT for results)")
    args = ap.parse_args()

    if args.selftest:
        return cte_selftest()

    print("reading constituent data")
    fib = load(args.fibre, args.allow_placeholder)
    mat = load(args.matrix, args.allow_placeholder)
    print("  fibre  rows: %s" % ", ".join(r["T_C"] for r in fib))
    print("  matrix rows: %s" % ", ".join(r["T_C"] for r in mat))

    temps, yrows, mrows, a1, a2, am, yarn, ct, ctm = build(fib, mat, args.zero)
    if temps and not (temps[0] <= args.zero <= temps[-1]):
        print("  WARNING: stress-free temperature %g C is OUTSIDE the measured"
              % args.zero)
        print("           range [%g, %g] C.  The thermal strain is extended"
              % (temps[0], temps[-1]))
        print("           past the last data point with the end value of")
        print("           alpha.  State this in the thesis, and prefer data")
        print("           that reaches the processing temperature.")
    ok = self_test(yarn)

    txt = emit(temps, yrows, mrows, a1, a2, am, args.zero, ct, ctm,
               len(fib), len(mat))
    with open(args.out, "w") as f:
        f.write(txt + "\n")
    print("  wrote %s" % args.out)
    if len(temps) < 2:
        print("\n  ONLY ONE TEMPERATURE POINT -- the generated table is a")
        print("  constant.  Fill in the high-temperature rows from")
        print("  docs/PROPERTY_DATA_REQUEST.md before using any result.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
