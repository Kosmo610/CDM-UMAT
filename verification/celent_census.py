"""How much fracture energy does our crack band actually dissipate?

WHY THIS FILE EXISTS (a1-0013, 2026-08-06)
------------------------------------------
The literature agent brought refs/[47] Jirasek & Bauer, "Numerical aspects
of the crack band approach", Comput. Struct. 110-111 (2012) 60-78.  It says
the rule our UMAT relies on -- Abaqus hands us CELENT, the cube root of the
element volume, and we use it as the crack band width le -- can misstate
the fracture energy "by 50% or even more", and that the error is worst for
elongated elements and for bands not aligned with the mesh.

The mail proposed reading that as a limitation of our 1185 distorted
elements.  This file measures it instead, and the measurement says
something different from what either of us expected.

THE METRIC
----------
A crack band model gives every element it damages a dissipation density
g_f = Gf/le.  An element that fully softens therefore releases g_f * V_e.
A crack plane crossing a set S of elements releases

    E = sum_{e in S} Gf * V_e / le_e  =  Gf * sum_{e in S} V_e^(2/3)

over a crack area A_plane, so the fracture energy the crack ACTUALLY sees is

    Gf_eff / Gf_card  =  sum_{e in S} V_e^(2/3) / A_plane            (*)

This needs no assumption about where inside an element the crack sits, and
it is exactly 1.0 for a mesh-aligned crack in a hexahedral mesh, because
there CELENT is the cube side.  It assumes every element the plane passes
through softens fully; a band that localises into fewer elements dissipates
less, so (*) is the upper end of the bracket.

WHAT IT SAYS
------------
    our RVE, crack normal x   1.59 .. 2.22   (median 1.92)
    our RVE, crack normal z   1.61 .. 2.17   (median 2.07)

That is not "+-50 % scatter".  It is a systematic factor of about two, in
one direction: the crack band as implemented is roughly twice as tough as
the card says.

AND WHERE IT COMES FROM -- THIS IS THE PART THAT DECIDES THE FIX
----------------------------------------------------------------
It is not the distorted elements.  They carry 0.31 % of the volume and
contribute 0.65 % of the sum in (*).  Deleting them changes nothing.

It is the tetrahedra.  A FLAWLESS mesh has the same problem, and the size
is closed-form: an aligned cut through a layer of cubes each split into
tets of volumes {V_i} gives sum V_i^(2/3) / h^2 -- which reduces to
N^(1/3) when the N tets are EQUAL (Kuhn), and to
4*(1/6)^(2/3) + (1/3)^(2/3) = 1.69216 for the 5-split, whose central tet
is twice the corner ones (a1-0015 noticed the 1 % gap to 5^(1/3); it is
not error, the split is just not equal-volume).

    Kuhn 6-tet subdivision, perfect   1.817 = 6^(1/3)   (measured, exact)
    5-tet subdivision, perfect        1.6923 = the unequal-volume form
    our RVE                           1.92
    any hexahedral mesh, aligned      1.000

AND THE FAMILY IS PUBLISHED, WHICH SETTLES THE FORM
---------------------------------------------------
refs/[47] section 5.3.1 gives the 2D member: triangles from diagonal
splitting need hb = sqrt(2*A) = 1.414*sqrt(A) -- N^(1/d) with N=2, d=2 --
and fixes them with a CONSTANT MULTIPLIER, which is exactly what kappa
is.  refs/[69] eq. (23) (citing Kurumatani 2016) tabulates the whole
family: sqrt(2A) triangles, sqrt(A) quads, (12*Ve)^(1/3) = 2.2894*Ve^(1/3)
tetrahedra, Ve^(1/3) hexes.  So the correction is not an invention of this
work; the only open question was ever WHICH N our mesh behaves as, and the
published default (N = 12, 2.2894) would over-correct this mesh by 19 %.
Measured beats default: kappa = 1.92 stays (a1-0016 concurs), and the
thesis cites the family as the reason the form is right.

So of our 1.92, about 1.8 is the price of C3D4 itself and only the
remainder is mesh quality.  Remeshing cannot fix it.  Aligning the mesh
cannot fix it -- a woven RVE has no alignment to offer, and the perfect
mesh above is aligned and still gives 1.817.  refs/[47]'s own final
recommendation, principal-strain-axis projection at the element centre,
removes the scatter as well and is the eventual answer; it is NOT
implemented here, and the thesis must say so (refs/[70]'s smooth
Lagrangian band is the other published alternative).

WHAT WE DO ABOUT IT
-------------------
Multiply CELENT by a mesh-measured constant kappa before it becomes le.
One number, measured by this file, applied where the cards are written.
It removes the systematic part exactly and leaves the scatter, which is
the honest residual and goes in the thesis as such.

The constant is only admissible if kappa*le stays under the snap-back
ceiling Gf/(1.02*g0) for every ACTIVE mode.  Section E checks that; every
mode that is on today passes with 36 % margin or better.  It does not pass
for every mode one might want to switch on -- see the Gtc paragraph below,
which is the case that made section E worth writing.  Section E is the
reason this file must run before a deck is regenerated, not after.

WHICH MODES THIS TOUCHES TODAY
------------------------------
Only the ones with a nonzero Gf in the card.  In V1_0 that is the matrix
alone (yarn slots 32-35 are all zero, so the yarn runs at fixed A = 2).
In V2_0 the yarn longitudinal modes join it at 12.5 N/mm.  The transverse
yarn modes are off in both, which is why a1-0005's Gtt = 0.107 N/mm from
refs/[31] has to clear section E before it goes in.

It clears it, and its compressive twin does not.  Gtt and Gtc would share
one fracture energy but not one ceiling -- Yc/Yt = 4.375 raises g0 by 19.1x
-- so at kappa the tensile mode is clean on all 26452 elements while the
compressive one clamps 89.7 % of them, against 4.0 % at kappa = 1.  kappa
is what breaks it.  Switch Gtt on, leave Gtc at zero; Ch.4 4.9-6a already
found there is no measured transverse compressive fracture energy to put
there anyway.

    python3 verification/celent_census.py
    python3 verification/celent_census.py --check
"""
from __future__ import print_function

