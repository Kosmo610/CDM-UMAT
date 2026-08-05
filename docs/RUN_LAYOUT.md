# 해석 폴더 규약 (워크스테이션 E: 드라이브)

여러 해석을 동시에 돌릴 때 **폴더를 나눠야 한다.** 같은 폴더에서
동시에 컴파일하면 `standardU.obj` / `standardU.lib` 임시파일이
충돌한다. 그래서 잡 하나당 폴더 하나를 쓴다.

## 트리

```
E:\LTH\
├─ extract_tension.py            ← 최신판 1개만. 각 폴더에서 ..\ 로 부름
├─ make_paper_figures.py         ← 최신판 1개만
│
├─ Try_1300\                     23 C 계열 (완료)
│    CSIC_t23_gf.odb                     V2_6 GF1T
│    CSIC_t23_noTRS.odb                  열잔류응력 제거
├─ Try_1430\                     고온 (완료)
│    CSIC_t1000.odb                      1050->23->1000 경유
├─ Try_C\                        23 C 연장 (완료, 중단)
│    CSIC_t23_long.odb                   목표 0.006, 속도 동일
│
├─ Try_D500\                     DIRECT 500 C   (실행 중)
├─ Try_D1000\                    DIRECT 1000 C  (실행 중)
├─ Try_GFC\                      ★ GF1T 정정 23 C
└─ Try_GFC25\                    ★ GF1T 정정 + eta 0.25x
```

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

### GF1T 정정 배치

| 항목 | Try_GFC | Try_GFC25 |
|---|---|---|
| 덱 | `CSIC_PLAIN_WEAVE_RVE_23C_GFC.inp` | `CSIC_PLAIN_WEAVE_RVE_23C_GFC25.inp` |
| job | `CSIC_t23_gfc` | `CSIC_t23_gfc25` |
| 태그 | `_GFC` | `_GFC25` |
| 차이 | 23C GF 대비 **GF1T 만** 0.03962→0.022728 | GFC 대비 **eta 만** 0.5x→0.25x |
| 산출 CSV | `tension_stress_strain_500D.csv` | `tension_stress_strain_1000D.csv` |
| | `tension_damage_500D.csv` | `tension_damage_1000D.csv` |

태그는 `make_paper_figures.py` 의 `TAGMAP` 에 등록되어 있어야 온도가
자동으로 잡힌다. `_500D` / `_1000D` 는 등록되어 있다.

## 왜 이 태그인가

`_500C` / `_1000C` 는 **23 C 를 경유한 기존 런**이 이미 쓰고 있다.
두 방식을 나란히 비교하는 것이 이번 배치의 목적이므로 태그를 반드시
구분해야 한다. `D` = DIRECT.

## 그림

```
cd /d E:\LTH
python make_paper_figures.py Try_1300 Try_1430 Try_C Try_D500 Try_D1000 --out E:\LTH
```

폴더를 여러 개 나열하면 전부 합쳐서 그린다. 같은 태그가 두 폴더에
있으면 이름 뒤에 폴더명이 붙는다.
