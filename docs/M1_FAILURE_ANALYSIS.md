# M1 post-mortem — why `ZHANG2022_c26k_*` (2026-07-28) died

All three jobs aborted with

```
***ERROR: TIME INCREMENT REQUIRED IS LESS THAN THE MINIMUM SPECIFIED
```

Everything below is read out of the three `.msg` files and out of the decks
themselves. No solver was used to write this document.

---

## 1. Where each job actually stopped

| job | steps in the deck | died in | step time | physical state reached | wall |
|---|---|---|---|---|---|
| `RT23`  | cool → **tension** | **step 2 = tension** | 0.0892 | ε_xx = **1.34e-4** (0.0134 %) | 1384 s |
| `T500`  | cool → **reheat** → tension | **step 2 = reheat** | 0.341 | T = **185.7 °C** | 1527 s |
| `T1000` | cool → **reheat** → tension | **step 2 = reheat** | 0.166 | T = **185.2 °C** | 1646 s |

Two things follow immediately.

**The cooldown is not the problem.** Step 1 reached step time 1.0 in all three
jobs. The UMAT, the periodic-BC `*Equation` block and the mesh are all fine.

**T500 and T1000 never reached their tension step at all.** Their step 2 is the
*reheat*. There is no stress–strain data in those two ODBs to extract, and
`extract_ss_curve.py` will find no tension step. Only `RT23` has any tension at
all, and 0.013 % strain is roughly 4 % of the way to Zhang's failure strain —
about 13 MPa against a 128.45 MPa target. **None of the three runs is usable for
calibration.**

**Both reheat jobs died at the same temperature — 185.7 °C and 185.2 °C — from
different ramp rates and different increment sizes.** T500 heats at 477 K per
unit step time, T1000 at 977 K, so a coincidence in step *fraction* is ruled
out. This is a material event on the unloading path, at a fixed temperature,
not an incrementation artefact.

## 2. Cutting the time increment could never have worked

The last two iterations of `RT23`:

```
iteration 7   AVERAGE FORCE 0.221   residual  1.393E-03   Δu -9.956E-10   correction -5.322E-10
iteration 8   AVERAGE FORCE 0.221   residual -2.412E-02   Δu -1.007E-09   correction -4.336E-10
***NOTE: THE SOLUTION APPEARS TO BE DIVERGING. CONVERGENCE IS JUDGED UNLIKELY.
```

The displacement increment is **1e-9 mm**. The time increment had already been
ground down to the `1.0E-12` floor through 18 cutbacks. At that point the strain
increment is numerically zero, so a well-posed problem converges on the first
iteration. It did not. **Whatever is wrong is not a step-size problem**, which
is why 18 cutbacks and ~23 minutes of wall clock achieved nothing.

Two distinct mechanisms are visible in those two lines.

**(a) The wrong convergence criterion is deciding.** The step ran with
`R_n^α = 0.005`, alternate `0.02`, `C_n^α = 0.08`, time-average force `0.228`.
At iteration 7 the residual was `1.393e-3`, i.e. **inside the alternate force
tolerance of `0.02 × 0.228 = 4.56e-3`**. Force had converged. What rejected the
iteration was the *displacement-correction* check:
`|c|/|Δu| = 5.322e-10 / 9.956e-10 = 0.53` against `0.08` — a ratio of two
numbers that are both physically zero. The `.msg` shows Abaqus accepting other
increments with `***WARNING: FORCE EQUILIBRIUM ACCEPTED USING THE ALTERNATE
TOLERANCE`, so this one criterion is what stood between the job and progress.

**(b) The divergence judgement fires too early.** The UMAT returns a **secant**
Jacobian (`CTAN = CD`, the damaged stiffness; the header of
`UMAT_CSIC_RVE_ZHANG2022_V1_0.for` says so). It does not contain `∂d/∂ε` and it
does not contain the elastoplastic correction. Newton with a secant Jacobian
converges *linearly*, not quadratically. Abaqus's logarithmic-rate check —
`I_R`, left at the default 10 — is calibrated for quadratic convergence and
declares "CONVERGENCE IS JUDGED UNLIKELY" on a run that is merely slow.

## 3. Why the material is in trouble at all

Mean-field estimate of the matrix state at the end of the 1050 → 23 °C
cooldown, driven through the **real** V1_0 point routine (plasticity + damage +
crack band) with parallel-bar in-plane compatibility:

