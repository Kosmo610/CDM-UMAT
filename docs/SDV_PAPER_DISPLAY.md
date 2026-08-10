# SDV 표시를 논문과 똑같이 (SDV14 / SDV1 / SDV2)

## 왜 우리는 `SDV_DMT` 로 나오고 논문은 `SDV14` 로 나오나

같은 것이다. Abaqus 는 `*Depvar` 에 **이름 줄을 주면** `SDV_이름`,
**안 주면** `SDV번호` 로 표시한다. 논문 팀은 이름을 안 붙였고 우리는
붙였다 — 표시 관행의 차이일 뿐, 상태변수라는 본질은 같다.

## 논문 SDV 번호의 의미 (Zhang 2022 그림 행 라벨에서 확정)

| 논문 표시 | 의미 | 우리 대응 (기존 이름) |
|---|---|---|
| **SDV1** | 얀 종방향(섬유) 손상 d1 | `SDV_DY1T` (슬롯 1) |
| **SDV2** | 얀 횡방향 손상 d2 | `SDV_DYTT` (기존 슬롯 3) |
| **SDV14** | 기지 손상 dm | `SDV_DMT` (슬롯 1) |

번호 자체는 그쪽 UMAT 의 STATEV 배열 위치다. 얀 손상이 1·2번,
기지 손상이 14번이라는 것은 얀 변수(압축 짝·문턱값 r·[17]계열
소성 변수들)가 3~13번을 채우고 그 뒤에 기지가 온다는 뜻이다.
1·2·14 의 의미는 그림 행 라벨로 확정이고, **3~13 의 내용은 논문에
공개돼 있지 않다.**

## 우리도 똑같이 나오게 하는 방법 = V2_7P + 이름 없는 *Depvar

두 가지를 **반드시 짝으로** 적용한다. 하나만 하면 라벨이 어긋난다.

### 1) UMAT: `UMAT_CSIC_RVE_DAMAGE_V2_7P.for`

V2_7 과 **수치 완전 동일** (식·기준·응답 무변경). 저장 위치만:

- 얀 `SV(2)↔SV(3)` 교환 → 횡손상 DYTT 가 **SDV2** 로
- 기지 `SV(14) = SV(1) 미러` → 기지 손상 DMT 가 **SDV14** 로
  (14번에 있던 진단값 MRJUMP 는 15번으로 이동)

### 2) 덱: *Depvar 이름 줄 삭제

두 재료의 `*Depvar` 블록을 아래로 교체한다 (이름 줄이 없으면
번호로 표시된다. 배치표는 주석으로 보존).

```
*Material, Name=SIC_MATRIX_DAMAGE
*Depvar
20,
** V2_7P 배치 (이름 없음 -> SDV번호로 표시):
**  1 DMT   2 DMC   3 RMT   4 RMC   5 DMACT  6 I1SGN  7 MMODE
**  8 TMINIT  9 XTE  10 ATEFF  11 MDJUMP  12 MCUTREQ  13 MTJUMP
** 14 = DMT 미러 (논문 SDV14)   15 MRJUMP   16-20 예비
```

```
*Material, Name=CSIC_YARN_DAMAGE
*Depvar
16,
** V2_7P 배치 (이름 없음 -> SDV번호로 표시):
**  1 DY1T (논문 SDV1)   2 DYTT (논문 SDV2)   3 DY1C   4 DYTC
**  5 RY1T  6 RY1C  7 RYTT  8 RYTC   9 DY1  10 DYT  11 YMODE
** 12 TYINIT  13 YDJUMP  14 YCUTREQ  15 YTEND  16 YRFAC
```

## 규칙

1. **이미 돌린 odb 는 안 바뀐다.** 이름은 해석 시점에 odb 에 박힌다.
   P0/P1/P2 는 영원히 `SDV_DMT` 식으로 표시된다. 번호 표시는
   V2_7P + 새 덱으로 **새로 돌린 해석부터**다.
2. **§4 변수 하나 규칙과 충돌하지 않는다.** 수치가 동일하므로
   비교 체인에 변수를 더하는 것이 아니다. 단, 검증 전 원칙대로
   **민감한 1변수 체인(P3=GF1T)에는 섞지 않는다** — P3 는 기존
   V2_7 로 돌리고, V2_7P 는 그 다음 배치(500/1000 등)부터 쓴다.
3. 추출 스크립트는 이름을 먼저 찾고 없으면 V2_7P 번호로 떨어지게
   전부 수정돼 있다 (`extract_tension` / `extract_cooling_damage` /
   `extract_damage_histogram` / `make_odb_images`). 즉 **기존 odb 와
   새 odb 를 같은 명령으로 섞어 처리할 수 있다.**
4. 이름 없는 덱을 **기존 V2_7 로 돌리면 안 된다** — SDV14 가 진단값
   (MRJUMP) 인 채 번호로 표시되어 그림이 오염된다. 반드시 짝으로.
