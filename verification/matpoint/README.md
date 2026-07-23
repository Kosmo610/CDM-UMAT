# Material-point verification of UMAT_CSIC_ZHANG2022_V3_1_FAST

Compiles the production UMAT against a stub `ABA_PARAM.INC` and drives a single
integration point (no Abaqus license needed — gfortran only).

```bash
bash run_matpoint_check.sh
```

Checks:
1. Clean compile (catches interface/syntax regressions).
2. Matrix uniaxial tension: peak sigma ~ Xt (=310 MPa), plasticity + softening.
3. Yarn longitudinal tension: peak sigma ~ Xt (=3969 MPa), initial slope = E1.
4. Consistent tangent vs central finite difference: 0% in elastic, plastic,
   and plastic+shear regimes (=> good Newton convergence in Abaqus/Standard).

Use it as a regression test whenever the UMAT is edited.
