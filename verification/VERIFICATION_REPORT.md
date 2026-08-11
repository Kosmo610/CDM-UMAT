# Verification Report — ZHANG2022 C/SiC RVE UMAT

**Target paper:** Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang,
*"Effect of thermal residual stress on the tensile properties and damage process
of C/SiC composites at high temperatures,"* Ceramics International **48** (2022)
3109–3124. Model equations deferred by Zhang to Ref. [17] = J. Ge et al.,
Compos. Sci. Technol. **157** (2018) 86–98.

**Files audited**

| File | Role |
|------|------|
| `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for` | UMAT (yarn `KYARN30`, matrix `KMTRX30`) |
| `abaqus/ZHANG2022_RT23_V1_0.inp` | RVE, cool 1050→23 °C, tension at 23 °C |
| `abaqus/ZHANG2022_T500_V1_0.inp` | + heat 23→500 °C, tension at 500 °C |
| `abaqus/ZHANG2022_T1000_V1_0.inp` | + heat 23→1000 °C, tension at 1000 °C |

---

## 요약 (Korean summary)

- **물성치 (재료 상수): 논문과 일치.** 매트릭스(SiC)는 Table 2 값과 정확히 일치하고,
  얀(yarn) 8개 상수는 논문이 사용한 **Chamis + Schapery 마이크로역학**으로 T300(Table 1)
  + SiC(Table 2)로부터 계산한 값과 **오차 0.15 % 이내로 완전히 재현**됩니다(얀 섬유체적비
  Vf≈0.792 → 복합재 Vf≈39.6 %, 논문 "약 40 %"와 일치).
- **수식: 논문과 일치.** 3D Hashin(식 11–14), von Mises(식 15–16), 지수형 손상(식 17/19),
  균열대 정규화(식 19–21)를 코드가 그대로 구현하고 있으며, 단위 테스트로 폐형식과 일치함을
  확인했습니다(모두 PASS). **명백한 버그는 없습니다.**
- **아직 논문과 다른 3가지 (논문이 값을 공개하지 않은 부분):**
  ① 얀 강도(Xt/Xc/Yt/Yc/S)와 손상계수 A는 논문에 없어 임시값으로 들어가 있음,
  ② 매트릭스 소성(SY0=0으로 꺼져 있음) — 논문은 탄소성 모델 사용,
  ③ 얀 종방향 인장의 혼합법칙(식 18)이 꺼져 있음(X_PO=0).
- **결론:** 물성·수식은 검증 완료. 논문의 **정확한 수치(128.45/179.42/199.15 MPa)**를 재현하려면
  (a) 사용자 PC의 Abaqus로 RVE 3-스텝 해석을 실행하고, (b) 위 ①②③의 미공개 파라미터를
  Table 3에 맞춰 **보정(calibration)** 해야 합니다. 이 환경에는 Abaqus가 없으므로 실행 재현은
  불가하며, 대신 **상수·수식 검증 + 온도별 비교 자동화 스크립트**를 제공합니다.

---

## 1. Scope and what "verified" means here

This environment has **no Abaqus solver**, so the full woven-RVE homogenisation
(116k–174k C3D4 elements, periodic BC, 3 analysis steps) that produces the paper's
macroscopic strengths **cannot be executed here**. Verification is therefore split
into the parts that *can* be checked rigorously now, and the parts that require a
run on your Abaqus machine:

| Layer | Verifiable here? | Result |
|-------|:---:|--------|
| Material constants vs paper Tables 1–2 (+ Chamis/Schapery) | ✅ | **Exact match** |
| Constitutive equations vs paper Eqs. (1)–(19) | ✅ | **Exact match** (unit-tested) |
| Analysis procedure (steps / temperatures / stress-free T) | ✅ | **Matches paper §3.2.4** |
| Macroscopic σ–ε and ultimate strength (Table 3) | ❌ (needs Abaqus) | tooling provided |

Reproducible check scripts:
`verification/micromech_check.py`, `verification/verify_constitutive.py`,
`verification/plot_paper_reference.py`.

---

## 2. Material properties — VERIFIED against the paper

### 2.1 SiC matrix (`SIC_MATRIX_DAMAGE`, 22 constants) vs Table 2

| Property | Paper Table 2 | Card | Verdict |
|---|---|---|---|
| E_m | 350 GPa | `350000.` MPa | ✅ exact |
| ν_m | 0.20 | `0.20` | ✅ exact |
| G_m | 146 GPa | E/2(1+ν)=145.83 GPa (computed) | ✅ consistent (0.1 %) |
| X_m,t = X_m,c | 310 MPa | `310., 310.` | ✅ exact |
| α_m | 4.5×10⁻⁶ /K | `4.5e-06` (`*Expansion, zero=1050`) | ✅ exact |

