#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cband_damage.py   (run INSIDE Abaqus:  abaqus python cband_damage.py <odb>...)
==============================================================================
Did the crack band LOCALISE, and how far had each bar got when the pull ended?

Why this exists
---------------
patch_report.py compares the three bars' force-displacement curves and reports
a 34 % spread in dissipated energy.  That number cannot be interpreted on its
own, because integrating the curves only to the truncation point hides two
different things:

  * whether the damage localised into ONE row of elements, which is what the
    crack-band derivation assumes.  If it spreads over n rows the bar
    dissipates roughly n times the fracture energy, and the spread says
    nothing about the regularisation.
  * how far along its softening branch each bar actually got.  Integrating to
    a fixed end displacement compares bars that are at different stages.

Both are already in the odbs -- the bar decks write SDV in the field output --
so this needs no re-run.

What it prints
--------------
For each bar, at the last frame:

  rows damaged      how many element rows along the bar carry damage above the
                    threshold.  ONE is what the crack band assumes.
  d_max, d_mean     the damage in the localising row.  d_max at the card's cap
                    (0.90) means the band SATURATED and the bar has started to
                    re-harden on the 10 % residual stiffness -- past that point
                    the curve is no longer a softening branch at all.
  band width        rows x element size, mm.  This is the physical width the
                    energy was smeared over, and it is the quantity that must
                    be mesh independent for the regularisation to be working.

Reading the verdict
-------------------
  all three localise to one row, none saturated  -> the energy comparison in
                                                    patch_report.py is valid
  rows differ between meshes                     -> localisation failed; the
                                                    trigger slice is too weak
                                                    or the pull too fast
  d_max at the cap on some bars only             -> the bars are at different
                                                    stages; extend the pull
