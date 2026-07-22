#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_fullmodel.py
===================
Shows, at a single material point, what the V2_0 full model (Ge 2018 physics
enabled) changes versus the V1_0 verified baseline:

  * yarn longitudinal tension : V1_0 pure exponential (Eq.17)  vs
                                V2_0 mixed linear-exponential (Eq.18) -> fibre
                                bridging / pull-out tail.
  * matrix tension            : V1_0 elastic-brittle (plasticity off) vs
                                V2_0 elastic-plastic-damage -> residual strain
                                ('pseudo-ductility', Zhang 2022 / Ge 2018).

These are the two mechanisms the paper actually uses that V1_0 left switched off.
Run:  python3 verify_fullmodel.py   ->  figures/fullmodel_vs_baseline.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from verify_constitutive import (yarn_point, matrix_point, uniaxial_stress,
                                 YARN, MATRIX, FIGDIR)

Vf = 0.79194

# V2_0 full-model yarn card (mirrors abaqus/*_V2_0.inp)
YARN_V2 = list(YARN)
YARN_V2[10] = Vf * 3580.0     # Xt = 2835 (micromechanics)
YARN_V2[11] = Vf * 2470.0     # Xc = 1956
YARN_V2[31] = 12.5            # G1t (Ge Table 3)
YARN_V2[32] = 12.5            # G1c
YARN_V2[35] = 700.0           # X_PO  (Eq.18 on)
YARN_V2[36] = 3.0             # rF
YARN_V2[37] = 8000.0          # K1

# V2_0 full-model matrix card
MATRIX_V2 = list(MATRIX)
MATRIX_V2[16] = 250.0         # SY0 (plasticity on)
MATRIX_V2[17] = 100000.0      # HISO


def curve(fn, P, d, em, n, nsv):
    h = uniaxial_stress(fn, P, d, em, n, nsv)
    return np.array(h["eps"]) * 100.0, np.array(h["sig"])


def main():
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))

    # yarn longitudinal tension
    e1, s1 = curve(yarn_point, YARN, 0, 0.020, 500, 16)          # V1_0 Eq.17
    e2, s2 = curve(yarn_point, YARN_V2, 0, 0.020, 500, 16)       # V2_0 Eq.18
    ax[0].plot(e1, s1, "b-", lw=2, label="V1_0: exponential (Eq.17), Xt=1200")
    ax[0].plot(e2, s2, "r-", lw=2, label="V2_0: mixed law (Eq.18), Xt=2835")
    ax[0].set_title("Yarn longitudinal tension\nEq.18 adds the fibre-bridging / pull-out tail")
    ax[0].set_xlabel("strain (%)"); ax[0].set_ylabel("stress (MPa)")
    ax[0].grid(alpha=0.3); ax[0].legend(fontsize=8, loc="upper right")

    # matrix tension
    e3, s3 = curve(matrix_point, MATRIX, 0, 0.004, 500, 20)      # V1_0 brittle
    e4, s4 = curve(matrix_point, MATRIX_V2, 0, 0.004, 500, 20)   # V2_0 plastic
    ax[1].plot(e3, s3, "b-", lw=2, label="V1_0: elastic-brittle (plasticity off)")
    ax[1].plot(e4, s4, "r-", lw=2, label="V2_0: elastic-plastic-damage (SY0=250)")
    ax[1].set_title("Matrix tension\nplasticity adds residual strain (pseudo-ductility)")
    ax[1].set_xlabel("strain (%)"); ax[1].set_ylabel("stress (MPa)")
    ax[1].grid(alpha=0.3); ax[1].legend(fontsize=8, loc="lower right")

    fig.suptitle("V2_0 full model (Ge 2018 physics ON) vs V1_0 baseline "
                 "- single material point", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    p = os.path.join(FIGDIR, "fullmodel_vs_baseline.png")
    fig.savefig(p, dpi=130)
    print("wrote", p)


if __name__ == "__main__":
    main()