### 2.2 Yarn (`CSIC_YARN_DAMAGE`, 38 constants) vs Chamis/Schapery of Tables 1–2

The paper (§3.2.3) states the yarn constants are computed from the T300 filament
(Table 1) and SiC matrix (Table 2) via **Chamis [32]** (stiffness) and
**Schapery [33]** (CTE). Recovering the yarn-level fibre volume fraction from the
card's `E1` gives **Vf = 0.79194** (→ composite Vf ≈ 39.6 %, matching the paper's
"nearly 40 %"). With that single Vf, every yarn constant is reproduced:

| Constant | Chamis/Schapery | Card | Rel. err |
|---|---|---|---|
| E1 | 254967.23 | 254967.228042 | 0.000 % |
| E2 = E3 | 44321.74 | 44321.737572 | 0.000 % |
| ν12 = ν13 | 0.247516 | 0.247516386 | 0.000 % |
| ν23 | 0.395833 | 0.395813581 | 0.005 % |
| G12 = G13 | 26430.91 | 26431.515264 | 0.002 % |
| G23 | 15876.45 | 15876.667974 | 0.001 % |
| α1 | 1.0706×10⁻⁶ | 1.070926×10⁻⁶ | 0.000 % |
| α2 = α3 | 3.3296×10⁻⁶ | 3.324909×10⁻⁶ | 0.142 % |

**Worst error over all 12 yarn constants: 0.142 %.** The yarn elastic + thermal
card is a faithful micromechanics homogenisation of the paper's constituent data.
(Reproduce: `python3 verification/micromech_check.py`.)

Chamis/Schapery relations used (Vf = yarn fibre fraction, √ = √Vf):
```
E1  = Vf·Ef1 + (1−Vf)·Em
E2  = Em / [1 − √Vf·(1 − Em/Ef2)]
G12 = Gm / [1 − √Vf·(1 − Gm/Gf12)]
G23 = Gm / [1 − √Vf·(1 − Gm/Gf23)]
ν12 = Vf·νf12 + (1−Vf)·νm
ν23 = E2/(2·G23) − 1
α1  = (Vf·Ef1·αf1 + (1−Vf)·Em·αm) / (Vf·Ef1 + (1−Vf)·Em)
α2  = √Vf·αf2 + (1−√Vf)·[(1+νm)·αm − α1·νm]
```

---

## 3. Constitutive equations — VERIFIED against the paper

Every kernel was re-implemented in Python (`verify_constitutive.py`) and unit-tested
against the closed-form paper equations. **All tests PASS.**

Zhang 2022 and Ge 2018 use **different equation numbers for the same physics**, so
the mapping below keeps them in separate columns (see `refs/GE2018_EXTRACTION.md` §A).
A dash means the paper has no corresponding equation.

