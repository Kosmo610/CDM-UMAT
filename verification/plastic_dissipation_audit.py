#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plastic_dissipation_audit.py -- does the matrix plastic work belong in A_m?

    python3 verification/plastic_dissipation_audit.py
    python3 verification/plastic_dissipation_audit.py --check

WHY THIS FILE EXISTS
====================
refs/GE2018_EXTRACTION.md section D listed Ge refs/[24] Eqs. (23)-(24) as a
GAP: "the plastic part is not included, so our A_m is over-estimated".  That
sentence was written from the table of contents of the argument, not from the
algebra, and this file settles it from the printed equations.

It settles it in the direction that COSTS us something, so it is worth being
explicit about why an audit finding is being withdrawn rather than fixed.
CLAUDE.md records the opposite failure -- a review with no source in hand
demoted a correct attribution and deleted a real citation, which was worse
than the defect it claimed to find.  The same discipline applies to our own
audit: a gap that the source says is not a gap has to be retracted with the
quotation attached, not quietly left in the list to look thorough.

WHAT GE ACTUALLY PRINTS
=======================
Eq. (23):   G_m = G_m^e(eps_m^e, d_m) + G_m^p(eps_m^p)
Eq. (24):   G_m = [s_11^2 + s_22^2 + s_33^2] / (2(1-d_m) E_m)
                  - (nu_m/E_m)(s_11 s_22 + s_22 s_33 + s_33 s_11)
                  + (1+nu_m)(s_12^2 + s_23^2 + s_31^2) / ((1-d_m) E_m)
                  + G_m^p(eps_m^p)

THE DECIDING FEATURE IS THE ARGUMENT LIST, NOT THE SIZE OF THE TERM.
G_m^p is a function of eps_m^p ALONE.  d_m does not appear in it -- Ge says so
in the sentence introducing Eq. (23): the elastic contribution "is affected by
damage", the plastic part "is the contribution due to plastic hardening".
That is the whole point of an effective-stress coupling: hardening is driven
by the effective stress, so it is damage-blind by construction.

Now look at what the crack band actually integrates.  Eq. (20)-(21):

    g_M = int (dG/dd_M) (dd_M/dr_M) dr_M = G_M / l*

Only dG/dd_M enters.  A term with no d_m in it differentiates to zero, so
G_m^p contributes EXACTLY ZERO to A_m -- not a little, not a correction term,
zero.  KABAND passing g0 = X_t^2/(2E) is therefore right, and the "gap" is
withdrawn.

WHAT IS ACTUALLY TRUE, AND IS NOT NOTHING
=========================================
The plastic work is large -- this file measures it -- and it is dissipated in
the same band as the damage.  The crack band regularises the DAMAGE
dissipation so that g_damage * l_e is mesh-independent.  It does not touch the
plastic dissipation, which stays proportional to the band volume and therefore
to l_e.  So the TOTAL dissipated energy of a localising matrix element is
mesh-dependent even with a perfect crack band, by the plastic share.

That is a real limitation of the model -- Ge's as much as ours, since Ge's
Eq. (21) has the same structure -- and it is what should be recorded in place
of the withdrawn gap.  It is quantified below at the real card and the real
element sizes rather than asserted.
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

_OK, _BAD = [], []


def check(name, cond, detail=""):
    (_OK if cond else _BAD).append(name)
    print("  %s  %-58s %s" % ("PASS" if cond else "FAIL", name, detail))


# --------------------------------------------------------------------------
# the card.  Slots are the V1_0 matrix layout; see the UMAT header.
# --------------------------------------------------------------------------
E_M = 350000.0          # PROPS(2)   MPa
XT_M = 310.0            # PROPS(4)   MPa, tensile damage-initiation stress
XC_M = 310.0            # PROPS(5)
SY0 = 250.0             # PROPS(17)  MPa, initial yield
HISO = 100000.0         # PROPS(18)  MPa, linear isotropic hardening modulus
GMT = 0.031             # PROPS(15)  N/mm
GMC = 0.031             # PROPS(16)  N/mm

# Element characteristic lengths this card is actually consumed at.
LE_RVE_MEAN = 0.0307    # mm, Ch.4 4.2.1 mean CELENT of the c26k RVE mesh
LE_RVE_MAX = 0.0845     # mm, largest CELENT in the same mesh
LE_BAR = (0.200, 0.100, 0.050)      # the crack-band bars of make_patch_tests


def g_elastic(X, E):
    """G_m^e at damage onset: d_m = 0 and the effective stress is X."""
    return X * X / (2.0 * E)


