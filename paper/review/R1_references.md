# R1 참고문헌 감사 보고서 — **Round 2 (검증 라운드)**

**감사 대상:** `paper/ch1_intro.md`(번호 인용 전면 도입), `paper/ch2_theory.md`, `paper/ch4_verification.md`,
`paper/references.md`(신설), `README.md`(파일명 주의문 추가), `verification/CALIBRATION_GUIDE.md` §3·§5
**감사 근거:** Round 1 보고서(본 파일 §5–§7 유지분), `paper/review/SYNTHESIS.md` §2·§4·§5, `verification/VERIFICATION_REPORT.md`, git 이력(`2d80ac0`, `93d7491`)
**감사일:** 2026-08-11 / 감사자: R1 (reference auditor)
**성격:** Round 1 지적사항의 **이행 검증** + 변경분 신규 감사. 저장소 PDF는 Round 1 실측 결과를 원용(재열람 없음).

---

## 0. 집계 및 이전 라운드 대비 변화

| 라운드 | BLOCKER | MAJOR | MINOR |
|---|---:|---:|---:|
| Round 1 | 1 | 16 | 6 |
| **Round 2 (본 보고)** | **0** | **2** | **6** |

- **Round 1 BLOCKER(ch1:27 Ge 2018 오기술) 해소 확인.** 신규 BLOCKER 없음 → R1 관점의 해석 게이트는 계속 **통과**.
- Round 1 MAJOR 16건 중 **13건 이행, 1건 부분 이행, 2건 보류(사용자 액션·버전 확정 대기)**.
- Round 2 MAJOR 2건은 모두 **신규**가 아니라 "부분 이행에서 남은 잔여분(1건)"과 "새 문단이 만들어낸 무인용 주장(1건)"이다.
- 인용 번호 25개 전체를 대조한 결과 **번호→내용 불일치(BLOCKER 급) 0건, 미등재 번호(dangling) 0건**.

---

## 1. Round 1 지적사항 이행 확인표

