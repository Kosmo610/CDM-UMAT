# 다운로드 목록 — 참고문헌에 넣을 논문 (2026-08-03)

> **쓰는 법.** DOI(논문마다 붙는 고유 번호)를 학교 도서관 검색창이나
> `https://doi.org/` 뒤에 붙여 넣으면 바로 열립니다.
> **OA**(오픈액세스 = 무료 공개)라고 적힌 것은 로그인 없이 열립니다.

---

# 0부. 새 최우선 1편 (2026-08-11 추가) — **카드 손잡이 2개를 값으로 바꾸는 유일한 출처**

Zhang (2022) `refs/[05]` 은 식 (18)의 혼합법칙 파라미터 $X_{PO}$·$K_1$ (그리고 그로부터
유도되는 $r_F$) 의 값을 **본문에 싣지 않고 자기 참고문헌 30번으로 미룬다.** 그 30번의
실체를 원문 참고문헌부에서 확인했다. 지금 카드에서 "선언된 손잡이"로 남아 있는 값들이
이 한 편으로 **출처 있는 값**이 된다.

| # | 논문 | DOI |
|---|---|---|
| **P-1** | **S.Y. Zhong, L.C. Guo, G. Liu, H.Y. Lu, T. Zeng** (2015). *A continuum damage model for three-dimensional woven composites and finite element implementation.* **Composite Structures 128, 1–9.** | `10.1016/j.compstruct.2015.03.030` |

> **✅ 2026-08-11 확보 완료 — `refs/[73]`.** 아래는 원문 표제면·본문에서 직접 확인한 것이다.

- **DOI가 표제면에 그대로 찍혀 있다** — `10.1016/j.compstruct.2015.03.030`.
  등급을 `search-verified` → **`fulltext`** 로 올린다.
- 세 번째 저자를 소문자 `Gang liu` 로 찍은 것은 **저널 자신의 조판**이다
  (Zhang의 인용도 같고, 원문 표제면도 같다). 정규 표기는 `G. Liu`.
- ★ **정작 찾던 수치는 이 논문에도 없다.** Table 1은 구성재 탄성상수와 $S_{f,1t}$만,
  Table 2는 구조만 싣는다. $X_{PO}$($S_{po}$)·$K_1$($K_{f,1}$)의 **값은 계보의 원전에도
  없다.** 따라서 이 둘은 추적 대상에서 내리고 **확정적으로 선언된 knob**으로 닫는다.
- 대신 세 가지를 얻었다 — ① $r_F$가 교점 조건으로 정해지는 **유도량**임을 원전이
  명시(주 knob 5 → **4개**), ② 연화 파라미터 $A$는 파괴에너지에서 유도하도록 정의됨
  (우리 $A$=2.0은 선언된 이탈), ③ 이 파라미터 계보 전체가 **에폭시 기지**(TDE-86)
  복합재에서 왔다 — 수치가 있었더라도 C/SiC 카드에는 DEV를 벗어나지 못했을 것이다.
- 상세는 제4장 §4.9-8.

---

# 1부. S등급 24편 — **최우선**

**왜 최우선인가.** 논문 본문이 *"Hashin 기준을 쓴다"*, *"Bažant 균열대를 쓴다"*,
*"Chamis 식으로 계산했다"* 라고 **이름을 부르는데, 참고문헌 목록에 그 논문이 없습니다.**
심사에서 가장 먼저 지적되는 종류의 결함입니다. 갖고 계신 45편은 전부 응용 논문이고
**기법의 원전(原典 = 그 방법을 처음 제시한 논문)이 0편**입니다.

## 1-1. 균열대 정규화 — 4편

논문의 메시 독립성 주장 전체가 이 계보에 걸려 있습니다.

| # | 논문 | DOI |
|---|---|---|
| **S1** | **Bažant, Z.P., Oh, B.H.** (1983). *Crack band theory for fracture of concrete.* **Materials and Structures 16**(93), 155–177. | `10.1007/BF02486267` |
| S21 | Jirásek, M., Bauer, M. (2012). *Numerical aspects of the crack band approach.* **Computers & Structures 110–111**, 60–78. | `10.1016/j.compstruc.2012.06.006` |
| S22 | Oliver, J. (1989). *A consistent characteristic length for smeared cracking models.* **Int. J. Numer. Methods Eng. 28**(2), 461–474. | `10.1002/nme.1620280214` |

