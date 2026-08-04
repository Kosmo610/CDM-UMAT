# EasyPBC 적용 계획 — Zhang 2022 재현에 Kim 2026 파이프라인 이식하기

## 0. 두 논문의 역할

| | **Zhang 2022** | **Kim 2026 (선배 논문)** |
|---|---|---|
| 서지 | Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang, *Effect of thermal residual stress on the tensile properties and damage process of C/SiC composites at high temperatures*, Ceramics International **48** (2022) 3109–3124 | D.-H. Kim, Y. Lee, S.-W. Kim, *Prediction of effective material properties of 2D plain-woven CFRP composite using a CNN–DNN hybrid surrogate model based on cross-sectional image*, Composite Structures **391** (2026) 120542 |
| 우리에게 주는 것 | **무엇을 재현할 것인가** — 재료계, RVE 치수, 손상 구성식, 검증 대상(Table 3) | **어떻게 유효물성을 뽑을 것인가** — TexGen→ABAQUS→EasyPBC 파이프라인, 인용 가능한 방법론 |
| 따라할 범위 | 전체 (M1) | **Fig. 1의 ①②만** — ③ 단면영상 추출과 CNN–DNN은 제외 |

**핵심**: 두 논문의 RVE는 **같은 종류다.** 둘 다 TexGen으로 만든 단층 2D 평직
주기 RVE에 주기경계조건을 걸고 유효물성을 뽑는다. 차이는 **재료계뿐**이다
(CFRP vs C/SiC). 따라서 Kim 2026의 ①②를 Zhang 2022의 RVE에 그대로 이식할 수 있다.

---

## 1. Fig. 1 ①② 를 우리 문제로 옮기는 매핑

| 항목 | Kim 2026 | Zhang 2022 | **우리 현재 상태** |
|---|---|---|---|
| 재료계 | AS4/8552 CFRP | T300/SiC CMC | T300/SiC ✔ 동일 |
| 아키텍처 | 2D 평직, 워프 2 + 필 2 | 2D 평직 (CT 기반) | 2D 평직 ✔ |
| RVE 치수 | d, w, t 스윕 (728 configs) | 3.5 × 3.5 × 0.4334 mm | 3.5 × 3.5 × 0.44 mm ✔ |
| 얀 단면 | TexGen 기본 | 타원 장축 1.28 / 단축 0.20 mm | 동일 |
| 요소 | DC3D4 (열) / C3D4 (역학) | C3D4, 116 724개 | C3D4, 174 407개 / 26 454개 |
| PBC 구현 | **EasyPBC 플러그인** | 자체 python 스크립트 | TexGen 자동생성 |
| 얀 물성 산출 | self-consistent + Rosen CCA | **Chamis + Schapery** | Chamis + Schapery ✔ (`micromech_check.py`가 증명) |
| 열전도 해석 | 정상상태, 100/0 °C, 나머지 4면 단열 | 없음 | ✔ `make_rve_conductivity.py` — **선배와 동일 방식** |
| CTE 해석 | EasyPBC + ΔT 0→100 °C | 냉각 1050→23 °C (손상 포함) | §4.5.3에 냉각 부산물로만 존재 |
| 유효 공학상수 | EasyPBC 참조점 변위 모드 | 없음 (손상 해석이 목적) | 없음 ← **여기가 빈칸** |

### 메시 크기 — 선배 논문이 우리 메시 전략을 정당화해 준다

Kim 2026은 in-plane CTE로 메시 수렴성을 검사해서 **공칭 요소크기 0.1 mm와
0.05 mm의 차이가 0.58 %** 임을 보이고, 이후 모든 RVE에 **최대 요소크기 0.1 mm
미만**을 적용했다. 우리 메시를 같은 척도로 환산하면:

| 덱 | 요소 수 | 등가 요소크기 $h_{eq}=(6\sqrt2 V/N)^{1/3}$ | Kim 2026 기준 |
|---|---|---|---|
| `ZHANG2022_*_V2_0` | 174 407 | **0.064 mm** | 통과 (여유 있음) |
| `M*_c26k_*` | 26 454 | **0.120 mm** | 살짝 초과 |

즉 정밀 메시(174k)는 **인용 가능한 수렴 기준을 이미 만족**한다. 거친 메시(26k)는
탐색용으로는 충분하지만 최종 유효물성 값은 174k에서 뽑아야 한다.
이는 `docs/MESH_STRATEGY.md`의 "탐색은 거칠게, 확정은 수렴 후" 원칙과 일치한다.

---

## 2. 무엇을 얻는가, 어디에 쓰는가

Kim 2026은 10개 물성을 뽑는다. 우리는 EasyPBC의 전체 출력을 켜서 **13개**를 뽑는다
(선배는 면내 4개만 보고했지만, 우리 거시 열충격 모델은 완전 직교이방성이 필요하다).

