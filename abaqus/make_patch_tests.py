#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_patch_tests.py
===================
Write the two small verification jobs that Ch.3 §3.8 lists as missing:

  A. PATCH TEST of the periodic boundary conditions       -> PATCH_PBC.inp
  B. CRACK-BAND MESH OBJECTIVITY demonstration            -> CBAND_N5/N10/N20.inp

Both are deliberately tiny.  Their value is not in the physics -- it is in
separating one question from another so that a later disagreement has only one
possible cause.

A. WHY A PATCH TEST, AND WHY IT USES NO UMAT
--------------------------------------------
The RVE answer depends on two things that are easy to confuse: the periodic
boundary conditions and the constitutive law.  If the RVE gives a wrong
effective stiffness there is no way to tell which one is at fault.

So this deck gives BOTH phases the SAME isotropic elastic material and does not
call the UMAT at all -- just *Elastic.  A homogeneous body under a prescribed
uniform macro strain has an exact answer, so any deviation is the periodic-BC
implementation and nothing else.

  steps 1-6   one unit macro strain component each, the other five HELD AT
              ZERO.  That is a uniaxial-STRAIN state, so the six driver
              reactions of step k are column k of the stiffness matrix, and
              the whole 6x6 must come back as the analytic isotropic C.
  step 7      uniform heating with every driver FREE.  A homogeneous body that
              is free to expand must develop EXACTLY ZERO stress, and the
              drivers must move by alpha*dT.  This is the sharpest of the
              seven: a sign error or a missing edge/corner equation in the PBC
              shows up as self-stress that has nowhere to come from.

Analytic answers for E = 100000 MPa, nu = 0.30, alpha = 5e-6 /K:
    C11 = 134615.384615    C12 = 57692.307692    C44 = 38461.538462  MPa
    step 1: sig11 = 134.615385, sig22 = sig33 = 57.692308 MPa
    step 4: sig12 = 38.461538 MPa
    step 7: |sig| = 0 and U(driver 0..2) = 5.0e-4

B. WHY A BAR, NOT A SECOND RVE
------------------------------
Crack-band regularisation claims that halving the element size does not change
the dissipated energy, because the softening factor A is recomputed from the
element size so that g_f * l_e = G_f.  Ch.3 asserts this; nobody has shown it.

Showing it on the RVE would need a second TexGen mesh, which is not available
here.  It does not need one: the claim is a property of the constitutive law,
so the classical one-dimensional demonstration is the right test and it runs in
seconds.

  A bar 1.0 mm long, 0.2 x 0.2 mm section, meshed with CUBIC C3D8 elements at
  three densities.  Keeping the elements cubic matters -- Abaqus reports
  CELENT for a hexahedron as the cube root of its volume, so a bar meshed with
  flat elements would feed the crack band a length that is not the element
  length along the bar, and the test would measure the wrong thing.

    N=5   h = 0.200 mm   1x1 across    5 elements
    N=10  h = 0.100 mm   2x2 across   40 elements
    N=20  h = 0.050 mm   4x4 across  320 elements

  One slice of elements is given a material 20 % weaker so the localisation
  band is chosen by the model, not by round-off.  All three h are below the
  snap-back limit Gf/(1.02*g0) = 0.2214 mm for this matrix.

  THE IMPERFECTION USED TO BE 5 % AND THAT WAS NOT ENOUGH.  On 2026-08-03 the
  three bars ran to completion and cband_damage.py found damage in 3 of 5 rows
  at N=5 but 10 of 10 and 20 of 20 at N=10 and N=20: the finer meshes damaged
  the WHOLE bar.  With no band there is nothing for the crack-band
  regularisation to be objective about, and the 33.6 % energy spread measured
  nothing.  The lesson is that a localisation demonstration has to be shown to
  have localised before its energies mean anything -- which is why
  cband_damage.py now runs before any energy is quoted.

  EXPECTED: the force-displacement curves coincide, the peak force is the
  same, and the dissipated energy equals G_f x area regardless of N.  If the
  crack band were absent the dissipated energy would fall by 4x from N=5 to
  N=20.

Usage
  python3 make_patch_tests.py --deck <assembled RVE deck>.inp   # A and B
  python3 make_patch_tests.py --bar-only                        # B only
  python3 make_patch_tests.py --check                           # self-test
