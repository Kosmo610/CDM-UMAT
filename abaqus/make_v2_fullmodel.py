#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_v2_fullmodel.py
====================
Generates the *full-model* V2_0 Abaqus input decks from the verified V1_0 decks by
swapping only the two `*User Material` cards (mesh, steps, PBC untouched). V2_0
turns ON the parts of the Ge-2018 model the paper actually uses but V1_0 left off:

  * matrix elastic-PLASTIC damage  (Eqs. 6-10) : SY0, HISO enabled
  * yarn longitudinal mixed law    (Eq. 18)    : X_PO, rF, K1 enabled
  * yarn longitudinal crack-band energies      : G1t, G1c (Ge Table 3)

and replaces the placeholder yarn longitudinal strengths with micromechanics
values (T300 rule of mixtures at the verified yarn Vf=0.792):
  Xf,1t = Vf*3580 = 2835 MPa,  Xf,1c = Vf*2470 = 1956 MPa.

Everything here is a *documented starting point* for calibration, NOT a value the
paper published. See verification/CALIBRATION_GUIDE.md for the tuning procedure.

Run:  python3 make_v2_fullmodel.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- V1_0 matrix data block (exact text) -> V2_0 (plasticity ON) ------------
MAT_OLD = """*User Material, constants=22
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
0.0, 0.0, 1.15, 0.75, 0.50, 30.0"""
MAT_NEW = """*User Material, constants=22
2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.99
0.99, 0.02, 0.10, 3.0, 0.25, 1.0, 0.031, 0.031
250.0, 100000.0, 1.15, 0.75, 0.50, 30.0"""

# ---- V1_0 yarn data block (exact text) -> V2_0 (Eq.18 + crack-band + micromech) -
YARN_OLD = """*User Material, constants=38
1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.247516386, 0.395813581, 26431.515264
26431.515264, 15876.667974, 1200.0, 1500.0, 80.0, 350.0, 120.0, 120.0
100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02
0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 0.0
0.0, 0.0, 0.0, 0.0, 0.0, 0.0"""
YARN_NEW = """*User Material, constants=38
1.0, 254967.228042, 44321.737572, 44321.737572, 0.247516386, 0.247516386, 0.395813581, 26431.515264
26431.515264, 15876.667974, 2835.0, 1956.0, 80.0, 350.0, 120.0, 120.0
100.0, 2.0, 2.0, 2.0, 2.0, 0.99, 0.99, 0.02
0.10, 3.0, 0.25, 1.0, 1.15, 0.75, 0.50, 12.5
12.5, 0.0, 0.0, 700.0, 3.0, 8000.0"""

# ---- comment lines updated so the deck stays self-documenting ---------------
COMMENT_OLD = """** Stage-1 values: Xt=Xc=310 (Zhang Table 2), crack band on,
** plasticity off (no SiC hardening data given in the paper)."""
COMMENT_NEW = """** V2_0 FULL MODEL (Ge 2018 + Zhang 2022): Xt=Xc=310 (Zhang Table 2),
** crack band on; matrix PLASTICITY ON (SY0=250, HISO=100000 -- calibration
** starting values for the paper's 'pseudo-ductility', NOT paper-published)."""

COMMENT2_OLD = """** Stage-1: fixed A=2.0, strengths carried over from V2_3 pending
** Stage-2 calibration (the paper does not list yarn strengths)."""
COMMENT2_NEW = """** V2_0 FULL MODEL: longitudinal Xt=2835, Xc=1956 (= Vf*3580, Vf*2470,
** T300 rule of mixtures at verified yarn Vf=0.792); longitudinal crack-band
** G1t=G1c=12.5 N/mm (Ge Table 3); Eq.18 mixed law ON (X_PO=700, rF=3, K1=8000).
** Transverse Yt=80,Yc=350 and shears S=120/120/100 are calibration knobs."""

SRC = {"ZHANG2022_RT23_V1_0.inp":  "ZHANG2022_RT23_V2_0.inp",
       "ZHANG2022_T500_V1_0.inp":  "ZHANG2022_T500_V2_0.inp",
       "ZHANG2022_T1000_V1_0.inp": "ZHANG2022_T1000_V2_0.inp"}


def transform(text):
    for old, new in [(MAT_OLD, MAT_NEW), (YARN_OLD, YARN_NEW),
                     (COMMENT_OLD, COMMENT_NEW), (COMMENT2_OLD, COMMENT2_NEW)]:
        if old not in text:
            raise RuntimeError("expected block not found:\n" + old[:80])
        if text.count(old) != 1:
            raise RuntimeError("block not unique: " + old[:60])
        text = text.replace(old, new)
    return text


def main():
    for src, dst in SRC.items():
        p_in = os.path.join(HERE, src)
        p_out = os.path.join(HERE, dst)
        with open(p_in) as f:
            txt = f.read()
        with open(p_out, "w") as f:
            f.write(transform(txt))
        print("wrote", dst)
    print("Done. V2_0 decks are the full model; V1_0 decks are the verified baseline.")


if __name__ == "__main__":
    main()
