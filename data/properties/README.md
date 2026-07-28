# 구성재 물성 데이터 (UMAT 카드 **입력**)

여기 있는 CSV는 **구성재(T300 섬유, SiC 매트릭스)** 물성만 담습니다.
어떤 논문을 어떻게 찾아 채울지는 **[`../../docs/PROPERTY_DATA_REQUEST.md`](../../docs/PROPERTY_DATA_REQUEST.md)** 참조.

```
fibre_T300_vsT.csv   ->  |
matrix_SiC_vsT.csv   ->  |  build_temperature_tables.py  ->  temperature_blocks.inp
                                    (Chamis/Schapery                 (UMAT에 붙일
                                     + CTE 기준 변환)                 카드 블록)
```

---

## ⛔ 절대 하면 안 되는 것

**복합재(2D C/SiC) 측정값을 여기 넣지 마세요.**

측정된 C/SiC의 E와 강도는 온도가 오르면 1000 °C까지 **증가**합니다. 재료가 강해져서가
아니라 **가열하면 열잔류응력이 이완되기** 때문입니다. 우리 모델은 그 TRS를 냉각 스텝으로
이미 계산하므로, 복합재 E(T)를 입력 배율로 넣으면 **같은 물리를 두 번 세게 됩니다.**

복합재 데이터는 `docs/PROPERTY_DATA_REQUEST.md` §3의 **검증 전용**입니다.

---

## 열 정의

### `fibre_T300_vsT.csv`

| 열 | 의미 | 단위 | 없으면 |
|---|---|---|---|
| `T_C` | 온도 | °C | 필수 |
| `E1`, `E2` | 섬유 축/횡 탄성계수 | MPa | 필수 |
| `G12`, `G23` | 섬유 전단탄성계수 | MPa | 필수 |
| `nu12` | 섬유 포아송비 | – | 필수 |
| `alpha1`, `alpha2` | 섬유 축/횡 CTE | 1/K | 필수 |
| `Xt`, `Xc` | 섬유 축방향 인장/압축강도 | MPa | 필수 |
| `k1`, `k2` | 섬유 축/횡 열전도율 | W/(mm·K) | 열해석에 필요 |
| `cp` | 비열 | mJ/(tonne·K) | 열해석에 필요 |
| `rho` | 밀도 | tonne/mm³ | 열해석에 필요 |

### `matrix_SiC_vsT.csv`

| 열 | 의미 | 단위 |
|---|---|---|
| `T_C` | 온도 | °C |
| `E`, `nu` | 탄성계수, 포아송비 | MPa, – |
| `alpha` | CTE | 1/K |
| `Xt`, `Xc` | 인장/압축강도 | MPa |
| `k`, `cp`, `rho` | 열전도율, 비열, 밀도 | W/(mm·K), mJ/(tonne·K), tonne/mm³ |
| `process` | `PIP` / `CVI` / `CVD` / `monolithic` | — |

### 공통 메타 열

| 열 | 값 | 의미 |
|---|---|---|
| `cte_type` | `instantaneous` \| `secant` | 원문이 CTE를 보고한 방식 |
| `cte_ref_C` | 숫자 | 할선 CTE의 기준온도 (보통 20 또는 23 °C) |
| `status` | `verified` \| `literature` \| `placeholder` | 신뢰도 |
| `source` | 자유 텍스트 | "저자 연도, Table N" 형태로 **반드시** 기록 |

`status=placeholder` 행은 `build_temperature_tables.py`가 **거부**합니다
(`--allow-placeholder`로 강제 가능하지만 결과에 쓰면 안 됩니다).

---

## 단위 규약 — mm-N-tonne-s-MPa

기존 모델 전체가 이 계를 씁니다. 논문 값을 SI에서 변환하세요.

| 물리량 | SI | → 이 계 | 변환 |
|---|---|---|---|
| 탄성계수·강도 | GPa | MPa | ×1000 |
| 열전도율 | W/(m·K) | W/(mm·K) | **÷1000** |
| 밀도 | kg/m³ | tonne/mm³ | **×1e-12** |
| 비열 | J/(kg·K) | mJ/(tonne·K) | **×1e6** |
| CTE | 1/K | 1/K | 그대로 |

예: SiC ρ = 3210 kg/m³ → `3.21e-9` · k = 60 W/(m·K) → `0.060` ·
cp = 670 J/(kg·K) → `6.7e8`

---

## CTE 기준온도 변환 (자동, 하지만 이해는 하고 계세요)

Abaqus `*Expansion, zero=T0`는 **T0 기준 할선 CTE**를 요구합니다.

```
eps_th(T) = alpha_sec(T)·(T − T0) − alpha_sec(Ti)·(Ti − T0)
```

논문은 보통 순간 CTE거나 상온 기준 할선 CTE를 줍니다. 그대로 넣으면 열변형률이,
따라서 **TRS가 틀립니다.** `build_temperature_tables.py`가 `cte_type`/`cte_ref_C`를 보고
1050 °C 기준 할선으로 변환합니다.

변환 자체는 검증되어 있습니다:

```bash
python3 abaqus/build_temperature_tables.py --selftest
#  [PASS] 상수 순간 CTE -> 상수 할선
#  [PASS] 선형 순간 CTE -> 해석해 할선
#  [PASS] 기준 변경이 모든 온도쌍의 열변형률 차를 보존
```

---

## 온도점을 몇 개 넣어야 하나

- **1개** (현재 상태): 온도 무관 모델. 열충격 결론을 낼 수 없습니다.
- **2개** (23 °C + 고온 1점): **최소 요구.** 논문이 성립합니다.
- **3개** (23 / 500 / 1000 °C): 충분. Zhang 2022의 시험 온도와 일치해 대조가 쉽습니다.
- 4개 이상: 1000 °C 이후 물성이 반전하므로(→ `PROPERTY_DATA_REQUEST.md` B1②)
  1050 °C 부근을 넘길 계획이면 추가하세요.

**섬유와 매트릭스 CSV는 같은 온도점을 가져야 합니다.** 얀은 둘의 균질화라서,
온도가 어긋나면 23 °C 매트릭스와 1000 °C 섬유가 조용히 섞입니다.
스크립트가 이를 감지해 중단시킵니다.

---

## 자기검증

`build_temperature_tables.py`는 실행할 때마다 23 °C 행의 Chamis/Schapery 결과가
**검증된 V2_0 얀 카드**와 일치하는지 확인합니다 (현재 최대 오차 0.142 %,
`verification/micromech_check.py`와 동일한 값). 이 검사가 깨지면 CSV의 상온 행이
Zhang 2022 Table 1/2에서 벗어난 것입니다.
