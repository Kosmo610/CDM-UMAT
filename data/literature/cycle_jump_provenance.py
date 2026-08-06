#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cycle_jump_provenance.py
========================
What refs/[57] and refs/[58] actually prescribe for cycle jumping, and where
our fixed-interval scheme sits against them.

a2 decided (a2-0020) to keep a FIXED cycle-jump interval and record the
limitation, citing refs/[57] and refs/[58] as the sources for that limitation.
That decision is sound, but the reading behind it was incomplete in one way
that matters, and this file records the corrected reading so the thesis prose
cannot be written from the incomplete one.

THE CORRECTION
--------------
a2's note treats both papers as "the better alternative we did not
implement", and says our max_djump plus the three cutbacks already "bound the
damage increment per jump", which is a different layer from Cojocaru's
question of whether the solution replicates the true one.

That is exactly right about refs/[58].  It is NOT right about refs/[57].

refs/[57]'s adaptive criterion IS a bound on the damage increment.  Section
6.1 defines the local cycle jump by imposing "an allowed increase of the
damage variable D", integrating forward with explicit Euler

    D(N + NJUMP1) = D(N) + (dD/dN)|_N * NJUMP1

and picking NJUMP1 so that the increase stays within tolerance -- the paper's
worked example uses dD = 0.01 with D in [0,1].  So our max_djump is not a
different layer from refs/[57]; it is the SAME criterion.  Two things follow,
and both belong in the thesis rather than only in a mailbox message.

  1. refs/[57] can be cited as the SOURCE OF OUR CRITERION, not merely as an
     unimplemented alternative.  That is a stronger citation than the one the
     limitation prose was going to make.

  2. Our tolerance is TEN TIMES LOOSER than their worked example (0.10 vs
     0.01).  A limitation paragraph that says "we used a fixed interval" while
     silently carrying a 10x looser tolerance understates the gap.  The number
     has to appear.

What separates us from refs/[57] is therefore not the criterion but the
MECHANISM: they compute the jump length forward from dD/dN so the interval
adapts, we fix the interval and cut back after the bound is exceeded.
Reactive bounding keeps the damage per increment inside the tolerance; it does
not choose the jump size.  That, precisely stated, is the limitation.

refs/[58] really is a different layer, as a2 said.  Its control function
bounds the change in RATE, not the magnitude of damage:

    |s_p(t1 + dt_jump) - s12(t1)| / |s12(t1)| <= q_y

with s_p linearly extrapolated from the slopes of the last two cycles.
Nothing in our scheme or in refs/[57]'s does this.  So refs/[58] is the honest
citation for "a better method exists and we did not implement it".

MATERIAL PROVENANCE -- why a polymer-matrix paper is admissible here
--------------------------------------------------------------------
refs/[57] validates on plain woven GLASS/EPOXY, and refs/[58] on thermal
barrier coatings.  Neither is a CMC.  Under the project rule that composite
measurements from other systems must not enter the card, that would normally
disqualify them -- but the rule is about MATERIAL DATA, and what we take from
these two is a NUMERICAL INTEGRATION SCHEME.  A tolerance on dD per jump is a
statement about integrating an ODE, not about glass fibres.  Recorded here
explicitly so no future reader mistakes the citation for a material one, and
so nobody harvests a stiffness or a strength out of either paper.

refs/[57] also states a constraint we inherit and should say out loud: a
finite element run can carry only ONE global jump length even when different
integration points want different ones, and their requirements "can be very
contradictory".  Our RVE has exactly that spread -- matrix and yarn damage at
very different rates -- so the single-interval restriction is not an artefact
of our simplification; it survives into the adaptive scheme too.

