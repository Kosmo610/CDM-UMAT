#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_tangent.py -- did the consistent tangent actually buy anything?

RUN WITH PLAIN PYTHON (it reads .msg only, never the odb):

    python3 compare_tangent.py CBAND_N5_ITAN0.msg CBAND_N5_ITAN1.msg
    python3 compare_tangent.py --selftest

WHY THIS EXISTS
---------------
src/UMAT_CSIC_THERMSHOCK_V3_0.for has carried the consistent tangent (the
stiffness matrix Abaqus asks for, Ge refs/[24] Eqs. 31-33) behind an ITAN
switch since 2026-08-10.  cross_check_fortran.py already proves the matrix is
CORRECT -- it agrees with a central-difference Jacobian of the very stress
update the routine performs, to 6.9e-9 over 64 states.  What no test can
answer offline is whether it is WORTH IT: an exact tangent costs arithmetic
per material point and pays back in iterations, and which side wins is a
property of the problem, not of the algebra.

So this reads the two .msg files of an otherwise identical pair and reports
the trade.  There are only three honest outcomes and all three are useful:

  ITAN=1 converges in fewer iterations   -> turn it on, quote the ratio
  ITAN=1 costs more than it saves        -> leave it off, and say WHY the
                                            default is off instead of
                                            leaving the reader to wonder
  the two disagree on the ANSWER         -> a DEFECT.  A tangent is the
                                            derivative of the stress update;
                                            it changes the path to the
                                            solution, never the solution.

THE THIRD ONE IS THE POINT.  A wrong tangent usually still converges -- to
the right answer, slowly -- so "it ran" proves nothing.  But a tangent that
has been mistakenly wired to change the STRESS rather than DDSDDE converges
to a different curve, and the only cheap way to catch that is to compare the
converged reaction histories of the pair.  The .msg carries enough for that:
every increment's final time and, on a displacement-controlled job, the
step time is a proxy for the loading.  The force comparison itself needs the
odb and belongs to patch_report.py -- this file says so rather than
pretending otherwise.

WHAT IS COUNTED, AND WHY EACH ONE
---------------------------------
  increments   how many the solver needed.  Fewer is not automatically
               better: a job that cut back less took bigger steps.
  attempts     increments that had to be retried.  This is the number an
               exact tangent is supposed to move most.
  iterations   the total equilibrium iterations -- the actual cost.
  severe disc. severe discontinuity iterations, counted separately because
               they are driven by contact/closure status changes, not by
               the tangent, and mixing them into the total flatters or
               punishes the comparison at random.

