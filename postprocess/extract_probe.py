"""E(N) from the interleaved elastic probes of a macro thermal-shock job.

RUN WITH:  abaqus python extract_probe.py <job>.odb
           (odbAccess needed; plain python only for --selftest)

WHAT IT READS
-------------
The mechanical decks from make_macro_thermalshock.py interleave elastic
probe steps (Probe_N0, Probe_N20, ...) between the cycling blocks.  Each
probe prescribes U1 = PROBE_STRAIN * Lx on the XHI face with the cycle
rate at zero, so the reaction it draws is the CURRENT secant stiffness
with nothing else moving:

    E(N) = (sum RF1 on XHI) / (Ly * Lz) / PROBE_STRAIN

The same frame's field output carries SDV17 (d_cyc) and SDV29 (TWMAX),
so each probe row also records how much cycle damage the block deposited
and the audit that the block really sat at its peak temperature.

Writes <job>_EN.csv:
    N, E_MPa, E_over_E0, dcyc_mean, dcyc_max, twmax_prev_block

The CSV is what postprocess/compare_cyclejump.py consumes -- one file per
job, jobs never read each other's odb.

WHY THE PROBE AND NOT THE CYCLE STEPS
-------------------------------------
A cycling step's stiffness is entangled with the thermal strain of the
moment; the probe is isothermal, tiny, and rate-free, so its slope is the
material's and nothing else's.  This is design decision 2 of the deck
generator, and this file is the consumer that makes it pay.
"""
from __future__ import print_function

import csv
import sys

#: Must match the generator; asserted rather than imported because this
#: script runs inside abaqus python, where the repo may not be on path.
PROBE_STRAIN = 1.0e-6

try:
    from odbAccess import openOdb
except ImportError:
    openOdb = None


def probe_rows(odb):
    """One row per probe step, in order."""
    rows = []
    xs = None
    asm = odb.rootAssembly
    for sname in odb.steps.keys():
        if not sname.startswith("Probe_N"):
            continue
        n = float(sname.split("Probe_N", 1)[1])
        step = odb.steps[sname]
        frame = step.frames[-1]
        # reaction on the XHI node set, component 1
        rf = frame.fieldOutputs["RF"]
        nset = None
        for key in ("XHI",):
            if key in asm.nodeSets.keys():
                nset = asm.nodeSets[key]
        if nset is None:
            for inst in asm.instances.values():
                if "XHI" in inst.nodeSets.keys():
                    nset = inst.nodeSets["XHI"]
        total = sum(v.data[0] for v in rf.getSubset(region=nset).values)
        d17 = sdv_values(frame, 17, "DCYC")
        d29 = sdv_values(frame, 29, "TWMAX")
        rows.append(dict(N=n, rf=total,
                         dcyc_mean=sum(d17) / max(1, len(d17)),
                         dcyc_max=max(d17) if d17 else 0.0,
                         twmax=max(d29) if d29 else 0.0))
    rows.sort(key=lambda r: r["N"])
    return rows


class _Frame(object):
    """Minimal stand-in for an odb frame: all resolve_sdv needs is keys()."""

    def __init__(self, fo):
        self.fieldOutputs = fo


def resolve_sdv(frame, slot, name):
    """The odb key for one state variable, whatever the deck called it.

    A bare "SDV17" is what Abaqus writes when the *Depvar entry is UNNAMED.
    Name it -- "17, DCYC, DCYC" -- and the field becomes "SDV_DCYC" and the
    old key stops existing.  The macro card started naming all 29 slots on
    2026-08-10, which turned this lookup into a KeyError on a job that had
    otherwise run to completion.  Name first, number second, so decks from
    either side of that change both read.
    """
    keys = frame.fieldOutputs.keys()
    for cand in ("SDV_%s" % name, "SDV%d" % slot, "SDV_%d" % slot,
                 "SDV%02d" % slot):
        if cand in keys:
            return cand
    return None


def sdv_values(frame, slot, name):
    """[values] for one state variable, or [] if the deck never wrote it."""
    var = resolve_sdv(frame, slot, name)
    if var is None:
        return []
    return [v.data for v in frame.fieldOutputs[var].values]


def stiffness(rows, area):
    """Fill E and E/E0 from the raw reactions."""
    out = []
    e0 = None
    for r in rows:
        e = r["rf"] / area / PROBE_STRAIN
        if e0 is None:
            e0 = e
        out.append(dict(N=r["N"], E_MPa=e,
                        E_over_E0=(e / e0 if e0 else float("nan")),
                        dcyc_mean=r["dcyc_mean"], dcyc_max=r["dcyc_max"],
                        twmax_prev_block=r["twmax"]))
    return out


