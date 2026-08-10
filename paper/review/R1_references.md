# R1 참고문헌 감사 보고서 (reference audit)

**감사 대상:** `paper/ch1_intro.md`, `paper/ch2_theory.md`, `paper/ch4_verification.md` (기준: `paper/OUTLINE.md`)
**감사 근거:** 저장소 PDF 3종 실측(1–5면 및 참고문헌부 추출), `verification/VERIFICATION_REPORT.md`, `README.md`, `verification/CALIBRATION_GUIDE.md`, `calibration/make_cards.py`, git 이력, WebSearch(3건 확인)
**감사일:** 2026-08-10 / 감사자: R1 (reference auditor)

---

## 요약

저장소의 PDF 3종은 **기준 논문(Zhang 2022 Ceram. Int.)도, 구성 모델 논문(Ge 2018 CST 157)도 아니며**, 후속 3D C-SiC 연구용 별개 문헌 3편(Compos. Part A 2026 / CST 2025 / JMRT 2024)이다 — 즉 본 논문의 두 핵심 근거 문헌은 저장소에 없어(git 이력에도 부재) 원문 대조가 불가능한 상태다. 두 핵심 문헌의 서지 자체는 실재함을 확인했다: Zhang 2022는 저장소 PDF 2편의 참고문헌에 원문 표기로 등장하고, Ge 2018은 WebSearch로 제목·권·쪽·DOI가 확인된다. 챕터 감사 결과 **BLOCKER 1건**(ch1:27 — Ge 2018을 "세라믹기지 직조 복합재" 논문으로 오기술; 실제는 3차원 **편조(braided)** 복합재), **MAJOR 16건**(미해결 `[ref 필요]` 9건 + Chamis/Schapery·Bažant–Oh·점성정규화·Xia·TexGen 서지 누락 + 출전 귀속 의심 3건 + 원문 PDF 미보유 1건), **MINOR 6건**(식 번호 귀속 불일치, 인용 스타일 등)을 확인했다. Zhang 2022·Ge 2018 원문 PDF 확보가 최우선이며, 확보 전까지는 절·표 단위의 세부 귀속("Ge §3.2 권고", "Ge Table 3의 G_f,1c" 등)을 완화하거나 검증 표시를 남겨야 한다. 아래에 두 챕터 수정 없이 바로 쓸 수 있는 참고문헌 목록 초안(25건, confidence 표기)을 제시한다.

---

## 1. 저장소 PDF 3종의 실체

세 파일 모두 실측 확인(1–2면 텍스트 + PDF 메타데이터). **셋 중 어느 것도 Ge et al. CST 157 (2018)이나 Zhang et al. Ceram. Int. 48 (2022)이 아니다.**

| 파일 | 실제 논문 | 저자 | 저널·서지 | DOI | 내용 요약 |
|---|---|---|---|---|---|
| `[15] 3D C-SiC 물성 A01.pdf` (15면) | *Quantification of thermal residual stresses and their effects on the mechanical behavior of 3D C/SiC composites* | S. Zhang, D. Zhang, J. Zhou, F. Du, K. Guan, Z. Guan, W.J. Cantwell | Compos. Part A **207** (2026) 109796 | 10.1016/j.compositesa.2026.109796 | 3D **편조** C/SiC의 열잔류응력(TRS) 정량화: 멀티스케일 FE+이론 모델+XRD 검증. 메소스케일 매트릭스 TRS 축방향 114.7/횡방향 40.3 MPa, 얀 −68.7/−23.9 MPa. 인장에서는 TRS가 강도 저하, 압축에서는 강도 증가. Zhang 2022를 자기 참고문헌 [26]으로 인용 |
| `[16] 3D C-SiC 물성 A02.pdf` (11면) | *Multi-scale characterisation and damage analysis of 3D braided composites under off-axis tensile loading* | X. Song, J. Zhou, J. Wang, L. Bai, X. Yang, J. Xue, D. Zhang, S. Zhang, X. Chen, Z. Guan, W.J. Cantwell | Compos. Sci. Technol. **261** (2025) 111017 | 10.1016/j.compscitech.2024.111017 | 3D 편조 복합재(수지계, **C/SiC 아님**)의 off-axis(0/45/60/90°) 인장: DIC·SEM·μCT, 강성 예측 모델, 기공 포함 FE, UMAT. Zhang 2022 인용 없음. Chamis[38]·Duvaut-Lions 정규화[42] 인용 |
| `[17] 3D C-SiC 물성 A03.pdf` (19면) | *Revealing thermal shock behaviors and damage mechanism of 3D needled C/C–SiC composites based on multi-scale analysis* | P. Zhang, L. Zhu, Y. Tong, Y. Li, Y. Xing, H. Lan, Y. Sun, X. Liang | J. Mater. Res. Technol. **29** (2024) 2016–2034 | 10.1016/j.jmrt.2024.01.260 | 3D 니들펀치 C/C–SiC의 열충격 거동 멀티스케일 해석(온도·사이클), 불활성 분위기 실험 검증. Zhang 2022를 자기 참고문헌 [19]로 인용. Xia 주기경계 [31][32]·Chamis[6]·Hashin[35] 인용 |

