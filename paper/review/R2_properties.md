# R2 — 물성·해석입력 감사 보고서 (material-property & solver-input audit)

- 감사자: R2 (pre-run gate)
- 일자: 2026-08-10
- 대상: `abaqus/ZHANG2022_{RT23,T500,T1000}_V2_0.inp`, `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for`,
  `calibration/{make_cards.py, ledger.json, evaluate.py}`, `verification/*`, `paper/ch1·ch2·ch4`
- 판정 기준: BLOCKER = 해석을 무효화하는 잘못된 수치(덱/카드), MAJOR = 본문(prose)에만 있는 잘못된 수치, MINOR = 표기·문서상 결함

---

## 1. 요약 및 판정

**판정: GO** (조건부 아님 — 덱은 그대로 제출 가능. 단, Stage A를 의도한다면 §6.1의 `--baseline` 선행 필수)

- 세 덱의 `*User Material` 카드 2종(매트릭스 22슬롯, 얀 38슬롯)은 **세 덱 간 바이트 단위로 동일**하고,
  `make_cards.py --dry-run` 출력·`ledger.json` iteration 1·`CALIBRATION_GUIDE.md` §1·
  `VERIFICATION_REPORT.md` §2와 **전 슬롯 일치**. 탄성·CTE 12상수는 감사자가 Chamis/Schapery를
  **독립 재계산**하여 카드값과 일치함을 재확인(최대 0.142 %, α2 — 보고서 §2.2와 동일).
- 덱 비카드 설정(무응력온도 1050, CTE, Depvar, 섹션·배향, 3-스텝, 적용변형, `*Static` 증분,
  double precision 명령) 모두 근거 문서와 일치. **BLOCKER 0건.**
- 발견 사항: **MAJOR 1건** (ch4/검증보고서 표의 α1 Chamis 계산치 표기 1.0706×10⁻⁶ — 올바른 값은
  1.0709×10⁻⁶; 카드값·오차율 주장은 정상), **MINOR 3건** (문서·스크립트 표기 수준).
- 검증 스크립트 2종 재실행 **모두 PASS**, gfortran 컴파일 검사 **PASS**.

| 심각도 | 건수 | 내용 |
|---|---|---|
| BLOCKER | **0** | — |
| MAJOR | **1** | α1 Chamis 계산치 표기 오류 (ch4 §4.2 표 + VERIFICATION_REPORT §2.2 표, 본문 한정) |
| MINOR | **3** | §5.2 참조 |

---

## 2. 재실행한 검증 스크립트 결과 (Task 1)

| 스크립트 | 결과 | 비고 |
|---|---|---|
| `verification/micromech_check.py` | **PASS** — 12개 얀 상수 전부 MATCH, worst 0.142 % (α2), "VERIFIED" | 의존성 없이 즉시 실행됨. Vf=0.79194 역산, 복합재 Vf≈39.6 % 재현 |
| `verification/verify_constitutive.py` | **PASS** — 단위테스트 7건 전부 PASS ("ALL KERNELS REPRODUCE THE PAPER EQUATIONS") | 초기 실행 시 `numpy`/`matplotlib` 부재로 실패 → `pip3 install numpy matplotlib` 후 정상 실행. 수치 검증은 matplotlib과 무관하게 전부 수행됨. 그림 2종 재생성 |
| `verification/verify_fullmodel.py` (보너스) | 실행 완료, `figures/fullmodel_vs_baseline.png` 재생성 | 수치 게이트 없는 시각 비교 스크립트 (PASS/FAIL 출력 없음 — 설계상 그러함) |
| `verification/compile_check.sh` (보너스) | **PASS** — "COMPILE OK: UMAT is valid fixed-form Fortran; interfaces resolve." | gfortran 설치 후 실행 |

단위테스트 세부 (verify_constitutive.py 출력):
Eq.17/19 3케이스, Eq.15/16 vonMises(155.81078), Eq.11 Hashin fib-t(1.003466),
Eq.13 Hashin trn-t(0.982379), Eq.19-21 crack-band(0.320359) — 모두 code=ref PASS.
검증보고서 §3에 인용된 수치와 자릿수까지 일치.

---

## 3. 카드 감사표 (Task 2)

교차 대조한 4개 소스: (a) VERIFICATION_REPORT §2, (b) CALIBRATION_GUIDE §1,
(c) ledger.json iteration 1, (d) `make_cards.py --dry-run` 렌더링.

**전수 대조 결과: 60슬롯(얀 38 + 매트릭스 22) × 3덱 전부 일치. 불일치 0건.**

