# `[74]`·`[75]` 심사 — OA 2편 (2026-08-23, a1)

> `docs/DOWNLOAD_LIST_RECENT.md` §24·§23 의 무료 2편이다. 새 세션의 네트워크
> 정책이 열리면서 비로소 직접 받을 수 있게 되었다. 등급은 둘 다 `fulltext`.
> **둘 다 카드 입력 금지** — 하나는 이론 모델이고 하나는 다른 재료다.

| # | 파일 | 서지 | 받은 곳 | 등급 |
|---|---|---|---|---|
| **74** | `[74] Li 2019 온도의존 PLS_CSiC.pdf` | **Li Longbiao**, *Temperature-dependent proportional limit stress of carbon fiber-reinforced silicon carbide ceramic-matrix composites*, **Ceramics-Silikáty 63(3) (2019) 330–337**, doi:`10.13168/cs.2019.0028` | 발행처 OA PDF (`www2.irsm.cas.cz`) | `fulltext` |
| **75** | `[75] Xu 2023 SiCSiC 편조관 열충격사이클 잔여강도_경향대조.pdf` | **Q. Xu, X. Jin, L. Liu, C. Hou, N. Hu, J. Chen, S. Zhao, T. J. Marrow, X. Fan**, *Thermal shock and residual strength testing of SiC/SiC composite braided tubes*, **Exp. Mech. 63(5) (2023) 955–964**, doi:`10.1007/s11340-023-00962-x` | **Oxford ORA 저자수용본**(`ora.ox.ac.uk`) — Springer 본문은 이 논문에 대해 `access: No` 를 반환한다 | `fulltext` (저자수용본) |

> **`[75]` 는 발행본이 아니라 저자수용본(accepted manuscript)이다.** 다운로드
> 목록이 "Springer PDF + Oxford ORA 사본" 으로 적어 두었으나 실측해 보니
> Springer 쪽은 열리지 않는다(`<meta name="access" content="No">`). 인용할 때
> 쪽번호는 발행본 기준(955–964)을 쓰되, **본문에서 인용한 문장·수치는 ORA
> 사본에서 읽은 것**이다. 표·그림 번호가 발행본과 어긋날 수 있다.

---

## 1. `[74]` Li 2019 — **우리 PLS 논리의 방법론 원전**

`postprocess/extract_pls.py` 와 `data/literature/pls_validation.py` 는 비례한도
(PLS)를 **TRS 검증 지표**로 쓴다. 그 논리의 근거가 지금까지 저장소 안에서만
서 있었는데, 이 논문이 **같은 재료계(2D C/SiC)에서 같은 주장을 이론으로 세운다.**

### 1.1 핵심 문장 — 기구까지 적혀 있다

<details><summary>원문 (클릭)</summary>

*"For C/SiC composite, the proportional limit stress of C/SiC composite **increases
with temperature**, due to the **increasing of fiber/matrix interface shear stress**
and **decreasing of the thermal residual stress**."*

</details>

**우리가 쓰는 것과 같은 기구다** — PLS 가 TRS 를 읽는 창인 이유가 바로
"온도가 오르면 TRS 가 풀리고 계면 전단이 커진다" 이고, 그것이 본 연구
제4장 §4.5(XRD TRS 대조)·제6장 PLS 비교의 전제다.

### 1.2 숫자 — 2D C/SiC 실험 + 이론

| | 973 K (700 °C) | 1273 K (1000 °C) | 상승 |
|---|---|---|---|
| $\sigma_{PLS}$ | 48 MPa | 82 MPa | **+71 %** |
| 계면 박리길이 $l_d/r_f$ | 2.7 | 6.3 | +133 % |

기준 시편: $\sigma_{PLS} \approx 80$ MPa, $\sigma_{UTS} = 271$ MPa,
파괴변형률 $\varepsilon_f = 0.33\,\%$.

민감도(같은 논문, 이론): $V_f$ 30 % → 48→103 MPa · $V_f$ 35 % → 47→113 MPa ·
$\tau_0 = 30$ MPa → 65→115 MPa. **$V_f$ 와 $\tau_0$ 둘 다 PLS 를 크게 움직인다.**

### 1.3 쓸 수 있는 것과 쓸 수 없는 것

- ✅ **방향과 기구**를 인용할 수 있다 — PLS 는 온도에 따라 **오르고**, 그 원인이
  TRS 완화다. 이것이 `pls_validation.py` 의 전제에 붙는 **외부 근거**다.
- ✅ **민감도의 순서**를 인용할 수 있다($V_f$·$\tau_0$ 가 지배).
- ❌ **절대값은 카드로 못 넣는다.** 48/82 MPa 는 **이 논문 시편**의 값이고,
  우리 재료([5], PIP)와 다르다. 게다가 이론 곡선이 섞여 있다.
- ❌ 온도점이 973/1273 K 라 우리 보정온도(23/500/1000 °C)와 **하나만 겹친다.**

---

## 2. `[75]` Xu 2023 — **사이클 대 잔여강도, 그러나 다른 재료**

### 2.1 무엇을 주는가 — 명시적 열화식

