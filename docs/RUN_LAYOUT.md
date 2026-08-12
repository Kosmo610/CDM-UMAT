# 해석 폴더 규약 (워크스테이션 E: 드라이브)

여러 해석을 동시에 돌릴 때 **폴더를 나눠야 한다.** 같은 폴더에서
동시에 컴파일하면 `standardU.obj` / `standardU.lib` 임시파일이
충돌한다. 그래서 잡 하나당 폴더 하나를 쓴다.

## 트리 (2026-08-07 `dir /s /b *.odb` 실측)

**중요: 2026-08-05 이전 폴더는 `Try_0805까지\` 아래로 들어갔다.**
그래서 깊이가 폴더마다 다르다 → **스크립트는 `..\` 가 아니라
절대경로 `E:\LTH\<이름>.py` 로 부를 것.** `Try_0805까지\Try_1430`
에서 `..\` 은 `E:\LTH\Try_0805까지\` 를 가리켜 실패한다.

```
E:\LTH\
├─ extract_tension.py            ← 최신판 1개만. E:\LTH\ 절대경로로 부름
├─ extract_cooling_damage.py     ← 냉각/승온 이력 (논문 Fig.4, Fig.6)
├─ extract_homogenization.py     ← HOM_* 섭동 6x6 강성
├─ extract_damage_histogram.py   ← 손상변수 분포 (Fig.A1~A3)
├─ make_paper_figures.py         ← 인장 그림 (Fig.11/13/15, Table 3)
├─ make_fig4_cooling.py          ← 냉각/승온 그림 (Fig.4, Fig.6)
├─ make_fig_a1_histogram.py      ← 히스토그램 그림 (Fig.A1~A3)
├─ make_odb_images.py            ← 상별 컨투어 (Fig.3/5/7/8/9/10/12)
├─ find_frames.py                ← 변형률/온도 → 프레임 번호
│    (그림별 명령 전체는 docs/PAPER_FIGURE_PLAYBOOK.md)
│    ※ audit_temperature_props.py 는 odb 가 필요 없다 —
│      저장소에서 그냥 `python verification/audit_...py`
│
├─ Try_P0\   CSIC_t23_p0.odb     ★ PAPERFAITH: Weibull 제거   (완료)
├─ Try_P1\   CSIC_t23_p1.odb     ★ PAPERFAITH: +MCRIT=1       (완료)
├─ Try_P2\   CSIC_t23_p2.odb     ★ PAPERFAITH: +Yt=50         (완료)
│
├─ Try_C\    CSIC_t23_long.odb   23 C 연장 (중단)
├─ Try_D500\  CSIC_t500_direct.odb    DIRECT 500 C   (완료)
├─ Try_D1000\ CSIC_t1000_direct.odb   DIRECT 1000 C  (완료)
│
└─ Try_0805까지\                  ← 08-05 이전 전부 여기로 이동
   ├─ Try_1300\ CSIC_t23_gf.odb        V2_6 GF1T
   │            CSIC_t23_noTRS.odb     열잔류응력 제거
   └─ Try_1430\ CSIC_t1000.odb         1050->23->1000 경유  ★Fig.6/9/10
                CSIC_t500.odb          1050->23->500  경유  ★Fig.6/7/8
                CSIC_t23.odb           23 C 초기
                CSIC_t23pc.odb         23 C (pc)
                peek500.odb            진단용
