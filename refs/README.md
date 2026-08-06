# 참고문헌 원문 색인

`docs/`에서 옮겨왔습니다. 이유는 아래 **§0 위치에 대한 판단** 참조.

원문에서 뽑은 상관식은 전부 **`data/properties/eval_correlations.py`** 에 코드로 들어가
있고, 논문이 스스로 말하는 값과 대조하는 검산이 붙어 있습니다:

```bash
python3 data/properties/eval_correlations.py --check   # 8개 검산 전부 PASS
python3 abaqus/build_temperature_tables.py             # -> UMAT 카드 블록
```

---

## 0. 위치에 대한 판단 — `docs/`는 적절하지 않습니다

`docs/`는 **이 프로젝트가 생산한 문서**(연구계획, 데이터 명세)를 담는 곳입니다.
남이 쓴 저작물 PDF 54 MB가 섞이면 세 가지 문제가 생깁니다.

| 문제 | 내용 |
|---|---|
| **저작권** | 출판사(Elsevier 등) PDF를 **공개** 저장소에 커밋하는 것은 대부분의 구독 라이선스 위반입니다. **이 저장소가 public이면 실제 문제**이고, private이면 위험은 낮지만 회색지대입니다. 확인해 보세요. |
| **저장소 비대화** | git은 바이너리 델타를 못 합니다. PDF를 한 번이라도 교체하면 **전체 사본이 히스토리에 영구히 추가**됩니다. 지금 54 MB, 한 번 갈아끼울 때마다 +54 MB. |
| **가독성** | `docs/`의 `.md` 두 개가 PDF 15개 사이에 묻힙니다. |

**선택지**

- **A. 지금처럼 `refs/`에 커밋 유지 (현재 상태).** 장점: 제가 매 세션 바로 읽을 수 있습니다
  (작업 컨테이너는 세션마다 초기화되므로, 커밋되어 있지 않으면 매번 다시 올리셔야 합니다).
  **저장소가 private일 때만 권합니다.**
- **B. `refs/`는 로컬 전용, 색인만 커밋.** `.gitignore`에 `refs/*.pdf`를 넣고 이 README만
  버전관리. 저작권·용량 문제가 모두 사라지지만, **매 세션 PDF를 다시 올려주셔야** 합니다.
- **C. 절충 (권장).** 저장소가 public이면 **B**로 전환하고, 필요한 수치는 이미
  `eval_correlations.py`에 상관식으로 들어가 있으므로 **PDF 없이도 파이프라인이 돕니다.**
  원문은 논문 집필 때 인용 확인용으로만 로컬에 두세요.

지금은 **A** 상태로 두었습니다. 저장소 공개 여부를 확인하시고 알려주시면 B/C로 바꾸겠습니다.

---

## 1. 색인

### 입력 데이터 (구성재 → UMAT 카드) — 추출 완료

| # | 파일 | 서지 | 뽑은 것 | 상태 |
|---|---|---|---|---|
| 06 | `[06] 1st SiC 매트릭스 열물성.pdf` | **Snead, Nozawa, Katoh, Byun, Kondo, Petti**, *Handbook of SiC properties for fuel performance modeling*, **J. Nucl. Mater. 371 (2007) 329–377** | Eq.10 `Cp(T)`, Eq.12 `k(T)`, Eq.16 `α(T)`, Eq.18 `E(T)`, ρ=3.21 g/cm³ | ✅ 코드화 + 검산 |
| 07 | `[07] 1st T300 탄소섬유 열팽창 물성.pdf` | **Pradère & Sauder**, *Transverse and longitudinal CTE of carbon fibers at high temperatures (300–2500 K)*, **Carbon 46 (2008) 1874–1884** | Table 3/4 열변형률 다항식 (PANEX 33) | ✅ 코드화 + 검산 |
| 08 | `[08] 1st T300 탄소섬유 고온 역학 물성.pdf` | **Sauder, Lamon, Pailler**, *Thermomechanical properties of carbon fibres at high temperatures (up to 2000 °C)*, **Compos. Sci. Technol. 62 (2002) 499–504** | Table 1: `E/E₀(T)`, `σ_R(T)` (PAN계) | ✅ 코드화 |
| 09 | `[09] 1st T300 탄소섬유 열전도비열 물성.pdf` | **Pradère, Batsale, Goyhénèche, Pailler, Dilhaire**, *Thermal properties of carbon fibers at very high temperature*, **Carbon 47 (2009) 737–743** | Table 1: ρ=1.75 g/cm³, k∥=75 W/(m·K) @1500 K · Fig. 5a `Cp(T)` · Fig. 5b 확산도 | ✅ 코드화 + 검산 2종. **단 측정범위 800–2000 K, 횡방향 k 미측정** (아래 §2-7,8) |

