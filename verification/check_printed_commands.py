#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_printed_commands.py -- a command we print has to be a command that runs
=============================================================================
    python3 verification/check_printed_commands.py

Scripts in this repository tell the user what to run next.  Those strings are
the only instructions a user standing at a console actually sees, and nothing
was checking them.  On 2026-08-18 postprocess/damage_ceiling.py was found
telling people

    abaqus python damage_map.py <job>.odb <job>.inp

while damage_map.py declares ONE positional argument, so argparse answers
"unrecognized arguments" and the user is stopped by a dead end we printed
ourselves -- at exactly the moment they are already stuck, since that hint
only appears when a damage map predates volfrac_at_cap.

Three things are checkable without running anything, and all three have bitten
this project:

  1. THE FILE EXISTS.  A renamed or never-written script is a dead end.
  2. THE INTERPRETER IS RIGHT.  A script that imports odbAccess runs only
     under `abaqus python`; one that needs numpy/matplotlib runs only under
     plain python.  CLAUDE.md 3-1 calls swapping them "immediate error", and
     the swap is invisible in the printed string.
  3. THE ARITY IS RIGHT.  More positionals than the target's parser declares
     is the damage_ceiling defect.  Fewer is usually fine (argparse nargs="?"
     and the script's own usage message), so only the excess is an error.

Cross-file references are what this is for.  A script quoting its OWN usage
line cannot drift out of step with itself in the same way, so those are
reported but not failed on arity.
"""
from __future__ import print_function

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCAN_DIRS = ("postprocess", "abaqus", "verification", "data")

#: This file is the only one excluded, and it has to be: its docstring quotes
#: the broken command it exists to catch, and section D rebuilds that command
#: deliberately.  An auditor that documents counter-examples will always fail
#: its own audit.  The exclusion is pinned to exactly one name below so that
#: nobody can quietly widen it to silence a real finding.
SELF_EXEMPT = ("check_printed_commands.py",)

#: `abaqus python foo.py a b` / `python3 foo.py a` / `python foo.py a`
CMD_RE = re.compile(
    r"(?P<how>abaqus\s+python|python3|python)\s+(?P<script>[A-Za-z0-9_]+\.py)"
    r"(?P<rest>[^\n\"']*)")

#: tokens that are options or prose, not positional arguments
OPT_RE = re.compile(r"^-")
PROSE_RE = re.compile(r"^[^\w<\[/.]|^\.\.\.$|←|→|#")

_OK, _BAD = [], []


def t(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


def py_files():
    out = {}
    for d in SCAN_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, d)):
            dirnames[:] = [x for x in dirnames if x != "__pycache__"]
            for fn in filenames:
                if fn.endswith(".py"):
                    out.setdefault(fn, os.path.join(dirpath, fn))
    return out


def positionals(src):
    """Names of positional arguments an argparse-based script declares.

    Returns None when the script does not use argparse -- arity cannot be
    judged then, and guessing would be worse than declining.
    """
    if "add_argument(" not in src:
        return None
    names = []
    for m in re.finditer(r'add_argument\(\s*"([^"]+)"', src):
        if not m.group(1).startswith("-"):
            names.append(m.group(1))
    return names


def needs_abaqus(src):
    """True when the script imports odbAccess, directly or in a try block."""
    return bool(re.search(r"^\s*(from|import)\s+odbAccess", src, re.M))


def needs_plain(src):
    """True when the script needs a package Abaqus' bundled python lacks."""
    return bool(re.search(r"^\s*import\s+matplotlib", src, re.M))


def args_of(rest):
    """Positional-looking tokens after the script name."""
    out = []
    for tok in rest.split():
        if OPT_RE.match(tok) or PROSE_RE.match(tok):
            break
        out.append(tok)
    return out


def scan():
    files = py_files()
    hits = []
    for fn, path in sorted(files.items()):
        if fn in SELF_EXEMPT:
            continue
        src = open(path, encoding="utf-8").read()
        for m in CMD_RE.finditer(src):
            target = m.group("script")
            hits.append(dict(where=fn, where_path=path, target=target,
                             how=m.group("how"), args=args_of(m.group("rest")),
                             self=(target == fn)))
    return files, hits


def check():
    print("=" * 78)
    print("check_printed_commands.py -- printed instructions must be runnable")
    print("=" * 78)
    files, hits = scan()
    cross = [h for h in hits if not h["self"]]
    print("\n  %d printed commands in %d files; %d of them name ANOTHER script"
          % (len(hits), len(set(h["where"] for h in hits)), len(cross)))

    print("\n A. every script named actually exists")
    missing = sorted(set(h["target"] for h in hits if h["target"] not in files))
    t("no printed command names a script that is not in the repo",
      not missing, ", ".join(missing))

    print("\n B. the interpreter matches what the target imports")
    for h in sorted(cross, key=lambda x: (x["where"], x["target"])):
        if h["target"] not in files:
            continue
        tsrc = open(files[h["target"]], encoding="utf-8").read()
        abq = h["how"].startswith("abaqus")
        if needs_abaqus(tsrc):
            t("%s -> %s needs abaqus python" % (h["where"], h["target"]), abq,
              "imports odbAccess, which plain python cannot import")
        elif needs_plain(tsrc):
            t("%s -> %s needs plain python" % (h["where"], h["target"]),
              not abq, "imports matplotlib, which abaqus python lacks")

    print("\n C. no printed command passes more positionals than declared")
    for h in sorted(cross, key=lambda x: (x["where"], x["target"])):
        if h["target"] not in files:
            continue
        pos = positionals(open(files[h["target"]], encoding="utf-8").read())
        if pos is None:
            continue
        n = len(h["args"])
        t("%s -> %s passes %d, parser declares %d"
          % (h["where"], h["target"], n, len(pos)),
          n <= len(pos),
          "" if n <= len(pos) else
          "argparse would answer 'unrecognized arguments'; declared: %s"
          % ", ".join(pos))

    print("\n D. the check would catch the defect it was written for")
    # Rebuild the exact 2026-08-18 defect and confirm it fails.
    dm = files.get("damage_map.py")
    t("damage_map.py is found and uses argparse", dm and
      positionals(open(dm, encoding="utf-8").read()) == ["odb"],
      "declares %s" % positionals(open(dm, encoding="utf-8").read()))
    bad = args_of(" <job>.odb <job>.inp")
    t("  the old hint's two positionals exceed the declared one",
      len(bad) == 2 and len(bad) > 1, "%s" % bad)
    good = args_of(" <job>.odb")
    t("  and the corrected hint does not", len(good) == 1, "%s" % good)
    t("  an odbAccess script is refused under plain python",
      needs_abaqus(open(dm, encoding="utf-8").read()),
      "so 'python damage_map.py ...' would be caught by B")
    t("  a matplotlib script is refused under abaqus python",
      any(needs_plain(open(p, encoding="utf-8").read())
          for p in files.values()),
      "at least one such script exists to be protected")

    print("\n E. the exemption is exactly one file, and it is this one")
    t("only one file is exempt from the scan", len(SELF_EXEMPT) == 1,
      "%s" % (SELF_EXEMPT,))
    t("  and it is this auditor, which must quote counter-examples",
      SELF_EXEMPT == (os.path.basename(__file__),),
      "widening this list would silence real findings, not fix them")
    t("  the exempt file really does contain a command that would fail",
      "damage_map.py <job>.odb <job>.inp" in open(__file__,
                                                  encoding="utf-8").read(),
      "the 2026-08-18 defect, kept as the worked example")

    print("\n F. prose and options are not mistaken for arguments")
    t("an option stops the argument scan", args_of(" x.odb --axis z") == ["x.odb"])
    t("a trailing arrow is not an argument",
      args_of(" <job>.odb   ← gate") == ["<job>.odb"])
    t("an ellipsis is not an argument", args_of(" ...") == [])
    t("a comment marker stops it", args_of(" a.odb  # note") == ["a.odb"])


def main(argv):
    check()
    print("\n" + "=" * 78)
    if _BAD:
        print("FAIL -- %s" % "; ".join(n for n in _BAD[:3]))
        print("=" * 78)
        return 1
    print("ALL %d PRINTED-COMMAND CHECKS PASS "
          "(what we tell the user to run, runs)" % len(_OK))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
