# 섬유 횡방향 열팽창 — 문헌 딥리서치 (2026-08-12)

**왜 이것을 찾았나.** `docs/CH4_RVE_HOMOGENISATION.md` §4.9-10의 4단 사다리에서
모델과 실측 사이의 간격이 세 칸으로 쪼개졌고, 그중 **2→3단(+9.4 %)이 섬유 횡방향
열팽창 카드값 하나로 설명된다.** 카드는 3.1×10⁻⁶/K(Zhang Table 1), 우리가 가진
유일한 대안은 refs/[07] Pradère & Sauder의 **5–10×10⁻⁶/K** 대역이다. 이 대역이
너무 넓어 "얼마나 틀렸는지"를 말할 수 없었다. 그것을 좁히는 것이 이 조사의 목적이다.

**이 문서의 등급 규칙.** 이 환경은 출판사 사이트에 접속할 수 없다(ScienceDirect ·
Springer · PMC 전부 차단). 따라서 **아래 항목은 전부 `search-verified`(초록 수준)**
이며, 프로젝트 규칙에 따라 **어느 것도 카드에 들어갈 수 없다.** 카드에 들어가려면
PDF를 확보해 `fulltext`로 올려야 한다. 값은 "이렇게 적혀 있다고 검색이 보고했다"는
뜻이지 "원문에서 읽었다"는 뜻이 아니다.

---

## 0. 한 줄 결론 — 대역이 5–10에서 **3.8–5.6**으로 좁아진다

가장 중요한 발견은 **N1**이다. PAN계 탄소섬유 두 종을 **20–1100 °C**에서 직접
측정한 값이 있고, 그 범위가 우리 온도 구간과 정확히 겹친다.

| 출처 | 섬유 | 축방향 | **횡방향** | 방법 · 온도 |
|---|---|---|---|---|
| **N1** Kulkarni & Ochoa 2006 | IM7 (PAN) | −0.4 | **5.6** | in-situ TEM, 20–1100 °C |
| **N1** 동 | T1000 (PAN) | −1.4 | **3.8** | 동 |
| refs/[07] Pradère & Sauder 2008 | 4종(레이온·PAN·피치) | 1.6–2.1 | **5–10** | 역해석, 300–2500 K |
| 우리 카드 (Zhang Table 1) | T300 | −0.3 | **3.1** | (Zhang이 인용) |
| 우리 대안 (PANEX33 할선) | PANEX 33 | +1.24 | **5.63** | refs/[07] 다항식 |

단위는 전부 10⁻⁶/K.

**이것이 바꾸는 것 셋.**

1. **카드 3.1은 이상값이 아니다.** PAN 실측 하한(T1000 3.8)보다 **18 % 아래**일
   뿐이다. "5–10 대역 밖"이라고 쓰면 실제보다 훨씬 나쁘게 들린다.
2. **PANEX33 5.63은 상한이 아니라 실측 상단과 거의 같다**(IM7 5.6). 즉 CONFIG_P가
   쓰는 값은 극단값이 아니라 **PAN계 실측 범위의 위쪽 끝**이다.
3. **refs/[07]의 5–10 대역은 PAN 전용이 아니다.** 레이온계·피치계와 2500 K까지를
   함께 담은 범위이므로, 우리 문제(PAN, ≤1050 °C)에는 **그대로 쓰면 넓다.**
   N1을 확보하면 민감도 스윕의 상·하한을 **3.8 / 5.6**으로 좁힐 수 있다.

**주의 — N1은 아직 초록 수준이다.** 위 네 숫자(−0.4 / 5.6 / −1.4 / 3.8)는
검색이 보고한 값이며 원문 표를 본 것이 아니다. **PDF를 확보하기 전에는 카드에도
민감도 표에도 넣지 않는다.**

---

## 1. 최우선 확보 — 섬유 횡방향 CTE 직접 관련

### N1 · Kulkarni & Ochoa (2006) ★ 최우선
- *Transverse and Longitudinal CTE Measurements of Carbon Fibers and their Impact
  on Interfacial Residual Stresses in Composites*
- **J. Compos. Mater. 40 (8) (2006) 733–754**, DOI `10.1177/0021998305055545`
- 왜 필요한가: **PAN계 두 종의 20–1100 °C 횡방향 CTE 직접 측정.** 우리 온도
  구간과 겹치는 유일한 직접 측정이다. 사다리 2→3단의 불확실 폭을 절반 이하로
  줄인다.
- 덤: 이 값들을 넣은 단방향 복합재 FE가 **냉각 구간에서 라미나 CTE 실측과 일치**
  했다고 한다 — 우리 §4.9-0의 두-상태 논리와 같은 계열의 검증이다.
