# 물성 문헌 조사 — 후보 논문과 추출할 숫자 명세

**목적:** `UMAT_CSIC_THERMSHOCK_V3_0`의 온도의존 물성 테이블과 급랭 해석용 열물성을
문헌으로 채우는 것.

> ### 상태: 2026-07 — 원문 확보 완료, 대부분 추출 완료
> 요청한 논문 15편이 **`refs/`** 에 들어왔습니다. 서지·추출 결과·발견 사항은
> **[`refs/README.md`](../refs/README.md)** 를 보세요. 상관식은 전부
> **`data/properties/eval_correlations.py`** 에 코드로 들어가 검산까지 붙었습니다.
>
> | 항목 | 상태 |
> |---|---|
> | SiC 매트릭스 `Cp(T)`, `k(T)`, `α(T)`, `E(T)`, `ρ` (Snead 2007) | ✅ 완료 |
> | 섬유 CTE (Pradère & Sauder 2008) | ✅ 완료 |
> | 섬유 `E(T)`, `σ_R(T)` (Sauder 2002) | ✅ 완료 |
> | 섬유 `k`, `cp`, `ρ` (Pradère 2009, `refs/[09]`) | ⚠️ **미추출** |
> | SiC 강도 vs 온도 | ❌ **출처 없음** — `fX/fY/fS`가 1.0 고정 |
>
> 아래 §2–§3은 어떤 논문이 어떤 역할인지의 원래 명세로 남겨둡니다.

---

## 0. 먼저 — 가장 중요한 원칙 (이거 틀리면 논문이 무너집니다)

### 입력 데이터와 검증 데이터를 절대 섞지 마세요

