# Ge 2018 원문 추출 보고서 — 구성모델 원전 확정

**원전:** J. Ge, C. He, J. Liang, Y. Chen, D. Fang,
*"A coupled elastic-plastic damage model for the mechanical behavior of
three-dimensional (3D) braided composites,"*
**Composites Science and Technology 157 (2018) 86–98.**
저장소 파일: `refs/[24] 3D C-SiC 물성 B01.pdf` (13쪽, 전문 판독 완료)

**이식 대상(replication target):** Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang,
*Ceramics International* **48** (2022) 3109–3124 — `refs/[05] 3D C-SiC 물성 A05.pdf`
(Zhang은 §3.1 각주에서 모델 수식을 Ref.[17] = Ge 2018로 위임한다.)

작성일 2026-08-11 · 원문 판독 기준 · **기존 저장소 파일은 일절 수정하지 않았음**

---

## 요약 (3줄 헤드라인)

- **확정된 것 —** Ge Table 3은 실재하고 우리가 인용해 온 `G_f,1t = 12.5`,
  `G_f,2(3)t = 1.0 N/mm`가 그대로 실려 있다. 그리고 **`G_f,1c = 12.5 N/mm`도
  Table 3에 명시적으로 인쇄되어 있다.** Ge Table 2의 T300 물성 7개는 Zhang Table 1과
  **완전히 동일**하다. `CALIBRATION_GUIDE.md §4`의 "Ge 2018 §3.2는 점성계수를 작게
  유지하라고 한다"는 귀속은 **stale가 아니라 정확**하다 — 해당 문장이 p.92 식 (30)
  직후에 그대로 있다.

- **뒤집힌 것 —** ① 저장소가 여러 곳(특히 `docs/M1_FAILURE_ANALYSIS.md:217`의 절
  제목과 `UMAT_CSIC_THERMSHOCK_V3_0.for` 5개소)에서 인장/압축 손상의 sign(I₁) 스위치를
  **"Ge Eq.7"**이라 부르는데, Ge 식 (7)은 **매트릭스 손상 컴플라이언스 행렬 S_m(d_m)**이고
  sign(I₁) 스위치는 **Ge 식 (13)**이다. ② `G_f,1c`를 "근거 없이 G_f,1t와 같다고 가정"으로
  적은 서술은 **근거가 원문에 있으므로 무효**다. ③ Hashin의 α·β 가중계수는 **Ge에 없다** —
  Zhang이 자기 식 (11)에서 도입하고 1로 놓은 것이다. ④ `THESIS_PLAN.md:18`의
  **"Ge Eq.(1)–(33) 전량 구현"은 거짓**이다 — 식 (31)–(33)(consistent tangent)은
  미구현(secant 사용)이고 식 (25)–(28)은 선형경화 전용 1-step으로 축약되어 있다.
  ⑤ `r_F`는 자유 knob이 아니라 Ge 식 (17)에서 X_f,PO로부터 **유도되는 종속량**이다.

- **원문에도 없는 것 —** **X_f,PO(pull-out 응력)와 K_f,1(선형연화 기울기)의 수치는
  Ge 2018 어디에도 없다.** Table 2·Table 3·§4.4 재료 특성화 절·Fig. 1(b) 어디에도
  숫자가 없다. Zhang 2022도 자기 식 (18) 밑에서 이 보조변수들을 다시 Ref.[30]으로
  넘긴다. **따라서 "선언된 knob" 분류는 X_PO와 K1에 대해 유지된다** (r_F만 격하).
  또한 손상지수 A_f,I / A_m,J의 수치도 없다 — Ge는 이것을 Table 3의 파괴에너지에서
  식 (19)–(21)로 **유도하도록** 설계했다.

---

## A. 식 번호 귀속 확정표

> ⚠️ **번호 충돌 주의.** Ge와 Zhang은 서로 다른 번호를 쓴다. 저장소의
> `VERIFICATION_REPORT.md §3` 표는 헤더가 "Paper Eq."이지만 **Zhang 번호와 Ge 번호가
> 섞여 있다** (예: 같은 표 안에서 "(19) Matrix exponential"은 Zhang, "(19–21) Crack-band"는
> Ge). Zhang에는 균열대 정규화 식 자체가 없다. 아래 표는 두 계열을 분리한다.