### 검증 데이터 (복합재 → 모델 출력과 대조, **입력 금지**)

| # | 파일 | 서지 | 쓸 곳 |
|---|---|---|---|
| 10 | `[10] 2nd 2D CSiC 인장물성과 온도_검증 전용.pdf` | **Yang, Zhang, Wang, Huang, Jiao**, *Tensile behavior of 2D-C/SiC composites at elevated temperatures: Experiment and modeling*, **J. Eur. Ceram. Soc. 37 (2017) 1281–1290** | Ch.6.1 — E(T), σu(T). 초록이 TRS 지배를 명시 |
| 11 | `[11] 2nd 2D CSiC 열팽창과 온도_검증 전용.pdf` | **Q. Zhang, Cheng, L. Zhang, Xu**, *Thermal expansion behavior of C/SiC from RT to 1400 °C*, **Mater. Lett. 60 (2006) 3245–3247** | Ch.4.3 — 균질화 ᾱ(T) 대조 |
| 12 | `[12] 2nd CSiC 열전도율_검증 전용.pdf` | **Cao, Liu, Zhang, Wang, Chen**, *Enhancing thermal conductivity of C/SiC composites containing heat transfer channels*, **J. Eur. Ceram. Soc. 40 (2020) 3520–3527** | Ch.4.3 — k̄ 대조 |
| 13 | `[13] 2nd CSiC 열전도율_검증 전용.pdf` | **Katoh, Nozawa, Snead, Hinoki, Kohyama**, *Property tailorability for advanced CVI SiC composites for fusion*, **Fusion Eng. Des. 81 (2006) 937–944** | Ch.4.3 — 축방향 tow가 k를 지배한다는 결론 |
| 14 | `[14] 2nd 보조_검증전용.pdf` | **Longbiao Li**, *Modeling Temperature-Dependent Vibration Damping in C/SiC*, **Materials (2020)** | 보조 |

### 반복 열충격 검증 — ★ 여기에 큰 수확이 있었습니다

| # | 파일 | 서지 | 내용 |
|---|---|---|---|
| 02 | `[02] yin2002 S.pdf` | **Yin, Cheng, Zhang, Xu**, *Thermal shock behavior of 3-dimensional C/SiC composite*, **Carbon 40 (2002) 905–910** | **3D** C/SiC, CVI, 공기 급랭 1300→300 °C. 100회 후 잔여 굽힘강도 83 %, 임계 N≈50, 이후 균열밀도 포화 |
| 03 | `[03] zhang2012 S.pdf` | **C. Zhang, Wang, Wang, Liu, Han, Qiao, Guo**, *Thermal Shock Properties of a 2D-C/SiC Composite Prepared by CVI*, **JMEPEG 22 (2013) 1680–1687** | **2D** C/SiC, 900↔300 °C 반복. **20 사이클까지 인장강도 유지, 그러나 탄성계수는 사이클에 따라 점진 감소** |

> **[03]이 [02]보다 우리 논문에 더 잘 맞습니다.** 이유: (1) **2D** — 우리 아키텍처와 동일,
> (2) **잔여 탄성계수 vs 사이클 수** — 우리 모델의 주 출력, (3) 굽힘이 아닌 **인장**.
> 지금 `data/literature/csic_thermal_shock.csv`는 [02]만 앵커로 쓰고 있으므로
> **[03]의 곡선을 디지타이즈해 추가하는 것이 다음 우선순위**입니다.
>
> 또한 CSV의 인용키 `SUN2002`는 **잘못**입니다. 저자는 Yin, Cheng, Zhang, Xu이므로
> `YIN2002`로 정정했습니다.

### ★ 2차 입고분 `[15]`–`[35]` — 노벨티 재점검 결과는 **[`../docs/NOVELTY.md`](../docs/NOVELTY.md)**

핵심 4편만 여기 적고, 전체 분석과 권고는 `docs/NOVELTY.md`에 있습니다.