C-ring 시편의 원주방향 인장강도가 열충격 사이클 수에 **선형으로** 떨어진다:

$$\sigma_{CTS} = a + bN, \qquad a = 597.0 \pm 20.0\ \text{MPa}, \quad b = -0.224 \pm 0.026\ \text{MPa/cycle}$$

즉 **1000 사이클에 597 → 373 MPa, 잔존율 62.5 %**, 정규화 열화율
$-3.75\times10^{-4}$ /cycle (= $-0.0375\,\%$/cycle).

부수 관측:

1. **파괴 양상이 바뀐다** — 0·250 사이클은 취성, **500 사이클 초과에서 의사소성**.
   사이클이 늘수록 뚜렷해진다.
2. **산화가 표면에서 안으로 번진다** — 섬유 뽑힘이 사라진 취화 영역이 바깥에서
   자라고, **1000 사이클에서 바깥 섬유 다발이 완전히 산화**된다.
3. 기구: SiC 기지의 열인장응력 미세균열이 산화 통로를 열어 준다.

### 2.2 Table 1 — ★ 우리 쪽에 **경고**가 되는 값

| 온도 | 탄성계수 | 비례한도 |
|---|---|---|
| 25 °C | 335 ± 25 GPa | **247 ± 15 MPa** |
| 900 °C | 327 ± 21 GPa | **170 ± 12 MPa** |

**SiC/SiC 의 PLS 는 온도에 따라 내려간다(−31 %).** 그런데 `[74]` 의 C/SiC 는
같은 구간에서 **올라간다(+71 %).** 부호가 반대다.

> **이 대비가 이번 두 편에서 가장 중요한 것이다.** PLS(T) 의 방향은
> **재료계의 성질이지 CMC 일반의 성질이 아니다.** C/SiC 는 탄소섬유의 CTE 가
> 기지보다 작아 냉각 시 기지가 인장 TRS 를 받고, 가열하면 그것이 풀리며
> PLS 가 오른다. SiC/SiC 는 섬유·기지 CTE 가 가까워 그 완화 이득이 작고,
> 대신 계면 열화가 이긴다. **따라서 SiC/SiC 문헌의 PLS(T) 방향을 우리
> C/SiC 모델의 검증 표적으로 옮기면 부호가 뒤집힌 표적을 세우게 된다.**
> `[75]` 를 사이클 곡선 때문에 들여오면서 이 값을 같이 들여오지 않도록
> 검사로 못박는다.

### 2.3 쓸 수 있는 것과 쓸 수 없는 것

- ✅ **경향의 모양**을 인용할 수 있다 — 사이클에 따른 잔여강도의 **단조 감소**와
  **취성 → 의사소성 전이**. 제6장 §6.3 의 사이클 손상 지수 $k$ 가 만들어야 할
  곡선의 모양이 이것이다.
- ✅ **선형 근사가 공학적으로 통한다**는 관측 자체 (우리 $\Delta d_{cyc}$ 도
  1차 법칙이다).
- ❌ **숫자는 못 옮긴다.** SiC/SiC · **편조관**(braided tube) · C-ring 원주방향 ·
  석영램프 · 공기. 재료도 구조도 시험형상도 다르다. 다운로드 목록이 애초에
  "경향 대조 전용" 으로 적어 둔 그대로다.
- ❌ **Table 1 의 PLS(T) 방향은 특히 옮기면 안 된다** (§2.2).
- ❌ 사이클 검증 표적(§6.2.3)에 **추가하지 않는다.** 표적은 2D 평직 C/SiC 로
  좁혀져 있고 `[02]`·`[03]`·`[65]` 가 그 자리다.

---

## 3. 시험 분위기 (a2 `atmosphere_census.py` 규약)

| # | 분위기 | 근거 |
|---|---|---|
| 74 | *(해당 없음)* | 이론·모델 논문. 자기 측정이 없고 타 문헌 데이터를 인용한다 |
| 75 | **공기** | 원문 명시 — *"decreased with increasing number of thermal shock cycles **in air**"*, 산화 취화층을 결과로 보고 |

둘 다 **하중지지 출처가 아니므로** census 본표에는 올리지 않는다(경향 대조
전용). 여기 적어 두는 것은 나중에 누군가 승격을 검토할 때 분위기를 다시
찾지 않게 하기 위해서다.

---

## 4. 판정 요약

| | `[74]` Li 2019 | `[75]` Xu 2023 |
|---|---|---|
| 등급 | `fulltext` | `fulltext` (저자수용본) |
| 카드 입력 | **금지** | **금지** |
| 검증 표적 | **아니오** — 방법론 근거로만 | **아니오** — 경향 대조로만 |
| 어디에 쓰나 | 제2장 PLS 기구 서술 · `pls_validation.py` 전제의 외부 근거 | 제2장 §2.4.2 사이클 데이터셋 표의 **대조행** · 제6장 §6.3 곡선 모양 |
| 위험 | 절대값 전용 유혹 | **PLS(T) 부호 전용 위험** — 검사로 막았다 |

판정기: `python3 data/literature/refs_74_75.py --check`