| # | Round 1 지적 (판정) | 반영 여부 | 근거 file:line |
|---|---|---|---|
| 1 | **ch1:27 Ge 2018 "세라믹기지 직조" 오기술** (BLOCKER) | **이행** | `paper/ch1_intro.md:27` — "3차원 편조(braided) 수지계 복합재를 대상으로 … Zhang 등 [5]은 이 구성 모델을 2차원 평직 C/SiC RVE에 채택·이식" |
| 2 | `[ref 필요]` 9건 치환 (MAJOR×9) | **이행** | `ch1_intro.md:5, 11, 23, 25` — 잔존 `[ref 필요]` 0건(전 파일 grep). LIKELY는 전부 `[n? DOI 확인 필요]` 표기 |
| 3 | 번호제 [n] 전환 (MINOR-6) | **이행** | ch1 전체에서 `[Zhang 2022]`/`[Ge 2018]` 괄호 저자-연도 인용 0건. 규칙은 `OUTLINE.md:111–112`에 등재 |
| 4 | Chamis·Schapery 서지 누락 (ch2:9, MAJOR) | **이행** | `ch2_theory.md:9` — "Chamis 강성 관계식 [16? DOI 확인 필요]과 Schapery 열팽창 관계식 [17]" |
| 5 | Bažant–Oh 균열대 원전 누락 (ch2:65, MAJOR) | **이행** | `ch2_theory.md:73` — "균열대 정규화(crack-band regularization) [12]"; ch1 대응은 `ch1_intro.md:23` |
| 6 | 점성 정규화 서지 부재 + "Ge §3.2 권고" 검증불가 귀속 (ch2:111/115, MAJOR) | **이행** | `ch2_theory.md:123, 127` — "[19,20]" 2회, "Ge §3.2 권고" 문구 삭제 확인(ch2 내 `§3.2` 문자열 0건) |
| 7 | Xia 주기경계 서지 누락 (ch4:72, MAJOR) | **이행** | `ch4_verification.md:74` — "통합 주기경계(Xia 방식 [14,15])" |
| 8 | TexGen 서지 누락 (ch4:121, MAJOR) | **이행** | `ch4_verification.md:123` — "TexGen [21? DOI 확인 필요]" |
| 9 | **G_f,1c 과잉귀속** (ch2:69, MAJOR) | **부분 이행** | 이행: `ch2_theory.md:77` "압축 파괴에너지 $G_{f,1c}$는 원 논문 근거 없이 동일한 12.5 N/mm로 두는 본 연구의 가정(시작값)", `ch4_verification.md:82` 동일 취지. **미이행: `verification/CALIBRATION_GUIDE.md:52, 135`가 여전히 G1c를 Ge Table 3에 귀속** → Round 2 MAJOR-1 |
| 10 | **X_PO/r_F/K₁ "논문 미공개" → Ref.[30] 이관** (ch2:79·ch4:78, MAJOR) | **이행(3개소 전부)** | `ch2_theory.md:91`, `ch4_verification.md:80`, `CALIBRATION_GUIDE.md:137–138` — 세 곳 모두 "본문에 싣지 않고 (자신의) 참고문헌 [30]으로 미룸(미확보)" 표현으로 통일 |
| 11 | 참고문헌 목록 정본화 (§4 초안) | **이행** | `paper/references.md` 신설 — 25건, 번호제, confidence를 HTML 주석으로 보존(`references.md:7–31`), Ref.[30] 미결 주석(`:33–34`) |
| 12 | 저장소 PDF 파일명 `[17]` 충돌 명기 (MINOR) | **이행 + 사실 정합 확인** | `README.md:42–48`, `OUTLINE.md:4`. 내용이 Round 1 실측(§5 표)과 **완전 일치** — 상세는 아래 §4 |
| 13 | **P-1 Zhang 2022·Ge 2018 원문 PDF 확보** (MAJOR/프로세스) | **미이행(보류 유지·사용자 액션)** | 저장소 PDF 여전히 3종뿐(`ls`), 신규 커밋 없음. SYNTHESIS §4.1에 등재된 상태 유지 → 정상적 보류 |
| 14 | Abaqus 매뉴얼 [22] 본문 인용 (MINOR) | **미이행(의도적 보류)** | `references.md:28` 항목만 존재, 버전 미확정. 본문 미인용 → 아래 MINOR-2 고아 항목으로 계상 |

**요약:** Round 1 항목 중 **방치된 것은 없다.** #13·#14는 명시적 보류(원문/버전 확보 대기), #9만 저장소 문서(`CALIBRATION_GUIDE`)에 잔여분이 남았다.

---

## 2. Round 2 신규 지적

### MAJOR

