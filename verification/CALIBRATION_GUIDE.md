# Calibration Guide — matching Zhang 2022 Table 3 with the V2_0 full model

**목표 (goal):** V2_0 풀‑모델을 Abaqus로 돌리고, 논문이 공개하지 않은 파라미터를
시행착오로 맞춰 **Table 3의 시뮬레이션 강도**(23 °C = 128.45, 500 °C = 179.42,
1000 °C = 199.15 MPa)와 온도별 응력‑변형 곡선을 재현합니다.

모델 자체(수식·탄성물성·CTE·해석절차)는 이미 검증됨(→ `VERIFICATION_REPORT.md`).
여기서 맞추는 것은 **논문에 값이 없는 손상/소성 파라미터**뿐입니다.

---

## 0. 워크플로우 (한 번의 반복)

```bash
# (1) 세 온도 해석 실행 (V2_0 = 풀 모델)
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V2_0.inp  \
       user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
abaqus job=Job-T500  input=abaqus/ZHANG2022_T500_V2_0.inp  user=src/...for double interactive
abaqus job=Job-T1000 input=abaqus/ZHANG2022_T1000_V2_0.inp user=src/...for double interactive

# (2) 각 온도의 거시 응력-변형 곡선 추출
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb    # -> Job-RT23_ss.csv
abaqus python postprocess/extract_ss_curve.py Job-T500.odb
abaqus python postprocess/extract_ss_curve.py Job-T1000.odb

# (3) 논문 Table 3와 겹쳐 비교
python3 postprocess/plot_compare.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv
#   -> ss_curves_by_temperature.png  +  강도 비교표

# (4) 아래 표를 보고 카드 값을 수정 -> (1)로 반복
```

UMAT 코드는 수정할 필요가 없습니다(풀 모델이 이미 구현되어 스위치로 제어됨).
보정은 `abaqus/ZHANG2022_*_V2_0.inp`의 `*User Material` 카드 숫자만 바꿉니다.
세 파일의 카드는 동일하게 유지하세요(온도 독립 가정 — 논문 §3.2.3).

---

## 1. V2_0 시작값과 출처 (calibration knobs)

### Yarn card (`CSIC_YARN_DAMAGE`, 38 constants)

| Slot | 이름 | V2_0 시작값 | 출처 | 성격 |
|---|---|---|---|---|
| 2–10 | E1..G23 | Chamis 값 | **검증됨** (Table 1+2) | 고정 |
| 11 | Xt (MPa) | **2835** | Vf·3580 (T300 rule of mix.) | 미세조정 |
| 12 | Xc (MPa) | **1956** | Vf·2470 | 미세조정 |
| 13 | Yt (MPa) | 80 | 보정 시작값 | **주요 knob** |
| 14 | Yc (MPa) | 350 | 보정 시작값 | **주요 knob** |
| 15–17 | S12,S13,S23 | 120,120,100 | 보정 시작값 | **주요 knob** |
| 18–21 | A1t,A1c,Att,Atc | 2.0 | 고정 A (G=0일 때) | 보조 |
| 32–33 | G1t,G1c (N/mm) | **12.5** | Ge Table 3 | 미세조정 |
| 34–35 | Gtt,Gtc (N/mm) | 0 (→ 고정 A=2) | — | 옵션 |
| 36 | X_PO (MPa) | **700** | ~0.25·Xt (pull-out) | **Eq.18 knob** |
| 37 | rF | **3.0** | linear→exp 전이 | **Eq.18 knob** |
| 38 | K1 (MPa) | **8000** | linear softening slope | **Eq.18 knob** |
| 22–23 | dmax1,dmaxt | 0.99 | 상한 | 고정 |
| 24 | eta | 0.02 | 점성 정규화 | 안정성 |

### Matrix card (`SIC_MATRIX_DAMAGE`, 22 constants)

