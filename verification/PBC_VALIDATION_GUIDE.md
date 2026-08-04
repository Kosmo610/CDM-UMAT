# 주기경계조건(PBC) 검증 워크플로우

목적: ZHANG2022 RVE에 걸린 **주기경계조건이 실제로 제대로 작동하는지**를,
논문 수치와 비교하기 *전에* 확정하는 것. 손상·소성이 섞여 있으면 "결과가 이상한데
PBC 탓인지 재료모델 탓인지" 구분이 안 되므로, **탄성 상태에서 답을 이미 아는 문제**로
먼저 잡고 간다.

검증은 4단계다. 앞 단계가 통과해야 뒷 단계 숫자가 의미를 가진다.

| 단계 | 무엇을 | 도구 | Abaqus 필요? | 소요 |
|---|---|---|---|---|
| 0 | 구속식 자체가 기하학적으로 맞는가 | `verification/check_pbc.py` | ❌ | ~1 초 |
| 1 | 패치 테스트 (균질 재료 → 정답을 앎) | `abaqus/make_pbc_check.py` → `PBC_PATCH` | ✅ | 수 분 |
| 2 | 2상 RVE 균질화 (C 행렬 + CTE) | 같은 스크립트 → `PBC_ELASTIC` | ✅ | 수 분 |
| 3 | EasyPBC 교차검증 (독립 구현) | `abaqus/make_easypbc_model.py` | ✅ | 수 분 |

---

## 0단계 — 정적 감사 (Abaqus 없이 1초)

```bash
python3 verification/check_pbc.py abaqus/ZHANG2022_RT23_V1_0.inp
```

`.inp` 텍스트만 읽고 다음 7가지를 확인한다. Abaqus를 돌려야만 알 수 있던 실패들을
1초 만에 먼저 걸러낸다.

1. **메쉬/격자** — 바운딩박스에서 Lx, Ly, Lz를 뽑고, ConstraintsDriver 노드가
   요소에 물려 있지 않은지(순수 DOF 운반체인지) 확인.
2. **세트 페어링** — `*Equation`은 노드 세트를 **나열된 순서대로** 짝지운다.
   따라서 FaceA[k]와 FaceB[k]가 정확히 격자벡터 하나만큼 떨어져 있어야 한다.
   TexGen이 `Unsorted`를 붙이는 이유가 이것이고, 누가 세트를 정렬해버리면 여기서 걸린다.
3. **방정식 계수** — 실측 오프셋 d로부터 계수를 **다시 유도해서** 파일 값과 대조한다.

   ```
   u_slave - u_master = H · d ,
   H = [[e_x , e_xy, e_xz],
        [0   , e_y , e_yz],      (CD0..CD5 = e_x, e_y, e_z, e_xy, e_xz, e_yz)
        [0   , 0   , e_z ]]
   ```
   메쉬를 다시 뽑았는데 계수에 옛날 Lx가 남아 있는 경우, 전단항이 빠진 경우,
   부호가 뒤집힌 경우가 전부 여기서 잡힌다.
4. **DOF 소거/과구속** — Abaqus는 각 `*Equation`의 **첫 항**을 소거한다. 그 DOF가
   두 방정식의 첫 항이거나 `*Boundary`까지 걸려 있으면 overconstraint로 죽는다.
5. **표면 커버리지** — RVE 표면의 모든 절점이 Face/Edge/MasterNode 세트에 **정확히
   한 번** 속하는지, 내부 절점이 끌려들어오지 않았는지. 마주보는 두 면의 절점 수가
   다르면 메쉬 자체가 주기적이지 않은 것이므로 TexGen에서 다시 뽑아야 한다.
6. **강체모드 억제** — 코너 하나가 1/2/3 방향으로 고정되어 있는지. 없으면 강성행렬이
   특이해진다.
7. **부피분율** — tet 부피를 실제로 적분해서 메쉬가 박스를 채우는지, 각 상의 분율이
   논문과 맞는지.

### 현재 저장소 상태 (6개 덱 전부)

```
RESULT: PBC DEFINITION IS CONSISTENT  (0 warning(s))
```

