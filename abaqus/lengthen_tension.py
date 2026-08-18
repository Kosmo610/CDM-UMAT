#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lengthen_tension.py -- give the tension step a softening branch to record
========================================================================
    python3 abaqus/lengthen_tension.py --check
    python3 abaqus/lengthen_tension.py IN.inp -o OUT.inp --span-factor 3

M7's decks inherited M6's applied strain, because retune_deck.detect_case
reads it out of the source deck so that a retune cannot silently change the
case.  That is the right default and the wrong answer here.  Measured off the
three M6 odbs, the tension step spans:

    RT23    0.4679 %   peak at 0.4679 %   ->  0.0000 % past peak
    T500    0.4828 %   peak at 0.2979 %   ->  died at 75.2 % of the step
    T1000   0.4816 %   peak at 0.2295 %   ->  0.2522 % past peak, fell 16.6 %

RT23's step ends EXACTLY at its own peak.  It converges, completes, reports
success, and yields a fracture energy of zero -- and no amount of
stabilisation changes that, because the step is simply too short.  M7 as
shipped would repeat it.

So this tool lengthens ONLY the tension step, and the whole point is that it
can prove it did nothing else.  Three lines change, all inside
*Step, Name=Tension_at_*:

    *Step ... inc=2000              -> inc=<budget for the longer path>
    <dt0>, 1.0, <min>, 0.0025       -> max TIME increment divided by the same
                                       factor, so the strain per increment on
                                       the softening branch stays where M6
                                       had it
    ConstraintsDriver0, 1, 1, <eps> -> the strain that reaches the branch

Everything else -- mesh, PBC, orientations, every card, the cooldown and
reheat steps -- is byte-identical, and check() asserts exactly that against
the real shipped M7 decks.

Why x3: fitting sigma = X exp(-k (eps - eps_pk)) to the only trustworthy
branch (T1000: 0.25 % long, 16.6 % fall) gives k = 84.1 /strain, so half of
peak is ln2/k = 0.824 % past the peak.  Tripling each span clears that with
margin in all three cases (0.94 / 1.15 / 1.22 % past peak).  T500's apparent
k = 4.0 is fitted to a 0.065 % arc that fell 0.3 % -- the flat top of the
curve, where the slope is near zero by construction.  It is not a decay rate
and nothing is designed to it.
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from retune_deck import (D_MAXINC, EPS_SPAN_FACTOR,          # noqa: E402
                         M6_POST_COOLDOWN, eps_for_span)

STEP_RE = re.compile(r"^\*Step,\s*Name=Tension_at_(\d+)C[^\n]*$", re.M)
END_RE = re.compile(r"^\*End Step\s*$", re.M)

#: increments budgeted for the longer path.  1/maxinc increments would do it
#: with no cutbacks at all; softening guarantees cutbacks, so this is that
#: number with room, and still far below the 10000 that let two M1 jobs crawl
#: for 15 h before dying.
INC_BUDGET = 4000


def tension_block(text):
    """(start, end) character offsets of the tension step, end exclusive."""
    m = STEP_RE.search(text)
    if not m:
        raise ValueError("no '*Step, Name=Tension_at_<T>C' in this deck")
    e = END_RE.search(text, m.end())
    if not e:
        raise ValueError("tension step has no *End Step")
    return m.start(), e.end(), int(m.group(1))