> **S1이 이 중 가장 급합니다.** 제3장 §3.2.3의 $A = 2g_0l_e/(G_f - g_0l_e)$ 와
> 스냅백 한계 $l_e < G_f/g_0$ 가 전부 이 논문에서 옵니다.
> ⚠️ 이 학술지는 데이터베이스에 **프랑스어 원제 *Matériaux et Constructions***
> 로도 등록돼 있습니다. 영어 제목으로 안 나오면 DOI로 찾으세요.

## 1-2. 파손 기준 — 4편

| # | 논문 | DOI |
|---|---|---|
| **S2** | **Hashin, Z.** (1980). *Failure criteria for unidirectional fiber composites.* **J. Appl. Mech. 47**(2), 329–334. | `10.1115/1.3153664` |
| **S3** | **Tsai, S.W., Wu, E.M.** (1971). *A general theory of strength for anisotropic materials.* **J. Compos. Mater. 5**(1), 58–80. | `10.1177/002199837100500106` |
| **S4** | **Liu, K.-S., Tsai, S.W.** (1998). *A progressive quadratic failure criterion for a laminate.* **Compos. Sci. Technol. 58**(7), 1023–1032. | `10.1016/S0266-3538(96)00141-8` |
| S24 | Hashin, Z., Rotem, A. (1973). *A fatigue failure criterion for fiber reinforced materials.* **J. Compos. Mater. 7**(4), 448–464. | `10.1177/002199837300700404` |

> S2는 **손상을 실제로 구동하는 기준**의 원전입니다. S4는 Tsai–Wu를 하중 배수로
> 정규화하는 방법(§2.6.1의 "반드시 주의할 점" 박스)의 출처입니다.

## 1-3. 손상역학 정식화 — 6편

| # | 논문 | DOI |
|---|---|---|
| **S5** | **Matzenmiller, A., Lubliner, J., Taylor, R.L.** (1995). *A constitutive model for anisotropic damage in fiber-composites.* **Mech. Mater. 20**(2), 125–152. | `10.1016/0167-6636(94)00053-0` |
| S14 | Lemaitre, J., Chaboche, J.-L. (1990). *Mechanics of Solid Materials.* Cambridge Univ. Press. | ISBN 978-0-521-32853-1 |
| S15 | Lemaitre, J. (1985). *A continuous damage mechanics model for ductile fracture.* **J. Eng. Mater. Technol. 107**(1), 83–89. | `10.1115/1.3225775` |
| S16 | Kachanov, L.M. (1958). *Time of the rupture process under creep conditions.* **Izv. AN SSSR, Otd. Tekh. Nauk 8**, 26–31. | 없음 |
| S19 | Ladevèze, P., Le Dantec, E. (1992). *Damage modelling of the elementary ply for laminated composites.* **Compos. Sci. Technol. 43**(3), 257–267. | `10.1016/0266-3538(92)90097-M` |

> **S5가 이 절의 핵심입니다.** 파손 판정지수 → 손상변수 → 연화 강성으로 가는
> **매핑**의 원전이며, Abaqus 계열 복합재 손상 UMAT의 사실상 조상입니다.
> Hashin(S2)은 "부서지는가"만 말하고 그 다음을 말하지 않습니다.
>
> S14는 책이라 도서관에서 빌리셔야 합니다. 교과서 인용을 꺼리면 S15로 대체 가능합니다.
> S16은 1958년 러시아어 논문이라 구하기 어렵습니다 — **못 구하면 S14를 통해 인용**하세요.

## 1-4. 단방향 손상(균열 닫힘) — 3편

