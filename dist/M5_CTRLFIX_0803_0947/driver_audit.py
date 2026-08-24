# -*- coding: utf-8 -*-
"""
driver_audit.py   (run INSIDE Abaqus:  abaqus python driver_audit.py <job.odb>)
==============================================================================
Reads ALL SIX periodic-BC ConstraintsDriver dummy nodes, not just the loaded
one, plus the stabilisation-energy ratio, for every step in the odb.

Why this exists
---------------
On the M3 runs (2026-07-30) three of the four jobs stopped with the residual
sitting on a driver that carries NO prescribed boundary condition -- e_z, e_xy,
e_xz.  Those drivers enforce the traction-free macro stress components, so their
residual IS the macro stress error:

    R_driver = sigma_component * V_RVE          [N.mm]

Abaqus judges that residual against 0.5 % of the global average nodal force,
which on this model is ~0.15 N.mm.  That demands the traction-free stresses
vanish to ~1.4e-4 MPa -- five orders below the axial stress being measured.
The jobs were not failing on physics, they were failing on a tolerance applied
at the wrong scale.

Before changing the deck we have to know whether the shear drivers can simply
be prescribed to zero.  For a balanced orthogonal 2-D weave loaded along a
principal material axis they should be zero by symmetry, but the TexGen mesh is
not exactly symmetric, so it has to be measured rather than assumed.  That is
what this script answers:

    * if |eps_shear| stays negligible against eps_xx, prescribing them costs
      nothing and removes three near-singular degrees of freedom
    * if it does not, prescribing them is a real modelling choice that has to
      be declared in the thesis

It also prints ALLSD/ALLIE so the 5 % viscous-stabilisation limit is checked in
the same pass instead of through the CAE GUI.

Usage:
    abaqus python driver_audit.py M3_c26k_RT23.odb
    abaqus python driver_audit.py M3_c26k_RT23.odb 5.390     # explicit V_RVE
"""
from __future__ import print_function

import os
import sys

from odbAccess import openOdb

# ConstraintsDriver<i> -> macroscopic strain component it drives.  This mapping
# is written in the deck header by assemble_inp.py and must not be reordered.
DRIVERS = [("CONSTRAINTSDRIVER0", "eps_xx"),
           ("CONSTRAINTSDRIVER1", "eps_yy"),
           ("CONSTRAINTSDRIVER2", "eps_zz"),
           ("CONSTRAINTSDRIVER3", "eps_xy"),
           ("CONSTRAINTSDRIVER4", "eps_xz"),
           ("CONSTRAINTSDRIVER5", "eps_yz")]

# Ratio of ALLSD to ALLIE above which the viscous stabilisation is judged to
# have carried a non-physical share of the load.  Same number as allsdtol in
# the deck.
ALLSD_LIMIT = 0.05


def rve_volume(odb):
    inst = list(odb.rootAssembly.instances.values())[0]
    xs = [n.coordinates[0] for n in inst.nodes]
    ys = [n.coordinates[1] for n in inst.nodes]
    zs = [n.coordinates[2] for n in inst.nodes]
    Lx, Ly, Lz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    print("  RVE bounding box  Lx=%.5f  Ly=%.5f  Lz=%.5f mm" % (Lx, Ly, Lz))
    return Lx * Ly * Lz


def node_label(odb, setname):
    ra = odb.rootAssembly
    st = ra.nodeSets.get(setname) if hasattr(ra.nodeSets, "get") else None
    if st is None and setname in ra.nodeSets.keys():
        st = ra.nodeSets[setname]
    if st is None:
        for inst in ra.instances.values():
            if setname in inst.nodeSets.keys():
                st = inst.nodeSets[setname]
                break
    if st is None:
        return None
    nodes = st.nodes
    # nodeSets on the assembly give a tuple-per-instance; instance sets do not
    first = nodes[0]
    if hasattr(first, "__len__"):
        first = first[0]
    return first.label


def history_for(step, label, setname):
    """Find the historyRegion belonging to the driver node."""
    for key, hp in step.historyRegions.items():
        if setname in key.upper().replace(" ", ""):
            return hp
    if label is not None:
        for key, hp in step.historyRegions.items():
            # region keys look like 'Node ASSEMBLY.5681'
            tail = key.replace(".", " ").split()
            if str(label) in tail:
                return hp
    return None


