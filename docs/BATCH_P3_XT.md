# P3 배치 — 얀 XT 를 논문 자신의 값으로 (421 → 2835)

**변수는 하나.** 얀 카드 `PROPS(11)`. 나머지는 P2 와 전부 동일 —
같은 메쉬, 같은 span, 같은 램프, 같은 eta.

**사전등록 완료.** 예측은 `verification/PAPER_DEVIATION_REGISTER.md`
§5.23E 에 배치 전에 적혀 있다. 결과를 보고 설명을 맞추지 않기 위해서다.

## 왜 이 배치인가

온도 강화 부재(§6-10)와 워프 종 손상률 절반(§6-9), 두 최대 미해결
항목이 **같은 뿌리**로 좁혀졌다. 얀 Eq.11 은

```
FI1T = √[ (σ11/XT)² + (τ12/S12)² + (τ13/S13)² ]
```

인데 우리 XT 는 강도를 맞추려 넣은 역보정 **421** 이고 전단은 **120**
이다. 그래서 σ11 이 지배하고, 얀이 강도를 정하고, 잔류응력 완화가
얀에는 **손해**라서 온도가 오르면 강도가 떨어진다.

논문 자신의 값 **2835** (= Table 1 X_f,t 3580 × Vf 0.79194) 를 쓰면
σ11 항이 `(421/2835)² = 2.2 %` 로 죽고 전단이 지배한다 — 논문이 본문에
서술하는 그 기구다.

**단일적분점에서는 이미 확인됐다** (`verify_diagnostic_inert.sh`):
같은 변형경로에서 XT 만 바꾸면 개시 시 전단분율이
**0.1096 → 0.8481**. 남은 질문은 RVE 에서도 그런가다.

## 한 배치로 답하는 질문 (§5 요건)

1. 온도 추세의 **부호**가 뒤집히는가
2. 워프 종 손상률이 논문(60.67 / 44.38 / 32.12 %)에 가까워지는가
3. 얀 개시가 실제로 전단 주도로 넘어가는가 — **SDV17 이 직접 답한다**
4. 논문 얀 강도의 강도 예측력 (23 °C 가 128.45 로 가는가)
5. 세 온도 손상률·히스토그램·손상 후 균질화 강성

## 준비 (순차적 진행 — 발사 전에 전부 끝낼 것)

### 1) 폴더

| | 23 °C | 500 °C | 1000 °C |
|---|---|---|---|
| 폴더 | `E:\LTH\Try_P3` | `E:\LTH\Try_P3T500` | `E:\LTH\Try_P3T1000` |
| job | `CSIC_t23_p3` | `CSIC_t500_p3` | `CSIC_t1000_p3` |
| 태그 | `_P3` | `_P3T500` | `_P3T1000` |
| 코어 | 10 | 10 | 10 |

P2 계열 폴더에서 **덱과 `.ori` 를 복사**한다 (`.ori` 없으면 즉시 실패).
UMAT 은 `src/UMAT_CSIC_RVE_DAMAGE_V2_7D.for` 를 각 폴더에 넣는다.

### 2) 덱 두 곳을 고친다 — 도구로, 손으로 말고

```bat
:: (a) 지금 값 확인. 421.0 이 나와야 한다
python E:\LTH\patch_material_prop.py --material YARN --slot 11 --show ^
       Try_P3\*.inp Try_P3T500\*.inp Try_P3T1000\*.inp

:: (b) 진단 SDV17 자리 만들기 — 미리보기 후 적용
python E:\LTH\patch_depvar_yarn.py Try_P3\*.inp Try_P3T500\*.inp Try_P3T1000\*.inp
python E:\LTH\patch_depvar_yarn.py --apply Try_P3\*.inp Try_P3T500\*.inp Try_P3T1000\*.inp

:: (c) XT 교체 — --expect 로 엉뚱한 덱 방지
python E:\LTH\patch_material_prop.py --material YARN --slot 11 ^
       --value 2835.0 --expect 421.0 ^
       Try_P3\*.inp Try_P3T500\*.inp Try_P3T1000\*.inp
python E:\LTH\patch_material_prop.py --material YARN --slot 11 ^
       --value 2835.0 --expect 421.0 --apply ^
       Try_P3\*.inp Try_P3T500\*.inp Try_P3T1000\*.inp
```

**(b) 미리보기에서 얀만 잡히고 기지 `*Depvar 20` 은 안 잡히는지 눈으로
확인한 뒤 `--apply` 를 돌린다.** `--expect 421.0` 이 있으면 P2 덱이
아닌 것을 실수로 지정했을 때 멈춘다.

### 3) 발사 전 최종 확인

```bat
python E:\LTH\patch_depvar_yarn.py   --check Try_P3\*.inp
python E:\LTH\patch_material_prop.py --material YARN --slot 11 --show Try_P3\*.inp
```

얀 `*Depvar 17`, 슬롯 11 = `2835.0`, 기지 `*Depvar 20` 이면 준비 끝.

## 발사 (병렬 가능 — 창 3개, 10코어씩 = 30/32)

