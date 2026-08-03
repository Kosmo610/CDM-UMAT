#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_cband.py   (ordinary python3 + matplotlib, NOT abaqus python)
==================================================================
Plot the three crack-band bars on one axis from the CSV that
postprocess/patch_report.py writes.

    python3 plot_cband.py cband_curves.csv

If crack-band regularisation works the three curves overlie, even though the
softening factor A differs by 27x between the coarsest and finest mesh
(15.500 / 1.590 / 0.569).  Without it the post-peak area would fall by 4x
from N=5 to N=20.
"""
from __future__ import print_function

import csv
import os
import sys
from collections import OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

A_BY_JOB = {"CBAND_N5": 15.500, "CBAND_N10": 1.590, "CBAND_N20": 0.569}
H_BY_JOB = {"CBAND_N5": 0.200, "CBAND_N10": 0.100, "CBAND_N20": 0.050}


def main(argv):
    path = argv[0] if argv else "cband_curves.csv"
    if not os.path.exists(path):
        sys.exit("no such file: %s  (run patch_report.py first)" % path)

    series = OrderedDict()
    with open(path) as f:
        for row in csv.DictReader(f):
            job = os.path.splitext(row["job"])[0]
            series.setdefault(job, ([], []))
            series[job][0].append(float(row["delta_mm"]) * 1000.0)   # um
            series[job][1].append(float(row["force_N"]))

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    for job, (d, f) in sorted(series.items(),
                              key=lambda kv: -H_BY_JOB.get(kv[0], 0)):
        h = H_BY_JOB.get(job)
        A = A_BY_JOB.get(job)
        lab = job
        if h is not None:
            lab += "   h = %.3f mm" % h
        if A is not None:
            lab += ",  A = %.3f" % A
        ax.plot(d, f, lw=1.8, label=lab)

    ax.set_xlabel(u"end displacement  δ  [µm]")
    ax.set_ylabel("reaction force  F  [N]")
    ax.set_title("Crack-band mesh objectivity\n"
                 "same bar, element size varied 4x, softening factor 27x")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    out = "cband_objectivity.png"
    fig.savefig(out, dpi=160)
    print("wrote %s" % out)
    print("the three curves should overlie; if they separate, the crack-band\n"
          "regularisation is not doing its job and every homogenised strength\n"
          "in Ch.4 becomes mesh dependent")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
