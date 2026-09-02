# RUN_ME — 2026-08-03 아침 실행분

**압축을 푼 폴더 안에서 그대로 실행하세요. 하위 폴더 없이 전부 평평하게 들어 있습니다.**
외부 참조 파일 없음 — `.ori` 방향 데이터는 `.inp` 안에 인라인되어 있습니다.

이 패키지는 **잡 2묶음**입니다. 서로 완전히 독립이지만, **A를 먼저 돌리세요** — 몇 분이면
끝나고, B의 전제가 되는 코드(균열대·주기경계조건)를 검사하는 관문이기 때문입니다.

| 묶음 | 잡 수 | 대략 소요 | UMAT |
|---|---|---|---|
| **A. 패치·균열대 검증** | 4 | 각 수 분 | `UMAT_CSIC_RVE_ZHANG2022_V1_0.for` |
| **B. M4 — Zhang Table 3 보정** | 3 (+1 예비) | 각 1–3 시간 | `UMAT_CSIC_THERMSHOCK_V3_0.for` |

> **물성 구성: 전부 CONFIG_V입니다** (`*Expansion, zero=1050`, Zhang Table 1 카드 그대로).
> 어제 정한 CONFIG_P(실측 CTE + 782 °C)는 **제5장 거시 해석용**이고, 여기 M4는 Zhang 논문을
> 재현하는 잡이므로 **Zhang의 물성이어야 합니다.** 이 덱들은 그 결정에 영향받지 않습니다.
> (예외: `M4_c26k_RT23_z600.inp` 하나만 `zero=600` — 보험용 대조입니다.)

---

## A. 패치·균열대 검증 — 먼저, 창 1개, 순차

작아서 병렬로 나눌 필요가 없습니다. **창 하나에 아래 4줄을 차례로** 넣으세요.

```
abaqus job=PATCH_PBC input=PATCH_PBC.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND_N5 input=CBAND_N5.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND_N10 input=CBAND_N10.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND_N20 input=CBAND_N20.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```

### A 완료 후 명령 (이걸 안 돌리면 CSV·그림이 안 나옵니다)

```
abaqus python patch_report.py PATCH_PBC.odb CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb
```
```
python3 plot_cband.py cband_curves.csv
```

> `patch_report.py`는 ODB를 읽으므로 **반드시 `abaqus python`**.
> `plot_cband.py`는 matplotlib이 필요하므로 **반드시 일반 `python3`**. 바꿔 쓰면 즉시 에러입니다.
> 후처리에는 `cpus`/`memory`를 붙이지 마세요 — 단일 스레드 수 초짜리입니다.

### A에서 봐야 할 것

1. **PATCH_PBC** — 균일 변형을 걸었을 때 응력이 요소마다 같아야 합니다.
   주기경계조건과 재료 Jacobian이 맞다는 뜻입니다. 편차가 크면 **B를 돌리지 마세요.**
2. **CBAND_N5 / N10 / N20** — 요소 크기만 다른 같은 문제입니다.
   **세 곡선의 피크 응력과 파괴에너지가 서로 붙어야** 균열대 정규화가 작동하는 것입니다.
   벌어지면 `KABAND`가 요소 크기를 제대로 못 지우고 있다는 뜻입니다.

---

## B. M4 — Zhang Table 3 보정 (본 작업)

**A가 통과한 뒤에 시작하세요. Abaqus Command 창을 3개 열고 각각 하나씩** 넣으세요.
세 잡은 서로 완전히 독립입니다.

**창 1**
```
abaqus job=M4_c26k_RT23 input=M4_c26k_RT23.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

**창 2**
```
abaqus job=M4_c26k_T500 input=M4_c26k_T500.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

**창 3**
```
abaqus job=M4_c26k_T1000 input=M4_c26k_T1000.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

세 잡 합계 30코어 / 210 GB입니다. OS용으로 2코어를 남깁니다.
스크래치가 SSD면 각 명령 끝에 `scratch=<경로>`를 붙이면 더 빠릅니다.

### 예비 잡 (선택) — 위 셋 중 **하나가 끝난 뒤에** 그 창에서

```
abaqus job=M4_c26k_RT23_z600 input=M4_c26k_RT23_z600.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

이건 `zero=600` 보험용입니다. M3에서 유일하게 완주한 케이스라 **비교 기준선**이 됩니다.
셋과 동시에 돌리지 마세요(코어가 모자랍니다).

### B 완료 후 명령 — **잡 하나가 끝날 때마다 바로** 돌리세요. 셋을 다 기다릴 필요 없습니다.

`M4_c26k_RT23`이 끝났으면:
```
abaqus python extract_ss_curve.py M4_c26k_RT23.odb
```
```
abaqus python damage_census.py M4_c26k_RT23.odb
```
```
abaqus python driver_audit.py M4_c26k_RT23.odb
```

