# 부호 규약 수정 — 0803 10:13 KST

## 결론부터: **주기경계조건(PBC)은 정확합니다.**

6×6 강성이 해석해와 **1e-8 상대오차로 일치**했습니다. 값이 전부 음수로 나온 것은
**제 리더의 부호 규약** 문제였고, 패치 테스트가 정답을 확정해 줬습니다.

| | 본 모델 | 해석해 | |
|---|---|---|---|
| $C_{11}$ | 134615.3845 | 134615.3846 | 1e-9 |
| $C_{12}$ | 57692.3109 | 57692.3077 | 5.6e-8 |
| $C_{44}$ | 38461.5396 | 38461.5385 | 3e-8 |
| 대칭성 | | | 1.07e-9 MPa |
| 변형률장 균일 | 26452점 | | **0.000e+00** |
| 자유 열팽창 응력 | | 0 | 1.29e-10 MPa |
| 드라이버 = $\alpha\Delta T$ | 5.000000e-04 | 5.000000e-04 | **일치** |

**PBC 구현에 오류가 없다는 것이 이것으로 증명되었습니다.** 제4장 L1의 마지막
미실행 항목이 닫힙니다.

## 무엇이 틀렸었나

드라이버 반력은 거시 변형률에 **일함수 켤레인 일반화 힘**입니다:

$$R = \frac{\partial W}{\partial \varepsilon} = \sigma V \quad\Rightarrow\quad \sigma = +\frac{R}{V}$$

세 리더가 모두 `-RF/V`로 쓰고 있었습니다. **패치 테스트가 유일한 해석해 케이스**이므로
이것이 부호의 최종 권위입니다.

## ★ M5 결과에 미치는 영향 — **없습니다**

| 스크립트 | 영향 | 이유 |
|---|---|---|
| `extract_ss_curve.py` | **없음** | 피크가 음수면 곡선을 통째로 뒤집는 보정이 들어 있었습니다. 즉 **강도 수치는 원래 맞았습니다.** |
| `driver_audit.py` | **없음** | 제가 필요한 값이 $\lvert\sigma\rvert/\lvert\sigma_{xx}\rvert$ **비율**이라 전역 부호가 상쇄됩니다. |

**이미 돌린 M5 후처리 결과가 있으면 그대로 유효합니다.** 다만 앞으로는 이 수정본을
쓰세요 — `extract_ss_curve.py`의 "뒤집기"는 **오류를 가리는 반창고**였고
(이번 부호 오류를 실제로 가렸습니다), 이제는 뒤집지 않고 **경고만** 냅니다.

## 사용법

기존 파일을 이 6개로 덮어쓰고, 평소대로 쓰시면 됩니다.

```
abaqus python patch_report.py PATCH_PBC.odb CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb > patch_report3.txt
```

이제 `the whole 6x6 matches the analytic isotropic C`까지 **PASS**가 나와야 합니다.

M5 후처리 (잡 하나 끝날 때마다 바로):
```
abaqus python extract_ss_curve.py M5_c26k_RT23.odb
abaqus python damage_census.py M5_c26k_RT23.odb
abaqus python driver_audit.py M5_c26k_RT23.odb
```

> `extract_ss_curve.py`가 **`WARNING: peak stress is NEGATIVE`** 를 찍으면
> 알려주세요. 수정 후에는 인장 시험에서 절대 나오면 안 되는 메시지입니다.

## 아직 남은 것 — 균열대(B)

균열대 판정은 **여전히 판정 불가**입니다(부호와 무관). `AFIX2_0803_1006.zip`의
`cband_damage.py`로 **손상이 몇 줄에 퍼졌는지** 먼저 확인하는 것이 순서입니다.
