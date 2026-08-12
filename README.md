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
src/UMAT_CSIC_RVE_DAMAGE_V2_7D.for        CURRENT UMAT = V2_7P + yarn SDV17 diagnostic
src/UMAT_CSIC_RVE_DAMAGE_V2_7P.for        the batch UMAT for P0..P2T1000 (paper SDV labels)
src/UMAT_CSIC_RVE_DAMAGE_V2_{5,6,7}.for   prior V2 steps kept for provenance
src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for      thermoelastic baseline (KYARN30 + KMTRX30)
abaqus/ZHANG2022_{RT23,T500,T1000}_V1_0.inp   provenance baseline decks
abaqus/ZHANG2022_{RT23,T500,T1000}_V2_0.inp   provenance full-model decks -- SEE WARNING BELOW
abaqus/make_v2_fullmodel.py               regenerates the V2_0 decks from V1_0 (card swap only)
abaqus/assemble_inp.py                    splice material cards + 3 steps onto ANY TexGen mesh
abaqus/MESH_REGEN_GUIDE.md                coarse-mesh (20-40k) trend-check workflow
verification/
  PAPER_DEVIATION_REGISTER.md              EVERY deviation from the paper, with numbers
  VERIFICATION_REPORT.md                   full property + equation audit
  CALIBRATION_GUIDE.md                     how to tune the unpublished params to Table 3
  audit_temperature_props.py               taints TEMP through the UMAT; --selftest
  verify_diagnostic_inert.sh               proves SDV17 changes nothing and is not vacuous
  patch_depvar_yarn.py                     yarn *Depvar 16 -> 17 only; --selftest
  patch_material_prop.py                   change ONE *User Material constant; --selftest
  micromech_check.py                       proves yarn card = Chamis/Schapery of Tables 1–2
  verify_constitutive.py                   single-point UMAT re-impl.; unit tests + curves
  verify_fullmodel.py                      V2_0 full model vs V1_0 baseline (Eq.18 + plasticity)
  compile_check.sh                         gfortran check of every UMAT, truncating at col 72
postprocess/
  extract_tension.py / extract_ss_curve.py macro σ–ε
  extract_cooling_damage.py                damaged-element fraction vs temperature (Fig.4/6)
  extract_damage_histogram.py              per-phase damage distributions (Fig.A1–A3) + SDV17
  extract_homogenization.py                damaged homogenized 6x6 from the HOM_* steps
  find_frames.py                           stage frames for Fig.12/14/16
  make_odb_images.py                       contour plates (Fig.3/5/7/8/9/10/12/14/16)
  make_fig4_cooling.py / make_paper_figures.py / make_fig_a1_histogram.py
docs/
  RUN_LAYOUT.md                            which run reproduces which paper configuration
  PAPER_FIGURE_PLAYBOOK.md                 every paper figure -> the command that makes it
  LAB_MEETING_BRIEF.md                     presentation-ready findings