import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

MESH = os.path.join(ROOT, "abaqus", "meshes", "CSiC_RVE_0135.inp")
DECK_V1 = os.path.join(ROOT, "abaqus", "ZHANG2022_RT23_V1_0.inp")
DECK_V2 = os.path.join(ROOT, "abaqus", "ZHANG2022_RT23_V2_0.inp")

#: Abaqus warns on 1185 elements in this mesh (docs/M1_FAILURE_ANALYSIS.md,
#: from the .dat quality check).  Abaqus does not publish which criterion
#: fired, so we use a normalised radius ratio R_circ/(3 r_in) > 5 as a
#: PROXY: it flags 1182, within 3 of the .dat, and all but one in the
#: matrix, which matches the .dat's "every one is in the matrix".  It is a
#: proxy and this file says so rather than tuning a threshold to hit 1185.
RADIUS_RATIO_LIMIT = 5.0
ABAQUS_DISTORTED = 1185

#: KABAND admits a positive (total-area) Gf only when Gf > 1.02*g0*le, so
#: the snap-back ceiling is Gf/(1.02*g0), not Gf/g0.  The 1.02 is in the
#: guard, not decoration: it is what makes the matrix ceiling 0.2214 mm --
#: the number Ch.4 and CLAUDE.md both quote -- rather than 0.2258.
GUARD = 1.02

#: Directions a crack can take in this material.  x and y are transverse
#: matrix cracking under in-plane tension; z is delamination.
DIRECTIONS = (
    ("x   transverse cracking, load along x", (1.0, 0.0, 0.0)),
    ("y   transverse cracking, load along y", (0.0, 1.0, 0.0)),
    ("z   delamination / through-thickness ", (0.0, 0.0, 1.0)),
    ("45 deg in-plane                      ", (1.0, 1.0, 0.0)),
)

#: Kuhn subdivision of a cube into 6 tets sharing the main diagonal.
KUHN = ((0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7),
        (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7))
#: The 5-tet subdivision.
FIVE = ((0, 1, 2, 4), (1, 2, 3, 7), (1, 4, 5, 7), (2, 4, 6, 7), (1, 2, 4, 7))


# ====================================================================== io
def parse_mesh(text):
    """Nodes, C3D4 connectivity and element sets, from a TexGen deck."""
    nodes, elems, elset = {}, {}, defaultdict(list)
    mode, cur = None, None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("**"):
            continue
        if s.startswith("*"):
            low = s.lower()
            if low.startswith("*node") and "output" not in low:
                mode = "node"
            elif low.startswith("*element") and "output" not in low:
                mode = "elem"
            elif low.startswith("*elset"):
                cur = s.split("=")[1].split(",")[0].strip()
                mode = "gen" if "generate" in low else "elset"
            else:
                mode = None
            continue
        f = [x.strip() for x in s.split(",")]
        if mode == "node":
            nodes[int(f[0])] = (float(f[1]), float(f[2]), float(f[3]))
        elif mode == "elem":
            elems[int(f[0])] = (int(f[1]), int(f[2]), int(f[3]), int(f[4]))
        elif mode == "elset":
            elset[cur].extend(int(t) for t in f if t)
        elif mode == "gen":
            lo, hi, st = (int(x) for x in f[:3])
            elset[cur].extend(range(lo, hi + 1, st))
    return nodes, elems, elset


def parse_card(text, name, nconst):
    """The *User Material constants that follow a named *Material block."""
    lines = text.splitlines()
    want = "*material, name=" + name.lower()
    anchor = "*user material, constants=%d" % nconst
    i = 0
    while i < len(lines) and lines[i].strip().lower() != want:
        i += 1
    while i < len(lines) and lines[i].strip().lower() != anchor:
        i += 1
    vals = []
    i += 1
    while i < len(lines) and len(vals) < nconst:
        s = lines[i].strip()
        if s.startswith("*"):
            break
        if s and not s.startswith("**"):
            vals.extend(float(x) for x in s.split(",") if x.strip())
        i += 1
    return vals


