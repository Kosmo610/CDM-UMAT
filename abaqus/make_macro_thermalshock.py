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
  python3 make_macro_thermalshock.py --specimen ZHANG2013        # validation run
  python3 make_macro_thermalshock.py --sev L M H                 # Biot sweep
  python3 make_macro_thermalshock.py --list-checks              # what to run first
"""
from __future__ import print_function

import argparse
import os
import re
import sys

STRESS_FREE_C = 1050.0
PROBE_STRAIN = 1.0e-6          # elastic probe: far below any damage threshold
FAIL_STRAIN = 0.010            # residual-strength continuation target

#: Severity levels, chosen to SWEEP THE BIOT NUMBER rather than to be
#: round numbers.  h comes from abaqus/quench_calibration.py, which solves
#: the 1-D transient for the film coefficient that reproduces each paper's
#: own stated cooling time.  Run that script before changing anything here.
#:
#: The point of the ladder: at Bi = 0.05 -- which is where refs/[03]
#: actually sits -- the through-thickness gradient is only 3-15 % of the
#: temperature drop, so the uniform-field assumption of refs/[17] is very
#: nearly right.  By Bi = 5 the gradient is essentially the whole drop and
#: that assumption cannot survive.  Bracketing the crossover is the
#: contribution; asserting that gradients matter is not.
#:
#: h in mW/(mm^2.K) = the SI value / 1e3.  NOT /1e6, which is what this file
#: carried until 2026-08-11.  The unit is forced by the energy unit of the
#: tonne-mm-s set (mJ), the same derivation that fixes conductivity at
#: mW/(mm.K); eval_correlations.py spells it out under "THE DECK'S THERMAL
#: UNIT".  h and k were both 1000x low, so Bi = h.L/k was RIGHT and only the
#: time scale was wrong -- the quench would have run 1000x slow and converged
#: beautifully doing it.  `thermal_audit` now recomputes Bi AND Fo from the
#: card the deck actually carries, because Bi alone cannot see this.
#:
#: Two kinds of entry, and they are not the same kind of fact:
#:   bi_target  -- the ladder.  Bi is the datum and h is DERIVED at build time
#:                 from the deck's own kbar_3 and the specimen's own half
#:                 thickness, so the label is exact for whatever specimen and
#:                 whatever kbar the deck ends up carrying.
#:   h          -- the published tests.  h is the datum (quench_calibration.py
#:                 solved it from the paper's own stated cooling time) and Bi
#:                 is whatever our kbar_3 makes it.
SEVERITIES = {
    "L": dict(T_hi=900.0, T_lo=300.0, bi_target=0.05,
              note="Bi~0.05: the refs/[03] validation point, near-uniform"),
    "M": dict(T_hi=900.0, T_lo=300.0, bi_target=1.0,
              note="Bi~1: the crossover, gradient ~45 % of the drop"),
    "H": dict(T_hi=900.0, T_lo=300.0, bi_target=5.0,
              note="Bi~5: gradient dominated"),
    # The two published tests, at their OWN calibrated film coefficients.
    # These are the validation runs; the ladder above is the parameter study.
    # `protocol` is what the PAPER states -- a cooling time to a stated
    # temperature.  h is then whatever reproduces that ON OUR OWN CARD, and
    # 2026-08-11 is when it stopped being hard-coded: 199.0 W/(m^2.K) was
    # solved on refs/[03]'s rho and refs/[20]'s cp with refs/[12]'s k, and
    # pairing that h with OUR kbar_3 is the one combination that belongs to
    # no material at all.  Re-solved on our card the same 15 s needs 161.7,
    # and Bi lands at 0.0445 rather than either 0.0475 or the 0.0548 that
    # mixing the two produces.
    "Z": dict(T_hi=900.0, T_lo=300.0, spec="ZHANG2013",
              note="refs/[03] Zhang 2013 as tested: 900->300 C in 15 s on "
                   "an iron plate, 3 mm thick"),
    "Y": dict(T_hi=1300.0, T_lo=300.0, spec="YIN2002",
              note="refs/[02] Yin 2002 as tested: 1300->300 C, 60 s in "
                   "air, 4 mm thick -- much gentler than refs/[03]"),
}

#: Our own homogenised through-thickness conductivity, W/(m.K) == mW/(mm.K),
#: measured on LTH2_COND_P32 (32.4 % matrix porosity, the stiffness-route
#: card).  quench_calibration.py solves h on refs/[12]'s 6.29, which is a
#: DIFFERENT material's measurement; using it to LABEL our deck would put
#: 6.29/5.4490 = 1.154 into every Biot number the thesis reports.
KBAR3_MEASURED = 5.4490


#: Our homogenised bulk density and RT specific heat in SI, for solving the
#: published protocols on the card the deck carries.  homogenised_thermal()
#: derives both; these are its answers at the default porosity, kept here so
#: severity() does not have to rebuild the whole card to ask one question.
RHO_BAR_SI, CP_BAR_SI = 2008.2, 681.3


def severity(sev, kbar3, lz, rho_si=RHO_BAR_SI, cp_si=CP_BAR_SI):
    """(h in mW/(mm^2.K), Bi) for the plate this deck actually builds.

    `lz` is the FULL thickness; the plate is cooled on both faces, so the
    conduction length is lz/2.  That halving is the difference between
    quench_calibration.py's 0.0445 for refs/[03] and the 0.0890 you get by
    reaching for the thickness -- it is not a detail.

    Two kinds of severity, resolved two ways:
      bi_target  the ladder.  h = Bi.k/L, so the label is exact.
      spec       a published protocol.  h is SOLVED from the paper's stated
                 cooling time on OUR rho, cp and kbar_3, and Bi is the
                 consequence.  Nothing here is carried over from the
                 properties the original calibration happened to use.
    """
    s = SEVERITIES[sev]
    half = 0.5 * lz
    if "bi_target" in s:
        h = s["bi_target"] * kbar3 / half
        return h, s["bi_target"]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import quench_calibration as qc
    spec = dict(qc.SPECIMENS[s["spec"]])
    spec["thickness"] = lz * 1.0e-3            # the deck's plate, in metres
    got = qc.solve_h(spec, dict(rho=rho_si, cp=cp_si, k3=kbar3))
    h_si = got[0] if isinstance(got, (tuple, list)) else got
    if h_si is None:
        raise SystemExit(
            "no film coefficient reproduces the %s protocol on this card: "
            "even an infinite h is too slow, which means the card's "
            "diffusivity is wrong, not the protocol" % s["spec"])
    return h_si * 1.0e-3, h_si * 1.0e-3 * half / kbar3

#: Specimen geometries taken from the papers, not invented.
#: (Lx, Ly, Lz) mm with Lz the THROUGH-THICKNESS direction that is quenched.
SPECIMENS = {
    "ZHANG2013": dict(
        dims=(12.5, 6.0, 3.0), mesh=(10, 6, 12), sev="Z",
        checkpoints=(20, 40, 60), t_quench=15.0, t_dwell=600.0,
        note="refs/[03] Fig. 1: 122 mm overall, 17.5 mm grip, R50 shoulders, "
             "6 mm gauge width, 3 mm thick.  Modelled as the GAUGE SECTION "
             "only (12.5 x 6 x 3): that is where the tensile test measures "
             "and where failure occurs, and the thermal problem is "
             "through-thickness so the shoulders do not change it."),
    "YIN2002": dict(
        dims=(20.0, 6.0, 4.0), mesh=(12, 6, 14), sev="Y",
        checkpoints=(20, 50, 100), t_quench=60.0, t_dwell=30.0,
        note="refs/[02]: 4 x 6 x 140 mm bar, 3-point bend over a 20 mm "
             "span.  Modelled as the SPAN (20 x 6 x 4).  N.B. the residual "
             "property is FLEXURAL strength, so the post-quench probe has "
             "to be a bend, not a tension -- not yet implemented."),
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
def quench_dt0(alpha, lz, t_quench, frac=0.02):
    """First time increment of a quench step, in seconds.

    NOT a fraction of the step.  The gradient this whole analysis exists to
    resolve peaks after about one DIFFUSION time, tau = (lz/2)^2 / alpha,
    which for our card is 0.565 s -- while t_quench/50 is 0.600 s at the
    default step length and 0.300 s even at the 15 s of refs/[03].  The old
    rule therefore put the first sample at or past the peak, and the reported
    peak gradient would have been whatever the second increment happened to
    see.  Converged, plausible, and low.

    Capped at t_quench/50 so a very slow quench does not get a needlessly
    fine start, and floored at 1e-6 s so a pathological card cannot ask for
    zero.  dtmax stays generous: `deltmx` shrinks the increment while the
    front is steep and lets it grow once the plate equilibrates, which is
    what makes one job cover both.
    """
    tau = (0.5 * lz) ** 2 / alpha
    return max(1.0e-6, min(frac * tau, t_quench / 50.0))


def heat_steps(sev, ncycle, t_quench, t_dwell, h=None, bi=None, dt0=None):
    s = SEVERITIES[sev]
    h = s["h"] if h is None else h
    dt0 = t_quench / 50.0 if dt0 is None else dt0
    L = []
    for c in range(1, ncycle + 1):
        L.append("*Step, Name=Quench_%d, inc=100000" % c)
        L.append("Quench %g -> %g degC, h = %g mW/(mm^2.K) = %g W/(m^2.K)%s"
                 % (s["T_hi"], s["T_lo"], h, h * 1.0e3,
                    "" if bi is None else ", Bi = %.4g" % bi))
        L.append("*Heat Transfer, end=PERIOD, deltmx=25.")
        L.append("%.6g, %.6g, 1e-8, %.6g"
                 % (dt0, t_quench, t_quench / 10.0))
        L.append("*Sfilm")
        L.append("SURF_LO, F, %.6g, %.6g" % (s["T_lo"], h))
        L.append("SURF_HI, F, %.6g, %.6g" % (s["T_lo"], h))
        L.append(_heat_output())
        L.append("*End Step")
        L.append("*Step, Name=Reheat_%d, inc=100000" % c)
        L.append("Reheat back to %g degC" % s["T_hi"])
        L.append("*Heat Transfer, end=PERIOD, deltmx=25.")
        L.append("%.6g, %.6g, 1e-8, %.6g"
                 % (t_dwell / 50.0, t_dwell, t_dwell / 10.0))
        L.append("*Sfilm")
        L.append("SURF_LO, F, %.6g, %.6g" % (s["T_hi"], h))
        L.append("SURF_HI, F, %.6g, %.6g" % (s["T_hi"], h))
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
        # ALL of a block's cycles are counted on the QUENCH halves, none on
        # the reheats.  A quench step BEGINS at T_hi, so the severity window
        # (SDV 29) equals the cycle's peak temperature from its very first
        # increment and the fC column is exact -- while the failure-index
        # drive still sweeps the full T_hi -> T_lo stress excursion, which
        # contains the same states as the reheat in reverse.  Spreading the
        # rate over the reheat instead would let the window fill from T_lo
        # and weight a non-monotonic fC peak during every rise (a1-0018,
        # the severity paradox).  The reheat still runs -- it restores the
        # stress state -- it just counts no cycles.
        rate = nblk / float(nsim) / t_quench
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
                L.append(_mech_field(rate if half == "Quench" else 0.0))
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
           # SDV9/10 damage, 17 d_cyc, 18 N, 19 Hashin, 23 Tsai-Wu,
           # 24 D-criterion, 25 latch flag -- the failure-criterion
           # comparison needs all three indices at every history frame.
           # SDV29 TWMAX: the audit that a cycling block really sat at
           # its Tmax -- the fC column is evaluated there (a1-0018).
           "*Element Output, elset=ALL\n"
           "SDV9, SDV10, SDV17, SDV18, SDV19, SDV23, SDV24, SDV25, "
           "SDV29\n")
    if restart:
        out += "*Restart, write, overlay\n"
    return out


# ==========================================================================
def write(path, parts):
    with open(path, "w") as f:
        f.write("\n".join(parts) + "\n")
    print("  wrote %s" % path)


#: Fracture-energy slots, 1-based, with the strength and modulus each one is
#: paired against.  Taken from KMACRO31's own KABAND calls, not assumed:
#:     CALL KABAND(XT*XT/(2*E1)*CELENT,G1T,...)   -> slot 32 uses PROPS(11),(2)
#:     CALL KABAND(YT*YT/(2*E2)*CELENT,GTT,...)   -> slot 34 uses PROPS(13),(3)
#: The fixed-exponent fallback A that KABAND returns for a zero entry lives in
#: slots 18-21 in the same order.
GF_MODES = ((32, "1t", 11, 2, 18), (33, "1c", 12, 2, 19),
            (34, "2t", 13, 3, 20), (35, "2c", 14, 3, 21))

#: Which f(T) column scales which slot, again read off KMACRO31:
#: F(1)->E1, F(2)->E2 and E3, F(4)->Xt and Xc, F(5)->Yt and Yc.
GF_TCOL = {2: 1, 3: 2, 11: 4, 12: 4, 13: 5, 14: 5}


def _kaband(g0le, gf, afix):
    """Python mirror of KABAND in src/UMAT_CSIC_THERMSHOCK_V3_0.for.

    Kept here rather than imported so that this validator has no dependency
    on the postprocess package: deck generation must work in a bare checkout.
    verification/check_gf_scale_transfer.py holds the same mirror and tests it
    against the Fortran text.
    """
    if gf == 0.0:
        return afix
    if gf < 0.0:
        a = 2.0 * g0le / (-gf) if (-gf) > 0.02 * g0le else 50.0
    else:
        a = 2.0 * g0le / (gf - g0le) if gf > 1.02 * g0le else 50.0
    return min(50.0, max(1.0e-2, a))


def _le_list(le):
    """Accept a single characteristic length or a range of them."""
    if le is None:
        return []
    if isinstance(le, (int, float)):
        le = [le]
    return sorted(set(float(v) for v in le if v and float(v) > 0.0))


def gf_audit(p, nt, le=None):
    """What each fracture-energy slot will actually DO inside KMACRO31.

    Two silent failures live in these four numbers, and neither one makes the
    UMAT complain, so neither can be caught anywhere but here.

    A POSITIVE entry is the Ch.4 4.9-16 defect.  Positive means the TOTAL area
    convention, Gf = le*g0 + le*2*g0/A, which carries whatever length made it.
    The only maker of macro cards in this repository is postprocess/
    homogenize.py, and it extracts with the RVE edge, 3.5 mm, while a macro
    element here is 0.68-0.94 mm.  KABAND takes the number without complaint
    and returns a softening exponent several times too small -- a branch that
    sheds load too slowly, so the specimen keeps carrying stress it should
    have lost.  That over-predicts residual strength, which is the quantity
    Ch.6 reports, so the error is non-conservative.

    A CLAMPED entry is the other one.  KABAND holds A inside [0.01, 50], and
    A = 50 is specifically the snap-back fallback: the element is too long to
    resolve that mode's crack band at all, and the card silently stops meaning
    what the RVE measured.  Since KMACRO31 scales E and X by the f(T) table
    but leaves Gf alone, g0 moves with temperature while |Gf| does not -- so a
    mode can be fine at the reference temperature and clamped at another.  The
    audit therefore walks every row of the table, not just the first.

    `le` is the macro element's characteristic length (CELENT, the cube root
    of the element volume for a hex).  Pass the real graded range; without it
    only the sign can be judged.
    """
    les = _le_list(le)
    rows = []
    for slot, mode, xslot, eslot, aslot in GF_MODES:
        gf = p[slot - 1]
        rec = dict(slot=slot, mode=mode, gf=gf, afix=p[aslot - 1],
                   sign=("total" if gf > 0.0 else
                         "off" if gf == 0.0 else "inelastic"),
                   states=[])
        X0, E0 = p[xslot - 1], p[eslot - 1]
        for T, fx, fe in _t_factors(p, nt, xslot, eslot):
            X, E = X0 * fx, E0 * fe
            if X <= 0.0 or E <= 0.0:
                continue
            g0 = X * X / (2.0 * E)
            for lc in les:
                A = _kaband(g0 * lc, gf, rec["afix"])
                rec["states"].append(dict(
                    T=T, le=lc, g0=g0, A=A,
                    clamped=("snapback" if A >= 50.0 - 1e-9 else
                             "floor" if A <= 1.0e-2 + 1e-12 else "")))
        rows.append(rec)
    return rows


def gf_temperature_drift(rows):
    """How far A wanders across the temperature table, per mode.

    Holding Gf fixed while E and X move is an ASSUMPTION, and until
    2026-08-06 it was an unstated one.  a1-0011 sourced its direction:
    Snead refs/[06] Fig. 14 and section 2.7.3 report that SiC's fracture
    resistance is constant or RISING to 1000 C, never falling.  Our card
    holds Gf fixed, so at temperature the card understates |Gf|, which
    overstates A = 2*g0*le/|Gf|, which softens faster and predicts MORE
    damage.  The error is therefore conservative for life prediction --
    the one direction we can afford.

    The size is small because E and X move together: A scales as
    g0 = X^2/(2E), and refs/[10]'s four measured temperatures move g0 by
    at most 5.1 % to 1273 K, while our own f(T) table moves it by 5.9 %.
    Returns {mode: (A_min, A_max, drift)} with drift = A_max/A_min - 1,
    at a single le so the length cancels.
    """
    out = {}
    for rec in rows:
        per_le = {}
        for st in rec["states"]:
            per_le.setdefault(st["le"], []).append(st["A"])
        best = None
        for le, As in per_le.items():
            if len(As) < 2:
                continue
            d = max(As) / min(As) - 1.0
            if best is None or d > best[2]:
                best = (min(As), max(As), d)
        if best is not None:
            out[rec["mode"]] = best
    return out


def _t_factors(p, nt, xslot, eslot):
    """(T, strength multiplier, modulus multiplier) for every table row.

    The table starts at PROPS(48) and is 8 wide: T, fE1, fE2, fG, fXt, fYt,
    fS, fC.  With no table there is still one state -- the reference row,
    which is 1.0 by construction.
    """
    xcol, ecol = GF_TCOL[xslot], GF_TCOL[eslot]
    if nt <= 0 or len(p) < 47 + 8 * nt:
        return [(None, 1.0, 1.0)]
    out = []
    for i in range(nt):
        row = p[47 + 8 * i:55 + 8 * i]
        out.append((row[0], row[xcol], row[ecol]))
    return out


def check_macro_card(card_text, where="", le=None, allow_total_gf=False):
    """Mirror KMACRO31's own card guards in Python, and audit what it accepts.

    Every rejection down to the failure-criterion block is one that the UMAT
    would raise as a CALL XIT at job start.  Catching it here costs nothing;
    catching it in Abaqus costs a submission, a queue wait and a confusing
    .msg.

    The fracture-energy check at the end is a different animal and is worth
    keeping straight: KABAND does NOT reject a positive Gf.  It accepts it,
    runs, and returns the wrong softening branch.  There is no CALL XIT to
    mirror, so this validator is the only place the mistake can be stopped.
    `allow_total_gf` exists for a card whose Gf really was measured at the
    macro element's own length -- nothing in this repository produces one.
    """
    lines = card_text.splitlines()
    ndep, vals, head = None, [], None
    for i, ln in enumerate(lines):
        s = ln.lstrip().lower()
        if s.startswith("*depvar"):
            for j in range(i + 1, len(lines)):
                t = lines[j].strip()
                if t.startswith("*"):
                    break
                ndep = int(float(t.split(",")[0]))
                break
        if s.startswith("*user material"):
            head = i
            for j in range(i + 1, len(lines)):
                if lines[j].lstrip().startswith("*"):
                    break
                vals.extend(v.strip() for v in lines[j].split(",") if v.strip())
            break
    tag = (" in " + where) if where else ""
    if head is None:
        raise SystemExit("macro card%s: no *User Material line" % tag)
    p = [float(v) for v in vals]
    n = len(p)

    declared = None
    m = re.search(r"constants\s*=\s*(\d+)", lines[head], re.I)
    if m:
        declared = int(m.group(1))
    if declared is not None and declared != n:
        raise SystemExit("macro card%s: constants=%d but %d values are listed"
                         % (tag, declared, n))
    if n < 47 or abs(p[35] - 31.0) > 1e-9:
        raise SystemExit("macro card%s: PROPS(36) must be 31.0 (got %s), "
                         "NPROPS >= 47 (got %d)" % (tag, p[35] if n >= 36
                                                    else "n/a", n))
    nt = int(round(p[46]))
    legal = (47 + 8 * nt, 49 + 8 * nt, 56 + 8 * nt, 58 + 8 * nt)
    if nt < 0 or n not in legal:
        raise SystemExit("macro card%s: NT=%d needs NPROPS in %s, got %d"
                         % (tag, nt, ", ".join(str(v) for v in legal), n))
    # The tangent block is the LAST thing on the card, so strip it before the
    # criterion block is located -- otherwise 58+8*NT would be read as a card
    # with no criterion block and the 41.0 guard would never be checked.
    itan = None
    if n in (49 + 8 * nt, 58 + 8 * nt):
        if abs(p[n - 1] - 33.0) > 1e-9:
            raise SystemExit("macro card%s: tangent block must end with 33.0, "
                             "got %g" % (tag, p[n - 1]))
        itan = int(round(p[n - 2]))
        if itan not in (0, 1):
            raise SystemExit("macro card%s: ITAN must be 0 or 1, got %d"
                             % (tag, itan))
        p, n = p[:n - 2], n - 2
    if n == 56 + 8 * nt:
        if abs(p[55 + 8 * nt] - 41.0) > 1e-9:
            raise SystemExit("macro card%s: failure-criterion block must end "
                             "with 41.0, got %g" % (tag, p[55 + 8 * nt]))
        icrit = int(round(p[47 + 8 * nt]))
        idmode = int(round(p[50 + 8 * nt]))
        dcs = p[51 + 8 * nt:54 + 8 * nt]
        if icrit > 0:
            if ndep is None or ndep < 29:
                raise SystemExit("macro card%s: ICRIT>0 needs *Depvar >= 29 "
                                 "(28 before the TWMAX window, 2026-08-06), "
                                 "got %s" % (tag, ndep))
            if idmode not in (1, 2):
                raise SystemExit("macro card%s: IDMODE must be 1 or 2, got %d"
                                 % (tag, idmode))
            if min(dcs) <= 0.0 or max(dcs) > 1.0:
                raise SystemExit("macro card%s: critical damages must lie in "
                                 "(0,1], got %s" % (tag, dcs))
        for k, name in ((48 + 8 * nt, "F12*"), (49 + 8 * nt, "F23*")):
            if abs(p[k]) >= 1.0:
                raise SystemExit("macro card%s: Tsai-Wu %s = %g gives an OPEN "
                                 "failure surface (|F*| < 1 required)"
                                 % (tag, name, p[k]))
    elif ndep is not None and ndep < 29:
        raise SystemExit("macro card%s: *Depvar >= 29 required (V3_0 writes "
                         "TWMAX, the cycle-severity window, to SDV 29 on "
                         "every macro card -- 22 was the pre-window layout), "
                         "got %d" % (tag, ndep))

    gf = gf_audit(p, nt, le)
    stale = [g for g in gf if g["sign"] == "total"]
    if stale and not allow_total_gf:
        msg = ["macro card%s: slots %s carry a POSITIVE fracture energy."
               % (tag, ", ".join(str(g["slot"]) for g in stale))]
        msg.append("  A positive entry is the TOTAL-area convention, which "
                   "contains g0 times")
        msg.append("  the length it was extracted at.  A macro card is by "
                   "definition consumed")
        msg.append("  at a different length, so only the DISSIPATED part may "
                   "cross the scale")
        msg.append("  boundary and it is carried NEGATED.  See Ch.4 4.9-16.")
        for g in stale:
            worst = max((s["A"] for s in g["states"]), default=None)
            msg.append("    slot %d (%s): Gf = %+.6g N/mm -> A = %s"
                       % (g["slot"], g["mode"], g["gf"],
                          "%.4g at best" % worst if worst is not None
                          else "unknown without le"))
        msg.append("  Regenerate with postprocess/homogenize.py (it splits "
                   "and negates), or")
        msg.append("  pass allow_total_gf=True if this card really was "
                   "measured at le(macro).")
        raise SystemExit("\n".join(msg))
    # n and p are the card WITHOUT the tangent block (stripped above), so
    # nprops is reported back at its true on-deck length.
    return dict(nprops=n + (0 if itan is None else 2), nt=nt, ndepvar=ndep,
                gf=gf, props=p, itan=itan,
                criteria=(n == 56 + 8 * nt and
                          int(round(p[47 + 8 * nt])) > 0))


def print_gf_audit(rows):
    """Say what the crack band will do, per mode, before anything is run.

    A clamped mode is not an error -- it is a legitimate outcome that means
    the macro mesh cannot resolve that mode's band -- but it must be visible,
    because a peak stress quoted out of a snap-back-clamped run is a mesh
    result rather than a material one.
    """
    live = [r for r in rows if r["states"]]
    if not live:
        print("  crack band: no characteristic length given, sign only")
        return
    print("  crack band, A per mode (KABAND):")
    for r in live:
        if r["sign"] == "off":
            print("    %-3s slot %d  OFF -> fixed exponent A = %.4g"
                  % (r["mode"], r["slot"], r["afix"]))
            continue
        As = [s["A"] for s in r["states"]]
        clamps = sorted(set(s["clamped"] for s in r["states"] if s["clamped"]))
        note = ""
        if "snapback" in clamps:
            snap = [s for s in r["states"] if s["clamped"] == "snapback"]
            note = ("  ** SNAP-BACK CLAMP at %d of %d (T, le) states -- the "
                    "element is too long for this band"
                    % (len(snap), len(r["states"])))
        elif "floor" in clamps:
            note = "  ** floor clamp A = 0.01"
        print("    %-3s slot %d  |Gf| = %.6g N/mm  ->  A = %.4g - %.4g%s"
              % (r["mode"], r["slot"], abs(r["gf"]), min(As), max(As), note))


def orientation_audit(deck_text):
    """Every section whose material carries an ORTHO/ANISO property must name
    an *Orientation, and that orientation must exist in the same deck.

    This is the check that was missing on 2026-08-10, when LTH_CJHEAT died in
    the pre-processor with

        ***ERROR: Anisotropic material properties without a local orientation
                  system

    after passing every static check this file had.  Nothing here reads a
    solver; it reads the deck the way Abaqus's input parser does.

    Returns a list of complaints -- empty means the deck is clean.
    """
    aniso_kw = ("*conductivity", "*expansion", "*elastic")
    mats, cur = {}, None
    for ln in deck_text.splitlines():
        s = ln.strip().lower()
        if s.startswith("*material"):
            cur = None
            for tok in ln.split(","):
                if tok.strip().lower().startswith("name"):
                    cur = tok.split("=", 1)[1].strip()
            if cur:
                mats[cur] = False
        elif cur and s.startswith(aniso_kw):
            if "ortho" in s or "aniso" in s:
                mats[cur] = True
    named = set()
    for ln in deck_text.splitlines():
        if ln.strip().lower().startswith("*orientation"):
            for tok in ln.split(","):
                if tok.strip().lower().startswith("name"):
                    named.add(tok.split("=", 1)[1].strip())
    bad = []
    for ln in deck_text.splitlines():
        s = ln.strip().lower()
        if not s.startswith(("*solid section", "*shell section")):
            continue
        mat = ori = None
        for tok in ln.split(","):
            k, _, v = tok.partition("=")
            k = k.strip().lower()
            if k == "material":
                mat = v.strip()
            elif k == "orientation":
                ori = v.strip()
        if mat and mats.get(mat):
            if not ori:
                bad.append("section using %s has an ORTHO/ANISO property but "
                           "no Orientation=" % mat)
            elif ori not in named:
                bad.append("section using %s names Orientation=%s, which the "
                           "deck never defines" % (mat, ori))
    return bad


def keyword_glue_audit(deck_text):
    """No line may hide a keyword after data.

    A patch that rewrites the *User Material data lines can drop the newline
    before the block that follows, producing

        ..., 0., 41.*Expansion, type=ORTHO, zero=1050.

    which Abaqus reads as data and mis-parses.  It happened to the shipped
    LTH_CJ1/CJ5 on 2026-08-07 and survived every check because each check
    looked at keywords or at numbers, never at both on one line.
    """
    bad = []
    for n, ln in enumerate(deck_text.splitlines(), 1):
        s = ln.strip()
        if s.startswith("*") or "*" not in s:
            continue
        head = s.split("*", 1)[0]
        if head.strip() and any(c.isdigit() for c in head):
            bad.append("line %d hides a keyword after data: %s"
                       % (n, s[:70]))
    return bad


def _mangle(card, slot=None, value=None, depvar=None, drop=0):
    """Return PLACEHOLDER_CARD with one thing deliberately broken."""
    out = card
    if depvar is not None:
        out = re.sub(r"(\*Depvar\n)\d+,", r"\g<1>%d," % depvar, out)
    if slot is not None:
        out = patch_card(out, slot, value)
    if drop:
        lines = out.splitlines()
        head = next(i for i, l in enumerate(lines)
                    if l.lstrip().lower().startswith("*user material"))
        vals = []
        tail = len(lines)
        for j in range(head + 1, len(lines)):
            if lines[j].lstrip().startswith("*"):
                tail = j
                break
            vals.extend(v.strip() for v in lines[j].split(",") if v.strip())
        vals = vals[:-drop]
        body = [", ".join(vals[k:k + 8]) for k in range(0, len(vals), 8)]
        lines[head] = re.sub(r"constants\s*=\s*\d+",
                             "constants=%d" % len(vals), lines[head])
        out = "\n".join(lines[:head + 1] + body + lines[tail:])
    return out


def selftest():
    """The card validator has to REJECT, not just accept.

    Each case below is a real mistake that would otherwise be found only when
    Abaqus aborts the job: a card that is the right length but the wrong
    content, a *Depvar that was not grown with the card, an interaction
    coefficient that opens the failure surface.
    """
    print("check_macro_card selftest")
    fails = []

    def expect_ok(name, card, **kw):
        try:
            info = check_macro_card(card, name, **kw)
            print("  [PASS] accepts %-38s NPROPS=%d Depvar=%s"
                  % (name, info["nprops"], info["ndepvar"]))
            return info
        except SystemExit as exc:
            fails.append(name)
            print("  [FAIL] rejected a VALID card %s: %s" % (name, exc))
            return None

    def expect_reject(name, card, **kw):
        try:
            check_macro_card(card, name, **kw)
        except SystemExit as exc:
            print("  [PASS] rejects %-38s (%s)"
                  % (name, str(exc).splitlines()[0].split(":")[-1].strip()[:46]))
            return
        fails.append(name)
        print("  [FAIL] ACCEPTED a broken card: %s" % name)

    def expect_true(name, cond, detail=""):
        if cond:
            print("  [PASS] %-46s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %-46s %s" % (name, detail))

    c = PLACEHOLDER_CARD
    expect_ok("placeholder card, criteria on", c)
    expect_ok("criteria off (47 slots, Depvar 29)",
              _mangle(c, depvar=29, drop=9))

    expect_reject("wrong card key PROPS(36)", _mangle(c, slot=36, value=30.0))
    expect_reject("missing block guard PROPS(56)",
                  _mangle(c, slot=56, value=0.0))
    expect_reject("ICRIT on but *Depvar still 22", _mangle(c, depvar=22))
    # 28 was VALID until the TWMAX window (2026-08-06).  A deck built by an
    # old generator is exactly the mistake that will happen, so the stale
    # layout is rejected by name, not merely by arithmetic.
    expect_reject("pre-window *Depvar 28 (stale layout)",
                  _mangle(c, depvar=28))
    expect_reject("criteria off but *Depvar 22 (stale layout)",
                  _mangle(c, depvar=22, drop=9))
    expect_reject("truncated card (55 slots)", _mangle(c, drop=1))
    expect_reject("NT says 2 but no table rows", _mangle(c, slot=47, value=2.0))
    expect_reject("IDMODE = 3", _mangle(c, slot=51, value=3.0))
    expect_reject("critical damage = 0", _mangle(c, slot=52, value=0.0))
    expect_reject("critical damage > 1", _mangle(c, slot=54, value=1.4))
    expect_reject("F12* = -1.0 (open surface)", _mangle(c, slot=49, value=-1.0))
    expect_reject("F23* = +1.2 (open surface)", _mangle(c, slot=50, value=1.2))

    bad = c.replace("constants=56", "constants=48")
    expect_reject("constants= disagrees with the values", bad)

    # ---- the consistent-tangent block (2026-08-11) -----------------------
    # The UMAT has carried Ge Eqs.(31)-(33) behind an ITAN switch since
    # 2026-08-10, but no generator emitted the slots, so it could not be
    # exercised at all.  The rules that matter are: omitting the flag must
    # change NOTHING, the block must not hide the criterion block behind it,
    # and a 0/1 pair must differ in exactly one number.
    expect_true("omitting --itan leaves the card untouched",
                append_tangent_block(c, None) == c)
    for want in (0, 1):
        t = append_tangent_block(c, want)
        i = check_macro_card(t, "itan%d" % want)
        expect_true("--itan %d gives NPROPS 58 and reads back ITAN=%d"
                    % (want, want),
                    i["nprops"] == 58 and i["itan"] == want,
                    "NPROPS=%d ITAN=%s" % (i["nprops"], i["itan"]))
        # THE TRAP THAT WAS ALREADY SPRUNG ONCE.  The HSMO and ICRIT readers
        # keyed on total NPROPS, so appending any block silently switched
        # them off.  Here the criterion block sits BEFORE the tangent block,
        # so if the validator located it by raw length it would now miss it.
        expect_true("--itan %d does not switch the criterion block off" % want,
                    i["criteria"] is True)
    t0, t1 = append_tangent_block(c, 0), append_tangent_block(c, 1)

    def _data(txt):
        return " ".join(ln for ln in txt.splitlines()
                        if not ln.lstrip().startswith("**")).split()
    d = [(a, b) for a, b in zip(_data(t0), _data(t1)) if a != b]
    expect_true("the 0/1 pair differs in exactly one number",
                len(d) == 1 and d[0] == ("0,", "1,"),
                "%d difference(s): %s" % (len(d), d))
    expect_true("the criterion guard 41.0 is still the second-to-last "
                "of its own block",
                check_macro_card(t1, "itan")["props"][-1] == 41.0)
    expect_reject("tangent block with a broken guard",
                  t1.replace("1, 33", "1, 34"))
    expect_reject("tangent block with ITAN = 2",
                  t1.replace("1, 33", "2, 33"))
    try:
        append_tangent_block(t1, 1)
        fails.append("double --itan")
        print("  [FAIL] appended the tangent block twice")
    except SystemExit:
        print("  [PASS] %-46s" % "refuses to append the block twice")
    # A card with the tangent block but WITHOUT the criterion block is the
    # 49+8*NT length, and it must still be legal.
    expect_ok("tangent block on a criteria-off card (49 slots)",
              append_tangent_block(_mangle(c, depvar=29, drop=9), 1))

    # ---- the Ch.4 4.9-16 convention -------------------------------------
    # These are the ones the UMAT will NOT catch.  A positive Gf runs, and
    # returns a softening branch that is too gentle by the ratio of the two
    # lengths, so the only defence is refusing to write the deck.
    E1, Xt = 105000.0, 220.0
    g0 = Xt * Xt / (2.0 * E1)                     # 0.2305 N/mm2
    LE = 0.7                                      # a ZHANG2013-sized element
    A_WANTED = 3.0
    gfin = 2.0 * g0 * LE / A_WANTED               # dissipated part at this le

    for slot, mode in ((32, "1t"), (33, "1c"), (34, "2t"), (35, "2c")):
        expect_reject("slot %d (%s) positive = total-area convention"
                      % (slot, mode),
                      _mangle(c, slot=slot, value=0.9), le=LE)
    expect_ok("the same card with allow_total_gf",
              _mangle(c, slot=32, value=0.9), le=LE, allow_total_gf=True)
    expect_ok("negated dissipated part is accepted",
              _mangle(c, slot=32, value=-gfin), le=LE)
    expect_ok("Gf = 0 (band off) is accepted", c, le=LE)

    # The audit has to reproduce KABAND, not merely judge the sign.
    info = check_macro_card(_mangle(c, slot=32, value=-gfin), "audit", le=LE)
    rec = info["gf"][0]
    # patch_card writes the slot with %.10g, so the value that comes back has
    # been through a ten-significant-digit text round trip.  1e-6 is the text,
    # not the algebra; check_gf_scale_transfer.py tests the algebra at 1e-9.
    expect_true("audit recovers the exponent that made the entry",
                abs(rec["states"][0]["A"] - A_WANTED) < 1e-6,
                "A = %.9f (wanted %.1f)" % (rec["states"][0]["A"], A_WANTED))
    expect_true("audit reads g0 = X^2/2E from the card's own slots",
                abs(rec["states"][0]["g0"] - g0) < 1e-9,
                "g0 = %.6f N/mm2" % rec["states"][0]["g0"])
    expect_true("a zero slot reports the fixed exponent, not a computed one",
                info["gf"][1]["sign"] == "off"
                and info["gf"][1]["states"][0]["A"] == info["gf"][1]["afix"],
                "A = %.4g" % info["gf"][1]["afix"])

    # Snap-back: too little dissipation for the element length.  KABAND
    # clamps to 50 and the branch stops being the one that was measured.
    tiny = 0.01 * g0 * LE
    info = check_macro_card(_mangle(c, slot=32, value=-tiny), "snap", le=LE)
    expect_true("snap-back clamp is reported, not silently applied",
                info["gf"][0]["states"][0]["clamped"] == "snapback",
                "|Gf| = %.4g N/mm at le = %.2f mm" % (tiny, LE))

    # The pairing must be right or every g0 is wrong.  Halving Yt may only
    # move the transverse modes.
    half = patch_card(_mangle(c, slot=32, value=-gfin), 13, 0.5 * 220.0)
    a_long = check_macro_card(half, "pair", le=LE)["gf"][0]["states"][0]["g0"]
    a_tran = check_macro_card(half, "pair", le=LE)["gf"][2]["states"][0]["g0"]
    expect_true("Yt moves the transverse g0 and leaves the longitudinal one",
                abs(a_long - g0) < 1e-9 and abs(a_tran - 0.25 * g0) < 1e-9,
                "g0(1t) = %.6f, g0(2t) = %.6f" % (a_long, a_tran))

    # KMACRO31 scales E and X by f(T) but never Gf, so a mode can be fine at
    # the reference temperature and clamped at another.  The audit must walk
    # every table row rather than trusting the first.
    info = check_macro_card(_mangle(c, slot=32, value=-gfin), "ttab",
                            le=[LE, 2.0 * LE])
    nstate = len(info["gf"][0]["states"])
    expect_true("audit walks every (temperature, le) state",
                nstate == max(info["nt"], 1) * 2,
                "%d states from NT=%d x 2 lengths" % (nstate, info["nt"]))

    # a1-0011: holding Gf fixed while E and X move with temperature is an
    # assumption, and its size is now bounded rather than merely admitted.
    # The bound is anchored on measurement, not on a test fixture:
    # refs/[10] Yang Table 1 gives E and the ultimate strength at four
    # temperatures on ONE material, so g0 = X^2/(2E) -- which is all A
    # depends on once Gf and le are fixed -- can be evaluated directly.
    YANG = ((300.0, 128.7e3, 225.8), (973.0, 152.3e3, 240.5),
            (1273.0, 172.7e3, 268.2), (1473.0, 169.1e3, 240.9))
    gfy, ley = 0.12, LE
    A_of = dict((T, _kaband(X * X / (2.0 * E) * ley, -gfy, 2.0))
                for T, E, X in YANG)
    in_range = [A_of[T] for T, _, _ in YANG if T <= 1273.0]
    dev_rt = max(abs(a / A_of[300.0] - 1.0) for a in in_range)
    expect_true("A stays within 5.2 % of its RT value out to 1273 K",
                dev_rt < 0.052, "%.1f %%" % (100.0 * dev_rt))
    expect_true("and it is not monotonic -- 973 K dips before 1273 K rises",
                A_of[973.0] < A_of[300.0] < A_of[1273.0],
                "%.4f < %.4f < %.4f"
                % (A_of[973.0], A_of[300.0], A_of[1273.0]))
    expect_true("beyond our 1000 C ceiling it does move, so the bound is"
                " scoped", abs(A_of[1473.0] / A_of[300.0] - 1.0) > 0.10,
                "%.1f %% at 1473 K" % (100.0 * (A_of[1473.0] / A_of[300.0]
                                                - 1.0)))
    # The reporter itself, on a hand-built two-temperature mode.
    rows = [dict(mode="1t", states=[dict(T=300.0, le=LE, g0=0.2, A=2.0),
                                    dict(T=1273.0, le=LE, g0=0.21, A=2.1)])]
    d = gf_temperature_drift(rows)
    expect_true("gf_temperature_drift reports max/min per mode",
                abs(d["1t"][2] - 0.05) < 1e-12, "%.4f" % d["1t"][2])
    # And the direction: real |Gf| rises with temperature (Snead refs/[06]
    # Fig. 14), the card does not, so the card over-predicts A and therefore
    # over-predicts damage.  Conservative.  Stated so it cannot be re-derived
    # backwards later.
    expect_true("the sign of that error is written down where A is computed",
                "conservative for life prediction" in gf_temperature_drift
                .__doc__)

    # Cross-module: the card that postprocess/homogenize.py will actually
    # emit after the RVE virtual tests must pass this validator.  Without
    # this the two files can drift apart and nobody notices until M3.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "postprocess"))
        import homogenize as hz
    except ImportError as exc:
        print("  [SKIP] homogenize.py not importable (%s)" % exc)
    else:
        elastic = dict(E1=105000.0, E2=105000.0, E3=52000.0, nu12=0.10,
                       nu13=0.25, nu23=0.25, G12=36000.0, G13=22000.0,
                       G23=22000.0)
        strength = dict(Xt=220.0, Xc=480.0, Yt=220.0, Yc=480.0,
                        S12=110.0, S13=90.0, S23=90.0)
        # Give it real dissipated parts as well, so the card that comes back
        # exercises the sign convention instead of four zeros.  If homogenize
        # ever stops negating them, this validator now says so.
        for m in ("1t", "1c", "2t", "2c"):
            strength["Gfin_" + m] = 0.12
        for temps in ([23.0], [23.0, 500.0, 1000.0]):
            by_T = {}
            for i, T in enumerate(temps):
                f = 1.0 - 0.1 * i
                by_T[T] = dict(
                    elastic={k: v * f for k, v in elastic.items()},
                    strength={k: v * f for k, v in strength.items()},
                    alpha=(2.5e-6, 2.5e-6, 5.0e-6))
            for crit, tag in ((hz.DEFAULT_CRIT, "on"), (None, "off")):
                emitted = hz.macro_card(by_T, hz.DEFAULT_CYC, temps, crit=crit)
                info = expect_ok("homogenize.py card, NT=%d, criteria %s"
                                 % (len(temps), tag), emitted, le=0.7)
                if info is None:
                    continue
                expect_true("  and its four Gf slots are all negated",
                            all(g["sign"] == "inelastic" for g in info["gf"]),
                            ", ".join("%s %+.3g" % (g["mode"], g["gf"])
                                      for g in info["gf"]))
                # KMACRO31 scales X and E with f(T) but leaves Gf alone, so A
                # is temperature dependent even though the card slot is not.
                # The audit has to see one state per table row.
                seen = [s["T"] for s in info["gf"][0]["states"]]
                expect_true("  and reports A at every one of the %d table rows"
                            % len(temps), seen == list(temps),
                            "A = %s" % ", ".join(
                                "%.3f" % s["A"]
                                for s in info["gf"][0]["states"]))

    # ---- the severity window's deck-side half (a1-0018) -----------------
    # V3_0 evaluates fC at the step's running-max temperature (SDV 29).
    # That is exact only if cycle counting happens in steps that BEGIN at
    # the cycle's peak temperature, which is the quench halves.  The deck
    # writer must therefore put the whole block's rate on the quenches and
    # zero on the reheats -- checked on the emitted text, not trusted.
    body, _ = mech_steps("Z", "C", 60, (20, 40, 60), 15.0, 45.0,
                         "HEATJOB", 5.0, 12.5)
    steps = body.split("*Step, Name=")[1:]
    q = [st for st in steps if st.startswith("Quench")]
    r = [st for st in steps if st.startswith("Reheat")]
    expect_true("cycling emits Quench and Reheat halves",
                len(q) == 12 and len(r) == 12,
                "%d + %d steps" % (len(q), len(r)))
    def _rate(st):
        m = re.search(r"\*Field, variable=1\nALLNODES, ([0-9.eE+-]+)", st)
        return float(m.group(1)) if m else None
    expect_true("every Quench half carries the block's cycle rate",
                all((_rate(st) or 0.0) > 0.0 for st in q),
                "rate = %.6g" % _rate(q[0]))
    expect_true("every Reheat half carries rate 0 (counts no cycles)",
                all(_rate(st) == 0.0 for st in r))
    # tolerance is the %.10g text round-trip's, not the arithmetic's
    expect_true("the quench rate absorbs the reheat's share "
                "(dN per block conserved)",
                abs(_rate(q[0]) * 15.0 * 4 - 20.0) < 1e-4,
                "%.6g cycles/s x 15 s x 4 steps = %.6g cycles"
                % (_rate(q[0]), _rate(q[0]) * 15.0 * 4))

    # ---- the *Depvar names are what the Viewer shows
    # An unnamed entry appears as "SDV9"; a named one as "SDV_D1".  The real
    # card comes from homogenize.py, which names all 29, so the placeholder
    # must too -- otherwise a placeholder run and a real run put damage under
    # DIFFERENT variable names and a saved Viewer session silently plots
    # nothing.  The names are cross-read from homogenize.py rather than
    # duplicated by hand, so a rename there cannot drift away from here.
    hp = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "postprocess", "homogenize.py")
    htxt = open(hp).read()
    m = re.search(r'names = \[(.*?)\]\n', htxt, re.S)
    hnames = re.findall(r'"([A-Z0-9]+)"', m.group(1)) if m else []
    pnames = re.findall(r'^(\d+), ([A-Z0-9]+), \2$', PLACEHOLDER_CARD,
                        re.M)
    expect_true("the placeholder names every one of the 29 macro SDVs",
                [int(i) for i, _n in pnames] == list(range(1, 30)),
                "named %d of 29" % len(pnames))
    expect_true("and uses homogenize.py's names, so the two cards agree",
                [n for _i, n in pnames] == hnames,
                "%d names read from homogenize.py" % len(hnames))
    expect_true("SDV9/SDV10 are the damage pair postprocess/damage_map.py "
                "reads", [n for _i, n in pnames][8:10] == ["D1", "DT"])

    # ---- the two defects that reached the solver on 2026-08-10
    import tempfile as _tf
    _d = _tf.mkdtemp()
    _argv = sys.argv[1:]
    sys.argv[1:] = ["--specimen", "ZHANG2013", "--prefix",
                    os.path.join(_d, "SC"), "--sev", "Z", "--trs", "C"]
    try:
        _so = sys.stdout
        sys.stdout = open(os.devnull, "w")
        try:
            main()
        finally:
            sys.stdout.close()
            sys.stdout = _so
    finally:
        sys.argv[1:] = _argv
    decks = {}
    for nm in ("SC_HEAT_SZ.inp", "SC_MECH_SZ_TRSC.inp"):
        decks[nm] = open(os.path.join(_d, nm)).read()

    for nm, txt in sorted(decks.items()):
        expect_true("%s: every ORTHO material's section names an orientation"
                    % nm.split("_", 1)[1][:-4],
                    orientation_audit(txt) == [],
                    "; ".join(orientation_audit(txt)) or "clean")
        expect_true("%s: no line hides a keyword after data"
                    % nm.split("_", 1)[1][:-4],
                    keyword_glue_audit(txt) == [],
                    "; ".join(keyword_glue_audit(txt)) or "clean")

    # and the audits must actually FIRE on the real defects, not just pass
    broke = decks["SC_HEAT_SZ.inp"].replace(", Orientation=MACRO_AXES", "")
    expect_true("the orientation audit catches a dropped Orientation=",
                len(orientation_audit(broke)) == 1
                and "no Orientation=" in orientation_audit(broke)[0],
                orientation_audit(broke)[0] if orientation_audit(broke) else
                "DID NOT FIRE")
    broke2 = decks["SC_HEAT_SZ.inp"].replace(
        ", Orientation=MACRO_AXES", ", Orientation=NOSUCH")
    expect_true("and a section pointing at an orientation that does not exist",
                any("never defines" in b for b in orientation_audit(broke2)))
    glued = decks["SC_MECH_SZ_TRSC.inp"].replace(
        "41.\n*Expansion", "41.*Expansion")
    expect_true("the glue audit catches the LTH_CJ1 missing newline",
                len(keyword_glue_audit(glued)) == 1
                and "*Expansion" in keyword_glue_audit(glued)[0],
                keyword_glue_audit(glued)[0] if keyword_glue_audit(glued)
                else "DID NOT FIRE")
    expect_true("a comment line with a * in prose is not a false positive",
                keyword_glue_audit("** 3 x 3 = 9 cases, see *Step below") == [])

    # ---- --hclo, the crack-closure control job (a1-0027 item 2)
    base_h = check_macro_card(PLACEHOLDER_CARD, "hclo-base")["props"][36]
    off = patch_card(PLACEHOLDER_CARD, 37, 0.0)
    expect_true("--hclo writes macro slot 37, the closure fraction",
                check_macro_card(off, "hclo-off")["props"][36] == 0.0
                and base_h != 0.0,
                "card ships H_clo = %g, control job forces 0" % base_h)
    expect_true("and changes nothing else on the card",
                [k for k, (a, b) in enumerate(zip(
                    check_macro_card(PLACEHOLDER_CARD, "a")["props"],
                    check_macro_card(off, "b")["props"])) if a != b] == [36])
    expect_true("the control job's H_clo=0 is what V1_0 did, so the "
                "difference is the new model alone",
                "HCLO=0 reproduces V1_0" in open(os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(
                        __file__))), "src",
                    "UMAT_CSIC_THERMSHOCK_V3_0.for")).read())

    print("\n G. the thermal card and the unit set it lives in")
    blk, aud = homogenised_thermal()
    # A ROUND TRIP, not new evidence: 32.4 % was derived from a measured
    # density in the first place (make_rve_conductivity.py, 0.196/0.60546).
    # What it checks is that the mass bookkeeping HERE matches the mass
    # bookkeeping THERE -- which now matters, because rho_bar has stopped
    # being decoration and started driving a transient.
    expect_true("rho_bar closes the loop on the porosity it was built from",
                abs(aud["rho_bar"] * 1.0e9 - 2.0) < 0.05,
                "%.4f g/cm^3 vs the 2.0 the porosity was derived from"
                % (aud["rho_bar"] * 1.0e9))
    expect_true("  and it is the pores that put it there, not luck",
                _mass_fractions(0.0)[2] * 1.0e9 - 2.0 > 0.5,
                "a pore-free cell would weigh %.4f g/cm^3"
                % (_mass_fractions(0.0)[2] * 1.0e9))
    a = thermal_audit(blk, 3.0, 0.199, 15.0)
    expect_true("the derived card has a physical diffusivity",
                a["ok"] and 1.0 < a["alpha"] < 100.0,
                "%.4f mm^2/s" % a["alpha"])
    # This is the card this file shipped until 2026-08-11, and the gate has
    # to reject it on the DIFFUSIVITY: its Biot number is perfectly ordinary,
    # because h was wrong by the same 1000 as k and Bi is their ratio.
    bad = thermal_audit(PLACEHOLDER_THERMAL, 3.0, 1.99e-4, 15.0)
    expect_true("and the old placeholder is rejected", not bad["ok"],
                "alpha = %.4g mm^2/s, Fo = %.3g" % (bad["alpha"], bad["fo"]))
    # Take OUR card and put it back in the old unit set -- k and h both /1000,
    # rho and cp untouched, which is exactly the mismatch that shipped.  Same
    # material, same test, so the comparison is clean: Bi does not move at
    # all, and that is precisely why a Biot check could never have caught it.
    legacy = re.sub(r"(\*Conductivity[^\n]*\n)([^\n]+)",
                    lambda m: m.group(1) + ", ".join(
                        "%.6g" % (float(v) / 1000.0) for v in
                        m.group(2).split(",")[:3]), blk, count=1)
    old = thermal_audit(legacy, 3.0, 0.199 / 1000.0, 15.0)
    expect_true("  and the same card in the old unit set is rejected too",
                not old["ok"] and "energy unit" in old["why"],
                "alpha %.4g -> %.4g mm^2/s" % (a["alpha"], old["alpha"]))
    expect_true("  for the reason a Biot check could never have seen",
                abs(old["bi"] - a["bi"]) < 1e-9,
                "Bi = %.4f either way; only Fo moved, %.3g -> %.3g"
                % (a["bi"], a["fo"], old["fo"]))
    expect_true("the ladder's Biot number is exact on OUR kbar_3",
                abs(severity("M", KBAR3_MEASURED, 3.0)[1] - 1.0) < 1e-12)
    # The paper's datum is a COOLING TIME, not a film coefficient, so h is
    # re-solved on our own rho, cp and kbar_3.  0.0475 is what refs/[03]'s
    # own properties give; 0.0548 is what you get by keeping their h and
    # swapping in our k, which is the one pairing that describes no material.
    zh, zbi = severity("Z", KBAR3_MEASURED, 3.0)
    expect_true("a published protocol is re-solved on OUR card, not imported",
                abs(zbi - 0.0445) < 5e-4 and abs(zh * 1e3 - 161.7) < 0.5,
                "h = %.1f W/(m^2.K), Bi = %.4f (theirs: 199.0 and 0.0475)"
                % (zh * 1e3, zbi))
    expect_true("  and mixing their h with our k would have given neither",
                abs(0.199 * 1.5 / KBAR3_MEASURED - 0.0548) < 5e-4,
                "the mixed pairing reads Bi = 0.0548")
    expect_true("a thicker specimen moves Bi, so h cannot be shared blindly",
                severity("Z", KBAR3_MEASURED, 4.0)[1]
                > severity("Z", KBAR3_MEASURED, 3.0)[1])
    # The gradient peaks after about one diffusion time; a first increment
    # longer than that samples the answer after the event it is measuring.
    tau = (1.5 ** 2) / a["alpha"]
    expect_true("the first increment resolves the gradient peak",
                quench_dt0(a["alpha"], 3.0, 15.0) < 0.25 * tau,
                "dt0 = %.4g s against tau = %.4g s (old rule gave %.4g s)"
                % (quench_dt0(a["alpha"], 3.0, 15.0), tau, 15.0 / 50.0))
    expect_true("  and the old rule did not, even at the published 15 s",
                15.0 / 50.0 >= 0.5 * tau)
    # The 3.0x threshold here belonged to the refs/[20] shape (ratio 0.5845),
    # which a1-0031 rejected.  Our own constituents give 0.82, so k falls less
    # and the drop is 2.79x, carried mostly by cp.  The DIRECTION is the claim;
    # the factor is pinned loosely so a future shape change is caught.
    expect_true("k(T) falls and cp(T) rises, so alpha falls with temperature",
                aud["rows"][0]["alpha3"] > aud["rows"][-1]["alpha3"] * 2.5,
                "%.3f -> %.3f mm^2/s over 23-1000 C (%.2fx)"
                % (aud["rows"][0]["alpha3"], aud["rows"][-1]["alpha3"],
                   aud["rows"][0]["alpha3"] / aud["rows"][-1]["alpha3"]))
    expect_true("  and the rejected borrowing would have fallen further",
                homogenised_thermal(kt_model="ref20_resistance")[1]["rows"][0]
                ["alpha3"] / homogenised_thermal(
                    kt_model="ref20_resistance")[1]["rows"][-1]["alpha3"]
                > aud["rows"][0]["alpha3"] / aud["rows"][-1]["alpha3"])
    expect_true("--no-kt is a declared assumption, not a silent one",
                "DISABLED: --no-kt" in homogenised_thermal(k_of_t=False)[0])
    # a1-0031 rejected the refs/[20] borrowing; the card now derives the shape
    # from our own constituents, so the deck must claim it as ours -- and must
    # not silently keep the old label.
    expect_true("the k(T) shape is labelled DERIVED, not BORROWED",
                "DERIVED from refs/[17]" in blk and "not borrowed" in blk
                and "BORROWED" not in blk)
    expect_true("the derived ratio is our 0.82, not the rejected 0.5845",
                abs(_ct_ratio() - 0.82) < 0.03
                and abs(_ct_ratio() - REF20_K_RATIO_296_1473) > 0.15)
    expect_true("the rejected shapes survive only as sensitivity switches",
                homogenised_thermal(kt_model="ref20_resistance")[1]["kt_model"]
                == "ref20_resistance"
                and homogenised_thermal()[1]["kt_model"] == "derived")

    if fails:
        print("\nSELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    print("\nSELFTEST PASSED")
    return 0


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


ITAN_KEY = 33.0          # PROPS(NPROPS) guard on the consistent-tangent block


def append_tangent_block(card_text, itan):
    """Append the 2-slot consistent-tangent block to the MACRO card.

    The block sits at the very end, with or without the failure-criterion
    block, so the legal lengths become 49+8*NT and 58+8*NT (UMAT header
    'MACRO consistent-tangent block').  `itan` is 0 or 1; 0 means the block
    is present but the routine still returns the secant DDSDDE, which is
    what makes an ITAN=0 vs ITAN=1 pair differ in exactly one number.

    Passing itan=None returns the card untouched -- that is the default and
    it keeps every shipped deck byte-identical to what it was before this
    function existed.
    """
    if itan is None:
        return card_text
    if itan not in (0, 1):
        raise SystemExit("--itan takes 0 or 1, got %r" % itan)
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
    if abs(float(vals[-1]) - ITAN_KEY) < 1e-9:
        raise SystemExit("macro card already carries a tangent block; "
                         "--itan must not be applied twice")
    vals = vals + ["%.10g" % itan, "%.10g" % ITAN_KEY]
    header = re.sub(r"constants\s*=\s*\d+", "constants=%d" % len(vals),
                    lines[head], flags=re.I)
    body = [", ".join(vals[k:k + 8]) for k in range(0, len(vals), 8)]
    note = ("** consistent-tangent block appended: ITAN=%d, guard %.1f "
            "(NPROPS %d -> %d)" % (itan, ITAN_KEY, len(vals) - 2, len(vals)))
    return "\n".join(lines[:head] + [note, header] + body + lines[tail:])


def read_block(path, default):
    if path and os.path.exists(path):
        return open(path).read().rstrip()
    return default


PLACEHOLDER_CARD = """** PLACEHOLDER macro card -- replace with the RVE output
** (postprocess/homogenize.py -> <prefix>_macro_card.inp).
** Running with these numbers produces a WORKING deck but MEANINGLESS results.
*Material, Name=CSIC_MACRO_CDM
*Depvar
29,
1, D1T, D1T
2, D1C, D1C
3, DTT, DTT
4, DTC, DTC
5, R1T, R1T
6, R1C, R1C
7, RTT, RTT
8, RTC, RTC
9, D1, D1
10, DT, DT
11, MODE, MODE
12, TINIT, TINIT
13, DJUMP, DJUMP
14, CUTREQ, CUTREQ
15, TJUMP, TJUMP
16, RJUMP, RJUMP
17, DCYC, DCYC
18, NCUM, NCUM
19, RDRV, RDRV
20, D1MONO, D1MONO
21, DTMONO, DTMONO
22, CLOFLG, CLOFLG
23, FITW, FITW
24, FIDC, FIDC
25, NFLAG, NFLAG
26, NFHA, NFHA
27, NFTW, NFTW
28, NFDC, NFDC
29, TWMAX, TWMAX
*User Material, constants=56
3., 105000., 105000., 52000., 0.10, 0.25, 0.25, 36000.
22000., 22000., 220., 480., 220., 480., 110., 90.
90., 2., 2., 2., 2., 0.99, 0.99, 0.02
0.10, 1000000., 0.25, 1., 1., 0.5, 1., 0.
0., 0., 0., 31., 0.8, 1., 8.2882e-02, 3.
1., 0.30, 0.95, 0.30, 0., 1., 0., 1.
-0.5, -0.5, 2., 0.5224, 0.5224, 0.5405, 0., 41."""

PLACEHOLDER_EXPANSION = """*Expansion, type=ORTHO, zero=1050.
2.5e-06, 2.5e-06, 5.0e-06"""

#: Abaqus REFUSES to pre-process anisotropic material properties -- and
#: *Conductivity/*Expansion "type=ORTHO" are anisotropic -- unless the section
#: that uses them names a local orientation.  It is a fatal input error, not a
#: warning:
#:
#:   ***ERROR: Anisotropic material properties without a local orientation system
#:
#: The macro card's axes ARE the global axes (1 = warp = x, 2 = fill = y,
#: 3 = through-thickness = z, the quench direction), so this orientation is the
#: identity.  Writing it out is not a formality: it is the only place in the
#: deck that STATES that mapping, and every alpha_1/alpha_3 and kbar_1/kbar_3
#: in the card depends on it.
MACRO_ORIENTATION = """*Orientation, Name=MACRO_AXES
1., 0., 0., 0., 1., 0.
3, 0."""

PLACEHOLDER_THERMAL = """** PLACEHOLDER homogenised thermal properties.
** kbar MUST come from the RVE conductivity job (RVE_COND) -- the quench
** result is more sensitive to this than to almost anything else.
*Conductivity, type=ORTHO
0.015, 0.015, 0.004
*Density
2.1e-09,
*Specific Heat
1.0e+09,"""

# ==========================================================================
# THE REAL homogenised thermal card
# ==========================================================================
#: kbar measured on LTH2_COND_P32, W/(m.K) == mW/(mm.K), at 23 C.
KBAR_MEASURED = (8.8627, 8.8631, 5.4490)
#: matrix porosity the card is built on -- the stiffness route (Ch.4 4.9-13).
CARD_POROSITY = 0.324
#: constituent densities, g/cm^3 -> tonne/mm^3.  conductivity_bounds.py names
#: the same two numbers for its rule-of-mixtures inversion.
RHO_FIBRE, RHO_SIC = 1.76e-9, 3.21e-9
#: refs/[20] Table 1, YANG2024, fulltext: a 2D CMC laminate's OWN kbar at
#: 296 K and 1473 K, ratio 2.04/3.49 = 0.5845.  This USED to set the shape of
#: k(T) on the card.  a1-0031 adjudicated a2-0027 and REJECTED the borrowing --
#: not because the material differs, but because the borrowed shape is
#: self-contradictory INSIDE our own card: 0.5845 is what the derivation gives
#: for a DENSE CVI matrix (70 W/(m.K)), whereas our deck's matrix is refs/[17]
#: CVI SiC at 25 W/(m.K).  With 91.5 % of that resistance temperature-
#: independent, our own constituents give 0.82, not 0.5845.
#:
#: The borrowing also erred in the direction that flatters us: at 900 C it
#: raises Bi by 23.9 % and the peak gradient from 21.9 K to 27.0 K, inflating
#: contribution C2 in our favour.  That is worse than a conservative error.
#:
#: The shape now comes from data/properties/conductivity_temperature.py, which
#: derives it from Snead's resistivity split plus refs/[17]'s matrix, and is
#: corroborated by refs/[13] Katoh 2006 using the same linear-in-resistance
#: form for a 2D CVI woven composite.  refs/[20] and constant k survive only
#: as sensitivity switches (--kt-model).
REF20_K_RATIO_296_1473 = 2.04 / 3.49


def _ct_ratio():
    """The derived k(T) ratio, from a1's module (single source of truth)."""
    _properties_on_path()
    import conductivity_temperature as ct
    return ct.derived_ratio()