"""
from __future__ import print_function

import os
import sys

try:
    from odbAccess import openOdb
except ImportError:
    sys.exit("odbAccess not found -- run with 'abaqus python', not python.")

SDV_DAMAGE = 1             # DMT, matrix tensile damage (see MATRIX_DEPVAR)
SDV_ACTIVE = 5             # DMACT, stress-state-active matrix damage
DMAX_CARD = 0.90           # the cap on the matrix card
THRESH = 0.01              # "damaged" means above this
ROW_TOL = 1.0e-6           # mm, for grouping element centroids into rows


def rows_of(odb):
    """Map element label -> x of its centroid, and the element size."""
    inst = list(odb.rootAssembly.instances.values())[0]
    coord = dict((n.label, n.coordinates[0]) for n in inst.nodes)
    xs = {}
    for e in inst.elements:
        cx = sum(coord[l] for l in e.connectivity) / float(len(e.connectivity))
        xs[e.label] = cx
    uniq = sorted(set(round(v / ROW_TOL) * ROW_TOL for v in xs.values()))
    h = (uniq[1] - uniq[0]) if len(uniq) > 1 else float("nan")
    return xs, uniq, h


def resolve_sdv(fr, index):
    """Find the field output holding state variable `index`, or None.

    Abaqus is not consistent about how state variables land in an odb.  Most
    versions create one field output per variable named SDV1, SDV2, ...; some
    write a single "SDV" with components.  The 2026-08-03 run found neither
    under the name this script assumed, so instead of guessing a third time
    it now searches every plausible spelling and, failing that, says what the
    frame actually contains.
    """
    keys = list(fr.fieldOutputs.keys())
    for cand in ("SDV%d" % index, "SDV_%d" % index, "SDV%02d" % index):
        if cand in keys:
            return fr.fieldOutputs[cand], 0
    if "SDV" in keys:
        return fr.fieldOutputs["SDV"], index - 1
    return None, None


def last_damage(odb, index):
    """element label -> max state variable `index` over its integration
    points, at the last frame that actually carries field output."""
    step = odb.steps[list(odb.steps.keys())[-1]]
    fr = None
    for f in reversed(step.frames):
        if len(f.fieldOutputs.keys()):
            fr = f
            break
    if fr is None:
        return None, 0.0, ["<no frame carries field output>"]
    fo, comp = resolve_sdv(fr, index)
    if fo is None:
        return None, fr.frameValue, sorted(fr.fieldOutputs.keys())
    out = {}
    for v in fo.values:
        d = v.data
        d = d if not hasattr(d, "__len__") else d[comp]
        lab = v.elementLabel
        if lab is not None:
            out[lab] = max(out.get(lab, -1.0e30), d)
    return out, fr.frameValue, None


def report(path):
    odb = openOdb(path, readOnly=True)
    name = os.path.basename(path)
    xs, uniq, h = rows_of(odb)
    dmg, t, avail = last_damage(odb, SDV_DAMAGE)
    if dmg is None:
        print("  %-14s  state variable %d not found.  This frame carries:"
              % (name, SDV_DAMAGE))
        for k in (avail or []):
            print("      %s" % k)
        print("      steps: %s" % list(odb.steps.keys()))
        st = odb.steps[list(odb.steps.keys())[-1]]
        print("      frames in last step: %d" % len(st.frames))
        odb.close()
        return None

    per_row = {}
    for lab, d in dmg.items():
        key = round(xs[lab] / ROW_TOL) * ROW_TOL
        per_row.setdefault(key, []).append(d)
    hot = sorted((k, v) for k, v in per_row.items() if max(v) > THRESH)
    nrows = len(hot)
    if nrows:
        dmax = max(max(v) for _, v in hot)
        dmean = sum(sum(v) / len(v) for _, v in hot) / nrows
    else:
        dmax = dmean = 0.0
    sat = "YES" if dmax >= DMAX_CARD - 1.0e-6 else "no"
    print("  %-14s %8d %8.4f %8.4f %8.4f %10.4f %7s %8.3f"
          % (name, nrows, h, dmax, dmean, nrows * h, sat, t))
    odb.close()
    return dict(name=name, rows=nrows, h=h, dmax=dmax, width=nrows * h,
                saturated=(sat == "YES"))


def main(paths):
    print("=" * 78)
    print("CRACK-BAND LOCALISATION -- last frame of each bar")
    print("=" * 78)
    print("  %-14s %8s %8s %8s %8s %10s %7s %8s"
          % ("odb", "rows", "h [mm]", "d_max", "d_mean", "width[mm]",
             "sat?", "time"))
    print("  " + "-" * 74)
    res = [r for r in (report(p) for p in paths) if r]
    print("  " + "-" * 74)
    if not res:
        return 1

    print("\n  what this means")
    one = [r for r in res if r["rows"] == 1]
    if len(one) == len(res):
        print("    every bar localised into a single element row -- the")
        print("    crack-band assumption holds and the energy comparison in")
        print("    patch_report.py is meaningful.")
    else:
        print("    LOCALISATION DIFFERS BETWEEN MESHES: rows = %s."
              % ", ".join("%s:%d" % (r["name"].replace("CBAND_", "")
                                     .replace(".odb", ""), r["rows"])
                          for r in res))
        print("    A bar that damages n rows dissipates about n times the")
        print("    fracture energy, so the energy spread patch_report.py")
        print("    reports is NOT a statement about the regularisation.")
        w = [r["width"] for r in res]
        print("    smeared band width: %s  (spread %.0f %%)"
              % (", ".join("%.3f" % x for x in w),
                 (max(w) - min(w)) / (sum(w) / len(w)) * 100.0))

    sat = [r for r in res if r["saturated"]]
    if sat and len(sat) != len(res):
        print("\n    THE BARS ARE AT DIFFERENT STAGES: %s reached the damage"
              % ", ".join(r["name"].replace("CBAND_", "").replace(".odb", "")
                          for r in sat))
        print("    cap d_max = %.2f and have started re-hardening on the"
              % DMAX_CARD)
        print("    residual stiffness, while the others are still softening.")
        print("    Comparing areas at a common end displacement compares")
        print("    different things.  Extend the pull until all three cap.")
    elif len(sat) == len(res):
        print("\n    all three reached the cap -- the pull is long enough.")
    else:
        print("\n    no bar reached the cap; every curve is still softening,")
        print("    so no dissipated-energy comparison is possible yet.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
