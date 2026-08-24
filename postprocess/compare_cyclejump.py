"""Cycle-jump error: explicit cycles vs the jumped run, measured once.

RUN WITH:  python3 compare_cyclejump.py CJ1_MECH_SZ_TRSC_EN.csv \
                                        CJ5_MECH_SZ_TRSC_EN.csv

WHY THIS JOB PAIR EXISTS
------------------------
The production matrix runs with cycle jump (one increment stands for
several cycles).  verify_thermshock.py T6 bounds the MATERIAL-POINT error
at 0.03 % for a x10 jump, but a structure adds what a point cannot see:
damage at one element changes the stress at its neighbours, and the jump
coarsens that redistribution.  Our answer (a2-0020) is to keep the fixed
interval and MEASURE the error once on the real mesh -- this file is that
measurement.

THE TWO CITATIONS DO DIFFERENT JOBS (a1-0021, corrected 2026-08-06)
-------------------------------------------------------------------
This file first put refs/[57] and refs/[58] together as "adaptive control
we did not implement".  That is right for [58] and wrong for [57].

refs/[57] section 6.1 sets its jump from an ALLOWED INCREASE OF THE DAMAGE
VARIABLE -- D(N + NJUMP) = D(N) + (dD/dN)|_N * NJUMP -- which is the same
criterion as our max_djump.  So [57] is the SOURCE of the criterion we
use, not an alternative to it.  What differs is the mechanism:

                bounds            picks the jump width
    refs/[57]   damage increment  FORWARD, from dD/dN        (adaptive)
    refs/[58]   change of RATE    from a relative error q_y  (adaptive)
    ours        damage increment  FIXED; cuts back on exceed (reactive)

A reactive cutback holds the per-increment damage inside the tolerance but
cannot CHOOSE the jump width.  That one sentence is the limitation's exact
shape -- and refs/[58], which bounds the change of the rate by linear
extrapolation from the previous two cycles, is the "better method, not
implemented" citation.  Neither we nor [57] do that.

AND OUR TOLERANCE IS 10x LOOSER, WHICH HAS TO BE SAID
------------------------------------------------------
    refs/[57] example    dD <= 0.01     (D in [0,1])
    ours, D_DJUMP        dD <= 0.10     (abaqus/retune_deck.py)

Writing "we used a fixed interval" without that ratio understates the gap.
data/literature/cycle_jump_provenance.py reads D_DJUMP straight out of
retune_deck.py, so the number follows if the card changes.

One constraint survives adaptivity: refs/[57] notes a finite element run
can carry only ONE global jump width while local demands "can be very
contradictory".  Our matrix and yarn damage at very different rates, so
that is exactly our case -- the single interval is not our simplification,
and adaptivity would only change who picks its value.

VERDICT SCALE
-------------
The error that matters is on E/E0 at the shared checkpoint, because E(N)
is the primary cycle-calibration target (T1, refs/[03]).

    < 1 %   negligible -- below every published modulus error bar we hold
    1-3 %   acceptable -- report the number next to every E(N) result
    > 3 %   too coarse -- halve the jump (or implement refs/[58]) and rerun

WHERE THE 1 % ANCHOR COMES FROM (a1, citation fix 2026-08-06)
-------------------------------------------------------------
This scale first read "below refs/[03]'s own error bars".  refs/[03]
publishes NO error bars -- not one "+/-" appears in the paper.  It tests
five unshocked and three shocked specimens per condition and reports
averages only, so nothing in it can anchor a tolerance.

The threshold survives on a different source.  refs/[10] Table 1 does
publish scatter, on the same quantity (tensile modulus) for the same class
of material:

    300 K   128.7 +/- 1.8 GPa   1.40 %
    973 K   152.3 +/- 4.7 GPa   3.09 %
   1273 K   172.7 +/- 7.0 GPa   4.05 %
   1473 K   169.1 +/- 2.6 GPa   1.54 %

1 % sits below the smallest of these, and 3 % below the largest, so the
scale is anchored to measured scatter after all -- just not to [03]'s.
The thresholds themselves are unchanged; only the citation is.
"""
from __future__ import print_function

import csv
import sys

THRESH_OK = 0.01
THRESH_WARN = 0.03


def load(path):
    with open(path) as fh:
        return {float(r["N"]): r for r in csv.DictReader(fh)}


#: Below this, d_cyc is numerical dust and no ratio taken against it means
#: anything.  The 2026-08-12 run reported "400.002 %" on d_cyc = 2e-6 against
#: an explicit 4e-7 -- both of which are zero for every purpose this thesis
#: has -- and printed it directly under a verdict of "OK: 0.00 %".  The two
#: lines contradicted each other and both were technically true, which is the
#: worst kind of output a checker can produce.
DCYC_FLOOR = 1.0e-4


