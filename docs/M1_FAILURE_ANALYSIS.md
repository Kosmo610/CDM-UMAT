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

## There is exactly one switch, and it is Ge Eq.7

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
