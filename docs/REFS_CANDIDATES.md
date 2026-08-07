# 신규 참고문헌 후보 — 우선순위 목록

**작성:** 2026-08-03 14:13 KST · 6개 병렬 문헌조사 결과 종합
**대상:** `refs/[01]`–`[45]` 45편과 **중복되지 않으면서** 본 연구의 미결 항목을 닫는 문헌

---

## 0. 이 문서를 읽는 법

### 0.1 등급 정의

| 등급 | 기준 | 없으면 |
|---|---|---|
| **S** | 본문이 **이름으로 인용하는데 참고문헌 목록에 원전이 없다** | 심사에서 즉시 지적 |
| **A** | 카드의 GUESS·하드픽스 숫자를 **출처 있는 값**으로 바꾼다 | 숫자를 못 채운다 |
| **B** | 모델 출력을 **대조할 실측**을 준다 | 검증을 못 한다 |
| **C** | 방법론적 주장의 **근거**가 된다 | 노벨티 주장이 무근거로 뜬다 |
| **D** | 서술·고찰 보강 | 있으면 좋다 |

### 0.2 카드 적법성 표기 — 이걸 틀리면 TRS를 이중 계산한다

| 표기 | 뜻 |
|---|---|
| **[카드]** | 구성재(섬유·기지·계면·얀) 수준 → UMAT 카드 **입력 허용** |
| **[검증]** | 복합재 수준 → 모델 출력과 **대조 전용**, 입력 금지 |
| **[방법]** | 수치·이론 근거. 숫자를 주지 않음 |

### 0.3 서지 검증 상태 — ★ 반드시 확인할 것

이 조사는 **WebFetch·curl이 전 호스트 403으로 차단된 환경**에서 수행되었다.
출판사 페이지를 **한 건도 직접 열지 못했고**, 검증은 전부 WebSearch 결과 요약에 의존했다.

| 표기 | 뜻 |
|---|---|
| **✔ 확정** | DOI가 검색결과 URL에 그대로 포함 + 권·호·페이지가 2개 이상 출처에서 일치 |
| **△ 부분** | 일부 필드만 확인. 비어 있는 칸은 **비워 두었다** |
| **✗ 미검증** | 서지 상세 미확인. **이 상태로 논문에 적으면 안 된다** |

**DOI·페이지를 지어내지 않았다.** 확인 못 한 것은 빈칸 또는 PII로 남겼다.
`data/literature/README.md`의 신뢰도 규칙에 따라, 원문 확보 전에는 전부 `abstract` 이하 등급이다.

---

## 1. ★ 즉시 반영해야 할 **본문 오류 3건**

문헌 조사 중 **현재 초안에 이미 들어가 있는 잘못된 서술**이 발견되었다. 새 문헌 추가와
별개로 먼저 고쳐야 한다.

### 1.1 `R''''`의 출처가 틀렸다 — 제2장 §2.4

제2장은 열충격 손상저항 파라미터 `R'''' = E·γ_f / [σ_f²(1−ν)]`를 **Hasselman 1969**에
귀속시킨다. **틀렸다.**

| 파라미터 | 올바른 출처 |
|---|---|
| `R = σ_f(1−ν)/(Eα)` | **Kingery 1955**, JACerS 38(1) 3–15 |
| **`R''''`** | **Hasselman 1963**, JACerS 46(11) 535–540 |
| `R_st` (균열 안정성) | Hasselman 1969, JACerS 52(11) 600–604 |

**세 편 모두 인용해야** §2.4의 교차검증 서술이 성립한다. 특히 1969년 논문은
**반복 열충격에서 "1회차 급락 후 완만"한 잔여강도 곡선이 왜 나오는지**를 설명하므로
본 연구 주제에 가장 잘 맞는다.

### 1.2 Hashin 1980은 이미 3차원이다 — 제2장 §2.6.1

"3D Hashin 기준"이라 쓰면서 별도의 3D 확장 문헌을 찾을 필요가 없다. **Hashin 1980이
그 자체로 3차원**이고, 흔히 쓰는 평면응력형이 오히려 축약판이다.

정말 필요한 것은 **판정식 → 손상변수 → 연화 강성**의 매핑이며, 그 원전은
**Matzenmiller, Lubliner & Taylor 1995**다. Abaqus 계열 복합재 손상 UMAT의 사실상 조상이다.

### 1.3 Chamis 인용은 확인 불가능한 형태다 — 제3·4장

`SAMPE Quarterly 15(3) 14–23`은 **DOI가 없고 원문 확보가 어렵다.** 심사위원이 확인할 수 없다.
→ **NASA TM-83320 (NTRS ID 19830011546)을 주 인용**으로 하고 SAMPE를 병기한다.
내용은 동일하고 NTRS는 무료 공개다.

---

## 2. S등급 — 기법 원전 (**최우선**)

> **현재 45편은 전부 응용 논문이고 기법 원전이 0편이다.** 본문은 Bažant, Hashin,
> Tsai–Wu, Chamis, Schapery를 이름으로 부르는데 참고문헌에 없다. 이것이 이번 조사에서
> 발견한 **가장 큰 구조적 결함**이다.

| # | 서지 | DOI | 검증 | 어디에 쓰는가 |
|---|---|---|---|---|
| **S1** | Bažant, Z.P., Oh, B.H. (1983). "Crack band theory for fracture of concrete." *Materials and Structures* **16**(93), 155–177. | `10.1007/BF02486267` | ✔ | §2.5.2 균열대 정규화 전체, `yarn_fracture_energy.py`의 스냅백 한계 `l_e < G_f/g_0` |
| **S2** | Hashin, Z. (1980). "Failure criteria for unidirectional fiber composites." *J. Appl. Mech.* **47**(2), 329–334. | `10.1115/1.3153664` | ✔ | §2.6.1, `KYARN31`의 4모드 판정식 |
| **S3** | Tsai, S.W., Wu, E.M. (1971). "A general theory of strength for anisotropic materials." *J. Compos. Mater.* **5**(1), 58–80. | `10.1177/002199837100500106` | ✔ | §2.6.1, C4의 Tsai–Wu 축 |
| **S4** | Liu, K.-S., Tsai, S.W. (1998). "A progressive quadratic failure criterion for a laminate." *Compos. Sci. Technol.* **58**(7), 1023–1032. | `10.1016/S0266-3538(96)00141-8` | ✔ (DOI는 PII 환산) | **강도비 R 정규화의 1차 출처.** `aR²+bR=1`을 풀어 Tsai–Wu를 1차 동차로 만드는 그 변환 — §2.6.1의 "반드시 주의할 점" 박스 |
| **S5** | Matzenmiller, A., Lubliner, J., Taylor, R.L. (1995). "A constitutive model for anisotropic damage in fiber-composites." *Mech. Mater.* **20**(2), 125–152. | `10.1016/0167-6636(94)00053-0` | ✔ | §2.5.1의 판정식→손상변수 매핑, DDSDDE 유도 |
| **S6** | Chamis, C.C. (1983). *Simplified Composite Micromechanics Equations for Hygral, Thermal and Mechanical Properties.* NASA TM-83320. | — (NTRS 19830011546) | ✔ | `micromech_check.py`가 검증하는 얀 물성 전부 |
| **S6b** | Chamis, C.C. (1984). 동제목, *SAMPE Quarterly* **15**(3), 14–23. | 없음 | △ | S6과 병기 |
| **S7** | Schapery, R.A. (1968). "Thermal expansion coefficients of composite materials based on energy principles." *J. Compos. Mater.* **2**(3), 380–404. | `10.1177/002199836800200308` | ✔ | 얀 CTE 균질화, `cte_sensitivity.py` |
| **S8** | Van Paepegem, W., Degrieck, J., De Baets, P. (2001). "Finite element approach for modelling fatigue damage in fibre-reinforced composite materials." *Compos. Part B* **32**(7), 575–588. | `10.1016/S1359-8368(01)00038-5` | ✔ | **cycle jump의 최적 1차 인용.** Gauss점별 국소 점프 → 누적분포 분위수로 전역 점프 결정. 검증 대상이 **평직 유리/에폭시**라 구조가 같다 |
| **S9** | Chaboche, J.-L. (1993). "Development of continuum damage mechanics for elastic solids sustaining anisotropic and unilateral damage." *Int. J. Damage Mech.* **2**(4), 311–329. | `10.1177/105678959300200401` | ✔ | §2.5.3 단방향 손상 (`HCLO`) |
| **S10** | Chaboche, J.-L. (1992). "Damage induced anisotropy: on the difficulties associated with the active/passive unilateral condition." *Int. J. Damage Mech.* **1**(2), 148–171. | `10.1177/105678959200100201` | ✔ | ★ **M1 비수렴 분석 직결.** 손상 비활성화가 강성텐서를 불연속·비대칭으로 만들어 Newton 수렴을 깨뜨리는 메커니즘의 원출처. §2.5.3 "수치적 주의" 박스와 `docs/M1_FAILURE_ANALYSIS.md` |
| **S11** | Kingery, W.D. (1955). "Factors affecting thermal stress resistance of ceramic materials." *J. Am. Ceram. Soc.* **38**(1), 3–15. | `10.1111/j.1151-2916.1955.tb14545.x` | ✔ | §2.4 `R` |
| **S12** | Hasselman, D.P.H. (1963). "Elastic energy at fracture and surface energy as design criteria for thermal shock." *J. Am. Ceram. Soc.* **46**(11), 535–540. | `10.1111/j.1151-2916.1963.tb14605.x` | ✔ | §2.4 **`R''''` (현재 오귀속)** |
| **S13** | Hasselman, D.P.H. (1969). "Unified theory of thermal shock fracture initiation and crack propagation in brittle ceramics." *J. Am. Ceram. Soc.* **52**(11), 600–604. | `10.1111/j.1151-2916.1969.tb15848.x` | ✔ | §2.4 `R_st`, 반복 열충격 잔여강도 곡선 형상 |
| **S14** | Lemaitre, J., Chaboche, J.-L. (1990). *Mechanics of Solid Materials.* Cambridge Univ. Press. | ISBN 978-0-521-32853-1 | ✔ | §2.5.1 유효응력·변형률등가 |
| **S15** | Lemaitre, J. (1985). "A continuous damage mechanics model for ductile fracture." *J. Eng. Mater. Technol.* **107**(1), 83–89. | `10.1115/1.3225775` | ✔ | S14의 저널 대체본 (교과서 인용을 꺼릴 때) |
| **S16** | Kachanov, L.M. (1958). "Time of the rupture process under creep conditions." *Izv. AN SSSR, Otd. Tekh. Nauk* **8**, 26–31. | 없음 | △ | 손상변수의 최초 도입 |
| **S17** | Curtin, W.A. (1991). "Theory of mechanical properties of ceramic-matrix composites." *J. Am. Ceram. Soc.* **74**(11), 2837–2845. | `10.1111/j.1151-2916.1991.tb06852.x` | ✔ | §2.2.2 섬유 인발, GLS 강도 |
| **S18** | Aveston, J., Kelly, A. (1973). "Theory of multiple fracture of fibrous composites." *J. Mater. Sci.* **8**(3), 352–362. | `10.1007/BF00550155` | ✔ | §2.2.2 기지 다중균열. **ACK 1971 프로시딩보다 이쪽을 주 인용 권장** (페이지 표기 충돌 없음) |
| **S19** | Ladevèze, P., Le Dantec, E. (1992). "Damage modelling of the elementary ply for laminated composites." *Compos. Sci. Technol.* **43**(3), 257–267. | `10.1016/0266-3538(92)90097-M` | ✔ | 인장/압축 손상 분리 구현형 |
| **S20** | Chaboche, J.-L., Lesne, P.-M., Maire, J.-F. (1995). "Continuum damage mechanics, anisotropy and damage deactivation for brittle materials like concrete and ceramic composites." *Int. J. Damage Mech.* **4**(1), 5–22. | `10.1177/105678959500400102` | △ (페이지 미검증) | S9·S10을 **CMC 맥락**에 적용한 편 |
| **S21** | Jirásek, M., Bauer, M. (2012). "Numerical aspects of the crack band approach." *Comput. Struct.* **110–111**, 60–78. | `10.1016/j.compstruc.2012.06.006` | ✔ | **3D solid + 연화에서 `l_e`를 어떻게 정의하는가.** 체적^(1/3) 사용 시 균열이 대각선으로 지날 때의 소산에너지 오차를 정량화 |
| **S22** | Oliver, J. (1989). "A consistent characteristic length for smeared cracking models." *Int. J. Numer. Methods Eng.* **28**(2), 461–474. | `10.1002/nme.1620280214` | ✔ | 특성길이를 `G_f/g_0` 비로 정의 — 본 연구가 쓰는 부등식과 형태 동일 |
| **S23** | Cojocaru, D., Karlsson, A.M. (2006). "A simple numerical method of cycle jumps for cyclically loaded structures." *Int. J. Fatigue* **28**(12), 1677–1689. | `10.1016/j.ijfatigue.2006.01.010` | ✔ | S8의 보완 — 적응형 ΔN 제어함수. ★ **저널이 *Int. J. Fatigue*임에 유의** (FEAD 아님) |
| **S24** | Hashin, Z., Rotem, A. (1973). "A fatigue failure criterion for fiber reinforced materials." *J. Compos. Mater.* **7**(4), 448–464. | `10.1177/002199837300700404` | ✔ | S2의 피로판 |

---

## 3. A등급 — 카드의 숫자를 채우는 문헌

### 3.1 ★ `fX/fY/fS = 1.0` 하드픽스가 **근거 있는 선택**이 된다

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A1** | Xu, T.T., Cheng, S., Jin, L.Z., Zhang, K., Zeng, T. (2020). "High-temperature flexural strength of SiC ceramics prepared by additive manufacturing." *Int. J. Appl. Ceram. Technol.* **17**, 438–448. | `10.1111/ijac.13454` | ✔ (쪽수 △) | **[카드]** |

**SLS + PIP**로 만든 SiC — **본 연구의 PIP 기지와 같은 계열**이다.

| T (°C) | RT | 800 | 1200 | 1400 | 1600 |
|---|---|---|---|---|---|
| σ_f (MPa) | 220.0 | 226.1 | 234.9 | 215.5 | 203.7 |
| **fX(T)** | **1.000** | **1.028** | **1.068** | **0.980** | **0.926** |

→ **현재 하드픽스 1.0은 폐기 대상이 아니라 인용 가능한 선택**이 된다. 1400 °C까지 fX ≈ 1.00±0.07.
`data/properties/eval_correlations.py`에 상관식으로 넣고 `--check`에 가드를 추가한다.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A2** | Cockeram, B.V. (2005). "Flexural Strength and Shear Strength of SiC-to-SiC Joints Fabricated by a Mo Diffusion Bonding Technique." *J. Am. Ceram. Soc.* **88**(7), 1892–1899. | `10.1111/j.1551-2916.2005.00381.x` | ✔ (쪽수 △) | **[카드]** |