| 물성 | 산출 잡 | 우리 논문에서의 용처 |
|---|---|---|
| $\bar k_x, \bar k_y, \bar k_z$ | 정상상태 열전달 (EasyPBC 불필요) | Ch.5 거시 열전달 카드 |
| $\bar\alpha_x, \bar\alpha_y, \bar\alpha_z$ | `job-CTE` | Ch.4 §4.6, Ch.5 거시 CTE 카드, §4.5.3 검산 |
| $\bar E_{xx}, \bar E_{yy}, \bar E_{zz}$ | `job-E11/E22/E33` | Ch.5 거시 강성 카드 |
| $\bar G_{xy}, \bar G_{xz}, \bar G_{yz}$ | `job-G12/G13/G23` | Ch.5 거시 강성 카드 |
| $\bar\nu$ 6개 | 위 3개 잡의 부산물 | Ch.5 |
| 총질량 · 균질화 밀도 | 자동 | Ch.5 열용량 카드 검산 |

**추가 소득 — M1 진단용 체크포인트.** EasyPBC의 $\bar E_{xx}$ 는 **손상 이전의
초기 접선 탄성계수**다. M3/M5/M6 인장 곡선의 초기 기울기가 이 값과 다르면
문제는 손상 법칙이 아니라 **탄성 설정**에 있다. 지금까지 M1은 "인장 스텝이
안 붙는다"만 알고 있었지, 붙은 구간의 기울기가 맞는지는 검증한 적이 없다.

---

## 3. 실행 계획

### Stage 0 — 탄성 쌍둥이 덱 생성기 (`abaqus/make_easypbc_twin.py`)

EasyPBC가 제출하는 모든 잡은 `userSubroutine=''` 이라 **UMAT이 붙지 않는다**
(`docs/EASYPBC_PBC_CHECK.md` §6-B). 따라서 `*User Material` 을 등가 선형탄성
카드로 치환한 덱이 필요하다.

생성 규칙:

| 원본 | 치환 |
|---|---|
| 얀 `*User Material` (38 PROPS) | `*Elastic, type=ENGINEERING CONSTANTS` (9상수) + `*Expansion, type=ORTHO` |
| 매트릭스 `*User Material` (21 PROPS) | `*Elastic, type=ISOTROPIC` + `*Expansion` |
| `*Orientation` (TexGen) | **그대로 유지** ← 빠지면 에러 없이 섬유방향이 틀린 채 수렴한다 |
| `*Equation` + `ConstraintsDriver*` | **삭제** (EasyPBC가 자기 것을 만든다) |
| `MasterNode1` 고정 BC | 유지 (강체 이동 억제) |
| `*Density` | 유지 (질량·밀도 출력용) |

값은 손으로 옮기지 않고 `data/properties/eval_correlations.py` 의 상관식에서
읽는다 (CLAUDE.md 코드 규칙 — 전사 오류가 이미 두 번 났다).

**온도 3점을 각각 하나의 등온 덱으로 만든다**: 23 / 500 / 1000 °C.

### Stage 1 — EasyPBC 실행 (등온 3점)

먼저 **26k 메시로 리허설**한다. EasyPBC는 경계 절점 하나마다 어셈블리 세트를
하나씩 만들고 자유도마다 `Equation` 을 하나씩 만든다. 대략적인 규모:

| 메시 | 경계 절점 (x/y/z 면) | 생성 세트 수 | 생성 구속식 수 |
|---|---|---|---|
| 26k | 122 / 118 / 1037 | 약 2 600 | 약 3 800 |
| 174k | 394 / 406 / 3951 | 약 9 500 | 약 14 000 |

CAE 커널 호출이 하나씩 나가므로 174k는 **수십 분에서 한 시간대**를 각오해야 한다.
26k로 절차와 옵션을 확정한 뒤 174k를 한 번만 돌리는 것이 맞다.

각 온도마다 E11/E22/E33/G12/G13/G23/CTE 전부 체크, `only PBC` 해제,
`Initial temperature` = 해당 온도, `Final temperature` = 해당 온도 + 100.
CPU는 10 (CLAUDE.md 코어 배분).

> **CTE 정의를 맞출 것.** EasyPBC는 $\bar\alpha = \Delta L/(L_0\Delta T)$ 로
> **할선(secant) CTE**를 준다. 우리 무응력 온도는 1050 °C 이므로, Ch.5 카드에
> 넣을 때 기준온도를 명시하지 않으면 §4.5.3의 냉각 부산물(3.132e−6 /K, 1050→23 °C
> 할선)과 정의가 어긋난다. **EasyPBC 값은 국소 접선에 가깝고(ΔT=100), §4.5.3 값은
> 1027 K 구간 할선이며 손상까지 포함한다.** 둘은 같은 값이 아니고, 같아서도 안 된다.

### Stage 2 — 열전도 (이미 있음)

`abaqus/make_rve_conductivity.py` 가 만드는 RVE_COND 덱은 Kim 2026 §2.1의
방법과 **동일하다**: 대향 두 면에 온도차, 나머지 4면 단열, 반력 열유속으로