### 3.1 일치 집계

| 검사 | 방법 | 판정 |
|---|---|---|
| 세 덱 카드 동일성 (온도독립 가정) | `diff` 3쌍 — 카드 영역 차이 0 (덱 간 차이는 스텝 3곳뿐: 가열스텝 유무·목표온도·적용변형) | **일치** |
| 덱 카드 = `make_cards.py --dry-run` | 카드 블록 추출 후 diff — 6블록(3덱×2카드) **바이트 단위 동일** | **일치** |
| 덱 카드 = ledger iter 1 params (24개 knob) | Xt 2835 / Xc 1956 / Yt 80 / Yc 350 / S12 120 / S13 120 / S23 100 / A₄종 2.0 / eta_y 0.02 / G1t·G1c 12.5 / Gtt·Gtc 0 / X_PO 700 / rF 3.0 / K1 8000 / eta_m 0.02 / Gm_t·Gm_c 0.031 / SY0 250 / HISO 100000 | **일치** |
| 얀 탄성·CTE 12상수 = 보고서 §2.2 카드열 | E1 254967.228042, E2=E3 44321.737572, ν12=ν13 0.247516386, ν23 0.395813581, G12=G13 26431.515264, G23 15876.667974, α1 1.070925962822e-06, α2=α3 3.324908565604e-06 — 마지막 자리까지 일치 | **일치** |
| 매트릭스 탄성·강도 = 보고서 §2.1 (Zhang Table 2) | E 350000 MPa, ν 0.20, Xt=Xc 310 MPa, α 4.5e-06, zero=1050 | **일치** |
| 감사자 독립 재계산 (Chamis/Schapery, 자체 코드) | Vf=(Em−E1card)/(Em−Ef1)=0.7919398 → 카드 8상수 오차 ≤0.005 % (α2만 0.142 %) — 보고서 주장과 동일. Xt=Vf·3580=2835.14→카드 2835.0, Xc=Vf·2470=1956.09→1956.0 (가이드 명기대로 반올림) | **일치** |
| 고정 슬롯 (dmax 0.99·0.99, cutback 1.15/0.75/0.50, max_djump 0.10, freeze 3.0, min_PNEWDT 0.25, enable 1.0, 매트릭스 KEY 슬롯22=30.0) | UMAT 헤더 PROPS 주석·make_cards 고정 문자열과 대조 | **일치** |
| UMAT 가드 정합 | NPROPS 38/22 요구 = `constants=38/22`; `PROPS(22)=30.0` 키 = 카드 슬롯22 `30.0`; 이름 매칭 `YARN`/`MATRIX` ⊂ 재료명 | **일치** |

### 3.2 불일치 상세

없음.

---

## 4. 덱 비카드 설정 감사표 (Task 3)

3덱 공통 확인 (라인 번호는 세 덱 동일):

