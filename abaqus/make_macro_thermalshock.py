#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_macro_thermalshock.py
==========================
M7 -- the macro-scale cyclic thermal-shock pipeline.  Generates the decks that
produce the thesis's main results, designed around one rule (CLAUDE.md):

    ABAQUS RUNS ARE SLOW.  GET AS MUCH AS POSSIBLE OUT OF EACH ONE.

Three design decisions follow from that rule
--------------------------------------------
1. THE THERMAL ANALYSIS IS SHARED.  The temperature field does not depend on
   how thermal residual stress is treated, so one transient heat-transfer job
   per severity level serves ALL the TRS cases.  3 severities x 3 TRS cases is
   nine mechanical jobs but only THREE thermal jobs.

2. ELASTIC PROBES ARE INTERLEAVED.  A short, tiny-strain step is inserted after
   each checkpoint, with the cycle rate field set to zero.  It generates no
   damage (strain stays far below the stored threshold, and d_cyc needs a
   nonzero rate), but its reaction force gives the CURRENT secant stiffness.
   So E(N) at every checkpoint comes out of the SAME job -- no extra runs.
   This is what makes the model directly comparable to refs/[03], whose
   primary measurement is exactly the residual modulus versus cycle count.

3. RESTARTS ARE WRITTEN AT EVERY CHECKPOINT.  Residual-STRENGTH probes destroy
   the specimen, so they cannot be interleaved.  Instead each checkpoint writes
   a restart, and a separate short job continues from it to failure.  Nothing
   is ever recomputed from cycle zero.

Decks written
-------------
  <prefix>_HEAT_S<sev>.inp        transient heat transfer, N cycles.
                                  SHARED by every TRS case at that severity.
  <prefix>_MECH_S<sev>_TRS<case>.inp
                                  static, reads the temperature history from
                                  the heat job, with interleaved elastic probes
                                  and restarts at each checkpoint.
  <prefix>_RESID_S<sev>_TRS<case>_N<n>.inp
                                  restart continuation, monotonic tension to
                                  failure -> residual strength at cycle n.

TRS cases (docs/THESIS_PLAN.md issue 5)
---------------------------------------
  A  none      no *Expansion at all; the analysis starts stress free at T_lo.
  B  initial   manufacturing cooldown once, then the damage state is FROZEN
               (freeze_step) so TRS is carried as an initial condition only.
  C  full      manufacturing cooldown, and damage stays live for every cycle so
               TRS relaxes and redistributes as damage accumulates.
  The B-versus-C difference is the quantity the thesis is about.

Usage
  python3 make_macro_thermalshock.py --card RVE_macro_card.inp \\
        --expansion RVE_macro_expansion.inp --thermal RVE_thermal.inp
  python3 make_macro_thermalshock.py --validation-zhang2013     # 900<->300 C
  python3 make_macro_thermalshock.py --list-checks              # what to run first