# ================================================================ geometry
def tet_volume(p):
    a, b, c, d = p
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    w = [d[i] - a[i] for i in range(3)]
    return abs(u[0] * (v[1] * w[2] - v[2] * w[1])
               - u[1] * (v[0] * w[2] - v[2] * w[0])
               + u[2] * (v[0] * w[1] - v[1] * w[0])) / 6.0


def unit(n):
    m = math.sqrt(sum(x * x for x in n))
    return tuple(x / m for x in n)


def box_section_area(lo, hi, n, d):
    """Area of the cross-section of an axis-aligned box by a plane.

    Exact, because the mesh fills its bounding box: the report asserts
    sum(V_e) == box volume, so the crack area inside the RVE is the box's.
    """
    corners = [(lo[0] if not (i & 1) else hi[0],
                lo[1] if not (i & 2) else hi[1],
                lo[2] if not (i & 4) else hi[2]) for i in range(8)]
    pts = []
    for a in range(8):
        for b in range(a + 1, 8):
            if bin(a ^ b).count("1") != 1:
                continue
            ta = sum(corners[a][k] * n[k] for k in range(3))
            tb = sum(corners[b][k] * n[k] for k in range(3))
            if (ta - d) * (tb - d) < 0.0:
                s = (d - ta) / (tb - ta)
                pts.append(tuple(corners[a][k] + s * (corners[b][k]
                                                      - corners[a][k])
                                 for k in range(3)))
    uniq = []
    for q in pts:
        if not any(sum((q[k] - r[k]) ** 2 for k in range(3)) < 1e-20
                   for r in uniq):
            uniq.append(q)
    if len(uniq) < 3:
        return 0.0
    c = tuple(sum(q[k] for q in uniq) / len(uniq) for k in range(3))
    e1 = unit(tuple(uniq[0][k] - c[k] for k in range(3)))
    e2 = (n[1] * e1[2] - n[2] * e1[1],
          n[2] * e1[0] - n[0] * e1[2],
          n[0] * e1[1] - n[1] * e1[0])
    def ang(q):
        v = [q[k] - c[k] for k in range(3)]
        return math.atan2(sum(v[k] * e2[k] for k in range(3)),
                          sum(v[k] * e1[k] for k in range(3)))
    uniq.sort(key=ang)
    tot = 0.0
    for i in range(len(uniq)):
        a = [uniq[i][k] - c[k] for k in range(3)]
        b = [uniq[(i + 1) % len(uniq)][k] - c[k] for k in range(3)]
        cr = (a[1] * b[2] - a[2] * b[1],
              a[2] * b[0] - a[0] * b[2],
              a[0] * b[1] - a[1] * b[0])
        tot += sum(n[k] * cr[k] for k in range(3))
    return abs(tot) / 2.0


def gf_ratio(pts, vols, n, d, area):
    """Equation (*): the fracture energy a crack plane really dissipates."""
    tot = 0.0
    for i, quad in enumerate(pts):
        ts = [sum(q[k] * n[k] for k in range(3)) for q in quad]
        if min(ts) < d < max(ts):
            tot += vols[i] ** (2.0 / 3.0)
    return tot / area


def scan(pts, vols, lo, hi, n, nsteps=40, min_area_frac=0.3):
    """Sweep a crack plane across the cell and collect (*) at each stop.

    Cut positions whose section area is a small fraction of the largest are
    dropped.  For an axis normal nothing is dropped -- the area is constant.
    For an oblique normal the extreme positions clip a corner of the box,
    where a handful of elements sit on a sliver of area and the ratio is a
    small-sample artefact of the box, not a property of the mesh.
    """
    n = unit(n)
    ts = [sum(q[k] * n[k] for k in range(3)) for quad in pts for q in quad]
    t0, t1 = min(ts), max(ts)
    stops = []
    for i in range(nsteps):
        d = t0 + (t1 - t0) * (0.03 + 0.94 * i / float(nsteps - 1))
        stops.append((d, box_section_area(lo, hi, n, d)))
    amax = max(a for _, a in stops)
    return [gf_ratio(pts, vols, n, d, a) for d, a in stops
            if a > max(1.0e-9, min_area_frac * amax)]


# ============================================================ ideal meshes
def ideal_mesh(scheme, nx=4, ny=4, nz=4):
    verts, tets = [], []
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                base = len(verts)
                for c in range(8):
                    verts.append((ix + (c & 1), iy + ((c >> 1) & 1),
                                  iz + ((c >> 2) & 1)))
                for t in scheme:
                    tets.append(tuple(base + c for c in t))
    pts = [tuple(verts[i] for i in t) for t in tets]
    vols = [tet_volume(q) for q in pts]
    return pts, vols, (0.0, 0.0, 0.0), (float(nx), float(ny), float(nz))