| # | 논문 | DOI |
|---|---|---|
| **S10** | **Chaboche, J.-L.** (1992). *Damage induced anisotropy: on the difficulties associated with the active/passive unilateral condition.* **Int. J. Damage Mech. 1**(2), 148–171. | `10.1177/105678959200100201` |
| S9 | Chaboche, J.-L. (1993). *Development of continuum damage mechanics for elastic solids sustaining anisotropic and unilateral damage.* **Int. J. Damage Mech. 2**(4), 311–329. | `10.1177/105678959300200401` |
| S20 | Chaboche, J.-L., Lesne, P.-M., Maire, J.-F. (1995). *Continuum damage mechanics, anisotropy and damage deactivation for brittle materials like concrete and ceramic composites.* **Int. J. Damage Mech. 4**(1), 5–22. | `10.1177/105678959500400102` |

> **S10이 특히 중요합니다.** 손상 비활성화가 강성을 불연속·비대칭으로 만들어
> **Newton 반복이 원리적으로 수렴할 수 없게 되는** 기구의 원출처입니다.
> 저희가 실제로 겪은 비수렴 문제(`M1_FAILURE_ANALYSIS.md`)와 직결됩니다.
>
> S20은 이 계보를 **CMC에 적용한** 편이고, `refs/[28]`의 참고문헌 21번으로
> 권·쪽이 확정되었습니다.

## 1-5. 마이크로역학(얀 물성 유도) — 2편

| # | 논문 | DOI |
|---|---|---|
| **S6** | **Chamis, C.C.** (1983). *Simplified Composite Micromechanics Equations for Hygral, Thermal and Mechanical Properties.* **NASA TM-83320.** | **NTRS 19830011546 — 무료** |
| **S7** | **Schapery, R.A.** (1968). *Thermal expansion coefficients of composite materials based on energy principles.* **J. Compos. Mater. 2**(3), 380–404. | `10.1177/002199836800200308` |

> **S6은 NASA NTRS에서 무료로 받으세요** — `https://ntrs.nasa.gov` 에서 `19830011546`.
> 흔히 인용되는 *SAMPE Quarterly* 판은 **DOI가 없고 원문 확보가 어려워
> 심사위원이 확인할 수 없습니다.** NASA TM을 주 인용으로 하고 SAMPE를 병기하세요.
>
> 이 둘이 `micromech_check.py`가 검증하는 **얀 물성 12개 전부**의 출처입니다.

## 1-6. 사이클 손상·시간 균질화 — 2편

| # | 논문 | DOI |
|---|---|---|
| **S8** | **Van Paepegem, W., Degrieck, J., De Baets, P.** (2001). *Finite element approach for modelling fatigue damage in fibre-reinforced composite materials.* **Compos. Part B 32**(7), 575–588. | `10.1016/S1359-8368(01)00038-5` |
| S23 | Cojocaru, D., Karlsson, A.M. (2006). *A simple numerical method of cycle jumps for cyclically loaded structures.* **Int. J. Fatigue 28**(12), 1677–1689. | `10.1016/j.ijfatigue.2006.01.010` |

> **S8이 cycle jump(사이클 건너뛰기)의 1차 출처**이고, 검증 대상이 **평직
> 유리/에폭시**라 저희 구조와 같습니다.
> ⚠️ S23의 학술지는 *Int. J. Fatigue* 입니다 (*Fatigue Fract. Eng. Mater. Struct.* 아님).

## 1-7. 열충격 저항 파라미터 — 3편

**본문 §2.4.4가 `R''''`를 Hasselman 1969로 잘못 귀속하고 있었습니다.** 세 편을 병기해야
합니다.

| # | 논문 | DOI |
|---|---|---|
| **S12** | **Hasselman, D.P.H.** (**1963**). *Elastic energy at fracture and surface energy as design criteria for thermal shock.* **J. Am. Ceram. Soc. 46**(11), 535–540. | `10.1111/j.1151-2916.1963.tb14605.x` |
| S11 | Kingery, W.D. (1955). *Factors affecting thermal stress resistance of ceramic materials.* **J. Am. Ceram. Soc. 38**(1), 3–15. | `10.1111/j.1151-2916.1955.tb14545.x` |
| S13 | Hasselman, D.P.H. (1969). *Unified theory of thermal shock fracture initiation and crack propagation in brittle ceramics.* **J. Am. Ceram. Soc. 52**(11), 600–604. | `10.1111/j.1151-2916.1969.tb15848.x` |