$$\bar k_i = \frac{\dot Q_{RFL} L_0}{A_0 \Delta T}$$

선배 논문이 같은 방법을 쓰고 있으므로, 우리 스크립트 docstring이 스스로 지적한
"엄밀한 주기적 방법이 아니다"라는 한계는 **문헌에 선례가 있는 표준 방법**으로
서술할 수 있다. 다만 그 한계 자체는 그대로 적어야 한다 —
`conductivity_bounds.py` 의 직렬/병렬 경계 안에 들어오는지 확인하는 절차를 유지한다.

### Stage 3 — 파라메트릭 확장 (선택, 후순위)

Kim 2026은 $d, w, t$ 를 스윕해 728개 configuration을 만들었다. 그것은 CNN 학습
데이터가 목적이었다. **우리 논문에는 그 목적이 없으므로 그대로 따라가지 않는다.**

우리 노벨티(`docs/NOVELTY.md`)에 맞는 스윕은 기하가 아니라 **공극률과 얀 Vf** 다.
`porosity_stiffness.py` 와 `insitu_yarn_strength.py` 가 이미 그 축을 다루고 있다.
Stage 1의 덱 생성기가 완성되면 그 축으로 스윕하는 것은 자동화된다.

**이건 Stage 1·2가 끝난 뒤에 판단한다.** 지금 결정할 필요 없다.

---

## 4. 반드시 지켜야 할 경계선

이 세 가지를 섞으면 논문이 무너진다.

**① 얀 물성 산출식을 섞지 마라.**
Kim 2026은 self-consistent field + Rosen CCA를, Zhang 2022는 Chamis + Schapery를
쓴다. 우리 얀 카드는 **Chamis + Schapery** 로 만들어져 있고
`verification/micromech_check.py` 가 그것을 증명한다. 선배 파이프라인을 쓴다고
해서 선배의 미시역학식까지 가져오면 Zhang 재현이 깨진다.
**가져오는 것은 EasyPBC라는 도구와 해석 절차뿐이다.**

**② EasyPBC는 Zhang의 Table 3를 재현하지 못한다.**
128.45 / 179.42 / 199.15 MPa 는 손상 UMAT의 결과다. EasyPBC는 손상 없는
선형탄성 균질화만 한다. **M1은 EasyPBC로 우회되지 않는다.** EasyPBC가 주는 것은
그 곡선의 *초기 기울기* 체크포인트와, M1과 독립적으로 확보되는 Ch.5 거시 카드다.

**③ 복합재 측정값을 카드로 넣지 마라.**
CLAUDE.md 규칙 그대로다. EasyPBC 출력은 **검증·거시카드 전용**이며,
RVE 구성재 카드로 역류시키면 TRS를 이중 계산한다.

---

## 5. 함정 요약 (`EASYPBC_PBC_CHECK.md` §7과 함께 볼 것)

| 함정 | 이 계획에서의 대응 |
|---|---|
| UMAT 미부착 | Stage 0의 탄성 쌍둥이 덱 |
| 하중이 변의 20 % | 선형탄성 전용이므로 무해 |
| `only PBC` + E + G 동시 체크 | Stage 1에서는 `only PBC` 해제 → 해당 없음 |
| CTE 잡의 강체 구속 부재 | `.msg` 의 numerical singularity 경고가 3개(강체 병진) 이하인지 확인 |
| 174k 메시의 세트 생성 시간 | 26k로 리허설 후 174k 1회 |
| 온도의존 물성 | 등온 덱 3개로 분리 (23/500/1000 °C) |
| Windows 전용 | 해당 없음 (워크스테이션이 Windows) |

---

## 6. 논문 서술에 쓸 문장 (초안)

> 유효 열기계 물성은 Kim 등 [Kim2026] 이 2D 평직 CFRP에 적용한 절차를 따라
> 산출하였다. RVE의 대향면 간 변위 적합성은 ABAQUS용 EasyPBC 플러그인
> [Omairey2018] 으로 부과하였으며, 플러그인이 생성한 참조점을 통해 독립적인
> 거시 변형 모드를 인가하고 그에 대응하는 반력과 변위로부터 유효 공학상수를
> 계산하였다. 유효 CTE는 동일한 주기경계조건을 유지한 채 균일 온도 변화
> ΔT = 100 °C 를 인가하고 거시 열신장으로부터 구하였다. 유효 열전도율은
> 별도의 정상상태 열전달 해석에서 대향 두 면에 온도차를 인가하고 나머지
> 네 면을 단열 처리하여 반력 열유속으로부터 산출하였다.

인용 두 개:
- `[Omairey2018]` Omairey S., Dunning P., Sriramula S., *Development of an ABAQUS plugin tool for periodic RVE homogenisation*, Engineering with Computers (2018). 신뢰도 `fulltext`.
- `[Kim2026]` 위 서지. 신뢰도 `fulltext`.