`T500`, `T1000`도 **잡 이름만 바꿔** 똑같이:
```
abaqus python extract_ss_curve.py M4_c26k_T500.odb
abaqus python damage_census.py M4_c26k_T500.odb
abaqus python driver_audit.py M4_c26k_T500.odb
```
```
abaqus python extract_ss_curve.py M4_c26k_T1000.odb
abaqus python damage_census.py M4_c26k_T1000.odb
abaqus python driver_audit.py M4_c26k_T1000.odb
```

**셋이 모두 끝난 뒤** 비교 그림 (여기만 일반 `python3`):
```
python3 plot_compare.py M4_c26k_RT23_ss.csv M4_c26k_T500_ss.csv M4_c26k_T1000_ss.csv
```

각 스크립트가 만드는 것:

| 스크립트 | 인터프리터 | 출력 | 답하는 질문 |
|---|---|---|---|
| `extract_ss_curve.py` | `abaqus python` | `<잡이름>_ss.csv` | **피크 응력이 얼마인가** (= Zhang Table 3 대조값) |
| `damage_census.py` | `abaqus python` | 화면 표 | 냉각 후 상별 평균응력 = **TRS** |
| `driver_audit.py` | `abaqus python` | 화면 표 | 전단 드라이버를 0으로 묶은 게 **정당했는가** |
| `plot_compare.py` | `python3` | `compare.png` | 세 온도 곡선 한 장 |

---

## 판정 기준 — 무엇이 나오면 성공인가

### 1차 목표: Zhang Table 3

| 케이스 | 목표 (Zhang Table 3) | M3(3차) 결과 |
|---|---|---|
| RT23 | **128.45 MPa** | 98.2 % 지점에서 정지 |
| T500 | **179.42 MPa** | 67.3 % 지점에서 정지 |
| T1000 | **199.15 MPa** | 57.2 % 지점에서 정지 |

**M4가 M3와 다른 점은 딱 두 가지**입니다 (메시·물성 블록은 바이트 단위로 동일):
1. 하중 없는 전단 드라이버 3개를 0으로 **고정** (`ConstraintsDriver3/4/5`)
2. 힘 수렴 허용오차 `0.005 → 0.02`

M3에서는 잔차의 63–84 %가 **하중이 걸리지 않은 거시 드라이버**에 있었고,
절대 응력으로 환산하면 7.3e-4 ~ 1.5e-2 MPa였습니다 — 축응력 100–200 MPa에 대해
Abaqus가 1.4e-4 MPa를 요구하고 있었습니다. **다섯 자릿수 과한 요구**입니다.

### 2차: driver_audit이 반드시 확인해줘야 하는 것

전단 드라이버를 0으로 묶은 것이 **물리적으로 공짜인지** 확인합니다.
**전단응력이 $\sigma_{xx}$의 1 % 미만**이면 정당한 구속입니다.
**1 %를 넘으면 이것은 실제 모델링 변경**이며, 논문에 한계로 명시해야 합니다.
→ 이 숫자를 꼭 알려주세요. 제4장 §4.9-1a가 이 값을 기다리고 있습니다.

### 3차: 공짜로 얻는 것

`damage_census.py`는 **중간에 죽은 ODB에서도 냉각 스텝을 읽습니다.**
잡이 인장 중에 멈춰도 **TRS는 온전히 나옵니다.** 실패해도 버리지 마세요.

---

## 잘 안 될 때

- **인장 스텝에서 또 멈추면** — `.msg`에서 잔차가 어느 절점에 있는지 보세요.
  `5681`–`5686`은 **메시 절점이 아니라 더미 드라이버**입니다. 그 "자유도 1"은
  전역 x가 아니라 그 드라이버의 유일한 자유도입니다. (3차에서 제가 이걸 착각했습니다.)
- **변위 증분이 1e-9까지 줄었는데도 안 붙으면** 증분 크기 문제가 아닙니다.
  컷백을 더 허용해도 소용없습니다. **최소 증분을 1e-8 아래로 내리지 마세요** —
  죽는 데만 20분 넘게 씁니다.
- 자세한 전말은 같이 넣은 `M1_FAILURE_ANALYSIS.md` Round 4에 있습니다.

---

## 실행 순서 요약

```
A (창 1개, 4잡 순차, 수 분)
   └─> patch_report.py  →  plot_cband.py       ← 통과해야 B로
B (창 3개, 병렬, 각 1–3시간)
   └─> 잡마다 extract_ss_curve / damage_census / driver_audit
       └─> 셋 다 끝나면 plot_compare.py
   └─> (선택) z600 을 빈 창에서
```