| # | 항목 | 우리 표기 | **Ge 2018 실제** | Zhang 2022 실제 | 판정 | 근거 |
|---|---|---|---|---|---|---|
| 1 | 얀 유효응력 / 손상-컴플라이언스 | "(2)–(4)" 또는 "(2)–(3)" | **(1) ε_f=S_f(d_f):σ_f, (2) S_f(d_f) 행렬, (4) σ̃_f=S_f0⁻¹:ε_f** | (2) σ_y=C_y(d):ε_y^e, (3) σ̃_y=M(d):σ_y, (4) M(d)=diag | **부분 확정** | Ge p.87 식(1)(2), p.88 식(4). 우리 "(2)–(3)"은 **Zhang 번호**로 맞고 **Ge 번호로는 (1)–(2)+(4)** |
| 2 | 전단 손상 커플링 | "(3)" | **(3)** — `d_f,4=1−(1−d_f,1)(1−d_f,2)`, `d_f,5=1−(1−d_f,2)(1−d_f,3)`, `d_f,6=1−(1−d_f,3)(1−d_f,1)` | 해당 식 없음(Zhang은 d₄~d₆를 독립 슬롯으로만 둠) | **확정 ✅** | Ge p.87 식 (3). 원문: *"the damage variables d_f,4, d_f,5 and d_f,6 are not independent, and can be expressed as a function of the remaining variables"* |
| 3 | 매트릭스 변형률 분해 | "(6)" ε=εe+εp+εth | **(5) `ε_m = ε_m^e + ε_m^p` — 열변형률 항 없음** | **(6) `ε_m = ε_m^e + ε_m^p + ε_m^th`** | **뒤집힘(번호) / Zhang 기준 확정** | Ge p.88 식 (5): *"the total strain tensor is decomposed into an elastic part ε_m^e and a plastic part ε_m^p"*. Ge는 등온(상온) 모델이라 ε^th가 아예 없다. ε^th는 **Zhang 식 (6)·(10)**의 추가분 |
| 4 | 매트릭스 von Mises 항복 + 등방경화 | "(8)–(9)" / "(9)" | **(8) 항복함수 `F(σ̃_m,ε̄_m^p)=f(σ̃_m)−σ̃_s(ε̄_m^p)=0`, (9) 연합유동 `ε̇_m^p=λ̇r=λ̇ ∂F/∂σ̃_m`, (10) `ε̄̇_m^p=λ̇`** | (9)만 (항복함수는 본문 서술) | **확정 ✅** ("(8)–(9)" 정확, "(9)"만 쓴 곳은 불완전) | Ge p.88 식 (8)(9)(10) |
| 5 | 매트릭스 등방 강성 저감 | "(7)" | **(7) — `S_m(d_m)` 손상 컴플라이언스 행렬** (대각 `1/(1−d_m)`, 비대각 `−ν_m`, 전단 `2(1+ν_m)/(1−d_m)`, 전체에 `1/E_m`) | (7) σ_m=C_m(d):ε_m^e | **확정 ✅ (단, 별건 오귀속 있음)** | Ge p.88 식 (7). **주의:** 저장소가 sign(I₁) 인장/압축 스위치를 "Ge Eq.7"이라 부르는 것은 **오귀속** — 아래 6번 참조 |
| 5b | 인장/압축 손상 선택(sign I₁) | "Ge Eq.7" ← **오귀속** | **(13)** `φ_m,t=σ̄_m/X_m,t ≥1 if Ī_m,1=σ̃_m,11+σ̃_m,22+σ̃_m,33 ≥ 0`; `φ_m,c=σ̄_m/X_m,c ≥1 if Ī_m,1 < 0` | (15)·(16) | **부정 ❌** | Ge p.89 식 (13). *"Ī_m,1 is the first-invariant of the effective stress tensor of matrix"* |
| 6 | 3D Hashin 개시기준(얀), 전 모드 | "(11)–(14)", α=β=1 | **(12) 한 덩어리에 4모드 전부**: φ_f,1t, φ_f,1c, φ_f,2(3)t, φ_f,2(3)c. **α·β 가중계수 자체가 없다 — 모든 전단항 계수가 1** | (11) 1t **(α, β 포함)**, (12) 1c, (13) 2(3)t, (14) 2(3)c | **부정 ❌ (α·β의 출처)** | Ge p.89 식 (12). Zhang p.3112: *"α, β were the factors which changed in different damage models and **were settled as 1 in this paper**"* → **α=β=1은 Zhang의 선언이지 Ge의 것이 아니다** |
| 7 | 지수형 손상 진화 | "(17)" 얀 / "(19)" 매트릭스 | **(16) 1행** `d_f,I = 1 − (1/r_f,I)·exp[A_f,I(1−r_f,I)]`, (I = 1c, 2t, 2c, 3t, 3c) / **(18)** `d_m,J = 1 − (1/r_m,J)·exp[A_m,J(1−r_m,J)]`, (J = t, c) | (17) 얀 / (19) 매트릭스 | **Zhang 번호로 확정 ✅ / Ge 번호로는 (16)·(18)** | Ge p.89 식 (16)(18) |
| 8 | 종방향 인장 혼합 선형–지수 법칙 | "Ge Eq.16–17" / "Zhang Eq.18" | **(16) 2행** `d_f,1t = 1 − ((1−d^L_f,1t)/r^F_f,1t)·exp[A_f,1t(1−r^F_f,1t)]` + **(17)** 보조변수 3식 | **(18)** | **확정 ✅ (양쪽 다 맞음)** | Ge p.89 식 (16)(17), Fig. 1(b). Zhang p.3112 식 (18) |
| 9 | 균열대(crack-band) 정규화 | "(19)–(21)" | **(19) `g_M = G_M/l*` (M = f,1t; f,1c; f,2t; f,2c; f,3t; f,3c; m,t; m,c), (20) `g_M=∫(∂G/∂d_M)ḋ_M dt`, (21) `∫₁^∞ (∂G/∂d_M)(∂d_M/∂r_M) dr_M = G_M/l*`** + 자유에너지 **(22) 얀 G_f**, **(23)(24) 매트릭스 G_m** | **Zhang에는 없음** | **확정 ✅ (Ge 번호)** | Ge p.90 식 (19)(20)(21). *"based on the crack band theory proposed by Bazant [21]"*; *"The softening parameters A_M obtained by Eq. (21) can ensure that the calculated dissipated energy is independent of mesh refinement"* |
| 10 | 점성계수 η를 "작게" 유지하라는 권고 | `CALIBRATION_GUIDE.md §4`: "Ge 2018 §3.2는 '작게 유지'라고 한다" | **확정 ✅ — §3.2 "Viscous regularization for damage variables", p.92, 식 (30) 직후** | — | **확정 ✅ (stale 아님)** | Ge p.92 원문 그대로: *"Note that, it is important to use the viscosity parameter with a **small value (small compared to the characteristic time increment)** which can help improving the rate of convergence of the model in the softening regime, without compromising results."* |

**추가 확정 — 점성 정규화 식 자체.** Ge 식 (29) Duvaut–Lions:
`ḋ^v_f,I = (1/η)(d_f,I − d^v_f,I)`, `ḋ^v_m = (1/η)(d_m − d^v_m)`;
식 (30) backward-Euler: `d^v_{f,I,n+1} = Δt/(η+Δt)·d_{f,I,n+1} + η/(η+Δt)·d^v_{f,I,n}`.
→ 우리 UMAT의 `GAM = DTIME/(ETA+DTIME)`
(`src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for:236, :425`)와 **정확히 일치**.