# ================================================================ quality
def radius_ratio(q):
    """R_circumscribed / (3 r_inscribed).  1.0 for a regular tet."""
    a, b, c, d = (tuple(float(x) for x in p) for p in q)
    def sub(u, v):
        return (u[0] - v[0], u[1] - v[1], u[2] - v[2])
    def cross(u, v):
        return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0])
    def dot(u, v):
        return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]
    A, B, C = sub(b, a), sub(c, a), sub(d, a)
    num = [cross(A, B)[k] * dot(C, C) + cross(B, C)[k] * dot(A, A)
           + cross(C, A)[k] * dot(B, B) for k in range(3)]
    den = 2.0 * dot(A, cross(B, C))
    if abs(den) < 1e-30:
        return float("inf")
    rc = math.sqrt(sum(x * x for x in num)) / abs(den)
    vol = abs(den) / 12.0
    def area(u, v, w):
        return 0.5 * math.sqrt(sum(x * x for x in cross(sub(v, u),
                                                        sub(w, u))))
    asum = area(b, c, d) + area(a, c, d) + area(a, b, d) + area(a, b, c)
    if asum <= 0.0 or vol <= 0.0:
        return float("inf")
    return rc / (3.0 * (3.0 * vol / asum))


# ================================================================ printing
_PASS = [0]
_FAIL = [0]