"""
from __future__ import print_function

import argparse
import os
import re
import sys

# ---------------------------------------------------------------- patch test
PATCH_E, PATCH_NU, PATCH_ALPHA = 100000.0, 0.30, 5.0e-6
PATCH_STRAIN = 1.0e-3
PATCH_DT = 100.0
MAT_ANCHOR = "*Material, Name=SIC_MATRIX_DAMAGE"

MODE_NAME = ["eps11", "eps22", "eps33", "gam12", "gam13", "gam23"]


def isotropic_C(E, nu):
    lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    mu = E / (2.0 * (1.0 + nu))
    C = [[0.0] * 6 for _ in range(6)]
    for i in range(3):
        for j in range(3):
            C[i][j] = lam + (2.0 * mu if i == j else 0.0)
    for i in range(3, 6):
        C[i][i] = mu
    return C


def patch_deck(mesh_head, sections):
    """Assemble the PBC patch deck from an existing RVE mesh + PBC block."""
    L = [mesh_head.rstrip("\n"),
         "*Material, Name=PATCH_ISO",
         "*Elastic",
         "%g, %g" % (PATCH_E, PATCH_NU),
         "*Expansion",
         "%g," % PATCH_ALPHA]
    # every section gets the same material; drop any orientation, the
    # material is isotropic so an orientation would only hide a mistake
    for s in sections:
        elset = re.search(r"ElSet\s*=\s*([A-Za-z0-9_]+)", s, re.I).group(1)
        L.append("*Solid Section, ElSet=%s, Material=PATCH_ISO" % elset)
        L.append("1.0,")
    L.append("*Initial Conditions, type=TEMPERATURE")
    L.append("AllNodes, 0.")

    # Nodal U and RF go into the FIELD output as well as the history output.
    # It costs almost nothing on a deck this size and it means a reader that
    # cannot match a historyRegion can still recover the driver reactions from
    # the last frame -- i.e. a post-processing bug never costs a re-run.
    out = """*Output, field
