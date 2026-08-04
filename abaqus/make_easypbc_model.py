# -*- coding: utf-8 -*-
"""
make_easypbc_model.py   (run INSIDE Abaqus/CAE)
===============================================
Turns one of the *_CAE.inp decks from make_pbc_check.py into a CAE model that the
EasyPBC plug-in can operate on, and -- optionally -- drives the plug-in headlessly.

EasyPBC (Omairey, Dunning & Sriramula, SoftwareX 9 (2019) 100027) builds its own
periodic constraint equations and its own load cases, so it is an *independent*
implementation of the same homogenisation.  Running it on the same mesh and the
same constituents is therefore a real cross-check on our TexGen/Xia constraints:
two different constraint generators, two different postprocessors, one answer.

Run it on the PATCH deck first.  A homogeneous isotropic cell must give back
exactly the E and nu that were typed in, whichever tool computes it -- so that run
tells you whether EasyPBC is set up correctly on this mesh before any composite
number is on the line.

Usage
-----
    abaqus cae noGUI=abaqus/make_easypbc_model.py -- PBC_PATCH_CAE.inp
    abaqus cae noGUI=abaqus/make_easypbc_model.py -- PBC_ELASTIC_CAE.inp --run

    --run       also try to call the EasyPBC kernel directly.  Without it the
                script only builds and saves the .cae, and prints what to click.
    --name X    model name (default: taken from the file name)

Output
------
    <stem>.cae          the CAE model, ready for Plug-ins -> EasyPBC
    prints the part/instance names EasyPBC asks for, and what came through the
    import (sections, materials, orientations, element count).

If --run cannot find or match the plug-in's kernel function it says so and falls
back to the GUI recipe rather than guessing at an API.
"""
from __future__ import print_function

import os
import sys
import glob

from abaqus import mdb, session          # noqa: F401
import assembly                          # noqa: F401
import part                              # noqa: F401


def argv_after_dashdash():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return [a for a in sys.argv[1:] if not a.endswith(".py")]


