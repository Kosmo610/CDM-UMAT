#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_history_driven_rve.py
==========================
Replay a macroscopic strain + temperature history on the RVE, through the same
six ConstraintsDriver DOFs the periodic boundary conditions already provide.

This is the bridge from the validated RVE to a thermal-shock coupon.  A coupon
analysis with homogenised properties tells you the macro strain and temperature
history at every point of the specimen; the hot spot's history, replayed here with
the damage UMAT switched on, tells you what the weave actually does there -- which
phase cracks, when, and in what order.  One-way coupling: the coupon drives the
RVE, the RVE does not feed back.  That is enough to answer "does the microstructure
survive this transient", and it costs one RVE run per interrogation point instead
of one per macro integration point.

Why the drivers are the right handle
------------------------------------
ConstraintsDriver0..5 carry exactly the six macroscopic strain components
(e_x, e_y, e_z, e_xy, e_xz, e_yz).  Prescribing them prescribes the macro strain
while the RVE keeps its periodic fluctuation -- which is precisely the boundary
condition a material point in a larger body experiences.  Nothing new has to be
built; the constraint set validated by check_pbc.py and the patch test is reused
verbatim.

The history file
----------------
CSV with a header row.  Recognised columns (any order, case insensitive; missing
ones are taken as zero):

    time, exx|e11, eyy|e22, ezz|e33, gxy|g12, gxz|g13, gyz|g23, T|temp

Feed it the TOTAL macro strain from the coupon model, not the mechanical part.
That means the coupon's homogenised material must carry the same stress-free
temperature as the RVE (1050 degC here) so that its strain output already includes
the thermal contraction the RVE will reproduce for itself.  Get that wrong and the
residual stress is counted twice.

Generated analysis
------------------
    Step 1  Precondition   1050 degC -> T(0), drivers ramped 0 -> eps(0).
                           Starts from the true stress-free state, so the
                           manufacturing residual stress builds up on the way in.
    Step 2  Coupon_history  every driver follows its own *Amplitude, temperature
                           follows another; runs for the full history duration.

Usage
-----
    python3 abaqus/make_history_driven_rve.py abaqus/ZHANG2022_RT23_V2_0.inp \\
            hotspot_history.csv --out RVE_hotspot.inp

    abaqus job=RVE_hotspot input=RVE_hotspot.inp \\
           user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
