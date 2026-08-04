# CDM-UMAT — C/SiC 반복 열충격 2-스케일 CDM 해석

석사학위논문 프로젝트. **실험 없이 해석만으로** C/SiC 복합재가 반복 열충격을 받을 때
강성·강도가 얼마나, 어디서 저하되는지를 예측하고, **열잔류응력(TRS)을 어떻게 모델링하느냐가
그 예측을 얼마나 바꾸는지**를 정량화합니다.

> 연구 계획·노벨티·검증 전략 전체는 **[`docs/THESIS_PLAN.md`](docs/THESIS_PLAN.md)** 참조.

## 두 개의 계보

| 계보 | 파일 | 상태 | 역할 |
|---|---|---|---|
| **V1_0 (재현·검증)** | `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for` | ✅ 검증 완료, **동결** | Zhang 2022 재현. 논문 Ch.3–4의 신뢰성 근거 |
| **V3_0 (논문 본편)** | `src/UMAT_CSIC_THERMSHOCK_V3_0.for` | ✅ 코드 검증 완료 ⚙️ Abaqus 실행 대기 | 온도의존 물성 + 균열 닫힘 + 거시 CDM + 사이클 손상 |

V3_0은 V1_0의 **엄격한 상위집합**입니다. V1_0 카드를 그대로 넣으면 **비트 단위로 동일한 결과**가
나오며, 이는 회귀 테스트로 강제되어 있습니다(아래 T2). 즉 기존 검증이 깨지지 않습니다.

## V3_0에서 새로 추가된 것

1. **온도의존 물성** — 카드 뒤에 붙는 `f(T)` 배율 테이블, `KPROP_INTERP`가 `TEMP+DTEMP`에서
   선형보간. 테이블 밖은 **클램프(외삽 금지)**. `NT=0`이면 V1_0과 동일.
   *CTE는 여기가 아니라 Abaqus `*Expansion, zero=1050`에 넣습니다* — 무응력 온도 기준
   할선 CTE를 이미 지원하므로 TRS 적분이 정확히 처리됩니다.
2. **단방향 손상(균열 닫힘)** — 열싸이클은 법선변형률의 부호를 매 사이클 뒤집으므로,
   인장에서 생긴 손상은 균열이 닫힐 때 부분적으로 비활성화되어야 합니다. `HCLO ∈ [0,1]`.
   전단 손상은 회복시키지 않습니다. 이력은 건드리지 않고
   할선 강성만 바뀌므로 손상은 여전히 단조입니다.

   > ⚠️ **전단 미회복은 "닫힌 균열면도 미끄러지니까"가 아니라, 실험을 알고서 택한
   > 보수 가정입니다.** `refs/[28]`(Li 2014, **우리와 동일한 2D 평직 CVI C/SiC**)은
   > 압축에서 *"the shear damage is also gradually deactivated"* 를 관측합니다.
   > 다만 회복을 구동하는 것은 **전단이 아니라 수직 압축**입니다 — 횡방향 압축이
   > 박리 계면을 닫아 하중전달을 되살리고, 전단강성이 그 계면에 의존하기 때문입니다.
   > 따라서 올바른 확장은 전단 부호가 아니라 **`HCLO`와 같은 조건(`ε_n < 0`)에서
   > 전단에도 독립 계수 `HCLOS`를 두는 것**입니다. 기본값 `HCLOS = 0`이면 현재 거동과
   > **비트 단위로 동일**하므로 T2 회귀가 그대로 통과합니다.
   > **M6 보정 종료 후에 착수합니다** — 지금 UMAT을 바꾸면 `docs/CH4_...` §4.9-0의
   > 강성 진단이 무효가 됩니다. 상세는 `docs/REFS_CANDIDATES.md` §4.7-(나).
3. **거시 균질화 CDM + 사이클 의존 손상** (`KMACRO31`) — **이 논문의 핵심**.

### 왜 사이클 손상이 필요한가

이력변수 기반 CDM은 **첫 사이클 후 shakedown** 합니다. 같은 열하중을 반복하면 파손지수가
저장된 임계값 `r`을 다시 넘지 못해 `dr = 0`이 되고, **N=1과 N=100의 결과가 같아집니다.**
그러면 "반복 열충격에 의한 열화"라는 주제 자체가 성립하지 않습니다.

