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

### ⚠️ P0/P1/P2 는 **온도가 아니다** — 자주 헷갈리는 지점

`P` 는 **PAPERFAITH 체인의 링크 번호**다. **셋 다 23 °C 한 온도**이며,
바꾼 것은 온도가 아니라 **모델 파라미터 하나씩**이다.

```
P0  =  23 °C,  Weibull 산포 제거 (WEIBM=0)
P1  =  23 °C,  P0 + 논문 파손기준 (MCRIT=1)
P2  =  23 °C,  P1 + 얀 횡인장강도 (Yt=50)
```

온도 시리즈는 완전히 다른 파일이다:
`Try_0805까지\Try_1430\CSIC_t500.odb` (500 °C),
`CSIC_t1000.odb` (1000 °C).

**세 P odb 의 스텝 구성 (냉각·인장 둘 다 들어 있다. 승온은 없다):**

| 스텝 | 이름 | 내용 | 논문 대응 |
|---|---|---|---|
| 1 | `Manufacturing_Cooling` | 1050 → 23 °C | Fig.3 / **Fig.4** / Fig.5 |
| 2 | `Tension_23C` | 23 °C 인장 | **Fig.11 / Fig.12 / Fig.A1**, Table 3 (23 °C 행) |
| 3~8 | `HOM_E11`~`HOM_G23` | 손상 후 6×6 강성 | (논문에 없음, 우리 추가) |

**승온(Heating) 스텝은 P 시리즈에 없다.** 논문 Fig.6/7/8/9/10 은
23 °C 를 경유해 시험온도로 올리는 `CSIC_t500.odb` / `CSIC_t1000.odb`
에서만 나온다.

### 런 ↔ 논문 그림 대응 한눈에

| 논문 | 온도 | 어느 odb |
|---|---|---|
| Fig.3/4/5 (냉각) | 1050→23 | **P0/P1/P2** 의 스텝 1 |
| Fig.6 (승온 불변) | 23→500, 23→1000 | t500 / t1000 |
| Fig.7/8 (승온 23→500) | | t500 |
| Fig.9/10 (승온 500→1000) | | t1000 |
| **Fig.11/12/A1** | **23 °C 인장** | **P0/P1/P2** 의 스텝 2 |
| Fig.13/14/A2 | 500 °C 인장 | t500 |
| Fig.15/16/A3 | 1000 °C 인장 | t1000 |
| Table 3 | 23 / 500 / 1000 | P (23 °C) + t500 + t1000 |

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