"""
from __future__ import print_function

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_inp import split_blocks, kwname, emit_blocks   # noqa: E402

# driver index -> (amplitude name, accepted column spellings)
CHANNELS = [(0, "MACRO_EXX", ["exx", "e11", "eps_xx", "epsxx", "ex"]),
            (1, "MACRO_EYY", ["eyy", "e22", "eps_yy", "epsyy", "ey"]),
            (2, "MACRO_EZZ", ["ezz", "e33", "eps_zz", "epszz", "ez"]),
            (3, "MACRO_GXY", ["gxy", "g12", "e12", "gamma_xy", "gammaxy"]),
            (4, "MACRO_GXZ", ["gxz", "g13", "e13", "gamma_xz", "gammaxz"]),
            (5, "MACRO_GYZ", ["gyz", "g23", "e23", "gamma_yz", "gammayz"])]
TIME_COLS = ["time", "t", "step_time", "steptime"]
TEMP_COLS = ["t_degc", "temp", "temperature", "tempc", "theta"]

STRESS_FREE_T = 1050.0      # ZHANG2022 processing temperature


def norm(s):
    return "".join(ch for ch in s.strip().lower() if ch.isalnum() or ch == "_")


def read_history(path, default_T):
    """Return (times, {driver: [values]}, temps).  Missing channels read zero."""
    with open(path) as fh:
        rows = list(csv.reader(fh))
    rows = [r for r in rows if r and any(c.strip() for c in r)]
    if len(rows) < 2:
        sys.exit("ERROR: %s has no data rows" % path)

    header = [norm(c) for c in rows[0]]
    # 'T' alone is ambiguous with time, so only treat it as temperature when a
    # separate time column exists.
    def find(names, skip=()):
        for i, h in enumerate(header):
            if h in names and i not in skip:
                return i
        return None

    it = find(TIME_COLS)
    if it is None:
        sys.exit("ERROR: no time column in %s (header: %s)" % (path, rows[0]))
    iT = find(TEMP_COLS + ["t"], skip=(it,))

    idx = {}
    for drv, _amp, names in CHANNELS:
        idx[drv] = find(names)

    missing = [n for d, n, _ in CHANNELS if idx[d] is None]
    if missing:
        print("  channels not in the file (taken as zero): %s" % ", ".join(missing))
    if iT is None:
        print("  no temperature column; holding %g degC throughout" % default_T)

    times, temps = [], []
    chans = dict((d, []) for d, _a, _n in CHANNELS)
    for r in rows[1:]:
        try:
            times.append(float(r[it]))
        except (ValueError, IndexError):
            continue                                   # skip stray text rows
        for d, _a, _n in CHANNELS:
            j = idx[d]
            v = 0.0
            if j is not None and j < len(r) and r[j].strip():
                v = float(r[j])
            chans[d].append(v)
        tv = default_T
        if iT is not None and iT < len(r) and r[iT].strip():
            tv = float(r[iT])
        temps.append(tv)

    if len(times) < 2:
        sys.exit("ERROR: fewer than two usable rows in %s" % path)
    if times[0] != 0.0:
        print("  history starts at t=%g; shifting it to 0" % times[0])
        t0 = times[0]
        times = [t - t0 for t in times]
    for a, b in zip(times, times[1:]):
        if b <= a:
            sys.exit("ERROR: the time column must increase strictly (%g then %g)"
                     % (a, b))
    return times, chans, temps


def amplitude_block(name, times, values):
    """*Amplitude in step time, four (t, value) pairs per line."""
    out = ["*Amplitude, Name=%s, Time=STEP TIME, Definition=TABULAR" % name]
    pairs = ["%.8g, %.8g" % (t, v) for t, v in zip(times, values)]
    for i in range(0, len(pairs), 4):
        out.append(", ".join(pairs[i:i + 4]))
    return "\n".join(out)


def keep_model(text):
    """Everything except the steps and the initial conditions -- the mesh, the
    orientation, the PBC and the original UMAT material cards all stay as they
    are, so this deck damages exactly like the tension decks do."""
    kept, in_step = [], False
    for kw, data in split_blocks(text):
        name = kwname(kw)
        if name == "step":
            in_step = True
            continue
        if name == "end step":
            in_step = False
            continue
        if in_step or name == "heading" or name.startswith("initial conditions"):
            continue
        kept.append((kw, data))
    return kept


CONTROLS = """*Controls, parameters=time incrementation
 8, 10, , 30, , , , 20, , ,
*Controls, parameters=field, field=displacement
 , 0.08
