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
abaqus/ZHANG2022_{RT23,T500,T1000}_V1_0.inp   3-step RVE jobs (cool→[heat]→tension)
verification/
  VERIFICATION_REPORT.md                   full property + equation audit (READ THIS)
  micromech_check.py                       proves yarn card = Chamis/Schapery of Tables 1–2
  verify_constitutive.py                   single-point UMAT re-impl.; unit tests + curves
  plot_paper_reference.py                  renders paper Table 3 as the target
  figures/                                 generated PNGs
  Zhang2022_CeramicsInternational.pdf      the paper
postprocess/
  extract_ss_curve.py                      (Abaqus) macro σ–ε from ConstraintsDriver history
  plot_compare.py                          overlay curves + strengths vs Table 3
```

## Verify the code now (no Abaqus needed)

```bash
python3 verification/micromech_check.py       # yarn constants vs paper Tables 1–2
python3 verification/verify_constitutive.py   # equation unit tests (PASS/FAIL) + curves
python3 verification/plot_paper_reference.py  # paper Table 3 targets
```

## Run the RVE and compare (on your Abaqus machine)

```bash
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V1_0.inp  \
       user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
# ... T500, T1000 likewise
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb   # -> Job-RT23_ss.csv
python3 postprocess/plot_compare.py Job-*_ss.csv             # -> ss_curves_by_temperature.png
```

## Status (see VERIFICATION_REPORT.md for detail)

- ✅ **Material constants match the paper** — matrix exact (Table 2); yarn exact via
  Chamis/Schapery of Tables 1–2 (≤0.14 % over 12 constants, Vf≈0.792).
- ✅ **Constitutive equations match the paper** — Hashin (11–14), von Mises (15–16),
  exponential damage (17/19), crack-band (19–21); all unit-tested PASS; no bugs.
- ✅ **Analysis procedure matches** paper §3.2.4 (stress-free 1050 °C, cool→heat→tension).
- ⚠️ **Exact Table 3 numbers need an Abaqus run + calibration** of parameters the paper
  never published: yarn strengths & softening factors, the Eq.18 mixed law (off), and
  matrix plasticity (off). These are modelling choices, not code errors.

### Open decision (calibration philosophy)

The paper omits yarn strengths, the Eq.18 parameters, and the matrix plastic
parameters. To move from "equations verified" to "Table 3 reproduced" pick one:
1. **Keep current cards**, treat this as an equation/property verification only.
2. **Calibrate** the unpublished parameters to hit Table 3 (128.45/179.42/199.15 MPa)
   — enable Eq.18 and matrix plasticity, tune yarn strengths.
3. **Adopt Ge et al. 2018 [17]** constituent strengths where given and calibrate the rest.

Option 2 is what "reproduce the paper" normally means; it changes the input cards and
should be a deliberate choice, so it is not applied silently.