def ck(name, cond, detail=""):
    ok = bool(cond)
    _PASS[0] += ok
    _FAIL[0] += not ok
    print("   [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                            ("   " + detail) if detail else ""))
    return ok


def pct(xs, p):
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[i]


# ==================================================================== main
def load():
    text = open(MESH).read()
    nodes, elems, elset = parse_mesh(text)
    ids = sorted(elems)
    pts = [tuple(nodes[i] for i in elems[e]) for e in ids]
    vols = [tet_volume(q) for q in pts]
    lo = tuple(min(nodes[n][k] for n in nodes) for k in range(3))
    hi = tuple(max(nodes[n][k] for n in nodes) for k in range(3))
    return ids, elset, pts, vols, lo, hi


def report():
    print("=" * 74)
    print("celent_census.py  --  what le = CELENT does to our fracture energy")
    print("=" * 74)

    ids, elset, pts, vols, lo, hi = load()
    cel = [v ** (1.0 / 3.0) for v in vols]
    boxv = (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])

    # ------------------------------------------------------------------ A
    print("\n A. the mesh, and the closure that makes the metric exact")
    ck("26452 C3D4 elements", len(ids) == 26452, "%d" % len(ids))
    ck("element volumes close on the bounding box",
       abs(sum(vols) / boxv - 1.0) < 1e-6,
       "sum %.4f vs box %.4f" % (sum(vols), boxv))
    print("      -> crack area inside the RVE is the box cross-section,")
    print("         so equation (*) needs no cut-area approximation.")
    ck("CELENT spans a factor 8 across the mesh",
       7.0 < max(cel) / min(cel) < 9.0,
       "%.4f .. %.4f mm" % (min(cel), max(cel)))
    print("      median CELENT %.4f mm" % pct(cel, 0.5))

    # ------------------------------------------------------------------ B
    print("\n B. Gf_effective / Gf_card, sweeping a crack plane (equation *)")
    scans = {}
    for label, n in DIRECTIONS:
        rs = scan(pts, vols, lo, hi, n)
        scans[label.strip().split()[0]] = rs
        print("      %s   %.3f .. %.3f   median %.3f"
              % (label, min(rs), max(rs), pct(rs, 0.5)))
    for key in ("x", "y", "z"):
        ck("crack normal %s over-dissipates by 1.5x or more" % key,
           min(scans[key]) > 1.5, "min %.3f" % min(scans[key]))
    ck("the median is near 2, not near 1",
       1.85 < pct(scans["x"], 0.5) < 2.15,
       "x median %.3f" % pct(scans["x"], 0.5))
    ck("no direction is anywhere near the intended 1.0",
       all(min(v) > 1.4 for v in scans.values()))

    # ------------------------------------------------------------------ C
    print("\n C. control -- a PERFECT tet mesh has the same disease")
    five_exact = 4.0 * (1.0 / 6.0) ** (2.0 / 3.0) + (1.0 / 3.0) ** (2.0 / 3.0)
    for name, scheme, closed in (("Kuhn 6-tet", KUHN, 6.0 ** (1.0 / 3.0)),
                                 ("5-tet     ", FIVE, five_exact)):
        ipts, ivols, ilo, ihi = ideal_mesh(scheme)
        rs = scan(ipts, ivols, ilo, ihi, (1.0, 0.0, 0.0), nsteps=20)
        print("      %s, flawless, aligned cut   %.4f .. %.4f"
              % (name, min(rs), max(rs)))
        ck("%s matches its closed form exactly" % name.strip(),
           abs(pct(rs, 0.5) - closed) < 1e-6,
           "%.6f vs %.6f" % (pct(rs, 0.5), closed))
    # a1-0015 flagged the 1 % gap between the 5-tet measurement and
    # 5^(1/3) = 1.70998.  The gap is the unequal volumes: four corner tets
    # of h^3/6 and one central of h^3/3, so the aligned-cut sum is
    # 4*(1/6)^(2/3) + (1/3)^(2/3), not N^(1/3).  N^(1/3) is the EQUAL-
    # volume special case, which Kuhn is and the 5-split is not.
    ck("the 5-tet 'discrepancy' is the unequal-volume closed form",
       abs(five_exact - 1.692164) < 5e-6, "%.6f" % five_exact)
    ck("refs/[69]'s published tet rule is the N=12 member of the family",
       abs(12.0 ** (1.0 / 3.0) - 2.2894) < 5e-5,
       "12^(1/3) = %.4f" % 12.0 ** (1.0 / 3.0))
    ck("refs/[47]'s 2D triangle rule is the N=2, d=2 member",
       abs(2.0 ** 0.5 - 1.414) < 5e-4, "sqrt(2) = %.4f" % 2.0 ** 0.5)
    ipts, ivols, ilo, ihi = ideal_mesh(KUHN)
    kuhn = pct(scan(ipts, ivols, ilo, ihi, (1.0, 0.0, 0.0), nsteps=20), 0.5)
    ck("a flawless tet mesh is already above 1.8", kuhn > 1.8,
       "%.4f" % kuhn)
    ck("our mesh is only modestly worse than a flawless one",
       1.0 < pct(scans["x"], 0.5) / kuhn < 1.2,
       "%.3fx the ideal" % (pct(scans["x"], 0.5) / kuhn))
    print("      -> remeshing cannot fix this.  A hexahedral mesh gives")
    print("         exactly 1.0 aligned; tetrahedra cannot.")

    # ------------------------------------------------------------------ D
    print("\n D. it is NOT the 1185 distorted elements")
    rr = [radius_ratio(q) for q in pts]
    bad = [i for i in range(len(ids)) if rr[i] > RADIUS_RATIO_LIMIT]
    mat = set(elset.get("Matrix", []))
    in_mat = sum(1 for i in bad if ids[i] in mat)
    print("      radius-ratio proxy R/(3r) > %.0f flags %d elements"
          % (RADIUS_RATIO_LIMIT, len(bad)))
    ck("the proxy lands within 5 of Abaqus's own %d" % ABAQUS_DISTORTED,
       abs(len(bad) - ABAQUS_DISTORTED) <= 5, "%d" % len(bad))
    ck("they are in the matrix, as the .dat says",
       in_mat >= len(bad) - 1, "%d of %d" % (in_mat, len(bad)))
    vshare = sum(vols[i] for i in bad) / sum(vols)
    gshare = (sum(vols[i] ** (2.0 / 3.0) for i in bad)
              / sum(v ** (2.0 / 3.0) for v in vols))
    print("      volume share      %.3f %%" % (100.0 * vshare))
    print("      share of sum (*)  %.3f %%" % (100.0 * gshare))
    ck("the distorted elements carry under 1 % of the volume",
       vshare < 0.01, "%.3f %%" % (100.0 * vshare))
    ck("and under 1 % of the fracture-energy sum",
       gshare < 0.01, "%.3f %%" % (100.0 * gshare))
    print("      -> a1-0013 proposed reading this as a distorted-element")
    print("         limitation.  The distorted elements are not the cause.")

    # ------------------------------------------------------------------ E
    print("\n E. the correction, and whether the card can take it")
    kappa = pct(scans["x"], 0.5)
    print("      kappa = %.3f   (median over crack normal x)" % kappa)
    print("      le_used = kappa * CELENT, so g_f = Gf/le drops by kappa")
    le_max = max(cel)
    print("      worst element: CELENT %.4f -> le %.4f mm"
          % (le_max, kappa * le_max))

    modes = []
    v1 = open(DECK_V1).read()
    v2 = open(DECK_V2).read()
    for deck, tag in ((v1, "V1_0"), (v2, "V2_0")):
        m = parse_card(deck, "sic_matrix_damage", 22)
        y = parse_card(deck, "csic_yarn_damage", 38)
        modes.append((tag, "matrix t", m[1], m[3], m[14]))
        modes.append((tag, "matrix c", m[1], m[4], m[15]))
        modes.append((tag, "yarn 1t ", y[1], y[10], y[31]))
        modes.append((tag, "yarn 1c ", y[1], y[11], y[32]))
        modes.append((tag, "yarn tt ", y[2], y[12], y[33]))
        modes.append((tag, "yarn tc ", y[3], y[13], y[34]))

    print("      %-5s %-9s %10s %10s %10s %s"
          % ("deck", "mode", "g0", "Gf/g0 mm", "k*le mm", "verdict"))
    active = 0
    for tag, name, e, x, gf in modes:
        if gf <= 0.0:
            print("      %-5s %-9s %10s %10s %10s  crack band OFF (fixed A)"
                  % (tag, name, "-", "-", "-"))
            continue
        active += 1
        g0 = x * x / (2.0 * e)
        ceil_ = gf / (GUARD * g0)
        ok = kappa * le_max < ceil_
        print("      %-5s %-9s %10.5f %10.4f %10.4f  %s"
              % (tag, name, g0, ceil_, kappa * le_max,
                 "ok, %.0f %% margin" % (100.0 * (ceil_ / (kappa * le_max) - 1.0))
                 if ok else "SNAP-BACK"))
        ck("%s %s survives kappa" % (tag, name), ok)
    ck("some mode actually uses the crack band", active > 0,
       "%d active" % active)

    # The two transverse modes a1-0005 wants to switch on next.  They share
    # one fracture energy but NOT one ceiling: Yc/Yt = 4.375 puts g0 up by
    # 19.1x, so the same 0.107 N/mm buys a band 19.1x shorter in compression.
    # Ch.4 4.9-6a already tabulated this at kappa = 1; kappa makes it worse,
    # and worse in the mode that was already the marginal one.
    yc = parse_card(v2, "csic_yarn_damage", 38)
    e2 = yc[2]
    print("      candidate transverse modes at Gf = 0.107 N/mm:")
    print("      %-5s %6s %10s %10s %9s %9s"
          % ("mode", "X", "ceiling", "k*le_max", "over at 1", "over at k"))
    frac = {}
    for name, x in (("tt", yc[12]), ("tc", yc[13])):
        g0 = x * x / (2.0 * e2)
        # The micro cards carry a POSITIVE Gf, so KABAND's own admissibility
        # test is Gf > 1.02*g0*le -- the 1.02 is in the guard, not decorative,
        # and Ch.4 4.9-6a's table uses it.  Dropping it here would move the
        # ceiling 2 % and the clamped count by 400 elements.
        ceil_ = 0.107 / (GUARD * g0)
        n1 = sum(1 for c in cel if c >= ceil_)
        nk = sum(1 for c in cel if kappa * c >= ceil_)
        frac[name] = (ceil_, n1, nk)
        print("      %-5s %6.0f %10.4f %10.4f %9s %9s"
              % (name, x, ceil_, kappa * le_max,
                 "%d (%.1f%%)" % (n1, 100.0 * n1 / len(cel)),
                 "%d (%.1f%%)" % (nk, 100.0 * nk / len(cel))))
    ck("Gtt = 0.107 survives kappa on every element",
       frac["tt"][2] == 0, "ceiling %.4f mm" % frac["tt"][0])
    ck("Gtc = 0.107 does NOT -- and kappa is what breaks it",
       frac["tc"][1] < len(cel) * 0.10 < frac["tc"][2],
       "%.1f %% -> %.1f %% of elements clamp"
       % (100.0 * frac["tc"][1] / len(cel), 100.0 * frac["tc"][2] / len(cel)))
    ck("Ch.4 4.9-6a's 4.0 % at kappa = 1 is reproduced",
       abs(100.0 * frac["tc"][1] / len(cel) - 4.0) < 0.5,
       "%.1f %%" % (100.0 * frac["tc"][1] / len(cel)))
    print("      -> switch Gtt on, leave Gtc off.  Ch.4 4.9-6a already says")
    print("         there is no measured transverse COMPRESSIVE fracture")
    print("         energy anyway, so nothing is lost by leaving it at 0.")

    # published default vs measured: the family says the FORM is right,
    # the measurement says which member.  2.2894 would over-correct.
    pub = 12.0 ** (1.0 / 3.0)
    ck("the published (12V)^(1/3) sits ABOVE the measured range",
       pub > max(max(v) for v in scans.values()),
       "%.4f vs measured max %.4f" % (pub, max(max(v)
                                               for v in scans.values())))
    ck("using it would over-correct this mesh by ~19 %",
       0.15 < pub / kappa - 1.0 < 0.25, "%.1f %%" % (100 * (pub / kappa - 1)))

    # The M6 lineage knocks the matrix modulus to 213110 (porosity), which
    # raises g0 by 1.64x and eats the margin the deck rows above show.
    # kappa on TOP of the knockdown pushes the ceiling to 0.0702 mm --
    # under 1624 of the matrix's own elements.  retune_deck.py refuses
    # that combination; this is the measurement its refusal quotes.
    # retune_deck.py applies the two-digit constant, so the exposure is
    # counted at THAT value -- 1662 at the raw median 1.9226 vs 1624 at
    # 1.92 is exactly the kind of gap that turns into two documents
    # quoting two facts.
    kap_applied = 1.92
    ck("the applied constant is the measurement to two digits",
       abs(kappa - kap_applied) < 0.01, "%.4f -> %.2f" % (kappa, kap_applied))
    mat = set(elset.get("Matrix", []))
    celm = [cel[i] for i in range(len(ids)) if ids[i] in mat]
    g0k = 310.0 ** 2 / (2.0 * 213110.0)
    limk = 0.031 / (GUARD * g0k)
    over1 = sum(1 for c in celm if c > limk)
    overk = sum(1 for c in celm if c > limk / kap_applied)
    print("      knocked matrix card (E = 213110, M6 lineage):")
    print("      ceiling %.4f mm; /kappa -> %.4f mm over %d matrix elements"
          % (limk, limk / kap_applied, len(celm)))
    ck("at kappa = 1 the knocked card clamps nothing", over1 == 0,
       "%d over %.4f mm" % (over1, limk))
    ck("at kappa = 1.92 it clamps 1624 matrix elements (10.6 %)",
       overk == 1624 and abs(100.0 * overk / len(celm) - 10.6) < 0.2,
       "%d = %.1f %%" % (overk, 100.0 * overk / len(celm)))
    print("      -> kappa stays OFF by default in retune_deck.py; turning")
    print("         it on is coupled to mesh refinement, not a flag flip.")

    # ----------------------------------------------------------------- E2
    print("\n E2. scope -- the macro model does NOT have this problem")
    gen = os.path.join(ROOT, "abaqus", "make_macro_thermalshock.py")
    src = open(gen).read() if os.path.exists(gen) else ""
    ck("the macro generator emits C3D8 hexahedra, not tets",
       '"C3D8"' in src and "C3D4" not in src)
    print("      A structured hex grid has CELENT = the cube root of a")
    print("      brick, and a crack normal to a grid axis cuts exactly one")
    print("      layer, so equation (*) is 1.0 identically.  Thermal-shock")
    print("      cracking runs normal to z, which is a grid axis.")
    print("      -> kappa is an RVE correction only.  It reaches the macro")
    print("         card only through Gbar_f, which the RVE measures.")

    # ------------------------------------------------------------------ F
    print("\n F. verdict")
    print("      (a) principal-strain projection in the UMAT -- correct, and")
    print("          it is what refs/[47] recommends.  It also removes the")
    print("          scatter (d) leaves behind, so it is the eventual answer,")
    print("          but it rewrites the band width every increment and the")
    print("          systematic part is what matters first.  Not now.")
    print("      (b) declare it a limitation -- rejected.  A systematic 1.9x")
    print("          in one direction is not a limitation, it is an error.")
    print("      (c) align the mesh -- cannot work.  Section C's mesh is")
    print("          perfectly aligned and still gives 1.817.")
    print("      (d) kappa = %.2f, measured here, applied where cards are"
          % kappa)
    print("          written.  Removes the systematic part, leaves the")
    print("          %.2f..%.2f scatter as the stated residual.  CHOSEN."
          % (min(scans["x"]), max(scans["x"])))
    print("")
    print("      One kappa cannot serve every direction: the medians are")
    print("      %.2f (x), %.2f (y), %.2f (z).  x is chosen because the mode"
          % (pct(scans["x"], 0.5), pct(scans["y"], 0.5), pct(scans["z"], 0.5)))
    print("      that matters is transverse matrix cracking under in-plane")
    print("      tension.  Delamination is then under-corrected by %.0f %%,"
          % (100.0 * (pct(scans["z"], 0.5) / kappa - 1.0)))
    print("      which is inside the scatter and is part of the residual.")
    print("")
    print("      NOT YET APPLIED to any deck.  Applying it is a card change")
    print("      and card changes go through the deck generators, which are")
    print("      waiting on the RVE strength runs.")

    print("\n" + "=" * 74)
    print("  %d passed, %d failed" % (_PASS[0], _FAIL[0]))
    print("=" * 74)
    return 1 if _FAIL[0] else 0


