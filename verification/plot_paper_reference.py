#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_paper_reference.py
=======================
Renders the paper's *own* quantitative results (Table 3) as the reference target
that the Abaqus RVE runs must reproduce, so the user has a like-for-like baseline
to overlay their extracted stress-strain curves against.

Table 3, Zhang et al. 2022, Ceramics International 48:3109-3124 - ultimate
tensile strength of the 2D plain-weave C/SiC composite:

    Temperature        23 C       500 C      1000 C
    Experiment      116.17+-8.78 160.19+-14.83 173.28+-12.94   MPa
    Simulation      128.45       179.42       199.15           MPa

Run:  python3 plot_paper_reference.py
Out:  figures/paper_table3_reference.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(HERE, "figures")
os.makedirs(FIGDIR, exist_ok=True)

T = np.array([23, 500, 1000])
exp = np.array([116.17, 160.19, 173.28])
exp_sd = np.array([8.78, 14.83, 12.94])
sim = np.array([128.45, 179.42, 199.15])
# Applied macroscopic strain limits in the three .inp tension steps (for reference):
applied_eps = np.array([0.0015, 0.0032, 0.0048]) * 100.0   # %

fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))

# (left) ultimate strength vs temperature: experiment vs paper simulation
ax[0].errorbar(T, exp, yerr=exp_sd, fmt="o-", color="k", capsize=5,
               label="experiment (Table 3)", lw=1.8, ms=7)
ax[0].plot(T, sim, "s--", color="crimson", label="paper simulation (Table 3)",
           lw=1.8, ms=7)
for x, y in zip(T, sim):
    ax[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                   xytext=(6, 6), color="crimson", fontsize=9)
for x, y in zip(T, exp):
    ax[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                   xytext=(6, -14), color="k", fontsize=9)
ax[0].set_xlabel("temperature (C)")
ax[0].set_ylabel("ultimate tensile strength (MPa)")
ax[0].set_title("Paper target: ultimate strength vs temperature")
ax[0].set_xticks(T)
ax[0].grid(alpha=0.3)
ax[0].legend(loc="lower right", fontsize=9)

# (right) relative strengthening vs 23 C (paper's headline result)
rel_exp = (exp / exp[0] - 1.0) * 100.0
rel_sim = (sim / sim[0] - 1.0) * 100.0
w = 60
ax[1].bar(T - w/2, rel_exp, width=w, color="0.4", label="experiment")
ax[1].bar(T + w/2, rel_sim, width=w, color="crimson", alpha=0.8, label="simulation")
for x, y in zip(T - w/2, rel_exp):
    ax[1].annotate(f"{y:.1f}%", (x, y), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8)
for x, y in zip(T + w/2, rel_sim):
    ax[1].annotate(f"{y:.1f}%", (x, y), textcoords="offset points",
                   xytext=(0, 3), ha="center", fontsize=8)
ax[1].set_xlabel("temperature (C)")
ax[1].set_ylabel("strengthening vs 23 C (%)")
ax[1].set_title("Paper headline: higher strength at higher temperature")
ax[1].set_xticks(T)
ax[1].grid(alpha=0.3, axis="y")
ax[1].legend(loc="upper left", fontsize=9)

fig.suptitle("Zhang et al. 2022 - reference results the RVE model must reproduce "
             "(Table 3)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
p = os.path.join(FIGDIR, "paper_table3_reference.png")
fig.savefig(p, dpi=130)
print("wrote", p)
print("\nReference targets (paper simulation):")
for t, s, e in zip(T, sim, applied_eps):
    print(f"  {t:5d} C : ultimate ~ {s:7.2f} MPa   (tension step applies eps_xx up to {e:.2f} %)")