```

**우리 것이 아닌 폴더** (같은 드라이브에 있지만 다른 프로젝트다.
`dir *.odb` 결과에 섞여 나오므로 헷갈리지 말 것):

```
E:\LTH\3D_0728_900\, 3D_0728_1530\, 3D_0729_1400\   초기 3D 시험 (구형)
E:\LTH\LTH_RUN1_0807_1712\                          LTH_COND_* 전도 해석
E:\LTH\[01] 2D CDM UMAT ...\, [02] ..., [03] ..., [04] ...   별개 과제
```

### 덱(.inp) 실제 경로 — 2026-08-10 `dir /s /b *.inp` 실측

**추측 금지.** 실제 이름은 `XT421` 계보를 달고 있다.

| 런 | 덱 경로 (E:\LTH\ 기준) |
|---|---|
| P0 | `Try_P0\CSIC_PLAIN_WEAVE_RVE_23C_P0.inp` |
| P1 | `Try_P1\CSIC_PLAIN_WEAVE_RVE_23C_P1.inp` |
| P2 | `Try_P2\CSIC_PLAIN_WEAVE_RVE_23C_P2.inp` |
| t23_long (P0 의 부모) | `Try_C\CSIC_PLAIN_WEAVE_RVE_23C_XT421_LONG.inp` |
| **500 °C 경유** | `Try_0805까지\Try_1430\CSIC_PLAIN_WEAVE_RVE_500C_XT421.inp` |
| **1000 °C 경유** | `Try_0805까지\Try_1430\CSIC_PLAIN_WEAVE_RVE_1000C_XT421.inp` |
| 23 °C (같은 계보 기준선) | `Try_0805까지\Try_1430\CSIC_PLAIN_WEAVE_RVE_23C_XT421.inp` |
| 23 °C PAPERCRIT | `Try_0805까지\Try_1430\CSIC_PLAIN_WEAVE_RVE_23C_PAPERCRIT_XT421.inp` |
| 23 °C GF / noTRS | `Try_0805까지\Try_1300\CSIC_PLAIN_WEAVE_RVE_23C_XT421_GF.inp` / `..._XT421_noTRS.inp` |
| DIRECT 500 / 1000 | `Try_D500\..._500C_DIRECT_GF.inp` / `Try_D1000\..._1000C_DIRECT_GF.inp` |

`dir *.inp` 결과에는 다른 과제(`2d_0730\`, `LTH_*\`, `[01]~[04]`)
덱이 섞여 나온다 — 위 표에 없는 것은 우리 것이 아니다.

### 자주 쓰는 절대경로

| 용도 | 경로 |
|---|---|
| Fig.6/7/8 승온 500 | `E:\LTH\Try_0805까지\Try_1430\CSIC_t500.odb` |
| Fig.6/9/10 승온 1000 | `E:\LTH\Try_0805까지\Try_1430\CSIC_t1000.odb` |
| 23 C 기준선 (GF) | `E:\LTH\Try_0805까지\Try_1300\CSIC_t23_gf.odb` |
| PAPERFAITH 체인 | `E:\LTH\Try_P0\|Try_P1\|Try_P2\` |

## 각 폴더에 들어가는 것 — 4개

| 파일 | 출처 |
|---|---|
| `CSIC_PLAIN_WEAVE_RVE_<T>C_DIRECT_GF.inp` | DIRECT zip |
| `UMAT_CSIC_RVE_DAMAGE_V2_7.for` | DIRECT zip |
| `CSIC_PLAIN_WEAVE_RVE_DAMAGE_V2_2.ori` | **기존 폴더에서 복사** (zip에 없음) |
| (해석이 만드는 나머지) | Abaqus |

`.ori` 는 덱이 `Input=` 으로 참조하는 메쉬 원본이라 없으면 즉시
실패한다. 용량이 커서 배포 zip 에 넣지 않는다.

## 이름 규약

| 항목 | Try_D500 | Try_D1000 |
|---|---|---|
| 폴더 | `E:\LTH\Try_D500` | `E:\LTH\Try_D1000` |
| 덱 | `CSIC_PLAIN_WEAVE_RVE_500C_DIRECT_GF.inp` | `CSIC_PLAIN_WEAVE_RVE_1000C_DIRECT_GF.inp` |
| job | `CSIC_t500_direct` | `CSIC_t1000_direct` |
| 추출 태그 | `_500D` | `_1000D` |
| 산출 CSV | `tension_stress_strain_500D.csv` | `tension_stress_strain_1000D.csv` |
| | `tension_damage_500D.csv` | `tension_damage_1000D.csv` |

### GF1T 정정 배치

| 항목 | Try_GFC | Try_GFC25 |
|---|---|---|
| 폴더 | `E:\LTH\Try_GFC` | `E:\LTH\Try_GFC25` |
| 덱 | `CSIC_PLAIN_WEAVE_RVE_23C_GFC.inp` | `CSIC_PLAIN_WEAVE_RVE_23C_GFC25.inp` |
| job | `CSIC_t23_gfc` | `CSIC_t23_gfc25` |
| 추출 태그 | `_GFC` | `_GFC25` |
| 차이 | 23C GF 대비 **GF1T 만** 0.03962→0.022728 | GFC 대비 **eta 만** 0.5x→0.25x |

## 다섯 런이 논문의 무엇을 따라한 것인가 (2026-08-12 확정판)

### 먼저 — 이름 읽는 법

이름이 **두 축**을 한 문자열에 담고 있어서 헷갈린다.

```
P2 T500
^^ ^^^^
|  └─ 시험온도 (T500 = 500 °C, T1000 = 1000 °C, 없으면 23 °C)
└──── 모델 카드 번호 (PAPERFAITH 체인 링크. 온도가 아니다)
```

`P` 는 **온도가 아니라 카드 세대**다. 링크당 숫자 하나씩만 바꿨다.

```
P0  =  Weibull 산포 제거 (WEIBM=0)      ← 논문은 결정론적
P1  =  P0 + 논문 파손기준 (MCRIT=1)      ← 논문 Eq.15/16
P2  =  P1 + 얀 횡인장강도 (Yt=50)
```

### 다섯 런 전부 **논문의 같은 절차**를 따른다

논문 3.2.4 절의 순서는 **제조 냉각 → 시험온도로 승온 → 인장** 이다
(§5.11A). 다섯 런 모두 이 순서이고, **다른 것은 시험온도와 카드뿐**이다.

| | 스텝 1 | 스텝 2 | 스텝 3 | 스텝 4~9 |
|---|---|---|---|---|
| **P0 / P1 / P2** | 냉각 1050→**23** | (없음 — 이미 23) | 인장 **23 °C** | HOM_* |
| **P2T500** | 냉각 1050→23 | **승온 23→500** | 인장 **500 °C** | HOM_* |
| **P2T1000** | 냉각 1050→23 | **승온 23→1000** | 인장 **1000 °C** | HOM_* |

- **냉각은 다섯 런 전부에 들어 있다.** 빼는 옵션이 아니라 제조
  잔류응력을 만드는 단계이며, 논문 Fig.3/4/5 가 곧 이 단계다.
- **승온은 P2T500 / P2T1000 에만 있다.** 23 °C 런은 냉각이 이미
  23 °C 에서 끝나므로 승온 단계가 필요 없다 — 논문의 23 °C 케이스도
  같다. **빠뜨린 것이 아니라 정의상 없는 것이다.**
- `HOM_*` 6 스텝은 **논문에 없는 우리 추가분** (손상 후 6×6 강성).

### 그래서 각 런이 논문의 어느 그림인가

| 런 | 냉각 (Fig.3/4/5) | 승온 (Fig.6~10) | 인장 (Fig.11~16, A1~A3, Table 3) |
|---|---|---|---|
| **P0** | ✔ Weibull 없는 냉각 | — | 23 °C — Fig.11/12/A1 |
| **P1** | ✔ 논문 기준 냉각 | — | 23 °C — Fig.11/12/A1 |
| **P2** | ✔ **기준 냉각** | — | 23 °C — **Fig.11/12/A1 확정판** |
| **P2T500** | ✔ (P2 와 비트 일치) | ✔ 23→500 — **Fig.7/8** | 500 °C — **Fig.13/14/A2** |
| **P2T1000** | ✔ (P2 와 비트 일치) | ✔ 23→1000 — **Fig.9/10** | 1000 °C — **Fig.15/16/A3** |

Table 3 세 행 = **P2 (23) + P2T500 (500) + P2T1000 (1000).**
같은 카드·같은 하중속도라서 세 점을 나란히 놓을 수 있다 (§5.21C).

### 왜 P0/P1/P2 는 셋이고 온도는 하나인가

**P0→P1→P2 는 온도 시리즈가 아니라 카드 검증 시리즈다.** 23 °C 한
온도에 고정해 두고 파라미터를 하나씩 논문 쪽으로 옮기며 무엇이
무엇을 움직이는지 본 것이다. 그 결과 P2 가 논문에 가장 가깝다고
확정됐고(§5.17), **그 확정된 카드 하나만 온도 시리즈로 확장한 것이
P2T500 / P2T1000** 이다. 그래서 앞에 `P2` 가 붙어 있다.

```
P0 ─→ P1 ─→ P2 ─┬─→ (23 °C 그대로)      Table 3 23 °C 행
   카드 검증      ├─→ P2T500              Table 3 500 °C 행
   (23 °C 고정)   └─→ P2T1000             Table 3 1000 °C 행
