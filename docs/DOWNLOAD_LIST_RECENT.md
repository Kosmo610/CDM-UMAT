# 최신 논문 목록 — 우선순위순 (조사일 2026-08-04)

> **범위.** 2024–2026년 논문을 중심으로 찾되, **주제가 정확히 겹치면 연도와 무관하게
> 포함**했습니다(1번이 그 경우입니다 — 2007년이지만 이 논문 주제의 정중앙입니다).
>
> **표기 규칙.**
> - **DOI ✔** = 검색으로 확인된 것.
> - **PII** = Elsevier 논문 고유번호. **DOI는 확인 못 했습니다.**
>   `https://www.sciencedirect.com/science/article/pii/<PII>` 로 바로 열립니다.
>   **DOI를 추측해서 적지 않았습니다.**
> - **OA** = 오픈액세스(무료 공개).
> - 저자 이니셜은 검색 결과에 나온 형태 그대로입니다. **인용 전 원문 첫 페이지에서
>   확인하세요.**

---

## 등급 뜻

| 등급 | 뜻 |
|---|---|
| **S** | 본 연구 **주장의 근거**가 되는 것. 없으면 논지가 약해짐 |
| **A** | **카드 숫자**나 모델 파라미터를 채워 줄 것 |
| **B** | **검증 데이터** (실험값과 대조용) |
| **C** | **방법론 방어**용 (심사 대비) |

---

# ★★★ 1군 — 산화가 손상 누적을 지배한다는 주장의 직접 근거 (4편)

본 연구의 사이클 손상 지수 $k$의 **부호가 산화 여부로 갈린다**는 것이 핵심 주장인데,
현재 그 근거가 **보유 데이터 3건의 정황 일치**뿐입니다. 아래가 그것을 문헌 근거로
바꿔 줍니다.

### 1. **[S]** Modeling the effects of thermal and mechanical load cycling on a C/SiC composite in **oxygen/argon mixtures**
- **저자**: H. Mei, L. F. Cheng, L. T. Zhang, Y. D. Xu
- **출처**: *Carbon* **45** (2007) 2195–2204
- **PII**: `S0008622307003119` — DOI 미확인
- **왜 1번인가**: **제목이 이 논문의 주장 그 자체입니다.** C/SiC를 **산소/아르곤 혼합
  분위기**에서 열·기계 반복 하중에 놓고 **모델링**한 논문입니다. 저희는
  `refs/[43]`(아르곤 98.90 % 유지)과 `refs/[03]`(공기 중 급락)을 나란히 놓고
  "산소가 있어야 손상이 쌓인다"고 주장하는데, **이 논문은 그 두 조건을 한 논문 안에서
  연속적으로 다룹니다.** 2007년이지만 **연도와 무관하게 1순위**입니다.
- ⚠️ 저자가 `refs/[43]`(Mei)·`refs/[28]`의 시편 제작 출처와 **같은 그룹(NWPU)**입니다.

### 2. **[S/A]** Predictive Constitutive Modelling of **Oxidation-Induced Degradation** in **2.5D Woven C/SiC** Composites
- **저자**: Tao Wu, Yukang Wang, Wenxuan Qi, Xingling Luo, Peng Luo, Xiguang Gao, Yingdong Song (난징항공항천대 NUAA)
- **출처**: *Materials* **19**(2) (2026) 307 — **OA(무료)**
- **DOI ✔**: `10.3390/ma19020307`
- **왜**: **2026년 논문이고, 700 / 900 / 1100 °C에서 산화 시험 후 구성식을 세웁니다.**
  저희가 $k>0$의 지배 영역이라 주장하는 **600–1000 °C 구간을 정확히 관통**합니다.
  게다가 **구성식**이라 저희 $\Delta d_{cyc}$ 항과 직접 비교됩니다.
  **무료라 지금 바로 열립니다.**

