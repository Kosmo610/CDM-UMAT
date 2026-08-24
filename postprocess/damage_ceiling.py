#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
damage_ceiling.py   (plain python3 -- reads a CSV, not an odb)
==============================================================
Judge the yarn/matrix damage cap dmax = 0.90.

    python3 damage_ceiling.py data/results/M6/LTH_M6_*_damage_map.csv

Ch.4 4.9-0a(4) marks every M6 strength as provisional because 42 of T500's
93 ranked worst points sit on the card's ceiling, and an element on the
ceiling keeps 10 % of its stiffness for ever instead of shedding to zero.
That is a statement that saturation EXISTS.  Quoting a strength needs three
further answers, and this file gives the ones a committed CSV can support:

  1. WHERE.  One localised band is a crack the model is resolving.  Points
     scattered over the whole cell are a card ceiling being hit everywhere,
     which is a different object and does not localise into a crack.

  2. WHEN.  Saturation AFTER the peak costs the peak nothing.  Saturation
     BEFORE it means the peak was reached with elements already forbidden to
     shed load, so the peak is partly an artefact of the ceiling.  The
     sharpest form of this question needs no increments at all: if a step
     that applies NO MECHANICAL LOAD already ends with elements at the cap,
     the tension step started from a saturated cell.

  3. HOW MUCH.  The Voigt bound: capped volume still carries (1 - dmax) of
     its undamaged stiffness, so the peak is inflated by at most
     volfrac_at_cap * (1 - dmax) of that phase's contribution.