def import_model(inp, name):
    print("importing %s ..." % inp)
    m = mdb.ModelFromInputFile(name=name, inputFileName=inp)
    print("  model '%s' created" % name)

    parts = list(m.parts.keys())
    print("  parts     : %s" % ", ".join(parts))
    insts = list(m.rootAssembly.instances.keys())
    print("  instances : %s" % ", ".join(insts))
    if not parts or not insts:
        print("  ERROR: the import produced no part/instance -- EasyPBC needs both.")
        return m, None, None

    p = m.parts[parts[0]]
    print("  elements  : %d      nodes: %d" % (len(p.elements), len(p.nodes)))
    print("  materials : %s" % ", ".join(m.materials.keys()))
    print("  sections  : %d" % len(m.sections))

    # Orientations arrive as discrete fields; if they did not survive the import
    # the yarn phase would silently become transversely isotropic in the *global*
    # frame, which is a different material.  Worth knowing before comparing.
    try:
        df = list(m.discreteFields.keys())
    except AttributeError:
        df = []
    n_ori = sum(1 for sa in p.sectionAssignments
                if getattr(sa, "field", "") not in ("", None))
    print("  discrete fields (orientation data): %s" % (", ".join(df) if df else "none"))
    if not df and len(m.materials) > 1:
        print("  WARNING: no discrete field imported.  If this is the two-phase deck,")
        print("           the yarn fibre directions did NOT come through and the")
        print("           EasyPBC result will not be comparable.  Cross-check on the")
        print("           PATCH deck instead, or assign the orientation in CAE.")
    print("  section assignments carrying a field: %d" % n_ori)

    bb = p.nodes.getBoundingBox()
    lo, hi = bb["low"], bb["high"]
    print("  bounding box: (%.5f, %.5f, %.5f) .. (%.5f, %.5f, %.5f) mm"
          % (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2]))
    print("  cell size   : Lx=%.5f  Ly=%.5f  Lz=%.5f mm"
          % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    return m, parts[0], insts[0]


def find_easypbc():
    """Put the usual plug-in directories on sys.path and import the kernel."""
    roots = []
    for env in ("ABAQUS_PLUGIN_PATH", "ABQ_PLUGIN_PATH"):
        if os.environ.get(env):
            roots.extend(os.environ[env].split(os.pathsep))
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "."
    roots += [os.path.join(home, "abaqus_plugins"),
              os.path.join(os.getcwd(), "abaqus_plugins")]
    exe = os.path.dirname(os.path.dirname(sys.executable or ""))
    roots += glob.glob(os.path.join(exe, "**", "abaqus_plugins"))

    for root in roots:
        if not os.path.isdir(root):
            continue
        for cand in [root] + glob.glob(os.path.join(root, "*")):
            if os.path.isdir(cand) and cand not in sys.path:
                sys.path.insert(0, cand)

    try:
        import easypbc                                       # noqa: F401
        return easypbc
    except ImportError as exc:
        print("  EasyPBC kernel not importable (%s)." % exc)
        print("  searched: %s" % ", ".join(r for r in roots if os.path.isdir(r)))
        return None


def call_easypbc(mod, model_name, part_name, inst_name):
    """Best-effort headless call.  The plug-in's kernel signature is not part of
    any published API, so the arguments are matched by name rather than assumed."""
    import inspect

    fn = None
    for cand in ("feasypbc", "easypbc", "run", "main"):
        f = getattr(mod, cand, None)
        if callable(f):
            fn = f
            print("  kernel function: easypbc.%s" % cand)
            break
    if fn is None:
        print("  no callable kernel found in the module; use the GUI.")
        return False

    try:
        spec = inspect.getfullargspec(fn)     # py3
    except AttributeError:
        spec = inspect.getargspec(fn)         # py2 (Abaqus <= 2023)
    names = list(spec.args)
    print("  signature      : %s(%s)" % (fn.__name__, ", ".join(names)))

    # what we know how to supply, keyed by the names plug-ins tend to use
    known = {
        "model": model_name, "modelname": model_name, "mdl": model_name,
        "part": part_name, "partname": part_name, "prt": part_name,
        "inst": inst_name, "instance": inst_name, "instname": inst_name,
        "instancename": inst_name,
        "meshsens": "OFF", "meshsensitivity": "OFF",
        "e": "ON", "g": "ON", "nu": "ON", "cte": "OFF",
        "youngs": "ON", "shear": "ON", "poisson": "ON",
    }
    ndef = len(spec.defaults or ())
    required = names[:len(names) - ndef]

    kwargs, unknown = {}, []
    for a in names:
        key = a.lower().replace("_", "")
        if key in known:
            kwargs[a] = known[key]
        elif a in required:
            unknown.append(a)

    if unknown:
        print("  cannot fill required argument(s): %s" % ", ".join(unknown))
        print("  -> run EasyPBC from the CAE GUI instead (recipe printed below).")
        return False

    print("  calling with   : %s" % kwargs)
    try:
        fn(**kwargs)
    except Exception as exc:                                  # noqa: BLE001
        print("  EasyPBC call failed: %s: %s" % (type(exc).__name__, exc))
        print("  -> run it from the GUI; the model is saved and ready.")
        return False
    print("  EasyPBC finished.  Its report file is written next to the .cae.")
    return True


def gui_recipe(part_name, inst_name):
    print("")
    print("EasyPBC from the CAE GUI")
    print("  1. abaqus cae database=<stem>.cae")
    print("  2. Plug-ins -> EasyPBC")
    print("  3. Part name      : %s" % part_name)
    print("     Instance name  : %s" % inst_name)
    print("  4. Tick Young's modulus, Shear modulus and Poisson's ratio.")
    print("     Leave mesh sensitivity off -- the mesh is fixed here on purpose,")
    print("     because the whole point is to compare two constraint generators on")
    print("     the SAME mesh.")
    print("  5. Run.  EasyPBC creates its own equations, submits its load cases and")
    print("     writes a report with E11/E22/E33, G12/G13/G23 and the Poisson ratios.")
    print("  6. Compare:")
    print("       python3 postprocess/compare_pbc_easypbc.py \\")
    print("           PBC_ELASTIC_constants.csv <EasyPBC report file>")


def main():
    args = argv_after_dashdash()
    files = [a for a in args if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 1
    inp = files[0]
    if not os.path.isfile(inp):
        print("error: %s not found" % inp)
        return 2

    stem = os.path.splitext(os.path.basename(inp))[0]
    name = args[args.index("--name") + 1] if "--name" in args else stem[:38]

    model, part_name, inst_name = import_model(inp, name)
    if part_name is None:
        return 1

    cae = stem + ".cae"
    mdb.saveAs(pathName=cae)
    print("  saved %s" % cae)

    ran = False
    if "--run" in args:
        print("")
        print("locating the EasyPBC plug-in ...")
        mod = find_easypbc()
        if mod is not None:
            ran = call_easypbc(mod, name, part_name, inst_name)

    if not ran:
        gui_recipe(part_name, inst_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