| 항목 | 덱 값 | 근거 소스 | 판정 |
|---|---|---|---|
| `*Expansion, zero=1050.` 매트릭스 (L219464) | `4.5e-06,` | 보고서 §2.1 / Zhang Table 2 / OUTLINE §2.1 | 일치 |
| `*Expansion, type=ORTHO, zero=1050.` 얀 (L219503) | `1.070925962822e-06, 3.324908565604e-06, 3.324908565604e-06` | 보고서 §2.2, 독립 재계산 | 일치 |
| `*Depvar` 매트릭스 = 20 | UMAT 요구 `NSTATV>=20` (미달 시 XIT), SDV 1–20 명명 리스트가 UMAT 헤더 레이아웃과 1:1 | UMAT 헤더 + 가드 코드 | 일치·충분 |
| `*Depvar` 얀 = 16 | UMAT 요구 `NSTATV>=16`, SDV 1–16 명명 일치 | 〃 | 일치·충분 |
| 솔리드 섹션 | Matrix→SIC_MATRIX_DAMAGE; Yarn0–3→CSIC_YARN_DAMAGE, `Orientation=TexGenOrientations` (5개 섹션, `*Orientation` L208473 정의 존재) | 과업 명세 | 일치 |
| 요소 커버리지 | Matrix 91,554 + Yarn0–3 82,851 = 174,405 = 전체 C3D4 수 (누락 없음); 절점 34,049 + PBC 더미 6 | 직접 계수 | 일치 |
| 스텝 구성 | RT23: 냉각(1050→23)→인장. T500/T1000: 냉각→가열(23→500/1000)→인장. `*Initial Conditions, type=TEMPERATURE` = 1050 | 보고서 §4 / 논문 §3.2.4 | 일치 |
| 적용 변형률 | `ConstraintsDriver0, 1, 1,` 0.001500 / 0.003200 / 0.004800 (= 0.15/0.32/0.48 %) — `evaluate.py`의 APPLIED_STRAIN과도 일치 | 가이드 §6 / 보고서 §4 | 일치 |
| `*Static` 냉각 | `0.001, 1.0, 1.0E-12, 0.0025` | 가이드 §4 (초기 1e-3~5e-4, 최소 1e-12, 최대 2.5e-3) | 일치 |
| `*Static` 인장 | `0.0005, 1.0, 1.0E-12, 0.0025` | 〃 | 일치 |
| `*Static` 가열 (T500/T1000만) | `0.005, 1.0, 1.0E-12, 0.01` | 가이드 §4 범위 밖이나 가열은 잔류응력 완화(제하) 방향의 순한 스텝 — 의도된 큰 증분으로 판단. §5.2 MINOR-1 | 허용 |
| 수렴 보조 | `*Controls` time incrementation 8,10,,30,…,20 / field 0.08 / line search 5 — 3덱·전 스텝 동일 | 덱 내 주석 | 일치 |
| freeze_step=3.0 커버리지 | 손상발전 조건 `KSTEP<=FREEZE` — RT23(2스텝)·T500/T1000(3스텝) 전 스텝에서 손상발전 활성 | UMAT KYARN30/KMTRX30 | 일치 |
| dmax 상한 집행 | KMIX1T 목표값도 호출측에서 `TAR=MIN(DMAX1,TAR)`로 0.99 상한 적용 확인 (ch2 §2.4 주장과 정합). 결합손상 d1·dt는 내부 0.999 클램프 — 수치 안전장치, 문제 없음 | UMAT 코드 | 일치 |
| 강체 구속 | MasterNode1 1–3 고정, PBC 더미절점 34050–34055 | 덱 | 일치 |
| nlgeom=NO (전 스텝) | 최대 적용변형 0.48 % — 소변형 가정 타당 | — | 일치 |
| 출력 요청 | `*Element Output ... SDV` 포함 (Stage A의 SDV 점검 가능), history에 Driver0–5 U/RF (곡선 추출 요건) | extract_ss_curve.py | 일치 |
| 실행 명령의 `double` | README L53–54, CALIBRATION_GUIDE §0, calibration/README A1 모두 `double` 포함 (UMAT 배정밀도 가정) | 가이드 §4 | 일치 |

---

## 5. 단위 정합성 및 챕터 수치 spot-check (Task 4)

### 5.1 단위계 (MPa–mm–N)

| 항목 | 확인 내용 | 판정 |
|---|---|---|
| 길이 | RVE 절점 좌표 범위 3.5×3.5×0.44 mm (mm 스케일) | 정합 |
| 응력·탄성계수 | 카드 MPa (350000, 254967, …) = N/mm² | 정합 |
| 파괴에너지 | Gf N/mm (12.5 / 0.031) — UMAT 헤더 주석 "N/mm" 명기, CELENT(mm)와 곱해 사용 | 정합 |
| CTE | /K (4.5e-06 등), 온도 °C (1050/23/500/1000) — 증분 기반이라 °C/K 혼용 무해 | 정합 |
| 균열대 스냅백 점검 | 평균 lc≈0.031 mm에서 매트릭스 g0·lc≈0.0043 < Gm=0.031 → 폐형식 A 사용(클램프 안 걸림); 얀 1t g0·lc≈0.49 ≪ 12.5 | 정합 (메시 재생성 시 lc>≈0.23 mm면 매트릭스 A=50 클램프 진입 — MESH_REGEN 시 참고) |
| 후처리 | extract_ss_curve.py 출력 `sigma_xx_MPa`, 부피 mm³; evaluate.py 목표 MPa | 정합 |

### 5.2 챕터 수치 spot-check (ch1 3건 + ch2 14건 + ch4 12건)