| # | 서지 | 왜 핵심인가 |
|---|---|---|
| **17** | **P. Zhang, Zhu, Tong 외**, *Revealing thermal shock behaviors and damage mechanism of 3D needled C/C–SiC composites based on multi-scale analysis*, **JMRT 29 (2024) 2016–2034** | ⚠️ **가장 위험한 선행연구.** 다중스케일+반복 열충격을 이미 함. 단 (a) **균일 온도장**으로 단순화 명시, (b) **온도무관 물성** 가정, (c) TRS 처리 1가지 → **이 셋이 우리 자리** |
| **15** | **S. Zhang, D. Zhang, J. Zhou 외**, *Quantification of thermal residual stresses and their effects on the mechanical behavior of 3D C/SiC composites*, **Compos. A 207 (2026) 109796** | ★ **XRD 실측 TRS**: 매트릭스 +114.7/+40.3 MPa, 얀 −68.7/−23.9 MPa. "TRS는 매트릭스 균열이 생겨야 강성에 영향" + **인장/압축 비대칭** → 새 노벨티 C3의 근거 |
| **30** | **Q. Zhang, J. Ge, Liang 외**, *…2D C/SiC composites under cyclic loading: Experiment and simulation*, **Compos. B 313 (2026) 113395** | **우리 기반 논문과 같은 그룹의 2026 후속작.** 단 **진폭 증가** 기계 반복이라 shakedown이 안 생김 → 우리 문제와 다름을 명시할 근거 |
| **20** | **Z. Yang, J. Wang, R. Yang, J. Jiao**, *Thermomechanical-induced cracking model for CMC laminates subjected to thermal gradients and transients*, **IJSS 300 (2024) 112927** | 급랭 문제에 가장 가까움. 단 **ERR 기반 균열 개시**(누적손상 아님) + 라미네이트 1D |

> **⚠️ 폐번 2개 — PDF 45편이 곧 논문 45편이다 (2026-08-05 정리).**
> 같은 논문이 두 번 들어와 있던 것을 통합했다. **통합 후 중복은 없다.**
>
> | 폐번 | 통합처 | 논문 |
> |---|---|---|
> | `[21]` | **`[20]`** | Yang, Wang, Yang, Jiao, IJSS **300** (2024) 112927 |
> | `[39]` | **`[32]`** | Jain & Koch, J. Compos. Sci. **4**(4) (2020) 183 |
>
> **폐번 21·39는 다시 쓰지 않는다.** 새 논문은 46번부터 매긴다.
> `[39]`쪽이 특히 위험했다 — `docs/REFS_36_45_ASSESSMENT.md`가 이것을
> '지금까지 원문 없이 인용하던 D-기준 1차 출처를 새로 확보' 라고 적고
> 있었는데, 원문은 처음부터 `[32]`로 있었다. 그 서술은 정정했다.
> 판정기: `python3 data/literature/refs_audit.py --check`

> **⚠️ 고분자 기지 논문 7편이 섞여 있다 — 카드값 출처로 쓰면 안 된다.**
> `[24]`(탄소/페놀), `[25]`(탄소/에폭시), `[26]`(에폭시), `[37]`·`[38]`·`[40]`·`[41]`(에폭시).
> 이 중 `[25]`·`[26]`은 파일명이 '3D C-SiC 물성'이라 특히 위험하다.
> **기법(균질화·주기경계조건) 인용은 정당하고, 물성 인용만 금지**된다.
> 실제로 `[24]`에서 얀 $G_{1t}$·$G_{1c}$와 횡방향 강도가 넘어온 적이 있다.

### ★ 3차 입고분 `[46]`–`[50]` (2026-08-06) — 기법 원전 4편 + 신규 1편

| # | 서지 | 위치 |
|---|---|---|
| **46** | **Bažant & Oh**, *Crack band theory for fracture of concrete*, **Mater. Struct. 16(93) (1983) 155–177** | **`[S1]` 원문** — 균열대 이론 원전. $w_c \approx 3d_a$ 를 *"about the minimum admissible from the viewpoint of continuum smoothing"* 로 규정 |
| **47** | **Jirásek & Bauer**, *Numerical aspects of the crack band approach*, **Comput. Struct. 110–111 (2012) 60–78**, doi:`10.1016/j.compstruc.2012.06.006` | ⚠️ **목록에 없던 신규.** 우리 구현에 직접 걸린다 — 아래 참조 |
| **48** | **Liu & Tsai**, *A progressive quadratic failure criterion for a laminate*, **CST 58 (1998) 1023–1032** | **`[S4]` 원문** — 강도비 $R$(하중 배수 정규화)의 출처 |
| **49** | **Hashin**, *Failure criteria for unidirectional fiber composites*, **J. Appl. Mech. 47(2) (1980) 329–334** | **`[S2]` 원문** — 우리 UMAT 파손기준 원전 |
| **50** | **Tsai & Wu**, *A general theory of strength for anisotropic materials*, **JCM 5(1) (1971) 58–80** | **`[S3]` 원문** — 상호작용항 제약 $F_{12}^2 \le F_{11}F_{22}$ 로 파손면이 쌍곡면이 되는 것을 막는다 |

