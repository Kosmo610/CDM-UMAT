# 랩미팅 2026-08-06 — RVE 구축과 주기경계조건 검증

## 발표용 (이걸 쓸 것): `CSiC_RVE_PBC_UMAT_visual.pptx` — 4장 + 부록 2장

발표자가 만든 **TexGen 슬라이드 뒤에** 이어 붙이는 구성이다.

| # | 슬라이드 | 시각 요소 |
|---|---|---|
| 1 | RVE | `fig_rve.png` — 실제 메쉬에서 뽑은 얀 4개 + 전체 RVE |
| 2 | PBC 코드 | 덱(.inp)의 `*NSet` / `*Node` / `*Equation` **원문 발췌** + 항별 해설 4개 |
| 3 | UMAT 코드 | V2_7 Fortran **원문 발췌** 5덩어리 (상 판별 → 손상변수 → 크랙밴드 → 비가역·점성 → 강성저하) |
| 4 | **작동 증명** | `fig_tile.png` — 변형된 셀을 3×3 으로 깔면 이음매가 **4.4e−16 mm** 로 맞는다 |
| A | 부록 | `fig_pair.png` — 마주보는 면의 절점 패턴 일치 / 58쌍 변위 점프 |
| B | 부록 | `fig_patch.png` — 26,452개 요소 응력 분포 |

다른 버전:
- `CSiC_PBC_RVE_4slides.pptx` — 그림 없는 텍스트 4장 (이전 버전)
- `CSiC_RVE_labmeeting_0806.pptx` — 전체 서사 19장 (참고용 보관)

## 새 결과 — 패치 테스트를 Python 으로 독립 재현했다

`verification/pbc_patch_python.py` 는 **실제 덱**(`abaqus/meshes/CSiC_RVE_0135.inp`,
브랜치 `claude/easypbc-plugin-guide-mj0xi5`)의 절점·C3D4 요소·`*NSet`·`*Boundary`·
`*Equation` 을 그대로 읽어, 셀 전체를 등방 재료(E = 350 GPa, ν = 0.2) 하나로 채우고
드라이버 절점으로 거시 변형률을 건 뒤 닫힌 해와 비교한다. Abaqus 도
`check_pbc.py` 도 쓰지 않는 **독립 구현**이다.

| 판정 항목 | 기준 | 인장 ε_x | 전단 ε_xy |
|---|---|---|---|
| 응력장 균일성 | < 1e−6 | **2.10e−12** | **4.51e−12** |
| 변형률 균일성 | < 1e−6 | **3.39e−12** | **4.24e−12** |
| 주기 요동 `u − H·x` 퍼짐 | < 1e−6 | **7.34e−14** | **6.64e−14** |
| 균질화 강성 C 열 오차 | < 1e−6 | **5.41e−15** | **6.04e−15** |
| 부피 충전율 | 1 ± 1e−3 | **100.0000 %** | **100.0000 %** |

부수적으로 얻은 값:

- 마주보는 z 면(각 925 절점)의 **절점 패턴 차이 0.0 mm** — 메쉬 자체가 주기적
- x 면 58쌍의 변위 점프가 전부 ε·Lx 위에 정확히 — **최대 편차 0.0 mm**
- 변형된 셀의 **3×3 타일 이음매 어긋남 4.4e−16 mm**
- 파싱 결과가 `check_pbc.py` 와 일치: V = 5.390000 mm³, 충전율 100.0000 %,
  57 카드 → 3,645 스칼라 식, 소거 DOF 중복 0

**한계 — 발표에서 반드시 밝힐 것**: 이것은 구속식·메쉬가 옳다는 증명이지
**Abaqus 실행 검증이 아니다.** `PBC_VALIDATION_GUIDE.md` 의 1단계
(`PBC_PATCH.inp` + Abaqus)는 여전히 남아 있다.

## 재생성

```bash
# 그림 — mesh.inp(=CSiC_RVE_0135.inp)와 pbc_patch_python.py 가 같은 폴더에 필요
python3 pbc_patch_python.py mesh.inp exx
python3 pbc_patch_python.py mesh.inp exy
python3 make_figs.py                     # -> figs/fig_*.png

# 덱
npm install pptxgenjs
node build_visual.js        # -> CSiC_RVE_PBC_UMAT_visual.pptx   (발표용)
node build_pbc4.js          # -> CSiC_PBC_RVE_4slides.pptx
node build_deck.js          # -> CSiC_RVE_labmeeting_0806.pptx
```

