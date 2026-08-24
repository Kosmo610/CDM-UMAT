# PATCHFIX — A단계 후처리 스크립트 수정본

**해석은 다시 돌리지 않습니다.** 어제 만든 `PATCH_PBC.odb`, `CBAND_N5/N10/N20.odb`가
그대로 쓰입니다. 이 두 파일만 **그 ODB들이 있는 폴더에 덮어쓰고** 아래를 실행하세요.

## 실행

```
abaqus python patch_report.py PATCH_PBC.odb CBAND_N5.odb CBAND_N10.odb CBAND_N20.odb
```

이거 하나면 됩니다. **터미널에 표가 다 찍힙니다** — 그림은 없어도 판정할 수 있습니다.

## 그림 (선택)

윈도우에는 `python3`가 없습니다. **`python`** 으로 쓰세요.

```
python plot_cband.py cband_curves.csv
```

`python`도 없다고 나오면 **건너뛰세요.** `cband_curves.csv`만 보내주시면 제가 그립니다.

## 무엇이 고쳐졌나

| # | 증상 | 원인 |
|---|---|---|
| 1 | 6×6 강성행렬이 전부 `nan` | `*Node Output, nset=Foo` 는 ODB 영역 키에 "Foo"를 넣지 않는다. Abaqus는 `Node ASSEMBLY.5681`로 이름 짓는다 → 이름으로 못 찾음. 이제 **절점 번호로 되찾는다**(`driver_audit.py`가 이미 쓰던 방식) |
| 2 | B단계에서 `AttributeError: 'Repository' object has no attribute 'get'` | `historyOutputs`는 dict가 아니라 **Repository**다. `.get()`이 없다. `in`/`[]`/`.keys()`로 교체 |
| 3 | **전부 `nan`인데 "PASS"가 떴다** | `nan > 0.0`이 **False**라서 최악값이 0.0에 머물렀고, 데이터가 하나도 없는데 "worst rel. dev. 0.00e+00"으로 통과했다. 이제 **값이 다 있는지를 먼저 별도 관문으로 검사**하고, 없으면 무조건 FAIL |

3번이 가장 위험한 버그였습니다 — **검증 스크립트가 아무 데이터 없이 초록불을 켰습니다.**
`make_patch_tests.py --check`에 재발 방지 검사 8개를 넣어 다시는 통과할 수 없게 했습니다.

## 이제 나와야 하는 것

```
PASS  every entry of the 6x6 was recovered from the odb   all 36 present
PASS  the whole 6x6 matches the analytic isotropic C      worst rel. dev. <2e-4
PASS  the recovered stiffness is symmetric
PASS  strain field is uniform in step 1                   (어제 이미 통과)
PASS  free thermal expansion develops zero stress         (어제 이미 통과)
```

그리고 B단계 표에 `F_max`, `work`, `tail`, `ALLSD/IE`가 세 줄(N5/N10/N20) 찍힙니다.
**세 줄의 `work`와 `tail`이 서로 붙어야** 균열대 정규화가 작동하는 것입니다.
`ALLSD/IE`는 **5 % 미만**이어야 안정화가 결과를 왜곡하지 않은 것입니다.