> **⚠️ `[47]`이 우리 균열대 구현을 직접 건드린다.**
> 우리 UMAT 은 `CELENT`(Abaqus 가 주는 요소 특성길이)를 $l_e$ 로 그대로 쓴다.
> `[47]`은 그 방식을 이렇게 평가한다 — *"the cubic root of the element volume
> (for three-dimensional elements). This rule, implemented in many commercial
> finite element packages, is easy to apply but it can induce a large error for
> elongated elements, and even for square or cube elements if the crack band is
> not aligned with the mesh."* 오차 크기는 *"comparable to a misprediction of
> the fracture energy by 50 % or even more"*.
> 권고는 **주변형률 주축에 요소를 투영**해 폭을 잡되 **요소 중심(또는 평균)에서**
> 주변형률을 평가하는 것이다. 반대로 **1차(선형) 요소를 쓰라**는 권고는 우리 C3D4
> 선택을 뒷받침한다 — *"higher-order elements are not suitable for crack band
> simulations, and the simplest (multi)linear elements should be preferred."*
> 우리 RVE 는 26 452개 중 **1 185개가 뒤틀린 요소**이므로 이 오차가 가장 커지는
> 조건에 해당한다. 판정은 코드 쪽(a2) 영역이라 `a1-0013`으로 넘겼다.

**파손기준 세트** (`[27]`,`[32]`,`[33]`,`[34]`,`[35]`,`[28]`) — D-criterion 계열.
`[33]` Yang, Jiao, Guo, *TAML* 4 (2014) 021007이 원전. `[35]` Yan 외, *Mater. Des.* 32 (2011)
3504는 **고온 면내 전단 파손** 데이터로 온도의존 파손포락선 검증에 쓸 수 있습니다.

**나머지** (`[16]`,`[18]`,`[19]`,`[22]`,`[23]`,`[24]`,`[25]`,`[26]`,`[29]`,`[31]`) —
용도별 정리는 `docs/NOVELTY.md` §5. 참고로 `[24]`는 **Ge 2018**, 우리 UMAT의 원 모델입니다.

---

### 노벨티 포지셔닝 (1차 입고분)

| # | 파일 | 서지 | 우리와의 차이 |
|---|---|---|---|
| 01a | `[01] A continuum damage mechanics model...pdf` | **Yang & Liu**, *A CDM model for 2-D woven ox/ox CMC under cyclic thermal shocks*, **Ceram. Int. 46 (2020) 6029–6037** | 산화물/산화물 CMC, 단일 스케일 |
| 01b | `[01] yang2020 S.pdf` | **Yang & Liu**, *A continuum fatigue damage model for the cyclic thermal shocked CMC*, **Int. J. Fatigue 134 (2020) 105507** | 열충격은 "전처리"이고 손상은 기계적 피로로 부여. 다중스케일 아님, TRS 비교 없음 |
| 04 | `[04] NiU 2022 A.pdf` | **Niu, Chen, Li, Xiao, Yang, Tong, Almeida**, *A damage constitutive model for the nonlinear mechanical behavior of C/SiC during mechanical cyclical loading/unloading*, **Compos. Part A 161 (2022) 107072** | **기계적** 반복하중, 열충격 아님 |
| 05a | `[05] 3D C-SiC 물성 A05.pdf` | **Zhang, Ge, Zhang, He, Wu, Liang**, **Ceram. Int. 48 (2022) 3109–3124** | 본 연구의 기반. 단조 인장 1회, 거시 스케일 없음 |
| 05b | `[05] skinner2021 A.pdf` | **Skinner & Chattopadhyay**, *Multiscale temperature-dependent CMC damage model with thermal residual stresses and manufacturing-induced damage*, **Compos. Struct. 268 (2021) 114006** | ⚠️ **우리 노벨티에 가장 가까움.** 다중스케일 + 온도의존 + TRS + 제조유발손상. **반복 열충격과 TRS 처리방식 비교가 없다**는 점이 우리 차별점 — 반드시 정독하고 §3.1 표에 넣으세요 |

---

## 2. 추출 중 발견한 것 (원문을 봐야만 알 수 있었던 것들)

