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
  djump 0.10 -> 0.03   the UMAT's own pre-emptive PNEWDT cutback now fires four
                       times earlier, BEFORE a large damage jump is committed.
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
MATRIX_SLOTS = dict(dmax_t=8, dmax_c=9, eta=10, djump=11, key=22)
YARN_SLOTS = dict(dmax_1=22, dmax_t=23, eta=24, djump=25)
MATRIX_NPROPS, YARN_NPROPS = 22, 38
MATRIX_KEY = 30.0                      # PROPS(22) guard checked by the UMAT

# --------------------------------------------------------------------------
# defaults -- the retuned values
# --------------------------------------------------------------------------
D_DMAX = 0.90
D_ETA = 0.05
D_DJUMP = 0.03
D_STABILIZE = 2.0e-4
D_ALLSDTOL = 0.05
D_DISPCTRL = 1.0
D_MININC = 1.0e-8
D_ZERO = 1050.0
D_IR = 16                              # log-rate divergence check
D_IA = 8                               # cutbacks per increment


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
    out = [kw]
    for i in range(0, len(nums), per_line):
        chunk = nums[i:i + per_line]
        out.append(", ".join(_fmt(x) for x in chunk))
    return "\n".join(out)


def _fmt(x):
    if x == int(x) and abs(x) < 1e7:
        return "%.1f" % x
    return repr(x)


def retune_matrix(dmax, eta, djump):
    kw, n = card_numbers(MATRIX_USERMAT["v2"])
    if len(n) != MATRIX_NPROPS:
        raise ValueError("matrix card has %d constants, expected %d"
                         % (len(n), MATRIX_NPROPS))
    n[MATRIX_SLOTS["dmax_t"] - 1] = dmax
    n[MATRIX_SLOTS["dmax_c"] - 1] = dmax
    n[MATRIX_SLOTS["eta"] - 1] = eta
    n[MATRIX_SLOTS["djump"] - 1] = djump
    if n[MATRIX_SLOTS["key"] - 1] != MATRIX_KEY:
        raise ValueError("matrix card key PROPS(22) is %r, the UMAT rejects "
                         "anything but %r" % (n[21], MATRIX_KEY))
    return emit_card(kw, n)


def retune_yarn(dmax, eta, djump):
    kw, n = card_numbers(YARN_USERMAT["v2"])
    if len(n) != YARN_NPROPS:
        raise ValueError("yarn card has %d constants, expected %d"
                         % (len(n), YARN_NPROPS))
    n[YARN_SLOTS["dmax_1"] - 1] = dmax
    n[YARN_SLOTS["dmax_t"] - 1] = dmax
    n[YARN_SLOTS["eta"] - 1] = eta
    n[YARN_SLOTS["djump"] - 1] = djump
    return emit_card(kw, n)


def materials(a):
    L = ["*Material, Name=SIC_MATRIX_DAMAGE",
         MATRIX_DEPVAR,
         retune_matrix(a.dmax, a.eta, a.djump),
         "*Expansion, zero=%g." % a.zero,
         "4.5e-06,",
         "*Material, Name=CSIC_YARN_DAMAGE",
         YARN_DEPVAR,
         retune_yarn(a.dmax, a.eta, a.djump),
         "*Expansion, type=ORTHO, zero=%g." % a.zero,
         "1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06"]
    return "\n".join(L)


def controls(a):
    return ("*Controls, parameters=time incrementation\n"
            " 12, %d, , 40, , , , %d, , ,\n"
            "*Controls, parameters=field, field=displacement\n"
            " , %g\n"
            "*Controls, parameters=line search\n"
            "5\n" % (a.i_r, a.i_a, a.dispctrl))


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


def steps(a, case):
    S = []
    S.append("*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=10000")
    S.append("Uniform cooling from %g degC to 23 degC with progressive damage"
             % a.zero)
    S.append(static_line(a, 0.001, a.mininc))
    S.append(controls(a) + "*Temperature\nAllNodes, 23.")
    S.append(OUTPUT)
    S.append("*End Step")
    if case["heat"] is not None:
        T = case["heat"]
        S.append("*Step, Name=Heating_to_%dC, nlgeom=NO, inc=10000" % T)
        S.append("Uniform reheating from 23 degC to %d degC before tension" % T)
        S.append(static_line(a, 0.001, a.mininc))
        S.append(controls(a) + "*Temperature\nAllNodes, %d." % T)
        S.append(OUTPUT)
        S.append("*End Step")
    T = case["test"]
    S.append("*Step, Name=Tension_at_%dC, nlgeom=NO, inc=10000" % T)
    S.append("Uniaxial x tension at %d degC via ConstraintsDriver0" % T)
    S.append(static_line(a, 0.0005, a.mininc))
    S.append(controls(a) + "*Boundary\nConstraintsDriver0, 1, 1, %.6f"
             % case["eps"])
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
    t("retuned matrix djump = 0.03", nm[10] == D_DJUMP)
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
    t("retuned yarn djump = 0.03", ny[24] == D_DJUMP)
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
    t("displacement control relaxed to 1", out.count(" , 1\n") == 3)
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

    # a deck without the anchor must raise, not produce garbage
    try:
        retune(_fake_deck().replace(MAT_ANCHOR, "*Material, Name=SOMETHING"),
               _A())
        t("missing material anchor is rejected", False)
    except ValueError:
        t("missing material anchor is rejected", True)

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
                         "(default %g)" % D_DJUMP)
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
    ap.add_argument("--i-r", dest="i_r", type=int, default=D_IR,
                    help="I_R, iteration at which the log-rate divergence "
                         "check starts (default %d)" % D_IR)
    ap.add_argument("--i-a", dest="i_a", type=int, default=D_IA,
                    help="I_A, cutbacks allowed per increment (default %d)"
                         % D_IA)
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
    print("  zero      %g degC" % a.zero)


if __name__ == "__main__":
    main()