| Slot | 이름 | V2_0 시작값 | 출처 | 성격 |
|---|---|---|---|---|
| 2–3 | E, nu | 350000, 0.20 | **검증됨** (Table 2) | 고정 |
| 4–5 | Xt, Xc (MPa) | 310, 310 | **Table 2** | 고정 |
| 15–16 | Gm_t,Gm_c (N/mm) | 0.031 | brittle SiC 시작값 | 미세조정 |
| 17 | SY0 (MPa) | **250** | 보정 시작값 (소성 ON) | **주요 knob** |
| 18 | HISO (MPa) | **100000** | 보정 시작값 | **주요 knob** |
| 10 | eta | 0.02 | 점성 정규화 | 안정성 |

> **굵은 값 = 논문에 없어 보정 대상.** `Vf=0.792`는 검증된 얀 섬유체적비.
> `SY0<=0`이면 소성 OFF, `X_PO<=0`이면 Eq.18 OFF (스위치로 단계별 검증 가능).

---

## 2. 어떤 knob이 무엇을 바꾸는가

| 관측량 (paper 그림) | 지배 파라미터 | 방향 |
|---|---|---|
| 초기 기울기(겉보기 탄성계수) | 냉각 후 손상상태 → **Yt, S23** (횡방향 얀 예비손상) | Yt↓ → 예비손상↑ → 기울기↓ |
| 비선형 개시 시점 | **Yt, S12/S13** (횡·전단 얀 손상) | 강도↓ → 조기 비선형 |
| 23 °C 극한강도 (→128.45) | **Xt + Eq.18**(X_PO,rF,K1) (warp 얀 종방향) | Xt↑·X_PO↑ → 강도↑ |
| 파단 변형률 | **Eq.18 tail**(rF,K1,X_PO), dmax | rF↑·X_PO↑ → 더 연성 |
| 잔류(영구) 변형 | **SY0, HISO** (매트릭스 소성) | SY0↓·HISO↓ → 잔류변형↑ |
| 온도 상승 시 강도 증가 추세 | **자동** (CTE mismatch → 잔류응력 재분포) | 구성재 강도는 온도독립 유지 |

핵심: 논문의 "고온일수록 강해짐"은 **열잔류응력 재분포**에서 자동으로 나옵니다
(매트릭스 잔류인장→잔류압축 전환). 구성재 강도를 온도별로 바꾸지 마세요 —
세 온도 카드를 동일하게 두고, 추세가 안 맞으면 CTE나 냉각손상을 점검하세요.

---

## 3. 단계별 보정 순서 (권장)

**Stage A — 안정성/기저 확인.** 먼저 소성 OFF(`SY0=0`)·Eq.18 OFF(`X_PO=0`)로
한 번 돌려 (a) 세 해석이 수렴하는지, (b) 냉각 후 매트릭스 손상이 논문처럼
광범위(≈100%)한지, 얀 횡방향 손상이 생기는지 SDV로 확인.

**Stage B — 얀 횡·전단(Yt, Yc, S).** 냉각 상태와 초기 비선형을 지배. 23 °C 곡선의
초기 기울기와 비선형 개시가 논문과 맞도록 Yt, S23을 먼저 조정.

**Stage C — 얀 종방향 + Eq.18 (Xt, X_PO, rF, K1).** 23 °C 극한강도(128.45)와 파단
변형률(≈0.15 %)을 맞춤. Xt는 2835 근방에서, tail은 X_PO·rF·K1로.

**Stage D — 매트릭스 소성(SY0, HISO).** 곡선의 잔류변형/형상 미세조정. 강도보다
곡선 모양이 목적이면 마지막에.

**Stage E — 온도 검증.** 500/1000 °C가 179/199 근방에 오는지 확인. 세 온도 카드는
동일하므로, 차이는 열잔류응력에서 나와야 함. 추세가 틀리면 냉각 수렴/CTE 재점검.