치밀 **CVD** SiC: RT → 1100 °C에서 **443 → 197 MPa (유지율 44 %)**. A1과 **정반대 경향**.
→ **§2.9-1 "PIP vs CVD 공정 불일치"가 실제로 결과를 가른다는 직접 증거.**
같은 SiC라도 제조법이 다르면 고온 거동이 반대다.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A3** | Cockeram, B.V. (2004). "Fracture Toughness and Flexural Strength of CVD SiC … Chevron-Notched and Surface Crack in Flexure Specimens." *J. Am. Ceram. Soc.* **87**(6), 1093–1101. | `10.1111/j.1551-2916.2004.01093.x` | ✔ (권·쪽 △) | **[카드]** |

CVD SiC의 **K_Ic = 2.8–5.5 MPa√m 이고 시험온도(RT→1100 °C)와 무관**.
→ **`G_f` = 0.031 N/mm를 온도 상수로 두는 현재 UMAT 구조가 문헌과 일치**한다.
온도 스케일링을 강도에만 넣은 설계에 인용 근거가 생겼다. §4.9-8에 추가.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A4** | Lee, H.M., Park, K.-I., Park, J.-Y., Kim, W.-J., Kim, D.K. (2015). "High-Temperature Fracture Strength of a CVD-SiC Coating Layer for TRISO Nuclear Fuel Particles by a Micro-Tensile Test." *J. Korean Ceram. Soc.* **52**(6), 441–448. | `10.4191/kcers.2015.52.6.441` | ✔ | **[카드]**, **OA** |
| **A5** | Breder, K. et al. (1995). "Time-Dependent Strength Degradation of a Siliconized Silicon Carbide Determined by Dynamic Fatigue." *J. Am. Ceram. Soc.* **78**. | `10.1111/j.1151-2916.1995.tb08040.x` | △ | **[카드]** 보조 |
| **A6** | Munro, R.G. (1997). "Material Properties of a Sintered α-SiC." *J. Phys. Chem. Ref. Data* **26**(5), 1195–1203. | `10.1063/1.556000` | ✔ | **[카드]**, **OA** |

- A4: RT→1000 °C에서 **파괴강도는 감소, 탄성계수는 유의미한 변화 없음** → UMAT 구조(E(T)≈const, fX(T)<1)와 일치. 한국 저널이라 심사 접근성도 좋다.
- A5: **Weibull m = 10.8 (RT) → 7.8 (1100 °C) → 2.8 (1400 °C)**. 고온에서 강도 산포가 붕괴하는 유일한 정량 근거.
- A6: NIST 표준참조데이터. **하나의 인용으로 E·강도·k·CTE·Cp를 전부 온도 의존으로** 채울 수 있는 유일한 후보. 무료.

### 3.2 ★ PIP 기지 물성 — 카드 두 값이 과대일 가능성

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A7** | Santhosh, B., Ionescu, E., Andreolli, F., Biesuz, M., Reitz, A., Albert, B., Sorarù, G.D. (2021). "Effect of pyrolysis temperature on the microstructure and thermal conductivity of polymer-derived monolithic and porous SiC ceramics." *J. Eur. Ceram. Soc.* **41**(2), 1151–1162. | `10.1016/j.jeurceramsoc.2020.09.028` | ✔ | **[카드]** |

PDC-SiC의 열전도율이 **0.5 ~ 47 W/(m·K)**, 지배 변수는 **1200 °C 이상의 나노결정→결정 전이**.
→ **본 연구 열분해는 1050 °C = 전이 이전 = 비정질 = k 하한.**
Snead(CVD) 값을 쓰면 기지 k를 **크게 과대평가**하고 있을 수 있고, 이는 §5.4.3의 Biot 사다리를 바꾼다.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A8** | Ren, Z., Mujib, S.B., Singh, G. (2021). "High-Temperature Properties and Applications of Si-Based Polymer-Derived Ceramics: A Review." *Materials* **14**(3), 614. | `10.3390/ma14030614` | ✔ | **[카드]**, **OA** |

1000 °C 열분해 PDC의 **E = 157–163 GPa**. 1100 °C 열분해 SiOC/SiCN은 **여전히 비정질**,
결정화 개시는 1300–1500 °C.
→ **현재 카드 E = 350 GPa는 약 2배 과대**일 가능성. §4.9-8의 "IN" 판정 8개 중 하나가 흔들린다.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A9** | Stabler, C., Reitz, A., Stein, P., Albert, B., Riedel, R., Ionescu, E. (2018). "Thermal Properties of SiOC Glasses and Glass Ceramics at Elevated Temperatures." *Materials* **11**(2), 279. | `10.3390/ma11020279` | ✔ | **[카드]** 경계값, **OA** |
| **A10** | Sujith, R., Jothi, S., Zimmermann, A., Aldinger, F., Kumar, R. (2021). "Mechanical behaviour of polymer derived ceramics – a review." *Int. Mater. Rev.* **66**. | `10.1080/09506608.2020.1784616` | △ | **[카드]** |
| **A11** | (저자 미검증) (2011). "Influence of polymer infiltration and pyrolysis process on mechanical strength of polycarbosilane-derived silicon carbide ceramics." *J. Mater. Sci.* **46**. | `10.1007/s10853-010-5182-0` | △ | **[카드]** |
| **A12** | Hu, J., Liu, C., Ye, F., Cheng, L., Wei, Y. (2024). "A review on high-performance SiCf/SiC composites prepared by PIP process." *J. Mater. Res. Technol.* **33**, 7216–7235. | ✗ | ✗ | **[검증]** + 서술 인용, **OA** |

A11은 **PIP 3사이클 이상에서 취성 거동으로 전환**한다고 보고 — 기지를 취성 CDM으로 다루는 것의 정당화.

### 3.3 ★ 섬유 횡방향 열전도율 — `refs/README.md` §2-7의 "아무도 측정 안 함"이 닫힌다

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A13** | (저자 미검증) (2022). "Anisotropic thermal and electrical conductivities of individual polyacrylonitrile-based carbon fibers." *Carbon* **197**. | ✗ (PII `S0008622322004353`) | ✗ | **[카드]** |

TDTR 매핑으로 **개별 PAN 섬유의 축·횡 열전도율을 각각 직접 측정**:

| | k_축 (W/m·K) | k_횡 (W/m·K) |
|---|---|---|
| IM7 | 7.5 | **2.0** |
| AS4 | 6.9 | **3.0 (core) / 2.4 (shell)** |

→ **이방성비 3–4.** T300은 아니지만 IM7·AS4 모두 PAN계 상용 섬유라 대리값으로 가장 방어 가능.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A14** | Olaya Gómez, R.A., Garnier, B. (2022). "Radial thermal conductivity of a PAN type carbon fiber using the 3 omega method." *Int. J. Therm. Sci.* **172**, 107321. | ✗ | △ | **[카드]**, **OA (HAL hal-03430963)** |
| **A15** | Olaya Gómez, R.A., Garnier, B. (2021). "Design of a new device for fibers strand axial thermal conductivity measurement." *Int. J. Therm. Sci.* **159**. | ✗ (PII `S1290072920311844`) | ✗ | **[카드]** |

★ **FT300B = T300 계열 섬유 자체**를 측정했다. 결론: **반경방향 k는 축방향의 약 1/10.**
A15에서 축방향 k ≈ 9.78 W/(m·K) [수치 미검증].
→ **T300 자체 재료에 대한 유일한 직접 측정.** A13(대리값)보다 우선한다.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A16** | Trinquecoste, M., Carlier, J.L., Derré, A., Delhaès, P., Chadeyron, P. (1996). "High temperature thermal and mechanical properties of high tensile carbon single filaments." *Carbon* **34**(7), 923–929. | ✗ | △ | **[카드]** 온도의존 보강 |

### 3.4 기공률 보정 — §4.9-3 미결 항목

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A17** | Smith, D.S., Alzina, A., Bourret, J., Nait-Ali, B., Pennec, F., Tessier-Doyen, N., Otsu, K., Matsubara, H., Elser, P., Gonzenbach, U.T. (2013). "Thermal conductivity of porous materials." *J. Mater. Res.* **28**(17), 2260–2272. | `10.1557/jmr.2013.179` | ✔ (끝쪽 △) | **[방법]** |

**ν_p < 0.65에서 폐기공 = Maxwell–Eucken, 개기공 = Landauer(EMT)**가 실험과 일치.
HS 상·하한이 Maxwell–Eucken 두 형태와 수학적으로 동치임도 명시.
→ **100 % 치밀 RVE의 k̄ 과대평가를 사후 보정식 한 줄로 정당화**할 수 있다. `conductivity_bounds.py`에 추가.

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A18** | Kim, Y.W., Kim, K.J. et al. (2020). "Effects of porosity on electrical and thermal conductivities of porous SiC ceramics." *J. Eur. Ceram. Soc.* **40**(4), 996–1004. | ✗ (PII `S0955221919307903`) | ✗ | **[카드]** |
| **A19** | (저자 미검증) (2021). "Influence of porosity on anisotropic thermal conductivity of SiC fiber reinforced SiC matrix composite: A microscopic modeling study." *Ceram. Int.* | ✗ (PII `S0272884220323944`) | ✗ | **[방법]** |
| **A20** | Pabst, W., Gregorová, E., Tichá, G. (2006). "Elasticity of porous ceramics — A critical study of modulus–porosity relations." *J. Eur. Ceram. Soc.* **26**. | ✗ (PII `S0955221905000981`) | ✗ | **[방법]** |
| **A21** | Phani, K.K., Niyogi, S.K. (1987). "Young's modulus of porous brittle solids." *J. Mater. Sci.* **22**. | ✗ | ✗ | **[방법]** |

- A18: 기공률 **30 % → 63 %일 때 k = 37.9 → 5.8 W/(m·K)**. SiC 자체의 실측 데이터점.
- A19: 기공률 10 %→18 %에서 등가 열전도율 **14.21 % 감소**. CMC 특화 모델.
- A20/A21: `E = E₀(1 − aP)ⁿ`. A7·A8의 낮은 PDC E와 결합하면 **E = 350 GPa 재검토의 두 번째 축**.

### 3.5 ★ 얀·계면 GUESS 14개 중 9개 전환

| # | 서지 | DOI | 검증 | 전환되는 GUESS |
|---|---|---|---|---|
| **A22** | Yu, G., Xie, C., Du, J., Ni, Z., Chang, L., Gao, X., Song, Y. (2023). "In-plane shear experimental method and mechanical behavior of ceramic matrix mini-composites." *J. Mater. Res. Technol.* **24**, 5541–5551. | `10.1016/j.jmrt.2023.04.139` | ✔ | **S_12, S_13, S_23** — **[카드]**, **OA** |
| **A23** | Yu, G. et al. (2022). "Transverse tensile mechanical experimental method and behavior of ceramic matrix mini-composites." *Compos. Struct.* **297**, 115923. | `10.1016/j.compstruct.2022.115923` | ✔ | **Y_t** — **[카드]** |

★ **이 두 편이 이번 조사의 최대 수확이다.** 난징항공대(NUAA) Gao/Song 그룹의
**CMC 미니콤포지트 횡방향 인장·면내 전단 직접 시험** — 사실상 세계에서 유일한 **tow-level** 측정이며,
따라서 **카드 입력이 적법**하다. **A22는 오픈액세스라 지금 바로 표를 열 수 있다.**

| # | 서지 | DOI | 검증 | 전환되는 GUESS |
|---|---|---|---|---|
| **A24** | Li, L., Su, K., Chen, Z., Zhang, Z., Xiong, X. (2024). "Influence of interphase type and thickness on the interface properties and tensile damage evolution of C/SiC composites." *Proc. IMechE Part L* | `10.1177/14644207241234395` | ✔ | **X_PO, K_1, r_F** — **[카드]** |
| **A25** | Duan et al. (2022). "Effect of pyrocarbon interphase texture and thickness on tensile damage and fracture in T-700™ carbon fiber–reinforced silicon carbide minicomposites." *J. Am. Ceram. Soc.* **105**, 2171–2181. | `10.1111/jace.18193` | ✔ | **X_PO, K_1** — **[카드]** |
| **A26** | (저자 미검증) (2024). "Actively-controlled PyC interphase failure mechanisms in C/SiC composite revealed using micro-mechanical interfacial testing." *Ceram. Int.* | ✗ (PII `S0272884224054403`) | ✗ | **K_1** — **[카드]** |
| **A27** | Zhang, Z., Li, L., Chen, Z. (2021). "Damage Evolution and Fracture Behavior of C/SiC Minicomposites with Different Interphases under Uniaxial Tensile Load." *Materials* **14**(6), 1525. | `10.3390/ma14061525` | ✔ | **[카드]**, **OA** |
| **A28** | (저자 미검증) (1998). "Effects of temperature and of oxidation on the interfacial shear stress between fibres and matrix in ceramic-matrix composites." *Acta Mater.* | ✗ (PII `S1359645498800293`) | ✗ | **τ(T)** — C3 서사 핵심 |

**★ 반드시 지킬 구분 — 섞으면 두 자릿수가 틀린다:**

| 물리량 | 값 | 대응 카드 |
|---|---|---|
| **디본딩 강도 (IDSS)** | HT-PyC **322 MPa** / LT-PyC **163 MPa** (마찰계수 0.139 / 0.341, Mohr-Coulomb) | **K_1** |
| **슬라이딩 마찰 τ** | **≈ 5–50 MPa** (상온 10 MPa → 1300 °C까지 소폭 감소) | **X_PO** |

A24는 PyC 두께 **300 / 600 / 1000 / 2000 nm**를 다룬다. **본 연구의 0.2 µm = 200 nm는 이 범위의 아래 끝 밖**이므로
**외삽임을 명시**해야 한다.

**전환 불가 — 문헌에 존재하지 않음:**
> **Y_c(얀 횡방향 압축)와 X_c(축방향 압축)의 tow-level 측정법 자체가 없다.**
> 미니콤포지트를 횡방향으로 압축하는 시험법이 존재하지 않는다. 검색 실패가 아니다.
> **"측정법 부재"로 §4.9-8에 정직하게 서술한다.**

### 3.6 ★ `G_tc` — §4.9-6a 스냅백 4 % 문제에 답이 나왔다

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A29** | Pinho, S.T., Robinson, P., Iannucci, L. (2006). "Fracture toughness of the tensile and compressive fibre failure modes in laminated composites." *Compos. Sci. Technol.* **66**(13), 2069–2079. | `10.1016/j.compscitech.2005.12.023` | ✔ | **[방법]** |

| 모드 | 값 |
|---|---|
| 섬유 인장 G_ft (개시 / 전파) | 91.6 / 133 kJ/m² |
| 섬유 압축 G_fc (개시) | 79.9 kJ/m² |
| 섬유 압축 G_fc (전파) | **측정 불가** |

