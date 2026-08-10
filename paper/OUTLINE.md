# 논문 개요 (B0) — C/SiC 직조 복합재 열잔류응력·고온 인장 거동 해석

**기준 논문:** Zhang et al., *Ceramics International* 48 (2022) 3109–3124
**구성 모델:** Ge et al., *Compos. Sci. Technol.* 157 (2018) 86–98 (Ref. [17])
**이 문서의 역할:** 모든 챕터 집필 에이전트가 공유하는 단일 기준점.
장별 담당 범위(입력/출력), 기호·용어 통일 규칙을 정의한다.
챕터 초안을 쓰거나 고칠 때 이 문서와 충돌하면 **이 문서가 우선**한다.

---

## 1. 장 구성과 담당 범위

| 장 | 제목 (가제) | 핵심 내용 | 주 참조 소스 | 상태 |
|---|---|---|---|---|
| 1 | 서론 및 연구동향 | C/SiC 복합재 배경, 열잔류응력 문제, CDM/RVE 연구동향, 연구 목적 | Zhang 2022 서론부, 일반 문헌 | 초안 대상 (B2) |
| 2 | 이론 및 손상 모델 | Ge 2018 구성방정식 (Eqs. 1–33), Hashin/von Mises 개시, 지수 손상발전, 균열대 정규화, Chamis/Schapery 균질화 | `verification/VERIFICATION_REPORT.md` §2–3 | 초안 대상 (B3) |
| 3 | 해석 방법 및 결과 | RVE 모델, 3-스텝 해석절차, 온도별 σ–ε 곡선, Table 3 비교 | `abaqus/*.inp`, `calibration/` 산출물 | **보정 완료 후** (B5) |
| 4 | 검증 및 보정 | 물성/수식/절차 3단 검증, 미공개 파라미터 보정 전략 (Stage A–E) | `VERIFICATION_REPORT.md`, `CALIBRATION_GUIDE.md` | 초안 대상 (B4) |
| 5 | 결론 | 요약, 검증 한계, 후속 연구 (3D C-SiC 확장) | 1–4장 완성 후 | 3장 이후 (B6) |

### 장 간 인터페이스 (누가 무엇을 넘기는가)

- 1장 → 2장: "왜 CDM + RVE인가"의 논리. 2장은 모델 선택의 정당화를 반복하지 않는다.
- 2장 → 3장: 식 번호 체계(아래 §3). 3장은 수식을 재기술하지 않고 번호로 인용한다.
- 4장 → 3장: 보정된 최종 파라미터 표는 4장이 아니라 **3장**에 싣는다.
  4장은 "어떻게 보정했는가(방법)"만, 3장은 "그 결과 값과 곡선"을 담당.
- 5장은 새로운 수치를 도입하지 않는다 (모든 수치는 3·4장에서 인용).

---

## 2. 기호 사전 (Symbol dictionary)

챕터 전체에서 아래 표기를 강제한다. 첨자 순서: (재료상)(방향)(하중부호).

### 2.1 탄성·열 물성

| 기호 | 의미 | 단위 | 비고 |
|---|---|---|---|
| $E_1, E_2, E_3$ | 얀 종/횡방향 탄성계수 | MPa | 1 = 섬유 종방향 |
| $\nu_{12}, \nu_{13}, \nu_{23}$ | 포아송비 | – | |
| $G_{12}, G_{13}, G_{23}$ | 전단탄성계수 | MPa | |
| $E_m, \nu_m, G_m$ | 매트릭스(SiC) 탄성 물성 | MPa, – | Zhang Table 2 |
| $\alpha_1, \alpha_2, \alpha_3$ | 얀 열팽창계수 | /K | Schapery |
| $\alpha_m$ | 매트릭스 열팽창계수 | /K | 4.5×10⁻⁶ |
| $V_f$ | 얀 내 섬유 체적분율 | – | 0.792 (검증값) |
| $T_0$ | 무응력(공정) 온도 | °C | 1050 |

### 2.2 강도·손상 파라미터