| ID | file:line | 판정 | 내용·수정안 |
|---|---|---|---|
| **M2-1** | `verification/CALIBRATION_GUIDE.md:52`, `:135` | **MAJOR** | **논문 본문과 저장소 문서의 귀속 불일치(Round 1 #9의 잔여분).** §3 표: "\| 32–33 \| G1t,G1c (N/mm) \| **12.5** \| **Ge Table 3** \|", §5: "**G1t=G1c=12.5, (Gtt=Gtc=1.0):** Ge 2018 Table 3(탄소/페놀)". 그러나 `VERIFICATION_REPORT.md:199–200`이 Ge Table 3에서 확인해 준 값은 **Gf,1t=12.5와 Gf,2t=1.0뿐**이며, ch2:77·ch4:82는 이미 "G_f,1c는 본 연구의 가정"으로 정정되었다. 같은 파일 §5의 X_PO 항목은 정정되었는데 바로 위 G1t/G1c 항목만 남아 문서 간 모순이 발생한다. **수정안:** 출처 열을 "Ge Table 3 (G1t만); G1c는 본 연구 가정" 으로, §5 문장을 "G1t=12.5는 Ge 2018 Table 3(탄소/페놀 편조재), G1c는 근거 없이 동일값으로 둔 본 연구의 가정" 으로. (편집 권한 밖 — S 노드 이관) |
| **M2-2** | `paper/ch1_intro.md:29` | **MAJOR** | **신규 삽입 문단의 무인용 문헌 동향 주장.** "직조·편조 복합재 해석에서 **최근 문헌에서도 여전히 주류로 사용되고 있다**", "위상장(phase-field) 파괴 모델이 세라믹 매트릭스 복합재에도 **적용되기 시작하였고**", "계산 균질화와 기계학습을 결합한 … 프레임워크가 **부상하고 있다**" — 세 문장 모두 문헌 상태에 대한 하중 주장인데 인용이 하나도 없다. 동시에 `references.md:29–31`의 [23]–[25](저장소 실물 보유, CERTAIN)는 **본문 미인용 고아 상태**이며, 그 주석 자체가 "§1.4 동향에서 인용 예정"이라고 적고 있다. **수정안:** ① "여전히 주류" 문장 끝에 [23,24,25] 부여(세 편 모두 2024–2026년 Chamis·Hashin·Xia PBC·UMAT 조합 사용 — Round 1 §5 표에서 실측 확인) — 이것으로 고아 3건도 동시 해소. ② 위상장·ML 문장은 서지를 붙이거나(CERTAIN 확보 전이면) "…확장이 시도되고 있다" 수준으로 완화하고 제5장 후속연구 서술로 이관. 무인용 상태 유지는 Round 1이 `[ref 필요]` 9건에 적용한 것과 같은 MAJOR 기준에 걸린다. |

### MINOR

| ID | file:line | 판정 | 내용·수정안 |
|---|---|---|---|
| m2-1 | `ch2_theory.md:91`, `ch4_verification.md:80` | MINOR | 본문 번호제와 **원 논문 내부 번호 [30]의 충돌 위험.** 두 곳 모두 "Zhang (2022)이 … 자신의 참고문헌 [30]에/으로"로 한정어가 붙어 있어 현재는 dangling이 아니지만, 번호제 원고에서 `[30]`은 시각적으로 본 원고의 30번 문헌으로 읽힌다(파일명 `[17]` 충돌과 동형의 위험). **수정안:** "문헌 [5]의 참고문헌 30번" 또는 "Ref. 30 of [5]" 표기. 한정어가 사라지면 즉시 MAJOR로 승격. |
| m2-2 | `references.md:28–31` | MINOR | **고아 항목 4건:** [22] Abaqus 매뉴얼(버전 미확정, 본문 미인용), [23][24][25](§1.4/ch5 인용 예정 주석만 존재). [23]–[25]는 M2-2 수정으로 해소 가능. [22]는 ch4 전반의 Abaqus 키워드(C3D4·`*Expansion`·CELENT·UMAT) 최초 등장부에 1회 인용하거나 목록에서 제거할 것(버전 확정이 선행). |
| m2-3 | `ch1_intro.md:5` | MINOR | 인용 괄호 표기 불일치: `[2? DOI 확인 필요]`, `[3?, 4? DOI 확인 필요]`(쉼표+공백) vs `[9,13]`·`[14,15]`(공백 없음), `[16? DOI 확인 필요], [17]`(별도 괄호 병렬). 최종 원고 조판 전 한 형식으로 통일(권장: `[3,4]`·`[16,17]` 형태로 병합하고 "? DOI 확인 필요"는 편집용 임시 표식임을 명시). |
| m2-4 | `verification/CALIBRATION_GUIDE.md:119` | MINOR | ch2에서 삭제된 검증불가 귀속 "**Ge 2018 §3.2: '작게 유지'**"가 GUIDE §4에 잔존. SYNTHESIS §4.4가 이미 "권한 밖"으로 이관한 항목이며, 원문 확보(P-1) 시 일괄 처리 대상으로 계속 등재할 것. |
| m2-5 | `references.md:28` | MINOR | 형식 미완결: "Abaqus Analysis User's Guide, **Version 20xx (사용 버전 기입)**" — Ceramics International 서지 형식으로는 placeholder가 남아 있으면 안 된다. m2-2와 함께 처리. |
| m2-6 | `ch1_intro.md:23` | MINOR | [13] Lomov 2007(*Meso-FE modelling of textile composites: road map*)이 "CDM 점진손상이 주류" 문장에 [9]와 병기되어 있다. Lomov는 CDM 원전이라기보다 **직조 meso-FE 절차** 문헌이므로 `ch1_intro.md:25`(RVE 멀티스케일 문장, 현재 [14,15])로 옮기는 편이 주장–출전 정합이 높다. 내용상 오류는 아니므로 MINOR. |

---

## 3. 인용 번호 ↔ `references.md` 정합표

**판정 기준:** 번호가 목록의 올바른 항목을 가리키는가(번호 정합) + 그 항목이 문장의 주장을 실제로 뒷받침하는가(내용 정합).

| [n] | 문헌 | 본문 사용처 (file:line) | 번호 | 내용 | 비고 |
|---|---|---|---|---|---|
| 1 | Naslain 2004 (비산화물 CMC 총설) | ch1:5(CMC 배경), ch1:11(CVI/MI/PIP 분류) | OK | OK | 공정 개괄·CVI 서술 포함 문헌 |
| 2? | Krenkel–Berndt 2005 (C/C–SiC 우주·마찰) | ch1:5 | OK | OK | LIKELY 표기 정상 |
| 3? | Glass 2008 (CMC TPS/hot structure) | ch1:5 | OK | OK | TPS·극초음속 주장에 정확히 대응 |
| 4? | Schmidt 2004 (추진 부품 CMC) | ch1:5 | OK | OK | 노즐·연소기 언급과 대응 |
| 5 | **Zhang 2022 (기준 논문)** | ch1:5,11,13,17×2,19,27,29,35 / ch2:3,7,33,65,81,91,117 / ch4:3,82 | OK | OK | 평직 C/SiC·PIP 1050 °C·Table 3 수치 모두 Round 1 대조 완료 |
| 6 | Colombo 2010 (polymer-derived ceramics) | ch1:11(PIP 설명) | OK | OK | |
| 7? | Rak 2001 (액상 고분자 침투 Cf/SiC) | ch1:11 | OK | OK | |
| 8? | Xu 1998 (CVI 3D C/SiC) | ch1:11(공정 분류) | OK | OK | |
| 9 | Matzenmiller 1995 (이방성 손상 CDM) | ch1:23, ch1:29(지수형 발전) | OK | OK | "Matzenmiller 계열 지수형 손상발전" 표현 정확 |
| 10,11 | Hashin–Rotem 1973 / Hashin 1980 | ch1:23, ch1:29 | OK | OK | |
| 12 | Bažant–Oh 1983 (crack band) | ch1:23, ch1:29, ch2:73 | OK | OK | 균열대 정규화 원전으로 정확 |
| 13 | Lomov 2007 (직조 meso-FE road map) | ch1:23 | OK | 준OK | m2-6 — 배치 이동 권고 |
| 14,15 | Xia 2003 / Xia 2006 (통합 PBC) | ch1:25, ch1:29, ch4:74 | OK | OK | ch4 "Xia 방식" 서술과 정확 대응 |
| 16? | Chamis 1984(대안 1987) 마이크로역학 | ch1:25, ch2:9 | OK | OK | 판본 미확정 → LIKELY 표기 정상(§7 보류) |
| 17 | Schapery 1968 (CTE) | ch1:25, ch2:9 | OK | OK | ch2:27의 "횡방향 (2.6)은 Chamis 계열 √V_f 가중" 병기도 정합 |
| 18 | **Ge 2018 (구성 모델)** | ch1:27,29,35 / ch2:3 / ch4:3 | OK | **OK(BLOCKER 해소)** | ch1:27이 3D **편조·수지계**로 정정됨 — §4 참조 |
| 19,20 | Duvaut–Lions 1976 / Lapczyk–Hurtado 2007 | ch1:29, ch2:123, ch2:127 | OK | OK | 점성 정규화 2개소 모두 부여 |
| 21? | Lin–Brown–Long 2011 (TexGen) | ch4:123 | OK | OK | LIKELY 표기 정상 |
| 22 | Abaqus User's Guide | **미인용** | — | — | 고아 (m2-2, m2-5) |
| 23,24,25 | 저장소 PDF 3종 (CPA 2026 / CST 2025 / JMRT 2024) | **미인용** | — | — | 고아 (M2-2에서 회수 권고) |
| ([30]) | Zhang 2022 내부 참고문헌 | ch2:91, ch4:80 | 한정어 有 | — | 본 원고 목록 밖 — m2-1 |

**목록 자체 검수:** 번호 1–25 **연속·중복·결번 없음**. 본문의 모든 [n]이 목록에 실재(dangling 0). Ceramics International 형식(저자 이니셜+성, 제목, 축약 저널명, 권(연도) 쪽) **일관** — 예외는 [22] placeholder(m2-5)와 [3](학회 논문, 형식상 정상). CERTAIN/LIKELY HTML 주석 **25건 전부 보존**(`references.md:7–31`), `[n? DOI 확인 필요]` 표기는 **LIKELY 6건([2],[3],[4],[7],[8],[16],[21])에만** 사용되고 CERTAIN 항목에는 미사용 — 규칙 준수. **비-CERTAIN 문헌이 확정 인용으로 삽입된 사례 0건.**

---

## 4. README 파일명 주의문의 사실 정합 검증 (Round 2 신규 항목)

`README.md:42–48`의 caution 문단을 Round 1 §5 실측표와 대조:

| README 진술 | Round 1 실측 | 판정 |
|---|---|---|
| 세 PDF는 후속 연구용 **별개 수집본** | 세 편 모두 Zhang 2022/Ge 2018과 무관한 3D C/SiC 관련 문헌 | **일치** |
| Compos. Part A 207 (2026) | `[15]` = S. Zhang et al., CPA 207 (2026) 109796 | **일치** |
| Compos. Sci. Technol. 261 (2025) | `[16]` = Song et al., CST 261 (2025) 111017 | **일치** |
| J. Mater. Res. Technol. 29 (2024) | `[17]` = P. Zhang et al., JMRT 29 (2024) 2016–2034 | **일치** |
| 괄호 번호는 개인 정리 번호이며 Zhang 2022의 참고문헌 번호가 **아님** | `README.md:38`·`VERIFICATION_REPORT.md:6`의 "Ref. [17] in Zhang 2022"와의 충돌을 정확히 지목 | **일치** |
| `[17] … A03.pdf`는 Ge 2018이 **아님** | Ge 2018 = CST 157 (2018) 86–98, 저장소 부재 | **일치** |
| Zhang 2022·Ge 2018 모두 현재 저장소에 없음 | git 이력 전수 확인(PDF 추가 커밋 `ed8d55f`, `5ae1b08`뿐) | **일치** |

→ **주의문에 사실 오류 없음.** 다만 `[16]`(Song 2025)은 3D 편조 **수지계** 복합재로 C/SiC가 아니므로, "3D C/SiC property papers"라는 README 표현은 파일명(`3D C-SiC 물성`) 유래의 관용적 묶음 표현으로만 유효하다(문서 수정이 필요할 정도는 아님 — 참고 사항).

한편 `paper/ch2_theory.md:11`의 "표 2.1 … 강도는 Ge (2018) Table 2에도 동일 수록"과 `ch2:65`, `ch4:82`의 "Ge (2018) Table 2 = Zhang Table 1"은 `VERIFICATION_REPORT.md:198`("Ge Table 2 lists the same T300 filament … Xt=3580, Xc=2470")에 근거가 있어 **Ge의 재료계(탄소섬유/수지)와 모순되지 않는다**(T300 필라멘트 물성은 두 논문 공통). ch1·ch2·ch4를 전수 검색한 결과 **Ge 2018을 세라믹기지 또는 2D 직조 재료로 기술하는 잔여 문장은 없다.**

---

## 5. (유지) 저장소 PDF 3종의 실체 — Round 1 실측표

세 파일 모두 Round 1에서 실측 확인(1–2면 텍스트 + 메타데이터). **셋 중 어느 것도 Ge et al. CST 157 (2018)이나 Zhang et al. Ceram. Int. 48 (2022)이 아니다.** (Round 2에서는 재열람하지 않음.)

| 파일 | 실제 논문 | 저자 | 저널·서지 | DOI | 내용 요약 |
|---|---|---|---|---|---|
| `[15] 3D C-SiC 물성 A01.pdf` (15면) | *Quantification of thermal residual stresses and their effects on the mechanical behavior of 3D C/SiC composites* | S. Zhang, D. Zhang, J. Zhou, F. Du, K. Guan, Z. Guan, W.J. Cantwell | Compos. Part A **207** (2026) 109796 | 10.1016/j.compositesa.2026.109796 | 3D 편조 C/SiC의 열잔류응력(TRS) 정량화: 멀티스케일 FE+이론 모델+XRD 검증. 메소스케일 매트릭스 TRS 축 114.7/횡 40.3 MPa, 얀 −68.7/−23.9 MPa. 인장은 강도 저하·압축은 증가. Zhang 2022를 자기 ref [26]으로 인용 |
| `[16] 3D C-SiC 물성 A02.pdf` (11면) | *Multi-scale characterisation and damage analysis of 3D braided composites under off-axis tensile loading* | X. Song, J. Zhou, J. Wang, L. Bai, X. Yang, J. Xue, D. Zhang, S. Zhang, X. Chen, Z. Guan, W.J. Cantwell | Compos. Sci. Technol. **261** (2025) 111017 | 10.1016/j.compscitech.2024.111017 | 3D 편조 복합재(**수지계, C/SiC 아님**) off-axis 인장: DIC·SEM·μCT, 강성 예측, 기공 포함 FE, UMAT. Chamis[38]·Duvaut–Lions[42] 인용 |
| `[17] 3D C-SiC 물성 A03.pdf` (19면) | *Revealing thermal shock behaviors and damage mechanism of 3D needled C/C–SiC composites based on multi-scale analysis* | P. Zhang, L. Zhu, Y. Tong, Y. Li, Y. Xing, H. Lan, Y. Sun, X. Liang | J. Mater. Res. Technol. **29** (2024) 2016–2034 | 10.1016/j.jmrt.2024.01.260 | 3D 니들펀치 C/C–SiC 열충격 멀티스케일 해석. Zhang 2022를 자기 ref [19]로 인용. Xia PBC [31][32]·Chamis[6]·Hashin[35] 인용 |

두 핵심 문헌의 실재 교차 확인(Round 1):
- Zhang 2022: PDF [15] ref [26], PDF [17] ref [19]에 원문 표기 + ScienceDirect PII S0272884221032235.
- Ge 2018: *A coupled elastic-plastic damage model for the mechanical behavior of three-dimensional (3D) braided composites*, Compos. Sci. Technol. 157 (2018) 86–98, DOI 10.1016/j.compscitech.2018.01.027 (Semantic Scholar / ScienceDirect PII S0266353817322145).

---

## 6. (유지) 참고문헌 목록 — `paper/references.md` 정본 반영본

> 정본은 `paper/references.md`. 아래는 감사 편의를 위한 사본이며, 번호·서지는 정본과 일치함을 Round 2에서 대조 확인하였다.

1. R. Naslain, Design, preparation and properties of non-oxide CMCs …, Compos. Sci. Technol. 64 (2004) 155–170. — CERTAIN
2. W. Krenkel, F. Berndt, C/C–SiC composites for space applications and advanced friction systems, Mater. Sci. Eng. A 412 (2005) 177–181. — LIKELY
3. D.E. Glass, Ceramic matrix composite (CMC) thermal protection systems (TPS) and hot structures for hypersonic vehicles, AIAA Paper 2008-2682, 2008. — LIKELY
4. S. Schmidt et al., Advanced ceramic matrix composite materials …, Acta Astronaut. 55 (2004) 409–420. — LIKELY
5. Q. Zhang, J. Ge, B. Zhang, C. He, Z. Wu, J. Liang, Effect of thermal residual stress …, Ceram. Int. 48 (2022) 3109–3124. — CERTAIN (DOI 문자열 LIKELY)
6. P. Colombo et al., Polymer-derived ceramics …, J. Am. Ceram. Soc. 93 (2010) 1805–1837. — CERTAIN
7. Z.S. Rak, A process for Cf/SiC composites using liquid polymer infiltration, J. Am. Ceram. Soc. 84 (2001) 2235–2239. — LIKELY
8. Y. Xu et al., Microstructure and mechanical properties of 3D C/SiC by CVI, Carbon 36 (1998) 1051–1056. — LIKELY
9. A. Matzenmiller, J. Lubliner, R.L. Taylor, Mech. Mater. 20 (1995) 125–152. — CERTAIN
10. Z. Hashin, A. Rotem, J. Compos. Mater. 7 (1973) 448–464. — CERTAIN
11. Z. Hashin, J. Appl. Mech. 47 (1980) 329–334. — CERTAIN
12. Z.P. Bažant, B.H. Oh, Crack band theory for fracture of concrete, Mater. Struct. 16 (1983) 155–177. — CERTAIN
13. S.V. Lomov et al., Meso-FE modelling of textile composites …, Compos. Sci. Technol. 67 (2007) 1870–1891. — CERTAIN
14. Z. Xia, Y. Zhang, F. Ellyin, Int. J. Solids Struct. 40 (2003) 1907–1921. — CERTAIN
15. Z. Xia, C. Zhou, Q. Yong, X. Wang, Int. J. Solids Struct. 43 (2006) 266–278. — CERTAIN
16. C.C. Chamis, SAMPE Q. 15(3) (1984) 14–23. — LIKELY (대안: Chamis, J. Reinf. Plast. Compos. 6 (1987) 268–289 — CERTAIN)
17. R.A. Schapery, J. Compos. Mater. 2 (1968) 380–404. — CERTAIN
18. J. Ge, C. He, J. Liang, Y. Chen, D. Fang, A coupled elastic-plastic damage model …, Compos. Sci. Technol. 157 (2018) 86–98. — 서지 핵심 CERTAIN / 저자 후미 LIKELY
19. G. Duvaut, J.L. Lions, Inequalities in Mechanics and Physics, Springer, 1976. — CERTAIN
20. I. Lapczyk, J.A. Hurtado, Compos. Part A 38 (2007) 2333–2341. — CERTAIN
21. H. Lin, L.P. Brown, A.C. Long, Adv. Mater. Res. 331 (2011) 44–47. — LIKELY
22. Dassault Systèmes SIMULIA, Abaqus Analysis User's Guide (버전 미확정). — 형식 CERTAIN / **본문 미인용**
23. S. Zhang et al., Compos. Part A 207 (2026) 109796. — CERTAIN (저장소 실물) / **본문 미인용**
24. X. Song et al., Compos. Sci. Technol. 261 (2025) 111017. — CERTAIN (저장소 실물) / **본문 미인용**
25. P. Zhang et al., J. Mater. Res. Technol. 29 (2024) 2016–2034. — CERTAIN (저장소 실물) / **본문 미인용**

*미결: Zhang (2022)의 Ref.[30] — 식 (18) 파라미터(X_PO, r_F, K₁)의 출처. 실체 미상이므로 목록 미등재; PDF 확보 시 [18] 다음 삽입 권장.*

---

## 7. (유지·갱신) 보류·확인 필요 목록

### 7.1 사용자 액션 (최우선, 미이행 상태 유지)

- **P-1 Zhang 2022 · Ge 2018 원문 PDF 확보** — Round 2 시점에도 미확보. 확보 시 확인할 것: Zhang Ref.[30](식 18 파라미터 출처), Ref.[32](Chamis 판본), Ref.[33](Schapery); Ge 저자 후미(D. Fang 여부); **Ge Table 3의 G_f,1c 수록 여부**(수록 시 ch2:77·ch4:82·CALIBRATION_GUIDE §5를 동시에 환원).

### 7.2 식 귀속 보류 8건 — Round 2 재점검 결과

원문 없이도 방어 가능한 표현인지(=새로 단정적 주장이 끼어들지 않았는지)를 전수 확인. **8건 전부 Round 1 대비 문구 강화 없음, 신규 단정 0건.**

| # | 위치 | 현재 문구 | 판정 |
|---|---|---|---|
| 1 | `ch2:39` | "(Ge (2018) 식 (2)–(4))" | 무변경 — 보고서 매핑은 (2)–(3), 보류 유지 |
| 2 | `ch2:43` | "(Ge (2018) 식 (3))" 전단 결합손상 | 무변경 — 범위 중복 귀속 보류 유지 |
| 3 | `ch2:105` | "(Ge (2018) 식 (8)–(9))" | 무변경 |
| 4 | `ch2:117` | "(Ge (2018) 식 (7))" 등방 저감 | 무변경 |
| 5 | `ch2:33` | "온도에 무관한 상수로 두며 …(Zhang 2022 §3.2.3)" | 무변경(보고서 경유). ch4:22·ch4:82도 동일 수준 유지 |
| 6 | `ch2:119`, `ch4:103` | "원 논문: 845 °C에서 매트릭스 손상 **부피분율** 100 %" | 용어 정렬만 반영, 주장 강도 동일 — 안전 |
| 7 | `ch2 §2.4` | (제거된) "Ge §3.2 권고" | ch2에서 삭제 확인. **단 `CALIBRATION_GUIDE.md:119`에 잔존(m2-4)** |
| 8 | `ch2:77` | Ge Table 3 인용 범위 | **개선** — G_f,1t만 귀속하도록 축소, G_f,1c는 본 연구 가정으로 분리(과잉귀속 해소) |

### 7.3 LIKELY 서지 DOI/쪽수 확인 대기 (변동 없음)

[2] Krenkel(쪽수) · [3] Glass(AIAA 페이퍼 번호) · [4] Schmidt · [7] Rak · [8] Xu · [16] Chamis 1984/1987 판 확정 · [21] TexGen · [5] Zhang DOI 문자열 · [18] Ge 저자 후미. (Round 1에서 Crossref/doi.org·Semantic Scholar API가 프록시 차단 상태였으며 Round 2에서 재시도하지 않음.)

### 7.4 편집 권한 밖 이관 (S 노드 처리 요망)

- **M2-1** `CALIBRATION_GUIDE.md:52, 135` G1c 귀속 정정 (**Round 2 최우선**).
- **M2-2** `ch1_intro.md:29` 동향 문장에 [23,24,25] 부여 + 위상장·ML 문장 완화.
- m2-1 `[30]` 표기 명확화, m2-2/m2-5 [22] 처리, m2-3 괄호 형식 통일, m2-4 GUIDE §4 "Ge §3.2" 잔존, m2-6 [13] 배치.

---

## 8. Round 2 게이트 의견 (R1 관할)

- **BLOCKER 0건** → R1 관점에서 해석 게이트 유지(**GO**). MAJOR 2건은 모두 산문·문서 층위이며 해석 입력(카드·덱·`ledger.json`)과 무관하다.
- 다음 라운드(R1 부분 재실행) 트리거: ① P-1 원문 PDF 확보(§7.1·§7.2·§7.3 일괄 해소) ② ch3/ch5 초안 작성 시 신규 인용 검수 ③ M2-1·M2-2 반영 후 확인.