★ **원조 논문에서조차 압축 파괴에너지의 전파값을 확정하지 못했다.**
같은 IM7/8552를 방법 바꿔 재면 **26 / 61 / 79.9 kJ/m² — 3배** 벌어진다.
→ **"정확한 압축 파괴에너지는 문헌에 존재하지 않는다"가 사실이며, 이것이 `G_tc` 가정을 방어하는 최강 논거다.**

| # | 서지 | DOI | 검증 | 적법성 |
|---|---|---|---|---|
| **A30** | Dalli, D., Catalanotti, G., Varandas, L.F., Falzon, B.G., Foster, S. (2020). "Compressive intralaminar fracture toughness and residual strength of 2D woven carbon fibre reinforced composites: New developments on using the size effect method." *Theor. Appl. Fract. Mech.* **106**, 102487. | `10.1016/j.tafmec.2020.102487` | △ | **[방법]** |
| **A31** | Maimí, P., Camanho, P.P., Mayugo, J.A., Dávila, C.G. (2007). "A continuum damage model for composite laminates: Part I – Constitutive model." *Mech. Mater.* **39**(10), 897–908. | `10.1016/j.mechmat.2007.03.005` | ✔ | **[방법]** |
| **A32** | 동, "Part II – Computational implementation and validation." *Mech. Mater.* **39**(10), 909–919. | `10.1016/j.mechmat.2007.03.006` (**추정**) | △ | **[방법]** |

A30은 **2D 직조** CFRP의 압축 층내 파괴인성 + post-peak crushing stress를 측정 — **본 연구 아키텍처에 가장 가깝다.**

**⚠️ 출처 미상 수치 — 확인 전 인용 금지:**
> 직조 복합재 4개 조: 종인장 453.89 / 종압축 114.44 / **횡인장 0.53 / 횡압축 7.52 kJ/m²**
> → **G_tc / G_tt ≈ 14.2**
>
> 이 세트의 출처 논문을 특정하지 못했다. 검색엔진이 A30과 어떤 LS-DYNA `MAT_261` 논문에
> 번갈아 귀속시켰다. **그러나 물리적 근거는 별개로 확실하다** — 횡방향 압축은 mode I 개구가
> 아니라 **약 53° 면의 전단 구동 파괴**이므로 `G_tc`는 **mode II에 묶여야** 한다(Camanho/LaRC 표준 논리).
>
> **`G_tc`를 `G_tt`의 10배로 올리면 `l_ch = 2EG/X²`가 10배가 되어 1059개(4.0 %) 위반이 소멸한다.**
> §4.9-6a의 선택지 (b)가 "측정값 아님"에서 "직조 복합재 데이터에 근거"로 승격된다.

### 3.7 ★ `σ_y0`·`H_iso` — GUESS가 아니라 **분류를 바꿔야 하는 항목**

> **SiC 기지의 항복응력을 측정한 문헌은 없고, 있을 수도 없다.**
> CVI/PIP SiC는 1000–1200 °C까지 취성이며 전위 소성이 활성화되지 않는다.
> CMC의 겉보기 소성(잔류변형·이력루프)은 문헌에서 **기지 미세균열 + 계면 슬라이딩**으로
> 설명되지 von Mises 소성으로 설명되지 않는다.
>
> → `σ_y0`, `H_iso`는 **물성이 아니라 수치 정규화**다. §4.9-8의 GUESS 14개 목록에서
> **"보정 knob"이 아니라 "정규화 파라미터"로 분류를 옮기고**, 결과가 이 두 값에 둔감함을
> 민감도로 보이는 것이 유일하게 방어 가능한 경로다.
>
> **대안:** A32(Maimí Part II)의 **점성 정규화** — *"A viscous model is proposed to mitigate the
> convergence difficulties associated with strain softening constitutive models"* — 로 갈아타면
> 동일한 수렴 효과를 **문헌 근거와 함께** 얻는다.

---

## 4. B등급 — 검증 데이터

### 4.1 ★★★ 반복 열충격 잔여물성 — 3건 → 최대 11건

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B1** | Kagawa, Y. (1997). "Thermal shock damage in a two-dimensional SiC/SiC composite reinforced with woven SiC fibers." *Compos. Sci. Technol.* **57**(5), 607–611. | ✗ (PII `S0266353897000055`) | △ | **2D 평직 — 본 연구와 동일 아키텍처.** 원문: *"saturation of the crack density and formation of long cracks **after three repeated thermal shock events**"* → **k<0의 직접 증거이자 포화 사이클수 N≈3** |
| **B2** | (저자 미검증) (2006). "Thermal shock behavior of a three-dimensional SiC/SiC composite." *Metall. Mater. Trans. A* | `10.1007/s11661-006-1053-3` | △ | 수냉 **1200→25 °C, 100사이클, 잔여강도 80 %**, 기공밀도 **포화** 명시. **YIN2002(83 %)의 독립 재현** |
| **B3** | Xu, Q., Jin, X., Liu, L., Hou, C., Hu, N., Chen, J., Zhao, S., Marrow, T.J., Fan, X. (2023). "Thermal Shock and Residual Strength Testing of SiC/SiC Composite Braided Tubes." *Exp. Mech.* **63**(5), 955–964. | `10.1007/s11340-023-00962-x` | ✔ | **석영램프 복사가열 = 진짜 온도구배.** C-ring 잔여 원주강도 vs 사이클수 + FEM 열응력 해석. **C2의 최근접 선행연구.** **OA (Oxford ORA)** |
| **B4** | You, B., Li, B., Li, X., Ma, X., Zhang, Y., Cheng, L. (2024). "Thermal Shock Damage and In-plane Shear Performance Degradation of 2D SiCf/SiC at Medium Temperature." *J. Inorg. Mater.* **39**(12), 1367–1376. | `10.15541/jim20240273` | ✔ | **2D, 중온(=산화 지배)**, **면내 전단** 저하 → `S̄` 카드와 직결. 대부분 문헌이 인장/굽힘만 보는데 희소. **OA** |
| **B5** | Yang et al. (2019). "Effects of thermal aging on the cyclic thermal shock behavior of oxide/oxide CMCs." *Mater. Sci. Eng. A* **769**, 138494. | `10.1016/j.msea.2019.138494` | ✔ | **refs/[01] Yang & Liu 모델의 실험 원데이터로 추정.** oxide/oxide라 PyC 산화가 없음 → **산화 없는 baseline**으로 쓰면 메커니즘 논증이 강해진다 |
| **B6** | (저자 미검증) (2024). "Properties evolution and damage mechanism of SiC/SiC composites after thermal shock at 1300 °C." *Ceram. Int.* **50**(18B) | ✗ (PII `S0272884224026762`) | ✗ | **2D와 2.5D를 같은 조건으로 비교**하는 유일한 자료. 10–30사이클, 중량·밀도·기공률·굽힘물성 동시. 초기 중량 **증가** 후 감소 → 1300 °C가 밀봉 영역임을 지지 |
| **B7** | Kastritseas, C., Smith, P.A., Yeomans, J.A. (2008). "Thermal shock behaviour of angle-ply and woven dense ceramic-matrix composites." *J. Mater. Sci.* **43**, 4112–4118. | `10.1007/s10853-007-2314-2` | ✔ | Nicalon/CAS 평직 + (±45°)3s. **경향 검증용** (C/SiC 아님) |
| **B8** | Wang, H., Singh, R.N., Lowden, R.A. (1996). "Thermal Shock Behavior of Two-Dimensional Woven Fiber-Reinforced Ceramic Composites." *J. Am. Ceram. Soc.* **79**, 1783–1792. | `10.1111/j.1151-2916.1996.tb07996.x` | ✔ | 2D 직조 CMC 열충격의 고전 |
| **B9** | Liu, X., Guo, X., Xu, Y., Li, L., Zhu, W., Zeng, Y., Li, J., Luo, X., Hu, X. (2021). "Cyclic Thermal Shock Damage Behavior in CVI SiC/SiC High-Pressure Turbine Twin Guide Vanes." *Materials* **14**(20), 6104. | `10.3390/ma14206104` | ✔ | 1400–1480 °C **400사이클**, XCT상 내부 손상 없음 → **SiC 산화막이 내부를 보호. k<0(밀봉) 분기의 부품레벨 증거.** 잔여강도 곡선은 없음 → 서론용. **OA** |

**빈 칸으로 남은 것:** **PIP 공정 C/SiC의 사이클별 잔여물성 데이터셋은 존재를 확인하지 못했다.**
우선 탐색했으나 없었다. → **§5.9.2에 명시적 한계로 적는다.**

### 4.2 ★★★ `k` 부호 — 조사 결론이 §NOVELTY의 가설을 **더 정밀하게** 만든다

> **부호를 가르는 것은 아키텍처(2D/3D)가 아니라 온도역이다.**

| 온도역 | 기구 | 부호 | 근거 |
|---|---|---|---|
| **> 1000–1100 °C** | SiC 산화로 실리카가 **충분한 양과 유동성**을 가져 균열을 **밀봉** → 산소 침투 둔화 | **k < 0** | B2, B6(1300 °C 중량 안정화), B9(400사이클 무손상) |
| **~ 600–1000 °C** | 실리카가 유동성 있게 형성되지 않아 밀봉 실패 → 균열 통로로 탄소 소진 지속 | **k > 0** | B10–B13 (Lamouroux <800 °C 급락, Morscher, Halbig) |

**보유 데이터 3건이 이 설명과 정확히 일치한다:**

| 데이터셋 | 온도 | 영역 | 관측 | 부호 |
|---|---|---|---|---|
| ZHANG2013 | **900↔300 °C** | 밀봉 실패 | E 98→46.5 GPa, 질량손실 −9.8 % | **k > 0** |
| YIN2002 | **1300→300 °C** | 밀봉 | 83 % 포화 | **k < 0** |
| MEI2005[43] | 700↔1200 °C, **아르곤** | 산화 배제 | 98.90 % | 사이클항 불필요 |

→ **`k`를 재료 상수가 아니라 `k(T_max)`로 두는 편이 문헌상 훨씬 방어하기 쉽다.**
이는 노벨티를 깎는 것이 아니라 **강화**한다 — "부호가 바뀌는 이유를 모델이 안다"가 되기 때문이다.
`docs/NOVELTY.md` §A.1의 "2D vs 3D" 프레임을 "밀봉 vs 비밀봉"으로 **바꿔야 한다.**

### 4.3 산화 kinetics — `k > 0`의 물리 근거

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B10** | Halbig, M.C., McGuffin-Cawley, J.D., Eckel, A.J., Brewer, D.N. (2008). "Oxidation Kinetics and Stress Effects for the Oxidation of Continuous Carbon Fibers within a Microcracked C/SiC CMC." *J. Am. Ceram. Soc.* **91**(2), 519–526. | `10.1111/j.1551-2916.2007.02170.x` | ✔ | ★ **k>0의 1차 물리 근거.** "미세균열 → 산소 침투 → 탄소섬유/PyC 소진 → 하중전달 상실" 전체를 지지. **응력이 산화속도를 올린다**는 결과는 `<r − R_th>` 구동력 항과 산화의 결합을 정당화. **OA (NTRS 20040111387)** |
| **B11** | Lamouroux, F., Camus, G., Thebault, J. (1994). "Kinetics and Mechanisms of Oxidation of 2D Woven C/SiC Composites: I, Experimental Approach." *J. Am. Ceram. Soc.* **77**(8), 2049–2057. | `10.1111/j.1151-2916.1994.tb07096.x` | ✔ | **2D 직조 C/SiC**, 500–900 °C, T300 섬유. 중온역 kinetics 원데이터 |
| **B12** | Lamouroux, F., Naslain, R., Jouin, J.M. (1994). "…: II, Theoretical Approach." *J. Am. Ceram. Soc.* **77**(8), 2058–2068. | `10.1111/j.1151-2916.1994.tb07097.x` | ✔ | `C(T)`의 온도 의존성을 물리적으로 유도할 때 인용 |
| **B13** | Lamouroux, F., Naslain, R. et al. (1994). "Oxidation effects on the mechanical properties of 2D woven C/SiC composites." *J. Eur. Ceram. Soc.* **14**. | ✗ (PII `0955221994901058`) | ✗ | ★ **질량손실 ↔ 강도손실 직접 연결.** 상대 질량손실 **최대 6 %**까지 산화 후 상온 인장물성 측정. *"Oxidation at low temperatures (<800 °C) induced a **drastic decrease** of the composite tensile properties"* → **ZHANG2013의 −9.8 %를 강도 저하와 잇는 정량 다리** |
| **B14** | Filipuzzi, L., Camus, G., Naslain, R., Thebault, J. (1994). "Oxidation Mechanisms and Kinetics of 1D-SiC/C/SiC Composite Materials: I." *J. Am. Ceram. Soc.* **77**(2), 459–466. | `10.1111/j.1151-2916.1994.tb07015.x` | ✔ | **PyC 계면 두께 효과 포함** |
| **B15** | Filipuzzi, L., Naslain, R. (1994). "…: II, Modeling." *J. Am. Ceram. Soc.* **77**(2), 467–480. | `10.1111/j.1151-2916.1994.tb07016.x` | ✔ | 모델링 |
| **B16** | Morscher, G.N., Cawley, J.D. (2002). "Intermediate temperature strength degradation in SiC/SiC composites." *J. Eur. Ceram. Soc.* **22**(14–15), 2777–2788. | ✗ (PII `S0955221902001449`) | ✗ | 중온 취화 |
| **B17** | Naslain, R. et al. (2004). "Oxidation mechanisms and kinetics of SiC-matrix composites and their constituents." *J. Mater. Sci.* | `10.1023/B:JMSC.0000048745.18938.d5` | ✔ | 리뷰 |
| **B18** | Poerschke, D.L. et al. (2017). "Intermediate temperature oxidative strength degradation of a SiC/SiNC composite with a polymer-derived matrix." *J. Am. Ceram. Soc.* | `10.1111/jace.14741` | ✔ | **PIP 계열 기지**의 중온 산화 — PIP 데이터 부재의 최근접 대체 |
| **B19** | Hammood, A. (2020). "A review of some of experimental and numerical studies of self-crack-healing in ceramics." *Int. J. Ceram. Eng. Sci.* | `10.1002/ces2.10071` | ✔ | 자가치유(밀봉) — **OA** |

### 4.4 균열밀도 포화 — `k < 0`의 근거

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B20** | Gowayed, Y., Ojard, G., Santhosh, U., Jefferson, G. (2015). "Modeling of crack density in ceramic matrix composites." *J. Compos. Mater.* | `10.1177/0021998314545188` | ✔ | 포화 균열밀도가 **섬유체적분율 > 얀 crimp 각 > 계면전단강도** 순으로 민감 → `k`가 아키텍처 파라미터에 어떻게 의존해야 하는지 |