def g_plastic(X, sy0, hiso):
    """G_m^p at damage onset, for the linear isotropic hardening this card
    carries.  Yield at sy0, then sigma_tilde = sy0 + hiso*p, so damage onset
    at sigma_tilde = X is reached at p* = (X - sy0)/hiso and

        G^p = int_0^p* sigma_tilde dp = sy0*p* + 0.5*hiso*p*^2.

    A card that never yields before damage (X <= sy0) returns zero, which is
    the elastic-brittle limit and is a legitimate configuration, not an
    error.
    """
    if X <= sy0:
        return 0.0, 0.0
    p = (X - sy0) / hiso
    return sy0 * p + 0.5 * hiso * p * p, p


def a_crackband(g0le, gf):
    """KABAND, total-area convention.  Mirrors the UMAT."""
    if gf == 0.0:
        return 2.0
    if gf > 1.02 * g0le:
        return min(50.0, max(1e-2, 2.0 * g0le / (gf - g0le)))
    return 50.0


def main():
    print("=" * 74)
    print(" GE EQS. (23)-(24): WHERE THE MATRIX PLASTIC WORK GOES")
    print("=" * 74)

    ge = g_elastic(XT_M, E_M)
    gp, pstar = g_plastic(XT_M, SY0, HISO)
    print("""
 At the tensile damage threshold X_t = %.0f MPa on the matrix card:

   elastic   G_m^e = X_t^2/(2E)          = %.6f N/mm^2
   plastic   G_m^p = sy0*p + H*p^2/2     = %.6f N/mm^2   (p* = %.3e)
   ------------------------------------------------------------------
   total     G_m                          = %.6f N/mm^2
   plastic share of the stored energy     = %.1f %%
""" % (XT_M, ge, gp, pstar, ge + gp, 100.0 * gp / (ge + gp)))

    check("the matrix DOES yield before it damages", XT_M > SY0,
          "X_t = %.0f > sy0 = %.0f MPa" % (XT_M, SY0))
    # If the plastic part entered A_m it would not be a rounding correction:
    # it is larger than the elastic part it would be added to.
    check("the plastic part is LARGER than the elastic part",
          gp > ge, "%.6f vs %.6f N/mm^2 (%.2fx)" % (gp, ge, gp / ge))

    print(""" So the question is not academic -- had G_m^p entered Eq. (21) the
 softening parameter would have moved by more than a factor of two.  It does
 not enter, because Eq. (24) makes G_m^p a function of eps_m^p alone and
 Eq. (21) integrates dG/dd_m.  A damage-free term differentiates to zero.

 The table below shows what the WRONG reading would have done, at the element
 sizes this card is really consumed at.  The 'wrong A' column is the number
 the withdrawn gap would have produced.
""")
    print(" %-26s %8s %10s %10s %9s" % ("consumed at", "le [mm]", "A (ours)",
                                        "A (wrong)", "ratio"))
    print(" " + "-" * 68)
    rows = []
    for label, le in ([("RVE mesh, mean CELENT", LE_RVE_MEAN),
                       ("RVE mesh, largest CELENT", LE_RVE_MAX)]
                      + [("crack-band bar N=%d" % n, le)
                         for n, le in zip((5, 10, 20), LE_BAR)]):
        a_ours = a_crackband(ge * le, GMT)
        a_wrong = a_crackband((ge + gp) * le, GMT)
        rows.append((label, le, a_ours, a_wrong))
        print(" %-26s %8.4f %10.4f %10.4f %9.3f"
              % (label, le, a_ours, a_wrong, a_wrong / a_ours))

    # Every row must actually differ, or the demonstration is empty.
    check("the wrong reading changes A_m at every element size",
          all(abs(w / o - 1.0) > 0.05 for _, _, o, w in rows),
          "min ratio %.3f" % min(w / o for _, _, o, w in rows))
    # And it always over-softens, i.e. the withdrawn gap had the SIGN wrong
    # too: it claimed our A_m was over-estimated.
    check("including it would RAISE A_m, not lower it -- the withdrawn "
          "gap had the sign backwards",
          all(w > o for _, _, o, w in rows))

    print("""
 WHAT REPLACES THE WITHDRAWN GAP
 -------------------------------
 The plastic work is dissipated in the localisation band and the crack band
 does NOT regularise it.  Damage dissipation is held at G_M by construction;
 plastic dissipation scales with the band volume, hence with l_e.  So the
 plastic share of the total dissipated energy is itself mesh-dependent:
""")
    print(" %-26s %8s %14s %14s %8s" % ("", "le [mm]", "G_damage [N/mm]",
                                        "G_plastic [N/mm]", "share"))
    print(" " + "-" * 74)
    shares = []
    for label, le in ([("RVE mesh, mean CELENT", LE_RVE_MEAN),
                       ("RVE mesh, largest CELENT", LE_RVE_MAX)]
                      + [("crack-band bar N=%d" % n, le)
                         for n, le in zip((5, 10, 20), LE_BAR)]):
        g_dam = GMT - ge * le          # dissipated part of the total-area Gf
        g_pl = gp * le
        share = g_pl / (g_dam + g_pl)
        shares.append((le, share))
        print(" %-26s %8.4f %14.6f %14.6f %7.1f %%"
              % (label, le, g_dam, g_pl, 100.0 * share))

    # ---- the crack-band bar's trigger slice (found 2026-08-12) ---------
    # BAR_WEAK = 0.80 was chosen to make the localisation band pick itself.
    # It also, unintentionally, put the trigger slice's X_t at 248 MPa --
    # BELOW sy0 = 250 -- so that slice is elastic-brittle while every slice
    # around it is elastoplastic.  The imperfection is therefore not "20 %
    # weaker"; it is "20 % weaker AND zero plastic dissipation", and the
    # second half is nowhere on the card.
    print("""
 THE CRACK-BAND BAR'S TRIGGER SLICE IS BRITTLE AND NOBODY ASKED FOR IT
 ---------------------------------------------------------------------""")
    bar_weak = 0.80
    xt_w = XT_M * bar_weak
    gp_w = g_plastic(xt_w, SY0, HISO)[0]
    print(" %-18s %8s %12s %12s %10s"
          % ("slice", "X_t [MPa]", "G^e", "G^p", "plastic"))
    print(" " + "-" * 64)
    for nm, xt in (("strong", XT_M), ("weak (trigger)", xt_w)):
        _gp = g_plastic(xt, SY0, HISO)[0]
        _ge = g_elastic(xt, E_M)
        print(" %-18s %8.1f %12.6f %12.6f %9.1f %%"
              % (nm, xt, _ge, _gp, 100.0 * _gp / (_ge + _gp)))
    print("""
 The two slices do not differ in one property, they differ in two, and the
 one nobody wrote down is the larger.  abaqus/make_patch_tests.py --brittle
 raises sy0 above the STRONG X_t so every slice is brittle; that is the only
 configuration in which the three meshes' energies test the crack band and
 nothing else.
""")
    check("the trigger slice's X_t falls below sy0", xt_w < SY0,
          "%.1f < %.1f MPa" % (xt_w, SY0))
    check("so the trigger slice carries NO plastic work", gp_w == 0.0,
          "G^p = %.6f N/mm^2" % gp_w)
    check("while its neighbours carry more plastic than elastic",
          gp > ge, "%.3f vs %.3f N/mm^2" % (gp, ge))
    check("the asymmetry is larger than the strength knockdown it came with",
          gp / (ge + gp) > (1.0 - bar_weak),
          "plastic share %.1f %% vs knockdown %.0f %%"
          % (100.0 * gp / (ge + gp), 100.0 * (1.0 - bar_weak)))
    check("--brittle exists and removes it",
          "--brittle" in open(os.path.join(ROOT, "abaqus",
                                           "make_patch_tests.py")).read())

    check("the plastic share is not negligible at the RVE mesh",
          shares[0][1] > 0.05, "%.1f %% at le = %.4f mm"
          % (100.0 * shares[0][1], shares[0][0]))
    # THE STATEMENT THAT GOES IN THE LIMITATIONS LIST: it is mesh-dependent,
    # so refining the mesh changes the total dissipated energy even though
    # the crack band is working perfectly.
    fine = [s for le, s in shares if le <= 0.05]
    coarse = [s for le, s in shares if le >= 0.20]
    check("and it FALLS as the mesh is refined, so the total dissipated "
          "energy is mesh-dependent",
          fine and coarse and max(fine) < min(coarse),
          "%.1f %% at 0.05 mm vs %.1f %% at 0.20 mm"
          % (100.0 * max(fine), 100.0 * min(coarse)))

    # ---- the documentation must carry the retraction, not the old gap ----
    ext = open(os.path.join(ROOT, "refs", "GE2018_EXTRACTION.md")).read()
    # The old phrase may survive INSIDE the retraction -- a retraction that
    # cannot quote what it withdraws is not a retraction -- but nowhere else.
    check("the old 'A_m over-estimated' verdict survives only inside the "
          "retraction",
          ext.count("매트릭스 A_m 과대추정") == 1
          and "한때" in ext.split("매트릭스 A_m 과대추정")[0][-120:],
          "%d occurrence(s)" % ext.count("매트릭스 A_m 과대추정"))
    check("it carries the retraction with the reason",
          "G_m^p" in ext and "이 들어 있지 않으므로" in ext)
    check("the summary no longer lists it as a real performance impact",
          "「소성 소산 누락」은 철회되었다" in ext)
    check("and the replacement limitation is recorded there",
          "소성 소산은 균열대가 정규화하지 않는다" in ext)

    print()
    print("=" * 74)
    if _BAD:
        print(" FAIL: %s" % "; ".join(_BAD))
        return 1
    print(" ALL %d PLASTIC-DISSIPATION CHECKS HOLD" % len(_OK))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