각 단계에서 `plot_compare.py`로 논문과 겹쳐 확인하고, 한 번에 하나의 그룹만
바꾸세요(시행착오 추적성).

---

## 4. 수렴/안정성 팁 (softening 해석)

- **eta (점성 정규화, matrix slot 10 / yarn slot 24):** 수렴이 어려우면 0.02→0.05
  로 올리고, 속도의존이 과하면 낮추세요. Ge 2018 §3.2: "작게 유지."
- **cutback 3종 (cut_trig/safety/maxf):** 손상 점프가 크면 자동으로 Δt를 줄임.
  기본 1.15/0.75/0.50 유지 권장.
- **`*Static` 증분:** 냉각·인장 스텝은 초기 1e‑3~5e‑4, 최소 1e‑12, 최대 2.5e‑3
  (이미 설정됨). 단 T500/T1000 덱의 **가열 스텝은 초기 0.005 / 최대 0.01**로
  더 크게 잡혀 있습니다(손상 진전이 없는 구간이므로 의도된 설정).
  발산 시 초기·최대 증분을 더 줄이세요.
- **dmax=0.99:** 완전파괴(1.0) 특이점 방지. 유지.
- **double precision 필수** (`abaqus ... double`) — UMAT이 배정밀도 가정.

---

## 5. 파라미터 유도 근거 (참고)

- **Xt=Vf·X_T300,t:** 종방향은 섬유지배(rule of mixtures). Vf=0.792, X_T300,t=3580
  (Ge Table 2 = Zhang Table 1) → 2835. Xc 동일 논리로 1956.
- **G1t=G1c=12.5, (Gtt=Gtc=1.0):** Ge 2018 Table 3(탄소/페놀). C/SiC는 더 취성이라
  종방향은 12.5로 시작하되 필요시 낮추고, 횡방향은 우선 고정 A=2.0(G=0) 사용.
- **X_PO, rF, K1 (Eq.18):** Ge Eq.16–17의 보조변수. Zhang 2022는 값을 본문에 싣지 않고
  Ref.[30]으로 미룸(미확보) → pull-out 응력 X_PO≈0.2–0.3·Xt, 전이 rF≈2–4, 선형연화 K1은
  E1의 수 % 수준에서 시작.
  주의: X_PO≪Xt인 시작값에서는 손상 개시 순간 d가 유한 점프(≈0.22–0.27)로 발생한 뒤
  지수 꼬리가 이어지는 강하–꼬리(drop-then-tail) 응답이 된다. 선형 연화 가지를 원하면
  정합조건 X_PO ≥ Xt·[1 − (K1/E1)(rF−1)]을 만족시킬 것.
- **SY0, HISO:** 논문의 "pseudo‑ductility"(매트릭스 소성)용. C/SiC 잔류변형이
  작으므로 SY0는 310에 가깝게(≈250), HISO는 크게(≈1e5) 시작해 소성량을 제한.
- **매트릭스는 냉각 중 잔류인장으로 조기 손상(논문: 845 °C에서 100%)** → 인장하중
  단계에서 매트릭스는 이미 크게 손상됨. 따라서 극한강도는 주로 **얀**이 지배.

---

## 6. 목표값 (Table 3, 재현 대상)

| T (°C) | 실험 (MPa) | 논문 시뮬 (MPa) | 인장스텝 적용변형 |
|---|---|---|---|
| 23 | 116.17 ± 8.78 | **128.45** | εxx ≤ 0.15 % |
| 500 | 160.19 ± 14.83 | **179.42** | εxx ≤ 0.32 % |
| 1000 | 173.28 ± 12.94 | **199.15** | εxx ≤ 0.48 % |

목표는 논문 시뮬 곡선/강도의 재현입니다(실험은 밴드로 참고). 강도뿐 아니라
곡선 형상(초기기울기·비선형·파단변형)까지 맞추면 검증 완료로 볼 수 있습니다.