검색 중 확인한 사실입니다. 2D C/SiC의 **탄성계수와 인장강도는 온도가 올라가면
1000 °C까지 오히려 증가**합니다 (J. Eur. Ceram. Soc. 2017 초록: *"tensile modulus and
strength increase continuously with increasing temperature till 1273 K … This manifests
the significant influence of thermal residual stresses"*). Zhang 2022의 128 → 179 →
199 MPa 경향과도 일치합니다.

**왜 올라가는가:** 재료가 본질적으로 강해져서가 아니라, 가열하면 제조 온도(1050 °C)
쪽으로 되돌아가면서 **열잔류응력이 이완되고 초기 손상이 닫히기** 때문입니다.

그런데 **우리 모델은 그 TRS를 냉각 스텝으로 직접 계산**합니다. 따라서:

| 데이터 종류 | 어디에 쓰는가 | 쓰면 안 되는 곳 |
|---|---|---|
| **구성재**(T300 섬유, SiC 매트릭스) 물성 vs 온도 | ✅ UMAT 카드의 `f(T)` 테이블 **입력** | — |
| **복합재**(2D C/SiC) E(T), σu(T), ᾱ(T), k̄(T) | ✅ 모델 출력과 대조하는 **검증** | ❌ **입력 금지** |

복합재 E(T)를 입력 배율로 넣으면 **TRS 효과를 두 번 세게 됩니다.** 심사에서 잡히면
치명적이고, 잡히지 않아도 결과가 틀립니다.

> 거시 카드의 `f(T)`는 문헌에서 오지 않습니다. `homogenize.py`가 각 온도의 RVE 가상시험
> 결과 C̄(T)에서 **계산**합니다. 즉 파이프라인은 이미 올바르게 되어 있고,
> 문헌 복합재 데이터는 순수하게 검증용입니다.

### 두 번째 함정 — CTE 기준온도

논문은 CTE를 **순간(instantaneous)** 또는 **상온 기준 할선(secant)** 으로 보고합니다.
Abaqus `*Expansion, zero=1050`은 **1050 °C 기준 할선 CTE**를 요구합니다.
그대로 넣으면 TRS가 틀립니다. `build_temperature_tables.py`가 변환해 주니
**CSV에 `cte_type`과 `cte_ref_C`만 정확히 기록**하면 됩니다.
(변환은 `--selftest`로 검증되어 있습니다: 열변형률 차가 모든 온도쌍에서 보존됨)

---

## 1. 작업 흐름 — 논문을 구하면 이렇게 하세요

```bash
# 1) data/properties/fibre_T300_vsT.csv 와 matrix_SiC_vsT.csv 에 행 추가
#    (T_C, 물성값, cte_type, cte_ref_C, status=literature, source="저자 연도 Table N")

# 2) 카드 블록 자동 생성
python3 abaqus/build_temperature_tables.py
#    -> data/properties/temperature_blocks.inp
#       · 얀 f(T) 테이블 (Chamis/Schapery를 각 온도에서 재계산)
#       · 얀 *Expansion, type=ORTHO, zero=1050  (기준 변환 완료)
#       · 매트릭스 f(T) 테이블 + *Expansion

# 3) 변환 로직 자체를 확인하고 싶으면
python3 abaqus/build_temperature_tables.py --selftest
```

스크립트는 매 실행마다 **자기검증**을 합니다: 23 °C 행에서 Chamis 결과가 검증된
V2_0 얀 카드와 일치해야 합니다(현재 최대 오차 0.142 %, 기존 `micromech_check.py`와 동일).

**중요:** 섬유와 매트릭스 CSV는 **같은 온도점**을 가져야 합니다. 얀은 둘의 균질화이므로,
온도가 어긋나면 23 °C 매트릭스와 1000 °C 섬유가 조용히 섞입니다. 스크립트가 막아줍니다.

**최소 요구:** 온도점 **2개(23 °C + 고온 1개)** 면 논문이 성립합니다. 3개면 충분합니다.
없는 물성은 **추측하지 말고 비워두세요** — 비면 상수로 처리되고 그 사실이 출력에 찍힙니다.

---

## 2. A그룹 — 구성재 물성 (UMAT 카드 **입력**)

### A1. SiC 매트릭스 열물성 ★★★ 최우선 — 이거 하나가 열물성 문제를 거의 다 해결

> **L.L. Snead, T. Nozawa, Y. Katoh, T.-S. Byun, S. Kondo, D.A. Petti**,
> *"Handbook of SiC properties for fuel performance modeling"*,
> **Journal of Nuclear Materials 371 (2007) 329–377**.
> DOI: `10.1016/j.jnucmat.2007.05.016` · 인용 1,200회 이상

**뽑을 것:** SiC의 `k(T)`, `cp(T)`, `ρ`, `α(T)`, `E(T)` **상관식(correlation)**.
비열은 200–1000 K 구간 불확실도 7 %, 1000–2400 K 구간 4 %로 명시되어 있습니다.
→ `matrix_SiC_vsT.csv`의 `k`, `cp`, `rho`, `alpha`, `E` 열

**백업/교차확인 (무료 PDF, 다운로드만 하면 됨):**
- ORNL, *"SiC/SiC Cladding Materials Properties Handbook"*
  `https://info.ornl.gov/sites/publications/Files/Pub100714.pdf`
- MOOSE 프레임워크 문서 `ThermalMonolithicSiCProperties` / `ThermalCompositeSiCProperties`
  — Snead 상관식을 코드로 정리해 둔 것. 식을 그대로 베껴 쓸 수 있습니다.

> ⚠️ **PIP vs CVI 주의.** Zhang 2022은 **PIP** 매트릭스(1050 °C 열분해)인데
> Snead/ORNL 데이터는 **CVD/CVI** SiC입니다. PIP는 더 다공질이라 k와 E가 낮습니다.
> CSV의 `process` 열에 반드시 기록하고, **차이를 민감도 해석으로 다루세요**
> (같다고 치면 안 됩니다). PIP 값을 못 구하면 "CVI 값 사용 + k에 대한 민감도 ±50 %"로
> 정직하게 처리하는 게 방어에 유리합니다.

### A2. T300 탄소섬유 열팽창 ★★★ — TRS의 심장

> **C. Pradère, C. Sauder**, *"Transverse and longitudinal coefficient of thermal
> expansion of carbon fibers at high temperatures (300–2500 K)"*, **Carbon 46 (2008)**.

**뽑을 것:** `α_f1(T)` (축방향), `α_f2(T)` (횡방향), 그리고 **어느 형식인지**
(순간 CTE인지 할선인지, 할선이면 기준온도).
→ `fibre_T300_vsT.csv`의 `alpha1`, `alpha2`, `cte_type`, `cte_ref_C`

**왜 최우선인가:** 탄소섬유 축방향 CTE는 상온에서 **음수**(Zhang Table 1: −0.3e-6/K)인데
고온에서 **양수로 바뀝니다**(검색 결과: 300–2500 K에서 1.6~2.1e-6/K). 이 부호 전환이
섬유-매트릭스 CTE 불일치의 크기를 온도에 따라 크게 바꾸고, **그게 곧 TRS**입니다.
α를 상수로 두면 이 논문의 주 변수가 틀린 값이 됩니다.

**보조:** Menessier et al., *Ceram. Eng. Sci. Proc.* 10 (1989) — 20–430 °C 저온 구간

### A3. T300 탄소섬유 고온 역학물성 ★★

> **C. Sauder, J. Lamon, R. Pailler**, *"Thermomechanical properties of carbon fibres
> at high temperatures (up to 2000 °C)"*, **Composites Science and Technology 62 (2002)**.

**뽑을 것:** `E_f1(T)`, 인장강도 `X_f(T)`.
검색 결과에 따르면 **E는 감소, 강도는 증가**하는 경향(2673 K까지, 진공)입니다.
→ `fibre_T300_vsT.csv`의 `E1`, `Xt`

`E2`, `G12`, `G23`(횡방향/전단)의 온도의존 데이터는 사실상 존재하지 않습니다.
없으면 비워두세요 — 그러면 상온값 고정이 되고, 그 가정을 논문에 명시하면 됩니다.

### A4. T300 탄소섬유 열전도/비열 ★★

> **C. Pradère et al.**, *"Thermal properties of carbon fibers at very high temperature"*,
> **Carbon 47 (2009)**.
> 보조: Toray T300 데이터시트 (ρ, cp 기본값)

**뽑을 것:** `k_f1(T)` (축), `k_f2(T)` (횡), `cp`, `ρ`.
→ `fibre_T300_vsT.csv`의 `k1`, `k2`, `cp`, `rho`

검색에서 나온 참고값(**출처 확정 필요**): T300 축방향 k ≈ 7.81, 횡방향 ≈ 0.675 W/(m·K),
cp ≈ 0.777 J/(g·°C), 축 CTE ≈ −0.41e-6/°C. 또 "축방향 k는 T의 선형함수, 횡방향은 거의 상수"
라는 서술이 있습니다. **이 값들은 2차 요약에서 온 것이니 원문 확인 전에는 인용하지 마세요.**

---

## 3. B그룹 — 복합재 물성 (**검증 전용**, 입력 금지)

### B1. 2D C/SiC 인장물성 vs 온도 ★★★ — 핵심 검증 대상

> ① **"Tensile behavior of 2D-C/SiC composites at elevated temperatures:
> Experiment and modeling"**, **J. European Ceramic Society** (2017).
> ScienceDirect PII: `S0955221916306112`

**가장 잘 맞는 논문입니다.** 우리 재료(2D C/SiC), 우리 온도범위, 그리고 초록이
**TRS의 영향이 지배적**이라고 명시합니다. 충격 흡수 방식(impulse excitation)으로
E(T)를 연속 측정했고, 2-스케일 해석 모델(shear-lag)까지 붙어 있어 우리 접근과 직접 비교됩니다.
→ Zhang 2022과 **독립적인** 두 번째 검증점이 생깁니다.

> ② **"Tensile properties of two-dimensional carbon fiber reinforced silicon carbide
> composites at temperatures up to 2300 °C"**, **J. European Ceramic Society** (2020).
> PII: `S0955221919307010`
> → E는 1000 °C까지 증가 후 감소, 강도는 1000 °C↑ → 1400 °C↓ → 1800 °C↑ → 감소.
> **1000 °C 이후의 반전**이 중요합니다. 우리 해석 범위(≤1050 °C)의 상한을 정당화해 줍니다.

> ③ **"Tensile properties of 2D-C/SiC composites at temperatures up to 1873 K at
> wide-ranging strain rates"**, **Composite Structures** (2023). PII: `S0263822323004543`
> → 변형률 속도 의존성. 급랭은 빠른 하중이라 관련 있음.

### B2. C/SiC 열팽창 vs 온도 ★★★ — ᾱ(T) 검증

> ④ **"Thermal expansion behavior of carbon fiber reinforced chemical-vapor-infiltrated
> silicon carbide composites from room temperature to 1400 °C"**,
> **Materials Letters 61 (2007)**. PII: `S0167577X06002758`
> → 세 가지 프리폼 구조 비교. **2D C/SiC 면내 CTE가 900 °C까지 선형 증가 후 변동.**
> `homogenize.py`가 뽑는 ᾱ(T)를 이 곡선과 대조하면 됩니다.

> ⑤ **"Investigation of thermal expansion of 3D-stitched C–SiC composites"**,
> **J. European Ceramic Society 29 (2009)**. PII: `S0955221909001551`
> → RT–1050 °C, 면내 CTE (0.5–2)×10⁻⁶/°C. 3D 구조라 참고용.

### B3. C/SiC 열전도율 ★★★ — 급랭 해석에 필수

> ⑥ **"Enhancing thermal conductivity of C/SiC composites containing heat transfer
> channels"**, **J. European Ceramic Society 40 (2020)**. PII: `S0955221920302727`

> ⑦ **"Effect of heat transfer channels on thermal conductivity of silicon carbide
> composites reinforced with pitch-based carbon fibers"**,
> **J. European Ceramic Society 41 (2021)**. PII: `S0955221921007160`
> → 면내 112.4, 두께방향 38.9 W/(m·K), RT–500 °C.
> ⚠️ **피치계(pitch-based) 섬유**입니다. T300은 PAN계로 열전도율이 **훨씬 낮습니다.**
> 이 숫자를 T300 기반 C/SiC에 그대로 쓰면 안 됩니다 — 이방성 **경향**의 참고로만.

> ⑧ **"Property tailorability for advanced CVI silicon carbide composites for fusion"**,
> **Fusion Engineering and Design** (2006). PII: `S0920379605006095`
> → 축방향 tow가 열전도율을 지배한다는 결론. 균질화 결과 해석에 유용.

### B4. 보조 — 오픈액세스(바로 읽을 수 있음)

> ⑨ *"Modeling Temperature-Dependent Vibration Damping in C/SiC Fiber-Reinforced
> Ceramic-Matrix Composites"* — PMC7178383 (무료)
> ⑩ *"Cf/SiC Ceramic Matrix Composites with Extraordinary Thermomechanical Properties
> up to 2000 °C"* — PMC10780313 (무료)

---

## 4. 확보 우선순위 (시간이 없으면 위에서부터)

| 순위 | 논문 | 없으면 무엇이 막히나 |
|---|---|---|
| 1 | **Snead 2007 (A1)** | 급랭 과도 열해석 자체가 불가. k, cp, ρ가 없으면 열충격 해석을 시작할 수 없음 |
| 2 | **Pradère & Sauder 2008 (A2)** | α(T) 없이는 TRS가 틀린 값 → 논문의 주 변수가 무의미 |
| 3 | **JECS 2017 (B1①)** | 거시 모델의 독립 검증점이 사라짐 (Zhang 하나만 남음) |
| 4 | **Mater. Lett. 2007 (B2④)** | 균질화 ᾱ(T)를 검증할 방법이 없음 |
| 5 | Sauder 2002 (A3) | E_f(T), X_f(T)가 상수로 고정 (가정 명시하면 논문은 성립) |
| 6 | JECS 2020/2021 (B3) | k̄ 균질화 결과를 대조할 수 없음 (경향만 논의) |
| 7 | 나머지 | 고찰 보강용 |

**1번과 2번만 있어도 해석은 돌아갑니다.** 3·4번은 검증 챕터의 질을 결정합니다.

---

## 5. 논문에서 이 문서가 쓰이는 곳

- Ch.3.2 **온도의존 물성 도입** — A그룹 표 + Chamis/Schapery 재계산 절차 + CTE 기준 변환
- Ch.4.3 **유효 열-기계 물성 추출** — B2/B3와 균질화 결과 대조
- Ch.6.1 **문헌 대조 검증** — B1의 E(T), σu(T)를 모델 예측과 겹쳐 그리기
- Ch.6.6 **한계** — PIP vs CVI 물성 차이, 피치계 vs PAN계 열전도율, 미확보 물성의 상수 가정

---

## 6. 관련 파일

| 파일 | 역할 |
|---|---|
| `data/properties/fibre_T300_vsT.csv` | 섬유 구성재 데이터 (채워 넣을 곳) |
| `data/properties/matrix_SiC_vsT.csv` | 매트릭스 구성재 데이터 (채워 넣을 곳) |
| `data/properties/README.md` | 열 정의, 단위 규약, 신뢰도 등급 |
| `abaqus/build_temperature_tables.py` | CSV → UMAT 카드 블록 + `*Expansion` 변환 |
| `data/literature/csic_thermal_shock.csv` | 반복 열충격 검증 데이터 (별건, 이미 확보) |
