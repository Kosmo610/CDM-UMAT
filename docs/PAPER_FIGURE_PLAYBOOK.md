# 논문 그림 재현 플레이북 (Zhang 2022 전 그림 ↔ 명령어)

목표: **새 해석 없이**, 이미 있는 odb 에서 논문의 모든 그림을 같은
형식·같은 온도·같은 범례로 뽑는다. 스크립트는 전부 `E:\LTH` 에 1개씩.

**경로는 항상 `E:\LTH\<스크립트>.py` 절대경로로 쓴다.** odb 폴더
깊이가 제각각이라 `..\` 은 폴더에 따라 빗나간다. 실제 트리는
`docs/RUN_LAYOUT.md` 참고.

## 준비물 대응표

| 논문 그림 | 내용 | 도구 | 필요한 odb |
|---|---|---|---|
| Fig.3 | 냉각 잔류응력 S11 컨투어 5온도 | `make_odb_images.py --fig stress` | 경유 덱 아무거나 (P0 권장) |
| Fig.4 | 냉각 손상요소율 곡선 | `extract_cooling_damage.py` + `make_fig4_cooling.py` | ✔ 이미 확보 (P0/P1/P2) |
| Fig.5 | 냉각 손상 컨투어 3행×5온도 | `make_odb_images.py --fig damage` | 경유 덱 |
| Fig.6 | 승온 손상요소율 (변화없음) | `extract_cooling_damage.py --step Heating_*` | t500 / t1000 경유 |
| Fig.7/8 | 승온(23→500) 응력/손상 컨투어 | `make_odb_images.py --step Heating_500C` | t500 경유 |
| Fig.9/10 | 승온(500→1000) 응력/손상 컨투어 | `make_odb_images.py --step Heating_1000C` | t1000 경유 |
| Fig.11/13/15 | 응력-변형률 + 손상률 이중축 | `make_paper_figures.py` (`fig11_style_*.png`) | 인장 CSV (23/500/1000 확보) |
| Fig.12/14/16 | 인장 단계점 손상 컨투어 | `find_frames.py` → `make_odb_images.py --frames` | 인장 odb |
| Fig.A1~A3 | 단계점 손상변수 히스토그램 | `find_frames.py` → `extract_damage_histogram.py` → `make_fig_a1_histogram.py` | 인장 odb |
| Table 3 | 강도 3온도 | `make_paper_figures.py` (기존) | 인장 CSV |

온도 세트 (논문 그대로):

```
냉각  (Fig.3/5)  : 1050,750,500,250,23
승온500 (Fig.7/8): 23,125,250,375,500
승온1000(Fig.9/10): 500,625,750,875,1000
```

## 실행 순서

### 0) 프레임↔온도 확인 (odb 안에서 직접 검증) — 순차, 몇 초
```bat
cd /d E:\LTH\Try_P0
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t23_p0.odb --list
```

### 1) 냉각 컨투어 Fig.3+5 — 순차 권장 (CAE 토큰 1개)
```bat
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t23_p0.odb --fig stress --temps 1050,750,500,250,23
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t23_p0.odb --fig damage --temps 1050,750,500,250,23
```

### 2) 승온 추출 Fig.6 — 병렬 가능 (같은 폴더지만 출력 파일명이 달라 안전, 창 2개)
```bat
:: 두 odb 가 같은 폴더에 있다 (docs/RUN_LAYOUT.md 트리 참고)
cd /d "E:\LTH\Try_0805까지\Try_1430"
abaqus python E:\LTH\extract_cooling_damage.py CSIC_t500.odb --step Heating_500C --stride 2 --tag _500C
:: 창 2 (같은 폴더에서)
abaqus python E:\LTH\extract_cooling_damage.py CSIC_t1000.odb --step Heating_1000C --stride 2 --tag _1000C
```
→ `heating_damage_500C.csv` / `_1000C.csv`

**스크립트는 `..\` 가 아니라 `E:\LTH\` 절대경로로 부른다.** 폴더
깊이가 제각각이라 `..\` 은 폴더에 따라 빗나간다 (RUN_LAYOUT 참고).

### 3) 승온 컨투어 Fig.7/8, 9/10 — 순차 권장
```bat
cd /d "E:\LTH\Try_0805까지\Try_1430"
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t500.odb --step Heating_500C --fig stress --temps 23,125,250,375,500
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t500.odb --step Heating_500C --fig damage --temps 23,125,250,375,500
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t1000.odb --step Heating_1000C --fig stress --temps 500,625,750,875,1000
abaqus cae noGUI=E:\LTH\make_odb_images.py -- CSIC_t1000.odb --step Heating_1000C --fig damage --temps 500,625,750,875,1000
```

### 4) 곡선 그림 Fig.4/6/11/13/15 + Table 3 — 순차 (CSV 필요), 일반 python
```bat
cd /d E:\LTH
python make_fig4_cooling.py Try_P0 Try_P1 Try_P2 "Try_0805까지\Try_1430" --out E:\LTH
python make_paper_figures.py Try_P0 Try_P1 Try_P2 Try_C Try_D500 Try_D1000 ^
       "Try_0805까지\Try_1300" "Try_0805까지\Try_1430" --out E:\LTH
