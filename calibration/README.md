# calibration/ — 보정 루프 (그래프의 서브그래프 A)

`CALIBRATION_GUIDE.md`의 Stage A–E 시행착오 보정을 **상태(원장) + 게이트**가 있는
루프로 자동화한 것. 한 번의 반복(iteration):

```bash
# A0. 파라미터 변경 + 3온도 덱 생성 + 원장 기록   (이 저장소, 어디서든)
python3 calibration/make_cards.py --stage B --set Yt=70 --set S23=90 --note "의도"

# A1. 3온도 해석                                   (Abaqus 머신)
abaqus job=Job-RT23  input=abaqus/ZHANG2022_RT23_V2_0.inp  user=src/UMAT_CSIC_RVE_ZHANG2022_V1_0.for double interactive
abaqus job=Job-T500  input=abaqus/ZHANG2022_T500_V2_0.inp  user=src/... double interactive
abaqus job=Job-T1000 input=abaqus/ZHANG2022_T1000_V2_0.inp user=src/... double interactive

# A2. 곡선 추출                                     (Abaqus 머신)
abaqus python postprocess/extract_ss_curve.py Job-RT23.odb   # 등 3회

# A3+A4. 지표·손실·Stage 게이트 판정 + 원장 기록     (어디서든)
python3 calibration/evaluate.py Job-RT23_ss.csv Job-T500_ss.csv Job-T1000_ss.csv --stage B
#   PASS -> 다음 Stage로 (make_cards --stage C ...)
#   FAIL -> 제안된 knob 조정 후 같은 Stage 반복      (exit code 2)
```

- **ledger.json** — 반복마다 `{iter, stage, params, changed, results, loss, gates, note}`
  가 쌓이는 상태 객체. 시행착오 추적성(GUIDE §3)의 근거 자료이며, 논문 3장 수치는
  여기의 최종 채택 iteration에서만 인용한다 (`paper/OUTLINE.md` §4).
- **make_cards.py** — knob 이름으로 파라미터를 바꾸면 세 덱의 `*User Material`
  카드를 동일하게 갱신 (온도독립 가정 강제). 검증된 탄성/CTE 슬롯은 잠겨 있음.
  `--baseline` = Stage A 기저 (SY0=0, X_PO=0). `--dry-run` = 카드 미리보기.
- **evaluate.py** — 극한강도·초기기울기·완주 여부 계산, Table 3 대비 loss(RMS),
  Stage A–E PASS/FAIL 게이트. matplotlib 불필요 (그림은 `postprocess/plot_compare.py`).

Stage 게이트 의미는 `verification/CALIBRATION_GUIDE.md` §3 참조.