| stress-free T on `*Expansion, zero=` | matrix σ (biaxial) | **r = σ_vM / X_t** | p̄ |
|---|---|---|---|
| **1050 °C (the deck as shipped)** | **302 MPa** *(estimate; measured 268.08)* | **0.973** | 5.2e-4 |
| 800 | 270 | 0.871 | 2.0e-4 |
| 600 | 233 | 0.751 | 0 |
| 500 | 192 | 0.621 | 0 |
| 307 | 114.7 | 0.370 | 0 |

**The matrix leaves the cooldown at 97 % of its damage threshold, on average,
after the model's own plasticity has already relieved it from a trial 414 MPa.**
Any local stress concentration above 1.03× — and a woven RVE has 1.5–3× at every
tow crossover — puts that element on the softening branch before the tension
step begins. With the crack-band softening factor `A ≈ 0.61` at the median
element size, an element at 2× the mean sits at `d = 0.73`; at 3×, `d = 0.90`.

That is the physical picture behind both failures: **there is no rising branch
left to walk up.** RT23 is asked to pull an RVE that is already at its limit;
the reheat jobs are asked to unload one, and the unloading path crosses the
sign change that switches the matrix between its tension and compression damage
branches (`DACT = DTN if I1 ≥ 0 else DCN`, a hard switch with no smoothing —
the one genuinely discontinuous line in the model, and the most likely
explanation for the reproducible 185 °C event, though confirming that needs the
SDV fields, see §6).

**This is a real result, not only a bug.** PIP C/SiC does come out of the
furnace microcracked. But it means the deck as configured cannot produce a
stress–strain curve, and the TRS it predicts is far from the measurement:

> refs/[15] measures the matrix residual stress by XRD as **+114.7 MPa**.
> The mean-field estimate above predicts **302 MPa** — 2.6× too high.
>
> **MEASURED, 2026-07-29** (`damage_census.py` on the cooled ODB): the
> volume-averaged matrix stress is **+268.08 MPa**, i.e. **2.34×** the XRD
> value. The mean-field estimate was 13 % high, as expected for a Voigt-type
> bound, and the conclusion is unchanged: the deck overpredicts the matrix
> TRS by more than a factor of two. Quote **268.08 MPa and 2.34×** from here
> on; the 302 MPa figure is the pre-run estimate and must be labelled as such
> wherever it appears.

(The XRD *yarn* reading, −68.7 MPa, is **not** a usable target: XRD sees the SiC
lattice, not the carbon fibre, so it is not comparable to our homogenised yarn
stress of −666 MPa. Do not calibrate against it.)

## 4. Secondary findings from the deck audit

* **Mesh** — 26452 C3D4 (5680 nodes): 15369 matrix, 11083 yarn.
  Crack-band snap-back limit for the matrix is `Gf/(1.02·g0) = 0.2214 mm`.
  By `V^(1/3)` (median 0.053, max 0.083 mm) **no** element exceeds it. By
  **longest edge** (median 0.162, max 0.322 mm) **5.5 % of matrix elements do**,
  and those get `A` clamped to the snap-back value 50 — a near-vertical drop.
  Which one Abaqus reports as `CELENT` for a C3D4 decides whether 849 elements
  are brittle. Worth checking with SDV10 (`ATEFF`), which the UMAT already
  writes.
* **`DMAX = 0.99`** left a failed matrix element with 1 % of 350 GPa = 3.5 GPa.
  Thousands of those beside intact elements is what collapsed the average force
  to 0.221 N and wrecked the conditioning.
* **Yarn `Gtt = Gtc = 0`** — the crack band is **off** for both yarn transverse
  modes, with `A` fixed at 2.0 and `Yt = 80 MPa`. That response is not mesh
  objective. It is not the cause of these failures, but it must be fixed with a
  sourced fracture energy before any mesh-convergence claim.
* **C3D4 linear tetrahedra** are the worst element for softening (constant
  strain, over-stiff). Not fixable today; record it as a limitation.
* **All three decks use the 23 °C material card**, including the 500 and
  1000 °C cases. V1_0 has no temperature dependence by design — that is what
  V3_0 adds. Our own correlations put E(500) 2 % and X_t(500) 0.3 % away from
  the RT values, so this is small, but it is an approximation to state.

## 5. The fix — all of it is card constants and step keywords