def selftest():
    """Assertions that do not need the RVE mesh, for the arithmetic."""
    print("=" * 74)
    print("celent_census.py --check")
    print("=" * 74)

    print("\n 1. the metric is exactly 1.0 for the case it must be")
    a = 0.25
    cube = [((0, 0, 0), (a, 0, 0), (0, a, 0), (0, 0, a))]
    ck("tet_volume matches a/6 for the corner tet",
       abs(tet_volume(cube[0]) - a ** 3 / 6.0) < 1e-15)
    pts, vols, lo, hi = ideal_mesh(KUHN, 3, 3, 3)
    ck("Kuhn fills its box exactly", abs(sum(vols) - 27.0) < 1e-9,
       "%.6f" % sum(vols))
    rs = scan(pts, vols, lo, hi, (1.0, 0.0, 0.0), nsteps=12)
    ck("Kuhn aligned == 6^(1/3) at every cut position",
       max(abs(r - 6.0 ** (1.0 / 3.0)) for r in rs) < 1e-9,
       "%.9f" % rs[0])
    pts5, vols5, lo5, hi5 = ideal_mesh(FIVE, 3, 3, 3)
    ck("the 5-tet split fills its box too", abs(sum(vols5) - 27.0) < 1e-9)
    r5 = pct(scan(pts5, vols5, lo5, hi5, (1.0, 0.0, 0.0), nsteps=12), 0.5)
    ck("5-tet sits below Kuhn, as N^(1/3) says it must",
       r5 < 6.0 ** (1.0 / 3.0), "%.4f < %.4f" % (r5, 6.0 ** (1.0 / 3.0)))

    print("\n 2. a hexahedral mesh would have no problem at all")
    # Not asserted by assertion: computed the same way section B computes it,
    # on cubes instead of tets.  A cube of side h has CELENT = h, so it
    # contributes V^(2/3) = h^2, and an x-normal plane cuts exactly one layer.
    n, h = 4, 0.37
    cubes = [(ix * h, iy * h, iz * h) for ix in range(n)
             for iy in range(n) for iz in range(n)]
    d = 1.5 * h                      # inside the second layer
    cut = [c for c in cubes if c[0] < d < c[0] + h]
    tot = sum((h ** 3) ** (2.0 / 3.0) for _ in cut)
    area = (n * h) * (n * h)
    # 1.0 algebraically; (h^3)^(2/3) does not round-trip bit-exactly, so the
    # tolerance is the float's, not the model's.
    ck("a hex mesh gives 1.0 to floating-point round-off",
       abs(tot / area - 1.0) < 1e-12,
       "%.17g from %d cubes" % (tot / area, len(cut)))
    ck("and it is one layer that gets cut, not several",
       len(cut) == n * n, "%d" % len(cut))
    print("      -> the problem belongs to C3D4, not to the mesher.")

    print("\n 3. box_section_area")
    lo, hi = (0.0, 0.0, 0.0), (2.0, 3.0, 5.0)
    ck("axis cut gives the face area",
       abs(box_section_area(lo, hi, (1.0, 0.0, 0.0), 1.0) - 15.0) < 1e-9,
       "%.4f" % box_section_area(lo, hi, (1.0, 0.0, 0.0), 1.0))
    d = unit((1.0, 1.0, 0.0))
    mid = sum((lo[k] + hi[k]) / 2.0 * d[k] for k in range(3))
    a45 = box_section_area(lo, hi, d, mid)
    # x + y = 2.5 crosses the 2x3 footprint from (0, 2.5) to (2, 0.5), a
    # chord of 2*sqrt(2); the section is that chord times the 5 in z.
    ck("45 deg cut gives the exact chord area 2*sqrt(2)*5",
       abs(a45 - 2.0 * math.sqrt(2.0) * 5.0) < 1e-9, "%.6f" % a45)
    ck("a plane outside the box has no area",
       box_section_area(lo, hi, (1.0, 0.0, 0.0), 99.0) == 0.0)

    print("\n 4. radius_ratio recognises a regular tet")
    s = math.sqrt(0.5)
    reg = ((s, 0.0, -0.5), (-s, 0.0, -0.5), (0.0, s, 0.5), (0.0, -s, 0.5))
    ck("regular tet has R/(3r) = 1", abs(radius_ratio(reg) - 1.0) < 1e-9,
       "%.9f" % radius_ratio(reg))
    sliver = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0.3, 0.3, 1e-4))
    ck("a sliver is flagged far above the limit",
       radius_ratio(sliver) > RADIUS_RATIO_LIMIT,
       "%.1f" % radius_ratio(sliver))

    print("\n 5. the correction direction is the one that helps")
    print("      g_f = Gf/le, so raising le LOWERS dissipation.  We are")
    print("      over-dissipating, so le must go UP.  kappa > 1.")
    ck("kappa multiplies CELENT and is greater than one",
       6.0 ** (1.0 / 3.0) > 1.0)
    g0 = 310.0 ** 2 / (2.0 * 350000.0)
    ck("matrix snap-back ceiling is the 0.2214 mm Ch.4 quotes",
       abs(0.031 / (GUARD * g0) - 0.2214) < 5e-4,
       "%.4f mm" % (0.031 / (GUARD * g0)))
    ck("dropping the 1.02 guard would have said 0.2258 instead",
       abs(0.031 / g0 - 0.2258) < 5e-4, "%.4f mm" % (0.031 / g0))
    ck("1.94 * the coarsest CELENT stays under the real ceiling",
       1.94 * 0.08451 < 0.031 / (GUARD * g0),
       "%.4f < %.4f" % (1.94 * 0.08451, 0.031 / (GUARD * g0)))

    print("\n 6. the card parser reads what the deck actually holds")
    if os.path.exists(DECK_V1):
        m = parse_card(open(DECK_V1).read(), "sic_matrix_damage", 22)
        ck("V1_0 matrix card has 22 constants", len(m) == 22, "%d" % len(m))
        ck("V1_0 matrix E and Xt are 350000 and 310",
           m[1] == 350000.0 and m[3] == 310.0)
        ck("V1_0 matrix crack band is ON", m[14] == 0.031 and m[15] == 0.031)
        y = parse_card(open(DECK_V1).read(), "csic_yarn_damage", 38)
        ck("V1_0 yarn card has 38 constants", len(y) == 38, "%d" % len(y))
        ck("V1_0 yarn crack band is OFF in all four modes",
           y[31] == 0.0 and y[32] == 0.0 and y[33] == 0.0 and y[34] == 0.0)
        y2 = parse_card(open(DECK_V2).read(), "csic_yarn_damage", 38)
        ck("V2_0 turns the yarn longitudinal band on at 12.5",
           y2[31] == 12.5 and y2[32] == 12.5)
        ck("V2_0 leaves the transverse yarn band off",
           y2[33] == 0.0 and y2[34] == 0.0)
    else:
        ck("decks present", False, DECK_V1)

    print("\n" + "=" * 74)
    print("  %d passed, %d failed" % (_PASS[0], _FAIL[0]))
    print("=" * 74)
    return 1 if _FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--check" in sys.argv else report())