#: The direction it moves is the point: conductivity FALLS with temperature
#: while the fibre's rises, and quench_calibration.py shows the choice moves
#: the predicted through-thickness gradient by a factor of 4.6.  Constant k
#: is not the safe default; it is just an undeclared one.


def _properties_on_path():
    """data/properties is where every derived constant lives."""
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "properties")
    if d not in sys.path:
        sys.path.insert(0, d)


def _mass_fractions(porosity=CARD_POROSITY, vy=None, vf=None):
    """(fibre, matrix) mass fractions and the phase densities behind them."""
    _properties_on_path()
    import conductivity_bounds as cb
    vy = cb.VY_RVE if vy is None else vy
    vf = cb.VF_YARN if vf is None else vf
    rho_m = RHO_SIC * (1.0 - porosity)          # pores carry no mass
    rho_y = vf * RHO_FIBRE + (1.0 - vf) * rho_m
    rho_bar = vy * rho_y + (1.0 - vy) * rho_m
    m_f = vy * vf * RHO_FIBRE
    m_m = vy * (1.0 - vf) * rho_m + (1.0 - vy) * rho_m
    tot = m_f + m_m
    return m_f / tot, m_m / tot, rho_bar, rho_m, rho_y


def homogenised_thermal(temps=(23.0, 500.0, 1000.0), kbar=KBAR_MEASURED,
                        porosity=CARD_POROSITY, k_of_t=True,
                        kt_model="derived"):
    """(the *Conductivity/*Density/*Specific Heat block, audit dict).

    Three quantities, three different provenances, and the deck header says
    which is which because they are not equally strong:

      kbar(23 C)  OURS.  The RVE_COND job, homogenised by extract_kbar.
      rho_bar     OURS.  Volume average of the constituent densities at the
                  card's own porosity.
      cp_bar(T)   OURS.  Mass-weighted constituent Cp, both fulltext.
      k(T) shape  BORROWED from refs/[20], and only as a ratio.

    rho_bar comes out at 2.008 g/cm^3, next to the 2.0 of refs/[28] and the
    2.05 of refs/[03].  That is NOT independent confirmation of the porosity
    and must not be written up as one: 32.4 % was itself derived from a
    measured density (make_rve_conductivity.py -- 0.196 composite / 0.60546
    matrix volume).  The agreement is a ROUND TRIP -- it proves the mass
    bookkeeping here matches the mass bookkeeping there, which is worth
    having, because rho_bar now feeds a transient and a silent factor of
    (1 - p) in it would change every cooling curve.  The porosity dispute
    (32.4 % from stiffness and density, 23.8-25.4 % from conductivity) is
    NOT settled by this number and stays open.

    cp_bar rises 2.43x over 296-1473 K where refs/[20]'s laminate rises 1.55x.
    That gap is not an error to split: their laminate has no carbon fibre, and
    carbon is the phase whose Cp climbs to ~2250 J/(kg.K).  Our composite
    genuinely stores more heat per kilogram at temperature than theirs, so the
    constituent route is the right one for Cp and the borrowed number is
    confined to k.
    """
    _properties_on_path()
    import eval_correlations as ec
    m_f, m_m, rho_bar, rho_m, rho_y = _mass_fractions(porosity)

    def cp_bar(T_C):
        K = T_C + 273.15
        return m_f * ec.fibre_cp(K) + m_m * ec.sic_cp(K)      # J/(kg.K)

    import conductivity_temperature as ct

    def k_scale(T_C):
        """k(T)/k(23 C) from our own constituents (a1-0031).

        Linear in RESISTANCE, not in k -- the two agree at the endpoints but
        differ by 0.0553 at 500 C, and the resistance form is the one both
        Snead Eq.12 and refs/[13] Katoh actually use.  --no-kt still pins the
        card to a constant, and --kt-model exposes the rejected shapes for the
        Ch.5 sensitivity table.
        """
        if not k_of_t:
            return 1.0
        return ct.k_scale(T_C, model=kt_model)

    rows_k, rows_cp, audit_rows = [], [], []
    for T in temps:
        s = k_scale(T)
        k = tuple(v * s for v in kbar)
        rows_k.append("%.6g, %.6g, %.6g, %.6g" % (k + (T,)))
        c = cp_bar(T)
        rows_cp.append("%.6g, %.6g" % (c * 1.0e6, T))   # J/(kg.K)->mJ/(t.K)
        audit_rows.append(dict(T_C=T, k1=k[0], k2=k[1], k3=k[2], cp=c,
                               alpha3=k[2] / (rho_bar * c * 1.0e6)))

    block = "\n".join([
        "** HOMOGENISED THERMAL CARD -- derived, not typed.",
        "**   kbar(23 C) = %.4f / %.4f / %.4f W/(m.K)   OURS, RVE_COND at "
        "%.1f %% matrix porosity" % (kbar + (100.0 * porosity,)),
        "**   rho_bar    = %.4f g/cm^3   OURS, volume average"
        % (rho_bar * 1.0e12 / 1000.0),
        "**                refs/[28] states 'about 2.0', refs/[03] 2.05.  A "
        "ROUND TRIP, not independent evidence:",
        "**                the 32.4 % was itself derived from a measured "
        "density.  The porosity dispute stays open.",
        "**   cp_bar(T)  = %.1f -> %.1f J/(kg.K)   OURS, mass-weighted "
        "constituent Cp" % (cp_bar(min(temps)), cp_bar(max(temps))),
        "**   k(T) shape = DERIVED from refs/[17] CVI matrix (25 W/(m.K)) + "
        "Snead resistivity split;",
        "**                linear in RESISTANCE, ratio %.4f over 296-1473 K.  "
        "OURS, not borrowed" % ct.derived_ratio(),
        "**                model=%s%s" % (kt_model,
                                          "" if k_of_t else
                                          "  [DISABLED: --no-kt]"),
        "*Conductivity, type=ORTHO, dependencies=0"] + rows_k + [
        "*Density", "%.6g," % rho_bar,
        "*Specific Heat"] + rows_cp)
    return block, dict(rho_bar=rho_bar, rho_matrix=rho_m, rho_yarn=rho_y,
                       mass_fibre=m_f, mass_matrix=m_m, rows=audit_rows,
                       porosity=porosity, k_of_t=k_of_t,
                       kt_model=kt_model)