**No UMAT change is required. V1_0 stays frozen (CLAUDE.md).**
Applied by `abaqus/retune_deck.py`, which rewrites the cards and steps of an
assembled deck and leaves the mesh byte-identical.

| what | was | now | why |
|---|---|---|---|
| `dmax` (matrix 8/9, yarn 22/23) | 0.99 | **0.90** | residual stiffness 3.5 → 35 GPa; conditioning ÷10 |
| `eta` (10 / 24) | 0.02 | **0.05** | realised damage fraction per max increment 0.111 → 0.048 |
| `max_djump` (11 / 25) | 0.10 | **0.03** | the UMAT's own pre-emptive `PNEWDT` cutback fires 4× earlier |
| `*Static` | plain | **`stabilize=2e-4, allsdtol=0.05`** | the standard Abaqus/Standard cure for localisation |
| history output | — | **`ALLIE, ALLSD, ALLWK, ALLPD`** | so the artificial damping energy can be checked |
| `C_n^α` (displacement) | 0.08 | **1.0** | §2(a): this is what rejected the converged iteration |
| `I_R` | 10 | **16** | §2(b): secant Jacobian ⇒ linear convergence |
| `I_A` (cutbacks) | 20 | **8** | cutbacks were proven useless; fail in 2 min, not 23 |
| min increment | 1e-12 | **1e-8** | same |

`stabilize` is the one that most likely decides whether a curve comes out. It is
also the one that must be *reported*: the run is only admissible if
**ALLSD stays below ~5 % of ALLIE**, which is why the energy history is now
written. If ALLSD/ALLIE is larger than that, the peak stress is partly
artificial damping and the factor must be reduced.

### The physics knob, held separately

`--zero` sets `*Expansion, zero=`. It is **not** part of the numerical fix and
is left at 1050 °C in the main three decks. One extra RT23 deck is built at
`--zero 600` as an insurance run and as the first point of the TRS calibration
that §3 shows is needed. Choosing the stress-free temperature is a thesis
decision, not a solver setting.

## 6. What to check in the ODBs you already have

`postprocess/damage_census.py` reads a **partial** ODB and reports, per phase
and per step, the distribution of the damage criterion `r`, the damage `d`, and
the volume-averaged stress. Run it on the three ODBs from the failed jobs — it
costs no solver time and settles three open questions:

1. Is the measured matrix `r` after the cooldown really ≈ 0.97 (§3)?
2. ~~Is the volume-averaged matrix stress 302 MPa, i.e. 2.6× the XRD value?~~
   **ANSWERED:** measured **+268.08 MPa**, **2.34×** the XRD value. The
   mean-field estimate was 13 % high; the conclusion stands.
3. Does SDV10 (`ATEFF`) show elements clamped at `A = 50` (§4)?

---

# Round 2 — why `M1FIX_c26k_RT23` (2026-07-29) also stopped

The retuned deck got **49 % further**: the tension step reached step time
0.133 against 0.0892, i.e. 0.063 % tensile strain against 0.042 %. The
cooldown converged in 402 increments with the iteration count climbing
smoothly from 1 to 8. Then it stalled again, and the `.msg` names the cause
outright.

## The failure is a two-cycle chatter, not softening

```
iteration 12   residual  5.104E-03   correction +1.709E-09   line search 2.674E-02
iteration 13   residual -3.833E-02   correction -1.709E-09   line search 0.196
```

The correction has **the same magnitude and the opposite sign** on successive
iterations — a textbook 2-cycle limit cycle. The displacement increment is
1e-9 mm, so the strain is not changing, yet the residual moves by a factor of
7.5 and the line search collapses to 2.7 % of the Newton step. A continuous
constitutive law cannot do that. Something is switching.

## There is exactly one switch, and it is Ge Eq.13

```fortran
IF (AI1.GE.0.0D0) THEN
   DACT=DTN          ! tensile damage
ELSE
   DACT=DCN          ! compressive damage
END IF
```

A point that damaged in tension carries `DTN` up to `dmax` while `DCN` is
still 0, because compressive damage never initiated. The moment `I1` crosses
zero the secant stiffness jumps from `E(1-DTN)` back to `E` — a factor of 10
at `DTN = 0.9`. The yarn routine has no such switch: it combines its four
modes multiplicatively, which is smooth.

Measured directly in the **compiled** Fortran (`cross_check_fortran.py`, case
"MATRIX (I1=0 continuity)"), sweeping a fixed deviatoric state through
`I1 = 0` with `d_t = 0.8` carried in:

| HSMO | largest stress step across `I1 = 0` |
|---|---|
| **0 (published)** | **78.0×** the typical step |
| 0.1 | 2.3× — continuous |

## Why this RVE in particular: 1185 sliver tetrahedra

The `.dat` element-quality check reports

```
***WARNING: 1185 elements are distorted.
```

* **1185 of 26452 (4.5 %) — and every single one is in the MATRIX.** Zero
  yarn elements are flagged. TexGen meshes the tow surfaces cleanly and fills
  the gaps between them with slivers.
* Worst quality **0.00089** against Abaqus's recommended > 0.02; **549 fall
  below it**. Worst minimum dihedral angle **0.313°** against the recommended
  > 10°; **428 are below 1°**.
* Both runs died on the **same nodes**: 1080 and 1081, **DOF 3** (through
  thickness). Node 1081 has **21 % distorted neighbours against a 4.1 %
  mesh-wide baseline** — five times the average. The driver with the most
  residual hits over the whole run is ConstraintsDriver2, which carries the
  through-thickness normal strain.

A sliver has a wildly anisotropic stress state, which makes `I1 ≈ 0` easy to
sit on. Slivers and the unsmoothed switch are the same failure.

## The fix: smooth the switch in V3_0, leave V1_0 frozen

`KMTRX31` gains an optional `HSMO`:

```
w      = 0.5*(1 + tanh(I1/(HSMO*Xt)))
d_act  = w*d_t + (1-w)*d_c
```

* `HSMO = 0` is the published step **bit for bit** — 28/28 cross-check states
  match V1_0 to 1.58e-15 on both the 22-slot and the new 25-slot card, so the
  Zhang replication is untouched and the T2 regression still holds.
* Only `d_act` is blended. The criteria keep their published routing and both
  `d_t` and `d_c` stay monotonic, so the blend creates and heals nothing.
* Card layout `25 + 4*NT`: slot `24+4*NT` = HSMO, slot `25+4*NT` = guard 32.0.
  The three matrix lengths 22, `23+4*NT` and `25+4*NT` are 2, 3 and 1 modulo
  4, so NPROPS alone identifies the layout and V1_0 **rejects** the new card
  rather than misreading it.

This is a regularisation with a reportable width, not a change of model. The
thesis must state HSMO and show that the answer is insensitive to it — run
0.05 and 0.2 once the calibration converges.

## If round 3 also stalls

Then the mesh is the binding constraint, not the constitutive law. Smoothing
removes the switch but cannot fix the conditioning of a 0.3° tetrahedron.
Re-mesh from TexGen with the matrix element quality raised, and **re-export
the `.ori` with it** — an old `.ori` on a new mesh converges silently with the
fibre directions wrong.

---

# Round 3 — the full `M1FIX_c26k_*` set (2026-07-30), and a correction

All four retuned jobs are in. Two of them changed the diagnosis, and one of
them refutes something this document previously asserted.

| job | step 2 is | reached | vs. the un-retuned run | wall | how it ended |
|---|---|---|---|---|---|
| `RT23` | tension | **0.0627 %** strain | +49 % | 23 min | minimum increment |
| `RT23_z600` | tension | **0.1339 %** strain | **2.14× RT23** | 3.8 h | minimum increment |
| `T500` | **reheat** | 68.0 °C | **−72 %** (was 186 °C) | **15.6 h** | increment budget exhausted |
| `T1000` | **reheat** | 147.1 °C | **−23 %** (was 185 °C) | **15.3 h** | increment budget exhausted |

## 1. The `max_djump` change was a mistake, and it cost 31 hours

`T500` and `T1000` did not diverge. They **crawled**: 12888 attempts of which
**2888 failed**, at a **median time increment of 9.5e-08** against the 2.5e-03
maximum — a factor of 26 000 down — until the 10 000-increment budget ran out.
Both burned more than fifteen hours to reach *less* of the reheat step than the
un-retuned deck had reached in 25 minutes.

Tightening the UMAT's own pre-emptive cutback from `max_djump` 0.10 to 0.03
multiplied the number of cutbacks without making any of them succeed. With a
22 % failure rate Abaqus can never grow the increment back, so the step never
recovers. **`max_djump` is reverted to 0.10 and the increment budget is capped
at 2000**, so a crawling job now dies in about two hours instead of fifteen.
Nothing useful happened in the last 8000 increments of either run.