```bat
:: 창 1
cd /d E:\LTH\Try_P3
abaqus job=CSIC_t23_p3 input=<덱이름> user=UMAT_CSIC_RVE_DAMAGE_V2_7D.for cpus=10 int

:: 창 2
cd /d E:\LTH\Try_P3T500
abaqus job=CSIC_t500_p3 input=<덱이름> user=UMAT_CSIC_RVE_DAMAGE_V2_7D.for cpus=10 int

:: 창 3
cd /d E:\LTH\Try_P3T1000
abaqus job=CSIC_t1000_p3 input=<덱이름> user=UMAT_CSIC_RVE_DAMAGE_V2_7D.for cpus=10 int
```

## 발사 직후 30분 안에 확인할 것

```bat
type E:\LTH\Try_P3\CSIC_t23_p3.sta
```

1. 냉각 스텝이 정상 진행하는가 (증분이 1e-7 바닥에 붙지 않는가)
2. 승온 스텝시간이 의도한 값인가 (1000 덱은 2.05)
3. `.msg` 에 `GF1T out of range` 가 **없는가** — 있으면 덱 슬롯 32 가
   잘못된 것이니 즉시 중단

이 셋이면 밤새 두고 가도 된다.

## 냉각에 대한 주의 — P2 와 같을 것이라 가정하지 말 것

P2 계열 세 런은 냉각 손상률이 소수점 15자리까지 같았다. **P3 도
자기들끼리는 같아야 한다.** 그러나 **P3 의 냉각이 P2 의 냉각과 같으리라
가정하면 안 된다.** XT 는 Eq.11 에 들어가므로, 냉각 중 얀이 국부적으로
종방향 인장을 받는 적분점이 하나라도 있으면 냉각 손상이 달라진다.

냉각 중 얀 종방향은 대체로 압축(−341.8 MPa)이라 `SE(1)<0` 경로를 타서
XT 를 안 쓴다. 그래서 **거의 같을 것으로 예상되지만, 확인 없이 단정하지
않는다.** 다르면 그 자체가 결과다.

```bat
:: 세 P3 런끼리 냉각이 같은지 (병렬 가능 — 창 3개)
abaqus python E:\LTH\extract_cooling_damage.py CSIC_t23_p3.odb   --stride 5 --tag _P3
abaqus python E:\LTH\extract_cooling_damage.py CSIC_t500_p3.odb  --stride 5 --tag _P3T500
abaqus python E:\LTH\extract_cooling_damage.py CSIC_t1000_p3.odb --stride 5 --tag _P3T1000
```

## 끝난 뒤 추출 (§5 — 한 odb 에서 뽑을 수 있는 건 전부)

```bat
:: (1) 인장 곡선 + 강도            (병렬 가능 — 창 3개)
abaqus python E:\LTH\extract_tension.py CSIC_t23_p3.odb --tag _P3

:: (2) 단계점 찾기                 (순차 — (1) 의 CSV 필요)
python E:\LTH\find_frames.py Try_P3\tension_damage_P3.csv --stages --paperstage 23

:: (3) 히스토그램 + SDV17          (순차 — (2) 의 프레임 번호 필요)
abaqus python E:\LTH\extract_damage_histogram.py Try_P3\CSIC_t23_p3.odb ^
       --frames <(2)에서 나온 번호> --tag _P3

:: (4) 손상 후 균질화 강성          (병렬 가능 — HOM_* 스텝)
abaqus python E:\LTH\extract_homogenization.py Try_P3\CSIC_t23_p3.odb --tag _P3
```

**(3) 이 이번 배치의 핵심 산출물이다.** `yarn_shear_frac_P3_f<NN>.csv`
에 개시 기구가 나온다:

| 열 | 뜻 |
|---|---|
| `mean_shear_frac` | 0 에 가까우면 σ11 주도, 1 에 가까우면 전단 주도 |
| `pct_shear_driven` | 개시 요소 중 전단분율 > 0.5 인 비율 |
| `onset_pct` | 1T 모드가 개시한 요소 비율 (XT 를 올리면 줄어들 것) |

**추출기는 항상 `SDV5(=R1T) ≥ 1` 로 먼저 거른다.** `SDV17 = 0` 이
"σ11 단독"과 "미개시"를 둘 다 뜻하기 때문이다. 안 거르면 미개시 요소가
전부 σ11 주도로 잡혀 결론이 뒤집힌다.

## 판정표 (§5.23E 사전등록)

| 결과 | 결론 |
|---|---|
| 1000 °C > 23 °C | **XT 보정이 추세를 뒤집고 있었음 확정.** 최대 미해결 2건 동시 해결 |
| 평탄 (±5 %) | σ11 은 일부일 뿐. 남은 후보는 기지 소성 |
| 여전히 하강 | XT 무관. 구성모델 또는 손상 비가역 구조의 문제 |

부수 예측 두 가지:

- 워프 종 손상률의 23→1000 비가 **1.0 아래로** 내려간다 (지금 0.96)
- 23 °C 강도가 오르되 **408 MPa 회귀 외삽에 한참 못 미쳐 포화**한다.
  128.45 근처에서 멈추면 이 프로젝트 최대 성과다