def thermal_audit(block, lz, h, t_quench):
    """Bi and Fo from the numbers the deck ACTUALLY carries.

    Bi alone cannot see a unit error that scales h and k together -- which is
    exactly the error this file shipped until 2026-08-11 -- so the Fourier
    number is checked too.  Fo is what says whether the quench the deck asks
    for is a quench at all: below ~0.5 the plate has barely begun to cool by
    the end of the step, and the job converges perfectly while doing it.
    """
    ks = re.search(r"\*Conductivity[^\n]*\n([^\n]+)", block)
    rho = re.search(r"\*Density\s*\n\s*([0-9.eE+-]+)", block)
    cps = re.search(r"\*Specific Heat\s*\n\s*([0-9.eE+-]+)", block)
    if not (ks and rho and cps):
        return dict(ok=False, why="the block is missing k, rho or cp")
    k3 = [float(v) for v in ks.group(1).split(",")][2]
    rho_v, cp_v = float(rho.group(1)), float(cps.group(1))
    alpha = k3 / (rho_v * cp_v)                 # mm^2/s
    half = 0.5 * lz
    bi = h * half / k3
    fo = alpha * t_quench / (half * half)
    notes = []
    if not 1.0 < alpha < 100.0:
        notes.append("thermal diffusivity %.4g mm^2/s is not physical for a "
                     "ceramic (expect 1-100); this is the signature of a "
                     "mismatched energy unit -- k must be mW/(mm.K), which is "
                     "numerically W/(m.K)" % alpha)
    if fo < 0.5:
        notes.append("Fo = %.3g at the end of the quench step: the plate has "
                     "barely started to cool, so t_quench or the card is "
                     "wrong" % fo)
    return dict(ok=not notes, why="; ".join(notes), alpha=alpha, bi=bi, fo=fo,
                k3=k3, rho=rho_v, cp=cp_v)


