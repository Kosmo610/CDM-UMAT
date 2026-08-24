# A단계 2차 — 0803 10:06 KST

**B(M5) 돌아가는 중에 하세요. 전부 수 초 ~ 수 분입니다.**

---

## ① 재실행 없이 — 6×6 다시 읽기 + 손상 분포 진단

`patch_report.py`와 `cband_damage.py`를 **기존 `.odb`가 있는 폴더**에 넣고:

```
abaqus python patch_report.py PATCH_PBC.odb CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb > patch_report2.txt
```
```
abaqus python cband_damage.py CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb > cband_damage.txt
```

두 txt를 보내주세요.

### 무엇이 고쳐졌나 (patch_report.py)

6×6이 전부 `nan`이었던 진짜 원인을 찾았습니다. **이 덱에는 `*Assembly`가 없습니다**(평면 덱).
그래서 `*NSet`이 자동 생성 인스턴스에 붙는데, 제 리더는 **어셈블리 레벨만** 뒤졌습니다.
이제 인스턴스 레벨도 찾습니다(`driver_audit.py`는 원래 그렇게 하고 있었습니다 —
그래서 **B의 후처리는 안전**합니다).

**그래도 못 찾으면**, 이제 ODB 안에 실제로 뭐가 있는지(영역 키, 절점 집합 이름)를
**같이 찍습니다.** 세 번째로 추측하지 않기 위해서입니다.

### `cband_damage.py`가 답하는 것

균열대 덱은 이미 `SDV`를 필드 출력에 넣고 있어 **손상 분포를 재실행 없이 읽을 수
있습니다.** 각 막대에 대해:

- **손상된 요소 열(row)이 몇 줄인가** — 균열대 이론은 **1줄**을 가정합니다.
  n줄로 퍼졌으면 소산에너지가 약 n배가 되고, 그러면 33.6 % 산포는
  **정규화에 대한 진술이 전혀 아닙니다.**
- **`d_max`가 카드의 상한 0.90에 닿았는가** — 닿았으면 그 막대는 이미 포화되어
  잔여강성 10 %로 **재경화 중**입니다. 그 지점 이후는 연화곡선이 아닙니다.

---

## ② 재실행 — 인장 거리를 5배로 늘린 균열대 (각 수 분)

**이유.** 0803 결과를 연화 구간만 따로 적분해 보니, 세 막대가 **완전히 다른 단계**에서
끝났습니다:

| 막대 | 연화 최저점 도달 | 종료 시 하중/피크 |
|---|---|---|
| N5 | δ=2.24e-3에서 도달, 이후 **재경화** | 35 % |
| N10 | δ=3.34e-3에서 도달 | 42 % |
| **N20** | **끝까지 도달 못 함 — 계속 연화 중** | **57 %** |

같은 끝점에서 면적을 비교한 것은 **서로 다른 상태를 비교한 것**입니다.
그래서 `BAR_DISP`를 **4.0e-3 → 2.0e-2 (5배)** 로 늘렸습니다. **이것 하나만** 바꿨습니다.

**창 1개에 순차로** (작아서 병렬 불필요):

```
abaqus job=CBAND_N5L input=CBAND_N5L.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND_N10L input=CBAND_N10L.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND_N20L input=CBAND_N20L.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```

### 완료 후

```
abaqus python patch_report.py CBAND_N5L.odb CBAND_N10L.odb CBAND_N20L.odb > cband_long.txt
```
```
abaqus python cband_damage.py CBAND_N5L.odb CBAND_N10L.odb CBAND_N20L.odb > cband_damage_long.txt
```

그림은 선택 (윈도우는 `python3`가 아니라 **`python`**):
```
python plot_cband.py cband_curves.csv
```

---

## 정정 — 어제 제가 성급했습니다

어제 저는 CSV만 보고 "**정규화가 작동합니다**(4배가 0.81배로)"라고 말씀드렸습니다.
**연화 구간만 따로 적분해 보니 산포가 33.6 %가 아니라 109 %였습니다.** N20이 아직
연화 중인데 N5는 이미 포화·재경화한 상태였기 때문입니다.

**현재 상태는 "통과"도 "실패"도 아니라 "판정 불가"입니다.** ①과 ②가 그것을 가릅니다.

한편 **인공 감쇠는 확실히 깨끗합니다** — `ALLSD/ALLIE` = 0.0003–0.0005 (0.03–0.05 %).
피크 응력이 감쇠로 부풀려지지 않았다는 뜻이고, 이 부분은 확정입니다.