Run:  python3 data/literature/cycle_jump_provenance.py --check
"""
from __future__ import print_function

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R57 = os.path.join(ROOT, "refs", "[57] 사이클 손상 시간 균질화 S8.pdf")
R58 = os.path.join(ROOT, "refs", "[58] 사이클 손상 시간 균질화 S23.pdf")
RETUNE = os.path.join(ROOT, "abaqus", "retune_deck.py")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def extract(path):
    try:
        out = subprocess.check_output(["pdftotext", "-q", path, "-"],
                                      stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.decode("utf-8", "replace")


# Our value, read from the deck generator rather than typed here.
def our_djump():
    if not os.path.exists(RETUNE):
        return None
    for line in open(RETUNE):
        if line.startswith("D_DJUMP"):
            return float(line.split("=")[1].split("#")[0].strip())
    return None


R57_EXAMPLE_TOL = 0.01      # refs/[57] section 6.1 worked example, D in [0,1]

# Phrases that must survive in the papers.  Short, because the PDFs are old
# scans whose ligatures come out as substitutions (fi -> ï¬, etc).
R57_NEEDLES = [
    ("fixed jumps were what they started with",
     "a ®xed set of simulated"),
    ("and they say fixed is not good enough",
     "an automatic algorithm should be developed"),
    ("their criterion is an allowed increase of the damage variable",
     "impose an allowed increase of the damage variable"),
    ("with 0.01 as the worked example", "limited to, for example, 0.01"),
    ("only one global jump length is possible",
     "no more than one global value of the cycle jump"),
    ("and local requirements can conflict",
     "can be very contradictory"),
    ("validated on glass/epoxy, not a CMC", "woven glass/epoxy"),
]

R58_NEEDLES = [
    ("its control function watches the jump length",
     "control function that automatically monitors"),
    ("and it claims the jump solution replicates the true one",
     "replicates the true solution"),
    ("the criterion is a RELATIVE ERROR on the slope",
     "where qy is a relative error"),
    ("extrapolated linearly from the last two cycles",
     "obtained by linear extrapolation"),
    ("its application is thermal barrier coatings, not a CMC",
     "thermal barrier coatings"),
]


def report():
    print("=" * 76)
    print("cycle_jump_provenance.py -- what [57] and [58] actually prescribe")
    print("=" * 76)

    d = our_djump()
    print("\n 1. the three schemes side by side")
    print("     %-28s %-22s %s" % ("", "what is bounded", "how the jump is set"))
    print("     %-28s %-22s %s"
          % ("refs/[57] Van Paepegem", "damage increment dD",
             "computed forward from dD/dN"))
    print("     %-28s %-22s %s"
          % ("refs/[58] Cojocaru", "change in RATE (slope)",
             "computed from a relative error"))
    print("     %-28s %-22s %s"
          % ("ours (V3_0)", "damage increment dD", "FIXED, cut back on excess"))

    print("\n 2. the tolerance gap")
    if d is not None:
        print("     refs/[57] worked example   dD <= %.2f" % R57_EXAMPLE_TOL)
        print("     ours (D_DJUMP)             dD <= %.2f" % d)
        print("     ratio                      %.0fx looser"
              % (d / R57_EXAMPLE_TOL))
    print("\n 3. so the citation splits")
    print("     refs/[57] -> the SOURCE of our criterion, plus the tolerance")
    print("                  gap and the single-global-jump restriction")
    print("     refs/[58] -> a genuinely different control (rate-based) that")
    print("                  we do not implement")


def check():
    print("\n" + "=" * 76)
    print(" CHECKS")
    print("=" * 76)

    print("\n A. refs/[57] says what we claim it says")
    txt = extract(R57)
    t("refs/[57] is on the shelf and has a text layer", bool(txt),
      "%d chars" % len(txt) if txt else "missing")
    for label, needle in R57_NEEDLES:
        t("  " + label, bool(txt) and needle in txt)

    print("\n B. refs/[58] says what we claim it says")
    t58 = extract(R58)
    t("refs/[58] is on the shelf and has a text layer", bool(t58),
      "%d chars" % len(t58) if t58 else "missing")
    for label, needle in R58_NEEDLES:
        t("  " + label, bool(t58) and needle in t58)

    print("\n C. the correction to a2-0020's reading")
    t("[57]'s criterion is a damage-increment bound, same kind as ours",
      bool(txt) and "impose an allowed increase of the damage variable" in txt,
      "so it is not merely an unimplemented alternative")
    t("[58]'s criterion is a rate bound, a genuinely different layer",
      bool(t58) and "where qy is a relative error" in t58)
    t("the two papers therefore get DIFFERENT citation roles",
      "SOURCE OF OUR CRITERION" in __doc__
      and "did not implement" in __doc__)

    print("\n D. the tolerance gap is real and is read from the generator")
    d = our_djump()
    t("D_DJUMP is read out of abaqus/retune_deck.py", d is not None,
      "%.2f" % d if d is not None else "not found")
    t("ours is 0.10", d is not None and abs(d - 0.10) < 1e-12)
    t("refs/[57]'s worked example is 0.01",
      bool(txt) and "limited to, for example, 0.01" in txt)
    t("so we are 10x looser and the thesis must say so",
      d is not None and abs(d / R57_EXAMPLE_TOL - 10.0) < 1e-9,
      "%.0fx" % (d / R57_EXAMPLE_TOL) if d else "")

    print("\n E. neither paper may supply material data")
    t("[57] is glass/epoxy", bool(txt) and "woven glass/epoxy" in txt)
    t("[58] is thermal barrier coatings",
      bool(t58) and "thermal barrier coatings" in t58)
    t("the file records why a method citation is still admissible",
      "NUMERICAL INTEGRATION SCHEME" in __doc__)
    t("and warns against harvesting properties from them",
      "nobody harvests a stiffness or a strength" in __doc__)

    print("\n F. the restriction that survives into the adaptive scheme")
    t("only one global jump length exists even when locals disagree",
      bool(txt) and "no more than one global value of the cycle jump" in txt)
    t("so our single-interval limitation is not purely our simplification",
      "it survives into the adaptive scheme too" in __doc__)


def main():
    report()
    if "--check" in sys.argv:
        check()
        print("\n" + "=" * 76)
        if _BAD:
            print("FAIL -- %s" % ", ".join(_BAD[:4]))
            print("=" * 76)
            return 1
        print("ALL %d CYCLE-JUMP PROVENANCE CLAIMS HOLD" % len(_OK))
        print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