def compare(explicit, jumped):
    """Rows of (N, quantity, explicit, jumped, rel_err) at shared N.

    rel_err is None when the baseline is below the floor for its quantity.
    None prints as "--", not as a number, because a percentage computed on
    dust looks exactly like a percentage computed on a measurement.
    """
    rows = []
    for n in sorted(set(explicit) & set(jumped)):
        for key in ("E_over_E0", "dcyc_mean", "dcyc_max"):
            a = float(explicit[n][key])
            b = float(jumped[n][key])
            floor = DCYC_FLOOR if key.startswith("dcyc") else 1.0e-12
            if abs(a) < floor and abs(b) < floor:
                rows.append((n, key, a, b, None))
            else:
                denom = max(abs(a), floor)
                rows.append((n, key, a, b, abs(b - a) / denom))
    return rows


def cycling_happened(rows):
    """Did either run accumulate cycle damage worth comparing?

    A jump-error measured on a job where d_cyc never left the floor is not a
    small error -- it is no test at all.  Saying "OK" there would certify the
    jump on the strength of a run in which nothing happened, which is exactly
    what this file did on 2026-08-12: the CJHEAT job it depended on had been
    built on the placeholder thermal card, so the plate swung 900 -> 898.9 C
    instead of 900 -> 300, and d_cyc stayed at 2e-6.
    """
    return any(max(abs(r[2]), abs(r[3])) >= DCYC_FLOOR
               for r in rows if r[1].startswith("dcyc"))


def verdict(rows):
    """(worst E-error, verdict string).  E rules; d_cyc is diagnostic."""
    es = [r[4] for r in rows
          if r[1] == "E_over_E0" and r[0] > 0 and r[4] is not None]
    if not es:
        return None, "no shared post-cycling checkpoint -- nothing compared"
    if not cycling_happened(rows):
        return None, (
            "VOID: d_cyc never rose above %.0e in EITHER run, so there is no "
            "cycle damage for the jump to get wrong.  This measures nothing "
            "about the jump.  Check the temperature history first -- "
            "extract_probe.py's stepdiag CSV shows whether the quench and "
            "reheat steps actually swing, and a plate that only moves a "
            "kelvin or two is a thermal CARD problem, not a jump problem."
            % DCYC_FLOOR)
    w = max(es)
    if w < THRESH_OK:
        return w, ("OK: %.2f %% -- under refs/[10]'s smallest published "
                   "modulus scatter (1.40 %%); the fixed jump stands, with "
                   "refs/[57] as the criterion's source and refs/[58] as "
                   "the unimplemented better method" % (100 * w))
    if w < THRESH_WARN:
        return w, ("ACCEPTABLE: %.2f %% -- quote this number beside every "
                   "E(N) result" % (100 * w))
    return w, ("TOO COARSE: %.2f %% -- halve --cycle-jump or implement "
               "adaptive control (refs/[58]) before the matrix" % (100 * w))