### 4.5 ★★★ TRS 실측 — 1건 → 8건, 그리고 **2.34배의 범인이 바뀐다**

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B21** | Broda, M., Pyzalla, A., Reimers, W. (1999). "X-ray Analysis of Residual Stresses in C/SiC Composites." *Appl. Compos. Mater.* **6**, 51–66. | `10.1023/A:1008885319105` | ✔ | ★★★ **열분해 공정 C/SiC — 본 연구와 공정 계열 동일.** 원문: 잔류응력은 *"**매트릭스 수축**과 **열불일치**의 **중첩**"* → **우리 모델은 뒤쪽 항 하나만 세고 있다.** ⚠️ MPa 수치는 미확보 |
| **B22** | Knauf, M.W. et al. (2021). "In situ characterization of residual stress evolution during heat treatment of SiC/SiC CMC using high-energy X-ray diffraction." *J. Am. Ceram. Soc.* **104**, 1424–1435. | `10.1111/jace.17493` | ✔ | ★ **온도를 올려가며 in-situ로 잔류응력이 0으로 가는 지점 추적** → §4.9-2 "유효 무응력 온도"의 유일한 실증. OSTI에 AM 공개 (`osti.gov/pages/biblio/1776625`) |
| **B23** | Chen, X., Cheng, G., Zhang, J. et al. (2020). "Residual stress variation in SiCf/SiC composite during heat treatment and its effects on mechanical behavior." *J. Adv. Ceram.* **9**(5), 567–575. | `10.1007/s40145-020-0395-4` | ✔ | 열처리에 따른 TRS 변화 + 역학거동 변화를 한 편에. **완전 오픈액세스 — 지금 바로 받을 수 있다** |
| **B24** | (제1저자 미검증) (2021). "Measurement of Residual Stress in Silicon Carbide Fibers of Tubular Composites Using Raman Spectroscopy." *Acta Mater.* **217**, 117164. | ✗ | △ | ★ **공정 단계별 분해: 직조 후 −716 MPa → 치밀화 후 −1075 MPa.** "1050 °C에서 한 번에 냉각"이라는 **단일 이벤트 가정 자체가 실제 공정과 다르다**는 실측 증거 |
| **B25** | Mei, H. et al. (2008). "Measurement and calculation of thermal residual stress in fiber reinforced ceramic matrix composites." *Compos. Sci. Technol.* **68**, 3285–3292. | ✗ (PII `S0266353808002972`) | △ | **측정과 계산을 같은 논문에서 대조** → 268 MPa를 비교할 벤치마크 형식. ⚠️ 보유 `refs/[43]` Mei 2005와 **같은 그룹일 가능성** — 독립 출처로 세울 때 주의 |
| **B26** | Bobet, J.L., Lamon, J. (1995). "Thermal residual stresses in ceramic matrix composites — I. Axisymmetrical model and finite element analysis." *Acta Metall. Mater.* **43**, 2241–2253. | ✗ | △ | CMC TRS 시뮬레이션의 정전. 본 연구 방법론의 계보 |
| **B27** | Bobet, J.L., Naslain, R., Guette, A. et al. (1995). "…— II. Experimental results for model materials." *Acta Metall. Mater.* **43**, 2255–2268. | ✗ (PII `0956715194004307`) | △ | 위의 실측편 |
| **B28** | Knauf, M.W. et al. (2020). "Measuring the effects of heat treatment on SiC/SiC CMC using Raman spectroscopy." *J. Am. Ceram. Soc.* **103**, 1293–1303. | `10.1111/jace.16724` | ✔ | B22의 라만 짝 |
| **B29** | Majumdar, S., Kupperman, D., Singh, J. (1988). "Determination of Residual Thermal Stresses in a SiC–Al₂O₃ Composite Using Neutron Diffraction." *J. Am. Ceram. Soc.* **71**. | `10.1111/j.1151-2916.1988.tb07536.x` | △ | 중성자 회절 경로 |
| **B30** | Dassios, K.G., Aggelis, D.G. (2013). "Residual Stress-Related Common Intersection Points in the Mechanical Behavior of Ceramic Matrix Composites Undergoing Cyclic Loading." *Exp. Mech.* | `10.1007/s11340-012-9709-y` | △ (**권·쪽 모순**) | 이력루프 공통교점(CIP)에서 TRS 역산 — 비파괴 대안 경로. ⚠️ **권·쪽 신뢰 불가, DOI만 신뢰** |

**★ §4.9-9의 결론 방향이 바뀐다.**

문헌 증거 3건이 **서로 독립적으로** CTE 오류가 아니라 **무응력 온도 가정 오류**를 지지한다:

1. **B21** — 열분해 C/SiC의 잔류응력 = **매트릭스 수축 + 열불일치의 중첩.** CTE 불일치만 넣은 모델은 **항이 하나 빠진** 모델이다.
2. **B24** — 응력이 **직조(−716) → 치밀화(−1075)** 두 단계로 나뉘어 쌓인다. 단일 냉각 이벤트가 아니다.
3. PIP 공정 모사 문헌 — 응력 피크가 **냉각이 아니라 승온 초기**에 오고 그때 이미 미세균열이 생긴다.
   ⚠️ **단 이것은 Research Square 프리프린트(미심사)라 인용 금지 등급.** 아이디어 확인용으로만.

→ **무응력 온도를 1050 °C보다 낮추는 것(CONFIG_P)은 "숫자 맞추기"가 아니라 문헌이 지지하는 물리적 보정으로 방어 가능하다.**
§4.9-11의 CONFIG_V/CONFIG_P 충돌을 제6장에서 다룰 때 이것이 핵심 논거가 된다.

### 4.6 TRS 완화 → 고온 강도 증가 (§2.6.3 Yan[35] 곡선의 독립 증거)

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B31** | (저자 미검증) (2015). "Experimental study of high-temperature tensile mechanical properties of 3D needled C/C–SiC composites." *Mater. Sci. Eng. A* | ✗ (PII `S0921509315307036`) | ✗ | ★ *"The peak load-carrying capacity at **1400 °C is considerably higher than at room temperature**, attributed to the **relaxation of the tensile thermal residual stresses within the matrix**"* — **비단조 강도-온도 곡선의 독립 실측** |
| **B32** | Li, L. (2020). "Temperature-dependent proportional limit stress of SiC/SiC fiber-reinforced ceramic-matrix composites." *High Temp. Mater. Process.* **39**, 209–. | `10.1515/htmp-2020-0052` | ✔ (끝쪽 △) | *"the **proportional limit stress increases with temperature**, due to … **decreasing of the thermal residual stress**"* ⚠️ **모델 논문이라 1차 실측 아님 — `secondary` 취급 검토** |
| **B33** | (저자 미검증) (2022). "Stress-Induced Microcracking and Fracture Characterization for Ultra-High-Temperature Ceramic Matrix Composites at High Temperatures." *Materials* **15**(20), 7074. | `10.3390/ma15207074` | △ | 고온 응력이완·미세균열로 stress-free 접근. **OA** |

### 4.7 ★★★ 노벨티 C3 — **`refs/[28]`이 바로 그 논문이었다 (2026-08-03 원문 확인)**

> **확인 완료.** `refs/[28] Part 1.pdf`의 PDF 텍스트를 직접 추출하여 서지를 확정하였다.
>
> **Li Jun, Jiao Guiqiong, Wang Bo, Yang Chengpeng, Wang Gang**,
> *Damage characteristics and constitutive modeling of the 2D C/SiC composite:
> **Part I — Experiment and analysis***,
> **Chinese Journal of Aeronautics 27(6) (2014) 1586–1597**,
> DOI **`10.1016/j.cja.2014.10.026`** — Dept. of Engineering Mechanics, **NWPU**,
> 접수 2013-12-25 / 수정 2014-02-08 / 게재확정 2014-03-07 / 온라인 2014-10-22. **오픈액세스.**
>
> **재료: 2D C/SiC, CVI, T300 평직 프리폼 — 본 연구와 완전히 동일하다.**
>
> 즉 **C3의 실험 근거를 처음부터 갖고 있으면서 쓰지 않고 있었다.**

| # | 서지 | DOI | 검증 | 상태 |
|---|---|---|---|---|
| **B34** | 위 Part I | `10.1016/j.cja.2014.10.026` | **✔ 원문 확인** | **보유 = `refs/[28]`** |
| **B35** | 동 저자, "**Part II** — Material model and numerical implementation." *Chin. J. Aeronaut.* **28** (2015). | `10.1016/j.cja.2014.10.027` | **✔ Crossref 확인** | **미보유 — 확보 대상** |

> ★ **주의: Part II는 27권이 아니라 28권이다.** Part I의 참고문헌 [32]가 이를 "ChinJAeronaut **2014**"로만
> 적고 있어(온라인 선공개 시점) 27권으로 오인하기 쉬우나, **Crossref 대조 결과 인쇄본은 28권**이다.
> 두 편을 같은 권으로 적으면 심사에서 바로 걸린다.

Part II는 unilateral / damage deactivation을 **CDM으로 구현**한 편이며, **V3_0의 `HCLO`와 직접 비교 대상**이다.
저자 목록이 Part I과 다르다: **Li J., Jiao G.Q., Wang B., Li L., Yang C.P.**

#### 원문에서 확인한 것 — C3를 뒷받침하는 3건

1. **압축이 손상을 저해한다 (초록):**
   *"Due to the **damage impediment effect of compression stress**, compression specimens show
   **higher mechanical properties and lower damage evolution rates** than tension specimens
   with the same off-axis angle."*
2. **TRS를 이력루프 교점에서 읽는다 (§3.3):**
   *"the hysteresis loops approximately intersect at **O′(σ_r, ε_r)**, and σ_r and ε_r are generally
   considered to be the **thermal residual stress and strain in the as-received material**."*
3. **초기 미세균열은 강성을 바꾸지 않고 TRS만 이완시킨다 (§3.2):**
   *"an array of **non-interacting microcracks** which are able to **relieve the thermal residual
   stress without affecting the elastic modulus** of the material."*
   → ★ **§4.9-9의 2.34배 문제에 직접 걸린다.** 유효 무응력 온도가 제조온도보다 낮은 **기구**가
   여기 있다. 강성으로는 안 보이면서 TRS만 푸는 미세균열이 실재한다는 실험 진술이다.

#### ⚠️ 원문이 **본 연구의 가정 두 개를 수정하라고 요구한다**

**(가) 손상 비활성화는 스위치가 아니라 점진적이며, 속도가 응력상태에 의존한다.**

> *"both on-axis and off-axis specimens exhibit **progressive damage deactivation** behaviors
> in the compression range, but with **different deactivation rates**"*
> *"the damage deactivation rate is **dependent on the compression stress state**"*

현재 `KMACRO31`/`KYARN31`의 `HCLO`는 **부호 전환 시 일정 비율을 회복**시키는 이진 처리이고,
`H_smo` tanh 혼합은 **수치 수렴을 위해** 도입한 것이다(§2.5.3, `M1_FAILURE_ANALYSIS.md`).
**이 논문은 그 매끄러운 전이가 실제로 물리적임을 실험으로 보인다.**
→ `H_smo`의 정당화가 **"수치 편법"에서 "실험이 지지하는 구성식"으로 승격**된다. 서술을 바꿔야 한다.

**(나) ★ 전단 손상도 압축에서 비활성화된다 — 현재 가정과 충돌한다.**

> *"During the compression loading (τ12 > 0), the **shear damage is also gradually deactivated**,
> meanwhile, the hysteresis effect … becomes more evident"*

`README.md`와 §2.5.3은 **"전단 손상은 회복시키지 않는다(닫힌 균열면도 미끄러진다)"**를
CMC 문헌의 통상 가정으로 적고 있다. **본 연구와 동일한 재료(2D CVI C/SiC, T300 평직)에서
그 가정이 실험으로 부정되었다.**

##### 결정 — 전단 회복은 "전단 부호"가 아니라 **"수직 압축"** 이 구동한다

**원문의 기구 설명이 답을 준다.** 논문은 강성 회복의 원인을 전단 자체가 아니라
**수직응력이 닫는 두 가지**로 귀속한다:

> *"In the warp, for example, the **debonded interface will be driven to close by the
> transverse compression stress σ₂** in addition to the **closure of matrix cracks caused by
> the longitudinal compression stress σ₁**. … the **extra closure process of the debonded
> interface** plays an important role in stiffness recovery by **restoring the load-transfer
> capacity of the interface**."*

전단강성은 계면의 하중전달 능력에 의존한다. 따라서 **압축이 계면을 닫으면 전단강성도
회복되는 것이 당연하며, 이는 전단응력의 부호와 무관하다.** 관측된 "전단 손상 비활성화"는
off-axis 시편에서 τ₁₂가 뒤집힐 때 **σ₁·σ₂가 함께 압축으로 간 결과**이지, 전단이 원인이 아니다.

> **따라서 현재 구현을 "전단은 회복 없음"에서 "전단 회복도 **수직변형률 부호**가 구동한다"로
> 바꾸는 것이 물리적으로 옳다.** 전단 부호에 회복을 매다는 설계는 오히려 틀린다.

**제안 — `HCLOS` 슬롯 1개 추가 (비용 작음, 회귀 안전)**

| | |
|---|---|
| 현재 | ε_n < 0 일 때 **수직** 손상만 `d(1−HCLO)` |
| 제안 | ε_n < 0 일 때 **전단** 손상도 `d(1−HCLOS)`, `HCLOS ∈ [0,1]` 독립 |
| 기본값 | `HCLOS = 0` → **현재 거동과 비트 단위로 동일** → T2 회귀 자동 통과 |
| 근거 | `HCLOS > 0`은 refs/[28] §3.3의 계면 폐합 기구 |
| 민감도 | `HCLOS = 0 / 0.5 / HCLO` 3케이스로 열싸이클 비대칭(C3)에 미치는 몫을 정량화 |

**이 설계를 권한다.** 기본값이 0이라 기존 검증이 전혀 흔들리지 않고, 켜는 순간
**실험 근거가 있는 기구**가 들어온다. 손상 이력 `d` 자체는 건드리지 않으므로 단조성도 보존된다.

**단, 지금 당장 구현하지는 않는다** — M6 보정이 끝나기 전에 UMAT을 건드리면 §4.9-0의
진단이 무효가 된다. **카드 슬롯 설계에만 반영해 두고**(`NPROPS` 여유 확인),
보정 종료 후 착수한다.

**(다) 이축 압축이 비활성화를 가속한다 — 열충격에 직결된다.**

> *"the **extra closure process of the debonded interface** plays an important role in stiffness
> recovery by restoring the load-transfer capacity of the interface under **biaxial compression**
> loadings, and therefore it leads to **faster damage deactivation rates**"*

기구는 이렇다 — 이축 압축에서는 종방향 σ₁이 기지 균열을 닫는 것에 더해 **횡방향 σ₂가
박리된 계면까지 닫는다.** 급가열 반사이클은 표면에 **정확히 이축 압축**을 만든다.
→ **C3의 "급랭/급가열 비대칭" 주장에 물리적 기구가 생겼다.** 단축 실험에서 외삽한 것이 아니라
**이축 상태에서 직접 관측된 것**이다.