Everything lands in <pair>_tangent.csv with the value, the basis it was
judged against and the verdict in the same row, because a console line is
not a deliverable (CLAUDE.md 3-2).
"""
from __future__ import print_function

import os
import re
import sys

# Abaqus writes these in fixed forms.  Each pattern is anchored on the words
# Abaqus itself uses, not on column positions, because the numeric fields
# change width between releases.
INC_RE = re.compile(r"INCREMENT\s+(\d+)\s+STARTS", re.I)
ATT_RE = re.compile(r"ATTEMPT\s+NUMBER\s+(\d+)", re.I)
ITER_RE = re.compile(r"EQUILIBRIUM\s+ITERATION\s+(\d+)", re.I)
SDI_RE = re.compile(r"SEVERE\s+DISCONTINUITY\s+ITERATION\s+(\d+)", re.I)
CONV_RE = re.compile(r"INCREMENT\s+(\d+)\s+SUMMARY", re.I)
TIME_RE = re.compile(r"TOTAL\s+TIME\s+COMPLETED\s+([0-9.E+-]+)", re.I)
CUT_RE = re.compile(r"TIME\s+INCREMENT\s+.*\s+CUT\s+BACK", re.I)
DIED_RE = re.compile(r"TOO\s+MANY\s+ATTEMPTS|ANALYSIS\s+.*\s+NOT\s+COMPLETED",
                     re.I)


def parse_msg(path_or_text, is_text=False):
    """Count what the solver had to do.  Returns a plain dict."""
    if is_text:
        text = path_or_text
    else:
        try:
            text = open(path_or_text, errors="replace").read()
        except TypeError:                      # python 2
            text = open(path_or_text).read()

    starts = INC_RE.findall(text)
    attempts = [int(v) for v in ATT_RE.findall(text)]
    return dict(
        increments=len(set(int(v) for v in starts)),
        starts=len(starts),
        # An attempt number above 1 is a retry; the count of retries is what
        # a tangent is supposed to reduce, so it is reported on its own.
        retries=sum(1 for v in attempts if v > 1),
        iterations=len(ITER_RE.findall(text)),
        severe=len(SDI_RE.findall(text)),
        cutbacks=len(CUT_RE.findall(text)),
        converged=len(CONV_RE.findall(text)),
        end_time=(float(TIME_RE.findall(text)[-1])
                  if TIME_RE.findall(text) else None),
        completed=not bool(DIED_RE.search(text)),
    )


def _ratio(a, b):
    """b relative to a, guarding the zero that an unrun job would give."""
    if a in (0, None) or b is None:
        return None
    return float(b) / float(a)


def compare(m0, m1, tol_time=1.0e-9):
    """Judge the pair.  Every row carries its own basis and verdict."""
    rows = []

    def add(name, v0, v1, basis, verdict):
        rows.append(dict(quantity=name, itan0=v0, itan1=v1,
                         basis=basis, verdict=verdict))

    # --- the correctness gate comes FIRST.  A speed-up on a different
    #     answer is not a speed-up.
    same_end = (m0["end_time"] is not None and m1["end_time"] is not None
                and abs(m0["end_time"] - m1["end_time"]) <= tol_time)
    add("end_time", m0["end_time"], m1["end_time"],
        "identical decks must reach the same step time",
        "SAME" if same_end else "DIFFERENT -- INVESTIGATE BEFORE READING COST")
    both_done = m0["completed"] and m1["completed"]
    add("completed", m0["completed"], m1["completed"],
        "both must run to the end for the cost to mean anything",
        "BOTH" if both_done else "AT LEAST ONE DIED -- COST IS NOT COMPARABLE")

    r_it = _ratio(m0["iterations"], m1["iterations"])
    add("iterations", m0["iterations"], m1["iterations"],
        "total equilibrium iterations; ITAN=1/ITAN=0",
        _verdict_cost(r_it, both_done and same_end))
    r_re = _ratio(m0["retries"], m1["retries"])
    add("retries", m0["retries"], m1["retries"],
        "attempts beyond the first; what an exact tangent should move most",
        _verdict_cost(r_re, both_done and same_end))
    add("cutbacks", m0["cutbacks"], m1["cutbacks"],
        "time-increment cutbacks", _verdict_cost(
            _ratio(m0["cutbacks"], m1["cutbacks"]), both_done and same_end))
    add("increments", m0["increments"], m1["increments"],
        "increments the solver needed; fewer means bigger steps, not "
        "necessarily cheaper", "INFORMATIONAL")
    add("severe_discontinuity_iterations", m0["severe"], m1["severe"],
        "status-change iterations; NOT driven by the tangent, excluded from "
        "the cost ratio on purpose", "INFORMATIONAL")

    ipi0 = _ratio(m0["converged"] or m0["increments"], m0["iterations"])
    ipi1 = _ratio(m1["converged"] or m1["increments"], m1["iterations"])
    add("iterations_per_increment", ipi0, ipi1,
        "the density measure -- immune to one job simply taking more steps",
        _verdict_cost(_ratio(ipi0, ipi1), both_done and same_end))
    return rows


def _verdict_cost(ratio, trustworthy):
    if not trustworthy:
        return "NOT COMPARABLE"
    if ratio is None:
        return "NO DATA"
    if ratio < 0.95:
        return "ITAN=1 CHEAPER (%.3fx)" % ratio
    if ratio > 1.05:
        return "ITAN=1 DEARER (%.3fx)" % ratio
    return "NO MEANINGFUL DIFFERENCE (%.3fx)" % ratio


def csv_text(rows):
    out = ["quantity,itan0,itan1,basis,verdict"]
    for r in rows:
        out.append("%s,%s,%s,\"%s\",%s"
                   % (r["quantity"],
                      "" if r["itan0"] is None else r["itan0"],
                      "" if r["itan1"] is None else r["itan1"],
                      r["basis"], r["verdict"]))
    return "\n".join(out) + "\n"


def report(rows, path):
    w = max(len(r["quantity"]) for r in rows)
    print("\n  %-*s %14s %14s   %s" % (w, "quantity", "ITAN=0", "ITAN=1",
                                       "verdict"))
    print("  " + "-" * (w + 50))
    for r in rows:
        def f(v):
            if v is None:
                return "-"
            if isinstance(v, float):
                return "%.4f" % v
            return str(v)
        print("  %-*s %14s %14s   %s"
              % (w, r["quantity"], f(r["itan0"]), f(r["itan1"]), r["verdict"]))
    open(path, "w").write(csv_text(rows))
    print("\n  wrote %s   <- upload THIS, not a screenshot" % path)


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", name, detail))


def _fake_msg(nincr, iters_per, retries=0, severe=0, end=1.0, died=False):
    """A .msg in the shapes Abaqus actually writes."""
    L = []
    for i in range(1, nincr + 1):
        L.append(" INCREMENT     %d STARTS. ATTEMPT NUMBER   1, "
                 "TIME INCREMENT   2.000E-03" % i)
        for k in range(1, iters_per + 1):
            L.append("  EQUILIBRIUM ITERATION     %d" % k)
            L.append("    AVERAGE FORCE  1.0  LARGEST RESIDUAL FORCE  "
                     "1.0E-06 AT NODE   17 DOF 1")
        for k in range(severe):
            L.append("  SEVERE DISCONTINUITY ITERATION     %d" % (k + 1))
        L.append(" INCREMENT     %d SUMMARY" % i)
        L.append(" TOTAL TIME COMPLETED  %.6E" % (end * i / nincr))
    for r in range(retries):
        L.insert(1, " ***NOTE: THE TIME INCREMENT HAS BEEN CUT BACK")
        L.insert(2, " INCREMENT     1 STARTS. ATTEMPT NUMBER   %d, "
                    "TIME INCREMENT   5.000E-04" % (r + 2))
    if died:
        L.append(" ***ERROR: TOO MANY ATTEMPTS MADE FOR THIS INCREMENT")
    return "\n".join(L) + "\n"


def selftest():
    print("=" * 74)
    print(" compare_tangent.py selftest")
    print("=" * 74)

    m = parse_msg(_fake_msg(10, 4), is_text=True)
    t("counts increments", m["increments"] == 10, "%d" % m["increments"])
    t("counts iterations", m["iterations"] == 40, "%d" % m["iterations"])
    t("a clean job reports no retries", m["retries"] == 0)
    t("reads the last completed time", abs(m["end_time"] - 1.0) < 1e-12)
    t("a clean job is completed", m["completed"] is True)

    mr = parse_msg(_fake_msg(10, 4, retries=3, severe=2), is_text=True)
    t("counts retries as attempts beyond the first", mr["retries"] == 3,
      "%d" % mr["retries"])
    t("counts cutbacks", mr["cutbacks"] == 3, "%d" % mr["cutbacks"])
    t("counts severe-discontinuity iterations separately",
      mr["severe"] == 20 and mr["iterations"] == 40,
      "sdi=%d iter=%d" % (mr["severe"], mr["iterations"]))
    # THE POINT OF KEEPING THEM APART: severe discontinuities are status
    # changes, so folding them into the total would report a tangent effect
    # where there is none.
    t("severe discontinuities never enter the iteration count",
      parse_msg(_fake_msg(4, 3, severe=9), is_text=True)["iterations"] == 12)

    md = parse_msg(_fake_msg(3, 4, died=True), is_text=True)
    t("a dead job is flagged", md["completed"] is False)

    # --- the judgement ---------------------------------------------------
    good = compare(parse_msg(_fake_msg(10, 6), is_text=True),
                   parse_msg(_fake_msg(10, 4), is_text=True))
    d = dict((r["quantity"], r) for r in good)
    t("a real saving is reported as cheaper",
      d["iterations"]["verdict"].startswith("ITAN=1 CHEAPER"),
      d["iterations"]["verdict"])
    t("the same end time passes the correctness gate",
      d["end_time"]["verdict"] == "SAME")

    worse = compare(parse_msg(_fake_msg(10, 4), is_text=True),
                    parse_msg(_fake_msg(10, 7), is_text=True))
    dw = dict((r["quantity"], r) for r in worse)
    t("a loss is reported as dearer, not hidden",
      dw["iterations"]["verdict"].startswith("ITAN=1 DEARER"),
      dw["iterations"]["verdict"])

    same = compare(parse_msg(_fake_msg(10, 4), is_text=True),
                   parse_msg(_fake_msg(10, 4), is_text=True))
    ds = dict((r["quantity"], r) for r in same)
    t("no difference is reported as no difference",
      ds["iterations"]["verdict"].startswith("NO MEANINGFUL"))

    # THE ONE THAT MATTERS.  A tangent may not change the answer, so a pair
    # that ends at different step times must not be read as a speed-up.
    bad = compare(parse_msg(_fake_msg(10, 8, end=1.0), is_text=True),
                  parse_msg(_fake_msg(10, 4, end=0.6), is_text=True))
    db = dict((r["quantity"], r) for r in bad)
    t("a different end time is called out as a defect",
      db["end_time"]["verdict"].startswith("DIFFERENT"))
    t("and the cost rows refuse to be read at all",
      db["iterations"]["verdict"] == "NOT COMPARABLE",
      db["iterations"]["verdict"])
    # A halved iteration count on a job that stopped early is exactly the
    # false result this guard exists to prevent.
    t("the false speed-up is NOT reported as a saving",
      "CHEAPER" not in db["iterations"]["verdict"])

    dead = compare(parse_msg(_fake_msg(10, 4), is_text=True),
                   parse_msg(_fake_msg(10, 4, died=True), is_text=True))
    dd = dict((r["quantity"], r) for r in dead)
    t("a dead partner makes the cost incomparable",
      dd["iterations"]["verdict"] == "NOT COMPARABLE")

    # --- the CSV is the deliverable --------------------------------------
    txt = csv_text(good)
    head = txt.splitlines()[0].split(",")
    t("the CSV carries value, basis and verdict in the same row",
      head == ["quantity", "itan0", "itan1", "basis", "verdict"],
      ",".join(head))
    t("every row reaches the CSV", len(txt.splitlines()) == len(good) + 1,
      "%d rows" % (len(txt.splitlines()) - 1))
    t("a failing judgement is still written out, not dropped",
      "DIFFERENT" in csv_text(bad))

    print()
    if _BAD:
        print("SELFTEST FAILED: %s" % "; ".join(_BAD))
        return 1
    print("SELFTEST PASSED (%d checks)" % len(_OK))
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--selftest" in sys.argv or "--check" in sys.argv:
        return selftest()
    if len(args) != 2:
        print(__doc__)
        return 2
    m0, m1 = parse_msg(args[0]), parse_msg(args[1])
    rows = compare(m0, m1)
    base = os.path.basename(args[0]).replace("_ITAN0.msg", "").replace(
        ".msg", "")
    report(rows, base + "_tangent.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
