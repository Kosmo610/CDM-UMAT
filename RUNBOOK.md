# RUNBOOK — 내일 연구실에서 바로 실행

이 문서는 **내일 Abaqus 커맨드로 바로 돌릴 수 있게** 정리한 실행 순서 + 에러 진단표다.
현재 상태: **UMAT(V3_1_FAST)은 검증 완료(컴파일 OK, 물성 재현 OK, 접선 정확도 0%)**.
따라서 3D 해석 에러는 UMAT 구성식 버그가 아니라 **런타임(.ori / 수렴 / PBC)** 쪽일 가능성이 크다.

---

## 0. 파일 배치 (작업 폴더에 반드시 함께)

| 파일 | 역할 |
|---|---|
| `CSIC_ZHANG2022_0023C.inp` (또는 0500C/1000C) | 해석 덱 |
| `UMAT_CSIC_ZHANG2022_V3_1_FAST.for` | 사용자 재료 서브루틴 |
| **`CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori`** | 야른 방향 벡터 (`*Distribution`이 이 **정확한 파일명**으로 읽음) |

`.ori`는 반드시 `.inp`와 **같은 폴더**, **철자 그대로**. 이름이 다르면 바로 에러난다.

---

## 1. 먼저 datacheck (5초, 덱/인터페이스 오류를 빨리 잡는다)

```bash
abaqus job=CSIC_ZHANG2022_0023C \
       user=UMAT_CSIC_ZHANG2022_V3_1_FAST.for \
       double=both datacheck interactive
```

- 통과하면 → 덱·UMAT 인터페이스·`.ori` 경로는 정상. 2번으로.
- 실패하면 → `CSIC_ZHANG2022_0023C.dat` 끝부분을 본다(아래 진단표 참조).

## 2. 기준선 재현 (Pillar B — 이것부터)

```bash
# 23 C
abaqus job=CSIC_ZHANG2022_0023C \
       user=UMAT_CSIC_ZHANG2022_V3_1_FAST.for \
       double=both interactive cpus=4

# 500 C, 1000 C (동일 UMAT)
abaqus job=CSIC_ZHANG2022_0500C user=UMAT_CSIC_ZHANG2022_V3_1_FAST.for double=both interactive cpus=4
abaqus job=CSIC_ZHANG2022_1000C user=UMAT_CSIC_ZHANG2022_V3_1_FAST.for double=both interactive cpus=4
```

- `double=both` (Standard는 배정밀도 권장). `cpus`는 라이선스에 맞게.
- 완료 후 인장 강도를 Zhang2022 Table 3(**128.45 / 179.42 / 199.15 MPa**, 오차 10~15%)와 대조.

## 3. 에러 진단 체크리스트 (지금 막힌 부분)

`.msg`와 `.dat` 파일을 먼저 확인. 아래는 이 덱에서 실제로 잘 나는 순서.

| 증상 (`.msg`/`.dat` 키워드) | 원인 | 조치 |
|---|---|---|
| `*** ERROR ... cannot be opened` / distribution input | `.ori` 파일명·경로 불일치 | 파일을 작업폴더에 `CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori` 이름 그대로 배치 |
| `distribution ... number of ... does not match` | `.ori` 벡터 수 ≠ 요소 수 (메시 재생성했는데 옛 .ori) | 현재 메시로 TexGen에서 `.ori` 재추출 |
| `too many attempts` / `too many increments` (COOL 스텝) | 냉각 중 손상·소성 연화로 수렴 실패 | (a) 초기 증분 축소 `0.0005, 1.0, 1e-12, 0.001` (b) **1차로 `ENABLE=0`(PROPS 29/13)으로 탄성 TRS만 먼저 성공** → 이후 ENABLE=1 재시작 |
| `negative eigenvalue` / `system ... not positive definite` | 강한 연화 + 대칭 solver | `ETA`(점성정규화)를 1e-6→1e-4로 키워 안정화 (PROPS: 야른 26, 매트릭스 10) |
| `numerical singularity` at ConstraintsDriver dof | 미사용 매크로변형 dof 미구속 | 열스텝에서 사용 안 하는 CD dof를 `*Boundary`로 0 고정(인장스텝처럼) |
| `UMAT ... ` 관련 컴파일/링크 실패 | ifort가 Abaqus에 안 잡힘 | `abaqus verify -user_std` 로 컴파일러 확인 |
| `PROPS/DEPVAR mismatch` | (해당 없음 — 이미 15/31, 14/12 일치 검증됨) | — |

> 위 조치로도 안 되면 **`.msg` 끝 40줄 + `.dat` 에러 블록**을 그대로 보내줘. 원인 특정해줄게.

## 4. UMAT 자체 재검증 (라이선스 불필요, gfortran만)

Abaqus로 돌리기 전에 UMAT이 멀쩡한지 30초 확인:

```bash
bash verification/matpoint/run_matpoint_check.sh
```

기대 출력: 매트릭스 peak ≈ 309 MPa (Xt=310), 야른 peak ≈ 3966 MPa (Xt=3969),
접선 오차 3케이스 모두 `0.00000 %`. (수정하다 깨지면 여기서 바로 걸린다.)

## 5. 반복 열사이클 — 노벨티 결과 (Path A, 지금 UMAT 그대로)

기준선이 돌면, **새 구성식 없이** 반복 열사이클 덱을 만들어 강성/강도 열화 곡선을 뽑는다:

```bash
# 냉각(TRS) -> [가열 23->1000 -> 냉각 1000->23] xN -> 인장(잔류물성)
python abaqus/make_cyclic_deck.py --base abaqus/CSIC_ZHANG2022_0023C.inp \
       --tmax 1000 --ncyc 5 --out CSIC_CYCLE_1000C_N5.inp

abaqus job=CSIC_CYCLE_1000C_N5 \
       user=src/UMAT_CSIC_ZHANG2022_V3_1_FAST.for \
       double=both interactive cpus=4
```

- `--ncyc` 를 1, 2, 5, 10 … 으로 바꿔 여러 잡을 돌리면 **강성/강도 vs 사이클수** 곡선이 나온다.
- 사이클 누적은 RVE 응력재분배(A03 메커니즘)로 발생 → 단조 UMAT로도 열화가 나온다.
- **주의(메시 객관성)**: V3_1은 고정 소성계수 A라 결과가 메시에 민감할 수 있음 → RVE 메시를 고정하고 논문에 명시.

## 6. 후처리

```bash
abaqus python postprocess/extract_ss_curve.py   # ODB -> 응력-변형 CSV
python postprocess/plot_compare.py              # Table3 대조 플롯
```

---

### 현재 파일 상태 요약
- **최신·검증됨**: `src/UMAT_CSIC_ZHANG2022_V3_1_FAST.for`, `abaqus/CSIC_ZHANG2022_{0023,0500,1000}C.inp`
- **레거시(구 인터페이스)**: `src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for`, `abaqus/ZHANG2022_*_{V1_0,V2_0}.inp` — 지금 흐름에선 쓰지 않음. 내일 실행 시 **최신 파일만** 사용할 것(옛 덱을 실수로 돌리지 말 것).