def write_csv(path, rows):
    with open(path, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["N", "E_MPa", "E_over_E0",
                                           "dcyc_mean", "dcyc_max",
                                           "twmax_prev_block"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def selftest():
    """The arithmetic, testable without an odb (extract_kbar.py pattern)."""
    npass = [0]

    def ck(name, cond, detail=""):
        npass[0] += cond
        print("   [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                                ("   " + detail) if detail else ""))
        if not cond:
            raise SystemExit(1)

    print("extract_probe.py --selftest")
    # A ZHANG2013 gauge section: Ly*Lz = 6*3 = 18 mm^2, probe strain 1e-6.
    # An undamaged card with E1 = 105 GPa must give RF = E*A*eps.
    area = 6.0 * 3.0
    rf0 = 105000.0 * area * PROBE_STRAIN
    rows = stiffness([dict(N=0.0, rf=rf0, dcyc_mean=0.0, dcyc_max=0.0,
                           twmax=900.0),
                      dict(N=20.0, rf=0.55 * rf0, dcyc_mean=0.4,
                           dcyc_max=0.6, twmax=900.0)], area)
    ck("E(0) recovers the card modulus",
       abs(rows[0]["E_MPa"] - 105000.0) < 1e-6, "%.1f" % rows[0]["E_MPa"])
    ck("E/E0 starts at exactly 1", rows[0]["E_over_E0"] == 1.0)
    ck("a 45 % stiffness loss reads as 0.55",
       abs(rows[1]["E_over_E0"] - 0.55) < 1e-12)
    # ---- the named/unnamed *Depvar lookup (2026-08-10 KeyError) --------
    class _F(object):
        def __init__(self, keys):
            self._k = list(keys)

        class _O(object):
            pass

        def keys(self):
            return self._k
    named = _F(["RF", "SDV_DCYC", "SDV_TWMAX"])
    plain = _F(["RF", "SDV17", "SDV29"])
    ck("a NAMED *Depvar resolves by name",
       resolve_sdv(_Frame(named), 17, "DCYC") == "SDV_DCYC")
    ck("an UNNAMED one still resolves by slot number",
       resolve_sdv(_Frame(plain), 17, "DCYC") == "SDV17")
    ck("the same holds for TWMAX, the severity-window audit",
       resolve_sdv(_Frame(named), 29, "TWMAX") == "SDV_TWMAX"
       and resolve_sdv(_Frame(plain), 29, "TWMAX") == "SDV29")
    ck("a variable the deck never wrote returns None, not a KeyError",
       resolve_sdv(_Frame(_F(["RF"])), 17, "DCYC") is None)
    ck("and sdv_values turns that into an empty list",
       sdv_values(_Frame(_F(["RF"])), 17, "DCYC") == [])

    # PROBE_STRAIN is duplicated from the generator (this file must run
    # inside abaqus python, off-repo).  Duplicates drift; when the
    # generator is reachable, the duplicate is checked against it.
    import os
    gen = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "abaqus", "make_macro_thermalshock.py")
    if os.path.exists(gen):
        src = open(gen).read()
        import re as _re
        m = _re.search(r"^PROBE_STRAIN = ([0-9.e-]+)", src, _re.M)
        ck("PROBE_STRAIN matches the deck generator's",
           m is not None and float(m.group(1)) == PROBE_STRAIN,
           m.group(1) if m else "not found")
    else:
        ck("PROBE_STRAIN carries the documented value (generator off-path)",
           PROBE_STRAIN == 1.0e-6)
    ck("rows are the comparator's whole input, no odb re-reads",
       set(rows[0]) == {"N", "E_MPa", "E_over_E0", "dcyc_mean", "dcyc_max",
                        "twmax_prev_block"})
    print("   %d passed" % npass[0])
    return 0


def main(argv):
    if "--selftest" in argv or "--check" in argv:
        return selftest()
    if openOdb is None:
        print("odbAccess unavailable -- run me as:  abaqus python "
              "extract_probe.py <job>.odb   (or --selftest)")
        return 2
    path = argv[0]
    odb = openOdb(path, readOnly=True)
    # gauge cross-section from the assembly's bounding box
    import numpy as _np  # abaqus python ships numpy
    coords = []
    for inst in odb.rootAssembly.instances.values():
        coords.extend(n.coordinates for n in inst.nodes)
    coords = _np.array(coords)
    ly = coords[:, 1].max() - coords[:, 1].min()
    lz = coords[:, 2].max() - coords[:, 2].min()
    rows = stiffness(probe_rows(odb), ly * lz)
    out = path.replace(".odb", "") + "_EN.csv"
    write_csv(out, rows)
    print("wrote %s  (%d probes, cross-section %.4g x %.4g mm)"
          % (out, len(rows), ly, lz))
    for r in rows:
        print("  N=%-6g E=%.1f MPa  E/E0=%.4f  dcyc mean/max %.4f/%.4f"
              % (r["N"], r["E_MPa"], r["E_over_E0"],
                 r["dcyc_mean"], r["dcyc_max"]))
    odb.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