WHAT THIS FILE CANNOT DO, AND SAYS SO
-------------------------------------
The ranked hotspot list in a damage map is TRUNCATED at 30 entries per step.
When fewer than 30 are capped the count is exact -- rank 31 would be lower
still.  When all 30 are capped the count is a LOWER BOUND and the real number
is unknown, which is exactly the case that matters.  Question 3 then needs
`volfrac_at_cap`, which older maps do not carry because the top volume bin
used to sit exactly on the cap and could never fire.  This file detects that
and prints the command that fixes it rather than quietly reporting zero.
"""
from __future__ import print_function

import csv
import glob
import math
import os
import sys

#: The command this file tells the user to run when a map predates
#: volfrac_at_cap.  It said "damage_map.py <job>.odb <job>.inp" until
#: 2026-08-18 -- damage_map.py takes ONE positional argument, so argparse
#: would have answered "unrecognized arguments" and the user would have been
#: stuck at a dead end printed by us.  A command we print has to be a command
#: that runs; the selftest below checks this string against damage_map.py's
#: real parser rather than trusting it.
RERUN_HINT = "abaqus python damage_map.py <job>.odb"

#: what damage_map.py ranks per step; a full list is a censored count
RANK_LIMIT = 30
#: the card ceiling and the tolerance the map itself uses
DMAX_CAP = 0.90
CAP_TOL = 1.0e-4
#: largest element edge in the RVE mesh [mm] -- celent_census.py
ELEMENT_MM = 0.0845
#: a cluster whose points sit within this many element edges of each other
#: is one feature; beyond it they are separate places in the cell
CLUSTER_EDGES = 2.0

CSV_HEADER = "kind,job,step,phase,value,unit,basis,verdict"


def read_map(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def job_of(path):
    base = os.path.basename(path)
    for suffix in ("_damage_map.csv", ".csv"):
        if base.endswith(suffix):
            return base[:-len(suffix)]
    return base


#: Phases whose ranked DAMG *is* a component, so a value at the cap is a cap
#: hit and a value above it is impossible.  Every other phase reports a
#: COMBINED magnitude -- a yarn's DY1 already merges DY1T and DY1C, so it can
#: read 0.976 with neither component at the 0.90 ceiling, and it reads exactly
#: 0.900 when one component is capped and the other is zero.  On those phases
#: a ranked value ABOVE the cap is genuinely indeterminate from the CSV, and
#: this file says so instead of counting it either way.
COMPONENT_PHASES = ("MATRIX",)


def is_component_phase(phase):
    return (phase or "").upper().startswith(COMPONENT_PHASES)


def hotspots(rows):
    return [r for r in rows
            if r.get("kind") == "hotspot" and r.get("value")
            and str(r.get("item", "")).startswith("rank")]


def at_cap(rows):
    """Ranked points that are certainly on the ceiling."""
    out = []
    for r in hotspots(rows):
        v = float(r["value"])
        if v < DMAX_CAP - CAP_TOL:
            continue
        if is_component_phase(r["phase"]) or abs(v - DMAX_CAP) <= CAP_TOL:
            out.append(r)
    return out


def indeterminate(rows):
    """Combined-magnitude points above the cap: cannot be judged from a CSV."""
    return [r for r in hotspots(rows)
            if not is_component_phase(r["phase"])
            and float(r["value"]) > DMAX_CAP + CAP_TOL]


def steps_in(rows):
    seen = []
    for r in rows:
        s = r.get("step") or ""
        if s and s not in seen:
            seen.append(s)
    return seen


def is_mechanical(step):
    """Does this step apply mechanical load?

    Names come from the deck generator: Manufacturing_Cooling and
    Heating_to_* are thermal, Tension_at_* pulls.  Anything unrecognised is
    treated as mechanical, because calling a loaded step thermal would turn
    the strongest finding this file can make into a false alarm.
    """
    s = step.lower()
    if s.startswith("tension") or "tens" in s:
        return True
    if "cool" in s or "heat" in s or "therm" in s:
        return False
    return True


def counted_or_bounded(n_capped, n_ranked):
    """Is the capped count exact, or censored by the ranking limit?"""
    if n_ranked >= RANK_LIMIT and n_capped >= n_ranked:
        return "LOWER BOUND", ("all %d ranked points are capped, so the real "
                               "count is unknown" % n_ranked)
    return "exact", ("%d of %d ranked; rank %d is below the cap"
                     % (n_capped, n_ranked, n_capped + 1))


def spread(points):
    """(bbox spans, median nearest-neighbour distance) over [(x,y,z)]."""
    if len(points) < 2:
        return None
    spans = [max(p[i] for p in points) - min(p[i] for p in points)
             for i in range(3)]
    nn = []
    for i, a in enumerate(points):
        nn.append(min(math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(3)))
                      for j, b in enumerate(points) if j != i))
    nn.sort()
    return spans, nn[len(nn) // 2]


def spatial_verdict(spans, cell_spans, nn_median):
    """One band, or the ceiling being hit all over the cell?

    Two independent readings have to agree before this says 'band'.  A
    cluster of points can span a small box AND be one element apart; only
    the first is evidence of localisation, and only the second says the
    points are contiguous rather than a scatter that happens to be near.
    """
    if spans is None:
        return "too few points", ""
    frac = [s / c if c > 0 else 0.0 for s, c in zip(spans, cell_spans)]
    inplane = max(frac[0], frac[1])
    near = nn_median <= CLUSTER_EDGES * ELEMENT_MM
    detail = ("spans %.0f/%.0f/%.0f %% of the cell in x/y/z, "
              "nearest neighbour %.4f mm = %.1f elements"
              % (100 * frac[0], 100 * frac[1], 100 * frac[2],
                 nn_median, nn_median / ELEMENT_MM))
    if inplane <= 0.35:
        return ("ONE BAND" if near else "one region, scattered"), detail
    return ("SCATTERED CLUSTERS" if near else "SCATTERED"), detail


def volfrac_rows(rows):
    """{(step, phase): fraction} from a map that carries volfrac_at_cap."""
    out = {}
    for r in rows:
        if r.get("item") == "volfrac_at_cap" and r.get("value"):
            out[(r["step"], r["phase"])] = float(r["value"])
    return out


def analyse(path):
    rows = read_map(path)
    job = job_of(path)
    out = []
    hs = hotspots(rows)
    cell = spread([(float(r["x"]), float(r["y"]), float(r["z"]))
                   for r in hs if r.get("x")])
    cell_spans = cell[0] if cell else (1.0, 1.0, 1.0)

    caps = at_cap(rows)
    unknown = indeterminate(rows)
    out.append(("summary", job, "", "ALL", len(caps), "points",
                "of %d ranked worst points across %d steps"
                % (len(hs), len(steps_in(rows))),
                "SATURATED" if caps else "no element certainly on the ceiling"))
    if unknown:
        out.append(("summary", job, "", "ALL", len(unknown), "points",
                    "combined-magnitude points above %.2f: DY1 merges two "
                    "components, so neither reaching the cap is possible and "
                    "one reaching it is possible" % DMAX_CAP,
                    "INDETERMINATE FROM THIS FILE"))

    # ---- 2. WHEN, in the sharpest form a per-step map can answer ---------
    pre_load = [s for s in steps_in(rows)
                if not is_mechanical(s) and
                any(r["step"] == s for r in caps)]
    for s in pre_load:
        n = sum(1 for r in caps if r["step"] == s)
        out.append(("timing", job, s, "ALL", n, "points",
                    "this step applies no mechanical load",
                    "CEILING REACHED BEFORE LOADING"))
    if not pre_load:
        out.append(("timing", job, "", "ALL", 0, "points",
                    "no unloaded step ends with an element at the cap",
                    "peak not pre-empted by the ceiling"))

    # ---- 1. WHERE, and 3. HOW MUCH, per step ----------------------------
    vf = volfrac_rows(rows)
    for s in steps_in(rows):
        here = [r for r in caps if r["step"] == s]
        ranked = [r for r in hs if r["step"] == s]
        if not here:
            continue
        kind, why = counted_or_bounded(len(here), len(ranked))
        out.append(("count", job, s, "ALL", len(here), "points", why, kind))
        for ph in sorted(set(r["phase"] for r in here)):
            n = sum(1 for r in here if r["phase"] == ph)
            modes = sorted(set(r["basis"] for r in here if r["phase"] == ph))
            out.append(("phase", job, s, ph, n, "points",
                        "; ".join(modes), "at the ceiling"))
        pts = [(float(r["x"]), float(r["y"]), float(r["z"]))
               for r in here if r.get("x")]
        sp = spread(pts)
        if sp:
            verdict, detail = spatial_verdict(sp[0], cell_spans, sp[1])
            out.append(("space", job, s, "ALL", "%.4f" % sp[1], "mm",
                        detail, verdict))
        got = [(k[1], v) for k, v in vf.items() if k[0] == s and v > 0.0]
        if got:
            for ph, f in sorted(got):
                out.append(("bound", job, s, ph, "%.6g" % (f * (1.0 - DMAX_CAP)),
                            "fraction of that phase's stress",
                            "Voigt bound = volfrac_at_cap %.6g * (1 - %.2f)"
                            % (f, DMAX_CAP), "upper bound"))
        else:
            out.append(("bound", job, s, "ALL", "", "",
                        "this map carries no volfrac_at_cap -- it predates "
                        "the fix, or no volume reached the cap",
                        "NOT COMPUTABLE FROM THIS FILE"))
    return out


def write_csv(rows, path):
    with open(path, "w") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER.split(","))
        for r in rows:
            w.writerow(list(r))
    return path


def report(paths, out_path=None):
    allrows = []
    print("=" * 78)
    print("damage_ceiling.py -- is the dmax = %.2f ceiling holding the peak up?"
          % DMAX_CAP)
    print("=" * 78)
    for p in paths:
        if not os.path.exists(p):
            print("\n  MISSING: %s" % p)
            continue
        rows = analyse(p)
        allrows += rows
        print("\n%s" % job_of(p))
        for kind, _job, step, phase, val, unit, basis, verdict in rows:
            print("  %-8s %-22s %-7s %8s %-6s %s"
                  % (kind, step[:22], phase, val, unit, verdict))
            if basis:
                print("           %s" % basis)

    if not allrows:
        print("\n  nothing to judge.")
        return 1
    need = [r for r in allrows if r[7] == "NOT COMPUTABLE FROM THIS FILE"]
    censored = [r for r in allrows if r[7] == "LOWER BOUND"]
    print("\n" + "-" * 78)
    print(" WHAT THIS RUN CAN AND CANNOT CONCLUDE")
    print("-" * 78)
    if censored:
        print("  %d step(s) exhausted the rank-%d list, so their counts are"
              % (len(censored), RANK_LIMIT))
        print("  lower bounds, not counts.")
    if need:
        print("  The inflation bound needs volfrac_at_cap, which these maps do")
        print("  not carry -- they were written before damage_map.py counted")
        print("  the cap on COMPONENTS.  Re-run the reader on the SAME odb;")
        print("  there is no solver in this and it takes seconds:")
        print("    %s" % RERUN_HINT)
        print("  then run this file again on the new <job>_damage_map.csv.")
    if not need and not censored:
        print("  Counts are exact and the bound is computed.  A strength may")
        print("  be quoted with the bound stated beside it.")
    out = write_csv(allrows, out_path or "damage_ceiling_summary.csv")
    print("\n  wrote %s -- upload THAT, not a screenshot." % out)
    print("=" * 78)
    return 0


# ==========================================================================
def selftest():
    ok = []

    def t(name, cond, detail=""):
        ok.append(cond)
        print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("damage_ceiling.py --selftest")

    print("\n  A. exact counts and censored ones are not the same claim")
    kind, why = counted_or_bounded(22, 30)
    t("22 capped out of 30 ranked is an exact count", kind == "exact", why)
    kind, why = counted_or_bounded(30, 30)
    t("30 of 30 is a LOWER BOUND, because rank 31 is not shown",
      kind == "LOWER BOUND", why)
    t("  and the wording says the real number is unknown",
      "unknown" in why)

    print("\n  B. an unloaded step that saturates is the strongest timing fact")
    t("the cooldown step is not mechanical",
      not is_mechanical("Manufacturing_Cooling"))
    t("the reheat step is not mechanical", not is_mechanical("Heating_to_500C"))
    t("the tension step is", is_mechanical("Tension_at_500C"))
    t("an unrecognised step is treated as loaded, not as thermal",
      is_mechanical("Some_New_Step"),
      "calling a loaded step thermal would manufacture the finding")

    print("\n  C. one band and a scatter must not read the same")
    cell = (3.4412, 3.4412, 0.4276)
    band = [(1.0 + 0.05 * i, 1.0, 0.2) for i in range(6)]
    sp = spread(band)
    v, d = spatial_verdict(sp[0], cell, sp[1])
    t("six contiguous points along one line read as ONE BAND",
      v == "ONE BAND", d)
    wide = [(-0.8, -0.8, 0.01), (2.5, 2.5, 0.39), (0.1, 2.0, 0.2),
            (0.15, 2.0, 0.2), (2.4, -0.7, 0.05), (2.45, -0.7, 0.05)]
    sp = spread(wide)
    v, d = spatial_verdict(sp[0], cell, sp[1])
    t("points across the whole cell read as SCATTERED CLUSTERS",
      v == "SCATTERED CLUSTERS", d)
    t("a single point cannot be judged either way",
      spatial_verdict(None, cell, 0.0)[0] == "too few points")

    print("\n  D. the real T500 map, which is what A-4 was asked about")
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(os.path.dirname(here), "data", "results", "M6",
                     "LTH_M6_T500_damage_map.csv")
    if os.path.exists(p):
        rows = analyse(p)
        tot = [r for r in rows if r[0] == "summary"][0]
        t("it finds the 42 the chapter cites", tot[4] == 42, "%s points" % tot[4])
        pre = [r for r in rows if r[0] == "timing"
               and r[7] == "CEILING REACHED BEFORE LOADING"]
        t("and the reheat step alone puts 12 there, before any load",
          len(pre) == 1 and pre[0][4] == 12 and "Heating" in pre[0][2],
          "%s in %s" % (pre[0][4], pre[0][2]) if pre else "none found")
        ten = [r for r in rows if r[0] == "count" and "Tension" in r[2]]
        t("the tension count is censored, not exact",
          ten and ten[0][7] == "LOWER BOUND",
          ten[0][6] if ten else "no tension row")
        ph = {r[3]: r[4] for r in rows if r[0] == "phase" and "Tension" in r[2]}
        t("and the ceiling is mostly MATRIX, not the yarn slots",
          ph.get("MATRIX", 0) > sum(v for k, v in ph.items() if k != "MATRIX"),
          "matrix %s vs yarn %s"
          % (ph.get("MATRIX"), sum(v for k, v in ph.items() if k != "MATRIX")))
        sprow = [r for r in rows if r[0] == "space" and "Tension" in r[2]]
        t("the capped points are not one band",
          sprow and sprow[0][7].startswith("SCATTERED"),
          sprow[0][6] if sprow else "no space row")
        bd = [r for r in rows if r[0] == "bound"]
        t("and the inflation bound is refused, not guessed",
          bd and bd[0][7] == "NOT COMPUTABLE FROM THIS FILE",
          "this map predates volfrac_at_cap")
    else:
        t("the T500 map is committed for this test", False, "missing %s" % p)

    print("\n  E. RT23 cannot be judged from this file, and must not be")
    p2 = os.path.join(os.path.dirname(here), "data", "results", "M6",
                      "LTH_M6_RT23_damage_map.csv")
    if os.path.exists(p2):
        rows = analyse(p2)
        sm = [r for r in rows if r[0] == "summary"]
        t("no RT23 point is CERTAINLY on the ceiling", sm[0][4] == 0,
          "%s certain, verdict %r" % (sm[0][4], sm[0][7]))
        und = [r for r in sm if r[7] == "INDETERMINATE FROM THIS FILE"]
        t("  but 30 yarn points sit ABOVE the cap, which decides nothing",
          und and und[0][4] == 30,
          "%s combined-magnitude points over %.2f"
          % (und[0][4] if und else "-", DMAX_CAP))
        t("  so the file refuses to call RT23 unsaturated",
          bool(und), "0.976 can be 0.85 and 0.84, or 0.90 and 0.76")
    else:
        t("the RT23 map is committed for this test", False, "missing %s" % p2)

    print("\n  F. the CSV carries value, basis and verdict together")
    import tempfile
    d = tempfile.mkdtemp()
    out = write_csv([("count", "J", "S", "MATRIX", 22, "points", "why",
                      "exact")], os.path.join(d, "x.csv"))
    body = open(out).read()
    t("it writes one", os.path.exists(out))
    t("header names value, basis and verdict",
      all(k in CSV_HEADER for k in ("value", "basis", "verdict")))
    t("and a row keeps them on one line",
      "22" in body and "why" in body and "exact" in body)

    print("\n  G. a command we PRINT has to be a command that RUNS")
    # This file's only instruction to the user named a second positional
    # argument that damage_map.py's parser does not have.  Anyone who
    # followed it got "unrecognized arguments" -- a dead end we printed
    # ourselves.  Checked against the real parser, not against a copy of it.
    here = os.path.dirname(os.path.abspath(__file__))
    dm = os.path.join(here, "damage_map.py")
    if not os.path.exists(dm):
        t("damage_map.py is beside this file", False, dm)
    else:
        src = open(dm).read()
        positional = [ln for ln in src.splitlines()
                      if "add_argument(" in ln and '"-' not in ln]
        n_pos = len(positional)
        args = RERUN_HINT.split()
        # "abaqus python damage_map.py <job>.odb" -> the arguments after the
        # script name are what the parser has to accept.
        after = args[args.index("damage_map.py") + 1:]
        t("the hint passes exactly as many positionals as the parser has",
          len(after) == n_pos,
          "hint passes %d (%s), parser declares %d (%s)"
          % (len(after), " ".join(after), n_pos,
             ", ".join(p.split('"')[1] for p in positional)))
        t("  and the one it passes is the odb, which is what is declared",
          n_pos == 1 and 'add_argument("odb"' in src
          and after and after[0].endswith(".odb"),
          "damage_map.py takes an odb and nothing else")
        t("  the hint names the tool that actually exists",
          "damage_map.py" in RERUN_HINT and os.path.exists(dm))
        t("  and runs it under abaqus python, since it opens an odb",
          RERUN_HINT.startswith("abaqus python "),
          "odbAccess is not importable from plain python")

    print("\n%s" % ("ALL %d SELFTESTS PASS" % len(ok) if all(ok)
                    else "FAILED %d of %d" % (ok.count(False), len(ok))))
    return 0 if all(ok) else 1


def main(argv):
    if "--selftest" in argv or "--check" in argv:
        return selftest()
    paths = []
    out = None
    i = 0
    while i < len(argv):
        if argv[i] == "-o":
            out = argv[i + 1]
            i += 2
            continue
        paths.extend(sorted(glob.glob(argv[i]))
                     if any(c in argv[i] for c in "*?") else [argv[i]])
        i += 1
    if not paths:
        print(__doc__)
        return 2
    return report(paths, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