```

### 냉각 이력이 세 런에서 같은지 확인됨

P2 / P2T500 / P2T1000 의 냉각 끝 손상요소율이 **소수점 15 자리까지
동일**하다 (58.753304060991326 등, §5.21A). 세 런은 같은 냉각을
공유하며, 갈라지는 것은 승온부터다. **온도 비교가 냉각 차이로
오염되지 않았다는 증명**이다.

### 옛 500/1000 런과 혼동하지 말 것

`Try_0805까지\Try_1430\CSIC_t500.odb` / `CSIC_t1000.odb` 도 같은
"23 °C 경유" 구조지만 **옛 카드(XT421 계보, P 이전)** 이고 하중속도도
다르다. 지금 Table 3 에 쓰는 것은 **P2T500 / P2T1000** 이다.
옛 런은 Fig.6 승온 이력 진단에만 남아 있다.

### P2 카드 온도 시리즈 — **완료** (준비 문서: `BATCH_T500_T1000_P2.md`)

| 항목 | Try_P2T500 | Try_P2T1000 |
|---|---|---|
| job | `CSIC_t500_p2` | `CSIC_t1000_p2` |
| 태그 | `_P2T500` | `_P2T1000` |
| 카드 | P2 와 동일 (WEIBM=0 / MCRIT=1 / Yt=50) | 동일 |
| UMAT | **V2_7P** (SDV 논문 표시) | 동일 |
| 승온 스텝시간 | 1.0 | **2.05** (dT/dt 통일, §5.18D) |
| 인장 span | 0.008495 로 통일 (§4.1) | 동일 |
| 결과 | 119.15 MPa | 109.72 MPa (§5.21C) |

### 다음 배치 후보 — P3 (얀 XT 를 논문 자신의 값으로)

§5.23E 에 **사전등록 완료.** 변수는 얀 카드 **P11 하나**.

| 항목 | 값 |
|---|---|
| 변경 | 얀 P11 `421.0` → **`2835.0`** (Table 1 X_f,t=3580 × Vf 0.79194) |
| 고정 | 나머지 전부 P2 와 동일. span 0.008495, 승온 램프 통일 |
| 온도 | 23 / 500 / 1000 세 점 (P2 계열과 1:1 대응) |
| 노림 | 온도 추세 **부호**가 뒤집히는지 — 최대 미해결 항목의 직격 |
| 선행 | 얀 전단분율 진단 SV 1칸 추가 + `*Depvar` 16→17 (§5.23E) |

**돌리기 전에 진단 SV 를 먼저 넣을 것.** 배치 뒤에 붙이면 재실행이
강제된다 (V2_7P 때 같은 실수를 되돌린 전례).

### PAPERFAITH 체인 (논문 완벽 재현 트랙 — 링크당 변수 1개)

| 항목 | Try_P0 | Try_P1 | Try_P2 |
|---|---|---|---|
| 덱 | `..._23C_P0.inp` | `..._23C_P1.inp` | `..._23C_P2.inp` |
| job | `CSIC_t23_p0` | `CSIC_t23_p1` | `CSIC_t23_p2` |
| 태그 | `_P0` | `_P1` | `_P2` |
| 차이 | t23_long 대비 **WEIBM=0** | P0 + **MCRIT=1** (V2_7) | P1 + **Yt=50** |
| 판정 | Weibull↔손상률 갭 | 논문 기준의 효과 | Fig.4 의 88% |

태그는 `make_paper_figures.py` 의 `TAGMAP` 에 등록되어 있어야 온도가
자동으로 잡힌다. `_500D` / `_1000D` 는 등록되어 있다.

## 왜 이 태그인가

`_500C` / `_1000C` 는 **23 C 를 경유한 기존 런**이 이미 쓰고 있다.
두 방식을 나란히 비교하는 것이 이번 배치의 목적이므로 태그를 반드시
구분해야 한다. `D` = DIRECT.

## 그림

```
cd /d E:\LTH
python make_paper_figures.py Try_P0 Try_P1 Try_P2 Try_C Try_D500 Try_D1000 ^
       "Try_0805까지\Try_1300" "Try_0805까지\Try_1430" --out E:\LTH
```

폴더를 여러 개 나열하면 전부 합쳐서 그린다. 같은 태그가 두 폴더에
있으면 이름 뒤에 폴더명이 붙는다. **공백이 든 경로는 따옴표로 감쌀 것.**
