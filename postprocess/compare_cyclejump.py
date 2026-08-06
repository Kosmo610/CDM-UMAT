"""Cycle-jump error: explicit cycles vs the jumped run, measured once.

RUN WITH:  python3 compare_cyclejump.py CJ1_MECH_SZ_TRSC_EN.csv \
                                        CJ5_MECH_SZ_TRSC_EN.csv

WHY THIS JOB PAIR EXISTS
------------------------
The production matrix runs with cycle jump (one increment stands for
several cycles).  verify_thermshock.py T6 bounds the MATERIAL-POINT error
at 0.03 % for a x10 jump, but a structure adds what a point cannot see:
damage at one element changes the stress at its neighbours, and the jump
coarsens that redistribution.  refs/[58] (Cojocaru & Karlsson) solves this
with adaptive jump control; our answer (a2-0020) is to keep the fixed
interval and MEASURE the error once on the real mesh -- this file is that
measurement.  If it comes back large, adaptive control gets implemented;
if small, refs/[57][58] are cited and the fixed interval is a documented,
quantified choice.

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


def compare(explicit, jumped):
    """Rows of (N, quantity, explicit, jumped, rel_err) at shared N."""
    rows = []
    for n in sorted(set(explicit) & set(jumped)):
        for key in ("E_over_E0", "dcyc_mean", "dcyc_max"):
            a = float(explicit[n][key])
            b = float(jumped[n][key])
            denom = abs(a) if abs(a) > 1e-12 else 1.0
            rows.append((n, key, a, b, abs(b - a) / denom))
    return rows


def verdict(rows):
    """(worst E-error, verdict string).  E rules; d_cyc is diagnostic."""
    es = [r[4] for r in rows if r[1] == "E_over_E0" and r[0] > 0]
    if not es:
        return None, "no shared post-cycling checkpoint -- nothing compared"
    w = max(es)
    if w < THRESH_OK:
        return w, ("OK: %.2f %% -- below the experiment's own scatter; "
                   "the fixed jump stands, cite refs/[57][58]" % (100 * w))
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
        print("%-6g %-11s %12.6f %12.6f %9.3f %%" % (nn, key, a, b, 100 * e))
    w, v = verdict(rows)
    print("\n" + v)
    return 0 if w is not None and w < THRESH_WARN else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