일치 확인(발췌): ch1 — 128.45/179.42/199.15, 116.17±8.78/160.19±14.83/173.28±12.94, T0=1050.
ch2 — Em 350 GPa·νm 0.20·Xm 310·αm 4.5e-6·T0 1050; Vf 0.792 대입값 E1 254,967 / E2 44,322 /
ν12 0.2475 / ν23 0.3958 / G12 26,431 / G23 15,877 / α1 1.071e-6 / α2 3.325e-6 (카드 반올림과 정합);
0.142 %·39.6 %; Xt=Vf·3580=2835·Xc=Vf·2470=1956; Gf,1t=12.5; A 상한 50(=KABAND 클램프 확인);
X_PO≈0.2–0.3Xt(카드 700/2835=0.247)·rF 2–4(3.0)·K1≈E1의 수 %(8000/254967=3.1 %); SY0≈250·HISO≈1e5;
Gf,m=0.031; η=0.02; dmax=0.99; Δp̄=(σ_tr−σY)/(3G+H)(UMAT DLAM 식과 동일); 식(2.15)–(2.16)=KMIX1T,
식(2.21)=GAM=Δt/(η+Δt) 코드와 동일. ch4 — §4.2 표(보고서 §2.2 전재), Gm 145.83 vs 146 GPa 0.1 %,
메시 174,405 vs 116,724(전자는 직접 계수로 실측 일치), 34,049 절점, §4.3 인용 수치(1198/78.7/309.9 —
V1 임시강도임을 명기, 정직), §4.5.1 시작값 전체 = 가이드 §1과 일치, 0.15/0.32/0.48 %.

**발견된 불일치:**

| # | 심각도 | 위치 | 내용 | 영향/권고 |
|---|---|---|---|---|
| 1 | **MAJOR** | `paper/ch4_verification.md` §4.2 표 α1 행 + `verification/VERIFICATION_REPORT.md` §2.2 표 α1 행 | Chamis/Schapery "계산치" 열이 **1.0706×10⁻⁶**으로 표기. 표가 명시한 방법(역산 Vf=0.79194 단일 적용) 대로면 **1.0709×10⁻⁶** (감사자 재계산 1.070926e-06, 카드와 0.0000 %). 1.0706은 Vf를 0.792로 반올림했을 때의 값(오차 0.033 %)이라 같은 행의 "0.000 %"·카드값과 표기상 모순 | 덱·해석 무영향(카드값 정상). ch4·보고서에서 1.0706→1.0709로 수정 권고. 표시 자릿수 기준 독자가 오차 재계산 시 0.03 %가 나와 "0.000 %" 주장과 충돌 |
| 2 | MINOR | `CALIBRATION_GUIDE.md` §4 | "*Static: 초기 1e-3~5e-4, 최소 1e-12, 최대 2.5e-3 (이미 설정됨)" — 가열스텝(0.005/0.01)의 예외를 언급하지 않음. 덱 자체는 의도된 설정으로 판단 | 문구에 "냉각·인장 스텝 기준, 가열스텝은 0.005/0.01" 각주 권고 |
| 3 | MINOR | `verification/verify_fullmodel.py` L31 | 재료점 검증용 Xt=Vf·3580=2835.145로 카드(2835.0)와 0.005 % 상이 | 시각 비교용 스크립트 한정, 무해. 카드값 2835.0 직접 사용 권고 |
| 4 | MINOR | 재현성 | `verify_constitutive.py`·`verify_fullmodel.py`가 numpy/matplotlib 필요하나 요구사항이 어디에도 명시 안 됨(이 환경에도 미설치 상태였음) | README "Verify the code now" 절에 `pip install numpy matplotlib` 1줄 추가 권고 |

참고(결함 아님): 보고서 §2.2 α2 행의 계산치 3.3296e-6·오차 0.142 %는 감사자 재계산(3.3296274e-06,
0.1419 %)과 정확히 일치 — α2의 0.142 %는 Schapery 근사 자체의 잔차로 문서화된 값이며 정상.

---

## 6. 해석 전 체크리스트 — 첫 Abaqus 실행 (Stage A 기저) (Task 5)

### 6.1 실행 전 (필수 순서)

1. [ ] **Stage A 기저 카드로 전환** (현재 리포지토리 덱은 풀모델 상태: SY0=250, X_PO=700):
   ```bash
   python3 calibration/make_cards.py --stage A --baseline --note "Stage A 기저 실행"
   ```
   동작(코드 확인 완료): SY0→0.0, X_PO→0.0만 변경(소성 OFF·Eq.18 OFF), 나머지 knob 유지,
   세 덱 동시 갱신 + ledger iteration 2 기록. 검증된 탄성·CTE 슬롯은 잠겨 있어 훼손 불가.
2. [ ] 갱신 확인: 매트릭스 카드 3행 첫 값 `0.0`(SY0), 얀 카드 5행 4번째 값 `0.0`(X_PO), 3덱 동일.
   (`python3 calibration/make_cards.py --dry-run`으로도 미리보기 가능 — 단 dry-run은 ledger 최신
   params 기준이므로 --baseline 이후에는 0이 찍히는 것이 정상)