"""
from __future__ import print_function

import argparse
import os
import sys

STRESS_FREE_C = 1050.0
PROBE_STRAIN = 1.0e-6          # elastic probe: far below any damage threshold
FAIL_STRAIN = 0.010            # residual-strength continuation target

#: severity levels: (label, T_hot C, T_cold C, film coefficient W/(mm^2.K))
#: h is the knob that sets the Biot number, i.e. how sharp the quench is.
SEVERITIES = {
    "L": dict(T_hi=900.0, T_lo=300.0, h=2.0e-4, note="mild, air"),
    "M": dict(T_hi=900.0, T_lo=300.0, h=2.0e-3, note="ZHANG2013 reference"),
    "H": dict(T_hi=1000.0, T_lo=23.0, h=2.0e-2, note="severe, water-like"),
}

TRS_CASES = ("A", "B", "C")


# ==========================================================================
# specimen mesh -- graded hexes, biased toward the quenched faces
# ==========================================================================
def graded(n, L, bias):
    """n+1 coordinates over [0, L], symmetric, clustered at BOTH ends.

    The thermal boundary layer during a quench sits within a fraction of the
    thickness; a uniform mesh either wastes elements in the core or fails to
    resolve the surface gradient.

    bias < 1 clusters toward the SURFACES (what a quench needs).
    bias > 1 would cluster toward the mid-plane -- the exact opposite.
    """
    if bias >= 1.0:
        raise ValueError("bias must be < 1 to refine at the surfaces; "
                         "got %g, which refines the mid-plane instead" % bias)
    out = []
    for i in range(n + 1):
        x = 2.0 * i / float(n) - 1.0          # -1 .. 1
        s = (abs(x) ** bias) * (1.0 if x >= 0 else -1.0)
        out.append(0.5 * L * (1.0 + s))
    return out


def plate_mesh(Lx, Ly, Lz, nx, ny, nz, bias=0.55):
    """Structured hex mesh of a plate, graded through the thickness (z)."""
    xs = [Lx * i / float(nx) for i in range(nx + 1)]
    ys = [Ly * j / float(ny) for j in range(ny + 1)]
    zs = graded(nz, Lz, bias)

    nid = {}
    nodes = []
    k = 0
    for iz, z in enumerate(zs):
        for iy, y in enumerate(ys):
            for ix, x in enumerate(xs):
                k += 1
                nid[(ix, iy, iz)] = k
                nodes.append((k, x, y, z))
    els = []
    e = 0
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                e += 1
                els.append((e,
                            nid[(ix, iy, iz)], nid[(ix + 1, iy, iz)],
                            nid[(ix + 1, iy + 1, iz)], nid[(ix, iy + 1, iz)],
                            nid[(ix, iy, iz + 1)], nid[(ix + 1, iy, iz + 1)],
                            nid[(ix + 1, iy + 1, iz + 1)],
                            nid[(ix, iy + 1, iz + 1)]))
    sets = {
        "ZLO": [nid[(ix, iy, 0)] for iy in range(ny + 1)
                for ix in range(nx + 1)],
        "ZHI": [nid[(ix, iy, nz)] for iy in range(ny + 1)
                for ix in range(nx + 1)],
        "XLO": [nid[(0, iy, iz)] for iz in range(nz + 1)
                for iy in range(ny + 1)],
        "XHI": [nid[(nx, iy, iz)] for iz in range(nz + 1)
                for iy in range(ny + 1)],
        "YLO": [nid[(ix, 0, iz)] for iz in range(nz + 1)
                for ix in range(nx + 1)],
    }
    # surface element faces for the film condition (S5 = -z, S6 = +z on C3D8)
    surf_lo = [(e[0], "S1") for e in els if e[0] <= nx * ny]
    surf_hi = [(e[0], "S2") for e in els if e[0] > nx * ny * (nz - 1)]
    return nodes, els, sets, surf_lo, surf_hi, zs


def emit_mesh(nodes, els, sets, etype):
    L = ["*Node"]
    for n, x, y, z in nodes:
        L.append("%d, %.8g, %.8g, %.8g" % (n, x, y, z))
    L.append("*Element, type=%s" % etype)
    for e in els:
        L.append(", ".join(str(v) for v in e))
    L.append("*ElSet, ElSet=ALL, Generate")
    L.append("1, %d, 1" % len(els))
    L.append("*NSet, NSet=ALLNODES, Generate")
    L.append("1, %d, 1" % len(nodes))
    for name, lbls in sorted(sets.items()):
        L.append("*NSet, NSet=%s" % name)
        u = sorted(set(lbls))
        for i in range(0, len(u), 16):
            L.append(", ".join(str(v) for v in u[i:i + 16]))
    return "\n".join(L)


def emit_surface(name, faces):
    L = ["*Surface, type=ELEMENT, name=%s" % name]
    for e, f in faces:
        L.append("%d, %s" % (e, f))
    return "\n".join(L)


# ==========================================================================
# thermal deck -- shared by every TRS case at the same severity
# ==========================================================================
def heat_steps(sev, ncycle, t_quench, t_dwell):
    s = SEVERITIES[sev]
    L = []
    for c in range(1, ncycle + 1):
        L.append("*Step, Name=Quench_%d, inc=100000" % c)
        L.append("Quench %g -> %g degC, h = %g W/(mm^2.K)"
                 % (s["T_hi"], s["T_lo"], s["h"]))
        L.append("*Heat Transfer, end=PERIOD, deltmx=25.")
        L.append("%.6g, %.6g, 1e-8, %.6g"
                 % (t_quench / 50.0, t_quench, t_quench / 10.0))
        L.append("*Sfilm")
        L.append("SURF_LO, F, %.6g, %.6g" % (s["T_lo"], s["h"]))
        L.append("SURF_HI, F, %.6g, %.6g" % (s["T_lo"], s["h"]))
        L.append(_heat_output())
        L.append("*End Step")
        L.append("*Step, Name=Reheat_%d, inc=100000" % c)
        L.append("Reheat back to %g degC" % s["T_hi"])
        L.append("*Heat Transfer, end=PERIOD, deltmx=25.")
        L.append("%.6g, %.6g, 1e-8, %.6g"
                 % (t_dwell / 50.0, t_dwell, t_dwell / 10.0))
        L.append("*Sfilm")
        L.append("SURF_LO, F, %.6g, %.6g" % (s["T_hi"], s["h"]))
        L.append("SURF_HI, F, %.6g, %.6g" % (s["T_hi"], s["h"]))
        L.append(_heat_output())
        L.append("*End Step")
    return "\n".join(L)


def _heat_output():
    return ("*Output, field, frequency=1\n"
            "*Node Output\nNT\n"
            "*Element Output\nHFL\n"
            "*Output, history, frequency=1\n"
            "*Node Output, nset=SURF_PROBE\nNT")


# ==========================================================================
# mechanical deck -- interleaved probes + restarts
# ==========================================================================
def mech_steps(sev, trs, ncycle, checkpoints, t_quench, t_dwell, heatjob,
               cyclejump, Lx):
    s = SEVERITIES[sev]
    L = []
    kstep = 0

    # ---- S1: manufacturing cooldown (TRS cases B and C only) -------------
    if trs in ("B", "C"):
        kstep += 1
        L.append("*Step, Name=Manufacturing_Cooldown, nlgeom=NO, inc=100000")
        L.append("Cool %g -> %g degC: thermal residual stress + initial damage"
                 % (STRESS_FREE_C, s["T_hi"]))
        L.append("*Static")
        L.append("0.005, 1.0, 1e-12, 0.05")
        L.append("*Temperature\nALLNODES, %.6g" % s["T_hi"])
        L.append(_mech_field(0.0))
        L.append(_mech_output(restart=True))
        L.append("*End Step")

    # ---- S2: probe at N = 0 ----------------------------------------------
    kstep += 1
    probe_step = {0: kstep}
    L.append(_probe_step("Probe_N0", Lx))

    # ---- cycles, in blocks between checkpoints ---------------------------
    done = 0
    for cp in checkpoints:
        nblk = cp - done
        if nblk <= 0:
            continue
        # cycles actually simulated in this block
        nsim = max(1, int(round(nblk / float(cyclejump))))
        rate = nblk / float(nsim) / (t_quench + t_dwell)
        for c in range(nsim):
            for half, tper, Tref in (("Quench", t_quench, s["T_lo"]),
                                     ("Reheat", t_dwell, s["T_hi"])):
                kstep += 1
                L.append("*Step, Name=%s_to%d_%d, nlgeom=NO, inc=100000"
                         % (half, cp, c + 1))
                L.append("%s half-cycle; this step represents %.3g real cycles"
                         % (half, (nblk / float(nsim)) / 2.0))
                L.append("*Static")
                L.append("%.6g, %.6g, 1e-12, %.6g"
                         % (tper / 100.0, tper, tper / 20.0))
                # temperature history from the SHARED heat job
                # op=NEW clears the probe displacement left by the previous
                # probe step; boundary conditions otherwise persist in Abaqus.
                L.append("*Boundary, op=NEW")
                L.append("XLO, 1\nYLO, 2\nZLO, 3")
                # Every mechanical cycle reads the SAME heat step, so the
                # thermal load really is identical cycle to cycle.  That is the
                # point: it is what creates the shakedown situation the
                # cycle-damage law exists to handle.
                hs = 1 if half == "Quench" else 2
                L.append("*Temperature, file=%s.odb, bstep=%d, estep=%d"
                         % (heatjob, hs, hs))
                L.append(_mech_field(rate))
                L.append(_mech_output(restart=False))
                L.append("*End Step")
        done = cp
        kstep += 1
        probe_step[cp] = kstep
        L.append(_probe_step("Probe_N%d" % cp, Lx))
    return "\n".join(L), probe_step


def _probe_step(name, Lx):
    """Elastic probe: prescribed STRAIN of PROBE_STRAIN over the gauge length.

    Cycle rate is set to zero so d_cyc cannot grow, and the strain is orders of
    magnitude below any damage threshold so the monotonic damage cannot grow
    either.  The reaction on XHI therefore measures the CURRENT secant
    stiffness, giving E(N) from inside the same job.
    """
    L = ["*Step, Name=%s, nlgeom=NO, inc=100" % name,
         "Elastic probe (strain %.1e): current secant stiffness, no damage"
         % PROBE_STRAIN,
         "*Static",
         "1.0, 1.0, 1e-12, 1.0",
         "*Boundary, op=NEW",
         "XLO, 1\nYLO, 2\nZLO, 3",
         "XHI, 1, 1, %.10g" % (PROBE_STRAIN * Lx),
         _mech_field(0.0),
         _mech_output(restart=True),
         "*End Step"]
    return "\n".join(L)


def _mech_field(rate):
    """Field variable 1 = cycles per unit time, read by KMACRO31 (PREDEFN=1)."""
    return "*Field, variable=1\nALLNODES, %.10g" % rate


def _mech_output(restart):
    out = ("*Output, field, number interval=20, time marks=NO\n"
           "*Element Output, directions=YES\n"
           "S, E, EE, THE, IVOL, SDV\n"          # SDV = every state variable
           "*Node Output\nU, RF, NT\n"
           "*Output, history, frequency=1\n"
           "*Node Output, nset=XHI\nU, RF\n"
           "*Element Output, elset=ALL\nSDV9, SDV10, SDV17, SDV18\n")
    if restart:
        out += "*Restart, write, overlay\n"
    return out


# ==========================================================================
def write(path, parts):
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print("  wrote %s" % path)


def patch_card(card_text, slot, value):
    """Set 1-based `slot` of the MACRO *User Material card.

    Needed for TRS case B: the manufacturing cooldown must run with damage
    LIVE, and every later step with damage FROZEN, so that the thermal residual
    stress is carried only as an initial condition and never relaxes.  That is
    exactly what PROPS(26) freeze_step does -- damage evolves only while
    KSTEP <= freeze_step.  Without this patch, cases B and C produce identical
    results and the central comparison of the thesis is empty.
    """
    lines = card_text.splitlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().lower().startswith("*user material"):
            head = i
            break
    else:
        raise SystemExit("no *User Material line in the macro card")
    vals, tail = [], len(lines)
    for j in range(head + 1, len(lines)):
        if lines[j].lstrip().startswith("*"):
            tail = j
            break
        vals.extend(v.strip() for v in lines[j].split(",") if v.strip())
    else:
        tail = len(lines)
    if slot > len(vals):
        raise SystemExit("macro card has %d constants, cannot set slot %d"
                         % (len(vals), slot))
    vals[slot - 1] = "%.10g" % value
    body = []
    for k in range(0, len(vals), 8):
        body.append(", ".join(vals[k:k + 8]))
    return "\n".join(lines[:head + 1] + body + lines[tail:])


def read_block(path, default):
    if path and os.path.exists(path):
        return open(path).read().rstrip()
    return default


PLACEHOLDER_CARD = """** PLACEHOLDER macro card -- replace with the RVE output
** (postprocess/homogenize.py -> <prefix>_macro_card.inp).
** Running with these numbers produces a WORKING deck but MEANINGLESS results.
*Material, Name=CSIC_MACRO_CDM
*Depvar
22,
*User Material, constants=47
3., 105000., 105000., 52000., 0.10, 0.25, 0.25, 36000.
22000., 22000., 220., 480., 220., 480., 110., 90.
90., 2., 2., 2., 2., 0.99, 0.99, 0.02
0.10, 1000000., 0.25, 1., 1., 0.5, 1., 0.
0., 0., 0., 31., 0.8, 1., 8.2882e-02, 3.
1., 0.30, 0.95, 0.30, 0., 1., 0."""

PLACEHOLDER_EXPANSION = """*Expansion, type=ORTHO, zero=1050.
2.5e-06, 2.5e-06, 5.0e-06"""

PLACEHOLDER_THERMAL = """** PLACEHOLDER homogenised thermal properties.
** kbar MUST come from the RVE conductivity job (RVE_COND) -- the quench
** result is more sensitive to this than to almost anything else.
*Conductivity, type=ORTHO
0.015, 0.015, 0.004
*Density
2.1e-09,
*Specific Heat
1.0e+09,"""


def main():
    ap = argparse.ArgumentParser(description="Macro cyclic thermal-shock decks")
    ap.add_argument("--prefix", default="TS")
    ap.add_argument("--card", help="macro *Material block from homogenize.py")
    ap.add_argument("--expansion", help="*Expansion block from homogenize.py")
    ap.add_argument("--thermal", help="homogenised *Conductivity/*Density/*Specific Heat")
    ap.add_argument("--sev", nargs="+", default=["M"], choices=sorted(SEVERITIES))
    ap.add_argument("--trs", nargs="+", default=list(TRS_CASES), choices=TRS_CASES)
    ap.add_argument("--checkpoints", type=int, nargs="+",
                    default=[5, 10, 20, 40, 60],
                    help="cycle counts at which to probe E and write a restart")
    ap.add_argument("--cycle-jump", type=float, default=5.0,
                    help="real cycles represented by one simulated cycle")
    ap.add_argument("--heat-cycles", type=int, default=2,
                    help="explicit cycles in the SHARED heat job")
    ap.add_argument("--t-quench", type=float, default=30.0, help="s")
    ap.add_argument("--t-dwell", type=float, default=120.0, help="s")
    ap.add_argument("--dims", type=float, nargs=3, default=[40.0, 10.0, 3.0],
                    help="Lx Ly Lz in mm")
    ap.add_argument("--mesh", type=int, nargs=3, default=[20, 6, 12])
    ap.add_argument("--validation-zhang2013", action="store_true",
                    help="preset for refs/[03]: 900<->300 C, N up to 60")
    ap.add_argument("--list-checks", action="store_true")
    args = ap.parse_args()

    if args.list_checks:
        print(CHECKS)
        return 0

    if args.validation_zhang2013:
        args.sev = ["M"]
        args.checkpoints = [5, 10, 20, 40, 60]

    Lx, Ly, Lz = args.dims
    nx, ny, nz = args.mesh
    nodes, els, sets, slo, shi, zs = plate_mesh(Lx, Ly, Lz, nx, ny, nz)
    dz_surf = zs[1] - zs[0]
    print("mesh: %d nodes, %d elements; thinnest through-thickness layer "
          "= %.4g mm (of %.4g mm)" % (len(nodes), len(els), dz_surf, Lz))

    card = read_block(args.card, PLACEHOLDER_CARD)
    expan = read_block(args.expansion, PLACEHOLDER_EXPANSION)
    therm = read_block(args.thermal, PLACEHOLDER_THERMAL)
    if not args.card:
        print("  !! using the PLACEHOLDER macro card -- results are meaningless")
    if not args.thermal:
        print("  !! using PLACEHOLDER thermal properties -- run RVE_COND first")

    sets2 = dict(sets)
    sets2["SURF_PROBE"] = [nodes[0][0], nodes[-1][0]]

    # ---------------- thermal jobs (shared) ------------------------------
    for sev in args.sev:
        parts = ["*Heading",
                 " Macro thermal shock, SHARED heat transfer, severity %s (%s)"
                 % (sev, SEVERITIES[sev]["note"]),
                 emit_mesh(nodes, els, sets2, "DC3D8"),
                 emit_surface("SURF_LO", slo),
                 emit_surface("SURF_HI", shi),
                 "*Material, Name=CSIC_MACRO_THERMAL",
                 therm.replace("** PLACEHOLDER homogenised thermal properties.",
                               "").strip(),
                 "*Solid Section, ElSet=ALL, Material=CSIC_MACRO_THERMAL",
                 "1.0,",
                 "*Initial Conditions, type=TEMPERATURE\nALLNODES, %.6g"
                 % SEVERITIES[sev]["T_hi"],
                 heat_steps(sev, args.heat_cycles, args.t_quench, args.t_dwell)]
        write("%s_HEAT_S%s.inp" % (args.prefix, sev), parts)

    # ---------------- mechanical jobs ------------------------------------
    probe_steps = {}
    for sev in args.sev:
        heatjob = "%s_HEAT_S%s" % (args.prefix, sev)
        for trs in args.trs:
            # TRS B: damage live only during the cooldown (step 1), frozen
            # afterwards.  A and C keep damage live throughout.
            this_card = patch_card(card, 26, 1.0) if trs == "B" else card
            body = [this_card]
            if trs != "A":
                body.append(expan)
            body.append("*Solid Section, ElSet=ALL, Material=CSIC_MACRO_CDM")
            body.append("1.0,")
            T0 = SEVERITIES[sev]["T_hi"]
            init = STRESS_FREE_C if trs in ("B", "C") else T0
            parts = ["*Heading",
                     " Macro thermal shock, severity %s, TRS case %s"
                     % (sev, trs),
                     "** TRS %s: %s" % (trs, {
                         "A": "no expansion at all -- no thermal residual stress",
                         "B": "cooldown once, damage then frozen "
                              "(TRS as initial condition only)",
                         "C": "cooldown, damage live every cycle "
                              "(TRS relaxes and redistributes)"}[trs]),
                     emit_mesh(nodes, els, sets2, "C3D8"),
                     "\n".join(body),
                     "*Initial Conditions, type=TEMPERATURE\nALLNODES, %.6g"
                     % init,
                     "*Initial Conditions, type=FIELD, variable=1\nALLNODES, 0.",
                     "** symmetry: XLO/YLO/ZLO-free plate, restrained minimally",
                     "*Boundary\nXLO, 1\nYLO, 2\nZLO, 3",
                     None]
            body_steps, probe_step = mech_steps(
                sev, trs, max(args.checkpoints), args.checkpoints,
                args.t_quench, args.t_dwell, heatjob, args.cycle_jump, Lx)
            parts[-1] = body_steps
            write("%s_MECH_S%s_TRS%s.inp" % (args.prefix, sev, trs), parts)
            probe_steps[(sev, trs)] = probe_step

    # ---------------- residual-strength continuations --------------------
    for sev in args.sev:
        for trs in args.trs:
            base = "%s_MECH_S%s_TRS%s" % (args.prefix, sev, trs)
            for cp in args.checkpoints:
                kp = probe_steps[(sev, trs)][cp]
                parts = ["*Heading",
                         " Residual strength after %d cycles "
                         "(restart from %s)" % (cp, base),
                         "** Continues from probe step %d of %s, so nothing is"
                         % (kp, base),
                         "** recomputed from cycle zero.",
                         "*Restart, read, step=%d" % kp,
                         "*Step, Name=Residual_N%d, nlgeom=NO, inc=100000" % cp,
                         "Monotonic tension to failure",
                         "*Static",
                         "0.002, 1.0, 1e-12, 0.02",
                         "*Boundary, op=NEW",
                         "XLO, 1\nYLO, 2\nZLO, 3",
                         "XHI, 1, 1, %.6g" % (FAIL_STRAIN * Lx),
                         _mech_field(0.0),
                         _mech_output(restart=False),
                         "*End Step"]
                write("%s_RESID_S%s_TRS%s_N%d.inp"
                      % (args.prefix, sev, trs, cp), parts)

    print("\n" + CHECKS)
    return 0


CHECKS = """RUN THESE THREE SMALL CHECKS BEFORE THE FULL MATRIX
====================================================
Each is minutes, not hours, and each can invalidate the whole matrix.

  1. THERMAL BOUNDARY LAYER.  Run one <prefix>_HEAT_S<sev>.inp alone and plot
     NT through the thickness at the end of the first quench.  The surface
     gradient must be resolved by several elements.  If the first two nodes
     already sit at the bath temperature, increase nz or the grading bias --
     an unresolved gradient makes the whole thermal-shock claim worthless.
     Also record the Biot number  Bi = h*Lz/kbar  and report it: it is the
     dimensionless severity the thesis plots against.

  2. TEMPERATURE MAPPING.  Run the mechanical job for TWO cycles only and check
     in the .dat/.msg that the *Temperature, file= step actually read the heat
     ODB (Abaqus warns loudly if the step/time mapping fails, and then silently
     holds the initial temperature -- which looks like a converged, wrong
     answer).  Compare NT in the mechanical ODB against the heat ODB.

  3. CYCLE-JUMP ERROR.  Run one case with --cycle-jump 1 (explicit) and one
     with the intended jump, both to the first checkpoint, and compare the
     probe stiffness.  verify_thermshock.py T6 shows the material-point error
     is 0.03 % at x10, but the structural error also involves redistribution
     and has to be measured once, not assumed.

Only after these three should the 3 severities x 3 TRS cases be launched."""


if __name__ == "__main__":
    sys.exit(main())
