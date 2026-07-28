#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_compare.py   (ordinary Python 3 + matplotlib, run on any machine)
======================================================================
Overlays the RVE macroscopic tensile stress-strain curves extracted at 23/500/
1000 C (the *_ss.csv files written by extract_ss_curve.py) and compares their
ultimate strengths with the paper's Table 3 - reproducing the paper's temperature
comparison (Figs. 11/13/15 and Table 3) in a single figure.

Usage:
    python3 plot_compare.py RT23_ss.csv T500_ss.csv T1000_ss.csv
    # or with no args it looks for ./{RT23,T500,T1000}_ss.csv
Out:
    ss_curves_by_temperature.png   and a printed strength-vs-paper table.
"""
import os
import sys
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Paper Table 3 (simulation) targets and experiment bands.
PAPER = {23: (128.45, 116.17, 8.78),
         500: (179.42, 160.19, 14.83),
         1000: (199.15, 173.28, 12.94)}
COLORS = {23: "#1f77b4", 500: "#d62728", 1000: "#2ca02c"}


def load_csv(path):
    eps, sig = [], []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            eps.append(float(row["eps_xx"]) * 100.0)   # %
            sig.append(float(row["sigma_xx_MPa"]))
    return eps, sig


def temp_of(path):
    b = os.path.basename(path).upper()
    for T, tag in [(1000, "1000"), (500, "500"), (23, "RT23"), (23, "_23")]:
        if tag in b:
            return T
    return None


def main(argv):
    files = argv or [f for f in ("RT23_ss.csv", "T500_ss.csv", "T1000_ss.csv")
                     if os.path.exists(f)]
    if not files:
        print("No *_ss.csv files given/found. Run extract_ss_curve.py first "
              "(inside Abaqus) to produce them, then re-run this script.")
        print("This script only PLOTS already-extracted curves; it does not "
              "invent data.")
        return

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    print("%-8s %12s %12s %12s" % ("T[C]", "sim(this)", "paper-sim", "experiment"))
    print("-" * 48)
    sims = {}
    for path in files:
        T = temp_of(path)
        eps, sig = load_csv(path)
        ult = max(sig)
        sims[T] = ult
        c = COLORS.get(T, "k")
        ax[0].plot(eps, sig, "-", color=c, lw=2, label="%d C (this model)" % T)
        if T in PAPER:
            ps, ex, sd = PAPER[T]
            ax[0].axhline(ps, color=c, ls=":", lw=1, alpha=0.7)
            print("%-8d %12.2f %12.2f  %6.2f+-%.2f"
                  % (T, ult, ps, ex, sd))
    ax[0].set_xlabel("macroscopic strain eps_xx (%)")
    ax[0].set_ylabel("macroscopic stress sigma_xx (MPa)")
    ax[0].set_title("RVE tensile response by temperature\n"
                    "(dotted = paper Table 3 simulation strength)")
    ax[0].grid(alpha=0.3)
    ax[0].legend(loc="lower right", fontsize=9)

    # strength comparison bar
    Ts = sorted(sims.keys())
    x = range(len(Ts))
    w = 0.27
    ax[1].bar([i - w for i in x], [sims[T] for T in Ts], width=w,
              color="0.3", label="this model")
    ax[1].bar([i for i in x], [PAPER[T][0] for T in Ts if T in PAPER], width=w,
              color="crimson", alpha=0.8, label="paper simulation")
    ax[1].bar([i + w for i in x], [PAPER[T][1] for T in Ts if T in PAPER], width=w,
              color="0.7", label="experiment",
              yerr=[PAPER[T][2] for T in Ts if T in PAPER], capsize=4)
    ax[1].set_xticks(list(x))
    ax[1].set_xticklabels(["%d C" % T for T in Ts])
    ax[1].set_ylabel("ultimate tensile strength (MPa)")
    ax[1].set_title("Ultimate strength vs paper")
    ax[1].grid(alpha=0.3, axis="y")
    ax[1].legend(fontsize=9)

    fig.suptitle("C/SiC RVE: model vs Zhang et al. 2022 (Table 3)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out = "ss_curves_by_temperature.png"
    fig.savefig(out, dpi=130)
    print("\nwrote", out)


if __name__ == "__main__":
    main(sys.argv[1:])