#### ★ 원문에서 추출한 수치 (2026-08-03)

**(A) Fig. 17(a)의 O′ — 2D C/SiC의 열잔류응력 실측**

논문은 O′의 좌표를 **숫자로 적지 않고 그림에만 표시**한다. PDF에 내장된 JPEG를 직접 꺼내
축 눈금으로 보정해 읽었다 — `data/literature/digitize_ref28_fig17.py`.

| 값 | |
|---|---|
| **ε_r** | **−0.0864 %** |
| **σ_r** | **−132.4 MPa** |

**독립 검산(저장소 규약).** O′가 정말 무응력 원점이면 O′→O 구간은 탄성이므로,
그 할선계수가 표에 인쇄된 초기계수와 같아야 한다.

| | 값 |
|---|---|
| 할선 O′→O | **153.2 GPa** |
| Table 1 `E0` (압축) | 144.87 ± 1.35 GPa |
| **편차** | **5.7 %** (허용 10 %) → **PASS** |

σ=0 격자선도 +0.31 MPa로 읽혀 축 보정이 맞다. **그림이 아니라 인쇄된 표가 판정한다.**

> ★ **§8의 "출처 미상, 인용 금지" 숫자 하나가 여기서 설명된다.**
> `−130.84 ± 34.53 MPa (2D C/SiC)` — 우리 디지타이즈 값 **−132.4 MPa와 1.2 % 차**다.
> 같은 계보(Li 2014 / Camus 1996[NEW1])에서 나온 값일 가능성이 매우 높다.
> **다만 그 논문을 특정한 것은 아니므로 인용 금지는 유지**하고, **우리 값(−132.4)을 쓴다** —
> 출처가 `refs/[28]`로 확실하고 재현 스크립트가 붙어 있다.

> ⚠️ **268 MPa와 직접 비교하면 안 된다.** σ_r은 **복합재 축방향** 값이고,
> §4.5.2의 268 MPa는 **기지 상(phase)의 인장** TRS다. **상이 다르고 부호 규약이 반대**다.
> refs/[15]의 XRD 기지값(+114.7 MPa)과도 마찬가지다. 스크립트가 이 경고를 출력한다.

**(B) Table 1 — `X_c` GUESS에 직접 걸리는 복합재 물성**

전문을 `data/literature/csic_2d_offaxis.csv`에 기록했다 (`role=validation`, **카드 입력 금지**).

| 모드 | θ | E₀ [GPa] | ν | σ₀ [MPa] | σ_u [MPa] | ε_f [%] |
|---|---|---|---|---|---|---|
| 인장 | 0° | 142.06±13.69 | 0.07 | 19.53 | **265.28** | 0.50 |
| 압축 | 0° | 144.87±1.35 | 0.06 | **158.28** | **338.94** | 0.23 |
| 전단 | 0° | 37.34±5.53 (G₀) | — | 12.96 | **139.76** | 1.40 |

여기서 나오는 것 네 가지:

1. **X̄_c / X̄_t = 338.94 / 265.28 = 1.278.** `X_c`는 §4.9-8의 GUESS 14개 중 하나다.
   **보정된 카드가 맞춰야 할 복합재 목표값**이 생겼다.
2. **비례한도 압축/인장 = 158.28 / 19.53 = 8.1배.** 극한강도 비대칭(1.28)보다 **개시 비대칭이
   훨씬 크다.** ★ **C3를 비 하나로 요약한 값**이다 — 압축은 균열 개시를 억제하고 인장은 촉진한다.
3. **S̄ = 139.76 MPa** vs **refs/[35] Yan의 293 K 값 144.1 MPa — 3.0 % 차.**
   서로 다른 그룹, 다른 시험법의 **독립 교차검증**이다.
4. ⚠️ **Ē₀ = 142 GPa인데 refs/[43] Mei는 70 GPa다 — 2배 차이.**
   §4.9-0은 M5의 초기 접선 235.2 GPa를 **Mei의 70 GPa 하나와만** 대조해
   "실재료가 제조 냉각에서 이미 미세균열을 겪었다"고 결론지었다.
   **"2D C/SiC의 실측 탄성계수"는 단일 숫자가 아니다.** 235 vs 142는 1.66배이고
   235 vs 70은 3.36배다. **§4.9-0의 진단 강도를 이 폭에 맞춰 조정해야 한다.**

**실행:** `python3 data/literature/digitize_ref28_fig17.py --check`

#### 부수 수확 — Part I의 참고문헌이 미검증 항목 5개를 확정했다

| 대상 | 확정된 서지 | 효과 |
|---|---|---|
| **S20** Chaboche, Lesne, Maire | *Int. J. Damage Mech.* **4**(1) (1995) **5–22** | 페이지 미검증 → **확정** |
| **B25** Mei, H. | *Compos. Sci. Technol.* **68**(15–16) (2008) **3285–3292** | 권·쪽 △ → **확정** |
| **C9** Marcin, Maire, Carrère, Martin | *Int. J. Damage Mech.* **20** (2011) **939–957** | △ → **확정** |
| **신규** Camus, G., Guillaumat, L., Baste, S. | *Development of damage in a 2D woven C/SiC composite under mechanical loading: I. Mechanical characterization*, *Compos. Sci. Technol.* **56**(12) (1996) **1363–1372** | ★ §8의 **출처 미상 진술** *"fictitious thermal stress-free origin … in the compression domain"*의 **원저자로 유력**. 2D 직조 C/SiC 손상 특성화의 정전 |
| **신규** Dassios, K.G., Aggelis, D.G., Kordatos, E.Z., Matikas, T.E. | *Cyclic loading of a SiC-fiber reinforced ceramic matrix composite reveals damage mechanisms and thermal residual stress state*, *Compos. Part A* **44** (2013) **105–113** | ★ §8의 **`−130.84 ± 34.53 MPa`** 출처 후보. **B30(Exp. Mech.)과는 다른 논문**이다 |
| 신규 | Morscher, G.N., Yun, H.M., DiCarlo, J.A., *JACerS* **90**(10) (2007) 3185–3193 | 2D 직조 면내 균열·극한강도 |
| 신규 | Li, L.B., *Compos. Part B* **53** (2013) 36–45 — cross-ply C/SiC 이력 모델링 | 이력 기반 계면 파라미터 |

**이것이 C3의 성격을 바꾼다.** C3는 "아무도 안 한 것"이 아니라
**"동일 재료에서 실험으로 관측되었고(단조), 본 연구가 반복 열충격으로 확장하는 것"**이 된다.
심사에서 훨씬 안전한 위치이며, **주장의 근거가 우리 모델의 스위치 두 개가 아니라 실험이 된다.**

### 4.8 급랭 대류계수 h — §5.4.3 역산의 정당화

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **B36** | Kim, Y., Lee, W.J., Case, E.D. (1991). "The measurement of the surface heat transfer coefficient for ceramics quenched into a water bath." *Mater. Sci. Eng. A* **145**, L7–. | ✗ (PII `0921509391903079`) | △ | 박막열전대 + 파라미터 추정으로 **h 직접 측정** |
| **B37** | (저자 미검증) "The effect of quenching media on the heat transfer coefficient of polycrystalline alumina." *J. Mater. Sci.* | `10.1007/BF00367565` | ✔ | **매질별 비교** — 물/공기/정지공기를 한 논문에서 |
| **B38** | Hugot, F., Glandus, J.C. (2007). "Thermal shock of alumina by compressed air cooling." *J. Eur. Ceram. Soc.* **27**, 1919–1925. | `10.1016/j.jeurceramsoc.2006.06.012` | ✔ | ★ **본 연구와 동일한 역산 방법** — 수치해석으로 h를 스윕해 최대인장응력이 강도에 닿는 값을 찾음 |
| **B39** | Wang, H., Singh, R.N. (1994). "Thermal shock behaviour of ceramics and ceramic composites." *Int. Mater. Rev.* **39**(6), 228–. | `10.1179/imr.1994.39.6.228` | ✔ | 고전 리뷰 |
| **B40** | (저자 미검증) (2009). "Modification and validation of the thermal shock parameter for CMCs under water quenching condition." *Mater. Des.* **30**, 4552–4556. | `10.1016/j.matdes.2009.04.037` | △ | CMC 전용 수정 |
| **B41** | Meng et al. (2024). "A review of thermal shock behavior of ceramics: Fundamental theory, experimental methods, and outlooks." *Int. J. Appl. Ceram. Technol.* | `10.1111/ijac.14846` | ✔ | 시험법 리뷰 |
| **B42** | ASTM C1525 — *Standard Test Method for Determination of Thermal Shock Resistance for Advanced Ceramics by Water Quenching.* | — | ✔ | 급랭 심각도 표준 |

**확보한 정량값 — §5.4.3에 그대로 쓸 수 있다:**

| 항목 | 값 |
|---|---|
| 물 담금질 h | **5,000 – 100,000 W/(m²·K)** (문헌 간 10배 이상 산포) |
| 압축공기 (알루미나 ΔT_c) | 480 K (원통, 강한 냉각) ~ 650 K (각형, 중간 냉각) |
| **h의 공간 3배 변동 → 인장 열응력 변화** | **최대 약 17 %** |

인용 가능한 비판 문구:
- *"Errors on the HTC may lead to **considerable divergences** between theoretical and actual thermal stresses"*
- *"the HTC obtained by measuring critical temperature differences only stands **roughly for the effective values**"*

→ **h를 가정하지 않고 역산한 §5.4.3의 선택이 옳았음이 문헌으로 확인된다.**
동시에 **17 %라는 정량 한계값**이 Biot 민감도 분석의 근거가 된다.

---

## 5. C등급 — 방법론적 주장의 근거

### 5.1 ★★★ 가장 무방비한 주장 — 스케일 간 메시 객관성 (**현재 인용 0건**)

> 제4장은 RVE에서 **연화까지 포함한** 거시 CDM 카드를 뽑아 거시 요소에 넘긴다.
> 그런데 **연화가 시작되면 RVE 자체가 정의되지 않는다**는 것이 이 분야의 알려진 결과다.
> RVE 크기를 바꾸면 답이 달라진다. **이 인용 없이는 제4장의 핵심 절차가 방어되지 않는다.**

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **C1** | Gitman, I.M., Askes, H., Sluys, L.J. (2007). "Representative volume: Existence and size determination." *Eng. Fract. Mech.* **74**(16), 2518–2534. | `10.1016/j.engfracmech.2006.12.021` | **✔ 서지 확정** | **연화 시 RVE 비존재** — 정면으로 다룬 논문. 탄성·경화에서는 존재하고 크기를 정할 수 있으나 **연화에서는 존재하지 않을 수 있다** |
| **C2** | Nguyen, V.P., Lloberas-Valls, O., Stroeven, M., Sluys, L.J. (2011). "Homogenization-based multiscale crack modelling: From micro-diffusive damage to macro-cracks." *CMAME* **200**(9–12), 1220–1236. | `10.1016/j.cma.2010.10.013` | **✔ 서지 확정** | **RVE 크기에 객관적인 traction–separation** 유도 — 스케일 간 에너지 등가 처방 |
| **C3** | Coenen, E.W.C., Kouznetsova, V.G., Geers, M.G.D. (2012). "Novel boundary conditions for strain localization analyses in microstructural volume elements." *IJNME* **90**(1), 1–21. | `10.1002/nme.3298` | **✔ 서지 확정** | 국소화 시 **주기경계조건이 부적절해지는 문제** + 대안 경계조건 |
| **C4** | Geers, M.G.D., Kouznetsova, V.G., Brekelmans, W.A.M. (2010). "Multi-scale computational homogenization: Trends and challenges." *J. Comput. Appl. Math.* **234**(7), 2175–2182. | `10.1016/j.cam.2009.08.077` | **✔ 서지 확정** | 1차 균질화가 **국부화에서 유효성을 잃는다**는 표준 정리 (README 첫 문장의 근거) |

> ### ✅ 해결 (2026-08-03) — 서지 확정 + 제4장 §4.6.1 신설
>
> **네 편 모두 권·호·쪽·DOI를 복수의 독립 출처에서 대조하여 확정하였다.**
> 이전 판의 *"C1–C4는 전부 서지 미검증, 도메인 지식 기반 후보"* 는 해소되었다.
> `data/literature/refs_candidates.csv`에 기록했고, 제2장 참고문헌에 `[C*]` 표를 두었다.
>
> ⚠️ **내용 등급은 `abstract`이다** — 원문 전문은 아직 확보하지 않았다. 따라서
> 본문 서술은 **각 편의 결론 수준을 넘지 않고 인용부호를 쓰지 않는다.**
>
> ### ★★ 그리고 이 인용을 채우다가 **실제 결함**이 나왔다
>
> [C1]의 경고가 §4.6의 $\bar G_f$ 추출식을 다시 보게 만들었고, 다음이 확인되었다.
>
> $$\bar G_f = \underbrace{l\,g_0}_{\text{탄성 — 길이에 비례}} + \underbrace{l\,\frac{2g_0}{A}}_{\text{소산 — 재료}}$$
>
> **추출은 $l = L_{RVE}$ = 3.5 mm에서, 사용은 $l = l_e$ = 0.68–0.78 mm에서 한다.**
> 그 차이 $g_0(L_{RVE}-l_e)$ = **0.41–0.70 N/mm** 가 잘못된 길이를 달고 스케일을
> 건너며, 이는 저장소에서 출처가 확인된 유일한 파괴에너지($G_{tt}$ = 0.107 N/mm)보다
> **크다.** `homogenize.py`와 `make_macro_thermalshock.py` 어디에도 보정이 없다.
>
> **M6 카드 생성 전에 고쳐야 한다** — 카드가 만들어진 뒤에 고치면 §4.9-8의 보정이
> 통째로 무효가 된다. 제4장 §4.9-16에 기록.
>
> **검증:** `python3 verification/check_gf_scale_transfer.py` (81항목)
>
> **이것이 "인용 0건"의 진짜 의미였다 — 서지의 공백이 아니라 검토되지 않은 절차였다.**

**추가 확보 후보 (§4.6.1 보강용).** 조사 중 발견한 것으로, 위 넷과 같은 계보이며
**연화 RVE의 처방**을 더 직접적으로 다룬다.

| 서지 | 검증 |
|---|---|
| Nguyen, V.P. 외, *On the existence of representative volumes for softening quasi-brittle materials — A failure zone averaging scheme*, *CMAME* (PII `S0045782510001854`) | △ (PII 확인, 권·쪽 미확정) |

### 5.2 ★★ shakedown 문제의 명시적 서술 — 제5장 도입의 핵심 인용

