# CDM-UMAT — ZHANG2022 C/SiC RVE replication

Replication and **verification** of the progressive-damage UMAT for 2D plain-weave
C/SiC composites in:

> Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang,
> *Effect of thermal residual stress on the tensile properties and damage process of
> C/SiC composites at high temperatures*, Ceramics International **48** (2022) 3109–3124.

Goal: reproduce the paper's temperature-dependent (23 / 500 / 1000 °C) tensile
results and verify the code for reuse in follow-on research.

## Layout

```
src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for      UMAT: KYARN30 (yarn) + KMTRX30 (matrix)
                                           - full Ge-2018 model; physics toggled by card
abaqus/ZHANG2022_{RT23,T500,T1000}_V1_0.inp   verified baseline decks (plasticity/Eq.18 OFF)
abaqus/ZHANG2022_{RT23,T500,T1000}_V2_0.inp   FULL-MODEL decks (plasticity + Eq.18 ON) -> run these
abaqus/make_v2_fullmodel.py               regenerates the V2_0 decks from V1_0 (card swap only)
abaqus/assemble_inp.py                    splice material cards + 3 steps onto ANY TexGen mesh
abaqus/make_pbc_check.py                  PBC patch-test / homogenisation / EasyPBC decks
abaqus/make_easypbc_model.py              (CAE) build the model EasyPBC runs on
abaqus/make_history_driven_rve.py         replay a macro strain+T history on the RVE
abaqus/MESH_REGEN_GUIDE.md                coarse-mesh (20-40k) trend-check workflow
abaqus/THERMAL_SHOCK_TRANSFER.md          plan for carrying the RVE to a thermal-shock coupon
verification/
  VERIFICATION_REPORT.md                   full property + equation audit (READ THIS)
  PBC_VALIDATION_GUIDE.md                  4-stage periodic-BC validation workflow
  CALIBRATION_GUIDE.md                     how to tune the unpublished params to Table 3
  micromech_check.py                       proves yarn card = Chamis/Schapery of Tables 1–2
  check_pbc.py                             static audit of the PBC in any TexGen deck
  test_check_pbc.py                        fault injection proving check_pbc.py has teeth
  verify_constitutive.py                   single-point UMAT re-impl.; unit tests + curves
  verify_fullmodel.py                      V2_0 full model vs V1_0 baseline (Eq.18 + plasticity)
  plot_paper_reference.py                  renders paper Table 3 as the target
  compile_check.sh                         gfortran syntax/interface check of the UMAT
  figures/                                 generated PNGs
postprocess/
  extract_ss_curve.py                      (Abaqus) macro σ–ε from ConstraintsDriver history
  extract_stiffness.py                     (Abaqus) 6x6 C + CTE + PBC consistency verdict
  compare_pbc_easypbc.py                   our homogenisation vs EasyPBC
  plot_compare.py                          overlay curves + strengths vs Table 3
```

**Model provenance:** the constitutive model is Ge et al., Compos. Sci. Technol. 157
(2018) 86–98 (Ref. [17] in Zhang 2022). The UMAT implements Ge Eqs. (1)–(33) in full;
V1_0 cards leave matrix plasticity (Eqs. 6–10) and the yarn Eq.18 mixed law switched
off, V2_0 cards switch them on with Ge/micromechanics-based starting values.

## Verify the code now (no Abaqus needed)

```bash
python3 verification/micromech_check.py       # yarn constants vs paper Tables 1–2
python3 verification/verify_constitutive.py   # equation unit tests (PASS/FAIL) + curves
python3 verification/plot_paper_reference.py  # paper Table 3 targets
python3 verification/check_pbc.py abaqus/ZHANG2022_RT23_V1_0.inp   # periodic BC audit
python3 verification/test_check_pbc.py        # 11 injected faults, all must be caught
python3 postprocess/extract_stiffness.py --selftest                # homogenisation algebra
```

