# M1 — Zhang 2022 재현 해석 (실행 안내)

**패키지 생성: 2026-07-28 15:19 KST**

이 3개 해석이 **논문 전체의 병목**입니다. 여기서 나온 보정 결과 없이 거시 해석을 쌓으면
잘못된 물성 위에 논문을 짓게 됩니다.

---

## ⚠️ 먼저 — 이 파일이 반드시 있어야 합니다

`.inp` 3개가 모두 아래 파일을 외부 참조합니다 (208472행):

```
Input=CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori
```

**TexGen 방향(orientation) 파일이고 이 저장소에 없습니다.** 사용자 PC에 있는 것을
**`abaqus/` 폴더 안, `.inp`와 같은 위치**에 두세요. 없으면 잡이 즉시 죽습니다.

확인:
```
dir abaqus\CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori
```

---

## 실행 — 세 잡은 서로 완전히 독립입니다

RT23 / T500 / T1000은 **서로의 결과를 쓰지 않습니다.** 순차로 돌릴 이유가 없습니다.

> ### **Abaqus Command 창을 3개 열고, 각각에 아래를 하나씩 입력하세요.**

**1번 창**
```
abaqus job=Job-RT23 input=abaqus/ZHANG2022_RT23_V2_0.inp user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
```

**2번 창**
```
abaqus job=Job-T500 input=abaqus/ZHANG2022_T500_V2_0.inp user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
```

**3번 창**
```
abaqus job=Job-T1000 input=abaqus/ZHANG2022_T1000_V2_0.inp user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
```

- `double`은 **필수**입니다 (단정밀도로 돌리면 손상 적분이 깨집니다).
- `interactive`는 진행 상황을 창에서 보기 위한 것입니다. 빼면 백그라운드로 돕니다.
- CPU가 넉넉하면 각 명령에 `cpus=4` 를 붙이세요. 3개를 동시에 돌리므로
  **총 코어 수를 넘지 않게** 나누세요 (예: 12코어면 각 `cpus=4`).

---

## 끝난 뒤 — 후처리

세 잡이 다 끝나면 순서대로:

```
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb
abaqus python postprocess/extract_ss_curve.py Job-T500.odb
abaqus python postprocess/extract_ss_curve.py Job-T1000.odb
```

```
python postprocess/plot_compare.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv
```

→ `ss_curves_by_temperature.png` 와 강도 비교표가 나옵니다.

---

## 목표값 (Zhang 2022 Table 3)

| 온도 | 목표 극한강도 |
|---|---|
| 23 °C | **128.45 MPa** |
| 500 °C | **179.42 MPa** |
| 1000 °C | **199.15 MPa** |

첫 실행에서 이 값이 맞지 않는 것이 **정상**입니다. 논문이 공개하지 않은 손상 파라미터가
있어서 보정이 필요합니다. 절차는 같이 넣은 **`CALIBRATION_GUIDE.md`** 를 보세요.

---

## 실행 결과로 알려주셔야 할 것

보정을 진행하려면 다음이 필요합니다. **`.odb`는 크니까 보내지 마시고**, 아래만 주세요:

1. **세 `*_ss.csv` 파일** (각 수백 KB) — 거시 응력-변형 곡선
2. **`.sta` 파일 3개** — 수렴 이력. 잘렸는지, 어디서 힘들어했는지 봅니다
3. **`.msg`에서 경고/에러가 있으면 그 부분**
4. 각 잡의 **소요 시간** — 이후 해석 규모를 잡는 데 씁니다

## 같이 확인해 두면 좋은 것 (선택)

이후 RVE 가상시험에 필요한 정보라 지금 한 번에 봐두면 좋습니다:

- Abaqus/CAE에서 `Job-RT23.odb`를 열어 **ConstraintsDriver0~5 노드셋이 존재하는지**,
  그리고 **드라이버 3/4/5가 각각 어느 전단성분인지**. TexGen 버전마다 다르고,
  나중에 `homogenize.py --shear-order` 를 정하는 데 필요합니다.
- **RVE 바운딩박스 치수** (`extract_ss_curve.py`가 출력해 줍니다) — 균질화에 씁니다.

---

## 문제가 생기면

| 증상 | 원인 |
|---|---|
| 시작하자마자 `.ori` 관련 에러 | 위 §1의 방향 파일이 없음 |
| `PROPS(22)=30.0` 가드 에러 | V2_x 계보 카드를 V1_0 UMAT에 넣은 것. 이 패키지 조합은 맞음 |
| 수렴 실패, 손상 급증 | 카드의 `eta`(점성 정규화)와 `max_djump`를 올리세요. `CALIBRATION_GUIDE.md` 참조 |
| 결과가 전부 탄성 | 카드의 `enable` 슬롯이 0인지 확인 (얀 28번, 매트릭스 14번) |
