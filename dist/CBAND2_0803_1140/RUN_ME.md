# 균열대 2차 — 국소화를 강제한 덱 (0803 11:40 KST)

## 1차가 왜 무효였나

`cband_damage.py`가 손상 장을 읽어 **밴드가 아예 없었음**을 밝혔습니다.

| 봉 | 손상 열 / 전체 | 손상 폭 |
|---|---|---|
| N5 | 3 / 5 | 0.600 mm |
| N10 | **10 / 10** | **1.000 mm (봉 전체)** |
| N20 | **20 / 20** | **1.000 mm (봉 전체)** |

균열대 이론은 손상이 **한 열**에 모인다고 가정합니다. $n$열로 퍼지면 소산에너지가
약 $n$배가 되므로, **1차의 33.6 % 산포는 정규화에 대해 아무 의미가 없습니다.**

## 2차에서 바꾼 것 — 딱 두 가지

| | 1차 | **2차** | 왜 |
|---|---|---|---|
| `BAR_WEAK` (트리거 슬라이스 강도) | 0.95 | **0.80** | 5 % 약화로는 이웃 요소가 **먼저** 손상 문턱에 닿습니다. 20 %는 이 시연의 표준이며 실제 세라믹 강도 산포보다 여전히 작습니다 |
| `BAR_DISP` (인장 거리) | 4×10⁻³ | **2×10⁻² mm** | 1차에서 N20은 연화 최저점에 **도달조차 못 했습니다** |

약화 슬라이스: $X_t = X_c$ = **248 MPa** (기준 310 MPa의 80 %).

## 실행 — 창 1개, 순차 (각 수 분)

```
abaqus job=CBAND2_N5 input=CBAND2_N5.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND2_N10 input=CBAND2_N10.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```
```
abaqus job=CBAND2_N20 input=CBAND2_N20.inp user=UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive cpus=4 memory="20gb"
```

## 완료 후 — ★ 반드시 이 순서로

**국소화를 먼저 확인하고, 통과해야 에너지를 봅니다.** 1차에서 순서를 거꾸로 해서
의미 없는 숫자를 판정할 뻔했습니다.

**① 국소화 확인 (관문)**
```
abaqus python cband_damage.py CBAND2_N5.odb CBAND2_N10.odb CBAND2_N20.odb > cband2_damage.txt
```

**`rows`가 셋 다 1(또는 최소한 서로 같아야)** 합니다. 다르면 **②를 볼 필요가 없습니다.**

**② 에너지 비교 (①을 통과했을 때만)**
```
abaqus python patch_report.py CBAND2_N5.odb CBAND2_N10.odb CBAND2_N20.odb > cband2_energy.txt
```

두 txt를 보내주세요. ①이 실패하면 ②는 안 보내셔도 됩니다.