```

### Which decks are canonical

The decks in `abaqus/` are the **provenance baseline** — they document the
V1_0 → V2_0 card swap. They are *not* what the batches run.

> ⚠️ `abaqus/*_V2_0.inp` **will not run with V2_6 or later.** Yarn slot 32
> holds `12.5`, written when that slot meant `G1t`; V2_6 redefined it as
> `GF1T` and V2_7 added a guard rejecting anything above 0.5 N/mm, so the
> job calls `XIT` on the first increment. The guard is working as designed.
> The value is left as found because changing a property is a modelling
> decision. `docs/RUN_LAYOUT.md` describes the decks the batches use
> (`GF1T=0.03962`), which live on the analysis machine.

**Model provenance:** the constitutive model is Ge et al., Compos. Sci. Technol. 157
(2018) 86–98 (Ref. [17] in Zhang 2022). The UMAT implements Ge Eqs. (1)–(33) in full;
V1_0 cards leave matrix plasticity (Eqs. 6–10) and the yarn Eq.18 mixed law switched
off, V2_0 cards switch them on with Ge/micromechanics-based starting values.

## Verify the code now (no Abaqus, no odb needed)

```bash
bash    verification/compile_check.sh            # every UMAT, truncated at col 72
bash    verification/verify_diagnostic_inert.sh  # SDV17 inert + non-vacuous
python3 verification/audit_temperature_props.py --selftest
python3 verification/patch_depvar_yarn.py    --selftest
python3 verification/patch_material_prop.py  --selftest
python3 verification/micromech_check.py       # yarn constants vs paper Tables 1–2
python3 verification/verify_constitutive.py   # equation unit tests (PASS/FAIL) + curves
python3 verification/plot_paper_reference.py  # paper Table 3 targets
```

Each of these runs in seconds and needs no Abaqus licence. Tools that edit
decks or claim "no effect" carry a `--selftest` on principle: a check that
reports zero findings is only worth reporting if it can find something.

## Run the full-model RVE and compare (on your Abaqus machine)

```bash
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V2_0.inp  \
       user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
# ... T500, T1000 likewise (V2_0 decks)
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb   # -> Job-RT23_ss.csv
python3 postprocess/plot_compare.py Job-*_ss.csv             # -> ss_curves_by_temperature.png
```

Then tune the unpublished parameters to Table 3 — see **`verification/CALIBRATION_GUIDE.md`**.

## Status

Full detail with numbers in `verification/PAPER_DEVIATION_REGISTER.md`.
Two axes, and they are **not** at the same level — the machinery is
essentially done, the physics is not.

### Machinery — done

- ✅ **Material constants match** — matrix exact (Table 2); yarn exact via
  Chamis/Schapery of Tables 1–2 (≤0.14 % over 12 constants, Vf≈0.792).
- ✅ **Constitutive equations match** — Hashin (11–14), von Mises (15–16),
  exponential damage (17/19), crack-band (19–21); unit-tested, no bugs.
- ✅ **Procedure matches §3.2.4** — stress-free 1050 °C, cool → heat → tension.
  All three temperature runs share a bit-identical cooling step.
- ✅ **Every figure in the paper can be regenerated** from the existing odbs.
  See `docs/PAPER_FIGURE_PLAYBOOK.md` for the command behind each one.
- ✅ **Temperature-dependent properties: none needed.** An audit of the UMAT,
  the decks and the paper's own tables found 0 on all three — `TEMP` reaches
  only the onset-temperature state variables. Both sides agree.

### Physics — the open problem

- ✅ **23 °C strength lands inside the experimental scatter**:
  118.71 MPa vs 116.17 ± 8.78 measured (paper FE 128.45).
- ❌ **The temperature trend has the wrong sign.** Paper +40 % (23→500)
  and +11 % (500→1000); ours **+0.4 %** and **−7.9 %**. With properties
  constant on both sides, the only temperature-varying input at the start
  of tension is the thermal residual stress — and the same relief that
  strengthens the paper weakens us.
- ❌ **The driving phase differs at 23 °C.** Warp longitudinal damage
  reaches 31.07 % against the paper's 60.67 %. Residual stress hands the
  matrix tensile headroom (+156.7 MPa) and the yarn compressive headroom
  (−341.8 MPa), so whichever phase sets the strength sets the sign; ours
  is the yarn, the paper's is matrix/shear.
- 🎯 **Both trace to one number: the yarn `XT=421` back-calibration.**
  In Eq.11 the σ11 term dominates at 421 against shear strengths of 120;
  at the paper's own 2835 it contributes 2.2 % and shear takes over,
  which is the mechanism the paper describes. Driving the single-point
  model over one strain path, the shear share at onset moves from
  **0.1096 (XT=421) to 0.8481 (XT=2835)**.
- ⏭️ **P3 tests exactly this** — one variable, yarn slot 11 `421 → 2835`,
  at all three temperatures. Prediction pre-registered in
  `PAPER_DEVIATION_REGISTER.md` §5.23E *before* the run, and the
  diagnostic needed to read the result (`SDV17`) is already in place.