- 격자 3.5 × 3.5 × 0.44 mm, **V_RVE = 5.390000 mm³**
- 57개 방정식 전부 기하학적으로 정합, 6개 거시변형률 성분 모두 구동 가능
- 표면 절점 9,062개(면 8,630 / 모서리 424 / 꼭짓점 8)가 빠짐없이 한 번씩 구속됨
- 마주보는 면의 절점 수 일치: x 394=394, y 406=406, z 3951=3951 → **메쉬가 주기적**
- 메쉬가 박스를 **정확히 100.0000 %** 채움 → RF/V_box로 거시응력을 뽑아도 됨
- 얀 50.51 % / 매트릭스 49.49 % →
  **전체 섬유 Vf = 0.5051 × 0.792 = 0.4000** — 논문의 Vf ≈ 40 %와 정확히 일치
  (얀 내부 Vf = 0.792는 `micromech_check.py`가 Chamis/Schapery로 독립 확인한 값)

### 감사 도구 자체의 검증

통과만 하는 검사기는 쓸모가 없으므로, 정상 덱에 실제로 자주 나는 결함 11가지를
주입해서 전부 잡히는지 확인한다.

```bash
python3 verification/test_check_pbc.py
# -> ALL 11 FAULTS DETECTED -- the audit has teeth.
```

주입하는 결함: 옛날 격자길이, 면 세트 길이 불일치, 세트 순서 뒤바뀜, 전단항 삭제,
부호 반전, DOF 이중소거, 소거 DOF에 `*Boundary`, 코너 고정 삭제, 표면 절점 누락,
드라이버 노드 번호 충돌, 비주기 메쉬.

---

## 1단계 — 패치 테스트 (여기가 진짜 검증)

### 왜 패치 테스트인가

RVE 전체에 **똑같은 등방 재료 하나**만 넣고 거시변형률을 걸면 정답이 닫힌 형태로 알려져 있다.

- 변형률장이 **어디서나 균일**하고 거시변형률과 같다
- 주기 요동 `u − H·x`가 **항등적으로 0**
- 균질화 강성이 그 재료의 강성 **그 자체**

C3D4 사면체는 상수변형률을 **정확히** 표현하므로, PBC가 맞다면 이 결과가 **기계정밀도**로
재현된다. 즉 판정 기준이 "공학적으로 그럴듯한가"가 아니라 "1e-12인가"다.
구속에 결함이 있으면 응력장이 즉시 불균일해진다. 보정도 판단도 개입할 여지가 없다.

### 실행

```bash
python3 abaqus/make_pbc_check.py abaqus/ZHANG2022_RT23_V1_0.inp
#  -> PBC_PATCH.inp        균질 등방, .ori 파일 불필요
#  -> PBC_ELASTIC.inp      2상 RVE (손상 off), .ori 필요
#  -> PBC_PATCH_CAE.inp    EasyPBC 입력용 (구속·스텝 없음)
#  -> PBC_ELASTIC_CAE.inp  같음

abaqus job=PBC_PATCH input=PBC_PATCH.inp double interactive
abaqus python postprocess/extract_stiffness.py PBC_PATCH.odb --patch
```

> `PBC_PATCH`는 **UMAT도 `.ori` 파일도 필요 없다**. 컴파일러 없이 바로 돌아가므로
> 새 메쉬를 받았을 때 가장 먼저 던져볼 수 있는 검사다.

7개 스텝이 들어간다. LC1~LC6은 여섯 개 드라이버 DOF를 **전부** 지정하되 하나만
`--eps`(기본 1e-3), 나머지는 0으로 묶는다. 나머지를 풀어두면 Abaqus가 거시응력 0이
되도록 이완시켜버려서 **강성행렬이 아니라 컴플라이언스행렬의 열**이 나온다 — 다른 실험이다.
LC7은 여섯 개를 전부 0으로 묶고 온도만 +1 K 올려 CTE를 뽑는다.

### 통과 기준

| 항목 | 기준 | 의미 |
|---|---|---|
| 응력장 균일성 | peak-to-peak / \|σ\| < 1e-6 | 모든 요소가 같은 응력 |
| 주기 요동 `u − H·x` | 퍼짐 / (H·L) < 1e-6 | 요동이 상수(=강체이동) |
| C = C_isotropic | 상대오차 < 1e-6 | 입력한 E, ν를 그대로 돌려줌 |
| 균질화 CTE | 상대오차 < 1e-4 | 입력한 α를 그대로 돌려줌 |
| 부피 적분 | ΣIVOL / V_box = 1 ± 1e-3 | 평균화 부피가 셀 부피 |

여기서 하나라도 깨지면 **2단계 이후 숫자는 볼 필요가 없다.**

---

## 2단계 — 2상 RVE 균질화