## 2. Lowering the stress-free temperature is the only change that clearly helped

`RT23_z600` is `RT23` with `*Expansion, zero=` moved from 1050 °C to 600 °C —
the same numerics, less thermal residual stress. It reached **2.14× the tensile
strain**, with only 8 unconverged attempts against RT23's 10, and a median
increment 50× larger than the reheat jobs managed.

This is the cleanest evidence yet for §3 of this document: **the binding
constraint is the TRS-induced pre-damage, not the solver settings.** Reduce the
residual stress and the analysis goes further, immediately. It also promotes
`zero=` from an insurance case to a main variable — see Ch.4 §4.9-2.

## 3. CORRECTION: the sliver-element explanation does not survive

Round 2 of this document attributed the failure partly to the 1185 distorted
matrix elements, on the evidence that node 1081 — where `RT23` failed — has
21 % distorted neighbours against a 4.6 % mesh-wide baseline.

**That correlation was one node, and it does not generalise.** The four jobs
fail at different places, and the distortion density at those places is:

| node | job(s) | distorted neighbours | in a periodic-BC set? |
|---|---|---|---|
| 1081 | RT23 (M1, M1FIX) | 21 % (7 of 34) | no |
| 1080 | RT23 (M1, M1FIX) | 3 % (1 of 30) | no |
| **2867** | T500, T1000, z600 | **0 %** (0 of 28) | no |
| **2868** | T500, T1000, z600 | **0 %** (0 of 13) | FaceE |
| 5673, 550, 569 | z600, T500 | **0 %** | no |

Only 2 of the 8 failing nodes lie in a periodic-BC set, against a 40.7 %
baseline — periodic nodes are **under**-represented, not over. So neither mesh
quality nor the periodic boundary conditions explains the pattern, and the
element-quality warning should be reported as a **mesh-hygiene item, not as a
cause of the non-convergence.**

## 4. What does hold across all four jobs

**The through-thickness direction.** Counting which degree of freedom carries
the largest residual over the whole of step 2:

| job | DOF 1 | DOF 2 | **DOF 3** |
|---|---|---|---|
| RT23 | 2238 | 1 | 200 |
| T500 | 17 266 | 34 | **36 541** |
| T1000 | 14 069 | 132 | **40 871** |
| z600 | 2715 | 1 | **14 946** |

DOF 3 dominates in three of four, overwhelmingly in the two reheat jobs. It is
the thinnest direction (0.44 mm), it is matrix-dominated because no tow runs
through the thickness in a 2-D weave, and it is therefore the most compliant —
which is exactly where a stiffness discontinuity produces the largest
displacement response.

**And the signature is unchanged.** `z600`'s last iteration:

```
LINE SEARCH SCALE FACTOR = 4.408E-02
AVERAGE FORCE 0.159    residual -0.150 AT NODE 2867 DOF 3
LARGEST CORRECTION TO DISP. -1.499E-14
```

A residual at **94 % of the average force** with a displacement correction of
1.5e-14 and the line search collapsed to 4 %. The displacement is frozen and
the stress is not. That is a discontinuous constitutive law and nothing else.

**Why the reheat is the worst step.** During tension only the subset of points
whose local `I1` happens to sit near zero can chatter. During the reheat the
whole matrix unloads *through* zero, progressively, as the temperature rises —
so the chatter is sustained across the entire step. That is why `T500` and
`T1000` never got going while `RT23` ran at full increment size for 74
increments before hitting its wall.

## 5. Consequences

* The `sign(I1)` smoothing (§ Ch.3 3.4.3) is the right fix and the reheat jobs
  should benefit from it most.
* `max_djump` back to 0.10, increment budget capped at 2000.
* `zero=600` becomes a main case, not insurance.
* The element-quality finding is demoted to mesh hygiene; it must still be
  fixed before any mesh-convergence claim, but it is not why these jobs stopped.

---

# Round 4 — the M3 results (2026-07-30)

M3 = HSMO 0.1 + `djump` 0.10 + `inc` 2000. Four jobs run in parallel.
**`RT23_z600` completed.** The other three stopped, but every one of them went
dramatically further than M1FIX, and the failure moved to a different place.