## 풀버전(19장) 슬라이드 구성

| # | 슬라이드 | 근거 |
|---|---|---|
| 1 | 제목 | 논문 Fig. 2(c) |
| 2 | 오늘 다룰 것 — 5단계 파이프라인 | — |
| 3 | 지금 어디까지 왔나 | `PAPER_DEVIATION_REGISTER.md` §0, 브리프 §3·§8 |
| 4 | 재현 대상 — Zhang et al. (2022) | 논문 Table 3, §2, §3.2.4 |
| 5 | 논문의 시편 | 논문 Fig. 1 (치수 직접 판독) |
| 6 | 시편 → RVE (핵심) | 논문 치수로부터 계산 |
| 7 | 논문의 형상 모델링 — CT → 타원 → TexGen | 논문 §3.2.1, Fig. 2 |
| 8 | 우리 RVE 대조표 | 등록부 §2, 브리프 §3.1, `abaqus/meshes/README.md` |
| 9 | TexGen 출력 3종 세트 | `abaqus/meshes/README.md`, `MESH_REGEN_GUIDE.md` |
| 10 | 얀 배향 검증 | `abaqus/meshes/README.md` 검증표 |
| 11 | 주기경계조건 — 왜 필요한가 | 논문 §3.2.2 |
| 12 | 구현 — `*Equation` 57식 + 드라이버 절점 | `PBC_VALIDATION_GUIDE.md` |
| 13 | 검증 4단계 사다리 | `PBC_VALIDATION_GUIDE.md` |
| 14 | 0단계 — 솔버 없는 정적 감사 7종 | `verification/check_pbc.py` 실행 결과 |
| 15 | 감사 도구 자체 검증 — 결함 11종 주입 | `verification/test_check_pbc.py` |
| 16 | 1~3단계 — 준비됨, 미실행 | `PBC_VALIDATION_GUIDE.md` |
| 17 | 확보된 PBC 증거 4가지 | 브리프 §7, §4.5 |
| 18 | 조립과 해석 절차 | `assemble_inp.py`, 논문 §3.2.4, 브리프 §3.3 |
| 19 | 여기까지의 결과 · 다음 | 브리프 §4.1, §6.1, §8 |

## 숫자 출처 원칙

브리프·등록부·논문 원문에 있는 값만 썼다. 예외는 슬라이드 6의 세 값뿐이며,
슬라이드 하단에 **논문 명시값이 아니라 계산값**이라고 적어 두었다.

| 계산값 | 유도 |
|---|---|
| 게이지부 630 mm³ | 30 × 6 × 3.5 (논문 Fig. 1) |
| RVE 5.31 mm³ | 3.5 × 3.5 × 0.4334 (논문 §3.2.1) |
| ≈ 119 개 | 630 ÷ 5.309 |
| ≈ 8 층 | 3.5 ÷ 0.4334 |

**발표에서 반드시 밝힐 것 (슬라이드 19에 이미 넣어 둠)**: 23 °C 의
125.81 MPa 는 얀 종방향 강도 `X_y,1t = 421 MPa` 를 논문 Table 3 에 맞춰
역보정해 얻은 값이다. 예측이 아니라 보정이다.

## 알려진 표기 주의

- 슬라이드 10 의 배향 검증표는 **coarse 메쉬(26,452 요소)** 기준,
  슬라이드 14 의 PBC 감사 결과는 **생산 메쉬(174,405 요소)** 기준이다.
  두 메쉬의 숫자를 섞어 말하지 않도록 슬라이드에 각각 명시해 두었다.
- 등록부 §2 의 "특성 요소크기 0.0570 mm" 는 §5.8 에서 coarse 메쉬 값으로
  정정되었다. 생산 메쉬의 체적가중 평균은 **0.0314 mm** 이고 덱은 이 값을 쓴다.

## figs/

논문 PDF 에서 추출한 그림이다. 원본 PDF 는 커밋하지 않는다.

```bash
pdfimages -f 2 -l 2 -png <paper>.pdf figs/p2   # Fig. 1  (시편)
pdfimages -f 5 -l 5 -png <paper>.pdf figs/p5   # Fig. 2  (CT → 타원 → TexGen)
```

| 파일 | 내용 |
|---|---|
| `p5-000.png` | 논문 Fig. 2 전체 (a)(b)(c) |
| `fig2c.png` | Fig. 2(c) 만 크롭 — TexGen RVC |
| `fig1_spec.png` | Fig. 1 상단 크롭 — 시편 치수도 |