```bash
abaqus job=PBC_ELASTIC input=PBC_ELASTIC.inp double interactive   # .ori 같은 폴더에
abaqus python postprocess/extract_stiffness.py PBC_ELASTIC.odb
```

손상·소성을 뺀 선형 탄성이므로 각 스텝이 1 증분에 수렴한다. 나오는 것:

- 6×6 균질화 강성 **C**
- 공학상수 E1, E2, E3, G12, G13, G23, ν12, ν13, ν23 (= EasyPBC가 주는 것과 같은 항목)
- 균질화 CTE α_x, α_y, α_z

### 여기서도 세 가지가 독립적으로 검증된다

1. **평균화** — 요소 변형률장의 부피평균이 드라이버에 건 거시변형률을 재현하는가.
   구속이 새면 셀이 지시한 것보다 덜 변형되고 이 비가 1에서 벗어난다.
2. **Hill–Mandel** — 드라이버 반력에서 얻은 거시응력(σ = RF/V)과 적분점 응력의
   부피평균이 일치하는가. 하나는 구속식을 통과한 경로, 하나는 적분점을 통과한 경로다.
   구속이 일에너지 정합적일 때만 두 값이 만난다.
3. **대칭성** — C가 대칭으로 나오는가. 추출 과정에서 대칭을 강제하는 부분이 전혀 없으므로
   C_ij vs C_ji는 전체 사슬에 대한 공짜 검사다.

> **부호 규약**: 드라이버 반력에서 거시응력을 만들 때의 부호는 Abaqus가 소거 DOF를
> 어떻게 조립하느냐에 달려 있다. 스크립트는 이를 가정하지 않고 **부피평균과 비교해서
> 실행 결과로부터 판정**하고, 어느 규약이었는지 출력한다.

### 예상되는 결과 (참고)

평직 C/SiC RVE이므로 대략 E1 ≈ E2 ≫ E3, G13 ≈ G23, C의 정규-전단 결합항(1..3행 ×
4..6열)은 0에 가깝게 나와야 한다. 결합항이 크게 남으면 얀 배향(`.ori`)이 잘못 붙었거나
셀이 직교이방성이 아니라는 뜻이다.

C3D4 선형 사면체는 알려진 대로 **과도하게 뻣뻣하다**. 절대값을 논문과 맞출 때는
이 편향을 감안하거나 C3D10으로 다시 뽑아 비교해야 한다. 다만 EasyPBC 비교는 **같은
메쉬**에서 하므로 이 편향이 양쪽에 똑같이 들어가 상쇄된다.

---

## 3단계 — EasyPBC 교차검증

EasyPBC(Omairey, Dunning & Sriramula, *SoftwareX* **9** (2019) 100027)는 자기만의
구속식과 하중케이스를 만든다. 즉 **우리 코드와 한 줄도 공유하지 않는 독립 구현**이다.
같은 메쉬·같은 구성재로 같은 답이 나오면, 우리 TexGen/Xia 구속이 외부 도구로부터
확증된 것이다.

```bash
abaqus cae noGUI=abaqus/make_easypbc_model.py -- PBC_PATCH_CAE.inp
# -> PBC_PATCH_CAE.cae + 플러그인에 넣을 Part/Instance 이름 출력
```

`*_CAE.inp`는 **우리 구속을 떼어낸** 덱이다(`*Equation`, 드라이버 노드, 코너 고정 제거).
EasyPBC가 자기 구속을 새로 만들기 때문에, 우리 것을 남겨두면 모든 경계절점이
이중구속되어 잡이 죽는다.

### 반드시 PATCH부터

균질 등방 셀이면 어느 도구로 계산하든 입력한 E, ν가 그대로 나와야 한다. 그러니
`PBC_PATCH_CAE`로 먼저 돌려서 **이 메쉬에서 EasyPBC가 제대로 세팅됐는지**를
확정한 다음에야, 2상 결과 비교가 의미를 갖는다.

```bash
python3 postprocess/compare_pbc_easypbc.py PBC_PATCH_constants.csv \
        <EasyPBC 리포트> --isotropic 350000 0.2
```

그 다음 2상:

```bash
abaqus cae noGUI=abaqus/make_easypbc_model.py -- PBC_ELASTIC_CAE.inp
python3 postprocess/compare_pbc_easypbc.py PBC_ELASTIC_constants.csv <EasyPBC 리포트>
```

리포트 형식은 버전마다 다르므로 스크립트가 `E11 = 12345` 류의 쌍을 유연하게 긁는다.
못 읽으면 `--set E1=... G12=...`로 직접 넣으면 된다.