```
Δd_cyc = C(T) · <r_drv − RTH>^n · (1 − d_cyc)^(−k) · ΔN
1 − d  = (1 − d_mono)(1 − w·d_cyc)
```

- `r_drv`는 무차원 파손지수(정적 개시에서 1)이므로 **`RTH`는 정적강도 대비 내구한도**,
  **`n`은 Basquin 지수** 역할 → 문헌의 잔여강도-사이클 데이터로 직접 보정 가능
- **`k`의 부호가 물리를 가릅니다**: `k<0` → 포화(균열밀도 포화, 공기 급랭 C/SiC의 실측 거동),
  `k>0` → 가속(산화 지배). `data/literature/README.md` 참조
- ΔN을 `*Field` 변수로 주면 한 증분이 여러 사이클을 대표 → **사이클 도약(cycle jump)**

## 지금 바로 실행 가능한 검증 (Abaqus 불필요)

```bash
bash verification/compile_check.sh          # 두 UMAT 모두 fixed-form 컴파일 + 인터페이스
python3 verification/verify_constitutive.py # V1_0 수식 단위테스트 (기존)
python3 verification/micromech_check.py     # 얀 물성 vs Chamis/Schapery (기존)
python3 verification/verify_thermshock.py   # V3_0 신규 기능 22개 체크 + 보정 + 그림
python3 verification/cross_check_fortran.py # ★ 컴파일된 Fortran vs 검증된 Python 모델
```

`verify_thermshock.py`가 확인하는 것:

| | 내용 |
|---|---|
| T1 | 보간이 노드에서 정확, 사이는 선형, 밖은 클램프 |
| T2 | **회귀**: `NT=0, HCLO=0`이면 V3_0 얀 법칙 = 검증된 V1_0 법칙 (기계정밀도) |
| T3 | `f(T)` 적용 결과 = 손으로 배율을 곱한 카드 (기계정밀도) |
| T4 | 균열 닫힘이 `HCLO` 비율만큼 강성을 회복시키고 이력은 불변 |
| T5 | **shakedown 실증**: 단조 CDM은 N=2~60 손상 drift = `0.00e+00`, 사이클 법칙은 계속 진행 |
| T6 | 사이클 도약이 `k=0`에서 정확, `k≠0`에서 오차 0.03 % |

`cross_check_fortran.py`는 한 단계 더 갑니다. Python 검증은 *모델*이 맞다는 것이지
*Fortran*이 맞다는 뜻이 아니므로, `verification/kmacro_driver.f`로 **실제 UMAT 서브루틴을
직접 호출**해 응력·강성·전 STATEV를 무작위 상태 64개에서 비교합니다(현재 전부 통과,
최대 상대편차 ~1e-15). 실제로 이 크로스체크가 Python 미러의 누락을 잡아냈습니다.

## RVE를 가상 시험기로 쓰기

거시 모델에 "유효물성"만 넘기면 손상이 전달되지 않아 강성이 절대 떨어지지 않습니다.
RVE는 **거시 CDM 카드 전체**를 만들어내는 가상 시험기로 씁니다.

```bash
# 1) 덱 생성 (TexGen 메시로부터)
python3 abaqus/make_rve_virtual_tests.py mesh.inp --temps 23 500 1000 --trs on
#   -> RVE_ELAS_T*.inp   6개 단위 거시변형 모드 (손상 OFF, 팽창 OFF) -> Cbar(T)
#      RVE_CTE_T*.inp    구속 2스텝의 응력 차 -> alphabar(T)
#      RVE_STR_*_T*.inp  1050 C 냉각 후 파손까지 -> 균질화 강도 + 연화
#      RVE_COND.inp      정상 열전도 3방향 -> kbar (급랭 해석에 필수)

# 2) 실행 후 거시 카드 조립
abaqus python postprocess/homogenize.py RVE --temps 23 500 1000
#   -> RVE_macro_card.inp        *User Material MACRO 카드 (47+8*NT 슬롯, f(T) 포함)
#      RVE_macro_expansion.inp   *Expansion, type=ORTHO
#      RVE_homogenised.csv       논문 표에 넣을 전 수치
```

