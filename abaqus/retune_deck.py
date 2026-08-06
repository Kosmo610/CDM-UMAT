#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retune_deck.py
==============
Rewrite the material cards and the analysis steps of an already-assembled
ZHANG2022 RVE deck WITHOUT touching the mesh, the orientation, the ElSets or
the PBC *Equation block.

Why this exists
---------------
The M1 run of 2026-07-28 (ZHANG2022_c26k_RT23 / _T500 / _T1000) died in all
three jobs.  docs/M1_FAILURE_ANALYSIS.md has the full post-mortem; the short
version is that every fix is a CARD CONSTANT or a STEP KEYWORD -- none of them
needs a change to the UMAT, so V1_0 stays frozen (CLAUDE.md).  Re-assembling
from the TexGen mesh is not possible here because the coarse mesh source is not
in the repository; only the assembled 2.5 MB decks are.  So this script splices
new cards and steps onto the deck we already have.

What it changes, and why (all measured, see the failure analysis)
----------------------------------------------------------------
  dmax  0.99 -> 0.90   a failed matrix element kept 1 % of 350 GPa = 3.5 GPa.
                       15369 such elements next to intact ones made the global
                       stiffness matrix badly conditioned.  0.90 leaves 35 GPa.
  eta   0.02 -> 0.05   viscous damage regularisation.  At the maximum allowed
                       increment 0.0025 this takes the realised fraction of the
                       damage target from 0.111 to 0.048 per increment.
  djump 0.10 -> 0.03   REVERTED on 2026-07-30, see below.
  djump kept at 0.10   The 0.03 experiment made things WORSE.  M1FIX_c26k_T500
                       and _T1000 did not diverge -- they CRAWLED, running the
                       whole 10000-increment budget at a median time increment
                       of 9.5e-08 (the maximum allowed is 2.5e-03, so a factor
                       of 26000 down) and burning 15.6 h and 15.3 h of wall
                       clock to reach LESS of the step than the un-retuned run
                       had: 68 C and 147 C against 186 C.  2888 of 12888
                       attempts failed, and with that failure rate Abaqus can
                       never grow the increment back.  Tightening the UMAT's
                       own pre-emptive cutback simply multiplied the number of
                       cutbacks; it did not make any of them succeed.
  stabilize            *Static, stabilize=... is the standard Abaqus/Standard
                       cure for localisation.  ALLSD/ALLIE is written to the
                       history output so the artificial energy can be checked.
  disp. control 0.08 -> 1.0
                       In RT23 the force residual at iteration 7 was 1.393e-3
                       against an alternate tolerance of 0.02*0.228 = 4.56e-3,
                       i.e. FORCE HAD CONVERGED.  What rejected the iteration
                       was the displacement-correction check: |c|/|du| =
                       5.322e-10/9.956e-10 = 0.53 against 0.08 -- a ratio of two
                       numbers that are both physically zero.  Relaxing it keeps
                       the force criterion in charge.
  I_R   10 -> 16       the log-rate check printed "SOLUTION APPEARS TO BE
                       DIVERGING" at iteration 8.  The UMAT returns a SECANT
                       Jacobian, so Newton converges linearly, not
                       quadratically, and that check gives false positives.
  I_A   20 -> 8        cutbacks were proven not to help; 18 of them burned
                       ~23 min of wall clock before the job gave up.
  min increment 1e-12 -> 1e-8
                       same reason.  At 1e-8 the strain increment is 1.5e-11.
  inc 10000 -> 2000    a job that is crawling must die in about two hours, not
                       fifteen.  Nothing useful happened in the last 8000
                       increments of either 15-hour run.

  --zero               *Expansion, zero= (the stress-free temperature).  This
                       one is PHYSICS, not numerics.  Leave it at 1050 unless
                       you have decided to calibrate it -- see the analysis doc.

Usage
-----
  python3 retune_deck.py ZHANG2022_c26k_RT23.inp -o M1FIX_RT23.inp
  python3 retune_deck.py ZHANG2022_c26k_RT23.inp -o M1FIX_RT23_z600.inp --zero 600
  python3 retune_deck.py --check          # static self-test, no deck needed