| # | 서지 | 검증 | 무엇을 주는가 |
|---|---|---|---|
| **C5** | Hochard, C., Thollon, Y. (2010). "A generalized damage model for woven ply laminates under static and fatigue loading conditions." *Int. J. Fatigue* | ✗ | **`d = d_static + d_cyc` 분해** 구조를 그대로 제공 — 본 연구의 Δd_cyc 항 도입 근거로 가장 직접적 |
| **C6** | Roe, K.L., Siegmund, T. (2003). "An irreversible cohesive zone model for interface fatigue crack growth simulation." *Eng. Fract. Mech.* | ✗ | **"단조 손상법칙은 이전 최대치를 넘지 않는 반복하중에서 추가 손상을 만들지 않는다"**를 명시적으로 서술 — `r = max(history)` 문제의 교과서적 진술 |
| **C7** | Nguyen, O., Repetto, E.A., Ortiz, M., Radovitzky, R.A. (2001). "A cohesive model of fatigue crack growth." *Int. J. Fract.* | ✗ | 같은 진술 + 명시적 사이클 항 추가라는 처방 |
| **C8** | Van Paepegem, W., Degrieck, J. (2001). "Fatigue damage modelling of fibre-reinforced composite materials: Review." *Appl. Mech. Rev.* | ✗ | 잔여강성/잔여강도 모델 분류 |
| **C9** | Marcin, L., Maire, J.-F., Carrère, N., Martin, E. (2011). "Development of a macroscopic damage model for woven ceramic matrix composites." *Int. J. Damage Mech.* **20**(6), 939–957. | △ | **직조 CMC 거시 손상모델** — 비교 대상 |

> **§1.2.3·§2.5.4의 "shakedown" 서술은 현재 자체 실험(T5의 drift = 0.00e+00)만을 근거로 한다.**
> C6/C7이 이를 **문헌이 이미 아는 문제**로 승격시키고, C5가 **처방의 선례**를 준다.
> T5 결과는 그 문헌적 사실을 **본 연구 재료·구성식에서 수치로 재현한 것**이 되므로 서술이 훨씬 강해진다.

### 5.3 균질화 — C2 기여의 1차 출처

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **C10** | (제1저자 이니셜만 확인) (2021). "Thermal conductivity of a thick 3D textile composite using an RVE model with specialized thermal periodic boundary conditions." *Funct. Compos. Struct.* **3**, 015002. | `10.1088/2631-6331/abd7cd` | ✔ | ★ **직물 RVE 전용 열 주기경계조건.** `RVE_COND.inp`의 방법론 1차 출처 |
| **C11** | (저자 미검증) (2024). "Multi-scale Modeling and Finite Element Analyses of Thermal Conductivity of 3D C/SiC Composites Fabricating by Flexible-Oriented Woven Process." *Chin. J. Mech. Eng.* | `10.1186/s10033-024-01016-6` | ✔ | ★ **3D C/SiC의 k̄ 다중스케일 예측 + 실험 검증.** **완전 오픈액세스** |
| **C12** | Ning, Q.G., Chou, T.-W. (1995). "Closed-form solutions of the in-plane effective thermal conductivities of woven-fabric composites." *Compos. Sci. Technol.* | ✗ | ✗ | k̄ **해석해** — RVE 결과 검산 |
| **C13** | Li, S. (2008). "Boundary conditions for unit cells from periodic microstructures and their implications." *Compos. Sci. Technol.* | ✗ | ✗ | 상용 FE에서 주기 BC를 `*Equation`으로 부과하는 방법 |
| **C14** | Feyel, F., Chaboche, J.-L. (2000). "FE² multiscale approach … SiC/Ti composite." *CMAME* | ✗ | ✗ | FE2 원본 — "왜 오프라인 카드로 대체하는가"의 대조군 |
| **C15** | Lomov, S.V. et al. (2007). "Meso-FE modelling of textile composites: Road map, data flow and algorithms." *Compos. Sci. Technol.* | ✗ | ✗ | TexGen 계열 메소 FE 표준 |
| **C16** | LLorca, J. et al. (2011). "Multiscale modeling of composite materials: a roadmap towards virtual testing." *Adv. Mater.* | ✗ | ✗ | **"virtual testing"** 용어의 표준 출처 — §4.6 제목의 근거 |

### 5.4 시간 균질화 — cycle jump의 이론적 방어

| # | 서지 | DOI | 검증 |
|---|---|---|---|
| **C17** | Fish, J., Yu, Q. (2002). "Computational mechanics of fatigue and life predictions for composite materials and structures." *CMAME* **191**(43), 4827–4849. | `10.1016/S0045-7825(02)00401-2` | ✔ |
| **C18** | Oskay, C., Fish, J. (2004). "Fatigue life prediction using 2-scale temporal asymptotic homogenization." *IJNME* **61**(3), 329–359. | `10.1002/nme.1069` (**추정**) | △ |
| **C19** | Peerlings, R.H.J., Brekelmans, W.A.M., de Borst, R., Geers, M.G.D. (2000). "Gradient-enhanced damage modelling of high-cycle fatigue." *IJNME* **49**(12), 1547–1569. | `10.1002/1097-0207(20001230)49:12<1547::AID-NME16>3.0.CO;2-D` | ✔ |

C19는 **표준 FE 피로손상 정식이 공간 이산화에 극도로 민감**하다고 경고 — 균열대 정규화를 쓰는 본 연구의 선택을 정당화한다.

### 5.5 다축 파손기준 — C4 기여

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **C20** | Kaddour, A.S., Hinton, M.J. (2013). "Maturity of 3D failure criteria … Part B of WWFE-II." *J. Compos. Mater.* | ✗ | ✗ | **3축 응력 상태**에 대한 판정 — 급랭 상태와 직접 대응 |
| **C21** | Hinton, M.J., Kaddour, A.S., Soden, P.D. (2002). WWFE 종합 비교. *Compos. Sci. Technol.* | ✗ | ✗ | 기준 선택의 표준 근거 |
| **C22** | Yang, C. et al. (2021). "Constitutive model and failure criterion for orthotropic ceramic matrix composites under macroscopic plane stress." *J. Am. Ceram. Soc.* | `10.1111/jace.17487` | ✔ | ⚠️ **보유 `refs/[27]`·`[33]` Yang 계열과 같은 그룹일 수 있음 — 중복 확인 필요** |

### 5.6 진짜 온도구배 하 열충격 — C2의 최근접 선행연구

| # | 서지 | DOI | 검증 | 무엇을 주는가 |
|---|---|---|---|---|
| **C23** | (저자 미검증) (2019). "Thermal-mechanical behavior of a SiC/SiC CMC subjected to laser heating." *Compos. Struct.* | ✗ (PII `S0263822318323547`) | ✗ | ★★ **한 면 레이저 가열 + 반대면 냉각 + 일축 인장, 1150 °C까지 in-situ.** 원문: *"applying mechanical loads axially **in the presence of thermal gradients** may induce **interply delamination cracks not observed** after CMC test specimens are loaded under **isothermal** conditions."* → **C2의 정당화 문장 그 자체.** 저자수용본 공개 |
| **C24** | (저자 미검증) (2024). "Representation of Thermomechanical Damage in Fiber-Reinforced Ceramic Composites at High Thermal Gradients." *AIAA J.* | `10.2514/1.J063058` | ✔ | **동일한 모델링 문제의식** — 선행 모델 비교 1순위 |
| **C25** | (저자 미검증) (2024). "Experimental and numerical analysis of CMCs mechanical properties under high-temperature thermal gradient environment." *Ceram. Int.* | ✗ (PII `S0272884223040014`) | ✗ | 구배 환경 실험+해석 |
| **C26** | NASA (2002). "Thermal Gradient Cyclic Behavior of a Thermal/Environmental Barrier Coating System on SiC/SiC CMCs." NASA TM / ASME GT2002-36096. | NTRS 20020066444 | ✔ | 열구배 사이클링 장치·프로파일 공개. **OA** |

---

## 6. 최종 우선순위 — 원문 확보 순서

### 6.1 지금 당장 (오픈액세스 — 유료장벽 없음)

| 순위 | 문헌 | 왜 지금 |
|---|---|---|
| **1** | **A22** Yu et al., *JMRT* **24** (2023) 5541–5551 | 혼자서 GUESS 3개(S_12/S_13/S_23) 제거. **tow-level이라 카드 입력 적법** |
| **2** | **B23** Chen et al., *J. Adv. Ceram.* **9**(5) 567–575 | TRS GAP 2·3을 동시에 채우는 유일한 완전 OA |
| **3** | **B3** Xu et al., *Exp. Mech.* **63**(5) 955–964 (Oxford ORA) | TARGET 1 + 5 동시 — **진짜 온도구배 실험 + FEM 대조** |
| **4** | **B10** Halbig et al., NASA NTRS 20040111387 | `k>0`의 1차 물리 근거, 표 데이터 포함 |
| **5** | **B4** You et al., *J. Inorg. Mater.* **39**(12) 1367–1376 | 2D 중온 열충격 **면내 전단** — `S̄` 직결 |
| **6** | **A8** Ren et al., *Materials* **14**(3) 614 | E = 350 GPa 재검토의 1차 근거 |
| **7** | **A6** Munro, *J. Phys. Chem. Ref. Data* **26**(5) (NIST 무료) | 카드 전체를 온도의존화 |
| **8** | **C11** *Chin. J. Mech. Eng.* (2024) `10.1186/s10033-024-01016-6` | k̄ 균질화의 검증된 선례 |
| **9** | **S6** Chamis NASA TM-83320 (NTRS) | Chamis 인용을 확인 가능한 형태로 |
| **10** | **A14** Olaya Gómez & Garnier (HAL hal-03430963) | **T300 계열** 반경방향 k |

### 6.2 유료 — 기관 계정 필요 (중요도 순)

| 순위 | 문헌 | 왜 |
|---|---|---|
| **1** | **B21** Broda 1999, *Appl. Compos. Mater.* **6** 51–66 | **2.34배의 책임을 CTE에서 무응력 온도로 옮길 근거가 이 한 편에 걸려 있다** |
| **2** | **A1** Xu 2020, *IJACT* **17** | fX/fY/fS 하드픽스를 근거 있는 값으로 |
| **3** | **A7** Santhosh 2021, *JECS* **41**(2) 1151–1162 | PIP 기지 k가 오더 단위로 틀릴 가능성 |
| **4** | **S1–S3, S5** Bažant / Hashin / Tsai–Wu / Schapery | 기법 원전 — 심사 필수 |
| **5** | **B1** Kagawa 1997, *CST* **57**(5) 607–611 | 2D 평직 균열밀도 포화 |
| **6** | **B13** Lamouroux JECS 14 (1994) | ZHANG2013의 −9.8 %를 강도와 잇는 다리 |
| **7** | **S10** Chaboche 1992, *IJDM* **1**(2) 148–171 | M1 비수렴 원인 가설 |
| **8** | **A23** Yu 2022, *Compos. Struct.* **297** 115923 | Y_t |
| **9** | **A24** Li 2024, IMechE Part L | PyC 두께 vs τ |
| **10** | **A29** Pinho 2006, *CST* **66**(13) 2069–2079 | G_tc 가정 방어 논거 |

### 6.3 먼저 **확인**만 하면 되는 것

| 확인 대상 | 후보 | 상태 |
|---|---|---|
| **B34** Li 2014 CJA 27(6):1586–1597 Part I | `refs/[28] Part 1.pdf` | ✅ **확인 완료 (2026-08-03) — 동일 논문.** §4.7 참조. **Part II(`10.1016/j.cja.2014.10.027`)는 미보유 → 확보 대상** |
| **C22** Yang 2021 JACerS `10.1111/jace.17487` | `refs/[27]`, `refs/[33]` | ⬜ 미확인 — 같은 그룹인지 |
| **B25** Mei 2008 CST **68**(15–16):3285–3292 | `refs/[43]` Mei 2005 | 서지는 확정(§4.7). 같은 그룹이면 독립 출처로 세울 수 없음 → ⬜ 미확인 |

### 6.4 검증 완료 기록

| 일시 | 항목 | 방법 | 결과 |
|---|---|---|---|
| 2026-08-03 | **S1** Bažant & Oh 1983 | Crossref REST API | ✅ `10.1007/BF02486267`, vol **16**, p **155–177** — 표와 일치 |
| 2026-08-03 | **B34 / `refs/[28]`** | PDF 텍스트 직접 추출 | ✅ CJA **27**(6) 1586–1597, `10.1016/j.cja.2014.10.026` |
| 2026-08-03 | **S20 / B25 / C9** | `refs/[28]` 참고문헌 목록 | ✅ 권·페이지 확정 (§4.7) |
| 2026-08-03 | **113편 전체** | `verification/verify_bibliography.ps1` (Crossref) | ✅ **§6.5 참조** — MISMATCH 3, FILLED 다수 |

### 6.5 Crossref 일괄 대조 결과 (2026-08-03)

`powershell -ExecutionPolicy Bypass -File verification\verify_bibliography.ps1` 113편 실행 결과.
**아래 값들은 §2–§5 표의 `✗ 미검증` 표시를 대체한다.**

#### (0) 집계

**2회 실행했다.** 1차에서 NOTFOUND 12건이 났는데 그중 `S1`은 같은 날 손으로 확인한 항목이라
**판정이 틀렸음이 즉시 드러났다.** 원인(학술지명 원어 등재)을 고쳐 DOI 직접 조회를 1단계로
넣고 2차를 돌렸다.

| 판정 | 1차 | **2차(최종)** | 뜻 |
|---|---|---|---|
| **OK** | 52 | **57** | DOI·권·쪽이 전부 일치 |
| **FILLED** | 46 | **46** | 비워 두었던 칸이 채워짐 |
| **LOWSCORE** | — | **7** | **DOI로는 확인됨.** 저장된 제목 문자열이 거칠어 점수만 낮음 |
| **MISMATCH** | 3 | **1** | 값이 틀림 |
| **NOTFOUND** | 12 | **2** | DOI를 모르고 검색도 실패 |
| 계 | 113 | 113 | |

> **NOTFOUND 12 → 2.** 나머지 10건은 전부 DOI 직접 조회로 해결되었다.
> **스크립트를 고친 것이 실제 성과의 대부분**이다 — 1차 결과를 그대로 믿었다면
> 있지도 않은 문제 10건을 쫓았을 것이다.

#### (1) MISMATCH — 값이 틀렸다 (1차 3건 → 2차 1건)

| key | 문헌 | Crossref 확정값 | 조치 |
|---|---|---|---|
| **S21** | Jirásek & Bauer, *Comput. Struct.* | `10.1016/j.compstruc.2012.06.006`, **110–111**, 60–78, 2012 | **문서가 옳았다** — 110/111 **합본호**다. CSV를 수정 → 2차 OK |
| **A15** | Olaya Gómez & Garnier, *Int. J. Therm. Sci.* | `10.1016/j.ijthermalsci.2020.106740`, **161**, **106740**, **2021** | ★ 권 159 → **161**, 연도 2021, DOI 확정 → 2차 OK |
| **B35** | Li et al., CJA **Part II** | `10.1016/j.cja.2014.10.027`, **28**, **314–326**, **2015** | ★ 권 27 → **28**, **2015년**, 쪽수 확정 → 2차 OK |
| **B4** | You et al., *J. Inorg. Mater.* **39** | `10.15541/jim20240273`, 39, **시작쪽 1367만 등재**, 2024 | ⚠️ **틀린 게 아니다.** Crossref에 **끝쪽이 등록되어 있지 않다**(중국어권 학술지에 흔함). 스크립트가 이를 `PARTIAL`로 분리하도록 수정 |