---

## B. 파라미터 값 — Ge Table 2·Table 3 전체 전사

### B-1. Ge **Table 2** — "Material properties of T300 [25]" (p.93)

| | E₁ (GPa) | E₂ (GPa) | G₁₂ (GPa) | G₂₃ (GPa) | μ₁₂ | X_t (MPa) | X_c (MPa) |
|---|---|---|---|---|---|---|---|
| **T300** | **230** | **40** | **24** | **14.3** | **0.26** | **3580** | **2470** |

**Zhang Table 1과의 대조 (Zhang p.3113, "Material properties of T300 [34,35]"):**

| | E₁ | E₂ | G₁₂ | G₂₃ | ν₁₂ | X_t | X_c | α₁ (×10⁻⁶/K) | α₂₍₃₎ (×10⁻⁶/K) |
|---|---|---|---|---|---|---|---|---|---|
| Zhang | 230 | 40 | 24 | 14.3 | 0.26 | 3580 | 2470 | **−0.3** | **3.1** |
| Ge | 230 | 40 | 24 | 14.3 | 0.26 | 3580 | 2470 | (없음) | (없음) |

**판정: 7개 항목 완전 일치 ✅.** Ge는 등온 모델이라 **CTE 두 개(α₁, α₂₍₃₎)는 싣지 않는다.**
→ `CALIBRATION_GUIDE.md:184`의 "Ge Table 2 = Zhang Table 1" 서술은 **탄성/강도 7항목에
한해 정확**하며, CTE는 Zhang 고유 데이터임을 부기해야 한다.

### B-2. Ge **Table 3** — "Material properties of matrix and yarn [27,29]" (p.94) — **전 행 전사**