### 3. **[B]** Properties evolution and damage mechanism of **SiC/SiC** composites after **thermal shock at 1300 °C**
- **저자**: 미확인 (검색으로 확정 못 함)
- **출처**: *Ceramics International* **50**(18, Part B) (2024)
- **PII**: `S0272884224026762` — DOI 미확인
- **왜**: **2D와 2.5D를 0 / 500 / 1000 사이클**로 비교합니다. 저희 `refs/[2]`(YIN2002)가
  1300 °C에서 포화($k<0$)를 보였는데, **같은 온도의 최신 독립 데이터**입니다.
  게다가 **밀도 감소·공극률 증가**를 함께 보고하므로 $k$ 부호의 기구 논증에 씁니다.

### 4. **[S]** Multiphysics model of **thermomechanical oxidative degradation** in SiC/SiC CMC microstructures
- **저자**: Mohamed H. Hamza, Jacob J. Schichtel (애리조나주립대)
- **출처**: *J. Eur. Ceram. Soc.* **45**(10) (2025) 117335
- **PII**: `S0955221925001554` — DOI 미확인
- **왜**: **열-역학-산화를 연성한 손상 정식을 확률적 RVE에 구현**합니다. 저희가
  "산화를 사이클 항으로 현상론적으로 표현한다"고 쓸 때, **그 현상론이 무엇을
  단순화한 것인지**를 이 논문으로 설명할 수 있습니다. 2025년.

---

# ★★ 2군 — 반복 열충격 실험 데이터 (3편)

$C(T)$, $R_{th}$, $n$, $k$ 보정에 쓸 곡선을 **보유 2건에서 5건으로** 늘립니다.

### 5. **[B]** Thermal Shock Damage and Failure Mechanism of **2D Laminated SiC/SiC** with BSAS Environmental Barrier Coating
- **저자**: Cao 외 (제1저자만 확인)
- **출처**: *Advanced Engineering Materials* (2025)
- **DOI ✔**: `10.1002/adem.202401878`
- **왜**: **상온↔1200 °C를 600 사이클**. 저희 매트릭스가 다루는 사이클 수(100회)를
  훨씬 넘는 장기 데이터라 **포화 여부를 판정**할 수 있습니다.
  ⚠️ 코팅(EBC)이 있는 시편이라 **코팅 없는 저희 재료와 직접 비교는 안 됩니다** —
  경향 비교용으로만 쓰세요.

### 6. **[B]** Strain response of C/SiC composite to **thermal and mechanical load cycling in oxidising atmosphere**
- **저자**: H. Mei, L. F. Cheng
- **출처**: *Advances in Applied Ceramics* (2008)
- **DOI ✔**: `10.1179/174367608X263296`
- **왜**: 1번의 짝이 되는 **실험** 논문입니다. 1번이 모델, 이쪽이 데이터.

### 7. **[B]** Thermal Cycling Damage Mechanisms of C/SiC Composites in **Displacement Constraint** and Oxidizing Atmosphere
- **저자**: H. Mei 외
- **출처**: *J. Am. Ceram. Soc.* (2006)
- **DOI ✔**: `10.1111/j.1551-2916.2006.01012.x`
- **왜**: **구속 조건 하** 열싸이클 — 실제 부품이 겪는 상태에 가깝습니다.
  같은 그룹의 3부작(1·6·7번)을 함께 보면 **분위기·구속·하중 세 변수의 영향**이
  분리됩니다.

---

# ★★ 3군 — 제4장 §4.6.1의 방어 (2편)

**연화를 포함한 카드를 RVE에서 뽑는 절차**가 이 논문의 가장 약한 고리인데, 현재
근거가 2007–2012년 논문 4편뿐입니다. 최신 리뷰가 있으면 훨씬 강해집니다.

### 8. **[C]** **State of art in regularization methods** for numerical analysis of structures with **softening**
- **저자**: Jiahui Shen, Mário Rui Tiago Arruda, Alfonso Pagani
- **출처**: *Int. J. Damage Mechanics* (2026)
- **DOI ✔**: `10.1177/10567895251329946`
- **왜**: **연화 해석의 정규화 기법 최신 리뷰**입니다. §2.5.2(균열대)와 §4.6.1이
  "왜 이 방법을 골랐는가"를 답할 때, **2026년 리뷰를 인용**하는 것과 1983년 원전만
  인용하는 것은 심사에서 무게가 다릅니다.

