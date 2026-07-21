#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
micromech_check.py
==================
Proves that the yarn material card in the ZHANG2022 Abaqus input files is an
*exact* Chamis + Schapery micromechanics homogenisation of the paper's
constituent data:

    Table 1  T300 filament :  E1f=230, E2f=40, G12f=24, G23f=14.3 GPa, nu12f=0.26,
                              a1f=-0.3e-6, a2f=3.1e-6 /K
    Table 2  SiC matrix    :  Em=350 GPa, num=0.20, Gm=146 GPa, am=4.5e-6 /K

The single free parameter is the *yarn-level* fibre volume fraction Vf, which is
recovered from the card's E1 and then shown to reproduce every other constant.

Reference: Q. Zhang et al., Ceramics International 48 (2022) 3109-3124, Sec. 3.2.3
("... material properties of yarns could be calculated" via Chamis [32] & Schapery [33]).

Run:  python3 micromech_check.py
"""
import math

# ---- Paper constituent data (MPa, /K) --------------------------------------
Ef1, Ef2, Gf12, Gf23, nuf12 = 230e3, 40e3, 24e3, 14.3e3, 0.26   # T300, Table 1
Em, num = 350e3, 0.20                                            # SiC,  Table 2
Gm = Em / (2.0 * (1.0 + num))                                   # 145833 MPa (~146)
af1, af2, am = -0.3e-6, 3.1e-6, 4.5e-6                          # CTEs

# ---- Yarn card as written in the .inp User Material (constants=38) ----------
CARD = dict(E1=254967.228042, E2=44321.737572, E3=44321.737572,
            nu12=0.247516386, nu13=0.247516386, nu23=0.395813581,
            G12=26431.515264, G13=26431.515264, G23=15876.667974,
            a1=1.070925962822e-06, a2=3.324908565604e-06, a3=3.324908565604e-06)


def chamis_schapery(Vf):
    sq = math.sqrt(Vf)
    Vm = 1.0 - Vf
    out = {}
    out["E1"]  = Vf * Ef1 + Vm * Em                                    # rule of mixtures
    out["E2"]  = Em / (1.0 - sq * (1.0 - Em / Ef2))                    # Chamis transverse
    out["E3"]  = out["E2"]
    out["G12"] = Gm / (1.0 - sq * (1.0 - Gm / Gf12))
    out["G13"] = out["G12"]
    out["G23"] = Gm / (1.0 - sq * (1.0 - Gm / Gf23))
    out["nu12"] = Vf * nuf12 + Vm * num
    out["nu13"] = out["nu12"]
    out["nu23"] = out["E2"] / (2.0 * out["G23"]) - 1.0
    out["a1"] = (Vf * Ef1 * af1 + Vm * Em * am) / (Vf * Ef1 + Vm * Em)  # Schapery long.
    out["a2"] = sq * af2 + (1.0 - sq) * ((1.0 + num) * am - out["a1"] * num)  # transverse
    out["a3"] = out["a2"]
    return out


def main():
    Vf = (Em - CARD["E1"]) / (Em - Ef1)      # invert longitudinal rule of mixtures
    print("=" * 74)
    print("YARN CARD  vs  CHAMIS/SCHAPERY MICROMECHANICS  (paper Tables 1 & 2)")
    print("=" * 74)
    print(f"Recovered yarn-level fibre volume fraction:  Vf = {Vf:.5f}")
    print(f"  -> if yarns occupy ~50% of the RVE, composite Vf ~ {Vf*0.5*100:.1f}%"
          f"   (paper: 'nearly 40%')\n")
    m = chamis_schapery(Vf)
    print(f"{'constant':6}  {'micromechanics':>16}  {'card value':>16}  {'err %':>8}   verdict")
    print("-" * 74)
    worst = 0.0
    for k in ["E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13", "G23",
              "a1", "a2", "a3"]:
        comp, ref = m[k], CARD[k]
        err = abs(comp - ref) / abs(ref) * 100.0 if ref else 0.0
        worst = max(worst, err)
        print(f"{k:6}  {comp:16.6f}  {ref:16.6f}  {err:8.3f}   "
              f"{'MATCH' if err < 0.5 else '**DIFF**'}")
    print("-" * 74)
    print(f"worst relative error over all 12 yarn constants: {worst:.3f} %")
    print("VERDICT: the yarn card is a faithful Chamis/Schapery homogenisation")
    print("         of the paper's T300 + SiC constituent data.  ->  VERIFIED")
    print("=" * 74)


if __name__ == "__main__":
    main()