def main():
    ap = argparse.ArgumentParser(description="Macro cyclic thermal-shock decks")
    ap.add_argument("--prefix", default="TS")
    ap.add_argument("--card", help="macro *Material block from homogenize.py")
    ap.add_argument("--expansion", help="*Expansion block from homogenize.py")
    ap.add_argument("--thermal", help="homogenised *Conductivity/*Density/*Specific Heat")
    ap.add_argument("--sev", nargs="+", default=["M"], choices=sorted(SEVERITIES))
    ap.add_argument("--trs", nargs="+", default=list(TRS_CASES), choices=TRS_CASES)
    ap.add_argument("--card-slot", nargs="+", default=[], metavar="N=V",
                    help="override 1-based macro card slots, e.g. 42=0.10 to "
                         "lower the endurance threshold for a preflight run.  "
                         "Goes through patch_card, which rewrites whole data "
                         "lines -- editing the deck by hand instead is what "
                         "glued *Expansion onto the card on 2026-08-07 and "
                         "cost a run.")
    ap.add_argument("--hclo", type=float, default=None,
                    help="force the crack-closure recovery fraction, macro "
                         "card slot 37, instead of using the card's own "
                         "value.  --hclo 0 writes the CONTROL job for the "
                         "half-cycle-asymmetry claim (C3): identical in every "
                         "other respect, so the difference between the two is "
                         "the closure model alone.  The value goes in the job "
                         "name so it cannot overwrite the job it controls.")
    ap.add_argument("--itan", type=int, default=None, choices=(0, 1),
                    help="append the 2-slot consistent-tangent block to the "
                         "macro card (UMAT Ge Eqs.31-33).  Omitting the flag "
                         "leaves the card and the whole deck byte-identical "
                         "to before -- the block is not written at all.  "
                         "--itan 0 writes the block with the switch OFF, "
                         "--itan 1 with it ON, so a 0/1 pair differs in "
                         "exactly one number and isolates the tangent.")
    ap.add_argument("--checkpoints", type=int, nargs="+",
                    default=None,
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
    ap.add_argument("--specimen", choices=sorted(SPECIMENS),
                    help="use a PUBLISHED specimen: sets the dimensions, "
                         "mesh, calibrated film coefficient and checkpoint "
                         "cycles all at once (see quench_calibration.py)")
    ap.add_argument("--validation-zhang2013", action="store_true",
                    help="deprecated alias for --specimen ZHANG2013")
    ap.add_argument("--allow-total-gf", action="store_true",
                    help="accept POSITIVE fracture energies in slots 32-35.  "
                         "Only correct if the card's Gf was measured at the "
                         "macro element's own length -- homogenize.py never "
                         "produces such a card.  See Ch.4 4.9-16.")
    ap.add_argument("--no-kt", action="store_true",
                    help="build the conductivity card at 23 C only.  Constant "
                         "k is a declared assumption, not a neutral default: "
                         "quench_calibration.py puts a factor of 4.6 on the "
                         "predicted gradient between the two ends, and "
                         "a1-0031 measures it as the SMALLER of the two "
                         "available errors (-14.4 %% on the 900 C gradient, "
                         "against +23.9 %% for the rejected refs/[20] shape).")
    ap.add_argument("--kt-model", default="derived",
                    choices=("derived", "derived_dense_matrix",
                             "ref20_linear_k", "ref20_resistance", "constant"),
                    help="which k(T) SHAPE the card uses.  Default 'derived' "
                         "is our own constituents (a1-0031).  The rest exist "
                         "so the Ch.5 5.4.3-a sensitivity table is generated "
                         "rather than typed: 'ref20_*' are the rejected "
                         "borrowing in its two readings, 'derived_dense_"
                         "matrix' is the same derivation on refs/[13]'s "
                         "denser CVI matrix (which is what reproduces "
                         "refs/[20]'s 0.5845, showing the borrowing assumes a "
                         "matrix our deck does not use).")
    ap.add_argument("--placeholder-thermal", action="store_true",
                    help="write the old meaningless thermal card instead of "
                         "the derived one, and skip the Bi/Fo gate with it")
    ap.add_argument("--list-checks", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="check that check_macro_card() accepts good cards "
                         "and rejects every broken one")
    args = ap.parse_args()

    if args.checkpoints is None:
        args.checkpoints = [5, 10, 20, 40, 60]

    if args.list_checks:
        print(CHECKS)
        return 0
    if args.selftest:
        return selftest()

    if args.validation_zhang2013 and not args.specimen:
        print("  note: --validation-zhang2013 is now --specimen ZHANG2013")
        args.specimen = "ZHANG2013"
    if args.specimen:
        sp = SPECIMENS[args.specimen]
        args.dims = list(sp["dims"])
        args.mesh = list(sp["mesh"])
        args.sev = [sp["sev"]]
        # An explicit --checkpoints wins over the specimen's defaults: the
        # cycle-jump preflight runs a published specimen but only to the
        # FIRST checkpoint, and silently forcing 60 cycles onto it would
        # turn a minutes job into an hour one.
        if args.checkpoints is None:
            args.checkpoints = list(sp["checkpoints"])
        print("specimen %s: %.4g x %.4g x %.4g mm, severity %s (Bi = %.4g on "
              "our own kbar_3)"
              % (args.specimen, args.dims[0], args.dims[1], args.dims[2],
                 sp["sev"],
                 severity(sp["sev"], KBAR3_MEASURED, args.dims[2])[1]))
        # The published protocol's own cooling time, not a generic 30 s.  A
        # quench step longer than the test's is not conservative: it lets the
        # plate equilibrate and then reports the equilibrated state as if the
        # test had reached it.
        if args.t_quench == ap.get_default("t_quench") and "t_quench" in sp:
            args.t_quench = sp["t_quench"]
            print("  t_quench = %g s, the protocol's own cooling time"
                  % args.t_quench)
        for line in sp["note"].split(".  "):
            if line.strip():
                print("  %s" % line.strip().rstrip(".") + ".")

    Lx, Ly, Lz = args.dims
    nx, ny, nz = args.mesh
    nodes, els, sets, slo, shi, zs = plate_mesh(Lx, Ly, Lz, nx, ny, nz)
    dz_surf = zs[1] - zs[0]
    print("mesh: %d nodes, %d elements; thinnest through-thickness layer "
          "= %.4g mm (of %.4g mm)" % (len(nodes), len(els), dz_surf, Lz))

    card = read_block(args.card, PLACEHOLDER_CARD)
    expan = read_block(args.expansion, PLACEHOLDER_EXPANSION)
    if args.thermal:
        therm = read_block(args.thermal, PLACEHOLDER_THERMAL)
        taud = None
    elif args.placeholder_thermal:
        therm, taud = PLACEHOLDER_THERMAL, None
        print("  !! using PLACEHOLDER thermal properties -- results meaningless")
    else:
        therm, taud = homogenised_thermal(k_of_t=not args.no_kt,
                                          kt_model=args.kt_model)
        print("  thermal card DERIVED: rho_bar = %.4f g/cm^3, "
              "cp_bar %.0f -> %.0f J/(kg.K), k(T) %s"
              % (taud["rho_bar"] * 1.0e9, taud["rows"][0]["cp"],
                 taud["rows"][-1]["cp"], "ON" if taud["k_of_t"] else "OFF"))
    if not args.card:
        print("  !! using the PLACEHOLDER macro card -- results are meaningless")

    # CELENT for a hex is the cube root of the element volume.  The mesh is
    # graded toward the quenched faces, so there is a range, and the crack
    # band has to be checked at BOTH ends: the thin surface elements are the
    # ones that resolve the gradient and the ones most likely to snap back.
    dzs = [zs[i + 1] - zs[i] for i in range(len(zs) - 1)]
    dx, dy = Lx / float(nx), Ly / float(ny)
    le_range = [(dx * dy * min(dzs)) ** (1.0 / 3.0),
                (dx * dy * max(dzs)) ** (1.0 / 3.0)]
    print("  element characteristic length CELENT = %.4g - %.4g mm"
          % (le_range[0], le_range[1]))

    for spec in args.card_slot:
        try:
            k, v = spec.split("=", 1)
            k, v = int(k), float(v)
        except ValueError:
            raise SystemExit("--card-slot wants N=VALUE, got %r" % spec)
        card = patch_card(card, k, v)
        card = card.replace(
            "*Material, Name=CSIC_MACRO_CDM",
            "** --card-slot %d=%g applied by make_macro_thermalshock.py\n"
            "*Material, Name=CSIC_MACRO_CDM" % (k, v), 1)
        print("  card slot %d forced to %g" % (k, v))

    if args.itan is not None:
        card = append_tangent_block(card, args.itan)
        print("  consistent-tangent block appended: ITAN=%d" % args.itan)

    info = check_macro_card(card, os.path.basename(args.card or "placeholder"),
                            le=le_range, allow_total_gf=args.allow_total_gf)
    print("  macro card OK: NPROPS=%d (NT=%d), *Depvar=%s, "
          "failure criteria %s"
          % (info["nprops"], info["nt"], info["ndepvar"],
             "ON" if info["criteria"] else "OFF"))
    print_gf_audit(info["gf"])
    if not info["criteria"]:
        print("  !! failure-criterion block is OFF.  Turning it on LATER means "
              "re-running\n     every macro job -- it only adds STATEV.  "
              "See postprocess/homogenize.py DEFAULT_CRIT.")

    sets2 = dict(sets)
    sets2["SURF_PROBE"] = [nodes[0][0], nodes[-1][0]]

    # ---------------- thermal jobs (shared) ------------------------------
    for sev in args.sev:
        h, bi = severity(sev, KBAR3_MEASURED, Lz)
        aud = thermal_audit(therm, Lz, h, args.t_quench)
        dt0 = (quench_dt0(aud["alpha"], Lz, args.t_quench)
               if aud.get("alpha") else args.t_quench / 50.0)
        print("  severity %s: h = %.4f mW/(mm^2.K) = %.1f W/(m^2.K), "
              "Bi = %.4f, Fo = %.3g, first increment %.4g s"
              % (sev, h, h * 1.0e3, bi, aud.get("fo", float("nan")), dt0))
        if not aud["ok"]:
            print("  !! THERMAL CARD REJECTED: %s" % aud["why"])
            if not args.placeholder_thermal:
                raise SystemExit(
                    "refusing to write a heat deck on a card that cannot "
                    "produce the quench it claims.  Pass --placeholder-thermal "
                    "only if you want a deck that runs and means nothing.")
        parts = ["*Heading",
                 " Macro thermal shock, SHARED heat transfer, severity %s (%s)"
                 % (sev, SEVERITIES[sev]["note"]),
                 "** Bi = %.4f on our own kbar_3 = %.4f W/(m.K); Fo(t_quench) "
                 "= %.3g" % (bi, KBAR3_MEASURED, aud.get("fo", 0.0)),
                 emit_mesh(nodes, els, sets2, "DC3D8"),
                 emit_surface("SURF_LO", slo),
                 emit_surface("SURF_HI", shi),
                 "*Material, Name=CSIC_MACRO_THERMAL",
                 therm.replace("** PLACEHOLDER homogenised thermal properties.",
                               "").strip(),
                 MACRO_ORIENTATION,
                 "*Solid Section, ElSet=ALL, "
                 "Material=CSIC_MACRO_THERMAL, Orientation=MACRO_AXES",
                 "1.0,",
                 "*Initial Conditions, type=TEMPERATURE\nALLNODES, %.6g"
                 % SEVERITIES[sev]["T_hi"],
                 heat_steps(sev, args.heat_cycles, args.t_quench, args.t_dwell,
                            h=h, bi=bi, dt0=dt0)]
        write("%s_HEAT_S%s.inp" % (args.prefix, sev), parts)

    # ---------------- mechanical jobs ------------------------------------
    # The control job must not overwrite the job it is a control FOR, so the
    # forced closure fraction goes in the file name.
    hclo_tag = "" if args.hclo is None else "_HCLO%g" % args.hclo
    probe_steps = {}
    for sev in args.sev:
        heatjob = "%s_HEAT_S%s" % (args.prefix, sev)
        for trs in args.trs:
            # TRS B: damage live only during the cooldown (step 1), frozen
            # afterwards.  A and C keep damage live throughout.
            this_card = patch_card(card, 26, 1.0) if trs == "B" else card
            # --hclo: the crack-closure control job (a1-0027 item 2).  C3, the
            # half-cycle asymmetry claim, is a DIFFERENCE between H_clo on and
            # off, and the 3 x 3 matrix contains only "on".  One extra job with
            # slot 37 forced to 0 supplies the other half of that difference;
            # nothing else in the deck changes, so the difference is the
            # closure model and only the closure model.
            if args.hclo is not None:
                this_card = patch_card(this_card, 37, args.hclo)
            body = [this_card]
            if trs != "A":
                body.append(expan)
            body.append(MACRO_ORIENTATION)
            body.append("*Solid Section, ElSet=ALL, "
                        "Material=CSIC_MACRO_CDM, Orientation=MACRO_AXES")
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
            write("%s_MECH_S%s_TRS%s%s.inp"
                  % (args.prefix, sev, trs, hclo_tag), parts)
            probe_steps[(sev, trs)] = probe_step

    # ---------------- residual-strength continuations --------------------
    for sev in args.sev:
        for trs in args.trs:
            base = "%s_MECH_S%s_TRS%s%s" % (args.prefix, sev, trs, hclo_tag)
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
                write("%s_RESID_S%s_TRS%s%s_N%d.inp"
                      % (args.prefix, sev, trs, hclo_tag, cp), parts)

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