> $R$ = Kingery 1955, **$R''''$ = Hasselman 1963**, $R_{st}$ = Hasselman 1969.
> S13은 **반복 열충격에서 "1회차 급락 후 완만"한 잔여강도 곡선**을 설명하므로
> 본 연구 주제에 가장 가깝습니다.

## 1-8. CMC 미시역학 — 2편

| # | 논문 | DOI |
|---|---|---|
| S17 | Curtin, W.A. (1991). *Theory of mechanical properties of ceramic-matrix composites.* **J. Am. Ceram. Soc. 74**(11), 2837–2845. | `10.1111/j.1151-2916.1991.tb06852.x` |
| S18 | Aveston, J., Kelly, A. (1973). *Theory of multiple fracture of fibrous composites.* **J. Mater. Sci. 8**(3), 352–362. | `10.1007/BF00550155` |

> §2.2.2의 섬유 인발과 기지 다중균열. S18은 ACK 1971 학회논문집보다 이쪽이
> **쪽수 표기 충돌이 없어** 주 인용으로 권장합니다.

---

# 2부. 추가 핵심 논문 — **`refs/[28]` 전문을 읽고 골랐습니다**

**왜 신뢰도가 높은가.** 아래는 전부 **`refs/[28]`의 참고문헌 목록에 인쇄된 것**을
그대로 옮긴 것입니다. 제가 추정한 정보가 아니라 **논문에 찍혀 있는 정보**입니다.
그리고 `refs/[28]`은 **저희와 완전히 같은 재료**(2D 평직 C/SiC, CVI, T300, PyC)를
다룬 논문이므로, 그 참고문헌은 곧 **이 재료 연구의 정전(正典) 목록**입니다.

## 2-1. ★★★ 반드시 구해야 하는 것 — 3편

| 논문 | 왜 |
|---|---|
| **Camus, G., Guillaumat, L., Baste, S.** (1996). *Development of damage in a 2D woven C/SiC composite under mechanical loading: I. Mechanical characterization.* **Compos. Sci. Technol. 56**(12), 1363–1372. | ★ **저희가 쓴 방법의 원전입니다.** 이력 곡선의 교점 O′를 **열잔류응력으로 읽는 방법**이 여기서 나왔습니다(`refs/[28]`이 자기 방법을 이 논문에 귀속합니다). `digitize_ref28_fig17.py`가 쓰는 방법이므로 **방법은 이 논문, 측정값은 [28]** 로 인용해야 맞습니다 |
| **Li, J., Jiao, G.Q., Wang, B., Li, L., Yang, C.P.** (2015). *Damage characteristics and constitutive modeling of the 2D C/SiC composite: **Part II** — Material model and numerical implementation.* **Chin. J. Aeronaut. 28**(2), 314–326. DOI `10.1016/j.cja.2014.10.027` | ★ **`refs/[28]`의 후속편.** Part I이 실험, **Part II가 그 실험을 CDM으로 구현한 편**입니다. 저희 `HCLO`(균열 닫힘)와 **직접 비교 대상**입니다. ⚠️ **27권이 아니라 28권입니다** — Part I의 참고문헌이 연도만 적어 놓아 오인하기 쉽습니다 |
| **Mei, H., Cheng, L.F., Zhang, L.T., Luan, X.G., Zhang, J.** (2006). *Behavior of two-dimensional C/SiC composites subjected to **thermal cycling in controlled environments**.* **Carbon 44**(1), 121–127. | ★ **`refs/[28]`이 자기 시편의 제작 절차를 이 논문에 귀속합니다** — 즉 **완전히 같은 재료**입니다. 동시에 **분위기를 제어한 반복 열싸이클** 논문이라, §2.5.4의 "산소가 있어야 손상이 쌓인다"는 주장의 **1차 근거**가 됩니다 |

## 2-2. ★★ 균열 닫힘·강성 회복 — 저희 C3 기여의 직접 선행연구

| 논문 | 왜 |
|---|---|
| **Morvan, J.M., Baste, S.** (1998). *Effect of the **opening/closure of microcracks** on the nonlinear behavior of a 2D C–SiC composite under **cyclic loading**.* **Int. J. Damage Mech. 7**(4), 381–402. | ★ **제목 그대로 저희 주제입니다.** 2D C–SiC의 미세균열 개폐가 사이클 하중에서 비선형 거동에 미치는 영향 |
| **El Bouazzaoui, R., Baste, S., Camus, G.** (1996). *Development of damage in a 2D woven C/SiC composite under mechanical loading: **II. Ultrasonic characterization**.* **Compos. Sci. Technol. 56**, 1373–1382. | 위 Camus 논문의 짝. **초음파로 강성 텐서 전체의 변화를 직접 측정**합니다 — 손상 변수를 강성으로 정의하는 저희 방식의 실험적 근거 |
| **Baste, S.** (2001). *Inelastic behaviour of ceramic-matrix composites.* **Compos. Sci. Technol. 61**(15), 2285–2297. | 위 두 편의 종합 |

## 2-3. ★★ 압축 거동 — 카드의 `X_c`가 추정값인 문제에 직결

| 논문 | 왜 |
|---|---|
| **Wang, M.D., Laird, C.** (1996). *Damage and fracture of a cross woven C/SiC composite subject to **compression** loading.* **J. Mater. Sci. 31**(8), 2065–2069. | ★ **직조 C/SiC의 압축을 전담한 거의 유일한 논문.** 얀 압축강도 $X_c$ = 1956 MPa는 지금 **근거 없는 추정값**입니다 |

## 2-4. ★★ 전단 — 카드의 `S12`·`S23`이 추정값인 문제에 직결

| 논문 | 왜 |
|---|---|
| **Guan, G.Y., Jiao, G.Q., Zhang, Z.G.** (2005). *In-plane shear fracture characteristics of plain-woven C/SiC composite.* **Mech. Sci. Technol. 24**(5), 515–517. **[중국어]** | 평직 C/SiC 면내 전단 전담 |
| **Wang, H.L., Zhang, C.Y., Liu, Y.S., Han, D., Li, M., Qiao, S.R.** (2012). *Temperature dependency of **interlaminar** shear strength of 2D-C/SiC composite.* **Mater. Des. 36**, 172–176. | 층간 전단 vs 온도. 보유 `refs/[35]`(면내 전단 vs 온도)의 짝 |

## 2-5. ★ 열잔류응력 측정 — 인용 금지 항목을 풀어 줄 후보

| 논문 | 왜 |
|---|---|
| **Mei, H.** (2008). *Measurement and calculation of thermal residual stress in fiber reinforced ceramic matrix composites.* **Compos. Sci. Technol. 68**(15–16), 3285–3292. | CMC 열잔류응력 측정·계산 전담 |
| **Dassios, K.G., Aggelis, D.G., Kordatos, E.Z., Matikas, T.E.** (2013). *Cyclic loading of a SiC-fiber reinforced CMC reveals damage mechanisms and **thermal residual stress state**.* **Compos. Part A 44**, 105–113. | ★ 저장소에 **"출처 미상, 인용 금지"**로 묶여 있는 값 `−130.84 ± 34.53 MPa`의 **유력한 출처 후보**입니다. 확인되면 인용 금지가 풀립니다 |

## 2-6. ★ 직조 CMC 거시 손상모델 — 저희 모델의 비교 대상

| 논문 | 왜 |
|---|---|
| **Camus, G.** (2000). *Modelling of the mechanical behavior and damage processes of fibrous ceramic matrix composites: application to a 2-D SiC/SiC.* **Int. J. Solids Struct. 37**(6), 919–942. | 2D SiC/SiC 거시 손상모델 |
| **Chaboche, J.-L., Maire, J.-F.** (2002). *A new micromechanics based CDM model and its application to CMC's.* **Aerosp. Sci. Technol. 6**(2), 131–145. | 미시역학 기반 CDM |
| **Marcin, L., Maire, J.-F., Carrère, N., Martin, E.** (2011). *Development of a macroscopic damage model for **woven** ceramic matrix composites.* **Int. J. Damage Mech. 20**(6), 939–957. | **직조** CMC 전용 거시 모델 — 저희와 같은 위치의 모델 |

## 2-7. ★ 2D 직조 인장·off-axis

| 논문 | 왜 |
|---|---|
| **Morscher, G.N., Yun, H.M., DiCarlo, J.A.** (2007). *In-plane cracking behavior and ultimate strength for 2D woven and braided melt-infiltrated SiC/SiC composites tensile loaded in **off-axis** fiber directions.* **J. Am. Ceram. Soc. 90**(10), 3185–3193. | `refs/[28]`이 "섬유 지배 복합재"라는 분류를 이 논문에 귀속합니다 |
| **Dalmaz, A., Reynaud, P., Rouby, D., Fantozzi, G.** (1996). *Damage propagation in carbon/silicon carbide composites during tensile tests **under the SEM**.* **J. Mater. Sci. 31**(16), 4213–4219. | 인장 중 손상 진전을 SEM으로 직접 관찰 |
| **Li, L.B.** (2013). *Modeling hysteresis behavior of cross-ply C/SiC ceramic matrix composites.* **Compos. Part B 53**, 36–45. | 이력 곡선 기반 계면 파라미터 추출 |

## 2-8. ★★ 얀(실 다발) 수준 직접 측정 — **추정값 5개를 실측값으로 바꿉니다**

**이 두 편이 제 조사에서 나온 최대 수확입니다.** 카드에 들어가는 26개 숫자 중
**14개가 근거 없는 추정값**인데, 그중 5개가 *"얀 하나만 따로 뽑아서 재는 시험법이
없다"*는 이유였습니다. 그 시험법을 확립한 그룹이 있습니다.

| 논문 | 무엇을 바꾸는가 |
|---|---|
| **Yu, G., Xie, C., Du, J., Ni, Z., Chang, L., Gao, X., Song, Y.** (2023). *In-plane shear experimental method and mechanical behavior of ceramic matrix **mini-composites**.* **J. Mater. Res. Technol. 24**, 5541–5551. DOI `10.1016/j.jmrt.2023.04.139` **— OA(무료)** | **$S_{12}$, $S_{13}$, $S_{23}$** 세 개 |
| **Yu, G. 외** (2022). *Transverse tensile experimental method and behavior of ceramic matrix **mini-composites**.* **Compos. Struct. 297**, 115923. DOI `10.1016/j.compstruct.2022.115923` | **$Y_t$** |

> **앞의 것은 무료 공개라 지금 바로 열립니다.** 이 둘만 확보되면 추정값이
> **14개 → 9개**로 줄어듭니다.

---

# 3. 우선순위 요약

| 순서 | 무엇 | 몇 편 | 왜 |
|---|---|---|---|
| **1** | **S1, S2, S5, S6, S12** | 5 | 본문이 이름을 부르는데 없는 것 중 **가장 자주 불리는 것**. S6은 무료 |
| **2** | **2-8의 미니콤포지트 2편** | 2 | **추정값 14 → 9.** 한 편은 무료 |
| **3** | **2-1의 3편** (Camus 1996, Part II, Mei 2006) | 3 | 같은 재료의 정전 + 저희 방법의 원전 |
| 4 | 나머지 S등급 | 19 | 인용 형태를 갖추기 위해 |
| 5 | 2-2 ~ 2-7 | 13 | 고찰·비교용 |

**1~3번 = 10편만 먼저 구하셔도 논문의 방어력이 크게 올라갑니다.**

---

# 4. 주의사항

- **S16**(Kachanov 1958, 러시아어)은 사실상 구하기 어렵습니다. **못 구하면
  S14(Lemaitre & Chaboche 교과서)를 통해 간접 인용**하시면 됩니다.
- **S14**는 책입니다. 도서관 대출이 필요합니다.
- **Guan 2005**는 중국어 논문이라 접근이 어려울 수 있습니다. 못 구하면 빼셔도 됩니다.
- **Part II는 28권**입니다(27권 아님). 두 편을 같은 권으로 적으면 심사에서 걸립니다.
- 위 목록의 **DOI·권·쪽은 전부 데이터베이스 대조 또는 `refs/[28]`의 인쇄된
  참고문헌으로 확인한 것**입니다. 제가 추정한 값은 없습니다.
- 확인하지 못한 것은 적지 않았습니다 — S16에는 DOI를 비워 두었습니다.