### 불일치가 났을 때의 해석

- **전단만 어긋남** → 전단 하중케이스 정의 차이(공학전단 γ vs 텐서전단 γ/2, 한쪽면
  구동 vs 대칭 구동). 깔끔한 2배/0.5배면 규약 차이지 구속 오류가 아니다.
- **탄성계수만 어긋남** → 평균화 부피, 또는 2상 덱에서 **얀 배향이 CAE 임포트를 통과하지
  못한 경우**를 의심. TexGen 배향은 `*Distribution` 이산장으로 들어가는데 이게
  안 넘어오면 얀이 전역좌표계 기준 횡등방성이 되어 다른 재료가 된다.
  `make_easypbc_model.py`가 임포트 직후 이걸 확인해서 경고한다.
- **전부 어긋남** → PATCH 비교부터 다시. 거기서 안 맞으면 어느 한쪽 세팅이 틀린 것이고,
  2상 숫자는 아무 의미가 없다.

### 알려진 제약

- EasyPBC 커널 함수의 시그니처는 공개 API가 아니다. `--run`을 주면 스크립트가
  플러그인을 찾아 시그니처를 **introspect** 해서 이름으로 인자를 맞춰 호출을 시도하고,
  못 맞추면 추측하지 않고 GUI 절차를 출력한다. GUI로 돌리는 게 정상 경로다.
- 메쉬 민감도(mesh sensitivity) 옵션은 끄고 쓴다. 여기서는 **같은 메쉬에서 두 구속
  생성기를 비교하는 것**이 목적이므로 메쉬를 바꾸면 비교가 흐려진다.

---

## 새 메쉬를 받았을 때 (요약 절차)

```bash
# 0. 1초 감사 — 여기서 걸리면 Abaqus 돌릴 필요 없음
python3 verification/check_pbc.py new_mesh.inp || exit 1

# 1. 패치 테스트 (.ori 없이도 돌아감)
python3 abaqus/make_pbc_check.py new_mesh.inp --prefix NEW --only patch
abaqus job=NEW_PATCH input=NEW_PATCH.inp double interactive
abaqus python postprocess/extract_stiffness.py NEW_PATCH.odb --patch

# 2. 통과했으면 2상 균질화
python3 abaqus/make_pbc_check.py new_mesh.inp --prefix NEW --only elastic
abaqus job=NEW_ELASTIC input=NEW_ELASTIC.inp double interactive
abaqus python postprocess/extract_stiffness.py NEW_ELASTIC.odb

# 3. 그 다음에야 손상 해석 (assemble_inp.py)
```

`check_pbc.py`는 실패 시 exit 1이므로 위처럼 게이트로 쓸 수 있다.

---

## 자주 나는 실패와 원인

| 증상 | 원인 |
|---|---|
| Abaqus: overconstraint / zero pivot | 소거 DOF 중복 또는 소거 DOF에 `*Boundary` → 0단계 4번이 잡음 |
| Abaqus: numerical singularity on 3 DOF | 코너 고정 누락 → 0단계 6번 |
| 패치 테스트 응력장이 불균일 | 면 세트 페어링/순서 문제 → 0단계 2번 |
| C가 비대칭 | 방정식 계수 비정합 → 0단계 3번 |
| σ = RF/V 와 부피평균이 안 맞음 | 평균화 부피 오류(메쉬가 박스를 안 채움) → 0단계 7번 |
| 마주보는 면 절점 수 다름 | 메쉬 자체가 비주기 → TexGen에서 periodic meshing 켜고 재생성 |
| 얀이 이상하게 무름/뻣뻣 | `.ori` 파일 누락 또는 미임포트 |

## 파일 목록

```
verification/check_pbc.py            .inp 정적 감사 (7개 검사, exit code로 게이트 가능)
verification/test_check_pbc.py       결함 11종 주입 → 감사 도구 자체 검증
abaqus/make_pbc_check.py             PATCH / ELASTIC / *_CAE 덱 생성기
abaqus/make_easypbc_model.py         *_CAE.inp → CAE 모델, EasyPBC 구동/안내
postprocess/extract_stiffness.py     ODB → C, 공학상수, CTE + 3(또는 5)가지 정합성 검사
                                     (--selftest 로 Abaqus 없이 대수 검증 가능)
postprocess/compare_pbc_easypbc.py   우리 결과 vs EasyPBC 비교표 + 불일치 진단
```