def series(hr, prefix):
    if hr is None:
        return []
    keys = [k for k in hr.historyOutputs.keys() if k.upper().startswith(prefix)]
    if not keys:
        return []
    return list(hr.historyOutputs[keys[0]].data)


def energies(step):
    """Return (ALLIE, ALLSD) final values, or (None, None)."""
    out = {}
    for key, hp in step.historyRegions.items():
        for name, ho in hp.historyOutputs.items():
            if name.upper() in ("ALLIE", "ALLSD", "ALLWK", "ALLPD") and ho.data:
                out[name.upper()] = ho.data[-1][1]
    return out


def audit(odbpath, Vuser=None):
    odb = openOdb(odbpath, readOnly=True)
    V = Vuser if Vuser else rve_volume(odb)
    print("  V_RVE = %.6f mm^3" % V)

    rows = []
    verdict_ok = True
    for step_name in odb.steps.keys():
        step = odb.steps[step_name]
        print("\n  === STEP %s   (%d frames, last step time %.4f)"
              % (step_name, len(step.frames),
                 step.frames[-1].frameValue if step.frames else 0.0))

        # ---- energies -------------------------------------------------
        en = energies(step)
        if "ALLIE" in en and "ALLSD" in en and abs(en["ALLIE"]) > 0.0:
            ratio = en["ALLSD"] / en["ALLIE"]
            flag = "OK" if abs(ratio) < ALLSD_LIMIT else "** OVER 5 % **"
            if abs(ratio) >= ALLSD_LIMIT:
                verdict_ok = False
            print("      ALLIE=%.6g  ALLSD=%.6g   ALLSD/ALLIE = %.3f %%   %s"
                  % (en["ALLIE"], en["ALLSD"], 100.0 * ratio, flag))
        else:
            print("      ALLIE/ALLSD not in history output for this step")

        # ---- drivers --------------------------------------------------
        axial = None
        print("      %-10s %14s %14s %14s"
              % ("component", "final strain", "final sigma", "|sigma| / |sig_xx|"))
        comp_rows = []
        for setname, comp in DRIVERS:
            lbl = node_label(odb, setname)
            hr = history_for(step, lbl, setname)
            U = series(hr, "U")
            RF = series(hr, "RF")
            if not U or not RF:
                print("      %-10s   (no history output in this step)" % comp)
                continue
            eps = U[-1][1]
            sig = -RF[-1][1] / V
            comp_rows.append((comp, eps, sig))
            if comp == "eps_xx":
                axial = sig
        for comp, eps, sig in comp_rows:
            rel = ("%13.4f %%" % (100.0 * abs(sig) / abs(axial))
                   if axial not in (None, 0.0) else "            --")
            print("      %-10s %14.6e %11.4f MPa %s" % (comp, eps, sig, rel))
            rows.append((os.path.basename(odbpath), step_name, comp, eps, sig))

        # ---- the question this script exists to answer ----------------
        shear = [(c, e, s) for c, e, s in comp_rows if c in
                 ("eps_xy", "eps_xz", "eps_yz")]
        if shear and axial not in (None, 0.0):
            worst = max(shear, key=lambda r: abs(r[2]))
            pct = 100.0 * abs(worst[2]) / abs(axial)
            if pct < 1.0:
                print("      -> largest macro shear stress is %s at %.4f %% of "
                      "sigma_xx:\n         prescribing the three shear drivers "
                      "to zero is physically free here." % (worst[0], pct))
            else:
                verdict_ok = False
                print("      -> largest macro shear stress is %s at %.4f %% of "
                      "sigma_xx:\n         NOT negligible -- constraining the "
                      "shear drivers would be a real\n         modelling "
                      "change and must be declared." % (worst[0], pct))

    out = os.path.splitext(odbpath)[0] + "_drivers.csv"
    with open(out, "w") as f:
        f.write("odb,step,component,final_strain,final_stress_MPa\n")
        for r in rows:
            f.write("%s,%s,%s,%.8e,%.8e\n" % r)
    print("\n  wrote %s  (%d rows)" % (out, len(rows)))
    print("  VERDICT: %s" % ("all checks clean" if verdict_ok
                             else "see the flagged lines above"))
    odb.close()
    return 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    V = float(argv[1]) if len(argv) > 1 else None
    return audit(argv[0], V)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