**주의 (파일명 번호 충돌):** `README.md`/`VERIFICATION_REPORT.md`의 "Ge 2018 (Ref. [17])"은 **Zhang 2022 논문 내 참고문헌 번호 [17]**을 뜻한다. 저장소 파일명의 `[17]`은 사용자의 개인 문헌 번호로서 **전혀 다른 논문**(P. Zhang, JMRT 2024)이다. 이 충돌은 후속 작업자가 "[17] pdf = Ge 2018"로 오인할 위험이 크므로 파일명 변경 또는 README 명기를 권고한다.

**결론:** Zhang 2022와 Ge 2018 원문 PDF는 저장소에 없다(git 이력 전수 확인: PDF 추가 커밋은 `ed8d55f`([15]), `5ae1b08`([16],[17])뿐). `VERIFICATION_REPORT.md` §5의 "Ge 2018 ... was obtained"는 저장소 밖에서 열람했다는 의미로 보이며, 현 저장소만으로는 두 문헌의 표·식 번호·절 번호 수준 주장을 재검증할 수 없다. → **원문 2편 확보를 MAJOR 액션으로 등재** (감사표 P-1).

두 핵심 문헌의 실재는 다음으로 교차 확인했다.
- Zhang 2022: PDF [15]의 ref [26], PDF [17]의 ref [19]에 원문 표기 — "Zhang Q, Ge J, Zhang B, He C, Wu Z, Liang J. Effect of thermal residual stress on the tensile properties and damage process of C/SiC composites at high temperatures. Ceram Int 2022;48(3):3109–24." + [ScienceDirect 수록 확인](https://www.sciencedirect.com/science/article/abs/pii/S0272884221032235)
- Ge 2018: WebSearch — [Semantic Scholar](https://www.semanticscholar.org/paper/A-coupled-elastic-plastic-damage-model-for-the-of-Ge-He/21a44d3020414ff8e46a3c9f3e6393972dd1c3e3), [ScienceDirect PII S0266353817322145](https://www.sciencedirect.com/science/article/abs/pii/S0266353817322145): *A coupled elastic-plastic damage model for the mechanical behavior of three-dimensional (3D) braided composites*, Compos. Sci. Technol. 157 (2018) 86–98, DOI 10.1016/j.compscitech.2018.01.027.

---

## 2. 인용 감사표

판정 기준 — **BLOCKER**: 주장–출전 불일치 또는 날조로 보일 수 있는 인용 / **MAJOR**: 하중을 받는(load-bearing) 주장의 참고문헌 부재·귀속 미확인 / **MINOR**: 형식·배치. "보고서"는 `verification/VERIFICATION_REPORT.md`(원문을 인용·발췌한 유일한 저장소 내 증거)를 뜻한다. R-번호는 §4 참고문헌 초안 번호.

### ch1_intro.md

| 위치 | 인용 | 판정 | 근거·수정안 |
|---|---|---|---|
| ch1:5 (a) | `[ref 필요]` — CMC 배경(저밀도·내열성 등) | **MAJOR** | R1(Naslain 2004) + R2(Krenkel 2005) 제안 |
| ch1:5 (b) | `[ref 필요]` — TPS·극초음속·1000 °C 이상 적용 | **MAJOR** | R3(Glass 2008) + R4(Schmidt 2004) 제안 |
| ch1:5 (c) | `[Zhang 2022]` — 대상 재료 = 2D 평직 C/SiC | OK | README·보고서와 일치. 최종 번호인용 전환은 공통 MINOR-6 |
| ch1:11 (a) | `[ref 필요]` — CVI/MI/PIP 공정 분류 | **MAJOR** | R1(Naslain 2004; CVI·공정 개괄) + 선택 R8(Xu 1998, CVI C/SiC) |
| ch1:11 (b) | `[ref 필요]` — PIP 공정 설명·널리 사용 | **MAJOR** | R6(Colombo 2010, polymer-derived ceramics 총설) + R7(Rak 2001, PIP C/SiC) |
| ch1:11 (c) | `[Zhang 2022]` — PIP, 공정온도 1050 °C | OK | 보고서 §4 (`*Expansion, zero=1050`, "PIP process temperature 1050 °C") 일치 |
| ch1:13 | `[Zhang 2022]` — CTE 불일치 → 열잔류응력 | OK | 보고서·OUTLINE과 일치 |
| ch1:17 | `[Zhang 2022]` ×2 — Table 3 시뮬 128.45/179.42/199.15, 실험 116.17±8.78/160.19±14.83/173.28±12.94 | OK | OUTLINE §4·보고서 §5와 수치 완전 일치 |
| ch1:19 | `[Zhang 2022]` — 열잔류응력 완화 → 고온 강도 증가 메커니즘 | OK | 보고서 §6의 온도 추세 논리와 일치 |
| ch1:23 (a) | `[ref 필요]` — CDM 점진손상 해석이 주류 | **MAJOR** | R9(Matzenmiller 1995) + R13(Lomov 2007) 제안 |
| ch1:23 (b) | `[ref 필요]` — Hashin형 개시 + 손상발전 | **MAJOR** | R10(Hashin–Rotem 1973) + R11(Hashin 1980) 제안 |
| ch1:23 (c) | `[ref 필요]` — 균열대 정규화 | **MAJOR** | R12(Bažant–Oh 1983; WebSearch로 서지 확인) 제안 |
| ch1:25 (a) | `[ref 필요]` — RVE 주기경계·균질화 멀티스케일 | **MAJOR** | R14(Xia 2003) + R15(Xia 2006) 제안 — PDF [17] 참고문헌부에서 원문 표기 확보 |
| ch1:25 (b) | `[ref 필요]` — Chamis 강성·Schapery 열팽창 | **MAJOR** | R16(Chamis 1984 또는 R16′ 1987) + R17(Schapery 1968) 제안 |
| ch1:27 (a) | `[Ge 2018]` — "Ge 등은 **세라믹기지 직조 복합재**를 대상으로 … CDM 구성 모델을 제안" | **BLOCKER** | **주장–출전 불일치.** Ge 2018의 실제 제목은 "*A coupled elastic-plastic damage model for the mechanical behavior of three-dimensional (3D) **braided** composites*" — 대상은 3차원 **편조**(braided) 복합재이며(매트릭스에 von Mises 탄소성을 쓰는 수지계 모델), 세라믹기지도 '직조(woven)'도 아님. 수정안: "Ge 등은 3차원 편조 복합재를 대상으로 … 제안하였고, Zhang 등은 이를 평직 C/SiC에 채택하였다". 모델 내용 기술(얀 Hashin+지수발전, 매트릭스 von Mises 탄소성–손상, 균열대)은 보고서 §3과 일치하므로 그대로 유지 가능 |
| ch1:27 (b) | `[Zhang 2022]` — RVE 냉각→온도별 인장 순차 해석 | OK | 보고서 §4 일치 |
| ch1:33 | `[Zhang 2022]`, `[Ge 2018]` — 연구 목적 서술 | OK | — |

### ch2_theory.md

| 위치 | 인용 | 판정 | 근거·수정안 |
|---|---|---|---|
| ch2:3 | Zhang et al. (2022) / Ge et al. (2018) 소개 | OK | — |
| ch2:7 | Zhang (2022) Table 2 — E_m 350 GPa, ν 0.20, 310 MPa, 4.5×10⁻⁶, T₀=1050 °C | OK | 보고서 §2.1과 완전 일치 |
| ch2:9, 11–23 | Chamis·Schapery 관계식 (2.1)–(2.6) — **서지 인용 없음** | **MAJOR** | 식 최초 제시 지점에 R16(Chamis)·R17(Schapery) 서지 필수. Zhang 원문도 자체 [32]=Chamis, [33]=Schapery를 인용(보고서 §2.2 발췌). 식 자체는 보고서 §2.2 수록 형태와 동일 |
| ch2:25 | 수치(E₁=254,967 … 0.142 %) + "(Zhang 2022 §3.2.3)" 온도독립 가정 | OK(주의) | 수치는 보고서 §2.2 표와 동일. §3.2.3 귀속은 보고서 경유 — 원문 확보 후 재확인(P-1) |
| ch2:31 | "Ge (2018) 식 (2)–(4)" — σ=C(d):εᵉ, σ̃=C₀:εᵉ | MINOR | 보고서 §3은 동일 내용을 Ge **(2)–(3)**으로 매핑. 원문 대조로 번호 확정(P-1) |
| ch2:35 | "Ge (2018) 식 (3)" — 전단 결합손상 d₄,d₅,d₆ | MINOR | ch2:31의 (2)–(4) 범위와 중복 귀속. 보고서상 (2)–(3)은 응력 관계 → 결합손상의 실제 식 번호 원문 확인 필요 |
| ch2:43 | "Zhang (2022) 식 (11)–(14), α=β=1" — 3D Hashin | OK | 보고서 §3 매핑((11)~(14), α=β=1)과 일치 |
| ch2:57 | X_t=V_f·3580=2835, X_c=V_f·2470=1956 (T300, Ge Table 2=Zhang Table 1); Y_t 등 "논문 미공개" | OK | 보고서 §5 update("Ge Table 2 … Xt=3580, Xc=2470", V2_0 시작값 2835/1956) 및 §5 표 항목 1("not listed")과 일치 |
| ch2:61 | "Zhang (2022) 식 (17)" — 지수형 손상발전 | OK | 보고서 §3 일치 |
| ch2:65 | "Ge (2018) 식 (19)–(21)" — 균열대 정규화 | OK(+권고) | 보고서 단위테스트 라벨 "Eq.19-21 crack-band"와 일치. 단, 개념 원전 R12(Bažant–Oh)를 함께 인용할 것(ch1:23c와 동일 건) |
| ch2:69 | "Ge (2018) Table 3의 **G_f,1t = G_f,1c = 12.5** N/mm" | **MAJOR** | **귀속 미확인.** 보고서가 Ge Table 3에서 확인해 준 값은 G_f,1t=12.5(및 G_f,2t=1.0)뿐. G_f,1c=12.5까지 Ge Table 3 값이라고 쓰면 출전 과잉귀속 위험. 수정안: "G_f,1t=12.5는 Ge (2018) Table 3, **G_f,1c는 동일값으로 둔 본 연구의 가정(시작값)**" — 또는 원문 Table 3 확인(P-1) 후 확정. ch4:80은 1t만 귀속하고 있어 올바름(챕터 간 불일치이기도 함) |
| ch2:73–79 | "Zhang (2022) 식 (18)" 혼합법칙 + "Ge (2018) 식 (16)–(17)" 보조변수 | OK | 보고서 §3(식 18=KMIX1T)·§5, CALIBRATION_GUIDE("Ge Eq.16–17의 보조변수")와 일치 |
| ch2:79 | X_PO, r_F, K₁ — "**원 논문이 값을 공개하지 않은** 논문 미공개" | **MAJOR** | **뉘앙스 불일치.** 보고서 §5 표: "Eq.18 **used** (params in **Ref.[30]**)" — Zhang은 값을 본문에 안 실었을 뿐 자기 참고문헌 [30]으로 이관함. 수정안: "Zhang (2022)은 식 (18)의 파라미터를 본문에 제시하지 않고 문헌 [30]에 미루고 있으며, 해당 문헌을 확보하지 못한 본 연구에서는 보정 대상으로 취급한다". Zhang PDF 확보 시 Ref.[30] 실체 확인·인용 필수(ch4:78도 동일 수정) |
| ch2:85 | "Ge (2018) 식 (6)" — ε=εᵉ+εᵖ+εᵗʰ | OK | 보고서 note "divides matrix strain into εᵉ+εᵖ+εᵗʰ (Eq. 6)" 일치 |
| ch2:93 | "Ge (2018) 식 (8)–(9)" — von Mises 연합유동·등방경화 | MINOR | 보고서는 (9)=소성, (6)–(8)=매트릭스 응력관계로 매핑. (8) 포함 여부 원문 확인(P-1) |
| ch2:97 | σ_Y0, H_iso "논문 미공개 → 보정 대상", 시작값 250/10⁵ | OK | 보고서 §5 항목 4("gives no yield stress / hardening modulus") 및 `make_cards.py`(SY0=250, HISO=100000)와 일치. 정직 서술 |
| ch2:101 | "Zhang (2022) 식 (15)–(16)" — 매트릭스 개시(sign I₁) | OK | 보고서 §3 일치 |
| ch2:105 | "Zhang (2022) 식 (19)" + "Ge (2018) 식 (7)" (등방 저감); G_f,m=0.031 시작값 | OK(주의) | (19)는 보고서 일치. (7)은 보고서의 (6)–(8) 범위 안이라 개연적이나 원문 확인 권고(MINOR로 계상). G_f,m=0.031은 출전 주장 없는 시작값으로 `make_cards.py`·GUIDE와 일치 — 문제 없음 |
| ch2:107 | "원 논문: 845 °C에서 손상률 100 %" | OK(주의) | 보고서 §6 "(paper: matrix damage = 100 % at 845 °C)" 동일. 원문 미보유 상태의 간접 인용임(P-1) |
| ch2:111–115 | 점성 정규화 — 서지 없음 + "**Ge (2018) §3.2의 권고대로**" | **MAJOR** | ① 점성 정규화의 원전 R18(Duvaut–Lions 1976)·R19(Lapczyk–Hurtado 2007) 인용 필수(현재 전무). ② "Ge §3.2 권고"는 보고서에 근거 발췌가 없는 **검증 불가한 절 단위 귀속** — 원문 확인 전까지 "해의 속도의존성이 무시될 만큼 작게 유지한다 [R18,R19]"로 완화 권고 |

### ch4_verification.md

| 위치 | 인용 | 판정 | 근거·수정안 |
|---|---|---|---|
| ch4:3 | (Zhang et al., 2022) / (Ge et al., 2018) | OK | — |
| ch4:7 | "116k–174k 규모" 메시 | OK | 보고서 §1 "116k–174k C3D4" 일치 |
| ch4:11–12 | Tables 1–2 + Chamis/Schapery, Ge 폐형식 | OK | 서지는 ch2:9 건(R16·R17)으로 해결 |
| ch4:20 | Table 2 대조 (350/0.20/310/4.5e-6; G_m 145.83 vs 논문 146 GPa) | OK | 보고서 §2.1과 완전 일치 |
| ch4:22 | 논문 §3.2.3 진술, V_f=0.79194 역산, 39.6 % ≈ "약 40 %" | OK | 보고서 §2.2 일치 |
| ch4:24–35 | Chamis/Schapery 재현표 (최대 0.142 %) | OK | 보고서 §2.2 표와 수치 동일 |
| ch4:39, 47 | Ge (2018) 폐형식 / "Ge (2018) 식 (16)–(17)의 X_PO, r_F, K₁" | OK | 보고서 §3 일치 |
| ch4:53–60 | 단위테스트 출력 발췌 | OK | 보고서 §3 출력과 문자 단위 동일 |
| ch4:62 | 1198/78.7/309.9 vs 입력 1200/80/310, gfortran 검사 | OK | 보고서와 일치, "검증용 임시값" 명시 정직 |
| ch4:66–70 | 논문 §3.2.4 3-스텝, 변형률 한계 0.15/0.32/0.48 % | OK | 보고서 §4 일치 |
| ch4:72 | "통합 주기경계(**Xia 방식**)" — 서지 없음 | **MAJOR** | R14(Xia 2003)·R15(Xia 2006) 인용 필수. 두 서지 모두 PDF [17] 참고문헌부([31],[32])에서 원문 표기 확보 완료 |
| ch4:78 | 미공개 파라미터 목록 ①–⑤, 메시 174,405 vs 116,724 | OK / **MAJOR** | 목록·메시 수치는 보고서 §5와 일치(OK). 단 ③ X_PO/r_F/K₁의 "공개하지 않은" 표현은 ch2:79와 동일하게 "Ref.[30]으로 이관"으로 정정(동일 건으로 계상) |
| ch4:80 | "T300 강도는 Ge (2018) Table 2 = Zhang Table 1", "Ge (2018) Table 3의 G_f,1t=12.5"; 시작값 Y_t=80, Y_c=350, S=100–120, X_PO=700, r_F=3.0, K₁=8000, σ_Y0=250, H_iso=10⁵ | OK | 보고서 §5 update·CALIBRATION_GUIDE·`make_cards.py`와 전 수치 일치. G_f는 1t만 Ge에 귀속 — 올바른 서술(ch2:69를 이 형태로 맞출 것) |
| ch4:101 | "논문: 845 °C에서 완전 손상" | OK(주의) | ch2:107과 동일 — 보고서 경유 간접 인용 |
| ch4:105, 121 | Table 3 목표 128.45/179.42/199.15; 메시 차이 서술 | OK | OUTLINE §4·보고서 일치 |
| ch4:121 | "**TexGen** 기하·메시를 재생성" — 서지 없음 | **MAJOR** | 도구 서지 R20(Lin–Brown–Long 2011) 인용 필요 |
| ch4 전반 | Abaqus 요소·키워드 (C3D4, `*Expansion`, CELENT, UMAT) | MINOR | Abaqus 매뉴얼 R21 인용 권장 (사용 버전 명기) |

### 공통·프로세스

| ID | 항목 | 판정 | 내용 |
|---|---|---|---|
| P-1 | **Zhang 2022·Ge 2018 원문 PDF 미보유** | **MAJOR** | 두 핵심 문헌이 저장소에 없어 표·식·절 번호 수준의 귀속(ch2:31, 35, 69, 93, 105, 115; ch2:25, 107)을 원문으로 확정할 수 없음. 현재 유일한 증거는 VERIFICATION_REPORT의 발췌. **시뮬레이션 이전에 두 PDF를 확보·저장**하고, Zhang의 Ref.[30](식 18 파라미터 출처)·[32](Chamis)·[33](Schapery)의 실체를 확인할 것 |
| MINOR-6 | ch1의 `[Zhang 2022]`/`[Ge 2018]` 괄호 저자-연도 표기 | MINOR | Ceramics International 투고 형식은 번호 인용 [n]. OUTLINE §3은 식 인용 형식만 규정하므로 본문 인용 스타일(번호제) 규칙을 OUTLINE에 추가하고 최종 원고에서 일괄 전환 |

**집계: BLOCKER 1 / MAJOR 16 / MINOR 6**
(MAJOR 내역: `[ref 필요]` 9건 — ch1:5a, 5b, 11a, 11b, 23a, 23b, 23c, 25a, 25b; 서지 누락 4건 — ch2:9(Chamis/Schapery), ch2:111(점성 정규화), ch4:72(Xia), ch4:121(TexGen); 귀속 문제 2건 — ch2:69(G_f,1c), ch2:79+ch4:78(X_PO "미공개"↔Ref.[30]); ch2:115의 "Ge §3.2" 귀속은 ch2:111 행에 포함; 프로세스 1건 — P-1. MINOR 내역: ch2:31, ch2:35, ch2:93, ch2:105, Abaqus 매뉴얼, MINOR-6.)

---

## 3. 추가 필요 참고문헌 제안 (confidence 표기)

confidence: **CERTAIN** = 정본·주지의 문헌(서지 확신) / **LIKELY** = 실재 확실, 쪽수·DOI 재확인 권장 / **UNSURE** = 대체 후보 탐색 권장.
검증 수단 메모: WebSearch 가동 — Ge 2018, Zhang 2022, Bažant–Oh 1983 3건을 검색으로 확인. Crossref·doi.org API 및 Semantic Scholar API는 프록시 차단(EGRESS_BLOCKED/403)으로 DOI 자동 대조는 불가했음. PDF [16]·[17]의 참고문헌부에서 Chamis 1987, Hashin–Rotem 1973, Xia 2003/2006 서지를 **원문 그대로 채록**함.

| 용도 (삽입 위치) | 제안 문헌 | confidence |
|---|---|---|
| CMC 배경·공정 개괄 (ch1:5a, 11a) | Naslain 2004, Compos. Sci. Technol. 64:155–170 | CERTAIN |
| C/SiC(C/C–SiC) 응용 (ch1:5a,b) | Krenkel & Berndt 2005, Mater. Sci. Eng. A 412:177–181 | LIKELY (쪽수 확인) |
| TPS·극초음속 (ch1:5b) | Glass 2008, AIAA 2008-2682 | LIKELY (페이퍼 번호 확인) |
| 추진 부품 적용 (ch1:5b) | Schmidt et al. 2004, Acta Astronaut. 55:409–420 | LIKELY |
| PIP·고분자 유래 세라믹 (ch1:11b) | Colombo et al. 2010, J. Am. Ceram. Soc. 93:1805–1837 | CERTAIN |
| PIP C/SiC 공정 (ch1:11b) | Rak 2001, J. Am. Ceram. Soc. 84:2235–2239 | LIKELY |
| CVI C/SiC (ch1:11a, 선택) | Xu et al. 1998, Carbon 36:1051–1056 | LIKELY |
| CDM 이방성 손상 원전 (ch1:23a) | Matzenmiller–Lubliner–Taylor 1995, Mech. Mater. 20:125–152 | CERTAIN |
| Hashin 개시 기준 (ch1:23b, ch2 §2.2.2) | Hashin & Rotem 1973, J. Compos. Mater. 7:448–464 (PDF[15] ref[41]에서 채록) / Hashin 1980, J. Appl. Mech. 47:329–334 | CERTAIN |
| 균열대 정규화 (ch1:23c, ch2 §2.2.3) | Bažant & Oh 1983, Mater. Struct. 16:155–177 (WebSearch 확인, DOI 10.1007/BF02486267) | CERTAIN |
| 직조 meso-FE 동향 (ch1:23a/25a) | Lomov et al. 2007, Compos. Sci. Technol. 67:1870–1891 | CERTAIN |
| 주기경계조건 (ch1:25a, ch4:72) | Xia–Zhang–Ellyin 2003, IJSS 40:1907–1921; Xia et al. 2006, IJSS 43:266–278 (모두 PDF[17]에서 채록) | CERTAIN |
| Chamis 마이크로역학 (ch1:25b, ch2 §2.1) | Chamis 1984, SAMPE Q. 15(3):14–23 (대안: Chamis 1987, J. Reinf. Plast. Compos. 6:268–289 — PDF[16] ref[38] 채록, DOI 10.1177/073168448700600303) | 1984: LIKELY(쪽수) / 1987: CERTAIN |
| Schapery CTE (ch1:25b, ch2 식 2.5–2.6) | Schapery 1968, J. Compos. Mater. 2:380–404 | CERTAIN |
| 점성 정규화 (ch2 §2.4) | Duvaut & Lions 1976 (Springer 단행본); Lapczyk & Hurtado 2007, Compos. Part A 38:2333–2341 | CERTAIN |
| TexGen (ch4:121) | Lin–Brown–Long 2011, Adv. Mater. Res. 331:44–47 | LIKELY |
| Abaqus (ch4 전반) | Dassault Systèmes SIMULIA, Abaqus Analysis User's Guide (사용 버전) | CERTAIN(형식만 확정) |
| 3D 확장 동향·후속연구 (ch1 §1.4 말미 또는 ch5) | 저장소 보유 3편: S. Zhang 2026 CPA 207:109796 / Song 2025 CST 261:111017 / P. Zhang 2024 JMRT 29:2016–2034 | CERTAIN (실물 보유) |
| Ge 2018 저자 명단 | "J. Ge, C. He, J. Liang, Y. Chen, D. Fang"으로 초안 — 검색 결과는 "Ge, He, Liang, Chen"까지 확인 | 서지 핵심 CERTAIN / 저자 후미(D. Fang 포함 여부) LIKELY — 원문 확보 시 확정 |
| Zhang 2022 DOI | 10.1016/j.ceramint.2021.10.081 (ScienceDirect PII S0272884221032235 확인) | LIKELY (DOI 문자열 재확인) |

---

## 4. 참고문헌 목록 초안 (Ceramics International 번호 형식, 본문 등장 순)

> ch1→ch2→ch4 등장 순 배열. [5]=기준 논문, [18]=구성 모델. 최종 원고에서 `[ref 필요]`·`[Zhang 2022]` 등을 아래 번호로 치환.

1. R. Naslain, Design, preparation and properties of non-oxide CMCs for application in engines and nuclear reactors: an overview, Compos. Sci. Technol. 64 (2004) 155–170. — **CERTAIN**
2. W. Krenkel, F. Berndt, C/C–SiC composites for space applications and advanced friction systems, Mater. Sci. Eng. A 412 (2005) 177–181. — **LIKELY**
3. D.E. Glass, Ceramic matrix composite (CMC) thermal protection systems (TPS) and hot structures for hypersonic vehicles, in: 15th AIAA Space Planes and Hypersonic Systems and Technologies Conference, AIAA Paper 2008-2682, 2008. — **LIKELY**
4. S. Schmidt, S. Beyer, H. Knabe, H. Immich, R. Meistring, A. Gessler, Advanced ceramic matrix composite materials for current and future propulsion technology applications, Acta Astronaut. 55 (2004) 409–420. — **LIKELY**
5. Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang, Effect of thermal residual stress on the tensile properties and damage process of C/SiC composites at high temperatures, Ceram. Int. 48 (2022) 3109–3124. — **CERTAIN** (DOI 10.1016/j.ceramint.2021.10.081: LIKELY)
6. P. Colombo, G. Mera, R. Riedel, G.D. Sorarù, Polymer-derived ceramics: 40 years of research and innovation in advanced ceramics, J. Am. Ceram. Soc. 93 (2010) 1805–1837. — **CERTAIN**
7. Z.S. Rak, A process for Cf/SiC composites using liquid polymer infiltration, J. Am. Ceram. Soc. 84 (2001) 2235–2239. — **LIKELY**
8. Y. Xu, L. Zhang, L. Cheng, D. Yan, Microstructure and mechanical properties of three-dimensional carbon/silicon carbide composites fabricated by chemical vapor infiltration, Carbon 36 (1998) 1051–1056. — **LIKELY**
9. A. Matzenmiller, J. Lubliner, R.L. Taylor, A constitutive model for anisotropic damage in fiber-composites, Mech. Mater. 20 (1995) 125–152. — **CERTAIN**
10. Z. Hashin, A. Rotem, A fatigue failure criterion for fiber reinforced materials, J. Compos. Mater. 7 (1973) 448–464. — **CERTAIN** (PDF[15] 참고문헌부 채록)
11. Z. Hashin, Failure criteria for unidirectional fiber composites, J. Appl. Mech. 47 (1980) 329–334. — **CERTAIN**
12. Z.P. Bažant, B.H. Oh, Crack band theory for fracture of concrete, Mater. Struct. 16 (1983) 155–177. — **CERTAIN** (DOI 10.1007/BF02486267)
13. S.V. Lomov, D.S. Ivanov, I. Verpoest, M. Zako, T. Kurashiki, H. Nakai, S. Hirosawa, Meso-FE modelling of textile composites: road map, data flow and algorithms, Compos. Sci. Technol. 67 (2007) 1870–1891. — **CERTAIN**
14. Z. Xia, Y. Zhang, F. Ellyin, A unified periodical boundary conditions for representative volume elements of composites and applications, Int. J. Solids Struct. 40 (2003) 1907–1921. — **CERTAIN** (PDF[17] 채록)
15. Z. Xia, C. Zhou, Q. Yong, X. Wang, On selection of repeated unit cell model and application of unified periodic boundary conditions in micro-mechanical analysis of composites, Int. J. Solids Struct. 43 (2006) 266–278. — **CERTAIN** (PDF[17] 채록)
16. C.C. Chamis, Simplified composite micromechanics equations for hygral, thermal and mechanical properties, SAMPE Q. 15 (3) (1984) 14–23. — **LIKELY** (대안: C.C. Chamis, Simplified composite micromechanics for predicting microstresses, J. Reinf. Plast. Compos. 6 (1987) 268–289 — **CERTAIN**, PDF[16] 채록)
17. R.A. Schapery, Thermal expansion coefficients of composite materials based on energy principles, J. Compos. Mater. 2 (1968) 380–404. — **CERTAIN**
18. J. Ge, C. He, J. Liang, Y. Chen, D. Fang, A coupled elastic-plastic damage model for the mechanical behavior of three-dimensional (3D) braided composites, Compos. Sci. Technol. 157 (2018) 86–98. — 서지 핵심 **CERTAIN** (DOI 10.1016/j.compscitech.2018.01.027), 저자 후미 **LIKELY** — 원문 확보 시 확정
19. G. Duvaut, J.L. Lions, Inequalities in Mechanics and Physics, Springer-Verlag, Berlin, 1976. — **CERTAIN**
20. I. Lapczyk, J.A. Hurtado, Progressive damage modeling in fiber-reinforced materials, Compos. Part A Appl. Sci. Manuf. 38 (2007) 2333–2341. — **CERTAIN**
21. H. Lin, L.P. Brown, A.C. Long, Modelling and simulating textile structures using TexGen, Adv. Mater. Res. 331 (2011) 44–47. — **LIKELY**
22. Dassault Systèmes SIMULIA, Abaqus Analysis User's Guide, Version 20xx (사용 버전 기입), Providence, RI. — 형식 **CERTAIN**
23. S. Zhang, D. Zhang, J. Zhou, F. Du, K. Guan, Z. Guan, W.J. Cantwell, Quantification of thermal residual stresses and their effects on the mechanical behavior of 3D C/SiC composites, Compos. Part A Appl. Sci. Manuf. 207 (2026) 109796. — **CERTAIN** (저장소 [15] 실물)
24. X. Song, J. Zhou, J. Wang, L. Bai, X. Yang, J. Xue, D. Zhang, S. Zhang, X. Chen, Z. Guan, W.J. Cantwell, Multi-scale characterisation and damage analysis of 3D braided composites under off-axis tensile loading, Compos. Sci. Technol. 261 (2025) 111017. — **CERTAIN** (저장소 [16] 실물)
25. P. Zhang, L. Zhu, Y. Tong, Y. Li, Y. Xing, H. Lan, Y. Sun, X. Liang, Revealing thermal shock behaviors and damage mechanism of 3D needled C/C–SiC composites based on multi-scale analysis, J. Mater. Res. Technol. 29 (2024) 2016–2034. — **CERTAIN** (저장소 [17] 실물)

*추가 미결(원문 확보 후 편입): Zhang (2022)의 Ref.[30] — 식 (18) 혼합법칙 파라미터(X_PO, r_F, K₁)의 출처 문헌. 실체 미상이므로 목록에 넣지 않음. Zhang PDF 확보 시 [18] 다음에 삽입 권장.*

---

## 5. 권고 액션 (우선순위)

1. **(BLOCKER) ch1:27 수정** — Ge 2018 대상 재료를 "3차원 편조(braided) 복합재"로 정정.
2. **(MAJOR/P-1) Zhang 2022·Ge 2018 원문 PDF 확보 및 저장소 추가** — 식·표·절 번호 귀속 8건(ch2:31, 35, 69, 93, 105, 115, 25, 107)과 Ref.[30]·[32]·[33] 실체 확인이 모두 여기에 걸려 있음. 시뮬레이션 착수 전 완료 권장.
3. **(MAJOR) `[ref 필요]` 9건 치환** — §4 목록 [1]–[4], [6]–[17]로 삽입.
4. **(MAJOR) 서지 누락 4건 보강** — Chamis/Schapery(ch2:9), Bažant–Oh(ch2:65), Duvaut–Lions/Lapczyk–Hurtado(ch2:111), Xia(ch4:72), TexGen(ch4:121).
5. **(MAJOR) 귀속 문구 2건 정정** — ch2:69 (G_f,1c는 본 연구 가정으로 분리), ch2:79·ch4:78 ("미공개" → "Ref.[30]으로 이관, 미확보").
6. **(MINOR) 파일명 `[17]` 충돌 해소, 본문 번호인용 전환, Abaqus 매뉴얼 인용.**

*검색 출처: [Ge 2018 — Semantic Scholar](https://www.semanticscholar.org/paper/A-coupled-elastic-plastic-damage-model-for-the-of-Ge-He/21a44d3020414ff8e46a3c9f3e6393972dd1c3e3) · [Ge 2018 — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0266353817322145) · [Zhang 2022 — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0272884221032235) · [Bažant–Oh 1983 — Springer](https://link.springer.com/article/10.1007/BF02486267)*