## Verify the periodic boundary conditions (Abaqus, no UMAT needed)

Before trusting any damage result, prove the constraints themselves. Full workflow
and pass criteria in **`verification/PBC_VALIDATION_GUIDE.md`**.

```bash
python3 abaqus/make_pbc_check.py abaqus/ZHANG2022_RT23_V1_0.inp
abaqus job=PBC_PATCH input=PBC_PATCH.inp double interactive     # needs no .ori, no UMAT
abaqus python postprocess/extract_stiffness.py PBC_PATCH.odb --patch
abaqus job=PBC_ELASTIC input=PBC_ELASTIC.inp double interactive # two-phase, needs .ori
abaqus python postprocess/extract_stiffness.py PBC_ELASTIC.odb
```

A homogeneous cell under correct PBC has a known closed-form answer, so the patch
test passes or fails at machine precision — no judgement call. Then cross-check the
whole thing against EasyPBC, an independent implementation:

```bash
abaqus cae noGUI=abaqus/make_easypbc_model.py -- PBC_ELASTIC_CAE.inp
python3 postprocess/compare_pbc_easypbc.py PBC_ELASTIC_constants.csv <EasyPBC report>
```

## Run the full-model RVE and compare (on your Abaqus machine)

```bash
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V2_0.inp  \
       user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
# ... T500, T1000 likewise (V2_0 decks)
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb   # -> Job-RT23_ss.csv
python3 postprocess/plot_compare.py Job-*_ss.csv             # -> ss_curves_by_temperature.png
```

Then tune the unpublished parameters to Table 3 — see **`verification/CALIBRATION_GUIDE.md`**.

## Status (see VERIFICATION_REPORT.md for detail)

- ✅ **Material constants match the paper** — matrix exact (Table 2); yarn exact via
  Chamis/Schapery of Tables 1–2 (≤0.14 % over 12 constants, Vf≈0.792).
- ✅ **Constitutive equations match the paper** — Hashin (11–14), von Mises (15–16),
  exponential damage (17/19), crack-band (19–21); all unit-tested PASS; no bugs.
- ✅ **Analysis procedure matches** paper §3.2.4 (stress-free 1050 °C, cool→heat→tension).
- ⚙️ **V2_0 full model built** — matrix plasticity + Eq.18 enabled, yarn longitudinal
  strengths from T300 micromechanics, fracture energies from Ge 2018 Table 3. Starting
  values verified stable at the material-point level (`verify_fullmodel.py`).
- ✅ **Periodic BCs audit clean on all six decks** — 57 equations re-derived from the
  measured lattice offsets, every one of the 9,062 surface nodes constrained exactly
  once, opposite faces node-for-node matched, mesh fills its box to 100.0000 %.
  The audit itself is proven by catching 11 injected faults. The Abaqus patch test
  and the EasyPBC cross-check are built and ready to run.
- ✅ **RVE composition confirmed against the paper** — tet-volume integration gives
  yarn 50.51 % / matrix 49.49 %, so overall fibre Vf = 0.5051 × 0.792 = **0.4000**,
  matching the paper's Vf ≈ 40 % (0.792 is the yarn-level Vf that `micromech_check.py`
  recovers independently from Chamis/Schapery).
- ⚠️ **Exact Table 3 numbers need an Abaqus run + calibration** of the parameters the
  paper never published (yarn transverse/shear strengths, Eq.18 X_PO/rF/K1, matrix
  SY0/HISO). This is expected trial-and-error tuning, documented step-by-step in
  `verification/CALIBRATION_GUIDE.md`. These are modelling choices, not code errors.
- ⏳ **Thermal-shock transfer designed, not run** — the route (macro transient thermal →
  macro thermal stress with the homogenised card → RVE replay of the hot-spot history)
  is laid out in `abaqus/THERMAL_SHOCK_TRANSFER.md`, and the replay generator exists.
  It is blocked on constituent thermal properties, which Zhang 2022 does not publish.