**Matrix (탄소/**페놀 수지**):**

| E_m (GPa) | ν_m | X_m,t (MPa) | X_m,c (MPa) | S_m,s (MPa) | G_m,t(c) (N/mm) |
|---|---|---|---|---|---|
| **3.2** | **0.35** | **75** | **180** | **60** | **1.0** |

**Yarn (T300/페놀 단방향 등가체, Chamis 경험식으로 산출):**

| 항목 | 값 | 항목 | 값 |
|---|---|---|---|
| E_f,1 (GPa) | **196.03** | E_f,2(3) (GPa) | **22.05** |
| ν_f,12(13) | **0.268** | ν_f,23 | **0.375** |
| G_f,12(13) (GPa) | **9.35** | G_f,23 (GPa) | **7.38** |
| X_f,1t (MPa) | **2556** | X_f,1c (MPa) | **1263** |
| Y_f,2t (MPa) | **70** | Y_f,2c (MPa) | **170** |
| S_f,12(13) (MPa) | **58** | S_f,23 (MPa) | **46** |
| **G_f,1t (N/mm)** | **12.5** | **G_f,1c (N/mm)** | **12.5** |
| **G_f,2(3)t (N/mm)** | **1.0** | **G_f,2(3)c (N/mm)** | **1.0** |

**출처 문장 (Ge p.96, §4.4):** *"The material properties of the yarn including stiffness
and strength can be calculated by the empirical formulae proposed by Chamis [28].
Table 3 lists the material properties of matrix and yarn for simulation, and the values
of the fracture toughness are taken from Ref. [29]."*
Ref.[29] = X. Li, W.K. Binienda, R.K. Goldberg, *J. Aero. Eng.* **24** (2) (2010) 170–180.

#### ★ B-2 판정 1 — `G_f,1c`

> **저장소가 "G_f,1c = G_f,1t = 12.5를 근거 없이 가정"이라고 적어 온 것은 무효다.**
> Ge Table 3은 **`G_f,1c (N/mm) = 12.5`를 독립 셀로 명시**한다. 값이 우연히 같을 뿐,
> 가정이 아니라 **인용**이다. `check_card_ranges.py:174`의 G1c 행 주석("the same
> carbon/PHENOLIC table that supplies G1t")은 사실상 맞지만, "동일 값을 가정"이라는
> 뉘앙스가 남아 있는 다른 문서(`VERIFICATION_REPORT.md:199`는 G1c를 아예 언급하지 않음)는
> 보정 필요. **DEV 등급 자체는 유지된다 — 사유는 '값이 없다'가 아니라 '페놀 매트릭스'다.**

#### ★ B-2 판정 2 — 횡방향 파괴에너지

Ge는 `G_f,2(3)t = G_f,2(3)c = 1.0 N/mm`를 **공개한다.** 우리 카드는 `Gtt = Gtc = 0.0`
(균열대 OFF, A=2.0 고정)이다 → 이는 **원전이 값을 안 준 것이 아니라 우리가 끄고 있는 것**이다.
`check_card_ranges.py:184-190`의 Gtt/Gtc 행 사유("no transverse compressive fracture
energy for C/SiC exists")는 C/SiC에 한해 맞지만, **Ge가 페놀계에 대해 1.0을 공개했다는
사실이 누락**되어 있다. `m6_calibration_plan.py`의 "Gtt를 켜는 것이 최소 정당화 부채로
최대 물리를 움직인다"는 결론을 **원전 근거로 강화**할 수 있다.

#### ★ B-2 판정 3 — **X_PO / r_F / K1 : "선언된 knob" 분류 검증**

전 표·전 본문·Fig. 1(b)를 훑은 결과:

| 우리 기호 | Ge 기호 | 정의 위치 | **수치 공개?** | 판정 |
|---|---|---|---|---|
| `X_PO` (36번 슬롯) | **`X_f,PO`** | Ge 식 (17) 3행, Fig. 1(b) 세로축 눈금 | **없음 ❌** | **"선언된 knob" 유지 ✅** |
| `K1` (38번 슬롯) | **`K_f,1`** | Ge 식 (17) 1행. 원문: *"where K_f,1 is the slope of the linear softening law"* | **없음 ❌** | **"선언된 knob" 유지 ✅** |
| `rF` (37번 슬롯) | **`r^F_f,1t`** | Ge 식 (17) 3행 | **없음 (수치) — 그러나 자유 파라미터도 아님** | **격하 ⚠️ — 종속량** |

**Ge 식 (17) 전문 (p.89):**
```
d^L_f,1t = 1 + K_f,1/E_f,1 − (1 + K_f,1/E_f,1) · (1/r^L_f,1t)
r^L_f,1t = max{1, min(r_f,1t, r^F_f,1t)}
r^F_f,1t = max{1, (1 − d^F_f,1t) · (X_f,1t / X_f,PO) · r_f,1t}          (17)
```
원문 설명: *"where K_f,1 is the slope of the linear softening law, and r^L_f,1t is the
auxiliary threshold value. **r^F_f,1t is the damage threshold value at the transition
between the linear and exponential damage evolution laws**, and d^F_f,1t, X_f,PO are the
corresponding values of the damage variable and stress."*

> **핵심 — r_F는 독립 입력이 아니다.** Fig. 1(b)에서 선형 가지는 X_f,1t에서
> **X_f,PO까지** 내려간 뒤 지수 가지로 전이한다. 즉 전이점은 (X_f,PO, K_f,1)로
> **결정**되며, `r^F_f,1t`와 `d^F_f,1t`는 그 전이점의 좌표일 뿐이다. 우리 카드가
> `rF = 3.0`을 **X_PO=700, K1=8000과 독립으로** 넣고 있다면, 세 값이 서로 모순된
> 전이점을 지시할 수 있다(과잉 매개변수화). **X_PO와 K1만 knob으로 두고 r_F는
> 이 둘에서 계산하는 것이 원전 충실**이며, 이는 M6 보정 차원을 5개에서 4개로 줄인다.

**Zhang 2022의 처리 (p.3112, 식 (18) 직후):** *"where A_y,I was the exponential damage
softening factor, and r_y,J was the damage threshold parameter. **d^L_y,1t and r^E_y,1t
were the auxiliary damage variables and their expressions could be found in Ref. [30].**"*
→ Zhang도 **수치를 주지 않고 다시 문헌으로 넘긴다.** 두 논문 어디에도 숫자가 없다는
우리의 진단이 **양방향으로 확인**되었다.

#### ★ B-2 판정 4 — 손상지수 A

Ge는 `A_f,I`·`A_m,J`의 **수치를 어디에도 싣지 않는다.** 대신 Table 3에 파괴에너지를
싣고 식 (19)–(21)로 **유도하게** 설계했다. 따라서 `VERIFICATION_REPORT.md:181`의
"Yarn softening A1t,A1c,Att,Atc / 2.0 (fixed) / **not listed**"는 **사실은 맞지만
프레이밍이 틀렸다** — "논문이 안 줌"이 아니라 "논문은 G에서 유도하라고 지시함"이다.
A=2.0 고정은 원전으로부터의 **의도적 이탈**로 기록되어야 한다.

#### ★ B-2 판정 5 — 얀 강도의 원전 대조

`check_card_ranges.py`의 얀 강도 행들을 Ge Table 3과 대조:

| 슬롯 | 우리 카드 | Ge Table 3 (페놀) | 현재 주석 상태 |
|---|---|---|---|
| 13 Yt | 80 | **70** | ✅ 이미 인용됨 |
| 14 Yc | 350 | **170** | ✅ 이미 인용됨 |
| 15 S12 | 120 | **58** | ❌ **누락** — "no tow-level shear strength found"라고 되어 있으나 Ge가 58 MPa를 준다 |
| 17 S23 | 100 | **46** | ✅ 이미 인용됨 |
| 11 Xt | 2835 | **2556** | ⚠️ Ge의 얀-레벨 값 미인용 (우리는 Vf·3580 혼합칙 사용) |
| 12 Xc | 1956 | **1263** | ⚠️ 동일 |

---

## C. 모델 이식 타당성 — 원문 근거 문장 (논문에 그대로 쓸 수 있는 형태)

### C-1. Ge가 **매트릭스 소성을 도입한 이유** (수지 연성)

> Ge p.89: *"The failure mode of the matrix is different from that of the fiber bundle.
> It can be seen from the experimental data in the literature that **the resin matrix
> shows a certain degree of plasticity** under both quasi-static tensile and compressive
> loads [3,14]. Therefore, as sketched in Fig. 2, the exponential damage evolution law
> is adopted to characterize the elastic-plastic damage of the matrix."*

→ **이식 위험의 핵심.** Ge의 소성 논거는 **에폭시/페놀 수지의 실측 연성**이다.
SiC 세라믹 기지에는 이 논거가 성립하지 않는다.

### C-2. Ge가 스스로 밝힌 **소성의 역할 = 비가역 변형률 생성** (기구 불특정)

> Ge p.88: *"In this model, the effective stress is used to couple the plasticity and
> damage effects in a single constitutive equation for matrix, because it can provide a
> simple way to separate the damage and plastic processes... **the isotropic damage
> accounts for the softening response and the decrease in the elastic stiffness, while
> the hardening plasticity is responsible for the development of irreversible strains.**
> In other words, the effect of plastic deformation which is driven by the effective
> stresses can be described independently from damage ones and vice versa."*

→ **이식을 정당화하는 문장.** Ge의 소성 모듈은 "금속적 전위 활주"를 주장하지 않고
**비가역 변형률을 만드는 현상론적 장치**로 정의되어 있다. 따라서 다른 기구(미세균열
마찰 슬립)로 생긴 잔류변형률에 **재해석하여 붙일 여지**가 원전 안에 이미 있다.

### C-3. Ge의 **등방 손상 근사 = 미세균열 연성저하의 근사**라는 자기 선언

> Ge p.88: *"The matrix is assumed to be isotropic homogeneous body. It has to be noted
> that for several specific damage modes, the matrix with micro-cracks is anisotropic.
> To simplify matter, this paper does not take into account the anisotropic damage of
> matrix, and **an isotropic elastic-plastic damage model is established to approximate
> the ductility degradation process due to micro-cracks.**"*

→ Ge 본인이 이 모듈의 물리적 대상을 **"미세균열"**로 명시했다. C/SiC 기지의 손상 기구도
미세균열이므로, **대상 기구는 오히려 일치**한다.

### C-4. Zhang의 이식 선언 — **"pseudo-ductility"의 현상론적 대체물**

> Zhang p.3111: *"inelastic residual strain will occur in the process of loading and
> unloading of C/SiC composites [9,21–23], which could be known as **'pseudo ductility'
> or 'pseudo plasticity'** [24–26]. In this paper, **to characterize the pseudo ductility
> behavior of the composites phenomenologically, it was assumed that the residual strain
> may be attributed to the plasticity of the SiC matrix. This plasticity of matrix could
> be caused by the micro-structures, such as defects existing in the matrix.** Therefore,
> a coupled elastic-plastic damage model [17] was adopted for the matrix."*

→ **우리 논문의 정직한 포지셔닝 문장은 이 조합으로 완성된다:**
> "Ge의 탄소성 손상 모듈은 수지의 실측 연성을 근거로 도입되었으나(Ge 2018, p.89),
> 원문은 그 소성부를 '비가역 변형률의 생성 장치'로, 손상부를 '미세균열에 의한 연성
> 저하의 등방 근사'로 각각 정의한다(Ge 2018, p.88). Zhang(2022)은 이 정의를 근거로,
> SiC 기지의 소성을 재료 고유의 연성이 아니라 **하중-제하 시 관측되는 pseudo-ductility의
> 현상론적 표현**으로 명시적으로 재해석하여 이식하였다. 본 연구도 동일한 유보 하에
> 이 모듈을 사용하며, SY0·HISO는 물성이 아닌 **잔류변형률 적합 파라미터**로 취급한다."

### C-5. Ge가 스스로 밝힌 **한계 — 온도와 계면이 모델에 없다** ★ 열충격 논문에 결정적

> Ge p.97 (Conclusions): *"However, further experiment for the 3D braided composites
> under quasi-static tensile and cyclic loadings would be needed for an advanced
> validation of the proposed elastic-plastic damage model, and **the effects of
> temperature and interface will be taken into account to complete the model.**"*

추가 정황:
- Ge §4.1: *"All the considered specimens were tested at **room temperature**."*
  → Ge의 검증은 **상온 준정적 인장 단일 조건**뿐이다.
- Ge §2 서두: *"the damage models ... are formulated within the framework of Continuum
  Damage Mechanics (CDM) using internal variables, and based on the **assumption of
  small strains**."*
- Ge 식 (5): **열변형률 항이 없다.** 온도 의존 물성도 없다.
- Ge §2.2: *"It has to be mentioned that the **Hashin criteria have been widely applied
  in the engineering, and it would be relatively straightforward to incorporate
  alternative initiation criteria.**"* → 개시기준 교체는 원전이 허용한다.

→ **본 논문의 novelty 근거이자 정직한 한계 서술:** 온도 효과·계면·반복하중은 Ge가
**"향후 과제"로 명시적으로 남긴 부분**이다. Zhang(2022)이 열잔류응력을 붙였고, 본 연구가
**반복 열충격에 의한 누적손상**을 붙인다 — 즉 우리가 추가하는 것은 원전이 비어 있다고
자인한 축이며, 이는 "무단 확장"이 아니라 **원저자가 지목한 확장 방향**이다.

---

## D. 구현 누락 점검 — Ge 식 (1)–(35) 대 우리 UMAT

`verification/VERIFICATION_REPORT.md:196-198`은 *"the UMAT implements Ge Eqs. (1)–(33)
in full"*이라고, `docs/THESIS_PLAN.md:18`은 *"Ge 2018 Eq.(1)–(33) 전량 구현"*이라고
주장한다. 원문 대조 결과:

| Ge 식 | 내용 | 우리 구현 | 판정 |
|---|---|---|---|
| (1)(2)(4) | 얀 손상 컴플라이언스·유효응력 | `KORTHO` + `KYARN30:266-277` | ✅ 구현 |
| **(3)** | **전단 손상 커플링 d₄,d₅,d₆** | `KYARN30:262-264`, V3_0 `:495-497` | ✅ **코드는 구현. 단 `VERIFICATION_REPORT.md §3` 매핑표에 이 행이 없다** → 문서 누락 |
| (5)(6)(7) | 매트릭스 분해·구성식·손상 컴플라이언스 | `KMTRX30:372, :435-445` | ✅ 구현 (+Zhang의 ε^th는 Abaqus `*Expansion`이 담당) |
| (8)(9)(10) | von Mises 항복·연합유동·등가소성변형률 | `KMTRX30:375-401` | ⚠️ **선형 등방경화 전용 1-step 폐형식.** Ge 식 (8)의 `σ̃_s(ε̄^p)`는 *"obtained from the **experimental hardening curve**"* — 즉 일반 비선형 경화곡선을 허용한다. 우리는 `SY0+HISO·p̄`로 고정 |
| (11)(12)(13) | 손상활성함수·3D Hashin·매트릭스 개시 | `KYARN30:195-211`, `KMTRX30:405-413` | ✅ 구현 (단 5b 오귀속) |
| (14)(15) | Kuhn–Tucker, r 임계값 이력 | `MAX(SV(·), φ)` 형태 | ✅ 구현 |
| (16)(17) | 지수형 + 혼합 선형–지수 | `KDAMAGE_TARGET`, `KMIX1T` | ✅ 구현 (V1_0 카드에선 X_PO=0으로 OFF) |
| (18) | 매트릭스 지수형 | `KDAMAGE_TARGET` | ✅ 구현 |
| (19)(20)(21) | 균열대 정규화 | `KABAND` | ✅ 구현 (폐형식) |
| **(22)** | **얀 Helmholtz 자유에너지 G_f** (6항 + 3개 Poisson 교차항) | `KABAND` 호출 시 `Xt²/(2E1)·CELENT` 단축 사용 | ⚠️ **단축 구현.** Ge 식 (22)는 다축 응력의 교차항(−ν₁₂/E₁·σ₁₁σ₂₂ 등)을 포함. 우리는 **1축 등가**만 쓴다. 1축 보정에는 정확하나 다축 상태에서는 원전과 다르다 |
| **(23)(24)** | **매트릭스 자유에너지 = 탄성분 + 소성분 `G_m^p(ε̄_m^p)`** | `KABAND(Xt²/(2E)·CELENT, GMT, ...)` | ✅ **구현 정확 — 2026-08-11 지적 철회.** 아래 표 밑의 철회문 참조. `G_m^p` 의 인자에 **`d_m` 이 들어 있지 않으므로** 식 (21)의 `∂G/∂d_m` 에 **정확히 0** 을 기여한다. 탄성분만 넣는 것이 옳다 |
| (25)–(28) | Backward-Euler 사영 + Newton–Raphson (`δΔλ`, `H_{n+1}=dσ̃_s/dε̄^p`) | `KMTRX30:375` *"Exact one step"* | ⚠️ **축약.** 선형경화에서는 등가, 비선형 경화곡선을 넣는 순간 무효 |
| **(29)(30)** | **Duvaut–Lions 점성 정규화** | `GAM=DTIME/(ETA+DTIME)` (`:236, :425`) | ✅ **정확히 일치** |
| **(31)(32)(33)** | **Consistent tangent** `C_f,t = S_f⁻¹(d^v):[I − M_f(d^v)]`, `M_f = Σ ∂S_f/∂d · σ · Δt/(η+Δt) · ∂d/∂ε`; 매트릭스는 (32) + 등가강성 (33) | V1_0은 `CTAN(I,J)=CD(I,J)` — **secant**(동결). **V3_0은 2026-08-11부터 카드 스위치 `ITAN`(+키 33.0) 뒤에 구현되어 있고 기본값은 OFF** | ⚠️ **구현됨(기본 OFF).** 손상 미분항 `M`을 얀·기지·거시 세 법칙 모두에 넣었고, 기지는 (32)+(33)을 **선형경화 반경귀환의 폐형식**으로 축약해 구현했다(일반 비선형 경화곡선에는 무효 — 그때는 식 (27)을 미분해야 한다). 합격 기준은 **UMAT 자신의 응력 갱신에 대한 중심차분 Jacobian**이며 전 영역 ≤ 6.9e-9로 일치한다(`verification/cross_check_fortran.py`, `TANGENT` 3개 군; docs/CH3_VERIFICATION.md §3.4.6). 연화 구간에서 보정항은 시컨트의 **206 %**다. η를 0.05에서 되돌릴 수 있는지는 **실메시 수렴 연구 미실시**이므로 스위치는 꺼 둔다 |
| (34)(35) | 3D 편조 기하 (γ, h, φ, a, b, c, 실 패킹계수 0.8) | 해당 없음 | N/A — **2D 평직에는 부적용.** "(1)–(33)"이라 쓴 것은 이 점에서 정당 |
| Suppl. App. A | 식 (21)의 수치적분 알고리즘 | 폐형식 대체 | ⚠️ 보충자료 미확보 |
| Suppl. App. B | `M_f`·`M_m` 성분 전개 | 미구현 | ❌ (31)–(33) 미구현과 동일 사안 |

### ★ 철회 — (23)(24) 「소성분 누락」 지적 (2026-08-11)

**이 표는 한때 (23)(24)를 "누락, 매트릭스 A_m 과대추정"으로 적고 있었다.
그것은 틀렸고, 원문을 읽어 철회한다.** `verification/plastic_dissipation_audit.py`
가 이 판정을 검사로 고정한다.

Ge p.90, 식 (23) 도입 문장 원문:

<details><summary>원문 (클릭)</summary>

> For matrix, the Helmholtz free energy G_m is the sum of the thermo-elastic
> G_m^e and the plastic G_m^p contributions. The elastic contribution G_m^e is
> affected by damage to model the experimentally-observed coupling between
> elasticity and damage through the effective stress, and **the plastic part
> G_m^p is the contribution due to plastic hardening** [16].

</details>

**판정의 근거는 항의 크기가 아니라 인자 목록이다.** 식 (24)에서 `G_m^p` 는
`ε̄_m^p` 만의 함수로 적혀 있고 `d_m` 이 들어 있지 않다 — 유효응력 커플링의
정의상 경화는 손상을 보지 않는다. 그런데 균열대 식 (20)(21)이 적분하는 것은
`∂G/∂d_M` 뿐이다. **손상이 없는 항은 미분하면 0이므로 `G_m^p` 는 `A_m` 에
정확히 0을 기여한다.**

크기로 보면 사소한 문제가 아니었다 — 카드값에서 `G_m^p` = 0.168 N/mm² 로
`G_m^e` = 0.1373 N/mm² **보다 크다**(저장 에너지의 55 %). 잘못 넣었다면
`A_m` 이 RVE 평균 요소에서 **2.75배**, 최대 요소에서 **8.29배** 움직였을 것이다.
게다가 원래 지적은 부호도 반대였다 — 넣으면 `A_m` 은 **올라간다**.

**대신 기록해야 할 진짜 한계.** 소성 일은 국부화 띠 안에서 함께 소산되는데,
**소성 소산은 균열대가 정규화하지 않는다.** 손상 소산은 `G_M` 으로 고정되지만
소성 소산은 띠 부피에, 즉 `l_e` 에 비례한다. 따라서 국부화한 기지 요소의
**총** 소산 에너지는 균열대가 완벽히 작동해도 메시 의존이다. 카드값에서 그
몫은 RVE 평균 요소 16.1 %, 최대 요소 42.3 %, 균열대 막대 N=5 에서는 90.5 %다
(막대가 거칠수록 소성이 지배한다 — 막대 결과를 읽을 때 이 점을 감안해야 한다).
이것은 우리만의 한계가 아니라 **Ge 식 (21)의 구조 자체가 갖는 한계**다.

> **결론: "Ge Eq.(1)–(33) 전량 구현"은 유지될 수 없다.** 정확한 표현은
> **"Ge 식 (1)–(21) 및 (29)–(30)을 구현하고, (22)–(28)은 1축·선형경화 축약형으로,
> (31)–(33) consistent tangent는 secant로 대체한다"**이다.
> 이 중 실질적 성능 영향이 있는 것은 **(31)–(33)** 하나뿐이다 — 그리고 그것도
> 2026-08-11 부터 `ITAN` 스위치 뒤에 구현되어 있다(기본 꺼짐).
> **(23)(24) 「소성 소산 누락」은 철회되었다** — 위 철회문 참조. `G_m^p` 는
> `d_m` 을 인자로 갖지 않아 식 (21)에 0을 기여하므로, 탄성분만 넣는 현재
> 구현이 옳다.

---

## 후속 조치 권고 (파일:행 · 현재 문구 · 제안 문구)

### ★ 우선순위 1 — 오귀속 "Ge Eq.7" (5개 파일, 8개소)

| 파일:행 | 현재 | 제안 |
|---|---|---|
| `docs/M1_FAILURE_ANALYSIS.md:217` | `## There is exactly one switch, and it is Ge Eq.7` | `## There is exactly one switch, and it is Ge Eq.13` |
| `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for:34` | `C ... compression damage active by sign of I1(s~) (Ge Eq.7)` | `... (Ge Eq.13 = Zhang Eqs.15-16)` |
| `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for:435` | `C     Ge Eq.7: tension or compression damage active by sign of I1.` | `C     Ge Eq.13: tension or compression damage active by sign of I1.` |
| `src/UMAT_CSIC_THERMSHOCK_V3_0.for:102, 105, 572, 706` | `... per Ge Eq.7 ...` (4개소) | `... per Ge Eq.13 ...` |

> 근거: Ge 식 (7)은 **S_m(d_m) 손상 컴플라이언스 행렬**이다(p.88). sign(I₁) 판정은
> **Ge 식 (13)**(p.89). — 단, `UMAT_CSIC_RVE_ZHANG2022_V1_0.for:16-34` 헤더 중
> **Eq.2·Eq.3·Eq.4·Eqs.8-9·Eqs.16-17·Eqs.19-21 귀속은 전부 정확**하므로 손대지 말 것.

### ★ 우선순위 2 — "전량 구현" 주장 철회

| 파일:행 | 현재 | 제안 |
|---|---|---|
| `docs/THESIS_PLAN.md:18` | `Ge 2018 Eq.(1)–(33) 전량 구현` | `Ge 2018 식 (1)–(21)·(29)–(30) 구현; (22)–(28)은 1축·선형경화 축약, (31)–(33) consistent tangent는 secant 대체` |
| `verification/VERIFICATION_REPORT.md:197` | `the UMAT implements Ge Eqs. (1)–(33) in full` | `the UMAT implements Ge Eqs. (1)–(21) and (29)–(30); Eqs. (22)–(28) are reduced to a uniaxial / linear-hardening closed form and the consistent tangent of Eqs. (31)–(33) is replaced by the secant operator (see §D of refs/GE2018_EXTRACTION.md)` |

### ★ 우선순위 3 — Ge Table 3 근거 보강

| 파일:행 | 현재 | 제안 |
|---|---|---|
| `verification/VERIFICATION_REPORT.md:199-200` | `Ge Table 3 gives the parameter structure and fracture energies (Gf,1t=12.5, Gf,2t=1.0 N/mm)` | `Ge Table 3 gives, explicitly and as four separate cells, Gf,1t = Gf,1c = 12.5 N/mm and Gf,2(3)t = Gf,2(3)c = 1.0 N/mm (matrix Gm,t(c) = 1.0 N/mm)` |
| `verification/VERIFICATION_REPORT.md:115` 표 | 헤더 `Paper Eq.` (Zhang/Ge 번호 혼재) | 열을 **`Zhang Eq.` / `Ge Eq.`** 둘로 분리. 특히 `(19-21) 균열대`는 **Ge 전용**이며 Zhang (19)(매트릭스 지수형)과 충돌 |
| `verification/VERIFICATION_REPORT.md:118` | `(11) Hashin fibre tension (α=β=1)` | `Zhang (11) / Ge (12) — α,β는 Zhang이 도입해 1로 놓은 계수이며 Ge 원문에는 없다(모든 전단항 계수 1)` |
| `verification/VERIFICATION_REPORT.md` §3 표 | Eq.(3) 전단 커플링 행 **없음** | 행 추가: `Ge (3) \| 전단 손상 커플링 d4,d5,d6 \| KYARN30 L262-264 \| ✅` |
| `verification/check_card_ranges.py:167-170` (S12 행) | `"no tow-level shear strength found. ..."` | 앞에 추가: `"Ge refs/[24] Table 3 gives 58 MPa but for a PHENOLIC matrix; "` |
| `verification/check_card_ranges.py:184-190` (Gtt/Gtc 행) | `"...no transverse compressive fracture energy for C/SiC exists in the literature searched"` | 뒤에 추가: `"; Ge refs/[24] Table 3 does publish Gf,2(3)t = Gf,2(3)c = 1.0 N/mm for carbon/phenolic, so 0.0 is our switch-off, not a missing source"` |

### ★ 우선순위 4 — `r_F` 격하 (과잉 매개변수화 제거)

| 파일:행 | 현재 | 제안 |
|---|---|---|
| `verification/check_card_ranges.py:190-191` | `(37, "rF yarn", 3.0, ..., "GUESS", "linear-to-exponential transition; no measurement", "knob")` | `(37, "rF yarn", 3.0, ..., "DERIVED", "Ge refs/[24] Eq.(17) fixes r^F_f,1t as the transition point implied by X_PO and K1 -- it is NOT an independent input", "should be computed from slots 36/38, not tuned")` |
| `verification/CALIBRATION_GUIDE.md:186-187` | `**X_PO, rF, K1 (Eq.18):** Ge Eq.16–17의 보조변수. 논문 미공개 → pull-out 응력 X_PO≈0.2–0.3·Xt, 전이 rF≈2–4, 선형연화 K1은 E1의 수 % 수준에서 시작.` | `**X_PO, K1 (Eq.18):** Ge Eq.17의 보조변수. **Ge·Zhang 모두 수치 미공개**(Zhang은 다시 Ref.[30]으로 위임) → 선언된 knob 유지. X_PO≈0.2–0.3·Xt, K1은 E1의 수 % 수준. **rF는 knob이 아니다** — Ge Eq.(17) 3행이 전이점을 X_PO/X_1t로 결정하므로 X_PO·K1에서 계산할 것(자유 파라미터로 두면 세 값이 모순된 전이점을 지시함).` |
| `verification/m6_calibration_plan.py:91` | `SHAPE = ("Gtt yarn", "Gtc yarn", "X_PO yarn", "rF yarn", "K1 yarn")` | rF 제거 → 4차원. 보정 차원 1 감소 |

### ★ 우선순위 5 — 유지 확인 (수정 불필요)

| 파일:행 | 판정 |
|---|---|
| `verification/CALIBRATION_GUIDE.md:155` `Ge 2018 §3.2는 "작게 유지"라고 한다` | **정확 ✅ — stale 아님.** Ge p.92 §3.2 식 (30) 직후 원문 그대로. "0.05가 권고 상한 근처"라는 해석도 Ge의 *"small compared to the characteristic time increment"* 기준(Δt≈1e−3~2.5e−3)에 비추면 **오히려 η=0.05는 Δt의 20~50배로 '작지 않다'** → 문구를 `"Ge의 기준(Δt 대비 작을 것)으로 보면 0.05는 Δt의 20-50배이므로 이미 권고를 넘는다. 수렴은 η가 아니라 consistent tangent(Ge 식 31-33) 미구현에서 사야 한다"`로 **강화** 권고 |
| `verification/CALIBRATION_GUIDE.md:183-185` `Xt=Vf·X_T300,t ... Ge Table 2 = Zhang Table 1` | **정확 ✅** (탄성/강도 7항목 한정. CTE 2개는 Zhang 고유임을 부기 권고) |
| `verification/check_card_ranges.py:172-177` G1t/G1c DEV 등급 | **유지 ✅** — 등급 사유는 "값 없음"이 아니라 "페놀 매트릭스". 값은 원문에 있다 |

### ★ 우선순위 6 — 새 물리 항목 (신규 이슈)

1. **Consistent tangent (Ge 식 31–33) 미구현**을 `VERIFICATION_REPORT.md §5` 표에
   **6번 행으로 신규 등재**. 영향: 연화 구간 수렴률 2차→1차. M1 수렴 문제의 유력 원인.
2. **매트릭스 A_m 유도 시 소성 소산 누락 (Ge 식 23–24)**. `KMTRX30:421-422`가
   `Xt²/(2E)·CELENT`(탄성분)만 넘긴다 → 소성이 켜지면 실제 소산이 카드 G_m을 **초과**하여
   메시 비의존성이 깨진다. `celent_census.py`가 측정한 1.92배와 **별개의 추가 오차원**.

---

## 부록 — 이 보고서로 확정된 원문 인용 목록 (논문 각주용)

1. Ge et al., *Compos. Sci. Technol.* **157** (2018) 86–98, Eq. (3), p. 87 — 전단 손상 커플링
2. 동, Eq. (5), p. 88 — `ε_m = ε_m^e + ε_m^p` (열변형률 없음)
3. 동, Eq. (7), p. 88 — 매트릭스 손상 컴플라이언스 `S_m(d_m)`
4. 동, Eq. (8)–(10), p. 88 — von Mises 항복 / 연합유동 / 등가소성변형률
5. 동, Eq. (12), p. 89 — 3D Hashin 4모드 (α·β 없음)
6. 동, Eq. (13), p. 89 — sign(Ī₁) 인장/압축 스위치
7. 동, Eq. (16)–(17), p. 89 — 지수형 및 혼합 선형–지수 법칙, `X_f,PO`·`K_f,1`·`r^F_f,1t`
8. 동, Eq. (19)–(21), p. 90 — Bazant 균열대 정규화
9. 동, Eq. (22)–(24), p. 90–91 — Helmholtz 자유에너지 (얀 / 매트릭스 탄성+소성)
10. 동, Eq. (29)–(30), p. 92 — Duvaut–Lions 점성 정규화 + η 소값 권고
11. 동, Eq. (31)–(33), p. 92 — Consistent tangent
12. 동, Table 2, p. 93 — T300 물성 7항목
13. 동, Table 3, p. 94 — 매트릭스 6항목 + 얀 16항목 (파괴에너지 4개 포함)
14. 동, §4.1, p. 94 — *"tested at room temperature"*
15. 동, §6 Conclusions, p. 97 — *"the effects of temperature and interface will be taken into account to complete the model"*
16. Zhang et al., *Ceram. Int.* **48** (2022) 3109–3124, p. 3111 — pseudo-ductility 이식 선언
17. 동, p. 3112 — α, β *"settled as 1 in this paper"*; 보조변수는 Ref.[30]으로 위임
18. 동, Table 1, p. 3113 — T300 (Ge Table 2 + CTE 2항목)