| 잡 | 결과 | 마지막 스텝 | 도달 | 벽시계 | M1FIX 대비 |
|---|---|---|---|---|---|
| `RT23_z600` | **성공** | 인장 | **100 %** | 0.71 h | 완주 |
| `RT23` | 정지 | 인장 | 98.2 % | 3.54 h | — |
| `T500` | 정지 | **인장** | 67.3 % | 1.05 h | 15.6 h → **1.05 h** |
| `T1000` | 정지 | **인장** | 57.2 % | 0.64 h | 15.3 h → **0.64 h** |

## 1. The reheat step is fixed. Completely.

This is the headline and it is unambiguous. `T500` and `T1000` died **in the
reheat step** in M1FIX. In M3 they walk through it and die in the *tension*
step, two steps later.

| 스텝 | 잡 | 증분 | 실패 시도 | 증분 크기 중앙값 | 반복/시도 |
|---|---|---|---|---|---|
| 냉각 (1) | 전부 | 402 | **0** | 2.5e-03 (최대) | 2.5–5.0 |
| **재가열 (2)** | T500 | 404 | **0** | **2.5e-03 (최대)** | **2.3** |
| **재가열 (2)** | T1000 | 403 | **0** | **2.5e-03 (최대)** | **2.6** |

Zero failed attempts, full increment size, 2.3 equilibrium iterations per
increment. In M1FIX the same step ran 12 888 attempts with 2 888 failures at a
median increment of 9.5e-08 and never finished.