### 9. **[C]** **Smooth Lagrangian crack band model** with softening stress–strain relation and crack width prediction
- **저자**: 미확인
- **출처**: *Int. J. Non-Linear Mechanics* (2026)
- **PII**: `S0020746226000259` — DOI 미확인
- **왜**: 균열대 기법의 **최신 개량형**. 저희가 쓰는 고전 균열대의 한계를 서술할 때
  "이런 개량이 있으나 본 연구 범위 밖"으로 처리하면 **한계 서술이 정직해집니다.**

---

# ★ 4군 — 손상 기구의 직접 관찰 (7편)

CT·X선으로 **손상이 실제로 어떻게 생기는지 본** 최신 논문들입니다. 저희 모델이
가정하는 기구(기지 균열 → 계면 박리 → 섬유 파단)가 **맞는지 확인**하는 데 씁니다.

### 10. **[B]** High-temperature tensile damage evolution of **plain-woven SiCf/SiC** at 1200 °C in an **INERT atmosphere**: 4D in-situ X-ray CT
- **출처**: *Composite Structures* (2026) — **PII** `S0263823126000807`, DOI 미확인
- **왜**: ★ **비활성 분위기**입니다. 1군의 산소/아르곤 논증에 **직접 관찰 근거**를
  더합니다. 게다가 **평직**이라 아키텍처도 같습니다.

### 11. **[B]** Internal damage evolution of **C/SiC** composites in **air at 1650 °C** studied by in-situ synchrotron X-ray imaging
- **출처**: *Compos. Part A* (2024) — **PII** `S1359836824006905`, DOI 미확인
- **왜**: 10번의 대조군(공기 중). 두 편을 함께 보면 산화의 영향이 **영상으로** 보입니다.

### 12. **[B]** 3D visualization and quantitative characterizations of damage evolution in **C/SiC**: Synchrotron X-ray CT and in-situ loading at **800 °C**
- **저자**: Long Wang, Chuantao Hou, Daxu Zhang, Ruisi Xing, Fang Ren, Junbai Song, Weiyu Guo, Yueping Zhang, Chao Chen
- **출처**: *J. Composite Materials* (2026)
- **DOI ✔**: `10.1177/00219983251388194`
- **왜**: **800 °C — 저희가 "밀봉 실패역"이라 주장하는 구간**의 손상을 정량화합니다.

### 13. **[B]** Temperature-driven **damage transition** in C/SiC composites up to 1800 °C via quantitative in-situ μCT
- **출처**: *Compos. Part A* (2026) — **PII** `S1359836826004828`, DOI 미확인
- **왜**: **온도에 따라 손상 기구가 바뀐다**는 것을 정량화 — 저희 $k(T_{max})$
  프레임의 직접 근거가 될 수 있습니다.

### 14. **[B]** Temperature dependent **fatigue** damage evolution of SiCf/SiC captured using in-situ X-ray imaging and strain analysis
- **출처**: *Compos. Part A* (2025) — **PII** `S1359835X25004919`, DOI 미확인

### 15. **[B]** 4D damage evolution in SiCf/SiC at 1800 °C: pores and strain fields by in-situ μCT and **DVC**
- **출처**: *J. Eur. Ceram. Soc.* (2026) — **PII** `S0955221926002153`, DOI 미확인

### 16. **[B]** Elevated-temperature in-situ μCT and progressive damage simulation of **EBC-coated SiC/SiC**
- **출처**: *Compos. Part A* (2025) — **PII** `S1359836825008315`, DOI 미확인
- **왜**: 1350 / 1600 / 1800 °C, **관측 + 시뮬레이션을 함께** 한 편. 저희처럼
  **메소스케일 공극을 모델에 넣은** 접근이라 방법론 비교 대상입니다.

---

# ★ 5군 — 열잔류응력 측정 (2편)

§4.9-2·§4.9-11의 **무응력 온도 결정**에 걸립니다. 지금 저희는 1050 °C를 가정하고
CONFIG_P에서 800 °C로 내리는데, **실측 근거가 `refs/[15]`의 XRD 한 건**뿐입니다.

