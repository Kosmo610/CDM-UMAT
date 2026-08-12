"""E(N) from the interleaved elastic probes of a macro thermal-shock job.

RUN WITH:  abaqus python extract_probe.py <job>.odb
           (odbAccess needed; plain python only for --selftest)

WHAT IT READS
-------------
The mechanical decks from make_macro_thermalshock.py interleave elastic
probe steps (Probe_N0, Probe_N20, ...) between the cycling blocks.  The
probe prescribes an ABSOLUTE face position, U1 = PROBE_STRAIN * Lx -- and
that is the defect this reader has to survive.  The face it clamps has
been carried away by thermal expansion (order 1e-3 mm), so the clamp
drags it back through a strain thousands of times the nominal 1e-6, and
the absolute reaction measures BLOCKED THERMAL DISPLACEMENT, not
stiffness.  The first real run (2026-08-10) read E = 3.9e7 MPa -- 376x
any physical modulus -- exactly this way.

The stiffness is still in the odb, as a DIFFERENCE.  Between the last
frame of the previous step (face free, RF = 0, position u0) and the end
of the probe (face at u1, reaction R1), the material was loaded by
eps = (u1-u0)/Lx and answered with R1-R0.  So:

    E(N) = (R1 - R0) * Lx / (A * (u1 - u0))

which is exact for the linear probe whatever u0 was, and identical at
every probe of a job since the thermal state repeats block to block.

Each probe row also records SDV17 (d_cyc) and SDV29 (TWMAX).  Note TWMAX
resets per STEP (STIME <= 0 at each step start), so at a probe it simply
reads the probe's own temperature -- ~T_hi confirms the block ended hot.

Writes <job>_EN.csv:
    N, E_MPa, E_over_E0, eps_probe, sigma_abs_MPa, dcyc_mean, dcyc_max,
    twmax_prev_block
(sigma_abs is the old contaminated observable, kept as its own column --
it is the blocked thermal stress, and its drift over N is real data.)

Also writes <job>_stepdiag.csv: per-step NT min/mean/max at the last
frame.  One look answers whether the thermal cycles after the first one
actually cycled -- the frozen-damage question the 2026-08-10 run raised
(d_cyc identical from Quench_1 to the end, and CJ5/CJ1 = 5.000 exactly).

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


def find_xhi(odb):
    asm = odb.rootAssembly
    if "XHI" in asm.nodeSets.keys():
        return asm.nodeSets["XHI"]
    for inst in asm.instances.values():
        if "XHI" in inst.nodeSets.keys():
            return inst.nodeSets["XHI"]
    return None


def face_state(frame, nset):
    """(sum RF1, mean U1) over the XHI face at one frame."""
    rf = sum(v.data[0] for v in
             frame.fieldOutputs["RF"].getSubset(region=nset).values)
    uv = [v.data[0] for v in
          frame.fieldOutputs["U"].getSubset(region=nset).values]
    return rf, (sum(uv) / len(uv) if uv else 0.0)


def nt_field(frame):
    """Nodal temperature values, whichever key this odb used."""
    for key in ("NT11", "NT"):
        if key in frame.fieldOutputs.keys():
            return [v.data for v in frame.fieldOutputs[key].values]
    return []


def probe_rows(odb):
    """One row per probe step, in order.

    E comes from the DIFFERENCE between the previous step's end (face
    free) and the probe's end (face clamped) -- see the module docstring.
    The previous step always exists: Probe_N0 follows the cooldown (TRS
    B/C) or is preceded by nothing only in a TRS A deck, where u0 = 0 and
    the initial frame of the same step serves.
    """
    rows = []
    nset = find_xhi(odb)
    names = list(odb.steps.keys())
    for i, sname in enumerate(names):
        if not sname.startswith("Probe_N"):
            continue
        n = float(sname.split("Probe_N", 1)[1])
        step = odb.steps[sname]
        frame = step.frames[-1]
        rf1, u1 = face_state(frame, nset)
        if i > 0:
            prev = odb.steps[names[i - 1]]
            rf0, u0 = face_state(prev.frames[-1], nset)
        else:
            rf0, u0 = face_state(step.frames[0], nset)
        d17 = sdv_values(frame, 17, "DCYC")
        d29 = sdv_values(frame, 29, "TWMAX")
        rows.append(dict(N=n, rf1=rf1, rf0=rf0, u1=u1, u0=u0,
                         dcyc_mean=sum(d17) / max(1, len(d17)),
                         dcyc_max=max(d17) if d17 else 0.0,
                         twmax=max(d29) if d29 else 0.0))
    rows.sort(key=lambda r: r["N"])
    return rows


def step_diagnosis(odb):
    """Per-step NT range at the last frame -- did the cycles really cycle?

    A healthy job alternates: every Quench ends cold, every Reheat ends
    hot.  If the swing dies after cycle 1, the *Temperature file= mapping
    stopped re-reading, and any cycle-damage number after that point is
    the first cycle's, frozen.
    """
    out = []
    for sname in odb.steps.keys():
        fr = odb.steps[sname].frames[-1] if len(odb.steps[sname].frames)             else None
        if fr is None:
            out.append(dict(step=sname, nframes=0, nt_min="", nt_mean="",
                            nt_max=""))
            continue
        nts = nt_field(fr)
        if nts:
            out.append(dict(step=sname, nframes=len(odb.steps[sname].frames),
                            nt_min=min(nts), nt_mean=sum(nts) / len(nts),
                            nt_max=max(nts)))
        else:
            out.append(dict(step=sname, nframes=len(odb.steps[sname].frames),
                            nt_min="", nt_mean="", nt_max=""))
    return out


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


def stiffness(rows, area, lx):
    """Fill E and E/E0 from the face DIFFERENCES.

    E = (R1-R0)*Lx / (A*(u1-u0)).  Immune to where thermal expansion had
    parked the face, which is what poisoned the absolute version.  The
    actually-imposed probe strain and the blocked absolute stress are
    kept as columns -- the first shows how far the deck's "1e-6" claim
    really was from the truth, the second is the mean-stress observable.
    """
    out = []
    e0 = None
    for r in rows:
        du = r["u1"] - r["u0"]
        eps = du / lx if lx else 0.0
        e = ((r["rf1"] - r["rf0"]) / (area * eps)) if eps else float("nan")
        if e0 is None:
            e0 = e
        out.append(dict(N=r["N"], E_MPa=e,
                        E_over_E0=(e / e0 if e0 else float("nan")),
                        eps_probe=eps,
                        sigma_abs_MPa=r["rf1"] / area,
                        dcyc_mean=r["dcyc_mean"], dcyc_max=r["dcyc_max"],
                        twmax_prev_block=r["twmax"]))
    return out


def write_csv(path, rows):
    with open(path, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["N", "E_MPa", "E_over_E0",
                                           "eps_probe", "sigma_abs_MPa",
                                           "dcyc_mean", "dcyc_max",
                                           "twmax_prev_block"])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_stepdiag(path, rows):
    with open(path, "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["step", "nframes", "nt_min",
                                           "nt_mean", "nt_max"])
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
    # ZHANG2013 gauge: Lx=12.5, A = 6*3 = 18 mm^2, card E1 = 105 GPa.
    # The scenario that broke the absolute version on 2026-08-10: thermal
    # expansion has parked the free face at u0 = -6.15e-3 mm, the probe
    # clamps it to +1.25e-5.  The DIFFERENCE still reads the modulus; the
    # absolute reaction reads blocked thermal stress hundreds of times
    # the probe signal.
    lx, area, E = 12.5, 6.0 * 3.0, 105000.0
    u0, u1 = -6.15e-3, PROBE_STRAIN * 12.5
    rf1 = E * area * (u1 - u0) / lx          # linear response to the drag
    base = dict(dcyc_mean=0.0, dcyc_max=0.0, twmax=900.0)
    r0 = dict(N=0.0, rf1=rf1, rf0=0.0, u1=u1, u0=u0, **base)
    r1 = dict(N=20.0, rf1=0.55 * rf1, rf0=0.0, u1=u1, u0=u0, **base)
    rows = stiffness([r0, r1], area, lx)
    ck("E(0) recovers the card modulus despite the thermal offset",
       abs(rows[0]["E_MPa"] - E) < 1e-6, "%.1f" % rows[0]["E_MPa"])
    ck("the absolute version would have been wrong by ~500x here",
       rows[0]["sigma_abs_MPa"] / (E * PROBE_STRAIN) > 400,
       "sigma_abs/probe signal = %.0fx"
       % (rows[0]["sigma_abs_MPa"] / (E * PROBE_STRAIN)))
    ck("the really-imposed strain is recorded, not the nominal 1e-6",
       abs(rows[0]["eps_probe"] - (u1 - u0) / lx) < 1e-18
       and rows[0]["eps_probe"] > 100 * PROBE_STRAIN,
       "eps_probe = %.3e" % rows[0]["eps_probe"])
    ck("E/E0 starts at exactly 1", rows[0]["E_over_E0"] == 1.0)
    ck("a 45 % stiffness loss reads as 0.55",
       abs(rows[1]["E_over_E0"] - 0.55) < 1e-12)
    ck("a zero-displacement probe yields nan, not a divide crash",
       stiffness([dict(N=0.0, rf1=1.0, rf0=0.0, u1=0.5, u0=0.5, **base)],
                 area, lx)[0]["E_MPa"] != stiffness(
           [dict(N=0.0, rf1=1.0, rf0=0.0, u1=0.5, u0=0.5, **base)],
           area, lx)[0]["E_MPa"])
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
       set(rows[0]) == {"N", "E_MPa", "E_over_E0", "eps_probe",
                        "sigma_abs_MPa", "dcyc_mean", "dcyc_max",
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
    lx = coords[:, 0].max() - coords[:, 0].min()
    ly = coords[:, 1].max() - coords[:, 1].min()
    lz = coords[:, 2].max() - coords[:, 2].min()
    rows = stiffness(probe_rows(odb), ly * lz, lx)
    out = path.replace(".odb", "") + "_EN.csv"
    write_csv(out, rows)
    diag = step_diagnosis(odb)
    dout = path.replace(".odb", "") + "_stepdiag.csv"
    write_stepdiag(dout, diag)
    print("wrote %s  (%d probes, gauge %.4g x %.4g x %.4g mm)"
          % (out, len(rows), lx, ly, lz))
    for r in rows:
        print("  N=%-6g E=%.1f MPa  E/E0=%.5f  eps_probe=%.3e  "
              "sigma_abs=%.2f MPa  dcyc max %.3e"
              % (r["N"], r["E_MPa"], r["E_over_E0"], r["eps_probe"],
                 r["sigma_abs_MPa"], r["dcyc_max"]))
    print("wrote %s  (per-step NT -- the did-it-really-cycle audit)" % dout)
    hot = [d for d in diag if str(d["step"]).startswith("Reheat")]
    cold = [d for d in diag if str(d["step"]).startswith("Quench")]
    if hot and cold and hot[0]["nt_mean"] != "" and cold[0]["nt_mean"] != "":
        print("  Quench-end NT mean: %s"
              % " ".join("%.0f" % d["nt_mean"] for d in cold))
        print("  Reheat-end NT mean: %s"
              % " ".join("%.0f" % d["nt_mean"] for d in hot))
        print("  (healthy = alternating cold/hot all the way; a swing that "
              "dies after cycle 1 = the *Temperature mapping stopped)")
    odb.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