- ⚠️ 피치계 P55도 함께 측정했으므로, **PAN 행만 골라 쓴다.**

### N2 · Pradère & Sauder (2007) — refs/[07]의 방법 원전
- *Estimation of the transverse coefficient of thermal expansion on carbon fibers
  at very high temperature*
- **Inverse Problems Sci. Eng. 15 (1) (2007) 77–89**, DOI `10.1080/17415970600574047`
- 왜 필요한가: 우리가 이미 쓰는 refs/[07]의 **횡방향 값이 어떻게 나온 것인지**가
  여기 있다. 제목이 말하듯 **"estimation"이며 역문제(inverse problem)** 다 —
  즉 직접 측정이 아니라 **모형을 통해 되짚은 값**이다.
- 이 사실 하나가 등급 판단을 바꾼다. N1(직접 측정)과 refs/[07](역해석)이 어긋나면
  **N1을 우선한다**는 근거가 된다.
- ⚠️ 현재 제2장·`cte_sensitivity.py`는 refs/[07]의 5–10을 "실측 대역"처럼 부른다.
  N2를 확보하면 그 표현을 **"역해석으로 얻은 대역"** 으로 고쳐야 한다.

### N3 · Bath 그룹 (2025) — 최신, 그러나 우리 범위 밖
- *Quantification of the thermal expansion of carbon fibres in CFRP at low
  temperatures using X-ray diffraction*
- **Compos. Part A (2025)**, 논문번호 `S1359836825005980`
- 보고값: Hexcel **IM7 반경방향 CTE = 26.2×10⁻⁶/K** (200 K 근방)
- ⚠️ **이 값을 우리 카드에 절대 넣지 말 것.** 두 가지 이유가 있다.
  1. **양이 다르다.** XRD가 재는 것은 **(002) 면간거리**, 즉 흑연 층 사이 방향의
     격자 팽창이다. 섬유 전체의 유효 반경방향 팽창이 아니다. 섬유 안에서 층이
     여러 방향으로 누워 있으면 유효값은 훨씬 작아진다.
  2. **온도가 다르다.** 200 K(−70 °C)이고 우리는 23–1050 °C다.
- 그럼에도 확보 가치가 있는 이유: **"섬유 횡방향 CTE가 왜 하나의 숫자로 정해지지
  않는가"를 설명하는 가장 좋은 최신 근거**다. 층 방향(c축) 27 정도와 면내(a축)
  거의 0 사이의 어디쯤이며, 그 조합이 섬유 조직에 달렸다는 것. 제7장 한계나
  제4장 §4.9-10의 "왜 이 손잡이를 열어 두는가"에 그대로 쓸 수 있다.

---

## 2. 복합재 절대 표적 — 지금 비어 있는 저온 구간을 메운다

현재 우리가 가진 복합재 CTE 절대 표적은 refs/[61](600–1200 °C 4점)뿐이고,
**600 °C 아래는 완전히 비어 있다**(`cte_composite_targets.py`가 외삽을 금지한다).
아래 둘이 그 구간을 채운다.

### N4 · Dang 등 (2024) ★★ 최우선 — 저온 표적 + TRS 표적
- *In-plane thermal expansion behavior of M55J carbon fiber reinforced SiC matrix
  composite*
- **J. Eur. Ceram. Soc. 44 (1) (2024) 119–129**, DOI `10.1016/j.jeurceramsoc.2023.08.044`
- 저자: Dang X, Zhao D, Fan X, Ma X, Chen X, Xue J 외 (Northwestern Polytechnical Univ.)
- **이 논문이 주는 것 둘, 둘 다 우리 병목에 정확히 꽂힌다.**
  1. **T300 C/SiC의 −20 ~ 50 °C 면내 평균 CTE = 1.09×10⁻⁶/K** (M55J로 바꾸면 0.34).
     **우리 재료와 같은 T300계의 상온 근방 실측값**이며, refs/[61]이 비워 둔
     구간의 첫 절대값이다.
  2. **SiC 기지의 축방향 열잔류응력 = 378 ± 26 MPa** (M55J 기준), 그리고 그
     응력이 **기지 미세균열을 만든다**고 명시한다.
- 왜 이것이 큰가: 우리 §4.5.2의 기지 TRS 268 MPa는 지금까지 **refs/[15]의 XRD
  114.7 MPa 하나**에만 대조되어 "2.34배 과대"로 보였다. 378 MPa라는 **더 높은
  독립 보고값**이 존재한다면, "268은 터무니없이 크다"는 서술 자체가 흔들린다.
  CONFIG_V/CONFIG_P 결정(§4.9-11)의 근거를 다시 볼 사안이다.
