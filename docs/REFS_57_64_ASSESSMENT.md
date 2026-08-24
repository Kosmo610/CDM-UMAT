# `refs/[57]`–`[64]` 검토 — 무엇에 쓸 수 있는가

> **작성 2026-08-06.** 8편 전문(텍스트 추출본)을 읽고, **우리 논문에서 어디에
> 쓸 수 있는지**를 기준으로 정리하였다. 서지·수치는 전부 PDF에서 직접 읽었으며
> 판정기는 `python3 data/literature/refs_audit.py --check`.
>
> 결론부터 — **8편 중 4편이 지금 당장 논문을 바꾼다.** 특히 `[59]`는 제가 이전에
> 보낸 판단 하나를 **뒤집습니다**(§6).

---

## 0. 목록

| # | 서지 | 성격 | 우선순위 |
|---|---|---|---|
| **[57]** | Van Paepegem, Degrieck, De Baets, *Finite element approach for modelling fatigue damage in fibre-reinforced composite materials*, **Compos. Part B 32 (2001) 575–588** | **`[S8]` 원문** — cycle jump | ② |
| **[58]** | Cojocaru, Karlsson, *A simple numerical method of cycle jumps for cyclically loaded structures*, **Int. J. Fatigue 28 (2006) 1677–1689**, doi:`10.1016/j.ijfatigue.2006.01.010` | 신규 — **적응형** cycle jump | **①** |
| **[59]** | Camus, Guillaumat, Baste, *Development of damage in a 2D woven C/SiC composite under mechanical loading: I. Mechanical characterisation*, **Compos. Sci. Technol. 56 (1996) 1363–1372** | 신규 — **우리 아키텍처의 손상 발달 실측** | **①** |
| **[60]** | Li, Jiao, Wang 등, *Damage characteristics and constitutive modeling of the 2D C/SiC composite: **Part II** — Material model and numerical implementation*, **Chin. J. Aeronaut. 28(1) (2015) 314–326**, doi:`10.1016/j.cja.2014.10.027` | 신규 — **`refs/[28]`의 짝** | **①** |
| **[61]** | Mei, Cheng, Zhang, Luan, Zhang, *Behavior of 2D C/SiC composites subjected to thermal cycling in controlled environments*, **Carbon 44 (2006) 121–127**, doi:`10.1016/j.carbon.2005.07.003` | 신규 — **열사이클 실측 + 물성표** | **①** |
| **[62]** | Baste, *Inelastic behaviour of ceramic-matrix composites*, **Compos. Sci. Technol. 61 (2001) 2285–2297** | 신규 — 초음파 이방성 손상 식별 | ③ |
| **[63]** | Mei, Cheng, Zhang, Xu, *Modeling the effects of thermal and mechanical load cycling on a C/SiC composite in oxygen/argon mixtures*, **Carbon 45 (2007) 2195–2204**, doi:`10.1016/j.carbon.2007.06.051` | 신규 — 산화 사이클 **모델** | ② |
| **[64]** | Wu, Wang, Qi, Luo, Luo, Gao, Song, *Predictive constitutive modelling of oxidation-induced degradation in 2.5D woven C/SiC composites*, **Materials 19(2) (2026) 307**, doi:`10.3390/ma19020307` | 신규 — **최신 경쟁 논문** | ② |

---

## 1. `[61]` Mei 2006 — **표 하나가 여러 구멍을 메운다**

Table 1(as-received 2D C/SiC, CVI)이 우리가 따로 찾아다니던 값을 한 표에 준다.

| 항목 | 값 | 우리 쓰임 |
|---|---|---|
| 밀도 | **2.0** ×10³ kg/m³ | 밀도 역산의 세 번째 독립 확인 (refs/[10]·[28]과 일치) |
| 탄성계수 | **70 GPa** | ⚠️ 아래 §1.1 |
| 강도 | **248 MPa** | 복합재 강도 대조점 |
| 포아송비 | 0.32 | 균질화 검증 |
| **공극률** | **13 %** | 공극률 논쟁의 독립 값 |
| **CTE ×10⁻⁶/°C** | 600 °C **4.6** / 800 °C **6.1** / 1000 °C **5.2** / 1200 °C **5.4** | **복합재 $\bar\alpha(T)$ 4점 — 제4장 균질화 검증** |

