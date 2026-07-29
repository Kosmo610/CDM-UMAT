# -*- coding: utf-8 -*-
"""
extract_ss_curve.py   (run INSIDE Abaqus:  abaqus python extract_ss_curve.py <job.odb>)
=======================================================================================
Extracts the macroscopic tensile stress-strain curve of the C/SiC RVE from the
history output of the periodic-BC "ConstraintsDriver" dummy nodes, so it can be
compared directly with the paper's Table 3 / Figs. 11,13,15.

Periodic-BC convention in the ZHANG2022 .inp files (TexGen / Xia unified PBC):
    U (ConstraintsDriver0, dof 1)  = macroscopic normal strain  eps_xx   [-]
    RF(ConstraintsDriver0, dof 1)  = -sigma_xx * V_RVE                    [N.mm]
  => sigma_xx = -RF / V_RVE ,   with  V_RVE = Lx*Ly*Lz  (bounding box, filled cell).

The tension step is the last step whose name contains "Tension". This script writes
    <job>_ss.csv   with columns:  eps_xx[-] , sigma_xx[MPa] , frame_time
and prints the peak (ultimate) stress.

Usage:
    abaqus python extract_ss_curve.py Job-RT23.odb
    abaqus python extract_ss_curve.py Job-RT23.odb 2.9138   # optional explicit V_RVE
"""
from __future__ import print_function
import sys
import os
from odbAccess import openOdb

DRIVER = "CONSTRAINTSDRIVER0"    # node-set name (Abaqus upper-cases set names)
DOF = 0                          # 0 -> dof 1 (x)  in the history data tuples


def rve_volume(odb):
    """Bounding-box volume of the instance mesh (mm^3). Filled cell => material V."""
    inst = list(odb.rootAssembly.instances.values())[0]
    xs = [n.coordinates[0] for n in inst.nodes]
    ys = [n.coordinates[1] for n in inst.nodes]
    zs = [n.coordinates[2] for n in inst.nodes]
    Lx, Ly, Lz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    print("  RVE bounding box  Lx=%.5f  Ly=%.5f  Lz=%.5f mm" % (Lx, Ly, Lz))
    return Lx * Ly * Lz


def region_by_nodeset(odb, name):
    ra = odb.rootAssembly
    if name in ra.nodeSets.keys():
        return ra.nodeSets[name]
    # fall back: search instance-scoped sets
    for inst in ra.instances.values():
        if name in inst.nodeSets.keys():
            return inst.nodeSets[name]
    raise KeyError("node set %s not found (available: %s)"
                   % (name, list(ra.nodeSets.keys())))


def extract(odbpath, Vuser=None):
    odb = openOdb(odbpath, readOnly=True)
    V = Vuser if Vuser else rve_volume(odb)
    print("  V_RVE = %.6f mm^3" % V)

    step_name = None
    for s in odb.steps.keys():
        if "TENSION" in s.upper():
            step_name = s
    if step_name is None:
        # A job that aborted during the cooldown or the reheat has no tension
        # step at all.  Falling back to the last step silently would turn a
        # thermal ramp into a fake stress-strain curve -- this happened with
        # ZHANG2022_c26k_T500/T1000 on 2026-07-28.  Refuse instead.
        sys.exit("  NO STEP NAMED 'Tension' IN THIS ODB.\n"
                 "  steps present: %s\n"
                 "  The job stopped before it reached the tension step, so\n"
                 "  there is no stress-strain curve to extract.  Use\n"
                 "  'abaqus python damage_census.py %s' to see how far it got."
                 % (list(odb.steps.keys()), odbpath))
    print("  tension step: %s" % step_name)
    step = odb.steps[step_name]
    if len(step.frames) < 2:
        print("  WARNING: only %d frame(s) in the tension step -- the job "
              "died at the very start." % len(step.frames))

    reg = region_by_nodeset(odb, DRIVER)
    hr = None
    for key, hp in step.historyRegions.items():
        # history region tied to the driver node
        if DRIVER.split("CONSTRAINTS")[-1] in key.upper() or DRIVER in key.upper():
            hr = hp
    if hr is None:
        # match by node label of the driver set
        lbl = reg.nodes[0][0].label if hasattr(reg.nodes[0], "__len__") else reg.nodes[0].label
        for key, hp in step.historyRegions.items():
            if str(lbl) in key:
                hr = hp
    if hr is None:
        raise RuntimeError("history region for %s not found; keys=%s"
                           % (DRIVER, list(step.historyRegions.keys())))

    u_key = [k for k in hr.historyOutputs.keys() if k.upper().startswith("U")][DOF]
    rf_key = [k for k in hr.historyOutputs.keys() if k.upper().startswith("RF")][DOF]
    Udata = hr.historyOutputs[u_key].data
    Rdata = hr.historyOutputs[rf_key].data

    # *Boundary values are TOTAL, not incremental, so the tension step ramps
    # the driver from wherever the thermal steps left it up to the prescribed
    # value.  Measured on ZHANG2022_c26k_RT23: the driver sits at U1 =
    # -3.216428e-3 at the end of the cooldown (the RVE has shrunk) with
    # RF1 = 0, and the tension step ramps from there.  Reporting the raw U as
    # the strain would put the whole curve at negative strain and make the
    # reported failure strain meaningless.  Zero it on the first frame of the
    # tension step, which is the unloaded as-cooled state -- exactly the
    # reference an experiment uses.
    eps0 = Udata[0][1]
    if abs(eps0) > 1.0e-9:
        print("  strain zeroed on the as-cooled state: eps_offset = %+.6e "
              "(%.4f %%)" % (eps0, eps0 * 100.0))

    rows = []
    for (t, u), (t2, rf) in zip(Udata, Rdata):
        eps = u - eps0
        sig = -rf / V
        rows.append((eps, sig, t, u))
    # align sign so that a tensile test reads positive
    peak = max(rows, key=lambda r: abs(r[1]))
    if peak[1] < 0:
        rows = [(e, -s, t, u) for (e, s, t, u) in rows]

    out = os.path.splitext(odbpath)[0] + "_ss.csv"
    with open(out, "w") as f:
        f.write("eps_xx,sigma_xx_MPa,time,U1_raw\n")
        for e, s, t, u in rows:
            f.write("%.8e,%.8e,%.6f,%.8e\n" % (e, s, t, u))
    ult = max(rows, key=lambda r: r[1])
    print("  wrote %s  (%d points)" % (out, len(rows)))
    print("  applied strain range: %.4f %% to %.4f %%"
          % (rows[0][0] * 100.0, rows[-1][0] * 100.0))
    if len(rows) > 1 and abs(rows[1][0]) > 1e-12:
        print("  initial modulus  E = %.1f GPa"
              % (rows[1][1] / rows[1][0] / 1000.0))
    print("  ULTIMATE STRESS = %.2f MPa  at eps_xx = %.4f %%"
          % (ult[1], ult[0] * 100.0))
    if ult is rows[-1]:
        print("  !! the peak is the LAST point -- the curve is still rising, "
              "so this is NOT the ultimate strength, only how far the job got.")
    odb.close()
    return out, ult[1]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    Vuser = float(sys.argv[2]) if len(sys.argv) > 2 else None
    extract(sys.argv[1], Vuser)
