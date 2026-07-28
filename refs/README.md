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
| 09 | `[09] 1st T300 탄소섬유 열전도비열 물성.pdf` | **Pradère, Batsale, Goyhénèche, Pailler, Dilhaire**, *Thermal properties of carbon fibers at very high temperature*, **Carbon 47 (2009) 737–743** | `Cp(T)`, `k(T)` (PANEX 33: E=230 GPa, ρ=1.75 g/cm³, k=75 W/m·K @1500 K) | ⚠️ **미추출** — 다음 할 일 |

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

### 노벨티 포지셔닝 (수치 추출 아님, 논문 §2 문헌고찰용)

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

## 3. 남은 일

1. **[09] Pradère 2009 추출** — 섬유 `k1`, `k2`, `cp`, `rho`. 급랭 해석에 필요한 마지막 조각.
2. **[03] zhang2012 디지타이즈** — 잔여 탄성계수 vs 사이클 수 곡선 → `data/literature/`
3. **SiC 강도 vs 온도 출처 확보** — 현재 `fX`, `fY`, `fS` 매트릭스 계열이 전부 1.0 고정
4. **[05b] skinner2021 정독** — 노벨티 진술 재점검