- ⚠️ 다만 **M55J는 고탄성률 섬유**라 T300보다 열팽창 불일치가 크다. 378은 M55J
  값이므로 **T300 카드에 그대로 옮기면 안 된다.** 원문에서 T300 쪽 TRS 값을
  따로 주는지가 확보 후 첫 확인 사항이다.
- ⚠️ 1.09×10⁻⁶/K는 **−20~50 °C 평균**이다. 우리 3.2827은 무응력 온도 기준 할선
  이므로 **직접 비교 금지** — `cte_rve_verdict.py`의 세 어긋남 중 ⓐ가 그대로 적용된다.

### N5 · Fan · Dang 등 (2025) — N4의 후속
- *Microstructure, thermal-expansion, and tensile properties of M55J-type carbon
  fiber–reinforced, SiC and Si3N4 multilayered matrix composites*
- **Ceram. Int. (2025)**, 논문번호 `S0272884225012684` / SSRN 사전본 `5010325`
- 저자: Xiaomeng Fan, Shu Tang, Tao He, Xiaolin Dang, Xuteng Wang, Donglin Zhao, Chao Chen
- 왜: N4와 같은 그룹의 후속이며 **SSRN에 사전본이 공개**되어 있어 본문 확보가
  상대적으로 쉽다. 다층 기지라 우리 단일 기지와 다르지만, **같은 그룹의 측정
  프로토콜**이 적혀 있을 가능성이 높다(N4의 방법을 읽는 우회로).

### N6 · Dang 등 (2025) — 계면 두께 영향
- *Microstructure, mechanical properties and thermal expansion behavior of M55J
  Cf/SiC-SiBC composites with different interphase thicknesses*
- **J. Eur. Ceram. Soc. (2025)**, 논문번호 `S0955221925002092`
- 왜: **PyC 계면 두께가 CTE와 TRS를 얼마나 움직이는가.** 우리 RVE에는 계면상이
  없으므로(얀/기지 2상), 이 논문은 **"계면을 안 넣어서 생기는 오차의 크기"** 를
  제7장 한계에 숫자로 적을 수 있게 해준다.

### N7 · Ceramics International (2021) — 석영램프 가열 중 CTE
- *High-temperature thermal expansion behaviour of C/SiC studied using an in-situ
  optical visualisation method and numerical simulations in a quartz lamp array
  heating environment*
- **Ceram. Int. (2021)**, 논문번호 `S0272884221001346`
- 왜: **석영램프 배열 가열은 우리 제5장 급랭/급가열 실험 계열과 같은 장치**다.
  팽창계(dilatometer)가 아니라 **실제 열충격 장치 안에서** 잰 CTE이므로,
  "실험실 CTE와 열충격 중 CTE가 같은가"라는 질문에 답한다.

---

## 3. 공극이 CTE를 낮춘다 — 우리 문서가 반대로 적고 있다

### N8 · Composite Structures (2021) ★ 확보 권장
- *A multiscale modeling for predicting the thermal expansion behaviors of 3D
  C/SiC composites considering porosity and fiber volume fraction*
- **Compos. Struct. (2021)**, 논문번호 `S027288422033474X`
- 보고 요지: X-ray CT로 공극·얀 형상·계면 두께를 특성화하고 미시→중시 RVE 2단
  균질화. **"공극이 3D C/SiC의 CTE를 낮추는 데 유효했다(voids were effective in
  lowering the CTE)"**, 중시 예측이 실측과 잘 맞았다.
- **왜 이것이 지금 중요한가.** `data/literature/cte_composite_targets.py`는
  refs/[61](CVI 공극 13 %)을 우리 재료(PIP 공극 32.4 %)에 옮기는 근거로
  *"CTE는 탄성계수보다 공극에 훨씬 덜 민감하다 — 구멍은 하중도 안 받지만 팽창도
  안 한다"* 고 적어 두었다. **N8이 맞다면 이 문장은 방향이 반대다.**
- 그리고 이것은 **우리에게 유리한 쪽**이다: 공극이 CTE를 낮춘다면, 공극 32.4 %인
  우리 재료가 공극 13 %인 refs/[61]보다 낮은 것이 **당연**하고, 사다리 3→4단의
  +14.2 % 중 일부가 **재료 차이로 설명**된다.
- ⚠️ 확보 전까지는 문서를 고치지 않는다. 다만 `cte_composite_targets.py`의 그
  문장은 **"확인 필요"** 로 표시해 두었다(아래 §6).

### N9 · J. Eur. Ceram. Soc. 41 (3) (2021) 1795–1809
- *Improved semi-analytical and numerical methods on prediction of in-plane
  coefficients of thermal expansion of woven ceramic matrix composite considering
  defects*