```
→ `fig4_cooling_damage.png`, `fig6_heating_damage.png`,
`fig11_style_*.png` (런당 1장, 논문 최대점이 속빈 원으로 함께 찍힘)

### 5) 인장 단계점 컨투어 Fig.12 + 히스토그램 Fig.A1 — 순차 (find→render)
```bat
:: (a) 단계점 프레임 찾기 (최대점의 5/35/70/100 %)
::     --paperstage 를 같이 주면 "논문 Fig.A1 최대점 손상상태에
::     해당하는 프레임" 도 같이 나온다. 우리 최대점과 다르면
::     그 차이 자체가 결과다 (§5.16C).
python find_frames.py Try_P0\tension_damage_P0.csv --stages --paperstage 23
:: (b) 나온 --frames 줄을 그대로:
abaqus cae noGUI=E:\LTH\make_odb_images.py -- Try_P0\CSIC_t23_p0.odb --step Tension_23C --fig damage --frames <a에서 나온 번호들>
abaqus python E:\LTH\extract_damage_histogram.py Try_P0\CSIC_t23_p0.odb --frames <같은 번호들> --tag _P0
:: (c) 히스토그램 그림 (일반 python, 순차 -- (b) 가 끝나야 함)
python make_fig_a1_histogram.py Try_P0 --out E:\LTH
```
→ `figA1_hist_P0.png` (단계 x 상·모드 격자),
`figA1_shape_P0.png` (평균 d / 저손상 비율 추이),
`damage_hist_shape_P0.csv`

## 주의

- **직행(DIRECT) odb 의 냉각**은 1050→500/1000 이므로 `--temps` 를
  쓰려면 `--trange 1050,500` 지정. (논문 재현 그림에는 직행 안 씀)
- 승온 컨투어의 손상(Fig.8/10)은 논문에서도 "변화 없음" 이 정답 —
  냉각 끝 그림과 같아 보이는 것이 정상.
- 인장 스텝은 온도 일정 → `--temps` 불가, `--frames` 사용
  (`find_frames.py` 가 번호를 준다).
- 렌더링은 컨테이너에서 검증 불가. 첫 장에서 시점·범례 확인.
- 컨투어는 `abaqus cae noGUI=` 로 실행 (viewer 도 가능하나 미검증).
  과거 dgo ImportError 의 진짜 원인은 커널이 아니라 스크립트가
  `visualization` 을 먼저 import 하지 않은 것 -- 2026-08-10 수정됨.
- **콘솔이 비는 것은 정상이다.** 이 환경의 `abaqus cae noGUI=` 는
  스크립트 stdout 을 콘솔에 안 남긴다 (라이선스 줄만 찍고 프롬프트로
  돌아온다). 실패했다는 뜻이 아니다 -- 두 번의 실패 모두 로그
  파일에는 트레이스백과 `exit : N` 이 온전히 남아 있었다.
  **판정은 항상 로그로 한다:**

  ```bat
  type make_odb_images_log.txt
  dir *.png
  ```

  `exit : 0` 이면 성공. 로그가 짧으면 아직 렌더링 중일 수 있으니
  잠시 뒤 다시 `type` 한다.