### 17. **[A]** **In situ** characterization of **residual stress evolution during heat treatment** of SiC/SiC using high-energy X-ray diffraction
- **저자**: Knauf 외
- **출처**: *J. Am. Ceram. Soc.* (2021)
- **DOI ✔**: `10.1111/jace.17493`
- **왜**: ★ **가열 중 잔류응력이 어떻게 풀리는지를 실시간으로** 측정합니다.
  검색 결과에 *"제조온도에 가까워지면 거의 무응력 상태에 접근한다"*는 진술이
  있었는데, **이것이 확인되면 저희 무응력 온도 가정의 직접 근거**가 됩니다.

### 18. **[A]** Measuring the effects of heat treatment on SiC/SiC CMC using **Raman spectroscopy**
- **저자**: Knauf 외
- **출처**: *J. Am. Ceram. Soc.* (2020)
- **DOI ✔**: `10.1111/jace.16724`
- **왜**: 17번의 다른 측정법 판. 두 방법이 일치하면 근거가 강해집니다.

---

# ★ 6군 — 그 밖에 볼 만한 것 (2편)

### 19. **[C]** Investigation on the Mechanism of **Thermal Cycling Failure in C/SiC**
- **출처**: ICAS 2024 학회논문 (논문번호 0796) — **무료 PDF**
  `https://www.icas.org/icas_archive/icas2024/data/papers/icas2024_0796_paper.pdf`
- **왜**: **무료이고 주제가 정확히 겹칩니다.** 학회논문이라 인용 가치는 낮지만
  **최신 동향 파악용으로 지금 바로 읽을 수 있습니다.**

### 20. **[C]** Evaluating the Thermal Shock Resistance of SiC-C/CA Composites Through the **Cohesive Finite Element Method and Machine Learning**
- **출처**: *Applied Sciences* **14**(23) (2024) 11025 — **OA(무료)**
  `https://www.mdpi.com/2076-3417/14/23/11025`
- **왜**: 열충격 저항을 **다른 수치기법(응집영역 + 기계학습)**으로 푼 예. 저희 CDM
  접근의 대안을 서술할 때 씁니다.

---

# 지금 바로 열 수 있는 것 — 4편

| # | 논문 | 접근 |
|---|---|---|
| **2** | Wu 외 2026, 2.5D C/SiC 산화 구성식 | **OA** `10.3390/ma19020307` |
| 19 | ICAS 2024 C/SiC 열싸이클 파손 | **무료 PDF** |
| 20 | Applied Sci. 2024, 응집영역+ML | **OA** |
| — | (참고) `DOWNLOAD_LIST.md`의 미니콤포지트 A22 | **OA** |

---

# 우선순위 요약

| 순서 | 무엇 | 편수 | 얻는 것 |
|---|---|---|---|
| **1** | **1·2번** | 2 | **산화가 $k$ 부호를 가른다는 주장의 문헌 근거.** 2번은 무료 |
| **2** | **3·4번** | 2 | 1300 °C 최신 데이터 + 산화-손상 연성 모델 |
| **3** | **17번** | 1 | **무응력 온도 가정의 실측 근거** — 지금 가장 약한 가정입니다 |
| **4** | **10·11번** | 2 | 비활성 vs 공기 손상 관찰 (1군의 영상 근거) |
| 5 | 8번 | 1 | §4.6.1 방어 (2026년 리뷰) |
| 6 | 5·6·7번 | 3 | 보정용 곡선 추가 |
| 7 | 나머지 | 9 | 고찰·비교 |

**1~4순위 = 7편이 가장 효율적입니다.**

---

# ⚠️ 정직한 고지

- **DOI를 확인하지 못한 것이 9편**입니다(3, 4, 9, 10, 11, 13, 14, 15, 16번).
  **PII로 찾으실 수 있으므로 추측해서 적지 않았습니다.**
- **저자를 확인하지 못한 것이 4편**입니다(3, 5(부분), 9, 그리고 PII만 있는 일부).
  검색 결과에 안 나온 것은 비워 두었습니다.
- **원문은 한 편도 못 읽었습니다.** 위 "왜"는 **제목·초록·검색 요약**을 근거로 한
  판단이며, 등급도 그 수준입니다. **받아 보시면 제가 내용을 확인해 조정하겠습니다.**
- 5번(Cao 2025)은 **코팅된 시편**이라 저희 재료와 직접 비교되지 않습니다.
  경향 비교용으로만 쓰세요.