> `--shear-order`: TexGen 버전에 따라 드라이버 3/4/5 ↔ 전단성분 대응이 다릅니다.
> **첫 실행에서 출력되는 raw Cbar로 반드시 확인**하고 플래그를 고정하세요.

## 저장소 구조

```
docs/THESIS_PLAN.md            연구계획 — 치명적 이슈, 노벨티 지형, 챕터, 마일스톤
src/
  UMAT_CSIC_RVE_ZHANG2022_V1_0.for   재현·검증 UMAT (동결)
  UMAT_CSIC_THERMSHOCK_V3_0.for      논문 UMAT: KYARN31/KMTRX31/KMACRO31
abaqus/
  ZHANG2022_*_V1_0.inp / _V2_0.inp   Zhang 재현 덱 (기존)
  assemble_inp.py                    임의 TexGen 메시에 카드+스텝 접합
  make_rve_virtual_tests.py          RVE 가상시험 덱 생성기
  MESH_REGEN_GUIDE.md
verification/
  VERIFICATION_REPORT.md             V1_0 물성·수식 감사 (기존)
  CALIBRATION_GUIDE.md               미공개 파라미터 보정 (기존)
  verify_constitutive.py             V1_0 수식 단위테스트 (기존)
  micromech_check.py                 얀 물성 검증 (기존)
  verify_thermshock.py               V3_0 기능 검증 + 문헌 보정
  cross_check_fortran.py             컴파일된 Fortran vs Python 모델
  kmacro_driver.f                    단일점 Fortran 드라이버
  compile_check.sh                   두 UMAT 컴파일 검증
  figures/
postprocess/
  extract_ss_curve.py                거시 sigma-eps 추출 (기존)
  plot_compare.py                    Table 3 대조 (기존)
  homogenize.py                      ODB -> 거시 CDM 카드 조립
data/
  literature/
    csic_thermal_shock.csv           반복 열충격 검증 데이터 (신뢰도 등급 표기)
    README.md                        출처·인용 가능 여부·추가 확보 목록
  properties/
    fibre_T300_vsT.csv               구성재 온도의존 물성 (섬유)
    matrix_SiC_vsT.csv               구성재 온도의존 물성 (매트릭스)
    eval_correlations.py             문헌 상관식 코드화 + 논문 자체 값과 검산
    temperature_blocks.inp           생성된 UMAT 카드 블록 + *Expansion
    README.md                        열 정의, 단위 규약, CTE 기준 변환
refs/
  README.md                          ★ 참고문헌 색인 + 추출 결과 + 발견 사항
  [01]..[14] *.pdf                   원문 (위치 판단은 refs/README.md §0)
```

## 온도의존 물성 파이프라인

```bash
python3 data/properties/eval_correlations.py --check   # 문헌 상관식 검산 8종
python3 abaqus/build_temperature_tables.py             # -> temperature_blocks.inp
python3 abaqus/build_temperature_tables.py --selftest  # CTE 기준 변환 검증 5종
```

구성재 CSV에 행을 추가하면 Chamis/Schapery를 각 온도에서 재계산해 얀 `f(T)` 테이블과
`*Expansion` 블록을 자동 생성합니다. 현재 **23 / 500 / 1000 °C 3점**이 들어가 있습니다.

## 현재 상태와 다음 할 일

- ✅ V1_0 물성·수식 검증 완료 (`VERIFICATION_REPORT.md`)
- ✅ V3_0 3개 기능 구현 + 코드 검증 + Fortran/Python 크로스체크 통과
- ✅ RVE 가상시험 덱 생성기 + 균질화 후처리 작성
- ✅ 문헌 검증 앵커 확보 (SUN2002: 100회 후 83 %, 임계 N≈50, 50회 이후 포화)
- ⚙️ **병목 — M1**: 사용자 PC의 Abaqus로 기존 V2_0 3케이스를 실행하고 Zhang Table 3에
  맞춰 보정. 이 결과 없이 그 위를 쌓으면 잘못된 물성 위에 논문을 짓게 됩니다.
- ⚠️ 거시 카드의 탄성·강도 기본값은 **자리표시자**입니다. RVE 가상시험 결과로 대체되기
  전까지는 어떤 수치도 인용하지 마세요.
- ⚠️ 열물성(k, rho, cp)은 **자리표시자**입니다 (`make_rve_virtual_tests.py` 헤더 참조).