| 기호 | 의미 | 단위 | 카드 슬롯 |
|---|---|---|---|
| $X_t, X_c$ | 얀 종방향 인장/압축 강도 | MPa | yarn 11–12 |
| $Y_t, Y_c$ | 얀 횡방향 인장/압축 강도 | MPa | yarn 13–14 |
| $S_{12}, S_{13}, S_{23}$ | 얀 전단 강도 | MPa | yarn 15–17 |
| $X_{m,t}, X_{m,c}$ | 매트릭스 인장/압축 강도 | MPa | matrix 4–5 |
| $d_I$ | 모드 $I$ 손상변수 ($I$=1t,1c,2t,2c) | – | SDV |
| $r_I$ | 손상 개시 지표 (Hashin/von Mises) | – | $r_I \ge 1$에서 손상 |
| $A_I$ | 지수 손상발전 계수 | – | yarn 18–21 |
| $G_{f,I}$ | 파괴에너지 (균열대 정규화) | N/mm | yarn 32–35, matrix 15–16 |
| $l_c$ | 특성요소길이 (crack band) | mm | Abaqus CELENT |
| $X_{PO}, r_F, K_1$ | Eq.18 혼합법칙 (풀아웃 응력, 전이지표, 연화기울기) | MPa, –, MPa | yarn 36–38 |
| $\sigma_{Y0}$ (SY0) | 매트릭스 초기 항복응력 | MPa | matrix 17 |
| $H_{iso}$ (HISO) | 등방 경화계수 | MPa | matrix 18 |
| $\eta$ | 점성 정규화 계수 | – | 수렴 안정화 |

### 2.3 응력·변형률

| 기호 | 의미 |
|---|---|
| $\boldsymbol{\sigma}, \tilde{\boldsymbol{\sigma}}$ | 명목응력 / 유효응력 ($\tilde\sigma = C_0 : \varepsilon^e$) |
| $\varepsilon^e, \varepsilon^p, \varepsilon^{th}$ | 탄성 / 소성 / 열 변형률 (매트릭스: $\varepsilon = \varepsilon^e + \varepsilon^p + \varepsilon^{th}$) |
| $\bar\sigma_{xx}, \bar\varepsilon_{xx}$ | RVE 거시(균질화) 응력·변형률 |
| $\sigma_{ult}$ | 극한 인장강도 |
| $\sigma_{vM}$ | von Mises 등가응력 |

### 2.4 용어 통일

| 사용 (O) | 금지 (X) |
|---|---|
| 얀 (yarn) | 다발, 토우 (혼용 금지 — 최초 1회 "yarn(토우)" 병기 가능) |
| 매트릭스 (matrix) | 기지, 모재 |
| 열잔류응력 (thermal residual stress) | 잔류열응력 |
| 손상변수 $d$ | 손상도, 손상률 |
| 균열대 정규화 (crack-band regularization) | 크랙밴드 |
| 대표체적요소 (RVE) | 단위셀 (unit cell은 기하 설명에만) |
| 보정 (calibration) | 튜닝, 피팅 |

---

## 3. 식 번호 규칙

- 본 논문의 식 번호는 장별 일련번호 (예: 식 (2.5)).
- 원 논문 수식 인용 시: "Ge (2018) 식 (17)" / "Zhang (2022) 식 (11)" 형식으로 출처 명시.
- 2장이 식 번호의 단일 소유자. 3·4장은 2장의 번호만 인용.

## 4. 수치 인용 규칙 (정직성)

- **검증된 값** (물성, Chamis 재현치)은 `VERIFICATION_REPORT.md` §2 수치를 그대로 인용.
- **보정 대상 값** (Yt, S, X_PO, SY0 등)은 반드시 "보정 시작값" 또는 "보정값"으로
  명시하고, 논문(Zhang/Ge)이 발표한 값처럼 기술하지 않는다.
- Table 3 목표: 128.45 / 179.42 / 199.15 MPa (23/500/1000 °C, 논문 시뮬레이션).
  실험값 116.17±8.78 / 160.19±14.83 / 173.28±12.94는 참고 밴드로만.
- 해석 결과 수치는 `calibration/ledger.json`의 최종 채택 iteration에서만 가져온다.

## 5. 파일 규약

```
paper/
  OUTLINE.md        이 문서 (기준점)
  ch1_intro.md      1장 서론 및 연구동향
  ch2_theory.md     2장 이론 및 손상 모델
  ch3_results.md    3장 해석 방법 및 결과  (보정 후 작성)
  ch4_verification.md  4장 검증 및 보정
  ch5_conclusion.md 5장 결론              (3장 후 작성)
calibration/
  ledger.json       보정 원장 (상태 객체)
  make_cards.py     파라미터 → 3온도 V2_0 덱 생성 (A0 노드)
  evaluate.py       곡선 → 지표·손실·게이트 판정 (A3/A4 노드)
```