1. **Snead Eq.16의 마이너스 부호.** 자동 텍스트 추출이 상수항의 `−`를 삼켰습니다.
   그대로 쓰면 298 K에서 CTE가 5.87e-6/K(참값 2.216e-6/K의 **2.6배**)가 되고,
   TRS 전체가 틀어집니다. 페이지 이미지를 렌더링해 확인했습니다.
2. **Pradère & Sauder Table 3/4는 CTE가 아니라 열변형률(%)입니다.**
   논문 Eq.(1)의 "specific CTE" α_S(T) = [b(T)−b(T₀)]/b(T₀) 는 300 K 기준 **누적 변형률**입니다.
   CTE율로 오해하면 값이 6자리 틀립니다. 오히려 이게 더 좋습니다 — Abaqus가 원하는 게
   열변형률이므로 정확한 할선 CTE를 바로 계산할 수 있습니다.
3. **PANEX 33 ≠ T300.** 이 논문은 T300을 측정하지 않았습니다. PANEX 33이 ex-PAN에
   E=230 GPa로 T300과 같아 가장 가깝습니다(HTA 5131은 248 GPa). 이게 섬유 데이터의
   **최대 가정**입니다.
4. **섬유 CTE 불일치.** PANEX 33의 1050 °C 기준 종방향 할선 CTE는 **+1.24e-6/K**인데
   Zhang의 카드값은 **−0.30e-6/K**로 **부호가 다릅니다**. 모순은 아닙니다(Zhang은 상온값,
   이쪽은 23→1050 °C 평균). 기본값은 검증된 카드값에 맞춰 **가산 보정**했고,
   `--no-anchor`로 실측값을 그대로 쓸 수 있게 해두었습니다. **민감도 해석 필수 항목입니다.**
5. **매트릭스 CTE는 두 독립 출처가 2.3 % 내로 일치.** Snead Eq.16 적분값 4.397e-6/K
   vs Zhang 카드 4.5e-6/K. 좋은 교차검증입니다.
6. **Snead Eq.12 열전도율은 단결정 상한**(상온 293 W/m·K)입니다. 다공질 PIP 매트릭스는
   훨씬 낮습니다. 상한/민감도 끝점으로만 쓰고, 실제 k̄는 RVE 균질화나 [12]/[13]에서 얻으세요.

7. **섬유 횡방향 열전도율은 아무도 측정하지 않았습니다.** Pradère 2009는 **종방향
   확산도만** 측정합니다. 그런데 2D 직물의 **두께방향 k̄**(급랭 해석이 가장 민감한 값)는
   횡방향 섬유 k와 매트릭스 k가 지배합니다. 지어내지 않고 CSV에 **비워 두었고**,
   대안으로 **역보정**(RVE가 `[12]`/`[13]`의 실측 복합재 k̄를 재현하도록 k2를 맞춤)을
   기록해 두었습니다. 이 경우 복합재 k̄ 하나가 **검증이 아니라 입력**이 되므로 논문에
   반드시 명시해야 합니다.
8. **섬유 k∥ ≈ 60–75 W/(m·K)** 는 표준탄성률 PAN 섬유의 통상값(상온 8–10)보다 훨씬 큽니다.
   단섬유 전용 장치 측정이고, 논문은 raw PAN 섬유의 k가 온도에 따라 **증가**한다고 보고합니다.
   민감도 파라미터로 다루세요.
9. **저온 구간은 측정이 아닙니다.** 800 K 미만의 `cp`, `k1`은 "섬유 비열이 벌크 흑연에
   가깝다"는 논문 자체의 서술을 근거로 벌크 흑연으로 앵커한 값입니다. 23 °C 행이
   테이블에서 **가장 약한 열데이터**입니다.

## 3. 남은 일

1. **`[03]` zhang2012 디지타이즈** — 잔여 탄성계수 vs 사이클 수 곡선 → `data/literature/`
   (우리 거시 모델의 주 출력과 직접 대응, **최우선**)
2. **`[15]`의 XRD 검증 TRS 수치와 우리 RVE 냉각 결과 대조** — M1 직후 가능한 강력한 검증점
3. **`[35]` 고온 전단 파손 데이터** → `data/literature/` (파손기준 온도의존 검증)
4. **섬유 횡방향 k** 출처 확보 또는 역보정 결정
5. **SiC 강도 vs 온도 출처** — 현재 `fX`, `fY`, `fS` 매트릭스 계열이 전부 1.0 고정
6. **`[05b]` skinner2021 정독** — `docs/NOVELTY.md`에 아직 미반영