def lengthen(text, factor=EPS_SPAN_FACTOR, post_cooldown=None,
             inc=INC_BUDGET):
    """Return (new_text, info).  Only the tension step is touched."""
    i, j, T = tension_block(text)
    blk = text[i:j]

    m = re.search(r"ConstraintsDriver0,\s*1,\s*1,\s*([0-9.eE+-]+)", blk)
    if not m:
        raise ValueError("tension step has no ConstraintsDriver0 *Boundary")
    eps_old = float(m.group(1))
    u0 = (M6_POST_COOLDOWN.get(T) if post_cooldown is None else post_cooldown)
    if u0 is None:
        raise ValueError("no post-cooldown driver strain known for T=%d; "
                         "pass --post-cooldown" % T)
    span_old = eps_old - u0
    if span_old <= 0.0:
        raise ValueError("the deck's strain %.6g is at or below the "
                         "post-cooldown state %.6g -- the step would run "
                         "backwards" % (eps_old, u0))
    eps_new = eps_for_span(T, factor * span_old, u0)

    new = blk
    new = new.replace("ConstraintsDriver0, 1, 1, %s" % m.group(1),
                      "ConstraintsDriver0, 1, 1, %.6f" % eps_new)
    # the *Static data line: <dt0>, <period>, <min>, <max>
    sm = re.search(r"^([0-9.eE+-]+),\s*1\.0,\s*([0-9.eE+-]+),\s*([0-9.eE+-]+)$",
                   new, re.M)
    if not sm:
        raise ValueError("tension step has no *Static data line")
    maxinc_new = float(sm.group(3)) / factor
    new = new.replace(sm.group(0), "%s, 1.0, %s, %g"
                      % (sm.group(1), sm.group(2), maxinc_new))
    new = re.sub(r"(\*Step,\s*Name=Tension_at_\d+C[^\n]*?)inc=\d+",
                 r"\g<1>inc=%d" % inc, new, count=1)

    return text[:i] + new + text[j:], dict(
        T=T, eps_old=eps_old, eps_new=eps_new, u0=u0,
        span_old=span_old, span_new=factor * span_old,
        maxinc_old=float(sm.group(3)), maxinc_new=maxinc_new,
        dstrain_old=float(sm.group(3)) * span_old,
        dstrain_new=maxinc_new * factor * span_old, inc=inc)


def changed_lines(a, b):
    """[(line_a, line_b)] for equal-length texts compared line by line."""
    la, lb = a.splitlines(), b.splitlines()
    if len(la) != len(lb):
        return [("<%d lines>" % len(la), "<%d lines>" % len(lb))]
    return [(x, y) for x, y in zip(la, lb) if x != y]


# --------------------------------------------------------------------------
_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-62s %s" % ("PASS" if cond else "FAIL", name, detail))


def check():
    print("=" * 78)
    print("lengthen_tension.py -- only the tension step, and provably so")
    print("=" * 78)

    # A synthetic deck first, so the checks do not depend on a dist/ zip.
    deck = "\n".join([
        "*Heading", " test", "*Node", "1, 0., 0., 0.",
        "*Step, Name=Manufacturing_Cooling, nlgeom=NO, inc=2000",
        "cool", "*Static, stabilize=0.001, allsdtol=0.05, continue=NO",
        "0.001, 1.0, 1e-08, 0.0025", "*Boundary", "AllNodes, 11, 11, 23.",
        "*End Step",
        "*Step, Name=Tension_at_23C, nlgeom=NO, inc=2000",
        "pull", "*Static, stabilize=0.001, allsdtol=0.05, continue=NO",
        "0.0005, 1.0, 1e-08, 0.0025",
        "*Boundary", "ConstraintsDriver0, 1, 1, 0.001500",
        "ConstraintsDriver3, 1, 1, 0.0", "*End Step", ""])
    out, info = lengthen(deck)

    print("\n A. what moved")
    ch = changed_lines(deck, out)
    t("exactly three lines change", len(ch) == 3,
      "; ".join("%s -> %s" % (a.strip(), b.strip()) for a, b in ch))
    t("  the applied strain", any("ConstraintsDriver0" in a for a, _ in ch),
      "%.6f -> %.6f  (span %.4f %% -> %.4f %%)"
      % (info["eps_old"], info["eps_new"], 100 * info["span_old"],
         100 * info["span_new"]))
    t("  the max time increment", any(a.startswith("0.0005,") for a, _ in ch),
      "%g -> %g" % (info["maxinc_old"], info["maxinc_new"]))
    t("  and the increment budget", any("inc=" in a for a, _ in ch),
      "2000 -> %d" % info["inc"])
    t("the strain per increment is UNCHANGED, which is the point",
      abs(info["dstrain_new"] - info["dstrain_old"]) < 1e-15,
      "%.4e both before and after -- a longer step, not a coarser one"
      % info["dstrain_new"])

    print("\n B. the cooldown step is not touched")
    cool_in = deck[deck.index("*Step, Name=Manufacturing"):
                   deck.index("*Step, Name=Tension")]
    cool_out = out[out.index("*Step, Name=Manufacturing"):
                   out.index("*Step, Name=Tension")]
    t("byte-identical cooldown block", cool_in == cool_out,
      "its 0.0025 and its inc=2000 both survive")
    t("  and the shear lock in the tension step survives",
      "ConstraintsDriver3, 1, 1, 0.0" in out)

    print("\n C. it refuses what it cannot do")
    for name, bad, msg in (
            ("a deck with no tension step",
             deck.replace("Tension_at_23C", "Probe_at_23C"), "Tension_at"),
            ("a strain already below the post-cooldown state",
             deck.replace("0.001500", "-0.009000"), "backwards")):
        try:
            lengthen(bad)
            raised = ""
        except ValueError as exc:
            raised = str(exc)
        t(name + " is refused", msg in raised, raised[:70])

    print("\n D. the real M7 decks, if they are here")
    zp = os.path.join(ROOT, "dist", "LTH_M7_0816_2022.zip")
    if not os.path.exists(zp):
        t("dist/LTH_M7_0816_2022.zip present", False, "skipping D")
        return
    import zipfile
    want = {"LTH_M7_RT23.inp": (23, 0.0015),
            "LTH_M7_T500.inp": (500, 0.0032),
            "LTH_M7_T1000.inp": (1000, 0.0048)}
    with zipfile.ZipFile(zp) as z:
        for nm, (T, eps0) in sorted(want.items()):
            member = [m for m in z.namelist() if m.endswith("/" + nm)]
            if not member:
                t("%s in the zip" % nm, False)
                continue
            src = z.read(member[0]).decode("ascii", "replace")
            new, info = lengthen(src)
            ch = changed_lines(src, new)
            t("%-18s changes exactly three lines" % nm, len(ch) == 3,
              "%d" % len(ch))
            t("  and it is the tension step's, not the cooldown's",
              all(t_ in tension_block_text(new) for t_, _ in
                  [(b, None) for _, b in ch]),
              "span %.4f %% -> %.4f %%, %.4f %% past the M6 peak"
              % (100 * info["span_old"], 100 * info["span_new"],
                 100 * (info["span_new"] - {23: 0.004679, 500: 0.002979,
                                            1000: 0.002295}[T])))
            t("  the deck really did carry M6's strain",
              abs(info["eps_old"] - eps0) < 1e-9, "%.6f" % info["eps_old"])
            t("  and the new one clears the 0.824 %% the fit asks",
              info["span_new"] - {23: 0.004679, 500: 0.002979,
                                  1000: 0.002295}[T] > 0.00824)