**시험 조건:** 700 ↔ 1200 °C, $\Delta T \approx 500$ °C, 주기 120 s
(저온 30 s 유지 → 60 s 승온 → 고온 30 s 유지 → 급랭).

**결과:** 50회 급랭 후 잔여 인장강도 —
습윤산소 **88.92 %**, 아르곤 **98.90 %**, 건조산소 **96.46 %**, 수증기 **95.82 %**.
**100회 초과** 습윤산소에서 **86.69 %**.

> **`refs/[43]`과의 관계 — 중복이 아니다.** [43](*J. Mater. Sci.* 40 (2005) 4261)이
> 같은 50회 수치를 보고하지만, [61]은 **100회 이상까지 연장**하고 **전기저항 실시간
> 계측**과 **외부 하중 중첩**을 추가한다. 같은 그룹의 후속 실험이며 둘 다 인용 가능하다.
> 다만 **50회 수치를 두 번 세면 안 된다** — 같은 데이터다.

### 1.1 ⚠️ 탄성계수 70 GPa — 이것이 a2가 말한 "Mei의 할선"이다

`data/properties/m6_calibration.py`가 *"the comparison modulus is Yang's INITIAL,
not Mei's chord — 172.7 vs 70 GPa"*라고 적어 둔 그 70 GPa의 **1차 출처가 이제 있다.**
[61] Table 1은 이것을 그냥 "Modulus"라고만 적고 초기접선인지 할선인지 밝히지 않는다.

**같은 CVI 2D C/SiC, 같은 밀도 2.0인데 두 측정이 1.84배 어긋난다:**
refs/[10] Yang 128.7 GPa vs refs/[61] Mei 70 GPa.
어느 쪽을 대조 기준으로 삼느냐가 M6 판정을 통째로 바꾸므로 **논문에 명시해야 한다.**

**→ 쓸 곳:** 제4장 균질화 검증(CTE 4점 · 강도 · 공극률), 제6장 사이클 데이터,
그리고 **제4장에 "대조 기준 모듈러스 선택" 을 한 문단으로 명시**.

---

## 2. `[60]` Part II — **`refs/[28]`의 짝이고, 우리 모델과 가장 가깝다**

`refs/[28]`(Part I, 실험)은 C3의 근거로 이미 쓰고 있다. **[60]은 그 모델링 짝**이며
2D 평직 C/SiC용 **UMAT**이다. 초록이 밝히는 구성:

- CDM + 소성 + **단방향(unilateral) 거동**
- **손상 비활성화를 연속함수로** 기술 (스위치가 아님)
- **이축 압축이 단축 압축보다 비활성화가 빠르다**
- 손상 모드 간 결합, 압축응력이 전단손상을 **저해**하는 효과
- Tsai–Wu로 강도 판정

> 본문 인용: *"the tension and/or shear damage generated in the loading history will
> be gradually deactivated during compression, and the **biaxial compression stresses
> yield a faster damage deactivation rate than the uniaxial** compression condition."*

**우리에게 두 방향으로 작용한다.**

**(A) C3를 강화한다.** 제1장 C3는 *"강성 회복 기구가 이축 압축에서 가속된다"*를
`[28]`(실험)에만 기대고 있었다. 이제 **같은 그룹의 모델링 논문이 그것을 정식화까지
했다**는 것을 보일 수 있다. 급가열 반사이클의 표면 응력이 이축 압축이라는 우리 논지가
실험 + 모델 양쪽에서 받쳐진다.

**(B) 우리 `HCLO`를 다시 봐야 한다.** 우리 균열 닫힘은 **스칼라 계수 하나**로
$d_{\text{eff}} = d(1-H_{clo})$ 형태다. [60]은 **연속함수 + 응력상태 의존 속도**다.
즉 우리 구현은 [60]보다 단순하다. 두 선택지:
1. 한계로 명시한다 — *"본 연구는 균열 닫힘을 상수 계수로 근사하며, 이축/단축
   구분은 [60]의 범위이다"*