def selftest():
    n = [0]

    def ck(name, cond, detail=""):
        n[0] += cond
        print("   [%s] %s%s" % ("PASS" if cond else "FAIL", name,
                                ("   " + detail) if detail else ""))
        if not cond:
            raise SystemExit(1)

    print("compare_cyclejump.py --selftest")
    ex = {0.0: dict(E_over_E0="1.0", dcyc_mean="0", dcyc_max="0"),
          20.0: dict(E_over_E0="0.80", dcyc_mean="0.30", dcyc_max="0.5")}
    ck("identical runs give zero error and OK",
       verdict(compare(ex, ex))[0] == 0.0)
    jm = {0.0: ex[0.0],
          20.0: dict(E_over_E0="0.798", dcyc_mean="0.31", dcyc_max="0.5")}
    w, v = verdict(compare(ex, jm))
    ck("a 0.25 % stiffness gap is OK", w < THRESH_OK and "OK" in v,
       "%.3f %%" % (100 * w))
    jm[20.0]["E_over_E0"] = "0.76"
    w, v = verdict(compare(ex, jm))
    ck("a 5 % gap is refused", w > THRESH_WARN and "TOO COARSE" in v,
       "%.1f %%" % (100 * w))
    ck("the verdict never keys on d_cyc alone",
       "E(N)" in __doc__ and "E rules" in verdict.__doc__)
    only0 = {0.0: ex[0.0]}
    w, v = verdict(compare(only0, only0))
    ck("N=0-only overlap says so instead of declaring victory",
       w is None and "nothing compared" in v)

    # ---- the 2026-08-12 run, reproduced exactly ------------------------
    # LTH_CJ1/LTH_CJ5 read a CJHEAT job built on the placeholder thermal
    # card, so the plate swung 900 -> 898.9 C and d_cyc stayed at 2e-6.
    # This file printed "400.002 %" on d_cyc and, three lines later, "OK:
    # 0.00 %".  Both were true of their own column and together they were
    # worthless.  Every check below fails on the OLD behaviour.
    dead_ex = {0.0: dict(E_over_E0="1.0", dcyc_mean="0", dcyc_max="0"),
               20.0: dict(E_over_E0="0.999813", dcyc_mean="0.0000004",
                          dcyc_max="0.0000004")}
    dead_jm = {0.0: dead_ex[0.0],
               20.0: dict(E_over_E0="0.999822", dcyc_mean="0.000002",
                          dcyc_max="0.000002")}
    dead = compare(dead_ex, dead_jm)
    w, v = verdict(dead)
    ck("a run where d_cyc never grew is VOID, not OK",
       w is None and v.startswith("VOID"))
    ck("  and the verdict says to look at the temperature history first",
       "stepdiag" in v and "thermal CARD" in v)
    ck("  no percentage is printed against a baseline of dust",
       all(e is None for nn, key, a, b, e in dead if key.startswith("dcyc")),
       "the old code printed 400.002 %")
    ck("  while the stiffness column, which is real, still gets its number",
       all(e is not None for nn, key, a, b, e in dead
           if key == "E_over_E0" and nn > 0))
    # The floor must not swallow a real result: 0.30 vs 0.31 is 3 %, and
    # three orders of magnitude above the floor.
    ck("a genuine d_cyc comparison is untouched by the floor",
       cycling_happened(compare(ex, jm)))
    ck("  and the floor sits far below any d_cyc worth reporting",
       DCYC_FLOOR < 0.30 / 1000.0, "floor %.0e vs a real 0.30" % DCYC_FLOOR)

    # a1-0021: the two citations do different jobs, and the tolerance gap
    # is a number that must not quietly go missing from the limitation.
    ck("refs/[57] is named the criterion's SOURCE, not an alternative",
       "SOURCE of the criterion we" in __doc__ and "same\ncriterion" in __doc__)
    ck("refs/[58] is named the unimplemented better method",
       "better method, not" in __doc__)
    ck("the 10x tolerance gap is stated with both numbers",
       "dD <= 0.01" in __doc__ and "dD <= 0.10" in __doc__)
    ck("the single-global-jump constraint is attributed to [57], not to us",
       "not our simplification" in __doc__)
    ck("the 1 % anchor cites refs/[10]'s scatter, not [03]'s absent bars",
       "publishes NO error bars" in __doc__ and "1.40 %" in __doc__)
    ck("the tolerance the error was measured at is read from the generator",
       abs(_djump() - 0.10) < 1e-12, "max_djump = %g" % _djump())
    print("   %d passed" % n[0])
    return 0


def main(argv):
    if "--selftest" in argv or "--check" in argv:
        return selftest()
    if len(argv) < 2:
        print(__doc__)
        return 2
    ex, jm = load(argv[0]), load(argv[1])
    rows = compare(ex, jm)
    print("%-6s %-11s %12s %12s %10s" % ("N", "quantity", "explicit",
                                         "jumped", "rel.err"))
    for nn, key, a, b, e in rows:
        print("%-6g %-11s %12.6f %12.6f %9s" %
              (nn, key, a, b,
               "--" if e is None else "%.3f %%" % (100 * e)))
    if any(e is None for _, _, _, _, e in rows):
        print("\n  '--' = the baseline is below the floor (d_cyc %.0e), so a"
              % DCYC_FLOOR)
        print("  ratio against it would be a percentage of nothing.")
    w, v = verdict(rows)
    print("\n" + v)
    # The CSV is the deliverable (CLAUDE.md 3-2), and it has to carry the
    # verdict too -- a console line does not survive being pasted into chat.
    out = "cyclejump_summary.csv"
    with open(out, "w") as fh:
        fh.write("N,quantity,explicit,jumped,rel_err_pct,dcyc_floor,verdict\n")
        for nn, key, a, b, e in rows:
            fh.write("%g,%s,%.9g,%.9g,%s,%g,%s\n"
                     % (nn, key, a, b,
                        "" if e is None else "%.4f" % (100 * e),
                        DCYC_FLOOR, v.split(":")[0].split(" --")[0]))
    print("wrote %s -- UPLOAD THIS ONE" % out)
    if w is None:
        return 1
    print("\nCONDITIONAL ON THE DAMAGE-INCREMENT TOLERANCE.  This error was")
    print("measured with max_djump = %g (retune_deck.py D_DJUMP), the cap the"
          % _djump())
    print("reactive cutback enforces.  refs/[57] sets its ADAPTIVE jump from")
    print("the same quantity but with an example tolerance of 0.01 -- ours is")
    print("10x looser, so quote the number above together with the tolerance")
    print("it was measured at, never on its own.")
    return 0 if w < THRESH_WARN else 1


def _djump(default=0.10):
    """D_DJUMP straight from the deck generator, so the caveat cannot drift."""
    import os
    import re
    p = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "abaqus", "retune_deck.py")
    if not os.path.exists(p):
        return default
    m = re.search(r"^D_DJUMP = ([0-9.]+)", open(p).read(), re.M)
    return float(m.group(1)) if m else default


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