> **`PARTIAL` 판정을 새로 두었다.** `1367`이 기대값 `1367-1376`의 **시작쪽과 일치**하면
> 모순이 아니라 **등재 정보가 불완전한 것**이다. 이를 MISMATCH로 두면 올바른 항목이
> 영원히 빨간불로 남는다.

#### (2) FILLED — 46건, 아래가 전부

**C등급 — ★ 방법론 근거가 전부 실존 확인되었다**

§5.1·§5.2는 "도메인 지식 기반 후보, 서지 미검증, 인용 전 확인 필수"로 적어 두었던 것들이다.
**DOI가 나왔다는 것은 그 논문이 실재하고 제목이 일치한다는 뜻이다.**

| key | 문헌 | DOI | 권 | 쪽 | 연도 |
|---|---|---|---|---|---|
| **C1** | Gitman, Askes, Sluys — 연화 시 RVE 비존재 | `10.1016/j.engfracmech.2006.12.021` | 74 | 2518–2534 | 2007 |
| **C2** | Nguyen, Lloberas-Valls, Stroeven, Sluys — CMAME | `10.1016/j.cma.2010.10.013` | 200 | 1220–1236 | 2011 |
| **C3** | Coenen, Kouznetsova, Geers — IJNME | `10.1002/nme.3298` | 90 | 1–21 | 2011 |
| **C4** | Geers, Kouznetsova, Brekelmans — *J. Comput. Appl. Math.* | `10.1016/j.cam.2009.08.077` | 234 | 2175–2182 | 2010 |
| **C5** | **Hochard & Thollon** — *Int. J. Fatigue* | `10.1016/j.ijfatigue.2009.02.016` | 32 | 158–165 | 2010 |
| **C6** | **Roe & Siegmund** — *Eng. Fract. Mech.* | `10.1016/S0013-7944(02)00034-6` | 70 | 209–232 | 2003 |
| **C7** | Nguyen, Repetto, Ortiz, Radovitzky — *Int. J. Fract.* | `10.1023/A:1010839522926` | 110 | 351–369 | 2001 |
| **C9** | Marcin, Maire, Carrère, Martin — IJDM | `10.1177/1056789510385259` | 20 | 939–957 | 2010 |
| **C12** | Ning & Chou — CST | `10.1016/0266-3538(95)00093-3` | 55 | 41–48 | 1995 |
| **C13** | Li, S. — CST, 단위셀 경계조건 | `10.1016/j.compscitech.2007.03.035` | 68 | 1962–1974 | 2008 |
| **C14** | Feyel & Chaboche — FE², CMAME | `10.1016/S0045-7825(99)00224-8` | 183 | 309–330 | 2000 |
| **C15** | Lomov et al. — Meso-FE 로드맵, CST | `10.1016/j.compscitech.2006.10.017` | 67 | 1870–1891 | 2007 |
| **C16** | LLorca et al. — *virtual testing* 로드맵, *Adv. Mater.* | `10.1002/adma.201101683` | 23 | 5130–5147 | 2011 |
| **C19** | Peerlings et al. — IJNME | `10.1002/1097-0207(20001230)49:12<1547::AID-NME16>3.0.CO;2-D` | 49 | 1547–1569 | 2000 |
| **C20** | Kaddour & Hinton — WWFE-II Part B, JCM | `10.1177/0021998313478710` | 47 | 925–966 | 2013 |
| **C22** | Yang et al. — 직교이방 CMC 파손기준, JACerS | `10.1111/jace.17487` | 104 | 1002–1013 | 2020 |
| **C24** | *AIAA J.* — 고열구배 CMC 손상 표현 | `10.2514/1.J063058` | 62 | 2331–2341 | 2024 |

> **C5·C6이 제5장에 가장 중요하다.** shakedown 문제(§5.2)의 프레이밍 인용이
> "존재 여부도 불확실"에서 **DOI가 있는 실재 논문**으로 올라갔다.
> **C1–C4는 제4장 §4.6**(연화까지 균질화해 거시 카드로 넘기는 절차)의 유일한 방어선이다.

**신규 2편 — `refs/[28]` 참고문헌에서 발굴한 것 (§4.7)**

| key | 문헌 | DOI | 권 | 쪽 | 연도 |
|---|---|---|---|---|---|
| **NEW1** | **Camus, Guillaumat, Baste** — *Development of damage in a 2D woven C/SiC composite under mechanical loading: I* | `10.1016/S0266-3538(96)00094-2` | 56 | 1363–1372 | 1996 |
| **NEW2** | **Dassios, Aggelis, Kordatos, Matikas** — *Cyclic loading … reveals damage mechanisms and thermal residual stress state*, *Compos. A* | `10.1016/j.compositesa.2012.06.011` | 44 | 105–113 | 2013 |

**A등급 — 카드 물성**

| key | DOI | 권 | 쪽 | 연도 |
|---|---|---|---|---|
| **A5** Breder — JACerS | `10.1111/j.1151-2916.1995.tb08040.x` | 78 | 2680–2684 | 1995 |
| **A10** Sujith — *Int. Mater. Rev.* | `10.1080/09506608.2020.1784616` | 66 | 426–449 | 2020 |
| **A11** PIP 사이클 vs 강도 — *J. Mater. Sci.* | `10.1007/s10853-010-5182-0` | 46 | 3046–3051 | 2010 |
| **A12** Hu et al. — PIP SiCf/SiC 리뷰 | `10.1016/j.jmrt.2024.11.050` | 33 | 7216–7235 | 2024 |
| **A13** ★ PAN 섬유 **이방성 열전도율** — *Carbon* | `10.1016/j.carbon.2022.06.005` | 197 | 1–9 | 2022 |
| **A14** ★ **반경방향 k (3ω, FT300B)** — IJTS | `10.1016/j.ijthermalsci.2021.107321` | 172 | 107321 | 2022 |
| **A16** Trinquecoste — *Carbon* | `10.1016/0008-6223(96)00052-8` | 34 | 923–929 | 1996 |
| **A18** 다공성 SiC k — JECS | `10.1016/j.jeurceramsoc.2019.11.045` | 40 | 996–1004 | 2020 |
| **A20** Pabst — 다공성 세라믹 탄성, JECS | `10.1016/j.jeurceramsoc.2005.01.041` | 26 | 1085–1097 | 2006 |
| **A21** Phani & Niyogi — *J. Mater. Sci.* | `10.1007/BF01160581` | 22 | 257–263 | 1987 |
| **A24** ★ PyC 두께 vs τ — IMechE Part L | `10.1177/14644207241234395` | 238 | 1805–1823 | 2024 |
| **A28** ★ **온도·산화가 계면 전단응력에 미치는 영향** — *Acta Mater.* | `10.1016/S1359-6454(98)80029-3` | 46 | 2461–2469 | 1998 |

**B등급 — 검증 데이터**

| key | DOI | 권 | 쪽 | 연도 |
|---|---|---|---|---|
| **B1** ★ **Kagawa** — 2D 평직 균열밀도 3사이클 포화, CST | `10.1016/S0266-3538(97)00005-5` | 57 | 607–611 | 1997 |
| **B2** ★ 3D SiC/SiC 100사이클 잔여강도 80 %, MMTA | `10.1007/s11661-006-1053-3` | 37 | 3587–3592 | 2006 |
| **B6** 1300 °C 열충격 2D/2.5D — *Ceram. Int.* | `10.1016/j.ceramint.2024.06.263` | 50 | 34442–34451 | 2024 |
| **B13** ★ **Lamouroux — 산화 vs 인장물성**, JECS | `10.1016/0955-2219(94)90105-8` | 14 | 177–188 | 1994 |
| **B20** Gowayed — 균열밀도 모델, JCM | `10.1177/0021998314545188` | 49 | 2285–2294 | 2014 |
| **B24** 라만 TRS(직조 −716 → 치밀화 −1075 MPa) — *Acta Mater.* | `10.1016/j.actamat.2021.117164` | 217 | 117164 | 2021 |
| **B25** ★ **Mei — TRS 측정·계산 대조**, CST | `10.1016/j.compscitech.2008.08.015` | 68 | 3285–3292 | 2008 |
| **B26** Bobet & Lamon I — *Acta Metall. Mater.* | `10.1016/0956-7151(94)00429-3` | 43 | 2241–2253 | 1995 |
| **B27** Bobet & Lamon II | `10.1016/0956-7151(94)00430-7` | 43 | 2255–2268 | 1995 |
| **B30** ★ Dassios & Aggelis — *Exp. Mech.* | `10.1007/s11340-012-9709-y` | **53** | **1033–1038** | 2013 |
| **B31** ★ 3D needled C/C–SiC 1400 °C, *MSEA* | `10.1016/j.msea.2015.12.010` | 654 | 271–277 | 2016 |
| **B32** Li L. — PLS vs 온도, HTMP | `10.1515/htmp-2020-0052` | 39 | 209–218 | 2020 |
| **B36** Kim, Lee, Case — 급랭 h 직접 측정, *MSEA* | `10.1016/0921-5093(91)90307-9` | 145 | L7–L11 | 1991 |
| **B39** Wang & Singh — *Int. Mater. Rev.* | `10.1179/imr.1994.39.6.228` | 39 | 228–244 | 1994 |
| **B41** Meng — 열충격 리뷰, IJACT | `10.1111/ijac.14846` | 21 | 3789–3811 | 2024 |

> **B30의 권·쪽 모순이 해소되었다** — §4.5에 "vol 56 vs 53 충돌, DOI만 신뢰"로 적어 두었으나
> **53권 1033–1038이 맞다.** 검색 요약의 "vol 56"이 틀렸다.

#### (3) ★ NOTFOUND 12건은 **스크립트의 한계였다** — 논문이 없다는 뜻이 아니다

`S1`(Bažant & Oh)이 NOTFOUND로 나왔는데, **이 항목은 같은 날 손으로 Crossref에 조회해
`10.1007/BF02486267`, vol 16, p 155–177을 이미 확인한 것이다**(§6.4). 즉 판정이 틀렸다.

**원인:** 1차 스크립트는 `query.bibliographic` + `query.container-title` 검색만 했다.
Bažant & Oh 1983은 Crossref에 학술지명이 **원어("Matériaux et Constructions")** 로 등재되어
있어 `Materials and Structures`로 거른 질의가 0건을 냈다. 제목이 길거나 표기가 흔들리는
항목도 같은 이유로 0건이 된다.

**수정(2026-08-03):** `verify_bibliography.ps1`을 3단계로 바꾸었다.

1. **`expected_doi`가 있으면 DOI로 직접 조회** (`/works/<doi>`) — 가장 확실하고 검색을 타지 않음
2. 없으면 제목 + 학술지 검색
3. 그래도 없으면 **학술지명을 빼고 제목만으로** 재검색

결과 CSV에 **`method` 열**이 추가된다 (`doi` / `title+journal` / `title-only` / `doi-fail`).
`doi-fail`은 **그 DOI 자체가 틀렸을 수 있다는 신호**이므로 눈으로 확인한다.

**2차 실행 결과 — 예측대로 10건이 해결되었다.** `S1`, `A17`은 `OK`,
`A2`·`A3`·`A6`·`A30`·`B18`·`B29`·`C11`은 `LOWSCORE`(=DOI로 확인, 제목 문자열만 거침),
`B4`는 `PARTIAL`이 되었다.

**LOWSCORE 7건은 문제가 아니다.** 전부 `method='doi'`이고, 권·쪽이 문서 기대값과 일치한다.

| key | DOI로 확인된 값 | 비고 |
|---|---|---|
| **A2** Cockeram 2005 | **88**, 1892–1899, 2005 | 기대값과 일치 |
| **A3** Cockeram 2004 | **87**, 1093–1101, 2004 | 기대값과 일치 |
| **A6** Munro 1997 | **26**, 1195–1203, 1997 | 기대값과 일치 |
| **A30** Dalli 2020 | **106**, 102487, 2020 | 기대값과 일치 |
| **B18** Poerschke 2017 | **100**, **1606–1617**, 2017 | ★ 신규 확보 |
| **B29** Majumdar 1988 | **71**, **858–863**, 1988 | ★ 신규 확보 |
| **C11** *Chin. J. Mech. Eng.* 2024 | **37**, 2024 | ★ 신규 확보 |

점수가 0으로 나온 것은 CSV의 제목에서 그리스문자·아래첨자·슬래시를 지워 적었기 때문이다
(`α-SiC` → `alpha-SiC`, `SiC/SiC` → `SiC SiC`). **DOI로 찾은 행은 그 DOI가 곧 신원**이므로
제목 점수로 등급을 낮추지 않도록 스크립트를 고쳤다 — 대신 주석으로 남긴다.

**끝까지 남은 2건 — DOI를 모르고 검색도 실패**

| key | 문헌 | 알아낸 것 | 남은 일 |
|---|---|---|---|
| **B16** | Morscher & Cawley, *J. Eur. Ceram. Soc.* **22**(14–15) (2002) | 권 22 확인. **쪽수 표기가 2777–2787과 2777–2788로 출처마다 다름** → 비워 둠. PII `S0955221902001449`. **NASA NTRS 20020028707에 무료 공개** | 원문 표지에서 쪽수·DOI 확정 |
| **C23** | *Thermal-mechanical behavior of a SiC/SiC CMC subjected to laser heating*, *Compos. Struct.* | PII `S0263822318323547` | DOI 확정 |

**재실행 명령:**

```powershell
powershell -ExecutionPolicy Bypass -File verification\verify_bibliography.ps1 -Mail <이메일>
```

#### (4) 이 대조가 확인하는 것과 확인하지 못하는 것

| 확인됨 | 확인 안 됨 |
|---|---|
| 그 서지의 논문이 **실재한다** | 본문의 **수치** |
| **제목**이 일치한다 | **식 번호** |
| DOI · 권 · 호 · 쪽 · 연도 | 인용하려는 **문장** |

따라서 위 항목들은 여전히 `data/literature/README.md`의 **`abstract` 등급**이다.
`fulltext`로 올리려면 원문을 열어야 한다. 예외는 `refs/`에 원문이 있는 것들과
**`refs/[28]`(§4.7)** 뿐이다.

---