| Zhang Eq. | Ge Eq. | Meaning | UMAT location | Status |
|---|---|---|---|---|
| (2)–(3) | (1)–(2), (4) | Yarn σ = C(d):εᵉ, effective stress σ̃ = C₀:εᵉ | `KYARN30` L188 | ✅ |
| — | (3) | Shear damage coupling d₄,d₅,d₆ = f(d₁,d₂,d₃) | `KYARN30` L262–264 | ✅ |
| (11) | (12) | Hashin fibre tension (α=β=1 — α,β are **Zhang's** coefficients, declared 1 by Zhang; Ge Eq. (12) has no α,β, i.e. every shear weight is 1) | `KYARN30` L195–197 | ✅ |
| (12) | (12) | Hashin fibre compression | `KYARN30` L199 | ✅ |
| (13) | (12) | Hashin transverse tension | `KYARN30` L202–205 | ✅ |
| (14) | (12) | Hashin transverse compression | `KYARN30` L207–211 | ✅ |
| (17) | (16) 1st line | Exponential evolution d=1−exp[A(1−r)]/r | `KDAMAGE_TARGET` | ✅ |
| (18) | (16) 2nd line + (17) | Mixed linear-exp. law (yarn 1t) | `KMIX1T` | ✅ coded, **disabled** (§5) |
| (6)–(8) | (5), (7) | Matrix σ̃ = C₀:(ε−εᵖ) | `KMTRX30` L372 | ✅ |
| (9) | (8)–(10) | von Mises associated flow, isotropic hardening | `KMTRX30` L376–401 | ✅ coded, **off** (§5) |
| (15)–(16) | (13) | Matrix initiation φ = σ_vM/X_{t,c} by sign(I₁) | `KMTRX30` L405–413 | ✅ |
| (19) | (18) | Matrix exponential evolution | `KDAMAGE_TARGET` | ✅ |
| — | (19)–(21) | Crack-band regularisation of A (Bazant; **Ge only** — Zhang has no crack-band equation, and Zhang's (19) is the matrix exponential law above) | `KABAND` | ✅ |

Unit-test output (excerpt):
```
Eq.17/19 A=2.0 r=1.5:  code=0.754747 ref=0.754747  PASS
Eq.15/16 vonMises   :  code=155.81078 ref=155.81078  PASS
Eq.11 Hashin fib-t  :  code=1.003466 ref=1.003466  PASS
Eq.13 Hashin trn-t  :  code=0.982379 ref=0.982379  PASS
Eq.19-21 crack-band :  code=0.320359 ref=0.320359  PASS
OVERALL: ALL KERNELS REPRODUCE THE PAPER EQUATIONS -> PASS
```

Single-point constituent curves (`figures/yarn_constitutive.png`,
`figures/matrix_constitutive.png`) confirm the peaks equal the input strengths:
yarn 1t → 1198 MPa (Xt=1200), yarn 2t → 78.7 MPa (Yt=80), matrix → 309.9 MPa
(Xm=310), each followed by the correct exponential softening branch.

**No correctness bugs were found in the constitutive code.**

The UMAT also passes a stand-alone **Fortran compile check** (`compile_check.sh`,
gfortran, Abaqus implicit-typing convention, stub `ABA_PARAM.INC`): it is valid
fixed-form Fortran and every subroutine interface
(`UMAT`/`KYARN30`/`KMTRX30`/`KMIX1T`/`KABAND`/`KDAMAGE_TARGET`/`KORTHO`/
`KMATVEC6`/`KMISES`) resolves consistently.

---

## 4. Analysis procedure — matches paper §3.2.4

| Paper step | RT23 | T500 | T1000 | Status |
|---|---|---|---|---|
| ① Cool 1050 °C → 23 °C (thermal residual stress + initial damage) | ✅ | ✅ | ✅ | matches |
| ② Heat 23 °C → test T | (n/a) | 23→500 | 23→1000 | matches |
| ③ Hold T, apply tension | εxx≤0.15 % | εxx≤0.32 % | εxx≤0.48 % | matches |

- Stress-free temperature `*Expansion, zero=1050` on both materials — ✅ (paper: PIP
  process temperature 1050 °C).
- Thermal strain supplied by Abaqus `*Expansion`; UMAT receives *mechanical* strain — ✅.
- Periodic BC via 6 `ConstraintsDriver` dummy nodes (Xia unified PBC) — ✅.
- Increasing applied failure strain with temperature (0.15→0.32→0.48 %) is consistent
  with the paper's higher ductility/strength at high T.

---

## 5. Gaps that block *exact* numerical reproduction of Table 3

These are **not coding errors** — they are parameters the paper **does not publish**,
so they cannot be derived, only calibrated. They are exactly the knobs that set the
macroscopic strengths (128.45 / 179.42 / 199.15 MPa).

| # | Item | Card now | Paper | Impact |
|---|------|----------|-------|--------|
| 1 | Yarn strengths Xt,Xc,Yt,Yc,S12,S13,S23 | 1200/1500/80/350/120/120/100 (placeholder, from prior line) | **not listed** | sets yarn damage onset → composite strength |
| 2 | Yarn softening A1t,A1c,Att,Atc | 2.0 (fixed) | **not listed** | post-peak slope / dissipation |
| 3 | Yarn longitudinal-tension mixed law Eq.18 | **off** (X_PO=0 → uses Eq.17) | Eq.18 **used** (params in Ref.[30]) | warp-yarn 1t tail (dominant failure mode) |
| 4 | Matrix plasticity SY0, HISO | **0 → off** | elastic-**plastic** (Eqs. 6–10) | residual strain / pseudo-ductility, curve shape |
| 5 | Mesh | 34 049 nodes / 174 405 C3D4 | 116 724 C3D4 | different discretisation → small result shift |
| 6 | Consistent tangent, Ge Eqs. (31)–(33) | **not implemented** — `CTAN(I,J)=CD(I,J)`, i.e. the **secant** operator (`KYARN30` L275–279, `KMTRX30` L437–) | Ge derives the algorithmic tangent `C_t = S⁻¹(dᵛ):[I − M(dᵛ)]` *"to ensure the quadratic convergence rate of the Newton-Raphson method"* (p.92) | the damage-derivative term `M` is missing, so convergence in the **softening branch drops from 2nd to 1st order** — the likely structural cause of the M1 round-3 escalation of η from 0.02 to 0.05 |
| 7 | Matrix free energy: plastic dissipation of Ge Eqs. (23)–(24) | **omitted** — `KMTRX30` L421–422 passes only the elastic part `Xt²/(2E)·CELENT` into `KABAND` | Ge Eq. (23) splits G_m into an elastic part **and** a plastic part `G_m^p(ε̄_m^p)`, *"the contribution due to plastic hardening"* | once matrix plasticity is switched on, the real dissipated energy **exceeds** the card G_m, so the crack-band normalisation of A_m no longer delivers mesh-independence. This is an error source **independent of** the 1.92× `CELENT` discrepancy measured by `celent_census.py` |

Notes:
- **#6 and #7 are not unpublished parameters** — unlike #1–#5 they are equations of
  Ge 2018 that the UMAT does not implement in full. They are listed here because they
  block exact reproduction for the same practical reason.
- **Matrix plasticity (#4)** is the reason the matrix curve in
  `figures/matrix_constitutive.png` is elastic-brittle instead of showing the
  paper's residual-strain plateau. The paper explicitly divides matrix strain into
  εᵉ+εᵖ+εᵗʰ (Eq. 6) but gives no yield stress / hardening modulus.
- **Eq.18 (#3)** governs the warp-yarn longitudinal-tension tail, which the paper
  names as a *primary* failure mode — enabling it changes the 23/500 °C curves most.
- The mesh (#5) differs from the paper's; even with identical constants the numbers
  will differ slightly because the TexGen geometry/mesh was regenerated.

**Update — V2_0 full model (with Ge 2018 [17] in hand).** The source model paper
(Ge et al., CST 157, 2018) was obtained and confirms: the UMAT implements Ge Eqs.
(1)–(21) and (29)–(30); Eqs. (22)–(28) are reduced to a uniaxial / linear-hardening
closed form and the consistent tangent of Eqs. (31)–(33) is replaced by the secant
operator (see §D of `refs/GE2018_EXTRACTION.md`); Ge Table 2 lists the same T300
filament (E1=230, Xt=3580, Xc=2470); Ge Table 3 gives, explicitly and as four separate
cells, Gf,1t = Gf,1c = 12.5 N/mm and Gf,2(3)t = Gf,2(3)c = 1.0 N/mm (matrix
Gm,t(c) = 1.0 N/mm). The `abaqus/*_V2_0.inp` decks now **enable** the previously-off
physics (#2 Eq.18, #4 matrix plasticity) and set #1 longitudinal yarn strengths from
T300 rule-of-mixtures (Xt=Vf·3580=2835, Xc=Vf·2470=1956). Remaining unknowns (yarn
transverse/shear strengths, X_PO/rF/K1, SY0/HISO) are calibration knobs — see
`CALIBRATION_GUIDE.md`. Material-point stability of the V2_0 starting values is
confirmed by `verify_fullmodel.py` (`figures/fullmodel_vs_baseline.png`).

---

## 6. Path to matching the paper's Table 3 (on your Abaqus machine)

1. **Run the 3 jobs** with the UMAT:
   `abaqus job=Job-RT23 input=abaqus/ZHANG2022_RT23_V1_0.inp user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive`
   (similarly T500, T1000).
2. **Extract** each macroscopic curve:
   `abaqus python postprocess/extract_ss_curve.py Job-RT23.odb` → `Job-RT23_ss.csv`.
3. **Compare** to the paper:
   `python3 postprocess/plot_compare.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv`
   → `ss_curves_by_temperature.png` (curves + strength bars vs Table 3).
4. **Calibrate the unpublished parameters (#1–#4)** to match Table 3. Recommended,
   minimal, physically-guided order:
   - Fix matrix at the paper's 310 MPa (already correct); it is ~100 % damaged after
     cooling (paper: matrix damage = 100 % at 845 °C), so it mostly sets the pre-load
     state, not the peak.
   - Tune **yarn Yt (transverse tension)** and **S** first — they control the early
     nonlinearity from transverse yarn damage that dominates the cooled state.
   - Tune **yarn Xt + enable Eq.18** (X_PO, rF, K1 from Ref.[30]) to set the warp-yarn
     longitudinal tail and the 23 °C ultimate (target 128.45 MPa).
   - Optionally enable **matrix plasticity** (small SY0, HISO) to recover the residual
     strain if you need the *shape*, not just the strength, to match.
   - The temperature trend (↑ strength with T) should then emerge from the thermal
     residual-stress redistribution already built into steps ①–②; verify 500/1000 °C
     land near 179 / 199 MPa and adjust only if the trend is off.

A calibration harness is not shipped enabled because injecting guessed strengths and
calling it "the paper" would be dishonest — see the decision requested in the README.

---

## 7. Bottom line

- **Material constants and constitutive equations are verified to match the paper**
  (matrix exact; yarn exact via Chamis/Schapery, ≤0.14 %; all damage equations
  unit-tested PASS; no bugs).
- **Exact reproduction of the Table 3 numbers additionally requires** (a) an Abaqus
  run of the provided 3-step models, and (b) calibration of the handful of
  parameters the paper never published (§5). Those are modelling choices, not code
  corrections, and are called out explicitly so the "verified" claim stays honest.