def tension_block_text(text):
    i, j, _T = tension_block(text)
    return text[i:j]


def main(argv):
    if "--check" in argv or "--selftest" in argv:
        check()
        print("\n" + "=" * 78)
        if _BAD:
            print("FAIL -- %s" % ", ".join(n.strip() for n in _BAD[:3]))
            print("=" * 78)
            return 1
        print("ALL %d TENSION-LENGTHENING CHECKS PASS "
              "(three lines, all in the tension step)" % len(_OK))
        print("=" * 78)
        return 0
    if not argv:
        print(__doc__)
        return 2
    src_path = argv[0]
    out_path = None
    factor = EPS_SPAN_FACTOR
    u0 = None
    i = 1
    while i < len(argv):
        if argv[i] in ("-o", "--out"):
            out_path = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--span-factor":
            factor = float(argv[i + 1])
            i += 2
            continue
        if argv[i] == "--post-cooldown":
            u0 = float(argv[i + 1])
            i += 2
            continue
        i += 1
    with open(src_path) as f:
        src = f.read()
    new, info = lengthen(src, factor, u0)
    out_path = out_path or (os.path.splitext(src_path)[0] + "_LONG.inp")
    with open(out_path, "w") as f:
        f.write(new)
    ch = changed_lines(src, new)
    print("%s -> %s" % (src_path, out_path))
    print("  T = %d C, post-cooldown driver %.6f" % (info["T"], info["u0"]))
    print("  strain    %.6f -> %.6f   (span %.4f %% -> %.4f %%, x%.1f)"
          % (info["eps_old"], info["eps_new"], 100 * info["span_old"],
             100 * info["span_new"], factor))
    print("  max inc   %g -> %g   (strain per increment %.4e, unchanged)"
          % (info["maxinc_old"], info["maxinc_new"], info["dstrain_new"]))
    print("  budget    inc = %d" % info["inc"])
    print("  changed   %d line(s), all inside the tension step" % len(ch))
    for a, b in ch:
        print("      - %s" % a.strip())
        print("      + %s" % b.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