> Crossref 조회는 인증도 API 키도 필요 없다. **PowerShell에서는 `curl`이 `Invoke-WebRequest`의
> 별칭**이므로 `-s`나 리눅스식 `\` 줄바꿈이 통하지 않는다. 다음을 쓴다:
> ```powershell
> $r = Invoke-RestMethod "https://api.crossref.org/works?query.bibliographic=<제목>&rows=1"
> $d = $r.message.items[0]; "$($d.DOI) vol=$($d.volume) p=$($d.page) $($d.title[0])"
> ```
> ※ Crossref는 DOI를 소문자로 반환한다. DOI는 대소문자를 구분하지 않으므로
> 논문에는 출판사 표기(`10.1007/BF02486267`)를 쓴다.

---

## 7. 이 조사가 문서에 요구하는 변경

> ### 진행 상황 — **21개 전부 완료 (2026-08-03)**
>
> | 상태 | 개수 | 항목 |
> |---|---|---|
> | ✅ **완료** | **21** | **전부 (1–21)** |
> | ⏸ **대기** | **0** | — |
>
> **원문 전문 없이 21개가 전부 닫혔다.** 처리 경로는 셋이었다 —
> ① `refs/[28]` 전문(이미 보유), ② **서지·초록 수준 확인으로 충분한 것**(14, 12),
> ③ **직접 계산으로 대체 가능한 것**(10 — Maxwell–Eucken·Landauer는 폐형식이라 구현해서 확인).
>
> **8은 "확보"가 아니라 "부재 확정"으로 닫혔다** — CMC 횡방향 압축 파괴에너지는 존재하지 않으며,
> 압축이 압괴로 파손하는 이상 그 양 자체가 잘 정의되지 않는다. **조건부 항목이 아니라 결론이다.**
>
> ⚠️ **쓰지 않은 것도 기록한다.** 12의 *"h 공간 3배 변동 → 열응력 17 %"* 는 **원문 미확보라
> 인용하지 않았다.** 초록에서 확인된 것(역산 방법, 임계 온도차 480–650 K)만 썼다.
>
> **★ 부수 수확 — 반영 과정에서 실제 결함 3건이 나왔다.**
> ① §4.9-8의 GUESS 목록이 **15개로 적혀 있었는데 선언된 개수는 14개**였다
> ($S_{13}$이 잘못 포함됨). ② 제1·3장의 자동 검증 총량이 928로 적혀 있었으나
> 실제는 936이다. ③ **가장 큰 것 — $\bar G_f$가 RVE 크기(3.5 mm)를 달고 거시
> ($l_e$ = 0.68–0.78 mm)로 넘어간다.** 초과분 0.41–0.70 N/mm는 저장소에서 출처가
> 확인된 유일한 파괴에너지보다 크다. **M6 카드 생성 전에 고쳐야 한다**(§4.9-16).
>
> **검증:** 28개 전수 통과(`check_gf_scale_transfer.py` 신설 포함).

| # | 변경 대상 | 내용 | 근거 |
|---|---|---|---|
| **1** | **제2장 §2.4** | ✅ **완료(2026-08-03).** §2.4.4를 세 파라미터 표로 재작성 — `R`=Kingery 1955[S11], `R''''`=Hasselman **1963**[S12], `R_st`=Hasselman 1969[S13]. 귀속 주의 박스 추가 | S11–S13 |
| **2** | **제2장 §2.6.1** | ✅ **완료.** §2.6.1에 "원전이 이미 3차원 — 확장이 아니다" 박스. 필요한 원전은 판정식→손상변수→연화강성 **매핑**(Matzenmiller 1995[S5])임을 명시. 제1장 C4도 "D-criterion만 확장"으로 명확화 | S2, S5 |
| **3** | **제2장 §2.6.1** | ✅ **완료.** §2.6.1 강도비 정규화에 Liu & Tsai 1998[S4] 인용 | S4 |
| **4** | **제3·4장** | ✅ **완료.** 제3장 §3.3에 인용 형태 주의 박스(NASA TM-83320 주 + SAMPE 병기, NTRS 무료). 제4장 §4.9-11도 [S6]/[S7]로 표기 | S6 |
| **5** | **`docs/NOVELTY.md` §A.1** | ✅ **완료.** NOVELTY §A.1에 정정 절 추가 — "2D vs 3D" → **밀봉/비밀봉 온도역**. MEI2005[43] 아르곤 98.90 %를 결정적 증거로. 제2장 §2.5.4·§2.8.4, 제1장 §1.4.1, 제5장 §5.2.2 전부 동기화. `k(T_max)` 미보정은 한계로 기록 | §4.2 |
| **6** | **제4장 §4.9-8** | ✅ **완료.** §4.9-8을 **세 부류**로 재분류 — (1) 수치 정규화 4개(σ_y0, H_iso, d_max, η — 측정 대상 아님), (2) tow-level 측정법 부재 5개, (3) 구성식 형상 5개. **초안 오류도 정정**: S_13은 GUESS가 아닌데 목록에 있어 15개로 적혀 있었다(선언값 14) | §3.7 |
| **7** | **제4장 §4.9-8** | ✅ **완료.** 위 (2)에 "미니콤포지트 시험법 자체가 최근 확립" 명시 — "추정값"이 아니라 **측정 가능한 스케일이 카드가 요구하는 스케일과 다름**으로 재서술 | §3.5 |
| **8** | **제4장 §4.9-6a** | ✅ **완료(2026-08-03).** **승격 불가로 확정.** CMC 횡방향 **압축** 파괴에너지는 재탐색에서도 부재 — 횡방향 **인장** $G_{Ic}$와 미니콤포지트 인장 시험법은 확립되어 있으나 압축 대응물이 없다. 물리적으로도 자연스럽다(압축은 균열 열림이 아니라 **압괴**로 파손 → 모드 I 파괴에너지가 잘 정의되지 않음). (a) 주 케이스 유지 + (b) 민감도 + 한계 명시. **⚠️ 이제 정량 결과가 붙는다 — $G_{tc}$=0은 $A$를 고정 2.0으로 만들고, 냉각이 구동하는 것이 바로 그 횡방향 모드다** | §3.6 |
| **9** | **제4장 §4.9-9/11** | ✅ **완료.** §4.9-9에 배분표 추가 — CTE만으로는 1.34배가 남고 T_sf만으로는 1.69배가 남는다. 무게를 **무응력 온도(주 변수)** 로 옮기고 CTE는 필요 이동폭을 줄이는 역할로 재배치. CONFIG_P의 정당성은 **두 관문을 동시에 통과하는 유일한 조합**이라는 사실에 둔다 | §4.5 |
| **10** | **제4장 §4.9-3** | ✅ **완료(2026-08-03).** Smith 등 *J. Mater. Res.* **28**(17) 2260–2272 (`10.1557/jmr.2013.179`) + Wang 등 *IJHMT* **49** 3075–3083 확보. **닫힌 공극→Maxwell–Eucken, 열린 공극→Landauer**($p<0.65$). CVI/PIP는 **열린 공극**(그래서 산소가 들어가고, 그것이 §2.5.4의 $k$ 부호 기구다) → **Landauer**. **단 정직한 결과는 "차이 없음"** — 필요 공극률 5.72 / 5.89 / 4.48 %로 폭 1.31배, 전부 refs/[22]의 24 %보다 훨씬 낮다. `conductivity_bounds.py`에 두 모델 구현 + 검증 | A17 |
| **11** | **제5장 §5.9.2** | ✅ **완료.** §5.9.2-6에 신설 — 사이클별 잔여물성 문헌([2][3][28][43])이 **전부 CVI**이고 기준 재료는 PIP. 산화가 지배 기구라면 기공률·균열망 연결성에서 갈릴 가능성. 처리 방침 3항(계수는 CVI 보정임을 명시 / 주 결론을 상대 비교로 / 절대값은 CVI 한정) | §4.1 |
| **12** | **제5장 §5.4.3** | ✅ **완료(2026-08-03).** Hugot & Glandus *JECS* **27**(4) 1919–1925 확인 — **본 절과 같은 구조의 역산**(수치로 $h$를 훑어 최대 인장응력이 강도에 닿는 값을 찾음), 임계 온도차 480–650 K. §5.4.1에 **"$h$는 급랭 시험에서 직접 측정되는 양이 아니므로 문헌 값을 빌리는 쪽이 오히려 근거가 약하다"**를 명시. **⚠️ "3배 변동 → 17 %"는 원문 미확보라 쓰지 않았다** — 대신 $Bi$ 사다리가 $h$를 조작 변수로 전환한다는 서술로 대체 | B36–B38 |
| **13** | **제1·2장** | ✅ **완료.** 제2장 §2.8.3과 제1장 §1.4의 C3을 재서술 — Li[28] Table 1의 **비례한도 8.1배 / 극한강도 1.28배**를 인용해 "실험 근거 있음, 본 연구가 반복으로 확장"으로 전환 | B34 |
| **14** | **제4장 §4.6** | ✅ **완료(2026-08-03).** C1–C4 **서지 확정**(권·호·쪽·DOI) 후 **§4.6.1 신설** — [C1] 연화 시 RVE 비존재 / [C4] 1차 균질화의 한계 / [C3] 국부화 시 주기BC 부적절 / [C2] 크기 객관적 traction–separation. 방어는 "넘기는 것은 곡선이 아니라 에너지". **그 과정에서 $\bar G_f$가 RVE 크기를 달고 넘어가는 결함 발견 → §4.9-16** | C1–C4 |
| **15** | **제5장 §5.2** | ✅ **완료.** §2.5.4를 "본 연구가 발견한 문제"에서 **"이력변수형 손상법칙 전부의 수학적 성질"** 로 승격. T5(drift 0.00e+00)는 그 사실의 **수치 재현**으로 재배치. 제1장 §1.2.3도 동기화. **⚠️ 2026-08-06 갱신 — C5–C7 귀속을 좁혔다(원문은 여전히 미확보).** 서지는 확정(권·쪽 기재)했고, 원문 없이 확인 가능한 것을 확인한 결과 **초안의 귀속이 과했다**: Roe & Siegmund에게 귀속했던 "이전 최대치 이하에서 손상 부재의 명시적 서술"은 **확인되지 않으며**, 확인된 것은 **처방** 쪽이다(손상변수 $D$로 단조 응집강도를 사이클마다 열화 + 문턱/내구한도). Hochard의 $d_s+d_f$ **가법 분해도 미확인**(정적·피로를 하나의 비선형 누적 모델로 다룬다는 것까지만 확인). Nguyen은 미확인. → **진단은 인용 불필요**(구성식의 대수), **처방만 인용**하며 본 연구 $\Delta d_{cyc}$의 문턱+곱셈 결합 구조가 그 선례와 일치함을 명시. 판정기 `refs_audit.py --check` §D4 | C5–C7 |
| **16** | **`README.md` · 제2장 §2.5.3** | ✅ **완료.** README.md와 제2장 §2.5.3·제5장 §5.2.3에 경고 추가 — 전단 미회복은 통상 가정이 아니라 **[28]을 알고서 택한 보수 가정**. 회복 구동은 전단 부호가 아니라 **수직 압축**(계면 폐합)임을 명시하고 `HCLOS` 슬롯 설계를 기록(기본값 0 → T2 무영향) | §4.7-(나) |
| **17** | **제2장 §2.5.3 · `M1_FAILURE_ANALYSIS.md`** | ✅ **완료.** §2.5.3에 `H_smo` 승격 박스 — [28]의 *"progressive damage deactivation … different deactivation rates"* 로 **"수치 편법"에서 "실험이 요구하는 정칙화"** 로. 응력상태 의존성 미반영은 §2.9-9에 1차 근사로 기록 | §4.7-(가) |
| **18** | **제1·2장 C3 서술** | ✅ **완료.** 제2장 §2.8.3·제1장 §1.4·제5장 §5.2.3에 **이축 압축 기구** 명시 — 횡방향 압축이 박리 계면까지 닫아 비활성화가 가속되며, 급가열 반사이클 표면이 정확히 그 상태. 단축 외삽이 아님 | §4.7-(다) |
| **19** | **제4장 §4.9-9** | ✅ **완료.** §4.9-9에 *"non-interacting microcracks … relieve the TRS without affecting the elastic modulus"* 인용 — 유효 무응력 온도 저하의 **기구**가 됨. "강성으로는 안 보이는데 TRS만 낮은 상태"가 실재. CONFIG_P의 T_sf=800 °C가 임의 보정값이 아님 | §4.7-3 |
| **20** | **제4장 §4.9-0** | ✅ **완료(2026-08-03).** "실측 2D C/SiC는 70 GPa"를 **≈140 / 70–98 두 무리**로 정정. 초기 접선끼리 비교하면 **3.36배 → 1.66배**. M6이 knob를 움직일 폭이 **절반**이 된다 | §4.7-(B)-4 |
| **21** | **`docs/REFS_36_45_ASSESSMENT.md`** | ✅ **완료.** Mei Table I의 70 GPa 옆에 단독 사용 금지 경고 추가 (강도 248 MPa는 refs/[28]의 265.28과 6.9 % 차로 정합하므로 유효) | 동상 |

---

## 8. 정직한 고지

- **이 조사에서 출판사 페이지를 한 건도 직접 열지 못했다.** WebFetch·curl이 전 호스트 403
  (조직 egress 정책). 검증은 WebSearch 결과 요약에만 의존했다.
- **DOI·페이지·저자명을 지어내지 않았다.** 확인 못 한 것은 빈칸 또는 PII로 남겼고
  **✗ 미검증**으로 표시했다.
- **본문 식 번호는 어느 항목도 확인하지 못했다.** 식 번호를 달아 인용할 항목
  (특히 S1의 스냅백 조건, S2의 3D 형식)은 **원문 PDF에서 1회 대조**해야 한다.
- **DOI를 추정으로 표시한 2건**(A32 Maimí Part II, C18 Oskay & Fish)은 제출 전 확인 필수.
- **쓰면 안 되는 숫자 2건:**
  1. `G_tc/G_tt ≈ 14.2`를 준 4개 조 값 — 출처 논문 특정 실패 (§3.6)
  2. `−130.84 ± 34.53 MPa (2D C/SiC)` — 출처 특정 실패 + **복합재 평균 압축응력**이라
     본 연구의 **기지 인장 268 MPa와 물리량도 부호도 다르다**
     → **유력 후보를 찾았다**(§4.7): Dassios, Aggelis, Kordatos, Matikas, *Compos. Part A*
     **44** (2013) 105–113. **확인 전까지는 여전히 인용 금지.**
- **§4.7의 `refs/[28]` 관련 서술만은 예외적으로 `fulltext` 등급이다** — PDF 원문에서
  직접 추출·확인하였다. 나머지는 여전히 `abstract` 이하다.
- **인용 금지 등급 1건:** PIP 공정 모사 Research Square 프리프린트 (`rs-9997234/v1`) — 미심사.
  공정이 정확히 일치해 아이디어는 값지지만 `data/literature/README.md` 규칙상 인용 불가.
- `data/literature/README.md`의 신뢰도 규칙에 따라, **위 문헌은 원문 확보 전까지 전부
  `abstract` 이하 등급**이며 본문 인용 대상이 아니다.