2. `HCLOS`(전단용)를 도입하며 이축 의존까지 넣는다 → **코드 영역, a2 판정**

**→ 쓸 곳:** 제2장 §2.8(선행연구 위치), 제1장 C3 근거 보강, 제3장 §3.4.2 한계 서술.
**그리고 제2장 참고문헌에서 `[28]`을 "Part I"로 명시**해야 한다 — 지금은 Part I만
있고 Part II가 있는 줄 모르게 적혀 있다.

---

## 3. `[58]` + `[57]` — cycle jump의 **방법 출처**와 **적응 제어**

`[57]`은 `[S8]`의 원문이다(고정 간격 cycle jump). **`[58]`이 그보다 낫다:**

> *"a control function that **automatically monitors the length of the cycle jump**
> to ensure a realistic solution"*
> *"the cycle jump solution **replicates the true solution**"*

즉 **점프 폭을 자동으로 조절**하고, 전 사이클 계산과 대조해 검증까지 했다.
우리 cycle jump는 지금 **간격이 고정**이며 오차를 사후에 확인할 뿐이다.

**→ 쓸 곳:** 제3장 cycle jump 검증 절의 **방법 인용**, 그리고 적응 제어 도입 여부는
**a2 판정**. 최소한 *"고정 간격을 썼고 적응 제어는 [58]의 방식이 있다"*로 한계를 적을 수 있다.

---

## 4. `[59]` Camus 1996 — **우리 아키텍처의 손상 발달을 실측한 편**

CVI 2D 직조 C/SiC, 상온 인장·압축. 우리가 계속 찾던 종류의 데이터다.

- **인장:** 다단계 손상 — 횡방향 기지 미세균열 → 다발/기지 및 다발간 박리 →
  **열잔류응력 해방**. 거동은 *"damageable-elastic with respect to a **fictitious
  thermal-stress-free origin of the stress/strain axis lying in the compression
  domain**"*.
  → **TRS가 응력–변형률 원점을 압축 쪽으로 밀어 놓는다**는 것을 실측으로 보인 문장이다.
  우리 C1(TRS 처리 방식)의 물리적 근거로 그대로 쓸 수 있다.
- **압축:** *"after an initial stage involving **closure of the thermal microcracks
  present from processing**, the composite displayed a linear-elastic behavior until
  failure"*
  → **제조 단계에서 이미 열균열이 존재하고, 압축이 그것을 닫는다.** C3의 직접 근거.
- **정량화:** 미시적으로 **평균 횡방향 균열 간격 감소**, 거시적으로 **종방향 탄성계수와
  면내 포아송비 감소**로 손상을 측정. (균열 간격은 5개 다발에서 15 mm 구간 평균)

**→ 쓸 곳:** 제2장 §2.2(손상 기구 순서), 제1장 C1·C3 근거, 제4장 RVE 손상 분포 대조.

---

## 5. `[63]` Mei 2007 + `[64]` Wu 2026 — 산화 사이클

**`[63]`**은 O₂/Ar 하 **열 + 기계 사이클**의 변형률 응답을 세 성분으로 분해한다:
열변형률(∝T) + 기계변형률(∝σ) + **기저변형률(손상 의존)**. 기저변형률의 두 기구를
명시한다 — (a) 기지 미세균열 + 섬유 박리·미끄럼·파단(물리), (b) **섬유 산화에 따른
종방향 컴플라이언스 증가**(화학).

> 이것이 **우리 사이클 손상 지수 부호의 물리적 해석**과 정확히 대응한다.
> 우리는 실리카 밀봉(>1000 °C, 포화)과 밀봉 실패(600–1000 °C, 가속)를 구분한다고
> 주장하는데, [63]은 그 화학 기구를 변형률 성분으로 분리해 놓았다.
> **다만 [63]은 Zhang [5]의 참고문헌 [36]이기도 하다** — 우리 기지 카드가 빌려온
> 세 논문 중 하나다. 인용할 때 그 사실을 알고 써야 한다.

