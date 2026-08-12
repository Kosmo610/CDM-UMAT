# M5 — M4의 입력덱 오류 수정본 (0803 09:47 KST)

## 무엇이 잘못됐었나

M4는 `pre.exe`(입력 파일 처리기)에서 즉시 죽었습니다. **UMAT은 정상**입니다 —
컴파일·링크까지 다 통과했고(`End Linking ... standardU.lib`), 덱 문법이 틀렸습니다.

제가 힘 수렴 허용오차를 이렇게 썼습니다:

```
*Controls, parameters=field, field=force      <-- 이런 필드는 없습니다
 0.02,
```

**`FORCE`는 Abaqus의 필드가 아닙니다.** `FIELD=` 는 **해(解) 변수**를 가리키고,
응력–변위 해석에서 그것은 `DISPLACEMENT` 하나입니다. 힘 잔차 허용오차는 **바로 그
블록의 첫 번째 값** $R_n^\alpha$ 입니다(기본 0.005 = "잔차가 평균 유량의 0.5 % 미만"
규칙). 두 번째 값이 변위 보정 기준 $C_n^\alpha$ 입니다. 그래서 올바른 표기는:

```
*Controls, parameters=field, field=displacement
 0.02, 1
```

M5는 **그것만** 고쳤습니다.

## M3(정상 실행됨) 대비 차이 — 전부 이것뿐입니다

```
 , 1                    ->   0.02, 1          (힘 허용오차 0.005 -> 0.02)
(없음)                  ->   *Boundary
                             ConstraintsDriver3, 1, 1, 0.0
                             ConstraintsDriver4, 1, 1, 0.0
                             ConstraintsDriver5, 1, 1, 0.0
```

`diff M3 M5`로 확인했고 **그 외 단 한 줄도 다르지 않습니다.** 메시·물성·스텝 구조
전부 동일합니다. 물성 구성은 여전히 **CONFIG_V**(`zero=1050`, Zhang 카드)입니다.

## 실행 — Abaqus Command 창 3개, 각각 하나씩

**창 1**
```
abaqus job=M5_c26k_RT23 input=M5_c26k_RT23.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

**창 2**
```
abaqus job=M5_c26k_T500 input=M5_c26k_T500.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

**창 3**
```
abaqus job=M5_c26k_T1000 input=M5_c26k_T1000.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

### 예비 (선택) — 위 셋 중 하나가 끝난 뒤 그 창에서
```
abaqus job=M5_c26k_RT23_z600 input=M5_c26k_RT23_z600.inp user=UMAT_CSIC_THERMSHOCK_V3_0.for double interactive cpus=10 memory="70gb"
```

> **30초 안에 판별됩니다.** `pre.exe`는 몇 초면 끝납니다. `Begin Analysis Input File
> Processor` 다음에 에러 없이 `Begin Abaqus/Standard Analysis`가 나오면 통과입니다.
> **세 창 다 그 지점을 넘기는지만 먼저 확인**하고 자리를 뜨세요.

## 완료 후 명령 — **잡 하나 끝날 때마다 바로**

```
abaqus python extract_ss_curve.py M5_c26k_RT23.odb
abaqus python damage_census.py M5_c26k_RT23.odb
abaqus python driver_audit.py M5_c26k_RT23.odb
```
`T500`, `T1000`도 잡 이름만 바꿔 동일하게.

셋 다 끝나면 (윈도우에서는 `python3`가 아니라 **`python`**):
```
python plot_compare.py M5_c26k_RT23_ss.csv M5_c26k_T500_ss.csv M5_c26k_T1000_ss.csv
```

## 목표

| 케이스 | Zhang Table 3 | M3에서 도달 |
|---|---|---|
| RT23 | **128.45 MPa** | 98.2 % |
| T500 | **179.42 MPa** | 67.3 % |
| T1000 | **199.15 MPa** | 57.2 % |

`driver_audit`의 **전단응력 / $\sigma_{xx}$ 비율**을 꼭 알려주세요 — **1 % 미만**이면
전단 구속이 정당하고, 넘으면 논문에 한계로 명시해야 합니다.