3. [ ] Abaqus 머신에 Fortran 컴파일러 연동 확인 (`abaqus verify -user_std` 권장).
4. [ ] 작업 디렉터리에 `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for`와 3개 V2_0 덱 복사/경로 확인.

### 6.2 실행 명령 (double 필수 — UMAT 배정밀도 가정)

```bash
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V2_0.inp  user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
abaqus job=Job-T500  input=abaqus/ZHANG2022_T500_V2_0.inp  user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
abaqus job=Job-T1000 input=abaqus/ZHANG2022_T1000_V2_0.inp user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
```

메모리·시간: 174,405 C3D4 / 34,055 절점, 스텝당 최소 400+ 증분(냉각 초기 Δt=1e-3, 상한 2.5e-3)
— 잡당 수 시간 각오. `*Restart` 파일이 냉각 20회/가열 5회/인장 20회 간격으로 기록됨.

### 6.3 실행 중 감시

- [ ] .sta에서 냉각 스텝 완주(누적시간 1.0 도달) — 냉각 미완주면 이후 결과 전부 무효.
- [ ] .msg의 UMAT 에러 문구 없음: "ZHANG2022 YARN card needs NPROPS=38…" / "MATRIX card needs
  NPROPS=22 with PROPS(22)=30.0…" / "3-D solid elements only." (뜨면 카드/요소 오배정 신호 — 본 감사
  기준으로는 발생하지 않아야 정상).
- [ ] 시간증분이 1e-12 부근까지 추락하면 중단하고 가이드 §4 (eta 0.02→0.05, 초기증분 축소) 적용.

### 6.4 실행 후 (Stage A 게이트)

```bash
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb    # -> Job-RT23_ss.csv
abaqus python postprocess/extract_ss_curve.py Job-T500.odb
abaqus python postprocess/extract_ss_curve.py Job-T1000.odb
python3 calibration/evaluate.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv --stage A
```

- 산출물: `Job-*.odb/.dat/.msg/.sta`, `Job-*_ss.csv` (열: eps_xx, sigma_xx_MPa, time),
  evaluate 게이트표 + ledger iteration 2에 results/loss/gates 기록.
- Stage A PASS 조건(코드 확인): 세 온도 모두 곡선 존재 + 최종변형 ≥ 0.9×적용변형(0.0015/0.0032/0.0048).
- [ ] SDV 점검(보고서 §5·가이드 §3): 냉각 직후 매트릭스 SDV1(DMT) 광범위 ≈1 (논문: 845 °C에서 100 %),
  얀 횡방향 SDV3(DYTT) 발생 여부.
- [ ] Stage A에서는 강도값이 목표(128.45/179.42/199.15)와 다른 것이 **정상** (소성·Eq.18 OFF 기저).

### 6.5 Stage B 진입 시 주의 (미리 경고)

- `make_cards.py`는 **ledger 최신 params를 승계**하므로 --baseline 이후에는 SY0=0·X_PO=0이 유지됨.
  Stage C/D에서 풀모델 복귀 시 반드시 명시적으로 `--set X_PO=700` / `--set SY0=250` (또는 보정값)을
  넣을 것 — 안 넣으면 Eq.18/소성이 꺼진 채 돌아 재실행 낭비가 발생한다.
- 세 덱 카드 동일성은 make_cards가 강제하므로 카드 수동 편집 금지.

---

## 부록 — 감사 방법 요약

- 카드 추출: 각 덱 L219466–219476(매트릭스), L219497–219502(얀) 블록을 awk로 추출,
  `make_cards.py --dry-run` 출력과 diff (6블록 모두 IDENTICAL).
- 덱 간 차이: `diff` 전수 — 카드·섹션·PBC 영역 차이 0, 스텝 영역(가열 유무·온도·적용변형)만 상이.
- 독립 재계산: 감사자 자체 Python으로 Chamis/Schapery 8식 + Vf 역산 + Xt/Xc 혼합법칙 재계산.
- UMAT 대조: PROPS 주석(L44–57)·NSTATV 가드(L96–116)·KMIX1T(L491)·KABAND(L515)·소성 반환사상
  (L379–381)·점성 정규화(L235–236, 424–425)·freeze 조건 직독.
- 요소/절점 계수: 덱 파싱으로 C3D4 174,405개·절점 34,049(+더미 6)·ElSet 합계 = 전체 확인.