*Controls, parameters=line search
5"""

OUTPUT = "\n".join(
    ["*Output, field, number interval=%d, time marks=NO",
     "*Element Output, directions=YES",
     "S, E, EE, THE, IVOL, SDV",
     "*Node Output",
     "U, RF",
     "*Output, history, frequency=1"] +
    ["*Node Output, nset=ConstraintsDriver%d\nU, RF" % i for i in range(6)])


def build_steps(times, chans, temps, intervals, dt0, dtmax):
    tend = times[-1]
    S = []

    # ---- step 1: from the stress-free state to the start of the history ----
    S.append("*Step, Name=Precondition, nlgeom=NO, inc=100000")
    S.append("Cool %g -> %g degC while ramping the macro strain to its t=0 value"
             % (STRESS_FREE_T, temps[0]))
    S.append("*Static")
    S.append("0.001, 1.0, 1.0E-12, 0.0025")
    S.append(CONTROLS)
    S.append("*Boundary")
    for d, _amp, _n in CHANNELS:
        S.append("ConstraintsDriver%d, 1, 1, %.8g" % (d, chans[d][0]))
    S.append("*Temperature")
    S.append("AllNodes, %.8g" % temps[0])
    S.append(OUTPUT % intervals)
    S.append("*End Step")

    # ---- step 2: the coupon history ---------------------------------------
    S.append("*Step, Name=Coupon_history, nlgeom=NO, inc=1000000")
    S.append("Replay of the macroscopic strain and temperature history "
             "(%g time units, %d points)" % (tend, len(times)))
    S.append("*Static")
    S.append("%.8g, %.8g, 1.0E-12, %.8g" % (dt0 * tend, tend, dtmax * tend))
    S.append(CONTROLS)
    for d, amp, _n in CHANNELS:
        S.append("*Boundary, Amplitude=%s" % amp)
        S.append("ConstraintsDriver%d, 1, 1, 1.0" % d)
    S.append("*Temperature, Amplitude=MACRO_TEMP")
    S.append("AllNodes, 1.0")
    S.append(OUTPUT % intervals)
    S.append("*End Step")
    return "\n".join(S)


def main():
    ap = argparse.ArgumentParser(
        description="Drive the RVE with a macro strain/temperature history.")
    ap.add_argument("mesh", help="a ZHANG2022 RVE deck (mesh + PBC + UMAT cards)")
    ap.add_argument("history", help="CSV: time, exx..gyz, T")
    ap.add_argument("--out", default="RVE_history.inp", help="output deck")
    ap.add_argument("--default-temp", type=float, default=23.0,
                    help="temperature to hold if the CSV has no T column")
    ap.add_argument("--intervals", type=int, default=200,
                    help="field-output intervals per step (default 200)")
    ap.add_argument("--dt0", type=float, default=1e-3,
                    help="initial increment as a fraction of the history (1e-3)")
    ap.add_argument("--dtmax", type=float, default=1e-2,
                    help="maximum increment as a fraction of the history (1e-2)")
    args = ap.parse_args()

    print("history: %s" % args.history)
    times, chans, temps = read_history(args.history, args.default_temp)
    print("  %d points over t = 0 .. %g" % (len(times), times[-1]))
    print("  temperature %g -> %g degC (min %g, max %g)"
          % (temps[0], temps[-1], min(temps), max(temps)))
    for d, amp, _n in CHANNELS:
        v = chans[d]
        if any(v):
            print("  %-11s range %+.6g .. %+.6g" % (amp, min(v), max(v)))

    with open(args.mesh) as fh:
        text = fh.read()
    kept = keep_model(text)

    amps = [amplitude_block(amp, times, chans[d]) for d, amp, _n in CHANNELS]
    amps.append(amplitude_block("MACRO_TEMP", times, temps))

    parts = ["*Heading",
             " ZHANG2022 C/SiC RVE driven by a macroscopic history",
             " mesh/PBC/materials from: %s" % os.path.basename(args.mesh),
             " history: %s (%d points, t_end = %g)"
             % (os.path.basename(args.history), len(times), times[-1]),
             " built by make_history_driven_rve.py -- units mm, N, MPa, degC",
             emit_blocks(kept),
             "**",
             "** Macroscopic history as amplitudes; the *Boundary magnitudes are",
             "** 1.0 so each driver DOF simply follows its own table.",
             "\n".join(amps),
             "**",
             "*Initial Conditions, type=TEMPERATURE",
             "AllNodes, %.8g" % STRESS_FREE_T,
             build_steps(times, chans, temps, args.intervals,
                         args.dt0, args.dtmax)]

    with open(args.out, "w") as fh:
        fh.write("\n".join(parts) + "\n")
    print("")
    print("wrote %s" % args.out)
    print("  step 1 Precondition   %g -> %g degC, macro strain 0 -> eps(0)"
          % (STRESS_FREE_T, temps[0]))
    print("  step 2 Coupon_history %d-point replay, t_end = %g"
          % (len(times), times[-1]))
    print("")
    print("run it (keep the .ori file beside the deck):")
    print("  abaqus job=%s input=%s user=<path>/UMAT_CSIC_RVE_ZHANG2022_V1_0.for "
          "double interactive"
          % (os.path.splitext(os.path.basename(args.out))[0], args.out))
    print("")
    print("check first:  python3 verification/check_pbc.py %s" % args.out)


if __name__ == "__main__":
    main()