*Element Output, directions=YES
S, E
*Node Output
U, RF
*Output, history, frequency=1
""" + "\n".join("*Node Output, nset=ConstraintsDriver%d\nU, RF" % i
                for i in range(6))

    for k in range(6):
        L.append("*Step, Name=PATCH_%s, nlgeom=NO" % MODE_NAME[k])
        L.append("unit macro strain %s, the other five held at zero"
                 % MODE_NAME[k])
        L.append("*Static")
        L.append("1.0, 1.0, 1e-6, 1.0")
        L.append("*Boundary, op=NEW")
        # op=NEW clears EVERY boundary condition, including the model-level
        # one that suppresses rigid-body motion.  It has to be restated in
        # each step or the stiffness matrix is singular.
        L.append("MasterNode1, 1, 3")
        for j in range(6):
            L.append("ConstraintsDriver%d, 1, 1, %.8e"
                     % (j, PATCH_STRAIN if j == k else 0.0))
        L.append(out)
        L.append("*End Step")

    # thermal patch test: drivers FREE, uniform heating, stress must vanish
    L.append("*Step, Name=PATCH_thermal_free, nlgeom=NO")
    L.append("uniform heating with every driver free -- stress must be zero")
    L.append("*Static")
    L.append("1.0, 1.0, 1e-6, 1.0")
    L.append("*Boundary, op=NEW")
    L.append("MasterNode1, 1, 3")
    L.append("*Temperature")
    L.append("AllNodes, %g." % PATCH_DT)
    L.append(out)
    L.append("*End Step")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ bar test
BAR_LENGTH = 1.0
BAR_SECTION = 0.2
BAR_CASES = [(5, 1), (10, 2), (20, 4)]        # (elements along x, across)
BAR_DISP = 2.0e-2                             # total end displacement, mm
#  4.0e-3 was too short: at that pull N=20 had not reached its softening
#  minimum at all while N=5 had already saturated and re-hardened, so the
#  three bars were compared at completely different stages (see 0803 run).
BAR_WEAK = 0.80                               # strength of the trigger slice
#  0.95 DID NOT LOCALISE.  cband_damage.py on the 2026-08-03 odbs found damage
#  in 3 of 5 rows at N=5 but 10 of 10 and 20 of 20 at N=10 and N=20 -- the
#  finer meshes damaged the ENTIRE bar, so there was no band and the energy
#  comparison measured nothing.  A 5 % knock-down is not enough separation:
#  neighbouring elements reach their own damage threshold before the trigger
#  slice has softened enough to unload them.  20 % is the standard imperfection
#  size for this demonstration and is still far below the scatter of a real
#  ceramic.

HSMO_KEY = 32.0        # PROPS(25+4*NT) guard on the I1-smoothing block
ITAN_KEY = 33.0        # PROPS(27+4*NT) guard on the tangent block

MATRIX_CARD = [2.0, 350000.0, 0.20, 310.0, 310.0, 0.0, 0.0, 0.90,
               0.90, 0.05, 0.03, 3.0, 0.25, 1.0, 0.031, 0.031,
               250.0, 100000.0, 1.15, 0.75, 0.50, 30.0]
MATRIX_DEPVAR = """*Depvar
20,
1, DMT, Matrix tensile damage
2, DMC, Matrix compressive damage
3, RMT, Matrix maximum tensile criterion
4, RMC, Matrix maximum compressive criterion
5, DMACT, Stress-state-active matrix damage
6, I1SGN, Sign of first effective-stress invariant
7, MMODE, Dominant matrix mode
8, TMINIT, First matrix damage-initiation temperature
9, EQPS, Equivalent plastic strain
10, ATEFF, Effective softening factor (crack band)
11, MDJUMP, Matrix maximum historical damage jump
12, MCUTREQ, Matrix minimum historical PNEWDT factor
13, MTJUMP, Temperature at maximum matrix damage jump
14, MRJUMP, Criterion at maximum matrix damage jump
15, EP11, Plastic strain 11
16, EP22, Plastic strain 22
17, EP33, Plastic strain 33
18, EP12, Plastic strain 12
19, EP13, Plastic strain 13
20, EP23, Plastic strain 23"""


def _card(vals, per_line=8):
    out = []
    for i in range(0, len(vals), per_line):
        out.append(", ".join(("%.10g" % v) for v in vals[i:i + per_line]))
    return "\n".join(out)


def bar_deck(nx, na, itan=None):
    """Structured bar of CUBIC C3D8 elements.  nx along the axis, na across.

    `itan` appends the 2-slot consistent-tangent block to both matrix cards
    (UMAT header, MATRIX layouts: it may only follow the I1-smoothing block,
    so HSMO=0 and its guard 32.0 are written first and the card runs 22 ->
    27 slots).  HSMO=0 is the published sign(I1) step, so the physics is
    unchanged and the ONLY difference between an itan=0 and an itan=1 bar is
    which DDSDDE the routine hands back -- which is exactly what a
    convergence comparison needs.  itan=None writes no block at all and
    leaves the deck byte-identical to what it was before.
    """
    h = BAR_LENGTH / nx
    if abs(h - BAR_SECTION / na) > 1e-12:
        raise ValueError("elements would not be cubic: h_axial=%g, "
                         "h_lateral=%g" % (h, BAR_SECTION / na))

    def nid(i, j, k):
        return 1 + i * (na + 1) * (na + 1) + j * (na + 1) + k

    L = ["*Heading",
         " crack-band mesh-objectivity bar, %d x %d x %d cubic C3D8, h=%g mm"
         % (nx, na, na, h),
         "*Node"]
    for i in range(nx + 1):
        for j in range(na + 1):
            for k in range(na + 1):
                L.append("%d, %.10g, %.10g, %.10g"
                         % (nid(i, j, k), i * h, j * h, k * h))

    weak_slice = nx // 2
    strong, weak = [], []
    L.append("*Element, Type=C3D8")
    eid = 0
    for i in range(nx):
        for j in range(na):
            for k in range(na):
                eid += 1
                # C3D8 wants face 1-2-3-4 counterclockwise as seen from the
                # side where nodes 5-8 sit.  Here 5-8 are at +x, so the first
                # face must run y before z; running z first flips the
                # Jacobian and Abaqus rejects the element outright.
                n = [nid(i, j, k), nid(i, j + 1, k),
                     nid(i, j + 1, k + 1), nid(i, j, k + 1),
                     nid(i + 1, j, k), nid(i + 1, j + 1, k),
                     nid(i + 1, j + 1, k + 1), nid(i + 1, j, k + 1)]
                L.append("%d, %s" % (eid, ", ".join(str(x) for x in n)))
                (weak if i == weak_slice else strong).append(eid)

    def elset(name, ids):
        L.append("*ElSet, ElSet=%s" % name)
        for i in range(0, len(ids), 16):
            L.append(", ".join(str(x) for x in ids[i:i + 16]))

    elset("BAR_STRONG", strong)
    elset("BAR_WEAK", weak)

    def nset(name, ids):
        L.append("*NSet, NSet=%s" % name)
        ids = sorted(ids)
        for i in range(0, len(ids), 16):
            L.append(", ".join(str(x) for x in ids[i:i + 16]))

    nset("X0", [nid(0, j, k) for j in range(na + 1) for k in range(na + 1)])
    nset("XL", [nid(nx, j, k) for j in range(na + 1) for k in range(na + 1)])
    nset("Y0", [nid(i, 0, k) for i in range(nx + 1) for k in range(na + 1)])
    nset("Z0", [nid(i, j, 0) for i in range(nx + 1) for j in range(na + 1)])
    nset("ALLN", list(range(1, (nx + 1) * (na + 1) * (na + 1) + 1)))

    weak_card = list(MATRIX_CARD)
    weak_card[3] *= BAR_WEAK          # Xt
    weak_card[4] *= BAR_WEAK          # Xc
    tail = []
    if itan is not None:
        if itan not in (0, 1):
            raise ValueError("itan must be 0 or 1, got %r" % itan)
        tail = [0.0, 0.0, HSMO_KEY, float(itan), ITAN_KEY]
    for name, card in (("SIC_MATRIX_BAR", MATRIX_CARD),
                       ("SIC_MATRIX_BAR_WEAK", weak_card)):
        full = list(card) + tail
        L.append("*Material, Name=%s" % name)
        L.append(MATRIX_DEPVAR)
        L.append("*User Material, constants=%d" % len(full))
        L.append(_card(full))
    L.append("*Solid Section, ElSet=BAR_STRONG, Material=SIC_MATRIX_BAR")
    L.append("1.0,")
    L.append("*Solid Section, ElSet=BAR_WEAK, Material=SIC_MATRIX_BAR_WEAK")
    L.append("1.0,")

    L.append("*Boundary")
    L.append("X0, 1, 1")            # axial restraint
    L.append("Y0, 2, 2")            # roller: free lateral contraction
    L.append("Z0, 3, 3")
    L.append("*Step, Name=Tension, nlgeom=NO, inc=100000")
    L.append("displacement-controlled tension to localisation and beyond")
    L.append("*Static, stabilize=2e-4, allsdtol=0.05, continue=NO")
    L.append("0.002, 1.0, 1e-8, 0.005")
    L.append("*Controls, parameters=time incrementation")
    L.append(" 12, 16, , 40, , , , 8, , ,")
    L.append("*Controls, parameters=field, field=displacement")
    L.append(" , 1")
    L.append("*Boundary")
    L.append("XL, 1, 1, %.8e" % BAR_DISP)
    L.append("*Output, field, number interval=200")
    L.append("*Element Output, directions=YES")
    L.append("S, E, IVOL, SDV")
    L.append("*Node Output")
    L.append("U, RF")
    L.append("*Output, history, frequency=1")
    L.append("*Node Output, nset=XL")
    L.append("U1, RF1")
    L.append("*Energy Output")
    L.append("ALLIE, ALLSD, ALLWK, ALLPD")
    L.append("*End Step")
    return "\n".join(L) + "\n", eid, h


# --------------------------------------------------------------------- check
def check():
    ok, bad = [0], [0]

    def t(name, cond, extra=""):
        if cond:
            ok[0] += 1
            print("  PASS  %-56s %s" % (name, extra))
        else:
            bad[0] += 1
            print("  FAIL  %-56s %s" % (name, extra))

    print("make_patch_tests.py self-test")

    C = isotropic_C(PATCH_E, PATCH_NU)
    t("C11 = 134615.384615", abs(C[0][0] - 134615.384615) < 1e-6,
      "%.6f" % C[0][0])
    t("C12 = 57692.307692", abs(C[0][1] - 57692.307692) < 1e-6,
      "%.6f" % C[0][1])
    t("C44 = 38461.538462", abs(C[3][3] - 38461.538462) < 1e-6,
      "%.6f" % C[3][3])
    t("C is symmetric", all(abs(C[i][j] - C[j][i]) < 1e-12
                            for i in range(6) for j in range(6)))
    t("no normal-shear coupling in an isotropic C",
      all(abs(C[i][j]) < 1e-12 for i in range(3) for j in range(3, 6)))

    # --- bar meshes -----------------------------------------------------
    g0 = 310.0 ** 2 / (2.0 * 350000.0)
    limit = 0.031 / (1.02 * g0)
    for nx, na in BAR_CASES:
        txt, ne, h = bar_deck(nx, na)
        t("N=%-2d mesh has %d cubic elements of h=%g mm" % (nx, ne, h),
          ne == nx * na * na, "%d" % ne)
        t("N=%-2d elements are cubic" % nx,
          abs(h - BAR_SECTION / na) < 1e-12,
          "h_axial=%g h_lat=%g" % (h, BAR_SECTION / na))
        t("N=%-2d h is below the snap-back limit %.4f mm" % (nx, limit),
          h < limit, "h=%g" % h)
        t("N=%-2d deck declares 22 constants twice" % nx,
          txt.count("*User Material, constants=22") == 2)
        t("N=%-2d card guard PROPS(22)=30 survives" % nx,
          txt.count(" 30") >= 2 or txt.count("30\n") >= 1)
        t("N=%-2d weak slice is exactly one layer" % nx,
          txt.count("*ElSet, ElSet=BAR_WEAK") == 1)
        t("N=%-2d energy output requested" % nx, "ALLSD" in txt)
        t("N=%-2d SDV in the field output" % nx, "S, E, IVOL, SDV" in txt)

        # --- the consistent-tangent pair (2026-08-11) -------------------
        # The bar is the cheapest deck in the repository that actually
        # SOFTENS, which is where the secant and the consistent tangent
        # part company, so it is the convergence comparison job.
        t("N=%-2d omitting --itan leaves the bar byte-identical" % nx,
          bar_deck(nx, na, None)[0] == txt)
        b0, b1 = bar_deck(nx, na, 0)[0], bar_deck(nx, na, 1)[0]
        t("N=%-2d --itan writes 27 constants twice" % nx,
          b1.count("*User Material, constants=27") == 2)
        # THE TRAP THAT WAS SPRUNG ONCE ALREADY: a reader keyed on total
        # NPROPS switches the block underneath it off.  Both guards have to
        # survive on the lengthened card.
        t("N=%-2d both card guards survive on the 27-slot card" % nx,
          b1.count("0.5, 30, 0, 0\n32, 1, 33") == 2)
        d = [(x, y) for x, y in zip(b0.split("\n"), b1.split("\n")) if x != y]
        t("N=%-2d the 0/1 pair differs in exactly two lines" % nx,
          len(d) == 2, "%d line(s)" % len(d))
        for ibad in (2, -1):
            try:
                bar_deck(nx, na, ibad)
                t("N=%-2d itan=%s rejected" % (nx, ibad), False)
            except ValueError:
                t("N=%-2d itan=%s rejected" % (nx, ibad), True)
        t("N=%-2d node numbering is contiguous" % nx,
          ("%d, " % ((nx + 1) * (na + 1) * (na + 1))) in txt)

    # C3D8 connectivity: a flipped face ordering gives a negative Jacobian
    # and Abaqus rejects the element at input processing.  Integrate the
    # hexahedron volume with the trilinear shape functions at 2x2x2 Gauss
    # points and require +h^3 for every element of every mesh.
    def hex_volume(p8):
        g = 1.0 / (3.0 ** 0.5)
        tot = 0.0
        for a in (-g, g):
            for b in (-g, g):
                for c in (-g, g):
                    sgn = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                           (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
                    J = [[0.0] * 3 for _ in range(3)]
                    for n, (sa, sb, sc) in enumerate(sgn):
                        dN = (0.125 * sa * (1 + sb * b) * (1 + sc * c),
                              0.125 * sb * (1 + sa * a) * (1 + sc * c),
                              0.125 * sc * (1 + sa * a) * (1 + sb * b))
                        for r in range(3):
                            for col in range(3):
                                J[r][col] += dN[r] * p8[n][col]
                    det = (J[0][0] * (J[1][1] * J[2][2] - J[1][2] * J[2][1])
                           - J[0][1] * (J[1][0] * J[2][2] - J[1][2] * J[2][0])
                           + J[0][2] * (J[1][0] * J[2][1] - J[1][1] * J[2][0]))
                    tot += det
        return tot

    for nx, na in BAR_CASES:
        txt, ne, h = bar_deck(nx, na)
        coord, conn = {}, []
        mode = None
        for ln in txt.splitlines():
            # "*Node Output" / "*Element Output" are output requests, not
            # mesh definitions -- parsing their data lines as coordinates is
            # how this check first went wrong.
            if ln.startswith("*Node") and "Output" not in ln:
                mode = "n"
                continue
            if ln.startswith("*Element") and "Output" not in ln:
                mode = "e"
                continue
            if ln.startswith("*"):
                mode = None
                continue
            f = [x.strip() for x in ln.split(",")]
            if mode == "n":
                coord[int(f[0])] = tuple(float(x) for x in f[1:4])
            elif mode == "e":
                conn.append([int(x) for x in f[1:9]])
        vols = [hex_volume([coord[n] for n in c]) for c in conn]
        t("N=%-2d every C3D8 has a POSITIVE volume" % nx,
          all(v > 0 for v in vols),
          "min %.6e" % min(vols))
        t("N=%-2d every element volume is exactly h^3" % nx,
          all(abs(v - h ** 3) < 1e-12 * h ** 3 for v in vols),
          "h^3 = %.6e, got %.6e" % (h ** 3, vols[0]))
        t("N=%-2d volumes sum to the bar volume" % nx,
          abs(sum(vols) - BAR_LENGTH * BAR_SECTION ** 2) < 1e-12,
          "%.6f vs %.6f" % (sum(vols), BAR_LENGTH * BAR_SECTION ** 2))

    # the crack band must give a DIFFERENT softening factor for each mesh,
    # otherwise the test would prove nothing
    As = []
    for nx, na in BAR_CASES:
        h = BAR_LENGTH / nx
        A = 2.0 * g0 * h / (0.031 - g0 * h) if 0.031 > 1.02 * g0 * h else 50.0
        As.append(min(50.0, max(0.01, A)))
    t("the three meshes really do get different softening factors",
      len(set("%.4f" % a for a in As)) == 3,
      "A = " + ", ".join("%.3f" % a for a in As))
    t("A grows with element size (coarser = more brittle)",
      As[0] > As[1] > As[2])

    # weak slice
    # Mirror the generator exactly: it scales BOTH Xt and Xc (see bar_deck).
    # The old local copy scaled only Xt, so the assertion below could not have
    # noticed if the generator ever stopped scaling Xc.
    wc = list(MATRIX_CARD)
    wc[3] *= BAR_WEAK
    wc[4] *= BAR_WEAK
    # Pinned to BAR_WEAK, not to one rendering of it -- the constant moved
    # once already (0.95 -> 0.80) and a hard-coded 294.5 only caught it by
    # accident.
    t("trigger slice is knocked down by exactly (1 - BAR_WEAK)",
      abs(wc[3] - MATRIX_CARD[3] * BAR_WEAK) < 1e-9,
      "Xt = %.1f = %.0f %% of %.1f" % (wc[3], 100 * BAR_WEAK, MATRIX_CARD[3]))
    t("both tensile and compressive strength are knocked down together",
      abs(wc[4] - MATRIX_CARD[4] * BAR_WEAK) < 1e-9,
      "Xc = %.1f" % wc[4])
    # A 5 % imperfection demonstrably failed to localise on 2026-08-03.
    t("the imperfection is large enough to have localised",
      BAR_WEAK <= 0.90,
      "%.0f %% knock-down; 5 %% damaged the whole bar at N=10 and N=20"
      % (100 * (1 - BAR_WEAK)))
    t("but still smaller than real ceramic strength scatter",
      BAR_WEAK >= 0.70, "%.2f" % BAR_WEAK)

    # --- patch deck structure -------------------------------------------
    fake_head = ("*Heading\n fake\n*Node\n1, 0., 0., 0.\n"
                 "*NSet, NSet=AllNodes\n1\n"
                 "*NSet, NSet=MasterNode1\n1\n"
                 "*Boundary\nMasterNode1, 1, 3\n")
    pd = patch_deck(fake_head, ["*Solid Section, ElSet=Matrix, Material=X",
                                "*Solid Section, ElSet=Yarn0, Material=X"])
    t("patch deck has 7 steps", pd.count("*Step, Name=") == 7,
      "%d" % pd.count("*Step, Name="))
    t("every step is closed",
      pd.count("*Step, Name=") == pd.count("*End Step"))
    # count only inside the steps -- the model-level block also has one
    steps_only = pd[pd.find("*Step, Name="):]
    t("EVERY step restates the rigid-body constraint after op=NEW",
      steps_only.count("MasterNode1, 1, 3")
      == steps_only.count("*Boundary, op=NEW"),
      "%d constraints for %d op=NEW blocks"
      % (steps_only.count("MasterNode1, 1, 3"),
         steps_only.count("*Boundary, op=NEW")))
    t("the patch deck never calls the UMAT", "*User Material" not in pd)
    t("both sections get the same isotropic material",
      pd.count("Material=PATCH_ISO") == 2)
    t("six mechanical steps constrain all six drivers",
      pd.count("ConstraintsDriver") == 6 * 6 + 7 * 6,
      "%d" % pd.count("ConstraintsDriver"))
    t("the thermal step leaves the drivers free",
      "PATCH_thermal_free" in pd
      and pd.split("PATCH_thermal_free")[1].count(
          "ConstraintsDriver%d, 1, 1" % 0) == 0)
    t("the thermal step heats by +100 K", "AllNodes, 100." in pd)

    # ---------------------------------------------------------------- #
    # The reader.  These three exist because all three bugs shipped: the
    # 2026-08-03 run printed a 6x6 of nan, PASSED the tolerance check on it,
    # and then crashed outright on the crack-band bars.  A deck that is
    # perfect and a reader that cannot read it is still a wasted morning.
    # ---------------------------------------------------------------- #
    rp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "postprocess", "patch_report.py")
    src = open(rp).read() if os.path.exists(rp) else ""
    t("postprocess/patch_report.py exists", bool(src))

    # 1. Repository is not a dict.
    t("the reader never calls .get() on an odb Repository",
      "historyOutputs.get(" not in src,
      "historyOutputs is a Repository: `in`, `[]`, `.keys()` -- no .get()")

    # 2. nan must not be able to buy a PASS.  nan compares False against
    #    everything, so `if err > worst` silently skips it and a `worst`
    #    initialised to 0.0 reports a perfect match on no data at all.
    nan = float("nan")
    t("nan really does compare False -- the trap is real",
      not (nan > 0.0) and not (nan < 0.0) and not (nan == 0.0))
    t("the reader gates on PRESENCE before it applies any tolerance",
      "every entry of the 6x6 was recovered from the odb" in src
      and src.find("every entry of the 6x6 was recovered")
      < src.find("the whole 6x6 matches the analytic isotropic C"),
      "presence check must run first")
    t("the reader starts `worst` below zero, not at zero",
      "worst, worst_at = -1.0" in src,
      "0.0 would be indistinguishable from a perfect match")
    t("the match verdict also requires nothing to be missing",
      "(not missing) and 0.0 <= worst < RTOL_C" in src)
    t("the symmetry verdict cannot pass on an empty comparison",
      "bool(pairs) and (not missing)" in src)

    # 3. The node-set name is not the region key.
    t("the reader falls back to the node label to find a driver region",
      "def region_for(" in src and "set_label(odb, setname)" in src,
      "`*Node Output, nset=Foo` yields 'Node ASSEMBLY.<label>'")

    # 4. The deck is FLAT, so its node sets are instance-level, not assembly
    #    level.  Searching only the assembly found nothing and the whole 6x6
    #    came back missing -- on a deck whose field output was perfect.
    t("the patch deck really is flat (no *Assembly)",
      "*Assembly" not in pd and "*Instance" not in pd,
      "so *NSet lands on the auto-generated instance")
    t("the reader searches instance node sets, not just the assembly",
      "ra.instances.values()" in src and "ra.nodeSets" in src)
    t("the reader uppercases the set name before lookup",
      "setname.upper()" in src, "odb stores set names upper case")

    # 5. A lookup failure must never cost a re-run: the same quantities are in
    #    the field output, and the reader must say what it did find.
    t("the reader falls back to FIELD output when history is unmatched",
      "def field_at_node(" in src and "fieldOutputs" in src)
    t("the patch deck writes nodal U and RF as field output too",
      "*Node Output\nU, RF" in pd or "*Node Output\n U, RF" in pd,
      "so the fallback has something to read")
    t("a failed lookup dumps what the odb actually contains",
      "def available(" in src and "printed because a driver lookup failed"
      in src, "no third round of guessing")

    # 6. THE SIGN.  PATCH_PBC is the only exact case in the project, so it is
    #    the authority on the driver-reaction convention.  The 2026-08-03 run
    #    returned the analytic 6x6 to 1e-8 with EVERY entry negated, which
    #    settles it: R = dW/d(eps) = sigma*V, so sigma = +RF/V.  All three
    #    readers had the minus; extract_ss_curve.py then flipped the curve
    #    back, which produced correct magnitudes and hid the error.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fn, pat in (("patch_report.py", "Cnum[i][k] = rf / V / UNIT_STRAIN"),
                    ("extract_ss_curve.py", "sig = rf / V"),
                    ("driver_audit.py", "sig = RF[-1][1] / V")):
        q = os.path.join(root, "postprocess", fn)
        txt = open(q).read() if os.path.exists(q) else ""
        t("%s uses sigma = +RF/V" % fn, pat in txt)
        t("%s has no leftover minus on the reaction" % fn,
          "-rf / V" not in txt and "-RF[-1][1] / V" not in txt
          and "-rf/V" not in txt)
    ess = open(os.path.join(root, "postprocess",
                            "extract_ss_curve.py")).read()
    t("extract_ss_curve no longer silently flips a negative curve",
      "The curve is written AS COMPUTED, not flipped." in ess,
      "a flip would hide exactly this bug")
    t("and warns loudly instead", "WARNING: peak stress is NEGATIVE" in ess)

    print("\n%d passed, %d failed" % (ok[0], bad[0]))
    return 0 if bad[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    ap.add_argument("--deck", help="assembled RVE deck to take the mesh + PBC "
                                   "from (for the patch test)")
    ap.add_argument("-o", "--outdir", default=".", help="output directory")
    ap.add_argument("--bar-only", action="store_true",
                    help="write only the crack-band bars")
    ap.add_argument("--itan", type=int, default=None, choices=(0, 1),
                    help="write the crack-band bars with the consistent-"
                         "tangent block (Ge Eqs.31-33) on the matrix card, "
                         "switched off (0) or on (1).  The job name gets an "
                         "_ITAN0/_ITAN1 suffix so the pair cannot overwrite "
                         "each other.  Omitting the flag writes no block and "
                         "leaves the decks byte-identical to before.")
    ap.add_argument("--check", action="store_true", help="self-test and exit")
    a = ap.parse_args()

    if a.check:
        sys.exit(check())

    if not os.path.isdir(a.outdir):
        os.makedirs(a.outdir)

    if not a.bar_only:
        if not a.deck:
            ap.error("--deck is required for the patch test "
                     "(or pass --bar-only)")
        text = open(a.deck).read()
        i = text.find(MAT_ANCHOR)
        if i < 0:
            sys.exit("anchor %r not found in %s" % (MAT_ANCHOR, a.deck))
        sections = re.findall(r"^\*Solid Section,.*$", text[i:], re.MULTILINE)
        out = os.path.join(a.outdir, "PATCH_PBC.inp")
        with open(out, "w") as f:
            f.write(patch_deck(text[:i], sections))
        print("wrote %s   (%d sections, 7 steps, no UMAT)"
              % (out, len(sections)))

    sfx = "" if a.itan is None else "_ITAN%d" % a.itan
    for nx, na in BAR_CASES:
        txt, ne, h = bar_deck(nx, na, a.itan)
        out = os.path.join(a.outdir, "CBAND_N%d%s.inp" % (nx, sfx))
        with open(out, "w") as f:
            f.write(txt)
        print("wrote %s   %d C3D8 of h=%g mm" % (out, ne, h))


if __name__ == "__main__":
    main()