**`[64]`**는 **2026년 최신 경쟁 논문**이다. 2.5D 직조 C/SiC의 산화 유발 열화를
CT 기반 RVE + 메소/미시 이중 스케일 + 계면 미끄럼으로 모델링하고 **700 / 900 / 1100 °C**
에서 검증했다.

**노벨티 판정 — 우리와 겹치지 않는다. 단 명시해야 한다.**
| | [64] | 본 연구 |
|---|---|---|
| 아키텍처 | **2.5D** 직조 | 2D 평직 |
| 구동 | **산화**(등온 노출) | **반복 열충격**(온도구배·과도) |
| 하중 | 하중–제하 사이클 | 정진폭 열사이클 |
| TRS | 변수 아님 | **처리 방식 3케이스 비교가 주 주장** |

**→ 쓸 곳:** 제2장 §2.4·§2.5.4 산화 기구, 제2장 §2.8 최신 선행연구 위치.

---

## 6. ⚠️ 정정 — `[59]`가 제 이전 판단을 뒤집는다

`a1-0012`에서 저는 **"기지 탄성계수 350 GPa 는 이상치이고, 두 독립 경로가 모두
더 낮은 값을 가리킨다"**고 보냈습니다. **[59]가 그 판단을 약화시킵니다.**

Camus 1996의 구성재 표(ex-PAN 탄소섬유 + CVI SiC 기지):

| | ρ (×10³ kg/m³) | E (GPa) | ν | CTE (×10⁻⁶/K) |
|---|---|---|---|---|
| C 섬유 | 1.8 | 230 | 0.3 | 축 0 / 반경 10 |
| **SiC 기지** | **3.2** | **350** | **0.2** | **4.6** |

우리 카드는 **350 / 0.20 / 4.5e-6**. **완전히 독립한 1996년 프랑스 그룹이 세 값 모두
사실상 동일하게 쓴다.** 따라서 350 GPa 는 Zhang [5] 만의 값이 아니다.

**수정된 그림:**

| 출처 | 기지 E | 성격 |
|---|---|---|
| Snead `refs/[06]` | 460 GPa | 치밀 CVD SiC 상한 |
| **우리 카드 / Camus `[59]`** | **350 GPa** | 널리 쓰이는 CVI SiC 값 (독립 2건) |
| 밀도 역산 (a1-0009) | 143 GPa | 공극을 반영한 **유효** 값 |
| `refs/[15]` (2026) | 80 GPa | 공극을 반영한 **유효** 값 |

**정직한 결론:** 350 이 틀린 게 아니라, **두 학파가 서로 다른 것을 "기지 탄성계수"로
부르고 있다** — 고체 SiC 상(phase)의 값(350–460) vs 공극이 이미 깎아낸 유효값(80–143).
우리 모델은 공극을 **기하로 표현하지 않으므로**(RVE에 공극이 없다) **유효값 쪽을
써야 정합**이지만, 그러면 Zhang [5] 재현이 깨진다. 이것이 진짜 딜레마이며,
"카드가 이상치"라는 제 서술은 **과했습니다.**

---

## 7. 지금 해야 할 일 (우선순위)

1. **제2장 참고문헌의 `[28]`을 "Part I"로 명시하고 `[60]`을 Part II로 나란히 둔다.**
   짝이 있는 줄 모르고 인용하는 상태다.
2. **`[61]` CTE 4점을 제4장 $\bar\alpha(T)$ 검증표에 넣는다.** 지금 `refs/[11]` 하나뿐이다.
3. **대조 기준 모듈러스(128.7 vs 70 GPa)를 제4장에 명시한다.** M6 판정이 여기 걸린다.
4. **`HCLO`의 단순화를 제3장에 한계로 적는다** — [60]과의 차이.
5. **기지 E 딜레마(§6)를 a2와 매듭짓는다.** 350을 쓰면 Zhang 재현, 유효값을 쓰면 밀도 정합.