"""
from __future__ import print_function

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assemble_inp import (MATRIX_DEPVAR, YARN_DEPVAR,          # noqa: E402
                          MATRIX_USERMAT, YARN_USERMAT)

MAT_ANCHOR = "*Material, Name=SIC_MATRIX_DAMAGE"

# --------------------------------------------------------------------------
# card slot map (1-indexed, exactly as PROPS(k) in the UMAT)
# --------------------------------------------------------------------------
MATRIX_SLOTS = dict(e=2, xt=4, xc=5, dmax_t=8, dmax_c=9, eta=10, djump=11,
                    gm_t=15, gm_c=16, key=22)
YARN_SLOTS = dict(e1=2, e2=3, xt=11, xc=12, yt=13, yc=14,
                  dmax_1=22, dmax_t=23, eta=24, djump=25,
                  g1t=32, g1c=33, gtt=34, gtc=35)
MATRIX_NPROPS, YARN_NPROPS = 22, 38
MATRIX_KEY = 30.0                      # PROPS(22) guard checked by the UMAT

# --------------------------------------------------------------------------
# defaults -- the retuned values
# --------------------------------------------------------------------------
D_DMAX = 0.90
D_ETA = 0.05
D_DJUMP = 0.10        # NOT 0.03 -- see the 2026-07-30 note below
D_INC = 2000          # increment budget per step; 10000 let two jobs crawl 15 h
D_STABILIZE = 2.0e-4
D_ALLSDTOL = 0.05
D_DISPCTRL = 1.0
D_MININC = 1.0e-8
D_ZERO = 1050.0
D_HSMO = 0.0                           # V3_0 only; 0 = published sign(I1) step
D_IR = 16                              # log-rate divergence check
D_IA = 8                               # cutbacks per increment

# --------------------------------------------------------------------------
# 2026-07-30, M3 post-mortem: the traction-free macro drivers
# --------------------------------------------------------------------------
# M3 fixed the reheat step outright (T500/T1000 step 2: 403 increments at full
# dt, zero failed attempts, where M1FIX never finished it at all).  What was
# left was the tension step, and reading the .msg iteration by iteration showed
# the residual was almost never on the loaded driver.  It sat on e_z, e_xy and
# e_xz -- the drivers with NO prescribed boundary condition, whose equilibrium
# equation is "this macro stress component is zero".
#
# Those residuals are meaningless at the level Abaqus was demanding.  The driver
# reaction is R = sigma * V_RVE, so with V_RVE = 5.390 mm^3 the largest residual
# RT23 ever failed on, 3.959e-03 N.mm, is a macro stress error of 7.3e-04 MPa.
# Abaqus was comparing it against 0.5 % of the global average nodal force
# (~0.15 N.mm), i.e. demanding the traction-free stresses vanish to 1.4e-04 MPa
# while the axial stress being measured is ~100-200 MPa.  A tolerance five
# orders of magnitude tighter than the quantity of interest.
#
# Two changes, in order of how much they are justified:
#
# SHEARLOCK -- prescribe eps_xy = eps_xz = eps_yz = 0 in every step.  For a
#   balanced orthogonal 2-D weave loaded along a principal material axis these
#   are zero by symmetry, so this removes three near-singular DOFs at no
#   physical cost.  It is aimed straight at the observed failures: at the moment
#   of death 11 of T1000's last 12 iterations and 13 of RT23's last 14 were on a
#   shear driver, and the only numerical singularities in the whole M3 set (36
#   of them, RT23) were on e_xy and e_y with pivot RATIO 2.6e+10.
#   This is an ASSUMPTION ABOUT THE MESH, so postprocess/driver_audit.py
#   measures the macro shear stress on the existing odbs and reports whether it
#   is under 1 % of sigma_xx.  Do not ship a thesis number without that check.
#
# FTOL -- relax the force residual ratio from Abaqus' default 0.005.  At 0.02
#   the tolerance becomes ~3e-03 N.mm = 5.6e-04 MPa of macro stress, still four
#   orders below the axial stress.  This one is a judgement call and applies to
#   the mesh equations too, so it is reported in the thesis rather than buried.
D_SHEARLOCK = True
D_FTOL = 0.02
ABAQUS_DEFAULT_FTOL = 0.005            # what Abaqus uses if we say nothing

# --------------------------------------------------------------------------
# 2026-08-03, M6: the three card values that stopped being guesses
# --------------------------------------------------------------------------
# These are NOT knobs and none of them was fitted.  Each replaces a card entry
# whose provenance turned out to be wrong or missing:
#
#   --matrix-e   350000 -> 213110 MPa.  The mesh is a FILLED CELL but the real
#                material is 19.6 % pore by its own measured density.  In a
#                parallel sum, deleting a phase's volume and scaling its
#                modulus are the same operation, so the knockdown 0.6089
#                emulates the void the mesh does not have.  Derivation and the
#                42 checks behind it: data/properties/porosity_stiffness.py.
#
#   --yarn-xt    2835 -> 475/581/694 MPa at 23/500/1000 C.  2835 was
#                Vf x 3580, and 3580 is a STRAND figure.  refs/[08] Sauder
#                Table 1 measured T300 single filaments directly and gives the
#                Weibull parameters; evaluated at the RVE's own aligned-fibre
#                volume of 1.063 mm^3 -- within 6 % of Sauder's own 1 mm^3
#                reference, so no extrapolation -- they give the band above.
#                data/properties/insitu_yarn_strength.py, 51 checks.
#
#   --gtt/--gtc  0 -> 0.107 N/mm.  Zero DISABLES the crack band, which leaves
#                the transverse yarn modes not mesh objective at all.  0.107
#                is Shi refs/[31] on 2D plain-weave C/SiC; Gtc takes the same
#                value on Ge's convention because no transverse COMPRESSIVE
#                fracture energy for C/SiC exists.  That is a stated
#                limitation, not a measurement.
#                data/properties/yarn_fracture_energy.py.
#
# WHAT IS DELIBERATELY *NOT* CHANGED: the matrix fracture energy Gm.  The
# porosity knockdown applies to E, k and rho -- not to Gf, whose 0.031 N/mm
# comes from Snead's K_Ic and is the one matrix entry with independent support.
# Lowering E does move the snap-back limit though, and section 5 of the report
# below prints the new margin so it cannot pass unnoticed.
D_MATRIX_E = None                      # None = keep the template's value
D_G1T = None
D_G1C = None
D_YARN_XT = None
D_GTT = None
D_GTC = None

#: Largest element characteristic length in the coarse 26k mesh [mm].
#: Measured, not assumed -- data/properties/yarn_fracture_energy.py section 4
#: reports CELENT max 0.0845, median 0.0573 over the 26452 elements.
#: A different mesh needs a different number here, and the .ori with it.
MESH_CELENT_MAX = 0.0845
SNAPBACK_MARGIN = 1.02                 # KABAND's own guard factor


def snapback_limit(strength, modulus, gf):
    """Largest element the crack band can regularise: le < Gf/(1.02*g0).

    g0 = X^2/(2E) is the elastic energy density at the onset of softening.
    Above this length the softening branch snaps back, KABAND clamps A to 50
    and the element is effectively brittle -- which it reports through ATEFF,
    but only if somebody looks.
    """
    if gf <= 0.0:
        return None                    # crack band disabled: no limit, no
        # regularisation either
    g0 = strength * strength / (2.0 * modulus)
    return gf / (SNAPBACK_MARGIN * g0)


def crack_band_rows(a):
    """(mode, strength, modulus, Gf, le_max, ok) for every regularised mode.

    Called for its report, and by the self-test.  A row with Gf = 0 is listed
    with le_max None so that 'the crack band is off' never reads as 'the crack
    band is fine'.
    """
    kw, m = card_numbers(MATRIX_USERMAT["v2"])
    kw, y = card_numbers(YARN_USERMAT["v2"])
    me = a.matrix_e if a.matrix_e is not None else m[MATRIX_SLOTS["e"] - 1]
    yxt = a.yarn_xt if a.yarn_xt is not None else y[YARN_SLOTS["xt"] - 1]
    gtt = a.gtt if a.gtt is not None else y[YARN_SLOTS["gtt"] - 1]
    gtc = a.gtc if a.gtc is not None else y[YARN_SLOTS["gtc"] - 1]
    g1t = a.g1t if a.g1t is not None else y[YARN_SLOTS["g1t"] - 1]
    g1c = a.g1c if a.g1c is not None else y[YARN_SLOTS["g1c"] - 1]
    out = []
    for mode, x, e, gf in (
            ("matrix tension", m[MATRIX_SLOTS["xt"] - 1], me,
             m[MATRIX_SLOTS["gm_t"] - 1]),
            ("matrix compression", m[MATRIX_SLOTS["xc"] - 1], me,
             m[MATRIX_SLOTS["gm_c"] - 1]),
            ("yarn axial tension", yxt, y[YARN_SLOTS["e1"] - 1], g1t),
            ("yarn axial compression", y[YARN_SLOTS["xc"] - 1],
             y[YARN_SLOTS["e1"] - 1], g1c),
            ("yarn transverse tension", y[YARN_SLOTS["yt"] - 1],
             y[YARN_SLOTS["e2"] - 1], gtt),
            ("yarn transverse compression", y[YARN_SLOTS["yc"] - 1],
             y[YARN_SLOTS["e2"] - 1], gtc)):
        le = snapback_limit(x, e, gf)
        out.append((mode, x, e, gf, le,
                    None if le is None else le > MESH_CELENT_MAX))
    return out


def card_numbers(card):
    """Return (keyword_line, [float, ...]) for a *User Material block."""
    lines = card.strip().splitlines()
    nums = []
    for ln in lines[1:]:
        for tok in ln.split(","):
            tok = tok.strip()
            if tok:
                nums.append(float(tok))
    return lines[0], nums


def emit_card(kw, nums, per_line=8):
    # The keyword line carries the constant count.  Appending a block without
    # rewriting it would hand Abaqus a card that claims 22 constants while
    # supplying 25 -- silently misread, not rejected.
    kw = re.sub(r"constants\s*=\s*\d+", "constants=%d" % len(nums), kw)
    out = [kw]
    for i in range(0, len(nums), per_line):
        chunk = nums[i:i + per_line]
        out.append(", ".join(_fmt(x) for x in chunk))
    return "\n".join(out)


def _fmt(x):
    if x == int(x) and abs(x) < 1e7:
        return "%.1f" % x
    return repr(x)


HSMO_KEY = 32.0                        # PROPS(25+4*NT) guard, V3_0 only


def retune_matrix(dmax, eta, djump, hsmo=0.0, matrix_e=None):
    kw, n = card_numbers(MATRIX_USERMAT["v2"])
    if len(n) != MATRIX_NPROPS:
        raise ValueError("matrix card has %d constants, expected %d"
                         % (len(n), MATRIX_NPROPS))
    if matrix_e is not None:
        # Guard the range rather than the value: 213110 is the porosity
        # knockdown, but a typo of 213 or 2131100 must not reach a solver.
        if not (50.0e3 <= matrix_e <= 500.0e3):
            raise ValueError("matrix E = %r MPa is outside [50e3, 500e3]; "
                             "dense CVD SiC is 460e3 and the porosity "
                             "knockdown gives 213110" % matrix_e)
        n[MATRIX_SLOTS["e"] - 1] = matrix_e
    n[MATRIX_SLOTS["dmax_t"] - 1] = dmax
    n[MATRIX_SLOTS["dmax_c"] - 1] = dmax
    n[MATRIX_SLOTS["eta"] - 1] = eta
    n[MATRIX_SLOTS["djump"] - 1] = djump
    if n[MATRIX_SLOTS["key"] - 1] != MATRIX_KEY:
        raise ValueError("matrix card key PROPS(22) is %r, the UMAT rejects "
                         "anything but %r" % (n[21], MATRIX_KEY))
    if hsmo < 0.0 or hsmo > 1.0:
        raise ValueError("HSMO must be in [0,1], got %r" % hsmo)
    if hsmo > 0.0:
        # V3_0 25+4*NT layout: NT=0, then HSMO, then the block guard.
        n = n + [0.0, hsmo, HSMO_KEY]
    return emit_card(kw, n)


def retune_yarn(dmax, eta, djump, yarn_xt=None,
                g1t=None, g1c=None, gtt=None, gtc=None):
    """Retune the yarn card.

    The four fracture energies are exposed because Ch.4 4.9-0 (2nd amendment)
    and verification/m6_calibration_plan.py put them at the head of the M6
    queue:

      G1t = G1c = 12.5 N/mm is one of the four DEV inputs, carried over from
      Ge refs/[24] Table 3, which is carbon/PHENOLIC.  At that value the
      crack-band exponent of the yarn longitudinal branch is A = 0.239 --
      8.4x gentler than the fixed default of 2.0 -- so the yarn sheds almost
      no load after peak.  That is the leading explanation for M5_c26k_T1000
      producing 313 monotonically increasing points with no peak.  A = 2.0
      would need 2.664 N/mm.

      Gtt = Gtc = 0 switches the crack band OFF for the transverse modes, so
      they run at the fixed exponent and are not mesh-regularised at all --
      and the transverse modes are the ones the cooldown drives.  Gtt has a
      source (Shi refs/[31], 0.107 N/mm on 2D plain weave C/SiC) and it is
      admissible on this mesh: the snap-back limit Gf/g0 is 1.482 mm against
      a largest CELENT of 0.0845 mm.  Gtc has no source and stays 0.

    Passing None leaves a slot at whatever the deck already had.
    """
    kw, n = card_numbers(YARN_USERMAT["v2"])
    if len(n) != YARN_NPROPS:
        raise ValueError("yarn card has %d constants, expected %d"
                         % (len(n), YARN_NPROPS))
    if yarn_xt is not None:
        if not (100.0 <= yarn_xt <= 4000.0):
            raise ValueError("yarn Xt = %r MPa is outside [100, 4000]; the "
                             "in-situ band is 475-745 and the old strand "
                             "value was 2835" % yarn_xt)
        n[YARN_SLOTS["xt"] - 1] = yarn_xt
    for key, val in (("g1t", g1t), ("g1c", g1c),
                     ("gtt", gtt), ("gtc", gtc)):
        if val is None:
            continue
        if val < 0.0:
            raise ValueError(
                "%s = %g: a NEGATIVE yarn fracture energy would be read "
                "by KABAND as the INELASTIC convention, which only the "
                "MACRO card uses (Ch.4 4.6.1).  The micro card carries "
                "total-area values." % (key, val))
        n[YARN_SLOTS[key] - 1] = val
    n[YARN_SLOTS["dmax_1"] - 1] = dmax
    n[YARN_SLOTS["dmax_t"] - 1] = dmax
    n[YARN_SLOTS["eta"] - 1] = eta
    n[YARN_SLOTS["djump"] - 1] = djump
    for key, val in (("g1t", g1t), ("g1c", g1c),
                     ("gtt", gtt), ("gtc", gtc)):
        if val is not None:
            if val < 0.0:
                raise ValueError(
                    "%s = %g: a NEGATIVE yarn fracture energy would be read "
                    "by KABAND as the inelastic convention, which only the "
                    "MACRO card uses (Ch.4 4.6.1).  The micro card carries "
                    "total-area values." % (key, val))
            n[YARN_SLOTS[key] - 1] = val
    return emit_card(kw, n)


def materials(a):
    L = ["*Material, Name=SIC_MATRIX_DAMAGE",
         MATRIX_DEPVAR,
         retune_matrix(a.dmax, a.eta, a.djump, a.hsmo, a.matrix_e),
         "*Expansion, zero=%g." % a.zero,
         "4.5e-06,",
         "*Material, Name=CSIC_YARN_DAMAGE",
         YARN_DEPVAR,
         retune_yarn(a.dmax, a.eta, a.djump, a.yarn_xt,
                     a.g1t, a.g1c, a.gtt, a.gtc),
         "*Expansion, type=ORTHO, zero=%g." % a.zero,
         "1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06"]
    return "\n".join(L)


#: The only values Abaqus accepts for the FIELD parameter of
#: `*CONTROLS, PARAMETERS=FIELD`.  FORCE is NOT among them, and that mistake
#: cost a lab morning: `field=force` is rejected by the input file processor,
#: so every M4 job died in pre.exe before a single increment.
VALID_CONTROL_FIELDS = ("DISPLACEMENT", "ROTATION", "TEMPERATURE",
                        "ELECTRICAL POTENTIAL", "HYDROSTATIC FLUID PRESSURE",
                        "WARPING", "GLOBAL")


def controls(a):
    """Solver controls for one step.

    FORCE IS NOT A FIELD.  The FIELD parameter names the SOLUTION variable,
    and for a stress/displacement analysis that is DISPLACEMENT.  The force
    residual tolerance is the FIRST data value of that same block -- Rn^alpha,
    default 0.005, the familiar "residual must be under 0.5 % of the average
    flux" rule.  The displacement-correction criterion Cn^alpha is the second.
    So loosening the force tolerance means writing

        *Controls, parameters=field, field=displacement
         0.02, 1

    and NOT a second block with field=force, which does not exist.
    """
    # Rn blank keeps the Abaqus default, so a deck built with --ftol 0.005 is
    # byte-identical to the pre-M4 decks and the regression stays meaningful.
    rn = ("" if abs(a.ftol - ABAQUS_DEFAULT_FTOL) <= 1.0e-12
          else "%g" % a.ftol)
    return ("*Controls, parameters=time incrementation\n"
            " 12, %d, , 40, , , , %d, , ,\n"
            "*Controls, parameters=field, field=displacement\n"
            " %s, %g\n"
            "*Controls, parameters=line search\n5\n"
            % (a.i_r, a.i_a, rn, a.dispctrl))


def shear_lock(a):
    """Prescribe the three macro shear strains to zero.

    Returned as boundary CARD LINES only -- the caller owns the '*Boundary'
    keyword, because a step may already be opening one for the loaded driver
    and two *Boundary blocks in a row would be legal but harder to read.
    """
    if not a.shearlock:
        return []
    return ["ConstraintsDriver3, 1, 1, 0.0",     # eps_xy
            "ConstraintsDriver4, 1, 1, 0.0",     # eps_xz
            "ConstraintsDriver5, 1, 1, 0.0"]     # eps_yz


OUTPUT = """*Output, field, number interval=101, time marks=NO
*Element Output, directions=YES
S, E, EE, THE, IVOL, SDV
*Node Output
U, RF
*Output, history, frequency=1
*Energy Output
ALLIE, ALLSD, ALLWK, ALLPD
%s
*Restart, write, number interval=20, time marks=NO""" % "\n".join(
    "*Node Output, nset=ConstraintsDriver%d\nU, RF" % i for i in range(6))


def static_line(a, dt0, minc):
    if a.stabilize > 0.0:
        head = ("*Static, stabilize=%g, allsdtol=%g, continue=NO"
                % (a.stabilize, a.allsdtol))
    else:
        head = "*Static"
    return "%s\n%g, 1.0, %g, 0.0025" % (head, dt0, minc)


def thermal_bc(a, T):
    """Boundary + temperature cards for a thermal step.

    The shear lock has to be restated in every step: a *Boundary block in a
    later step does not inherit a prescribed value from an earlier one unless
    it is repeated, and the whole point is that these three DOFs are never left
    free once damage starts localising.
    """
    lines = []
    lock = shear_lock(a)
    if lock:
        lines.append("*Boundary")
        lines.extend(lock)
    lines.append("*Temperature")
    lines.append("AllNodes, %g." % T)
    return "\n".join(lines)


def steps(a, case):
    S = []
    S.append("*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=%d" % a.inc)
    S.append("Uniform cooling from %g degC to 23 degC with progressive damage"
             % a.zero)
    S.append(static_line(a, 0.001, a.mininc))
    S.append(controls(a) + thermal_bc(a, 23))
    S.append(OUTPUT)
    S.append("*End Step")
    if case["heat"] is not None:
        T = case["heat"]
        S.append("*Step, Name=Heating_to_%dC, nlgeom=NO, inc=%d" % (T, a.inc))
        S.append("Uniform reheating from 23 degC to %d degC before tension" % T)
        S.append(static_line(a, 0.001, a.mininc))
        S.append(controls(a) + thermal_bc(a, T))
        S.append(OUTPUT)
        S.append("*End Step")
    T = case["test"]
    S.append("*Step, Name=Tension_at_%dC, nlgeom=NO, inc=%d" % (T, a.inc))
    S.append("Uniaxial x tension at %d degC via ConstraintsDriver0" % T)
    S.append(static_line(a, 0.0005, a.mininc))
    S.append(controls(a) + "\n".join(
        ["*Boundary", "ConstraintsDriver0, 1, 1, %.6f" % case["eps"]]
        + shear_lock(a)))
    S.append(OUTPUT)
    S.append("*End Step")
    return "\n".join(S)


def detect_case(text):
    """Read the test temperature, the reheat target and the applied strain out
    of the deck being retuned, so the tool cannot silently change the case."""
    m = re.search(r"\*Step,\s*Name=Tension_at_(\d+)C", text)
    if not m:
        raise ValueError("no 'Tension_at_<T>C' step found -- is this a "
                         "ZHANG2022 RVE deck?")
    test = int(m.group(1))
    h = re.search(r"\*Step,\s*Name=Heating_to_(\d+)C", text)
    heat = int(h.group(1)) if h else None
    e = re.search(r"ConstraintsDriver0,\s*1,\s*1,\s*([0-9.eE+-]+)", text)
    if not e:
        raise ValueError("no tension *Boundary on ConstraintsDriver0 found")
    return dict(test=test, heat=heat, eps=float(e.group(1)))


def retune(text, a):
    i = text.find(MAT_ANCHOR)
    if i < 0:
        raise ValueError("anchor %r not found -- deck was not produced by "
                         "assemble_inp.py" % MAT_ANCHOR)
    case = detect_case(text)
    head = text[:i].rstrip("\n")

    # keep the *Solid Section lines verbatim: they name the real ElSets and
    # the real orientation, which differ from mesh to mesh.
    sections = re.findall(r"^\*Solid Section,.*\n.*$", text[i:], re.MULTILINE)
    if not sections:
        raise ValueError("no *Solid Section found after the material anchor")

    parts = [head,
             materials(a),
             "\n".join(sections),
             "*Initial Conditions, type=TEMPERATURE\nAllNodes, %g." % a.zero,
             steps(a, case)]
    return "\n".join(parts) + "\n", case, len(sections)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def _fake_deck():
    return "\n".join([
        "*Heading",
        " fake",
        "*Node",
        "1, 0., 0., 0.",
        "*Element, Type=C3D4",
        "1, 1, 1, 1, 1",
        "*ElSet, ElSet=Matrix",
        "1",
        "*NSet, NSet=AllNodes, Generate",
        "1, 1, 1",
        "*Equation",
        "2",
        "FaceA, 1, 1.0, FaceB, 1, -1.0",
        MAT_ANCHOR,
        MATRIX_DEPVAR,
        MATRIX_USERMAT["v2"],
        "*Expansion, zero=1050.",
        "4.5e-06,",
        "*Material, Name=CSIC_YARN_DAMAGE",
        YARN_DEPVAR,
        YARN_USERMAT["v2"],
        "*Expansion, type=ORTHO, zero=1050.",
        "1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06",
        "*Solid Section, ElSet=Matrix, Material=SIC_MATRIX_DAMAGE",
        "1.0,",
        "*Solid Section, ElSet=Yarn0, Material=CSIC_YARN_DAMAGE, "
        "Orientation=TexGenOrientations",
        "1.0,",
        "*Initial Conditions, type=TEMPERATURE",
        "AllNodes, 1050.",
        "*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=10000",
        "cool",
        "*Static",
        "0.001, 1.0, 1.0E-12, 0.0025",
        "*Temperature",
        "AllNodes, 23.",
        "*End Step",
        "*Step, Name=Heating_to_500C, nlgeom=NO, inc=10000",
        "heat",
        "*Static",
        "0.001, 1.0, 1.0E-12, 0.0025",
        "*Temperature",
        "AllNodes, 500.",
        "*End Step",
        "*Step, Name=Tension_at_500C, nlgeom=NO, inc=10000",
        "pull",
        "*Static",
        "0.0005, 1.0, 1.0E-12, 0.0025",
        "*Boundary",
        "ConstraintsDriver0, 1, 1, 0.003200",
        "*End Step",
    ]) + "\n"


class _A(object):
    dmax, eta, djump = D_DMAX, D_ETA, D_DJUMP
    stabilize, allsdtol = D_STABILIZE, D_ALLSDTOL
    dispctrl, mininc, zero = D_DISPCTRL, D_MININC, D_ZERO
    i_r, i_a = D_IR, D_IA
    hsmo = D_HSMO
    inc = D_INC
    shearlock = D_SHEARLOCK
    ftol = D_FTOL
    matrix_e, yarn_xt, gtt, gtc = D_MATRIX_E, D_YARN_XT, D_GTT, D_GTC
    g1t, g1c = D_G1T, D_G1C


def check():
    ok = [0]
    bad = [0]

    def t(name, cond, extra=""):
        if cond:
            ok[0] += 1
            print("  PASS  %s %s" % (name, extra))
        else:
            bad[0] += 1
            print("  FAIL  %s %s" % (name, extra))

    print("retune_deck.py self-test")

    # --- card arithmetic -------------------------------------------------
    kw, n0 = card_numbers(MATRIX_USERMAT["v2"])
    t("matrix source card has 22 constants", len(n0) == MATRIX_NPROPS,
      "(%d)" % len(n0))
    t("matrix source dmax is the old 0.99",
      n0[7] == 0.99 and n0[8] == 0.99)
    t("matrix source eta is the old 0.02", n0[9] == 0.02)
    t("matrix source djump is the old 0.10", n0[10] == 0.10)
    t("matrix guard PROPS(22)=30", n0[21] == MATRIX_KEY)

    kwm, nm = card_numbers(retune_matrix(D_DMAX, D_ETA, D_DJUMP))
    t("retuned matrix still 22 constants", len(nm) == MATRIX_NPROPS,
      "(%d)" % len(nm))
    t("retuned matrix dmax_t/dmax_c = 0.90", nm[7] == D_DMAX and nm[8] == D_DMAX)
    t("retuned matrix eta = 0.05", nm[9] == D_ETA)
    t("retuned matrix djump = %g" % D_DJUMP, nm[10] == D_DJUMP)
    t("retuned matrix guard survived", nm[21] == MATRIX_KEY)
    untouched = [i for i in range(22) if i not in (7, 8, 9, 10)]
    t("retuned matrix touches ONLY the four intended slots",
      all(nm[i] == n0[i] for i in untouched))

    kwy, ny0 = card_numbers(YARN_USERMAT["v2"])
    kwy2, ny = card_numbers(retune_yarn(D_DMAX, D_ETA, D_DJUMP))
    t("yarn source card has 38 constants", len(ny0) == YARN_NPROPS,
      "(%d)" % len(ny0))
    t("retuned yarn still 38 constants", len(ny) == YARN_NPROPS,
      "(%d)" % len(ny))
    t("retuned yarn dmax_1/dmax_t = 0.90", ny[21] == D_DMAX and ny[22] == D_DMAX)
    t("retuned yarn eta = 0.05", ny[23] == D_ETA)
    t("retuned yarn djump = %g" % D_DJUMP, ny[24] == D_DJUMP)
    yun = [i for i in range(38) if i not in (21, 22, 23, 24)]
    t("retuned yarn touches ONLY the four intended slots",
      all(ny[i] == ny0[i] for i in yun))

    # a broken card must be rejected, not silently written
    save = MATRIX_USERMAT["v2"]
    try:
        MATRIX_USERMAT["v2"] = save.replace(", 30.0", ", 31.0")
        try:
            retune_matrix(D_DMAX, D_ETA, D_DJUMP)
            t("wrong PROPS(22) guard is rejected", False)
        except ValueError:
            t("wrong PROPS(22) guard is rejected", True)
    finally:
        MATRIX_USERMAT["v2"] = save

    # --- whole-deck round trip ------------------------------------------
    a = _A()
    out, case, nsec = retune(_fake_deck(), a)
    t("case detected from the deck itself",
      case == dict(test=500, heat=500, eps=0.0032), repr(case))
    t("both *Solid Section lines carried over verbatim", nsec == 2)
    t("mesh preamble preserved", "*Element, Type=C3D4" in out
      and "FaceA, 1, 1.0, FaceB, 1, -1.0" in out)
    t("PBC *Equation preserved", out.count("*Equation") == 1)
    t("three steps written", out.count("*Step, Name=") == 3)
    t("every step closed", out.count("*Step, Name=") == out.count("*End Step"))
    t("stabilization on every *Static",
      out.count("*Static, stabilize=") == 3 and "\n*Static\n" not in out)
    t("no 1e-12 minimum increment left", "1.0E-12" not in out
      and "1e-12" not in out)
    t("minimum increment is 1e-08",
      out.count("1e-08, 0.0025") == 3, "(%d)" % out.count("1e-08, 0.0025"))
    # Cn is the SECOND slot; Rn may or may not be filled depending on --ftol,
    # so match the slot rather than one particular rendering of the line.
    t("displacement control relaxed to 1 on every step",
      len(re.findall(r"field=displacement\n\s*[0-9.eE+-]*,\s*1\s*\n", out)) == 3,
      "%d steps" % len(re.findall(
          r"field=displacement\n\s*[0-9.eE+-]*,\s*1\s*\n", out)))
    t("I_R=16 and I_A=8 on every step",
      out.count(" 12, 16, , 40, , , , 8, , ,") == 3)
    t("energy output requested", out.count("ALLSD") == 3)
    t("SDV still in the field output", out.count("S, E, EE, THE, IVOL, SDV") == 3)
    t("restart still written", out.count("*Restart, write") == 3)
    t("orientation reference kept",
      "Orientation=TexGenOrientations" in out)
    t("applied strain unchanged", "ConstraintsDriver0, 1, 1, 0.003200" in out)

    # --zero must move BOTH expansions, the initial condition and the label
    a2 = _A()
    a2.zero = 600.0
    out2, _, _ = retune(_fake_deck(), a2)
    t("--zero moves both *Expansion blocks",
      out2.count("zero=600.") == 2, "(%d)" % out2.count("zero=600."))
    t("--zero moves the initial temperature",
      "*Initial Conditions, type=TEMPERATURE\nAllNodes, 600." in out2)
    t("--zero relabels the cooling step",
      "from 600 degC to 23 degC" in out2)
    t("--zero leaves no 1050 behind", "1050" not in out2)

    # stabilization can be switched off
    a3 = _A()
    a3.stabilize = 0.0
    out3, _, _ = retune(_fake_deck(), a3)
    t("--stabilize 0 writes a plain *Static",
      out3.count("\n*Static\n") == 3 and "stabilize=" not in out3)

    # a deck with no reheat step must come out with two steps
    rt = _fake_deck().replace("Tension_at_500C", "Tension_at_23C")
    rt = re.sub(r"\*Step, Name=Heating_to_500C.*?\*End Step\n", "", rt,
                flags=re.S)
    out4, case4, _ = retune(rt, _A())
    t("RT23-style deck (no reheat) gives two steps",
      out4.count("*Step, Name=") == 2 and case4["heat"] is None)

    # --hsmo must lengthen the matrix card to exactly 25 and keep the rest
    kwh, nh = card_numbers(retune_matrix(D_DMAX, D_ETA, D_DJUMP, 0.1))
    t("hsmo card has 25 constants (25+4*NT with NT=0)", len(nh) == 25,
      "(%d)" % len(nh))
    t("hsmo card keeps the V1_0 guard at slot 22", nh[21] == MATRIX_KEY)
    t("hsmo card sets NT=0 at slot 23", nh[22] == 0.0)
    t("hsmo lands in slot 24", nh[23] == 0.1)
    t("hsmo block guard 32.0 in slot 25", nh[24] == HSMO_KEY)
    t("hsmo leaves slots 1-22 identical to the no-hsmo card",
      nh[:22] == nm[:22])
    t("22 vs 25 slot lengths are distinguishable mod 4",
      (22 % 4, 23 % 4, 25 % 4) == (2, 3, 1))
    for hbad in (-0.1, 1.5):
        try:
            retune_matrix(D_DMAX, D_ETA, D_DJUMP, hbad)
            t("hsmo=%g rejected" % hbad, False)
        except ValueError:
            t("hsmo=%g rejected" % hbad, True)
    ah = _A()
    ah.hsmo = 0.1
    outh, _, _ = retune(_fake_deck(), ah)
    t("hsmo deck writes constants=25", "*User Material, constants=25" in outh)
    t("hsmo deck leaves the yarn card at 38",
      "*User Material, constants=38" in outh)
    t("no-hsmo deck writes constants=22",
      "*User Material, constants=22" in out)

    # the 2026-07-30 regression guards
    t("default djump is NOT the 0.03 that caused the crawl", D_DJUMP >= 0.08,
      "%g" % D_DJUMP)
    t("default increment budget is capped well below 10000", D_INC <= 3000,
      "%d" % D_INC)
    ai = _A()
    ai.inc = 2000
    outi, _, _ = retune(_fake_deck(), ai)
    t("every step carries the increment cap",
      outi.count("inc=2000") == 3 and "inc=10000" not in outi,
      "%d steps" % outi.count("inc=2000"))

    # ---- the 2026-07-30 M3 post-mortem guards: free macro drivers ----
    t("shear lock is on by default", D_SHEARLOCK is True)
    t("default ftol is looser than the Abaqus default",
      D_FTOL > ABAQUS_DEFAULT_FTOL, "%g > %g" % (D_FTOL, ABAQUS_DEFAULT_FTOL))
    t("default ftol is still tight enough to be defensible", D_FTOL <= 0.05,
      "%g" % D_FTOL)

    alk = _A()
    outl, _, _ = retune(_fake_deck(), alk)
    # 3 steps in the fake deck (cool / heat / pull) x 3 shear DOFs
    for drv in (3, 4, 5):
        t("eps_%d driver locked in all 3 steps" % drv,
          outl.count("ConstraintsDriver%d, 1, 1, 0.0" % drv) == 3,
          "%d" % outl.count("ConstraintsDriver%d, 1, 1, 0.0" % drv))
    t("the loaded driver is NOT locked to zero",
      "ConstraintsDriver0, 1, 1, 0.0\n" not in outl)
    t("eps_yy and eps_zz stay free (Poisson must not be suppressed)",
      "ConstraintsDriver1, 1, 1," not in outl
      and "ConstraintsDriver2, 1, 1," not in outl)
    # every locked block must be introduced by a *Boundary keyword
    t("each thermal step opens a *Boundary before *Temperature",
      outl.count("*Boundary\nConstraintsDriver3") == 2,
      "%d thermal steps" % outl.count("*Boundary\nConstraintsDriver3"))
    t("the tension step locks shear in the same block as the load",
      "ConstraintsDriver0, 1, 1, 0.003200\nConstraintsDriver3, 1, 1, 0.0"
      in outl)
    # THE CHECK THAT WAS MISSING.  The old version asserted that a string I
    # invented appeared in the deck -- which it did, faithfully, and Abaqus
    # rejected the whole file for it.  Assert against Abaqus's grammar instead.
    import re as _re
    fields = _re.findall(r"parameters=field,\s*field=([a-z ]+)", outl)
    t("every *Controls FIELD= names a real Abaqus field",
      all(f.strip().upper() in VALID_CONTROL_FIELDS for f in fields),
      "saw %s" % sorted(set(f.strip() for f in fields)))
    t("FORCE is never used as a FIELD -- it is not one",
      "field=force" not in outl.lower(),
      "the force tolerance is Rn, the 1st value of field=displacement")
    t("the force tolerance rides in the displacement block",
      (" %g, %g\n" % (D_FTOL, D_DISPCTRL)) in outl,
      "Rn=%g, Cn=%g" % (D_FTOL, D_DISPCTRL))
    t("one displacement control block per step",
      outl.count("*Controls, parameters=field, field=displacement") == 3,
      "%d" % outl.count("*Controls, parameters=field, field=displacement"))
    # Rn and Cn must sit on ONE data line, comma separated, in that order.
    t("the control data line has both slots in the right order",
      bool(_re.search(r"field=displacement\n\s*%g,\s*%g\s*\n"
                      % (D_FTOL, D_DISPCTRL), outl)))

    afs = _A()
    afs.shearlock = False
    afs.ftol = ABAQUS_DEFAULT_FTOL
    outf, _, _ = retune(_fake_deck(), afs)
    # NB: match the *Boundary line, not the bare driver name -- every deck
    # also carries '*Node Output, nset=ConstraintsDriver3' for history output,
    # and those requests must survive --free-shear untouched.
    t("--free-shear removes every shear lock",
      not any(("ConstraintsDriver%d, 1, 1," % d) in outf for d in (3, 4, 5)))
    t("--free-shear keeps the shear history output requests",
      all(("nset=ConstraintsDriver%d" % d) in outf for d in (3, 4, 5)))
    t("ftol at the Abaqus default leaves Rn blank, keeping the default",
      "field=displacement\n , %g\n" % D_DISPCTRL in outf,
      "blank Rn -> Abaqus default 0.005")
    t("and still never writes a force field",
      "field=force" not in outf.lower())
    t("--free-shear still writes the tension load",
      "ConstraintsDriver0, 1, 1, 0.003200" in outf)
    t("--free-shear still writes both *Temperature cards",
      outf.count("*Temperature") == 2, "%d" % outf.count("*Temperature"))

    # ---- 2026-08-03, M6: the three card values that stopped being guesses --
    t("all four M6 options default to 'leave it alone'",
      (D_MATRIX_E, D_YARN_XT, D_GTT, D_GTC) == (None, None, None, None))
    a6 = _A()
    a6.matrix_e, a6.yarn_xt, a6.gtt, a6.gtc = 213109.6277699348, 694.4, .107, .107
    out6, _, _ = retune(_fake_deck(), a6)
    kw6, m6 = card_numbers(retune_matrix(D_DMAX, D_ETA, D_DJUMP, 0.0,
                                         213109.6277699348))
    kwy6, y6 = card_numbers(retune_yarn(D_DMAX, D_ETA, D_DJUMP,
                                        yarn_xt=694.4, gtt=0.107, gtc=0.107))
    t("matrix E lands in slot 2",
      abs(m6[MATRIX_SLOTS["e"] - 1] - 213109.6277699348) < 1e-6)
    t("yarn Xt lands in slot 11", abs(y6[YARN_SLOTS["xt"] - 1] - 694.4) < 1e-9)
    t("Gtt lands in slot 34", abs(y6[YARN_SLOTS["gtt"] - 1] - 0.107) < 1e-12)
    t("Gtc lands in slot 35", abs(y6[YARN_SLOTS["gtc"] - 1] - 0.107) < 1e-12)
    t("the matrix card is still 22 slots without --hsmo", len(m6) == 22)
    t("the yarn card is still 38 slots", len(y6) == 38)
    t("matrix Xt is NOT touched by the E change",
      m6[MATRIX_SLOTS["xt"] - 1] == nm[MATRIX_SLOTS["xt"] - 1], "310")
    # Gm is deliberately left alone: the knockdown covers E, k and rho, and Gm
    # is the one matrix entry with independent support (Snead's K_Ic).
    t("matrix Gf is NOT knocked down with E",
      m6[MATRIX_SLOTS["gm_t"] - 1] == nm[MATRIX_SLOTS["gm_t"] - 1]
      and m6[MATRIX_SLOTS["gm_c"] - 1] == nm[MATRIX_SLOTS["gm_c"] - 1],
      "0.031 kept")
    t("yarn Xc is NOT scaled with Xt (compression is kinking, not rupture)",
      y6[YARN_SLOTS["xc"] - 1] == ny[YARN_SLOTS["xc"] - 1], "1956 kept")
    t("yarn elastic constants untouched", y6[1:10] == ny[1:10])
    t("the M6 values reach the emitted deck",
      "694.4" in out6 and "0.107" in out6 and "213109" in out6)

    # guards: a typo must not reach a solver
    for bad_e in (213.0, 2131100.0, 0.0):
        try:
            retune_matrix(D_DMAX, D_ETA, D_DJUMP, 0.0, bad_e)
            t("matrix E=%g rejected" % bad_e, False)
        except ValueError:
            t("matrix E=%g rejected" % bad_e, True)
    for bad_x in (47.5, 47500.0):
        try:
            retune_yarn(D_DMAX, D_ETA, D_DJUMP, yarn_xt=bad_x)
            t("yarn Xt=%g rejected" % bad_x, False)
        except ValueError:
            t("yarn Xt=%g rejected" % bad_x, True)
    try:
        retune_yarn(D_DMAX, D_ETA, D_DJUMP, gtt=-0.1)
        t("negative Gtt rejected", False)
    except ValueError:
        t("negative Gtt rejected", True)

    # ---- the crack-band admissibility report --------------------------
    base_rows = dict((r[0], r) for r in crack_band_rows(_A()))
    m6_rows = dict((r[0], r) for r in crack_band_rows(a6))
    t("Gf=0 reports le_max None, never 'fine'",
      base_rows["yarn transverse tension"][4] is None
      and base_rows["yarn transverse tension"][5] is None,
      "the shipped card has Gtt=0")
    t("matrix tension is admissible on the SHIPPED card",
      base_rows["matrix tension"][5] is True,
      "le_max %.4f mm" % base_rows["matrix tension"][4])
    t("lowering E SHRINKS the matrix snap-back limit",
      m6_rows["matrix tension"][4] < base_rows["matrix tension"][4],
      "%.4f -> %.4f mm" % (base_rows["matrix tension"][4],
                           m6_rows["matrix tension"][4]))
    t("matrix tension is STILL admissible after the knockdown",
      m6_rows["matrix tension"][5] is True,
      "%.4f mm > CELENT max %.4f, margin %.2fx"
      % (m6_rows["matrix tension"][4], MESH_CELENT_MAX,
         m6_rows["matrix tension"][4] / MESH_CELENT_MAX))
    t("lowering yarn Xt RELAXES its snap-back limit",
      m6_rows["yarn axial tension"][4] > base_rows["yarn axial tension"][4],
      "%.4f -> %.2f mm" % (base_rows["yarn axial tension"][4],
                           m6_rows["yarn axial tension"][4]))
    t("Gtt=0.107 makes transverse tension admissible",
      m6_rows["yarn transverse tension"][5] is True,
      "le_max %.4f mm" % m6_rows["yarn transverse tension"][4])
    # This one is knowingly violated -- Ge's convention, no measurement exists.
    t("Gtc=0.107 is knowingly NOT admissible, and says so",
      m6_rows["yarn transverse compression"][5] is False,
      "le_max %.4f mm < CELENT max %.4f -- ATEFF must be read"
      % (m6_rows["yarn transverse compression"][4], MESH_CELENT_MAX))
    t("the mesh CELENT max is the measured one, not a guess",
      abs(MESH_CELENT_MAX - 0.0845) < 1e-9,
      "yarn_fracture_energy.py section 4")
    t("snapback_limit returns None for a disabled band",
      snapback_limit(310.0, 350.0e3, 0.0) is None)
    t("snapback_limit reproduces the documented 0.2214 mm",
      abs(snapback_limit(310.0, 350.0e3, 0.031) - 0.2214) < 5e-4,
      "%.4f" % snapback_limit(310.0, 350.0e3, 0.031))

    # a deck without the anchor must raise, not produce garbage
    try:
        retune(_fake_deck().replace(MAT_ANCHOR, "*Material, Name=SOMETHING"),
               _A())
        t("missing material anchor is rejected", False)
    except ValueError:
        t("missing material anchor is rejected", True)

    # ---- yarn fracture energies (M6 stage 0/1) ---------------------------
    def _yarn_slots(txt):
        import re as _re
        m = _re.search(r"\*Material, Name=CSIC_YARN_DAMAGE(.*?)\*Expansion",
                       txt, _re.S)
        blk = _re.search(r"\*User Material[^\n]*\n(.*)", m.group(1),
                         _re.S).group(1)
        return [float(x) for x in blk.replace("\n", ",").split(",")
                if x.strip()]

    base = retune(_fake_deck(), _A())[0]
    nb = _yarn_slots(base)
    t("untouched deck keeps G1t = 12.5", abs(nb[31] - 12.5) < 1e-12,
      "%g" % nb[31])
    t("untouched deck keeps Gtt = 0", nb[33] == 0.0, "%g" % nb[33])

    a = _A()
    a.g1t = a.g1c = 2.664
    a.gtt = 0.107
    n2 = _yarn_slots(retune(_fake_deck(), a)[0])
    t("--g1t reaches PROPS(32)", abs(n2[31] - 2.664) < 1e-12, "%g" % n2[31])
    t("--g1c reaches PROPS(33)", abs(n2[32] - 2.664) < 1e-12, "%g" % n2[32])
    t("--gtt reaches PROPS(34)", abs(n2[33] - 0.107) < 1e-12, "%g" % n2[33])
    t("--gtc left alone stays 0", n2[34] == 0.0, "%g" % n2[34])
    t("the card is still %d constants" % YARN_NPROPS,
      len(n2) == YARN_NPROPS, "%d" % len(n2))
    t("nothing else on the yarn card moved",
      all(abs(x - y) < 1e-12 for i, (x, y) in enumerate(zip(nb, n2))
          if i not in (31, 32, 33)))

    # A negative micro-card Gf would be read by KABAND as the MACRO card's
    # inelastic convention (Ch.4 4.6.1).  It must be refused here.
    a = _A()
    a.g1t = -1.0
    try:
        retune(_fake_deck(), a)
        t("a negative yarn Gf is refused", False)
    except ValueError:
        t("a negative yarn Gf is refused", True)

    # ------------------------------------------------------------------
    # The guide is a transcription of the constants above.  a1-0005 found
    # it holding dmax 0.99 and eta 0.02 -- the pre-retune values -- with
    # nothing in the repository able to notice.  Transcriptions drift; the
    # fix is not to be careful, it is to check.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guide = os.path.join(root, "verification", "CALIBRATION_GUIDE.md")
    if os.path.exists(guide):
        g = open(guide, encoding="utf-8").read()
        t("CALIBRATION_GUIDE quotes the live dmax %g" % D_DMAX,
          ("**%g**" % D_DMAX) in g or ("dmax = %g" % D_DMAX) in g)
        t("CALIBRATION_GUIDE quotes the live eta %g" % D_ETA,
          ("**%g**" % D_ETA) in g)
        t("the guide says which file is authoritative",
          "retune_deck.py" in g and "D_DMAX" in g and "D_ETA" in g)
        t("the guide no longer tells anyone to keep dmax at 0.99",
          "dmax=0.99:" not in g)
        t("dmax and eta are declared knobs there, not 'fixed'",
          g.count("선언된 knob") >= 4)
    else:
        t("CALIBRATION_GUIDE.md present", False, guide)

    print("\n%d passed, %d failed" % (ok[0], bad[0]))
    return 0 if bad[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser(
        description="Retune an assembled ZHANG2022 RVE deck (mesh untouched).")
    ap.add_argument("deck", nargs="?", help="assembled .inp to retune")
    ap.add_argument("-o", "--out", help="output .inp (default <deck>_M1FIX.inp)")
    ap.add_argument("--dmax", type=float, default=D_DMAX,
                    help="damage cap for matrix and yarn (default %g)" % D_DMAX)
    ap.add_argument("--eta", type=float, default=D_ETA,
                    help="viscous regularisation (default %g)" % D_ETA)
    ap.add_argument("--djump", type=float, default=D_DJUMP,
                    help="max damage jump before the UMAT cuts back "
                         "(default %g). Do NOT tighten this below ~0.08: "
                         "0.03 was tried and produced a 15-hour crawl." % D_DJUMP)
    ap.add_argument("--inc", type=int, default=D_INC,
                    help="increment budget per step (default %d). 10000 let a "
                         "crawling job burn 15 h before giving up." % D_INC)
    ap.add_argument("--stabilize", type=float, default=D_STABILIZE,
                    help="*Static stabilize factor, 0 disables (default %g)"
                         % D_STABILIZE)
    ap.add_argument("--allsdtol", type=float, default=D_ALLSDTOL,
                    help="adaptive stabilization energy tolerance (default %g)"
                         % D_ALLSDTOL)
    ap.add_argument("--dispctrl", type=float, default=D_DISPCTRL,
                    help="displacement-correction tolerance (default %g)"
                         % D_DISPCTRL)
    ap.add_argument("--mininc", type=float, default=D_MININC,
                    help="minimum time increment (default %g)" % D_MININC)
    ap.add_argument("--zero", type=float, default=D_ZERO,
                    help="stress-free temperature on *Expansion, zero= "
                         "(default %g). THIS IS PHYSICS, not numerics." % D_ZERO)
    ap.add_argument("--hsmo", type=float, default=D_HSMO,
                    help="half-width (in units of Xt) of the tanh blend that "
                         "replaces the hard sign(I1) switch in the matrix. "
                         "0 = published step (default). REQUIRES the V3_0 "
                         "UMAT: it lengthens the matrix card to 25 slots, "
                         "which V1_0 rejects.")
    ap.add_argument("--i-r", dest="i_r", type=int, default=D_IR,
                    help="I_R, iteration at which the log-rate divergence "
                         "check starts (default %d)" % D_IR)
    ap.add_argument("--i-a", dest="i_a", type=int, default=D_IA,
                    help="I_A, cutbacks allowed per increment (default %d)"
                         % D_IA)
    ap.add_argument("--free-shear", dest="shearlock", action="store_false",
                    default=D_SHEARLOCK,
                    help="leave eps_xy/eps_xz/eps_yz free instead of "
                         "prescribing them to zero. The M3 runs showed the "
                         "free shear drivers go singular once damage "
                         "localises (pivot RATIO 2.6e+10), so the default is "
                         "to lock them. Use this to reproduce the M3 decks or "
                         "to measure the shear response deliberately.")
    ap.add_argument("--g1t", type=float, default=D_G1T,
                    help="yarn longitudinal TENSILE fracture energy, N/mm. "
                         "The deck carries 12.5, a DEV input taken from Ge "
                         "refs/[24] Table 3 which is carbon/PHENOLIC. At 12.5 "
                         "the crack-band exponent is A = 0.239, 8.4x gentler "
                         "than the fixed default, which is why M5 T1000 never "
                         "peaked. A = 2.0 needs 2.664. See "
                         "verification/m6_calibration_plan.py.")
    ap.add_argument("--g1c", type=float, default=D_G1C,
                    help="yarn longitudinal COMPRESSIVE fracture energy, N/mm "
                         "(deck: 12.5, same provenance as --g1t).")
    ap.add_argument("--gtt", type=float, default=D_GTT,
                    help="yarn TRANSVERSE tensile fracture energy, N/mm. The "
                         "deck carries 0, which switches the crack band OFF "
                         "for the mode the cooldown drives. Shi refs/[31] "
                         "measured 0.107 on 2D plain weave C/SiC and it is "
                         "admissible on this mesh (limit 1.482 mm vs CELENT "
                         "0.0845 mm).")
    ap.add_argument("--gtc", type=float, default=D_GTC,
                    help="yarn TRANSVERSE compressive fracture energy, N/mm "
                         "(deck: 0). NO measurement exists for a CMC and the "
                         "re-search of 2026-08-03 confirmed the absence, so "
                         "changing this is a sensitivity case, not a fix "
                         "(Ch.4 4.9-6a).")
    ap.add_argument("--ftol", type=float, default=D_FTOL,
                    help="force residual ratio Rn^alpha (default %g; Abaqus "
                         "default is %g). The traction-free macro drivers "
                         "cannot meet %g, and their residual is a macro "
                         "stress error of <0.01 MPa, so the stock value is "
                         "the wrong scale for this model."
                         % (D_FTOL, ABAQUS_DEFAULT_FTOL, ABAQUS_DEFAULT_FTOL))
    ap.add_argument("--matrix-e", dest="matrix_e", type=float,
                    default=D_MATRIX_E,
                    help="matrix E [MPa]. Omit to keep the card's 350000. "
                         "213110 applies the 0.6089 porosity knockdown "
                         "(data/properties/porosity_stiffness.py). This is a "
                         "MISSING PHYSICAL FEATURE, not a knob.")
    ap.add_argument("--yarn-xt", dest="yarn_xt", type=float, default=D_YARN_XT,
                    help="yarn axial tensile strength [MPa]. Omit to keep the "
                         "card's 2835, which is Vf x a STRAND figure. The "
                         "in-situ band from refs/[08] is 475 / 581 / 694 at "
                         "23 / 500 / 1000 C "
                         "(data/properties/insitu_yarn_strength.py).")
    ap.add_argument("--check", action="store_true",
                    help="run the static self-test and exit")
    a = ap.parse_args()

    if a.check:
        sys.exit(check())
    if not a.deck:
        ap.error("give a deck to retune, or --check")

    with open(a.deck) as f:
        text = f.read()
    out, case, nsec = retune(text, a)
    dest = a.out or (os.path.splitext(a.deck)[0] + "_M1FIX.inp")
    with open(dest, "w") as f:
        f.write(out)
    print("%s -> %s" % (a.deck, dest))
    print("  case      test=%d C, heat=%s, eps_xx=%.6f"
          % (case["test"], case["heat"], case["eps"]))
    print("  sections  %d *Solid Section lines carried over" % nsec)
    print("  cards     dmax=%g  eta=%g  djump=%g" % (a.dmax, a.eta, a.djump))
    print("  steps     stabilize=%s  min inc=%g  disp tol=%g  I_R=%d  I_A=%d"
          % (a.stabilize or "off", a.mininc, a.dispctrl, a.i_r, a.i_a))
    print("  drivers   shear lock=%s  force tol=%g%s"
          % ("eps_xy=eps_xz=eps_yz=0" if a.shearlock else "ALL FREE",
             a.ftol,
             "" if abs(a.ftol - ABAQUS_DEFAULT_FTOL) > 1e-12
             else " (Abaqus default -- no force control emitted)"))
    if a.shearlock:
        print("            CHECK THIS: run driver_audit.py on the odb and "
              "confirm the\n            macro shear stress is <1 %% of "
              "sigma_xx, or the lock is not free.")
    print("  zero      %g degC" % a.zero)
    if any(v is not None for v in (a.matrix_e, a.yarn_xt, a.gtt, a.gtc)):
        print("  M6 cards  matrix E=%s  yarn Xt=%s  Gtt=%s  Gtc=%s"
              % tuple("unchanged" if v is None else "%g" % v
                      for v in (a.matrix_e, a.yarn_xt, a.gtt, a.gtc)))
        print("            ** THIS DECK IS NO LONGER ZHANG'S CARD. **  M1-M5")
        print("            reproduced Zhang 2022 verbatim, so their 1.64x was")
        print("            a property of HIS parameter set.  Here the card is")
        print("            re-sourced from primary constituent data, so Zhang")
        print("            Table 3 becomes an INDEPENDENT VALIDATION TARGET,")
        print("            not a reproduction target.  Say so in the thesis.")
    # The crack band is where a lowered E bites: g0 = X^2/(2E) grows, so the
    # largest element the softening branch can survive shrinks.  Print it every
    # time rather than only on request -- a silent brittle clamp is exactly the
    # kind of thing that reaches a thesis figure unnoticed.
    print("  crack band (mesh CELENT max %.4f mm)" % MESH_CELENT_MAX)
    for mode, x, e, gf, le, ok in crack_band_rows(a):
        if le is None:
            print("    %-28s Gf=0        DISABLED -- mode is NOT mesh "
                  "objective" % mode)
        else:
            print("    %-28s Gf=%-7.4g le_max=%.4f mm  %s"
                  % (mode, gf, le,
                     "OK (%.1fx)" % (le / MESH_CELENT_MAX) if ok
                     else "** VIOLATED -- elements clamp to brittle, "
                          "check ATEFF **"))
    if a.hsmo > 0.0:
        print("  hsmo      %g  -> matrix card is 25 slots; RUN THIS WITH "
              "user=UMAT_CSIC_THERMSHOCK_V3_0.for" % a.hsmo)


if __name__ == "__main__":
    main()