The `sign(I1)` discontinuity was the cause of the reheat failure and the tanh
blend removed it. Round 3 predicted exactly this ("the smoothing should help
the reheat jobs most"); the prediction is confirmed. **This is a Ch.3 result,
not just a numerical convenience** — it is direct evidence for the V3_0
feature T3.

## 2. What is still failing is not the material. It is the free macro drivers.

Reading the `.msg` iteration by iteration: the residual is almost never on the
loaded driver. It sits on the drivers that carry **no** boundary condition.

Nodes 5681–5686 are the periodic-BC `ConstraintsDriver` dummy nodes, not
material points:

| 절점 | 드라이버 | 의미 |
|---|---|---|
| 5681 | ConstraintsDriver0 | `eps_xx` ← **유일하게 하중이 걸린 것** |
| 5682–5683 | 1, 2 | `eps_yy`, `eps_zz` (자유, 포아송) |
| 5684–5686 | 3, 4, 5 | `eps_xy`, `eps_xz`, `eps_yz` (자유, 전단) |

Where the residual actually sat, over each whole run:

| 잡 | 매크로 드라이버 위 | 그중 하중 드라이버 | 메시 절점 위 |
|---|---|---|---|
| RT23 | **63.4 %** | 3 회 (0.03 %) | 36.6 % |
| T500 | **69.8 %** | 153 회 (4.3 %) | 30.2 % |
| T1000 | **84.5 %** | 289 회 (7.6 %) | 15.5 % |
| z600 | **75.1 %** | 2 회 (0.08 %) | 24.9 % |

At the moment of death it is even more lopsided — 11 of `T1000`'s last 12
iterations and 13 of `RT23`'s last 14 are on a **shear** driver.

### The residual there is physically meaningless at the level demanded

The driver reaction is `R = sigma * V_RVE`, with `V_RVE` = 5.390 mm³. So a
residual on a free driver *is* the macro stress error:

| 잡 | 마지막 잔차 | 매크로 응력 오차 | 축 응력 대비 |
|---|---|---|---|
| RT23 | 3.959e-03 N·mm | **7.3e-04 MPa** | ~4e-06 |
| T1000 | 4.310e-02 N·mm | **8.0e-03 MPa** | ~4e-05 |
| T500 | 8.249e-02 N·mm | **1.5e-02 MPa** | ~8e-05 |

Abaqus judges these against 0.5 % of the global average nodal force (~0.15 N·mm
here), i.e. it demands the traction-free stresses vanish to **1.4e-04 MPa**
while the axial stress being measured is 100–200 MPa. The tolerance is five
orders of magnitude tighter than the quantity of interest. The jobs were not
failing on physics; they were failing on a criterion applied at the wrong scale.

### It is not a step-size problem

`T1000` increment 259 was retried 8 times, `dt` from 2.44e-06 down to 3.05e-07
— an 8× reduction that left the residual essentially unchanged (−3.4e-02 →
−4.3e-02). `RT23` ran at `dt` = 1e-08 with Newton corrections of **1e-19 to
1e-22** — the correction is zero to machine precision while the residual is
not. Per the standing rule: if cutting `dt` does not move the residual, the
increment size is not the problem.

### The free drivers genuinely go singular

`RT23` is the only job that reported numerical singularities — 36 of them, all
on the driver nodes:

```
***WARNING: SOLVER PROBLEM. NUMERICAL SINGULARITY WHEN PROCESSING NODE 5684
            D.O.F. 1 RATIO = 25.7164E+09 .
```

Node 5684 = `eps_xy`, node 5682 = `eps_yy`, 18 times each. A pivot ratio of
2.6e+10 means the macro tangent for those components has effectively vanished.
Physically that is a damage band percolating across the RVE: once it does, the
two halves can shear past each other at almost no cost, and the macro shear
stiffness — which is what that driver's diagonal *is* — goes to zero.

`RT23` is also the most TRS-pre-damaged case (`zero` = 1050 °C), and it is the
only one to reach that state. Consistent.

## 3. Corrections to Round 3

Round 3 read the residual DOF histogram as "DOF 3, the through-thickness
direction, is the common thread." **That reading was wrong**, for two reasons,
and both are worth recording because they were avoidable.

1. **The node numbers were not checked against the deck.** Nodes 5681–5686 are
   dummy drivers with a single active DOF each. Their "DOF 1" is not the global
   x-direction of any material point — it is that driver's only degree of
   freedom. Counting them alongside mesh DOFs mixed two different things.
2. Once drivers are separated out, the mesh-node DOF histogram in M3 is
   1: 2794 / 2: 2106 / 3: 1493 for `RT23` — no through-thickness dominance at
   all.

The Round 3 *physical* argument (through-thickness is matrix-dominated and most
compliant) is still sound as far as it goes, and the reheat diagnosis built on
it was correct — the fix worked. But the DOF evidence offered for it was
misread, and the conclusion happened to be right for a reason other than the
one given. Recording that distinction matters more than the outcome.

**Standing rule added:** before attributing a convergence failure to a node,
look the node number up in the deck.

## 4. What is already usable, before any re-run

`AVERAGE FORCE` through the tension step, as a load proxy:

| 잡 | 인장 스텝 거동 | 피크 위치 | 판정 |
|---|---|---|---|
| z600 | 0.168 → **0.174** → 0.172 | 스텝의 76 % | **피크 통과, 완주** |
| T500 | 0.129 → **0.163** → 0.159 | 스텝의 60 % | **피크 통과** |
| RT23 | 0.242 → 0.143, 계속 평탄/하강 | 시작 직후 | **상승 구간 자체가 없음** |
| T1000 | 0.060 → **0.149**, 마지막까지 상승 | 마지막 증분 | **피크 미도달** |

Three of the four already contain the peak. Only `T1000` genuinely needs more.
The dead `.odb`s hold every converged increment, so **extract before re-running**.

`RT23` having no rising branch at all is itself a physical result: at
`zero` = 1050 °C the matrix is already so TRS-cracked that the tensile response
starts at its peak. `z600`, identical in every numerical respect, has a proper
rising branch. That is the same conclusion as the Round 3 `z600` comparison,
now visible in the load history rather than only in how far the job got.

## 5. Consequences — the M4 deck

* **Lock the three shear drivers**: `eps_xy = eps_xz = eps_yz = 0`, restated in
  every step. For a balanced orthogonal 2-D weave loaded along a principal
  material axis these are zero by symmetry, so this removes three
  near-singular DOFs at no physical cost — and it targets exactly the DOFs the
  jobs died on.
  **This is an assumption about the mesh, not a fact.**
  `postprocess/driver_audit.py` measures the macro shear stress on the existing
  `.odb`s; if it is not under 1 % of `sigma_xx`, the lock is a real modelling
  change and has to be declared in the thesis instead of assumed away.
* **Relax the force residual ratio** from Abaqus' 0.005 to 0.02. At 0.02 the
  tolerance is ~5.6e-04 MPa of macro stress, still four orders below the axial
  stress. This one is a judgement call, it applies to the mesh equations too,
  and it goes in the thesis as a stated numerical setting.
* Everything else is unchanged from M3: HSMO 0.1, `djump` 0.10, `inc` 2000,
  `dmax` 0.90, `eta` 0.05, `stabilize` 2e-04. The M3→M4 deck diff is exactly
  these two changes and nothing else (verified by diff; mesh and material
  blocks are byte-identical).