- 재료: 5매 주자직 C/C, **PIP 공법**, 기지 부피분율을 바꿔가며 면내 CTE 측정
- 왜: **우리와 같은 PIP 공법**이고, 결함(공극·균열)이 직물 CMC의 면내 CTE에
  들어가는 방식을 반해석식으로 준다. N8과 함께 §4.9-10의 "재료가 다르다" 항목을
  **정성 서술에서 정량 서술로** 올릴 수 있다.

---

## 4. 참고문헌으로 쓸 것 — 노벨티 위치 잡기

이 묶음은 물성값이 아니라 **"우리 앞에 누가 무엇을 했는가"** 에 쓴다. 제1·2장과
제7장 향후과제의 인용 후보다.

| 라벨 | 논문 | 어디에 쓰나 |
|---|---|---|
| **N10** | *A continuum fatigue damage model for the cyclic thermal shocked ceramic-matrix composites*, Int. J. Fatigue (2020), `S0142112320300384` | **가장 가까운 선행연구.** 반복 열충격 + 연속체 손상. 제2장에서 우리와의 차이(2스케일 여부·TRS 처리)를 밝혀야 한다 |
| **N11** | *Development and validation of an anisotropic damage constitutive model for C/SiC composite*, Ceram. Int. (2019), `S0272884218325495` | C/SiC 이방성 손상 구성모델. 제3장 정식화 위치 |
| **N12** | *Damage analysis of CVI SiCf/SiCm ceramic matrix composites under thermal shock* (2025) | 최신 열충격 손상 해석. SiC/SiC이지만 방법론 비교 |
| **N13** | *Multiphysics model of thermomechanical oxidative degradation in SiC/SiC CMC microstructures*, J. Eur. Ceram. Soc. (2025), `S0955221925001554` | 제7장 향후과제(산화 결합)의 최신 기준점 |
| **N14** | *Thermal-mechanical coupling constitutive theory for nonlinear ceramic matrix composite laminates*, J. Compos. Mater. (2026) | **가장 최신.** 제1장 "왜 지금인가"에 쓸 수 있다 |
| **N15** | *Multiphysics phase-field modeling of ceramic matrix composites: from oxidation-driven damage to digital twins* (2026) | 제7장 향후과제 — 우리 CDM 대비 위상장(phase-field) 계열 |
| **N16** | *Unraveling the oxidation-induced hoop tensile failure mechanism of 2.5D woven C/C–ZrC–SiC composites at 1100–1500 °C*, Compos. Part A (2026), `S1359836826001381` | 2026년 2월. 최신성 확보용 |
| **N17** | *Thermal cyclic fatigue damage evolution of fiber-reinforced ceramic-matrix composites under constant loading* (2021) | 2.5D C/SiC 열피로 손상 지표. 제6장 T1·T2 표적 비교 |

⚠️ N10–N17은 **초록만 본 상태**다. 제2장에 넣기 전에 최소한 초록 전문을 읽고
"무엇이 우리와 다른가"를 한 줄로 적을 수 있어야 한다. 지금 넣으면
`check_manuscript_citations`의 무인용 주장 검사에 걸린다.

---

## 5. 확보 우선순위 — 셋만 고른다면

| 순위 | 라벨 | 무엇이 풀리나 | 대안이 있나 |
|---|---|---|---|
| **1** | **N4** Dang 2024 | 상온 근방 복합재 CTE 절대값 **+** 기지 TRS 378 MPa | 없다. 두 병목을 동시에 친다 |
| **2** | **N1** Kulkarni 2006 | 섬유 횡방향 대역 5–10 → **3.8–5.6** | 없다. 우리 온도구간 직접 측정은 이것뿐 |
| **3** | **N8** Compos. Struct. 2021 | 공극→CTE 방향. 사다리 3→4단의 일부를 재료 차이로 귀속 | N9가 부분적으로 대신한다 |

**N4 하나만 받아도 이번 조사는 값을 한다.** 상온 근방 절대값과 기지 TRS를
동시에 주는 논문은 지금까지 하나도 없었다.

---

## 6. 이 조사가 저장소에 남긴 조치

1. **아무 카드값도 바꾸지 않았다.** 전부 `search-verified`이므로 규칙상 불가하다.
2. `data/literature/cte_composite_targets.py`의 **공극 관련 문장에 확인 표시**를
   달았다 — N8이 반대 방향을 보고하므로, 확보 전까지 그 문장을 근거로 인용하지
   않는다.
3. `data/properties/cte_sensitivity.py`의 5–10 대역 설명에 **"refs/[07]의 횡방향은
   역해석 값"** 이라는 사실을 적었다(N2 제목이 근거).
4. 제4장 §4.9-10의 사다리·판정은 **바꾸지 않았다.** 위 값들이 전부 미확보이므로
   바꿀 근거가 없다. 확보되면 2→3단의 폭이 좁아진다.
